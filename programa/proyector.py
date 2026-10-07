"""Proyeccion del instructivo sobre la bandeja REAL (pestaña 📽 Proyector de la web, web/proyector.js).

La pestaña proyecta solo las canaletas y el recorrido del cable que se esta cableando (no la imagen del topografico).
Para que caiga sobre la bandeja de verdad se calibra con los cuatro ORIFICIOS de montaje de la placa, uno en cada
esquina: el usuario arrastra una mira sobre cada orificio real y la pestaña deforma la capa (homografia). Aca se buscan
esos orificios en el dibujo de la bandeja (hoja del topografico de AutoCAD o de bandejas de EPLAN): cerca de cada
esquina de la placa hay un simbolo chico (circulo con cruz de centro en AutoCAD; tuerca hexagonal con el agujero en
EPLAN) y se calcula su centro. Si no estan dibujados se usan las esquinas de la placa y se avisa.
Todo es general: no hay coordenadas ni tags de ningun plano."""
import math, random, collections

ORIF_MIN_MM, ORIF_MAX_MM = 3.0, 40.0     # tamano del simbolo del orificio (circulo o tuerca) en mm de bandeja
VENTANA_MM = 60.0                        # se busca hasta 60 mm (o el 12 % del lado menor de la placa) de cada esquina
SEG_MAX_MM = 14.0                        # segmentos que arman el simbolo (los lados de la tuerca miden 12,7 mm)
NOMBRES = ['arriba a la izquierda', 'arriba a la derecha', 'abajo a la derecha', 'abajo a la izquierda']


def segmentos_hoja(pdf_path, pag):
    """segmentos [(a, b)] de los trazos de la hoja (pypdf; si el PDF esta protegido, la copia de proceso de EPLAN)"""
    import pypdf
    from pdfvec import page_strokes
    import eplan
    r = pypdf.PdfReader(eplan.copia_proceso(pdf_path))
    return [(p[i], p[i + 1]) for _, _, p in page_strokes(r, pag - 1, {}) for i in range(len(p) - 1)]


def centro_por_mediatrices(segs, max_pares=6000):
    """centro de un simbolo redondo dibujado con segmentos (circulos concentricos, hexagono, cruz): la mediatriz de
    cualquier cuerda de un circulo pasa por su centro, asi que el centro es la mediana de las intersecciones de pares
    de mediatrices. Robusto a un simbolo recortado (en EPLAN la canaleta tapa parte de la tuerca), a varios circulos
    concentricos y a algun segmento suelto. None si no alcanza."""
    L = []
    for a, b in segs:
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy)
        if d < 0.3:
            continue
        L.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, -dy / d, dx / d))
    n = len(L)
    if n < 2:
        return None
    if n * (n - 1) // 2 <= max_pares:
        pares = [(i, j) for i in range(n) for j in range(i + 1, n)]
    else:
        rnd = random.Random(1)
        pares = [(rnd.randrange(n), rnd.randrange(n)) for _ in range(max_pares)]
    xs, ys = [], []
    for i, j in pares:
        if i == j:
            continue
        mx, my, ux, uy = L[i]
        qx, qy, vx, vy = L[j]
        den = ux * vy - uy * vx
        if abs(den) < 0.3:               # mediatrices casi paralelas: la interseccion es inestable
            continue
        t = ((qx - mx) * vy - (qy - my) * vx) / den
        xs.append(mx + t * ux)
        ys.append(my + t * uy)
    if len(xs) < 4:
        return None
    xs.sort(); ys.sort()
    return xs[len(xs) // 2], ys[len(ys) // 2]


def _agrupar(segs, gap):
    """grupos de segmentos que se tocan (puntas a menos de ~gap)"""
    pts = [q for s in segs for q in s]
    celdas = collections.defaultdict(list)
    for i, p in enumerate(pts):
        celdas[(int(p[0] // gap), int(p[1] // gap))].append(i)
    par = list(range(len(pts)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for (gx, gy), ids in celdas.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in celdas.get((gx + dx, gy + dy), []):
                    par[f(ids[0])] = f(j)
    for i in range(0, len(pts), 2):
        par[f(i)] = f(i + 1)
    grupos = collections.defaultdict(list)
    for i in range(0, len(pts), 2):
        grupos[f(i)].append(segs[i // 2])
    return list(grupos.values())


def _caja(segs):
    xs = [q[0] for s in segs for q in s]
    ys = [q[1] for s in segs for q in s]
    return min(xs), min(ys), max(xs), max(ys)


def _esquinas(region):
    x0, y0, x1, y1 = region
    return [(x0, y1), (x1, y1), (x1, y0), (x0, y0)]       # arriba-izq, arriba-der, abajo-der, abajo-izq (y hacia arriba)


def orificio_cerca(segs, esquina, region, escala, win, corto):
    """centro del simbolo de orificio mas cercano a la esquina (dentro de la placa), o None"""
    x0, y0, x1, y1 = region
    cx, cy = esquina
    m = 2.0
    cerca = [(a, b) for a, b in segs if math.dist(a, b) <= corto
             and all(abs(q[0] - cx) <= win and abs(q[1] - cy) <= win and x0 - m <= q[0] <= x1 + m and y0 - m <= q[1] <= y1 + m
                     for q in (a, b))]
    mejor = None
    for grupo in _agrupar(cerca, 2.0):
        bx0, by0, bx1, by1 = _caja(grupo)
        w, h = bx1 - bx0, by1 - by0
        if min(w, h) < ORIF_MIN_MM / escala or max(w, h) > ORIF_MAX_MM / escala or min(w, h) / max(w, h) < 0.5:
            continue
        d = math.hypot((bx0 + bx1) / 2 - cx, (by0 + by1) / 2 - cy)
        if mejor is None or d < mejor[0]:
            mejor = (d, (bx0, by0, bx1, by1))
    if not mejor:
        return None
    bx0, by0, bx1, by1 = mejor[1]
    # el simbolo entero: tambien lo que cae dentro de su caja (los circulos de adentro de la tuerca, la cruz)
    todo = [s for s in cerca if all(bx0 - 1 <= q[0] <= bx1 + 1 and by0 - 1 <= q[1] <= by1 + 1 for q in s)]
    c = centro_por_mediatrices(todo)
    if not c or not (bx0 - 2 <= c[0] <= bx1 + 2 and by0 - 2 <= c[1] <= by1 + 2):   # sin sentido: el centro de la caja
        c = ((bx0 + bx1) / 2, (by0 + by1) / 2)
    return c


def orificios(pdf_path, pag, region, escala, segs=None):
    """los cuatro orificios de montaje de la placa de la bandeja, en pt de la hoja:
    dict(puntos=[[x, y] x 4] (arriba-izq, arriba-der, abajo-der, abajo-izq), fuente='dibujo' | 'esquinas', avisos=[...]).
    Sin placa, sin dibujo legible o con menos de 3 simbolos en las esquinas, los puntos son las esquinas de la placa
    (fuente 'esquinas') y se avisa. Con 3 de 4, el que falta se completa por simetria (los orificios forman un rectangulo)."""
    if not region or not pag:
        return dict(puntos=[], fuente='esquinas', avisos=['el topográfico no tiene la placa de la bandeja: no hay nada que proyectar'])
    esquinas = [[round(x, 2), round(y, 2)] for x, y in _esquinas(region)]
    esc = escala or 1.0
    try:
        if segs is None:
            segs = segmentos_hoja(pdf_path, pag)
    except Exception as e:
        return dict(puntos=esquinas, fuente='esquinas', avisos=[f'no se pudo leer el dibujo de la bandeja ({e}): la calibración usa las esquinas de la placa'])
    x0, y0, x1, y1 = region
    win = max(0.12 * min(x1 - x0, y1 - y0), VENTANA_MM / esc)
    hallados = [orificio_cerca(segs, e, region, esc, win, SEG_MAX_MM / esc) for e in _esquinas(region)]
    n = sum(1 for h in hallados if h)
    avisos = []
    if n < 3:
        avisos.append('no se encontraron los orificios de montaje en el dibujo de la bandeja'
                      + (f' ({n} de 4)' if n else '') + ': la calibración usa las esquinas de la placa. '
                      'Si la bandeja tiene orificios, marcalos en el visor ▶ Cablear de a uno con 🎯')
        return dict(puntos=esquinas, fuente='esquinas', avisos=avisos)
    columnas, filas = ((0, 3), (1, 2)), ((0, 1), (3, 2))         # misma x los de cada columna, misma y los de cada fila
    pts = []
    for i, c in enumerate(hallados):
        if c is None:
            col = next(cc for cc in columnas if i in cc)
            fil = next(ff for ff in filas if i in ff)
            otro_col = hallados[[j for j in col if j != i][0]]
            otro_fil = hallados[[j for j in fil if j != i][0]]
            c = (otro_col[0], otro_fil[1])
            avisos.append(f'orificio {NOMBRES[i]}: no se encontró en el dibujo, se completó por simetría con los otros tres')
        pts.append([round(c[0], 2), round(c[1], 2)])
    tol = 3.0 / esc
    if any(abs(pts[i][0] - pts[j][0]) > tol for i, j in columnas) or any(abs(pts[i][1] - pts[j][1]) > tol for i, j in filas):
        avisos.append('los orificios encontrados no forman un rectángulo: revisá las miras en el dibujo (🎯 en el visor ▶ Cablear de a uno)')
    return dict(puntos=pts, fuente='dibujo', avisos=avisos)
