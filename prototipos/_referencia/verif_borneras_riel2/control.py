import json, pypdfium2 as pdfium
from PIL import ImageDraw, ImageFont
d=json.load(open('../bornes_referencia.json',encoding='utf-8'))
pts=[p for p in d['puntos'] if p['familia']=='borneras_riel2']
pdf=pdfium.PdfDocument('../topografico.pdf'); page=pdf[7]; W,H=page.get_size()
x0,y0,x1,y1=583,498,705,566; S=16
im=page.render(scale=S,crop=(x0,y0,W-x1,H-y1)).to_pil().convert('RGB')
dr=ImageDraw.Draw(im)
try: f=ImageFont.truetype('arial.ttf',18)
except: f=ImageFont.load_default()
cols={'12XP':'red','13XC1':'blue','13X24':'green','62XDIO':'magenta','62XDO':'orange'}
seen={}
for p in pts:
    X=(p['x']-x0)*S; Y=(y1-p['y'])*S
    c=cols[p['componente']]
    dr.ellipse((X-1.5*S,Y-1.5*S,X+1.5*S,Y+1.5*S),outline=c,width=3)
    k=(round(p['x'],1),round(p['y'],1)); n=seen.get(k,0); seen[k]=n+1
    dr.text((X+14,Y-10+n*18),p['cables'][0]+' '+p['texto'].split(' ',1)[1],fill=c,font=f)
im.save('control_ref_riel2.png'); print(im.size)
