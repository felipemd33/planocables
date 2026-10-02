import json, strk, numpy as np
from comps import components
P=json.load(open(r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/puntos_riel1.json',encoding='utf-8'))['puntos']
cache={}
def comps_near(x,y,w=6):
    key=(round(x/10),round(y/10))
    return components(x-w,y-w,x+w,y+w)
out=[]
for p in P:
    x,y,r=p['x'],p['y'],p['r']
    cs=comps_near(x,y)
    best=[]
    for c in cs:
        a=np.array([q for s in c for q in s[2]])
        bx0,by0=a.min(0); bx1,by1=a.max(0)
        w,h=bx1-bx0,by1-by0
        if bx0<=x<=bx1 and by0<=y<=by1 and w<8 and h<8 and w>1 and h>1:
            cx,cy=(bx0+bx1)/2,(by0+by1)/2
            best.append((round(w*h,2),round(cx,3),round(cy,3),round(w,2),round(h,2),len(c)))
    best.sort()
    print(f"{p['d']:<16}{p['cables'][0][:5]:<6} pt=({x},{y}) r={r} ->", best[:3])
