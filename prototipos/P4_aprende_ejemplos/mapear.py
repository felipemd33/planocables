"""Ubica cada borne del instructivo en el plano topografico usando la BASE DE EJEMPLOS (prototipo P4).

uso:
  python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json>
                   [--base base_bornes.json] [--lista lista_materiales.txt] [--modelos modelos_del_tablero.json]
                   [--loo] [--sin-memoria] [--control control.png]

Pasos, para cada componente del instructivo:
  1. MODELO: el de la lista de materiales (si falta, un tag parecido de la lista; si el dibujo no coincide con
     ese modelo, el modelo de la base cuyo dibujo se parece mas).
  2. RECUADRO: busca en el dibujo el recuadro (mascara blanca del bloque) de cada unidad del componente:
     'serie' = las piezas/modulos a la DERECHA de la etiqueta hasta la etiqueta siguiente del riel (regla del taller);
     'contiene' = el aparato que contiene la etiqueta.  Se reconoce por el tamano de los ejemplos de la base.
  3. TEXTO -> BORNE: la regla del modelo traduce el texto del instructivo a (unidad, borne).
  4. TRANSFERENCIA: elige los ejemplos mas parecidos del mismo modelo (descriptor del dibujo) que tengan ese borne y
     pasa su posicion normalizada (u, v de 0 a 1) al recuadro encontrado.
  5. AJUSTE FINO (snap): corre el punto al centro de la boca/tornillo dibujado mas cercano (circulo del mismo radio
     que en el ejemplo) o, si el borne no es un circulo, al lugar donde el dibujo coincide con el parche del ejemplo.

--loo  : dejando-un-tag-afuera.  Cada componente se mapea con una base SIN sus propios ejemplos (ni los ejemplos que
         otro tag dejo en sus piezas, ni sus reasignaciones de texto).  Mide como andaria en un tablero nuevo.
--sin-memoria : no usa las reasignaciones de texto aprendidas (errores del instructivo corregidos en tableros verificados).

No lee bornes_referencia.json ni tiene coordenadas de ningun tablero: todo sale del PDF, de los usos y de la base.
"""
import sys, os, re, json, math, time, argparse, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import nucleo as N

TOL_TAM = 0.04          # tolerancia de tamano del recuadro (4 %) para reconocer un modelo por sus ejemplos
TOL_TAM_PARIENTE = 0.25  # tolerancia cuando se usa un modelo pariente (el modelo no tiene ejemplos)
K_EJEMPLOS = 3          # cuantos ejemplos parecidos se promedian


# ----------------------------------------------------------------------------------------- utilidades
def dist_desc(a, b):
    """Distancia entre dos descriptores de recuadro (0 = identicos)."""
    lg = lambda p, q: abs(math.log(max(p, 1e-3) / max(q, 1e-3)))
    return (4 * lg(a['w_mm'], b['w_mm']) + 4 * lg(a['h_mm'], b['h_mm']) + 0.5 * lg(a['trazos'] + 1, b['trazos'] + 1)
            + 0.5 * lg(a['largo_pt2'] + 0.01, b['largo_pt2'] + 0.01) + 3 * abs(a['densidad'] - b['densidad'])
            + 2 * abs(a['verde'] - b['verde']) + 2 * abs(a['azul'] - b['azul']))


def tam_coincide(caja, tams_mm, esc, tol):
    return any(abs(caja['w'] * esc / w - 1) <= tol and abs(caja['h'] * esc / h - 1) <= tol for w, h in tams_mm)


def mediana(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None


def tags_parecidos(lista_tags, tags_usos):
    """tag del instructivo -> tag de la lista de materiales con el mismo prefijo (hoja + letras) cuando el del
    instructivo no figura en la lista y hay un solo candidato libre (ej. 13PS3 en el plano, 13PS2 en la lista)."""
    out = {}
    libres = [t for t in lista_tags if t not in tags_usos]
    for t in tags_usos:
        if t in lista_tags:
            continue
        m = re.match(r'^(\d+[A-Z]+)', t)
        if not m:
            continue
        c = [l for l in libres if re.match(r'^(\d+[A-Z]+)', l) and re.match(r'^(\d+[A-Z]+)', l).group(1) == m.group(1)]
        if len(c) == 1:
            out[t] = c[0]
    return out


def texto_de(modelo, comp, un, borne):
    """El texto del instructivo que corresponde a (componente, unidad, borne): para el 'renombrar' del programa."""
    t = modelo['regla']['tipo']
    if t == 'quattro':
        return f'{comp} {un}.{borne}'
    if t == 'doble_piso' and '_' in borne:
        lado, pos = borne.split('_')
        return f"{comp} {2 * un - 1 if pos == 'EXT' else 2 * un} {lado}"
    if t == 'dio':
        return f'{comp} {un} {borne}'
    if t == 'modulos':
        return f'{comp}{un} {borne}'
    return None


# ----------------------------------------------------------------------------------------- mapeador
class Mapeador:
    def __init__(self, pl, usos, base, lista=None, forzados=None, usar_memoria=True):
        self.pl, self.base = pl, base
        self.comps = usos['componentes']
        self.mods = base['modelos']
        self.esc = pl.escala
        self.usar_memoria = usar_memoria
        # modelo segun la lista de materiales (y tags parecidos)
        prior = N.modelos_de_lista(lista, base) if lista else {}
        todos = {}
        if lista and os.path.exists(lista):
            for linea in open(lista, encoding='utf-8', errors='replace'):
                c = linea.split('|')[0].strip()
                if re.match(r'^\d+[A-Z]+[A-Z0-9]*$', c):
                    todos[c] = 1
        self.nota_lista = {}
        for t, l in tags_parecidos(list(todos), list(self.comps)).items():
            if l in prior and t not in prior:
                prior[t] = prior[l]
                self.nota_lista[t] = f'la lista de materiales lo nombra {l}'
        if forzados:
            prior.update(forzados)
        self.prior = prior
        self._desc = {}

    # ---------------------------------------------------------------- ejemplos disponibles
    def ejemplos(self, clave, excl):
        return [e for e in self.mods[clave].get('ejemplos', []) if e['tag'] not in excl and e.get('componente') not in excl]

    def fuentes_de_ejemplos(self, clave, excl):
        """[(clave_ejemplos, ejemplos, nivel)]: 0 = el mismo modelo, 1 = mismo dibujo ('forma'), 2 = pariente de la
        misma familia que tiene bornes con el mismo nombre (fallback: tolerancia de tamano amplia)."""
        m = self.mods[clave]
        out = []
        e = self.ejemplos(clave, excl)
        if e:
            out.append((clave, e, 0))
        for k, mm in self.mods.items():
            if k != clave and mm.get('forma') == m.get('forma'):
                e = self.ejemplos(k, excl)
                if e:
                    out.append((k, e, 1))
        if not out:
            for k, mm in self.mods.items():
                if k != clave and mm.get('familia') == m.get('familia') and set(mm.get('bornes', [])) & set(m.get('bornes', [])):
                    e = self.ejemplos(k, excl)
                    if e:
                        out.append((k, e, 2))
        return out

    def modelo_por_texto(self, tag, prior):
        """Cuando ningun modelo con ejemplos coincide con el dibujo: el modelo (de la familia del de la lista, o de
        cualquiera si no hay lista) cuya regla entiende mas textos del instructivo.  Gana el de la lista si empata."""
        usos = self.comps[tag]['usos']
        if prior in self.mods:
            sirve = lambda m: m.get('familia') == self.mods[prior].get('familia')
        elif self.comps[tag].get('es_bornera'):
            sirve = lambda m: m.get('familia') == 'bornera'
        else:
            sirve = lambda m: m.get('familia') != 'bornera'
        best = None
        for k, m in self.mods.items():
            if not sirve(m):
                continue
            frac = sum(N.resolver_uso(m, tag, u) is not None for u in usos) / max(1, len(usos))
            key = (round(frac, 2), k == prior)
            if best is None or key > best[0]:
                best = (key, k)
        if best is None:
            return prior, 0
        if prior in self.mods:
            fp = sum(N.resolver_uso(self.mods[prior], tag, u) is not None for u in usos) / max(1, len(usos))
            if fp >= best[0][0]:
                return prior, fp
        return best[1], best[0][0]

    def unidades_genericas(self, tag, modelo):
        """Recuadros sin ejemplos de tamano: 'contiene' = la mascara mas chica que contiene la etiqueta (de mas de
        5 mm); 'serie' = las piezas a la derecha de la etiqueta, del tamano que mas se repite."""
        tx, ty, _ = self.etiqueta(tag)
        e = self.esc
        if modelo.get('busqueda') == 'contiene':
            cs = [c for c in self.pl.cajas_que_contienen(tx, ty, 0.5) if c['w'] * e >= 5 and c['h'] * e >= 5]
            cs.sort(key=lambda c: (c['fuente'] != 'mascara', c['w'] * c['h']))
            return cs[:1]
        xl = self.xlim(tag)
        cs = [c for c in self.pl.cajas if 2 <= c['w'] * e <= 25 and 20 <= c['h'] * e <= 150 and c['x0'] > tx - 1.0
              and not (c['x0'] <= tx <= c['x1'] and c['y0'] <= ty <= c['y1'])
              and c['y0'] - 1 <= ty <= c['y1'] + 1 and (c['x0'] + c['x1']) / 2 < xl]
        cnt = collections.Counter((round(c['w'], 1), round(c['h'], 1)) for c in cs)
        if not cnt:
            return []
        (w0, h0), _ = cnt.most_common(1)[0]
        cs = N.sin_solapes([c for c in cs if abs(c['w'] - w0) < 0.3 and abs(c['h'] - h0) < 0.3], w0)
        out = []
        for c in cs:
            if out and c['x0'] - out[-1]['x1'] > 2.5 * c['w']:
                break
            if not out and c['x0'] - tx > 40:
                break
            out.append(c)
        return out

    def por_disposicion(self, caja, disp, borne, modelo=None):
        """Borne ubicado con la disposicion de la hoja de datos: filas de bocas/tornillos dibujados dentro del
        recuadro, de arriba hacia abajo, y en cada fila de izquierda a derecha.  Las filas del dibujo se aparean con las
        de la hoja por cantidad de bornes (se saltean LEDs, potenciometros, etc.).  Si con los circulos no alcanza,
        se prueba con las bocas que no son circulos cerrados (estadios).  Devuelve (x, y, r) o None."""
        modelo = modelo or {}
        e = 0.5
        for fuente in ('circulos', 'aberturas'):
            if fuente == 'circulos':
                bs = self.pl.bocas(caja['x0'] - e, caja['y0'] - e, caja['x1'] + e, caja['y1'] + e, 0.8, 4.5)
            else:
                bs = self.pl.aberturas(caja['x0'] - e, caja['y0'] - e, caja['x1'] + e, caja['y1'] + e)
            if not bs:
                continue
            rmed = mediana([b[2] for b in bs])
            bs = [b for b in bs if abs(b[2] - rmed) <= 0.25 * rmed]
            filas = []
            for b in sorted(bs, key=lambda b: -b[1]):
                if filas and abs(filas[-1][0] - b[1]) < 0.8 and abs(filas[-1][2] - b[2]) < 0.25 * b[2]:
                    filas[-1][1].append(b)
                else:
                    filas.append([b[1], [b], b[2]])
            asig, j = {}, 0
            for fila in disp:
                while j < len(filas) and len(filas[j][1]) != len(fila):
                    j += 1
                if j >= len(filas):
                    break
                for bn, c in zip(fila, sorted(filas[j][1], key=lambda c: c[0])):
                    asig[bn] = c
                j += 1
            asig = self.polaridad(caja, modelo, asig)
            c = asig.get(borne)
            if c:
                return (c[0], c[1], c[2])
        return None

    def polaridad(self, caja, modelo, asig):
        """Piezas con polaridad (borne con diodo): la hoja de datos dice de que lado estan las ranuras del puente
        ('borne_lado_puente').  Si hay un puente (FBS) dibujado sobre la pieza, ese borne es la boca mas cercana al
        puente y el otro la del otro extremo; asi no importa como se haya girado la pieza en el riel."""
        pol = modelo.get('polaridad')
        if not pol or len(asig) != 2 or pol.get('borne_lado_puente') not in asig:
            return asig
        bp = [p for p in self.pl.puentes() if p[0] < caja['x1'] and p[2] > caja['x0'] and caja['y0'] < (p[1] + p[3]) / 2 < caja['y1']]
        if not bp:
            return asig
        yb = sum((p[1] + p[3]) / 2 for p in bp) / len(bp)
        a = pol['borne_lado_puente']
        o = next(k for k in asig if k != a)
        if abs(asig[o][1] - yb) < abs(asig[a][1] - yb):
            asig = {a: asig[o], o: asig[a]}
        return asig

    def orientar(self, m, caja, borne, v, fuentes):
        """Pieza con polaridad y ejemplos: si el puente dibujado esta del otro lado que en los ejemplos (la pieza se
        monto girada), se espeja el borne (v -> 1 - v)."""
        pol = m.get('polaridad')
        if not pol:
            return v
        a = pol.get('borne_lado_puente')
        bp = [p for p in self.pl.puentes() if p[0] < caja['x1'] and p[2] > caja['x0'] and caja['y0'] < (p[1] + p[3]) / 2 < caja['y1']]
        if not bp or not a:
            return v
        vb = (sum((p[1] + p[3]) / 2 for p in bp) / len(bp) - caja['y0']) / caja['h']
        va = [e['puntos'][a]['v'] for _, exs, _ in fuentes for e in exs if a in e['puntos']]
        vo = [1 - e['puntos'][k]['v'] for _, exs, _ in fuentes for e in exs for k in e['puntos'] if k != a]
        va = mediana(va or vo)
        if va is None:
            return v
        return 1 - v if abs(va - vb) > abs((1 - va) - vb) else v

    def por_franja(self, caja, franja, borne):
        """Aparato sin tornillos dibujados (toma corriente): los bornes estan en una franja del borde del recuadro
        (la hoja de datos dice cual y en que orden).  Se reparten parejos a lo ancho de la franja dibujada; si no hay
        franja, a 1/20 del alto desde el borde.  Es una estimacion: confianza baja hasta que se verifique."""
        orden = franja.get('orden', [])
        if borne not in orden:
            return None
        lado = franja.get('lado', 'abajo')
        e = 0.3
        bandas = [c for c in self.pl.cajas if c is not caja and c['x0'] >= caja['x0'] - e and c['x1'] <= caja['x1'] + e
                  and c['y0'] >= caja['y0'] - e and c['y1'] <= caja['y1'] + e and c['w'] >= 0.8 * caja['w']
                  and 1.0 <= c['h'] <= 0.15 * caja['h']]
        if bandas:
            b = min(bandas, key=lambda c: c['y0']) if lado == 'abajo' else max(bandas, key=lambda c: c['y1'])
            x0, x1, y = b['x0'], b['x1'], (b['y0'] + b['y1']) / 2
            r = 0.45 * b['h']
        else:
            x0, x1 = caja['x0'], caja['x1']
            y = caja['y0'] + 0.05 * caja['h'] if lado == 'abajo' else caja['y1'] - 0.05 * caja['h']
            r = 1.5
        i = orden.index(borne)
        return (x0 + (i + 0.5) / len(orden) * (x1 - x0), y, r)

    def desc(self, c):
        k = (round(c['x0'], 2), round(c['y0'], 2), round(c['x1'], 2), round(c['y1'], 2))
        if k not in self._desc:
            self._desc[k] = self.pl.descriptor(c)
        return self._desc[k]

    # ---------------------------------------------------------------- recuadros de las unidades
    def etiqueta(self, tag):
        et = self.comps[tag]['etiqueta_topografico']
        return et['x'], et['y'], et.get('riel')

    def vecino_derecha(self, tag):
        """El componente cuya etiqueta es la siguiente a la derecha en el mismo riel."""
        tx, ty, riel = self.etiqueta(tag)
        c = [(self.etiqueta(t)[0], t) for t in self.comps if t != tag and self.etiqueta(t)[2] == riel
             and self.etiqueta(t)[0] > tx + 1 and abs(self.etiqueta(t)[1] - ty) < 40]
        return min(c)[1] if c else None

    def xlim(self, tag):
        tx, ty, riel = self.etiqueta(tag)
        v = self.vecino_derecha(tag)
        xs = self.pl.marcos_a_la_derecha(tx, ty - 12, ty + 12) + ([self.etiqueta(v)[0]] if v else [])
        return min(xs + [1e9])

    def unidades(self, tag, modelo, ejemplos, tol):
        tx, ty, _ = self.etiqueta(tag)
        tams = sorted({(e['tam_mm'][0], e['tam_mm'][1]) for e in ejemplos})
        verde_ej = max(e['descriptor']['verde'] for e in ejemplos)
        if modelo.get('busqueda') == 'contiene':
            cs = [c for c in self.pl.cajas_que_contienen(tx, ty, 0.5) if tam_coincide(c, tams, self.esc, tol)]
            cs.sort(key=lambda c: (c['fuente'] != 'mascara', min(abs(math.log(c['w'] * self.esc / w)) + abs(math.log(c['h'] * self.esc / h))
                                                                 for w, h in tams), c['w'] * c['h']))
            return cs[:1]
        xl = self.xlim(tag)
        cs = [c for c in self.pl.cajas if tam_coincide(c, tams, self.esc, tol) and c['x0'] > tx - 1.0
              and not (c['x0'] <= tx <= c['x1'] and c['y0'] <= ty <= c['y1'])
              and c['y0'] - 1 <= ty <= c['y1'] + 1 and (c['x0'] + c['x1']) / 2 < xl]
        if tol > TOL_TAM:        # pariente: de los tamanos parecidos, el mas repetido (las piezas de una bornera son iguales)
            cnt = collections.Counter((round(c['w'], 1), round(c['h'], 1)) for c in cs)
            if cnt:
                (w0, h0), _ = cnt.most_common(1)[0]
                cs = [c for c in cs if abs(c['w'] - w0) < 0.3 and abs(c['h'] - h0) < 0.3]
        w_ref = min(w for w, h in tams) / self.esc
        cs = N.sin_solapes(cs, w_ref)
        out = []
        for c in cs:
            if verde_ej < 0.1 and self.desc(c)['verde'] > 0.3:
                continue            # pieza PE (verde): no se numera
            if out and c['x0'] - out[-1]['x1'] > 2.5 * c['w']:
                break               # hueco grande: ya es otro grupo
            if not out and c['x0'] - tx > 40:
                break
            out.append(c)
        return out

    # ---------------------------------------------------------------- modelo de cada componente
    def info(self, tag, excl, _cache):
        """(clave_modelo, unidades, fuentes_de_ejemplos, nivel, nota) del componente, o None."""
        ck = (tag, tuple(sorted(excl)))
        if ck in _cache:
            return _cache[ck]
        usos = self.comps[tag]['usos']
        prior = self.prior.get(tag)
        cands = []
        for clave, m in self.mods.items():
            fu = self.fuentes_de_ejemplos(clave, excl)
            fu = [f for f in fu if f[2] <= 1]
            if not fu:
                continue
            exs = [e for _, ee, _ in fu for e in ee]
            un = self.unidades(tag, m, exs, TOL_TAM)
            if not un:
                continue
            res = [N.resolver_uso(m, tag, u) for u in usos]
            frac = sum(r is not None for r in res) / max(1, len(res))
            dd = sum(min(dist_desc(self.desc(u), e['descriptor']) for e in exs) for u in un) / len(un)
            cands.append(dict(clave=clave, frac=frac, dd=dd, un=un, fu=fu))
        nota = self.nota_lista.get(tag, '')
        elegido = None
        if prior:
            p = [c for c in cands if c['clave'] == prior and c['frac'] >= 0.5]
            if p:
                elegido = p[0]
        if not elegido and cands:
            cands.sort(key=lambda c: (-round(c['frac'], 1), c['dd']))
            elegido = cands[0]
            if prior and prior != elegido['clave']:
                nota = (nota + '; ' if nota else '') + f"la lista dice {prior} pero el dibujo es de {elegido['clave']}"
            elif not prior:
                nota = (nota + '; ' if nota else '') + 'modelo reconocido por el dibujo (no esta en la lista)'
        if elegido:
            nivel = min(f[2] for f in elegido['fu'])
            r = (elegido['clave'], elegido['un'], elegido['fu'], nivel, nota)
        else:
            # ningun modelo con ejemplos coincide con el dibujo: modelo por el texto, ejemplos de un pariente de la
            # misma familia (tolerancia de tamano amplia) o, si no, recuadro generico + disposicion de la hoja de datos
            clave, frac = self.modelo_por_texto(tag, prior)
            if clave is None or frac < 0.5:
                r = (None, [], [], 9, (nota + '; ' if nota else '') + 'modelo desconocido: agregarlo a modelos_base.json')
            else:
                if prior and clave != prior:
                    nota = (nota + '; ' if nota else '') + f'la lista dice {prior}, pero el dibujo no coincide y los textos son de {clave}'
                fu = self.fuentes_de_ejemplos(clave, excl)
                exs = [e for _, ee, _ in fu for e in ee]
                un = self.unidades(tag, self.mods[clave], exs, TOL_TAM_PARIENTE) if exs else []
                if un:
                    r = (clave, un, fu, 2, (nota + '; ' if nota else '') + 'sin ejemplos del modelo: se usa un pariente ('
                         + ', '.join(sorted({f[0] for f in fu})) + ')')
                else:
                    un = self.unidades_genericas(tag, self.mods[clave])
                    r = (clave, un, fu, 3, (nota + '; ' if nota else '') + 'sin ejemplos del modelo: recuadro generico'
                         + (' + disposicion de la hoja de datos' if self.mods[clave].get('disposicion') else '')
                         + (' + pariente (' + ', '.join(sorted({f[0] for f in fu})) + ')' if fu else ''))
        _cache[ck] = r
        return r

    # ---------------------------------------------------------------- transferencia + ajuste fino
    def transferir(self, clave, caja, borne, fuentes, nivel):
        """Punto del borne en la caja: promedio de los ejemplos mas parecidos (posicion normalizada) + ajuste fino.
        Sin ejemplos del modelo (nivel >= 2) manda la disposicion de la hoja de datos si el dibujo la muestra."""
        m = self.mods[clave]
        if nivel >= 2 and m.get('disposicion'):
            p = self.por_disposicion(caja, m['disposicion'], borne, m)
            if p:
                return dict(x=round(p[0], 2), y=round(p[1], 2), r=round(p[2], 2), ajuste='disposicion', desplazamiento=0.0,
                            espejo=False, ejemplos=[])
        sim = m.get('simetria_vertical') or {}
        inv = {v: k for k, v in sim.items()}
        d0 = self.desc(caja)
        cand = []
        for _, exs, niv in fuentes:
            for e in exs:
                if borne in e['puntos']:
                    cand.append((dist_desc(d0, e['descriptor']) + niv, e, e['puntos'][borne], False))
        espejo = False
        if not cand:
            gem = sim.get(borne) or inv.get(borne)
            if gem:
                for _, exs, niv in fuentes:
                    for e in exs:
                        if gem in e['puntos']:
                            cand.append((dist_desc(d0, e['descriptor']) + niv, e, e['puntos'][gem], True))
                espejo = bool(cand)
        if not cand:
            # ningun ejemplo tiene este borne (todavia): la disposicion de la hoja de datos, si el dibujo la muestra
            p = self.por_disposicion(caja, m['disposicion'], borne, m) if m.get('disposicion') else None
            if p:
                return dict(x=round(p[0], 2), y=round(p[1], 2), r=round(p[2], 2), ajuste='disposicion', desplazamiento=0.0,
                            espejo=False, ejemplos=[])
            p = self.por_franja(caja, m['franja'], borne) if m.get('franja') else None
            if p:
                return dict(x=round(p[0], 2), y=round(p[1], 2), r=round(p[2], 2), ajuste='franja', desplazamiento=0.0,
                            espejo=False, ejemplos=[])
            return None
        cand.sort(key=lambda t: t[0])
        top = cand[:K_EJEMPLOS]
        ws = [1.0 / (0.02 + t[0]) for t in top]
        u = sum(w * t[2]['u'] for w, t in zip(ws, top)) / sum(ws)
        v = sum(w * (1 - t[2]['v'] if t[3] else t[2]['v']) for w, t in zip(ws, top)) / sum(ws)
        v = self.orientar(m, caja, borne, v, fuentes)
        x = caja['x0'] + u * caja['w']
        y = caja['y0'] + v * caja['h']
        r_ej = mediana([t[2]['r'] for t in top])
        # ajuste fino (snap)
        amplio = nivel >= 2
        dmax = 2.5 if amplio else 1.2
        circs = [t[2]['circulo'] for t in top if t[2].get('circulo')]
        aj, desp, r = 'ninguno', 0.0, r_ej
        best, dx, dy = None, 0.0, 0.0
        if circs:
            # 1) el circulo dibujado del mismo radio que el del ejemplo, mas cercano
            rc = mediana([c['r'] for c in circs])
            dx = mediana([c['dx'] for c in circs])
            dy = mediana([-c['dy'] if espejo else c['dy'] for c in circs])
            for c in self.pl._circulos():
                if abs(c[0] + dx - x) > dmax or abs(c[1] + dy - y) > dmax or abs(c[2] - rc) > 0.2 * rc + 0.1:
                    continue
                d = math.hypot(c[0] + dx - x, c[1] + dy - y)
                if d <= dmax and (best is None or d < best[0]):
                    best = (d, c)
        if best is None and amplio:
            # 2) modelo pariente: la boca puede ser de otro tamano; la boca dibujada mas cercana
            bs = [c for c in self.pl.bocas(x - dmax, y - dmax, x + dmax, y + dmax, 0.8, 4.5)
                  if math.hypot(c[0] - x, c[1] - y) <= dmax]
            if bs:
                c = min(bs, key=lambda c: math.hypot(c[0] - x, c[1] - y))
                best, dx, dy = (math.hypot(c[0] - x, c[1] - y), c), 0.0, 0.0
        if best:
            nx, ny = best[1][0] + dx, best[1][1] + dy
            desp = math.hypot(nx - x, ny - y)
            x, y, r, aj = nx, ny, best[1][2], 'circulo'
        if aj == 'ninguno':
            # 3) el borne no es un circulo: donde el dibujo coincide con el parche del ejemplo
            par = next((N.txt_a_parche(t[2]['parche']) for t in top if t[2].get('parche')), None)
            if par is not None:
                if espejo:
                    par = par[::-1, :]
                nx, ny, sc, dd = self.pl.ajustar(x, y, par, R=2.0 if amplio else 1.0)
                if sc is not None and sc >= (0.7 if amplio else 0.6):
                    desp = math.hypot(nx - x, ny - y)
                    x, y, aj = nx, ny, 'parche'
        fuente = sorted({f"{t[1]['tablero']}/{t[1]['tag']}/{t[1]['unidad']}" for t in top})
        return dict(x=round(float(x), 2), y=round(float(y), 2), r=round(float(r or 1.5), 2), ajuste=aj, desplazamiento=round(float(desp), 2),
                    espejo=espejo, ejemplos=fuente)

    # ---------------------------------------------------------------- un componente
    def mapear_tag(self, tag, excl=frozenset(), cache=None):
        cache = {} if cache is None else cache
        clave, uns, fuentes, nivel, nota = self.info(tag, excl, cache)
        usos = self.comps[tag]['usos']
        memoria = {}
        if self.usar_memoria:
            for r in self.base.get('reasignaciones', []):
                if r['tag'] in excl or r['componente'] in excl:
                    continue
                memoria[(r['texto'], str(r['cable']))] = r
        puntos, faltan = [], []
        if clave is None:
            for u in usos:
                faltan.append(dict(texto=u['texto'], cable=u['cable'], motivo=nota))
            return puntos, faltan
        m = self.mods[clave]
        # 1) texto -> (componente, unidad, borne)
        res = []
        for u in usos:
            mem = memoria.get((u['texto'], str(u['cable'])))
            if mem:
                res.append([u, mem['componente'], mem['unidad'], mem['borne'], 'memoria: ' + mem['motivo']])
                continue
            r = N.resolver_uso(m, tag, u)
            if r is None:
                res.append([u, tag, None, None, f'el texto no se entiende con la regla {m["regla"]["tipo"]}'])
                continue
            res.append([u, tag, r[0], r[1], ''])
        # nombres repetidos (-Vo / -Vo): por numero de cable creciente, de izquierda a derecha
        grupos = collections.defaultdict(list)
        for i, it in enumerate(res):
            if isinstance(it[3], list):
                grupos[tuple(it[3])].append(i)
        for bl, ii in grupos.items():
            ii.sort(key=lambda i: N.num_cable(res[i][0]['cable']))
            for j, i in enumerate(ii):
                res[i][3] = bl[min(j, len(bl) - 1)]
                res[i][4] = 'nombre repetido: por numero de cable'
        # modulo sin numero (46KR A2): el modulo cuyos otros cables tienen el numero mas cercano
        for it in res:
            if it[2] == 0:
                otros = [(o[2], N.num_cable(o[0]['cable'])) for o in res if o[2] and o[1] == tag]
                c0 = N.num_cable(it[0]['cable'])
                if otros:
                    it[2] = min(otros, key=lambda t: (abs(t[1] - c0), t[0]))[0]
                    it[4] = 'el texto no dice el modulo: modulo del cable de numero mas cercano'
                else:
                    it[2] = 1
                    it[4] = 'el texto no dice el modulo: se toma el 1'
        # 2) unidad fuera de rango -> bornera vecina (el instructivo puso el tag del vecino)
        for it in res:
            if it[1] == tag and it[2] and uns and m.get('busqueda') == 'serie' and it[2] > len(uns):
                v = self.vecino_derecha(tag)
                if v:
                    cv = self.info(v, excl, cache)
                    if cv[0]:
                        u2 = dict(it[0], texto=v + it[0]['texto'][len(tag):])
                        r2 = N.resolver_uso(self.mods[cv[0]], v, u2)
                        if r2 and not isinstance(r2[1], list) and 1 <= r2[0] <= len(cv[1]):
                            it[1], it[2], it[3] = v, r2[0], r2[1]
                            it[4] = f'{tag} tiene {len(uns)} piezas: el borne {it[0]["texto"][len(tag):].strip()} es de la bornera vecina {v}'
        # 3) punto de cada uso
        for u, comp, un, borne, motivo in res:
            base_item = dict(texto=u['texto'], cables=[str(u['cable'])], componente=comp)
            if un is None or borne is None:
                faltan.append(dict(texto=u['texto'], cable=u['cable'], motivo=motivo))
                continue
            if comp == tag:
                cl, us, fu, niv, nt = clave, uns, fuentes, nivel, nota
            else:
                cl, us, fu, niv, nt = self.info(comp, excl, cache)
            if not us or un > len(us) or un < 1:
                faltan.append(dict(texto=u['texto'], cable=u['cable'],
                                   motivo=(nt or '') + f' (unidad {un}: se encontraron {len(us)} en el dibujo)'))
                continue
            t = self.transferir(cl, us[un - 1], borne, fu, niv)
            if t is None:
                faltan.append(dict(texto=u['texto'], cable=u['cable'], motivo=f'ningun ejemplo de {cl} tiene el borne {borne}'))
                continue
            # confianza: alta = ejemplos del mismo modelo; media = mismo dibujo de otro modelo, borne deducido por
            # simetria, disposicion de la hoja de datos, o texto resuelto con una heuristica o con la memoria;
            # baja = modelo pariente (dibujo distinto) o franja estimada
            conf = 'alta'
            if niv >= 2:
                conf = 'media' if t['ajuste'] == 'disposicion' else 'baja'
            elif niv == 1 or t['espejo'] or t['ajuste'] == 'disposicion' or motivo:
                conf = 'media'      # (tambien los textos corregidos por la memoria: conviene que el operario los mire)
            if motivo and motivo != 'nombre repetido: por numero de cable':
                nuevo = texto_de(self.mods[cl], comp, un, borne)
                if nuevo and nuevo != u['texto']:
                    base_item['texto_correcto'] = nuevo
            puntos.append(dict(base_item, x=t['x'], y=t['y'], r=t['r'], confianza=conf, modelo=cl, unidad=un, borne=borne,
                               ajuste=t['ajuste'], desplazamiento_ajuste=t['desplazamiento'], ejemplos=t['ejemplos'],
                               nota='; '.join(x for x in (nt if comp == tag else '', motivo,
                                                           'borne deducido por simetria' if t['espejo'] else '') if x)))
        return puntos, faltan


# ----------------------------------------------------------------------------------------- imagen de control
def control(pdf, pagina_idx, puntos, comps, path, titulo=''):
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw, ImageFont
    doc = pdfium.PdfDocument(pdf)
    pg = doc[pagina_idx]
    W, H = pg.get_size()
    try:
        fnt = ImageFont.truetype('arial.ttf', 13)
        fnt_b = ImageFont.truetype('arialbd.ttf', 20)
    except Exception:
        fnt = fnt_b = ImageFont.load_default()
    # un panel por riel (segun la etiqueta de cada componente); lo que no tiene riel va aparte
    grupos = collections.defaultdict(list)
    for p in puntos:
        et = comps.get(p['componente'], {}).get('etiqueta_topografico', {})
        grupos[et.get('riel') or 0].append(p)
    # un riel muy ancho con puntos lejanos se parte en tramos (para que el zoom sea legible)
    paneles = []
    for riel in sorted(grupos):
        # primero por altura (un aparato del mismo riel pero lejos, como un portafusible suelto), despues por x
        porY = sorted(grupos[riel], key=lambda p: p['y'])
        bandas, b = [], [porY[0]]
        for p in porY[1:]:
            if p['y'] - b[-1]['y'] > 40:
                bandas.append(b); b = [p]
            else:
                b.append(p)
        bandas.append(b)
        for b in sorted(bandas, key=lambda b: -max(p['y'] for p in b)):
            ps = sorted(b, key=lambda p: p['x'])
            tramo = [ps[0]]
            for p in ps[1:]:
                if p['x'] - tramo[-1]['x'] > 60 or p['x'] - tramo[0]['x'] > 200:
                    paneles.append((riel, tramo)); tramo = [p]
                else:
                    tramo.append(p)
            paneles.append((riel, tramo))
    COL = {'alta': (0, 160, 0), 'media': (230, 130, 0), 'baja': (220, 0, 0)}
    imgs = []
    for riel, ps in paneles:
        x0 = min(p['x'] for p in ps) - 14; x1 = max(p['x'] for p in ps) + 14
        y0 = min(p['y'] for p in ps) - 12; y1 = max(p['y'] for p in ps) + 12
        s = max(3.0, min(9.0, 1500.0 / max(1.0, x1 - x0)))
        bm = pg.render(scale=s, crop=(x0, y0, W - x1, H - y1))
        im = bm.to_pil().convert('RGB')
        im = Image.blend(im, Image.new('RGB', im.size, (255, 255, 255)), 0.35)
        dr = ImageDraw.Draw(im)
        a_px = lambda x, y: ((x - x0) * s, (y1 - y) * s)
        ocupado = []
        for p in ps:
            cx, cy = a_px(p['x'], p['y'])
            rr = max(3.0, p['r'] * s)
            ocupado.append((cx - rr, cy - rr, cx + rr, cy + rr))
        for i, p in enumerate(ps):
            cx, cy = a_px(p['x'], p['y'])
            rr = max(3.0, p['r'] * s)
            c = COL.get(p['confianza'], (0, 0, 255))
            dr.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=c, width=3)
            dr.line((cx - 4, cy, cx + 4, cy), fill=c, width=2); dr.line((cx, cy - 4, cx, cy + 4), fill=c, width=2)
        for i, p in enumerate(ps):
            cx, cy = a_px(p['x'], p['y'])
            rr = max(3.0, p['r'] * s)
            c = COL.get(p['confianza'], (0, 0, 255))
            etq = f"{p['texto'].split(' ', 1)[1] if ' ' in p['texto'] else p['texto']} #{p['cables'][0]}"
            tw, th = dr.textbbox((0, 0), etq, font=fnt)[2:]
            puesto = None
            for dist in (rr + 6, rr + 22, rr + 40, rr + 60):
                for ang in (45, 135, -45, -135, 0, 180, 90, -90):
                    a = math.radians(ang)
                    lx = cx + math.cos(a) * dist - (tw if math.cos(a) < -0.1 else 0 if math.cos(a) > 0.1 else tw / 2)
                    ly = cy - math.sin(a) * dist - (th if math.sin(a) > 0.1 else 0 if math.sin(a) < -0.1 else th / 2)
                    rect = (lx - 2, ly - 1, lx + tw + 2, ly + th + 1)
                    if rect[0] < 0 or rect[1] < 0 or rect[2] > im.size[0] or rect[3] > im.size[1]:
                        continue
                    if any(not (rect[2] < o[0] or rect[0] > o[2] or rect[3] < o[1] or rect[1] > o[3]) for o in ocupado):
                        continue
                    puesto = (lx, ly, rect); break
                if puesto:
                    break
            if not puesto:
                lx, ly = cx + rr + 2, cy - th / 2
                puesto = (lx, ly, (lx - 2, ly - 1, lx + tw + 2, ly + th + 1))
            lx, ly, rect = puesto
            ocupado.append(rect)
            # linea guia del rotulo al punto
            qx = min(max(cx, rect[0]), rect[2]); qy = min(max(cy, rect[1]), rect[3])
            if math.hypot(qx - cx, qy - cy) > rr + 3:
                dr.line((cx, cy, qx, qy), fill=c, width=1)
            dr.rectangle(rect, fill=(255, 255, 255), outline=c)
            dr.text((lx, ly), etq, fill=(0, 0, 0), font=fnt)
        tit = f'Riel {riel}' if riel else 'Sin riel'
        tags = sorted({p['componente'] for p in ps})
        cab = Image.new('RGB', (im.size[0], 30), (235, 235, 235))
        ImageDraw.Draw(cab).text((8, 4), f"{tit}: {', '.join(tags)}", fill=(0, 0, 0), font=fnt_b)
        pan = Image.new('RGB', (im.size[0], im.size[1] + 30), (255, 255, 255))
        pan.paste(cab, (0, 0)); pan.paste(im, (0, 30))
        imgs.append(pan)
    # mosaico: paneles en filas de hasta 1600 px de ancho
    filas, fila, ancho = [], [], 0
    for im in imgs:
        if fila and ancho + im.size[0] > 1600:
            filas.append(fila); fila, ancho = [], 0
        fila.append(im); ancho += im.size[0] + 10
    if fila:
        filas.append(fila)
    Wt = max(sum(i.size[0] + 10 for i in f) for f in filas) + 10
    Ht = sum(max(i.size[1] for i in f) + 10 for f in filas) + 60
    out = Image.new('RGB', (Wt, Ht), (255, 255, 255))
    d = ImageDraw.Draw(out)
    d.text((10, 8), titulo, fill=(0, 0, 0), font=fnt_b)
    lx = 10
    for k, c in COL.items():
        d.ellipse((lx, 36, lx + 14, 50), outline=c, width=3); d.text((lx + 20, 35), f'confianza {k}', fill=(0, 0, 0), font=fnt); lx += 150
    d.text((lx, 35), 'circulo = tamano del borne (r); rotulo = borne #cable', fill=(0, 0, 0), font=fnt)
    y = 60
    for f in filas:
        x = 10
        for im in f:
            out.paste(im, (x, y)); x += im.size[0] + 10
        y += max(i.size[1] for i in f) + 10
    out.save(path)


# ----------------------------------------------------------------------------------------- principal
def main():
    t0 = time.time()
    ap = argparse.ArgumentParser(description='Mapea los bornes del instructivo sobre el topografico con la base de ejemplos.')
    ap.add_argument('pdf'); ap.add_argument('usos'); ap.add_argument('salida')
    ap.add_argument('--base', default=os.path.join(AQUI, 'base_bornes.json'))
    ap.add_argument('--lista', default=None, help='lista de materiales (por defecto lista_materiales.txt junto a los usos)')
    ap.add_argument('--modelos', default=None, help='JSON {"modelos": {tag: modelo}} para forzar el modelo de algun tag')
    ap.add_argument('--loo', action='store_true', help='dejando-un-tag-afuera: cada tag sin sus propios ejemplos')
    ap.add_argument('--sin-memoria', action='store_true', help='no usar las reasignaciones de texto aprendidas')
    ap.add_argument('--control', default=None, help='imagen de control (por defecto control.png / control_loo.png junto a la salida)')
    a = ap.parse_args()

    U = json.load(open(a.usos, encoding='utf-8'))
    base = N.cargar_base(a.base)
    lista = a.lista or os.path.join(os.path.dirname(os.path.abspath(a.usos)), 'lista_materiales.txt')
    forz = json.load(open(a.modelos, encoding='utf-8'))['modelos'] if a.modelos else None
    pl = N.Plano(a.pdf, int(U.get('pagina_pdf', 1)) - 1, U['region_bandeja'], U.get('escala_mm_por_pt', 1.0))
    mp = Mapeador(pl, U, base, lista, forz, usar_memoria=not a.sin_memoria)

    puntos, faltan, modelos = [], [], {}
    cache = {}
    for tag in U['componentes']:
        excl = frozenset([tag]) if a.loo else frozenset()
        ps, fs = mp.mapear_tag(tag, excl, cache if not a.loo else {})
        puntos += ps
        faltan += fs
        inf = mp.info(tag, excl, cache if not a.loo else {})
        modelos[tag] = dict(modelo=inf[0], unidades=len(inf[1]), nivel=['mismo modelo', 'mismo dibujo', 'pariente', 'hoja de datos'][inf[3]] if inf[3] <= 3 else 'ninguno',
                            nota=inf[4])
    # el radio no puede pasar la mitad de la distancia al borne vecino (la marca no tapa al de al lado)
    for p in puntos:
        ds = [math.hypot(p['x'] - q['x'], p['y'] - q['y']) for q in puntos if q is not p]
        ds = [d for d in ds if d > 0.5]
        if ds:
            p['r'] = round(min(p['r'], 0.48 * min(ds)), 2)
    seg = round(time.time() - t0, 2)
    out = dict(descripcion=('Bornes ubicados por P4 (base que aprende de tableros verificados)' +
                            (' - DEJANDO-UN-TAG-AFUERA: cada tag sin sus propios ejemplos' if a.loo else '')),
               topografico=os.path.abspath(a.pdf), base=os.path.abspath(a.base), modo='loo' if a.loo else 'normal',
               memoria=not a.sin_memoria, segundos=seg, modelos=modelos, puntos=puntos, no_ubicados=faltan)
    os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
    with open(a.salida, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    if not a.loo:
        # el mismo resultado en el formato que ya lee el programa (bornes.json de la carpeta del proyecto)
        prog = dict(fuente='prototipos/P4_aprende_ejemplos/mapear.py',
                    puntos={f"{p['texto']}#{p['cables'][0]}": dict(xy=[p['x'], p['y']], r=p['r'], conf=p['confianza'], cables=p['cables'])
                            for p in puntos},
                    renombrar={f"{p['texto']}#{p['cables'][0]}": p['texto_correcto'] for p in puntos if p.get('texto_correcto')})
        with open(os.path.join(os.path.dirname(os.path.abspath(a.salida)), 'bornes_programa.json'), 'w', encoding='utf-8') as f:
            json.dump(prog, f, ensure_ascii=False, indent=1)
    png = a.control or os.path.join(os.path.dirname(os.path.abspath(a.salida)), 'control_loo.png' if a.loo else 'control.png')
    try:
        control(a.pdf, int(U.get('pagina_pdf', 1)) - 1, puntos, U['componentes'], png,
                titulo=f"P4 aprende de ejemplos - {'dejando-un-tag-afuera' if a.loo else 'normal'} - {len(puntos)} puntos, {len(faltan)} sin ubicar")
    except Exception as e:
        print('no se pudo dibujar el control:', e)
    print(f'{len(puntos)} puntos, {len(faltan)} sin ubicar, {seg} s -> {a.salida}')
    for f in faltan:
        print(f"  sin ubicar: {f['texto']} #{f['cable']}: {f['motivo']}")


if __name__ == '__main__':
    main()
