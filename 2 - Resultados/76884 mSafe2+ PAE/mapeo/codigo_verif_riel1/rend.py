import sys, json, pypdfium2 as pdfium
from PIL import Image, ImageDraw
PDF=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
PTS=r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/puntos_riel1.json'
def render(x0,y0,x1,y1,S,out,pts=True,label=False,page=7):
    doc=pdfium.PdfDocument(PDF); pg=doc[page]; W,H=pg.get_size()
    img=pg.render(scale=S,crop=(x0,y0,W-x1,H-y1)).to_pil().convert('RGB')
    d=ImageDraw.Draw(img)
    if pts and page==7:
        P=json.load(open(PTS,encoding='utf-8'))['puntos']
        for p in P:
            x,y,r=p['x'],p['y'],p['r']
            if x0<=x<=x1 and y0<=y<=y1:
                px=(x-x0)*S; py=(y1-y)*S
                d.ellipse([px-r*S,py-r*S,px+r*S,py+r*S],outline=(255,0,0),width=1)
                d.line([px-3,py,px+3,py],fill=(255,0,0)); d.line([px,py-3,px,py+3],fill=(255,0,0))
                if label: d.text((px+r*S+1,py-6),p['cables'][0][:4],fill=(200,0,200))
    img.save(out); print(out,img.size)
if __name__=='__main__':
    a=sys.argv; render(float(a[1]),float(a[2]),float(a[3]),float(a[4]),float(a[5]),a[6],pts=(a[7]=='1') if len(a)>7 else True,label=(len(a)>8), page=int(a[9]) if len(a)>9 else 7)
