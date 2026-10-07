"""Pruebas de los arreglos del instructivo para planos de EPLAN (PAE, ZPL-76884), 2026-10-02.
No escribe nada en los trabajos (el de la web va a una carpeta temporal). Termina con error si alguna falla.
uso: python pruebas/probar_arreglos_pae.py
  A. tipo de circuito por la zona: los de campo de 32XEX/41XEX van por la canaleta azul hasta la salida (todos por el
     mismo camino); el RS-485 azul de 81XCM no es intrinseco (zona comun); el otro piso del mismo borne manda.
  B. EPLAN: dos tramos de la misma punta de la bandeja a dos puntos distintos de afuera no se pierden al deduplicar.
  C. otra estacion (E8): el destino en la zona hidraulica es el texto real de la punta, no 'LI'.
  D. web: POST /api/trabajo/<id>/topografico/mismo da 400 si el trabajo no es de EPLAN."""
import os, sys, json, copy, shutil, tempfile
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'programa'))
from core import process
import instructivo, topo, eplan, ruteo

PDF = os.path.join(RAIZ, '1 - Planos', 'Producto nuevo', 'ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.pdf')
JOB = os.path.join(RAIZ, 'pruebas', 'trabajos', '76884')
fallas = []


def chequear(ok, msg):
    print(('  ok    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)


def preparar():
    res = process(PDF, log=lambda m: None)
    lay = topo.layout(PDF, instructivo.known_tags(res), log=lambda m: None)
    eplan.aplicar_puntos(res, lay, JOB)
    lay.update(bornes_usuario={}, estaciones={}, estacion='E6', estacion_auto={'seccion_min': 35, 'estacion': 'E8'})
    return res, lay


def armar(res, lay):
    """build + el tipo de circuito (ex) con que se ruteo cada linea: {id(ruta): ex}"""
    tipos, orig = {}, ruteo.route_line
    def rl(*a, **k):
        r = orig(*a, **k)
        if r is not None:
            tipos[id(r)] = a[5]
        return r
    ruteo.route_line = rl
    try:
        ins = instructivo.build(res, copy.deepcopy(lay))
    finally:
        ruteo.route_line = orig
    lineas = [l for p in ins['pasos'] for l in p['lineas']]
    return ins, lineas, (lambda l: tipos.get(id(l.get('ruta')), 'sin ruta'))


def recorrido(ruta, ductos, tol=0.5):
    """[(x, y, en_azul)] de puntos a lo largo de la ruta, desde que entra a la primera canaleta"""
    out = []
    for a, b in zip(ruta[1:], ruta[2:]):
        for k in range(1, 20):
            t = k / 20.0
            p = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            azul = any(d['b'][0] - tol <= p[0] <= d['b'][2] + tol and d['b'][1] - tol <= p[1] <= d['b'][3] + tol for d in ductos if d['ex'])
            out.append((p[0], p[1], azul))
    return out


res, lay = preparar()
ins, lineas, ex_de = armar(res, lay)
ductos = lay['ductos']

print('A. tipo de circuito por la zona de la punta')
campo_ex = [l for l in lineas if l['origen'].split(' ')[0] in ('32XEX', '41XEX') and (l['num'].startswith(('s/n', '⏚')))]
chequear(len(campo_ex) == 15, f'15 cables de campo en 32XEX/41XEX (2 PIT01F, 12 IP_x, la tierra): {len(campo_ex)}')
chequear(all(ex_de(l) is True for l in campo_ex), 'todos se rutean como intrinsecos')
caminos = {json.dumps(l['ruta'][2:]) for l in campo_ex}
chequear(len(caminos) == 1, f'todos por el mismo camino desde la canaleta: {len(caminos)} camino(s)')
def azul_hasta_salida(l):
    """entra a la canaleta azul y va por azules hasta que la deja una sola vez, derecho a la salida a LI (sin pasar por
    la comun de abajo ni por la del medio, la de la salida de 220 VAC)"""
    rec = recorrido(l['ruta'], ductos)
    deja = next((i for i, p in enumerate(rec) if not p[2]), len(rec))
    media = ruteo.ancho(ductos) / 2 + 0.5           # dentro de la canaleta de la salida (medio ancho de su eje)
    return rec and rec[0][2] and all(not p[2] for p in rec[deja:]) and all(abs(p[1] - l['ruta'][-1][1]) <= media for p in rec[deja:])
malos = [l['num'] for l in campo_ex if not azul_hasta_salida(l)]
chequear(not malos, f'por la canaleta azul hasta el tramo recto de la salida a LI (fuera de eso: {malos})')
rs485 = [l for l in lineas if l['origen'].startswith('81XCM') and l['cable'].endswith('0.32MM')]
chequear(rs485 and all(ex_de(l) is False for l in rs485),
         f"RS-485 de 81XCM ({', '.join(sorted({l['num'] + ' ' + l['cable'] for l in rs485}))}): comun por la zona, aunque el 2132/2135 sean azules")
rotork = [l for l in lineas if l['origen'].startswith('15XR')]
chequear(rotork and all(ex_de(l) is False for l in rotork), 'ROTORK (15XR, zona comun): comun')
barreras = [l for l in lineas if l['cable'].startswith('A0.75') and l['destino'].split(' ')[0] in ('32XEX', '41XEX')]
chequear(len(barreras) == 16 and all(ex_de(l) is True for l in barreras), f'barreras -> 32XEX/41XEX azules (16): intrinsecos ({len(barreras)})')
# el otro piso del mismo borne: con la canaleta azul de abajo y la vertical como comunes, la zona de las bocas de abajo de
# 32XEX/41XEX es comun, pero el piso de arriba tiene un azul intrinseco -> los de campo siguen siendo intrinsecos
lay2 = copy.deepcopy(lay)
for d in lay2['ductos']:
    if d['ex'] and not (d['h'] and d['b'][1] > min(x['b'][1] for x in lay2['ductos'] if x['ex']) + 1):
        d['ex'] = False          # quedan azules solo las horizontales de arriba de 32XEX/41XEX
net2 = ruteo.Net(copy.deepcopy(lay2['ductos']))
_, lineas2, ex2 = armar(res, lay2)
c2 = {l['num']: l for l in lineas2 if l['origen'].split(' ')[0] in ('32XEX', '41XEX') and l['num'].startswith(('s/n', '⏚'))}
z = net2.zona(c2['s/n IP_1_ZSO 13']['marca_o'][:2], 1)
chequear(z is False, f"(variante) zona de 41XEX 1 ABAJO = comun: {z}")
chequear(ex2(c2['s/n IP_1_ZSO 13']) is True, '(variante) 41XEX 1 ABAJO de campo: intrinseco por el otro piso (41XEX 1 ARRIBA = 4116 azul)')
chequear(all(ex2(l) is True for n, l in c2.items() if n != '⏚32XEX'), '(variante) todos los de campo de bornes con azul arriba: intrinsecos')
chequear(ex2(c2['⏚32XEX']) is False, '(variante) la tierra 32XEX 5.4 (borne sin azul): comun')

print('B. deduplicacion por par de puntas (EPLAN)')
res3 = copy.copy(res)
res3.conductores = copy.deepcopy(res.conductores)
c = res3.conductores['2135']
nuevo = dict(c['nodes']['-21PCB01:35'], texto='21PCB01 99', borne='99', d='-21PCB01:99')
c['nodes']['-21PCB01:99'] = nuevo
par = tuple(sorted(('-81XCM:7:2', '-21PCB01:99')))
c['pares'].append(par); c['desc_par'][par] = c['desc_par'][tuple(sorted(('-12XPS:10', '-81XCM:7:2')))]
c['bornes'] = sorted(c['nodes'])
_, lineas3, _ = armar(res3, lay)
n_antes = sum(1 for l in lineas if l['num'] == '2135' and l['origen'] == '81XCM 7 ARRIBA')
n3 = sum(1 for l in lineas3 if l['num'] == '2135' and l['origen'] == '81XCM 7 ARRIBA')
chequear(n_antes == 1 and n3 == 2, f'2135 con un segundo tramo 81XCM 7 ARRIBA -> LI (otro punto de afuera): {n_antes} -> {n3} lineas')
chequear(len(lineas) == 136, f'PAE sin cambios: {len(lineas)} lineas E6 (136: bateria 12PB1 y solenoides SP_x en E8 desde el 2026-10-06)')

print('C. otra estacion (E8): texto real del destino')
otra = {(l['num'], l['origen']): l['destino'] for l in ins['otra_estacion'] if not l.get('pendiente')}
esperado = {('3221', '32XAI F1 ABAJO'): 'PT001 x1', ('3222', '32XAI 1 ABAJO'): 'PT001 x2', ('6151', '61XDO 1.4'): 'BH_01_ZV A1',
            ('1339', '13X24V 2.2'): 'empalme con LS001A 1 Marron (+)', ('1340', '13X24V 4.3'): 'empalme con LS001A 2 Azul (-)'}
for k, v in esperado.items():
    chequear(otra.get(k) == v, f'{k[0]}: {k[1]} -> {otra.get(k)} (esperado {v})')
chequear(len(ins['otra_estacion']) == 24, f"24 en otra estacion (16 + bateria y solenoides): {len(ins['otra_estacion'])}")
base = json.load(open(os.path.join(RAIZ, 'pruebas', 'bases', 'base_76884.json'), encoding='utf-8'))
chequear([(l['num'], l['origen'], l['destino']) for l in lineas] == [(l['num'], l['origen'], l['destino']) for l in base['lineas']],
         'lineas E6 iguales a la base (siguen con LI donde corresponde)')

print('D. web: «Usar las bandejas de este mismo PDF» solo para EPLAN')
import web
tmp = tempfile.mkdtemp(prefix='pae_web_')
try:
    web.WORK = tmp
    for jid, ep in (('a0a0a0a0a0a0', False), ('b1b1b1b1b1b1', True)):
        os.makedirs(os.path.join(tmp, jid))
        json.dump(dict(id=jid, nombre='plano.pdf', archivo='plano.pdf', estado='terminado', eplan=ep),
                  open(os.path.join(tmp, jid, 'estado.json'), 'w', encoding='utf-8'))
    llamados = []
    orig = web.usar_mismo_pdf
    web.usar_mismo_pdf = lambda jid: llamados.append(jid)
    try:
        cli = web.app.test_client()
        r = cli.post('/api/trabajo/a0a0a0a0a0a0/topografico/mismo', base_url=f'http://127.0.0.1:{web.PORT}')
        chequear(r.status_code == 400 and (r.get_json() or {}).get('error') == 'Solo para planos de EPLAN',
                 f'AutoCAD: {r.status_code} {r.get_json()}')
        r = cli.post('/api/trabajo/b1b1b1b1b1b1/topografico/mismo', base_url=f'http://127.0.0.1:{web.PORT}')
        chequear(r.status_code == 200 and llamados == ['b1b1b1b1b1b1'], f'EPLAN: {r.status_code} {r.get_json()}, usar_mismo_pdf {llamados}')
    finally:
        web.usar_mismo_pdf = orig
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('\n' + ('TODO OK' if not fallas else f'{len(fallas)} FALLA(S)'))
sys.exit(1 if fallas else 0)
