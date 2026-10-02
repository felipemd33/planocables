import pypdfium2 as pdfium, sys
from PIL import Image, ImageDraw
PDF='C:/Buscar Termos en plano/prototipos/_referencia/topografico.pdf'
def render(x0,y0,x1,y1,scale,out,marks=()):
    pdf=pdfium.PdfDocument(PDF); page=pdf[7]
    W,H=page.get_size()
    img=page.render(scale=scale, crop=(x0, y0, W-x1, H-y1)).to_pil().convert('RGB')
    d=ImageDraw.Draw(img)
    for (x,y,lab,col) in marks:
        px=(x-x0)*scale; py=(y1-y)*scale
        r=0.5*scale
        d.ellipse([px-r,py-r,px+r,py+r],outline=col,width=2)
        d.text((px+r+2,py-6),lab,fill=col)
    img.save(out); print(img.size)
if __name__=='__main__':
    a=list(map(float,sys.argv[1:6])); render(a[0],a[1],a[2],a[3],a[4],sys.argv[6])
