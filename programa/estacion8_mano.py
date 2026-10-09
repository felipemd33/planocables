"""RUTEO A MANO POR GRUPOS de la estacion 8 (etapa E8-6, pedido del taller del 2026-10-08).

Hay cables de E8 que no se rutean solos: solenoides, la contactora (la bobina del contactor de la bomba), la bateria (por
separado los de 35 mm² y los de 4 / 6 mm²), el doorswitch, los pulsadores, las selectoras, las llaves seccionadoras y
los grupos de cables de cada placa. Su recorrido lo DIBUJA el taller a mano (clics sobre las vistas de E8) y hasta que
se dibuja el visor dice «falta dibujar el recorrido» (no se inventa una ruta). Los demas cables de E8 siguen como antes.

- GRUPOS AUTOMATICOS (clasificar): con la tabla editable programa/web/e8_grupos.json (categorias en orden; un cable cae
  en la primera que le corresponde y en una sola). Criterios generales: seccion, pines (A1 / A2 de la bobina), el texto
  del aparato (renglon de la lista de materiales del funcional + el material de bornes/aparamenta.json que nombra) y, si
  el aparato no tiene texto, las letras de su tag (en la tabla, nunca en el codigo). La contactora se reconoce por sus
  cables: un aparato con un cable de 35 mm² (sus contactos de potencia) y otro chico (la bobina).
- CORRECCIONES DEL TALLER: mover un cable de grupo (o sacarlo: vuelve al ruteo automatico) y armar grupos nuevos de placa.
- RECORRIDO: por grupo, una secuencia de TRAMOS, cada uno en una vista de E8 (una bandeja lateral por su clave_vista,
  'PUERTA' o 'FONDO' = la bandeja principal y la zona del fondo), con los puntos en pt del topografico.
- SE GUARDA POR PRODUCTO: codigo de producto + numero y revision del topografico (ins['producto']): se dibuja una vez y
  sirve para todos los trabajos del mismo producto con el mismo topografico; corregirlo en uno lo cambia para los demas
  (la web avisa). Con otro topografico no se reusa. Archivo: programa/recorridos_e8.json (PLANOCABLES_RECORRIDOS_E8
  cambia la ruta: pruebas), escritura atomica con respaldo (.bak) y numero de version (dos trabajos guardando a la vez:
  el segundo recibe un conflicto y recarga). Si el producto no esta confirmado o falta el topografico (numero y revision),
  se guarda en el trabajo (ins['estacion8']['mano_trabajo']) con un aviso, y al confirmarlo pasa al producto.
- NO cambia E6, las estaciones ni la lista WPC: en las lineas de E8 solo se agrega 'grupo_mano' (la ruta automatica
  'ruta' / 'largo_mm' de las laterales queda: la usa la WPC; el visor no la dibuja para un cable con grupo).

Estructura en ins['estacion8']['ruteo_mano'] (la arma estacion8.build; aplicar() le suma lo del taller):
  {version, categorias: [{id, nombre, nota}], vistas: [{clave, nombre, tipo: 'lateral' | 'puerta' | 'fondo', i}],
   auto: {clave_cable: id_grupo}, auto_info: {id_grupo: {categoria, aparato}},
   cables: {clave_cable: {num, cable, color, secc, a, b, aparatos, puntos: {clave_vista: [[x, y], ...]}}},
   -- de aplicar(): grupos: [{id, nombre, categoria, aparato, auto, cables: [clave...], n, tramos, dibujado}],
   miembro: {clave_cable: id_grupo}, manual (lo guardado, normalizado), clave_producto, por_producto, aviso,
   version_almacen, editado: {trabajo, archivo, fecha}, avisos}"""
import collections
import copy
import datetime
import json
import math
import os
import re
import shutil
import threading

AQUI = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(AQUI, 'web', 'e8_grupos.json')
VERSION = 1
VERSION_ALMACEN = 1       # formato de programa/recorridos_e8.json ('version' de arriba; cada producto lleva la suya)
VISTA_PUERTA, VISTA_FONDO = 'PUERTA', 'FONDO'
MAX_PUNTOS = 400          # por tramo
MAX_TRAMOS = 60           # por grupo
LOCK = threading.Lock()   # escritura del archivo de recorridos (dos pedidos a la vez desde la web)


def almacen():
    """archivo de los recorridos por producto (se lee en cada llamada: las pruebas cambian la variable de entorno)"""
    return os.environ.get('PLANOCABLES_RECORRIDOS_E8') or os.path.join(AQUI, 'recorridos_e8.json')


def _natk(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', str(s or ''))]


def _num(v):
    try:
        x = float(str(v).replace(',', '.'))
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ tabla de categorias (programa/web/e8_grupos.json)
def _rx(p):
    try:
        return re.compile(p) if isinstance(p, str) and p else None
    except re.error:
        return None


def leer_config(path=None):
    """la tabla de grupos, validada: {categorias: [{id, nombre, nota, aparato: {familias, texto_re, tag_re,
    potencia_seccion_min} | None, cable: {seccion_min, seccion_max, secciones}, pines, por_aparato, puerta}], directo: {...}}.
    Lo roto se descarta (una categoria sin id, una expresion invalida)"""
    try:
        with open(path or CONFIG, encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    cats = []
    for c in (d.get('categorias') if isinstance(d, dict) else None) or []:
        if not isinstance(c, dict) or not re.fullmatch(r'[a-z0-9_]{1,40}', str(c.get('id') or '')):
            continue
        a = c.get('aparato') if isinstance(c.get('aparato'), dict) else None
        cab = c.get('cable') if isinstance(c.get('cable'), dict) else {}
        cats.append(dict(
            id=c['id'], nombre=str(c.get('nombre') or c['id']), nota=str(c.get('nota') or ''),
            aparato=None if a is None else dict(familias=[str(x) for x in a.get('familias') or []], texto_re=_rx(a.get('texto_re')),
                                                tag_re=_rx(a.get('tag_re')), potencia=_num(a.get('potencia_seccion_min'))),
            cable=dict(min=_num(cab.get('seccion_min')), max=_num(cab.get('seccion_max')),
                       secciones=[x for x in (_num(v) for v in cab.get('secciones') or []) if x is not None]),
            pines=[str(p).strip().upper() for p in c.get('pines') or [] if str(p).strip()],
            por_aparato=bool(c.get('por_aparato')), puerta=c.get('puerta') is True))
    di = d.get('directo') if isinstance(d, dict) and isinstance(d.get('directo'), dict) else {}
    directo = dict(familias=[str(x) for x in di.get('familias') or []], tag_re=_rx(di.get('tag_re')),
                   distancia=_num(di.get('distancia_max_perfiles')) or 2.0)
    return dict(categorias=cats, directo=directo)


# ------------------------------------------------------------------ texto de cada aparato (lista de materiales + aparamenta)
_APARAMENTA = {}


def textos_aparamenta():
    """[(codigo de fabricante normalizado, 'texto | modelo | clase')] de bornes/aparamenta.json (los que tienen un codigo
    de 4 o mas letras y numeros, para no confundir codigos cortos)"""
    p = os.path.join(AQUI, 'bornes', 'aparamenta.json')
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return []
    if _APARAMENTA.get('mt') != mt:
        out = []
        try:
            with open(p, encoding='utf-8') as f:
                mats = (json.load(f) or {}).get('materiales') or {}
        except (OSError, ValueError):
            mats = {}
        for v in mats.values():
            if not isinstance(v, dict):
                continue
            cod = re.sub(r'[^A-Z0-9]', '', str(v.get('codigo_fabricante') or '').upper())
            if len(cod) >= 4:
                out.append((cod, ' | '.join(str(v.get(k) or '') for k in ('texto', 'modelo', 'clase'))))
        _APARAMENTA.update(mt=mt, lista=out)
    return _APARAMENTA.get('lista') or []


def texto_aparato(bom_txt):
    """el renglon de la lista de materiales de un aparato con el texto del material de aparamenta.json cuyo codigo de
    fabricante nombra (HL-5200 -> 'final de carrera de puerta'); None sin renglon"""
    if not bom_txt:
        return None
    n = re.sub(r'[^A-Z0-9]', '', str(bom_txt).upper())
    extra = [t for cod, t in textos_aparamenta() if cod in n]
    return ' | '.join([str(bom_txt)] + extra)


# ------------------------------------------------------------------ grupos automaticos
def _pin(p):
    return str(p or '').strip().upper()


def es_bornera(tag):
    """bornera: letra X tras el prefijo numerico (como convenciones.is_terminal_block)"""
    return bool(re.match(r'^(\d{2})?X', str(tag or '')))


def _cumple(A, tag, txt, fam):
    """el aparato (tag, su texto y su familia) cumple el criterio 'aparato' A de una categoria: con texto (lista de
    materiales) manda la familia si la categoria las nombra ('Cargador de baterias' es un cargador, no una bateria) y si
    no el texto; sin texto, las letras del tag"""
    if txt:
        if fam and A['familias']:
            return fam in A['familias']
        return bool(A['texto_re'] and A['texto_re'].search(txt))
    return bool(A['tag_re'] and A['tag_re'].search(tag))


def aparato_de_puerta(tag, info_de, cfg=None):
    """el aparato es de la PUERTA segun la tabla: cumple el aparato de una categoria con 'puerta': true (pulsadores,
    selectoras, doorswitch, seccionadoras, placa), por su texto o, sin texto, por las letras del tag. Solo lo usa la capa
    «Pasan hacia la puerta» de E8 para separar los cables que van de verdad a la puerta de los que tienen el aparato sin
    dibujar en el topografico (no cambia el ruteo, los grupos, E6 ni la WPC). Nunca levanta excepciones."""
    if not tag or es_bornera(tag):
        return False
    try:
        cfg = cfg or leer_config()
        txt, fam = info_de(tag) or (None, None)
    except Exception:                                                      # noqa: BLE001
        return False
    if fam == 'bornera':
        return False
    return any(c.get('puerta') and c['aparato'] is not None and _cumple(c['aparato'], tag, txt, fam) for c in cfg['categorias'])


def clasificar(tramos, info_de, cfg=None):
    """grupo automatico de cada cable de E8. tramos: [{clave, sec (mm² o None), puntas: [(tag, pin), (tag, pin)]}];
    info_de(tag) -> (texto del aparato o None, familia o None). -> ({clave: id_grupo}, {id_grupo: {categoria, aparato}})
    El cable cae en la PRIMERA categoria de la tabla que le corresponde (ver e8_grupos.json, _nota_como)."""
    cfg = cfg or leer_config()
    secs, pines = collections.defaultdict(list), collections.defaultdict(set)
    for t in tramos:
        for tag, pin in t['puntas']:
            if tag:
                if t.get('sec') is not None:
                    secs[tag].append(t['sec'])
                pines[tag].add(_pin(pin))
    info = {}

    def inf(tag):
        if tag not in info:
            try:
                info[tag] = info_de(tag) or (None, None)
            except Exception:                                              # noqa: BLE001
                info[tag] = (None, None)
        return info[tag]

    def cable_ok(cat, s):
        c = cat['cable']
        if c['min'] is None and c['max'] is None and not c['secciones']:
            return True
        if s is None:
            return False
        return (c['min'] is None or s >= c['min'] - 1e-6) and (c['max'] is None or s <= c['max'] + 1e-6) \
            and (not c['secciones'] or any(abs(s - x) < 1e-6 for x in c['secciones']))

    def aparato_ok(cat, tag):
        A = cat['aparato']
        if A is None:
            return True
        if not tag or es_bornera(tag):         # (una bornera nunca es el aparato de un grupo: lo es la otra punta)
            return False
        txt, fam = inf(tag)
        if fam == 'bornera':
            return False
        if A['potencia'] is not None:          # contactor: un cable de potencia y otro chico (la bobina) en el mismo aparato
            chico = cat['cable']['max']
            if any(s >= A['potencia'] - 1e-6 for s in secs[tag]) and (chico is None or any(s <= chico + 1e-6 for s in secs[tag])):
                return True
        return _cumple(A, tag, txt, fam)

    auto, ainfo = {}, {}
    for t in tramos:
        for cat in cfg['categorias']:
            if not cable_ok(cat, t.get('sec')):
                continue
            tag = None
            if cat['aparato'] is None:
                ok = True
            else:
                ok = False
                for tg, pin in t['puntas']:
                    if not aparato_ok(cat, tg):
                        continue
                    # pines (A1 / A2): si el aparato tiene cables en esos pines, solo esos
                    if cat['pines'] and pines[tg] & set(cat['pines']) and _pin(pin) not in cat['pines']:
                        continue
                    ok, tag = True, tg
                    break
            if not ok:
                continue
            gid = f"{cat['id']}:{tag}" if cat['por_aparato'] and tag else cat['id']
            auto[t['clave']] = gid
            ainfo.setdefault(gid, dict(categoria=cat['id'], aparato=tag if cat['por_aparato'] else None))
            break
    return auto, ainfo


# ------------------------------------------------------------------ lo que dibuja y corrige el taller (manual)
def manual_vacio():
    return {'grupos': {}, 'nuevos': [], 'mover': {}}


def _texto(v, n=80):
    return str(v).strip()[:n] if isinstance(v, (str, int, float)) and str(v).strip() else ''


def normalizar_manual(m, categorias=None):
    """lo que guarda el taller, validado: {grupos: {id: {tramos: [{vista, puntos: [[x, y], ...]}], nombre?}}, nuevos:
    [{id, nombre, categoria, aparato}], mover: {clave_cable: id_grupo | '' (sin grupo: ruteo automatico)}}.
    -> (manual, errores). Un tramo sin puntos se descarta; los numeros se redondean a 0,01 pt."""
    out, err = manual_vacio(), []
    if m is None:
        return out, err
    if not isinstance(m, dict):
        return out, ['el ruteo a mano tiene que ser un objeto']
    cats = set(categorias or [])
    gs = m.get('grupos') if isinstance(m.get('grupos'), dict) else {}
    for gid, g in gs.items():
        gid = _texto(gid, 120)
        if not gid or not isinstance(g, dict):
            continue
        tramos = []
        for t in (g.get('tramos') if isinstance(g.get('tramos'), list) else [])[:MAX_TRAMOS]:
            if not isinstance(t, dict) or not _texto(t.get('vista'), 200):
                continue
            pts = []
            for p in (t.get('puntos') if isinstance(t.get('puntos'), list) else [])[:MAX_PUNTOS]:
                if isinstance(p, (list, tuple)) and len(p) >= 2 and _num(p[0]) is not None and _num(p[1]) is not None:
                    pts.append([round(_num(p[0]), 2), round(_num(p[1]), 2)])
            if pts:
                tramos.append({'vista': _texto(t['vista'], 200), 'puntos': pts})
        d = {'tramos': tramos}
        if _texto(g.get('nombre')):
            d['nombre'] = _texto(g.get('nombre'))
        if tramos or d.get('nombre'):
            out['grupos'][gid] = d
    for x in (m.get('nuevos') if isinstance(m.get('nuevos'), list) else []):
        if not isinstance(x, dict) or not re.fullmatch(r'nuevo:[A-Za-z0-9_-]{1,40}', str(x.get('id') or '')):
            if isinstance(x, dict):
                err.append(f"grupo nuevo con un id inválido: {x.get('id')!r}")
            continue
        cat = _texto(x.get('categoria'), 40) or 'placa'
        if cats and cat not in cats:
            err.append(f"grupo nuevo {x['id']}: categoría desconocida {cat!r}")
            continue
        if any(y['id'] == x['id'] for y in out['nuevos']):
            continue
        out['nuevos'].append({'id': x['id'], 'nombre': _texto(x.get('nombre')) or 'Grupo nuevo', 'categoria': cat,
                              'aparato': _texto(x.get('aparato'), 40) or None})
    mv = m.get('mover') if isinstance(m.get('mover'), dict) else {}
    for k, v in mv.items():
        k = _texto(k, 300)
        if k and isinstance(v, str) and len(v) <= 120:
            out['mover'][k] = v
    return out, err


# ------------------------------------------------------------------ almacen por producto
def clave_producto(prod):
    """('<codigo>|<numero del topografico>|rev<revision>', None) o (None, motivo): solo con el producto confirmado y el
    numero y la revision del topografico"""
    p = prod if isinstance(prod, dict) else {}
    if not p.get('codigo') or not p.get('confirmado'):
        return None, 'el producto del trabajo no está confirmado'
    t = p.get('topografico') if isinstance(p.get('topografico'), dict) else {}
    num, rev = str(t.get('numero') or '').strip(), re.sub(r'\s+', '', str(t.get('revision') or '')).upper()
    rev = re.sub(r'^0+(?=\d)', '', rev)
    if not num or not rev:
        return None, 'falta el número o la revisión del topográfico'
    return f"{str(p['codigo']).strip()}|{num}|rev{rev}", None


def leer_almacen(path=None):
    """{'_nota', 'version' (formato), 'productos': {clave: entrada}} ({} si no esta o esta roto; el de git viene sin
    productos)"""
    try:
        with open(path or almacen(), encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def entrada(clave, path=None):
    """lo guardado para ese producto y topografico: {version, manual, editado, trabajos, producto, topografico} o None"""
    if not clave:
        return None
    e = ((leer_almacen(path).get('productos') or {}).get(clave))
    if not isinstance(e, dict):
        return None
    man, _ = normalizar_manual(e.get('manual'))
    return dict(e, manual=man, version=int(e.get('version') or 0))


NOTA_ALMACEN = ('Ruteo a mano de la estación 8, por producto (código de producto | número del topográfico | rev revisión): '
                'los recorridos dibujados por grupo y los grupos corregidos por el taller (estacion8_mano.py). Lo escribe la web. '
                "'version' (arriba) = formato del archivo; la 'version' de cada producto cuenta las veces que se guardó (si otro "
                'trabajo lo cambió, la web avisa y recarga).')


def almacen_vacio():
    """el archivo sin ningun producto (el que esta en git: lo que dibuja el taller se ve como cambios del archivo)"""
    return {'_nota': NOTA_ALMACEN, 'version': VERSION_ALMACEN, 'productos': {}}


def guardar(clave, manual, trabajo=None, archivo=None, version_base=None, path=None, prod=None):
    """guarda lo del taller para el producto 'clave' (escritura atomica, con respaldo .bak del archivo anterior).
    version_base: la version que tenia la web cuando lo cambio; si en el archivo hay otra (lo cambio otro trabajo), no
    guarda. -> (entrada nueva, None) o (entrada actual, 'conflicto')"""
    path = path or almacen()
    with LOCK:
        d = leer_almacen(path)
        prods = d.get('productos') if isinstance(d.get('productos'), dict) else {}
        vieja = prods.get(clave) if isinstance(prods.get(clave), dict) else None
        v0 = int((vieja or {}).get('version') or 0)
        if version_base is not None and int(version_base) != v0:
            man, _ = normalizar_manual((vieja or {}).get('manual'))
            return dict(vieja or {}, manual=man, version=v0), 'conflicto'
        p = prod if isinstance(prod, dict) else {}
        top = p.get('topografico') if isinstance(p.get('topografico'), dict) else {}
        trabajos = [t for t in ((vieja or {}).get('trabajos') or []) if isinstance(t, str) and t != trabajo] + ([trabajo] if trabajo else [])
        e = dict(producto=clave.split('|')[0], nombre=p.get('nombre') or (vieja or {}).get('nombre'),
                 topografico=dict(numero=top.get('numero') or clave.split('|')[1], revision=top.get('revision') or clave.split('|')[2][3:]),
                 version=v0 + 1, editado=dict(trabajo=trabajo, archivo=archivo, fecha=datetime.datetime.now().strftime('%d/%m/%Y %H:%M')),
                 trabajos=trabajos[-50:], manual=manual)
        prods = dict(prods)
        prods[clave] = e
        nuevo = dict(almacen_vacio(), productos={k: prods[k] for k in sorted(prods)})
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if os.path.exists(path):
            try:
                shutil.copyfile(path, path + '.bak')
            except OSError:
                pass
        with open(path + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(nuevo, f, ensure_ascii=False, indent=1)
            f.write('\n')
        os.replace(path + '.tmp', path)
        return e, None


# ------------------------------------------------------------------ grupos efectivos (automaticos + lo del taller)
def _orden_grupo(R):
    """los automaticos primero, por categoria (en el orden de la tabla) y aparato; en cada categoria, un grupo sin aparato
    (un grupo nuevo de placa de un trabajo sin placas) va despues de los que lo tienen"""
    pos = {c['id']: i for i, c in enumerate(R.get('categorias') or [])}

    def k(g):
        return (0 if g.get('auto') else 1, pos.get(g.get('categoria'), 99), 0 if g.get('aparato') else 1,
                _natk(g.get('aparato') or ''), _natk(g['id']))
    return k


def aplicar(R, manual=None, meta=None):
    """grupos efectivos en R (= e8['ruteo_mano']): los automaticos con lo que corrigio el taller (mover, nuevos) y su
    recorrido dibujado (solo los tramos de vistas que tiene este trabajo). -> {clave_cable: id_grupo} (miembro)"""
    if not isinstance(R, dict):
        return {}
    cats = {c['id']: c for c in R.get('categorias') or []}
    man, err = normalizar_manual(manual, cats)
    auto, ainfo, cables = R.get('auto') or {}, R.get('auto_info') or {}, R.get('cables') or {}
    vistas = {v['clave'] for v in R.get('vistas') or []}
    grupos = {}
    for gid, i in ainfo.items():
        c = cats.get(i.get('categoria')) or {}
        grupos[gid] = dict(id=gid, categoria=i.get('categoria'), aparato=i.get('aparato'), auto=True,
                           nombre=(c.get('nombre') or gid) + (f" {i['aparato']}" if i.get('aparato') else ''))
    for x in man['nuevos']:
        grupos.setdefault(x['id'], dict(id=x['id'], categoria=x['categoria'], aparato=x.get('aparato'), auto=False, nombre=x['nombre']))
    miembro = dict(auto)
    avisos = list(err)
    viejos = 0
    for k, gid in man['mover'].items():
        if k not in cables:
            viejos += 1
            continue
        if gid and gid not in grupos:
            avisos.append(f'el cable {cables[k].get("num")} estaba en un grupo que ya no existe ({gid}): queda en su grupo automático')
            continue
        if gid:
            miembro[k] = gid
        else:
            miembro.pop(k, None)
    if viejos:
        avisos.append(f'{viejos} cable{"s" if viejos > 1 else ""} movido{"s" if viejos > 1 else ""} a mano ya no '
                      f'{"están" if viejos > 1 else "está"} en este trabajo (otro plano del mismo producto): se {"ignoran" if viejos > 1 else "ignora"}')
    sin_vista = 0
    lista = []
    for gid, g in grupos.items():
        mg = man['grupos'].get(gid) or {}
        tramos = [t for t in mg.get('tramos') or [] if t['vista'] in vistas]
        sin_vista += len(mg.get('tramos') or []) - len(tramos)
        cs = sorted((k for k, v in miembro.items() if v == gid), key=lambda k: (_natk(cables.get(k, {}).get('num')), k))
        lista.append(dict(g, nombre=mg.get('nombre') or g['nombre'], cables=cs, n=len(cs), tramos=tramos,
                          dibujado=any(len(t['puntos']) >= 2 for t in tramos)))
    if sin_vista:
        avisos.append(f'{sin_vista} tramo{"s" if sin_vista > 1 else ""} dibujado{"s" if sin_vista > 1 else ""} en una vista que este trabajo no tiene: no se muestra{"n" if sin_vista > 1 else ""}')
    lista.sort(key=_orden_grupo(R))
    R.update(grupos=lista, miembro=miembro, manual=man, avisos=avisos)
    R.update(meta or {})
    return miembro


def anotar(e8, miembro):
    """'grupo_mano' en cada linea de E8 (laterales, puerta, tablas de puerta y placa) de un cable con grupo de ruteo a
    mano; se saca de las demas"""
    def marcar(l):
        g = (miembro or {}).get(l.get('clave'))
        if g:
            l['grupo_mano'] = g
        else:
            l.pop('grupo_mano', None)
    for L in e8.get('laterales') or []:
        for p in L.get('pasos') or []:
            for l in p.get('lineas') or []:
                marcar(l)
    for p in (e8.get('puerta') or {}).get('pasos') or []:
        for l in p.get('lineas') or []:
            marcar(l)
    for g in e8.get('afuera') or []:
        for x in g.get('cables') or []:
            marcar(x)


def meta_de(clave, motivo, ent=None):
    """lo que acompaña a los grupos: de donde salen (producto o trabajo) y el aviso"""
    if clave:
        return dict(clave_producto=clave, por_producto=True, aviso=None, version_almacen=int((ent or {}).get('version') or 0),
                    editado=(ent or {}).get('editado'), trabajos=(ent or {}).get('trabajos') or [])
    return dict(clave_producto=None, por_producto=False, version_almacen=0, editado=None, trabajos=[],
                aviso=f'El ruteo a mano se guarda en este trabajo hasta que se confirme el producto ({motivo}); al confirmarlo pasa al producto')


def cargar_y_aplicar(e8, prod, local=None, trabajo=None, archivo=None):
    """al regenerar (web.gen_instructivo): los grupos de e8['ruteo_mano'] con lo del taller. Con el producto confirmado,
    lo del producto (si el trabajo tenia un ruteo propio de antes de confirmar y el producto todavia no tiene, pasa al
    producto); si no, lo del trabajo (e8['mano_trabajo']). Nunca levanta excepciones."""
    R = e8.get('ruteo_mano')
    if not isinstance(R, dict):
        return
    try:
        clave, motivo = clave_producto(prod)
        loc, _ = normalizar_manual(local) if local else (None, None)
        if clave:
            ent = entrada(clave)
            extra = []
            if ent is None and loc and (loc['grupos'] or loc['nuevos'] or loc['mover']):
                ent, _ = guardar(clave, loc, trabajo=trabajo, archivo=archivo, prod=prod)
                extra.append('el ruteo a mano que estaba guardado en este trabajo pasó al producto')
            elif loc and (loc['grupos'] or loc['nuevos'] or loc['mover']):
                extra.append('este trabajo tenía un ruteo a mano propio (de antes de confirmar el producto) que no se usa: el producto ya tiene uno')
            aplicar(R, (ent or {}).get('manual'), meta_de(clave, None, ent))
            R['avisos'] = extra + R['avisos']
        else:
            aplicar(R, loc, meta_de(None, motivo))
            if loc:
                e8['mano_trabajo'] = loc
        anotar(e8, R.get('miembro'))
    except Exception as ex:                                                # noqa: BLE001
        R.setdefault('avisos', []).append(f'no se pudo cargar el ruteo a mano ({type(ex).__name__}: {ex})')
        try:
            aplicar(R, None, meta_de(None, 'error'))
            anotar(e8, R.get('miembro'))
        except Exception:                                                  # noqa: BLE001
            pass


def resumen(R):
    """'N grupos de ruteo a mano (M sin dibujar)' para los avisos"""
    gs = [g for g in (R or {}).get('grupos') or [] if g.get('n')]
    falta = sum(1 for g in gs if not g.get('dibujado'))
    return gs, falta


def copia(R):
    return copy.deepcopy(R)
