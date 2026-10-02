import sys, pypdfium2 as pdfium
# rfun.py pagina(1-based) escala salida [x0 y0 x1 y1 frac 0..1 desde arriba-izq]
pdf=pdfium.PdfDocument('C:/Buscar Termos en plano/1 - Planos/75287 DIAGRAMA ELECTRICO mSafe2AC - REV.6.pdf')
pg=pdf[int(sys.argv[1])-1]; esc=float(sys.argv[2]); out=sys.argv[3]
W,H=pg.get_size()
if len(sys.argv)>4:
    fx0,fy0,fx1,fy1=map(float,sys.argv[4:8])
    crop=(fx0*W, (1-fy1)*H, (1-fx1)*W, fy0*H)
else: crop=(0,0,0,0)
im=pg.render(scale=esc,crop=crop).to_pil(); im.save(out); print(W,H,im.size)
