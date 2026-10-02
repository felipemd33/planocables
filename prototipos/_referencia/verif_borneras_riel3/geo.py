import sys, pickle, os
sys.path.insert(0, 'C:/Buscar Termos en plano/programa')
import pypdf
from pdfvec import page_strokes, layer_names
cache='strokes_p7.pkl'
if os.path.exists(cache):
    st=pickle.load(open(cache,'rb'))
else:
    r=pypdf.PdfReader('C:/Buscar Termos en plano/prototipos/_referencia/topografico.pdf')
    st=page_strokes(r,7,layer_names(r),with_color=True)
    pickle.dump(st,open(cache,'wb'))
print(len(st))
from collections import Counter
print(Counter((l,o) for l,o,p,c in st).most_common(40))
