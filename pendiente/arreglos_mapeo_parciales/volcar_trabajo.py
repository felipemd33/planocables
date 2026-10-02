"""Arma el instructivo de un trabajo web con el codigo ACTUAL y lo vuelca a JSON (para comparar antes/despues).
Hace lo mismo que web.py gen_instructivo (overrides, correcciones.json, bornes_usuario, mapeo automatico de bornes con
el mismo respaldo si falla, bornes.json), sin escribir NADA en el trabajo (salvo --con-cache).
uso: python volcar_trabajo.py <carpeta_trabajo> <salida.json> [--relayout] [--sin-mapeo] [--con-cache]
  --relayout:  vuelve a leer el topografico (topo.layout) en vez de usar layout.json
  --sin-mapeo: como antes de integrar el mapeo automatico (solo bornes.json / correcciones.json)
  --con-cache: usa y escribe el cache del mapeo (bornes_auto.json DENTRO del trabajo). Por defecto el mapeo se
               calcula de nuevo y no se escribe nada ('--sin-cache' se acepta y es lo mismo que no ponerlo)"""
import sys, json, os, time
sys.path.insert(0, r'C:\Buscar Termos en plano\programa')
from core import process
from instructivo import build, conductors, fmt_terminal, known_tags, leer_json_trabajo, leer_bornes_manuales
import topo
JOB, OUT = sys.argv[1], sys.argv[2]
t0 = time.time()
est = json.load(open(os.path.join(JOB, 'estado.json'), encoding='utf-8'))
res = process(os.path.join(JOB, est['archivo']), log=lambda m: None)
t_func = time.time() - t0
if '--relayout' in sys.argv or not os.path.exists(os.path.join(JOB, 'layout.json')):
    lay = topo.layout(os.path.join(JOB, 'topografico.pdf'), known_tags(res), log=lambda m: None)
else:
    lay = json.load(open(os.path.join(JOB, 'layout.json'), encoding='utf-8'))
ij = os.path.join(JOB, 'instructivo.json')
old = json.load(open(ij, encoding='utf-8')) if os.path.exists(ij) else {}
# overrides de 'Componentes y orden' (igual que gen_instructivo)
for tag, o in (old.get('overrides') or {}).items():
    c = lay['comp'].setdefault(tag, dict(x=0, y=0, leido='')); c['ubic'] = o.get('ubic', c.get('ubic', 'LI'))
    if c['ubic'] == 'BANDEJA':
        c['fila'] = int(o.get('fila') or c.get('fila') or 1)
        if o.get('x') not in (None, ''):
            c['x'] = float(o['x'])
        if o.get('lado') in ('ARRIBA', 'ABAJO'):
            c['lado'] = o['lado']
# correcciones.json (igual que gen_instructivo: ilegible -> se ignora con aviso; 'agregar' antes del mapeo)
avisos_archivos = []
corr = leer_json_trabajo(os.path.join(JOB, 'correcciones.json'), avisos_archivos)
if not isinstance(corr, dict):
    corr = None
if corr:
    for tag, c in (corr.get('componentes') or {}).items():
        try:
            lay['comp'][tag] = dict(lay['comp'].get(tag) or {}, ubic='BANDEJA', fila=c['fila'], x=c['x'], y=c['y'], leido=tag)
        except (TypeError, KeyError):
            avisos_archivos.append(f"correcciones.json: el componente '{tag}' no tiene fila, x e y; se ignora")
    for k in ('agregar', 'pendientes_agregar', 'pendientes_texto', 'pendientes_quitar', 'sueltos_quitar', 'accesorios'):
        lay[k] = corr.get(k) or ([] if k != 'pendientes_texto' else {})
lay['bornes_usuario'] = old.get('bornes_usuario') or {}
t1 = time.time()
mapeo = None
if '--sin-mapeo' in sys.argv:
    lay['bornes'], lay['renombrar'] = leer_bornes_manuales(JOB, avisos_archivos, corr=corr if corr else {})
else:
    try:
        import bornes as mapeo_bornes
        mapeo = mapeo_bornes.aplicar_al_layout(res, lay, JOB, os.path.join(JOB, 'topografico.pdf'), cache='--con-cache' in sys.argv,
                                               usuario=lay['bornes_usuario'])
    except Exception as e:      # el mismo respaldo que gen_instructivo: se arma como sin mapeo
        import traceback
        mapeo = dict(error=f'{type(e).__name__}: {e}', detalle=traceback.format_exc(), avisos=[f'el mapeo automatico de bornes fallo ({e})'],
                     n_puntos={}, modelos={}, usados=0)
        for k in ('bornes', 'renombrar', 'bornes_conf', 'bornes_nota', 'renombrar_auto'):
            lay.pop(k, None)
        lay['bornes'], lay['renombrar'] = leer_bornes_manuales(JOB, mapeo['avisos'], corr=corr if corr else {})
    mapeo['avisos'] = list(dict.fromkeys(avisos_archivos + list(mapeo.get('avisos') or [])))
t_mapeo = time.time() - t1
lay['estaciones'] = old.get('estaciones') or {}; lay['estacion'] = old.get('estacion') or 'E6'
lay['estacion_auto'] = old.get('estacion_auto') or {'seccion_min': 35, 'estacion': 'E8'}
ins = build(res, lay)
lado_fisico = ins.pop('lado_fisico', None) or []
if mapeo is not None:
    mapeo['lado_fisico'] = lado_fisico
cs = conductors(res)
out = dict(
    lineas=[dict(num=l['num'], cable=l['cable'], origen=l['origen'], destino=l['destino'], ruta=bool(l.get('ruta')), exacto=bool(l.get('exacto_o'))) for p in ins['pasos'] for l in p['lineas']],
    pendientes=[dict(num=x['num'], a=x['a'], b=x['b']) for x in ins['pendientes']], sueltos=ins['sueltos'],
    otra_estacion=[dict(num=l['num'], origen=l['origen'], destino=l['destino']) for l in ins['otra_estacion']],
    extremos={n: sorted(fmt_terminal(c['nodes'][k]) for k in c['bornes']) for n, c in cs.items()},
    layout=dict(pag=lay.get('pag'), region=lay.get('region'), filas=lay.get('filas'), escala=lay.get('escala'), ductos=len(lay.get('ductos') or []),
                comp={t: dict(ubic=c.get('ubic'), fila=c.get('fila'), x=c.get('x'), leido=c.get('leido')) for t, c in lay['comp'].items()}),
    cables=sorted({d['num'] for d in res.detail}), n_detalle=len(res.detail), segundos=round(time.time() - t0, 1),
    # detalle de las puntas (no entra en la comparacion de 'lineas')
    puntas=[dict(num=l['num'], origen=l['origen'], destino=l['destino'], marca_o=l.get('marca_o'), marca_d=l.get('marca_d'),
                 exacto_o=l.get('exacto_o'), exacto_d=l.get('exacto_d'), conf_o=l.get('conf_o'), conf_d=l.get('conf_d'),
                 nota_o=l.get('nota_o'), nota_d=l.get('nota_d'), func_o=l.get('func_o'), func_d=l.get('func_d'), ruta=l.get('ruta'))
            for p in ins['pasos'] for l in p['lineas']],
    mapeo=mapeo, renombrar_auto=lay.get('renombrar_auto') or {}, lado_fisico=lado_fisico, avisos_archivos=avisos_archivos,
    tiempos=dict(funcional=round(t_func, 1), mapeo=round(t_mapeo, 2), total=round(time.time() - t0, 1)))
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
m = mapeo or {}
print(f"{len(out['lineas'])} lineas ({sum(l['ruta'] for l in out['lineas'])} con ruta), {len(out['pendientes'])} pendientes, {len(out['sueltos'])} sueltos, "
      f"{len(out['cables'])} cables, layout pag {out['layout']['pag']} filas {out['layout']['filas']} ductos {out['layout']['ductos']} escala {out['layout']['escala']} -> {OUT} ({out['segundos']} s)")
if mapeo is not None:
    print(f"mapeo: {m.get('n_puntos')} usados {m.get('usados')} (con punto manual {m.get('manuales')}{', motor no corrido: todos con punto manual' if m.get('omitido') else ''}), "
          f"{m.get('segundos')} s{' (cache)' if m.get('de_cache') else ''}, error {m.get('error')}; tiempo del paso de mapeo {out['tiempos']['mapeo']} s")
