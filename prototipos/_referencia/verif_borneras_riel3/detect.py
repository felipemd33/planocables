import pickle, math, json
from collections import defaultdict
st=pickle.load(open('strokes_p7.pkl','rb'))
X0,Y0,X1,Y1=665,362,830,442
segs=[]
for l,o,p,c in st:
    if o!='S' or not p: continue
    if not all(X0<=x<=X1 and Y0<=y<=Y1 for x,y in p): continue
    for a,b in zip(p,p[1:]): segs.append((a,b,l,tuple(round(v,2) for v in c) if c else None))
print('segs',len(segs))
# 1) lineas planas de la U: horizontales de 1.9..2.4
flats=[s for s in segs if abs(s[0][1]-s[1][1])<0.02 and 1.9<=abs(s[0][0]-s[1][0])<=2.4]
# 2) arcos: segmentos cortos no ortogonales
def near(a,b,t=0.06): return abs(a[0]-b[0])<t and abs(a[1]-b[1])<t
# agrupar flats por (xc,y) 
cands=[]
for s in flats:
    xl,xr=sorted((s[0][0],s[1][0])); y=s[0][1]
    # verticales que salen de los extremos
    def vert(x):
        out=[]
        for a,b,_,_ in segs:
            if abs(a[0]-x)<0.03 and abs(b[0]-x)<0.03 and abs(a[1]-b[1])>0.3:
                ya,yb=a[1],b[1]
                if abs(ya-y)<0.05: out.append(yb)
                elif abs(yb-y)<0.05: out.append(ya)
        return out
    L=vert(xl); R=vert(xr)
    if not L or not R: continue
    cands.append((xl,xr,y,L,R,s[3],s[2]))
# para cada U: direccion hacia el arco; extremo del arco = punto con x entre xl,xr mas alejado en esa direccion dentro de 2.2
Us=[]
for xl,xr,y,L,R,col,lay in cands:
    d=1 if (L[0]-y)>0 else -1
    tip=None
    for a,b,_,_ in segs:
        for px,py in (a,b):
            if xl+0.2<px<xr-0.2:
                t=(py-y)*d
                if 0.5<t<2.3:
                    if tip is None or t>tip: tip=t
    if tip is None: continue
    Us.append(dict(xl=xl,xr=xr,yflat=y,d=d,tip=y+d*tip,col=col,lay=lay))
# unir duplicados (lineas planas dobles/triples): tomar el flat mas exterior
groups=[]
for u in sorted(Us,key=lambda u:(u['xl'],u['yflat'])):
    for g in groups:
        if abs(g[0]['xl']-u['xl'])<0.2 and abs(g[0]['tip']-u['tip'])<0.3:
            g.append(u); break
    else: groups.append([u])
E=[]
for g in groups:
    d=g[0]['d']
    outer=max((u['yflat'] for u in g), key=lambda v: -v*d)  # flat mas alejado del arco
    tip=g[0]['tip']
    xc=(g[0]['xl']+g[0]['xr'])/2
    E.append(dict(x=round(xc,3),y=round((outer+tip)/2,3),yflat=outer,tip=tip,d=d,col=g[0]['col'],lay=g[0]['lay'],n=len(g)))
E.sort(key=lambda e:(e['x'],-e['y']))
for e in E: print(e)
json.dump(E,open('entradas_mias.json','w'),indent=0)
print(len(E))
