"""Instructivo de cableado: origen -> destino de cada conductor, ordenado segun la aparamenta
de la bandeja (plano topografico).

Reglas del taller (ver LEEME):
  - Bornes de 4 puntos (PT QUATTRO): 'N.p' (p = 1..4; 1 y 2 arriba, 3 y 4 abajo).
  - Bornes de 2 puntos / doble piso: 'N ARRIBA' / 'N ABAJO'.
  - En el funcional, borne en vertical = igual que en la bandeja; en horizontal, izquierda = arriba.
  - Fuera de la bandeja se escribe 'LI' (lateral izquierdo; lo de la puerta tambien pasa por LI).
  - Cables con los dos extremos fuera de la bandeja: pendientes (se cablean al montar la bandeja).
  - Un numero con 3 o mas puntas = puente/derivacion: la union se hace en el borne mas cercano.
"""
import math, re, collections

from textdec import bbox

TAG_RE = re.compile(r'(?<![A-Z0-9])(?!\d+V(?:DC|AC|CC)?(?![A-Z0-9]))(\d{2}[A-Z][A-Z0-9]{1,7}|X[A-Z]{0,2}\d{1,2})(?![A-Z0-9])')
# referencia a otra hoja: '(Sh13:D5)', '(Sh15:B2/D2/E2)' (una flecha que va a varias zonas), '(Sh: 61:E4)'
SHREF_RE = re.compile(r'\(\s*Sh\s*:?\s*(\d+)[A-Z]?\s*[:;.]\s*([A-F]\d)(?:\s*/\s*[A-F]\d)*\s*\)', re.I)
# equipos de campo con tag de planta: 'BH-01-ZV', 'BH-01-M', 'PT 001' / 'PT-001' (numero de lazo con 0 adelante),
# valvula 'ZY(N/C)' / 'ZY(N/O)' (la fuente SHX dibuja la O y el 0 con el mismo trazo: 'ZY(N/0)')
FIELD_RE = re.compile(r'^(?:[A-Z]{2}-\d{2}(?:-[A-Z]{1,2})?|[A-Z]{2,3}[ -]0\d{2}|[A-Z]{2,3}\s?\(N\s?/\s?[CO0]\))$')
ISA_ESTADO_RE = re.compile(r'\s?\(N\s?/\s?[CO0]\)$')   # 'ZY(N/C)' -> tag 'ZY' (el estado del contacto no es parte del tag)
# rotulos de borne; ademas de los numeros y '+Vo': los que llevan el signo al final ('V+', 'V-', 'D1+', 'D1-' del MOXA)
LABEL_RE = re.compile(r'^([+-]|\d{1,3}|[A-Z]\d{1,2}|N|L|PE|F\d?|[+-]V[a-zA-Z]{0,3}\d?|\([+-]\)|[A-Z]{1,2}\(\d{1,2}\)?|L-\d|N-\d|\d{1,3}\s*\([+-]\)|[A-Z]\d?[+-])$')
# hoja o franja de una hoja que es una ALTERNATIVA del mismo circuito ('ALTERNATIVA 1', 'ALTERNATIVE 2'; la SHX
# puede leer la I como l o 1: 'ALTERNATlVA 1')
ALT_RE = re.compile(r'\bALTERNAT[I1l]V[AE]\s*(\d{1,2})\b', re.I)
COLOR_INI = {'Negro': 'N', 'Rojo': 'R', 'Blanco': 'B', 'Marrón': 'M', 'Azul': 'A', 'Gris': 'G', 'Verde': 'V',
             'Amarillo': 'AM', 'Verde-Amarillo': 'VA', 'Naranja': 'NA', 'Violeta': 'VI', 'Celeste': 'C', 'Rosa': 'RS'}


def is_terminal_block(tag):
    """borneras: letra X tras el prefijo numerico (13XC1, 13X24, 43XCS, 62XDO, 12XPS...)"""
    return bool(re.match(r'^(\d{2})?X', tag or ''))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def box_dist(p, b):
    return math.hypot(max(b[0] - p[0], 0, p[0] - b[2]), max(b[1] - p[1], 0, p[1] - b[3]))


# ------------------------------------------------------------------ simbolos geometricos
class Symbols:
    """circulos (bornes), triangulos (flechas a otra hoja) y rectangulos pequenos de una hoja"""
    def __init__(self, strokes, text_ids=(), u=1.0, pw=2383.4, ph=1683.4):
        self.circles, self.tris, self.rects, self.boxes = [], [], [], []
        self.rounds = []   # circulos mas grandes que un borne (polo de una bateria, pin redondo de un aparato)
        self._strokes = strokes; self.u = u; self.sym_ids = set(); self._by_id = {id(p): p for _, _, p in strokes}
        cmin, cmax = 4.5 * u, max(8.5 * u, 8.5)
        for layer, op, p in strokes:
            if len(p) < 4:
                continue
            if id(p) in text_ids:
                continue          # la 'o' de un texto no es un borne
            closed = dist(p[0], p[-1]) < 0.4
            x0, y0, x1, y1 = bbox(p); w, h = x1 - x0, y1 - y0
            if closed and len(p) >= 8 and cmin <= w <= cmax and abs(w - h) < 0.6 and op in ('S', 's'):
                self.circles.append(((x0 + x1) / 2, (y0 + y1) / 2, w / 2)); self.sym_ids.add(id(p))
            elif closed and len(p) >= 8 and cmax < w <= 2 * cmax and abs(w - h) < 0.6 and op in ('S', 's'):
                self.rounds.append(((x0 + x1) / 2, (y0 + y1) / 2, w / 2))
            elif closed and len(p) >= 8 and w < cmin and abs(w - h) < 0.3:
                self.sym_ids.add(id(p))          # punto de union (circulito chico) leido como '0' / '.'
            elif closed and len(p) == 4 and 4 * u <= max(w, h) <= 16 * u:
                self.tris.append((x0, y0, x1, y1)); self.sym_ids.add(id(p))
            elif closed and len(p) == 5 and 3 * u <= w <= 25 * u and 3 * u <= h <= 25 * u:
                self.rects.append((x0, y0, x1, y1)); self.sym_ids.add(id(p))
            if closed and len(p) == 5 and 20 * u < max(w, h) and w * h < 0.5 * pw * ph and min(w, h) > 12 * u:
                self.boxes.append((x0, y0, x1, y1))
                if max(w, h) < 45 * u:
                    self.sym_ids.add(id(p))

        self.tris += self._dashed_tris(strokes, u)

    @staticmethod
    def _dashed_tris(strokes, u):
        """flecha dibujada en linea discontinua (derivacion opcional, 66817 hoja 21: 8101/8102 hacia 81XCM): rayas rectas
        cortas de una misma capa, unidas punta con punta, cuyas puntas caen todas sobre el contorno de un triangulo
        isosceles del tamano de las flechas llenas (base horizontal o vertical, vertice en el medio del lado opuesto)"""
        rayas = [(layer, p) for layer, op, p in strokes if op in ('S', 's') and len(p) == 2 and 0.3 < dist(p[0], p[1]) < 6 * u]
        if len(rayas) < 4:
            return []
        par = list(range(len(rayas)))
        def f(i):
            while par[i] != i:
                par[i] = par[par[i]]; i = par[i]
            return i
        C = 8 * u; grid = collections.defaultdict(list)
        for i, (_, p) in enumerate(rayas):
            for q in p:
                grid[(int(q[0] // C), int(q[1] // C))].append(i)
        for i, (layer, p) in enumerate(rayas):
            for q in p:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for j in grid.get((int(q[0] // C) + dx, int(q[1] // C) + dy), []):
                            if j > i and rayas[j][0] == layer and min(dist(q, r) for r in rayas[j][1]) < 1.3 * max(dist(*p), dist(*rayas[j][1])):
                                par[f(i)] = f(j)
        grupos = collections.defaultdict(list)
        for i in range(len(rayas)):
            grupos[f(i)].append(rayas[i][1])
        out = []
        for g in grupos.values():
            if len(g) < 4:
                continue
            # los dos lados inclinados (pendientes de signo contrario) dan el triangulo; una esquina de un recuadro
            # discontinuo no tiene diagonales, y las rayas del cable que llega a la base quedan afuera
            diag = [p for p in g if 0.3 < abs(p[1][0] - p[0][0]) / dist(p[0], p[1]) < 0.95]
            if len({(p[1][0] - p[0][0]) * (p[1][1] - p[0][1]) > 0 for p in diag}) < 2:
                continue
            x0, y0, x1, y1 = bbox([q for p in diag for q in p]); w, h = x1 - x0, y1 - y0
            if not (4 * u <= max(w, h) <= 16 * u and min(w, h) >= 0.5 * max(w, h)):
                continue
            dentro = [p for p in g if all(x0 - 0.4 <= q[0] <= x1 + 0.4 and y0 - 0.4 <= q[1] <= y1 + 0.4 for q in p)]
            if len(dentro) < 4:
                continue
            pts = [q for p in dentro for q in p]
            for base in ('b', 't', 'l', 'r'):
                if base in 'bt':
                    yb = y0 if base == 'b' else y1; apex = ((x0 + x1) / 2, y1 if base == 'b' else y0); c1, c2 = (x0, yb), (x1, yb)
                else:
                    xb = x0 if base == 'l' else x1; apex = (x1 if base == 'l' else x0, (y0 + y1) / 2); c1, c2 = (xb, y0), (xb, y1)
                sides = ((c1, c2), (c1, apex), (c2, apex))
                if all(min(seg_dist(q, a, b) for a, b in sides) < 0.4 for q in pts):
                    out.append((x0, y0, x1, y1)); break
        return out

    def boxes_around(self, p, m=2.0):
        """recuadros que contienen (o tocan) el punto, del mas chico al mas grande"""
        c = [b for b in self.boxes if b[0] - m <= p[0] <= b[2] + m and b[1] - m <= p[1] <= b[3] + m]
        return sorted(c, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))

    def on_box_edge(self, p, tol=1.2):
        return any(min(abs(p[0] - b[0]), abs(p[0] - b[2])) < tol and b[1] - tol <= p[1] <= b[3] + tol or
                   min(abs(p[1] - b[1]), abs(p[1] - b[3])) < tol and b[0] - tol <= p[0] <= b[2] + tol
                   for b in self.boxes if max(b[2] - b[0], b[3] - b[1]) < 80 * self.u)

    def drop_dots(self, strokes):
        """los puntos de union (rellenos) no son bornes"""
        fills = [((bbox(p)[0] + bbox(p)[2]) / 2, (bbox(p)[1] + bbox(p)[3]) / 2) for l, o, p in strokes
                 if o in ('f', 'F', 'f*', 'B', 'B*', 'b', 'b*') and len(p) >= 4 and max(bbox(p)[2] - bbox(p)[0], bbox(p)[3] - bbox(p)[1]) < max(8.5 * self.u, 8.5)]
        self.circles = [c for c in self.circles if not any(dist(f, c) < 0.8 for f in fills)]

    def circle_at(self, p, tol=1.3):
        best = None
        for cx, cy, r in self.circles:
            d = abs(dist(p, (cx, cy)) - r)
            if (d < tol or dist(p, (cx, cy)) < r) and (best is None or d < best[0]):
                best = (d, (cx, cy, r))
        return best[1] if best else None

    def round_at(self, p, tol=1.3):
        """circulo grande (no es borne) sobre cuyo contorno termina el cable: polo de una bateria, pin redondo"""
        c = [(abs(dist(p, (cx, cy)) - r), (cx, cy, r)) for cx, cy, r in self.rounds if abs(dist(p, (cx, cy)) - r) < tol]
        return min(c)[1] if c else None

    def tri_at(self, p, tol=1.5):
        return any(box_dist(p, b) < tol for b in self.tris)

    def column(self, c, vertical):
        """circulos alineados con c (misma x si vertical, misma y si horizontal), solo el grupo
        contiguo que contiene a c (un hueco de mas de 60 pt separa bornes distintos)"""
        cx, cy, r = c
        if vertical:
            col = sorted((k for k in self.circles if abs(k[0] - cx) < 0.8 and abs(k[1] - cy) < 150 * self.u), key=lambda k: -k[1])
            pos = lambda k: -k[1]
        else:
            col = sorted((k for k in self.circles if abs(k[1] - cy) < 0.8 and abs(k[0] - cx) < 150 * self.u), key=lambda k: k[0])
            pos = lambda k: k[0]
        runs, cur = [], []
        for k in col:
            if cur and pos(k) - pos(cur[-1]) > 80 * self.u:
                runs.append(cur); cur = []
            cur.append(k)
        if cur:
            runs.append(cur)
        for run in runs:
            if any(abs(k[0] - cx) < 0.1 and abs(k[1] - cy) < 0.1 for k in run):
                return run
        return [c]


# ------------------------------------------------------------------ analisis de cada punta
def end_direction(graph, route_chains, p):
    """vector desde la punta hacia el cable (para saber por que lado llega)"""
    best = None
    for c in route_chains:
        for s in graph.chains[c]:
            a, b, _ = graph.segs[s]
            for q, o in ((a, b), (b, a)):
                d = dist(q, p)
                if d < 0.8 and (best is None or d < best[0]):
                    best = (d, (o[0] - q[0], o[1] - q[1]))
    return best[1] if best else (0.0, 0.0)


def describe_end(pg, sym, p, direction, cable_nums):
    """-> dict(tipo='flecha'|'borne', tag, borne, punto, lado, texto)"""
    lines = pg['lines']; u = sym.u
    # flecha a otra hoja: triangulo en la punta o referencia (ShNN:XX) al lado
    near_ref = [l for l in lines if box_dist(p, l['bbox']) < 30 * u and SHREF_RE.search(l['text'])]
    if sym.tri_at(p) and not near_ref:        # flecha con la referencia (ShNN:XX) escrita un poco mas lejos
        lej = [l for l in lines if box_dist(p, l['bbox']) < 60 * u and SHREF_RE.search(l['text'])]
        near_ref = sorted(lej, key=lambda l: box_dist(p, l['bbox']))[:1] or ref_apilada(lines, p, u)
    if sym.tri_at(p) or (near_ref and not sym.circle_at(p)):
        refs = [m.group(0) for l in near_ref for m in SHREF_RE.finditer(l['text'])]
        hint = [l['text'] for l in lines if box_dist(p, l['bbox']) < 30 * u and re.search(r'\d{2}[A-Z]+\.?\d*:\w+', l['text'])]
        # rotulo corto al lado de la flecha ('L' / 'N' de la alimentacion de red): nombra la punta si la flecha es una
        # conexion al exterior (sin referencia de hoja ni otra flecha que la continue)
        rot = sorted((box_dist(p, l['bbox']), l['text'].strip()) for l in lines if box_dist(p, l['bbox']) < 30 * u
                     and re.fullmatch(r'[A-Z]{1,2}\d?', l['text'].strip()))
        return dict(tipo='flecha', refs=refs, pista=hint[0] if hint else '', rotulo=rot[0][1] if rot else '')
    q = seguir_empalme(sym, p)
    if q:
        p, direction = q
    circ = sym.circle_at(p)
    center = (circ[0], circ[1]) if circ else p
    # componente: referencia (TAG) mas cercana, tambien dentro de textos largos "(21PCB01)"
    tags = []; campo = []; kr_mod = {}
    if '_sint' not in pg:   # tags armados con dos textos: burbuja 'PT'/'001', 'BH-01' + '-M'
        pg['_sint'] = burbujas(lines) + pegados(lines)
    if '_pistas' not in pg:
        pg['_pistas'] = pistas_de_flecha(lines, sym)
    for l in lines + pg['_sint']:
        t = l['text'].strip()
        if ':' in t or (circ and id(l) in pg['_pistas']):
            continue      # (la pista de una flecha, '43DIB1' encima de '(Sh43:A4)', nombra el destino, no este borne)
        t2 = re.sub(r'^(\d{2}) ([A-Z][A-Z0-9]{1,7})$', r'\1\2', t)    # '31 AIB1': la fuente SHX deja un espacio
        mkr = re.fullmatch(r'(\d{2}[A-Z]{0,3}KR)\.(\d{1,2})', t2)     # '61KR.3': modulo 3 del rele 61KR
        if mkr:
            found = [mkr.group(1)]; kr_mod[id(l)] = mkr.group(2)
        elif TAG_RE.fullmatch(t2):
            found = [t2]
        elif FIELD_RE.fullmatch(t):
            found = [ISA_ESTADO_RE.sub('', t)]
        else:
            found = re.findall(r'\((\d{2}[A-Z][A-Z0-9]{1,7})\)', t)
        for tg in found:
            dd = box_dist(center, l['bbox'])
            es_campo = not TAG_RE.fullmatch(tg) and (FIELD_RE.fullmatch(tg) or FIELD_RE.fullmatch(t))
            if es_campo:
                campo.append((dd, tg, l))
            if TAG_RE.fullmatch(tg) or (es_campo and dd < 80 * u):
                tags.append((dd, tg, l))
    tags.sort(key=lambda t: t[0])
    tag = tags[0][1] if tags and tags[0][0] < 400 * u else ''
    if not tag and tags:
        # regla del taller: el tag nombra los bornes de abajo en su columna hasta el proximo tag (el rotulo de un modulo
        # o de una bornera se escribe una sola vez arriba de la columna, aunque quede lejos de los ultimos bornes)
        tag = tag_de_columna(sym, center, tags, u) or ''
    tag_cercano = tag
    # referencia dentro del recuadro (aparato o marco) mas chico que contiene la punta
    for bx in sym.boxes_around(p):
        inside = [t for t in tags if bx[0] <= t[2]['bbox'][0] and t[2]['bbox'][2] <= bx[2] and bx[1] <= t[2]['bbox'][1] and t[2]['bbox'][3] <= bx[3]]
        if inside:
            tag = min(inside, key=lambda t: t[0])[1]
            break
    else:
        borde = not circ and sym.on_box_edge(p)   # llega al borde de un recuadro sin referencia dentro
        pcb = [t for t in tags if 'PCB' in t[1]]
        if borde and pcb:
            tag = pcb[0][1]                        # pin de E/S de la placa (21PCB01)
    borde = not circ and sym.on_box_edge(p)
    # bornera: el rotulo suele estar una sola vez encima (o debajo) de su columna de bornes
    if circ and is_terminal_block(tag):
        colx = [t for t in tags if is_terminal_block(t[1]) and abs((t[2]['bbox'][0] + t[2]['bbox'][2]) / 2 - center[0]) < 45 * u
                and abs((t[2]['bbox'][1] + t[2]['bbox'][3]) / 2 - center[1]) < 400 * u]
        if colx:
            best = min(colx, key=lambda t: abs((t[2]['bbox'][1] + t[2]['bbox'][3]) / 2 - center[1]))
            if best[1] != tag and best[0] < 3 * max(tags[0][0], 30 * u):
                tag = best[1]
        else:
            cx = lambda t: (t[2]['bbox'][0] + t[2]['bbox'][2]) / 2
            cy = lambda t: (t[2]['bbox'][1] + t[2]['bbox'][3]) / 2
            if abs(cx(tags[0]) - center[0]) >= 45 * u:          # el tag mas cercano esta al costado, no sobre esta columna
                arriba = sorted((t for t in tags if is_terminal_block(t[1]) and abs(cx(t) - center[0]) < 45 * u and 0 < cy(t) - center[1] < 900 * u),
                                key=lambda t: cy(t) - center[1])
                if arriba:
                    best = arriba[0]
                    entre = [t for t in tags if t is not best and abs(cx(t) - center[0]) < 45 * u and center[1] < cy(t) < cy(best)]
                    if not entre:
                        tag = best[1]
    if not tag:   # hoja de distribucion de una placa: 'Placa electronica E2.5 (21PCB01)'
        m = re.search(r'\((\d{2}[A-Z][A-Z0-9]{1,7})\)', pg['meta'].get('title', ''))
        if m:
            tag = m.group(1)
    vertical = abs(direction[1]) >= abs(direction[0])
    col = []
    if circ:
        cv, ch = sym.column(circ, True), sym.column(circ, False)
        def same_number(run):
            labs = set()
            for k in run:
                near = [l['text'].strip() for l in lines if not es_simbolo(l, sym) and re.fullmatch(r'\d{1,3}', l['text'].strip()) and box_dist((k[0], k[1]), l['bbox']) < 12 * u]
                labs |= set(near)
            return len(labs) <= 1
        if is_terminal_block(tag) and len(cv) == 4 and same_number(cv): col, vertical = cv, True
        elif is_terminal_block(tag) and len(ch) == 4 and same_number(ch): col, vertical = ch, False
        else:
            col = cv if vertical else ch
            if len(col) == 4:
                col = [circ]
    anchors = [(k[0], k[1]) for k in col] if len(col) == 4 and is_terminal_block(tag) else [center]
    # polo redondo grande (bateria 12PB1 del 75287, 11.5 pt): su '+'/'-' se mide desde el centro (del lado opuesto al
    # cable queda a mas de 22u de la punta). Solo el polo: los pines redondos de una placa siguen con la punta
    rnd = None if circ else sym.round_at(p)
    Hn = 7.93 * u   # alto de los numeros de cable de este plano
    # rotulo del borne: texto corto valido mas cercano (sin confundir el circulito con un '0')
    cands = []
    for l in lines + list(pg.get('signos') or ()):
        t = l['text'].strip()
        if not t or t in cable_nums or SHREF_RE.search(t) or ':' in t:
            continue
        t2 = t.replace(' ', '')
        if not LABEL_RE.match(t2) or t2 in ('0', '00', 'O'):
            continue
        if es_simbolo(l, sym):
            continue
        if (l.get('H') or 0) > 3 * Hn:
            continue   # 'letra' de mas de 3 veces el alto de texto del plano: rayas de un cable leidas como texto, no un rotulo
        if t2 in ('+', '-') and (is_terminal_block(tag) or sobre_cable(pg, l) or
                                 (t2 == '-' and l['bbox'][3] - l['bbox'][1] > 0.2 * (l['bbox'][2] - l['bbox'][0]))):
            continue   # polo de un aparato; no la raya de corte de un cable, la cruz de dos cables ni el lado de un fusible
        b = l['bbox']; bc = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        if any(dist(bc, (k[0], k[1])) < k[2] + 0.8 and max(b[2] - b[0], b[3] - b[1]) < 2 * k[2] + 1.5 for k in sym.circles + ([rnd] if rnd else [])):
            continue   # es el propio simbolo del borne
        d = min(box_dist(a, b) for a in anchors)
        if rnd and t2 in ('+', '-'):
            d = min(d, box_dist((rnd[0], rnd[1]), b))
        if t2 in ('+', '-') and any(bbox_gap(b, tr) < min(d, 8 * u) for tr in sym.tris):
            continue   # el '+' de una flecha de alimentacion (triangulo) que esta al lado, no el polo de esta punta
        if d < 22 * u:
            cands.append((d, t2, l))
    cands.sort(key=lambda c: c[0])
    label = cands[0][1] if cands else ''
    if cands and re.fullmatch(r'\d|[A-Z]{1,2}\(\d', label):
        # rotulo partido por el decodificador: 'NC(1' + '2' (el '2)' quedo aparte, a veces girado) = 'NC(12)'
        b0 = cands[0][2]['bbox']; h0 = b0[3] - b0[1]
        for l in lines:
            t, b = l['text'].strip(), l['bbox']
            if l is cands[0][2] or not (b[1] < b0[3] and b0[1] < b[3]):
                continue
            if label.isdigit() and re.fullmatch(r'[A-Z]{1,2}\(\d', t) and 0 <= b0[0] - b[2] < 0.8 * max(h0, b[3] - b[1]):
                label = t + label; break
            if not label.isdigit() and re.fullmatch(r'\d\)?', t) and 0 <= b[0] - b0[2] < 0.8 * max(h0, b[3] - b[1]):
                label = label + t; break
    if re.fullmatch(r'[A-Z]\d', label) and 'KR' not in tag:
        # rotulo con el signo al final que el decodificador dejo aparte ('D1' + '-' del MOXA): el signo pegado a la derecha
        b0 = cands[0][2]['bbox']; h0 = b0[3] - b0[1]
        sg = [s for s in (pg.get('signos') or ()) if s['text'].strip() in ('+', '-') and 0 <= s['bbox'][0] - b0[2] < 0.8 * h0
              and b0[1] - 0.2 * h0 <= (s['bbox'][1] + s['bbox'][3]) / 2 <= b0[3] + 0.2 * h0]
        if sg:
            label += sg[0]['text'].strip()
    if label in ('(+)', '(-)'):   # fuente: '1 (-)'
        num = next((l['text'].strip() for l in sorted(lines, key=lambda l: box_dist(center, l['bbox']))
                    if re.fullmatch(r'\d{1,2}', l['text'].strip()) and box_dist(center, l['bbox']) < 24 * u), '')
        label = f'{num} {label}'.strip()
    # lado: por donde llega el cable. Vertical: desde arriba = ARRIBA. Horizontal: desde la izquierda = ARRIBA
    if vertical:
        lado = 'ARRIBA' if direction[1] > 0 else 'ABAJO'
    else:
        lado = 'ARRIBA' if direction[0] < 0 else 'ABAJO'
    punto = None
    if circ:
        if len(col) == 4 and is_terminal_block(tag):   # borne de 4 puntos (QUATTRO): numerar los circulos
            idx = min(range(len(col)), key=lambda i: dist(col[i], circ))
            punto = idx + 1
        elif len(col) == 2:   # borne de 2 puntos: el primero (arriba / izquierda) = ARRIBA
            idx = min(range(2), key=lambda i: dist(col[i], circ))
            lado = 'ARRIBA' if idx == 0 else 'ABAJO'
    # rele: numero del modulo (recuadro con un digito cerca de la referencia KR)
    modulo = ''
    if tag and 'KR' in tag:
        # el recuadro es casi cuadrado y de 5u a 20u de lado (en el A3 del TPT mide 8,55 pt = 16,03u: con el tope de 16u
        # quedaba '61KR 11' sin modulo en una hoja y '61KR1 11' en la otra)
        boxes = [l for l in lines if re.fullmatch(r'[1-9]', l['text'].strip()) and
                 (box_dist(p, l['bbox']) < max(110 * u, 110) or (box_dist(p, l['bbox']) < max(170 * u, 170) and abs((l['bbox'][0] + l['bbox'][2]) / 2 - p[0]) < max(60 * u, 60))) and
                 any(r[0] - 1 <= l['bbox'][0] and r[1] - 1 <= l['bbox'][1] and l['bbox'][2] <= r[2] + 1 and l['bbox'][3] <= r[3] + 1
                     and 5 * u <= r[2] - r[0] <= 20 * u and 5 * u <= r[3] - r[1] <= 20 * u
                     and abs((r[2] - r[0]) - (r[3] - r[1])) < 0.3 * max(r[2] - r[0], r[3] - r[1]) for r in sym.rects)]
        if boxes:
            modulo = min(boxes, key=lambda l: box_dist(p, l['bbox']))['text'].strip()
        if not modulo:      # modulo escrito con punto en el rotulo: '61KR.3 (Sh:61:E4)'
            tl = next((t[2] for t in tags if t[1] == tag), None)
            if tl is not None and id(tl) in kr_mod:
                modulo = kr_mod[id(tl)]
    if not circ and not borde and not label and not modulo and tag == tag_cercano and (not tag or tags[0][0] > 80 * u):
        # punta suelta (sin circulo, pin ni rotulo) lejos de toda referencia: es un equipo de campo cuyo tag esta al pie
        # de su bloque de descripcion, mas lejos que el tag de un componente (66817 hoja 12: contacto de la trombetta
        # BH-01-ZV y masa del motor BH-01-M, a ~190u; el tag de componente mas cercano es 12PB1)
        lejos = sorted(t for t in campo if t[0] < 400 * u and (not tag or t[0] < tags[0][0]))
        if lejos:
            tag = lejos[0][1]
    borne = norm_label(label)
    # QUATTRO con el numero repetido en la misma bornera (66817: 13XC1 tiene una '1', dos '2' y dos '3'): la de la
    # IZQUIERDA (en el funcional y en la bandeja) es N.1..N.4, la siguiente N.5..N.8, y asi
    if punto and len(col) == 4 and is_terminal_block(tag) and re.fullmatch(r'\d{1,3}', borne or ''):
        xs = quattro_gemelas(pg, sym, u, tag, borne, col, lines)
        if len(xs) > 1:
            me = sum(k[0] for k in col) / 4
            punto += 4 * min(range(len(xs)), key=lambda j: abs(xs[j] - me))
    if re.fullmatch(r'\d{2}Q\d+', tag) and borne in ('1', '2', '3', '4'):
        borne = 'F' if borne in ('1', '2') else 'N'
    tit = re.search(r'\((\d{2}[A-Z][A-Z0-9]{1,7})\)', pg['meta'].get('title', ''))
    if circ and tit and borne and not punto and not modulo and tag == tag_cercano and tag != tit.group(1) and (not tags or tags[0][0] > 80 * u):
        # hoja de distribucion de una placa ('Electronic Board (21PCB01)'): sus pines numerados (circulos) son de ese
        # aparato aunque haya otro tag a media distancia (la descripcion de un canal, '12PB1 Power Battery')
        tag = tit.group(1)
    return dict(tipo='borne', tag=tag + modulo, tag_base=tag, borne=borne, borde=borde, punto=punto, lado=lado,
                vertical=vertical, circulo=bool(circ), p=[round(p[0], 1), round(p[1], 1)])


def pistas_de_flecha(lines, sym):
    """ids de los textos que son la PISTA de una flecha a otra hoja: el renglon pegado a un '(ShNN:XX)' (en el mismo
    sentido de escritura) junto al triangulo de la flecha ('43DIB1' / '(Sh43:A4)' al pie de las flechas de la placa del
    TPT). Nombran el aparato de destino, no el de un borne de al lado."""
    u = sym.u; out = set()
    refs = [r for r in lines if SHREF_RE.search(r['text'])]
    if not refs or not sym.tris:
        return out
    for l in lines:
        t = l['text'].strip()
        if not TAG_RE.fullmatch(t) or SHREF_RE.search(t):
            continue
        b = l['bbox']; ang = l.get('ang', 0)
        for r in refs:
            if r is l or r.get('ang', 0) != ang:
                continue
            c = r['bbox']
            if ang in (90, 270):     # renglones verticales, uno al lado del otro
                h = min(b[2] - b[0], c[2] - c[0])
                pegado = b[1] < c[3] and c[1] < b[3] and bbox_gap(b, c) < 1.5 * h
            else:
                h = min(b[3] - b[1], c[3] - c[1])
                pegado = b[0] < c[2] and c[0] < b[2] and bbox_gap(b, c) < 1.5 * h
            if not pegado:
                continue
            un = (min(b[0], c[0]), min(b[1], c[1]), max(b[2], c[2]), max(b[3], c[3]))
            if any(bbox_gap(un, tr) < 30 * u for tr in sym.tris):
                out.add(id(l)); break
    return out


def empalme_en_rama(pg, sym, g, chains, k, cable_nums):
    """el nodo k es una esquina del recorrido (llegan dos de sus tramos) donde sale un tercer tramo que no es del
    recorrido. Si uno de los dos llega en DIAGONAL apuntando a ese tercero, que sigue recto al otro, y el tercero pasa
    por un empalme (rectangulo relleno chico) cerca: -> la punta 'EMPALME' (con el aparato al que sigue ese tramo)."""
    u = sym.u; J = g.nodes[k]
    def salida(s):                      # direccion de un segmento desde J
        a, b, _ = g.segs[s]
        o = b if dist(a, J) < dist(b, J) else a
        vx, vy = o[0] - J[0], o[1] - J[1]; L = math.hypot(vx, vy)
        return (vx / L, vy / L) if L > 0.3 else None
    mias, otras = [], []
    for _, s in g.adj.get(k, []):
        c = g.seg_chain.get(s); w = salida(s)
        if c is None or w is None:
            continue
        (mias if c in chains else otras).append((c, w))
    diag = [t for t in mias if 0.25 < abs(t[1][0]) < 0.97]
    trunk = [t for t in mias if t not in diag]
    if len(mias) != 2 or len(diag) != 1 or len(trunk) != 1 or not otras:
        return None
    din = (-diag[0][1][0], -diag[0][1][1])           # sentido en que llega la diagonal
    t = trunk[0][1]
    rama = [c for c, w in otras if w[0] * din[0] + w[1] * din[1] > 0.7 and w[0] * t[0] + w[1] * t[1] < -0.99]
    if len(rama) != 1:
        return None
    c2 = rama[0]
    if '_empalmes' not in pg:
        pg['_empalmes'] = [bbox(p) for layer, op, p in pg.get('strokes', []) if op in ('f', 'F', 'f*', 'B', 'B*') and len(p) in (4, 5)
                           and 4.8 * u <= max(bbox(p)[2] - bbox(p)[0], bbox(p)[3] - bbox(p)[1]) <= 16 * u
                           and min(bbox(p)[2] - bbox(p)[0], bbox(p)[3] - bbox(p)[1]) >= 3 * u]
    for b in pg['_empalmes']:
        cen = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        if dist(cen, J) > 150 * u or not any(seg_dist(cen, *g.segs[s][:2]) < 0.8 for s in g.chains[c2]):
            continue
        # a donde sigue el tramo despues del empalme: su otra punta
        lejos = [g.nodes[q] for q in g.chain_end_keys(c2) if q != k]
        otro = ''
        if lejos:
            f = max(lejos, key=lambda q: dist(q, J))
            d = describe_end(pg, sym, f, salida_de(g, c2, f), cable_nums)
            if d.get('tipo') == 'borne' and d.get('tag'):
                otro = fmt_terminal(d)
        return dict(tipo='borne', tag='EMPALME', tag_base='EMPALME', borne=f'con {otro}' if otro else '', punto=None, lado='',
                    vertical=False, circulo=False, borde=False, p=[round(cen[0], 1), round(cen[1], 1)], empalme=True)
    return None


def limites_de_hoja(pg):
    """lineas de trazo y punto que marcan el limite del tablero (lo de afuera es campo): rayas finas alineadas (rellenas
    o de trazo) que cubren mas de 150 pt -> [('v', x, y0, y1) | ('h', y, x0, x1)]"""
    if '_limites' in pg:
        return pg['_limites']
    rayas = {'v': collections.defaultdict(list), 'h': collections.defaultdict(list)}
    for layer, op, p in pg.get('strokes', []):
        if len(p) < 2 or len(p) > 5:
            continue
        x0, y0, x1, y1 = bbox(p); w, h = x1 - x0, y1 - y0
        if w < 1.5 and 3 <= h <= 15:
            rayas['v'][round((x0 + x1) / 2 * 2) / 2].append((y0, y1))
        elif h < 1.5 and 3 <= w <= 15:
            rayas['h'][round((y0 + y1) / 2 * 2) / 2].append((x0, x1))
    out = []
    for k, por in rayas.items():
        for c, rs in por.items():
            rs = sorted(set((round(a, 1), round(b, 1)) for a, b in rs))
            tramos, cur = [], []
            for r in rs:                 # rayas seguidas (con huecos de menos de 20 pt) de la misma linea
                if cur and not 0.5 < r[0] - cur[-1][1] < 20:
                    tramos.append(cur); cur = []
                cur.append(r)
            tramos.append(cur)
            for t in tramos:
                if len(t) >= 8 and t[-1][1] - t[0][0] > 150:
                    out.append((k, c, t[0][0], t[-1][1]))
    pg['_limites'] = out
    return out


def cruza_limite(pg, segs):
    """algun tramo cruza una linea de limite del tablero"""
    for k, c, lo, hi in limites_de_hoja(pg):
        for a, b in segs:
            if k == 'v' and min(a[0], b[0]) < c < max(a[0], b[0]) and lo <= (a[1] + b[1]) / 2 <= hi and abs(a[1] - b[1]) < 0.5:
                return True
            if k == 'h' and min(a[1], b[1]) < c < max(a[1], b[1]) and lo <= (a[0] + b[0]) / 2 <= hi and abs(a[0] - b[0]) < 0.5:
                return True
    return False


def salida_de(g, c, p):
    """vector desde la punta p de la cadena c hacia el cable"""
    for s in g.chains[c]:
        a, b, _ = g.segs[s]
        for q, o in ((a, b), (b, a)):
            if dist(q, p) < 0.8:
                return (o[0] - q[0], o[1] - q[1])
    return (0.0, 0.0)


def tag_de_columna(sym, c, tags, u):
    """el tag que encabeza la columna de la punta c (sin tag a menos de 400u): el mas cercano ARRIBA cuyo texto cae en el
    ancho de la columna, que es la fila de recuadros pegados de la punta (pin + canal + descripcion de un modulo, como
    el MOXA del TPT) o +-45u si es una columna de circulos (bornera). El mas cercano arriba no tiene otro tag en el medio."""
    pin = [b for b in sym.boxes if b[0] - 1 <= c[0] <= b[2] + 1 and b[1] - 1 <= c[1] <= b[3] + 1 and max(b[2] - b[0], b[3] - b[1]) < 160 * u]
    if pin:
        fila = list(pin)
        for _ in range(6):     # recuadros de la misma fila pegados a los ya tomados
            nuevos = [b for b in sym.boxes if b not in fila and max(b[2] - b[0], b[3] - b[1]) < 260 * u and any(
                abs(b[2] - a[0]) < 1 or abs(b[0] - a[2]) < 1 for a in fila) and any(b[1] < a[3] and a[1] < b[3] for a in fila)]
            if not nuevos:
                break
            fila += nuevos
        x0, x1 = min(b[0] for b in fila), max(b[2] for b in fila)
    else:
        x0, x1 = c[0] - 45 * u, c[0] + 45 * u
    cy = lambda t: (t[2]['bbox'][1] + t[2]['bbox'][3]) / 2
    col = sorted((t for t in tags if TAG_RE.fullmatch(t[1]) and t[2]['bbox'][0] < x1 and t[2]['bbox'][2] > x0 and cy(t) > c[1]),
                 key=cy)
    return col[0][1] if col else None


def sobre_cable(pg, l, tol=0.6):
    """el centro del texto cae sobre un tramo de cable: un '-' / '+' asi es la raya de corte o el cruce de dos cables"""
    g = pg.get('graph')
    if g is None or not getattr(g, 'segs', None):
        return False
    b = l['bbox']; c = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    for i in g.near_segs(c, tol):
        a, bb, _ = g.segs[i]
        if seg_dist(c, a, bb) < tol:
            return True
    return False


def bbox_gap(a, b):
    return math.hypot(max(a[0] - b[2], b[0] - a[2], 0), max(a[1] - b[3], b[1] - a[3], 0))


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def es_simbolo(l, sym):
    """'texto' que el decodificador armo con trazos de simbolos (circulitos de borne -> '8' '0' 'o', pines -> '日' '□'):
    todos sus trazos son simbolos detectados o tramitos rectos (el cable entre dos circulitos)"""
    ids = l.get('ids') or ()
    si = getattr(sym, 'sym_ids', set())
    if not ids or not (set(ids) & si):
        return False
    by = getattr(sym, '_by_id', {})
    return all(len(by[i]) == 2 for i in ids if i not in si and i in by)


def burbujas(lines):
    """'PT' + '001' (uno debajo del otro, centrados) -> texto sintetico 'PT 001' con la caja de los dos"""
    out = []
    let = [l for l in lines if re.fullmatch(r'[A-Z]{2,3}', l['text'].strip())]
    num = [l for l in lines if re.fullmatch(r'0\d{2}', l['text'].strip())]
    for a in let:
        ha = a['bbox'][3] - a['bbox'][1]; cxa = (a['bbox'][0] + a['bbox'][2]) / 2
        for b in num:
            cxb = (b['bbox'][0] + b['bbox'][2]) / 2
            if abs(cxa - cxb) < 0.8 * ha and 0 <= a['bbox'][1] - b['bbox'][3] < 1.2 * ha:
                bb = (min(a['bbox'][0], b['bbox'][0]), b['bbox'][1], max(a['bbox'][2], b['bbox'][2]), a['bbox'][3])
                out.append(dict(text=a['text'].strip() + ' ' + b['text'].strip(), bbox=bb, ids=set()))
    return out


def ref_apilada(lines, p, u):
    """(ShNN:XX) al pie de un rotulo de varios renglones centrado en la flecha ('Comand' / 'Solenoide Valve' /
    'NC (Normaly Close)' / '+12Vdc' / '(Sh62:D6)'): se baja (o sube) renglon por renglon desde el mas cercano"""
    horiz = [l for l in lines if l.get('ang', 0) in (0, 180)]
    centrado = lambda l: l['bbox'][0] - 2 * u <= p[0] <= l['bbox'][2] + 2 * u
    first = [l for l in horiz if centrado(l) and box_dist(p, l['bbox']) < 30 * u]
    if not first:
        return []
    cur = min(first, key=lambda l: box_dist(p, l['bbox']))
    abajo = (cur['bbox'][1] + cur['bbox'][3]) / 2 < p[1]          # la pila sigue alejandose de la flecha
    seen = [cur]
    for _ in range(8):
        if SHREF_RE.search(cur['text']):
            return [cur]
        h = cur['bbox'][3] - cur['bbox'][1]
        gap = (lambda l: cur['bbox'][1] - l['bbox'][3]) if abajo else (lambda l: l['bbox'][1] - cur['bbox'][3])
        nxt = [l for l in horiz if all(l is not x for x in seen) and centrado(l) and -0.3 * h <= gap(l) < 1.2 * h]
        if not nxt:
            break
        cur = min(nxt, key=gap); seen.append(cur)
    return []


def borne_en_otro_recorrido(pg, sym, g, num, e, dr, cable_nums):
    """la punta e (sin borne propio) cae sobre el recorrido de OTRO numero de la hoja: es una union en T con ese cable
    (66817 hoja 61: 6203 baja de la linea de 6201). El conductor va al borne de ese recorrido hacia donde apunta la
    diagonal de la union, o al mas cercano por el recorrido si llega en angulo recto. -> (punto, extremo) o None"""
    import heapq
    for onum, ort in (pg.get('routes') or {}).items():
        if onum == num:
            continue
        hc = set(ort.get('chains') or [])
        segs = [g.segs[sidx] for c in hc for sidx in g.chains[c]]
        if not any(seg_dist(e, a, b) < 0.8 for a, b, _ in segs):
            continue
        fines = [tuple(f) for f in ort.get('fines') or []]
        if not fines:
            return None
        L = math.hypot(*dr)
        din = (-dr[0] / L, -dr[1] / L) if L > 0.3 else None
        diagonal = din is not None and 0.25 < abs(din[0]) < 0.97
        key = lambda q: (round(q[0], 1), round(q[1], 1))
        adj = collections.defaultdict(list)
        for a, b, _ in segs:
            w = dist(a, b)
            adj[key(a)].append((key(b), w, b)); adj[key(b)].append((key(a), w, a))
        # desde e: por cada tramo que pasa por e (o arranca en e), hacia sus dos puntas
        heap = []
        for a, b, _ in segs:
            if seg_dist(e, a, b) >= 0.8:
                continue
            for q in (a, b):
                v = (q[0] - e[0], q[1] - e[1]); lv = math.hypot(*v)
                if lv < 0.3:
                    continue
                if diagonal and (v[0] * din[0] + v[1] * din[1]) / lv <= 0.2:
                    continue   # la diagonal apunta para el otro lado
                heapq.heappush(heap, (lv, key(q), q))
        best, seen = None, set()
        while heap:
            dd, k, q = heapq.heappop(heap)
            if k in seen:
                continue
            seen.add(k)
            f = next((f for f in fines if dist(f, q) < 1.0), None)
            if f is not None:
                best = f
                break
            for k2, w, q2 in adj[k]:
                if k2 not in seen:
                    heapq.heappush(heap, (dd + w, k2, q2))
        if best is None:
            return None
        d = describe_end(pg, sym, best, end_direction(g, hc, best), cable_nums)
        return (best, d) if d.get('tipo') == 'borne' else None
    return None


def pegados(lines):
    """tag de campo partido en dos textos del mismo renglon ('BH-01' + '-M') -> texto sintetico 'BH-01-M'"""
    out = []
    horiz = [l for l in lines if l.get('ang', 0) == 0 and len(l['text'].strip()) <= 8]
    for a in horiz:
        ta = a['text'].strip()
        if not re.fullmatch(r'[A-Z]{2}-\d{2}-?', ta):
            continue
        h = a['bbox'][3] - a['bbox'][1]
        for b in horiz:
            tb = b['text'].strip()
            if b is a or not re.fullmatch(r'-?[A-Z]{1,2}', tb) or abs(b['bbox'][1] - a['bbox'][1]) > 0.3 * h or not 0 <= b['bbox'][0] - a['bbox'][2] < 0.8 * h:
                continue
            t = ta + tb
            if FIELD_RE.fullmatch(t):
                bb = (a['bbox'][0], min(a['bbox'][1], b['bbox'][1]), b['bbox'][2], max(a['bbox'][3], b['bbox'][3]))
                out.append(dict(text=t, bbox=bb, ids=set()))
    return out


def seguir_empalme(sym, p):
    u = sym.u
    for layer, op, pts in sym._strokes:
        if op not in ('f', 'F', 'f*', 'B', 'B*') or len(pts) not in (4, 5):
            continue
        x0, y0, x1, y1 = bbox(pts)
        if not (4.8 * u <= max(x1 - x0, y1 - y0) <= 16 * u and min(x1 - x0, y1 - y0) >= 3 * u) or box_dist(p, (x0, y0, x1, y1)) > 0.8:
            continue
        c = ((x0 + x1) / 2, (y0 + y1) / 2)
        if abs(p[0] - c[0]) < abs(p[1] - c[1]):          # llega por arriba/abajo: sigue del lado opuesto en vertical
            o = (p[0], y1 if p[1] < c[1] else y0); vert = True
        else:
            o = (x1 if p[0] < c[0] else x0, p[1]); vert = False
        best = None
        for l2, op2, s in sym._strokes:
            if op2 not in ('S', 's') or len(s) != 2:
                continue
            for a, b in ((s[0], s[1]), (s[1], s[0])):
                if dist(a, o) < 0.8 and (abs(a[0] - b[0]) < 0.3 if vert else abs(a[1] - b[1]) < 0.3) and dist(a, b) > 2 * u:
                    if best is None or dist(a, b) > dist(*best):
                        best = (a, b)
        if best:
            a, b = best
            return b, (a[0] - b[0], a[1] - b[1])
    return None


def quattro_gemelas(pg, sym, u, tag, num, col, lines):
    """x (ordenadas) de las columnas QUATTRO de 4 circulos con el mismo numero 'num' y de la misma bornera 'tag'
    que la columna 'col', en la misma franja de la hoja"""
    if '_q4' not in pg:
        runs, vistos = [], set()
        for c in sym.circles:
            run = sym.column(c, True)
            if len(run) != 4:
                continue
            k = tuple(sorted((round(q[0], 1), round(q[1], 1)) for q in run))
            if k in vistos:
                continue
            vistos.add(k)
            labs = set()
            for q in run:
                labs |= {l['text'].strip() for l in lines if not es_simbolo(l, sym) and re.fullmatch(r'\d{1,3}', l['text'].strip())
                         and box_dist((q[0], q[1]), l['bbox']) < 12 * u}
            if len(labs) == 1:
                runs.append((sum(q[0] for q in run) / 4, min(q[1] for q in run), max(q[1] for q in run), labs.pop()))
        pg['_q4'] = runs
    y0, y1 = min(q[1] for q in col), max(q[1] for q in col)
    def tag_de(x, y):          # el rotulo de bornera mas cercano (la bornera puede estar rotulada mas de una vez)
        best = None
        for l in lines:
            t = re.sub(r'^(\d{2}) ([A-Z][A-Z0-9]{1,7})$', r'', l['text'].strip())
            if TAG_RE.fullmatch(t) and is_terminal_block(t):
                d = box_dist((x, y), l['bbox'])
                if best is None or d < best[0]:
                    best = (d, t)
        return best[1] if best else None
    return sorted(r[0] for r in pg['_q4'] if r[3] == num and r[1] <= y1 + 2 * u and r[2] >= y0 - 2 * u
                  and tag_de(r[0], (r[1] + r[2]) / 2) == tag)


def norm_label(t):
    if not t:
        return ''
    m = re.fullmatch(r'[A-Z]{1,2}\((\d{1,2})\)?', t)       # C(11) / NO(14) -> 11 / 14
    if m:
        return m.group(1)
    m = re.fullmatch(r'(\d{1,3})\s*\(([+-])\)', t)          # 1 (-) -> 1 (-)
    if m:
        return f'{m.group(1)} ({m.group(2)})'
    return t


def fmt_terminal(e):
    """texto del extremo segun las reglas del taller"""
    if e is None:
        return '?'
    if e.get('fuera'):
        return 'LI'
    if e.get('texto'):            # punta de EPLAN: el texto del taller ya viene armado (mapeo verificado o regla general)
        return e['texto']
    tag, b = e.get('tag') or '?', e.get('borne') or ''
    if is_terminal_block(e.get('tag_base')):
        if e.get('punto'):
            return f'{tag} {b}.{e["punto"]}' if b else f'{tag} ?.{e["punto"]}'
        return f'{tag} {b} {e["lado"]}'.replace('  ', ' ')
    if 'KR' in tag or 'PS' in tag or 'PCB' in tag or not e.get('vertical') or b in ('+', '-') or FIELD_RE.fullmatch(tag):
        # (el polo '+'/'-' de un aparato ya lo nombra: '12CB1 +'; un equipo de campo 'BH-01-ZV' / 'PT 001' no es un
        # borne de doble piso: sin ARRIBA/ABAJO)
        return f'{tag} {b}'.strip()
    return f'{tag} {b} {e["lado"]}'.replace('  ', ' ')


# ------------------------------------------------------------------ conductores
def pin_box_at(pg, sym, j, tol=1.0):
    """recuadro chico con un numero adentro (pin de un aparato) sobre cuyo borde esta el punto j"""
    for b in sym.boxes:
        w, h = b[2] - b[0], b[3] - b[1]
        if max(w, h) > 45 * sym.u:
            continue
        sobre = (min(abs(j[0] - b[0]), abs(j[0] - b[2])) < tol and b[1] - tol <= j[1] <= b[3] + tol or
                 min(abs(j[1] - b[1]), abs(j[1] - b[3])) < tol and b[0] - tol <= j[0] <= b[2] + tol)
        if not sobre:
            continue
        if any(re.fullmatch(r'\d{1,3}', l['text'].strip()) and b[0] <= l['bbox'][0] and l['bbox'][2] <= b[2] and b[1] <= l['bbox'][1] and l['bbox'][3] <= b[3]
               for l in pg['lines']):
            return b
    return None


def pin_box_on_chain(pg, sym, g, c, tol=1.0):
    """recuadro numerado de pin que la cadena c toca en el MEDIO (no en sus puntas): dos cables que llegan al mismo
    pin y el dibujo los une en el borde del recuadro"""
    on = lambda p, b: (min(abs(p[0] - b[0]), abs(p[0] - b[2])) < tol and b[1] - tol <= p[1] <= b[3] + tol or
                       min(abs(p[1] - b[1]), abs(p[1] - b[3])) < tol and b[0] - tol <= p[0] <= b[2] + tol)
    puntas = [g.nodes[k] for k in g.chain_end_keys(c)]
    medio = [p for sidx in g.chains[c] for p in g.segs[sidx][:2] if all(dist(p, q) > 1.5 for q in puntas)]
    for bx in sym.boxes:
        if max(bx[2] - bx[0], bx[3] - bx[1]) > 45 * sym.u or not any(on(p, bx) for p in medio):
            continue
        if any(re.fullmatch(r'\d{1,3}', l['text'].strip()) and bx[0] <= l['bbox'][0] and l['bbox'][2] <= bx[2] and bx[1] <= l['bbox'][1] and l['bbox'][3] <= bx[3]
               for l in pg['lines']):
            return bx
    return None


def unidad(res, pg, cable_nums):
    """escala del dibujo respecto del plano con que se calibraron los umbrales en pt (A1 75287): core la mide como la
    altura del texto de los numeros de cable / 7.93 pt (res.k: 1.0 en el A1, ~0.54 en un A3). Respaldo si no esta:
    medirla en la hoja, o por el ancho de la hoja."""
    k = getattr(res, 'k', None)
    if k:
        return k
    hs = sorted(min(l['bbox'][2] - l['bbox'][0], l['bbox'][3] - l['bbox'][1]) for l in pg['lines'] if l['text'].strip() in cable_nums)
    if len(hs) >= 2:
        return hs[len(hs) // 2] / 7.93
    return (pg.get('w') or 2383.4) / 2383.4


def hoja_base(h):
    """numero de una hoja sin la letra de subhoja / alternativa ni los ceros de adelante: '61A' -> '61', '09' -> '9'"""
    m = re.match(r'\d+', h or '')
    return (m.group(0) if m else (h or '')).lstrip('0')


def alternativas_hoja(pg):
    """None | ('hoja', grupo, n): toda la hoja es la ALTERNATIVA n (61A 'ALTERNATIVA 1', 61B 'ALTERNATIVA 2') |
    ('franjas', grupo, [(y del titulo, n)...]): la hoja tiene varias, cada una debajo de su titulo (TPT hoja 15)"""
    if '_alts' not in pg:
        tit = sorted(((l['bbox'][1] + l['bbox'][3]) / 2, int(m.group(1))) for l in pg['lines'] for m in [ALT_RE.search(l['text'])] if m)
        ns = {n for _, n in tit}
        g = hoja_base(pg['meta'].get('sheet') or str(pg['index']))
        pg['_alts'] = ('hoja', g, ns.pop()) if len(ns) == 1 else ('franjas', g, tit) if ns else None
    return pg['_alts']


def alternativa(pg, p):
    """(grupo, n) de la punta p si esta en una ALTERNATIVA, o None"""
    a = alternativas_hoja(pg)
    if not a or p is None:
        return None
    if a[0] == 'hoja':
        return (a[1], a[2])
    arriba = [(y, n) for y, n in a[2] if y >= p[1]]            # el titulo mas cercano por encima de la punta
    return (a[1], min(arriba)[1]) if arriba else None


def alternativas(res):
    """{grupo: dict(ns, elegida, por, marcas)} de las alternativas del plano. Se elige la que tiene en la lista de
    materiales la marca o el modelo que la distingue de las otras ('BARRERA CHENZHU', 'MARCA: VIBO'); si no se puede
    saber, la primera (ALTERNATIVA 1)."""
    a = getattr(res, '_alternativas', None)
    if a is not None:
        return a
    regiones = collections.defaultdict(lambda: collections.defaultdict(list))     # grupo -> n -> textos
    for pg in res.pages:
        al = alternativas_hoja(pg)
        if not al:
            continue
        for l in pg['lines']:
            n = al[2] if al[0] == 'hoja' else (alternativa(pg, (0, (l['bbox'][1] + l['bbox'][3]) / 2)) or (None, None))[1]
            if not n:
                continue
            t = l['text']
            if ALT_RE.search(t):      # el titulo sigue en otros textos del mismo renglon: 'ALTERNATIVA 1' 'BARRERA CHENZHU'
                h = l['bbox'][3] - l['bbox'][1]
                sig = sorted((x for x in pg['lines'] if x is not l and abs((x['bbox'][1] + x['bbox'][3]) / 2 - (l['bbox'][1] + l['bbox'][3]) / 2) < 0.5 * h
                              and 0 <= x['bbox'][0] - l['bbox'][2] < 3 * h), key=lambda x: x['bbox'][0])
                t = ' '.join([t] + [x['text'] for x in sig])
            regiones[al[1]][n].append(t)
    def marcas(textos):
        """palabras de la marca / el modelo: lo que sigue a 'MARCA:' / 'BRAND:' o al titulo 'ALTERNATIVA n'
        -> (palabras, frase para mostrar: la de 'MARCA:' si hay, si no la del titulo)"""
        w = set(); frases = []
        for t in textos:
            ma = ALT_RE.search(t)
            mb = re.search(r'(?:BRAND|MARCA)\s*:?\s*(.+)', t, re.I)
            resto = t[ma.end():] if ma else mb.group(1) if mb else ''
            w |= {x for x in re.findall(r'[A-Z0-9+]{3,}', resto.upper()) if not x.isdigit()}
            if resto.strip():
                frases.append((0 if mb else 1, resto.strip()))
        return w, (min(frases)[1] if frases else '')
    bom = set()
    for pg in res.pages:
        if re.search(r'materia', pg['meta'].get('title', ''), re.I):
            for l in pg['lines']:
                bom |= set(re.findall(r'[A-Z0-9+]{3,}', l['text'].upper()))
    out = {}
    for g, por_n in regiones.items():
        ns = sorted(por_n)
        mw = {n: marcas(por_n[n]) for n in ns}
        w = {n: mw[n][0] for n in ns}
        dist_ = {n: {x for x in w[n] if not any(x in w[m] for m in ns if m != n)} for n in ns}
        score = {n: len(dist_[n] & bom) for n in ns}
        best = max(score.values()) if score else 0
        if len(ns) > 1 and best > 0 and list(score.values()).count(best) == 1:
            el, por = max(ns, key=lambda n: score[n]), 'la de la lista de materiales'
        else:
            el, por = ns[0], 'la primera' if len(ns) > 1 else 'unica'
        out[g] = dict(ns=ns, elegida=el, por=por, marcas={n: mw[n][1] for n in ns})
    try:
        res._alternativas = out
    except AttributeError:
        pass
    return out


def alternativas_del_cable(nodes, alts):
    """-> (nodos de las alternativas que NO se cablean, notas para el taller). En un cable dibujado en varias
    alternativas del mismo grupo quedan solo las puntas de la elegida; un cable que existe solo en otra alternativa se
    deja, con la nota para confirmar"""
    grupos = collections.defaultdict(set)
    for d in nodes.values():
        if d.get('alt'):
            grupos[d['alt'][0]].add(d['alt'][1])
    fuera, notas = set(), []
    for g, ns in sorted(grupos.items()):
        info = alts.get(g)
        if not info or len(info['ns']) < 2:
            continue
        marca = lambda n: f" ({info['marcas'].get(n)})" if info['marcas'].get(n) else ''
        if len(ns) > 1:
            keep = info['elegida'] if info['elegida'] in ns else min(ns)
            fuera |= {nid for nid, d in nodes.items() if d.get('alt') and d['alt'][0] == g and d['alt'][1] != keep}
            txt = lambda n: {fmt_terminal(d) for d in nodes.values() if d['tipo'] == 'borne' and d.get('alt') == (g, n)}
            otras = [f"en la {n}{marca(n)}: {', '.join(sorted(txt(n) - txt(keep)))}" for n in sorted(ns) if n != keep and txt(n) - txt(keep)]
            if otras:     # (si todas las alternativas lo dibujan igual no hay nada que avisar)
                notas.append(f"hoja {g}: ALTERNATIVA {keep}{marca(keep)}, {info['por'] if keep == info['elegida'] else 'la unica donde esta este cable'}; "
                             + '; '.join(otras))
        else:
            n = next(iter(ns))
            if n != info['elegida']:
                notas.append(f"hoja {g}: este cable esta solo en la ALTERNATIVA {n}{marca(n)} y la elegida es la "
                             f"{info['elegida']}{marca(info['elegida'])}: confirmar si se monta")
    return fuera, notas


def arbol(nodes, adj, canon, terms):
    """tramos de un conductor: N puntas = N-1 tramos reales. Los dibujados de borne a borne (o contraidos en una union
    en T) y, por cada grupo de flechas / nodos de paso que junta k bornes, k-1 tramos siguiendo el grupo desde el borne
    del lado 'unico' (la hoja con menos bornes del grupo: la flecha que reparte). Nunca todos los pares k(k-1)/2."""
    es_borne = lambda v: nodes.get(v, {}).get('tipo') == 'borne'
    pairs = set()
    for n in terms:
        for v in adj[n]:
            if es_borne(v) and canon[n] != canon[v]:
                pairs.add(tuple(sorted((canon[n], canon[v]))))
    vistos = set()
    for s0 in sorted(adj):
        if es_borne(s0) or s0 in vistos:
            continue
        grupo, stack = {s0}, [s0]
        while stack:
            x = stack.pop()
            for v in adj[x]:
                if not es_borne(v) and v not in grupo:
                    grupo.add(v); stack.append(v)
        vistos |= grupo
        toca = {}                                  # canon -> pagina del borne que toca el grupo
        att = {}                                   # nodo del grupo -> bornes (canon) que llegan a el
        for x in sorted(grupo):
            att[x] = []
            for v in sorted(adj[x]):
                if es_borne(v):
                    if canon[v] not in att[x]:
                        att[x].append(canon[v])
                    toca.setdefault(canon[v], nodes[v].get('pag'))
        if len(toca) < 2:
            continue
        # se recorre el grupo (flecha -> flecha de la otra hoja -> ...) desde el borne del lado 'unico' (la hoja con
        # menos bornes del grupo: la flecha que reparte) y cada borne se une al ultimo borne del camino: una flecha que
        # sigue de largo por otra hoja da un tramo por hoja, no uno entre todos
        cnt = collections.Counter(toca.values())
        raiz = min(toca, key=lambda m: (cnt[toca[m]], toca[m] or 0))
        start = next(x for x in sorted(grupo) if raiz in att[x])
        cola, visto = [(start, None)], {start}
        while cola:
            x, rep = cola.pop(0)
            bs = att[x]
            if bs:
                base = rep if rep is not None else bs[0]
                for b in bs:
                    if b != base:
                        pairs.add(tuple(sorted((base, b))))
                rep = bs[0] if raiz not in bs else raiz
            for v in sorted(adj[x]):
                if v in grupo and v not in visto:
                    visto.add(v); cola.append((v, rep))
    return pairs


def conductors(res):
    """para cada numero de cable: lista de conductores (extremo A, extremo B)"""
    pre = getattr(res, 'conductores', None)
    if pre is not None:           # plano de EPLAN: los conductores salen de la lista de conexiones (eplan.process)
        return {num: dict(c, pares=list(c['pares']), bornes=list(c['bornes'])) for num, c in pre.items()}
    cable_nums = {d['num'] for d in res.detail}
    by_num = collections.defaultdict(list)          # num -> [(pg, route)]
    for pg in res.pages:
        for num, rt in pg.get('routes', {}).items():
            by_num[num].append((pg, rt))
    out = {}
    for num, items in by_num.items():
        nodes = {}            # id -> extremo
        edges = []
        arrows = []           # (node_id, hoja, refs)
        for pg, rt in items:
            g = pg['graph']
            if '_sym' not in pg:
                tids = set()
                for l in pg['lines']:
                    if sum(ch.isalpha() for ch in l['text']) >= 2:
                        tids |= set(l.get('ids') or ())
                pg['_sym'] = Symbols(pg.get('strokes', []), tids, u=unidad(res, pg, cable_nums), pw=pg.get('w') or 2383.4, ph=pg.get('h') or 1683.4)
                pg['_sym'].drop_dots(pg.get('strokes', []))
            sym = pg['_sym']
            chains = set(rt.get('chains') or [])
            ends = [tuple(e) for e in rt['fines']]; joins = [tuple(j) for j in rt['uniones']]
            for j in list(joins):
                if sym.circle_at(j) and not any(dist(e, j) < 1.5 for e in ends):
                    joins.remove(j); ends.append(j)
            ids = {}
            for e in ends:
                nid = f'{pg["index"]}:{e[0]:.1f},{e[1]:.1f}'
                dr = end_direction(g, chains, e)
                d = describe_end(pg, sym, e, dr, cable_nums)
                if d['tipo'] == 'borne' and not d['circulo'] and not d['borde'] and not d['borne']:
                    otro = borne_en_otro_recorrido(pg, sym, g, num, e, dr, cable_nums)
                    if otro:      # union en T con el recorrido de otro numero: el conductor va a ese borne
                        d = otro[1]
                d['hoja'] = pg['meta'].get('sheet', str(pg['index'])); d['pag'] = pg['index']; d['alt'] = alternativa(pg, e)
                nodes[nid] = d; ids[e] = nid
                if d['tipo'] == 'flecha':
                    arrows.append((nid, d['hoja'], d.get('refs', [])))
            # union sobre el recuadro numerado de un pin (ej. barrera: dos cables al mismo pin): ese pin es un borne
            snap = {}
            for j in joins:
                bx = pin_box_at(pg, sym, j)
                if bx:
                    nid = f'{pg["index"]}:pin{bx[0]:.1f},{bx[1]:.1f}'
                    if nid not in nodes:
                        c0 = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
                        d = describe_end(pg, sym, c0, (j[0] - c0[0], j[1] - c0[1]), cable_nums)
                        d['hoja'] = pg['meta'].get('sheet', str(pg['index'])); d['pag'] = pg['index']; d['p'] = [round(j[0], 1), round(j[1], 1)]
                        d['alt'] = alternativa(pg, j)
                        nodes[nid] = d
                    snap[j] = nid
            # union en T dibujada con un tramo en DIAGONAL: la diagonal 'apunta' al borne donde se hace la union
            # (ej. 6201 en la hoja 62 o la derivacion del toma en la hoja 11): se sigue el tramo recto hacia donde apunta
            def snap_diagonal(j):
                incid = []
                for c in chains:
                    pk = [g.nodes[k] for k in g.chain_end_keys(c)]
                    if not any(dist(p, j) < 0.8 for p in pk):
                        continue
                    first = None
                    for sidx in g.chains[c]:
                        a, b, _ = g.segs[sidx]
                        if dist(a, j) < 0.8:
                            first = (a, b); break
                        if dist(b, j) < 0.8:
                            first = (b, a); break
                    if not first:
                        continue
                    vx, vy = first[1][0] - first[0][0], first[1][1] - first[0][1]; L = math.hypot(vx, vy)
                    if L < 0.3:
                        continue
                    incid.append(((vx / L, vy / L), next((p for p in pk if dist(p, j) >= 0.8), None)))
                diag = [t for t in incid if 0.25 < abs(t[0][0]) < 0.97]
                trunk = [t for t in incid if t not in diag]
                if len(diag) != 1 or not trunk:
                    return None
                din = (-diag[0][0][0], -diag[0][0][1])            # sentido en que llega la diagonal a la union
                best = max(trunk, key=lambda t: t[0][0] * din[0] + t[0][1] * din[1])
                if best[0][0] * din[0] + best[0][1] * din[1] <= 0.2 or not best[1]:
                    return None
                cand = [e for e in ends if nodes[ids[e]]['tipo'] == 'borne' and dist(e, best[1]) < 1.5]
                return ids[cand[0]] if cand else None
            # union en T: se contrae en el extremo (borne) mas cercano -> puente en ese borne
            for j in joins:
                if j in snap:
                    continue
                sd = snap_diagonal(j)
                if sd:
                    snap[j] = sd
                    continue
                real = [e for e in ends if nodes[ids[e]]['tipo'] == 'borne'] or ends
                snap[j] = ids[min(real, key=lambda e: dist(e, j))] if real else None
            # union en T con una rama SIN numero (otro conductor: 'Blanco/0,3mm2 PIN 2') que pasa por un EMPALME
            # (cuadradito relleno), con la diagonal apuntando a esa rama: el recorrido la tomaba como una esquina y se
            # perdia la tercera punta. Los dos tramos del cable van al empalme (TPT hoja 81: 8105 / 8106 con el RS-485)
            cnt_k = collections.Counter(k for c in chains for k in g.chain_end_keys(c))
            for k, v in cnt_k.items():
                if v != 2 or len(g.adj.get(k, [])) < 3:
                    continue
                J = g.nodes[k]
                if any(dist(J, e) < 1.5 for e in ends) or any(dist(J, j) < 1.5 for j in joins):
                    continue
                emp = empalme_en_rama(pg, sym, g, chains, k, cable_nums)
                if emp:
                    nid = f'{pg["index"]}:emp{emp["p"][0]:.1f},{emp["p"][1]:.1f}'
                    emp.update(hoja=pg['meta'].get('sheet', str(pg['index'])), pag=pg['index'], alt=alternativa(pg, emp['p']))
                    nodes[nid] = emp; joins.append(J); snap[J] = nid
            # aristas: cada tramo del recorrido une dos nodos (extremos o uniones)
            pts = [(e, ids[e]) for e in ends] + [(j, snap[j]) for j in joins]
            for c in chains:
                ks = g.chain_end_keys(c)
                ns = []
                for k in ks:
                    q = g.nodes[k]
                    near = min(pts, key=lambda t: dist(t[0], q)) if pts else None
                    if near and dist(near[0], q) < 1.5:
                        ns.append(near[1])
                    else:
                        ns.append(f'{pg["index"]}:paso{q[0]:.1f},{q[1]:.1f}')
                if len(ns) == 2 and ns[0] and ns[1] and ns[0] != ns[1]:
                    bx = pin_box_on_chain(pg, sym, g, c)
                    if bx:        # el recorrido pasa por el borde de un pin: ese pin es un borne en el medio (puente)
                        nid = f'{pg["index"]}:pin{bx[0]:.1f},{bx[1]:.1f}'
                        if nid not in nodes:
                            c0 = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
                            d = describe_end(pg, sym, c0, (0.0, 0.0), cable_nums)
                            d['vertical'] = False
                            d['hoja'] = pg['meta'].get('sheet', str(pg['index'])); d['pag'] = pg['index']; d['p'] = [round(c0[0], 1), round(c0[1], 1)]
                            d['alt'] = alternativa(pg, c0)
                            nodes[nid] = d
                        edges += [(ns[0], nid), (nid, ns[1])]
                    else:
                        edges.append((ns[0], ns[1]))
        # ALTERNATIVAS: hojas o franjas 'ALTERNATIVA n' que dibujan el mismo circuito con otro aparato (TPT: tres
        # barreras 43DIB1 en la hoja 15 y en las 43A/43B/43C, dos unidades hidraulicas en la 61A/61B). Se monta UNA (la
        # de la lista de materiales o, si no se sabe, la primera): las puntas de las otras no son puntas de este cable
        fuera_alt, notas_alt = alternativas_del_cable(nodes, alternativas(res))
        for n in fuera_alt:
            nodes.pop(n, None)
        edges = [(a, b) for a, b in edges if a not in fuera_alt and b not in fuera_alt]
        arrows = [a for a in arrows if a[0] not in fuera_alt]
        # componer por el recorrido: nodos intermedios que no son extremos (flechas de paso) se saltan
        adj = collections.defaultdict(set)
        for a, b in edges:
            adj[a].add(b); adj[b].add(a)
        # unir flechas entre hojas: la flecha de la hoja A que apunta a la hoja B se une con las
        # flechas de la hoja B que apuntan a A (si ninguna apunta a A, con todas las de B). La hoja se compara por su
        # numero: '61A' es la hoja 61 (la referencia dice 'Sh61')
        for nid, hoja, refs in arrows:
            dest = {m.group(1).lstrip('0') for r in refs for m in [SHREF_RE.search(r)] if m}
            for nid2, hoja2, refs2 in arrows:
                if nid2 == nid or hoja_base(hoja2) not in dest:
                    continue
                back = {m.group(1).lstrip('0') for r in refs2 for m in [SHREF_RE.search(r)] if m}
                others = [a for a in arrows if hoja_base(a[1]) == hoja_base(hoja2) and
                          hoja_base(hoja) in {m.group(1).lstrip('0') for r in a[2] for m in [SHREF_RE.search(r)] if m}]
                if hoja_base(hoja) in back or not others:
                    adj[nid].add(nid2); adj[nid2].add(nid)
        terms = [n for n, d in nodes.items() if d['tipo'] == 'borne']
        # mismo borne dibujado en dos hojas -> un solo nodo
        canon = {}
        for n in terms:
            d = nodes[n]
            key = (d['tag'], d['borne'], d['punto'], d['lado']) if d['tag'] and d['borne'] else None
            canon[n] = next((m for m in canon.values() if key and (nodes[m]['tag'], nodes[m]['borne'], nodes[m]['punto'], nodes[m]['lado']) == key), n)
        # mismo borne de rele dibujado en dos hojas con el numero de modulo leido en una sola: '61KR A1' (sin modulo) es
        # el '61KRn A1' de ESTE cable si hay uno solo con ese borne
        for n in terms:
            d = nodes[n]
            if canon[n] != n or 'KR' not in (d['tag'] or '') or d['tag'] != d.get('tag_base') or not d['borne']:
                continue
            con = {canon[m] for m in terms if canon[m] != n and nodes[m].get('tag_base') == d['tag_base']
                   and nodes[m]['borne'] == d['borne'] and nodes[m]['tag'] != d['tag_base']}
            if len(con) == 1:
                dst = con.pop()
                for m in terms:
                    if canon[m] == n:
                        canon[m] = dst
        pcb_nodes = [n for n in terms if 'PCB' in (nodes[n]['tag'] or '') and nodes[n]['borne']]
        for n in terms:
            d = nodes[n]
            if canon[n] == n and d.get('borde') and 'PCB' not in (d['tag'] or '') and d['borne']:
                same = [m for m in pcb_nodes if nodes[m]['borne'] == d['borne']]
                if same:
                    canon[n] = canon[same[0]]
        pairs = arbol(nodes, adj, canon, terms)
        # un tramo que se lee igual que otro (el mismo borne dibujado en dos hojas sin unirse en un nodo) es el mismo;
        # uno que se lee igual de los dos lados es un borne consigo mismo, no un conductor
        por_texto = {}
        for a, b in sorted(pairs):
            k = tuple(sorted((fmt_terminal(nodes[a]), fmt_terminal(nodes[b]))))
            if k[0] != k[1]:
                por_texto.setdefault(k, (a, b))
        pairs = set(por_texto.values())
        if not pairs and len({canon[n] for n in terms}) == 1:
            # una sola punta y una flecha SIN referencia de hoja que no continua en ninguna otra, con el cable cruzando
            # la linea de trazo y punto del limite del tablero: es la conexion al exterior (campo: la alimentacion de
            # red L / N / tierra del cliente), no un cable cortado
            def al_campo(a):
                pg_ = res.pages_by_index.get(nodes[a[0]]['pag']) if hasattr(res, 'pages_by_index') else None
                rt_ = (pg_ or {}).get('routes', {}).get(num) if pg_ else None
                if not rt_:
                    return False
                g_ = pg_['graph']
                return cruza_limite(pg_, [g_.segs[s][:2] for c_ in rt_.get('chains') or [] for s in g_.chains[c_]])
            sueltas = [a for a in arrows if not a[2] and not any(nodes.get(v, {}).get('tipo') == 'flecha' for v in adj[a[0]]) and al_campo(a)]
            if sueltas:
                nid = sueltas[0][0]
                nodes[nid].update(tipo='borne', tag='CAMPO', tag_base='CAMPO', borne=nodes[nid].get('rotulo') or '', punto=None,
                                  lado='', vertical=False, circulo=False, borde=False, campo=True)
                canon[nid] = nid; terms.append(nid)
                pairs = {tuple(sorted((canon[terms[0]], nid)))}
        out[num] = dict(nodes=nodes, pares=sorted(pairs), bornes=sorted({canon[n] for n in terms}))
        if notas_alt:
            out[num]['alternativas'] = notas_alt
    # interruptor ('11Q1') dibujado sin numeros de borne: los polos por su posicion en el simbolo (regla del taller:
    # 1/2 = F, 3/4 = N; el polo de la izquierda es el 1/2). Solo con dos polos en vertical.
    polos = collections.defaultdict(list)
    for c in out.values():
        for d in c['nodes'].values():
            if d.get('tipo') == 'borne' and not d.get('borne') and d.get('vertical') and d.get('p') and re.fullmatch(r'\d{2}Q\d+', d.get('tag_base') or ''):
                polos[(d.get('pag'), d['tag'])].append(d)
    for ds in polos.values():
        xs = []
        for x in sorted(d['p'][0] for d in ds):
            if not xs or x - xs[-1][-1] > 2.0:
                xs.append([x])
            else:
                xs[-1].append(x)
        if len(xs) == 2:
            for d in ds:
                d['borne'] = 'F' if d['p'][0] <= xs[0][-1] + 0.5 else 'N'
    return out


# ------------------------------------------------------------------ armado del instructivo
def natk(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', str(s or ''))]


def side_of(e):
    """0 = parte de ARRIBA del aparato, 1 = parte de ABAJO"""
    tag = e.get('tag_base') or ''; b = e.get('borne') or ''
    if is_terminal_block(tag):
        if e.get('punto'):                            # QUATTRO: 1, 2 arriba / 3, 4 abajo (segunda bornera del numero: 5..8)
            return 0 if (e['punto'] - 1) % 4 < 2 else 1
        return 0 if e.get('lado') == 'ARRIBA' else 1
    if 'KR' in tag:                                   # rele: contactos arriba, bobina A1/A2 abajo
        return 1 if b in ('A1', 'A2') else 0
    if re.search(r'PS\d', tag):                       # fuente: salida arriba, entrada abajo
        return 1 if re.search(r'L|N|Vin|PE|~', b) and not re.search(r'Vo|\(', b) else 0
    return 0 if e.get('lado') == 'ARRIBA' else 1


def cable_desc(res, num, e, e2=None):
    """('N2.5MM', color, '2.5'): color + seccion de la aparicion del numero que queda en el camino entre las dos
    puntas del conductor (en una derivacion cada tramo puede tener otra seccion)"""
    occ = [d for d in res.detail if d['num'] == num]
    same = [d for d in occ if d['pag'] == e.get('pag')] or occ
    if not same:
        return '', '', ''
    p = e.get('p') or [0, 0]
    q = e2.get('p') if e2 and e2.get('pag') == e.get('pag') and e2.get('p') else None
    cen = lambda d: ((d['bbox'][0] + d['bbox'][2]) / 2, (d['bbox'][1] + d['bbox'][3]) / 2)
    d = min(same, key=lambda d: dist(p, cen(d)) + (dist(q, cen(d)) if q else 0))
    ini = COLOR_INI.get(d['color'], (d['color'] or '?')[:1].upper())
    sec = str(d['sec']).replace(',', '.')
    return f'{ini}{sec}MM', d['color'], sec


def build(res, lay, max_lineas=7):
    """lay: layout del topografico + opcionales:
       bornes          texto (o 'texto#cable') -> [x, y] o [x, y, r]  punto exacto del borne (mapeo)
       bornes_usuario  idem, ajustados a mano en el visor (mandan sobre el mapeo)
       renombrar       'texto#cable' -> texto correcto (modulo del rele, bornera vecina mal leida...)
       estaciones      cable -> estacion donde se cablea si NO es esta (ej. {'3141': 'E8'})"""
    cs = conductors(res)
    con_lista = getattr(res, 'conductores', None) is not None      # EPLAN: conductores de la lista de conexiones
    comp = lay.get('comp', {})
    bornes = lay.get('bornes') or {}
    usuario = lay.get('bornes_usuario') or {}
    renombrar = lay.get('renombrar') or {}
    bornes_conf = lay.get('bornes_conf') or {}      # clave de 'bornes' -> 'alta' | 'media' (mapeo automatico)
    bornes_nota = lay.get('bornes_nota') or {}      # clave -> por que (puntos 'media' del mapeo)
    estaciones = lay.get('estaciones') or {}
    # aparatos que se cablean en otra estacion (ej. la zona hidraulica en E8): del topografico o del mapeo verificado
    est_tag = {t: c['estacion'] for t, c in (lay.get('comp') or {}).items() if c.get('estacion')}
    est_tag.update(lay.get('estaciones_tag') or {})
    def est_par(*es):
        for e in es:
            t = (e or {}).get('tag_base')
            if t and t in est_tag:
                return est_tag[t]
        return None
    filas = lay.get('filas') or []
    kr = (lay.get('perfil_riel_pt') or 24.8) / 24.8      # 1.0 en el topografico 75441 (A1); se escala en otros planos
    def lateral(e):
        """'LD' si la punta esta en el lateral derecho segun el topografico; si no 'LI' (lateral izquierdo, puerta...)"""
        c = comp.get(e.get('tag_base')) if e else None
        return 'LD' if c and c.get('lateral') == 'DERECHO' else 'LI'
    def bandeja(e):
        c = comp.get(e.get('tag_base'))
        return c if c and c.get('ubic') == 'BANDEJA' else None
    def base_txt(e, num):
        t = fmt_terminal(e)
        return t, renombrar.get(f'{t}#{num}', t)
    def buscar(dic, ts, num):
        for t in ts:
            for k in (f'{t}#{num}', t):
                if k in dic:
                    return dic[k]
        return None
    def flip(t):
        m = re.match(r'^(.*) (ARRIBA|ABAJO)$', t)
        return f"{m.group(1)} {'ABAJO' if m.group(2) == 'ARRIBA' else 'ARRIBA'}" if m else t
    def exacto(e, num):
        """(x, y, r, de_usuario) del borne, o None"""
        t, tn = base_txt(e, num)
        u = buscar(usuario, (tn, flip(tn)), num)
        v = u or buscar(bornes, (tn, t), num)
        if not v:
            return None
        return (float(v[0]), float(v[1]), float(v[2]) if len(v) > 2 and v[2] else None, bool(u))
    def confianza(e, num):
        """de donde sale el punto de la punta: ('usuario' | 'manual' | 'alta' | 'media' | None, por que)
        usuario = ajustado en el visor; manual = bornes.json / correcciones.json del trabajo; alta / media = mapeo"""
        if not e or not bandeja(e):
            return None, None
        t, tn = base_txt(e, num)
        if buscar(usuario, (tn, flip(tn)), num):
            return 'usuario', None
        for x in (tn, t):
            for k in (f'{x}#{num}', x):
                if k in bornes:
                    return bornes_conf.get(k, 'manual'), bornes_nota.get(k)
        return None, None
    def lado_fisico(e, num):
        """0 = arriba / 1 = abajo por la posicion real del borne respecto del eje de su riel (None si no se sabe)"""
        c = bandeja(e)
        if not c:
            return None
        if c.get('lado') in ('ARRIBA', 'ABAJO'):        # forzado en 'Componentes y orden' (ej. toma que se cablea todo por abajo)
            return 0 if c['lado'] == 'ARRIBA' else 1
        p = exacto(e, num)
        f = c.get('fila')
        if not p or not f or f > len(filas):
            return None
        eje = filas[f - 1]
        return (0 if p[1] > eje else 1) if 3 * kr < abs(p[1] - eje) < 80 * kr else None
    def lado(e, num):
        f = lado_fisico(e, num)
        return side_of(e) if f is None else f
    def texto(e, num):
        t = base_txt(e, num)[1]
        f = lado_fisico(e, num)
        m = re.match(r'^(.*) (ARRIBA|ABAJO)$', t)
        if f is not None and m:
            t = f"{m.group(1)} {'ARRIBA' if f == 0 else 'ABAJO'}"
        return t
    # ORDEN DE CABLEADO (regla del taller): primero los cables que quedan DEBAJO de otros. En una columna de bornes
    # el de afuera (el mas cerca de la canaleta) va primero: rele 11 (C) -> 14 (NO) -> 12 (NC); A2 -> A1; QUATTRO
    # 1 -> 2 arriba y 4 -> 3 abajo; doble piso impar -> par; barreras enchufe de afuera -> de adentro.
    # Los modulos iguales pegados (banco de reles, banco de barreras) se cablean capa por capa en todo el banco;
    # el resto, aparato por aparato (como las etapas del WPC 75286-1).
    familia = lambda t: 'KR' if 'KR' in (t or '') else 'IB' if re.search(r'[A-Z]IB\d*$', t or '') else None
    banco = {}
    for f_ in {c.get('fila') for c in comp.values() if c.get('ubic') == 'BANDEJA'}:
        prev = None
        for t_, c_ in sorted(((t, c) for t, c in comp.items() if c.get('ubic') == 'BANDEJA' and c.get('fila') == f_), key=lambda tc: tc[1]['x']):
            fm = familia(t_)
            banco[t_] = prev[1] if fm and prev and prev[0] == fm else c_['x']
            prev = (fm, banco[t_]) if fm else None
    def capa(e, num):
        """0, -1, -2...: mas negativo = mas afuera (mas lejos del eje del riel) = se cablea antes"""
        p = exacto(e, num); c = bandeja(e); f = c.get('fila')
        if p and f and f <= len(filas):
            return -round(abs(p[1] - filas[f - 1]) / (3.0 * kr))
        tag, b = e.get('tag') or '', e.get('borne') or ''
        if 'KR' in tag:
            n = {'11': 0, '14': 1, '12': 2, 'A2': 0, 'A1': 1}.get(b, 1)
        elif e.get('punto'):
            n = 0 if (e['punto'] - 1) % 4 in (0, 3) else 1     # 1/4 (y 5/8) = extremos, van abajo
        elif is_terminal_block(e.get('tag_base')) and b.isdigit():
            n = 0 if int(b) % 2 else 1
        else:
            n = 0
        return -10 + 2 * n
    # ZONAS: las canaletas verticales que cruzan un riel lo dividen (ej. la azul del riel 2: borneras | barreras);
    # se cablea zona por zona, y en cada zona primero la parte de arriba y despues la de abajo
    ductos = lay.get('ductos') or []
    def zona(tag):
        c = comp.get(tag); f = c.get('fila') if c else None
        if not c or not f or f > len(filas):
            return 0
        eje = filas[f - 1]
        return sum(1 for d in ductos if not d['h'] and d['b'][1] <= eje <= d['b'][3] and (d['b'][0] + d['b'][2]) / 2 < c['x'])
    def key(e, num):
        c = bandeja(e)
        tag = e.get('tag') or ''
        mod = re.sub(r'^.*?KR', '', tag) if 'KR' in tag else ''
        p = exacto(e, num)
        return (c['fila'], zona(e.get('tag_base')), lado(e, num), banco.get(e.get('tag_base'), c['x']), capa(e, num),
                p[0] if p else c['x'], natk(mod), natk(e.get('borne')), e.get('punto') or 0)
    lineas, pendientes, sueltos = [], [], []
    for num, c in cs.items():
        nodes = c['nodes']
        if not c['pares']:
            tray = [n for n in c['bornes'] if bandeja(nodes[n])]
            fuera = [n for n in c['bornes'] if not bandeja(nodes[n])]
            if len(tray) == 1 and fuera:
                c['pares'] = [(tray[0], fuera[0])]
            else:
                if c['bornes']:
                    sueltos.append(dict(num=num, extremos=[fmt_terminal(nodes[n]) for n in c['bornes']]))
                continue
        grado = collections.Counter(n for par in c['pares'] for n in par)
        nota_alt = '; '.join(c.get('alternativas') or []) or None
        for a, b in c['pares']:
            ea, eb = nodes[a], nodes[b]
            if not con_lista and base_txt(ea, num)[1] == base_txt(eb, num)[1]:
                continue      # 'tramo' de un borne a si mismo (el mismo borne leido distinto en dos hojas): no es un conductor
            ta, tb = bandeja(ea), bandeja(eb)
            # derivacion (3+ puntas): el borne donde se hace la union es comun a varios tramos; la seccion de cada
            # tramo es la de la etiqueta mas cerca de su otra punta (la parte del dibujo que es solo de ese tramo)
            propia = eb if grado[a] > 1 and grado[b] == 1 else ea if grado[b] > 1 and grado[a] == 1 else None
            pdesc = (c.get('desc_par') or {}).get((a, b))     # EPLAN: color y seccion de ese renglon de la lista de conexiones
            desc_de = (lambda o, d: pdesc) if pdesc else (lambda o, d: cable_desc(res, num, propia) if propia else cable_desc(res, num, o, d))
            if not ta and not tb:
                desc, col, sec = desc_de(ea, eb)
                pendientes.append(dict(num=num, cable=desc, color=col, secc=sec, a=fmt_terminal(ea), b=fmt_terminal(eb)))
                if nota_alt:
                    pendientes[-1]['alternativa'] = nota_alt
                if est_par(ea, eb):
                    pendientes[-1]['_est'] = est_par(ea, eb)
                elif ea.get('campo') or eb.get('campo'):
                    pendientes[-1]['_est'] = 'CAMPO'     # cable de campo (lo conecta el cliente en la obra): no se cablea aca
                continue
            if ta and tb:
                o, d = (ea, eb) if key(ea, num) <= key(eb, num) else (eb, ea)
            else:
                o, d = (ea, eb) if ta else (eb, ea)
            desc, col, sec = desc_de(o, d)
            origen = texto(o, num)
            lineas.append(dict(num=num, cable=desc, color=col, secc=sec, origen=origen, _o=o, _d=d,
                               destino=texto(d, num) if bandeja(d) else lateral(d),
                               componente=origen.split(' ')[0] if base_txt(o, num)[1] != base_txt(o, num)[0] else (o.get('tag') or ''),
                               fila=bandeja(o)['fila'], zona=zona(o.get('tag_base')), lado='arriba' if lado(o, num) == 0 else 'abajo',
                               orden=key(o, num), puente=len(c['pares']) > 1,
                               hojas=sorted({ea.get('hoja'), eb.get('hoja')} - {None}, key=natk)))
            if nota_alt:      # el cable cambia segun la ALTERNATIVA que se monte (hojas 'ALTERNATIVA n'): cual se tomo
                lineas[-1]['alternativa'] = nota_alt
            if est_par(ea, eb):
                lineas[-1]['_est'] = est_par(ea, eb)
            if not bandeja(d) and est_par(d):
                # la otra punta es un aparato que se cablea en otra estacion (ej. la zona hidraulica en E8): en la
                # lista de esa estacion va su texto real, no 'LI'
                lineas[-1]['_dreal'] = base_txt(d, num)[1]
            if con_lista:
                # EPLAN: cada renglon de la lista de conexiones es un tramo real (aunque dos tramos de la misma punta
                # de la bandeja a dos puntos distintos de afuera se escriban igual, 'X 1 -> LI')
                lineas[-1]['_par'] = (num,) + tuple(sorted((a, b)))
    # ---- correcciones de la verificacion contra el funcional (correcciones.json del trabajo): conductores que el
    # programa no lee solo (tierras sin numero, mallas a trazos), pendientes mal armados
    def sintetico(txt):
        """punta armada desde su texto ('XPE 1 ARRIBA', '13XC1 2.1', '11PS1 L-3'): fmt_terminal(e) == txt"""
        tag, _, rest = txt.partition(' ')
        base = tag if tag in comp else re.sub(r'\d+$', '', tag) if re.sub(r'\d+$', '', tag) in comp else tag
        e = dict(tipo='borne', tag=tag, tag_base=base, borne=rest, punto=None, lado='ARRIBA', vertical=False, circulo=True, p=None, hoja=None, pag=None)
        m = re.match(r'^(.*) (ARRIBA|ABAJO)$', rest)
        if m:
            e.update(borne=m.group(1), lado=m.group(2), vertical=True)
        m2 = re.fullmatch(r'(\d+)\.(\d)', rest)
        if m2 and is_terminal_block(base):
            e.update(borne=m2.group(1), punto=int(m2.group(2)))
        return e
    for a in lay.get('agregar') or []:
        eo = sintetico(a['origen']); ed = None if a['destino'] in ('LI', 'LD') else sintetico(a['destino'])
        if not bandeja(eo):
            if ed and bandeja(ed):
                eo, ed = ed, eo
            else:
                continue
        num = a['num']
        lineas.append(dict(num=num, cable=a.get('cable', ''), color=a.get('color', ''), secc=a.get('secc', ''), origen=texto(eo, num),
                           _o=eo, _d=ed or dict(fuera=True), destino=texto(ed, num) if ed and bandeja(ed) else (lateral(ed) if ed else a['destino']),
                           componente=eo['tag'], fila=bandeja(eo)['fila'], zona=zona(eo['tag_base']), lado='arriba' if lado(eo, num) == 0 else 'abajo',
                           orden=key(eo, num), puente=sum(1 for x in lay.get('agregar') or [] if x['num'] == num) > 1,
                           hojas=[a['hoja']] if a.get('hoja') else [], agregado=a.get('nota') or 'agregado a mano'))
    # pendientes fantasma: las dos puntas en el mismo aparato y una sin borne (ej. '21PCB01 48 <-> 21PCB01')
    pendientes = [x for x in pendientes if not (x['a'].split(' ')[0] == x['b'].split(' ')[0] and (' ' not in x['a'] or ' ' not in x['b']))]
    quitar = set(lay.get('pendientes_quitar') or [])
    pendientes = [x for x in pendientes if x['num'] not in quitar]
    for num, t in (lay.get('pendientes_texto') or {}).items():
        for x in pendientes:
            if x['num'] == num:
                x.update({k: v for k, v in t.items() if k in ('a', 'b')})
    for x in lay.get('pendientes_agregar') or []:
        pendientes.append(dict(num=x['num'], cable=x.get('cable', ''), color=x.get('color', ''), secc=x.get('secc', ''), a=x['a'], b=x['b'],
                               agregado=x.get('nota') or 'agregado a mano'))
    sq = set(lay.get('sueltos_quitar') or [])
    sueltos = [x for x in sueltos if x['num'] not in sq]
    # ---- ruteo por los cablecanales del topografico
    net = None
    if lay.get('ductos'):
        from ruteo import Net, route_line, length
        net = Net(lay['ductos'])
    mods = collections.defaultdict(set)
    for l in lineas:
        if 'KR' in l['componente']:
            mods[re.sub(r'\d+$', '', l['componente'])].add(l['componente'])
    def punto(e, side, num):
        """-> (x, y, r, exacto)"""
        p = exacto(e, num)
        if p:
            return (p[0], p[1], p[2], True)
        c = bandeja(e)
        x, y = c['x'], c['y']
        tag = e.get('tag') or ''
        if 'KR' in tag:            # modulos del rele repartidos a lo ancho de la etiqueta del grupo
            ms = sorted(mods.get(e.get('tag_base'), {tag}), key=natk)
            if tag in ms and len(ms) > 1:
                x += (ms.index(tag) - (len(ms) - 1) / 2) * 5 * kr
        elif is_terminal_block(e.get('tag_base')) and re.fullmatch(r'\d+', e.get('borne') or ''):
            x += min(int(e['borne']), 12) * 3.5 * kr      # el tag nombra los bornes que tiene a su derecha
        return (x, y + (9 * kr if side == 0 else -9 * kr), None, False)
    a_rutear = []
    for l in lineas:
        o, d = l.pop('_o'), l.pop('_d')
        l['ruta'] = None; l['largo_mm'] = None
        to_li = l['destino'] in ('LI', 'LD')
        so, sd = lado(o, l['num']), (None if to_li else lado(d, l['num']))
        po = punto(o, so, l['num']); pd = None if to_li else punto(d, sd, l['num'])
        l['marca_o'] = [round(po[0], 2), round(po[1], 2), po[2]]; l['exacto_o'] = po[3]
        if pd:
            l['marca_d'] = [round(pd[0], 2), round(pd[1], 2), pd[2]]; l['exacto_d'] = pd[3]
        # de donde sale cada punto (para marcar 'a confirmar' los del mapeo automatico con confianza media)
        l['conf_o'], nota_o = confianza(o, l['num']) if po[3] else (None, None)
        l['conf_d'], nota_d = confianza(d, l['num']) if pd and pd[3] else (None, None)
        if l['conf_o'] == 'media' and nota_o:
            l['nota_o'] = nota_o
        if l['conf_d'] == 'media' and nota_d:
            l['nota_d'] = nota_d
        for w_, e_ in (('o', o), ('d', d)):    # EPLAN sin mapeo verificado: texto de la regla general (eplan.textos_generales)
            if e_ is not None and e_.get('a_confirmar') and not l.get(f'conf_{w_}'):
                l[f'conf_{w_}'], l[f'nota_{w_}'] = 'media', 'texto de la regla general: ' + e_['a_confirmar']
        if net:
            a_rutear.append((l, o, d, so, sd, po, pd, to_li))
    # TIPO DE CIRCUITO de cada cable (intrinsecamente seguro -> canaletas azules; comun -> las otras):
    # - por el color: los azules son intrinsecos;
    # - EPLAN, ademas, por la ZONA de sus puntas en la bandeja (la canaleta a la que entra un cable que sale de ese
    #   borne, net.zona): un azul con todas sus puntas en zona comun no es intrinseco (ej. el RS-485 azul de
    #   0,32 mm2 de 81XCM). Los cables de campo, las mallas y las tierras sin otra punta (sin color, '+Campo' o solo
    #   LI) no tienen color que diga: toman el tipo de la zona de su borne, o del otro piso del mismo borne
    #   (41XEX 1 ARRIBA = 4116 azul -> 41XEX 1 ABAJO es intrinseco). Asi todos los de campo de una bornera de
    #   intrinsecos van por la canaleta azul hasta la salida.
    zonas = {id(l): [z for z in (net.zona(po[:2], so), None if pd is None else net.zona(pd[:2], sd)) if z is not None]
             for l, o, d, so, sd, po, pd, to_li in a_rutear}
    de_campo = lambda l, o, d: bool(o.get('eplan')) and (not l['color'] or d.get('fuera') or d.get('ubicacion'))
    tipo, borne_ex = {}, set()
    for l, o, d, so, sd, po, pd, to_li in a_rutear:
        if de_campo(l, o, d):
            continue
        ex = l['color'] == 'Azul'
        if ex and o.get('eplan') and zonas[id(l)] and not any(zonas[id(l)]):
            ex = False
        tipo[id(l)] = ex
        if ex:
            borne_ex |= {(e.get('tag'), e.get('borne')) for e in (o, d) if bandeja(e) and e.get('borne')}
    for l, o, d, so, sd, po, pd, to_li in a_rutear:
        if de_campo(l, o, d):
            zs = zonas[id(l)]
            tipo[id(l)] = True if any(zs) or (o.get('tag'), o.get('borne')) in borne_ex else (False if zs else None)
    for l, o, d, so, sd, po, pd, to_li in a_rutear:
        try:
            sec = float(l['secc'] or 0)
        except ValueError:
            sec = 0
        # 220 VAC (marron y blanco de potencia) salen a LI por la salida de abajo; el resto por la de arriba
        abajo = l['color'] in ('Marrón', 'Blanco') and sec >= 1.0
        ruta = route_line(net, po[:2], so, None if to_li else pd[:2], sd, tipo[id(l)], to_li, abajo, lado_li='der' if l['destino'] == 'LD' else 'izq')
        if ruta:
            l['ruta'] = ruta
            if lay.get('escala'):
                l['largo_mm'] = int(round(length(ruta) * lay['escala'] / 10.0) * 10)
    # lineas repetidas: el mismo cable con el mismo origen y destino (un agregado a mano que ya estaba, el mismo borne
    # dibujado en dos hojas). EPLAN: cada renglon de la lista es un tramo; se quita solo si es el mismo par de puntas
    vistas = set(); uniq = []
    for l in lineas:
        par = l.pop('_par', None)
        k = (l['num'], l['origen'], l['destino'])
        if (par if par else k) in vistas:
            continue
        vistas |= {k, par} - {None}; uniq.append(l)
    lineas = sorted(uniq, key=lambda l: l['orden'])
    # los tramos de un mismo cable (3 puntas) se cablean seguidos: el puente con terminal doble se hace en el momento
    seguidos, puestos = [], set()
    for l in lineas:
        if id(l) in puestos:
            continue
        for i, x in enumerate([l] + [x for x in lineas if x is not l and x['num'] == l['num'] and id(x) not in puestos]):
            puestos.add(id(x)); x['_sigue'] = i > 0; seguidos.append(x)
    lineas = seguidos
    # cables que se cablean en otra estacion (ej. en el gabinete, E8): fuera de los pasos de esta estacion.
    # Marcados a mano por cable, o por regla de seccion (los de 35 mm2 van en E8). Marcado con esta misma estacion = se queda.
    propia = lay.get('estacion') or 'E6'
    auto = lay.get('estacion_auto') or {}
    def estacion_de(num, secc, por_tag=None):
        e = estaciones.get(num)
        if e:
            return None if e == propia else e
        if por_tag and por_tag != propia:            # una punta en un aparato de otra estacion
            return por_tag
        try:
            sv = float(str(secc or 0).replace(',', '.'))
        except ValueError:
            sv = 0
        return auto.get('estacion', 'E8') if auto.get('seccion_min') and sv >= float(auto['seccion_min']) else None
    otra = [dict(l, estacion=estacion_de(l['num'], l['secc'], l.get('_est'))) for l in lineas if estacion_de(l['num'], l['secc'], l.get('_est'))]
    lineas = [l for l in lineas if not estacion_de(l['num'], l['secc'], l.get('_est'))]
    for x in pendientes:
        if estacion_de(x['num'], x.get('secc'), x.get('_est')):
            otra.append(dict(num=x['num'], cable=x.get('cable', ''), color=x.get('color', ''), secc=x.get('secc', ''),
                             origen=x['a'], destino=x['b'], estacion=estacion_de(x['num'], x.get('secc'), x.get('_est')), pendiente=True))
    pendientes = [x for x in pendientes if not estacion_de(x['num'], x.get('secc'), x.get('_est'))]
    for l in otra:          # en la otra estacion se escribe adonde va de verdad (ej. 'PT001 x1'), no 'LI'
        if l.get('_dreal') and l['destino'] in ('LI', 'LD'):
            l['destino'] = l['_dreal']
    for l in lineas + otra + pendientes:
        l.pop('_est', None); l.pop('_dreal', None)
    for l in otra:
        l.pop('orden', None)
    # pasos: cambia de paso al cambiar de riel o de lado, o al llenarse (sin partir un componente)
    pasos = []
    for l in lineas:
        cur = pasos[-1] if pasos else None
        sigue = l.pop('_sigue', False)          # otro tramo del mismo cable: va en el mismo paso que el primero
        nuevo = not sigue and (cur is None or (cur['fila'], cur['zona'], cur['lado']) != (l['fila'], l['zona'], l['lado']) or
                               (len(cur['lineas']) >= max_lineas and l['componente'] != cur['lineas'][-1]['componente']))
        if nuevo:
            cur = dict(fila=l['fila'], zona=l['zona'], lado=l['lado'], lineas=[]); pasos.append(cur)
        cur['lineas'].append(l)
    for l in otra:
        l.pop('_sigue', None)
    nzonas = collections.defaultdict(set)
    for p in pasos:
        nzonas[p['fila']].add(p['zona'])
    for i, p in enumerate(pasos, 1):
        comps = []
        for l in p['lineas']:
            if l['componente'] not in comps:
                comps.append(l['componente'])
        zt = f" · zona {sorted(nzonas[p['fila']]).index(p['zona']) + 1}" if len(nzonas[p['fila']]) > 1 else ''
        p.update(n=i, titulo=f"Riel {p['fila']}{zt} · parte de {p['lado']} · " + ', '.join(comps), etapa='Etapa 1', foto=None)
        for l in p['lineas']:
            l.pop('orden', None)
    topo = dict(pag=lay.get('pag'), region=lay.get('region'), escala=lay.get('escala'), ductos=lay.get('ductos', []), filas=filas,
                comp={k: dict(x=v['x'], y=v['y'], fila=v.get('fila')) for k, v in comp.items() if v.get('ubic') == 'BANDEJA'})
    # alternativas del plano (hojas / franjas 'ALTERNATIVA n'): cual se tomo para el instructivo y por que
    alts = [dict(hoja=g, elegida=a['elegida'], por=a['por'], opciones={str(n): a['marcas'].get(n, '') for n in a['ns']})
            for g, a in sorted((alternativas(res) if not con_lista else {}).items()) if len(a['ns']) > 1]
    return dict(pasos=pasos, pendientes=sorted(pendientes, key=lambda x: natk(x['num'])),
                sueltos=sueltos, otra_estacion=otra, componentes=comp, topo=topo, accesorios=lay.get('accesorios') or [],
                alternativas=alts)


def linea_txt(l):
    return f"{l['num']}: {l['cable']}   {l['origen']}   →   {l['destino']}"


def known_tags(res):
    cs = conductors(res)
    return sorted({n.get('tag_base') for c in cs.values() for n in c['nodes'].values()
                   if n.get('tipo') == 'borne' and n.get('tag_base') and not n.get('campo') and not n.get('empalme')})


def componentes_panel(res, lay):
    """lista de componentes del funcional con su ubicacion segun el topografico"""
    comp = lay.get('comp', {})
    out = []
    for t in known_tags(res):
        c = comp.get(t)
        out.append(dict(tag=t, ubic=c['ubic'] if c else 'LI', fila=c.get('fila') if c else None,
                        x=c.get('x') if c else None, encontrado=bool(c), leido=c.get('leido', '') if c else ''))
    out.sort(key=lambda c: (c['ubic'] != 'BANDEJA', c['fila'] or 99, c['x'] or 0, c['tag']))
    return out


# ------------------------------------------------------------------ mapeo automatico de bornes (paquete bornes/)
def usos_bandeja(res, lay, topo_pdf=None):
    """Que bornes de cada componente de la BANDEJA usa cada cable, segun el funcional: la entrada del mapeo automatico
    (bornes.mapear_trabajo). Formato usos_por_componente.json: {topografico, pagina_pdf, region_bandeja,
    escala_mm_por_pt, componentes: {tag_base: {etiqueta_topografico: {x, y, riel, leido}, es_bornera, usos: [{cable,
    texto, tag, borne, punto, lado, parte, hoja_funcional, orden_funcional}]}}}.
    'orden_funcional': posicion del borne entre los del mismo nombre en el SIMBOLO del funcional (1 = el primero, de
    izquierda a derecha; de arriba hacia abajo si el simbolo los tiene en columna). Sirve para los pines repetidos
    (DDR: -Vo -Vo +Vo +Vo): el n-esimo de ese nombre en el simbolo va al n-esimo tornillo de ese nombre."""
    cs = conductors(res)
    comp = lay.get('comp') or {}
    comps = {}
    for t, c in comp.items():
        if c.get('ubic') != 'BANDEJA':
            continue
        comps[t] = dict(etiqueta_topografico=dict(x=c.get('x'), y=c.get('y'), riel=c.get('fila'), leido=c.get('leido')),
                        es_bornera=is_terminal_block(t), usos=[])
    vistos = set()
    pos = {}                       # (tag_base, cable, texto) -> [(pag, x, y)] de ese borne en las hojas del funcional
    for num, c in cs.items():
        for par in c['pares']:
            for n in par:
                e = c['nodes'][n]
                tb = e.get('tag_base')
                if tb not in comps:
                    continue
                texto = fmt_terminal(e)
                if (num, texto) in vistos:
                    continue
                vistos.add((num, texto))
                comps[tb]['usos'].append(dict(cable=num, texto=texto, tag=e.get('tag'), borne=e.get('borne'), punto=e.get('punto'),
                                              lado=e.get('lado'), parte='ARRIBA' if side_of(e) == 0 else 'ABAJO',
                                              hoja_funcional=e.get('hoja'), orden_funcional=None))
                # el mismo borne puede estar dibujado en varias hojas (un nodo por hoja antes de unirlos)
                pos[(tb, num, texto)] = [(d.get('pag'), d['p'][0], d['p'][1]) for d in c['nodes'].values()
                                         if d.get('tipo') == 'borne' and d.get('p') and d.get('tag') == e.get('tag')
                                         and d.get('borne') == e.get('borne') and d.get('punto') == e.get('punto')]
    # orden dentro del simbolo de los bornes con el mismo nombre (el mismo texto, distintos cables)
    for tb, cc in comps.items():
        cc['usos'].sort(key=lambda u: (u['texto'], natk(u['cable'])))
        grupos = collections.defaultdict(list)
        for u in cc['usos']:
            grupos[u['texto']].append(u)
        for g in grupos.values():
            if len(g) < 2:
                g[0]['orden_funcional'] = 1
                continue
            # la hoja donde estan dibujados juntos la mayor cantidad de esos bornes (el simbolo)
            hojas = collections.Counter(p[0] for u in g for p in {q[0]: q for q in pos.get((tb, u['cable'], u['texto']), [])}.values())
            if not hojas:
                continue
            pag = max(hojas, key=lambda h: (hojas[h], -(h or 0)))
            en = {}
            for u in g:
                q = [p for p in pos.get((tb, u['cable'], u['texto']), []) if p[0] == pag]
                if q:
                    en[id(u)] = q[0]
            if len(en) < 2:
                continue
            xs = [p[1] for p in en.values()]
            ys = [p[2] for p in en.values()]
            fila = (max(xs) - min(xs)) >= (max(ys) - min(ys))           # bornes en fila (izq -> der) o en columna (arriba -> abajo)
            orden = sorted((u for u in g if id(u) in en), key=lambda u: (en[id(u)][1] if fila else -en[id(u)][2]))
            for i, u in enumerate(orden, 1):
                u['orden_funcional'] = i
    return dict(topografico=topo_pdf, pagina_pdf=lay.get('pag'), region_bandeja=lay.get('region'),
                escala_mm_por_pt=lay.get('escala'), componentes={t: c for t, c in comps.items() if c['usos']})


FABRICANTES_RE = re.compile(r'(?i)\b(phoenix|schneider|mean\s*well|finder|chenzhu|weidm(?:u|ü|ue)ller|omron|abb|siemens|wago|'
                            r'epever|legrand|hager|eaton|moeller|allen[\s-]*bradley|rockwell|telemecanique|steute|'
                            r'pilz|murr|turck|pepperl|sick|ifm|lovato|chint|wieland|entrelec|conexel|vivion|trombetta)\b')


def materiales_funcional(res, min_fabricantes=8):
    """Renglones de la LISTA DE MATERIALES del funcional ('tag | descripcion | marca | modelo ...'), en el formato que
    lee bornes.materiales_de_lineas, o None si el plano no la trae. Una hoja es lista de materiales si tiene muchos
    textos con fabricantes conocidos (PHOENIX, SCHNEIDER, MEAN WELL, FINDER, CHENZHU, WEIDMULLER...). Cada renglon de
    la tabla son los textos a la misma altura, de izquierda a derecha."""
    out = []
    for pg in res.pages:
        lines = [l for l in pg.get('lines') or [] if (l.get('text') or '').strip()]
        n = sum(1 for l in lines if FABRICANTES_RE.search(l['text']))
        titulo = (pg.get('meta') or {}).get('title') or ''
        if n < min_fabricantes and not (n >= 3 and re.search(r'(?i)materiales|bill of materials|\bBOM\b', titulo)):
            continue
        # (los renglones del rotulo de la hoja no traen tags: materiales_de_lineas los ignora)
        # textos horizontales (los rotulos girados del margen no son de la tabla)
        lines = [l for l in lines if (l['bbox'][2] - l['bbox'][0]) >= 0.8 * (l['bbox'][3] - l['bbox'][1]) or len(l['text'].strip()) <= 2]
        alto = sorted(l['bbox'][3] - l['bbox'][1] for l in lines)
        tol = 0.45 * (alto[len(alto) // 2] if alto else 10.0)
        filas = []
        for l in sorted(lines, key=lambda l: -(l['bbox'][1] + l['bbox'][3]) / 2):
            yc = (l['bbox'][1] + l['bbox'][3]) / 2
            if filas and abs(filas[-1]['y'] - yc) <= tol:
                filas[-1]['l'].append(l)
            else:
                filas.append(dict(y=yc, l=[l]))
        for f in filas:
            campos = [l['text'].strip() for l in sorted(f['l'], key=lambda l: l['bbox'][0])]
            if len(campos) >= 2:
                out.append(' | '.join(campos))
    return out or None
