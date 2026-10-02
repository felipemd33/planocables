# -*- coding: utf-8 -*-
"""Imagen de control: recortes ampliados de la pag. 8 con cada punto (circulo de radio r) y rotulo 'designacion #cable'."""
import json, sys
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

PDF = r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
COL = {'alta': (0, 160, 0), 'media': (230, 120, 0), 'baja': (220, 0, 0)}


def font(sz):
    for f in ('arial.ttf', 'C:/Windows/Fonts/arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def recorte(doc, pts, x0, y0, x1, y1, S, titulo, fs=15, margen=None):
    pg = doc[7]
    W, H = pg.get_size()
    base = pg.render(scale=S, crop=(x0, y0, W - x1, H - y1)).to_pil().convert('RGB')
    sel = [p for p in pts if x0 <= p['x'] <= x1 and y0 <= p['y'] <= y1]
    f = font(fs)
    ft = font(fs + 6)
    # niveles de rotulos arriba (ARRIBA) y abajo (ABAJO)
    def tw(s):
        b = f.getbbox(s)
        return b[2] - b[0] + 8
    lh = fs + 6
    grupos = {'ARRIBA': [], 'ABAJO': []}
    for p in sorted(sel, key=lambda q: q['x']):
        grupos['ARRIBA' if p['y'] > (y0 + y1) / 2 else 'ABAJO'].append(p)
    niveles = {}
    for lado, lst in grupos.items():
        ocup = []   # por nivel: lista de (xa, xb)
        for p in lst:
            dd = p['d'] + (f" ({p['texto_taller']})" if 'd_usada' in p or p['tag'] == '32XAI' else '')
            s = f"{p['_k']}: {dd} #{'+'.join(p['cables'])}"
            w = tw(s)
            px = (p['x'] - x0) * S
            xa = px - w / 2
            xa = max(2, min(xa, base.size[0] - w - 2))
            lv = 0
            while True:
                if lv >= len(ocup):
                    ocup.append([])
                if all(xb + 6 < xa or xa + w + 6 < xa2 for xa2, xb in ocup[lv]):
                    ocup[lv].append((xa, xa + w))
                    break
                lv += 1
            niveles[id(p)] = (lado, lv, xa, s)
        grupos[lado] = (lst, len(ocup))
    nA = grupos['ARRIBA'][1]
    nB = grupos['ABAJO'][1]
    top = 34 + nA * lh + 10
    bot = nB * lh + 14
    img = Image.new('RGB', (base.size[0], base.size[1] + top + bot), 'white')
    img.paste(base, (0, top))
    d = ImageDraw.Draw(img)
    d.text((6, 4), titulo, fill=(0, 0, 0), font=ft)
    for p in sel:
        lado, lv, xa, s = niveles[id(p)]
        px = (p['x'] - x0) * S
        py = top + (y1 - p['y']) * S
        rr = p['r'] * S
        c = COL[p['confianza']]
        if lado == 'ARRIBA':
            ly = 34 + (nA - 1 - lv) * lh
            ay = ly + lh - 2
        else:
            ly = top + base.size[1] + 6 + lv * lh
            ay = ly + 1
        ax = xa + (tw(s)) / 2
        d.line([(px, py - rr if lado == 'ARRIBA' else py + rr), (ax, ay)], fill=c + (0,), width=1)
        d.ellipse([px - rr, py - rr, px + rr, py + rr], outline=c, width=3)
        d.line([(px - 3, py), (px + 3, py)], fill=c, width=1)
        d.line([(px, py - 3), (px, py + 3)], fill=c, width=1)
        d.rectangle([xa, ly, xa + tw(s) - 2, ly + lh - 3], fill=(255, 255, 255), outline=c)
        d.text((xa + 4, ly + 1), s, fill=(0, 0, 0), font=f)
        fk = font(max(11, fs - 3))
        d.text((px + rr + 1, py - rr - fs + 4), str(p['_k']), fill=c, font=fk)
    return img


def main(pts_json, out):
    pts = json.load(open(pts_json, encoding='utf-8'))
    if isinstance(pts, dict):
        pts = pts['puntos']
    for k, p in enumerate(pts, 1):
        p['_k'] = k
    doc = pdfium.PdfDocument(PDF)
    S1 = 14
    a = recorte(doc, pts, 628, 612, 708, 704, S1, 'Riel 1 (U10) - fuentes 11PS1 / 11PS2  (14 px/pt)')
    b = recorte(doc, pts, 709, 612, 824, 704, S1, 'Riel 1 - 13PS1 y portafusibles 11F1 11F2 12F3 13F4 13F5 13F6  (14 px/pt)')
    c = recorte(doc, pts, 826, 620, 857, 694, 24, '42KS1 (PSR-ESA2) y 42KR1  (24 px/pt)', fs=14)
    e = recorte(doc, pts, 860, 620, 912, 698, 24, '61KR1..61KR4, 32XAI y XPE  (24 px/pt)', fs=14)
    leyenda = 'verde = alta, naranja = media (a confirmar). x,y = centro de la boca o tornillo; circulo = r.'
    filas = [[a, b], [c, e]]
    W = max(sum(i.size[0] for i in fl) + 20 * (len(fl) - 1) for fl in filas)
    H = sum(max(i.size[1] for i in fl) for fl in filas) + 20 * len(filas) + 40
    out_img = Image.new('RGB', (W, H), 'white')
    dd = ImageDraw.Draw(out_img)
    dd.text((8, 8), 'ZPL-76884 mSafe2+ PAE - pag. 8 - puntos de borne del riel 1 de la bandeja principal. ' + leyenda,
            fill=(0, 0, 0), font=font(20))
    y = 40
    for fl in filas:
        x = 0
        for i in fl:
            out_img.paste(i, (x, y))
            x += i.size[0] + 20
        y += max(i.size[1] for i in fl) + 20
    out_img.save(out)
    print(out_img.size)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
