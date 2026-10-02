import pypdfium2 as pdfium, sys
F='C:/Buscar Termos en plano/2 - Resultados/75287 DIAGRAMA ELECTRICO mSafe2AC - REV.6/75287 DIAGRAMA ELECTRICO mSafe2AC - REV.6 - BUSCABLE.pdf'
pdf=pdfium.PdfDocument(F)
i=int(sys.argv[1]); x0,y0,x1,y1,sc=map(float,sys.argv[2:7]); out=sys.argv[7]
p=pdf[i]; W,H=p.get_size()
img=p.render(scale=sc, crop=(x0,y0,W-x1,H-y1)).to_pil(); img.save(out); print(img.size)
