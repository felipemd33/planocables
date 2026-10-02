"""Deteccion de bornes de reles Phoenix RIF-0-RPT-..../21 (1 inversor, push-in)
en el plano topografico vectorial (Batfer) y asignacion de los usos del
instructivo a su punto de conexion exacto.

Aparato real (fotos del tablero 75286-1: 1.2, 1.3, 1.6, 1.7; hoja de datos
Phoenix 2903370 RIF-0-RPT-24DC/21 y base RIF-0-BPT/21 2900958):
  * modulo de 6.2 mm de ancho x 93 mm de alto; en el dibujo: rectangulo de
    4.33 x 65.1 pt (1.41 mm/pt); los modulos se montan pegados (paso 4.33 pt).
  * lado de CONTACTOS (salida): 3 bornes push-in escalonados, numeros
    moldeados en la carcasa. Del mas externo (extremo del modulo) al mas
    interno (hacia el rele): 11 (comun C), 14 (NA), 12 (NC).  [foto 1.2]
  * lado de BOBINA (entrada): 2 bornes; el interno (junto al LED) A1+, el
    externo (extremo del modulo) A2-.                         [foto 1.6]
  * en el dibujo cada borne es una celda: ovalo chico (abertura de prueba) en
    el extremo, CIRCULO GRANDE (r 1.43-1.52 pt, 2-3 arcos con centro comun
    = entrada del conductor = PUNTO DE CONEXION) y rectangulo con semicirculo
    (pulsador naranja) hacia el cuerpo. El LED es un circulo r 0.98 (no se
    confunde por el radio).
  * numeracion de modulos: 1, 2, 3... de izquierda a derecha a partir del
    rotulo amarillo del grupo, que esta a la izquierda del primer modulo
    (fotos 1.2/1.3/1.7: 11 = 2118, 4318, 2122, 4358 en 43KR1..4).
  * puentes FBS: el topografico los anota sobre el grupo ("FBS.. AZUL (A2)",
    "FBS.. ROJO (C 11)"); por eso un rotulo del funcional puede nombrar el
    grupo sin modulo ("46KR A2") o un modulo equivocado.

La regla no depende de la orientacion: el lado con 3 circulos es el de
contactos y el orden se cuenta desde el extremo exterior hacia el cuerpo.

Uso:  python reles.py   -> reles_puntos.json + control_reles.png
"""
import os
import sys
import json
import pickle

import numpy as np

sys.path.insert(0, r'C:\Buscar Termos en plano\programa')

AQUI = os.path.dirname(os.path.abspath(__file__))
TOPO = os.path.normpath(os.path.join(AQUI, '..', 'topo.pdf'))
PAGINA = 7                      # indice 0 -> pagina PDF 8
CAPAS_COMP = ('COMPONENTES', '00_COMPONENTS')
R_MIN, R_MAX = 1.25, 1.70       # radio del circulo de entrada del conductor (pt)
PASO_MOD = 4.33                 # paso de modulo en el dibujo (pt) = 6.1 mm
GRUPOS = (('43KR', 4), ('46KR', 2), ('62KR', 3))
ORDEN_CONTACTOS = ('11', '14', '12')   # externo -> interno
ORDEN_BOBINA = ('A1', 'A2')            # interno -> externo


# --------------------------------------------------------------- geometria
def cargar_trazos(pdf=TOPO, pagina=PAGINA, cache=os.path.join(AQUI, 'strokes_p8.pkl')):
    if cache and os.path.exists(cache):
        return pickle.load(open(cache, 'rb'))
    import pypdf
    from pdfvec import page_strokes, layer_names
    r = pypdf.PdfReader(pdf)
    return page_strokes(r, pagina, layer_names(r), with_color=True)


def _fit_circle(pts):
    P = np.asarray(pts, float)
    x, y = P[:, 0], P[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x * x + y * y
    c = np.linalg.lstsq(A, b, rcond=None)[0]
    cx, cy = c[0], c[1]
    r = float(np.sqrt(c[2] + cx * cx + cy * cy))
    res = float(np.abs(np.hypot(x - cx, y - cy) - r).max())
    return float(cx), float(cy), r, res


def circulos_entrada(strokes, ventana):
    """Centros de los circulos grandes (entrada de cable) dentro de
    ventana=(x0, y0, x1, y1). Cada circulo viene partido en 2-3 arcos que
    comparten centro; se agrupan. Devuelve [(x, y, n_arcos)]."""
    x0, y0, x1, y1 = ventana
    cents = []
    for s in strokes:
        l, o, pts = s[0], s[1], s[2]
        if o != 'S' or l not in CAPAS_COMP or len(pts) < 7:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if min(xs) < x0 or max(xs) > x1 or min(ys) < y0 or max(ys) > y1:
            continue
        cx, cy, r, res = _fit_circle(pts)
        if R_MIN <= r <= R_MAX and res < 0.06:
            cents.append((cx, cy, r))
    grupos = []
    for cx, cy, r in cents:
        for g in grupos:
            if abs(g['x'] - cx) < 0.35 and abs(g['y'] - cy) < 0.35:
                g['pts'].append((cx, cy, r))
                n = len(g['pts'])
                g['x'] = sum(p[0] for p in g['pts']) / n
                g['y'] = sum(p[1] for p in g['pts']) / n
                break
        else:
            grupos.append({'x': cx, 'y': cy, 'pts': [(cx, cy, r)]})
    return [(g['x'], g['y'], len(g['pts'])) for g in grupos]


def _columnas(circ, tol=1.0):
    cols = []
    for c in sorted(circ, key=lambda c: c[0]):
        if cols and abs(cols[-1][-1][0] - c[0]) < tol:
            cols[-1].append(c)
        else:
            cols.append([c])
    return cols


def detectar_grupo_reles(strokes, etiqueta_xy, tag, n_esperado=None,
                         alto=48.0, ancho_max=60.0):
    """Devuelve {'modulos': [...], 'bornes': {'43KR1 11': (x, y), ...}}.

    etiqueta_xy: posicion de la etiqueta amarilla del grupo (a la izquierda
    del primer modulo). Se toman las columnas de 5 circulos (3 contactos +
    2 bobina) contiguas a paso ~4.33 pt que arrancan a la derecha de la
    etiqueta; se corta en el primer salto (siguiente grupo)."""
    ex, ey = etiqueta_xy
    ventana = (ex - 1.0, ey - alto, ex + ancho_max, ey + alto)
    circ = circulos_entrada(strokes, ventana)
    cols = [c for c in _columnas(circ) if len(c) in (5, 6)]
    cols = [c for c in cols if min(p[0] for p in c) > ex + 1.0]
    cols.sort(key=lambda c: np.mean([p[0] for p in c]))
    mods = []
    for c in cols:
        xm = float(np.mean([p[0] for p in c]))
        if not mods:
            if xm - ex > 12:          # primer modulo demasiado lejos
                break
        elif abs((xm - mods[-1]['x']) - PASO_MOD) > 0.8:
            break
        mods.append({'x': xm, 'circ': sorted(c, key=lambda p: -p[1])})
    if n_esperado is not None and len(mods) > n_esperado:
        mods = mods[:n_esperado]
    bornes, salida = {}, []
    for i, m in enumerate(mods, 1):
        ys = [p[1] for p in m['circ']]
        gaps = [ys[k] - ys[k + 1] for k in range(len(ys) - 1)]
        k = int(np.argmax(gaps))           # hueco del cuerpo del rele
        sup, inf = m['circ'][:k + 1], m['circ'][k + 1:]
        if len(sup) == 3 and len(inf) == 2:
            orient = 'contactos ARRIBA'
            cont_ext_int = sup              # mayor y (extremo) primero: 11,14,12
            bob_int_ext = inf               # mayor y (junto al LED) primero: A1,A2
        elif len(sup) == 2 and len(inf) == 3:
            orient = 'contactos ABAJO (rele girado 180)'
            cont_ext_int = inf[::-1]
            bob_int_ext = sup[::-1]
        else:
            salida.append({'modulo': f'{tag}{i}', 'error': f'{len(sup)}+{len(inf)} circulos'})
            continue
        nombres = {}
        for nom, p in zip(ORDEN_CONTACTOS, cont_ext_int):
            nombres[nom] = (round(p[0], 2), round(p[1], 2))
        for nom, p in zip(ORDEN_BOBINA, bob_int_ext):
            nombres[nom] = (round(p[0], 2), round(p[1], 2))
        mod = f'{tag}{i}'
        for nom, xy in nombres.items():
            bornes[f'{mod} {nom}'] = xy
        salida.append({'modulo': mod, 'x': round(m['x'], 2), 'orientacion': orient,
                       'bornes': nombres})
    return {'modulos': salida, 'bornes': bornes}


# ------------------------------------------------ asignacion de los usos
# Casos donde el texto del instructivo no alcanza (grupo sin numero de
# modulo) o no coincide con la realidad: (texto, cable) -> borne fisico.
CORRECCIONES = {
    ('46KR A2', '4669'): ('46KR1 A2',
        'el texto no dice modulo; funcional hoja 46: 4669 sale de A2 del modulo [1]; '
        'foto 1.6: 4669 entra en A2 del 1er modulo 46KR'),
    ('46KR A2', '4615'): ('46KR2 A2',
        'el texto no dice modulo; funcional hoja 46: 4615 sale de A2 del modulo [2]; '
        'foto 1.6: 4615 entra en A2 del 2do modulo 46KR'),
    ('43KR2 A2', '1328'): ('43KR1 A2',
        'el instructivo dice 43KR2 pero el funcional hoja 43 dibuja 1328 en A2 del modulo [1] '
        '(A2 de los 4 modulos puenteados con FBS 4-6 AZUL, anotado en el topografico "(A2)"); '
        'foto 1.6: 1328 entra en A2 del 1er modulo 43KR (el de la izquierda)'),
}

FOTO = {'11': 'foto 1.2 (fila "11" impresa, la mas externa)',
        '14': 'foto 1.3 (fila "14" impresa, la del medio)',
        '12': 'foto 1.2/1.3 (fila "12", la interna)',
        'A1': 'foto 1.7 (fila A1, junto al LED)',
        'A2': 'foto 1.6 (fila A2, la del extremo)'}


def punto_de_uso(uso, bornes):
    """uso: dict de usos_por_componente.json. Devuelve (clave_fisica, (x,y), nota)."""
    t = uso['texto'].strip()
    k = (t, str(uso.get('cable')))
    if k in CORRECCIONES:
        fis, nota = CORRECCIONES[k]
        return fis, bornes.get(fis), nota
    return t, bornes.get(t), ''


def ubicar_usos(usos, strokes, grupos=GRUPOS):
    bornes, modulos, puntos = {}, {}, []
    for tag, n in grupos:
        e = usos['componentes'][tag]['etiqueta_topografico']
        r = detectar_grupo_reles(strokes, (e['x'], e['y']), tag, n)
        bornes.update(r['bornes'])
        modulos[tag] = r['modulos']
    for tag, n in grupos:
        for u in usos['componentes'][tag]['usos']:
            fis, xy, nota = punto_de_uso(u, bornes)
            mod, b = fis.split()
            if xy is None:
                puntos.append({'componente': tag, 'texto': u['texto'], 'cables': [u['cable']],
                               'x': None, 'y': None, 'confianza': 'baja',
                               'como': f'no se encontro {fis} en el dibujo'})
                continue
            lado = 'contactos (arriba)' if b in ORDEN_CONTACTOS else 'bobina (abajo)'
            orden = (f'{ORDEN_CONTACTOS.index(b) + 1}o desde el extremo' if b in ORDEN_CONTACTOS
                     else ('interno, junto al LED' if b == 'A1' else 'externo, en el extremo'))
            como = (f'centro del circulo de entrada del conductor (arcos r~1.45 pt, capa COMPONENTES) '
                    f'del modulo {mod} (columna {mod[len(tag):]} a la derecha del rotulo {tag}), '
                    f'lado {lado}, borne {b} = {orden} (numero moldeado en la carcasa RIF-0; '
                    f'el esquema de la hoja de datos 2903370 no es posicional); confirmado con '
                    f'{FOTO[b]}: cable {u["cable"]} en ese borne')
            if nota:
                como = f'{nota}. Punto: {como}'
            puntos.append({'componente': tag, 'texto': u['texto'], 'cables': [u['cable']],
                           'borne_fisico': fis, 'x': xy[0], 'y': xy[1],
                           'confianza': 'alta', 'como': como})
    return {'modulos': modulos, 'bornes': bornes, 'puntos': puntos}


# ------------------------------------------------------ imagen de control
def imagen_control(res, salida, ventana=(832.0, 624.0, 898.0, 728.0), S=22):
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw, ImageFont
    X0, Y0, X1, Y1 = ventana
    doc = pdfium.PdfDocument(TOPO)
    pg = doc[PAGINA]
    W, H = pg.get_size()
    im = pg.render(scale=S, crop=(X0, Y0, W - X1, H - Y1)).to_pil().convert('RGB')
    TOP = 74
    canvas = Image.new('RGB', (im.width, im.height + TOP), 'white')
    canvas.paste(im, (0, TOP))
    im = canvas
    d = ImageDraw.Draw(im, 'RGBA')
    f = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 17)
    fs = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
    fg = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 13)
    fh = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 22)

    def px(x, y):
        return ((x - X0) * S, (Y1 - y) * S + TOP)

    usados = {(p['x'], p['y']) for p in res['puntos']}
    for k, (x, y) in res['bornes'].items():
        cx, cy = px(x, y)
        d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), outline=(110, 110, 110, 255), width=2)
        if (x, y) not in usados:
            t = k.split()[1]
            d.text((cx - d.textlength(t, font=fg) / 2, cy + 8), t, font=fg, fill=(90, 90, 90))
    por_punto = {}
    for p in res['puntos']:
        por_punto.setdefault((p['x'], p['y']), []).append(p)
    for (x, y), ps in por_punto.items():
        cx, cy = px(x, y)
        corr = any(p['texto'] != p['borne_fisico'] for p in ps)
        col = (230, 120, 0, 255) if corr else (220, 0, 0, 255)
        d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=col, outline=(255, 255, 255, 255), width=2)
        lines = [ps[0]['texto'] + ('*' if corr else '')]
        lines += [c for p in ps for c in p['cables']]
        ly = cy + 13
        wmax = max(d.textlength(t, font=f) for t in lines)
        bx = cx - wmax / 2
        d.rectangle((bx - 3, ly - 2, bx + wmax + 3, ly + 19 * len(lines) + 1),
                    fill=(255, 255, 210, 235), outline=col)
        for i, t in enumerate(lines):
            d.text((cx - d.textlength(t, font=f) / 2, ly + 19 * i), t, font=f,
                   fill=(0, 0, 160) if i else (0, 0, 0))
    d.text((8, 6), 'Reles RIF-0 43KR / 46KR / 62KR - pagina 8 topografico, x %.0f..%.0f  y %.0f..%.0f pt'
           % (X0, X1, Y0, Y1), font=fh, fill='black')
    d.text((8, 36), 'rojo = uso ubicado (texto + cable); naranja * = texto del instructivo distinto del borne '
           'fisico (ver JSON); gris = borne libre/puenteado.', font=fs, fill='black')
    d.text((8, 54), 'Contactos (arriba): 11 extremo, 14, 12 interno.  Bobina (abajo): A1 junto al LED, '
           'A2 extremo.  Modulos 1..n de izquierda a derecha desde el rotulo.', font=fs, fill='black')
    im.save(salida)
    return im.size


if __name__ == '__main__':
    st = cargar_trazos()
    U = json.load(open(os.path.join(AQUI, 'usos_por_componente.json'), encoding='utf-8'))
    res = ubicar_usos(U, st)
    for tag, n in GRUPOS:
        assert len(res['modulos'][tag]) == n, (tag, res['modulos'][tag])
    json.dump(res, open(os.path.join(AQUI, 'reles_puntos.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(imagen_control(res, os.path.join(AQUI, 'control_reles.png')))
    for p in res['puntos']:
        print(p['texto'], p['cables'], p['borne_fisico'], p['x'], p['y'], p['confianza'])
