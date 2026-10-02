import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')
from comps import *
from det_quattro import bocas
from det_dio import dio, octo
OUTD = r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo'
con = json.load(open(os.path.join(OUTD, 'conexiones.json'), encoding='utf-8'))
ZONA = ['12XP', '13X12V', '13X24V', '61XDO', '61X0V', '61XDIO', '15AIB1', '15DIB1', '15DIB2', '15DIB3']
E8 = {'12F2', 'BH', 'BH_01_ZV', 'PT001', 'LS001A', 'BH-01-M', 'M1', 'X1'}

# ---------- geometria ----------
QX = {'12XP': (622.6, 641.6), '13X12V': (648.2, 661.5), '13X24V': (668.0, 694.4),
      '61XDO': (701.0, 725.8), '61X0V': (732.4, 745.7)}
geo = {}
for tag, (x0, x1) in QX.items():
    cols = [c for c in bocas(x0, x1) if len(c[2]) == 4]
    piezas = []
    for xc, ys, pairs in cols:
        yy = sorted([p[0] for p in pairs], reverse=True)  # arriba-ext, arriba-int, abajo-int, abajo-ext
        piezas.append({'x': round(xc, 2), 'y': {1: round(yy[0], 2), 2: round(yy[1], 2), 3: round(yy[2], 2), 4: round(yy[3], 2)}})
    geo[tag] = piezas
    print(tag, [(p['x']) for p in piezas], piezas[0]['y'])
DX = [752.32, 755.97, 759.62, 763.27, 766.92]
geo['61XDIO'] = []
for i in range(4):
    bars = dio(DX[i], DX[i + 1])
    xu = round(sum(b[0] for b in bars) / len(bars), 2)
    bt = octo(DX[i], DX[i + 1], 526.8, 531.0); bb = octo(DX[i], DX[i + 1], 500.4, 504.6)
    geo['61XDIO'].append({'x': xu, 'y_arriba': round((bt[1] + bt[3]) / 2, 2), 'y_abajo': round((bb[1] + bb[3]) / 2, 2)})
print('61XDIO', geo['61XDIO'])
ss = segs_in(819, 474, 862, 557)
circ = {}
for c in components(ss):
    b = bbox(c); w = b[2] - b[0]; h = b[3] - b[1]
    if 2.6 < w < 3.0 and 2.6 < h < 3.0:
        k = (round((b[0] + b[2]) / 2, 2), round((b[1] + b[3]) / 2, 2))
        circ[k] = round(max(w, h) / 2, 2)
xs = sorted(set(k[0] for k in circ)); ys = sorted(set(k[1] for k in circ), reverse=True)
print('tornillos x', xs, 'y', ys)
Y_SUP_EXT, Y_SUP_INT, Y_INF_INT, Y_INF_EXT = ys
R_TOR = 1.4
BAR = {'15AIB1': [x for x in xs if 821.1 < x < 833.6], '15DIB1': [x for x in xs if 833.6 < x < 842.46],
       '15DIB2': [x for x in xs if 842.46 < x < 851.32], '15DIB3': [x for x in xs if 851.32 < x < 860.25]}
print(BAR)
PASO = 5.0 / 1.41111  # 5,0 mm a escala 1:4


def barrera(tag, pin):
    p = int(pin); X = BAR[tag]
    if tag == '15AIB1':
        xc = X[1]
        tabla = {3: (X[0], Y_SUP_EXT, 'enchufe [3 4 5] (OUT1), fila exterior dibujada de arriba, tornillo izquierdo'),
                 4: (X[1], Y_SUP_EXT, 'enchufe [3 4 5] (OUT1), fila exterior de arriba, tornillo del medio'),
                 5: (X[2], Y_SUP_EXT, 'enchufe [3 4 5], fila exterior de arriba, tornillo derecho'),
                 6: (X[0], Y_SUP_INT, 'enchufe delantero [6 7 8] (OUT2), fila interior dibujada de arriba, tornillo izquierdo'),
                 7: (X[1], Y_SUP_INT, 'enchufe [6 7 8] (OUT2), fila interior de arriba, tornillo del medio'),
                 8: (X[2], Y_SUP_INT, 'enchufe [6 7 8], fila interior de arriba, tornillo derecho'),
                 9: (X[0], Y_INF_INT, 'enchufe IS [9 10 11] (IN1), fila interior dibujada de abajo (pegada al cuerpo), tornillo izquierdo'),
                 10: (X[1], Y_INF_INT, 'enchufe IS [9 10 11] (IN1), fila interior de abajo, tornillo del medio'),
                 11: (X[2], Y_INF_INT, 'enchufe IS [9 10 11], fila interior de abajo, tornillo derecho'),
                 12: (X[0], Y_INF_EXT, 'enchufe IS [12 13 14] (IN2), fila exterior dibujada de abajo, tornillo izquierdo'),
                 13: (X[1], Y_INF_EXT, 'enchufe IS [12 13 14] (IN2), fila exterior de abajo, tornillo del medio'),
                 14: (X[2], Y_INF_EXT, 'enchufe IS [12 13 14], fila exterior de abajo, tornillo derecho'),
                 1: (round(xc - PASO / 2, 2), Y_SUP_EXT, 'enchufe de alimentacion [1 2] (+24 V), trasero, NO dibujado: queda detras del [3 4 5] con el tornillo a la misma altura (vista lateral del manual; regla del 75286/66817 y catalogo GS8536-EX); 2 bornes a paso 5,0 mm centrados en la carcasa: x = tornillo del medio - 2,5 mm'),
                 2: (round(xc + PASO / 2, 2), Y_SUP_EXT, 'enchufe de alimentacion [1 2] (0 V), trasero, NO dibujado: detras del [3 4 5], misma altura; x = tornillo del medio + 2,5 mm')}
    else:
        tabla = {1: (X[0], Y_SUP_EXT, 'enchufe de alimentacion [1 2] (+24 V), trasero: visto de frente queda DETRAS del [3 4] con el tornillo a la misma altura (vista lateral acotada del manual GS8512, correccion verificada del 75286); mismo punto que el borne 3, tornillo izquierdo'),
                 2: (X[1], Y_SUP_EXT, 'enchufe de alimentacion [1 2] (0 V), trasero, detras del [3 4]: mismo punto que el borne 4, tornillo derecho'),
                 3: (X[0], Y_SUP_EXT, 'enchufe [3 4] (OUT2, rele), fila exterior dibujada de arriba, tornillo izquierdo'),
                 4: (X[1], Y_SUP_EXT, 'enchufe [3 4] (OUT2), fila exterior de arriba, tornillo derecho'),
                 5: (X[0], Y_SUP_INT, 'enchufe delantero [5 6] (OUT1, rele), fila interior dibujada de arriba, tornillo izquierdo'),
                 6: (X[1], Y_SUP_INT, 'enchufe [5 6] (OUT1), fila interior de arriba, tornillo derecho'),
                 7: (X[0], Y_INF_INT, 'enchufe IS [7 8] (IN1), fila interior dibujada de abajo (pegada al cuerpo), tornillo izquierdo'),
                 8: (X[1], Y_INF_INT, 'enchufe IS [7 8] (IN1), fila interior de abajo, tornillo derecho'),
                 9: (X[0], Y_INF_EXT, 'enchufe IS [9 10] (IN2), fila exterior dibujada de abajo, tornillo izquierdo'),
                 10: (X[1], Y_INF_EXT, 'enchufe IS [9 10] (IN2), fila exterior de abajo, tornillo derecho')}
    return tabla[p]


puntas = {}
orden = []
for r in con['conexiones']:
    for a, b in (('d1', 'd2'), ('d2', 'd1')):
        tag = r.get(a + '_tag')
        if tag not in ZONA:
            continue
        cab = r['num'] if r['num'] else 'sin numero %s %s' % (r['color_norm'], r['seccion_mm2'])
        k = (r[a], cab)
        if k not in puntas:
            puntas[k] = {'d': r[a], 'cable': cab, 'tag': tag, 'borne': r.get(a + '_borne'), 'punto': r.get(a + '_punto'),
                         'otros': [], 'filas': [], 'color': r['color_norm'], 'seccion': r['seccion_mm2']}
            orden.append(k)
        P = puntas[k]
        otag = r.get(b + '_tag')
        z = 'E8' if otag in E8 else r.get(b + '_zona')
        P['otros'].append({'d': r[b], 'propuesto': r.get(b + '_propuesto'), 'zona': z, 'fila': r['fila']})
        P['filas'].append(r['fila'])

ZTXT = {'bandeja_principal': 'bandeja principal', 'lateral_izquierda': 'LI (bandeja lateral izquierda)',
        'fuera_topografico': 'LI (fuera de la bandeja: puerta/campo)', 'campo': 'LI (campo)',
        'E8': 'E8 (zona hidraulica / empalmes X1, se cablea en gabinete)'}
QMOD = {'12XP': 'PT 6-QUATTRO x3 (PXC.3212934), puente FBS 3-8 BU en 1-2-3',
        '13X12V': 'PT 6-QUATTRO x2 (PXC.3212934)',
        '13X24V': 'PT 6-QUATTRO x4 (PXC.3212934): 1, FBS 2-8 rojo, 2, tapa D-PT 6-QUATTRO, 3, FBS 2-8 BU, 4 (la tapa entre 2 y 3 corre 1,55 pt las piezas 3 y 4)',
        '61XDO': 'PT 6-QUATTRO x4 (PXC.3212934), sin puentes',
        '61X0V': 'PT 6-QUATTRO x2 (PXC.3212934), puente FBS 2-8 BU'}
BOCA = {1: 'ARRIBA extremo (la boca mas lejos del riel)', 2: 'ARRIBA interior (la mas cerca del riel)',
        3: 'ABAJO interior (la mas cerca del riel)', 4: 'ABAJO extremo (la mas lejos del riel)'}
out = []
for k in orden:
    P = puntas[k]; tag = P['tag']; d = P['d']
    n_cond = len(P['filas'])
    otros = '; '.join('%s%s -> %s' % (o['d'], (' [=' + o['propuesto'] + ']') if o['propuesto'] else '', ZTXT.get(o['zona'], o['zona'])) for o in P['otros'])
    rec = {'d': d, 'cables': [P['cable']], 'tag': tag}
    if tag in QX:
        n = int(P['borne']); p = int(P['punto'])
        pz = geo[tag][n - 1]
        rec.update(texto_taller='%s %d.%d' % (tag, n, p), x=pz['x'], y=pz['y'][p], r=2.5,
                   lado='ARRIBA' if p <= 2 else 'ABAJO', confianza='alta',
                   como='%s. Pieza %d contada desde el tope de la etiqueta (numero "%d" dibujado debajo), punto EPLAN %d = boca %s. Centro del contorno redondeado de la entrada push-in (page_strokes: la boca mide 5,0 x 5,7 pt). Regla N.p del taller: 1 y 2 arriba (1 extremo), 3 y 4 abajo (4 extremo); el simbolo EPLAN del esquema dibuja los puntos 1-2-3-4 en ese orden.' % (QMOD[tag], n, n, p, BOCA[p]))
    elif tag == '61XDIO':
        n = int(P['borne']); pz = geo['61XDIO'][n - 1]
        anodo = P['cable'] == '1264'
        lado = 'ABAJO' if anodo else 'ARRIBA'
        rec.update(texto_taller='61XDIO %d %s' % (n, lado), x=pz['x'], y=pz['y_abajo'] if anodo else pz['y_arriba'], r=1.6,
                   lado=lado, confianza='alta',
                   como='PT 2,5-DIO/L-R (PXC.3210224), pieza %d (numero "%d" dibujado debajo), una boca push-in por extremo; centro del octogono con U. %s Hoja 61: anodo a la izquierda del diodo (1264 entra en el 1 y el puente FBS 4-5 BU une los anodos de 1 a 4), catodo a la derecha (6171-6174 a 61XDO N.2). En la pag. 8 (y en la vista 3D de la hoja de hileras) el puente esta dibujado en la mitad de ABAJO: el anodo esta fisicamente ABAJO y el catodo ARRIBA (igual que 62XDIO del 75286 y 61XDIO del 66817, confirmados con fotos). EPLAN no da punto (-61XDIO:%d en los dos extremos): el lado sale del cable.' % (n, n, 'ANODO (lado del puente): boca de ABAJO.' if anodo else 'CATODO: boca de ARRIBA.', n))
    else:
        x, y, txt = barrera(tag, P['borne'])
        p = int(P['borne'])
        lado = 'ARRIBA' if (tag == '15AIB1' and p <= 8) or (tag != '15AIB1' and p <= 6) else 'ABAJO'
        modelo = 'CHENZHU GS8536-EX (2 AI, 17,5 mm)' if tag == '15AIB1' else 'CHENZHU GS8512-EX.22 (2 DI salida rele, 12,5 mm)'
        conf = 'alta'
        if p in (1, 2) or tag == '15DIB3':
            conf = 'media'
        rec.update(texto_taller='%s %d' % (tag, p), x=x, y=y, r=R_TOR, lado=lado, confianza=conf,
                   como='%s. %s. Tornillos dibujados (circulos de r=1,4 pt con ranura) en x %s; filas y=%.2f/%.2f arriba (lado seguro, verde) y %.2f/%.2f abajo (lado IS, azul, hacia la canaleta azul U7). Numero menor a la izquierda.%s' % (
                       modelo, txt, '/'.join('%.2f' % v for v in BAR[tag]), Y_SUP_EXT, Y_SUP_INT, Y_INF_INT, Y_INF_EXT,
                       ' OJO: las hojas 15 y 41 dicen que 15DIB3 queda prevista SIN barrera (bornes cuchilla abiertos); el punto es el de la barrera dibujada en la pag. 8.' if tag == '15DIB3' else ''))
    if n_cond > 1:
        rec['n_conductores'] = n_cond
        rec['como'] += ' Entran %d conductores del mismo cable %s en este borne (cadena de alimentacion de las barreras, filas %s de la lista): puntera doble.' % (n_cond, P['cable'], ', '.join(map(str, P['filas'])))
    rec['otro_extremo'] = otros
    if any(o['zona'] == 'E8' for o in P['otros']):
        rec['otro_extremo_estacion'] = 'E8'
    rec['color'] = P['color']; rec['seccion_mm2'] = P['seccion']
    rec['filas_lista'] = P['filas']
    out.append(rec)
print(len(out))
json.dump({'puntos': out}, open('puntos_tmp.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
