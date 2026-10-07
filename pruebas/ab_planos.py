"""Regresion A/B sobre TODOS los planos de '1 - Planos' (etapa 0 del plan modular, batería B).
Para cada par funcional + topografico arma, con el mismo camino que la web y SIN archivos manuales del trabajo:
  core.process (listado, normalizado como resultado.json) -> topo.layout (con ida y vuelta por JSON, como layout.json)
  -> mapeo automatico de bornes (bornes.aplicar_al_layout, o eplan.aplicar_puntos en EPLAN) -> instructivo.build
y guarda un JSON compacto por plano (<salida>/<clave>.json): cables, lineas E6, pendientes, sueltos, otra estacion,
extremos, resumen del layout y del mapeo. Lo que cambia solo (tiempos, OCR en vivo) va en 'meta' y no se compara.
Desde la etapa 2 el listado trae tambien 'producto' (el de web.result_json: codigo, plano y revision), entero y fuera
de la huella, con el catalogo fijo pruebas/fixtures/productos.json.
uso:
  python pruebas/ab_planos.py <dir_salida> [--programa <carpeta programa>] [--solo clave1,clave2] [-j N]
                              [--memoria-ocr <ocr_cache.json>] [--semilla 0|aleatoria]
  python pruebas/ab_planos.py --comparar <dirA> <dirB> [--max 25]
  python pruebas/ab_planos.py --listar          (solo la clasificacion de los PDF)
  --programa:    otra copia de programa/ (ej. un 'git worktree' de un commit viejo), como PLANOCABLES_PROGRAMA en
                 probar_ronda3.py. Por defecto, PLANOCABLES_PROGRAMA o el programa/ de este repo.
  --memoria-ocr: memoria de OCR a usar (por defecto la de la carpeta del programa). Siempre en SOLO LECTURA: la corrida
                 nunca reescribe ocr_cache.json; los renglones que no estan en la memoria se leen con OCR en vivo y se
                 cuentan en meta.ocr_en_vivo (si hubo, se avisa: el resultado depende del motor de OCR).
  -j N:          planos en paralelo (cada plano corre en su propio proceso). Con -j 1 los tiempos son los reales.
  --semilla:     PYTHONHASHSEED de cada proceso (por defecto 0, para que A y B sean comparables).
Base de este repo: pruebas/bases/ab/ (python pruebas/ab_planos.py <tmp> ; python pruebas/ab_planos.py --comparar
pruebas/bases/ab <tmp>). Sale con 0 si todo anduvo (o si no hay diferencias, con --comparar) y 1 si no."""
import os, sys, re, json, time, glob, hashlib, subprocess, tempfile, argparse, inspect, numbers, difflib, collections

sys.dont_write_bytecode = True          # no deja __pycache__ dentro de programa/
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANOS = os.path.join(RAIZ, '1 - Planos')
PRODUCTOS = os.path.join(RAIZ, 'pruebas', 'fixtures', 'productos.json')     # catalogo de productos (solo se lee)
ESTE = os.path.abspath(__file__)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# --------------------------------------------------------------------------- clasificacion de los PDF
# pares que no se deducen solos por la carpeta (rutas relativas a '1 - Planos', con '/'): {funcional: topografico}.
# Hoy todos se deducen (un funcional y un topografico por carpeta; EPLAN = el mismo PDF).
PARES = {}
RX_FUNCIONAL = re.compile(r'functional|funcional|diagrama\s+el[eé]ctrico', re.I)
RX_TOPO = re.compile(r'structure\s+and\s+arrangement|topogr[aá]fico|constructivo', re.I)
RX_GABINETE = re.compile(r'envolvente|gabinete', re.I)
TIPOS = {'funcional': 'funcional (AutoCAD / ZWCAD, letras SHX)', 'topografico': 'topografico (AutoCAD / ZWCAD)',
         'eplan': 'EPLAN (funcional y bandejas en el mismo PDF)', 'orden_sap': 'orden de montaje de SAP (se saltea)',
         'bom_sap': 'lista de materiales de SAP (se saltea)', 'gabinete': 'plano mecanico del gabinete, sin cables (se saltea)',
         'otro': 'no reconocido (se saltea)'}


def rel(p):
    return os.path.relpath(p, RAIZ).replace('\\', '/')


def ruta_corta(p):
    """relativa a la raiz del repo si esta adentro (las bases no llevan rutas de esta PC)"""
    p = os.path.abspath(p)
    try:
        r = os.path.relpath(p, RAIZ)
    except ValueError:                  # otra unidad
        return p
    return p if r.startswith('..') else r.replace('\\', '/')


def sha_archivo(p):
    h = hashlib.sha1()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]


def texto_portada(p):
    """titulo y texto real de la primera hoja (los dibujos de ZWCAD no tienen texto: letras SHX en trazos)"""
    import pypdf
    r = pypdf.PdfReader(p)
    if r.is_encrypted:
        r.decrypt('')
    titulo = str((r.metadata or {}).get('/Title') or '')
    try:
        txt = r.pages[0].extract_text() or ''
    except Exception:
        txt = ''
    return titulo, txt, len(r.pages)


def clave_de(nombre):
    """'75287 DIAGRAMA ELECTRICO mSafe2AC - REV.6.pdf' -> '75287_rev6'; '5000…072715-Rev4-…' -> '72715_rev4'"""
    m = re.search(r'(\d{5})(?=\D|$)', nombre)
    doc = m.group(1) if m else re.sub(r'\W+', '_', os.path.splitext(nombre)[0])[:30]
    r = re.search(r'rev\.?\s*-?\s*([0-9][0-9A-Z]*)', nombre, re.I)
    return f'{doc}_rev{r.group(1)}' if r else doc


def clasificar():
    """-> (archivos, planos). archivos: [{archivo, sha, tipo, ...}]; planos: [{clave, funcional, topografico, eplan, ...}]"""
    archivos, vistos = [], {}
    for p in sorted(glob.glob(os.path.join(PLANOS, '**', '*.pdf'), recursive=True)):
        sha = sha_archivo(p)
        a = dict(archivo=rel(p), sha=sha)
        if sha in vistos:               # el mismo PDF en dos carpetas (PAE rev 1, gabinete 66336): se procesa una vez
            a.update(tipo='copia', igual_a=vistos[sha]['archivo'], tipo_original=vistos[sha]['tipo'])
            archivos.append(a)
            continue
        titulo, txt, n = texto_portada(p)
        nombre = os.path.basename(p) + ' ' + titulo
        if re.search(r'ORDEN DE MONTAJE', txt, re.I):         # (la orden tambien trae su lista de materiales)
            tipo = 'orden_sap'
        elif re.search(r'Lista de Materiales', txt, re.I):
            tipo = 'bom_sap'
        elif txt.strip():               # texto real que no es de SAP: EPLAN (lista de conexiones y bandejas en el PDF)
            tipo = 'eplan'
        elif RX_GABINETE.search(nombre):
            tipo = 'gabinete'
        elif RX_FUNCIONAL.search(nombre):
            tipo = 'funcional'
        elif RX_TOPO.search(nombre):
            tipo = 'topografico'
        else:
            tipo = 'otro'
        a.update(tipo=tipo, titulo=titulo, hojas=n)
        archivos.append(a); vistos[sha] = a
    planos = []
    por_carpeta = collections.defaultdict(list)
    for a in archivos:
        if a['tipo'] in ('funcional', 'topografico'):
            por_carpeta[os.path.dirname(a['archivo'])].append(a)
    explicitos = {'1 - Planos/' + f: '1 - Planos/' + t for f, t in PARES.items()}
    for a in archivos:
        if a['tipo'] == 'eplan':
            planos.append(dict(funcional=a['archivo'], topografico=a['archivo'], eplan=True))
        elif a['tipo'] == 'funcional':
            if a['archivo'] in explicitos:
                topo = explicitos[a['archivo']]
            else:
                ts = [x['archivo'] for x in por_carpeta[os.path.dirname(a['archivo'])] if x['tipo'] == 'topografico']
                fs = [x for x in por_carpeta[os.path.dirname(a['archivo'])] if x['tipo'] == 'funcional']
                topo = ts[0] if len(ts) == 1 and len(fs) == 1 else None    # ambiguo: va en PARES
            planos.append(dict(funcional=a['archivo'], topografico=topo, eplan=False))
    for pl in planos:
        pl['clave'] = clave_de(os.path.basename(pl['funcional']))
        pl['copias'] = [a['archivo'] for a in archivos if a.get('igual_a') in (pl['funcional'], pl['topografico'])]
    claves = collections.Counter(pl['clave'] for pl in planos)
    if any(n > 1 for n in claves.values()):
        raise SystemExit(f'FALLA: dos planos con la misma clave: {[k for k, n in claves.items() if n > 1]}')
    usados = {pl['topografico'] for pl in planos}
    for a in archivos:
        if a['tipo'] == 'topografico' and a['archivo'] not in usados:
            a['aviso'] = 'topografico sin funcional en su carpeta (agregarlo en PARES)'
    return archivos, planos


# --------------------------------------------------------------------------- normalizacion
def redondear(o, nd=2):
    if isinstance(o, bool) or o is None or isinstance(o, (str, int)):
        return o
    if isinstance(o, numbers.Real):
        v = round(float(o), nd)
        return 0.0 if v == 0 else v
    if isinstance(o, dict):
        return {str(k): redondear(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [redondear(v, nd) for v in o]
    if isinstance(o, (set, frozenset)):
        return sorted((redondear(v, nd) for v in o), key=lambda x: json.dumps(x, sort_keys=True, default=str))
    return str(o)


def huella(o):
    return hashlib.sha1(json.dumps(redondear(o), sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')).hexdigest()[:16]


def pt(v):
    """punto [x, y, ...] -> [x, y] con un decimal (o None)"""
    if not v:
        return None
    try:
        return [round(float(v[0]), 1), round(float(v[1]), 1)]
    except (TypeError, ValueError, IndexError):
        return str(v)


def result_json_local(res):
    """copia de web.result_json (por si la copia del programa no tiene web.py), sin nombre, fecha ni tiempos"""
    from core import sheet_name
    pages = [dict(index=p['index'], sheet=sheet_name(p), title=p['meta'].get('title', ''), w=p['w'] - p.get('x0', 0), h=p['h'] - p.get('y0', 0),
                  x0=p.get('x0', 0), y0=p.get('y0', 0),
                  cables=sum(1 for n in p['nums'] if n['chain'] is not None)) for p in res.pages]
    clean = lambda d: {k: v for k, v in d.items() if k not in ('chain', 'etiquetas', 'via')}
    return dict(nota=res.default[2] if res.default else None, paginas=pages,
                cables=res.cables, detalle=[clean(d) for d in res.detail], revisar=res.review,
                rutas={str(p['index']): p.get('routes', {}) for p in res.pages if p.get('routes')},
                sin_numero=getattr(res, 'unnumbered', []))


VOLATILES_LISTADO = ('nombre', 'fecha', 'segundos', 'opciones', 'stats')


def resumen_listado(res, meta):
    try:
        import web                      # el mismo resultado.json que escribe la web
        rj = web.result_json(res, '', {})
        meta['resultado_json'] = 'web.result_json'
    except Exception as e:              # noqa: BLE001
        rj = result_json_local(res)
        meta['resultado_json'] = f'copia local ({type(e).__name__})'
    rj = {k: v for k, v in rj.items() if k not in VOLATILES_LISTADO}
    rj = json.loads(json.dumps(rj, ensure_ascii=False, default=str))      # como resultado.json
    # producto (codigo, plano y revision; desde la etapa 2): va aparte, entero, al final, y la huella del listado sigue
    # siendo la de siempre (una copia vieja del programa no lo trae: no aparece la clave)
    producto = rj.pop('producto', None)
    g = lambda d, *ks: [d.get(k) for k in ks]
    return dict(
        huella=huella(rj), huella_rutas=huella(rj.get('rutas')), nota=rj.get('nota'),
        paginas=[g(p, 'index', 'sheet', 'title', 'cables') for p in rj.get('paginas') or []],
        n_cables=len({c['num'] for c in rj.get('cables') or []}),
        cables=[g(c, 'num', 'color', 'sec', 'puntas', 'n', 'hojas', 'ubic', 'refs', 'obs') for c in rj.get('cables') or []],
        detalle=[g(d, 'num', 'pag', 'zona', 'color', 'sec', 'puntas', 'origen', 'texto', 'src') for d in rj.get('detalle') or []],
        revisar=[g(r, 'tipo', 'texto', 'hoja', 'zona') for r in rj.get('revisar') or []],
        sin_numero=[g(s, 'texto', 'hoja', 'zona', 'color', 'sec') for s in rj.get('sin_numero') or []],
        **({'producto': producto} if producto is not None else {}))


def resumen_layout(lay):
    lay = lay or {}
    comp = lay.get('comp') or {}
    otras = {k: v for k, v in lay.items() if k not in ('comp', 'ductos', 'filas', 'vistas', 'region', 'escala', 'pag', 'size',
                                                       'version_lector', 'eplan', 'bandeja')}
    e = lay.get('eplan') if isinstance(lay.get('eplan'), dict) else {}
    return dict(
        huella=huella(lay), version_lector=lay.get('version_lector'), pag=lay.get('pag'), size=redondear(lay.get('size'), 1),
        region=redondear(lay.get('region'), 1), escala=redondear(lay.get('escala'), 4), bandeja=lay.get('bandeja'),
        rieles=redondear(lay.get('filas'), 1), vistas=redondear(lay.get('vistas'), 1),
        canaletas=[redondear(d, 1) for d in lay.get('ductos') or []],
        componentes={t: [c.get('ubic'), c.get('fila'), redondear(c.get('x'), 1), redondear(c.get('y'), 1), c.get('leido')]
                     for t, c in sorted(comp.items())},
        eplan=dict(documento=e.get('documento'), revision=e.get('revision'), claves=sorted(e), huella=huella(e)) if e else None,
        otras_claves={k: (redondear(v, 3) if len(json.dumps(v, default=str)) <= 80 else 'huella ' + huella(v)) for k, v in sorted(otras.items())})


def texto_linea(l):
    return f"{l.get('num')}: {l.get('cable')} {l.get('origen')} → {l.get('destino')}"


def resumen_instructivo(ins, lay, res):
    import instructivo as I
    # pasos = [titulo, cuantas lineas]: las lineas van en orden, sin el numero de paso (asi un paso de menos no cambia
    # todas las lineas que siguen en la comparacion)
    lineas, pasos = [], []
    for p in ins.get('pasos') or []:
        pasos.append([p.get('titulo'), len(p.get('lineas') or [])])
        for l in p.get('lineas') or []:
            lineas.append(dict(t=texto_linea(l), mm=l.get('largo_mm'), o=pt(l.get('marca_o')), d=pt(l.get('marca_d')),
                               ex=('o' if l.get('exacto_o') else '') + ('d' if l.get('exacto_d') else ''),
                               conf=[l.get('conf_o'), l.get('conf_d')], puente=bool(l.get('puente')), intr=l.get('intrinseco'),
                               sal=l.get('salida'), ruta=huella(l.get('ruta'))))
    otra = [dict(t=texto_linea(l), est=l.get('estacion'), mm=l.get('largo_mm'), o=pt(l.get('marca_o')), d=pt(l.get('marca_d')))
            for l in ins.get('otra_estacion') or []]
    pend = [f"{x.get('num')}: {x.get('cable')} {x.get('a')} ↔ {x.get('b')}" for x in ins.get('pendientes') or []]
    cs = I.conductors(res)
    extremos = {n: sorted(I.fmt_terminal(c['nodes'][k]) for k in c['bornes']) for n, c in cs.items()}
    return dict(
        n=dict(lineas=len(lineas), con_ruta=sum(1 for l in lineas if l['mm']), exactas=sum(len(l['ex']) for l in lineas),
               pendientes=len(pend), otra_estacion=len(otra), sueltos=len(ins.get('sueltos') or [])),
        pasos=pasos, lineas=lineas, pendientes=pend, sueltos=redondear(ins.get('sueltos') or [], 1), otra_estacion=otra,
        extremos=dict(sorted(extremos.items(), key=lambda kv: I.natk(kv[0]) if hasattr(I, 'natk') else kv[0])),
        alternativas=redondear(ins.get('alternativas') or [], 1), lado_fisico=redondear(ins.get('lado_fisico') or [], 1),
        quitados=redondear(ins.get('quitados') or [], 1), accesorios=redondear(ins.get('accesorios') or [], 1),
        topo=huella(ins.get('topo')), componentes=huella(ins.get('componentes')))


def resumen_mapeo(mapeo, lay):
    m = dict(mapeo or {})
    for k in ('segundos', 'de_cache', 'segundos_cache', 'detalle'):
        m.pop(k, None)
    m['bornes'] = len(lay.get('bornes') or {})
    m['huella_bornes'] = huella(lay.get('bornes') or {})
    m['renombrar'] = redondear(lay.get('renombrar') or {})
    m['renombrar_auto'] = redondear(lay.get('renombrar_auto') or {})
    return redondear(m, 3)


def sin_rutas_locales(o, reemplazos):
    """las rutas de esta PC (programa, raiz, temporales) no entran en la comparacion"""
    if isinstance(o, str):
        for a, b in reemplazos:
            o = o.replace(a, b)
        return o
    if isinstance(o, dict):
        return {k: sin_rutas_locales(v, reemplazos) for k, v in o.items()}
    if isinstance(o, list):
        return [sin_rutas_locales(v, reemplazos) for v in o]
    return o


# --------------------------------------------------------------------------- un plano (en su propio proceso)
def llamar(f, *args, **kw):
    """llama con los argumentos que la funcion acepte (copias viejas del programa)"""
    try:
        ps = inspect.signature(f).parameters
        if not any(p.kind == p.VAR_KEYWORD for p in ps.values()):
            kw = {k: v for k, v in kw.items() if k in ps}
    except (TypeError, ValueError):
        pass
    return f(*args, **kw)


def correr_plano(clave, funcional, topografico, salida, prog, memoria_ocr=None):
    sys.path.insert(0, prog)
    tmp = tempfile.mkdtemp(prefix='ab_planos_')
    os.environ.setdefault('PLANOCABLES_HISTORIAL', os.path.join(tmp, 'historial'))     # (por si se importa web.py)
    # producto del listado (web.result_json, desde la etapa 2) con el catalogo fijo de las pruebas: el de programa/ lo
    # cambia el taller cuando confirma un producto
    os.environ['PLANOCABLES_PRODUCTOS'] = PRODUCTOS
    fpath = os.path.join(RAIZ, funcional)
    tpath = os.path.join(RAIZ, topografico) if topografico else None
    out = dict(plano=clave, archivos=dict(funcional=funcional, topografico=topografico, sha_funcional=sha_archivo(fpath),
                                          sha_topografico=sha_archivo(tpath) if tpath else None))
    meta = dict(programa=ruta_corta(prog), python=sys.version.split()[0], semilla=os.environ.get('PYTHONHASHSEED'), segundos={})
    errores = {}
    # memoria de OCR en solo lectura y cuenta de los renglones leidos con OCR en vivo
    vivo = collections.Counter()
    try:
        import textdec
        D = textdec.Decoder
        if hasattr(D, 'ocr_line') and hasattr(D, 'line_key'):
            orig = D.ocr_line

            def ocr_line(self, line, H):
                vivo['en_vivo' if self.line_key(line, H) not in getattr(self, 'cache', {}) else 'memoria'] += 1
                return orig(self, line, H)
            D.ocr_line = ocr_line
        if hasattr(D, 'save_cache'):
            D.save_cache = lambda self: None
        if memoria_ocr:
            ini = D.__init__

            def __init__(self, *a, **k):
                ini(self, *a, **k)
                with open(memoria_ocr, encoding='utf-8') as f:
                    self.cache = json.load(f)
            D.__init__ = __init__
    except Exception as e:              # noqa: BLE001
        errores['ocr'] = f'{type(e).__name__}: {e}'
    nada = lambda *a, **k: None
    t0 = time.time()
    res = lay = ins = None
    # 1. listado del funcional
    try:
        from core import process
        res = process(fpath, log=nada)
        out['eplan'] = bool(getattr(res, 'eplan', False))
        out['listado'] = resumen_listado(res, meta)
    except Exception as e:              # noqa: BLE001
        import traceback
        errores['listado'] = f'{type(e).__name__}: {e}'; meta['traceback_listado'] = traceback.format_exc()
    meta['segundos']['listado'] = round(time.time() - t0, 1)
    # 2. layout del topografico (como layout.json: ida y vuelta por JSON)
    if res is not None and tpath:
        t1 = time.time()
        try:
            import instructivo as I, topo
            lay = topo.layout(tpath, I.known_tags(res), log=nada)
            lay = json.loads(json.dumps(lay, ensure_ascii=False))
            out['layout'] = resumen_layout(lay)
        except Exception as e:          # noqa: BLE001
            import traceback
            errores['layout'] = f'{type(e).__name__}: {e}'; meta['traceback_layout'] = traceback.format_exc(); lay = None
        meta['segundos']['layout'] = round(time.time() - t1, 1)
    # 3. mapeo automatico de bornes (trabajo vacio: sin bornes.json, correcciones.json ni marcas del usuario)
    if lay is not None:
        t2 = time.time()
        trabajo = os.path.join(tmp, 'trabajo'); os.makedirs(trabajo, exist_ok=True)
        lay['bornes_usuario'] = {}
        try:
            if getattr(res, 'eplan', False) and lay.get('eplan'):
                import eplan
                mapeo = eplan.aplicar_puntos(res, lay, trabajo)
            else:
                import bornes as mapeo_bornes
                mapeo = llamar(mapeo_bornes.aplicar_al_layout, res, lay, trabajo, tpath, cache=False, usuario=lay['bornes_usuario'])
        except Exception as e:          # noqa: BLE001  (como la web: el mapeo nunca frena el instructivo)
            mapeo = dict(error=f'{type(e).__name__}: {e}', n_puntos={}, modelos={}, usados=0)
            for k in ('bornes', 'renombrar', 'bornes_conf', 'bornes_nota', 'renombrar_auto'):
                lay.pop(k, None)
            lay['bornes'], lay['renombrar'] = {}, {}
        out['mapeo'] = resumen_mapeo(mapeo if isinstance(mapeo, dict) else {}, lay)
        meta['segundos']['mapeo'] = round(time.time() - t2, 1)
        # 4. instructivo (valores de un trabajo nuevo, como gen_instructivo con el topografico recien cargado)
        t3 = time.time()
        lay['estaciones'] = {}; lay['estacion'] = 'E6'
        lay['estacion_auto'] = {'seccion_min': 35, 'estacion': 'E8'}
        lay['salidas'] = {'grupos': [], 'preguntar': True}
        lay['quitados'] = []
        try:
            import instructivo as I
            ins = I.build(res, lay)
            out['instructivo'] = resumen_instructivo(ins, lay, res)
        except Exception as e:          # noqa: BLE001
            import traceback
            errores['instructivo'] = f'{type(e).__name__}: {e}'; meta['traceback_instructivo'] = traceback.format_exc()
        meta['segundos']['instructivo'] = round(time.time() - t3, 1)
    elif res is not None:               # funcional sin topografico: al menos las puntas de cada cable
        try:
            import instructivo as I
            out['extremos'] = {n: sorted(I.fmt_terminal(c['nodes'][k]) for k in c['bornes']) for n, c in I.conductors(res).items()}
        except Exception as e:          # noqa: BLE001
            errores['extremos'] = f'{type(e).__name__}: {e}'
    meta['segundos']['total'] = round(time.time() - t0, 1)
    meta['ocr_en_vivo'] = vivo['en_vivo']; meta['ocr_memoria'] = vivo['memoria']
    meta['stats_ocr'] = dict(getattr(res, 'stats', None) or {}) if res is not None else {}
    out['errores'] = errores
    reemplazos = sorted({(p, f'<{n}>') for n, base in (('programa', prog), ('raiz', RAIZ), ('tmp', tmp), ('tmp', tempfile.gettempdir()))
                         for p in (base, base.replace('\\', '/'), base.replace('\\', '\\\\'))}, key=lambda x: -len(x[0]))
    out = sin_rutas_locales(out, reemplazos)
    out['meta'] = meta
    escribir(os.path.join(salida, f'{clave}.json'), out)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    n = (out.get('instructivo') or {}).get('n') or {}
    print(f"{clave}: {(out.get('listado') or {}).get('n_cables')} cables, {n.get('lineas')} lineas E6, {n.get('pendientes')} pendientes, "
          f"{n.get('otra_estacion')} otra estacion, {n.get('sueltos')} sueltos; OCR en vivo {meta['ocr_en_vivo']}; "
          f"{meta['segundos']['total']} s{'; ERRORES ' + str(errores) if errores else ''}")
    return 0 if not errores else 1


def volcar(o, nivel=0, max_nivel=3):
    """JSON con un elemento por renglon hasta max_nivel (diffs legibles y archivo chico)"""
    if nivel >= max_nivel or not isinstance(o, (dict, list)) or not o:
        return json.dumps(o, ensure_ascii=False)
    pad = ' ' * (nivel + 1)
    if isinstance(o, dict):
        cuerpo = [f'{pad}{json.dumps(str(k), ensure_ascii=False)}: {volcar(v, nivel + 1, max_nivel)}' for k, v in o.items()]
        return '{\n' + ',\n'.join(cuerpo) + '\n' + ' ' * nivel + '}'
    return '[\n' + ',\n'.join(pad + volcar(v, nivel + 1, max_nivel) for v in o) + '\n' + ' ' * nivel + ']'


def escribir(path, o):
    with open(path + '.tmp', 'w', encoding='utf-8', newline='\n') as f:
        f.write(volcar(o) + '\n')
    os.replace(path + '.tmp', path)


# --------------------------------------------------------------------------- corrida de todos los planos
def correr_todos(salida, prog, solo=None, j=1, memoria_ocr=None, semilla='0'):
    archivos, planos = clasificar()
    if solo:
        faltan = set(solo) - {p['clave'] for p in planos}
        if faltan:
            print('FALLA: no hay planos con clave', sorted(faltan)); return 1
        planos = [p for p in planos if p['clave'] in solo]
    os.makedirs(salida, exist_ok=True)
    memoria = memoria_ocr or os.path.join(prog, 'ocr_cache.json')
    sha_mem = sha_archivo(memoria) if os.path.exists(memoria) else None
    print(f'programa: {prog}\nmemoria OCR (solo lectura): {memoria}\n{len(planos)} planos, {j} en paralelo')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', PLANOCABLES_PROGRAMA=prog)
    if semilla != 'aleatoria':
        env['PYTHONHASHSEED'] = str(semilla)
    else:
        env.pop('PYTHONHASHSEED', None)

    def uno(pl):
        cmd = [sys.executable, ESTE, '--uno', pl['clave'], pl['funcional'], pl['topografico'] or '-', salida, '--programa', prog]
        if memoria_ocr:
            cmd += ['--memoria-ocr', memoria_ocr]
        t = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        return pl, r, round(time.time() - t, 1)
    t0 = time.time()
    resultados = []
    if j <= 1:
        for pl in planos:
            resultados.append(uno(pl)); mostrar(*resultados[-1])
    else:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(j) as ex:
            for x in ex.map(uno, planos):
                resultados.append(x); mostrar(*x)
    fallas = []
    resumen = []
    for pl, r, seg in resultados:
        p = os.path.join(salida, pl['clave'] + '.json')
        d = json.load(open(p, encoding='utf-8')) if r.returncode in (0, 1) and os.path.exists(p) else None
        if d is None:
            fallas.append(f"{pl['clave']}: el proceso termino con {r.returncode}")
            continue
        if d.get('errores'):
            fallas.append(f"{pl['clave']}: {d['errores']}")
        resumen.append(dict(clave=pl['clave'], segundos=d['meta']['segundos'], ocr_en_vivo=d['meta'].get('ocr_en_vivo'),
                            n=(d.get('instructivo') or {}).get('n'), cables=(d.get('listado') or {}).get('n_cables')))
    indice = dict(parcial=bool(solo), programa=ruta_corta(prog), semilla=semilla,
                  clasificacion=[{k: v for k, v in a.items()} for a in archivos],
                  planos=planos, resumen=resumen, segundos_total=round(time.time() - t0, 1))
    escribir(os.path.join(salida, '_indice.json'), indice)
    if sha_mem and os.path.exists(memoria) and sha_archivo(memoria) != sha_mem:
        fallas.append(f'la memoria de OCR {memoria} cambio durante la corrida (no la escribe esta prueba: otro proceso?)')
    vivos = [f"{x['clave']} ({x['ocr_en_vivo']})" for x in resumen if x.get('ocr_en_vivo')]
    tam = sum(os.path.getsize(os.path.join(salida, f)) for f in os.listdir(salida) if f.endswith('.json'))
    print(f"\n{'plano':14s} {'listado':>8s} {'layout':>8s} {'mapeo':>8s} {'instr.':>8s} {'total':>8s}  (segundos)")
    for x in resumen:
        s = x['segundos']
        print(f"{x['clave']:14s} " + ' '.join(f"{s.get(k, '-'):>8}" for k in ('listado', 'layout', 'mapeo', 'instructivo', 'total')))
    print(f'\n{len(resultados)} planos en {indice["segundos_total"]} s; salida {salida} ({tam / 1024:.0f} KB)')
    if vivos:
        print('AVISO: renglones leidos con OCR en vivo (no estaban en la memoria):', ', '.join(vivos))
    salteados = [a for a in archivos if a['tipo'] not in ('funcional', 'topografico', 'eplan')]
    print('salteados:', '; '.join(f"{a['archivo']} = {TIPOS.get(a['tipo'], a['tipo']) if a['tipo'] != 'copia' else 'copia de ' + a['igual_a']}"
                                  for a in salteados))
    for a in archivos:
        if a.get('aviso'):
            fallas.append(f"{a['archivo']}: {a['aviso']}")
    if fallas:
        for f in fallas:
            print('FALLA:', f)
        return 1
    print('TODO OK')
    return 0


def mostrar(pl, r, seg):
    linea = (r.stdout or '').strip().splitlines()
    print(f"  {linea[-1] if linea else pl['clave'] + ': sin salida'}  [{seg} s con el arranque]", flush=True)
    if r.returncode not in (0, 1) or not linea:
        print('    ' + '\n    '.join((r.stderr or '').strip().splitlines()[-15:]), flush=True)


# --------------------------------------------------------------------------- comparar dos corridas
def renglones(x):
    if isinstance(x, list):
        return [json.dumps(v, ensure_ascii=False) for v in x]
    if isinstance(x, dict):
        return [f'{k}: {json.dumps(v, ensure_ascii=False)}' for k, v in x.items()]
    return [json.dumps(x, ensure_ascii=False)]


def comparar(da, db, maximo=25):
    def leer(d):
        out = {}
        for p in sorted(glob.glob(os.path.join(d, '*.json'))):
            n = os.path.basename(p)[:-5]
            out[n] = json.load(open(p, encoding='utf-8'))
        return out
    A, B = leer(da), leer(db)
    ia, ib = A.pop('_indice', {}), B.pop('_indice', {})
    if not A and not B:
        print(f'FALLA: no hay planos en {da} ni en {db}'); return 1
    difs = 0
    for n in sorted(set(A) | set(B)):
        if n not in A or n not in B:
            falta, parcial = (da, ia.get('parcial')) if n not in A else (db, ib.get('parcial'))
            if parcial:
                print(f'{n}: no esta en {falta} (corrida parcial, no se compara)')
            else:
                print(f'{n}: FALTA en {falta}'); difs += 1
            continue
        a, b = A[n], B[n]
        ma, mb = a.pop('meta', {}), b.pop('meta', {})
        ta, tb = (ma.get('segundos') or {}).get('total'), (mb.get('segundos') or {}).get('total')
        avisos = [f'OCR en vivo A={ma.get("ocr_en_vivo")} B={mb.get("ocr_en_vivo")}'] if ma.get('ocr_en_vivo') or mb.get('ocr_en_vivo') else []
        cambios = []
        for k in list(dict.fromkeys(list(a) + list(b))):
            va, vb = a.get(k), b.get(k)
            if va == vb:
                continue
            partes = [(f'{k}.{s}', (va or {}).get(s), (vb or {}).get(s)) for s in dict.fromkeys(list(va or {}) + list(vb or {}))] \
                if isinstance(va, dict) and isinstance(vb, dict) and k not in ('errores',) else [(k, va, vb)]
            for nombre, x, y in partes:
                if x == y:
                    continue
                ra, rb = renglones(x), renglones(y)
                dl = [l for l in difflib.unified_diff(ra, rb, lineterm='', n=0) if not l.startswith(('---', '+++', '@@'))]
                cambios.append((nombre, dl or [f'- {json.dumps(x, ensure_ascii=False)[:200]}', f'+ {json.dumps(y, ensure_ascii=False)[:200]}']))
        estado = 'IGUAL' if not cambios else f'DISTINTO ({len(cambios)} partes)'
        print(f'{n}: {estado}   [A {ta} s, B {tb} s]' + (f'   AVISO: {"; ".join(avisos)}' if avisos else ''))
        for nombre, dl in cambios:
            difs += 1
            print(f'  {nombre}: {sum(1 for l in dl if l.startswith("-"))} renglones en A, {sum(1 for l in dl if l.startswith("+"))} en B')
            for l in dl[:maximo]:
                print('    ' + (l[:220] + '…' if len(l) > 220 else l))
            if len(dl) > maximo:
                print(f'    … y {len(dl) - maximo} renglones mas')
    if difs:
        print(f'FALLA: {difs} diferencias entre {da} y {db}')
        return 1
    print('TODO OK (sin diferencias)')
    return 0


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('salida', nargs='?')
    ap.add_argument('--comparar', nargs=2, metavar=('DIR_A', 'DIR_B'))
    ap.add_argument('--programa', default=os.environ.get('PLANOCABLES_PROGRAMA') or os.path.join(RAIZ, 'programa'))
    ap.add_argument('--solo', default='')
    ap.add_argument('-j', type=int, default=1)
    ap.add_argument('--memoria-ocr', default=None)
    ap.add_argument('--semilla', default='0')
    ap.add_argument('--max', type=int, default=25)
    ap.add_argument('--listar', action='store_true')
    ap.add_argument('--uno', nargs=3, metavar=('CLAVE', 'FUNCIONAL', 'TOPOGRAFICO'))
    a = ap.parse_args()
    prog = os.path.abspath(a.programa)
    if a.uno:
        if not a.salida:
            ap.error('falta la carpeta de salida')
        clave, f, t = a.uno
        return correr_plano(clave, f, None if t == '-' else t, os.path.abspath(a.salida), prog,
                            os.path.abspath(a.memoria_ocr) if a.memoria_ocr else None)
    if a.comparar:
        return comparar(*a.comparar, maximo=a.max)
    if a.listar:
        archivos, planos = clasificar()
        for x in archivos:
            print(f"{x['tipo']:12s} {x['archivo']}" + (f"  (= {x['igual_a']})" if x.get('igual_a') else '') + (f"  AVISO {x['aviso']}" if x.get('aviso') else ''))
        print()
        for p in planos:
            print(f"{p['clave']:14s} {p['funcional']}\n{'':14s} + {p['topografico']}")
        return 0
    if not a.salida:
        ap.error('falta la carpeta de salida (o --comparar / --listar)')
    if not os.path.isdir(prog) or not os.path.exists(os.path.join(prog, 'core.py')):
        print(f'FALLA: {prog} no es una carpeta del programa (no tiene core.py)'); return 1
    solo = [s.strip() for s in a.solo.split(',') if s.strip()]
    return correr_todos(os.path.abspath(a.salida), prog, solo, a.j, os.path.abspath(a.memoria_ocr) if a.memoria_ocr else None, a.semilla)


if __name__ == '__main__':
    sys.exit(main())
