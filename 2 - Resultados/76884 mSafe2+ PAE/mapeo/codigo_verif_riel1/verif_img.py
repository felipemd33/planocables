import json, pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
PDF=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
OUT=r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/verif_riel1.png'
P=json.load(open(r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/puntos_riel1.json',encoding='utf-8'))['puntos']
M={(m['d'],m['cable'],m['x'],m['y']):m for m in json.load(open('medicion.json',encoding='utf-8'))}
doc=pdfium.PdfDocument(PDF); pg=doc[7]; W,H=pg.get_size()
def font(n,b=False):
    try: return ImageFont.truetype('arialbd.ttf' if b else 'arial.ttf',n)
    except Exception: return ImageFont.load_default()
FB=font(15,True)
def pin(p):
    t=p['texto_taller'].split(' ',1)[1]
    return t
def panel(x0,y0,x1,y1,S,title,mode='cable',fs=11,where='below'):
    img=pg.render(scale=S,crop=(x0,y0,W-x1,H-y1)).to_pil().convert('RGB')
    d=ImageDraw.Draw(img); F=font(fs)
    for p in P:
        x,y,r=p['x'],p['y'],p['r']
        if not(x0<=x<=x1 and y0<=y<=y1): continue
        m=M.get((p.get('d_usada',p['d']),p['cables'][0],x,y))
        px=(x-x0)*S; py=(y1-y)*S
        if m and m['cx'] is not None:
            qx=(m['cx']-x0)*S; qy=(y1-m['cy'])*S
            d.ellipse([qx-r*S,qy-r*S,qx+r*S,qy+r*S],outline=(0,160,0),width=2)
        d.line([px-5,py,px+5,py],fill=(230,0,0),width=2); d.line([px,py-5,px,py+5],fill=(230,0,0),width=2)
        cab=p['cables'][0]; cab='PE' if cab.startswith('sin') else cab
        lines=[cab] if mode=='cable' else [cab,pin(p)]
        tw=max(d.textlength(l,font=F) for l in lines); th=(fs+2)*len(lines)
        if where=='below': tx,ty=px-tw/2,py+r*S+2
        elif where=='above': tx,ty=px-tw/2,py-r*S-2-th
        else: tx,ty=px+r*S+3,py-th/2
        d.rectangle([tx-1,ty,tx+tw+1,ty+th],fill=(255,255,235))
        for k,l in enumerate(lines): d.text((tx+(tw-d.textlength(l,font=F))/2,ty+k*(fs+2)),l,fill=(150,0,150),font=F)
    out=Image.new('RGB',(img.width,img.height+22),(255,255,255)); ImageDraw.Draw(out).text((3,2),title,fill=(0,0,0),font=FB); out.paste(img,(0,22))
    return out
def hcat(ims,gap=12):
    h=max(i.height for i in ims); w=sum(i.width for i in ims)+gap*(len(ims)-1)
    o=Image.new('RGB',(w,h),(255,255,255)); x=0
    for i in ims: o.paste(i,(x,0)); x+=i.width+gap
    return o
def vcat(ims,gap=12):
    w=max(i.width for i in ims); h=sum(i.height for i in ims)+gap*(len(ims)-1)
    o=Image.new('RGB',(w,h),(255,255,255)); y=0
    for i in ims: o.paste(i,(0,y)); y+=i.height+gap
    return o
A=panel(615,605,915,730,4.6,'Riel 1 (U10), 69 puntas. Cruz roja = puntos_riel1.json; circulo verde = centro medido de nuevo por el verificador (diferencia max 0,08 pt)',mode='cable',fs=10,where='right')
B1=panel(713,694.5,731,702.5,24,'13PS1 TB2 (arriba): -Vo -Vo +Vo +Vo',mode='pin',fs=11)
B2=panel(716,614.5,731,624.5,24,'13PS1 TB1 (abajo): PE -Vin +Vin',mode='pin',fs=11)
C1=panel(827,676,846,692.5,18,'42KS1 arriba: A1 S34 S33 S11 / S12 51 52 A2',mode='pin',fs=11)
C2=panel(827,622.5,846,640,18,'42KS1 abajo: 43 44 13 14 / 33 34 23 24',mode='pin',fs=11)
D1=panel(850,670,881,691.5,16,'42KR1, 61KR1..4 arriba: 11 (ext), 14, 12',mode='pin',fs=11)
D2=panel(850,624.5,881,642,16,'42KR1, 61KR1..4 abajo: A1 (LED), A2 (ext)',mode='pin',fs=11)
E=panel(885,623,911,697,12,'32XAI / XPE',mode='pin',fs=11,where='right')
row2=hcat([vcat([B1,B2]),vcat([C1,C2]),vcat([D1,D2])])
row2=hcat([row2,E])
N1=panel(634,691,654,699.5,18,'11PS1 TB2: -V -V +V +V',mode='pin',fs=11)
N2=panel(639.5,614,656.5,622.5,18,'11PS1 TB1: FG N L',mode='pin',fs=11)
N3=panel(678.5,691,698.5,699.5,18,'11PS2 TB2: -V -V +V +V',mode='pin',fs=11)
N4=panel(684,614,701,622.5,18,'11PS2 TB1: FG N L',mode='pin',fs=11)
row0=hcat([N1,N2,N3,N4])
out=vcat([A,row0,row2],gap=16)
bg=Image.new('RGB',(out.width+16,out.height+16),(255,255,255)); bg.paste(out,(8,8)); bg.save(OUT); print(OUT,bg.size)
