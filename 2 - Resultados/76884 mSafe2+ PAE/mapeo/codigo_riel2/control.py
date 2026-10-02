import json, sys
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding='utf-8')
PROC = r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
src = sys.argv[1]; dst = sys.argv[2]
pts = json.load(open(src, encoding='utf-8'))['puntos']
doc = pdfium.PdfDocument(PROC); pg = doc[7]; W, H = pg.get_size()
S = 16
try:
    F = ImageFont.truetype('arial.ttf', 17); FT = ImageFont.truetype('arialbd.ttf', 20)
except Exception:
    F = ImageFont.load_default(); FT = F
COL = {'alta': (0, 150, 0), 'media': (230, 120, 0), 'baja': (220, 0, 0)}
paneles = [
    ('12XP y 13X12V', 617, 476, 663, 549),
    ('13X24V', 662, 476, 696, 549),
    ('61XDO', 695, 476, 727, 549),
    ('61X0V y 61XDIO', 726, 476, 770, 549),
    ('15AIB1 15DIB1 15DIB2 15DIB3 (arriba)', 819, 538, 862, 557),
    ('15AIB1 15DIB1 15DIB2 15DIB3 (abajo)', 819, 474, 862, 494),
]
imgs = []
for titulo, x0, y0, x1, y1 in paneles:
    base = pg.render(scale=S, crop=(x0, y0, W - x1, H - y1)).to_pil().convert('RGB')
    bw, bh = base.size
    sel = [p for p in pts if x0 <= p['x'] <= x1 and y0 <= p['y'] <= y1]
    # agrupar puntos coincidentes
    grupos = {}
    for p in sel:
        k = (round(p['x'], 1), round(p['y'], 1))
        grupos.setdefault(k, []).append(p)
    ML = 330; MR = 330; MT = 40
    nl = 0
    img = Image.new('RGB', (bw + ML + MR, bh + MT + 20), 'white')
    img.paste(base, (ML, MT))
    d = ImageDraw.Draw(img)
    d.text((10, 8), '%s  (pag. 8, %d px/pt, x %.0f-%.0f, y %.0f-%.0f)' % (titulo, S, x0, x1, y0, y1), fill='black', font=FT)
    def px(x, y):
        return ML + (x - x0) * S, MT + (y1 - y) * S
    xm = (x0 + x1) / 2
    izq = []; der = []
    for k, g in grupos.items():
        (izq if k[0] < xm else der).append((k, g))
    for lado, lst in (('L', izq), ('R', der)):
        # etiquetas ordenadas por y de pantalla
        items = []
        for k, g in lst:
            X, Y = px(g[0]['x'], g[0]['y'])
            txt = ' + '.join('%s #%s' % (p['d'], ','.join(p['cables'])) + ('x%d' % p['n_conductores'] if p.get('n_conductores') else '') for p in g)
            items.append([Y, X, txt, g])
        items.sort()
        lh = 21
        ys = []
        last = MT - lh
        for it in items:
            yy = max(it[0], last + lh)
            ys.append(yy); last = yy
        # si se pasan del alto, comprimir hacia arriba
        over = (ys[-1] if ys else 0) - (bh + MT)
        if over > 0:
            ys = [y - over for y in ys]
            for i in range(len(ys) - 2, -1, -1):
                if ys[i] > ys[i + 1] - lh: ys[i] = ys[i + 1] - lh
        for (Y, X, txt, g), yy in zip(items, ys):
            c = COL['media' if any(q['confianza']!='alta' for q in g) else 'alta']
            if lado == 'L':
                tx = 6; ex = ML - 4
                d.text((tx, yy - 8), txt, fill=c, font=F)
                d.line([(ex - 2, yy), (X, Y)], fill=c, width=1)
            else:
                tx = ML + bw + 6; ex = ML + bw + 2
                d.text((tx, yy - 8), txt, fill=c, font=F)
                d.line([(ex, yy), (X, Y)], fill=c, width=1)
    for k, g in grupos.items():
        p = g[0]
        X, Y = px(p['x'], p['y']); R = p['r'] * S
        c = COL[p['confianza']]
        d.ellipse([X - R, Y - R, X + R, Y + R], outline=c, width=3)
        d.line([(X - 4, Y), (X + 4, Y)], fill=c, width=2); d.line([(X, Y - 4), (X, Y + 4)], fill=c, width=2)
    imgs.append(img)
# componer: 4 borneras en una fila, barreras debajo
fila1 = imgs[:4]; fila2 = imgs[4:]
w1 = sum(i.size[0] for i in fila1); h1 = max(i.size[1] for i in fila1)
w2 = max(i.size[0] for i in fila2); h2 = sum(i.size[1] for i in fila2)
Wt = max(w1, w2); Ht = h1 + h2 + 60
out = Image.new('RGB', (Wt, Ht), 'white')
x = 0
for i in fila1:
    out.paste(i, (x, 0)); x += i.size[0]
y = h1 + 10
for i in fila2:
    out.paste(i, (0, y)); y += i.size[1]
d = ImageDraw.Draw(out)
d.text((10, Ht - 40), 'Verde = confianza alta, naranja = media. Circulo = radio r de la boca/tornillo. Rotulo: designacion EPLAN #cable (xN = N conductores en el borne). Puntos superpuestos se rotulan juntos.', fill='black', font=F)
out.save(dst)
print(out.size)
