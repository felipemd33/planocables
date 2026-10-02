import strk, numpy as np, sys
st=strk.load()
def arcfit(x,y,r,tol=0.12):
    # take segments whose both endpoints are at distance r +- tol*? from guess center; iterate
    segs=strk.inbox(st,x-r-1.5,y-r-1.5,x+r+1.5,y+r+1.5)
    pts=np.array([q for s in segs for q in s[2]])
    cx,cy=x,y
    for it in range(5):
        d=np.hypot(pts[:,0]-cx,pts[:,1]-cy)
        sel=pts[np.abs(d-r)<max(0.25,r*0.15)]
        if len(sel)<6: return None
        f=strk.circfit(sel)
        cx,cy,r=f[0],f[1],f[2]
    ang=np.degrees(np.arctan2(sel[:,1]-cy,sel[:,0]-cx))
    return round(cx,3),round(cy,3),round(r,3),len(sel),round(ang.min()),round(ang.max())
if __name__=='__main__':
    x,y,r=map(float,sys.argv[1:4]); print(arcfit(x,y,r))
