import sys, pickle
sys.path.insert(0, r'C:/Buscar Termos en plano/programa')
from bornes import primitivas as P
sel=pickle.load(open('riel1_strokes.pkl','rb'))
x0,x1,y0,y1=[float(v) for v in sys.argv[1:5]]
wmax=float(sys.argv[5]) if len(sys.argv)>5 else 8
def bb(p): return P.bbox(p)
sub=[t for t in sel if (lambda b: b[2]>=x0-1 and b[0]<=x1+1 and b[3]>=y0-1 and b[1]<=y1+1 and max(b[2]-b[0],b[3]-b[1])<=20)(bb(t[2]))]
cs=P._contornos(sub)
for c in sorted(cs,key=lambda c:(-round(c['y'],1),c['x'])):
    if x0<=c['x']<=x1 and y0<=c['y']<=y1 and max(c['w'],c['h'])<=wmax:
        print(f"x={c['x']:.2f} y={c['y']:.2f} w={c['w']:.2f} h={c['h']:.2f} n={c['n']} curvos={c['curvos']}")
