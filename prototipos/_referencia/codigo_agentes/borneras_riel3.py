"""Deteccion de los puntos de conexion de borneras Phoenix Contact PTT 2,5-2MT (gris, 3210258)
y PTT 2,5-2MT BU (azul, 3210265) -- borne seccionable push-in de DOBLE PISO -- en el plano
topografico vectorial (Batfer / AutoCAD -> PDF).

Uso rapido:
    import borneras_riel3 as br
    res, grupos, piezas = br.ubicar(r'...\\usos_por_componente.json', pdf=r'...\\topo.pdf', pi=7,
                                    tags=['43XCS', '46XC', '81XCM', '31XEX', '43XDI'])
    # res: [{'componente','texto','cable','x','y','confianza','como',...}]  (x, y en puntos PDF)

Hechos (hoja de datos Phoenix 3210265 / 3210258 + fotos tablero 75286-1):
  * 2 pisos, 4 conexiones, 2 potenciales; ancho 5,2 mm (= 3,66 pt en este plano), largo 92,4 mm.
  * Cada piso tiene una conexion en el extremo de ARRIBA y otra en el de ABAJO.
  * Piso de abajo (nivel 1, linea larga del esquema) -> entradas del EXTREMO de la pieza
    (las mas alejadas del riel). Piso de arriba (nivel 2) -> entradas INTERIORES (mas cerca del riel,
    en la parte elevada). En la pieza real la fila interior lleva impresos 2, 4, 6, 8, 10, 12, 14.
  * Numeracion: pieza k (contando izq -> der a partir de la etiqueta amarilla, SIN contar la pieza
    verde/amarilla de tierra PT 2,5-QUATTRO-PE) = bornes 2k-1 (impar, extremo) y 2k (par, interior).
  * "N ARRIBA" = extremo superior de la pieza; "N ABAJO" = extremo inferior.

Geometria en el dibujo: cada entrada de conductor es un octogono (~3,4 x 3,8 pt) con una abertura en
"U" adentro: linea plana (doble/triple) del lado exterior + dos verticales separadas ~2,13 pt + arco.
El punto de conexion devuelto es el centro de esa U (= el agujero donde entra el conductor).
"""
import sys, json, re
from collections import defaultdict

PROG = r'C:\Buscar Termos en plano\programa'
if PROG not in sys.path:
    sys.path.insert(0, PROG)

U_ANCHO = (1.9, 2.4)      # ancho de la abertura U en pt (2,13 pt = 3 mm)
TOL = 0.05
PASO_PIEZA = 3.66         # 5,2 mm


def cargar_trazos(pdf, pi):
    import pypdf
    from pdfvec import page_strokes, layer_names
    r = pypdf.PdfReader(pdf)
    return page_strokes(r, pi, layer_names(r), with_color=True)


def segmentos(pdf, pi, box=None, strokes=None):
    """[(p0, p1, capa, color)] de los trazos 'S' completamente dentro de box (x0, y0, x1, y1)."""
    if strokes is None:
        strokes = cargar_trazos(pdf, pi)
    out = []
    for l, o, p, c in strokes:
        if o != 'S' or not p:
            continue
        if box and not all(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in p):
            continue
        cc = tuple(round(v, 2) for v in c) if c else None
        for a, b in zip(p, p[1:]):
            out.append((a, b, l, cc))
    return out


def entradas(segs):
    """Aberturas U de entrada de conductor -> [{'x','y','color','u':(x0,y0,x1,y1)}]."""
    H = [s for s in segs if abs(s[0][1] - s[1][1]) < 0.02 and U_ANCHO[0] <= abs(s[0][0] - s[1][0]) <= U_ANCHO[1]]
    V = [s for s in segs if abs(s[0][0] - s[1][0]) < 0.02 and abs(s[0][1] - s[1][1]) > 0.3]
    vx = defaultdict(list)
    for v in V:
        vx[round(v[0][0], 1)].append(v)

    def verts(x, y):
        res = []
        for k in (round(x, 1) - 0.1, round(x, 1), round(x, 1) + 0.1):
            for v in vx.get(round(k, 1), []):
                if abs(v[0][0] - x) < TOL:
                    y0, y1 = sorted((v[0][1], v[1][1]))
                    if abs(y0 - y) < TOL:
                        res.append(y1)
                    elif abs(y1 - y) < TOL:
                        res.append(y0)
        return res

    pts = []
    for h in H:
        xl, xr = sorted((h[0][0], h[1][0]))
        y = (h[0][1] + h[1][1]) / 2
        L, R = verts(xl, y), verts(xr, y)
        if not L or not R:
            continue
        d = 1 if (L[0] - y) > 0 else -1          # desde la linea plana hacia el arco de la U
        if (R[0] - y) * d <= 0:
            continue
        tip, flat = y, y
        for a, b, _, _ in segs:
            for (px, py) in (a, b):
                if xl - TOL <= px <= xr + TOL:
                    t = (py - y) * d
                    if 0 < t <= 2.0 and xl + 0.1 < px < xr - 0.1:
                        tip = y + d * max((tip - y) * d, t)
                    if -0.4 <= t < 0 and abs(a[1] - b[1]) < 0.02 and abs(abs(a[0] - b[0]) - (xr - xl)) < 0.1:
                        flat = y + d * min((flat - y) * d, t)
        pts.append({'x': (xl + xr) / 2, 'y': (tip + flat) / 2, 'color': h[3],
                    'u': (xl, min(tip, flat), xr, max(tip, flat))})
    uniq = []                                    # las lineas planas son dobles/triples
    for p in sorted(pts, key=lambda p: (p['x'], p['y'])):
        if not any(abs(p['x'] - q['x']) < 0.3 and abs(p['y'] - q['y']) < 0.5 for q in uniq):
            uniq.append(p)
    return uniq


def es_verde(c):
    return c is not None and c[1] > 0.4 and c[0] < 0.3 and c[2] < 0.3


def piezas(segs, excluir_verde=True):
    """Una pieza = una columna de 4 entradas. Devuelve [{'x','color','ymid','arriba':[ext,int],
    'abajo':[ext,int],'n'}] ordenadas izq -> der. ext = entrada del extremo, int = interior."""
    E = [e for e in entradas(segs) if not (excluir_verde and es_verde(e['color']))]
    cols = []
    for e in sorted(E, key=lambda e: e['x']):
        if cols and abs(e['x'] - cols[-1][-1]['x']) < 0.8:
            cols[-1].append(e)
        else:
            cols.append([e])
    out = []
    for c in cols:
        ys = sorted(c, key=lambda e: e['y'])
        if len(ys) < 2:
            continue
        g, i = max((ys[j + 1]['y'] - ys[j]['y'], j) for j in range(len(ys) - 1))  # el riel queda en la brecha
        bajo, alto = ys[:i + 1], ys[i + 1:]
        out.append({'x': sum(e['x'] for e in c) / len(c), 'color': c[0]['color'],
                    'ymid': (bajo[-1]['y'] + alto[0]['y']) / 2,
                    'arriba': sorted(alto, key=lambda e: -e['y']),
                    'abajo': sorted(bajo, key=lambda e: e['y']),
                    'n': len(c)})
    return out


def num_borne(b):
    m = re.match(r'\s*(\d+)', str(b))
    return int(m.group(1)) if m else None


def grupo_de(etiqueta, pz_todas, x_limite):
    """Piezas de un componente: a la derecha de su etiqueta amarilla, antes de la etiqueta siguiente
    del mismo riel, y que cruzan en vertical la altura de la etiqueta."""
    ex, ey = etiqueta['x'], etiqueta['y']
    sel = []
    for p in pz_todas:
        if ex < p['x'] < x_limite:
            ys = [e['y'] for e in p['arriba'] + p['abajo']]
            if min(ys) - 5 <= ey <= max(ys) + 5:
                sel.append(p)
    sel.sort(key=lambda p: p['x'])
    avisos = []
    for a, b in zip(sel, sel[1:]):
        if b['x'] - a['x'] > 1.5 * PASO_PIEZA:
            avisos.append(f'hueco entre piezas en x={a["x"]:.1f}..{b["x"]:.1f}')
    return sel, avisos


def ubicar(usos_json, pdf, pi, tags, box=None, strokes=None, confirmados=None):
    """confirmados: {tag: 'texto de como se confirmo'} -> confianza alta; resto media."""
    d = json.load(open(usos_json, encoding='utf-8')) if isinstance(usos_json, str) else usos_json
    C = d['componentes']
    confirmados = confirmados or {}
    if box is None:
        xs = [C[t]['etiqueta_topografico']['x'] for t in tags]
        ys = [C[t]['etiqueta_topografico']['y'] for t in tags]
        box = (min(xs) - 5, min(ys) - 60, max(xs) + 60, max(ys) + 60)
    segs = segmentos(pdf, pi, box, strokes)
    pz = piezas(segs)
    riel = C[tags[0]]['etiqueta_topografico'].get('riel')
    todas = sorted((v['etiqueta_topografico']['x'], k) for k, v in C.items()
                   if v.get('etiqueta_topografico') and v['etiqueta_topografico'].get('riel') == riel)
    res, grupos = [], {}
    for t in tags:
        et = C[t]['etiqueta_topografico']
        sig = [x for x, k in todas if x > et['x'] + 0.5]
        g, avisos = grupo_de(et, pz, min(sig) if sig else 1e9)
        grupos[t] = g
        for u in C[t]['usos']:
            n = num_borne(u['borne'])
            lado = 'arriba' if str(u.get('lado') or u.get('parte') or '').upper().startswith('ARR') else 'abajo'
            item = dict(componente=t, texto=u['texto'], cable=u['cable'], x=None, y=None,
                        confianza='baja', como='')
            if n is None:
                item['como'] = 'borne sin numero en el texto'
                res.append(item); continue
            k = (n + 1) // 2
            if k > len(g):
                item['como'] = f'pieza {k} no existe en el dibujo ({len(g)} piezas tras la etiqueta)'
                res.append(item); continue
            p = g[k - 1]
            lst = p[lado]
            if len(lst) < 2:
                item['como'] = f'pieza {k}: solo {len(lst)} entradas detectadas del lado {lado}'
                res.append(item); continue
            e = lst[0] if n % 2 else lst[1]
            nivel = 'extremo (piso de abajo)' if n % 2 else 'interior (piso de arriba)'
            item.update(x=round(e['x'], 2), y=round(e['y'], 2), pieza=k, npiezas=len(g), nivel=nivel, lado=lado)
            base = (f'pieza {k} de {len(g)} a la derecha de la etiqueta {t} (x={p["x"]:.2f}); '
                    f'borne {n} {"impar" if n % 2 else "par"} -> entrada {nivel} del extremo {lado}; '
                    f'centro de la abertura U (x {e["u"][0]:.2f}..{e["u"][2]:.2f}, y {e["u"][1]:.2f}..{e["u"][3]:.2f})')
            if avisos:
                base += '; AVISO: ' + ', '.join(avisos)
            if t in confirmados and not avisos:
                item['confianza'] = 'alta'
                item['como'] = base + '. ' + confirmados[t]
            else:
                item['confianza'] = 'media'
                item['como'] = base + '. Sin foto del lado de la bornera: regla de hoja de datos + regla del taller.'
            res.append(item)
    return res, grupos, pz


if __name__ == '__main__':
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    usos = os.path.join(here, 'usos_por_componente.json')
    pdf = os.path.join(os.path.dirname(here), 'topo.pdf')
    res, grupos, pz = ubicar(usos, pdf, 7, ['43XCS', '46XC', '81XCM', '31XEX', '43XDI'])
    for t, g in grupos.items():
        print(t, len(g), 'piezas en x =', [round(p['x'], 2) for p in g])
    for r in res:
        print(r['texto'], r['cable'], r['x'], r['y'], r.get('nivel'))
