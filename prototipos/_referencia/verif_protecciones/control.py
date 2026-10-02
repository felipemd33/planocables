import json, pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
PDF = '../topografico.pdf'
pts = json.load(open('puntos_verificados.json', encoding='utf-8'))
doc = pdfium.PdfDocument(PDF); pg = doc[7]; W, H = pg.get_size()
fnt = ImageFont.truetype('arialbd.ttf', 15)
def panel(x0, y0, x1, y1, s, sel):
    im = pg.render(scale=s, crop=(x0, y0, W - x1, H - y1)).to_pil().convert('RGB')
    can = Image.new('RGB', (im.width + 300, im.height + 260), 'white'); can.paste(im, (150, 130))
    d = ImageDraw.Draw(can)
    P = lambda x, y: (150 + (x - x0) * s, 130 + (y1 - y) * s)
    grp = {}
    for k, v in pts.items():
        if sel(v): grp.setdefault(tuple(v), []).append(k)
    for i, (v, ks) in enumerate(sorted(grp.items())):
        px, py = P(*v)
        d.ellipse([px - 2.1 * s, py - 2.1 * s, px + 2.1 * s, py + 2.1 * s], outline=(220, 0, 0), width=3)
        t = ' / '.join(k.replace('#', ' [') + ']' for k in ks)
        arriba = v[1] > (y0 + y1) / 2
        ty = 10 + (i % 4) * 28 if arriba else can.height - 120 + (i % 4) * 28
        tx = max(4, min(px - d.textlength(t, font=fnt) / 2, can.width - d.textlength(t, font=fnt) - 4))
        d.line([px, py, px, ty + (18 if arriba else 0)], fill=(220, 0, 0), width=1)
        d.text((tx, ty), t, fill=(180, 0, 0), font=fnt)
    return can
a = panel(641, 636, 806, 712, 7, lambda v: v[1] > 600)
b = panel(566, 292, 640, 318, 7, lambda v: v[1] < 400)
out = Image.new('RGB', (max(a.width, b.width), a.height + b.height), 'white'); out.paste(a, (0, 0)); out.paste(b, (0, a.height))
out.save('control_verificacion.png'); print(out.size)
