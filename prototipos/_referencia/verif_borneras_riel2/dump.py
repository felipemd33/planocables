import sys, pickle, os
sys.path.insert(0, 'C:/Buscar Termos en plano/programa')
import pypdf
from pdfvec import page_strokes, layer_names
pk='strokes_p8.pkl'
if not os.path.exists(pk):
    r = pypdf.PdfReader('C:/Buscar Termos en plano/prototipos/_referencia/topografico.pdf')
    st = page_strokes(r, 7, layer_names(r), with_color=True)
    pickle.dump(st, open(pk,'wb'))
st=pickle.load(open(pk,'rb'))
print(len(st))
from collections import Counter
box=(585,495,705,570)
sel=[s for s in st if s[2] and all(box[0]<=x<=box[2] and box[1]<=y<=box[3] for x,y in s[2])]
print(len(sel))
print(Counter((s[0],s[1]) for s in sel))
