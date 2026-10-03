"""Interfaz web local: http://127.0.0.1:8765
Sube un plano PDF, genera el PDF buscable y el listado de cables, y permite
explorar el listado y ver cada cable resaltado sobre el plano."""
import os, sys, json, uuid, threading, time, datetime, shutil, subprocess, re, io
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from flask import Flask, request, jsonify, send_file, abort

ROOT = os.path.dirname(HERE)
WORK = os.path.join(ROOT, '3 - Historial web')
os.makedirs(WORK, exist_ok=True)
PORT = int(os.environ.get('PLANOCABLES_PORT', '8765'))

app = Flask(__name__, static_folder=os.path.join(HERE, 'web'), static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024
JOBS = {}
RUN_LOCK = threading.Lock()   # un plano a la vez (el proceso usa toda la CPU)
from ocr_raster import PDFIUM_LOCK   # pdfium no admite uso simultaneo desde varios hilos


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


def result_json(res, name, opts):
    from core import sheet_name
    pages = [dict(index=p['index'], sheet=sheet_name(p), title=p['meta'].get('title', ''), w=p['w'] - p.get('x0', 0), h=p['h'] - p.get('y0', 0),
                  x0=p.get('x0', 0), y0=p.get('y0', 0),
                  cables=sum(1 for n in p['nums'] if n['chain'] is not None)) for p in res.pages]
    clean = lambda d: {k: v for k, v in d.items() if k not in ('chain', 'etiquetas', 'via')}
    return dict(
        nombre=name, fecha=datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), segundos=round(res.seconds, 1),
        nota=res.default[2] if res.default else None, paginas=pages, opciones=opts,
        cables=res.cables, detalle=[clean(d) for d in res.detail], revisar=res.review,
        rutas={str(p['index']): p.get('routes', {}) for p in res.pages if p.get('routes')},
        sin_numero=getattr(res, 'unnumbered', []), stats=res.stats)


def run_job(jid, pdf_path, opts):
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
                json.dump(result_json(res, j['nombre'], opts), f, ensure_ascii=False)
            j['cables'] = len({c['num'] for c in res.cables}); j['revisar'] = len(res.review)
            j['segundos'] = round(res.seconds, 1)
            j['estado'] = 'terminado'; j['progreso'] = 1.0
            log(f"Listo en {res.seconds:.0f} s: {j['cables']} números de cable.")
    except Exception as e:
        import traceback
        j['estado'] = 'error'; j['error'] = str(e); j['log'].append(traceback.format_exc())
    finally:
        save_state(jid)
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
    threading.Thread(target=gen_instructivo, args=(jid, None, True), daemon=True).start()


@app.before_request
def solo_local():
    ok_hosts = {f'127.0.0.1:{PORT}', f'localhost:{PORT}'}
    if request.host not in ok_hosts:
        abort(403)
    origin = request.headers.get('Origin')
    if request.method in ('POST', 'DELETE', 'PUT') and origin and origin not in {f'http://{h}' for h in ok_hosts}:
        abort(403)


@app.get('/')
def index():
    # version en los .js/.css (fecha del archivo): al actualizar el programa el navegador no usa lo viejo guardado
    with open(os.path.join(HERE, 'web', 'index.html'), encoding='utf-8') as f:
        html = f.read()
    ver = lambda m: f"/static/{m.group(1)}?v={int(os.path.getmtime(os.path.join(HERE, 'web', m.group(1))))}"
    html = re.sub(r'/static/([\w.-]+\.(?:js|css))(?=")', lambda m: ver(m) if os.path.exists(os.path.join(HERE, 'web', m.group(1))) else m.group(0), html)
    r = app.response_class(html, mimetype='text/html')
    r.headers['Cache-Control'] = 'no-cache'
    return r


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
    threading.Thread(target=run_job, args=(jid, os.path.join(d, s['archivo']), opts), daemon=True).start()
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


def gen_instructivo(jid, overrides=None, relayout=False):
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
                for k in ('bornes', 'renombrar', 'bornes_conf', 'bornes_nota', 'renombrar_auto'):
                    lay.pop(k, None)
                # solo los manuales del trabajo (bornes.json y los 'bornes' de correcciones.json); un archivo roto se ignora
                lay['bornes'], lay['renombrar'] = leer_bornes_manuales(P['dir'], mapeo['avisos'], corr=corr if corr else {})
            mapeo = mapeo if isinstance(mapeo, dict) else {}
            mapeo['avisos'] = list(dict.fromkeys(avisos_archivos + list(mapeo.get('avisos') or [])))
            lay['estaciones'] = old.get('estaciones') or {}
            lay['estacion'] = old.get('estacion') or 'E6'
            lay['estacion_auto'] = old.get('estacion_auto') or {'seccion_min': 35, 'estacion': 'E8'}   # 35 mm2 -> gabinete
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
            ins['estaciones'] = lay['estaciones']
            ins['estacion'] = lay['estacion']
            ins['estacion_auto'] = lay['estacion_auto']
            ins['auditoria'] = old.get('auditoria') or {}
            ins['wpc'] = old.get('wpc') or {}     # lista WPC: largos y colores a mano, cortes de etapa, excluidos
            ins['e8'] = old.get('e8') or {}       # E8 (gabinete): cables marcados y aparatos ubicados a mano
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
            with E8_LOCK:      # las marcas de E8 hechas mientras se regeneraba (las guarda su visor) no se pierden
                ins['e8'] = e8_del_disco(P['json'], ins['e8'])
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
    threading.Thread(target=gen_instructivo, args=(jid, None, True), daemon=True).start()
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


@app.get('/api/trabajo/<jid>/instructivo')
def ver_instructivo(jid):
    P = ins_paths(jid)
    if not os.path.exists(P['json']):
        abort(404)
    return send_file(P['json'], mimetype='application/json', max_age=0)


@app.put('/api/trabajo/<jid>/instructivo')
def guardar_instructivo(jid):
    P = ins_paths(jid)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('pasos'), list):
        return jsonify(error='Datos inválidos'), 400
    data['editado'] = True
    with E8_LOCK:      # las marcas de E8 las guarda su visor (/e8/marcas): una copia vieja de la pestaña de E6 no las pisa
        data['e8'] = e8_del_disco(P['json'], data.get('e8') or {})
        write_json(P['json'], data)
    return jsonify(ok=True)


@app.get('/api/trabajo/<jid>/topo.png')
def topo_png(jid):
    """imagen de la bandeja del topografico (la region del instructivo) para dibujar el ruteo encima"""
    P = ins_paths(jid)
    if not os.path.exists(P['json']) or not os.path.exists(P['topo']):
        abort(404)
    with open(P['json'], encoding='utf-8') as f:
        topo = json.load(f).get('topo') or {}
    reg, pag = topo.get('region'), topo.get('pag')
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


# ------------------------------------------------------------------ E8: cableado dentro del gabinete (vista 3D)
E8 = {}                       # jid -> estado de la lectura del gabinete
E8_LOCK = threading.Lock()    # leer-cambiar-escribir instructivo.json: marcas de E8, pestaña de E6 y regenerar


def e8_del_disco(path, por_defecto=None):
    """ins['e8'] (marcas de E8 y aparatos ubicados a mano) tal como esta guardado, o por_defecto"""
    try:
        with open(path, encoding='utf-8') as f:
            v = json.load(f).get('e8')
        return v if isinstance(v, dict) else (por_defecto or {})
    except (OSError, ValueError, AttributeError):
        return por_defecto or {}


def e8_firma(P, ins):
    """el modelo del gabinete se vuelve a leer si cambia el topografico, layout.json, los tags del funcional o gabinete.py"""
    import gabinete, hashlib
    h = hashlib.md5(gabinete.VERSION.encode())
    for p in (P['topo'], P['layout']):
        try:
            s_ = os.stat(p); h.update(f'{s_.st_size}:{int(s_.st_mtime)}'.encode())
        except OSError:
            h.update(b'-')
    h.update(json.dumps(sorted({c.get('tag') or '' for c in ins.get('componentes') or []})).encode())
    return h.hexdigest()[:16]


def e8_leer(jid):
    """lee el gabinete del topografico (vistas, aparatos, canaletas) y lo guarda en e8_gabinete.json del trabajo"""
    st = E8[jid]
    try:
        P = ins_paths(jid)
        with RUN_LOCK:
            import gabinete
            st.update(estado='procesando', mensaje='Leyendo el gabinete en el topográfico…', progreso=0.08)
            with open(P['json'], encoding='utf-8') as f:
                ins = json.load(f)
            with open(P['layout'], encoding='utf-8') as f:
                lay = json.load(f)
            firma = e8_firma(P, ins)
            M = gabinete.leer_gabinete(P['topo'], lay, [c.get('tag') for c in ins.get('componentes') or []],
                                       log=lambda m: st.update(mensaje=m, progreso=min(0.92, st['progreso'] + 0.18)))
            write_json(os.path.join(P['dir'], 'e8_gabinete.json'), dict(firma=firma, modelo=M))
            st.update(estado='terminado', mensaje='Listo', progreso=1.0)
    except Exception as e:
        import traceback
        st.update(estado='error', error=str(e), detalle=traceback.format_exc())


def e8_modelo(P):
    try:
        with open(os.path.join(P['dir'], 'e8_gabinete.json'), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


@app.get('/api/trabajo/<jid>/e8')
def ver_e8(jid):
    """modelo del gabinete + cables de E8 con sus puntas y recorrido en 3D. 202 mientras se lee el gabinete."""
    P = ins_paths(jid)
    if (INS.get(jid) or {}).get('estado') in ('procesando', 'en cola'):
        return jsonify(estado='procesando', mensaje='Se está armando el instructivo…', progreso=(INS[jid].get('progreso') or 0) * 0.5), 202
    if not os.path.exists(P['json']) or not os.path.exists(P['layout']):
        return jsonify(estado='sin_instructivo', error='Primero armá el instructivo de E6: cargá el plano topográfico en la pestaña 🧰 Instructivo.')
    with open(P['json'], encoding='utf-8') as f:
        ins = json.load(f)
    c = e8_modelo(P)
    releer = request.args.get('releer') == '1'
    st = E8.get(jid) or {}
    if releer or not c.get('modelo') or c.get('firma') != e8_firma(P, ins):
        if st.get('estado') == 'error' and not releer:
            return jsonify(estado='error', error=st.get('error') or 'No se pudo leer el gabinete')
        if st.get('estado') not in ('procesando', 'en cola'):
            E8[jid] = dict(estado='en cola', mensaje='En cola…', progreso=0.0)
            threading.Thread(target=e8_leer, args=(jid,), daemon=True).start()
        return jsonify({k: v for k, v in E8[jid].items() if k != 'detalle'}), 202
    import gabinete
    M = c['modelo']
    E = gabinete.armar_e8(ins, M, ins.get('e8'))
    migrar = E.pop('migrar', None) or {}
    if migrar:
        # marcas guardadas con la clave de antes ('num|desde|hasta', que cambiaba al ubicar un aparato): a la clave estable
        with E8_LOCK:
            try:
                with open(P['json'], encoding='utf-8') as f:
                    ins2 = json.load(f)
                hs = (ins2.get('e8') or {}).get('hechos') or {}
                cambio = False
                for vieja, nueva in migrar.items():
                    if vieja in hs:
                        hs.setdefault(nueva, hs[vieja]); hs.pop(vieja); cambio = True
                if cambio:
                    write_json(P['json'], ins2)
                    ins['e8'] = ins2.get('e8')
            except (OSError, ValueError, AttributeError):
                pass
    return jsonify(estado='listo', modelo=M, generado=ins.get('generado'), e8=ins.get('e8') or {}, **E)


@app.get('/api/trabajo/<jid>/e8/vista/<vid>.png')
def e8_vista_png(jid, vid):
    """imagen de una vista del gabinete (recorte del topografico, como topo.png) para la placa en 3D"""
    P = ins_paths(jid)
    if not re.fullmatch(r'[a-z_]{2,40}', vid):
        abort(404)
    M = e8_modelo(P).get('modelo') or {}
    v = next((v for v in M.get('vistas') or [] if v.get('id') == vid and v.get('imagen')), None)
    if not v or not os.path.exists(P['topo']):
        abort(404)
    import hashlib
    box, pag = v['box'], v['pag']
    rk = hashlib.md5(json.dumps([pag] + [round(x, 1) for x in box]).encode()).hexdigest()[:8]
    cache = os.path.join(P['dir'], f'e8_{vid}_{rk}.png')
    with PDFIUM_LOCK:
        if not os.path.exists(cache) or os.path.getmtime(cache) < os.path.getmtime(P['topo']):
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(P['topo'])
            try:
                pg = doc[pag - 1]
                try:
                    W, H = pg.get_size()
                    k = min(6.0, 2048.0 / max(box[2] - box[0], box[3] - box[1]))
                    img = pg.render(scale=k, crop=(box[0], box[1], W - box[2], H - box[3])).to_pil().convert('RGB').quantize(colors=96)
                finally:
                    pg.close()
            finally:
                doc.close()
            img.save(cache + '.tmp.png', optimize=True); os.replace(cache + '.tmp.png', cache)
    return send_file(cache, mimetype='image/png', max_age=0)


@app.post('/api/trabajo/<jid>/e8/marcas')
def e8_marcas(jid):
    """guarda en instructivo.json['e8']: {hechos: {clave: true|false}} (cable cableado en E8) y/o
    {ubicacion: {tag, vista, pt: [X, Y]}} (aparato ubicado a mano en el visor; {tag, borrar: true} lo saca)"""
    P = ins_paths(jid)
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not os.path.exists(P['json']):
        return jsonify(error='Datos inválidos'), 400
    ahora = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    with E8_LOCK:
        with open(P['json'], encoding='utf-8') as f:
            ins = json.load(f)
        e8 = ins.get('e8') if isinstance(ins.get('e8'), dict) else {}
        hechos = body.get('hechos')
        if isinstance(hechos, dict):
            hs = e8.setdefault('hechos', {})
            for k, v in hechos.items():
                if isinstance(k, str) and len(k) <= 400:
                    if v:
                        hs[k] = dict(hecho=True, cuando=ahora)
                    else:
                        hs.pop(k, None)
        u = body.get('ubicacion')
        if isinstance(u, dict) and isinstance(u.get('tag'), str) and 0 < len(u['tag']) <= 80:
            ub = e8.setdefault('ubicaciones', {})
            if u.get('borrar'):
                ub.pop(u['tag'], None)
            else:
                try:
                    if not re.fullmatch(r'[a-z_]{2,40}', u.get('vista') or ''):
                        raise ValueError
                    ub[u['tag']] = dict(vista=u['vista'], pt=[round(float(u['pt'][0]), 1), round(float(u['pt'][1]), 1)], cuando=ahora)
                except (TypeError, ValueError, IndexError, KeyError):
                    return jsonify(error='Ubicación inválida'), 400
        ins['e8'] = e8
        write_json(P['json'], ins)
    return jsonify(ok=True, e8=e8)


def already_running():
    import socket
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', PORT)) == 0


if __name__ == '__main__':
    url = f'http://127.0.0.1:{PORT}/'
    if already_running():   # ya esta abierta: solo abrir el navegador
        if '--no-abrir' not in sys.argv:
            __import__('webbrowser').open(url)
        sys.exit(0)
    if '--no-abrir' not in sys.argv:
        threading.Timer(1.2, lambda: __import__('webbrowser').open(url)).start()
    print('Interfaz en', url)
    app.run(host='127.0.0.1', port=PORT, debug=False, threaded=True)
