# -*- coding: utf-8 -*-
"""Verificacion independiente de puntos_riel3_lateral.json (76884, pag. 8).
- Cobertura contra conexiones.json (todas las puntas de la zona).
- Cada punto contra la geometria propia: contornos cerrados y circulos ajustados a los arcos (primitivas).
- Escribe correcciones_riel3_lateral.json y verif_riel3_lateral.png.
"""
import json, math, sys
sys.path.insert(0, r'C:/Buscar Termos en plano/programa')
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium
from bornes import primitivas as pr
import geo

MAP = r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/'
PDF = r'C:/Buscar Termos en plano/1 - Planos/Producto nuevo/ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.pdf'
P = json.load(open(MAP + 'puntos_riel3_lateral.json', encoding='utf-8'))
C = json.load(open(MAP + 'conexiones.json', encoding='utf-8'))
ZONA = {'15XR', '42XC', '81XCM', '32XEX', '41XEX', '12PS1', '12XPS', '11SK1', '11Q1', '11Q2', '11XPVAC', '11X220V'}

# ---------------------------------------------------------------- cobertura
ends = set()
for r in C['conexiones']:
    for k in ('d1', 'd2'):
        if r[k + '_tag'] in ZONA:
            ends.add((r[k], r['fila']))
mapeadas = set((p['d'], f) for p in P['puntos'] for f in p['filas_lista'])
faltan = sorted(ends - mapeadas)
sobran = sorted(mapeadas - ends)

# ---------------------------------------------------------------- geometria propia
G = {n: geo.geo(n) for n in geo.REG}
CIR = {n: pr.circulos(G[n]['arc'], 0.8, 4.0, cob_min=120) for n in G}


def zona(x, y):
    for n, (x0, y0, x1, y1) in geo.REG.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            return n


def mejor_rasgo(x, y, r):
    z = zona(x, y)
    if not z:
        return None
    cand = []
    for c in G[z]['cont']:
        if 1.5 < c['w'] < 8 and 1.5 < c['h'] < 8:
            cand.append((math.hypot(c['x'] - x, c['y'] - y), 'contorno %.2fx%.2f' % (c['w'], c['h']), c['x'], c['y']))
    for c in CIR[z]:
        if abs(c['r'] - r) < 0.6:
            cand.append((math.hypot(c['x'] - x, c['y'] - y), 'circulo r%.2f' % c['r'], c['x'], c['y']))
    return min(cand) if cand else None


# correcciones con evidencia: 11Q2 tornillos de abajo. Envolvente del hexagono y centro de la cruz
# en y 358.69 (igual que 11Q1 abajo y simetrico con los de arriba en 408.17); el punto estaba en 358.56.
CORR = {}
for d, cable in (('-11Q2:2', '1158'), ('-11Q2:4', '1159')):
    p = next(q for q in P['puntos'] if q['d'] == d)
    c = [c for c in G['lat_bajo']['cont'] if abs(c['x'] - p['x']) < 0.3 and abs(c['y'] - p['y']) < 0.5][0]
    CORR[d] = dict(d=d, cable=cable, x=round(c['x'], 2), y=round(c['y'], 2),
                   motivo=('Ajuste fino (0,13 pt, sin cambio de borne): el tornillo hexagonal de abajo de 11Q2 tiene '
                           'envolvente %.2f-%.2f en y (centro %.2f), igual que el centro de su cruz y que los tornillos de '
                           'abajo de 11Q1 (y 358,69); el punto estaba en y %.2f.' % (c['bb'][1], c['bb'][3], c['y'], p['y'])),
                   texto_taller=p['texto_taller'])

filas = []
for p in P['puntos'] + P['extra_esquema']:
    m = mejor_rasgo(p['x'], p['y'], p['r'])
    filas.append((p, m))

if __name__ == '__main__':
    print('puntas de la zona en conexiones.json:', len(ends), ' puntos:', len(P['puntos']))
    print('faltan:', faltan)
    print('sobran:', sobran)
    for p, m in filas:
        s = 'SIN RASGO' if m is None else '%.3f %s (%.2f,%.2f)' % m
        print('%-15s %-28s %-22s %s' % (p['d'], p['cables'][0][:28], p['texto_taller'], s))
    out = dict(
        zona='BANDEJA PRINCIPAL riel 3 (15XR, 42XC, 81XCM, 32XEX, 41XEX) + BANDEJA LATERAL IZQUIERDA (12PS1, 12XPS, 11SK1, 11Q1, 11Q2, 11XPVAC, 11X220V)',
        archivo_verificado='puntos_riel3_lateral.json (%d puntos + %d extra_esquema)' % (len(P['puntos']), len(P['extra_esquema'])),
        correcciones=list(CORR.values()))
    try:  # conservar el texto de verificacion y las dudas escritos a mano
        prev = json.load(open(MAP + 'correcciones_riel3_lateral.json', encoding='utf-8'))
        for k in ('verificacion', 'dudas'):
            if k in prev:
                out[k] = prev[k]
    except Exception:
        pass
    json.dump(out, open(MAP + 'correcciones_riel3_lateral.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
