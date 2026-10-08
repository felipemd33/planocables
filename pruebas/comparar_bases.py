"""Compara las salidas de la bateria B contra las bases (red de seguridad del plan modular, etapa 0).
uso: python pruebas/comparar_bases.py <dir_salidas> [--bases pruebas/bases] [--max N] [--tol T]
     python pruebas/comparar_bases.py <dirA> --entre <dirB> [--max N] [--tol T]
  <dir_salidas>: la carpeta donde quedaron las salidas de una corrida.
    - salida_<t>.json (volcar_trabajo.py) contra la base de su trabajo (BASES; el TPT contra base_tpt_ronda3.json).
      Se comparan TODAS las claves de primer nivel que trae la base (una base vieja, como la del 75287, no tiene
      'puntas' ni 'mapeo': esas no se comparan) y, adentro de cada una, todo. Si falta una salida_<t>.json: FALLA.
    - listado_<t>.json, layout_<t>.json, e8_<t>.json, ins_<t>.json (volcar_bases_nuevas.py): se compara todo, si el
      archivo esta en las dos carpetas (si esta en una sola, se avisa y no cuenta como falla).
  --entre <dirB>: compara todos los .json del mismo nombre de dos corridas (ej. PYTHONHASHSEED=0 contra =1), enteros.
  --max N: cuantas diferencias se muestran por archivo (12). --tol T: tolerancia para los numeros (0 = exactos).
  --estricto: las diferencias CONOCIDAS de las bases viejas (ver abajo) tambien cuentan como falla.
  Se ignoran los campos que cambian solos de una corrida a otra (IGNORAR, a cualquier profundidad).
  Las diferencias CONOCIDAS (bases viejas contra el codigo de la etapa 0, que no cambian resultados) estan fijadas con
  su valor exacto: se muestran, no cuentan, y si cambian otra vez o aparece otra, es FALLA. Las bases no se tocan.
  Las listas se comparan en orden (el orden de las lineas es el orden de cableado): si tienen los mismos elementos en
  otro orden, se dice asi.
  Muestra las primeras diferencias con su ruta (ej. lineas[12].origen). Termina con 0 si todo da igual y 1 si no."""
import os, sys, json, glob, collections

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# base de cada trabajo (salida_<t>.json contra esta)
BASES = {'75287': 'base_75287.json', '66817': 'base_66817.json', '76884': 'base_76884.json', 'tpt': 'base_tpt_ronda3.json',
         # el TPT del usuario con su constructivo 72715-1 (desde 2026-10-08; base sacada con el codigo de d12fa6d, antes
         # de la etapa E8-1: E6 no cambia)
         'tpt_constructivo': 'base_tpt_constructivo.json'}
# bases nuevas (volcar_bases_nuevas.py): <prefijo>_<t>.json
PREFIJOS = ('listado', 'layout', 'e8', 'ins')

# campos que cambian solos de una corrida a otra: se ignoran con ese nombre en CUALQUIER nivel
IGNORAR = {
    'segundos',        # tiempo de la corrida (volcar_trabajo, mapeo.segundos, estado del trabajo)
    'segundos_cache',  # tiempo de leer bornes_auto.json
    'tiempos',         # volcar_trabajo: funcional / mapeo / total
    'de_cache',        # mapeo.de_cache: depende de --sin-cache y de si habia bornes_auto.json
    'stats',           # conteos del decodificador SHX (dict / ocr / memoria): dependen de la memoria OCR
    'generado',        # fecha y hora en que se armo el instructivo
    'fecha', 'creado', 'ts', '_ts', 'inicio', 'transcurrido',   # fechas y horas (estado del trabajo, auditoria.inicio)
    'log',             # mensajes de progreso de la lectura
}

FALTA = object()

# Diferencias CONOCIDAS entre una base vieja y el codigo de la etapa 0 (2026-10-07), que no son cambios de resultado.
# Las bases no se tocan: cada diferencia queda fijada con el valor exacto de la base y el de hoy (si cambia otra vez, o
# aparece otra, es FALLA). Se muestran en cada corrida; con --estricto cuentan como falla.
_LI = lambda x, t: {'fila': None, 'leido': t, 'ubic': 'LI', 'x': x}
CONOCIDAS = {
    # base_75287.json se saco antes de los arreglos del topografico de la ronda 2 (etiquetas partidas '1' + '3F3',
    # solenoides SP-n); el layout.json del trabajo es de otra version del lector y volcar_trabajo lo vuelve a leer.
    # El contrato del 75287 (CLAUDE.md) son lineas, pendientes, sueltos, otra estacion y extremos: dan IGUAL.
    '75287': [('layout.comp.12PS2', _LI(245.7, '12PS2'), FALTA),
              ('layout.comp.13F3.leido', '3F3', '13F3'), ('layout.comp.12F1.leido', '2F1', '12F1'),
              ('layout.comp.13X24.leido', '3X24', '13X24'), ('layout.comp.13XC1.leido', '3XC1', '13XC1'),
              ('layout.comp.12XPS.leido', '2XPS', '12XPS'),
              ('layout.comp.SP-1', FALTA, _LI(727.7, 'SP-1')), ('layout.comp.SP-2', FALTA, _LI(763.2, 'SP-2')),
              ('layout.comp.11XP', FALTA, _LI(276.7, '11XP'))],
    # version del motor de bornes (bornes/motor.py VERSION), subida a 2026.10.07-1 en 93d7947 y a 2026.10.07-4 en
    # 6322435 (bornera en columna al frente, zona segura con aparatos, rieles en otra capa) sin regenerar la base del
    # 66817: sus puntos, puntas y lineas dan iguales. (La del TPT, base_tpt_ronda3.json, ya se regenero en 6322435 con
    # 2026.10.07-4: no tiene diferencia conocida.)
    '66817': [('mapeo.version', '2026.10.02-3', '2026.10.07-4')],
}
ETIQ = ['base', 'salida']                     # como se llaman los dos lados en los mensajes (--entre: A / B)


def clave_dif(r, a, b):
    c = lambda x: '<no está>' if x is FALTA else json.dumps(x, sort_keys=True, ensure_ascii=False)
    return r, c(a), c(b)


def separar_conocidas(difs, t):
    """(difs sin las conocidas de ese trabajo, cuantas conocidas aparecieron, conocidas que ya no aparecen)"""
    con = {clave_dif(*x): x for x in CONOCIDAS.get(t, [])}
    vistas = {clave_dif(r, a, b) for r, que, a, b in difs} & set(con)
    return [d for d in difs if clave_dif(d[0], d[2], d[3]) not in con], len(vistas), [con[k][0] for k in con if k not in vistas]


def limpiar(x):
    """x sin los campos de IGNORAR (para comparar elementos enteros de una lista)"""
    if isinstance(x, dict):
        return {k: limpiar(v) for k, v in x.items() if k not in IGNORAR}
    if isinstance(x, list):
        return [limpiar(v) for v in x]
    return x


def canon(x):
    return json.dumps(limpiar(x), sort_keys=True, ensure_ascii=False)


def corto(x, n=110):
    if x is FALTA:
        return '(no está)'
    s = json.dumps(x, ensure_ascii=False, sort_keys=True)
    return s if len(s) <= n else s[:n - 1] + '…'


def iguales(a, b, tol):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b or abs(a - b) <= tol
    return type(a) is type(b) and a == b


def comparar(a, b, ruta, difs, tol, solo_claves_de_a=False):
    """a = base (o corrida A), b = salida. Agrega a 'difs' tuplas (ruta, que, valor en a, valor en b)."""
    if isinstance(a, dict) and isinstance(b, dict):
        claves = list(a) + ([] if solo_claves_de_a else [k for k in b if k not in a])
        for k in claves:
            if k in IGNORAR:
                continue
            r = f'{ruta}.{k}' if ruta else str(k)
            if k not in b:
                difs.append((r, f'solo en {ETIQ[0]}', a[k], FALTA))
            elif k not in a:
                difs.append((r, f'solo en {ETIQ[1]}', FALTA, b[k]))
            else:
                comparar(a[k], b[k], r, difs, tol)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) == len(b) and all(canon(x) == canon(y) for x, y in zip(a, b)):
            return
        ca, cb = collections.Counter(map(canon, a)), collections.Counter(map(canon, b))
        if ca == cb:                       # mismos elementos, otro orden
            i = next(i for i, (x, y) in enumerate(zip(a, b)) if canon(x) != canon(y))
            difs.append((f'{ruta}[{i}]', f'mismos {len(a)} elementos en OTRO ORDEN (primera posición distinta: {i})', a[i], b[i]))
        elif len(a) != len(b):             # faltan o sobran elementos: se dicen cuales (comparar por posicion seria ruido)
            solo_a, solo_b = list((ca - cb).elements()), list((cb - ca).elements())
            difs.append((ruta, f'{len(a)} elementos en {ETIQ[0]} y {len(b)} en {ETIQ[1]} '
                               f'({len(solo_a)} solo en {ETIQ[0]}, {len(solo_b)} solo en {ETIQ[1]})', FALTA, FALTA))
            for s in solo_a[:4]:
                difs.append((ruta, f'  elemento solo en {ETIQ[0]}', json.loads(s), FALTA))
            for s in solo_b[:4]:
                difs.append((ruta, f'  elemento solo en {ETIQ[1]}', FALTA, json.loads(s)))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                comparar(x, y, f'{ruta}[{i}]', difs, tol)
    elif not iguales(a, b, tol):
        difs.append((ruta, 'distinto', a, b))


def cargar(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def resumen_salida(d):
    """lineas / pendientes / otra estacion / sueltos (y puntas exactas) de una salida de volcar_trabajo"""
    if not isinstance(d, dict) or 'lineas' not in d:
        return ''
    ex = sum(1 for l in d['lineas'] if l.get('exacto'))
    return (f"{len(d['lineas'])} líneas ({ex} exactas), {len(d.get('pendientes') or [])} pendientes, "
            f"{len(d.get('otra_estacion') or [])} en otra estación, {len(d.get('sueltos') or [])} sueltos")


def informar(nombre, difs, maximo, nota=''):
    if not difs:
        print(f'  IGUAL  {nombre}{nota}')
        return True
    print(f'  FALLA  {nombre}: {len(difs)} diferencia(s){nota}')
    for r, que, a, b in difs[:maximo]:
        if que == 'distinto':
            print(f'           {r}: {ETIQ[0]} {corto(a)}  |  {ETIQ[1]} {corto(b)}')
        elif a is FALTA and b is FALTA:
            print(f'           {r}: {que}')
        elif que.startswith('  elemento'):
            print(f'           {r}: {que.strip()}: {corto(a if b is FALTA else b, 150)}')
        else:
            print(f'           {r}: {que}: {ETIQ[0]} {corto(a)}  |  {ETIQ[1]} {corto(b)}')
    if len(difs) > maximo:
        print(f'           … y {len(difs) - maximo} más')
    return False


def main(argv):
    if len(argv) < 2 or argv[1].startswith('--'):
        print(__doc__)
        return 2
    sal = argv[1]
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    maximo, tol, estricto = int(opt('--max', 12)), float(opt('--tol', 0)), '--estricto' in argv
    ok, comparados = True, 0
    if '--entre' in argv:                                  # dos corridas entre si
        otra = opt('--entre')
        ETIQ[:] = ['A', 'B']
        na = {os.path.basename(p) for p in glob.glob(os.path.join(sal, '*.json'))}
        nb = {os.path.basename(p) for p in glob.glob(os.path.join(otra, '*.json'))}
        print(f'Comparando A = {sal}  contra  B = {otra}  (sin {", ".join(sorted(IGNORAR))})')
        solo = sorted(na ^ nb)
        if solo:
            print(f'  aviso  {len(solo)} archivo(s) en una sola de las dos carpetas (no se comparan): '
                  + ', '.join(solo[:8]) + (' …' if len(solo) > 8 else ''))
        for n in sorted(na & nb):
            difs = []
            comparar(cargar(os.path.join(sal, n)), cargar(os.path.join(otra, n)), '', difs, tol)
            ok = informar(n, difs, maximo) and ok
            comparados += 1
    else:
        bases = opt('--bases', os.path.join(RAIZ, 'pruebas', 'bases'))
        print(f'Comparando {sal}  contra las bases de {bases}  (sin {", ".join(sorted(IGNORAR))})')
        for t, bn in BASES.items():                        # salida de volcar_trabajo contra su base
            ps, pb = os.path.join(sal, f'salida_{t}.json'), os.path.join(bases, bn)
            if not os.path.exists(pb):
                print(f'  FALLA  salida_{t}.json: no está la base {bn}')
                ok = False
                continue
            if not os.path.exists(ps):
                print(f'  FALLA  salida_{t}.json: no está en {sal}')
                ok = False
                continue
            a, b = cargar(pb), cargar(ps)
            difs = []
            comparar(a, b, '', difs, tol, solo_claves_de_a=True)
            nota = ''
            if not estricto:
                difs, n_con, ya_no = separar_conocidas(difs, t)
                if n_con or ya_no:
                    nota = (f'  [{n_con} diferencia(s) conocida(s) de la base vieja, no cuentan: ver CONOCIDAS]' if n_con else '') + \
                           (f'  [conocidas que ya no aparecen: {", ".join(ya_no)}]' if ya_no else '')
            ok = informar(f'salida_{t}.json contra {bn}: {resumen_salida(b)}', difs, maximo, nota) and ok
            if difs:
                print(f'           (base: {resumen_salida(a)})')
            comparados += 1
        for pre in PREFIJOS:                               # bases nuevas, si estan en las dos carpetas
            na = {os.path.basename(p) for p in glob.glob(os.path.join(sal, f'{pre}_*.json'))}
            nb = {os.path.basename(p) for p in glob.glob(os.path.join(bases, f'{pre}_*.json'))}
            for n in sorted(na - nb):
                print(f'  aviso  {n}: no hay base para comparar')
            for n in sorted(nb - na):
                print(f'  aviso  {n}: hay base pero no está en {sal}')
            for n in sorted(na & nb):
                difs = []
                comparar(cargar(os.path.join(bases, n)), cargar(os.path.join(sal, n)), '', difs, tol)
                ok = informar(n, difs, maximo) and ok
                comparados += 1
    if not comparados:
        print('FALLA: no había nada para comparar')
        return 1
    print('TODO OK' if ok else 'FALLA: hay diferencias')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main(sys.argv))
