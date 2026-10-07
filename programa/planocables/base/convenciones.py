"""Convenciones del taller para escribir las puntas y los cables (CLAUDE.md, «Reglas del taller»). Solo biblioteca
estandar.

  - Formato de linea: '1110: N2.5MM 11PS1 1 (-) -> LI' = numero, inicial del color + seccion + MM, origen y destino
    (cable_desc arma el 'N2.5MM'; fmt_terminal, el texto de cada punta).
  - Borneras (tag con X tras el prefijo numerico): QUATTRO 'N.p' o doble piso 'N ARRIBA' / 'N ABAJO'.
  - Fuera de la bandeja se escribe 'LI'.

Variantes que NO se unifican (PLAN_MODULAR 2.3): sin_lado (texto) y sin_lado_clave (clave 'texto#cable', corta el
'#cable'). Cambiar estas funciones es cambiar una convencion del taller: hay que preguntarle al usuario."""
import re

from .colores import inicial
from .geom import dist

# equipos de campo con tag de planta: 'BH-01-ZV', 'BH-01-M', 'SP-1' (solenoide de la valvula 1, 75287 hoja 62),
# 'PT 001' / 'PT-001' (numero de lazo con 0 adelante),
# valvula 'ZY(N/C)' / 'ZY(N/O)' (la fuente SHX dibuja la O y el 0 con el mismo trazo: 'ZY(N/0)')
FIELD_RE = re.compile(r'^(?:[A-Z]{2}-\d{2}(?:-[A-Z]{1,2})?|[A-Z]{2}-[1-9]|[A-Z]{2,3}[ -]0\d{2}|[A-Z]{2,3}\s?\(N\s?/\s?[CO0]\))$')
# titulos de las vistas laterales del topografico: 'VISTA LATERAL IZQUIERDA / DERECHA' (topo.RX_LATERAL)
LATERAL_RE = re.compile(r'LATERAL\s+(IZQ|DER)', re.I)


def is_terminal_block(tag):
    """borneras: letra X tras el prefijo numerico (13XC1, 13X24, 43XCS, 62XDO, 12XPS...)"""
    return bool(re.match(r'^(\d{2})?X', tag or ''))


def norm_label(t):
    if not t:
        return ''
    m = re.fullmatch(r'[A-Z]{1,2}\((\d{1,2})\)?', t)       # C(11) / NO(14) -> 11 / 14
    if m:
        return m.group(1)
    m = re.fullmatch(r'(\d{1,3})\s*\(([+-])\)', t)          # 1 (-) -> 1 (-)
    if m:
        return f'{m.group(1)} ({m.group(2)})'
    return t


def fmt_terminal(e):
    """texto del extremo segun las reglas del taller"""
    if e is None:
        return '?'
    if e.get('fuera'):
        return 'LI'
    if e.get('texto'):            # punta de EPLAN: el texto del taller ya viene armado (mapeo verificado o regla general)
        return e['texto']
    tag, b = e.get('tag') or '?', e.get('borne') or ''
    if is_terminal_block(e.get('tag_base')):
        if e.get('punto'):
            return f'{tag} {b}.{e["punto"]}' if b else f'{tag} ?.{e["punto"]}'
        return f'{tag} {b} {e["lado"]}'.replace('  ', ' ')
    if 'KR' in tag or 'PS' in tag or 'PCB' in tag or not e.get('vertical') or b in ('+', '-') or FIELD_RE.fullmatch(tag):
        # (el polo '+'/'-' de un aparato ya lo nombra: '12CB1 +'; un equipo de campo 'BH-01-ZV' / 'PT 001' no es un
        # borne de doble piso: sin ARRIBA/ABAJO)
        return f'{tag} {b}'.strip()
    return f'{tag} {b} {e["lado"]}'.replace('  ', ' ')


def side_of(e):
    """0 = parte de ARRIBA del aparato, 1 = parte de ABAJO"""
    tag = e.get('tag_base') or ''; b = e.get('borne') or ''
    if is_terminal_block(tag):
        if e.get('punto'):                            # QUATTRO: 1, 2 arriba / 3, 4 abajo (segunda bornera del numero: 5..8)
            return 0 if (e['punto'] - 1) % 4 < 2 else 1
        return 0 if e.get('lado') == 'ARRIBA' else 1
    if 'KR' in tag:                                   # rele: contactos arriba, bobina A1/A2 abajo
        return 1 if b in ('A1', 'A2') else 0
    if re.search(r'PS\d', tag):                       # fuente: salida arriba, entrada abajo
        return 1 if re.search(r'L|N|Vin|PE|~', b) and not re.search(r'Vo|\(', b) else 0
    return 0 if e.get('lado') == 'ARRIBA' else 1


def cable_desc(num, a, b, detalle):
    """('N2.5MM', color, '2.5'): color + seccion de la aparicion del numero (en 'detalle', el detalle por aparicion del
    listado) que queda en el camino entre las dos puntas a y b del conductor (b puede ser None). En una derivacion cada
    tramo puede tener otra seccion."""
    occ = [d for d in detalle if d['num'] == num]
    same = [d for d in occ if d['pag'] == a.get('pag')] or occ
    if not same:
        return '', '', ''
    p = a.get('p') or [0, 0]
    q = b.get('p') if b and b.get('pag') == a.get('pag') and b.get('p') else None
    cen = lambda d: ((d['bbox'][0] + d['bbox'][2]) / 2, (d['bbox'][1] + d['bbox'][3]) / 2)
    d = min(same, key=lambda d: dist(p, cen(d)) + (dist(q, cen(d)) if q else 0))
    ini = inicial(d['color'])
    sec = str(d['sec']).replace(',', '.')
    return f'{ini}{sec}MM', d['color'], sec


def punta_sintetica(txt, comp):
    """punta armada desde su texto ('XPE 1 ARRIBA', '13XC1 2.1', '11PS1 L-3'), para los conductores agregados a mano
    (correcciones.json 'agregar'): fmt_terminal(e) == txt. 'comp': componentes del layout (para el tag_base)."""
    tag, _, rest = str(txt or '').partition(' ')
    base = tag if tag in comp else re.sub(r'\d+$', '', tag) if re.sub(r'\d+$', '', tag) in comp else tag
    e = dict(tipo='borne', tag=tag, tag_base=base, borne=rest, punto=None, lado='ARRIBA', vertical=False, circulo=True, p=None, hoja=None, pag=None)
    m = re.match(r'^(.*) (ARRIBA|ABAJO)$', rest)
    if m:
        e.update(borne=m.group(1), lado=m.group(2), vertical=True)
    m2 = re.fullmatch(r'(\d+)\.(\d)', rest)
    if m2 and is_terminal_block(base):
        e.update(borne=m2.group(1), punto=int(m2.group(2)))
    return e


def sin_lado(t):
    """texto de la punta sin ' ARRIBA' / ' ABAJO' al final (el lado puede cambiar con el punto exacto)"""
    return re.sub(r' (ARRIBA|ABAJO)$', '', t or '')


def sin_lado_clave(k):
    """clave 'texto#cable' -> el texto sin el '#cable' y sin ' ARRIBA' / ' ABAJO' (k no puede ser None)"""
    return re.sub(r' (ARRIBA|ABAJO)$', '', k.rsplit('#', 1)[0])


def clave_par(num, a, b):
    """clave estable del tramo (sin ARRIBA/ABAJO, que puede cambiar con el lado fisico; sin importar el orden).
    Es estacion8.e8_clave: con ella se guardan las marcas de E8 (ins['estacion8']['hechos'])"""
    return '|'.join([str(num)] + sorted((sin_lado(a), sin_lado(b))))
