"""Producto del tablero (PLAN_MODULAR 5.1, etapa 2): codigo de producto SAP, plano funcional y topografico con su
revision. No escribe en el repo: la web corre sobre una copia temporal de un trabajo y con una copia temporal del
catalogo FIJO de las pruebas (pruebas/fixtures/productos.json, por PLANOCABLES_PRODUCTOS; el de programa/ lo cambia el
taller al confirmar productos, solo se mira que se pueda leer). Termina con error si algo falla.
uso: python pruebas/probar_producto.py [--todas] [--sin-web]
  --todas:   lee todas las hojas de cada funcional (como la web); por defecto las hojas 1 y 2 (alcanza para el rotulo)
  --sin-web: salta la parte C
  A. planocables.producto sin planos: titulos y nombres de archivo, numero largo de SAP, revisiones como texto,
     precedencia del codigo (confirmado > catalogo > rotulo > portada > archivo), confianza (rotulo en 1 hoja = media),
     avisos cuando dos fuentes no coinciden, el «Code: 2344» de EPLAN no se lee, catalogo ambiguo, topografico de otro
     producto y cuando pregunta el asistente.
  B. deteccion sobre los planos de '1 - Planos' (los pares de ab_planos.clasificar: todos tienen que tener su valor
     esperado) y los trabajos de pruebas/trabajos (66817, TPT), con web.detectar_producto (rotulo de las hojas leidas,
     /Title y nombre del archivo), el topografico por su /Title y el catalogo programa/productos.json.
  C. la web (test_client) sobre una copia del TPT: GET / PUT /api/trabajo/<id>/producto, el asistente (preguntar una
     sola vez, tambien al regenerar), producto.json manda al regenerar (no se pisa), el PUT del instructivo no pisa el
     producto, y el catalogo suma los alias (el plano pasa al producto confirmado). El catalogo del repo no cambia."""
import os, sys, json, time, shutil, hashlib, tempfile, subprocess

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROG = os.path.join(RAIZ, 'programa')
PRUEBAS = os.path.join(RAIZ, 'pruebas')
CATALOGO = os.path.join(PROG, 'productos.json')                     # el del taller (lo cambia la web): no se usa ni se toca
FIJO = os.path.join(PRUEBAS, 'fixtures', 'productos.json')           # el de las pruebas (las bases salen con este)
OCR = os.path.join(PROG, 'ocr_cache.json')
sys.stdout.reconfigure(encoding='utf-8')
sys.dont_write_bytecode = True
TODAS = '--todas' in sys.argv
TMP = tempfile.mkdtemp(prefix='probar_producto_')
os.environ['PLANOCABLES_MEMORIA_OCR'] = 'solo-lectura'
os.environ['PLANOCABLES_HISTORIAL'] = os.path.join(TMP, 'historial')
os.environ['PLANOCABLES_PORT'] = '8797'
os.environ['PLANOCABLES_PRODUCTOS'] = os.path.join(TMP, 'productos.json')
os.makedirs(os.environ['PLANOCABLES_HISTORIAL'])
shutil.copyfile(FIJO, os.environ['PLANOCABLES_PRODUCTOS'])
sys.path.insert(0, PROG)
sys.path.insert(0, PRUEBAS)
from planocables import producto as PR

fallas = []


def chequear(ok, msg):
    print(('  ok    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)
    return ok


def sha(p):
    try:
        with open(p, 'rb') as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None


def git_status():
    r = subprocess.run(['git', '-c', 'core.quotepath=false', '-C', RAIZ, 'status', '--porcelain=v1', '-uall'],
                       capture_output=True, text=True, encoding='utf-8')
    return r.stdout if r.returncode == 0 else None


# ------------------------------------------------------------------ A. sin planos
def linea(t, x0, y, x1=None, h=4.0):
    return dict(text=t, bbox=[x0, y, x1 if x1 is not None else x0 + 2.2 * len(t), y + h], ang=0, H=h)


def parte_a():
    print('A. planocables.producto sin planos')
    casos = [('75287 ZPL Functional Diagram mSafe2 REV6.pdf', ('75287', '6', None)),
             ('50000000000000072715-Rev4-PI&D + Functional Diagram - mSafeTecpetrol.pdf', ('72715', '4', None)),
             ('75206  ZPL-REV2- Functional Diagram - mSafe NA - 220V - SHELL.pdf', ('75206', '2', None)),
             ('76739 ZPL Diagrama Eléctrico Funcional REV 4.pdf', ('76739', '4', None)),
             ('mSafe2 PAE - Rev 0', (None, '0', None)),
             ('ZPL-76884 - mSafe2+ PAE - Rev 0A - FABRICACIÓN.pdf', ('76884', '0A', None)),
             ('Diagrama eléctrico funcional 66817-1.07.pdf', (None, None, '66817-1')),
             ('75287 DIAGRAMA ELECTRICO mSafe2AC - REV.6.pdf', ('75287', '6', None)),
             ('X 4(A).pdf', (None, None, None)), ('72715 rev 4(A)', ('72715', '4(A)', None)),
             ('LFONTES/PRO0000021436_1', (None, None, None)), ('5000000000000000076426ZPL', ('76426', None, None))]
    for t, esp in casos:
        r = PR.de_texto(t)
        chequear(r == esp, f'de_texto({t!r}) = {r} (se espera {esp})')
    chequear(PR.nucleo('ZPL-76884') == '76884' and PR.nucleo('50000000000000074676 ZPL') == '74676', 'nucleo: ZPL-76884 -> 76884, el número largo de SAP -> 74676')
    chequear(PR.norm_rev('06') == '6' and PR.norm_rev('0A') != PR.norm_rev('0') and PR.norm_rev(' 4 (a) ') == '4(A)', 'revisiones como texto: 06 = 6, 0A ≠ 0, 4(A)')
    # rotulo de AutoCAD: CODE y DOC NUMBER en el mismo renglon; REV: del renglon del documento; campo vacio
    hoja = dict(lines=[linea('CODE:', 100, 50), linea('75286-1', 130, 50), linea('TITLE:', 400, 50),
                       linea('DOC NUMBER:', 100, 60), linea('50000000000000075287 ZPL', 140, 60), linea('REV:', 260, 60), linea('6', 275, 60),
                       linea('REV:', 500, 50), linea('2', 500, 42)])
    r = PR.rotulo_hoja(hoja)
    chequear(r == dict(codigo='75286-1', numero='75287', revision='6'), f'rótulo de una hoja: {r}')
    vacio = dict(lines=[linea('CÓDIGO:', 100, 50), linea('TITULO:', 140, 50), linea('N° DE DOC:', 100, 60), linea('75441', 130, 60),
                        linea('REV.', 160, 60), linea('GRAL:', 172, 60), linea('6', 186, 60)])
    r = PR.rotulo_hoja(vacio)
    chequear(r == dict(codigo=None, numero='75441', revision='6'), f'CÓDIGO: vacío (sigue TITULO:) y «REV.» + «GRAL:» partido: {r}')
    # deteccion: rotulo en 2 hojas = alta; en 1 = media; dos codigos = aviso
    d2 = PR.producto_del_plano([hoja, hoja], '75287 ZPL Functional Diagram mSafe2 REV6.pdf', '75287 - REV.6.pdf')
    p = PR.combinar(d2, None, {}, None)
    chequear((p['codigo'], p['fuente'], p['confianza'], p['confirmado']) == ('75286-1', 'rotulo', 'alta', False) and not p['avisos'],
             f'rótulo igual en 2 hojas, sin catálogo: {p["codigo"]} {p["fuente"]} {p["confianza"]} confirmado={p["confirmado"]} {p["avisos"]}')
    p1 = PR.combinar(PR.producto_del_plano([hoja], None, None), None, {}, None)
    chequear((p1['codigo'], p1['confianza'], p1['funcional']['fuente']) == ('75286-1', 'media', 'rotulo') and PR.hay_que_preguntar(p1),
             f'rótulo en 1 hoja: confianza media y el asistente pregunta ({p1["confianza"]}, plano del {p1["funcional"]["fuente"]})')
    otra = dict(lines=[linea('CODE:', 100, 50), linea('75286-2', 130, 50)])
    p = PR.combinar(PR.producto_del_plano([hoja, hoja, otra], None, None), None, {}, None)
    chequear(p['codigo'] == '75286-1' and any('más de un código' in a for a in p['avisos']), f'dos códigos en el rótulo: aviso ({p["avisos"]})')
    # el titulo manda en plano y revision; si el rotulo dice otro numero: aviso (el rotulo del 76740 dice 75877)
    h76740 = dict(lines=[linea('DOC NUMBER:', 100, 60), linea('75877 ZPL', 140, 60)])
    p = PR.combinar(PR.producto_del_plano([h76740], '76740 ZPL Topografico Panel mSafe REV 3.pdf', None), None, {}, None)
    chequear(p['funcional']['numero'] == '76740' and any('número de plano no coincide' in a and '75877' in a for a in p['avisos']),
             f'título 76740 y rótulo 75877: manda el título, con aviso ({p["avisos"]})')
    # precedencia del codigo
    cat = {'productos': {'76572-1': {'nombre': 'mSafe1 PP STD', 'alias': {'planos': ['76739', '76740'], 'codigo_rotulo': ['76571-1']}},
                         '75286-1': {'nombre': 'mSafe2AC VISTA', 'alias': {'planos': ['75287']}}}}
    hpp = dict(lines=[linea('CODE:', 100, 50), linea('76571-1', 130, 50)])
    dpp = PR.producto_del_plano([hpp, hpp], '76739 ZPL Diagrama Eléctrico Funcional REV 4.pdf', None)
    p = PR.combinar(dpp, None, cat, None)
    chequear((p['codigo'], p['nombre'], p['fuente'], p['confirmado'], p['codigo_rotulo']) == ('76572-1', 'mSafe1 PP STD', 'catalogo', True, '76571-1') and not p['avisos'],
             f'PP STD: el rótulo dice 76571-1, el catálogo lo tiene como alias: {p["codigo"]} «{p["nombre"]}» ({p["fuente"]}) sin avisos')
    p = PR.combinar(dpp, None, cat, {'codigo': '76572-9', 'nombre': 'otro'})
    chequear((p['codigo'], p['nombre'], p['fuente']) == ('76572-9', 'otro', 'confirmado') and not PR.hay_que_preguntar(p), 'lo confirmado a mano manda sobre el catálogo')
    p = PR.combinar(dpp, None, cat, {'codigo': 'xx'})
    chequear(p['codigo'] == '76572-1', 'un producto.json con un código inválido no cuenta')
    d = PR.producto_del_plano([hoja, hoja], '75287 ZPL Functional Diagram mSafe2 REV6.pdf', None)
    p = PR.combinar(d, None, {'productos': {'75286-9': {'nombre': 'A', 'alias': {'planos': ['75287']}}}}, None)
    chequear(p['codigo'] == '75286-9' and any('75286-1' in a for a in p['avisos']), f'catálogo y rótulo distintos: manda el catálogo, con aviso ({p["avisos"]})')
    amb = {'productos': {'75286-8': {'alias': {'planos': ['75287']}}, '75286-9': {'alias': {'planos': ['75287']}}}}
    p = PR.combinar(d, None, amb, None)
    chequear(p['codigo'] == '75286-1' and p['fuente'] == 'rotulo' and any('mismo plano' in a for a in p['avisos']),
             f'el mismo plano en dos productos del catálogo: no se elige ninguno, aviso ({p["avisos"]})')
    p = PR.combinar(d, dict(numero='76740', revision='3', fuente='titulo_pdf'), cat, None)
    chequear(any('topográfico 76740' in a and '76572-1' in a for a in p['avisos']), f'topográfico de otro producto del catálogo: aviso ({p["avisos"]})')
    # EPLAN: documento y revision del rotulo; 'Code: 2344' no; la portada solo sugiere
    pe = dict(lines=[linea('Code:', 100, 50), linea('2344', 130, 50), linea('Diagrama Eléctrico Funcional Conjunto 76860-1', 100, 300)])
    de = PR.producto_del_plano([pe], 'mSafe2 PAE - Rev 1', 'ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.pdf', eplan=dict(documento='ZPL-76884', revision='1'))
    p = PR.combinar(de, None, {}, None)
    chequear((p['codigo'], p['fuente'], p['confianza'], p['confirmado'], p['documento'], p['revision']) == ('76860-1', 'portada', 'baja', False, 'ZPL-76884', '1')
             and PR.hay_que_preguntar(p) and not p['avisos'],
             f'EPLAN sin catálogo: la portada solo sugiere (baja, pregunta), documento {p["documento"]} rev {p["revision"]}')
    chequear(de['codigo']['rotulo'] is None, 'EPLAN: el «Code: 2344» del rótulo no se lee como código')
    p = PR.combinar(PR.producto_del_plano([], None, 'algo sin datos.pdf'), None, {}, None)
    chequear(p['codigo'] is None and p['confianza'] == 'baja' and PR.hay_que_preguntar(p), 'sin ningún dato: sin código y pregunta')
    t = PR.topografico_del_pdf('75441 ZPL Topográfico Panel mSafe2 REV6.pdf', '75441 TOPOGRAFICO PANEL MSAFE2 - REV.5.pdf')
    chequear((t['numero'], t['revision'], t['fuente']) == ('75441', '6', 'titulo_pdf') and len(t.get('avisos') or []) == 1,
             f'topográfico: manda el título; la revisión del nombre no coincide: aviso ({t.get("avisos")})')
    # los dos catalogos: el del taller (programa/productos.json, lo agranda la web) y el fijo de las pruebas
    decididos = {'75286-1', '66817-1', '72715-1', '76857-1', '76572-1'}     # (decididos el 2026-10-07)
    for nombre, p in (('programa/productos.json', CATALOGO), ('pruebas/fixtures/productos.json', FIJO)):
        try:
            with open(p, encoding='utf-8') as f:
                prods = PR.productos_de(json.load(f))
        except (OSError, ValueError) as e:
            prods = {}
            print('   ', type(e).__name__, e)
        chequear(decididos <= set(prods), f'{nombre}: se lee y tiene los {len(decididos)} productos decididos ({len(prods)} productos)')
    with open(FIJO, encoding='utf-8') as f:
        fijo = PR.productos_de(json.load(f))
    chequear(fijo.get('76857-1', {}).get('alias', {}).get('documentos') == ['ZPL-76884'] and
             fijo.get('76572-1', {}).get('alias', {}).get('codigo_rotulo') == ['76571-1'],
             'catálogo de las pruebas: el PAE por el documento ZPL-76884 y el PP STD con el rótulo 76571-1')


# ------------------------------------------------------------------ B. planos
C = '1 - Planos/Catalogo (referencia)/'
ESPERADO = {
    # clave (ab_planos.clave_de): codigo, confirmado, fuente del codigo, plano funcional, revision, topografico, avisos
    '75287_rev6': ('75286-1', True, 'catalogo', '75287', '6', ('75441', '6'), []),
    '75206_rev2': ('75206-1', False, 'rotulo', '75206', '2', ('75208', '2'), []),
    '72715_rev4': ('72715-1', True, 'catalogo', '72715', '4', ('72887', '3'), []),
    '76425': ('76222-1', False, 'rotulo', '76425', '0', ('76426', '0'), []),         # la orden dice 76244-1: sin confirmar
    '75733_rev1': ('75902-1', False, 'rotulo', '75733', '1', ('75992', '1'), []),
    '76611_rev0': ('76610-1', False, 'rotulo', '76611', '0', ('76612', '0'), []),
    '76884_rev1': ('76857-1', True, 'catalogo', 'ZPL-76884', '1', ('ZPL-76884', '1'), []),     # no esta en el PDF: catalogo
    '76884_rev0A': ('76857-1', True, 'catalogo', 'ZPL-76884', '0', ('ZPL-76884', '0'), ['0A']),  # el rotulo dice 0
    'trabajo 66817': ('66817-1', True, 'catalogo', '74676', '7', ('75775', '8'), []),           # el plano no es 66817
    'trabajo tpt': ('72715-1', True, 'catalogo', '72715', '8', ('72887', '7'), []),
}


def parte_b():
    print(f'B. detección sobre los planos ({"todas las hojas" if TODAS else "hojas 1 y 2"}, memoria OCR en solo lectura)')
    import ab_planos, web
    from core import process
    _, planos = ab_planos.clasificar()
    casos = [(p['clave'], os.path.join(RAIZ, p['funcional']), os.path.join(RAIZ, p['topografico']) if p['topografico'] else None,
              os.path.basename(p['funcional']), os.path.basename(p['topografico'] or ''), p['eplan']) for p in planos]
    for t in ('66817', 'tpt'):
        d = os.path.join(PRUEBAS, 'trabajos', t)
        with open(os.path.join(d, 'estado.json'), encoding='utf-8') as f:
            s = json.load(f)
        casos.append((f'trabajo {t}', os.path.join(d, s['archivo']), os.path.join(d, 'topografico.pdf'), s.get('nombre') or s['archivo'],
                      s.get('topo_nombre'), False))
    sin = sorted(set(c[0] for c in casos) - set(ESPERADO))
    chequear(not sin, 'todos los planos de 1 - Planos tienen su valor esperado' + (f' (faltan: {sin})' if sin else ''))
    faltan = sorted(set(ESPERADO) - set(c[0] for c in casos))
    chequear(not faltan, 'y están todos los esperados' + (f' (no están: {faltan})' if faltan else ''))
    catalogo = web.leer_catalogo()
    for clave, f, topo, nombre, topo_nombre, eplan in casos:
        if clave not in ESPERADO:
            continue
        t0 = time.time()
        res = process(f, log=lambda m: None, use_ocr=True, pages=None if TODAS else {1, 2})
        det = web.detectar_producto(res, nombre)
        if eplan:       # «Usar las bandejas de este mismo PDF» (web.topografico_de)
            top = dict(numero=res.documento, revision=res.revision, fuente='mismo_pdf', mismo_pdf=True)
        else:
            top = PR.topografico_del_pdf(web.titulo_pdf(topo), topo_nombre)
        p = PR.combinar(det, top, catalogo, None)
        cod, conf, fuente, num, rev, (tn, tr), av = ESPERADO[clave]
        ok_av = (not av and not p['avisos']) or (av and len(p['avisos']) == len(av) and all(x in a for x, a in zip(av, p['avisos'])))
        chequear((p['codigo'], p['confirmado'], p['fuente'], p['funcional']['numero'], p['funcional']['revision'],
                  p['topografico']['numero'], p['topografico']['revision']) == (cod, conf, fuente, num, rev, tn, tr) and ok_av,
                 f'{clave}: {p["codigo"]} {"«" + p["nombre"] + "» " if p["nombre"] else ""}({p["fuente"]}, '
                 f'{"confirmado" if p["confirmado"] else "sin confirmar"}, {p["confianza"]}) · funcional {p["funcional"]["numero"]} rev '
                 f'{p["funcional"]["revision"]} ({p["funcional"]["fuente"]}) · topográfico {p["topografico"]["numero"]} rev '
                 f'{p["topografico"]["revision"]} · rótulo {p["codigo_rotulo"]} en {det["codigo"]["hojas"]} hojas'
                 + (f' · avisos: {p["avisos"]}' if p['avisos'] else '') + f' ({time.time() - t0:.0f} s)')


# ------------------------------------------------------------------ C. web
def parte_c():
    print('C. web: GET / PUT /producto sobre una copia del TPT (catálogo temporal)')
    import web
    with open(os.path.join(PRUEBAS, 'trabajos', 'tpt', 'estado.json'), encoding='utf-8') as f:
        jid = json.load(f)['id']
    d = os.path.join(web.WORK, jid)
    shutil.copytree(os.path.join(PRUEBAS, 'trabajos', 'tpt'), d)
    # catalogo sin el TPT: el producto sale del plano y el asistente pregunta
    cat = json.load(open(web.PRODUCTOS, encoding='utf-8'))
    del cat['productos']['72715-1']
    with open(web.PRODUCTOS, 'w', encoding='utf-8') as f:
        f.write(web.texto_catalogo(cat))
    cl = web.app.test_client()
    B = f'http://127.0.0.1:{web.PORT}'
    get = lambda u: cl.get(u, base_url=B)
    put = lambda u, j: cl.put(u, base_url=B, json=j)
    u = f'/api/trabajo/{jid}'
    ins = get(u + '/instructivo').get_json() or {}
    p = ins.get('producto') or {}
    chequear(p.get('preguntar') is True and p.get('codigo') is None and (p.get('funcional') or {}).get('numero') == '72715'
             and (p.get('topografico') or {}).get('numero') == '72887',
             f'instructivo viejo sin producto: se completa al leerlo (plano {p.get("funcional")}, topográfico {p.get("topografico")}) y pregunta')
    r = get(u + '/producto').get_json() or {}
    chequear(r.get('producto', {}).get('preguntar') is True and isinstance(r.get('sugerencias'), list) and any(c['codigo'] == '76857-1' for c in r.get('catalogo') or []),
             f'GET /producto: pregunta, {len(r.get("sugerencias") or [])} sugerencias y el catálogo')
    chequear(put(u + '/producto', {}).status_code == 400 and put(u + '/producto', {'codigo': '7271-1'}).status_code == 400,
             'PUT /producto sin datos o con un código inválido: 400')
    r = put(u + '/producto', {'preguntado': True})
    j = r.get_json() or {}
    chequear(r.status_code == 200 and j['producto'].get('preguntar') is False and j['producto'].get('preguntado') is True
             and not os.path.exists(os.path.join(d, 'producto.json')), 'el asistente se cerró sin confirmar: no vuelve a preguntar (y no hay producto.json)')
    ins = get(u + '/instructivo').get_json() or {}
    chequear((ins.get('producto') or {}).get('preguntar') is False, 'GET /instructivo: ya no pregunta')
    # regenerar: el plano leido entero (rotulo 72715-1 en las 20 hojas); ya se pregunto: no vuelve a preguntar
    t0 = time.time()
    web.INS[jid] = dict(estado='en cola', mensaje='', progreso=0.0)
    web.gen_instructivo(jid)
    st = web.INS[jid]
    if chequear(st.get('estado') == 'terminado', f'regenerado en {time.time() - t0:.0f} s ({st.get("estado")} {st.get("error") or ""})'):
        p = (get(u + '/instructivo').get_json() or {}).get('producto') or {}
        chequear((p.get('codigo'), p.get('fuente'), p.get('confianza'), p.get('confirmado'), p.get('preguntar'), p.get('preguntado'))
                 == ('72715-1', 'rotulo', 'alta', False, False, True) and (p.get('detectado') or {}).get('codigo', {}).get('hojas') == 20,
                 f'al regenerar: código del rótulo ({p.get("codigo")}, {p.get("fuente")}, {p.get("confianza")}), sin confirmar y sin volver a preguntar')
    # confirmar: producto.json, el catalogo y el instructivo (sin regenerar)
    r = put(u + '/producto', {'codigo': '72715-1', 'nombre': '  mSafe1   TPT '})
    j = (r.get_json() or {}).get('producto') or {}
    conf = json.load(open(os.path.join(d, 'producto.json'), encoding='utf-8')) if os.path.exists(os.path.join(d, 'producto.json')) else {}
    chequear(r.status_code == 200 and (j.get('codigo'), j.get('nombre'), j.get('fuente'), j.get('confirmado')) == ('72715-1', 'mSafe1 TPT', 'confirmado', True)
             and (conf.get('codigo'), conf.get('nombre'), conf.get('confirmado')) == ('72715-1', 'mSafe1 TPT', True),
             f'PUT /producto 72715-1: producto.json {conf.get("codigo")} «{conf.get("nombre")}»')
    ins = get(u + '/instructivo').get_json() or {}
    chequear((ins.get('producto') or {}).get('codigo') == '72715-1' and ins['producto'].get('fuente') == 'confirmado',
             'el instructivo lo tiene sin regenerar')
    cat = json.load(open(web.PRODUCTOS, encoding='utf-8'))
    e = cat['productos'].get('72715-1') or {}
    chequear(e.get('nombre') == 'mSafe1 TPT' and e.get('alias', {}).get('planos') == ['72715', '72887'],
             f'catálogo: 72715-1 «{e.get("nombre")}» con los planos {e.get("alias", {}).get("planos")}')
    # el PUT del instructivo (copia vieja de la ventana) no pisa el producto
    ins['producto'] = dict(ins['producto'], codigo='00000-0')
    chequear(put(u + '/instructivo', ins).status_code == 200 and (get(u + '/instructivo').get_json() or {}).get('producto', {}).get('codigo') == '72715-1',
             'PUT /instructivo con un producto viejo: queda el del disco')
    # producto.json manda aunque el instructivo tenga otro (se confirmo mientras se regeneraba): se completa al leerlo
    with open(os.path.join(d, 'producto.json'), 'w', encoding='utf-8') as f:
        json.dump({'codigo': '72715-3', 'nombre': 'otro', 'confirmado': True}, f)
    p = (get(u + '/instructivo').get_json() or {}).get('producto') or {}
    chequear((p.get('codigo'), p.get('fuente'), p.get('preguntar')) == ('72715-3', 'confirmado', False),
             f'instructivo con otro código que producto.json: GET /instructivo da el de producto.json ({p.get("codigo")}, {p.get("fuente")})')
    # otro codigo: el plano funcional pasa al producto nuevo; el topografico se suma (lo pueden compartir)
    put(u + '/producto', {'codigo': '72715-2', 'nombre': ''})
    cat = json.load(open(web.PRODUCTOS, encoding='utf-8'))
    a1, a2 = cat['productos']['72715-1']['alias'], cat['productos']['72715-2']['alias']
    chequear(a2['planos'] == ['72715', '72887'] and a1['planos'] == ['72887'], f'el plano 72715 pasa a 72715-2 ({a2["planos"]}; 72715-1 queda con {a1["planos"]})')
    chequear(cat['productos']['72715-2'].get('nombre') is None and json.load(open(os.path.join(d, 'producto.json'), encoding='utf-8'))['codigo'] == '72715-2',
             'sin nombre: queda sin nombre')
    # regenerar: lo confirmado manda (no se pisa)
    t0 = time.time()
    web.INS[jid] = dict(estado='en cola', mensaje='', progreso=0.0)
    web.gen_instructivo(jid)
    p = (get(u + '/instructivo').get_json() or {}).get('producto') or {}
    chequear(web.INS[jid].get('estado') == 'terminado' and (p.get('codigo'), p.get('fuente'), p.get('preguntar')) == ('72715-2', 'confirmado', False)
             and p.get('documento') == '72715' and p.get('revision') == '8',
             f'al regenerar manda lo confirmado: {p.get("codigo")} ({p.get("fuente")}), documento {p.get("documento")} rev {p.get("revision")} ({time.time() - t0:.0f} s)')
    r = get(u + '/producto').get_json() or {}
    chequear(r.get('producto', {}).get('codigo') == '72715-2' and r['sugerencias'][0]['codigo'] == '72715-2',
             'GET /producto: el confirmado primero en las sugerencias')


antes = dict(ocr=sha(OCR), catalogo=sha(CATALOGO), fijo=sha(FIJO), git=git_status())
t_inicio = time.time()
try:
    for parte in (parte_a, parte_b) + (() if '--sin-web' in sys.argv else (parte_c,)):
        try:
            parte()
        except Exception:
            import traceback
            traceback.print_exc()
            chequear(False, f'{parte.__name__} se cortó con una excepción')
finally:
    shutil.rmtree(TMP, ignore_errors=True)
print('D. nada cambió en el repo')
chequear(sha(OCR) == antes['ocr'], 'programa/ocr_cache.json sin cambios' + ('' if sha(OCR) == antes['ocr'] else
         ' (hubo OCR en vivo; en el worktree se restaura con: git checkout -- programa/ocr_cache.json)'))
chequear(sha(CATALOGO) == antes['catalogo'] and sha(FIJO) == antes['fijo'],
         'programa/productos.json y pruebas/fixtures/productos.json sin cambios (la web usó una copia)')
chequear(git_status() == antes['git'], 'git status igual')
print(f'\n({time.time() - t_inicio:.0f} s)')
if fallas:
    print(f'{len(fallas)} FALLA(S):')
    for f in fallas:
        print(' -', f.split('\n')[0])
    sys.exit(1)
print('TODO OK')
