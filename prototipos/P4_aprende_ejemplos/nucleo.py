"""Funciones comunes del prototipo P4 (base que aprende de tableros verificados).

Idea: cada aparato del topografico Batfer es un bloque de CAD que trae su propio "recuadro":
un poligono blanco de relleno (mascara) del tamano del aparato, de la pieza de bornera o del
modulo de rele.  Ese recuadro se detecta solo en el dibujo, sin saber nada del tablero.
La base guarda, por modelo, ejemplos verificados: la posicion de cada borne NORMALIZADA al
recuadro (u, v de 0 a 1), un descriptor simple del dibujo (tamano, cantidad de trazos, colores)
y un parche chico del dibujo alrededor del borne (para el ajuste fino = snap).

Este modulo no tiene coordenadas de ningun tablero: todo sale del PDF, de usos_por_componente.json
y de la base de ejemplos.
"""
import sys, os, re, json, math, base64

import numpy as np
import cv2

PROG = r'C:\Buscar Termos en plano\programa'
if PROG not in sys.path:
    sys.path.insert(0, PROG)

CAPAS = ('COMPONENTES', '00_COMPONENTS')
S = 10              # pixeles por punto PDF en el raster de trabajo
MEDIO_PARCHE = 3.0  # el parche de cada borne mide 2*3 = 6 pt de lado
R_SNAP = 1.6        # radio maximo del ajuste fino (pt)
SCORE_SNAP = 0.55   # correlacion minima para aceptar el ajuste


# ----------------------------------------------------------------------------------------- lectura
def cargar_trazos(pdf, pagina_idx):
    import pypdf
    from pdfvec import page_strokes, layer_names
    r = pypdf.PdfReader(pdf)
    return page_strokes(r, pagina_idx, layer_names(r), with_color=True)


def bbox(p):
    xs = [a for a, b in p]
    ys = [b for a, b in p]
    return min(xs), min(ys), max(xs), max(ys)


def es_blanco(c):
    return c is not None and min(c) > 0.95


def color_clase(c):
    """'verde' / 'azul' / 'negro' / 'gris' / 'otro' del color de un trazo."""
    r, g, b = c
    if g > 0.4 and r < 0.2 and b < 0.3:
        return 'verde'
    if b > 0.4 and r < 0.2 and g < 0.2:
        return 'azul'
    if max(c) < 0.15:
        return 'negro'
    if abs(r - g) < 0.05 and abs(g - b) < 0.05:
        return 'gris'
    return 'otro'


# ----------------------------------------------------------------------------------------- plano
class Plano:
    """El topografico ya leido: trazos, raster, recuadros candidatos y marcos de etiquetas."""

    def __init__(self, pdf, pagina_idx, region, escala_mm_por_pt):
        self.pdf = pdf
        self.escala = float(escala_mm_por_pt)
        self.st = cargar_trazos(pdf, pagina_idx)
        m = 15.0
        self.X0, self.Y0, self.X1, self.Y1 = region[0] - m, region[1] - m, region[2] + m, region[3] + m
        self._raster()
        self._marcos()
        self._cajas()

    # --- raster de las capas de componentes, respetando el orden de dibujo (las mascaras blancas tapan)
    def _raster(self):
        W = int((self.X1 - self.X0) * S) + 1
        H = int((self.Y1 - self.Y0) * S) + 1
        img = np.zeros((H, W), np.uint8)
        for lay, op, p, c in self.st:
            if lay not in CAPAS or len(p) < 2:
                continue
            b = bbox(p)
            if b[2] < self.X0 or b[0] > self.X1 or b[3] < self.Y0 or b[1] > self.Y1:
                continue
            q = np.round(np.array([[(x - self.X0) * S, (self.Y1 - y) * S] for x, y in p]) * 16).astype(np.int32)
            val = 0 if es_blanco(c) else 255
            if op in ('f', 'F', 'f*', 'B', 'B*', 'b', 'b*'):
                cv2.fillPoly(img, [q], val, lineType=cv2.LINE_8, shift=4)
            else:
                cv2.polylines(img, [q], False, val, 1, lineType=cv2.LINE_8, shift=4)
        self.img = img
        self.imgf = cv2.GaussianBlur(img.astype(np.float32) / 255.0, (3, 3), 0.8)

    def a_px(self, x, y):
        return (x - self.X0) * S, (self.Y1 - y) * S

    def a_pt(self, c, r):
        return self.X0 + c / S, self.Y1 - r / S

    # --- marcos de las etiquetas amarillas (rectangulo gris de la capa 'Texto etiquetas')
    def _marcos(self):
        out = []
        for lay, op, p, c in self.st:
            if lay != 'Texto etiquetas' or op != 'S' or len(p) < 4 or not c:
                continue
            if not (0.2 < c[0] < 0.45 and abs(c[0] - c[1]) < 0.02):
                continue
            x0, y0, x1, y1 = bbox(p)
            w, h = x1 - x0, y1 - y0
            if 3 < min(w, h) < 9 and max(w, h) > 8:
                if not any(abs(x0 - m[0]) < 0.3 and abs(y0 - m[1]) < 0.3 and abs(x1 - m[2]) < 0.3 for m in out):
                    out.append((x0, y0, x1, y1))
        self.marcos = out

    # --- recuadros candidatos: mascaras blancas (preferidas) y contornos de trazos
    def _cajas(self):
        cajas = []
        for i, (lay, op, p, c) in enumerate(self.st):
            if lay not in CAPAS or len(p) < 4:
                continue
            x0, y0, x1, y1 = bbox(p)
            w, h = x1 - x0, y1 - y0
            if x1 < self.X0 or x0 > self.X1 or y1 < self.Y0 or y0 > self.Y1:
                continue
            if op == 'f' and es_blanco(c):
                if w < 1 or h < 1 or w > 250 or h > 250:
                    continue
                # la mascara del propio rotulo amarillo no es un aparato
                if any(abs(x0 - m[0]) < 0.4 and abs(y0 - m[1]) < 0.4 and abs(x1 - m[2]) < 0.4 and abs(y1 - m[3]) < 0.4
                       for m in self.marcos):
                    continue
                cajas.append(dict(x0=x0, y0=y0, x1=x1, y1=y1, fuente='mascara'))
            elif op == 'S' and not es_blanco(c) and w >= 3 and h >= 3 and w < 250 and h < 250:
                cajas.append(dict(x0=x0, y0=y0, x1=x1, y1=y1, fuente='contorno'))
        # sin duplicados (el mismo recuadro repetido); la mascara gana
        cajas.sort(key=lambda b: (b['fuente'] != 'mascara', b['x0'], b['y0']))
        uniq, idx = [], {}
        for b in cajas:
            k = (round(b['x0'] * 4), round(b['y0'] * 4), round(b['x1'] * 4), round(b['y1'] * 4))
            if any(kk in idx for kk in [(k[0] + a, k[1] + bb, k[2] + a, k[3] + bb) for a in (-1, 0, 1) for bb in (-1, 0, 1)]):
                continue
            idx[k] = 1
            uniq.append(b)
        for b in uniq:
            b['w'] = b['x1'] - b['x0']
            b['h'] = b['y1'] - b['y0']
        self.cajas = uniq
        # indice de trazos por posicion (para los descriptores): bbox, largo y color
        filas, cols = [], []
        for lay, op, p, c in self.st:
            if lay in CAPAS and op == 'S' and len(p) >= 2 and not es_blanco(c):
                x0, y0, x1, y1 = bbox(p)
                L = sum(math.dist(a, b) for a, b in zip(p, p[1:]))
                filas.append((x0, y0, x1, y1, L))
                cols.append(color_clase(c))
        self._tr = np.array(filas), np.array(cols)

    # ------------------------------------------------------------------------------ descriptor
    def descriptor(self, b):
        """Descriptor simple del dibujo dentro del recuadro: tamano en mm, cantidad de trazos (de mas de 0.3 pt),
        largo total de trazo por pt2, fraccion (por largo) de trazo verde y azul, y densidad de tinta del raster."""
        arr, cols = self._tr
        e = 0.05
        m = (arr[:, 0] >= b['x0'] - e) & (arr[:, 2] <= b['x1'] + e) & (arr[:, 1] >= b['y0'] - e) & (arr[:, 3] <= b['y1'] + e)
        L = arr[m, 4]
        cs = cols[m]
        Lt = float(L.sum()) or 1.0
        fr = lambda k: round(float(L[cs == k].sum()) / Lt, 3)
        c0, r1 = self.a_px(b['x0'], b['y0'])
        c1, r0 = self.a_px(b['x1'], b['y1'])
        sub = self.img[max(0, int(r0)):int(r1) + 1, max(0, int(c0)):int(c1) + 1]
        dens = float(sub.mean() / 255.0) if sub.size else 0.0
        return dict(w_mm=round(b['w'] * self.escala, 2), h_mm=round(b['h'] * self.escala, 2), trazos=int((L > 0.3).sum()),
                    largo_pt2=round(Lt / max(1e-6, b['w'] * b['h']), 3), densidad=round(dens, 4), verde=fr('verde'), azul=fr('azul'))

    # ------------------------------------------------------------------------------ parches y snap
    def parche(self, x, y, medio=MEDIO_PARCHE):
        c, r = self.a_px(x, y)
        c, r = int(round(c)), int(round(r))
        k = int(round(medio * S))
        sub = self.img[r - k:r + k + 1, c - k:c + k + 1]
        if sub.shape != (2 * k + 1, 2 * k + 1):
            return None
        return (sub > 0).astype(np.uint8)

    def ajustar(self, x, y, parche, R=R_SNAP, escala_parche=None):
        """Busca el parche del ejemplo alrededor de (x, y), hasta R pt.  Devuelve (x, y, score, desplazamiento)."""
        if parche is None or R <= 0.05:
            return x, y, None, 0.0
        pt = parche.astype(np.float32)
        if escala_parche and abs(escala_parche - 1) > 0.01:
            n = int(round(pt.shape[0] * escala_parche)) | 1
            pt = cv2.resize(pt, (n, n), interpolation=cv2.INTER_AREA)
        pt = cv2.GaussianBlur(pt, (3, 3), 0.8)
        if pt.std() < 1e-3:
            return x, y, None, 0.0
        k = pt.shape[0] // 2
        rr = int(math.ceil(R * S))
        c, r = self.a_px(x, y)
        c, r = int(round(c)), int(round(r))
        sub = self.imgf[r - k - rr:r + k + rr + 1, c - k - rr:c + k + rr + 1]
        if sub.shape != (2 * (k + rr) + 1, 2 * (k + rr) + 1):
            return x, y, None, 0.0
        res = cv2.matchTemplate(sub, pt, cv2.TM_CCOEFF_NORMED)
        yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]
        res = np.where(xx * xx + yy * yy <= rr * rr, res, -1)
        j = np.unravel_index(np.argmax(res), res.shape)
        sc = float(res[j])
        # si el dibujo es parejo (una banda, un borde largo) muchas posiciones empatan: solo se mueve si mejora de verdad
        if sc < float(res[rr, rr]) + 0.03:
            j = (rr, rr)
            sc = float(res[j])
        dy, dx = j[0] - rr, j[1] - rr
        # refinamiento subpixel (parabola en cada eje)
        def sub_px(a, b, cc):
            den = a - 2 * b + cc
            return 0.0 if abs(den) < 1e-9 else 0.5 * (a - cc) / den
        fx = sub_px(res[j[0], j[1] - 1], res[j], res[j[0], j[1] + 1]) if 0 < j[1] < res.shape[1] - 1 else 0
        fy = sub_px(res[j[0] - 1, j[1]], res[j], res[j[0] + 1, j[1]]) if 0 < j[0] < res.shape[0] - 1 else 0
        fx = max(-0.5, min(0.5, fx if np.isfinite(fx) else 0))
        fy = max(-0.5, min(0.5, fy if np.isfinite(fy) else 0))
        nx = float(x + (dx + fx) / S)
        ny = float(y - (dy + fy) / S)
        if sc < SCORE_SNAP:
            return x, y, sc, 0.0
        return nx, ny, sc, math.hypot(nx - x, ny - y)

    def radio(self, x, y):
        """Radio de la boca/tornillo en (x, y), en pt.  1) Si hay trazos que forman un circulo (o un poligono
        regular) centrado en el punto, su radio (el menor que da la vuelta, hasta 4 pt).  2) Si no, mediana de 16 rayos hasta el
        primer trazo del raster."""
        grupos = []
        for lay, op, p, c in self.st:
            if lay not in CAPAS or op != 'S' or len(p) < 3 or es_blanco(c):
                continue
            b = bbox(p)
            if b[2] < x - 7 or b[0] > x + 7 or b[3] < y - 7 or b[1] > y + 7:
                continue
            d = [math.hypot(a - x, bb - y) for a, bb in p]
            md = sum(d) / len(d)
            if not (0.5 < md < 4.0) or max(d) - min(d) > 0.12 * md + 0.05:
                continue
            angs = [math.degrees(math.atan2(bb - y, a - x)) % 360 for a, bb in p]
            for g in grupos:
                if abs(g['r'] - md) < 0.08 * md + 0.03:
                    g['angs'] += angs
                    break
            else:
                grupos.append(dict(r=md, angs=angs))
        buenos = []
        for g in grupos:
            a = sorted(g['angs'])
            gaps = [(a[(i + 1) % len(a)] - a[i]) % 360 for i in range(len(a))]
            if 360 - max(gaps) >= 240:
                buenos.append(g['r'])
        if buenos:
            return round(min(buenos), 2)
        c0, r0 = self.a_px(x, y)
        ds = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            d = None
            for s in np.arange(0.35, 4.0, 0.05):
                c = int(round(c0 + math.cos(a) * s * S))
                r = int(round(r0 - math.sin(a) * s * S))
                if 0 <= r < self.img.shape[0] and 0 <= c < self.img.shape[1] and self.img[r, c]:
                    d = s
                    break
            ds.append(d if d is not None else 4.0)
        return round(float(np.median(ds)), 2)

    # ------------------------------------------------------------------------------ bocas / tornillos dibujados
    def _circulos(self):
        """Todos los circulos dibujados (bocas, tornillos, esparragos) de la zona: cada trazo curvo se ajusta a
        un circulo y los arcos del mismo centro y radio se juntan (muchas bocas son dos medias circunferencias).
        Queda (cx, cy, r, cobertura en grados).  Tambien entran poligonos regulares chicos (octogonos)."""
        if hasattr(self, '_circ'):
            return self._circ
        arcos = []
        for lay, op, p, c in self.st:
            if lay not in CAPAS or op != 'S' or len(p) < 3 or es_blanco(c):
                continue
            x0, y0, x1, y1 = bbox(p)
            if x1 < self.X0 or x0 > self.X1 or y1 < self.Y0 or y0 > self.Y1:
                continue
            if max(x1 - x0, y1 - y0) > 20 or max(x1 - x0, y1 - y0) < 0.5:
                continue
            if len(p) == 3:
                # arco de Bezier aplanado en 3 puntos: circulo por los 3 puntos, si parece un arco (angulo en el
                # punto del medio >= 115 grados y cuerdas parecidas), no una esquina en L
                (ax, ay), (bx, by), (qx, qy) = p
                l1, l2 = math.hypot(bx - ax, by - ay), math.hypot(qx - bx, qy - by)
                if min(l1, l2) < 0.05 or max(l1, l2) > 1.35 * min(l1, l2):
                    continue
                cosang = ((ax - bx) * (qx - bx) + (ay - by) * (qy - by)) / (l1 * l2)
                if math.degrees(math.acos(max(-1, min(1, cosang)))) < 115:
                    continue
                den = 2 * (ax * (by - qy) + bx * (qy - ay) + qx * (ay - by))
                if abs(den) < 1e-9:
                    continue
                cx = ((ax * ax + ay * ay) * (by - qy) + (bx * bx + by * by) * (qy - ay) + (qx * qx + qy * qy) * (ay - by)) / den
                cy = ((ax * ax + ay * ay) * (qx - bx) + (bx * bx + by * by) * (ax - qx) + (qx * qx + qy * qy) * (bx - ax)) / den
                r = math.hypot(ax - cx, ay - cy)
                if not (0.5 <= r <= 9.0):
                    continue
                t0 = math.atan2(ay - cy, ax - cx)
                t2 = math.atan2(qy - cy, qx - cx)
                span = (t2 - t0 + 3 * math.pi) % (2 * math.pi) - math.pi
                th = t0 + np.linspace(0, span, max(2, int(abs(math.degrees(span)) / 5)) + 1)
                arcos.append((cx, cy, r, np.c_[cx + r * np.cos(th), cy + r * np.sin(th)]))
                continue
            a = np.array(p, float)
            A = np.c_[a[:, 0], a[:, 1], np.ones(len(a))]
            bb = -(a[:, 0] ** 2 + a[:, 1] ** 2)
            try:
                sol, *_ = np.linalg.lstsq(A, bb, rcond=None)
            except np.linalg.LinAlgError:
                continue
            cx, cy = -sol[0] / 2, -sol[1] / 2
            r2 = cx * cx + cy * cy - sol[2]
            if r2 <= 0:
                continue
            r = math.sqrt(r2)
            if not (0.5 <= r <= 9.0):
                continue
            d = np.hypot(a[:, 0] - cx, a[:, 1] - cy)
            if np.abs(d - r).max() > 0.09 * r + 0.03:
                continue
            # angulos de los puntos y de los tramos (se densifica para que un tramo largo cuente como cubierto)
            th = np.unwrap(np.arctan2(a[:, 1] - cy, a[:, 0] - cx))
            dens = np.concatenate([np.linspace(th[i], th[i + 1], 6, endpoint=False) for i in range(len(th) - 1)] + [th[-1:]])
            # tramos rectos largos (poligono de pocos lados) no son arco, salvo que el poligono sea cerrado
            if len(a) < 6 and np.abs(np.diff(th)).max() > math.radians(50):
                continue
            arcos.append((cx, cy, r, np.c_[cx + r * np.cos(dens), cy + r * np.sin(dens)]))
        # juntar arcos de la misma boca: radio parecido y centros cercanos (las bocas ovaladas son arcos con
        # centros un poco corridos); el centro de la boca es el del recuadro de todos sus puntos
        grupos = []
        for cx, cy, r, pts in sorted(arcos, key=lambda t: t[2]):
            for g in grupos:
                if abs(g[2] - r) < 0.06 * r + 0.03 and math.hypot(g[0] - cx, g[1] - cy) < 0.25 * r + 0.05:
                    g[3].append(pts)
                    g[4].append(r)
                    break
            else:
                grupos.append([cx, cy, r, [pts], [r]])
        out = []
        for _, _, _, lp, rs in grupos:
            a = np.concatenate(lp)
            cx = (a[:, 0].min() + a[:, 0].max()) / 2
            cy = (a[:, 1].min() + a[:, 1].max()) / 2
            ang = np.sort(np.degrees(np.arctan2(a[:, 1] - cy, a[:, 0] - cx)) % 360)
            gaps = np.diff(np.r_[ang, ang[0] + 360])
            cob = 360 - gaps.max()
            if cob >= 250:
                r = float(np.median(np.hypot(a[:, 0] - cx, a[:, 1] - cy)))
                out.append((round(cx, 3), round(cy, 3), round(r, 3), round(float(cob), 1)))
        self._circ = out
        return out

    def bocas(self, x0, y0, x1, y1, rmin=0.8, rmax=4.5):
        """Bocas/tornillos dentro del rectangulo: circulos de radio rmin..rmax; de los concentricos queda el mas
        chico (la boca dentro del anillo del tornillo)."""
        cs = [c for c in self._circulos() if x0 <= c[0] <= x1 and y0 <= c[1] <= y1 and rmin <= c[2] <= rmax]
        cs.sort(key=lambda c: c[2])
        out = []
        for c in cs:
            if any(math.hypot(c[0] - o[0], c[1] - o[1]) < 0.35 * max(c[2], o[2]) for o in out):
                continue
            out.append(c)
        return out

    def aberturas(self, x0, y0, x1, y1, rmin=1.2, rmax=3.0):
        """Bocas que NO son un circulo cerrado (estadio, circulo cortado por rectas: la entrada push-in de un
        PT 2,5-DIO, por ejemplo).  Se juntan los arcos de radio rmin..rmax con centro de curvatura parecido
        (los dos medios circulos de un estadio tienen centros un poco corridos) y la boca es el centro del
        recuadro de todos sus arcos.  Tienen que rodear el centro (cobertura >= 200 grados).  Solo se usa cuando
        la base todavia no tiene ejemplos del modelo (disposicion de la hoja de datos)."""
        arcos = []
        for lay, op, p, c in self.st:
            if lay not in CAPAS or op != 'S' or len(p) not in (3, 4) or es_blanco(c):
                continue
            bx0, by0, bx1, by1 = bbox(p)
            if bx1 < x0 - 3 or bx0 > x1 + 3 or by1 < y0 - 3 or by0 > y1 + 3:
                continue
            (ax, ay), (bx, by), (qx, qy) = p[0], p[len(p) // 2], p[-1]
            den = 2 * (ax * (by - qy) + bx * (qy - ay) + qx * (ay - by))
            if abs(den) < 1e-9:
                continue
            cx = ((ax * ax + ay * ay) * (by - qy) + (bx * bx + by * by) * (qy - ay) + (qx * qx + qy * qy) * (ay - by)) / den
            cy = ((ax * ax + ay * ay) * (qx - bx) + (bx * bx + by * by) * (ax - qx) + (qx * qx + qy * qy) * (bx - ax)) / den
            r = math.hypot(ax - cx, ay - cy)
            if not (rmin <= r <= rmax) or math.dist(p[0], p[-1]) < 0.3:
                continue
            # todos los puntos a la misma distancia del centro (es un arco, no una esquina)
            if max(abs(math.hypot(a - cx, b - cy) - r) for a, b in p) > 0.1 * r:
                continue
            arcos.append((cx, cy, r, p))
        grupos = []
        for cx, cy, r, p in sorted(arcos, key=lambda t: t[2]):
            for g in grupos:
                if abs(g['r'] - r) < 0.25 * r and math.hypot(g['cx'] - cx, g['cy'] - cy) < 0.6 * r:
                    g['pts'] += list(p)
                    break
            else:
                grupos.append(dict(cx=cx, cy=cy, r=r, pts=list(p)))
        out = []
        for g in grupos:
            a = np.array(g['pts'])
            cx = (a[:, 0].min() + a[:, 0].max()) / 2
            cy = (a[:, 1].min() + a[:, 1].max()) / 2
            if not (x0 <= cx <= x1 and y0 <= cy <= y1):
                continue
            ang = np.sort(np.degrees(np.arctan2(a[:, 1] - cy, a[:, 0] - cx)) % 360)
            cob = 360 - np.diff(np.r_[ang, ang[0] + 360]).max()
            if cob < 200:
                continue
            rr = float((a[:, 0].max() - a[:, 0].min() + a[:, 1].max() - a[:, 1].min()) / 4)
            out.append((round(float(cx), 3), round(float(cy), 3), round(rr, 3), round(float(cob), 1)))
        return out

    def puentes(self):
        """Puentes enchufables (FBS) dibujados: barras rellenas de color saturado (azul, rojo...), de cualquier capa,
        mas anchas que altas y de menos de 4 pt de alto.  [(x0, y0, x1, y1)]."""
        if hasattr(self, '_puentes'):
            return self._puentes
        out = []
        for lay, op, p, c in self.st:
            if op not in ('f', 'F', 'f*', 'B', 'b') or not c or len(p) < 4:
                continue
            if max(c) - min(c) < 0.5:
                continue
            x0, y0, x1, y1 = bbox(p)
            if x1 < self.X0 or x0 > self.X1 or y1 < self.Y0 or y0 > self.Y1:
                continue
            if 0.8 <= y1 - y0 <= 4.0 and x1 - x0 >= 2.5 * (y1 - y0):
                out.append((x0, y0, x1, y1))
        self._puentes = out
        return out

    def circulo_cerca(self, x, y, r, dmax=1.0, tol_r=0.2):
        """Centro del circulo de radio ~r mas cercano a (x, y), a menos de dmax pt.  None si no hay."""
        best = None
        for c in self._circulos():
            if abs(c[0] - x) > dmax or abs(c[1] - y) > dmax:
                continue
            if abs(c[2] - r) > tol_r * r + 0.05:
                continue
            d = math.hypot(c[0] - x, c[1] - y)
            if d <= dmax and (best is None or d < best[0]):
                best = (d, c)
        return best[1] if best else None

    def circulo_en(self, x, y, dmax=0.35):
        """El circulo dibujado cuyo centro esta en (x, y) (a menos de dmax pt).  De los concentricos (boca dentro del
        anillo del tornillo, esparrago con arandela) se queda el mas chico.  None si el punto no es centro de un circulo."""
        cs = [c for c in self._circulos() if abs(c[0] - x) <= dmax and abs(c[1] - y) <= dmax
              and math.hypot(c[0] - x, c[1] - y) <= dmax and 0.5 <= c[2] <= 9.0]
        return min(cs, key=lambda c: c[2]) if cs else None

    # ------------------------------------------------------------------------------ busqueda de recuadros
    def cajas_que_contienen(self, x, y, margen=0.3):
        return [b for b in self.cajas if b['x0'] - margen <= x <= b['x1'] + margen and b['y0'] - margen <= y <= b['y1'] + margen]

    def marcos_a_la_derecha(self, tx, y0, y1):
        """x de los rotulos amarillos que estan a la derecha de tx y a la altura [y0, y1]."""
        out = []
        for m in self.marcos:
            xc, yc = (m[0] + m[2]) / 2, (m[1] + m[3]) / 2
            if xc > tx + 1.0 and y0 <= yc <= y1:
                out.append(m[0])
        return sorted(out)


def tam_ok(b, w, h, tw, th):
    return abs(b['w'] / w - 1) <= tw and abs(b['h'] / h - 1) <= th


def sin_solapes(cajas, w):
    """Cajas ordenadas por x sin repetir la misma unidad (mascara y contorno del mismo bloque): gana la mascara."""
    out = []
    for c in sorted(cajas, key=lambda c: c['x0']):
        if out and abs(c['x0'] - out[-1]['x0']) < 0.5 * w:
            if out[-1]['fuente'] != 'mascara' and c['fuente'] == 'mascara':
                out[-1] = c
            continue
        out.append(c)
    return out


# ----------------------------------------------------------------------------------------- parches <-> texto
def parche_a_txt(p):
    if p is None:
        return None
    n = p.shape[0]
    return f'{n}:' + base64.b64encode(np.packbits(p.flatten()).tobytes()).decode('ascii')


def txt_a_parche(t):
    if not t:
        return None
    n, d = t.split(':', 1)
    n = int(n)
    bits = np.unpackbits(np.frombuffer(base64.b64decode(d), np.uint8))[:n * n]
    return bits.reshape(n, n).astype(np.uint8)


# ----------------------------------------------------------------------------------------- base
def cargar_base(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def guardar_base(base, path):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(base, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


# ----------------------------------------------------------------------------------------- reglas de texto
LADOS = ('ARRIBA', 'ABAJO')


def norm(s):
    return re.sub(r'\s+', '', (s or '').upper())


def partir_texto(texto, tag):
    """'43KR2 A1' con tag '43KR' -> ('2', 'A1', None);  '81XCM 5 ARRIBA' -> (None, '5', 'ARRIBA')."""
    toks = texto.split()
    if not toks:
        return None, '', None
    first = toks[0]
    sufijo = None
    if first != tag and first.upper().startswith(tag.upper()):
        sufijo = first[len(tag):]
    resto = toks[1:]
    lado = None
    if resto and resto[-1].upper() in LADOS:
        lado = resto[-1].upper()
        resto = resto[:-1]
    return sufijo, ' '.join(resto), lado


def resolver_uso(modelo, tag, uso):
    """Traduce el texto del instructivo a (unidad, borne) segun la regla del modelo.
    unidad = numero de pieza/modulo contando desde la etiqueta (1 = la primera a la derecha);
    borne = nombre del punto dentro de la unidad (como esta en la base).  Devuelve None si no se entiende.
    Si hay que desempatar entre varios bornes (dos usos '-Vo'), devuelve una lista de bornes."""
    regla = modelo['regla']
    tipo = regla['tipo']
    suf, cuerpo, lado = partir_texto(uso['texto'], tag)
    c = norm(cuerpo)
    if tipo == 'quattro':
        m = re.match(r'^(\d+)\.(\d)$', c)
        if not m and uso.get('punto') and re.match(r'^\d+$', c):
            m = re.match(r'^(\d+)\.(\d)$', f"{c}.{uso['punto']}")
        if not m:
            return None
        return int(m.group(1)), m.group(2)
    if tipo == 'doble_piso':
        m = re.match(r'^(\d+)$', c)
        if not m or not lado:
            return None
        n = int(m.group(1))
        return (n + 1) // 2, f"{lado}_{'EXT' if n % 2 else 'INT'}"
    if tipo == 'dio':
        m = re.match(r'^(\d+)$', c)
        if not m or not lado:
            return None
        return int(m.group(1)), lado
    if tipo == 'modulos':
        borne = c
        if borne not in [norm(b) for b in modelo.get('bornes', [])]:
            return None
        if suf and re.match(r'^\d+$', suf):
            return int(suf), borne
        return 0, borne          # modulo sin numero: se decide despues (ver desempatar_modulos)
    if tipo == 'polos':
        polos = [norm(p) for p in regla['polos']]
        if not lado:
            return None
        if c in polos:
            return 1, f'P{polos.index(c) + 1}_{lado}'
        if len(polos) == 1 and c == '':
            return 1, f'P1_{lado}'
        return None
    if tipo == 'tabla':
        tabla = {norm(k): v for k, v in regla['tabla'].items()}
        claves = []
        if not regla.get('ignorar_lado') and lado:
            claves.append(c + lado)
        claves.append(c)
        if c == '':
            claves.append('|' + (uso.get('lado') or ''))
        for k in claves:
            if k in tabla and k != '':
                return 1, tabla[k]
        return None
    return None


# ----------------------------------------------------------------------------------------- lista de materiales
def modelos_de_lista(path, base):
    """{tag: clave_modelo} leyendo lista_materiales.txt (lineas 'TAG | descripcion | marca | modelo')."""
    if not path or not os.path.exists(path):
        return {}
    alias = []
    for k, m in base['modelos'].items():
        for a in m.get('alias', []):
            alias.append((len(a), a, k))
    alias.sort(reverse=True)
    out = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for linea in f:
            campos = [c.strip() for c in linea.split('|')]
            tags = []
            for i, c in enumerate(campos[:2]):
                if re.match(r'^\d+[A-Z]+[A-Z0-9]*$', c):
                    tags.append(c)
                    if i + 1 < len(campos) and re.match(r'^/\d+$', campos[i + 1]):
                        tags.append(c[:-1] + campos[i + 1][1:])      # '43DIB1 | /2' = 43DIB1 y 43DIB2
                    break
            if not tags:
                continue
            for _, a, k in alias:
                if re.search(a, linea, re.I):
                    for t in tags:
                        out.setdefault(t, k)
                    break
    return out


def num_cable(c):
    d = re.sub(r'\D', '', str(c or ''))
    return int(d) if d else 0
