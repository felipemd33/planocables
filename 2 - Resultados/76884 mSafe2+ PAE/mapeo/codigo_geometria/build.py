# -*- coding: utf-8 -*-
"""Geometria de las bandejas del 76884 (pagina PDF 8) -> bandejas.json + control_bandejas.png
Medidas sacadas de los vectores de la copia de proceso (pypdf/pdfvec) y del texto de pdfium.
Ver analisis en geo/*.py (objs.py: proyeccion de objetos por riel; cc.py: componentes conexas)."""
import sys, json, math, re, os
sys.path.insert(0, os.path.dirname(__file__))
import pypdfium2 as pdfium, pypdfium2.raw as raw
from objs import SEGS

PROC = r'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad/p76884/76884_proc.pdf'
OUT = r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo'
PI = 7
MM = 25.4 / 72 * 4          # 1:4 -> 1.41111 mm por pt
R2 = lambda v: round(v, 2)
mm = lambda pt: round(pt * MM, 1)

# ---------------------------------------------------------------- texto
doc = pdfium.PdfDocument(PROC)
page = doc[PI]
W, H = page.get_size()
tp = page.get_textpage()
chars = []
for k in range(tp.count_chars()):
    t = tp.get_text_range(k, 1)
    l, b, r, tt = tp.get_charbox(k)
    chars.append(dict(t=t, l=l, b=b, r=r, tp=tt, ang=raw.FPDFText_GetCharAngle(tp.raw, k),
                      fs=raw.FPDFText_GetFontSize(tp.raw, k)))
toks, cur = [], []
for c in chars + [dict(t=' ')]:
    if c['t'].strip() == '':
        if cur: toks.append(cur)
        cur = []
    else:
        if cur:
            p = cur[-1]
            # salto de posicion sin espacio (texto de otro objeto pegado): cortar
            if abs(c['b'] - p['b']) > 3 and abs(c['l'] - p['l']) > 3 or abs(c['ang'] - p['ang']) > 0.1 \
               or (abs(c['ang']) < 0.1 and c['l'] - p['r'] > 3):
                toks.append(cur); cur = []
        cur.append(c)

def mk(cs):
    return dict(t=''.join(c['t'] for c in cs), l=min(c['l'] for c in cs), b=min(c['b'] for c in cs),
                r=max(c['r'] for c in cs), tp=max(c['tp'] for c in cs),
                vert=abs(cs[0]['ang'] - 3 * math.pi / 2) < 0.1, fs=cs[0]['fs'], cs=cs)

words = []
for cs in toks:
    s = ''.join(c['t'] for c in cs)
    # 'F13' de 42XC = 'F1' (fusible) + '3' (otro texto con otra linea base)
    m = re.match(r'^(F\d)(\d+)$', s)
    if m and abs(cs[2]['b'] - cs[1]['b']) > 0.15:
        words.append(mk(cs[:2])); words.append(mk(cs[2:]))
    else:
        words.append(mk(cs))
# '-' suelto debajo de 'PT001' (texto vertical partido)
for w in list(words):
    if w['t'] == '-':
        for v in words:
            if v is not w and v['vert'] and abs((v['l'] + v['r']) / 2 - (w['l'] + w['r']) / 2) < 3 and 0 <= v['b'] - w['tp'] < 2:
                v.update(mk(w['cs'] + v['cs'])); v['t'] = '-' + v['t'].lstrip('-'); words.remove(w); break

PRINC = [573.42, 129.29, 1094.28, 745.83]
LAT = [192.61, 150.02, 468.99, 725.10]
inside = lambda x, y, b, e=2: b[0] - e <= x <= b[2] + e and b[1] - e <= y <= b[3] + e

def label_dict(region):
    out = {}
    for w in words:
        if w['t'].startswith('-') and len(w['t']) > 1 and inside(w['l'], w['b'], region):
            out[w['t'][1:]] = w
    return out

def numbers(region):
    return [w for w in words if re.match(r'^F?\d+$', w['t']) and inside((w['l'] + w['r']) / 2, (w['b'] + w['tp']) / 2, region, 0)]

# ---------------------------------------------------------------- geometria medida
# rieles: y0/y1 = bordes del perfil (8 lineas: 0, 2.12, 3.19, 3.90, 20.90, 21.61, 22.68, 24.80 pt)
RIELES_P = [
    dict(id='U10', numero=1, tramo='unico', x0=615.94, x1=913.57, y0=644.85, y1=669.65, largo_lista_m=0.42),
    dict(id='U11', numero=2, tramo='izquierdo', x0=615.94, x1=786.01, y0=503.08, y1=527.89, largo_lista_m=0.24),
    dict(id='U12', numero=2, tramo='derecho', x0=814.36, x1=913.57, y0=503.11, y1=527.92, largo_lista_m=0.14),
    dict(id='U13', numero=3, tramo='izquierdo', x0=615.94, x1=786.01, y0=372.13, y1=396.93, largo_lista_m=0.24),
    dict(id='U14', numero=3, tramo='derecho', x0=814.36, x1=913.57, y0=372.01, y1=396.81, largo_lista_m=0.14),
]
RIELES_L = [
    dict(id='U19', numero=1, tramo='unico', x0=192.61, x1=426.47, y0=520.30, y1=545.10, largo_lista_m=0.33),
    dict(id='U18', numero=2, tramo='izquierdo', x0=192.61, x1=288.28, y0=371.48, y1=396.28, largo_lista_m=0.135,
         nota='x1 = x0 + 135 mm (el extremo derecho queda tapado por el tope 281.34-288.07)'),
    dict(id='U21', numero=2, tramo='derecho', x0=344.97, x1=398.12, y0=371.48, y1=396.28, largo_lista_m=0.075,
         nota='x0 = x1 - 75 mm (el tope 344.62-351.35 sobresale 0.35 pt)'),
]
TOPES = {   # E/NS 35 N (6.73 pt = 9.5 mm), x0-x1 por riel
    'U10': [(615.94, 622.67), (734.64, 741.37), (821.98, 828.71), (844.73, 851.46), (855.78, 862.48), (879.79, 886.47), (891.45, 898.18)],
    'U11': [(615.94, 622.67), (641.55, 648.29), (661.40, 668.13), (694.35, 701.08), (725.74, 732.48), (745.59, 752.32), (768.48, 775.21)],
    'U12': [(814.36, 821.09), (860.28, 866.98)],
    'U13': [(681.27, 688.01), (697.43, 704.16), (716.96, 723.69), (742.50, 749.24)],
    'U14': [(814.36, 821.09), (834.17, 840.90), (863.37, 870.10)],
    'U19': [(220.95, 227.69), (304.33, 311.06)],
    'U18': [(192.34, 199.07), (281.34, 288.07)],
    'U21': [(344.62, 351.35), (369.67, 376.40), (389.51, 396.24)],
}
TOPES_NOTA = {'U12': 'el tope izquierdo (814.36-821.09) se ve solo en parte (su contorno queda bajo la canaleta U6)',
              'U14': 'el tope izquierdo (814.36-821.09) se ve solo en parte (su contorno queda bajo la canaleta U6)'}

CANAL_P = [
    dict(id='U2', b=[587.59, 717.48, 913.57, 745.83], horizontal=True, tipo='comun', articulo='CD 40X80 (PXC.3240198)', lista='0,46 m TAPA / 0,42 m BASE',
         nota='tapa de 460 mm desde x=587.59 (cubre la union con U3); base de 420 mm desde x=615.94'),
    dict(id='U3', b=[587.59, 334.81, 615.94, 717.48], horizontal=False, tipo='comun', articulo='CD 40X80 (PXC.3240198)', lista='0,54 m'),
    dict(id='U4', b=[615.94, 568.66, 913.57, 597.01], horizontal=True, tipo='comun', articulo='CD 40X80 (PXC.3240198)', lista='0,42 m'),
    dict(id='U5', b=[615.94, 434.02, 786.01, 462.37], horizontal=True, tipo='comun', articulo='CD 40X80 (PXC.3240198)', lista='0,24 m'),
    dict(id='U6', b=[786.01, 334.81, 814.36, 568.66], horizontal=False, tipo='intrinseca (azul)', articulo='CD 40X80 BU (PXC.3240198 BU)', lista='0,33 m'),
    dict(id='U7', b=[814.36, 434.02, 913.57, 462.37], horizontal=True, tipo='intrinseca (azul)', articulo='CD 40X80 BU (PXC.3240198 BU)', lista='0,14 m'),
    dict(id='U8', b=[587.59, 292.29, 786.01, 334.81], horizontal=True, tipo='comun', articulo='CD 60X80 (PXC.3240199)', lista='0,28 m'),
    dict(id='U9', b=[786.01, 292.29, 913.57, 334.81], horizontal=True, tipo='intrinseca (azul)', articulo='CD 60X80 BU (PXC.3240199 BU)', lista='0,18 m'),
]
CANAL_L = [
    dict(id='U15', b=[192.61, 440.57, 426.47, 468.92], horizontal=True, tipo='comun', articulo='CD 40X40 (PXC.3240189)', lista='0,33 m'),
    dict(id='U16', b=[398.12, 327.19, 426.47, 440.57], horizontal=False, tipo='comun', articulo='CD 40X40 (PXC.3240189)', lista='0,16 m'),
    dict(id='U17', b=[192.61, 298.84, 426.47, 327.19], horizontal=True, tipo='comun', articulo='CD 40X40 (PXC.3240189)', lista='0,33 m'),
]

def P(x0, x1, tipo, **k):
    d = dict(x0=x0, x1=x1, tipo=tipo); d.update(k); return d
def split(x0, x1, n, tipo):
    w = (x1 - x0) / n
    return [P(R2(x0 + i * w), R2(x0 + (i + 1) * w), tipo) for i in range(n)]

T6Q, T6, PTT, PTTBU, PE, DIO, HESI = 'PT 6-QUATTRO', 'PT 6', 'PTT 2,5-2MT', 'PTT 2,5-2MT BU', 'PT 2,5-QUATTRO-PE (verde)', 'PT 2,5-DIO/L-R', 'PTTB 4-HESI (5X20) portafusible'
TAPA6Q, TAPA6, TAPAPE, TAPAPTT, TAPADIO = 'tapa D-PT 6-QUATTRO', 'tapa D-PT 6', 'tapa D-ST 2,5-QUATTRO GN', 'tapa D-PTT 2,5-2MT-0,8', 'tapa D-ST 2,5'

# aparatos: caja = cuerpo dibujado (x0, y0, x1, y1); piezas solo en borneras
AP_P = {
    '11PS1': dict(riel='U10', caja=[622.67, 611.64, 667.31, 702.85], modelo='MEAN WELL NDR-240-24 (fuente 24 VDC)'),
    '11PS2': dict(riel='U10', caja=[667.31, 611.64, 711.96, 702.85], modelo='MEAN WELL NDR-240-24 (fuente 24 VDC)'),
    '13PS1': dict(riel='U10', caja=[711.96, 612.88, 734.64, 701.61], modelo='MEAN WELL DDR-120A-24 (elevador 12/24 VDC)'),
    '11F1': dict(riel='U10', caja=[741.37, 625.94, 753.77, 688.55], modelo='Schneider DF101 + DF2CN10 (10x38 gG 10 A)'),
    '11F2': dict(riel='U10', caja=[753.77, 625.94, 766.17, 688.55], modelo='Schneider DF101 + DF2CN10 (10x38 gG 10 A)'),
    '12F3': dict(riel='U10', caja=[766.17, 617.63, 784.95, 696.86], modelo='Schneider DF141 + DF2EA32 (14x51 aM 32 A)'),
    '13F4': dict(riel='U10', caja=[784.95, 625.94, 797.18, 688.55], modelo='Schneider DF101 + DF2CN10 (10x38 gG 10 A)'),
    '13F5': dict(riel='U10', caja=[797.18, 625.94, 809.58, 688.55], modelo='Schneider DF101 + DF2CN10 (10x38 gG 10 A)'),
    '13F6': dict(riel='U10', caja=[809.58, 625.94, 821.98, 688.55], modelo='Schneider DF101 + DF2CN06 (10x38 gG 6 A)'),
    '42KS1': dict(riel='U10', caja=[828.71, 622.33, 844.73, 692.49], modelo='Phoenix PSR-SCP-24UC/ESA2/4X1/1X2/B (rele de seguridad)'),
    '42KR': dict(riel='U10', caja=[851.46, 624.75, 855.78, 689.74], modelo='grupo de reles Phoenix RIF-0 (etiqueta sobre el tope)',
                 modulos=[dict(tag='42KR1', x0=851.46, x1=855.78, modelo='RIF-0-RPT-24DC/21 (PXC.2903370)')]),
    '61KR': dict(riel='U10', caja=[862.48, 624.75, 879.79, 689.75], modelo='grupo de reles Phoenix RIF-0 (etiqueta sobre el tope)',
                 modulos=[dict(tag='61KR%d' % (i + 1), x0=R2(862.48 + i * 4.3275), x1=R2(862.48 + (i + 1) * 4.3275),
                               modelo='RIF-0-RPT-12DC/21 (PXC.2903371)') for i in range(4)],
                 nota_modulos='orden 61KR1..61KR4 de izquierda a derecha SUPUESTO: la hoja 8 no rotula cada modulo'),
    '32XAI': dict(riel='U10', caja=[886.47, 624.19, 891.39, 697.12], modelo='bornera Phoenix Contact (ver piezas)',
                  piezas=[P(886.47, 890.83, HESI), P(890.83, 891.39, TAPAPTT)]),
    'XPE': dict(riel='U10', caja=[898.18, 631.88, 910.69, 683.04], modelo='bornera de tierra Phoenix Contact (ver piezas)',
                piezas=split(898.18, 909.13, 3, PE) + [P(909.13, 910.69, TAPAPE)],
                nota='no hay tope a la derecha: despues de la tapa sigue el riel hasta 913.57'),
    '12XP': dict(riel='U11', caja=[622.67, 482.80, 641.55, 546.95], modelo='bornera Phoenix Contact (ver piezas)',
                 piezas=split(622.67, 640.00, 3, T6Q) + [P(640.00, 641.55, TAPA6Q)], puentes='FBS 3-8 BU'),
    '13X12V': dict(riel='U11', caja=[648.29, 482.80, 661.40, 546.95], modelo='bornera Phoenix Contact (ver piezas)',
                   piezas=split(648.29, 659.84, 2, T6Q) + [P(659.84, 661.40, TAPA6Q)]),
    '13X24V': dict(riel='U11', caja=[668.13, 482.80, 694.35, 546.95], modelo='bornera Phoenix Contact (ver piezas)',
                   piezas=split(668.13, 692.79, 4, T6Q) + [P(692.79, 694.35, TAPA6Q)], puentes='FBS 2-8 (1-2) y FBS 2-8 BU (3-4)'),
    '61XDO': dict(riel='U11', caja=[701.08, 482.80, 725.74, 546.95], modelo='bornera Phoenix Contact (ver piezas)',
                  piezas=split(701.08, 724.18, 4, T6Q) + [P(724.18, 725.74, TAPA6Q)]),
    '61X0V': dict(riel='U11', caja=[732.48, 482.80, 745.59, 546.95], modelo='bornera Phoenix Contact (ver piezas)',
                  piezas=split(732.48, 744.03, 2, T6Q) + [P(744.03, 745.59, TAPA6Q)], puentes='FBS 2-8 BU'),
    '61XDIO': dict(riel='U11', caja=[752.32, 498.48, 768.48, 532.92], modelo='bornera Phoenix Contact (ver piezas)',
                   piezas=split(752.32, 766.92, 4, DIO) + [P(766.92, 768.48, TAPADIO)], puentes='FBS 4-5 BU'),
    '15AIB1': dict(riel='U12', caja=[821.13, 476.01, 833.60, 555.02], modelo='CHENZHU GS8536-EX (barrera intrinseca, 2 AI)'),
    '15DIB1': dict(riel='U12', caja=[833.60, 476.01, 842.46, 555.02], modelo='CHENZHU GS8512-EX.22 (barrera intrinseca, 2 DI)'),
    '15DIB2': dict(riel='U12', caja=[842.46, 476.01, 851.32, 555.02], modelo='CHENZHU GS8512-EX.22 (barrera intrinseca, 2 DI)'),
    '15DIB3': dict(riel='U12', caja=[851.32, 476.01, 860.25, 555.02], modelo='CHENZHU GS8512-EX.22 (barrera intrinseca, 2 DI)'),
    '15XR': dict(riel='U13', caja=[688.01, 351.79, 697.43, 417.27], modelo='bornera Phoenix Contact (ver piezas)',
                 piezas=[P(688.01, 691.66, PTT), P(691.66, 692.22, TAPAPTT), P(692.22, 695.87, PE), P(695.87, 697.43, TAPAPE)]),
    '42XC': dict(riel='U13', caja=[704.16, 351.47, 716.96, 424.40], modelo='bornera Phoenix Contact (ver piezas)',
                 piezas=[P(704.16, 708.52, HESI), P(708.52, 709.09, TAPAPTT)] + split(709.09, 716.39, 2, PTT) + [P(716.39, 716.96, TAPAPTT)]),
    '81XCM': dict(riel='U13', caja=[723.69, 351.79, 742.50, 417.27], modelo='bornera Phoenix Contact (ver piezas)',
                  piezas=split(723.69, 741.93, 5, PTT) + [P(741.93, 742.50, TAPAPTT)]),
    '32XEX': dict(riel='U14', caja=[821.09, 351.67, 834.17, 417.15], modelo='bornera Phoenix Contact (ver piezas)',
                  piezas=split(821.09, 828.39, 2, PTTBU) + [P(828.39, 828.96, TAPAPTT), P(828.96, 832.61, PE), P(832.61, 834.17, TAPAPE)]),
    '41XEX': dict(riel='U14', caja=[840.90, 351.67, 863.37, 417.15], modelo='bornera Phoenix Contact (ver piezas)',
                  piezas=split(840.90, 862.80, 6, PTTBU) + [P(862.80, 863.37, TAPAPTT)]),
    # zona hidraulica (a la derecha de x=913.57, sin riel)
    '12F2': dict(riel=None, montaje='atornillado a la placa, zona hidraulica arriba', caja=[955.03, 693.39, 1048.22, 724.57],
                 modelo='Littelfuse MEGA fuse holder + fusible MEGA 150 A',
                 nota='dos espárragos visibles (contornos): izq. [978.36, 703.66, 988.76, 714.30], der. [1014.50, 703.66, 1025.29, 714.30] (sin verificar como puntos de conexion)'),
    'BH': dict(riel=None, montaje='unidad hidraulica atornillada a la placa con soporte (x 922.43-1092.51, y 473.0-593.5)',
               caja=[922.43, 277.40, 1093.56, 680.99], modelo='DIGITO UNIDAD HIDRAULICA R2 / Vibo (motor -M1 = -BH-01-M)',
               nota='caja = contorno de todo el conjunto (acumulador, motor, bloque con manometro, tanque [962.83, 277.40, 1088.97, 504.04]); dentro estan BH_01_ZV, PT001 y LS001A'),
    'BH_01_ZV': dict(riel=None, montaje='sobre la unidad hidraulica (lado derecho)', caja=[1047.24, 574.33, 1095.61, 633.65],
                     modelo='Trombetta 684-1261-212-17 (contactor de bomba 12 VDC)', nota='la etiqueta se sale de la placa (termina en x=1113.5); el cuerpo pasa 1.3 pt el borde derecho de la placa'),
    'PT001': dict(riel=None, montaje='en el bloque de la unidad hidraulica', caja=[1055.31, 526.25, 1069.67, 540.14],
                  modelo='ifm PT-250-SEG14-A-ZVG/VE (transmisor de presion, conector DIN)',
                  nota='caja = racor/cuerpo que asoma a la derecha del bloque, debajo de la etiqueta; identificacion por cercania (baja confianza)'),
    'LS001A': dict(riel=None, montaje='en el tanque de la unidad hidraulica (abajo)', caja=[1019.16, 289.45, 1036.88, 321.34],
                   modelo='XKC-Y28-NO (sensor de nivel capacitivo)'),
}
AP_L = {
    '12PS1': dict(riel=None, montaje='atornillado a la placa, arriba del riel 1 (U19)', caja=[210.32, 578.41, 317.33, 687.54],
                  modelo='EPEVER TRACER7810BP (regulador de carga MPPT)'),
    '12XPS': dict(riel='U19', caja=[227.69, 511.63, 304.33, 552.54], modelo='bornera Phoenix Contact (ver piezas)',
                  piezas=split(227.69, 302.77, 13, T6) + [P(302.77, 304.33, TAPA6)], puentes='FBS 2-8 (piezas 7-8)'),
    '11SK1': dict(riel='U18', caja=[199.07, 357.13, 230.89, 410.29], modelo='Phoenix EO-I/UT (tomacorriente para riel)'),
    '11Q1': dict(riel='U18', caja=[230.89, 349.82, 256.26, 417.37], modelo='Schneider Acti9 iID 2P 25 A 30 mA (EZ9F36225) diferencial'),
    '11Q2': dict(riel='U18', caja=[256.26, 350.17, 281.34, 416.66], modelo='Schneider EZ9F34210 termomagnetica 2x10 A'),
    '11XPVAC': dict(riel='U21', caja=[351.35, 358.51, 369.67, 409.68], modelo='bornera Phoenix Contact (ver piezas)',
                    piezas=split(351.35, 362.90, 2, T6) + [P(362.90, 364.46, TAPA6), P(364.46, 368.11, PE), P(368.11, 369.67, TAPAPE)]),
    '11X220V': dict(riel='U21', caja=[376.40, 351.19, 389.51, 415.34], modelo='bornera Phoenix Contact (ver piezas)',
                    piezas=split(376.40, 387.95, 2, T6Q) + [P(387.95, 389.51, TAPA6Q)]),
}
OTROS_L = [
    dict(que='hueco/abertura sin etiqueta (rectangulo de esquinas redondeadas, blanco en las vistas 2D/3D)', b=[289.34, 335.69, 343.20, 434.90],
         nota='entre los rieles U18 y U21; no tiene bornes. Probable paso del cuerpo de -11MS1 (selector montado en la pared lateral exterior, se ve del lado de afuera en las hojas 6/26/28)'),
    dict(que='4 separadores de la tapa transparente de la zona baja (simbolos hexagonales)', puntos=[[198.3, 338.3], [198.3, 431.0], [391.7, 338.3], [391.7, 431.0]]),
    dict(que='linea doble horizontal (y 390.9-391.0) que sale de U16 hasta x=454.8 y linea doble vertical x=454.74-454.88 de y 419.3 a 719.3', b=[426.47, 390.90, 454.88, 719.32],
         nota='no es canaleta ni riel (no figura en la hoja 31); probable borde/pliegue o marco de la tapa. Sin aparatos'),
]

def rail_of(rid, rails):
    for r in rails:
        if r['id'] == rid: return r

def build(region, rails, canal, aps, otros=None, nombre=''):
    labs = label_dict(region)
    nums = numbers(region)
    used = set()
    out_aps = {}
    for tag, a in aps.items():
        w = labs.get(tag)
        if w is None:
            raise SystemExit('sin etiqueta: ' + tag)
        cx, cy = (w['l'] + w['r']) / 2, (w['b'] + w['tp']) / 2
        d = dict(x=R2(cx), y=R2(cy), etiqueta_bbox=[R2(w['l']), R2(w['b']), R2(w['r']), R2(w['tp'])],
                 orientacion='vertical (girada 90 grados, se lee de abajo hacia arriba)' if w['vert'] else 'horizontal')
        r = rail_of(a['riel'], rails) if a['riel'] else None
        d['riel'] = r['numero'] if r else None
        d['riel_id'] = a['riel']
        if r: d['riel_tramo'] = r['tramo']
        for k in ('montaje',):
            if k in a: d[k] = a[k]
        c = a['caja']; d['caja'] = [R2(v) for v in c]
        d['caja_mm'] = [mm(c[2] - c[0]), mm(c[3] - c[1])]
        d['modelo'] = a['modelo']
        # donde cae la etiqueta respecto del cuerpo
        topes = TOPES.get(a['riel'], []) if a['riel'] else []
        if not a['riel']:
            d['etiqueta_sobre'] = 'junto al cuerpo (aparato sin riel)'
        elif c[0] - 0.3 <= cx <= c[2] + 0.3:
            d['etiqueta_sobre'] = 'el cuerpo (centrada en x)'
        else:
            t = [tt for tt in topes if tt[0] - 0.3 <= cx <= tt[1] + 0.3]
            if t:
                d['etiqueta_sobre'] = 'el tope de la izquierda [%.2f-%.2f] (nombra las piezas a su derecha)' % t[0]
            else:
                d['etiqueta_sobre'] = 'afuera del cuerpo'
        if 'piezas' in a:
            pz = []; n = 0
            for i, p in enumerate(a['piezas']):
                q = dict(x0=R2(p['x0']), x1=R2(p['x1']), xc=R2((p['x0'] + p['x1']) / 2), ancho_mm=mm(p['x1'] - p['x0']), tipo=p['tipo'])
                if not p['tipo'].startswith('tapa'):
                    n += 1; q = dict(n=n, **q)
                pz.append(q)
            d['piezas'] = pz
        for k in ('modulos', 'nota_modulos', 'puentes', 'nota'):
            if k in a: d[k] = a[k]
        # numeros dibujados: debajo de la caja (hasta 14 pt) y dentro de su ancho
        nd = []
        for n in nums:
            nx, ny = (n['l'] + n['r']) / 2, (n['b'] + n['tp']) / 2
            if c[0] - 0.8 <= nx <= c[2] + 0.8 and c[1] - 14 <= ny <= c[1] + 1:
                e = dict(texto=n['t'], x=R2(nx), y=R2(ny))
                if 'piezas' in d:
                    k = [p for p in d['piezas'] if p['x0'] - 0.3 <= nx <= p['x1'] + 0.3 and 'n' in p]
                    if k:
                        e['pieza'] = k[0]['n']
                        e['pieza_tipo'] = k[0]['tipo']
                nd.append(e); used.add(id(n))
        nd.sort(key=lambda e: e['x'])
        d['numeros_borne_dibujados'] = nd
        out_aps[tag] = d
    sobr = [n['t'] + '@(%.1f,%.1f)' % ((n['l'] + n['r']) / 2, (n['b'] + n['tp']) / 2) for n in nums if id(n) not in used]
    sin_def = [t for t in labs if t not in aps]
    rr = []
    for r in rails:
        q = dict(id=r['id'], numero=r['numero'], tramo=r['tramo'], y_eje=R2((r['y0'] + r['y1']) / 2), x0=R2(r['x0']), x1=R2(r['x1']),
                 alto_pt=R2(r['y1'] - r['y0']), y0=R2(r['y0']), y1=R2(r['y1']), largo_mm=mm(r['x1'] - r['x0']), largo_lista_m=r['largo_lista_m'],
                 articulo='NS 35/ 7,5 PERF 2000MM (PXC.0801733)',
                 topes=[[R2(a), R2(b)] for a, b in TOPES.get(r['id'], [])])
        if r['id'] in TOPES_NOTA: q['nota_topes'] = TOPES_NOTA[r['id']]
        if 'nota' in r: q['nota'] = r['nota']
        rr.append(q)
    cc = []
    for k in canal:
        b = k['b']
        q = dict(id=k['id'], b=[R2(v) for v in b], horizontal=k['horizontal'], tipo=k['tipo'], articulo=k['articulo'],
                 ancho_mm=mm(min(b[2] - b[0], b[3] - b[1])), largo_mm=mm(max(b[2] - b[0], b[3] - b[1])), largo_lista=k['lista'])
        if 'nota' in k: q['nota'] = k['nota']
        cc.append(q)
    res = dict(region=[R2(v) for v in region], region_mm=[mm(region[2] - region[0]), mm(region[3] - region[1])],
               rieles=rr, canaletas=cc, aparatos=out_aps)
    if otros: res['otros_elementos'] = otros
    if sobr: res['numeros_sin_aparato'] = sobr
    if sin_def: res['etiquetas_sin_definir'] = sin_def
    return res

principal = build(PRINC, RIELES_P, CANAL_P, AP_P, nombre='principal')
principal['zonas'] = {
    'electrica': dict(b=[587.59, 292.29, 913.57, 745.83], nota='canaletas U2-U9 y rieles U10-U14'),
    'hidraulica': dict(b=[913.57, 129.29, 1094.28, 745.83],
                       nota='unidad hidraulica BH (motor -M1/-BH-01-M), BH_01_ZV, PT001, LS001A y 12F2. En las vistas 24/26 hay una PLACA DIVISORIA entre esta zona y la electrica (no esta dibujada en la hoja 8)'),
    'margen_inferior_libre': dict(b=[573.42, 129.29, 913.57, 292.29], nota='sin aparatos (abajo esta la bateria 12PB1 en el piso del gabinete)'),
}
lateral = build(LAT, RIELES_L, CANAL_L, AP_L, OTROS_L, nombre='lateral')

res = {
    'pagina': 8,
    'documento': 'ZPL-76884 Rev 1 - mSafe2+ PAE (EPLAN), hoja 08 "Detalle bandejas"',
    'unidades': 'pt de la pagina PDF 8 (1192.04 x 851.39), origen abajo-izquierda; caja/b = [x0, y0, x1, y1]',
    'escala_mm_por_pt': round(MM, 5),
    'escala_explicacion': (
        'Escala 1:4 exacta (1 pt = 25.4/72 mm x 4 = 1.41111 mm). Se comprobo de 4 formas: '
        '(1) el perfil del riel DIN mide 24.80 pt entre sus bordes = 35.0 mm; '
        '(2) el ancho de las canaletas CD 40X80/40X40 mide 28.35 pt = 40.0 mm y el de las CD 60X80 42.52 pt = 60.0 mm; '
        '(3) los largos de la lista de articulos de la hoja 31: U4 0,42 m = 297.63 pt, U5 0,24 m = 170.07 pt, U6 0,33 m = 233.85 pt, U3 0,54 m = 382.67 pt, U19 0,33 m = 233.86 pt, U16 0,16 m = 113.38 pt; '
        '(4) las cotas de la hoja 29 (misma escala que la 8): la linea de cota de 420 mm mide 291.97 pt + 2 flechas de 2.835 pt = 297.64 pt; 330 mm -> 228.19 + 5.67 = 233.86 pt; 540 mm -> 377.01 + 5.67 = 382.68 pt.'),
    'convencion_riel': 'riel 1 = el de arriba; en la principal los rieles 2 y 3 estan cortados en dos tramos por la canaleta vertical U6 (izquierdo U11/U13 de 240 mm, derecho U12/U14 de 140 mm); en la lateral el riel 2 son U18 (135 mm) y U21 (75 mm) separados por un hueco',
    'convencion_etiquetas': 'EPLAN pone la etiqueta de cada bornera (y de los grupos de reles 42KR/61KR) SOBRE EL TOPE de su izquierda, en texto vertical; la de los aparatos (fuentes, fusibles, barreras, reles de seguridad, termomagneticas) centrada sobre el cuerpo. Las piezas de una bornera son las que siguen a la derecha de su tope hasta el tope siguiente.',
    'principal': principal,
    'lateral_izquierda': lateral,
}
res['ubicacion_en_gabinete'] = {
    'fuentes': 'hojas 6 (topografico exterior), 7 (vista 2D interior frontal), 24 (vistas 2D internas), 25 (3D), 26 (vista superior), 27 (vistas 2D bandejas a color), 28 (vistas 2D gabinete), 31 (detalle de ductos y rieles con la lista de canaletas y rieles)',
    'bandeja_principal': 'placa de FONDO del gabinete, dibujada como se ve de frente con la puerta abierta (izquierda del dibujo = lado de la bandeja lateral). La parte izquierda (x < 913.6) es la zona electrica; la derecha es la zona de la unidad hidraulica, separada por una placa divisoria perpendicular al fondo (hojas 24 "VISTA DERECHA INTERNA DESDE PLACA DIVISORIA" y 26).',
    'bandeja_lateral_izquierda': 'placa sobre la PARED LATERAL IZQUIERDA, dibujada como se ve desde adentro mirando hacia la pared: el borde izquierdo del dibujo (x=192.6) es el lado de la PUERTA (frente) y el derecho (x=469) es el lado del FONDO, junto al borde izquierdo de la bandeja principal (comprobado con la hoja 24 izquierda, donde la puerta queda a la izquierda, y con la vista superior de la hoja 26, donde el riel U19 llega al borde del lado de la puerta). La zona baja (entre U15 y U17) tiene una tapa transparente con 4 separadores (hoja 25).',
    'puerta': 'SI hay aparatos en la puerta (hoja 31 "INTERIOR DE PUERTA" y hoja 6): -21PCB01 (placa E2.5 con display, en el interior de la puerta, con la canaleta U22 CD 40X40 0,45 m y un riel debajo), -13MS1 (selector TeSys VARIO VBF1 "ENCENDIDO/APAGADO", al frente de la puerta) y -42DB1 (parada de emergencia XB4BS8442 + contacto ZBE102, al frente de la puerta). Ninguno esta dibujado en la hoja 8.',
    'pared_lateral_izquierda_exterior': '-11MS1 (selector VARIO VBF1 "ALIMENTACION / CARGA BATERIA") en la cara exterior de la pared izquierda (hojas 6 "VISTA LATERAL IZQUIERDA", 28 y 26); su cuerpo probablemente entra por el hueco de la bandeja lateral entre U18 y U21.',
    'piso_y_campo': '-12PB1 bateria 12 V 68 Ah en el piso, debajo de la zona electrica; bloque de valvulas con -SP_1, -SP_2, -SP_3 (solenoides 12 VDC) en el piso del compartimiento hidraulico (abajo a la derecha, hojas 7 y 25). -M1/-BH-01-M es el motor de la unidad hidraulica BH. -42DS (fin de carrera, sensor de puerta) no aparece en ninguna vista: ubicacion sin determinar (probable marco o placa divisoria junto a la puerta).',
    'no_ubicados': '-12 (tapon negro ZB5SZ3 para orificio de 22 mm): no se ve en las vistas; probable orificio de reserva en la puerta o en un lateral.',
}
res['dudas'] = [
    'Orden de los modulos 61KR1..61KR4 dentro del grupo -61KR (supuesto izquierda a derecha; la hoja 8 no rotula cada modulo). 42KR tiene un solo modulo (42KR1).',
    'Los aparatos de la zona hidraulica (BH_01_ZV, PT001, LS001A, motor M1) estan en la placa principal pero del otro lado de la placa divisoria: decidir si en el instructivo van como destino en la bandeja o como "campo/LI".',
    'La caja de PT001 es el racor que asoma a la derecha del bloque, junto a la etiqueta; no hay contorno claro del transmisor en la vista frontal (baja confianza).',
    'El rectangulo blanco de la lateral (x 289.3-343.2) no tiene etiqueta; lo tome como hueco de la placa para el selector 11MS1 (no tiene bornes en la bandeja).',
    'En la hoja 8 todos los trazos son negros: el tipo "intrinseca (azul)" de U6, U7 y U9 sale de la hoja 31 (CD ... BU) y del color azul de las hojas 7 y 27.',
    'La pagina 30 del PDF es "Cotas de Carteleria"; el "Detalle de ductos y rieles" esta en la pagina 31.',
]
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'bandejas.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)

# -------------------------------------------------- chequeos
for nombre, t in (('principal', principal), ('lateral', lateral)):
    print('==', nombre, len(t['aparatos']), 'aparatos; sin aparato:', t.get('numeros_sin_aparato'), 'sin definir:', t.get('etiquetas_sin_definir'))
    for tag, d in t['aparatos'].items():
        print('  %-9s riel=%s %-10s label=(%.1f,%.1f) %s | nums=%s' % (tag, d['riel'], d['riel_id'], d['x'], d['y'], d['etiqueta_sobre'][:22],
              ' '.join('%s/%s' % (n['texto'], n.get('pieza', '-')) for n in d['numeros_borne_dibujados'])))
json.dump(res, open(os.path.join(os.path.dirname(__file__), 'bandejas_last.json'), 'w', encoding='utf-8'), ensure_ascii=False)
