import sys, pickle
st=pickle.load(open('strokes_p7.pkl','rb'))
x0,y0,x1,y1=map(float,sys.argv[1:5])
for l,o,p,c in st:
    if not p: continue
    xs=[a for a,b in p]; ys=[b for a,b in p]
    if min(xs)>=x0 and max(xs)<=x1 and min(ys)>=y0 and max(ys)<=y1:
        print(l,o,tuple(round(v,2) for v in c) if c else None,len(p),' '.join(f'({a:.2f},{b:.2f})' for a,b in p[:14]))
