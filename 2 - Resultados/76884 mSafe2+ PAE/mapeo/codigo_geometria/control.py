# -*- coding: utf-8 -*-
import json, sys, os
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
PROC = r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
OUT = r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo'
J = json.load(open(os.path.join(OUT, 'bandejas.json'), encoding='utf-8'))
S = float(sys.argv[1]) if len(sys.argv) > 1 else 2.2
X0, Y0, X1, Y1 = 180, 120, 1120, 805
doc = pdfium.PdfDocument(PROC); p = doc[7]; W, H = p.get_size()
base = p.render(scale=S, crop=(X0, Y0, W - X1, H - Y1)).to_pil().convert('RGBA')
ov = Image.new('RGBA', base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
try:
    F = ImageFont.truetype('arial.ttf', max(9, int(4.2 * S))); FS = ImageFont.truetype('arial.ttf', max(8, int(3.0 * S)))
    FB = ImageFont.truetype('arialbd.ttf', max(12, int(7 * S)))
except Exception:
    F = FS = FB = ImageFont.load_default()
T = lambda x, y: ((x - X0) * S, (Y1 - y) * S)
def R(b): (a, c), (e, f) = T(b[0], b[3]), T(b[2], b[1]); return [a, c, e, f]
for key, nombre in (('principal', 'BANDEJA PRINCIPAL'), ('lateral_izquierda', 'BANDEJA LATERAL IZQUIERDA')):
    t = J[key]
    d.rectangle(R(t['region']), outline=(200, 0, 200, 255), width=max(2, int(S)))
    x, y = T(t['region'][0], t['region'][3]); d.text((x + 4, y - 7 * S - 6), nombre + ' (region)', fill=(200, 0, 200, 255), font=FB)
    for k in t['canaletas']:
        col = (0, 90, 255, 70) if 'azul' in k['tipo'] else (110, 110, 110, 70)
        oc = (0, 60, 220, 255) if 'azul' in k['tipo'] else (70, 70, 70, 255)
        d.rectangle(R(k['b']), fill=col, outline=oc, width=2)
        cx, cy = T((k['b'][0] + k['b'][2]) / 2, (k['b'][1] + k['b'][3]) / 2)
        d.text((cx - 10, cy - 8), k['id'] + (' AZUL' if 'azul' in k['tipo'] else ''), fill=oc, font=F)
    for r in t['rieles']:
        d.rectangle(R([r['x0'], r['y0'], r['x1'], r['y1']]), fill=(255, 140, 0, 55), outline=(255, 120, 0, 255), width=1)
        a, yy = T(r['x0'], r['y_eje']); b, _ = T(r['x1'], r['y_eje'])
        for xx in range(int(a), int(b), 12): d.line([(xx, yy), (min(xx + 6, b), yy)], fill=(230, 0, 0, 255), width=2)
        d.text((a + 2, yy - 2 * S - 12), '%s riel %d (%s) y=%.2f' % (r['id'], r['numero'], r['tramo'][:3], r['y_eje']), fill=(200, 60, 0, 255), font=FS)
        for t0, t1 in r['topes']:
            d.rectangle(R([t0, r['y_eje'] - 2, t1, r['y_eje'] + 2]), fill=(150, 0, 200, 160))
    for tag, a in t['aparatos'].items():
        d.rectangle(R(a['caja']), outline=(0, 170, 0, 255), width=2)
        for pz in a.get('piezas', []):
            for xv in (pz['x0'], pz['x1']):
                u, v0 = T(xv, a['caja'][1]); _, v1 = T(xv, a['caja'][1] + 4)
                d.line([(u, v0), (u, v1)], fill=(0, 140, 0, 255), width=1)
        for m in a.get('modulos', []):
            u, v0 = T(m['x0'], a['caja'][3]); _, v1 = T(m['x0'], a['caja'][3] - 4)
            d.line([(u, v0), (u, v1)], fill=(0, 140, 0, 255), width=1)
        cx, cy = T(a['x'], a['y'])
        d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(255, 0, 0, 255))
        d.text((cx + 5, cy - 6), tag, fill=(220, 0, 0, 255), font=FS)
        for n in a['numeros_borne_dibujados']:
            u, v = T(n['x'], n['y'])
            d.ellipse([u - 2.5, v - 2.5, u + 2.5, v + 2.5], outline=(0, 180, 220, 255), width=2)
    for o in t.get('otros_elementos', []):
        if 'b' in o and 'hueco' in o['que']:
            d.rectangle(R(o['b']), outline=(255, 0, 255, 255), width=2)
            x, y = T(o['b'][0], o['b'][3]); d.text((x + 3, y + 3), 'hueco (11MS1?)', fill=(255, 0, 255, 255), font=FS)
for (x, y), txt in ((T(590, 290), 'zona electrica | zona hidraulica ->'),):
    pass
x, y = T(913.57, 752)
d.line([T(913.57, 129.29), T(913.57, 745.83)], fill=(200, 0, 200, 180), width=1)
d.text((x - 95, y), 'zona electrica  |  zona hidraulica', fill=(200, 0, 200, 255), font=F)
leg = ['LEYENDA: magenta = region de bandeja; gris = canaleta comun; azul = canaleta intrinseca; naranja = riel DIN (35 mm) con eje rojo; violeta = topes;',
       'verde = caja del aparato (marcas = limites de piezas/modulos); punto rojo = centro de la etiqueta; circulo celeste = numero de borne dibujado. Escala 1:4 (1.41111 mm/pt)']
for i, l in enumerate(leg): d.text((10, base.size[1] - 40 + i * 16), l, fill=(0, 0, 0, 255), font=FS)
img = Image.alpha_composite(base, ov).convert('RGB')
img.save(os.path.join(OUT, 'control_bandejas.png'))
print(img.size)
