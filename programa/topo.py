"""Lectura del plano topografico: donde esta cada componente (bandeja o lateral) y en que orden
(riel por riel de arriba abajo, de izquierda a derecha).

Cada estandar de dibujo llama distinto a las capas y dibuja distinto las cosas; por eso:
- las capas se reconocen por patron (RX_*): 'RIEL DIN' / '_IGV_Riel DIN', 'TABLERO' / '_IGV_Envolvente', ...
- los rieles DIN se leen como TRAMOS DE PERFIL: un rectangulo cerrado (el perfil es el lado corto) o un grupo de
  lineas paralelas de todo el largo (el perfil es el alto del grupo). Los aparatos tapan el riel: a veces solo
  asoma un tramo corto entre dos aparatos, y eso alcanza.
- la medida de referencia del dibujo es el PERFIL DEL RIEL H (riel TS35 = 35 mm): todas las distancias van en
  perfiles, no en puntos fijos (en el 75441, 1:4, H = 24.8 pt; en el 66817, 1:5, H = 19.6 pt).
- la escala mm/pt sale de las cotas contra la placa si coincide con la del riel (+-3 %); si no, del riel mismo
  (35 mm / H llevado a la escala normalizada mas cercana)."""
import re, collections, math
import pypdf
from pdfvec import page_strokes, layer_names
from textdec import Decoder, page_text, bbox, DSU

TAG_TXT = re.compile(r'\d{2}[A-Z][A-Z0-9]{0,7}')

# capas por patron
RX_RIEL = re.compile(r'RIEL|\bDIN\b', re.I)                        # 'RIEL DIN', '_IGV_Riel DIN'
RX_PLACA = re.compile(r'TABLERO|ENVOLVENTE|PLACA|BANDEJA', re.I)   # 'TABLERO', '_IGV_Envolvente'
RX_COTA = re.compile(r'COTA|(?<![A-Z])DIM', re.I)                  # 'COTAS', 'DIM', '_DIMENSIONES'
RX_LATERAL = re.compile(r'LATERAL\s+(IZQ|DER)', re.I)              # titulos 'VISTA LATERAL IZQUIERDA / DERECHA'

RIEL_MM = 35.0                   # riel DIN TS35
PT_MM = 25.4 / 72                # 1 pt en mm a escala 1:1
ESCALAS = (0.2, 0.5, 1, 2, 2.5, 3, 4, 5, 6, 8, 10, 15, 20, 25, 50)   # 1:N normalizadas
CLOSE_OPS = ('f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 's')

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


def rect_of(p, op=None, tol=0.5):
    """bbox si el trazo es un rectangulo cerrado alineado con los ejes ('re', m-l-l-l-h o relleno), si no None"""
    if len(p) == 5 and math.dist(p[0], p[-1]) < tol:
        q = p[:4]
    elif len(p) == 4 and op in CLOSE_OPS:
        q = p
    else:
        return None
    x0, y0, x1, y1 = bbox(q)
    if x1 - x0 < tol or y1 - y0 < tol:
        return None
    corners = {(abs(x - x0) < tol, abs(y - y0) < tol) for x, y in q if (abs(x - x0) < tol or abs(x - x1) < tol) and (abs(y - y0) < tol or abs(y - y1) < tol)}
    return (x0, y0, x1, y1) if len(corners) == 4 else None


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


def rails_of(strokes):
    """(x0, x1, y) de cada borde de los tramos de riel (compatibilidad)"""
    return [(b['x0'], b['x1'], y) for b in rail_bands(strokes) for y in (b['y0'], b['y1'])]


def snap_escala(mm_pt, tol=0.05):
    """mm/pt -> la escala normalizada 1:N mas cercana, si esta a menos del 5 %"""
    n = mm_pt / PT_MM
    k = min(ESCALAS, key=lambda e: abs(e / n - 1))
    return round(k * PT_MM, 4) if abs(k / n - 1) < tol else round(mm_pt, 4)


def layout(pdf_path, known_tags, log=print, dec=None):
    reader = pypdf.PdfReader(pdf_path); names = layer_names(reader)
    dec = dec or Decoder()
    best = None; cotas = []
    for pi in range(len(reader.pages)):
        st = page_strokes(reader, pi, names)
        bands = rail_bands(st)
        if not bands:
            continue
        H = perfil(bands)
        lines = page_text(st, dec, ('WATERMARK',))
        for l in lines:   # cotas (mm) para calcular la escala del dibujo
            if RX_COTA.search(l.get('layer', '')) and re.fullmatch(r'\d{2,4}', l['text'].strip()):
                cotas.append((int(l['text'].strip()), l['ang']))
        if RIEL_MM / H < 0.9 * PT_MM:
            # dibujo AMPLIADO (escala mayor que 1:1): es un detalle (ej. 'Detalle de etiquetado'), no la bandeja
            log(f'Topográfico hoja {pi + 1}: detalle ampliado (perfil del riel {H:.0f} pt), no es la bandeja')
            continue
        hits = []
        for l in lines:
            k = match_tag(l['text'], known_tags)
            if not k and 'ETIQUETA' in l.get('layer', '').upper() and re.search(r'\d', l['text']) and dec.use_ocr:
                k = match_tag(ocr_crop(pdf_path, pi, l['bbox'], l['ang'], dec), known_tags)   # etiqueta chica girada
            if k:
                b = l['bbox']
                hits.append(dict(tag=k, leido=l['text'], x=(b[0] + b[2]) / 2, y=(b[1] + b[3]) / 2))
        log(f'Topográfico hoja {pi + 1}: {len({h["tag"] for h in hits})} componentes reconocidos')
        if best is None or len({h['tag'] for h in hits}) > len({h['tag'] for h in best['hits']}):
            plates = [r for r in (rect_of(p_, o_) for l_, o_, p_ in st if RX_PLACA.search(l_))
                      if r and min(r[2] - r[0], r[3] - r[1]) > PLACA_MIN_H * H]
            titulos = [dict(texto=l['text'].strip(), lado='DERECHO' if RX_LATERAL.search(l['text']).group(1).upper() == 'DER' else 'IZQUIERDO',
                            x=(l['bbox'][0] + l['bbox'][2]) / 2, y=(l['bbox'][1] + l['bbox'][3]) / 2)
                       for l in lines if RX_LATERAL.search(l['text'])]
            best = dict(pag=pi + 1, hits=hits, bands=bands, H=H, size=[float(v) for v in reader.pages[pi].mediabox[2:]],
                        plates=plates, titulos=titulos)
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
    views = []
    for g in groups.values():
        x0 = min(b['x0'] for b in g) - VISTA_MX_H * H; x1 = max(b['x1'] for b in g) + VISTA_MX_H * H
        y0 = min(b['y0'] for b in g) - VISTA_MY_H * H; y1 = max(b['y1'] for b in g) + VISTA_MY_H * H
        # filas: tramos con el mismo eje = un riel (cortado por una canaleta vertical o tapado por los aparatos)
        rows = []
        for b in sorted(g, key=lambda b: -b['eje']):
            if rows and abs(rows[-1]['ejes'][-1] - b['eje']) < FILA_H * H:
                rows[-1]['ejes'].append(b['eje']); rows[-1]['tramos'].append((b['x0'], b['x1']))
            else:
                rows.append(dict(ejes=[b['eje']], tramos=[(b['x0'], b['x1'])]))
        views.append(dict(box=[x0, y0, x1, y1], rails=[round(sum(r['ejes']) / len(r['ejes']), 1) for r in rows],
                          tramos=[r['tramos'] for r in rows]))
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
    for h in best['hits']:
        if h['tag'] in comp and comp[h['tag']]['ubic'] == 'BANDEJA':
            continue
        c = dict(ubic='LI', fila=None, x=round(h['x'], 1), y=round(h['y'], 1), leido=h['leido'])
        if h['vista'] == tray and tray is not None:
            rs = views[tray]['rails']
            fila = min(range(len(rs)), key=lambda i: abs(rs[i] - h['y'])) if rs else 0
            if not rs or largo[fila][0] <= h['x'] <= largo[fila][1]:
                c.update(ubic='BANDEJA', fila=fila + 1)
            else:
                c['nota'] = 'en la vista de la bandeja pero fuera del largo de su riel'
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
        m = PLACA_MX_H * H
        inside = [b for b in best['plates'] if b[0] - m <= (vb[0] + vb[2]) / 2 <= b[2] + m and b[1] - m <= (vb[1] + vb[3]) / 2 <= b[3] + m]
        plate = min(inside, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])) if inside else None
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
    return dict(pag=best['pag'], comp=comp, vistas=[dict(box=v['box'], rails=v['rails']) for v in views], bandeja=tray,
                size=best['size'], region=region, escala=escala, escala_fuente=fuente, perfil_riel_pt=round(H, 2),
                ductos=duct_list, filas=views[tray]['rails'] if tray is not None else [])
