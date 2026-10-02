import sys, json, math, pickle, os
sys.path.insert(0, r'C:/Buscar Termos en plano/programa')
from bornes import primitivas as pr
import strk
REG={'r3':(680,345,870,425),'lat_bajo':(195,345,400,440),'lat_alto':(220,500,320,610)}
CACHE=strk.CACHE.replace('st7.pkl','geo_%s.pkl')
def trazos_reg(st,reg,m=3):
    x0,y0,x1,y1=reg; out=[]
    for s in st:
        p=s[2]
        if len(p)<2: continue
        b=strk.bbox(p)
        if b[2]<x0-m or b[0]>x1+m or b[3]<y0-m or b[1]>y1+m: continue
        if max(b[2]-b[0],b[3]-b[1])>20: continue
        out.append((s[0],s[1],pr.limpiar(p),s[3],b))
    return out
def geo(name):
    f=CACHE%name
    if os.path.exists(f): return pickle.load(open(f,'rb'))
    st=strk.strokes(); tr=trazos_reg(st,REG[name])
    cont=pr._contornos(tr)
    arc=pr._arcos(tr)
    res=dict(cont=cont,arc=arc)
    pickle.dump(res,open(f,'wb')); return res
if __name__=='__main__':
    for n in REG:
        g=geo(n); print(n,len(g['cont']),len(g['arc']))
