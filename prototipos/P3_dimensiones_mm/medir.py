"""Herramienta para CARGAR UN MODELO NUEVO en la base: mide en milimetros la posicion de los tornillos /
bocas respecto de la esquina superior izquierda del cuerpo.

Dos formas:

 1) Sobre la HOJA DE DATOS del fabricante (PDF vectorial con la vista frontal acotada, p. ej. MEAN WELL):
      python medir.py hoja <hoja.pdf> <pagina> <x0> <y0> <x1> <y1> --ancho_mm 32
    (x0 y0 x1 y1 = recuadro de la vista frontal en puntos PDF, origen abajo a la izquierda; se puede sacar
     abriendo la hoja y mirando la regla, o probando.)  La escala sale del ancho acotado del cuerpo.

 2) Sobre el BLOQUE CAD tal como aparece en un topografico (el bloque que usa el dibujante):
      python medir.py plano <topografico.pdf> <pagina> <x_etiqueta> <y_etiqueta> --ancho_mm 6.2 --alto_mm 93
          [--escala 1.4086] [--pieza 1]
    Busca el cuerpo (o la pieza N) a la derecha de la etiqueta con esas medidas y lista lo que hay adentro.

La salida son filas listas para copiar en datos/bornes.csv (poniendo el nombre del borne a mano):
    modelo;nombre;x_mm;y_mm;radio_mm;lado;fuente
y un PNG (medir_control.png) con cada circulo numerado para saber cual es cual.
"""
import argparse, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from geometria import Plano


def _tramo_mas_largo(P, xl, y0, y1, hueco=0.8):
    iv = sorted((v[1], v[2]) for v in P.vseg if abs(v[0] - xl) < 0.06 and v[2] > y0 and v[1] < y1)
    tramos, (cs, ce) = [], iv[0]
    for s_, e_ in iv[1:]:
        if s_ > ce + hueco:
            tramos.append((cs, ce)); cs, ce = s_, e_
        else:
            ce = max(ce, e_)
    tramos.append((cs, ce))
    return max(tramos, key=lambda t: t[1] - t[0])


def cuerpo_hoja(P, x0, y0, x1, y1):
    """Cuerpo de la vista frontal: los lados verticales extremos del recuadro, en su tramo continuo mas largo
    (las lineas de referencia de las cotas quedan cortadas por un hueco), ajustado a las horizontales."""
    lados = [l for l in P.lados_verticales(x0, x1, y0, y1) if (l['y1'] - l['y0']) > 0.6 * (y1 - y0)]
    if len(lados) < 2:
        raise SystemExit('No encontre dos lados verticales largos en el recuadro')
    a, b = lados[0], lados[-1]
    ta, tb = _tramo_mas_largo(P, a['x'], y0, y1), _tramo_mas_largo(P, b['x'], y0, y1)
    yb, yt = max(ta[0], tb[0]), min(ta[1], tb[1])
    w = b['x'] - a['x']
    hs = [h[0] for h in P.hseg if h[1] <= a['x'] + 0.15 * w and h[2] >= b['x'] - 0.15 * w]
    top = [h for h in hs if abs(h - yt) < 0.8]
    bot = [h for h in hs if abs(h - yb) < 0.8]
    yt = max(top) if top else yt
    yb = min(bot) if bot else yb
    return dict(x0=a['x'], x1=b['x'], y0=yb, y1=yt)


def listar(P, c, escala, margen, pdf, pagina, rmin, rmax):
    print('Cuerpo en pt: x %.2f..%.2f  y %.2f..%.2f  ->  %.2f x %.2f mm (escala %.4f mm/pt)' % (
        c['x0'], c['x1'], c['y0'], c['y1'], (c['x1'] - c['x0']) * escala, (c['y1'] - c['y0']) * escala, escala))
    circ = P.circulos(c['x0'] - margen, c['y0'] - margen, c['x1'] + margen, c['y1'] + margen, rmin, rmax)
    print('\n n   x_mm    y_mm   radio_mm   (x desde el borde izquierdo, y desde el borde de ARRIBA)')
    for i, (cx, cy, r, cob) in enumerate(circ, 1):
        print('%2d %7.2f %7.2f %7.2f      [pt %.2f %.2f]' % (i, (cx - c['x0']) * escala, (c['y1'] - cy) * escala, r * escala, cx, cy))
    try:
        import pypdfium2 as pdfium
        from PIL import ImageDraw
        doc = pdfium.PdfDocument(pdf); pg = doc[pagina]; W, H = pg.get_size(); k = 8
        bx0, by0, bx1, by1 = c['x0'] - margen, c['y0'] - margen, c['x1'] + margen, c['y1'] + margen
        img = pg.render(scale=k, crop=(bx0, by0, W - bx1, H - by1)).to_pil().convert('RGB')
        d = ImageDraw.Draw(img)
        for i, (cx, cy, r, cob) in enumerate(circ, 1):
            X, Y = (cx - bx0) * k, (by1 - cy) * k
            d.ellipse((X - r * k, Y - r * k, X + r * k, Y + r * k), outline=(255, 0, 0), width=2)
            d.text((X + r * k + 2, Y - 6), str(i), fill=(255, 0, 0))
        d.rectangle(((c['x0'] - bx0) * k, (by1 - c['y1']) * k, (c['x1'] - bx0) * k, (by1 - c['y0']) * k), outline=(0, 160, 0), width=2)
        img.save(os.path.join(os.getcwd(), 'medir_control.png'))
        print('\nImagen: medir_control.png')
    except Exception as e:
        print('(sin imagen: %s)' % e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('modo', choices=['hoja', 'plano'])
    ap.add_argument('pdf'); ap.add_argument('pagina', type=int)
    ap.add_argument('nums', nargs='+', type=float)
    ap.add_argument('--ancho_mm', type=float, required=True)
    ap.add_argument('--alto_mm', type=float)
    ap.add_argument('--escala', type=float, default=1.4086)
    ap.add_argument('--pieza', type=int, default=1)
    ap.add_argument('--rmin', type=float, default=0.3); ap.add_argument('--rmax', type=float, default=10)
    a = ap.parse_args()
    if a.modo == 'hoja':
        P = Plano(a.pdf, a.pagina - 1, capas=None)
        x0, y0, x1, y1 = a.nums[:4]
        c = cuerpo_hoja(P, x0, y0, x1, y1)
        escala = a.ancho_mm / (c['x1'] - c['x0'])
        listar(P, c, escala, 3, a.pdf, a.pagina - 1, a.rmin, a.rmax)
    else:
        P = Plano(a.pdf, a.pagina - 1)
        tx, ty = a.nums[:2]
        riel = P.riel_de(tx, ty)
        W, H = a.ancho_mm / a.escala, (a.alto_mm or 80) / a.escala
        ps = [p for p in P.piezas(tx - W, tx + 40 * W, riel['y'], W, H) if p['x1'] > tx - 0.5 * W and not p['verde']]
        if not ps:
            raise SystemExit('No encontre un cuerpo de esas medidas cerca de la etiqueta')
        c = ps[min(a.pieza, len(ps)) - 1]
        listar(P, c, a.escala, 1.0, a.pdf, a.pagina - 1, a.rmin, a.rmax)


if __name__ == '__main__':
    main()
