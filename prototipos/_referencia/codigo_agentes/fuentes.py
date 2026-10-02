# -*- coding: utf-8 -*-
"""
Ubicacion de bornes de FUENTES MEAN WELL (NDR / DDR) y del TOMACORRIENTE IRAM
de riel DIN en el plano topografico (vector PDF de Batfer).

Uso rapido:
    python fuentes.py            -> calcula los puntos de 11PS1, 13PS3, 11SK1,
                                    escribe fuentes_puntos.json y control_fuentes.png

Funciones reutilizables:
    cargar_trazos(pdf, pi)                    trazos de la pagina (con cache .pkl)
    detectar_tornillos(trazos, ventana)       circulos de tornillo (centro, radio)
    filas_de_tornillos(tornillos)             agrupa en filas equiespaciadas
    bornes_meanwell(trazos, etiqueta_xy)      {'TB2': [...4], 'TB1': [...3]} con
                                              tornillo y punto de entrada del cable
    resolver_meanwell(familia, borne, cable)  -> ('TB2'|'TB1', pin 1..n)
    bornes_toma_iram(trazos, etiqueta_xy)     {'N','PE','L'} (estimados, abajo)

Regla (datos del fabricante + fotos del tablero 75286-1):
  * NDR-120 / NDR-240 (AC/DC) y DDR-120 (DC/DC): vista frontal, TB2 = bornera
    de SALIDA arriba (4 pines, 1..4 de izquierda a derecha), TB1 = ENTRADA
    abajo (3 pines, 1..3 de izquierda a derecha).
      NDR  TB2: 1,2 = -V   3,4 = +V      TB1: 1 = FG, 2 = N (AC/N), 3 = L (AC/L)
      DDR  TB2: 1,2 = -Vo  3,4 = +Vo     TB1: 1 = FG, 2 = -Vin,     3 = +Vin
    En el dibujo del topografico cada tornillo es un circulo (dos medias
    circunferencias) con una cruz Phillips adentro; las dos borneras son las
    unicas filas de 4 y 3 circulos iguales equiespaciados (paso 3.5..5.5 pt)
    dentro del cuerpo de la fuente.
  * Toma IRAM de riel DIN (VIVION, tipo AC30 de 45 mm): los tres bornes estan
    TODOS ABAJO, en la franja de la base que asoma debajo de la tapa, de
    izquierda a derecha N - PE - L (foto "WhatsApp Image 2026-09-25 at
    15.54.54.jpeg": 1109 blanco en N, verde-amarillo en PE, 1108 marron en L;
    los cables salen hacia ABAJO). El dibujo del topografico es un bloque
    simbolico (32 mm de ancho, el real mide 45 mm) y no dibuja tornillos: tiene
    una banda inferior (rectangulo abierto de 4 puntos, 3.4 pt de alto, ancho
    total del aparato) que corresponde a esa franja de bornes. Los tornillos
    se ubican en el centro vertical de la banda a las fracciones medidas en la
    foto sobre la franja (N 0.292, PE 0.501, L 0.710: simetricos, PE al medio).
    El "L ARRIBA / N ABAJO" del instructivo sale del simbolo del esquema
    (hoja 11: L arriba, N abajo), NO del aparato real.
"""
import math
import os
import pickle
import re
import sys

PROG = r'C:\Buscar Termos en plano\programa'
if PROG not in sys.path:
    sys.path.insert(0, PROG)

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.dirname(AQUI)
TOPO = os.path.join(SCRATCH, 'topo.pdf')
USOS = os.path.join(AQUI, 'usos_por_componente.json')
CAPAS_COMP = ('COMPONENTES', '00_COMPONENTS')


# ---------------------------------------------------------------- trazos
def cargar_trazos(pdf=TOPO, pi=7, cache=True):
    """[(capa, op, [(x,y)...], color)] de la pagina pi (0-based)."""
    pk = os.path.join(AQUI, 'strokes_p%d.pkl' % pi)
    if cache and os.path.exists(pk) and os.path.getmtime(pk) >= os.path.getmtime(pdf):
        with open(pk, 'rb') as f:
            return pickle.load(f)
    import pypdf
    from pdfvec import page_strokes, layer_names
    r = pypdf.PdfReader(pdf)
    tr = page_strokes(r, pi, layer_names(r), with_color=True)
    if cache:
        with open(pk, 'wb') as f:
            pickle.dump(tr, f)
    return tr


def _bbox(p):
    xs = [a for a, b in p]
    ys = [b for a, b in p]
    return min(xs), min(ys), max(xs), max(ys)


def _en(b, v):
    return b[0] >= v[0] and b[1] >= v[1] and b[2] <= v[2] and b[3] <= v[3]


def _fit_circulo(p):
    """Ajuste algebraico (Kasa). Devuelve (cx, cy, r, residuo_relativo)."""
    n = len(p)
    mx = sum(a for a, b in p) / n
    my = sum(b for a, b in p) / n
    u = [a - mx for a, b in p]
    v = [b - my for a, b in p]
    suu = sum(x * x for x in u)
    svv = sum(y * y for y in v)
    suv = sum(x * y for x, y in zip(u, v))
    suuu = sum(x ** 3 for x in u)
    svvv = sum(y ** 3 for y in v)
    suvv = sum(x * y * y for x, y in zip(u, v))
    svuu = sum(y * x * x for x, y in zip(u, v))
    det = suu * svv - suv * suv
    if abs(det) < 1e-12:
        return None
    b1 = 0.5 * (suuu + suvv)
    b2 = 0.5 * (svvv + svuu)
    uc = (b1 * svv - b2 * suv) / det
    vc = (suu * b2 - suv * b1) / det
    cx, cy = uc + mx, vc + my
    ds = [math.hypot(a - cx, b - cy) for a, b in p]
    r = sum(ds) / n
    if r <= 0:
        return None
    res = math.sqrt(sum((d - r) ** 2 for d in ds) / n) / r
    return cx, cy, r, res


# ---------------------------------------------------------------- tornillos
def detectar_tornillos(trazos, ventana, rmin=1.2, rmax=3.2, capas=CAPAS_COMP):
    """Circulos de tornillo dentro de ventana=(x0,y0,x1,y1).
    Acepta circunferencias completas o medias circunferencias (arcos) dibujadas
    como polilineas; la cruz Phillips interior se descarta por no ser circular.
    Devuelve [{'x','y','r'}] sin duplicados."""
    cands = []
    for capa, op, p, *_ in trazos:
        if op != 'S' or capa not in capas or len(p) < 7:
            continue
        b = _bbox(p)
        if not _en(b, ventana):
            continue
        w, h = b[2] - b[0], b[3] - b[1]
        if max(w, h) < 2 * rmin or max(w, h) > 2 * rmax + 0.3:
            continue
        f = _fit_circulo(p)
        if not f:
            continue
        cx, cy, r, res = f
        if res > 0.06 or not (rmin <= r <= rmax):
            continue
        # el arco debe cubrir al menos media vuelta (ancho ~ diametro)
        if max(w, h) < 1.8 * r:
            continue
        cands.append((cx, cy, r))
    out = []
    for cx, cy, r in cands:
        for o in out:
            if math.hypot(o['x'] - cx, o['y'] - cy) < 0.6 * r and abs(o['r'] - r) < 0.3 * r:
                o['n'] += 1
                o['x'] = (o['x'] * (o['n'] - 1) + cx) / o['n']
                o['y'] = (o['y'] * (o['n'] - 1) + cy) / o['n']
                break
        else:
            out.append({'x': cx, 'y': cy, 'r': r, 'n': 1})
    # concentricos (circulo exterior + interior): quedarse con el mayor
    out.sort(key=lambda o: -o['r'])
    fin = []
    for o in out:
        if any(math.hypot(o['x'] - q['x'], o['y'] - q['y']) < 0.5 for q in fin):
            continue
        fin.append(o)
    return fin


def filas_de_tornillos(torn, tol_y=0.6, paso=(3.0, 6.0), min_n=2):
    """Agrupa tornillos del mismo radio en filas horizontales equiespaciadas."""
    filas = []
    for t in sorted(torn, key=lambda t: t['y']):
        for f in filas:
            if abs(f['y'] - t['y']) < tol_y and abs(f['r'] - t['r']) < 0.25 * f['r']:
                f['t'].append(t)
                f['y'] = sum(q['y'] for q in f['t']) / len(f['t'])
                break
        else:
            filas.append({'y': t['y'], 'r': t['r'], 't': [t]})
    res = []
    for f in filas:
        ts = sorted(f['t'], key=lambda t: t['x'])
        # partir la fila donde el paso se sale del rango (aparatos vecinos)
        tramo = [ts[0]]
        for a, b in zip(ts, ts[1:]):
            if paso[0] <= b['x'] - a['x'] <= paso[1]:
                tramo.append(b)
            else:
                if len(tramo) >= min_n:
                    res.append(tramo)
                tramo = [b]
        if len(tramo) >= min_n:
            res.append(tramo)
    return [{'y': sum(t['y'] for t in tr) / len(tr), 'r': tr[0]['r'],
             'x0': tr[0]['x'], 'x1': tr[-1]['x'], 'tornillos': tr} for tr in res]


def _borde_bornera(trazos, fila, arriba, capas=CAPAS_COMP, alcance=8.0):
    """Borde exterior del enchufe de la bornera (por donde entra el cable):
    la linea horizontal mas alejada (arriba para TB2, abajo para TB1) que
    cubre toda la fila, a menos de `alcance` pt de los tornillos."""
    r = fila['r']
    xa, xb = fila['x0'] - r, fila['x1'] + r
    best = None
    for capa, op, p, *_ in trazos:
        if op != 'S' or capa not in capas:
            continue
        for (x1, y1), (x2, y2) in zip(p, p[1:]):
            if abs(y1 - y2) > 0.05:
                continue
            lo, hi = min(x1, x2), max(x1, x2)
            if lo > xa + 0.3 or hi < xb - 0.3:
                continue
            d = (y1 - fila['y']) if arriba else (fila['y'] - y1)
            if r < d <= alcance and (best is None or d > best):
                best = d
    if best is None:
        return None
    return fila['y'] + best if arriba else fila['y'] - best


# ---------------------------------------------------------------- MEAN WELL
MEANWELL = {
    # familia: nombres por pin, de izquierda a derecha en la vista frontal
    'NDR': {'TB2': ['-V', '-V', '+V', '+V'], 'TB1': ['FG', 'N', 'L']},
    'DDR': {'TB2': ['-Vo', '-Vo', '+Vo', '+Vo'], 'TB1': ['FG', '-Vin', '+Vin']},
}

# Asignacion fisica confirmada con fotos cuando el nombre se repite en 2 pines
# (tag -> {cable: (bornera, pin)}).
FOTO = {
    # foto 1.0.jpeg: 1110 en el 1er -V, 1111 en el 1er +V (3er tornillo)
    '11PS1': {'1110': ('TB2', 1), '1111': ('TB2', 3),
              # foto 1.4.jpeg: abajo tierra - N(1109) - L(1108)
              '1109': ('TB1', 2), '1108': ('TB1', 3)},
    # foto 1.1.jpeg: arriba 1311 | 1323 | 1310 | libre ; foto 1.5 / 15.54.54:
    # abajo tierra - 1305(-Vin) - 1304(+Vin)
    '13PS3': {'1311': ('TB2', 1), '1323': ('TB2', 2), '1310': ('TB2', 3),
              '1305': ('TB1', 2), '1304': ('TB1', 3)},
}


def resolver_meanwell(familia, borne, cable=None, tag=None, usados=None):
    """Texto de borne del funcional -> (bornera, pin 1-based)."""
    if tag and cable and cable in FOTO.get(tag, {}):
        return FOTO[tag][cable]
    s = borne.strip().replace(' ', '')
    m = re.match(r'^(\d)\((\+|-)\)$', s)          # NDR: "1 (-)", "3 (+)"
    if m:
        return 'TB2', int(m.group(1))
    m = re.match(r'^(L|N|FG|PE)-?(\d)$', s, re.I)   # NDR: "L-3", "N-2"
    if m:
        return 'TB1', int(m.group(2))
    nombres = MEANWELL[familia]
    for tb in ('TB1', 'TB2'):
        pins = [i + 1 for i, n in enumerate(nombres[tb]) if n.lower() == s.lower()]
        if pins:
            libres = [p for p in pins if not usados or (tb, p) not in usados]
            return tb, (libres or pins)[0]
    if s.upper() in ('L', 'N', 'FG', 'PE', 'TIERRA'):
        return 'TB1', {'FG': 1, 'PE': 1, 'TIERRA': 1, 'N': 2, 'L': 3}[s.upper()]
    raise ValueError('borne no reconocido: %r' % borne)


def bornes_meanwell(trazos, etiqueta_xy, semiancho=32, semialto=60):
    """Filas TB2 (arriba, 4 tornillos) y TB1 (abajo, 3 tornillos) de la fuente
    cuya etiqueta esta en etiqueta_xy. Devuelve
    {'TB2': {'y','entrada_y','tornillos':[(x,y)..]}, 'TB1': {...}}"""
    lx, ly = etiqueta_xy
    ven = (lx - semiancho, ly - semialto, lx + semiancho, ly + semialto)
    torn = detectar_tornillos(trazos, ven)
    filas = filas_de_tornillos(torn)

    def cerca(f):
        return abs((f['x0'] + f['x1']) / 2 - lx)

    tb2 = sorted([f for f in filas if len(f['tornillos']) == 4 and f['y'] > ly], key=cerca)
    tb1 = sorted([f for f in filas if len(f['tornillos']) == 3 and f['y'] < ly], key=cerca)
    out = {}
    for nom, lst, arriba in (('TB2', tb2, True), ('TB1', tb1, False)):
        if not lst:
            out[nom] = None
            continue
        f = lst[0]
        out[nom] = {'y': round(f['y'], 2), 'r': round(f['r'], 2),
                    'entrada_y': _borde_bornera(trazos, f, arriba),
                    'tornillos': [(round(t['x'], 2), round(t['y'], 2)) for t in f['tornillos']]}
    return out


# ---------------------------------------------------------------- toma IRAM
# Medido en "WhatsApp Image 2026-09-25 at 15.54.54.jpeg" (px del original
# 2048x1523): franja de bornes de la base x 175..667, tornillos N 318.5,
# PE 421.5, L 524 (y ~636).  Fraccion del ancho de la franja:
TOMA_FRAC = {'N': 0.292, 'PE': 0.501, 'L': 0.710}
TOMA_PIN = {'N': 1, 'PE': 2, 'L': 3}


def cuerpo_con_punto(trazos, xy, wmin=10, hmin=20, capas=CAPAS_COMP):
    """Rectangulo cerrado (5 puntos) mas chico de la capa de componentes que
    contiene xy."""
    x, y = xy
    best = None
    for capa, op, p, *_ in trazos:
        if capa not in capas or len(p) != 5:
            continue
        b = _bbox(p)
        w, h = b[2] - b[0], b[3] - b[1]
        if w < wmin or h < hmin:
            continue
        if not (b[0] <= x <= b[2] and b[1] <= y <= b[3]):
            continue
        if best is None or w * h < (best[2] - best[0]) * (best[3] - best[1]):
            best = b
    return best


def banda_inferior(trazos, cuerpo, capas=CAPAS_COMP, hmin=1.5, hmax=6.0):
    """Banda horizontal pegada DEBAJO del cuerpo del aparato: polilinea de 4-5
    puntos, de 1.5..6 pt de alto, que cubre todo el ancho del cuerpo (y a lo
    sumo 8 pt mas) y cuyo borde superior queda a <3 pt del borde inferior del
    cuerpo.  En 11SK1: 737.31..760.15 x 649.78..653.16."""
    x0, y0, x1, y1 = cuerpo
    best = None
    for capa, op, p, *_ in trazos:
        if capa not in capas or op != 'S' or len(p) not in (4, 5):
            continue
        b = _bbox(p)
        h = b[3] - b[1]
        if not (hmin <= h <= hmax):
            continue
        if b[0] > x0 + 0.1 or b[2] < x1 - 0.1 or (b[2] - b[0]) > (x1 - x0) + 8:
            continue
        if not (y0 - 3.0 <= b[3] <= y0 + 0.1):
            continue
        if best is None or b[3] > best[3]:
            best = b
    return best


def bornes_toma_iram(trazos, etiqueta_xy):
    """Bornes N / PE / L del toma IRAM de riel DIN (todos ABAJO).
    Devuelve {'N':(x,y), 'PE':(x,y), 'L':(x,y), '_cuerpo', '_banda',
    '_entrada_y'} o None.  Los puntos son ESTIMADOS (el dibujo no tiene
    tornillos): centro vertical de la banda inferior, x a TOMA_FRAC del ancho."""
    lx, ly = etiqueta_xy
    b = cuerpo_con_punto(trazos, (lx, ly - 5))
    if b is None:
        return None
    banda = banda_inferior(trazos, b)
    if banda:
        bx0, by0, bx1, by1 = banda
        yc, ent = (by0 + by1) / 2, by0
    else:                        # sin banda dibujada: borde inferior del cuerpo
        bx0, bx1 = b[0], b[2]
        yc, ent = b[1] + 1.7, b[1]
    out = {k: (round(bx0 + f * (bx1 - bx0), 2), round(yc, 2)) for k, f in TOMA_FRAC.items()}
    out.update({'_cuerpo': tuple(round(v, 2) for v in b),
                '_banda': tuple(round(v, 2) for v in banda) if banda else None,
                '_entrada_y': round(ent, 2)})
    return out


# ---------------------------------------------------------------- principal
COMPONENTES = {
    # tag: (tipo, familia)
    '11PS1': ('meanwell', 'NDR'),   # real: NDR-240-24 (foto 1.0 "Max. 240 Watt")
    '13PS3': ('meanwell', 'DDR'),   # DDR-120A-24
    '11SK1': ('toma', 'IRAM'),
}


def calcular(trazos=None, usos_path=USOS):
    import json
    trazos = trazos or cargar_trazos()
    usos = json.load(open(usos_path, encoding='utf-8'))['componentes']
    puntos, geo = [], {}
    for tag, (tipo, fam) in COMPONENTES.items():
        c = usos[tag]
        lab = (c['etiqueta_topografico']['x'], c['etiqueta_topografico']['y'])
        if tipo == 'meanwell':
            g = bornes_meanwell(trazos, lab)
            geo[tag] = g
            usados = set()
            for u in c['usos']:
                tb, pin = resolver_meanwell(fam, u['borne'], u['cable'], tag, usados)
                usados.add((tb, pin))
                x, y = g[tb]['tornillos'][pin - 1]
                puntos.append({'componente': tag, 'texto': u['texto'], 'cable': u['cable'],
                               'bornera': tb, 'pin': pin,
                               'nombre_fisico': MEANWELL[fam][tb][pin - 1],
                               'x': x, 'y': y,
                               'entrada': (x, round(g[tb]['entrada_y'], 2)) if g[tb]['entrada_y'] else None,
                               'confianza': 'alta'})
        else:
            g = bornes_toma_iram(trazos, lab)
            geo[tag] = g
            for u in c['usos']:
                k = u['borne'].strip().upper()
                x, y = g[k]
                puntos.append({'componente': tag, 'texto': u['texto'], 'cable': u['cable'],
                               'bornera': 'ABAJO', 'pin': {'N': 1, 'PE': 2, 'L': 3}[k],
                               'nombre_fisico': k, 'x': x, 'y': y,
                               'entrada': (x, g['_entrada_y']), 'confianza': 'media'})
    return puntos, geo


def _render(ventana, escala):
    import pypdfium2 as pdfium
    x0, y0, x1, y1 = ventana
    doc = pdfium.PdfDocument(TOPO)
    pg = doc[7]
    W, H = pg.get_size()
    img = pg.render(scale=escala, crop=(x0, y0, W - x1, H - y1)).to_pil().convert('RGB')
    doc.close()
    return img


def _fuentes_pil(tam):
    from PIL import ImageFont
    try:
        return ImageFont.truetype('arialbd.ttf', tam)
    except OSError:
        return ImageFont.load_default()


def _anotar(img, ventana, escala, puntos, geo, tam=17, sep=26, dist=60):
    """Dibuja sobre img (render de ventana a escala): tornillos detectados
    (verde, numerados), punto de uso (rojo), punto de entrada del cable (azul)
    y rotulo 'texto [cable]'."""
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    fnt, fnt2 = _fuentes_pil(tam), _fuentes_pil(max(10, tam - 3))
    x0, y0, x1, y1 = ventana

    def px(x, y):
        return (x - x0) * escala, (y1 - y) * escala

    for tag, g in geo.items():
        if not g:
            continue
        if 'TB2' in g:
            for tb in ('TB2', 'TB1'):
                if not g[tb]:
                    continue
                rr = g[tb]['r'] * escala
                for i, (x, y) in enumerate(g[tb]['tornillos']):
                    X, Y = px(x, y)
                    d.ellipse([X - rr, Y - rr, X + rr, Y + rr], outline=(0, 170, 0), width=2)
                    d.text((X - 4, Y + (rr + 2 if tb == 'TB2' else -rr - tam)), str(i + 1),
                           fill=(0, 130, 0), font=fnt2)
        else:
            if g.get('_banda'):
                bx0, by0, bx1, by1 = g['_banda']
                A, B = px(bx0, by1)
                C, D = px(bx1, by0)
                d.rectangle([A, B, C, D], outline=(0, 170, 0), width=2)
            for k in ('N', 'PE', 'L'):
                X, Y = px(*g[k])
                d.ellipse([X - 6, Y - 6, X + 6, Y + 6], outline=(0, 170, 0), width=2)
                d.text((X - 6, Y - 6 - tam), k, fill=(0, 130, 0), font=fnt2)
    arriba = [p for p in puntos if p['bornera'] == 'TB2']
    abajo = [p for p in puntos if p['bornera'] != 'TB2']
    for grupo, sube in ((arriba, True), (abajo, False)):
        grupo = sorted(grupo, key=lambda p: (p['componente'], p['x'], p['cable']))
        for i, p in enumerate(grupo):
            X, Y = px(p['x'], p['y'])
            if not (0 <= X <= img.width and 0 <= Y <= img.height):
                continue
            col = (230, 0, 0) if p['confianza'] == 'alta' else (230, 120, 0)
            d.ellipse([X - 7, Y - 7, X + 7, Y + 7], outline=col, width=3)
            d.line([X - 10, Y, X + 10, Y], fill=col, width=2)
            d.line([X, Y - 10, X, Y + 10], fill=col, width=2)
            if p.get('entrada'):
                EX, EY = px(*p['entrada'])
                d.ellipse([EX - 4, EY - 4, EX + 4, EY + 4], fill=(0, 90, 255))
            txt = '%s  [%s]' % (p['texto'], p['cable'])
            dy = (dist + sep * (i % 3)) * (-1 if sube else 1)
            tx, ty = X + 12, Y + dy
            tw = d.textlength(txt, font=fnt)
            if tx + tw > img.width - 2:
                tx = max(2, img.width - tw - 4)
            d.line([X, Y, tx, ty + tam // 2], fill=col, width=1)
            d.rectangle([tx - 2, ty - 1, tx + tw + 2, ty + tam + 2], fill=(255, 255, 255), outline=col)
            d.text((tx, ty), txt, fill=col, font=fnt)
    return img


PANELES = [
    # filas de paneles: (titulo, ventana en pt PDF)
    [('11PS1 TB2 (salida, arriba)', (606, 704, 633, 726)),
     ('11PS1 TB1 (entrada, abajo)', (609, 620, 637, 642)),
     ('13PS3 TB2 (salida, arriba)', (809, 708, 834, 728))],
    [('13PS3 TB1 (entrada, abajo)', (811, 625, 836, 646)),
     ('11SK1 (bornes abajo, posicion estimada)', (733, 640, 768, 660))],
]


def imagen_control(puntos, geo, salida, ventana=(592, 622, 848, 728), escala=9,
                   paneles=PANELES, escala_panel=26):
    """Vista general + paneles ampliados de cada bornera, todo rotulado."""
    from PIL import Image, ImageDraw
    gen = _anotar(_render(ventana, escala), ventana, escala, puntos, geo)
    gap = 12
    filas = []
    for fila in paneles:
        imgs = []
        for tit, v in fila:
            im = _anotar(_render(v, escala_panel), v, escala_panel, puntos, geo,
                         tam=20, sep=30, dist=70)
            dd = ImageDraw.Draw(im)
            f = _fuentes_pil(20)
            tw = dd.textlength(tit, font=f)
            dd.rectangle([0, 0, tw + 10, 28], fill=(40, 40, 40))
            dd.text((5, 3), tit, fill=(255, 255, 255), font=f)
            dd.rectangle([0, 0, im.width - 1, im.height - 1], outline=(40, 40, 40), width=2)
            imgs.append(im)
        filas.append(imgs)
    W = max([gen.width] + [sum(i.width for i in f) + gap * (len(f) - 1) for f in filas])
    H = gen.height + sum(max(i.height for i in f) + gap for f in filas) + 44
    out = Image.new('RGB', (W, H), (255, 255, 255))
    out.paste(gen, (0, 0))
    y = gen.height + gap
    for f in filas:
        x = 0
        for im in f:
            out.paste(im, (x, y))
            x += im.width + gap
        y += max(i.height for i in f) + gap
    d = ImageDraw.Draw(out)
    d.text((6, H - 34),
           'rojo = uso de borne (confianza alta)  |  naranja = confianza media (posicion estimada)  |  '
           'verde = tornillos detectados en el dibujo (n = pin)  |  azul = borde por donde entra el cable',
           fill=(0, 0, 0), font=_fuentes_pil(20))
    out.save(salida)
    return salida


if __name__ == '__main__':
    import json
    tr = cargar_trazos()
    pts, geo = calcular(tr)
    for p in pts:
        print('%-6s %-18s %-5s %-5s pin%d %-5s  (%.2f, %.2f)  entrada=%s  %s' % (
            p['componente'], p['texto'], p['cable'], p['bornera'], p['pin'],
            p['nombre_fisico'], p['x'], p['y'], p['entrada'], p['confianza']))
    print(json.dumps(geo, indent=1, default=str))
    json.dump({'puntos': pts, 'geometria': geo}, open(os.path.join(AQUI, 'fuentes_puntos.json'), 'w',
              encoding='utf-8'), ensure_ascii=False, indent=1, default=list)
    print(imagen_control(pts, geo, os.path.join(AQUI, 'control_fuentes.png')))
