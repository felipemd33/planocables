# Verificacion independiente de los puntos de la familia 'protecciones'
import json, math, pickle
from circ import fit
tr = pickle.load(open('strokes7.pkl', 'rb'))
REF = json.load(open('../bornes_referencia.json', encoding='utf-8'))

def trazos(win, capas=('COMPONENTES', '00_COMPONENTS')):
    x0, y0, x1, y1 = win
    for lay, op, pts, col in tr:
        if lay not in capas or op != 'S' or len(pts) < 5: continue
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if min(xs) >= x0 and max(xs) <= x1 and min(ys) >= y0 and max(ys) <= y1:
            yield pts, col

def circulos_cerrados(win, rmin, rmax):
    out = []
    for pts, col in trazos(win):
        f = fit(pts)
        if f and rmin <= f[2] <= rmax and f[3] < 0.02 and f[4] > 300:
            if not any(abs(o[0]-f[0]) < .3 and abs(o[1]-f[1]) < .3 and abs(o[2]-f[2]) < .2 for o in out):
                out.append((round(f[0], 2), round(f[1], 2), round(f[2], 2)))
    return sorted(out)

def bocas_pushin(win):
    """bocas push-in: dos arcos (sup e inf) de r~2.04 con centros separados ~0.4 pt; centro = medio del contorno"""
    arcs = []
    for pts, col in trazos(win):
        f = fit(pts)
        if f and 1.9 <= f[2] <= 2.2 and f[3] < 0.02 and f[4] > 80:
            ys = [p[1] for p in pts]
            arcs.append((f[0], f[1], min(ys), max(ys)))
    arcs.sort(key=lambda a: -a[1])
    grupos = []
    for a in arcs:
        if grupos and abs(grupos[-1][-1][1] - a[1]) < 1.0: grupos[-1].append(a)
        else: grupos.append([a])
    res = []
    for g in grupos:
        lo = min(a[2] for a in g); hi = max(a[3] for a in g)
        res.append((round(sum(a[0] for a in g)/len(g), 2), round((lo+hi)/2, 2), round((hi-lo)/2, 2)))
    return res

# 11Q1 / 11Q2: tornillos r~2.48 en filas arriba/abajo
q = circulos_cerrados((640, 640, 700, 712), 2.3, 2.7)
print('tornillos 11Q:', q)
cols = sorted(set(c[0] for c in q))
arr = {c[0]: c for c in q if c[1] > 680}; aba = {c[0]: c for c in q if c[1] < 680}
# cajas de etiquetas (capa _IGV_Componentes Txt, relleno blanco): 11Q1 646.7-664.5, 11Q2 671.6-689.3
etq = {'11Q1': 646.7, '11Q2': 671.6, 'fin': 693.3}  # 693.3 = tope (no cuenta)
c11q1 = [x for x in cols if etq['11Q1'] <= x < etq['11Q2']]
c11q2 = [x for x in cols if etq['11Q2'] <= x < etq['fin']]
print('11Q1 cols', c11q1, '11Q2 cols', c11q2)
mio = {}
mio[('11Q1 N ARRIBA', '1105')] = arr[c11q1[0]][:2]; mio[('11Q1 F ARRIBA', '1104')] = arr[c11q1[1]][:2]
mio[('11Q1 N ABAJO', '1107')] = aba[c11q1[0]][:2]; mio[('11Q1 F ABAJO', '1106')] = aba[c11q1[1]][:2]
mio[('11Q2 F ARRIBA', '1106')] = arr[c11q2[0]][:2]; mio[('11Q2 N ARRIBA', '1107')] = arr[c11q2[1]][:2]
mio[('11Q2 F ABAJO', '1108')] = aba[c11q2[0]][:2]; mio[('11Q2 N ABAJO', '1109')] = aba[c11q2[1]][:2]
# DF101: tornillos r~1.92
f = circulos_cerrados((765, 640, 795, 710), 1.8, 2.0)
print('tornillos DF101:', f)
# etiquetas 12F1 770.7-776.1, 13F3 783.1-788.6, 31XAI 792.9-798.4
a12 = [c for c in f if 770.7 <= c[0] < 783.1]; a13 = [c for c in f if 783.1 <= c[0] < 792.9]
mio[('12F1 ARRIBA', '1201')] = max(a12, key=lambda c: c[1])[:2]; mio[('12F1 ABAJO', '1202')] = min(a12, key=lambda c: c[1])[:2]
mio[('13F3 ARRIBA', '1206')] = max(a13, key=lambda c: c[1])[:2]; mio[('13F3 ABAJO', '1301')] = min(a13, key=lambda c: c[1])[:2]
# 31XAI: primera pieza a la derecha de la etiqueta (792.9) -> borne 799.2-803.5
b = bocas_pushin((799.0, 636, 803.8, 712))
print('bocas 31XAI (x, y, r):', b)
ext_sup, int_sup, int_inf, ext_inf = b
mio[('31XAI 1 ARRIBA', '2142')] = ext_sup[:2]; mio[('31XAI F1 ARRIBA', '1324')] = int_sup[:2]
mio[('31XAI F1 ABAJO', '3141')] = int_inf[:2]; mio[('31XAI 1 ABAJO', '3142')] = ext_inf[:2]
mio[('31XAI 1 ARRIBA', '3141')] = ext_sup[:2]  # texto literal (erroneo)
# 12F2 MEGA: esparragos r~8.1
m = circulos_cerrados((560, 285, 650, 325), 7.9, 8.3)
print('esparragos 12F2:', m)
izq, der = sorted(m)[0], sorted(m)[-1]
mio[('12F2', '1215')] = izq[:2]; mio[('12F2 ARRIBA', '1204')] = der[:2]
mio[('12F2', '1204')] = der[:2]; mio[('12F2', '1216')] = izq[:2]

print()
print('%-18s %-5s %-6s %-18s %-18s %s' % ('texto', 'cable', 'conf', 'referencia', 'verificado', 'dif pt'))
for p in REF['puntos']:
    if p['familia'] != 'protecciones': continue
    k = (p['texto'], p['cables'][0])
    v = mio.get(k)
    d = math.hypot(v[0]-p['x'], v[1]-p['y']) if v else None
    print('%-18s %-5s %-6s (%7.2f,%7.2f) %-18s %s' % (k[0], k[1], p['confianza'], p['x'], p['y'],
          '(%7.2f,%7.2f)' % v if v else '-', '%.2f' % d if d is not None else '-'))
json.dump({'%s#%s' % k: list(v) for k, v in mio.items()}, open('puntos_verificados.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
