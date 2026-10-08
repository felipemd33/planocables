"""Estacion E8 (gabinete): lo que se cablea con la bandeja ya montada. Dos vistas, como el instructivo de E6:
- BANDEJAS LATERALES (la lateral izquierda del PAE; las dos del TPT y del 66817): cada cable que tiene una punta en un
  aparato de la lateral, con el punto del borne en la vista de esa bandeja (mapeo verificado o aproximado) y el ruteo
  por sus canaletas. La otra punta puede estar en la misma lateral, en la bandeja principal (el cable quedo tirado desde
  E6), en la otra lateral o en la puerta / placa.
  La vista de cada lateral es su PLACA entera (topo.vistas_e8: 'placa', 'ductos', 'titulo', 'rieles_e8' con los rieles
  tapados por los aparatos; las vistas sin riel traen 'rails': []). En una vista sin riel los pasos van aparato por
  aparato.
  - Un cable de una lateral a la otra (66817: 1101 / 1102, de 11XP en la LD al cargador en la LI) sale en las DOS
    laterales, cada una con su punta y su recorrido hasta la salida hacia el fondo, y la otra punta dice a que lateral
    va. Es un solo cable: la marca de cableado (misma clave) vale para las dos.
  - Un cable de una lateral a la puerta / placa sale en la lateral (con su recorrido hasta la salida) y en la tabla del
    aparato de la puerta (con adonde va la otra punta). Tambien es una sola marca.
- PUERTA Y PLACA: los cables de los aparatos que no estan en ninguna bandeja (puerta, placa electronica, botones),
  aparato por aparato y borne por borne, con adonde va la otra punta.
Los cables de campo (los conecta el cliente en la obra) no van en E8. Las marcas de cableado se guardan en
ins['estacion8']['hechos'] (clave del tramo: e8_clave) y se conservan al regenerar.
Punto aproximado del borne (sin mapeo): x del tag + min(borne, 14) * 3,5 pt y 12 pt arriba o abajo del tag segun el lado
del borne (side_of, como E6), las tres medidas escaladas con kr (perfil del riel del dibujo / 24,8 pt del 75441).

ENTRADA A LAS LATERALES Y BISAGRA (etapa E8-2, 2026-10-08, pedido del taller): ins['estacion8']['recorridos'] =
{preguntar, bisagra: 'izq' | 'der' | None, vistas: {<clave_vista>: {entrada: [puntos], puerta: [puntos], grupos:
[{id, nombre, cables, puntos}]}}}, en pt del topografico (como las salidas a LI / LD de E6: los puntos por donde pasan
los cables y, el ultimo, por donde entran a la lateral o salen de ella). La clave de la vista es estable: lado + titulo
normalizado ('LD|vista lateral derecha interior'), no el indice. Lo elige el taller en la web (asistente la primera vez
y boton «Entrada / salida»); se conserva al regenerar (web.gen_instructivo lo pasa como lay['recorridos_e8']) y se
borra con un topografico nuevo (preguntar: True).
Por donde sale cada cable que no queda en la misma lateral (rutear_lineas):
  - un grupo de cables elegidos con recorrido manda;
  - en la lateral del lado de la BISAGRA de la puerta, los que siguen a la puerta salen por 'puerta' (elegida; si no,
    la propuesta: la regla del taller, li_exit, por el borde del lado de la puerta). «Sigue a la puerta» ('a_puerta' en
    la linea) = la otra punta es de «puerta / placa» y su aparato no esta dibujado en el topografico (lo dibujado en la
    vista del fondo, como la zona hidraulica de AutoCAD, queda en el gabinete y sale por la entrada);
  - el resto (vienen de E6, van a la otra lateral, a la zona hidraulica o sin aparato; y los de la otra lateral que van
    a la puerta: cruzan el fondo) por 'entrada' (elegida; si no, la propuesta: a la altura de la salida de E6 del mismo
    lado si las vistas estan alineadas en la hoja, si no la regla del taller por el borde del lado del fondo).
  Sin bisagra elegida (todavia no se contesto el asistente) no hay salida a la puerta: todo sale por la entrada.
  Si el recorrido elegido no llega por las canaletas, el cable sale por la propuesta (no_llega).

EMPALMES CON EL CABLE PROPIO DE UN APARATO (etapa E8-3, 2026-10-08, decision del taller; regla: manda el dibujo del
funcional). Una punta con 'empalme_dibujado' (instructivo: el cable numerado llega al pin a traves de un ■ / ⊟ dibujado,
TPT y 66817: el cargador) se empalma con un WAGO con el cable propio del aparato: la punta va PELADA (sin pino) y el
WAGO queda a la salida de la canaleta mas cercana debajo del aparato (punta libre de una canaleta, por debajo de su
etiqueta; si no hay ninguna debajo, la mas cercana): el recorrido va por las canaletas hasta el WAGO y del WAGO al
aparato va el cable propio (marca_o: el punto del aparato). Varios empalmes del mismo aparato van uno al lado del otro,
en el orden de sus pines. El pin se nombra por la regla de los pines repetidos (n-esimo '+' del simbolo, con los nombres
de su familia en bornes/pines_repetidos.json: '+ panel', '- bateria'). Una punta EMPALME (empalme_en_rama: el RS-485 del
cargador, «EMPALME con 12PS2») va junto al aparato con cuyo cable propio se empalma; si junta 3 o mas conductores
(sus tramos numerados + el cable propio) queda «empalme de N, a confirmar». En la linea: 'empalme' (punta de la
lateral; 'empalme_d' la otra punta de un cable de la misma lateral) = {tipo: 'wago' | 'empalme', texto, aparato, pin,
n, confirmar, pelado, simbolo, p (el empalme), fin (la punta de la canaleta, en su eje), entra (por donde entra a la
canaleta)}. El texto de la punta y la clave de la marca no cambian; los pines sin cable no se muestran."""
import collections
import json
import math
import os
import re
import unicodedata

from instructivo import conductors, fmt_terminal, cable_desc, natk, puntos_salida, sale_abajo, materiales_funcional
# (movida a planocables.base: sigue siendo estacion8.e8_clave)
from planocables.base.convenciones import clave_par as e8_clave, sin_lado, side_of, LATERAL_RE

VERSION = 4       # 2 (2026-10-08): laterales completas (placa, canaletas, riel tapado, vistas sin riel) y lado con side_of
                  # 3 (2026-10-08): entrada a las laterales y bisagra de la puerta (recorridos)
                  # 4 (2026-10-08): empalmes con el cable propio de un aparato (WAGO del cargador, RS-485)
AQUI = os.path.dirname(os.path.abspath(__file__))
MAX_LINEAS = 7
MARGEN_IMG_H = 0.5    # imagen de la lateral: la placa entera + medio perfil de riel de cada lado
DONDE = {'BANDEJA': 'bandeja principal', 'LATERAL': 'otra bandeja lateral', 'E8': 'zona hidráulica', 'AFUERA': 'puerta / placa'}
PUERTA = DONDE['AFUERA']
# propuesta del asistente para la bisagra de la puerta (depende del producto: se elige una vez por trabajo). La del TPT
# (foto 2 del taller): la puerta abre del lado de la lateral izquierda
BISAGRA_PROPUESTA = 'izq'
ALTURA_W = 1.0        # entrada a la altura de la salida de E6: la canaleta horizontal a menos de 1 ancho de esa altura


def _dentro(p, b):
    return b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]


def _dibujado(c):
    """el aparato esta dibujado en el topografico (tiene posicion)"""
    return bool(c) and isinstance(c.get('x'), (int, float)) and isinstance(c.get('y'), (int, float))


def _lado_titulo(t):
    """'LD' / 'LI' por el titulo de la vista ('VISTA LATERAL DERECHA', 'BANDEJA LATERAL IZQUIERDA'), o None"""
    m = LATERAL_RE.search(t or '')
    return None if not m else ('LD' if m.group(1).upper() == 'DER' else 'LI')


def _nombre_vista(v, lado):
    """el titulo si nombra la bandeja (EPLAN: 'BANDEJA LATERAL IZQUIERDA'); si no ('VISTA LATERAL DERECHA INTERIOR' de
    AutoCAD, o sin titulo), 'Bandeja lateral derecha / izquierda'"""
    t = (v.get('titulo') or '').strip()
    if t and re.search(r'BANDEJA', t, re.I):
        return t[:1].upper() + t[1:].lower()
    return 'Bandeja lateral ' + ('derecha' if lado == 'LD' else 'izquierda')


# ------------------------------------------------------------------ entrada a las laterales y bisagra (recorridos)
def clave_vista(lado, titulo):
    """clave estable de la vista de una lateral (no el indice: cambia si se relee el topografico): lado + titulo
    normalizado, sin tildes ni mayusculas ('LD|vista lateral derecha interior'; sin titulo: 'LI|')"""
    t = unicodedata.normalize('NFKD', str(titulo or '')).encode('ascii', 'ignore').decode().lower()
    return f"{lado}|{' '.join(t.split())}"


def recorridos_nuevos():
    """sin nada elegido: el asistente de la web pregunta la primera vez (la bisagra y la entrada de cada lateral)"""
    return {'preguntar': True, 'bisagra': None, 'vistas': {}}


def leer_recorridos(rec):
    """lo guardado en ins['estacion8']['recorridos'], validado (lo roto se descarta). None (la primera vez, o un
    topografico nuevo) -> recorridos_nuevos()"""
    if not isinstance(rec, dict):
        return recorridos_nuevos()
    out = {'preguntar': bool(rec.get('preguntar')), 'bisagra': rec.get('bisagra') if rec.get('bisagra') in ('izq', 'der') else None,
           'vistas': {}}
    vistas = rec.get('vistas') if isinstance(rec.get('vistas'), dict) else {}
    for k, v in vistas.items():
        if not isinstance(v, dict):
            continue
        gs = []
        for g in v.get('grupos') if isinstance(v.get('grupos'), list) else []:
            if not isinstance(g, dict) or not g.get('id'):
                continue
            cab = g.get('cables') if isinstance(g.get('cables'), list) else []
            gs.append({'id': str(g['id']), 'nombre': str(g.get('nombre') or g['id']),
                       'cables': [str(c) for c in cab if isinstance(c, (str, int))], 'puntos': puntos_salida(g)})
        out['vistas'][str(k)] = {'entrada': puntos_salida({'puntos': v.get('entrada')}),
                                 'puerta': puntos_salida({'puntos': v.get('puerta')}), 'grupos': gs}
    return out


def hacia_fondo(lado):
    """borde de la lateral del lado del fondo (por donde entran los cables de la bandeja principal): la lateral
    izquierda por su derecha, la derecha por su izquierda (vistas desplegadas: LI | fondo | LD)"""
    return 'der' if lado == 'LI' else 'izq'


def es_bisagra(rec, lado):
    """la lateral 'lado' es la del lado de la bisagra de la puerta (por ahi pasan los cables a la puerta)"""
    return (rec or {}).get('bisagra') == ('izq' if lado == 'LI' else 'der')


def salida_e6(ins, lado):
    """punto por donde salen de la bandeja principal (instructivo de E6) los cables comunes al lateral 'LI' / 'LD' (sin
    los intrinsecos ni los de 220 VAC, que tienen su salida): el ultimo punto de su ruta, el mas repetido. None si no hay"""
    c = collections.Counter()
    for p in (ins or {}).get('pasos') or []:
        for l in p.get('lineas') or []:
            if l.get('destino') == lado and l.get('ruta') and not l.get('intrinseco') and not sale_abajo(l):
                c[tuple(l['ruta'][-1])] += 1
    return list(c.most_common(1)[0][0]) if c else None


def _alineadas(placa, pag, region, band_pag):
    """la vista de la lateral y la de la bandeja principal estan en la misma hoja y a la misma altura (vistas
    desplegadas, como el constructivo del TPT y del 66817): se solapan en altura al menos la mitad de la mas baja"""
    if not placa or not region or pag is None or pag != band_pag:
        return False
    sol = min(placa[3], region[3]) - max(placa[1], region[1])
    return sol >= 0.5 * min(placa[3] - placa[1], region[3] - region[1])


def _punto_regla(ductos, lado):
    """[x, y] por donde sale la regla del taller (li_exit: la canaleta de arriba del borde 'lado'), o None"""
    from ruteo import Net
    try:
        net = Net(ductos)
        k = net.li_exit(False, False, lado)
        return None if k is None else [round(net.nodes[k][0], 1), round(net.nodes[k][1], 1)]
    except Exception:
        return None


def _a_la_altura(ductos, lado, y):
    """punto de entrada por el borde 'lado' de la red de canaletas a la altura y (la de la salida de E6): de costado de
    la canaleta vertical del borde que pasa por esa altura, o por la punta de la horizontal que llega al borde mas cercana
    en altura (a menos de ALTURA_W anchos de canaleta). None si no hay"""
    from ruteo import ancho, SALIDA_W, BORDE_W
    cs = [d for d in ductos if not d.get('ex')]
    if not cs:
        return None
    W = ancho(ductos); izq = lado != 'der'
    borde = min(d['b'][0] for d in ductos) if izq else max(d['b'][2] for d in ductos)     # (como li_exit)
    best = None
    for d in cs:
        x0, y0, x1, y1 = d['b']
        if not (x0 <= borde + BORDE_W * W if izq else x1 >= borde - BORDE_W * W):
            continue
        xe = x0 - SALIDA_W * W if izq else x1 + SALIDA_W * W
        if not d['h']:
            if y0 <= y <= y1:
                cand = (0.0, [xe, y])
            else:
                continue
        elif y0 - ALTURA_W * W <= y <= y1 + ALTURA_W * W:
            cand = (abs((y0 + y1) / 2 - y), [xe, (y0 + y1) / 2])
        else:
            continue
        if best is None or cand[0] < best[0]:
            best = cand
    return None if best is None else [round(best[1][0], 1), round(best[1][1], 1)]


def propuestas(ductos, lado, bisagra_aqui, sal_e6, placa, pag, band_region, band_pag):
    """lo que se propone sin elegir nada en la lateral 'lado':
    -> {entrada: [x, y] (para la flecha), por_entrada: recorrido para route_line (None = la regla del taller, li_exit),
        puerta: [x, y] o None (solo en la lateral de la bisagra: la regla del taller del lado de la puerta)}
    La entrada propuesta va a la altura de la salida de E6 del mismo lado (sal_e6) si las vistas estan alineadas y hay
    una canaleta a esa altura en el borde del fondo; si no (o si da el mismo punto), la regla del taller."""
    out = dict(entrada=None, por_entrada=None, puerta=None)
    if not ductos:
        return out
    hacia = hacia_fondo(lado)
    regla = _punto_regla(ductos, hacia)
    out['entrada'] = regla
    if sal_e6 and _alineadas(placa, pag, band_region, band_pag):
        p = _a_la_altura(ductos, hacia, float(sal_e6[1]))
        if p and (regla is None or math.dist(p, regla) > 1.0):
            out['entrada'], out['por_entrada'] = p, [p]
    if bisagra_aqui:
        out['puerta'] = _punto_regla(ductos, 'izq' if hacia == 'der' else 'der')
    return out


def _otras_salidas(net, ductos, lado):
    """canaletas partidas (75441: dos horizontales sin una vertical que las una): puntas del lado 'lado' de las
    horizontales que llegan a ese borde, de arriba hacia abajo (si la regla no esta en la misma parte de la red que el
    borne, el cable sale por una de estas)"""
    from ruteo import SALIDA_W, BORDE_W
    hs = [d for d in ductos if d['h'] and not d.get('ex')]
    out = []
    if not hs:
        return out
    borde = max(d['b'][2] for d in hs) if lado == 'der' else min(d['b'][0] for d in hs)
    for d in sorted(hs, key=lambda d: -(d['b'][1] + d['b'][3])):
        if abs((d['b'][2] if lado == 'der' else d['b'][0]) - borde) <= BORDE_W * net.w:
            x = d['b'][2] + SALIDA_W * net.w if lado == 'der' else d['b'][0] - SALIDA_W * net.w
            out.append((x, (d['b'][1] + d['b'][3]) / 2))
    return out


# ------------------------------------------------------------------ empalmes con el cable propio de un aparato (WAGO)
def _leer_json(p):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def familias_catalogo():
    """[(familia, patron)] de bornes/catalogo.json (el tipo de aparato por el renglon de la lista de materiales)"""
    out = []
    for f in (((_leer_json(os.path.join(AQUI, 'bornes', 'catalogo.json')) or {}).get('general') or {}).get('familias') or []):
        try:
            out.append((f['familia'], re.compile(f['patron'])))
        except (KeyError, TypeError, re.error):
            pass
    return out


def nombres_pines():
    """{familia: [nombre del 1.er pin repetido, del 2.o...]} de bornes/pines_repetidos.json"""
    d = _leer_json(os.path.join(AQUI, 'bornes', 'pines_repetidos.json')) or {}
    return {k: list(v.get('nombres') or []) for k, v in (d.get('familias') or {}).items() if isinstance(v, dict)}


def familia_de(textos, fams):
    """familia del aparato por el primer texto que la nombra (renglon de la lista de materiales, textos del recuadro del
    aparato en el funcional); tambien sin los espacios que la fuente SHX mete en las palabras ('Batery Ch arger')"""
    for t in textos:
        if not t:
            continue
        for fam, rx in fams:        # (en el orden del catalogo: 'Battery Ch arger' es cargador, no bateria)
            if rx.search(t) or rx.search(re.sub(r'\s+', '', t)):
                return fam
    return None


def texto_pin(borne, emp, fam, nombres):
    """'+ panel' (el n-esimo '+' del simbolo con el n-esimo nombre de su familia), '+ (2.º de 3)' sin nombres, o el
    rotulo solo"""
    b = str(borne or '').strip()
    n, de = (emp or {}).get('orden'), (emp or {}).get('de')
    lista = nombres.get(fam) or []
    if n and n <= len(lista):
        return f'{b} {lista[n - 1]}'.strip()
    if n and de and de > 1:
        return f'{b} ({n}.º de {de})'.strip()
    return b


def puntas_libres(ductos):
    """puntas de canaleta por donde puede salir un cable (no siguen en otra canaleta): [(fin, salida, canaleta)] con
    fin = la punta del eje (el nodo de ruteo.Net, a 0,1 pt del final) y salida = (dx, dy) hacia afuera"""
    from ruteo import ancho, TOQUE_W
    W = ancho(ductos); m = TOQUE_W * W
    out = []
    for d in ductos:
        x0, y0, x1, y1 = d['b']
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ps = [((x0 + 0.1, cy), (-1, 0)), ((x1 - 0.1, cy), (1, 0))] if d['h'] else [((cx, y0 + 0.1), (0, -1)), ((cx, y1 - 0.1), (0, 1))]
        for fin, dr in ps:
            q = (fin[0] + dr[0] * (0.1 + 0.3 * W), fin[1] + dr[1] * (0.1 + 0.3 * W))       # justo afuera de la punta
            if any(o is not d and o['b'][0] - m <= q[0] <= o['b'][2] + m and o['b'][1] - m <= q[1] <= o['b'][3] + m for o in ductos):
                continue
            out.append((fin, dr, d))
    return out


def punto_empalme(ductos, xy):
    """donde queda el empalme (WAGO) del cable propio de un aparato con etiqueta en xy (decision del taller: debajo del
    aparato, a la salida de la canaleta): la punta libre de canaleta mas cercana por DEBAJO de la etiqueta (si no hay
    ninguna, la mas cercana); el empalme va afuera de la punta, a la distancia de una salida de cable (ruteo.SALIDA_W).
    -> {fin, dir, p} o None (sin canaletas)"""
    from ruteo import ancho, SALIDA_W
    if not ductos:
        return None
    libres = [x for x in puntas_libres(ductos) if not x[2].get('ex')] or puntas_libres(ductos)
    if not libres:
        return None
    abajo = [x for x in libres if x[0][1] < xy[1]]
    fin, dr, _ = min(abajo or libres, key=lambda x: (math.dist(x[0], xy), x[0]))
    W = ancho(ductos)
    return dict(fin=[round(fin[0], 2), round(fin[1], 2)], dir=list(dr),
                p=[round(fin[0] + dr[0] * SALIDA_W * W, 2), round(fin[1] + dr[1] * SALIDA_W * W, 2)])


def con_empalmes(r, eo, ed):
    """recorrido por las canaletas (desde / hasta la punta de la canaleta) con el tramo hasta el empalme de cada punta"""
    if not r:
        return r
    r = [list(p) for p in r]
    for emp, al_final in ((eo, False), (ed, True)):
        if not (emp and emp.get('fin') and emp.get('p')):
            continue
        pre = [list(emp['p'])] + ([list(emp['entra'])] if emp.get('entra') and math.dist(emp['entra'], (r[-1] if al_final else r[0])) > 0.3 else [])
        r = r + pre[::-1] if al_final else pre + r
    return [[round(x, 1), round(y, 1)] for x, y in r]


def rutear_lineas(net, ductos, ls, lado, vrec, bisagra_aqui, por_entrada, escala):
    """recorrido de cada cable de la lateral 'lado' por sus canaletas (net; None = sin canaletas, sin recorrido).
    ls: lineas con _po, _so (y las de la misma lateral, con marca_d, _pd y _sd). vrec: lo elegido en esa vista
    ({entrada, puerta, grupos}). Pone en cada linea ruta y largo_mm; en las que salen de la lateral, 'sale' ('puerta'
    si la lateral es la de la bisagra y la linea sigue a la puerta, 'a_puerta'; si no 'entrada'), 'salida' (id del grupo
    de cables elegidos que manda) y 'no_llega' (el recorrido elegido no llega por las canaletas: sale por la propuesta).
    -> cuantas no llegan"""
    from ruteo import route_line, length
    vrec = vrec or {}
    hacia = hacia_fondo(lado)
    al_frente = 'izq' if hacia == 'der' else 'der'        # borde del lado de la puerta
    grupos = [g for g in vrec.get('grupos') or [] if g.get('puntos')]
    otras = {s: _otras_salidas(net, ductos, s) for s in (hacia, al_frente)} if net else {}
    no_llegan = 0

    def ruta_a(l, por, s):
        emp = l.get('empalme') or {}
        try:
            if emp.get('fin'):           # sale del empalme del cable propio de un aparato: por la punta de su canaleta
                return con_empalmes(route_line(net, tuple(emp['fin']), 0, None, None, False, True, False, lado_li=s,
                                               por=por or None, o_red=True), emp, None)
            return route_line(net, l['_po'][:2], l['_so'], None, None, False, True, False, lado_li=s, por=por or None)
        except Exception:
            return None

    for l in ls:
        l['ruta'] = None; l['largo_mm'] = None
        for k in ('sale', 'salida', 'no_llega'):
            l.pop(k, None)
        afuera_ = 'marca_d' not in l
        g = None
        if afuera_:
            l['sale'] = 'puerta' if bisagra_aqui and l.get('a_puerta') else 'entrada'
            g = next((x for x in grupos if l['num'] in x['cables']), None)
            if g:
                l['salida'] = g['id']
        if not net:
            continue
        if not afuera_:
            eo, ed = l.get('empalme') or {}, l.get('empalme_d') or {}
            try:
                ruta = con_empalmes(route_line(net, tuple(eo['fin']) if eo.get('fin') else l['_po'][:2], l['_so'],
                                               tuple(ed['fin']) if ed.get('fin') else l['_pd'][:2], l['_sd'], False, False, False,
                                               lado_li=hacia, o_red=bool(eo.get('fin')), d_red=bool(ed.get('fin'))), eo, ed)
            except Exception:
                ruta = None
        else:
            s = al_frente if l['sale'] == 'puerta' else hacia
            fijo = vrec.get(l['sale']) or None
            elegido = g['puntos'] if g else fijo
            # el grupo -> la entrada (o salida a la puerta) elegida -> la propuesta (a la altura de E6) -> la regla del
            # taller -> las puntas de otras horizontales (canaletas partidas)
            pruebas = ([elegido] if elegido else []) + ([fijo] if g and fijo else []) \
                + ([por_entrada] if por_entrada and l['sale'] == 'entrada' else []) + [None]
            ruta, por_ok = None, None
            for por in pruebas:
                ruta = ruta_a(l, por, s)
                if ruta:
                    por_ok = por
                    break
            for p in (otras.get(s, []) if not ruta else []):
                ruta = ruta_a(l, [p], s)
                if ruta:
                    break
            if elegido and (not ruta or por_ok is not elegido):
                l['no_llega'] = True
                no_llegan += 1
        if ruta:
            l['ruta'] = ruta
            if escala:
                l['largo_mm'] = int(round(length(ruta) * escala / 10.0) * 10)
    return no_llegan


def build(res, lay, ins):
    """-> dict(version, laterales=[{nombre, lado, region (la imagen), placa, titulo, pag, escala, ductos, rieles,
    sin_riel, pasos, n}], afuera=[{tag, donde, cables}], campo=n, avisos). ins = el instructivo de E6 ya armado (para
    escribir las puntas de la bandeja principal con el mismo texto que E6, con su lado fisico)."""
    comp = lay.get('comp') or {}
    bornes = lay.get('bornes') or {}
    usuario = lay.get('bornes_usuario') or {}
    vistas = lay.get('vistas') or []
    i_band = lay.get('bandeja')
    kr = (lay.get('perfil_riel_pt') or 24.8) / 24.8      # (como E6: 1.0 en el 75441; las medidas en pt se escalan)
    avisos = []
    # entrada a las laterales y bisagra elegidas en la web (se conservan al regenerar; None la primera vez o con un
    # topografico nuevo: el asistente pregunta)
    rec = leer_recorridos(lay.get('recorridos_e8'))
    # vistas laterales: las de la hoja del topografico que no son la bandeja principal y tienen aparatos de un lateral.
    # La vista es la PLACA entera de la lateral (topo.vistas_e8; EPLAN: el recuadro de la vista)
    lat_comp = {t: c for t, c in comp.items() if c.get('ubic') != 'BANDEJA' and not c.get('estacion')
                and isinstance(c.get('x'), (int, float)) and isinstance(c.get('y'), (int, float))}
    laterales = []
    for i, v in enumerate(vistas):
        if i == i_band or not v.get('box') or v.get('en_vista') is not None:
            continue
        placa = v.get('placa') or v['box']
        tags = {t for t, c in lat_comp.items() if _dentro((c['x'], c['y']), placa)}
        if not tags:
            continue
        cs_ = [lat_comp[t] for t in tags]
        lado = _lado_titulo(v.get('titulo')) or (
            'LD' if collections.Counter(c.get('lateral') or 'IZQUIERDO' for c in cs_).most_common(1)[0][0] == 'DERECHO' else 'LI')
        # rieles de la vista y los tapados por los aparatos (fila de etiquetas: rieles_e8, solo para E8)
        ejes = sorted({round(e, 1) for e in (v.get('rieles_e8') or v.get('rails') or [])}, reverse=True)
        # (ejes repetidos: tramos del mismo riel cortados por un hueco)
        rieles = []
        for e in ejes:
            if not rieles or abs(rieles[-1] - e) > 12 * kr:
                rieles.append(e)
        if v.get('placa'):              # imagen: la placa entera con un poco de aire (para ver la salida de los cables)
            m = MARGEN_IMG_H * (lay.get('perfil_riel_pt') or 24.8)
            region = [placa[0] - m, placa[1] - m, placa[2] + m, placa[3] + m]
        else:
            region = list(v['box'])
        ck = clave_vista(lado, v.get('titulo'))
        if any(x['clave'] == ck for x in laterales):         # (dos vistas del mismo lado sin titulo: la segunda con #2)
            ck += f'#{sum(1 for x in laterales if x["clave"].split("#")[0] == ck) + 1}'
        laterales.append(dict(i=i, nombre=_nombre_vista(v, lado), lado=lado, region=region, placa=list(placa), tags=tags,
                              rieles=rieles, ductos=v.get('ductos') or [], titulo=v.get('titulo'), clave=ck))
    de_lateral = {t: L for L in laterales for t in L['tags']}

    # textos de las puntas de la bandeja principal como en E6 (lado fisico): (num, texto sin lado) -> texto de E6
    txt_e6 = {}
    for l in [x for p in ins.get('pasos') or [] for x in p['lineas']] + list(ins.get('otra_estacion') or []) + list(ins.get('quitados') or []):
        for t in (l.get('origen'), l.get('destino')):
            if t and t not in ('LI', 'LD'):
                txt_e6.setdefault((l['num'], sin_lado(t)), t)

    def ap_tag(e):
        """aparato donde esta la punta: su tag; una punta EMPALME ('EMPALME con 12PS2', instructivo.empalme_en_rama) va
        junto al aparato con cuyo cable propio se empalma"""
        if e.get('empalme'):
            m = re.match(r'con\s+(\S+)', e.get('borne') or '')
            if m:
                t = m.group(1)
                return t if t in comp else re.sub(r'\d+$', '', t) if re.sub(r'\d+$', '', t) in comp else t
        return e.get('tag_base')

    def donde(e):
        """('BANDEJA' | 'LATERAL' | 'E8' | 'CAMPO' | 'AFUERA', comp)"""
        if e.get('fuera'):
            return 'AFUERA', None
        t = e.get('tag_base')
        c = comp.get(t)
        if e.get('ubicacion') == 'Campo' or e.get('campo'):
            return 'CAMPO', c
        if e.get('empalme'):            # el empalme va donde esta su aparato si es de una lateral; si no, afuera (como antes)
            return ('LATERAL', comp.get(ap_tag(e))) if ap_tag(e) in de_lateral else ('AFUERA', c)
        if c and c.get('ubic') == 'BANDEJA':
            return 'BANDEJA', c
        if t in de_lateral:
            return 'LATERAL', c
        if c and c.get('estacion'):
            return 'E8', c
        return 'AFUERA', c

    def texto(e, num, w):
        t = fmt_terminal(e)
        if w == 'BANDEJA':
            return txt_e6.get((num, sin_lado(t)), t)
        return t

    def punto(e, num, L):
        """(x, y, r, exacto) del borne en la vista lateral L. Sin mapeo: aproximado, del lado del borne (side_of, como
        E6: 'parte de arriba' arriba del tag y 'parte de abajo' abajo), con las medidas escaladas con kr"""
        for t in (fmt_terminal(e), e.get('texto')):
            if not t:
                continue
            for k in (f'{t}#{num}', t):
                v = usuario.get(k) or bornes.get(k)
                if v and _dentro((float(v[0]), float(v[1])), L['placa']):
                    return float(v[0]), float(v[1]), (float(v[2]) if len(v) > 2 and v[2] else None), True
        c = comp.get(ap_tag(e)) or {}
        x, y = float(c.get('x') or 0), float(c.get('y') or 0)
        if e.get('empalme'):          # (el empalme no es un borne: el punto del aparato, donde llega su cable propio)
            return x, y, None, False
        b = e.get('borne') or ''
        if re.fullmatch(r'\d+', b):
            x += min(int(b), 14) * 3.5 * kr      # el tag nombra los bornes que tiene a su derecha
        return x, y + (12 * kr if side_of(e) == 0 else -12 * kr), None, False

    def lado_de(p, e, L):
        """(0 = parte de arriba / 1 = parte de abajo, numero de riel: 1 = el de arriba; None en una vista sin riel).
        Punto exacto: arriba o abajo del eje del riel mas cercano. Punto aproximado: el riel del tag y el lado del borne
        (side_of, como E6). Sin rieles: el lado del borne."""
        if not L['rieles']:
            return side_of(e), None
        y = p[1] if p[3] else float((comp.get(ap_tag(e)) or {}).get('y') or p[1])
        i = min(range(len(L['rieles'])), key=lambda k: abs(L['rieles'][k] - y))
        if not p[3]:
            return side_of(e), i + 1
        return (0 if p[1] >= L['rieles'][i] else 1), i + 1

    # empalmes con el cable propio de un aparato: la familia del aparato (lista de materiales del funcional o textos de
    # su recuadro) da el nombre de sus pines repetidos ('+ panel')
    cache_fam = {}

    def fam_de(tag, txt):
        if 'fams' not in cache_fam:
            cache_fam['fams'], cache_fam['nombres'] = familias_catalogo(), nombres_pines()
            try:
                from bornes.motor import materiales_de_lineas
                cache_fam['bom'] = materiales_de_lineas(materiales_funcional(res)) or {}
            except Exception:
                cache_fam['bom'] = {}
        return familia_de([cache_fam['bom'].get(tag), txt], cache_fam['fams'])

    def empalme_de(e, nid, c):
        """lo que hay en la punta e de un empalme con el cable propio de su aparato (sin la posicion), o None"""
        ap = ap_tag(e)
        emp = e.get('empalme_dibujado')
        if emp and emp.get('tipo') == 'wago':
            pin = texto_pin(e.get('borne'), emp, fam_de(ap, emp.get('aparato_txt')), cache_fam.get('nombres') or {})
            return dict(tipo='wago', aparato=ap, pin=pin, n=2, confirmar=False, pelado=True, simbolo=emp.get('simbolo'),
                        texto=f'WAGO con el cable propio de {ap}' + (f' · {pin}' if pin else ''),
                        _orden=(emp.get('orden') or 99, (emp.get('p') or [0, 0])[0]))
        if e.get('empalme'):
            # conductores en el empalme: los tramos numerados que llegan + el cable propio del aparato
            n = 1 + sum(1 for p_ in c['pares'] if nid in p_)
            if n <= 2:
                return dict(tipo='wago', aparato=ap, pin='', n=n, confirmar=False, pelado=True, simbolo='relleno',
                            texto=f'WAGO con el cable propio de {ap}', _orden=(100, 0))
            return dict(tipo='empalme', aparato=ap, pin='', n=n, confirmar=True, pelado=False, simbolo='relleno',
                        texto=f'Empalme de {n}, a confirmar (con el cable propio de {ap})', _orden=(100, 0))
        return None

    cs = conductors(res)
    tramos_lat = collections.defaultdict(list)
    afuera = collections.defaultdict(list)
    n_campo = 0
    vistos = set()
    for num, c in cs.items():
        nodes = c['nodes']
        for a, b in c['pares']:
            ea, eb = nodes[a], nodes[b]
            wa, ca = donde(ea); wb, cb = donde(eb)
            if 'CAMPO' in (wa, wb):
                n_campo += 1
                continue
            if wa == 'BANDEJA' and wb == 'BANDEJA':
                continue
            pdesc = (c.get('desc_par') or {}).get((a, b))
            desc, col, sec = pdesc if pdesc else cable_desc(res, num, ea, eb)
            ta, tb = texto(ea, num, wa), texto(eb, num, wb)
            k = e8_clave(num, ta, tb)
            if k in vistos:
                continue
            vistos.add(k)
            base = dict(num=num, cable=desc, color=col, secc=sec, clave=k,
                        hojas=sorted({ea.get('hoja'), eb.get('hoja')} - {None}, key=natk))
            # --- bandejas laterales
            for e, w, t, eo, wo, to, ne, no in ((ea, wa, ta, eb, wb, tb, a, b), (eb, wb, tb, ea, wa, ta, b, a)):
                if w != 'LATERAL':
                    continue
                L = de_lateral[ap_tag(e)]
                otra_lat = wo == 'LATERAL' and de_lateral.get(ap_tag(eo)) is L
                if otra_lat and (num, k) in {(x['num'], x['clave']) for x in tramos_lat[L['i']]}:
                    continue          # (el tramo de lateral a lateral ya se puso desde la otra punta)
                po = punto(e, num, L)
                so, riel = lado_de(po, e, L)
                ce = comp.get(ap_tag(e)) or {}
                l = dict(base, origen=t, marca_o=[round(po[0], 2), round(po[1], 2), po[2]], exacto_o=po[3],
                         riel=riel, lado='arriba' if so == 0 else 'abajo', componente=e.get('tag') or e.get('tag_base') or '',
                         _so=so, _po=po, _x=ce.get('x') or po[0], _y=ce.get('y') or po[1], _tag=ap_tag(e))
                emp = empalme_de(e, ne, c)
                if emp:
                    l['_emp'] = emp          # empalme con el cable propio del aparato (su lugar, despues: por aparato)
                if otra_lat:
                    pd = punto(eo, num, L)
                    sd, _ = lado_de(pd, eo, L)
                    l.update(destino=to, marca_d=[round(pd[0], 2), round(pd[1], 2), pd[2]], exacto_d=pd[3], otra='misma bandeja',
                             _sd=sd, _pd=pd)
                    emp_d = empalme_de(eo, no, c)
                    if emp_d:
                        l['_emp_d'] = emp_d
                elif wo == 'LATERAL':
                    # a la OTRA lateral: sale en las dos (cada una con su punta); la otra punta dice a cual va
                    l.update(destino=to, otra=de_lateral[ap_tag(eo)]['nombre'].lower())
                else:
                    l.update(destino=to, otra='sin aparato en el plano' if to in ('LI', 'LD') else DONDE[wo])
                    if wo == 'BANDEJA':
                        l['viene_de_e6'] = True     # la punta de la bandeja principal se cableo en E6: el cable ya esta tirado
                    elif (l['otra'] == PUERTA and eo.get('tag_base') and not str(to).startswith('?')
                          and not _dibujado(comp.get(ap_tag(eo)))):
                        # sigue a la puerta: un aparato que no esta dibujado en el topografico (lo que esta dibujado en la
                        # vista del fondo, como la zona hidraulica de AutoCAD, queda en el gabinete: sale por la entrada;
                        # una punta sin aparato, '?', tampoco)
                        l['a_puerta'] = True
                tramos_lat[L['i']].append(l)
            # --- puerta y placa (y la zona hidraulica): aparato por aparato
            for e, w, t, eo, wo, to, ne in ((ea, wa, ta, eb, wb, tb, a), (eb, wb, tb, ea, wa, ta, b)):
                if w not in ('AFUERA', 'E8') or t in ('LI', 'LD') or not e.get('tag_base'):
                    continue
                donde_o = ('sin aparato en el plano' if to in ('LI', 'LD') else
                           de_lateral[ap_tag(eo)]['nombre'].lower() if wo == 'LATERAL' else DONDE[wo])
                fila = dict(base, borne=t, pin=e.get('borne') or '', otra=to, otra_donde=donde_o, viene_de_e6=wo == 'BANDEJA')
                emp = empalme_de(e, ne, c)
                if emp:
                    fila['empalme'] = {k_: v_ for k_, v_ in emp.items() if not k_.startswith('_')}
                afuera[(e['tag_base'], w)].append(fila)

    def ubicar_empalmes(L, ls):
        """lugar de los empalmes con el cable propio de cada aparato de la lateral L (decision del taller: debajo del
        aparato, a la salida de la canaleta): uno al lado del otro a lo ancho de la canaleta, en el orden de los pines
        del aparato (los RS-485 al final). Deja en cada linea 'empalme' / 'empalme_d' con p, fin y entra."""
        from ruteo import ancho
        por_ap = collections.defaultdict(dict)          # aparato -> {(num, texto de la punta): orden}
        for l in ls:
            for kk, txt in (('_emp', l['origen']), ('_emp_d', l.get('destino'))):
                if l.get(kk):
                    por_ap[l[kk]['aparato']].setdefault((l['num'], txt), (l[kk]['_orden'], natk(l['num'])))
        lugar = {}
        for ap, ks in por_ap.items():
            c = comp.get(ap) or {}
            base = punto_empalme(L['ductos'], (float(c.get('x') or 0), float(c.get('y') or 0))) if L['ductos'] else None
            if not base:
                continue
            W = ancho(L['ductos'])
            orden = sorted(ks, key=lambda k_: ks[k_])
            n = len(orden)
            paso = min(0.2 * W, 0.8 * W / (n - 1)) if n > 1 else 0.0
            perp = (-base['dir'][1], base['dir'][0])
            for i, k_ in enumerate(orden):
                o = (i - (n - 1) / 2) * paso
                lugar[(ap,) + k_] = dict(fin=base['fin'], p=[round(base['p'][0] + perp[0] * o, 2), round(base['p'][1] + perp[1] * o, 2)],
                                          entra=[round(base['fin'][0] + perp[0] * o, 2), round(base['fin'][1] + perp[1] * o, 2)])
        for l in ls:
            for kk, out_k, txt in (('_emp', 'empalme', l['origen']), ('_emp_d', 'empalme_d', l.get('destino'))):
                emp = l.get(kk)
                if not emp:
                    continue
                d = {k_: v_ for k_, v_ in emp.items() if not k_.startswith('_')}
                d.update(lugar.get((emp['aparato'], l['num'], txt)) or {})
                l[out_k] = d

    # ---- orden y pasos de cada bandeja lateral (regla del taller: riel por riel de arriba abajo; en cada riel la parte
    # de arriba de izquierda a derecha y despues la de abajo; aparato por aparato; el de mas afuera del riel primero).
    # Vista SIN riel: aparato por aparato, de arriba abajo y de izquierda a derecha; en cada aparato la parte de arriba
    # y despues la de abajo
    out_lat = []
    for L in laterales:
        ls = tramos_lat[L['i']]
        if not ls:
            continue
        for l in ls:
            if L['rieles']:
                eje = L['rieles'][l['riel'] - 1]
                l['_orden'] = (l['riel'], l['_so'], round(l['_x'], 1), -round(abs(l['_po'][1] - eje) / (3.0 * kr)), l['_po'][0], natk(l['origen']))
            else:
                l['_orden'] = (-round(l['_y']), round(l['_x'], 1), l['_tag'], l['_so'], l['_po'][0], natk(l['origen']))
        ls.sort(key=lambda l: l['_orden'])
        ubicar_empalmes(L, ls)
        # ruteo por las canaletas de la bandeja lateral; los que salen de la lateral entran / salen por la entrada (del
        # lado del fondo) o, en la lateral de la bisagra, los que siguen a la puerta por el lado de la puerta: elegidas
        # a mano (recorridos) o la propuesta (ver rutear_lineas)
        net = None
        if L['ductos']:
            try:
                from ruteo import Net
                net = Net(L['ductos'])
            except Exception as ex_:
                avisos.append(f"{L['nombre']}: no se pudieron armar las canaletas ({ex_})")
        bis = es_bisagra(rec, L['lado'])
        prop = propuestas(L['ductos'], L['lado'], bis, salida_e6(ins, L['lado']), L['placa'], lay.get('pag'), lay.get('region'), lay.get('pag'))
        n_no = rutear_lineas(net, L['ductos'], ls, L['lado'], rec['vistas'].get(L['clave']), bis, prop['por_entrada'], lay.get('escala'))
        if n_no:
            avisos.append(f"{L['nombre']}: {n_no} cable{'s' if n_no > 1 else ''} no llega{'n' if n_no > 1 else ''} por las canaletas "
                          f"hasta la entrada o salida elegida: sale{'n' if n_no > 1 else ''} por la propuesta")
        pasos = []
        for l in ls:
            cur = pasos[-1] if pasos else None
            if L['rieles']:
                nuevo = cur is None or (cur['riel'], cur['lado']) != (l['riel'], l['lado']) or (
                    len(cur['lineas']) >= MAX_LINEAS and l['componente'] != cur['lineas'][-1]['componente'])
            else:                       # sin riel: un paso por aparato
                nuevo = cur is None or cur['aparato'] != l['_tag']
            if nuevo:
                cur = dict(riel=l['riel'], lado=l['lado'], lineas=[]) if L['rieles'] else dict(riel=None, aparato=l['_tag'], lineas=[])
                pasos.append(cur)
            cur['lineas'].append(l)
        for n, p in enumerate(pasos, 1):
            comps = list(dict.fromkeys(l['componente'] for l in p['lineas']))
            p.update(n=n, titulo=(f"Riel {p['riel']} · parte de {p['lado']} · " if L['rieles'] else 'Aparato ') + ', '.join(comps))
            for l in p['lineas']:
                for k in [k for k in l if k.startswith('_')]:
                    l.pop(k)
        out_lat.append(dict(nombre=L['nombre'], lado=L['lado'], vista=L['i'], region=[round(v, 2) for v in L['region']], pag=lay.get('pag'),
                            escala=lay.get('escala'), ductos=L['ductos'], rieles=L['rieles'], pasos=pasos,
                            n=sum(len(p['lineas']) for p in pasos), sin_canaletas=not L['ductos'],
                            exactos=sum(1 for p in pasos for l in p['lineas'] if l.get('exacto_o')),
                            placa=[round(v, 2) for v in L['placa']], titulo=L['titulo'], sin_riel=not L['rieles'],
                            clave_vista=L['clave'], hacia=hacia_fondo(L['lado']), bisagra=bis,
                            entrada_propuesta=prop['entrada'], puerta_propuesta=prop['puerta']))
    if not out_lat:
        avisos.append('el topográfico no tiene una vista de bandeja lateral con aparatos: la vista de la lateral queda vacía')

    # ---- puerta y placa: un grupo por aparato, borne por borne
    grupos = []
    for (tag, w), xs in afuera.items():
        xs.sort(key=lambda x: (natk(x['pin']), natk(x['num'])))
        grupos.append(dict(tag=tag, zona='zona hidráulica' if w == 'E8' else 'puerta / placa', cables=xs,
                           nota=(comp.get(tag) or {}).get('nota')))
    grupos.sort(key=lambda g: (g['zona'] != 'puerta / placa', -len(g['cables']), natk(g['tag'])))
    return dict(version=VERSION, laterales=out_lat, afuera=grupos, campo=n_campo, avisos=avisos, hechos=[],
                recorridos=rec, bisagra_propuesta=BISAGRA_PROPUESTA)


def rutear_guardado(ins, rec):
    """vista previa del editor de entradas de la web (POST /e8/recorridos): vuelve a rutear los cables que salen de cada
    lateral con los recorridos 'rec' SIN rearmar nada, desde lo guardado en ins['estacion8'] (marca_o, lado, otra) y con
    las canaletas y la escala de cada lateral. La propuesta sale como en build (salida de E6 de ins y la bandeja de
    ins['topo']). Como la vista previa de salidas de E6, rutea desde marca_o (redondeado a 0,01): puede haber una decima
    de diferencia con build en algun vertice.
    -> [{vista, clave_vista, bisagra, entrada_propuesta, puerta_propuesta, no_llegan,
         lineas: [{clave, ruta, largo_mm, sale, salida, no_llega}]}]   (lineas = las que salen de la lateral, en orden)"""
    from ruteo import Net
    rec = leer_recorridos(rec)
    topo = (ins or {}).get('topo') or {}
    out = []
    for i, L in enumerate(((ins or {}).get('estacion8') or {}).get('laterales') or []):
        ductos = L.get('ductos') or []
        ck = L.get('clave_vista') or clave_vista(L.get('lado'), L.get('titulo'))
        bis = es_bisagra(rec, L.get('lado'))
        prop = propuestas(ductos, L.get('lado'), bis, salida_e6(ins, L.get('lado')), L.get('placa') or L.get('region'), L.get('pag'),
                          topo.get('region'), topo.get('pag'))
        ls = []
        for p in L.get('pasos') or []:
            for l in p.get('lineas') or []:
                mo = l.get('marca_o')
                if 'marca_d' in l or not mo:
                    continue
                ls.append(dict(num=l.get('num'), otra=l.get('otra'), a_puerta=l.get('a_puerta'), clave=l.get('clave'), _po=(float(mo[0]), float(mo[1])),
                               _so=0 if l.get('lado') == 'arriba' else 1, empalme=l.get('empalme')))
        try:
            net = Net(ductos) if ductos else None
        except Exception:
            net = None
        n_no = rutear_lineas(net, ductos, ls, L.get('lado'), rec['vistas'].get(ck), bis, prop['por_entrada'], L.get('escala'))
        out.append(dict(vista=i, clave_vista=ck, bisagra=bis, entrada_propuesta=prop['entrada'], puerta_propuesta=prop['puerta'],
                        no_llegan=n_no, lineas=[{k: l.get(k) for k in ('clave', 'ruta', 'largo_mm', 'sale', 'salida', 'no_llega')} for l in ls]))
    return out
