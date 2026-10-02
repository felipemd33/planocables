"""Estructuras de aparatos: como se agrupan las bocas encontradas por imagen y como se nombran.

Cada modelo de la base tiene una 'estructura':
  bornera    piezas angostas en fila a la derecha de la etiqueta; cada pieza es una columna de bocas,
             la mitad arriba del riel y la mitad abajo (PT QUATTRO, PTT, PT DIO, PTTB HESI...)
  rele       modulos de rele de interfaz en fila (RIF-0): 3 celdas del lado contactos y 2 del lado bobina
  modular    aparatos de 17.5 mm por polo (termomagneticas, diferenciales, DF101): un tornillo arriba y
             uno abajo por polo, polos de izquierda a derecha
  fuente     fuentes de riel (MEAN WELL): una fila de tornillos arriba (TB2) y otra abajo (TB1)
  barrera    barreras angostas con enchufes escalonados: se ve el enchufe exterior de cada lado; las otras
             filas se corren hacia adentro lo que dice la hoja de datos
  aparato    aparato sin tornillos dibujados: se busca el aparato entero y los bornes son anclas fijas
  esparragos portafusible de esparragos (MEGA): esparrago izquierdo y derecho

detectar(...) devuelve un objeto Deteccion con .calidad (0..1, para reconocer el modelo) y
.ubicar(direccion) -> (x, y, confianza, como). parsear(modelo, uso, tag) pasa el texto del instructivo a una
direccion propia de la estructura (o None si el texto no corresponde a ese modelo).
"""
import math
import re

import numpy as np

import vision


# ----------------------------------------------------------------------------------------------
# Lectura de los textos del instructivo
# ----------------------------------------------------------------------------------------------
def lado_texto(uso):
    """ARRIBA/ABAJO: el que dice el texto; si no dice, el campo 'parte' (el 'lado' de usos a veces sale invertido)."""
    t = uso['texto'].upper().split()
    for w in reversed(t):
        if w in ('ARRIBA', 'ABAJO'):
            return w
    p = (uso.get('parte') or '').upper()
    return p if p in ('ARRIBA', 'ABAJO') else None


def _borne_limpio(uso):
    b = (uso.get('borne') or '').strip()
    return re.sub(r'\s+(ARRIBA|ABAJO)$', '', b, flags=re.I).strip()


def _pin_fuente(b):
    """'1 (-)' -> (1, '-');  'L-3' -> (3, 'L');  '+Vin' -> (None, '+Vin')"""
    m = re.match(r'^\s*(\d+)\s*\(\s*([+-])\s*\)\s*$', b)
    if m:
        return int(m.group(1)), m.group(2)
    m = re.match(r'^\s*([A-Za-z]+)\s*-\s*(\d+)\s*$', b)
    if m:
        return int(m.group(2)), m.group(1)
    m = re.match(r'^\s*([+-]?[A-Za-z]+)\s*$', b)
    if m:
        return None, m.group(1)
    return None, None


def _nombre_pin_ok(pin, nombre):
    return pin.upper() == nombre.upper() or (nombre in '+-' and pin.startswith(nombre))


def parsear(modelo, uso, tag):
    """Texto del instructivo -> direccion (tupla) en la estructura del modelo, o None."""
    est = modelo['estructura']
    nom = modelo['nombres']
    b = _borne_limpio(uso)
    lado = lado_texto(uso)
    if est == 'bornera':
        f = nom['formato']
        if f == 'N.p':
            if uso.get('punto') is None or not b.isdigit():
                return None
            pl = nom['puntos'].get(str(uso['punto']))
            return None if pl is None else ('boca', int(b), pl[0], pl[1])
        if f == 'N LADO':
            if not b.isdigit() or lado is None:
                return None
            n = int(b)
            if 'lado_por_puente' in nom:
                return ('boca_puente', n, nom['lado_por_puente'][lado], 0)
            if nom.get('pieza') == 'mitad':
                return ('boca', (n + 1) // 2, lado.lower(), nom['orden_impar'] if n % 2 else nom['orden_par'])
            return ('boca', n, lado.lower(), 0)
        if f == 'nombre LADO':
            m = re.match(r'^([A-Za-z]*)(\d+)$', b)
            if not m or lado is None or m.group(1).upper() not in nom['prefijos']:
                return None
            return ('boca', int(m.group(2)), lado.lower(), nom['prefijos'][m.group(1).upper()])
        return None
    if est == 'rele':
        m = re.match(r'^' + re.escape(tag) + r'(\d*)\s+(\S+)', uso['texto'].strip())
        if not m:
            return None
        borne = m.group(2)
        celdas = modelo['celdas']
        for lado_c, lista in celdas.items():
            if borne in lista:
                return ('celda', int(m.group(1)) if m.group(1) else None, lado_c, lista.index(borne))
        return None
    if est == 'modular':
        polos = modelo['polos']
        if lado is None:
            return None
        if len(polos) == 1:
            return ('polo', 0, lado.lower()) if b == '' else None
        return ('polo', polos.index(b), lado.lower()) if b in polos else None
    if est == 'fuente':
        n, nombre = _pin_fuente(b)
        if nombre is None:
            return None
        cand = []
        for fi, fila in enumerate(modelo['filas']):
            for pi, pin in enumerate(fila['pines']):
                if _nombre_pin_ok(pin, nombre):
                    cand.append((fi, pi))
        if n is not None:
            cand = [c for c in cand if c[1] == n - 1]
        return ('pin', tuple(cand)) if cand else None
    if est == 'barrera':
        if not b.isdigit():
            return None
        n = int(b)
        for ei, e in enumerate(modelo['enchufes']):
            if n in e['bornes']:
                return ('enchufe', ei, e['bornes'].index(n))
        return None
    if est == 'aparato':
        return ('ancla', b) if b in modelo.get('_anclas', {}) else None
    if est == 'esparragos':
        if b != '' or lado is None:
            return None
        return ('esparrago', modelo['lados'][lado])
    return None


# ----------------------------------------------------------------------------------------------
# Utilidades de agrupamiento
# ----------------------------------------------------------------------------------------------
def agrupar_1d(vals, tol):
    """Agrupa valores ordenados: devuelve lista de listas de indices."""
    orden = sorted(range(len(vals)), key=lambda i: vals[i])
    grupos = []
    for i in orden:
        if grupos and vals[i] - vals[grupos[-1][-1]] <= tol:
            grupos[-1].append(i)
        else:
            grupos.append([i])
    return grupos


class Deteccion:
    def __init__(self, modelo, calidad, bocas, info, ubicador):
        self.modelo, self.calidad, self.bocas, self.info = modelo, calidad, bocas, info
        self._ub = ubicador

    def ubicar(self, dire):
        return self._ub(dire)


def _cadena(columnas, et, paso, x_max, min_bocas=1):
    """Columnas contiguas a la derecha de la etiqueta (regla del tag): la primera a menos de ~2.6 pasos del
    borde de la etiqueta (puede haber una pieza PE en el medio), las siguientes sin saltos de mas de 1.6 pasos.
    Una columna con menos de min_bocas bocas no es una pieza (es algo suelto que se parecio a una boca)."""
    cad = []
    for c in sorted(columnas, key=lambda c: c['x']):
        if c['x'] < et['x0'] - 1.0 or c['x'] > x_max or len(c['dets']) < min_bocas:
            continue
        if not cad:
            if c['x'] - et['x1'] > 2.6 * paso + 2.0:
                break
            cad.append(c)
        else:
            if c['x'] - cad[-1]['x'] > 1.6 * paso:
                break
            cad.append(c)
    return cad


def _columnas(dets, tol):
    g = agrupar_1d([d['x'] for d in dets], tol)
    cols = []
    for idx in g:
        ds = [dets[i] for i in idx]
        cols.append(dict(x=float(np.median([d['x'] for d in ds])), dets=ds))
    return cols


def _y_riel(cad, et):
    """Altura del riel: mediana de los centros del hueco mas grande de cada columna."""
    ys = []
    for c in cad:
        y = sorted(d['y'] for d in c['dets'])
        if len(y) >= 2:
            gaps = [(y[i + 1] - y[i], (y[i + 1] + y[i]) / 2) for i in range(len(y) - 1)]
            ys.append(max(gaps)[1])
    return float(np.median(ys)) if ys else et['yc']


def _niveles(distancias, tol=1.2):
    """Niveles de distancia al riel (de afuera hacia adentro)."""
    if not distancias:
        return []
    g = agrupar_1d(distancias, tol)
    lv = [(float(np.median([distancias[i] for i in idx])), len(idx)) for idx in g]
    return sorted(lv, key=lambda t: -t[0])


# ----------------------------------------------------------------------------------------------
# Estructuras
# ----------------------------------------------------------------------------------------------
def det_bornera(ctx, m, dets, et, zona):
    paso = m['paso_mm'] / ctx.esc
    if m.get('descartar_color'):
        dets = [d for d in dets if vision.fraccion_color(ctx.zona_color, d['x'] - 1.2, d['y'] - 1.2, d['x'] + 1.2, d['y'] + 1.2,
                                                         m['descartar_color']) < 0.4]
    cols = _columnas(dets, 0.3 * paso)
    k = m.get('bocas_por_lado', 2)
    cad = _cadena(cols, et, paso, zona[2], min_bocas=k)
    if not cad:
        return None
    yr = _y_riel(cad, et)
    niveles = {}
    for lado in ('arriba', 'abajo'):
        dist = [abs(d['y'] - yr) for c in cad for d in c['dets'] if (d['y'] > yr) == (lado == 'arriba')]
        lv = _niveles(dist)
        lv = sorted(sorted(lv, key=lambda t: -t[1])[:k], key=lambda t: -t[0])  # los k niveles con mas bocas
        niveles[lado] = [t[0] for t in lv]
    buenas = 0
    for c in cad:
        ok = True
        for lado in ('arriba', 'abajo'):
            n = sum(1 for d in c['dets'] if (d['y'] > yr) == (lado == 'arriba'))
            ok &= (n == k)
        buenas += ok
    consist = buenas / len(cad)
    if any(len(niveles[l]) != k for l in niveles):
        consist *= 0.5
    sc = float(np.mean([d['score'] for c in cad for d in c['dets']]))

    # lado del puente dibujado (para el borne con diodo): relleno rojo/azul dentro de la cadena
    lado_puente = None
    if 'lado_por_puente' in m.get('nombres', {}):
        x0, x1 = cad[0]['x'] - paso / 2, cad[-1]['x'] + paso / 2
        rel = vision.rellenos_color(ctx.zona_color, x0, zona[1], x1, zona[3], 'rojo_azul', 1.0)
        if rel:
            yb = max(rel, key=lambda t: t[2])[1]
            lado_puente = 'arriba' if yb > yr else 'abajo'

    def ubicar(dire):
        tipo = dire[0]
        pieza, lado, orden = dire[1], dire[2], dire[3]
        nota = ''
        if tipo == 'boca_puente':
            if lado_puente is None:
                return None
            lado = lado_puente if lado == 'lado_puente' else ('abajo' if lado_puente == 'arriba' else 'arriba')
            nota = f'puente dibujado del lado {lado_puente}; '
        if pieza < 1 or pieza > len(cad) or orden >= len(niveles[lado]):
            return None
        c = cad[pieza - 1]
        objetivo = niveles[lado][orden]
        mejor = None
        for d in c['dets']:
            if (d['y'] > yr) != (lado == 'arriba'):
                continue
            e = abs(abs(d['y'] - yr) - objetivo)
            if e < 1.2 and (mejor is None or e < mejor[0]):
                mejor = (e, d)
        como = f"{nota}pieza {pieza} de {len(cad)} a la derecha de la etiqueta, {lado}, boca {'extrema' if orden == 0 else 'interior' if orden == 1 else orden + 1}"
        if mejor:
            d = mejor[1]
            return d['x'], d['y'], 'alta' if d['score'] > 0.8 else 'media', como + f" (plantilla {d['plantilla']}, NCC {d['score']:.2f})"
        y = yr + objetivo if lado == 'arriba' else yr - objetivo
        return c['x'], y, 'media', como + ' (boca no encontrada: se toma la x de la pieza y la altura del nivel)'

    return Deteccion(m, sc * consist, [d for c in cad for d in c['dets']],
                     dict(piezas=len(cad), x_piezas=[round(c['x'], 2) for c in cad], y_riel=round(yr, 2), niveles=niveles,
                          consistencia=round(consist, 2), lado_puente=lado_puente), ubicar)


def det_rele(ctx, m, dets, et, zona):
    paso = m['paso_mm'] / ctx.esc
    cols = _columnas(dets, 0.3 * paso)
    cad = _cadena(cols, et, paso, zona[2], min_bocas=max(1, sum(len(v) for v in m['celdas'].values()) // 2))
    if not cad:
        return None
    yr = _y_riel(cad, et)
    n_arr = sum(1 for c in cad for d in c['dets'] if d['y'] > yr)
    n_aba = sum(1 for c in cad for d in c['dets'] if d['y'] <= yr)
    celdas = m['celdas']
    lados = sorted(celdas, key=lambda l: -len(celdas[l]))  # el lado con mas celdas (contactos) primero
    fis = {lados[0]: 'arriba' if n_arr >= n_aba else 'abajo'}
    fis[lados[1]] = 'abajo' if fis[lados[0]] == 'arriba' else 'arriba'
    niveles = {}
    for lc in lados:
        lado = fis[lc]
        dist = [abs(d['y'] - yr) for c in cad for d in c['dets'] if (d['y'] > yr) == (lado == 'arriba')]
        lv = _niveles(dist)
        lv = sorted(sorted(lv, key=lambda t: -t[1])[:len(celdas[lc])], key=lambda t: -t[0])
        niveles[lc] = [t[0] for t in lv]
    buenas = sum(1 for c in cad if all(sum(1 for d in c['dets'] if (d['y'] > yr) == (fis[lc] == 'arriba')) == len(celdas[lc]) for lc in lados))
    consist = buenas / len(cad)
    sc = float(np.mean([d['score'] for c in cad for d in c['dets']]))

    def ubicar(dire):
        _, mod, lc, orden = dire
        if mod is None or mod < 1 or mod > len(cad) or orden >= len(niveles[lc]):
            return None
        lado = fis[lc]
        c = cad[mod - 1]
        objetivo = niveles[lc][orden]
        mejor = None
        for d in c['dets']:
            if (d['y'] > yr) != (lado == 'arriba'):
                continue
            e = abs(abs(d['y'] - yr) - objetivo)
            if e < 1.2 and (mejor is None or e < mejor[0]):
                mejor = (e, d)
        nombre = celdas[lc][orden]
        como = f"modulo {mod} de {len(cad)}, lado {lc} ({lado}), celda {orden + 1} desde el extremo = {nombre}"
        if mejor:
            d = mejor[1]
            return d['x'], d['y'], 'alta' if d['score'] > 0.8 else 'media', como + f" (NCC {d['score']:.2f})"
        y = yr + objetivo if lado == 'arriba' else yr - objetivo
        return c['x'], y, 'media', como + ' (celda no encontrada: x del modulo, altura del nivel)'

    return Deteccion(m, sc * consist, [d for c in cad for d in c['dets']],
                     dict(modulos=len(cad), x_modulos=[round(c['x'], 2) for c in cad], y_riel=round(yr, 2),
                          lados=fis, consistencia=round(consist, 2)), ubicar)


def det_modular(ctx, m, dets, et, zona):
    cols = _columnas(dets, 1.5)
    polos = m['polos']
    cols = [c for c in cols if len(c['dets']) >= 2 and max(d['y'] for d in c['dets']) - min(d['y'] for d in c['dets']) > 15]
    if not cols:
        return None
    cols = sorted(sorted(cols, key=lambda c: abs(c['x'] - et['xc']))[:len(polos)], key=lambda c: c['x'])
    consist = len(cols) / len(polos)
    usados = []
    for c in cols:
        usados += [max(c['dets'], key=lambda d: d['y']), min(c['dets'], key=lambda d: d['y'])]
    sc = float(np.mean([d['score'] for d in usados]))

    def ubicar(dire):
        _, pi, lado = dire
        if len(cols) != len(polos):
            return None
        c = cols[pi]
        d = max(c['dets'], key=lambda d: d['y']) if lado == 'arriba' else min(c['dets'], key=lambda d: d['y'])
        return d['x'], d['y'], 'alta' if d['score'] > 0.8 else 'media', \
            f"polo {pi + 1} de {len(polos)} ('{polos[pi] or 'unico'}'), tornillo de {lado} (NCC {d['score']:.2f})"

    return Deteccion(m, sc * consist, usados, dict(x_polos=[round(c['x'], 2) for c in cols], consistencia=round(consist, 2)), ubicar)


def _fila_equiespaciada(ds, n):
    """De una fila de detecciones (misma y) elige n contiguas y parejas; devuelve la lista o None."""
    ds = sorted(ds, key=lambda d: d['x'])
    mejor = None
    for i in range(len(ds) - n + 1):
        sub = ds[i:i + n]
        if n > 1:
            pasos = np.diff([d['x'] for d in sub])
            if pasos.min() < 0.7 * np.median(pasos) or pasos.max() > 1.35 * np.median(pasos):
                continue
        s = float(np.mean([d['score'] for d in sub]))
        if mejor is None or s > mejor[0]:
            mejor = (s, sub)
    return None if mejor is None else mejor[1]


def det_fuente(ctx, m, dets, et, zona):
    filas_y = agrupar_1d([d['y'] for d in dets], 1.0)
    grupos = [[dets[i] for i in g] for g in filas_y]
    elegido = {}
    for fi, fila in enumerate(m['filas']):
        n = len(fila['pines'])
        cands = []
        for g in grupos:
            sub = _fila_equiespaciada(g, n)
            if sub and len(g) <= n + 1:
                cands.append(sub)
        if not cands:
            continue
        # la fila mas extrema (arriba o abajo) entre las que se parecen casi tanto como la mejor: una fila de
        # "tornillos" falsos (ruido de un escaneo, otro dibujo) encaja peor y no se toma aunque este mas afuera
        cands = [c for c in cands if (c[0]['y'] > et['yc']) == (fila['posicion'] == 'arriba')]  # de su lado de la etiqueta
        if not cands:
            continue
        media = [float(np.mean([d['score'] for d in c])) for c in cands]
        cands = [c for c, mm in zip(cands, media) if mm >= 0.9 * max(media)]
        if fila['posicion'] == 'arriba':
            elegido[fi] = max(cands, key=lambda s: s[0]['y'])
        else:
            elegido[fi] = min(cands, key=lambda s: s[0]['y'])
    if not elegido:
        return None
    consist = len(elegido) / len(m['filas'])
    usados = [d for s in elegido.values() for d in s]
    sc = float(np.mean([d['score'] for d in usados]))
    asignados = {}

    def ubicar(dire, cable=None, orden_cable=0):
        cands = [c for c in dire[1] if c[0] in elegido]
        if not cands:
            return None
        fi, pi = cands[min(orden_cable, len(cands) - 1)]
        d = elegido[fi][pi]
        fila = m['filas'][fi]
        return d['x'], d['y'], 'alta' if d['score'] > 0.7 else 'media', \
            f"{fila['nombre']} ({fila['posicion']}), pin {pi + 1} de {len(fila['pines'])} = {fila['pines'][pi]} " \
            f"(plantilla escala {d['escala']:.2f}, NCC {d['score']:.2f})"

    return Deteccion(m, sc * consist, usados, dict(filas={m['filas'][k]['nombre']: [round(d['x'], 2) for d in v] for k, v in elegido.items()},
                                                  y_filas={m['filas'][k]['nombre']: round(v[0]['y'], 2) for k, v in elegido.items()},
                                                  consistencia=round(consist, 2)), ubicar)


def det_barrera(ctx, m, dets, et, zona):
    filas = {}
    for lado, var in (('arriba', ('normal',)), ('abajo', ('giro180', 'espejo_v'))):
        ds = [d for d in dets if d['var'] in var and ((d['y'] > et['yc']) == (lado == 'arriba'))]
        if not ds:
            continue
        # la fila exterior: la de y extrema; dos tornillos, los mas cercanos a la etiqueta
        yext = max(d['y'] for d in ds) if lado == 'arriba' else min(d['y'] for d in ds)
        ds = [d for d in ds if abs(d['y'] - yext) < 1.0]
        ds = sorted(sorted(ds, key=lambda d: abs(d['x'] - et['xc']))[:2], key=lambda d: d['x'])
        if len(ds) == 2 and 1.5 < ds[1]['x'] - ds[0]['x'] < 8:
            filas[lado] = ds
    if not filas:
        return None
    consist = len(filas) / 2
    usados = [d for v in filas.values() for d in v]
    sc = float(np.mean([d['score'] for d in usados]))

    def ubicar(dire):
        _, ei, k = dire
        e = m['enchufes'][ei]
        lado = e['lado']
        if lado not in filas:
            return None
        izq, der = filas[lado]
        paso = der['x'] - izq['x']
        n = len(e['bornes'])
        if n == 2:
            x = (izq, der)[k]['x']
        else:
            xc = (izq['x'] + der['x']) / 2
            x = xc + (k - (n - 1) / 2) * paso
        dy = e.get('dy_mm', 0.0) / ctx.esc
        y0 = (izq['y'] + der['y']) / 2
        y = y0 - dy if lado == 'arriba' else y0 + dy
        dibujado = (n == 2 and dy == 0 and ei == min(i for i, q in enumerate(m['enchufes']) if q['lado'] == lado))
        conf = 'alta' if dibujado else 'media'
        como = f"enchufe {e['bornes']} ({lado}), tornillo {k + 1}: " + \
            ('tornillo dibujado' if dibujado else f"fila no dibujada: x de la columna, y corrida {e.get('dy_mm', 0)} mm hacia adentro (hoja de datos)")
        return x, y, conf, como

    return Deteccion(m, sc * consist, usados, dict(filas={k: [(round(d['x'], 2), round(d['y'], 2)) for d in v] for k, v in filas.items()},
                                                  consistencia=round(consist, 2)), ubicar)


def det_aparato(ctx, m, dets, et, zona):
    if not dets:
        return None
    d = max(dets, key=lambda d: d['score'])
    pl = ctx.plantillas[d['plantilla']]
    anclas = pl.info.get('anclas_px', {})
    ax, ay = pl.ancla

    def ubicar(dire):
        _, nombre = dire
        if nombre not in anclas:
            return None
        jx, iy = anclas[nombre]
        x = d['x'] + (jx - ax) / pl.s * d['escala']
        y = d['y'] - (iy - ay) / pl.s * d['escala']
        return x, y, 'media', f"aparato entero encontrado con la plantilla {d['plantilla']} (NCC {d['score']:.2f}); borne {nombre} = ancla fija de la plantilla"

    return Deteccion(m, d['score'], [d], dict(centro=(round(d['x'], 2), round(d['y'], 2))), ubicar)


def det_esparragos(ctx, m, dets, et, zona):
    if len(dets) < 2:
        return None
    ds = sorted(sorted(dets, key=lambda d: -d['score'])[:2], key=lambda d: d['x'])
    sc = float(np.mean([d['score'] for d in ds]))

    def ubicar(dire):
        d = ds[dire[1]]
        return d['x'], d['y'], 'media', f"esparrago {'izquierdo' if dire[1] == 0 else 'derecho'} (NCC {d['score']:.2f})"

    return Deteccion(m, sc, ds, dict(x=[round(d['x'], 2) for d in ds]), ubicar)


DETECTORES = dict(bornera=det_bornera, rele=det_rele, modular=det_modular, fuente=det_fuente, barrera=det_barrera,
                  aparato=det_aparato, esparragos=det_esparragos)
