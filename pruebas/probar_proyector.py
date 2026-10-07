"""Pruebas de la pestaña 📽 Proyector (2026-10-05): orificios de montaje de la placa para calibrar la proyeccion y los
endpoints de la web. No escribe nada en los trabajos (la web corre sobre una carpeta temporal). Termina con error si
alguna falla.
uso: python pruebas/probar_proyector.py
  A. PAE (EPLAN, hoja de bandejas): los 4 orificios son las tuercas de las esquinas de la placa principal; forman un
     rectangulo de 700 x 845 mm (placa de 735 x 870 mm), aunque la canaleta tape parte de la tuerca de arriba a la
     izquierda.
  B. Mediatrices: el centro de circulos concentricos recortados y de un hexagono se recupera exacto.
  C. Sin orificios dibujados (placa vacia): se usan las esquinas de la placa y se avisa; con 3 de 4 se completa el que
     falta por simetria.
  D. Web: GET /api/trabajo/<id>/proyector da la bandeja y los orificios; PUT guarda calibracion y ventana sin tocar el
     resto del instructivo; PUT /instructivo (la ventana principal) conserva la seccion 'proyector'; /proyector/<id>
     sirve la pestaña."""
import os, sys, json, math, shutil, tempfile
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'programa'))
sys.stdout.reconfigure(encoding='utf-8')
import proyector

PDF = os.path.join(RAIZ, '1 - Planos', 'Producto nuevo', 'ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.pdf')
fallas = []


def chequear(ok, msg):
    print(('  ok    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)


print('A. PAE: orificios de la placa principal (hoja de bandejas)')
from core import process
import topo, instructivo
res = process(PDF, log=lambda m: None)
lay = topo.layout(PDF, instructivo.known_tags(res), log=lambda m: None)
o = proyector.orificios(PDF, lay['pag'], lay['region'], lay['escala'])
print('    ', o)
chequear(o['fuente'] == 'dibujo' and len(o['puntos']) == 4, 'se encontraron los 4 orificios en el dibujo')
p = o['puntos']
mm = lambda a, b: math.dist(a, b) * lay['escala']
chequear(abs(mm(p[0], p[1]) - 700) < 1.5 and abs(mm(p[3], p[2]) - 700) < 1.5, f'separación horizontal 700 mm ({mm(p[0], p[1]):.1f} / {mm(p[3], p[2]):.1f})')
chequear(abs(mm(p[0], p[3]) - 845) < 1.5 and abs(mm(p[1], p[2]) - 845) < 1.5, f'separación vertical 845 mm ({mm(p[0], p[3]):.1f} / {mm(p[1], p[2]):.1f})')
r = lay['region']
chequear(all(r[0] <= q[0] <= r[2] and r[1] <= q[1] <= r[3] for q in p), 'los 4 orificios caen dentro de la placa')
chequear(abs(p[0][0] - p[3][0]) < 0.3 and abs(p[1][0] - p[2][0]) < 0.3 and abs(p[0][1] - p[1][1]) < 0.3 and abs(p[3][1] - p[2][1]) < 0.3,
         'forman un rectángulo (misma x por columna, misma y por fila, a menos de 0,3 pt)')
chequear(not o['avisos'], f'sin avisos ({o["avisos"]})')

print('B. mediatrices: circulos concentricos recortados y hexagono')


def circulo(cx, cy, r, n=24, desde=0, hasta=360):
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in [desde + (hasta - desde) * i / n for i in range(n + 1)]]
    return list(zip(pts, pts[1:]))


segs = circulo(100, 50, 4) + circulo(100, 50, 2.5, desde=0, hasta=250) + circulo(100, 50, 7, n=6)   # el de 2,5 recortado; el de 7 es un hexagono
c = proyector.centro_por_mediatrices(segs)
chequear(c is not None and abs(c[0] - 100) < 0.05 and abs(c[1] - 50) < 0.05, f'centro {c} ≈ (100, 50)')

print('C. placa sin orificios y placa con 3 de 4')
region = [0, 0, 500, 400]
placa = [((0, 0), (500, 0)), ((500, 0), (500, 400)), ((500, 400), (0, 400)), ((0, 400), (0, 0))]
o = proyector.orificios(None, 1, region, 1.0, segs=placa)
chequear(o['fuente'] == 'esquinas' and o['puntos'] == [[0, 400], [500, 400], [500, 0], [0, 0]] and o['avisos'], 'sin símbolos: esquinas de la placa y aviso')
tres = placa + circulo(10, 390, 4) + circulo(490, 390, 4) + circulo(490, 10, 4)      # falta abajo a la izquierda
o = proyector.orificios(None, 1, region, 1.0, segs=tres)
chequear(o['fuente'] == 'dibujo' and len(o['puntos']) == 4, 'con 3 símbolos se arma igual')
chequear(abs(o['puntos'][3][0] - 10) < 0.1 and abs(o['puntos'][3][1] - 10) < 0.1, f'el que falta se completa por simetría: {o["puntos"][3]} ≈ (10, 10)')
chequear(any('simetría' in a for a in o['avisos']), 'y se avisa')
o = proyector.orificios(None, 1, None, 1.0, segs=[])
chequear(o['puntos'] == [] and o['fuente'] == 'esquinas', 'sin placa: sin puntos')

print('D. web: endpoints del proyector sobre una copia temporal de un trabajo')
tmp = tempfile.mkdtemp(prefix='planocables_proy_')
try:
    os.environ['PLANOCABLES_HISTORIAL'] = tmp
    os.environ['PLANOCABLES_PORT'] = '8799'
    import web
    jid = 'abcdef012345'
    d = os.path.join(tmp, jid); os.makedirs(d)
    json.dump(dict(id=jid, nombre='prueba.pdf', archivo='plano.pdf', estado='terminado', eplan=True, topo_nombre='bandejas'), open(os.path.join(d, 'estado.json'), 'w', encoding='utf-8'))
    shutil.copyfile(PDF, os.path.join(d, 'topografico.pdf'))
    ins = dict(pasos=[dict(titulo='Riel 1', lineas=[dict(num='1', origen='A 1', destino='LI', hecho=False)])], pendientes=[], estacion='E6',
               topo=dict(pag=lay['pag'], region=lay['region'], escala=lay['escala'], ductos=lay['ductos'], filas=lay['filas']))
    json.dump(ins, open(os.path.join(d, 'instructivo.json'), 'w', encoding='utf-8'))
    json.dump(dict(comp={'11PS1': dict(ubic='BANDEJA', x=600, y=700), 'PT001': dict(ubic='LI', estacion='E8', x=1000, y=400)}), open(os.path.join(d, 'layout.json'), 'w', encoding='utf-8'))
    cl = web.app.test_client()
    host = {'Host': 'localhost:8799'}
    r = cl.get(f'/proyector/{jid}', headers=host)
    chequear(r.status_code == 200 and b'proyector.js?v=' in r.data, 'GET /proyector/<id> sirve la pestaña con los .js versionados')
    chequear(cl.get('/proyector/zzzzzzzzzzzz', headers=host).status_code == 404, 'GET /proyector/<id> de un trabajo que no existe: 404')
    r = cl.get(f'/api/trabajo/{jid}/proyector', headers=host)
    j = r.get_json()
    chequear(r.status_code == 200 and j['topo']['region'] == lay['region'] and len(j['topo']['ductos']) == len(lay['ductos']), 'GET /api/.../proyector: bandeja (región y canaletas)')
    chequear(j['orificios']['fuente'] == 'dibujo' and j['orificios']['puntos'] == p, 'GET /api/.../proyector: orificios del dibujo (los mismos que en A)')
    chequear(set(j['comp']) == {'11PS1', 'PT001'} and j['comp']['PT001']['x'] == 1000, 'GET /api/.../proyector: aparatos con su posición (para la zona libre)')
    guardado = json.load(open(os.path.join(d, 'instructivo.json'), encoding='utf-8'))
    chequear(guardado.get('proyector', {}).get('orificios_auto', {}).get('puntos') == p, 'los orificios quedan guardados en instructivo.json (proyector.orificios_auto)')
    cal = dict(dst=[[10, 10], [900, 12], [905, 600], [8, 598]], pantalla=[1920, 1080])
    r = cl.put(f'/api/trabajo/{jid}/proyector', json=dict(calibracion=cal, ventana=dict(x=1, y=2, w=300, h=200)), headers=host)
    chequear(r.status_code == 200, 'PUT /api/.../proyector guarda')
    j = cl.get(f'/api/trabajo/{jid}/proyector', headers=host).get_json()
    chequear(j['calibracion'] == cal and j['ventana']['w'] == 300, 'y se vuelve a leer la calibración y la ventana')
    r = cl.put(f'/api/trabajo/{jid}/proyector', json=dict(orificios_usuario=[[1, 2], [3, 4], [5, 6], [7, 8]], pasos='no'), headers=host)
    j = cl.get(f'/api/trabajo/{jid}/proyector', headers=host).get_json()
    chequear(j['orificios_usuario'] == [[1, 2], [3, 4], [5, 6], [7, 8]], 'orificios marcados a mano')
    guardado = json.load(open(os.path.join(d, 'instructivo.json'), encoding='utf-8'))
    chequear(guardado['pasos'] == ins['pasos'] and 'pasos' not in guardado['proyector'], 'el PUT del proyector no toca el resto del instructivo ni acepta otras claves')
    r = cl.put(f'/api/trabajo/{jid}/proyector', json=dict(orificios_usuario=None), headers=host)
    j = cl.get(f'/api/trabajo/{jid}/proyector', headers=host).get_json()
    chequear(j['orificios_usuario'] is None and j['calibracion'] == cal, 'null borra los orificios a mano y deja la calibración')
    chequear(cl.put(f'/api/trabajo/{jid}/proyector', json=[1, 2], headers=host).status_code == 400, 'PUT con datos inválidos: 400')
    # la ventana principal guarda el instructivo entero sin la seccion proyector (o con una vieja): se conserva la del disco
    otro = dict(ins, editado=False, pasos=[dict(titulo='Riel 1', lineas=[dict(num='1', origen='A 1', destino='LI', hecho=True)])], proyector={'calibracion': 'vieja'})
    r = cl.put(f'/api/trabajo/{jid}/instructivo', json=otro, headers=host)
    guardado = json.load(open(os.path.join(d, 'instructivo.json'), encoding='utf-8'))
    chequear(r.status_code == 200 and guardado['pasos'][0]['lineas'][0]['hecho'] is True, 'PUT /instructivo guarda las marcas')
    chequear(guardado['proyector']['calibracion'] == cal and guardado['proyector']['ventana']['w'] == 300, 'y conserva la calibración del proyector guardada en el disco')
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fallas:
    print(f'{len(fallas)} FALLA(S):')
    for f in fallas:
        print(' -', f)
    sys.exit(1)
print('TODO OK')
