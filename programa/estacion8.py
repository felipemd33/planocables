"""Estacion E8 (gabinete): lo que se cablea con la bandeja ya montada. Dos vistas, como el instructivo de E6:
- BANDEJAS LATERALES (la lateral izquierda del PAE): cada cable que tiene una punta en un aparato de la lateral, con
  el punto del borne en la vista de esa bandeja (mapeo verificado o aproximado) y el ruteo por sus canaletas. La otra
  punta puede estar en la misma lateral, en la bandeja principal (el cable quedo tirado desde E6) o en la puerta / placa.
- PUERTA Y PLACA: los cables de los aparatos que no estan en ninguna bandeja (puerta, placa electronica, botones),
  aparato por aparato y borne por borne, con adonde va la otra punta.
Los cables de campo (los conecta el cliente en la obra) no van en E8. Las marcas de cableado se guardan en
ins['estacion8']['hechos'] (clave del tramo: e8_clave) y se conservan al regenerar."""
import collections
import math
import re

from instructivo import conductors, fmt_terminal, cable_desc, natk

VERSION = 1
MAX_LINEAS = 7
DONDE = {'BANDEJA': 'bandeja principal', 'LATERAL': 'otra bandeja lateral', 'E8': 'zona hidráulica', 'AFUERA': 'puerta / placa'}


def e8_clave(num, a, b):
    """clave estable del tramo (sin ARRIBA/ABAJO, que puede cambiar con el lado fisico; sin importar el orden)"""
    s = lambda t: re.sub(r' (ARRIBA|ABAJO)$', '', t or '')
    return '|'.join([str(num)] + sorted((s(a), s(b))))


def _dentro(p, b):
    return b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]


def _nombre_vista(v, comps):
    t = (v.get('titulo') or '').strip()
    if t:
        return t[:1].upper() + t[1:].lower()
    lados = collections.Counter(c.get('lateral') or 'IZQUIERDO' for c in comps)
    return 'Bandeja lateral ' + ('derecha' if lados.most_common(1)[0][0] == 'DERECHO' else 'izquierda') if lados else 'Bandeja lateral'


def build(res, lay, ins):
    """-> dict(version, laterales=[{nombre, lado, region, pag, escala, ductos, rieles, pasos, n}], afuera=[{tag, donde,
    cables}], campo=n, avisos). ins = el instructivo de E6 ya armado (para escribir las puntas de la bandeja principal
    con el mismo texto que E6, con su lado fisico)."""
    comp = lay.get('comp') or {}
    bornes = lay.get('bornes') or {}
    usuario = lay.get('bornes_usuario') or {}
    vistas = lay.get('vistas') or []
    i_band = lay.get('bandeja')
    avisos = []
    # vistas laterales: las de la hoja del topografico que no son la bandeja principal y tienen aparatos de un lateral
    lat_comp = {t: c for t, c in comp.items() if c.get('ubic') != 'BANDEJA' and not c.get('estacion')
                and isinstance(c.get('x'), (int, float)) and isinstance(c.get('y'), (int, float))}
    laterales = []
    for i, v in enumerate(vistas):
        if i == i_band or not v.get('box'):
            continue
        tags = {t for t, c in lat_comp.items() if _dentro((c['x'], c['y']), v['box'])}
        if not tags:
            continue
        cs_ = [lat_comp[t] for t in tags]
        lado = 'LD' if collections.Counter(c.get('lateral') or 'IZQUIERDO' for c in cs_).most_common(1)[0][0] == 'DERECHO' else 'LI'
        ejes = sorted({round(e, 1) for e in v.get('rails') or []}, reverse=True)
        # (ejes repetidos: tramos del mismo riel cortados por un hueco)
        rieles = []
        for e in ejes:
            if not rieles or abs(rieles[-1] - e) > 12:
                rieles.append(e)
        laterales.append(dict(i=i, nombre=_nombre_vista(v, cs_), lado=lado, region=v['box'], tags=tags, rieles=rieles,
                              ductos=v.get('ductos') or []))
    de_lateral = {t: L for L in laterales for t in L['tags']}

    # textos de las puntas de la bandeja principal como en E6 (lado fisico): (num, texto sin lado) -> texto de E6
    sin_lado = lambda t: re.sub(r' (ARRIBA|ABAJO)$', '', t or '')
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
        """(x, y, r, exacto) del borne en la vista lateral L"""
        for t in (fmt_terminal(e), e.get('texto')):
            if not t:
                continue
            for k in (f'{t}#{num}', t):
                v = usuario.get(k) or bornes.get(k)
                if v and _dentro((float(v[0]), float(v[1])), L['region']):
                    return float(v[0]), float(v[1]), (float(v[2]) if len(v) > 2 and v[2] else None), True
        c = comp.get(e.get('tag_base')) or {}
        x, y = float(c.get('x') or 0), float(c.get('y') or 0)
        b = e.get('borne') or ''
        if re.fullmatch(r'\d+', b):
            x += min(int(b), 14) * 3.5       # el tag nombra los bornes que tiene a su derecha
        return x, y - 12, None, False

    def lado_de(p, L):
        """0 = arriba del eje del riel mas cercano, 1 = abajo; y el numero de riel (1 = el de arriba)"""
        if not L['rieles']:
            return 0, 1
        i = min(range(len(L['rieles'])), key=lambda k: abs(L['rieles'][k] - p[1]))
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
                so, riel = lado_de(po, L)
                l = dict(base, origen=t, marca_o=[round(po[0], 2), round(po[1], 2), po[2]], exacto_o=po[3],
                         riel=riel, lado='arriba' if so == 0 else 'abajo', componente=e.get('tag') or e.get('tag_base') or '',
                         _so=so, _po=po, _x=(comp.get(e['tag_base']) or {}).get('x') or po[0])
                if otra_lat:
                    pd = punto(eo, num, L)
                    sd, _ = lado_de(pd, L)
                    l.update(destino=to, marca_d=[round(pd[0], 2), round(pd[1], 2), pd[2]], exacto_d=pd[3], otra='misma bandeja',
                             _sd=sd, _pd=pd)
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
    # de arriba de izquierda a derecha y despues la de abajo; aparato por aparato; el de mas afuera del riel primero)
    out_lat = []
    for L in laterales:
        ls = tramos_lat[L['i']]
        if not ls:
            continue
        for l in ls:
            eje = L['rieles'][l['riel'] - 1] if L['rieles'] else l['_po'][1]
            l['_orden'] = (l['riel'], l['_so'], round(l['_x'], 1), -round(abs(l['_po'][1] - eje) / 3.0), l['_po'][0], natk(l['origen']))
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
        from ruteo import route_line, length
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
            if ruta:
                l['ruta'] = ruta
                if lay.get('escala'):
                    l['largo_mm'] = int(round(length(ruta) * lay['escala'] / 10.0) * 10)
        pasos = []
        for l in ls:
            cur = pasos[-1] if pasos else None
            if cur is None or (cur['riel'], cur['lado']) != (l['riel'], l['lado']) or (
                    len(cur['lineas']) >= MAX_LINEAS and l['componente'] != cur['lineas'][-1]['componente']):
                cur = dict(riel=l['riel'], lado=l['lado'], lineas=[]); pasos.append(cur)
            cur['lineas'].append(l)
        for n, p in enumerate(pasos, 1):
            comps = list(dict.fromkeys(l['componente'] for l in p['lineas']))
            p.update(n=n, titulo=f"Riel {p['riel']} · parte de {p['lado']} · " + ', '.join(comps))
            for l in p['lineas']:
                for k in [k for k in l if k.startswith('_')]:
                    l.pop(k)
        x0, y0, x1, y1 = L['region']
        out_lat.append(dict(nombre=L['nombre'], lado=L['lado'], vista=L['i'], region=[round(v, 2) for v in L['region']], pag=lay.get('pag'),
                            escala=lay.get('escala'), ductos=L['ductos'], rieles=L['rieles'], pasos=pasos,
                            n=sum(len(p['lineas']) for p in pasos), sin_canaletas=not L['ductos'],
                            exactos=sum(1 for p in pasos for l in p['lineas'] if l.get('exacto_o'))))
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
