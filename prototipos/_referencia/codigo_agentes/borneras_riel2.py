"""Deteccion de los puntos de entrada de conductor de borneras Phoenix Contact push-in del riel 2
en el plano topografico vectorial:
  * PT 6-QUATTRO   (12XP, 13XC1, 13X24): 1 nivel, 4 entradas (2 arriba + 2 abajo) -> "N.p"
  * PT 2,5-DIO/L-R (62XDIO): 1 nivel, 2 entradas (1 arriba + 1 abajo), diodo L->R -> "N ARRIBA/ABAJO"
  * PTT 2,5        (62XDO): 2 niveles, 4 entradas (2 arriba + 2 abajo)          -> "N ARRIBA/ABAJO"

Uso:
    import borneras_riel2 as b2
    res, grupos, pz = b2.ubicar(usos_json, pdf, 7, b2.TIPOS, correcciones=b2.CORRECCIONES_75286)

Como se reconoce una entrada (abertura push-in) en el dibujo (capa COMPONENTES):
  el contorno de la abertura esta hecho con arcos de 3 puntos (curvas Bezier aplanadas) de radio
  1,55..2,8 pt (2,2..3,9 mm): circulo/estadio en PT 2,5-DIO (r 1,70) y PTT 2,5 (r 2,06), rectangulo
  redondeado en PT 6-QUATTRO (esquinas r 2,13 a la derecha y 2,70 a la izquierda). Se agrupan los arcos
  por centro de curvatura y el punto de conexion es el centro del rectangulo que encierra el contorno.
  Se descartan los tornillos de los topes (circulos r 1,4-1,5 con una X).  Los pulsadores naranja
  (rectangulos con una 'V') y el zocalo de prueba (circulo r 0,7) quedan fuera por el radio.

Reglas de numeracion (confirmadas con hojas de datos Phoenix y fotos del tablero 75286-1):
  * Pieza k de un componente = k-esima pieza contando de izquierda a derecha desde su etiqueta amarilla.
  * QUATTRO "N.p": pieza N; p=1 entrada EXTREMA de arriba, p=2 entrada INTERIOR de arriba (mas cerca del
    riel), p=3 interior de abajo, p=4 extrema de abajo.
  * PTT 2,5 "N ARRIBA/ABAJO": pieza ceil(N/2); N impar = piso de abajo = entrada extrema; N par = piso de
    arriba = entrada interior.  ARRIBA/ABAJO = extremo superior/inferior de la pieza.
  * PT 2,5-DIO "N ARRIBA/ABAJO": pieza N.  En el instructivo ARRIBA = borne izquierdo del funcional =
    anodo (lado L, el del puente FBS), ABAJO = catodo.  El extremo fisico del anodo es el del lado del
    puente (el rectangulo de color dibujado sobre las piezas); en este tablero el puente esta en la mitad
    de abajo -> el anodo (instructivo "ARRIBA") entra por ABAJO y el catodo ("ABAJO") por ARRIBA
    (foto WhatsApp 12.35.39 (2): 6201/6203/6206 arriba, 1315 abajo).
"""
import sys, math, json, re

PROG = r'C:\Buscar Termos en plano\programa'
if PROG not in sys.path:
    sys.path.insert(0, PROG)

CAPAS = ('COMPONENTES', '00_COMPONENTS')
R_BANDA = (1.55, 2.8)     # radio de los arcos del contorno de una abertura (pt)
CUERDA_MIN = 0.9          # arcos con cuerda menor dan un centro poco fiable (solo se usan para el contorno)
TOL_CX, TOL_CY = 0.8, 1.6  # agrupamiento de centros de curvatura de una misma abertura

TIPOS = {'12XP': 'quattro', '13XC1': 'quattro', '13X24': 'quattro', '62XDIO': 'dio', '62XDO': 'ptt'}

# Correcciones del tablero 75286-1 / funcional 75287 hoja 62 (ver 'dudas'): el instructivo le asigna
# a 62XDIO bornes que en el funcional son de 62XDO.  clave (componente_json, texto, cable) ->
# (componente_real, borne, lado_instructivo, confianza, motivo)
CORRECCIONES_75286 = {
    ('62XDIO', '62XDIO 3 ARRIBA', '6203'): ('62XDO', 3, 'ARRIBA', 'alta',
        'funcional h62 C6: 6203 entra a 62XDO 3 (izq.); foto 12.35.39(2): 6203 en la 2a pieza de 62XDO arriba, entrada extrema'),
    ('62XDIO', '62XDIO 5 ARRIBA', '6206'): ('62XDO', 5, 'ARRIBA', 'alta',
        'funcional h62 D6: 6206 entra a 62XDO 5 (izq.); foto 12.35.39(2): 6206 en la 3a pieza de 62XDO arriba, entrada extrema'),
    ('62XDIO', '62XDIO 3 ABAJO', '6204'): ('62XDO', 3, 'ABAJO', 'media',
        'funcional h62 C7: 6204 sale de 62XDO 3 (der.) a SP-1; cable de campo, no conectado en las fotos'),
    ('62XDIO', '62XDIO 4 ABAJO', '6205'): ('62XDO', 4, 'ABAJO', 'media',
        'funcional h62 C7: 6205 sale de 62XDO 4 (der.) a SP-1; cable de campo, no conectado en las fotos'),
    ('62XDIO', '62XDIO 5 ABAJO', '6207'): ('62XDO', 5, 'ABAJO', 'media',
        'funcional h62 D7: 6207 sale de 62XDO 5 (der.) a SP-2; cable de campo, no conectado en las fotos'),
    ('62XDIO', '62XDIO 6 ABAJO', '6208'): ('62XDO', 6, 'ABAJO', 'media',
        'funcional h62 D7: 6208 sale de 62XDO 6 (der.) a SP-2; cable de campo, no conectado en las fotos'),
    ('62XDO', '62XDO ARRIBA', '6202'): ('62XDO', 1, 'ABAJO', 'baja',
        'extremo espurio: en el funcional 6202 va de 62XDO 1 (der.) a BH-01-ZV (campo); en el tablero 6202 solo '
        'entra en la 1a pieza de 62XDO abajo (foto 2.1). Se devuelve ese mismo punto'),
}


# ----------------------------------------------------------------------------------------- geometria
def trazos(pdf, pi, box=None, strokes=None):
    """[(capa, op, puntos, color)] de la pagina, opcionalmente solo los que caen enteros dentro de box."""
    if strokes is None:
        import pypdf
        from pdfvec import page_strokes, layer_names
        r = pypdf.PdfReader(pdf)
        strokes = page_strokes(r, pi, layer_names(r), with_color=True)
    if box is None:
        return strokes
    return [s for s in strokes if s[2] and all(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in s[2])]


def _circ(a, b, c):
    ax, ay = a; bx, by = b; cx, cy = c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return ux, uy, math.hypot(ax - ux, ay - uy)


def _suave(p, giro_max=60.0):
    """Curva aplanada (Bezier de 3-4 puntos): todos los giros en el mismo sentido y menores a giro_max."""
    sg = 0
    for a, b, c in zip(p, p[1:], p[2:]):
        v1 = (b[0] - a[0], b[1] - a[1]); v2 = (c[0] - b[0], c[1] - b[1])
        n1, n2 = math.hypot(*v1), math.hypot(*v2)
        if n1 < 1e-6 or n2 < 1e-6:
            return False
        cr = v1[0] * v2[1] - v1[1] * v2[0]
        ang = math.degrees(math.atan2(abs(cr), v1[0] * v2[0] + v1[1] * v2[1]))
        if ang > giro_max or ang < 1.0:
            return False
        s = 1 if cr > 0 else -1
        if sg and s != sg:
            return False
        sg = s
    return True


def _tiene_x(tr, cx, cy, r):
    """True si hay dos diagonales que cruzan cerca del centro (cabeza de tornillo con X)."""
    n = 0
    for l, o, p, c in tr:
        if l not in CAPAS or o != 'S':
            continue
        for a, b in zip(p, p[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy)
            if L < 0.5 or abs(dx) < 0.25 * L or abs(dy) < 0.25 * L:
                continue
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if math.hypot(mx - cx, my - cy) > r:
                continue
            dist = abs(dy * (cx - a[0]) - dx * (cy - a[1])) / L
            if dist < 0.35:
                n += 1
    return n >= 2


def aberturas(tr):
    """Entradas push-in: [{'x','y','w','h','r','n'}] (x,y = centro del contorno)."""
    arcos = []
    for l, o, p, c in tr:
        if l in CAPAS and o == 'S' and len(p) in (3, 4) and _suave(p):
            cc = _circ(p[0], p[len(p) // 2], p[-1])
            if cc and R_BANDA[0] <= cc[2] <= R_BANDA[1]:
                arcos.append((cc, p, math.dist(p[0], p[-1])))
    cl = []
    for cc, p, ch in arcos:
        if ch < CUERDA_MIN:
            continue
        for g in cl:
            if abs(g['cx'] - cc[0]) <= TOL_CX and abs(g['cy'] - cc[1]) <= TOL_CY:
                g['m'].append(cc)
                g['cx'] = sum(m[0] for m in g['m']) / len(g['m'])
                g['cy'] = sum(m[1] for m in g['m']) / len(g['m'])
                break
        else:
            cl.append({'cx': cc[0], 'cy': cc[1], 'm': [cc]})
    out = []
    for g in cl:
        if len(g['m']) < 2:
            continue
        pts = [q for cc, p, ch in arcos
               if abs(cc[0] - g['cx']) <= TOL_CX + 0.05 and abs(cc[1] - g['cy']) <= TOL_CY + 0.05 for q in p]
        xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        w, h = x1 - x0, y1 - y0
        r = sum(m[2] for m in g['m']) / len(g['m'])
        if not (2.5 <= w <= 6.5 and 2.5 <= h <= 6.5):
            continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if _tiene_x(tr, cx, cy, r):
            continue
        out.append({'x': cx, 'y': cy, 'w': w, 'h': h, 'r': r, 'n': len(g['m'])})
    # sin duplicados
    uniq = []
    for a in sorted(out, key=lambda a: (a['x'], a['y'])):
        if not any(abs(a['x'] - b['x']) < 0.6 and abs(a['y'] - b['y']) < 1.0 for b in uniq):
            uniq.append(a)
    return uniq


def piezas(ab):
    """Agrupa las aberturas por columna (= pieza), izq -> der.  Cada pieza:
    {'x','ymid','arriba':[extrema, interior...], 'abajo':[extrema, interior...]}"""
    cols = []
    for a in sorted(ab, key=lambda a: a['x']):
        if cols and abs(a['x'] - cols[-1][-1]['x']) < 1.0:
            cols[-1].append(a)
        else:
            cols.append([a])
    out = []
    for c in cols:
        ys = sorted(c, key=lambda a: a['y'])
        if len(ys) < 2:
            continue
        g, i = max((ys[k + 1]['y'] - ys[k]['y'], k) for k in range(len(ys) - 1))
        bajo, alto = ys[:i + 1], ys[i + 1:]
        out.append({'x': sum(a['x'] for a in c) / len(c),
                    'ymid': (bajo[-1]['y'] + alto[0]['y']) / 2,
                    'arriba': sorted(alto, key=lambda a: -a['y']),   # [0] = extrema (mas lejos del riel)
                    'abajo': sorted(bajo, key=lambda a: a['y']),
                    'ancho': max(a['w'] for a in c)})
    return out


def puentes(tr):
    """Rectangulos rellenos de color (puentes FBS dibujados, capas 'rojo', '_Zona Segura', ...):
    [{'x0','y0','x1','y1','color'}]"""
    out = []
    for l, o, p, c in tr:
        if o != 'f' or not p or not c or l == 'Texto etiquetas':
            continue
        r_, g_, b_ = c[:3]
        amarillo = r_ > 0.8 and g_ > 0.7 and b_ < 0.4
        if amarillo or max(c[:3]) - min(c[:3]) < 0.3:     # etiquetas amarillas / grises / blanco / negro
            continue
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        out.append({'x0': min(xs), 'x1': max(xs), 'y0': min(ys), 'y1': max(ys), 'color': tuple(round(v, 2) for v in c[:3])})
    return out


def grupo(pz, x_etiqueta, x_limite, paso_max=9.0):
    """Piezas contiguas a la derecha de la etiqueta del componente (hasta la etiqueta siguiente)."""
    sel = []
    for p in sorted(pz, key=lambda p: p['x']):
        if x_etiqueta < p['x'] < x_limite:
            if sel and p['x'] - sel[-1]['x'] > paso_max:
                break
            sel.append(p)
    return sel


def lado_anodo_dio(g, pts_puente):
    """'abajo' o 'arriba': extremo del anodo (lado del puente) de un grupo de piezas PT 2,5-DIO."""
    if not g:
        return None
    x0, x1 = g[0]['x'] - 2, g[-1]['x'] + 2
    ymid = sum(p['ymid'] for p in g) / len(g)
    cand = [b for b in pts_puente if b['x0'] < x1 and b['x1'] > x0]
    if not cand:
        return None
    yb = sum((b['y0'] + b['y1']) / 2 for b in cand) / len(cand)
    return 'abajo' if yb < ymid else 'arriba'


# ----------------------------------------------------------------------------------------- asignacion
def num(s):
    m = re.match(r'\s*(\d+)', str(s or ''))
    return int(m.group(1)) if m else None


def entrada(tipo, g, borne, punto=None, lado=None, anodo='abajo'):
    """Devuelve (abertura, descripcion) o (None, motivo)."""
    if borne is None:
        return None, 'borne sin numero'
    lado = (lado or '').upper()
    if tipo == 'quattro':
        if punto not in (1, 2, 3, 4):
            return None, f'punto {punto} invalido'
        k, sub = borne, {1: ('arriba', 0), 2: ('arriba', 1), 3: ('abajo', 1), 4: ('abajo', 0)}[punto]
        desc = f"pieza {k}, {sub[0]}, entrada {'extrema' if sub[1] == 0 else 'interior'}"
    elif tipo == 'ptt':
        k = (borne + 1) // 2
        sub = ('arriba' if lado.startswith('ARR') else 'abajo', 0 if borne % 2 else 1)
        desc = (f"pieza {k}, {sub[0]}, entrada {'extrema (piso de abajo, impar)' if sub[1] == 0 else 'interior (piso de arriba, par)'}")
    elif tipo == 'dio':
        k = borne
        ano = lado.startswith('ARR')
        fis = anodo if ano else ('arriba' if anodo == 'abajo' else 'abajo')
        sub = (fis, 0)
        desc = f"pieza {k}, {'anodo' if ano else 'catodo'} -> extremo fisico {fis}"
    else:
        return None, f'tipo {tipo} desconocido'
    if k < 1 or k > len(g):
        return None, f'la pieza {k} no existe ({len(g)} piezas en el dibujo)'
    lst = g[k - 1][sub[0]]
    if sub[1] >= len(lst):
        return None, f'pieza {k}: solo {len(lst)} entradas en el lado {sub[0]}'
    return lst[sub[1]], desc


def ubicar(usos_json, pdf, pi, tipos=TIPOS, correcciones=None, box=None, strokes=None):
    d = json.load(open(usos_json, encoding='utf-8')) if isinstance(usos_json, str) else usos_json
    C = d['componentes']
    tags = list(tipos)
    riel = C[tags[0]]['etiqueta_topografico'].get('riel')
    if box is None:
        xs = [C[t]['etiqueta_topografico']['x'] for t in tags]
        ys = [C[t]['etiqueta_topografico']['y'] for t in tags]
        box = (min(xs) - 5, min(ys) - 45, max(xs) + 45, max(ys) + 45)
    tr = trazos(pdf, pi, box, strokes)
    pz = piezas(aberturas(tr))
    fills = puentes(tr)
    todas = sorted((v['etiqueta_topografico']['x'], k) for k, v in C.items()
                   if v['etiqueta_topografico'].get('riel') == riel)
    grupos = {}
    for t in tags:
        ex = C[t]['etiqueta_topografico']['x']
        sig = [x for x, k in todas if x > ex + 0.5]
        grupos[t] = grupo(pz, ex, min(sig) if sig else 1e9)
    anodos = {t: (lado_anodo_dio(grupos[t], fills) or 'abajo') for t in tags if tipos[t] == 'dio'}
    res = []
    for t in tags:
        for u in C[t]['usos']:
            item = dict(componente=t, texto=u['texto'], cable=u['cable'], x=None, y=None, confianza='baja', como='')
            comp, borne, lado, punto = t, num(u['borne']), u.get('parte') or u.get('lado'), u.get('punto')
            conf, extra = None, ''
            key = (t, u['texto'], u['cable'])
            if correcciones and key in correcciones:
                comp, borne, lado, conf, extra = correcciones[key]
            e, desc = entrada(tipos[comp], grupos[comp], borne, punto, lado, anodos.get(comp, 'abajo'))
            if e is None:
                item['como'] = desc
                res.append(item); continue
            item.update(x=round(e['x'], 2), y=round(e['y'], 2), comp_fisico=comp, borne_fisico=borne,
                        detalle=f'{comp} ' + desc, confianza=conf or 'alta', nota=extra)
            res.append(item)
    return res, grupos, pz, fills, anodos


if __name__ == '__main__':
    import os, pickle
    here = os.path.dirname(os.path.abspath(__file__))
    usos = os.path.join(here, 'usos_por_componente.json')
    pdf = os.path.join(os.path.dirname(here), 'topo.pdf')
    pk = os.path.join(here, 'strokes_p8.pkl')
    st = pickle.load(open(pk, 'rb')) if os.path.exists(pk) else None
    res, grupos, pz, fills, anodos = ubicar(usos, pdf, 7, TIPOS, CORRECCIONES_75286, strokes=st)
    for t, g in grupos.items():
        print(t, len(g), 'piezas x =', [round(p['x'], 2) for p in g],
              'filas y =', sorted({round(a['y'], 2) for p in g for a in p['arriba'] + p['abajo']}, reverse=True))
    print('anodo DIO:', anodos, 'puentes:', [(round(f['x0'], 1), round(f['x1'], 1), round(f['y0'], 1), round(f['y1'], 1), f['color']) for f in fills])
    for r in res:
        print(f"{r['texto']:18s} {r['cable']:5s} {r['x']} {r['y']}  {r['confianza']:5s} {r.get('detalle', r['como'])}")
