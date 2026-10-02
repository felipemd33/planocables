import sys, pickle
sys.path.insert(0, r'C:/Buscar Termos en plano/programa')
import pypdf
from pdfvec import layer_names, page_strokes
PROC=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
rd=pypdf.PdfReader(PROC)
st=page_strokes(rd,7,layer_names(rd),with_color=True)
pickle.dump(st,open('st8.pkl','wb'))
print(len(st))
from collections import Counter
print(Counter(s[1] for s in st))
print(Counter(s[3] for s in st).most_common(10))
