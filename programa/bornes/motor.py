# -*- coding: utf-8 -*-
"""Mapeo de bornes del topografico con un CATALOGO DE MODELOS + un DETECTOR GEOMETRICO GENERICO.

El programa lo usa desde bornes/__init__.py (mapear_trabajo). Para probarlo a mano:
    python motor.py <topografico.pdf> <usos_por_componente.json> <salida.json>
                    [--materiales lista_materiales.txt | --materiales no] [--catalogo catalogo.json]
                    [--control control.png | --control no] [--pagina N] [--escala mm_por_pt | --escala auto]
  --pagina y --escala mandan sobre 'pagina_pdf' y 'escala_mm_por_pt' de los usos; 'auto' saca la escala del alto del
  riel DIN (35 mm). Sin lista de materiales el modelo de cada tag sale de la geometria.

Idea (ver LEEME.md):
  1. Se leen los trazos vectoriales de la pagina (programa/pdfvec.py), las etiquetas amarillas (render de la
     pagina) y los rieles DIN (capa 'RIEL DIN').
  2. Cada componente de usos_por_componente.json se asocia a su etiqueta amarilla y a su riel. Su ZONA es lo que
     esta a la DERECHA de su etiqueta hasta la etiqueta siguiente del mismo riel (regla 1 del taller), con la
     altura del modelo.
  3. El modelo sale de la lista de materiales (alias del catalogo). Si no figura o su firma no aparece en la
     zona, se prueban todos los modelos del catalogo y se queda el que mejor explica los usos.
  4. En la zona se buscan las bocas con la FIRMA del modelo (circulo de tal radio, contorno de tal tamano,
     tornillo cortado, caja), se agrupan en piezas/columnas o filas y se nombran con las reglas del catalogo.
  5. Controles de coherencia que el catalogo activa por modelo: 'desborde' (borne que no existe -> bloque
     siguiente de la misma hoja), 'conductores_por_boca' (dos cables en una boca de 1 conductor -> uno va al bloque
     siguiente) y 'comunes' (borne puenteado entre modulos -> el cable entra por el primer modulo).

Nada de este archivo conoce este tablero: todas las medidas y nombres estan en catalogo.json.
"""
import sys
import os
import re
import json
import math
import time
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
PROGRAMA = os.path.dirname(AQUI)              # la carpeta 'programa' (pdfvec.py, ocr_raster.py)
if PROGRAMA not in sys.path:
    sys.path.insert(0, PROGRAMA)
try:
    from . import primitivas as P              # como paquete: programa/bornes
except ImportError:                            # suelto: python motor.py ...
    if AQUI not in sys.path:
        sys.path.insert(0, AQUI)
    import primitivas as P  # noqa: E402

# version del motor: si cambia, el programa vuelve a calcular el mapeo aunque haya cache (bornes_auto.json)
VERSION = '2026.10.07-1'

LADOS = ('ARRIBA', 'ABAJO')


def _lock_pdfium():
    """pdfium no admite uso simultaneo desde varios hilos: el programa web comparte un candado (ocr_raster)."""
    try:
        from ocr_raster import PDFIUM_LOCK
        return PDFIUM_LOCK
    except Exception:
        import threading
        global _LOCK_LOCAL
        try:
            return _LOCK_LOCAL
        except NameError:
            _LOCK_LOCAL = threading.Lock()
            return _LOCK_LOCAL


# ============================================================================================ lectura
def leer_trazos(pdf, pagina):
    import pypdf
    from pdfvec import page_strokes, layer_names
    r = pypdf.PdfReader(pdf)
    return page_strokes(r, pagina, layer_names(r), with_color=True)


def detectar_etiquetas(pdf, pagina, region, escala=4.0):
    """Etiquetas amarillas: se renderiza la pagina y se buscan las manchas amarillas rectangulares.
    Devuelve [dict(x0, y0, x1, y1, cx, cy)] en puntos PDF (origen abajo a la izquierda)."""
    import numpy as np
    import pypdfium2 as pdfium
    with _lock_pdfium():
        doc = pdfium.PdfDocument(pdf)
        try:
            pg = doc[pagina]
            W, H = pg.get_size()
            img = np.asarray(pg.render(scale=escala).to_pil().convert('RGB'))
        finally:
            doc.close()
    return _etiquetas_de_imagen(img, W, H, region, escala)


def _etiquetas_de_imagen(img, W, H, region, escala):
    import numpy as np
    import cv2
    r, g, b = [img[:, :, i].astype(np.int16) for i in range(3)]
    m = ((r > 200) & (g > 200) & (b < 120)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, connectivity=8)
    out = []
    x0r, y0r, x1r, y1r = region
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        ex0, ex1 = x / escala, (x + w) / escala
        ey1, ey0 = H - y / escala, H - (y + h) / escala
        if min(ex1 - ex0, ey1 - ey0) < 3.0 or max(ex1 - ex0, ey1 - ey0) < 8.0:
            continue
        if a < 0.5 * w * h:
            continue
        cx, cy = (ex0 + ex1) / 2, (ey0 + ey1) / 2
        if not (x0r <= cx <= x1r and y0r <= cy <= y1r):
            continue
        out.append(dict(x0=float(ex0), y0=float(ey0), x1=float(ex1), y1=float(ey1), cx=float(cx), cy=float(cy)))
    return out


def capas_del_plano(trazos, region, general):
    """Capas que se toman como dibujo de los aparatos y capas del riel. Cada plano usa su estandar de capas
    (COMPONENTES, 00_COMPONENTS, _IGV_Componentes, '0', '01'...): ademas de las capas que nombra el catalogo, se
    toma toda capa con trazos en la bandeja que no sea de texto, cotas, marco, canaletas o riel (patrones del
    catalogo). Devuelve (capas_componentes, capas_riel)."""
    x0, y0, x1, y1 = region
    presentes = set()
    for t in trazos:
        if not t[2]:
            continue
        q = t[2][0]
        if x0 - 5 <= q[0] <= x1 + 5 and y0 - 5 <= q[1] <= y1 + 5:
            presentes.add(t[0])
    explicitas = set(general.get('capas_componentes', []))
    p_riel = re.compile(general.get('capas_riel_patron', r'(?i)riel|rail|\bdin\b'))
    p_no = re.compile(general.get('capas_excluidas_patron', r'(?i)text|txt|r[oó]tulo|etiqueta|amarillo|cota|dim'))
    riel = {c for c in presentes if c == general.get('capa_riel') or p_riel.search(c)}
    comp = set(c for c in presentes if c in explicitas)
    if general.get('capas_componentes_auto', True):
        comp |= {c for c in presentes if c not in riel and not p_no.search(c)}
    return comp, riel


def detectar_rieles(trazos, capa, region, alto_min=10.0, largo_min=30.0):
    """Tramos de riel DIN: grupos de lineas horizontales largas de la capa del riel con la misma extension en x.
    Las lineas pueden venir sueltas o como lados de un rectangulo (polilinea cerrada). Devuelve
    [dict(x0, x1, y0, y1, yc)]. 'capa' puede ser un nombre o un conjunto de nombres."""
    capas = {capa} if isinstance(capa, str) else set(capa)
    x0r, y0r, x1r, y1r = region
    hs = []
    for t in trazos:
        if t[0] not in capas or not t[2] or len(t[2]) < 2:
            continue
        for a, b in zip(t[2], t[2][1:]):
            if abs(a[1] - b[1]) < 0.5 and abs(a[0] - b[0]) > largo_min:
                xa, xb, y = min(a[0], b[0]), max(a[0], b[0]), (a[1] + b[1]) / 2
                if x0r - 5 <= xa and xb <= x1r + 5 and y0r <= y <= y1r:
                    hs.append((xa, xb, y))
    grupos = []
    for a, b, y in sorted(hs, key=lambda h: (round(h[0]), round(h[1]), h[2])):
        for g in grupos:
            if abs(g['x0'] - a) < 2 and abs(g['x1'] - b) < 2 and g['y0'] - 20 <= y <= g['y1'] + 20:
                g['y0'] = min(g['y0'], y)
                g['y1'] = max(g['y1'], y)
                break
        else:
            grupos.append(dict(x0=a, x1=b, y0=y, y1=y))
    out = [g for g in grupos if g['y1'] - g['y0'] > alto_min]
    # el mismo tramo dibujado dos veces (lineas sueltas + rectangulo) queda una sola vez
    ded = []
    for g in sorted(out, key=lambda g: -(g['x1'] - g['x0'])):
        if not any(abs(g['y0'] - h['y0']) < 1 and abs(g['y1'] - h['y1']) < 1 and g['x0'] >= h['x0'] - 2 and g['x1'] <= h['x1'] + 2
                   for h in ded):
            ded.append(g)
    for g in ded:
        g['yc'] = (g['y0'] + g['y1']) / 2
    return ded


def extender_rieles(rieles, etiquetas, comp, region, margen_v, hueco_max, ancho_max_trazo):
    """El riel casi siempre queda tapado por los aparatos y el plano solo dibuja los pedazos que se ven entre ellos.
    Cada tramo de riel se extiende a lo largo de su banda: primero por la cadena de etiquetas amarillas que estan a
    la altura del riel (sin saltos mayores que 'hueco_max'), y despues por los trazos chicos de los aparatos que
    cruzan la linea central del riel, mientras sigan pegados (asi el ultimo aparato del tramo entra en la zona)."""
    x0r, y0r, x1r, y1r = region
    for r in rieles:
        otros = [o for o in rieles if o is not r and not (o['y1'] < r['y0'] or o['y0'] > r['y1'])]

        def libre(x):
            return not any(o['x0'] - 2 <= x <= o['x1'] + 2 for o in otros)
        labs = sorted([t for t in etiquetas if r['y0'] - margen_v <= t['cy'] <= r['y1'] + margen_v and libre(t['cx'])],
                      key=lambda t: t['x0'])
        x1 = r['x1']
        for t in labs:
            if t['x1'] > x1 and t['x0'] - x1 < hueco_max:
                x1 = t['x1']
        x0 = r['x0']
        for t in sorted(labs, key=lambda t: -t['x1']):
            if t['x0'] < x0 and x0 - t['x1'] < hueco_max:
                x0 = t['x0']
        # trazos que cruzan el centro del riel
        cruzan = [b for b in comp if b[1] <= r['yc'] <= b[3] and b[2] - b[0] <= ancho_max_trazo]
        cambio = True
        while cambio:
            cambio = False
            for b in cruzan:
                if b[0] <= x1 + 0.6 and b[2] > x1 + 0.05 and libre(b[2]):
                    x1 = b[2]
                    cambio = True
                if b[2] >= x0 - 0.6 and b[0] < x0 - 0.05 and libre(b[0]):
                    x0 = b[0]
                    cambio = True
        r['x0'], r['x1'] = max(x0, x0r - 5), min(x1, x1r + 5)
    return rieles


def norm(s):
    return re.sub(r'\s+', '', str(s).upper()).replace(',', '.')


PAT_TAG = re.compile(r'^\d{2}[A-Z]+\d*$')
# fabricantes de aparamenta (para separar marca y modelo en un renglon de la lista de materiales)
FABRICANTES_RE = re.compile(r'(?i)\b(phoenix|schneider|mean\s*well|finder|chenzhu|weidm(?:u|ü|ue)ller|omron|abb|siemens|wago|'
                            r'epever|legrand|hager|eaton|moeller|allen[\s-]*bradley|rockwell|telemecanique|steute|'
                            r'pilz|murr|turck|pepperl|sick|ifm|lovato|chint|wieland|entrelec|conexel|vivion|trombetta|moxa|'
                            r'advantech|gefran|brevini)\b')


def leer_materiales(path):
    """lista_materiales.txt: una linea por componente, campos separados por '|'. Devuelve {tag: texto}."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8', errors='replace') as f:
        return materiales_de_lineas(f.read().splitlines())


def materiales_de_lineas(lineas):
    """Renglones de la lista de materiales ('tag | descripcion | marca | modelo'), como los de
    lista_materiales.txt o los que saca instructivo.materiales_funcional del plano funcional. Devuelve {tag: texto}."""
    out = {}
    for linea in lineas or []:
        campos = [c.strip() for c in str(linea).split('|')]
        tag = next((c for c in campos if PAT_TAG.match(c.replace(' ', ''))), None)
        if not tag:
            continue
        resto = ' | '.join(c for c in campos if c != tag)
        out[tag] = (out.get(tag, '') + ' | ' + resto).strip(' |')
    return out


def modelo_por_materiales(texto, modelos):
    """El modelo del catalogo cuyo alias mas largo aparece en el texto de la lista de materiales. Se ignoran los
    separadores de celda ('|'): el modelo puede venir partido en celdas ('ABB | SH | 202 | C10' = SH 202)."""
    t = norm(texto).replace('|', '')
    mejor, largo = None, 0
    for m in modelos:
        for a in m.get('alias', []):
            na = norm(a)
            if na and na in t and len(na) > largo:
                mejor, largo = m, len(na)
    return mejor


def raiz(tag):
    return re.sub(r'\d+$', '', tag)


# ============================================================================================ utilidades
def color_ok(c, general, color_modelo=None):
    if general.get('_monocromo'):
        return True
    tol = general.get('tolerancia_color', 0.12)
    if c is None:
        return color_modelo is None
    for ex in general.get('colores_excluidos', []):
        if P.color_parecido(c, ex, tol):
            return False
    if color_modelo is not None:
        return P.color_parecido(c, color_modelo, tol)
    return True


def dedup(bocas, d):
    out = []
    for b in sorted(bocas, key=lambda b: -b.get('peso', 0)):
        if not any(math.hypot(b['x'] - o['x'], b['y'] - o['y']) < d for o in out):
            out.append(b)
    return out


def num_cable(c):
    m = re.search(r'\d+', str(c))
    return int(m.group()) if m else 0


def orden_de_uso(q):
    """clave de orden de (i, uso, ...) para pines repetidos: posicion en el simbolo del funcional y despues numero de cable"""
    u = q[1]
    of = u.get('orden_funcional')
    try:
        of = float(of)
    except (TypeError, ValueError):
        of = None
    return (of is None, of or 0.0, num_cable(u.get('cable')))


def lado_de_uso(u):
    """ARRIBA/ABAJO del uso: la palabra del texto si la tiene; si no, 'parte' (el lado del borne en el aparato),
    y si no, 'lado'."""
    t = (u.get('texto') or '').upper()
    for w in LADOS:
        if re.search(r'\b' + w + r'\b', t):
            return w
    for k in ('parte', 'lado'):
        v = (u.get(k) or '').upper()
        if v in LADOS:
            return v
    return None


# ============================================================================================ motor
class Motor:
    def __init__(self, pdf, usos, catalogo, materiales):
        self.t0 = time.time()
        self.usos = usos
        self.cat = catalogo
        self.g = catalogo['general']
        self.modelos = catalogo['modelos']
        self.esc = float(usos.get('escala_mm_por_pt') or self.g.get('escala_defecto_mm_por_pt', 1.41))
        self.pagina = int(usos.get('pagina_pdf') or 1) - 1
        trazos = leer_trazos(pdf, self.pagina)
        if usos.get('region_bandeja'):
            self.region = tuple(usos['region_bandeja'])
        else:
            xs = [q[0] for t in trazos for q in t[2]]
            ys = [q[1] for t in trazos for q in t[2]]
            self.region = (min(xs), min(ys), max(xs), max(ys))
        self.capas_comp, self.capas_riel = capas_del_plano(trazos, self.region, self.g)
        self.esc_ = P.Escena(trazos, self.region, dict(self.g, capas_componentes=sorted(self.capas_comp)))
        # plano monocromo: si todo el dibujo de los aparatos es de un solo color, los colores del catalogo (pieza
        # azul, PE verde, bocas grises) no sirven para distinguir nada y se ignoran
        colores = defaultdict(int)
        for t in self.esc_.comp:
            if t[3] is not None and max(t[3][:3]) < 0.97:
                colores[tuple(round(v, 1) for v in t[3][:3])] += 1
        tot = sum(colores.values()) or 1
        self.monocromo = max(colores.values(), default=0) / tot > self.g.get('fraccion_monocromo', 0.995)
        self.g = dict(self.g, _monocromo=self.monocromo)
        self.arcos = self.esc_.arcos()
        self.curvas = self.esc_.curvas()
        self.rects = self.esc_.rectangulos()
        aviso_escala = None
        if not usos.get('escala_mm_por_pt'):
            # sin escala: el perfil del riel DIN mide 35 mm de alto (EN 60715)
            rs = detectar_rieles(trazos, self.capas_riel, self.region, alto_min=8.0, largo_min=15.0)
            hs = sorted(r['y1'] - r['y0'] for r in rs if r['y1'] - r['y0'] > 8.0)
            if hs:
                self.esc = float(self.g.get('alto_riel_mm', 35.0)) / hs[len(hs) // 2]
                aviso_escala = (f"sin escala en los usos: {self.esc:.4f} mm/pt sacada del alto del riel DIN "
                                f"({hs[len(hs) // 2]:.2f} pt = {self.g.get('alto_riel_mm', 35.0)} mm)")
        self.puentes = self._puentes(trazos)
        self.rieles = detectar_rieles(trazos, self.capas_riel, self.region,
                                      alto_min=self.mm(self.g.get('riel_alto_min_mm', 14.0)),
                                      largo_min=self.mm(self.g.get('riel_largo_min_mm', 25.0)))
        self.etiquetas = detectar_etiquetas(pdf, self.pagina, self.region)
        extender_rieles(self.rieles, self.etiquetas, [t[4] for t in self.esc_.comp], self.region,
                        self.mm(self.g.get('margen_etiqueta_riel_mm', 21)), self.mm(self.g.get('riel_hueco_max_mm', 40.0)),
                        self.mm(self.g.get('riel_ancho_max_trazo_mm', 30.0)))
        self.materiales = materiales
        # familias (tipo de aparato) del catalogo, en orden: para saber de la lista de materiales que es cada aparato
        self.familias = []
        for f in self.g.get('familias', []):
            try:
                self.familias.append((f['familia'], f.get('nombre') or f['familia'], re.compile(f['patron'])))
            except (KeyError, TypeError, re.error):
                continue
        self.avisos = [aviso_escala] if aviso_escala else []
        self.faltantes = []          # [{tag, texto_de_la_lista}]: la lista de materiales nombra un modelo que no esta en el catalogo
        self.sin_resolver = {}       # (componente, indice, texto, cable del uso) -> (modelo, por que quedo sin punto)
        if self.monocromo:
            self.avisos.append('plano monocromo: no se usan los colores del catalogo (PE verde, pieza azul, bocas grises)')
        self._asociar()

    def mm(self, v):
        return float(v) / self.esc

    # ------------------------------------------------------------------ puentes FBS (rellenos de color)
    def _puentes(self, trazos):
        """Puentes FBS: rellenos de color saturado (rojo, azul). En un plano monocromo (sin rellenos de color) se
        toman las barras oscuras rellenas, horizontales y finas, de la capa de los aparatos."""
        out, oscuros = [], []
        x0, y0, x1, y1 = self.region
        h_max, w_min = self.mm(self.g.get('puente_alto_max_mm', 4.5)), self.mm(self.g.get('puente_ancho_min_mm', 6.0))
        for t in trazos:
            if t[1] not in ('f', 'F', 'b', 'B') or not t[3] or not t[2]:
                continue
            c = t[3]
            b = P.bbox(t[2])
            if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
                continue
            d = dict(x0=b[0], y0=b[1], x1=b[2], y1=b[3], yc=(b[1] + b[3]) / 2)
            if max(c[:3]) - min(c[:3]) >= 0.5:
                out.append(d)
            elif max(c[:3]) < 0.3 and t[0] in self.capas_comp and b[3] - b[1] <= h_max and b[2] - b[0] >= max(w_min, 2.5 * (b[3] - b[1])):
                oscuros.append(d)
        return out if out else oscuros

    # ------------------------------------------------------------------ etiquetas y rieles
    @staticmethod
    def posicion_etiqueta(c):
        """(x, y) de la etiqueta del componente segun los usos, o None si no la trae (sin etiqueta_topografico, o con
        x / y vacios o que no son numeros)"""
        e = c.get('etiqueta_topografico') if isinstance(c, dict) else None
        if not isinstance(e, dict):
            return None
        try:
            x, y = float(e.get('x')), float(e.get('y'))
        except (TypeError, ValueError):
            return None
        return (x, y) if math.isfinite(x) and math.isfinite(y) else None

    def _asociar(self):
        dmax = self.mm(self.g.get('distancia_max_etiqueta_mm', 20))
        pares = []
        comps = self.usos['componentes']
        # componentes sin la posicion de su etiqueta (x / y vacios): no se puede saber cual es su zona; sus bornes
        # quedan sin punto (confianza baja, con aviso) y los demas siguen
        self.sin_posicion = set()
        for k, c in comps.items():
            pe = self.posicion_etiqueta(c)
            if pe is None:
                self.sin_posicion.add(k)
                continue
            for i, t in enumerate(self.etiquetas):
                d = math.hypot(t['cx'] - pe[0], t['cy'] - pe[1])
                if d <= dmax:
                    pares.append((d, k, i))
        usados_k, usados_i = set(), set()
        self.tag = {}
        for d, k, i in sorted(pares):
            if k in usados_k or i in usados_i:
                continue
            usados_k.add(k)
            usados_i.add(i)
            self.tag[k] = dict(self.etiquetas[i], leida=True)
        for k, c in comps.items():
            if k in self.tag:
                continue
            h, w = 2.4, 8.5
            if k in self.sin_posicion:
                x, y = self.region[0], self.region[1]
                self.tag[k] = dict(x0=x - w, x1=x + w, y0=y - h, y1=y + h, cx=x, cy=y, leida=False, sin_posicion=True)
                self.avisos.append(f'{k}: no tiene la posicion de su etiqueta en el topografico; sus bornes quedan sin punto exacto')
                continue
            x, y = self.posicion_etiqueta(c)
            self.tag[k] = dict(x0=x - w, x1=x + w, y0=y - h, y1=y + h, cx=x, cy=y, leida=False)
            self.avisos.append(f'{k}: no encontre su etiqueta amarilla, uso la posicion de usos_por_componente.json')
        # riel de cada componente: el tramo de riel que contiene la etiqueta (con margen vertical)
        self.riel = {}
        for k, t in self.tag.items():
            if t.get('sin_posicion'):
                self.riel[k] = None
                continue
            mv = self.mm(self.g.get('margen_etiqueta_riel_mm', 21))
            cand = [r for r in self.rieles if r['x0'] - 5 <= t['cx'] <= r['x1'] + 5 and r['y0'] - mv <= t['cy'] <= r['y1'] + mv]
            self.riel[k] = min(cand, key=lambda r: abs(r['yc'] - t['cy'])) if cand else None
        # delimitadores por riel: etiquetas de componentes + etiquetas ajenas que pisan la banda del riel
        self.delims = defaultdict(list)
        for k, t in self.tag.items():
            if self.riel[k] is not None:
                self.delims[id(self.riel[k])].append(dict(t, comp=k))
        propias = {(round(t['x0'], 1), round(t['y0'], 1)) for t in self.tag.values() if not t.get('sin_posicion')}
        for t in self.etiquetas:
            if (round(t['x0'], 1), round(t['y0'], 1)) in propias:
                continue
            for r in self.rieles:
                if r['x0'] - 5 <= t['cx'] <= r['x1'] + 5 and t['y0'] <= r['y1'] and t['y1'] >= r['y0']:
                    self.delims[id(r)].append(dict(t, comp=None))
        for v in self.delims.values():
            v.sort(key=lambda t: t['x0'])

    def siguiente(self, k):
        r = self.riel[k]
        if r is None:
            return None
        t = self.tag[k]
        for d in self.delims[id(r)]:
            if d['x0'] > t['x0'] + 0.5:
                return d
        return None

    def zona(self, k, m):
        t = self.tag[k]
        r = self.riel[k]
        alto = self.mm(m.get('alto_mm', 90) / 2 + self.g.get('margen_alto_mm', 5))
        if m.get('anclaje') == 'libre' or r is None:
            ancho = self.mm(m.get('ancho_mm', 80) / 2 + self.g.get('margen_alto_mm', 5))
            if m.get('anclaje') == 'izquierda':
                return (t['x0'] - self.mm(m.get('margen_izq_mm', 1)), t['cy'] - alto, t['x0'] + 2 * ancho, t['cy'] + alto), t['cy']
            return (t['cx'] - ancho, t['cy'] - alto, t['cx'] + ancho, t['cy'] + alto), t['cy']
        x0 = t['x0'] - self.mm(m.get('margen_izq_mm', 1))
        s = self.siguiente(k)
        x1 = (s['x0'] - self.mm(self.g.get('margen_der_mm', 1))) if s else r['x1']
        x1 = min(x1, r['x1'] + 2)
        return (x0, r['yc'] - alto, x1, r['yc'] + alto), r['yc']

    # ------------------------------------------------------------------ deteccion de bocas (firma)
    def bocas(self, m, caja):
        f = m['boca']
        x0, y0, x1, y1 = caja
        prim = f['primitiva']
        out = []
        if prim == 'circulo':
            rmin, rmax = self.mm(f['r_mm'][0]), self.mm(f['r_mm'][1])
            arcs = [a for a in self.arcos if x0 - 3 <= a[0] <= x1 + 3 and y0 - 3 <= a[1] <= y1 + 3]
            for c in P.circulos(arcs, rmin, rmax, cob_min=f.get('cob_min', 250)):
                if not (x0 <= c['x'] <= x1 and y0 <= c['y'] <= y1):
                    continue
                if not color_ok(c['color'], self.g, f.get('color')):
                    continue
                if f.get('sin_x', True) and self.esc_.tiene_x(c['x'], c['y'], c['r']):
                    continue
                out.append(dict(x=c['x'], y=c['y'], r=c['r'], peso=c['cob']))
            out = dedup(out, 0.6 * self.mm(f['r_mm'][0]))
        elif prim == 'contorno':
            wmin, wmax = [self.mm(v) for v in f['w_mm']]
            hmin, hmax = [self.mm(v) for v in f['h_mm']]
            for c in self.esc_.contornos(caja):
                if not (wmin <= c['w'] <= wmax and hmin <= c['h'] <= hmax):
                    continue
                if c['curvos'] < f.get('curvos_min', 0):
                    continue
                if not color_ok(c['color'], self.g, f.get('color')):
                    continue
                r = (c['w'] + c['h']) / 4
                if f.get('sin_x', True) and self.esc_.tiene_x(c['x'], c['y'], r):
                    continue
                out.append(dict(x=c['x'], y=c['y'], r=r, peso=c['n']))
            out = dedup(out, 0.5 * wmin)
        elif prim == 'tornillo_cortado':
            wmin, wmax = [self.mm(v) for v in f['w_mm']]
            cur = [c for c in self.curvas if x0 <= c[1][0] and c[1][2] <= x1 and y0 <= c[1][1] and c[1][3] <= y1
                   and color_ok(c[2], self.g)]
            for c in P.tornillos_cortados(cur, ancho=(wmin, wmax), alto_max=self.mm(f.get('h_max_mm', 4.8))):
                out.append(dict(x=c['x'], y=c['y'], r=c['r'], peso=1))
        elif prim == 'caja':
            pass
        return out

    # ------------------------------------------------------------------ estructura segun la disposicion
    def estructura(self, k, m):
        caja, yc = self.zona(k, m)
        t = self.tag[k]
        disp = m['disposicion']
        est = dict(modelo=m, caja=caja, yc=yc, tipo=disp['tipo'], piezas=[], grupos={}, cuerpo=None, validas=0, total=0)
        if disp['tipo'] == 'caja':
            f = m['boca']
            wmin, wmax = [self.mm(v) for v in f['w_mm']]
            hmin, hmax = [self.mm(v) for v in f['h_mm']]
            cand = [b for b in self.rects if b[0] - 0.5 <= t['cx'] <= b[2] + 0.5 and b[1] - 0.5 <= t['cy'] <= b[3] + 0.5
                    and wmin <= b[2] - b[0] <= wmax and hmin <= b[3] - b[1] <= hmax]
            if cand:
                est['cuerpo'] = min(cand, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
                est['validas'] = est['total'] = 1
            return est
        if disp['tipo'] == 'cuerpo':
            # aparato cuyos bornes no se reconocen en el dibujo (columna de bornes al frente, enchufes en la cara de
            # arriba): se toma el cuerpo y cada borne va donde dice la hoja de datos ('cuerpo' del modelo)
            est['total'] = 1
            cu = m['cuerpo']
            cuerpo = self.cuerpo_del_tag(t, cu)
            if cuerpo is not None:
                est['cuerpo'] = cuerpo
                est['validas'] = 1
                est['filas_cuerpo'] = self.filas_del_cuerpo(cuerpo, yc, cu) if cu.get('filas_dibujadas', True) else {}
            return est
        bocas = self.bocas(m, caja)
        est['bocas'] = bocas
        if disp['tipo'] == 'piezas':
            paso = self.mm(m.get('paso_mm', 6))
            tolx = max(0.9, 0.35 * paso)
            cols = []
            for b in sorted(bocas, key=lambda b: b['x']):
                if cols and abs(b['x'] - cols[-1]['x']) <= tolx:
                    cols[-1]['b'].append(b)
                    cols[-1]['x'] = sum(q['x'] for q in cols[-1]['b']) / len(cols[-1]['b'])
                else:
                    cols.append(dict(x=b['x'], b=[b]))
            esperado = disp['bocas']
            lxc = disp.get('lados_por_cantidad')
            piezas = []
            for c in cols:
                ys = sorted(c['b'], key=lambda b: b['y'])
                if len(ys) >= 2:
                    gap, i = max((ys[j + 1]['y'] - ys[j]['y'], j) for j in range(len(ys) - 1))
                    if self.riel[k] is not None and not (ys[i]['y'] <= yc <= ys[i + 1]['y']):
                        i = max([j for j in range(len(ys)) if ys[j]['y'] < yc], default=-1)
                    abajo, arriba = ys[:i + 1], ys[i + 1:]
                else:
                    abajo, arriba = ([], ys) if ys and ys[0]['y'] > yc else (ys, [])
                pz = dict(x=c['x'], arriba=sorted(arriba, key=lambda b: -b['y']), abajo=sorted(abajo, key=lambda b: b['y']))
                if lxc:
                    na, nb = len(pz['arriba']), len(pz['abajo'])
                    la, lb = lxc.get(str(na)), lxc.get(str(nb))
                    ok = la is not None and lb is not None and la != lb
                    if ok:
                        pz[la] = pz['arriba']
                        pz[lb] = pz['abajo']
                else:
                    ok = len(pz['arriba']) == esperado.get('arriba', 0) and len(pz['abajo']) == esperado.get('abajo', 0)
                pz['ok'] = ok
                piezas.append(pz)
            est['total'] = len(piezas)
            buenas = [p for p in piezas if p['ok']]
            if m.get('anclaje') == 'sobre' and m.get('polos'):
                buenas = sorted(buenas, key=lambda p: abs(p['x'] - t['cx']))[:int(m['polos'])]
                buenas.sort(key=lambda p: p['x'])
            est['piezas'] = buenas
            est['validas'] = len(buenas)
            est['descartadas'] = [p for p in piezas if not p['ok']]
        elif disp['tipo'] == 'filas':
            filas = []
            for b in sorted(bocas, key=lambda b: b['y']):
                for f in filas:
                    if abs(f['y'] - b['y']) <= max(0.6, 0.4 * b['r']):
                        f['b'].append(b)
                        f['y'] = sum(q['y'] for q in f['b']) / len(f['b'])
                        break
                else:
                    filas.append(dict(y=b['y'], b=[b]))
            for f in filas:
                f['b'].sort(key=lambda b: b['x'])
            for gspec in disp['grupos']:
                n = int(gspec['n'])
                lado = gspec.get('lado', 'centro')
                if gspec.get('paso_mm') and not gspec.get('alineado_con'):
                    bs = self.serie_con_paso(filas, gspec, n, lado, yc, t['cx'])
                    if bs:
                        est['grupos'][gspec['nombre']] = dict(spec=gspec, b=bs, y=sum(b['y'] for b in bs) / n)
                    continue
                cand = [f for f in filas if len(f['b']) >= n and (lado == 'centro' or (lado == 'arriba') == (f['y'] > yc))]
                if not cand:
                    continue
                al = gspec.get('alineado_con')
                if al:
                    # fila de pocos tornillos que se reconoce por estar en la misma columna que un pin de otro grupo
                    # (ej. B1 del temporizador, debajo de A1) y mas adentro o mas afuera que ese grupo
                    ref = est['grupos'].get(al[0])
                    if ref is None or len(ref['b']) < int(al[1]):
                        continue
                    rb = ref['b'][int(al[1]) - 1]
                    tolx = max(0.4, 0.5 * rb['r'])
                    pos = gspec.get('posicion')
                    opciones = []
                    for f in cand:
                        if abs(f['y'] - ref['y']) < 0.3:
                            continue
                        if pos == 'interior' and not abs(f['y'] - yc) < abs(ref['y'] - yc):
                            continue
                        if pos == 'exterior' and not abs(f['y'] - yc) > abs(ref['y'] - yc):
                            continue
                        cerca = [j for j, b in enumerate(f['b']) if abs(b['x'] - rb['x']) <= tolx]
                        if cerca:
                            opciones.append((abs(f['y'] - ref['y']), f, cerca[0]))
                    if not opciones:
                        continue
                    _, f, j = min(opciones, key=lambda q: q[0])
                    j0 = max(0, min(j, len(f['b']) - n))
                    bs = f['b'][j0:j0 + n]
                else:
                    f = min(cand, key=lambda f: (len(f['b']) != n, abs(sum(b['x'] for b in f['b']) / len(f['b']) - t['cx'])))
                    bs = f['b']
                    if len(bs) > n:
                        i0 = min(range(len(bs) - n + 1), key=lambda i: abs(sum(b['x'] for b in bs[i:i + n]) / n - t['cx']))
                        bs = bs[i0:i0 + n]
                est['grupos'][gspec['nombre']] = dict(spec=gspec, b=bs, y=sum(b['y'] for b in bs) / n)
            est['total'] = len(disp['grupos'])
            est['validas'] = len(est['grupos'])
            # el bloque del plano no dibuja los bornes del modelo (otra biblioteca de CAD): se toma el cuerpo del
            # aparato (contorno cerrado que contiene la etiqueta) y los bornes se ubican con las medidas de la hoja
            # de datos, desde el borde de arriba o de abajo del cuerpo
            cu = m.get('cuerpo')
            if cu and est['validas'] < est['total']:
                cuerpo = self.cuerpo_del_tag(t, cu)
                if cuerpo is not None:
                    est['cuerpo'] = cuerpo
                    est['tipo'] = 'cuerpo'
                    est['validas'] = est['total']
                    est['filas_cuerpo'] = self.filas_del_cuerpo(est['cuerpo'], yc, cu)
        return est

    def cuerpo_del_tag(self, t, cu):
        """contorno cerrado mas chico que contiene la etiqueta t con el ancho y alto del 'cuerpo' del modelo, o None"""
        wmin, wmax = [self.mm(v) for v in cu['w_mm']]
        hmin, hmax = [self.mm(v) for v in cu['h_mm']]
        cc = [b for b in self.esc_.cerrados() if b[0] - 0.5 <= t['cx'] <= b[2] + 0.5 and b[1] - 0.5 <= t['cy'] <= b[3] + 0.5
              and wmin <= b[2] - b[0] <= wmax and hmin <= b[3] - b[1] <= hmax]
        return min(cc, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])) if cc else None

    def serie_con_paso(self, filas, gspec, n, lado, yc, cx):
        """Grupo de n tornillos con paso fijo ('paso_mm' del grupo: enchufes de los modulos). En cada fila del lado se
        busca la serie de n posiciones con ese paso que mas tornillos dibujados explica (desempate: la mas cercana a la
        etiqueta); asi no se mezcla el enchufe del aparato vecino ni se corre la serie si un tornillo esta dibujado de
        otra forma. Los que faltan se completan con el paso ('inferido': confianza media). Hacen falta al menos
        'min_vistos' tornillos vistos (por defecto n-1, minimo 2). Devuelve la lista de bocas o None."""
        paso = self.mm(float(gspec['paso_mm']))
        tol = 0.3 * paso
        min_vistos = int(gspec.get('min_vistos', max(2, n - 1)))
        mejor = None
        for f in filas:
            if not (lado == 'centro' or (lado == 'arriba') == (f['y'] > yc)):
                continue
            for b0 in f['b']:
                for j in range(n):
                    xs = [b0['x'] + (q - j) * paso for q in range(n)]
                    hits = []
                    for x in xs:
                        c = min(f['b'], key=lambda b: abs(b['x'] - x))
                        hits.append(c if abs(c['x'] - x) <= tol and all(c is not h for h in hits) else None)
                    nh = sum(h is not None for h in hits)
                    clave = (nh, -abs(sum(xs) / n - cx))
                    if mejor is None or clave > mejor[0]:
                        mejor = (clave, f, xs, hits)
        if mejor is None or mejor[0][0] < min_vistos:
            return None
        _, f, xs, hits = mejor
        vistos = [h for h in hits if h is not None]
        r = sum(h['r'] for h in vistos) / len(vistos)
        return [h if h is not None else dict(x=x, y=f['y'], r=r, peso=0, inferido=True) for x, h in zip(xs, hits)]

    @staticmethod
    def dy_por_lado(cu):
        """distancias distintas (mm) desde el borde de arriba y desde el de abajo que usan los pines de 'cuerpo',
        ordenadas de afuera (la mas chica: enchufe exterior) hacia adentro"""
        pines = cu.get('pines', {})
        return {lado: sorted({float(s['dy_mm']) for s in pines.values() if (s.get('desde', 'abajo') == 'arriba') == (lado == 'arriba')})
                for lado in ('arriba', 'abajo')}

    def filas_del_cuerpo(self, cuerpo, yc, cu):
        """Bloque SIMBOLICO (de otra biblioteca de CAD) que no dibuja un tornillo por borne, pero si las filas de los
        enchufes: tornillos, ranuras o lenguetas chicas dentro del cuerpo, cerca del borde de arriba o de abajo.
        Convencion verificada con fotos (66817): x = centro del cuerpo + posicion real del borne; y = la fila DIBUJADA
        que corresponde al escalonado real del enchufe. Se toman, en cada lado, tantas filas dibujadas como filas de
        enchufes tiene el modelo ('dy_mm' distintos de ese lado): primero las filas de piezas repetidas (dos o mas
        tornillos o ranuras iguales lado a lado), las mas de adentro; si faltan, las de una sola pieza (lengueta) mas
        cercanas a las ya elegidas. Devuelve {'arriba': [y...], 'abajo': [y...]} de afuera (borde) hacia adentro;
        una lista vacia si ese lado no tiene suficientes filas dibujadas (se usa la medida 'dy_mm' desde el borde)."""
        bx0, by0, bx1, by1 = cuerpo
        W = bx1 - bx0
        dys = self.dy_por_lado(cu)
        hmax = self.mm(cu.get('pieza_alto_max_mm', 3.0))
        wmin = self.mm(cu.get('pieza_ancho_min_mm', 0.8))
        wmax = float(cu.get('pieza_ancho_max_frac', 0.5)) * W
        margen = self.mm(cu.get('filas_margen_mm', 5.0))
        tol = max(0.25, self.mm(0.35))
        piezas, vistas = [], set()
        for t in self.esc_.comp + self.esc_.comp_fill:
            b = t[4]
            if b[0] < bx0 - 0.05 or b[2] > bx1 + 0.05 or b[1] < by0 - 0.05 or b[3] > by1 + 0.05:
                continue
            w, h = b[2] - b[0], b[3] - b[1]
            if not (wmin <= w <= wmax and h <= hmax):
                continue
            if b[0] <= bx0 + 0.15 or b[2] >= bx1 - 0.15:          # pegada a un costado: es parte de la carcasa
                continue
            k = tuple(round(v, 1) for v in b)
            if k in vistas:
                continue
            vistas.add(k)
            piezas.append(dict(x=(b[0] + b[2]) / 2, y=(b[1] + b[3]) / 2, w=w, h=h))
        out = {}
        for lado, borde in (('arriba', by1), ('abajo', by0)):
            n = len(dys[lado])
            out[lado] = []
            if not n:
                continue
            alcance = self.mm(max(dys[lado])) + margen
            ps = [p for p in piezas if abs(borde - p['y']) <= alcance and (p['y'] > yc) == (lado == 'arriba')]
            filas = []
            for p in sorted(ps, key=lambda p: abs(borde - p['y'])):
                for f in filas:
                    if abs(f['y'] - p['y']) <= tol:
                        f['p'].append(p)
                        f['y'] = sum(q['y'] for q in f['p']) / len(f['p'])
                        break
                else:
                    filas.append(dict(y=p['y'], p=[p]))
            for f in filas:
                f['repetida'] = any(abs(a['w'] - b['w']) <= 0.2 * max(a['w'], b['w']) and abs(a['h'] - b['h']) <= 0.2 * max(a['h'], b['h'])
                                    and abs(a['x'] - b['x']) > 0.5 * max(a['w'], b['w'])
                                    for i, a in enumerate(f['p']) for b in f['p'][i + 1:])
            adentro = lambda f: -abs(borde - f['y'])            # mas grande = mas cerca del riel
            elegidas = sorted([f for f in filas if f['repetida']], key=adentro, reverse=True)[:n]
            sueltas = [f for f in filas if not f['repetida']]
            while len(elegidas) < n and sueltas:
                if elegidas:
                    s = min(sueltas, key=lambda f: min(abs(f['y'] - e['y']) for e in elegidas))
                else:
                    s = max(sueltas, key=adentro)
                sueltas.remove(s)
                elegidas.append(s)
            if len(elegidas) == n:
                out[lado] = [f['y'] for f in sorted(elegidas, key=lambda f: abs(borde - f['y']))]
        return out

    # ------------------------------------------------------------------ lado fisico del diodo
    def lado_puente(self, est, defecto):
        pz = est['piezas']
        if not pz:
            return defecto
        xa = min(p['x'] for p in pz) - 1
        xb = max(p['x'] for p in pz) + 1
        ya = [p['arriba'][0]['y'] for p in pz if p['arriba']]
        yb = [p['abajo'][0]['y'] for p in pz if p['abajo']]
        if not ya or not yb:
            return defecto
        ymid = (sum(ya) / len(ya) + sum(yb) / len(yb)) / 2
        cand = [b for b in self.puentes if b['x1'] >= xa and b['x0'] <= xb and min(yb) <= b['yc'] <= max(ya)]
        if not cand:
            return defecto
        b = max(cand, key=lambda b: min(b['x1'], xb) - max(b['x0'], xa))
        if abs(b['yc'] - ymid) < 0.2:
            return defecto
        return 'arriba' if b['yc'] > ymid else 'abajo'

    # ------------------------------------------------------------------ nombres -> punto
    def resolver(self, k, est, usos_k):
        """Devuelve {indice_uso: dict(x, y, r, confianza, como)} y la lista de usos que desbordan."""
        m = est['modelo']
        nom = m.get('nombres', {})
        res, desborde = {}, []
        if est['tipo'] == 'piezas':
            pz = est['piezas']
            comunes = self.comunes_puenteados(k, usos_k, nom)
            numeracion = self.numeracion(k, est, usos_k, nom)
            for i, u in usos_k:
                clave = str(u.get('borne') or '').strip()
                if u.get('punto') not in (None, ''):
                    clave = f"{clave}.{u['punto']}"
                regla, mo = None, None
                for rg in nom.get('reglas', []):
                    mo = re.match(rg['patron'], clave, re.I)
                    if mo:
                        regla = rg
                        break
                if not regla:
                    continue
                g1 = mo.group(1) if mo.groups() else None
                # pieza
                pv = regla.get('pieza', 1)
                nota_comun = ''
                renombra_modulo = False        # el texto se corrige al modulo donde quedo el punto
                if pv == 'modulo':
                    suf = str(u.get('tag') or '')[len(k):]
                    borne_u = str(u.get('borne') or '').strip().upper()
                    if borne_u in comunes:
                        npz, conf = 1, 'media'
                        renombra_modulo = True     # comun puenteado real: entra por el primer modulo del grupo
                        nota_comun = (f" | {borne_u} es un comun puenteado (cableado en {comunes[borne_u][0]} modulo(s) y "
                                      f"{comunes[borne_u][1]} en {comunes[borne_u][2]}): el cable entra por el primer modulo"
                                      + (f" (el texto dice modulo {suf})" if suf.isdigit() and int(suf) != 1 else ''))
                    elif suf.isdigit():
                        npz = int(suf)
                        conf = 'alta'
                    elif len(pz) == 1 and not est.get('descartadas'):
                        # rele UNICO sin numero de modulo en el texto ('43KR 11'): no hay otro modulo y el texto queda
                        # como esta (no se renombra a '43KR1 11')
                        npz, conf = 1, 'alta'
                    else:
                        # texto sin numero de modulo en un bloque de varios modulos ('46KR A2'): el de su pareja de
                        # bobina; si no hay pareja, el modulo queda a revisar (sin punto)
                        npz = self.modulo_por_pareja(k, u, usos_k, nom)
                        conf = 'media'
                        if npz is None:
                            self.sin_resolver[(k, i, u.get('texto'), str(u.get('cable')))] = (m['id'], f"{m['id']}: '{u.get('texto')}' no dice el numero de modulo y "
                                                                  f"el bloque tiene {len(pz)} modulos; modulo a revisar (queda en la etiqueta)")
                            continue
                        renombra_modulo = len(pz) > 1
                elif isinstance(pv, int):
                    npz, conf = pv, 'alta'
                elif pv == '$1':
                    npz, conf = int(g1), 'alta'
                elif pv.startswith('ceil($1/'):
                    d = int(re.search(r'/(\d+)', pv).group(1))
                    npz, conf = -(-int(g1) // d), 'alta'
                else:
                    npz, conf = int(pv), 'alta'
                # lado y boca
                nota_num = ''
                if 'punto' in regla:
                    pto = mo.group(2)
                    segunda = False
                    if pto not in nom['puntos'] and nom.get('segunda_bornera'):
                        # N.5-N.8: la segunda bornera del numero N (regla del taller: N.1-N.4 es la de la izquierda)
                        ppp = int(nom['segunda_bornera'].get('puntos_por_pieza', 4))
                        if pto.isdigit() and ppp < int(pto) <= 2 * ppp:
                            pto, segunda = str(int(pto) - ppp), True
                    if pto not in nom['puntos']:
                        continue
                    lado, boca = nom['puntos'][pto]
                    if numeracion is not None:
                        mapa, conf_num, como_num = numeracion
                        lst = mapa.get(npz)
                        if not lst or (segunda and len(lst) < 2):
                            npz = len(pz) + 1
                        else:
                            npz = lst[1 if segunda else 0] + 1
                            if conf_num != 'alta':
                                conf = 'media'
                            nota_num = (f" | numero {g1} = " + ('piezas ' + ' y '.join(str(j + 1) for j in lst) if len(lst) > 1
                                                                else 'pieza ' + str(lst[0] + 1)) + f" ({como_num})")
                    elif segunda:
                        continue
                else:
                    lado = regla.get('lado', 'texto')
                    bv = regla.get('boca', 0)
                    if isinstance(bv, str) and bv.startswith('paridad'):
                        boca = 0 if int(g1) % 2 == 1 else 1
                    else:
                        boca = int(bv)
                if lado == 'texto':
                    lt = lado_de_uso(u)
                    if lt is None:
                        continue
                    lado = lt.lower()
                elif lado == 'diodo':
                    dd = nom.get('diodo', {})
                    lt = lado_de_uso(u)
                    if lt is None:
                        continue
                    lp = self.lado_puente(est, dd.get('puente_por_defecto', 'abajo'))
                    rel = dd.get(lt, 'puente')
                    lado = lp if rel == 'puente' else ('arriba' if lp == 'abajo' else 'abajo')
                if npz < 1 or npz > len(pz):
                    if nom.get('desborde'):
                        desborde.append((i, u))
                    continue
                lista = pz[npz - 1].get(lado, [])
                if boca >= len(lista):
                    continue
                b = lista[boca]
                res[i] = dict(x=b['x'], y=b['y'], r=b['r'], confianza=conf, bloque=k,
                              como=f"{m['id']}: pieza {npz} de {len(pz)}, lado {lado}, boca {boca} ({'extremo' if boca == 0 else 'interior'})" + nota_comun + nota_num)
                if pv == 'modulo' and renombra_modulo:
                    res[i]['modulo'] = npz          # modulo donde quedo el punto (43KR2 A2 comun -> modulo 1)
        elif est['tipo'] == 'filas':
            pines = nom.get('pines', {})
            alias = {norm(a): v for a, v in nom.get('alias', {}).items()}
            porname = defaultdict(list)
            for i, u in usos_k:
                borne = str(u.get('borne') or '').strip()
                spec, num, nombre = None, None, None
                if borne in pines:
                    spec, nombre = pines[borne], borne
                else:
                    mnum = re.search(r'\d+', borne)
                    num = int(mnum.group()) if mnum else None
                    nm = norm(re.sub(r'[\d()]', '', borne))
                    if len(nm) > 1 and nm.endswith('-'):
                        nm = nm[:-1]
                    if len(nm) > 1 and nm.startswith('-') and norm(nm[1:]) in {norm(p) for p in pines}:
                        pass
                    nm = alias.get(nm, nm)
                    for pn, ps in pines.items():
                        if norm(pn) == nm:
                            spec, nombre = ps, pn
                            break
                if spec is None:
                    continue
                porname[nombre].append((i, u, spec, num))
            for nombre, lst in porname.items():
                # pines con el mismo nombre en varios tornillos (DDR: -Vo -Vo +Vo +Vo): el n-esimo borne de ese nombre en
                # el SIMBOLO del funcional va al n-esimo tornillo de ese nombre (de izquierda a derecha); el numero de
                # cable solo desempata (o manda, si los usos no traen 'orden_funcional')
                lst.sort(key=orden_de_uso)
                for j, (i, u, spec, num) in enumerate(lst):
                    gr = est['grupos'].get(spec.get('grupo'))
                    if gr is None:
                        continue
                    conf = nom.get('confianza', 'alta')
                    if 'por_lado' in spec:
                        lt = lado_de_uso(u)
                        if lt is None or lt not in spec['por_lado']:
                            continue
                        pin = int(spec['por_lado'][lt])
                    elif 'pin' in spec:
                        pin = int(spec['pin'])
                    else:
                        lp = spec.get('pines', [1])
                        if num is not None and num in lp:
                            pin = num
                        else:
                            pin = lp[j % len(lp)]
                    fila = int(spec.get('fila', 0))
                    bs = gr['b']
                    gspec = gr['spec']
                    nota_inf = ''
                    if fila == 0 and len(bs) >= pin and gspec.get('tornillos_por_fila', [len(bs)])[0] == len(bs):
                        b = bs[pin - 1]
                        x, y, r = b['x'], b['y'], b['r']
                        if b.get('inferido'):
                            # tornillo que no se reconocio en el dibujo: se completo con el paso de los vecinos
                            conf = 'media'
                            nota_inf = f" (tornillo no reconocido en el dibujo: ubicado con el paso de {gspec['paso_mm']} mm)"
                    else:
                        nfila = gspec.get('tornillos_por_fila', [len(bs)] * (fila + 1))[fila]
                        cx = sum(b['x'] for b in bs) / len(bs)
                        pitch = (bs[-1]['x'] - bs[0]['x']) / (len(bs) - 1) if len(bs) > 1 else 0
                        x = cx + (pin - (nfila + 1) / 2) * pitch
                        off = self.mm(gspec.get('filas_mm', [0] * (fila + 1))[fila])
                        y = gr['y'] - off if gspec.get('lado') == 'arriba' else gr['y'] + off
                        r = sum(b['r'] for b in bs) / len(bs)
                        conf = 'media'
                    res[i] = dict(x=x, y=y, r=r, confianza=conf,
                                  como=f"{m['id']}: grupo {spec.get('grupo')} pin {pin}" + (f" fila {fila} (no dibujada, corrida {gspec.get('filas_mm')[fila]} mm)" if fila else '') + nota_inf)
        elif est['tipo'] == 'cuerpo' and est['cuerpo']:
            bx0, by0, bx1, by1 = est['cuerpo']
            cu = m['cuerpo']
            pines = cu.get('pines', {})
            dys = self.dy_por_lado(cu)
            filas = est.get('filas_cuerpo') or {}
            for i, u in usos_k:
                borne = norm(u.get('borne') or '')
                spec = next((v for pn, v in pines.items() if norm(pn) == borne), None)
                if spec is None:
                    continue
                lado = 'arriba' if spec.get('desde', 'abajo') == 'arriba' else 'abajo'
                x = (bx0 + bx1) / 2 + self.mm(spec['dx_mm']) if 'dx_mm' in spec else bx0 + spec['fx'] * (bx1 - bx0)
                pos_x = (f" y {spec['dx_mm']:+} mm del centro" if 'dx_mm' in spec else '')
                fl = filas.get(lado) or []
                if fl and float(spec['dy_mm']) in dys[lado]:
                    j = dys[lado].index(float(spec['dy_mm']))
                    y = fl[j]
                    nombre_fila = ('exterior' if j == 0 else 'interior') if len(fl) == 2 else f'{j + 1} de {len(fl)} desde afuera'
                    como = (f"{m['id']}: el bloque es simbolico y no dibuja cada borne; {u.get('borne')} va en la fila dibujada "
                            f"{nombre_fila} de {lado} (enchufe a {spec.get('dy_mm')} mm del borde en el aparato real){pos_x}")
                else:
                    y = by1 - self.mm(spec['dy_mm']) if lado == 'arriba' else by0 + self.mm(spec['dy_mm'])
                    como = (f"{m['id']}: " + ('' if m['disposicion']['tipo'] == 'cuerpo' else 'el bloque no dibuja sus bornes; ')
                            + f"{u.get('borne')} ubicado con la hoja de datos a {spec.get('dy_mm')} mm del borde {lado} del cuerpo{pos_x}")
                res[i] = dict(x=x, y=y, r=self.mm(cu.get('r_borne_mm', 1.5)), confianza='media', como=como)
        elif est['tipo'] == 'caja' and est['cuerpo']:
            bx0, by0, bx1, by1 = est['cuerpo']
            pines = nom.get('pines', {})
            for i, u in usos_k:
                borne = norm(u.get('borne') or '')
                spec = next((v for pn, v in pines.items() if norm(pn) == borne), None)
                if spec is None:
                    continue
                x = bx0 + spec['fx'] * (bx1 - bx0)
                y = by0 + self.mm(spec['dy_mm']) if spec.get('desde', 'abajo') == 'abajo' else by1 - self.mm(spec['dy_mm'])
                res[i] = dict(x=x, y=y, r=self.mm(m.get('r_borne_mm', 2.5)), confianza=nom.get('confianza', 'media'),
                              como=f"{m['id']}: {borne} a {spec['fx']:.3f} del ancho del cuerpo, {spec.get('desde', 'abajo')}")
        return res, desborde

    def puente_entre(self, a, b, est):
        """True si un puente (relleno) cubre las piezas a y b (las dos columnas) entre sus bocas de arriba y de abajo."""
        ya = [q['y'] for q in a.get('arriba', []) + b.get('arriba', [])]
        yb = [q['y'] for q in a.get('abajo', []) + b.get('abajo', [])]
        if not ya or not yb:
            return False
        tol = 0.25 * self.mm(est['modelo'].get('paso_mm', 6))
        return any(p['x0'] <= min(a['x'], b['x']) + tol and p['x1'] >= max(a['x'], b['x']) - tol and min(yb) < p['yc'] < max(ya)
                   for p in self.puentes)

    def numeracion(self, k, est, usos_k, nom):
        """Numero de borne -> piezas, cuando el instructivo usa la 'segunda bornera' de un numero (N.5-N.8).
        Regla del taller: si un numero tiene dos borneras, la de la izquierda es N.1-N.4 y la segunda N.5-N.8. Las
        borneras de un mismo numero van pegadas (sin separador entre ellas: el separador se ve como un hueco mayor que
        el paso) y, si el plano dibuja puentes, unidas por un puente; un separador o la falta de puente empiezan otro
        numero. Si eso no cierra con los usos (algun N.5-N.8 sin segunda pieza, o menos grupos que numeros), se
        reparte por los usos: cada numero ocupa una pieza, o dos si tiene usos N.5-N.8.
        Sin usos N.5-N.8 devuelve None: un numero = una pieza (como en el 75286, donde hay puentes entre numeros).
        Devuelve ({numero: [indices de pieza]}, confianza, como)."""
        sb = nom.get('segunda_bornera')
        pz = est['piezas']
        if not sb or not pz:
            return None
        ppp = int(sb.get('puntos_por_pieza', 4))
        dobles, maxn = set(), 0
        for _, u in usos_k:
            try:
                n, p = int(str(u.get('borne')).strip()), int(u.get('punto'))
            except (TypeError, ValueError):
                continue
            maxn = max(maxn, n)
            if p > ppp:
                dobles.add(n)
        if not dobles:
            return None
        paso = self.mm(est['modelo'].get('paso_mm', 6))
        juntos = [pz[i]['x'] - pz[i - 1]['x'] <= float(sb.get('factor_separador', 1.15)) * paso for i in range(1, len(pz))]
        puentes = [self.puente_entre(pz[i - 1], pz[i], est) for i in range(1, len(pz))]
        if any(puentes):
            juntos = [j and q for j, q in zip(juntos, puentes)]
        grupos = [[0]]
        for i in range(1, len(pz)):
            if juntos[i - 1] and len(grupos[-1]) < 2:
                grupos[-1].append(i)
            else:
                grupos.append([i])
        if len(grupos) >= maxn and all(len(grupos[n - 1]) >= 2 for n in dobles if n >= 1):
            return ({n + 1: g for n, g in enumerate(grupos)}, 'alta',
                    'borneras agrupadas por separador' + (' y puente' if any(puentes) else ''))
        mapa, i = {}, 0
        for n in range(1, maxn + 1):
            c = 2 if n in dobles else 1
            mapa[n] = list(range(i, min(i + c, len(pz))))
            i += c
        aviso = f"{k}: los separadores/puentes del dibujo no explican los N.5-N.8; se reparte por los usos (revisar)"
        if aviso not in self.avisos:
            self.avisos.append(aviso)
        return mapa, 'media', 'repartido por los usos'

    def comunes_puenteados(self, k, usos_k, nom):
        """Bornes comunes unidos con un puente FBS entre modulos (ej. los A2 de un grupo de reles).
        Se deducen de los usos: si un borne esta cableado en MENOS modulos que su pareja (A2 en 1 modulo y A1 en
        4), los demas modulos lo reciben por el puente. Devuelve {borne: (n_modulos, pareja, n_modulos_pareja)}."""
        out = {}
        for c in nom.get('comunes', []):
            b, pj = str(c['borne']).upper(), str(c['pareja']).upper()

            def modulos(nombre):
                ms, sueltos = set(), 0
                for _, u in usos_k:
                    if str(u.get('borne') or '').strip().upper() != nombre:
                        continue
                    suf = str(u.get('tag') or '')[len(k):]
                    if suf.isdigit():
                        ms.add(int(suf))
                    else:
                        sueltos += 1
                return len(ms) + sueltos
            nb, npj = modulos(b), modulos(pj)
            if 0 < nb < npj and npj >= int(c.get('min_modulos', 2)):
                out[b] = (nb, pj, npj)
        return out

    def resolver_compartidas(self):
        """Una boca push-in lleva UN conductor. Si en un bloque con 'desborde' dos cables distintos caen en la misma
        boca, uno de los dos tiene mal la etiqueta (el instructivo puso la del bloque vecino). Se pasa al bloque
        siguiente el cable que deja todo coherente: sin bocas compartidas y sin cables con dos puntas en el mismo
        bloque (dos bornes de un mismo bloque se unen con puente, no con cable). Si no hay una opcion claramente
        mejor, no se mueve nada y queda el aviso."""
        comps = self.usos['componentes']

        def puntas(cable, excluir=None):
            out = []
            for k2, r2 in self.resultado.items():
                for i2, p2 in r2.items():
                    u2 = comps[k2]['usos'][i2]
                    if str(u2.get('cable')) == cable and (k2, i2) != excluir:
                        out.append((p2.get('bloque', k2), p2))
            return out

        for k, c in comps.items():
            nom = self.elegido[k].get('nombres', {})
            if int(nom.get('conductores_por_boca', 0)) != 1 or not nom.get('desborde'):
                continue
            sig = self.vecino_desborde(k)
            if sig is None or self.estructuras.get(sig) is None:
                continue
            por_boca = defaultdict(list)
            for i, p in self.resultado[k].items():
                if p.get('bloque', k) == k:
                    por_boca[(round(p['x'], 1), round(p['y'], 1))].append(i)
            for boca, idx in por_boca.items():
                cables = {str(c['usos'][i].get('cable')) for i in idx}
                if len(idx) < 2 or len(cables) < 2:
                    continue
                opciones = []
                for i in idx:
                    u = c['usos'][i]
                    cab = str(u.get('cable'))
                    res, _ = self.resolver(sig, self.estructuras[sig], [(i, dict(u))])
                    if i not in res:
                        continue
                    p2 = res[i]
                    costo = 0
                    # la boca de destino tiene que estar libre
                    for k3, r3 in self.resultado.items():
                        for i3, p3 in r3.items():
                            if (k3, i3) != (k, i) and math.hypot(p3['x'] - p2['x'], p3['y'] - p2['y']) < 0.3 \
                                    and str(comps[k3]['usos'][i3].get('cable')) != cab:
                                costo += 1
                    # el cable movido no puede quedar con dos puntas en el bloque de destino
                    costo += sum(1 for b2, _ in puntas(cab, (k, i)) if b2 == sig)
                    # los que se quedan no pueden tener otra punta en este bloque
                    for j in idx:
                        if j == i:
                            continue
                        cj = str(c['usos'][j].get('cable'))
                        costo += sum(1 for b2, q in puntas(cj, (k, j)) if b2 == k and
                                     (round(q['x'], 1), round(q['y'], 1)) != boca)
                    if len(idx) > 2:
                        costo += 1      # con 3 o mas cables en la boca no alcanza con mover uno
                    opciones.append((costo, i, p2))
                opciones.sort(key=lambda q: q[0])
                if not opciones or opciones[0][0] > 0 or (len(opciones) > 1 and opciones[1][0] == 0):
                    continue
                _, i, p2 = opciones[0]
                u = c['usos'][i]
                p2 = dict(p2, confianza='media', bloque=sig)
                p2['como'] = (f"{k} {u.get('borne')} ya tiene otro cable en esa boca (una boca = un conductor) y este cable "
                              f"no puede ir en {k}: se ubica en {sig}, bloque siguiente de la hoja {k[:2]}. " + p2['como'])
                self.resultado[k][i] = p2
                self.avisos.append(f"{k}: '{u.get('texto')}' #{u.get('cable')} comparte boca con otro cable; "
                                   f"se paso a {sig} {u.get('borne')} (revisar la etiqueta en el instructivo)")

    def modulo_por_pareja(self, k, u, usos_k, nom):
        """Modulo de un uso sin numero de modulo ('46KR A2'): el del otro borne de bobina con cable vecino.
        None si no hay pareja: el modulo queda a revisar (antes se tomaba el 1 sin avisar)."""
        c = num_cable(u.get('cable'))
        for _, v in usos_k:
            suf = str(v.get('tag') or '')[len(k):]
            if suf.isdigit() and str(v.get('borne')).upper() in ('A1', 'A2') and abs(num_cable(v.get('cable')) - c) == 1:
                return int(suf)
        return None

    # ------------------------------------------------------------------ eleccion del modelo
    def candidatos(self, k):
        """Modelo de k segun la lista de materiales: (modelo del catalogo o None, tag de la lista de donde salio).
        Si k no figura con un modelo del catalogo, se prueba con los tags de la misma raiz (43KR -> 43KR1)."""
        mats = self.materiales
        if k in mats:
            listado = modelo_por_materiales(mats[k], self.modelos)
            if listado is not None:
                return listado, k
        for tg, tx in mats.items():
            if raiz(tg) == raiz(k) and tg != k:
                listado = modelo_por_materiales(tx, self.modelos)
                if listado:
                    return listado, tg
        return None, None

    @staticmethod
    def texto_lista(texto):
        """el renglon de la lista de materiales en una linea ('Interruptor termomagnetico 2x10A | SCHNEIDER | EZ9F34210'
        -> 'Interruptor termomagnetico 2x10A SCHNEIDER EZ9F34210'; sin las letras sueltas de la grilla de la hoja)"""
        return re.sub(r'\s+', ' ', ' '.join(c.strip() for c in str(texto or '').split('|') if len(c.strip()) > 1)).strip()

    def modelo_lista(self, texto):
        """marca y modelo del renglon de la lista de materiales (desde el campo del fabricante hasta el final):
        '... | Base de fusible ... | ABB | E 91/32' -> 'ABB E 91/32'. Sin fabricante conocido, el renglon entero."""
        campos = [c.strip() for c in str(texto or '').split('|') if len(c.strip()) > 1]
        fabs = {norm(f) for m in self.modelos for f in str(m.get('fabricante') or '').split('/') if len(f.strip()) > 1}
        for i, c in enumerate(campos):
            if FABRICANTES_RE.search(c) or any(f and f in norm(c) for f in fabs):
                return ' '.join(campos[i:])
        return self.texto_lista(texto)

    @staticmethod
    def tipo_corto(m):
        """lo que es el modelo, para los avisos: 'modular DIN (termomagnetica 2 polos)' -> 'termomagnetica 2 polos';
        'barrera de seguridad intrinseca (carcasa angosta...)' -> 'barrera de seguridad intrinseca'"""
        t = str(m.get('tipo') or '').strip()
        mo = re.match(r'^(.*?)\s*\(([^)]*)\)\s*$', t)
        if mo:
            pre, par = mo.group(1).strip(), mo.group(2).strip()
            return par if (not pre or re.match(r'(?i)^modular\b', pre) and len(pre.split()) <= 2) else pre
        return t or m.get('id', '?')

    def familia_de_texto(self, texto):
        """familia (tipo de aparato) de un renglon de la lista de materiales: la del primer patron de 'familias' del
        catalogo que aparece en el renglon (sin el tag): 'Interruptor termico de control AC | ABB | SH 202' ->
        'termomagnetica', 'Modulo de entradas analogicas | MOXA' -> 'modulo_es'. None si no se reconoce."""
        t = ' '.join(c.strip() for c in str(texto or '').split('|'))
        for fam, _, rx in self.familias:
            if rx.search(t):
                return fam
        return None

    def nombre_familia(self, fam):
        return next((n for f, n, _ in self.familias if f == fam), None) or str(fam)

    def familia_de(self, k, c, listado, texto_k):
        """familia del aparato k segun la lista de materiales: la del modelo que nombra (si esta en el catalogo) o la
        de la descripcion de su renglon; un renglon sin familia reconocible de un tag de bornera cuenta como bornera.
        None si k no figura en la lista (o el renglon no dice que es)."""
        if listado is not None and listado.get('familia'):
            return listado['familia']
        if texto_k is None:
            return None
        fam = self.familia_de_texto(texto_k)
        if fam is None and c.get('es_bornera'):
            fam = 'bornera'
        return fam

    def mapear(self):
        """Ubica cada uso. Si un componente falla (dibujo raro, modelo mal cargado), ese componente queda sin punto
        y con un aviso; los demas siguen."""
        comps = self.usos['componentes']
        self.resultado = {}
        self.elegido = {}
        self.estructuras = {}
        pendientes_desborde = []
        for k, c in comps.items():
            if k in self.sin_posicion:                               # sin etiqueta: sus bornes quedan con confianza baja
                self.elegido[k] = dict(id='?')
                self.estructuras[k] = None
                self.resultado[k] = {}
                continue
            try:
                m, est, res, desb = self._elegir_modelo(k, c)
            except Exception as e:                                   # noqa: BLE001
                self.avisos.append(f"{k}: no se pudo ubicar sus bornes ({type(e).__name__}: {e}); quedan sin punto exacto")
                self.elegido[k] = dict(id='?')
                self.estructuras[k] = None
                self.resultado[k] = {}
                continue
            self.elegido[k] = m
            self.estructuras[k] = est
            self.resultado[k] = res
            for i, u in desb:
                pendientes_desborde.append((k, i, u))
        # desborde: borne que no existe en el bloque -> bloque siguiente del mismo riel y de la misma hoja
        for k, i, u in pendientes_desborde:
            try:
                sig = self.vecino_desborde(k)
                if sig is None or self.estructuras.get(sig) is None:
                    continue
                est = self.estructuras[sig]
                u2 = dict(u)
                res, _ = self.resolver(sig, est, [(i, u2)])
                if i in res:
                    p = res[i]
                    p['confianza'] = 'media'
                    p['como'] = f"{k} no tiene borne {u.get('borne')}: se ubica en {sig} (bloque siguiente de la hoja {k[:2]}). " + p['como']
                    self.resultado[k][i] = p
            except Exception as e:                                   # noqa: BLE001
                self.avisos.append(f"{k}: no se pudo revisar el bloque vecino de '{u.get('texto')}' ({type(e).__name__}: {e})")
        try:
            self.resolver_compartidas()
        except Exception as e:                                       # noqa: BLE001
            self.avisos.append(f"no se pudo revisar las bocas compartidas ({type(e).__name__}: {e})")
        return self.salida()

    def _elegir_modelo(self, k, c):
        """prueba los modelos del catalogo en la zona de k y devuelve (modelo, estructura, resultado, desbordes)"""
        usos_k = list(enumerate(c.get('usos', [])))
        listado, de_tag = self.candidatos(k)
        # la lista de materiales nombra a k con un modelo que NO esta en el catalogo: se avisa claro (el taller arma el
        # catalogo con la lista de materiales y necesita saber que modelos faltan)
        texto_k = self.materiales.get(k)
        faltante = texto_k is not None and modelo_por_materiales(texto_k, self.modelos) is None
        # la geometria solo puede elegir un modelo de la MISMA familia (tipo de aparato) que dice la lista de
        # materiales: un modulo de E/S que no esta en el catalogo no se ubica como barrera, ni una termomagnetica como
        # toma corriente (antes sus bornes caian sobre el dibujo de otro aparato)
        familia = self.familia_de(k, c, listado, texto_k)
        if faltante:
            self.faltantes.append(dict(tag=k, modelo=self.modelo_lista(texto_k), texto_de_la_lista=self.texto_lista(texto_k),
                                       familia=self.nombre_familia(familia) if familia else None))
        pruebas = []
        # los modelos de un aparato puntual (rele de seguridad, modulos, toma Phoenix...) tienen 'solo_por_lista': se
        # usan cuando la lista de materiales los nombra, nunca para adivinar por el dibujo otro aparato de su familia
        # (un modulo de E/S que no esta en el catalogo no se ubica con los bornes de otro modulo)
        elegibles = [m for m in self.modelos if not m.get('solo_por_lista')]
        if familia:
            modelos = [m for m in elegibles if m.get('familia') == familia]
            if listado is not None and listado not in modelos:
                modelos = modelos + [listado]
            if not modelos:
                # ningun modelo del catalogo es de esa familia (o solo los que se usan si la lista de materiales los
                # nombra): no se adivina con otro tipo de aparato; sus bornes quedan sin punto (en la etiqueta) con el
                # aviso del modelo faltante
                que = self.modelo_lista(texto_k) if texto_k else k
                solo = [m['id'] for m in self.modelos if m.get('familia') == familia and m.get('solo_por_lista')]
                nada = (f"solo tiene {', '.join(solo)}, que se usa(n) cuando la lista de materiales lo(s) nombra" if solo
                        else 'no tiene ningun modelo de esa familia')
                motivo = (f"{que} ({k}) es {self.nombre_familia(familia)} y el catalogo {nada}; "
                          "sus bornes quedan sin punto exacto (punto aproximado en la etiqueta)")
                self.avisos.append(f"{que} ({k}): no esta en el catalogo y no hay ningun modelo de {self.nombre_familia(familia)}"
                                   + (f" que se pueda elegir por el dibujo ({', '.join(solo)} solo con la lista de materiales)" if solo else '')
                                   + "; sus bornes quedan sin punto (punto aproximado en la etiqueta)")
                for i, u in usos_k:
                    self.sin_resolver[(k, i, u.get('texto'), str(u.get('cable')))] = ('?', motivo)
                return dict(id='?', familia=familia), None, {}, []
        else:
            modelos = elegibles
            if 'es_bornera' in c:
                modelos = [m for m in elegibles if bool(m.get('es_bornera', False)) == bool(c['es_bornera'])] or elegibles
            if listado is not None and listado not in modelos:
                modelos = modelos + [listado]
        for m in modelos:
            try:
                est = self.estructura(k, m)
                res, desb = self.resolver(k, est, usos_k)
            except Exception as e:                                   # noqa: BLE001
                if m is listado:                                     # ese modelo no se pudo probar en este dibujo
                    self.avisos.append(f"{k}: el modelo {m['id']} de la lista de materiales no se pudo probar ({type(e).__name__}: {e})")
                continue
            n = max(1, len(usos_k))
            # los bornes que 'desbordan' (numero mayor que las piezas: van al bloque vecino) solo cuentan si el modelo
            # encontro su dibujo en la zona: un modelo sin ninguna pieza no explica nada (antes una bornera con diodo
            # sin piezas le ganaba a la bornera de la lista de materiales porque desbordaban todos sus bornes)
            score = (len(res) + (0.5 * len(desb) if est['validas'] > 0 else 0.0)) / n + (0.05 if m is listado else 0) + 0.01 * (est['validas'] > 0)
            pruebas.append((score, m, est, res, desb))
        if not pruebas:
            if faltante:
                self.avisos.append(f"{self.modelo_lista(texto_k)} ({k}): no esta en el catalogo; no se pudo ubicar por la "
                                   "geometria: quedo en la etiqueta")
            raise ValueError('ningun modelo del catalogo se pudo probar en su zona')
        # 1) el modelo de la lista de materiales se respeta si su firma aparece en la zona y explica al menos
        #    la mitad de los usos; 2) si no, gana el modelo del catalogo que mejor explica los usos
        #    (desempate por el color del dibujo: borne gris / azul)
        pruebas.sort(key=lambda q: -q[0])
        mejor = pruebas[0]
        for q in pruebas:
            if q[1] is listado and q[2]['validas'] > 0 and q[0] - 0.06 >= 0.5:
                mejor = q
        empatados = [q for q in pruebas if abs(q[0] - mejor[0]) < 1e-6]
        dudosos = {}                   # indice del uso -> modelos empatados que lo ubican en otro lugar
        if len(empatados) > 1 and mejor[1] is not listado:
            # desempate: color del dibujo; despues, el modelo mas chico que explica los usos (menos pines con
            # nombre: entre GS8512 de 10 bornes y GS8536 de 14, si los usos van del 1 al 10, el GS8512)
            def n_pines(q):
                nm = q[1].get('nombres', {})
                return len(nm.get('pines', {})) or len(nm.get('reglas', [])) or 99
            afin = {id(q): self.afinidad_color(q[2]) for q in empatados}
            mejor = max(empatados, key=lambda q: (afin[id(q)], -n_pines(q)))
            # modelos que nada distingue (mismo puntaje, mismo color y mismo tamano: la eleccion es arbitraria) pero
            # que ubican DISTINTO los mismos usos (sin lista de materiales, diferencial y termomagnetica de 2 polos: el
            # mismo dibujo con F y N cruzados): no hay como saber cual es; esos puntos bajan a 'media' para
            # confirmarlos en el visor. (Si el desempate es por el tamano, GS8512 contra GS8536, se respeta.)
            tol = max(0.5, 0.25 * self.mm(mejor[1].get('paso_mm', 6)))
            for q in empatados:
                if q is mejor or abs(afin[id(q)] - afin[id(mejor)]) > 1e-6 or n_pines(q) != n_pines(mejor):
                    continue
                for i, p in mejor[3].items():
                    p2 = q[3].get(i)
                    if p2 is not None and math.hypot(p2['x'] - p['x'], p2['y'] - p['y']) > tol:
                        dudosos.setdefault(i, []).append(q[1])
        score, m, est, res, desb = mejor
        if dudosos:
            otros = []
            for lst in dudosos.values():
                for q in lst:
                    if q not in otros:
                        otros.append(q)
            bornes_d = sorted({str(usos_k[i][1].get('borne') or '?').strip() for i in dudosos}, key=lambda b: (len(b), b))
            nb = '/'.join(bornes_d)
            # interruptores (modelos con 'polos'): 'confirmar polos F/N'
            que = f"polos {nb}" if all(x.get('polos') for x in [m] + otros) else nb
            if faltante:
                razon = 'el modelo de la lista de materiales no esta en el catalogo'
            elif listado is not None:
                razon = f'la lista de materiales dice {listado["id"]} pero su dibujo no coincide'
            else:
                razon = 'sin lista de materiales'
            tipos = ' o '.join(dict.fromkeys(self.tipo_corto(x) for x in [m] + otros))
            ids = ' y '.join(x['id'] for x in [m] + otros)
            nota = f"confirmar {que}: {tipos} ({razon}; el dibujo coincide igual con {ids}, que los ubican distinto)"
            for i in dudosos:
                res[i]['confianza'] = 'media'
                res[i]['como'] = nota + ' | ' + res[i]['como']
            self.avisos.append(f"{k}: {razon} y el dibujo coincide igual con {ids}, que ubican distinto {nb}; "
                               f"se tomo {m['id']}: confirmar {que} en el visor")
        if est['validas'] == 0:
            desb = []                  # sin dibujo del modelo en la zona no hay bloque del que 'desbordar'
        if faltante:
            tl = self.modelo_lista(texto_k)
            if not res and not desb:
                como = 'quedo en la etiqueta (no se pudo ubicar por la geometria)'
            elif listado is not None and m is listado:
                como = f'se tomo el modelo de {de_tag} en la lista ({m["id"]})'
            elif familia:
                como = f'se ubico por la geometria como {m["id"]} (misma familia: {self.nombre_familia(familia)})'
            else:
                # el renglon no dice que tipo de aparato es: el modelo de la geometria puede ser de otra familia, asi
                # que sus puntos quedan 'a confirmar'
                como = f'se ubico por la geometria como {m["id"]} (el renglon no dice que tipo de aparato es: a confirmar)'
                for p in res.values():
                    if p.get('confianza') == 'alta':
                        p['confianza'] = 'media'
                    p['como'] = (f"{tl}: la lista de materiales nombra un modelo que no esta en el catalogo y no dice que tipo de "
                                 f"aparato es; se ubico como {m['id']}: confirmar | " + p['como'])
            self.avisos.append(f"{tl} ({k}): no esta en el catalogo; {como}")
        elif listado is not None and m is not listado:
            self.avisos.append(f"{k}: la lista de materiales dice {listado['id']} pero el dibujo coincide mejor con {m['id']}")
        elif listado is not None and not res and not desb and usos_k:
            self.avisos.append(f"{k}: no se encontro en el dibujo el modelo de la lista de materiales ({m['id']}) ni otro de la "
                               "misma familia; sus bornes quedan sin punto exacto")
        elif listado is None and (res or desb or not usos_k):
            self.avisos.append(f"{k}: no figura en la lista de materiales; por la geometria es {m['id']}")
        elif listado is None:
            self.avisos.append(f"{k}: " + ('su renglon de la lista de materiales no nombra un modelo del catalogo' if texto_k is not None
                                           else 'no figura en la lista de materiales')
                               + ' y no se encontro en el dibujo ningun modelo del catalogo' + (f' de la familia {self.nombre_familia(familia)}' if familia else '')
                               + '; sus bornes quedan sin punto exacto')
        return m, est, res, desb

    def afinidad_color(self, est):
        m = est['modelo']
        cm = m.get('color_dibujo')
        if cm is None or not est.get('bocas'):
            return 0
        caja = est['caja']
        cc = defaultdict(int)
        for t in self.esc_.comp:
            b = t[4]
            if caja[0] <= b[0] and b[2] <= caja[2] and caja[1] <= b[1] and b[3] <= caja[3] and t[3] is not None:
                cc[tuple(round(v, 2) for v in t[3][:3])] += 1
        tot = sum(cc.values()) or 1
        return sum(v for c, v in cc.items() if P.color_parecido(c, cm, 0.12)) / tot

    def vecino_desborde(self, k):
        r = self.riel[k]
        if r is None:
            return None
        t = self.tag[k]
        for d in self.delims[id(r)]:
            if d['x0'] > t['x0'] + 0.5 and d['comp']:
                if d['comp'][:2] == k[:2]:
                    return d['comp']
                return None
        return None

    def cuerpos(self, puntos):
        """cuerpo (x0, y0, x1, y1) de cada aparato ubicado: el que uso su modelo (barreras, toma) o, si no, el contorno
        cerrado mas chico que contiene su etiqueta y alguno de sus puntos (la carcasa de una fuente, de una
        termomagnetica). No cuenta un contorno con la etiqueta de otro aparato adentro (placa, riel) ni uno mas grande
        que 'cuerpo_max_mm'."""
        etiquetas = {k: (t['cx'], t['cy']) for k, t in self.tag.items() if not t.get('sin_posicion')}
        lim = self.mm(self.g.get('cuerpo_max_mm', 250.0))
        out = {}
        for k, est in self.estructuras.items():
            if est is None or k not in etiquetas:
                continue
            propios = [p for p in puntos if p['confianza'] != 'baja' and (p.get('ubicado_en') or p['componente']) == k]
            if not propios:
                continue
            ajena = lambda b: any(j != k and b[0] < x < b[2] and b[1] < y < b[3] for j, (x, y) in etiquetas.items())
            if est.get('cuerpo') is not None:
                b = tuple(est['cuerpo'])
                if not ajena(b):
                    out[k] = b
                continue
            cx, cy = etiquetas[k]
            cand = [b for b in self.esc_.cerrados()
                    if b[0] <= cx <= b[2] and b[1] <= cy <= b[3] and b[2] - b[0] <= lim and b[3] - b[1] <= lim
                    and any(b[0] <= p['x'] <= b[2] and b[1] <= p['y'] <= b[3] for p in propios) and not ajena(b)]
            if cand:
                out[k] = min(cand, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
        return out

    def red_de_seguridad(self, puntos):
        """Red de seguridad: un borne no puede caer sobre OTRO aparato. Baja a 'baja' (sin punto: queda en la etiqueta,
        con aviso) los puntos que caen dentro del cuerpo de otro aparato y los que quedan encima (a menos de
        'distancia_otro_tag_mm') de un punto de otro tag; de dos puntos encimados se descarta el de menor confianza,
        o los dos si tienen la misma (no hay como saber cual es). No cuentan los puntos que el motor paso a propósito
        al bloque vecino (desborde, boca compartida): esos son del bloque donde quedaron."""
        bloque = lambda p: p.get('ubicado_en') or p['componente']
        rango = {'alta': 2, 'media': 1}

        def descartar(p, motivo):
            k = p['componente']
            t = self.tag.get(k) or {}
            p['como'] = f"DESCARTADO: {motivo}; queda en la etiqueta (el modelo lo ubicaba en ({p['x']}, {p['y']})) | {p['como']}"
            p['confianza'] = 'baja'
            if t.get('cx') is not None:
                p.update(x=round(float(t['cx']), 2), y=round(float(t['cy']), 2), r=2.0)
            for c in ('ubicado_en', 'tag_ubicado', 'texto_ubicado'):
                p.pop(c, None)
            avisos.setdefault((k, motivo.split(':')[0]), []).append(p)

        avisos = {}
        cuerpos = self.cuerpos(puntos)
        for p in puntos:
            if p['confianza'] == 'baja':
                continue
            for j, b in cuerpos.items():
                if j in (bloque(p), p['componente']):
                    continue
                if b[0] < p['x'] < b[2] and b[1] < p['y'] < b[3]:
                    descartar(p, f"cae dentro del cuerpo de {j} (otro aparato)")
                    break
        dmin = self.mm(self.g.get('distancia_otro_tag_mm', 1.5))
        vivos = [p for p in puntos if p['confianza'] != 'baja']
        malos = {}
        for i, p in enumerate(vivos):
            for q in vivos[i + 1:]:
                if bloque(p) == bloque(q) or p['componente'] == q['componente']:
                    continue
                if math.hypot(p['x'] - q['x'], p['y'] - q['y']) >= dmin:
                    continue
                rp, rq = rango.get(p['confianza'], 0), rango.get(q['confianza'], 0)
                if rp <= rq:
                    malos.setdefault(id(p), (p, bloque(q)))
                if rq <= rp:
                    malos.setdefault(id(q), (q, bloque(p)))
        for p, j in malos.values():
            descartar(p, f"queda encima de un borne de {j} (otro aparato)")
        for (k, motivo), lst in avisos.items():
            self.avisos.append(f"{k}: {len(lst)} punto(s) descartado(s) porque {motivo} "
                               f"({', '.join(str(q['texto']) + ' #' + ','.join(q['cables']) for q in lst[:6])}"
                               + ('…' if len(lst) > 6 else '') + "); quedan en la etiqueta")

    def salida(self):
        puntos = []
        for k, c in self.usos['componentes'].items():
            m = self.elegido.get(k) or dict(id='?')
            t = self.tag[k]
            for i, u in enumerate(c.get('usos', [])):
                p = (self.resultado.get(k) or {}).get(i)
                base = dict(texto=u.get('texto'), cables=[str(u.get('cable'))] if u.get('cable') else [], componente=k, modelo=m['id'])
                if p is None:
                    sr = self.sin_resolver.get((k, i, u.get('texto'), str(u.get('cable'))))
                    como = (f"{k}: no tiene la posicion de su etiqueta en el topografico; queda sin punto" if t.get('sin_posicion') else
                            sr[1] if sr and sr[0] == m['id'] else
                            f"{m['id']}: no pude resolver '{u.get('borne')}' {lado_de_uso(u) or ''}; queda en la etiqueta")
                    base.update(x=round(float(t['cx']), 2), y=round(float(t['cy']), 2), r=2.0, confianza='baja', como=como)
                else:
                    base.update(x=round(float(p['x']), 2), y=round(float(p['y']), 2), r=round(float(p['r']), 2), confianza=p['confianza'], como=p['como'])
                    if p.get('bloque') and p['bloque'] != k:
                        base['ubicado_en'] = p['bloque']
                    # el punto quedo en otro bloque (bornera vecina) o en otro modulo (comun puenteado, texto sin
                    # numero de modulo): el texto que corresponde a donde quedo, para corregir el instructivo
                    tag_u = str(u.get('tag') or '')
                    nuevo = p['bloque'] if p.get('bloque') and p['bloque'] != k else k
                    if p.get('modulo') is not None:
                        nuevo = f"{nuevo}{p['modulo']}"
                    elif nuevo == k and tag_u.startswith(k):
                        nuevo = tag_u
                    texto = str(u.get('texto') or '')
                    if tag_u and nuevo != tag_u and texto.startswith(tag_u):
                        base['tag_ubicado'] = nuevo
                        base['texto_ubicado'] = nuevo + texto[len(tag_u):]
                puntos.append(base)
        try:
            self.red_de_seguridad(puntos)
        except Exception as e:                                       # noqa: BLE001
            self.avisos.append(f"no se pudo revisar los puntos que caen sobre otro aparato ({type(e).__name__}: {e})")
        # dos cables distintos en la misma boca: puede ser un puente o una derivacion a proposito, pero tambien
        # un error del instructivo (etiqueta del bloque vecino, extremo repetido). Se avisa y se baja a 'media'.
        vistos = defaultdict(list)
        bornes_de = {}
        for k, c in self.usos['componentes'].items():
            for i, u in enumerate(c.get('usos', [])):
                bornes_de[(k, u.get('texto'), str(u.get('cable')))] = norm(u.get('borne') or '')
        for p in puntos:
            if p['confianza'] != 'baja' and p['cables']:
                vistos[(p['componente'], round(p['x'], 1), round(p['y'], 1))].append(p)
        for (k, x, y), lst in vistos.items():
            cables = sorted({c for p in lst for c in p['cables']})
            # bornes distintos que en la vista de frente quedan uno detras del otro (enchufes escalonados de las
            # barreras): el catalogo los declara en 'superpuestos' y no son una boca compartida
            sup = ((self.elegido.get(k) or {}).get('nombres', {}).get('superpuestos') or [])
            bs = {bornes_de.get((k, q['texto'], q['cables'][0] if q['cables'] else 'None'), '') for q in lst}
            if len(bs) == len(lst) and any(bs <= {norm(v) for v in g} for g in sup):
                continue
            if len(cables) > 1:
                self.avisos.append(f"{k}: dos o mas cables en la misma boca ({', '.join(q['texto'] + ' #' + ','.join(q['cables']) for q in lst)}): "
                                   "revisar si es un puente/derivacion o un error del instructivo")
                for p in lst:
                    if p['confianza'] == 'alta':
                        p['confianza'] = 'media'
                    p['como'] += ' | AVISO: la boca la comparten los cables ' + ', '.join(cables)
        return dict(descripcion='Puntos de conexion de los bornes (mapeo automatico: catalogo de modelos + detector geometrico). Coordenadas en puntos PDF, origen abajo a la izquierda; r = radio de la boca en pt.',
                    version=VERSION, pagina_pdf=self.pagina + 1, escala_mm_por_pt=self.esc,
                    modelos={k: m['id'] for k, m in self.elegido.items()},
                    avisos=self.avisos, puntos=puntos, modelos_faltantes=self.faltantes, segundos=round(time.time() - self.t0, 2))


# ============================================================================================ control
def control(pdf, motor, salida, png, ancho_px=2200, escala_max=12.0):
    """Imagen de control: un panel ampliado por riel (y uno por cada aparato fuera del riel), con cada punto
    marcado del tamano de la boca y rotulado 'borne cable'. Verde = alta, naranja = media, rojo = baja."""
    import numpy as np
    import cv2
    import pypdfium2 as pdfium
    col = {'alta': (0, 140, 0), 'media': (0, 120, 235), 'baja': (0, 0, 220)}      # BGR
    # grupos de componentes: por tramo de riel; los que no estan en un riel, cada uno aparte
    grupos = defaultdict(list)
    for k in motor.usos['componentes']:
        r = motor.riel.get(k)
        if r is not None and motor.elegido[k].get('anclaje') != 'libre':
            grupos[('riel', round(r['x0']), round(r['yc']))].append(k)
        else:
            grupos[('libre', k)].append(k)
    pts_por = defaultdict(list)
    for p in salida['puntos']:
        pts_por[p['componente']].append(p)
    orden = sorted(grupos.items(), key=lambda kv: (-max(motor.tag[k]['cy'] for k in kv[1]), min(motor.tag[k]['x0'] for k in kv[1])))
    # un riel muy largo se parte en tramos para que el panel se vea ampliado
    max_pt = ancho_px / 8.0
    partido = []
    for gk, ks in orden:
        ks = sorted(ks, key=lambda k: motor.tag[k]['x0'])
        tramo = []
        for k in ks:
            xs = [p['x'] for p in pts_por[k]] + [motor.tag[k]['x0'], motor.tag[k]['x1']]
            if tramo:
                x_ini = min(min(p['x'] for p in pts_por[q]) if pts_por[q] else motor.tag[q]['x0'] for q in tramo)
                if max(xs) - x_ini > max_pt:
                    partido.append((gk, tramo))
                    tramo = []
            tramo.append(k)
        if tramo:
            partido.append((gk, tramo))
    orden = partido
    doc = pdfium.PdfDocument(pdf)
    pg = doc[motor.pagina]
    W, H = pg.get_size()
    paneles = []
    for gk, ks in orden:
        ks = sorted(ks, key=lambda k: motor.tag[k]['x0'])
        xs, ys = [], []
        for k in ks:
            t = motor.tag[k]
            xs += [t['x0'], t['x1']]
            ys += [t['y0'], t['y1']]
            for p in pts_por[k]:
                xs += [p['x'] - p['r'], p['x'] + p['r']]
                ys += [p['y'] - p['r'], p['y'] + p['r']]
        x0, x1 = min(xs) - 10, max(xs) + 26
        y0, y1 = min(ys) - 10, max(ys) + 10
        esc = min(escala_max, ancho_px / (x1 - x0))
        img = pg.render(scale=esc, crop=(x0, y0, W - x1, H - y1)).to_pil().convert('RGB')
        a = np.asarray(img)[:, :, ::-1].copy()
        a = (255 - (255 - a.astype(np.int16)) * 0.5).astype(np.uint8)

        def X(x):
            return int(round((x - x0) * esc))

        def Y(y):
            return int(round((y1 - y) * esc))
        ocupado = []
        fs = 0.42
        for k in ks:
            est = motor.estructuras.get(k)
            if not est:
                continue
            cj = est['caja']
            cv2.rectangle(a, (X(cj[0]), Y(cj[3])), (X(cj[2]), Y(cj[1])), (255, 170, 120), 1)
            txt = f"{k}: {est['modelo']['id']}"
            (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            tx, ty = max(2, X(cj[0]) + 2), max(th + 3, Y(cj[3]) - 3)
            for o in list(ocupado):
                if tx < o[2] and tx + tw > o[0] and ty - th < o[3] and ty > o[1]:
                    ty = o[3] + th + 3
            cv2.putText(a, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 60, 20), 1, cv2.LINE_AA)
            ocupado.append((tx, ty - th, tx + tw, ty))
        pts = [p for k in ks for p in pts_por[k]]
        for p in pts:
            cx, cy, rr = X(p['x']), Y(p['y']), max(4, int(p['r'] * esc))
            ocupado.append((cx - rr, cy - rr, cx + rr, cy + rr))
        for p in sorted(pts, key=lambda p: (-p['y'], p['x'])):
            c = col.get(p['confianza'], (0, 0, 0))
            cx, cy, rr = X(p['x']), Y(p['y']), max(4, int(p['r'] * esc))
            cv2.circle(a, (cx, cy), rr, c, 2, cv2.LINE_AA)
            cv2.circle(a, (cx, cy), 2, c, -1)
            texto = p['texto'] or ''
            partes = texto.split(' ', 1)
            borne = partes[1] if len(partes) > 1 and partes[0] == p['componente'] else texto
            lab = f"{borne} {','.join(p['cables'])}".strip()
            if p.get('ubicado_en'):
                lab = f"{p['componente']} {lab} -> {p['ubicado_en']}"
            (tw, th), _ = cv2.getTextSize(lab, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)
            d = rr + 3
            cand = [(d, -th // 2), (-d - tw, -th // 2), (-tw // 2, -d - th), (-tw // 2, d), (d, -d - th), (-d - tw, -d - th),
                    (d, d), (-d - tw, d), (d + 14, -th // 2 - 16), (-d - tw - 14, -th // 2 + 16),
                    (-tw // 2, -d - th - 18), (-tw // 2, d + 18), (d + 20, -th // 2 + 22), (-d - tw - 20, -th // 2 - 22)]
            mejor = None
            for dx, dy in cand:
                bx = (cx + dx, cy + dy, cx + dx + tw, cy + dy + th)
                sol = sum(max(0, min(bx[2], o[2]) - max(bx[0], o[0])) * max(0, min(bx[3], o[3]) - max(bx[1], o[1])) for o in ocupado)
                fuera = bx[0] < 0 or bx[1] < 0 or bx[2] > a.shape[1] or bx[3] > a.shape[0]
                sc = sol + (10 ** 6 if fuera else 0)
                if mejor is None or sc < mejor[0]:
                    mejor = (sc, bx)
                if sc == 0:
                    break
            bx = mejor[1]
            ocupado.append(bx)
            mx, my = (bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2
            if math.hypot(mx - cx, my - cy) > rr + tw / 2 + 8:
                cv2.line(a, (cx, cy), (mx, my), c, 1, cv2.LINE_AA)
            cv2.rectangle(a, (bx[0] - 1, bx[1] - 1), (bx[2] + 1, bx[3] + 2), (255, 255, 255), -1)
            cv2.putText(a, lab, (bx[0], bx[3]), cv2.FONT_HERSHEY_SIMPLEX, fs, c, 1, cv2.LINE_AA)
        titulo = ('Riel: ' if gk[0] == 'riel' else 'Fuera del riel: ') + ', '.join(ks)
        barra = np.full((30, a.shape[1], 3), 255, np.uint8)
        cv2.putText(barra, titulo, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        paneles.append(np.vstack([barra, a]))
    doc.close()
    Wmax = max(p.shape[1] for p in paneles)
    ley = np.full((70, Wmax, 3), 255, np.uint8)
    n = {c: sum(1 for p in salida['puntos'] if p['confianza'] == c) for c in col}
    cv2.putText(ley, f"Control P1 catalogo geometrico - {len(salida['puntos'])} puntos (rotulo: borne cable; circulo = tamano de la boca)",
                (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 1, cv2.LINE_AA)
    x = 8
    for nom, c in (('alta: boca detectada', 'alta'), ('media: extrapolado, regla o a revisar', 'media'),
                   ('baja: sin resolver (queda en la etiqueta)', 'baja')):
        s = f"{nom} ({n[c]})"
        cv2.circle(ley, (x + 8, 50), 7, col[c], 2)
        cv2.putText(ley, s, (x + 20, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col[c], 1, cv2.LINE_AA)
        x += 30 + cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0][0]
    cv2.putText(ley, 'celeste: zona de cada etiqueta y modelo elegido', (x + 10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 60, 20), 1, cv2.LINE_AA)
    filas = [ley]
    for p in paneles:
        if p.shape[1] < Wmax:
            p = np.hstack([p, np.full((p.shape[0], Wmax - p.shape[1], 3), 255, np.uint8)])
        filas.append(p)
        filas.append(np.full((12, Wmax, 3), 200, np.uint8))
    cv2.imwrite(png, np.vstack(filas))


# ============================================================================================ main
def main(argv):
    args = [a for a in argv[1:]]
    opts = {}
    pos = []
    i = 0
    while i < len(args):
        if args[i].startswith('--') and i + 1 < len(args):
            opts[args[i][2:]] = args[i + 1]
            i += 2
        else:
            pos.append(args[i])
            i += 1
    if len(pos) < 3:
        print(__doc__)
        return 2
    pdf, usos_path, out = pos[:3]
    usos = json.load(open(usos_path, encoding='utf-8'))
    if opts.get('pagina'):
        usos['pagina_pdf'] = int(opts['pagina'])                 # pagina PDF (1 = la primera)
    if opts.get('escala') == 'auto':
        usos.pop('escala_mm_por_pt', None)                       # se saca del alto del riel DIN (35 mm)
    elif opts.get('escala'):
        usos['escala_mm_por_pt'] = float(opts['escala'])
    catalogo = json.load(open(opts.get('catalogo', os.path.join(AQUI, 'catalogo.json')), encoding='utf-8'))
    mat = opts.get('materiales') or os.path.join(os.path.dirname(os.path.abspath(usos_path)), 'lista_materiales.txt')
    if mat == 'no':
        mat = None                                               # plano sin lista de materiales
    motor = Motor(pdf, usos, catalogo, leer_materiales(mat))
    sal = motor.mapear()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(sal, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    png = opts.get('control', os.path.join(os.path.dirname(os.path.abspath(out)), 'control.png'))
    if png != 'no':
        control(pdf, motor, sal, png)
    n = len(sal['puntos'])
    nb = sum(1 for p in sal['puntos'] if p['confianza'] != 'baja')
    print(f"{n} puntos ({nb} ubicados, {n - nb} sin resolver) en {sal['segundos']} s -> {out}")
    for a in sal['avisos']:
        print('  aviso:', a)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
