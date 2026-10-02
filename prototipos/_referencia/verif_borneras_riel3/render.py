import sys, pypdfium2 as pdfium
# uso: render.py x0 y0 x1 y1 escala salida.png   (coords PDF, origen abajo-izq)
x0,y0,x1,y1,esc=map(float,sys.argv[1:6]); out=sys.argv[6]
pdf=pdfium.PdfDocument('C:/Buscar Termos en plano/prototipos/_referencia/topografico.pdf')
pg=pdf[7]
W,H=pg.get_size()
bm=pg.render(scale=esc, crop=(x0, y0, W-x1, H-y1))
im=bm.to_pil()
im.save(out)
print(W,H,im.size)
