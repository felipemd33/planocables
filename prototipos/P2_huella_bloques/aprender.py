"""Aprende la base de bornes (huellas de bloques + desplazamientos de cada borne) de un plano verificado.

uso:  python aprender.py [catalogo_modelos.json] [base_bornes.json] [--sin TAG]

Lee, para cada plano de 'planos_verificados' del catalogo: el topografico, los usos del instructivo y la
respuesta verificada (bornes_referencia.json + correcciones_*.json de la misma carpeta). Para cada modelo:
  1. Toma una instancia semilla: la mascara blanca (wipeout del bloque CAD) mas chica que contiene los
     bornes de referencia del tag (la pieza, en borneras y reles). Si el bloque no tiene mascara, la corrida
     de trazos contiguos del PDF alrededor de los bornes.
  2. La huella son los segmentos de esa instancia, relativos al centro de la mascara (el ancla).
  3. Busca la huella en el mismo plano (hashing geometrico) y se queda con los segmentos que tambien estan
     en las otras instancias del mismo color (huella de consenso: saca rayas que no son del bloque).
  4. Cada borne de referencia se lleva a coordenadas del bloque (se deshace la traslacion y el giro de la
     instancia que lo contiene) y se guarda con su clave generica (TB2_1, polo1_ARRIBA, ARRIBA_ext, A1...).
  5. Se completan los bornes que el plano verificado no uso: por 'filas' (el dibujito del borne se repite:
     se buscan sus copias alineadas dentro del bloque y se asignan en orden, por ejemplo el TB2_2 de una
     fuente o el contacto 12 de un RIF-0) y por 'derivados' (reglas de la hoja de datos escritas en el
     catalogo, por ejemplo el PE del toma en el medio de N y L).
  6. Radio de cada borne: el hueco libre del dibujo alrededor del punto.
--sin TAG aprende sin ese tag (validacion dejando-un-tag-afuera): no usa sus bornes ni sus instancias.
"""
import sys, os, json, glob, math, time, collections

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import huellas as H


def referencia_con_correcciones(path):
    """bornes_referencia.json con las correcciones de verificacion (correcciones_*.json) aplicadas."""
    ref = H.cargar_json(path)
    pts = [dict(p) for p in ref['puntos']]
    for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(path)), 'correcciones_*.json'))):
        cs = H.cargar_json(f)
        cs = cs.get('correcciones', cs) if isinstance(cs, dict) else cs
        for c in cs:
            for p in pts:
                if p['texto'] == c['texto'] and (not c.get('cable') or c['cable'] in p['cables']):
                    p['x'], p['y'] = float(c['x']), float(c['y'])
                    if c.get('confianza'):
                        p['confianza'] = c['confianza']
    return pts


def plano_de(pv, planos, usos):
    clave = os.path.abspath(pv['topografico'])
    if planos is not None and clave in planos:
        return planos[clave]
    pag = int(usos.get('pagina_pdf', 1)) - 1
    P = H.Plano(pv['topografico'], pag, region=usos.get('region_bandeja'))
    if planos is not None:
        planos[clave] = P
    return P


from huellas import zonas_de, contiene, en_zona


# ============================================================================================ aprender
def aprender(catalogo, excluir=None, planos=None, log=print):
    t0 = time.time()
    modelos_cat = catalogo['modelos']
    base = dict(
        descripcion='Base de bornes del prototipo P2 (huellas de bloques CAD). La genera aprender.py; mapear.py '
                    'solo lee este archivo. Cada modelo: su huella (segmentos del bloque relativos al ancla = centro '
                    'de la mascara del bloque, en pt PDF), su color, y la posicion de cada borne relativa al ancla.',
        generado=time.strftime('%Y-%m-%d %H:%M'), sin_tag=excluir,
        parametros=dict(umbral=H.UMBRAL, dist_color=H.DIST_COLOR, q_vector=H.Q_VECTOR, q_traslacion=H.Q_TRASL),
        modelos={})
    aprendido = {}
    for pv in catalogo['planos_verificados']:
        usos = H.cargar_json(pv['usos'])
        comps = usos['componentes']
        P = plano_de(pv, planos, usos)
        zonas = zonas_de(P, comps)
        zexc = zonas.get(excluir) if excluir else None
        ref = [p for p in referencia_con_correcciones(pv['referencia']) if p.get('confianza') != 'baja']
        por_modelo = collections.defaultdict(list)
        for tag, mid in pv['tags'].items():
            if tag != excluir:
                por_modelo[mid].append(tag)
        for mid, tags in por_modelo.items():
            if mid in aprendido:
                continue                       # ya aprendido de un plano anterior
            m = modelos_cat[mid]
            r = _aprender_modelo(P, m, mid, tags, comps, ref, zonas, zexc, log)
            if r:
                r['aprendido_de'] = dict(plano=pv['nombre'], tags=tags, **r.get('aprendido_de', {}))
                aprendido[mid] = r
    for mid, m in modelos_cat.items():
        e = {k: v for k, v in m.items()}
        if mid in aprendido:
            e.update(aprendido[mid])
        else:
            e.update(huella=None, bornes={}, nota='sin aprender: no hay un plano verificado con este modelo')
        base['modelos'][mid] = e
    base['segundos_aprendizaje'] = round(time.time() - t0, 1)
    return base


def _uso_de(comps, p):
    c = comps.get(p['componente']) or {}
    for u in c.get('usos', []):
        if u['texto'] == p['texto'] and u['cable'] in p['cables']:
            return u
    return None


def _aprender_modelo(P, m, mid, tags, comps, ref, zonas, zexc, log):
    fisico = m['esquema'] in H.ESQUEMAS_FISICOS
    por_pieza = m['tipo'] in ('pieza', 'modulo')
    pts_tag = {tg: [p for p in ref if p['componente'] == tg] for tg in tags}
    # ------------------------------------------------ 1. semilla
    semilla = None
    for tg in tags:
        ps = pts_tag[tg]
        if not ps:
            continue
        if por_pieza:
            for p in ps:
                mk = P.mascara_de(p['x'], p['y'])
                if mk:
                    semilla = (tg, 'mascara', P.bloque_de_mascara(mk)); break
        else:
            cands = [mk for mk in P.mascaras if all(contiene(mk['bbox'], p['x'], p['y'], 1.0) for p in ps)]
            if cands:
                mk = min(cands, key=lambda mk: mk['area'])
                semilla = (tg, 'mascara', P.bloque_de_mascara(mk))
            else:
                c = P.corrida([(p['x'], p['y']) for p in ps])
                if c:
                    semilla = (tg, 'corrida', c)
        if semilla:
            break
    if not semilla:
        log('  %-15s sin semilla (no hay bornes de referencia)' % mid)
        return None
    tg0, origen, (caja0, A0, B0) = semilla
    ancla = np.array([(caja0[0] + caja0[2]) / 2, (caja0[1] + caja0[3]) / 2])
    color = P.color_en(caja0)
    h = H.hacer_huella(A0, B0, ancla, color)
    # ------------------------------------------------ 2. instancias del mismo dibujo y color
    encontradas = H.buscar(P, h, umbral=0.90, zona=P.region)
    inst = []
    for s, t, (cx, cy) in encontradas:
        b = H.caja_instancia(h, t, cx, cy)
        if H.dist_color(P.color_en(b), color) > H.DIST_COLOR:
            continue
        if zexc and en_zona(b, zexc):
            continue                                  # instancias del tag que se deja afuera: no se usan
        inst.append(dict(t=t, cx=cx, cy=cy, s=s, caja=b))
    es_semilla = lambda i: abs(i['cx'] - ancla[0]) < 0.3 and abs(i['cy'] - ancla[1]) < 0.3
    if not any(es_semilla(i) for i in inst):
        inst.append(dict(t=(0, 0), cx=float(ancla[0]), cy=float(ancla[1]), s=1.0, caja=caja0))
    # ------------------------------------------------ 3. huella de consenso
    otras = [i for i in inst if not es_semilla(i)]
    nseg0 = h['nseg']
    if otras:
        presente = np.zeros((len(h['A']), len(otras)), bool)
        for j, i in enumerate(otras):
            for q, (a, b) in enumerate(zip(h['A'], h['B'])):
                S = H.muestras_de([a], [b], 0.3)
                presente[q, j] = P.sobre_lineas(H.transformar(S, i['t']) + (i['cx'], i['cy'])).mean() >= 0.75
        keep = presente.mean(1) >= 0.5
        if keep.sum() >= 0.6 * len(keep):
            h = H.hacer_huella(h['A'][keep] + ancla, h['B'][keep] + ancla, ancla, color)
    # ------------------------------------------------ 4. bornes en coordenadas del bloque
    obs = collections.defaultdict(list)
    usados = set()
    for tg in tags:
        grupos = collections.defaultdict(list)
        for p in pts_tag[tg]:
            u = _uso_de(comps, p)
            if not u:
                continue
            it = H.interpretar(m, u, tg)
            if not it:
                continue
            cont = [i for i in inst if contiene(i['caja'], p['x'], p['y'], 0.5)]
            if not cont:
                log('  %-15s %s: el borne no cae en ninguna instancia' % (mid, p['texto']))
                continue
            i = min(cont, key=lambda i: math.hypot(i['cx'] - p['x'], i['cy'] - p['y']))
            loc = H.destransformar([(p['x'] - i['cx'], p['y'] - i['cy'])], i['t'])[0]
            clave = it[1]
            if isinstance(clave, list):
                grupos[(p['texto'], tuple(clave))].append((loc, i, p))
                continue
            if fisico and H.arriba_invertido(i['t']):
                clave = H.invertir_clave(clave)
            obs[clave].append(loc); usados.add(id(i))
        for (texto, cands), lst in grupos.items():       # pines con el mismo nombre: de izquierda a derecha
            lst.sort(key=lambda e: e[0][0])
            for (loc, i, p), pin in zip(lst, cands):
                obs[pin].append(loc); usados.add(id(i))
    if not obs:
        log('  %-15s sin bornes aprendidos' % mid)
        return None
    bornes = {}
    for k, L in obs.items():
        L = np.array(L)
        med = np.median(L, axis=0)
        bornes[k] = dict(dx=round(float(med[0]), 3), dy=round(float(med[1]), 3), n=len(L),
                         dispersion=round(float(np.max(np.hypot(*(L - med).T))), 3), origen='referencia')
    for k, b in bornes.items():
        vec = [(o['dx'], o['dy']) for k2, o in bornes.items() if k2 != k]
        b['r'] = H.radio_de_borne(h['A'], h['B'], h['caja'], (b['dx'], b['dy']), vec)
    # ------------------------------------------------ 5. filas de bornes: completar las claves que faltan
    filas = list(m.get('filas', []))
    if fisico:
        filas.append(dict(claves=list(H.CLAVES_4), eje='y'))
    completadas = []
    for fila in filas:
        completadas += completar_fila(P, h, ancla, bornes, fila, caja0)
    completadas += derivar(bornes, m.get('derivados', []))
    for k in completadas:
        vec = [(o['dx'], o['dy']) for k2, o in bornes.items() if k2 != k]
        bornes[k]['r'] = H.radio_de_borne(h['A'], h['B'], h['caja'], (bornes[k]['dx'], bornes[k]['dy']), vec)
    log('  %-15s semilla %-6s (%s) huella %4d seg (de %4d)  instancias %2d  bornes %s%s' % (
        mid, tg0, origen, h['nseg'], nseg0, len(inst), ','.join(sorted(bornes)),
        ('  (completados por fila o derivados: %s)' % ','.join(completadas)) if completadas else ''))
    return dict(huella=H.huella_a_json(h), color=color, ancla='centro de la mascara del bloque' if origen == 'mascara' else 'centro de la corrida de trazos',
                bornes=bornes,
                aprendido_de=dict(semilla=tg0, instancias_en_el_plano=len(inst)))


def derivar(bornes, derivados):
    """Bornes que el dibujo no muestra pero que la hoja de datos ubica respecto de otros ya aprendidos. Cada
    regla del catalogo es {clave, origen, vector: [A, B], t}: clave = origen + t * (B - A). Por ejemplo el PE
    del toma IRAM esta en el medio de N y L (origen N, vector [N, L], t 0.5), o el 4 de la barrera GS8512 esta
    respecto del 3 como el 2 respecto del 1 (origen 3, vector [1, 2], t 1)."""
    nuevas = []
    for d in derivados:
        k, o, (a, b), t = d['clave'], d['origen'], d['vector'], float(d.get('t', 1.0))
        if k in bornes or not all(x in bornes for x in (o, a, b)):
            continue
        bornes[k] = dict(dx=round(bornes[o]['dx'] + t * (bornes[b]['dx'] - bornes[a]['dx']), 3),
                         dy=round(bornes[o]['dy'] + t * (bornes[b]['dy'] - bornes[a]['dy']), 3), n=0, dispersion=0.0,
                         origen='derivado: %s + %g x (%s - %s)%s' % (o, t, b, a, (' [%s]' % d['fuente']) if d.get('fuente') else ''))
        nuevas.append(k)
    return nuevas


def completar_fila(P, h, ancla, bornes, fila, caja0):
    """Bornes de una fila que el plano verificado no uso: el dibujo de cada borne (tornillo, boca push-in) es
    un dibujito que se repite. Se toma el dibujo alrededor de un borne conocido de la fila, se buscan sus
    copias (tambien espejadas) dentro del bloque semilla, y si aparecen tantas copias alineadas como bornes
    tiene la fila, se asignan en orden (eje x: de izquierda a derecha; eje y: de arriba a abajo)."""
    claves = fila['claves']
    conocidas = [k for k in claves if k in bornes]
    if not conocidas or len(conocidas) == len(claves):
        return []
    eje = fila.get('eje', 'x')
    copias = []
    for k in conocidas:
        q = np.array([bornes[k]['dx'], bornes[k]['dy']])
        R = min(3.0, max(1.2, bornes[k].get('r', 1.5) + 0.4))
        sel = (np.hypot(*(h['A'] - q).T) <= R) & (np.hypot(*(h['B'] - q).T) <= R)
        if sel.sum() < 4:
            continue
        for S in ((0, 0), (2, 1), (0, 1), (2, 0)):
            A = H.transformar(h['A'][sel] - q, S); B = H.transformar(h['B'][sel] - q, S)
            patch = dict(A=A, B=B, muestras=H.muestras_de(A, B), caja=(2 * R, 2 * R), hash=H.hash_huella(A, B))
            for s, _, (x, y) in H.buscar(P, patch, [(0, 0)], umbral=0.95, zona=caja0):
                c = np.array([x, y]) - ancla
                if not any(np.hypot(*(c - o)) < 0.6 for o in copias):
                    copias.append(c)
    ref = np.array([[bornes[k]['dx'], bornes[k]['dy']] for k in conocidas])
    mitad = fila.get('mitad')                          # 'arriba' / 'abajo': solo las copias de esa mitad del bloque
    if mitad == 'arriba':
        copias = [c for c in copias if c[1] > 0]
    elif mitad == 'abajo':
        copias = [c for c in copias if c[1] < 0]
    if eje == 'x':
        lin = [c for c in copias if abs(c[1] - ref[:, 1].mean()) < 0.4]
        lin.sort(key=lambda c: c[0])
    else:
        lin = [c for c in copias if abs(c[0] - ref[:, 0].mean()) < 0.4]
        lin.sort(key=lambda c: -c[1])
    if len(lin) != len(claves):
        return []
    for k, c in zip(claves, lin):                      # las conocidas tienen que caer en su lugar
        if k in bornes and np.hypot(bornes[k]['dx'] - c[0], bornes[k]['dy'] - c[1]) > 0.5:
            return []
    nuevas = []
    for k, c in zip(claves, lin):
        if k not in bornes:
            bornes[k] = dict(dx=round(float(c[0]), 3), dy=round(float(c[1]), 3), n=0, dispersion=0.0,
                             origen='fila: copia del dibujo de %s' % '/'.join(conocidas))
            nuevas.append(k)
    return nuevas


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    excluir = None
    if '--sin' in sys.argv:
        excluir = sys.argv[sys.argv.index('--sin') + 1]
        args = [a for a in args if a != excluir]
    cat_path = args[0] if len(args) > 0 else os.path.join(AQUI, 'catalogo_modelos.json')
    out_path = args[1] if len(args) > 1 else os.path.join(AQUI, 'base_bornes.json')
    cat = H.cargar_json(cat_path)
    print('Aprendiendo la base de bornes%s...' % (' sin %s' % excluir if excluir else ''))
    base = aprender(cat, excluir=excluir, planos={})
    H.guardar_json(out_path, base)
    n = sum(1 for m in base['modelos'].values() if m.get('huella'))
    print('Base: %d modelos aprendidos de %d, %d bornes -> %s (%.1f s)' % (
        n, len(base['modelos']), sum(len(m['bornes']) for m in base['modelos'].values()), out_path, base['segundos_aprendizaje']))


if __name__ == '__main__':
    main()
