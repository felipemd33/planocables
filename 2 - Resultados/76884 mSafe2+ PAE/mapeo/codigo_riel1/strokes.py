import sys, pickle
sys.path.insert(0, r'C:/Buscar Termos en plano/programa')
import pypdf
from pdfvec import layer_names, page_strokes
PROC=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
rd=pypdf.PdfReader(PROC)
st=page_strokes(rd,7,layer_names(rd),with_color=True)
print(len(st))
sel=[]
for t in st:
    p=t[2]
    if not p: continue
    xs=[q[0] for q in p]; ys=[q[1] for q in p]
    if max(xs)>=610 and min(xs)<=920 and max(ys)>=600 and min(ys)<=730:
        sel.append(t)
print(len(sel))
from collections import Counter
print(Counter((t[0],t[1],tuple(round(c,2) for c in t[3]) if t[3] else None) for t in sel))
pickle.dump(sel,open('riel1_strokes.pkl','wb'))
