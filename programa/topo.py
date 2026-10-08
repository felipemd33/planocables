"""Lectura del plano topografico: donde esta cada componente (bandeja o lateral) y en que orden
(riel por riel de arriba abajo, de izquierda a derecha).

Cada estandar de dibujo llama distinto a las capas y dibuja distinto las cosas; por eso:
- las capas se reconocen por patron (RX_*): 'RIEL DIN' / '_IGV_Riel DIN', 'TABLERO' / '_IGV_Envolvente', ...
- los rieles DIN se leen como TRAMOS DE PERFIL: un rectangulo cerrado (el perfil es el lado corto) o un grupo de
  lineas paralelas de todo el largo (el perfil es el alto del grupo). Los aparatos tapan el riel: a veces solo
  asoma un tramo corto entre dos aparatos, y eso alcanza. Los tramos dibujados como rectangulo en OTRAS capas se
  reconocen por el perfil (rieles_geometria), y la bandeja son todos los rieles que caen dentro de su placa.
- las etiquetas verticales partidas ('1', '1', 'XP' = 11XP) se unen antes de buscar los componentes (unir_partidas).
- la medida de referencia del dibujo es el PERFIL DEL RIEL H (riel TS35 = 35 mm): todas las distancias van en
  perfiles, no en puntos fijos (en el 75441, 1:4, H = 24.8 pt; en el 66817, 1:5, H = 19.6 pt).
- la escala mm/pt sale de las cotas contra la placa si coincide con la del riel (+-3 %); si no, del riel mismo
  (35 mm / H llevado a la escala normalizada mas cercana)."""
import re, collections, math
import pypdf
from pdfvec import page_strokes, layer_names
from textdec import Decoder, page_text
# (movidos a planocables.base; siguen siendo topo.rect_of, topo.snap_escala, topo.RIEL_MM, topo.RX_LATERAL...)
from planocables.base.geom import bbox, DSU, rect_of, CLOSE_OPS
from planocables.base.escala import RIEL_MM, PT_MM, ESCALAS, snap_escala
from planocables.base.convenciones import LATERAL_RE as RX_LATERAL

TAG_TXT = re.compile(r'\d{2}[A-Z][A-Z0-9]{0,7}')

# Version del LECTOR del topografico (topo.layout y ruteo.ducts; la de las hojas de bandejas de EPLAN esta en
# eplan.VERSION_LECTOR). Se guarda en layout.json ('version_lector') y, si cambia, web.gen_instructivo vuelve a leer el
# topografico de un trabajo existente al regenerar (lo del usuario esta en instructivo.json y se conserva).
# SUBIRLA cada vez que cambie la lectura: rieles, etiquetas, placa, canaletas, escala...
VERSION_LECTOR = '2026.10.08-e8p'     # (2026.10.08: vistas laterales completas para E8: placa, canaletas y titulo;
                                      #  e8p: vista de la PUERTA para E8, lay['puerta'])

# capas por patron
RX_RIEL = re.compile(r'RIEL|\bDIN\b', re.I)                        # 'RIEL DIN', '_IGV_Riel DIN'
RX_PLACA = re.compile(r'TABLERO|ENVOLVENTE|PLACA|BANDEJA', re.I)   # 'TABLERO', '_IGV_Envolvente'
RX_COTA = re.compile(r'COTA|(?<![A-Z])DIM', re.I)                  # 'COTAS', 'DIM', '_DIMENSIONES'
# (RX_LATERAL, titulos 'VISTA LATERAL IZQUIERDA / DERECHA'; RIEL_MM, PT_MM, ESCALAS y CLOSE_OPS: de planocables.base)

# Distancias en perfiles de riel H (antes en pt fijos, medidos en el 75441 con H = 24.8 pt; con ese H dan lo mismo)
GAP_H = 1.21          # lineas de un mismo riel: a menos de 30 pt entre si
VISTA_SOLAPE_H = 1.6  # tramos de riel de una misma vista: se solapan en x con +40 pt
VISTA_MX_H = 2.4      # caja de la vista: +-60 pt en x
VISTA_MY_H = 3.6      #                   +-90 pt en y
FILA_H = 1.2          # tramos con el mismo eje (riel cortado por una canaleta vertical)
APOYO_H = 0.6         # etiqueta apoyada en el riel: |dy| <= 0.6 H
SALTO_H = 2.4         # etiquetas contiguas de un riel (saltos <= 2.4 H) y margen del largo del riel
PLACA_MIN_H = 8.0     # placa: lado minimo > 200 pt
PLACA_MX_H = 3.2      # el centro de la vista cae en la placa (+-80 pt)
PLACA_RIEL_H = 0.25   # un riel es de la placa si cae dentro de ella (+-0.25 perfil)
GEO_TOL = 0.03        # riel dibujado en otra capa: su perfil difiere del de la capa del riel en menos del 3 %
GEO_ESC_TOL = 0.02    # sin capa de riel: el perfil es 35 mm a una escala normalizada (+-2 %)
GEO_LARGO_H = 2.0     # y el tramo mide al menos 2 perfiles de largo
GEO_LARGO_MAX_H = 60  # (sin capa de riel) y a lo sumo 60 perfiles (un riel de 2 m)
GEO_MIN_COMP = 3      # (sin capa de riel) la vista de esos tramos tiene al menos 3 componentes apoyados en ellos
RX_NO_RIEL = re.compile(r'CANAL|DUCTO|SEGURA|INTRINSEC|TABLERO|ENVOLVENTE|PLACA|BANDEJA|COTA|(?<![A-Z])DIM|ROTULO|MARCO', re.I)
PARTIDA_GAP = 1.0     # etiqueta vertical partida: el '1' suelto esta a menos de un alto de letra de la etiqueta
# vistas de las bandejas laterales para la estacion E8 (vistas_e8; claves aparte, no cambian la bandeja):
LAT_PLACA_MIN_H = 5.0     # placa de una lateral: rectangulo cerrado (cualquier capa) con el lado corto > 5 perfiles
LAT_MARGEN_H = 1.0        # sin placa dibujada: union de rieles, canaletas y etiquetas de la vista + 1 perfil
FILA_ETQ_MIN = 3          # riel tapado por los aparatos: fila de 3 o mas etiquetas alineadas en horizontal...
FILA_ETQ_PASO_H = 0.3     # ...separadas en x de 0.3 a SALTO_H perfiles (etiquetas una debajo de otra no son una fila)
TITULO_RENGLON_H = 2.0    # titulo en dos renglones ('VISTA LATERAL DERECHA' / 'INTERIOR'): el de abajo, centrado y a
                          # menos de 2 altos de letra
# vista de la PUERTA para la estacion E8 (puerta_e8; clave aparte lay['puerta'], no cambia la bandeja):
RX_PUERTA = re.compile(r'\bPUERTA\b', re.I)     # titulo de la vista ('PUERTA', 'VISTA POSTERIOR PUERTA'); no 'sobrepuerta'
PUERTA_MIN_H = 5.0        # recuadro de la puerta: rectangulo cerrado (cualquier capa) con el lado corto > 5 perfiles
PUERTA_TITULO_TOL_H = 0.5 # el titulo esta ARRIBA del recuadro (se tolera medio perfil de solape)
CUERPO_LETRA = 3.0        # cuerpo de un aparato de la puerta: rectangulo cerrado que contiene su etiqueta, con el lado
CUERPO_MAX = 0.5          # corto >= 3 altos de letra de la etiqueta y menos de la mitad del recuadro de la puerta


def norm(t):
    return t.upper().replace('0', 'O')


def lev1(a, b):
    """distancia de edicion <= 1"""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def match_tag(text, known):
    """texto leido en el topografico -> referencia del funcional (tolera el '1' inicial perdido, 0/O...)"""
    t = text.strip().replace(' ', '')
    if len(t) < 3 or not re.search(r'[A-Z]', t):
        return None
    nt = norm(t)
    exact = [k for k in known if norm(k) == nt]
    if exact:
        return exact[0]
    suf = [k for k in known if norm(k).endswith(nt) and len(k) - len(t) <= 1 and len(t) >= 3]
    if len(suf) == 1:
        return suf[0]
    near = [k for k in known if len(k) >= 4 and lev1(norm(k), nt)]
    if len(near) == 1:
        return near[0]
    return None


def ocr_crop(pdf_path, pi, bb, ang, dec):
    """lee con OCR una etiqueta pequena renderizandola sola, derecha y grande"""
    try:
        import numpy as np, pypdfium2 as pdfium
        from ocr_raster import PDFIUM_LOCK
        with PDFIUM_LOCK:
            doc = pdfium.PdfDocument(pdf_path)
            try:
                pg = doc[pi]; W, H = pg.get_size(); m = 1.5
                img = pg.render(scale=14, crop=(bb[0] - m, bb[1] - m, W - bb[2] - m, H - bb[3] - m)).to_pil().convert('RGB')
                pg.close()
            finally:
                doc.close()
        if ang == 90:
            img = img.rotate(-90, expand=True)
        elif ang == 270:
            img = img.rotate(90, expand=True)
        r = dec.ocr(np.array(img), use_det=False, use_cls=False, use_rec=True)
        return (r.txts[0] if r.txts else '').replace(' ', '')
    except Exception:
        return ''


def _line_bands(segs, gap):
    """lineas horizontales sueltas de la capa del riel -> grupos (un riel = varias lineas paralelas)"""
    out = []
    d = DSU(len(segs))
    order = sorted(range(len(segs)), key=lambda i: segs[i][2])
    for ii, i in enumerate(order):
        for j in order[ii + 1:]:
            if segs[j][2] - segs[i][2] > gap:
                break
            if segs[i][0] < segs[j][1] and segs[j][0] < segs[i][1]:
                d.u(i, j)
    g = collections.defaultdict(list)
    for i in range(len(segs)):
        g[d.f(i)].append(segs[i])
    for s in g.values():
        y0, y1 = min(t[2] for t in s), max(t[2] for t in s)
        if y1 - y0 <= 2:
            continue
        H = y1 - y0
        # eje: promedio de las lineas de todo el largo (las rectas cortas de las ranuras no cuentan)
        largos = sorted({round(t[2], 1) for t in s if t[1] - t[0] >= 0.75 * H}) or [round((y0 + y1) / 2, 1)]
        out.append(dict(x0=min(t[0] for t in s), x1=max(t[1] for t in s), y0=y0, y1=y1, H=H,
                        eje=sum(largos) / len(largos), forma='lineas'))
    return out


def perfil(bands):
    """perfil H dominante de la hoja: el del tramo de riel mas largo"""
    return max(bands, key=lambda b: b['x1'] - b['x0'])['H'] if bands else None


def _aceptar(bands):
    """tramos del perfil dominante (+-30 %) y de largo >= 0.75 perfil (fuera ranuras, rieles verticales, recuadros)"""
    Hd = perfil(bands)
    return [b for b in bands if 0.7 * Hd <= b['H'] <= 1.3 * Hd and b['x1'] - b['x0'] >= 0.75 * b['H']] if bands else []


def rail_bands(strokes):
    """-> [dict(x0, x1, y0, y1, H, eje, forma)] tramos de riel DIN horizontales de la hoja.
    a) riel dibujado como RECTANGULO cerrado (66817, '_IGV_Riel DIN'): el perfil es el lado corto;
    b) riel dibujado con LINEAS sueltas de todo el largo (75441, 'RIEL DIN': 6 lineas por riel): se agrupan las
       lineas cercanas (a menos de GAP_H perfiles) y el perfil es el alto del grupo."""
    rects, segs = [], []
    for l, o, p, *_ in strokes:
        if not RX_RIEL.search(l) or len(p) < 2:
            continue
        r = rect_of(p, o)
        if r:
            x0, y0, x1, y1 = r
            if x1 - x0 >= y1 - y0 > 2:          # horizontal (los rieles verticales de los laterales no)
                rects.append(dict(x0=x0, x1=x1, y0=y0, y1=y1, H=y1 - y0, eje=(y0 + y1) / 2, forma='rect'))
            continue
        for a, b in zip(p, p[1:]):
            if abs(a[1] - b[1]) < 0.5 and abs(a[0] - b[0]) >= 3:
                segs.append((min(a[0], b[0]), max(a[0], b[0]), (a[1] + b[1]) / 2))
    dentro = lambda s, r: r['x0'] - 0.5 <= s[0] and s[1] <= r['x1'] + 0.5 and r['y0'] - 0.5 <= s[2] <= r['y1'] + 0.5
    # lo que cae dentro de un rectangulo de riel (ranuras, el canal del perfil) no es otro riel
    rects = [r for r in rects if not any(q is not r and q['H'] > r['H'] and q['x0'] - 0.5 <= r['x0'] and r['x1'] <= q['x1'] + 0.5
                                         and q['y0'] - 0.5 <= r['y0'] and r['y1'] <= q['y1'] + 0.5 for q in rects)]
    segs = [s for s in segs if not any(dentro(s, r) for r in rects)]
    if not segs:
        return _aceptar(rects)
    # las lineas se agrupan con un hueco en perfiles, pero el perfil sale de los grupos: se parte de 30 pt
    # (GAP_H con el perfil de 24.8 pt del 75441) y se reagrupa con el perfil medido si da otro hueco
    gap = 30.0
    bands = _aceptar(rects + _line_bands(segs, gap))
    for _ in range(3):
        H = perfil(bands)
        if not H or abs(GAP_H * H / gap - 1) <= 0.1:
            break
        nb = _aceptar(rects + _line_bands(segs, GAP_H * H))
        if not nb:
            break
        gap, bands = GAP_H * H, nb
    return bands


def rieles_geometria(strokes, bands=()):
    """tramos de riel DIN dibujados como RECTANGULO cerrado en CUALQUIER capa (en el 72887 el tramo izquierdo del riel
    1 esta en la capa '01' y los del lateral derecho en '0', no en '_IGV_Riel DIN'), reconocidos por el perfil:
    rectangulo horizontal con el lado corto igual al perfil H de los rieles de la capa del riel (+-3 %) y de largo
    >= 2 perfiles. Si la hoja no tiene capa de riel, el lado corto tiene que ser 35 mm a una escala normalizada
    (+-2 %) y repetirse en dos rectangulos o mas. Quedan afuera las capas de canaletas, placas, cotas y rotulo, lo que
    ya es un tramo de 'bands' y lo que cae dentro de otro rectangulo de riel (ranuras, el canal del perfil)."""
    H = perfil(bands)
    cand = []
    for l, o, p, *_ in strokes:
        if RX_RIEL.search(l) or RX_NO_RIEL.search(l) or len(p) < 4:
            continue
        r = rect_of(p, o)
        if not r:
            continue
        x0, y0, x1, y1 = r
        h = y1 - y0
        if h <= 2 or x1 - x0 < GEO_LARGO_H * h:
            continue
        if H:
            if abs(h / H - 1) > GEO_TOL:
                continue
        else:
            # escala de una bandeja (1:1 a 1:10) y largo de un riel (hasta 2 m = 57 perfiles): una raya de una tabla
            # o del rotulo no es un riel
            n = RIEL_MM / h / PT_MM
            if min(abs(e / n - 1) for e in ESCALAS if 1 <= e <= 10) > GEO_ESC_TOL or x1 - x0 > GEO_LARGO_MAX_H * h:
                continue
        cand.append(dict(x0=x0, x1=x1, y0=y0, y1=y1, H=h, eje=(y0 + y1) / 2, forma='rect'))
    if not H:   # sin capa de riel: el perfil tiene que repetirse (+-1 %)
        cand = [c for c in cand if sum(abs(d['H'] / c['H'] - 1) <= 0.01 for d in cand) >= 2]
    igual = lambda a, b: all(abs(a[k] - b[k]) < 0.5 for k in ('x0', 'x1', 'y0', 'y1'))
    dentro = lambda a, b: (b['x0'] - 0.5 <= a['x0'] and a['x1'] <= b['x1'] + 0.5 and b['y0'] - 0.5 <= a['y0']
                           and a['y1'] <= b['y1'] + 0.5)
    out = []
    for c in cand:
        if any(igual(c, b) or dentro(c, b) for b in list(bands) + out):   # repetido (relleno + borde) o ya leido
            continue
        if any(q is not c and not igual(q, c) and dentro(c, q) for q in cand):
            continue
        out.append(c)
    return out


def etiquetas_hoja(pdf_path, pi, lines, known_tags, dec):
    """etiquetas de componentes de la hoja: [dict(tag, leido, x, y)] (las chicas giradas de la capa de etiquetas se
    leen con OCR si hace falta)"""
    hits = []
    for l in lines:
        k = match_tag(l['text'], known_tags)
        if not k and 'ETIQUETA' in l.get('layer', '').upper() and re.search(r'\d', l['text']) and dec.use_ocr:
            k = match_tag(ocr_crop(pdf_path, pi, l['bbox'], l['ang'], dec), known_tags)   # etiqueta chica girada
        if k:
            b = l['bbox']
            hits.append(dict(tag=k, leido=l['text'], x=(b[0] + b[2]) / 2, y=(b[1] + b[3]) / 2))
    return hits


def geo_con_etiquetas(tramos, hits):
    """(hojas SIN capa de riel) los tramos de rieles_geometria que son rieles de verdad: con etiquetas de componentes
    apoyadas (|dy| <= APOYO_H perfiles, a lo largo del tramo estirado por la cadena de etiquetas, como el largo de los
    rieles de la bandeja) y en una vista (tramos que se solapan en x) que junta al menos GEO_MIN_COMP componentes
    apoyados. Una tabla, un recuadro o una vista con uno o dos aparatos no es una bandeja (en el FCS 75992 la vista
    interior derecha armaba una bandeja falsa con 60DS y 60VN1)."""
    def apoyados(t):
        m = SALTO_H * t['H']
        on = sorted((h['x'], h['tag']) for h in hits if abs(h['y'] - t['eje']) <= APOYO_H * t['H'])
        lo, hi = t['x0'], t['x1']
        for xs in (on, on[::-1]):
            for x, _ in xs:
                if lo - m <= x <= hi + m:
                    lo, hi = min(lo, x), max(hi, x)
        return {tag for x, tag in on if lo - m <= x <= hi + m}
    con = [(t, apoyados(t)) for t in tramos]
    con = [(t, a) for t, a in con if a]
    if not con:
        return []
    d = DSU(len(con))
    for i, (a, _) in enumerate(con):
        for j, (b, _) in enumerate(con[:i]):
            H = max(a['H'], b['H'])
            if a['x0'] < b['x1'] + VISTA_SOLAPE_H * H and b['x0'] < a['x1'] + VISTA_SOLAPE_H * H:
                d.u(i, j)
    vistas = collections.defaultdict(list)
    for i in range(len(con)):
        vistas[d.f(i)].append(con[i])
    return [t for v in vistas.values() if len(set().union(*(a for _, a in v))) >= GEO_MIN_COMP for t, _ in v]


def unir_partidas(lines):
    """une las etiquetas VERTICALES partidas: en el 72887 la etiqueta '11XP' girada 90 grados sale como '1', '1' y
    'XP' (el '1' girado es una raya horizontal y se lee aparte, con angulo 0). Los '1' sueltos que estan justo antes
    del comienzo de la etiqueta (abajo si se lee de abajo hacia arriba, arriba si se lee de arriba hacia abajo),
    alineados con ella y a menos de un alto de letra, se pegan adelante. Devuelve las lineas nuevas."""
    sueltos = [l for l in lines if l['text'].strip() == '1' and l['ang'] == 0]
    usados = set()
    out = []
    for l in lines:
        if id(l) in usados:
            continue
        if l['ang'] not in (90, 270) or not re.search(r'[A-Z]', l['text']) or l['text'].strip() == '1':
            out.append(l)
            continue
        b = list(l['bbox']); w = b[2] - b[0]          # w = alto de letra (la etiqueta esta girada)
        txt = l['text'].strip()
        while w > 0:
            def antes(f):
                fb = f['bbox']
                if id(f) in usados or f.get('layer') != l.get('layer'):
                    return False
                if abs(fb[0] - b[0]) > 0.3 * w or abs(fb[2] - b[2]) > 0.3 * w:
                    return False
                gap = b[1] - fb[3] if l['ang'] == 90 else fb[1] - b[3]
                return -0.1 * w <= gap <= PARTIDA_GAP * w
            f = next((f for f in sueltos if antes(f)), None)
            if f is None:
                break
            usados.add(id(f)); txt = '1' + txt
            fb = f['bbox']
            b = [min(b[0], fb[0]), min(b[1], fb[1]), max(b[2], fb[2]), max(b[3], fb[3])]
        out.append(dict(l, text=txt, bbox=tuple(b)) if txt != l['text'].strip() else l)
    return [l for l in out if id(l) not in usados]


def rails_of(strokes):
    """(x0, x1, y) de cada borde de los tramos de riel (compatibilidad)"""
    return [(b['x0'], b['x1'], y) for b in rail_bands(strokes) for y in (b['y0'], b['y1'])]


def version_lector(de_eplan=False):
    """version del lector que arma el layout: la de topo (AutoCAD) o la de las hojas de bandejas de EPLAN"""
    if de_eplan:
        import eplan
        return f'eplan {getattr(eplan, "VERSION_LECTOR", "?")}'
    return f'topo {VERSION_LECTOR}'


def layout_al_dia(lay):
    """True si el layout (dict, o ruta de layout.json) se leyo con la version actual del lector. Un layout.json viejo
    (sin 'version_lector'), ilegible o de otra version hay que volver a leerlo."""
    if isinstance(lay, str):
        try:
            import json
            with open(lay, encoding='utf-8') as f:
                lay = json.load(f)
        except (OSError, ValueError):
            return False
    if not isinstance(lay, dict):
        return False
    return lay.get('version_lector') == version_lector(bool(lay.get('eplan')))


def layout(pdf_path, known_tags, log=print, dec=None):
    """lee el topografico y devuelve el layout de la bandeja (lo que se guarda en layout.json), con la version del
    lector en 'version_lector'"""
    import eplan
    if eplan.es_eplan(pdf_path):      # PDF de EPLAN: la hoja de bandejas del mismo plano
        lay = eplan.layout(pdf_path, known_tags, log=log)
        if isinstance(lay, dict):
            lay['version_lector'] = version_lector(bool(lay.get('eplan')))
        return lay
    lay = _layout(pdf_path, known_tags, log=log, dec=dec)
    lay['version_lector'] = version_lector(False)
    return lay


def _layout(pdf_path, known_tags, log=print, dec=None):
    reader = pypdf.PdfReader(pdf_path); names = layer_names(reader)
    dec = dec or Decoder()
    best = None; cotas = []
    puertas = []        # (estacion E8) hojas sin rieles con un titulo PUERTA: la vista de la puerta (puerta_e8)
    for pi in range(len(reader.pages)):
        st = page_strokes(reader, pi, names)
        bands = rail_bands(st)
        geo = rieles_geometria(st, bands)                # tramos de riel dibujados en otras capas
        lines = hits = None
        if geo and not bands:
            # hoja SIN capa de riel: los tramos salen solo de la geometria y valen si tienen etiquetas de componentes
            # apoyadas y su vista junta al menos GEO_MIN_COMP componentes; si no, la hoja sigue sin bandeja
            lines = unir_partidas(page_text(st, dec, ('WATERMARK',)))
            hits = etiquetas_hoja(pdf_path, pi, lines, known_tags, dec)
            geo = geo_con_etiquetas(geo, hits)
        bands = bands + geo
        if not bands:
            # (estacion E8) una hoja sin rieles puede ser la de la PUERTA: se buscan los titulos SIN OCR (rapido y sin
            # tocar la memoria de OCR); la hoja elegida se vuelve a leer al final (puerta_e8). No suma cotas ni compite
            # por la hoja de la bandeja. E8 nunca frena el layout de E6.
            try:
                if lines is None:
                    lines = _texto_sin_ocr(st, dec)
                if any(RX_PUERTA.search(l['text']) for l in lines):
                    puertas.append(dict(pi=pi, st=st, lines=lines))
            except Exception:                               # noqa: BLE001
                pass
            continue
        H = perfil(bands)
        if lines is None:
            lines = unir_partidas(page_text(st, dec, ('WATERMARK',)))
        for l in lines:   # cotas (mm) para calcular la escala del dibujo
            if RX_COTA.search(l.get('layer', '')) and re.fullmatch(r'\d{2,4}', l['text'].strip()):
                cotas.append((int(l['text'].strip()), l['ang']))
        if RIEL_MM / H < 0.9 * PT_MM:
            # dibujo AMPLIADO (escala mayor que 1:1): es un detalle (ej. 'Detalle de etiquetado'), no la bandeja
            log(f'Topográfico hoja {pi + 1}: detalle ampliado (perfil del riel {H:.0f} pt), no es la bandeja')
            continue
        if hits is None:
            hits = etiquetas_hoja(pdf_path, pi, lines, known_tags, dec)
        log(f'Topográfico hoja {pi + 1}: {len({h["tag"] for h in hits})} componentes reconocidos')
        if best is None or len({h['tag'] for h in hits}) > len({h['tag'] for h in best['hits']}):
            plates = [r for r in (rect_of(p_, o_) for l_, o_, p_ in st if RX_PLACA.search(l_))
                      if r and min(r[2] - r[0], r[3] - r[1]) > PLACA_MIN_H * H]
            titulos = [dict(texto=l['text'].strip(), lado='DERECHO' if RX_LATERAL.search(l['text']).group(1).upper() == 'DER' else 'IZQUIERDO',
                            x=(l['bbox'][0] + l['bbox'][2]) / 2, y=(l['bbox'][1] + l['bbox'][3]) / 2)
                       for l in lines if RX_LATERAL.search(l['text'])]
            # (para las vistas de E8: rectangulos cerrados grandes de cualquier capa y los renglones de texto)
            rects = [r for r in (rect_of(p_, o_) for l_, o_, p_ in st)
                     if r and min(r[2] - r[0], r[3] - r[1]) > LAT_PLACA_MIN_H * H]
            best = dict(pag=pi + 1, hits=hits, bands=bands, H=H, size=[float(v) for v in reader.pages[pi].mediabox[2:]],
                        plates=plates, titulos=titulos, rects=rects,
                        renglones=[(l['text'].strip(), tuple(l['bbox'])) for l in lines if l['text'].strip()],
                        # (E8: la puerta puede ser una vista de esta misma hoja; puerta_e8)
                        puerta=dict(pi=pi, st=st, lines=lines) if any(RX_PUERTA.search(l['text']) for l in lines) else None)
    dec.save_cache()
    if not best:
        return dict(pag=None, comp={}, vistas=[], filas=[])
    H = best['H']; bands = best['bands']
    # vistas: tramos de riel que se solapan en x (cada vista del gabinete tiene los suyos)
    d = DSU(len(bands))
    for i, a in enumerate(bands):
        for j, b in enumerate(bands[:i]):
            if a['x0'] < b['x1'] + VISTA_SOLAPE_H * H and b['x0'] < a['x1'] + VISTA_SOLAPE_H * H:
                d.u(i, j)
    groups = collections.defaultdict(list)
    for i in range(len(bands)):
        groups[d.f(i)].append(bands[i])
    def vista(g):
        x0 = min(b['x0'] for b in g) - VISTA_MX_H * H; x1 = max(b['x1'] for b in g) + VISTA_MX_H * H
        y0 = min(b['y0'] for b in g) - VISTA_MY_H * H; y1 = max(b['y1'] for b in g) + VISTA_MY_H * H
        # filas: tramos con el mismo eje = un riel (cortado por una canaleta vertical o tapado por los aparatos)
        rows = []
        for b in sorted(g, key=lambda b: -b['eje']):
            if rows and abs(rows[-1]['ejes'][-1] - b['eje']) < FILA_H * H:
                rows[-1]['ejes'].append(b['eje']); rows[-1]['tramos'].append((b['x0'], b['x1']))
            else:
                rows.append(dict(ejes=[b['eje']], tramos=[(b['x0'], b['x1'])]))
        return dict(box=[x0, y0, x1, y1], rails=[round(sum(r['ejes']) / len(r['ejes']), 1) for r in rows],
                    tramos=[r['tramos'] for r in rows], bands=g)
    views = [vista(g) for g in groups.values()]
    def view_of(h):
        for k, v in enumerate(views):
            b = v['box']
            if b[0] <= h['x'] <= b[2] and b[1] <= h['y'] <= b[3]:
                return k
        return None
    for h in best['hits']:
        h['vista'] = view_of(h)
    count = collections.Counter(h['vista'] for h in best['hits'] if h['vista'] is not None)
    tray = count.most_common(1)[0][0] if count else None
    # placa de la bandeja: el recuadro mas chico que contiene el centro de la vista con mas componentes
    plate = None
    if tray is not None:
        vb = views[tray]['box']
        m = PLACA_MX_H * H
        inside = [b for b in best['plates'] if b[0] - m <= (vb[0] + vb[2]) / 2 <= b[2] + m and b[1] - m <= (vb[1] + vb[3]) / 2 <= b[3] + m]
        plate = min(inside, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])) if inside else None
    # la bandeja son TODOS los rieles que caen dentro de su placa, aunque esten lejos en x de los demas (72887: el
    # riel 2 de la zona intrinseca, abajo a la izquierda, separado del riel 1 por la canaleta)
    if plate:
        mr = PLACA_RIEL_H * H
        en_placa = lambda b: (plate[0] - mr <= b['x0'] and b['x1'] <= plate[2] + mr and plate[1] - mr <= b['y0']
                              and b['y1'] <= plate[3] + mr)
        juntar = [k for k, v in enumerate(views) if k != tray and all(en_placa(b) for b in v['bands'])]
        if juntar:
            nueva = vista(views[tray]['bands'] + [b for k in juntar for b in views[k]['bands']])
            views = [nueva] + [v for k, v in enumerate(views) if k != tray and k not in juntar]
            tray = 0
            for h in best['hits']:
                h['vista'] = view_of(h)
    # largo de cada riel de la bandeja: sus tramos visibles estirados por las etiquetas apoyadas en el y contiguas
    # (los aparatos tapan el riel); lo que esta en la vista pero fuera de ese largo (motor, valvula, bateria...) no
    # esta montado en el riel
    largo = []
    if tray is not None:
        for i, e in enumerate(views[tray]['rails']):
            tr = views[tray]['tramos'][i]
            lo, hi = min(t[0] for t in tr), max(t[1] for t in tr)
            on = sorted(h['x'] for h in best['hits'] if h['vista'] == tray and abs(h['y'] - e) <= APOYO_H * H)
            for xs in (on, on[::-1]):
                for x in xs:
                    if lo - SALTO_H * H <= x <= hi + SALTO_H * H:
                        lo, hi = min(lo, x), max(hi, x)
            largo.append((lo - SALTO_H * H, hi + SALTO_H * H))
    comp = {}
    exacta = lambda tag, leido: norm(str(leido or '').replace(' ', '')) == norm(tag.replace(' ', ''))
    for h in best['hits']:
        c = dict(ubic='LI', fila=None, x=round(h['x'], 1), y=round(h['y'], 1), leido=h['leido'])
        if h['vista'] == tray and tray is not None:
            rs = views[tray]['rails']
            fila = min(range(len(rs)), key=lambda i: abs(rs[i] - h['y'])) if rs else 0
            if not rs or largo[fila][0] <= h['x'] <= largo[fila][1]:
                c.update(ubic='BANDEJA', fila=fila + 1)
            else:
                c['nota'] = 'en la vista de la bandeja pero fuera del largo de su riel'
        v = comp.get(h['tag'])
        # dos lecturas del mismo tag en la bandeja: manda la que coincide exacto con el tag (no '43XD阳DIB1' para
        # 43DIB1, un texto mal partido que se le parece)
        if v and v['ubic'] == 'BANDEJA' and not (c['ubic'] == 'BANDEJA' and exacta(h['tag'], h['leido'])
                                                  and not exacta(h['tag'], v.get('leido'))):
            continue
        comp[h['tag']] = c
    # lateral de lo que no esta en la bandeja, por los titulos de las vistas ('VISTA LATERAL DERECHA'): el titulo
    # que esta arriba del componente y mas cerca en x. Sin titulos no se marca (se toma como lateral izquierdo, LI).
    if best['titulos']:
        for c in comp.values():
            if c['ubic'] == 'BANDEJA':
                continue
            ts = [t for t in best['titulos'] if t['y'] > c['y']] or best['titulos']
            t = min(ts, key=lambda t: abs(t['x'] - c['x']))
            vb = views[tray]['box'] if tray is not None else None
            # el titulo lateral solo manda si el componente esta mas cerca de el que de la vista de la bandeja
            if vb and abs(t['x'] - c['x']) > abs((vb[0] + vb[2]) / 2 - c['x']):
                continue
            c['lateral'] = t['lado']
    # recuadro de la bandeja (placa) y escala mm/pt
    region, escala, fuente = None, None, None
    if tray is not None:
        vb = views[tray]['box']
        region = [round(v, 1) for v in (plate if plate else vb)]
        riel = RIEL_MM / H
        # 1) cotas mayores del plano contra la placa (convencion Digito: 740 x 820 de las hojas 7 y 9 del 75441),
        #    solo si coincide con la escala del riel; 2) el riel DIN de 35 mm
        W_mm = max((v for v, a in cotas if a in (0, 180)), default=None); H_mm = max((v for v, a in cotas if a in (90, 270)), default=None)
        if plate and W_mm and H_mm:
            sx, sy = W_mm / (plate[2] - plate[0]), H_mm / (plate[3] - plate[1])
            if abs(sx / sy - 1) < 0.05 and abs((sx + sy) / 2 / riel - 1) <= 0.03:
                escala, fuente = round((sx + sy) / 2, 4), 'cotas'
        if escala is None:
            escala, fuente = snap_escala(riel), 'riel DIN 35 mm'
    from ruteo import ducts
    duct_list = ducts(pdf_path, best['pag'] - 1, region, H) if region else []
    log(f'Topográfico: bandeja en la hoja {best["pag"]}, {len(views[tray]["rails"]) if tray is not None else 0} rieles, '
        f'{len(duct_list)} cablecanales, escala {escala} mm/pt ({fuente})')
    vistas = [dict(box=v['box'], rails=v['rails']) for v in views]
    # bandejas laterales para la estacion E8: DESPUES de clasificar la bandeja y en claves aparte (la bandeja, las cotas,
    # la escala y la hoja no cambian). E8 nunca frena el layout de E6.
    try:
        vistas, n_lat = vistas_e8(pdf_path, best, views, vistas, tray, region, comp, H)
        if n_lat:
            log(f'Topográfico: {n_lat} bandeja(s) lateral(es) para la estación E8')
    except Exception as ex_:                                   # noqa: BLE001
        log(f'Topográfico: no se pudieron leer las bandejas laterales para E8 ({type(ex_).__name__}: {ex_})')
    out = dict(pag=best['pag'], comp=comp, vistas=vistas, bandeja=tray,
               size=best['size'], region=region, escala=escala, escala_fuente=fuente, perfil_riel_pt=round(H, 2),
               ductos=duct_list, filas=views[tray]['rails'] if tray is not None else [])
    # vista de la PUERTA para la estacion E8: en una clave aparte (otra hoja; no suma cotas ni toca la bandeja)
    try:
        pu = puerta_e8(pdf_path, puertas, best, vistas, region, comp, H, known_tags, dec)
        if pu:
            out['puerta'] = pu
            log(f"Topográfico: puerta en la hoja {pu['pag']} ({pu['titulo']}): {len(pu['ductos'])} cablecanales, "
                f"{len(pu['comp'])} aparatos")
        dec.save_cache()
    except Exception as ex_:                                   # noqa: BLE001
        log(f'Topográfico: no se pudo leer la vista de la puerta para E8 ({type(ex_).__name__}: {ex_})')
    return out


# --------------------------------------------------------------------------- bandejas laterales (estacion E8)
def _caja_en(a, b, m=0.0):
    """la caja a cae dentro de la caja b (+-m)"""
    return b[0] - m <= a[0] and a[2] <= b[2] + m and b[1] - m <= a[1] and a[3] <= b[3] + m


def _se_tocan(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _pt_en(x, y, b):
    return b[0] <= x <= b[2] and b[1] <= y <= b[3]


def _titulo_lateral(renglones, caja, usados=()):
    """titulo de la vista lateral que esta ARRIBA de la caja y centrado en ella ('VISTA LATERAL DERECHA', con los
    renglones centrados de abajo: 'INTERIOR'); el mas cercano. -> (texto, indice del renglon) o None"""
    cands = []
    for i, (t, b) in enumerate(renglones):
        if i in usados or not RX_LATERAL.search(t):
            continue
        if caja[0] <= (b[0] + b[2]) / 2 <= caja[2] and b[1] >= caja[3]:
            cands.append((b[1] - caja[3], i))
    if not cands:
        return None
    i = min(cands)[1]
    t, b = renglones[i]
    h, cx, y, partes = b[3] - b[1], (b[0] + b[2]) / 2, b[1], [t]
    for t2, b2 in sorted(renglones, key=lambda r: -r[1][3]):
        if b2[3] <= y and y - b2[3] <= TITULO_RENGLON_H * h and abs((b2[0] + b2[2]) / 2 - cx) <= h and b2[1] >= caja[3]:
            partes.append(t2); y = b2[1]
    return ' '.join(partes), i


def _filas_etiquetas(hits, placa, ductos, rieles, H):
    """riel TAPADO por los aparatos (no queda ningun trazo del perfil): una fila horizontal de FILA_ETQ_MIN o mas
    etiquetas alineadas (|dy| <= APOYO_H perfiles, separadas en x de FILA_ETQ_PASO_H a SALTO_H perfiles) entre una
    canaleta horizontal de la vista arriba y otra abajo, lejos de los rieles dibujados. -> [eje] (la mediana de las y)"""
    en = {}
    for h in sorted(hits, key=lambda h: (h['x'], h['y'])):
        if _pt_en(h['x'], h['y'], placa):
            en.setdefault(h['tag'], h)                         # una lectura por tag
    hs = list(en.values())
    d = DSU(len(hs))
    for i, a in enumerate(hs):
        for j, b in enumerate(hs[:i]):
            if abs(a['y'] - b['y']) <= APOYO_H * H and FILA_ETQ_PASO_H * H <= abs(a['x'] - b['x']) <= SALTO_H * H:
                d.u(i, j)
    grupos = collections.defaultdict(list)
    for i in range(len(hs)):
        grupos[d.f(i)].append(hs[i])
    out = []
    for g in grupos.values():
        if len(g) < FILA_ETQ_MIN or max(h['y'] for h in g) - min(h['y'] for h in g) > 2 * APOYO_H * H:
            continue
        xs = sorted(h['x'] for h in g)
        if any(b - a < FILA_ETQ_PASO_H * H for a, b in zip(xs, xs[1:])):      # dos etiquetas una sobre otra: no es fila
            continue
        ys = sorted(h['y'] for h in g)
        y = ys[len(ys) // 2] if len(ys) % 2 else (ys[len(ys) // 2 - 1] + ys[len(ys) // 2]) / 2
        cruza = lambda dd: dd['h'] and dd['b'][0] < xs[-1] and xs[0] < dd['b'][2]
        if not (any(cruza(dd) and dd['b'][1] >= y for dd in ductos) and any(cruza(dd) and dd['b'][3] <= y for dd in ductos)):
            continue
        if any(abs(y - r) < FILA_H * H for r in list(rieles) + out):
            continue
        out.append(round(y, 1))
    return out


def vistas_e8(pdf_path, best, views, vistas, tray, region, comp, H):
    """Bandejas laterales completas para la estacion E8 (gabinete). Agrega a cada vista que no es la bandeja, en claves
    APARTE (la bandeja, las cotas, la escala y la eleccion de la hoja no cambian; E6 no las lee):
    - 'placa': el rectangulo cerrado mas chico (cualquier capa; en el TPT la placa lateral esta en la capa '0') que
      contiene sus rieles y no toca la bandeja; si no hay, la union de rieles, canaletas y etiquetas + LAT_MARGEN_H;
    - 'ductos': las canaletas de la hoja (ruteo.ducts) que caen en esa placa;
    - 'titulo': el titulo lateral de arriba ('VISTA LATERAL DERECHA INTERIOR'), si lo hay;
    - 'rieles_e8': los rieles de la vista mas los TAPADOS por los aparatos (fila de etiquetas entre canaletas), solo si
      hay alguno tapado (riel solo para E8: la bandeja no lo usa).
    Ademas agrega al final las vistas SIN RIEL: una placa con canaletas o con etiquetas de aparatos que no son de la
    bandeja, con un titulo lateral arriba ('rails': [], 'sin_riel': True; la lateral izquierda del TPT, con el
    cargador y la bateria; las dos laterales del 66817, con riel vertical). Dos vistas de riel en la misma placa: la
    segunda queda con 'en_vista' (el indice de la primera, que se lleva sus rieles).
    -> (vistas nuevas, cuantas laterales)"""
    vistas = [dict(v) for v in vistas]
    if tray is None or not region:
        return vistas, 0
    from ruteo import ducts
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])
    # placas posibles: rectangulos cerrados grandes que no tocan la bandeja (el marco de la hoja la contiene: afuera)
    cands = []
    for r in best.get('rects') or []:
        r = tuple(round(v, 1) for v in r)
        if not _se_tocan(r, region) and r not in cands:
            cands.append(r)
    todas = ducts(pdf_path, best['pag'] - 1, None, H)
    renglones = best.get('renglones') or []
    hits = best.get('hits') or []
    fuera = [h for h in hits if (comp.get(h['tag']) or {}).get('ubic') != 'BANDEJA']   # aparatos que no son de la bandeja
    md = 0.2 * H                                               # (como el recorte de ruteo.ducts)
    usados_t, placas, n_lat = set(), {}, 0
    # la placa es la que junta MAS canaletas y aparatos de afuera de la bandeja (no el cuerpo de un aparato dibujado
    # como rectangulo) y, entre las que juntan lo mismo, la mas chica (no el contorno del gabinete)
    contenido = lambda r: (sum(1 for dd in todas if _caja_en(dd['b'], r, md)) +
                           len({h['tag'] for h in fuera if _pt_en(h['x'], h['y'], r)}))
    mejor = lambda rs: max(rs, key=lambda r: (contenido(r), -area(r)))

    def completar(k, placa, de):
        nonlocal n_lat
        v = vistas[k]
        ds = [dict(dd) for dd in todas if _caja_en(dd['b'], placa, md)]
        v.update(placa=[round(x, 1) for x in placa], ductos=ds)
        if de:
            v['placa_de'] = de
        t = _titulo_lateral(renglones, placa, usados_t)
        if t:
            v['titulo'] = t[0]; usados_t.add(t[1])
        filas = _filas_etiquetas(hits, placa, ds, v['rails'], H)
        if filas:
            v['rieles_e8'] = sorted(list(v['rails']) + filas, reverse=True)
        placas[tuple(v['placa'])] = k
        n_lat += 1

    for k, vw in enumerate(views):
        if k == tray:
            continue
        bs = [(b['x0'], b['y0'], b['x1'], b['y1']) for b in vw['bands']]
        con = [r for r in cands if all(_caja_en(b, r, PLACA_RIEL_H * H) for b in bs)]
        placa, de = (mejor(con), None) if con else (None, 'union')
        if placa is None:
            vb = vistas[k]['box']
            xs = [b[0] for b in bs] + [b[2] for b in bs]; ys = [b[1] for b in bs] + [b[3] for b in bs]
            for dd in todas:
                if _pt_en((dd['b'][0] + dd['b'][2]) / 2, (dd['b'][1] + dd['b'][3]) / 2, vb):
                    xs += [dd['b'][0], dd['b'][2]]; ys += [dd['b'][1], dd['b'][3]]
            for h in hits:
                if _pt_en(h['x'], h['y'], vb) and (comp.get(h['tag']) or {}).get('ubic') != 'BANDEJA':
                    xs.append(h['x']); ys.append(h['y'])
            m = LAT_MARGEN_H * H
            placa = (min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m)
            if _se_tocan(placa, region):                       # (no se mete en la bandeja: queda la caja de antes)
                placa, de = tuple(vb), 'caja'
        placa = tuple(round(x, 1) for x in placa)
        if placa in placas:                                    # otra vista de riel de la misma placa: se juntan
            j = placas[placa]
            vistas[k]['en_vista'] = j
            vistas[j]['rieles_e8'] = sorted(set(vistas[j].get('rieles_e8') or vistas[j]['rails']) | set(vistas[k]['rails']), reverse=True)
            continue
        completar(k, placa, de)
    # vistas SIN riel: una placa con un titulo lateral arriba y canaletas o aparatos que no son de la bandeja
    for i, (t, b) in enumerate(renglones):
        if i in usados_t or not RX_LATERAL.search(t):
            continue
        cx = (b[0] + b[2]) / 2
        libres = [r for r in cands if r[0] <= cx <= r[2] and r[3] <= b[1] and not any(_se_tocan(r, p) for p in placas)
                  and contenido(r)]
        if not libres:
            continue
        placa = mejor(libres)
        vistas.append(dict(box=list(placa), rails=[], sin_riel=True))
        completar(len(vistas) - 1, placa, None)
    return vistas, n_lat


# --------------------------------------------------------------------------- vista de la PUERTA (estacion E8)
def _texto_sin_ocr(st, dec):
    """renglones de una hoja leidos solo con el diccionario de letras (sin OCR: rapido y sin tocar la memoria de OCR)"""
    uso = dec.use_ocr
    dec.use_ocr = False
    try:
        return unir_partidas(page_text(st, dec, ('WATERMARK',)))
    finally:
        dec.use_ocr = uso


def _rects_hoja(st):
    """rectangulos cerrados de la hoja (cualquier capa salvo las de canaletas), sin repetidos: [(x0, y0, x1, y1)]"""
    from ruteo import RX_DUCTO, RX_SEGURA
    out = []
    vistos = set()
    for l, o, p, *_ in st:
        if RX_DUCTO.search(l) or RX_SEGURA.search(l):
            continue
        r = rect_of(p, o)
        if r:
            k = tuple(round(v, 1) for v in r)
            if k not in vistos:
                vistos.add(k); out.append(k)
    return out


def _titulo_desde(lines, t, caja):
    """renglones del titulo de una vista que empieza en el renglon t (el que dice PUERTA) con los renglones centrados de
    abajo ('PUERTA' / 'DETALLE DE RIELES Y DUCTOS'), todos arriba de la caja -> [renglon]"""
    b = t['bbox']
    h, cx, y, partes = b[3] - b[1], (b[0] + b[2]) / 2, b[1], [t]
    for l in sorted(lines, key=lambda l: -l['bbox'][3]):
        b2 = l['bbox']
        if l is t or not l['text'].strip():
            continue
        if b2[3] <= y and y - b2[3] <= TITULO_RENGLON_H * h and abs((b2[0] + b2[2]) / 2 - cx) <= h and b2[1] >= caja[3] - 0.5:
            partes.append(l); y = b2[1]
    return partes


def _completar(texto, leido):
    """texto leido con el diccionario con letras sin reconocer ('?') completado con el OCR del renglon (que viene sin
    espacios), si coinciden en todo lo demas: 'DETALLE DE RIELES ? DUCTOS' + 'DETALLEDERIELESYDUCTOS' -> '... Y DUCTOS'"""
    ns = texto.replace(' ', '')
    if '?' not in ns or len(leido) != len(ns) or any(a != '?' and a.upper() != b.upper() for a, b in zip(ns, leido)):
        return texto
    it = iter(leido)
    return ''.join(ch if ch == ' ' else (next(it) if ch == '?' else (next(it), ch)[1]) for ch in texto)


def _cuerpo(rects, et, caja, otras):
    """cuerpo de un aparato de la puerta: el rectangulo cerrado mas chico que contiene el centro de su etiqueta (et =
    caja del texto), con el lado corto de al menos CUERPO_LETRA altos de letra (no el fondo de la etiqueta), menos de
    CUERPO_MAX del recuadro de la puerta y sin otra etiqueta de la puerta adentro. None si no hay (el aparato esta
    dibujado sin contorno cerrado: el cable llega a la etiqueta)"""
    cx, cy = (et[0] + et[2]) / 2, (et[1] + et[3]) / 2
    hl = max(0.5, min(et[2] - et[0], et[3] - et[1]))
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])
    cs = [r for r in rects if _pt_en(cx, cy, r) and min(r[2] - r[0], r[3] - r[1]) >= CUERPO_LETRA * hl
          and area(r) <= CUERPO_MAX * area(caja) and _caja_en(r, caja, 0.5)
          and not any(_pt_en(x, y, r) for x, y in otras)]
    return list(min(cs, key=area)) if cs else None


def puerta_e8(pdf_path, cands, best, vistas, region, comp, H, known_tags, dec):
    """Vista de la PUERTA para la estacion E8 (gabinete), en una clave APARTE del layout (la bandeja, las cotas, la
    escala y la eleccion de la hoja no cambian; E6 no la lee). Es una hoja sin rieles (cands: las que tienen un titulo
    PUERTA, leidas sin OCR) o una vista de la hoja de la bandeja con un titulo PUERTA arriba (que no toca la bandeja ni las
    laterales), con un recuadro (rectangulo cerrado de cualquier capa, el lado corto > PUERTA_MIN_H perfiles) debajo del
    titulo que tiene canaletas o etiquetas de aparatos del funcional. La vista exterior de la puerta (sin canaletas ni
    etiquetas) y el indice de hojas ('PUERTA INTERIOR' en una tabla) no cuentan. Si hay varias, la que junta mas
    canaletas y aparatos. En la hoja elegida, solo las etiquetas de la capa de etiquetas que no se leyeron enteras
    ('???????' = '21PCB01') y los renglones del titulo con letras sin leer se leen con OCR (recortados, como las
    etiquetas chicas de la bandeja): la hoja entera no se vuelve a leer con OCR.
    -> {pag, box, titulo, ductos, rieles, comp: {tag: {x, y, leido, etiqueta, cuerpo}}} o None"""
    from ruteo import ducts, RX_DUCTO, RX_SEGURA
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])
    md = 0.2 * H
    opciones = []           # (contenido, -separacion, -pagina, datos)

    def evaluar(pi, st, lines, ds, hits, excluir=()):
        rects = _rects_hoja(st)
        grandes = [r for r in rects if min(r[2] - r[0], r[3] - r[1]) > PUERTA_MIN_H * H and not any(_se_tocan(r, e) for e in excluir)]
        for t in lines:
            if not RX_PUERTA.search(t['text']):
                continue
            tb = t['bbox']; tcx = (tb[0] + tb[2]) / 2
            for r in grandes:
                if not (r[0] <= tcx <= r[2] and tb[1] >= r[3] - PUERTA_TITULO_TOL_H * H):
                    continue
                n = (sum(1 for dd in ds if _caja_en(dd['b'], r, md)) + len({h['tag'] for h in hits if _pt_en(h['x'], h['y'], r)}))
                if n:
                    opciones.append(((n, -(tb[1] - r[3]), -area(r), -pi), dict(pi=pi, st=st, lines=lines, caja=r, titulo=t, ds=ds)))

    for c in cands:
        st, lines = c['st'], c['lines']
        if not any(RX_DUCTO.search(l) or RX_SEGURA.search(l) for l, *_ in st) and not any(re.search(r'\d', l['text']) for l in lines):
            continue
        ds = ducts(pdf_path, c['pi'], None, H) if any(RX_DUCTO.search(l) or RX_SEGURA.search(l) for l, *_ in st) else []
        uso = dec.use_ocr; dec.use_ocr = False
        try:
            hits = etiquetas_hoja(pdf_path, c['pi'], lines, known_tags, dec)
        finally:
            dec.use_ocr = uso
        evaluar(c['pi'], st, lines, ds, hits)
    # una vista de la hoja de la bandeja: afuera de la bandeja y de las laterales; aparatos que no son de la bandeja
    bp = best.get('puerta')
    if bp:
        excl = [region] + [v['placa'] for v in vistas if v.get('placa')]
        ds = ducts(pdf_path, bp['pi'], None, H)
        fuera = [h for h in best.get('hits') or [] if (comp.get(h['tag']) or {}).get('ubic') != 'BANDEJA']
        evaluar(bp['pi'], bp['st'], bp['lines'], [dd for dd in ds if not any(_se_tocan(dd['b'], e) for e in excl)], fuera, excl)
    if not opciones:
        return None
    _, el = max(opciones, key=lambda o: o[0])
    pi, st, caja, t = el['pi'], el['st'], el['caja'], el['titulo']
    lines = el['lines']
    # etiquetas de la puerta: las leidas con el diccionario y, con OCR del recorte, las de la capa de etiquetas que
    # quedaron con letras sin leer (sin digitos, etiquetas_hoja no las intenta)
    hits = []
    for l in lines:
        b = l['bbox']
        if not _pt_en((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, caja):
            continue
        k = match_tag(l['text'], known_tags)
        if not k and 'ETIQUETA' in l.get('layer', '').upper() and (re.search(r'\d', l['text']) or '?' in l['text']) and dec.use_ocr:
            k = match_tag(ocr_crop(pdf_path, pi, l['bbox'], l['ang'], dec), known_tags)
        if k:
            hits.append(dict(tag=k, leido=l['text'] if match_tag(l['text'], known_tags) else k, x=(b[0] + b[2]) / 2, y=(b[1] + b[3]) / 2,
                             bbox=tuple(b)))
    # titulo: los renglones con letras sin leer, completados con el OCR del recorte
    partes = []
    for l in _titulo_desde(lines, t, caja):
        txt = l['text'].strip()
        if '?' in txt and dec.use_ocr:
            txt = _completar(txt, ocr_crop(pdf_path, pi, l['bbox'], l['ang'], dec))
        partes.append(txt)
    rects = _rects_hoja(st)
    cpu = {}
    for h in sorted(hits, key=lambda h: (h['tag'], h['x'], h['y'])):
        if h['tag'] in cpu:
            continue
        et = h['bbox']                                   # (la caja del texto de la etiqueta: para el cuerpo del aparato)
        otras = [(o['x'], o['y']) for o in hits if o['tag'] != h['tag']]
        cpu[h['tag']] = dict(x=round(h['x'], 1), y=round(h['y'], 1), leido=h['leido'], etiqueta=[round(v, 1) for v in et],
                             cuerpo=_cuerpo(rects, et, caja, otras))
    rieles = sorted({round(b['eje'], 1) for b in (best['bands'] if bp and pi == bp['pi'] else [])
                     if _caja_en((b['x0'], b['y0'], b['x1'], b['y1']), caja, PLACA_RIEL_H * H)}, reverse=True)
    # (las canaletas de la hoja ya leidas, las del recuadro: como ruteo.ducts con la caja, +-0.2 perfil)
    return dict(pag=pi + 1, box=[round(v, 1) for v in caja], titulo=' '.join(partes),
                ductos=[dict(dd) for dd in el['ds'] if _caja_en(dd['b'], caja, md)], rieles=rieles, comp=cpu)
