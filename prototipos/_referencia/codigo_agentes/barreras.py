"""Bornes de barreras de seguridad intrinseca CHENZHU GS8500-EX (GS8512-EX.xx, GS8536-EX)
en el plano topografico (pagina PDF 8 de topo.pdf).

Como esta dibujada la barrera en el topografico (bloque CAD simplificado, capa COMPONENTES):
  - carcasa = rectangulo con lados verticales largos (~70 pt = 99 mm de cuerpo); ancho 8.9 pt
    (12.5 mm, GS8512) o 12.8 pt (17.5 mm, GS8536);
  - UN solo enchufe arriba y UNO abajo, cada uno con 2 tornillos (elipses de ~2.8 x 2.4 pt,
    cortadas por el borde de la carcasa) y el borde exterior del enchufe (linea horizontal).

Como es la barrera real (hoja de datos CHENZHU + fotos del tablero 3.0/3.1/3.2/3.3 y
WhatsApp 12.35.42/12.35.43):
  - ARRIBA = lado seguro (enchufes verdes, no-IS), 3 enchufes escalonados. Del borde exterior
    hacia el centro: [1 2] (alimentacion, etiqueta roja/negra), [3 4 (5)], [5 6] o [6 7 8].
  - ABAJO = lado de campo (enchufes azules, IS), 2 enchufes escalonados. Del centro hacia el
    borde exterior: [7 8] o [9 10 11]; y afuera del todo [9 10] o [12 13 14].
  - En cada enchufe el numero menor queda a la IZQUIERDA (mirando el tablero de frente).
  - El enchufe mas exterior de cada lado es el mas profundo (escalonado) y coincide con los 2
    tornillos que dibuja el topografico; los otros niveles no estan dibujados y se ubican con
    el paso entre filas de la vista frontal de la hoja de datos (fracciones de la altura total).

Uso:
    from barreras import detectar_barrera, bornes_barrera
    det = detectar_barrera(strokes, x_etiqueta, y_etiqueta)
    pos = bornes_barrera('GS8512-EX.22', det)   # {'7': (x, y, fila, dibujado), ...}
"""
import math
import os
import pickle
import sys

sys.path.insert(0, r'C:\Buscar Termos en plano\programa')

HERE = os.path.dirname(os.path.abspath(__file__))
TOPO = os.path.join(os.path.dirname(HERE), 'topo.pdf')
CACHE = os.path.join(HERE, 'barreras_strokes.pkl')
LAYERS_COMP = ('COMPONENTES', '00_COMPONENTS')

# Disposicion fisica: listas de enchufes (filas) de AFUERA hacia ADENTRO en cada lado;
# dentro de cada enchufe, de izquierda a derecha.
MODELOS = {
    'GS8512-EX.22': {'ARRIBA': [[1, 2], [3, 4], [5, 6]],
                     'ABAJO': [[9, 10], [7, 8]]},
    'GS8512-EX.12': {'ARRIBA': [[1, 2], [3, 4], [5, 6]],
                     'ABAJO': [[9, 10], [7, 8]]},
    'GS8512-EX.11': {'ARRIBA': [[1, 2], [3, 4], [5, 6]],
                     'ABAJO': [[9, 10], [7, 8]]},
    'GS8536-EX': {'ARRIBA': [[1, 2], [3, 4, 5], [6, 7, 8]],
                  'ABAJO': [[12, 13, 14], [9, 10, 11]]},
}

# Vista frontal de la hoja de datos GS8512-EX (CZ.GS8512-EX.11(S)E-5.0, pag. 3, vectorial):
# centro de cada fila de tornillos como fraccion de la altura total del aparato
# (borde exterior del enchufe superior -> borde exterior del enchufe inferior), medida desde
# el borde de su lado, de afuera hacia adentro.
FRAC_FILAS = {'ARRIBA': [0.0611, 0.1465, 0.2296],
              'ABAJO': [0.0578, 0.1351]}


def load_strokes():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    import pypdf
    from pdfvec import page_strokes, layer_names
    r = pypdf.PdfReader(TOPO)
    st = page_strokes(r, 7, layer_names(r), with_color=True)
    pickle.dump(st, open(CACHE, 'wb'))
    return st


def _bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _segs(st, x0, y0, x1, y1):
    for lay, op, pts, col in st:
        if lay not in LAYERS_COMP or not pts or len(pts) < 2:
            continue
        b = _bbox(pts)
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
            continue
        yield lay, op, pts, b


def detectar_barrera(st, xl, yl, win_x=12.0, win_y=60.0):
    """Detecta carcasa, tornillos dibujados y bordes de enchufe de la barrera cuya etiqueta
    amarilla esta en (xl, yl). Devuelve dict con left, right, body_top, body_bot, top_edge,
    bot_edge, screws_top [(x,y)], screws_bot [(x,y)]."""
    x0, x1, y0, y1 = xl - win_x, xl + win_x, yl - win_y, yl + win_y
    verts, hors, arcs = [], [], []
    for lay, op, pts, b in _segs(st, x0, y0, x1, y1):
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            if abs(ax - bx) < 0.05 and abs(ay - by) > 40:
                verts.append((ax, min(ay, by), max(ay, by)))
            if abs(ay - by) < 0.05 and abs(ax - bx) > 3:
                hors.append((ay, min(ax, bx), max(ax, bx)))
        w, h = b[2] - b[0], b[3] - b[1]
        if len(pts) >= 5 and w < 3.5 and h < 3.5:
            arcs.append((pts, b))
    # carcasa: lados verticales largos mas cercanos a la etiqueta
    lefts = [v for v in verts if v[0] < xl - 1]
    rights = [v for v in verts if v[0] > xl + 1]
    if not lefts or not rights:
        raise ValueError('no encuentro la carcasa cerca de (%.1f, %.1f)' % (xl, yl))
    L = max(lefts, key=lambda v: v[0])
    R = min(rights, key=lambda v: v[0])
    left, right = L[0], R[0]
    body_bot, body_top = max(L[1], R[1]), min(L[2], R[2])
    # arcos de tornillo: dentro de la carcasa en x y pegados al borde superior / inferior
    sides = {'ARRIBA': [], 'ABAJO': []}
    for pts, b in arcs:
        cx = (b[0] + b[2]) / 2
        if not (left < cx < right):
            continue
        if b[1] >= body_top - 0.2 and b[3] <= body_top + 4:
            sides['ARRIBA'].append((pts, b))
        elif b[3] <= body_bot + 0.2 and b[1] >= body_bot - 4:
            sides['ABAJO'].append((pts, b))
    screws = {}
    for side, lst in sides.items():
        # agrupar por solapamiento en x (cada tornillo = varios arcos: aro exterior + interior)
        lst.sort(key=lambda a: a[1][0])
        groups = []
        for pts, b in lst:
            if groups and b[0] <= groups[-1]['x1'] + 0.05:
                g = groups[-1]
                g['pts'].extend(pts)
                g['x1'] = max(g['x1'], b[2])
            else:
                groups.append({'pts': list(pts), 'x1': b[2]})
        out = []
        for g in groups:
            P = g['pts']
            xa = min(p[0] for p in P)
            xb = max(p[0] for p in P)
            if xb - xa < 1.5:  # restos sueltos
                continue
            cx = (xa + xb) / 2
            # centro vertical = altura donde el aro exterior es mas ancho
            ext = [p[1] for p in P if p[0] <= xa + 0.03 or p[0] >= xb - 0.03]
            cy = sum(ext) / len(ext)
            out.append((round(cx, 2), round(cy, 2), round((xb - xa) / 2, 2)))
        # deduplicar (el bloque aparece repetido en el PDF)
        ded = []
        for s in out:
            if not any(abs(s[0] - t[0]) < 0.3 and abs(s[1] - t[1]) < 0.3 for t in ded):
                ded.append(s)
        screws[side] = sorted(ded)
    # bordes exteriores de los enchufes
    tops = [h[0] for h in hors if h[0] > body_top + 1 and h[1] > left - 0.5 and h[2] < right + 0.5]
    bots = [h[0] for h in hors if h[0] < body_bot - 1 and h[1] > left - 0.5 and h[2] < right + 0.5]
    return {
        'left': left, 'right': right, 'body_top': body_top, 'body_bot': body_bot,
        'top_edge': max(tops) if tops else None, 'bot_edge': min(bots) if bots else None,
        'screws_top': [(s[0], s[1]) for s in screws['ARRIBA']],
        'screws_bot': [(s[0], s[1]) for s in screws['ABAJO']],
        'screw_r': [s[2] for s in screws['ARRIBA'] + screws['ABAJO']],
    }


def bornes_barrera(modelo, det):
    """Posicion (x, y) de cada borne del modelo sobre el dibujo detectado.
    Devuelve {borne(str): {'x','y','lado','fila','dibujado'}}; fila 0 = enchufe exterior
    (el dibujado)."""
    spec = MODELOS[modelo]
    H = det['top_edge'] - det['bot_edge']
    xc = (det['left'] + det['right']) / 2
    res = {}
    for side in ('ARRIBA', 'ABAJO'):
        drawn = det['screws_top'] if side == 'ARRIBA' else det['screws_bot']
        if len(drawn) < 2:
            raise ValueError('no encuentro 2 tornillos %s' % side)
        y0 = sum(s[1] for s in drawn) / len(drawn)
        pitch = (drawn[-1][0] - drawn[0][0]) / (len(drawn) - 1)
        sgn = -1 if side == 'ARRIBA' else 1  # hacia adentro
        fr = FRAC_FILAS[side]
        for k, fila in enumerate(spec[side]):
            y = y0 + sgn * (fr[k] - fr[0]) * H
            if len(fila) == len(drawn):
                xs = [s[0] for s in drawn]
            else:  # enchufe de otro ancho: centrado en la carcasa con el paso dibujado
                n = len(fila)
                xs = [xc + (i - (n - 1) / 2) * pitch for i in range(n)]
            for b, x in zip(fila, xs):
                res[str(b)] = {'x': round(x, 2), 'y': round(y, 2), 'lado': side, 'fila': k,
                               'dibujado': k == 0 and len(fila) == len(drawn)}
    return res


if __name__ == '__main__':
    import json
    st = load_strokes()
    for tag, xl, yl, mod in [('31AIB1', 789.4, 533.3, 'GS8536-EX'),
                             ('43DIB1', 799.9, 534.1, 'GS8512-EX.22'),
                             ('43DIB2', 808.9, 534.1, 'GS8512-EX.22')]:
        det = detectar_barrera(st, xl, yl)
        print(tag, json.dumps(det))
        for b, p in sorted(bornes_barrera(mod, det).items(), key=lambda kv: int(kv[0])):
            print('   ', b, p)
