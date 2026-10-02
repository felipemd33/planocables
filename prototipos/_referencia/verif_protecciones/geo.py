import sys, pickle, os, math
sys.path.insert(0,'C:/Buscar Termos en plano/programa')
import pypdf
from pdfvec import page_strokes, layer_names
PDF='C:/Buscar Termos en plano/prototipos/_referencia/topografico.pdf'
pk='strokes7.pkl'
if not os.path.exists(pk):
    r=pypdf.PdfReader(PDF)
    tr=page_strokes(r,7,layer_names(r),with_color=True)
    pickle.dump(tr,open(pk,'wb'))
tr=pickle.load(open(pk,'rb'))
print(len(tr))
from collections import Counter
print(Counter(t[0] for t in tr).most_common(40))
print(Counter(t[1] for t in tr))
