import sys; sys.path.insert(0,'geo')
from objs import SEGS
import numpy as np
from collections import defaultdict
def components(x0,y0,x1,y1,tol=0.4):
    S=[(a,b) for a,b in SEGS if x0<=min(a[0],b[0]) and max(a[0],b[0])<=x1 and y0<=min(a[1],b[1]) and max(a[1],b[1])<=y1]
    n=len(S); par=list(range(n))
    def f(i):
        while par[i]!=i: par[i]=par[par[i]]; i=par[i]
        return i
    # grid of endpoints + segment intersection approx: use endpoints near any point of other segment
    from shapely.geometry import LineString
    from shapely.strtree import STRtree
    geoms=[LineString([a,b]) if a!=b else LineString([a,(a[0]+1e-6,a[1])]) for a,b in S]
    tree=STRtree(geoms)
    for i,g in enumerate(geoms):
        for j in tree.query(g.buffer(tol)):
            j=int(j)
            if j!=i and g.distance(geoms[j])<=tol:
                a,b=f(i),f(j)
                if a!=b: par[a]=b
    groups=defaultdict(list)
    for i in range(n): groups[f(i)].append(i)
    out=[]
    for k,idx in groups.items():
        xs=[p[0] for i in idx for p in S[i]]; ys=[p[1] for i in idx for p in S[i]]
        out.append([min(xs),min(ys),max(xs),max(ys),len(idx)])
    out.sort(key=lambda o:-o[4])
    return out
