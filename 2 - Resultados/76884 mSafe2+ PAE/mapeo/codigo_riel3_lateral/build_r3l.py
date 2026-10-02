# -*- coding: utf-8 -*-
"""Mapeo de bornes del 76884 (mSafe2+ PAE, EPLAN): riel 3 de la bandeja principal (15XR, 42XC, 81XCM,
32XEX, 41XEX) y toda la bandeja lateral izquierda (12PS1, 12XPS, 11SK1, 11Q1, 11Q2, 11XPVAC, 11X220V).

Entrada: conexiones.json y bandejas.json (misma carpeta mapeo) + vectores de la pagina 8 (copia sin proteccion).
Salida : puntos_riel3_lateral.json y control_riel3_lateral.png en la carpeta mapeo.

x, y = centro de la boca push-in o del tornillo en pt de la pagina PDF 8 (origen abajo-izq); r = radio de la boca.
"""
import json, math, os, sys
from collections import OrderedDict
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from find_open import ring_groups          # bocas redondas (aros de 2 medias circunferencias)
from geo import segs_in, chains

MAP = os.path.dirname(AQUI)
C = json.load(open(os.path.join(MAP, 'conexiones.json'), encoding='utf-8'))
B = json.load(open(os.path.join(MAP, 'bandejas.json'), encoding='utf-8'))
AP_P = B['principal']['aparatos']
AP_L = B['lateral_izquierda']['aparatos']

ZONA = ['15XR', '42XC', '81XCM', '32XEX', '41XEX', '12PS1', '12XPS', '11SK1', '11Q1', '11Q2', '11XPVAC', '11X220V']
PTT_A = ('15XR', '81XCM')            # simbolo con :1/:2 dibujados ARRIBA (o a la izquierda): hojas 15 y 81
PTT_B = ('42XC', '32XEX', '41XEX')   # simbolo con :3/:4 dibujados ARRIBA: hojas 32, 41 y 42
HOJA = {'15XR': 15, '42XC': 42, '81XCM': 81, '32XEX': 32, '41XEX': 41, '12XPS': '12 y 81', '11XPVAC': 11,
        '11X220V': 11, '11Q1': 11, '11Q2': 11, '11SK1': 11, '12PS1': '12 y 81'}


def f2(v):
    return round(float(v), 2)


# ------------------------------------------------------------------------------------------------ geometria
def piezas(tag):
    a = AP_P.get(tag) or AP_L.get(tag)
    labels = {nb['pieza']: nb['texto'] for nb in a.get('numeros_borne_dibujados', [])}
    out = []
    for p in a.get('piezas', []):
        if 'tapa' in p['tipo']:
            continue
        q = dict(p)
        q['label'] = labels.get(p['n'])
        out.append(q)
    return out


def bocas_redondas(p, ywin=(340, 432)):
    """4 aros (PTT 2,5-2MT, PT 2,5-QUATTRO-PE, PTTB 4-HESI) de arriba hacia abajo: [ext. arriba, int. arriba,
    int. abajo, ext. abajo]"""
    g = ring_groups((p['x0'] - 0.2, ywin[0], p['x1'] + 0.2, ywin[1]))
    g = [q for q in g if 3.0 <= q['w'] <= 4.6 and q['span'] > 250]
    g = sorted(g, key=lambda q: -q['by'])
    assert len(g) == 4, (p, g)
    return [dict(x=q['bx'], y=q['by'], r=q['w'] / 2, w=q['w'], h=q['h']) for q in g]


def contornos_pt6(p, ywin, wmin=4.8):
    """bocas de PT 6 / PT 6-QUATTRO: contorno redondeado partido en varias polilineas; se juntan las de ancho
    >= wmin que se solapan en y y se toma el centro del rectangulo envolvente. De arriba hacia abajo."""
    S = segs_in((p['x0'] - 0.1, ywin[0], p['x1'] + 0.1, ywin[1]))
    cand = []
    for c in chains(S):
        if len(c) < 5:
            continue
        P = np.array(c)
        x0, y0 = P.min(0)
        x1, y1 = P.max(0)
        # contorno de la boca: ancho >= wmin, alto <= 6 pt y sin tocar los bordes de la pieza (los lados de la
        # carcasa van de borde a borde)
        if x1 - x0 >= wmin and 1.2 <= (y1 - y0) <= 6.0 and x0 >= p['x0'] + 0.2 and x1 <= p['x1'] - 0.05:
            cand.append([x0, y0, x1, y1])
    cand.sort(key=lambda b: -b[3])
    grupos = []
    for b in cand:
        for g in grupos:
            if b[1] <= g[3] + 0.05 and b[3] >= g[1] - 0.05:
                g[0] = min(g[0], b[0]); g[1] = min(g[1], b[1]); g[2] = max(g[2], b[2]); g[3] = max(g[3], b[3])
                break
        else:
            grupos.append(list(b))
    grupos.sort(key=lambda g: -g[3])
    return [dict(x=(g[0] + g[2]) / 2, y=(g[1] + g[3]) / 2, r=(g[2] - g[0]) / 2, w=g[2] - g[0], h=g[3] - g[1])
            for g in grupos]


def octogono_pt6(p, ywin):
    """bocas octogonales de 11XPVAC (PT 6): vertices de la polilinea sin los tramos largos (> 3 pt, son lineas
    de la carcasa) ni los puntos pegados al borde derecho de la pieza (recorte). Centro del envolvente."""
    S = segs_in((p['x0'] - 0.1, ywin[0], p['x1'] + 0.1, ywin[1]))
    todos = []
    for c in chains(S):
        if len(c) < 5:
            continue
        pts = []
        for a, b in zip(c, c[1:]):
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 3.0:
                continue
            pts += [a, b]
        pts = [q for q in pts if q[0] < p['x1'] - 0.1]
        if len(pts) < 4:
            continue
        P = np.array(pts)
        if P[:, 0].max() - P[:, 0].min() > 4.8:      # el octogono (entero o en dos mitades); no el cuadro interior
            todos += pts
    P = np.array(todos)
    x0, y0 = P.min(0)
    x1, y1 = P.max(0)
    assert x1 - x0 > 4.0 and y1 - y0 > 4.5, (p, x0, y0, x1, y1)
    return dict(x=(x0 + x1) / 2, y=(y0 + y1) / 2, r=min(x1 - x0, y1 - y0) / 2, w=x1 - x0, h=y1 - y0)


def tornillo(gx, gy, R=2.9):
    """tornillo de aparato modular: envolvente de los tramos cortos (circulo/hexagono + cruz) cerca del punto"""
    P = []
    for a, b in segs_in((gx - R - 1, gy - R - 1, gx + R + 1, gy + R + 1)):
        if math.hypot(b[0] - a[0], b[1] - a[1]) > 2.0:
            continue
        for q in (a, b):
            if math.hypot(q[0] - gx, q[1] - gy) <= R:
                P.append(q)
    P = np.array(P)
    x0, y0 = P.min(0)
    x1, y1 = P.max(0)
    return dict(x=(x0 + x1) / 2, y=(y0 + y1) / 2, r=min(x1 - x0, y1 - y0) / 2, w=x1 - x0, h=y1 - y0)


GEO = {}


def geo_borneras():
    for tag in ('15XR', '42XC', '81XCM', '32XEX', '41XEX'):
        for p in piezas(tag):
            GEO[(tag, p['label'])] = dict(pieza=p, bocas=bocas_redondas(p))
    for p in piezas('12XPS'):
        b = contornos_pt6(p, (505, 556))
        assert len(b) == 2, (p, b)
        GEO[('12XPS', p['label'])] = dict(pieza=p, bocas=b)
    for p in piezas('11X220V'):
        b = contornos_pt6(p, (350, 416))
        assert len(b) == 4, (p, b)
        GEO[('11X220V', p['label'])] = dict(pieza=p, bocas=b)
    for p in piezas('11XPVAC'):
        if 'QUATTRO' in p['tipo']:
            GEO[('11XPVAC', p['label'])] = dict(pieza=p, bocas=bocas_redondas(p, (355, 412)))
        else:
            GEO[('11XPVAC', p['label'])] = dict(pieza=p, bocas=[octogono_pt6(p, (393.5, 402.2)),
                                                               octogono_pt6(p, (364.5, 371.2))])
    # 11Q1 / 11Q2: 2 polos, tornillo arriba y abajo. Columnas a +/- 1/4 del ancho del cuerpo.
    for tag in ('11Q1', '11Q2'):
        a = AP_L[tag]
        x0, y0, x1, y1 = a['caja']
        cx = (x0 + x1) / 2
        q = (x1 - x0) / 4
        cols = {}
        for lado_x, gx in (('izq', cx - q), ('der', cx + q)):
            for lado_y, gy in (('ARRIBA', y1 - 9.0), ('ABAJO', y0 + 8.7)):
                cols[(lado_x, lado_y)] = tornillo(gx, gy)
        GEO[(tag, None)] = dict(tornillos=cols)
    # 11SK1: 3 tornillos ranurados en la franja de abajo (aros r~1.6)
    a = AP_L['11SK1']
    x0, y0, x1, y1 = a['caja']
    g = ring_groups((x0, y0, x1, y0 + 12))
    g = sorted([q for q in g if 2.8 <= q['w'] <= 3.6 and abs(q['w'] - q['h']) < 0.3], key=lambda q: q['bx'])
    assert len(g) == 3, g
    GEO[('11SK1', None)] = dict(tornillos=[dict(x=q['bx'], y=q['by'], r=q['w'] / 2) for q in g])


# ------------------------------------------------------------------------------------------------ resolucion
def ptt(tag, borne, punto):
    b = int(borne)
    impar = b % 2 == 1
    label = str(b if impar else b - 1)
    G = GEO[(tag, label)]
    p = G['pieza']
    if not p['tipo'].startswith('PTT'):
        raise ValueError((tag, borne, p['tipo']))
    puntos_ok = (2, 3) if impar else (1, 4)
    assert int(punto) in puntos_ok, (tag, borne, punto)
    if tag in PTT_A:
        lado = 'ARRIBA' if int(punto) in (1, 2) else 'ABAJO'
        regla = 'en la hoja %s el simbolo tiene :1/:2 dibujados arriba (o a la izquierda en horizontal) y :3/:4 abajo' % HOJA[tag]
    else:
        lado = 'ARRIBA' if int(punto) in (3, 4) else 'ABAJO'
        regla = 'en la hoja %s el simbolo tiene :3/:4 dibujados arriba (lado aparatos) y :1/:2 abajo (campo)' % HOJA[tag]
    piso = 'extremo' if impar else 'interior'
    idx = {('ARRIBA', 'extremo'): 0, ('ARRIBA', 'interior'): 1, ('ABAJO', 'interior'): 2, ('ABAJO', 'extremo'): 3}[(lado, piso)]
    bo = G['bocas'][idx]
    npz = p['n']
    como = ('%s, pieza %d de %s (la que tiene el numero %s debajo en la pag 8; lleva los bornes %s y %s). '
            'Borne %s %s = piso %s = boca %s %s (aro r %.1f pt, centro sacado de los arcos). '
            'Lado: %s, asi que :%s = %s. Piso: convencion del taller (impar = piso de abajo = boca del extremo; '
            'par = piso de arriba = boca interior), verificada con fotos en 75286 y 66817 para el mismo PTT.'
            % (p['tipo'], npz, tag, label, label, int(label) + 1, borne, 'impar' if impar else 'par',
               'de abajo' if impar else 'de arriba', piso, lado, bo['r'], regla, punto, lado))
    if tag == '41XEX' and label in ('7', '9'):
        como += ' OJO: en 41XEX las piezas 4 y 5 estan cambiadas (9-10 antes que 7-8) en la hoja de hileras y en la pag 8; se respeta el numero.'
    return dict(x=bo['x'], y=bo['y'], r=bo['r'], lado=lado, texto='%s %s %s' % (tag, borne, lado),
                confianza='alta', como=como, pieza=npz)


def quattro_pe(tag, borne, punto):
    G = GEO[(tag, str(borne))]
    p = G['pieza']
    k = int(punto)
    bo = G['bocas'][[0, 1, 2, 3][k - 1]]
    lado = 'ARRIBA' if k in (1, 2) else 'ABAJO'
    pos = {1: 'ARRIBA extremo', 2: 'ARRIBA interior', 3: 'ABAJO interior', 4: 'ABAJO extremo'}[k]
    como = ('%s (verde, PE), pieza %d de %s (numero %s). Punto %d = %s (convencion N.p del taller: 1 y 2 arriba, '
            '1 el extremo; 3 y 4 abajo, 4 el extremo). Aro r %.1f pt.' % (p['tipo'], p['n'], tag, borne, k, pos, bo['r']))
    if tag in ('15XR', '32XEX'):
        como += ' En la hoja %s el simbolo esta espejado (punto 4 a la izquierda); como los 4 puntos son PE y el cable es de campo (entra por abajo), se deja 4 = ABAJO extremo.' % HOJA[tag]
    else:
        como += ' Hoja 11: simbolo horizontal, el 4 es el de la derecha (= ABAJO por la regla horizontal) y de ahi sale la tierra al 11SK1.'
    return dict(x=bo['x'], y=bo['y'], r=bo['r'], lado=lado, texto='%s %s.%d' % (tag, borne, k),
                confianza='alta', como=como, pieza=p['n'])


def pttb_42xc(borne):
    G = GEO[('42XC', 'F1')]
    p = G['pieza']
    lado = 'ARRIBA'
    if borne == 'F1':
        bo = G['bocas'][1]
        piso = 'nivel del fusible = piso de arriba = boca INTERIOR'
    else:
        bo = G['bocas'][0]
        piso = 'paso directo = piso de abajo = boca del EXTREMO'
    como = ('PTTB 4-HESI (5X20), pieza 1 de 42XC (F1 debajo en la pag 8). EPLAN no da punto (-42XC:%s). '
            '%s: %s. Lado ARRIBA: en la hoja 42 el cable de la bandeja entra por arriba (el presostato PS1 de '
            'campo va abajo). Piso: hoja de datos Phoenix 3211886 (2do nivel con fusible) y 31XAI del 75286 '
            '(mismo articulo, fotos: el borne 1 entra por la boca del extremo). Aro r %.1f pt.'
            % (borne, borne, piso, bo['r']))
    return dict(x=bo['x'], y=bo['y'], r=bo['r'], lado=lado, texto='42XC %s %s' % (borne, lado),
                confianza='alta', como=como, pieza=p['n'])


def pt6(tag, borne, punto, nota_punto=None):
    G = GEO[(tag, str(borne))]
    p = G['pieza']
    k = int(punto)
    bo = G['bocas'][0 if k == 1 else 1]
    lado = 'ARRIBA' if k == 1 else 'ABAJO'
    forma = 'contorno redondeado' if tag == '12XPS' else 'octogono'
    como = ('PT 6 (borne de paso push-in, una boca por extremo), pieza %d de %s (numero %s). Punto :%d = boca de %s '
            '(%s de %.1f x %.1f pt, centro del envolvente). Hoja %s: simbolo vertical con :1 arriba.'
            % (p['n'], tag, borne, k, 'arriba' if k == 1 else 'abajo', forma, bo['w'], bo['h'], HOJA[tag]))
    if nota_punto:
        como += ' ' + nota_punto
    if tag == '12XPS' and str(borne) in ('7', '8'):
        como += ' 12XPS 7 y 8 llevan el puente enchufable FBS 2-8 (rojo) en el canal central: no ocupa boca.'
    return dict(x=bo['x'], y=bo['y'], r=min(bo['r'], 2.6), lado=lado, texto='%s %s %s' % (tag, borne, lado),
                confianza='alta', como=como, pieza=p['n'])


def quattro_pt6(tag, borne, punto):
    G = GEO[(tag, str(borne))]
    p = G['pieza']
    k = int(punto)
    bo = G['bocas'][k - 1]
    lado = 'ARRIBA' if k in (1, 2) else 'ABAJO'
    pos = {1: 'ARRIBA extremo', 2: 'ARRIBA interior', 3: 'ABAJO interior', 4: 'ABAJO extremo'}[k]
    como = ('PT 6-QUATTRO (4 bocas push-in, 2 por extremo), pieza %d de %s (numero %s). Punto %d = %s (convencion '
            'N.p; en la hoja 11 el simbolo va 1..4 de arriba hacia abajo). Contorno de %.1f x %.1f pt, centro del envolvente.'
            % (p['n'], tag, borne, k, pos, bo['w'], bo['h']))
    return dict(x=bo['x'], y=bo['y'], r=2.4, lado=lado, texto='%s %s.%d' % (tag, borne, k),
                confianza='alta', como=como, pieza=p['n'])


def proteccion(tag, borne):
    T = GEO[(tag, None)]['tornillos']
    if tag == '11Q1':
        # diferencial 2P: neutro a la IZQUIERDA (Easy9 EZ9R36225 y Acti9 iID A9R11225: "neutral position: left")
        m = {'N': ('izq', 'ARRIBA', 'N'), "N'": ('izq', 'ABAJO', 'N'), '1': ('der', 'ARRIBA', 'F'), '2': ('der', 'ABAJO', 'F')}
        lx, ly, polo = m[borne]
        to = T[(lx, ly)]
        como = ('Diferencial 2P (lista: EZ9F36225 "ACTI9 IID 2P 25A 30MA AC RCCB"). Tornillo %s del polo %s '
                '(circulo r %.2f con cruz). Polo de neutro a la IZQUIERDA: ficha Schneider "neutral position: left" '
                'tanto del Easy9 EZ9R36225 como del Acti9 iID A9R11225, y 75286 (foto, N impresa a la izquierda). '
                'OJO: el esquema (hoja 11) dibuja 1 a la izquierda y N a la derecha; el lado fisico manda. '
                'EPLAN: 1/2 = fase, N/N\' = neutro.' % ('superior' if ly == 'ARRIBA' else 'inferior',
                                                        'izquierdo' if lx == 'izq' else 'derecho', to['r']))
        conf = 'alta'
    else:
        m = {'1': ('izq', 'ARRIBA', 'F'), '2': ('izq', 'ABAJO', 'F'), '3': ('der', 'ARRIBA', 'N'), '4': ('der', 'ABAJO', 'N')}
        lx, ly, polo = m[borne]
        to = T[(lx, ly)]
        como = ('Termomagnetica Schneider EZ9F34210 2P 10 A. Borne %s = tornillo %s del polo %s (hexagono con cruz, '
                'r %.2f). Marcado Schneider 2P: 1-2 polo izquierdo, 3-4 polo derecho, impares arriba. Hoja 11: 1 marron '
                '(fase) y 3 celeste (neutro).' % (borne, 'superior' if ly == 'ARRIBA' else 'inferior',
                                                  'izquierdo' if lx == 'izq' else 'derecho', to['r']))
        conf = 'alta'
    return dict(x=to['x'], y=to['y'], r=to['r'], lado=ly, texto='%s %s %s' % (tag, polo, ly), confianza=conf, como=como)


def toma(borne):
    T = GEO[('11SK1', None)]['tornillos']
    i = {'L': 0, 'PE': 1, 'N': 2}[borne]
    to = T[i]
    como = ('Phoenix EO-I/UT (toma tipo I, 45 x 75 mm, bornes a tornillo M3). Los 3 tornillos ranurados estan en la '
            'franja de ABAJO del dibujo (aros r %.2f a y %.1f); regla del taller: 11SK1 todo por abajo. Orden supuesto '
            'L / PE / N de izquierda a derecha, igual que el simbolo de la macro EPLAN (hoja 11); la ficha Phoenix no '
            'trae la vista de bornes: A CONFIRMAR en el aparato (PE al medio es lo habitual).' % (to['r'], to['y']))
    return dict(x=to['x'], y=to['y'], r=to['r'], lado='ABAJO', texto='11SK1 %s ABAJO' % borne, confianza='media', como=como)


def regulador(borne):
    a = AP_L['12PS1']
    x0, y0, x1, y1 = a['caja']
    cx = (x0 + x1) / 2
    orden = ['+Pan', '-Pan', '+Bat', '-Bat', '+Car', '-Car']
    if borne in orden:
        k = orden.index(borne)
        x = cx - 17.5 + 7.0 * k
        r = 1.8
        que = 'cable propio de potencia (10 AWG = 6 mm2, como dice la lista)'
    else:
        x = cx + 28.0
        r = 3.0
        que = 'puerto RS-485 estanco (el cable 0,32 mm2 A/B/GND/VCC sale del conector)'
    como = ('EPEVER Tracer7810BP: no tiene bornes, es IP67/IP68 con cables propios (PV, bateria, carga) y un puerto '
            'RS-485 estanco, todos en el mismo extremo corto de la caja (manual Tracer-BP, foto Tracer52**BP: LEDs, '
            '6 cables y RS-485 a la derecha). El dibujo de la pag 8 es solo el cuerpo (153 mm vertical, agujeros de '
            'fijacion a 120 x 94 mm). Se toma la salida por ABAJO (12XPS esta justo debajo y todos sus cables van a '
            '12XPS :1 ARRIBA). %s: punto sobre el borde inferior de la caja (y %.1f); la x es una estimacion del orden '
            'PV, bateria, carga (+ a la izquierda) y NO esta dibujada: A CONFIRMAR con el aparato.' % (que, y0))
    return dict(x=x, y=y0, r=r, lado='ABAJO', texto='12PS1 %s' % borne, confianza='media', como=como)


def resolver(tag, borne, punto):
    if tag in ('15XR', '81XCM', '32XEX', '41XEX', '42XC'):
        if tag == '42XC' and borne in ('F1', '1') and punto is None:
            return pttb_42xc(borne)
        lab = str(borne)
        if (tag, lab) in GEO and 'QUATTRO-PE' in GEO[(tag, lab)]['pieza']['tipo']:
            return quattro_pe(tag, borne, punto)
        return ptt(tag, borne, punto)
    if tag == '12XPS':
        if punto is None:
            return pt6(tag, borne, 2, nota_punto=(
                'EPLAN escribe -12XPS:%s sin punto. El punto :1 (ARRIBA) lo ocupa el RS-485 de 12PS1 y en la hoja 81 '
                'la union en T del cable sale del lado derecho del borne (= ABAJO, regla horizontal): las dos puntas '
                'del cable van juntas en la boca de ABAJO, con TERMINAL DOBLE.' % borne))
        return pt6(tag, borne, punto)
    if tag == '11XPVAC':
        if str(borne) == '3':
            return quattro_pe(tag, borne, punto)
        return pt6(tag, borne, punto)
    if tag == '11X220V':
        return quattro_pt6(tag, borne, punto)
    if tag in ('11Q1', '11Q2'):
        return proteccion(tag, borne)
    if tag == '11SK1':
        return toma(borne)
    if tag == '12PS1':
        return regulador(borne)
    raise KeyError(tag)


# ------------------------------------------------------------------------------------------------ puntas
def etiqueta_cable(r):
    if r['num']:
        return r['num']
    tipo = r.get('tipo_sin_numero')
    if tipo == 'campo':
        return 'sin numero campo'
    col = r.get('color_norm') or r.get('color') or ''
    sec = r.get('seccion_mm2')
    s = 'sin numero %s' % col
    if sec:
        s += ' %s' % (('%g' % sec).replace('.', ','))
    return s.strip()


def zona_de(tag, rr, lado):
    z = rr.get(lado + '_zona')
    return z


def otro_texto(r, s):
    o = 'd2' if s == 'd1' else 'd1'
    d = r[o]
    if d is None:
        return '(sin otro extremo en la lista)'
    if r.get(o + '_propuesto'):
        d += ' (pin propuesto %s)' % r[o + '_propuesto']
    return d


def estacion_otro(r, s):
    o = 'd2' if s == 'd1' else 'd1'
    tag = r.get(o + '_tag') or ''
    z = r.get(o + '_zona')
    if r[o] is None:
        return None
    if z == 'campo' or (r[o] or '').startswith('+Campo'):
        return 'campo'
    if tag in ('12F2', 'BH_01_ZV', 'BH-01-M', 'PT001', 'LS001A', 'X1'):
        return 'E8'
    if tag in ('12PB1',):
        return 'gabinete (bateria en el piso del gabinete, fuera de la bandeja)'
    if z == 'fuera_topografico':
        return 'fuera de las bandejas (puerta / gabinete)'
    return z


def main():
    geo_borneras()
    puntos = OrderedDict()
    for r in C['conexiones']:
        for s in ('d1', 'd2'):
            tag = r.get(s + '_tag')
            if tag not in ZONA:
                continue
            d = r[s]
            borne = r.get(s + '_borne')
            punto = r.get(s + '_punto')
            cab = etiqueta_cable(r)
            key = (d, cab)
            if key in puntos:
                P = puntos[key]
                P['otro_extremo'].append(otro_texto(r, s))
                P['filas_lista'].append(r['fila'])
                P['tramos'] += 1
                continue
            res = resolver(tag, borne, punto)
            P = OrderedDict()
            P['d'] = d
            P['cables'] = [cab]
            P['tag'] = tag
            P['texto_taller'] = res['texto']
            P['x'] = f2(res['x'])
            P['y'] = f2(res['y'])
            P['r'] = f2(res['r'])
            P['lado'] = res['lado']
            P['confianza'] = res['confianza']
            P['como'] = res['como']
            P['zona'] = 'bandeja principal, riel 3' if tag in AP_P else 'bandeja lateral izquierda'
            P['color'] = r.get('color_norm') or r.get('color')
            P['seccion_mm2'] = r.get('seccion_mm2')
            P['otro_extremo'] = [otro_texto(r, s)]
            P['otro_extremo_donde'] = estacion_otro(r, s)
            P['filas_lista'] = [r['fila']]
            P['tramos'] = 1
            if r.get('tipo_sin_numero'):
                P['tipo_sin_numero'] = r['tipo_sin_numero']
            puntos[key] = P
    tres = set(C['_meta'].get('cables_3_o_mas_puntas', []))
    for P in puntos.values():
        num = P['cables'][0]
        if num in tres and P['tramos'] == 1:
            pts = C['cables'][num]['puntas']
            P['como'] += (' Cable %s de %d puntas (%s); en este borne entra un solo conductor (la union esta en otro borne).'
                          % (num, len(pts), ', '.join(pts)))
        if P['tramos'] > 1:
            P['como'] += (' Cable de %d puntas: en este borne entran %d tramos con el mismo numero (%s): TERMINAL DOBLE.'
                          % (P['tramos'] + 1, P['tramos'], ', '.join(P['otro_extremo'])))
    # comprobacion: dos cables distintos en la misma boca
    usados = {}
    for P in puntos.values():
        k = (P['x'], P['y'])
        usados.setdefault(k, []).append(P['d'] + ' #' + P['cables'][0])
    compartidas = {('%.2f, %.2f' % k): v for k, v in usados.items() if len(v) > 1}

    extra = []
    # conexiones dibujadas en el esquema que no estan en la lista (las cablea el taller)
    q = quattro_pe('11XPVAC', '3', 1)
    extra.append(OrderedDict(d='-11XPVAC:3:1', cables=['sin numero Verde/amarillo 2,5 (no esta en la lista)'], tag='11XPVAC',
                             texto_taller='11XPVAC 3.1', x=f2(q['x']), y=f2(q['y']), r=f2(q['r']), lado='ARRIBA',
                             confianza='media', como='Hoja 11: tierra 2,5 mm2 V/A de TIERRA GABINETE CONEXION INTERIOR al punto de la '
                             'izquierda del borne PE 11XPVAC 3 (= punto 1 = ARRIBA extremo por la regla horizontal). No figura en la '
                             'lista de conexiones; el otro extremo es el perno de tierra del gabinete (E8/LI). ' + q['como']))
    for borne, punto, x in (('7', 3, 'x1'), ('8', 4, 'x2')):
        q = ptt('81XCM', borne, punto)
        extra.append(OrderedDict(d='-81XCM:%s:%d' % (borne, punto), cables=['R1 120 ohm pata %s (no esta en la lista)' % x],
                                 tag='81XCM', texto_taller='81XCM %s ABAJO' % borne, x=f2(q['x']), y=f2(q['y']), r=f2(q['r']),
                                 lado='ABAJO', confianza='media', como='Hoja 81: resistencia de fin de linea R1 120R entre 81XCM 7 y 8 del lado '
                                 'derecho del simbolo (campo = ABAJO). No esta en la lista de conexiones ni en la de articulos. ' + q['como']))

    dudas = [
        'PTT 2,5-2MT (15XR, 42XC 3-6, 81XCM, 32XEX, 41XEX): el piso sale de la convencion del taller (borne impar = piso de abajo = boca del EXTREMO; par = piso de arriba = boca INTERIOR), verificada con fotos en el 75286 y el 66817 para el mismo articulo Phoenix. EPLAN numera las bocas de la pieza de forma que el impar usa :2/:3 y el par :1/:4; si esa numeracion fuera correlativa a lo largo de la pieza (1 ext, 2 int, 3 int, 4 ext), el impar quedaria en las bocas INTERIORES. Lo importante es que las dos puntas de un mismo numero queden en el mismo piso: con la convencion del taller quedan. Confirmar en el primer tablero.',
        'El lado ARRIBA/ABAJO de los PTT sale del dibujo de cada esquema (regla del taller): en 15XR y 81XCM los puntos :1/:2 estan dibujados arriba (o a la izquierda) y en 32XEX, 41XEX y 42XC los :3/:4. En todos, los cables del tablero quedan ARRIBA y los de campo (ROTORK, PIT01F, IP_x, PS1, R1) ABAJO, que es lo logico (campo entra por la canaleta de abajo U8/U9).',
        '41XEX: las piezas 4 y 5 estan cambiadas (la 4ta lleva 9-10 y la 5ta 7-8) en la hoja de hileras (pag 38) y en la pag 8. Se mapeo respetando el numero: 4122/4123 (41XEX 7/8) en la 5ta pieza y 4124/4125 (41XEX 9/10) en la 4ta. Si el taller las arma en orden 1..12, hay que mover esos 4 puntos (y los de campo) una pieza. Conviene avisar al proyectista.',
        '12XPS 10 y 11: EPLAN no da el punto para 2135 y 2136 (-12XPS:10 / -12XPS:11). Se pusieron en la boca de ABAJO (:2), con los dos tramos de cada cable (a 21PCB01 y a 81XCM) en la misma boca con TERMINAL DOBLE de 0,32 mm2 (seccion de terminal doble sin definir en terminales.json). El ARRIBA lo ocupa el RS-485 de 12PS1 (A, B).',
        '12PS1 (EPEVER Tracer7810BP) no tiene bornes: los cables 1221-1226 (6 mm2 = 10 AWG) son los cables propios del regulador y el RS-485 sale de un conector estanco. Los puntos estan sobre el borde inferior de la caja con una x ESTIMADA (orden PV, bateria, carga y RS-485 a la derecha, de la foto del manual). Confirmar de que lado salen los cables en el aparato montado y si el taller les pone la manga con el numero.',
        '12PS1 RS-485: los 4 hilos A/B/GND/VCC (0,32 mm2, sin numero) salen del mismo conector: los 4 puntos coinciden.',
        '11SK1 (Phoenix EO-I/UT): los 3 tornillos estan abajo y se ven en el dibujo, pero el orden L / PE / N de izquierda a derecha es supuesto (el de la macro EPLAN); la ficha Phoenix no muestra la vista de bornes. Confianza media.',
        '11Q1: el esquema (hoja 11) dibuja la fase (1/2) a la izquierda y el neutro (N/N\') a la derecha, pero el aparato (Easy9 EZ9R36225 o Acti9 iID; la lista dice EZ9F36225) tiene el NEUTRO a la IZQUIERDA. Se mapeo el lado fisico: 1155/1157 (celeste) en el polo izquierdo y 1154/1156 (marron) en el derecho. 1156 y 1157 se cruzan entre 11Q1 y 11Q2 (11Q2 tiene la fase a la izquierda).',
        '11XPVAC 1 y 2 (PT 6): la macro dibuja la boca como un octogono irregular recortado por el borde de la pieza; el centro (envolvente) queda unos 0,1-0,4 pt corrido a la derecha del eje de la pieza. Dentro de la tolerancia.',
        'Conexiones de mi zona que estan en el esquema y no en la lista (van en "extra_esquema"): tierra 2,5 mm2 V/A del perno del gabinete a 11XPVAC 3 (punto 1, hoja 11) y la resistencia R1 120R en 81XCM 7 y 8 ABAJO (hoja 81). Ademas, del lado de campo (ABAJO) quedan sin fila: 42XC F1/1/3/4 al presostato PS1 (hoja 42) y 81XCM 7/8/9 al ROTORK 27/28/malla (hoja 81); en 81XCM 7 ABAJO y 8 ABAJO entrarian R1 y el cable de campo juntos.',
        'Mallas: 81XCM 3 y 4 ARRIBA reciben las 2 mallas "2134" que van a 21PCB01:34 (sin numero en la lista); 81XCM 9 ARRIBA la malla "2137" (la lista la da como Verde/amarillo sin origen; el esquema dice Apantallamiento hacia 21PCB01:37). 32XEX 5.4 es la malla SH del cable de campo de PIT01F.',
        'Cables de campo (ROTORK, PIT01F, IP_x) y la tierra del ROTORK (15XR 3.4) estan mapeados en la boca de ABAJO correspondiente, pero no se cablean en E6.',
        '15XR 3.4 y 32XEX 5.4 (PT 2,5-QUATTRO-PE): el simbolo del esquema esta espejado (el 4 dibujado a la izquierda); como los 4 puntos son PE y el cable es de campo se dejo 4 = ABAJO extremo.',
    ]
    if compartidas:
        dudas.append('Bocas con mas de un punto de la lista: ' + json.dumps(compartidas, ensure_ascii=False))

    out = OrderedDict()
    out['descripcion'] = ('Puntos de conexion del 76884 (ZPL-76884 Rev 1, mSafe2+ PAE, EPLAN): riel 3 de la bandeja principal '
                          '(15XR, 42XC, 81XCM, 32XEX, 41XEX) y bandeja lateral izquierda (12PS1, 12XPS, 11SK1, 11Q1, 11Q2, '
                          '11XPVAC, 11X220V). x, y = centro de la boca push-in o del tornillo en pt de la pagina PDF 8 '
                          '(origen abajo-izq); r = radio de la boca. Un punto por (designacion EPLAN, cable). lado = lado '
                          'fisico respecto del riel. Fuente de las puntas: conexiones.json (lista de conexiones pags 47-50).')
    out['pagina_pdf'] = 8
    out['escala_mm_por_pt'] = B['escala_mm_por_pt']
    out['puntos'] = list(puntos.values())
    out['extra_esquema'] = extra
    out['dudas'] = dudas
    json.dump(out, open(os.path.join(MAP, 'puntos_riel3_lateral.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('puntos', len(out['puntos']), 'extra', len(extra))
    return out


if __name__ == '__main__':
    main()
