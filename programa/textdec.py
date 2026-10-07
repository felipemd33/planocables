"""Decodificador de texto vectorial: agrupa trazos en renglones y caracteres,
reconoce cada caracter por su firma exacta (diccionario de glifos) y recurre
al OCR solo para los renglones con caracteres desconocidos."""
import math, collections, json, os

from planocables.base.geom import bbox, DSU      # (siguen siendo textdec.bbox / textdec.DSU)

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT_EXCLUDE_OPS = {'n'}   # los rellenos se incluyen: fuentes TrueType exportadas como contornos
OCR_FIX = {'一': '-', '十': '+', '：': ':', '（': '(', '）': ')', '，': ',', '。': '.', '－': '-', '—': '-'}

ROT = {0: lambda x, y: (x, y), 90: lambda x, y: (y, -x), 270: lambda x, y: (-y, x), 180: lambda x, y: (-x, -y)}
UNROT = {0: lambda x, y: (x, y), 90: lambda x, y: (-y, x), 270: lambda x, y: (y, -x), 180: lambda x, y: (-x, -y)}


def maxdim(p):
    x0, y0, x1, y1 = bbox(p); return max(x1 - x0, y1 - y0)


def estimate_H(strokes):
    c = collections.Counter()
    for p in strokes:
        if len(p) > 2:
            m = round(maxdim(p), 1)
            if 2 < m < 40:
                c[m] += 1
    if not c:
        return None
    top = c.most_common(1)[0][1]
    return max(h for h, n in c.items() if n >= 0.35 * top)


def estimate_H_all(strokes):
    """como estimate_H pero contando tambien los trazos rectos (palo del 4, la I...)"""
    c = collections.Counter(round(maxdim(p), 1) for p in strokes if 2 < maxdim(p) < 40)
    if not c:
        return None
    top = c.most_common(1)[0][1]
    return max(h for h, n in c.items() if n >= 0.35 * top)


def is_text_stroke(p, H):
    x0, y0, x1, y1 = bbox(p)
    if max(x1 - x0, y1 - y0) > 1.7 * H:
        return False
    if len(p) == 2:
        dx, dy = abs(p[1][0] - p[0][0]), abs(p[1][1] - p[0][1])
        if (dx < 0.01 or dy < 0.01) and math.hypot(dx, dy) > 1.12 * H:
            return False
    return True


def group(strokes, t):
    n = len(strokes); bbs = [bbox(p) for p in strokes]
    cell = max(20.0, 4 * t); grid = collections.defaultdict(list)
    for i, (x0, y0, x1, y1) in enumerate(bbs):
        for gx in range(int((x0 - t) // cell), int((x1 + t) // cell) + 1):
            for gy in range(int((y0 - t) // cell), int((y1 + t) // cell) + 1):
                grid[(gx, gy)].append(i)
    d = DSU(n)
    for lst in grid.values():
        for a in range(len(lst)):
            A = bbs[lst[a]]
            for b in range(a + 1, len(lst)):
                B = bbs[lst[b]]
                if A[0] - t <= B[2] and B[0] - t <= A[2] and A[1] - t <= B[3] and B[1] - t <= A[3]:
                    d.u(lst[a], lst[b])
    g = collections.defaultdict(list)
    for i in range(n):
        g[d.f(i)].append(i)
    return list(g.values())


def canon(block, ang):
    f = ROT[ang]
    return [[f(x, y) for x, y in p] for p in block]


def split_lines(cw, H):
    ivs = sorted((bbox(p)[1], bbox(p)[3], k) for k, p in enumerate(cw))
    bands = []
    for y0, y1, k in ivs:
        if bands and y0 <= bands[-1][1] + 0.08 * H:
            bands[-1][1] = max(bands[-1][1], y1); bands[-1][2].append(k)
        else:
            bands.append([y0, y1, [k]])
    changed = True
    while changed and len(bands) > 1:
        changed = False
        for i, b in enumerate(bands):
            if b[1] - b[0] < 0.5 * H:
                if i == 0: j = 1
                elif i == len(bands) - 1: j = i - 1
                else: j = i - 1 if b[0] - bands[i - 1][1] < bands[i + 1][0] - b[1] else i + 1
                o = bands[j]; o[0] = min(o[0], b[0]); o[1] = max(o[1], b[1]); o[2] += b[2]
                bands.pop(i); changed = True; break
    return [[cw[k] for k in b[2]] for b in sorted(bands, key=lambda b: -b[1])]


def split_chars(cw, H):
    items = sorted(cw, key=lambda p: bbox(p)[0])
    chars, cur, cx1 = [], [], None
    for p in items:
        x0, _, x1, _ = bbox(p)
        if cur and x0 <= cx1 + 0.02 * H:
            cur.append(p); cx1 = max(cx1, x1)
        else:
            if cur: chars.append(cur)
            cur = [p]; cx1 = x1
    if cur: chars.append(cur)
    return chars


def line_metrics(chars, H0):
    bots = collections.Counter(round(min(bbox(p)[1] for p in c) / (0.05 * H0)) for c in chars)
    base = bots.most_common(1)[0][0] * 0.05 * H0
    hs = [max(bbox(p)[3] for p in c) - base for c in chars
          if abs(min(bbox(p)[1] for p in c) - base) < 0.08 * H0]
    H = max(hs) if hs else H0
    if len(chars) < 2 or H < 0.8 * H0 or H > 1.25 * H0:
        H = H0
    return base, H


def normalize(char, H, base):
    x0 = min(bbox(p)[0] for p in char)
    return [[((x - x0) / H, (base + H - y) / H) for x, y in p] for p in char]


def sig(norm, g=20):
    segs = []
    for p in norm:
        q = tuple((round(x * g), round(y * g)) for x, y in p)
        if len(q) > 2 and q[0] == q[-1]:
            body = q[:-1]; k = body.index(min(body)); body = body[k:] + body[:k]
            rb = tuple(reversed(body)); k2 = rb.index(min(rb)); rb = rb[k2:] + rb[:k2]
            q = min(body, rb) + (min(body, rb)[0],)
        else:
            q = min(q, tuple(reversed(q)))
        qq = [q[0]]
        for pt in q[1:]:
            if pt != qq[-1]: qq.append(pt)
        segs.append(tuple(qq))
    return tuple(sorted(set(segs)))


def render_line(line, H, px=40, pad=12):
    import numpy as np, cv2          # solo para el OCR: sin numpy ni opencv igual cargan textdec, wires, core...
    x0, y0, x1, y1 = bbox([pt for p in line for pt in p]); s = px / H
    W = int((x1 - x0) * s) + 2 * pad; Hh = int((y1 - y0) * s) + 2 * pad
    img = np.full((max(Hh, 24), max(W, 24), 3), 255, np.uint8)
    for p in line:
        pts = np.array([[(x - x0) * s + pad, (y1 - y) * s + pad] for x, y in p], np.int32)
        cv2.polylines(img, [pts], False, (0, 0, 0), 2, cv2.LINE_AA)
    return img


class Decoder:
    def __init__(self, dict_path=None, use_ocr=True):
        dict_path = dict_path or os.path.join(HERE, 'glyphdict.json')
        raw = json.load(open(dict_path, encoding='utf-8')) if os.path.exists(dict_path) else {}
        import ast
        self.d = {ast.literal_eval(k): v for k, v in raw.items()}
        self._ocr = None; self.use_ocr = use_ocr
        self.stats = collections.Counter()
        # memoria de OCR: un renglon con exactamente los mismos trazos ya leido no se vuelve a leer
        self.cache_path = os.path.join(HERE, 'ocr_cache.json')
        try:
            self.cache = json.load(open(self.cache_path, encoding='utf-8'))
        except Exception:
            self.cache = {}
        self._cache_dirty = False

    @property
    def ocr(self):
        if self._ocr is None:
            from rapidocr import RapidOCR
            self._ocr = RapidOCR(params={'Global.log_level': 'error'})
        return self._ocr

    @staticmethod
    def line_key(line, H):
        x0, y0, _, _ = bbox([pt for p in line for pt in p])
        g = 0.05 * H
        shape = sorted(tuple((round((x - x0) / g), round((y - y0) / g)) for x, y in p) for p in line)
        import hashlib
        return hashlib.md5(repr(shape).encode()).hexdigest()

    def ocr_line(self, line, H):
        k = self.line_key(line, H)
        if k in self.cache:
            self.stats['ocr-memoria'] += 1
            t, sc = self.cache[k]
            return t, sc
        res = self.ocr(render_line(line, H), use_det=False, use_cls=False, use_rec=True)
        out = ('', 0.0) if not res.txts else (''.join(OCR_FIX.get(c, c) for c in res.txts[0]).replace(' ', ''), float(res.scores[0]))
        self.cache[k] = list(out); self._cache_dirty = True
        return out

    def save_cache(self):
        if not self._cache_dirty:
            return
        if os.environ.get('PLANOCABLES_MEMORIA_OCR') == 'solo-lectura':
            return      # pruebas y otra app: lo aprendido queda en la memoria de este Decoder, no se escribe el archivo
        try:
            tmp = self.cache_path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False)
            os.replace(tmp, self.cache_path)
            self._cache_dirty = False
        except Exception:
            pass

    def lookup(self, char, Hl, base):
        return self.d.get(sig(normalize(char, Hl, base)))

    def lines_for(self, block, H, ang):
        out = []
        cw = canon(block, ang)
        self._back = {id(c): id(o) for c, o in zip(cw, block)}
        for line in split_lines(cw, H):
            chars = split_chars(line, H)
            base, Hl = line_metrics(chars, H)
            labs = [self.lookup(c, Hl, base) for c in chars]
            out.append((line, chars, base, Hl, labs))
        return out

    def lee_entero(self, block, H):
        """el bloque se lee ENTERO con el diccionario a la altura H (a 0 o 90 grados), sin OCR"""
        for a in (0, 90):
            ls = self.lines_for(block, H, a)
            if ls and all(l is not None and not l.startswith('\x00') for line in ls for l in line[4]):
                return True
        return False

    def decode_block(self, block, H):
        x0, y0, x1, y1 = bbox([pt for p in block for pt in p])
        pref = [0, 90] if (x1 - x0) >= (y1 - y0) else [90, 0]
        if len(split_chars(block, H)) == 1 and len(split_chars(canon(block, 90), H)) == 1:
            pref = [0, 90]   # caracter suelto: se asume horizontal salvo que no se reconozca

        def attempt(a):
            ls = self.lines_for(block, H, a)
            n = sum(len(l[4]) for l in ls); k = sum(1 for l in ls for x in l[4] if x)
            return (k / n if n else 0, n, ls, dict(self._back))
        tried = {a: attempt(a) for a in pref}
        q0 = tried[pref[0]][0]; q1 = tried[pref[1]][0]
        # la orientacion alternativa solo gana si lee claramente mejor
        ang = pref[1] if (q1 > q0 + 0.25 or (q1 == 1.0 and q0 < 0.75)) else pref[0]
        q, n, lines, back = tried[ang]
        if q < 0.5 and n >= 4:   # texto boca abajo o girado 270: solo en textos largos
            for alt in (270, 180):
                qa, na, al, ba = attempt(alt)
                if na and qa == 1.0:
                    ang, lines, back = alt, al, ba; break
        results = []
        for line, chars, base, Hl, labs in lines:
            txt, src = self.resolve(line, Hl, labs)
            xs0 = min(bbox(p)[0] for p in line); xs1 = max(bbox(p)[2] for p in line)
            cpos = [(min(bbox(p)[0] for p in c), max(bbox(p)[2] for p in c)) for c in chars]
            if len(cpos) != len(txt):  # texto del OCR con otra longitud: repartir uniformemente
                w = (xs1 - xs0) / max(len(txt), 1)
                cpos = [(xs0 + i * w, xs0 + (i + 1) * w) for i in range(len(txt))]
            results.append(dict(text=txt, src=src, ang=ang, H=Hl, base=base, x0=xs0, x1=xs1, cpos=cpos,
                                bbox=self.pdf_bbox(line, ang), nchars=len(chars),
                                ids={back.get(id(p)) for p in line}))
        return results

    def resolve(self, line, Hl, labs):
        amb = [l is not None and l.startswith('\x00') for l in labs]
        if all(l is not None for l in labs) and not any(amb):
            self.stats['dict'] += 1
            return ''.join(labs), 'dict'
        o, sc = ('', 0.0)
        if self.use_ocr:
            o, sc = self.ocr_line(line, Hl)
        if len(o) == len(labs) and sc > 0.5:
            out = []
            for l, oc in zip(labs, o):
                if l is None: out.append(oc)
                elif l == '\x00Il': out.append(oc if oc in 'Il1|' else 'l')
                elif l.startswith('\x00case:'): out.append(oc if oc in l[6:] else l[6])
                else: out.append(l)
            self.stats['dict+ocr'] += 1
            return ''.join(out), 'dict+ocr'
        if any(l is None for l in labs):
            if sc > 0.8:
                self.stats['ocr'] += 1
                return o, 'ocr'
        # sin OCR fiable: resolver ambiguos por contexto
        out = []
        for i, l in enumerate(labs):
            if l is None: out.append('?')
            elif l == '\x00Il':
                nb = ''.join(x for x in (labs[i - 1] if i else '', labs[i + 1] if i + 1 < len(labs) else '') if x and not x.startswith('\x00'))
                out.append('l' if nb.islower() else 'I')
            elif l.startswith('\x00case:'): out.append(l[6])
            else: out.append(l)
        self.stats['partial' if '?' in out else 'dict-ctx'] += 1
        return ''.join(out), 'partial' if '?' in out else 'dict-ctx'

    @staticmethod
    def pdf_bbox(line, ang):
        f = UNROT[ang]
        x0, y0, x1, y1 = bbox([pt for p in line for pt in p])
        pts = [f(x0, y0), f(x1, y0), f(x0, y1), f(x1, y1)]
        return bbox(pts)


def page_text(strokes, decoder, skip_layers=()):
    """strokes: [(capa, op, pts)] -> lista de renglones decodificados"""
    by_layer = collections.defaultdict(list); fills = collections.defaultdict(list)
    for l, o, p in strokes:
        if o in TEXT_EXCLUDE_OPS or len(p) < 2 or any(k in l for k in skip_layers):
            continue
        (fills if o in FILL_OPS else by_layer)[l].append(p)
    out = []
    for layer, fl in fills.items():
        out += fill_text(fl, decoder, layer)
    for layer, st in by_layer.items():
        H = estimate_H(st)
        if not H:
            continue
        st = [p for p in st if is_text_stroke(p, H * 2.5)]
        small = [p for p in st if is_text_stroke(p, H)]
        pool = [p for p in st if not is_text_stroke(p, H)]
        groups = []
        for g in group(small, 0.45 * H):
            gs = [small[i] for i in g]
            Hg = estimate_H(gs) or H
            if Hg > 1.1 * H and pool:
                # texto mas alto: recuperar sus trazos largos (palo de la T, la I...)
                x0, y0, x1, y1 = bbox([pt for p in gs for pt in p]); m = 0.6 * Hg
                take = [p for p in pool if is_text_stroke(p, 1.5 * Hg) and
                        bbox(p)[0] <= x1 + m and bbox(p)[2] >= x0 - m and bbox(p)[1] <= y1 + m and bbox(p)[3] >= y0 - m]
                if take:
                    ids = {id(p) for p in take}
                    pool = [p for p in pool if id(p) not in ids]; gs = gs + take
                    Hg = max(Hg, estimate_H_all(gs) or Hg)
            groups.append((gs, Hg if Hg > 1.1 * H else H))
        big_idx = {k for k, (g, h) in enumerate(groups) if h > 1.3 * H}
        big = [p for k in big_idx for p in groups[k][0]] + pool
        groups = [gr for k, gr in enumerate(groups) if k not in big_idx]
        if big:
            Hb = estimate_H(big) or H
            pool_ids = {id(p) for p in pool}
            for g in group(big, 0.45 * Hb):
                gs = [big[i] for i in g]
                if all(id(p) in pool_ids for p in gs):
                    continue   # rayas de corte, lineas sueltas: no son texto
                groups.append((gs, Hb))
        lay = []
        for g, Hg in groups:
            rs = decoder.decode_block(g, Hg)
            if Hg > 1.1 * H and any(r['src'] != 'dict' for r in rs) and decoder.lee_entero(g, H):
                # grupo 'alto' solo por un parentesis ('2)' de 'NC(12)': el ')' mide 1,5 veces el digito): a la altura
                # de la capa se lee entero con el diccionario -> esa lectura (si no, el giro a 90 + OCR leia '2')
                alt = decoder.decode_block(g, H)
                if alt and all(r['src'] == 'dict' for r in alt):
                    rs = alt
            for r in rs:
                r['layer'] = layer
                lay.append(r)
        out += merge_lines(lay)
    return dedupe(out)


def dedupe(lines):
    seen = {}; out = []
    for l in lines:
        b = l['bbox']
        k = (l['text'], l['ang'], round(b[0]), round(b[1]))
        if k in seen:
            seen[k].setdefault('ids', set()).update(l.get('ids', set()))
            continue
        seen[k] = l; out.append(l)
    return out


FILL_OPS = {'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'}


def fill_text(fl, decoder, layer):
    """texto en fuentes TrueType (contornos rellenos): renglones completos por OCR"""
    H = estimate_H(fl)
    if not H or not decoder.use_ocr:
        return []
    fl = [p for p in fl if maxdim(p) < 2.0 * H and maxdim(p) > 0.25 * H]
    out = []
    for g in group(fl, 0.6 * H):
        blk = [fl[i] for i in g]
        x0, y0, x1, y1 = bbox([pt for p in blk for pt in p])
        if len(blk) < 2 and (x1 - x0) < 1.2 * H:
            continue   # punto de union, punta de flecha...
        ang = 0 if (x1 - x0) >= 0.8 * (y1 - y0) else 90
        for line in split_lines(canon(blk, ang), H):
            lx0, ly0, lx1, ly1 = bbox([pt for p in line for pt in p])
            txt, sc = decoder.ocr_line(line, max(ly1 - ly0, 1.0))
            if sc < 0.7 or not any(ch.isalnum() for ch in txt):
                continue
            decoder.stats['ocr-relleno'] += 1
            w = (lx1 - lx0) / max(len(txt), 1)
            out.append(dict(text=txt, src='ocr-relleno', ang=ang, H=(ly1 - ly0), base=ly0, x0=lx0, x1=lx1,
                            cpos=[(lx0 + i * w, lx0 + (i + 1) * w) for i in range(len(txt))],
                            bbox=Decoder.pdf_bbox(line, ang), nchars=len(txt), layer=layer,
                            ids={id(p) for p in blk}))
    return out


def merge_lines(lines):
    """une trozos del mismo renglon (p.ej. el '1' deja un hueco mayor: 'GS851' + '2-EX.22')"""
    out = []
    by_ang = collections.defaultdict(list)
    for r in lines:
        by_ang[r['ang']].append(r)
    for ang, rs in by_ang.items():
        # agrupar por linea base cercana (no por valor redondeado)
        rs.sort(key=lambda r: r['base'])
        rows = []
        for r in rs:
            if rows and abs(r['base'] - rows[-1][-1]['base']) < 0.15 * max(r['H'], rows[-1][-1]['H']):
                rows[-1].append(r)
            else:
                rows.append([r])
        for row in rows:
            row.sort(key=lambda r: r['x0'])
            cur = []
            for r in row:
                r = dict(r); r['cpos'] = list(r['cpos'])
                if cur:
                    p = cur[-1]
                    H = max(p['H'], r['H'])
                    gap = r['x0'] - p['x1']
                    h = min(p['H'], r['H'])
                    ov = min(p['base'] + p['H'], r['base'] + r['H']) - max(p['base'], r['base'])
                    if ((abs(p['H'] - r['H']) < 0.3 * H or ov > 0.6 * h) and abs(p['base'] - r['base']) < 0.15 * h
                            and -0.1 * h <= gap <= 1.3 * h):
                        if gap > 0.55 * h:
                            p['text'] += ' '; p['cpos'].append((p['x1'], r['x0']))
                        p['text'] += r['text']; p['cpos'] += r['cpos']
                        p['ids'] = set(p.get('ids', set())) | set(r.get('ids', set()))
                        p['x1'] = r['x1']; p['nchars'] += r['nchars']; p['H'] = H
                        p['bbox'] = (min(p['bbox'][0], r['bbox'][0]), min(p['bbox'][1], r['bbox'][1]),
                                     max(p['bbox'][2], r['bbox'][2]), max(p['bbox'][3], r['bbox'][3]))
                        if r['src'] != 'dict' and p['src'] == 'dict':
                            p['src'] = r['src']
                        continue
                cur.append(r)
            out += cur
    return out


def sub_bbox(line, i, j):
    """caja en coordenadas PDF de los caracteres [i, j) de un renglon"""
    cp = line['cpos']
    if not cp or len(cp) != len(line['text']):
        return line['bbox']
    i = max(0, min(i, len(cp) - 1)); j = max(i + 1, min(j, len(cp)))
    x0, x1 = cp[i][0], cp[j - 1][1]
    y0, y1 = line['base'] - 0.3 * line['H'], line['base'] + line['H']
    f = UNROT[line['ang']]
    return bbox([f(x0, y0), f(x1, y0), f(x0, y1), f(x1, y1)])
