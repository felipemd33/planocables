"""Hojas del plano: numero de hoja, zona de la rejilla, referencias a otras hojas '(Sh13:D5)' y orden natural.
Solo biblioteca estandar.

Hay variantes que NO se unifican (dan distinto en casos raros; unificarlas cambia resultados, PLAN_MODULAR seccion 10):
  - natkey (core: str(s)) y natk (instructivo / estacion8: str(s or ''), None -> '');
  - stacked_ref (core: devuelve el renglon o None, usa core.near) y ref_apilada (instructivo: [renglon] o [], usa
    instructivo.box_dist)."""
import math
import re

from .geom import cerca, dist_caja

# referencia a otra hoja: '(Sh13:D5)', '(Sh15:B2/D2/E2)' (una flecha que va a varias zonas), '(Sh: 61:E4)'; la letra de
# subhoja no cuenta ('(Sh15A:D2)')
SHREF_RE = re.compile(r'\(\s*Sh\s*:?\s*(\d+)[A-Z]?\s*[:;.]\s*([A-F]\d)(?:\s*/\s*[A-F]\d)*\s*\)', re.I)
H_REF = 7.93   # altura del texto de los numeros de cable en el plano con que se calibraron los umbrales (75287, A1)


def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', str(s))]


def natk(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', str(s or ''))]


def sheet_name(pg):
    return pg['meta'].get('sheet', str(pg['index']))


def hoja_base(h):
    """numero de una hoja sin la letra de subhoja / alternativa ni los ceros de adelante: '61A' -> '61', '09' -> '9'"""
    m = re.match(r'\d+', h or '')
    return (m.group(0) if m else (h or '')).lstrip('0')


def zone_of(meta, x, y, pw, ph):
    if 'col_edges' in meta:
        col = meta['col_first']
        for e, lab in meta['col_edges']:
            if x > e: col = lab
    else:
        col = str(1 + min(7, int((x / pw - 0.08) / 0.105))) if x / pw > 0.08 else '1'
    if 'row_edges' in meta:
        row = meta['row_first']
        for e, lab in meta['row_edges']:
            if y < e: row = lab
    else:
        row = 'ABCDEF'[max(0, min(5, int((1 - y / ph - 0.04) / 0.157)))]
    return f'{row}{col}'


def stacked_ref(lines, p, k):
    """(ShNN:XX) al pie del rotulo de varios renglones centrado en la punta p (flecha): 'Comand' / 'Timer Relay' /
    '-0Vdc' / '(Sh62:D3)'. Se baja (o sube) renglon por renglon desde el mas cercano (como ref_apilada)"""
    horiz = [l for l in lines if l.get('ang', 0) in (0, 180)]
    centrado = lambda l: l['bbox'][0] - 2 * k <= p[0] <= l['bbox'][2] + 2 * k
    first = [l for l in horiz if centrado(l) and cerca(l['bbox'], p, 30 * k)]
    if not first:
        return None
    cur = min(first, key=lambda l: math.hypot(max(l['bbox'][0] - p[0], 0, p[0] - l['bbox'][2]), max(l['bbox'][1] - p[1], 0, p[1] - l['bbox'][3])))
    abajo = (cur['bbox'][1] + cur['bbox'][3]) / 2 < p[1]
    seen = [cur]
    for _ in range(8):
        if SHREF_RE.search(cur['text']):
            return cur
        h = cur['bbox'][3] - cur['bbox'][1]
        gap = (lambda l: cur['bbox'][1] - l['bbox'][3]) if abajo else (lambda l: l['bbox'][1] - cur['bbox'][3])
        nxt = [l for l in horiz if all(l is not x for x in seen) and centrado(l) and -0.3 * h <= gap(l) < 1.2 * h]
        if not nxt:
            break
        cur = min(nxt, key=gap); seen.append(cur)
    return None


def ref_apilada(lines, p, u):
    """(ShNN:XX) al pie de un rotulo de varios renglones centrado en la flecha ('Comand' / 'Solenoide Valve' /
    'NC (Normaly Close)' / '+12Vdc' / '(Sh62:D6)'): se baja (o sube) renglon por renglon desde el mas cercano"""
    horiz = [l for l in lines if l.get('ang', 0) in (0, 180)]
    centrado = lambda l: l['bbox'][0] - 2 * u <= p[0] <= l['bbox'][2] + 2 * u
    first = [l for l in horiz if centrado(l) and dist_caja(p, l['bbox']) < 30 * u]
    if not first:
        return []
    cur = min(first, key=lambda l: dist_caja(p, l['bbox']))
    abajo = (cur['bbox'][1] + cur['bbox'][3]) / 2 < p[1]          # la pila sigue alejandose de la flecha
    seen = [cur]
    for _ in range(8):
        if SHREF_RE.search(cur['text']):
            return [cur]
        h = cur['bbox'][3] - cur['bbox'][1]
        gap = (lambda l: cur['bbox'][1] - l['bbox'][3]) if abajo else (lambda l: l['bbox'][1] - cur['bbox'][3])
        nxt = [l for l in horiz if all(l is not x for x in seen) and centrado(l) and -0.3 * h <= gap(l) < 1.2 * h]
        if not nxt:
            break
        cur = min(nxt, key=gap); seen.append(cur)
    return []
