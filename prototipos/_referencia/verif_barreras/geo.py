import sys, pickle, os
sys.path.insert(0,'C:/Buscar Termos en plano/programa')
import pypdf
from pdfvec import page_strokes, layer_names
C='strokes.pkl'
if os.path.exists(C): st=pickle.load(open(C,'rb'))
else:
    r=pypdf.PdfReader('C:/Buscar Termos en plano/prototipos/_referencia/topografico.pdf')
    st=page_strokes(r,7,layer_names(r),with_color=True); pickle.dump(st,open(C,'wb'))
x0,x1,y0,y1=775,825,485,580
from collections import Counter
cnt=Counter()
sel=[]
for lay,op,pts,col in st:
    if not pts: continue
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    if max(xs)<x0 or min(xs)>x1 or max(ys)<y0 or min(ys)>y1: continue
    cnt[lay]+=1; sel.append((lay,op,pts,col))
print(cnt)
pickle.dump(sel,open('sel.pkl','wb'))
