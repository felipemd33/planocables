"""P3 - Mapeo de bornes con HOJAS DE DATOS EN MILIMETROS (base SQLite bornes.db).

    python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json>
                     [--materiales lista_materiales.txt] [--base bornes.db] [--pagina N] [--escala 1.4086]
                     [--control salida/control.png]

La idea:
  1. De cada aparato se guarda en la base (datos/modelos.csv + datos/bornes.csv -> bornes.db) el tamano del
     cuerpo en mm y la posicion de cada borne en mm, medida desde la esquina de ARRIBA a la IZQUIERDA del cuerpo
     (vista de frente, riel horizontal), como en la hoja de datos del fabricante.
  2. En el plano se busca el CUERPO del aparato: dos lados verticales separados por el ancho del modelo y con el
     alto del modelo (pasados a pt con la escala del plano), junto a su etiqueta amarilla y en su riel. En las
     borneras y modulos de rele se buscan las PIEZAS que estan a la DERECHA de la etiqueta, hasta la etiqueta
     siguiente del mismo riel (regla del taller), sin contar las piezas verdes (PE).
  3. Cada borne se calcula: x = borde izquierdo + x_mm / escala, y = borde de arriba - y_mm / escala.
     No hace falta que el dibujo tenga tornillos ni bocas: alcanza con el contorno del cuerpo.

El modelo de cada componente sale de la lista de materiales (si esta) y se controla con las medidas del cuerpo
dibujado: si la lista dice un modelo que no entra en el dibujo, se prueba con todos los de la base y se queda el
que coincide en medidas (queda un aviso).  No hay coordenadas de ningun tablero escritas en este programa.
"""
import argparse, json, math, os, re, sqlite3, sys, time, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from geometria import Plano  # noqa: E402

BASE = os.path.join(AQUI, 'bornes.db')
REGLAS_PIEZA = ('cuatro_puntos', 'dos_pisos', 'diodo', 'fusible')


# ============================================================================ base de datos
def cargar_base(ruta):
    """Lee bornes.db.  Si es la base por defecto y las planillas CSV son mas nuevas, la rearma antes."""
    if os.path.abspath(ruta) == os.path.abspath(BASE):
        csvs = [os.path.join(AQUI, 'datos', f) for f in ('modelos.csv', 'bornes.csv')]
        if not os.path.exists(ruta) or any(os.path.getmtime(c) > os.path.getmtime(ruta) for c in csvs if os.path.exists(c)):
            import cargar_base as cb
            cb.armar(ruta)
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    modelos = {r['codigo']: dict(r) for r in con.execute('SELECT * FROM modelo')}
    for m in modelos.values():
        m['bornes'] = []
    for r in con.execute('SELECT * FROM borne ORDER BY rowid'):
        modelos[r['modelo']]['bornes'].append(dict(r))
    con.close()
    return modelos


# ============================================================================ lista de materiales
def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Z0-9]', '', s.upper())


def normb(s):
    """Nombre de borne comparable: mayusculas, sin acentos ni espacios, pero con los signos (+Vo y -Vo son distintos)."""
    s = unicodedata.normalize('NFKC', s or '').upper()
    s = ''.join(ch for ch in unicodedata.normalize('NFKD', s) if not unicodedata.combining(ch))
    return re.sub(r'\s+', '', s)


TAG_RE = re.compile(r'^\d{2,3}[A-Z]{1,6}\d{0,3}$')


def leer_materiales(ruta):
    """{tag: texto} a partir de la lista de materiales (una fila por renglon, campos separados por '|').
    Renglones sin tag se suman al tag anterior.  '43DIB1 | /2' vale para 43DIB1 y 43DIB2."""
    out, ultimo = {}, []
    if not ruta or not os.path.exists(ruta):
        return out
    for linea in open(ruta, encoding='utf-8', errors='replace'):
        toks = [t.strip() for t in linea.strip().split('|')]
        if not any(toks):
            continue
        i = 0
        while i < len(toks) and toks[i] in ('A', 'B', 'C', '-', ''):
            i += 1
        if i < len(toks) and TAG_RE.match(toks[i].upper().replace(' ', '')):
            t = toks[i].upper().replace(' ', '')
            tags, resto = [t], toks[i + 1:]
            if resto and re.match(r'^/\d+$', resto[0]):
                tags.append(re.sub(r'\d+$', '', t) + resto[0][1:])
                resto = resto[1:]
            ultimo = tags
        else:
            tags, resto = ultimo, toks
        for t in tags:
            out.setdefault(t, []).append(' | '.join(resto))
    return {t: ' | '.join(v) for t, v in out.items()}


def modelos_de_lista(texto, modelos):
    """Modelos de la base cuyo alias aparece en el texto de la lista de materiales.  Si un alias corto esta
    contenido en otro mas largo que tambien aparece (PTT 2,5 dentro de PTT 2,5-2MT), gana el mas largo."""
    t = norm(texto)
    if not t:
        return []
    puntaje = {}
    for cod, m in modelos.items():
        als = [cod] + [a for a in (m['alias_bom'] or '').split('|') if a.strip()]
        largos = [len(norm(a)) for a in als if len(norm(a)) >= 3 and norm(a) in t]
        if largos:
            puntaje[cod] = max(largos)
    if not puntaje:
        return []
    mx = max(puntaje.values())
    return [c for c, v in sorted(puntaje.items(), key=lambda kv: -kv[1]) if v == mx]


# ============================================================================ busqueda de cuerpos
class Buscador:
    def __init__(self, P, escala):
        self.P = P
        self.esc = escala
        self.rieles = P.rieles()
        self._cache = {}

    def riel_de(self, x, y, max_dy=60):
        cand = [r for r in self.rieles if r['x0'] - 25 <= x <= r['x1'] + 25 and abs(r['y'] - y) <= max_dy]
        return min(cand, key=lambda r: abs(r['y'] - y)) if cand else None

    def medidas_pt(self, m):
        w, h = m['ancho_mm'] / self.esc, m['alto_mm'] / self.esc
        tol = (m['tol_pct'] or 5.0) / 100.0
        return w, h, max(0.18, 0.6 * tol * w), tol + 0.02

    def cuerpos(self, m, x0, x1, yref):
        k = (m['codigo'], round(x0, 1), round(x1, 1), round(yref, 1))
        if k not in self._cache:
            w, h, tw, th = self.medidas_pt(m)
            self._cache[k] = self.P.piezas(x0, x1, yref, w, h, tol_ancho=tw, tol_alto=th, max_n=200)
        return self._cache[k]

    def aparato(self, m, tx, ty, x_fin):
        """Cuerpo del modelo m que contiene la etiqueta, o el primero a su derecha (antes de la etiqueta
        siguiente).  Devuelve (cuerpo, distancia) o (None, None)."""
        w, h, _, _ = self.medidas_pt(m)
        riel = self.riel_de(tx, ty)
        mejor = None
        for yref in [ty] + ([riel['y']] if riel else []):
            for c in self.cuerpos(m, tx - w - 2, tx + max(w, 20) + 2, yref):
                cx = (c['x0'] + c['x1']) / 2
                dentro_x = c['x0'] - 0.8 <= tx <= c['x1'] + 0.8
                dentro_y = c['y0'] - 0.8 <= ty <= c['y1'] + 0.8
                if dentro_x and dentro_y:
                    d = 0.0
                elif dentro_x:
                    d = min(abs(ty - c['y0']), abs(ty - c['y1'])) * 0.5 + 0.5
                elif cx > tx and c['x0'] < x_fin and c['x0'] - tx < max(20.0, w):
                    d = (c['x0'] - tx) + 1.0 + (0 if dentro_y else 5)
                else:
                    continue
                d += c['err']
                if mejor is None or d < mejor[1]:
                    mejor = (c, d)
        return mejor if mejor else (None, None)

    def piezas(self, m, tx, ty, x_fin):
        """Piezas del modelo m a la derecha de la etiqueta y antes de la siguiente del mismo riel (sin PE)."""
        riel = self.riel_de(tx, ty)
        if riel is None:
            return []
        w, h, _, _ = self.medidas_pt(m)
        cs = self.cuerpos(m, tx - w, min(x_fin, riel['x1'] + 5) + w, riel['y'])
        return [c for c in cs if tx < (c['x0'] + c['x1']) / 2 < x_fin and not c['verde']]


def puentes_de_color(P):
    """Rectangulos rellenos de color (puentes FBS dibujados) fuera de la capa de etiquetas."""
    out = []
    for lay, op, pts, rgb in P.trazos:
        if op not in ('f', 'F', 'f*', 'B', 'b', 'B*', 'b*') or not rgb or 'etiqueta' in lay.lower() or len(pts) < 4:
            continue
        if max(rgb) - min(rgb) < 0.5 or (rgb[0] > 0.7 and rgb[1] > 0.7):   # sin gris / negro / amarillo
            continue
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if max(ys) - min(ys) < 4 and max(xs) - min(xs) > 3:
            out.append((min(xs), max(xs), (min(ys) + max(ys)) / 2))
    return out


# ============================================================================ bornes
def borne_pt(c, b, m, esc, espejo=False):
    """Punto de un borne de la base en el cuerpo c (x_mm desde la izquierda, y_mm desde arriba)."""
    xm, ym = b['x_mm'], b['y_mm']
    if espejo:
        xm, ym = m['ancho_mm'] - xm, m['alto_mm'] - ym
    return c['x0'] + xm / esc, c['y1'] - ym / esc


def nombres(b):
    return [normb(b['nombre'])] + [normb(a) for a in (b['alias'] or '').split('|') if a.strip()]


def buscar_borne(m, borne, parte):
    """Bornes del modelo que corresponden al rotulo del instructivo (regla 'nombre')."""
    B = m['bornes']
    k1, k2, kp = normb('%s %s' % (borne, parte)), normb(borne), normb(parte)
    if k2:
        r = [b for b in B if k1 in nombres(b)]
        if r:
            return r, 'nombre+lado'
        r = [b for b in B if k2 in nombres(b)]
        if r and not m['ignora_lado_texto'] and parte:
            r2 = [b for b in r if b['lado'] == parte]
            if r2:
                return r2, 'nombre (lado del texto)'
        if r:
            return r, 'nombre' + (' (el lado del texto no se usa en este modelo)' if m['ignora_lado_texto'] else '')
        return [], 'sin borne con ese nombre'
    if kp:
        r = [b for b in B if kp in nombres(b)] or [b for b in B if b['lado'] == parte]
        return r, 'solo lado'
    return [], 'sin nombre'


def numero(s):
    mm = re.match(r'^\D*(\d+)', s or '')
    return int(mm.group(1)) if mm else None


def cable_num(u):
    try:
        return int(re.sub(r'\D', '', u.get('cable') or '') or 0)
    except ValueError:
        return 0


# ============================================================================ programa
def argumentos(lista=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('topografico'); ap.add_argument('usos'); ap.add_argument('salida')
    ap.add_argument('--materiales', help='lista de materiales (por defecto lista_materiales.txt junto a los usos)')
    ap.add_argument('--base', default=BASE)
    ap.add_argument('--pagina', type=int, help='pagina PDF (1 = primera); por defecto la de los usos')
    ap.add_argument('--escala', type=float, help='mm por pt; por defecto la de los usos o la del riel DIN')
    ap.add_argument('--control', help='imagen de control (por defecto control.png junto a la salida)')
    return ap.parse_args(lista)


def main():
    mapear(argumentos())


def mapear(a, trazos=None):
    """a = argumentos (ver argumentos()); trazos = trazos ya leidos de la pagina (para pruebas)."""
    t0 = time.time()

    modelos = cargar_base(a.base)
    usos = json.load(open(a.usos, encoding='utf-8'))
    pagina = a.pagina or usos.get('pagina_pdf') or 1
    mat = a.materiales or os.path.join(os.path.dirname(os.path.abspath(a.usos)), 'lista_materiales.txt')
    lista = leer_materiales(mat)
    avisos = []
    if not lista:
        avisos.append('Sin lista de materiales: el modelo de cada componente se elige solo por las medidas del cuerpo')

    P = Plano(a.topografico, pagina - 1, trazos=trazos)
    rieles = P.rieles()
    esc_riel = None
    if rieles:
        anchos = sorted(r['ancho_pt'] for r in rieles)
        esc_riel = 35.0 / anchos[len(anchos) // 2]          # perfil DIN = 35 mm
    esc = a.escala or usos.get('escala_mm_por_pt') or esc_riel or 1.0
    if esc_riel and abs(esc_riel - esc) / esc > 0.02:
        avisos.append('La escala del riel DIN (%.4f mm/pt) no coincide con la usada (%.4f)' % (esc_riel, esc))
    Bq = Buscador(P, esc)

    comps = usos['componentes']
    conocidas = [(c['etiqueta_topografico']['x'], c['etiqueta_topografico']['y']) for c in comps.values()]
    etiquetas = []
    for e in P.etiquetas(conocidas) + [dict(x=x, y=y) for x, y in conocidas]:
        if not any(abs(e['x'] - f['x']) < 1.2 and abs(e['y'] - f['y']) < 1.2 for f in etiquetas):
            etiquetas.append(e)

    def x_siguiente(tx, ty):
        riel = Bq.riel_de(tx, ty)
        if riel is None:
            return tx + 200
        sig = [e['x'] for e in etiquetas if e['x'] > tx + 1.0 and abs(e['y'] - riel['y']) < 40
               and riel['x0'] - 25 <= e['x'] <= riel['x1'] + 25]
        return min(sig) if sig else riel['x1'] + 5

    def borde_izq_etiqueta(xc):
        """Borde izquierdo del recuadro de la etiqueta con centro en xc (o el centro si no se conoce)."""
        e = min(etiquetas, key=lambda e: abs(e['x'] - xc))
        return e.get('x0', e['x']) if abs(e['x'] - xc) < 0.5 else xc

    puentes = puentes_de_color(P)

    # ---------------------------------------------------------------- 1) modelo y cuerpo de cada componente
    ubic = {}
    for tag, c in comps.items():
        e = c['etiqueta_topografico']; tx, ty = e['x'], e['y']
        xf = x_siguiente(tx, ty)
        de_lista = modelos_de_lista(lista.get(tag, ''), modelos)
        candidatos = []

        def probar(cod, origen):
            m = modelos[cod]
            if m['tipo'] == 'pieza':
                ps = Bq.piezas(m, tx, ty, xf)
                if ps:
                    err = sum(p['err'] for p in ps) / len(ps)
                    candidatos.append(dict(modelo=cod, cuerpos=ps, origen=origen, n=len(ps), err=err,
                                           tipo_ok=bool(c.get('es_bornera')) or m['regla'] == 'modulo'))
            else:
                cu, d = Bq.aparato(m, tx, ty, xf)
                if cu:
                    candidatos.append(dict(modelo=cod, cuerpos=[cu], origen=origen, n=1, err=d,
                                           tipo_ok=not c.get('es_bornera')))
        for cod in de_lista:
            probar(cod, 'lista')
        if not candidatos:
            for cod in modelos:
                probar(cod, 'medidas')
            if de_lista:
                avisos.append('%s: la lista de materiales dice %s, pero el cuerpo dibujado no tiene esas medidas'
                              % (tag, ' / '.join(de_lista)))
        if not candidatos:
            avisos.append('%s: no encontre ningun cuerpo de la base junto a la etiqueta' % tag)
            ubic[tag] = None
            continue
        candidatos.sort(key=lambda k: (not k['tipo_ok'], -k['n'] if modelos[k['modelo']]['tipo'] == 'pieza' else 0, k['err']))
        g = candidatos[0]
        if g['origen'] == 'medidas':
            iguales = [k['modelo'] for k in candidatos[1:] if abs(k['err'] - g['err']) < 0.05 and k['n'] == g['n']]
            avisos.append('%s: modelo elegido por las medidas del cuerpo: %s%s' % (
                tag, g['modelo'], (' (empata con %s)' % ', '.join(iguales)) if iguales else ''))
        m = modelos[g['modelo']]
        # orientacion por el puente dibujado (borne con diodo: el puente marca el lado del anodo)
        espejo = False
        if m['lado_puente'] and m['regla'] in REGLAS_PIEZA:
            votos = 0
            for cu in g['cuerpos']:
                ym = (cu['y0'] + cu['y1']) / 2
                for bx0, bx1, by in puentes:
                    if bx0 < cu['x1'] - 0.3 and bx1 > cu['x0'] + 0.3 and cu['y0'] < by < cu['y1'] and abs(by - ym) > 0.3:
                        votos += 1 if by < ym else -1
            if votos:
                lado = 'ABAJO' if votos > 0 else 'ARRIBA'
                espejo = lado != m['lado_puente']
                g['puente'] = lado
        g['espejo'] = espejo
        g['xf'] = xf
        # lugar libre entre la ultima pieza y la etiqueta siguiente (si entra otra pieza, puede faltar una)
        g['libre_final'] = borde_izq_etiqueta(xf) - g['cuerpos'][-1]['x1'] if m['tipo'] == 'pieza' else 0.0
        rl = Bq.riel_de(tx, ty)
        g['riel_y'] = round(rl['y'], 2) if rl else None
        # hueco entre piezas: puede haber una pieza que no se reconocio y la numeracion quedaria corrida
        g['hueco_desde'] = None
        if m['tipo'] == 'pieza' and len(g['cuerpos']) > 1:
            w = m['ancho_mm'] / esc
            for i in range(1, len(g['cuerpos'])):
                hueco = g['cuerpos'][i]['x0'] - g['cuerpos'][i - 1]['x1']
                if hueco > 0.6 * w:
                    g['hueco_desde'] = i + 1
                    avisos.append('%s: hueco de %.1f pt entre las piezas %d y %d (puede haber una pieza que no se '
                                  'reconocio): desde la pieza %d la confianza baja a media' % (tag, hueco, i, i + 1, i + 1))
                    break
        ubic[tag] = g

    # vecino a la derecha en el mismo riel (para numeros que no existen en la bornera)
    def vecino_derecha(tag):
        e = comps[tag]['etiqueta_topografico']
        riel = Bq.riel_de(e['x'], e['y'])
        if riel is None:
            return None
        cand = [(comps[t]['etiqueta_topografico']['x'], t) for t in comps if t != tag and ubic.get(t)
                and comps[t]['etiqueta_topografico']['x'] > e['x']
                and abs(comps[t]['etiqueta_topografico']['y'] - riel['y']) < 40]
        return min(cand)[1] if cand else None

    # ---------------------------------------------------------------- 2) cada uso -> borne -> punto
    puntos = []
    for tag, c in comps.items():
        g = ubic.get(tag)
        e = c['etiqueta_topografico']
        if not g:
            for u in c['usos']:
                puntos.append(dict(texto=u['texto'], cables=[u['cable']], x=e['x'], y=e['y'], r=1.0, confianza='baja',
                                   componente=tag, modelo=None, como='sin cuerpo encontrado: punto en la etiqueta'))
            continue
        m = modelos[g['modelo']]
        conf0 = 'alta' if g['origen'] == 'lista' else 'media'
        # repartir los usos que nombran un borne repetido (p. ej. dos '-Vo'): de izquierda a derecha por cable
        repetidos = {}

        def punto(tagc, gg, mm, pieza, b, conf, como, u):
            cu = gg['cuerpos'][pieza - 1]
            x, y = borne_pt(cu, b, mm, esc, gg.get('espejo'))
            return dict(texto=u['texto'], cables=[u['cable']], x=round(x, 2), y=round(y, 2),
                        r=round((b['radio_mm'] or 1.5) / esc, 2), confianza=conf, componente=tagc, modelo=mm['codigo'],
                        pieza=pieza, borne_modelo=b['nombre'], lado_fisico=('ABAJO' if b['lado'] == 'ARRIBA' else 'ARRIBA')
                        if gg.get('espejo') else b['lado'], como=como)

        usos_ord = sorted(c['usos'], key=cable_num)
        for u in usos_ord:
            borne, parte = (u.get('borne') or '').strip(), (u.get('parte') or u.get('lado') or '').strip().upper()
            if not parte:
                parte = 'ARRIBA' if 'ARRIBA' in u['texto'].upper() else ('ABAJO' if 'ABAJO' in u['texto'].upper() else '')
            regla = m['regla']
            conf, notas = conf0, []
            if m['ignora_lado_texto'] and parte:
                notas.append('el ARRIBA/ABAJO del texto no se usa en este modelo')
            res = None   # (tag, g, modelo, pieza, borne_db)

            def por_nombre(mm, key_extra=''):
                bs, como = buscar_borne(mm, borne, parte)
                if not bs:
                    return None, como
                bs = sorted(bs, key=lambda b: (b['x_mm'], b['y_mm']))
                k = (tag, key_extra, tuple(b['nombre'] for b in bs))
                i = repetidos.get(k, 0)
                repetidos[k] = i + 1
                if len(bs) > 1:
                    como += '; %d bornes con ese nombre, se reparten de izquierda a derecha por numero de cable (%d de %d)' % (
                        len(bs), min(i, len(bs) - 1) + 1, len(bs))
                return bs[min(i, len(bs) - 1)], como

            if regla == 'nombre':
                b, como = por_nombre(m)
                if b:
                    res = (tag, g, m, 1, b); notas.insert(0, 'borne %s por %s' % (b['nombre'], como))
            elif regla == 'modulo':
                t0_ = u['texto'].split()[0] if u['texto'] else ''
                suf = t0_[len(tag):] if t0_.upper().startswith(tag.upper()) else ''
                mod = int(suf) if suf.isdigit() else None
                if mod is None and len(g['cuerpos']) > 1:
                    # sin numero de modulo: el modulo cuyos otros cables tienen el numero mas parecido
                    cn = cable_num(u); best = None
                    for v in c['usos']:
                        tv = v['texto'].split()[0]
                        sv = tv[len(tag):] if tv.upper().startswith(tag.upper()) else ''
                        if sv.isdigit() and v is not u:
                            d = abs(cable_num(v) - cn)
                            if best is None or d < best[0]:
                                best = (d, int(sv))
                    mod = best[1] if best else 1
                    conf = 'baja'
                    notas.append('el texto no dice el modulo: se toma el %d (cable de numero mas cercano)' % mod)
                mod = mod or 1
                if mod > len(g['cuerpos']):
                    notas.append('solo hay %d modulos: se usa el ultimo' % len(g['cuerpos'])); conf = 'baja'
                    mod = len(g['cuerpos'])
                b, como = por_nombre(m, key_extra=str(mod))
                if b:
                    res = (tag, g, m, mod, b); notas.insert(0, 'modulo %d, borne %s' % (mod, b['nombre']))
            else:
                n = numero(borne)
                if n is None:
                    n = 1; conf = 'baja'; notas.append('el texto no trae numero de borne: se usa el 1')

                def resolver(mm, n):
                    """(pieza, nombre del borne en la base, explicacion) segun la regla del modelo."""
                    rg = mm['regla']
                    if rg == 'cuatro_puntos':
                        p = u.get('punto')
                        if not p and '.' in u['texto']:
                            p = numero(u['texto'].split('.')[-1])
                        p = p or (1 if parte == 'ARRIBA' else 4)
                        return n, str(p), 'pieza %d, punto %s' % (n, p)
                    if rg == 'dos_pisos':
                        k = (n + 1) // 2
                        return k, '%s_%s' % ('impar' if n % 2 else 'par', parte or 'ARRIBA'), \
                            'pieza %d (= ceil(%d/2)), %s' % (k, n, 'impar: boca del extremo' if n % 2 else 'par: boca interior')
                    if rg == 'fusible':
                        f = borne.upper().startswith('F')
                        return n, '%s_%s' % ('int' if f else 'ext', parte or 'ARRIBA'), \
                            'pieza %d, %s' % (n, 'nivel del fusible: boca interior' if f else 'paso directo: boca del extremo')
                    if rg == 'diodo':
                        bs, _ = buscar_borne(mm, '', parte)
                        nb = bs[0]['nombre'] if bs else mm['bornes'][0]['nombre']
                        return n, nb, 'pieza %d, %s (texto %s)' % (n, nb, parte)
                    return n, None, ''
                pieza, nb, como = resolver(m, n)
                gg, mm, tg = g, m, tag
                if pieza > len(g['cuerpos']):
                    vec = vecino_derecha(tag)
                    if vec and modelos[ubic[vec]['modelo']]['regla'] in REGLAS_PIEZA:
                        gv, mv = ubic[vec], modelos[ubic[vec]['modelo']]
                        pv, nbv, comov = resolver(mv, n)
                        propios = [v for v in comps[vec]['usos'] if numero(v.get('borne') or '') == n
                                   and (v.get('parte') or v.get('lado') or '').upper() == parte and v['cable'] != u['cable']]
                        if propios:
                            notas.append('la bornera vecina %s ya usa su borne %d %s con el cable %s: no se desborda'
                                         % (vec, n, parte, propios[0]['cable']))
                        elif g.get('libre_final', 0) > 0.8 * m['ancho_mm'] / esc:
                            notas.append('despues de la ultima pieza de %s queda lugar para otra (%.1f pt): puede faltar una '
                                         'pieza en el dibujo, no se desborda a %s' % (tag, g['libre_final'], vec))
                        elif pv <= len(gv['cuerpos']):
                            gg, mm, tg, pieza, nb, como = gv, mv, vec, pv, nbv, comov
                            conf = 'baja'
                            notas.append('%s tiene %d piezas y no existe el borne %d: se toma en la bornera vecina %s'
                                         % (tag, len(g['cuerpos']), n, vec))
                    if tg == tag:
                        notas.append('%s tiene %d piezas: no existe el borne %d' % (tag, len(g['cuerpos']), n))
                        conf = 'baja'
                        pieza = None
                if pieza:
                    bdb = [b for b in mm['bornes'] if b['nombre'] == nb]
                    if bdb:
                        res = (tg, gg, mm, pieza, bdb[0]); notas.insert(0, como)
            if res is None:
                puntos.append(dict(texto=u['texto'], cables=[u['cable']], x=e['x'], y=e['y'], r=1.0, confianza='baja',
                                   componente=tag, modelo=m['codigo'], como='; '.join(notas + ['no se pudo resolver el borne: punto en la etiqueta'])))
                continue
            tg, gg, mm, pieza, b = res
            if b['fuente'] in ('estimado', 'foto') and conf == 'alta':
                conf = 'media'
            if gg.get('hueco_desde') and pieza >= gg['hueco_desde']:
                notas.append('hay un hueco antes de esta pieza: revisar la numeracion')
                if conf == 'alta':
                    conf = 'media'
            notas.append('modelo %s (%s), borne a %.2f / %.2f mm del borde izq. / sup.' % (
                mm['codigo'], 'lista de materiales' if gg['origen'] == 'lista' else 'por medidas', b['x_mm'], b['y_mm']))
            if gg.get('espejo'):
                notas.append('pieza girada 180 grados (puente dibujado del otro lado)')
            puntos.append(punto(tg, gg, mm, pieza, b, conf, '; '.join(notas), u))

    # ---------------------------------------------------------------- 3) control: dos cables distintos en una misma boca
    por_boca = {}
    for p in puntos:
        if p.get('borne_modelo'):
            por_boca.setdefault((p['componente'], p.get('pieza'), p['borne_modelo']), []).append(p)
    for (tg, pz, bn), ps in por_boca.items():
        cables = sorted(set(c for p in ps for c in p['cables']))
        if len(cables) > 1:
            for p in ps:
                p['revisar'] = 'la boca %s %s de %s recibe %d cables distintos (%s): revisar el instructivo' % (
                    'pieza %s' % pz if pz else '', bn, tg, len(cables), ', '.join(cables))
                if p['confianza'] == 'alta':
                    p['confianza'] = 'media'

    seg = round(time.time() - t0, 1)
    salida = dict(metodo='P3_dimensiones_mm', topografico=a.topografico, pagina_pdf=pagina, escala_mm_por_pt=esc,
                  escala_riel_din=round(esc_riel, 4) if esc_riel else None, segundos=seg, puntos=puntos,
                  componentes={t: (None if not g else dict(modelo=g['modelo'], origen=g['origen'], piezas=len(g['cuerpos']),
                                                          espejo=g.get('espejo', False), riel_y=g.get('riel_y'),
                                                          cuerpos=[dict(x0=round(k['x0'], 2), x1=round(k['x1'], 2), y0=round(k['y0'], 2),
                                                                        y1=round(k['y1'], 2)) for k in g['cuerpos']]))
                               for t, g in ubic.items()},
                  avisos=avisos)
    os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
    with open(a.salida, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    ctl = a.control or os.path.join(os.path.dirname(os.path.abspath(a.salida)), 'control.png')
    try:
        dibujar_control(a.topografico, pagina - 1, salida, ctl)
        dibujar_general(a.topografico, pagina - 1, salida, usos.get('region_bandeja'),
                        os.path.splitext(ctl)[0] + '_general.png')
    except Exception as ex:   # la imagen es un control, no debe cortar el mapeo
        avisos.append('no se pudo dibujar el control: %s' % ex)
    salida['segundos'] = round(time.time() - t0, 1)
    with open(a.salida, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    n = len(puntos)
    print('%d puntos (%d alta, %d media, %d baja) en %.1f s -> %s' % (
        n, sum(p['confianza'] == 'alta' for p in puntos), sum(p['confianza'] == 'media' for p in puntos),
        sum(p['confianza'] == 'baja' for p in puntos), salida['segundos'], a.salida))
    for av in avisos:
        print('  aviso: ' + av)
    return salida


# ============================================================================ imagenes de control
COLORES = dict(alta=(215, 0, 0), media=(235, 115, 0), baja=(150, 0, 210))


def _fuentes(t=12):
    from PIL import ImageFont
    try:
        return ImageFont.truetype('arial.ttf', t), ImageFont.truetype('arialbd.ttf', t + 3)
    except Exception:
        f = ImageFont.load_default()
        return f, f


def _render(pdf, idx, x0, y0, x1, y1, k):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    pg = doc[idx]
    W, H = pg.get_size()
    img = pg.render(scale=k, crop=(x0, y0, W - x1, H - y1)).to_pil().convert('RGB')
    return img.point(lambda v: 120 + v * 135 // 255)    # plano aclarado para que resalten las marcas


def dibujar_control(pdf, idx, salida, ruta, k=7.0):
    """Un panel por riel (y uno por aparato fuera de riel): cuerpos ubicados en verde, cada borne con un circulo
    del radio del borne y su rotulo vertical (texto del instructivo sin el tag + cable) arriba o abajo."""
    import textwrap
    from PIL import Image, ImageDraw
    fuente, fuente_t = _fuentes(12)
    comps = {t: g for t, g in salida['componentes'].items() if g}
    grupos = {}
    for t, g in comps.items():
        clave = ('riel', g['riel_y']) if g.get('riel_y') is not None else ('solo', t)
        grupos.setdefault(clave, []).append(t)

    def altura(kv):
        return kv[0][1] if kv[0][0] == 'riel' else comps[kv[1][0]]['cuerpos'][0]['y1']
    paneles = []
    for clave, tags in sorted(grupos.items(), key=lambda kv: -altura(kv)):
        cs = [c for t in tags for c in comps[t]['cuerpos']]
        pts = [p for p in salida['puntos'] if p.get('componente') in tags]
        bx0 = min(c['x0'] for c in cs); bx1 = max(c['x1'] for c in cs)
        by0 = min(c['y0'] for c in cs); by1 = max(c['y1'] for c in cs)
        for p in pts:
            bx0, bx1 = min(bx0, p['x']), max(bx1, p['x'])
            by0, by1 = min(by0, p['y'] - 1), max(by1, p['y'] + 1)
        mx, my = 8.0, 20.0
        x0, x1, y0, y1 = bx0 - mx, bx1 + mx, by0 - my, by1 + my
        img = _render(pdf, idx, x0, y0, x1, y1, k)
        d = ImageDraw.Draw(img)
        X = lambda x: (x - x0) * k
        Y = lambda y: (y1 - y) * k
        for t in tags:
            for c in comps[t]['cuerpos']:
                d.rectangle((X(c['x0']), Y(c['y1']), X(c['x1']), Y(c['y0'])), outline=(0, 150, 0), width=2)
        ocupado = dict(arriba=[], abajo=[])
        for p in sorted(pts, key=lambda p: (p['x'], -p['y'])):
            cl = COLORES.get(p['confianza'], COLORES['alta'])
            cx, cy, r = X(p['x']), Y(p['y']), max(3.0, (p.get('r') or 0.5) * k)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=cl, width=2)
            d.ellipse((cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5), fill=cl)
            g = comps[p['componente']]
            pz = p.get('pieza')
            cu = g['cuerpos'][pz - 1] if pz and pz <= len(g['cuerpos']) else g['cuerpos'][0]
            lado = 'arriba' if p['y'] >= (cu['y0'] + cu['y1']) / 2 else 'abajo'
            txt = p['texto'][len(p['componente']):].strip() if p['texto'].startswith(p['componente']) else p['texto']
            txt = ('%s  %s' % (txt or '-', p['cables'][0] if p['cables'] else '')).strip() + (' !' if p.get('revisar') else '')
            tw = int(d.textlength(txt, font=fuente)) + 4
            lab = Image.new('RGB', (tw, 16), (255, 255, 255))
            ImageDraw.Draw(lab).text((2, 1), txt, fill=cl, font=fuente)
            lab = lab.rotate(90, expand=True)           # 16 x tw, se lee de abajo hacia arriba
            base = cx - 8
            lx = base
            for paso in range(0, 80):
                cand = base + ((paso + 1) // 2) * 16 * (1 if paso % 2 else -1)
                if all(abs(cand - o) >= 16 for o in ocupado[lado]):
                    lx = cand
                    break
            ocupado[lado].append(lx)
            if lado == 'arriba':
                ly = max(2, Y(by1) - 10 - lab.size[1])
                d.line((cx, cy - r, lx + 8, ly + lab.size[1]), fill=cl, width=1)
            else:
                ly = min(img.size[1] - lab.size[1] - 2, Y(by0) + 10)
                d.line((cx, cy + r, lx + 8, ly), fill=cl, width=1)
            img.paste(lab, (int(lx), int(ly)))
        titulo = ('Riel y = %.1f pt' % clave[1]) if clave[0] == 'riel' else 'Fuera de riel'
        leyenda = '   '.join('%s: %s (%s%s)' % (t, comps[t]['modelo'], 'lista de materiales' if comps[t]['origen'] == 'lista'
                                                  else 'por medidas', ', %d piezas' % comps[t]['piezas'] if comps[t]['piezas'] > 1 else '')
                               for t in sorted(tags, key=lambda t: comps[t]['cuerpos'][0]['x0']))
        paneles.append((titulo, leyenda, img))
    ancho = max(1100, max(p[2].size[0] for p in paneles) + 20)
    bloques = []
    for titulo, leyenda, img in paneles:
        lineas = textwrap.wrap(leyenda, width=max(40, int(ancho / 7)))
        bloques.append((titulo, lineas, img, 26 + 16 * len(lineas) + img.size[1] + 14))
    cab = 64
    total = Image.new('RGB', (ancho, cab + sum(b[3] for b in bloques)), (255, 255, 255))
    D = ImageDraw.Draw(total)
    D.text((10, 8), 'P3 dimensiones mm - control de bornes (%d puntos)' % len(salida['puntos']), fill=(0, 0, 0), font=fuente_t)
    D.text((10, 32), 'Circulo = radio del borne.  Rojo: confianza alta, naranja: media, violeta: baja.  "!" = dos cables '
                     'distintos en la misma boca.  Verde: cuerpo ubicado por sus medidas en mm.', fill=(60, 60, 60), font=fuente)
    yy = cab
    for titulo, lineas, img, h in bloques:
        D.text((10, yy + 4), titulo, fill=(0, 0, 0), font=fuente_t)
        for i, l in enumerate(lineas):
            D.text((10, yy + 26 + 16 * i), l, fill=(0, 100, 0), font=fuente)
        total.paste(img, (10, yy + 26 + 16 * len(lineas)))
        yy += h
    total.save(ruta)


def dibujar_general(pdf, idx, salida, region, ruta, k=3.0):
    """Vista de toda la bandeja con los cuerpos y los bornes (sin rotulos)."""
    from PIL import ImageDraw
    pts = salida['puntos']
    if region:
        x0, y0, x1, y1 = region
    else:
        x0 = min(p['x'] for p in pts) - 30; x1 = max(p['x'] for p in pts) + 30
        y0 = min(p['y'] for p in pts) - 30; y1 = max(p['y'] for p in pts) + 30
    img = _render(pdf, idx, x0, y0, x1, y1, k)
    d = ImageDraw.Draw(img)
    X = lambda x: (x - x0) * k
    Y = lambda y: (y1 - y) * k
    for g in salida['componentes'].values():
        for c in (g or {}).get('cuerpos', []):
            d.rectangle((X(c['x0']), Y(c['y1']), X(c['x1']), Y(c['y0'])), outline=(0, 150, 0), width=2)
    for p in pts:
        cl = COLORES.get(p['confianza'], COLORES['alta'])
        cx, cy, r = X(p['x']), Y(p['y']), max(2.5, (p.get('r') or 0.5) * k)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=cl, width=2)
    img.save(ruta)


if __name__ == '__main__':
    main()
