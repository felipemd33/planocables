# -*- coding: utf-8 -*-
"""Mapeo automatico de los bornes en las BANDEJAS LATERALES (estacion E8, etapa E8-5 del 2026-10-08).

Es el mismo motor de la bandeja (motor.py + catalogo.json), corrido por cada lateral con su PLACA como region y sus
rieles. Lo usa estacion8.mapear_bornes; el resultado va a claves aparte del layout (lay['bornes_e8'], ...) y NUNCA
renombra textos: el instructivo de E6 y sus pendientes no cambian. El calculo se guarda en <trabajo>/bornes_e8_auto.json
(una entrada por lateral, con su firma), aparte del bornes_auto.json de la bandeja.

Rieles de una lateral (ademas de los de la capa del riel, que el motor lee solo):
  - si la capa del riel no da ningun tramo en la placa, los tramos dibujados como rectangulo en CUALQUIER capa con el
    perfil del riel de la bandeja (topo.rieles_geometria; la lateral derecha del TPT tiene el riel 1 en la capa '0');
  - los ejes que da el lector del topografico para la vista (rieles_e8: el riel TAPADO por los aparatos, una fila de
    etiquetas entre dos canaletas) que no tienen ningun tramo: un riel del perfil de la bandeja a lo largo de las
    etiquetas apoyadas en ese eje (el motor lo estira por las etiquetas y los aparatos, como a los demas)."""
import os
import json
import time

from .motor import Motor, VERSION, materiales_de_lineas
from . import CATALOGO, firma as firma_bandeja, _sha_archivo

VERSION_LATERAL = 1        # si cambia la regla de los rieles de las laterales, se recalcula el cache
APOYO_H = 0.6              # etiqueta apoyada en el eje de un riel: |dy| <= 0.6 perfiles (como topo.APOYO_H)
CUBIERTO_H = 0.6           # un eje ya tiene tramo si un riel leido esta a menos de 0.6 perfiles


class MotorLateral(Motor):
    """el motor de la bandeja con los rieles de la vista lateral (ver arriba). 'ejes': ejes y de los rieles de la vista
    (pt); 'H': perfil del riel de la bandeja (pt)."""

    def __init__(self, pdf, usos, catalogo, materiales, ejes=(), H=None, ductos=()):
        self._ejes = [float(e) for e in (ejes or [])]
        self._H = float(H) if H else None
        self._ductos = [d for d in (ductos or []) if isinstance(d, dict) and d.get('b') and d.get('h')]
        self.origen_rieles = []          # ('geometria' | 'etiquetas', yc) de los rieles agregados para la lateral
        super().__init__(pdf, usos, catalogo, materiales)

    def _rieles_otras_capas(self, trazos):
        out = super()._rieles_otras_capas(trazos)
        if not self._H:
            return out
        x0r, y0r, x1r, y1r = self.region
        ya = list(self.rieles) + out
        if not ya:
            # 1) sin capa de riel en la placa: rectangulos con el perfil del riel de la bandeja en cualquier capa
            try:
                from topo import rieles_geometria
                ref = [dict(x0=0.0, x1=10 * self._H, y0=-1e6, y1=-1e6 + self._H, H=self._H, eje=-1e6 + self._H / 2)]  # (solo el perfil)
                for g in rieles_geometria(trazos, ref):
                    if not (x0r - 5 <= g['x0'] and g['x1'] <= x1r + 5 and y0r <= g['eje'] <= y1r):
                        continue
                    if any(g['x0'] < r['x1'] and r['x0'] < g['x1'] and abs(g['eje'] - r['yc']) < (r['y1'] - r['y0']) / 2 for r in ya):
                        continue
                    d = dict(x0=g['x0'], x1=g['x1'], y0=g['y0'], y1=g['y1'], yc=g['eje'])
                    out.append(d)
                    ya.append(d)
                    self.origen_rieles.append(('geometria', round(g['eje'], 1)))
            except ImportError:
                pass
        # 2) ejes de la vista sin ningun tramo (riel tapado por los aparatos): a lo largo de sus etiquetas apoyadas
        for e in self._ejes:
            if not (y0r <= e <= y1r) or any(abs(r['yc'] - e) < CUBIERTO_H * self._H for r in ya):
                continue
            xs = []
            for c in (self.usos.get('componentes') or {}).values():
                p = self.posicion_etiqueta(c)
                if p and abs(p[1] - e) <= APOYO_H * self._H and x0r <= p[0] <= x1r:
                    xs.append(p[0])
            if not xs:
                continue
            x0, x1 = min(xs), max(xs)
            # el riel corre a lo ancho de las canaletas horizontales que lo encierran (la de arriba y la de abajo): asi
            # el ultimo aparato del riel (a la derecha de su etiqueta) queda adentro
            arriba = [d for d in self._ductos if d['b'][1] > e and d['b'][0] < x1 and x0 < d['b'][2]]
            abajo = [d for d in self._ductos if d['b'][3] < e and d['b'][0] < x1 and x0 < d['b'][2]]
            cerca = [min(g, key=lambda d: abs((d['b'][1] + d['b'][3]) / 2 - e)) for g in (arriba, abajo) if g]
            if cerca:
                x0 = min(x0, min(d['b'][0] for d in cerca))
                x1 = max(x1, max(d['b'][2] for d in cerca))
            d = dict(x0=x0, x1=x1, y0=e - self._H / 2, y1=e + self._H / 2, yc=e)
            out.append(d)
            ya.append(d)
            self.origen_rieles.append(('etiquetas', round(e, 1)))
        return out


def firma(topo_pdf, usos, materiales, ejes, H, ductos=()):
    """firma del calculo de una lateral: la de la bandeja (contenido del topografico, catalogo, codigo del motor, usos,
    region = la placa, materiales) + este archivo, su version, los rieles y las canaletas de la vista"""
    f = firma_bandeja(topo_pdf, usos, materiales)
    f.update(lateral=VERSION_LATERAL, codigo_lateral=_sha_archivo(os.path.abspath(__file__)),
             ejes=[round(float(e), 1) for e in (ejes or [])], H=round(float(H), 2) if H else None,
             ductos=[[round(float(v), 1) for v in d['b']] for d in (ductos or []) if isinstance(d, dict) and d.get('b')])
    return f


def leer_cache(path):
    try:
        with open(path, encoding='utf-8') as f:
            c = json.load(f)
        return c if isinstance(c, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def escribir_cache(path, data):
    try:
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass


def mapear_lateral(topo_pdf, usos, materiales=None, ejes=(), H=None, ductos=(), cache=None, clave=None, catalogo_path=None):
    """Ubica los bornes de 'usos' (los de una lateral, region = su placa) con el motor y los rieles (y las canaletas,
    para el largo del riel tapado) de la vista.
    'cache': {clave: {firma, salida}} (bornes_e8_auto.json leido; se actualiza la entrada de 'clave').
    -> salida del motor ({puntos, modelos, avisos, segundos, ...} + de_cache, rieles) o, si falla, {error, avisos,
    puntos: []}: la lateral queda con el punto aproximado"""
    catalogo_path = catalogo_path or CATALOGO
    t0 = time.time()
    fm = None
    try:
        fm = firma(topo_pdf, usos, materiales, ejes, H, ductos)
        e = (cache or {}).get(clave) if cache is not None and clave else None
        if isinstance(e, dict) and e.get('firma') == fm and isinstance(e.get('salida'), dict):
            sal = dict(e['salida'], de_cache=True, segundos_cache=round(time.time() - t0, 2))
            return sal
    except Exception:                                                      # noqa: BLE001
        pass
    try:
        if not usos or not usos.get('componentes'):
            return dict(error=None, avisos=[], puntos=[], modelos={}, segundos=0.0, version=VERSION, de_cache=False, rieles=[])
        with open(catalogo_path, encoding='utf-8') as f:
            catalogo = json.load(f)
        m = MotorLateral(topo_pdf, usos, catalogo, materiales_de_lineas(materiales) if materiales else {}, ejes=ejes, H=H, ductos=ductos)
        sal = m.mapear()
        sal['rieles'] = [dict(x0=round(r['x0'], 1), x1=round(r['x1'], 1), yc=round(r['yc'], 1)) for r in m.rieles]
        sal['rieles_agregados'] = [dict(origen=o, yc=y) for o, y in m.origen_rieles]
    except Exception as ex:                                                # noqa: BLE001
        import traceback
        return dict(error=f'{type(ex).__name__}: {ex}', detalle=traceback.format_exc(), puntos=[], modelos={}, rieles=[],
                    avisos=[f'el mapeo automatico de bornes de la lateral fallo ({type(ex).__name__}: {ex}); queda el punto aproximado'],
                    segundos=round(time.time() - t0, 2), version=VERSION, de_cache=False)
    sal['de_cache'] = False
    if cache is not None and clave and fm:
        cache[clave] = dict(firma=fm, salida=sal)
    return sal
