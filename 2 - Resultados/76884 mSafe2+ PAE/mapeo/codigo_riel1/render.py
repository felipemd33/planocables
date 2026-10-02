import sys, pypdfium2 as pdfium
PDF=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
def render(x0,y0,x1,y1,S,out,page=7):
    doc=pdfium.PdfDocument(PDF); pg=doc[page]
    W,H=pg.get_size()
    img=pg.render(scale=S,crop=(x0,y0,W-x1,H-y1)).to_pil()
    img.save(out); return img
if __name__=='__main__':
    a=sys.argv[1:]
    render(*map(float,a[:5]),a[5],int(a[6]) if len(a)>6 else 7)
