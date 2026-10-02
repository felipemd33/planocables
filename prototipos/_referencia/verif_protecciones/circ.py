import pickle, math, sys
import numpy as np
tr=pickle.load(open('strokes7.pkl','rb'))
def fit(pts):
    P=np.array(pts,float)
    P=np.unique(P.round(4),axis=0)
    if len(P)<4: return None
    A=np.c_[2*P[:,0],2*P[:,1],np.ones(len(P))]
    b=(P**2).sum(1)
    s,*_=np.linalg.lstsq(A,b,rcond=None)
    cx,cy=s[0],s[1]; r=math.sqrt(max(s[2]+cx*cx+cy*cy,0))
    d=np.hypot(P[:,0]-cx,P[:,1]-cy)
    err=np.abs(d-r).max()/max(r,1e-9)
    ang=np.sort(np.degrees(np.arctan2(P[:,1]-cy,P[:,0]-cx))%360)
    gaps=np.diff(np.r_[ang,ang[0]+360])
    return cx,cy,r,err,360-gaps.max(),len(P)
def strokes_in(win,layers=None):
    x0,y0,x1,y1=win
    out=[]
    for lay,op,pts,col in tr:
        if layers and lay not in layers: continue
        if not pts: continue
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        if min(xs)>=x0 and max(xs)<=x1 and min(ys)>=y0 and max(ys)<=y1:
            out.append((lay,op,pts,col))
    return out
if __name__=='__main__':
    win=tuple(map(float,sys.argv[1:5]))
    rmin=float(sys.argv[5]) if len(sys.argv)>5 else 0.5
    rmax=float(sys.argv[6]) if len(sys.argv)>6 else 10
    for lay,op,pts,col in strokes_in(win):
        f=fit(pts)
        if f and rmin<=f[2]<=rmax and f[3]<0.12 and f[4]>120:
            print('%-12s %s n=%2d c=(%.2f,%.2f) r=%.2f err=%.3f cov=%.0f col=%s'%(lay,op,f[5],f[0],f[1],f[2],f[3],f[4],col))
