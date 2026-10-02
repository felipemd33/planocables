"""Suma a la base de bornes los puntos VERIFICADOS de un tablero.

uso:
  python agregar_tablero.py <topografico.pdf> <usos_por_componente.json> <verificados> [<verificados> ...] --tablero 75286-1
                            [--modelos tableros/75286-1/modelos.json] [--lista lista_materiales.txt]
                            [--base base_bornes.json] [--definiciones modelos_base.json]

<verificados> (uno o varios; si un borne aparece en varios, manda el ULTIMO) puede ser:
  * bornes_referencia.json (lista 'puntos' con texto, cables, x, y, confianza). Si al lado hay
    correcciones_*.json, se aplican (son parte de la verificacion).
  * instructivo.json del programa: se usan los 'bornes_usuario' (puntos ajustados a mano en el visor).
  * bornes.json del programa ({'puntos': {texto: {'xy': [x, y], ...}}}) o una salida de mapear.py.
  * un diccionario simple {'texto#cable': [x, y]}.

Que hace, por cada componente del tablero:
  1. Busca el modelo (--modelos, si no la lista de materiales).
  2. Traduce cada texto del instructivo a (unidad, borne) con la regla del modelo.
  3. Busca en el dibujo el RECUADRO de la unidad que contiene el punto (la mascara blanca del bloque).
  4. Guarda la posicion del borne normalizada al recuadro (u, v de 0 a 1), el radio del borne,
     un parche del dibujo alrededor del punto y un descriptor del recuadro.
Si el tablero ya estaba en la base, sus ejemplos se reemplazan.  Los puntos 'baja' no se usan.
"""
import sys, os, json, glob, argparse, collections, math, re

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import nucleo as N


def leer_verificados(path):
    """[(texto, cable, x, y, confianza)]"""
    d = json.load(open(path, encoding='utf-8'))
    out = []
    if isinstance(d, dict) and isinstance(d.get('puntos'), list):
        pts = [dict(p) for p in d['puntos']]
        # correcciones de la verificacion (mismo formato que usa evaluar.py)
        for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(path)), 'correcciones_*.json')):
            cs = json.load(open(f, encoding='utf-8'))
            cs = cs.get('correcciones', cs) if isinstance(cs, dict) else cs
            for c in cs:
                for p in pts:
                    if p['texto'] == c['texto'] and (not c.get('cable') or c['cable'] in (p.get('cables') or [])):
                        p['x'], p['y'] = float(c['x']), float(c['y'])
                        if c.get('confianza'):
                            p['confianza'] = c['confianza']
        for p in pts:
            cables = [str(c) for c in (p.get('cables') or ([p['cable']] if p.get('cable') else [None]))]
            for c in cables:
                out.append((p['texto'], c, float(p['x']), float(p['y']), p.get('confianza') or 'alta'))
        return out
    if isinstance(d, dict) and isinstance(d.get('bornes_usuario'), dict):
        d = d['bornes_usuario']
    elif isinstance(d, dict) and isinstance(d.get('puntos'), dict):
        for k, v in d['puntos'].items():
            t, _, c = k.partition('#')
            xy = v['xy'] if isinstance(v, dict) else v
            cables = [c] if c else [str(x) for x in (v.get('cables') or [None])] if isinstance(v, dict) else [None]
            conf = v.get('conf', 'alta') if isinstance(v, dict) else 'alta'
            for cc in cables:
                out.append((t, cc, float(xy[0]), float(xy[1]), conf))
        return out
    for k, v in d.items():
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            t, _, c = k.partition('#')
            out.append((t, c or None, float(v[0]), float(v[1]), 'alta'))
    return out


def unir_definiciones(base, defs):
    """Los modelos de modelos_base.json mandan; se conservan los ejemplos que ya tenia la base."""
    mods = base.setdefault('modelos', {})
    for k, m in defs['modelos'].items():
        ej = mods.get(k, {}).get('ejemplos', [])
        mods[k] = dict(m)
        mods[k]['ejemplos'] = ej
    base['version'] = defs.get('version', 1)
    base['descripcion'] = ('Base de bornes que aprende de tableros verificados (prototipo P4). Por modelo: la regla del '
                           'instructivo y los EJEMPLOS: posicion de cada borne normalizada al recuadro del aparato '
                           '(u, v de 0 a 1; u de izquierda a derecha, v de abajo hacia arriba), radio r en pt, '
                           'parche del dibujo para el ajuste fino y descriptor del recuadro. Sin coordenadas absolutas.')
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf'); ap.add_argument('usos'); ap.add_argument('verificados', nargs='+')
    ap.add_argument('--tablero', required=True)
    ap.add_argument('--modelos', default=None)
    ap.add_argument('--lista', default=None)
    ap.add_argument('--base', default=os.path.join(AQUI, 'base_bornes.json'))
    ap.add_argument('--definiciones', default=os.path.join(AQUI, 'modelos_base.json'))
    a = ap.parse_args()

    defs = N.cargar_base(a.definiciones)
    base = N.cargar_base(a.base) if os.path.exists(a.base) else {}
    base = unir_definiciones(base, defs)
    U = json.load(open(a.usos, encoding='utf-8'))
    comps = U['componentes']
    lista = a.lista or os.path.join(os.path.dirname(os.path.abspath(a.usos)), 'lista_materiales.txt')
    pl = N.Plano(a.pdf, int(U.get('pagina_pdf', 1)) - 1, U['region_bandeja'], U.get('escala_mm_por_pt', 1.0))
    # modelo de cada tag: el mismo criterio que mapear.py (lista de materiales + comprobacion con el dibujo);
    # --modelos (revisado en la auditoria) manda sobre todo
    import mapear
    mp = mapear.Mapeador(pl, U, base, lista)
    modelos_tag = {}
    cache = {}
    for tag in comps:
        k = mp.info(tag, frozenset(), cache)[0]
        if k:
            modelos_tag[tag] = k
    if a.modelos:
        modelos_tag.update(json.load(open(a.modelos, encoding='utf-8'))['modelos'])
    # varios archivos: ej. el bornes.json del programa (mapeo aceptado) y despues el instructivo.json (bornes_usuario,
    # ajustados a mano en el visor): el ultimo manda
    junt = collections.OrderedDict()
    for f in a.verificados:
        vv = leer_verificados(f)
        print(f'{len(vv)} puntos leidos de {f}')
        for t, cab, x, y, conf in vv:
            junt[(t, cab)] = (t, cab, x, y, conf)
    ver = list(junt.values())
    print(f'{len(ver)} puntos verificados en total')

    # texto#cable -> tag  (del instructivo)
    uso_de = {}
    for tag, c in comps.items():
        for u in c['usos']:
            uso_de.setdefault((u['texto'], str(u['cable'])), (tag, u))
            uso_de.setdefault((u['texto'], None), (tag, u))

    # cable -> [(tag, uso)]: para los puntos del visor con el texto ya renombrado ('62XDO 3 ABAJO#6204' cuando el
    # instructivo dice '62XDIO 3 ABAJO'): se busca el uso del mismo cable con el resto del texto mas parecido
    por_cable = collections.defaultdict(list)
    for tag, c in comps.items():
        for u in c['usos']:
            por_cable[str(u['cable'])].append((tag, u))
    exactos = {(t, cab) for t, cab, *_ in ver}

    def por_numero(t, cab):
        cs = [(tag, u) for tag, u in por_cable.get(str(cab), []) if (u['texto'], str(u['cable'])) not in exactos]
        if not cs:
            return None
        resto = t.split(' ', 1)[1] if ' ' in t else ''
        sc = lambda tu: (2 * ((tu[1]['texto'].split(' ', 1)[1] if ' ' in tu[1]['texto'] else '') == resto)
                         + (tu[1]['texto'].split()[0][:2] == t.split()[0][:2]))
        cs.sort(key=sc, reverse=True)
        return cs[0] if len(cs) == 1 or sc(cs[0]) > sc(cs[1]) else None

    por_tag = collections.defaultdict(list)
    log = []
    for t, cab, x, y, conf in ver:
        if conf == 'baja':
            continue
        k = uso_de.get((t, cab)) or uso_de.get((t, None))
        if not k and cab:
            k = por_numero(t, cab)
            if k:
                log.append(f'  {t} #{cab}: texto renombrado; se toma el uso "{k[1]["texto"]}" del mismo cable')
        if not k:
            log.append(f'  {t} #{cab}: el texto no esta en el instructivo, no se usa')
            continue
        por_tag[k[0]].append(dict(texto=k[1]['texto'], cable=cab, x=x, y=y, conf=conf, uso=k[1]))

    asignados = []            # (clave, tag_fuente, componente, unidad, caja, punto, borne, modo, tx, ty)
    reasig = []               # textos del instructivo que el tablero verificado ubica en otra unidad o en otro componente
    fuera = []                # puntos que caen en piezas de otro componente
    fisicas = {}              # tag -> (clave, [cajas de sus unidades])
    for tag, pts in sorted(por_tag.items()):
        clave = modelos_tag.get(tag)
        if not clave or clave not in base['modelos']:
            log.append(f'{tag}: sin modelo en la base ({clave}); agregarlo a modelos_base.json')
            continue
        mod = base['modelos'][clave]
        et = comps[tag]['etiqueta_topografico']
        tx, ty = et['x'], et['y']
        # 1) regla: texto -> (unidad, borne)
        res = []
        for p in pts:
            r = N.resolver_uso(mod, tag, p['uso'])
            if r is None:
                log.append(f'{tag}: "{p["texto"]}" no se entiende con la regla {mod["regla"]["tipo"]}')
                continue
            res.append((p, r[0], r[1]))
        # bornes con varios candidatos (dos '-Vo'): por numero de cable creciente
        grupos = collections.defaultdict(list)
        for i, (p, un, b) in enumerate(res):
            if isinstance(b, list):
                grupos[tuple(b)].append(i)
        for bl, ii in grupos.items():
            ii.sort(key=lambda i: N.num_cable(res[i][0]['cable']))
            for j, i in enumerate(ii):
                res[i] = (res[i][0], res[i][1], bl[min(j, len(bl) - 1)])
        # 2) recuadro de cada punto
        modo = mod.get('busqueda', 'serie')
        if modo == 'contiene':
            cands = [b for b in pl.cajas_que_contienen(tx, ty, 0.5)
                     if all(b['x0'] - 0.6 <= p['x'] <= b['x1'] + 0.6 and b['y0'] - 0.6 <= p['y'] <= b['y1'] + 0.6 for p, _, _ in res)]
            cands.sort(key=lambda b: (b['fuente'] != 'mascara', b['w'] * b['h']))
            if not cands:
                log.append(f'{tag}: no encontre un recuadro que contenga la etiqueta y todos sus puntos')
                continue
            caja = cands[0]
            fisicas[tag] = (clave, [caja])
            for p, _, b in res:
                asignados.append((clave, tag, tag, 1, caja, p, b, modo, tx, ty))
            continue
        tam = collections.Counter()
        cajas_p = []
        # la etiqueta siguiente del mismo riel cierra el componente (regla del taller)
        xlim = min(pl.marcos_a_la_derecha(tx, ty - 12, ty + 12) +
                   [cc['etiqueta_topografico']['x'] for tt, cc in comps.items()
                    if cc['etiqueta_topografico'].get('riel') == et.get('riel') and cc['etiqueta_topografico']['x'] > tx + 1] + [1e9])
        for p, un, b in res:
            cs = [c for c in pl.cajas_que_contienen(p['x'], p['y'], 0.3)
                  if not (c['x0'] <= tx <= c['x1'] and c['y0'] <= ty <= c['y1']) and c['x0'] > tx - 1.0
                  and c['y0'] - 1 <= ty <= c['y1'] + 1 and (c['x0'] + c['x1']) / 2 < xlim]
            cs.sort(key=lambda c: (c['fuente'] != 'mascara', c['w'] * c['h']))
            cajas_p.append(cs)
            if cs:
                tam[(round(cs[0]['w'], 1), round(cs[0]['h'], 1))] += 1
        if not tam:
            # ninguno de sus puntos cae en sus propias piezas: pueden ser de la bornera vecina (se prueba abajo)
            fuera += [(tag, p) for p, un, b in res]
            continue
        (w0, h0), _ = tam.most_common(1)[0]
        # unidades fisicas a la derecha de la etiqueta, para verificar la numeracion
        fis = sorted([c for c in pl.cajas if N.tam_ok(c, w0, h0, 0.04, 0.04) and c['x0'] > tx - 1.0
                      and c['y0'] - 1 <= ty <= c['y1'] + 1 and (c['x0'] + c['x1']) / 2 < xlim], key=lambda c: c['x0'])
        fis = N.sin_solapes(fis, w0)
        fisicas[tag] = (clave, fis)
        for (p, un, b), cs in zip(res, cajas_p):
            cs = [c for c in cs if N.tam_ok(c, w0, h0, 0.04, 0.04)]
            if not cs:
                fuera.append((tag, p))
                continue
            c = cs[0]
            nfis = next((i + 1 for i, f in enumerate(fis) if abs(f['x0'] - c['x0']) < 0.3), None)
            if un and nfis and un != nfis:
                log.append(f'{tag}: "{p["texto"]}" #{p["cable"]} dice unidad {un} pero el punto esta en la unidad {nfis}: '
                           f'se aprende en la {nfis}')
            if nfis and un != nfis and not isinstance(b, list):
                reasig.append(dict(tablero=a.tablero, tag=tag, texto=p['texto'], cable=p['cable'], componente=tag,
                                   unidad=nfis, borne=b, motivo=('el texto no dice el modulo' if not un else
                                                                 f'el texto dice la unidad {un}, el borne verificado esta en la {nfis}')))
            asignados.append((clave, tag, tag, nfis or un, c, p, b, modo, tx, ty))

    # puntos que el instructivo le da a un tag pero que estan en las piezas del componente vecino
    # (ej. '62XDIO 4 ABAJO' que en el tablero es 62XDO): se aprenden para el vecino, con la regla del vecino
    for tag, p in fuera:
        hecho = False
        for t2, (cl2, fis2) in fisicas.items():
            if t2 == tag or base['modelos'][cl2].get('busqueda') != 'serie':
                continue
            for i, c in enumerate(fis2):
                if c['x0'] - 0.3 <= p['x'] <= c['x1'] + 0.3 and c['y0'] - 0.3 <= p['y'] <= c['y1'] + 0.3:
                    uso2 = dict(p['uso'], texto=t2 + p['texto'][len(tag):])
                    r = N.resolver_uso(base['modelos'][cl2], t2, uso2)
                    if r and r[0] == i + 1 and not isinstance(r[1], list):
                        e2 = comps[t2]['etiqueta_topografico']
                        asignados.append((cl2, tag, t2, i + 1, c, p, r[1], 'serie', e2['x'], e2['y']))
                        reasig.append(dict(tablero=a.tablero, tag=tag, texto=p['texto'], cable=p['cable'], componente=t2,
                                           unidad=i + 1, borne=r[1], motivo=f'el borne verificado esta en la bornera vecina {t2}'))
                        log.append(f'{tag}: "{p["texto"]}" #{p["cable"]} esta en la pieza {i + 1} de {t2}: '
                                   f'se aprende como {t2} {r[1]} (bornera vecina)')
                        hecho = True
                    break
            if hecho:
                break
        if not hecho:
            log.append(f'{tag}: "{p["texto"]}" #{p["cable"]} cae fuera de las piezas de {tag}, no se usa')

    # 3) ejemplos: uno por recuadro y por tag de origen
    nuevos = collections.defaultdict(list)
    por_caja = collections.OrderedDict()
    for clave, tag, compo, un, c, p, b, modo, tx, ty in asignados:
        k = (clave, tag, round(c['x0'], 2), round(c['y0'], 2))
        por_caja.setdefault(k, (clave, tag, compo, un, c, modo, tx, ty, []))[8].append((p, b))
    for k, (clave, tag, compo, un, c, modo, tx, ty, lst) in por_caja.items():
        ej = dict(tablero=a.tablero, tag=tag, componente=compo, unidad=un, modo=modo, fuente_caja=c['fuente'],
                  tam_mm=[round(c['w'] * pl.escala, 3), round(c['h'] * pl.escala, 3)], escala_mm_por_pt=pl.escala,
                  etiqueta_uv=[round((tx - c['x0']) / c['w'], 3), round((ty - c['y0']) / c['h'], 3)],
                  descriptor=pl.descriptor(c), puntos={})
        for p, b in lst:
            if b in ej['puntos']:
                continue
            ej['puntos'][b] = dict(u=round((p['x'] - c['x0']) / c['w'], 5), v=round((p['y'] - c['y0']) / c['h'], 5),
                                   r=pl.radio(p['x'], p['y']), parche=N.parche_a_txt(pl.parche(p['x'], p['y'])),
                                   texto=p['texto'], cable=p['cable'], confianza=p['conf'])
            ci = pl.circulo_en(p['x'], p['y'])
            if ci:
                # el punto verificado es el centro de un circulo dibujado (boca o tornillo): el ajuste fino lo busca
                ej['puntos'][b]['circulo'] = dict(r=round(ci[2], 3), dx=round(p['x'] - ci[0], 3), dy=round(p['y'] - ci[1], 3))
        nuevos[clave].append(ej)

    # reemplazar lo que ya hubiera de este tablero
    for k, m in base['modelos'].items():
        m['ejemplos'] = [e for e in m.get('ejemplos', []) if e.get('tablero') != a.tablero] + nuevos.get(k, [])
    base['reasignaciones'] = [r for r in base.get('reasignaciones', []) if r.get('tablero') != a.tablero] + reasig
    base.setdefault('tableros', {})[a.tablero] = dict(topografico=os.path.basename(a.pdf), verificados=[os.path.basename(f) for f in a.verificados],
                                                     puntos=sum(len(e['puntos']) for v in nuevos.values() for e in v))
    N.guardar_base(base, a.base)
    for l in log:
        print(l)
    print()
    for k, v in nuevos.items():
        print(f'{k:48s} {len(v):3d} recuadros  {sum(len(e["puntos"]) for e in v):3d} puntos')
    print(f'{len(reasig)} reasignaciones de texto aprendidas (memoria del instructivo de este tablero)')
    print(f'\nBase guardada: {a.base}')


if __name__ == '__main__':
    main()
