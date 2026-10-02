import json, strk, numpy as np
st=strk.load()
P=json.load(open(r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/puntos_riel1.json',encoding='utf-8'))['puntos']
# index strokes by bbox
bb=[]
for s in st:
    a=np.array(s[2]); bb.append((a[:,0].min(),a[:,1].min(),a[:,0].max(),a[:,1].max()))
bb=np.array(bb)
for p in P:
    x,y=p['x'],p['y']; w=4
    idx=np.where((bb[:,0]>=x-w)&(bb[:,2]<=x+w)&(bb[:,1]>=y-w)&(bb[:,3]<=y+w))[0]
    res=[]
    for i in idx:
        s=st[i]; pts=s[2]
        if len(pts)<6: continue
        f=strk.circfit(pts)
        if f and f[3]<0.15 and np.hypot(f[0]-x,f[1]-y)<1.0:
            res.append((round(f[0],3),round(f[1],3),round(f[2],3),round(f[3],3),s[1]))
    res=sorted(set(res),key=lambda t:-t[2])
    print(p['d'],p['cables'][0][:6],(x,y,p['r']),'->',res[:4])
