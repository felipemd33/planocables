"""Prueba de plano a OTRA ESCALA para el prototipo P5.

uso:  python prueba_escala.py [carpeta_referencia] [salida.txt]
      (por defecto ../_referencia y salida/evaluacion_escala.txt)

Las plantillas se recortaron de un plano a 1,4086 mm por punto. Si el topografico de otro tablero se imprime
en otra hoja (A3 en vez de A2, por ejemplo) el dibujo queda mas chico o mas grande. mapear.py lo corrige solo:
agranda o achica las plantillas en la proporcion entre la escala de la base y la del plano nuevo
(escala_mm_por_pt de usos_por_componente.json). Para probarlo:
  1. se copia la pagina del topografico achicada o agrandada (pypdf, sigue siendo vectorial),
  2. se pasan las posiciones de las etiquetas y la region de la bandeja de los usos a la escala nueva,
  3. se corre mapear.py con la MISMA base,
  4. se vuelven los puntos a la escala original y se evalua con evaluar.py.
Este script lee la referencia (a traves de evaluar.py): es un paso de evaluacion, aparte de mapear.py.
"""
import json
import os
import shutil
import sys
import tempfile
import time

from pypdf import PdfReader, PdfWriter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import mapear  # noqa: E402

FACTORES = [0.8, 1.25]


def main():
    refdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, '..', '_referencia')
    txt = sys.argv[2] if len(sys.argv) > 2 else os.path.join(AQUI, 'salida', 'evaluacion_escala.txt')
    sys.path.insert(0, refdir)
    import evaluar  # noqa: E402
    pdf = os.path.join(refdir, 'topografico.pdf')
    U = json.load(open(os.path.join(refdir, 'usos_por_componente.json'), encoding='utf-8'))
    L = []

    def pr(s=''):
        print(s)
        L.append(s)

    pr('PRUEBA DE PLANO A OTRA ESCALA - P5 vision por imagen')
    pr('La pagina del topografico se achica o agranda (sigue vectorial); se corre mapear.py con la misma base y los')
    pr('puntos se vuelven a la escala original para evaluar con evaluar.py (tolerancia 1.5 pt de la escala original).')
    pr('')
    tmp = tempfile.mkdtemp(prefix='p5_escala_')
    try:
        for f in FACTORES:
            w = PdfWriter()
            pag = PdfReader(pdf).pages[U['pagina_pdf'] - 1]
            pag.scale_by(f)
            w.add_page(pag)
            ruta = os.path.join(tmp, f'escala_{f}.pdf')
            with open(ruta, 'wb') as fh:
                w.write(fh)
            u2 = json.loads(json.dumps(U))
            u2['pagina_pdf'] = 1
            u2['escala_mm_por_pt'] = U['escala_mm_por_pt'] / f
            if u2.get('region_bandeja'):
                u2['region_bandeja'] = [v * f for v in U['region_bandeja']]
            for c in u2['componentes'].values():
                c['etiqueta_topografico']['x'] *= f
                c['etiqueta_topografico']['y'] *= f
            upath = os.path.join(tmp, 'usos.json')
            json.dump(u2, open(upath, 'w', encoding='utf-8'), ensure_ascii=False)
            t0 = time.time()
            salida = os.path.join(tmp, f'bornes_{f}.json')
            res = mapear.mapear(ruta, upath, salida, materiales=os.path.join(refdir, 'lista_materiales.txt'), control=None)
            seg = time.time() - t0
            for p in res['puntos']:  # a la escala original
                p['x'], p['y'], p['r'] = p['x'] / f, p['y'] / f, p['r'] / f
            json.dump(res, open(salida, 'w', encoding='utf-8'), ensure_ascii=False, default=float)
            ev = evaluar.evaluar(salida)
            radios = sorted({round(p['r'] * f, 2) for p in res['puntos']})
            pr(f"Factor {f} (escala del plano {u2['escala_mm_por_pt']:.4f} mm/pt; plantillas x {f}): BIEN {ev['bien']}/{ev['total']} = "
               f"{100 * ev['acierto']:.1f} %   con punto {ev['hallados']}/{ev['total']}   error mediano {ev['error_mediano_pt']} pt   tiempo {seg:.1f} s")
            for k, fam in ev['por_familia'].items():
                pr(f"      {k:16s} {fam['bien']:3d}/{fam['total']:3d}   err medio {fam['error_medio_pt']} pt")
            for x in ev['fallas']:
                pr(f"   falla: {x['texto']} {x['cables']} {'SIN PUNTO' if x['error_pt'] is None else str(x['error_pt']) + ' pt'}")
            pr(f"   radios r informados (pt del plano nuevo): {radios}")
            pr('')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.dirname(os.path.abspath(txt)), exist_ok=True)
    open(txt, 'w', encoding='utf-8').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
