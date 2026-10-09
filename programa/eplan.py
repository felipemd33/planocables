"""Planos de EPLAN: un solo PDF con texto real (no trazos SHX), con la lista de conexiones y la hoja de bandejas.

EPLAN exporta en el mismo PDF lo que en AutoCAD viene en dos planos:
  - el esquema (las hojas del funcional) con los numeros de cable como texto;
  - la LISTA DE CONEXIONES (hojas 'Lista de conexiones': numero, destino 1, destino 2, color, seccion). Cada renglon es un
    tramo real de cable entre dos puntos de conexion EPLAN ('-11PS1:TB2:1' = aparato 11PS1, borne TB2, punto 1). Un numero
    en varios renglones que comparten un punto es un cable de 3 o mas puntas (puente en ese borne);
  - la hoja de BANDEJAS (vista frontal de las placas con rieles DIN, canaletas y la etiqueta '-TAG' de cada aparato).

Este modulo da la MISMA interfaz que core.process (listado de cables, Excel, visor) y que topo.layout (topografico), y
ademas los conductores ya armados desde la lista de conexiones (res.conductores, que instructivo.conductors devuelve tal
cual). Todo se lee del PDF: nada de coordenadas ni tags de un plano en el codigo. Lo que el PDF no dice (el punto exacto de
cada borne, el texto del taller, la zona hidraulica) sale del MAPEO VERIFICADO del producto, guardado como dato en
programa/mapeos_verificados/<documento>_rev<revision>.json (se elige por el numero de documento y la revision del rotulo).
Sin mapeo verificado el instructivo sale igual, con el punto aproximado y un aviso.

El PDF de EPLAN suele venir protegido (AES): pypdfium2 lo lee directo; para los trazos (pypdf / pdfvec) se usa una COPIA
DE PROCESO sin la proteccion, en la carpeta temporal (el original no se toca)."""
import os, re, math, json, time, collections, threading, hashlib, tempfile, ctypes

AQUI = os.path.dirname(os.path.abspath(__file__))
MAPEOS = os.path.join(AQUI, 'mapeos_verificados')

try:
    from ocr_raster import PDFIUM_LOCK          # pdfium no admite uso simultaneo desde varios hilos
except Exception:                                # pragma: no cover
    PDFIUM_LOCK = threading.Lock()

# designacion de un punto de conexion EPLAN: [=funcion][+ubicacion]-aparato[:borne[:punto]]
DESIG_RE = re.compile(r'^(?:=[^+\-\s:]*)?(?:\+[^\-\s:]+)?-[^\s:]+(?::\S*)?$')
DESIG_PARTES = re.compile(r'^(?:=(?P<fun>[^+\-\s:]*))?(?:\+(?P<ubic>[^\-\s:]+))?-(?P<tag>[^\s:]+)(?::(?P<pines>\S*))?$')
NUM_RE = re.compile(r'^\d{3,5}[A-Z]?$')                 # numero de cable (conexion)
SEC_RE = re.compile(r'^\d{1,3}(?:[.,]\d+)?$')           # seccion en mm2: 0,32 / 2,5 / 35
SEC_MM_RE = re.compile(r'^(\d{1,3}(?:[.,]\d+)?)\s*mm(?:²|2)?$', re.I)
TERMINAL_RE = re.compile(r'^(\d{2})?X')                 # borneras: 13X24V, 61XDO, XPE, X1 (como instructivo.is_terminal_block)
LATERAL_RE = re.compile(r'LATERAL\s+(IZQ|DER)', re.I)
LISTA_RE = re.compile(r'(?i)lista\s+de\s+conexiones|connection\s+list|verbindungsliste|conexiones')
CAB_DOC = re.compile(r'(?i)^(doc\.?|documento:?|document:?)$')
VERSION = 1
# version del lector de la hoja de bandejas (layout): se guarda en layout.json y, si cambia, web.gen_instructivo vuelve
# a leer el topografico de los trabajos existentes (ver topo.VERSION_LECTOR). SUBIRLA cuando cambie layout().
VERSION_LECTOR = '2026.10.06-e8-bateria'    # estaciones_tag del mapeo: bateria y solenoides en E8 (regla del taller)

_CACHE = collections.OrderedDict()          # firma del PDF -> textos de las hojas
_COPIAS = {}                                 # firma -> copia de proceso sin proteccion


# ------------------------------------------------------------------ utilidades
def _firma(pdf):
    try:
        st = os.stat(pdf)
        return (os.path.abspath(pdf), st.st_size, int(st.st_mtime))
    except OSError:
        return (os.path.abspath(pdf), None, None)


_HASH = {}


def _contenido(pdf):
    """firma por CONTENIDO (el mismo PDF copiado como topografico.pdf de un trabajo da la misma): sha1 del archivo"""
    k = _firma(pdf)
    if k not in _HASH:
        h = hashlib.sha1()
        with open(pdf, 'rb') as f:
            for blk in iter(lambda: f.read(1 << 20), b''):
                h.update(blk)
        _HASH[k] = h.hexdigest()
    return _HASH[k]


def natk(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', str(s or ''))]


def _bb_union(bs):
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


def _centro(bb):
    return ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)


def _dentro(p, b, m=0.0):
    return b[0] - m <= p[0] <= b[2] + m and b[1] - m <= p[1] <= b[3] + m


COLOR_ALIAS = {'verde/amarillo': 'Verde-Amarillo', 'verde-amarillo': 'Verde-Amarillo', 'verdeamarillo': 'Verde-Amarillo',
               'amarillo/verde': 'Verde-Amarillo', 'gn/ye': 'Verde-Amarillo', 'green/yellow': 'Verde-Amarillo',
               'apantallamiento': 'Malla', 'pantalla': 'Malla', 'malla': 'Malla', 'shield': 'Malla'}


def norm_color(c):
    """color de la lista de conexiones -> nombre del programa ('AZUL' -> 'Azul', 'Verde/amarillo' -> 'Verde-Amarillo')"""
    if not c:
        return ''
    k = c.strip().lower()
    if k in COLOR_ALIAS:
        return COLOR_ALIAS[k]
    from wires import norm_color as nc
    return nc(c)


def es_malla(c):
    return bool(c) and c.strip().lower() in ('apantallamiento', 'pantalla', 'malla', 'shield')


def partes(d):
    """'-11PS1:TB2:1' -> dict(tag='11PS1', pines=['TB2', '1'], ubic=''); '+Campo-ROTORK:27' -> ubic 'Campo'"""
    m = DESIG_PARTES.match(d or '')
    if not m:
        return dict(tag=(d or '').lstrip('-'), pines=[], ubic='', fun='')
    pines = [p for p in (m.group('pines') or '').split(':') if p != ''] if m.group('pines') is not None else []
    return dict(tag=m.group('tag'), pines=pines, ubic=m.group('ubic') or '', fun=m.group('fun') or '')


# ------------------------------------------------------------------ textos (pdfium)
def _chars(tp):
    from pypdfium2 import raw
    n = tp.count_chars()
    l, r, b, t = ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double()
    ox, oy = ctypes.c_double(), ctypes.c_double()
    out = []
    for k in range(n):
        u = raw.FPDFText_GetUnicode(tp.raw, k)
        if not u:
            out.append(None); continue
        ch = chr(u)
        if ch.isspace() or u in (0xFFFE, 0xFFFF):
            out.append(None); continue
        raw.FPDFText_GetCharBox(tp.raw, k, ctypes.byref(l), ctypes.byref(r), ctypes.byref(b), ctypes.byref(t))
        raw.FPDFText_GetCharOrigin(tp.raw, k, ctypes.byref(ox), ctypes.byref(oy))
        a = raw.FPDFText_GetCharAngle(tp.raw, k)
        fs = raw.FPDFText_GetFontSize(tp.raw, k) or 1.0
        out.append((ch, l.value, b.value, r.value, t.value, ox.value, oy.value, a if a >= 0 else 0.0, fs))
    return out


def _dir(a):
    """sentido de lectura (dx, dy) y normal (para medir la linea base) de un angulo de pdfium (radianes)"""
    return (math.cos(a), -math.sin(a)), (math.sin(a), math.cos(a))


def _ang_deg(a):
    """angulo de lectura en grados 0 / 90 / 180 / 270 como textdec (90 = se lee de abajo hacia arriba)"""
    d = round(math.degrees(a) / 90) % 4
    return {0: 0, 1: 270, 2: 180, 3: 90}[d]


def _palabras(chars):
    """caracteres -> palabras (texto, bbox, angulo). Corta en los espacios, en un cambio de angulo o de renglon y en un
    salto de posicion. Un '-' suelto pegado a la palabra que sigue (las etiquetas '-11PS1' de EPLAN salen asi) se une."""
    words, cur = [], []

    def flush():
        if cur:
            words.append(cur[:])
            cur.clear()
    for c in chars:
        if c is None:
            flush(); continue
        if cur:
            p = cur[-1]
            d, nrm = _dir(p[7])
            dx, dy = c[5] - p[5], c[6] - p[6]
            along, across = dx * d[0] + dy * d[1], dx * nrm[0] + dy * nrm[1]
            ext = max((q[0] - p[5]) * d[0] + (q[1] - p[6]) * d[1] for q in ((p[1], p[2]), (p[3], p[2]), (p[1], p[4]), (p[3], p[4])))
            fs = max(p[8], c[8])
            tol = 0.6 if p[0] == '-' and len(cur) == 1 else 0.35
            if abs(c[7] - p[7]) > 0.1 or abs(across) > tol * fs or along < -0.2 * fs or along - ext > 0.45 * fs:
                flush()
        cur.append(c)
    flush()
    out = []
    for cs in words:
        bb = _bb_union([(c[1], c[2], c[3], c[4]) for c in cs])
        out.append(dict(text=''.join(c[0] for c in cs), bbox=bb, ang=_ang_deg(cs[0][7]), a=cs[0][7], fs=cs[0][8],
                        o=(cs[0][5], cs[0][6])))
    # '-' suelto + palabra siguiente
    res, i = [], 0
    while i < len(out):
        w = out[i]
        if w['text'] == '-' and i + 1 < len(out):
            v = out[i + 1]
            d, nrm = _dir(w['a'])
            cw, cv = _centro(w['bbox']), _centro(v['bbox'])
            dx, dy = cv[0] - cw[0], cv[1] - cw[1]
            across = abs(dx * nrm[0] + dy * nrm[1])
            gap = min(abs((q[0] - cw[0]) * d[0] + (q[1] - cw[1]) * d[1]) for q in ((v['bbox'][0], v['bbox'][1]), (v['bbox'][2], v['bbox'][3])))
            if abs(v['a'] - w['a']) < 0.1 and across < 0.6 * v['fs'] and gap < 1.2 * v['fs'] and not v['text'].startswith('-'):
                res.append(dict(v, text='-' + v['text'], bbox=_bb_union([w['bbox'], v['bbox']])))
                i += 2
                continue
        res.append(w); i += 1
    return res


def _renglones(words):
    """palabras -> renglones (frases): mismo angulo, misma linea base y pegadas (hueco < 0.8 del alto de letra)"""
    out = []
    por_ang = collections.defaultdict(list)
    for w in words:
        por_ang[w['ang']].append(w)
    for ang, ws in por_ang.items():
        d, nrm = _dir(ws[0]['a'])
        along = lambda q: q[0] * d[0] + q[1] * d[1]
        info = []
        for w in ws:
            b = w['bbox']
            ext = [along(q) for q in ((b[0], b[1]), (b[2], b[3]), (b[0], b[3]), (b[2], b[1]))]
            info.append((w['o'][0] * nrm[0] + w['o'][1] * nrm[1], min(ext), max(ext), w))
        info.sort(key=lambda t: t[0])
        bases, cur = [], []
        for t in info:                                  # misma linea base (en cadena)
            if cur and t[0] - cur[-1][0] > 0.35 * max(t[3]['fs'], cur[-1][3]['fs']):
                bases.append(cur); cur = []
            cur.append(t)
        if cur:
            bases.append(cur)
        for bs in bases:
            bs.sort(key=lambda t: t[1])
            grupo = [bs[0]]
            for t in bs[1:] + [None]:
                if t is not None and -0.2 * t[3]['fs'] < t[1] - max(g[2] for g in grupo) < 0.8 * t[3]['fs']:
                    grupo.append(t); continue
                gw = [g[3] for g in grupo]
                out.append(dict(text=' '.join(g['text'] for g in gw), bbox=_bb_union([g['bbox'] for g in gw]), ang=ang, H=gw[0]['fs'] * 0.72, layer=''))
                if t is not None:
                    grupo = [t]
    return out


def leer(pdf):
    """textos de todas las hojas (cache por archivo): [dict(index, w, h, x0, y0, words, lines)]"""
    key = _contenido(pdf)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    import pypdfium2 as pdfium
    pages = []
    with PDFIUM_LOCK:
        doc = pdfium.PdfDocument(pdf)
        try:
            for i in range(len(doc)):
                pg = doc[i]
                try:
                    mb = pg.get_mediabox()
                    tp = pg.get_textpage()
                    try:
                        chars = _chars(tp)
                    finally:
                        tp.close()
                finally:
                    pg.close()
                pages.append(dict(index=i + 1, x0=float(mb[0]), y0=float(mb[1]), w=float(mb[2]), h=float(mb[3]), chars=chars))
        finally:
            doc.close()
    for p in pages:
        p['words'] = _palabras(p.pop('chars'))
        p['lines'] = _renglones(p['words'])
    _CACHE[key] = pages
    while len(_CACHE) > 4:
        _CACHE.popitem(last=False)
    return pages


def copia_proceso(pdf):
    """ruta de un PDF que pypdf puede leer: el mismo si no esta protegido, si no una copia sin la proteccion en la carpeta
    temporal (pypdfium2 save con FPDF_REMOVE_SECURITY). El original nunca se modifica."""
    key = _contenido(pdf)
    if key in _COPIAS and os.path.exists(_COPIAS[key]):
        return _COPIAS[key]
    try:
        import pypdf
        if not pypdf.PdfReader(pdf).is_encrypted:
            _COPIAS[key] = pdf
            return pdf
    except Exception:
        pass
    import pypdfium2 as pdfium
    from pypdfium2 import raw
    d = os.path.join(tempfile.gettempdir(), 'planocables_eplan')
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, key[:16] + '.pdf')
    for fn in os.listdir(d):            # las copias viejas (mas de una semana) se borran
        try:
            fp = os.path.join(d, fn)
            if fp != out and time.time() - os.path.getmtime(fp) > 7 * 86400:
                os.remove(fp)
        except OSError:
            pass
    if not os.path.exists(out):
        with PDFIUM_LOCK:
            doc = pdfium.PdfDocument(pdf)
            try:
                with open(out + '.tmp', 'wb') as f:
                    doc.save(f, flags=raw.FPDF_REMOVE_SECURITY)
            finally:
                doc.close()
        os.replace(out + '.tmp', out)
    _COPIAS[key] = out
    return out


# ------------------------------------------------------------------ deteccion y rotulo
_ES = {}


# etiqueta de aparato EPLAN en texto real: '-11PS1', '-13X24V:2:1', '+Campo-ROTORK:27' (con letra y numero: '-V' o '-10'
# sueltos no cuentan). Los PDF de AutoCAD / ZWCAD no traen texto real y el PDF buscable del programa trae pocas.
TAG_TXT_RE = re.compile(r'^(?:=[^+\-\s:]*)?(?:\+[^\-\s:]+)?-(?=[\w\-]*\d)(?=[\w\-]*[A-Z])[A-Z0-9][\w\-]*(?::\S*)?$')


def deteccion(pdf):
    """dict(eplan, lista): eplan = el PDF es un plano de EPLAN (texto real con muchas designaciones '-TAG' / '-TAG:borne':
    una hoja con 15 o mas '-TAG:borne', o 3 hojas con 12 o mas etiquetas '-TAG'); lista = trae la LISTA DE CONEXIONES
    (una hoja con 15 o mas '-TAG:borne' y el titulo o la cabecera de la lista). Rapido para los PDF de AutoCAD."""
    key = _firma(pdf)
    if key in _ES:
        return _ES[key]
    out = dict(eplan=False, lista=False)
    try:
        import pypdfium2 as pdfium
        hojas_tags = 0; total_tags = 0
        with PDFIUM_LOCK:
            doc = pdfium.PdfDocument(pdf)
            try:
                for i in range(len(doc)):
                    pg = doc[i]
                    try:
                        tp = pg.get_textpage()
                        try:
                            t = tp.get_text_range()
                        finally:
                            tp.close()
                    finally:
                        pg.close()
                    toks = t.split()
                    n = sum(1 for x in toks if ':' in x and DESIG_RE.match(x))
                    if n >= 15:
                        out['eplan'] = True
                        if LISTA_RE.search(t):
                            out['lista'] = True
                            break
                    nt = sum(1 for x in toks if TAG_TXT_RE.match(x))
                    total_tags += nt
                    if nt >= 8:
                        hojas_tags += 1
                    if hojas_tags >= 3 or total_tags >= 40:      # solo el esquema (sin la lista): sigue siendo EPLAN
                        out['eplan'] = True
            finally:
                doc.close()
    except Exception:
        out = dict(eplan=False, lista=False)
    _ES[key] = out
    return out


def es_eplan(pdf):
    """True si el PDF es un plano de EPLAN (texto real con muchas designaciones '-TAG:borne'), tenga o no la lista de
    conexiones: un EPLAN sin la lista NO se lee con el lector de AutoCAD (process corta con un mensaje claro)."""
    return deteccion(pdf)['eplan']


def tiene_lista(pdf):
    """True si el PDF de EPLAN trae la lista de conexiones (origen / destino de cada cable)"""
    return deteccion(pdf)['lista']


FALTA_LISTA = ('Falta la lista de conexiones: exportala desde EPLAN (informe «Lista de conexiones», con el número de cable, '
               'los dos destinos, el color y la sección) en el mismo PDF que el esquema y volvé a cargarlo.')


def rotulo(pg):
    """del cajetin de la hoja: hoja, titulo, documento, revision y caja del cajetin. Busca los rotulos ('Cont:', 'Title:',
    'Doc. number:', 'Rev.:') en ingles o castellano y lee lo que esta en su celda."""
    W = pg['words']; meta = {}
    low = lambda w: w['text'].strip().lower()
    horiz = [w for w in W if w['ang'] == 0]
    # 'Cont:' con los dos puntos: un 'CONT.' suelto en el esquema ('ALIM. CONT. E2.5') no es el rotulo del cajetin
    cont = [w for w in horiz if re.fullmatch(r'(cont|sig|siguiente|next):', low(w))]
    tit = [w for w in horiz if re.fullmatch(r'(title|t[ií]tulo)[:.]?', low(w))]
    rot = [w for w in horiz if re.fullmatch(r'(rev\.?|revisi[oó]n|cont|title|t[ií]tulo|project|proyecto|code|c[oó]digo|client|cliente|'
                                             r'doc\.?|number|n[uú]mero|date|fecha|description|descripci[oó]n|proj\.?|dw\.?|apr\.?)[:.]?', low(w))]
    if cont:
        c = min(cont, key=lambda w: w['bbox'][1] - w['bbox'][0])          # el de mas abajo a la derecha (el del cajetin)
        cb = c['bbox']
        cand = [w for w in horiz if w is not c and cb[3] - 1 < w['bbox'][1] < cb[3] + 30 and w['bbox'][2] > cb[0] - 10
                and w['bbox'][0] < cb[2] + 15 and re.fullmatch(r'[0-9A-Za-z][\w.]{0,9}', w['text']) and not w['text'].endswith(':')]
        if cand:
            meta['sheet'] = max(cand, key=lambda w: (w['fs'], -w['bbox'][1]))['text']
        if tit:
            t = min(tit, key=lambda w: abs(w['bbox'][1] - cb[1]))
            tb = t['bbox']
            lines = [l for l in pg['lines'] if l['ang'] == 0 and l['bbox'][0] > tb[0] - 5 and l['bbox'][2] < cb[0] - 3
                     and cb[1] - 6 < l['bbox'][1] and l['bbox'][3] < tb[3] + 2 and not re.fullmatch(r'(?i)(title|t[ií]tulo)[:.]?', l['text'].strip())]
            lines.sort(key=lambda l: -l['bbox'][1])
            if lines:      # el primer renglon es la descripcion del proyecto; el titulo de la hoja, los de abajo
                meta['title'] = ' '.join(l['text'] for l in (lines[1:] or lines))
                if len(lines) > 1:
                    meta['descripcion'] = lines[0]['text']
    # documento y revision: 'Doc. number:' y el 'Rev.:' del mismo renglon
    dn = [w for w in horiz if re.fullmatch(r'(?i)number:?|n[uú]mero:?|documento:?', w['text'].strip())]
    for w in dn:
        y = w['o'][1]
        fila = sorted((v for v in horiz if abs(v['o'][1] - y) < 0.5 * w['fs'] and v['bbox'][0] > w['bbox'][2] - 0.5), key=lambda v: v['bbox'][0])
        vals = [v for v in fila if not v['text'].endswith(':')]
        if vals:
            meta['documento'] = vals[0]['text']
            rv = [v for v in fila if re.fullmatch(r'(?i)rev(\.|isi[oó]n)?:?', v['text'])]
            if rv:
                after = [v for v in vals if v['bbox'][0] > rv[0]['bbox'][2]]
                if after:
                    meta['revision'] = after[0]['text']
            break
    # cajetin: SOLO el bloque del rotulo (el de 'Cont:' / 'Doc. number:' / 'Rev.:'), no la union de todas las palabras tipo
    # rotulo de la hoja (la cabecera 'Revisión / Fecha' de una tabla o un 'CONT.' del esquema lo estiraban a toda la hoja y
    # se perdian los numeros de cable). Se arranca de esos rotulos y se suman los que estan pegados en vertical.
    caj = cajetin_rotulo(horiz, rot, cont, dn, pg['h'])
    if caj:
        meta['cajetin'] = (caj[0] - 30, caj[1] - 25, pg['w'], caj[3] + 15)
    # rejilla de zonas (como core.page_meta): numeros arriba y letras a la izquierda
    pw, ph = pg['w'], pg['h']
    cols = sorted(((w['bbox'][0] + w['bbox'][2]) / 2, w['text']) for w in horiz if w['text'] in list('123456789') and w['bbox'][1] > 0.9 * ph)
    rows = sorted((-(w['bbox'][1] + w['bbox'][3]) / 2, w['text']) for w in horiz if w['text'] in list('ABCDEFGH') and w['bbox'][2] < 0.1 * pw)
    cols = [c for i, c in enumerate(cols) if i == 0 or c[1] != cols[i - 1][1]]
    rows = [r for i, r in enumerate(rows) if i == 0 or r[1] != rows[i - 1][1]]
    if len(cols) >= 3 and [c[1] for c in cols] == sorted(c[1] for c in cols):
        meta['col_edges'] = [((a[0] + b[0]) / 2, b[1]) for a, b in zip(cols, cols[1:])]
        meta['col_first'] = cols[0][1]
    if len(rows) >= 3:
        meta['row_edges'] = [(-(a[0] + b[0]) / 2, b[1]) for a, b in zip(rows, rows[1:])]
        meta['row_first'] = rows[0][1]
    return meta


def cajetin_rotulo(horiz, rot, cont, dn, h):
    """caja de los rotulos del bloque del cajetin: arranca del 'Cont:' de la hoja (o del 'Doc. number:' / 'Rev.:' si no hay)
    y suma los rotulos que estan a menos de 4 alturas de letra en vertical del bloque (en cadena), sin pasar de un quinto
    del alto de la hoja. -> (x0, y0, x1, y1) o None"""
    sem = []
    if cont:
        sem = [min(cont, key=lambda w: w['bbox'][1] - w['bbox'][0])]
    elif dn:
        sem = [min(dn, key=lambda w: w['bbox'][1])]
    else:
        rv = [w for w in rot if re.fullmatch(r'(?i)rev(\.|isi[oó]n)?:', w['text'].strip())]
        sem = [min(rv, key=lambda w: w['bbox'][1])] if rv else []
    if not sem:
        return None
    blk = list(sem)
    y0, y1 = sem[0]['bbox'][1], sem[0]['bbox'][3]
    resto = [w for w in rot if w is not sem[0]]
    cambio = True
    while cambio:
        cambio = False
        for w in list(resto):
            gap = max(w['bbox'][1] - y1, y0 - w['bbox'][3], 0.0)
            if gap <= 4 * max(w['fs'], 1.0) and max(y1, w['bbox'][3]) - min(y0, w['bbox'][1]) <= 0.2 * h:
                blk.append(w); resto.remove(w)
                y0, y1 = min(y0, w['bbox'][1]), max(y1, w['bbox'][3])
                cambio = True
    return _bb_union([w['bbox'] for w in blk]) if len(blk) >= 3 else None


def documento(pdf):
    """(numero de documento, revision) del rotulo (la primera hoja que los trae)"""
    for pg in leer(pdf):
        m = pg.get('_meta') or rotulo(pg)
        pg['_meta'] = m
        if m.get('documento'):
            return m['documento'], m.get('revision')
    return None, None


# ------------------------------------------------------------------ lista de conexiones
def lista_conexiones(pages):
    """renglones de las hojas 'Lista de conexiones': [dict(fila, pag, num, d1, d2, color, sec, bbox, bbox_num)] en el
    orden de lectura de EPLAN (cada hoja: la tabla de la izquierda de arriba abajo y despues la de la derecha).
    Cada renglon de la hoja se lee por contenido, no por columnas fijas: [numero] destino1 destino2 [color...] [seccion]
    (la tabla de la derecha no repite la cabecera); dos tablas lado a lado salen como dos registros."""
    out = []
    for pg in pages:
        meta = pg.get('_meta') or rotulo(pg); pg['_meta'] = meta
        caj = meta.get('cajetin')
        W = [w for w in pg['words'] if w['ang'] == 0 and not (caj and _dentro(_centro(w['bbox']), caj))]
        if sum(1 for w in W if ':' in w['text'] and DESIG_RE.match(w['text'])) < 5:
            continue
        txt = ' '.join(l['text'] for l in pg['lines'])
        if not LISTA_RE.search(txt) and not re.search(r'(?i)destino|target|ziel|origen|source', txt):
            continue
        # renglones: misma linea base
        W.sort(key=lambda w: (-w['o'][1], w['bbox'][0]))
        filas = []
        for w in W:
            if filas and abs(filas[-1]['y'] - w['o'][1]) < 0.5 * w['fs']:
                filas[-1]['w'].append(w)
            else:
                filas.append(dict(y=w['o'][1], w=[w]))
        regs = []
        for f in filas:
            toks = sorted(f['w'], key=lambda w: w['bbox'][0])
            if sum(1 for w in toks if DESIG_RE.match(w['text'])) < 1:
                continue
            rec = None

            def nuevo():
                return dict(num=None, d=[], dx=[], color=[], sec=None, bb=[], bbn=None, pag=pg['index'], y=f['y'])

            def cerrar(r):
                if r and r['d'] and (len(r['d']) == 2 or r['color'] or r['num']):
                    regs.append(r)
            rec = nuevo()
            for w in toks:
                t = w['text'].strip()
                if DESIG_RE.match(t):
                    if len(rec['d']) >= 2 or rec['color'] or rec['sec'] is not None:
                        cerrar(rec); rec = nuevo()
                    rec['d'].append(t); rec['bb'].append(w['bbox']); rec['dx'].append(w['bbox'][0])
                elif NUM_RE.match(t) and not (rec['d'] and rec['sec'] is None and not rec['color'] and len(t) <= 3):
                    if rec['d'] or rec['num']:
                        cerrar(rec); rec = nuevo()
                    rec['num'] = t; rec['bbn'] = w['bbox']; rec['bb'].append(w['bbox'])
                elif SEC_RE.match(t) and rec['d'] and rec['sec'] is None:
                    rec['sec'] = t.replace('.', ','); rec['bb'].append(w['bbox'])
                elif re.search(r'[A-Za-zÁÉÍÓÚáéíóúñÑ]', t) and rec['d'] and rec['sec'] is None:
                    rec['color'].append(t); rec['bb'].append(w['bbox'])
            cerrar(rec)
        # orden de lectura: tabla (por la x del primer destino) y de arriba abajo
        xs = sorted({round(min(b[0] for b in r['bb'])) for r in regs})
        tablas = []
        for x in xs:
            if not tablas or x - tablas[-1][-1] > 0.2 * pg['w']:
                tablas.append([x])
            else:
                tablas[-1].append(x)
        def tabla(r):
            x = round(min(b[0] for b in r['bb']))
            return next(i for i, t in enumerate(tablas) if t[0] <= x <= t[-1])
        regs.sort(key=lambda r: (tabla(r), -r['y']))
        # un renglon con un solo destino: va en la columna (destino 1 o 2) donde esta escrito
        col = collections.defaultdict(lambda: ([], []))
        for r in regs:
            if len(r['d']) == 2:
                col[tabla(r)][0].append(r['dx'][0]); col[tabla(r)][1].append(r['dx'][1])
        med = lambda v: sorted(v)[len(v) // 2] if v else None
        for r in regs:
            d = r['d'] + [None] * (2 - len(r['d']))
            c1, c2 = (med(v) for v in col[tabla(r)])
            if len(r['d']) == 1 and c1 is not None and c2 is not None and abs(r['dx'][0] - c2) < abs(r['dx'][0] - c1):
                d = [None, r['d'][0]]
            color_txt = ' '.join(r['color'])
            out.append(dict(fila=len(out) + 1, pag=pg['index'], hoja=meta.get('sheet', str(pg['index'])), num=r['num'],
                            d1=d[0], d2=d[1], color_txt=color_txt, color=norm_color(color_txt), malla=es_malla(color_txt),
                            sec=r['sec'] or '', bbox=_bb_union(r['bb']), bbox_num=r['bbn'], zona=None))
    return out


# ------------------------------------------------------------------ mapeo verificado (dato del producto)
def cargar_mapeo(doc, rev):
    """mapeo verificado del documento (programa/mapeos_verificados/*.json con documento y revision iguales) o None"""
    if not doc or not os.path.isdir(MAPEOS):
        return None
    for fn in sorted(os.listdir(MAPEOS)):
        if not fn.lower().endswith('.json'):
            continue
        try:
            with open(os.path.join(MAPEOS, fn), encoding='utf-8') as f:
                m = json.load(f)
        except Exception:
            continue
        if str(m.get('documento', '')).strip().upper() == str(doc).strip().upper() and str(m.get('revision', '')).strip() == str(rev or '').strip():
            m['_archivo'] = fn
            return m
    return None


def clave_punta(d, num):
    """clave de una punta en el mapeo verificado: '<designacion EPLAN>#<cable>' ('#s/n' si el renglon no tiene numero)"""
    return f'{d}#{num or "s/n"}'


def clave_tramo(d, num, otra):
    """clave de una punta cuando la de clave_punta no alcanza (varios renglones sin numero con la misma designacion y
    distinto texto, ej. los empalmes '-X1:2' del sensor de nivel): '<designacion>#<cable>@<designacion de la otra punta>'"""
    return f'{clave_punta(d, num)}@{otra or ""}'


# ------------------------------------------------------------------ textos del taller
HILERAS_RE = re.compile(r'(?i)hileras?\s+de\s+bornes|plano\s+de\s+bornes|terminal\s+(?:strip|diagram)|klemmen(?:plan|leiste)')
ARTICULOS_RE = re.compile(r'(?i)lista\s+de\s+art[ií]culos|lista\s+de\s+materiales|parts\s+list|bill\s+of\s+materials|st[üu]ckliste')
COL_TIPO_RE = re.compile(r'(?i)^(n[uú]mero\s+de\s+tipo|type\s+number|typnummer)$')
COL_ART_RE = re.compile(r'(?i)^(n[uú]mero\s+de\s+art[ií]culo|part\s+number|artikelnummer)$')
COL_SEC_RE = re.compile(r'(?i)^(secci[oó]n|cross[\s-]?section|querschnitt)$')
ACCESORIO_RE = re.compile(r'(?i)^(D-|E/|FBS|ZB|ATP|UBE|KLM|CLIPFIX|E-?NS\b)')   # tapas, topes, puentes, marcadores
QUATTRO_RE = re.compile(r'(?i)QUATTRO')
DOBLE_RE = re.compile(r'(?i)^(?:P|U|S|ST|PS|UT|UK)TT|TTB|UKK|DIK|-2L\b|2\s*pisos|doble\s+piso')
NUM_BORNE_RE = re.compile(r'^[A-Z]{0,2}\d{1,3}[A-Z]?$')
PROTECCION_RE = re.compile(r'^\d*[FQ]\d+[A-Z]?$')       # fusibles / interruptores (IEC 81346: F, Q)


def clase_borne(tipo):
    """'QUATTRO' (4 puntos: 'N.p'), 'DOBLE' (doble piso: 'N ARRIBA/ABAJO'), '2P' (2 puntos: 'N ARRIBA/ABAJO') o None
    (accesorio: tapa, tope, puente) segun el numero de tipo del articulo ('PT 6-QUATTRO', 'PTT 2,5-2MT', 'PT 6')"""
    t = (tipo or '').strip()
    if not t or ACCESORIO_RE.match(t):
        return None
    if QUATTRO_RE.search(t):
        return 'QUATTRO'
    if DOBLE_RE.search(t):
        return 'DOBLE'
    return '2P'


def tipos_bornes(pages):
    """tipo de cada borne de las borneras, leido del mismo PDF:
    - hojas 'Plano de hileras de bornes': por tira ('-15XR') y numero de borne, el 'Numero de tipo' de su renglon (un
      renglon sin tipo es el otro piso del articulo de arriba: 'F1' + '1' de un PTTB);
    - si no, la 'Lista de articulos': el tipo de la tira cuando tiene una sola clase de borne.
    -> (por_num {(tira, n): dict(clase, tipo, pag)}, por_tira {tira: dict(clase, tipo, pag)})"""
    por_num, por_tira = {}, {}
    clases_tira = collections.defaultdict(dict)
    for pg in pages:
        caj = (pg.get('_meta') or rotulo(pg)).get('cajetin')
        L = [l for l in pg['lines'] if l['ang'] == 0 and not (caj and _dentro(_centro(l['bbox']), caj))]
        cy = lambda l: (l['bbox'][1] + l['bbox'][3]) / 2
        tits = sorted((l for l in L if HILERAS_RE.search(l['text'])), key=lambda l: -cy(l))
        for i, t in enumerate(tits):
            bot = cy(tits[i + 1]) if i + 1 < len(tits) else -1e9
            blk = [l for l in L if bot < cy(l) < cy(t)]
            hdr = [l for l in blk if COL_TIPO_RE.match(l['text'].strip())]
            if not hdr:
                continue
            hdr = max(hdr, key=cy)
            x_tipo, y_hdr = hdr['bbox'][0], cy(hdr)
            tiras = [l for l in blk if re.fullmatch(r'-\S+', l['text']) and TERMINAL_RE.match(l['text'][1:]) and cy(l) > y_hdr - 6]
            if not tiras:
                continue
            tira = tiras[0]['text'][1:]
            x_num = max(l['bbox'][0] for l in tiras) if len(tiras) > 1 else None
            if x_num is None or x_num < x_tipo + 100:
                continue
            # columnas de la tabla por sus cabeceras (los valores no estan alineados con la cabecera: cada valor va a la
            # columna de la cabecera mas cercana)
            cols = [('tipo', x_tipo), ('num', x_num)] + [(k, l['bbox'][0]) for l in blk if abs(cy(l) - y_hdr) < 6 and l is not hdr
                                                          for k, rx in (('art', COL_ART_RE), ('sec', COL_SEC_RE)) if rx.match(l['text'].strip())]
            col_de = lambda l: min(cols, key=lambda c: abs(l['bbox'][0] - c[1]))[0]
            filas_t = [(cy(l), l['text'].strip()) for l in blk if cy(l) < y_hdr - 2 and l['bbox'][0] < x_num - 10 and col_de(l) == 'tipo']
            for l in blk:
                if not (cy(l) < y_hdr - 2 and x_num - 10 <= l['bbox'][0] <= x_num + 90):
                    continue
                for tok in l['text'].split():
                    if not NUM_BORNE_RE.match(tok):
                        continue
                    y = cy(l)
                    mismo = [ft for ft in filas_t if abs(ft[0] - y) < 4 and clase_borne(ft[1])]
                    arriba = sorted((ft for ft in filas_t if 0 < ft[0] - y < 70 and clase_borne(ft[1])), key=lambda ft: ft[0] - y)
                    ft = (mismo or arriba or [None])[0]
                    if ft:
                        por_num[(tira, tok)] = dict(clase=clase_borne(ft[1]), tipo=ft[1], pag=pg['index'])
        # lista de articulos: tag a la izquierda y 'Numero de tipo' en su columna, en el mismo renglon
        if any(ARTICULOS_RE.search(l['text']) for l in L):
            hdr = [l for l in L if COL_TIPO_RE.match(l['text'].strip())]
            if hdr:
                x_tipo = hdr[0]['bbox'][0]
                for l in L:
                    if re.fullmatch(r'-\S+', l['text']) and TERMINAL_RE.match(l['text'][1:]) and l['bbox'][0] < x_tipo - 100:
                        for v in L:
                            if abs(cy(v) - cy(l)) < 3 and abs(v['bbox'][0] - x_tipo) < 15 and clase_borne(v['text']):
                                clases_tira[l['text'][1:]][clase_borne(v['text'])] = dict(clase=clase_borne(v['text']), tipo=v['text'].strip(), pag=pg['index'])
    for tira, cs in clases_tira.items():
        if len(cs) == 1:
            por_tira[tira] = next(iter(cs.values()))
    return por_num, por_tira


def texto_general(d, info=None):
    """texto del taller de un punto de conexion EPLAN sin mapeo verificado ni tipo de bornera conocido (ultimo recurso;
    lo normal es textos_generales, que lee el tipo de las hojas de hileras de bornes):
    bornera con punto: QUATTRO (4 puntos) 'N.p'; borne de 2 puntos 'N ARRIBA' (punto 1) / 'N ABAJO' (punto 2).
    aparato: 'TAG borne' con los campos de la designacion ('11PS1 TB2 1', '61KR1 A1', '13MS1 2/T1')."""
    if not d:
        return 'LI'
    p = partes(d)
    tag, pines = p['tag'], p['pines']
    if TERMINAL_RE.match(tag) and len(pines) == 2 and pines[1].isdigit():
        n, pt = pines[0], int(pines[1])
        maxp = (info or {}).get((tag, n), pt)
        if maxp > 2:
            return f'{tag} {n}.{pt}'
        return f'{tag} {n} {"ARRIBA" if pt == 1 else "ABAJO"}'
    if not pines:
        return tag
    b = ' '.join(pines)
    b = re.sub(r'^(A[12])[+-]$', r'\1', b)            # bobina 'A1+' / 'A2-' -> 'A1' / 'A2'
    return f'{tag} {b}'


def textos_generales(filas, tipos):
    """texto del taller de cada punta SIN mapeo verificado (regla general) y, si algo no se puede saber del PDF, por que
    hay que confirmarlo: {(fila, designacion): (texto, motivo o None)}.
    - Borneras: la CLASE sale del tipo del articulo (tipos_bornes), no del punto mas alto usado:
      QUATTRO 'N.p' (los puntos de EPLAN son los del taller); doble piso (PTT) y 2 puntos 'N ARRIBA' / 'N ABAJO'.
      El LADO no sale del numero de punto (en el PTT EPLAN numera al reves que el taller y depende de como se monta la
      tira): en el doble piso los puntos 1-2 son un lado y 3-4 el otro; va ABAJO el lado de los cables de campo
      ('+Campo...'), y si todos van del mismo lado, ARRIBA. Siempre 'a confirmar'.
      Una designacion sin punto ('-12XPS:10') va al lado que no usa otro cable de ese borne.
    - Fusibles / interruptores (F, Q) con pines numericos: IEC, impar = entrada ARRIBA y par = salida ABAJO; con dos
      polos, 'F' y 'N' ('11Q2 F ARRIBA'); 'N' / "N'" = 'N ARRIBA' / 'N ABAJO'. A confirmar.
    - Sin pin ('-42KS1'): 'TAG', a confirmar (EPLAN no da el borne).
    - El resto: 'TAG pin' con los campos de la designacion (texto_general)."""
    por_num, por_tira = tipos or ({}, {})
    maxp = collections.defaultdict(int)
    usos = collections.defaultdict(list)               # (tira, n) -> [(fila, d, punto o None)]
    pines_dev = collections.defaultdict(set)
    for f in filas:
        for d in (f['d1'], f['d2']):
            if not d:
                continue
            p = partes(d)
            if TERMINAL_RE.match(p['tag']) and p['pines']:
                pt = int(p['pines'][1]) if len(p['pines']) >= 2 and p['pines'][1].isdigit() else None
                usos[(p['tag'], p['pines'][0])].append((f, d, pt))
                if pt:
                    maxp[(p['tag'], p['pines'][0])] = max(maxp[(p['tag'], p['pines'][0])], pt)
            elif PROTECCION_RE.match(p['tag']) and len(p['pines']) == 1:
                pines_dev[p['tag']].add(p['pines'][0])

    def clase(tag, n):
        c = por_num.get((tag, n)) or por_tira.get(tag)
        return (c['clase'], c['tipo']) if c else (None, None)
    par = lambda pt: 0 if (pt - 1) % 4 < 2 else 1          # 0 = puntos 1-2 (5-6), 1 = puntos 3-4 (7-8)
    campo = lambda f, d: any(partes(x)['ubic'] for x in (f['d1'], f['d2']) if x and x != d)
    # orientacion de cada tira de doble piso: que par de puntos queda ARRIBA
    est = collections.defaultdict(lambda: [[0, 0], [0, 0]])
    for (tag, n), us in usos.items():
        if clase(tag, n)[0] == 'DOBLE':
            for f, d, pt in us:
                if pt:
                    est[tag][1][par(pt)] += 1
                    est[tag][0][par(pt)] += campo(f, d)
    orient = {}
    for tag, (cm, us) in est.items():
        if cm[0] != cm[1]:
            orient[tag] = (1 if cm[0] > cm[1] else 0, 'va ABAJO el lado de los cables de campo')
        elif bool(us[0]) != bool(us[1]):
            orient[tag] = (0 if us[0] else 1, 'todos sus cables van del mismo lado: se puso ARRIBA')
        else:
            orient[tag] = (0, 'se puso ARRIBA el lado de los puntos 1-2')
    out = {}
    for (tag, n), us in usos.items():
        cl, tipo = clase(tag, n)
        lados = {}
        for f, d, pt in us:
            if not pt:
                continue
            if cl == 'QUATTRO':
                out[(f['fila'], d)] = (f'{tag} {n}.{pt}', None)
            elif cl == 'DOBLE':
                arriba, why = orient.get(tag, (0, ''))
                lado = 'ARRIBA' if par(pt) == arriba else 'ABAJO'
                lados[d] = lado
                out[(f['fila'], d)] = (f'{tag} {n} {lado}', f'borne de doble piso ({tipo}): EPLAN no dice qué lado queda arriba; {why}')
            elif cl == '2P':
                lado = 'ARRIBA' if pt % 2 else 'ABAJO'
                lados[d] = lado
                out[(f['fila'], d)] = (f'{tag} {n} {lado}', f'borne de 2 puntos ({tipo}): lado tomado del punto de EPLAN (1 = ARRIBA, 2 = ABAJO)')
            else:
                t = texto_general(d, maxp)
                out[(f['fila'], d)] = (t, 'no se encontró el tipo de esta bornera en las hojas de hileras de bornes ni en la lista de '
                                          'artículos: se supuso por los puntos usados' + (' (y el lado, por el número de punto)' if t.endswith(('ARRIBA', 'ABAJO')) else ''))
        # designaciones sin punto: al lado que no usa otro cable de ese borne (si no, ARRIBA / ABAJO en el orden de la lista)
        sin = [(f, d) for f, d, pt in us if not pt]
        if not sin:
            continue
        if cl is None:          # ni tipo ni punto (ej. un empalme 'X1'): el texto de la designacion, sin inventar el lado
            for f, d in sin:
                out[(f['fila'], d)] = (texto_general(d), 'no se encontró el tipo de esta bornera en las hojas de hileras de bornes '
                                                         'ni en la lista de artículos')
            continue
        if cl == 'QUATTRO':
            for f, d in sin:
                out[(f['fila'], d)] = (f'{tag} {n}', 'EPLAN no da el punto del borne QUATTRO')
            continue
        libres = [s for s in ('ARRIBA', 'ABAJO') if s not in set(lados.values())] or ['ARRIBA', 'ABAJO']
        cables = []
        for f, d in sin:
            k = f['num'] or ('s/n', f['fila'])
            if k not in cables:
                cables.append(k)
        for f, d in sin:
            i = cables.index(f['num'] or ('s/n', f['fila']))
            lado = libres[min(i, len(libres) - 1)]
            como = ('del lado que no usa otro cable de ese borne' if len(libres) < 2 else
                    'ARRIBA y ABAJO repartidos en el orden de la lista' if len(cables) > 1 else 'se puso ARRIBA')
            out[(f['fila'], d)] = (f'{tag} {n} {lado}', f'EPLAN no da el punto del borne ({tipo or "tipo desconocido"}): {como}')
    # fusibles e interruptores
    for f in filas:
        for d in (f['d1'], f['d2']):
            if not d or (f['fila'], d) in out:
                continue
            p = partes(d)
            if not p['pines']:
                if not TERMINAL_RE.match(p['tag']):
                    out[(f['fila'], d)] = (p['tag'], 'EPLAN no da el borne: buscalo en el esquema')
                continue
            pins = pines_dev.get(p['tag'])
            if not pins or len(p['pines']) != 1:
                continue
            nums = sorted(int(x) for x in pins if x.isdigit())
            otros = {x for x in pins if not x.isdigit()}
            if not nums or nums[-1] > 8 or otros - {'N', "N'"}:
                continue
            polos = (nums[-1] + 1) // 2
            pin = p['pines'][0]
            motivo = 'protección (fusible / interruptor): regla general IEC, impar = entrada ARRIBA y par = salida ABAJO'
            if pin in ('N', "N'"):
                out[(f['fila'], d)] = (f"{p['tag']} N {'ARRIBA' if pin == 'N' else 'ABAJO'}", motivo)
                continue
            k = int(pin)
            lado = 'ARRIBA' if k % 2 else 'ABAJO'
            if polos <= 1 and not otros:
                out[(f['fila'], d)] = (f"{p['tag']} {lado}", motivo)
            elif polos <= 2:
                out[(f['fila'], d)] = (f"{p['tag']} {'F' if k <= 2 else 'N'} {lado}", motivo + '; polo 1 = F, polo 2 = N')
            else:
                out[(f['fila'], d)] = (f"{p['tag']} {k} {lado}", motivo)
    return out


def nodo(texto, d, tag_base, hoja, pag, p):
    """punta en el formato de instructivo.describe_end, armada desde su texto del taller"""
    from instructivo import is_terminal_block
    tag, _, rest = (texto or '').partition(' ')
    e = dict(tipo='borne', tag=tag, tag_base=tag_base or tag, borne=rest, punto=None, lado='ARRIBA', vertical=False, circulo=True,
             borde=False, p=p, hoja=hoja, pag=pag, texto=texto, d=d, eplan=True)
    m = re.match(r'^(.*) (ARRIBA|ABAJO)$', rest)
    if m:
        e.update(borne=m.group(1), lado=m.group(2), vertical=True)
    elif rest in ('ARRIBA', 'ABAJO'):                # '11F1 ABAJO': aparato de 2 bornes, el lado es todo el borne
        e.update(borne='', lado=rest, vertical=True)
    m2 = re.fullmatch(r'(\d+)\.(\d)', rest)
    if m2 and is_terminal_block(tag_base or tag):
        e.update(borne=m2.group(1), punto=int(m2.group(2)))
    return e


def hojas_esquema(cond, detail, pages):
    """la hoja de cada punta es la del ESQUEMA donde aparece su numero (no la de la lista de conexiones, que es la misma
    para todas): la aparicion del numero mas cerca de la etiqueta '-TAG' de su aparato en esa hoja (si el numero esta en
    varias hojas, la que tiene dibujado el aparato). Asi el boton Funcional del visor abre la hoja correcta.
    La de la lista queda en hoja_lista / pag_lista / p_lista."""
    occ = collections.defaultdict(list)
    for d in detail:
        if not str(d.get('origen', '')).startswith('Solo'):
            occ[d['num']].append(d)
    etq = {}
    for pg in pages:
        m = collections.defaultdict(list)
        for w in pg['words']:
            if w['text'][:1] in '-=+':
                mm = DESIG_PARTES.match(w['text'])
                if mm:
                    m[mm.group('tag')].append(_centro(w['bbox']))
        etq[pg['index']] = m
    hoja_de = {d['pag']: d['hoja'] for d in detail}
    esquema = {d['pag'] for v in occ.values() for d in v}          # hojas del esquema (las que tienen numeros)
    for num, c in cond.items():
        oc = occ.get(num)
        if not oc:
            # sin numero en el esquema (tierras, mallas, cables de campo): la hoja del esquema donde estan dibujados sus
            # aparatos (la que tiene mas etiquetas de sus puntas)
            tags_c = {partes(e['d'])['tag'] for e in c['nodes'].values() if e.get('d')}
            cand = sorted(((sum(1 for t in tags_c if etq.get(pg_, {}).get(t)), -pg_) for pg_ in esquema), reverse=True)
            if not cand or cand[0][0] == 0:
                continue
            pg_ = -cand[0][1]
            for e in c['nodes'].values():
                e.update(hoja_lista=e.get('hoja'), pag_lista=e.get('pag'), p_lista=e.get('p'), hoja=hoja_de[pg_], pag=pg_)
                pts = etq[pg_].get(partes(e['d'])['tag']) if e.get('d') else None
                if e.get('p') is not None:
                    e['p'] = [round(v, 1) for v in pts[0]] if pts else None
            continue
        for e in c['nodes'].values():
            tags = {partes(e['d'])['tag'], e.get('tag_base')} - {None, ''} if e.get('d') else set()
            def costo(o):
                pts = [q for t in tags for q in etq.get(o['pag'], {}).get(t, [])]
                ce = _centro(o['bbox'])
                return (0, min(math.dist(ce, q) for q in pts), o['pag']) if pts else (1, 0.0, o['pag'])
            o = min(oc, key=costo)
            e.update(hoja_lista=e.get('hoja'), pag_lista=e.get('pag'), p_lista=e.get('p'), hoja=o['hoja'], pag=o['pag'])
            if e.get('p') is not None:
                e['p'] = [round(v, 1) for v in _centro(o['bbox'])]


# ------------------------------------------------------------------ proceso del plano (como core.process)
class Result:
    pass


def process(pdf_path, log=print, use_ocr=True, pages=None):
    from core import zone_of, natkey
    t0 = time.time()
    log('Plano de EPLAN: leyendo los textos de las hojas…')
    pgs = leer(pdf_path)
    n = len(pgs)
    for pg in pgs:
        pg['_meta'] = pg.get('_meta') or rotulo(pg)
    doc, rev = documento(pdf_path)
    mapeo = cargar_mapeo(doc, rev)
    filas = lista_conexiones(pgs)
    if not filas:            # EPLAN sin la lista de conexiones: no se puede saber de donde a donde va cada cable
        raise ValueError(FALTA_LISTA)
    log(f'Lista de conexiones: {len(filas)} renglones' + (f' · mapeo verificado {mapeo["_archivo"]}' if mapeo else ''))
    hojas_lista = {f['pag'] for f in filas}
    res = Result(); res.path = pdf_path; res.eplan = True; res.H = 7.93; res.k = 1.0; res.default = None
    res.documento, res.revision = doc, rev
    res.mapeo_verificado = mapeo
    res.filas_conexiones = filas
    # tags de las etiquetas '-TAG' de las hojas que no son la lista (bandejas, vistas): un rele '61KR1' cuya etiqueta en
    # la bandeja es la del grupo '-61KR' toma ese tag de base (como el modulo del rele en los planos de AutoCAD)
    tags_lista = {partes(d)['tag'] for f in filas for d in (f['d1'], f['d2']) if d}
    grupos_lista = tags_lista | {re.sub(r'\d+$', '', t) for t in tags_lista}
    nums_lista = {f['num'] for f in filas if f['num']}
    etiquetas, mejor = set(), 0
    for pg in pgs:          # la hoja con mas etiquetas de aparatos y sin numeros de cable: la de bandejas (o su vista)
        if pg['index'] in hojas_lista or any(w['text'] in nums_lista for w in pg['words']):
            continue
        et = {w['text'][1:] for w in pg['words'] if re.fullmatch(r'-[A-Z0-9][\w\-]*', w['text'])}
        n_ = len(et & grupos_lista)
        if n_ > mejor:
            etiquetas, mejor = et, n_
    def tag_base(tag):
        if tag in etiquetas:
            return tag
        b = re.sub(r'\d+$', '', tag)
        return b if b != tag and b in etiquetas and re.search(r'[A-Z]$', b) else tag
    # textos del taller sin mapeo verificado: regla general con el tipo de cada bornera (hojas de hileras de bornes /
    # lista de articulos del mismo PDF); lo que el PDF no dice queda 'a confirmar'
    tipos = tipos_bornes(pgs)
    general = textos_generales(filas, tipos)
    mp_puntas = (mapeo or {}).get('puntas') or {}
    mp_textos = (mapeo or {}).get('textos') or {}
    def texto_de(d, f):
        """(texto, motivo 'a confirmar' o None): del mapeo verificado o de la regla general"""
        otra = f['d2'] if d == f['d1'] else f['d1']
        for k in (clave_tramo(d, f['num'], otra), clave_punta(d, f['num'])):
            if k in mp_puntas and mp_puntas[k].get('texto'):
                return mp_puntas[k]['texto'], None
            if k in mp_textos:
                return mp_textos[k], None
        return general.get((f['fila'], d)) or (texto_general(d), None)
    # nombres de los renglones sin numero (tierras, mallas, cables de campo): unicos y legibles
    usados = collections.Counter()
    from instructivo import is_terminal_block
    def nombre_sn(f):
        ds = [d for d in (f['d1'], f['d2']) if d]
        ps = [partes(d) for d in ds]
        dev = [p for p in ps if not is_terminal_block(p['tag'])] or ps
        p = dev[-1] if dev else dict(tag='?', pines=[])
        if f['color'] == 'Verde-Amarillo':
            base = '⏚' + p['tag']
        elif f['malla']:
            base = 'MALLA ' + ' '.join([p['tag']] + p['pines'][:1])
        else:
            base = 's/n ' + ' '.join([p['tag']] + p['pines'][:1])
        usados[base] += 1
        return base if usados[base] == 1 else f'{base} ({usados[base]})'
    puentes_internos = []
    cond = collections.OrderedDict()
    for f in filas:
        if not f['num'] and f['d1'] and f['d1'] == f['d2']:
            puentes_internos.append(f)            # '-61KR1 -61KR1': union interna del aparato (rele y su zocalo), no es un cable
            continue
        num = f['num'] or nombre_sn(f)
        f['cable'] = num
        c = cond.setdefault(num, dict(nodes={}, pares=[], bornes=[], desc_par={}, filas=[]))
        ids = []
        for k, d in (('d1', f['d1']), ('d2', f['d2'])):
            if d:
                nid = d
                if nid not in c['nodes']:
                    p = partes(d)
                    bb = f['bbox']
                    txt, motivo = texto_de(d, f)
                    c['nodes'][nid] = nodo(txt, d, tag_base(p['tag']), f['hoja'], f['pag'], [round(bb[0], 1), round(bb[1], 1)])
                    if p['ubic']:
                        c['nodes'][nid]['ubicacion'] = p['ubic']
                    if motivo:                  # texto de la regla general: lo que el PDF no dice, a confirmar
                        c['nodes'][nid]['a_confirmar'] = motivo
            else:                               # renglon con un solo destino (malla o tierra de un cable de campo)
                nid = f'?{f["fila"]}'
                c['nodes'][nid] = dict(tipo='borne', tag='', tag_base='', borne='', punto=None, lado='ARRIBA', vertical=False, circulo=False,
                                       borde=False, p=None, hoja=f['hoja'], pag=f['pag'], fuera=True, texto='LI', d=None, eplan=True)
            ids.append(nid)
        par = tuple(sorted(ids))
        if par[0] != par[1] and par not in c['pares']:
            c['pares'].append(par)
            sec = f['sec'].replace(',', '.')
            if f['malla']:
                desc = ('MALLA', '', '')
            else:
                ini = __import__('instructivo').COLOR_INI.get(f['color'], (f['color'] or '?')[:1].upper())
                desc = (f'{ini}{sec}MM' if sec else (ini if f['color'] else '?'), f['color'], sec)
            c['desc_par'][par] = desc
        c['filas'].append(f['fila'])
    for num, c in cond.items():
        c['pares'].sort()
        c['bornes'] = sorted(c['nodes'])
    res.conductores = cond
    res.puentes_internos = puentes_internos
    # ---- hojas (como core: meta, numeros, recorridos)
    nums = {f['num'] for f in filas if f['num']}
    res.pages = []
    detail = []
    for pg in pgs:
        meta = pg['_meta']
        caj = meta.get('cajetin')
        lines = [dict(l) for l in pg['lines']]
        page = dict(index=pg['index'], w=pg['w'], h=pg['h'], x0=pg['x0'], y0=pg['y0'], lines=lines, signos=[], strokes=[], meta=meta,
                    graph=None, nums=[], labels=[], routes={}, raster=False)
        if pg['index'] not in hojas_lista:
            for w in pg['words']:
                t = w['text'].strip()
                if t in nums and not (caj and _dentro(_centro(w['bbox']), caj)):
                    page['nums'].append(dict(num=t, bbox=w['bbox'], chain=0, line=dict(text=t)))
        res.pages.append(page)
        log(f'Hoja {pg["index"]}/{n}: {len(page["nums"])} números de cable')
    res.pages_by_index = {p['index']: p for p in res.pages}
    # variantes de color / seccion de cada numero (en la lista)
    var = collections.defaultdict(list)
    for f in filas:
        if f['num'] and not f['malla']:
            v = (f['color'], f['sec'])
            if v not in var[f['num']]:
                var[f['num']].append(v)
    for f in filas:
        if f['num'] and f['num'] not in var:
            var[f['num']].append(('', ''))
    sheet = lambda pg: pg['meta'].get('sheet', str(pg['index']))
    for page in res.pages:
        for nm in page['nums']:
            vs = var.get(nm['num']) or [('', '')]
            c, s = vs[0]
            if len(vs) > 1:     # varias secciones: la que esta escrita junto al numero en el esquema ('35 mm²', 'Negro')
                cerca = [l['text'] for l in page['lines'] if math.dist(_centro(l['bbox']), _centro(nm['bbox'])) < 45]
                for cc, ss in vs:
                    if any(SEC_MM_RE.match(t.strip()) and SEC_MM_RE.match(t.strip()).group(1).replace('.', ',') == ss for t in cerca):
                        c, s = cc, ss; break
            bb = nm['bbox']
            detail.append(dict(num=nm['num'], pag=page['index'], hoja=sheet(page), zona=zone_of(page['meta'], *_centro(bb), page['w'], page['h']),
                               bbox=[round(v, 2) for v in bb], color=c, sec=s, origen='Lista de conexiones de EPLAN', corte=False, refs=[],
                               texto=nm['num'], src='eplan', puntas=0))
    # numeros que no aparecen en el esquema: su renglon de la lista de conexiones
    con_esquema = {d['num'] for d in detail}
    for f in filas:
        if f['num'] and f['num'] not in con_esquema:
            page = res.pages_by_index[f['pag']]
            bb = f['bbox_num'] or f['bbox']
            detail.append(dict(num=f['num'], pag=f['pag'], hoja=sheet(page), zona=zone_of(page['meta'], *_centro(bb), page['w'], page['h']),
                               bbox=[round(v, 2) for v in bb], color=f['color'], sec=f['sec'], origen='Solo en la lista de conexiones de EPLAN',
                               corte=False, refs=[], texto=f['num'], src='eplan', puntas=0))
            con_esquema.add(f['num'])
    # puntas de cada numero (cable de 3 o mas puntas = puente en un borne)
    for d in detail:
        c = cond.get(d['num'])
        d['puntas'] = len(c['bornes']) if c else 0
    res.detail = detail
    hojas_esquema(cond, detail, pgs)
    cables = []
    by_num = collections.defaultdict(list)
    for d in detail:
        by_num[d['num']].append(d)
    for num in sorted(by_num, key=natkey):
        occ = by_num[num]; c = cond.get(num)
        vs = var.get(num) or [('', '')]
        for col, sec in vs:
            ds = [d for d in occ if (d['color'], d['sec']) == (col, sec)] or ([] if len(vs) > 1 else occ)
            obs = []
            if len(vs) > 1:
                obs.append('Este número tiene tramos con distinto color/sección: revisar')
            if c and len(c['bornes']) >= 3:
                grado = collections.Counter(x for par in c['pares'] for x in par)
                junto = [c['nodes'][x]['texto'] for x, g in grado.items() if g > 1]
                obs.insert(0, f'Cable de {len(c["bornes"])} puntas: puente/derivación' + (f' en {", ".join(junto)}' if junto else '') + ' (hecho a propósito)')
            sin_pin = [c['nodes'][x]['d'] for x in (c['bornes'] if c else []) if c['nodes'][x].get('d') and ':' not in c['nodes'][x]['d']]
            if sin_pin:
                obs.append('EPLAN no da el borne de ' + ', '.join(sorted(set(sin_pin))) + (' (tomado del mapeo verificado)' if mapeo else ': revisar en el esquema'))
            if not col and not sec:
                obs.append('Color y sección no indicados en la lista')
            hojas = sorted({x['hoja'] for x in ds}, key=natkey)
            cables.append(dict(num=num, color=col, sec=sec, puntas=len(c['bornes']) if c else 0, hojas=', '.join(hojas),
                               ubic=', '.join(f"{x['hoja']}:{x['zona']}" for x in ds), n=len(ds), refs='', obs='; '.join(obs)))
    res.cables = cables
    # sin numero (tierras, mallas, campo) y a revisar
    res.unnumbered = []
    for f in filas:
        if f['num'] or (f['d1'] and f['d1'] == f['d2']):
            continue
        page = res.pages_by_index[f['pag']]
        bb = f['bbox']
        res.unnumbered.append(dict(color=f['color'] or ('Malla' if f['malla'] else ''), sec=f['sec'], hoja=sheet(page), pag=f['pag'], bbox=[round(v, 2) for v in bb],
                                   zona=zone_of(page['meta'], *_centro(bb), page['w'], page['h']), largo=0, refs='',
                                   texto=f"{f['cable']}: {f['d1'] or '—'} → {f['d2'] or '—'}"))
    review = []
    for f in filas:
        page = res.pages_by_index[f['pag']]
        bb = [round(v, 2) for v in f['bbox']]
        z = zone_of(page['meta'], *_centro(bb), page['w'], page['h'])
        for k in ('d1', 'd2'):
            d = f[k]
            if d and ':' not in d and not (f['d1'] == f['d2'] and not f['num']):
                k2 = clave_punta(d, f['num'])
                if k2 in mp_puntas or k2 in mp_textos or clave_tramo(d, f['num'], f['d2'] if k == 'd1' else f['d1']) in mp_textos:
                    continue
                review.append(dict(tipo='EPLAN no indica el borne (solo el aparato)', texto=f"{f['num'] or f.get('cable', '')}: {d}", pag=f['pag'],
                                   hoja=sheet(page), zona=z, bbox=bb, num=f['num'] or None))
        if not f['d1'] or not f['d2']:
            review.append(dict(tipo='Renglón con un solo destino', texto=f"{f.get('cable', '')}: {f['d1'] or f['d2']} ({f['color_txt']})", pag=f['pag'],
                               hoja=sheet(page), zona=z, bbox=bb))
    for num, vs in var.items():
        if len(vs) > 1:
            occ = by_num.get(num) or []
            review.append(dict(tipo='Cable con distintos colores/secciones', texto=num + ': ' + ' | '.join(f'{c} {s}' for c, s in vs),
                               pag=occ[0]['pag'] if occ else filas[0]['pag'], hoja=occ[0]['hoja'] if occ else '', zona=occ[0]['zona'] if occ else '',
                               bbox=occ[0]['bbox'] if occ else None, num=num))
    # textos del taller de la regla general que hay que confirmar (lado del borne, tipo de bornera); los que no tienen
    # borne ya estan arriba ('EPLAN no indica el borne')
    n_conf = 0
    for num, c in cond.items():
        for e in c['nodes'].values():
            if not e.get('a_confirmar'):
                continue
            n_conf += 1
            if e['a_confirmar'].startswith('EPLAN no da el borne'):
                continue
            page = res.pages_by_index.get(e.get('pag'))
            q = e.get('p')
            bb = [round(q[0] - 8, 2), round(q[1] - 4, 2), round(q[0] + 8, 2), round(q[1] + 4, 2)] if q else None
            review.append(dict(tipo='Texto del taller a confirmar (regla general)', texto=f"{num}: {e['d']} → {e['texto']} ({e['a_confirmar']})",
                               pag=e.get('pag'), hoja=e.get('hoja'), bbox=bb, num=num if num in nums else None,
                               zona=zone_of(page['meta'], *q, page['w'], page['h']) if (page and q) else ''))
    res.textos_a_confirmar = n_conf
    if n_conf:
        log(f'Textos del taller: {n_conf} puntas con la regla general a confirmar' + (' (fuera del mapeo verificado)' if mapeo else ''))
    res.review = review
    res.stats = dict(eplan=1, filas_lista=len(filas), puentes_internos=len(puentes_internos), mapeo_verificado=(mapeo or {}).get('_archivo'),
                     textos_a_confirmar=n_conf)
    res.seconds = time.time() - t0
    return res


# ------------------------------------------------------------------ hoja de bandejas (como topo.layout)
def _merge(lines, gap):
    by = collections.defaultdict(list)
    for c, a0, a1 in lines:
        by[round(c, 1)].append((a0, a1, c))
    out = []
    for L in by.values():
        L.sort()
        cur = list(L[0])
        for a0, a1, c in L[1:]:
            if a0 <= cur[1] + gap:
                cur[1] = max(cur[1], a1)
            else:
                out.append((cur[2], cur[0], cur[1])); cur = [a0, a1, c]
        out.append((cur[2], cur[0], cur[1]))
    return out


def _cobertura(lines, c, a0, a1, tol=0.3):
    L = sorted((max(a0, p0), min(a1, p1)) for cc, p0, p1 in lines if abs(cc - c) < tol and p1 > a0 and p0 < a1)
    tot, cur = 0.0, None
    for s, e in L:
        if cur is None or s > cur[1]:
            if cur:
                tot += cur[1] - cur[0]
            cur = [s, e]
        else:
            cur[1] = max(cur[1], e)
    if cur:
        tot += cur[1] - cur[0]
    return tot / max(a1 - a0, 1e-9)


def rieles(segs):
    """tramos de riel DIN horizontales: grupos de >= 4 lineas paralelas con el mismo largo (los bordes y los pliegues del
    perfil), simetricas respecto del eje y con el canal del medio vacio. Primero los tramos largos (dan el perfil H y el
    patron de lineas); despues cualquier tramo visible entre dos aparatos que tenga ese mismo patron."""
    grp = collections.defaultdict(set)
    for (ax, ay), (bx, by_) in segs:
        if abs(ay - by_) < 0.05 and abs(ax - bx) > 0.3:
            grp[(round(min(ax, bx), 2), round(max(ax, bx), 2))].add(round((ay + by_) / 2, 2))
    def perfil_en(ys, x0, x1, largo_min):
        ys = sorted(ys)
        for i in range(len(ys)):
            for j in range(len(ys) - 1, i, -1):
                a, b = ys[i], ys[j]; H = b - a
                if H < 8 or H > 80 or x1 - x0 < largo_min * H:
                    continue
                inn = [y for y in ys if a - 0.01 <= y <= b + 0.01]
                if len(inn) < 4 or not all(any(abs((a + b) - y - z) < 0.15 for z in inn) for y in inn):
                    continue
                if max(q - p for p, q in zip(inn, inn[1:])) < 0.45 * H:
                    continue
                return a, b, [round((y - a) / H, 3) for y in inn]
        return None
    bands = []
    for (x0, x1), ys in grp.items():
        if len(ys) >= 4:
            r = perfil_en(ys, x0, x1, 0.75)
            if r:
                bands.append(dict(x0=x0, x1=x1, y0=r[0], y1=r[1], H=round(r[1] - r[0], 2), eje=(r[0] + r[1]) / 2, patron=tuple(r[2])))
    if not bands:
        return [], None
    pesos = collections.Counter()
    for b in bands:
        pesos[(round(b['H'], 1), b['patron'])] += b['x1'] - b['x0']
    (H, patron), _ = pesos.most_common(1)[0]
    bands = [b for b in bands if abs(b['H'] - H) < 0.05 * H]
    # segunda pasada: tramos cortos con el mismo patron
    vistos = {(b['x0'], b['x1'], round(b['y0'], 1)) for b in bands}
    for (x0, x1), ys in grp.items():
        if len(ys) < len(patron):
            continue
        ys = sorted(ys)
        for a in ys:
            if all(any(abs(a + f * H - y) < 0.12 for y in ys) for f in patron):
                k = (x0, x1, round(a, 1))
                if k not in vistos:
                    vistos.add(k)
                    bands.append(dict(x0=x0, x1=x1, y0=a, y1=a + H, H=H, eje=a + H / 2, patron=patron))
    return bands, H


def canaletas(segs, H, mm_pt):
    """canaletas: franjas VACIAS entre dos lineas paralelas largas, con un ancho normalizado (25 a 120 mm) y de largo al
    menos el doble del ancho. Se cortan donde una linea perpendicular cruza toda la franja (union de dos canaletas)."""
    import numpy as np
    A = np.array([[a[0], a[1], b[0], b[1]] for a, b in segs]) if segs else np.zeros((0, 4))
    rawH = [((a[1] + b[1]) / 2, min(a[0], b[0]), max(a[0], b[0])) for a, b in segs if abs(a[1] - b[1]) < 0.05 and abs(a[0] - b[0]) > 0.3]
    rawV = [((a[0] + b[0]) / 2, min(a[1], b[1]), max(a[1], b[1])) for a, b in segs if abs(a[0] - b[0]) < 0.05 and abs(a[1] - b[1]) > 0.3]
    Hl, Vl = _merge(rawH, 0.6), _merge(rawV, 0.6)
    LH = [l for l in Hl if l[2] - l[1] >= 1.5 * H]
    LV = [l for l in Vl if l[2] - l[1] >= 1.5 * H]
    STD = (25, 30, 40, 50, 60, 80, 100, 120)

    def tinta(x0, y0, x1, y1, m=0.4):
        x0 += m; y0 += m; x1 -= m; y1 -= m
        if not len(A):
            return 0.0
        ax, ay, bx, by_ = A[:, 0], A[:, 1], A[:, 2], A[:, 3]
        sel = (np.maximum(ax, bx) > x0) & (np.minimum(ax, bx) < x1) & (np.maximum(ay, by_) > y0) & (np.minimum(ay, by_) < y1)
        tot = 0.0
        for sx, sy, ex, ey in A[sel]:
            dx, dy = ex - sx, ey - sy; u0, u1 = 0.0, 1.0; ok = True
            for p, q in ((-dx, sx - x0), (dx, x1 - sx), (-dy, sy - y0), (dy, y1 - sy)):
                if abs(p) < 1e-12:
                    if q < 0:
                        ok = False; break
                else:
                    t = q / p
                    if p < 0:
                        u0 = max(u0, t)
                    else:
                        u1 = min(u1, t)
            if ok and u1 > u0:
                tot += (u1 - u0) * math.hypot(dx, dy)
        return tot

    def franjas(L, Lperp, horiz):
        out = []
        L = sorted(L)
        for i in range(len(L)):
            for j in range(i + 1, len(L)):
                ca, a0, a1 = L[i]; cb, b0, b1 = L[j]
                w = cb - ca
                if w < 0.6 * H:
                    continue
                if w > 5 * H:
                    break
                if not any(abs(w * mm_pt / s - 1) < 0.04 for s in STD):
                    continue
                o0, o1 = max(a0, b0), min(a1, b1)
                if o1 - o0 < 2.0 * w:
                    continue
                cuts = sorted({c for c, p0, p1 in Lperp if o0 + 0.3 < c < o1 - 0.3 and p0 <= ca + 0.3 and p1 >= cb - 0.3})
                xs = [o0] + cuts + [o1]
                for u0, u1 in zip(xs, xs[1:]):
                    if u1 - u0 < 1.0 * w:
                        continue
                    box = (u0, ca, u1, cb) if horiz else (ca, u0, cb, u1)
                    if tinta(*box) < 0.5 * w:
                        out.append(dict(b=[round(v, 2) for v in box], h=horiz, ex=False, ancho_mm=round(w * mm_pt, 1)))
        return out
    return franjas(LH, Vl, True) + franjas(LV, Hl, False), Hl, Vl


def _toca(a, b, m):
    return a[0] - m <= b[2] and b[0] - m <= a[2] and a[1] - m <= b[3] and b[1] - m <= a[3]


def _placa(core, Hl, Vl, H):
    """rectangulo de la placa (bandeja) que rodea al nucleo (canaletas + rieles): el mas chico armado con lineas largas
    que cubren al menos el 90 % de cada lado"""
    LH = _merge([(c, a0, a1) for c, a0, a1 in Hl], H)
    LV = _merge([(c, a0, a1) for c, a0, a1 in Vl], H)
    LH = [l for l in LH if l[2] - l[1] >= max(4 * H, 0.6 * (core[2] - core[0]))]
    LV = [l for l in LV if l[2] - l[1] >= max(4 * H, 0.6 * (core[3] - core[1]))]
    izq = sorted({round(c, 2) for c, a0, a1 in LV if c <= core[0] + 0.5}, reverse=True)[:10]
    der = sorted({round(c, 2) for c, a0, a1 in LV if c >= core[2] - 0.5})[:10]
    aba = sorted({round(c, 2) for c, a0, a1 in LH if c <= core[1] + 0.5}, reverse=True)[:10]
    arr = sorted({round(c, 2) for c, a0, a1 in LH if c >= core[3] - 0.5})[:10]
    best = None
    for x0 in izq:
        for x1 in der:
            for y0 in aba:
                for y1 in arr:
                    area = (x1 - x0) * (y1 - y0)
                    if best and area >= best[0]:
                        continue
                    if min(_cobertura(LV, x0, y0, y1), _cobertura(LV, x1, y0, y1), _cobertura(LH, y0, x0, x1), _cobertura(LH, y1, x0, x1)) >= 0.9:
                        best = (area, [x0, y0, x1, y1])
    return best[1] if best else None


def _etiquetas(pg, known):
    out = []
    for w in pg['words']:
        m = re.fullmatch(r'-([A-Z0-9][\w\-]*)', w['text'])
        if m and (not known or m.group(1) in known):
            out.append(dict(tag=m.group(1), leido=w['text'], x=_centro(w['bbox'])[0], y=_centro(w['bbox'])[1], bbox=w['bbox']))
    return out


def layout(pdf_path, known_tags, log=print, dec=None):
    """hoja de bandejas del PDF de EPLAN -> el mismo dict que topo.layout: pag, region (placa de la bandeja principal),
    escala (riel DIN de 35 mm), filas (ejes de los rieles), comp {tag: ubic BANDEJA/LI, fila, x, y, lateral, estacion},
    ductos [{b, h, ex}] para ruteo.Net. La bandeja principal es la placa con mas aparatos; las otras placas (con titulo
    'LATERAL IZQUIERDA / DERECHA') y todo lo que no esta en una placa van como LI (o LD). Lo que esta en la placa
    principal pero fuera de la zona de rieles y canaletas (zona hidraulica) se marca para otra estacion (E8)."""
    import pypdf
    from pdfvec import page_strokes
    known = set(known_tags or [])
    pgs = leer(pdf_path)
    for pg in pgs:
        pg['_meta'] = pg.get('_meta') or rotulo(pg)
    doc, rev = documento(pdf_path)
    mapeo = cargar_mapeo(doc, rev)
    lista = {f['pag'] for f in lista_conexiones(pgs)}
    cand = sorted(((len({e['tag'] for e in _etiquetas(pg, known)}), pg['index']) for pg in pgs if pg['index'] not in lista), reverse=True)
    if mapeo and mapeo.get('pagina_bandejas'):
        cand.sort(key=lambda c: c[1] != mapeo['pagina_bandejas'])
    cand = [c for c in cand if c[0] >= 3][:4]
    proc = copia_proceso(pdf_path)
    reader = pypdf.PdfReader(proc)
    best = None
    for n_et, pi in cand:
        st = page_strokes(reader, pi - 1, {})
        segs = [(p[i], p[i + 1]) for _, _, p in st for i in range(len(p) - 1)]
        bands, H = rieles(segs)
        log(f'Hoja {pi}: {n_et} aparatos, {len(bands)} tramos de riel')
        if bands:
            best = dict(pag=pi, segs=segs, bands=bands, H=H, n=n_et)
            break
    if not best:
        # sin hoja de bandejas el instructivo sale sin cables en la bandeja (todo a pendientes): el aviso tiene que verse
        aviso = ('no se encontró la hoja de bandejas en el PDF (la vista de las placas con los rieles DIN y las canaletas): '
                 'sin ella todos los cables quedan como pendientes; exportala desde EPLAN en el mismo PDF o cargá el topográfico aparte')
        log('No se encontró la hoja de bandejas en el PDF')
        return dict(pag=None, comp={}, vistas=[], filas=[], ductos=[], region=None, escala=None, avisos=[aviso],
                    eplan=dict(documento=doc, revision=rev, mapeo=(mapeo or {}).get('_archivo'), ex=None, avisos=[aviso], sin_bandejas=True))
    pg = pgs[best['pag'] - 1]
    H = best['H']
    from topo import snap_escala, RIEL_MM
    escala = snap_escala(RIEL_MM / H)
    ductos, Hl, Vl = canaletas(best['segs'], H, escala)
    # las franjas que caen dentro de un riel (el canal del perfil) no son canaletas
    ductos = [d for d in ductos if not any(b['x0'] - 0.5 <= d['b'][0] and d['b'][2] <= b['x1'] + 0.5 and b['y0'] - 0.5 <= d['b'][1] and d['b'][3] <= b['y1'] + 0.5
                                           for b in best['bands'])]
    # redes de canaletas (se tocan) que tienen rieles: cada una es una bandeja
    W0 = sorted(min(d['b'][2] - d['b'][0], d['b'][3] - d['b'][1]) for d in ductos)
    toque = 0.105 * (W0[len(W0) // 2] if W0 else 28.5)
    par = list(range(len(ductos)))
    def f_(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    for i in range(len(ductos)):
        for j in range(i):
            if _toca(ductos[i]['b'], ductos[j]['b'], toque):
                par[f_(i)] = f_(j)
    redes = collections.defaultdict(list)
    for i, d in enumerate(ductos):
        redes[f_(i)].append(d)
    # cada tramo de riel va con la red de canaletas que lo rodea (canaletas arriba / abajo a menos de 4 perfiles, o una
    # vertical pegada a su punta); las redes sin rieles (lineas de un aparato que parecen una canaleta) no son bandejas
    redes = list(redes.values())
    def puntaje(b, ds):
        n = 0
        for d in ds:
            x0, y0, x1, y1 = d['b']
            if d['h'] and x0 <= b['x1'] + 0.5 and x1 >= b['x0'] - 0.5 and min(abs(y0 - b['y1']), abs(b['y0'] - y1)) <= 4 * H:
                n += 1
            elif not d['h'] and y0 <= b['eje'] <= y1 and min(abs(x0 - b['x1']), abs(b['x0'] - x1)) <= 1.0 * H:
                n += 1
        return n
    asig = collections.defaultdict(list); sueltos = []
    for b in best['bands']:
        pts = [(puntaje(b, ds), -i) for i, ds in enumerate(redes)]
        mejor = max(pts) if pts else (0, 0)
        if mejor[0] > 0:
            asig[-mejor[1]].append(b)
        else:
            sueltos.append(b)
    bandejas = []
    for i, ds in enumerate(redes):
        rs = asig.get(i)
        if rs:
            bb = _bb_union([d['b'] for d in ds])
            bandejas.append(dict(ductos=ds, rieles=rs, nucleo=_bb_union([bb] + [(b['x0'], b['y0'], b['x1'], b['y1']) for b in rs])))
    if sueltos:      # rieles sin canaletas alrededor: una bandeja por grupo de rieles que se solapan en x
        grupos = []
        for b in sorted(sueltos, key=lambda b: b['x0']):
            if grupos and b['x0'] <= max(x['x1'] for x in grupos[-1]) + 4 * H:
                grupos[-1].append(b)
            else:
                grupos.append([b])
        for g in grupos:
            bandejas.append(dict(ductos=[], rieles=g, nucleo=_bb_union([(b['x0'], b['y0'], b['x1'], b['y1']) for b in g])))
    etiquetas = _etiquetas(pg, known)
    for t in bandejas:
        t['placa'] = _placa(t['nucleo'], Hl, Vl, H)
        t['region'] = t['placa'] or [t['nucleo'][0] - 2 * H, t['nucleo'][1] - 2 * H, t['nucleo'][2] + 2 * H, t['nucleo'][3] + 2 * H]
        t['etiquetas'] = [e for e in etiquetas if _dentro((e['x'], e['y']), t['region'])]
        # titulo de la placa: el renglon de texto grande que esta arriba y centrado sobre ella
        tits = [l for l in pg['lines'] if l['ang'] == 0 and l['bbox'][1] >= t['region'][3] - 2 and t['region'][0] <= _centro(l['bbox'])[0] <= t['region'][2]
                and len(l['text']) > 6 and not re.fullmatch(r'-\S+', l['text'])]
        t['titulo'] = min(tits, key=lambda l: l['bbox'][1])['text'] if tits else ''
    principal = max(bandejas, key=lambda t: (len({e['tag'] for e in t['etiquetas']}), not LATERAL_RE.search(t['titulo'])))
    # filas (rieles) de la principal: tramos con el mismo eje, de arriba abajo
    filas = []
    for b in sorted(principal['rieles'], key=lambda b: -b['eje']):
        if filas and abs(filas[-1]['ejes'][-1] - b['eje']) < 1.2 * H:
            filas[-1]['ejes'].append(b['eje'])
        else:
            filas.append(dict(ejes=[b['eje']]))
    ejes = [round(sum(f['ejes']) / len(f['ejes']), 2) for f in filas]
    zona = principal['nucleo']
    m = 0.5 * H
    zona_e = (zona[0] - m, zona[1] - m, zona[2] + m, zona[3] + m)
    comp = {}
    avisos = []
    for e in sorted(etiquetas, key=lambda e: (e['tag'], e['x'])):
        if e['tag'] in comp and comp[e['tag']]['ubic'] == 'BANDEJA':
            continue
        c = dict(ubic='LI', fila=None, x=round(e['x'], 1), y=round(e['y'], 1), leido=e['leido'])
        t = next((t for t in bandejas if _dentro((e['x'], e['y']), t['region'])), None)
        if t is principal:
            if _dentro((e['x'], e['y']), zona_e) and ejes:
                c.update(ubic='BANDEJA', fila=min(range(len(ejes)), key=lambda i: abs(ejes[i] - e['y'])) + 1)
            else:
                c.update(estacion='E8', nota='en la placa de la bandeja principal pero fuera de la zona de rieles y canaletas (zona hidráulica): se cablea en E8')
        elif t is not None:
            lm = LATERAL_RE.search(t['titulo'] or '')
            c['lateral'] = ('DERECHO' if lm.group(1).upper() == 'DER' else 'IZQUIERDO') if lm else 'IZQUIERDO'
            c['nota'] = f"en la {t['titulo'].lower() or 'otra bandeja'}"
        comp[e['tag']] = c
    # canaletas de intrinsecos: del mapeo verificado (si coincide el documento) o de la vista a color de las bandejas
    dl = [dict(b=d['b'], h=d['h'], ex=False) for d in principal['ductos']]
    fuente_ex = None
    if mapeo and mapeo.get('canaletas_intrinsecas'):
        for d in dl:
            if any(_iou(d['b'], b) > 0.6 for b in mapeo['canaletas_intrinsecas']):
                d['ex'] = True
        fuente_ex = 'mapeo verificado'
    else:
        try:
            azules = canaletas_azules(pdf_path, pgs, best['pag'], principal['etiquetas'])
        except Exception as ex_:           # nunca frena el topografico
            azules = []; avisos.append(f'no se pudo leer la vista a color de las bandejas ({ex_})')
        if azules:
            for d in dl:
                if any(_frac_dentro(d['b'], a) > 0.6 for a in azules):
                    d['ex'] = True
            fuente_ex = 'vista a color de las bandejas'
    # zona hidraulica y empalmes que se cablean en otra estacion (mapeo verificado)
    for tag, est in ((mapeo or {}).get('estaciones_tag') or {}).items():
        c = comp.setdefault(tag, dict(ubic='LI', fila=None, x=None, y=None, leido=''))
        if c.get('ubic') != 'BANDEJA':
            c['estacion'] = est
            c['nota'] = c.get('nota') or f'se cablea en {est} (mapeo verificado)'
    region = [round(v, 2) for v in principal['region']]
    if not mapeo:
        avisos.append('sin mapeo verificado para este documento: los puntos de los bornes son aproximados (ajustalos en el visor con 📍)')
    log(f'Bandejas: hoja {best["pag"]}, {len(ejes)} rieles, {len(dl)} canaletas ({sum(d["ex"] for d in dl)} de intrínsecos'
        + (f', {fuente_ex}' if fuente_ex else '') + f'), escala {escala} mm/pt')
    # (las canaletas de cada vista: la estacion E8 rutea los cables de las bandejas laterales)
    vistas = [dict(box=[round(v, 2) for v in t['region']], rails=[round(b['eje'], 2) for b in t['rieles']], titulo=t['titulo'],
                   ductos=dl if t is principal else [dict(b=[round(v, 2) for v in d['b']], h=d['h'], ex=False) for d in t['ductos']])
              for t in bandejas]
    return dict(pag=best['pag'], comp=comp, vistas=vistas, bandeja=bandejas.index(principal), size=[pg['w'], pg['h']], region=region,
                escala=escala, escala_fuente='riel DIN 35 mm', perfil_riel_pt=round(H, 2), ductos=dl, filas=ejes,
                eplan=dict(documento=doc, revision=rev, mapeo=(mapeo or {}).get('_archivo'), ex=fuente_ex, avisos=avisos))


def _iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0


def _frac_dentro(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    area = (a[2] - a[0]) * (a[3] - a[1])
    return ix * iy / area if area > 0 else 0.0


def canaletas_azules(pdf_path, pgs, pag_bandejas, etiquetas):
    """zonas azules (canaletas de circuitos intrinsecamente seguros) de la VISTA A COLOR de las bandejas, llevadas a las
    coordenadas de la hoja de bandejas. La vista a color es otra hoja con las mismas etiquetas '-TAG' (EPLAN la exporta
    como imagen): la transformacion sale de las etiquetas que estan en las dos hojas. -> [[x0, y0, x1, y1]]"""
    import numpy as np
    pos = {}
    for e in etiquetas:
        pos.setdefault(e['tag'], (e['x'], e['y']))
    mejor = None
    for pg in pgs:
        if pg['index'] == pag_bandejas:
            continue
        otras = {}
        for e in _etiquetas(pg, set(pos)):
            otras.setdefault(e['tag'], (e['x'], e['y']))
        comun = [t for t in otras if t in pos]
        if len(comun) >= 8 and (mejor is None or len(comun) > len(mejor[1])):
            mejor = (pg, comun, otras)
    if not mejor:
        return []
    pg, comun, otras = mejor
    # x' = ax * x + bx, y' = ay * y + by (misma vista, otra escala y otro lugar en la hoja)
    X = np.array([otras[t][0] for t in comun]); Y = np.array([otras[t][1] for t in comun])
    Xp = np.array([pos[t][0] for t in comun]); Yp = np.array([pos[t][1] for t in comun])
    sel = np.ones(len(comun), bool)
    for _ in range(3):              # ajuste robusto: fuera las etiquetas que en la otra vista estan en otro lugar
        if sel.sum() < 6:
            return []
        ax, bx = np.polyfit(X[sel], Xp[sel], 1); ay, by_ = np.polyfit(Y[sel], Yp[sel], 1)
        r = np.maximum(np.abs(ax * X + bx - Xp), np.abs(ay * Y + by_ - Yp))
        sel = r < max(3.0, 2.5 * np.median(r))
    if sel.sum() < 6 or np.max(r[sel]) > 4:
        return []
    import pypdfium2 as pdfium
    esc = 2.0
    with PDFIUM_LOCK:
        doc = pdfium.PdfDocument(pdf_path)
        try:
            p = doc[pg['index'] - 1]
            try:
                img = np.asarray(p.render(scale=esc).to_pil().convert('RGB')).astype(int)
            finally:
                p.close()
        finally:
            doc.close()
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    mask = ((b > 140) & (r < 60) & (g < 90)).astype('uint8')
    import cv2
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)
    out = []
    hpx = img.shape[0]
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 400 or min(w, h) < 8:
            continue
        x0, x1 = x / esc + pg['x0'], (x + w) / esc + pg['x0']
        y1, y0 = (hpx - y) / esc + pg['y0'], (hpx - y - h) / esc + pg['y0']
        out.append([round(float(ax * x0 + bx), 2), round(float(ay * y0 + by_), 2), round(float(ax * x1 + bx), 2), round(float(ay * y1 + by_), 2)])
    return out


# ------------------------------------------------------------------ puntos de los bornes para el instructivo
def aplicar_puntos(res, lay, dir_trabajo):
    """lay['bornes'] (+ bornes_conf, bornes_nota, renombrar) con los puntos del MAPEO VERIFICADO del documento, si hay
    y el trabajo no tiene su propio bornes.json (manda el del trabajo, como en los planos de AutoCAD). Devuelve el
    resumen para ins['mapeo']."""
    import bornes as mb
    mapeo = getattr(res, 'mapeo_verificado', None)
    le = lay.get('eplan') if isinstance(lay.get('eplan'), dict) else {}     # (layouts viejos: eplan=True)
    sin_bandejas = bool(le.get('sin_bandejas')) or not lay.get('pag')
    if mapeo and (str(le.get('documento') or '').upper() != str(mapeo.get('documento')).upper()
                  or (mapeo.get('pagina_bandejas') and lay.get('pag') != mapeo.get('pagina_bandejas'))):
        mapeo = None              # el topografico no es la hoja de bandejas de ese documento: los puntos no sirven
    avisos_man = []           # un bornes.json / correcciones.json ilegible se ignora, pero con aviso (no en silencio)
    manual, ren_m = mb.leer_manuales(dir_trabajo, avisos_man)
    # (un bornes.json ilegible se ignora: no tapa el mapeo verificado)
    hay_bj = (os.path.exists(os.path.join(dir_trabajo, 'bornes.json'))
              and not any(str(a).startswith('bornes.json ilegible') for a in avisos_man))
    avisos = avisos_man + list(le.get('avisos') or lay.get('avisos') or [])
    if sin_bandejas and not avisos:
        avisos.append('no se encontró la hoja de bandejas en el PDF: sin ella todos los cables quedan como pendientes')
    bornes, conf, nota = {}, {}, {}
    n = collections.Counter()
    if mapeo and not hay_bj:
        puntas = mapeo.get('puntas') or {}
        comp = lay.get('comp') or {}
        for num, c in (res.conductores or {}).items():
            for nid, e in c['nodes'].items():
                if not e.get('d'):
                    continue
                f = next((f for f in res.filas_conexiones if f.get('cable') == num and e['d'] in (f['d1'], f['d2'])), None)
                p = puntas.get(clave_punta(e['d'], f['num'] if f else num))
                if not p or p.get('x') is None:
                    continue
                k = f"{e['texto']}#{num}"
                bornes[k] = [round(float(p['x']), 2), round(float(p['y']), 2), p.get('r')]
                cf = 'alta' if p.get('conf') == 'alta' else 'media'
                conf[k] = cf
                if cf != 'alta' and p.get('como'):
                    nota[k] = p['como'][:400]
                if (comp.get(e.get('tag_base')) or {}).get('ubic') == 'BANDEJA':
                    n[cf] += 1
        avisos += list(mapeo.get('avisos') or [])
    elif mapeo and hay_bj:
        avisos.append('el trabajo tiene su propio bornes.json: manda sobre el mapeo verificado')
    bornes.update(manual)
    lay['bornes'] = bornes
    lay['renombrar'] = dict(ren_m)
    lay['bornes_conf'] = {k: v for k, v in conf.items() if k not in manual}
    lay['bornes_nota'] = {k: v for k, v in nota.items() if k not in manual}
    lay['renombrar_auto'] = {}
    if not mapeo and not sin_bandejas:
        avisos.append('sin mapeo verificado para este plano de EPLAN: cada cable sale de un punto aproximado del aparato')
    # textos de la regla general (sin mapeo verificado, o puntas que el mapeo no tiene): lo que el PDF no dice
    conf_txt = [(num, e) for num, c in (res.conductores or {}).items() for e in c['nodes'].values() if e.get('a_confirmar')]
    if conf_txt:
        ej = '; '.join(f"{num}: {e['texto']}" for num, e in conf_txt[:6])
        avisos.append(f'los TEXTOS de {len(conf_txt)} puntas salen de una regla general (tipo de bornera de las hojas de hileras de bornes '
                      f'o de la lista de artículos, lado ARRIBA/ABAJO, pines que EPLAN no da): marcados «a confirmar» (ej. {ej}'
                      + ('…' if len(conf_txt) > 6 else '') + ')')
    titulo = (f"Mapeo verificado {mapeo.get('documento')} rev {mapeo.get('revision')}" if mapeo else
              'Plano de EPLAN sin hoja de bandejas' if sin_bandejas else 'Plano de EPLAN sin mapeo verificado')
    return dict(version=f'eplan-{VERSION}', titulo=titulo, sin_bandejas=sin_bandejas,
                modelos={}, avisos=avisos, segundos=0, de_cache=False, error=None,
                materiales='mapeo verificado del producto' if mapeo else None,
                n_puntos=dict(alta=n['alta'], media=n['media'], baja=0), usados=sum(n.values()), manuales=len(manual))


def excel_extra(res, path):
    """agrega al Excel del listado la hoja 'Lista de conexiones (EPLAN)' con cada renglon y sus textos del taller"""
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    wb = load_workbook(path)
    ws = wb.create_sheet('Lista de conexiones (EPLAN)')
    ws.append(['Renglón', 'Hoja', 'Nº cable', 'Destino 1 (EPLAN)', 'Destino 2 (EPLAN)', 'Texto taller 1', 'Texto taller 2', 'Color', 'Sección (mm²)', 'Nota'])
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='1F4E78'); c.alignment = Alignment(wrap_text=True)
    def numero(s):
        """'1101' -> 1101 y '2,5' -> 2.5 (numeros de verdad en el Excel, para ordenar y filtrar); lo demas, texto"""
        s = str(s or '').strip()
        if re.fullmatch(r'\d+', s):
            return int(s)
        if re.fullmatch(r'\d+(?:[.,]\d+)?', s):
            return float(s.replace(',', '.'))
        return s or None
    for f in res.filas_conexiones:
        c = (res.conductores or {}).get(f.get('cable')) or {}
        nd = lambda d: (c.get('nodes', {}).get(d) or {}) if d else {}
        nota = 'unión interna del aparato (no es un cable)' if not f['num'] and f['d1'] == f['d2'] else ''
        dudas = [f"{nd(d).get('texto')}: {nd(d)['a_confirmar']}" for d in (f['d1'], f['d2']) if nd(d).get('a_confirmar')]
        if dudas:
            nota = '; '.join([nota] * bool(nota) + ['a confirmar: ' + ' | '.join(dudas)])
        ws.append([f['fila'], f['hoja'], numero(f['num']) if f['num'] else f.get('cable', ''), f['d1'] or '', f['d2'] or '',
                   nd(f['d1']).get('texto', ''), nd(f['d2']).get('texto', ''), f['color_txt'], numero(f['sec']), nota])
    for i, w in enumerate([9, 8, 14, 22, 22, 22, 22, 16, 12, 40], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
    wb.save(path)
