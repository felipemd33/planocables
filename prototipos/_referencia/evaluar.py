"""Evalua la salida de un prototipo de mapeo de bornes contra la referencia.

uso:  python evaluar.py <salida_prototipo.json> [--json]

Formato de la salida del prototipo (cualquiera de los dos):
  {"puntos": [{"texto": "11PS1 1 (-)", "cables": ["1110"], "x": 612.9, "y": 712.4, "r": 1.8, "confianza": "alta"}, ...],
   "segundos": 3.2}
  o bien {"11PS1 1 (-)": [612.9, 712.4], "13PS3 -Vo#1311": [815.5, 715.4], ...}   (texto o texto#cable -> [x, y])

Criterio: un borne esta BIEN si el punto cae a <= 1.5 pt (~2 mm) del punto de referencia (la mitad del paso del
borne mas angosto de este tablero, 3.66 pt, es 1.83 pt: mas lejos ya es otro borne). Los puntos de referencia
con confianza 'baja' (usos dudosos del instructivo) no se evaluan. Se aplican las correcciones de verificacion
que haya en correcciones_<familia>.json (lista {"texto", "cable"?, "x", "y", "motivo"}).
"""
import json, math, os, sys, glob, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
TOL = 1.5


def referencia():
    ref = json.load(open(os.path.join(AQUI, 'bornes_referencia.json'), encoding='utf-8'))
    pts = [dict(p) for p in ref['puntos']]
    for f in glob.glob(os.path.join(AQUI, 'correcciones_*.json')):
        cs = json.load(open(f, encoding='utf-8'))
        cs = cs.get('correcciones', cs) if isinstance(cs, dict) else cs
        for c in cs:
            for p in pts:
                if p['texto'] == c['texto'] and (not c.get('cable') or c['cable'] in p['cables']):
                    p['x'], p['y'] = float(c['x']), float(c['y'])
                    p['corregido'] = c.get('motivo', '')
                    if c.get('confianza'):
                        p['confianza'] = c['confianza']
    return pts


def cargar(path):
    d = json.load(open(path, encoding='utf-8'))
    seg = d.get('segundos') if isinstance(d, dict) else None
    out = []
    if isinstance(d, dict) and 'puntos' in d:
        for p in d['puntos']:
            out.append(dict(texto=p['texto'], cables=[str(c) for c in (p.get('cables') or ([p['cable']] if p.get('cable') else []))],
                            x=float(p['x']), y=float(p['y'])))
    else:
        for k, v in d.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                t, _, c = k.partition('#')
                out.append(dict(texto=t, cables=[c] if c else [], x=float(v[0]), y=float(v[1])))
    return out, seg


def evaluar(path):
    ref = referencia()
    got, seg = cargar(path)
    fam = collections.defaultdict(lambda: dict(total=0, hallados=0, bien=0, errores=[]))
    detalle, no_eval = [], []
    for r in ref:
        if r['confianza'] == 'baja':
            no_eval.append(f"{r['texto']} {r['cables']}")
            continue
        f = fam[r['familia']]; f['total'] += 1
        cand = [g for g in got if g['texto'] == r['texto'] and (not g['cables'] or set(g['cables']) & set(r['cables']))]
        if len([g for g in cand if g['cables']]) > 0:
            cand = [g for g in cand if g['cables']] or cand
        if not cand:
            detalle.append((r['familia'], r['texto'], r['cables'], None)); continue
        g = min(cand, key=lambda g: math.hypot(g['x'] - r['x'], g['y'] - r['y']))
        e = math.hypot(g['x'] - r['x'], g['y'] - r['y'])
        f['hallados'] += 1; f['errores'].append(e)
        if e <= TOL:
            f['bien'] += 1
        else:
            detalle.append((r['familia'], r['texto'], r['cables'], e))
    tot = {k: sum(f[k] for f in fam.values()) for k in ('total', 'hallados', 'bien')}
    errs = sorted(e for f in fam.values() for e in f['errores'])
    res = dict(salida=path, segundos=seg, total=tot['total'], hallados=tot['hallados'], bien=tot['bien'],
               cobertura=round(tot['hallados'] / max(1, tot['total']), 3), acierto=round(tot['bien'] / max(1, tot['total']), 3),
               error_mediano_pt=round(errs[len(errs) // 2], 2) if errs else None,
               por_familia={k: dict(total=f['total'], hallados=f['hallados'], bien=f['bien'],
                                    error_medio_pt=round(sum(f['errores']) / len(f['errores']), 2) if f['errores'] else None)
                            for k, f in sorted(fam.items())},
               fallas=[dict(familia=a, texto=b, cables=c, error_pt=None if e is None else round(e, 2)) for a, b, c, e in detalle],
               no_evaluados=no_eval)
    return res


def texto(res):
    L = [f"Salida: {res['salida']}", f"Tiempo: {res['segundos']} s" if res['segundos'] is not None else 'Tiempo: (no informado)',
         f"BIEN (<= {TOL} pt ~ 2 mm): {res['bien']}/{res['total']} = {res['acierto'] * 100:.1f} %   |   con punto: {res['hallados']}/{res['total']}"
         f"   |   error mediano: {res['error_mediano_pt']} pt", '', f"{'familia':16s} {'bien':>6s} {'con punto':>10s} {'total':>6s} {'err medio pt':>13s}"]
    for k, f in res['por_familia'].items():
        L.append(f"{k:16s} {f['bien']:6d} {f['hallados']:10d} {f['total']:6d} {str(f['error_medio_pt']):>13s}")
    if res['fallas']:
        L += ['', 'Fallas (sin punto o a mas de %.1f pt):' % TOL]
        L += [f"  {x['familia']:15s} {x['texto']:22s} {','.join(x['cables']):10s} {'SIN PUNTO' if x['error_pt'] is None else str(x['error_pt']) + ' pt'}" for x in res['fallas']]
    L += ['', f"No evaluados (referencia dudosa): {', '.join(res['no_evaluados'])}"]
    return '\n'.join(L)


if __name__ == '__main__':
    r = evaluar(sys.argv[1])
    if '--json' in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        t = texto(r); print(t)
        with open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), 'evaluacion.txt'), 'w', encoding='utf-8') as f:
            f.write(t + '\n')
