"""Mapeo de bornes por VISION DE IMAGEN (prototipo P5).

uso:  python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json> [--materiales lista_materiales.txt]
                       [--control control.png]

Que hace, para cada componente de usos_por_componente.json:
  1. Renderiza la pagina (pypdfium2) y ubica la etiqueta amarilla del tag mirando el COLOR de la imagen.
  2. Arma la zona de busqueda: a la DERECHA de la etiqueta hasta la etiqueta siguiente del mismo riel
     (borneras y reles, regla del taller) o centrada en la etiqueta (aparatos con la etiqueta encima).
  3. Busca en esa zona las plantillas de imagen del modelo (cv2.matchTemplate + supresion de no-maximos).
  4. Agrupa las bocas encontradas segun la estructura del modelo (piezas, modulos, polos, filas) y las nombra
     por orden con el mapa de nombres de la base (base/modelos.json).
El modelo de cada tag sale de la lista de materiales si esta (lista_materiales.txt en la carpeta de los usos, o
--materiales); si no esta o no coincide con el dibujo, se reconoce por la imagen (la plantilla que mejor encaja).

No lee la estructura vectorial del PDF ni la respuesta de referencia: solo la imagen renderizada, los usos
(texto del instructivo + posicion de la etiqueta) y la base de plantillas.
"""
import argparse
import json
import math
import os
import re
import sys
import time
import unicodedata

import cv2
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import estructuras  # noqa: E402
import vision  # noqa: E402

MARGEN_PT = 1.5  # margen de la zona de busqueda alrededor del aparato
# plano escaneado (la bandeja es una imagen de menos de 10 px/pt): como se ajusta la comparacion de plantillas
ESCANEO = dict(suavizado=0.4,        # suavizado = esta fraccion de un pixel del escaneo (en px de trabajo)
               degradar=False,       # achicar la plantilla a la resolucion del escaneo antes de comparar
               umbral_ncc=0.45,      # umbral absoluto mas bajo que en vectorial (el escaneo esta sucio)
               umbral_relativo=0.8)  # y ademas >= 0.8 x la mejor boca encontrada en la zona


# ----------------------------------------------------------------------------------------------
# Base de datos
# ----------------------------------------------------------------------------------------------
class Base:
    def __init__(self, carpeta):
        self.carpeta = carpeta
        m = json.load(open(os.path.join(carpeta, 'modelos.json'), encoding='utf-8'))
        self.modelos = m['modelos']
        self.umbral = m.get('umbral_ncc', 0.6)
        idx_todo = json.load(open(os.path.join(carpeta, 'plantillas.json'), encoding='utf-8'))
        idx = idx_todo['plantillas']
        # escala (mm por pt) del plano del que se recortaron las plantillas: en un plano de otra escala las
        # plantillas se agrandan/achican en la misma proporcion (ver factor_escala)
        self.mm_por_pt = idx_todo.get('mm_por_pt')
        self.k = 1.0
        self.plantillas = {k: vision.Plantilla.cargar(k, v, carpeta) for k, v in idx.items()}
        self.cache = {}
        self.alto_riel_mm = max([m['zona']['alto_mm'] for m in self.modelos.values() if m['zona']['tipo'] == 'derecha'] or [100])
        for nombre, mod in self.modelos.items():
            mod['_nombre'] = nombre
            if mod['estructura'] == 'aparato':
                an = {}
                for p in mod['plantillas']:
                    an.update(self.plantillas[p].info.get('anclas_px', {}))
                mod['_anclas'] = an


def _norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', '', s.upper())


def leer_materiales(path, base):
    """lista_materiales.txt -> {tag: nombre_modelo}. Cada renglon se asocia al tag que aparece en el; el modelo es el
    alias mas largo de la base que aparece en el renglon (o en el renglon siguiente sin tag)."""
    if not path or not os.path.exists(path):
        return {}
    lineas = [l.strip() for l in open(path, encoding='utf-8') if l.strip()]
    pat_tag = re.compile(r'^\d{2}[A-Z]+\d*$')
    por_tag = {}
    ultimo = None
    for l in lineas:
        campos = [c.strip() for c in l.split('|')]
        tags = [c for c in campos if pat_tag.match(c)]
        if tags:
            ultimo = tags[0]
            por_tag[ultimo] = por_tag.get(ultimo, '') + ' ' + l
        elif ultimo:
            por_tag[ultimo] += ' ' + l
    alias = []
    for nombre, mod in base.modelos.items():
        for a in [nombre, mod.get('codigo', '').split(' ')[0]] + mod.get('alias', []):
            if a and len(_norm(a)) >= 3:
                alias.append((_norm(a), nombre))
    alias.sort(key=lambda t: -len(t[0]))
    out = {}
    for tag, txt in por_tag.items():
        t = _norm(txt)
        for a, nombre in alias:
            if a in t:
                out[tag] = nombre
                break
    return out


def modelo_de_materiales(tag, mat):
    if tag in mat:
        return mat[tag]
    raiz = re.sub(r'\d+$', '', tag)
    for t, m in mat.items():
        if re.sub(r'\d+$', '', t) == raiz and raiz != t:
            return m
    return None


# ----------------------------------------------------------------------------------------------
# Etiquetas y zonas
# ----------------------------------------------------------------------------------------------
def etiqueta_de(comp, etiquetas):
    e = comp['etiqueta_topografico']
    x, y = e['x'], e['y']
    dentro = [q for q in etiquetas if q['x0'] - 1 <= x <= q['x1'] + 1 and q['y0'] - 1 <= y <= q['y1'] + 1]
    if dentro:
        q = min(dentro, key=lambda q: (q['x1'] - q['x0']) * (q['y1'] - q['y0']))
    else:
        cerca = sorted(etiquetas, key=lambda q: math.hypot(q['xc'] - x, q['yc'] - y))
        q = cerca[0] if cerca and math.hypot(cerca[0]['xc'] - x, cerca[0]['yc'] - y) < 6 else None
    if q is None:  # sin caja amarilla: caja chica alrededor del punto
        q = dict(x0=x - 2.5, x1=x + 2.5, y0=y - 8.5, y1=y + 8.5, xc=x, yc=y, vertical=True, sintetica=True)
    return dict(q)


def siguiente_en_riel(et, etiquetas):
    """Etiqueta siguiente a la derecha en el mismo riel: la mas cercana cuyo alto se solapa con el de esta."""
    sig = [q for q in etiquetas if q['x0'] > et['x1'] - 0.5 and min(q['y1'], et['y1']) - max(q['y0'], et['y0']) > 0.3 * (et['y1'] - et['y0'])
           and abs(q['yc'] - et['yc']) < 6]
    return min(sig, key=lambda q: q['x0']) if sig else None


def zona_de(mod, et, etiquetas, esc, region, alto_riel_mm=None):
    """Zona de busqueda [x0, y0, x1, y1] en pt. 'derecha': desde la etiqueta hasta la etiqueta siguiente del mismo
    riel, con el MISMO alto para todos los modelos de riel (el del aparato mas alto de la base), asi los modelos
    candidatos se comparan sobre la misma imagen. 'centrada': el ancho del aparato y el doble de su alto alrededor
    de la etiqueta (la etiqueta no siempre esta en el centro del aparato)."""
    z = mod['zona']
    if z['tipo'] == 'derecha':
        sig = siguiente_en_riel(et, etiquetas)
        x0 = et['x0'] - 1.0
        x1 = sig['x0'] if sig else min(region[2], et['x1'] + 40 * mod['paso_mm'] / esc)
        h = 0.6 * (alto_riel_mm or z['alto_mm']) / esc
        y0, y1 = et['yc'] - h, et['yc'] + h
    else:
        w = z['ancho_mm'] / esc / 2 + MARGEN_PT
        h = z['alto_mm'] / esc
        x0, x1 = et['xc'] - w, et['xc'] + w
        y0, y1 = et['yc'] - h, et['yc'] + h
    return [max(region[0], x0), max(region[1], y0), min(region[2], x1), min(region[3], y1)]


class Ctx:
    pass


def detectar(plano, base, mod, et, etiquetas, esc, region):
    zona = zona_de(mod, et, etiquetas, esc, region, base.alto_riel_mm)
    zn = plano.zona(*zona)
    dets = []
    for pn in mod['plantillas']:
        pl = base.plantillas[pn]
        umbral = mod.get('umbral_ncc', base.umbral)
        umbral_rel = None
        if plano.res_fuente and plano.res_fuente < vision.S:  # escaneado: umbral bajo + relativo a la mejor boca
            umbral = min(umbral, ESCANEO['umbral_ncc'])
            umbral_rel = mod.get('umbral_relativo_escaneo', ESCANEO['umbral_relativo'])
        var = tuple(mod.get('variantes', ['normal']))
        escs = tuple(round(e * base.k, 4) for e in mod.get('escalas', [1.0]))  # base.k: escala del plano nuevo
        clave = (tuple(round(v, 1) for v in zona), pn, var, escs, umbral, umbral_rel)
        if clave not in base.cache:  # dos modelos con la misma plantilla y la misma zona: se busca una sola vez
            base.cache[clave] = vision.buscar(zn, pl, variantes=var, escalas=escs, umbral=umbral, sigma=plano.sigma_px(ESCANEO['suavizado']),
                                              res=plano.res_fuente if ESCANEO['degradar'] else None, umbral_rel=umbral_rel)
        for d in base.cache[clave]:
            dets.append(dict(d, plantilla=pn))
    ctx = Ctx()
    ctx.esc, ctx.zona_color, ctx.plantillas = esc, zn, base.plantillas
    det = estructuras.DETECTORES[mod['estructura']](ctx, mod, dets, et, zona)
    if det is not None:
        det.zona = zona
        det.n_dets = len(dets)
    return det


# ----------------------------------------------------------------------------------------------
# Un componente
# ----------------------------------------------------------------------------------------------
def _num(c):
    try:
        return int(re.sub(r'\D', '', c) or 0)
    except ValueError:
        return 0


def resolver_componente(tag, comp, plano, base, etiquetas, esc, region, mat_modelo):
    et = etiqueta_de(comp, etiquetas)
    usos = comp['usos']
    # 1) modelos que entienden los textos del instructivo
    cuenta = {}
    for nombre, mod in base.modelos.items():
        n = sum(1 for u in usos if estructuras.parsear(mod, u, tag) is not None)
        if n:
            cuenta[nombre] = n
    if not cuenta:
        return et, None, {}, 'ningun modelo de la base entiende los textos de este tag'
    mx = max(cuenta.values())
    cands = [n for n, c in cuenta.items() if c == mx]
    # 2) deteccion en la imagen con cada candidato
    dets = {}
    for n in cands:
        d = detectar(plano, base, base.modelos[n], et, etiquetas, esc, region)
        if d is not None and d.calidad > 0:
            dets[n] = d
    if not dets:
        return et, None, {}, 'no se encontraron bocas de ningun modelo candidato (' + ', '.join(cands) + ')'
    mejor = max(dets, key=lambda n: dets[n].calidad)
    elegido, motivo = mejor, 'reconocido por la imagen'
    if mat_modelo in dets and dets[mat_modelo].calidad >= 0.75 * dets[mejor].calidad:
        elegido, motivo = mat_modelo, 'lista de materiales (confirmado por la imagen)'
    elif mat_modelo and mat_modelo not in cuenta:
        motivo = f'reconocido por la imagen (la lista de materiales dice {mat_modelo}, que no entiende los textos)'
    elif mat_modelo and mat_modelo != mejor:
        motivo = f'reconocido por la imagen (la lista de materiales dice {mat_modelo}, que encaja peor)'
    empates = [n for n in dets if n != elegido and dets[n].calidad >= 0.98 * dets[elegido].calidad]
    if empates and 'materiales' not in motivo:
        motivo += '; empata con ' + ', '.join(empates) + ' (el dibujo no los distingue)'
    info = dict(candidatos={n: round(d.calidad, 3) for n, d in dets.items()}, motivo=motivo)
    return et, dets[elegido], info, None


def ubicar_usos(tag, comp, det, usos_pendientes=None):
    """Devuelve lista de (uso, resultado|None) con resultado = (x, y, conf, como)."""
    mod = det.modelo
    usos = comp['usos']
    dires = [estructuras.parsear(mod, u, tag) for u in usos]
    # rele sin numero de modulo: el modulo cuyos otros cables tienen el numero mas cercano
    if mod['estructura'] == 'rele':
        con_mod = [(u, d) for u, d in zip(usos, dires) if d and d[1] is not None]
        for i, (u, d) in enumerate(zip(usos, dires)):
            if d and d[1] is None and con_mod:
                ref = min(con_mod, key=lambda t: abs(_num(t[0]['cable']) - _num(u['cable'])))
                dires[i] = (d[0], ref[1][1], d[2], d[3])
                usos[i] = dict(u, _nota=f"modulo {ref[1][1]} por cercania con el cable {ref[0]['cable']}")
    out = []
    for i, (u, d) in enumerate(zip(usos, dires)):
        if d is None:
            out.append((u, None))
            continue
        if mod['estructura'] == 'fuente':
            iguales = sorted([usos[k] for k in range(len(usos)) if dires[k] == d], key=lambda q: _num(q['cable']))
            orden = [q['cable'] for q in iguales].index(u['cable'])
            r = det.ubicar(d) if orden == 0 and len(iguales) == 1 else det._ub(d, u['cable'], orden)
            if r and len(iguales) > 1:
                r = (r[0], r[1], 'media', r[3] + f'; {len(iguales)} cables con el mismo nombre: se reparten por numero de cable')
        else:
            r = det.ubicar(d)
        if r and u.get('_nota'):
            r = (r[0], r[1], 'media', r[3] + '; ' + u['_nota'])
        out.append((u, r))
    return out


# ----------------------------------------------------------------------------------------------
# Principal
# ----------------------------------------------------------------------------------------------
def mapear(pdf, usos_path, salida, materiales=None, control=None, base_dir=None):
    t0 = time.time()
    U = json.load(open(usos_path, encoding='utf-8'))
    esc = U['escala_mm_por_pt']
    region = U.get('region_bandeja')
    base = Base(base_dir or os.path.join(AQUI, 'base'))
    if base.mm_por_pt:  # plano dibujado a otra escala que el de las plantillas: se escalan las plantillas
        base.k = base.mm_por_pt / esc
    plano = vision.Plano(pdf, U['pagina_pdf'] - 1)
    if not region:
        region = [0, 0, plano.W, plano.H]
    plano.medir_resolucion(region)  # plano escaneado: resolucion de la imagen (para suavizar la comparacion)
    etiquetas = vision.etiquetas_amarillas(plano, region)
    if materiales is None:
        cand = os.path.join(os.path.dirname(os.path.abspath(usos_path)), 'lista_materiales.txt')
        materiales = cand if os.path.exists(cand) else None
    mat = leer_materiales(materiales, base)

    puntos, componentes, detecciones = [], {}, {}
    pendientes = []  # usos cuyo borne no existe en su tag (se prueban en la etiqueta vecina)
    for tag, comp in U['componentes'].items():
        mm = modelo_de_materiales(tag, mat)
        et, det, info, error = resolver_componente(tag, comp, plano, base, etiquetas, esc, region, mm)
        componentes[tag] = dict(etiqueta=[round(et['x0'], 2), round(et['y0'], 2), round(et['x1'], 2), round(et['y1'], 2)],
                                modelo_materiales=mm)
        if det is None:
            componentes[tag]['error'] = error
            for u in comp['usos']:
                pendientes.append((tag, u, error))
            continue
        detecciones[tag] = (et, det)
        componentes[tag].update(modelo=det.modelo['_nombre'], zona=[round(v, 1) for v in det.zona], calidad=round(det.calidad, 3),
                                **info, **{k: v for k, v in det.info.items()})
        for u, r in ubicar_usos(tag, comp, det):
            if r is None:
                pendientes.append((tag, u, 'el borne no existe en lo que se encontro a la derecha de la etiqueta'))
                continue
            puntos.append(dict(texto=u['texto'], cables=[u['cable']], x=round(r[0], 2), y=round(r[1], 2), r=round(det.modelo['r_pt'] * base.k, 2),
                               confianza=r[2], tag=tag, tag_fisico=tag, modelo=det.modelo['_nombre'], como=r[3]))

    def vecino(tag):
        """(tag, deteccion) de la etiqueta siguiente del mismo riel, si se detecto."""
        if tag not in detecciones:
            return None, None
        sig = siguiente_en_riel(detecciones[tag][0], etiquetas)
        if not sig:
            return None, None
        vec = [t for t, (e2, _) in detecciones.items() if abs(e2['xc'] - sig['xc']) < 0.5 and abs(e2['yc'] - sig['yc']) < 0.5]
        return (vec[0], detecciones[vec[0]][1]) if vec else (None, None)

    def en_vecino(tag, u):
        """El mismo borne del texto, buscado en la etiqueta vecina: (tag_vecino, deteccion, resultado) o None."""
        t2, det2 = vecino(tag)
        if det2 is None:
            return None
        d2 = estructuras.parsear(det2.modelo, u, tag)
        r = det2.ubicar(d2) if d2 else None
        return (t2, det2, r) if r else None

    # usos que no se pudieron ubicar en su tag: se prueba el mismo borne en la etiqueta siguiente del mismo riel
    # (el instructivo a veces confunde dos borneras vecinas, p. ej. un diodo y la bornera de comandos de al lado)
    sin_punto = []
    for tag, u, motivo in pendientes:
        v = en_vecino(tag, u)
        if v:
            t2, det2, r = v
            puntos.append(dict(texto=u['texto'], cables=[u['cable']], x=round(r[0], 2), y=round(r[1], 2), r=round(det2.modelo['r_pt'] * base.k, 2),
                               confianza='baja', tag=tag, tag_fisico=t2, modelo=det2.modelo['_nombre'],
                               como=f"{tag} no tiene ese borne ({motivo}); se toma el mismo borne en la etiqueta vecina {t2}: " + r[3]))
        else:
            sin_punto.append(dict(texto=u['texto'], cable=u['cable'], tag=tag, motivo=motivo))

    # bocas push-in con dos cables distintos: en una boca de bornera entra UN cable. Si el instructivo manda dos
    # cables distintos a la misma boca, uno esta anotado con el tag de la bornera de al lado. Se queda el que
    # menos se parece (por numero) a los cables propios de la etiqueta vecina; los otros se prueban en el mismo
    # borne de la vecina, si esa boca esta libre.
    ocupadas = {(p['x'], p['y']) for p in puntos}
    for tag, (et, det) in detecciones.items():
        if det.modelo['estructura'] != 'bornera':
            continue
        grupos = {}
        for p in puntos:
            if p.get('tag_fisico') == tag and p['modelo'] == det.modelo['_nombre']:
                grupos.setdefault((p['x'], p['y']), []).append(p)
        t2, _ = vecino(tag)
        propios_vec = [_num(u['cable']) for u in U['componentes'].get(t2, {}).get('usos', [])] if t2 else []
        for key, ps in grupos.items():
            if len({p['cables'][0] for p in ps}) < 2:
                continue
            if not propios_vec:
                for p in ps:
                    p['confianza'] = 'media' if p['confianza'] == 'alta' else p['confianza']
                    p['como'] += '; ATENCION: dos cables en la misma boca push-in (revisar el instructivo)'
                continue
            afin = {id(p): min(abs(_num(p['cables'][0]) - n) for n in propios_vec) for p in ps}
            queda = max(ps, key=lambda p: (afin[id(p)], -ps.index(p)))
            for p in ps:
                if p is queda:
                    continue
                u = next(q for q in U['componentes'][p['tag']]['usos'] if q['cable'] == p['cables'][0] and q['texto'] == p['texto'])
                v = en_vecino(tag, u)
                if not v or (round(v[2][0], 2), round(v[2][1], 2)) in ocupadas:
                    for q in (p, queda):
                        if 'ATENCION' not in q['como']:
                            q['confianza'] = 'media' if q['confianza'] == 'alta' else q['confianza']
                            q['como'] += (f"; ATENCION: dos cables ({queda['cables'][0]} y {p['cables'][0]}) en la misma boca push-in "
                                          f"y la etiqueta vecina no tiene ese borne libre: revisar el instructivo")
                    continue
                t2, det2, r = v
                p.update(x=round(r[0], 2), y=round(r[1], 2), r=round(det2.modelo['r_pt'] * base.k, 2), confianza='baja', tag_fisico=t2, modelo=det2.modelo['_nombre'],
                         como=f"la boca de {p['texto']} en {tag} ya la ocupa el cable {queda['cables'][0]} y en una boca push-in entra un "
                              f"solo cable; el cable {p['cables'][0]} se parece mas a los de {t2} (diferencia de numero "
                              f"{afin[id(p)]}), se toma el mismo borne en {t2}: " + r[3])
                ocupadas.add((p['x'], p['y']))

    seg = round(time.time() - t0, 2)
    res = dict(descripcion='Bornes ubicados por vision de imagen (prototipo P5): plantillas de imagen por tipo de boca + regla del tag',
               metodo='P5_vision_imagen', topografico=os.path.abspath(pdf), pagina_pdf=U['pagina_pdf'], materiales=materiales,
               segundos=seg, imagen=dict(resolucion_escaneo_px_por_pt=plano.res_fuente, suavizado_px=round(plano.sigma_px(ESCANEO['suavizado']), 2)),
               puntos=puntos, sin_punto=sin_punto, componentes=componentes)
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    json.dump(res, open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    if control:
        dibujar_control(plano, region, res, control, etiquetas)
    return res


# ----------------------------------------------------------------------------------------------
# Imagen de control
# ----------------------------------------------------------------------------------------------
COL = {'alta': (0, 160, 0), 'media': (0, 140, 255), 'baja': (0, 0, 230)}


def dibujar_control(plano, region, res, path, etiquetas):
    """Un panel ampliado por grupo de componentes vecinos: cada punto con un circulo del radio r del borne (color
    = confianza) y un numero; al costado, la leyenda numero -> texto del instructivo [cable] (modelo)."""
    s = 8
    pts = res['puntos']
    comps = res['componentes']
    cajas = []
    for tag, c in comps.items():
        ps = [p for p in pts if p['tag'] == tag]
        if not ps:
            continue
        xs = [p['x'] for p in ps] + [c['etiqueta'][0], c['etiqueta'][2]]
        ys = [p['y'] for p in ps] + [c['etiqueta'][1], c['etiqueta'][3]]
        cajas.append([min(xs) - 5, min(ys) - 5, max(xs) + 5, max(ys) + 5, [tag]])
    grupos = []
    for b in sorted(cajas, key=lambda b: (-b[3], b[0])):
        for g in grupos:
            if b[0] < g[2] + 3 and b[2] > g[0] - 3 and b[1] < g[3] and b[3] > g[1] and max(g[2], b[2]) - min(g[0], b[0]) < 140:
                g[:4] = [min(g[0], b[0]), min(g[1], b[1]), max(g[2], b[2]), max(g[3], b[3])]
                g[4] += b[4]
                break
        else:
            grupos.append(list(b))
    F = cv2.FONT_HERSHEY_SIMPLEX
    paneles = []
    for g in sorted(grupos, key=lambda g: (-g[3], g[0])):
        dentro = sorted([p for p in pts if p['tag'] in g[4]], key=lambda p: (p['x'], -p['y']))
        # escala del panel: en las zonas apretadas (reles, bornes QUATTRO, borneras angostas) se amplia mas, para
        # que entre el rotulo de cada punto sin tapar los vecinos
        claves = sorted({(round(p['x'], 1), round(p['y'], 1)) for p in dentro})
        dmin = min([math.hypot(a[0] - b[0], a[1] - b[1]) for k, a in enumerate(claves) for b in claves[k + 1:]] or [10.0])
        sg = int(np.clip(round(46 / max(dmin, 0.5)), s, 16))
        sg = min(sg, max(s, int(2200 / max(1.0, g[2] - g[0]))))
        z = plano.zona(*g[:4], s=sg)
        im = cv2.addWeighted(z.bgr, 0.45, np.full_like(z.bgr, 255), 0.55, 0)
        ley = []
        vistos = {}
        circulos = []
        for p in dentro:
            key = (round(p['x'], 1), round(p['y'], 1))
            if key not in vistos:
                vistos[key] = len(vistos) + 1
            n = vistos[key]
            j, i = z.px(p['x'], p['y'])
            c = COL.get(p['confianza'], (255, 0, 255))
            rp = max(3, int(round(p['r'] * sg)))
            cv2.circle(im, (int(round(j)), int(round(i))), rp, c, 2, cv2.LINE_AA)
            cv2.drawMarker(im, (int(round(j)), int(round(i))), (0, 0, 0), cv2.MARKER_CROSS, 9, 1)
            circulos.append((j, i, rp))
            ley.append((n, f"{n:2d}  {p['texto']}  [{p['cables'][0]}]", c))
        # rotulos con caja blanca, puestos alrededor del circulo en el primer lugar libre (sin pisar circulos ni
        # otros rotulos); si queda lejos se une al circulo con una raya fina
        cajas_t = []
        fs = 0.5

        def choca(b):
            x0, y0, x1, y1 = b
            if x0 < 0 or y0 < 0 or x1 >= im.shape[1] or y1 >= im.shape[0]:
                return 1e9
            pen = 0.0
            for (cj, ci, cr) in circulos:
                dx = max(x0 - cj, 0, cj - x1); dy = max(y0 - ci, 0, ci - y1)
                if math.hypot(dx, dy) < cr + 1:
                    pen += 1
            for q in cajas_t:
                if x0 < q[2] + 1 and x1 > q[0] - 1 and y0 < q[3] + 1 and y1 > q[1] - 1:
                    pen += 3
            return pen

        for key, n in vistos.items():
            j, i = z.px(*key)
            rp = next(cr for (cj, ci, cr) in circulos if abs(cj - j) < 1.5 and abs(ci - i) < 1.5) if circulos else 6
            t = str(n)
            (tw, th), bl = cv2.getTextSize(t, F, fs, 1)
            bw, bh = tw + 6, th + bl + 4
            mejor = None
            for dist in (rp + 2, rp + 10, rp + 22):
                for ang in (45, 135, -45, -135, 0, 180, 90, -90):
                    a = math.radians(ang)
                    cx, cy = j + math.cos(a) * (dist + bw / 2), i - math.sin(a) * (dist + bh / 2)
                    b = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
                    pen = choca(b)
                    if mejor is None or pen < mejor[0]:
                        mejor = (pen, b, dist)
                    if pen == 0:
                        break
                if mejor[0] == 0:
                    break
            _, b, dist = mejor
            b = tuple(int(round(v)) for v in b)
            if dist > rp + 3:
                bx, by = min(max(j, b[0]), b[2]), min(max(i, b[1]), b[3])
                cv2.line(im, (int(round(j)), int(round(i))), (int(bx), int(by)), (160, 0, 160), 1, cv2.LINE_AA)
            cv2.rectangle(im, (b[0], b[1]), (b[2], b[3]), (255, 255, 255), -1)
            cv2.rectangle(im, (b[0], b[1]), (b[2], b[3]), (160, 0, 160), 1)
            cv2.putText(im, t, (b[0] + 3, b[3] - bl - 1), F, fs, (160, 0, 160), 1, cv2.LINE_AA)
            cajas_t.append(b)
        modelos = sorted({f"{p['tag']}: {p['modelo']}" for p in dentro})
        lineas = [(None, ' / '.join(modelos[k:k + 2]), (0, 0, 0)) for k in range(0, len(modelos), 2)] + ley
        alto_l = 16 * len(lineas) + 10
        ancho_l = max(cv2.getTextSize(t, F, 0.42, 1)[0][0] for _, t, _ in lineas) + 16
        h = max(im.shape[0], alto_l)
        pan = np.full((h + 22, im.shape[1] + ancho_l, 3), 255, np.uint8)
        pan[22:22 + im.shape[0], :im.shape[1]] = im
        cv2.putText(pan, f"x {g[0]:.0f}..{g[2]:.0f}  y {g[1]:.0f}..{g[3]:.0f} pt", (4, 16), F, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        for k, (_, t, c) in enumerate(lineas):
            cv2.putText(pan, t, (im.shape[1] + 10, 38 + 16 * k), F, 0.42, c, 1, cv2.LINE_AA)
        cv2.rectangle(pan, (0, 0), (pan.shape[1] - 1, pan.shape[0] - 1), (190, 190, 190), 1)
        paneles.append(pan)
    # mosaico en filas de hasta 2600 px
    filas, fila, ancho = [], [], 0
    for pn in paneles:
        if fila and ancho + pn.shape[1] > 2600:
            filas.append(fila); fila, ancho = [], 0
        fila.append(pn); ancho += pn.shape[1] + 12
    if fila:
        filas.append(fila)
    bloques = []
    for f in filas:
        h = max(pn.shape[0] for pn in f)
        row = []
        for pn in f:
            pad = np.full((h, pn.shape[1] + 12, 3), 255, np.uint8)
            pad[:pn.shape[0], :pn.shape[1]] = pn
            row.append(pad)
        bloques.append(np.hstack(row))
    W = max(b.shape[1] for b in bloques)
    bloques = [np.hstack([b, np.full((b.shape[0], W - b.shape[1], 3), 255, np.uint8)]) for b in bloques]
    cab = np.full((34, W, 3), 255, np.uint8)
    cv2.putText(cab, f"P5 vision por imagen - {len(pts)} puntos.  Circulo = radio r del borne.  Verde = confianza alta, naranja = media, "
                     f"rojo = baja.  Numero -> leyenda al costado.", (6, 23), F, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    out = [cab]
    for b in bloques:
        out += [b, np.full((12, W, 3), 255, np.uint8)]
    cv2.imwrite(path, np.vstack(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pdf')
    ap.add_argument('usos')
    ap.add_argument('salida')
    ap.add_argument('--materiales', default=None, help='lista de materiales (por defecto lista_materiales.txt junto a los usos)')
    ap.add_argument('--control', default=None, help='imagen de control (por defecto control.png junto a la salida)')
    ap.add_argument('--base', default=None, help='carpeta de la base (por defecto base/ junto a mapear.py)')
    a = ap.parse_args()
    control = a.control or os.path.join(os.path.dirname(os.path.abspath(a.salida)), 'control.png')
    res = mapear(a.pdf, a.usos, a.salida, a.materiales, control, a.base)
    n = sum(len(c['usos']) for c in json.load(open(a.usos, encoding='utf-8'))['componentes'].values())
    print(f"{len(res['puntos'])} puntos de {n} usos en {res['segundos']} s  ->  {a.salida}")
    for tag, c in res['componentes'].items():
        print(f"  {tag:8s} {c.get('modelo', '-'):20s} {c.get('motivo', c.get('error', ''))}")
    for s in res['sin_punto']:
        print(f"  SIN PUNTO: {s['texto']} [{s['cable']}]: {s['motivo']}")


if __name__ == '__main__':
    main()
