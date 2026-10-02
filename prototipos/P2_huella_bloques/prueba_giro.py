"""Prueba de giro del reconocimiento de bloques (P2).

uso:  python prueba_giro.py <topografico.pdf> <usos_por_componente.json> [salida/prueba_giro.txt]

Gira 90 grados TODO el dibujo de la pagina (como si el bloque estuviera insertado girado en un plano nuevo),
busca otra vez todos los bloques de la base en el dibujo girado y compara con lo hallado en el dibujo sin
girar: mismo modelo, misma posicion (girada) y mismos puntos de borne. Mide solo el reconocimiento vectorial
(huella + transferencia de bornes); la lectura de tags/rieles del taller supone rieles horizontales.
No usa bornes_referencia.json.
"""
import sys, os, time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.dont_write_bytecode = True
import huellas as H
import mapear as MP


def girar_xy(x, y, c):
    """90 grados antihorario alrededor de c."""
    return (c[0] - (y - c[1]), c[1] + (x - c[0]))


def puntos_de_bornes(base, i):
    m = base['modelos'][i['modelo']]
    out = []
    for k, b in m['bornes'].items():
        q = H.transformar([(b['dx'], b['dy'])], i['t'])[0] + (i['cx'], i['cy'])
        out.append((k, float(q[0]), float(q[1])))
    return out


def main():
    t0 = time.time()
    pdf, usos_p = sys.argv[1:3]
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(AQUI, 'salida', 'prueba_giro.txt')
    base = H.cargar_json(os.path.join(AQUI, 'base_bornes.json'))
    usos = H.cargar_json(usos_p)
    pag = int(usos.get('pagina_pdf', 1)) - 1
    reg = usos.get('region_bandeja')
    trazos = H.leer_trazos(pdf, pag)
    P0 = H.Plano(pdf, pag, region=reg, trazos=trazos)
    c = ((P0.region[0] + P0.region[2]) / 2, (P0.region[1] + P0.region[3]) / 2)
    trazos_g = [(lay, op, [girar_xy(x, y, c) for x, y in pts], col) for lay, op, pts, col in trazos]
    a = girar_xy(P0.region[0], P0.region[1], c); b = girar_xy(P0.region[2], P0.region[3], c)
    reg_g = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
    P1 = H.Plano(pdf, pag, region=reg_g, trazos=trazos_g)
    base0 = H.cargar_json(os.path.join(AQUI, 'base_bornes.json'))
    I0 = MP.instancias(P0, base0, P0.region)
    I1 = MP.instancias(P1, base, P1.region)
    L = ['PRUEBA DE GIRO 90 GRADOS (reconocimiento de bloques por huella)', '',
         'Se gira todo el dibujo 90 grados y se buscan de nuevo los bloques de la base.', '']
    ok_inst = ok_b = tot_b = 0
    faltan = []
    por_modelo = {}
    for i in I0:
        gx, gy = girar_xy(i['cx'], i['cy'], c)
        cand = [j for j in I1 if j['modelo'] == i['modelo'] and abs(j['cx'] - gx) < 0.3 and abs(j['cy'] - gy) < 0.3]
        pm = por_modelo.setdefault(i['modelo'], [0, 0, 0, 0])
        pm[0] += 1
        if not cand:
            faltan.append(i)
            continue
        j = cand[0]
        ok_inst += 1; pm[1] += 1
        b0 = [girar_xy(x, y, c) for _, x, y in puntos_de_bornes(base0, i)]
        b1 = [(x, y) for _, x, y in puntos_de_bornes(base, j)]
        for x, y in b0:
            tot_b += 1; pm[3] += 1
            if min(np.hypot(x - u, y - v) for u, v in b1) < 0.2:
                ok_b += 1; pm[2] += 1
    L.append('Instancias sin girar: %d. Reencontradas en el dibujo girado (mismo modelo, ancla a < 0.3 pt): %d.' % (len(I0), ok_inst))
    L.append('Puntos de borne de esas instancias que caen en el mismo lugar (girado, < 0.2 pt): %d/%d.' % (ok_b, tot_b))
    L.append('Instancias nuevas que solo aparecen en el girado: %d.' % max(0, len(I1) - ok_inst))
    L += ['', 'modelo            instancias  reencontradas  bornes ok']
    for mid, (n, r, bo, bt) in sorted(por_modelo.items()):
        L.append('  %-16s %6d %12d %8d/%d' % (mid, n, r, bo, bt))
    if faltan:
        L += ['', 'No reencontradas:'] + ['  %s en (%.2f, %.2f)' % (i['modelo'], i['cx'], i['cy']) for i in faltan]
    L += ['', 'Tiempo: %.1f s' % (time.time() - t0)]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
