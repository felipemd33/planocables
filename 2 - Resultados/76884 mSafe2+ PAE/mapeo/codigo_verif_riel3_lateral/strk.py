import sys, pickle, os, math
sys.path.insert(0, r'C:/Buscar Termos en plano/programa')
PROC=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
CACHE=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/vr3l/st7.pkl'
def strokes():
    if os.path.exists(CACHE): return pickle.load(open(CACHE,'rb'))
    import pypdf
    from pdfvec import layer_names, page_strokes
    rd=pypdf.PdfReader(PROC)
    st=page_strokes(rd,7,layer_names(rd),with_color=True)
    pickle.dump(st,open(CACHE,'wb')); return st
def bbox(p):
    xs=[q[0] for q in p]; ys=[q[1] for q in p]; return min(xs),min(ys),max(xs),max(ys)
def fitc(pts):
    n=len(pts)
    if n<3: return None
    mx=sum(p[0] for p in pts)/n; my=sum(p[1] for p in pts)/n
    u=[p[0]-mx for p in pts]; v=[p[1]-my for p in pts]
    suu=sum(a*a for a in u); svv=sum(b*b for b in v); suv=sum(a*b for a,b in zip(u,v))
    det=suu*svv-suv*suv
    if abs(det)<1e-12: return None
    r1=0.5*(sum(a**3 for a in u)+sum(a*b*b for a,b in zip(u,v)))
    r2=0.5*(sum(b**3 for b in v)+sum(b*a*a for a,b in zip(u,v)))
    uc=(r1*svv-r2*suv)/det; vc=(r2*suu-r1*suv)/det
    cx,cy=uc+mx,vc+my; r=math.sqrt(uc*uc+vc*vc+(suu+svv)/n)
    err=max(abs(math.hypot(p[0]-cx,p[1]-cy)-r) for p in pts)
    return cx,cy,r,err
def near(st,x0,y0,x1,y1):
    out=[]
    for s in st:
        pts=s[2]
        if not pts: continue
        b=bbox(pts)
        if b[0]>=x0 and b[2]<=x1 and b[1]>=y0 and b[3]<=y1: out.append(s)
    return out
