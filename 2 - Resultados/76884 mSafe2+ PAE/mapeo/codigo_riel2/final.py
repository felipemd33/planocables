import json, sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8')
OUTD = r'C:/Buscar Termos en plano/2 - Resultados/76884 mSafe2+ PAE/mapeo'
d = json.load(open('puntos_tmp.json', encoding='utf-8'))
ZONA = ['12XP', '13X12V', '13X24V', '61XDO', '61X0V', '61XDIO', '15AIB1', '15DIB1', '15DIB2', '15DIB3']


def key(p):
    parts = p['d'].lstrip('-').split(':')
    n = int(parts[1]); q = int(parts[2]) if len(parts) > 2 else (0 if p['lado'] == 'ARRIBA' else 1)
    return (ZONA.index(p['tag']), n, q, p['cables'][0])


pts = sorted(d['puntos'], key=key)
dudas = [
    "15AIB1 1 y 2 (1370 y 1361, cadena de alimentacion de las barreras): el enchufe de alimentacion [1 2] de la GS8536-EX NO esta dibujado en la pag. 8 (el bloque EPLAN dibuja solo las filas [3 4 5] y [6 7 8] arriba). Lo ubique detras del [3 4 5], a la misma altura que su tornillo (regla de la vista lateral del manual, usada en el 75286 y el 66817), con 2 bornes a paso 5,0 mm centrados en la carcasa: x = 825.56 / 829.10. Confianza media; confirmar con la barrera real.",
    "15DIB1, 15DIB2, 15DIB3 1 y 2: en la GS8512-EX.22 el enchufe [1 2] queda detras del [3 4], asi que de frente el 1 cae en el mismo punto que el 3 y el 2 en el mismo que el 4 (no es boca compartida: son dos enchufes). Confianza media, igual que en la referencia del 75286.",
    "Cadena 1370 / 1361: en 15AIB1:1, 15DIB1:1 y 15DIB2:1 (y en los :2) entran 2 conductores del mismo cable (llega uno y sale otro hacia la barrera siguiente): puntera doble de 2 x 1 mm2 en un tornillo M3 (admite 0,5-2,5 mm2). En 15DIB3:1 y :2 termina la cadena (1 conductor). Cada (designacion, cable) es un solo punto con n_conductores = 2.",
    "15DIB3: las hojas 15 y 41 dicen 'se deja previsto el cableado SIN la barrera, se reemplaza por bornes tipo cuchilla abiertos', pero la pag. 8 dibuja la barrera y la lista de conexiones lleva 1370, 1361, 2124-2127 y 4124-4127 a 15DIB3:x. Mapee los 10 puntos en la barrera dibujada (confianza media). Si se monta con bornes cuchilla, hay que saber su tag, su ubicacion y su numeracion para rehacer esos puntos.",
    "61XDIO: EPLAN no da el punto (-61XDIO:N en los dos extremos de cada cable). El lado sale del cable: 1264 (desde 12XP 2.3, 0 V) entra al ANODO, que es el lado del puente FBS 4-5 BU = fisicamente ABAJO (el puente esta dibujado en la mitad de abajo en la pag. 8 y en la vista 3D de la hoja de hileras); 6171-6174 salen del CATODO = ARRIBA hacia 61XDO N.2. En la hoja 61 el anodo esta a la izquierda (el funcional diria 'ARRIBA'): el texto lleva el lado fisico ('61XDIO 1 ABAJO' para 1264, '61XDIO 1 ARRIBA' para 6171).",
    "Puntas con el otro extremo en E8 (zona hidraulica / empalmes X1, se cablean en el gabinete): 1339 en 13X24V 2.2 y 1340 en 13X24V 4.3 (van a los empalmes X1 del cable de LS001A) y 6151 en 61XDO 1.4 (va a BH_01_ZV A1). Estan mapeadas como puntas de esta zona, con otro_extremo_estacion = 'E8'.",
    "13X24V tiene una tapa D-PT 6-QUATTRO entre las piezas 2 y 3 (hoja de hileras pag. 34: 1, FBS 2-8 rojo, 2, tapa, 3, FBS 2-8 BU, 4). Por eso las piezas 3 y 4 quedan 1,55 pt mas a la derecha y los 'xc' repartidos parejos de bandejas.json (671.21 / 677.38 / 683.54 / 689.70) difieren hasta 0,6 pt de las bocas reales (671.00 / 676.77 / 684.11 / 689.88). Usar las x de este archivo.",
    "Bocas libres (sin cable en la lista): 12XP pieza 3 completa (puenteada con FBS 3-8 BU a 1 y 2), 12XP 2.1 y 2.2; 13X24V 1.2, 1.3, 3.2 y 3.3; 61X0V 1.2, 1.3, 2.1 y 2.2; 15AIB1 5, 8, 11 y 14. No es un error: son bornes de reserva o puenteados.",
    "Regla N.p de los QUATTRO: el punto EPLAN p se toma como la boca de la regla del taller (1 arriba extremo, 2 arriba interior, 3 abajo interior, 4 abajo extremo). El bloque es simetrico; el simbolo del esquema (hojas 12, 13 y 61) dibuja los puntos 1-2-3-4 en ese orden y la lista de conexiones coincide. Si EPLAN Pro Panel tiene otra posicion 3D de los puntos, la hoja 8 no la muestra.",
]
geom = {
    'QUATTRO_y_bocas': {'1 ARRIBA extremo': 541.93, '2 ARRIBA interior': 530.31, '3 ABAJO interior': 499.43, '4 ABAJO extremo': 487.81, 'r': 2.5},
    'QUATTRO_x_piezas': {'12XP': [625.54, 631.31, 637.09], '13X12V': [651.16, 656.93], '13X24V': [671.0, 676.77, 684.11, 689.88],
                         '61XDO': [703.95, 709.73, 715.5, 721.28], '61X0V': [735.35, 741.12]},
    'DIO': {'x': [754.2, 757.85, 761.5, 765.14], 'y_arriba_catodo': 528.88, 'y_abajo_anodo': 502.45, 'r': 1.6},
    'barreras_tornillos': {'x': {'15AIB1': [823.79, 827.33, 830.87], '15DIB1': [836.26, 839.8], '15DIB2': [845.12, 848.66], '15DIB3': [853.98, 857.52]},
                           'y': {'arriba_exterior': 551.17, 'arriba_interior': 544.8, 'abajo_interior': 486.23, 'abajo_exterior': 479.86}, 'r': 1.4},
    'metodo': 'page_strokes de la copia sin proteccion (76884_proc.pdf, pagina indice 7). QUATTRO: tapas superior e inferior (segmentos horizontales de 0,57 pt) del contorno redondeado de cada boca, pareadas a 5,67 pt. DIO: barra de la U (2,13 pt) para x y caja del octogono para y. Barreras: componentes conexos de segmentos con caja de 2,8 x 2,8 pt (aro del tornillo).',
}
res = {'documento': 'ZPL-76884 Rev 1 mSafe2+ PAE, pag. 8 (Detalle bandejas), BANDEJA PRINCIPAL riel 2 (U11 izquierdo y U12 derecho)',
       'unidades': 'pt de la pagina PDF 8, origen abajo-izquierda; r = radio de la boca o del tornillo en pt',
       'zona': ZONA, 'n_puntos': len(pts), 'puntos': pts, 'dudas': dudas, 'geometria': geom}
os.makedirs(OUTD, exist_ok=True)
json.dump(res, open(os.path.join(OUTD, 'puntos_riel2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
os.makedirs(os.path.join(OUTD, 'codigo_riel2'), exist_ok=True)
for f in ('comps.py', 'det_quattro.py', 'det_dio.py', 'build.py', 'control.py', 'final.py', 'strokes.py', 'rend.py'):
    shutil.copy(f, os.path.join(OUTD, 'codigo_riel2', f))
json.dump({'puntos': pts}, open('puntos_final.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print(len(pts), Counter(p['tag'] for p in pts), Counter(p['confianza'] for p in pts))
