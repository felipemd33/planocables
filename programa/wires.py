"""Reconstruccion de cables a partir de la geometria vectorial y asignacion de
numero de cable, color y seccion."""
import math, re, collections
from textdec import bbox, DSU, sub_bbox

NUM_RE = re.compile(r'(?<![\w/,.])(\d{3,5})(?![\w/,.])')
# (el parentesis de apertura puede faltar si la etiqueta empieza el renglon o va tras un espacio: 66817 hoja 11 'G-Y/2,5mm2)')
LABEL_RE = re.compile(r'(?:[\(<{\[]|(?<![^\s]))\s*([A-Za-zÁÉÍÓÚáéíóúñÑ\- ]+?)\s*/\s*([\d]+(?:[.,]\d+)?)\s*mm2?(?:\s+([^\)>}\]\(/]{1,20}?))?\s*[\)>}\]]', re.I)
NON_WIRE_LAYER_KEYS = ('Texto Rotulo', 'TEXTO', 'Textos', 'WATERMARK', 'VP', '|', 'PDF_Text', '_Equipos')
NON_WIRE_LAYERS = {'0', '03', '05'}
COLORES = {'rojo': 'Rojo', 'negro': 'Negro', 'azul': 'Azul', 'blanco': 'Blanco', 'marron': 'Marrón', 'marrón': 'Marrón',
           'gris': 'Gris', 'verde': 'Verde', 'amarillo': 'Amarillo', 'a-v': 'Verde-Amarillo', 'v-a': 'Verde-Amarillo',
           'violeta': 'Violeta', 'naranja': 'Naranja', 'celeste': 'Celeste', 'rosa': 'Rosa',
           # planos en ingles (66817): mismos nombres que usa el instructivo (N/R/B/A... y Azul = intrinsecamente seguro)
           'red': 'Rojo', 'black': 'Negro', 'blue': 'Azul', 'white': 'Blanco', 'brown': 'Marrón', 'grey': 'Gris', 'gray': 'Gris',
           'green': 'Verde', 'yellow': 'Amarillo', 'g-y': 'Verde-Amarillo', 'y-g': 'Verde-Amarillo', 'green-yellow': 'Verde-Amarillo',
           'yellow-green': 'Verde-Amarillo', 'gn-ye': 'Verde-Amarillo', 'violet': 'Violeta', 'purple': 'Violeta', 'orange': 'Naranja',
           'pink': 'Rosa', 'light blue': 'Celeste', 'lightblue': 'Celeste'}


def is_wire_layer(l):
    return l not in NON_WIRE_LAYERS and not any(k in l for k in NON_WIRE_LAYER_KEYS)


def seglen(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def point_seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)), t


def box_dist(pt, bb):
    dx = max(bb[0] - pt[0], 0, pt[0] - bb[2]); dy = max(bb[1] - pt[1], 0, pt[1] - bb[3])
    return math.hypot(dx, dy)


def inside(pt, bb, m=0.0):
    return bb[0] - m <= pt[0] <= bb[2] + m and bb[1] - m <= pt[1] <= bb[3] + m


class WireGraph:
    def __init__(self, strokes, text_lines, H=7.93, keep_dashed=()):
        self.H = H
        self.keep_dashed = set(keep_dashed)   # lineas discontinuas que son cables (cableado opcional): se dejan como tramo
        by_id = {id(p): p for _, _, p in strokes}
        self._by_id = by_id
        text_ids = set()
        for l in text_lines:
            ids = set(l.get('ids') or ())
            if len(l['text'].strip()) <= 1 and len(ids) == 1:
                p = by_id.get(next(iter(ids)))
                if p is not None and len(p) == 2 and seglen(p[0], p[1]) > 0.9 * H:
                    continue   # una raya recta suelta ('I', 'l', '-') es un tramo de cable, no una letra
            text_ids |= ids
        segs = []; self.path_ends = []; self.claimed_dashes = []
        self.dash_ids = set()   # trazos que son rayas de una discontinua conservada (no son letras aunque el texto los tome)
        for layer, op, pts in strokes:
            if op not in ('S', 's') or not is_wire_layer(layer) or len(pts) < 2:
                continue
            long_straight = len(pts) == 2 and seglen(pts[0], pts[1]) > 1.4 * H
            if id(pts) in text_ids and not is_hop(pts, H) and not long_straight and not long_ortho(pts, H):
                if len(pts) == 2:
                    self.claimed_dashes.append((pts[0], pts[1], layer))   # ¿raya de una discontinua leida como 'l', '-' o '/'?
                continue  # trazo usado por un texto (un arco de salto o un tramo recto largo nunca es una letra)
            pts = hop_to_chord(pts, H)
            self.path_ends += [pts[0], pts[-1]]
            for a, b in zip(pts, pts[1:]):
                if seglen(a, b) > 0.05:
                    segs.append((a, b, layer))
        segs += self._through_squares(strokes, text_ids)
        hosts = self._merge_collinear(segs)
        self.dash_runs = self._dash_runs(segs + self.claimed_dashes)
        if self.keep_dashed:   # un cable en linea discontinua tambien lleva rayas de corte
            hosts = hosts + [(r['a'], r['b'], r['layer']) for r in self.dash_runs if self._kept(r)]
        self.ticks, segs = self._find_ticks(segs, hosts)
        segs = self._drop_dashes(segs)
        if self.keep_dashed:   # las discontinuas conservadas quedan como un tramo continuo
            kept = [r for r in self.dash_runs if self._kept(r)]
            # salto (arco) de una discontinua sobre otro cable: dos tramos de la misma recta separados menos de 3H
            kept.sort(key=lambda r: (r['ang'], r['off'], r['lo']))
            for r, q in zip(kept, kept[1:]):
                if abs(r['ang'] - q['ang']) <= 2 and abs(r['off'] - q['off']) < 0.8 and 0 < q['lo'] - r['hi'] < 3 * H:
                    ends = sorted([(r['a'], q['a']), (r['a'], q['b']), (r['b'], q['a']), (r['b'], q['b'])], key=lambda t: seglen(*t))
                    segs.append((ends[0][0], ends[0][1], r['layer']))   # la cuerda del salto, como en hop_to_chord
            segs = [sg for sg in segs if not any(on_run(sg, r) for r in kept)] + [(r['a'], r['b'], r['layer']) for r in kept]
            self.path_ends += [p for r in kept for p in (r['a'], r['b'])]
            self.dash_ids |= {id(pts) for layer, op, pts in strokes if op in ('S', 's') and len(pts) == 2 and is_wire_layer(layer)
                              and any(on_run((pts[0], pts[1], layer), r) for r in kept)}
            segs = self._trace_dashed(segs, kept, strokes)
        segs = self._merge_collinear(segs)
        self.segs = self._split_T(segs)
        self._build()

    # --- tramo de una discontinua conservada que no forma 'linea' (saltos dibujados con rayas curvas, quiebre en diagonal)
    def _trace_dashed(self, segs, kept, strokes):
        """desde la punta suelta de una discontinua conservada se siguen las rayas sueltas (rectas o trozos de arco, tambien
        las que tomo un texto) punta con punta, con huecos de raya, hasta llegar a un cable lleno: es la derivacion
        discontinua que baja de ese cable saltando sobre otros (66817 hoja 81: 8101/8102 hacia 81TM01). Si no llega a un
        cable lleno no se toca nada."""
        H = self.H
        pieces = []
        for layer, op, pts in strokes:
            if op not in ('S', 's') or not is_wire_layer(layer) or not 2 <= len(pts) <= 6 or seglen(pts[0], pts[-1]) < 0.3:
                continue
            x0, y0, x1, y1 = bbox(pts)
            if max(x1 - x0, y1 - y0) <= 1.5 * H:
                pieces.append((layer, [tuple(q) for q in pts], id(pts)))
        if not pieces:
            return segs
        C = 2 * H; grid = collections.defaultdict(list)
        runsegs0 = [(r['a'], r['b']) for r in kept]
        on_kept = lambda q: any(point_seg_dist(q, a, b)[0] < 0.3 for a, b in runsegs0)
        for i, (_, pts, _) in enumerate(pieces):
            if on_kept(pts[0]) and on_kept(pts[-1]):
                continue   # raya de la propia discontinua conservada (ya es tramo): seguirla es volver por el mismo camino
            for q in (pts[0], pts[-1]):
                grid[(int(q[0] // C), int(q[1] // C))].append(i)
        near_pieces = lambda c: {i for dx in (-1, 0, 1) for dy in (-1, 0, 1) for i in grid.get((int(c[0] // C) + dx, int(c[1] // C) + dy), [])}
        short = lambda sg: seglen(sg[0], sg[1]) <= 1.5 * H
        solid = [sg for sg in segs if seglen(sg[0], sg[1]) > 3 * H and not any(on_run(sg, r) for r in kept)]
        runsegs = [(r['a'], r['b']) for r in kept]
        used = set(); add = []
        for r in kept:
            for e in (r['a'], r['b']):
                # punta suelta: nada que no sea una raya suelta llega ahi (ni otra punta ni un cable que pase)
                if any(not short(sg) and not (seglen(sg[0], r['a']) < 0.05 and seglen(sg[1], r['b']) < 0.05) and
                       (min(seglen(e, sg[0]), seglen(e, sg[1])) < 0.6 or point_seg_dist(e, sg[0], sg[1])[0] < 0.3) for sg in segs):
                    continue
                c = e; path = [e]; seen = set(); total = 0.0; fin = None
                for _ in range(80):
                    best = None
                    for i in near_pieces(c):
                        if i in seen or i in used or pieces[i][0] != r['layer']:
                            continue
                        pts = pieces[i][1]
                        for q0, orient in ((pts[0], pts), (pts[-1], pts[::-1])):
                            d = seglen(c, q0)
                            if d < 0.8 * H and (best is None or d < best[0]):
                                best = (d, i, orient)
                    if best is None:
                        break
                    d, i, orient = best
                    seen.add(i); path += orient; total += d + sum(seglen(a, b) for a, b in zip(orient, orient[1:]))
                    c = orient[-1]
                    if total > 40 * H:
                        break
                    if any(point_seg_dist(c, a, b)[0] < 0.3 for a, b, _ in solid) and not any(point_seg_dist(c, a, b)[0] < 0.3 for a, b in runsegs):
                        fin = c
                        break
                if fin is None or len(seen) < 2:
                    continue
                used |= seen
                self.dash_ids |= {pieces[i][2] for i in seen}
                pts = [path[0]]
                for q in path[1:]:
                    if seglen(q, pts[-1]) > 0.05:
                        pts.append(q)
                add += [(a, b, r['layer']) for a, b in zip(pts, pts[1:])]
                self.path_ends += [pts[0], pts[-1]]
        if not used:
            return segs
        # las rayas recorridas ya no son tramos sueltos
        mine = {(round(a[0], 2), round(a[1], 2), round(b[0], 2), round(b[1], 2)) for i in used for a, b in zip(pieces[i][1], pieces[i][1][1:])}
        k = lambda a, b: (round(a[0], 2), round(a[1], 2), round(b[0], 2), round(b[1], 2))
        segs = [sg for sg in segs if k(sg[0], sg[1]) not in mine and k(sg[1], sg[0]) not in mine]
        return segs + add

    # --- cuadradito negro (puntera / borne de un equipo) intercalado en un cable
    def _through_squares(self, strokes, text_ids):
        """un cable que entra por un lado de un cuadradito relleno y sale por el lado opuesto sigue siendo el mismo
        cable (66817 hoja 12: bornes del cargador 12PS1): se une con la cuerda que atraviesa el cuadrado"""
        H = self.H; out = []
        rects = []
        for layer, op, pts in strokes:
            if not is_wire_layer(layer) or len(pts) < 4 or op not in ('f', 'F', 'f*', 'B', 'B*', 'b', 'b*'):
                continue
            x0, y0, x1, y1 = bbox(pts)
            if 0.5 < x1 - x0 < 1.5 * H and 0.5 < y1 - y0 < 1.5 * H and                     all(abs(a[0] - b[0]) < 0.05 or abs(a[1] - b[1]) < 0.05 for a, b in zip(pts, pts[1:])):
                rects.append((x0, y0, x1, y1, layer))
        if not rects:
            return out
        ends = self.path_ends
        for x0, y0, x1, y1, layer in rects:
            m = 0.4
            top = [p for p in ends if abs(p[1] - y1) < m and x0 - m < p[0] < x1 + m]
            bot = [p for p in ends if abs(p[1] - y0) < m and x0 - m < p[0] < x1 + m]
            lef = [p for p in ends if abs(p[0] - x0) < m and y0 - m < p[1] < y1 + m]
            rig = [p for p in ends if abs(p[0] - x1) < m and y0 - m < p[1] < y1 + m]
            for A, B in ((top, bot), (lef, rig)):
                for p in A:
                    tol = 0.25 * min(x1 - x0, y1 - y0)   # entra y sale casi alineado (el CAD corre 0.3 pt)
                    q = next((q for q in B if (abs(q[0] - p[0]) < tol if A is top else abs(q[1] - p[1]) < tol)), None)
                    if q is not None:
                        out.append((p, q, layer))
        return out

    # --- rayas de corte: segmento corto cuyo punto medio cae sobre un cable perpendicular
    def _find_ticks(self, segs, hosts):
        H = self.H; ticks = []; keep = []
        longs = [s for s in hosts if seglen(s[0], s[1]) > 1.7 * H]
        grid = collections.defaultdict(list); C = 40.0
        for i, (a, b, _) in enumerate(longs):
            x0, y0, x1, y1 = bbox([a, b])
            for gx in range(int(x0 // C), int(x1 // C) + 1):
                for gy in range(int(y0 // C), int(y1 // C) + 1):
                    grid[(gx, gy)].append(i)
        for s in segs:
            a, b, _ = s; L = seglen(a, b)
            if 0.9 * H <= L <= 1.65 * H:
                m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                hit = None
                for i in grid.get((int(m[0] // C), int(m[1] // C)), []):
                    c, d, _ = longs[i]; Ld = seglen(c, d)
                    vx, vy = (d[0] - c[0]) / Ld, (d[1] - c[1]) / Ld
                    dist, t = point_seg_dist(m, c, d)
                    if dist < 1.2 and abs(ux * vx + uy * vy) < 0.1 and 0 < t < 1:
                        hit = i; break
                if hit is not None:
                    c, d, _ = longs[hit]
                    ticks.append(dict(p=m, seg=longs[hit], horiz_wire=abs(d[1] - c[1]) < abs(d[0] - c[0])))
                    continue
            keep.append(s)
        return ticks, keep

    # --- lineas discontinuas: >=3 segmentos colineales de igual longitud separados por huecos
    def _drop_dashes(self, segs):
        H = self.H
        buckets = collections.defaultdict(list)
        for i, (a, b, l) in enumerate(segs):
            L = seglen(a, b)
            if L > 3 * H:
                continue
            if abs(a[0] - b[0]) < 0.05:
                buckets[('v', round(a[0], 1), round(L, 1))].append((min(a[1], b[1]), max(a[1], b[1]), i))
            elif abs(a[1] - b[1]) < 0.05:
                buckets[('h', round(a[1], 1), round(L, 1))].append((min(a[0], b[0]), max(a[0], b[0]), i))
        drop = set()
        for k, v in buckets.items():
            if len(v) < 3:
                continue
            v.sort(); run = [v[0]]
            for iv in v[1:]:
                if 0.2 < iv[0] - run[-1][1] < 1.0 * k[2]:
                    run.append(iv)
                else:
                    if len(run) >= 4: drop.update(x[2] for x in run)
                    run = [iv]
            if len(run) >= 4: drop.update(x[2] for x in run)
        return [s for i, s in enumerate(segs) if i not in drop]

    def _dash_runs(self, segs):
        """lineas discontinuas (para decidir si alguna es un cable): rayas cortas encadenadas punta con punta, en la
        misma direccion y sobre la misma recta, con huecos menores que una raya (en cualquier direccion: tambien el
        quiebre en diagonal de una derivacion). Tolerante al redondeo del CAD (rayas de 3.5/3.6, x=1077.0/1077.1)."""
        H = self.H
        ds = []
        for a, b, l in segs:
            L = seglen(a, b)
            if 0.12 * H < L <= 3 * H:   # (sin los cuadraditos de 0.14 que el CAD pone en las esquinas)
                ds.append((a, b, l, L, ((b[0] - a[0]) / L, (b[1] - a[1]) / L)))
        if not ds:
            return []
        grid = collections.defaultdict(list); C = 3 * H
        for i, (a, b, *_ ) in enumerate(ds):
            for p in (a, b):
                grid[(int(p[0] // C), int(p[1] // C))].append(i)
        d = DSU(len(ds))
        for i, (a, b, l, L, u) in enumerate(ds):
            for p in (a, b):
                gx, gy = int(p[0] // C), int(p[1] // C)
                for j in {j for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in grid.get((gx + dx, gy + dy), [])}:
                    if j <= i or ds[j][2] != l:
                        continue
                    a2, b2, _, L2, u2 = ds[j]
                    if abs(u[0] * u2[0] + u[1] * u2[1]) < 0.99:          # misma direccion (+-8 grados)
                        continue
                    axis = abs(u[0]) < 0.01 or abs(u[1]) < 0.01
                    tol = 0.3 if axis else 0.6
                    if max(point_line_dist(a2, a, u), point_line_dist(b2, a, u)) > tol:
                        continue
                    gap = min(seglen(p1, p2) for p1 in (a, b) for p2 in (a2, b2))
                    if 0.15 < gap < 1.3 * max(L, L2):
                        d.u(i, j)
        groups = collections.defaultdict(list)
        for i in range(len(ds)):
            groups[d.f(i)].append(i)
        out = []
        for g in groups.values():
            Ls = sorted(ds[i][3] for i in g); med = Ls[len(Ls) // 2]
            u = ds[g[0]][4]
            axis = abs(u[0]) < 0.01 or abs(u[1]) < 0.01
            if sum(1 for x in Ls if abs(x - med) <= 0.25 * med) < (4 if axis else 3):
                continue
            if u[0] < -0.01 or (abs(u[0]) <= 0.01 and u[1] < 0):
                u = (-u[0], -u[1])
            pts = [p for i in g for p in ds[i][:2]]
            o = pts[0]
            ts = [(p[0] - o[0]) * u[0] + (p[1] - o[1]) * u[1] for p in pts]
            a = pts[ts.index(min(ts))]; b = pts[ts.index(max(ts))]
            if abs(u[1]) < 0.01:
                kind, c = 'h', sum(p[1] for p in pts) / len(pts); a, b = (a[0], c), (b[0], c)
            elif abs(u[0]) < 0.01:
                kind, c = 'v', sum(p[0] for p in pts) / len(pts); a, b = (c, a[1]), (c, b[1])
            else:
                kind = 'd'
            ang = round(math.degrees(math.atan2(u[1], u[0])) % 180)
            off = round(-u[1] * a[0] + u[0] * a[1], 1)
            lo, hi = sorted((u[0] * a[0] + u[1] * a[1], u[0] * b[0] + u[1] * b[1]))
            out.append(dict(a=a, b=b, kind=kind, layer=ds[g[0]][2], n=len(g), ang=ang, off=off, lo=lo, hi=hi))
        out.sort(key=lambda r: (r['ang'], r['off'], r['lo']))
        return out

    @staticmethod
    def run_key(r):
        return (r['ang'], r['off'], round(r['lo'], 1), round(r['hi'], 1))

    def _kept(self, r):
        k, c, lo, hi = self.run_key(r)
        return any(abs(k - k2) <= 2 and abs(c - c2) < 0.8 and lo < hi2 and lo2 < hi for k2, c2, lo2, hi2 in self.keep_dashed)

    # --- fusionar segmentos horizontales/verticales superpuestos (dibujados dos veces)
    def _merge_collinear(self, segs):
        rows = collections.defaultdict(list); out = []
        for a, b, l in segs:
            if abs(a[1] - b[1]) < 0.05:
                rows[('h', round((a[1] + b[1]) / 2, 1))].append((min(a[0], b[0]), max(a[0], b[0]), l))
            elif abs(a[0] - b[0]) < 0.05:
                rows[('v', round((a[0] + b[0]) / 2, 1))].append((min(a[1], b[1]), max(a[1], b[1]), l))
            else:
                out.append((a, b, l))
        for (kind, c), ivs in rows.items():
            ivs.sort(); cur = list(ivs[0])
            for s, e, l in ivs[1:]:
                if s <= cur[1] + 0.05:
                    cur[1] = max(cur[1], e)
                else:
                    out.append(self._mk(kind, c, cur)); cur = [s, e, l]
            out.append(self._mk(kind, c, cur))
        return out

    @staticmethod
    def _mk(kind, c, iv):
        s, e, l = iv
        return ((s, c), (e, c), l) if kind == 'h' else ((c, s), (c, e), l)

    # --- dividir segmentos donde otro cable termina sobre ellos (union en T)
    def _split_T(self, segs):
        # solo los extremos reales de un trazo forman union en T (no los vertices
        # intermedios, p.ej. la cima del arco con que un cable salta sobre otro)
        ends = self.path_ends
        grid = collections.defaultdict(list); C = 40.0
        for p in ends:
            grid[(int(p[0] // C), int(p[1] // C))].append(p)
        out = []
        for a, b, l in segs:
            x0, y0, x1, y1 = bbox([a, b]); cuts = []
            for gx in range(int(x0 // C) - 1, int(x1 // C) + 2):
                for gy in range(int(y0 // C) - 1, int(y1 // C) + 2):
                    for p in grid.get((gx, gy), []):
                        d, t = point_seg_dist(p, a, b)
                        if d < 0.3 and 0.001 < t < 0.999 and seglen(p, a) > 0.3 and seglen(p, b) > 0.3:
                            cuts.append(t)
            pts = [a] + [(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])) for t in sorted(set(round(c, 6) for c in cuts))] + [b]
            for p, q in zip(pts, pts[1:]):
                out.append((p, q, l))
        return out

    def _build(self):
        # agrupar extremos que coinciden (tolerancia 0.35 pt) en nodos
        pts = [p for a, b, _ in self.segs for p in (a, b)]
        cell = collections.defaultdict(list)
        for i, p in enumerate(pts):
            cell[(int(p[0] // 1), int(p[1] // 1))].append(i)
        d = DSU(len(pts))
        for (cx, cy), lst in cell.items():
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for j in cell.get((cx + dx, cy + dy), []):
                        for i in lst:
                            if i < j and abs(pts[i][0] - pts[j][0]) < 0.6 and abs(pts[i][1] - pts[j][1]) < 0.6:
                                d.u(i, j)
        pid = {}
        for i, p in enumerate(pts):
            pid[(round(p[0], 4), round(p[1], 4))] = d.f(i)
        key = lambda p: pid.get((round(p[0], 4), round(p[1], 4)), (round(p[0], 1), round(p[1], 1)))
        nodes = {}
        for p in pts:
            nodes.setdefault(key(p), p)
        self.nodes = nodes
        self.adj = collections.defaultdict(list)
        for i, (a, b, _) in enumerate(self.segs):
            ka, kb = key(a), key(b)
            if ka == kb: continue
            self.adj[ka].append((kb, i)); self.adj[kb].append((ka, i))
        self.key = key
        # tramos: recorrer por nodos de grado 2
        seg_chain = {}; chains = []
        for i, (a, b, _) in enumerate(self.segs):
            if i in seg_chain or key(a) == key(b):
                continue
            cid = len(chains); ch = [i]; seg_chain[i] = cid
            for start in (key(a), key(b)):
                prev_seg = i; node = start
                while len(self.adj[node]) == 2:
                    nxt = [(n, s) for n, s in self.adj[node] if s != prev_seg]
                    if not nxt: break
                    n, s = nxt[0]
                    if s in seg_chain: break
                    seg_chain[s] = cid; ch.append(s); prev_seg = s; node = n
            chains.append(ch)
        self.chains = chains; self.seg_chain = seg_chain
        # redes: componentes conexas
        d = DSU(len(chains))
        for node, lst in self.adj.items():
            cs = {seg_chain[s] for _, s in lst if s in seg_chain}
            cs = list(cs)
            for c in cs[1:]:
                d.u(cs[0], c)
        self.chain_net = [d.f(c) for c in range(len(chains))]
        # tramos que vienen de una linea discontinua conservada (cableado opcional)
        self.dashed_chains = set()
        kept = [r for r in getattr(self, 'dash_runs', []) if self._kept(r)] if self.keep_dashed else []
        for i, (a, b, _) in enumerate(self.segs):
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if any(point_seg_dist(m, r['a'], r['b'])[0] < 0.05 for r in kept) and i in seg_chain:
                self.dashed_chains.add(seg_chain[i])
        # rejilla de segmentos para busquedas
        self.grid = collections.defaultdict(list); C = 40.0
        for i, (a, b, _) in enumerate(self.segs):
            x0, y0, x1, y1 = bbox([a, b])
            for gx in range(int(x0 // C), int(x1 // C) + 1):
                for gy in range(int(y0 // C), int(y1 // C) + 1):
                    self.grid[(gx, gy)].append(i)

    def dashed_wanted(self, nums, labels):
        """lineas discontinuas que hay que conservar como cable: las que llevan una etiqueta de color o un numero que
        no encontro cable, o que continuan la punta suelta de un tramo numerado (cableado opcional, p.ej. telemetria).
        Se devuelve la linea completa (todas las rayas unidas por esquinas)."""
        runs = getattr(self, 'dash_runs', [])
        if not runs:
            return set()
        H = self.H

        def rdist(r, bb):
            if r['kind'] not in ('h', 'v'):
                cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
                return max(0.0, point_seg_dist((cx, cy), r['a'], r['b'])[0] - 0.5 * math.hypot(bb[2] - bb[0], bb[3] - bb[1]))
            if r['kind'] == 'h':
                c, lo, hi = r['a'][1], min(r['a'][0], r['b'][0]), max(r['a'][0], r['b'][0])
                return math.hypot(max(lo - bb[2], 0, bb[0] - hi), max(bb[1] - c, 0, c - bb[3]))
            c, lo, hi = r['a'][0], min(r['a'][1], r['b'][1]), max(r['a'][1], r['b'][1])
            return math.hypot(max(bb[0] - c, 0, c - bb[2]), max(lo - bb[3], 0, bb[1] - hi))
        seeds = set()
        for lb in labels:
            if lb['chain'] is not None:
                continue
            horiz = lb['line']['ang'] in (0, 180)
            for rid, r in enumerate(runs):
                if (r['kind'] == 'h') == horiz and rdist(r, lb['bbox']) <= 1.8 * H:
                    seeds.add(rid)
        for n in nums:
            if n['chain'] is not None or not n['whole']:
                continue
            for rid, r in enumerate(runs):
                if rdist(r, n['bbox']) <= 2.2 * H:
                    seeds.add(rid)
        for c in {n['chain'] for n in nums if n['chain'] is not None}:
            for k in self.chain_end_keys(c):
                if len(self.adj[k]) != 1:
                    continue
                p = self.nodes[k]
                for rid, r in enumerate(runs):
                    if min(seglen(p, r['a']), seglen(p, r['b'])) < 0.6:
                        seeds.add(rid)
        if not seeds:
            return set()
        d = DSU(len(runs))
        for i, r in enumerate(runs):
            for j in range(i + 1, len(runs)):
                q = runs[j]
                if r['layer'] != q['layer']:
                    continue
                touch = min(seglen(p1, p2) for p1 in (r['a'], r['b']) for p2 in (q['a'], q['b'])) < 0.6
                tee = any(point_seg_dist(p, q['a'], q['b'])[0] < 0.3 for p in (r['a'], r['b'])) or any(point_seg_dist(p, r['a'], r['b'])[0] < 0.3 for p in (q['a'], q['b']))
                hop = abs(r['ang'] - q['ang']) <= 2 and abs(r['off'] - q['off']) < 0.8 and (0 < q['lo'] - r['hi'] < 3 * H or 0 < r['lo'] - q['hi'] < 3 * H)   # salto sobre otro cable
                if touch or tee or hop:
                    d.u(i, j)
        roots = {d.f(i) for i in seeds}
        return {self.run_key(runs[i]) for i in range(len(runs)) if d.f(i) in roots}

    def dash_text(self, line):
        """renglon 'leido' en las rayas de una discontinua conservada (66817 hoja 21: la bajada discontinua de 8102 se leia
        '1' y quedaba como borne '21PCB01 1'): todos sus trazos (sin contar los puntitos de las esquinas) son rayas del cable"""
        if not self.dash_ids:
            return False
        by_id = self._by_id
        ps = [by_id[i] for i in (line.get('ids') or ()) if i in by_id]
        ps = [p for p in ps if max(bbox(p)[2] - bbox(p)[0], bbox(p)[3] - bbox(p)[1]) > 0.3]
        return bool(ps) and all(id(p) in self.dash_ids for p in ps)

    def lone_short(self, seg):
        """segmento suelto del largo de una raya de corte (tramo de un solo segmento, sin nada en sus puntas)"""
        c = self.seg_chain.get(seg)
        if c is None or len(self.chains[c]) != 1:
            return False
        a, b, _ = self.segs[seg]
        return seglen(a, b) < 1.7 * self.H and all(len(self.adj[k]) == 1 for k in self.chain_end_keys(c))

    def near_segs(self, p, r):
        C = 40.0; out = set()
        for gx in range(int((p[0] - r) // C), int((p[0] + r) // C) + 1):
            for gy in range(int((p[1] - r) // C), int((p[1] + r) // C) + 1):
                out.update(self.grid.get((gx, gy), []))
        return out

    def chain_ends(self, cid):
        cnt = collections.Counter()
        for s in self.chains[cid]:
            a, b, _ = self.segs[s]
            cnt[self.key(a)] += 1; cnt[self.key(b)] += 1
        ends = [k for k, v in cnt.items() if v == 1]
        return [self.nodes[k] for k in ends]

    def straight_neighbors(self, cid):
        """tramos que continuan en linea recta a traves de una union en T (mismo conductor)"""
        out = []
        mine = set(self.chains[cid])
        for s in self.chains[cid]:
            a, b, _ = self.segs[s]
            for node, other in ((self.key(a), b), (self.key(b), a)):
                nb = self.adj.get(node, [])
                if len(nb) < 3:
                    continue
                # direcciones con los propios segmentos (no con la posicion del nodo: al juntar puntas cercanas el nodo
                # puede quedar corrido unas decimas del cable, y en un tramo corto eso tuerce la direccion)
                p = a if node == self.key(a) else b
                vx, vy = p[0] - other[0], p[1] - other[1]; L = math.hypot(vx, vy) or 1
                for n2, s2 in nb:
                    if s2 in mine:
                        continue
                    c2, d2, _ = self.segs[s2]
                    p2, q = (c2, d2) if self.key(c2) == node else (d2, c2)
                    wx, wy = q[0] - p2[0], q[1] - p2[1]; M = math.hypot(wx, wy) or 1
                    if (vx * wx + vy * wy) / (L * M) > 0.995:   # misma direccion, sigue recto
                        out.append(self.seg_chain.get(s2))
        return [c for c in out if c is not None and c != cid]

    def chain_end_keys(self, cid):
        cnt = collections.Counter()
        for s in self.chains[cid]:
            a, b, _ = self.segs[s]
            cnt[self.key(a)] += 1; cnt[self.key(b)] += 1
        return [k for k, v in cnt.items() if v == 1]

    def route(self, seeds, blocked):
        """Recorrido de un conductor: sus tramos numerados + tramos sin numero que
        (a) siguen recto tras una union o (b) unen dos tramos del recorrido.
        'blocked' = tramos que son de otro conductor (otro numero u otra etiqueta)."""
        route = set(seeds)
        for _ in range(5):
            added = False
            ends = collections.Counter(k for c in route for k in self.chain_end_keys(c))
            for c in list(route):
                for c2 in self.straight_neighbors(c):
                    if c2 not in route and c2 not in blocked:
                        route.add(c2); added = True
            for node in list(ends):
                for _, s2 in self.adj.get(node, []):
                    c2 = self.seg_chain.get(s2)
                    if c2 is None or c2 in route or c2 in blocked:
                        continue
                    if any(k != node and k in ends for k in self.chain_end_keys(c2)):
                        route.add(c2); added = True
            if not added:
                break
        # topologia: extremos (puntas) y uniones en T dentro del recorrido
        cnt = collections.Counter(k for c in route for k in self.chain_end_keys(c))
        ends, joins = [], [self.nodes[k] for k, v in cnt.items() if v >= 3]
        for k, v in cnt.items():
            if v != 1:
                continue
            p = self.nodes[k]
            own = {c for c in route if k in self.chain_end_keys(c)}
            # los tramos que tocan al propio tramo (p.ej. el resto del mismo cable cortado por una raya del recuadro
            # discontinuo de un rele) no cuentan: estan a un tramo de distancia, no a un paso
            own_keys = {k2 for c in own for k2 in self.chain_end_keys(c)}
            near_c = route - own - {c for c in route if own_keys & set(self.chain_end_keys(c))}
            # extremo que se queda a un paso de otro tramo del mismo cable: union en T mal cerrada en el dibujo
            gap = min((point_seg_dist(p, self.segs[s][0], self.segs[s][1])[0] for c in near_c for s in self.chains[c]), default=1e9)
            if gap < 1.6 * self.H:
                joins.append(p)
            else:
                ends.append(p)
        return route, ends, joins

    def chain_length(self, cid):
        return sum(seglen(self.segs[s][0], self.segs[s][1]) for s in self.chains[cid])

    def seg_at_tick(self, tick):
        a, b = tick['seg'][0], tick['seg'][1]
        best = None
        for i in self.near_segs(tick['p'], 2):
            c, d, _ = self.segs[i]
            dist, t = point_seg_dist(tick['p'], c, d)
            if dist < 1.2 and (best is None or dist < best[0]):
                best = (dist, i)
        return best[1] if best else None

    def seg_parallel_near(self, pt, direction, maxd, prefer_side=None):
        """segmento paralelo a 'direction' (0=horizontal, 1=vertical) mas cercano a pt"""
        best = None
        for i in self.near_segs(pt, maxd + 2):
            a, b, _ = self.segs[i]
            dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
            horiz = dy < 0.3 or dy < 0.03 * dx; vert = dx < 0.3 or dx < 0.03 * dy
            if (direction == 0 and not horiz) or (direction == 1 and not vert):
                continue
            dist, t = point_seg_dist(pt, a, b)
            if dist > maxd:
                continue
            if i not in self.seg_chain:
                continue   # segmento degenerado (trazo de una letra sin decodificar): no es un cable
            if prefer_side is not None:
                side = (a[1] - pt[1]) if direction == 0 else (a[0] - pt[0])
                if side * prefer_side < -0.5:
                    continue
            if best is None or dist < best[0]:
                best = (dist, i)
        return best[1] if best else None


def point_line_dist(p, a, u):
    return abs((p[0] - a[0]) * u[1] - (p[1] - a[1]) * u[0])


def on_run(sg, r):
    """el segmento (raya) cae sobre la linea discontinua r"""
    a, b, _ = sg
    # (0.3 como al armar la linea en _dash_runs: una discontinua larga puede venir apenas inclinada, 66817 hoja 81:
    # 0.2 pt de deriva en 127 pt, y la ultima raya quedaba a 0.12 de la recta media y duplicaba el tramo)
    tol = 0.3 if r['kind'] in ('h', 'v') else 0.6
    return point_seg_dist(a, r['a'], r['b'])[0] < tol and point_seg_dist(b, r['a'], r['b'])[0] < tol


def long_ortho(pts, H):
    """polilinea abierta de tramos horizontales/verticales mucho mas grande que una letra: es un cable en L aunque el
    decodificador de texto la haya tomado como letra (capa mixta con la altura de texto mal estimada, p.ej. 66817 hoja 61)"""
    if len(pts) < 3 or seglen(pts[0], pts[-1]) < 0.05:
        return False
    orto = [abs(a[0] - b[0]) < 0.05 or abs(a[1] - b[1]) < 0.05 for a, b in zip(pts, pts[1:])]
    if all(orto):
        x0, y0, x1, y1 = bbox(pts)
        return max(x1 - x0, y1 - y0) > 3 * H
    # con un quiebre en diagonal (derivacion en T dibujada con una diagonal que apunta al borne, 66817 hoja 61: la
    # diagonal + horizontal que baja de 6201 a 6203 se leia 'J'): pocas esquinas (no es una curva muestreada) y un
    # tramo horizontal/vertical mas largo que 3H, que ninguna letra de un texto de cable tiene
    return (len(pts) <= 5 and orto.count(False) <= 2 and
            any(o and seglen(a, b) > 3 * H for o, a, b in zip(orto, pts, pts[1:])))


def is_hop(pts, H):
    """arco de salto: semicirculo (curva muestreada) cuyos extremos estan alineados en horizontal o vertical"""
    if len(pts) < 4:
        return False
    a, b = pts[0], pts[-1]
    L = seglen(a, b)
    if not (1.3 * H <= L <= 3.2 * H) or not (abs(a[0] - b[0]) < 0.3 or abs(a[1] - b[1]) < 0.3):
        return False
    dev = max(point_seg_dist(p, a, b)[0] for p in pts)
    return 0.35 * L <= dev <= 0.65 * L


def hop_to_chord(pts, H):
    """El cable pasa por encima de otro sin conectarse: el arco se sustituye por la cuerda recta
    entre sus extremos, para que el cable siga continuo y la cima del arco no se confunda con una
    conexion con el cable que cruza."""
    return [pts[0], pts[-1]] if is_hop(pts, H) else pts


def _una_letra(a, b):
    """a y b difieren en una sola letra (cambiada, de mas, de menos) o en dos letras vecinas cambiadas de lugar"""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def norm_color(c):
    k = c.strip().lower().replace(' ', '')
    if k in COLORES:
        return COLORES[k]
    # error de tipeo del plano ('Balck' = Black): el color conocido que difiere en una letra, si hay uno solo
    cand = {v for n, v in COLORES.items() if len(n) >= 4 and len(k) >= 4 and _una_letra(k, n)}
    return cand.pop() if len(cand) == 1 else c.strip().capitalize()


def label_anchor(ang, bb):
    """punto del lado del cable (debajo del texto en su orientacion canonica)"""
    x0, y0, x1, y1 = bb
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if ang == 0: return (cx, y0), 0, -1     # cable horizontal debajo
    if ang == 90: return (x1, cy), 1, +1    # texto vertical (lee hacia arriba): cable a la derecha
    if ang == 270: return (x0, cy), 1, -1
    return (cx, y1), 0, +1


def glued_to_word(ln, lines, H):
    """renglon que es solo un numero pero de otra altura que los numeros de cable y pegado (misma linea base, sin
    hueco) a un texto con letras: es el pedazo de una palabra, no un numero de cable"""
    t = ln['text'].strip()
    if not t.isdigit() or abs(ln['H'] / H - 1) < 0.18:
        return False
    for o in lines:
        if o is ln or o['ang'] != ln['ang'] or sum(ch.isalpha() for ch in o['text']) < 2:
            continue
        gap = 1.3 * max(ln['H'], o['H'])
        if abs(o['base'] - ln['base']) < 0.3 * H and (0 <= ln['x0'] - o['x1'] < gap or 0 <= o['x0'] - ln['x1'] < gap):
            return True
    return False


def assign(graph, text_lines, H=7.93):
    """devuelve lista de apariciones: numeros y etiquetas asociados a tramos"""
    nums, labels = [], []
    ticks_used = set()
    for ln in text_lines:
        t = ln['text']
        if ln['ang'] not in (0, 90, 270, 180):
            continue
        for m in LABEL_RE.finditer(t):
            labels.append(dict(line=ln, bbox=sub_bbox(ln, m.start(), m.end()), color=norm_color(m.group(1)),
                               sec=m.group(2).replace('.', ','), raw=m.group(0), extra=(m.group(3) or '').strip()))
        rest = LABEL_RE.sub(' ', t)
        if ln.get('layer') in NON_WIRE_LAYERS:
            continue
        if glued_to_word(ln, text_lines, H):
            continue   # cola de una palabra grande mal leida ('Communication' -> 'ColmIm ul7 ICa' + '1017')
        for m in NUM_RE.finditer(rest):
            if m.group(1).startswith('0'):
                continue   # '0000', 'TT 001', 'PT 002' (burbujas de instrumento del P&ID): los cables del taller no empiezan con 0
            nums.append(dict(line=ln, bbox=sub_bbox(ln, m.start(), m.end()), num=m.group(1), whole=rest.strip() == m.group(1)))
    # numeros: primero por raya de corte cercana
    for n in nums:
        ln = n['line']; bb = n['bbox']
        best = None
        for k, tk in enumerate(graph.ticks):
            d = box_dist(tk['p'], bb)
            if d <= 2.2 * H and (best is None or d < best[0]):
                best = (d, k)
        seg = None
        if best:
            n['tick'] = graph.ticks[best[1]]['p']
            seg = graph.seg_at_tick(graph.ticks[best[1]])
        if seg is None and n['whole']:
            anchor, direction, side = label_anchor(ln['ang'], bb)
            seg = graph.seg_parallel_near(anchor, direction, 1.8 * H, side)
            if seg is None:  # cable perpendicular al lado del texto
                cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
                seg = graph.seg_parallel_near((cx, cy), 1 - direction, 0.5 * (bb[2] - bb[0] if direction == 0 else bb[3] - bb[1]) + 2.5 * H)
        if seg is not None and 'tick' not in n and graph.lone_short(seg):
            seg = None   # la raya de corte suelta de un cable en linea discontinua no es el cable (66817 hoja 81: 8101/8102)
        n['seg'] = seg
        n['chain'] = graph.seg_chain.get(seg) if seg is not None else None
    for lb in labels:
        anchor, direction, side = label_anchor(lb['line']['ang'], lb['bbox'])
        seg = graph.seg_parallel_near(anchor, direction, 1.8 * H, side)
        if seg is None:  # etiqueta al otro lado del cable
            x0, y0, x1, y1 = lb['bbox']
            opp = {0: ((x0 + x1) / 2, y1), 90: (x0, (y0 + y1) / 2), 270: (x1, (y0 + y1) / 2), 180: ((x0 + x1) / 2, y0)}[lb['line']['ang']]
            seg = graph.seg_parallel_near(opp, direction, 1.5 * H, -side)
            lb['lado_opuesto'] = seg is not None
        lb['seg'] = seg
        lb['chain'] = graph.seg_chain.get(seg) if seg is not None else None
    return nums, labels
