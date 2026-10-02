# -*- coding: utf-8 -*-
"""Puntos de borne del riel 1 de la bandeja principal (ZPL-76884, pag. PDF 8).
Coordenadas medidas en los vectores (page_strokes) con primitivas.circulos / _contornos; ver 'como'."""
import json, os, re

MAPEO = r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo'
RAIL_Y = 657.25          # eje del riel U10
ZONA = {'11PS1', '11PS2', '13PS1', '11F1', '11F2', '12F3', '13F4', '13F5', '13F6', '42KS1', '42KR1',
        '61KR1', '61KR2', '61KR3', '61KR4', '32XAI', 'XPE'}
HIDRAULICA = {'12F2', 'BH', 'BH-01-M', 'BH_01_ZV', 'PT001', 'LS001A', 'X1'}

# ------------------------------------------------------------------ geometria medida (pt pagina 8)
# MEAN WELL NDR-240-24: TB2 4 circulos (r 1.52, dentro de triangulos), TB1 3 circulos r 1.81
NDR = {
    '11PS1': {'TB2': [637.26, 641.71, 646.25, 650.86], 'TB2_y': 696.41,
              'TB1': [642.49, 648.07, 653.48], 'TB1_y': 619.48},
    '11PS2': {'TB2': [681.90, 686.36, 690.90, 695.50], 'TB2_y': 696.41,
              'TB1': [687.14, 692.72, 698.12], 'TB1_y': 619.48},
}
NDR_NOMBRE = {('TB1', '1'): 'FG', ('TB1', '2'): 'N', ('TB1', '3'): 'L',
              ('TB2', '1'): '-V', ('TB2', '2'): '-V', ('TB2', '3'): '+V', ('TB2', '4'): '+V'}
# MEAN WELL DDR-120A-24 (13PS1): TB2 arriba 4 aberturas cuadradas 2.83 pt; TB1 abajo 3 hexagonos
DDR_TB2 = [716.895, 720.495, 723.77, 727.37]; DDR_TB2_Y = 698.895
DDR_TB1 = [719.86, 723.54, 727.23]; DDR_TB1_Y = 619.69
DDR_PIN = {'-Vo': ('TB2', 1), '(-Vo)': ('TB2', 2), '+Vo': ('TB2', 3), '(+Vo)': ('TB2', 4),
           'PE': ('TB1', 1), '-Vin': ('TB1', 2), '+Vin': ('TB1', 3)}
# Portafusibles Schneider DF101 (hexagono r 2.13) y DF141 (12F3, hexagono r 2.5)
DF = {'11F1': 747.57, '11F2': 759.97, '13F4': 790.98, '13F5': 803.38, '13F6': 815.78}
DF_Y = {'1': 682.88, '2': 635.40}
DF141 = {'x': 775.56, '1': 690.05, '2': 627.41}
# Phoenix PSR-SCP-24UC/ESA2/4X1/1X2/B (42KS1): 4 filas de 4 tornillos octogonales (2.84 pt)
KS_X = [831.40, 834.95, 838.49, 842.03]
KS_ROW = {'arr_ext': 687.10, 'arr_int': 680.58, 'abj_int': 634.23, 'abj_ext': 627.10}
KS_PIN = {}
for i, p in enumerate(['A1', 'S34', 'S33', 'S11']):
    KS_PIN[p] = ('arr_ext', i)
for i, p in enumerate(['S12', '51', '52', 'A2']):
    KS_PIN[p] = ('arr_int', i)
for i, p in enumerate(['43', '44', '13', '14']):
    KS_PIN[p] = ('abj_int', i)
for i, p in enumerate(['33', '34', '23', '24']):
    KS_PIN[p] = ('abj_ext', i)
# 42KS1 sin pin en la lista: pin del esquema hoja 42 (conexiones.json, *_propuesto)
# Phoenix RIF-0-RPT-xxDC/21: columna por modulo; circulo grande de entrada del conductor
RIF_X = {'42KR1': 853.63, '61KR1': 864.645, '61KR2': 868.97, '61KR3': 873.295, '61KR4': 877.625}
RIF_Y = {'42KR1': {'11': 686.29, '14': 679.91, '12': 673.60, 'A1': 634.57, 'A2': 628.21},
         '61KR': {'11': 686.31, '14': 679.84, '12': 673.48, 'A1': 634.48, 'A2': 628.16}}
# PTTB 4-HESI (32XAI): 4 bocas redondas r 2.06 en x 888.77
XAI_X = 888.77
XAI_Y = {('1', 'ARRIBA'): 691.72, ('F1', 'ARRIBA'): 672.76, ('F1', 'ABAJO'): 641.80, ('1', 'ABAJO'): 629.44}
# PT 2,5-QUATTRO-PE (XPE): 3 piezas, bocas r 1.70
XPE_X = {'1': 900.13, '2': 903.77, '3': 907.43}
XPE_Y = {'1': 677.86, '2': 670.63, '3': 644.21, '4': 636.99}


def tag_de(d):
    return d.lstrip('-').split(':')[0] if d else None


def zona_otro(tag, zona):
    if tag is None:
        return '?'
    t = tag.replace('+Campo', '')
    if t in HIDRAULICA or tag in HIDRAULICA:
        return 'E8'
    if t in ZONA:
        return 'riel1'
    if zona == 'bandeja_principal':
        return 'bandeja'
    return 'LI'


def punto(d, cable_info):
    """d = designacion EPLAN (o la propuesta cuando EPLAN no da pin). Devuelve dict sin 'd'/'cables'."""
    s = d.lstrip('-')
    parts = s.split(':')
    tag = parts[0]
    if tag in NDR:
        tb, pin = parts[1], parts[2]
        xs = NDR[tag][tb]
        x = xs[int(pin) - 1]
        y = NDR[tag][tb + '_y']
        r = 1.52 if tb == 'TB2' else 1.81
        nom = NDR_NOMBRE[(tb, pin)]
        lado = 'ARRIBA' if tb == 'TB2' else 'ABAJO'
        orden = ['primer', 'segundo', 'tercer', 'cuarto'][int(pin) - 1]
        como = (f"MEAN WELL NDR-240-24, {tb} pin {pin} = {nom}: {orden} tornillo desde la izquierda de la fila de "
                f"{len(xs)} circulos {'(r 1.52, cada uno entre triangulos)' if tb == 'TB2' else '(r 1.81)'} "
                f"{'de arriba' if tb == 'TB2' else 'de abajo'} (y={y}). Hoja 11: simbolo TB1 1 FG / 2 N / 3 L y TB2 1 -V / 2 -V / 3 +V / 4 +V; "
                f"hoja de datos NDR-240 y referencia 75286 (fotos: '-V -V +V +V' arriba, 'FG N L' abajo). Cable "
                f"{'sale por arriba' if tb == 'TB2' else 'sale por abajo'}.")
        return dict(tag=tag, texto_taller=f"{tag} {tb} {pin} ({nom})", x=x, y=y, r=r, lado=lado,
                    confianza='alta', como=como)
    if tag == '13PS1':
        name = parts[1]
        tb, pin = DDR_PIN[name]
        if tb == 'TB2':
            x, y, r = DDR_TB2[pin - 1], DDR_TB2_Y, 1.42
            como = (f"MEAN WELL DDR-120A-24, TB2 (salida, arriba) pin {pin}: abertura cuadrada {pin} de 4 desde la izquierda "
                    f"(2.83 x 2.83 pt, y={y}). Hoja de datos DDR-120 y referencias 75286/66817 (fotos): TB2 = -Vo -Vo +Vo +Vo. ")
            if name in ('-Vo', '(-Vo)'):
                como += ("EPLAN distingue los dos -Vo como '-Vo' y '(-Vo)' (hoja 13: +Vo, -Vo, (+Vo), (-Vo)); regla del n-esimo pin "
                         "del 66817: '-Vo' = 1er tornillo -Vo (pin 1), '(-Vo)' = 2do (pin 2). Mismo potencial.")
                conf = 'media'
            else:
                como += "+Vo = pin 3 (el primer +Vo; el 4 queda libre)."
                conf = 'alta'
            lado = 'ARRIBA'
        else:
            x, y, r = DDR_TB1[pin - 1], DDR_TB1_Y, 1.52
            como = (f"MEAN WELL DDR-120A-24, TB1 (entrada, abajo a la derecha) pin {pin} = {name}: hexagono {pin} de 3 desde la "
                    f"izquierda (y={y}). Hoja de datos DDR-120: TB1 1 FG, 2 -Vin, 3 +Vin (fotos 75286/66817). Hoja 13: simbolo +Vin -Vin PE.")
            conf = 'alta'
            lado = 'ABAJO'
        return dict(tag=tag, texto_taller=f"13PS1 {name}", x=x, y=y, r=r, lado=lado, confianza=conf, como=como)
    if tag in DF:
        pin = parts[1]
        x, y = DF[tag], DF_Y[pin]
        lado = 'ARRIBA' if pin == '1' else 'ABAJO'
        fus = '6 A' if tag == '13F6' else '10 A'
        como = (f"Portafusible Schneider DF101 (10x38 gG {fus}), borne {pin}: tornillo {'de arriba' if pin == '1' else 'de abajo'} "
                f"(hexagono con cruz, r 2.13, y={y}) en la columna x={x} bajo la etiqueta. Marcado TeSys DF 1 arriba / 2 abajo; "
                f"esquema dibuja 1 arriba.")
        return dict(tag=tag, texto_taller=f"{tag} {lado}", x=x, y=y, r=2.13, lado=lado, confianza='alta', como=como)
    if tag == '12F3':
        pin = parts[1]
        x, y = DF141['x'], DF141[pin]
        lado = 'ARRIBA' if pin == '1' else 'ABAJO'
        como = (f"Portafusible Schneider DF141 (14x51 aM 32 A, 26.5 mm), borne {pin}: tornillo {'de arriba' if pin == '1' else 'de abajo'} "
                f"(hexagono con cruz, r 2.5, y={y}). Marcado 1 arriba / 2 abajo (hoja 12).")
        return dict(tag=tag, texto_taller=f"12F3 {lado}", x=x, y=y, r=2.5, lado=lado, confianza='alta', como=como)
    if tag == '42KS1':
        pin = parts[1]
        fila, col = KS_PIN[pin]
        x, y = KS_X[col], KS_ROW[fila]
        lado = 'ARRIBA' if fila.startswith('arr') else 'ABAJO'
        bloque = {'arr_ext': 'enchufe de arriba TRASERO (fila exterior): A1 S34 S33 S11',
                  'arr_int': 'enchufe de arriba DELANTERO (fila interior): S12 51 52 A2',
                  'abj_int': 'enchufe de abajo DELANTERO (fila interior): 43 44 13 14',
                  'abj_ext': 'enchufe de abajo TRASERO (fila exterior): 33 34 23 24'}[fila]
        como = (f"Phoenix PSR-SCP-24UC/ESA2/4X1/1X2/B, borne {pin}: {bloque}, tornillo {col + 1} de 4 desde la izquierda "
                f"(octogono 2.84 pt, x={x}, y={y}). Disposicion sacada de fotos del aparato real 2963802 (enchufes rotulados "
                f"'A1 S34 S33 S11' atras y 'S12 51 52 A2' adelante; rotulo frontal de la carcasa A1|S34|S33|S11 / S12|51|52|A2 arriba y "
                f"43|44|13|14 / 33|34|23|24 abajo). Los 13..44 estan TODOS abajo (no 13/23/33/43 arriba como en el esquema de caja).")
        if lado == 'ABAJO':
            como += (" Que la fila 43 44 13 14 sea la interior y 33 34 23 24 la exterior sale de leer el rotulo como mapa "
                     "(fila de arriba del rotulo = enchufe de mas arriba, igual que arriba); A CONFIRMAR en el aparato.")
            conf = 'media'
        else:
            conf = 'alta'
        if len(parts) == 2 and cable_info.get('pin_propuesto'):
            como += f" EPLAN no da el pin ('{cable_info['d_original']}'): pin {pin} por el esquema hoja 42."
            conf = 'media' if conf == 'alta' else conf
        return dict(tag=tag, texto_taller=f"42KS1 {pin}", x=x, y=y, r=1.42, lado=lado, confianza=conf, como=como)
    if tag in RIF_X:
        pin = parts[1].replace('+', '').replace('-', '')
        x = RIF_X[tag]
        y = (RIF_Y['42KR1'] if tag == '42KR1' else RIF_Y['61KR'])[pin]
        lado = 'ARRIBA' if pin in ('11', '14', '12') else 'ABAJO'
        celda = {'11': 'boca exterior (la mas lejos del riel) del lado contactos = 11 (C)',
                 '14': 'boca del medio del lado contactos = 14 (NA)',
                 '12': 'boca interior del lado contactos = 12 (NC)',
                 'A1': 'boca interior del lado bobina (junto al LED) = A1+',
                 'A2': 'boca exterior del lado bobina = A2-'}[pin]
        mod = 1 if tag == '42KR1' else int(tag[-1])
        como = (f"Rele Phoenix RIF-0-RPT-{'24' if tag == '42KR1' else '12'}DC/21, modulo {mod} a la derecha de la etiqueta "
                f"-{tag[:4]} (columna x={x}): {celda}; centro del circulo grande de entrada del conductor (r ~1.45, y={y}). "
                f"Disposicion de las referencias 75286 y 66817 (numeros moldeados, fotos): 11/14/12 arriba del extremo hacia el rele, "
                f"A1 junto al LED y A2 en el extremo de abajo.")
        conf = 'alta'
        if tag != '42KR1':
            como += " Orden 61KR1..61KR4 de izquierda a derecha SUPUESTO: la hoja 8 solo rotula '-61KR' sobre el tope."
            conf = 'media'
        txt_pin = pin
        return dict(tag=tag, texto_taller=f"{tag} {txt_pin}", x=x, y=y, r=1.45, lado=lado, confianza=conf, como=como)
    if tag == '32XAI':
        nivel = parts[1]
        lado = cable_info['lado_esquema']
        y = XAI_Y[(nivel, lado)]
        ext = 'del EXTREMO' if nivel == '1' else 'INTERIOR'
        como = (f"Phoenix PTTB 4-HESI (5X20) portafusible de doble piso, unica pieza de 32XAI (x={XAI_X}): nivel {nivel} "
                f"({'paso directo, piso de abajo' if nivel == '1' else 'con fusible 100 mA, piso de arriba'}) = boca {ext} "
                f"{'de arriba' if lado == 'ARRIBA' else 'de abajo'} (circulo r 2.06, y={y}). EPLAN no da punto ('-32XAI:{nivel}'): "
                f"el lado sale de la hoja 32 (simbolo vertical: {cable_info['cable']} {'arriba' if lado == 'ARRIBA' else 'abajo'}). "
                f"Piso: referencia 75286 (31XAI, mismo articulo; foto: 2142 en la boca de mas arriba) y 66817.")
        return dict(tag=tag, texto_taller=f"32XAI {nivel} {lado}", x=XAI_X, y=y, r=2.06, lado=lado,
                    confianza='alta', como=como)
    if tag == 'XPE':
        n, p = parts[1], parts[2]
        x, y = XPE_X[n], XPE_Y[p]
        lado = 'ARRIBA' if p in ('1', '2') else 'ABAJO'
        pos = {'1': 'ARRIBA extremo', '2': 'ARRIBA interior', '3': 'ABAJO interior', '4': 'ABAJO extremo'}[p]
        como = (f"Phoenix PT 2,5-QUATTRO-PE (verde), pieza {n} de 3 a la derecha de la etiqueta -XPE (numero '{n}' dibujado "
                f"debajo, x={x}); punto {p} = {pos} (boca push-in r 1.70, y={y}). Hojas 11 y 13: simbolo horizontal 1..4 de "
                f"izquierda a derecha; regla QUATTRO del taller (1 y 2 arriba, 1 extremo; 3 y 4 abajo, 4 extremo).")
        return dict(tag=tag, texto_taller=f"XPE {n}.{p}", x=x, y=y, r=1.70, lado=lado,
                    confianza='media' if False else 'alta', como=como)
    raise ValueError(d)


def main():
    con = json.load(open(os.path.join(MAPEO, 'conexiones.json'), encoding='utf-8'))
    puntos = []
    for r in con['conexiones']:
        for k in ('d1', 'd2'):
            o = 'd2' if k == 'd1' else 'd1'
            tag = r[k + '_tag']
            if tag not in ZONA:
                continue
            d = r[k]
            if r['d1'] == r['d2']:
                continue  # conexion interna del zocalo RIF-0 (61KRn -> 61KRn)
            num = r['num']
            if num:
                cab = num
            else:
                sec = str(r['seccion_mm2']).replace('.', ',').rstrip('0').rstrip(',') if r['seccion_mm2'] else ''
                cab = f"sin numero {r['color_norm']} {sec}".strip()
            info = {'cable': cab, 'd_original': d}
            dd = d
            prop = r.get(k + '_propuesto')
            if prop and len(d.lstrip('-').split(':')) == 1:
                dd = '-' + prop
                info['pin_propuesto'] = True
            if tag == '32XAI':
                # hoja 32 (vertical): el cable del tablero (1350, 2142) llega arriba; el de PT001 (3221, 3222) sale abajo
                info['lado_esquema'] = 'ABAJO' if tag_de(r[o]) == 'PT001' else 'ARRIBA'
            p = punto(dd, info)
            otro_tag = tag_de(r[o])
            item = {'d': d, 'cables': [cab]}
            if dd != d:
                item['d_usada'] = dd
            item.update(p)
            item['otro_extremo'] = r[o]
            if r.get(o + '_propuesto') and len(r[o].lstrip('-').split(':')) == 1:
                item['otro_extremo_pin_esquema'] = '-' + r[o + '_propuesto']
            item['otro_zona'] = zona_otro(otro_tag, r[o + '_zona'])
            item['color'] = r['color_norm']
            item['seccion_mm2'] = r['seccion_mm2']
            item['fila_lista'] = r['fila']
            puntos.append(item)
    # orden: de izquierda a derecha, arriba primero
    puntos.sort(key=lambda q: (round(q['x'], 0), -q['y']))
    return puntos


if __name__ == '__main__':
    pts = main()
    print(len(pts))
    for q in pts:
        print(f"{q['d']:<18} {','.join(q['cables']):<28} {q['texto_taller']:<24} {q['x']:8.2f} {q['y']:8.2f} {q['r']:.2f} {q['lado']:<6} {q['confianza']:<5} -> {q['otro_extremo']} [{q['otro_zona']}]")
    json.dump(pts, open('puntos_tmp.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
