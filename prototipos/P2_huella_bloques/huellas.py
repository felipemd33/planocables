"""Huellas de bloques CAD: biblioteca comun de aprender.py, mapear.py y validar_loo.py.

Idea: el topografico se dibuja con bloques de biblioteca. Cada instancia de un bloque es una copia exacta
del mismo dibujo (mismos segmentos, solo trasladados y a veces girados). Entonces:

  * La HUELLA de un bloque es su lista de segmentos, en coordenadas relativas al centro del bloque
    (el ANCLA), mas el color dominante del trazo.
  * Para encontrar el bloque en un plano se usa HASHING GEOMETRICO: cada segmento se indexa por su vector
    (dx, dy) redondeado; cada segmento de la huella que coincide con un segmento del dibujo "vota" por una
    traslacion (punto del dibujo - punto de la huella). Donde se juntan muchos votos hay una instancia.
    Se prueban los giros de 0/90/180/270 grados y el espejo.
  * Cada candidato se VERIFICA sobre una imagen de lineas del dibujo: puntaje directo = fraccion de la
    huella que cae sobre lineas dibujadas; puntaje inverso = fraccion de las lineas del dibujo dentro de la
    caja que la huella explica. Se descarta si no llega al umbral o si el color no es el del modelo.
  * Los bornes se guardan como desplazamientos (dx, dy) respecto del ancla, asi que al encontrar una
    instancia se trasladan (y giran) directamente.

Nada de este archivo tiene coordenadas de un tablero en particular.
"""
import sys, os, math, json, re, hashlib

import numpy as np
import cv2

PROG = r'C:\Buscar Termos en plano\programa'
if PROG not in sys.path:
    sys.path.insert(0, PROG)

CAPAS_COMP = ('COMPONENTES', '00_COMPONENTS')
CAPAS_ETIQ = ('Texto etiquetas',)
CAPAS_ETIQ_MASC = ('_IGV_Componentes Txt',)
OPS_TRAZO = ('S', 's')
OPS_RELLENO = ('f', 'F', 'f*', 'B', 'B*', 'b', 'b*')
ESCALA_RASTER = 8.0            # px por pt de la imagen de lineas usada para verificar
Q_VECTOR = 0.03                # redondeo (pt) del vector de un segmento para el indice del hashing
Q_TRASL = 0.10                 # redondeo (pt) de la traslacion votada
LARGO_MIN = 0.25               # segmentos mas cortos no votan (direccion poco fiable)
N_VOTANTES = 140               # segmentos "raros" de la huella que votan
PASO_MUESTRA = 0.2             # pt entre puntos de muestra de la huella (verificacion)
UMBRAL = 0.92                  # puntaje directo minimo para aceptar una instancia
DIST_COLOR = 0.30              # diferencia maxima de color (0..1 por canal) entre modelo e instancia


def es_blanco(c):
    return c is not None and len(c) == 3 and min(c) > 0.98


def _bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


# ============================================================================================ transformaciones
# Una transformacion es (giro en cuartos de vuelta k, espejo m): primero espejo en x (x -> -x), despues giro
# antihorario de k * 90 grados.
TRANSFORMACIONES = [(k, m) for m in (0, 1) for k in (0, 1, 2, 3)]
PRIOR_TRANSF = {(0, 0): 0.003, (2, 0): 0.001}   # a igualdad de puntaje se prefiere el dibujo sin girar


def transformar(xy, t):
    """Aplica la transformacion t=(k,m) a un array (n,2) de coordenadas relativas al ancla."""
    k, m = t
    a = np.array(xy, dtype=float).reshape(-1, 2).copy()
    if m:
        a[:, 0] = -a[:, 0]
    for _ in range(k % 4):
        a = np.stack([-a[:, 1], a[:, 0]], axis=1)
    return a


def destransformar(xy, t):
    """Inversa de transformar."""
    k, m = t
    a = np.array(xy, dtype=float).reshape(-1, 2).copy()
    for _ in range(k % 4):
        a = np.stack([a[:, 1], -a[:, 0]], axis=1)
    if m:
        a[:, 0] = -a[:, 0]
    return a


def componer(t1, t2):
    """Transformacion equivalente a aplicar t2 y despues t1."""
    for t in TRANSFORMACIONES:
        p = np.array([[1.0, 0.3], [-0.2, 1.0]])
        if np.allclose(transformar(transformar(p, t2), t1), transformar(p, t)):
            return t
    raise ValueError


def arriba_invertido(t):
    """True si la transformacion lleva el 'arriba' local del bloque hacia abajo (o hacia la derecha, que en
    una representacion horizontal es el lado ABAJO segun la regla del taller: izquierda = arriba)."""
    v = transformar([(0.0, 1.0)], t)[0]
    return bool(v[1] < -0.5 or v[0] > 0.5)


def nombre_transf(t):
    k, m = t
    s = '%d grados' % (90 * k)
    return s + (' + espejo' if m else '')


# ============================================================================================ el plano
class Plano:
    """Lee la pagina del topografico y deja listo: segmentos de componentes, mascaras de bloque, etiquetas,
    indice de hashing geometrico e imagen de lineas para verificar."""

    def __init__(self, pdf, pagina_idx, region=None, trazos=None):
        if trazos is None:
            trazos = leer_trazos(pdf, pagina_idx)
        self.pdf, self.pagina_idx = pdf, pagina_idx
        self.trazos = trazos
        self.region = tuple(region) if region else None
        self._segmentos()
        self._mascaras_y_etiquetas()
        self._raster()
        self._indice()
        self._grilla()
        self.cache = {}

    # ------------------------------------------------------------------ segmentos de las capas de componentes
    def _segmentos(self):
        A, B, sid, col = [], [], [], []
        for i, (lay, op, pts, c) in enumerate(self.trazos):
            if lay not in CAPAS_COMP or op not in OPS_TRAZO or es_blanco(c) or len(pts) < 2:
                continue
            for j in range(len(pts) - 1):
                A.append(pts[j]); B.append(pts[j + 1]); sid.append(i); col.append(c if c else (0, 0, 0))
        self.A = np.array(A, float); self.B = np.array(B, float)
        self.sid = np.array(sid, int); self.col = np.array(col, float)
        self.largo = np.hypot(*(self.B - self.A).T)
        if self.region is None:
            allp = np.vstack([self.A, self.B])
            self.region = (float(allp[:, 0].min()) - 5, float(allp[:, 1].min()) - 5,
                           float(allp[:, 0].max()) + 5, float(allp[:, 1].max()) + 5)

    # ------------------------------------------------------------------ mascaras (wipeouts) y cajas de etiqueta
    def _mascaras_y_etiquetas(self):
        et = []
        for i, (lay, op, pts, c) in enumerate(self.trazos):
            if len(pts) < 4:
                continue
            b = _bbox(pts)
            w, h = b[2] - b[0], b[3] - b[1]
            if lay in CAPAS_ETIQ and op in OPS_TRAZO and len(pts) == 5 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.05 \
                    and 2.5 < min(w, h) < 12 and max(w, h) > 1.8 * min(w, h):
                et.append(b)
            elif lay in CAPAS_ETIQ_MASC and op in OPS_RELLENO and es_blanco(c) and 2.5 < min(w, h) < 12:
                et.append(b)
        etiq = []
        for b in et:
            if not any(max(abs(b[j] - e[j]) for j in range(4)) < 0.3 for e in etiq):
                etiq.append(b)
        self.etiquetas = etiq
        self.blancos = []           # indices de todos los rellenos blancos (cortan las corridas de trazos)
        masc = []
        for i, (lay, op, pts, c) in enumerate(self.trazos):
            if op in OPS_RELLENO and es_blanco(c):
                self.blancos.append(i)
                if lay in CAPAS_COMP and len(pts) >= 4:
                    b = _bbox(pts)
                    if any(max(abs(b[j] - e[j]) for j in range(4)) < 0.4 for e in etiq):
                        continue          # es la mascara de una etiqueta, no de un aparato
                    if (b[2] - b[0]) * (b[3] - b[1]) < 2.0:
                        continue
                    masc.append(dict(idx=i, bbox=b, area=(b[2] - b[0]) * (b[3] - b[1])))
        self.mascaras = masc
        self.blancos = np.array(sorted(self.blancos), int)

    # ------------------------------------------------------------------ imagen de lineas (verificacion)
    def _raster(self):
        x0, y0, x1, y1 = self.region
        s = ESCALA_RASTER
        W = int(math.ceil((x1 - x0) * s)) + 4
        H = int(math.ceil((y1 - y0) * s)) + 4
        img = np.zeros((H, W), np.uint8)
        pa = self.a_px(self.A); pb = self.a_px(self.B)
        sh = 4
        ok = (np.abs(pa).max(1) < 60000) & (np.abs(pb).max(1) < 60000)
        lines = np.concatenate([pa[ok], pb[ok]], axis=1) * (1 << sh)
        lines = np.round(lines).astype(np.int32).reshape(-1, 2, 2)
        cv2.polylines(img, list(lines), False, 255, 1, cv2.LINE_8, sh)
        self.img = cv2.dilate(img, np.ones((3, 3), np.uint8))    # tolerancia ~1 px = 0.12 pt
        self.W, self.H = W, H

    def a_px(self, xy):
        x0, y0, x1, y1 = self.region
        xy = np.asarray(xy, float).reshape(-1, 2)
        return np.stack([(xy[:, 0] - x0) * ESCALA_RASTER, (y1 - xy[:, 1]) * ESCALA_RASTER], axis=1)

    def fraccion_sobre_lineas(self, pts):
        """Fraccion de los puntos (n,2) en pt que caen sobre lineas dibujadas."""
        p = np.round(self.a_px(pts)).astype(int)
        ok = (p[:, 0] >= 0) & (p[:, 1] >= 0) & (p[:, 0] < self.W) & (p[:, 1] < self.H)
        if not ok.any():
            return 0.0
        v = np.zeros(len(p), bool)
        v[ok] = self.img[p[ok, 1], p[ok, 0]] > 0
        return float(v.mean())

    def sobre_lineas(self, pts):
        p = np.round(self.a_px(pts)).astype(int)
        ok = (p[:, 0] >= 0) & (p[:, 1] >= 0) & (p[:, 0] < self.W) & (p[:, 1] < self.H)
        v = np.zeros(len(p), bool)
        v[ok] = self.img[p[ok, 1], p[ok, 0]] > 0
        return v

    # ------------------------------------------------------------------ indice del hashing geometrico
    def _indice(self):
        S, K = normalizar(self.A, self.B)
        codes = codificar(K)
        o = np.argsort(codes, kind='stable')
        self.idx_codes = codes[o]
        self.idx_start = S[o]
        self.idx_seg = o

    def frecuencia(self, K):
        c = codificar(K)
        lo = np.searchsorted(self.idx_codes, c, 'left'); hi = np.searchsorted(self.idx_codes, c, 'right')
        return hi - lo

    # ------------------------------------------------------------------ grilla espacial de segmentos
    def _grilla(self, celda=8.0):
        self.celda = celda
        mid = (self.A + self.B) / 2
        gx = np.floor(mid[:, 0] / celda).astype(np.int64); gy = np.floor(mid[:, 1] / celda).astype(np.int64)
        code = gx * 100000 + gy
        o = np.argsort(code, kind='stable')
        self.g_code = code[o]; self.g_seg = o

    def segmentos_en(self, b):
        """Indices de los segmentos con los dos extremos dentro de la caja b=(x0,y0,x1,y1)."""
        c = self.celda
        ix0, ix1 = int(math.floor(b[0] / c)), int(math.floor(b[2] / c))
        iy0, iy1 = int(math.floor(b[1] / c)), int(math.floor(b[3] / c))
        out = []
        for gx in range(ix0, ix1 + 1):
            lo = np.searchsorted(self.g_code, gx * 100000 + iy0, 'left')
            hi = np.searchsorted(self.g_code, gx * 100000 + iy1, 'right')
            out.append(self.g_seg[lo:hi])
        if not out:
            return np.zeros(0, int)
        s = np.concatenate(out)
        A, B = self.A[s], self.B[s]
        ok = ((np.minimum(A[:, 0], B[:, 0]) >= b[0]) & (np.maximum(A[:, 0], B[:, 0]) <= b[2]) &
              (np.minimum(A[:, 1], B[:, 1]) >= b[1]) & (np.maximum(A[:, 1], B[:, 1]) <= b[3]))
        return s[ok]

    def color_en(self, b):
        """Color dominante (ponderado por largo) de los trazos dentro de la caja b."""
        s = self.segmentos_en(b)
        if not len(s):
            return None
        cols = np.round(self.col[s] * 10) / 10
        keys = [tuple(c) for c in cols]
        tot = {}
        for k, L, c in zip(keys, self.largo[s], self.col[s]):
            if k not in tot:
                tot[k] = [0.0, c]
            tot[k][0] += L
        best = max(tot.values(), key=lambda v: v[0])
        return [round(float(v), 3) for v in best[1]]

    # ------------------------------------------------------------------ bloque de una instancia (para aprender)
    def mascara_de(self, x, y, margen=0.3):
        """La mascara blanca mas chica que contiene el punto (x, y), o None."""
        cands = [m for m in self.mascaras
                 if m['bbox'][0] - margen <= x <= m['bbox'][2] + margen and m['bbox'][1] - margen <= y <= m['bbox'][3] + margen]
        if not cands:
            return None
        return min(cands, key=lambda m: (m['area'], math.hypot(x - (m['bbox'][0] + m['bbox'][2]) / 2, y - (m['bbox'][1] + m['bbox'][3]) / 2)))

    def bloque_de_mascara(self, m):
        """(caja, A, B) de la instancia que empieza en la mascara m: los trazos que siguen a la mascara en el
        PDF hasta el proximo relleno blanco, dentro de la caja de la mascara (+3 pt)."""
        i0 = m['idx']
        nx = self.blancos[self.blancos > i0]
        i1 = int(nx[0]) if len(nx) else len(self.trazos)
        b = m['bbox']
        sel = (self.sid > i0) & (self.sid < i1)
        A, B = self.A[sel], self.B[sel]
        dentro = ((np.minimum(A[:, 0], B[:, 0]) >= b[0] - 3) & (np.maximum(A[:, 0], B[:, 0]) <= b[2] + 3) &
                  (np.minimum(A[:, 1], B[:, 1]) >= b[1] - 3) & (np.maximum(A[:, 1], B[:, 1]) <= b[3] + 3))
        return b, A[dentro], B[dentro]

    def corrida(self, pts, radio=4.0):
        """Bloque sin mascara: la corrida de trazos contiguos (en el orden del PDF) alrededor de los puntos."""
        P = np.array(pts, float)
        mid = (self.A + self.B) / 2
        d = np.min(np.hypot(mid[:, None, 0] - P[None, :, 0], mid[:, None, 1] - P[None, :, 1]), axis=1)
        cerca = np.unique(self.sid[d <= radio])
        if not len(cerca):
            return None
        lo, hi = int(cerca.min()), int(cerca.max())
        es_comp = lambda i: (self.trazos[i][0] in CAPAS_COMP and not (self.trazos[i][1] in OPS_RELLENO and es_blanco(self.trazos[i][3])))
        core = np.isin(self.sid, np.arange(lo, hi + 1))
        cb = (min(self.A[core, 0].min(), self.B[core, 0].min()) - 10, min(self.A[core, 1].min(), self.B[core, 1].min()) - 10,
              max(self.A[core, 0].max(), self.B[core, 0].max()) + 10, max(self.A[core, 1].max(), self.B[core, 1].max()) + 10)
        inside = lambda i: all(cb[0] <= x <= cb[2] and cb[1] <= y <= cb[3] for x, y in self.trazos[i][2])
        while lo - 1 >= 0 and es_comp(lo - 1) and inside(lo - 1):
            lo -= 1
        while hi + 1 < len(self.trazos) and es_comp(hi + 1) and inside(hi + 1):
            hi += 1
        sel = (self.sid >= lo) & (self.sid <= hi)
        A, B = self.A[sel], self.B[sel]
        b = (float(min(A[:, 0].min(), B[:, 0].min())), float(min(A[:, 1].min(), B[:, 1].min())),
             float(max(A[:, 0].max(), B[:, 0].max())), float(max(A[:, 1].max(), B[:, 1].max())))
        return b, A, B

    # ------------------------------------------------------------------ etiquetas
    def caja_etiqueta(self, x, y):
        best, bd = None, 1e9
        for b in self.etiquetas:
            dx = max(b[0] - x, 0, x - b[2]); dy = max(b[1] - y, 0, y - b[3])
            d = math.hypot(dx, dy) + 0.01 * math.hypot(x - (b[0] + b[2]) / 2, y - (b[1] + b[3]) / 2)
            if d < bd:
                best, bd = b, d
        if best is not None and bd < 4:
            return best
        return (x - 2.7, y - 8.9, x + 2.7, y + 8.9)


def leer_trazos(pdf, pagina_idx):
    import pypdf
    from pdfvec import page_strokes, layer_names
    r = pypdf.PdfReader(pdf)
    return page_strokes(r, pagina_idx, layer_names(r), with_color=True)


# ============================================================================================ la huella
def hacer_huella(A, B, ancla, color=None):
    """Huella de un bloque: segmentos relativos al ancla (centro de la caja), caja, muestras, firma, hash."""
    A = np.asarray(A, float) - ancla; B = np.asarray(B, float) - ancla
    allp = np.vstack([A, B])
    caja = (float(allp[:, 0].max() - allp[:, 0].min()), float(allp[:, 1].max() - allp[:, 1].min()))
    return dict(A=A, B=B, caja=caja, muestras=muestras_de(A, B), color=color,
                firma=firma(A, B), hash=hash_huella(A, B), nseg=int(len(A)))


def huella_a_json(h):
    return dict(nseg=h['nseg'], caja=[round(v, 3) for v in h['caja']], color=h['color'], hash=h['hash'],
                firma=h['firma'],
                segmentos=[[round(float(a[0]), 3), round(float(a[1]), 3), round(float(b[0]), 3), round(float(b[1]), 3)]
                           for a, b in zip(h['A'], h['B'])])


def huella_de_json(d):
    S = np.array(d['segmentos'], float).reshape(-1, 4)
    A, B = S[:, :2], S[:, 2:]
    return dict(A=A, B=B, caja=tuple(d['caja']), muestras=muestras_de(A, B), color=d.get('color'),
                firma=d.get('firma'), hash=d.get('hash'), nseg=len(A))


def caja_instancia(h, t, cx, cy):
    """Caja (x0,y0,x1,y1) de la huella h puesta con la transformacion t en (cx, cy)."""
    P = transformar(np.vstack([h['A'], h['B']]), t)
    return (float(P[:, 0].min() + cx), float(P[:, 1].min() + cy), float(P[:, 0].max() + cx), float(P[:, 1].max() + cy))


# ============================================================================================ hashing geometrico
def normalizar(A, B):
    """Orienta cada segmento (dx>0, o vertical hacia arriba) y devuelve (inicio, clave entera del vector)."""
    A = np.asarray(A, float).reshape(-1, 2); B = np.asarray(B, float).reshape(-1, 2)
    v = B - A
    flip = (v[:, 0] < -0.005) | ((np.abs(v[:, 0]) <= 0.005) & (v[:, 1] < 0))
    S = np.where(flip[:, None], B, A)
    v = np.where(flip[:, None], -v, v)
    K = np.round(v / Q_VECTOR).astype(np.int64)
    return S, K


def codificar(K):
    return (K[:, 0] + 20000) * 40000 + (K[:, 1] + 20000)


def buscar(plano, huella, transformaciones=TRANSFORMACIONES, umbral=UMBRAL, zona=None):
    """Busca las instancias de una huella en el plano. Devuelve [(puntaje, t, (cx, cy))] sin repetidos.
    zona = (x0, y0, x1, y1) limita la posicion del ancla. Los resultados se guardan en plano.cache."""
    clave = (huella.get('hash') or hash_huella(huella['A'], huella['B']), tuple(transformaciones), round(umbral, 3),
             tuple(round(v, 1) for v in zona) if zona else None)
    if clave in plano.cache:
        return plano.cache[clave]
    A0, B0 = np.asarray(huella['A'], float), np.asarray(huella['B'], float)
    largo = np.hypot(*(B0 - A0).T)
    usar = largo >= LARGO_MIN
    if usar.sum() < 3:
        usar = largo > 0.02
    A0, B0 = A0[usar], B0[usar]
    M0 = np.asarray(huella['muestras'], float)
    res = []
    for t in transformaciones:
        A, B = transformar(A0, t), transformar(B0, t)
        S, K = normalizar(A, B)
        f = plano.frecuencia(K)
        orden = np.argsort(np.where(f > 0, f, 10 ** 9), kind='stable')
        orden = orden[f[orden] > 0][:N_VOTANTES]
        if len(orden) < 3:
            continue
        votos_t, votos_j = [], []
        for dkx in (-1, 0, 1):                      # vecinos del vector (tolerancia al redondeo)
            for dky in (-1, 0, 1):
                KK = K[orden] + np.array([dkx, dky])
                c = codificar(KK)
                lo = np.searchsorted(plano.idx_codes, c, 'left'); hi = np.searchsorted(plano.idx_codes, c, 'right')
                n = hi - lo
                if n.sum() == 0:
                    continue
                rep = np.repeat(np.arange(len(orden)), n)
                pos = np.concatenate([np.arange(a, b) for a, b in zip(lo, hi) if b > a])
                tt = plano.idx_start[pos] - S[orden][rep]
                votos_t.append(tt); votos_j.append(rep)
        if not votos_t:
            continue
        T = np.concatenate(votos_t); J = np.concatenate(votos_j)
        if zona is not None:
            ok = (T[:, 0] >= zona[0]) & (T[:, 0] <= zona[2]) & (T[:, 1] >= zona[1]) & (T[:, 1] <= zona[3])
            T, J = T[ok], J[ok]
            if not len(T):
                continue
        qb = np.round(T / Q_TRASL).astype(np.int64)
        code = (qb[:, 0] + 200000) * 400000 + (qb[:, 1] + 200000)
        uj = np.unique(np.stack([code, J], 1), axis=0)          # un voto por segmento y por celda
        cc, cnt = np.unique(uj[:, 0], return_counts=True)
        cmap = dict(zip(cc.tolist(), cnt.tolist()))
        nvot = len(orden)
        cand = []
        for c0, n0 in zip(cc.tolist(), cnt.tolist()):
            if n0 < 0.25 * nvot:
                continue
            qx, qy = c0 // 400000 - 200000, c0 % 400000 - 200000
            tot = sum(cmap.get((qx + a + 200000) * 400000 + (qy + b + 200000), 0) for a in (-1, 0, 1) for b in (-1, 0, 1))
            if tot >= 0.45 * nvot:
                cand.append((tot, qx * Q_TRASL, qy * Q_TRASL))
        cand.sort(reverse=True)
        Mt = transformar(M0, t)
        vistos = []
        for tot, tx, ty in cand:
            if any(abs(tx - a) < 0.6 and abs(ty - b) < 0.6 for a, b in vistos):
                continue
            vistos.append((tx, ty))
            cerca = (np.abs(T[:, 0] - tx) <= 1.5 * Q_TRASL) & (np.abs(T[:, 1] - ty) <= 1.5 * Q_TRASL)
            if cerca.sum() == 0:
                continue
            txy = np.median(T[cerca], axis=0)
            punt = plano.fraccion_sobre_lineas(Mt + txy)
            if punt >= umbral:
                res.append((punt, t, (float(txy[0]), float(txy[1]))))
    # suprimir repetidos (misma posicion, otra transformacion): gana el mejor puntaje con el prior
    res.sort(key=lambda r: -(r[0] + PRIOR_TRANSF.get(r[1], 0.0)))
    out = []
    for r in res:
        b1 = caja_instancia(huella, r[1], *r[2])
        if any(iou(b1, caja_instancia(huella, o[1], *o[2])) > 0.3 for o in out):
            continue
        out.append(r)
    plano.cache[clave] = out
    return out


def iou(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0]); iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def contencion(a, b):
    """Fraccion de la caja mas chica que queda dentro de la otra."""
    ix = min(a[2], b[2]) - max(a[0], b[0]); iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    return ix * iy / max(1e-9, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


def puntaje_inverso(plano, huella, t, cx, cy, margen=0.4):
    """Fraccion (por largo) de las lineas del dibujo dentro de la caja de la instancia que la huella explica."""
    b = caja_instancia(huella, t, cx, cy)
    bi = (b[0] + margen, b[1] + margen, b[2] - margen, b[3] - margen)
    if bi[2] <= bi[0] or bi[3] <= bi[1]:
        return 1.0
    s = plano.segmentos_en(bi)
    if not len(s):
        return 1.0
    esc = ESCALA_RASTER
    W = int((b[2] - b[0]) * esc) + 6; H = int((b[3] - b[1]) * esc) + 6
    img = np.zeros((H, W), np.uint8)
    f = lambda xy: np.stack([(xy[:, 0] - b[0]) * esc + 3, (b[3] - xy[:, 1]) * esc + 3], 1)
    A = transformar(huella['A'], t) + (cx, cy); B = transformar(huella['B'], t) + (cx, cy)
    L = np.round(np.concatenate([f(A), f(B)], 1) * 16).astype(np.int32).reshape(-1, 2, 2)
    cv2.polylines(img, list(L), False, 255, 1, cv2.LINE_8, 4)
    img = cv2.dilate(img, np.ones((3, 3), np.uint8))
    tot = ok = 0.0
    for a, bb in zip(plano.A[s], plano.B[s]):
        Lg = math.hypot(bb[0] - a[0], bb[1] - a[1])
        n = max(1, int(Lg / PASO_MUESTRA))
        P = np.array([a + (bb - a) * (i / n) for i in range(n + 1)])
        q = np.round(f(P)).astype(int)
        q[:, 0] = np.clip(q[:, 0], 0, W - 1); q[:, 1] = np.clip(q[:, 1], 0, H - 1)
        ok += Lg * float((img[q[:, 1], q[:, 0]] > 0).mean()); tot += Lg
    return ok / tot if tot > 0 else 1.0


def muestras_de(A, B, paso=PASO_MUESTRA):
    A = np.asarray(A, float).reshape(-1, 2); B = np.asarray(B, float).reshape(-1, 2)
    if not len(A):
        return np.zeros((0, 2))
    L = np.hypot(*(B - A).T)
    n = np.maximum(1, (L / paso).astype(int))
    idx = np.repeat(np.arange(len(A)), n + 1)
    fr = np.concatenate([np.arange(k + 1) / k for k in n])
    return A[idx] + (B - A)[idx] * fr[:, None]


def firma(A, B):
    """Histograma normalizado de largos (escala log) x angulos (8 sectores) de los segmentos: sirve para
    comparar bloques de un vistazo (distancia L1) sin buscarlos."""
    v = np.asarray(B, float) - np.asarray(A, float)
    L = np.hypot(v[:, 0], v[:, 1])
    ang = np.degrees(np.arctan2(v[:, 1], v[:, 0])) % 180
    lb = np.clip(np.floor(np.log2(np.maximum(L, 1e-3) / 0.125)), 0, 7).astype(int)
    ab = np.clip(np.floor((ang + 11.25) % 180 / 22.5), 0, 7).astype(int)
    H = np.zeros((8, 8))
    np.add.at(H, (lb, ab), L)
    s = H.sum()
    return (H / s if s > 0 else H).round(4).tolist()


def hash_huella(A, B):
    S, K = normalizar(A, B)
    q = np.round(np.concatenate([S, S + K * Q_VECTOR], 1) / 0.02).astype(np.int64)
    q = q[np.lexsort(q.T[::-1])]
    return hashlib.sha1(q.tobytes()).hexdigest()[:16]


def dist_color(a, b):
    if a is None or b is None:
        return 0.0
    return max(abs(float(x) - float(y)) for x, y in zip(a, b))


# ============================================================================================ radio del borne
def radio_de_borne(A, B, caja, pos, vecinos, rmax=2.5, rmin=0.8):
    """Radio del dibujo del borne alrededor de pos (coordenadas relativas al ancla): se rellena la zona libre
    que rodea al punto (entre las lineas del bloque) y se mide hasta donde llega. Nunca mas de 0.48 x la
    distancia al borne vecino, para que la marca no tape al de al lado."""
    s = 12.0
    A = np.asarray(A, float); B = np.asarray(B, float)
    P = np.vstack([A, B])
    x0, y0 = P[:, 0].min() - 3, P[:, 1].min() - 3
    x1, y1 = P[:, 0].max() + 3, P[:, 1].max() + 3
    W, H = int((x1 - x0) * s) + 2, int((y1 - y0) * s) + 2
    f = lambda xy: np.stack([(xy[:, 0] - x0) * s, (y1 - xy[:, 1]) * s], 1)
    L = np.round(np.concatenate([f(A), f(B)], 1) * 16).astype(np.int32).reshape(-1, 2, 2)
    base = np.zeros((H, W), np.uint8)
    cv2.polylines(base, list(L), False, 255, 1, cv2.LINE_8, 4)
    p = f(np.array([pos], float))[0]
    regiones = np.zeros((H, W), bool)
    for dx, dy in ((0.3, 0.3), (-0.3, 0.3), (0.3, -0.3), (-0.3, -0.3), (0, 0)):
        sx, sy = int(round(p[0] + dx * s)), int(round(p[1] - dy * s))
        if not (0 <= sx < W and 0 <= sy < H) or base[sy, sx] or regiones[sy, sx]:
            continue
        work = base.copy()
        mask = np.zeros((H + 2, W + 2), np.uint8)
        _, _, _, rect = cv2.floodFill(work, mask, (sx, sy), 128, flags=4)
        reg = work == 128
        x, y, ww, hh = rect
        if x <= 0 or y <= 0 or x + ww >= W - 1 or y + hh >= H - 1 or reg.sum() > (4.0 * s) ** 2 * 3.2:
            continue                       # la zona se escapa: no es la abertura del borne
        regiones |= reg
    r = rmax
    if regiones.any():
        ys, xs = np.nonzero(regiones)
        d = np.hypot(xs - p[0], ys - p[1]) / s
        r = min(float(np.percentile(d, 98)) + 0.05, rmax)
    if vecinos:
        dn = min(math.hypot(pos[0] - v[0], pos[1] - v[1]) for v in vecinos)
        if dn > 0.2:
            r = min(r, 0.48 * dn)
    return round(max(rmin, r), 2)


# ============================================================================================ zonas de tags
def zonas_de(plano, comps):
    """Zona de cada componente: su etiqueta y la x donde empieza la etiqueta siguiente del mismo riel."""
    z = {}
    for c, v in comps.items():
        e = v.get('etiqueta_topografico') or {}
        if 'x' not in e:
            continue
        z[c] = dict(tx=float(e['x']), ty=float(e['y']), riel=e.get('riel'), caja=plano.caja_etiqueta(float(e['x']), float(e['y'])))
    for c, a in z.items():
        sig = [b for d, b in z.items() if d != c and b['riel'] == a['riel'] and b['tx'] > a['tx'] + 1.0]
        a['x_fin'] = min([b['caja'][0] for b in sig], default=float('inf'))
        a['siguiente'] = min([(b['tx'], d) for d, b in z.items() if d != c and b['riel'] == a['riel'] and b['tx'] > a['tx'] + 1.0],
                             default=(None, None))[1]
    return z


def contiene(caja, x, y, margen=0.0):
    return caja[0] - margen <= x <= caja[2] + margen and caja[1] - margen <= y <= caja[3] + margen


def en_zona(caja, z):
    """La instancia (caja) es de la zona del tag: contiene la etiqueta, o esta a su derecha, antes de la
    etiqueta siguiente del mismo riel, y cruza la altura de la etiqueta."""
    if contiene(caja, z['tx'], z['ty']):
        return True
    cx = (caja[0] + caja[2]) / 2
    return z['tx'] < cx < z['x_fin'] and caja[1] - 2 <= z['ty'] <= caja[3] + 2


# ============================================================================================ lectura del instructivo
LADOS = ('ARRIBA', 'ABAJO')
ESQUEMAS_FISICOS = ('cuatro_puntos', 'doble_piso', 'fusible_doble_piso')   # claves por posicion fisica
CLAVES_4 = ('ARRIBA_ext', 'ARRIBA_int', 'ABAJO_int', 'ABAJO_ext')


def lado_de(u):
    t = (u.get('texto') or '').upper()
    for l in LADOS:
        if re.search(r'\b%s\b' % l, t):
            return l
    return (u.get('parte') or u.get('lado') or '').upper() or None


def norm_borne(b):
    return re.sub(r'\s+', '', (b or '').upper())


def invertir_clave(k):
    """ARRIBA_x <-> ABAJO_x (para bloques girados 180 grados o simetrias arriba/abajo)."""
    if k.startswith('ARRIBA'):
        return 'ABAJO' + k[6:]
    if k.startswith('ABAJO'):
        return 'ARRIBA' + k[5:]
    return k


def interpretar(modelo, u, comp):
    """Traduce un uso del instructivo a (unidad, clave) segun el esquema del modelo.
    unidad = numero de pieza / modulo (1 para aparatos; None si el texto no lo dice);
    clave = nombre generico del borne en el bloque (o lista de pines posibles).
    Devuelve None si el texto no encaja en el esquema del modelo."""
    esq = modelo['esquema']
    borne = (u.get('borne') or '').strip()
    lado = lado_de(u)
    if esq == 'cuatro_puntos':
        p = u.get('punto')
        if p is None:
            m = re.match(r'^\s*(\d+)\s*[.](\d)\s*$', (u.get('texto') or '')[len(comp):])
            if m:
                borne, p = m.group(1), int(m.group(2))
        if p is None or not str(borne).isdigit() or int(p) not in (1, 2, 3, 4):
            return None
        return int(borne), CLAVES_4[int(p) - 1]
    if esq == 'doble_piso':
        if not borne.isdigit() or lado not in LADOS or u.get('punto') is not None:
            return None
        n = int(borne)
        return (n + 1) // 2, '%s_%s' % (lado, 'ext' if n % 2 else 'int')
    if esq == 'fusible_doble_piso':
        m = re.match(r'^(F?)(\d+)$', norm_borne(borne))
        if not m or lado not in LADOS:
            return None
        return int(m.group(2)), '%s_%s' % (lado, 'int' if m.group(1) else 'ext')
    if esq == 'pieza_lado':
        if not borne.isdigit() or lado not in LADOS:
            return None
        return int(borne), lado
    if esq == 'modulos':
        b = norm_borne(borne)
        if b not in [norm_borne(x) for x in modelo['contactos']]:
            return None
        suf = (u.get('tag') or '')[len(comp):]
        k = int(suf) if suf.isdigit() else None
        return k, b
    if esq == 'aparato':
        clave = modelo['clave']
        if clave == 'lado':
            if norm_borne(borne) not in ('',) or lado not in LADOS:
                return None
            return 1, lado
        if clave == 'polos':
            b = norm_borne(borne)
            pol = [norm_borne(x) for x in modelo['polos']]
            if b not in pol or lado not in LADOS:
                return None
            return 1, 'polo%d_%s' % (pol.index(b) + 1, lado)
        if clave == 'borne':
            b = norm_borne(borne)
            alias = {norm_borne(k): norm_borne(v) for k, v in modelo.get('alias', {}).items()}
            b = alias.get(b, b)
            if b not in [norm_borne(x) for x in modelo['bornes']]:
                return None
            return 1, b
        if clave == 'pin':
            c = pines_candidatos(modelo, borne)
            if not c:
                return None
            return 1, c          # lista de pines posibles; se elige despues (repetidos por numero de cable)
    return None


def pines_candidatos(modelo, borne):
    """Pines de la tabla del modelo compatibles con el rotulo del funcional: '1 (-)', 'L-3', 'N-2', '+Vo',
    '-Vin', '3'. Si trae numero se usa el numero (y el nombre, si lo trae, tiene que coincidir)."""
    t = norm_borne(borne)
    num, nombre = None, None
    m = re.match(r'^(\d+)\((.+)\)$', t) or re.match(r'^(\d+)([^\d].*)$', t)
    if m:
        num, nombre = int(m.group(1)), m.group(2)
    else:
        m = re.match(r'^(.+?)-(\d+)$', t) or re.match(r'^([^\d]+?)(\d+)$', t)
        if m and not re.match(r'^[+-]?V', t):
            nombre, num = m.group(1), int(m.group(2))
        elif t.isdigit():
            num = int(t)
        else:
            nombre = t
    out = []
    for pid, info in modelo['pines'].items():
        nombres = [norm_borne(n) for n in info['nombres']]
        if num is not None and info['num'] != num:
            continue
        if nombre and nombre not in nombres:
            continue
        out.append(pid)
    return out


# ============================================================================================ lista de materiales
RE_TAG = re.compile(r'^\d{2}[A-Z]{1,6}\d{0,3}$')


def leer_lista_materiales(path):
    """Lista de materiales del funcional (texto 'TAG | descripcion | fabricante | modelo', una linea por
    renglon; los renglones sin tag siguen al anterior). Devuelve {tag: texto}. 'TAG | /2' = TAG y TAG con el
    ultimo numero cambiado por 2."""
    out, ultimo = {}, None
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding='utf-8', errors='replace') as f:
        for linea in f:
            partes = [p.strip() for p in linea.strip().split('|')]
            tags = [p for p in partes if RE_TAG.match(p)]
            if tags:
                ultimo = []
                for tg in tags:
                    ultimo.append(tg)
                    i = partes.index(tg)
                    if i + 1 < len(partes) and re.match(r'^/\d+$', partes[i + 1]):
                        ultimo.append(re.sub(r'\d+$', partes[i + 1][1:], tg))
                for tg in ultimo:
                    out[tg] = out.get(tg, '') + ' ' + linea.strip()
            elif ultimo:
                for tg in ultimo:
                    out[tg] = out.get(tg, '') + ' ' + linea.strip()
    return out


def modelos_de_lista(texto, modelos):
    """Modelos del catalogo cuyos patrones aparecen en el texto de la lista de materiales."""
    if not texto:
        return []
    T = texto.upper()
    return [mid for mid, m in modelos.items() if any(re.search(p, T) for p in m.get('patrones', []))]


def cargar_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def guardar_json(p, d, indent=1):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=indent)
