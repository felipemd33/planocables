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
del borne (side_of, como E6), las tres medidas escaladas con kr (perfil del riel del dibujo / 24,8 pt del 75441)."""
import collections
import math
import re

from instructivo import conductors, fmt_terminal, cable_desc, natk
# (movida a planocables.base: sigue siendo estacion8.e8_clave)
from planocables.base.convenciones import clave_par as e8_clave, sin_lado, side_of, LATERAL_RE

VERSION = 2       # 2 (2026-10-08): laterales completas (placa, canaletas, riel tapado, vistas sin riel) y lado con side_of
MAX_LINEAS = 7
MARGEN_IMG_H = 0.5    # imagen de la lateral: la placa entera + medio perfil de riel de cada lado
DONDE = {'BANDEJA': 'bandeja principal', 'LATERAL': 'otra bandeja lateral', 'E8': 'zona hidráulica', 'AFUERA': 'puerta / placa'}


def _dentro(p, b):
    return b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]


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
        laterales.append(dict(i=i, nombre=_nombre_vista(v, lado), lado=lado, region=region, placa=list(placa), tags=tags,
                              rieles=rieles, ductos=v.get('ductos') or [], titulo=v.get('titulo')))
    de_lateral = {t: L for L in laterales for t in L['tags']}

    # textos de las puntas de la bandeja principal como en E6 (lado fisico): (num, texto sin lado) -> texto de E6
    txt_e6 = {}
    for l in [x for p in ins.get('pasos') or [] for x in p['lineas']] + list(ins.get('otra_estacion') or []) + list(ins.get('quitados') or []):
        for t in (l.get('origen'), l.get('destino')):
            if t and t not in ('LI', 'LD'):
                txt_e6.setdefault((l['num'], sin_lado(t)), t)

    def donde(e):
        """('BANDEJA' | 'LATERAL' | 'E8' | 'CAMPO' | 'AFUERA', comp)"""
        if e.get('fuera'):
            return 'AFUERA', None
        t = e.get('tag_base')
        c = comp.get(t)
        if e.get('ubicacion') == 'Campo' or e.get('campo'):
            return 'CAMPO', c
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
        c = comp.get(e.get('tag_base')) or {}
        x, y = float(c.get('x') or 0), float(c.get('y') or 0)
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
        y = p[1] if p[3] else float((comp.get(e.get('tag_base')) or {}).get('y') or p[1])
        i = min(range(len(L['rieles'])), key=lambda k: abs(L['rieles'][k] - y))
        if not p[3]:
            return side_of(e), i + 1
        return (0 if p[1] >= L['rieles'][i] else 1), i + 1

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
            for e, w, t, eo, wo, to in ((ea, wa, ta, eb, wb, tb), (eb, wb, tb, ea, wa, ta)):
                if w != 'LATERAL':
                    continue
                L = de_lateral[e['tag_base']]
                otra_lat = wo == 'LATERAL' and de_lateral.get(eo.get('tag_base')) is L
                if otra_lat and (num, k) in {(x['num'], x['clave']) for x in tramos_lat[L['i']]}:
                    continue          # (el tramo de lateral a lateral ya se puso desde la otra punta)
                po = punto(e, num, L)
                so, riel = lado_de(po, e, L)
                ce = comp.get(e['tag_base']) or {}
                l = dict(base, origen=t, marca_o=[round(po[0], 2), round(po[1], 2), po[2]], exacto_o=po[3],
                         riel=riel, lado='arriba' if so == 0 else 'abajo', componente=e.get('tag') or e.get('tag_base') or '',
                         _so=so, _po=po, _x=ce.get('x') or po[0], _y=ce.get('y') or po[1], _tag=e['tag_base'])
                if otra_lat:
                    pd = punto(eo, num, L)
                    sd, _ = lado_de(pd, eo, L)
                    l.update(destino=to, marca_d=[round(pd[0], 2), round(pd[1], 2), pd[2]], exacto_d=pd[3], otra='misma bandeja',
                             _sd=sd, _pd=pd)
                elif wo == 'LATERAL':
                    # a la OTRA lateral: sale en las dos (cada una con su punta); la otra punta dice a cual va
                    l.update(destino=to, otra=de_lateral[eo['tag_base']]['nombre'].lower())
                else:
                    l.update(destino=to, otra='sin aparato en el plano' if to in ('LI', 'LD') else DONDE[wo])
                    if wo == 'BANDEJA':
                        l['viene_de_e6'] = True     # la punta de la bandeja principal se cableo en E6: el cable ya esta tirado
                tramos_lat[L['i']].append(l)
            # --- puerta y placa (y la zona hidraulica): aparato por aparato
            for e, w, t, eo, wo, to in ((ea, wa, ta, eb, wb, tb), (eb, wb, tb, ea, wa, ta)):
                if w not in ('AFUERA', 'E8') or t in ('LI', 'LD') or not e.get('tag_base'):
                    continue
                donde_o = ('sin aparato en el plano' if to in ('LI', 'LD') else
                           de_lateral[eo['tag_base']]['nombre'].lower() if wo == 'LATERAL' else DONDE[wo])
                afuera[(e['tag_base'], w)].append(dict(base, borne=t, pin=e.get('borne') or '', otra=to, otra_donde=donde_o,
                                                       viene_de_e6=wo == 'BANDEJA'))

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
        # ruteo por las canaletas de la bandeja lateral; los que van afuera salen por el borde del lado de la principal
        net = None
        if L['ductos']:
            try:
                from ruteo import Net
                net = Net(L['ductos'])
            except Exception as ex_:
                avisos.append(f"{L['nombre']}: no se pudieron armar las canaletas ({ex_})")
        hacia = 'der' if L['lado'] == 'LI' else 'izq'      # la lateral izquierda sale por su borde derecho (hacia el fondo)
        from ruteo import route_line, length, SALIDA_W, BORDE_W
        # canaletas partidas (75441: dos horizontales sin una vertical que las una): si la salida de la regla (li_exit, la
        # canaleta de arriba) no esta en la misma parte de la red que el borne, el cable sale por la punta del lado del
        # fondo de otra horizontal que llegue a ese borde (de arriba hacia abajo)
        otras_salidas = []
        if net:
            hs = [d for d in L['ductos'] if d['h'] and not d.get('ex')]
            if hs:
                borde = max(d['b'][2] for d in hs) if hacia == 'der' else min(d['b'][0] for d in hs)
                for d in sorted(hs, key=lambda d: -(d['b'][1] + d['b'][3])):
                    if abs((d['b'][2] if hacia == 'der' else d['b'][0]) - borde) <= BORDE_W * net.w:
                        x = d['b'][2] + SALIDA_W * net.w if hacia == 'der' else d['b'][0] - SALIDA_W * net.w
                        otras_salidas.append((x, (d['b'][1] + d['b'][3]) / 2))
        for l in ls:
            l['ruta'] = None; l['largo_mm'] = None
            if not net:
                continue
            afuera_ = 'marca_d' not in l
            try:
                ruta = route_line(net, l['_po'][:2], l['_so'], None if afuera_ else l['_pd'][:2], None if afuera_ else l['_sd'],
                                  False, afuera_, False, lado_li=hacia)
            except Exception:
                ruta = None
            for p in (otras_salidas if afuera_ and not ruta else []):
                try:
                    ruta = route_line(net, l['_po'][:2], l['_so'], None, None, False, True, False, lado_li=hacia, por=[p])
                except Exception:
                    ruta = None
                if ruta:
                    break
            if ruta:
                l['ruta'] = ruta
                if lay.get('escala'):
                    l['largo_mm'] = int(round(length(ruta) * lay['escala'] / 10.0) * 10)
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
                            placa=[round(v, 2) for v in L['placa']], titulo=L['titulo'], sin_riel=not L['rieles']))
    if not out_lat:
        avisos.append('el topográfico no tiene una vista de bandeja lateral con aparatos: la vista de la lateral queda vacía')

    # ---- puerta y placa: un grupo por aparato, borne por borne
    grupos = []
    for (tag, w), xs in afuera.items():
        xs.sort(key=lambda x: (natk(x['pin']), natk(x['num'])))
        grupos.append(dict(tag=tag, zona='zona hidráulica' if w == 'E8' else 'puerta / placa', cables=xs,
                           nota=(comp.get(tag) or {}).get('nota')))
    grupos.sort(key=lambda g: (g['zona'] != 'puerta / placa', -len(g['cables']), natk(g['tag'])))
    return dict(version=VERSION, laterales=out_lat, afuera=grupos, campo=n_campo, avisos=avisos, hechos=[])
