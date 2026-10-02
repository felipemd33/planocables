import pickle
st=pickle.load(open('geo/st08.pkl','rb'))
SEGS=[]
for c,op,pts,rgb in st:
    for a,b in zip(pts,pts[1:]):
        SEGS.append((a,b))
def band_objects(x0,x1,y0,y1,rail_y=None,tol=0.25):
    """intervalos x de objetos dentro de la banda [x0,x1]x[y0,y1] (segmentos completamente dentro)"""
    iv=[]
    for a,b in SEGS:
        xa,xb=sorted((a[0],b[0])); ya,yb=sorted((a[1],b[1]))
        if xa<x0-0.01 or xb>x1+0.01 or ya<y0 or yb>y1: continue
        if rail_y is not None and abs(ya-yb)<0.05 and any(abs(ya-(rail_y+o))<0.03 for o in rail_y_offsets()):
            if xb-xa>3: continue
        iv.append([xa,xb,ya,yb])
    iv.sort()
    objs=[]
    for s in iv:
        if objs and s[0] < objs[-1][1]-tol:
            o=objs[-1]; o[1]=max(o[1],s[1]); o[2]=min(o[2],s[2]); o[3]=max(o[3],s[3]); o[4]+=1
        else:
            objs.append([s[0],s[1],s[2],s[3],1])
    return objs
def rail_y_offsets():
    return [-12.4,-10.28,-9.21,-8.5,8.5,9.21,10.28,12.4]
