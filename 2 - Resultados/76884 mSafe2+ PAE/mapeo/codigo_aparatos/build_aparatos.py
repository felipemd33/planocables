# -*- coding: utf-8 -*-
"""Arma aparatos.json del 76884 (mSafe2+ PAE, EPLAN) a partir de:
 - lista_art_raw.json  (paginas 40-46, lista de articulos, extraida por celdas)
 - conex_raw.json      (paginas 47-50, lista de conexiones)
 - lo leido a mano en los planos de hileras (32-39), la bandeja (pag 8) y los esquemas (10-21)
"""
import json, re, collections, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r"C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo/aparatos.json"

lista = json.load(open(os.path.join(HERE, 'lista_art_raw.json'), encoding='utf-8'))
conex = json.load(open(os.path.join(HERE, 'conex_raw.json'), encoding='utf-8'))

# ---------------------------------------------------------------- lista de articulos
def parts(s):
    return [p.strip() for p in s.split('|') if p.strip()]

def sap_de(fab_parts, tipo_parts):
    for i, p in enumerate(fab_parts):
        if re.match(r'^AB\d{3}$', p) and i + 1 < len(fab_parts) and re.match(r'^\d+$', fab_parts[i + 1]):
            return p + fab_parts[i + 1]
    for p in tipo_parts[1:]:
        if p.startswith('AB'):
            return p
    return None

FABS = ['Phoenix Contact', 'Schneider Electric', 'CHENZHU', 'MEAN WELL', 'DIGITO', 'Vibo', 'Trombetta',
        'Littelfuse', 'OMRON Corporation', 'XKC', 'ODYSSEY', 'EPEVER', 'ifm electronic']

renglones = []
for r in lista:
    tp = parts(r['tag'])
    tag = tp[0].lstrip('-')
    coloc = ' '.join(tp[1:])
    tipo_p = parts(r['tipo'])
    fab_p = parts(r['fab'])
    fab_txt = ' '.join(fab_p)
    fab = None
    for f in FABS:
        if f.replace(' ', '') in fab_txt.replace(' ', ''):
            fab = f
            break
    art_p = parts(r['art'])
    art_p = [a for a in art_p if a not in ('g', 'gg')]
    numero_tipo = tipo_p[0] if tipo_p else None
    if r['pos'] in ('56', '57', '58'):           # el tipo ocupa dos renglones
        numero_tipo = 'VALV.SOLENOIDE 3/2 NC POPPET 30W 12VDC'
    pedido = tipo_p[1] if len(tipo_p) > 1 and r['pos'] not in ('56', '57', '58') else None
    if numero_tipo and numero_tipo.startswith('PSR-SCP-'):
        numero_tipo = 'PSR-SCP-24UC/ESA2/4X1/1X2/B'
    texto_funcion = art_p[1] if len(art_p) > 1 and art_p[1] != '=' else None
    renglones.append({
        'pos': int(r['pos']), 'pagina_pdf': r['page'], 'tag': tag, 'colocacion': coloc,
        'cantidad': int(r['cant']) if r['cant'].isdigit() else r['cant'],
        'designacion': r['desig'].replace(' | ', ' / '),
        'numero_tipo': numero_tipo, 'numero_pedido': pedido,
        'fabricante': fab, 'numero_articulo': art_p[0] if art_p else None,
        'texto_funcion': texto_funcion, 'codigo_sap': sap_de(fab_p, tipo_p)})
# arreglos puntuales de la lectura por celdas
for rr in renglones:
    if rr['pos'] == 106:
        rr['colocacion'] = '(mSafe.S1); &CLIENTE/12.7B'
    if rr['pos'] == 26:
        rr['codigo_sap'] = None
        rr['numero_pedido'] = 'DF141'

por_tag = collections.OrderedDict()
for rr in renglones:
    por_tag.setdefault(rr['tag'], []).append(rr)

# ---------------------------------------------------------------- lista de conexiones
def limpiar(s):
    s = s.strip()
    s = re.sub(r'\s+A$', '', s)          # 'A' de 'Apantallamiento' que se cuela en la celda
    return s

conexiones = []
for r in conex:
    num = ''.join(r['num']).strip()
    d1 = limpiar(''.join(r['d1']))
    d2 = limpiar(''.join(r['d2']))
    color = ' '.join(r['color']).strip()
    sec = ''.join(r['sec']).strip()
    conexiones.append({'cable': num or None, 'd1': d1, 'd2': d2, 'color': color or None,
                       'seccion': sec or None, 'pagina_pdf': r['page']})

# designaciones que la lista de conexiones deja sin punto y que salen del esquema
INFERIDO = {
    ('2114', '-42KS1'): '-42KS1:13', ('2115', '-42KS1'): '-42KS1:14',
    ('1394', '-42KS1'): '-42KS1:23', ('4294', '-42KS1'): '-42KS1:24',
    ('1395', '-42KS1'): '-42KS1:33', ('4295', '-42KS1'): '-42KS1:34',
    ('1396', '-42KS1'): '-42KS1:43', ('4296', '-42KS1'): '-42KS1:44',
    ('2135', '-12XPS:10'): '-12XPS:10:2', ('2136', '-12XPS:11'): '-12XPS:11:2',
    ('1101', '-11MS1'): '-11MS1:1/L1', ('1154', '-11MS1'): '-11MS1:2/T1',
    ('1102', '-11MS1'): '-11MS1:3/L2', ('1155', '-11MS1'): '-11MS1:4/T2',
}
usos = collections.defaultdict(lambda: collections.defaultdict(list))
for c in conexiones:
    for a, b in (('d1', 'd2'), ('d2', 'd1')):
        s = c[a]
        if not s.startswith('-'):
            continue
        s2 = INFERIDO.get((c['cable'] or '', s), s)
        inferido = s2 != s
        m = re.match(r'^-([^:]+)(?::(.*))?$', s2)
        tag, pt = m.group(1), m.group(2) or ''
        if c[a] == c[b]:
            continue                          # -61KR1 -> -61KR1 (conexion interna rele/base)
        usos[tag][pt].append({'cable': c['cable'] or '(sin numero)', 'otro_extremo': c[b].lstrip('-') or '(sin destino en la lista)',
                              'color': c['color'], 'seccion': c['seccion'],
                              **({'designacion_inferida_del_esquema': True} if inferido else {})})

# ---------------------------------------------------------------- metadatos por tag
U_LAT = 'bandeja lateral izquierda (LI para el instructivo de E6)'
U_P1 = 'bandeja principal, riel 1'
U_P2 = 'bandeja principal, riel 2'
U_P3 = 'bandeja principal, riel 3'
META = {
 '11PS1': ('fuente', U_P1, 'Fuente 24 VDC General (alimenta regulador 12PS1 via 11F1)', '11'),
 '11PS2': ('fuente', U_P1, 'Fuente 24 VDC Rotork (via 11F2 a 15XR)', '11'),
 '13PS1': ('fuente', U_P1, 'Elevador DC/DC 12 -> 24 VDC principal', '13'),
 '12PS1': ('fuente', U_LAT, 'Regulador de carga MPPT / cargador de bateria (panel, bateria, carga y RS-485)', '12, 81'),
 '11F1': ('proteccion', U_P1, 'Portafusible 10x38 gG 10 A: proteccion alimentacion regulador', '11'),
 '11F2': ('proteccion', U_P1, 'Portafusible 10x38 gG 10 A: proteccion ROTORK', '11'),
 '12F3': ('proteccion', U_P1, 'Portafusible 14x51 aM 32 A: proteccion carga de baterias', '12'),
 '13F4': ('proteccion', U_P1, 'Portafusible 10x38 gG 10 A: proteccion cargas principales 12 V', '13'),
 '13F5': ('proteccion', U_P1, 'Portafusible 10x38 gG 10 A: proteccion solenoides 12 V', '13'),
 '13F6': ('proteccion', U_P1, 'Portafusible 10x38 gG 6 A: proteccion cargas 24 VDC', '13'),
 '12F2': ('proteccion', 'bandeja principal, arriba a la derecha (fuera de riel)', 'Portafusible MEGA + fusible MEGA 150 A: proteccion motor unidad hidraulica', '12'),
 '11Q1': ('proteccion', U_LAT, 'Diferencial 2P 25 A 30 mA (110/220 V)', '11'),
 '11Q2': ('proteccion', U_LAT, 'Termomagnetica 2P 10 A (110/220 V)', '11'),
 '11MS1': ('proteccion', 'fuera de las bandejas: seccionador con manija (gabinete) -> LI', 'Llave de corte alimentacion / carga bateria (TeSys VARIO VBF1)', '11'),
 '13MS1': ('proteccion', 'fuera de las bandejas: seccionador con manija (gabinete) -> LI', 'Llave de corte encendido / apagado 12 V (TeSys VARIO VBF1)', '13'),
 '42KR': ('otro', U_P1, 'Tope E/NS 35 N del grupo de reles 42KR', '42'),
 '42KR1': ('rele', U_P1, 'Rele de interfaz 24 VDC (permisivo / seguridad)', '42'),
 '61KR': ('otro', U_P1, 'Tope E/NS 35 N del grupo de reles 61KR', '61'),
 '61KR1': ('rele', U_P1, 'Rele 12 VDC: motor (accionamiento contactor BH_01_ZV)', '61'),
 '61KR2': ('rele', U_P1, 'Rele 12 VDC: valvula 1 (SP_1)', '61'),
 '61KR3': ('rele', U_P1, 'Rele 12 VDC: valvula 2 (SP_2)', '61'),
 '61KR4': ('rele', U_P1, 'Rele 12 VDC: valvula 3 (SP_3)', '61'),
 '42KS1': ('rele', U_P1, 'Rele de seguridad (parada de emergencia 42DB1, 4 NA + 1 NC)', '42'),
 '15AIB1': ('barrera', 'bandeja principal, riel 2 (a la derecha de la canaleta azul)', 'Barrera IS 2 entradas analogicas', '15, 32'),
 '15DIB1': ('barrera', 'bandeja principal, riel 2 (a la derecha de la canaleta azul)', 'Barrera IS 2 entradas digitales (valvula 1)', '15, 41'),
 '15DIB2': ('barrera', 'bandeja principal, riel 2 (a la derecha de la canaleta azul)', 'Barrera IS 2 entradas digitales (valvula 2)', '15, 41'),
 '15DIB3': ('barrera', 'bandeja principal, riel 2 (a la derecha de la canaleta azul)', 'Barrera IS 2 entradas digitales (valvula 3). Hoja 41: "SE DEJA PREVISTO EL CABLEADO SIN LA BARRERA, SE REEMPLAZA POR BORNES TIPO CUCHILLA ABIERTOS"', '15, 41'),
 '11SK1': ('toma', U_LAT, 'Tomacorriente de servicio 250 V 16 A (tipo I, riel DIN)', '11'),
 '21PCB01': ('otro', 'puerta (interior de puerta, pag 31) -> LI', 'Placa electronica de control E2.5 (DI/DO/AI, RS-485)', '16, 21'),
 '12PB1': ('otro', 'gabinete (base), fuera de las bandejas -> E8', 'Bateria de potencia 12 V 68 Ah', '12'),
 'BH-01-M': ('otro', 'bandeja principal, unidad hidraulica (derecha)', 'Motor de la unidad hidraulica 12 VDC 1,6 kW', '12'),
 'M1': ('otro', 'bandeja principal, unidad hidraulica (derecha)', 'Unidad hidraulica (renglon de articulo, sin conexiones)', '-'),
 'BH_01_ZV': ('otro', 'bandeja principal, unidad hidraulica (derecha)', 'Contactor de potencia 12 VDC del motor de la bomba (250 A)', '12, 61'),
 'PT001': ('aparato de campo', 'bandeja principal, unidad hidraulica (transmisor sobre el bloque)', 'Transmisor de presion 4-20 mA actuador interno (conector DIN)', '32'),
 'LS001A': ('aparato de campo', 'tanque de la unidad hidraulica', 'Sensor de nivel de aceite capacitivo (via conector X1)', '42'),
 'SP_1': ('aparato de campo', 'unidad hidraulica', 'Solenoide valvula 1 (conector DIN x1/x2)', '61'),
 'SP_2': ('aparato de campo', 'unidad hidraulica', 'Solenoide valvula 2 (conector DIN x1/x2)', '61'),
 'SP_3': ('aparato de campo', 'unidad hidraulica', 'Solenoide valvula 3. Hoja 61: "SE DEJA PREVISTO EL CABLEADO CON EL CONECTOR DIN SIN LA SOLENOIDE"', '61'),
 '42DB1': ('otro', 'puerta -> LI', 'Pulsador de parada de emergencia (seta) + contacto ZBE102', '42'),
 '42DS': ('aparato de campo', 'gabinete (puerta) -> LI', 'Sensor de puerta (final de carrera 1NA/1NC)', '42'),
 '12': ('otro', 'puerta', 'Tapon ciego para orificio de 22 mm', '-'),
}
for t in ['11X220V', '11XPVAC', '12XPS']:
    META[t] = ('bornera', U_LAT, None, None)
for t in ['32XAI', 'XPE']:
    META[t] = ('bornera', U_P1, None, None)
for t in ['12XP', '13X12V', '13X24V', '61XDO', '61X0V', '61XDIO']:
    META[t] = ('bornera', U_P2, None, None)
for t in ['15XR', '42XC', '81XCM', '32XEX', '41XEX']:
    META[t] = ('bornera', U_P3, None, None)
FUNC_BORNERA = {
 '11X220V': 'Distribucion 110/220 VAC (L = borne 1, N = borne 2)', '11XPVAC': 'Entrada de alimentacion 110/220 VAC desde campo (1 = fase, 2 = neutro, 3 = PE)',
 '12XPS': 'Bornera del regulador 12PS1 (panel, bateria, carga 12 V y RS-485)', '12XP': '0 V / negativo comun 12 V',
 '13X12V': 'Distribucion +12 V (1: general, 2: solenoides)', '13X24V': 'Distribucion 24 VDC (+ en 1-2, - en 3-4)',
 '61XDO': 'Salidas digitales a contactor y solenoides (+)', '61X0V': '0 V de accionamientos (solenoides)', '61XDIO': 'Diodos de rueda libre de las bobinas (anodos comunes a 0 V)',
 '15XR': 'Alimentacion ROTORK (campo) + PE', '42XC': 'Presostato de seguridad PS1 (campo) y permisivo externo', '81XCM': 'Comunicacion RS-485 (campo), resistencia de fin de linea R1 en 7-8',
 '32XEX': 'Entradas analogicas IS (campo PIT01F, reserva) + PE de malla', '41XEX': 'Entradas digitales IS (sensores de posicion de valvulas, campo)',
 '32XAI': 'Borne fusible 100 mA del transmisor PT001', 'XPE': 'Tierra (PE) de fuentes y elevador'}

TOPES = {'31', '22', '24', '28', '29', '30'}

def familia_de(tag):
    if tag in META:
        return META[tag][0]
    if tag in TOPES:
        return 'otro'
    return 'otro'

aparatos = collections.OrderedDict()
for tag, rs in por_tag.items():
    fam = familia_de(tag)
    meta = META.get(tag)
    principal = rs[0]
    # renglon principal: el aparato (no el cartucho ni accesorios)
    if tag in ('11F1', '11F2', '13F4', '13F5', '13F6', '12F3', '12F2', '42DB1'):
        principal = rs[0]
    if fam == 'bornera':
        # el renglon principal es el borne (no el tope)
        bornes = [x for x in rs if x['numero_tipo'] and not x['numero_tipo'].startswith(('E/NS', 'D-', 'FBS'))]
        principal = bornes[0] if bornes else rs[0]
    a = collections.OrderedDict()
    a['fabricante'] = principal['fabricante']
    a['numero_tipo'] = principal['numero_tipo']
    a['numero_articulo'] = principal['numero_articulo']
    a['codigo_sap'] = principal['codigo_sap']
    a['descripcion'] = principal['designacion']
    a['funcion'] = (meta[2] if meta and meta[2] else None) or FUNC_BORNERA.get(tag) or principal['texto_funcion'] or principal['designacion']
    a['cantidad'] = principal['cantidad'] if fam != 'bornera' else sum(x['cantidad'] for x in bornes) if bornes else principal['cantidad']
    a['familia'] = fam
    a['ubicacion'] = meta[1] if meta else ('tope de riel (colocacion mSafe.S1)' if tag in TOPES else None)
    a['hojas_esquema'] = meta[3] if meta and meta[3] else None
    a['colocacion_eplan'] = sorted(set(x['colocacion'] for x in rs))
    if len(rs) > 1:
        a['componentes'] = [{k: x[k] for k in ('pos', 'numero_tipo', 'numero_articulo', 'codigo_sap', 'numero_pedido', 'fabricante', 'designacion', 'cantidad', 'colocacion')} for x in rs]
    else:
        a['pos_lista'] = rs[0]['pos']
        if rs[0]['numero_pedido'] and rs[0]['numero_pedido'] != rs[0]['codigo_sap']:
            a['numero_pedido'] = rs[0]['numero_pedido']
    if tag in TOPES:
        a['cantidad'] = sum(x['cantidad'] for x in rs)
        a['nota'] = 'Tag de colocacion (mSafe.S1) de un tope E/NS 35 N; no tiene conexiones.'
    aparatos[tag] = a

# aparatos que aparecen en las conexiones y no en la lista
aparatos['X1'] = collections.OrderedDict([('fabricante', None), ('numero_tipo', None), ('numero_articulo', None), ('codigo_sap', None),
    ('descripcion', 'Conector del sensor de nivel LS001A (hoja 42: cuadraditos de conector en los 4 hilos del sensor)'),
    ('funcion', 'Union entre el cableado del tablero (X1:1, cables 1339, 1340, 2166, 2167) y los hilos del sensor LS001A (X1:2)'),
    ('cantidad', 1), ('familia', 'otro'), ('ubicacion', 'junto al sensor LS001A (campo / unidad hidraulica)'), ('hojas_esquema', '42'),
    ('nota', 'No figura en la lista de articulos. La lista de conexiones no trae el numero de pin (todos dicen -X1:1 o -X1:2).')])
aparatos['R1'] = collections.OrderedDict([('fabricante', None), ('numero_tipo', 'Resistencia 120 ohm'), ('numero_articulo', None), ('codigo_sap', None),
    ('descripcion', 'Resistencia de fin de linea RS-485 120 R (x1/x2)'),
    ('funcion', 'Hoja 81: va en 81XCM 7 y 8 del lado de campo (puntos 7:3 y 8:4). Nota 1: dejarla si no se usa la comunicacion con otros equipos.'),
    ('cantidad', 1), ('familia', 'otro'), ('ubicacion', U_P3 + ' (sobre 81XCM)'), ('hojas_esquema', '81'),
    ('nota', 'No figura en la lista de articulos ni en la lista de conexiones (es un componente, no un cable).')])

# designaciones usadas
for tag in list(aparatos.keys()):
    if tag in usos:
        aparatos[tag]['conexiones_eplan'] = {pt or '(sin designacion)': v for pt, v in sorted(usos[tag].items(), key=lambda kv: [(0, int(x), '') if x.isdigit() else (1, 0, x) for x in re.split(r'[:/]', kv[0])] if kv[0] else [(-1, 0, '')])}

# ---------------------------------------------------------------- borneras (planos de hileras 32-39 + bandeja pag 8)
TOPE = ('tope', 'E/NS 35 N', 'PXC.0800886')
def P(tipo, art, num=None, puntos=None, puentes=None, x=None, extra=None):
    d = collections.OrderedDict([('tipo', tipo), ('articulo', art), ('numero_borne', num), ('puntos', puntos or [])])
    if puentes:
        d['puentes'] = puentes
    if x is not None:
        d['x_etiqueta_pag8'] = x
    if extra:
        d.update(extra)
    return d
def tope():
    return P('E/NS 35 N (tope)', 'PXC.0800886')
def tapa(t, a):
    return P(t + ' (tapa)', a)
Q = lambda n: [f'{n}:1', f'{n}:2', f'{n}:3', f'{n}:4']
D2 = lambda n: [f'{n}:1', f'{n}:2']
def PTT(nimp, x, bu=False, lado='bandeja_abajo'):
    npar = nimp + 1
    tipo = 'PTT 2,5-2MT BU' if bu else 'PTT 2,5-2MT'
    art = 'PXC.3210265' if bu else 'PXC.3210258'
    return P(tipo, art, [str(nimp), str(npar)], [f'{nimp}:2', f'{nimp}:3', f'{npar}:1', f'{npar}:4'], x=x,
             extra={'niveles': {str(nimp): f'puntos {nimp}:2 y {nimp}:3', str(npar): f'puntos {npar}:1 y {npar}:4'},
                    'orientacion_esquema': lado})
def FBS(t, a, une, color):
    return {'tipo': t, 'articulo': a, 'color': color, 'une_bornes': une}

B = collections.OrderedDict()
B['11X220V'] = {'hoja_hileras_pdf': 32, 'ubicacion': U_LAT, 'piezas': [tope(),
    P('PT 6-QUATTRO', 'PXC.3212934', '1', Q(1), x=377.66), P('PT 6-QUATTRO', 'PXC.3212934', '2', Q(2), x=383.39),
    tapa('D-PT 6-QUATTRO', 'PXC.3212963'), tope()]}
B['11XPVAC'] = {'hoja_hileras_pdf': 32, 'ubicacion': U_LAT, 'piezas': [tope(),
    P('PT 6', 'PXC.3211813', '1', D2(1), x=352.61), P('PT 6', 'PXC.3211813', '2', D2(2), x=358.35),
    tapa('D-PT 6', 'PXC.3212044'),
    P('PT 2,5-QUATTRO-PE', 'PXC.3209594', '3', Q(3), x=365.63, extra={'es_pe': True, 'nota': 'Borne de tierra con numero de funcional 3 (11XPVAC:3:4 -> 11SK1:PE).'}),
    tapa('D-ST 2,5-QUATTRO GN', 'PXC.3032059')]}
xs12 = [228.95, 234.69, 240.41, 246.2, 252.01, 257.78, 263.56, 269.31, 275.08, 282.22, 287.91, 293.76, 299.51]
pz = [tope()]
for n in range(1, 14):
    pu = [FBS('FBS 2-8', 'PXC.3030284', ['7', '8'], 'rojo')] if n in (7, 8) else None
    pz.append(P('PT 6', 'PXC.3211813', str(n), D2(n), pu, x=xs12[n - 1]))
pz += [tapa('D-PT 6', 'PXC.3212044'), tope()]
B['12XPS'] = {'hoja_hileras_pdf': 33, 'ubicacion': U_LAT, 'piezas': pz,
              'nota': 'En la hoja de hileras el FBS 2-8 figura entre las piezas 7 y 8 (puente 7-8, +12 V de 1230/1232).'}
f12 = FBS('FBS 3-8 BU', 'PXC.3032570', ['1', '2', '3'], 'azul')
B['12XP'] = {'hoja_hileras_pdf': 34, 'ubicacion': U_P2, 'piezas': [tope(),
    P('PT 6-QUATTRO', 'PXC.3212934', '1', Q(1), [f12], x=623.93), P('PT 6-QUATTRO', 'PXC.3212934', '2', Q(2), [f12], x=629.66),
    P('PT 6-QUATTRO', 'PXC.3212934', '3', Q(3), [f12], x=635.40), tapa('D-PT 6-QUATTRO', 'PXC.3212963')]}
B['13X12V'] = {'hoja_hileras_pdf': 34, 'ubicacion': U_P2, 'piezas': [tope(),
    P('PT 6-QUATTRO', 'PXC.3212934', '1', Q(1), x=649.55), P('PT 6-QUATTRO', 'PXC.3212934', '2', Q(2), x=655.28),
    tapa('D-PT 6-QUATTRO', 'PXC.3212963')]}
fa = FBS('FBS 2-8', 'PXC.3030284', ['1', '2'], 'rojo')
fb = FBS('FBS 2-8 BU', 'PXC.3032567', ['3', '4'], 'azul')
B['13X24V'] = {'hoja_hileras_pdf': 34, 'ubicacion': U_P2, 'piezas': [tope(),
    P('PT 6-QUATTRO', 'PXC.3212934', '1', Q(1), [fa], x=669.39), P('PT 6-QUATTRO', 'PXC.3212934', '2', Q(2), [fa], x=675.12),
    tapa('D-PT 6-QUATTRO', 'PXC.3212963'),
    P('PT 6-QUATTRO', 'PXC.3212934', '3', Q(3), [fb], x=682.42), P('PT 6-QUATTRO', 'PXC.3212934', '4', Q(4), [fb], x=688.20),
    tapa('D-PT 6-QUATTRO', 'PXC.3212963')]}
B['61XDO'] = {'hoja_hileras_pdf': 35, 'ubicacion': U_P2, 'piezas': [tope()] +
    [P('PT 6-QUATTRO', 'PXC.3212934', str(n), Q(n), x=x) for n, x in zip(range(1, 5), [702.35, 708.08, 713.81, 719.60])] +
    [tapa('D-PT 6-QUATTRO', 'PXC.3212963')]}
f0 = FBS('FBS 2-8 BU', 'PXC.3032567', ['1', '2'], 'azul')
B['61X0V'] = {'hoja_hileras_pdf': 35, 'ubicacion': U_P2, 'piezas': [tope(),
    P('PT 6-QUATTRO', 'PXC.3212934', '1', Q(1), [f0], x=733.74), P('PT 6-QUATTRO', 'PXC.3212934', '2', Q(2), [f0], x=739.47),
    tapa('D-PT 6-QUATTRO', 'PXC.3212963')]}
fd = FBS('FBS 4-5 BU', 'PXC.3036893', ['1', '2', '3', '4'], 'azul')
B['61XDIO'] = {'hoja_hileras_pdf': 36, 'ubicacion': U_P2, 'piezas': [tope()] +
    [P('PT 2,5-DIO/L-R', 'PXC.3210224', str(n), [str(n)], [fd], x=x,
       extra={'nota': 'EPLAN no le da designacion de punto: los dos extremos se llaman 61XDIO:%d. Anodo = lado del puente FBS; catodo = el otro.' % n})
     for n, x in zip(range(1, 5), [753.58, 757.19, 760.80, 764.46])] +
    [tapa('D-ST 2,5', 'PXC.3030417'), tope()]}
B['15XR'] = {'hoja_hileras_pdf': 37, 'ubicacion': U_P3, 'piezas': [tope(),
    PTT(1, 689.27, lado='bandeja_arriba'), tapa('D-PTT 2,5-2MT-0,8', 'PXC.3210300'),
    P('PT 2,5-QUATTRO-PE', 'PXC.3209594', '3', Q(3), x=693.40, extra={'es_pe': True, 'nota': 'Tierra del ROTORK (15XR:3:4, campo). En la hoja 15 el simbolo esta espejado (el punto 4 dibujado a la izquierda).'}),
    tapa('D-ST 2,5-QUATTRO GN', 'PXC.3032059')]}
B['42XC'] = {'hoja_hileras_pdf': 37, 'ubicacion': U_P3, 'piezas': [tope(),
    P('PTTB 4-HESI (5X20)', 'PXC.3211886', ['F1', '1'], ['F1', '1'], x=706.6,
      extra={'niveles': {'F1': 'nivel con fusible 5x20 100 mA (sin designacion de punto)', '1': 'nivel de paso directo (sin designacion de punto)'},
             'nota': 'Hoja 42: F1 = alimentacion 24 V del presostato PS1 (1391 desde 13X24V:1:1), 1 = retorno (1392 a 13X24V:3:4). Los extremos de campo no tienen numero de cable.'}),
    tapa('D-PTT 2,5-2MT-0,8', 'PXC.3210300'),
    PTT(3, 710.27, lado='bandeja_abajo'), PTT(5, 713.96, lado='bandeja_abajo'),
    tapa('D-PTT 2,5-2MT-0,8', 'PXC.3210300')],
    'nota': 'En la hoja de hileras el borne 4 aparece en un renglon aparte, sin articulo, debajo del 3; en la lista de articulos son 2 PTT 2,5-2MT y en la bandeja se ven 3 piezas (F1, 3, 5).'}
B['81XCM'] = {'hoja_hileras_pdf': 37, 'ubicacion': U_P3, 'piezas': [tope()] +
    [PTT(n, x, lado='bandeja_arriba') for n, x in zip((1, 3, 5, 7, 9), (724.95, 728.51, 732.21, 735.87, 739.46))] +
    [tapa('D-PTT 2,5-2MT-0,8', 'PXC.3210300'), tope()],
    'nota': 'Hoja 81 (dibujo horizontal): izquierda = lado tablero (21PCB01 / 12XPS), derecha = campo y resistencia R1 (7:3 - 8:4). Piezas: 1-2, 3-4 (mallas), 5-6, 7-8, 9-10.'}
B['32XEX'] = {'hoja_hileras_pdf': 38, 'ubicacion': U_P3, 'piezas': [tope(),
    PTT(1, 822.36, bu=True), PTT(3, 825.92, bu=True), tapa('D-PTT 2,5-2MT-0,8', 'PXC.3210300'),
    P('PT 2,5-QUATTRO-PE', 'PXC.3209594', '5', Q(5), x=830.18, extra={'es_pe': True, 'nota': 'PE de la malla del cable de campo PIT01F (32XEX:5:4). En la hoja 32 el simbolo esta espejado (punto 4 a la izquierda).'}),
    tapa('D-ST 2,5-QUATTRO GN', 'PXC.3032059')]}
B['41XEX'] = {'hoja_hileras_pdf': 38, 'ubicacion': U_P3, 'piezas': [tope()] +
    [PTT(n, x, bu=True) for n, x in zip((1, 3, 5, 9, 7, 11), (842.17, 845.73, 849.42, 853.04, 856.73, 861.6))] +
    [tapa('D-PTT 2,5-2MT-0,8', 'PXC.3210300'), tope()],
    'nota': 'ORDEN FISICO 1-2, 3-4, 5-6, 9-10, 7-8, 11-12: las piezas 9-10 y 7-8 estan cambiadas, igual en la hoja de hileras (pag 38) y en la bandeja (etiquetas 1 3 5 9 7 11).'}
B['32XAI'] = {'hoja_hileras_pdf': 39, 'ubicacion': U_P1, 'piezas': [tope(),
    P('PTTB 4-HESI (5X20)', 'PXC.3211886', ['F1', '1'], ['F1', '1'], x=888.9,
      extra={'niveles': {'F1': 'nivel con fusible 5x20 100 mA', '1': 'nivel de paso directo'},
             'nota': 'Hoja 32: F1 = 1350 (desde 13X24V:2:1) arriba y 3221 a PT001:x1 abajo; 1 = 2142 (21PCB01:42) arriba y 3222 a PT001:x2 abajo.'}),
    tapa('D-PTT 2,5-2MT-0,8', 'PXC.3210300')]}
B['XPE'] = {'hoja_hileras_pdf': 39, 'ubicacion': U_P1, 'piezas': [tope()] +
    [P('PT 2,5-QUATTRO-PE', 'PXC.3209594', str(n), Q(n), x=x, extra={'es_pe': True}) for n, x in zip((1, 2, 3), (899.44, 903.05, 906.65))] +
    [tapa('D-ST 2,5-QUATTRO GN', 'PXC.3032059')],
    'nota': 'La hoja de hileras muestra un renglon extra "1" sin articulo antes de la primera pieza (terminal 1 duplicado en EPLAN); fisicamente son 3 piezas (lista de articulos: 3).'}

# orden + lado fisico de cada punto, + conexiones
LADO_Q = {1: 'ARRIBA extremo', 2: 'ARRIBA interior', 3: 'ABAJO interior', 4: 'ABAJO extremo'}
def lado_ptt(n, p, orient):
    impar = int(n) % 2 == 1
    piso = 'extremo' if impar else 'interior'
    if orient == 'bandeja_abajo':      # 41XEX, 42XC, 32XEX: 3/4 arriba (lado barrera / aparato), 1/2 abajo (campo)
        lado = 'ARRIBA' if p in (3, 4) else 'ABAJO'
    else:                              # 15XR, 81XCM: 1/2 arriba (lado tablero), 3/4 abajo (campo)
        lado = 'ARRIBA' if p in (1, 2) else 'ABAJO'
    return f'{lado} {piso}'

for tag, b in B.items():
    for i, pz in enumerate(b['piezas'], 1):
        pz['orden'] = i
        pz.move_to_end('orden', last=False)
        lp = collections.OrderedDict()
        for pt in pz['puntos']:
            if pz['tipo'] in ('PT 6',):
                lp[pt] = 'ARRIBA' if pt.endswith(':1') else 'ABAJO'
            elif pz['tipo'] in ('PT 6-QUATTRO', 'PT 2,5-QUATTRO-PE'):
                lp[pt] = LADO_Q[int(pt.split(':')[1])]
            elif pz['tipo'].startswith('PTT 2,5-2MT'):
                n, p = pt.split(':')
                lp[pt] = lado_ptt(n, int(p), pz['orientacion_esquema'])
            elif pz['tipo'].startswith('PTTB 4-HESI'):
                lp[pt] = ('bocas interiores (piso de arriba, fusible): ARRIBA interior = cable de la bandeja, ABAJO interior = campo' if pt.startswith('F')
                          else 'bocas del extremo (piso de abajo, paso directo): ARRIBA extremo = cable de la bandeja, ABAJO extremo = campo')
            elif pz['tipo'].startswith('PT 2,5-DIO'):
                lp[pt] = 'ARRIBA = catodo (cable a 61XDO); ABAJO = anodo, lado del puente FBS (cable 1264 en la pieza 1)'
        if lp:
            pz['lado_por_punto'] = lp
        cx = collections.OrderedDict()
        for pt in pz['puntos']:
            if pt in usos.get(tag, {}):
                cx[pt] = usos[tag][pt]
        if cx:
            pz['conexiones'] = cx
        if 'orientacion_esquema' in pz:
            o = pz.pop('orientacion_esquema')
            pz['orientacion_en_el_esquema'] = ('puntos 3/4 dibujados ARRIBA (lado barrera/aparato) y 1/2 ABAJO (campo)' if o == 'bandeja_abajo'
                                              else 'puntos 1/2 dibujados ARRIBA o a la IZQUIERDA (lado tablero) y 3/4 ABAJO o a la DERECHA (campo)')

# ---------------------------------------------------------------- puntos EPLAN -> lado fisico, por tipo
PE = collections.OrderedDict()
PE['PT 6'] = {
  'articulo': 'PXC.3211813', 'borneras': ['12XPS', '11XPVAC (1-2)'],
  ':N:1': 'ARRIBA (boca push-in del extremo superior)', ':N:2': 'ABAJO (boca push-in del extremo inferior)',
  'fuente': 'Esquemas EPLAN: en 12XPS (hoja 12, vertical) los cables de 12PS1 entran por arriba y son :1; los de abajo son :2; en la hoja 81 (horizontal) el :1 es el de la izquierda; 11XPVAC:1:1 sale hacia arriba (hoja 11). Regla del taller: vertical arriba = arriba, horizontal izquierda = arriba. La pieza es simetrica (una boca por extremo, hoja de datos Phoenix 3211813), asi que la designacion es la que fija el lado.',
  'confianza': 'alta', 'nota': '2135 y 2136 llegan a "-12XPS:10" / "-12XPS:11" sin punto: por la hoja 81 son el punto 2 (ABAJO), con dos conductores en la misma boca (cables de 3 puntas: 21PCB01 -> 12XPS -> 81XCM).'}
PE['PT 6-QUATTRO'] = {
  'articulo': 'PXC.3212934', 'borneras': ['11X220V', '12XP', '13X12V', '13X24V', '61XDO', '61X0V'],
  ':N:1': 'ARRIBA extremo', ':N:2': 'ARRIBA interior', ':N:3': 'ABAJO interior', ':N:4': 'ABAJO extremo',
  'texto_taller': 'N.p  (ej. -13X24V:2:3 -> "13X24V 2.3")',
  'fuente': 'En todos los QUATTRO de este plano el simbolo EPLAN dibuja los puntos 1, 2, 3, 4 en orden de arriba hacia abajo (11X220V, 12XP, 13X12V, 61XDO verticales) o de izquierda a derecha (13X24V, 61X0V horizontales); comprobado cable por cable contra la lista de conexiones. Coincide con la convencion del taller N.p (1 extremo y 2 interior arriba, 3 interior y 4 extremo abajo). La pieza fisica es simetrica: 4 bocas push-in, 2 por extremo (bandeja pag 8: bocas a y 543/531 arriba y 501/490 abajo en el riel 2).',
  'confianza': 'alta (convencion); la hoja de datos Phoenix no numera las bocas'}
PE['PT 2,5-QUATTRO-PE'] = {
  'articulo': 'PXC.3209594', 'borneras': ['XPE (1-3)', '11XPVAC (3)', '15XR (3)', '32XEX (5)'],
  ':N:1': 'ARRIBA extremo', ':N:2': 'ARRIBA interior', ':N:3': 'ABAJO interior', ':N:4': 'ABAJO extremo',
  'fuente': 'Igual que el QUATTRO: en XPE (hojas 11 y 13) y 11XPVAC:3 (hoja 11) el simbolo horizontal va 1..4 de izquierda a derecha. En 15XR:3 (hoja 15) y 32XEX:5 (hoja 32) el simbolo esta ESPEJADO (el 4 a la izquierda); como los 4 puntos son el mismo potencial (PE) y esos cables son de campo, se deja el lado por numero (4 = ABAJO extremo).',
  'confianza': 'media (los 4 puntos son PE; el lado es convencion)'}
PE['PTT 2,5-2MT'] = {
  'articulo': 'PXC.3210258 (gris) y PXC.3210265 (BU, azul): mismo cuerpo', 'borneras': ['15XR', '42XC (3-6)', '81XCM', '32XEX (1-4)', '41XEX'],
  'estructura': 'Cada pieza tiene 2 bornes (2 pisos, hoja de datos Phoenix: "4 connections, 2 levels, 1st and 2nd level"). EPLAN numera las 4 bocas de la pieza 1..4: el borne IMPAR usa los puntos :2 y :3 y el borne PAR los puntos :1 y :4 (sin excepcion en 15XR, 42XC, 81XCM, 32XEX y 41XEX). Los puntos 1 y 2 estan en un extremo de la pieza y 3 y 4 en el otro (en todas las borneras un extremo del borne va a campo y el otro al tablero).',
  'lado_ARRIBA_ABAJO_por_bornera': {
     '41XEX, 42XC, 32XEX': ':3 y :4 = ARRIBA (lado barreras / reles, cables 41xx, 42xx, 32xx); :1 y :2 = ABAJO (campo)',
     '15XR, 81XCM': ':1 y :2 = ARRIBA (lado tablero: 1171/1172, 21PCB01, 12XPS); :3 y :4 = ABAJO (campo, R1)'},
  'piso_extremo_interior': 'Convencion del taller (75286 y 66817, fotos): borne IMPAR = piso de abajo = bocas del EXTREMO; borne PAR = piso de arriba = bocas INTERIORES.',
  'resultado_41XEX_42XC_32XEX': {':impar:3': 'ARRIBA extremo', ':impar:2': 'ABAJO extremo', ':par:4': 'ARRIBA interior', ':par:1': 'ABAJO interior'},
  'resultado_15XR_81XCM': {':impar:2': 'ARRIBA extremo', ':impar:3': 'ABAJO extremo', ':par:1': 'ARRIBA interior', ':par:4': 'ABAJO interior'},
  'fuente': 'Lista de conexiones (pags 47-50) + esquemas 15, 32, 41, 42 y 81 (orientacion del simbolo) + regla del taller (vertical arriba = arriba, horizontal izquierda = arriba) + convencion impar = extremo del 75286/66817. Hoja de datos Phoenix 3210258: no numera las bocas.',
  'confianza': 'media: el lado ARRIBA/ABAJO sale del esquema; el piso (extremo/interior) es convencion del taller y la numeracion EPLAN sugiere lo contrario (ver dudas)'}
PE['PTTB 4-HESI (5X20)'] = {
  'articulo': 'PXC.3211886', 'borneras': ['32XAI', '42XC (F1/1)'],
  'F1': 'piso de arriba con el fusible = bocas INTERIORES: ARRIBA interior (cable de la bandeja: 1350 en 32XAI, 1391 en 42XC) y ABAJO interior (campo: 3221 a PT001:x1 / presostato PS1 +)',
  '1': 'piso de abajo, paso directo = bocas del EXTREMO: ARRIBA extremo (2142 en 32XAI, 1392 en 42XC) y ABAJO extremo (campo: 3222 a PT001:x2 / PS1 -)',
  'fuente': 'EPLAN no le da designacion de punto (los dos extremos se llaman -32XAI:F1 o -32XAI:1). El lado sale de los esquemas 32 y 42 (cable del tablero arriba, campo abajo). El piso: hoja de datos Phoenix 3211886 (2do nivel con fusible, IEC 60947-7-3) y referencia 75286 verificada con fotos (31XAI, mismo articulo). Dibujo pag 8: 4 bocas en el eje (32XAI x~888.6: y~691.6 / 672.8 / 642.2 / 629.4).',
  'confianza': 'alta para el lado; media para el piso'}
PE['PT 2,5-DIO/L-R'] = {
  'articulo': 'PXC.3210224', 'borneras': ['61XDIO'],
  'anodo': 'ABAJO (lado del puente FBS 4-5 BU; 1264 desde 12XP:2:3 entra en la pieza 1)',
  'catodo': 'ARRIBA (6171..6174 a 61XDO:N:2)',
  'fuente': 'EPLAN no da designacion de punto (-61XDIO:N en los dos extremos). Funcional hoja 61: anodo a la izquierda (lado del puente) y catodo a la derecha -> por la regla horizontal el funcional diria anodo ARRIBA. Pero en la bandeja (pag 8 y vista color pag 7) el puente FBS esta en la mitad de ABAJO de las 4 piezas, asi que el anodo esta fisicamente ABAJO y el catodo ARRIBA. Es el mismo caso del 62XDIO del 75286 y del 61XDIO del 66817 (catodo arriba, confirmado con fotos). Se escribe el lado fisico.',
  'confianza': 'media-alta'}
PE['RIF-0-RPT-xxDC/21'] = {
  'articulo': 'PXC.2903370 (24DC, 42KR1) y PXC.2903371 (12DC, 61KR1..4)',
  '11': 'ARRIBA extremo (comun)', '14': 'ARRIBA medio (NA)', '12': 'ARRIBA interior (NC)',
  'A1 / A1+': 'ABAJO interior (junto al LED)', 'A2 / A2-': 'ABAJO extremo',
  'modulos': '42KR -> 42KR1 (1 modulo); 61KR -> 61KR1..61KR4 de izquierda a derecha a partir de la etiqueta',
  'fuente': 'Referencias 75286 y 66817 (mismo modelo, numeros moldeados en la carcasa, fotos). Dibujo EPLAN pag 8: 3 bocas arriba (y~686/680/673) y 2 abajo (y~633/628) + LED (y~641) en cada modulo: no esta girado. Las filas "-61KRn -> -61KRn" de la lista de conexiones son internas (rele / base) y no son cables.',
  'confianza': 'alta'}
PE['MEAN WELL NDR-240-24'] = {
  'tags': ['11PS1', '11PS2'],
  'TB1:1': 'ABAJO, tornillo 1 (izquierda): FG / tierra', 'TB1:2': 'ABAJO, tornillo 2: N', 'TB1:3': 'ABAJO, tornillo 3 (derecha): L',
  'TB2:1': 'ARRIBA, tornillo 1 (izquierda): -V', 'TB2:2': 'ARRIBA, tornillo 2: -V', 'TB2:3': 'ARRIBA, tornillo 3: +V', 'TB2:4': 'ARRIBA, tornillo 4 (derecha): +V',
  'fuente': 'EPLAN usa directamente bornera:pin (TB1:2, TB2:3). Hoja de datos MEAN WELL NDR-240 (Terminal Pin No. Assignment) + referencia 75286 con fotos. Dibujo pag 8: 4 tornillos arriba (y~697) y 3 abajo (y~620).',
  'texto_taller_sugerido': '11PS1 TB2 1 (-V), 11PS1 TB1 3 (L)...', 'confianza': 'alta'}
PE['MEAN WELL DDR-120A-24'] = {
  'tags': ['13PS1'],
  'PE': 'ABAJO TB1 pin 1 (FG)', '-Vin': 'ABAJO TB1 pin 2', '+Vin': 'ABAJO TB1 pin 3',
  '-Vo': 'ARRIBA TB2 pin 1', '(-Vo)': 'ARRIBA TB2 pin 2', '+Vo': 'ARRIBA TB2 pin 3', '(+Vo)': 'ARRIBA TB2 pin 4 (sin uso)',
  'fuente': 'Hoja de datos MEAN WELL DDR-120 (TB1 entrada abajo FG/-Vin/+Vin, TB2 salida arriba -Vo -Vo +Vo +Vo) + referencias 75286/66817. EPLAN distingue los pines repetidos con parentesis: se aplica la regla verificada en el 66817 (el n-esimo pin con el mismo nombre va al n-esimo tornillo), asi -Vo = pin 1 (1312) y (-Vo) = pin 2 (1235).',
  'confianza': 'alta para el lado; media para -Vo vs (-Vo) (son el mismo potencial)'}
PE['EPEVER Tracer7810BP'] = {
  'tags': ['12PS1'],
  '+Pan/-Pan/+Bat/-Bat/+Car/-Car': 'NO son bornes del aparato: el Tracer7810BP es IP67 con cables propios (panel, bateria y carga); terminan en 12XPS:3..9 punto 1 (ARRIBA).',
  'A/B/GND/VCC': 'Cable RS-485 del regulador, terminan en 12XPS:10..13 punto 1 (ARRIBA).',
  'fuente': 'Ficha EPEVER Tracer7810BP (cables de PV, bateria y carga + puerto RS-485 estanco); hoja 12 y 81; el dibujo de la bandeja lateral (pag 8) no dibuja bornes en 12PS1.',
  'confianza': 'alta'}
PE['DF101 / DF141'] = {
  'tags': ['11F1', '11F2', '13F4', '13F5', '13F6', '12F3 (DF141)'],
  '1': 'ARRIBA (tornillo superior, entrada)', '2': 'ABAJO (tornillo inferior, salida)',
  'fuente': 'Marcado Schneider TeSys DF (1 arriba, 2 abajo) + esquemas 11, 12, 13 (1 dibujado arriba) + dibujo pag 8 (un tornillo arriba y otro abajo por polo).', 'confianza': 'alta'}
PE['EZ9F34210 (termomagnetica 2P)'] = {
  'tags': ['11Q2'],
  '1': 'ARRIBA polo izquierdo (fase, marron)', '2': 'ABAJO polo izquierdo', '3': 'ARRIBA polo derecho (neutro, celeste)', '4': 'ABAJO polo derecho',
  'fuente': 'Marcado Schneider 2P (impares arriba, polo 1-2 a la izquierda) + hoja 11 (1156 marron a 11Q2:1, 1157 celeste a 11Q2:3) + referencia 75286 (F izquierda, N derecha).', 'confianza': 'alta'}
PE['EZ9F36225 (diferencial 2P)'] = {
  'tags': ['11Q1'],
  'N': 'ARRIBA polo izquierdo (neutro)', "N'": 'ABAJO polo izquierdo', '1': 'ARRIBA polo derecho (fase)', '2': 'ABAJO polo derecho',
  'fuente': 'Referencia 75286 (Easy9 RCCB 2P 25 A 30 mA, N impresa a la izquierda, fotos). EPLAN usa 1/2 para la fase y N / N\' para el neutro.',
  'confianza': 'media: la lista dice EZ9F36225 con texto "ACTI9 IID 2P 25A 30MA AC RCCB"; si se monta un Acti9 iID el neutro puede ir del otro lado'}
PE['PSR-SCP-24UC/ESA2/4X1/1X2/B'] = {
  'tags': ['42KS1'],
  'ARRIBA': ['A1', 'S11', 'S12', '13', '23', '33', '43', '51'], 'ABAJO': ['A2', 'S33', 'S34', '14', '24', '34', '44', '52'],
  'fuente': 'Hoja de datos Phoenix 2963802 (2017, esquema de aplicacion: A1 S11 S12 13 23 33 43 51 arriba y A2 S33 S34 14 24 34 44 52 abajo) + dibujo pag 8 (2 filas de 4 tornillos arriba y 2 filas de 4 abajo = 16 bornes). La lista de conexiones no trae el borne en 2114, 2115, 1394-1396 y 4294-4296: por la hoja 42 son 13, 14, 23, 33, 43 (arriba) y 24, 34, 44 (abajo). 4221 es un puente S33-S34 en el mismo aparato.',
  'confianza': 'media para el lado; la boca exacta (fila exterior/interior y columna) queda A CONFIRMAR'}
PE['CHENZHU GS8536-EX'] = {
  'tags': ['15AIB1'],
  'ARRIBA': '[1 2] alimentacion (enchufe trasero, se ve en la misma fila que [3 4 5]); [3 4 5] fila exterior; [6 7 8] fila interior; numero menor a la izquierda',
  'ABAJO': '[9 10 11] fila interior; [12 13 14] fila exterior',
  'fuente': 'Manual CHENZHU + referencia 66817 verificada con fotos + catalogo programa/bornes (GS8536-EX). Dibujo EPLAN pag 8: arriba 2 filas de 3 tornillos (y~552 / 546), abajo 2 filas de 3 (y~487 / 481).',
  'confianza': 'alta para el lado; media para la fila de [1 2]'}
PE['CHENZHU GS8512-EX.22'] = {
  'tags': ['15DIB1', '15DIB2', '15DIB3'],
  'ARRIBA': '[1 2] alimentacion (enchufe trasero, detras de [3 4]); [3 4] fila exterior; [5 6] fila interior', 'ABAJO': '[7 8] fila interior; [9 10] fila exterior',
  'fuente': 'Manual CHENZHU GS8512 + referencia 66817 (fotos) + catalogo (GS8512-EX). Dibujo EPLAN pag 8: arriba 2 filas de 2 (y~552 / 546), abajo 2 filas de 2 (y~487 / 481).',
  'confianza': 'alta para el lado; media para la fila de [1 2]'}
PE['Phoenix EO-I/UT (toma)'] = {
  'tags': ['11SK1'],
  'L / N / PE': 'los tres ABAJO (3 tornillos en la franja inferior del toma, pag 8 x~208/215/222, y~364)',
  'fuente': 'Ficha Phoenix 0804087 (toma tipo I, 45 mm, bornes a tornillo) + dibujo pag 8 + regla del taller "11SK1 todo por abajo".',
  'confianza': 'alta para el lado; el orden L/N/PE de izquierda a derecha queda A CONFIRMAR'}
PE['FUSE MEGA HOLDER (Littelfuse)'] = {
  'tags': ['12F2'], '1': 'esparrago del lado bateria (1211 desde 12PB1 (+))', '2': 'esparrago del lado contactor (1209 a BH_01_ZV:1)',
  'fisico': 'horizontal, esparragos en x~983 y x~1021 (y~711) de la pag 8; sugerido 1 = izquierdo, 2 = derecho (como el 12F2 del 75286)',
  'fuente': 'Hoja 12 + lista de conexiones; el dibujo no marca cual es cual.', 'confianza': 'baja (A CONFIRMAR); cables de 35 mm2 -> E8'}
PE['Trombetta 684-1261-212-17 (contactor)'] = {
  'tags': ['BH_01_ZV'], '1 / 2': 'esparragos de potencia (35 mm2, E8)', 'A1 / A2': 'bobina (A1 = 6151 desde 61XDO:1:4; A2 = 1218 azul 1 mm2)',
  'fuente': 'Hoja 12 y 61; el dibujo pag 8 muestra los esparragos arriba del contactor (y~615) sin designacion.', 'confianza': 'baja (A CONFIRMAR)'}
PE['VBF1 (seccionador TeSys VARIO)'] = {
  'tags': ['11MS1', '13MS1'], '1/L1, 3/L2': 'entrada', '2/T1, 4/T2': 'salida',
  'fuente': 'Lista de conexiones (13MS1) y hoja 11 (11MS1 sin designacion en la lista: 1101/1102 entrada, 1154/1155 salida). Fuera de las bandejas -> LI.', 'confianza': 'no aplica a la bandeja'}

# ---------------------------------------------------------------- dudas
DUDAS = [
 'PTT 2,5-2MT (15XR, 42XC, 81XCM, 32XEX, 41XEX): EPLAN da al borne IMPAR los puntos :2/:3 y al PAR los puntos :1/:4. Si Phoenix numera las 4 bocas de forma correlativa a lo largo de la pieza (lo normal), el PAR quedaria en las bocas del EXTREMO (piso de abajo) y el IMPAR en las INTERIORES, al reves de la convencion del taller (impar = extremo, 75286/66817). En el JSON se dejo la convencion del taller. Hay que confirmarlo en el primer tablero o con la macro EPLAN de Phoenix (EPLAN Data Portal); lo importante es que las dos puntas de un mismo numero queden en el mismo piso.',
 'El lado ARRIBA/ABAJO de los bornes simetricos sale del dibujo del esquema y el proyectista giro los simbolos distinto en cada hoja: en 41XEX, 42XC y 32XEX los puntos :3/:4 estan arriba; en 15XR y 81XCM los :1/:2. No se puede tomar "punto 1 = arriba" fijo para el PTT: hay que leerlo por bornera (campo lado_por_punto de cada pieza).',
 'PT 2,5-QUATTRO-PE de 15XR (3) y 32XEX (5): simbolo espejado (el punto 4 dibujado a la izquierda). Como los 4 puntos son PE y los cables son de campo, se dejo 4 = ABAJO extremo.',
 '61XDIO: el funcional dibuja el anodo a la izquierda (ARRIBA por la regla), pero el puente FBS esta en la mitad de abajo de la bornera en la bandeja: el anodo (1264) va ABAJO y los catodos (6171-6174) ARRIBA. Igual que en el 75286 y el 66817. Confirmar con el usuario que el texto lleve el lado fisico.',
 'PTTB 4-HESI (32XAI y 42XC): EPLAN no designa puntos; el piso F1 = interior (fusible) y 1 = extremo sale de la referencia 75286 (fotos) y de la hoja de datos, no del PDF.',
 '42KS1 (PSR-SCP-24UC/ESA2/4X1/1X2/B): el lado de cada borne sale del esquema de aplicacion de la hoja de datos; no encontre la vista frontal con la fila (exterior/interior) y la columna de cada tornillo. La lista de conexiones deja sin borne a 2114, 2115, 1394, 1395, 1396, 4294, 4295 y 4296 (se tomaron de la hoja 42).',
 '11Q1: la lista de articulos dice EZ9F36225 con texto "ACTI9 IID 2P 25A 30MA AC RCCB" (el codigo Easy9 del diferencial es EZ9R36225). Se uso N a la izquierda como en el 75286; si el aparato montado es otro, puede cambiar.',
 '11SK1 (Phoenix EO-I/UT): los tres bornes van abajo, pero el orden L / N / PE de izquierda a derecha no lo pude confirmar (la ficha no tiene la vista de bornes).',
 '12F2 (MEGA): no hay forma de saber en el dibujo cual esparrago es el 1; se sugiere izquierdo = 1 (bateria). BH_01_ZV: posicion de 1/2/A1/A2 a confirmar. Son cables de 35 mm2 (E8), salvo A1 (6151) y A2 (1218) de 1 mm2.',
 '13PS1: EPLAN nombra los dos -Vo como "-Vo" y "(-Vo)": se tomo -Vo = TB2 pin 1 (1312) y (-Vo) = pin 2 (1235), por la regla del n-esimo pin del 66817.',
 '15DIB3: la hoja 41 dice "SE DEJA PREVISTO EL CABLEADO SIN LA BARRERA, SE REEMPLAZA POR BORNES TIPO CUCHILLA ABIERTOS", pero la barrera figura en la lista de articulos y en la bandeja. SP_3: "SE DEJA PREVISTO EL CABLEADO CON EL CONECTOR DIN SIN LA SOLENOIDE".',
 '41XEX: el orden fisico de las piezas es 1-2, 3-4, 5-6, 9-10, 7-8, 11-12 (las piezas 9-10 y 7-8 cambiadas) en la hoja de hileras y en la bandeja. Puede ser un error del proyectista; el mapeo tiene que respetar el numero, no la posicion.',
 'XPE: la hoja de hileras muestra un terminal "1" extra sin articulo; 42XC muestra el "4" en un renglon aparte sin articulo. Fisicamente XPE tiene 3 piezas y 42XC 3 piezas (F1/1, 3/4, 5/6).',
 'La lista de conexiones no trae destino para algunos cables: tierras sin numero (XPE, 11SK1:PE, 13PS1:PE, 15XR:3:4, 32XEX:5:4, 81XCM:9:2), mallas (21PCB01:34 y :37) y cables de campo (+Campo-...). X1 (conector del sensor de nivel) y R1 (120 R) no estan en la lista de articulos.',
 '12XPS:10 y 12XPS:11 llevan dos conductores en el punto 2 (2135 y 2136 son cables de 3 puntas 21PCB01 -> 12XPS -> 81XCM): terminal doble.',
 '11MS1 y 13MS1 (seccionadores VBF1) no estan en el dibujo de las bandejas; se tomaron como fuera de bandeja (LI).',
]

out = collections.OrderedDict()
out['proyecto'] = {'doc': 'ZPL-76884 Rev 1', 'producto': 'mSafe2+ PAE', 'cliente': 'PAE', 'origen': 'EPLAN (PDF con texto real)',
                   'pdf': 'C:/Buscar Termos en plano/1 - Planos/Producto nuevo/ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.pdf',
                   'paginas': {'bandeja': 8, 'esquemas': '10-21', 'hileras': '32-39', 'lista_articulos': '40-46', 'lista_conexiones': '47-50'},
                   'convencion_lado': 'ARRIBA/ABAJO = lado fisico en la bandeja (pag 8). extremo = boca mas lejos del riel; interior = boca mas cerca del riel.',
                   'x_etiqueta_pag8': 'x (pt, pagina 8, origen abajo-izq) del numero que EPLAN escribe debajo de cada pieza; sirve para ubicar la pieza, no es el punto del borne.'}
out['proyecto']['fuentes_externas'] = [
  'Phoenix Contact PTT 2,5-2MT 3210258, hoja de datos (files.kempstoncontrols.com/files/79f3f39887d59daa5dd65d4fc2d41c12/3210258.pdf): 4 conexiones, 2 niveles, no numera bocas',
  'Phoenix Contact PSR-SCP-24UC/ESA2/4X1/1X2/B 2963802, hoja de datos (media.distrelec.com/Web/Downloads/_t/ds/PSR-SCP-_24UC_ESA2_4X1_1X2_B_eng_tds.pdf y farnell.com/datasheets/1500067.pdf)',
  'Phoenix Contact PTTB 4-HESI (5X20) 3211886 (fichas de distribuidores; 1er y 2do nivel push-in, fusible G 5x20)',
  'Phoenix Contact EO-I/UT 0804087 (ficha: toma tipo I, 45 x 75 mm, bornes a tornillo M3)',
  'EPEVER Tracer7810BP (ficha: IP67, cables de PV/bateria/carga y puerto RS-485)',
  'Referencias del taller: prototipos/_referencia (75286) y prototipos/_referencia_66817, programa/bornes/catalogo.json']
out['aparatos'] = aparatos
out['borneras'] = B
out['puntos_eplan'] = PE
out['dudas'] = DUDAS
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
base = os.path.dirname(OUT)
with open(os.path.join(base, 'codigo_aparatos', 'lista_articulos.json'), 'w', encoding='utf-8') as f:
    json.dump({'fuente': 'paginas PDF 40-46 (Lista de articulos), leida por celdas con pypdfium2', 'renglones': renglones}, f, ensure_ascii=False, indent=1)
with open(os.path.join(base, 'codigo_aparatos', 'lista_conexiones.json'), 'w', encoding='utf-8') as f:
    json.dump({'fuente': 'paginas PDF 47-50 (Lista de conexiones), leida por celdas con pypdfium2; cable None = fila sin numero',
               'conexiones': conexiones}, f, ensure_ascii=False, indent=1)
print('ok', OUT, len(aparatos), 'aparatos', len(B), 'borneras')
