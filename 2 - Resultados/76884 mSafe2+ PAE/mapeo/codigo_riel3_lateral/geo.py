import math
from collections import defaultdict
from strokes import get
import numpy as np

def bb(p):
    xs=[q[0] for q in p]; ys=[q[1] for q in p]; return min(xs),min(ys),max(xs),max(ys)

def segs_in(win, st=None):
    st = st or get()
    x0,y0,x1,y1=win
    out=[]
    for s in st:
        p=s[2]
        for a,b in zip(p,p[1:]):
            if min(a[0],b[0])>=x0 and max(a[0],b[0])<=x1 and min(a[1],b[1])>=y0 and max(a[1],b[1])<=y1:
                if abs(a[0]-b[0])+abs(a[1]-b[1])>1e-6:
                    out.append((a,b))
    return out

def kasa(pts):
    pts=np.asarray(pts,float)
    if len(pts)<3: return None
    A=np.c_[2*pts[:,0],2*pts[:,1],np.ones(len(pts))]
    bvec=(pts**2).sum(1)
    try:
        sol,*_=np.linalg.lstsq(A,bvec,rcond=None)
    except Exception: return None
    cx,cy,c=sol; r=math.sqrt(max(c+cx*cx+cy*cy,0))
    err=np.abs(np.hypot(pts[:,0]-cx,pts[:,1]-cy)-r).max()
    return cx,cy,r,err

def chains(segs, tol=0.01):
    key=lambda p:(round(p[0]/tol),round(p[1]/tol))
    adj=defaultdict(list)
    for i,(a,b) in enumerate(segs):
        adj[key(a)].append((i,0)); adj[key(b)].append((i,1))
    used=[False]*len(segs)
    out=[]
    for i in range(len(segs)):
        if used[i]: continue
        used[i]=True
        a,b=segs[i]
        path=[a,b]
        # extend forward from b, backward from a
        for direction in (1,0):
            while True:
                end=path[-1] if direction else path[0]
                k=key(end)
                cand=[(j,e) for j,e in adj[k] if not used[j]]
                if len(adj[k])!=2 or not cand: break
                j,e=cand[0]; used[j]=True
                nxt=segs[j][1-e]
                if direction: path.append(nxt)
                else: path.insert(0,nxt)
        out.append(path)
    return out

def turn(a,b,c):
    v1=(b[0]-a[0],b[1]-a[1]); v2=(c[0]-b[0],c[1]-b[1])
    return math.degrees(math.atan2(v1[0]*v2[1]-v1[1]*v2[0], v1[0]*v2[0]+v1[1]*v2[1]))

def arcs(win, rmin=0.8, rmax=3.0, st=None):
    segs=segs_in(win, st)
    res=[]
    for p in chains(segs):
        if len(p)<4: continue
        # split into runs of consistent turning
        run=[p[0],p[1]]; sgn=0
        def flush(run):
            if len(run)>=4:
                f=kasa(run)
                if f and rmin<=f[2]<=rmax and f[3]<0.06:
                    # arc angle span
                    ang=[math.atan2(q[1]-f[1],q[0]-f[0]) for q in run]
                    span=sum(abs(math.remainder(ang[k+1]-ang[k],2*math.pi)) for k in range(len(ang)-1))
                    res.append(dict(cx=f[0],cy=f[1],r=f[2],err=f[3],n=len(run),span=math.degrees(span),pts=run))
        for k in range(2,len(p)):
            t=turn(run[-2],run[-1],p[k])
            s=1 if t>0.5 else (-1 if t<-0.5 else 0)
            if abs(t)>50 or (s and sgn and s!=sgn):
                flush(run); run=[run[-1],p[k]]; sgn=0; continue
            if s: sgn=s
            run.append(p[k])
        flush(run)
    return res

def circles(win, rmin=0.8, rmax=3.0, merge=0.25, st=None):
    """agrupa arcos por centro y radio; devuelve circulos con span total"""
    A=arcs(win,rmin,rmax,st)
    groups=[]
    for a in A:
        for g in groups:
            if math.hypot(g['cx']-a['cx'],g['cy']-a['cy'])<merge and abs(g['r']-a['r'])<merge:
                g['pts']+=a['pts']; g['span']+=a['span']; g['n']+=1
                f=kasa(g['pts']); g['cx'],g['cy'],g['r'],g['err']=f
                break
        else:
            groups.append(dict(cx=a['cx'],cy=a['cy'],r=a['r'],err=a['err'],span=a['span'],n=1,pts=list(a['pts'])))
    for g in groups: g.pop('pts')
    return groups
