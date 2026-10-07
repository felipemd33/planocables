"""Puentes (PLAN_MODULAR.md, 2.4): los modulos viejos de programa/ siguen dando, con el mismo nombre, todo lo que usan
la web, las pruebas, los prototipos y los scripts de '2 - Resultados'. No escribe nada en el repo (la web se importa con
un historial temporal). Termina con error si algo falla.
uso: python pruebas/probar_puentes.py [-v]
  A. nombres: busca (con ast) en programa/, pruebas/, prototipos/ y '2 - Resultados/' cada 'from <modulo viejo> import X',
     cada '<modulo viejo>.X' (tambien con alias: 'import instructivo as I' -> I.X) y '__import__("<modulo>").X', y
     verifica que X siga existiendo. Una variable que se llama como un modulo ('topo = lay.get(...)') no cuenta.
  B. lo movido a planocables.base: el nombre viejo es EL MISMO objeto que el de base (no una copia), y
     instructivo.cable_desc conserva su firma (res, num, e, e2=None).
  C. PDFIUM_LOCK es uno solo: el de planocables.base.pdfium_lock es el de ocr_raster, eplan, web y bornes.motor."""
import os, sys, ast, inspect, importlib, shutil, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROG = os.path.join(RAIZ, 'programa')
CARPETAS = ['programa', 'pruebas', 'prototipos', '2 - Resultados']
sys.stdout.reconfigure(encoding='utf-8')
sys.dont_write_bytecode = True
VERBOSO = '-v' in sys.argv
TMP = tempfile.mkdtemp(prefix='puentes_')
os.environ['PLANOCABLES_HISTORIAL'] = os.path.join(TMP, 'historial')     # (import web: no toca el historial del usuario)
os.environ.setdefault('PLANOCABLES_PORT', '8797')
os.environ.setdefault('PLANOCABLES_MEMORIA_OCR', 'solo-lectura')
sys.path.insert(0, PROG)

VIEJOS = {os.path.splitext(f)[0] for f in os.listdir(PROG) if f.endswith('.py')} | {'bornes'}
BORNES_SUELTOS = {os.path.splitext(f)[0] for f in os.listdir(os.path.join(PROG, 'bornes')) if f.endswith('.py') and f != '__init__.py'}
fallas = []


def chequear(ok, msg):
    print(('  ok    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)
    return ok


def archivos():
    for c in CARPETAS:
        for base, dirs, fs in os.walk(os.path.join(RAIZ, c)):
            dirs[:] = sorted(d for d in dirs if d not in ('__pycache__', 'planocables'))
            for f in sorted(fs):
                if f.endswith('.py'):
                    yield os.path.join(base, f)


def modulo_viejo(nombre, carpeta):
    """'core' -> 'core'; 'motor' (con programa/bornes en sys.path) -> 'bornes.motor'; None si no es un modulo viejo o si
    hay un modulo propio con ese nombre al lado del script (prototipos/P6_ductos_rieles/app.py)"""
    top = nombre.split('.')[0]
    if os.path.exists(os.path.join(carpeta, top + '.py')) and os.path.abspath(carpeta) != os.path.abspath(PROG):
        if os.path.abspath(carpeta) != os.path.abspath(os.path.join(PROG, 'bornes')):
            return None
    if top in VIEJOS:
        return nombre
    if top in BORNES_SUELTOS:
        return 'bornes.' + nombre
    return None


class Ambito:
    def __init__(self, padre):
        self.padre, self.mods, self.otros, self.globales = padre, {}, set(), set()


def ligaduras(nodos, amb, carpeta, paquete):
    """nombres ligados en un ambito (sin entrar a las funciones / clases de adentro): imports de modulos viejos aparte"""
    pila = list(nodos)
    while pila:
        n = pila.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            amb.otros.add(n.name)
            pila.extend(n.decorator_list)
            continue
        if isinstance(n, ast.Lambda):
            continue
        if isinstance(n, ast.Global):
            amb.globales.update(n.names)
        elif isinstance(n, ast.Import):
            for a in n.names:
                m = modulo_viejo(a.name, carpeta)
                if a.asname:
                    (amb.mods.__setitem__(a.asname, m) if m else amb.otros.add(a.asname))
                else:
                    top = a.name.split('.')[0]
                    (amb.mods.__setitem__(top, modulo_viejo(top, carpeta)) if m else amb.otros.add(top))
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                amb.otros.add(a.asname or a.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            amb.otros.add(n.id)
        elif isinstance(n, ast.arg):
            amb.otros.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            amb.otros.add(n.name)
        elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name:
            amb.otros.add(n.name)
        pila.extend(ast.iter_child_nodes(n))
    amb.otros -= amb.globales


def resolver(nombre, amb):
    while amb is not None:
        if nombre in amb.globales:
            while amb.padre is not None:
                amb = amb.padre
            continue
        if nombre in amb.otros:
            return None
        if nombre in amb.mods:
            return amb.mods[nombre]
        amb = amb.padre
    return None


def usos(path):
    """[(modulo, nombre, linea)] de un archivo"""
    carpeta = os.path.dirname(path)
    paquete = 'bornes' if os.path.abspath(carpeta) == os.path.abspath(os.path.join(PROG, 'bornes')) else None
    arbol = ast.parse(open(path, encoding='utf-8-sig').read(), path)
    out = []

    def recorrer(nodo, amb):
        cuerpo = ([nodo.args] if hasattr(nodo, 'args') and isinstance(nodo.args, ast.arguments) else []) + \
                 (nodo.body if isinstance(nodo.body, list) else [nodo.body])
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.Module)):
            amb = Ambito(amb)
            ligaduras(cuerpo, amb, carpeta, paquete)
        pila = list(cuerpo)
        while pila:
            n = pila.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                recorrer(n, amb); continue
            if isinstance(n, ast.ClassDef):
                pila.extend(n.body); continue
            if isinstance(n, ast.ImportFrom):
                if n.level and paquete:
                    m = '.'.join([paquete] + ([n.module] if n.module else []))
                else:
                    m = modulo_viejo(n.module or '', carpeta) if not n.level else None
                if m:
                    out.extend((m, a.name, n.lineno) for a in n.names if a.name != '*')
            elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                m = resolver(n.value.id, amb)
                if m:
                    out.append((m, n.attr, n.lineno))
            elif (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                  and n.value.func.id == '__import__' and n.value.args and isinstance(n.value.args[0], ast.Constant)):
                m = modulo_viejo(str(n.value.args[0].value), carpeta)
                if m:
                    out.append((m, n.attr, n.lineno))
            pila.extend(ast.iter_child_nodes(n))
    recorrer(arbol, None)
    return out


# ------------------------------------------------------------------ A
print('A. nombres de los módulos viejos que se usan en el repo')
todos, ilegibles = {}, []
for p in archivos():
    try:
        for m, x, lin in usos(p):
            todos.setdefault((m, x), []).append(f'{os.path.relpath(p, RAIZ)}:{lin}')
    except (SyntaxError, UnicodeDecodeError, ValueError) as e:
        ilegibles.append(f'{os.path.relpath(p, RAIZ)} ({type(e).__name__})')
if ilegibles:
    print(f'        (no se pudieron leer {len(ilegibles)}: {", ".join(ilegibles[:5])})')
faltan, cargados = [], {}
for (m, x), donde in sorted(todos.items()):
    if m not in cargados:
        try:
            cargados[m] = importlib.import_module(m)
        except Exception as e:                                             # noqa: BLE001
            cargados[m] = e
    mod = cargados[m]
    if isinstance(mod, Exception):
        faltan.append(f'{m}: no se puede importar ({type(mod).__name__}: {mod}) — usado en {donde[0]}')
        continue
    if not hasattr(mod, x):
        try:
            importlib.import_module(f'{m}.{x}')                            # 'from bornes import motor': submodulo
        except ImportError:
            faltan.append(f'{m}.{x} — usado en {", ".join(donde[:3])}' + (f' (y {len(donde) - 3} más)' if len(donde) > 3 else ''))
    if VERBOSO:
        print(f'        {m}.{x}  ({len(donde)})')
for f in faltan:
    print('        FALTA', f)
mods = sorted({m for m, _ in todos})
chequear(not faltan, f'{len(todos)} nombres de {len(mods)} módulos ({", ".join(mods)}) en '
         f'{len({d.split(":")[0] for v in todos.values() for d in v})} archivos: siguen existiendo todos'
         + ('' if not faltan else f' (faltan {len(faltan)}, arriba)'))

# ------------------------------------------------------------------ B
print('B. lo movido a planocables.base es el mismo objeto con el nombre de siempre')
MOVIDOS = {   # modulo viejo: {nombre viejo: 'modulo de base.nombre'}
    'textdec': {'bbox': 'geom.bbox', 'DSU': 'geom.DSU'},
    'wires': {'bbox': 'geom.bbox', 'DSU': 'geom.DSU', 'seglen': 'geom.dist', 'point_seg_dist': 'geom.dist_segmento',
              'box_dist': 'geom.dist_caja', 'inside': 'geom.dentro', 'COLORES': 'colores.COLORES',
              'norm_color': 'colores.norm_color', '_una_letra': 'colores.una_letra'},
    'core': {'SHREF_RE': 'hojas.SHREF_RE', 'H_REF': 'hojas.H_REF', 'natkey': 'hojas.natkey', 'sheet_name': 'hojas.sheet_name',
             'zone_of': 'hojas.zone_of', 'stacked_ref': 'hojas.stacked_ref', 'box_dist': 'geom.dist_caja_bp',
             'near': 'geom.cerca', 'COLOR_EN': 'colores.COLOR_EN', 'norm_color': 'colores.norm_color'},
    'instructivo': {'bbox': 'geom.bbox', 'dist': 'geom.dist', 'box_dist': 'geom.dist_caja', 'SHREF_RE': 'hojas.SHREF_RE',
                    'natk': 'hojas.natk', 'hoja_base': 'hojas.hoja_base', 'ref_apilada': 'hojas.ref_apilada',
                    'COLOR_INI': 'colores.COLOR_INI', 'FIELD_RE': 'convenciones.FIELD_RE',
                    'is_terminal_block': 'convenciones.is_terminal_block', 'norm_label': 'convenciones.norm_label',
                    'fmt_terminal': 'convenciones.fmt_terminal', 'side_of': 'convenciones.side_of',
                    'punta_sintetica': 'convenciones.punta_sintetica'},
    'estacion8': {'e8_clave': 'convenciones.clave_par', 'fmt_terminal': 'convenciones.fmt_terminal', 'natk': 'hojas.natk'},
    'topo': {'bbox': 'geom.bbox', 'DSU': 'geom.DSU', 'rect_of': 'geom.rect_of', 'CLOSE_OPS': 'geom.CLOSE_OPS',
             'RIEL_MM': 'escala.RIEL_MM', 'PT_MM': 'escala.PT_MM', 'ESCALAS': 'escala.ESCALAS',
             'snap_escala': 'escala.snap_escala', 'RX_LATERAL': 'convenciones.LATERAL_RE'},
    'ruteo': {'bbox': 'geom.bbox'},
    'ocr_raster': {'PDFIUM_LOCK': 'pdfium_lock.PDFIUM_LOCK'},
}
distintos = []
for viejo, nombres in MOVIDOS.items():
    mv = importlib.import_module(viejo)
    for n, destino in nombres.items():
        mb, nb = destino.split('.')
        ob = getattr(importlib.import_module(f'planocables.base.{mb}'), nb)
        if getattr(mv, n, None) is not ob:
            distintos.append(f'{viejo}.{n} no es planocables.base.{destino}')
for d in distintos:
    print('        ', d)
chequear(not distintos, f'{sum(len(v) for v in MOVIDOS.values())} nombres en {len(MOVIDOS)} módulos viejos'
         + ('' if not distintos else f' ({len(distintos)} distintos, arriba)'))
import instructivo
chequear(str(inspect.signature(instructivo.cable_desc)) == '(res, num, e, e2=None)',
         f'instructivo.cable_desc{inspect.signature(instructivo.cable_desc)} conserva su firma')

# ------------------------------------------------------------------ C
print('C. un solo candado de PDFium')
from planocables.base.pdfium_lock import PDFIUM_LOCK
import ocr_raster, eplan, web
from bornes import motor
chequear(ocr_raster.PDFIUM_LOCK is PDFIUM_LOCK and eplan.PDFIUM_LOCK is PDFIUM_LOCK and web.PDFIUM_LOCK is PDFIUM_LOCK
         and motor._lock_pdfium() is PDFIUM_LOCK, 'ocr_raster, eplan, web y bornes.motor usan el de planocables.base.pdfium_lock')

shutil.rmtree(TMP, ignore_errors=True)
print()
if fallas:
    print(f'{len(fallas)} FALLA(S):')
    for f in fallas:
        print(' -', f)
    sys.exit(1)
print('TODO OK')
