"""Uso:  python cli.py plano.pdf [otro.pdf ...] [--salida CARPETA] [--sin-pdf] [--sin-excel] [--sin-ocr]"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import process, write_searchable_pdf, write_excel


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTADOS = os.path.join(ROOT, '2 - Resultados')


def run(pdf, outdir=None, make_pdf=True, make_xlsx=True, use_ocr=True, log=print):
    base = os.path.splitext(os.path.basename(pdf))[0]
    outdir = outdir or os.path.join(RESULTADOS, base)   # por defecto: 2 - Resultados/<plano>/
    os.makedirs(outdir, exist_ok=True)
    log(f'Procesando {os.path.basename(pdf)} ...')
    res = process(pdf, log=log, use_ocr=use_ocr)
    outs = []
    if make_pdf:
        from ocr_raster import page_items
        p = os.path.join(outdir, base + ' - BUSCABLE.pdf')
        write_searchable_pdf(res, p, raster_ocr=page_items if use_ocr else None)
        outs.append(p)
    if make_xlsx:
        p = os.path.join(outdir, base + ' - LISTADO DE CABLES.xlsx')
        write_excel(res, p)
        outs.append(p)
    ncab = len({c['num'] for c in res.cables})
    log(f'Listo en {res.seconds:.0f} s: {ncab} números de cable, {len(res.review)} elementos a revisar.')
    for o in outs:
        log('  -> ' + o)
    return res, outs


def main():
    ap = argparse.ArgumentParser(description='PDF buscable + listado de cables de planos eléctricos vectoriales')
    ap.add_argument('pdf', nargs='+')
    ap.add_argument('--salida', default=None, help='carpeta de salida (por defecto: 2 - Resultados/<plano>)')
    ap.add_argument('--sin-pdf', action='store_true')
    ap.add_argument('--sin-excel', action='store_true')
    ap.add_argument('--sin-ocr', action='store_true', help='no usar OCR (aun más rápido, puede dejar algún texto sin leer)')
    a = ap.parse_args()
    for pdf in a.pdf:
        run(pdf, a.salida, not a.sin_pdf, not a.sin_excel, not a.sin_ocr)


if __name__ == '__main__':
    main()
