# -*- coding: utf-8 -*-
"""Mapeo automatico de los bornes en el topografico de la bandeja (ver LEEME.md).

El programa (web.py, gen_instructivo) lo usa asi:
    mapeo = aplicar_al_layout(res, lay, dir_trabajo, topo_pdf, usuario=bornes_usuario)
que hace:
    manual, ren_m = leer_manuales(dir_trabajo)                   # bornes.json / correcciones.json: mandan
    usos = instructivo.usos_bandeja(res, lay, topo_pdf)          # que bornes usa cada cable, segun el funcional
    mats = instructivo.materiales_funcional(res)                 # lista de materiales del funcional (o None)
    sal = mapear_trabajo(topo_pdf, usos, mats, cache=<trabajo>/bornes_auto.json)   # (no se corre si todos los
                                                                 #  usos ya tienen punto manual)
    auto = puntos_automaticos(sal)                               # puntos de confianza alta y media
    componer_bornes(lay, auto, manual, ren_m, usuario)           # los manuales y los del visor mandan
"""
import os
import json
import time
import hashlib

from .motor import Motor, VERSION, materiales_de_lineas, leer_materiales  # noqa: F401

AQUI = os.path.dirname(os.path.abspath(__file__))
CATALOGO = os.path.join(AQUI, 'catalogo.json')
CODIGO = [os.path.join(AQUI, 'motor.py'), os.path.join(AQUI, 'primitivas.py')]   # el codigo que calcula los puntos


def _sha(b):
    return hashlib.sha1(b).hexdigest()[:16]


def _sha_archivo(path):
    """sha1 del CONTENIDO del archivo (None si no se puede leer). Un PDF de unos MB se lee en milisegundos."""
    try:
        h = hashlib.sha1()
        with open(path, 'rb') as f:
            for bloque in iter(lambda: f.read(1 << 20), b''):
                h.update(bloque)
        return h.hexdigest()[:16]
    except OSError:
        return None


def firma(topo_pdf, usos, materiales, catalogo_path=CATALOGO):
    """Firma del calculo: si no cambia nada de esto, el resultado guardado en bornes_auto.json sirve.
    Entra el CONTENIDO del topografico (no su fecha), el catalogo, el codigo del motor (motor.py, primitivas.py) y
    su VERSION, los usos (componentes de la bandeja y sus bornes) y la lista de materiales."""
    u = {k: v for k, v in (usos or {}).items() if k != 'topografico'}       # la ruta del archivo no importa
    return dict(version=VERSION, catalogo=_sha_archivo(catalogo_path), topografico=_sha_archivo(topo_pdf),
                codigo={os.path.basename(p): _sha_archivo(p) for p in CODIGO},
                pagina=u.get('pagina_pdf'), region=u.get('region_bandeja'), escala=u.get('escala_mm_por_pt'),
                usos=_sha(json.dumps(u, sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')),
                materiales=_sha('\n'.join(materiales or []).encode('utf-8')) if materiales else None)


def mapear_trabajo(topo_pdf, usos, materiales=None, cache=None, catalogo_path=None, log=None):
    """Ubica cada borne de 'usos' en el topografico. 'materiales': renglones de la lista de materiales
    ('tag | descripcion | marca | modelo') o None. 'cache': ruta de bornes_auto.json (se reusa si la firma no cambio).
    Devuelve la salida del motor ({puntos, modelos, avisos, segundos, ...} + de_cache) o, si el motor entero falla,
    {error, avisos: [...], puntos: []}: el instructivo se arma igual, como sin mapeo."""
    catalogo_path = catalogo_path or CATALOGO
    t0 = time.time()
    fm = None
    try:
        fm = firma(topo_pdf, usos, materiales, catalogo_path)
        if cache and os.path.exists(cache):
            with open(cache, encoding='utf-8') as f:
                c = json.load(f)
            if c.get('firma') == fm and isinstance(c.get('salida'), dict):
                sal = c['salida']
                sal['de_cache'] = True
                sal['segundos_cache'] = round(time.time() - t0, 2)
                return sal
    except Exception:                                                      # noqa: BLE001
        pass                                                               # cache roto: se recalcula
    try:
        if not usos or not usos.get('componentes'):
            return dict(error=None, avisos=['no hay componentes en la bandeja para ubicar'], puntos=[], modelos={}, segundos=0.0,
                        version=VERSION, de_cache=False)
        with open(catalogo_path, encoding='utf-8') as f:
            catalogo = json.load(f)
        motor = Motor(topo_pdf, usos, catalogo, materiales_de_lineas(materiales) if materiales else {})
        sal = motor.mapear()
        sal['materiales'] = 'lista de materiales del funcional' if materiales else 'sin lista de materiales (modelo por la geometria)'
    except Exception as e:                                                 # noqa: BLE001
        import traceback
        return dict(error=f'{type(e).__name__}: {e}', detalle=traceback.format_exc(), puntos=[], modelos={},
                    avisos=[f'el mapeo automatico de bornes fallo ({type(e).__name__}: {e}); el instructivo se arma sin el'],
                    segundos=round(time.time() - t0, 2), version=VERSION, de_cache=False)
    sal['de_cache'] = False
    if cache and fm:
        try:
            tmp = cache + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(dict(firma=fm, salida=sal), f, ensure_ascii=False)
            os.replace(tmp, cache)
        except OSError:
            pass
    return sal


def puntos_automaticos(sal, confianzas=('alta', 'media')):
    """Puntos del mapeo que van al instructivo: [{texto (el del funcional), cable, texto_final (el que corresponde al
    bloque donde quedo el punto), x, y, r, confianza, como}]"""
    out = []
    for p in (sal or {}).get('puntos') or []:
        if p.get('confianza') not in confianzas or not p.get('cables'):
            continue
        out.append(dict(texto=p['texto'], cable=str(p['cables'][0]), texto_final=p.get('texto_ubicado') or p['texto'],
                        x=float(p['x']), y=float(p['y']), r=p.get('r'), confianza=p['confianza'], como=p.get('como') or ''))
    return out


def _flip(t):
    """'X 1 ARRIBA' <-> 'X 1 ABAJO' (el visor guarda el punto con el texto que muestra, que puede llevar el lado fisico)"""
    t = str(t or '')
    for a, b in ((' ARRIBA', ' ABAJO'), (' ABAJO', ' ARRIBA')):
        if t.endswith(a):
            return t[:-len(a)] + b
    return t


def _ajustado(usuario, texto, num):
    """True si el usuario ajusto en el visor el punto de ese texto (o del mismo texto con el otro lado) para ese cable"""
    return any(k in usuario for t in (texto, _flip(texto)) for k in (f'{t}#{num}', t))


def componer_bornes(lay, auto, manual=None, renombrar_manual=None, usuario=None):
    """Arma lay['bornes'] y lay['renombrar'] con los puntos automaticos y los MANUALES (bornes.json del trabajo y
    correcciones.json), que mandan: un punto automatico se descarta si el mismo texto (con o sin '#cable', el del
    funcional o el corregido) ya tiene un punto manual, o si bornes.json corrige ese texto a otro bloque.
    'usuario' (bornes_usuario, puntos ajustados en el visor) manda sobre todo: si el usuario ajusto el texto del
    funcional, el mapeo no le cambia el texto (no se renombra) y su punto automatico no se usa.
    Ademas deja lay['bornes_conf'] (clave -> 'alta' | 'media', solo de los automaticos), lay['bornes_nota']
    (clave -> por que, de los 'media') y lay['renombrar_auto'] (los textos que corrigio el mapeo).
    Devuelve (usados, descartados_por_manual, renombres_automaticos)."""
    manual = dict(manual or {})
    ren_m = dict(renombrar_manual or {})
    usuario = usuario or {}
    bornes = dict(manual)
    ren = dict(ren_m)
    conf, nota, ren_auto = {}, {}, {}
    usados, descartados = 0, 0
    for a in auto or []:
        t0, n, t1 = a['texto'], a['cable'], a['texto_final']
        if {f'{t0}#{n}', t0, f'{t1}#{n}', t1} & manual.keys():
            descartados += 1
            continue
        k0 = f'{t0}#{n}'
        if k0 in ren_m and ren_m[k0] != t1:
            descartados += 1
            continue
        if t1 != t0 and _ajustado(usuario, t0, n) and not _ajustado(usuario, t1, n):
            continue                     # el usuario eligio el borne con el texto del funcional: manda el
        key = f'{t1}#{n}'
        bornes[key] = [round(a['x'], 2), round(a['y'], 2), a.get('r')]
        conf[key] = a['confianza']
        if a['confianza'] != 'alta':
            nota[key] = a.get('como') or ''
        if t1 != t0 and k0 not in ren_m:
            ren[k0] = t1
            ren_auto[k0] = t1
        usados += 1
    lay['bornes'] = bornes
    lay['renombrar'] = ren
    lay['bornes_conf'] = conf
    lay['bornes_nota'] = nota
    lay['renombrar_auto'] = ren_auto
    return usados, descartados, ren_auto


def resumen(sal, usados=0, descartados=0, ren_auto=None, avisos_previos=None):
    """lo que se guarda en el instructivo (ins['mapeo']) para mostrar en la pestana"""
    import re
    sal = sal or {}
    n = {c: sum(1 for p in sal.get('puntos') or [] if p.get('confianza') == c) for c in ('alta', 'media', 'baja')}
    # 'X: no figura en la lista de materiales; por la geometria es M' (uno por componente) -> un solo aviso
    avisos, geo = list(avisos_previos or []), []
    for a in sal.get('avisos') or []:
        m = re.match(r'^(\S+): no figura en la lista de materiales; por la geometria es (\S+)$', a)
        if m:
            geo.append(f'{m.group(1)} = {m.group(2)}')
        else:
            avisos.append(a)
    if geo:
        avisos.insert(len(avisos_previos or []), ('sin lista de materiales en el funcional' if not (sal.get('materiales') or '').startswith('lista') else
                                                  'no figuran en la lista de materiales') + f'; modelo por la geometria: {", ".join(geo)}')
    for p in sal.get('puntos') or []:
        if p.get('confianza') == 'baja':
            avisos.append(f"'{p.get('texto')}' #{','.join(p.get('cables') or [])}: no se pudo ubicar el borne; queda el punto aproximado")
    for k0, t1 in sorted((ren_auto or {}).items()):
        t0, _, num = k0.rpartition('#')
        avisos.append(f"cable {num}: el funcional dice '{t0}' pero el borne quedo en '{t1}' (se corrigio el texto; revisar)")
    avisos = list(dict.fromkeys(avisos))                                   # sin repetidos, en el mismo orden
    return dict(version=sal.get('version', VERSION), modelos=sal.get('modelos') or {}, avisos=avisos,
                segundos=sal.get('segundos'), de_cache=bool(sal.get('de_cache')), error=sal.get('error'),
                materiales=sal.get('materiales'), n_puntos=n, usados=usados, manuales=descartados,
                omitido=bool(sal.get('omitido')), modelos_faltantes=list(sal.get('modelos_faltantes') or []))


def leer_manuales(dir_trabajo, avisos=None):
    """Puntos y textos corregidos A MANO en el trabajo: bornes.json ({puntos: {texto: {xy, r}}, renombrar:
    {'texto#cable': texto}}, o el formato viejo {texto: [x, y]}) + los 'bornes' de correcciones.json.
    Un archivo ilegible (JSON invalido) se ignora: devuelve vacio y deja el aviso en 'avisos' ('bornes.json ilegible,
    se ignora'). Devuelve (puntos, renombrar)."""
    from instructivo import leer_bornes_manuales
    return leer_bornes_manuales(dir_trabajo, avisos)


def todos_con_punto_manual(usos, manual, ren_m, usuario=None):
    """True si TODOS los usos de la bandeja ya tienen punto manual (bornes.json / correcciones.json, o ajustado en el
    visor): el mapeo automatico no cambiaria nada y no hace falta correrlo."""
    usuario = usuario or {}
    hay = False
    for c in ((usos or {}).get('componentes') or {}).values():
        for u in c.get('usos') or []:
            hay = True
            t, n = str(u.get('texto') or ''), str(u.get('cable'))
            ts = [t] + ([ren_m[f'{t}#{n}']] if f'{t}#{n}' in ren_m else [])
            if any(k in manual for x in ts for k in (f'{x}#{n}', x)) or _ajustado(usuario, t, n):
                continue
            return False
    return hay


def mapeo_del_trabajo(res, lay, dir_trabajo, topo_pdf, cache=True, manual=None, ren_m=None, usuario=None):
    """Mapeo automatico de un trabajo: arma los usos desde el funcional (instructivo.usos_bandeja), la lista de
    materiales del funcional si la trae, y llama al motor (con cache en <trabajo>/bornes_auto.json).
    Si se pasan los puntos manuales y TODOS los usos ya tienen uno, el motor no se corre (salida con omitido=True).
    Nunca levanta excepciones: si algo falla devuelve {error, avisos, puntos: []}."""
    try:
        from instructivo import usos_bandeja, materiales_funcional
        usos = usos_bandeja(res, lay, topo_pdf)
        if manual is not None and todos_con_punto_manual(usos, manual, ren_m or {}, usuario):
            n = sum(len(c['usos']) for c in usos['componentes'].values())
            return dict(error=None, avisos=[], puntos=[], modelos={}, segundos=0.0, version=VERSION, de_cache=False,
                        omitido=True, n_usos=n)
        mats = materiales_funcional(res)
    except Exception as e:                                                 # noqa: BLE001
        return dict(error=f'{type(e).__name__}: {e}', puntos=[], modelos={}, segundos=0.0, version=VERSION, de_cache=False,
                    avisos=[f'no se pudieron armar los usos de la bandeja para el mapeo ({type(e).__name__}: {e})'])
    return mapear_trabajo(topo_pdf, usos, mats, cache=os.path.join(dir_trabajo, 'bornes_auto.json') if cache else None)


def aplicar_al_layout(res, lay, dir_trabajo, topo_pdf, cache=True, usuario=None):
    """Todo junto, como lo hace web.py: mapeo automatico + puntos manuales del trabajo (mandan) en lay['bornes'],
    lay['renombrar'], lay['bornes_conf'], lay['bornes_nota']. 'usuario': los puntos ajustados en el visor
    (bornes_usuario; si no se pasa, se toma lay['bornes_usuario']), que mandan sobre todo. Los conductores agregados
    a mano (lay['agregar']) tienen que estar cargados antes, para que el motor tambien los ubique.
    Devuelve el resumen para ins['mapeo']."""
    if usuario is None:
        usuario = lay.get('bornes_usuario') or {}
    avisos = []
    manual, ren_m = leer_manuales(dir_trabajo, avisos)
    sal = mapeo_del_trabajo(res, lay, dir_trabajo, topo_pdf, cache=cache, manual=manual, ren_m=ren_m, usuario=usuario)
    usados, descartados, ren_auto = componer_bornes(lay, puntos_automaticos(sal), manual, ren_m, usuario)
    if sal.get('omitido'):
        descartados = sal.get('n_usos') or 0          # todos los usos con punto manual
    return resumen(sal, usados, descartados, ren_auto, avisos)
