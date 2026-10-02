import pickle
sel=pickle.load(open('sel.pkl','rb'))
# long vertical and horizontal lines in COMPONENTES
V=set();Hh=set()
for lay,op,pts,col in sel:
    if lay!='COMPONENTES': continue
    for i in range(len(pts)-1):
        (ax,ay),(bx,by)=pts[i],pts[i+1]
        if abs(ax-bx)<0.05 and abs(ay-by)>2: V.add((round(ax,2),round(min(ay,by),2),round(max(ay,by),2)))
        if abs(ay-by)<0.05 and abs(ax-bx)>1: Hh.add((round(ay,2),round(min(ax,bx),2),round(max(ax,bx),2)))
print('VERT')
for v in sorted(V):
    if 780<v[0]<816: print(v)
print('HOR')
for h in sorted(Hh,reverse=True):
    if h[1]>780 and h[2]<816: print(h)
