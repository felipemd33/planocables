"""Verificacion independiente (2da pasada) de la familia barreras: 31AIB1 (GS8536-EX), 43DIB1/43DIB2 (GS8512-EX.22).

1) Tornillos dibujados en el topografico (capa COMPONENTES, pag. PDF 8): centro x del aro exterior, y donde el
   aro es mas ancho (el aro esta cortado por el borde de la carcasa).
2) Filas no dibujadas: con las cruces de centro de tornillo de la VISTA LATERAL acotada del manual
   CZ.GS8512-EX.11(S)E-5.0 (pag. 2 del PDF, vectorial). Escala del manual con la cota 106.0 mm.
3) Escribe correcciones_barreras.json y la imagen de control control_verif_v2.png.
"""
import json, math, pickle, re, sys
from PIL import Image, ImageDraw
import pypdfium2 as pdfium

AQ = 'C:/Buscar Termos en plano/prototipos/_referencia/'
MM_TOPO = 1.4086

# ---------- 2) manual: cruces de centro de tornillo en la vista lateral ----------
L = open(AQ + 'verif_barreras/man_side.txt').read().splitlines()
H, V = [], []
for l in L:
    m = re.match(r'S 2 x ([\d.]+)-([\d.]+) y ([\d.]+)-([\d.]+)', l)
    if not m: continue
    x0, x1, y0, y1 = map(float, m.groups())
    if abs(y1 - y0) < 0.01 and 0.8 < x1 - x0 < 1.0: H.append(((x0 + x1) / 2, y0))
    if abs(x1 - x0) < 0.01 and 0.8 < y1 - y0 < 1.0: V.append((x0, (y0 + y1) / 2))
cruces = sorted({(round(h[0], 2), round(h[1], 2)) for h in H for v in V if abs(h[0] - v[0]) < .05 and abs(h[1] - v[1]) < .05})
print('cruces de tornillo (manual, pt):', cruces)
# atras (inclinado) [1 2], medio [3 4], adelante [5 6]  -> ordenadas por x (x chico = lado riel)
(xa, ya), (xm, ym), (xf, yf) = sorted(cruces)
MM_MAN = 106.0 / (194.57 - 46.86)          # cota 106.0 mm (lineas de referencia y=194.57 y y=46.86)
d12_34 = (ya - ym) * MM_MAN                # mm, [1 2] respecto de [3 4]
d56 = (ym - yf) * MM_MAN                   # mm, [5 6] hacia adentro respecto de [3 4]
d_bot = (55.78 - 43.47) * MM_MAN           # mm, [7 8] hacia adentro respecto de [9 10] (bordes exteriores de enchufe)
print('[1 2] sobre [3 4]: %.2f mm   [5 6] adentro: %.2f mm = %.2f pt   abajo [7 8] adentro: %.2f mm = %.2f pt'
      % (d12_34, d56, d56 / MM_TOPO, d_bot, d_bot / MM_TOPO))

# ---------- 1) topografico: tornillos dibujados ----------
sel = pickle.load(open(AQ + 'verif_barreras/sel.pkl', 'rb'))
aros = set()
for lay, op, pts, col in sel:
    if lay != 'COMPONENTES' or len(pts) < 16: continue
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    if 2.7 < max(xs) - min(xs) < 3.0 and 780 < min(xs) < 815:
        top = min(ys) > 560
        aros.add((round((min(xs) + max(xs)) / 2, 2), round(min(ys) if top else max(ys), 2)))
print('aros completos dibujados:', sorted(aros))
Y_T = 567.05; Y_B = 495.67; P = 3.55
Y_T1 = round(Y_T - d56 / MM_TOPO, 2); Y_B1 = round(Y_B + d_bot / MM_TOPO, 2)
print('filas: arriba exterior %.2f, arriba adelante %.2f, abajo exterior %.2f, abajo adelante %.2f' % (Y_T, Y_T1, Y_B, Y_B1))

# ---------- comparacion con la referencia ----------
ref = json.load(open(AQ + 'bornes_referencia.json', encoding='utf-8'))
pts = [p for p in ref['puntos'] if p['familia'] == 'barreras']
fila = {'1': Y_T, '2': Y_T, '3': Y_T, '4': Y_T, '5': Y_T1, '6': Y_T1, '7': Y_B1, '8': Y_B1, '9': Y_B, '10': Y_B}
mio = []
for p in pts:
    b = p['texto'].split()[1]
    y = fila[b]
    e = abs(y - p['y'])
    mio.append((p['texto'], p['cables'][0], p['x'], p['y'], y, e))
    print('%-16s %-5s ref (%.2f, %.2f)  mio y=%.2f  dif %.2f %s' % (p['texto'], p['cables'][0], p['x'], p['y'], y, e, 'MAL' if e > 1.5 else 'ok'))

# ---------- bornes cableados que faltan en el instructivo (posicion fisica) ----------
xc31 = (782.76 + 795.54) / 2    # centro de la carcasa de 31AIB1
falt = [
    ('43DIB1 4', '4329', 798.20 + P, Y_T), ('43DIB2 4', '4369', 807.15 + P, Y_T),
    ('31AIB1 3', '2139', xc31 - P, Y_T), ('31AIB1 4', '2140', xc31, Y_T),
    ('31AIB1 6', '2105', xc31 - P, Y_T1), ('31AIB1 7', '2106', xc31, Y_T1),
    ('31AIB1 9', '3104', xc31 - P, Y_B1), ('31AIB1 10', '3105', xc31, Y_B1),
    ('31AIB1 12', '3138', xc31 - P, Y_B), ('31AIB1 13', '3139', xc31, Y_B),
]

# ---------- imagen de control ----------
x0, y0, x1, y1, sc = 778, 485, 818, 578, 14
pdf = pdfium.PdfDocument(AQ + 'topografico.pdf'); page = pdf[7]
W, Hh = page.get_size()
img = page.render(scale=sc, crop=(x0, y0, W - x1, Hh - y1)).to_pil().convert('RGB')
d = ImageDraw.Draw(img)
Pp = lambda x, y: ((x - x0) * sc, (y1 - y) * sc)
for t, c, x, yr, ym_, e in mio:
    a = Pp(x, yr); b = Pp(x, ym_)
    if e > 1.5:
        d.ellipse([a[0] - 7, a[1] - 7, a[0] + 7, a[1] + 7], outline=(255, 0, 0), width=2)
        d.line([a, b], fill=(255, 0, 0), width=1)
    d.ellipse([b[0] - 6, b[1] - 6, b[0] + 6, b[1] + 6], fill=(0, 160, 0))
    d.text((b[0] + 7, b[1] - 12), t.split()[1] + ' ' + c, fill=(0, 0, 200))
for t, c, x, y in falt:
    b = Pp(x, y)
    d.ellipse([b[0] - 6, b[1] - 6, b[0] + 6, b[1] + 6], outline=(230, 120, 0), width=3)
    d.text((b[0] - 10, b[1] + 6), t.split()[1] + ' ' + c, fill=(200, 90, 0))
img.save(AQ + 'verif_barreras/control_verif_v2.png'); print('imagen', img.size)

# ---------- correcciones ----------
MOT_ARR = ("GS8512-EX.22: el borne %s esta en el enchufe verde del medio [3 4], que es el mas exterior arriba y tiene el "
           "tornillo a la MISMA altura que el enchufe de alimentacion [1 2] (que queda detras, inclinado). Vista lateral acotada "
           "del manual CZ.GS8512-EX.11(S)E-5.0: cruces de tornillo [1 2] y=%.2f, [3 4] y=%.2f pt (diferencia %.2f mm); la foto del "
           "fabricante (GS8547) muestra la tapa del lugar [3 4] y el [2 1] inclinado sobresaliendo lo mismo; en la foto 3.0 (sin el "
           "enchufe [5 6]) las punteras rojas de 1312/1313 asoman detras del [3 4] solo por perspectiva. La vista frontal del manual "
           "(3 filas parejas) es esquematica. Punto = tornillo %s de la fila exterior dibujada. El punto de la referencia (y=560.22) "
           "cae sobre el enchufe delantero [5 6].")
MOT_56 = ("GS8512-EX.22: el enchufe delantero [5 6] (pegado a la etiqueta del aparato, fotos 3.1 y 12.35.42) esta UNA fila hacia "
          "adentro de la fila exterior dibujada, no dos: en la vista lateral acotada del manual su tornillo esta %.2f mm mas adentro "
          "que el de [3 4] (= %.2f pt del topografico), y = 567.05 - %.2f. El punto de la referencia (y=553.58) queda 13.5 pt adentro, "
          "sobre la tapa de la etiqueta, donde no hay bornes. Borne %s = tornillo %s del enchufe (foto 3.1: %s). Anclando en el borde "
          "de la carcasa en vez del tornillo dibujado daria y=561.8 (1 pt de diferencia, dentro de tolerancia).")
C = [
    dict(texto='43DIB1 3', cable='1318', x=798.20, y=Y_T, confianza='media',
         motivo=MOT_ARR % ('3', ya, ym, d12_34, 'izquierdo') + ' Foto 3.0: 1318 en el 3 de 43DIB1.'),
    dict(texto='43DIB2 3', cable='1319', x=807.15, y=Y_T, confianza='media',
         motivo=MOT_ARR % ('3', ya, ym, d12_34, 'izquierdo') + ' Foto 3.0: 131(9) en el 3 de 43DIB2.'),
    dict(texto='43DIB1 5', cable='2116', x=798.20, y=Y_T1, confianza='media',
         motivo=MOT_56 % (d56, d56 / MM_TOPO, round(d56 / MM_TOPO, 2), '5', 'izquierdo', '2116 en el 5')),
    dict(texto='43DIB1 6', cable='2117', x=801.75, y=Y_T1, confianza='media',
         motivo=MOT_56 % (d56, d56 / MM_TOPO, round(d56 / MM_TOPO, 2), '6', 'derecho', '2117 en el 6')),
    dict(texto='43DIB2 5', cable='2120', x=807.15, y=Y_T1, confianza='media',
         motivo=MOT_56 % (d56, d56 / MM_TOPO, round(d56 / MM_TOPO, 2), '5', 'izquierdo', '2120 en el 5')),
    dict(texto='43DIB2 6', cable='2121', x=810.70, y=Y_T1, confianza='media',
         motivo=MOT_56 % (d56, d56 / MM_TOPO, round(d56 / MM_TOPO, 2), '6', 'derecho', '2121 en el 6')),
]
out = {
    'familia': 'barreras',
    'correcciones': C,
    'verificacion': ("Verificados los 20 puntos de 31AIB1, 43DIB1 y 43DIB2 con geometria propia (page_strokes: aros de tornillo "
                     "completos arriba en x 790.63/801.75/810.70 y abajo en 787.29/798.27/807.22, carcasas x 782.76-795.54-804.48-813.43, "
                     "borde superior 566.5 e inferior 496.22 = 99.0 mm como la cota del manual), vista lateral acotada del manual "
                     "GS8512-EX, fotos 3.0-3.3, 12.35.42/43 y foto del fabricante, y hojas 15, 31 y 43 del funcional. Regla del tag: "
                     "cada barrera tiene su etiqueta sobre su propia carcasa y todos sus puntos caen dentro de ella; no hay piezas del "
                     "vecino. 14 puntos bien (1, 2, 7, 8, 9, 10 de cada barrera; dif <= 0.1 pt). 6 corregidos (3, 5, 6 de 43DIB1/43DIB2): "
                     "la referencia uso las fracciones de la vista frontal esquematica (3 filas parejas); la vista lateral acotada da "
                     "[1 2] y [3 4] a la misma altura (fila exterior dibujada) y [5 6] %.2f pt mas adentro. Script: "
                     "verif_barreras/verificar_v2.py; imagen: verif_barreras/control_verif_v2.png." % (d56 / MM_TOPO)),
    'bornes_cableados_sin_uso_en_instructivo': [dict(texto=t, cable=c, x=round(x, 2), y=round(y, 2)) for t, c, x, y in falt],
}
json.dump(out, open(AQ + 'correcciones_barreras.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('correcciones escritas:', len(C))
