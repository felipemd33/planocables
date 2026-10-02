import sys, pickle
sys.path.insert(0, r'C:/Buscar Termos en plano/programa')
from bornes import primitivas as P
sel=pickle.load(open('riel1_strokes.pkl','rb'))
small=[t for t in sel if max(max(q[0] for q in t[2])-min(q[0] for q in t[2]), max(q[1] for q in t[2])-min(q[1] for q in t[2]))<=20]
arcs=P._arcos(small)
cs=P.circulos(arcs,0.4,5.0,cob_min=200)
pickle.dump((arcs,cs),open('circ.pkl','wb'))
x0,x1,y0,y1=[float(v) for v in sys.argv[1:5]]
for c in sorted(cs,key=lambda c:(-round(c['y'],0),c['x'])):
    if x0<=c['x']<=x1 and y0<=c['y']<=y1:
        print(f"x={c['x']:.2f} y={c['y']:.2f} r={c['r']:.2f} cob={c['cob']:.0f} n={c['n']}")
