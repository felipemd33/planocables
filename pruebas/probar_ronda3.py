"""Pruebas de la ronda 3 (2026-10-02 noche): mapeo de bornes con modelos que no estan en el catalogo, topografico sin
capa de riel, version del lector del topografico y avisos de bornes.json en EPLAN. No escribe nada en los trabajos
(lo que necesita escribir lo hace en una copia temporal). Termina con error si alguna falla.
uso: python pruebas/probar_ronda3.py
  A. familias del catalogo: el tipo de aparato sale del renglon de la lista de materiales.
  B. TPT (72715 + 72887): 33MX01 (MOXA, modulo de E/S) con un catalogo SIN su modelo queda sin puntos y no cae sobre
     13PS3; con el modelo MOXA-R1240 (2026-10-06) sus 20 bornes van a la columna del frente;
     11Q1 (ABB SH 202, termomagnetica) no sale como toma corriente; 43XDIB sale con el modelo de la lista
     (PTT 2,5-2MT BU), no como bornera con diodo; ningun punto cae dentro del cuerpo de otro aparato.
  C. red de seguridad: sin la lista de materiales, los puntos de 33MX01 que caen sobre la bornera TB2 de 13PS3 se
     descartan; dos puntos de tags distintos encimados se descartan (el de menor confianza, o los dos).
  D. dos pisos del MISMO borne en el mismo punto con confianza media: el texto queda como el funcional (no se pasa al
     lado fisico).
  E. topografico: sin capa de riel, un tramo por geometria vale solo con etiquetas apoyadas y 3 componentes o mas
     (FCS 75992: sin bandeja falsa); dos lecturas del mismo tag: manda la exacta (43DIB1).
  F. version del lector en layout.json: un layout viejo se vuelve a leer al regenerar y se conserva lo del usuario.
  G. EPLAN: un bornes.json roto se avisa (no se ignora en silencio) y no tapa el mapeo verificado."""
import os, sys, json, collections, shutil, tempfile, copy
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROG = os.environ.get('PLANOCABLES_PROGRAMA') or os.path.join(RAIZ, 'programa')
sys.path.insert(0, PROG)
sys.stdout.reconfigure(encoding='utf-8')
from core import process
import instructivo, topo, bornes
from bornes.motor import Motor, materiales_de_lineas

JOB = os.path.join(RAIZ, 'pruebas', 'trabajos', 'tpt')
FCS = os.path.join(RAIZ, '1 - Planos', 'Catalogo (referencia)', '20059147 - FCS - 10un', '75992  ZPL-Rev1 Structure and Arrangement - dFrac FCS.pdf')
# tags del funcional del FCS (75733), para no leerlo entero en la prueba
FCS_TAGS = ['11F1', '11Q1', '11XG', '11XP', '12PS1', '12PS2', '12XP1', '12XP2', '13F2', '13F3', '13XP', '14XN', '15MX', '15XP1',
            '16F4', '16F5', '16XP2', '16XP3', '30AIB1', '30XAI', '31AIB2', '31AIB3', '31AIB4', '32AIB1', '32AIB2', '32XAI',
            '41DIB1', '41DIB2', '41XDI', '42DIB3', '42DIB4', '43DIB5', '43DIB6', '60DS', '60IL1', '60KR', '60VN1', '61KR',
            '63IL1', '63IL2']
PAE = os.path.join(RAIZ, '1 - Planos', 'Producto nuevo', 'ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.pdf')
CAT = json.load(open(os.path.join(PROG, 'bornes', 'catalogo.json'), encoding='utf-8'))
fallas = []


def chequear(ok, msg):
    print(('  ok    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)


print('A. familias del catalogo')
mo0 = Motor.__new__(Motor)
mo0.familias = [(f['familia'], f['nombre'], __import__('re').compile(f['patron'])) for f in CAT['general']['familias']]
casos = {'AC Control Circuit Breaker | / | Interruptor térmico de control AC | ABB | SH | 202 | C10': 'termomagnetica',
         'Interruptor termomagnético 2x10A curva C | SCHNEIDER | EZ9F34210': 'termomagnetica',
         'Disyuntor diferencial 25A | -': 'diferencial',
         'Analog Inputs Module | 1 | Modulo de entradas analógicas | MOXA | ioLogik R1240-T': 'modulo_es',
         'Terminal Relay 24Vdc | / | Borne relé 24Vcc | PHOENIX CONTACT | RIF-0-RPT-24DC/21': 'rele',
         'Intrinsic Safety Digital Inputs Terminals | / | Bornes de entradas digitales Seg. Intrínseca | PHOENIX CONTACT | PTT 2,5-2 MT BU': 'bornera',
         'Digital Input signals | Intrinsic safety barrier | / | Entrada Digital | Barrera Seg. Intrínseca | CHENZHU | GS8512-EX.22': 'barrera',
         'Power Supply Terminals | 1 | Bornes de alimentación | PHOENIX CONTACT | PT 4': 'bornera',
         'Power Source 110-240 Vca to 12 Vdc | / | Fuente de | alimentación | MEAN WELL | NDR-120-12': 'fuente',
         'Conversor 12/24VDC | MEAN WELL | DDR-120A-24': 'fuente',
         '12Vdc Control Voltage | Fuse Base | / | Base de fusible para voltage de control 12Vcc | ABB | E 91/32': 'portafusible',
         'Bornes fusible para AI | PHOENIX CONTACT': 'bornera',
         'Toma corriente IRAM | VIVION | -': 'toma',
         'Battery Charger 12 Vdc | / | Cargador de baterías 12 Vcc | EPEVER | Tracer 5210BP': 'cargador',
         'Módulo conversor HART a MODBUS | EXEMYS | EGW1-MB-HT': 'modulo_es',
         'Interruptor limite de puerta | OMRON | HL-5200': 'mando',
         'AC RCBO BREAKER | AB2000530 | ABB | DS201': 'diferencial',
         'VENTILATION (FAN) | AB2000470 | FINDER | 7F.31.8.230.1020': 'ventilador',
         'INTERRUPTOR AUTOMÁTICO DE POTENCIA AC | AB2000423 | ABB | S202-C': 'termomagnetica',
         'A | FUSILERA PARA RIEL DIN | SCHNEIDER | DF101 10x38': 'portafusible',
         'PHOENIX CONTACT | PT 4': None}
for t, f in casos.items():
    chequear(mo0.familia_de_texto(t) == f, f"'{t[:60]}' -> {mo0.familia_de_texto(t)} (esperado {f})")
sin_fam = [m['id'] for m in CAT['modelos'] if not m.get('familia')]
chequear(not sin_fam, f'todos los modelos del catalogo tienen familia (sin familia: {sin_fam})')

print('B. mapeo del TPT con la lista de materiales del funcional')
est = json.load(open(os.path.join(JOB, 'estado.json'), encoding='utf-8'))
res = process(os.path.join(JOB, est['archivo']), log=lambda m: None)
TOPO = os.path.join(JOB, 'topografico.pdf')
lay0 = topo.layout(TOPO, instructivo.known_tags(res), log=lambda m: None)
usos = instructivo.usos_bandeja(res, json.loads(json.dumps(lay0)), TOPO)
mats = instructivo.materiales_funcional(res)
# (2026-10-06) el MOXA ioLogik R1240 ya esta en el catalogo (MOXA-R1240): lo de un modulo de E/S que NO esta en el
# catalogo se prueba con una copia del catalogo sin ese modelo
CAT_SIN_MOXA = dict(CAT, modelos=[m for m in CAT['modelos'] if m['id'] != 'MOXA-R1240'])
mo_sm = Motor(TOPO, copy.deepcopy(usos), CAT_SIN_MOXA, materiales_de_lineas(mats))
sal_sm = mo_sm.mapear()
p33 = [p for p in sal_sm['puntos'] if p['componente'] == '33MX01']
chequear(sal_sm['modelos'].get('33MX01') == '?' and all(p['confianza'] == 'baja' for p in p33),
         f"(catalogo sin el MOXA) 33MX01 (modulo de E/S) sin modelo y sin puntos: modelo {sal_sm['modelos'].get('33MX01')}, "
         f"{collections.Counter(p['confianza'] for p in p33)}")
falt = {f['tag']: f for f in sal_sm.get('modelos_faltantes') or []}
chequear((falt.get('33MX01') or {}).get('familia') == 'módulo de E/S' and 'MOXA' in (falt.get('33MX01') or {}).get('modelo', ''),
         f"(catalogo sin el MOXA) 33MX01 en los modelos faltantes con su familia: {falt.get('33MX01')}")
mo = Motor(TOPO, copy.deepcopy(usos), CAT, materiales_de_lineas(mats))
sal = mo.mapear()
pts = collections.defaultdict(list)
for p in sal['puntos']:
    pts[p['componente']].append(p)
p1 = next((p for p in pts['33MX01'] if p['texto'] == '33MX01 1'), None)
chequear(sal['modelos'].get('33MX01') == 'MOXA-R1240' and len(pts['33MX01']) == 20 and all(p['confianza'] == 'media' for p in pts['33MX01'])
         and p1 is not None and abs(p1['x'] - 561.0) < 0.5 and abs(p1['y'] - 588.1) < 0.5,
         f"33MX01 con el modelo MOXA-R1240: los 20 bornes con la hoja de datos (pin 1 en el primer cuadradito de la columna, "
         f"561.0 / 588.1): {sal['modelos'].get('33MX01')}, {collections.Counter(p['confianza'] for p in pts['33MX01'])}, "
         f"pin 1 {p1 and (p1['x'], p1['y'])}")
fam_mod = {m['id']: m.get('familia') for m in CAT['modelos']}
chequear(fam_mod.get(sal['modelos'].get('11Q1')) == 'termomagnetica', f"11Q1 (ABB SH 202) solo puede ser termomagnetica: {sal['modelos'].get('11Q1')}")
chequear(sal['modelos'].get('43XDIB') == 'PTT2.5-2MT-BU', f"43XDIB con el modelo de la lista (PTT 2,5-2MT BU), no PT2.5-DIO: {sal['modelos'].get('43XDIB')}")
chequear(sorted((p['texto'], p['confianza']) for p in pts['13PS3'] if 'Vo' in p['texto']) ==
         [('13PS3 +Vo', 'alta')] * 2 + [('13PS3 -Vo', 'alta')] * 2, '13PS3: los 4 bornes de TB2 (+Vo, -Vo) siguen exactos')
cu = mo.cuerpos(sal['puntos'])
dentro = [(p['texto'], j) for p in sal['puntos'] if p['confianza'] != 'baja' for j, b in cu.items()
          if j not in (p['componente'], p.get('ubicado_en')) and b[0] < p['x'] < b[2] and b[1] < p['y'] < b[3]]
chequear(not dentro and '13PS3' in cu, f'ningun punto dentro del cuerpo de otro aparato (cuerpos: {sorted(cu)}; dentro: {dentro})')
encima = [(p['texto'], q['texto']) for i, p in enumerate(sal['puntos']) for q in sal['puntos'][i + 1:]
          if p['confianza'] != 'baja' and q['confianza'] != 'baja' and p['componente'] != q['componente']
          and (p.get('ubicado_en') or p['componente']) != (q.get('ubicado_en') or q['componente'])
          and abs(p['x'] - q['x']) < 0.85 and abs(p['y'] - q['y']) < 0.85]
chequear(not encima, f'ningun punto encima de un borne de otro tag: {encima}')

print('C. red de seguridad (sin los renglones de 33MX01 y 11Q1 en la lista: la geometria elige libre)')
mats2 = [m for m in mats if not m.startswith('33MX01') and not m.startswith('11Q1')]
mo2 = Motor(TOPO, copy.deepcopy(usos), CAT, materiales_de_lineas(mats2))
sal2 = mo2.mapear()
p33 = [p for p in sal2['puntos'] if p['componente'] == '33MX01']
desc = [p for p in p33 if p['como'].startswith('DESCARTADO')]
chequear(sal2['modelos'].get('33MX01') != '?' and len(desc) >= 6 and all(p['confianza'] == 'baja' for p in p33),
         f"33MX01 como {sal2['modelos'].get('33MX01')}: sus puntos sobre 13PS3 se descartan ({len(desc)} descartados, "
         f"{collections.Counter(p['confianza'] for p in p33)})")
chequear(any('descartado' in a and '13PS3' in a for a in sal2['avisos']), 'aviso de los puntos descartados')
chequear(all(p['confianza'] == 'alta' for p in sal2['puntos'] if p['componente'] == '13PS3' and 'Vo' in p['texto']),
         '13PS3 conserva sus puntos de TB2')
# dos tags encimados (armado): alta contra media -> se descarta la media; misma confianza -> las dos
mo2.cuerpos = lambda puntos: {}
falsos = [dict(texto='61XDIO 1', cables=['1'], componente='61XDIO', modelo='x', x=700.0, y=580.0, r=1, confianza='alta', como=''),
          dict(texto='13XC1 1.1', cables=['2'], componente='13XC1', modelo='x', x=700.4, y=580.2, r=1, confianza='media', como=''),
          dict(texto='12XP 1.1', cables=['3'], componente='12XP', modelo='x', x=650.0, y=580.0, r=1, confianza='media', como=''),
          dict(texto='31XAI 1', cables=['4'], componente='31XAI', modelo='x', x=650.3, y=580.0, r=1, confianza='media', como=''),
          dict(texto='XM1 1', cables=['5'], componente='XM1', modelo='x', x=640.0, y=580.0, r=1, confianza='alta', como='')]
mo2.red_de_seguridad(falsos)
chequear([p['confianza'] for p in falsos] == ['alta', 'baja', 'baja', 'baja', 'alta'],
         f"encimados: alta/media -> se descarta la media; media/media -> las dos: {[p['confianza'] for p in falsos]}")

print('D. dos pisos del mismo borne en el mismo punto (confianza media): queda el texto del funcional')
q11 = {p['texto']: p for p in sal2['puntos'] if p['componente'] == '11Q1'}
mismo = q11.get('11Q1 N ARRIBA') and q11.get('11Q1 N ABAJO') and q11['11Q1 N ARRIBA']['confianza'] == 'media' and \
    (q11['11Q1 N ARRIBA']['x'], q11['11Q1 N ARRIBA']['y']) == (q11['11Q1 N ABAJO']['x'], q11['11Q1 N ABAJO']['y'])
chequear(bool(mismo), f"(sin lista, 11Q1 sale como {sal2['modelos'].get('11Q1')}: N ARRIBA y N ABAJO en el mismo punto, media)")


def lineas_de(sal_, forzar_alta=()):
    lay = json.loads(json.dumps(lay0))
    auto = bornes.puntos_automaticos(sal_)
    for a in auto:
        if a['texto'] in forzar_alta:
            a['confianza'] = 'alta'
    bornes.componer_bornes(lay, auto, {}, {}, {})
    lay.update(bornes_usuario={}, estaciones={}, estacion='E6', estacion_auto={'seccion_min': 35, 'estacion': 'E8'})
    ins = instructivo.build(res, lay)
    return {l['num']: l for p in ins['pasos'] for l in p['lineas']}


lin = lineas_de(sal2)
t1105 = lin.get('1105', {}).get('origen'), lin.get('1107', {}).get('origen')
chequear(t1105 == ('11Q1 N ARRIBA', '11Q1 N ABAJO'), f'1105 / 1107 con el texto del funcional: {t1105}')
lin = lineas_de(sal2, forzar_alta=('11Q1 N ARRIBA', '11Q1 N ABAJO'))
t1105 = lin.get('1105', {}).get('origen'), lin.get('1107', {}).get('origen')
chequear(t1105 == ('11Q1 N ABAJO', '11Q1 N ABAJO'), f'(control) con confianza alta el texto lleva el lado fisico: {t1105}')

print('E. topografico')
H = 19.56
tr = lambda x0, x1, y: dict(x0=x0, x1=x1, y0=y - H / 2, y1=y + H / 2, H=H, eje=y, forma='rect')
hit = lambda t, x, y: dict(tag=t, leido=t, x=x, y=y)
dos = topo.geo_con_etiquetas([tr(100, 300, 500)], [hit('60DS', 150, 502), hit('60VN1', 250, 498), hit('11Q1', 200, 700)])
tres = topo.geo_con_etiquetas([tr(100, 300, 500)], [hit('60DS', 150, 502), hit('60VN1', 250, 498), hit('11Q1', 330, 505)])
chequear(dos == [] and len(tres) == 1, f'sin capa de riel: 2 componentes apoyados no son bandeja ({len(dos)}), 3 si ({len(tres)})')
lf = topo.layout(FCS, set(FCS_TAGS), log=lambda m: None)
chequear(lf.get('pag') is None and not any(c.get('ubic') == 'BANDEJA' for c in lf.get('comp', {}).values()),
         f"FCS 75992: sin bandeja falsa (hoja {lf.get('pag')}, filas {lf.get('filas')})")
chequear(lay0['pag'] == 4 and len(lay0['filas']) == 2, f"TPT: bandeja en la hoja 4 con 2 rieles ({lay0['pag']}, {lay0['filas']})")
c43 = lay0['comp'].get('43DIB1') or {}
chequear(c43.get('leido') == '43DIB1' and c43.get('ubic') == 'BANDEJA' and c43.get('fila') == 2,
         f"43DIB1: la lectura exacta manda (leido {c43.get('leido')!r}, {c43.get('ubic')}, fila {c43.get('fila')})")

print('F. version del lector del topografico')
chequear(topo.layout_al_dia(lay0) and not topo.layout_al_dia(dict(lay0, version_lector=None)),
         f"layout_al_dia: {lay0.get('version_lector')}")
chequear(not topo.layout_al_dia(os.path.join(JOB, 'layout.json')), 'el layout.json del TPT de prueba es viejo (sin version)')
import web
tmp = tempfile.mkdtemp(prefix='ronda3_')
try:
    jid = 'abcdef123456'
    d = os.path.join(tmp, jid)
    shutil.copytree(JOB, d)
    ij = os.path.join(d, 'instructivo.json')
    old = json.load(open(ij, encoding='utf-8'))
    n_hechos = sum(1 for p in old['pasos'] for l in p['lineas'] if l.get('hecho'))
    old['overrides'] = {'12PB1': {'ubic': 'LI'}, '11PS1': {'ubic': 'BANDEJA', 'fila': 1, 'lado': 'ABAJO'}}
    old['bornes_usuario'] = {'12XP 1.1#1203': [700.0, 600.0, 2.0]}
    json.dump(old, open(ij, 'w', encoding='utf-8'), ensure_ascii=False)
    web.WORK = tmp
    web.INS[jid] = dict(estado='en cola', mensaje='', progreso=0.0)
    web.gen_instructivo(jid)
    st = web.INS[jid]
    nuevo_lay = json.load(open(os.path.join(d, 'layout.json'), encoding='utf-8'))
    nuevo = json.load(open(ij, encoding='utf-8'))
    chequear(st.get('estado') == 'terminado', f"regenerar: {st.get('estado')} {st.get('error') or ''}")
    chequear(topo.layout_al_dia(nuevo_lay) and len(nuevo_lay.get('filas') or []) == 2,
             f"el layout viejo se volvio a leer: version {nuevo_lay.get('version_lector')}, filas {nuevo_lay.get('filas')}")
    chequear(nuevo.get('overrides') == old['overrides'] and nuevo.get('bornes_usuario') == old['bornes_usuario'],
             'se conservan los overrides de Componentes y orden y los puntos ajustados en el visor')
    # las marcas de las lineas que siguen igual (mismo cable y mismas puntas, sin mirar ARRIBA/ABAJO) se conservan;
    # las de lineas que cambiaron con los arreglos del lector (1304 y 1309 ahora van de 13PS3 a 13XC1, 1305...) no
    import re as _re
    sl = lambda t: _re.sub(r' (ARRIBA|ABAJO)$', '', t or '')
    par = lambda l: (l['num'], frozenset((sl(l['origen']), sl(l['destino']))))
    nuevas = {par(l): l for p in nuevo['pasos'] for l in p['lineas']}
    siguen = [par(l) for p in old['pasos'] for l in p['lineas'] if l.get('hecho') and par(l) in nuevas]
    sin_marca = [k[0] for k in siguen if not nuevas[k].get('hecho')]
    n2 = sum(1 for l in nuevas.values() if l.get('hecho'))
    chequear(siguen and not sin_marca, f'se conservan las marcas de cableado de las lineas que siguen igual: {len(siguen)} de {n_hechos} '
             f'marcadas siguen igual, {n2} marcadas ahora (sin la marca: {sin_marca})')
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('G. EPLAN: bornes.json roto')
import eplan
rp = process(PAE, log=lambda m: None)
lp = topo.layout(PAE, instructivo.known_tags(rp), log=lambda m: None)
chequear(topo.layout_al_dia(lp) and str(lp.get('version_lector')).startswith('eplan'), f"layout de EPLAN con su version: {lp.get('version_lector')}")
tmp = tempfile.mkdtemp(prefix='ronda3_')
try:
    open(os.path.join(tmp, 'bornes.json'), 'w', encoding='utf-8').write('{"puntos": {roto')
    r = eplan.aplicar_puntos(rp, json.loads(json.dumps(lp)), tmp)
    chequear(any('bornes.json ilegible' in a for a in r['avisos']), f"aviso del bornes.json roto: {[a for a in r['avisos'] if 'bornes' in a][:2]}")
    chequear(r['n_puntos'].get('alta', 0) > 100, f"el mapeo verificado se aplica igual: {r['n_puntos']}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print('TODO OK' if not fallas else f'{len(fallas)} FALLAS')
sys.exit(1 if fallas else 0)
