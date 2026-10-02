"""Ayuda para agregar un modelo nuevo a la base: mira una zona del plano con una grilla en puntos PDF y, si se
pide, prueba una plantilla de la base en esa zona.

uso:  python ver_zona.py <plano.pdf> <pagina> <x0> <y0> <x1> <y1> [--plantilla NOMBRE] [--salida zona.png]
                         [--variantes normal,espejo_v] [--escala 1.0] [--umbral 0.6] [--px 20]

  <pagina>          numero de pagina del PDF contando desde 1 (en el topografico de prueba, la 8)
  x0 y0 x1 y1       rectangulo en puntos PDF, origen abajo a la izquierda (como usos_por_componente.json)

Sin --plantilla: guarda la zona ampliada con una raya fina cada 1 pt y una raya con numero cada 5 pt. Con esa
imagen se lee el "clic" (el centro aproximado de una boca) para anotarlo en base/recortes.json.
Con --plantilla: ademas busca esa plantilla (cv2.matchTemplate, igual que mapear.py) y marca cada boca
encontrada con un circulo y su parecido (NCC). Sirve para ver si un modelo nuevo se puede buscar con una
plantilla que ya esta en la base, o si hace falta recortar una nueva.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import vision  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pdf')
    ap.add_argument('pagina', type=int)
    ap.add_argument('x0', type=float)
    ap.add_argument('y0', type=float)
    ap.add_argument('x1', type=float)
    ap.add_argument('y1', type=float)
    ap.add_argument('--plantilla', default=None)
    ap.add_argument('--variantes', default='normal')
    ap.add_argument('--escala', type=float, default=1.0)
    ap.add_argument('--umbral', type=float, default=0.6)
    ap.add_argument('--px', type=int, default=20, help='px por punto de la imagen que se guarda (por defecto 20)')
    ap.add_argument('--salida', default='zona.png')
    a = ap.parse_args()

    plano = vision.Plano(a.pdf, a.pagina - 1)
    s = a.px
    z = plano.zona(a.x0, a.y0, a.x1, a.y1, s=s)
    im = z.bgr.copy()
    # grilla: raya fina cada 1 pt, raya marcada con numero cada 5 pt
    for x in np.arange(np.ceil(z.x0), z.x0 + z.w / s, 1.0):
        j = int(round((x - z.x0) * s))
        fuerte = abs(x / 5 - round(x / 5)) < 1e-6
        cv2.line(im, (j, 0), (j, z.h - 1), (200, 120, 0) if fuerte else (235, 215, 190), 1)
        if fuerte:
            cv2.putText(im, f'{x:.0f}', (j + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 120, 0), 1, cv2.LINE_AA)
    y_arriba = z.y1
    for y in np.arange(np.floor(y_arriba), y_arriba - z.h / s, -1.0):
        i = int(round((y_arriba - y) * s))
        fuerte = abs(y / 5 - round(y / 5)) < 1e-6
        cv2.line(im, (0, i), (z.w - 1, i), (200, 120, 0) if fuerte else (235, 215, 190), 1)
        if fuerte:
            cv2.putText(im, f'{y:.0f}', (2, i - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 120, 0), 1, cv2.LINE_AA)

    if a.plantilla:
        idx = json.load(open(os.path.join(AQUI, 'base', 'plantillas.json'), encoding='utf-8'))['plantillas']
        if a.plantilla not in idx:
            sys.exit(f'no existe la plantilla {a.plantilla}; hay: ' + ', '.join(idx))
        pl = vision.Plantilla.cargar(a.plantilla, idx[a.plantilla], os.path.join(AQUI, 'base'))
        zb = plano.zona(a.x0, a.y0, a.x1, a.y1)  # la busqueda va a la resolucion de trabajo (10 px/pt)
        dets = vision.buscar(zb, pl, variantes=tuple(a.variantes.split(',')), escalas=(a.escala,), umbral=a.umbral)
        for d in dets:
            j, i = z.px(d['x'], d['y'])
            c = (0, 160, 0) if d['score'] > 0.8 else (0, 140, 255)
            cv2.circle(im, (int(round(j)), int(round(i))), max(3, int(pl.r_pt * a.escala * s)), c, 2, cv2.LINE_AA)
            cv2.putText(im, f"{d['score']:.2f}", (int(j) + 4, int(i) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, c, 1, cv2.LINE_AA)
        print(f'{len(dets)} bocas con NCC >= {a.umbral}:')
        for d in sorted(dets, key=lambda d: (-d['y'], d['x'])):
            print(f"   x {d['x']:8.2f}  y {d['y']:8.2f}  NCC {d['score']:.2f}  ({d['var']})")
    cv2.imwrite(a.salida, im)
    print('imagen:', os.path.abspath(a.salida))


if __name__ == '__main__':
    main()
