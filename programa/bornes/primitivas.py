# -*- coding: utf-8 -*-
"""Primitivas geometricas genericas para leer bornes en el plano topografico vectorial (PDF de CAD).

Nada de este archivo conoce un tablero en particular: solo sabe encontrar formas en los trazos.
Las formas que se buscan y sus tamanos los define cada modelo en catalogo.json.

Primitivas:
  contorno         lazo cerrado convexo (circulo, estadio, rectangulo redondeado, octogono, abertura en U,
                   poligono de n lados). Punto = centro de su rectangulo envolvente.
  circulo          arcos (curvas aplanadas) agrupados por centro de curvatura; sirve para bocas redondas
                   cortadas por otras lineas. Dos medios circulos del mismo radio muy juntos (estadio)
                   se funden. Punto = centro.
  tornillo_cortado elipse de tornillo cortada por el borde de una carcasa (barreras). Punto = mitad del
                   ancho maximo, a la altura donde el aro es mas ancho.
  caja             el cuerpo del aparato (rectangulo cerrado) cuando el dibujo no trae bornes: los bornes se
                   ubican por fracciones del cuerpo (toma corriente).
"""
import math
from collections import defaultdict


# ----------------------------------------------------------------------------------------- basicos
def bbox(p):
    xs = [q[0] for q in p]
    ys = [q[1] for q in p]
    return min(xs), min(ys), max(xs), max(ys)


def giro(a, b, c):
    """angulo de giro con signo (grados) en b al ir de a hacia c"""
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    if abs(v1[0]) + abs(v1[1]) < 1e-9 or abs(v2[0]) + abs(v2[1]) < 1e-9:
        return 0.0
    return math.degrees(math.atan2(v1[0] * v2[1] - v1[1] * v2[0], v1[0] * v2[0] + v1[1] * v2[1]))


def ajuste_circulo(pts):
    """ajuste algebraico (Kasa): (cx, cy, r, error_maximo) o None"""
    n = len(pts)
    if n < 3:
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
    err = max(abs(math.hypot(p[0] - cx, p[1] - cy) - r) for p in pts)
    return cx, cy, r, err


def color_parecido(c, rgb, tol):
    return c is not None and all(abs(a - b) <= tol for a, b in zip(c[:3], rgb))


def limpiar(p):
    """polilinea sin puntos repetidos"""
    q = [p[0]]
    for a in p[1:]:
        if abs(a[0] - q[-1][0]) + abs(a[1] - q[-1][1]) > 1e-6:
            q.append(a)
    return q


# ----------------------------------------------------------------------------------------- escena
class Escena:
    """Trazos de la pagina recortados a la bandeja, con indices espaciales y las primitivas ya calculadas."""

    def __init__(self, trazos, region, general):
        self.g = general
        x0, y0, x1, y1 = region
        m = 5.0
        self.region = region
        self.todos = [t for t in trazos if t[2] and len(t[2]) >= 1]
        caps = set(general['capas_componentes'])
        self.comp = []           # trazos 'S' de la capa de componentes dentro de la region
        self.comp_fill = []
        for t in self.todos:
            if t[0] not in caps:
                continue
            b = bbox(t[2])
            if b[2] < x0 - m or b[0] > x1 + m or b[3] < y0 - m or b[1] > y1 + m:
                continue
            (self.comp if t[1] == 'S' else self.comp_fill).append((t[0], t[1], limpiar(t[2]), t[3], b))
        # indice de segmentos por celda (para cruces en X, cuerpos, etc.)
        self.celda = 4.0
        self.seg_idx = defaultdict(list)
        for k, t in enumerate(self.comp):
            p = t[2]
            for a, b in zip(p, p[1:]):
                cx = int(((a[0] + b[0]) / 2) // self.celda)
                cy = int(((a[1] + b[1]) / 2) // self.celda)
                self.seg_idx[(cx, cy)].append((a, b))
        self._contornos = None
        self._arcos = None
        self._curvas = None

    # ------------------------------------------------------------- segmentos cerca de un punto
    def segmentos_cerca(self, x, y, d):
        out = []
        c = self.celda
        for i in range(int((x - d) // c) - 1, int((x + d) // c) + 2):
            for j in range(int((y - d) // c) - 1, int((y + d) // c) + 2):
                for s in self.seg_idx.get((i, j), ()):
                    out.append(s)
        return out

    def tiene_x(self, x, y, r):
        """True si hay una cruz en X (dos diagonales que se cortan en el centro): tornillo de tope."""
        pend = set()
        for a, b in self.segmentos_cerca(x, y, r + 1):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy)
            if L < 0.5 * r or abs(dx) < 0.35 * L or abs(dy) < 0.35 * L:
                continue
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if math.hypot(mx - x, my - y) > r:
                continue
            dist = abs(dy * (x - a[0]) - dx * (y - a[1])) / L
            if dist < 0.35:
                pend.add(1 if dx * dy > 0 else -1)
        return len(pend) == 2

    # ------------------------------------------------------------- contornos cerrados convexos
    def contornos(self, caja=None):
        """Contornos cerrados convexos; con caja=(x0, y0, x1, y1) solo se buscan en esa zona (mucho mas rapido)."""
        if caja is None:
            if self._contornos is None:
                self._contornos = _contornos([t for t in self.comp if max(t[4][2] - t[4][0], t[4][3] - t[4][1]) <= 20.0])
            return self._contornos
        if not hasattr(self, '_cache_cont'):
            self._cache_cont = {}
        k = tuple(round(v, 1) for v in caja)
        if k not in self._cache_cont:
            x0, y0, x1, y1 = caja
            sel = [t for t in self.comp if max(t[4][2] - t[4][0], t[4][3] - t[4][1]) <= 20.0
                   and t[4][2] >= x0 - 1 and t[4][0] <= x1 + 1 and t[4][3] >= y0 - 1 and t[4][1] <= y1 + 1]
            self._cache_cont[k] = [c for c in _contornos(sel) if x0 <= c['x'] <= x1 and y0 <= c['y'] <= y1]
        return self._cache_cont[k]

    # ------------------------------------------------------------- arcos (para circulos)
    def arcos(self):
        if self._arcos is None:
            self._arcos = _arcos([t for t in self.comp if max(t[4][2] - t[4][0], t[4][3] - t[4][1]) <= 20.0])
        return self._arcos

    # ------------------------------------------------------------- curvas chicas (tornillos cortados)
    def curvas(self):
        if self._curvas is None:
            out = []
            for t in self.comp:
                p, b = t[2], t[4]
                if len(p) < 4 or max(b[2] - b[0], b[3] - b[1]) > 3.6:
                    continue
                gs = [giro(p[k - 1], p[k], p[k + 1]) for k in range(1, len(p) - 1)]
                if not gs or max(abs(v) for v in gs) > 60:
                    continue
                if min(gs) < -1 and max(gs) > 1:
                    continue
                out.append((p, b, t[3]))
            self._curvas = out
        return self._curvas

    # ------------------------------------------------------------- contornos cerrados cualquiera (cuerpos de aparatos)
    def cerrados(self):
        """Envolventes (x0, y0, x1, y1) de las polilineas cerradas (o rellenos) de 4 o mas puntos: el contorno
        exterior de un aparato aunque no sea un rectangulo (carcasas con chaflanes, barreras)."""
        if getattr(self, '_cerrados', None) is None:
            out = set()
            for t in self.comp + self.comp_fill:
                p = t[2]
                if len(p) >= 4 and (t[1] != 'S' or abs(p[0][0] - p[-1][0]) + abs(p[0][1] - p[-1][1]) < 0.05):
                    out.add(tuple(round(v, 2) for v in t[4]))
            self._cerrados = sorted(out)
        return self._cerrados

    # ------------------------------------------------------------- rectangulos cerrados (cuerpos)
    def rectangulos(self, capas=None):
        out = []
        for t in self.comp + self.comp_fill:
            if capas and t[0] not in capas:
                continue
            p = t[2]
            if len(p) in (4, 5) and abs(p[0][0] - p[-1][0]) + abs(p[0][1] - p[-1][1]) < 0.05:
                ok = all(abs(a[0] - b[0]) < 0.05 or abs(a[1] - b[1]) < 0.05 for a, b in zip(p, p[1:]))
                if ok:
                    out.append(t[4])
        return out


def _contornos(trazos, tol=0.02, giro_max=95.0, largo_max=70.0):
    """Lazos cerrados convexos: se camina por los trazos eligiendo siempre la continuacion que menos gira."""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))
    edges, cols = [], []
    for t in trazos:
        p = t[2]
        if len(p) >= 2:
            edges.append(p)
            cols.append(t[3])
    adj = defaultdict(list)
    for i, e in enumerate(edges):
        adj[key(e[0])].append((i, 0))
        adj[key(e[-1])].append((i, 1))
    out, vistos = [], set()
    for i0, e0 in enumerate(edges):
        for d0 in (0, 1):
            pts = list(e0 if d0 == 0 else e0[::-1])
            if len(pts) >= 3 and max(abs(giro(pts[k - 1], pts[k], pts[k + 1])) for k in range(1, len(pts) - 1)) > giro_max:
                continue
            usados = [i0]
            L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
            cerrado = False
            signo = 0
            while L < largo_max:
                fin = pts[-1]
                if len(pts) > 3 and key(fin) == key(pts[0]):
                    cerrado = True
                    break
                mejor = None
                for j, lado in adj[key(fin)]:
                    if j == usados[-1] or (j in usados and j != i0):
                        continue
                    q = edges[j] if lado == 0 else edges[j][::-1]
                    t = giro(pts[-2], fin, q[1])
                    if abs(t) <= giro_max and (mejor is None or abs(t) < abs(mejor[0])):
                        mejor = (t, j, q)
                if mejor is None:
                    break
                t, j, q = mejor
                if j == i0:
                    cerrado = True
                    break
                usados.append(j)
                pts.extend(q[1:])
                L += sum(math.dist(a, b) for a, b in zip(q, q[1:]))
            if not cerrado:
                continue
            P = pts[:-1] if key(pts[-1]) == key(pts[0]) else pts
            if len(P) < 4:
                continue
            gs = [giro(P[k - 1], P[k], P[(k + 1) % len(P)]) for k in range(len(P))]
            tot = sum(gs)
            if abs(abs(tot) - 360) > 30:
                continue
            s = 1 if tot > 0 else -1
            if any(g * s < -4 for g in gs):          # no convexo
                continue
            b = bbox(P)
            k = (round((b[0] + b[2]) / 0.05), round((b[1] + b[3]) / 0.05), round((b[2] - b[0]) / 0.05), round((b[3] - b[1]) / 0.05))
            if k in vistos:
                continue
            vistos.add(k)
            cc = defaultdict(int)
            for j in usados:
                cc[cols[j]] += 1
            color = max(cc, key=cc.get)
            curvos = sum(1 for g in gs if 3 < abs(g) < 60)
            out.append(dict(x=(b[0] + b[2]) / 2, y=(b[1] + b[3]) / 2, w=b[2] - b[0], h=b[3] - b[1], n=len(P),
                            giro_max=max(abs(g) for g in gs), curvos=curvos, color=color, bb=b))
    return out


def _arcos(trazos, tol=0.02):
    """Tramos curvos de las polilineas (se unen primero los segmentos sueltos que siguen de largo) con su
    circulo ajustado: [(cx, cy, r, puntos, color)]"""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))
    # unir polilineas por nodos de grado 2
    edges = [(t[2], t[3]) for t in trazos if len(t[2]) >= 2]
    grado = defaultdict(int)
    for p, c in edges:
        grado[key(p[0])] += 1
        grado[key(p[-1])] += 1
    adj = defaultdict(list)
    for i, (p, c) in enumerate(edges):
        adj[key(p[0])].append(i)
        adj[key(p[-1])].append(i)
    usado = [False] * len(edges)
    cadenas = []
    for i in range(len(edges)):
        if usado[i]:
            continue
        usado[i] = True
        pl = list(edges[i][0])
        col = edges[i][1]
        for hacia_fin in (True, False):
            while True:
                extremo = pl[-1] if hacia_fin else pl[0]
                k = key(extremo)
                if grado[k] != 2:
                    break
                nx = next((j for j in adj[k] if not usado[j]), None)
                if nx is None:
                    break
                usado[nx] = True
                q = edges[nx][0]
                if key(q[0]) != k:
                    q = q[::-1]
                if hacia_fin:
                    pl.extend(q[1:])
                else:
                    pl[:0] = q[::-1][:-1]
        cadenas.append((limpiar(pl), col))
    res = []
    for p, col in cadenas:
        if len(p) < 3:
            continue
        # tramos de curvatura sostenida: giros entre 1 y 60 grados, del mismo signo
        tramos = []
        tramo = [p[0], p[1]]
        signo = 0
        for k in range(1, len(p) - 1):
            g = giro(p[k - 1], p[k], p[k + 1])
            s = 1 if g > 0 else -1
            if 1.0 < abs(g) <= 60 and (signo == 0 or s == signo):
                tramo.append(p[k + 1])
                signo = s
            else:
                if len(tramo) >= 3:
                    tramos.append(tramo)
                tramo = [p[k], p[k + 1]]
                signo = 0
                if 1.0 < abs(g) <= 60:
                    tramo = [p[k - 1], p[k], p[k + 1]]
                    signo = s
        if len(tramo) >= 3:
            tramos.append(tramo)
        for tr in tramos:
            f = ajuste_circulo(tr)
            if not f:
                continue
            cx, cy, r, err = f
            if err > max(0.06, 0.08 * r):
                continue
            res.append((cx, cy, r, tr, col))
    return res


def circulos(arcos, rmin, rmax, cob_min=150.0, fusionar_estadio=0.6):
    """Agrupa arcos del mismo centro y radio. Devuelve [dict(x, y, r, cob, n, color)].
    Dos grupos del mismo radio con centros muy juntos (estadio: dos medias circunferencias separadas) se
    funden en uno solo, con el centro en el punto medio."""
    cand = [a for a in arcos if rmin <= a[2] <= rmax]
    cl = []
    for a in cand:
        cx, cy, r = a[0], a[1], a[2]
        for g in cl:
            if math.hypot(g['cx'] - cx, g['cy'] - cy) < max(0.2, 0.12 * r) and abs(g['r'] - r) < max(0.15, 0.12 * r):
                g['m'].append(a)
                n = len(g['m'])
                g['cx'] += (cx - g['cx']) / n
                g['cy'] += (cy - g['cy']) / n
                g['r'] += (r - g['r']) / n
                break
        else:
            cl.append(dict(cx=cx, cy=cy, r=r, m=[a]))
    usados = set()
    res = []
    orden = sorted(range(len(cl)), key=lambda i: -len(cl[i]['m']))
    for i in orden:
        if i in usados:
            continue
        g = cl[i]
        grupo = [g]
        usados.add(i)
        for j in orden:
            if j in usados:
                continue
            h = cl[j]
            if abs(h['r'] - g['r']) < max(0.15, 0.12 * g['r']) and math.hypot(h['cx'] - g['cx'], h['cy'] - g['cy']) < fusionar_estadio * g['r']:
                grupo.append(h)
                usados.add(j)
        xs = [q['cx'] for q in grupo]
        ys = [q['cy'] for q in grupo]
        x = (min(xs) + max(xs)) / 2
        y = (min(ys) + max(ys)) / 2
        pts = [p for q in grupo for m in q['m'] for p in m[3]]
        cob = _cobertura(pts, x, y)
        r = sum(q['r'] for q in grupo) / len(grupo)
        cc = defaultdict(int)
        for q in grupo:
            for m in q['m']:
                cc[m[4]] += len(m[3])
        color = max(cc, key=cc.get) if cc else None
        if cob >= cob_min:
            res.append(dict(x=x, y=y, r=r, cob=cob, n=sum(len(q['m']) for q in grupo), color=color))
    return res


def _cobertura(pts, cx, cy):
    if len(pts) < 2:
        return 0.0
    angs = sorted(math.degrees(math.atan2(q[1] - cy, q[0] - cx)) % 360 for q in pts)
    gaps = [(angs[(i + 1) % len(angs)] - angs[i]) % 360 for i in range(len(angs))]
    return 360 - max(gaps)


def tornillos_cortados(curvas, ancho=(2.2, 3.4), alto_max=3.4):
    """Elipses de tornillo (posiblemente cortadas por el borde de la carcasa). Agrupa las curvas chicas que
    se tocan; x = mitad del ancho maximo, y = altura del punto mas a la izquierda y a la derecha."""
    grupos = []
    for p, b, c in sorted(curvas, key=lambda t: t[1][0]):
        for g in grupos:
            gb = g['bb']
            if b[0] <= gb[2] + 0.1 and b[2] >= gb[0] - 0.1 and b[1] <= gb[3] + 0.1 and b[3] >= gb[1] - 0.1:
                g['pts'].extend(p)
                g['bb'] = (min(gb[0], b[0]), min(gb[1], b[1]), max(gb[2], b[2]), max(gb[3], b[3]))
                break
        else:
            grupos.append(dict(pts=list(p), bb=b))
    out = []
    for g in grupos:
        xa, ya, xb, yb = g['bb']
        w, h = xb - xa, yb - ya
        if not (ancho[0] <= w <= ancho[1]) or h > alto_max:
            continue
        ext = [q[1] for q in g['pts'] if q[0] <= xa + 0.03 or q[0] >= xb - 0.03]
        cy = sum(ext) / len(ext)
        out.append(dict(x=(xa + xb) / 2, y=cy, w=w, h=h, r=w / 2))
    # sin duplicados (el bloque puede estar repetido en el PDF)
    ded = []
    for s in out:
        if not any(abs(s['x'] - t['x']) < 0.3 and abs(s['y'] - t['y']) < 0.3 for t in ded):
            ded.append(s)
    return ded
