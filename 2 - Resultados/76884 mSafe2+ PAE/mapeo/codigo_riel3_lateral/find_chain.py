import numpy as np, sys
from geo import segs_in, chains
def chain_boxes(win, nmin=8, wmin=2.5, wmax=6.5, hmin=2.5, hmax=7.0):
    S=segs_in(win)
    out=[]
    for p in chains(S):
        if len(p)<nmin: continue
        P=np.array(p); x0,y0=P.min(0); x1,y1=P.max(0)
        w,h=x1-x0,y1-y0
        if wmin<=w<=wmax and hmin<=h<=hmax:
            out.append(dict(cx=(x0+x1)/2, cy=(y0+y1)/2, w=w, h=h, n=len(p), b=(x0,y0,x1,y1)))
    # quitar contenidos dentro de otro
    keep=[]
    for a in sorted(out, key=lambda a:-a['w']*a['h']):
        if any(k['b'][0]-0.05<=a['b'][0] and a['b'][2]<=k['b'][2]+0.05 and k['b'][1]-0.05<=a['b'][1] and a['b'][3]<=k['b'][3]+0.05 for k in keep): continue
        keep.append(a)
    return keep
if __name__=='__main__':
    win=tuple(map(float,sys.argv[1:5]))
    for a in sorted(chain_boxes(win), key=lambda a:(round(a['cx']),-a['cy'])):
        print(round(a['cx'],2), round(a['cy'],2), 'w',round(a['w'],2),'h',round(a['h'],2),'n',a['n'])
