"""Lectura de la geometria vectorial de un PDF exportado desde CAD (trazos + capas)."""
import pypdf
from pypdf.generic import ContentStream


def layer_names(reader):
    try:
        ocgs = reader.trailer['/Root']['/OCProperties']['/OCGs']
    except KeyError:
        return {}
    return {o.idnum: str(o.get_object().get('/Name', '')) for o in ocgs}


def page_strokes(reader, pi, names=None, with_color=False):
    """Devuelve [(capa, operador, [(x, y), ...])] con la matriz CTM aplicada.
    Las curvas se aproximan por su punto final (en planos CAD casi todo son lineas)."""
    names = names if names is not None else layer_names(reader)
    page = reader.pages[pi]
    res = page.get('/Resources') or {}
    props = res.get('/Properties') or {}
    pm = {}
    for k, v in props.items():
        pm[k] = names.get(getattr(v, 'idnum', None), str(k))
    contents = page.get_contents()
    if contents is None:
        return []
    cs = ContentStream(contents, reader)
    stack, gs, out = [], [], []
    ctm = [1, 0, 0, 1, 0, 0]
    fill, stroke = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)   # color de relleno / trazo (RGB 0-1)
    cstack = []
    cur, paths = [], []

    def T(x, y):
        a, b, c, d, e, f = ctm
        return (a * x + c * y + e, b * x + d * y + f)

    for ops, op in cs.operations:
        if op == b'BDC':
            stack.append(pm.get(ops[1], str(ops[1])) if ops[0] == '/OC' else (stack[-1] if stack else ''))
        elif op == b'BMC':
            stack.append(stack[-1] if stack else '')
        elif op == b'EMC':
            if stack:
                stack.pop()
        elif op == b'q':
            gs.append(list(ctm)); cstack.append((fill, stroke))
        elif op == b'Q':
            if gs:
                ctm = gs.pop()
            if cstack:
                fill, stroke = cstack.pop()
        elif with_color and op in (b'rg', b'RG', b'g', b'G', b'k', b'K', b'sc', b'SC', b'scn', b'SCN'):
            v = [float(x) for x in ops if not isinstance(x, str) and hasattr(x, '__float__')]
            if len(v) == 1: c = (v[0],) * 3
            elif len(v) == 3: c = tuple(v)
            elif len(v) == 4: c = tuple((1 - v[i]) * (1 - v[3]) for i in range(3))
            else: c = None
            if c is not None:
                if op in (b'rg', b'g', b'k', b'sc', b'scn'): fill = c
                else: stroke = c
        elif op == b'cm':
            a, b, c, d, e, f = [float(v) for v in ops]
            A, B, C, D, E, F = ctm
            ctm = [a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F]
        elif op == b'm':
            if cur:
                paths.append(cur)
            cur = [T(float(ops[0]), float(ops[1]))]
        elif op == b'l':
            cur.append(T(float(ops[0]), float(ops[1])))
        elif op in (b'c', b'v', b'y') and cur:
            # curva de Bezier: muestrear 3 puntos (las fuentes TrueType usan curvas)
            p0 = cur[-1]
            v = [float(x) for x in ops]
            if op == b'c':
                c1, c2, p3 = T(v[0], v[1]), T(v[2], v[3]), T(v[4], v[5])
            elif op == b'v':
                c1, c2, p3 = p0, T(v[0], v[1]), T(v[2], v[3])
            else:
                c1, c2, p3 = T(v[0], v[1]), T(v[2], v[3]), T(v[2], v[3])
            for t in (1 / 3, 2 / 3):
                a = (1 - t) ** 3; b = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t * t; d = t ** 3
                cur.append((a * p0[0] + b * c1[0] + c * c2[0] + d * p3[0], a * p0[1] + b * c1[1] + c * c2[1] + d * p3[1]))
            cur.append(p3)
        elif op == b'h':
            if cur:
                cur.append(cur[0])
        elif op == b're':
            x, y, w, h = [float(v) for v in ops]
            if cur:
                paths.append(cur)
            cur = [T(x, y), T(x + w, y), T(x + w, y + h), T(x, y + h), T(x, y)]
        elif op in (b'S', b's', b'f', b'F', b'B', b'f*', b'B*', b'b', b'b*', b'n'):
            if cur:
                paths.append(cur)
            if op != b'n':
                for p in paths:
                    if with_color:
                        out.append((stack[-1] if stack else '', op.decode(), p, fill if op.decode() in ('f', 'F', 'f*', 'B', 'B*', 'b', 'b*') else stroke))
                    else:
                        out.append((stack[-1] if stack else '', op.decode(), p))
            cur, paths = [], []
    return out
