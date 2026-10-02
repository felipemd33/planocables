"""Verificacion independiente de los puntos de barreras (31AIB1, 43DIB1, 43DIB2).
1) Tornillos dibujados: centro de la elipse (aro exterior) en la capa COMPONENTES del topografico.
2) Filas no dibujadas: offsets tomados de la VISTA LATERAL acotada del manual CZ.GS8512-EX.11(S)E-5.0
   (pag. 3, vectorial, cotas 106.0 mm y 99.0 mm), no de la vista frontal esquematica.
   Arriba (lado seguro): enchufe trasero inclinado [1 2] y enchufe del medio [3 4] quedan a la MISMA altura
   (tornillos a 193.26 y 192.72 pt del manual); el enchufe delantero [5 6] esta 12.33 pt del manual mas adentro.
   Abajo (IS): [9 10] exterior, [7 8] 12.31 pt del manual mas adentro.
"""
import json, pickle, math
from PIL import Image, ImageDraw
import pypdfium2 as pdfium

MM_PT_MANUAL = 106.0 / (194.57 - 46.86)      # cota 106.0 mm de la vista lateral
MM_PT_TOPO = 1.4086
d_top = (192.72 - 180.39) * MM_PT_MANUAL / MM_PT_TOPO   # [3 4]/[1 2] -> [5 6]
d_12 = (193.26 - 192.72) * MM_PT_MANUAL / MM_PT_TOPO    # [1 2] sobre [3 4]
d_bot = (55.78 - 43.47) * MM_PT_MANUAL / MM_PT_TOPO     # [9 10] -> [7 8]
print('offset arriba fila delantera: %.2f pt  (%.2f mm)' % (d_top, d_top * MM_PT_TOPO))
print('[1 2] sobre [3 4]: %.2f pt' % d_12)
print('offset abajo fila interior: %.2f pt' % d_bot)

sel = pickle.load(open('sel.pkl', 'rb'))
scr = []
for lay, op, pts, col in sel:
    if lay != 'COMPONENTES' or len(pts) < 16: continue
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    if max(xs) - min(xs) > 2.7 and max(xs) - min(xs) < 3.0 and 780 < min(xs) < 815:
        top = min(ys) > 560
        yc = min(ys) if top else max(ys)          # altura donde el aro es mas ancho
        scr.append((round((min(xs) + max(xs)) / 2, 2), round(yc, 2), 'ARRIBA' if top else 'ABAJO'))
scr = sorted(set(scr))
print('tornillos dibujados:', scr)

ref = json.load(open('../bornes_referencia.json', encoding='utf-8'))
pts = [p for p in ref['puntos'] if p['familia'] == 'barreras']
Y_TOP = 567.05; Y_BOT = 495.67
fila = {'1': 'T0', '2': 'T0', '3': 'T0', '4': 'T0', '5': 'T1', '6': 'T1', '7': 'B1', '8': 'B1', '9': 'B0', '10': 'B0'}
yf = {'T0': Y_TOP, 'T1': Y_TOP - d_top, 'B0': Y_BOT, 'B1': Y_BOT + d_bot}
out = []
for p in pts:
    b = p['texto'].split()[1]
    y = round(yf[fila[b]], 2)
    e = math.hypot(0, y - p['y'])
    out.append((p['texto'], p['cables'][0], p['x'], p['y'], y, round(e, 2)))
    print('%-16s %-5s ref (%.2f, %.2f) -> mio y=%.2f  dif %.2f' % out[-1])
json.dump(out, open('comparacion.json', 'w'), indent=1)

# imagen de control
x0, y0, x1, y1, sc = 778, 485, 818, 578, 14
pdf = pdfium.PdfDocument('C:/Buscar Termos en plano/prototipos/_referencia/topografico.pdf'); page = pdf[7]
W, H = page.get_size()
img = page.render(scale=sc, crop=(x0, y0, W - x1, H - y1)).to_pil().convert('RGB')
d = ImageDraw.Draw(img)
P = lambda x, y: ((x - x0) * sc, (y1 - y) * sc)
for t, c, x, yr, ym, e in out:
    a = P(x, yr); d.ellipse([a[0]-8, a[1]-8, a[0]+8, a[1]+8], outline=(255, 0, 0), width=2)
    b = P(x, ym); d.ellipse([b[0]-6, b[1]-6, b[0]+6, b[1]+6], fill=(0, 160, 0))
    if e > 1.5:
        d.line([a, b], fill=(255, 0, 0), width=1)
    d.text((b[0] + 8, b[1] - 6), t.split()[0][-4:] + ' ' + t.split()[1] + ' ' + c, fill=(0, 0, 200))
img.save('control_verif_barreras.png'); print(img.size)
