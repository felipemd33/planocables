import json, numpy as np, strk
from arcs import arcfit
from comps import components
P=json.load(open(r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/puntos_riel1.json',encoding='utf-8'))['puntos']
st=strk.load()
def square_center(x,y):
    segs=strk.inbox(st,714,696,730,701.5)
    vx=sorted(set(round(s[2][0][0],3) for s in segs if abs(s[2][0][0]-s[2][-1][0])<0.01 and abs(s[2][0][1]-s[2][-1][1])>2))
    hy=sorted(set(round(s[2][0][1],3) for s in segs if abs(s[2][0][1]-s[2][-1][1])<0.01 and min(s[2][0][0],s[2][-1][0])<=x<=max(s[2][0][0],s[2][-1][0])))
    L=[v for v in vx if v<x]; R=[v for v in vx if v>x]; B=[v for v in hy if v<y]; T=[v for v in hy if v>y]
    if L and R and B and T: return ((max(L)+min(R))/2,(max(B)+min(T))/2)
def poly_center(x,y):
    best=None
    for c in components(x-4,y-4,x+4,y+4):
        a=np.array([q for s in c for q in s[2]]); (bx0,by0),(bx1,by1)=a.min(0),a.max(0)
        if bx0<=x<=bx1 and by0<=y<=by1 and 1<bx1-bx0<6 and 1<by1-by0<6:
            ar=(bx1-bx0)*(by1-by0)
            if best is None or ar<best[0]: best=(ar,(bx0+bx1)/2,(by0+by1)/2)
    return best[1:] if best else None
res=[]
for p in P:
    x,y,r=p['x'],p['y'],p['r']
    if p['tag']=='13PS1' and p['lado']=='ARRIBA':
        c=square_center(x,y); met='cuadrado'
    elif p['tag'] in ('42KS1','11F1','11F2','13F4','13F5','13F6','12F3') or (p['tag']=='13PS1'):
        c=poly_center(x,y); met='poligono'
    else:
        f=arcfit(x,y,r); c=(f[0],f[1]) if f else None; met='arcos'
    d=float(np.hypot(c[0]-x,c[1]-y)) if c else None
    res.append(dict(d=p.get('d_usada',p['d']),cable=p['cables'][0],x=x,y=y,cx=round(float(c[0]),3) if c else None,cy=round(float(c[1]),3) if c else None,dist=round(d,3) if d is not None else None,metodo=met,texto=p['texto_taller']))
json.dump(res,open('medicion.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
for q in res: print(f"{q['d']:<16}{q['cable'][:5]:<6}{q['metodo']:<9} dist={q['dist']}")
print('max',max(q['dist'] for q in res))
