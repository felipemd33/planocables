import json, math, geo
from bornes import primitivas as pr
P=json.load(open('../puntos_riel3_lateral.json',encoding='utf-8'))
G={n:geo.geo(n) for n in geo.REG}
CIR={n:pr.circulos(G[n]['arc'],0.8,4.0,cob_min=120) for n in G}
def zona(x,y):
    for n,(x0,y0,x1,y1) in geo.REG.items():
        if x0<=x<=x1 and y0<=y<=y1: return n
pts=P['puntos']+P['extra_esquema']
for p in pts:
    z=zona(p['x'],p['y'])
    if not z: print(p['d'],'FUERA'); continue
    cs=sorted(G[z]['cont'],key=lambda c:math.hypot(c['x']-p['x'],c['y']-p['y']))
    cc=[c for c in cs if 1.5<c['w']<8 and 1.5<c['h']<8][:2]
    ci=sorted(CIR[z],key=lambda c:math.hypot(c['x']-p['x'],c['y']-p['y']))[:1]
    s=' | '.join('cont d=%.2f c=(%.2f,%.2f) %.2fx%.2f n=%d'%(math.hypot(c['x']-p['x'],c['y']-p['y']),c['x'],c['y'],c['w'],c['h'],c['n']) for c in cc)
    s2=' | '.join('circ d=%.2f c=(%.2f,%.2f) r=%.2f cob=%.0f'%(math.hypot(c['x']-p['x'],c['y']-p['y']),c['x'],c['y'],c['r'],c['cob']) for c in ci)
    print('%-16s %-8s (%.2f,%.2f) r%.2f :: %s :: %s'%(p['d'],p['cables'][0][:8],p['x'],p['y'],p['r'],s,s2))
