import pickle
tr=pickle.load(open('strokes7.pkl','rb'))
for lay,op,pts,col in tr:
    if lay!='Texto etiquetas': continue
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    if op=='f' and col and col[0]>0.9 and col[1]>0.8 and col[2]<0.3:
        print('%s bbox x %.1f-%.1f y %.1f-%.1f  w=%.1f h=%.1f'%(op,min(xs),max(xs),min(ys),max(ys),max(xs)-min(xs),max(ys)-min(ys)))
