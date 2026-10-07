"""Geometria en pt del PDF (origen abajo a la izquierda). Solo biblioteca estandar.

Los nombres viejos siguen en sus modulos (puentes): textdec.bbox / DSU, wires.seglen / point_seg_dist / box_dist /
inside, core.box_dist / near, instructivo.dist / box_dist, topo.rect_of / CLOSE_OPS.
OJO con box_dist: core lo llama (caja, punto) y wires / instructivo (punto, caja). Aca son dos funciones (dist_caja y
dist_caja_bp) y cada modulo viejo importa la suya con el nombre de hoy."""
import math

CLOSE_OPS = ('f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 's')   # operadores de un trazo cerrado (relleno o 's')


def bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


class DSU:
    def __init__(s, n): s.p = list(range(n))
    def f(s, i):
        while s.p[i] != i:
            s.p[i] = s.p[s.p[i]]; i = s.p[i]
        return i
    def u(s, a, b): s.p[s.f(a)] = s.f(b)


def dist(a, b):
    """distancia entre dos puntos (instructivo.dist; wires.seglen da lo mismo con los puntos al reves)"""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def dist_segmento(p, a, b):
    """(distancia del punto p al segmento a-b, t en [0, 1] del punto mas cercano) (wires.point_seg_dist)"""
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)), t


def dist_caja(p, bb):
    """distancia del punto p a la caja bb (0 adentro). Orden (punto, caja): wires.box_dist e instructivo.box_dist"""
    dx = max(bb[0] - p[0], 0, p[0] - bb[2]); dy = max(bb[1] - p[1], 0, p[1] - bb[3])
    return math.hypot(dx, dy)


def dist_caja_bp(bb, p):
    """lo mismo con el orden (caja, punto) de core.box_dist"""
    dx = max(bb[0] - p[0], 0, p[0] - bb[2]); dy = max(bb[1] - p[1], 0, p[1] - bb[3])
    return math.hypot(dx, dy)


def cerca(bb, p, r):
    """el punto p esta a lo sumo a r de la caja bb (core.near)"""
    dx = max(bb[0] - p[0], 0, p[0] - bb[2]); dy = max(bb[1] - p[1], 0, p[1] - bb[3])
    return math.hypot(dx, dy) <= r


def dentro(p, bb, m=0.0):
    """el punto p cae en la caja bb agrandada m de cada lado (wires.inside)"""
    return bb[0] - m <= p[0] <= bb[2] + m and bb[1] - m <= p[1] <= bb[3] + m


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
