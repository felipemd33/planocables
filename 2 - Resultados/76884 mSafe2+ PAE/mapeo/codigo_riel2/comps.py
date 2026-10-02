import pickle, math
from collections import defaultdict
st=pickle.load(open('st8.pkl','rb'))
def segs_in(x0,y0,x1,y1):
    out=[]
    for c,op,pts,rgb in st:
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        if min(xs)>=x0 and max(xs)<=x1 and min(ys)>=y0 and max(ys)<=y1:
            out.append(pts)
    return out
def components(segs, tol=0.03):
    # union-find on endpoints
    n=len(segs); par=list(range(n))
    def f(i):
        while par[i]!=i:
            par[i]=par[par[i]]; i=par[i]
        return i
    grid=defaultdict(list)
    q=lambda p:(round(p[0]/tol),round(p[1]/tol))
    for i,s in enumerate(segs):
        for p in (s[0],s[-1]):
            k=q(p)
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    for j in grid[(k[0]+dx,k[1]+dy)]:
                        a,b=f(i),f(j)
                        if a!=b: par[a]=b
            grid[k].append(i)
    g=defaultdict(list)
    for i in range(n): g[f(i)].append(segs[i])
    return list(g.values())
def bbox(ss):
    xs=[p[0] for s in ss for p in s]; ys=[p[1] for s in ss for p in s]
    return min(xs),min(ys),max(xs),max(ys)
