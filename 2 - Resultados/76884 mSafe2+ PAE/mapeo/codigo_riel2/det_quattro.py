from comps import *
import json
def caps(x0,x1,y0=480,y1=548):
    out=[]
    for s in segs_in(x0,y0,x1,y1):
        (ax,ay),(bx,by)=s[0],s[-1]
        if abs(ay-by)<0.01 and 0.5<=abs(ax-bx)<=0.65:
            out.append(((ax+bx)/2,ay))
    return out
def bocas(x0,x1):
    cs=sorted(caps(x0,x1))
    # cluster by x
    cols=[]
    for x,y in cs:
        for c in cols:
            if abs(c['x']-x)<0.3: c['pts'].append((x,y)); break
        else: cols.append({'x':x,'pts':[(x,y)]})
    res=[]
    for c in cols:
        ys=sorted(set(round(p[1],3) for p in c['pts']),reverse=True)
        # pair consecutive with dy~5.67
        pairs=[]; i=0
        while i<len(ys)-1:
            if 5.3<ys[i]-ys[i+1]<6.0:
                pairs.append(((ys[i]+ys[i+1])/2, ys[i]-ys[i+1])); i+=2
            else: i+=1
        res.append((round(sum(p[0] for p in c['pts'])/len(c['pts']),3), ys, pairs))
    return res
if __name__=='__main__':
    for tag,(x0,x1) in {'12XP':(622.6,641.6),'13X12V':(648.2,661.5),'13X24V':(668.0,694.4),'61XDO':(701.0,725.8),'61X0V':(732.4,745.7)}.items():
        print(tag)
        for r in bocas(x0,x1): print('  ',r)
