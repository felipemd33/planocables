"""Arma (o rearma) las plantillas de imagen de la base a partir de base/recortes.json.

uso:  python hacer_base.py [recortes.json] [carpeta_base]
      (por defecto base/recortes.json -> base/plantillas/*.png + base/plantillas.json)

Para cada entrada de recortes.json: renderiza el plano, busca el centro exacto de la boca cerca del 'clic'
(solo mirando la imagen, ver vision.anclar), recorta 'recorte_pt' alrededor y guarda el PNG en gris con su ancla.
Las plantillas de tipo 'aparato' (aparatos sin tornillos dibujados, como el toma IRAM) guardan el recorte del
aparato entero y varias anclas con nombre.
"""
import json
import os
import sys

import cv2
import numpy as np

import vision

AQUI = os.path.dirname(os.path.abspath(__file__))


def caja_aparato(plano, aprox, tol=0.8):
    """Caja exterior del aparato a partir de una caja aproximada [x0, y0, x1, y1] marcada a ojo:
    cada borde se "pega" a la raya mas fuerte (la columna o fila con mas tinta) a menos de tol pt."""
    s = vision.S
    x0, y0, x1, y1 = aprox
    z = plano.zona(x0 - tol - 1, y0 - tol - 1, x1 + tol + 1, y1 + tol + 1, s=s)
    ink = (z.gris < 170).astype(np.float32)
    j0, i1 = z.px(x0, y0); j1, i0 = z.px(x1, y1)
    j0, j1, i0, i1 = int(j0), int(j1), int(i0), int(i1)
    col = ink[i0:i1, :].mean(axis=0)   # tinta por columna dentro del alto de la caja
    fil = ink[:, j0:j1].mean(axis=1)   # tinta por fila dentro del ancho de la caja
    t = int(tol * s)

    def pegar(perfil, c):
        a, b = max(0, c - t), min(len(perfil), c + t + 1)
        return a + int(np.argmax(perfil[a:b])) + 0.5

    ja, jb = pegar(col, j0), pegar(col, j1)
    ia, ib = pegar(fil, i0), pegar(fil, i1)
    xa, ya = z.pt(ja, ia); xb, yb = z.pt(jb, ib)
    return z, (xa, yb, xb, ya)


def banda_inferior(plano, caja):
    """Altura media de la banda de abajo del aparato: se mira una franja angosta pegada al borde izquierdo
    y se buscan las dos primeras rayas horizontales desde abajo (borde exterior y borde de la banda)."""
    xa, yb, xb, ya = caja
    s = vision.S
    z = plano.zona(xa + 0.2, yb - 0.5, xa + 1.0, yb + 8, s=s)
    ink = (z.gris < 170).mean(axis=1) > 0.5
    filas = np.flatnonzero(ink)
    runs = []
    for f in filas[::-1]:  # de abajo hacia arriba
        if runs and runs[-1][0] - f <= 1:
            runs[-1][0] = f
        else:
            runs.append([f, f])
    if len(runs) < 2:
        return yb + 1.5
    c = [z.pt(0, (a + b + 1) / 2)[1] for a, b in runs[:2]]
    return (c[0] + c[1]) / 2


def main():
    rec_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, 'base', 'recortes.json')
    base = sys.argv[2] if len(sys.argv) > 2 else os.path.join(AQUI, 'base')
    rec = json.load(open(rec_path, encoding='utf-8'))
    plano = vision.Plano(rec['plano']['pdf'], rec['plano']['pagina'] - 1)
    os.makedirs(os.path.join(base, 'plantillas'), exist_ok=True)
    idx = {}
    for p in rec['plantillas']:
        nombre = p['nombre']
        if p.get('tipo') == 'aparato':
            z, caja = caja_aparato(plano, p['caja_aprox'])
            xa, yb, xb, ya = caja
            yb_banda = banda_inferior(plano, caja) if p.get('anclas_y') == 'banda_inferior' else (yb + ya) / 2
            m = 1.0
            g, _ = vision.recortar(plano, (xa + xb) / 2, (yb + ya) / 2, xb - xa + 2 * m, ya - yb + 2 * m)
            zz = plano.zona((xa + xb) / 2 - (xb - xa + 2 * m) / 2, (yb + ya) / 2 - (ya - yb + 2 * m) / 2,
                            (xa + xb) / 2 + (xb - xa + 2 * m) / 2, (yb + ya) / 2 + (ya - yb + 2 * m) / 2)
            anclas = {}
            for k, f in p['anclas_frac'].items():
                x = xa + f * (xb - xa)
                anclas[k] = [round(v, 2) for v in zz.px(x, yb_banda)]
            cx, cy = (xa + xb) / 2, (yb + ya) / 2
            ancla = [round(v, 2) for v in zz.px(cx, cy)]
            info = dict(caja_pt=[round(v, 2) for v in caja], y_banda_pt=round(yb_banda, 2),
                        anclas_px=anclas, anclas_pt={k: [round(xa + f * (xb - xa), 2), round(yb_banda, 2)] for k, f in p['anclas_frac'].items()})
            g = zz.gris
        else:
            cx, cy, bw, bh, (zm, mancha) = vision.anclar(plano, p['clic'][0], p['clic'][1], p['r_pt'],
                                                         modo=p.get('ancla', 'contorno'), con_mancha=True)
            g, anc = vision.recortar(plano, cx, cy, p['recorte_pt'][0], p['recorte_pt'][1])
            ancla = [round(v, 2) for v in anc]
            info = dict(boca_pt=[round(bw, 2), round(bh, 2)])
            if p.get('mascara', True):
                # mascara = la mancha de la boca, engordada un poco: la plantilla solo compara lo de adentro
                # de la boca y no se confunde con lo que la rodea (tope negro, pieza vecina)
                d = int(round(p.get('mascara_margen_pt', 0.3) * vision.S))
                mancha = cv2.dilate(mancha, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * d + 1, 2 * d + 1)))
                # la mancha esta en la zona zm; se lleva a la grilla del recorte
                zr = plano.zona(cx - p['recorte_pt'][0] / 2, cy - p['recorte_pt'][1] / 2, cx + p['recorte_pt'][0] / 2, cy + p['recorte_pt'][1] / 2)
                mm = np.zeros_like(g, np.uint8)
                oj = int(round((zr.x0 - zm.x0) * vision.S)); oi = int(round((zm.y1 - zr.y1) * vision.S))
                for i in range(mm.shape[0]):
                    si = i + oi
                    if 0 <= si < mancha.shape[0]:
                        for_j = np.arange(mm.shape[1]) + oj
                        ok = (for_j >= 0) & (for_j < mancha.shape[1])
                        mm[i, ok] = mancha[si, for_j[ok]]
                mpng = f'plantillas/{nombre}_mascara.png'
                cv2.imwrite(os.path.join(base, mpng), mm * 255)
                info['mascara_png'] = mpng
        png = f'plantillas/{nombre}.png'
        cv2.imwrite(os.path.join(base, png), g)
        idx[nombre] = dict(png=png, ancla_px=ancla, px_por_pt=vision.S, r_pt=p['r_pt'], tipo=p.get('tipo', 'boca'),
                           origen=dict(plano=rec['plano']['nombre'], pagina=rec['plano']['pagina'], tag=p['tag'], que=p['que'],
                                       centro_pt=[round(cx, 2), round(cy, 2)]), **info)
        print(f"{nombre:22s} tag {p['tag']:7s} centro ({cx:.2f}, {cy:.2f})  {g.shape[1]}x{g.shape[0]} px")
    json.dump(dict(descripcion='Indice de plantillas (generado por hacer_base.py desde ' + os.path.basename(rec_path) + ')',
                   mm_por_pt=rec['plano'].get('mm_por_pt'), plantillas=idx), open(os.path.join(base, 'plantillas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    vista(base, idx)


def vista(base, idx, alto=260):
    """base/plantillas_vista.png: todas las plantillas ampliadas, con el centro (ancla) en rojo, el borde de la
    mascara en verde y el nombre y el tag de donde salio cada una. Sirve para revisar la base de un vistazo."""
    F = cv2.FONT_HERSHEY_SIMPLEX
    fichas = []
    for nombre, d in idx.items():
        g = cv2.imread(os.path.join(base, d['png']), cv2.IMREAD_GRAYSCALE)
        f = alto / g.shape[0]
        im = cv2.cvtColor(cv2.resize(g, (int(round(g.shape[1] * f)), alto), interpolation=cv2.INTER_NEAREST if f >= 1 else cv2.INTER_AREA),
                          cv2.COLOR_GRAY2BGR)
        if d.get('mascara_png'):
            m = cv2.imread(os.path.join(base, d['mascara_png']), cv2.IMREAD_GRAYSCALE)
            m = cv2.resize(m, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST)
            cs, _ = cv2.findContours((m > 127).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(im, cs, -1, (0, 170, 0), 2)
        puntos = [d['ancla_px']] + list(d.get('anclas_px', {}).values())
        for (ax, ay) in puntos:
            c = (int(round(ax * f)), int(round(ay * f)))
            cv2.drawMarker(im, c, (0, 0, 230), cv2.MARKER_CROSS, 18, 2)
        ancho = max(im.shape[1], 230)
        ficha = np.full((alto + 58, ancho + 10, 3), 255, np.uint8)
        ficha[5:5 + alto, 5:5 + im.shape[1]] = im
        cv2.putText(ficha, nombre, (5, alto + 25), F, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(ficha, f"de {d['origen']['tag']}  r {d['r_pt']} pt", (5, alto + 47), F, 0.45, (90, 90, 90), 1, cv2.LINE_AA)
        fichas.append(ficha)
    filas, fila, w = [], [], 0
    for fi in fichas:
        if fila and w + fi.shape[1] > 1600:
            filas.append(fila); fila, w = [], 0
        fila.append(fi); w += fi.shape[1]
    if fila:
        filas.append(fila)
    W = max(sum(f.shape[1] for f in fl) for fl in filas)
    bloques = []
    for fl in filas:
        b = np.hstack(fl)
        bloques.append(np.hstack([b, np.full((b.shape[0], W - b.shape[1], 3), 255, np.uint8)]))
    cab = np.full((30, W, 3), 255, np.uint8)
    cv2.putText(cab, 'Plantillas de la base P5 (una por tipo de boca). Cruz roja = centro del borne; verde = mascara.', (6, 20), F, 0.55,
                (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(base, 'plantillas_vista.png'), np.vstack([cab] + bloques))


if __name__ == '__main__':
    main()
