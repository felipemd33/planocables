"""Pruebas de la ronda 2 del TPT (72715 REV.8 + topografico 72887 REV.7), 2026-10-02: topografico y listado.
No escribe nada en los trabajos. Termina con error si alguna falla.
uso: python pruebas/probar_ronda2_topo.py
     (PLANOCABLES_PROGRAMA=<carpeta> prueba otra copia del programa; por defecto la de este repositorio)
  A. topografico: rieles DIN reconocidos por el perfil en cualquier capa (el riel 1 izquierdo del 72887 esta en la
     capa '01'), la bandeja con todos los rieles de su placa (el riel 2 intrinseco) y las etiquetas verticales
     partidas ('1', '1', 'XP' = 11XP, en el lateral derecho). En el instructivo, los cables con las dos puntas en la
     bandeja segun la verdad del funcional salen como lineas de bandeja a bandeja.
  B. listado, columna 'Puntas': sin las puntas de las alternativas que no se cablean (1313/1314) ni las flechas que
     siguen en la misma hoja (1319).
  C. listado: 1204 no hereda el 'Rojo 35' del tramo de 1205 por la union en T con diagonal (un solo renglon, Rojo 4).
  D. el 8104 de la hoja 21, pegado al cable que baja a la flecha, queda asociado a su cable."""
import os, sys, json, collections
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.environ.get('PLANOCABLES_PROGRAMA') or os.path.join(RAIZ, 'programa'))
from core import process
import instructivo, topo

JOB = os.path.join(RAIZ, 'pruebas', 'trabajos', 'tpt')
VERDAD = os.path.join(RAIZ, 'pendiente', 'tpt_diagnostico', 'verdad_tpt.json')
fallas = []


def chequear(ok, msg):
    print(('  ok    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)


print('A0. funciones del topografico con datos armados')
L = lambda t, ang, bb, capa='Texto etiquetas': dict(text=t, ang=ang, bbox=bb, layer=capa)
lineas = [L('XP', 90, (1020.4, 503.0, 1023.2, 507.6)), L('1', 0, (1020.4, 500.9, 1023.2, 501.5)),
          L('1', 0, (1020.4, 498.7, 1023.2, 499.4)), L('3XC1', 90, (705.4, 574.2, 708.2, 583.1)),
          L('1', 0, (705.4, 572.0, 708.2, 572.7)), L('1', 0, (687.8, 590.0, 690.7, 590.6)),   # '1' lejos: no se une
          L('2XP', 90, (687.8, 576.1, 690.7, 583.4)), L('1', 0, (900, 500, 900, 501))]
u = topo.unir_partidas(lineas)
textos = sorted(l['text'] for l in u)
chequear('11XP' in textos and '13XC1' in textos and '2XP' in textos, f'etiquetas unidas: {textos}')
chequear(sum(1 for l in u if l['text'] == '1') == 2, 'los "1" que no son de una etiqueta quedan sueltos')
rect = lambda capa, x0, y0, x1, y1: (capa, 'S', [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
st = [rect('_IGV_Riel DIN', 612.3, 568.3, 762.6, 587.9), rect('01', 476.3, 566.9, 589.7, 586.5),
      rect('_IGV_Ductos', 400, 540, 800, 559.6), rect('01', 490, 570, 520, 574),          # canaleta / ranura
      rect('0', 500, 300, 560, 318.5)]                                                     # otro perfil (-5.6 %)
b = topo.rail_bands(st)
g = topo.rieles_geometria(st, b)
chequear(len(b) == 1 and [(round(x['x0']), round(x['x1'])) for x in g] == [(476, 590)],
         f"riel en la capa '01' con el perfil del riel (19.56 pt): {[(round(x['x0']), round(x['x1']), round(x['H'], 2)) for x in g]}")
tabla = [rect('0', 80, 228, 843, 231.93), rect('0', 80, 300, 843, 303.93)]
chequear(topo.rieles_geometria(tabla, []) == [], 'sin capa de riel: las rayas largas de una tabla (1:25) no son rieles')
sin_capa = [rect('0', 592.3, 560.8, 742.6, 580.4), rect('0', 456.3, 560.8, 569.7, 580.4)]
chequear(len(topo.rieles_geometria(sin_capa, [])) == 2, 'sin capa de riel: dos perfiles de 35 mm a 1:5 son rieles')

print('A. topografico del TPT (72887, hoja 4)')
est = json.load(open(os.path.join(JOB, 'estado.json'), encoding='utf-8'))
res = process(os.path.join(JOB, est['archivo']), log=lambda m: None)
lay = topo.layout(os.path.join(JOB, 'topografico.pdf'), instructivo.known_tags(res), log=lambda m: None)
comp = lay['comp']
ub = lambda t: (comp.get(t) or {}).get('ubic'), lambda t: (comp.get(t) or {}).get('fila')
chequear(lay['pag'] == 4 and len(lay['filas']) == 2, f"bandeja en la hoja 4 con 2 rieles: hoja {lay['pag']}, filas {lay['filas']}")
for t in ('11Q1', '11PS1', '13PS3', '33MX01', '12F1', '61XDIO'):
    chequear(ub[0](t) == 'BANDEJA' and ub[1](t) == 1, f'{t}: riel 1 ({ub[0](t)}, fila {ub[1](t)})')
for t in ('43DIB1', '43XDIB'):
    chequear(ub[0](t) == 'BANDEJA' and ub[1](t) == 2, f'{t}: riel 2, intrinseco ({ub[0](t)}, fila {ub[1](t)})')
for t in ('11XP', '13XC2', '16XC', '81XCM'):
    c = comp.get(t) or {}
    chequear(c.get('ubic') == 'LI' and c.get('lateral') == 'DERECHO', f"{t}: lateral derecho (LD) ({c.get('ubic')}, {c.get('lateral')}, leido {c.get('leido')})")
for t in ('PT 001', 'BH-01-ZV', '12PB1'):
    chequear(ub[0](t) == 'LI', f'{t}: fuera de los rieles ({ub[0](t)})')
chequear(lay['region'] == [456.4, 236.5, 762.6, 644.7] and len(lay['ductos']) == 5, f"placa y canaletas: {lay['region']}, {len(lay['ductos'])}")

print('A2. instructivo del TPT contra la verdad del funcional')
lay.update(bornes_usuario={}, estaciones={}, estacion='E6', estacion_auto={'seccion_min': 35, 'estacion': 'E8'})
ins = instructivo.build(res, json.loads(json.dumps(lay)))
lin = collections.defaultdict(list)
for p in ins['pasos']:
    for l in p['lineas']:
        lin[l['num']].append(l)
V = json.load(open(VERDAD, encoding='utf-8'))['cables']
bb = [n for n, v in V.items() if v.get('ubic') and all(x.startswith('BANDEJA') for x in v['ubic'].values())]
ok = [n for n in bb if lin[n] and all(l['destino'] not in ('LI', 'LD') for l in lin[n])]
chequear(len(bb) == 19 and len(ok) == 19, f'cables con todas las puntas en la bandeja: {len(ok)}/{len(bb)} como lineas de bandeja a bandeja '
         f'(faltan {sorted(set(bb) - set(ok))})')
tipo = lambda v, p: 'B' if v['ubic'].get(p, '').startswith('BANDEJA') else v['ubic'].get(p, 'LI')
ld = [n for n, v in V.items() if v.get('ubic') and any({tipo(v, a), tipo(v, b_)} == {'B', 'LD'} for a, b_ in v.get('tramos') or [])]
ld_ok = [n for n in ld if any(l['destino'] == 'LD' for l in lin[n])]
chequear(len(ld_ok) == len(ld), f'bandeja -> lateral derecho: {len(ld_ok)}/{len(ld)} con destino LD (faltan {sorted(set(ld) - set(ld_ok))})')

print('B. columna Puntas del listado')
cab = {}
for c in res.cables:
    cab.setdefault(c['num'], []).append(c)
for n, esp in (('1313', 2), ('1314', 2), ('1319', 2), ('1310', 3), ('6101', 3), ('1206', 3)):
    got = sorted({c['puntas'] for c in cab.get(n, [])})
    chequear(got == [esp], f'{n}: {got} puntas (esperado {esp})')
chequear(all(c['puntas'] <= 3 for c in res.cables), f"ningun cable del TPT con mas de 3 puntas: {[(c['num'], c['puntas']) for c in res.cables if c['puntas'] > 3]}")

print('C. 1204 sin el Rojo 35 de 1205')
r1204 = [(c['color'], c['sec']) for c in cab.get('1204', [])]
chequear(r1204 == [('Rojo', '4')], f'1204: {r1204} (un renglon, Rojo 4)')
chequear(not any(r.get('num') == '1204' for r in res.review), 'sin "1204: Rojo 35 | Rojo 4" en A revisar')
chequear([(c['color'], c['sec']) for c in cab.get('1205', [])] == [('Rojo', '35')], '1205 sigue Rojo 35')
chequear(any(r.get('num') == '1206' for r in res.review), '1206 (negro 4 + negro 35, 3 puntas reales) sigue en A revisar')

print('D. 8104 de la hoja 21 asociado a su cable')
d8104 = [d for d in res.detail if d['num'] == '8104' and d['hoja'] == '21']
chequear(len(d8104) == 1, f'8104 en la hoja 21: {len(d8104)} aparicion(es)')
chequear(not any(r['texto'] == '8104' for r in res.review), 'sin "Numero sin cable asociado: 8104"')
chequear(any(d['num'] == '8103' and d['hoja'] == '21' for d in res.detail), '8103 de la hoja 21 sigue asociado')

print()
print('TODO OK' if not fallas else f'{len(fallas)} FALLA(S)')
sys.exit(1 if fallas else 0)
