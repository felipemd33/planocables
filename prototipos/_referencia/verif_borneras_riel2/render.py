import sys, pypdfium2 as pdfium
pdf = pdfium.PdfDocument('C:/Buscar Termos en plano/prototipos/_referencia/topografico.pdf')
page = pdf[7]
W,H = page.get_size()
print(W,H)
def render(x0,y0,x1,y1,scale,out):
    # PDF coords origin bottom-left; crop in pdfium: (left, bottom, right, top) margins
    bm = page.render(scale=scale, crop=(x0, y0, W-x1, H-y1))
    img = bm.to_pil()
    img.save(out)
    print(out, img.size)
if __name__=='__main__':
    x0,y0,x1,y1,s=map(float,sys.argv[1:6]); render(x0,y0,x1,y1,s,sys.argv[6])
