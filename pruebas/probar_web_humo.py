"""Prueba de humo de la web (etapa 0 del plan modular, bateria B). No escribe en los trabajos ni en el historial del
usuario: la web corre sobre copias en una carpeta temporal. Termina con error si algo falla.
uso: python pruebas/probar_web_humo.py [--crear] [--sin-pythonw]
  --crear:       (re)escribe los golden de pruebas/bases/web/ con lo que da el codigo de hoy
  --sin-pythonw: salta la parte B
  A. Flask test_client sobre copias del 75287 (ac0f0949510a) y del TPT: paginas, estado, resultado, imagen de la hoja,
     regenerar el instructivo (comparado con el golden y con la base de regresion), una marca 'hecho' de ida y vuelta
     (y que sobrevive a otro regenerar), vista previa de salidas a LI / LD, pestaña y API del proyector, topo.png y los
     estaticos (wpc.json, terminales.json y los .js / .css de las paginas). El producto (etapa 2) sale con el catalogo
     fijo pruebas/fixtures/productos.json, y GET /producto tiene que dar el mismo que el instructivo.
     Parametros de la WPC (etapa 3): GET y PUT /api/config/wpc sobre una COPIA temporal de wpc.json
     (PLANOCABLES_CONFIG_WPC): respaldo con fecha, version (409 si otro guardo), PUT invalido = 400 sin tocar nada, el
     orden de las claves se conserva; programa/web/wpc.json no se toca.
     Ruteo a mano de la estacion 8 (etapa E8-6, A5d): GET / PUT /e8/grupos y /e8/fondo.png sobre una COPIA del fixture
     pruebas/fixtures/recorridos_e8.json (PLANOCABLES_RECORRIDOS_E8); 409 con una version vieja; el recorrido dibujado
     se conserva al regenerar.
  B. Arranque como en el taller (pythonw, sin consola) en el puerto 8791 con un historial temporal; cierre con
     POST /api/salir y el proceso tiene que terminar.
  C. Nada cambio fuera de pruebas/ (git status), ni en '3 - Historial web' ni en pruebas/trabajos.
  D. node --check de todos los .js de programa/web (tambien los del nucleo)."""
import os, sys, io, json, re, time, shutil, socket, hashlib, tarfile, tempfile, subprocess, urllib.request
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROG = os.path.join(RAIZ, 'programa')
GOLD = os.path.join(RAIZ, 'pruebas', 'bases', 'web')
PRODUCTOS = os.path.join(RAIZ, 'pruebas', 'fixtures', 'productos.json')   # catalogo de productos de los golden
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
    resp = os.path.join(PROG, 'web', 'respaldos_wpc')       # (en .gitignore: git status no los ve)
    return dict(git=git_fuera_de_pruebas(), ocr=sha(os.path.join(PROG, 'ocr_cache.json')),
                carpetas={d: foto_carpeta(d) for d in PROTEGIDAS}, wpc=sha(os.path.join(PROG, 'web', 'wpc.json')),
                respaldos=sorted(os.listdir(resp)) if os.path.isdir(resp) else None)


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
    os.environ['PLANOCABLES_PRODUCTOS'] = PRODUCTOS     # catalogo fijo (el de programa/ lo cambia el taller); solo se lee
    # parametros de la WPC: una copia (el PUT de A9 la escribe y deja respaldos al lado, en la carpeta temporal)
    cwpc = os.path.join(tmp, 'config_wpc', 'wpc.json')
    os.makedirs(os.path.dirname(cwpc))
    shutil.copyfile(os.path.join(PROG, 'web', 'wpc.json'), cwpc)
    os.environ['PLANOCABLES_CONFIG_WPC'] = cwpc
    # ruteo a mano de la estacion 8 por producto (E8-6): una copia del fixture (el PUT de A5d la escribe)
    shutil.copyfile(os.path.join(RAIZ, 'pruebas', 'fixtures', 'recorridos_e8.json'), os.path.join(tmp, 'recorridos_e8.json'))
    os.environ['PLANOCABLES_RECORRIDOS_E8'] = os.path.join(tmp, 'recorridos_e8.json')
    sys.path.insert(0, PROG)
    import web
    chequear(os.path.normcase(web.CONFIG_WPC) == os.path.normcase(cwpc), f'la web usa la copia de wpc.json ({web.CONFIG_WPC})')
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
    chequear(re.search(rb'/static/nucleo/zip\.js\?v=\d+".*/static/nucleo/wpc_core\.js\?v=\d+".*/static/wpc\.js\?v=', r.data, re.S) is not None,
             'index.html carga el núcleo de la WPC (zip.js y wpc_core.js, versionados) antes de wpc.js')
    estaticos = sorted(set(re.findall(r'/static/(?:[\w.-]+/)*[\w.-]+\.(?:js|css)\?v=\d+', r.get_data(as_text=True))))
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
        # producto (etapa 2): el del instructivo y el de GET /producto son el mismo (catalogo fijo de las pruebas)
        pr = ins.get('producto') or {}
        r = get(u + '/producto')
        jp = (r.get_json() or {}).get('producto') or {} if r.status_code == 200 else {}
        chequear(pr.get('codigo') and (jp.get('codigo'), jp.get('funcional'), jp.get('topografico')) == (pr.get('codigo'), pr.get('funcional'), pr.get('topografico')),
                 f'producto {pr.get("codigo")} · funcional {(pr.get("funcional") or {}).get("numero")} rev {(pr.get("funcional") or {}).get("revision")}'
                 f' · topográfico {(pr.get("topografico") or {}).get("numero")} rev {(pr.get("topografico") or {}).get("revision")}; GET /producto da el mismo')
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
                         lado=l.get('lado'), color=l.get('color'), secc=l.get('secc'), **({'intrinseco': l['intrinseco']} if 'intrinseco' in l else {}),
                         **({'sale_hacia': l['sale_hacia']} if l.get('sale_hacia') else {}))      # (como salidas.js)
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

        print(f'A5b. {t}: estación 8, entrada a las laterales y bisagra (vista previa POST /e8/recorridos)')
        e8 = ins.get('estacion8') or {}
        lats = e8.get('laterales') or []
        rec_e8 = None
        punto_e8 = None         # (E8-5: el punto ajustado a mano en el visor de E8: clave de la vista, del cable y el punto)
        sale_e8 = lambda L: [l for p in L['pasos'] for l in p['lineas'] if 'marca_d' not in l]
        chequear(e8.get('recorridos') == {'preguntar': True, 'bisagra': None, 'vistas': {}} and all(L.get('clave_vista') for L in lats),
                 f"E8 la primera vez: el asistente pregunta ({e8.get('recorridos')}) y {len(lats)} laterales con su clave")
        r = post(u + '/e8/recorridos', json={'recorridos': {}})
        rl = (r.get_json() or {}).get('laterales') if r.status_code == 200 else None
        if chequear(isinstance(rl, list) and len(rl) == len(lats), f'POST /e8/recorridos sin elegir: {len(lats)} laterales ({r.status_code})'):
            cerca = lambda a, b: (a is None) == (b is None) and (a is None or len(a) == len(b) and all(
                abs(p[0] - q[0]) <= 0.5 and abs(p[1] - q[1]) <= 0.5 for p, q in zip(a, b)))
            n = sum(len(sale_e8(L)) for L in lats)
            par = sum(1 for x, L in zip(rl, lats) for y, l in zip(x['lineas'], sale_e8(L)) if y['clave'] == l['clave'] and cerca(y['ruta'], l.get('ruta')))
            chequear(par == n, f'sin elegir da las mismas rutas que el instructivo, a menos de 0,5 pt ({par}/{n})')
            golden['e8_recorridos'] = normalizar(rl, tmp)
            # una entrada elegida: la de la propuesta corrida un poco hacia afuera; los cables terminan ahi (o no llegan)
            L = next((L for L in lats if L.get('ductos') and sale_e8(L)), None)
            # (E8-4) la vista de la puerta: imagen, y sin elegir la vista previa da lo armado
            pu = e8.get('puerta')
            if chequear(isinstance(pu, dict) and pu.get('pasos'), f"E8 con la vista de la puerta ({(pu or {}).get('titulo')}, {(pu or {}).get('n')} cables)"):
                rp = get(u + '/e8/puerta.png')
                chequear(rp.status_code == 200 and rp.mimetype == 'image/png' and rp.data[:4] == b'\x89PNG', f'GET /e8/puerta.png ({len(rp.data) // 1024} KB)')
                xp = (r.get_json() or {}).get('puerta') or {}
                chequear([y['ruta'] for y in xp.get('lineas') or []] == [l['ruta'] for p in pu['pasos'] for l in p['lineas']],
                         f"POST /e8/recorridos sin elegir: la puerta da las mismas rutas que el instructivo ({len(xp.get('lineas') or [])})")
                golden['e8_puerta'] = normalizar(xp, tmp)
            if L:
                q = [round(L['entrada_propuesta'][0] + (-4 if L.get('hacia') == 'izq' else 4), 2), L['entrada_propuesta'][1]]
                rec_e8 = {'preguntar': False, 'bisagra': 'izq', 'vistas': {L['clave_vista']: {'entrada': [q], 'puerta': [], 'grupos': []}}}
                if isinstance(pu, dict):        # (la puerta: puntos de paso por debajo de sus aparatos, como el perfil de la foto 3)
                    yp = round(min(a['caja'][1] for a in pu['aparatos']) - 2 * pu['H'], 1)
                    dp = min(pu['ductos'], key=lambda d: abs(d['b'][2] - pu['box'][2]))
                    rec_e8['vistas']['PUERTA'] = {'entrada': [], 'puerta': [], 'grupos': [], 'paso': [
                        [round((dp['b'][0] + dp['b'][2]) / 2, 1), yp], [round(min(a['caja'][0] for a in pu['aparatos']) - pu['H'], 1), yp]]}
                r = post(u + '/e8/recorridos', json={'recorridos': rec_e8})
                x = next((x for x in ((r.get_json() or {}).get('laterales') or []) if x['clave_vista'] == L['clave_vista']), None)
                ok = x is not None and all(y.get('no_llega') or (y['ruta'] and abs(y['ruta'][-1][0] - q[0]) <= 0.6 and abs(y['ruta'][-1][1] - q[1]) <= 0.6)
                                           for y in x['lineas'] if y['sale'] == 'entrada')
                chequear(ok, f"POST /e8/recorridos con la entrada de la {L['nombre'].lower()} en {q}: los cables terminan ahí")
                if x is not None and L['lado'] == 'LI':
                    chequear((x.get('transito') or {}).get('n'), f"con la bisagra a la izquierda la {L['nombre'].lower()} muestra los que pasan hacia la puerta ({(x.get('transito') or {}).get('n')})")
                if isinstance(pu, dict):
                    xp = (r.get_json() or {}).get('puerta') or {}
                    pasan = sum(1 for y in xp.get('lineas') or [] if any(abs(p[1] - yp) <= 0.15 for p in y['ruta']))
                    chequear(pasan == len(xp.get('lineas') or []) and pasan and not xp.get('no_llegan'),
                             f"POST /e8/recorridos con un punto de paso en la puerta a la altura {yp}: {pasan} de {len(xp.get('lineas') or [])} cables pasan por ahí")
                golden['e8_recorridos_elegidos'] = normalizar((r.get_json() or {}).get('laterales'), tmp)
                ins5 = get(u + '/instructivo').get_json() or {}
                ins5['estacion8']['recorridos'] = rec_e8        # (como la pestaña: se guarda con el instructivo)
                # (E8-5) el punto de un borne de la lateral ajustado a mano con 📍: vista previa POST /e8/punto y se guarda en
                # bornes_usuario (como E6); al regenerar (A7) manda
                il = lats.index(L)
                lp = next((l for p in L['pasos'] for l in p['lineas'] if l.get('ruta') and not l.get('empalme')), None)
                if chequear(lp is not None, f"A5c. {L['nombre']}: un cable para ajustar el punto de su borne"):
                    pp_ = [round(lp['marca_o'][0] + 1.5, 2), lp['marca_o'][1]]
                    r = post(u + '/e8/punto', json={'vista': il, 'clave': lp['clave'], 'punta': 'o', 'xy': pp_, 'recorridos': rec_e8,
                                                    'linea': {k: lp.get(k) for k in ('marca_o', 'marca_d', 'lado', 'lado_d')}})
                    j = r.get_json() or {}
                    chequear(r.status_code == 200 and j.get('marca') == pp_ and j.get('ruta') and abs(j['ruta'][0][0] - pp_[0]) <= 0.06
                             and abs(j['ruta'][0][1] - pp_[1]) <= 0.06 and j.get('largo_mm'),
                             f"POST /e8/punto: {lp['num']} {lp['origen']} con el punto en {pp_}: el recorrido sale de ahí ({j.get('largo_mm')} mm)")
                    golden['e8_punto'] = normalizar(j, tmp)
                    ins5['bornes_usuario'] = dict(ins5.get('bornes_usuario') or {}, **{f"{lp['origen']}#{lp['num']}": pp_})
                    punto_e8 = (L['clave_vista'], lp['clave'], pp_)
                chequear(post(u + '/e8/punto', json={'vista': il, 'clave': 'no-existe', 'punta': 'o', 'xy': [1, 2]}).status_code == 404,
                         'POST /e8/punto de un cable que no está: 404')
                chequear(post(u + '/e8/punto', json={'vista': il, 'clave': 'x', 'punta': 'z', 'xy': [1, 2]}).status_code == 400, 'POST /e8/punto inválido: 400')
                chequear(put(u + '/instructivo', json=ins5).status_code == 200, 'PUT /instructivo con la entrada y la bisagra de E8 (y el punto ajustado)')
        chequear(post(u + '/e8/recorridos', json={'recorridos': 'no'}).status_code == 400, 'POST /e8/recorridos inválido: 400')
        chequear(post('/api/trabajo/0123456789ab/e8/recorridos', json={'recorridos': {}}).status_code == 404, 'POST /e8/recorridos de un trabajo que no existe: 404')

        print(f'A5d. {t}: estación 8, ruteo a mano por grupos (GET / PUT /e8/grupos, vista del fondo)')
        mano_e8 = None          # (el grupo y el recorrido dibujado: se conservan al regenerar)
        r = get(u + '/e8/grupos')
        Rm = (r.get_json() or {}).get('ruteo_mano') or {}
        gs = [g for g in Rm.get('grupos') or [] if g.get('n')]
        if chequear(r.status_code == 200 and gs and Rm.get('por_producto') and Rm.get('clave_producto'),
                    f"GET /e8/grupos: {len(gs)} grupos ({', '.join(g['id'] for g in gs)}), por producto {Rm.get('clave_producto')}"):
            golden['e8_grupos'] = normalizar({k: Rm.get(k) for k in ('categorias', 'vistas', 'auto', 'auto_info', 'grupos', 'miembro', 'clave_producto')}, tmp)
            rf = get(u + '/e8/fondo.png')
            chequear(rf.status_code == 200 and rf.mimetype == 'image/png' and rf.data[:4] == b'\x89PNG', f'GET /e8/fondo.png ({len(rf.data) // 1024} KB)')
            g0 = gs[0]
            man = json.loads(json.dumps(Rm.get('manual') or {}))
            man.setdefault('grupos', {})[g0['id']] = {'tramos': [{'vista': 'FONDO', 'puntos': [[tp['region'][0] + 20, tp['region'][1] + 20], [tp['region'][0] + 60, tp['region'][1] + 20]]}]}
            r = put(u + '/e8/grupos', json={'manual': man, 'version': Rm.get('version_almacen')})
            R2 = (r.get_json() or {}).get('ruteo_mano') or {}
            chequear(r.status_code == 200 and any(g['id'] == g0['id'] and g['dibujado'] for g in R2.get('grupos') or [])
                     and R2.get('version_almacen') == (Rm.get('version_almacen') or 0) + 1,
                     f"PUT /e8/grupos: el recorrido de «{g0['nombre']}» queda dibujado para el producto (versión {R2.get('version_almacen')})")
            with open(os.environ['PLANOCABLES_RECORRIDOS_E8'], encoding='utf-8') as f:
                chequear(Rm['clave_producto'] in (json.load(f).get('productos') or {}), 'se guardó en el archivo de recorridos por producto (la copia de las pruebas)')
            chequear(put(u + '/e8/grupos', json={'manual': man, 'version': Rm.get('version_almacen')}).status_code == 409,
                     'PUT /e8/grupos con la versión vieja: 409')
            chequear(put(u + '/e8/grupos', json={'manual': 'no'}).status_code == 400, 'PUT /e8/grupos inválido: 400')
            mano_e8 = g0['id']

        print(f'A6. {t}: proyector y topo.png')
        r = get(f'/proyector/{jid}')
        chequear(r.status_code == 200 and b'proyector.js?v=' in r.data, 'GET /proyector/<id> sirve la pestaña')
        estaticos += re.findall(r'/static/(?:[\w.-]+/)*[\w.-]+\.(?:js|css)\?v=\d+', r.get_data(as_text=True))
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
            if rec_e8:
                chequear((ins4.get('estacion8') or {}).get('recorridos') == rec_e8, 'se conservan la entrada a la lateral y la bisagra de E8')
            if mano_e8:             # (E8-6) el recorrido dibujado a mano (por producto) se conserva
                R4 = (ins4.get('estacion8') or {}).get('ruteo_mano') or {}
                chequear(any(g['id'] == mano_e8 and g['dibujado'] for g in R4.get('grupos') or [])
                         and any(l.get('grupo_mano') == mano_e8 for L in (ins4.get('estacion8') or {}).get('laterales') or [] for p in L['pasos'] for l in p['lineas'])
                         | any(x.get('grupo_mano') == mano_e8 for g in (ins4.get('estacion8') or {}).get('afuera') or [] for x in g['cables']),
                         f'se conserva el recorrido dibujado a mano de «{mano_e8}» (por producto) y las líneas siguen marcadas con su grupo')
            if punto_e8:            # (E8-5) el punto ajustado a mano en la lateral manda al regenerar y E6 no cambia
                vk, ck, pp_ = punto_e8
                L4 = next((L for L in (ins4.get('estacion8') or {}).get('laterales') or [] if L.get('clave_vista') == vk), {})
                l4p = next((l for p in L4.get('pasos') or [] for l in p['lineas'] if l['clave'] == ck), None)
                chequear(l4p and l4p.get('exacto_o') and l4p.get('conf_o') == 'usuario' and l4p['marca_o'][:2] == pp_ and l4p.get('ruta')
                         and abs(l4p['ruta'][0][0] - pp_[0]) <= 0.06,
                         f"el punto ajustado a mano en la {L4.get('nombre', '?').lower()} ({(l4p or {}).get('origen')} #{(l4p or {}).get('num')}) manda al regenerar")
                chequear([(l.get('marca_o'), l.get('marca_d')) for l in lineas_de(ins4)] == [(l.get('marca_o'), l.get('marca_d')) for l in lineas_de(ins3)],
                         'y los puntos de E6 no cambian')
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
    parte_a9(get, put, cwpc)


def parte_a9(get, put, cwpc):
    """GET y PUT /api/config/wpc sobre la copia temporal (cwpc). El wpc.json del repo no se toca"""
    print('A9. parámetros de la WPC: GET y PUT /api/config/wpc (sobre una copia)')
    repo = os.path.join(PROG, 'web', 'wpc.json')
    sha_repo = sha(repo)
    respaldos = os.path.join(os.path.dirname(cwpc), 'respaldos_wpc')
    lista = lambda: sorted(os.listdir(respaldos)) if os.path.isdir(respaldos) else []
    with open(cwpc, 'rb') as f:
        orig = f.read()
    r = get('/api/config/wpc')
    cfg = json.loads(r.data.decode('utf-8')) if r.status_code == 200 else {}
    ver = r.headers.get('X-Version')
    chequear(r.status_code == 200 and r.data == orig and ver and isinstance(cfg.get('parametros'), list) and isinstance(cfg.get('productos'), dict),
             f'GET /api/config/wpc: el archivo tal cual, con X-Version ({ver}) y {len(cfg.get("parametros") or [])} parámetros')
    chequear(not web_validar(cfg), f'la configuración de hoy es válida ({web_validar(cfg)[:3]})')
    # un cambio de un producto, con la version: 200, respaldo del anterior y el orden de las claves se conserva
    nuevo = json.loads(orig.decode('utf-8'))
    nuevo['productos'] = dict(nuevo.get('productos') or {}, **{'75286-1': {'acometida': 80, 'fuera': {'seccion_desde': 25}}})
    # (como el navegador: el JSON en el orden de las claves; json= de test_client las ordena)
    r = put('/api/config/wpc', data=json.dumps(nuevo, ensure_ascii=False).encode('utf-8'), content_type='application/json', headers={'X-Version': ver})
    j = json.loads(r.data.decode('utf-8')) if r.status_code == 200 else (r.get_json() or {})
    with open(cwpc, encoding='utf-8') as f:
        disco = json.load(f)
    chequear(r.status_code == 200 and j.get('ok') and disco == nuevo and list(disco) == list(nuevo) and list(j.get('config') or {}) == list(nuevo),
             f'PUT /api/config/wpc (producto 75286-1): guardado, mismo orden de claves ({r.status_code} {j.get("error") or ""})')
    rs = lista()
    chequear(len(rs) == 1 and rs[0] == j.get('respaldo') and re.fullmatch(r'wpc_\d{4}-\d\d-\d\d_\d{6}_\d{6}\.json', rs[0] or '')
             and open(os.path.join(respaldos, rs[0]), 'rb').read() == orig, f'respaldo con fecha del anterior en respaldos_wpc/ ({rs})')
    r2 = get('/api/config/wpc')
    chequear(r2.headers.get('X-Version') == j.get('version') != ver, 'la versión nueva es la del archivo guardado')
    # con la version vieja: 409 (otro guardo mientras tanto) y no se toca nada
    with open(cwpc, 'rb') as f:
        antes = f.read()
    r = put('/api/config/wpc', json=nuevo, headers={'X-Version': ver})
    chequear(r.status_code == 409 and open(cwpc, 'rb').read() == antes and len(lista()) == 1, f'PUT con una versión vieja: 409 ({r.status_code}), sin tocar el archivo')
    # invalidos: 400, sin tocar el archivo ni dejar respaldo
    for nombre, cuerpo in [('un largo con texto', dict(nuevo, margen_bandeja='mucho')),
                           ('un producto con un número inválido', dict(nuevo, productos={'75286-1': {'redondeo': -5}})),
                           ('una regla de reemplazo incompleta', dict(nuevo, reemplazos=[{'de': {'color': 'Negro'}}])),
                           ('productos que no es un objeto', dict(nuevo, productos=[])),
                           ('un sí / no con texto', dict(nuevo, pendientes='si')),
                           ('una lista', [1, 2])]:
        r = put('/api/config/wpc', json=cuerpo)
        chequear(r.status_code == 400 and (r.get_json() or {}).get('error') and open(cwpc, 'rb').read() == antes and len(lista()) == 1,
                 f'PUT inválido ({nombre}): 400 «{(r.get_json() or {}).get("error")}» {((r.get_json() or {}).get("errores") or [""])[0]}')
    # sin 'parametros' en el cuerpo se conservan los del archivo
    sin = {k: v for k, v in nuevo.items() if k != 'parametros'}
    r = put('/api/config/wpc', json=sin)
    with open(cwpc, encoding='utf-8') as f:
        disco = json.load(f)
    chequear(r.status_code == 200 and disco.get('parametros') == nuevo['parametros'] and len(lista()) == 2, 'PUT sin «parametros»: se conservan los del archivo')
    chequear(put('/api/config/wpc', json=nuevo, headers={'Origin': 'http://evil.example'}).status_code == 403, 'PUT con otro Origin: 403')
    chequear(sha(repo) == sha_repo, 'programa/web/wpc.json sin tocar')


def web_validar(cfg):
    import web
    return web.validar_config_wpc(cfg)


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
chequear(despues['wpc'] == antes['wpc'] and despues['respaldos'] == antes['respaldos'],
         'programa/web/wpc.json sin tocar y ningún respaldo nuevo en programa/web/respaldos_wpc/')

print('D. node --check de los .js de programa/web')
jss = sorted(os.path.join(r, f) for r, _, fs in os.walk(os.path.join(PROG, 'web')) for f in fs if f.endswith('.js'))
malos = []
for js in jss:
    try:
        p = subprocess.run(['node', '--check', js], capture_output=True, text=True, encoding='utf-8', timeout=60)
        if p.returncode:
            malos.append(f'{os.path.relpath(js, PROG)}: {p.stderr.strip().splitlines()[-1] if p.stderr.strip() else p.returncode}')
    except OSError as e:
        malos.append(f'no se pudo correr node ({e})')
        break
chequear(jss and not malos, f'node --check de {len(jss)} archivos .js ({", ".join(os.path.relpath(j, os.path.join(PROG, "web")) for j in jss)})'
         + ('' if not malos else ': ' + ' · '.join(malos)))

print(f'\n({time.time() - t_inicio:.0f} s)')
if fallas:
    print(f'{len(fallas)} FALLA(S):')
    for f in fallas:
        print(' -', f.split('\n')[0])
    sys.exit(1)
print('TODO OK' + (' (golden creados)' if CREAR else ''))
