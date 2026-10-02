import sys, pypdfium2 as pdfium
from PIL import Image, ImageDraw
PDF='C:/Buscar Termos en plano/prototipos/_referencia/topografico.pdf'
def render(x0,y0,x1,y1,escala,out,marks=()):
    doc=pdfium.PdfDocument(PDF); pg=doc[7]; W,H=pg.get_size()
    im=pg.render(scale=escala,crop=(x0,y0,W-x1,H-y1)).to_pil().convert('RGB')
    dr=ImageDraw.Draw(im)
    for (x,y,c,lab) in marks:
        px=(x-x0)*escala; py=(y1-y)*escala
        dr.ellipse([px-6,py-6,px+6,py+6],outline=c,width=2)
        if lab: dr.text((px+8,py-8),lab,fill=c)
    # grid ticks every 5pt
    im.save(out); return im.size
if __name__=='__main__':
    a=list(map(float,sys.argv[1:6])); print(render(*a[:4],a[4],sys.argv[6]))
