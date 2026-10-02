import json
from strk import *
st=load(); segs=[s[2] for s in st]
PTS=r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/puntos_riel2.json'
P=json.load(open(PTS,encoding='utf-8'))['puntos']
res={}
mx=0
for p in P:
    if p['r']!=2.5: continue
    x,y=p['x'],p['y']
    ss=[s for s in segs if all(abs(px-x)<=3.3 and abs(py-y)<=3.3 for px,py in s)]
    caps=[s for s in ss if abs(s[0][1]-s[-1][1])<0.01 and 0.5<=abs(s[0][0]-s[-1][0])<=0.65]
    top=max(c[0][1] for c in caps); bot=min(c[0][1] for c in caps)
    ct=[(c[0][0]+c[-1][0])/2 for c in caps if abs(c[0][1]-top)<0.01]
    cb=[(c[0][0]+c[-1][0])/2 for c in caps if abs(c[0][1]-bot)<0.01]
    # left vertical of contour
    lv=[s[0][0] for s in ss if abs(s[0][0]-s[-1][0])<0.01 and 1.0<=abs(s[0][1]-s[-1][1])<=1.6 and s[0][0]<x]
    cx=(sum(ct)+sum(cb))/(len(ct)+len(cb)); cy=(top+bot)/2
    d=((cx-x)**2+(cy-y)**2)**.5; mx=max(mx,d)
    print(f"{p['d']:13s} {p['cables'][0]} pt=({x:.2f},{y:.2f}) cap_c=({cx:.3f},{cy:.3f}) h={top-bot:.2f} left={min(lv) if lv else None} d={d:.3f}")
print('max d',mx)
