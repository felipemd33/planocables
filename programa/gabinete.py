"""Estacion E8 (cableado DENTRO del gabinete): el gabinete en 3D y la lista de cables de E8.

E6 es la bandeja (la placa de fondo: lo que arma el instructivo). E8 es lo que se cablea con la bandeja ya montada en
el gabinete:
  - la otra punta de las lineas de E6 que dicen '-> LI' / '-> LD': el cable queda tirado en la salida de la bandeja y se
    conecta en el lateral, la puerta... El instructivo la guarda en 'destino_e8' (instructivo.build);
  - los pendientes LI <-> LI;
  - la lista 'otra estacion' que va a E8 (35 mm2, zona hidraulica).

Todo sale del topografico y de lo que ya leyo el programa (layout.json e instructivo.json), sin nada escrito a mano por
producto:
  - el contorno del gabinete (ancho x alto) es el recuadro que encierra la placa de la bandeja en su hoja (escala de
    layout.json);
  - las vistas de los laterales son las dibujadas al costado de una vista de frente del mismo contorno, DESPLEGADAS
    (el borde pegado al frente es el fondo del gabinete): se reconocen por las lineas verticales del alto del gabinete.
    La profundidad sale de ahi (y el espesor de la puerta, si la vista la dibuja);
  - la puerta es la vista con el mismo contorno titulada '... PUERTA' ('POSTERIOR' = vista desde adentro: espejada);
  - los aparatos de afuera de la bandeja: layout.json y las etiquetas de las otras vistas (sin OCR);
  - las canaletas de cada vista: ruteo.ducts.
Lo que el plano no dice (caras de montaje, espesor de la puerta...) va como supuesto y con aviso. Lo que el usuario
corrige en el visor (un aparato sin etiqueta ubicado a mano) va en instructivo.json['e8']['ubicaciones'] y manda.

Ejes del gabinete (mm, mano derecha, igual que three.js con Y arriba): origen en el rincon de abajo, a la izquierda y
al fondo, mirando el gabinete de frente; x = ancho (izquierda -> derecha), y = alto (piso -> techo), z = profundidad
(fondo -> puerta). La puerta cerrada va de z = prof a z = prof + puerta.
Cada vista: [x, y, z] = o_mm + esc * ((X - o_pt[0]) * ex + (Y - o_pt[1]) * ey) + h * normal (h = altura sobre la cara
de montaje, normal hacia adentro del gabinete), con (X, Y) en pt del PDF (Y hacia arriba, como layout.json).

Uso suelto (no escribe nada):  python gabinete.py <carpeta del trabajo> [salida.json]
"""
import re, math, json, os, collections

VERSION = 'e8-2026.10.03-4'

# ---- supuestos de montaje (el plano no los acota), en mm
Z_FONDO = 20.0          # cara de montaje de la placa de fondo, desde la cara exterior del fondo
LATERAL = 25.0          # cara de montaje de los laterales, desde su cara exterior
PUERTA = 30.0           # espesor de la puerta si la vista lateral no la dibuja
CHAPA = 2.0             # la cara interior de la chapa de la puerta queda a 2 mm de su cara exterior
APERTURA = 110          # grados que se abre la puerta en el visor
H_CANAL = {'fondo': 30.0, 'lateral': 20.0, 'puerta': 20.0}       # el mazo va por adentro de la canaleta
H_APARATO = {'fondo': 50.0, 'lateral': 45.0, 'puerta': 18.0}     # los bornes, por delante de la placa
PROF_CANALETA = {'fondo': 60.0, 'lateral': 40.0, 'puerta': 40.0}  # si la vista no tiene el rotulo 'CD 40x80'
PASO_BORNE = 4.93       # mm de un borne al siguiente de una bornera (3,5 pt a 1:4, como instructivo.build)
DY_PISO = 12.7          # mm del eje del riel al piso de arriba / abajo de un borne (9 pt a 1:4, como instructivo.build)
ASPECTO_TOL = 0.015     # otra vista del mismo contorno: ancho / alto igual +-1,5 %

RX_TITULO = re.compile(r'VISTA|PUERTA', re.I)
RX_PUERTA = re.compile(r'PUERTA', re.I)
RX_DESDE_ADENTRO = re.compile(r'POSTERIOR|INTERIOR|TRASERA|DENTRO', re.I)
RX_CERRADURA = re.compile(r'CERRADURA|MANIJA|LLAVE', re.I)
RX_FRENTE = re.compile(r'FRENTE|FRONTAL|EXTERIOR', re.I)
RX_NO_VISTA = re.compile(r'BANDEJA|PLACA|MECANIZ|RIEL|DUCTO|DETALLE|ETIQUET', re.I)
RX_TIERRA = re.compile(r'TIERRA|⏚', re.I)
RX_CD = re.compile(r'CD\s*(\d{2,3})\s*[xX]\s*(\d{2,3})')
# capas que no son aparatos (para los recuadros sin etiqueta de la puerta)
RX_NO_CAJA = re.compile(r'TEXT|COTA|DIM|ROTULO|CARTEL|CENTRO|TABLERO|ENVOLVENTE|CANAL|DUCTO|RIEL|^VP$|^0$', re.I)
TIERRA_TAG = 'TIERRA GABINETE'

ZONA_BASE = {'bandeja': 'fondo', 'fondo': 'fondo', 'lateral izq': 'lateral', 'lateral der': 'lateral', 'puerta': 'puerta'}
RANGO = {'bandeja': 0, 'lateral izq': 1, 'lateral der': 1, 'fondo': 2, 'puerta': 3, 'otro': 4, 'sin ubicar': 5}


def r1(v, n=1):
    return round(float(v), n)


def _redondo(v):
    """medida del gabinete: a 5 mm si esta a menos de 1,5 mm (800,4 -> 800), si no al mm"""
    r5 = round(v / 5.0) * 5
    return float(r5) if abs(v - r5) <= 1.5 else float(round(v))


def _add(a, b, k=1.0):
    return [a[0] + k * b[0], a[1] + k * b[1], a[2] + k * b[2]]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def a3d(v, X, Y, h=0.0):
    """punto (X, Y) de la hoja de la vista v -> [x, y, z] del gabinete (h mm hacia adentro de su cara de montaje)"""
    p = _add(_add(v['o_mm'], v['ex'], v['esc'] * (X - v['o_pt'][0])), v['ey'], v['esc'] * (Y - v['o_pt'][1]))
    return [r1(c) for c in _add(p, v['normal'], h)]


def a_hoja(v, p):
    """[x, y, z] del gabinete -> (X, Y) en la hoja de la vista v (ex y ey son ortonormales)"""
    d = [p[0] - v['o_mm'][0], p[1] - v['o_mm'][1], p[2] - v['o_mm'][2]]
    return (v['o_pt'][0] + _dot(d, v['ex']) / v['esc'], v['o_pt'][1] + _dot(d, v['ey']) / v['esc'])


# ------------------------------------------------------------------ geometria de las hojas
def _rects(st, min_lado=8.0):
    """recuadros cerrados alineados con los ejes: [(x0, y0, x1, y1, capa)] sin repetidos"""
    from topo import rect_of
    out, vistos = [], set()
    for l, o, p, *_ in st:
        if len(p) < 4:
            continue
        r = rect_of(p, o)
        if not r or min(r[2] - r[0], r[3] - r[1]) < min_lado:
            continue
        k = tuple(round(v, 1) for v in r)
        if k in vistos:
            continue
        vistos.add(k); out.append(k + (l,))
    return out


def _verticales(st, min_largo=40.0):
    """lineas verticales: [(x, y0, y1, capa)]"""
    out = []
    for l, o, p, *_ in st:
        for a, b in zip(p, p[1:]):
            if abs(a[0] - b[0]) < 0.3 and abs(a[1] - b[1]) >= min_largo:
                out.append(((a[0] + b[0]) / 2, min(a[1], b[1]), max(a[1], b[1]), l))
    return out


def _contorno(rects, reg):
    """el recuadro mas chico que encierra la placa de la bandeja (con margen) y no es mucho mas grande: el gabinete"""
    rw, rh = reg[2] - reg[0], reg[3] - reg[1]
    c = [r[:4] for r in rects if r[0] < reg[0] - 0.5 and r[1] < reg[1] - 0.5 and r[2] > reg[2] + 0.5 and r[3] > reg[3] + 0.5
         and r[2] - r[0] <= 1.6 * rw and r[3] - r[1] <= 1.6 * rh]
    return min(c, key=lambda r: (r[2] - r[0]) * (r[3] - r[1])) if c else None


def _lateral(segs, C, lado, esc):
    """vista DESPLEGADA de un lateral al costado ('izq' / 'der') de la vista de frente C: borde del fondo = linea vertical
    del alto del gabinete pegada al frente; borde de afuera = la linea larga mas lejana (el frente del cuerpo, o la
    puerta cerrada si la vista la dibuja: entonces hay lineas largas a 15-36 mm hacia adentro).
    -> dict(x_fondo, x_frente, prof_mm, puerta_mm) o None"""
    cx0, cy0, cx1, cy1 = C
    W, H = cx1 - cx0, cy1 - cy0
    tol = 0.015 * H
    alto = lambda s: s[2] - s[1]
    llena = lambda s: s[1] <= cy0 + tol and s[2] >= cy1 - tol and alto(s) <= H + 3 * tol
    izq = lado == 'izq'
    # (pegada al frente en el 75441; separada por un hueco de hasta ~0,4 del ancho en el 66817)
    if izq:
        inn = [s[0] for s in segs if llena(s) and cx0 - 0.45 * W <= s[0] <= cx0 - 0.5]
        xi = max(inn) if inn else None
    else:
        inn = [s[0] for s in segs if llena(s) and cx1 + 0.5 <= s[0] <= cx1 + 0.45 * W]
        xi = min(inn) if inn else None
    if xi is None:
        return None
    lejos = (lambda x: xi - x) if izq else (lambda x: x - xi)
    largas = [lejos(s[0]) for s in segs if alto(s) >= 0.85 * H and s[1] >= cy0 - tol and s[2] <= cy1 + tol
              and 0.12 * W <= lejos(s[0]) <= 1.3 * W]
    if not largas:
        return None
    d_ext = max(largas)
    pu = [d for d in largas if 15 / esc <= d_ext - d <= 36 / esc]
    d_fr = min(pu) if pu else d_ext
    return dict(lado=lado, x_fondo=xi, x_frente=xi - d_fr if izq else xi + d_fr, y0=cy0, y1=cy1,
                prof_mm=d_fr * esc, puerta_mm=(d_ext - d_fr) * esc if pu else None)


def _titulo(lines, C):
    """titulo de la vista C: el texto con VISTA / PUERTA mas cerca, arriba o abajo del contorno y dentro de su ancho"""
    H = C[3] - C[1]
    best = None
    for l in lines:
        t = l['text'].strip()
        if not RX_TITULO.search(t):
            continue
        b = l['bbox']; cx = (b[0] + b[2]) / 2
        if not C[0] <= cx <= C[2]:
            continue
        gap = b[1] - C[3] if b[1] >= C[3] else (C[1] - b[3] if b[3] <= C[1] else None)
        if gap is None or gap > 0.2 * H:
            continue
        if best is None or gap < best[0]:
            best = (gap, t)
    return best[1] if best else ''


def _cd(lines, box):
    """profundidad de canaleta del rotulo 'CD 40x80' dentro de la vista (la mas comun), o None"""
    vals = [int(m.group(2)) for l in lines for m in [RX_CD.search(l['text'])]
            if m and box[0] <= (l['bbox'][0] + l['bbox'][2]) / 2 <= box[2] and box[1] <= (l['bbox'][1] + l['bbox'][3]) / 2 <= box[3]]
    return collections.Counter(vals).most_common(1)[0][0] if vals else None


def _vista(id_, nombre, zona, pag, box, esc, o_pt, o_mm, ex, ey, normal, **kw):
    return dict(id=id_, nombre=nombre, zona=zona, pag=pag, box=[r1(v) for v in box], esc=round(esc, 4),
                o_pt=[r1(v) for v in o_pt], o_mm=[r1(v) for v in o_mm], ex=ex, ey=ey, normal=normal, **kw)


# ------------------------------------------------------------------ lectura del gabinete (lenta: se guarda en cache)
def leer_gabinete(topo_pdf, lay, conocidos=(), log=print):
    """modelo del gabinete desde el topografico y su layout.json. conocidos = tags del funcional (para buscar las
    etiquetas de las otras vistas). No escribe nada (tampoco el cache de OCR: lee sin OCR)."""
    avisos, supuestos = [], []
    lay = lay or {}
    pag_b, reg, esc = lay.get('pag'), lay.get('region'), lay.get('escala')
    conocidos = sorted({t for t in conocidos if t} | set((lay.get('comp') or {}).keys()))
    M = dict(version=VERSION, vistas=[], aparatos={}, canaletas=[], recuadros_puerta=[], avisos=avisos, supuestos=supuestos)
    if not (pag_b and reg and esc and os.path.exists(topo_pdf or '')):
        avisos.append('No hay bandeja leída en el topográfico: el gabinete se dibuja con medidas por defecto (800 × 1000 × 400).')
        M['gabinete'] = dict(ancho=800.0, alto=1000.0, prof=400.0, puerta=PUERTA, bisagra='izq', y_mazo=500.0, apertura=APERTURA)
        _eje(M)
        return M
    import pypdf
    from pdfvec import page_strokes, layer_names
    from textdec import Decoder, page_text
    from topo import unir_partidas, etiquetas_hoja
    import ruteo
    reader = pypdf.PdfReader(topo_pdf); names = layer_names(reader)
    dec = Decoder(use_ocr=False)
    hojas = {}

    def hoja(pi):
        """trazos, recuadros y verticales de la pagina pi (0-based); el texto se lee aparte (es lo lento)"""
        if pi not in hojas:
            st = page_strokes(reader, pi, names)
            hojas[pi] = dict(st=st, rects=_rects(st), vert=_verticales(st), lines=None)
        return hojas[pi]

    def textos(pi):
        h = hoja(pi)
        if h['lines'] is None:
            h['lines'] = unir_partidas(page_text(h['st'], dec, ('WATERMARK',)))
        return h['lines']

    # ---- hoja de la bandeja: contorno del gabinete, placa y laterales desplegados
    log('Gabinete: leyendo la hoja de la bandeja…')
    hb = hoja(pag_b - 1)
    C = _contorno(hb['rects'], reg)
    rw, rh = (reg[2] - reg[0]) * esc, (reg[3] - reg[1]) * esc
    if C:
        ancho, alto = _redondo((C[2] - C[0]) * esc), _redondo((C[3] - C[1]) * esc)
    else:
        ancho, alto = _redondo(rw + 60), _redondo(rh + 120)
        m = (60 / 2 / esc, 120 / 2 / esc)
        C = (reg[0] - m[0], reg[1] - m[1], reg[2] + m[0], reg[3] + m[1])
        avisos.append(f'No se encontró el contorno del gabinete alrededor de la placa: se supone de {ancho:.0f} × {alto:.0f} mm '
                      '(placa centrada con 30 mm a los costados y 60 mm arriba y abajo).')
    aspecto = (C[2] - C[0]) / (C[3] - C[1])
    placa_rel = ((reg[2] - reg[0]) / (C[2] - C[0]), (reg[3] - reg[1]) / (C[3] - C[1]))
    laterales = {}
    for lado in ('izq', 'der'):
        s = _lateral(hb['vert'], C, lado, esc)
        if s:
            laterales[lado] = dict(s, pag=pag_b, esc=esc, C=C)
    # ---- otras hojas: vistas con el mismo contorno (interior desplegado, puerta, frente exterior)
    otras = []
    if not lay.get('eplan'):          # (EPLAN: solo la hoja de bandejas)
        for pi in range(min(len(reader.pages), 40)):
            if pi == pag_b - 1:
                continue
            h = hoja(pi)
            for r in h['rects']:
                w, hh = r[2] - r[0], r[3] - r[1]
                if w < 120 or hh < 120 or abs(w / hh / aspecto - 1) > ASPECTO_TOL:
                    continue
                if any(abs(r[0] - o['C'][0]) < 2 and abs(r[1] - o['C'][1]) < 2 and o['pi'] == pi for o in otras):
                    continue
                interior = any(abs((q[2] - q[0]) / w - placa_rel[0]) < 0.02 and abs((q[3] - q[1]) / hh - placa_rel[1]) < 0.02
                               and r[0] <= q[0] and q[2] <= r[2] and r[1] <= q[1] and q[3] <= r[3] for q in h['rects'])
                otras.append(dict(pi=pi, C=r[:4], interior=interior, esc=ancho / w))
        for i, o in enumerate(otras):
            if not i or otras[i - 1]['pi'] != o['pi']:
                log(f'Gabinete: leyendo la hoja {o["pi"] + 1}…')
            o['titulo'] = _titulo(textos(o['pi']), o['C'])
            # interior = tiene la placa adentro; puerta / frente exterior: por el titulo de la vista (un recuadro con la
            # misma proporcion sin titulo, como la placa sola del mecanizado o un detalle de etiquetas, no es una vista)
            o['tipo'] = 'interior' if o['interior'] else ('puerta' if RX_PUERTA.search(o['titulo']) else
                        'exterior' if RX_FRENTE.search(o['titulo']) and not RX_NO_VISTA.search(o['titulo']) else None)
            if o['tipo'] == 'interior':
                for lado in ('izq', 'der'):
                    if lado in laterales:
                        continue
                    s = _lateral(hoja(o['pi'])['vert'], o['C'], lado, o['esc'])
                    if s:
                        laterales[lado] = dict(s, pag=o['pi'] + 1, esc=o['esc'], C=o['C'])
    # profundidad: la de la vista lateral (la de la hoja de la bandeja manda)
    lat_med = [laterales[k] for k in ('izq', 'der') if k in laterales]
    if lat_med:
        prof = _redondo(lat_med[0]['prof_mm'])
        pu = next((x['puerta_mm'] for x in lat_med if x.get('puerta_mm')), None)
        puerta = _redondo(pu) if pu and 10 <= pu <= 80 else PUERTA
        if not pu:
            supuestos.append(f'Puerta de {PUERTA:.0f} mm de espesor (la vista lateral no la dibuja).')
    else:
        prof, puerta = 400.0, PUERTA
        avisos.append('No se encontró ninguna vista lateral del gabinete: se supone de 400 mm de profundidad y puerta de 30 mm.')
    G = dict(ancho=ancho, alto=alto, prof=prof, puerta=puerta, apertura=APERTURA, aspecto=round(aspecto, 4))
    M['gabinete'] = G
    z_pi = prof + puerta - CHAPA           # cara interior de la chapa de la puerta (cerrada)
    supuestos += [f'Cara de montaje de la placa de fondo a {Z_FONDO:.0f} mm del fondo y de los laterales a {LATERAL:.0f} mm de '
                  'la cara exterior (el plano no las acota).',
                  f'Cara interior de la puerta a {z_pi:.0f} mm del fondo con la puerta cerrada.']

    # ---- vistas (placas con su imagen)
    V = M['vistas']
    V.append(_vista('pared_fondo', 'Fondo del gabinete', 'fondo', pag_b, C, esc, (C[0], C[1]), (0, 0, 1.6), [1, 0, 0], [0, 1, 0],
                    [0, 0, 1], imagen=True, ductos=[]))
    V.append(_vista('fondo', 'Placa de fondo (bandeja de E6)', 'bandeja', pag_b, reg, esc, (C[0], C[1]), (0, 0, Z_FONDO),
                    [1, 0, 0], [0, 1, 0], [0, 0, 1], imagen=True, ductos=lay.get('ductos') or [],
                    placa=dict(ancho=r1(rw), alto=r1(rh))))
    for lado, s in sorted(laterales.items()):
        izq = lado == 'izq'
        x_face = LATERAL if izq else ancho - LATERAL
        box = (min(s['x_fondo'], s['x_frente']), s['y0'], max(s['x_fondo'], s['x_frente']), s['y1'])
        v = _vista('lateral_' + ('izquierda' if izq else 'derecha'), 'Lateral ' + ('izquierdo (LI)' if izq else 'derecho (LD)'),
                   'lateral ' + lado, s['pag'], box, s['esc'], (s['x_fondo'], s['y0']), (x_face, 0, 0),
                   [0, 0, -1] if izq else [0, 0, 1], [0, 1, 0], [1, 0, 0] if izq else [-1, 0, 0], imagen=True)
        try:
            v['ductos'] = ruteo.ducts(topo_pdf, s['pag'] - 1, list(box))
        except Exception:
            v['ductos'] = []
        V.append(v)
    for lado in ('izq', 'der'):
        if lado not in laterales:
            avisos.append(f'Sin vista del lateral {"izquierdo" if lado == "izq" else "derecho"} en el topográfico: se dibuja liso.')
    puertas = [o for o in otras if o['tipo'] == 'puerta']
    exteriores = [o for o in otras if o['tipo'] == 'exterior']
    vp = None
    if puertas:
        o = puertas[0]; c = o['C']
        adentro = bool(RX_DESDE_ADENTRO.search(o['titulo'])) or not re.search(r'FRENTE|EXTERIOR', o['titulo'], re.I)
        if adentro:      # vista posterior: espejada (la izquierda de la hoja es la derecha del gabinete)
            vp = _vista('puerta', 'Puerta por dentro', 'puerta', o['pi'] + 1, c, o['esc'], (c[0], c[1]), (ancho, 0, z_pi),
                        [-1, 0, 0], [0, 1, 0], [0, 0, -1], imagen=True, en_puerta=True, titulo=o['titulo'])
        else:
            vp = _vista('puerta', 'Puerta', 'puerta', o['pi'] + 1, c, o['esc'], (c[0], c[1]), (0, 0, z_pi),
                        [1, 0, 0], [0, 1, 0], [0, 0, -1], imagen=False, en_puerta=True, titulo=o['titulo'])
            supuestos.append('La vista de la puerta es de afuera: los aparatos se ubican por su frente.')
        try:
            vp['ductos'] = ruteo.ducts(topo_pdf, o['pi'], list(c))
        except Exception:
            vp['ductos'] = []
        V.append(vp)
    else:
        avisos.append('Sin vista de la puerta por dentro (una vista del mismo contorno titulada «… PUERTA»): la puerta se dibuja lisa.')
    if exteriores:
        o = exteriores[0]; c = o['C']
        V.append(_vista('frente_exterior', 'Frente (puerta por fuera)', 'puerta_ext', o['pi'] + 1, c, o['esc'], (c[0], c[1]),
                        (0, 0, prof + puerta + 0.8), [1, 0, 0], [0, 1, 0], [0, 0, 1], imagen=True, en_puerta=True,
                        titulo=o['titulo'], ductos=[]))
        if vp is None:       # sin vista de adentro: los aparatos de la puerta se toman del frente
            vp = V[-1]
    porid = {v['id']: v for v in V}

    # ---- profundidad de las canaletas (rotulo 'CD 40x80' de la vista, si lo tiene)
    for v in V:
        base = ZONA_BASE.get(v['zona'])
        if not base or not v.get('ductos'):
            continue
        cd = _cd(textos(v['pag'] - 1), v['box'])
        prof_c = float(cd) if cd and 20 <= cd <= 150 else PROF_CANALETA[base]
        for d in v['ductos']:
            b = d['b']
            p0, p1 = a3d(v, b[0], b[1], 0), a3d(v, b[2], b[3], prof_c)
            M['canaletas'].append(dict(vista=v['id'], min=[min(a, c) for a, c in zip(p0, p1)], max=[max(a, c) for a, c in zip(p0, p1)],
                                       ex=bool(d.get('ex')), en_puerta=bool(v.get('en_puerta'))))

    # ---- aparatos: layout.json (hoja de la bandeja) y las etiquetas de las otras vistas
    A = M['aparatos']
    dentro = lambda b, x, y, m=0.0: b[0] - m <= x <= b[2] + m and b[1] - m <= y <= b[3] + m
    lat_v = [v for v in V if v['zona'].startswith('lateral')]

    def vista_de(pag, x, y):
        for v in lat_v:
            if v['pag'] == pag and dentro(v['box'], x, y):
                return v
        if vp is not None and vp['pag'] == pag and dentro(vp['box'], x, y):
            return vp
        if pag == pag_b and dentro(C, x, y):
            return porid['fondo']
        return None

    def poner(tag, v, x, y, fuente, leido=None):
        if tag in A:
            return
        zona = 'bandeja' if v['id'] == 'fondo' and ((lay.get('comp') or {}).get(tag) or {}).get('ubic') == 'BANDEJA' else \
            ('fondo' if v['id'] == 'fondo' else ('puerta' if v.get('en_puerta') else v['zona']))
        A[tag] = dict(tag=tag, zona=zona, vista=v['id'], pt=[r1(x), r1(y)], fuente=fuente, leido=leido)

    for tag, c in sorted((lay.get('comp') or {}).items()):
        if not isinstance(c.get('x'), (int, float)) or not isinstance(c.get('y'), (int, float)):
            continue
        v = porid['fondo'] if c.get('ubic') == 'BANDEJA' else vista_de(pag_b, c['x'], c['y'])
        if v:
            poner(tag, v, c['x'], c['y'], 'topográfico (layout)', c.get('leido'))
    paginas = sorted({v['pag'] for v in V if v['zona'] != 'puerta_ext'} | ({vp['pag']} if vp else set()))
    for pag in paginas:
        try:
            hits = etiquetas_hoja(topo_pdf, pag - 1, textos(pag - 1), conocidos, dec)
        except Exception:
            hits = []
        # etiqueta cortada o con una letra sin leer, en la capa de etiquetas: 'BH-01' + el trozo pegado '-?' (la M no
        # esta en el diccionario de letras) = 'BH-01-' + UNA letra -> el unico tag conocido asi es BH-01-M (BH-01-ZV
        # tiene dos). Sin trozo pegado: el comienzo de UN solo tag conocido. ('?' = una letra cualquiera)
        lns = textos(pag - 1)
        sin_esp = {k: k.replace(' ', '') for k in conocidos}
        patron = lambda s: ''.join('.' if ch == '?' else re.escape(ch) for ch in s)
        for l in lns:
            t = l['text'].strip().replace(' ', '')
            if len(t) < 4 or not re.search(r'ETIQUETA', l.get('layer', ''), re.I) or not re.search(r'\d', t):
                continue
            if any(h['leido'] == l['text'] for h in hits):
                continue
            b = l['bbox']; h0 = b[3] - b[1]
            peg = sorted((m for m in lns if m is not l and l.get('ang', 0) == m.get('ang', 0) == 0 and abs(m['bbox'][1] - b[1]) < 0.3 * h0
                          and 0 <= m['bbox'][0] - b[2] < 0.8 * h0 and 0 < len(m['text'].strip()) <= 4), key=lambda m: m['bbox'][0])
            if peg:
                tt = t + peg[0]['text'].strip().replace(' ', '')
                rx = re.compile(patron(tt) + '$')
                cand = [k for k, s in sin_esp.items() if rx.match(s)]
                b = (b[0], min(b[1], peg[0]['bbox'][1]), peg[0]['bbox'][2], max(b[3], peg[0]['bbox'][3]))
                leido = l['text'].strip() + peg[0]['text'].strip()
            else:
                rx = re.compile(patron(t))
                cand = [k for k, s in sin_esp.items() if rx.match(s) and 0 < len(s) - len(t) <= 3]
                leido = l['text']
            if len(cand) == 1:
                hits.append(dict(tag=cand[0], leido=leido, x=(b[0] + b[2]) / 2, y=(b[1] + b[3]) / 2))
        for h in hits:
            v = vista_de(pag, h['x'], h['y'])
            if v:
                poner(h['tag'], v, h['x'], h['y'], f'etiqueta del topográfico (hoja {pag})', h['leido'])
    # cerradura -> las bisagras van del otro lado (sin cerradura en el dibujo: a la izquierda)
    bis = None
    if vp is not None:
        for l in textos(vp['pag'] - 1):
            b = l['bbox']; x, y = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if RX_CERRADURA.search(l['text']) and dentro(vp['box'], x, y):
                bis = 'der' if a3d(vp, x, y)[0] < ancho / 2 else 'izq'
                break
    if bis is None:
        supuestos.append('Bisagras de la puerta a la izquierda (no se vio la cerradura en la vista de la puerta).')
    G['bisagra'] = bis or 'izq'
    # altura del mazo que cruza a la puerta: la canaleta horizontal de la puerta (si esta entre las bisagras)
    y_mazo = alto * 0.5
    if vp is not None and vp.get('ductos'):
        hs = [d for d in vp['ductos'] if d.get('h')]
        if hs:
            d = max(hs, key=lambda d: d['b'][2] - d['b'][0])
            y = a3d(vp, d['b'][0], (d['b'][1] + d['b'][3]) / 2)[1]
            if 0.12 * alto <= y <= 0.88 * alto:
                y_mazo = y
    G['y_mazo'] = r1(y_mazo)
    _eje(M)
    # recuadros de aparatos SIN etiqueta en la puerta (ej. una placa electronica): para ubicar por descarte
    if vp is not None:
        e_pt = 1.0 / vp['esc']
        hits_p = [a['pt'] for a in A.values() if a['vista'] == vp['id']]
        cajas = []
        for r in hoja(vp['pag'] - 1)['rects']:
            x0, y0, x1, y1, capa = r
            w, h = x1 - x0, y1 - y0
            if RX_NO_CAJA.search(capa) or not dentro(vp['box'], (x0 + x1) / 2, (y0 + y1) / 2):
                continue
            if min(w, h) < 40 * e_pt or max(w, h) > 0.6 * (vp['box'][2] - vp['box'][0]) or max(w, h) > 3 * min(w, h):
                continue
            if any(dentro((x0, y0, x1, y1), p[0], p[1]) for p in hits_p):
                continue
            cajas.append((x0, y0, x1, y1))
        cajas = [c for c in cajas if not any(o != c and o[0] <= c[0] and o[1] <= c[1] and c[2] <= o[2] and c[3] <= o[3] for o in cajas)]
        M['recuadros_puerta'] = [[r1(v) for v in c] for c in sorted(cajas, key=lambda c: -(c[2] - c[0]) * (c[3] - c[1]))]
    M['resumen'] = dict(vistas=[v['id'] for v in V], aparatos_fuera_bandeja=sorted(t for t, a in A.items() if a['zona'] != 'bandeja'),
                        paginas_leidas=sorted(p + 1 for p in hojas))
    return M


def _eje(M):
    """eje de las bisagras (vertical) en el borde de afuera de la puerta"""
    G = M['gabinete']
    G.setdefault('bisagra', 'izq'); G.setdefault('y_mazo', r1(G['alto'] * 0.5))
    G['eje'] = dict(x=3.0 if G['bisagra'] == 'izq' else r1(G['ancho'] - 3.0), z=r1(G['prof'] + G['puerta']))


# ------------------------------------------------------------------ cables de E8
def tag_de(texto, conocidos):
    """aparato de una punta: el tag conocido con el que empieza el texto ('12XPS 2 ABAJO' -> 12XPS, 'PT 001 x1' ->
    PT 001), la tierra del gabinete, o el primer tag conocido que aparece ('malla del tramo 12XPS-81XCM' -> 12XPS)"""
    t = (texto or '').strip()
    if not t or t in ('LI', 'LD') or t.startswith('?'):     # ('? 1': aparato que el lector no reconocio)
        return None
    pre = [k for k in conocidos if t == k or t.startswith(k + ' ')]
    if pre:
        return max(pre, key=len)
    if RX_TIERRA.search(t):
        return TIERRA_TAG
    hits = []
    for k in conocidos:
        m = re.search(r'(?<![\w-])' + re.escape(k) + r'(?![\w])', t)
        if m:
            hits.append((m.start(), -len(k), k))
    if hits:
        return min(hits)[2]
    return t.split(' ')[0]


def _borne(tag, texto):
    """(numero, piso) del borne de la punta: '12XPS 2 ABAJO' -> (2, 'ABAJO'); '21PCB01 28' -> (28, None)"""
    rest = (texto or '')[len(tag):].strip() if tag and (texto or '').startswith(tag) else ''
    m = re.match(r'^(\d+)', rest)
    piso = re.search(r'\b(ARRIBA|ABAJO)$', rest)
    return (int(m.group(1)) if m else None, piso.group(1) if piso else None)


def clave_cable(num, de, a, b, origen=None):
    """clave ESTABLE de un cable de E8 para sus marcas: no depende de cual punta es 'desde' y cual 'hasta' (eso cambia
    si el usuario ubica o saca un aparato con 📍). Linea de E6: numero + su origen en la bandeja; pendiente u otra
    estacion: numero + el par ordenado de textos"""
    if origen is not None:
        return f'{num}|{origen}'
    return f'{num}|' + '|'.join(sorted([a or '', b or '']))


def _rango_fila(filas, n):
    """(fila, posicion 0..1 en la fila, n de filas) del pin n segun las filas del funcional [[min, max], ...]"""
    if not filas or n is None:
        return None
    r = next((i for i, (lo, hi) in enumerate(filas) if lo <= n <= hi), None)
    if r is None:
        r = min(range(len(filas)), key=lambda i: min(abs(n - filas[i][0]), abs(n - filas[i][1])))
    lo, hi = filas[r]
    return r, (min(max(n, lo), hi) - lo) / max(1, hi - lo), len(filas)


def armar_e8(ins, M, e8=None):
    """lista de cables de E8 desde instructivo.json (ins) y el modelo del gabinete (M), con lo del usuario (e8: marcas
    de cableado y ubicaciones a mano). -> dict(cables, grupos, aparatos, avisos, resumen, migrar)
    migrar = {clave vieja: clave nueva} de las marcas guardadas con la clave de antes (web.py las pasa al leer)"""
    from instructivo import FIELD_RE, is_terminal_block
    e8 = e8 or {}
    hechos = e8.get('hechos') or {}
    G = M['gabinete']
    V = {v['id']: v for v in M.get('vistas') or []}
    avisos = list(M.get('avisos') or [])
    comp_b = (ins.get('topo') or {}).get('comp') or {}
    filas_pin = ins.get('filas_pin') or {}
    conocidos = sorted({c.get('tag') for c in ins.get('componentes') or [] if c.get('tag')} | set(comp_b) | set(M.get('aparatos') or {}))
    # aparatos: los del topografico + los ubicados a mano en el visor (mandan)
    A = {t: dict(a) for t, a in (M.get('aparatos') or {}).items()}
    for t, u in (e8.get('ubicaciones') or {}).items():
        v = V.get(u.get('vista'))
        if v and isinstance(u.get('pt'), list) and len(u['pt']) == 2:
            zona = 'puerta' if v.get('en_puerta') else ('fondo' if v['zona'] in ('fondo', 'bandeja') else v['zona'])
            if t in comp_b and v['id'] == 'fondo':
                zona = 'bandeja'
            A[t] = dict(tag=t, zona=zona, vista=v['id'], pt=[r1(u['pt'][0]), r1(u['pt'][1])], fuente='ubicado a mano en el visor')

    # ---- 1) cables de E8 (sin ruta todavia)
    crudos = []
    sin_e8 = 0
    est_propia = ins.get('estacion') or 'E6'
    for p in ins.get('pasos') or []:
        for l in p.get('lineas') or []:
            if l.get('destino') not in ('LI', 'LD') or l.get('destino_campo'):
                continue          # (destino_campo: la otra punta es de campo, la conecta el cliente: no es de E8)
            if not l.get('destino_e8') and not l.get('agregado'):     # (un agregado a mano a 'LI' no tiene otra punta)
                sin_e8 += 1
            crudos.append(dict(de='linea', l=l, a=l.get('origen'), b=l.get('destino_e8') or l['destino'], salida=l['destino'],
                               e6_hecho=bool(l.get('hecho'))))
    for x in ins.get('pendientes') or []:
        if x.get('destino_campo'):
            continue
        crudos.append(dict(de='pendiente', l=x, a=x.get('a'), b=x.get('b')))
    for l in ins.get('otra_estacion') or []:
        est = l.get('estacion') or ''
        if est in (est_propia, 'CAMPO') or l.get('destino_campo'):
            continue
        if l.get('pendiente'):
            crudos.append(dict(de='otra', l=l, a=l.get('origen'), b=l.get('destino'), estacion=est))
        else:
            dest = l.get('destino_e8') or l.get('destino')
            if dest in ('LI', 'LD') and not l.get('destino_e8'):
                sin_e8 += 1
            crudos.append(dict(de='otra', l=l, a=l.get('origen'), b=dest, salida=l.get('destino') if l.get('destino') in ('LI', 'LD') else 'LI',
                               estacion=est))
    if sin_e8:
        avisos.insert(0, f'{sin_e8} cables «→ LI» sin la otra punta: este instructivo se armó con una versión anterior. '
                         'Tocá ↻ Regenerar (se conservan las marcas) para ver adónde va cada uno.')
    # clave estable de cada cable (antes de ordenar las puntas por zona)
    for c in crudos:
        de_e6 = c['de'] == 'linea' or (c['de'] == 'otra' and c.get('salida'))
        c['clave'] = clave_cable(c['l'].get('num'), c['de'], c['a'], c['b'], c['a'] if de_e6 else None)
    rep = collections.Counter(c['clave'] for c in crudos)
    for c in crudos:
        if rep[c['clave']] > 1:          # (dos tramos del mismo numero desde la misma punta de la bandeja)
            c['clave'] += f"|{c['b']}"

    # ---- 2) puntas: aparato, zona y punto
    fuera = collections.OrderedDict()            # tags sin vista: ('otro' | 'sin ubicar') -> orden de aparicion

    def base_b(tag):
        """tag de la bandeja: el mismo o el del grupo de modulos ('46KR2' -> '46KR')"""
        if tag in comp_b:
            return tag
        b = re.sub(r'\d+$', '', tag or '')
        return b if b in comp_b else None

    def zona_de(tag, txt, estacion=None):
        if base_b(tag):
            return 'bandeja'
        if tag in A:
            return A[tag]['zona']
        if tag == TIERRA_TAG:
            return 'fondo'
        if not tag or txt in ('LI', 'LD'):
            return 'sin ubicar'
        if FIELD_RE.match(tag) or estacion == 'CAMPO':
            return 'otro'               # zona hidraulica (bomba, valvulas, transmisor) sin ubicar en el topografico
        return 'sin ubicar'

    for c in crudos:
        for k in ('a', 'b'):
            t = c[k]
            tag = tag_de(t, conocidos)
            c[k + '_tag'] = tag
            c[k + '_zona'] = zona_de(tag, t, c.get('estacion'))
        if c['de'] == 'linea' or (c['de'] == 'otra' and c.get('salida')):
            c['a_zona'] = 'bandeja'          # la punta de la bandeja (ya cableada en E6)
    # aparato sin etiqueta en el topografico: el que mas cables de E8 tiene va al recuadro de aparato sin etiqueta de la
    # puerta, como 'a confirmar'. Solo si queda UN recuadro libre: sin el punto de otro aparato de la puerta adentro
    # (tambien los ubicados a mano: si el usuario ya puso la placa en ese recuadro, no se mete otro aparato ahi)
    cajas = list(M.get('recuadros_puerta') or [])
    if cajas and 'puerta' in V:
        ocupados = [a['pt'] for a in A.values() if a.get('vista') == 'puerta' and isinstance(a.get('pt'), list)]
        libres = [b for b in cajas if not any(b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3] for p in ocupados)]
        cuenta = collections.Counter(c[k + '_tag'] for c in crudos for k in ('a', 'b') if c[k + '_zona'] == 'sin ubicar'
                                     and c[k + '_tag'] and c[k + '_tag'] not in ('LI', 'LD') and not is_terminal_block(c[k + '_tag']))
        if len(libres) == 1 and cuenta:
            tag = cuenta.most_common(1)[0][0]
            b = libres[0]
            A[tag] = dict(tag=tag, zona='puerta', vista='puerta', pt=[r1((b[0] + b[2]) / 2), r1((b[1] + b[3]) / 2)], caja=b,
                          fuente='deducido: recuadro de aparato sin etiqueta en la puerta', a_confirmar=True)
            for c in crudos:
                for k in ('a', 'b'):
                    if c[k + '_tag'] == tag:
                        c[k + '_zona'] = 'puerta'
    # desde = la punta que ya esta (bandeja) o la de la zona de mas abajo en el orden; hasta = la que se conecta en E8
    for c in crudos:
        if c['de'] != 'linea' and not (c['de'] == 'otra' and c.get('salida')) and RANGO[c['b_zona']] < RANGO[c['a_zona']]:
            for s in ('', '_tag', '_zona'):
                c['a' + s], c['b' + s] = c['b' + s], c['a' + s]
    for c in crudos:
        for k in ('a', 'b'):
            if c[k + '_zona'] in ('otro', 'sin ubicar'):
                fuera.setdefault((c[k + '_zona'], c[k + '_tag'] or c[k]), None)
    # lugares de lo que no esta en ninguna vista. Zona hidraulica ('otro'): ADENTRO, en la pared del fondo abajo, junto al
    # aparato ubicado del mismo equipo ('BH-01-ZV', el contactor, junto al motor 'BH-01-M') o junto a lo que ya esta
    # ubicado de la zona hidraulica; si no hay nada, abajo a la derecha. 'sin ubicar': arriba del gabinete (para
    # ubicarlo a mano con el visor), en filas a lo ancho
    lugar = {}
    n_s = 0
    por_fila = max(2, int(G['ancho'] // 270))
    z_f = Z_FONDO + H_APARATO['fondo']
    p3 = lambda a: a3d(V[a['vista']], a['pt'][0], a['pt'][1], H_APARATO[ZONA_BASE.get(a['zona'], 'fondo')]) if a.get('vista') in V else None
    hidr = {t: p3(a) for t, a in A.items() if FIELD_RE.match(t) and p3(a)}
    equipo = lambda t: (re.match(r'^([A-Z]{2,3}[ -]?\d{1,3})', t or '') or [None])[0]
    junto = collections.Counter()
    x_min, x_max = LATERAL + 60, G['ancho'] - LATERAL - 60
    for (z, t) in fuera:
        if z == 'otro':
            her = [p for tt, p in hidr.items() if equipo(tt) and equipo(tt) == equipo(t)]
            if her:
                base = her[0]; k = junto[('e', equipo(t))]; junto[('e', equipo(t))] += 1
                p = [base[0] - 25 * k, base[1] - 70 * (k + 1), base[2]]
            elif hidr:
                xs = [p[0] for p in hidr.values()]; ys = [p[1] for p in hidr.values()]
                k = junto['g']; junto['g'] += 1
                p = [min(xs) - 110 * (k + 1), min(ys), z_f]
                if p[0] < x_min:
                    p = [max(xs) + 110 * (k + 1), min(ys), z_f]
            else:
                k = junto['f']; junto['f'] += 1
                p = [x_max - 110 * k, 90.0, z_f]
            lugar[t] = [r1(min(max(p[0], x_min), x_max)), r1(min(max(p[1], 50.0), G['alto'] - 50)), r1(p[2])]
        else:
            lugar[t] = [r1(70 + 270 * (n_s % por_fila)), r1(G['alto'] + 110 + 60 * (n_s // por_fila)), r1(G['prof'] * 0.5)]; n_s += 1

    def punta(txt, tag, zona, l=None, primera=False):
        """-> dict(texto, tag, zona, vista, P (hoja), p (3D), aprox, fuente)"""
        out = dict(texto=txt, tag=tag, zona=zona)
        if zona == 'bandeja' and 'fondo' not in V:      # (topografico sin bandeja leida: al medio del fondo)
            return dict(out, vista=None, P=None, p=[r1(G['ancho'] / 2), r1(G['alto'] / 2), Z_FONDO + H_APARATO['fondo']], aprox=True,
                        fuente='sin bandeja en el topográfico')
        if zona == 'bandeja' and primera and l is not None and l.get('marca_o'):
            v = V.get('fondo')
            X, Y = l['marca_o'][0], l['marca_o'][1]
            return dict(out, vista='fondo', P=[X, Y], p=a3d(v, X, Y, H_APARATO['fondo']), aprox=not l.get('exacto_o'),
                        fuente='punto del borne (instructivo E6)')
        a = A.get(tag)
        if zona == 'bandeja' and not a and base_b(tag):
            cb = comp_b[base_b(tag)]
            a = dict(vista='fondo', pt=[cb['x'], cb['y']], fuente='topográfico (layout)')
        if tag == TIERRA_TAG and not a:
            vl = V.get('lateral_izquierda')
            p = [LATERAL + 15, 70.0, 60.0] if vl else [60.0, 70.0, Z_FONDO + 15]
            return dict(out, vista=None, P=None, p=p, aprox=True, fuente='supuesto: bulón de tierra abajo a la izquierda')
        if not a or a.get('vista') not in V:
            return dict(out, vista=None, P=None, p=lugar.get(tag or txt, [-170.0, 100.0, 200.0]), aprox=True,
                        fuente='lugar aproximado: adentro, abajo, junto a lo ubicado de la zona hidráulica' if zona == 'otro' else 'sin ubicar en el topográfico')
        v = V[a['vista']]
        X, Y = a['pt']
        n, piso = _borne(tag, txt)
        e = 1.0 / v['esc']
        # (la puerta por dentro: la hoja YA es la vista desde adentro y a3d la espeja; el borne n crece hacia la derecha
        # de la hoja igual que en las otras vistas)
        fr = _rango_fila(filas_pin.get(tag), n)
        if a.get('caja'):
            b = a['caja']
            if n and fr:          # filas de pines del funcional (21PCB01: abajo 1-37, arriba 38-69)
                r, pos, nf = fr
                X = b[0] + (0.06 + 0.88 * pos) * (b[2] - b[0])
                Y = b[1] + (0.12 + (0.76 * r / (nf - 1) if nf > 1 else 0)) * (b[3] - b[1])
            elif n:
                X = b[0] + (0.06 + 0.88 * ((n - 1) % 40) / 39) * (b[2] - b[0])
                Y = b[1] + (0.12 + 0.12 * (((n - 1) // 40) % 4)) * (b[3] - b[1])
        elif n is not None and is_terminal_block(tag):
            X += min(n, 12) * PASO_BORNE * e
            if piso:
                Y += (DY_PISO if piso == 'ARRIBA' else -DY_PISO) * e
        elif n is not None and fr:
            r, pos, nf = fr
            X += (pos - 0.5) * 36.0 * e
            Y += (r - (nf - 1) / 2) * 12.0 * e
        elif n is not None:
            X += (((n - 1) % 10) - 4.5) * 4.0 * e
            Y -= (((n - 1) // 10) % 4) * 6.0 * e
        base = ZONA_BASE.get(zona, 'fondo')
        return dict(out, vista=v['id'], P=[r1(X), r1(Y)], p=a3d(v, X, Y, H_APARATO[base]), aprox=True,
                    fuente=a.get('fuente'), a_confirmar=bool(a.get('a_confirmar')))

    cables = []
    migrar = {}
    for c in crudos:
        l = c['l']
        A_ = punta(c['a'], c['a_tag'], c['a_zona'], l, primera=c['de'] == 'linea' or (c['de'] == 'otra' and bool(c.get('salida'))))
        B_ = punta(c['b'], c['b_tag'], c['b_zona'])
        num = l.get('num')
        clave = c['clave']
        # marca guardada con la clave de antes ('num|desde|hasta', en cualquier orden): vale y se pasa a la nueva
        h = hechos.get(clave)
        if h is None:
            for vieja in (f"{num}|{c['a']}|{c['b']}", f"{num}|{c['b']}|{c['a']}"):
                if vieja != clave and vieja in hechos:
                    h = hechos[vieja]; migrar[vieja] = clave
                    break
        tramos = _recorrido(c, l, A_, B_, M, V)
        av = []
        if B_['zona'] == 'sin ubicar' and c['b'] in ('LI', 'LD'):
            av.append('agregado a mano sin la otra punta: mirá la nota' if l.get('agregado') else 'sin la otra punta (regenerá el instructivo)')
        elif B_['zona'] == 'sin ubicar' and (c['b'] or '').startswith('?'):
            av.append('el programa no leyó este aparato en el funcional: mirá el plano')
        elif B_['zona'] == 'sin ubicar' or A_['zona'] == 'sin ubicar':
            av.append('aparato sin ubicar en el topográfico: ubicalo con 📍')
        elif 'otro' in (A_['zona'], B_['zona']):
            av.append('zona hidráulica: el topográfico no ubica este aparato (está abajo, adentro): ubicalo con 📍')
        if A_.get('a_confirmar') or B_.get('a_confirmar'):
            av.append('aparato ubicado por descarte: confirmalo (📍 para corregir)')
        if l.get('destino_e8_de') == 'funcional':
            av.append('la otra punta sale del funcional (el cable es un agregado a mano a «LI»): confirmala')
        cables.append(dict(id=clave, num=num, cable=l.get('cable', ''), color=l.get('color', ''), secc=l.get('secc', ''),
                           de=c['de'], estacion=c.get('estacion'), desde=A_, hasta=B_, tramos=tramos,
                           hecho=bool((h or {}).get('hecho')), e6_hecho=bool(c.get('e6_hecho')),
                           avisos=av, **{k: l[k] for k in ('agregado', 'alternativa') if l.get(k)}))
    # ---- 3) orden: primero lo que queda abajo (los dos extremos en el lateral), despues la puerta (cortos), lo que va a
    # la puerta por la bisagra (de la bandeja y de los laterales, en mazo), de la bandeja a los laterales y al final la
    # zona hidraulica, el fondo y los de 35 mm2
    def grupo(c):
        za, zb = c['desde']['zona'], c['hasta']['zona']
        if za == zb and za.startswith('lateral'):
            return 'lat-lat'
        if za == zb == 'puerta':
            return 'pue-pue'
        if za in ('bandeja', 'lateral izq', 'lateral der') and zb == 'puerta':
            return 'a-pue'
        if za == 'bandeja' and zb.startswith('lateral'):
            return 'ban-lat'
        if 'sin ubicar' in (za, zb):
            return 'sin'
        return 'otro'
    GR = [('lat-lat', 'Laterales: cables con las dos puntas en el lateral',
           'Quedan debajo de todo lo que llega después desde la bandeja y la puerta.'),
          ('pue-pue', 'Puerta: cables con las dos puntas en la puerta', 'Cortos, dentro de la puerta.'),
          ('a-pue', 'A la puerta por la bisagra (de la bandeja y de los laterales)',
           'En mazo: por el lateral hasta la bisagra, la cruzan y entran a la canaleta de la puerta. Aparato por aparato '
           '(el de más cables primero); en cada uno, la fila de abajo y después la de arriba (los de arriba pasan por delante).'),
          ('ban-lat', 'De la bandeja a los laterales', 'Salen por la salida LI de la bandeja y van por las canaletas del lateral.'),
          ('otro', 'Fondo, zona hidráulica y 35 mm²', 'Lo que va a la zona hidráulica (abajo), al piso y los de 35 mm² al final.'),
          ('sin', 'Con un aparato sin ubicar', 'Ubicá el aparato con 📍 (o regenerá el instructivo si falta la otra punta).')]
    orden_g = {g: i for i, (g, _, _) in enumerate(GR)}
    from instructivo import natk
    for c in cables:
        c['grupo'] = grupo(c)
    n_ap = collections.Counter(c['hasta']['tag'] for c in cables if c['grupo'] == 'a-pue')

    def secc(c):
        try:
            return float(str(c.get('secc') or 0).replace(',', '.'))
        except ValueError:
            return 0.0

    def orden(c):
        t = c['hasta']['tag'] or c['hasta']['texto'] or ''
        n, _ = _borne(c['hasta']['tag'], c['hasta']['texto'])
        fr = _rango_fila(filas_pin.get(c['hasta']['tag']), n)
        k = (orden_g[c['grupo']],)
        if c['grupo'] == 'a-pue':
            k += (-n_ap[c['hasta']['tag']], natk(t), fr[0] if fr else 0, n if n is not None else 0)
        elif c['grupo'] == 'otro':
            k += (secc(c) >= 35, natk(t))
        else:
            k += (natk(t),)
        return k + (natk(c['hasta']['texto'] or ''), natk(c['num'] or ''))
    cables.sort(key=orden)
    for i, c in enumerate(cables, 1):
        c['n'] = i
    grupos = [dict(id=g, titulo=t, por_que=p, n=sum(1 for c in cables if c['grupo'] == g)) for g, t, p in GR]
    grupos = [g for g in grupos if g['n']]
    # aparatos para el visor (etiquetas): los de afuera de la bandeja y los que tocan algun cable de E8
    usados = {c[k]['tag'] for c in cables for k in ('desde', 'hasta') if c[k]['tag']}
    ap = []
    for t, a in sorted(A.items()):
        if a['zona'] == 'bandeja' and t not in usados:
            continue
        v = V.get(a['vista'])
        if not v:
            continue
        ap.append(dict(tag=t, zona=a['zona'], vista=a['vista'], pt=a['pt'], fuente=a.get('fuente'), a_confirmar=bool(a.get('a_confirmar')),
                       p=a3d(v, a['pt'][0], a['pt'][1], H_APARATO[ZONA_BASE.get(a['zona'], 'fondo')] + 12),
                       en_puerta=bool(v.get('en_puerta')), caja=a.get('caja'), hidraulica=bool(FIELD_RE.match(t))))
    for t, p in lugar.items():
        z = next((zz for (zz, tt) in fuera if tt == t), 'sin ubicar')
        ap.append(dict(tag=t, zona=z, vista=None, pt=None, p=p, en_puerta=False, hidraulica=z == 'otro',
                       fuente='lugar aproximado: adentro, abajo, junto a lo ubicado de la zona hidráulica' if z == 'otro' else 'sin ubicar en el topográfico'))
    puntas_fuera = [(c, c[k]) for c in cables for k in ('desde', 'hasta') if c[k]['zona'] == 'sin ubicar']
    res = dict(total=len(cables), hechos=sum(1 for c in cables if c['hecho']),
               por_grupo={g['id']: g['n'] for g in grupos},
               por_lista=dict(collections.Counter(c['de'] for c in cables)),
               sin_ubicar=sorted({p['tag'] for c, p in puntas_fuera if p['tag']}),
               hidraulica_sin_ubicar=sorted(t for (z, t) in fuera if z == 'otro'),
               no_leidos=sum(1 for c, p in puntas_fuera if (p['texto'] or '').startswith('?')),
               sin_otra_punta=sum(1 for c, p in puntas_fuera if p['texto'] in ('LI', 'LD')))
    if res['sin_ubicar']:
        avisos.append('Sin ubicar en el topográfico: ' + ', '.join(res['sin_ubicar']) + '. Ubicalos con 📍 (elegí el aparato y '
                      'hacé clic en su lugar en la placa, el lateral o la puerta).')
    if res['hidraulica_sin_ubicar']:
        avisos.append('Zona hidráulica sin ubicar en el topográfico: ' + ', '.join(res['hidraulica_sin_ubicar']) + '. Se dibujan '
                      'adentro, abajo, junto a lo que sí está ubicado; corregilos con 📍.')
    if res['no_leidos']:
        avisos.append(f'{res["no_leidos"]} cables van a un aparato que el lector no reconoció en el funcional («?»): mirá el plano.')
    if res['sin_otra_punta'] and not sin_e8:
        avisos.append(f'{res["sin_otra_punta"]} cables agregados a mano a «LI» (correcciones del trabajo) no tienen la otra punta: mirá su nota.')
    return dict(cables=cables, grupos=grupos, aparatos=ap, avisos=avisos, resumen=res, migrar=migrar)


# ------------------------------------------------------------------ recorrido de cada cable (simple)
def _ruta_vista(v, P, Q, ex=False):
    """P -> Q por las canaletas de la vista v (ruteo.Net); sin canaletas, en L"""
    dl = v.get('ductos') or []
    if dl:
        from ruteo import Net, length
        best = None
        for sp in (0, 1):
            for sq in (0, 1):
                try:
                    net = Net([dict(d) for d in dl])
                    a, va = net.enganche(tuple(P), sp, None)
                    b, vb = net.enganche(tuple(Q), sq, None)
                    mid = net.path(a, b, ex) if a is not None and b is not None else None
                except Exception:
                    mid = None
                if mid is None:
                    continue
                pts = [tuple(P)] + list(va) + list(mid) + list(vb)[::-1] + [tuple(Q)]
                L = length(pts)
                if best is None or L < best[0]:
                    best = (L, pts)
        if best:
            return best[1]
    return [tuple(P), (Q[0], P[1]), tuple(Q)]


def _en3d(v, pts, base, extremos=(True, True)):
    """polilinea de la hoja -> 3D: por adentro de las canaletas; las puntas que son bornes, a la altura del aparato"""
    out = []
    for i, (X, Y) in enumerate(pts):
        es_borne = (i == 0 and extremos[0]) or (i == len(pts) - 1 and extremos[1])
        out.append(a3d(v, X, Y, H_APARATO[base] if es_borne else H_CANAL[base]))
    return out


def _limpiar(pts):
    out = []
    for p in pts:
        if not out or math.dist(out[-1], p) > 0.5:
            out.append([r1(c) for c in p])
    return out


def _recorrido(c, l, A_, B_, M, V):
    """tramos 3D del cable: [dict(pts, tipo)] con tipo 'e6' (lo que ya se cableo en la bandeja), 'e8' (en el cuerpo) o
    'puerta' (en la puerta: gira con ella; empieza en el eje de las bisagras, que no se mueve)"""
    G = M['gabinete']
    ex = (c['l'].get('color') == 'Azul')
    tramos = []
    vf = V.get('fondo')
    lat = {('lateral izq' if k == 'lateral_izquierda' else 'lateral der'): v for k, v in V.items() if k.startswith('lateral_')}
    vpu = V.get('puerta')
    izq_b = G.get('bisagra', 'izq') == 'izq'
    lado_b = 'lateral izq' if izq_b else 'lateral der'
    eje = [G['eje']['x'], G['y_mazo'], G['eje']['z']]
    z_pi = G['prof'] + G['puerta'] - CHAPA

    def zbase(z):
        return 'fondo' if z in ('bandeja', 'fondo') else z

    # puntas: la de la puerta va al final (se arma de la otra hacia la puerta)
    a, b = A_, B_
    al_reves = a['zona'] == 'puerta' and b['zona'] != 'puerta'
    if al_reves:
        a, b = b, a
    cuerpo = []          # puntos 3D en el cuerpo (puerta cerrada)
    # 1) arranque: el tramo de la bandeja (E6) hasta la salida LI, o el aparato
    ruta = l.get('ruta') if not al_reves and c['de'] in ('linea', 'otra') and c.get('salida') and a['zona'] == 'bandeja' else None
    if ruta and vf and len(ruta) >= 2:
        e6 = _en3d(vf, ruta, 'fondo', (True, False))
        tramos.append(dict(pts=_limpiar(e6), tipo='e6'))
        cur = dict(zona='fondo', vista='fondo', P=list(ruta[-1]), p=e6[-1], borne=False)
        lado_sal = 'lateral der' if c.get('salida') == 'LD' else 'lateral izq'
    else:
        cur = dict(zona=zbase(a['zona']), vista=a.get('vista'), P=a.get('P'), p=a['p'], borne=True)
        lado_sal = a['zona'] if a['zona'].startswith('lateral') else lado_b
    cuerpo.append(cur['p'])

    def ir_al_lateral(zl, y):
        """del fondo (cur) a la entrada del lateral zl por atras, a la altura y -> punto en la hoja del lateral"""
        v = lat.get(zl)
        x_l = (LATERAL if zl == 'lateral izq' else G['ancho'] - LATERAL)
        x_l += H_CANAL['lateral'] if zl == 'lateral izq' else -H_CANAL['lateral']
        p = [x_l, y, Z_FONDO + 30]
        cuerpo.append(p)
        return (v, a_hoja(v, p)) if v else (None, p)

    def por_lateral(zl, P0, destino3, P1=None, borne_fin=False):
        """por el lateral zl desde P0 (hoja) hasta P1 (hoja) o destino3 (3D)"""
        v = lat.get(zl)
        if v is None:
            cuerpo.append(destino3)
            return
        P1 = P1 or a_hoja(v, destino3)
        pts = _ruta_vista(v, P0, P1, ex)
        cuerpo.extend(_en3d(v, pts, 'lateral', (False, borne_fin))[1:])

    zb = zbase(b['zona'])
    if zb == 'puerta' and cur['zona'] != 'puerta':
        # al frente del lateral de las bisagras, a la altura del mazo, y a la puerta por el eje
        frente = [(LATERAL + H_CANAL['lateral']) if izq_b else (G['ancho'] - LATERAL - H_CANAL['lateral']), G['y_mazo'], G['prof'] - 25]
        if cur['zona'] == 'fondo':
            vl, P0 = ir_al_lateral(lado_b, cur['p'][1])
            por_lateral(lado_b, P0, frente) if vl else cuerpo.append(frente)
        elif cur['zona'] == lado_b and lat.get(lado_b) and cur.get('P'):
            por_lateral(lado_b, cur['P'], frente)
        else:
            # del otro lateral o de afuera: por arriba, hasta el frente del lateral de las bisagras
            q = cur['p']
            cuerpo.extend([[q[0], q[1], G['prof'] - 40], [q[0], G['alto'] - 70, G['prof'] - 40],
                           [frente[0], G['alto'] - 70, G['prof'] - 40], frente])
        cuerpo.append(eje)
        tramos.append(dict(pts=_limpiar(cuerpo), tipo='e8'))
        # en la puerta: del eje a la canaleta (entrada del lado de las bisagras) y por ella al aparato
        ent = [LATERAL if izq_b else G['ancho'] - LATERAL, G['y_mazo'], z_pi - H_CANAL['puerta']]
        pu = [eje, ent]
        if vpu and b.get('P'):
            pts = _ruta_vista(vpu, a_hoja(vpu, ent), b['P'], ex)
            pu.extend(_en3d(vpu, pts, 'puerta', (False, True))[1:])
        else:
            pu.append(b['p'])
        tramos.append(dict(pts=_limpiar(pu), tipo='puerta'))
    elif zb == 'puerta' and cur['zona'] == 'puerta':
        if vpu and cur.get('P') and b.get('P'):
            pts = _ruta_vista(vpu, cur['P'], b['P'], ex)
            tramos.append(dict(pts=_limpiar(_en3d(vpu, pts, 'puerta')), tipo='puerta'))
        else:
            tramos.append(dict(pts=_limpiar([cur['p'], b['p']]), tipo='puerta'))
        cuerpo = []
    elif zb.startswith('lateral') and lat.get(zb) and b.get('P'):
        if cur['zona'] == zb and cur.get('P'):
            pts = _ruta_vista(lat[zb], cur['P'], b['P'], ex)
            cuerpo.extend(_en3d(lat[zb], pts, 'lateral', (True, True))[1:])
        elif cur['zona'] == 'fondo':
            vl, P0 = ir_al_lateral(zb, cur['p'][1])
            por_lateral(zb, P0, b['p'], b['P'], borne_fin=True)
        else:
            q = cur['p']
            cuerpo.extend([[q[0], q[1], G['prof'] - 40], [q[0], G['alto'] - 70, G['prof'] - 40],
                           [b['p'][0], G['alto'] - 70, G['prof'] - 40], b['p']])
    elif zb == 'fondo' and cur['zona'] == 'fondo' and a['zona'] == 'bandeja' and b['zona'] == 'bandeja' and vf and cur.get('P') and b.get('P'):
        pts = _ruta_vista(vf, cur['P'], b['P'], ex)
        cuerpo.extend(_en3d(vf, pts, 'fondo')[1:])
    else:
        # a lo que esta en el fondo fuera de los rieles, en el piso o afuera: por el rincon del lateral de la salida, hasta
        # abajo, y derecho al aparato
        q, t = cur['p'], b['p']
        if cur['zona'].startswith('lateral') and lat.get(cur['zona']) and cur.get('P'):
            # del aparato del lateral hasta su borde de atras, a la misma altura
            atras = [q[0], q[1], Z_FONDO + 30]
            por_lateral(cur['zona'], cur['P'], atras)
            q = cuerpo[-1]
        y_b = max(40.0, min(q[1], t[1])) if t[1] > 0 else 40.0
        x_c = G['ancho'] - LATERAL - 30 if lado_sal == 'lateral der' else LATERAL + 30
        if t[1] > G['alto']:  # sin ubicar: arriba del gabinete, por el techo
            y_t = G['alto'] - 50
            cuerpo.extend([[x_c, q[1], q[2]], [x_c, y_t, q[2]], [t[0], y_t, q[2]], [t[0], G['alto'], t[2]], t])
        elif t[1] < 0:        # afuera por el piso (zona hidraulica / campo)
            cuerpo.extend([[x_c, q[1], q[2]], [x_c, y_b, q[2]], [t[0], y_b, q[2]], [t[0], 0.0, t[2]], t])
        else:
            cuerpo.extend([[x_c, q[1], q[2]], [x_c, y_b, q[2]]])
            cuerpo.extend([[t[0], y_b, q[2]], [t[0], t[1], q[2]], t])
    if cuerpo and len(cuerpo) >= 2 and not (tramos and tramos[-1]['tipo'] in ('e8', 'puerta') and zb == 'puerta'):
        tramos.append(dict(pts=_limpiar(cuerpo), tipo='e8'))
    if al_reves:
        tramos = [dict(t, pts=t['pts'][::-1]) for t in tramos[::-1]]
    return [t for t in tramos if len(t['pts']) >= 2]


# ------------------------------------------------------------------ uso suelto
if __name__ == '__main__':
    import sys, time
    sys.stdout.reconfigure(encoding='utf-8')
    d = sys.argv[1]
    t0 = time.time()
    lay = json.load(open(os.path.join(d, 'layout.json'), encoding='utf-8'))
    ins = json.load(open(os.path.join(d, 'instructivo.json'), encoding='utf-8'))
    topo_pdf = os.path.join(d, 'topografico.pdf')
    if not os.path.exists(topo_pdf):
        est = json.load(open(os.path.join(d, 'estado.json'), encoding='utf-8'))
        topo_pdf = os.path.join(d, est['archivo'])
    M = leer_gabinete(topo_pdf, lay, [c.get('tag') for c in ins.get('componentes') or []], log=lambda m: print(' ', m))
    t1 = time.time()
    E = armar_e8(ins, M, ins.get('e8'))
    print(f'gabinete {M["gabinete"]} ({t1 - t0:.1f} s), {len(E["cables"])} cables E8 ({time.time() - t1:.2f} s)')
    print('vistas', [(v['id'], v['pag'], v['box']) for v in M['vistas']])
    print('aparatos fuera de la bandeja', {t: (a['zona'], a['vista']) for t, a in M['aparatos'].items() if a['zona'] != 'bandeja'})
    print('grupos', [(g['id'], g['n']) for g in E['grupos']])
    for a in E['avisos']:
        print('AVISO', a)
    if len(sys.argv) > 2:
        json.dump(dict(modelo=M, e8=E), open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
