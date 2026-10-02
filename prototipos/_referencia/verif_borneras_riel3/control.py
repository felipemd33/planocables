import json, pypdfium2 as pdfium
from PIL import ImageDraw, ImageFont
ref=json.load(open('../bornes_referencia.json',encoding='utf-8'))
P=[p for p in ref['puntos'] if p['familia']=='borneras_riel3']
falt=[('81XCM 9 ARRIBA','2164',728.12,433.27),('81XCM 10 ARRIBA','2165',728.10,422.00),
      ('81XCM 3 ARRIBA','malla',717.15,433.29),('81XCM 7 ARRIBA','malla',724.46,433.27),('81XCM 13 ARRIBA','malla',735.43,433.25)]
x0,y0,x1,y1=665,365,820,442; esc=10
pdf=pdfium.PdfDocument('../topografico.pdf'); pg=pdf[7]; W,H=pg.get_size()
im=pg.render(scale=esc,crop=(x0,y0,W-x1,H-y1)).to_pil().convert('RGB')
d=ImageDraw.Draw(im)
try: f=ImageFont.truetype('arial.ttf',16)
except: f=ImageFont.load_default()
def px(x,y): return ((x-x0)*esc,(y1-y)*esc)
for p in P:
    X,Y=px(p['x'],p['y']); r=1.0*esc
    d.ellipse((X-r,Y-r,X+r,Y+r),outline=(255,0,0),width=3)
    d.text((X-18,Y-(34 if p['texto'].split()[1] in '13579' or int(p['texto'].split()[1])%2 else -14)),p['cables'][0],fill=(200,0,0),font=f)
for t,c,x,y in falt:
    X,Y=px(x,y); r=1.0*esc
    d.ellipse((X-r,Y-r,X+r,Y+r),outline=(0,160,0),width=3)
    d.text((X-18,Y-34 if int(t.split()[1])%2 else Y+14),c,fill=(0,130,0),font=f)
im.save('control_verif_riel3.png'); print(im.size)
