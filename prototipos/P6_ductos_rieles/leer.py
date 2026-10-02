"""Prototipo: ductos (cablecanales) y rieles DIN de un topografico, con su largo de corte en mm."""
import os, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'programa'))
import pypdf
from pdfvec import page_strokes, layer_names
from topo import rail_bands, perfil, rect_of, snap_escala, RIEL_MM, PT_MM, RX_PLACA, PLACA_MIN_H, FILA_H
from ruteo import ducts

R5 = lambda v: int(round(v / 5.0) * 5)


def leer(pdf_path, log=print):
    reader = pypdf.PdfReader(pdf_path); names = layer_names(reader)
    best = None
    for pi in range(len(reader.pages)):
        st = page_strokes(reader, pi, names)
        bands = rail_bands(st)
        if not bands:
            continue
        H = perfil(bands)
        if RIEL_MM / H < 0.9 * PT_MM:      # detalle ampliado
            continue
        if best is None or len(bands) > len(best['bands']):
            plates = [r for r in (rect_of(p, o) for l, o, p in st if RX_PLACA.search(l))
                      if r and min(r[2] - r[0], r[3] - r[1]) > PLACA_MIN_H * H]
            best = dict(pi=pi, bands=bands, H=H, plates=plates, size=[float(v) for v in reader.pages[pi].mediabox[2:]])
    if not best:
        raise ValueError('No encontré rieles DIN en ninguna hoja')
    H, bands = best['H'], best['bands']
    esc = snap_escala(RIEL_MM / H)
    # vista de la bandeja: la placa que tiene mas tramos de riel adentro
    def adentro(b, p):
        return p[0] - H <= b['x0'] and b['x1'] <= p[2] + H and p[1] - H <= b['eje'] <= p[3] + H
    placa = max(best['plates'], key=lambda p: (sum(adentro(b, p) for b in bands), -(p[2] - p[0]) * (p[3] - p[1])), default=None)
    if placa and sum(adentro(b, placa) for b in bands):
        bands = [b for b in bands if adentro(b, placa)]
    else:
        placa = [min(b['x0'] for b in bands) - 2 * H, min(b['y0'] for b in bands) - 3 * H,
                 max(b['x1'] for b in bands) + 2 * H, max(b['y1'] for b in bands) + 3 * H]
    dl = ducts(pdf_path, best['pi'], placa, H)
    # rieles: tramos con el mismo eje = un riel; se estira hasta el ducto vertical (o el borde de la placa) de cada lado
    filas = []
    for b in sorted(bands, key=lambda b: -b['eje']):
        if filas and abs(filas[-1]['eje'] - b['eje']) < FILA_H * H:
            f = filas[-1]; f['x0'] = min(f['x0'], b['x0']); f['x1'] = max(f['x1'], b['x1'])
        else:
            filas.append(dict(eje=b['eje'], x0=b['x0'], x1=b['x1'], y0=b['y0'], y1=b['y1']))
    rieles = []
    for i, f in enumerate(filas):
        vert = [d['b'] for d in dl if not d['h'] and d['b'][1] - H <= f['eje'] <= d['b'][3] + H]
        izq = [v[2] for v in vert if v[2] <= f['x0'] + H]
        der = [v[0] for v in vert if v[0] >= f['x1'] - H]
        x0 = max(izq) if izq else f['x0']; x1 = min(der) if der else f['x1']
        rieles.append(dict(n=i + 1, b=[round(x0, 1), round(f['eje'] - H / 2, 1), round(x1, 1), round(f['eje'] + H / 2, 1)],
                           largo=R5((x1 - x0) * esc), visto=R5((f['x1'] - f['x0']) * esc)))
    ductos = []
    for i, d in enumerate(sorted(dl, key=lambda d: (not d['h'], -d['b'][3], d['b'][0]))):
        x0, y0, x1, y1 = d['b']; w, h = (x1 - x0) * esc, (y1 - y0) * esc
        ductos.append(dict(n=i + 1, b=d['b'], horizontal=d['h'], intrinseco=bool(d['ex']),
                           largo=R5(max(w, h)), ancho=R5(min(w, h))))
    log(f'hoja {best["pi"] + 1}: {len(rieles)} rieles, {len(ductos)} ductos, escala {esc} mm/pt')
    return dict(pagina=best['pi'] + 1, escala=esc, size=best['size'], placa=[round(v, 1) for v in placa],
                rieles=rieles, ductos=ductos)


if __name__ == '__main__':
    import json; print(json.dumps(leer(sys.argv[1]), indent=1)[:3000])
