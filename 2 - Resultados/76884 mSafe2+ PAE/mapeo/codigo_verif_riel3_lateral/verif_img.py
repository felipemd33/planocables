# -*- coding: utf-8 -*-
"""Imagen de verificacion: recortes ampliados de la pag. 8 con cada punto marcado.
verde = confirmado sobre la boca/tornillo; naranja = cae en el rasgo pero queda una duda de asignacion;
rojo = corregido (cruz gris = posicion anterior); azul = extra_esquema; violeta = 12PS1 (sin bornes, x estimada)."""
import json
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium
import verif

PDF = verif.PDF
OUT = verif.MAP + 'verif_riel3_lateral.png'
doc = pdfium.PdfDocument(PDF)
pg = doc[7]
W, H = pg.get_size()
F = ImageFont.truetype(r'C:/Windows/Fonts/arial.ttf', 13)
FB = ImageFont.truetype(r'C:/Windows/Fonts/arialbd.ttf', 18)
FS = ImageFont.truetype(r'C:/Windows/Fonts/arial.ttf', 11)

DUDA = {'-11SK1:L', '-11SK1:PE', '-11SK1:N'}
VERDE, NAR, ROJO, AZUL, VIO, GRIS = (0, 150, 0), (235, 120, 0), (220, 0, 0), (0, 90, 230), (150, 0, 170), (120, 120, 120)

PANELES = [
    ('Riel 3 izq.: 15XR, 42XC, 81XCM', (681, 343, 745, 424), 10),
    ('Riel 3 der.: 32XEX, 41XEX', (816, 343, 866, 424), 10),
    ('Lateral abajo: 11SK1, 11Q1, 11Q2', (198, 350, 284, 416), 8),
    ('Lateral abajo: 11XPVAC, 11X220V', (345, 343, 392, 430), 10),
    ('Lateral arriba: 12XPS, 12PS1', (222, 503, 306, 600), 8),
]


def lab(p):
    c = p['cables'][0]
    if c.startswith('sin numero campo'):
        return 'campo'
    if 'Apantallamiento' in c:
        return 'malla'
    if c.startswith('sin numero Verde'):
        return 'PE'
    if c.startswith('sin numero'):
        return c.split()[2][:3]
    if c.startswith('R1'):
        return 'R1'
    return c[:4]


def panel(titulo, box, S):
    x0, y0, x1, y1 = box
    img = pg.render(scale=S, crop=(x0, y0, W - x1, H - y1)).to_pil().convert('RGB')
    img = Image.blend(img, Image.new('RGB', img.size, 'white'), 0.25)
    d = ImageDraw.Draw(img)
    pts = [(p, False) for p in verif.P['puntos']] + [(p, True) for p in verif.P['extra_esquema']]
    hechos = set()
    for p, extra in pts:
        x, y = p['x'], p['y']
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        col = VERDE
        if extra:
            col = AZUL
        elif p['d'] in verif.CORR:
            c = verif.CORR[p['d']]
            ox, oy = (x - x0) * S, (y1 - y) * S
            d.line([ox - 4, oy - 4, ox + 4, oy + 4], fill=GRIS, width=2)
            d.line([ox - 4, oy + 4, ox + 4, oy - 4], fill=GRIS, width=2)
            x, y, col = c['x'], c['y'], ROJO
        elif p['tag'] == '12PS1':
            col = VIO
        elif p['d'] in DUDA:
            col = NAR
        px, py, r = (x - x0) * S, (y1 - y) * S, p['r'] * S
        d.ellipse([px - r, py - r, px + r, py + r], outline=col, width=2)
        d.line([px - 3, py, px + 3, py], fill=col, width=1)
        d.line([px, py - 3, px, py + 3], fill=col, width=1)
        k = (round(x, 1), round(y, 1))
        if p['tag'] == '12PS1' and k in hechos:
            continue
        hechos.add(k)
        t = lab(p) if p['tag'] != '12PS1' or p['d'][-1] not in 'ABDC' else 'RS485'
        if p['tag'] == '12PS1':
            t = p['d'].split(':')[1] if 'RS485' not in t else 'RS485 x4'
        tw = d.textlength(t, font=FS)
        ty = py - r - 13 if p.get('lado') == 'ARRIBA' or (p['tag'] in ('11SK1', '12PS1')) else py + r + 1
        if p['tag'] == '12PS1':
            ty = py + r + 2
        d.rectangle([px - tw / 2 - 1, ty, px + tw / 2 + 1, ty + 12], fill='white')
        d.text((px - tw / 2, ty), t, fill=col, font=FS)
    head = Image.new('RGB', (img.width, 26), 'white')
    ImageDraw.Draw(head).text((4, 3), titulo, fill='black', font=FB)
    out = Image.new('RGB', (img.width, img.height + 26), 'white')
    out.paste(head, (0, 0))
    out.paste(img, (0, 26))
    ImageDraw.Draw(out).rectangle([0, 0, out.width - 1, out.height - 1], outline=(160, 160, 160))
    return out


ims = [panel(*a) for a in PANELES]
fila1 = ims[:2]
fila2 = ims[2:]
w1 = sum(i.width for i in fila1) + 10 * (len(fila1) + 1)
w2 = sum(i.width for i in fila2) + 10 * (len(fila2) + 1)
Wt = max(w1, w2)
h1 = max(i.height for i in fila1)
h2 = max(i.height for i in fila2)
leyenda = 110
canvas = Image.new('RGB', (Wt, 50 + h1 + h2 + 30 + leyenda), 'white')
dd = ImageDraw.Draw(canvas)
dd.text((10, 10), '76884 mSafe2+ PAE - verificacion de puntos riel 3 + bandeja lateral izquierda (pag. 8)', fill='black', font=FB)
x = 10
for i in fila1:
    canvas.paste(i, (x, 45)); x += i.width + 10
x = 10
for i in fila2:
    canvas.paste(i, (x, 55 + h1)); x += i.width + 10
yl = 65 + h1 + h2
items = [(VERDE, 'confirmado: cae en el centro de la boca/tornillo (<= 0,13 pt) y es el borne correcto'),
         (ROJO, 'corregido (cruz gris = posicion anterior): 11Q2 2 y 4, ajuste fino de 0,13 pt'),
         (NAR, 'en el tornillo, pero el orden L / PE / N del toma 11SK1 queda a confirmar'),
         (VIO, '12PS1: el regulador no tiene bornes (cables propios); x estimada en el borde de la caja'),
         (AZUL, 'extra_esquema (no esta en la lista de conexiones): tierra 11XPVAC 3.1 y R1 en 81XCM 7/8 ABAJO')]
for k, (c, t) in enumerate(items):
    yy = yl + k * 20
    dd.ellipse([12, yy + 2, 24, yy + 14], outline=c, width=3)
    dd.text((32, yy), t, fill='black', font=F)
canvas.save(OUT)
print(OUT, canvas.size)
