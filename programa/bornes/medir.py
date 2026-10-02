# -*- coding: utf-8 -*-
"""Ayuda para AGREGAR UN MODELO al catalogo: mide las formas que hay en la zona de una etiqueta del topografico.

uso:
    python medir.py <topografico.pdf> <usos_por_componente.json> <TAG> [--alto_mm 100] [--png zona.png]

Toma la zona del TAG como la toma motor.py (a la derecha de la etiqueta amarilla hasta la etiqueta siguiente del
mismo riel; si el tag no esta en un riel, un cuadrado alrededor de la etiqueta) y lista, en MILIMETROS del tablero:
  - los circulos (radio, cantidad, columnas en x y paso entre columnas),
  - los contornos cerrados convexos (ancho x alto, cantidad),
  - los tornillos cortados (elipses abiertas de las barreras).
Con eso se completan 'boca' (primitiva y rango de tamano), 'paso_mm' y 'alto_mm' de la entrada nueva de catalogo.json.
Con --png guarda un render ampliado de la zona para mirarlo.
"""
import sys
import os
import json
import math
from collections import Counter, defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import motor as M  # noqa: E402
import primitivas as P  # noqa: E402


def main(argv):
    args, opts, i = [], {}, 1
    while i < len(argv):
        if argv[i].startswith('--') and i + 1 < len(argv):
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    if len(args) < 3:
        print(__doc__)
        return 2
    pdf, usos_path, tag = args[:3]
    usos = json.load(open(usos_path, encoding='utf-8'))
    cat = json.load(open(os.path.join(AQUI, 'catalogo.json'), encoding='utf-8'))
    if tag not in usos['componentes']:
        print(f'{tag} no esta en {usos_path}. Tags: {", ".join(usos["componentes"])}')
        return 1
    motor = M.Motor(pdf, usos, cat, {})
    alto = float(opts.get('alto_mm', 100))
    ficticio = dict(id='medir', alto_mm=alto, ancho_mm=alto, anclaje='izquierda' if motor.riel.get(tag) else 'libre')
    caja, yc = motor.zona(tag, ficticio)
    mm = motor.esc
    print(f'{tag}: zona x {caja[0]:.1f}-{caja[2]:.1f} pt, y {caja[1]:.1f}-{caja[3]:.1f} pt '
          f'({(caja[2] - caja[0]) * mm:.1f} x {(caja[3] - caja[1]) * mm:.1f} mm); riel en y {yc:.1f}')
    # circulos
    arcs = [a for a in motor.arcos if caja[0] <= a[0] <= caja[2] and caja[1] <= a[1] <= caja[3]]
    cs = [c for c in P.circulos(arcs, 0.3 / mm, 15.0 / mm, cob_min=250) if caja[0] <= c['x'] <= caja[2] and caja[1] <= c['y'] <= caja[3]]
    por_r = defaultdict(list)
    for c in cs:
        por_r[round(c['r'] * mm * 10) / 10].append(c)
    print('\nCIRCULOS (radio mm: cantidad | columnas x en pt | paso mm | filas y en pt)')
    for r in sorted(por_r):
        lst = por_r[r]
        xs = sorted({round(c['x'], 1) for c in lst})
        ys = sorted({round(c['y'], 1) for c in lst}, reverse=True)
        pasos = [round((b - a) * mm, 2) for a, b in zip(xs, xs[1:]) if (b - a) * mm > 1]
        paso = Counter(pasos).most_common(1)[0][0] if pasos else '-'
        cruz = sum(1 for c in lst if motor.esc_.tiene_x(c['x'], c['y'], c['r']))
        print(f'  r {r:4.1f} mm: {len(lst):3d} | x {xs[:12]}{" ..." if len(xs) > 12 else ""} | paso {paso} | '
              f'y {ys[:8]}{" ..." if len(ys) > 8 else ""}' + (f' | {cruz} con cruz en X (tope)' if cruz else ''))
    # contornos
    cont = motor.esc_.contornos(caja)
    por_t = Counter((round(c['w'] * mm * 2) / 2, round(c['h'] * mm * 2) / 2, c['curvos'] >= 8) for c in cont
                    if min(c['w'], c['h']) * mm >= 1.0)
    print('\nCONTORNOS CERRADOS (ancho x alto mm, redondeado a 0,5: cantidad; "curvo" = esquinas redondeadas)')
    for (w, h, cur), n in sorted(por_t.items(), key=lambda kv: -kv[1])[:25]:
        print(f'  {w:5.1f} x {h:5.1f}{" curvo" if cur else ""}: {n}')
    # tornillos cortados
    cur = [c for c in motor.curvas if caja[0] <= c[1][0] and c[1][2] <= caja[2] and caja[1] <= c[1][1] and c[1][3] <= caja[3]]
    tc = P.tornillos_cortados(cur, ancho=(2.5 / mm, 8.0 / mm), alto_max=8.0 / mm)
    if tc:
        print('\nTORNILLOS CORTADOS (ancho x alto mm: posicion pt)')
        for t in sorted(tc, key=lambda t: (-t['y'], t['x']))[:30]:
            print(f'  {t["w"] * mm:4.1f} x {t["h"] * mm:4.1f}: ({t["x"]:.1f}, {t["y"]:.1f})')
    if opts.get('png'):
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf)
        pg = doc[motor.pagina]
        W, H = pg.get_size()
        esc = min(14.0, 1600 / max(1.0, caja[2] - caja[0]))
        pg.render(scale=esc, crop=(caja[0], caja[1], W - caja[2], H - caja[3])).to_pil().save(opts['png'])
        print(f'\nrender de la zona: {opts["png"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
