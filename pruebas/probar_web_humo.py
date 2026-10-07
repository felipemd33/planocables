"""Prueba de humo de la web (etapa 0 del plan modular, bateria B). No escribe en los trabajos ni en el historial del
usuario: la web corre sobre copias en una carpeta temporal. Termina con error si algo falla.
uso: python pruebas/probar_web_humo.py [--crear] [--sin-pythonw]
  --crear:       (re)escribe los golden de pruebas/bases/web/ con lo que da el codigo de hoy
  --sin-pythonw: salta la parte B
  A. Flask test_client sobre copias del 75287 (ac0f0949510a) y del TPT: paginas, estado, resultado, imagen de la hoja,
     regenerar el instructivo (comparado con el golden y con la base de regresion), una marca 'hecho' de ida y vuelta
     (y que sobrevive a otro regenerar), vista previa de salidas a LI / LD, pestaña y API del proyector, topo.png y los
     estaticos (wpc.json, terminales.json y los .js / .css de las paginas).
  B. Arranque como en el taller (pythonw, sin consola) en el puerto 8791 con un historial temporal; cierre con
     POST /api/salir y el proceso tiene que terminar.
  C. Nada cambio fuera de pruebas/ (git status), ni en '3 - Historial web' ni en pruebas/trabajos."""
import os, sys, io, json, re, time, shutil, socket, hashlib, tarfile, tempfile, subprocess, urllib.request
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROG = os.path.join(RAIZ, 'programa')
GOLD = os.path.join(RAIZ, 'pruebas', 'bases', 'web')
sys.stdout.reconfigure(encoding='utf-8')
sys.dont_write_bytecode = True          # (nada de __pycache__ nuevo en programa/)
CREAR = '--crear' in sys.argv
PUERTO_A = 8798     # solo para el Host de test_client (no abre el puerto)
PUERTO_B = 8791     # arranque con pythonw. Nunca 8765 (el del taller)
ID_75287 = 'ac0f0949510a'
TRABAJOS = [('75287', os.path.join(RAIZ, '3 - Historial web', ID_75287), {}, 'base_75287.json'),
            ('tpt', os.path.join(RAIZ, 'pruebas', 'trabajos', 'tpt'), {'releer': True}, 'base_tpt_ronda3.json')]   # (TPT: como --relayout)
PROTEGIDAS = [os.path.join(RAIZ, '3 - Historial web'), os.path.join(RAIZ, 'pruebas', 'trabajos')]
VOLATILES = {'generado', 'segundos', 'tiempos', 'de_cache', 'fecha', 'ts', 'log', 'transcurrido', 'inicio'}
fallas = []


def chequear(ok, msg):
    print(('  ok    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)
    return ok


# ------------------------------------------------------------------ fotos del repo (parte C)
def foto_carpeta(d):
    out = {}
    for r, _, fs in os.walk(d):
        for f in fs:
            p = os.path.join(r, f)
            st = os.stat(p)
            out[os.path.relpath(p, d)] = (st.st_size, st.st_mtime_ns)
    return out


def git_fuera_de_pruebas():
    r = subprocess.run(['git', '-c', 'core.quotepath=false', '-C', RAIZ, 'status', '--porcelain=v1', '-uall'],
                       capture_output=True, text=True, encoding='utf-8')
    if r.returncode:
        return None
    return sorted(l for l in r.stdout.splitlines() if not l[3:].strip('"').startswith('pruebas/'))


def sha(p):
    try:
        with open(p, 'rb') as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None


def foto_repo():
    return dict(git=git_fuera_de_pruebas(), ocr=sha(os.path.join(PROG, 'ocr_cache.json')),
                carpetas={d: foto_carpeta(d) for d in PROTEGIDAS})


# ------------------------------------------------------------------ golden
def normalizar(x, tmp):
    if isinstance(x, dict):
        return {k: normalizar(v, tmp) for k, v in x.items() if k not in VOLATILES}
    if isinstance(x, list):
        return [normalizar(v, tmp) for v in x]
    if isinstance(x, str):
        for t in (tmp, tmp.replace('\\', '/')):
            x = x.replace(t, '<TMP>')
    return x


def diferencias(a, b, camino='', out=None, maximo=12):
    out = [] if out is None else out
    if len(out) >= maximo:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in list(a) + [k for k in b if k not in a]:
            if k not in a or k not in b:
                out.append(f'{camino}/{k}: {"falta en el golden" if k not in b else "falta ahora"}')
            else:
                diferencias(a[k], b[k], f'{camino}/{k}', out, maximo)
            if len(out) >= maximo:
                break
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f'{camino}: {len(a)} elementos (golden {len(b)})')
        for i, (x, y) in enumerate(zip(a, b)):
            diferencias(x, y, f'{camino}[{i}]', out, maximo)
            if len(out) >= maximo:
                break
    elif a != b:
        out.append(f'{camino}: {str(a)[:120]!s} (golden {str(b)[:120]!s})')
    return out


def contra_golden(t, actual):
    p = os.path.join(GOLD, f'humo_{t}.json')
    if CREAR:
        os.makedirs(GOLD, exist_ok=True)
        with open(p + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(actual, f, ensure_ascii=False, indent=1)
        os.replace(p + '.tmp', p)
        print(f'    golden escrito: {os.path.relpath(p, RAIZ)}')
        return
    if not chequear(os.path.exists(p), f'{t}: existe el golden {os.path.relpath(p, RAIZ)} (si no, correr con --crear)'):
        return
    with open(p, encoding='utf-8') as f:
        gold = json.load(f)
    for parte in actual:
        d = diferencias(actual[parte], gold.get(parte))
        chequear(not d, f'{t}: {parte} igual al golden' + ('' if not d else ':\n          ' + '\n          '.join(d)))


# ------------------------------------------------------------------ parte A: test_client
def copiar_trabajos(hist, tmp):
    ids = {}
    for t, src, _, _ in TRABAJOS:
        if not os.path.isdir(src) and t == '75287':
            # el usuario lo borro del historial (2026-10-05): se saca de git a una carpeta temporal (nunca al historial)
            r = subprocess.run(['git', '-C', RAIZ, 'archive', '--format=tar', 'HEAD', f'3 - Historial web/{ID_75287}'], capture_output=True)
            if r.returncode == 0:
                tarfile.open(fileobj=io.BytesIO(r.stdout)).extractall(os.path.join(tmp, 'git'), filter='data')
                src = os.path.join(tmp, 'git', '3 - Historial web', ID_75287)
        if not chequear(os.path.isdir(src), f'{t}: está el trabajo ({src})'):
            continue
        with open(os.path.join(src, 'estado.json'), encoding='utf-8') as f:
            jid = json.load(f)['id']        # (la carpeta del TPT se llama 'tpt': en la web va con su id)
        shutil.copytree(src, os.path.join(hist, jid))
        ids[t] = jid
    return ids


def lineas_de(ins):
    return [l for p in ins.get('pasos') or [] for l in p.get('lineas') or []]


def parte_a(tmp):
    hist = os.path.join(tmp, 'hist_a')
    os.makedirs(hist)
    ids = copiar_trabajos(hist, tmp)
    # el historial y el puerto se leen al importar web
    os.environ['PLANOCABLES_HISTORIAL'] = hist
    os.environ['PLANOCABLES_PORT'] = str(PUERTO_A)
    sys.path.insert(0, PROG)
    import web
    chequear(os.path.normcase(os.path.abspath(web.WORK)) == os.path.normcase(hist), f'la web usa el historial temporal ({web.WORK})')
    chequear(os.path.normcase(web.ROOT) == os.path.normcase(RAIZ), f'web.py es el de este repo ({web.__file__})')
    if fallas:
        return
    cl = web.app.test_client()
    BASE = f'http://127.0.0.1:{web.PORT}'
    get = lambda u, **kw: cl.get(u, base_url=BASE, **kw)
    post = lambda u, **kw: cl.post(u, base_url=BASE, **kw)
    put = lambda u, **kw: cl.put(u, base_url=BASE, **kw)

    print('A1. páginas, lista de trabajos y solo_local')
    r = get('/')
    chequear(r.status_code == 200 and r.mimetype == 'text/html' and b'/static/app.js?v=' in r.data, 'GET / sirve index.html con los .js versionados')
    estaticos = sorted(set(re.findall(r'/static/[\w.-]+\.(?:js|css)\?v=\d+', r.get_data(as_text=True))))
    r = get('/api/trabajos')
    lista = r.get_json() if r.status_code == 200 else None
    chequear(isinstance(lista, list) and {e.get('id') for e in lista} == set(ids.values())
             and all({'id', 'nombre', 'estado', 'cables'} <= set(e) for e in lista), f'GET /api/trabajos: los {len(ids)} trabajos copiados')
    chequear(cl.get('/', base_url='http://evil.example:80').status_code == 403, 'otro Host: 403')
    jid0 = next(iter(ids.values()))
    r = post(f'/api/trabajo/{jid0}/instructivo/salidas', json={}, headers={'Origin': 'http://evil.example'})
    chequear(r.status_code == 403, 'POST con otro Origin: 403')
    chequear(get('/api/trabajo/0123456789ab/estado').status_code == 404 and get('/api/trabajo/zzz/estado').status_code == 404,
             'trabajo que no existe o id inválido: 404')

    for t, _, cuerpo, base_nombre in TRABAJOS:
        if t not in ids:
            continue
        jid = ids[t]
        u = f'/api/trabajo/{jid}'
        print(f'A2. {t} ({jid}): estado, resultado e imagen de la hoja')
        r = get(u + '/estado')
        j = r.get_json() or {}
        chequear(r.status_code == 200 and j.get('id') == jid and j.get('estado') == 'terminado' and len(j.get('log') or []) <= 12,
                 f'GET /estado: terminado ({j.get("estado")}), log recortado')
        r = get(u + '/resultado')
        if os.path.exists(os.path.join(hist, jid, 'resultado.json')):
            j = r.get_json() if r.status_code == 200 else {}
            chequear(r.status_code == 200 and {'nombre', 'paginas', 'cables', 'detalle', 'revisar'} <= set(j) and j['cables'],
                     f'GET /resultado: listado con {len(j.get("cables") or [])} filas y {len(j.get("paginas") or [])} hojas')
        else:
            chequear(r.status_code == 404, f'GET /resultado sin resultado.json: 404 ({r.status_code})')
        t0 = time.time()
        r = get(u + '/pagina/1.png')
        chequear(r.status_code == 200 and r.mimetype == 'image/png' and r.data[:8] == b'\x89PNG\r\n\x1a\n',
                 f'GET /pagina/1.png ({len(r.data) // 1024} KB, {time.time() - t0:.1f} s)')
        chequear(get(u + '/pagina/999.png').status_code == 404, 'GET /pagina/999.png: 404')

        print(f'A3. {t}: regenerar el instructivo')
        r = get(u + '/instructivo/estado')
        j = r.get_json() or {}
        chequear(r.status_code == 200 and j.get('hay_topo') is True and j.get('hay_instructivo') is True, 'GET /instructivo/estado: hay topográfico e instructivo')
        t0 = time.time()
        r = post(u + '/instructivo/regenerar', json=cuerpo)
        chequear(r.status_code == 200 and (r.get_json() or {}).get('ok'), f'POST /instructivo/regenerar {json.dumps(cuerpo)}')
        r2 = post(u + '/instructivo/regenerar', json=cuerpo)
        chequear(r2.status_code == 409, f'otro regenerar mientras se genera: 409 ({r2.status_code})')
        st = esperar(get, u)
        seg = time.time() - t0
        if not chequear(st.get('estado') == 'terminado', f'el instructivo se generó en {seg:.0f} s ({st.get("estado")} {st.get("error") or ""})'):
            print(web.INS.get(jid, {}).get('detalle', ''))
            continue
        r = get(u + '/instructivo')
        ins = r.get_json() if r.status_code == 200 else {}
        claves = {'pasos', 'pendientes', 'sueltos', 'otra_estacion', 'componentes', 'topo', 'mapeo', 'estacion8', 'salidas',
                  'producto', 'estacion', 'estaciones', 'estacion_auto', 'auditoria', 'wpc', 'proyector', 'overrides',
                  'generado', 'topografico', 'hoja_topo', 'editado'}
        chequear(r.status_code == 200 and claves <= set(ins), f'GET /instructivo: todas las secciones (faltan {sorted(claves - set(ins))})')
        ls = lineas_de(ins)
        chequear(ls and all({'num', 'cable', 'origen', 'destino', 'componente', 'fila', 'lado'} <= set(l) for l in ls)
                 and all({'titulo', 'lineas'} <= set(p) for p in ins['pasos']), f'{len(ins["pasos"])} pasos y {len(ls)} líneas con sus campos')
        chequear(all({'num', 'a', 'b'} <= set(x) for x in ins['pendientes']) and isinstance(ins['sueltos'], list)
                 and all({'num', 'origen', 'destino'} <= set(x) for x in ins['otra_estacion']),
                 f'{len(ins["pendientes"])} pendientes, {len(ins["sueltos"])} sueltos, {len(ins["otra_estacion"])} en otra estación')
        tp = ins.get('topo') or {}
        chequear(tp.get('ductos') and tp.get('region') and tp.get('escala') and tp.get('pag'), 'topo con bandeja, canaletas y escala')
        chequear(ins.get('editado') is False and not (ins.get('mapeo') or {}).get('error') and not (ins.get('estacion8') or {}).get('detalle'),
                 f'sin errores del mapeo ni de E8 ({(ins.get("mapeo") or {}).get("error")})')
        # mismo resultado que volcar_trabajo.py (la base de regresion de ese trabajo)
        with open(os.path.join(RAIZ, 'pruebas', 'bases', base_nombre), encoding='utf-8') as f:
            bb = json.load(f)
        ya = [(l['num'], l['cable'], l['origen'], l['destino'], bool(l.get('ruta')), bool(l.get('exacto_o'))) for l in ls]
        yb = [(l['num'], l['cable'], l['origen'], l['destino'], l['ruta'], l['exacto']) for l in bb['lineas']]
        chequear(ya == yb, f'líneas iguales a {base_nombre} ({len(ya)} / {len(yb)})')
        chequear([(x['num'], x['a'], x['b']) for x in ins['pendientes']] == [(x['num'], x['a'], x['b']) for x in bb['pendientes']]
                 and ins['sueltos'] == bb['sueltos']
                 and [(x['num'], x['origen'], x['destino']) for x in ins['otra_estacion']] == [(x['num'], x['origen'], x['destino']) for x in bb['otra_estacion']],
                 f'pendientes, sueltos y otra estación iguales a {base_nombre}')
        golden = dict(instructivo=normalizar(ins, tmp))

        print(f'A4. {t}: marca «hecho» de ida y vuelta')
        hechos0 = sum(1 for l in ls if l.get('hecho'))
        k = next((i for i, l in enumerate(ls) if not l.get('hecho')), 0)       # una sin marcar (o se desmarca la primera)
        marca = not ls[k].get('hecho')
        clave = (ls[k]['num'], ls[k]['origen'], ls[k]['destino'])
        ls[k]['hecho'] = marca
        ins['proyector'] = {'calibracion': 'vieja'}      # (la ventana principal manda una copia vieja: no tiene que pisar la del disco)
        r = put(u + '/instructivo', json=ins)
        chequear(r.status_code == 200, f'PUT /instructivo con {clave[0]} hecho={marca}')
        ins2 = get(u + '/instructivo').get_json() or {}
        l2 = [l for l in lineas_de(ins2) if (l['num'], l['origen'], l['destino']) == clave]
        chequear(len(l2) == 1 and bool(l2[0].get('hecho')) == marca and ins2.get('editado') is True,
                 f'GET /instructivo: la marca se conserva y queda editado ({hechos0} → {sum(1 for l in lineas_de(ins2) if l.get("hecho"))} hechos)')
        chequear(ins2.get('proyector') == golden['instructivo'].get('proyector'), 'PUT /instructivo conserva la sección proyector del disco')
        chequear(put(u + '/instructivo', json={'pasos': 'no'}).status_code == 400, 'PUT /instructivo inválido: 400')

        print(f'A5. {t}: vista previa de salidas a LI / LD')
        sal = [l for l in ls + (ins.get('otra_estacion') or []) if (l.get('lateral') or l.get('destino')) in ('LI', 'LD')]
        cuerpo_l = [dict(num=l['num'], destino=l['destino'], lateral=l.get('lateral'), marca_o=l.get('marca_o') or (l.get('ruta') or [None])[0],
                         lado=l.get('lado'), color=l.get('color'), secc=l.get('secc'), **({'intrinseco': l['intrinseco']} if 'intrinseco' in l else {}))
                    for l in sal]
        r = post(u + '/instructivo/salidas', json=dict(lineas=cuerpo_l, salidas={'grupos': []}))
        rt = (r.get_json() or {}).get('rutas') if r.status_code == 200 else None
        chequear(isinstance(rt, list) and len(rt) == len(sal), f'POST /instructivo/salidas (regla del taller): {len(sal)} cables a LI / LD')
        if rt:
            # (build rutea desde el punto sin redondear y la vista previa desde marca_o, redondeado a 0,01: puede haber
            # una decima de diferencia en algun vertice, ej. 6204 / 6205 del 75287)
            cerca = lambda a, b: (a is None) == (b is None) and (a is None or len(a) == len(b) and all(
                abs(p[0] - q[0]) <= 0.5 and abs(p[1] - q[1]) <= 0.5 for p, q in zip(a, b)))
            iguales = sum(1 for l, x in zip(sal, rt) if x['ruta'] == l.get('ruta'))
            parecidas = sum(1 for l, x in zip(sal, rt) if cerca(x['ruta'], l.get('ruta')) and x['largo_mm'] == l.get('largo_mm'))
            chequear(parecidas == len(sal), f'sin grupos da la misma ruta y el mismo largo que el instructivo, a menos de 0,5 pt '
                                            f'({parecidas}/{len(sal)}; idénticas {iguales})')
        # un grupo «Todos los LI» que sale por el ultimo punto de la ruta de un cable a LI
        fin = next((l['ruta'][-1] for l in sal if l.get('destino') == 'LI' and l.get('ruta') and not l.get('intrinseco')), None)
        grupo = dict(id='humo', aplica='LI', puntos=[fin] if fin else [])
        r = post(u + '/instructivo/salidas', json=dict(lineas=cuerpo_l, salidas={'grupos': [grupo]}))
        rg = (r.get_json() or {}).get('rutas') if r.status_code == 200 else None
        if chequear(isinstance(rg, list) and len(rg) == len(sal) and fin is not None, f'POST /instructivo/salidas con un grupo «Todos los LI» por {fin}'):
            ex = lambda c: c['intrinseco'] if 'intrinseco' in c else c.get('color') == 'Azul'       # (como rutear_salidas)
            esperado = [(c.get('lateral') or c['destino']) == 'LI' and not ex(c) and bool(c['marca_o']) for c in cuerpo_l]
            chequear([x['salida'] == 'humo' for x in rg] == esperado, f'los LI no intrínsecos toman el grupo ({sum(esperado)}) y el resto no')
        chequear(post(u + '/instructivo/salidas', json={'lineas': 'no'}).status_code == 400, 'POST /instructivo/salidas inválido: 400')
        golden.update(salidas_taller=normalizar(rt, tmp), salidas_grupo=normalizar(rg, tmp))

        print(f'A6. {t}: proyector y topo.png')
        r = get(f'/proyector/{jid}')
        chequear(r.status_code == 200 and b'proyector.js?v=' in r.data, 'GET /proyector/<id> sirve la pestaña')
        estaticos += re.findall(r'/static/[\w.-]+\.(?:js|css)\?v=\d+', r.get_data(as_text=True))
        r = get(u + '/proyector')
        j = r.get_json() if r.status_code == 200 else {}
        o = j.get('orificios') or {}
        chequear(r.status_code == 200 and j.get('topo', {}).get('region') == tp.get('region') and isinstance(o.get('puntos'), list)
                 and o.get('fuente') in ('dibujo', 'esquinas') and isinstance(j.get('comp'), dict) and j.get('estacion'),
                 f'GET /api/.../proyector: bandeja, {len(o.get("puntos") or [])} orificios ({o.get("fuente")}) y {len(j.get("comp") or {})} aparatos')
        golden['proyector'] = normalizar(dict(orificios=o, estacion=j.get('estacion')), tmp)
        cal = dict(dst=[[10, 10], [900, 12], [905, 600], [8, 598]], pantalla=[1920, 1080])
        r = put(u + '/proyector', json=dict(calibracion=cal, ventana=dict(x=1, y=2, w=300, h=200)))
        j = get(u + '/proyector').get_json() or {}
        chequear(r.status_code == 200 and j.get('calibracion') == cal and (j.get('ventana') or {}).get('w') == 300, 'PUT /api/.../proyector: calibración y ventana de ida y vuelta')
        ins3 = get(u + '/instructivo').get_json() or {}
        l3 = [l for l in lineas_de(ins3) if (l['num'], l['origen'], l['destino']) == clave]
        chequear(len(l3) == 1 and bool(l3[0].get('hecho')) == marca and ins3.get('proyector', {}).get('calibracion') == cal,
                 'el PUT del proyector no toca las marcas y queda guardado en el instructivo')
        r = get(u + '/topo.png')
        chequear(r.status_code == 200 and r.mimetype == 'image/png' and r.data[:4] == b'\x89PNG', f'GET /topo.png ({len(r.data) // 1024} KB)')

        print(f'A7. {t}: regenerar otra vez conserva la marca y el proyector')
        t0 = time.time()
        r = post(u + '/instructivo/regenerar', json={})
        st = esperar(get, u)
        if chequear(r.status_code == 200 and st.get('estado') == 'terminado', f'regenerado en {time.time() - t0:.0f} s'):
            ins4 = get(u + '/instructivo').get_json() or {}
            l4 = [l for l in lineas_de(ins4) if (l['num'], l['origen'], l['destino']) == clave]
            chequear(len(l4) == 1 and bool(l4[0].get('hecho')) == marca, f'la marca de {clave[0]} sobrevive')
            chequear(sum(1 for l in lineas_de(ins4) if l.get('hecho')) == sum(1 for l in lineas_de(ins3) if l.get('hecho')), 'y las demás marcas también')
            chequear((ins4.get('proyector') or {}).get('calibracion') == cal and ins4.get('editado') is False, 'se conserva la calibración del proyector')
            chequear([(l['num'], l['origen'], l['destino']) for l in lineas_de(ins4)] == [(l['num'], l['origen'], l['destino']) for l in ls],
                     'mismas líneas que la primera vez')
        contra_golden(t, golden)

    print('A8. estáticos')
    for nombre in ('wpc.json', 'terminales.json'):
        r = get('/static/' + nombre)
        with open(os.path.join(PROG, 'web', nombre), encoding='utf-8') as f:
            disco = json.load(f)
        chequear(r.status_code == 200 and r.get_json() == disco, f'GET /static/{nombre} (igual al archivo)')
    chequear({'margen_bandeja', 'agregado_bandeja', 'acometida', 'curva_LI', 'acometida_LI', 'puerta'} <= set(get('/static/wpc.json').get_json() or {}),
             'wpc.json con los parámetros de los largos')
    j = get('/static/terminales.json').get_json() or {}
    chequear(isinstance(j.get('pino'), dict) and isinstance(j.get('doble'), dict) and j['pino'].get('2.5') == 'azul', 'terminales.json: pino 2,5 = azul y doble')
    malos = [e for e in sorted(set(estaticos)) if get(e).status_code != 200]
    chequear(estaticos and not malos, f'los {len(set(estaticos))} .js / .css de las páginas responden ({malos})')


def esperar(get, u, limite=900):
    t0 = time.time()
    st = {}
    while time.time() - t0 < limite:
        st = get(u + '/instructivo/estado').get_json() or {}
        if st.get('estado') in ('terminado', 'error'):
            return st
        time.sleep(0.5)
    return dict(st, estado='sin terminar a los %d s' % limite)


# ------------------------------------------------------------------ parte B: pythonw
def abrir(url, metodo='GET', headers=None, timeout=3):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))      # (sin proxy del sistema)
    req = urllib.request.Request(url, data=b'' if metodo == 'POST' else None, method=metodo, headers=headers or {})
    with op.open(req, timeout=timeout) as r:
        return r.status, r.read()


def puerto_ocupado(p):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', p)) == 0


def parte_b(tmp):
    print('B. arranque con pythonw (como el .bat del taller) en el puerto', PUERTO_B)
    pyw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
    if not chequear(os.name == 'nt' and os.path.exists(pyw), f'está pythonw.exe ({pyw})'):
        return
    if not chequear(not puerto_ocupado(PUERTO_B), f'el puerto {PUERTO_B} está libre'):
        return       # (con otra web ahi, web.py solo abriria el navegador y saldria)
    hist = os.path.join(tmp, 'hist_b')
    os.makedirs(os.path.join(hist, 'abcabcabcabc'))
    with open(os.path.join(hist, 'abcabcabcabc', 'estado.json'), 'w', encoding='utf-8') as f:     # (para saber que responde ESTA web)
        json.dump(dict(id='abcabcabcabc', nombre='humo.pdf', archivo='humo.pdf', estado='terminado'), f)
    env = dict(os.environ, PLANOCABLES_PORT=str(PUERTO_B), PLANOCABLES_HISTORIAL=hist, PYTHONDONTWRITEBYTECODE='1')
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    # con estas opciones pythonw arranca sin stdout ni stderr, como con 'start pythonw' (un print al importar romperia)
    sonda = os.path.join(tmp, 'sonda.py')
    with open(sonda, 'w', encoding='utf-8') as f:
        f.write("import sys\nopen(sys.argv[1], 'w').write(repr((sys.stdout, sys.stderr)))\n")
    subprocess.run([pyw, sonda, sonda + '.txt'], env=env, creationflags=flags, timeout=30)
    with open(sonda + '.txt', encoding='utf-8') as f:
        chequear(f.read() == '(None, None)', 'pythonw arranca sin stdout ni stderr (como en el taller)')
    t0 = time.time()
    p = subprocess.Popen([pyw, os.path.join(PROG, 'web.py'), '--no-abrir'], env=env, cwd=RAIZ, creationflags=flags)
    try:
        ok = False
        while time.time() - t0 < 40 and p.poll() is None:
            try:
                ok = abrir(f'http://127.0.0.1:{PUERTO_B}/')[0] == 200
                break
            except OSError:
                time.sleep(0.3)
        if not chequear(ok, f'GET / responde 200 a los {time.time() - t0:.1f} s' + (f' (el proceso terminó con código {p.returncode})' if p.poll() is not None else '')):
            return
        st, data = abrir(f'http://127.0.0.1:{PUERTO_B}/api/trabajos')
        chequear(st == 200 and [e['id'] for e in json.loads(data)] == ['abcabcabcabc'], 'GET /api/trabajos: responde la web con el historial temporal')
        st, data = abrir(f'http://127.0.0.1:{PUERTO_B}/api/salir', 'POST', {'Origin': f'http://127.0.0.1:{PUERTO_B}'})
        chequear(st == 200 and json.loads(data).get('ok'), 'POST /api/salir')
        try:
            p.wait(15)
        except subprocess.TimeoutExpired:
            pass
        chequear(p.poll() == 0, f'el proceso terminó solo (código {p.poll()})')
        chequear(not puerto_ocupado(PUERTO_B), f'el puerto {PUERTO_B} quedó libre')
    finally:
        if p.poll() is None:
            p.kill(); p.wait(10)
            chequear(False, 'pythonw no terminó: se mató')


# ------------------------------------------------------------------ principal
t_inicio = time.time()
antes = foto_repo()
tmp = tempfile.mkdtemp(prefix='planocables_humo_')
try:
    print('A. web con test_client sobre copias temporales de los trabajos')
    t0 = time.time()
    try:
        parte_a(tmp)
    except Exception:
        import traceback
        traceback.print_exc()
        chequear(False, 'la parte A se cortó con una excepción')
    print(f'    (parte A: {time.time() - t0:.0f} s)')
    if '--sin-pythonw' not in sys.argv:
        t0 = time.time()
        try:
            parte_b(tmp)
        except Exception:
            import traceback
            traceback.print_exc()
            chequear(False, 'la parte B se cortó con una excepción')
        print(f'    (parte B: {time.time() - t0:.0f} s)')
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('C. nada cambió fuera de pruebas/ ni en los trabajos')
despues = foto_repo()
chequear(despues['git'] is not None and despues['git'] == antes['git'],
         'git status igual fuera de pruebas/' + ('' if despues['git'] == antes['git'] else f": {sorted(set(despues['git'] or []) ^ set(antes['git'] or []))}"))
chequear(despues['ocr'] == antes['ocr'], 'programa/ocr_cache.json sin cambios' + ('' if despues['ocr'] == antes['ocr'] else
         ' (hubo OCR en vivo; en el worktree se restaura con: git checkout -- programa/ocr_cache.json)'))
for d in PROTEGIDAS:
    a, b = antes['carpetas'][d], despues['carpetas'][d]
    cambios = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    chequear(not cambios, f'{os.path.relpath(d, RAIZ)} sin cambios ({len(a)} archivos)' + ('' if not cambios else f': {cambios[:8]}'))

print(f'\n({time.time() - t_inicio:.0f} s)')
if fallas:
    print(f'{len(fallas)} FALLA(S):')
    for f in fallas:
        print(' -', f.split('\n')[0])
    sys.exit(1)
print('TODO OK' + (' (golden creados)' if CREAR else ''))
