import sys, pypdfium2 as pdfium
PDF=r'C:/Buscar Termos en plano/1 - Planos/Producto nuevo/ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.pdf'
OUT=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/vr3l/'
_doc=None
def doc():
    global _doc
    if _doc is None: _doc=pdfium.PdfDocument(PDF)
    return _doc
def render(pi, x0,y0,x1,y1, S, name, marks=()):
    """pi = pdf page index (0-based); box in pt bottom-left origin"""
    from PIL import ImageDraw
    pg=doc()[pi]; W,H=pg.get_size()
    img=pg.render(scale=S, crop=(x0, y0, W-x1, H-y1)).to_pil().convert('RGB')
    d=ImageDraw.Draw(img)
    for m in marks:
        x,y,r=m[:3]; col=m[3] if len(m)>3 else (255,0,0); lab=m[4] if len(m)>4 else None
        px=(x-x0)*S; py=(y1-y)*S
        d.ellipse([px-r*S,py-r*S,px+r*S,py+r*S],outline=col,width=1)
        d.line([px-2,py,px+2,py],fill=col); d.line([px,py-2,px,py+2],fill=col)
        if lab: d.text((px+r*S+1,py-6),lab,fill=col)
    img.save(OUT+name); return OUT+name
if __name__=='__main__':
    a=sys.argv
    print(render(int(a[1]),*map(float,a[2:6]),float(a[6]),a[7]))
