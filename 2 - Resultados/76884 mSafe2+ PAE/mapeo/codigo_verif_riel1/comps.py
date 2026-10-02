import strk, numpy as np, pickle, os
from collections import defaultdict
def components(x0,y0,x1,y1,tol=0.03):
    st=strk.load()
    segs=[s for s in strk.inbox(st,x0,y0,x1,y1)]
    # union-find over endpoints
    keyof=lambda p:(round(p[0]/tol),round(p[1]/tol))
    parent={}
    def f(a):
        while parent.setdefault(a,a)!=a:
            parent[a]=parent[parent[a]]; a=parent[a]
        return a
    def u(a,b): parent[f(a)]=f(b)
    def keys(p):
        kx,ky=keyof(p); return [(kx+i,ky+j) for i in (-1,0,1) for j in (-1,0,1)]
    occupied=set()
    for s in segs:
        for p in s[2]: occupied.add(keyof(p))
    for s in segs:
        ks=[keyof(p) for p in s[2]]
        for k in ks[1:]: u(ks[0],k)
        for p in s[2]:
            for k in keys(p):
                if k in occupied: u(keyof(p),k)
    comp=defaultdict(list)
    for s in segs: comp[f(keyof(s[2][0]))].append(s)
    return list(comp.values())
def circles(x0,y0,x1,y1,maxres=0.08,rmin=0.5,rmax=4):
    out=[]
    for c in components(x0,y0,x1,y1):
        pts=[p for s in c for p in s[2]]
        if len(pts)<8: continue
        fc=strk.circfit(pts)
        if fc and fc[3]<maxres and rmin<fc[2]<rmax:
            a=np.array(pts); ang=np.arctan2(a[:,1]-fc[1],a[:,0]-fc[0])
            cov=len(set(np.floor((ang+np.pi)/(np.pi/8)).astype(int)))
            out.append((round(fc[0],3),round(fc[1],3),round(fc[2],3),round(fc[3],3),cov,len(c)))
    return out
if __name__=='__main__':
    import sys
    a=[float(v) for v in sys.argv[1:5]]
    for c in sorted(circles(*a),key=lambda t:(-t[1],t[0])): print(c)
