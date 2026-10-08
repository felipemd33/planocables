"""Ruteo de cables por los cablecanales del plano topografico.

- Los cablecanales (capas CANAL/DUCTO: 'CABLECANAL', '_IGV_Ductos') forman una red: cada canaleta aporta su eje
  y se une con las que toca. Se dibujan rellenas (75441: relleno + borde) o solo con el contorno (66817).
- Un cable sale del borne hacia la canaleta del lado del aparato (parte de arriba -> canaleta de arriba del riel;
  parte de abajo -> canaleta de abajo), recorre la red por el camino mas corto y entra al destino de la misma forma.
  Del borne sale en vertical, hacia afuera del riel: si se engancha en una canaleta vertical (intrinsecos), primero
  sube (o baja) hasta el borde de la canaleta de ese lado y recien ahi va en horizontal (no pasa por encima de los
  bornes vecinos); si la canaleta termina antes de la x del borne, corre por el borde de la canaleta hasta esa x (no
  entra en diagonal).
- Canaletas de circuitos intrinsecamente seguros: rellenas de azul (75441) o en la capa de zona segura (66817,
  '_Zona Segura', rayadas). Los cables azules van por ellas y el resto no.
- Salida a LI (regla del taller): por el lateral, arriba; los marrones y blancos (220 VAC) por abajo; los
  intrinsecos por su canaleta si llega al borde.
- Salida elegida a mano (editor de salidas de la web, por grupo de cables): puntos por donde pasa el cable y, el
  ultimo, por donde sale de la bandeja (salida_a_mano).
- Bornera en columna al frente (modelo del catalogo con 'columna_frente', ej. MOXA ioLogik R1240): el cable sale del
  borne en HORIZONTAL hacia el costado ('der' / 'izq') y entra a la canaleta vertical que pasa a esa altura, si esta a
  menos de LATERAL_W anchos de canaleta (enganche_lateral); si no hay, se engancha como siempre.
- Las tolerancias van en anchos de canaleta (W, medido en el plano: 28.5 pt en el 75441, 22.7 pt en el 66817;
  las dos son de 40 mm) o en perfiles de riel H, no en puntos fijos.
"""
import heapq, math, re
import pypdf
from pdfvec import page_strokes, layer_names
from planocables.base.geom import bbox      # (antes de textdec; sigue siendo ruteo.bbox)

RX_DUCTO = re.compile(r'CANAL|DUCTO', re.I)            # 'CABLECANAL', '_IGV_Ductos'
RX_SEGURA = re.compile(r'SEGURA|INTRINSEC', re.I)      # '_Zona Segura': canaletas de intrinsecos
FILL_OPS = ('f', 'F', 'f*', 'B', 'B*', 'b', 'b*')
# en anchos de canaleta W (antes en pt, con W = 28.5 pt del 75441)
TOQUE_W = 0.105       # dos canaletas se tocan: 3 pt
SALIDA_W = 0.42       # tramo que sale de la canaleta hacia el lateral: 12 pt
BORDE_W = 0.5         # una canaleta llega al borde de la red si termina a menos de medio ancho de el
FUERA_W = 0.15        # un cable que corre por fuera de una canaleta va pegado a su borde: 4.3 pt (75441), 3.4 (66817)
SUBIDA_W = 1.0        # salida vertical del borne cuando de ese lado no hay canaleta horizontal que la limite
LATERAL_W = 3.0       # bornera en columna: la canaleta vertical del costado esta a menos de 3 anchos (unos 120 mm)


def is_blue(c):
    return c is not None and c[2] > 0.8 and c[0] < 0.6 and c[1] < 0.6


def ancho(dl):
    """ancho tipico de las canaletas (mediana del lado corto de las comunes)"""
    lado = lambda d: min(d['b'][2] - d['b'][0], d['b'][3] - d['b'][1])
    ws = sorted(lado(d) for d in dl if not d.get('ex')) or sorted(lado(d) for d in dl)
    return ws[len(ws) // 2] if ws else 28.5          # (sin canaletas no hay red: el valor no se usa)


def ducts(pdf_path, pi, box=None, H=None):
    """canaletas de la hoja pi (dentro de box): [dict(b=[x0, y0, x1, y1], h=horizontal, ex=intrinseca)].
    H = perfil del riel en pt (medida del dibujo); si no se da, se mide en la hoja."""
    r = pypdf.PdfReader(pdf_path)
    st = page_strokes(r, pi, layer_names(r), with_color=True)
    if H is None:
        from topo import rail_bands, perfil
        H = perfil(rail_bands([(l, o, p) for l, o, p, c in st])) or 24.8   # hoja sin rieles: perfil del 75441
    out = []
    for l, o, p, col in st:
        duct_layer, ex_layer = bool(RX_DUCTO.search(l)), bool(RX_SEGURA.search(l))
        if not (duct_layer or ex_layer) or len(p) < 4:
            continue
        filled = o in FILL_OPS
        closed = math.dist(p[0], p[-1]) < 0.5 or o == 's'
        if not (filled or (o in ('S', 's') and closed)):     # relleno, o solo el contorno cerrado
            continue
        x0, y0, x1, y1 = bbox(p)
        m = 0.2 * H
        if box and not (box[0] - m <= x0 and x1 <= box[2] + m and box[1] - m <= y0 and y1 <= box[3] + m):
            continue
        w, h = x1 - x0, y1 - y0
        if max(w, h) < 0.8 * H or min(w, h) < 0.32 * H:          # antes 20 / 8 pt
            continue
        ex = (filled and is_blue(col)) or ex_layer
        # el mismo rectangulo dibujado dos veces (relleno + borde): una sola canaleta
        dup = next((q for q in out if all(abs(a - b) < 1.0 for a, b in zip(q['b'], (x0, y0, x1, y1)))), None)
        if dup:
            dup['ex'] = dup['ex'] or ex
            continue
        out.append(dict(b=[round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)], h=w >= h, ex=ex, _capa_ex=ex_layer and not (filled and is_blue(col))))
    # en la capa de zona segura solo cuentan los rectangulos del ancho de las canaletas comunes (+-25 %)
    comunes = sorted(min(q['b'][2] - q['b'][0], q['b'][3] - q['b'][1]) for q in out if not q['ex'])
    wd = comunes[len(comunes) // 2] if comunes else None
    out = [q for q in out if not q['_capa_ex'] or (wd and abs(min(q['b'][2] - q['b'][0], q['b'][3] - q['b'][1]) / wd - 1) < 0.25)]
    for q in out:
        q.pop('_capa_ex')
    return out


class Net:
    def __init__(self, dl):
        self.d = dl
        self.w = ancho(dl)               # ancho de canaleta: unidad de las tolerancias
        self.pts = [[] for _ in dl]      # puntos sobre el eje de cada canaleta
        self.nodes = []                  # (x, y)
        self.adj = {}
        self.extra = []                  # tramos fijos (salidas a LI)
        for i, a in enumerate(dl):
            for j in range(i + 1, len(dl)):
                b = dl[j]
                if self._touch(a['b'], b['b']):
                    p = self._joint(a, b)
                    k = self._node(p)
                    self.pts[i].append(k); self.pts[j].append(k)
        for i, a in enumerate(dl):   # extremos de cada eje
            x0, y0, x1, y1 = a['b']
            ends = [((x0 + 0.1), (y0 + y1) / 2), ((x1 - 0.1), (y0 + y1) / 2)] if a['h'] else [((x0 + x1) / 2, y0 + 0.1), ((x0 + x1) / 2, y1 - 0.1)]
            for e in ends:
                self.pts[i].append(self._node(e))
        self._link_all()

    def _touch(self, a, b):
        m = TOQUE_W * self.w
        return a[0] - m <= b[2] and b[0] - m <= a[2] and a[1] - m <= b[3] and b[1] - m <= a[3]

    def axis(self, d):
        x0, y0, x1, y1 = d['b']
        return ('h', (y0 + y1) / 2, x0, x1) if d['h'] else ('v', (x0 + x1) / 2, y0, y1)

    def _joint(self, a, b):
        ta, ca, a0, a1 = self.axis(a); tb, cb, b0, b1 = self.axis(b)
        if ta != tb:
            # cruce de ejes (aunque una canaleta toque a la otra de canto: la vertical desemboca en la horizontal)
            h, v = (self.axis(a), self.axis(b)) if ta == 'h' else (self.axis(b), self.axis(a))
            return (v[1], h[1])
        if ta == 'h':
            x = (max(a0, b0) + min(a1, b1)) / 2
            return (x, (ca + cb) / 2)
        y = (max(a0, b0) + min(a1, b1)) / 2
        return ((ca + cb) / 2, y)

    def _node(self, p):
        for k, q in enumerate(self.nodes):
            if abs(q[0] - p[0]) < 0.5 and abs(q[1] - p[1]) < 0.5:
                return k
        self.nodes.append((p[0], p[1])); return len(self.nodes) - 1

    def _link_all(self):
        self.adj = {k: [] for k in range(len(self.nodes))}
        for i, d in enumerate(self.d):
            t, c, lo, hi = self.axis(d)
            ks = sorted(set(self.pts[i]), key=lambda k: self.nodes[k][0] if t == 'h' else self.nodes[k][1])
            for a, b in zip(ks, ks[1:]):
                L = math.dist(self.nodes[a], self.nodes[b])
                self.adj[a].append((b, L, d['ex'])); self.adj[b].append((a, L, d['ex']))
        for a, b, L in getattr(self, 'extra', []):
            self.adj.setdefault(a, []).append((b, L, False)); self.adj.setdefault(b, []).append((a, L, False))

    def attach(self, p, side, ex=None):
        """engancha el punto p (borne) a la canaleta horizontal de arriba (side=0) o de abajo (side=1).
        Separacion de los circuitos intrinsecos (ex = tipo del cable; None = sin distinguir, como antes):
        - un cable comun no entra en una canaleta intrinseca: si del lado pedido solo hay intrinsecas, va a la
          canaleta comun mas cercana;
        - un cable intrinseco que del lado pedido no tiene canaleta intrinseca horizontal se engancha en una
          vertical intrinseca que llegue a ese lado, si esta mas cerca que la comun."""
        return self.enganche(p, side, ex)[0]

    def enganche(self, p, side, ex=None):
        """como attach -> (nodo, via): via = puntos del tramo borne -> canaleta (del borne hacia la canaleta, sin los
        extremos), para que ese tramo no tenga diagonales ni pase por encima de otros bornes:
        - canaleta VERTICAL: el cable sale vertical del borne hacia afuera del riel hasta el borde de la canaleta
          horizontal de ese lado y recien ahi va horizontal hasta la vertical (codo en (x del borne, y de enganche));
        - canaleta horizontal que TERMINA antes de la x del borne: sale por el extremo, corre pegado al borde de la
          canaleta hasta la x del borne y baja (o sube) vertical al borne."""
        _, i, q, rama = self._elegir(p, side, ex)
        if rama == 'v':
            q = self._salida_a_vertical(p, side, i)
        # la canaleta horizontal termina antes de la x del borne (el enganche quedo en el extremo del eje, no sobre el
        # borne; un nodo que ya estaba a menos de 0.5 pt no cuenta)
        pasado = rama == 'h' and abs(q[0] - p[0]) > 0.5
        k = self._node(q)
        if k not in self.pts[i]:
            self.pts[i].append(k); self._link_all()
        q = self.nodes[k]                                 # (el nodo puede ser uno que ya estaba a menos de 0.5)
        via = []
        if rama == 'v':
            via = [(p[0], q[1])]
        elif pasado:
            via = self._por_el_borde(p, side, i, q)
        return k, via

    def enganche_lateral(self, p, hacia, ex=None):
        """borne p de una bornera en columna al frente: el cable sale en HORIZONTAL hacia el costado ('der' o 'izq') y
        entra a la canaleta vertical que pasa a la altura del borne de ese lado, la mas cercana a menos de LATERAL_W
        anchos de canaleta (del tipo del cable: comun o intrinseca; ex None = cualquiera). -> (nodo, via) con via = []
        (tramo recto del borne al eje), o (None, None) si no hay: se engancha como siempre."""
        der = hacia != 'izq'
        best = None
        for i, d in enumerate(self.d):
            t, c, lo, hi = self.axis(d)
            if t != 'v' or not (lo <= p[1] <= hi) or (ex is not None and bool(d['ex']) != bool(ex)):
                continue
            gap = d['b'][0] - p[0] if der else p[0] - d['b'][2]
            if -0.5 <= gap <= LATERAL_W * self.w and (best is None or gap < best[0]):
                best = (gap, i, c)
        if best is None:
            return None, None
        _, i, c = best
        k = self._node((c, p[1]))
        if k not in self.pts[i]:
            self.pts[i].append(k); self._link_all()
        return k, []

    def _salida_a_vertical(self, p, side, i):
        """borne p -> canaleta vertical i: primero un tramo vertical que sale del borne hacia afuera del riel (hacia
        arriba con side=0, hacia abajo con side=1) hasta quedar pegado al borde de la canaleta horizontal de ese lado que
        pasa sobre el borne (la que limita el espacio de los aparatos), y recien ahi en horizontal hasta el eje de la
        vertical: asi no pasa por encima de los bornes vecinos. Sin canaleta horizontal de ese lado, sale SUBIDA_W.
        -> punto de enganche en el eje de la vertical"""
        _, c, lo, hi = self.axis(self.d[i])
        f = FUERA_W * self.w
        arriba = side == 0
        bordes = [d['b'][1] if arriba else d['b'][3] for d in self.d
                  if d['h'] and d['b'][0] <= p[0] <= d['b'][2] and (d['b'][1] >= p[1] if arriba else d['b'][3] <= p[1])]
        if bordes:
            e = min(bordes) if arriba else max(bordes)
            y = e - f if arriba else e + f
            if (y < p[1]) if arriba else (y > p[1]):    # borne pegado a la canaleta: a mitad de camino
                y = (p[1] + e) / 2
        else:
            y = p[1] + SUBIDA_W * self.w if arriba else p[1] - SUBIDA_W * self.w
        return (c, min(max(y, lo + 0.2), hi - 0.2))      # dentro del largo de la vertical

    def _por_el_borde(self, p, side, i, q):
        """borne p mas alla del extremo de la canaleta horizontal i (enganche q, en el extremo del eje): el cable sale
        por el extremo, corre en horizontal pegado al borde de la canaleta (el del lado del borne) hasta la x del borne
        y recien ahi va vertical al borne. -> [puntos del borne hacia la canaleta]"""
        x0, y0, x1, y1 = self.d[i]['b']
        f = FUERA_W * self.w
        y = max(y0 - f, p[1]) if side == 0 else min(y1 + f, p[1])   # borde de abajo (canaleta arriba) o de arriba
        return [(p[0], y), (q[0], y)]

    def zona(self, p, side):
        """tipo de la zona del borne p del lado side: True si un cable intrinseco que sale de ahi entra a una canaleta
        de intrinsecos (la horizontal de ese lado, o la vertical azul mas cercana si de ese lado no hay horizontal
        azul), False si entra a una comun, None sin canaletas. No cambia la red."""
        if not self.d:
            return None
        return bool(self.d[self._elegir(p, side, True)[1]]['ex'])

    def _elegir(self, p, side, ex):
        """(costo, canaleta, punto de enganche, rama) para attach; rama: 'h' horizontal de ese lado, 'v' vertical
        intrinseca, 'c' la mas cercana"""
        todas = range(len(self.d))
        def horizontal(pool):
            best = None
            for i in pool:
                t, c, lo, hi = self.axis(self.d[i])
                if t != 'h' or (side == 0 and c < p[1]) or (side == 1 and c > p[1]):
                    continue
                x = min(max(p[0], lo + 0.2), hi - 0.2)
                cost = abs(c - p[1]) + 3 * abs(x - p[0])
                if best is None or cost < best[0]:
                    best = (cost, i, (x, c), 'h')
            return best
        def vertical(pool):
            best = None
            for i in pool:
                t, c, lo, hi = self.axis(self.d[i])
                if t != 'v' or (side == 0 and hi < p[1]) or (side == 1 and lo > p[1]):
                    continue
                y = min(max(p[1], lo + 0.2), hi - 0.2)
                cost = abs(c - p[0]) + 3 * abs(y - p[1])
                if best is None or cost < best[0]:
                    best = (cost, i, (c, y), 'v')
            return best
        def cercana(pool):   # sin canaleta de ese lado: la mas cercana
            best = None
            for i in pool:
                t, c, lo, hi = self.axis(self.d[i])
                q = (min(max(p[0], lo), hi), c) if t == 'h' else (c, min(max(p[1], lo), hi))
                cost = math.dist(p, q)
                if best is None or cost < best[0]:
                    best = (cost, i, q, 'c')
            return best
        best = None
        if ex is not None:
            propias = [i for i in todas if bool(self.d[i]['ex']) == bool(ex)]
            if not ex:
                comunes = propias
                best = horizontal(comunes) or cercana(comunes)
            elif not horizontal(propias):
                h, v = horizontal(todas), vertical(propias)
                best = min((b for b in (h, v) if b), default=None, key=lambda b: b[0])
        return best or horizontal(todas) or cercana(todas)

    def path(self, a, b, ex):
        """camino mas corto; penaliza canaletas del tipo equivocado (azul/intrinseco vs normal)"""
        dist = {a: 0.0}; prev = {}; pq = [(0.0, a)]
        while pq:
            dd, u = heapq.heappop(pq)
            if u == b:
                break
            if dd > dist.get(u, 1e18):
                continue
            for v, L, dex in self.adj.get(u, []):
                nd = dd + L * (1.0 if dex == ex else 6.0)
                if nd < dist.get(v, 1e18):
                    dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
        if b not in dist:
            return None
        out = [b]
        while out[-1] != a:
            out.append(prev[out[-1]])
        return [self.nodes[k] for k in reversed(out)]

    def _stub(self, j, e, L):
        """tramo fijo j -> e (sale de la canaleta hacia el lateral) de largo L"""
        if (j, e) not in [(a, b) for a, b, _ in self.extra]:
            self.extra.append((j, e, L)); self._link_all()
        return e

    def li_exit(self, abajo, ex=False, lado='izq'):
        """Salida a LI (regla del taller) por el lateral ('izq', o 'der' para el lateral derecho):
        a) canaleta vertical en el borde de la red, del lado del lateral (75441): sale por su borde exterior a la
           altura de sus uniones en T con las canaletas horizontales;
        b) si no hay, por el extremo de las canaletas horizontales que llegan a ese borde (66817).
        La de arriba para todos los cables, la de abajo para marron y blanco (220 VAC).
        Los intrinsecos (ex) salen por su canaleta si alguna llega al borde; si no, por la comun."""
        W = self.w; tol = TOQUE_W * W; izq = lado != 'der'
        borde = min(d['b'][0] for d in self.d) if izq else max(d['b'][2] for d in self.d)   # borde de la red
        en_borde = lambda d: d['b'][0] <= borde + BORDE_W * W if izq else d['b'][2] >= borde - BORDE_W * W
        out = lambda x: x - SALIDA_W * W if izq else x + SALIDA_W * W
        cy = lambda d: (d['b'][1] + d['b'][3]) / 2
        for tipo in ((True, False) if ex else (False,)):
            pool = [d for d in self.d if bool(d['ex']) == tipo]
            # a) vertical del borde con uniones en T
            vs = [d for d in pool if not d['h'] and en_borde(d)]
            if vs:
                v = min(vs, key=lambda d: d['b'][0]) if izq else max(vs, key=lambda d: d['b'][2])
                vx0, vx1 = v['b'][0], v['b'][2]; vcx = (vx0 + vx1) / 2
                ts = [d for d in pool if d['h'] and abs((d['b'][0] - vx1) if izq else (d['b'][2] - vx0)) < tol
                      and v['b'][1] <= cy(d) <= v['b'][3]]
                if ts:
                    ts.sort(key=lambda d: -cy(d))                           # de arriba hacia abajo
                    t = ts[-1] if abajo else ts[0]
                    j = self._node((vcx, cy(t)))                            # union en T (ya existe)
                    xe = out(vx0 if izq else vx1)
                    return self._stub(j, self._node((xe, cy(t))), abs(vcx - xe))
            # b) horizontales que llegan al borde
            hs = [d for d in pool if d['h'] and en_borde(d)]
            if hs:
                t = (min if abajo else max)(hs, key=cy)
                x = t['b'][0] + 0.1 if izq else t['b'][2] - 0.1                # extremo del eje (ya existe)
                xe = out(t['b'][0] if izq else t['b'][2])
                return self._stub(self._node((x, cy(t))), self._node((xe, cy(t))), abs(x - xe))
        # respaldo: extremo de la canaleta comun horizontal de mas arriba (o de mas abajo)
        hs = [(i, self.axis(d)) for i, d in enumerate(self.d) if self.axis(d)[0] == 'h' and not d['ex']]
        if not hs:
            return None
        i, (t, c, lo, hi) = (min if abajo else max)(hs, key=lambda t: t[1][1])
        return self._node((lo + 0.1, c) if izq else (hi - 0.1, c))

    def en_red(self, p):
        """punto p elegido a mano (clic en el topografico) -> (nodo, canaleta): el punto del eje de la canaleta que lo
        contiene (o de la mas cercana, si cae afuera de todas), agregado a la red; (None, None) sin canaletas"""
        best = None
        for i, d in enumerate(self.d):
            t, c, lo, hi = self.axis(d)
            q = (min(max(p[0], lo + 0.1), hi - 0.1), c) if t == 'h' else (c, min(max(p[1], lo + 0.1), hi - 0.1))
            x0, y0, x1, y1 = d['b']
            cost = (0 if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 else 1, math.dist(p, q))
            if best is None or cost < best[0]:
                best = (cost, i, q)
        if best is None:
            return None, None
        _, i, q = best
        k = self._node(q)
        if k not in self.pts[i]:
            self.pts[i].append(k); self._link_all()
        return k, i

    def salida_a_mano(self, p):
        """salida a LI / LD elegida a mano (p = por donde salen los cables de la bandeja) -> (nodo, tramo final): el
        cable va por las canaletas hasta el eje de la canaleta de p y sale derecho hasta p: siguiendo el eje si p esta
        mas alla de la punta de la canaleta, o perpendicular si esta al costado. Con p adentro de la canaleta, el cable
        termina ahi."""
        k, i = self.en_red(p)
        if k is None:
            return None, []
        q = self.nodes[k]
        t, c, lo, hi = self.axis(self.d[i])
        x0, y0, x1, y1 = self.d[i]['b']
        a = p[0] if t == 'h' else p[1]
        if a < lo or a > hi:                                   # mas alla de la punta: sigue el eje
            fin = (p[0], c) if t == 'h' else (c, p[1])
        elif not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1):      # al costado: sale perpendicular
            fin = (q[0], p[1]) if t == 'h' else (p[0], q[1])
        else:
            fin = None
        return k, ([fin] if fin and math.dist(fin, q) > 0.3 else [])


def route_line(net, o_pt, o_side, d_pt, d_side, ex, to_li, abajo_li, lado_li='izq', por=None, o_lat=None, d_lat=None,
               o_red=False, d_red=False):
    """polilinea del cable: borne -> canaleta -> ... -> canaleta -> borne (o salida a LI).
    por = recorrido elegido a mano para la salida a LI / LD: puntos por donde pasa el cable, en orden, y el ultimo
    por donde sale de la bandeja (sin por: la regla del taller, li_exit).
    o_lat / d_lat = 'der' | 'izq': la punta es de una bornera en columna al frente y sale en horizontal a la canaleta
    vertical de ese costado (enganche_lateral)
    o_red / d_red = la punta ya esta en el eje de una canaleta (la punta de la canaleta por donde sale el cable hacia un
    empalme, estacion 8): se engancha ahi mismo (en_red), sin el tramo del borne a la canaleta"""
    a, via_o = net.enganche_lateral(o_pt, o_lat, ex) if o_lat else (None, None)
    if o_red:
        a, via_o = net.en_red(o_pt)[0], []
    elif a is None:
        a, via_o = net.enganche(o_pt, o_side, ex)
    paradas = []
    if to_li and por:
        paradas = [net.en_red(p)[0] for p in por[:-1]]
        b, tail = net.salida_a_mano(por[-1])
    elif to_li:
        b = net.li_exit(abajo_li, ex, lado_li)
        tail = []
    else:
        b, via_d = net.enganche_lateral(d_pt, d_lat, ex) if d_lat else (None, None)
        if d_red:
            b, via_d = net.en_red(d_pt)[0], []
        elif b is None:
            b, via_d = net.enganche(d_pt, d_side, ex)
        tail = via_d[::-1] + [d_pt]
    if a is None or b is None or None in paradas:
        return None
    mid = []
    for u, v in zip([a] + paradas, paradas + [b]):
        tramo = net.path(u, v, ex)
        if tramo is None:
            return None
        mid += tramo[1:] if mid else tramo
    pts = [o_pt] + via_o + mid + tail
    clean = [pts[0]]
    for q in pts[1:]:
        if math.dist(q, clean[-1]) > 0.3:
            clean.append(q)
    # quitar puntos intermedios alineados y retrocesos (A -> B -> A)
    out = [clean[0]]
    for i in range(1, len(clean) - 1):
        a, b, c = out[-1], clean[i], clean[i + 1]
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(cross) < 0.5 and ((b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1])) >= 0:
            continue
        out.append(b)
    out.append(clean[-1])
    return [[round(x, 1), round(y, 1)] for x, y in out]


def length(poly):
    return sum(math.dist(a, b) for a, b in zip(poly, poly[1:])) if poly else 0.0
