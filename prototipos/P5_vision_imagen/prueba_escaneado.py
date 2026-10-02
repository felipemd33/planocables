"""Prueba de plano ESCANEADO para el prototipo P5.

uso:  python prueba_escaneado.py [carpeta_referencia] [salida.txt]
      (por defecto ../_referencia y salida/evaluacion_escaneado.txt)

La idea del prototipo es que trabaja sobre la IMAGEN, asi que tiene que andar igual con un plano que no trae
dibujo vectorial (escaneado, o exportado como imagen desde otro CAD). Para probarlo sin tener un escaneo real:
  1. se renderiza la pagina del topografico como imagen (300 y 200 dpi),
  2. se la "ensucia" como un escaneo: desenfoque, ruido, compresion JPEG,
  3. se guarda como un PDF de UNA pagina que solo tiene esa imagen (ya no hay trazos ni textos adentro),
  4. se corre mapear.py sobre ese PDF con la MISMA base (las plantillas se recortaron del render vectorial a
     10 px/pt; aca la imagen tiene 4,2 o 2,8 px/pt y viene sucia) y se evalua con evaluar.py.
Este script lee la referencia (a traves de evaluar.py): es un paso de evaluacion, aparte de mapear.py.
"""
import json
import os
import shutil
import sys
import tempfile
import time

import cv2
import numpy as np
import pypdfium2 as pdfium
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import mapear  # noqa: E402

# Las dos primeras se usaron para AJUSTAR el modo escaneado de mapear.py (ESCANEO: suavizado y umbrales); las
# otras NO se usaron para ajustar nada (otro ruido, otra resolucion): son la prueba de verdad.
VARIANTES = [
    dict(nombre='300 dpi, ruido 8, JPEG 70 (usada para ajustar)', dpi=300, blur=0.7, ruido=8, jpeg=70, semilla=1),
    dict(nombre='200 dpi, ruido 8, JPEG 70 (usada para ajustar)', dpi=200, blur=0.6, ruido=8, jpeg=70, semilla=1),
    dict(nombre='250 dpi, ruido 14, JPEG 50 (no usada para ajustar)', dpi=250, blur=0.9, ruido=14, jpeg=50, semilla=7),
    dict(nombre='150 dpi, ruido 8, JPEG 70 (no usada para ajustar)', dpi=150, blur=0.5, ruido=8, jpeg=70, semilla=3),
]


def escanear(pdf, pagina_idx, v, destino):
    pg = pdfium.PdfDocument(pdf)[pagina_idx]
    img = pg.render(scale=v['dpi'] / 72).to_numpy()[:, :, :3][:, :, ::-1].copy()  # RGB
    img = cv2.GaussianBlur(img, (0, 0), v['blur'])
    rng = np.random.default_rng(v.get('semilla', 1))
    img = np.clip(img.astype(np.int16) + rng.normal(0, v['ruido'], img.shape).astype(np.int16), 0, 255).astype(np.uint8)
    W, H = pg.get_size()  # dpi exacto en x e y para que la pagina nueva mida lo mismo que la original (mismas coordenadas)
    Image.fromarray(img).save(destino, 'PDF', dpi=(img.shape[1] * 72 / W, img.shape[0] * 72 / H), quality=v['jpeg'])
    d = pdfium.PdfDocument(destino)
    return img.shape, d[0].get_size()


def main():
    refdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, '..', '_referencia')
    txt = sys.argv[2] if len(sys.argv) > 2 else os.path.join(AQUI, 'salida', 'evaluacion_escaneado.txt')
    sys.path.insert(0, refdir)
    import evaluar  # noqa: E402
    pdf = os.path.join(refdir, 'topografico.pdf')
    U = json.load(open(os.path.join(refdir, 'usos_por_componente.json'), encoding='utf-8'))
    L = []

    def pr(s=''):
        print(s)
        L.append(s)

    pr('PRUEBA DE PLANO ESCANEADO - P5 vision por imagen')
    pr('El topografico se pasa a imagen, se ensucia como un escaneo y se guarda como PDF sin vectores; se corre mapear.py')
    pr('con la misma base y se evalua con evaluar.py (tolerancia 1.5 pt).')
    pr('')
    tmp = tempfile.mkdtemp(prefix='p5_escaneo_')
    try:
        for v in VARIANTES:
            ruta = os.path.join(tmp, f"escaneo_{v['dpi']}_{v['semilla']}.pdf")
            forma, tam = escanear(pdf, U['pagina_pdf'] - 1, v, ruta)
            u2 = dict(U, topografico=ruta, pagina_pdf=1)
            upath = os.path.join(tmp, 'usos.json')
            json.dump(u2, open(upath, 'w', encoding='utf-8'), ensure_ascii=False)
            t0 = time.time()
            salida = os.path.join(tmp, f"bornes_{v['dpi']}_{v['semilla']}.json")
            res = mapear.mapear(ruta, upath, salida, materiales=os.path.join(refdir, 'lista_materiales.txt'), control=None)
            seg = time.time() - t0
            ev = evaluar.evaluar(salida)
            pr(f"{v['nombre']}: imagen {forma[1]}x{forma[0]} px ({v['dpi'] / 72:.2f} px/pt), PDF de {os.path.getsize(ruta) / 1e6:.1f} MB")
            pr(f"   BIEN {ev['bien']}/{ev['total']} = {100 * ev['acierto']:.1f} %   con punto {ev['hallados']}/{ev['total']}   "
               f"error mediano {ev['error_mediano_pt']} pt   tiempo {seg:.1f} s")
            for k, f in ev['por_familia'].items():
                pr(f"      {k:16s} {f['bien']:3d}/{f['total']:3d}   err medio {f['error_medio_pt']} pt")
            for x in ev['fallas']:
                pr(f"   falla: {x['texto']} {x['cables']} {'SIN PUNTO' if x['error_pt'] is None else str(x['error_pt']) + ' pt'}")
            cambios = [f"{t}: {c.get('modelo', '-')}" for t, c in res['componentes'].items()]
            pr('   modelos reconocidos: ' + ', '.join(cambios))
            pr('')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.dirname(os.path.abspath(txt)), exist_ok=True)
    open(txt, 'w', encoding='utf-8').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
