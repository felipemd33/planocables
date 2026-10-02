import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
PDF=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
_doc=None
def crop(x0,y0,x1,y1,S,page=8):
    global _doc
    if _doc is None: _doc=pdfium.PdfDocument(PDF)
    pg=_doc[page-1]; W,H=pg.get_size()
    im=pg.render(scale=S, crop=(x0,y0,W-x1,H-y1)).to_pil().convert('RGB')
    return im
def mark(im, x0,y1,S, pts, grid=None, font=None):
    d=ImageDraw.Draw(im)
    if grid:
        import math
        gx0=math.ceil(x0/grid)*grid
        W,H=im.size
        x=gx0
        while (x-x0)*S<W:
            d.line([((x-x0)*S,0),((x-x0)*S,H)],fill=(200,220,255),width=1); d.text(((x-x0)*S+2,2),f'{x:g}',fill=(0,0,255),font=font); x+=grid
        y=math.floor(y1/grid)*grid
        while (y1-y)*S<H:
            d.line([(0,(y1-y)*S),(W,(y1-y)*S)],fill=(200,220,255),width=1); d.text((2,(y1-y)*S+2),f'{y:g}',fill=(0,0,255),font=font); y-=grid
    for p in pts:
        x,y,r=p['x'],p['y'],p.get('r',1.5)
        px,py=(x-x0)*S,(y1-y)*S
        col=p.get('col',(255,0,0))
        d.ellipse([px-r*S,py-r*S,px+r*S,py+r*S],outline=col,width=max(2,int(S/8)))
        d.line([px-3,py,px+3,py],fill=col); d.line([px,py-3,px,py+3],fill=col)
        if p.get('lab'):
            d.text((px+r*S+2,py-6),p['lab'],fill=col,font=font)
    return im
