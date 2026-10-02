import sys, pypdfium2 as pdfium
PDF=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
def words(page):
    doc=pdfium.PdfDocument(PDF); tp=doc[page].get_textpage()
    n=tp.count_chars(); out=[]; cur=None
    for i in range(n):
        ch=tp.get_text_range(i,1)
        l,b,r,t=tp.get_charbox(i)
        if ch.strip()=='' :
            if cur: out.append(cur); cur=None
            continue
        if cur and (abs(l-cur[3])<1.5*max(1,(t-b)) ) and abs(b-cur[2])<2 and r>cur[3]-0.5:
            cur=[cur[0]+ch,cur[1],min(cur[2],b),r,max(cur[4],t)]
        else:
            if cur: out.append(cur)
            cur=[ch,l,b,r,t]
    if cur: out.append(cur)
    return out
if __name__=='__main__':
    pg=int(sys.argv[1]); x0,x1,y0,y1=[float(v) for v in sys.argv[2:6]]
    for w in words(pg):
        if x0<=w[1]<=x1 and y0<=w[2]<=y1: print(f'{w[0]!r} x={w[1]:.1f}-{w[3]:.1f} y={w[2]:.1f}-{w[4]:.1f}')
