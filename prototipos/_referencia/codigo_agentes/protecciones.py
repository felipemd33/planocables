# -*- coding: utf-8 -*-
"""
Ubicacion de bornes de PROTECCIONES en el plano topografico vectorial (Batfer):
  * aparatos modulares de riel DIN con tornillo arriba y abajo
      - disyuntor diferencial 2P (11Q1, Schneider Easy9 EZ9R36225)
      - termomagnetica 2P (11Q2, Schneider Easy9 EZ9F34210)
      - portafusible 1P (12F1, 13F3, Schneider TeSys DF101 10x38)
  * borne fusible de doble piso push-in (31XAI, dibujado como Phoenix
    PTTB 4-HESI (5X20): 6.2 x 102.9 mm, negro, "BORNE FUSIBLE 0.1A")
  * portafusible MEGA de dos esparragos (12F2)

Uso rapido:
    python protecciones.py      -> protecciones_puntos.json + control_protecciones.png

Funciones reutilizables:
    cargar_trazos(pdf, pi)                   trazos de la pagina (cache .pkl)
    circulos(trazos, ventana, rmin, rmax)    circulos del dibujo (poligonos cerrados
                                             o arcos partidos en segmentos sueltos)
    bornes_modular(trazos, etq, polos)       {polo: {'ARRIBA': (x,y), 'ABAJO': (x,y)}}
    bornes_fusible_doble_piso(trazos, etq)   {'1': {...}, 'F1': {...}}
    bornes_mega(trazos, etq, lado_bateria)   {'ARRIBA': (x,y), 'ABAJO': (x,y)}
    ubicar(usos_json)                        lista de puntos con confianza y explicacion

REGLA GENERAL (ver tambien REGLA abajo, se imprime con -h):
  1. El punto de conexion de un aparato modular de riel DIN (termomagnetica,
     diferencial, portafusible) es el CIRCULO DE TORNILLO del frente: en el
     dibujo Batfer son poligonos cerrados de 12 lados (r ~2.5 pt en
     termomagneticas, r ~1.9 pt con una raya diagonal en el DF101). Hay una
     fila arriba y una fila abajo del riel; cada polo es una columna
     (paso = ancho de modulo: 12.4 pt = 17.5 mm).  ARRIBA = circulo de mayor y,
     ABAJO = el de menor y (origen PDF abajo-izquierda).
  2. Los polos de cada aparato se toman de la etiqueta amarilla: las N columnas
     de tornillos mas cercanas a la x de la etiqueta (N = polos del modelo).
  3. Nombre de cada polo, de izquierda a derecha (fotos del tablero 75286-1 +
     hoja de datos): diferencial Easy9 = N, F (neutro a la IZQUIERDA, impreso
     "N" en el frente); termomagnetica 2P del tablero = F, N (fase a la
     izquierda: cables marron a la izquierda, blanco a la derecha arriba y
     abajo); portafusible DF101 = un solo polo (ARRIBA/ABAJO).
  4. Borne fusible doble piso push-in (PTTB ...-HESI): 4 bocas redondas
     (r ~2 pt) en el eje del borne.  Ordenadas de arriba a abajo:
     [externa sup, interna sup, interna inf, externa inf].  Las externas son
     del piso de ABAJO (1er nivel, paso directo, borne impar "1"); las internas
     son del piso de ARRIBA (2do nivel, el del fusible, "F1").  Asi lo dice la
     hoja de datos (2nd level = IEC 60947-7-3, corriente fijada por el
     fusible) y lo confirma la foto: 2142 (borne 1) entra por la boca de mas
     arriba y 1324 (F1) por la segunda.
  5. Portafusible MEGA horizontal: dos esparragos (circulos concentricos
     r ~8 pt).  ARRIBA/ABAJO del instructivo sale del esquema (izq/der del
     fusible dibujado horizontal) y NO de la geometria: se decide por el
     recorrido del cable de potencia dibujado (trazo gris grueso a trazos,
     capa TABLERO): el esparrago que va a la bateria es el lado bateria.
"""
import json
import math
import os
import pickle
import sys
from collections import defaultdict

PROG = r'C:\Buscar Termos en plano\programa'
if PROG not in sys.path:
    sys.path.insert(0, PROG)

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.dirname(AQUI)
TOPO = os.path.join(SCRATCH, 'topo.pdf')
USOS = os.path.join(AQUI, 'usos_por_componente.json')
CAPAS_COMP = ('COMPONENTES', '00_COMPONENTS')


# ------------------------------------------------------------------ trazos
def cargar_trazos(pdf=TOPO, pi=7, cache=True):
    """[(capa, op, [(x,y)...], color)] de la pagina pi (0-based), con cache."""
    pk = os.path.join(AQUI, 'strokes_p%d.pkl' % pi)
    if cache and os.path.exists(pk) and os.path.getmtime(pk) >= os.path.getmtime(pdf):
        with open(pk, 'rb') as f:
            return pickle.load(f)
    import pypdf
    from pdfvec import page_strokes, layer_names
    r = pypdf.PdfReader(pdf)
    tr = page_strokes(r, pi, layer_names(r), with_color=True)
    if cache:
        with open(pk + '.tmp', 'wb') as f:
            pickle.dump(tr, f)
        os.replace(pk + '.tmp', pk)
    return tr


def _bbox(p):
    xs = [a for a, b in p]
    ys = [b for a, b in p]
    return min(xs), min(ys), max(xs), max(ys)


def _segmentos(trazos, v, capas=CAPAS_COMP):
    """Segmentos (a, b) de los trazos 'S' totalmente dentro de la ventana v."""
    out = []
    for lay, op, pts, col in trazos:
        if capas and lay not in capas:
            continue
        if op != 'S' or not pts or len(pts) < 2:
            continue
        b = _bbox(pts)
        if b[0] >= v[0] and b[1] >= v[1] and b[2] <= v[2] and b[3] <= v[3]:
            for i in range(len(pts) - 1):
                out.append((tuple(pts[i]), tuple(pts[i + 1])))
    return out


def _cadenas(segs, tol=0.02):
    """Une segmentos sueltos que comparten extremos en polilineas."""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))
    adj = defaultdict(list)
    for i, (a, b) in enumerate(segs):
        adj[key(a)].append(i)
        adj[key(b)].append(i)
    usado = [False] * len(segs)
    res = []
    for i in range(len(segs)):
        if usado[i]:
            continue
        usado[i] = True
        pl = [segs[i][0], segs[i][1]]
        for fin in (True, False):
            while True:
                p = pl[-1] if fin else pl[0]
                nx = next((j for j in adj[key(p)] if not usado[j]), None)
                if nx is None:
                    break
                usado[nx] = True
                a, b = segs[nx]
                q = b if key(a) == key(p) else a
                if fin:
                    pl.append(q)
                else:
                    pl.insert(0, q)
        res.append(pl)
    return res


def _ajuste(pl):
    """Ajuste algebraico de circulo (Kasa) -> (cx, cy, r, err_rel, cobertura_grados)."""
    pts = list(dict.fromkeys(pl))
    n = len(pts)
    if n < 5:
        return None
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    u = [p[0] - mx for p in pts]
    v = [p[1] - my for p in pts]
    suu = sum(a * a for a in u)
    svv = sum(b * b for b in v)
    suv = sum(a * b for a, b in zip(u, v))
    det = suu * svv - suv * suv
    if abs(det) < 1e-12:
        return None
    r1 = 0.5 * (sum(a ** 3 for a in u) + sum(a * b * b for a, b in zip(u, v)))
    r2 = 0.5 * (sum(b ** 3 for b in v) + sum(b * a * a for a, b in zip(u, v)))
    uc = (r1 * svv - r2 * suv) / det
    vc = (r2 * suu - r1 * suv) / det
    cx, cy = uc + mx, vc + my
    r = math.sqrt(uc * uc + vc * vc + (suu + svv) / n)
    err = max(abs(math.hypot(p[0] - cx, p[1] - cy) - r) for p in pts) / r
    ang = sorted(math.degrees(math.atan2(p[1] - cy, p[0] - cx)) % 360 for p in pts)
    gaps = [(ang[(i + 1) % n] - ang[i]) % 360 for i in range(n)]
    return cx, cy, r, err, 360 - max(gaps)


def circulos(trazos, v, rmin=0.8, rmax=9.0, cobertura=150, err_max=0.10, capas=CAPAS_COMP):
    """Circulos del dibujo dentro de la ventana v=(x0,y0,x1,y1).

    Sirve tanto para circulos dibujados como un poligono cerrado (tornillos de
    termomagneticas) como para circulos partidos en medias circunferencias de
    segmentos sueltos (bocas de bornes push-in).  Dos arcos del mismo radio con
    centros a menos de 0.6 pt se funden en un solo circulo (centro = promedio).
    Devuelve [(cx, cy, r)] ordenado de arriba a abajo e izquierda a derecha."""
    arcos = []
    for pl in _cadenas(_segmentos(trazos, v, capas)):
        f = _ajuste(pl)
        if f and rmin <= f[2] <= rmax and f[3] <= err_max and f[4] >= cobertura:
            b = _bbox(pl)
            # un arco "de verdad" (>= media circunferencia) mide al menos ~r en
            # ambos sentidos; descarta tapas de borne muy chatas
            if min(b[2] - b[0], b[3] - b[1]) >= 0.8 * f[2]:
                arcos.append(f[:3])
    res = []
    for cx, cy, r in sorted(arcos, key=lambda a: -a[2]):
        for c in res:
            if abs(c['r'] - r) < 0.25 * r and math.hypot(c['x'] - cx, c['y'] - cy) < max(0.6, 0.3 * r):
                c['n'] += 1
                c['x'] += (cx - c['x']) / c['n']
                c['y'] += (cy - c['y']) / c['n']
                break
        else:
            res.append({'x': cx, 'y': cy, 'r': r, 'n': 1})
    return sorted([(c['x'], c['y'], c['r']) for c in res], key=lambda c: (-round(c[1], 1), c[0]))


# ------------------------------------------------ aparatos modulares (tornillos)
def bornes_modular(trazos, etq, polos, ancho_modulo=12.4, rmin=1.5, rmax=3.2, alto=40.0):
    """Tornillos de un aparato modular de riel DIN.

    etq    : (x, y) de la etiqueta amarilla (centro del aparato).
    polos  : nombres de los polos de izquierda a derecha, ej. ['N','F'] o [''].
    Devuelve {polo: {'ARRIBA': (x, y), 'ABAJO': (x, y), 'r': radio}}.
    Los tornillos son los circulos de radio rmin..rmax dentro de la columna
    del aparato; ARRIBA = el de mayor y de cada columna, ABAJO = el de menor y."""
    ex, ey = etq
    n = len(polos)
    v = (ex - (n / 2 + 0.6) * ancho_modulo, ey - alto, ex + (n / 2 + 0.6) * ancho_modulo, ey + alto)
    cs = circulos(trazos, v, rmin=rmin, rmax=rmax, cobertura=300, err_max=0.08)
    # columnas por x
    cols = []
    for c in sorted(cs, key=lambda c: c[0]):
        if cols and abs(cols[-1][-1][0] - c[0]) < 1.0:
            cols[-1].append(c)
        else:
            cols.append([c])
    cols = [c for c in cols if any(p[1] > ey for p in c) and any(p[1] < ey for p in c)]
    cols.sort(key=lambda c: abs(sum(p[0] for p in c) / len(c) - ex))
    cols = sorted(cols[:n], key=lambda c: c[0][0])
    if len(cols) != n:
        raise ValueError('se esperaban %d columnas de tornillos cerca de %s, hay %d' % (n, etq, len(cols)))
    out = {}
    for nombre, col in zip(polos, cols):
        arr = max(col, key=lambda p: p[1])
        aba = min(col, key=lambda p: p[1])
        out[nombre] = {'ARRIBA': (round(arr[0], 2), round(arr[1], 2)),
                       'ABAJO': (round(aba[0], 2), round(aba[1], 2)), 'r': round(arr[2], 2)}
    return out


# ------------------------------------------- borne fusible doble piso push-in
def bornes_fusible_doble_piso(trazos, etq, buscar_dx=(0.0, 14.0), alto=45.0,
                              piso_abajo='1', piso_arriba='F1'):
    """Borne de doble piso push-in con fusible (Phoenix PTTB 4-HESI y similares).

    Busca a la derecha de la etiqueta (etq) el borne angosto (~4.4 pt de ancho)
    y sus 4 bocas redondas (r 1.8..2.3 pt, dibujadas como dos medias
    circunferencias).  De arriba a abajo: externa sup (piso de abajo),
    interna sup (piso de arriba), interna inf (piso de arriba), externa inf
    (piso de abajo)."""
    ex, ey = etq
    v = (ex + buscar_dx[0], ey - alto, ex + buscar_dx[1], ey + alto)
    bocas = circulos(trazos, v, rmin=1.8, rmax=2.3, cobertura=150, err_max=0.10)
    # quedarse con la columna de bocas mas poblada
    grupos = []
    for b in sorted(bocas, key=lambda c: c[0]):
        if grupos and abs(grupos[-1][-1][0] - b[0]) < 0.8:
            grupos[-1].append(b)
        else:
            grupos.append([b])
    g = max(grupos, key=len) if grupos else []
    # fundir medias bocas del mismo agujero (centros a < 1.2 pt en y)
    g = sorted(g, key=lambda c: -c[1])
    bocas = []
    for b in g:
        if bocas and abs(bocas[-1][1] - b[1]) < 1.2:
            p = bocas[-1]
            bocas[-1] = ((p[0] + b[0]) / 2, (p[1] + b[1]) / 2, max(p[2], b[2]))
        else:
            bocas.append(b)
    if len(bocas) != 4:
        raise ValueError('borne doble piso cerca de %s: se esperaban 4 bocas, hay %d' % (etq, len(bocas)))
    ext_sup, int_sup, int_inf, ext_inf = [(round(b[0], 2), round(b[1], 2)) for b in bocas]
    return {piso_abajo: {'ARRIBA': ext_sup, 'ABAJO': ext_inf},
            piso_arriba: {'ARRIBA': int_sup, 'ABAJO': int_inf}}


# ----------------------------------------------------- portafusible MEGA
def bornes_mega(trazos, etq, lado_bateria='izquierda', dx=35.0, dy=15.0):
    """Portafusible MEGA horizontal: dos esparragos (circulos concentricos r 6..9 pt).

    lado_bateria: esparrago que va a la bateria ('izquierda'/'derecha'); segun el
    esquema 75287 hoja 12 el lado bateria (1215) es ABAJO y el lado contactor
    (1204) es ARRIBA.  En el topografico el cable de potencia dibujado (gris a
    trazos, capa TABLERO) sale del esparrago IZQUIERDO hacia el borne de la
    bateria 12PB1 y del DERECHO baja hacia la bomba/contactor."""
    ex, ey = etq
    v = (ex - dx - 10, ey - dy, ex + dx + 10, ey + dy)
    cs = circulos(trazos, v, rmin=6.0, rmax=9.0, cobertura=300, err_max=0.05)
    cs = sorted(cs, key=lambda c: c[0])
    izq, der = cs[0], cs[-1]
    if der[0] - izq[0] < 10:
        raise ValueError('no se encontraron dos esparragos en %s' % (etq,))
    izq = (round(izq[0], 2), round(izq[1], 2))
    der = (round(der[0], 2), round(der[1], 2))
    bat, cont = (izq, der) if lado_bateria == 'izquierda' else (der, izq)
    return {'ABAJO': bat, 'ARRIBA': cont}


# ------------------------------------------------------------ modelos / reglas
MODELOS = {
    '11Q1': {'tipo': 'modular', 'polos': ['N', 'F'],
             'modelo': 'SCHNEIDER Easy9 EZ9R36225 (RCCB 2P 25A 30mA)'},
    '11Q2': {'tipo': 'modular', 'polos': ['F', 'N'],
             'modelo': 'SCHNEIDER Easy9 EZ9F34210 (MCB 2P C10); en la foto hay un ABB S202 C10'},
    '12F1': {'tipo': 'modular', 'polos': [''], 'modelo': 'SCHNEIDER TeSys DF101 10x38 (fusible 20A)'},
    '13F3': {'tipo': 'modular', 'polos': [''], 'modelo': 'SCHNEIDER TeSys DF101 10x38 (fusible 10A)'},
    '31XAI': {'tipo': 'fusible_doble_piso',
              'modelo': 'lista: PHOENIX PTT 2,5-2MT; dibujo y foto: borne fusible doble piso push-in '
                        'negro tipo PHOENIX PTTB 4-HESI (5X20), 6.2x102.9 mm, fusible 100mA'},
    '12F2': {'tipo': 'mega', 'modelo': 'Base portafusible MEGA (2 esparragos), fusible MEGA 150A'},
}

# Usos del instructivo que NO coinciden con el esquema (hojas 12 y 31): se
# ubican por su texto literal pero con confianza baja.
SOSPECHOSOS = {
    ('12F2', '1204', '12F2'): 'el instructivo pone 1204 "12F2 ARRIBA -> 12F2" (los dos extremos en el mismo '
                              'fusible). Segun la hoja 12, 1204 va de 12F2 (lado izq. del simbolo) al '
                              'contactor BH-01-ZV de la bomba: este extremo NO esta en 12F2.',
    ('12F2', '1216', '12F2'): 'segun la hoja 12, 1216 (Negro 35mm2) va de 12PB1 (-) a GND de BH-01-M; no '
                              'toca 12F2. Se deja en el esparrago ABAJO solo por el texto.',
    ('31XAI', '3141', '31XAI 1 ARRIBA'): 'segun la hoja 31, 3141 va de 31XAI F1 (salida del fusible) al '
                                         'transmisor PT 001 borne 1 (campo). "31XAI 1 ARRIBA" es en realidad '
                                         'el borne 1 de PT 001; en 31XAI 1 ARRIBA entra solo 2142.',
    ('31XAI', '3142', '31XAI 2 ARRIBA'): 'segun la hoja 31, 3142 va de 31XAI 1 al transmisor PT 001 borne 2 '
                                         '(campo). 31XAI no tiene borne "2" (solo F1 y 1).',
}

COMO = {
    '11Q1': 'Dibujo: 4 modulos con fila de tornillos arriba y abajo (poligonos de 12 lados r=2.5); 11Q1 = '
            'las 2 columnas bajo su etiqueta. Hoja de datos Easy9 RCCB: neutro a la izquierda. Fotos '
            '12.35.34 (arriba 1105 blanco izq, 1104 marron der) y 1.4 (abajo 1107 izq, 1106 der) y la "N" '
            'impresa en el polo izquierdo.',
    '11Q2': 'Dibujo: columnas 3 y 4 de tornillos (bajo la etiqueta 11Q2). Fotos 12.35.34 (arriba 1106 marron '
            'izq, 1107 blanco der) y 1.4 (abajo 1108 marron izq, 1109 blanco der): F a la izquierda, N a la '
            'derecha.',
    '12F1': 'Dibujo DF101: tornillo (circulo r=1.9 con raya) arriba y abajo en el centro del modulo de 17.5 mm. '
            'Fotos 12.35.37(1) / 1.1 (1201 arriba) y 12.35.36(2) / 09-25 (1202 abajo). 12F1 es el de la '
            'izquierda (etiqueta x=773.4).',
    '13F3': 'Dibujo DF101: tornillo arriba y abajo. Fotos 12.35.37(1) / 1.1 (1206 arriba) y 12.35.36(2) / '
            '09-25 (1301 abajo). 13F3 es el de la derecha (etiqueta x=785.8).',
    '31XAI': 'Dibujo: borne angosto 4.3x72 pt (=6.1x101 mm, coincide con PTTB 4-HESI 6.2x102.9 mm) con 4 '
             'bocas redondas r=2 (medias circunferencias). Hoja de datos PTTB 4-HESI: 2do nivel (piso de '
             'arriba, bocas internas) es el fusible (IEC 60947-7-3); 1er nivel (piso de abajo, bocas '
             'externas) paso directo. Foto 12.35.37(1) / 1.1: 2142 (borne 1) entra por la boca de mas '
             'arriba y 1324 (F1) por la segunda; proporciones de altura de las bocas en la foto (0.05/0.35/'
             '0.80/0.94) coinciden con el dibujo (0.07/0.33/0.76/0.93).',
    '12F2': 'Dibujo: portafusible MEGA horizontal con dos esparragos (circulos concentricos r=8.1). Hoja 12: '
            '1204 (lado contactor BH-01-ZV) y 1215 (lado bateria 12PB1 +). En el topografico (y en la hoja 04 '
            'Detalles) el cable de 35mm2 dibujado sale del esparrago IZQUIERDO y baja al borne de la bateria, '
            'y del DERECHO baja hacia la bomba/contactor: izquierdo = 1215 (ABAJO), derecho = 1204 (ARRIBA). '
            'No hay foto de este fusible.',
}


def ubicar(usos_path=USOS, trazos=None):
    """Devuelve (puntos, geometria) para los componentes de MODELOS presentes en usos."""
    d = json.load(open(usos_path, encoding='utf-8'))
    comps = d['componentes']
    trazos = trazos or cargar_trazos()
    geo = {}
    for tag, m in MODELOS.items():
        if tag not in comps:
            continue
        e = comps[tag]['etiqueta_topografico']
        etq = (e['x'], e['y'])
        if m['tipo'] == 'modular':
            geo[tag] = bornes_modular(trazos, etq, m['polos'])
        elif m['tipo'] == 'fusible_doble_piso':
            geo[tag] = bornes_fusible_doble_piso(trazos, etq)
        elif m['tipo'] == 'mega':
            geo[tag] = {'': bornes_mega(trazos, etq)}
    puntos = []
    for tag in geo:
        e = comps[tag]['etiqueta_topografico']
        for u in comps[tag]['usos']:
            borne = u.get('borne') or ''
            lado = u.get('lado') or u.get('parte')
            nota = SOSPECHOSOS.get((tag, u['cable'], u['texto']))
            conf = 'alta'
            if tag == '12F2':
                conf = 'media'
            if borne in geo[tag] and lado in geo[tag][borne]:
                x, y = geo[tag][borne][lado]
            else:
                x, y = e['x'], e['y']
                conf = 'baja'
                nota = (nota or '') + ' Borne "%s" inexistente en el aparato: se deja en la etiqueta.' % borne
            if nota:
                conf = 'baja'
            como = COMO[tag] + ((' ATENCION: ' + nota.strip()) if nota else '')
            puntos.append({'componente': tag, 'texto': u['texto'], 'cables': [u['cable']],
                           'x': round(x, 2), 'y': round(y, 2), 'confianza': conf, 'como': como,
                           'borne': borne, 'lado': lado})
    return puntos, geo


# ------------------------------------------------------------ imagen de control
def imagen_control(puntos, salida, pdf=TOPO, pi=7, escala=9):
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw, ImageFont
    doc = pdfium.PdfDocument(pdf)
    pg = doc[pi]
    W, H = pg.get_size()
    try:
        fnt = ImageFont.truetype('arialbd.ttf', 17)
        fnt_t = ImageFont.truetype('arialbd.ttf', 24)
    except Exception:
        fnt = fnt_t = ImageFont.load_default()

    def panel(v, pts, margen=(230, 330, 250, 330), titulo=''):
        x0, y0, x1, y1 = v
        im = pg.render(scale=escala, crop=(x0, y0, W - x1, H - y1)).to_pil().convert('RGB')
        ml, mt, mr, mb = margen
        can = Image.new('RGB', (im.width + ml + mr, im.height + mt + mb), 'white')
        can.paste(im, (ml, mt))
        dr = ImageDraw.Draw(can)
        dr.text((10, 8), titulo, fill=(0, 0, 0), font=fnt_t)
        P = lambda x, y: (ml + (x - x0) * escala, mt + (y1 - y) * escala)
        # agrupar por punto
        grp = {}
        for p in pts:
            grp.setdefault((p['x'], p['y']), []).append(p)
        orden = sorted(grp.items(), key=lambda kv: (kv[0][0], -kv[0][1]))
        n_arr = n_aba = 0
        for (x, y), lst in orden:
            px, py = P(x, y)
            col = {'alta': (220, 0, 0), 'media': (230, 120, 0), 'baja': (160, 0, 200)}[
                min((q['confianza'] for q in lst), key=['baja', 'media', 'alta'].index)]
            dr.ellipse([px - 9, py - 9, px + 9, py + 9], outline=col, width=4)
            dr.line([px - 14, py, px + 14, py], fill=col, width=2)
            dr.line([px, py - 14, px, py + 14], fill=col, width=2)
            COL = {'alta': (220, 0, 0), 'media': (230, 120, 0), 'baja': (160, 0, 200)}
            lineas = []
            for q in lst:
                t = q['texto']
                if q.get('lado') and q['lado'] not in t:
                    t += ' (%s)' % q['lado']
                lineas.append(('%s  [%s]%s' % (t, ','.join(q['cables']),
                                               ' (?)' if q['confianza'] == 'baja' else ''), COL[q['confianza']]))
            tw = max(dr.textlength(t, font=fnt) for t, c in lineas)
            th = 21 * len(lineas)
            lado = lst[0].get('lado')
            if lst[0]['componente'] == '31XAI':
                lx = ml + im.width + 15
                ly = py - th / 2
                ax, ay = lx, ly + th / 2
            elif lst[0]['componente'] == '12F2':
                lx = px - tw / 2
                ly = (mt - th - 20) if px < can.width / 2 else (mt + im.height + 20)
                ax, ay = px, (ly + th) if ly < mt else ly
            elif lado == 'ARRIBA':
                k = n_arr % 3
                n_arr += 1
                lx = px - tw / 2
                ly = mt - 40 - th - k * 85
                ax, ay = px, ly + th
            else:
                k = n_aba % 3
                n_aba += 1
                lx = px - tw / 2
                ly = mt + im.height + 40 + k * 85
                ax, ay = px, ly
            lx = max(4, min(lx, can.width - tw - 4))
            dr.line([px, py, ax, ay], fill=col, width=2)
            dr.rectangle([lx - 3, ly - 2, lx + tw + 3, ly + th + 2], fill=(255, 255, 255), outline=col)
            for i, (t, c) in enumerate(lineas):
                dr.text((lx, ly + 21 * i), t, fill=c, font=fnt)
        return can

    a = [p for p in puntos if p['componente'] != '12F2']
    b = [p for p in puntos if p['componente'] == '12F2']
    pa = panel((641, 636, 810, 716), a, margen=(40, 330, 470, 330),
               titulo='Riel 1: 11Q1, 11Q2, 12F1, 13F3, 31XAI  (rojo=alta, naranja=media, violeta=baja/dudoso)')
    pb = panel((566, 292, 640, 318), b, margen=(40, 150, 40, 150), titulo='12F2 (portafusible MEGA)')
    out = Image.new('RGB', (max(pa.width, pb.width), pa.height + pb.height + 20), 'white')
    out.paste(pa, (0, 0))
    out.paste(pb, (0, pa.height + 20))
    out.save(salida)
    return out.size


REGLA = __doc__[__doc__.index('REGLA GENERAL'):]

if __name__ == '__main__':
    if '-h' in sys.argv:
        print(REGLA)
        sys.exit(0)
    puntos, geo = ubicar()
    for p in puntos:
        print('%-6s %-18s %-5s (%.2f, %.2f) %s' % (p['componente'], p['texto'], p['cables'][0], p['x'], p['y'],
                                                   p['confianza']))
    json.dump({'puntos': puntos, 'geometria': {k: {b: {l: list(xy) if isinstance(xy, tuple) else xy
                                                        for l, xy in d.items()} for b, d in g.items()}
                                               for k, g in geo.items()},
               'modelos': MODELOS, 'regla': REGLA},
              open(os.path.join(AQUI, 'protecciones_puntos.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(imagen_control(puntos, os.path.join(AQUI, 'control_protecciones.png')))
