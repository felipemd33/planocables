import json, pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
PDF=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
PTS=r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/puntos_riel2.json'
OUT=r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/verif_riel2.png'
P=json.load(open(PTS,encoding='utf-8'))['puntos']
doc=pdfium.PdfDocument(PDF); pg=doc[7]; W,H=pg.get_size()
f=ImageFont.truetype('arial.ttf',11); fb=ImageFont.truetype('arialbd.ttf',16); fs=ImageFont.truetype('arial.ttf',10)
def panel(x0,y0,x1,y1,S,tags,lab):
    img=pg.render(scale=S,crop=(x0,y0,W-x1,H-y1)).to_pil().convert('RGB')
    img=Image.blend(img,Image.new('RGB',img.size,(255,255,255)),0.35)
    d=ImageDraw.Draw(img)
    groups={}
    for p in P:
        if p['tag'] not in tags: continue
        groups.setdefault((p['x'],p['y']),[]).append(p)
    for (x,y),ps in groups.items():
        px=(x-x0)*S; py=(y1-y)*S; r=ps[0]['r']*S
        med=any(q['confianza']!='alta' for q in ps)
        col=(230,120,0) if med else (0,150,0)
        d.ellipse([px-r,py-r,px+r,py+r],outline=col,width=2)
        d.line([px-3,py,px+3,py],fill=(200,0,0)); d.line([px,py-3,px,py+3],fill=(200,0,0))
        isbar=ps[0]['tag'][2:5] in ('AIB','DIB')
        if isbar:
            for q in ps:
                pin=q['d'].split(':')[1]
                txt=pin+':'+q['cables'][0]+('x2' if q.get('n_conductores',1)==2 else '')
                tw=d.textlength(txt,font=fs)
                lvl=1 if pin in ('1','2') else 0
                if y>515: ty=py-r-12-lvl*12
                else: ty=py+r+1
                tx=px-tw/2
                if lvl: d.line([px,py-r,px,ty+11],fill=(230,120,0))
                d.rectangle([tx-1,ty,tx+tw+1,ty+11],fill=(255,255,255))
                d.text((tx,ty),txt,fill=(120,0,140),font=fs)
            continue
        txt='/'.join(q['cables'][0]+('x2' if q.get('n_conductores',1)==2 else '') for q in ps)
        tw=d.textlength(txt,font=fs)
        if ps[0]['r']>=2.5: tx,ty=px-tw/2,py-6
        else: tx,ty=px-tw/2,(py-r-12 if ps[0]['lado']=='ARRIBA' else py+r+1)
        d.rectangle([tx-1,ty,tx+tw+1,ty+11],fill=(255,255,255))
        d.text((tx,ty),txt,fill=(120,0,140),font=fs)
    d.text((6,4),lab,fill=(0,0,0),font=fb)
    return img
a=panel(612,474,776,562,8,{'12XP','13X12V','13X24V','61XDO','61X0V','61XDIO'},'Riel 2 izq (U11): borneras')
b=panel(815,472,864,584,15,{'15AIB1','15DIB1','15DIB2','15DIB3'},'Riel 2 der (U12): barreras')
Wt=a.width+b.width+10; Ht=max(a.height+190,b.height)
can=Image.new('RGB',(Wt,Ht),(255,255,255)); can.paste(a,(0,40)); can.paste(b,(a.width+10,0))
d=ImageDraw.Draw(can)
d.text((6,8),'ZPL-76884 pag. 8 - verificacion puntos_riel2.json (86 puntos, 92 puntas de conexiones.json)',fill=(0,0,0),font=fb)
y=a.height+60
lines=['Verde = punto confirmado (centro de boca/tornillo dibujado, pieza/enchufe correcto). Naranja = confirmado pero confianza media (enchufe [1 2] no dibujado / 15DIB3 prevista sin barrera).',
 'QUATTRO: centro de las tapas de 0,57 pt de la boca (dif <= 0,01 pt). DIO: octogono con U (dif < 0,1 pt); catodo arriba, anodo abajo del lado del puente FBS 4-5 BU (pag. 8 y 3D pag. 36).',
 'Barreras: aro del tornillo (contorno 2,9 pt, dif <= 0,03 pt). [1 2] detras de [3 4 5]/[3 4]. 3D pag. 25: enchufes verdes (seguro) arriba, azules (IS) abajo.',
 'Etiqueta = numero(s) de cable; x2 = puntera doble (cadena 1370/1361). Sin correcciones de coordenadas.']
for L in lines: d.text((8,y),L,fill=(0,0,0),font=f); y+=18
can.save(OUT); print(OUT,can.size)
