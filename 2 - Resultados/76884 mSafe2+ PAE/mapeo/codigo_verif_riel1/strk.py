import sys, pickle, os
sys.path.insert(0, r'C:/Buscar Termos en plano/programa')
import pypdf
from pdfvec import layer_names, page_strokes
PROC=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
CACHE=os.path.join(os.path.dirname(os.path.abspath(__file__)),'st8.pkl')
def load():
    if os.path.exists(CACHE): return pickle.load(open(CACHE,'rb'))
    rd=pypdf.PdfReader(PROC); st=page_strokes(rd,7,layer_names(rd),with_color=True)
    pickle.dump(st,open(CACHE,'wb')); return st
def inbox(st,x0,y0,x1,y1):
    return [s for s in st if all(x0<=x<=x1 and y0<=y<=y1 for x,y in s[2])]
def circfit(pts):
    import numpy as np
    P=np.array(pts,float)
    if len(P)<5: return None
    x,y=P[:,0],P[:,1]
    A=np.c_[2*x,2*y,np.ones(len(x))]; b=x*x+y*y
    c,_,_,_=np.linalg.lstsq(A,b,rcond=None)
    cx,cy=c[0],c[1]; r=(c[2]+cx*cx+cy*cy)**0.5
    res=abs(np.hypot(x-cx,y-cy)-r).max()
    return cx,cy,r,res
