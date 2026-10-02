import sys, pickle
sel=pickle.load(open('riel1_strokes.pkl','rb'))
x0,x1,y0,y1=[float(v) for v in sys.argv[1:5]]
mx=float(sys.argv[5]) if len(sys.argv)>5 else 100
for t in sel:
    p=t[2]; xs=[q[0] for q in p]; ys=[q[1] for q in p]
    if min(xs)>=x0 and max(xs)<=x1 and min(ys)>=y0 and max(ys)<=y1 and max(max(xs)-min(xs),max(ys)-min(ys))<=mx:
        print(len(p), ' '.join(f'({q[0]:.2f},{q[1]:.2f})' for q in p[:12]))
