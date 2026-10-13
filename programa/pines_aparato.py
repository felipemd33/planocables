"""PINES DE UN APARATO CON BORNERA NUMERADA (estacion E8, etapa E8-7, 2026-10-09, pedido del taller: «que se pueda hacer
el mapeo automatico de la placa: las referencias son las mismas; a la punta del cable en la vista de la placa agregarle
la aclaracion del pin que va (pagina 21)»).

1. FUNCIONAL (filas_funcional): en la hoja donde esta dibujado el simbolo del aparato (la hoja de las puntas de sus
   cables: en el TPT la 21, «Electronic Board (21PCB01)»), las FILAS de pines numerados (circulos o pines redondos
   alineados, cada uno con su numero) y, por cada pin, la aclaracion: su NOMBRE (el texto de su columna, en la celda de
   al lado del numero: 'Signal AI5', 'Battery +', 'DO 1+') y su GRUPO (el recuadro que encierra la columna, del otro lado
   de la celda del nombre: 'AP Analog Input #5', 'Feeder', 'Solenoid Valve #1'; el recuadro de mas afuera, 'Analog
   Input' / 'Digital Output', no se usa). Las celdas son los recuadros cerrados del simbolo, uno pegado al otro.
   El texto de cada celda se vuelve a leer desde sus trazos (_leer_celda: el lector lo leyo pedazo por pedazo y a veces
   giro mal un pedazo chico, el '1' de 'DO 1+', o no leyo una letra grande, la 'AP'): con el diccionario de letras en el
   sentido de la celda (vertical en la del nombre, derecho en la del grupo) y, las letras que no reconoce, con el OCR del
   renglon en memoria del proceso (solo de apoyo: no toca la memoria de OCR del lector, ocr_cache.json); la I / l y las
   mayusculas de la misma forma, por contexto ('AI6', 'DI 9-', 'TX(I)'); el '0' que puso el OCR donde va la letra O
   ('RX(0)' -> 'RX(O)', _cero_o); un renglon largo sin espacios toma los espacios del OCR si lee las mismas letras
   ('PlungerArrival' -> 'Plunger Arrival'). Si la celda no tiene trazos de letras que se puedan medir, quedan los
   pedazos del lector (_pedazos). En un renglon del grupo con varios rotulos que empiezan igual ('DO #1 ... DO #2')
   manda el renglon con un solo rotulo ('Solenoid Valve #1'). Sin OCR (ocr=False, o sin rapidocr: una copia del motor
   que no lo trae) las letras que el diccionario no reconoce quedan sin leer y el pin lleva 'incompleto' (la aclaracion
   termina en '(texto incompleto)').
2. MAPEO (mapear): cada fila del funcional va a la fila de tornillos del dibujo del aparato en la vista de la puerta
   (topo.puerta_e8: 'bornera' de cada aparato) con la MISMA cantidad de pines, en el mismo orden (de izquierda a
   derecha) y de arriba abajo como en el funcional; el n-esimo pin de la fila va al n-esimo tornillo. Confianza 'alta'
   si cada fila tiene una sola fila del dibujo con esa cantidad y los huecos de las dos coinciden (TPT: la fila de
   arriba con el hueco entre el 53 y el 54); 'media' si no. Un pin sin fila queda en la franja con aviso.
3. PLACA SIN ETIQUETA (reconocer): un cuerpo de la vista de la puerta sin etiqueta ('sin_etiqueta' de topo.puerta_e8:
   75441, la placa E2.5 dibujada sin el tag 21PCB01) es el aparato del funcional cuyas filas de pines coinciden TODAS
   con sus filas de tornillos (cantidad y huecos), si hay uno solo: confianza 'media' (a confirmar).
Nada de esto cambia los textos de E6 ni del listado: la aclaracion va aparte (ins['estacion8'])."""
import collections
import math
import re

from planocables.base.geom import bbox

NUM_RE = re.compile(r'\d{1,3}')
RARO_RE = re.compile(r'[^A-Za-z0-9 #*/+\-.,()°:_&]')       # letras que no son de un rotulo de pin ('Γeedel', 'In|Cu')
HUECO = 1.6               # hueco de una fila: separacion > 1,6 veces la separacion normal entre pines
FILA_MIN = 3              # una fila de pines tiene al menos 3
MAX_CADENA = 3            # celdas pegadas una a otra desde el pin: nombre, grupo y el bloque de afuera
_DEC = {}


def _dec():
    """decodificador solo con el diccionario de letras (sin OCR: no toca la memoria de OCR)"""
    if 'd' not in _DEC:
        from textdec import Decoder
        _DEC['d'] = Decoder(use_ocr=False)
    return _DEC['d']


def _sym(res, pg):
    """los simbolos de la hoja (los mismos que arma instructivo.conductors)"""
    if '_sym' not in pg:
        from instructivo import Symbols, unidad
        cable_nums = {d['num'] for d in getattr(res, 'detail', None) or []}
        tids = set()
        for l in pg['lines']:
            if sum(ch.isalpha() for ch in l['text']) >= 2:
                tids |= set(l.get('ids') or ())
        pg['_sym'] = Symbols(pg.get('strokes', []), tids, u=unidad(res, pg, cable_nums), pw=pg.get('w') or 2383.4, ph=pg.get('h') or 1683.4)
        pg['_sym'].drop_dots(pg.get('strokes', []))
    return pg['_sym']


def _area(b):
    return (b[2] - b[0]) * (b[3] - b[1])


def _dentro(p, b, m=0.0):
    return b[0] - m <= p[0] <= b[2] + m and b[1] - m <= p[1] <= b[3] + m


def _centro(l):
    b = l['bbox']
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def huecos(xs, hueco=HUECO):
    """posiciones de los huecos de una fila (xs ordenadas): indices i con xs[i+1] - xs[i] > hueco * la separacion normal
    (la mediana) -> tupla"""
    if len(xs) < 3:
        return ()
    ds = sorted(b - a for a, b in zip(xs, xs[1:]))
    paso = ds[len(ds) // 2]
    return tuple(i for i, (a, b) in enumerate(zip(xs, xs[1:])) if paso > 0 and b - a > hueco * paso)


# ------------------------------------------------------------------ 1. funcional: filas de pines y su aclaracion
def nodos_aparato(cs, tag):
    """puntas de los cables en un pin numerado del aparato: [(pag, pin, p, num)]"""
    out = []
    for num, c in (cs or {}).items():
        for d in c['nodes'].values():
            if d.get('tipo') == 'borne' and d.get('tag_base') == tag and d.get('p') and d.get('pag') is not None \
                    and NUM_RE.fullmatch(str(d.get('borne') or '').strip()):
                out.append((d['pag'], str(d['borne']).strip(), (float(d['p'][0]), float(d['p'][1])), num))
    return out


def _numero(pg, sym, c, lado=None):
    """numero escrito junto al circulo c (arriba o abajo, centrado): (texto, dy) o None"""
    cx, cy, r = c
    best = None
    for l in pg['lines']:
        t = l['text'].strip()
        if not NUM_RE.fullmatch(t):
            continue
        x, y = _centro(l)
        dy = y - cy
        if abs(x - cx) > 1.1 * r or not (0.6 * r <= abs(dy) <= 3.6 * r):
            continue
        if lado is not None and (dy > 0) != (lado > 0):
            continue
        if best is None or abs(dy) < abs(best[1]):
            best = (t, dy)
    return best


def _cadena(sym, c, paso):
    """celdas (recuadros cerrados) pegadas una a otra desde el pin c hacia el lado de su nombre: [celda del nombre (o
    None si la primera es ancha), grupo, bloque...]. Empieza en el recuadro mas chico que contiene al circulo (la franja
    de los numeros) y sigue por el lado (arriba o abajo) que tiene una celda angosta (la del nombre) pegada."""
    cx, cy, r = c
    tol = max(0.6, 1.0 * getattr(sym, 'u', 1.0))
    con = [b for b in sym.boxes if _dentro((cx, cy), b)]
    ini = min(con, key=_area) if con else (cx - r, cy - r, cx + r, cy + r)
    opciones = []
    for abajo in (True, False):
        seq, cur = [], ini
        while len(seq) < MAX_CADENA:
            cand = [b for b in sym.boxes if not _dentro((cx, cy), b) and b[0] - tol <= cx <= b[2] + tol
                    and (abs(b[3] - cur[1]) < tol if abajo else abs(b[1] - cur[3]) < tol)]
            if not cand:
                break
            b = min(cand, key=_area)
            seq.append(b); cur = b
        if seq:
            opciones.append(((seq[0][2] - seq[0][0]) <= 1.6 * paso, len(seq), seq))
    return max(opciones, key=lambda o: o[:2])[2] if opciones else []


def _labs(sym, l, ang, H):
    """letras del pedazo l leidas con el diccionario girado 'ang' (sin OCR): [lab] (None = no reconocida; '\\x00Il' = I o l)
    o None"""
    by = getattr(sym, '_by_id', {})
    block = [by[i] for i in (l.get('ids') or ()) if i in by]
    if not block:
        return None
    try:
        return [x for line in _dec().lines_for(block, H, ang) for x in line[4]]
    except Exception:                                                      # noqa: BLE001
        return None


def _redecodificar(sym, l, ang, H):
    """vuelve a leer con el diccionario (sin OCR) los trazos del pedazo l girados 'ang' (el '1' de 'DO 1+' que el lector
    leyo derecho). -> texto o None si alguna letra no se reconoce"""
    labs = _labs(sym, l, ang, H)
    if not labs or any(x is None for x in labs):
        return None
    return ''.join(x[6] if x.startswith('\x00case:') else ('I' if x == '\x00Il' else x) for x in labs) or None


def _arreglar_il(sym, l, t):
    """una letra que el diccionario reconoce como I o l (misma forma) y el OCR leyo distinto ('A16' por 'AI6', 'TX(1)' por
    'TX(I)', 'Dl' por 'DI'): l si la palabra sigue (o venia) en minuscula, I si no. Una 'l' leida despues de una
    mayuscula y sin minuscula despues es I ('Dl 9-' -> 'DI 9-'; 'Plunger' queda)"""
    if not t:
        return t
    labs = _labs(sym, l, l['ang'], l.get('H') or 4.0)
    cs = [c for c in t if c != ' ']
    if not labs or len(labs) != len(cs) or '\x00Il' not in labs:
        return t
    out, k = [], 0
    for i, ch in enumerate(t):
        if ch == ' ':
            out.append(ch)
            continue
        if labs[k] == '\x00Il' and ch != 'I':
            prev = out[-1] if out else ''
            nxt = t[i + 1] if i + 1 < len(t) else ''
            if ch != 'l':
                ch = 'l' if (prev.islower() or nxt.islower()) else 'I'
            elif prev.isupper() and not nxt.islower():
                ch = 'I'
        out.append(ch)
        k += 1
    return ''.join(out)


def _ocr(pdf, pi, bb, ang, cache):
    """OCR del recorte (solo de apoyo; no usa la memoria de OCR) -> texto ('' si no se pudo)"""
    if not pdf:
        return ''
    k = (pi, tuple(round(v, 1) for v in bb), ang)
    if k not in cache:
        try:
            import topo
            from textdec import Decoder
            if 'ocr' not in _DEC:
                _DEC['ocr'] = Decoder(use_ocr=True)
            cache[k] = topo.ocr_crop(pdf, pi, bb, ang, _DEC['ocr']) or ''
        except Exception:                                                  # noqa: BLE001
            cache[k] = ''
    return cache[k]


def _raya(l, ang, H):
    """el pedazo es una raya recta a lo largo del renglon de una celda girada 'ang' (el '-' de 'AUX -' en un texto vertical,
    que el lector leyo como una 'I' derecha)"""
    b = l['bbox']; w, h = b[2] - b[0], b[3] - b[1]
    if ang in (90, 270):
        return w < 0.12 * H and 0.3 * H <= h <= 1.0 * H
    return h < 0.12 * H and 0.3 * H <= w <= 1.0 * H


def _pedazos(pg, sym, celda, ocr, nombre=False, estado=None):
    """los textos de la celda: [{text, bbox, ang, H}]. El sentido de la celda: vertical si es alta y tiene texto vertical
    (la del nombre), si no derecho. Los pedazos girados distinto se vuelven a leer con el diccionario girado (o con el OCR
    del recorte), los que tienen letras raras con el OCR del recorte, la I / l que el OCR leyo '1' se arregla, y los
    trazos de letras que ningun texto cubre (la 'AP' grande que el lector no leyo) se leen con el OCR del recorte, por
    manchas de letras pegadas. Los signos sueltos ('-') solo cuentan en la celda del nombre y en su sentido. Sin OCR
    (ocr None), un pedazo con letras raras o trazos de letras sin leer: estado['incompleto'] = True."""
    estado = {} if estado is None else estado
    m = 0.3
    dentro = lambda l: _dentro(_centro(l), celda, -m)
    from instructivo import es_simbolo
    ps = [l for l in pg['lines'] if l['text'].strip() and dentro(l) and not es_simbolo(l, sym)]
    alta = (celda[3] - celda[1]) > 1.3 * (celda[2] - celda[0])
    peso = collections.Counter()
    for l in ps:
        peso[l['ang']] += len(l['text'].strip())
    vert = collections.Counter({a: n for a, n in peso.items() if a in (90, 270)})
    ang = vert.most_common(1)[0][0] if (alta and vert) else (0 if (not alta and peso.get(0)) else (peso.most_common(1)[0][0] if peso else (90 if alta else 0)))
    if nombre:
        ps += [l for l in pg.get('signos') or () if dentro(l) and l['ang'] == ang]
    Hs = sorted(l.get('H') or 0 for l in ps if l['ang'] == ang and len(l['text'].strip()) >= 2) or sorted(l.get('H') or 0 for l in ps)
    H = (Hs[len(Hs) // 2] if Hs else 0) or 4.0
    out = []
    for l in ps:
        t = l['text'].strip()
        a = l['ang']
        if a != ang and len(t) <= 3 and _raya(l, ang, H):
            t, a = '-', ang                     # (el '-' de un texto vertical, leido 'I' derecho)
        elif a != ang and len(t) <= 3:
            t2 = _redecodificar(sym, l, ang, H)
            if not t2 and ocr:
                t2 = re.sub(r'\s+', '', ocr(l['bbox'], ang) or '')
            if t2 and not RARO_RE.search(t2):
                t, a = t2, ang
        elif RARO_RE.search(t) or '?' in t:
            t2 = ocr(l['bbox'], a) if ocr else ''
            if t2 and not RARO_RE.search(t2):
                t = t2
        else:
            t = _arreglar_il(sym, l, t)
        t = _cero_o(t)
        if not nombre and PUNTUACION.fullmatch(t):
            continue
        if RARO_RE.search(t) or '?' in t:
            estado['incompleto'] = True
        out.append(dict(text=t, bbox=tuple(l['bbox']), ang=a, H=l.get('H') or H))
    # trazos de letras que ningun texto leido cubre (la 'AP' grande): por manchas, con el OCR del recorte (sin OCR: el
    # texto queda incompleto)
    usados = set()
    for l in list(pg['lines']) + list(pg.get('signos') or ()):
        usados |= set(l.get('ids') or ())
    si = getattr(sym, 'sym_ids', set())
    lado = min(celda[2] - celda[0], celda[3] - celda[1])
    sueltos = []
    for _, o, p in pg.get('strokes', []):
        if id(p) in usados or id(p) in si or len(p) < 2:
            continue
        b = bbox(p)
        if not (celda[0] + m < b[0] and b[2] < celda[2] - m and celda[1] + m < b[1] and b[3] < celda[3] - m):
            continue
        if max(b[2] - b[0], b[3] - b[1]) > 0.9 * lado:
            continue
        sueltos.append(b)
    hl = H
    manchas = []
    for b in sorted(sueltos):
        for mm in manchas:
            if b[0] <= mm[2] + 0.3 * hl and mm[0] <= b[2] + 0.3 * hl and b[1] <= mm[3] + 0.3 * hl and mm[1] <= b[3] + 0.3 * hl:
                mm[0], mm[1], mm[2], mm[3] = min(mm[0], b[0]), min(mm[1], b[1]), max(mm[2], b[2]), max(mm[3], b[3])
                break
        else:
            manchas.append(list(b))
    # letras de un mismo renglon (en el sentido de la celda): una sola mancha ('D' 'I' '#9' -> 'DI#9')
    manchas.sort()
    unidas = []
    for mm in manchas:
        u = unidas[-1] if unidas else None
        hm = max(mm[3] - mm[1], 0.1) if ang == 0 else max(mm[2] - mm[0], 0.1)
        if u and ang == 0 and min(u[3], mm[3]) - max(u[1], mm[1]) > 0.5 * min(u[3] - u[1], hm) and mm[0] - u[2] < 0.9 * hm:
            u[0], u[1], u[2], u[3] = min(u[0], mm[0]), min(u[1], mm[1]), max(u[2], mm[2]), max(u[3], mm[3])
        else:
            unidas.append(list(mm))
    for mm in unidas:
        if max(mm[2] - mm[0], mm[3] - mm[1]) < 0.6 * hl or any(_dentro(((mm[0] + mm[2]) / 2, (mm[1] + mm[3]) / 2), x['bbox']) for x in out):
            continue
        if not ocr:
            estado['incompleto'] = True
            continue
        t = _cero_o(re.sub(r'\s+', '', ocr(tuple(mm), ang) or ''))
        if t and not RARO_RE.search(t) and re.search(r'[A-Za-z0-9]', t):
            out.append(dict(text=t, bbox=tuple(mm), ang=ang, H=(mm[3] - mm[1]) if ang == 0 else (mm[2] - mm[0]), suelto=True))
    for x in out:
        x['celda'] = ang
    return out


PUNTUACION = re.compile(r'[-_.,•·]+')
_OCR_MEM = {}             # OCR de renglones de las celdas, en memoria del proceso (no se escribe en ocr_cache.json)


def _ocr_renglon(line, H):
    """OCR de un renglon de trazos (sin la memoria de OCR del lector: solo en memoria del proceso). -> texto"""
    from textdec import Decoder, render_line, OCR_FIX
    k = Decoder.line_key(line, H)
    if k not in _OCR_MEM:
        try:
            if 'ocr' not in _DEC:
                _DEC['ocr'] = Decoder(use_ocr=True)
            r = _DEC['ocr'].ocr(render_line(line, H), use_det=False, use_cls=False, use_rec=True)
            _OCR_MEM[k] = (''.join(OCR_FIX.get(c, c) for c in r.txts[0]), float(r.scores[0])) if r.txts else ('', 0.0)
        except Exception:                                                  # noqa: BLE001
            _OCR_MEM[k] = ('', 0.0)
    return _OCR_MEM[k]


def _il(txt, labs):
    """las letras que el diccionario reconoce como I o l (misma forma): l despues de una minuscula o en el medio de una
    palabra que sigue en minuscula ('Plunger', 'Signal'), I si no ('AI6', 'DI 9-', 'TX(I)', 'Input')"""
    out = []
    for i, (ch, lb) in enumerate(zip(txt, labs)):
        if lb == '\x00Il':
            prev = out[-1] if out else ''
            nxt = txt[i + 1] if i + 1 < len(txt) else ''
            ch = 'l' if (prev.islower() or (prev.isalpha() and nxt.islower())) else 'I'
        out.append(ch)
    return ''.join(out)


def _mayusculas(txt, labs):
    """una letra que el diccionario no distingue entre mayuscula y minuscula ('X' / 'x'): mayuscula entre mayusculas
    ('TX(I)'), minuscula entre minusculas"""
    if len(txt) != len(labs):
        return txt
    out = list(txt)
    for i, lb in enumerate(labs):
        if lb and lb.startswith('\x00case:'):
            vec = [c for c in (txt[i - 1] if i else '', txt[i + 1] if i + 1 < len(txt) else '') if c.isalpha()]
            if vec and all(c.isupper() for c in vec):
                out[i] = out[i].upper()
            elif vec and all(c.islower() for c in vec):
                out[i] = out[i].lower()
    return ''.join(out)


def _cero_o(txt, labs=None):
    """un '0' que puso el OCR (labs[i] None; labs None = no se sabe de donde viene) y por el contexto es la letra O:
    entre parentesis despues de letras ('RX(0)' -> 'RX(O)': el TX(I) / RX(O) del RS-232) o entre dos mayusculas en una
    palabra sin otras cifras ('C0M' -> 'COM'). Un '0' que el diccionario leyo como cero, o al final o junto a otras
    cifras ('AI0', 'DI 10+'), queda"""
    if '0' not in txt:
        return txt
    out = list(txt)
    for m in re.finditer(r'\S+', txt):
        w = m.group(0)
        for i, ch in enumerate(w):
            j = m.start() + i
            if ch != '0' or (labs is not None and len(labs) == len(txt) and labs[j] is not None):
                continue
            prev, nxt, prev2 = w[i - 1] if i else '', w[i + 1] if i + 1 < len(w) else '', w[i - 2] if i >= 2 else ''
            if (prev == '(' and nxt == ')' and prev2.isalpha()) or \
                    (prev.isupper() and nxt.isupper() and not any(c.isdigit() for k, c in enumerate(w) if k != i)):
                out[j] = 'O'
    return ''.join(out)


LARGA = 10                # un renglon de 10 o mas letras sin espacios: el OCR de apoyo dice si eran dos palabras


def _sin_espacios(t):
    """para comparar el texto del diccionario con el del OCR: sin espacios, en minuscula, la I / l / 1 y la O / 0 iguales"""
    return re.sub(r'\s+', '', t).lower().translate(str.maketrans({'i': 'l', '1': 'l', '|': 'l', '0': 'o'}))


MISMA_FORMA = 'lxocsvwz'   # minusculas que en estas letras SHX tienen la misma forma que su mayuscula


def _caja_letras(t):
    """una minuscula de la misma forma que su mayuscula ('l' / 'I', 'x' / 'X') en una palabra corta sin otras minusculas
    (y con alguna mayuscula, o sola) es mayuscula: 'Dl' -> 'DI', 'Tx(l)' -> 'TX(I)'; 'Signal', 'Ret.' quedan"""
    out = list(t)
    for m in re.finditer(r'[A-Za-z]+', t):
        w = m.group(0)
        if len(w) > 4:
            continue
        for i, ch in enumerate(w):
            if ch in MISMA_FORMA:
                otras = w[:i] + w[i + 1:]
                if not any(c.islower() and c not in MISMA_FORMA for c in otras) and (any(c.isupper() for c in otras) or len(w) == 1):
                    out[m.start() + i] = 'I' if ch == 'l' else ch.upper()
    return ''.join(out)


def _dist_ps(p, a, b):
    """distancia del punto p al segmento ab"""
    vx, vy = b[0] - a[0], b[1] - a[1]
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


def _toca(a, b, q, tol):
    """el segmento ab toca (se cruza o pasa a menos de tol de) algun tramo del trazo q"""
    bb = bbox(q)
    if bb[0] > max(a[0], b[0]) + tol or bb[2] < min(a[0], b[0]) - tol or bb[1] > max(a[1], b[1]) + tol or bb[3] < min(a[1], b[1]) - tol:
        return False
    o = lambda p, q_, r: (q_[0] - p[0]) * (r[1] - p[1]) - (q_[1] - p[1]) * (r[0] - p[0])
    for c, d in zip(q, q[1:]):
        c, d = c[:2], d[:2]
        if (o(a, b, c) > 0) != (o(a, b, d) > 0) and (o(c, d, a) > 0) != (o(c, d, b) > 0):
            return True
        if min(_dist_ps(c, a, b), _dist_ps(d, a, b), _dist_ps(a, c, d), _dist_ps(b, c, d)) < tol:
            return True
    return False


def _trazos_celda(pg, sym, celda):
    """trazos de texto dentro de la celda (sin sus bordes ni los simbolos), con su caja"""
    if '_cajas_trazos' not in pg:
        from textdec import TEXT_EXCLUDE_OPS
        pg['_cajas_trazos'] = [(bbox(p), p) for _, o, p in pg.get('strokes', []) if o not in TEXT_EXCLUDE_OPS and len(p) >= 2]
    m = 0.3
    si = getattr(sym, 'sym_ids', set())
    lado = min(celda[2] - celda[0], celda[3] - celda[1])
    return [p for b, p in pg['_cajas_trazos'] if celda[0] + m < b[0] and b[2] < celda[2] - m and celda[1] + m < b[1] and b[3] < celda[3] - m
            and id(p) not in si and max(b[2] - b[0], b[3] - b[1]) < 0.9 * lado]


def _leer_celda(pg, sym, celda, nombre=False, ocr=True, estado=None):
    """vuelve a leer el texto de una celda desde sus trazos, en el sentido de la celda (el lector lo leyo pedazo por
    pedazo y a veces giro mal un pedazo chico: el '1' de 'DO 1+', el '#1' de 'Port #1', o junto letras de dos renglones):
    el diccionario de letras con el texto girado a 90 (vertical) o derecho, el que reconoce mas letras (en una celda alta,
    vertical si empata); las letras que el diccionario no reconoce, con el OCR del renglon (en memoria; no toca la memoria
    de OCR del lector; ocr=False: sin el). Un renglon largo sin espacios ('PlungerArrival': las letras de este dibujo
    van casi tan separadas como las palabras) toma los espacios del OCR si el OCR lee las mismas letras. Si quedan letras
    sin leer, estado['incompleto'] = True. -> [{text, bbox, ang, H}] (renglones, como los del lector)"""
    estado = {} if estado is None else estado
    from textdec import group, estimate_H, estimate_H_all, merge_lines, Decoder
    st = _trazos_celda(pg, sym, celda)
    if not st:
        return []
    H = estimate_H(st) or estimate_H_all(st)
    if not H:
        return []
    dec = _dec()
    alta = (celda[3] - celda[1]) > 1.3 * (celda[2] - celda[0])
    angs = (90, 0, 270) if alta else (0, 90)
    # una barra '/' alta (un trazo recto en diagonal de 1,2 a 2,5 letras de alto) que sube hasta el renglon de arriba: el
    # decodificador la juntaria con las letras de ese renglon y se perderia (75287: la barra de 'Sensor / ED#11' entre
    # 'Plunger' y 'Arrival'). Va aparte, como un pedazo '/' en su lugar (el renglon de su centro)
    barras = []
    if not alta:
        for p in st:
            if len(p) == 2:
                (xa, ya), (xb, yb) = p[0][:2], p[1][:2]
                dx, dy = abs(xb - xa), abs(yb - ya)
                # (suelta: no toca ningun otro trazo; los palos del '#' se cruzan con sus rayas)
                if 1.2 * H <= dy <= 2.5 * H and 0.15 * dy <= dx <= 0.8 * dy and (xb - xa) * (yb - ya) > 0 \
                        and not any(q is not p and _toca((xa, ya), (xb, yb), q, 0.08 * H) for q in st):
                    barras.append(p)
        if barras and len(barras) < len(st):
            ids_b = {id(p) for p in barras}
            st = [p for p in st if id(p) not in ids_b]
        else:
            barras = []
    bloques = []
    for g in group(st, 0.45 * H):
        gs = [st[i] for i in g]
        Hg = estimate_H(gs) or estimate_H_all(gs) or H
        bloques.append((gs, Hg if Hg > 1.1 * H else H))
    mejor = None
    for ang in angs:
        n = k = 0
        lineas = []
        for gs, Hg in bloques:
            for line, chars, base, Hl, labs in dec.lines_for(gs, Hg, ang):
                n += len(labs); k += sum(1 for x in labs if x is not None)
                lineas.append((line, chars, base, Hl, labs, ang))
        q = k / n if n else 0
        if mejor is None or q > mejor[0] + 1e-9:
            mejor = (q, lineas)
    out = []
    for line, chars, base, Hl, labs, ang in mejor[1]:
        txt = ''.join('?' if x is None else (x[6] if x.startswith('\x00case:') else ('I' if x == '\x00Il' else x)) for x in labs)
        txt = _mayusculas(txt, labs)
        if '?' in txt and ocr:
            o, sc = _ocr_renglon(line, Hl)
            o = o.replace(' ', '')
            if len(o) == len(labs) and sc > 0.5:
                txt = ''.join(c if c != '?' else oc for c, oc in zip(txt, o))
            elif sc > 0.8 and not RARO_RE.search(o):
                txt, labs = o, [None] * len(o)
        if len(txt) == len(labs):
            txt = _il(txt, labs)
            txt = _cero_o(txt, labs)               # (la O que el OCR leyo cero: 'RX(0)' -> 'RX(O)')
        xs0 = min(bbox(p)[0] for p in line); xs1 = max(bbox(p)[2] for p in line)
        cpos = [(min(bbox(p)[0] for p in c), max(bbox(p)[2] for p in c)) for c in chars]
        if len(cpos) == len(txt) and len(txt) > 1:
            # espacios adentro del renglon (el decodificador junta 'Plunger Arrival' en un solo bloque): hueco de mas de
            # media letra entre dos letras
            t2, c2 = txt[0], [cpos[0]]
            for i in range(1, len(txt)):
                if cpos[i][0] - cpos[i - 1][1] > 0.55 * Hl:
                    t2 += ' '; c2.append((cpos[i - 1][1], cpos[i][0]))
                t2 += txt[i]; c2.append(cpos[i])
            txt, cpos = t2, c2
        if ocr and ' ' not in txt and '?' not in txt and sum(c.isalpha() for c in txt) >= LARGA:
            # renglon largo sin espacios: los espacios del OCR, si lee las mismas letras ('PlungerArrival' del 75287)
            o, sc = _ocr_renglon(line, Hl)
            o = re.sub(r'\s+', ' ', o).strip()
            if sc > 0.8 and ' ' in o and _sin_espacios(o) == _sin_espacios(txt):
                cortes, k = set(), 0
                for w in o.split(' ')[:-1]:
                    k += len(w); cortes.add(k)
                ok_c = len(cpos) == len(txt)
                t2, c2 = '', []
                for i, ch in enumerate(txt):
                    if i in cortes:
                        t2 += ' '
                        if ok_c:
                            c2.append((cpos[i - 1][1], cpos[i][0]))
                    t2 += ch
                    if ok_c:
                        c2.append(cpos[i])
                txt, cpos = t2, (c2 if ok_c else cpos)
        if '?' in txt:
            estado['incompleto'] = True            # letras sin leer (sin OCR de apoyo, o el OCR no las leyo)
        txt = txt.replace('?', '')
        if not txt.strip():
            continue
        if len(cpos) != len(txt):
            w = (xs1 - xs0) / max(len(txt), 1)
            cpos = [(xs0 + i * w, xs0 + (i + 1) * w) for i in range(len(txt))]
        out.append(dict(text=txt, src='celda', ang=ang, H=Hl, base=base, x0=xs0, x1=xs1, cpos=cpos, bbox=Decoder.pdf_bbox(line, ang),
                        nchars=len(chars), ids=set()))
    out = merge_lines(out)
    res = []
    for l in out:
        t = l['text'].strip()
        if not t or (not nombre and PUNTUACION.fullmatch(t)) or RARO_RE.search(t):
            continue
        res.append(dict(text=_caja_letras(t), bbox=tuple(l['bbox']), ang=l['ang'], H=l['H'], celda=l['ang']))
    for p in barras:
        res.append(dict(text='/', bbox=tuple(bbox(p)), ang=0, H=H, celda=0))
    return res


def _juntar(xs, h):
    """pedazos de un mismo renglon (ordenados) en un texto: con espacio si estan separados mas de un tercio de letra"""
    s = ''
    for a, b in zip([None] + xs[:-1], xs):
        if a is not None and b['bbox'][0] - a['bbox'][2] > 0.3 * max(a['H'] or h, b['H'] or h):
            s += ' '
        s += b['text'].strip()
    return s


def _armar(ps, x_pin=None, nombre=False):
    """texto de una celda con sus pedazos. Texto vertical (90): columnas de izquierda a derecha (cada columna, de abajo
    hacia arriba); en la celda del nombre dos columnas son dos nombres del pin ('RS485 A / RS232 TX(I)'). Texto derecho:
    renglones de arriba abajo; un renglon con varios rotulos separados ('DO #1 ... DO #2') es de los subgrupos: si hay
    otro renglon con un solo rotulo manda ese; una letra grande al costado ('AP', 'PB') va adelante."""
    if not ps:
        return ''
    ang = ps[0].get('celda', collections.Counter(p['ang'] for p in ps).most_common(1)[0][0])
    if ang in (90, 270):
        cols = []
        for p in sorted(ps, key=lambda p: p['bbox'][0]):
            h = p['H'] or (p['bbox'][2] - p['bbox'][0])
            if cols and abs(p['bbox'][0] - cols[-1][-1]['bbox'][0]) < 0.6 * h:
                cols[-1].append(p)
            else:
                cols.append([p])
        if ang == 270:
            cols = cols[::-1]
        txts = []
        for c in cols:
            c.sort(key=lambda p: p['bbox'][1] if ang == 90 else -p['bbox'][3])
            s = ''
            for a, b in zip([None] + c[:-1], c):
                if a is not None:
                    gap = (b['bbox'][1] - a['bbox'][3]) if ang == 90 else (a['bbox'][1] - b['bbox'][3])
                    s += ' ' if gap > 0.6 * max(a['H'] or 1, b['H'] or 1) else ''
                s += b['text'].strip()
            txts.append(s)
        return (' / ' if nombre else ' ').join(t for t in txts if t)
    hs = sorted(p['H'] or 0 for p in ps)
    hmed = hs[(len(hs) - 1) // 2] or 1
    chicos = [p for p in ps if (p['H'] or 0) <= 1.45 * hmed]
    grandes = [p for p in ps if (p['H'] or 0) > 1.45 * hmed]
    rengs = []
    for p in sorted(chicos, key=lambda p: -(p['bbox'][1] + p['bbox'][3]) / 2):
        y = (p['bbox'][1] + p['bbox'][3]) / 2
        if rengs and abs(rengs[-1][0] - y) < 0.6 * (p['H'] or hmed):
            rengs[-1][1].append(p)
        else:
            rengs.append([y, [p]])
    salida = []
    for _, r in rengs:
        r.sort(key=lambda p: p['bbox'][0])
        rot, cur = [], [r[0]]
        for a, b in zip(r, r[1:]):
            if b['bbox'][0] - a['bbox'][2] > 2.2 * max(a['H'] or hmed, b['H'] or hmed):
                rot.append(cur); cur = [b]
            else:
                cur.append(b)
        rot.append(cur)
        salida.append([(_juntar(x, hmed), (x[0]['bbox'][0] + x[-1]['bbox'][2]) / 2) for x in rot])
    # renglon de subgrupos: varios rotulos que empiezan igual ('DO #1' ... 'DO #2', 'DI #1' ... 'DI #2'); otro renglon
    # con varios rotulos distintos ('Sensor' ... 'ED#11', con la '/' que no se leyo) es un solo rotulo
    primera = lambda t: (re.match(r'[A-Za-z]+', t[0]) or re.match(r'', '')).group(0).upper()
    sub = lambda s: len(s) > 1 and len({primera(t) for t in s}) == 1 and primera(s[0])
    unicos = [s for s in salida if not sub(s)]
    partes = []
    for s in salida:
        if not sub(s):
            partes.append(' '.join(t[0] for t in s))
        elif not unicos and x_pin is not None:
            partes.append(min(s, key=lambda t: abs(t[1] - x_pin))[0])
    x0 = min((p['bbox'][0] for p in chicos), default=None)
    gs = sorted(grandes, key=lambda p: p['bbox'][0])
    pre = [p for p in gs if x0 is None or p['bbox'][2] <= x0 + 0.5 * hmed]
    post = [p for p in gs if x0 is not None and p['bbox'][2] > x0 + 0.5 * hmed]
    txt = ' '.join(x for x in ([_juntar(pre, hmed)] if pre else []) + partes + ([_juntar(post, hmed)] if post else []) if x)
    return re.sub(r'\s+', ' ', txt).strip()


def filas_funcional(res, tag, cs=None, ocr=True):
    """filas de pines numerados del simbolo del aparato 'tag' en el funcional, con la aclaracion de cada pin.
    -> {tag, pag, hoja, filas: [{y, r, pines: [{pin, x, y, nombre, grupo}]}] (de arriba abajo; los pines de izquierda a
       derecha, tambien los que no tienen cable: la fila entera), pines: {pin: {nombre, grupo, fila, orden}}} o None (sin
       pines numerados dibujados)"""
    if cs is None:
        from instructivo import conductors
        cs = conductors(res)
    ns = nodos_aparato(cs, tag)
    if not ns:
        return None
    pag = collections.Counter(n[0] for n in ns).most_common(1)[0][0]
    pg = (getattr(res, 'pages_by_index', None) or {p['index']: p for p in res.pages}).get(pag)
    if not pg or not pg.get('lines'):
        return None
    sym = _sym(res, pg)
    circs = list(sym.circles) + list(getattr(sym, 'rounds', []))
    usados = []
    for _, pin, p, _ in (n for n in ns if n[0] == pag):
        c = sym.circle_at(p) or (sym.round_at(p) if hasattr(sym, 'round_at') else None)
        if c and not any(abs(c[0] - u[0][0]) < 0.1 and abs(c[1] - u[0][1]) < 0.1 for u in usados):
            usados.append((c, pin))
    if not usados:
        return None
    # el simbolo del aparato: el recuadro mas chico que contiene todos los pines con cable
    caja = None
    cand = [b for b in sym.boxes if all(_dentro(c[:2], b, c[2]) for c, _ in usados)]
    if cand:
        caja = min(cand, key=_area)
    filas = []
    for c, pin in sorted(usados, key=lambda u: (-u[0][1], u[0][0])):
        if any(abs(c[1] - f['y']) < 0.5 * c[2] and abs(c[2] - f['r']) < 0.2 * c[2] for f in filas):
            continue
        ms = sorted({(round(k[0], 2), round(k[1], 2), round(k[2], 2)) for k in circs
                     if abs(k[1] - c[1]) < 0.5 * c[2] and abs(k[2] - c[2]) < 0.2 * c[2] and (caja is None or _dentro(k[:2], caja, k[2]))})
        if caja is None:          # sin recuadro: los circulos seguidos (huecos de hasta 6 pines)
            xs = [k[0] for k in ms]
            ds = sorted(b - a for a, b in zip(xs, xs[1:])) or [0]
            paso = ds[len(ds) // 2]
            i = min(range(len(ms)), key=lambda j: abs(ms[j][0] - c[0]))
            a_, z_ = i, i
            while a_ > 0 and ms[a_][0] - ms[a_ - 1][0] <= 6 * paso:
                a_ -= 1
            while z_ < len(ms) - 1 and ms[z_ + 1][0] - ms[z_][0] <= 6 * paso:
                z_ += 1
            ms = ms[a_:z_ + 1]
        if len(ms) < FILA_MIN:
            continue
        lado = _numero(pg, sym, c)
        lado = lado[1] if lado else None
        filas.append(dict(y=round(c[1], 2), r=round(c[2], 2), _ms=ms, _lado=lado))
    if not filas:
        return None
    cache = {}
    pdf = getattr(res, 'path', None)
    fo = (lambda bb, a: _ocr(pdf, pag - 1, bb, a, cache)) if ocr else None
    piezas = {}
    pines = {}
    for fi, f in enumerate(filas):
        xs = [k[0] for k in f['_ms']]
        ds = sorted(b - a for a, b in zip(xs, xs[1:]))
        paso = ds[len(ds) // 2] if ds else 2 * f['r']
        f['pines'] = []
        for oi, k in enumerate(f['_ms']):
            nm = _numero(pg, sym, k, f['_lado'])
            pin = nm[0] if nm else None
            cad = _cadena(sym, k, paso)
            celdas = ([None] if cad and (cad[0][2] - cad[0][0]) > 1.6 * paso else []) + cad
            vals, inc = [], False
            for j, cel in enumerate(celdas[:2]):
                if cel is None:
                    vals.append('')
                    continue
                kk = tuple(round(v, 1) for v in cel)
                if kk not in piezas:
                    e1, e2 = {}, {}
                    pz = _leer_celda(pg, sym, cel, nombre=(j == 0), ocr=ocr, estado=e1)
                    if not pz:
                        pz = _pedazos(pg, sym, cel, fo, nombre=(j == 0), estado=e2)
                        e1 = dict(incompleto=True) if (e1.get('incompleto') and not pz) or e2.get('incompleto') else {}
                    piezas[kk] = (pz, bool(e1.get('incompleto')))
                vals.append(_armar(piezas[kk][0], x_pin=k[0], nombre=(j == 0)))
                inc = inc or piezas[kk][1]
            vals += [''] * (2 - len(vals))
            d = dict(pin=pin, x=round(k[0], 2), y=round(k[1], 2), nombre=vals[0], grupo=vals[1])
            if inc:
                d['incompleto'] = True
            f['pines'].append(d)
            if pin and pin not in pines:
                pines[pin] = dict(nombre=d['nombre'], grupo=d['grupo'], fila=fi, orden=oi)
                if inc:
                    pines[pin]['incompleto'] = True
        f.pop('_ms'); f.pop('_lado')
    return dict(tag=tag, pag=pag, hoja=pg['meta'].get('sheet', str(pag)), filas=filas, pines=pines)


def aclaracion(pin, info):
    """texto corto de la punta: 'pin 42 · Signal AI5 · AP Analog Input #5' (sin grupo, sin esa parte); con letras sin
    leer en el nombre o el grupo (sin OCR de apoyo), lo dice: 'pin 46 · AUX + · Feed · (texto incompleto)'"""
    if not pin:
        return ''
    info = info or {}
    s = ' · '.join(x for x in (f'pin {pin}', info.get('nombre') or '', info.get('grupo') or '') if x)
    return s + (' · (texto incompleto)' if info.get('incompleto') else '')


# ------------------------------------------------------------------ 2. mapeo: filas del funcional -> filas del dibujo
def mapear(ff, filas_dibujo):
    """ff = filas_funcional(...); filas_dibujo = [{y, d, xs}] (topo.puerta_e8, de arriba abajo). Cada fila del funcional
    va a una fila del dibujo con la MISMA cantidad de pines (si hay varias, la de los mismos huecos y en el mismo orden
    de arriba abajo); el n-esimo pin de la fila al n-esimo tornillo. -> {pines: {pin: [x, y]}, conf: {pin: 'alta' |
    'media'}, filas: [{fila, dibujo, n, huecos_ok, unica}], sin_fila: [pin...], avisos: [...]}"""
    out = dict(pines={}, conf={}, filas=[], sin_fila=[], avisos=[])
    if not ff or not filas_dibujo:
        return out
    td = [dict(i=i, y=float(f['y']), xs=sorted(float(x) for x in f['xs'])) for i, f in enumerate(filas_dibujo) if len(f.get('xs') or []) >= FILA_MIN]
    usadas = set()
    ultimo_y = None
    for fi, f in enumerate(ff['filas']):
        n = len(f['pines'])
        hf = huecos([p['x'] for p in f['pines']])
        cands = [t for t in td if len(t['xs']) == n and t['i'] not in usadas]
        if not cands:
            out['sin_fila'] += [p['pin'] for p in f['pines'] if p['pin']]
            out['avisos'].append(f"la fila de {n} pines del funcional ({f['pines'][0]['pin'] or '?'} a {f['pines'][-1]['pin'] or '?'}) no tiene "
                                 f"una fila de {n} bornes en el dibujo: esos cables quedan en la franja")
            continue
        # de arriba abajo como en el funcional; entre las que quedan, la de los mismos huecos
        orden = [t for t in cands if ultimo_y is None or t['y'] < ultimo_y] or cands
        mismos = [t for t in orden if huecos(t['xs']) == hf]
        t = (mismos or orden)[0]
        usadas.add(t['i']); ultimo_y = t['y']
        unica = len(cands) == 1
        ok = huecos(t['xs']) == hf
        conf = 'alta' if unica and ok else 'media'
        out['filas'].append(dict(fila=fi, dibujo=t['i'], n=n, huecos_ok=ok, unica=unica))
        for p, x in zip(f['pines'], t['xs']):
            if p['pin'] and p['pin'] not in out['pines']:
                out['pines'][p['pin']] = [round(x, 2), round(t['y'], 2)]
                out['conf'][p['pin']] = conf
        if not ok:
            out['avisos'].append(f"la fila de {n} pines ({f['pines'][0]['pin'] or '?'} a {f['pines'][-1]['pin'] or '?'}) tiene otros huecos en el "
                                 "dibujo que en el funcional: pines a confirmar")
        elif not unica:
            out['avisos'].append(f"hay {len(cands)} filas de {n} bornes en el dibujo: se tomó la que sigue el orden del funcional (a confirmar)")
    return out


def coinciden(ff, filas_dibujo):
    """las filas del funcional y las del dibujo son las mismas: misma cantidad de filas con la misma cantidad de pines y
    los mismos huecos (para reconocer una placa sin etiqueta)"""
    if not ff or not filas_dibujo:
        return False
    a = sorted((len(f['pines']), huecos([p['x'] for p in f['pines']])) for f in ff['filas'])
    b = sorted((len(f['xs']), huecos(sorted(float(x) for x in f['xs']))) for f in filas_dibujo if len(f.get('xs') or []) >= FILA_MIN)
    return bool(a) and a == b and sum(n for n, _ in a) >= 8
