"""Capas del paquete planocables (PLAN_MODULAR.md, 2.3): que cada parte importe solo lo que le toca, que el nucleo no
toque el disco y que base/ cargue sin las dependencias pesadas. No escribe nada (los subprocesos corren con -B, sin
__pycache__). Termina con error si algo falla.
uso: python pruebas/probar_capas.py
  A. imports (con ast, sin ejecutar): cada capa importa solo las que permite la tabla PUEDE (la del plan); base/ solo la
     biblioteca estandar; ningun archivo de planocables importa un modulo viejo de programa/ (core, wires, textdec,
     pdfvec, ocr_raster, topo, ruteo, eplan, instructivo, estacion8, proyector, bornes, web...) ni toca sys.path; nada de
     imports internos adentro de funciones (los imports tardios solo valen para dependencias pesadas opcionales); Flask
     solo en api/; y sin ciclos entre modulos del paquete.
  B. disco: ningun open( / os.replace / json.dump / shutil... en planocables, salvo en las capas que el plan permite
     (trabajo/ escribe; datos/ solo lee).
  C. sin dependencias pesadas, en subprocesos: con numpy, cv2, pypdf y pypdfium2 bloqueados se importan todos los
     modulos de planocables.base (y ninguno carga un modulo viejo); con numpy y cv2 bloqueados cargan textdec y wires;
     con los cuatro bloqueados cargan instructivo y estacion8, y planocables.producto.
  D. nucleo JS (programa/web/nucleo/*.js, etapa 3): cada archivo corre en Node en un contexto vacio (sin document,
     window, fetch, require ni module) y tambien con require (module.exports)."""
import os, sys, ast, json, subprocess

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROG = os.path.join(RAIZ, 'programa')
PAQ = os.path.join(PROG, 'planocables')
sys.stdout.reconfigure(encoding='utf-8')

# los modulos viejos de programa/ (puentes y adaptadores): nada de planocables los importa
VIEJOS = {os.path.splitext(f)[0] for f in os.listdir(PROG) if f.endswith('.py')} | \
         {d for d in os.listdir(PROG) if os.path.isfile(os.path.join(PROG, d, '__init__.py')) and d != 'planocables'}
# tabla de capas del plan (2.3): capa -> capas internas que puede importar (ademas de si misma)
NUCLEO_ARMADO = {'instructivo', 'estacion8', 'producto', 'proyector'}
PUEDE = {
    '__init__': set(), 'base': set(), 'datos': set(), 'esquemas': set(),
    'pdf': {'base'}, 'ocr': {'base'}, 'shx': {'base'}, 'ruteo': {'base'},
    'funcional': {'base', 'pdf', 'shx'},
    'eplan': {'base', 'pdf'},
    'topografico': {'base', 'pdf', 'shx'},
    'bornes': {'base', 'pdf'},
    'lectura': {'base', 'funcional', 'eplan', 'topografico'},
    **{c: {'base', 'ruteo'} | NUCLEO_ARMADO for c in NUCLEO_ARMADO},       # entre ellos, sin ciclos (se controla abajo)
    'wpc': {'base'}, 'terminales': {'base'}, 'auditoria': {'base'},       # (solo si la otra app resulta Python)
    'exportar': {'base'},
    'trabajo': {'base', 'datos'},
}
TODAS = set(PUEDE) | {'servicio', 'api', '__main__'}
PUEDE['servicio'] = TODAS - {'api', '__main__'}
PUEDE['api'] = PUEDE['__main__'] = {'servicio', 'trabajo', 'datos', 'exportar', 'base'} | NUCLEO_ARMADO
SOLO_ESTANDAR = {'base', 'datos', '__init__'}     # sin bibliotecas de afuera
ESCRIBEN = {'trabajo'}                             # las unicas que escriben archivos (+ herramientas, cuando las haya)
LEEN = {'trabajo', 'datos'}                        # las unicas que abren archivos
FLASK = {'api'}
ESTANDAR = set(sys.stdlib_module_names)

fallas = []


def chequear(ok, msg):
    print(('  ok    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)
    return ok


def archivos():
    for base, dirs, fs in os.walk(PAQ):
        dirs[:] = sorted(d for d in dirs if d != '__pycache__')
        for f in sorted(fs):
            if f.endswith('.py'):
                yield os.path.join(base, f)


def modulo_de(path):
    """'planocables.base.geom' y si es un paquete (__init__)"""
    rel = os.path.relpath(path, PROG)[:-3].replace(os.sep, '.')
    es_paq = rel.endswith('.__init__')
    return (rel[:-9] if es_paq else rel), es_paq


def capa_de(mod):
    """capa de un modulo interno: 'planocables.base.geom' -> 'base'; 'planocables' -> '__init__'"""
    partes = mod.split('.')
    return partes[1] if len(partes) > 1 else '__init__'


class Imports(ast.NodeVisitor):
    """imports de un archivo: (modulo absoluto, nombres, linea, adentro de una funcion), y usos de sys.path / disco"""
    def __init__(self, mod, es_paq):
        self.paquete = mod if es_paq else mod.rpartition('.')[0]
        self.imps, self.syspath, self.disco, self.funcion = [], [], [], 0

    def visit_FunctionDef(self, n):
        self.funcion += 1; self.generic_visit(n); self.funcion -= 1
    visit_AsyncFunctionDef = visit_Lambda = visit_FunctionDef

    def visit_Import(self, n):
        for a in n.names:
            self.imps.append((a.name, [], n.lineno, self.funcion > 0))

    def visit_ImportFrom(self, n):
        if n.level:
            base = self.paquete.split('.')
            base = base[:len(base) - (n.level - 1)]
            mod = '.'.join(base + ([n.module] if n.module else []))
        else:
            mod = n.module or ''
        self.imps.append((mod, [a.name for a in n.names], n.lineno, self.funcion > 0))

    def visit_Attribute(self, n):
        if isinstance(n.value, ast.Name) and n.value.id == 'sys' and n.attr == 'path':
            self.syspath.append(n.lineno)
        self.generic_visit(n)

    def visit_Call(self, n):
        f = n.func
        nombre = (f.id if isinstance(f, ast.Name) else
                  f'{f.value.id}.{f.attr}' if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else
                  f'.{f.attr}' if isinstance(f, ast.Attribute) else '')
        lee = nombre in ('open', 'io.open', 'os.open', 'codecs.open')
        escribe = (nombre in ('os.replace', 'os.rename', 'os.remove', 'os.unlink', 'os.makedirs', 'os.mkdir', 'os.rmdir',
                              'json.dump', 'pickle.dump', 'tempfile.mkstemp', 'tempfile.mkdtemp', 'tempfile.NamedTemporaryFile')
                   or nombre.startswith('shutil.') or nombre in ('.write_text', '.write_bytes', '.touch', '.unlink', '.mkdir'))
        if lee and n.args[1:2]:
            m = n.args[1]
            escribe = escribe or not (isinstance(m, ast.Constant) and isinstance(m.value, str) and not set(m.value) & set('wax+'))
        for k in n.keywords:
            if lee and k.arg == 'mode':
                escribe = escribe or not (isinstance(k.value, ast.Constant) and isinstance(k.value.value, str) and not set(k.value.value) & set('wax+'))
        if lee or escribe:
            self.disco.append((nombre, n.lineno, escribe))
        self.generic_visit(n)


# ------------------------------------------------------------------ A y B
print(f'A. imports de planocables (capas del plan, 2.3)   [{PAQ}]')
if not chequear(os.path.isdir(PAQ), 'existe programa/planocables'):
    sys.exit(1)
MODULOS = {modulo_de(p)[0]: p for p in archivos()}
grafo = {m: set() for m in MODULOS}            # modulo -> modulos del paquete que importa (a nivel de modulo)
problemas_a, problemas_b = [], []
for mod, path in sorted(MODULOS.items()):
    rel = os.path.relpath(path, RAIZ)
    es_paq = path.endswith('__init__.py')
    capa = capa_de(mod)
    try:
        arbol = ast.parse(open(path, encoding='utf-8').read(), path)
    except SyntaxError as e:
        problemas_a.append(f'{rel}: no se puede leer ({e})'); continue
    v = Imports(mod, es_paq); v.visit(arbol)
    if capa not in PUEDE:
        problemas_a.append(f'{rel}: la capa «{capa}» no está en la tabla de capas (agregarla a PUEDE, según el plan)')
        continue
    for m, nombres, lin, tardio in v.imps:
        top = m.split('.')[0]
        if top == 'planocables':
            # 'from planocables.base import geom' importa el submodulo geom; 'from .geom import bbox', el modulo geom
            destinos = [f'{m}.{x}' for x in nombres if f'{m}.{x}' in MODULOS] or [m]
            for d in destinos:
                c = capa_de(d)
                if c not in (capa, '__init__') and c not in PUEDE[capa]:
                    problemas_a.append(f'{rel}:{lin}: la capa «{capa}» no puede importar «{c}» ({d})')
                if tardio:
                    problemas_a.append(f'{rel}:{lin}: import interno adentro de una función ({d}): los imports tardíos solo '
                                       'valen para dependencias pesadas opcionales')
                elif d != mod and d in MODULOS:
                    grafo[mod].add(d)
        elif top in VIEJOS:
            problemas_a.append(f'{rel}:{lin}: importa el módulo viejo «{m}» (nada de planocables importa un puente)')
        elif capa in SOLO_ESTANDAR and top not in ESTANDAR:
            problemas_a.append(f'{rel}:{lin}: «{m}» no es de la biblioteca estándar (la capa «{capa}» usa solo la estándar)')
        elif top == 'flask' and capa not in FLASK:
            problemas_a.append(f'{rel}:{lin}: Flask fuera de api/')
    for lin in v.syspath:
        problemas_a.append(f'{rel}:{lin}: usa sys.path (prohibido dentro de planocables)')
    for nombre, lin, escribe in v.disco:
        if escribe and capa not in ESCRIBEN:
            problemas_b.append(f'{rel}:{lin}: {nombre}(...) escribe en el disco (solo trabajo/ escribe)')
        elif not escribe and capa not in LEEN:
            problemas_b.append(f'{rel}:{lin}: {nombre}(...) abre un archivo (solo datos/ y trabajo/ leen el disco)')

# ciclos entre modulos (imports de nivel de modulo)
def ciclo():
    estado, pila = {}, []
    def dfs(u):
        estado[u] = 1; pila.append(u)
        for w in sorted(grafo[u]):
            if estado.get(w) == 1:
                return pila[pila.index(w):] + [w]
            if not estado.get(w):
                r = dfs(w)
                if r:
                    return r
        estado[u] = 2; pila.pop()
        return None
    for u in sorted(grafo):
        if not estado.get(u):
            r = dfs(u)
            if r:
                return r
    return None

c = ciclo()
for p in problemas_a:
    print('        ', p)
chequear(not problemas_a, f'{len(MODULOS)} archivos: imports según la tabla de capas, sin módulos viejos, sin sys.path, sin imports '
         'internos tardíos' + ('' if not problemas_a else f' ({len(problemas_a)} problema(s), arriba)'))
chequear(c is None, 'sin ciclos entre módulos del paquete' + ('' if c is None else ': ' + ' -> '.join(c)))

print('B. disco: nada lee ni escribe archivos fuera de trabajo/ (y datos/ que lee)')
for p in problemas_b:
    print('        ', p)
chequear(not problemas_b, 'sin open( / os.replace / json.dump / shutil... en el núcleo' + ('' if not problemas_b else f' ({len(problemas_b)}, arriba)'))

# ------------------------------------------------------------------ C
print('C. carga sin las dependencias pesadas (subprocesos)')
VIEJOS_JSON = json.dumps(sorted(VIEJOS))


def sub(bloqueados, codigo):
    pre = (f'import sys, json\nsys.path.insert(0, {PROG!r})\n'
           + ''.join(f'sys.modules[{m!r}] = None\n' for m in bloqueados))
    p = subprocess.run([sys.executable, '-B', '-c', pre + codigo], capture_output=True, cwd=RAIZ,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PLANOCABLES_MEMORIA_OCR='solo-lectura'))
    return p.returncode, (p.stdout + p.stderr).decode('utf-8', 'replace').strip()


cod, out = sub(('numpy', 'cv2', 'pypdf', 'pypdfium2'), f'''
import importlib, pkgutil
import planocables, planocables.base
mods = ['planocables', 'planocables.base'] + [m.name for m in pkgutil.walk_packages(planocables.base.__path__, 'planocables.base.')]
for m in mods:
    importlib.import_module(m)
viejos = sorted(set({VIEJOS_JSON}) & set(sys.modules))
print(json.dumps(dict(mods=mods, viejos=viejos)))
''')
try:
    r = json.loads(out.splitlines()[-1])
    chequear(cod == 0, f"sin numpy, cv2, pypdf ni pypdfium2 cargan los {len(r['mods'])} módulos: {', '.join(m.split('.')[-1] for m in r['mods'])}")
    chequear(not r['viejos'], 'y no cargan ningún módulo viejo' + ('' if not r['viejos'] else f": {', '.join(r['viejos'])}"))
except (ValueError, IndexError, KeyError):
    chequear(False, f'planocables.base sin numpy, cv2, pypdf ni pypdfium2: código {cod}\n{out[-2000:]}')
for bloq, mods in ((('numpy', 'cv2'), ('textdec', 'wires')), (('numpy', 'cv2', 'pypdf', 'pypdfium2'), ('instructivo', 'estacion8')),
                   (('numpy', 'cv2', 'pypdf', 'pypdfium2'), ('planocables.producto',))):
    cod, out = sub(bloq, f'import {", ".join(mods)}\nprint("ok")')
    chequear(cod == 0 and out.endswith('ok'), f'sin {", ".join(bloq)} cargan {" y ".join(mods)}' + ('' if cod == 0 else f'\n{out[-1500:]}'))

# ------------------------------------------------------------------ D
print('D. núcleo JS (programa/web/nucleo/*.js): carga en Node sin DOM')
NUC = os.path.join(PROG, 'web', 'nucleo')
jss = sorted(f for f in os.listdir(NUC) if f.endswith('.js')) if os.path.isdir(NUC) else []
# en un contexto vacío (sin document, window, fetch, require ni module), en el orden de index.html (zip.js antes), y con require
NODE = r'''
const fs = require('fs'), path = require('path'), vm = require('vm');
const dir = process.argv[1], archivos = JSON.parse(process.argv[2]), orden = ['zip.js', ...archivos.filter(a => a !== 'zip.js')];
const ctx = vm.createContext({}), out = {};
for (const a of orden) {
  try { vm.runInContext(fs.readFileSync(path.join(dir, a), 'utf8'), ctx, { filename: a }); out[a] = 'ok'; } catch (e) { out[a] = 'contexto vacío: ' + e.message; continue; }
  try { const m = require(path.join(dir, a)); if (!m || typeof m !== 'object') throw new Error('sin module.exports'); } catch (e) { out[a] = 'require: ' + e.message; }
}
console.log(JSON.stringify(out));
'''
if chequear(jss, f'hay núcleo JS ({", ".join(jss)})'):
    try:
        p = subprocess.run(['node', '-e', NODE, NUC, json.dumps(jss)], capture_output=True, text=True, encoding='utf-8', timeout=60)
        r = json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 and p.stdout.strip() else {}
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        p, r = None, {'node': str(e)}
    malos = {k: v for k, v in r.items() if v != 'ok'}
    chequear(set(r) == set(jss) and not malos, 'cada uno corre en un contexto vacío de Node y con require'
             + ('' if not malos and set(r) == set(jss) else f': {malos or (p.stderr[-800:] if p else r)}'))

print()
if fallas:
    print(f'{len(fallas)} FALLA(S):')
    for f in fallas:
        print(' -', f.splitlines()[0])
    sys.exit(1)
print('TODO OK')
