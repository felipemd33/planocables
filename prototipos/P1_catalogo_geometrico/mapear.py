# -*- coding: utf-8 -*-
"""Mapeo de bornes del topografico con un CATALOGO DE MODELOS + un DETECTOR GEOMETRICO GENERICO.

uso:
    python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json>
                     [--materiales lista_materiales.txt] [--catalogo catalogo.json] [--control control.png]

Idea (ver LEEME.md):
  1. Se leen los trazos vectoriales de la pagina (programa/pdfvec.py), las etiquetas amarillas (render de la
     pagina) y los rieles DIN (capa 'RIEL DIN').
  2. Cada componente de usos_por_componente.json se asocia a su etiqueta amarilla y a su riel. Su ZONA es lo que
     esta a la DERECHA de su etiqueta hasta la etiqueta siguiente del mismo riel (regla 1 del taller), con la
     altura del modelo.
  3. El modelo sale de la lista de materiales (alias del catalogo). Si no figura o su firma no aparece en la
     zona, se prueban todos los modelos del catalogo y se queda el que mejor explica los usos.
  4. En la zona se buscan las bocas con la FIRMA del modelo (circulo de tal radio, contorno de tal tamano,
     tornillo cortado, caja), se agrupan en piezas/columnas o filas y se nombran con las reglas del catalogo.
  5. Controles de coherencia que el catalogo activa por modelo: 'desborde' (borne que no existe -> bloque
     siguiente de la misma hoja), 'conductores_por_boca' (dos cables en una boca de 1 conductor -> uno va al bloque
     siguiente) y 'comunes' (borne puenteado entre modulos -> el cable entra por el primer modulo).

Nada de este archivo conoce este tablero: todas las medidas y nombres estan en catalogo.json.
"""
import sys
import os
import re
import json
import math
import time
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
PROGRAMA = os.path.join(os.path.dirname(os.path.dirname(AQUI)), 'programa')
for p in (AQUI, PROGRAMA, r'C:/Buscar Termos en plano/programa'):
    if p not in sys.path:
        sys.path.insert(0, p)

import primitivas as P  # noqa: E402

LADOS = ('ARRIBA', 'ABAJO')


# ============================================================================================ lectura
def leer_trazos(pdf, pagina):
    import pypdf
    from pdfvec import page_strokes, layer_names
    r = pypdf.PdfReader(pdf)
    return page_strokes(r, pagina, layer_names(r), with_color=True)


def detectar_etiquetas(pdf, pagina, region, escala=4.0):
    """Etiquetas amarillas: se renderiza la pagina y se buscan las manchas amarillas rectangulares.
    Devuelve [dict(x0, y0, x1, y1, cx, cy)] en puntos PDF (origen abajo a la izquierda)."""
    import numpy as np
    import cv2
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    pg = doc[pagina]
    W, H = pg.get_size()
    img = np.asarray(pg.render(scale=escala).to_pil().convert('RGB'))
    r, g, b = [img[:, :, i].astype(np.int16) for i in range(3)]
    m = ((r > 200) & (g > 200) & (b < 120)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, connectivity=8)
    out = []
    x0r, y0r, x1r, y1r = region
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        ex0, ex1 = x / escala, (x + w) / escala
        ey1, ey0 = H - y / escala, H - (y + h) / escala
        if min(ex1 - ex0, ey1 - ey0) < 3.0 or max(ex1 - ex0, ey1 - ey0) < 8.0:
            continue
        if a < 0.5 * w * h:
            continue
        cx, cy = (ex0 + ex1) / 2, (ey0 + ey1) / 2
        if not (x0r <= cx <= x1r and y0r <= cy <= y1r):
            continue
        out.append(dict(x0=ex0, y0=ey0, x1=ex1, y1=ey1, cx=cx, cy=cy))
    doc.close()
    return out


def detectar_rieles(trazos, capa, region):
    """Tramos de riel DIN: grupos de lineas horizontales largas de la capa del riel con la misma extension en x.
    Devuelve [dict(x0, x1, y0, y1, yc)]."""
    x0r, y0r, x1r, y1r = region
    hs = []
    for t in trazos:
        if t[0] != capa or not t[2] or len(t[2]) < 2:
            continue
        xs = [q[0] for q in t[2]]
        ys = [q[1] for q in t[2]]
        if max(xs) - min(xs) > 30 and max(ys) - min(ys) < 0.5:
            if x0r - 5 <= min(xs) and max(xs) <= x1r + 5 and y0r <= ys[0] <= y1r:
                hs.append((min(xs), max(xs), sum(ys) / len(ys)))
    grupos = []
    for a, b, y in sorted(hs, key=lambda h: (round(h[0]), round(h[1]), h[2])):
        for g in grupos:
            if abs(g['x0'] - a) < 2 and abs(g['x1'] - b) < 2 and g['y0'] - 20 <= y <= g['y1'] + 20:
                g['y0'] = min(g['y0'], y)
                g['y1'] = max(g['y1'], y)
                break
        else:
            grupos.append(dict(x0=a, x1=b, y0=y, y1=y))
    out = [g for g in grupos if g['y1'] - g['y0'] > 10]
    for g in out:
        g['yc'] = (g['y0'] + g['y1']) / 2
    return out


def norm(s):
    return re.sub(r'\s+', '', str(s).upper()).replace(',', '.')


PAT_TAG = re.compile(r'^\d{2}[A-Z]+\d*$')


def leer_materiales(path):
    """lista_materiales.txt: una linea por componente, campos separados por '|'. Devuelve {tag: texto}."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    for linea in open(path, encoding='utf-8', errors='replace'):
        campos = [c.strip() for c in linea.split('|')]
        tag = next((c for c in campos if PAT_TAG.match(c.replace(' ', ''))), None)
        if not tag:
            continue
        resto = ' | '.join(c for c in campos if c != tag)
        out[tag] = (out.get(tag, '') + ' | ' + resto).strip(' |')
    return out


def modelo_por_materiales(texto, modelos):
    """El modelo del catalogo cuyo alias mas largo aparece en el texto de la lista de materiales."""
    t = norm(texto)
    mejor, largo = None, 0
    for m in modelos:
        for a in m.get('alias', []):
            na = norm(a)
            if na and na in t and len(na) > largo:
                mejor, largo = m, len(na)
    return mejor


def raiz(tag):
    return re.sub(r'\d+$', '', tag)


# ============================================================================================ utilidades
def color_ok(c, general, color_modelo=None):
    tol = general.get('tolerancia_color', 0.12)
    if c is None:
        return color_modelo is None
    for ex in general.get('colores_excluidos', []):
        if P.color_parecido(c, ex, tol):
            return False
    if color_modelo is not None:
        return P.color_parecido(c, color_modelo, tol)
    return True


def dedup(bocas, d):
    out = []
    for b in sorted(bocas, key=lambda b: -b.get('peso', 0)):
        if not any(math.hypot(b['x'] - o['x'], b['y'] - o['y']) < d for o in out):
            out.append(b)
    return out


def num_cable(c):
    m = re.search(r'\d+', str(c))
    return int(m.group()) if m else 0


def lado_de_uso(u):
    """ARRIBA/ABAJO del uso: la palabra del texto si la tiene; si no, 'parte' (el lado del borne en el aparato),
    y si no, 'lado'."""
    t = (u.get('texto') or '').upper()
    for w in LADOS:
        if re.search(r'\b' + w + r'\b', t):
            return w
    for k in ('parte', 'lado'):
        v = (u.get(k) or '').upper()
        if v in LADOS:
            return v
    return None


# ============================================================================================ motor
class Motor:
    def __init__(self, pdf, usos, catalogo, materiales):
        self.t0 = time.time()
        self.usos = usos
        self.cat = catalogo
        self.g = catalogo['general']
        self.modelos = catalogo['modelos']
        self.esc = float(usos.get('escala_mm_por_pt') or 1.4086)
        self.pagina = int(usos.get('pagina_pdf') or 1) - 1
        trazos = leer_trazos(pdf, self.pagina)
        if usos.get('region_bandeja'):
            self.region = tuple(usos['region_bandeja'])
        else:
            xs = [q[0] for t in trazos for q in t[2]]
            ys = [q[1] for t in trazos for q in t[2]]
            self.region = (min(xs), min(ys), max(xs), max(ys))
        self.esc_ = P.Escena(trazos, self.region, self.g)
        self.arcos = self.esc_.arcos()
        self.curvas = self.esc_.curvas()
        self.rects = self.esc_.rectangulos()
        self.puentes = self._puentes(trazos)
        self.rieles = detectar_rieles(trazos, self.g.get('capa_riel', 'RIEL DIN'), self.region)
        self.etiquetas = detectar_etiquetas(pdf, self.pagina, self.region)
        self.materiales = materiales
        self.avisos = []
        self._asociar()

    def mm(self, v):
        return float(v) / self.esc

    # ------------------------------------------------------------------ puentes FBS (rellenos de color)
    def _puentes(self, trazos):
        out = []
        x0, y0, x1, y1 = self.region
        for t in trazos:
            if t[1] not in ('f', 'F', 'b', 'B') or not t[3] or not t[2]:
                continue
            c = t[3]
            if max(c[:3]) - min(c[:3]) < 0.5:
                continue
            b = P.bbox(t[2])
            if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
                continue
            out.append(dict(x0=b[0], y0=b[1], x1=b[2], y1=b[3], yc=(b[1] + b[3]) / 2))
        return out

    # ------------------------------------------------------------------ etiquetas y rieles
    def _asociar(self):
        dmax = self.mm(self.g.get('distancia_max_etiqueta_mm', 20))
        pares = []
        comps = self.usos['componentes']
        for k, c in comps.items():
            e = c.get('etiqueta_topografico') or {}
            if 'x' not in e:
                continue
            for i, t in enumerate(self.etiquetas):
                d = math.hypot(t['cx'] - e['x'], t['cy'] - e['y'])
                if d <= dmax:
                    pares.append((d, k, i))
        usados_k, usados_i = set(), set()
        self.tag = {}
        for d, k, i in sorted(pares):
            if k in usados_k or i in usados_i:
                continue
            usados_k.add(k)
            usados_i.add(i)
            self.tag[k] = dict(self.etiquetas[i], leida=True)
        for k, c in comps.items():
            if k not in self.tag:
                e = c.get('etiqueta_topografico') or {'x': self.region[0], 'y': self.region[1]}
                h, w = 2.4, 8.5
                self.tag[k] = dict(x0=e['x'] - w, x1=e['x'] + w, y0=e['y'] - h, y1=e['y'] + h, cx=e['x'], cy=e['y'], leida=False)
                self.avisos.append(f'{k}: no encontre su etiqueta amarilla, uso la posicion de usos_por_componente.json')
        # riel de cada componente: el tramo de riel que contiene la etiqueta (con margen vertical)
        self.riel = {}
        for k, t in self.tag.items():
            mv = self.mm(self.g.get('margen_etiqueta_riel_mm', 21))
            cand = [r for r in self.rieles if r['x0'] - 5 <= t['cx'] <= r['x1'] + 5 and r['y0'] - mv <= t['cy'] <= r['y1'] + mv]
            self.riel[k] = min(cand, key=lambda r: abs(r['yc'] - t['cy'])) if cand else None
        # delimitadores por riel: etiquetas de componentes + etiquetas ajenas que pisan la banda del riel
        self.delims = defaultdict(list)
        for k, t in self.tag.items():
            if self.riel[k] is not None:
                self.delims[id(self.riel[k])].append(dict(t, comp=k))
        propias = {(round(t['x0'], 1), round(t['y0'], 1)) for t in self.tag.values()}
        for t in self.etiquetas:
            if (round(t['x0'], 1), round(t['y0'], 1)) in propias:
                continue
            for r in self.rieles:
                if r['x0'] - 5 <= t['cx'] <= r['x1'] + 5 and t['y0'] <= r['y1'] and t['y1'] >= r['y0']:
                    self.delims[id(r)].append(dict(t, comp=None))
        for v in self.delims.values():
            v.sort(key=lambda t: t['x0'])

    def siguiente(self, k):
        r = self.riel[k]
        if r is None:
            return None
        t = self.tag[k]
        for d in self.delims[id(r)]:
            if d['x0'] > t['x0'] + 0.5:
                return d
        return None

    def zona(self, k, m):
        t = self.tag[k]
        r = self.riel[k]
        alto = self.mm(m.get('alto_mm', 90) / 2 + self.g.get('margen_alto_mm', 5))
        if m.get('anclaje') == 'libre' or r is None:
            ancho = self.mm(m.get('ancho_mm', 80) / 2 + self.g.get('margen_alto_mm', 5))
            if m.get('anclaje') == 'izquierda':
                return (t['x0'] - self.mm(m.get('margen_izq_mm', 1)), t['cy'] - alto, t['x0'] + 2 * ancho, t['cy'] + alto), t['cy']
            return (t['cx'] - ancho, t['cy'] - alto, t['cx'] + ancho, t['cy'] + alto), t['cy']
        x0 = t['x0'] - self.mm(m.get('margen_izq_mm', 1))
        s = self.siguiente(k)
        x1 = (s['x0'] - self.mm(self.g.get('margen_der_mm', 1))) if s else r['x1']
        x1 = min(x1, r['x1'] + 2)
        return (x0, r['yc'] - alto, x1, r['yc'] + alto), r['yc']

    # ------------------------------------------------------------------ deteccion de bocas (firma)
    def bocas(self, m, caja):
        f = m['boca']
        x0, y0, x1, y1 = caja
        prim = f['primitiva']
        out = []
        if prim == 'circulo':
            rmin, rmax = self.mm(f['r_mm'][0]), self.mm(f['r_mm'][1])
            arcs = [a for a in self.arcos if x0 - 3 <= a[0] <= x1 + 3 and y0 - 3 <= a[1] <= y1 + 3]
            for c in P.circulos(arcs, rmin, rmax, cob_min=f.get('cob_min', 250)):
                if not (x0 <= c['x'] <= x1 and y0 <= c['y'] <= y1):
                    continue
                if not color_ok(c['color'], self.g, f.get('color')):
                    continue
                if f.get('sin_x', True) and self.esc_.tiene_x(c['x'], c['y'], c['r']):
                    continue
                out.append(dict(x=c['x'], y=c['y'], r=c['r'], peso=c['cob']))
            out = dedup(out, 0.6 * self.mm(f['r_mm'][0]))
        elif prim == 'contorno':
            wmin, wmax = [self.mm(v) for v in f['w_mm']]
            hmin, hmax = [self.mm(v) for v in f['h_mm']]
            for c in self.esc_.contornos(caja):
                if not (wmin <= c['w'] <= wmax and hmin <= c['h'] <= hmax):
                    continue
                if c['curvos'] < f.get('curvos_min', 0):
                    continue
                if not color_ok(c['color'], self.g, f.get('color')):
                    continue
                r = (c['w'] + c['h']) / 4
                if f.get('sin_x', True) and self.esc_.tiene_x(c['x'], c['y'], r):
                    continue
                out.append(dict(x=c['x'], y=c['y'], r=r, peso=c['n']))
            out = dedup(out, 0.5 * wmin)
        elif prim == 'tornillo_cortado':
            wmin, wmax = [self.mm(v) for v in f['w_mm']]
            cur = [c for c in self.curvas if x0 <= c[1][0] and c[1][2] <= x1 and y0 <= c[1][1] and c[1][3] <= y1
                   and color_ok(c[2], self.g)]
            for c in P.tornillos_cortados(cur, ancho=(wmin, wmax), alto_max=self.mm(f.get('h_max_mm', 4.8))):
                out.append(dict(x=c['x'], y=c['y'], r=c['r'], peso=1))
        elif prim == 'caja':
            pass
        return out

    # ------------------------------------------------------------------ estructura segun la disposicion
    def estructura(self, k, m):
        caja, yc = self.zona(k, m)
        t = self.tag[k]
        disp = m['disposicion']
        est = dict(modelo=m, caja=caja, yc=yc, tipo=disp['tipo'], piezas=[], grupos={}, cuerpo=None, validas=0, total=0)
        if disp['tipo'] == 'caja':
            f = m['boca']
            wmin, wmax = [self.mm(v) for v in f['w_mm']]
            hmin, hmax = [self.mm(v) for v in f['h_mm']]
            cand = [b for b in self.rects if b[0] - 0.5 <= t['cx'] <= b[2] + 0.5 and b[1] - 0.5 <= t['cy'] <= b[3] + 0.5
                    and wmin <= b[2] - b[0] <= wmax and hmin <= b[3] - b[1] <= hmax]
            if cand:
                est['cuerpo'] = min(cand, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
                est['validas'] = est['total'] = 1
            return est
        bocas = self.bocas(m, caja)
        est['bocas'] = bocas
        if disp['tipo'] == 'piezas':
            paso = self.mm(m.get('paso_mm', 6))
            tolx = max(0.9, 0.35 * paso)
            cols = []
            for b in sorted(bocas, key=lambda b: b['x']):
                if cols and abs(b['x'] - cols[-1]['x']) <= tolx:
                    cols[-1]['b'].append(b)
                    cols[-1]['x'] = sum(q['x'] for q in cols[-1]['b']) / len(cols[-1]['b'])
                else:
                    cols.append(dict(x=b['x'], b=[b]))
            esperado = disp['bocas']
            lxc = disp.get('lados_por_cantidad')
            piezas = []
            for c in cols:
                ys = sorted(c['b'], key=lambda b: b['y'])
                if len(ys) >= 2:
                    gap, i = max((ys[j + 1]['y'] - ys[j]['y'], j) for j in range(len(ys) - 1))
                    if self.riel[k] is not None and not (ys[i]['y'] <= yc <= ys[i + 1]['y']):
                        i = max([j for j in range(len(ys)) if ys[j]['y'] < yc], default=-1)
                    abajo, arriba = ys[:i + 1], ys[i + 1:]
                else:
                    abajo, arriba = ([], ys) if ys and ys[0]['y'] > yc else (ys, [])
                pz = dict(x=c['x'], arriba=sorted(arriba, key=lambda b: -b['y']), abajo=sorted(abajo, key=lambda b: b['y']))
                if lxc:
                    na, nb = len(pz['arriba']), len(pz['abajo'])
                    la, lb = lxc.get(str(na)), lxc.get(str(nb))
                    ok = la is not None and lb is not None and la != lb
                    if ok:
                        pz[la] = pz['arriba']
                        pz[lb] = pz['abajo']
                else:
                    ok = len(pz['arriba']) == esperado.get('arriba', 0) and len(pz['abajo']) == esperado.get('abajo', 0)
                pz['ok'] = ok
                piezas.append(pz)
            est['total'] = len(piezas)
            buenas = [p for p in piezas if p['ok']]
            if m.get('anclaje') == 'sobre' and m.get('polos'):
                buenas = sorted(buenas, key=lambda p: abs(p['x'] - t['cx']))[:int(m['polos'])]
                buenas.sort(key=lambda p: p['x'])
            est['piezas'] = buenas
            est['validas'] = len(buenas)
            est['descartadas'] = [p for p in piezas if not p['ok']]
        elif disp['tipo'] == 'filas':
            filas = []
            for b in sorted(bocas, key=lambda b: b['y']):
                for f in filas:
                    if abs(f['y'] - b['y']) <= max(0.6, 0.4 * b['r']):
                        f['b'].append(b)
                        f['y'] = sum(q['y'] for q in f['b']) / len(f['b'])
                        break
                else:
                    filas.append(dict(y=b['y'], b=[b]))
            for f in filas:
                f['b'].sort(key=lambda b: b['x'])
            for gspec in disp['grupos']:
                n = int(gspec['n'])
                lado = gspec.get('lado', 'centro')
                cand = [f for f in filas if len(f['b']) >= n and (lado == 'centro' or (lado == 'arriba') == (f['y'] > yc))]
                if not cand:
                    continue
                f = min(cand, key=lambda f: (len(f['b']) != n, abs(sum(b['x'] for b in f['b']) / len(f['b']) - t['cx'])))
                bs = f['b']
                if len(bs) > n:
                    i0 = min(range(len(bs) - n + 1), key=lambda i: abs(sum(b['x'] for b in bs[i:i + n]) / n - t['cx']))
                    bs = bs[i0:i0 + n]
                est['grupos'][gspec['nombre']] = dict(spec=gspec, b=bs, y=sum(b['y'] for b in bs) / n)
            est['total'] = len(disp['grupos'])
            est['validas'] = len(est['grupos'])
        return est

    # ------------------------------------------------------------------ lado fisico del diodo
    def lado_puente(self, est, defecto):
        pz = est['piezas']
        if not pz:
            return defecto
        xa = min(p['x'] for p in pz) - 1
        xb = max(p['x'] for p in pz) + 1
        ya = [p['arriba'][0]['y'] for p in pz if p['arriba']]
        yb = [p['abajo'][0]['y'] for p in pz if p['abajo']]
        if not ya or not yb:
            return defecto
        ymid = (sum(ya) / len(ya) + sum(yb) / len(yb)) / 2
        cand = [b for b in self.puentes if b['x1'] >= xa and b['x0'] <= xb and min(yb) <= b['yc'] <= max(ya)]
        if not cand:
            return defecto
        b = max(cand, key=lambda b: min(b['x1'], xb) - max(b['x0'], xa))
        if abs(b['yc'] - ymid) < 0.2:
            return defecto
        return 'arriba' if b['yc'] > ymid else 'abajo'

    # ------------------------------------------------------------------ nombres -> punto
    def resolver(self, k, est, usos_k):
        """Devuelve {indice_uso: dict(x, y, r, confianza, como)} y la lista de usos que desbordan."""
        m = est['modelo']
        nom = m.get('nombres', {})
        res, desborde = {}, []
        if est['tipo'] == 'piezas':
            pz = est['piezas']
            comunes = self.comunes_puenteados(k, usos_k, nom)
            for i, u in usos_k:
                clave = str(u.get('borne') or '').strip()
                if u.get('punto') not in (None, ''):
                    clave = f"{clave}.{u['punto']}"
                regla, mo = None, None
                for rg in nom.get('reglas', []):
                    mo = re.match(rg['patron'], clave, re.I)
                    if mo:
                        regla = rg
                        break
                if not regla:
                    continue
                g1 = mo.group(1) if mo.groups() else None
                # pieza
                pv = regla.get('pieza', 1)
                nota_comun = ''
                if pv == 'modulo':
                    suf = str(u.get('tag') or '')[len(k):]
                    borne_u = str(u.get('borne') or '').strip().upper()
                    if borne_u in comunes:
                        npz, conf = 1, 'media'
                        nota_comun = (f" | {borne_u} es un comun puenteado (cableado en {comunes[borne_u][0]} modulo(s) y "
                                      f"{comunes[borne_u][1]} en {comunes[borne_u][2]}): el cable entra por el primer modulo"
                                      + (f" (el texto dice modulo {suf})" if suf.isdigit() and int(suf) != 1 else ''))
                    elif suf.isdigit():
                        npz = int(suf)
                        conf = 'alta'
                    else:
                        npz = self.modulo_por_pareja(k, u, usos_k, nom)
                        conf = 'media'
                elif isinstance(pv, int):
                    npz, conf = pv, 'alta'
                elif pv == '$1':
                    npz, conf = int(g1), 'alta'
                elif pv.startswith('ceil($1/'):
                    d = int(re.search(r'/(\d+)', pv).group(1))
                    npz, conf = -(-int(g1) // d), 'alta'
                else:
                    npz, conf = int(pv), 'alta'
                # lado y boca
                if 'punto' in regla:
                    lado, boca = nom['puntos'][mo.group(2)]
                else:
                    lado = regla.get('lado', 'texto')
                    bv = regla.get('boca', 0)
                    if isinstance(bv, str) and bv.startswith('paridad'):
                        boca = 0 if int(g1) % 2 == 1 else 1
                    else:
                        boca = int(bv)
                if lado == 'texto':
                    lt = lado_de_uso(u)
                    if lt is None:
                        continue
                    lado = lt.lower()
                elif lado == 'diodo':
                    dd = nom.get('diodo', {})
                    lt = lado_de_uso(u)
                    if lt is None:
                        continue
                    lp = self.lado_puente(est, dd.get('puente_por_defecto', 'abajo'))
                    rel = dd.get(lt, 'puente')
                    lado = lp if rel == 'puente' else ('arriba' if lp == 'abajo' else 'abajo')
                if npz < 1 or npz > len(pz):
                    if nom.get('desborde'):
                        desborde.append((i, u))
                    continue
                lista = pz[npz - 1].get(lado, [])
                if boca >= len(lista):
                    continue
                b = lista[boca]
                res[i] = dict(x=b['x'], y=b['y'], r=b['r'], confianza=conf, bloque=k,
                              como=f"{m['id']}: pieza {npz} de {len(pz)}, lado {lado}, boca {boca} ({'extremo' if boca == 0 else 'interior'})" + nota_comun)
        elif est['tipo'] == 'filas':
            pines = nom.get('pines', {})
            alias = {norm(a): v for a, v in nom.get('alias', {}).items()}
            porname = defaultdict(list)
            for i, u in usos_k:
                borne = str(u.get('borne') or '').strip()
                spec, num, nombre = None, None, None
                if borne in pines:
                    spec, nombre = pines[borne], borne
                else:
                    mnum = re.search(r'\d+', borne)
                    num = int(mnum.group()) if mnum else None
                    nm = norm(re.sub(r'[\d()]', '', borne))
                    if len(nm) > 1 and nm.endswith('-'):
                        nm = nm[:-1]
                    if len(nm) > 1 and nm.startswith('-') and norm(nm[1:]) in {norm(p) for p in pines}:
                        pass
                    nm = alias.get(nm, nm)
                    for pn, ps in pines.items():
                        if norm(pn) == nm:
                            spec, nombre = ps, pn
                            break
                if spec is None:
                    continue
                porname[nombre].append((i, u, spec, num))
            for nombre, lst in porname.items():
                lst.sort(key=lambda q: num_cable(q[1].get('cable')))
                for j, (i, u, spec, num) in enumerate(lst):
                    gr = est['grupos'].get(spec.get('grupo'))
                    if gr is None:
                        continue
                    conf = nom.get('confianza', 'alta')
                    if 'por_lado' in spec:
                        lt = lado_de_uso(u)
                        if lt is None or lt not in spec['por_lado']:
                            continue
                        pin = int(spec['por_lado'][lt])
                    elif 'pin' in spec:
                        pin = int(spec['pin'])
                    else:
                        lp = spec.get('pines', [1])
                        if num is not None and num in lp:
                            pin = num
                        else:
                            pin = lp[j % len(lp)]
                    fila = int(spec.get('fila', 0))
                    bs = gr['b']
                    gspec = gr['spec']
                    if fila == 0 and len(bs) >= pin and gspec.get('tornillos_por_fila', [len(bs)])[0] == len(bs):
                        b = bs[pin - 1]
                        x, y, r = b['x'], b['y'], b['r']
                    else:
                        nfila = gspec.get('tornillos_por_fila', [len(bs)] * (fila + 1))[fila]
                        cx = sum(b['x'] for b in bs) / len(bs)
                        pitch = (bs[-1]['x'] - bs[0]['x']) / (len(bs) - 1) if len(bs) > 1 else 0
                        x = cx + (pin - (nfila + 1) / 2) * pitch
                        off = self.mm(gspec.get('filas_mm', [0] * (fila + 1))[fila])
                        y = gr['y'] - off if gspec.get('lado') == 'arriba' else gr['y'] + off
                        r = sum(b['r'] for b in bs) / len(bs)
                        conf = 'media'
                    res[i] = dict(x=x, y=y, r=r, confianza=conf,
                                  como=f"{m['id']}: grupo {spec.get('grupo')} pin {pin}" + (f" fila {fila} (no dibujada, corrida {gspec.get('filas_mm')[fila]} mm)" if fila else ''))
        elif est['tipo'] == 'caja' and est['cuerpo']:
            bx0, by0, bx1, by1 = est['cuerpo']
            pines = nom.get('pines', {})
            for i, u in usos_k:
                borne = norm(u.get('borne') or '')
                spec = next((v for pn, v in pines.items() if norm(pn) == borne), None)
                if spec is None:
                    continue
                x = bx0 + spec['fx'] * (bx1 - bx0)
                y = by0 + self.mm(spec['dy_mm']) if spec.get('desde', 'abajo') == 'abajo' else by1 - self.mm(spec['dy_mm'])
                res[i] = dict(x=x, y=y, r=self.mm(m.get('r_borne_mm', 2.5)), confianza=nom.get('confianza', 'media'),
                              como=f"{m['id']}: {borne} a {spec['fx']:.3f} del ancho del cuerpo, {spec.get('desde', 'abajo')}")
        return res, desborde

    def comunes_puenteados(self, k, usos_k, nom):
        """Bornes comunes unidos con un puente FBS entre modulos (ej. los A2 de un grupo de reles).
        Se deducen de los usos: si un borne esta cableado en MENOS modulos que su pareja (A2 en 1 modulo y A1 en
        4), los demas modulos lo reciben por el puente. Devuelve {borne: (n_modulos, pareja, n_modulos_pareja)}."""
        out = {}
        for c in nom.get('comunes', []):
            b, pj = str(c['borne']).upper(), str(c['pareja']).upper()

            def modulos(nombre):
                ms, sueltos = set(), 0
                for _, u in usos_k:
                    if str(u.get('borne') or '').strip().upper() != nombre:
                        continue
                    suf = str(u.get('tag') or '')[len(k):]
                    if suf.isdigit():
                        ms.add(int(suf))
                    else:
                        sueltos += 1
                return len(ms) + sueltos
            nb, npj = modulos(b), modulos(pj)
            if 0 < nb < npj and npj >= int(c.get('min_modulos', 2)):
                out[b] = (nb, pj, npj)
        return out

    def resolver_compartidas(self):
        """Una boca push-in lleva UN conductor. Si en un bloque con 'desborde' dos cables distintos caen en la misma
        boca, uno de los dos tiene mal la etiqueta (el instructivo puso la del bloque vecino). Se pasa al bloque
        siguiente el cable que deja todo coherente: sin bocas compartidas y sin cables con dos puntas en el mismo
        bloque (dos bornes de un mismo bloque se unen con puente, no con cable). Si no hay una opcion claramente
        mejor, no se mueve nada y queda el aviso."""
        comps = self.usos['componentes']

        def puntas(cable, excluir=None):
            out = []
            for k2, r2 in self.resultado.items():
                for i2, p2 in r2.items():
                    u2 = comps[k2]['usos'][i2]
                    if str(u2.get('cable')) == cable and (k2, i2) != excluir:
                        out.append((p2.get('bloque', k2), p2))
            return out

        for k, c in comps.items():
            nom = self.elegido[k].get('nombres', {})
            if int(nom.get('conductores_por_boca', 0)) != 1 or not nom.get('desborde'):
                continue
            sig = self.vecino_desborde(k)
            if sig is None:
                continue
            por_boca = defaultdict(list)
            for i, p in self.resultado[k].items():
                if p.get('bloque', k) == k:
                    por_boca[(round(p['x'], 1), round(p['y'], 1))].append(i)
            for boca, idx in por_boca.items():
                cables = {str(c['usos'][i].get('cable')) for i in idx}
                if len(idx) < 2 or len(cables) < 2:
                    continue
                opciones = []
                for i in idx:
                    u = c['usos'][i]
                    cab = str(u.get('cable'))
                    res, _ = self.resolver(sig, self.estructuras[sig], [(i, dict(u))])
                    if i not in res:
                        continue
                    p2 = res[i]
                    costo = 0
                    # la boca de destino tiene que estar libre
                    for k3, r3 in self.resultado.items():
                        for i3, p3 in r3.items():
                            if (k3, i3) != (k, i) and math.hypot(p3['x'] - p2['x'], p3['y'] - p2['y']) < 0.3 \
                                    and str(comps[k3]['usos'][i3].get('cable')) != cab:
                                costo += 1
                    # el cable movido no puede quedar con dos puntas en el bloque de destino
                    costo += sum(1 for b2, _ in puntas(cab, (k, i)) if b2 == sig)
                    # los que se quedan no pueden tener otra punta en este bloque
                    for j in idx:
                        if j == i:
                            continue
                        cj = str(c['usos'][j].get('cable'))
                        costo += sum(1 for b2, q in puntas(cj, (k, j)) if b2 == k and
                                     (round(q['x'], 1), round(q['y'], 1)) != boca)
                    if len(idx) > 2:
                        costo += 1      # con 3 o mas cables en la boca no alcanza con mover uno
                    opciones.append((costo, i, p2))
                opciones.sort(key=lambda q: q[0])
                if not opciones or opciones[0][0] > 0 or (len(opciones) > 1 and opciones[1][0] == 0):
                    continue
                _, i, p2 = opciones[0]
                u = c['usos'][i]
                p2 = dict(p2, confianza='media', bloque=sig)
                p2['como'] = (f"{k} {u.get('borne')} ya tiene otro cable en esa boca (una boca = un conductor) y este cable "
                              f"no puede ir en {k}: se ubica en {sig}, bloque siguiente de la hoja {k[:2]}. " + p2['como'])
                self.resultado[k][i] = p2
                self.avisos.append(f"{k}: '{u.get('texto')}' #{u.get('cable')} comparte boca con otro cable; "
                                   f"se paso a {sig} {u.get('borne')} (revisar la etiqueta en el instructivo)")

    def modulo_por_pareja(self, k, u, usos_k, nom):
        """Modulo de un uso sin numero de modulo ('46KR A2'): el del otro borne de bobina con cable vecino."""
        c = num_cable(u.get('cable'))
        for _, v in usos_k:
            suf = str(v.get('tag') or '')[len(k):]
            if suf.isdigit() and str(v.get('borne')).upper() in ('A1', 'A2') and abs(num_cable(v.get('cable')) - c) == 1:
                return int(suf)
        return 1

    # ------------------------------------------------------------------ eleccion del modelo
    def candidatos(self, k):
        mats = self.materiales
        listado = None
        if k in mats:
            listado = modelo_por_materiales(mats[k], self.modelos)
        if listado is None:
            for tg, tx in mats.items():
                if raiz(tg) == raiz(k) and tg != k:
                    listado = modelo_por_materiales(tx, self.modelos)
                    if listado:
                        break
        return listado

    def mapear(self):
        comps = self.usos['componentes']
        self.resultado = {}
        self.elegido = {}
        self.estructuras = {}
        pendientes_desborde = []
        for k, c in comps.items():
            usos_k = list(enumerate(c.get('usos', [])))
            listado = self.candidatos(k)
            pruebas = []
            modelos = self.modelos
            if 'es_bornera' in c:
                modelos = [m for m in self.modelos if bool(m.get('es_bornera', False)) == bool(c['es_bornera'])] or self.modelos
            if listado is not None and listado not in modelos:
                modelos = modelos + [listado]
            for m in modelos:
                est = self.estructura(k, m)
                res, desb = self.resolver(k, est, usos_k)
                n = max(1, len(usos_k))
                col = 0
                if m.get('color_dibujo') is not None and est.get('bocas'):
                    col = 1 if sum(1 for _ in est['bocas']) else 0
                score = (len(res) + 0.5 * len(desb)) / n + (0.05 if m is listado else 0) + 0.01 * (est['validas'] > 0)
                pruebas.append((score, m, est, res, desb))
            # 1) el modelo de la lista de materiales se respeta si su firma aparece en la zona y explica al menos
            #    la mitad de los usos; 2) si no, gana el modelo del catalogo que mejor explica los usos
            #    (desempate por el color del dibujo: borne gris / azul)
            pruebas.sort(key=lambda q: -q[0])
            mejor = pruebas[0]
            for q in pruebas:
                if q[1] is listado and q[2]['validas'] > 0 and q[0] - 0.06 >= 0.5:
                    mejor = q
            empatados = [q for q in pruebas if abs(q[0] - mejor[0]) < 1e-6]
            if len(empatados) > 1 and mejor[1] is not listado:
                mejor = max(empatados, key=lambda q: self.afinidad_color(q[2]))
            score, m, est, res, desb = mejor
            if listado is not None and m is not listado:
                self.avisos.append(f"{k}: la lista de materiales dice {listado['id']} pero el dibujo coincide mejor con {m['id']}")
            elif listado is None:
                self.avisos.append(f"{k}: no figura en la lista de materiales; por la geometria es {m['id']}")
            self.elegido[k] = m
            self.estructuras[k] = est
            self.resultado[k] = res
            for i, u in desb:
                pendientes_desborde.append((k, i, u))
        # desborde: borne que no existe en el bloque -> bloque siguiente del mismo riel y de la misma hoja
        for k, i, u in pendientes_desborde:
            sig = self.vecino_desborde(k)
            if sig is None:
                continue
            est = self.estructuras[sig]
            u2 = dict(u)
            res, _ = self.resolver(sig, est, [(i, u2)])
            if i in res:
                p = res[i]
                p['confianza'] = 'media'
                p['como'] = f"{k} no tiene borne {u.get('borne')}: se ubica en {sig} (bloque siguiente de la hoja {k[:2]}). " + p['como']
                self.resultado[k][i] = p
        self.resolver_compartidas()
        return self.salida()

    def afinidad_color(self, est):
        m = est['modelo']
        cm = m.get('color_dibujo')
        if cm is None or not est.get('bocas'):
            return 0
        caja = est['caja']
        cc = defaultdict(int)
        for t in self.esc_.comp:
            b = t[4]
            if caja[0] <= b[0] and b[2] <= caja[2] and caja[1] <= b[1] and b[3] <= caja[3] and t[3] is not None:
                cc[tuple(round(v, 2) for v in t[3][:3])] += 1
        tot = sum(cc.values()) or 1
        return sum(v for c, v in cc.items() if P.color_parecido(c, cm, 0.12)) / tot

    def vecino_desborde(self, k):
        r = self.riel[k]
        if r is None:
            return None
        t = self.tag[k]
        for d in self.delims[id(r)]:
            if d['x0'] > t['x0'] + 0.5 and d['comp']:
                if d['comp'][:2] == k[:2]:
                    return d['comp']
                return None
        return None

    def salida(self):
        puntos = []
        for k, c in self.usos['componentes'].items():
            m = self.elegido[k]
            t = self.tag[k]
            for i, u in enumerate(c.get('usos', [])):
                p = self.resultado[k].get(i)
                base = dict(texto=u.get('texto'), cables=[str(u.get('cable'))] if u.get('cable') else [], componente=k, modelo=m['id'])
                if p is None:
                    base.update(x=round(t['cx'], 2), y=round(t['cy'], 2), r=2.0, confianza='baja',
                                como=f"{m['id']}: no pude resolver '{u.get('borne')}' {lado_de_uso(u) or ''}; queda en la etiqueta")
                else:
                    base.update(x=round(p['x'], 2), y=round(p['y'], 2), r=round(p['r'], 2), confianza=p['confianza'], como=p['como'])
                    if p.get('bloque') and p['bloque'] != k:
                        base['ubicado_en'] = p['bloque']
                puntos.append(base)
        # dos cables distintos en la misma boca: puede ser un puente o una derivacion a proposito, pero tambien
        # un error del instructivo (etiqueta del bloque vecino, extremo repetido). Se avisa y se baja a 'media'.
        vistos = defaultdict(list)
        for p in puntos:
            if p['confianza'] != 'baja' and p['cables']:
                vistos[(p['componente'], round(p['x'], 1), round(p['y'], 1))].append(p)
        for (k, x, y), lst in vistos.items():
            cables = sorted({c for p in lst for c in p['cables']})
            if len(cables) > 1:
                self.avisos.append(f"{k}: dos o mas cables en la misma boca ({', '.join(q['texto'] + ' #' + ','.join(q['cables']) for q in lst)}): "
                                   "revisar si es un puente/derivacion o un error del instructivo")
                for p in lst:
                    if p['confianza'] == 'alta':
                        p['confianza'] = 'media'
                    p['como'] += ' | AVISO: la boca la comparten los cables ' + ', '.join(cables)
        return dict(descripcion='Puntos de conexion de los bornes (prototipo P1: catalogo geometrico). Coordenadas en puntos PDF, origen abajo a la izquierda; r = radio de la boca en pt.',
                    pagina_pdf=self.pagina + 1, escala_mm_por_pt=self.esc,
                    modelos={k: m['id'] for k, m in self.elegido.items()},
                    avisos=self.avisos, puntos=puntos, segundos=round(time.time() - self.t0, 2))


# ============================================================================================ control
def control(pdf, motor, salida, png, ancho_px=2200, escala_max=12.0):
    """Imagen de control: un panel ampliado por riel (y uno por cada aparato fuera del riel), con cada punto
    marcado del tamano de la boca y rotulado 'borne cable'. Verde = alta, naranja = media, rojo = baja."""
    import numpy as np
    import cv2
    import pypdfium2 as pdfium
    col = {'alta': (0, 140, 0), 'media': (0, 120, 235), 'baja': (0, 0, 220)}      # BGR
    # grupos de componentes: por tramo de riel; los que no estan en un riel, cada uno aparte
    grupos = defaultdict(list)
    for k in motor.usos['componentes']:
        r = motor.riel.get(k)
        if r is not None and motor.elegido[k].get('anclaje') != 'libre':
            grupos[('riel', round(r['x0']), round(r['yc']))].append(k)
        else:
            grupos[('libre', k)].append(k)
    pts_por = defaultdict(list)
    for p in salida['puntos']:
        pts_por[p['componente']].append(p)
    orden = sorted(grupos.items(), key=lambda kv: (-max(motor.tag[k]['cy'] for k in kv[1]), min(motor.tag[k]['x0'] for k in kv[1])))
    # un riel muy largo se parte en tramos para que el panel se vea ampliado
    max_pt = ancho_px / 8.0
    partido = []
    for gk, ks in orden:
        ks = sorted(ks, key=lambda k: motor.tag[k]['x0'])
        tramo = []
        for k in ks:
            xs = [p['x'] for p in pts_por[k]] + [motor.tag[k]['x0'], motor.tag[k]['x1']]
            if tramo:
                x_ini = min(min(p['x'] for p in pts_por[q]) if pts_por[q] else motor.tag[q]['x0'] for q in tramo)
                if max(xs) - x_ini > max_pt:
                    partido.append((gk, tramo))
                    tramo = []
            tramo.append(k)
        if tramo:
            partido.append((gk, tramo))
    orden = partido
    doc = pdfium.PdfDocument(pdf)
    pg = doc[motor.pagina]
    W, H = pg.get_size()
    paneles = []
    for gk, ks in orden:
        ks = sorted(ks, key=lambda k: motor.tag[k]['x0'])
        xs, ys = [], []
        for k in ks:
            t = motor.tag[k]
            xs += [t['x0'], t['x1']]
            ys += [t['y0'], t['y1']]
            for p in pts_por[k]:
                xs += [p['x'] - p['r'], p['x'] + p['r']]
                ys += [p['y'] - p['r'], p['y'] + p['r']]
        x0, x1 = min(xs) - 10, max(xs) + 26
        y0, y1 = min(ys) - 10, max(ys) + 10
        esc = min(escala_max, ancho_px / (x1 - x0))
        img = pg.render(scale=esc, crop=(x0, y0, W - x1, H - y1)).to_pil().convert('RGB')
        a = np.asarray(img)[:, :, ::-1].copy()
        a = (255 - (255 - a.astype(np.int16)) * 0.5).astype(np.uint8)

        def X(x):
            return int(round((x - x0) * esc))

        def Y(y):
            return int(round((y1 - y) * esc))
        ocupado = []
        fs = 0.42
        for k in ks:
            est = motor.estructuras[k]
            cj = est['caja']
            cv2.rectangle(a, (X(cj[0]), Y(cj[3])), (X(cj[2]), Y(cj[1])), (255, 170, 120), 1)
            txt = f"{k}: {est['modelo']['id']}"
            (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            tx, ty = max(2, X(cj[0]) + 2), max(th + 3, Y(cj[3]) - 3)
            for o in list(ocupado):
                if tx < o[2] and tx + tw > o[0] and ty - th < o[3] and ty > o[1]:
                    ty = o[3] + th + 3
            cv2.putText(a, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 60, 20), 1, cv2.LINE_AA)
            ocupado.append((tx, ty - th, tx + tw, ty))
        pts = [p for k in ks for p in pts_por[k]]
        for p in pts:
            cx, cy, rr = X(p['x']), Y(p['y']), max(4, int(p['r'] * esc))
            ocupado.append((cx - rr, cy - rr, cx + rr, cy + rr))
        for p in sorted(pts, key=lambda p: (-p['y'], p['x'])):
            c = col.get(p['confianza'], (0, 0, 0))
            cx, cy, rr = X(p['x']), Y(p['y']), max(4, int(p['r'] * esc))
            cv2.circle(a, (cx, cy), rr, c, 2, cv2.LINE_AA)
            cv2.circle(a, (cx, cy), 2, c, -1)
            texto = p['texto'] or ''
            partes = texto.split(' ', 1)
            borne = partes[1] if len(partes) > 1 and partes[0] == p['componente'] else texto
            lab = f"{borne} {','.join(p['cables'])}".strip()
            if p.get('ubicado_en'):
                lab = f"{p['componente']} {lab} -> {p['ubicado_en']}"
            (tw, th), _ = cv2.getTextSize(lab, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)
            d = rr + 3
            cand = [(d, -th // 2), (-d - tw, -th // 2), (-tw // 2, -d - th), (-tw // 2, d), (d, -d - th), (-d - tw, -d - th),
                    (d, d), (-d - tw, d), (d + 14, -th // 2 - 16), (-d - tw - 14, -th // 2 + 16),
                    (-tw // 2, -d - th - 18), (-tw // 2, d + 18), (d + 20, -th // 2 + 22), (-d - tw - 20, -th // 2 - 22)]
            mejor = None
            for dx, dy in cand:
                bx = (cx + dx, cy + dy, cx + dx + tw, cy + dy + th)
                sol = sum(max(0, min(bx[2], o[2]) - max(bx[0], o[0])) * max(0, min(bx[3], o[3]) - max(bx[1], o[1])) for o in ocupado)
                fuera = bx[0] < 0 or bx[1] < 0 or bx[2] > a.shape[1] or bx[3] > a.shape[0]
                sc = sol + (10 ** 6 if fuera else 0)
                if mejor is None or sc < mejor[0]:
                    mejor = (sc, bx)
                if sc == 0:
                    break
            bx = mejor[1]
            ocupado.append(bx)
            mx, my = (bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2
            if math.hypot(mx - cx, my - cy) > rr + tw / 2 + 8:
                cv2.line(a, (cx, cy), (mx, my), c, 1, cv2.LINE_AA)
            cv2.rectangle(a, (bx[0] - 1, bx[1] - 1), (bx[2] + 1, bx[3] + 2), (255, 255, 255), -1)
            cv2.putText(a, lab, (bx[0], bx[3]), cv2.FONT_HERSHEY_SIMPLEX, fs, c, 1, cv2.LINE_AA)
        titulo = ('Riel: ' if gk[0] == 'riel' else 'Fuera del riel: ') + ', '.join(ks)
        barra = np.full((30, a.shape[1], 3), 255, np.uint8)
        cv2.putText(barra, titulo, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        paneles.append(np.vstack([barra, a]))
    doc.close()
    Wmax = max(p.shape[1] for p in paneles)
    ley = np.full((70, Wmax, 3), 255, np.uint8)
    n = {c: sum(1 for p in salida['puntos'] if p['confianza'] == c) for c in col}
    cv2.putText(ley, f"Control P1 catalogo geometrico - {len(salida['puntos'])} puntos (rotulo: borne cable; circulo = tamano de la boca)",
                (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 1, cv2.LINE_AA)
    x = 8
    for nom, c in (('alta: boca detectada', 'alta'), ('media: extrapolado, regla o a revisar', 'media'),
                   ('baja: sin resolver (queda en la etiqueta)', 'baja')):
        s = f"{nom} ({n[c]})"
        cv2.circle(ley, (x + 8, 50), 7, col[c], 2)
        cv2.putText(ley, s, (x + 20, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col[c], 1, cv2.LINE_AA)
        x += 30 + cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0][0]
    cv2.putText(ley, 'celeste: zona de cada etiqueta y modelo elegido', (x + 10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 60, 20), 1, cv2.LINE_AA)
    filas = [ley]
    for p in paneles:
        if p.shape[1] < Wmax:
            p = np.hstack([p, np.full((p.shape[0], Wmax - p.shape[1], 3), 255, np.uint8)])
        filas.append(p)
        filas.append(np.full((12, Wmax, 3), 200, np.uint8))
    cv2.imwrite(png, np.vstack(filas))


# ============================================================================================ main
def main(argv):
    args = [a for a in argv[1:]]
    opts = {}
    pos = []
    i = 0
    while i < len(args):
        if args[i].startswith('--') and i + 1 < len(args):
            opts[args[i][2:]] = args[i + 1]
            i += 2
        else:
            pos.append(args[i])
            i += 1
    if len(pos) < 3:
        print(__doc__)
        return 2
    pdf, usos_path, out = pos[:3]
    usos = json.load(open(usos_path, encoding='utf-8'))
    catalogo = json.load(open(opts.get('catalogo', os.path.join(AQUI, 'catalogo.json')), encoding='utf-8'))
    mat = opts.get('materiales') or os.path.join(os.path.dirname(os.path.abspath(usos_path)), 'lista_materiales.txt')
    motor = Motor(pdf, usos, catalogo, leer_materiales(mat))
    sal = motor.mapear()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(sal, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    png = opts.get('control', os.path.join(os.path.dirname(os.path.abspath(out)), 'control.png'))
    if png != 'no':
        control(pdf, motor, sal, png)
    n = len(sal['puntos'])
    nb = sum(1 for p in sal['puntos'] if p['confianza'] != 'baja')
    print(f"{n} puntos ({nb} ubicados, {n - nb} sin resolver) en {sal['segundos']} s -> {out}")
    for a in sal['avisos']:
        print('  aviso:', a)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
