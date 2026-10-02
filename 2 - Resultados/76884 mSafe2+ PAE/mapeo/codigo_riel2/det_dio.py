from comps import *
def dio(x0,x1):
    res=[]
    # find U bars: horizontal segs of length 2.0-2.3 inside piece
    bars=[]
    for s in segs_in(x0,495,x1,536):
        (ax,ay),(bx,by)=s[0],s[-1]
        if abs(ay-by)<0.01 and 2.0<=abs(ax-bx)<=2.3:
            bars.append(((ax+bx)/2,ay))
    return sorted(bars,key=lambda b:(round(b[0],1),-b[1]))
def octo(x0,x1,ya,yb):
    pts=[]
    for s in segs_in(x0-0.01,ya,x1+0.01,yb):
        (ax,ay),(bx,by)=s[0],s[-1]
        L=((ax-bx)**2+(ay-by)**2)**0.5
        if abs(ax-bx)<0.01 and (abs(ax-x0)<0.02 or abs(ax-x1)<0.02): continue
        if abs(ay-by)<0.01 and abs(ax-bx)>3.0: continue
        pts+= [s[0],s[-1]]
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    return min(xs),min(ys),max(xs),max(ys)
if __name__=='__main__':
    xs=[752.32,755.97,759.62,763.27,766.92]
    for i in range(4):
        print(i+1, [ (round(a,2),round(b,2)) for a,b in dio(xs[i],xs[i+1])])
        for ya,yb in ((526.8,531.0),(500.4,504.6)):
            b=octo(xs[i],xs[i+1],ya,yb)
            print('   oct', [round(v,2) for v in b], 'c', round((b[0]+b[2])/2,2), round((b[1]+b[3])/2,2))
