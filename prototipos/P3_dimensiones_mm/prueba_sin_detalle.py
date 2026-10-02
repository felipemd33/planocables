"""Prueba: el metodo no necesita el detalle del dibujo (tornillos, bocas, pulsadores).

    python prueba_sin_detalle.py <topografico.pdf> <usos_por_componente.json> <carpeta_salida> [--agresivo]

Lee los trazos de la pagina, BORRA de las capas de componentes todo trazo chico (el recuadro que lo encierra mide
menos de 6 pt = 8.5 mm de lado y no es un tramo recto horizontal o vertical: circulos de tornillo, bocas
push-in, pulsadores, LEDs, cruces, textos...) y corre
mapear.py sobre lo que queda: solo contornos y lineas largas.  Deja en la carpeta:
    bornes.json            puntos calculados sin detalle
    control.png            control (sobre el plano original)
    trazos_sin_detalle.png lo que ve el programa en esta prueba, con los puntos
Con --agresivo borra tambien los tramos rectos cortos, o sea tambien pedazos de los contornos (caso extremo).
Despues se evalua con evaluar.py como cualquier salida.
"""
import os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, 'C:/Buscar Termos en plano/programa')
import mapear  # noqa: E402
from geometria import CAPAS_COMP, bbox  # noqa: E402

LADO_MAX = 6.0


def main():
    pdf, usos, carpeta = sys.argv[1:4]
    agresivo = '--agresivo' in sys.argv     # borra tambien los tramos rectos cortos (se pierden pedazos de contorno)
    os.makedirs(carpeta, exist_ok=True)
    import json, pypdf
    from pdfvec import page_strokes, layer_names
    u = json.load(open(usos, encoding='utf-8'))
    pagina = u.get('pagina_pdf') or 1
    r = pypdf.PdfReader(pdf)
    trazos = page_strokes(r, pagina - 1, layer_names(r), with_color=True)
    quedan, borrados = [], 0
    for t in trazos:
        lay, op, pts, rgb = t
        if lay in CAPAS_COMP and len(pts) >= 2:
            b = bbox(pts)
            recto = len(pts) == 2 and (abs(pts[0][0] - pts[1][0]) < 0.03 or abs(pts[0][1] - pts[1][1]) < 0.03)
            if max(b[2] - b[0], b[3] - b[1]) < LADO_MAX and (agresivo or not recto):
                borrados += 1
                continue
        quedan.append(t)
    print('Trazos de la pagina: %d; borrados por chicos (< %.0f pt): %d; quedan %d' % (len(trazos), LADO_MAX, borrados, len(quedan)))
    a = mapear.argumentos([pdf, usos, os.path.join(carpeta, 'bornes.json'), '--control', os.path.join(carpeta, 'control.png')])
    sal = mapear.mapear(a, trazos=quedan)
    # imagen de lo que queda
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = u.get('region_bandeja') or (0, 0, 1200, 850)
    k = 3.0
    img = Image.new('RGB', (int((x1 - x0) * k), int((y1 - y0) * k)), (255, 255, 255))
    d = ImageDraw.Draw(img)
    X = lambda x: (x - x0) * k
    Y = lambda y: (y1 - y) * k
    for lay, op, pts, rgb in quedan:
        if lay in CAPAS_COMP or 'RIEL' in lay.upper():
            d.line([(X(p[0]), Y(p[1])) for p in pts], fill=(90, 90, 90), width=1)
    for p in sal['puntos']:
        rr = max(2.5, (p.get('r') or 0.5) * k)
        cl = mapear.COLORES.get(p['confianza'], (215, 0, 0))
        d.ellipse((X(p['x']) - rr, Y(p['y']) - rr, X(p['x']) + rr, Y(p['y']) + rr), outline=cl, width=2)
    img.save(os.path.join(carpeta, 'trazos_sin_detalle.png'))


if __name__ == '__main__':
    main()
