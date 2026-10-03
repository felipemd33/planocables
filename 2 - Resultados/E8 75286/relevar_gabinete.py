"""Relevamiento del gabinete del 75286 (topografico 75441 rev 6) para E8 en 3D -> gabinete.json + control_gabinete.png

Solo lee: copia topografico.pdf, layout.json e instructivo.json del trabajo a una carpeta temporal y lee de ahi
(el trabajo del usuario no se toca). Usa el lector del programa (pdfvec, textdec, topo) sin modificarlo.

Lo que sale del PDF automaticamente: etiquetas de los aparatos (texto SHX + OCR de las chicas), cajas de los aparatos
(trazos de las capas de componentes), rieles DIN, canaletas, salidas a LI de las rutas del instructivo.
Lo que esta medido a mano en esta sesion (recuadros de cada vista, escalas) va en VISTAS con su fuente, y el script
lo VERIFICA contra la geometria del PDF (recuadros TABLERO de la hoja) y contra las cotas.

Uso:  python relevar_gabinete.py
"""
import sys, os, json, math, shutil, tempfile, collections, re

PROG = 'C:/Buscar Termos en plano/programa'
sys.path.insert(0, PROG)
import pypdf
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
from pdfvec import page_strokes, layer_names
from textdec import Decoder, page_text, bbox, DSU
from topo import unir_partidas, etiquetas_hoja, rail_bands, rect_of, ocr_crop, match_tag

TRABAJO = 'C:/Buscar Termos en plano/3 - Historial web/ac0f0949510a'
OUT = os.path.dirname(os.path.abspath(__file__))
BASE = 'C:/Buscar Termos en plano/pruebas/bases/base_75287.json'

# ---------------------------------------------------------------------------------------------------------------
# Supuestos de montaje (no estan en el plano): ver 'supuestos' en el JSON
Z_FONDO = 20.0       # cara de montaje de la placa de fondo, desde la cara exterior del fondo (fin de los perfiles soldados)
X_LI = 25.0          # cara de montaje de la placa lateral izquierda, desde la cara exterior izquierda
X_LD = 775.0         # cara de montaje del lateral derecho (perfiles soldados), desde la cara exterior izquierda
Z_PUERTA = 428.0     # cara interior de la chapa de la puerta cerrada (puerta de 30 mm: de z=400 a z=430)
Y_PISO = 1.5         # cara interior del piso
PROF_CANALETA = {'fondo': 80.0, 'lateral_izquierda': 40.0, 'puerta': 40.0}   # CD 40x80 / CD 40x40
PROF_RIEL = 7.5      # NS 35/7,5

# ---------------------------------------------------------------------------------------------------------------
# Vistas: recuadros medidos en el PDF (pt, origen abajo a la izquierda, y hacia arriba) y su ubicacion en el gabinete.
# Gabinete: x = ancho (0 = cara exterior IZQUIERDA vista de frente), y = alto (0 = piso exterior),
#           z = profundidad (0 = cara exterior del FONDO, crece hacia la puerta; 400 = plano del frente del cuerpo).
VISTAS = [
    dict(id='fondo', nombre='Placa de fondo (la bandeja de E6)', zona='bandeja', pared='fondo', pagina=8, hoja='07',
         titulo_plano='VISTA DE FRENTE (hoja 07 "Vista detallada de componentes montados", sin titulo propio)',
         escala=1.4086,
         escala_fuente='placa 740 x 820 (cotas de la hoja 08) contra su recuadro en la hoja 07 (525,3 x 582,2 pt); '
                       'igual a layout.json; contorno del gabinete 567,9 x 667,3 pt = 800 x 940 mm',
         region_pt=[520.1, 177.1, 1045.4, 759.3], vista_pt=[498.8, 134.9, 1066.7, 802.2],
         origen_pt=[498.8, 134.9], origen_mm=[0.0, 0.0, Z_FONDO], eje_X=[1, 0, 0], eje_Y=[0, 1, 0], normal=[0, 0, 1],
         desde='de frente, con la puerta abierta (igual que el instructivo de E6): la izquierda de la hoja es la '
               'izquierda del gabinete',
         placa_mm=dict(ancho=740, alto=820, espesor=1.5),
         otras=[dict(pagina=9, hoja='08', region_pt=[503.2, 162.6, 1052.3, 771.0], escala=1.3478,
                     que='mecanizado de la placa con cotas (rieles, canaletas, agujeros)'),
                dict(pagina=6, hoja='05', region_pt=[455.3, 170.5, 755.0, 502.6], escala=2.4691,
                     que='vista general del interior (VISTA DE FRENTE)')]),
    dict(id='lateral_izquierda', nombre='Lateral izquierdo (LI)', zona='lateral izq', pared='lateral_izquierda',
         pagina=8, hoja='07',
         titulo_plano='vista lateral a la izquierda de la hoja 07 (sin titulo); en la hoja 05 la misma pared se titula '
                      '"VISTA DERECHA"',
         escala=1.4086,
         escala_fuente='misma hoja que la bandeja; placa lateral 310 x 810 (cotas hoja 08) = 220,1 x 575,0 pt; '
                       'cuerpo 400 x 940 = 283,9 x 667,3 pt',
         region_pt=[179.8, 170.4, 399.9, 745.4], vista_pt=[179.5, 134.9, 463.4, 802.2],
         origen_pt=[179.5, 134.9], origen_mm=[X_LI, 0.0, 400.0], eje_X=[0, 0, -1], eje_Y=[0, 1, 0], normal=[1, 0, 0],
         desde='desde ADENTRO del gabinete mirando la pared izquierda: el frente (puerta) a la izquierda de la hoja y '
               'el fondo a la derecha',
         placa_mm=dict(ancho=310, alto=810, espesor=1.5),
         otras=[dict(pagina=9, hoja='08', region_pt=[166.0, 155.6, 396.0, 756.5], escala=1.3478,
                     que='mecanizado de la placa lateral con cotas'),
                dict(pagina=6, hoja='05', region_pt=[261.2, 166.7, 386.7, 494.7], escala=2.4691,
                     que='vista general, titulada "VISTA DERECHA"')]),
    dict(id='lateral_derecha', nombre='Lateral derecho (LD)', zona='lateral der', pared='lateral_derecha',
         pagina=6, hoja='05',
         titulo_plano='"VISTA IZQUIERDA" de la hoja 05 (a la derecha de la hoja); es la pared derecha vista desde adentro',
         escala=2.4691,
         escala_fuente='contorno de la vista de frente de la hoja 05 = 324,0 x 380,7 pt = 800 x 940; '
                       'cuerpo lateral 162,0 pt = 400 mm; perfil del riel DIN 14,1 pt = 35 mm',
         region_pt=[787.3, 146.4, 949.3, 527.1], vista_pt=[787.3, 146.4, 949.3, 527.1],
         origen_pt=[787.3, 146.4], origen_mm=[X_LD, 0.0, 0.0], eje_X=[0, 0, 1], eje_Y=[0, 1, 0], normal=[-1, 0, 0],
         desde='desde ADENTRO del gabinete mirando la pared derecha: el fondo a la izquierda de la hoja y el frente '
               '(puerta) a la derecha',
         placa_mm=None, otras=[]),
    dict(id='puerta', nombre='Puerta, cara interior', zona='puerta', pared='puerta', pagina=5, hoja='04',
         titulo_plano='VISTA POSTERIOR PUERTA (hoja 04)',
         escala=1.5776,
         escala_fuente='canaleta CD 40x40: 363,7 x 25,3 pt = cotas 574 x 40; contorno 507,1 x 595,8 pt = 800 x 940',
         region_pt=[357.2, 149.8, 860.5, 716.5], vista_pt=[355.3, 147.9, 862.4, 743.7],
         origen_pt=[355.3, 147.9], origen_mm=[800.0, 0.0, Z_PUERTA], eje_X=[-1, 0, 0], eje_Y=[0, 1, 0],
         normal=[0, 0, -1],
         desde='desde ADENTRO (la puerta vista por detras): la izquierda de la hoja es la DERECHA del gabinete '
               '(espejado); las coordenadas en mm son con la puerta CERRADA',
         placa_mm=dict(ancho=794, alto=894, espesor=1.5), otras=[]),
    dict(id='piso', nombre='Piso (vista inferior)', zona='otro', pared='piso', pagina=6, hoja='05',
         titulo_plano='VISTA INFERIOR (hoja 05)',
         escala=2.4691, escala_fuente='misma hoja 05: 324,0 x 162,0 pt = 800 x 400',
         region_pt=[443.1, 568.7, 767.1, 730.7], vista_pt=[443.1, 568.7, 767.1, 730.7],
         origen_pt=[443.1, 568.7], origen_mm=[0.0, Y_PISO, 0.0], eje_X=[1, 0, 0], eje_Y=[0, 0, 1], normal=[0, 1, 0],
         desde='desde ABAJO (primer diedro, va arriba de la vista de frente): el frente (puerta) arriba en la hoja, '
               'la izquierda del gabinete a la izquierda',
         placa_mm=None,
         otras=[dict(pagina=4, hoja='03', region_pt=[436.3, 564.0, 773.2, 732.4], escala=2.3739,
                     que='vista inferior exterior con las cotas de los agujeros de prensacables')]),
]
VISTAS_EXT = [
    dict(id='frente_exterior', nombre='Frente (puerta por fuera)', pared='puerta_exterior', pagina=3, hoja='02',
         titulo_plano='VISTA DE FRENTE (hoja 02)', escala=2.4638,
         escala_fuente='contorno 324,7 x 381,5 pt = 800 x 940',
         vista_pt=[451.2, 142.6, 775.9, 524.1], origen_pt=[451.2, 142.6], origen_mm=[0.0, 0.0, 430.0],
         eje_X=[1, 0, 0], eje_Y=[0, 1, 0], normal=[0, 0, 1], desde='de frente, desde afuera'),
    dict(id='lateral_izquierda_exterior', nombre='Costado izquierdo por fuera', pared='lateral_izquierda_exterior',
         pagina=3, hoja='02', titulo_plano='"VISTA IZQUIERDA" a la derecha de la hoja 02 (manija de 11MS1)',
         escala=2.4638, escala_fuente='misma hoja: 174,5 pt = 430 mm (cuerpo 400 + puerta 30)',
         vista_pt=[839.5, 142.6, 1014.1, 524.1], origen_pt=[839.5, 142.6], origen_mm=[0.0, 0.0, 0.0],
         eje_X=[0, 0, 1], eje_Y=[0, 1, 0], normal=[-1, 0, 0],
         desde='desde afuera, del lado izquierdo: el fondo a la izquierda de la hoja y la puerta a la derecha'),
    dict(id='lateral_derecha_exterior', nombre='Costado derecho por fuera', pared='lateral_derecha_exterior',
         pagina=3, hoja='02', titulo_plano='"VISTA IZQUIERDA" a la izquierda de la hoja 02 (el titulo esta mal: es la derecha)',
         escala=2.4638, escala_fuente='misma hoja: 174,5 pt = 430 mm',
         vista_pt=[213.0, 142.6, 387.5, 524.1], origen_pt=[213.0, 142.6], origen_mm=[800.0, 0.0, 430.0],
         eje_X=[0, 0, -1], eje_Y=[0, 1, 0], normal=[1, 0, 0],
         desde='desde afuera, del lado derecho: la puerta a la izquierda de la hoja y el fondo a la derecha'),
]
POR_ID = {v['id']: v for v in VISTAS + VISTAS_EXT}

# recuadros TABLERO que tienen que existir en el PDF (verificacion de lo medido): (pagina, rect, ancho_mm, alto_mm, que)
CHEQUEO_RECT = [
    (8, [520.1, 177.1, 1045.4, 759.3], 740, 820, 'placa de fondo (hoja 07)'),
    (8, [498.8, 134.9, 1066.7, 802.2], 800, 940, 'contorno del gabinete en la vista de frente (hoja 07)'),
    (8, [179.8, 170.4, 399.9, 745.4], 310, 810, 'placa lateral izquierda (hoja 07)'),
    (9, [503.2, 162.6, 1052.3, 771.0], 740, 820, 'placa de fondo (hoja 08, con cotas)'),
    (9, [166.0, 155.6, 396.0, 756.5], 310, 810, 'placa lateral (hoja 08, con cotas)'),
    (5, [355.3, 147.9, 862.4, 743.7], 800, 940, 'contorno en la vista posterior de puerta (hoja 04)'),
    (6, [443.1, 146.4, 767.1, 527.1], 800, 940, 'contorno de la vista de frente (hoja 05)'),
    (6, [443.1, 568.7, 767.1, 730.7], 800, 400, 'vista inferior (hoja 05)'),
    (4, [436.3, 564.0, 773.2, 732.4], 800, 400, 'vista inferior exterior (hoja 03)'),
    (3, [451.2, 142.6, 775.9, 524.1], 800, 940, 'vista de frente exterior (hoja 02)'),
]
ESCALA_PAG = {8: 1.4086, 9: 1.3478, 5: 1.5776, 6: 2.4691, 4: 2.3739, 3: 2.4638}

CAPAS_COMP = ('COMPONENTES', '00_COMPONENTS', '_IGV_Componentes', '00_COMPONENTS_1')


def r1(v, n=1):
    return round(float(v), n)


def a_mm(v, X, Y):
    e = v['escala']; X0, Y0 = v['origen_pt']; O = v['origen_mm']; u = v['eje_X']; w = v['eje_Y']
    return [r1(O[i] + e * ((X - X0) * u[i] + (Y - Y0) * w[i])) for i in range(3)]


def matriz(v):
    """[x, y, z] = M . [X, Y, 1]  (X, Y en pt de la hoja; x, y, z en mm del gabinete)"""
    e = v['escala']; X0, Y0 = v['origen_pt']; O = v['origen_mm']; u = v['eje_X']; w = v['eje_Y']
    return [[r1(e * u[i], 5), r1(e * w[i], 5), r1(O[i] - e * (X0 * u[i] + Y0 * w[i]), 3)] for i in range(3)]


def caja_mm(v, b, z_extra=0.0):
    """recuadro en pt de una vista -> caja 3D {min, max} en mm (z_extra = lo que sobresale de la cara, hacia la normal)"""
    p = [a_mm(v, b[0], b[1]), a_mm(v, b[2], b[3])]
    n = v['normal']
    q = [[p[0][i] + n[i] * z_extra for i in range(3)], [p[1][i] + n[i] * z_extra for i in range(3)]]
    pts = p + q
    return dict(min=[r1(min(t[i] for t in pts)) for i in range(3)], max=[r1(max(t[i] for t in pts)) for i in range(3)])


def dentro(b, x, y, m=0.0):
    return b[0] - m <= x <= b[2] + m and b[1] - m <= y <= b[3] + m


def clusters(st, region, tol=0.3):
    """trazos de las capas de componentes dentro de 'region' agrupados por contacto de sus recuadros"""
    bs = [bbox(p) for l, o, p, *_ in st if l in CAPAS_COMP and len(p) >= 2]
    bs = [b for b in bs if b[0] >= region[0] and b[2] <= region[2] and b[1] >= region[1] and b[3] <= region[3]]
    n = len(bs); d = DSU(n)
    order = sorted(range(n), key=lambda i: bs[i][0])
    for ii, i in enumerate(order):
        for j in order[ii + 1:]:
            if bs[j][0] > bs[i][2] + tol:
                break
            if bs[j][1] <= bs[i][3] + tol and bs[i][1] <= bs[j][3] + tol:
                d.u(i, j)
    g = collections.defaultdict(list)
    for i in range(n):
        g[d.f(i)].append(bs[i])
    out = [dict(b=[min(b[0] for b in v), min(b[1] for b in v), max(b[2] for b in v), max(b[3] for b in v)], n=len(v))
           for v in g.values()]
    return [c for c in out if c['n'] >= 3]


def unir_partido_por_riel(cs, H):
    """un aparato partido por el riel DIN (el riel esta en otra capa): dos grupos con el mismo ancho, uno arriba del
    otro y separados a lo sumo por un perfil de riel, son el mismo aparato (11MS1)"""
    cs = [dict(c) for c in cs]
    cambio = True
    while cambio:
        cambio = False
        for i, a in enumerate(cs):
            for j, b in enumerate(cs):
                if i >= j:
                    continue
                A, B = a['b'], b['b']
                if abs(A[0] - B[0]) < 1 and abs(A[2] - B[2]) < 1:
                    gap = max(A[1], B[1]) - min(A[3], B[3])
                    if 0 <= gap <= 1.05 * H:
                        a['b'] = [min(A[0], B[0]), min(A[1], B[1]), max(A[2], B[2]), max(A[3], B[3])]
                        a['n'] += b['n']; cs.pop(j); cambio = True
                        break
            if cambio:
                break
    return cs


def caja_de(cs, x, y, vista_box):
    """el grupo de trazos que es el aparato de la etiqueta (x, y): el que la contiene, o el mas cercano (<= 15 pt);
    no vale un grupo de mas del 60 % de la vista"""
    area_v = (vista_box[2] - vista_box[0]) * (vista_box[3] - vista_box[1])
    lados = lambda b: (b[2] - b[0], b[3] - b[1])
    # fuera: grupos enormes (mas del 60 % de la vista) y alargados (perfiles, soportes de canaleta: largo > 6 x ancho)
    ok = [c for c in cs if lados(c['b'])[0] * lados(c['b'])[1] < 0.6 * area_v
          and max(lados(c['b'])) <= 6 * max(min(lados(c['b'])), 0.1)]
    cont = [c for c in ok if dentro(c['b'], x, y, 0.5)]
    if cont:
        return min(cont, key=lambda c: (c['b'][2] - c['b'][0]) * (c['b'][3] - c['b'][1]))['b']
    def dist(c):
        b = c['b']
        dx = max(b[0] - x, 0, x - b[2]); dy = max(b[1] - y, 0, y - b[3])
        return math.hypot(dx, dy)
    cerca = [c for c in ok if dist(c) <= 15 and c['n'] >= 10]
    return min(cerca, key=dist)['b'] if cerca else None


def main():
    tmp = tempfile.mkdtemp(prefix='e8_75286_')
    for f in ('topografico.pdf', 'layout.json', 'instructivo.json'):
        shutil.copy2(os.path.join(TRABAJO, f), tmp)
    pdf = os.path.join(tmp, 'topografico.pdf')
    lay = json.load(open(os.path.join(tmp, 'layout.json'), encoding='utf-8'))
    ins = json.load(open(os.path.join(tmp, 'instructivo.json'), encoding='utf-8'))
    reader = pypdf.PdfReader(pdf); names = layer_names(reader)
    dec = Decoder()
    st_cache = {}
    def st(p):
        if p not in st_cache:
            st_cache[p] = page_strokes(reader, p - 1, names)
        return st_cache[p]

    verif = []
    # 1) recuadros medidos: tienen que estar en la capa TABLERO de la hoja y dar las medidas de las cotas
    for p, rr, w, h, que in CHEQUEO_RECT:
        rects = [rect_of(q, o) for l, o, q in st(p) if l == 'TABLERO']
        hay = any(r and all(abs(r[i] - rr[i]) < 0.3 for i in range(4)) for r in rects)
        e = ESCALA_PAG[p]
        verif.append(dict(que=que, pagina=p, encontrado_en_pdf=hay,
                          medida_mm=[r1((rr[2] - rr[0]) * e), r1((rr[3] - rr[1]) * e)], esperado_mm=[w, h]))

    known = sorted({c['tag'] for c in ins['componentes']} | set(lay['comp']) | {'21PCB01', '41DS', 'SP-1', 'SP-2'})

    # 2) etiquetas de aparatos de cada hoja
    def etiquetas(p, region):
        lines = unir_partidas(page_text(st(p), dec, ('WATERMARK',)))
        hits = etiquetas_hoja(pdf, p - 1, lines, known, dec)
        # las chicas sin digitos legibles ('?') de la capa de etiquetas: OCR derecho (41DS en la hoja 05)
        for l in lines:
            b = l['bbox']; cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if not dentro(region, cx, cy) or 'ETIQUETA' not in l.get('layer', '').upper():
                continue
            if any(abs(h['x'] - cx) < 1 and abs(h['y'] - cy) < 1 for h in hits):
                continue
            for ang in (l['ang'], 0):
                k = match_tag(ocr_crop(pdf, p - 1, b, ang, dec), known)
                if k:
                    hits.append(dict(tag=k, leido=k + ' (OCR)', x=cx, y=cy)); break
        # caja de la etiqueta: el recuadro de la capa '_IGV_Componentes Txt' que la contiene (une 'BH-01' + '-M')
        cajas = [rect_of(q, o) for l, o, q in st(p) if l == '_IGV_Componentes Txt']
        cajas = [c for c in cajas if c]
        for h in hits:
            cs = [c for c in cajas if dentro(c, h['x'], h['y'], 0.3)]
            if cs:
                c = min(cs, key=lambda c: (c[2] - c[0]) * (c[3] - c[1]))
                h['caja_etiqueta'] = [r1(v) for v in c]
                h['x'], h['y'] = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
                # etiqueta horizontal partida en varios textos ('BH-01' + '-M'): se lee entera
                piezas = sorted((l for l in lines if l['ang'] == 0 and dentro(c, (l['bbox'][0] + l['bbox'][2]) / 2,
                                                                                (l['bbox'][1] + l['bbox'][3]) / 2, 0.3)),
                                key=lambda l: l['bbox'][0])
                if len(piezas) > 1:
                    h['leido'] = ''.join(l['text'].strip() for l in piezas)
        return [h for h in hits if dentro(region, h['x'], h['y'])]

    # 3) rieles DIN y canaletas por vista
    rieles = []
    for b in rail_bands(st(8)):
        for vid in ('fondo', 'lateral_izquierda'):
            v = POR_ID[vid]
            if dentro(v['vista_pt'], (b['x0'] + b['x1']) / 2, b['eje']):
                rieles.append(dict(vista=vid, tipo='riel DIN NS 35/7,5 perforado', pt=[r1(b['x0']), r1(b['y0']), r1(b['x1']), r1(b['y1'])],
                                   eje_pt=r1(b['eje']), caja_mm=caja_mm(v, [b['x0'], b['y0'], b['x1'], b['y1']], PROF_RIEL)))
    # perfiles soldados (soporte de las placas laterales): TABLERO de 380 x 55 mm
    for vid, p in (('lateral_izquierda', 8), ('lateral_derecha', 6)):
        v = POR_ID[vid]; e = v['escala']
        for l, o, q in st(p):
            if l != 'TABLERO':
                continue
            r = rect_of(q, o)
            if r and dentro(v['vista_pt'], (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, 1) and \
                    abs((r[2] - r[0]) * e - 380) < 4 and abs((r[3] - r[1]) * e - 55) < 3:
                # el perfil queda DETRAS de la cara de montaje (entre la pared y la placa): hacia -normal
                rieles.append(dict(vista=vid, tipo='perfil soldado de la pared (sostiene la placa lateral; 380 x 55)',
                                   pt=[r1(x) for x in r], caja_mm=caja_mm(v, r, -(X_LI - 5.0))))

    canaletas = []
    for d in lay['ductos']:
        b = d['b']; v = POR_ID['fondo']
        canaletas.append(dict(vista='fondo', pt=b, horizontal=d['h'], intrinseca=d['ex'],
                              tipo='CD 40x80 BU (azul, intrínsecos)' if d['ex'] else 'CD 40x80 (gris)',
                              ancho_mm=r1(((b[3] - b[1]) if d['h'] else (b[2] - b[0])) * v['escala']),
                              largo_mm=r1(((b[2] - b[0]) if d['h'] else (b[3] - b[1])) * v['escala']),
                              profundidad_mm=PROF_CANALETA['fondo'], fuente='layout.json (ductos) + rótulos CD 40x80 de la hoja 08',
                              caja_mm=caja_mm(v, b, PROF_CANALETA['fondo'])))
    for vid, p, tipo, fuente in (('lateral_izquierda', 8, 'canaleta 40 mm (sin rótulo de modelo)',
                                  'capa CABLECANAL de la hoja 07; ancho 40 y largo 230 = cotas de la hoja 08'),
                                 ('puerta', 5, 'CD 40x40', 'capa CABLECANAL de la hoja 04; cotas 574 y 40, rótulo CD40x40')):
        v = POR_ID[vid]; vistos = set()
        for l, o, q in st(p):
            if l != 'CABLECANAL' or o not in ('f', 'F', 'f*'):
                continue
            r = rect_of(q, o)
            if not r or not dentro(v['vista_pt'], (r[0] + r[2]) / 2, (r[1] + r[3]) / 2):
                continue
            k = tuple(round(x) for x in r)
            if k in vistos:
                continue
            vistos.add(k)
            h = (r[2] - r[0]) >= (r[3] - r[1])
            canaletas.append(dict(vista=vid, pt=[r1(x) for x in r], horizontal=h, intrinseca=False, tipo=tipo,
                                  ancho_mm=r1(((r[3] - r[1]) if h else (r[2] - r[0])) * v['escala']),
                                  largo_mm=r1(((r[2] - r[0]) if h else (r[3] - r[1])) * v['escala']),
                                  profundidad_mm=PROF_CANALETA[vid], fuente=fuente, caja_mm=caja_mm(v, r, PROF_CANALETA[vid])))

    # 4) aparatos
    H8 = lay.get('perfil_riel_pt') or 24.8
    aparatos = []
    comp_lay = lay['comp']
    hits8 = etiquetas(8, [100, 100, 1100, 800])
    hits5 = etiquetas(5, POR_ID['puerta']['vista_pt'])
    hits6 = etiquetas(6, POR_ID['lateral_derecha']['vista_pt'])
    piso_y = POR_ID['fondo']['vista_pt'][1] + 0.6           # sin los prensacables de abajo del gabinete
    cl_li = unir_partido_por_riel(clusters(st(8), [175, piso_y, 470, 805]), H8)
    cl_fo = clusters(st(8), [500, piso_y, 1070, 805])
    mas = lambda b, m: [b[0] - m, b[1] - m, b[2] + m, b[3] + m]     # lo que asoma del borde (actuador de 41DS)
    cl_pu = clusters(st(5), mas(POR_ID['puerta']['vista_pt'], 15))
    cl_ld = clusters(st(6), mas(POR_ID['lateral_derecha']['vista_pt'], 15))

    FISICO = {   # donde esta de verdad lo que se dibuja en la vista de frente fuera de los rieles
        '12PB1': ('otro', 'batería', 'piso', 'batería sobre el piso, abajo a la izquierda (dibujada en la vista de frente, '
                  'de costado en la vista lateral y de abajo en la vista inferior)'),
        'BH-01': ('otro', 'zona hidráulica', 'fondo', 'motor-bomba con tanque VIBO (etiqueta "BH-01-M"), abajo a la '
                  'derecha, apoyada en el piso contra la placa de fondo'),
        'SP-1': ('otro', 'zona hidráulica', 'piso', 'solenoide SP-1 del bloque de válvulas apoyado en el piso (cables 6204 '
                 'y 6205; el lector no lo tiene entre los componentes del funcional)'),
        'SP-2': ('otro', 'zona hidráulica', 'piso', 'solenoide SP-2 del bloque de válvulas apoyado en el piso (cables 6207 '
                 'y 6208; el lector no lo tiene entre los componentes del funcional)'),
        '12F2': ('bandeja', None, 'fondo', 'portafusible de 35 mm² en la placa de fondo, debajo de la canaleta de abajo '
                 '(sus cables 1204 y 1215 son de E8)'),
    }

    def agregar(h, vid, cs, nota=None):
        v = POR_ID[vid]
        tag = h['tag']; x, y = h['x'], h['y']
        ap = dict(tag=tag, leido=h.get('leido'), vista=vid, pagina=v['pagina'], zona=v['zona'], subzona=None,
                  apoyado_en=v['pared'], estacion='E8', etiqueta_pt=[r1(x), r1(y)], etiqueta_mm=a_mm(v, x, y))
        if h.get('caja_etiqueta'):
            ap['caja_etiqueta_pt'] = h['caja_etiqueta']
        c = lay_c = comp_lay.get(tag)
        if vid == 'fondo':
            if lay_c and lay_c.get('ubic') == 'BANDEJA' and tag not in FISICO:
                ap.update(zona='bandeja', estacion='E6', fila=lay_c.get('fila'))
        if tag in FISICO:
            z, sub, pared, txt = FISICO[tag]
            ap.update(zona=z, subzona=sub, apoyado_en=pared, nota=txt)
            if tag == '12F2':
                ap['fila_layout'] = (lay_c or {}).get('fila')
        if cs is not None and ap['estacion'] == 'E8':
            b = caja_de(cs, x, y, v['vista_pt'])
            if b:
                ap['caja_pt'] = [r1(t) for t in b]
                ap['centro_mm'] = a_mm(v, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
                ap['tamano_mm'] = [r1((b[2] - b[0]) * v['escala']), r1((b[3] - b[1]) * v['escala'])]
        if nota:
            ap['nota'] = '. '.join(t for t in (ap.get('nota', '').rstrip('. '), nota) if t)
        aparatos.append(ap)
        return ap

    vistos = set()
    for h in sorted(hits8, key=lambda h: (-h['y'], h['x'])):
        vid = next((k for k in ('fondo', 'lateral_izquierda') if dentro(POR_ID[k]['vista_pt'], h['x'], h['y'])), None)
        if vid is None or (h['tag'], vid) in vistos:
            continue
        vistos.add((h['tag'], vid))
        agregar(h, vid, cl_fo if vid == 'fondo' else cl_li)
    for h in hits5:
        agregar(h, 'puerta', cl_pu)
    for h in hits6:
        agregar(h, 'lateral_derecha', cl_ld)
    # 21PCB01: la placa electronica de la puerta no tiene etiqueta amarilla en el topografico
    pcb = max(cl_pu, key=lambda c: c['n'])['b']
    v = POR_ID['puerta']
    aparatos.append(dict(tag='21PCB01', leido=None, vista='puerta', pagina=5, zona='puerta', subzona=None,
                         apoyado_en='puerta', estacion='E8', etiqueta_pt=None, etiqueta_mm=None,
                         caja_pt=[r1(t) for t in pcb], centro_mm=a_mm(v, (pcb[0] + pcb[2]) / 2, (pcb[1] + pcb[3]) / 2),
                         tamano_mm=[r1((pcb[2] - pcb[0]) * v['escala']), r1((pcb[3] - pcb[1]) * v['escala'])],
                         nota='sin etiqueta en el topográfico: es la placa electrónica con su "PROTECTOR PLACA E2.5" '
                              '(76254-1) de la hoja 04; identificada con las fotos E08 (cables 21xx en las borneras '
                              'AI#1 ... PORT#1)'))
    # profundidad de la bateria: de la vista lateral (la vista de frente no la da)
    v_li = POR_ID['lateral_izquierda']
    bat_lat = next((c['b'] for c in cl_li if c['b'][1] <= piso_y + 1 and (c['b'][2] - c['b'][0]) * v_li['escala'] > 200), None)
    for ap in aparatos:
        if ap['tag'] == '12PB1' and bat_lat:
            z0 = a_mm(v_li, bat_lat[2], bat_lat[1])[2]; z1 = a_mm(v_li, bat_lat[0], bat_lat[3])[2]
            ap['profundidad_mm'] = dict(z_min=z0, z_max=z1, fuente='vista lateral de la hoja 07 (de costado, '
                                        f'caja {[r1(t) for t in bat_lat]} pt)')
            if ap.get('centro_mm'):
                ap['centro_mm'][2] = r1((z0 + z1) / 2)
        elif ap['apoyado_en'] in ('fondo', 'piso') and ap['vista'] == 'fondo' and ap['estacion'] == 'E8':
            ap['profundidad_mm'] = None
            ap['nota'] = '. '.join(t for t in (ap.get('nota', '').rstrip('. '),
                                               'La profundidad (z) no está en el plano: z = cara de la placa.') if t)

    # 5) salidas de la bandeja hacia LI/LD: ultimo punto de las rutas del instructivo que terminan en LI / LD
    def salidas_de(lineas, estacion):
        g = collections.OrderedDict()
        for l in lineas:
            if l.get('destino') not in ('LI', 'LD') or not l.get('ruta'):
                continue
            k = (l['destino'], round(l['ruta'][-1][0], 1), round(l['ruta'][-1][1], 1))
            g.setdefault(k, []).append(dict(num=l['num'], cable=l.get('cable'), color=l.get('color'),
                                            secc=l.get('secc'), origen=l.get('origen'), estacion=estacion))
        return g
    lineas = [l for p in ins['pasos'] for l in p['lineas']]
    g = salidas_de(lineas, 'E6')
    g2 = salidas_de(ins.get('otra_estacion', []), 'E8')
    destinos = {}
    try:   # el otro extremo real de cada linea -> LI (lo arma el relevamiento de cables de E8, si ya esta)
        ce8 = json.load(open(os.path.join(OUT, 'cables_e8.json'), encoding='utf-8'))
        for c in ce8.get('cables', []):
            if c.get('num') and c.get('hasta'):
                destinos.setdefault(c['num'], c['hasta'].get('texto'))
    except (OSError, ValueError):
        ce8 = None
    v = POR_ID['fondo']
    salidas = []
    for (dst, X, Y), cs in g.items():
        hc = [d for d in lay['ductos'] if d['h'] and d['b'][1] - 0.5 <= Y <= d['b'][3] + 0.5]
        vc = [d for d in lay['ductos'] if not d['h'] and abs(d['b'][0] - X) < 20]
        if destinos:
            for c in cs:
                c['hasta_e8'] = destinos.get(c['num'])
        salidas.append(dict(destino=dst, pt=[X, Y], mm=a_mm(v, X, Y),
                            mm_cable_en_canaleta=[*a_mm(v, X, Y)[:2], r1(Z_FONDO + PROF_CANALETA['fondo'] / 2)],
                            canaleta_horizontal_pt=hc[0]['b'] if hc else None,
                            canaleta_vertical_pt=vc[0]['b'] if vc else None,
                            n_lineas=len(cs), n_numeros=len({c['num'] for c in cs}), cables=cs))
    salidas.sort(key=lambda s: -s['pt'][1])
    filas = lay.get('filas') or []
    for i, s in enumerate(salidas):
        alto = 'arriba' if i == 0 else ('abajo' if i == len(salidas) - 1 else f'intermedia {i}')
        s['nombre'] = f"{s['destino']} {alto}"
        Y = s['pt'][1]
        entre = next((f'entre el riel {k + 1} y el riel {k + 2}' for k in range(len(filas) - 1)
                      if filas[k] > Y > filas[k + 1]), '')
        lado = 'izquierda' if s['destino'] == 'LI' else 'derecha'
        s['descripcion'] = (f'sale por el borde de la canaleta vertical de la {lado}, a la altura de la canaleta '
                            f'horizontal {entre}').strip()
        cols = collections.Counter(c['color'] or '(sin color)' for c in s['cables'])
        s['colores'] = dict(cols)
    otra = []
    for (dst, X, Y), cs in g2.items():
        otra.append(dict(destino=dst, pt=[X, Y], mm=a_mm(v, X, Y), cables=cs,
                         nota='rutas que el programa manda a la salida LI pero se cablean en E8 (otra estación). '
                              'Los de 35 mm² (1204, 1215) van en realidad a la zona hidráulica y a la batería, no al lateral.'))

    # 6) bisagras y cerraduras (hoja 04 / 03)
    vp = POR_ID['puerta']
    bis = []
    for l, o, q in st(5):
        b = bbox(q)
        if l == 'TABLERO' and b[0] > vp['region_pt'][2] - 8 and b[2] <= vp['vista_pt'][2] and 15 < b[3] - b[1] < 25 and b[2] - b[0] < 8:
            bis.append(dict(pt=[r1(t) for t in b], mm=caja_mm(vp, b)))
    bis.sort(key=lambda b: b['pt'][1])
    v4 = dict(escala=2.3739, origen_pt=[436.3, 143.9], origen_mm=[0, 0, 430], eje_X=[1, 0, 0], eje_Y=[0, 1, 0])
    cerr_pt = {'arriba al centro': (604.7, 500.0), 'derecha arriba (con llave)': (747.4, 460.5),
               'derecha abajo': (747.4, 207.9), 'abajo al centro': (604.7, 167.4),
               'sobrepuerta / visor (con llave)': (664.7, 384.2)}
    cerraduras = [dict(que=k, pagina=4, pt=[r1(x), r1(y)], mm=a_mm(v4, x, y)) for k, (x, y) in cerr_pt.items()]
    bisagras = dict(
        puerta=dict(lado='izquierdo (mirando el gabinete de frente)',
                    bisagras=bis, y_mm=[r1((b['mm']['min'][1] + b['mm']['max'][1]) / 2) for b in bis],
                    eje_mm=dict(x=5.0, z=430.0, direccion=[0, 1, 0]),
                    apertura='hacia afuera girando sobre el eje vertical izquierdo (rotación sobre +y de 0 a -130°: '
                             'el borde libre, x = 800, va hacia +z)',
                    angulo_max_grados=130,
                    fuente='hoja 04 (vista posterior de puerta): 2 bisagras en el borde DERECHO de la hoja, que mirando de '
                           'frente es el izquierdo; las cerraduras están del otro lado (hoja 03). Fotos E08 20 y 23: puerta '
                           'abierta hacia la izquierda y el mazo espiral cruza por ese lado. 130° es de las bisagras del '
                           'gabinete BATFER 66336 (supuesto)'),
        sobrepuerta=dict(lado='izquierdo (supuesto)', marco_mm=dict(x=[180.0, 580.0], y=[340.0, 800.0], z=430.0),
                         fuente='marco del visor 400 x 460 en la hoja 02 (como la "overdoor" del 66336); la cerradura con '
                                'llave está a la derecha del marco (hoja 03), así que las bisagras van a la izquierda'),
        cerraduras=cerraduras)

    # 7) objetos sin tag (para el 3D)
    objetos = [
        dict(que='bloque de válvulas (base de SP-1 / SP-2)', vista='fondo', apoyado_en='piso', pt=[703.2, 135.2, 859.2, 184.8],
             caja_mm=caja_mm(POR_ID['fondo'], [703.2, 135.2, 859.2, 184.8]), nota='recuadro tomado del dibujo; profundidad desconocida'),
        dict(que='fusibles de repuesto', vista='lateral_izquierda', pt=next((c['b'] for c in cl_li if abs(c['b'][0] - 265.0) < 2), None)),
        dict(que='protección 220 V (pieza U 76251-1) sobre 11MS1', vista='lateral_izquierda', pt=[208.2, 338.1, 314.7, 409.1]),
        dict(que='portadocumentos', vista='lateral_derecha',
             pt=next((c['b'] for c in cl_ld if (c['b'][2] - c['b'][0]) > 80), None)),
        dict(que='etiqueta de conexionado a campo', vista='puerta', pt=[449.7, 203.1, 556.1, 247.3]),
        dict(que='perfiles verticales soldados de la puerta', vista='puerta', pt=[404.7, 179.0, 439.6, 687.3]),
        dict(que='perfiles verticales soldados de la puerta', vista='puerta', pt=[803.4, 179.0, 838.3, 687.3]),
    ]
    for o in objetos:
        if o.get('pt') and 'caja_mm' not in o:
            o['pt'] = [r1(t) for t in o['pt']]
            o['caja_mm'] = caja_mm(POR_ID[o['vista']], o['pt'])
    prensa = dict(vista='piso', pagina=6, grupos=[
        dict(que='9 prensacables M16', zona='adelante a la derecha'),
        dict(que='4 prensacables grandes en placa (fila)', zona='centro, adelante'),
        dict(que='5 prensacables M16 + 1 M32', zona='centro, atrás'),
        dict(que='3 prensacables M25', zona='atrás a la izquierda')],
        nota='posiciones exactas con cotas en la vista inferior exterior (hoja 03, pág. 4); coinciden con los grupos de '
             'prensacables que asoman abajo en la vista lateral de la hoja 07 (adelante z 250-360 y atrás z 30-120)')

    # 8) verificaciones cruzadas
    def ap_de(tag):
        return next((a for a in aparatos if a['tag'] == tag), None)
    ms = ap_de('11MS1'); db = ap_de('46DB1'); sh = ap_de('13SH1')
    if ms and ms.get('centro_mm'):
        verif.append(dict(que='11MS1 (llave general) en el lateral izquierdo contra el agujero de su manija por fuera',
                          relevado_mm=dict(y=ms['centro_mm'][1], z=ms['centro_mm'][2]),
                          plano_mm=dict(y=345, z=320, fuente='hoja 03: 345 del piso y 80 del frente (320 desde el fondo)')))
    if db and db.get('centro_mm'):
        verif.append(dict(que='46DB1 (parada de emergencia) en la puerta contra su agujero Ø22 por fuera',
                          relevado_mm=dict(x=db['centro_mm'][0], y=db['centro_mm'][1]),
                          plano_mm=dict(x=485, y=231, fuente='hoja 03: cotas 290 + 110 + 85 = 485 desde la izquierda; altura medida')))
    if sh and sh.get('centro_mm'):
        verif.append(dict(que='13SH1 (selectora) en la puerta contra la perilla que asoma en el frente (hoja 02)',
                          relevado_mm=dict(x=sh['centro_mm'][0], y=sh['centro_mm'][1]),
                          plano_mm=dict(x=508, y=473, fuente='hoja 02: perilla al borde derecho del panel, bajo el cartel (1); '
                                                             'medida en el dibujo, ±10 mm')))
    verif.append(dict(que='bisagras de la puerta contra las cerraduras del lado opuesto',
                      relevado_mm=dict(bisagras_y=bisagras['puerta']['y_mm']),
                      plano_mm=dict(cerraduras_y=[c['mm'][1] for c in cerraduras if 'derecha' in c['que']])))
    verif.append(dict(que='lateral izquierdo de la hoja 07 contra el de la hoja 05 (misma pared, otra escala)',
                      relevado_mm=dict(rieles_y=[r1((595.9 - 134.9) * 1.4086), r1((376.2 - 134.9) * 1.4086)],
                                       placa_y=[r1((170.4 - 134.9) * 1.4086), r1((745.4 - 134.9) * 1.4086)]),
                      plano_mm=dict(rieles_y=[r1((409.4 - 146.4) * 2.4691), r1((284.0 - 146.4) * 2.4691)],
                                    placa_y=[r1((166.7 - 146.4) * 2.4691), r1((494.7 - 146.4) * 2.4691)])))
    verif.append(dict(que='fotos E08 del 75286-1 (disco G:)',
                      resultado='la puerta abre hacia la izquierda (fotos 0, 2, 20, 23); la pared con 12PS2, 12XPS, '
                                'repuesto de fusibles, 11MS1 y 11XP es la que está junto a la bisagra = lateral IZQUIERDO '
                                '(fotos 7, 12, 20, 34, 36, 38); 13SH1 a la izquierda de la placa vista desde adentro '
                                '(31-33); 46DB1 abajo junto a la etiqueta de conexionado a campo (35); válvulas SP-1/SP-2 '
                                'abajo en el piso (19, 21); motor de la bomba con el contactor (16)'))

    gab = dict(
        version=1,
        producto='Tablero 75286 (mSafe2AC) · funcional 75287 rev 6 · topográfico 75441 rev 6',
        generado='2026-10-02',
        fuente=dict(topografico='3 - Historial web/ac0f0949510a/topografico.pdf (se leyó una copia)',
                    layout='layout.json del mismo trabajo (bandeja en la página 8)',
                    instructivo='instructivo.json del mismo trabajo (rutas de E6; no se tocó)',
                    referencia_gabinete='1 - Planos/66336-1.pdf (gabinete BATFER 800x940x400: bisagras 130°, placas, chapa 1,5 mm)',
                    fotos='G:/.../Fotos soporte E08/75286-1 (31 fotos + carpeta "a")',
                    script='2 - Resultados/E8 75286/relevar_gabinete.py'),
        convenciones=dict(
            hoja_pt='coordenadas del PDF en pt: origen abajo a la izquierda de la hoja, X a la derecha, Y hacia ARRIBA '
                    '(igual que layout.json e instructivo.json). La página es la del PDF (1 a 9); "hoja" es el número del rótulo.',
            gabinete_mm='mm, ejes de mano derecha: x = ancho, de la cara exterior IZQUIERDA (mirando de frente) hacia la '
                        'derecha (0 a 800); y = alto, del piso exterior hacia arriba (0 a 940, incluye 40 de techo); z = '
                        'profundidad, de la cara exterior del FONDO hacia la puerta (0 a 400 el cuerpo; la puerta cerrada '
                        'va de 400 a 430). En three.js: Y arriba y la cámara de frente mira desde +z.',
            mapeo='punto (X, Y) de la hoja -> [x, y, z] = origen_mm + escala * ((X - origen_pt[0]) * eje_X + '
                  '(Y - origen_pt[1]) * eje_Y). Es lo mismo que [x, y, z] = matriz · [X, Y, 1]. eje_X / eje_Y dicen hacia '
                  'dónde va en el gabinete la derecha / el arriba de la hoja; normal es hacia dónde mira la cara donde se '
                  'montan los aparatos.',
            puerta='los mm de la vista "puerta" son con la puerta CERRADA; para abrirla se rota todo alrededor de '
                   'bisagras.puerta.eje_mm',
            zonas='"zona" usa el mismo vocabulario que cables_e8.json: bandeja, lateral izq, lateral der, puerta, otro '
                  '(subzona: batería, zona hidráulica)'),
        medidas=dict(
            exterior_mm=dict(ancho=800, alto=940, profundidad=400, profundidad_con_puerta=430,
                             profundidad_total_con_cerraduras=475,
                             fuente='cotas de la hoja 03 (pág. 4): 800, 940, 400 y 475; puerta de 30 mm en la vista lateral '
                                    'de la hoja 07'),
            cuerpo_mm=dict(alto_sin_techo=900, techo=40,
                           fuente='hoja 03: el frente es un recuadro de 800 x 900 y arriba va la franja del techo; el '
                                  'gabinete BATFER 66336 da 900 + 40'),
            interior_mm=dict(ancho=797, alto=897, profundidad=398.5, supuesto=True,
                             fuente='no está en el plano: exterior menos chapa de 1,5 mm (calibre 16 del 66336)'),
            placa_fondo_mm=dict(ancho=740, alto=820, espesor=1.5, x=[30.0, 770.0], y=[59.4, 879.5], z_cara=Z_FONDO,
                                fuente='cotas 740 x 820 (hoja 08); ubicación medida en la hoja 07 contra el contorno del '
                                       'gabinete (centrada); z supuesto'),
            placa_lateral_izquierda_mm=dict(ancho=310, alto=810, espesor=1.5, x_cara=X_LI, y=[50.0, 860.0], z=[89.7, 399.6],
                                            fuente='cotas 310 x 810 (hoja 08); ubicación medida en las hojas 07 y 05 '
                                                   '(arranca en el frente del cuerpo); x supuesto'),
            lateral_derecho='sin placa: el sensor 41DS va en el perfil soldado de arriba y el portadocumentos en la pared',
            puerta_mm=dict(ancho=794, alto=894, profundidad=30, x=[3.0, 797.0], y=[3.0, 897.0], z=[400.0, 430.0],
                           fuente='hoja 04 (recuadro de la puerta dentro del contorno de 800 x 940) y vista lateral de la hoja 07'),
            sobrepuerta_mm=dict(ancho=400, alto=460, x=[180.0, 580.0], y=[340.0, 800.0],
                                fuente='marco del visor en la hoja 02 (igual a la overdoor 400 x 460 del 66336)'),
            escalas_mm_por_pt={f'pagina {p}': e for p, e in sorted(ESCALA_PAG.items())}),
        vistas=[dict({k: v[k] for k in v if k not in ('otras',)}, matriz=matriz(v), otras_hojas=v.get('otras', []))
                for v in VISTAS],
        vistas_exteriores=[dict(v, matriz=matriz(v)) for v in VISTAS_EXT],
        aparatos=aparatos,
        canaletas=canaletas,
        rieles=rieles,
        salidas_bandeja=salidas,
        salidas_otra_estacion=otra,
        bisagras=bisagras,
        objetos=objetos,
        prensacables=prensa,
        techo=dict(aparatos=[], nota='el plano no tiene vista del techo ni aparatos ahí: es la franja de 40 mm de arriba '
                                     '(techo/visera, y = 900 a 940) con los cáncamos de izaje en las esquinas (hoja 02)'),
        verificaciones=verif,
        supuestos=[
            f'Placa de fondo: cara de montaje a z = {Z_FONDO} mm de la cara exterior del fondo. El plano no lo acota; es '
            'donde terminan los perfiles soldados de las paredes (hojas 05 y 07) y en el 66336 la placa va pegada al fondo.',
            f'Placa lateral izquierda: cara de montaje a x = {X_LI} mm (pared 1,5 + perfil soldado + placa 1,5). Sin cota.',
            f'Lateral derecho: aparatos a x = {X_LD} mm (sobre el perfil soldado). Sin cota.',
            f'Puerta: cara interior de la chapa a z = {Z_PUERTA} mm con la puerta cerrada (puerta de 30 mm de 400 a 430, '
            'medida en la vista lateral de la hoja 07; chapa de 1,5 mm supuesta).',
            'Interior del gabinete (797 x 897 x 398,5) = exterior menos chapa de 1,5 mm: no está en el plano.',
            'Ángulo máximo de la puerta 130°: es de las bisagras del gabinete BATFER 66336, el plano del 75441 no lo dice.',
            'Sobrepuerta (visor) con bisagras a la izquierda: se deduce de la cerradura con llave a la derecha del marco.',
            'Profundidad de las canaletas: 80 mm en la placa de fondo (rótulo CD 40x80), 40 en la puerta (CD 40x40) y 40 '
            'supuesto en el lateral izquierdo (sin rótulo).',
            'La profundidad (z) de los aparatos no está en el plano (salvo la batería, que se ve de costado): etiqueta_mm y '
            'centro_mm van en la cara de su placa.',
            'Batería 12PB1: x e y de la vista de frente; z de la vista lateral de la hoja 07 (85 a 352). La vista inferior '
            'de la hoja 05 la dibuja ~20 mm más adelante (101 a 371).',
            'Títulos de las vistas: en la hoja 05 "VISTA DERECHA" es la pared IZQUIERDA vista desde adentro y "VISTA '
            'IZQUIERDA" la DERECHA; en la hoja 02 las dos vistas exteriores dicen "VISTA IZQUIERDA". Se tomó la pared por '
            'la geometría (dónde está la puerta en cada vista, agujero de 11MS1 a 80 del frente) y por las fotos E08.',
            'Cotas 95, 50 y 250 del lateral derecho (hoja 05) no coinciden con la escala del dibujo (dan 60, 42 y 242): '
            'se usó la geometría. 41DS queda a 0-60 mm del frente del cuerpo (la cota diría 95).',
            '21PCB01 (placa de la puerta) no tiene etiqueta en el topográfico: se ubicó por el dibujo "PROTECTOR PLACA E2.5" '
            'y las fotos.',
            'Vistas exteriores (hoja 02): se incluyen solo para texturas o carteles; los aparatos se ubican con las '
            'vistas interiores.'],
        dudas=[
            'PT 001 (transmisor de presión, cables 3141/3142) y BH-01-ZV (contactor de la bomba, cables 1204 y 6202) no '
            'tienen etiqueta en el topográfico: por las fotos, BH-01-ZV va sobre el motor de BH-01-M; PT 001 no se ubicó.',
            'SP-1 y SP-2 están etiquetados en el topográfico (solenoides del bloque de válvulas, abajo en el piso) pero el '
            'lector del funcional no los tiene entre sus componentes (ver dudas de cables_e8.json).',
            '¿Las placas lateral y de fondo están a las profundidades supuestas (x = 25, z = 20)? Si en el taller se mide, '
            'se cambian las constantes del script y se regenera.'],
    )
    with open(os.path.join(OUT, 'gabinete.json'), 'w', encoding='utf-8') as f:
        json.dump(gab, f, ensure_ascii=False, indent=1)
    # (no se guarda el cache de OCR del programa: este script solo lee)
    imagen_control(gab, pdf, os.path.join(OUT, 'control_gabinete.png'))
    shutil.rmtree(tmp, ignore_errors=True)
    print('gabinete.json:', len(aparatos), 'aparatos,', len(canaletas), 'canaletas,', len(rieles), 'rieles,',
          len(salidas), 'salidas')


# -------------------------------------------------------------------------------------------------------------------
# Imagen de control
K = 0.85   # px por mm en las vistas


def fuente(n):
    for f in ('arial.ttf', 'C:/Windows/Fonts/arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            pass
    return ImageFont.load_default()


def render_vista(pdf, v):
    doc = pdfium.PdfDocument(pdf)
    pg = doc[v['pagina'] - 1]; W, H = pg.get_size()
    b = v['vista_pt']; s = K * v['escala']
    img = pg.render(scale=s, crop=(b[0], b[1], W - b[2], H - b[3])).to_pil().convert('RGB')
    doc.close()
    # aclarar el dibujo para que se lea lo de arriba
    img = Image.blend(img, Image.new('RGB', img.size, 'white'), 0.45)
    to_px = lambda X, Y: ((X - b[0]) * s, (b[3] - Y) * s)
    return img, to_px


def flecha(d, p0, p1, col, w=3):
    d.line([p0, p1], fill=col, width=w)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for da in (2.6, -2.6):
        d.line([p1, (p1[0] + 12 * math.cos(ang + da), p1[1] + 12 * math.sin(ang + da))], fill=col, width=w)


EJE_TXT = {(1, 0, 0): '+x', (-1, 0, 0): '-x', (0, 1, 0): '+y', (0, -1, 0): '-y', (0, 0, 1): '+z', (0, 0, -1): '-z'}


def panel_vista(gab, pdf, v, titulo):
    img, to_px = render_vista(pdf, v)
    pad_t, pad = 46, 30
    W, H = img.size
    can = Image.new('RGB', (W + 2 * pad, H + pad_t + pad + 26), 'white')
    can.paste(img, (pad, pad_t))
    d = ImageDraw.Draw(can)
    f, fs, fb = fuente(13), fuente(11), fuente(16)
    P = lambda X, Y: (to_px(X, Y)[0] + pad, to_px(X, Y)[1] + pad_t)
    d.text((pad, 6), titulo, fill='black', font=fb)
    d.text((pad, 26), f"pág. {v['pagina']} (hoja {v['hoja']}) · {v['escala']} mm/pt · {v['desde'][:95]}", fill=(60, 60, 60), font=fs)
    # region (placa)
    r = v.get('region_pt')
    if r and r != v['vista_pt']:
        d.rectangle([P(r[0], r[3]), P(r[2], r[1])], outline=(0, 140, 0), width=2)
    # escala de mm del gabinete sobre los bordes: cada 100 mm
    b = v['vista_pt']; e = v['escala']
    for i, eje in ((0, 'X'), (1, 'Y')):
        lo, hi = (b[0], b[2]) if i == 0 else (b[1], b[3])
        vec = v['eje_X'] if i == 0 else v['eje_Y']
        k = next(j for j in range(3) if vec[j])
        # valores del eje k del gabinete en cada punto de la hoja
        for t in range(0, 1001, 100):
            # X (o Y) de la hoja donde la coordenada k vale t
            O = v['origen_mm'][k]; X0 = v['origen_pt'][i]
            Xt = X0 + (t - O) / (e * vec[k])
            if lo - 0.5 <= Xt <= hi + 0.5:
                if i == 0:
                    p = P(Xt, b[1]); d.line([p, (p[0], p[1] + 7)], fill=(0, 0, 200), width=1)
                    d.text((p[0] - 9, p[1] + 8), str(t), fill=(0, 0, 200), font=fs)
                else:
                    p = P(b[0], Xt); d.line([p, (p[0] - 7, p[1])], fill=(0, 0, 200), width=1)
                    d.text((p[0] - 28, p[1] - 6), str(t), fill=(0, 0, 200), font=fs)
    # ejes: derecha / arriba de la hoja -> eje del gabinete
    o = (pad + 14, pad_t + H - 14)
    flecha(d, o, (o[0] + 60, o[1]), (0, 0, 200)); d.text((o[0] + 64, o[1] - 8), EJE_TXT[tuple(v['eje_X'])], fill=(0, 0, 200), font=fb)
    flecha(d, o, (o[0], o[1] - 60), (0, 0, 200)); d.text((o[0] + 4, o[1] - 80), EJE_TXT[tuple(v['eje_Y'])], fill=(0, 0, 200), font=fb)
    d.text((o[0] + 18, o[1] - 34), f"normal {EJE_TXT[tuple(v['normal'])]}", fill=(0, 0, 200), font=fs)
    # canaletas y rieles
    for c in gab['canaletas']:
        if c['vista'] == v['id']:
            q = c['pt']; col = (40, 70, 255) if c['intrinseca'] else (110, 110, 110)
            d.rectangle([P(q[0], q[3]), P(q[2], q[1])], outline=col, width=2)
    for rr in gab['rieles']:
        if rr['vista'] == v['id']:
            q = rr['pt']
            d.rectangle([P(q[0], q[3]), P(q[2], q[1])], outline=(200, 140, 0), width=1)
    for o_ in gab['objetos']:
        if o_['vista'] == v['id'] and o_.get('pt'):
            q = o_['pt']
            d.rectangle([P(q[0], q[3]), P(q[2], q[1])], outline=(150, 0, 150), width=1)
    # aparatos
    for a in gab['aparatos']:
        if a['vista'] != v['id']:
            continue
        col = (200, 0, 0) if a['estacion'] == 'E8' else (0, 120, 0)
        if a.get('caja_pt'):
            q = a['caja_pt']; d.rectangle([P(q[0], q[3]), P(q[2], q[1])], outline=col, width=2)
        if a.get('etiqueta_pt'):
            x, y = P(*a['etiqueta_pt']); d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=col)
            ref = a['centro_mm'] if a.get('centro_mm') else a['etiqueta_mm']
            if a['estacion'] == 'E8':
                d.text((x + 5, y - 15), a['tag'], fill=col, font=f)
                d.text((x + 5, y), f"{ref[0]:.0f},{ref[1]:.0f},{ref[2]:.0f}", fill=col, font=fs)
        elif a.get('caja_pt'):
            q = a['caja_pt']; x, y = P(q[0], q[3])
            d.text((x + 4, y + 4), a['tag'] + f"  {a['centro_mm'][0]:.0f},{a['centro_mm'][1]:.0f},{a['centro_mm'][2]:.0f}", fill=col, font=f)
    # salidas
    if v['id'] == 'fondo':
        for s in gab['salidas_bandeja']:
            x, y = P(*s['pt'])
            d.polygon([(x, y - 9), (x + 8, y + 6), (x - 8, y + 6)], fill=(230, 0, 160))
            d.text((x + 10, y - 30), f"{s['nombre']}: {s['n_lineas']} líneas", fill=(230, 0, 160), font=f)
            d.text((x + 10, y - 16), f"({s['mm'][0]:.0f}, {s['mm'][1]:.0f}, {s['mm'][2]:.0f}) mm", fill=(230, 0, 160), font=fs)
    # lo que esta apoyado en el piso, con profundidad conocida (bateria): x de la vista de frente y z de la lateral
    if v['id'] == 'piso':
        for a in gab['aparatos']:
            pz = a.get('profundidad_mm')
            if a.get('apoyado_en') == 'piso' and pz and a.get('caja_pt'):
                vf = next(w for w in gab['vistas'] if w['id'] == a['vista'])
                x0 = a_mm(vf, a['caja_pt'][0], 0)[0]; x1 = a_mm(vf, a['caja_pt'][2], 0)[0]
                inv = lambda x, z: (v['origen_pt'][0] + (x - v['origen_mm'][0]) / e, v['origen_pt'][1] + (z - v['origen_mm'][2]) / e)
                q0 = P(*inv(x0, pz['z_max'])); q1 = P(*inv(x1, pz['z_min']))
                d.rectangle([q0, q1], outline=(200, 0, 0), width=2)
                d.text((q0[0] + 4, q1[1] + 2), f"{a['tag']} (x de la vista de frente, z de la lateral)", fill=(200, 0, 0), font=f)
    # origen del mapeo
    x, y = P(*v['origen_pt'])
    d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(0, 0, 200), width=2)
    om = v['origen_mm']
    d.text((x + 6, y + 4), f"origen ({om[0]:.0f}, {om[1]:.0f}, {om[2]:.0f})", fill=(0, 0, 200), font=fs)
    return can


def panel_3d(gab, Wp=1300, Hp=900):
    img = Image.new('RGB', (Wp, Hp), 'white'); d = ImageDraw.Draw(img)
    f, fs, fb = fuente(13), fuente(11), fuente(16)
    C = (1500.0, 1500.0, 2900.0); T = (330.0, 430.0, 300.0)
    def sub(a, b): return [a[i] - b[i] for i in range(3)]
    def nor(a): n = math.sqrt(sum(t * t for t in a)); return [t / n for t in a]
    def cru(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    def dot(a, b): return sum(a[i] * b[i] for i in range(3))
    fw = nor(sub(T, C)); rt = nor(cru(fw, [0, 1, 0])); up = cru(rt, fw)
    hb = gab['bisagras']['puerta']['eje_mm']; th = math.radians(-105)
    def abrir(p):
        dx, dz = p[0] - hb['x'], p[2] - hb['z']
        return [hb['x'] + dx * math.cos(th) + dz * math.sin(th), p[1], hb['z'] - dx * math.sin(th) + dz * math.cos(th)]
    def proy(p):
        q = sub(p, C); return dot(q, rt) / dot(q, fw), dot(q, up) / dot(q, fw)
    # encuadre: el cuerpo y la puerta abierta entran en el panel
    caja = [[x, y, z] for x in (0, 800) for y in (0, 940) for z in (0, 430)]
    caja += [abrir([x, y, 430]) for x in (0, 800) for y in (0, 940)]
    pr = [proy(p) for p in caja]
    u0, u1 = min(a for a, b in pr), max(a for a, b in pr); v0, v1 = min(b for a, b in pr), max(b for a, b in pr)
    F = min((Wp - 80) / (u1 - u0), (Hp - 120) / (v1 - v0))
    def Pp(p):
        a, b = proy(p)
        return (40 + (a - u0) * F, 80 + (v1 - b) * F)
    def poly(pts, fill=None, outline=(0, 0, 0), w=1):
        d.polygon([Pp(p) for p in pts], fill=fill, outline=outline)
        if w > 1:
            q = [Pp(p) for p in pts] + [Pp(pts[0])]; d.line(q, fill=outline, width=w)
    def rect3(c, n, fill, outline):
        a, b = c['min'], c['max']
        # la cara de la caja que mira hacia la normal de su vista (la tapa de la canaleta)
        if n[2]:
            z = b[2] if n[2] > 0 else a[2]
            pts = [[a[0], a[1], z], [b[0], a[1], z], [b[0], b[1], z], [a[0], b[1], z]]
        elif n[0]:
            x = b[0] if n[0] > 0 else a[0]
            pts = [[x, a[1], a[2]], [x, a[1], b[2]], [x, b[1], b[2]], [x, b[1], a[2]]]
        else:
            y = b[1] if n[1] > 0 else a[1]
            pts = [[a[0], y, a[2]], [b[0], y, a[2]], [b[0], y, b[2]], [a[0], y, b[2]]]
        poly(pts, fill, outline)
    NV = {v['id']: v['normal'] for v in gab['vistas']}
    # cuerpo
    X, Y, Z = 800, 940, 400
    poly([[0, 0, 0], [X, 0, 0], [X, 0, Z], [0, 0, Z]], (235, 235, 235))                 # piso
    poly([[0, 0, 0], [X, 0, 0], [X, Y, 0], [0, Y, 0]], (225, 225, 225))                 # fondo
    poly([[0, 0, 0], [0, 0, Z], [0, Y, Z], [0, Y, 0]], (215, 215, 215))                 # lateral izq
    poly([[X, 0, 0], [X, 0, Z], [X, Y, Z], [X, Y, 0]], (240, 240, 240))                 # lateral der
    pf = gab['medidas']['placa_fondo_mm']
    poly([[pf['x'][0], pf['y'][0], Z_FONDO], [pf['x'][1], pf['y'][0], Z_FONDO], [pf['x'][1], pf['y'][1], Z_FONDO],
          [pf['x'][0], pf['y'][1], Z_FONDO]], (250, 250, 235), (0, 140, 0), 2)
    pl = gab['medidas']['placa_lateral_izquierda_mm']
    poly([[X_LI, pl['y'][0], pl['z'][0]], [X_LI, pl['y'][0], pl['z'][1]], [X_LI, pl['y'][1], pl['z'][1]],
          [X_LI, pl['y'][1], pl['z'][0]]], (250, 250, 235), (0, 140, 0), 2)
    for c in gab['canaletas']:
        cm = c['caja_mm']
        if c['vista'] == 'puerta':
            cm = dict(min=abrir(cm['min']), max=abrir(cm['max']))
            continue
        rect3(cm, NV[c['vista']], (120, 140, 255) if c['intrinseca'] else (170, 170, 170), (90, 90, 90))
    for r in gab['rieles']:
        if 'perfil' in r['tipo']:
            rect3(r['caja_mm'], NV[r['vista']], (205, 205, 205), (120, 120, 120))
    # puerta abierta
    pu = gab['medidas']['puerta_mm']
    door = [[pu['x'][0], pu['y'][0], 430], [pu['x'][1], pu['y'][0], 430], [pu['x'][1], pu['y'][1], 430], [pu['x'][0], pu['y'][1], 430]]
    poly([abrir(p) for p in door], (245, 240, 225), (0, 0, 0), 2)
    poly([[0, 0, Z], [X, 0, Z], [X, Y, Z], [0, Y, Z]], None, (150, 150, 150))        # boca del cuerpo
    d.line([Pp([hb['x'], 0, hb['z']]), Pp([hb['x'], 940, hb['z']])], fill=(0, 0, 200), width=3)
    d.text(Pp([hb['x'], 945, hb['z']]), 'eje de bisagras', fill=(0, 0, 200), font=f)
    # aparatos
    for a in gab['aparatos']:
        p = a.get('centro_mm') or a.get('etiqueta_mm')
        if not p:
            continue
        if a['vista'] == 'puerta':
            p = abrir(p)
        col = (200, 0, 0) if a['estacion'] == 'E8' else (0, 120, 0)
        x, y = Pp(p); rr = 5 if a['estacion'] == 'E8' else 3
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)
        if a['estacion'] == 'E8':
            d.text((x + 6, y - 7), a['tag'], fill=col, font=f)
    for s in gab['salidas_bandeja']:
        x, y = Pp(s['mm_cable_en_canaleta'])
        d.polygon([(x, y - 9), (x + 8, y + 6), (x - 8, y + 6)], fill=(230, 0, 160))
        d.text((x + 9, y - 6), s['nombre'], fill=(230, 0, 160), font=f)
    # ejes
    o = [0, 0, 430]
    for v_, t in (([150, 0, 0], '+x'), ([0, 150, 0], '+y'), ([0, 0, 150], '+z')):
        p1 = Pp([o[i] + v_[i] for i in range(3)]); flecha(d, Pp(o), p1, (0, 0, 200)); d.text((p1[0] + 4, p1[1] - 6), t, fill=(0, 0, 200), font=fb)
    d.text((14, 10), '3D de control: gabinete 800 x 940 x 400, puerta abierta 105° sobre la bisagra izquierda', fill='black', font=fb)
    d.text((14, 32), 'verde = placas (fondo y lateral izq.) · gris/azul = canaletas · rojo = aparatos de E8 · verde chico = '
                     'aparatos de la bandeja (E6) · magenta = salidas LI de la bandeja', fill=(60, 60, 60), font=fs)
    return img


def imagen_control(gab, pdf, salida):
    V = {v['id']: v for v in gab['vistas']}
    pan = [panel_vista(gab, pdf, V['fondo'], 'FONDO (bandeja E6) · pág. 8'),
           panel_vista(gab, pdf, V['lateral_izquierda'], 'LATERAL IZQUIERDO (LI) · pág. 8'),
           panel_vista(gab, pdf, V['lateral_derecha'], 'LATERAL DERECHO (LD) · pág. 6'),
           panel_vista(gab, pdf, V['puerta'], 'PUERTA por dentro · pág. 5')]
    piso = panel_vista(gab, pdf, V['piso'], 'PISO (vista inferior) · pág. 6')
    p3 = panel_3d(gab)
    W1 = sum(p.size[0] for p in pan) + 10 * (len(pan) - 1)
    H1 = max(p.size[1] for p in pan)
    W2 = piso.size[0] + 10 + p3.size[0]
    H2 = max(piso.size[1], p3.size[1])
    can = Image.new('RGB', (max(W1, W2) + 20, H1 + H2 + 70), 'white')
    d = ImageDraw.Draw(can)
    d.text((10, 8), 'Control del relevamiento del gabinete 75286 (topográfico 75441 rev 6) para E8 · '
                    'azul: ejes y escala en mm del gabinete (x ancho, y alto, z profundidad desde el fondo)',
           fill='black', font=fuente(18))
    x = 10
    for p in pan:
        can.paste(p, (x, 40)); x += p.size[0] + 10
    can.paste(piso, (10, 50 + H1))
    can.paste(p3, (20 + piso.size[0], 50 + H1))
    can.save(salida)


if __name__ == '__main__':
    main()
