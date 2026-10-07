"""Bases nuevas de la red de seguridad (etapa 0 del plan modular): listado, layout, estacion E8 e instructivo COMPLETO
de un trabajo, armados con web.gen_instructivo (lo mismo que «Regenerar» en la web) sobre una COPIA TEMPORAL del
trabajo. No escribe nada en el trabajo ni en programa/ (salvo la memoria OCR si hay OCR en vivo: ver abajo).
uso: python pruebas/volcar_bases_nuevas.py <trabajo_dir> <dir_salida> --nombre <t> [--relayout]
  escribe en <dir_salida>:
    listado_<t>.json  lo que web.result_json guarda en resultado.json, sin nombre, fecha, opciones, segundos ni stats
    layout_<t>.json   {'layout': el layout.json que deja gen_instructivo (antes del mapeo),
                       'en_memoria': las claves que el mapeo y gen_instructivo agregan o cambian en el layout
                                     (bornes, renombrar, bornes_conf, ..., estaciones, salidas, quitados) tal como
                                     quedan en memoria justo antes de instructivo.build}
    e8_<t>.json       ins['estacion8']
    ins_<t>.json      el instructivo.json completo, sin los campos que cambian solos (generado, mapeo.segundos,
                      mapeo.de_cache)
  --relayout: vuelve a leer el topografico (como volcar_trabajo.py --relayout). Sin esto, como la web: se relee solo si
              no hay layout.json o si es de otra version del lector.
  Plano de EPLAN sin topografico.pdf (el PAE de pruebas/trabajos/76884): como el boton «Usar las bandejas de este mismo
  PDF» (web.usar_mismo_pdf: copia el PDF como topografico y regenera con el topografico nuevo; siempre relee).
  Un 'archivo' relativo en estado.json (../../../1 - Planos/...) se resuelve contra la carpeta ORIGINAL del trabajo.
  Las rutas de la carpeta temporal y de la raiz del repo se escriben como <trabajo> y <raiz>.
  La memoria OCR (programa/ocr_cache.json) la puede reescribir el lector si lee un renglon nuevo: si pasa, se avisa."""
import os, sys, json, copy, shutil, tempfile, threading, hashlib, time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAMA = os.path.join(RAIZ, 'programa')
JID = 'b0b0b0b0b0b0'          # fijo: el id del trabajo no tiene que cambiar las bases

# campos que cambian solos de una corrida a otra (no van en las bases)
VOLATILES_LISTADO = ('nombre', 'fecha', 'opciones', 'segundos', 'stats')
VOLATILES_INS = ('generado',)
VOLATILES_MAPEO = ('segundos', 'de_cache')
# claves del layout que agregan el mapeo y gen_instructivo antes de build (se guardan aparte, en 'en_memoria')


def sha1(p):
    try:
        with open(p, 'rb') as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None


def a_json(x):
    """lo mismo que quedaria al escribirlo y leerlo como JSON (tuplas -> listas, claves -> texto)"""
    return json.loads(json.dumps(x, ensure_ascii=False, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o)))


def limpiar_rutas(x, reemplazos):
    if isinstance(x, str):
        for a, b in reemplazos:
            x = x.replace(a, b)
        return x
    if isinstance(x, list):
        return [limpiar_rutas(v, reemplazos) for v in x]
    if isinstance(x, dict):
        return {limpiar_rutas(k, reemplazos): limpiar_rutas(v, reemplazos) for k, v in x.items()}
    return x


def escribir(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def main():
    try:
        sys.stdout.reconfigure(errors='replace')        # (consola cp1252 de Windows)
    except (AttributeError, ValueError):
        pass
    args = [a for a in sys.argv[1:]]
    if len(args) < 4 or '--nombre' not in args:
        print(__doc__)
        sys.exit(2)
    i = args.index('--nombre'); nombre = args[i + 1]
    relayout = '--relayout' in args
    resto = [a for k, a in enumerate(args) if k not in (i, i + 1) and a != '--relayout']
    trabajo, salida = os.path.abspath(resto[0]), os.path.abspath(resto[1])
    os.makedirs(salida, exist_ok=True)
    t0 = time.time()
    ocr_antes = sha1(os.path.join(PROGRAMA, 'ocr_cache.json'))

    tmp = tempfile.mkdtemp(prefix='bases_nuevas_')
    historial = os.path.join(tmp, 'historial')
    os.makedirs(historial)
    os.environ['PLANOCABLES_HISTORIAL'] = historial      # (antes de importar web: nunca el historial del usuario)
    sys.path.insert(0, PROGRAMA)
    try:
        d = os.path.join(historial, JID)
        shutil.copytree(trabajo, d, ignore=shutil.ignore_patterns('*.png', 'fotos'))
        ep = os.path.join(d, 'estado.json')
        with open(ep, encoding='utf-8') as f:
            est = json.load(f)
        if not os.path.exists(os.path.join(d, est['archivo'])):
            # PDF fuera del trabajo (ruta relativa a la carpeta original): se apunta al mismo archivo con ruta absoluta
            pdf = os.path.normpath(os.path.join(trabajo, est['archivo']))
            if not os.path.exists(pdf):
                print(f'FALLA: no se encuentra el plano {est["archivo"]!r} (ni en {pdf})')
                sys.exit(1)
            est['archivo'] = pdf
            with open(ep, 'w', encoding='utf-8') as f:
                json.dump(est, f, ensure_ascii=False)

        import web, instructivo
        web.WORK = historial
        # se captura el listado y el layout en memoria justo antes de armar el instructivo (gen_instructivo importa
        # build de instructivo en cada llamada, asi que alcanza con reemplazarlo en el modulo)
        capt = {}
        build_orig = instructivo.build

        def build_capturado(res, lay, *a, **k):
            capt.setdefault('listado', a_json(web.result_json(res, '', {})))
            capt.setdefault('lay', a_json(lay))
            capt['llamadas'] = capt.get('llamadas', 0) + 1
            return build_orig(res, lay, *a, **k)

        instructivo.build = build_capturado
        try:
            mismo_pdf = bool(est.get('eplan')) and not os.path.exists(os.path.join(d, 'topografico.pdf'))
            if mismo_pdf:
                antes = set(threading.enumerate())
                web.usar_mismo_pdf(JID)               # arranca gen_instructivo(jid, None, True, True) en un hilo
                for t in set(threading.enumerate()) - antes:
                    t.join()
            else:
                web.INS[JID] = dict(estado='en cola', mensaje='', progreso=0.0)
                web.gen_instructivo(JID, relayout=relayout)
        finally:
            instructivo.build = build_orig
        st = web.INS.get(JID) or {}
        if st.get('estado') != 'terminado':
            print(f"FALLA: gen_instructivo termino en {st.get('estado')!r}: {st.get('error')}\n{st.get('detalle') or ''}")
            sys.exit(1)
        if capt.get('llamadas') != 1:
            print(f"FALLA: instructivo.build se llamo {capt.get('llamadas')} veces (se esperaba 1)")
            sys.exit(1)

        with open(os.path.join(d, 'instructivo.json'), encoding='utf-8') as f:
            ins = json.load(f)
        with open(os.path.join(d, 'layout.json'), encoding='utf-8') as f:
            lay_disco = json.load(f)
        reemplazos = [(d, '<trabajo>'), (d.replace('\\', '/'), '<trabajo>'), (RAIZ, '<raiz>'), (RAIZ.replace('\\', '/'), '<raiz>')]

        listado = {k: v for k, v in capt['listado'].items() if k not in VOLATILES_LISTADO}
        lay_mem = capt['lay']
        en_memoria = {k: v for k, v in lay_mem.items() if k not in lay_disco or lay_disco[k] != v}
        quitadas = sorted(k for k in lay_disco if k not in lay_mem)
        layout = dict(layout=lay_disco, en_memoria=en_memoria)
        if quitadas:
            layout['quitadas_en_memoria'] = quitadas
        for k in VOLATILES_INS:
            ins.pop(k, None)
        for k in VOLATILES_MAPEO:
            (ins.get('mapeo') or {}).pop(k, None)
        e8 = ins.get('estacion8')

        salidas = {}
        for pref, data in (('listado', listado), ('layout', layout), ('e8', e8), ('ins', ins)):
            p = os.path.join(salida, f'{pref}_{nombre}.json')
            escribir(p, limpiar_rutas(data, reemplazos))
            salidas[pref] = p
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    lineas = [l for p in ins['pasos'] for l in p['lineas']]
    print(f"{nombre}: {len(lineas)} lineas E6 en {len(ins['pasos'])} pasos, {len(ins['pendientes'])} pendientes, "
          f"{len(ins['sueltos'])} sueltos, {len(ins['otra_estacion'])} en otra estacion, "
          f"{sum(1 for l in lineas if l.get('hecho'))} marcadas como hechas; E8: {len((e8 or {}).get('laterales') or [])} laterales; "
          f"en memoria: {', '.join(sorted(en_memoria))} ({time.time() - t0:.0f} s)")
    for pref, p in salidas.items():
        print(f'  {p} ({os.path.getsize(p) // 1024} KB)')
    if sha1(os.path.join(PROGRAMA, 'ocr_cache.json')) != ocr_antes:
        print('AVISO: la corrida reescribio programa/ocr_cache.json (hubo OCR en vivo). Restaurarlo con:\n'
              f'  git -C "{RAIZ}" checkout -- programa/ocr_cache.json')
    print('TODO OK')


if __name__ == '__main__':
    main()
