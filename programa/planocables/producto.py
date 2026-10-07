"""Producto del tablero (PLAN_MODULAR 5.1): el CODIGO DE PRODUCTO SAP con su sufijo (75286-1), y el plano funcional y
el topografico con su revision (75287 rev 6, 75441 rev 6). Solo biblioteca estandar y sin disco: recibe lo que ya leyo
el programa (los renglones decodificados de cada hoja, el /Title del PDF, el nombre del archivo, el rotulo de EPLAN);
el catalogo (programa/productos.json) y lo confirmado a mano en el trabajo (producto.json) llegan como argumentos.

  producto_del_plano(paginas, titulo_pdf, nombre_archivo, eplan=None) -> lo detectado en el funcional
  topografico_del_pdf(titulo_pdf, nombre_archivo)                     -> {numero, revision, fuente}
  combinar(detectado, topografico, catalogo, confirmado)              -> ins['producto'] (la estructura de 5.1)
  hay_que_preguntar(producto)                                         -> si el asistente de la web pregunta (una vez)

De donde sale cada dato (de mayor a menor):
  codigo  1) confirmado a mano en el trabajo (producto.json); 2) alias del catalogo: plano funcional, documento o
          codigo del rotulo; 3) CODE: / CODIGO: del rotulo (confianza alta si es el mismo en 2 hojas o mas);
          4) EPLAN: «Conjunto NNNNN-N» de la portada, solo como sugerencia (en el PAE dice 76860-1 y el producto es
          76857-1); 5) el nombre del archivo. El «Code: 2344» del rotulo de EPLAN no es un codigo SAP: no se lee.
  plano y revision  1) el /Title del PDF; 2) el rotulo: DOC NUMBER / N° DE DOC y GRAL REV / REV. GRAL / REV: del
          renglon del documento; 3) el nombre del archivo. En EPLAN, documento y revision del rotulo (eplan.documento).
          Si dos fuentes no coinciden: aviso (el rotulo del 76740 dice 75877).
  El numero largo de SAP se normaliza con 5?0{9,}(\\d{5}): 50000000000000075287 -> 75287. Las revisiones son texto
  ('0A', '4(A)')."""
import collections
import re

CODIGO_RE = re.compile(r'(?<![\d-])(\d{5}-\d{1,2})(?!\d)')                  # 75286-1, 76343-7
LARGO_RE = re.compile(r'5?0{9,}(\d{5})(?!\d)')                              # 50000000000000075287 -> 75287
NUMERO_RE = re.compile(r'(?<!\d)(\d{5})(?!\d|-\d)')                         # 75287 (75286-1 es un codigo, no un plano)
REV_RE = re.compile(r'(?<![a-z])rev\.?\s*-?\s*(\d{1,2}[a-z]?(?:\s*\(\s*[a-z0-9]{1,2}\s*\))?)(?![a-z0-9])', re.I)
REV_VALOR = re.compile(r'\d{1,2}[A-Z]?(?:\([A-Z0-9]{1,2}\))?')               # revision suelta del rotulo: 6, 0A, 4(A)
CONJUNTO_RE = re.compile(r'conjunto\s*(\d{5}-\d{1,2})(?!\d)', re.I)          # portada: 'Diagrama ... Conjunto 76860-1'
# rotulos del cajetin (AutoCAD): el valor va en el mismo renglon o en el texto que sigue a la derecha
ROT_CODIGO = re.compile(r'(?:CODE|C[ÓO]DIGO)\s*:\s*(.*)', re.I)
ROT_DOC = re.compile(r'(?:DOC(?:UMENT)?\.?\s*NUMBER|N\s*[°ºO]?\s*DE\s*DOC(?:UMENTO)?\.?)\s*:\s*(.*)', re.I)
ROT_GRAL = re.compile(r'(?:GRAL\.?\s*REV|REV\.?\s*GRAL|GRAL)\s*[.:]\s*(.*)', re.I)      # 'REV.' + 'GRAL:' sale partido
ROT_REV = re.compile(r'REV(?:ISI[ÓO]N)?\s*[.:]\s*(.*)', re.I)
ROTULO = re.compile(r'[A-ZÁÉÍÓÚÑ°º. ]{2,}:', re.I)                            # otro rotulo ('TITLE:'): el campo esta vacio

FUENTES = {'titulo_pdf': 'título del PDF', 'rotulo': 'rótulo', 'archivo': 'nombre del archivo', 'portada': 'portada',
           'catalogo': 'catálogo de productos', 'confirmado': 'confirmado a mano', 'mismo_pdf': 'mismo PDF'}


def codigo_valido(c):
    """'75286-1': numero SAP de 5 cifras y sufijo"""
    return isinstance(c, str) and bool(re.fullmatch(r'\d{5}-\d{1,2}', c.strip()))


def norm_rev(r):
    """revision para comparar: sin espacios, en mayusculas y sin ceros adelante ('06' = '6'; '0A' no es '0')"""
    if r is None:
        return None
    s = re.sub(r'\s+', '', str(r)).upper()
    m = re.match(r'0*(\d+)(.*)$', s)
    return (str(int(m.group(1))) + m.group(2)) if m else (s or None)


def nucleo(numero):
    """las 5 cifras del plano para comparar: 'ZPL-76884' -> '76884', '50000000000000075287 ZPL' -> '75287'"""
    if not numero:
        return None
    s = str(numero)
    m = LARGO_RE.search(s) or NUMERO_RE.search(s)
    return m.group(1) if m else s.strip().upper()


def de_texto(t):
    """(numero de plano, revision, codigo de producto) de un /Title o de un nombre de archivo"""
    t = re.sub(r'\.pdf\s*$', '', str(t or '').strip(), flags=re.I)
    m = LARGO_RE.search(t) or NUMERO_RE.search(t)
    r = REV_RE.search(t)
    c = CODIGO_RE.search(t)
    return (m.group(1) if m else None, re.sub(r'\s+', '', r.group(1)).upper() if r else None, c.group(1) if c else None)


# ------------------------------------------------------------------ rotulo del cajetin (AutoCAD)
def _horizontales(p):
    return [l for l in (p.get('lines') or []) if l.get('bbox') and l.get('ang', 0) in (0, None) and str(l.get('text', '')).strip()]


def _cajetin(p):
    return p.get('cajetin') or (p.get('meta') or {}).get('cajetin')


def _alto(l):
    b = l['bbox']
    return max(1.0, l.get('H') or (b[3] - b[1]))


def _a_la_derecha(lab, lineas):
    """los textos del mismo renglon a la derecha del rotulo, del mas cercano al mas lejano (hasta 40 alturas de letra)"""
    b, h = lab['bbox'], _alto(lab)
    cy = (b[1] + b[3]) / 2
    out = [l for l in lineas if l is not lab and abs((l['bbox'][1] + l['bbox'][3]) / 2 - cy) <= max(1.5, 0.6 * h)
           and l['bbox'][0] >= b[2] - 0.5 * h and l['bbox'][0] - b[2] <= 40 * h]
    return sorted(out, key=lambda l: l['bbox'][0])


def _valor(lab, m, lineas):
    """el valor de un rotulo: lo que sigue en el mismo texto ('CÓDIGO: 66817-1') o el texto de al lado; None si el
    campo esta vacio (lo que sigue es otro rotulo, como 'TITULO:')"""
    resto = m.group(1).strip()
    if resto:
        return resto
    der = _a_la_derecha(lab, lineas)
    if not der:
        return None
    t = der[0]['text'].strip()
    return None if ROTULO.fullmatch(t) or ROTULO.match(t) and t.endswith(':') else t


def _rotulos(lineas, rx, caj):
    """(linea, match) de los rotulos de ese tipo; si hay cajetin, los de adentro mandan sobre los sueltos en la hoja"""
    out = [(l, m) for l in lineas for m in [rx.fullmatch(l['text'].strip())] if m]
    if caj and out:
        adentro = [(l, m) for l, m in out if caj[0] - 20 <= (l['bbox'][0] + l['bbox'][2]) / 2 <= caj[2] + 20
                   and caj[1] - 20 <= (l['bbox'][1] + l['bbox'][3]) / 2 <= caj[3] + 20]
        out = adentro or out
    return out


def rotulo_hoja(p):
    """{codigo, numero, revision} del cajetin de una hoja (lo que no esta, None)"""
    lineas = _horizontales(p)
    caj = _cajetin(p)
    out = dict(codigo=None, numero=None, revision=None)
    for lab, m in _rotulos(lineas, ROT_CODIGO, caj):
        v = _valor(lab, m, lineas)
        c = CODIGO_RE.search(v or '')
        if c:
            out['codigo'] = c.group(1)
            break
    docs = _rotulos(lineas, ROT_DOC, caj)
    for lab, m in docs:
        n = nucleo(_valor(lab, m, lineas))
        if n and re.fullmatch(r'\d{5}', n):
            out['numero'] = n
            break
    revs = [(lab, m) for lab, m in _rotulos(lineas, ROT_GRAL, caj)]
    if not revs:
        # sin 'GRAL REV': el 'REV:' del renglon del documento (76739: DOC NUMBER: 76739 ZPL ... REV: 4); el 'REV:' de
        # abajo a la derecha, con el numero debajo, es la revision de la hoja
        filas = [(d['bbox'][1] + d['bbox'][3]) / 2 for d, _ in docs]
        revs = [(lab, m) for lab, m in _rotulos(lineas, ROT_REV, caj)
                if any(abs((lab['bbox'][1] + lab['bbox'][3]) / 2 - y) <= max(1.5, 0.6 * _alto(lab)) for y in filas)]
    for lab, m in revs:
        v = re.sub(r'\s+', '', _valor(lab, m, lineas) or '').upper()
        if REV_VALOR.fullmatch(v):
            out['revision'] = v
            break
    return out


def _mas_comun(cont):
    return cont.most_common(1)[0][0] if cont else None


# ------------------------------------------------------------------ deteccion
def producto_del_plano(paginas, titulo_pdf=None, nombre_archivo=None, eplan=None):
    """lo que dice el plano funcional sobre el producto.
    paginas: las hojas leidas (res.pages: 'lines' con 'text' y 'bbox', y el cajetin en 'cajetin' o en meta['cajetin']).
    eplan: {documento, revision} del rotulo de EPLAN (None en AutoCAD)."""
    paginas = list(paginas or [])
    avisos = []
    tit_n, tit_r, tit_c = de_texto(titulo_pdf)
    arc_n, arc_r, arc_c = de_texto(nombre_archivo)
    codigos, numeros, revisiones = collections.Counter(), collections.Counter(), collections.Counter()
    if not eplan:
        for p in paginas:
            r = rotulo_hoja(p)
            if r['codigo']:
                codigos[r['codigo']] += 1
            if r['numero']:
                numeros[r['numero']] += 1
            if r['revision']:
                revisiones[r['revision']] += 1
    # portada: 'Conjunto NNNNN-N' en las dos primeras hojas (solo sugerencia)
    portada = None
    for p in paginas[:2]:
        for l in p.get('lines') or []:
            m = CONJUNTO_RE.search(str(l.get('text', '')).replace(' ', ''))
            if m:
                portada = m.group(1)
                break
        if portada:
            break
    rot_c = _mas_comun(codigos)
    if len(codigos) > 1:
        avisos.append('El rótulo trae más de un código de producto: ' +
                      ', '.join(f'{c} ({n} hoja{"s" if n > 1 else ""})' for c, n in codigos.most_common()))
    if eplan:
        rot_n, rot_r = eplan.get('documento'), eplan.get('revision')
    else:
        rot_n, rot_r = _mas_comun(numeros), _mas_comun(revisiones)
    # plano y revision: en EPLAN el documento del rotulo ('ZPL-76884'); en AutoCAD el /Title, el rotulo y el archivo
    orden_n = ([('rotulo', rot_n)] if eplan else []) + [('titulo_pdf', tit_n), ('rotulo', rot_n), ('archivo', arc_n)]
    orden_r = ([('rotulo', rot_r)] if eplan else []) + [('titulo_pdf', tit_r), ('rotulo', rot_r), ('archivo', arc_r)]
    fn, numero = next(((f, v) for f, v in orden_n if v), (None, None))
    fr, revision = next(((f, v) for f, v in orden_r if v), (None, None))
    fun = dict(numero=numero, revision=str(revision) if revision is not None else None, fuente=fn)
    if fr and fr != fn:
        fun['fuente_revision'] = fr
    vistos_n = [(f, v) for f, v in (('titulo_pdf', tit_n), ('rotulo', rot_n), ('archivo', arc_n)) if v]
    if len({nucleo(v) for _, v in vistos_n}) > 1:
        avisos.append('El número de plano no coincide: ' + ', '.join(f'{FUENTES[f]} {v}' for f, v in vistos_n))
    vistos_r = [(f, v) for f, v in (('titulo_pdf', tit_r), ('rotulo', rot_r), ('archivo', arc_r)) if v]
    if len({norm_rev(v) for _, v in vistos_r}) > 1:
        avisos.append('La revisión no coincide: ' + ', '.join(f'{FUENTES[f]} {v}' for f, v in vistos_r))
    if rot_c and arc_c and rot_c != arc_c:
        avisos.append(f'El rótulo dice el código {rot_c} y el nombre del archivo {arc_c}')
    return dict(
        funcional=fun,
        codigo=dict(rotulo=rot_c, hojas=codigos.get(rot_c, 0) if rot_c else 0, portada=portada, archivo=arc_c),
        fuentes=dict(titulo_pdf=dict(texto=titulo_pdf or None, numero=tit_n, revision=tit_r),
                     rotulo=dict(numero=rot_n, revision=rot_r, hojas=len(paginas)),
                     archivo=dict(texto=nombre_archivo or None, numero=arc_n, revision=arc_r)),
        eplan=bool(eplan), avisos=avisos)


def topografico_del_pdf(titulo_pdf=None, nombre_archivo=None):
    """{numero, revision, fuente} del topografico: su /Title (el rotulo solo se decodifica en la hoja de la bandeja) y
    el nombre del archivo; 'avisos' si no coinciden"""
    tn, tr, _ = de_texto(titulo_pdf)
    an, ar, _ = de_texto(nombre_archivo)
    out = dict(numero=tn or an, revision=tr or ar, fuente='titulo_pdf' if tn else ('archivo' if an else None))
    avisos = []
    if tn and an and tn != an:
        avisos.append(f'Topográfico: el título del PDF dice {tn} y el nombre del archivo {an}')
    if tr and ar and norm_rev(tr) != norm_rev(ar):
        avisos.append(f'Topográfico: la revisión del título del PDF es {tr} y la del nombre del archivo {ar}')
    if avisos:
        out['avisos'] = avisos
    return out


# ------------------------------------------------------------------ catalogo y combinacion
def productos_de(catalogo):
    """{codigo: {nombre, alias: {planos, documentos, codigo_rotulo}}} del catalogo (con o sin la envoltura 'productos')"""
    if not isinstance(catalogo, dict):
        return {}
    p = catalogo.get('productos') if isinstance(catalogo.get('productos'), dict) else catalogo
    return {k: v for k, v in p.items() if codigo_valido(k) and isinstance(v, dict)}


def _alias(e, k):
    a = (e.get('alias') or {}).get(k) or []
    return [str(x).strip() for x in (a if isinstance(a, list) else [a]) if str(x).strip()]


def buscar_en_catalogo(catalogo, numero=None, documento=None, codigos_plano=(), avisos=None):
    """(codigo, entrada, por) del producto del catalogo que tiene como alias el plano funcional, el documento o el
    codigo que dice el plano (rotulo o portada); None si no esta. Dos productos con el mismo alias: aviso y no se elige."""
    prods = productos_de(catalogo)
    pruebas = [('plano', lambda e: nucleo(numero) and nucleo(numero) in {nucleo(x) for x in _alias(e, 'planos')}),
               ('documento', lambda e: documento and str(documento).strip().upper() in {x.upper() for x in _alias(e, 'documentos')}),
               ('codigo_rotulo', lambda e: any(c and c in _alias(e, 'codigo_rotulo') for c in codigos_plano))]
    for por, ok in pruebas:
        hay = [(c, e) for c, e in prods.items() if ok(e)]
        if len(hay) == 1:
            return hay[0][0], hay[0][1], por
        if len(hay) > 1 and avisos is not None:
            avisos.append(f'El catálogo de productos tiene el mismo {por.replace("_", " ")} en {" y ".join(c for c, _ in hay)}: confirmá cuál es')
    return None


def combinar(detectado, topografico=None, catalogo=None, confirmado=None):
    """ins['producto']: {codigo, nombre, funcional, topografico, codigo_rotulo, documento, revision, confirmado,
    confianza, fuente, avisos}. 'documento' y 'revision' quedan por compatibilidad (wpc.json -> reemplazos[documento],
    mapeos verificados): en EPLAN el documento del rotulo ('ZPL-76884', '1'); en AutoCAD el plano funcional y su revision.
    confirmado: el producto.json del trabajo ({codigo, nombre}) o None."""
    d = detectado or {}
    f = d.get('funcional') or {}
    fun = dict(numero=f.get('numero'), revision=f.get('revision'), fuente=f.get('fuente'))
    if f.get('fuente_revision'):
        fun['fuente_revision'] = f['fuente_revision']
    t = dict(topografico or {})
    avisos = list(d.get('avisos') or []) + list(t.pop('avisos', None) or [])
    top = dict(numero=t.get('numero'), revision=t.get('revision'), fuente=t.get('fuente'),
               **{k: v for k, v in t.items() if k not in ('numero', 'revision', 'fuente')})
    cod = d.get('codigo') or {}
    rot, portada, arc = cod.get('rotulo'), cod.get('portada'), cod.get('archivo')
    prods = productos_de(catalogo)
    cat = buscar_en_catalogo(catalogo, fun['numero'], fun['numero'], [rot, portada], avisos)
    conf = confirmado if isinstance(confirmado, dict) and codigo_valido(confirmado.get('codigo')) else None
    nombre = None
    if conf:
        codigo, fuente, confianza = conf['codigo'].strip(), 'confirmado', 'alta'
        nombre = (conf.get('nombre') or '').strip() or None
    elif cat:
        codigo, fuente, confianza = cat[0], 'catalogo', 'alta'
        if rot and rot != codigo and rot not in _alias(cat[1], 'codigo_rotulo'):
            avisos.append(f'El rótulo dice el código {rot} y el catálogo tiene este plano como {codigo}')
    elif rot:
        codigo, fuente, confianza = rot, 'rotulo', ('alta' if (cod.get('hojas') or 0) >= 2 else 'media')
    elif portada:
        codigo, fuente, confianza = portada, 'portada', 'baja'
    elif arc:
        codigo, fuente, confianza = arc, 'archivo', 'baja'
    else:
        codigo, fuente, confianza = None, None, 'baja'
    if not nombre and codigo in prods:
        nombre = (prods[codigo].get('nombre') or '').strip() or None
    # el topografico es de otro producto del catalogo (se cargo el de otro tablero)
    if top['numero'] and codigo and not top.get('mismo_pdf'):
        otros = [c for c, e in prods.items() if c != codigo and nucleo(top['numero']) in {nucleo(x) for x in _alias(e, 'planos')}]
        if otros and nucleo(top['numero']) not in {nucleo(x) for x in _alias(prods.get(codigo) or {}, 'planos')}:
            avisos.append(f'El topográfico {top["numero"]} es del producto {" / ".join(otros)} según el catálogo')
    return dict(codigo=codigo, nombre=nombre, funcional=fun, topografico=top, codigo_rotulo=rot or portada,
                documento=fun['numero'], revision=fun['revision'], confirmado=fuente in ('confirmado', 'catalogo'),
                confianza=confianza, fuente=fuente, avisos=list(dict.fromkeys(avisos)))


def hay_que_preguntar(producto):
    """el asistente pregunta (una sola vez) si el producto no esta confirmado y la deteccion no es segura o las
    fuentes no coinciden"""
    p = producto or {}
    return not p.get('confirmado') and (p.get('confianza') != 'alta' or bool(p.get('avisos')))


def sugerencias(producto, catalogo=None):
    """codigos para elegir en la pantalla: [{codigo, nombre, de}] (lo detectado primero, despues el catalogo)"""
    p = producto or {}
    cod = ((p.get('detectado') or {}).get('codigo')) or {}
    prods = productos_de(catalogo)
    out, vistos = [], set()

    def sumar(c, de):
        if codigo_valido(c) and c not in vistos:
            vistos.add(c)
            out.append(dict(codigo=c, nombre=(prods.get(c) or {}).get('nombre'), de=de))
    sumar(p.get('codigo'), FUENTES.get(p.get('fuente'), p.get('fuente') or ''))
    sumar(cod.get('rotulo'), 'rótulo')
    sumar(cod.get('portada'), 'portada')
    sumar(cod.get('archivo'), 'nombre del archivo')
    for c in sorted(prods):
        sumar(c, 'catálogo')
    return out
