import math, json
from geo import arcs, kasa
import numpy as np

def ring_groups(win, rmin=1.2, rmax=3.2, merge=1.0):
    """agrupa arcos de radio en rango por cercania de centro; devuelve bbox de los puntos y centro bbox"""
    A=[a for a in arcs(win, 0.5, 4.0) if rmin<=a['r']<=rmax]
    groups=[]
    for a in A:
        for g in groups:
            if math.hypot(g['cx']-a['cx'],g['cy']-a['cy'])<merge:
                g['arcs'].append(a); g['pts']+=a['pts']
                n=len(g['arcs']); g['cx']=np.mean([q['cx'] for q in g['arcs']]); g['cy']=np.mean([q['cy'] for q in g['arcs']])
                break
        else:
            groups.append(dict(cx=a['cx'],cy=a['cy'],arcs=[a],pts=list(a['pts'])))
    out=[]
    for g in groups:
        P=np.array(g['pts']); x0,y0=P.min(0); x1,y1=P.max(0)
        span=sum(a['span'] for a in g['arcs'])
        out.append(dict(bx=(x0+x1)/2, by=(y0+y1)/2, w=x1-x0, h=y1-y0, span=span, n=len(g['arcs']),
                        rs=[round(a['r'],2) for a in g['arcs']], cs=[(round(a['cx'],2),round(a['cy'],2)) for a in g['arcs']]))
    return out
if __name__=='__main__':
    import sys
    win=tuple(map(float,sys.argv[1:5]))
    for g in sorted(ring_groups(win), key=lambda g:(round(g['bx']),-g['by'])):
        print(round(g['bx'],2), round(g['by'],2), 'w',round(g['w'],2),'h',round(g['h'],2),'span',round(g['span']),g['rs'],g['cs'])
