# -*- coding: utf-8 -*-
"""Imagen de control de puntos_riel3_lateral.json: recortes ampliados de la pagina 8 con cada punto (circulo de
radio r) y su rotulo 'designacion #cable' (rotulos verticales con linea guia: los de ARRIBA en el margen de
arriba y los de ABAJO en el de abajo)."""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from ctl import crop

MAP = os.path.dirname(AQUI)
D = json.load(open(os.path.join(MAP, 'puntos_riel3_lateral.json'), encoding='utf-8'))
FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
FONT_T = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 22)
COL = {'alta': (0, 160, 0), 'media': (230, 120, 0), 'baja': (220, 0, 0)}

RECORTES = [
    ('Riel 3 izquierdo (U13): 15XR, 42XC, 81XCM', (680, 349, 745, 424), 14),
    ('Riel 3 derecho (U14): 32XEX, 41XEX', (814, 349, 866, 420), 14),
    ('Lateral: 12PS1 (borde inferior) y 12XPS (riel 1, U19)', (205, 508, 322, 586), 12),
    ('Lateral riel 2 izquierdo (U18): 11SK1, 11Q1, 11Q2', (196, 350, 285, 416), 12),
    ('Lateral riel 2 derecho (U21): 11XPVAC, 11X220V', (344, 350, 392, 416), 14),
]


def texto_vertical(txt, col):
    w, h = FONT.getbbox(txt)[2] + 4, 19
    im = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    ImageDraw.Draw(im).text((2, 0), txt, fill=col, font=FONT)
    return im.rotate(90, expand=True)


def panel(titulo, box, S, puntos):
    x0, y0, x1, y1 = box
    base = crop(x0, y0, x1, y1, S)
    W, H = base.size
    sel = [p for p in puntos if x0 <= p['x'] <= x1 and y0 <= p['y'] <= y1]
    ym = (y0 + y1) / 2      # rotulo arriba si el punto esta en la mitad de arriba del recorte
    arr = sorted([p for p in sel if p['y'] >= ym], key=lambda p: (p['x'], -p['y']))
    aba = sorted([p for p in sel if p['y'] < ym], key=lambda p: (p['x'], p['y']))
    def largo(lst):
        return max([FONT.getbbox(p['lab'])[2] + 10 for p in lst] + [40])
    mt, mb = largo(arr) + 40, largo(aba) + 20
    paso = 19
    ancho = max(W, 20 + paso * max(len(arr), len(aba)))
    im = Image.new('RGB', (ancho + 20, H + mt + mb), 'white')
    im.paste(base, (10, mt))
    d = ImageDraw.Draw(im)
    d.text((10, 4), titulo + '   (%d px/pt)' % S, fill=(0, 0, 0), font=FONT_T)

    def px(p):
        return 10 + (p['x'] - x0) * S, mt + (y1 - p['y']) * S

    def ubicar(lst):
        xs = []
        for p in lst:
            xs.append(px(p)[0])
        # separar al menos 'paso' px conservando el orden
        out = []
        for i, x in enumerate(xs):
            if out and x < out[-1] + paso:
                x = out[-1] + paso
            out.append(x)
        # recentrar si se pasa del ancho
        if out and out[-1] > im.size[0] - 10:
            sh = out[-1] - (im.size[0] - 10)
            out = [v - sh for v in out]
            for i in range(len(out) - 2, -1, -1):
                if out[i] > out[i + 1] - paso:
                    out[i] = out[i + 1] - paso
        return out

    for lst, arriba in ((arr, True), (aba, False)):
        lx = ubicar(lst)
        for p, xl in zip(lst, lx):
            c = COL[p['confianza']]
            X, Y = px(p)
            r = p['r'] * S
            d.ellipse([X - r, Y - r, X + r, Y + r], outline=c, width=3)
            d.line([X - 4, Y, X + 4, Y], fill=c, width=1)
            d.line([X, Y - 4, X, Y + 4], fill=c, width=1)
            tv = texto_vertical(p['lab'], c)
            if arriba:
                ya = mt - 8
                d.line([X, Y - r, X, mt + 2, xl, ya], fill=c, width=1)
                im.paste(tv, (int(xl - tv.size[0] / 2), int(ya - tv.size[1])), tv)
            else:
                ya = mt + H + 8
                d.line([X, Y + r, X, mt + H - 2, xl, ya], fill=c, width=1)
                im.paste(tv, (int(xl - tv.size[0] / 2), int(ya)), tv)
    return im


def main():
    pts = []
    for p in D['puntos']:
        q = dict(p)
        q['lab'] = '%s #%s' % (p['d'], ' / '.join(p['cables']).replace('sin numero', 's/n'))
        pts.append(q)
    for p in D.get('extra_esquema', []):
        q = dict(p)
        q['lab'] = '%s [%s]' % (p['d'], 'extra: ' + p['cables'][0].split(' (')[0])
        q['confianza'] = 'media'
        pts.append(q)
    paneles = [panel(t, b, S, pts) for t, b, S in RECORTES]
    W = max(p.size[0] for p in paneles)
    H = sum(p.size[1] for p in paneles) + 80 + 10 * len(paneles)
    out = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(out)
    d.text((10, 6), '76884 mSafe2+ PAE - pag 8 - riel 3 + bandeja lateral izquierda (%d puntos + %d extra)'
           % (len(D['puntos']), len(D.get('extra_esquema', []))), fill=(0, 0, 0), font=FONT_T)
    d.text((10, 34), 'Verde = alta, naranja = media. Circulo = radio r de la boca. Rotulo: designacion EPLAN #cable', fill=(0, 0, 0), font=FONT_T)
    y = 70
    for p in paneles:
        out.paste(p, (0, y))
        y += p.size[1] + 10
    dest = os.path.join(MAP, 'control_riel3_lateral.png')
    out.save(dest)
    print(dest, out.size)
    # tambien cada panel suelto (para revisar)
    for i, p in enumerate(paneles):
        p.save(os.path.join(AQUI, 'panel_%d.png' % (i + 1)))


if __name__ == '__main__':
    main()
