"""Vision por imagen para ubicar bornes en un plano topografico.

Todo trabaja sobre la IMAGEN de la pagina (render con pypdfium2), no sobre los trazos vectoriales:
el mismo codigo sirve para un PDF escaneado o exportado de otro CAD (se renderiza igual).

Coordenadas: siempre en puntos PDF con origen abajo-izquierda (como el programa del taller).
Una Zona es un recorte renderizado a S px/pt; zona.pt(j, i) pasa de pixel (continuo) a punto.
"""
import math
import os

import cv2
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

S = 10  # px por punto con el que se renderiza y con el que estan guardadas las plantillas


class Zona:
    def __init__(self, bgr, x0, y1, s):
        self.bgr = bgr
        self.gris = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        self.x0, self.y1, self.s = x0, y1, s
        self.h, self.w = self.gris.shape

    def pt(self, j, i):
        """pixel continuo (columna j, fila i) -> punto PDF (x, y)"""
        return self.x0 + j / self.s, self.y1 - i / self.s

    def px(self, x, y):
        """punto PDF -> pixel continuo (j, i)"""
        return (x - self.x0) * self.s, (self.y1 - y) * self.s


class Plano:
    def __init__(self, pdf_path, pagina_idx):
        self.pdf = pdfium.PdfDocument(pdf_path)
        self.pg = self.pdf[pagina_idx]
        self.W, self.H = self.pg.get_size()
        self.res_fuente = None  # px/pt de la imagen escaneada que tapa la pagina (None = dibujo vectorial)

    def medir_resolucion(self, region):
        """Si la region esta tapada por una imagen (plano escaneado o exportado como imagen), guarda su resolucion
        en px/pt. En un PDF vectorial (o con solo un logo chico) queda None."""
        x0, y0, x1, y1 = region
        area = max(1e-6, (x1 - x0) * (y1 - y0))
        res = []
        for o in self.pg.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=4):
            a, b, c, d = o.get_bounds()
            inter = max(0, min(c, x1) - max(a, x0)) * max(0, min(d, y1) - max(b, y0))
            if inter > 0.5 * area:
                w, h = o.get_px_size()
                res.append(min(w / max(1e-6, c - a), h / max(1e-6, d - b)))
        self.res_fuente = min(res) if res else None
        return self.res_fuente

    def sigma_px(self, fraccion=0.5, s=S):
        """Suavizado para comparar plantillas: 0,8 px en un plano vectorial; en uno escaneado, 'fraccion' de un
        pixel de la imagen original (pasado a los px de trabajo)."""
        if not self.res_fuente or self.res_fuente >= s:
            return 0.8
        return max(0.8, fraccion * s / self.res_fuente)

    def zona(self, x0, y0, x1, y1, s=S):
        # bordes redondeados a 1/s pt para que cada pixel caiga en una grilla fija
        x0 = math.floor(x0 * s) / s; y0 = math.floor(y0 * s) / s
        x1 = math.ceil(x1 * s) / s; y1 = math.ceil(y1 * s) / s
        x0 = max(0.0, x0); y0 = max(0.0, y0); x1 = min(self.W, x1); y1 = min(self.H, y1)
        bm = self.pg.render(scale=s, crop=(x0, y0, self.W - x1, self.H - y1))
        a = bm.to_numpy()[:, :, :3].copy()  # BGR
        return Zona(a, x0, y1, s)


# ----------------------------------------------------------------------------------------------
# Etiquetas amarillas
# ----------------------------------------------------------------------------------------------
def etiquetas_amarillas(plano, region=None, s=4):
    """Cajas de las etiquetas amarillas (relleno amarillo) en la region [x0,y0,x1,y1] (pt).
    Devuelve lista de dict(x0,y0,x1,y1,xc,yc,vertical)."""
    if region is None:
        region = (0, 0, plano.W, plano.H)
    z = plano.zona(*region, s=s)
    hsv = cv2.cvtColor(z.bgr, cv2.COLOR_BGR2HSV)
    m = ((hsv[:, :, 0] >= 20) & (hsv[:, :, 0] <= 38) & (hsv[:, :, 1] >= 120) & (hsv[:, :, 2] >= 170)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for k in range(1, n):
        bx, by, bw, bh, area = st[k]
        if bw < 2.5 * s or bh < 2.5 * s or area < 0.35 * bw * bh:
            continue
        xa, yb = z.pt(bx, by + bh)
        xb, ya = z.pt(bx + bw, by)
        out.append(dict(x0=xa, y0=yb, x1=xb, y1=ya, xc=(xa + xb) / 2, yc=(ya + yb) / 2, vertical=bh > bw))
    return out


# ----------------------------------------------------------------------------------------------
# Plantillas
# ----------------------------------------------------------------------------------------------
class Plantilla:
    def __init__(self, nombre, gris, ancla, r_pt, s=S, info=None, mascara=None):
        self.nombre, self.gris, self.ancla, self.r_pt, self.s = nombre, gris, ancla, r_pt, s
        self.mascara = mascara
        self.info = info or {}
        self._cache = {}

    @staticmethod
    def cargar(nombre, d, carpeta):
        g = cv2.imread(os.path.join(carpeta, d['png']), cv2.IMREAD_GRAYSCALE)
        m = None
        if d.get('mascara_png'):
            m = (cv2.imread(os.path.join(carpeta, d['mascara_png']), cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8)
        return Plantilla(nombre, g, tuple(d['ancla_px']), d['r_pt'], d.get('px_por_pt', S), d, m)

    def variante(self, var, escala, res=None):
        """Plantilla transformada (espejo/giro) y escalada; devuelve (img float32, (ax, ay), mascara).
        res: resolucion (px/pt) del escaneo, si el plano es una imagen de menos resolucion que la de trabajo: la
        plantilla se "degrada" igual que el escaneo (se achica a esa resolucion y se vuelve a agrandar)."""
        key = (var, round(escala, 3), None if res is None else round(res, 2))
        if key in self._cache:
            return self._cache[key]
        g = self.gris
        m = self.mascara if self.mascara is not None else np.ones_like(g, np.uint8)
        ax, ay = self.ancla
        h, w = g.shape
        if var == 'espejo_v':
            g = g[::-1, :]; m = m[::-1, :]; ay = h - ay
        elif var == 'espejo_h':
            g = g[:, ::-1]; m = m[:, ::-1]; ax = w - ax
        elif var == 'giro180':
            g = g[::-1, ::-1]; m = m[::-1, ::-1]; ax = w - ax; ay = h - ay
        if abs(escala - 1) > 1e-3:
            nw, nh = max(3, int(round(w * escala))), max(3, int(round(h * escala)))
            g = cv2.resize(g, (nw, nh), interpolation=cv2.INTER_AREA)
            m = cv2.resize(m, (nw, nh), interpolation=cv2.INTER_NEAREST)
            ax, ay = ax * nw / w, ay * nh / h
        if res is not None and res < self.s:
            hh, ww = g.shape
            f = res / self.s
            chica = cv2.resize(np.ascontiguousarray(g), (max(2, int(round(ww * f))), max(2, int(round(hh * f)))), interpolation=cv2.INTER_AREA)
            g = cv2.resize(chica, (ww, hh), interpolation=cv2.INTER_LINEAR)
        m = np.ascontiguousarray(m).astype(np.float32)
        res = (np.ascontiguousarray(g).astype(np.float32), (ax, ay), None if self.mascara is None else m)
        self._cache[key] = res
        return res


def _suave(g, sigma=0.8):
    return cv2.GaussianBlur(g.astype(np.float32), (0, 0), sigma)


def buscar(zona, plantilla, variantes=('normal',), escalas=(1.0,), umbral=0.55, dist_min_pt=None, mascara=None, sigma=0.8, res=None,
           umbral_rel=None):
    """cv2.matchTemplate (TM_CCOEFF_NORMED) de una plantilla en una zona, con varias variantes/escalas.
    Antes de comparar, la zona y la plantilla se suavizan igual (sigma en px): en un plano escaneado de baja
    resolucion se suaviza mas, para que la plantilla (nitida) y la imagen (borrosa) se parezcan.
    Supresion de no-maximos: queda el mejor pico dentro de dist_min_pt.
    Devuelve lista de dict(x, y, score, var, escala) con (x, y) = ancla de la plantilla en pt."""
    img = _suave(zona.gris, sigma)
    cand = []
    for esc in escalas:
        for var in variantes:
            t, (ax, ay), m = plantilla.variante(var, esc, res)
            th, tw = t.shape
            if th >= zona.h or tw >= zona.w:
                continue
            if m is None:
                R = cv2.matchTemplate(img, _suave(t, sigma), cv2.TM_CCOEFF_NORMED)
            else:
                R = cv2.matchTemplate(img, _suave(t, sigma), cv2.TM_CCOEFF_NORMED, mask=m)
            R = np.nan_to_num(R, nan=-1.0, posinf=-1.0, neginf=-1.0)
            k = max(3, int(0.6 * min(th, tw)) | 1)
            mx = cv2.dilate(R, np.ones((k, k), np.uint8))
            ii, jj = np.where((R >= mx - 1e-7) & (R >= umbral))
            for i, j in zip(ii, jj):
                sc = float(R[i, j])
                # refinamiento sub-pixel (parabola)
                dj = di = 0.0
                if 0 < j < R.shape[1] - 1:
                    a, b, c = R[i, j - 1], R[i, j], R[i, j + 1]
                    den = a - 2 * b + c
                    if den < 0:
                        dj = float(np.clip(0.5 * (a - c) / den, -0.5, 0.5))
                if 0 < i < R.shape[0] - 1:
                    a, b, c = R[i - 1, j], R[i, j], R[i + 1, j]
                    den = a - 2 * b + c
                    if den < 0:
                        di = float(np.clip(0.5 * (a - c) / den, -0.5, 0.5))
                x, y = zona.pt(j + dj + ax, i + di + ay)
                if mascara is not None and not mascara(x, y):
                    continue
                cand.append(dict(x=x, y=y, score=sc, var=var, escala=esc))
    if dist_min_pt is None:
        dist_min_pt = 0.8 * plantilla.r_pt * max(escalas)
    cand.sort(key=lambda c: -c['score'])
    if umbral_rel and cand:  # plano escaneado: vale solo lo que se parece casi tanto como la mejor boca de la zona
        cand = [c for c in cand if c['score'] >= umbral_rel * cand[0]['score']]
    out = []
    for c in cand:
        if all(math.hypot(c['x'] - o['x'], c['y'] - o['y']) >= dist_min_pt for o in out):
            out.append(c)
    return out


# ----------------------------------------------------------------------------------------------
# Ancla de una plantilla (para armar la base): centro de la boca a partir de un clic aproximado
# ----------------------------------------------------------------------------------------------
def anclar(plano, x, y, r_pt, modo='contorno', s=S, umbral=170, con_mancha=False):
    """Centro de la boca/tornillo cerca del punto (x, y), mirando solo la imagen.
    modo 'contorno': se rellenan los huecos cerrados, se abre con un disco de 0.5 r (se borran las rayas
                     finas) y se toma el centro de la caja de la mancha que queda (el contorno exterior).
    modo 'hueco':    centro de la caja del hueco blanco que contiene el punto (circulos concentricos).
    modo 'ancho_maximo': x del centro de la mancha, y en la fila donde la mancha es mas ancha
                     (tornillos cortados por el borde de la carcasa)."""
    half = 1.7 * r_pt
    z = plano.zona(x - half, y - half, x + half, y + half, s=s)
    ink = (z.gris < umbral).astype(np.uint8)
    pj, pi = z.px(x, y)
    pj, pi = int(pj), int(pi)
    if modo == 'hueco':
        n, lab, st, _ = cv2.connectedComponentsWithStats(1 - ink, connectivity=4)
        k = lab[pi, pj]
        bx, by, bw, bh, _ = st[k]
        cx, cy = z.pt(bx + bw / 2, by + bh / 2)
        if con_mancha:
            yy, xx = np.mgrid[0:z.h, 0:z.w]
            mj, mi = z.px(cx, cy)
            mancha = (np.hypot(xx + 0.5 - mj, yy + 0.5 - mi) <= r_pt * s).astype(np.uint8)
            return cx, cy, bw / s, bh / s, (z, mancha)
        return cx, cy, bw / s, bh / s
    n, lab = cv2.connectedComponents(1 - ink, connectivity=4)
    borde = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
    filled = ink.copy()
    for k in range(1, n):
        if k not in borde:
            filled[lab == k] = 1
    kk = max(3, int(round(0.5 * r_pt * s)) | 1)
    op = cv2.morphologyEx(filled, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kk, kk)))
    n2, lab2, st, cen = cv2.connectedComponentsWithStats(op)
    k = lab2[pi, pj]
    if k == 0:
        k = min(range(1, n2), key=lambda q: math.hypot(cen[q][0] - pj, cen[q][1] - pi))
    bx, by, bw, bh, _ = st[k]
    if modo == 'ancho_maximo':
        filas = (lab2[by:by + bh, bx:bx + bw] == k).sum(axis=1)
        imax = np.flatnonzero(filas >= filas.max() - 0.5)
        fi = by + (imax.min() + imax.max() + 1) / 2
        cx, cy = z.pt(bx + bw / 2, fi)
    else:
        cx, cy = z.pt(bx + bw / 2, by + bh / 2)
    if con_mancha:
        mancha = (lab2 == k).astype(np.uint8)
        return cx, cy, bw / s, bh / s, (z, mancha)
    return cx, cy, bw / s, bh / s


def recortar(plano, cx, cy, ancho_pt, alto_pt, s=S):
    """Recorte en gris de ancho_pt x alto_pt centrado en (cx, cy); devuelve (gris, ancla_px)."""
    z = plano.zona(cx - ancho_pt / 2, cy - alto_pt / 2, cx + ancho_pt / 2, cy + alto_pt / 2, s=s)
    ax, ay = z.px(cx, cy)
    return z.gris.copy(), (ax, ay)


# ----------------------------------------------------------------------------------------------
# Color
# ----------------------------------------------------------------------------------------------
def fraccion_color(zona, x0, y0, x1, y1, color):
    """Fraccion de pixeles con tinta de un color ('verde', 'rojo', 'azul') dentro del rectangulo (pt),
    respecto de todos los pixeles con tinta."""
    j0, i0 = zona.px(x0, y1); j1, i1 = zona.px(x1, y0)
    j0, i0 = max(0, int(j0)), max(0, int(i0)); j1, i1 = min(zona.w, int(j1) + 1), min(zona.h, int(i1) + 1)
    if j1 <= j0 or i1 <= i0:
        return 0.0
    b = zona.bgr[i0:i1, j0:j1].astype(np.int16)
    B, G, R = b[:, :, 0], b[:, :, 1], b[:, :, 2]
    tinta = (b.min(axis=2) < 200)
    if color == 'verde':
        c = (G > R + 40) & (G > B + 40)
    elif color == 'rojo':
        c = (R > G + 80) & (R > B + 80)
    elif color == 'azul':
        c = (B > R + 80) & (B > G + 80)
    else:
        raise ValueError(color)
    nt = int(tinta.sum())
    return float((c & tinta).sum()) / nt if nt else 0.0


def rellenos_color(zona, x0, y0, x1, y1, color, min_area_pt2=2.0):
    """Manchas rellenas de un color (puentes FBS dibujados como rectangulos llenos). Devuelve centros (pt)."""
    b = zona.bgr.astype(np.int16)
    B, G, R = b[:, :, 0], b[:, :, 1], b[:, :, 2]
    if color == 'rojo':
        m = (R > 180) & (G < 90) & (B < 90)
    elif color == 'azul':
        m = (B > 180) & (R < 90) & (G < 90)
    else:
        m = ((R > 180) & (G < 90) & (B < 90)) | ((B > 180) & (R < 90) & (G < 90))
    m = m.astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    out = []
    for k in range(1, n):
        if st[k][4] / zona.s ** 2 < min_area_pt2:
            continue
        x, y = zona.pt(cen[k][0] + 0.5, cen[k][1] + 0.5)
        if x0 <= x <= x1 and y0 <= y <= y1:
            out.append((x, y, st[k][4] / zona.s ** 2))
    return out
