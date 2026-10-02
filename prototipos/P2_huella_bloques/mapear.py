"""Mapea los bornes de un topografico nuevo con la base de huellas de bloques (P2).

uso:  python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json>
                       [--base base_bornes.json] [--materiales lista_materiales.txt] [--control control.png]

Solo lee la base (base_bornes.json, la genera aprender.py). No tiene coordenadas de ningun tablero.
Pasos:
  1. Lee los trazos de la pagina del topografico (la pagina y la region de la bandeja salen de los usos).
  2. Busca cada bloque de la base por su huella (hashing geometrico, giros de 90 grados y espejo), verifica
     cada candidato (puntaje directo e inverso) y el color, y resuelve solapes entre modelos (gana el que
     mejor explica el dibujo).
  3. Para cada componente de los usos arma su zona: desde su etiqueta amarilla hasta la etiqueta siguiente
     del mismo riel (regla del taller). Elige el modelo: el de la lista de materiales, si su bloque esta en la
     zona; si no, el bloque reconocido en la zona (reconocimiento vectorial).
  4. Cada uso del instructivo se traduce a (pieza/modulo, borne generico) segun el esquema del modelo y se
     transfiere el desplazamiento aprendido del borne, con el giro de la instancia.
La lista de materiales es opcional: por defecto se usa lista_materiales.txt de la carpeta de los usos.
"""
import sys, os, re, math, time, json, collections

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import huellas as H
from huellas import zonas_de, en_zona, contiene

GAP_MAX = 10.0        # pt: un hueco mayor entre piezas corta la bornera (otro grupo)


# ============================================================================================ instancias
def instancias(plano, base, region=None, log=None):
    """Busca todos los modelos aprendidos. Devuelve la lista de instancias aceptadas (sin solapes)."""
    todas = []
    for mid, m in base['modelos'].items():
        if not m.get('huella') or not m.get('bornes'):
            continue
        h = H.huella_de_json(m['huella'])
        m['_h'] = h
        for s, t, (cx, cy) in H.buscar(plano, h, zona=region or plano.region):
            b = H.caja_instancia(h, t, cx, cy)
            col = plano.color_en(b)
            if H.dist_color(col, m.get('color')) > H.DIST_COLOR:
                continue
            inv = H.puntaje_inverso(plano, h, t, cx, cy)
            todas.append(dict(modelo=mid, t=tuple(t), cx=cx, cy=cy, directo=round(s, 3), inverso=round(inv, 3),
                              caja=b, nseg=h['nseg'], tipo=m['tipo']))
    todas.sort(key=lambda i: (-(i['directo'] + i['inverso']) / 2, -i['nseg']))
    out = []
    for i in todas:
        if any(H.iou(i['caja'], o['caja']) > 0.3 or H.contencion(i['caja'], o['caja']) > 0.85 for o in out):
            continue
        out.append(i)
    return out


# ============================================================================================ boca doble
def _num(s):
    s = re.sub(r'\D', '', str(s or ''))
    return int(s) if s else None


def corregir_boca_doble(puntos, elegidos, zonas, orden_riel, modelos, ubicar):
    """Bornes de riel push-in (tipo 'pieza'): cada boca recibe UN cable. Si el instructivo manda dos cables
    distintos a la misma boca, casi siempre es el error de 'tag de la bornera vecina' (el mismo que el
    desborde, pero con un numero que tambien existe en esta bornera). Se prueba mover cada cable al mismo
    numero y lado de la bornera siguiente del riel: se mueve el que respeta el orden de numeracion de los
    cables de esa bornera (numero de borne mayor -> numero de cable mayor) y los otros no, siempre que la boca
    de destino este libre. Si no hay un unico candidato claro, no se toca (queda para revisar)."""
    grupos = collections.defaultdict(list)
    for p in puntos:
        c = p['componente']
        e = elegidos.get(c) or {}
        if not e.get('modelo') or modelos[e['modelo']]['tipo'] != 'pieza' or p.get('_dest') != c or not p.get('_u'):
            continue
        grupos[(c, round(p['x'], 1), round(p['y'], 1))].append(p)
    for (c, _, _), ps in grupos.items():
        if len({p['cables'][0] for p in ps}) < 2:
            continue
        k = orden_riel.index(c)
        sig = orden_riel[k + 1] if k + 1 < len(orden_riel) else None
        e2 = elegidos.get(sig) if sig and zonas[sig]['riel'] == zonas[c]['riel'] else None
        if not e2 or not e2.get('modelo') or modelos[e2['modelo']]['tipo'] != 'pieza':
            continue
        en_sig = [q for q in puntos if q.get('_dest') == sig and q.get('_u') and _num(q['_u'].get('borne')) is not None]
        opciones = []
        for p in ps:
            u = p['_u']
            n, cab = _num(u.get('borne')), _num(p['cables'][0])
            if n is None or cab is None:
                continue
            res, _ = ubicar(sig, dict(u, tag=sig), e2['modelo'])
            if not res:
                continue
            x, y = res[0], res[1]
            if any(math.hypot(q['x'] - x, q['y'] - y) < 0.5 for q in puntos):
                continue                                   # la boca de destino ya tiene cable
            viol = 0
            for q in en_sig:
                nq, cq = _num(q['_u'].get('borne')), _num(q['cables'][0])
                if cq is None:
                    continue
                if (nq < n and cq > cab) or (nq > n and cq < cab):
                    viol += 1
            opciones.append((viol, p, res))
        if not opciones:
            continue
        opciones.sort(key=lambda o: o[0])
        if opciones[0][0] != 0 or (len(opciones) > 1 and opciones[1][0] == 0) or len(opciones) < len(ps):
            continue                                       # no hay un unico candidato claro
        viol, p, (x, y, r, como, i) = opciones[0]
        otros = [q['cables'][0] for q in ps if q is not p]
        p.update(x=round(x, 2), y=round(y, 2), r=r, modelo=i['modelo'], confianza='baja', _dest=sig, _i=i,
                 como='BOCA DOBLE: el instructivo manda %s y %s a la misma boca de %s (un borne push-in recibe un solo '
                      'cable); %s respeta el orden de numeracion de los cables de la bornera siguiente %s y se paso a su '
                      'mismo numero. %s' % (p['cables'][0], '/'.join(otros), c, p['cables'][0], sig, como))


# ============================================================================================ mapeo
def mapear(plano, base, usos, lista=None, solo=None):
    modelos = base['modelos']
    comps = usos['componentes']
    region = usos.get('region_bandeja') or plano.region
    inst = instancias(plano, base, region)
    zonas = zonas_de(plano, comps)
    puntos, sin_punto, elegidos = [], [], {}

    def piezas_de(z, tipos):
        cand = sorted([i for i in inst if i['tipo'] in tipos and en_zona(i['caja'], z)], key=lambda i: i['cx'])
        out = []
        for i in cand:
            if out and i['caja'][0] - out[-1]['caja'][2] > GAP_MAX:
                break
            if not out and i['caja'][0] - z['caja'][2] > GAP_MAX + 8:
                break
            out.append(i)
        return out

    def aparato_de(z, mid):
        cand = [i for i in inst if i['modelo'] == mid and en_zona(i['caja'], z)]
        if not cand:
            return None
        dentro = [i for i in cand if contiene(i['caja'], z['tx'], z['ty'])]
        if dentro:
            return max(dentro, key=lambda i: (i['directo'] + i['inverso']))
        return min(cand, key=lambda i: i['caja'][0])

    def presentes(z):
        """Modelos con instancias en la zona (aparato: la que contiene la etiqueta o la primera a la derecha)."""
        out = {}
        for i in inst:
            if not en_zona(i['caja'], z):
                continue
            if i['tipo'] == 'aparato' and aparato_de(z, i['modelo']) is not i:
                continue
            out.setdefault(i['modelo'], []).append(i)
        return out

    def n_interpretables(mid, c):
        return sum(1 for u in comps[c]['usos'] if H.interpretar(modelos[mid], u, c))

    # ---------------------------------------------------------------- 1. modelo de cada componente
    for c in comps:
        z = zonas.get(c)
        if not z:
            continue
        pres = presentes(z)
        texto_lista = (lista or {}).get(c)
        de_lista = H.modelos_de_lista(texto_lista, modelos) if lista is not None else []
        aprend = lambda mid: bool(modelos[mid].get('huella') and modelos[mid].get('bornes'))
        ok_lista = [mid for mid in de_lista if mid in pres]
        nota = ''
        if ok_lista:
            mid = max(ok_lista, key=lambda mid: (n_interpretables(mid, c), max(i['directo'] + i['inverso'] for i in pres[mid])))
            conf = 'alta'
            nota = 'modelo de la lista de materiales, bloque hallado en la zona'
        elif de_lista and not any(aprend(mid) for mid in de_lista):
            sim = sorted(pres, key=lambda mid: -max(i['directo'] + i['inverso'] for i in pres[mid]))
            elegidos[c] = dict(modelo=None, lista=de_lista, nota='la lista de materiales dice %s, que no tiene huella aprendida en la base%s' % (
                '/'.join(de_lista), ('; en la zona hay un bloque parecido: %s' % sim[0]) if sim else ''))
            continue
        else:
            cands = [mid for mid in pres if n_interpretables(mid, c) > 0]
            if not cands:
                elegidos[c] = dict(modelo=None, lista=de_lista, nota='ningun bloque de la base en la zona de la etiqueta' +
                                   (' (la lista dice %s)' % '/'.join(de_lista) if de_lista else ''))
                continue
            mid = max(cands, key=lambda mid: (n_interpretables(mid, c), max(i['directo'] + i['inverso'] for i in pres[mid])))
            conf = 'media'
            nota = ('bloque reconocido en la zona (la lista de materiales dice %s)' % '/'.join(de_lista)) if de_lista else \
                   ('bloque reconocido en la zona (%s)' % ('sin renglon en la lista de materiales' if lista is not None and not texto_lista else
                                                           'la lista no nombra un modelo de la base' if lista is not None else 'sin lista de materiales'))
        elegidos[c] = dict(modelo=mid, conf=conf, nota=nota, lista=de_lista)

    # ---------------------------------------------------------------- 2. bornes
    orden_riel = sorted([c for c in comps if c in zonas], key=lambda c: (zonas[c]['riel'] or 0, zonas[c]['tx']))

    def ubicar(c, u, mid, forzar_unidad=None):
        """(x, y, r, como, instancia) o (None, motivo)."""
        m = modelos[mid]
        z = zonas[c]
        it = H.interpretar(m, u, c)
        if not it:
            return None, 'el texto no encaja en el esquema %s del modelo %s' % (m['esquema'], mid)
        unidad, clave = it
        if forzar_unidad is not None:
            unidad = forzar_unidad
        if m['tipo'] == 'aparato':
            i = aparato_de(z, mid)
            if i is None:
                return None, 'no se encontro el bloque %s en la zona' % mid
        else:
            ps = piezas_de(z, ('modulo',) if m['tipo'] == 'modulo' else ('pieza',))
            if unidad is None:
                return None, 'el texto no dice el modulo'
            if unidad > len(ps) or unidad < 1:
                return None, 'desborde:%d:%d' % (unidad, len(ps))
            i = ps[unidad - 1]
        mi = modelos[i['modelo']]
        if isinstance(clave, list):
            return None, 'pines:' + ','.join(clave)
        loc = clave
        if mi['esquema'] in H.ESQUEMAS_FISICOS and H.arriba_invertido(i['t']):
            loc = H.invertir_clave(clave)
        b = mi['bornes'].get(loc)
        if not b:
            return None, 'el borne %s no esta en la base del modelo %s (no se aprendio)' % (loc, i['modelo'])
        q = H.transformar([(b['dx'], b['dy'])], i['t'])[0] + (i['cx'], i['cy'])
        como = 'bloque %s en (%.2f, %.2f) %s, puntaje %.3f/%.3f; %s%s = ancla + (%.2f, %.2f) [%s]' % (
            i['modelo'], i['cx'], i['cy'], H.nombre_transf(i['t']), i['directo'], i['inverso'],
            ('pieza %d, ' % unidad) if m['tipo'] != 'aparato' else '', loc, b['dx'], b['dy'], b.get('origen', ''))
        return (float(q[0]), float(q[1]), float(b['r']), como, i), None

    for c in comps:
        if solo and c not in solo:
            continue
        e = elegidos.get(c)
        usos_c = comps[c]['usos']
        if not e or not e.get('modelo'):
            for u in usos_c:
                sin_punto.append(dict(texto=u['texto'], cable=u['cable'], componente=c, motivo=(e or {}).get('nota', 'sin etiqueta')))
            continue
        mid, m = e['modelo'], modelos[e['modelo']]
        pend_pines = collections.defaultdict(list)
        pend_mod = []
        for u in usos_c:
            res, motivo = ubicar(c, u, mid)
            if res:
                x, y, r, como, i = res
                puntos.append(dict(texto=u['texto'], cables=[u['cable']], componente=c, modelo=i['modelo'], x=round(x, 2), y=round(y, 2),
                                   r=r, confianza=e['conf'], como=como, _i=i, _u=u, _dest=c))
                continue
            if motivo.startswith('pines:'):
                pend_pines[(u['texto'], motivo)].append(u); continue
            if motivo == 'el texto no dice el modulo':
                pend_mod.append(u); continue
            if motivo.startswith('desborde:'):
                # el numero no existe en esta bornera: el instructivo a veces pone el tag de la bornera vecina
                k = orden_riel.index(c)
                sig = orden_riel[k + 1] if k + 1 < len(orden_riel) else None
                e2 = elegidos.get(sig) if sig and zonas[sig]['riel'] == zonas[c]['riel'] else None
                if e2 and e2.get('modelo') and modelos[e2['modelo']]['tipo'] == 'pieza':
                    u2 = dict(u, tag=sig)
                    res2, mot2 = ubicar(sig, u2, e2['modelo'])
                    if res2:
                        x, y, r, como, i = res2
                        puntos.append(dict(texto=u['texto'], cables=[u['cable']], componente=c, modelo=i['modelo'], x=round(x, 2), y=round(y, 2),
                                           r=r, confianza='baja', _i=i, _u=u, _dest=sig,
                                           como='DESBORDE: %s tiene %s piezas; se uso el mismo numero en la bornera siguiente %s. %s' % (
                                               c, motivo.split(':')[2], sig, como)))
                        continue
                motivo = '%s solo tiene %s piezas y no hay bornera vecina que lo explique' % (c, motivo.split(':')[2])
            sin_punto.append(dict(texto=u['texto'], cable=u['cable'], componente=c, motivo=motivo))
        # pines con el mismo nombre (-Vo / -Vo): por numero de cable, de izquierda a derecha
        for (texto, motivo), lst in pend_pines.items():
            cands = motivo[6:].split(',')
            i = aparato_de(zonas[c], mid)
            mi = modelos[mid]
            pos = []
            for pin in cands:
                b = mi['bornes'].get(pin)
                if b and i:
                    q = H.transformar([(b['dx'], b['dy'])], i['t'])[0] + (i['cx'], i['cy'])
                    pos.append((float(q[0]), pin, b, q))
            pos.sort()
            if not pos:
                for u in lst:
                    sin_punto.append(dict(texto=u['texto'], cable=u['cable'], componente=c,
                                          motivo='los pines %s no estan aprendidos en la base' % '/'.join(cands)))
                continue
            lst = sorted(lst, key=lambda u: int(re.sub(r'\D', '', u['cable']) or 0))
            for j, u in enumerate(lst):
                x, pin, b, q = pos[min(j, len(pos) - 1)]
                conf = e['conf'] if len(pos) >= len(lst) and (len(cands) == 1 or len(lst) > 1) else 'media'
                if len(cands) > 1:
                    conf = 'media' if conf == 'alta' else conf
                puntos.append(dict(texto=u['texto'], cables=[u['cable']], componente=c, modelo=mid, x=round(float(q[0]), 2), y=round(float(q[1]), 2),
                                   r=float(b['r']), confianza=conf, _i=i,
                                   como='bloque %s en (%.2f, %.2f) %s; pin %s (el nombre %s corresponde a %s; con el mismo nombre se asignan de izquierda a derecha por numero de cable)' % (
                                       mid, i['cx'], i['cy'], H.nombre_transf(i['t']), pin, u['borne'], '/'.join(cands))))
        # reles sin numero de modulo: el modulo cuyos otros cables tienen numeracion mas cercana
        if pend_mod:
            ps = piezas_de(zonas[c], ('modulo',))
            cab_mod = collections.defaultdict(list)
            for p in puntos:
                if p['componente'] == c and p.get('_i') in ps:
                    cab_mod[ps.index(p['_i']) + 1].append(int(re.sub(r'\D', '', p['cables'][0]) or 0))
            ocupado = set()
            for u in sorted(pend_mod, key=lambda u: u['cable']):
                num = int(re.sub(r'\D', '', u['cable']) or 0)
                it = H.interpretar(m, u, c)
                opciones = []
                for k in range(1, len(ps) + 1):
                    if (k, it[1]) in ocupado:
                        continue
                    d = min([abs(num - v) for v in cab_mod.get(k, [])], default=10 ** 6)
                    opciones.append((d, k))
                if not opciones:
                    sin_punto.append(dict(texto=u['texto'], cable=u['cable'], componente=c, motivo='el texto no dice el modulo')); continue
                d, k = min(opciones)
                ocupado.add((k, it[1]))
                res, motivo = ubicar(c, u, mid, forzar_unidad=k)
                if res:
                    x, y, r, como, i = res
                    puntos.append(dict(texto=u['texto'], cables=[u['cable']], componente=c, modelo=i['modelo'], x=round(x, 2), y=round(y, 2),
                                       r=r, confianza='media', _i=i,
                                       como='el texto no dice el modulo: se eligio el %d, cuyos cables tienen la numeracion mas cercana (%s). %s' % (
                                           k, 'dif. %d' % d if d < 10 ** 6 else 'sin datos', como)))
                else:
                    sin_punto.append(dict(texto=u['texto'], cable=u['cable'], componente=c, motivo=motivo))
    # ---------------------------------------------------------------- 3. dos cables en una misma boca
    corregir_boca_doble(puntos, elegidos, zonas, orden_riel, modelos, ubicar)
    for p in puntos:
        for k in ('_i', '_u', '_dest'):
            p.pop(k, None)
    return dict(puntos=puntos, sin_punto=sin_punto,
                componentes={c: {k: v for k, v in e.items()} for c, e in elegidos.items()},
                instancias=[dict(modelo=i['modelo'], cx=round(i['cx'], 2), cy=round(i['cy'], 2), giro=H.nombre_transf(i['t']),
                                 directo=i['directo'], inverso=i['inverso'], caja=[round(v, 2) for v in i['caja']]) for i in inst])


# ============================================================================================ imagen de control
def imagen_control(pdf, pagina_idx, res, path, region=None, escala=6.0):
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw, ImageFont
    doc = pdfium.PdfDocument(pdf)
    pg = doc[pagina_idx]
    W, Hh = pg.get_size()
    pts = res['puntos']
    ins = res.get('instancias', [])
    if pts:
        xs = [p['x'] for p in pts] + [c for i in ins for c in (i['caja'][0], i['caja'][2])]
        ys = [p['y'] for p in pts] + [c for i in ins for c in (i['caja'][1], i['caja'][3])]
        x0, x1 = max(0, min(xs) - 12), min(W, max(xs) + 45)
        y0, y1 = max(0, min(ys) - 12), min(Hh, max(ys) + 12)
    else:
        x0, y0, x1, y1 = region or (0, 0, W, Hh)
    img = pg.render(scale=escala, crop=(x0, y0, W - x1, Hh - y1)).to_pil().convert('RGB')
    img = Image.blend(img, Image.new('RGB', img.size, (255, 255, 255)), 0.35)
    d = ImageDraw.Draw(img)
    f = lambda x, y: ((x - x0) * escala, (y1 - y) * escala)
    try:
        font = ImageFont.truetype('arial.ttf', int(2.1 * escala))
        font_m = ImageFont.truetype('arialbd.ttf', int(2.6 * escala))
    except Exception:
        font = font_m = ImageFont.load_default()
    paleta = {}
    colores = [(0, 110, 200), (200, 90, 0), (0, 150, 70), (150, 0, 160), (180, 150, 0), (0, 150, 160), (120, 70, 20)]
    for i in ins:
        c = paleta.setdefault(i['modelo'], colores[len(paleta) % len(colores)])
        a = f(i['caja'][0], i['caja'][3]); b = f(i['caja'][2], i['caja'][1])
        d.rectangle([a, b], outline=c, width=2)
    for mid, c in paleta.items():
        pass
    col_conf = {'alta': (0, 170, 0), 'media': (230, 140, 0), 'baja': (220, 0, 0)}
    usados = []
    for p in sorted(pts, key=lambda p: (-p['y'], p['x'])):
        cx, cy = f(p['x'], p['y'])
        rr = max(2.0, p.get('r', 1.5) * escala)
        c = col_conf.get(p.get('confianza'), (220, 0, 0))
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=c, width=3)
        d.line([cx - 3, cy, cx + 3, cy], fill=c, width=1); d.line([cx, cy - 3, cx, cy + 3], fill=c, width=1)
        txt = '%s #%s' % (p['texto'], ','.join(p['cables']))
        tx, ty = cx + rr + 2, cy - 1.1 * escala
        for _ in range(12):
            if not any(abs(ty - uy) < 2.3 * escala and abs(tx - ux) < 40 * escala for ux, uy in usados):
                break
            ty += 2.3 * escala
        usados.append((tx, ty))
        d.text((tx + 1, ty + 1), txt, fill=(255, 255, 255), font=font)
        d.text((tx, ty), txt, fill=(170, 0, 0) if p.get('confianza') == 'baja' else (20, 20, 20), font=font)
        if abs(ty - (cy - 1.1 * escala)) > 1:
            d.line([cx + rr, cy, tx, ty + 1.1 * escala], fill=(120, 120, 120), width=1)
    # leyenda: en una franja arriba de la imagen, sin tapar el dibujo
    fl = ImageFont.truetype('arial.ttf', 17) if font is not font_m else font
    fb = ImageFont.truetype('arialbd.ttf', 17) if font is not font_m else font_m
    ncol = 4
    filas_ley = (len(paleta) + ncol - 1) // ncol
    alto = 16 + 26 * (2 + filas_ley)
    lienzo = Image.new('RGB', (img.width, img.height + alto), (255, 255, 255))
    lienzo.paste(img, (0, alto))
    d = ImageDraw.Draw(lienzo)
    n_b = sum(1 for p in pts if p.get('confianza') == 'baja')
    d.text((10, 8), 'P2 huellas de bloques: %d puntos. Circulo = borne (radio r). Verde = confianza alta, naranja = media, '
                    'rojo = baja (%d: desbordes / boca doble, revisar).' % (len(pts), n_b), fill=(0, 0, 0), font=fb)
    d.text((10, 8 + 26), 'Rectangulos = instancias de bloques halladas por su huella vectorial (color = modelo):', fill=(0, 0, 0), font=fl)
    colw = (img.width - 20) // ncol
    for k, (mid, c) in enumerate(paleta.items()):
        x = 12 + (k % ncol) * colw; y = 8 + 26 * (2 + k // ncol)
        d.rectangle([x, y + 3, x + 22, y + 19], outline=c, width=3)
        d.text((x + 30, y), mid, fill=c, font=fb)
    d.line([0, alto - 2, img.width, alto - 2], fill=(0, 0, 0), width=2)
    img = lienzo
    img.save(path)
    return path


# ============================================================================================ main
def main():
    t0 = time.time()
    args = sys.argv[1:]
    opts = {}
    for k in ('--base', '--materiales', '--control'):
        if k in args:
            j = args.index(k); opts[k] = args[j + 1]; del args[j:j + 2]
    if len(args) < 3:
        print(__doc__); sys.exit(1)
    pdf, usos_p, out_p = args[:3]
    base = H.cargar_json(opts.get('--base', os.path.join(AQUI, 'base_bornes.json')))
    usos = H.cargar_json(usos_p)
    lista_p = opts.get('--materiales', os.path.join(os.path.dirname(os.path.abspath(usos_p)), 'lista_materiales.txt'))
    lista = H.leer_lista_materiales(lista_p) if os.path.exists(lista_p) else None
    pag = int(usos.get('pagina_pdf', 1)) - 1
    plano = H.Plano(pdf, pag, region=usos.get('region_bandeja'))
    res = mapear(plano, base, usos, lista)
    res['segundos'] = round(time.time() - t0, 1)
    res['topografico'] = pdf
    res['base'] = opts.get('--base', 'base_bornes.json')
    res['lista_materiales'] = lista_p if lista is not None else None
    os.makedirs(os.path.dirname(os.path.abspath(out_p)), exist_ok=True)
    ctrl = opts.get('--control', os.path.join(os.path.dirname(os.path.abspath(out_p)), 'control.png'))
    imagen_control(pdf, pag, res, ctrl, region=usos.get('region_bandeja'))
    res['segundos'] = round(time.time() - t0, 1)
    H.guardar_json(out_p, dict(segundos=res['segundos'], **{k: v for k, v in res.items() if k != 'segundos'}))
    n_u = sum(len(v['usos']) for v in usos['componentes'].values())
    print('%d usos: %d con punto, %d sin punto. %d instancias de bloques. %.1f s -> %s' % (
        n_u, len(res['puntos']), len(res['sin_punto']), len(res['instancias']), res['segundos'], out_p))
    for s in res['sin_punto']:
        print('  sin punto: %-20s #%s  %s' % (s['texto'], s['cable'], s['motivo']))


if __name__ == '__main__':
    main()
