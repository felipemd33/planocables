import sys, pickle, os
sys.path.insert(0, r'C:/Buscar Termos en plano/programa')
import pypdf
from pdfvec import layer_names, page_strokes
PROC=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
CACHE='st8.pkl'
def load():
    if os.path.exists(CACHE): return pickle.load(open(CACHE,'rb'))
    rd=pypdf.PdfReader(PROC); st=page_strokes(rd,7,layer_names(rd),with_color=True)
    pickle.dump(st,open(CACHE,'wb')); return st
def inbox(st,x0,y0,x1,y1):
    out=[]
    for s in st:
        pts=s[2]
        if all(x0<=x<=x1 and y0<=y<=y1 for x,y in pts): out.append(s)
    return out
