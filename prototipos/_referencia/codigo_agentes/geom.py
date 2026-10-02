"""Geometry helpers for the topographic PDF: circles (screw heads / wire openings) from
page_strokes, which come as many short 2-point segments.

Circle detection = vote of circumcentres: every pair of connected short segments that turn
a little (arc-like) votes for the circumcentre of its 3 points; circles appear as clusters.
This survives circles that are cut by other lines (screw slots, inner rectangles)."""
import math
from collections import defaultdict
from dump_strokes import load_strokes, bbox

LAYERS_COMP = ('COMPONENTES', '00_COMPONENTS')


def segs_in(st, x0, y0, x1, y1, layers=LAYERS_COMP, touch=False):
    out = []
    for lay, op, pts, col in st:
        if layers and lay not in layers:
            continue
        if not pts or len(pts) < 2:
            continue
        b = bbox(pts)
        inside = b[0] >= x0 and b[2] <= x1 and b[1] >= y0 and b[3] <= y1
        if touch:
            inside = not (b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1)
        if inside:
            for i in range(len(pts) - 1):
                out.append((tuple(pts[i]), tuple(pts[i + 1]), lay, op))
    return out


def _circumcentre(a, b, c):
    ax, ay = a; bx, by = b; cx, cy = c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return ux, uy, math.hypot(ax - ux, ay - uy)


def circles(segs, rmin=0.3, rmax=8.0, max_seg=1.5, min_votes=5, tol=0.02, cell=0.15):
    """Return [(cx, cy, r, votes, arc_points)] detected from arc-like segment chains."""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))
    short = [s for s in segs if 0.02 < math.hypot(s[0][0] - s[1][0], s[0][1] - s[1][1]) <= max_seg]
    adj = defaultdict(list)
    for a, b, *_ in short:
        adj[key(a)].append((a, b))
        adj[key(b)].append((b, a))
    votes = []
    for k, lst in adj.items():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                p, a = lst[i]  # p is the shared point
                _, c = lst[j]
                v1 = (a[0] - p[0], a[1] - p[1]); v2 = (c[0] - p[0], c[1] - p[1])
                n1, n2 = math.hypot(*v1), math.hypot(*v2)
                cosang = -(v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
                turn = math.degrees(math.acos(max(-1, min(1, cosang))))
                if not (3 < turn < 70):
                    continue
                cc = _circumcentre(a, p, c)
                if cc and rmin <= cc[2] <= rmax:
                    votes.append((cc[0], cc[1], cc[2], p))
    # cluster
    clusters = []
    for x, y, r, p in votes:
        for cl in clusters:
            if math.hypot(cl['x'] - x, cl['y'] - y) < max(cell, 0.12 * r) and abs(cl['r'] - r) < max(cell, 0.15 * r):
                n = cl['n']
                cl['x'] = (cl['x'] * n + x) / (n + 1); cl['y'] = (cl['y'] * n + y) / (n + 1); cl['r'] = (cl['r'] * n + r) / (n + 1)
                cl['n'] += 1; cl['pts'].append(p)
                break
        else:
            clusters.append({'x': x, 'y': y, 'r': r, 'n': 1, 'pts': [p]})
    out = []
    for cl in clusters:
        if cl['n'] < min_votes:
            continue
        # angular coverage of supporting points
        angs = sorted(math.degrees(math.atan2(p[1] - cl['y'], p[0] - cl['x'])) % 360 for p in cl['pts'])
        gaps = [(angs[(i + 1) % len(angs)] - angs[i]) % 360 for i in range(len(angs))]
        cover = 360 - max(gaps) if len(angs) > 1 else 0
        out.append((cl['x'], cl['y'], cl['r'], cl['n'], cover))
    return out


def find_circles(x0, y0, x1, y1, st=None, min_cover=200, **kw):
    st = st or load_strokes()
    segs = segs_in(st, x0 - 3, y0 - 3, x1 + 3, y1 + 3, touch=True)
    cs = [c for c in circles(segs, **kw) if c[4] >= min_cover and x0 <= c[0] <= x1 and y0 <= c[1] <= y1]
    # merge duplicates (concentric double lines count once: keep the biggest)
    cs.sort(key=lambda c: -c[2])
    res = []
    for c in cs:
        if any(math.hypot(c[0] - d[0], c[1] - d[1]) < 0.35 * d[2] for d in res):
            continue
        res.append(c)
    return sorted(res, key=lambda c: (-round(c[1], 0), c[0]))


if __name__ == '__main__':
    import sys
    x0, y0, x1, y1 = [float(v) for v in sys.argv[1:5]]
    mc = float(sys.argv[5]) if len(sys.argv) > 5 else 200
    for c in find_circles(x0, y0, x1, y1, min_cover=mc):
        print('circle c=(%.2f, %.2f) r=%.2f votes=%d cover=%.0f' % c)
