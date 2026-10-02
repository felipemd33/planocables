import json, numpy as np, cv2, pypdfium2 as pdfium
PDF=r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
PTS=r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/puntos_riel2.json'
X0,Y0,X1,Y1=615,470,870,560; S=24
doc=pdfium.PdfDocument(PDF); pg=doc[7]; W,H=pg.get_size()
img=np.array(pg.render(scale=S,crop=(X0,Y0,W-X1,H-Y1)).to_pil().convert('L'))
bw=(img<160).astype(np.uint8)*255
cnts,hier=cv2.findContours(bw,cv2.RETR_TREE,cv2.CHAIN_APPROX_NONE)
boxes=[]
for c in cnts:
    x,y,w,h=cv2.boundingRect(c)
    # pt coords
    bx0=X0+x/S; bx1=X0+(x+w)/S; by1=Y1-y/S; by0=Y1-(y+h)/S
    boxes.append((bx0,by0,bx1,by1))
np.save('boxes.npy',np.array(boxes))
P=json.load(open(PTS,encoding='utf-8'))['puntos']
for p in P:
    x,y,r=p['x'],p['y'],p['r']
    best=None
    for b in boxes:
        w=b[2]-b[0]; h=b[3]-b[1]
        if b[0]<=x<=b[2] and b[1]<=y<=b[3] and 1.0*r<=max(w,h)/2<=1.6*r+0.5:
            cx=(b[0]+b[2])/2; cy=(b[1]+b[3])/2
            d=((cx-x)**2+(cy-y)**2)**.5
            if best is None or d<best[0]: best=(d,cx,cy,w,h)
    if best: print(f"{p['d']:14s} {p['cables'][0]} pt=({x:.2f},{y:.2f}) r={r} -> contorno c=({best[1]:.2f},{best[2]:.2f}) {best[3]:.2f}x{best[4]:.2f} d={best[0]:.2f}")
    else: print(f"{p['d']:14s} {p['cables'][0]} pt=({x:.2f},{y:.2f}) r={r} -> SIN CONTORNO")
