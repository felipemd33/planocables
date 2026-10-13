"""Interfaz web local: http://127.0.0.1:8765
Sube un plano PDF, genera el PDF buscable y el listado de cables, y permite
explorar el listado y ver cada cable resaltado sobre el plano."""
import os, sys, json, uuid, threading, time, datetime, shutil, subprocess, re, io, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from flask import Flask, request, jsonify, send_file, abort

ROOT = os.path.dirname(HERE)
WORK = os.environ.get('PLANOCABLES_HISTORIAL') or os.path.join(ROOT, '3 - Historial web')    # (otra carpeta: pruebas)
os.makedirs(WORK, exist_ok=True)
PORT = int(os.environ.get('PLANOCABLES_PORT', '8765'))

app = Flask(__name__, static_folder=os.path.join(HERE, 'web'), static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024
JOBS = {}
RUN_LOCK = threading.Lock()   # un plano a la vez (el proceso usa toda la CPU)
from ocr_raster import PDFIUM_LOCK   # pdfium no admite uso simultaneo desde varios hilos
from planocables import producto as PR   # codigo de producto, plano y revision (sin disco: los archivos los lee la web)
# catalogo de productos del taller (crece cuando se confirma el producto de un trabajo). Otra ruta: pruebas
PRODUCTOS = os.environ.get('PLANOCABLES_PRODUCTOS') or os.path.join(HERE, 'productos.json')
CATALOGO_LOCK = threading.Lock()
# parametros de la lista WPC (los cambia el taller con el panel ⚙ Parametros; respaldos en respaldos_wpc/ al lado). Otra ruta: pruebas
CONFIG_WPC = os.environ.get('PLANOCABLES_CONFIG_WPC') or os.path.join(HERE, 'web', 'wpc.json')
CONFIG_WPC_LOCK = threading.Lock()


def job_dir(jid):
    if not re.fullmatch(r'[0-9a-f]{12}', jid or ''):
        abort(404)
    d = os.path.join(WORK, jid)
    if not os.path.isdir(d):
        abort(404)
    return d


def save_state(jid):
    j = JOBS[jid]
    p = os.path.join(WORK, jid, 'estado.json')
    with open(p + '.tmp', 'w', encoding='utf-8') as f:
        json.dump({k: v for k, v in j.items() if k != 'log'} | {'log': j['log'][-200:]}, f, ensure_ascii=False)
    os.replace(p + '.tmp', p)   # escritura atomica: nunca queda un estado.json a medias


def load_state(jid):
    if jid in JOBS:
        return JOBS[jid]
    p = os.path.join(WORK, jid, 'estado.json')
    if os.path.exists(p):
        try:
            with open(p, encoding='utf-8') as f:
                st = json.load(f)
        except Exception:
            return None
        if st.get('estado') in ('procesando', 'en cola'):   # el programa se cerro a mitad
            st['estado'] = 'error'; st['error'] = 'Proceso interrumpido (se cerró el programa). Vuelve a procesar el plano.'
            try:
                with open(p + '.tmp', 'w', encoding='utf-8') as f:
                    json.dump(st, f, ensure_ascii=False)
                os.replace(p + '.tmp', p)
            except Exception:
                pass
        return st
    return None


def result_json(res, name, opts, confirmado=None):
    """resultado.json. 'producto' (codigo, plano y revision): lo detectado en el plano con el catalogo y lo confirmado a
    mano en el trabajo (producto.json), sin el topografico (todavia no se cargo)"""
    from core import sheet_name
    pages = [dict(index=p['index'], sheet=sheet_name(p), title=p['meta'].get('title', ''), w=p['w'] - p.get('x0', 0), h=p['h'] - p.get('y0', 0),
                  x0=p.get('x0', 0), y0=p.get('y0', 0),
                  cables=sum(1 for n in p['nums'] if n['chain'] is not None)) for p in res.pages]
    clean = lambda d: {k: v for k, v in d.items() if k not in ('chain', 'etiquetas', 'via')}
    try:
        det = detectar_producto(res, name)
        producto = dict(PR.combinar(det, None, leer_catalogo(), confirmado), detectado=det)
    except Exception as e:      # el producto nunca frena el listado
        producto = dict(error=f'{type(e).__name__}: {e}', avisos=[f'no se pudo leer el producto del plano ({e})'])
    return dict(
        nombre=name, fecha=datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), segundos=round(res.seconds, 1),
        nota=res.default[2] if res.default else None, paginas=pages, opciones=opts,
        cables=res.cables, detalle=[clean(d) for d in res.detail], revisar=res.review,
        rutas={str(p['index']): p.get('routes', {}) for p in res.pages if p.get('routes')},
        sin_numero=getattr(res, 'unnumbered', []), stats=res.stats, producto=producto)


def run_job(jid, pdf_path, opts, rearmar_instructivo=False):
    """procesa el plano; rearmar_instructivo (↻ Reprocesar): si el trabajo ya tiene topografico, al terminar se vuelve a
    armar el instructivo con el resultado nuevo (como ↻ Regenerar: se conservan marcas, puntos ajustados, estaciones,
    cables quitados y auditoria)"""
    j = JOBS[jid]
    try:
        j['estado'] = 'en cola'; save_state(jid)
        with RUN_LOCK:
            j['estado'] = 'procesando'; j['inicio'] = time.time(); save_state(jid)
            from core import process, write_searchable_pdf, write_excel

            def log(m):
                j['log'].append(m); j['mensaje'] = m
                mm = re.match(r'Hoja (\d+)/(\d+)', m)
                if mm:
                    j['progreso'] = int(mm.group(1)) / int(mm.group(2)) * 0.85
            res = process(pdf_path, log=log, use_ocr=opts.get('ocr', True))
            base = os.path.splitext(os.path.basename(pdf_path))[0]
            d = os.path.dirname(pdf_path)
            es_eplan = bool(getattr(res, 'eplan', False))
            j['eplan'] = es_eplan
            if es_eplan:
                # plano de EPLAN: el PDF ya trae el texto (se busca con Ctrl+F tal cual), no hace falta un PDF buscable
                j['pdf'] = j['archivo']
            elif opts.get('pdf', True):
                log('Generando PDF buscable…'); j['progreso'] = 0.88
                from ocr_raster import page_items
                write_searchable_pdf(res, os.path.join(d, base + ' - BUSCABLE.pdf'),
                                     raster_ocr=page_items if opts.get('ocr', True) else None)
                j['pdf'] = base + ' - BUSCABLE.pdf'
            if opts.get('excel', True):
                log('Generando Excel…'); j['progreso'] = 0.95
                write_excel(res, os.path.join(d, base + ' - LISTADO DE CABLES.xlsx'))
                if es_eplan:
                    import eplan
                    eplan.excel_extra(res, os.path.join(d, base + ' - LISTADO DE CABLES.xlsx'))
                j['excel'] = base + ' - LISTADO DE CABLES.xlsx'
            with open(os.path.join(d, 'resultado.json'), 'w', encoding='utf-8') as f:
                json.dump(result_json(res, j['nombre'], opts, confirmado=leer_confirmado(d)), f, ensure_ascii=False)
            j['cables'] = len({c['num'] for c in res.cables}); j['revisar'] = len(res.review)
            j['segundos'] = round(res.seconds, 1)
            j['estado'] = 'terminado'; j['progreso'] = 1.0
            log(f"Listo en {res.seconds:.0f} s: {j['cables']} números de cable.")
    except Exception as e:
        import traceback
        j['estado'] = 'error'; j['error'] = str(e); j['log'].append(traceback.format_exc())
    finally:
        save_state(jid)
    if j.get('estado') == 'terminado' and rearmar_instructivo:
        try:
            P = ins_paths(jid)
            if os.path.exists(P['topo']) and (INS.get(jid) or {}).get('estado') not in ('procesando', 'en cola'):
                INS[jid] = dict(estado='en cola', mensaje='En cola…', progreso=0.0)
                gen_instructivo(jid)
                return
        except Exception:
            import traceback
            j['log'].append('No se pudo volver a armar el instructivo: ' + traceback.format_exc()); save_state(jid)
    # plano de EPLAN: el mismo PDF trae la hoja de bandejas; se arma el instructivo solo (si todavia no hay uno)
    if j.get('estado') == 'terminado' and j.get('eplan'):
        try:
            P = ins_paths(jid)
            if not os.path.exists(P['json']) and (INS.get(jid) or {}).get('estado') not in ('procesando', 'en cola'):
                usar_mismo_pdf(jid)
        except Exception:
            import traceback
            j['log'].append('No se pudo armar el instructivo: ' + traceback.format_exc()); save_state(jid)


def usar_mismo_pdf(jid):
    """el PDF del plano (EPLAN) se usa tambien como topografico del trabajo y se arma el instructivo"""
    P = ins_paths(jid); s = load_state(jid) or {}
    src = os.path.join(P['dir'], s['archivo'])
    if not os.path.exists(P['topo']) or os.path.getsize(P['topo']) != os.path.getsize(src):
        shutil.copyfile(src, P['topo'] + '.tmp'); os.replace(P['topo'] + '.tmp', P['topo'])
        if os.path.exists(P['layout']):
            os.remove(P['layout'])
    nombre = (s.get('nombre') or s['archivo']) + ' (hoja de bandejas)'
    if jid in JOBS:
        JOBS[jid]['topo_nombre'] = nombre; save_state(jid)
    else:
        s['topo_nombre'] = nombre; write_json(os.path.join(P['dir'], 'estado.json'), s)
    INS[jid] = dict(estado='en cola', mensaje='En cola…', progreso=0.0)
    threading.Thread(target=gen_instructivo, args=(jid, None, True, True), daemon=True).start()


@app.before_request
def solo_local():
    ok_hosts = {f'127.0.0.1:{PORT}', f'localhost:{PORT}'}
    if request.host not in ok_hosts:
        abort(403)
    origin = request.headers.get('Origin')
    if request.method in ('POST', 'DELETE', 'PUT') and origin and origin not in {f'http://{h}' for h in ok_hosts}:
        abort(403)


def html_estatico(nombre):
    # version en los .js/.css (fecha del archivo): al actualizar el programa el navegador no usa lo viejo guardado
    with open(os.path.join(HERE, 'web', nombre), encoding='utf-8') as f:
        html = f.read()
    ver = lambda m: f"/static/{m.group(1)}?v={int(os.path.getmtime(os.path.join(HERE, 'web', m.group(1))))}"
    # (tambien los de una subcarpeta: /static/nucleo/wpc_core.js)
    html = re.sub(r'/static/((?:[\w.-]+/)*[\w.-]+\.(?:js|css))(?=")', lambda m: ver(m) if os.path.exists(os.path.join(HERE, 'web', m.group(1))) else m.group(0), html)
    r = app.response_class(html, mimetype='text/html')
    r.headers['Cache-Control'] = 'no-cache'
    return r


@app.get('/')
def index():
    return html_estatico('index.html')


@app.post('/api/procesar')
def procesar():
    f = request.files.get('plano')
    if not f or not f.filename.lower().endswith('.pdf'):
        return jsonify(error='Elige un archivo PDF'), 400
    head = f.stream.read(1024); f.stream.seek(0)
    if b'%PDF-' not in head:
        return jsonify(error='El archivo no es un PDF válido'), 400
    jid = uuid.uuid4().hex[:12]
    d = os.path.join(WORK, jid)
    name = os.path.basename(f.filename.replace('\\', '/'))
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')
    stem, ext = os.path.splitext(safe)
    safe = (stem[:150] or 'plano') + '.pdf'
    try:
        os.makedirs(d); path = os.path.join(d, safe); f.save(path)
    except Exception as e:
        shutil.rmtree(d, ignore_errors=True)
        return jsonify(error='No se pudo guardar el archivo: ' + str(e)), 500
    opts = dict(pdf=request.form.get('pdf', '1') == '1', excel=request.form.get('excel', '1') == '1',
                ocr=request.form.get('ocr', '1') == '1')
    JOBS[jid] = dict(id=jid, nombre=re.sub(r'[\x00-\x1f]', '', name), archivo=safe, estado='en cola', progreso=0.0,
                     mensaje='En cola…', log=[], creado=datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
                     ts=time.time(), tam=os.path.getsize(path), opciones=opts)
    save_state(jid)
    threading.Thread(target=run_job, args=(jid, path, opts), daemon=True).start()
    return jsonify(id=jid)


@app.post('/api/trabajo/<jid>/reprocesar')
def reprocesar(jid):
    """vuelve a procesar el mismo plano con la version actual del programa"""
    d = job_dir(jid); s = load_state(jid)
    if not s or not s.get('archivo'):
        abort(404)
    if (JOBS.get(jid) or {}).get('estado') in ('procesando', 'en cola'):
        return jsonify(error='Ya se está procesando'), 409
    try:
        if os.path.exists(os.path.join(d, 'resultado.json')):
            os.remove(os.path.join(d, 'resultado.json'))
    except OSError:
        return jsonify(error='No se pudo reemplazar el resultado anterior'), 409
    opts = s.get('opciones') or dict(pdf=True, excel=True, ocr=True)
    JOBS[jid] = {k: v for k, v in s.items() if k not in ('error', 'inicio', 'transcurrido')} | dict(
        estado='en cola', progreso=0.0, mensaje='En cola…', log=[], opciones=opts)
    save_state(jid)
    threading.Thread(target=run_job, args=(jid, os.path.join(d, s['archivo']), opts, True), daemon=True).start()
    return jsonify(id=jid)


@app.get('/api/trabajo/<jid>/estado')
def estado(jid):
    job_dir(jid)
    s = load_state(jid)
    if not s:
        abort(404)
    out = {k: v for k, v in s.items() if k != 'log'}
    out['log'] = s.get('log', [])[-12:]
    if s.get('estado') == 'procesando' and s.get('inicio'):
        out['transcurrido'] = round(time.time() - s['inicio'])
    return jsonify(out)


@app.get('/api/trabajo/<jid>/resultado')
def resultado(jid):
    p = os.path.join(job_dir(jid), 'resultado.json')
    if not os.path.exists(p):
        abort(404)
    return send_file(p, mimetype='application/json')


@app.get('/api/trabajo/<jid>/descargar/<tipo>')
def descargar(jid, tipo):
    d = job_dir(jid); s = load_state(jid) or {}
    name = {'pdf': s.get('pdf'), 'excel': s.get('excel'), 'original': s.get('archivo')}.get(tipo)
    if not name or not os.path.exists(os.path.join(d, name)):
        abort(404)
    return send_file(os.path.join(d, name), as_attachment=True, download_name=name)


@app.get('/api/trabajo/<jid>/pagina/<int:n>.png')
def pagina(jid, n):
    d = job_dir(jid); s = load_state(jid) or {}
    cache = os.path.join(d, f'pag_{n:03d}.png')
    if not s.get('archivo'):
        abort(404)
    with PDFIUM_LOCK:
        if not os.path.exists(cache):
            render_page(os.path.join(d, s['archivo']), n, cache)
    r = send_file(cache, mimetype='image/png')
    r.headers['Cache-Control'] = 'max-age=86400'
    return r


def render_page(pdf, n, cache):
    """PNG de la hoja n: MediaBox completa y sin /Rotate (mismo sistema de coordenadas que los recuadros)"""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    try:
        if not 1 <= n <= len(doc):
            abort(404)
        pg = doc[n - 1]
        try:
            pg.set_rotation(0)
            mb = pg.get_mediabox(); pg.set_cropbox(*mb)
            w, h = mb[2] - mb[0], mb[3] - mb[1]
            scale = min(2.2, 5200 / max(w, h))
            img = pg.render(scale=scale).to_pil().convert('RGB').quantize(colors=48)
        finally:
            pg.close()
    finally:
        doc.close()
    img.save(cache + '.tmp.png', optimize=True)
    os.replace(cache + '.tmp.png', cache)


@app.get('/api/trabajos')
def trabajos():
    out = []
    for jid in os.listdir(WORK):
        if not re.fullmatch(r'[0-9a-f]{12}', jid):
            continue
        try:
            s = load_state(jid)
        except Exception:
            s = None
        if s and s.get('id'):
            e = {k: s.get(k) for k in ('id', 'nombre', 'estado', 'creado', 'cables', 'revisar', 'segundos', 'pdf', 'excel')}
            e['_ts'] = s.get('ts') or os.path.getmtime(os.path.join(WORK, jid))
            out.append(e)
    out.sort(key=lambda e: e['_ts'], reverse=True)
    for e in out:
        e.pop('_ts')
    return jsonify(out)


@app.delete('/api/trabajo/<jid>')
def borrar(jid):
    d = job_dir(jid)
    j = JOBS.get(jid)
    if j and j.get('estado') in ('procesando', 'en cola'):
        return jsonify(error='Ese plano se está procesando; espera a que termine.'), 409
    import gc
    for intento in range(3):
        shutil.rmtree(d, ignore_errors=True)
        if not os.path.exists(d):
            break
        gc.collect(); time.sleep(0.4)
    if os.path.exists(d):
        # quedaron archivos: normalmente abiertos en Excel o Acrobat
        return jsonify(error='No se pudo borrar todo: cierra el PDF o el Excel de este plano y vuelve a intentarlo.'), 409
    JOBS.pop(jid, None)
    return jsonify(ok=True)


@app.post('/api/trabajo/<jid>/abrir-carpeta')
def abrir_carpeta(jid):
    d = job_dir(jid); s = load_state(jid) or {}
    target = os.path.join(d, s.get('excel') or s.get('pdf') or s.get('archivo', ''))
    subprocess.Popen(['explorer', '/select,', os.path.normpath(target)])
    return jsonify(ok=True)


@app.post('/api/salir')
def salir():
    threading.Timer(0.4, lambda: os._exit(0)).start()
    return jsonify(ok=True)


# ------------------------------------------------------------------ instructivo de cableado
INS = {}   # jid -> estado de la generacion del instructivo


def ins_paths(jid):
    d = job_dir(jid)
    return dict(dir=d, topo=os.path.join(d, 'topografico.pdf'), json=os.path.join(d, 'instructivo.json'),
                layout=os.path.join(d, 'layout.json'), fotos=os.path.join(d, 'fotos'))


def write_json(path, data):
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(path + '.tmp', path)


def leer_json(path):
    """el JSON del archivo, o None si no existe o esta roto"""
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


PROY_LOCK = threading.Lock()   # escritura de instructivo.json desde la pestaña del proyector y desde la ventana principal


def gen_instructivo(jid, overrides=None, relayout=False, topo_nuevo=False):
    """topo_nuevo: se acaba de cargar el topografico. Las salidas a LI / LD elegidas con el anterior no sirven (son
    puntos de otro dibujo): se borran y la web pregunta una vez por donde salen ('preguntar')"""
    st = INS[jid]
    try:
        P = ins_paths(jid); s = load_state(jid) or {}
        with RUN_LOCK:
            from core import process
            from instructivo import build, componentes_panel, known_tags, leer_json_trabajo, leer_bornes_manuales
            import topo
            st.update(estado='procesando', mensaje='Leyendo el plano eléctrico…', progreso=0.05)
            def lg(m):
                st['mensaje'] = m; st['progreso'] = min(0.5, st['progreso'] + 0.025)
            res = process(os.path.join(P['dir'], s['archivo']), log=lg)
            # un layout.json leido con otra version del lector del topografico se vuelve a leer, para que el trabajo
            # tome los arreglos del lector sin volver a subir el topografico (lo del usuario: 'Componentes y orden',
            # puntos ajustados en el visor y marcas, esta en instructivo.json y se aplica igual)
            if not relayout and os.path.exists(P['layout']) and not topo.layout_al_dia(P['layout']):
                relayout = True
            if relayout or not os.path.exists(P['layout']):
                st.update(mensaje='Leyendo el topográfico…', progreso=0.55)
                lay = topo.layout(P['topo'], known_tags(res), log=lambda m: st.update(mensaje=m))
                write_json(P['layout'], lay)
            with open(P['layout'], encoding='utf-8') as f:
                lay = json.load(f)
            old = {}
            if os.path.exists(P['json']):
                with open(P['json'], encoding='utf-8') as f:
                    old = json.load(f)
            ov = overrides if overrides is not None else old.get('overrides', {})
            for tag, o in (ov or {}).items():
                c = lay['comp'].setdefault(tag, dict(x=0, y=0, leido=''))
                c['ubic'] = o.get('ubic', c.get('ubic', 'LI'))
                if c['ubic'] == 'BANDEJA':
                    c['fila'] = int(o.get('fila') or c.get('fila') or 1)
                    if o.get('x') not in (None, ''):
                        c['x'] = float(o['x'])
                    if o.get('lado') in ('ARRIBA', 'ABAJO'):     # todos sus bornes se cablean por ese lado
                        c['lado'] = o['lado']
            # correcciones de la verificacion contra el funcional (correcciones.json del trabajo). Un archivo roto
            # (JSON invalido) no frena el instructivo: se ignora con el aviso 'correcciones.json ilegible, se ignora'
            avisos_archivos = []
            corr = leer_json_trabajo(os.path.join(P['dir'], 'correcciones.json'), avisos_archivos)
            if corr is not None and not isinstance(corr, dict):
                avisos_archivos.append('correcciones.json ilegible, se ignora (no es un objeto JSON)')
                corr = None
            if corr:
                for tag, c in (corr.get('componentes') or {}).items():
                    try:
                        lay['comp'][tag] = dict(lay['comp'].get(tag) or {}, ubic='BANDEJA', fila=int(c['fila']), x=float(c['x']),
                                                y=float(c['y']), leido=tag)
                    except (TypeError, KeyError, ValueError):
                        avisos_archivos.append(f"correcciones.json: el componente '{tag}' no tiene fila, x e y; se ignora")
                # (antes del mapeo: los conductores agregados a mano tambien se ubican en el topografico)
                for k in ('agregar', 'pendientes_agregar', 'pendientes_texto', 'pendientes_quitar', 'sueltos_quitar', 'accesorios'):
                    lay[k] = corr.get(k) or ([] if k != 'pendientes_texto' else {})
            # (antes del mapeo: un punto ajustado a mano en el visor manda, y su texto no se renombra)
            lay['bornes_usuario'] = old.get('bornes_usuario') or {}
            # puntos exactos de bornes: 1) el mapeo automatico (bornes/, con cache en bornes_auto.json);
            # 2) mandan los manuales del trabajo: bornes.json y los 'bornes' de correcciones.json;
            # 3) mandan sobre todo los ajustados a mano en el visor (bornes_usuario)
            st.update(mensaje='Ubicando cada borne en el topográfico…', progreso=0.7)
            try:
                if getattr(res, 'eplan', False) and lay.get('eplan'):   # EPLAN con sus bandejas: mapeo verificado del producto (dato)
                    import eplan
                    mapeo = eplan.aplicar_puntos(res, lay, P['dir'])
                else:
                    import bornes as mapeo_bornes
                    mapeo = mapeo_bornes.aplicar_al_layout(res, lay, P['dir'], P['topo'], usuario=lay['bornes_usuario'])
            except Exception as e:      # el mapeo nunca frena el instructivo: se arma como sin mapeo
                import traceback
                mapeo = dict(error=f'{type(e).__name__}: {e}', detalle=traceback.format_exc(), avisos=[f'el mapeo automatico de bornes fallo ({e})'],
                             n_puntos={}, modelos={}, usados=0)
                for k in ('bornes', 'renombrar', 'bornes_conf', 'bornes_nota', 'bornes_salida', 'renombrar_auto'):
                    lay.pop(k, None)
                # solo los manuales del trabajo (bornes.json y los 'bornes' de correcciones.json); un archivo roto se ignora
                lay['bornes'], lay['renombrar'] = leer_bornes_manuales(P['dir'], mapeo['avisos'], corr=corr if corr else {})
            mapeo = mapeo if isinstance(mapeo, dict) else {}
            mapeo['avisos'] = list(dict.fromkeys(avisos_archivos + list(mapeo.get('avisos') or [])))
            lay['estaciones'] = old.get('estaciones') or {}
            lay['estacion'] = old.get('estacion') or 'E6'
            lay['estacion_auto'] = old.get('estacion_auto') or {'seccion_min': 35, 'estacion': 'E8'}   # 35 mm2 -> gabinete
            # salidas a LI / LD elegidas a mano (editor de salidas)
            lay['salidas'] = {'grupos': [], 'preguntar': True} if topo_nuevo else (old.get('salidas') or {})
            # cables quitados a mano del instructivo (no se cablean en esta estacion): siguen afuera
            lay['quitados'] = old.get('quitados') if isinstance(old.get('quitados'), list) else []
            st.update(mensaje='Armando el instructivo…', progreso=0.92)
            ins = build(res, lay)
            ins['bornes_usuario'] = lay['bornes_usuario']
            # textos con el ARRIBA/ABAJO cambiado respecto del funcional (lado fisico del borne): van con el mapeo
            mapeo['lado_fisico'] = ins.pop('lado_fisico', None) or []
            ins['mapeo'] = mapeo
            hechos_acc = {a.get('id') for a in old.get('accesorios') or [] if a.get('hecho')}
            for a in ins.get('accesorios') or []:
                if a.get('id') in hechos_acc:
                    a['hecho'] = True
            # estacion E8 (gabinete): bandejas laterales y puerta / placa; se conservan sus marcas de cableado y la entrada a
            # las laterales y la bisagra elegidas (recorridos). Con un topografico nuevo los recorridos se borran (son puntos
            # de otro dibujo) y el asistente de la estacion 8 vuelve a preguntar (como las salidas a LI / LD de E6).
            # (despues de instructivo.build: es solo de E8)
            lay['recorridos_e8'] = None if topo_nuevo else (old.get('estacion8') or {}).get('recorridos')
            # producto (antes de E8: el ruteo a mano de E8 se guarda por producto y topografico; va en ins['producto'] mas abajo)
            prod_ins = producto_nuevo(P, s, res, lay, old, topo_nuevo)
            # ruteo a mano de E8 guardado en el trabajo (producto sin confirmar); con un topografico nuevo no sirve (son puntos
            # de otro dibujo)
            mano_local = None if topo_nuevo else (old.get('estacion8') or {}).get('mano_trabajo')
            try:
                import estacion8
                import estacion8_mano
                # puntos de los bornes de las laterales: el motor de bornes por cada lateral (claves aparte del layout,
                # bornes_e8; cache en bornes_e8_auto.json; sin renombrar textos: E6 no cambia). Los ajustados a mano en
                # el visor de E8 van en bornes_usuario, como los de E6, y mandan
                st.update(mensaje='Ubicando los bornes de las bandejas laterales…', progreso=0.95)
                mapeo_e8 = estacion8.mapear_bornes(res, lay, P['dir'], P['topo'])
                e8 = estacion8.build(res, lay, ins)
                e8['mapeo'] = mapeo_e8
                # ruteo a mano por grupos (E8-6): lo dibujado y corregido por el taller, guardado por producto
                estacion8_mano.cargar_y_aplicar(e8, prod_ins, mano_local, trabajo=jid, archivo=s.get('nombre') or s.get('archivo'))
                vivas = {l['clave'] for L in e8['laterales'] for p in L['pasos'] for l in p['lineas']} | {x['clave'] for g in e8['afuera'] for x in g['cables']}
                e8['hechos'] = [k for k in ((old.get('estacion8') or {}).get('hechos') or []) if k in vivas]
            except Exception as e:      # E8 nunca frena el instructivo de E6
                import traceback
                rec = lay['recorridos_e8'] if isinstance(lay['recorridos_e8'], dict) else {'preguntar': True, 'bisagra': None, 'vistas': {}}
                e8 = dict(version=0, laterales=[], afuera=[], hechos=(old.get('estacion8') or {}).get('hechos') or [], recorridos=rec,
                          avisos=[f'no se pudo armar la estación E8 ({type(e).__name__}: {e})'], detalle=traceback.format_exc())
                if mano_local:
                    e8['mano_trabajo'] = mano_local
            ins['estacion8'] = e8
            ins['estaciones'] = lay['estaciones']
            ins['estacion'] = lay['estacion']
            ins['estacion_auto'] = lay['estacion_auto']
            ins['salidas'] = lay['salidas']
            ins['auditoria'] = old.get('auditoria') or {}
            ins['wpc'] = old.get('wpc') or {}     # lista WPC: largos y colores a mano, cortes de etapa, excluidos
            ins['proyector'] = old.get('proyector') or {}   # pestaña 📽 Proyector: orificios marcados, calibración y ventana
            # producto (código SAP, plano y revisión): lo detectado con el catálogo y lo confirmado a mano (producto.json
            # manda: no se pisa al regenerar). 'documento' sigue siendo el de las reglas por producto de la lista WPC
            ins['producto'] = prod_ins
            # conservar las fotos de la version anterior (paso identificado por su primer cable)
            prev = {}
            for p_ in old.get('pasos', []):
                if p_.get('lineas'):
                    prev[(p_['lineas'][0]['num'], p_['lineas'][0]['origen'])] = p_
            for p_ in ins['pasos']:
                k = (p_['lineas'][0]['num'], p_['lineas'][0]['origen'])
                if k in prev:
                    p_['foto'] = prev[k].get('foto')
            # conservar lo que ya se marco como cableado (mismo cable y mismo origen o destino, sin mirar ARRIBA/ABAJO
            # porque el lado puede haberse corregido con el punto exacto)
            # (el par de puntas sin importar el orden; si el cable tiene un solo tramo, alcanza con el numero)
            sin_lado = lambda t: re.sub(r' (ARRIBA|ABAJO)$', '', t or '')
            par = lambda l: frozenset((sin_lado(l['origen']), sin_lado(l['destino'])))
            viejas = [l for p_ in old.get('pasos', []) for l in p_.get('lineas', [])]
            nuevas = [l for p_ in ins['pasos'] for l in p_['lineas']]
            cuenta = lambda ls, n: sum(1 for l in ls if l['num'] == n)
            hechos = {(l['num'], par(l)) for l in viejas if l.get('hecho')}
            # por numero solo si las puntas siguen en los mismos aparatos (cambio de pin o de lado): si una punta cambio
            # de aparato, de modulo de rele o entre LI/LD y la bandeja, el cable hay que volver a cablearlo
            tags = lambda l: frozenset(t.split(' ')[0] for t in (l['origen'] or '', l['destino'] or ''))
            hechos_num = {l['num']: tags(l) for l in viejas if l.get('hecho') and cuenta(viejas, l['num']) == 1}
            for l in nuevas:
                if (l['num'], par(l)) in hechos or (l['num'] in hechos_num and cuenta(nuevas, l['num']) == 1
                                                     and tags(l) == hechos_num[l['num']]):
                    l['hecho'] = True
            ins.update(componentes=componentes_panel(res, lay), overrides=ov or {},
                       generado=datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
                       topografico=s.get('topo_nombre', 'topografico.pdf'), hoja_topo=lay.get('pag'), editado=False)
            write_json(P['json'], ins)
            st.update(estado='terminado', mensaje='Listo', progreso=1.0)
    except Exception as e:
        import traceback
        st.update(estado='error', error=str(e), detalle=traceback.format_exc())


@app.post('/api/trabajo/<jid>/topografico')
def subir_topografico(jid):
    P = ins_paths(jid)
    f = request.files.get('plano')
    if not f or not f.filename.lower().endswith('.pdf'):
        return jsonify(error='Elige el plano topográfico en PDF'), 400
    head = f.stream.read(1024); f.stream.seek(0)
    if b'%PDF-' not in head:
        return jsonify(error='El archivo no es un PDF válido'), 400
    if (INS.get(jid) or {}).get('estado') in ('procesando', 'en cola'):
        return jsonify(error='Ya se está generando'), 409
    f.save(P['topo'])
    if os.path.exists(P['layout']):
        os.remove(P['layout'])
    s = load_state(jid) or {}
    s['topo_nombre'] = os.path.basename(f.filename)
    if jid in JOBS:
        JOBS[jid]['topo_nombre'] = s['topo_nombre']; save_state(jid)
    else:
        write_json(os.path.join(P['dir'], 'estado.json'), s)
    INS[jid] = dict(estado='en cola', mensaje='En cola…', progreso=0.0)
    threading.Thread(target=gen_instructivo, args=(jid, None, True, True), daemon=True).start()
    return jsonify(ok=True)


@app.post('/api/trabajo/<jid>/topografico/mismo')
def topografico_mismo(jid):
    """plano de EPLAN: usar las bandejas del mismo PDF como topografico"""
    ins_paths(jid); s = load_state(jid) or {}
    if not s.get('archivo'):
        abort(404)
    if not s.get('eplan'):          # en AutoCAD el topografico es otro PDF: copiar el funcional no sirve
        return jsonify(error='Solo para planos de EPLAN'), 400
    if (INS.get(jid) or {}).get('estado') in ('procesando', 'en cola'):
        return jsonify(error='Ya se está generando'), 409
    usar_mismo_pdf(jid)
    return jsonify(ok=True)


@app.post('/api/trabajo/<jid>/instructivo/regenerar')
def regenerar_instructivo(jid):
    P = ins_paths(jid)
    if not os.path.exists(P['topo']):
        return jsonify(error='Falta el plano topográfico'), 400
    if (INS.get(jid) or {}).get('estado') in ('procesando', 'en cola'):
        return jsonify(error='Ya se está generando'), 409
    body = request.get_json(silent=True) or {}
    INS[jid] = dict(estado='en cola', mensaje='En cola…', progreso=0.0)
    threading.Thread(target=gen_instructivo, args=(jid, body.get('overrides'), bool(body.get('releer'))), daemon=True).start()
    return jsonify(ok=True)


@app.get('/api/trabajo/<jid>/instructivo/estado')
def estado_instructivo(jid):
    P = ins_paths(jid)
    st = {k: v for k, v in (INS.get(jid) or {}).items() if k != 'detalle'}
    st['hay_topo'] = os.path.exists(P['topo']); st['hay_instructivo'] = os.path.exists(P['json'])
    st['eplan'] = bool((load_state(jid) or {}).get('eplan'))
    return jsonify(st)


def producto_de(lay):
    """documento y revision del rotulo (planos de EPLAN), para las reglas por producto de la lista WPC (wpc.json →
    reemplazos[documento]); en los planos de AutoCAD no hay. (Lo que habia antes del producto: queda si falla la deteccion)"""
    e = ((lay or {}).get('eplan') or {}) if isinstance(lay, dict) else {}
    return dict(documento=e.get('documento'), revision=e.get('revision'))


# ------------------------------------------------------------------ producto: codigo SAP, plano y revision (planocables.producto)
def leer_catalogo():
    """catalogo de productos del taller (programa/productos.json); {} si no esta o esta roto"""
    c = leer_json(PRODUCTOS)
    return c if isinstance(c, dict) else {}


def leer_confirmado(d):
    """producto.json del trabajo (el producto confirmado a mano) o None"""
    c = leer_json(os.path.join(d, 'producto.json'))
    return c if isinstance(c, dict) and PR.codigo_valido(c.get('codigo')) else None


def titulo_pdf(path):
    """/Title de los metadatos del PDF, o None (barato: no lee las hojas)"""
    try:
        import pypdf
        r = pypdf.PdfReader(path)
        if r.is_encrypted:
            r.decrypt('')
        t = (r.metadata or {}).get('/Title')
        return (str(t).strip() or None) if t is not None else None
    except Exception:
        return None


def detectar_producto(res, nombre):
    """lo que dice el plano funcional ya leido sobre el producto: rotulo de cada hoja, /Title y nombre del archivo"""
    pags = [dict(index=p['index'], lines=p.get('lines') or [], cajetin=(p.get('meta') or {}).get('cajetin')) for p in res.pages]
    ep = dict(documento=getattr(res, 'documento', None), revision=getattr(res, 'revision', None)) if getattr(res, 'eplan', False) else None
    return PR.producto_del_plano(pags, titulo_pdf(res.path), os.path.basename(nombre or res.path), eplan=ep)


def topografico_de(P, s, lay):
    """{numero, revision, fuente, hoja} del topografico del trabajo (None si todavia no se cargo). EPLAN: el rotulo de
    las bandejas ('mismo_pdf' si es el PDF del funcional: «Usar las bandejas de este mismo PDF»)"""
    if not os.path.exists(P['topo']):
        return None
    lay = lay if isinstance(lay, dict) else {}
    e = lay.get('eplan') if isinstance(lay.get('eplan'), dict) else None
    if e:
        fun = os.path.join(P['dir'], s.get('archivo') or '')
        mismo = os.path.isfile(fun) and os.path.getsize(fun) == os.path.getsize(P['topo'])
        t = dict(numero=e.get('documento'), revision=e.get('revision'), fuente='mismo_pdf' if mismo else 'rotulo')
        if mismo:
            t['mismo_pdf'] = True
    else:
        t = PR.topografico_del_pdf(titulo_pdf(P['topo']), s.get('topo_nombre'))
    if lay.get('pag'):
        t['hoja'] = lay['pag']
    return t


def marcar_pregunta(prod, preguntado):
    """'preguntar': el asistente de la web pregunta una sola vez (sin confirmar y con una deteccion dudosa o avisos)"""
    if preguntado:
        prod['preguntado'] = True
    prod['preguntar'] = PR.hay_que_preguntar(prod) and not preguntado
    return prod


def producto_nuevo(P, s, res, lay, old, topo_nuevo):
    """ins['producto'] al regenerar: lo detectado en el plano recien leido, el topografico, el catalogo y producto.json.
    Ya se pregunto una vez: no se vuelve a preguntar (salvo con un topografico nuevo, como las salidas)"""
    try:
        det = detectar_producto(res, s.get('nombre') or s.get('archivo'))
        prod = dict(PR.combinar(det, topografico_de(P, s, lay), leer_catalogo(), leer_confirmado(P['dir'])), detectado=det)
    except Exception as e:      # el producto nunca frena el instructivo
        return dict(producto_de(lay), error=f'{type(e).__name__}: {e}', avisos=[f'no se pudo leer el producto del plano ({e})'])
    return marcar_pregunta(prod, bool((old.get('producto') or {}).get('preguntado')) and not topo_nuevo)


def producto_actual(P, s, ins=None):
    """el producto con lo que ya esta en el disco, sin volver a leer el plano: lo detectado (instructivo.json o
    resultado.json; en un trabajo viejo, solo el /Title y el nombre del archivo), el topografico, el catalogo y
    producto.json. Sin 'preguntar' (lo pone quien lo llama)"""
    ins = ins if isinstance(ins, dict) else (leer_json(P['json']) or {})
    det = (ins.get('producto') or {}).get('detectado') if isinstance(ins.get('producto'), dict) else None
    if not isinstance(det, dict):
        det = (((leer_json(os.path.join(P['dir'], 'resultado.json')) or {}).get('producto')) or {}).get('detectado')
    lay = leer_json(P['layout'])
    if not isinstance(det, dict):
        e = (lay or {}).get('eplan') if isinstance(lay, dict) and isinstance(lay.get('eplan'), dict) else None
        fun = os.path.join(P['dir'], s.get('archivo') or '')
        det = PR.producto_del_plano([], titulo_pdf(fun) if os.path.isfile(fun) else None,
                                    os.path.basename(s.get('nombre') or s.get('archivo') or ''),
                                    eplan=dict(documento=e.get('documento'), revision=e.get('revision')) if e else None)
    return dict(PR.combinar(det, topografico_de(P, s, lay), leer_catalogo(), leer_confirmado(P['dir'])), detectado=det)


def texto_catalogo(cat):
    """productos.json legible: un producto por renglon (el diff de git se lee)"""
    prods = cat.get('productos') or {}
    otras = [f' {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}' for k, v in cat.items() if k != 'productos']
    filas = [f'  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}' for k, v in prods.items()]
    return '{\n' + ''.join(o + ',\n' for o in otras) + ' "productos": {\n' + ',\n'.join(filas) + '\n }\n}\n'


def sumar_al_catalogo(codigo, nombre, prod):
    """el producto confirmado queda en el catalogo con los alias de este trabajo: el plano funcional (o el documento de
    EPLAN), el topografico y el codigo que dice el plano si no es el del producto. El plano funcional, el documento y
    el codigo del plano se sacan de otro producto que los tuviera (el taller los confirmo para este)"""
    eplan = bool((prod.get('detectado') or {}).get('eplan'))
    fun, top = prod.get('funcional') or {}, prod.get('topografico') or {}
    mueve = collections.defaultdict(list)       # alias que pasan a este producto
    if fun.get('numero'):
        mueve['documentos' if eplan else 'planos'].append(fun['numero'] if eplan else PR.nucleo(fun['numero']))
    rot = prod.get('codigo_rotulo')
    if PR.codigo_valido(rot) and rot != codigo:
        mueve['codigo_rotulo'].append(rot)
    suma = collections.defaultdict(list, {k: list(v) for k, v in mueve.items()})
    if top.get('numero') and not top.get('mismo_pdf'):      # el topografico se suma (lo pueden compartir dos productos)
        suma['documentos' if top.get('fuente') == 'rotulo' else 'planos'].append(
            top['numero'] if top.get('fuente') == 'rotulo' else PR.nucleo(top['numero']))
    clave = lambda k, x: PR.nucleo(x) if k == 'planos' else str(x).strip().upper()
    with CATALOGO_LOCK:
        cat = leer_catalogo()
        prods = cat['productos'] if isinstance(cat.get('productos'), dict) else PR.productos_de(cat)
        cat = {k: v for k, v in cat.items() if k == '_nota' or not PR.codigo_valido(k)} | {'productos': prods}
        e = prods.setdefault(codigo, {'nombre': None, 'alias': {}})
        if nombre:
            e['nombre'] = nombre
        a = e.setdefault('alias', {})
        for k in ('planos', 'documentos', 'codigo_rotulo'):
            a[k] = list(a.get(k) or [])
        for c, o in prods.items():
            oa = (o.get('alias') or {}) if c != codigo else {}
            for k, vs in mueve.items():
                if isinstance(oa.get(k), list):
                    oa[k] = [x for x in oa[k] if clave(k, x) not in {clave(k, v) for v in vs}]
        for k, vs in suma.items():
            for v in vs:
                if clave(k, v) not in {clave(k, x) for x in a[k]}:
                    a[k].append(v)
        with open(PRODUCTOS + '.tmp', 'w', encoding='utf-8') as f:
            f.write(texto_catalogo(cat))
        os.replace(PRODUCTOS + '.tmp', PRODUCTOS)


@app.get('/api/trabajo/<jid>/producto')
def ver_producto(jid):
    """el producto del trabajo (como queda hoy), las sugerencias de codigo y los productos del catalogo"""
    P = ins_paths(jid); s = load_state(jid) or {}
    ins = leer_json(P['json'])
    prod = producto_actual(P, s, ins)
    viejo = (ins or {}).get('producto') if isinstance(ins, dict) else None
    marcar_pregunta(prod, bool(isinstance(viejo, dict) and viejo.get('preguntado')))
    cat = leer_catalogo()
    return jsonify(producto=prod, sugerencias=PR.sugerencias(prod, cat),
                   catalogo=[dict(codigo=c, nombre=e.get('nombre')) for c, e in sorted(PR.productos_de(cat).items())])


@app.put('/api/trabajo/<jid>/producto')
def guardar_producto(jid):
    """{codigo, nombre}: confirma el producto del trabajo. Guarda producto.json (manda al regenerar), suma los alias al
    catalogo y actualiza ins['producto'] en instructivo.json (con el lock del PUT del instructivo: el visor lo ve sin
    regenerar). {preguntado: true} (sin codigo): el asistente ya pregunto y se cerro sin confirmar"""
    P = ins_paths(jid); s = load_state(jid) or {}
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or ('codigo' not in data and data.get('preguntado') is not True):
        return jsonify(error='Datos inválidos'), 400
    confirma = 'codigo' in data
    if confirma:
        codigo = str(data.get('codigo') or '').strip()
        nombre = re.sub(r'\s+', ' ', str(data.get('nombre') or '')).strip()[:80] or None
        if not PR.codigo_valido(codigo):
            return jsonify(error='El código de producto es el número de SAP con su sufijo, como 75286-1'), 400
        write_json(os.path.join(P['dir'], 'producto.json'), dict(codigo=codigo, nombre=nombre, confirmado=True,
                                                               fecha=datetime.datetime.now().strftime('%d/%m/%Y %H:%M')))
    with PROY_LOCK:
        ins = leer_json(P['json'])
        prod = producto_actual(P, s, ins)
        if confirma:
            sumar_al_catalogo(codigo, nombre, prod)
            prod = producto_actual(P, s, ins)       # (con el catalogo nuevo)
        marcar_pregunta(prod, True)
        if isinstance(ins, dict):
            ins['producto'] = prod
            write_json(P['json'], ins)
    return jsonify(ok=True, producto=prod)


# ------------------------------------------------------------------ parametros de la lista WPC (wpc.json)
TIPOS_WPC = {'numero', 'si_no', 'texto', 'regex', 'opcion', 'lista', 'colores', 'reemplazos', 'marcador', 'largos'}
_FALTA = object()


def version_config_wpc(datos):
    """version del archivo (para no pisar lo que otro guardo mientras tanto): sha1 de los bytes"""
    import hashlib
    return hashlib.sha1(datos).hexdigest()[:16]


def _ruta(o, clave):
    for k in clave.split('.'):
        if not isinstance(o, dict) or k not in o:
            return _FALTA
        o = o[k]
    return o


def _invalido_wpc(p, v, todos):
    """que tiene de malo el valor v del parametro p (None si esta bien). todos: nivel «todos los productos»"""
    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and abs(x) != float('inf')
    num_o_nada = lambda x: x is None or num(x)
    t = p['tipo']
    if t == 'numero':
        if not num(v):
            return f'tiene que ser un número ({v!r})'
        if num(p.get('minimo')) and v < p['minimo']:
            return f"tiene que ser {p['minimo']} o más ({v})"
    elif t == 'si_no':
        if not isinstance(v, bool):
            return f'tiene que ser sí o no ({v!r})'
    elif t in ('texto', 'regex'):
        if not isinstance(v, str) or len(v) > 2000:
            return 'tiene que ser un texto'
    elif t == 'opcion':
        ops = [o.get('valor') if isinstance(o, dict) else o for o in p['opciones']] if isinstance(p.get('opciones'), list) else None
        if not isinstance(v, str) or (ops is not None and v not in ops):
            return f'opción desconocida ({v!r})'
    elif t == 'lista':
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            return 'tiene que ser una lista de textos'
    elif t == 'colores':
        if not isinstance(v, dict) or not all(isinstance(k, str) and isinstance(x, str) for k, x in v.items()):
            return 'tiene que ser una tabla color → código'
    elif t == 'reemplazos':
        regla = lambda r: (isinstance(r, dict) and all(isinstance(r.get(k), dict) and isinstance(r[k].get('color'), str)
                                                       and num_o_nada(r[k].get('secc')) for k in ('de', 'a'))
                           and isinstance(r.get('motivo', ''), str))
        if todos and isinstance(v, dict):       # (la forma vieja: {documento: [reglas]})
            v = [r for x in v.values() for r in (x if isinstance(x, list) else [None])]
        if not isinstance(v, list) or not all(regla(r) for r in v):
            return 'cada fila: color y sección de origen y de destino (y el motivo, si hay)'
    elif t == 'marcador':
        if not isinstance(v, list) or not all(isinstance(x, dict) and num_o_nada(x.get('desde')) and num_o_nada(x.get('hasta'))
                                              and isinstance(x.get('valor', ''), str) for x in v):
            return 'cada fila: desde y hasta (números o vacíos) y el marcador'
    elif t == 'largos':         # largo total de cada cable de comunicacion: [{cable, mm}]
        if not isinstance(v, list) or not all(isinstance(x, dict) and isinstance(x.get('cable', ''), str) and num_o_nada(x.get('mm'))
                                              and (x.get('mm') is None or x['mm'] >= 0) for x in v):
            return 'cada fila: el número del cable y su largo total en mm (0 o más)'
    return None


def validar_config_wpc(cfg):
    """errores de la configuracion de la WPC antes de guardarla ([] = esta bien): la forma de cada parametro declarado en
    'parametros', en la raiz (todos los productos) y en cada producto. Las expresiones regulares las valida la pantalla
    (con las reglas de JavaScript, que no son las de Python)"""
    if not isinstance(cfg, dict):
        return ['la configuración tiene que ser un objeto JSON']
    ps = cfg.get('parametros')
    if not isinstance(ps, list) or not all(isinstance(p, dict) and isinstance(p.get('clave'), str) and p['clave']
                                           and p.get('tipo') in TIPOS_WPC for p in ps):
        return ['«parametros» tiene que ser una lista de {clave, tipo} con un tipo conocido']
    prods = cfg.get('productos', {})
    if not isinstance(prods, dict):
        return ['«productos» tiene que ser un objeto {código de producto: {parámetros}}']
    err, niveles = [], [('todos los productos', cfg, True)]
    for k, v in prods.items():
        if not k.strip() or len(k) > 60:
            err.append(f'producto con un código inválido: {k!r}')
        elif not isinstance(v, dict) or 'productos' in v or 'parametros' in v:
            err.append(f'producto {k}: tiene que ser un objeto con los parámetros que cambian')
        else:
            niveles.append((f'producto {k}', v, False))
    for nombre, nivel, todos in niveles:
        for p in ps:
            v = _ruta(nivel, p['clave'])
            if v is _FALTA or (not todos and v in (None, '')):     # (en un producto: vacio = el de arriba)
                continue
            e = 'falta el valor' if v is None else _invalido_wpc(p, v, todos)
            if e:
                err.append(f"{nombre} → {p.get('etiqueta') or p['clave']}: {e}")
    return err[:30]


@app.get('/api/config/wpc')
def ver_config_wpc():
    """wpc.json tal cual (todos los niveles y 'parametros'), con su version en la cabecera X-Version"""
    try:
        with open(CONFIG_WPC, 'rb') as f:
            datos = f.read()
        json.loads(datos.decode('utf-8'))
    except (OSError, ValueError) as e:
        return jsonify(error=f'No se pudo leer la configuración de la WPC ({type(e).__name__})'), 500
    r = app.response_class(datos, mimetype='application/json')
    r.headers['X-Version'] = version_config_wpc(datos)
    r.headers['Cache-Control'] = 'no-cache'
    return r


@app.put('/api/config/wpc')
def guardar_config_wpc():
    """guarda wpc.json entero (panel ⚙ Parametros: «Producto» y «Todos los productos»). Valida la forma, deja un respaldo
    con fecha del anterior en respaldos_wpc/ (al lado del archivo) y escribe de forma atomica. Con X-Version: si otro
    guardo mientras tanto, 409. Sin 'parametros' en el cuerpo, se conservan los del archivo"""
    if (request.content_length or 0) > 2 * 1024 * 1024:
        return jsonify(error='La configuración es demasiado grande'), 413
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Datos inválidos'), 400
    with CONFIG_WPC_LOCK:
        try:
            with open(CONFIG_WPC, 'rb') as f:
                actual = f.read()
        except OSError:
            actual = None
        pedida = request.headers.get('X-Version')
        if pedida and actual is not None and pedida != version_config_wpc(actual):
            return jsonify(error='Otro guardó los parámetros de la WPC mientras tanto. Cerrá la lista y volvé a abrirla para ver lo último'), 409
        if 'parametros' not in data and actual is not None:
            try:
                data['parametros'] = json.loads(actual.decode('utf-8')).get('parametros')
            except (ValueError, AttributeError):
                pass
        errores = validar_config_wpc(data)
        if errores:
            return jsonify(error='Parámetros inválidos', errores=errores), 400
        respaldo = None
        if actual is not None:
            carpeta = os.path.join(os.path.dirname(CONFIG_WPC), 'respaldos_wpc')
            os.makedirs(carpeta, exist_ok=True)
            respaldo = os.path.join(carpeta, 'wpc_' + datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S_%f') + '.json')
            with open(respaldo, 'wb') as f:
                f.write(actual)
        texto = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        with open(CONFIG_WPC + '.tmp', 'w', encoding='utf-8', newline='\n') as f:
            f.write(texto)
        os.replace(CONFIG_WPC + '.tmp', CONFIG_WPC)
    # (sin jsonify, que ordena las claves: la pantalla manda de vuelta lo que recibe y el archivo quedaria reordenado)
    r = dict(ok=True, config=data, version=version_config_wpc(texto.encode('utf-8')), respaldo=os.path.basename(respaldo) if respaldo else None)
    return app.response_class(json.dumps(r, ensure_ascii=False), mimetype='application/json')


@app.get('/api/trabajo/<jid>/instructivo')
def ver_instructivo(jid):
    P = ins_paths(jid)
    ins = leer_json(P['json'])
    if not isinstance(ins, dict):
        abort(404)
    prod = ins.get('producto')
    if not isinstance(prod, dict) or 'funcional' not in prod:
        # instructivo armado antes del producto (sin 'producto', o solo con documento y revision del rotulo de EPLAN):
        # se completa al leerlo (no se escribe); el asistente pregunta si hace falta
        try:
            ins['producto'] = marcar_pregunta(producto_actual(P, load_state(jid) or {}, ins), False)
        except Exception:
            ins['producto'] = producto_de(leer_json(P['layout']))
    else:
        # producto.json manda: si el instructivo tiene otro (se confirmo mientras se regeneraba), se completa al leerlo
        conf = leer_confirmado(P['dir'])
        if conf and (prod.get('fuente') != 'confirmado' or prod.get('codigo') != conf['codigo'].strip()):
            try:
                ins['producto'] = marcar_pregunta(producto_actual(P, load_state(jid) or {}, ins), bool(prod.get('preguntado')))
            except Exception:
                pass
    return jsonify(ins)


@app.put('/api/trabajo/<jid>/instructivo')
def guardar_instructivo(jid):
    P = ins_paths(jid)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('pasos'), list):
        return jsonify(error='Datos inválidos'), 400
    data['editado'] = True
    data.pop('e8', None)          # (marcas de la vista 3D del gabinete, que ya no existe)
    with PROY_LOCK:
        # la seccion 'proyector' (orificios, calibracion y ventana de la pestaña 📽) la escribe solo /proyector, desde la
        # otra pestaña: se conserva la del disco, no la copia (vieja) que trae la ventana principal
        viejo = leer_json(P['json'])
        if isinstance(viejo, dict) and 'proyector' in viejo:
            data['proyector'] = viejo['proyector']
        else:
            data.pop('proyector', None)
        # el producto lo escriben solo el servidor (al regenerar) y PUT /producto: se conserva el del disco
        if isinstance(viejo, dict) and isinstance(viejo.get('producto'), dict) and 'funcional' in viejo['producto']:
            data['producto'] = viejo['producto']
        # el ruteo a mano de E8 guardado en el trabajo (producto sin confirmar) lo escribe solo PUT /e8/grupos
        e8v = (viejo or {}).get('estacion8') if isinstance(viejo, dict) else None
        if isinstance(data.get('estacion8'), dict):
            if isinstance(e8v, dict) and 'mano_trabajo' in e8v:
                data['estacion8']['mano_trabajo'] = e8v['mano_trabajo']
            else:
                data['estacion8'].pop('mano_trabajo', None)
        write_json(P['json'], data)
    return jsonify(ok=True)


@app.post('/api/trabajo/<jid>/instructivo/salidas')
def rutas_salidas(jid):
    """vista previa del editor de salidas a LI / LD: el recorrido de los cables que salen a un lateral con las salidas
    elegidas a mano (no guarda nada: la pestaña guarda el instructivo con las rutas y las salidas)"""
    P = ins_paths(jid)
    if not os.path.exists(P['json']):
        abort(404)
    body = request.get_json(silent=True) or {}
    lineas, salidas = body.get('lineas'), body.get('salidas') or {}
    if not isinstance(lineas, list) or not all(isinstance(l, dict) for l in lineas) or not isinstance(salidas, dict):
        return jsonify(error='Datos inválidos'), 400
    with open(P['json'], encoding='utf-8') as f:
        topo = json.load(f).get('topo') or {}
    if not topo.get('ductos'):
        return jsonify(error='El topográfico no tiene cablecanales para rutear'), 400
    from instructivo import rutear_salidas
    return jsonify(rutas=rutear_salidas(lineas, topo, salidas.get('grupos') or []))


@app.post('/api/trabajo/<jid>/e8/recorridos')
def rutas_e8(jid):
    """vista previa del editor de entradas de la estacion 8 (asistente y boton «Entrada / salida»): el recorrido de los
    cables que salen de cada bandeja lateral con la entrada, la salida a la puerta, los grupos y la bisagra elegidos
    ({recorridos}), con las canaletas y la escala de cada lateral (y el transito hacia la puerta de la lateral de la
    bisagra); y, si el topografico trae la vista de la puerta, los de la puerta (entrada y puntos de paso: 'puerta').
    No guarda nada: la pestaña guarda el instructivo con las rutas y los recorridos"""
    P = ins_paths(jid)
    if not os.path.exists(P['json']):
        abort(404)
    body = request.get_json(silent=True)
    rec = body.get('recorridos') if isinstance(body, dict) else None
    if not isinstance(rec, dict) or not isinstance(rec.get('vistas', {}), dict):
        return jsonify(error='Datos inválidos'), 400
    with open(P['json'], encoding='utf-8') as f:
        ins = json.load(f)
    e8 = ins.get('estacion8') or {}
    if not (e8.get('laterales') or e8.get('puerta')):
        return jsonify(error='El topográfico no tiene bandejas laterales'), 400
    import estacion8
    return jsonify(laterales=estacion8.rutear_guardado(ins, rec), puerta=estacion8.rutear_guardado_puerta(ins, rec))


@app.post('/api/trabajo/<jid>/e8/punto')
def punto_e8(jid):
    """vista previa del ajuste a mano de un punto en el visor de la estacion 8 (📍): el recorrido del cable con su punta
    en el punto marcado ({vista, clave, punta: 'o' | 'd', xy: [x, y], recorridos, linea: {marca_o, marca_d, lado,
    lado_d} como la tiene la pestaña}), con las canaletas de la lateral y lo elegido de la entrada. No guarda nada: la
    pestaña guarda el punto en bornes_usuario (como E6) y el instructivo"""
    P = ins_paths(jid)
    if not os.path.exists(P['json']):
        abort(404)
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get('vista'), int) or body.get('punta') not in ('o', 'd') \
            or not isinstance(body.get('xy'), list) or len(body['xy']) != 2 or not all(isinstance(v, (int, float)) for v in body['xy']) \
            or not isinstance(body.get('clave'), str):
        return jsonify(error='Datos inválidos'), 400
    rec = body.get('recorridos')
    if rec is not None and (not isinstance(rec, dict) or not isinstance(rec.get('vistas', {}), dict)):
        return jsonify(error='Datos inválidos'), 400
    with open(P['json'], encoding='utf-8') as f:
        ins = json.load(f)
    import estacion8
    linea = body.get('linea')
    if linea is not None and not isinstance(linea, dict):
        return jsonify(error='Datos inválidos'), 400
    r = estacion8.rutear_punto(ins, rec if rec is not None else (ins.get('estacion8') or {}).get('recorridos'),
                               body['vista'], body['clave'], body['punta'], body['xy'], linea=linea)
    if r is None:
        return jsonify(error='No está ese cable en la bandeja lateral (o la punta es un empalme)'), 404
    return jsonify(r)


def _grupos_e8(P, ins):
    """(e8, R efectivo, clave del producto, motivo): los grupos de ruteo a mano de la estacion 8 del instructivo con lo
    guardado HOY para el producto (otro trabajo del mismo producto lo pudo cambiar despues de regenerar este) o, con el
    producto sin confirmar, lo del trabajo"""
    import estacion8_mano as E8M
    e8 = ins.get('estacion8') if isinstance(ins.get('estacion8'), dict) else {}
    R0 = e8.get('ruteo_mano')
    if not isinstance(R0, dict):
        return e8, None, None, None
    R = E8M.copia(R0)
    clave, motivo = E8M.clave_producto(ins.get('producto'))
    if clave:
        ent = E8M.entrada(clave)
        loc = e8.get('mano_trabajo') if ent is None and isinstance(e8.get('mano_trabajo'), dict) else None
        E8M.aplicar(R, (ent or {}).get('manual') if loc is None else loc, E8M.meta_de(clave, None, ent))
        if loc is not None:     # (se confirmo el producto despues de dibujar: pasa al producto al guardar o al regenerar)
            R['avisos'] = ['el ruteo a mano de este trabajo pasa al producto la próxima vez que se guarde o se regenere'] + R['avisos']
    else:
        E8M.aplicar(R, e8.get('mano_trabajo'), E8M.meta_de(None, motivo))
    return e8, R, clave, motivo


@app.get('/api/trabajo/<jid>/e8/grupos')
def ver_grupos_e8(jid):
    """los grupos de RUTEO A MANO de la estacion 8 (etapa E8-6) como estan hoy: los automaticos con lo que dibujo y
    corrigio el taller, guardado por producto (codigo + topografico) o en el trabajo. No escribe nada"""
    P = ins_paths(jid)
    ins = leer_json(P['json'])
    if not isinstance(ins, dict):
        abort(404)
    _, R, _, _ = _grupos_e8(P, ins)
    if R is None:
        return jsonify(error='Este instructivo no tiene los grupos de ruteo a mano: tocá ↻ Regenerar'), 400
    return jsonify(ruteo_mano=R)


@app.put('/api/trabajo/<jid>/e8/grupos')
def guardar_grupos_e8(jid):
    """guarda lo que dibuja y corrige el taller en el ruteo a mano de la estacion 8: {manual: {grupos: {id: {tramos,
    nombre}}, nuevos, mover}, version: la version del producto que tenia la pantalla}. Con el producto confirmado va al
    archivo de recorridos por producto (vale para todos sus trabajos con el mismo topografico); si no, al trabajo.
    409 si otro trabajo del mismo producto lo cambio mientras tanto (devuelve lo de hoy). -> {ok, ruteo_mano}"""
    import estacion8_mano as E8M
    P = ins_paths(jid)
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get('manual'), dict):
        return jsonify(error='Datos inválidos'), 400
    ver = body.get('version')
    if ver is not None and (isinstance(ver, bool) or not isinstance(ver, int)):
        return jsonify(error='Datos inválidos (versión)'), 400
    with PROY_LOCK:
        ins = leer_json(P['json'])
        if not isinstance(ins, dict):
            abort(404)
        e8 = ins.get('estacion8') if isinstance(ins.get('estacion8'), dict) else {}
        R = e8.get('ruteo_mano')
        if not isinstance(R, dict):
            return jsonify(error='Este instructivo no tiene los grupos de ruteo a mano: tocá ↻ Regenerar'), 400
        man, err = E8M.normalizar_manual(body['manual'], [c['id'] for c in R.get('categorias') or []])
        if err:
            return jsonify(error='; '.join(err)), 400
        clave, motivo = E8M.clave_producto(ins.get('producto'))
        s = load_state(jid) or {}
        if clave:
            try:
                ent, conflicto = E8M.guardar(clave, man, trabajo=jid, archivo=s.get('nombre') or s.get('archivo'),
                                             version_base=ver, prod=ins.get('producto'))
            except OSError as e:
                return jsonify(error=f'No se pudo guardar el archivo de recorridos por producto ({e})'), 500
            if conflicto:
                _, Rhoy, _, _ = _grupos_e8(P, ins)
                return jsonify(error='Otro trabajo del mismo producto cambió el ruteo a mano mientras tanto: se recargó lo de hoy',
                               conflicto=True, ruteo_mano=Rhoy), 409
            e8.pop('mano_trabajo', None)
            miembro = E8M.aplicar(R, man, E8M.meta_de(clave, None, ent))
        else:
            e8['mano_trabajo'] = man
            miembro = E8M.aplicar(R, man, E8M.meta_de(None, motivo))
        E8M.anotar(e8, miembro)
        write_json(P['json'], ins)
    return jsonify(ok=True, ruteo_mano=R)


@app.get('/api/trabajo/<jid>/e8/fondo.png')
def fondo_png(jid):
    """imagen de la vista del FONDO de la estacion 8 (la bandeja principal con la zona del fondo), para dibujar encima el
    ruteo a mano"""
    P = ins_paths(jid)
    if not os.path.exists(P['json']) or not os.path.exists(P['topo']):
        abort(404)
    with open(P['json'], encoding='utf-8') as f:
        fo = (json.load(f).get('estacion8') or {}).get('fondo') or {}
    return region_png(P, fo.get('pag'), fo.get('region'))


@app.get('/api/trabajo/<jid>/topo.png')
def topo_png(jid):
    """imagen de la bandeja del topografico (la region del instructivo) para dibujar el ruteo encima"""
    P = ins_paths(jid)
    if not os.path.exists(P['json']) or not os.path.exists(P['topo']):
        abort(404)
    with open(P['json'], encoding='utf-8') as f:
        topo = json.load(f).get('topo') or {}
    return region_png(P, topo.get('pag'), topo.get('region'))


@app.get('/api/trabajo/<jid>/e8/lateral/<int:i>.png')
def lateral_png(jid, i):
    """imagen de una bandeja lateral (estacion E8) del topografico, para dibujar sus cables encima"""
    P = ins_paths(jid)
    if not os.path.exists(P['json']) or not os.path.exists(P['topo']):
        abort(404)
    with open(P['json'], encoding='utf-8') as f:
        lats = (json.load(f).get('estacion8') or {}).get('laterales') or []
    if not 0 <= i < len(lats):
        abort(404)
    return region_png(P, lats[i].get('pag'), lats[i].get('region'))


@app.get('/api/trabajo/<jid>/e8/puerta.png')
def puerta_png(jid):
    """imagen de la vista de la puerta (estacion E8) del topografico, para dibujar sus cables encima"""
    P = ins_paths(jid)
    if not os.path.exists(P['json']) or not os.path.exists(P['topo']):
        abort(404)
    with open(P['json'], encoding='utf-8') as f:
        pu = (json.load(f).get('estacion8') or {}).get('puerta') or {}
    return region_png(P, pu.get('pag'), pu.get('region'))


def region_png(P, pag, reg):
    if not reg or not pag:
        abort(404)
    hd = request.args.get('hd') == '1'          # alta resolucion para las lupas del visor
    # la clave del cache incluye la region: si se relee el topografico y cambia la bandeja, se vuelve a dibujar
    import hashlib
    rk = hashlib.md5(json.dumps([round(v, 1) for v in reg]).encode()).hexdigest()[:8]
    cache = os.path.join(P['dir'], ('topo_%d_%s_hd.png' if hd else 'topo_%d_%s.png') % (pag, rk))
    with PDFIUM_LOCK:
        if not os.path.exists(cache) or os.path.getmtime(cache) < os.path.getmtime(P['topo']):
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(P['topo'])
            try:
                pg = doc[pag - 1]
                try:
                    W, H = pg.get_size()
                    img = pg.render(scale=8.0 if hd else 3.0, crop=(reg[0], reg[1], W - reg[2], H - reg[3])).to_pil().convert('RGB').quantize(colors=64)
                finally:
                    pg.close()
            finally:
                doc.close()
            img.save(cache + '.tmp.png', optimize=True); os.replace(cache + '.tmp.png', cache)
    return send_file(cache, mimetype='image/png', max_age=0)


@app.post('/api/trabajo/<jid>/fotos')
def subir_fotos(jid):
    P = ins_paths(jid); os.makedirs(P['fotos'], exist_ok=True)
    out = []
    from PIL import Image, ImageOps
    for f in request.files.getlist('fotos'):
        if os.path.splitext(f.filename)[1].lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
            continue
        name = uuid.uuid4().hex[:10] + '.jpg'
        try:
            im = ImageOps.exif_transpose(Image.open(f.stream)).convert('RGB')
            im.thumbnail((1800, 1800))
            im.save(os.path.join(P['fotos'], name), quality=86)
        except Exception:
            continue
        out.append(dict(nombre=f.filename, archivo=name))
    return jsonify(fotos=out)


@app.get('/api/trabajo/<jid>/fotos/<name>')
def ver_foto(jid, name):
    P = ins_paths(jid)
    if not re.fullmatch(r'[0-9a-f]{10}\.jpg', name):
        abort(404)
    fp = os.path.join(P['fotos'], name)
    if not os.path.exists(fp):
        abort(404)
    return send_file(fp, mimetype='image/jpeg', max_age=86400)


# ------------------------------------------------------------------ pestaña 📽 Proyector (proyectar el ruteo sobre la bandeja real)
@app.get('/proyector/<jid>')
def proyector_html(jid):
    """pestaña aparte (para llevarla a la pantalla del proyector): web/proyector.html"""
    job_dir(jid)
    return html_estatico('proyector.html')


PROY_CLAVES = ('orificios_usuario', 'calibracion', 'ventana', 'opciones')   # lo que guarda la pestaña en ins['proyector']


@app.get('/api/trabajo/<jid>/proyector')
def ver_proyector(jid):
    """lo que necesita la pestaña: la bandeja (region, canaletas, rieles, escala), los orificios de montaje de la placa
    (los del dibujo, calculados una vez y guardados en instructivo.json; y los marcados a mano, si los hay), la
    calibracion y la ventana guardadas, y los aparatos con su posicion (para ubicar la ventana en la parte vacia)"""
    P = ins_paths(jid); s = load_state(jid) or {}
    ins = leer_json(P['json'])
    if not isinstance(ins, dict):
        abort(404)
    topo = ins.get('topo') or {}
    pr = ins.get('proyector') or {}
    auto = pr.get('orificios_auto')
    clave = [topo.get('pag'), topo.get('region')]
    if not isinstance(auto, dict) or auto.get('clave') != clave:      # (otra bandeja u otra lectura del topografico)
        import proyector
        auto = proyector.orificios(P['topo'], topo.get('pag'), topo.get('region'), topo.get('escala'))
        auto['clave'] = clave
        with PROY_LOCK:
            ins2 = leer_json(P['json'])
            if isinstance(ins2, dict):
                ins2.setdefault('proyector', {})['orificios_auto'] = auto
                write_json(P['json'], ins2)
    lay = leer_json(P['layout']) or {}
    comp = {t: dict(x=c.get('x'), y=c.get('y'), ubic=c.get('ubic'), estacion=c.get('estacion'))
            for t, c in (lay.get('comp') or {}).items() if isinstance(c, dict) and c.get('x') is not None}
    return jsonify(nombre=s.get('nombre'), estacion=ins.get('estacion') or 'E6', topo=topo, orificios=auto,
                   orificios_usuario=pr.get('orificios_usuario'), calibracion=pr.get('calibracion'), ventana=pr.get('ventana'),
                   opciones=pr.get('opciones') or {}, comp=comp)


@app.put('/api/trabajo/<jid>/proyector')
def guardar_proyector(jid):
    """guarda en ins['proyector'] solo las claves de la pestaña (null borra una); el resto del instructivo no se toca"""
    P = ins_paths(jid)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Datos inválidos'), 400
    with PROY_LOCK:
        ins = leer_json(P['json'])
        if not isinstance(ins, dict):
            abort(404)
        pr = ins.setdefault('proyector', {})
        for k in PROY_CLAVES:
            if k in data:
                if data[k] is None:
                    pr.pop(k, None)
                else:
                    pr[k] = data[k]
        write_json(P['json'], ins)
    return jsonify(ok=True)


def firma_codigo():
    """sha1 de los .py del programa (programa/ y sus subcarpetas): es lo que el servidor carga al arrancar y no vuelve a
    leer (los .js / .css y los catalogos se leen en cada pedido y no cuentan)"""
    import hashlib
    h = hashlib.sha1()
    for raiz, dirs, archivos in os.walk(HERE):
        dirs[:] = sorted(d for d in dirs if d != '__pycache__')
        for a in sorted(archivos):
            if a.endswith('.py'):
                with open(os.path.join(raiz, a), 'rb') as f:
                    h.update(os.path.relpath(os.path.join(raiz, a), HERE).encode('utf-8') + b'\0' + f.read())
    return h.hexdigest()[:16]


FIRMA = firma_codigo()      # el codigo con el que arranco este servidor
INICIO = time.time()


@app.get('/api/version')
def version():
    """con que codigo corre este servidor y si esta ocupado (lo usa el arranque para cerrar un servidor viejo)"""
    ocupado = (sum(1 for j in list(JOBS.values()) if j.get('estado') in ('procesando', 'en cola'))
               + sum(1 for j in list(INS.values()) if (j or {}).get('estado') in ('procesando', 'en cola')))
    return jsonify(firma=FIRMA, carpeta=ROOT, inicio=INICIO, pid=os.getpid(), ocupado=ocupado)


def already_running():
    import socket
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', PORT)) == 0


def aviso(texto):
    """mensaje al usuario al arrancar (pythonw no tiene consola: ventanita de Windows); con --no-abrir, por stderr"""
    if '--no-abrir' not in sys.argv:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, texto, 'Listado de cables', 0x40)
            return
        except Exception:
            pass
    print(texto, file=sys.stderr)


def cerrar_servidor_viejo():
    """Al abrir el programa con un servidor ya andando: si ese servidor corre con OTRO codigo (arranco antes de un cambio
    en los .py), se lo cierra para arrancar este; antes solo se abria el navegador y se seguia usando el codigo viejo.
    No se corta un servidor que esta procesando un plano o un instructivo (se avisa), ni el de otra copia del programa
    (otra carpeta: se avisa cual es). Un servidor de antes de /api/version es de esta version vieja del programa y se
    cierra si no esta procesando ningun plano. Devuelve True si el puerto quedo libre."""
    import urllib.request
    base = f'http://127.0.0.1:{PORT}'

    def leer(ruta):
        with urllib.request.urlopen(base + ruta, timeout=3) as r:
            return json.loads(r.read().decode('utf-8'))
    try:
        v = leer('/api/version')
    except Exception:
        v = None
    if v is not None:
        if v.get('firma') == FIRMA:
            return False                  # mismo codigo: se usa el que ya esta abierto
        if os.path.normcase(os.path.abspath(str(v.get('carpeta')))) != os.path.normcase(os.path.abspath(ROOT)):
            aviso(f"Está abierto el programa de otra carpeta:\n{v.get('carpeta')}\n\nPara usar el de\n{ROOT}\n"
                  "cerralo (Historial → «Cerrar el programa») y volvé a abrir «Listado de cables (web).bat».")
            return False
        ocupado = int(v.get('ocupado') or 0)
    else:
        try:
            ocupado = sum(1 for j in leer('/api/trabajos') if j.get('estado') in ('procesando', 'en cola'))
        except Exception:
            return False                  # no es este programa: como antes, solo se abre el navegador
    if ocupado:
        aviso('Hay una versión nueva del programa, pero el que está abierto está procesando un plano.\n'
              'Cuando termine, tocá «Cerrar el programa» (en el historial) y volvé a abrir «Listado de cables (web).bat».')
        return False
    try:
        urllib.request.urlopen(urllib.request.Request(base + '/api/salir', data=b'', method='POST'), timeout=3).close()
    except Exception:
        pass
    for _ in range(50):
        if not already_running():
            return True
        time.sleep(0.1)
    return False


if __name__ == '__main__':
    url = f'http://127.0.0.1:{PORT}/'
    if already_running() and not cerrar_servidor_viejo():   # ya esta abierta con este codigo: solo abrir el navegador
        if '--no-abrir' not in sys.argv:
            __import__('webbrowser').open(url)
        sys.exit(0)
    if '--no-abrir' not in sys.argv:
        threading.Timer(1.2, lambda: __import__('webbrowser').open(url)).start()
    print('Interfaz en', url)
    app.run(host='127.0.0.1', port=PORT, debug=False, threaded=True)
