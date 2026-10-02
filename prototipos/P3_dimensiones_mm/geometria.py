"""Geometria del plano topografico vectorial (P3: base de bornes en milimetros).

Lo que hace este modulo:
  * lee los trazos de la pagina (pdfvec del programa, sin modificarlo);
  * encuentra los rieles DIN (capa RIEL DIN) y las etiquetas amarillas (recuadros de la capa de etiquetas);
  * encuentra CUERPOS de aparatos y PIEZAS de borneras a partir de sus medidas en mm (base de datos):
    un cuerpo es un par de lados verticales largos separados por el ancho del aparato y con el alto del
    aparato (segun la base).  No mira tornillos ni bocas: por eso sirve con simbolos simplificados.
  * herramientas de medicion (circulos y contornos cerrados dentro de un cuerpo) para cargar modelos nuevos.
"""
import math, sys, collections

PROG = 'C:/Buscar Termos en plano/programa'
if PROG not in sys.path:
    sys.path.insert(0, PROG)

CAPAS_COMP = ('COMPONENTES', '00_COMPONENTS')


def bbox(p):
    xs = [a for a, b in p]; ys = [b for a, b in p]
    return min(xs), min(ys), max(xs), max(ys)


def es_verde(rgb):
    return rgb is not None and rgb[1] > 0.4 and rgb[1] > rgb[0] + 0.25 and rgb[1] > rgb[2] + 0.25


class Plano:
    def __init__(self, pdf, pagina_idx, trazos=None, capas=CAPAS_COMP):
        """capas: capas donde estan dibujados los aparatos (None = todas, por ejemplo en una hoja de datos)."""
        if trazos is None:
            import pypdf
            from pdfvec import page_strokes, layer_names
            r = pypdf.PdfReader(pdf)
            trazos = page_strokes(r, pagina_idx, layer_names(r), with_color=True)
        self.trazos = trazos
        self.capas = capas
        ok = (lambda l: True) if capas is None else (lambda l: l in capas)
        self.es_comp = ok
        # en el plano solo los trazos de linea; en una hoja de datos tambien los rellenos (tornillos dibujados rellenos)
        ops = ('S', 's') if capas is not None else ('S', 's', 'f', 'F', 'f*', 'b', 'B', 'b*', 'B*')
        # segmentos de la capa de componentes: (x1, y1, x2, y2, indice_trazo)
        self.vseg, self.hseg, self.seg = [], [], []
        for i, (lay, op, pts, rgb) in enumerate(trazos):
            if not ok(lay) or op not in ops or len(pts) < 2:
                continue
            for a, b in zip(pts, pts[1:]):
                self.seg.append((a[0], a[1], b[0], b[1], i))
                if abs(a[0] - b[0]) < 0.03 and abs(a[1] - b[1]) >= 0.3:
                    self.vseg.append(((a[0] + b[0]) / 2, min(a[1], b[1]), max(a[1], b[1]), i))
                elif abs(a[1] - b[1]) < 0.03 and abs(a[0] - b[0]) >= 0.3:
                    self.hseg.append(((a[1] + b[1]) / 2, min(a[0], b[0]), max(a[0], b[0]), i))
        self.vseg.sort()
        self.hseg.sort()

    # ------------------------------------------------------------------ rieles DIN
    def rieles(self):
        """[{'y': eje, 'x0', 'x1', 'ancho_pt'}] a partir de las lineas horizontales largas de la capa RIEL.
        El perfil DIN mide 35 mm: el ancho dibujado sirve de control de escala."""
        L = []
        for lay, op, pts, rgb in self.trazos:
            if 'RIEL' not in lay.upper():
                continue
            for a, b in zip(pts, pts[1:]):
                if abs(a[1] - b[1]) < 0.05 and abs(a[0] - b[0]) > 30:
                    L.append(((a[1] + b[1]) / 2, min(a[0], b[0]), max(a[0], b[0])))
        L.sort()
        bandas = []
        for y, x0, x1 in L:
            for bd in bandas:
                if abs(bd['y1'] - y) < 30 and x0 < bd['x1'] + 5 and x1 > bd['x0'] - 5:
                    bd['y1'] = max(bd['y1'], y); bd['y0'] = min(bd['y0'], y)
                    bd['x0'] = min(bd['x0'], x0); bd['x1'] = max(bd['x1'], x1); break
            else:
                bandas.append(dict(y0=y, y1=y, x0=x0, x1=x1))
        out = []
        for bd in bandas:
            if bd['y1'] - bd['y0'] > 10:
                out.append(dict(y=(bd['y0'] + bd['y1']) / 2, x0=bd['x0'], x1=bd['x1'], ancho_pt=bd['y1'] - bd['y0']))
        # unir tramos del mismo riel cortados (misma y)
        out.sort(key=lambda r: (round(r['y'], 0), r['x0']))
        return out

    def riel_de(self, x, y, rieles=None):
        rieles = rieles if rieles is not None else self.rieles()
        cand = [r for r in rieles if r['x0'] - 20 <= x <= r['x1'] + 20]
        if not cand:
            return None
        return min(cand, key=lambda r: abs(r['y'] - y))

    # ------------------------------------------------------------------ etiquetas amarillas
    def rectangulos(self, capa_filtro=None):
        out = []
        for lay, op, pts, rgb in self.trazos:
            if capa_filtro and not capa_filtro(lay):
                continue
            if len(pts) in (5, 4) and op in ('S', 's', 'f', 'F', 'B', 'b'):
                b = bbox(pts)
                esquinas = [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])]
                # rectangulo (se admite un giro chico del dibujo): cada vertice cerca de una esquina
                if all(min(math.hypot(p[0] - e[0], p[1] - e[1]) for e in esquinas) < 0.2 for p in pts):
                    out.append((lay, b))
        return out

    def etiquetas(self, puntos_conocidos):
        """Todos los recuadros de etiqueta de la pagina.  El tamano y la capa se aprenden de las etiquetas
        conocidas (posiciones que trae usos_por_componente.json): el recuadro mas chico que contiene cada punto."""
        rects = self.rectangulos()
        ejemplos = []
        for (x, y) in puntos_conocidos:
            dentro = [(lay, b) for lay, b in rects if b[0] - 0.5 <= x <= b[2] + 0.5 and b[1] - 0.5 <= y <= b[3] + 0.5
                      and (b[2] - b[0]) * (b[3] - b[1]) < 400]
            if dentro:
                ejemplos.append(min(dentro, key=lambda t: (t[1][2] - t[1][0]) * (t[1][3] - t[1][1])))
        if not ejemplos:
            return [dict(x=x, y=y, w=0, h=0) for x, y in puntos_conocidos]
        capas = collections.Counter(l for l, b in ejemplos)
        capa = capas.most_common(1)[0][0]
        lados = collections.Counter(tuple(sorted((round(b[2] - b[0], 0), round(b[3] - b[1], 0)))) for l, b in ejemplos)
        (c, l), _ = lados.most_common(1)[0]
        vistos, out = set(), []
        for lay, b in rects:
            if lay != capa:
                continue
            w, h = b[2] - b[0], b[3] - b[1]
            lo, hi = sorted((w, h))
            if abs(lo - c) > 1.2 or abs(hi - l) > 1.2:
                continue
            k = (round((b[0] + b[2]) / 2, 0), round((b[1] + b[3]) / 2, 0))
            if k in vistos:
                continue
            vistos.add(k)
            out.append(dict(x=(b[0] + b[2]) / 2, y=(b[1] + b[3]) / 2, w=w, h=h, x0=b[0], x1=b[2], y0=b[1], y1=b[3]))
        return out

    # ------------------------------------------------------------------ lados verticales
    def lados_verticales(self, x0, x1, y0, y1, tol=0.05):
        """Agrupa los segmentos verticales por x.  Devuelve [{x, y0, y1, cubierto, verde}] (cubierto = largo
        real dibujado, sin contar huecos)."""
        V = [v for v in self.vseg if x0 <= v[0] <= x1 and v[1] < y1 and v[2] > y0]
        V.sort()
        grupos = []
        for v in V:
            if grupos and v[0] - grupos[-1][-1][0] <= tol:
                grupos[-1].append(v)
            else:
                grupos.append([v])
        out = []
        for g in grupos:
            iv = sorted((a[1], a[2]) for a in g)
            cov, (cs, ce), tramos = 0.0, iv[0], []
            for s, e in iv[1:]:
                if s > ce:
                    cov += ce - cs; tramos.append((cs, ce)); cs, ce = s, e
                else:
                    ce = max(ce, e)
            cov += ce - cs
            tramos.append((cs, ce))
            verdes = sum(1 for a in g if es_verde(self.trazos[a[3]][3]))
            out.append(dict(x=sum(a[0] for a in g) / len(g), y0=min(a[1] for a in g), y1=max(a[2] for a in g),
                            cubierto=cov, verde=verdes > len(g) / 2, tramos=tramos))
        return out

    @staticmethod
    def cobertura(lado, y0, y1):
        """Largo dibujado del lado dentro de [y0, y1]."""
        return sum(max(0.0, min(e, y1) - max(s, y0)) for s, e in lado['tramos'])

    def piezas(self, x0, x1, y_riel, ancho_pt, alto_pt, tol_ancho=None, tol_alto=0.07, max_n=60, esquina=3.5):
        """Cuerpos de ancho `ancho_pt` y alto `alto_pt` (en pt) que cruzan el riel (o la altura y_riel) y estan
        entre x0 y x1.  Sirve para piezas de bornera pegadas (comparten lados) y para aparatos sueltos.

        Un cuerpo es un par de lados verticales separados por el ancho.  Al menos uno de los dos tiene el alto
        del modelo; el otro puede ser mas largo (lado compartido con un aparato vecino mas alto) si cubre ese
        tramo.  Si los lados son algo mas cortos (esquinas redondeadas, hasta `esquina` pt), el alto se toma de
        las lineas horizontales de arriba y abajo.  Devuelve [{x0, x1, y0, y1, verde, err}] de izquierda a derecha."""
        tol_ancho = tol_ancho if tol_ancho is not None else max(0.15, 0.03 * ancho_pt)
        lados = self.lados_verticales(x0 - ancho_pt, x1 + ancho_pt, y_riel - 1.3 * alto_pt, y_riel + 1.3 * alto_pt)
        hmin, hmax = alto_pt * (1 - tol_alto), alto_pt * (1 + tol_alto)
        justos = [l for l in lados if hmin - esquina <= (l['y1'] - l['y0']) <= hmax
                  and l['cubierto'] >= 0.5 * (l['y1'] - l['y0']) and l['y0'] - 2 <= y_riel <= l['y1'] + 2]
        out, vistos, ids = [], set(), {id(l) for l in justos}
        for a in justos:
            for b in lados:
                d = b['x'] - a['x']
                if abs(abs(d) - ancho_pt) > tol_ancho:
                    continue
                izq, der = (a, b) if d > 0 else (b, a)
                if izq['x'] < x0 - 0.5 or izq['x'] > x1:
                    continue
                if id(b) in ids and abs(a['y0'] - b['y0']) < 0.12 * alto_pt and abs(a['y1'] - b['y1']) < 0.12 * alto_pt:
                    ya, yb, pen = (a['y0'] + b['y0']) / 2, (a['y1'] + b['y1']) / 2, 0.0
                else:   # b es mas largo: tiene que cubrir el tramo de a
                    if self.cobertura(b, a['y0'], a['y1']) < 0.6 * (a['y1'] - a['y0']):
                        continue
                    ya, yb, pen = a['y0'], a['y1'], 0.05
                k = (round(izq['x'], 2), round(der['x'], 2), round(ya, 1))
                if k in vistos:
                    continue
                vistos.add(k)
                if yb - ya < hmin:        # lados cortos: hacen falta los bordes horizontales
                    e0 = self._borde_h(izq['x'], der['x'], ya, esquina + 0.5, abajo=True)
                    e1 = self._borde_h(izq['x'], der['x'], yb, esquina + 0.5, abajo=False)
                    if e0 is None or e1 is None:
                        continue
                    ya, yb = e0, e1
                else:
                    ya, yb = self._bordes_horizontales(izq['x'], der['x'], ya, yb)
                if abs((yb - ya) - alto_pt) > tol_alto * alto_pt:
                    continue
                # lados con huecos (lineas interiores del dibujo) pesan como error
                hueco = sum(1 - min(1.0, self.cobertura(l, ya, yb) / max(0.1, yb - ya)) for l in (izq, der))
                out.append(dict(x0=izq['x'], x1=der['x'], y0=ya, y1=yb, verde=izq['verde'] and der['verde'],
                                err=abs(abs(d) - ancho_pt) + abs((yb - ya) - alto_pt) * 0.2 + pen + 0.5 * hueco))
        # sin solapes: si dos cuerpos se pisan, queda el de menor error
        out.sort(key=lambda c: c['err'])
        final = []
        for c in out:
            if all(c['x1'] <= f['x0'] + 0.3 or c['x0'] >= f['x1'] - 0.3 for f in final):
                final.append(c)
        final.sort(key=lambda c: c['x0'])
        return final[:max_n]

    def _bordes_horizontales(self, xa, xb, y0, y1, busca=1.5):
        """Afina arriba/abajo del cuerpo con la linea horizontal que une los dos lados (si la hay)."""
        def mejor(yref):
            c = [h for h in self.hseg if abs(h[0] - yref) <= busca and h[1] <= xa + 0.3 and h[2] >= xb - 0.3]
            return min(c, key=lambda h: abs(h[0] - yref))[0] if c else yref
        return mejor(y0), mejor(y1)

    def _borde_h(self, xa, xb, yref, busca, abajo, cubre=0.6):
        """Borde horizontal (puede venir en tramos y con esquinas redondeadas) entre xa y xb, a menos de `busca`
        de yref; el mas exterior (el mas bajo si abajo=True).  None si no hay."""
        grupos = {}
        for h in self.hseg:
            if abs(h[0] - yref) <= busca and h[2] > xa and h[1] < xb:
                grupos.setdefault(round(h[0] / 0.05), []).append((max(h[1], xa), min(h[2], xb), h[0]))
        ok = []
        for g in grupos.values():
            iv = sorted(g)
            cov, (cs, ce) = 0.0, iv[0][:2]
            for s, e, _ in iv[1:]:
                if s > ce:
                    cov += ce - cs; cs, ce = s, e
                else:
                    ce = max(ce, e)
            cov += ce - cs
            if cov >= cubre * (xb - xa):
                ok.append(sum(t[2] for t in g) / len(g))
        if not ok:
            return None
        return min(ok) if abajo else max(ok)

    # ------------------------------------------------------------------ medicion (para cargar modelos)
    def circulos(self, x0, y0, x1, y1, rmin=0.5, rmax=10.0):
        """Circulos dibujados dentro de la caja: poligonos cerrados o arcos (voto de circuncentros).
        Devuelve [(cx, cy, r, soporte)] sin duplicados concentricos (queda el mayor)."""
        segs = [s for s in self.seg if x0 - 1 <= min(s[0], s[2]) and max(s[0], s[2]) <= x1 + 1
                and y0 - 1 <= min(s[1], s[3]) and max(s[1], s[3]) <= y1 + 1]
        key = lambda p: (round(p[0] / 0.02), round(p[1] / 0.02))
        adj = collections.defaultdict(list)
        for ax, ay, bx, by, i in segs:
            L = math.hypot(bx - ax, by - ay)
            if 0.02 < L <= 2.5:
                adj[key((ax, ay))].append(((ax, ay), (bx, by)))
                adj[key((bx, by))].append(((bx, by), (ax, ay)))
        votos = []
        for lst in adj.values():
            for i in range(len(lst)):
                for j in range(i + 1, len(lst)):
                    p, a = lst[i]; _, c = lst[j]
                    v1 = (a[0] - p[0], a[1] - p[1]); v2 = (c[0] - p[0], c[1] - p[1])
                    n1, n2 = math.hypot(*v1), math.hypot(*v2)
                    cosang = -(v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
                    giro = math.degrees(math.acos(max(-1, min(1, cosang))))
                    if not 3 < giro < 70:
                        continue
                    cc = _circuncentro(a, p, c)
                    if cc and rmin <= cc[2] <= rmax:
                        votos.append((cc[0], cc[1], cc[2], p))
        grupos = []
        for x, y, r, p in votos:
            for g in grupos:
                if math.hypot(g['x'] - x, g['y'] - y) < max(0.15, 0.12 * r) and abs(g['r'] - r) < max(0.15, 0.15 * r):
                    n = g['n']; g['x'] = (g['x'] * n + x) / (n + 1); g['y'] = (g['y'] * n + y) / (n + 1)
                    g['r'] = (g['r'] * n + r) / (n + 1); g['n'] += 1; g['p'].append(p); break
            else:
                grupos.append(dict(x=x, y=y, r=r, n=1, p=[p]))
        out = []
        # arcos: cada polilinea curva (>= 4 puntos) se ajusta a un circulo; los arcos con el mismo centro y
        # radio se juntan (un circulo suele venir en 2-3 arcos) y se mide cuanto del giro cubren
        arcos = []
        for lay, op, pts, rgb in self.trazos:
            if not self.es_comp(lay) or len(pts) < 4:
                continue
            b = bbox(pts)
            if not (x0 - 1 <= b[0] and b[2] <= x1 + 1 and y0 - 1 <= b[1] and b[3] <= y1 + 1):
                continue
            f = _ajuste_circulo(pts)
            if f and rmin <= f[2] <= rmax and f[3] < 0.06 * f[2] + 0.02:
                arcos.append((f[0], f[1], f[2], pts))
        ga = []
        for cx, cy, r, pts in arcos:
            for g in ga:
                if math.hypot(g['x'] - cx, g['y'] - cy) < max(0.12, 0.2 * r) and abs(g['r'] - r) < max(0.1, 0.12 * r):
                    g['arcos'].append((cx, cy, r, pts)); break
            else:
                ga.append(dict(x=cx, y=cy, r=r, arcos=[(cx, cy, r, pts)]))
        for g in ga:
            w = [len(a[3]) for a in g['arcos']]
            gx = sum(a[0] * n for a, n in zip(g['arcos'], w)) / sum(w)
            gy = sum(a[1] * n for a, n in zip(g['arcos'], w)) / sum(w)
            gr = sum(a[2] * n for a, n in zip(g['arcos'], w)) / sum(w)
            angs = sorted(math.degrees(math.atan2(p[1] - gy, p[0] - gx)) % 360 for a in g['arcos'] for p in a[3])
            huecos = [(angs[(k + 1) % len(angs)] - angs[k]) % 360 for k in range(len(angs))]
            cob = 360 - max(huecos) if len(angs) > 1 else 0
            if cob >= 300:
                # contorno casi completo: el centro es el del rectangulo que lo encierra (sirve para ovalos)
                bx = bbox([p for a in g['arcos'] for p in a[3]])
                gx, gy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
                gr = ((bx[2] - bx[0]) + (bx[3] - bx[1])) / 4
            if cob >= 200 and x0 <= gx <= x1 and y0 <= gy <= y1:
                out.append((gx, gy, gr, cob))
        for g in grupos:
            if g['n'] < 4:
                continue
            angs = sorted(math.degrees(math.atan2(p[1] - g['y'], p[0] - g['x'])) % 360 for p in g['p'])
            huecos = [(angs[(i + 1) % len(angs)] - angs[i]) % 360 for i in range(len(angs))]
            cob = 360 - max(huecos) if len(angs) > 1 else 0
            if cob >= 180 and x0 <= g['x'] <= x1 and y0 <= g['y'] <= y1:
                out.append((g['x'], g['y'], g['r'], cob))
        out.sort(key=lambda c: -c[2])
        res = []
        for c in out:
            if any(math.hypot(c[0] - d[0], c[1] - d[1]) < 0.35 * d[2] for d in res):
                continue
            res.append(c)
        return sorted(res, key=lambda c: (-round(c[1], 0), c[0]))

    def figuras(self, x0, y0, x1, y1, lado_min=1.2, lado_max=8.0, tol=0.03, sin_bordes=None):
        """Figuras chicas conectadas (trazos que se tocan en sus extremos) dentro de la caja: octogonos de las
        bocas push-in, rectangulos redondeados, tornillos...  Devuelve [(cx, cy, ancho, alto, n_segmentos)] con
        el centro del rectangulo que encierra cada figura."""
        segs = [s for s in self.seg if x0 - 0.5 <= min(s[0], s[2]) and max(s[0], s[2]) <= x1 + 0.5
                and y0 - 0.5 <= min(s[1], s[3]) and max(s[1], s[3]) <= y1 + 0.5
                and math.hypot(s[2] - s[0], s[3] - s[1]) < lado_max]
        if sin_bordes:   # sacar los lados del cuerpo (las figuras que los tocan quedarian pegadas al contorno)
            bx0, bx1 = sin_bordes
            segs = [s for s in segs if not (abs(s[0] - s[2]) < 0.03 and (abs(s[0] - bx0) < 0.08 or abs(s[0] - bx1) < 0.08))]
        padre = list(range(len(segs)))

        def raiz(i):
            while padre[i] != i:
                padre[i] = padre[padre[i]]; i = padre[i]
            return i
        donde = {}
        for i, s in enumerate(segs):
            for p in ((s[0], s[1]), (s[2], s[3])):
                k = (round(p[0] / tol), round(p[1] / tol))
                if k in donde:
                    padre[raiz(i)] = raiz(donde[k])
                else:
                    donde[k] = i
        grupos = collections.defaultdict(list)
        for i in range(len(segs)):
            grupos[raiz(i)].append(segs[i])
        out = []
        for g in grupos.values():
            xs = [v for s in g for v in (s[0], s[2])]; ys = [v for s in g for v in (s[1], s[3])]
            w, h = max(xs) - min(xs), max(ys) - min(ys)
            if lado_min <= w <= lado_max and lado_min <= h <= lado_max and len(g) >= 3:
                out.append(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, w, h, len(g)))
        return sorted(out, key=lambda f: (-f[1], f[0]))

    def contornos_cerrados(self, x0, y0, x1, y1, lado_min=1.0, lado_max=12.0):
        """Polilineas cerradas chicas (bocas, rectangulos redondeados, octogonos) dentro de la caja: centro del
        rectangulo que las encierra."""
        out = []
        for lay, op, pts, rgb in self.trazos:
            if not self.es_comp(lay) or len(pts) < 4:
                continue
            if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 0.05:
                continue
            b = bbox(pts)
            w, h = b[2] - b[0], b[3] - b[1]
            if lado_min <= w <= lado_max and lado_min <= h <= lado_max and x0 <= b[0] and b[2] <= x1 and y0 <= b[1] and b[3] <= y1:
                out.append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, w, h, len(pts)))
        return out


def _ajuste_circulo(pts):
    """Ajuste algebraico (Kasa) de un circulo a los puntos: (cx, cy, r, error_rms) o None."""
    import numpy as np
    P = np.asarray(pts, dtype=float)
    if len(P) >= 2 and np.hypot(*(P[0] - P[-1])) < 1e-6:
        P = P[:-1]
    if len(P) < 4:
        return None
    x, y = P[:, 0], P[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(P))]
    bb = x * x + y * y
    try:
        sol, *_ = np.linalg.lstsq(A, bb, rcond=None)
    except Exception:
        return None
    cx, cy, c = sol
    r2 = c + cx * cx + cy * cy
    if r2 <= 0:
        return None
    r = math.sqrt(r2)
    err = float(np.sqrt(np.mean((np.hypot(x - cx, y - cy) - r) ** 2)))
    # tiene que ser un arco de verdad: los puntos recorren al menos 60 grados
    ang = np.unwrap(np.arctan2(y - cy, x - cx))
    if abs(ang.max() - ang.min()) < math.radians(60):
        return None
    return float(cx), float(cy), r, err


def _circuncentro(a, b, c):
    ax, ay = a; bx, by = b; cx, cy = c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return ux, uy, math.hypot(ax - ux, ay - uy)
