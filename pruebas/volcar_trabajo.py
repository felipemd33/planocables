"""Arma el instructivo de un trabajo web con el codigo ACTUAL y lo vuelca a JSON (para comparar antes/despues).
Hace lo mismo que web.py gen_instructivo (overrides, correcciones.json, mapeo automatico de bornes, bornes.json,
bornes_usuario), sin escribir en el trabajo salvo el cache del mapeo (bornes_auto.json).
uso: python volcar_trabajo.py <carpeta_trabajo> <salida.json> [--relayout] [--sin-mapeo] [--sin-cache]
  --relayout:  vuelve a leer el topografico (topo.layout) en vez de usar layout.json. Como en la web, tambien se
               vuelve a leer (sin escribir layout.json) si layout.json es de otra version del lector (topo.layout_al_dia)
  --sin-mapeo: como antes de integrar el mapeo automatico (solo bornes.json / correcciones.json)
  --sin-cache: calcula el mapeo de nuevo y no escribe bornes_auto.json"""
import os, sys, json, os, glob, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'programa'))
from core import process
from instructivo import build, conductors, fmt_terminal, known_tags
import topo
JOB, OUT = sys.argv[1], sys.argv[2]
t0 = time.time()
est = json.load(open(os.path.join(JOB, 'estado.json'), encoding='utf-8'))
res = process(os.path.join(JOB, est['archivo']), log=lambda m: None)
t_func = time.time() - t0
TOPO = os.path.join(JOB, 'topografico.pdf')
if not os.path.exists(TOPO) and getattr(res, 'eplan', False):
    TOPO = os.path.join(JOB, est['archivo'])        # EPLAN: la hoja de bandejas viene en el mismo PDF
if ('--relayout' in sys.argv or not os.path.exists(os.path.join(JOB, 'layout.json'))
        or not topo.layout_al_dia(os.path.join(JOB, 'layout.json'))):     # (como web.gen_instructivo)
    lay = topo.layout(TOPO, known_tags(res), log=lambda m: None)
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
cj = os.path.join(JOB, 'correcciones.json')
corr = json.load(open(cj, encoding='utf-8')) if os.path.exists(cj) else None
if corr:
    for tag, c in (corr.get('componentes') or {}).items():
        lay['comp'][tag] = dict(lay['comp'].get(tag) or {}, ubic='BANDEJA', fila=c['fila'], x=c['x'], y=c['y'], leido=tag)
    # (antes del mapeo, como gen_instructivo: los conductores agregados a mano tambien se ubican en el topografico)
    for k in ('agregar', 'pendientes_agregar', 'pendientes_texto', 'pendientes_quitar', 'sueltos_quitar', 'accesorios'):
        lay[k] = corr.get(k) or ([] if k != 'pendientes_texto' else {})
# (antes del mapeo, como gen_instructivo: los puntos ajustados en el visor mandan y su texto no se renombra)
lay['bornes_usuario'] = old.get('bornes_usuario') or {}
t1 = time.time()
mapeo = None
if '--sin-mapeo' in sys.argv:
    bj = os.path.join(JOB, 'bornes.json')
    if os.path.exists(bj):
        bd = json.load(open(bj, encoding='utf-8'))
        lay['bornes'] = {k: (v['xy'] + [v.get('r')]) if isinstance(v, dict) else v for k, v in bd.get('puntos', bd).items()}
        lay['renombrar'] = bd.get('renombrar') or {}
    if corr:
        lay['bornes'] = dict(lay.get('bornes') or {}); lay['bornes'].update(corr.get('bornes') or {})
elif getattr(res, 'eplan', False) and lay.get('eplan'):   # plano de EPLAN: puntos del mapeo verificado (como web.gen_instructivo)
    import eplan
    mapeo = eplan.aplicar_puntos(res, lay, JOB)
else:
    import bornes as mapeo_bornes
    mapeo = mapeo_bornes.aplicar_al_layout(res, lay, JOB, TOPO, cache='--sin-cache' not in sys.argv)
t_mapeo = time.time() - t1
lay['estaciones'] = old.get('estaciones') or {}; lay['estacion'] = old.get('estacion') or 'E6'
lay['estacion_auto'] = old.get('estacion_auto') or {'seccion_min': 35, 'estacion': 'E8'}
lay['salidas'] = old.get('salidas') or {}      # salidas a LI / LD elegidas a mano (editor de salidas)
lay['quitados'] = old.get('quitados') if isinstance(old.get('quitados'), list) else []    # quitados a mano en la web
ins = build(res, lay)
cs = conductors(res)
out = dict(
    lineas=[dict(num=l['num'], cable=l['cable'], origen=l['origen'], destino=l['destino'], ruta=bool(l.get('ruta')), exacto=bool(l.get('exacto_o'))) for p in ins['pasos'] for l in p['lineas']],
    pendientes=[dict(num=x['num'], a=x['a'], b=x['b']) for x in ins['pendientes']], sueltos=ins['sueltos'],
    otra_estacion=[dict(num=l['num'], origen=l['origen'], destino=l['destino']) for l in ins['otra_estacion']],
    extremos={n: sorted(fmt_terminal(c['nodes'][k]) for k in c['bornes']) for n, c in cs.items()},
    layout=dict(pag=lay.get('pag'), region=lay.get('region'), filas=lay.get('filas'), escala=lay.get('escala'), ductos=len(lay.get('ductos') or []),
                comp={t: dict(ubic=c.get('ubic'), fila=c.get('fila'), x=c.get('x'), leido=c.get('leido')) for t, c in lay['comp'].items()}),
    cables=sorted({d['num'] for d in res.detail}), n_detalle=len(res.detail), segundos=round(time.time() - t0, 1),
    # apariciones de numeros por hoja del PDF (un cajetin mal leido se come los numeros de una hoja)
    detalle_por_pag={str(k): v for k, v in sorted(__import__('collections').Counter(d['pag'] for d in res.detail).items())},
    solo_en_lista=sorted(d['num'] for d in res.detail if str(d.get('origen', '')).startswith('Solo en la lista')),
    # detalle de las puntas (no entra en la comparacion de 'lineas')
    puntas=[dict(num=l['num'], origen=l['origen'], destino=l['destino'], marca_o=l.get('marca_o'), marca_d=l.get('marca_d'),
                 exacto_o=l.get('exacto_o'), exacto_d=l.get('exacto_d'), conf_o=l.get('conf_o'), conf_d=l.get('conf_d'),
                 nota_o=l.get('nota_o'), nota_d=l.get('nota_d'), ruta=l.get('ruta')) for p in ins['pasos'] for l in p['lineas']],
    mapeo=mapeo, renombrar_auto=lay.get('renombrar_auto') or {},
    tiempos=dict(funcional=round(t_func, 1), mapeo=round(t_mapeo, 2), total=round(time.time() - t0, 1)))
if ins.get('quitados') or ins.get('quitados_vueltos'):     # (solo si el trabajo tiene cables quitados a mano)
    out['quitados'] = [dict(num=x['num'], origen=x.get('origen', x.get('a')), destino=x.get('destino', x.get('b')),
                            pendiente=bool(x.get('pendiente'))) for x in ins['quitados']]
    out['quitados_vueltos'] = ins.get('quitados_vueltos') or []
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
m = mapeo or {}
print(f"{len(out['lineas'])} lineas ({sum(l['ruta'] for l in out['lineas'])} con ruta), {len(out['pendientes'])} pendientes, {len(out['sueltos'])} sueltos, "
      f"{len(out['cables'])} cables, layout pag {out['layout']['pag']} filas {out['layout']['filas']} ductos {out['layout']['ductos']} escala {out['layout']['escala']} -> {OUT} ({out['segundos']} s)")
if mapeo is not None:
    print(f"mapeo: {m.get('n_puntos')} usados {m.get('usados')} (descartados por manuales {m.get('manuales')}), {m.get('segundos')} s"
          f"{' (cache)' if m.get('de_cache') else ''}, error {m.get('error')}; tiempo del paso de mapeo {out['tiempos']['mapeo']} s")
