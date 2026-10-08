"""Bateria B de la red de seguridad (PLAN_MODULAR.md, seccion 9): corre todo lo que exista y resume.
uso: python pruebas/bateria.py [--ab] [--semillas] [--dejar]
  En una carpeta temporal (nunca en los trabajos ni en el historial del usuario):
   1. volcar_trabajo.py --sin-cache de los 5 trabajos: 75287 sin --relayout (el trabajo ac0f0949510a; si no esta en la
      carpeta, se saca de git con git archive), 66817 / PAE / TPT / TPT con el constructivo 72715-1 (tpt_constructivo,
      el del usuario, desde 2026-10-08: tiene las dos laterales para la E8) con --relayout; el 66817 con --puntos.
   2. evaluar_bornes.py --no-guardar sobre los puntos del 66817: 104/104 bornes; y 75/75 puntas exactas.
   3. todas las pruebas/probar_*.py que haya (arreglos_pae, capas, producto, proyector, puentes, ronda2_topo, ronda3,
      web_humo...): TODO OK. (probar_capas: capas de planocables; probar_puentes: los nombres de los modulos viejos
      siguen; probar_producto: codigo de producto, plano y revision de los planos de 1 - Planos y la API /producto.)
   4. volcar_bases_nuevas.py de los 5 trabajos, si existe (listado_, layout_, e8_, ins_).
   5. comparar_bases.py <tmp> --bases pruebas/bases.
   6. node --test pruebas/js/, si existe la carpeta.
   7. con --ab: ab_planos.py <tmp>/ab y ab_planos.py --comparar pruebas/bases/ab <tmp>/ab.
   8. con --semillas: el paso 1 corre con PYTHONHASHSEED=0 y se repite con PYTHONHASHSEED=1; las dos corridas se
      comparan entre si (comparar_bases.py --entre): si difieren, el resultado depende del orden de los sets.
  Antes de empezar guarda una copia de programa/ocr_cache.json; al final dice si cambio (= hubo OCR en vivo) y la
  restaura. Tambien verifica que no cambio nada mas en programa/, en 1 - Planos/, en pruebas/fixtures/ ni en las
  carpetas de los trabajos.
  Todo corre con PLANOCABLES_MEMORIA_OCR=solo-lectura, PLANOCABLES_HISTORIAL en la carpeta temporal,
  PLANOCABLES_PORT=8798 (nunca el 8765 del taller) y PLANOCABLES_PRODUCTOS=pruebas/fixtures/productos.json (el
  catalogo de productos de las bases; el de programa/ lo cambia el taller al confirmar productos).
  --dejar: no borra la carpeta temporal (si algo falla no se borra nunca, para mirar las salidas y los logs).
  Resumen final: OK / FALLA / AVISO por paso, y «TODO OK» si todo pasa. Exit 0 / 1."""
import os, sys, json, time, shutil, tempfile, subprocess, hashlib, glob, io, tarfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRUEBAS = os.path.join(RAIZ, 'pruebas')
OCR = os.path.join(RAIZ, 'programa', 'ocr_cache.json')
PRODUCTOS = os.path.join(PRUEBAS, 'fixtures', 'productos.json')    # catalogo de productos fijo de las pruebas
J75287 = os.path.join('3 - Historial web', 'ac0f0949510a')
# (nombre, carpeta del trabajo relativa a la raiz, --relayout)
TRABAJOS = [('75287', J75287, False), ('66817', os.path.join('pruebas', 'trabajos', '66817'), True),
            ('76884', os.path.join('pruebas', 'trabajos', '76884'), True), ('tpt', os.path.join('pruebas', 'trabajos', 'tpt'), True),
            ('tpt_constructivo', os.path.join('pruebas', 'trabajos', 'tpt_constructivo'), True)]
REF_66817 = os.path.join(RAIZ, 'prototipos', '_referencia_66817', 'bornes_referencia.json')
BORNES_66817, PUNTAS_66817 = 104, 75          # CLAUDE.md: 104/104 bornes y 75/75 puntas exactas
NUEVAS = ('listado', 'layout', 'e8', 'ins')   # lo que escribe volcar_bases_nuevas.py
LIMITE = 20 * 60                              # segundos por comando

resumen = []                                  # (paso, estado, detalle, segundos)


def paso(nombre, estado, detalle='', seg=None):
    resumen.append((nombre, estado, detalle, seg))
    print(f"  {estado:5s} {nombre}{(': ' + detalle) if detalle else ''}{f'  ({seg:.0f} s)' if seg is not None else ''}", flush=True)


def correr(args, log, env=None):
    """corre un comando en la raiz del repo; devuelve (codigo, salida, segundos). La salida queda en 'log'."""
    t0 = time.time()
    try:
        p = subprocess.run(args, cwd=RAIZ, env=env, capture_output=True, timeout=LIMITE)
        cod, out = p.returncode, (p.stdout + p.stderr).decode('utf-8', 'replace')
    except subprocess.TimeoutExpired as e:
        cod, out = -1, ((e.stdout or b'') + (e.stderr or b'')).decode('utf-8', 'replace') + f'\n(cortado a los {LIMITE} s)'
    except OSError as e:
        cod, out = -2, f'no se pudo correr {args[0]}: {e}'
    with open(log, 'w', encoding='utf-8') as f:
        f.write(' '.join(f'"{a}"' if ' ' in a else a for a in args) + '\n\n' + out)
    return cod, out, time.time() - t0


def cola(out, n=20):
    return '\n'.join('          | ' + l for l in out.strip().splitlines()[-n:])


def firma_carpeta(d, sin=()):
    """{ruta relativa: sha1} de todos los archivos (sin __pycache__ ni los de 'sin')"""
    out = {}
    for base, dirs, archivos in os.walk(d):
        dirs[:] = [x for x in dirs if x != '__pycache__']
        for a in archivos:
            p = os.path.join(base, a)
            if os.path.abspath(p) in sin:
                continue
            h = hashlib.sha1()
            with open(p, 'rb') as f:
                for b in iter(lambda: f.read(1 << 20), b''):
                    h.update(b)
            out[os.path.relpath(p, RAIZ)] = h.hexdigest()
    return out


def trabajo_dir(rel, tmp):
    """carpeta del trabajo; el 75287 se saca de git a la carpeta temporal si no esta (nunca al historial)"""
    d = os.path.join(RAIZ, rel)
    if os.path.isdir(d):
        return d
    dest = os.path.join(tmp, 'git')
    p = subprocess.run(['git', '-C', RAIZ, 'archive', 'HEAD', rel.replace(os.sep, '/')], capture_output=True)
    if p.returncode:
        raise RuntimeError(f"git archive {rel}: {p.stderr.decode('utf-8', 'replace').strip()}")
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as t:
        t.extractall(dest, filter='data')
    return os.path.join(dest, rel)


def volcar_todos(dirs, sal, env, etiqueta):
    """paso 1: volcar_trabajo de los trabajos en 'sal'. Devuelve True si todos corrieron."""
    os.makedirs(sal, exist_ok=True)
    ok = True
    for t, rel, relayout in TRABAJOS:
        args = [sys.executable, os.path.join(PRUEBAS, 'volcar_trabajo.py'), dirs[t], os.path.join(sal, f'salida_{t}.json'), '--sin-cache']
        if relayout:
            args.append('--relayout')
        if t == '66817':
            args += ['--puntos', os.path.join(sal, 'puntos_66817.json')]
        cod, out, seg = correr(args, os.path.join(LOGS, f'volcar_{t}{etiqueta}.txt'), env)
        lin = [l for l in out.splitlines() if ' lineas (' in l or l.startswith('mapeo:')]
        if cod == 0 and os.path.exists(os.path.join(sal, f'salida_{t}.json')):
            paso(f'volcar_trabajo {t}{etiqueta}', 'OK', ' / '.join(l.split(' -> ')[0] for l in lin[:1]), seg)
        else:
            ok = False
            paso(f'volcar_trabajo {t}{etiqueta}', 'FALLA', f'código {cod}\n{cola(out)}', seg)
    return ok


def main():
    global LOGS
    sys.stdout.reconfigure(encoding='utf-8')
    con_ab, semillas, dejar = '--ab' in sys.argv, '--semillas' in sys.argv, '--dejar' in sys.argv
    t_total = time.time()
    tmp = tempfile.mkdtemp(prefix='bateria_')
    LOGS = os.path.join(tmp, 'logs'); os.makedirs(LOGS)
    sal = os.path.join(tmp, 'salidas')
    print(f'Batería B  ({RAIZ})\ncarpeta temporal: {tmp}', flush=True)
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PLANOCABLES_MEMORIA_OCR='solo-lectura',
               PLANOCABLES_HISTORIAL=os.path.join(tmp, 'historial'), PLANOCABLES_PORT='8798',
               PLANOCABLES_PRODUCTOS=PRODUCTOS)
    if semillas:
        env['PYTHONHASHSEED'] = '0'
    # copia de la memoria OCR y firma de lo que la bateria no tiene que tocar
    with open(OCR, 'rb') as f:
        ocr_antes = f.read()
    dirs = {t: trabajo_dir(rel, tmp) for t, rel, _ in TRABAJOS}
    vigilar = [os.path.join(RAIZ, 'programa'), os.path.join(RAIZ, '1 - Planos'), os.path.join(PRUEBAS, 'fixtures')] + \
              [d for d in dirs.values() if d.startswith(RAIZ)]
    firma_antes = {}
    for d in vigilar:
        firma_antes.update(firma_carpeta(d, sin=(os.path.abspath(OCR),)))
    try:
        # 1. volcar_trabajo
        print(f'\n1. volcar_trabajo ({len(TRABAJOS)} trabajos)' + (' con PYTHONHASHSEED=0' if semillas else ''), flush=True)
        volcar_todos(dirs, sal, env, '')

        # 2. bornes del 66817
        print('\n2. 66817: bornes y puntas exactas', flush=True)
        pts = os.path.join(sal, 'puntos_66817.json')
        if os.path.exists(pts):
            cod, out, seg = correr([sys.executable, os.path.join(PRUEBAS, 'evaluar_bornes.py'), pts, '--ref', REF_66817,
                                    '--no-guardar', '--json'], os.path.join(LOGS, 'evaluar_bornes_66817.txt'), env)
            try:
                r = json.JSONDecoder().raw_decode(out[out.index('{'):])[0]
                det = (f"BIEN {r['bien']}/{r['total']}, con punto {r['hallados']}/{r['total']}, error mediano {r['error_mediano_pt']} pt"
                       + (f"; fallas: {', '.join(x['texto'] + ' #' + ','.join(x['cables']) for x in r['fallas'][:6])}" if r['fallas'] else ''))
                paso('evaluar_bornes 66817', 'OK' if cod == 0 and r['bien'] == r['total'] == BORNES_66817 else 'FALLA',
                     det + ('' if r['total'] == BORNES_66817 else f' (se esperaban {BORNES_66817})'), seg)
            except (ValueError, KeyError) as e:
                paso('evaluar_bornes 66817', 'FALLA', f'{type(e).__name__}: {e}\n{cola(out)}', seg)
        else:
            paso('evaluar_bornes 66817', 'FALLA', 'no está puntos_66817.json (falló el volcar del 66817)')
        s66 = os.path.join(sal, 'salida_66817.json')
        if os.path.exists(s66):
            d = json.load(open(s66, encoding='utf-8'))
            ex, n = sum(1 for l in d['lineas'] if l.get('exacto')), len(d['lineas'])
            paso('puntas exactas 66817', 'OK' if ex == n == PUNTAS_66817 else 'FALLA', f'{ex}/{n} (se esperan {PUNTAS_66817}/{PUNTAS_66817})')

        # 3. probar_*.py
        print('\n3. pruebas probar_*.py', flush=True)
        for p in sorted(glob.glob(os.path.join(PRUEBAS, 'probar_*.py'))):
            n = os.path.basename(p)
            cod, out, seg = correr([sys.executable, p], os.path.join(LOGS, n.replace('.py', '.txt')), env)
            ok = cod == 0 and 'TODO OK' in out
            fallas = [l.strip() for l in out.splitlines() if 'FALLA' in l][:8]
            paso(n, 'OK' if ok else 'FALLA', 'TODO OK' if ok else f'código {cod}\n' + ('\n'.join('          | ' + l for l in fallas) or cola(out)), seg)

        # 4. bases nuevas
        vbn = os.path.join(PRUEBAS, 'volcar_bases_nuevas.py')
        print('\n4. volcar_bases_nuevas.py', flush=True)
        if os.path.exists(vbn):
            for t, rel, relayout in TRABAJOS:
                args = [sys.executable, vbn, dirs[t], sal, '--nombre', t] + (['--relayout'] if relayout else [])
                cod, out, seg = correr(args, os.path.join(LOGS, f'volcar_bases_nuevas_{t}.txt'), env)
                faltan = [f'{x}_{t}.json' for x in NUEVAS if not os.path.exists(os.path.join(sal, f'{x}_{t}.json'))]
                paso(f'volcar_bases_nuevas {t}', 'OK' if cod == 0 and not faltan else 'FALLA',
                     ('' if not faltan else f"no escribió {', '.join(faltan)}") + ('' if cod == 0 else f' código {cod}\n{cola(out)}'), seg)
        else:
            paso('volcar_bases_nuevas', 'NO ESTÁ', 'pruebas/volcar_bases_nuevas.py no existe (se saltea)')

        # 5. comparar contra las bases
        print('\n5. comparar_bases.py', flush=True)
        cod, out, seg = correr([sys.executable, os.path.join(PRUEBAS, 'comparar_bases.py'), sal, '--bases', os.path.join(PRUEBAS, 'bases')],
                               os.path.join(LOGS, 'comparar_bases.txt'), env)
        print('\n'.join('          | ' + l for l in out.strip().splitlines()[1:]))
        paso('comparar_bases', 'OK' if cod == 0 else 'FALLA', 'TODO OK' if cod == 0 else f'código {cod} (detalle arriba)', seg)

        # 6. node --test
        print('\n6. node --test pruebas/js/', flush=True)
        if os.path.isdir(os.path.join(PRUEBAS, 'js')):
            cod, out, seg = correr(['node', '--test', 'pruebas/js/'], os.path.join(LOGS, 'node_test.txt'), env)
            res = [l.strip() for l in out.splitlines() if l.strip().startswith(('# pass', '# fail', 'ℹ pass', 'ℹ fail'))]
            paso('node --test pruebas/js/', 'OK' if cod == 0 else 'FALLA', ', '.join(res) + ('' if cod == 0 else f'\n{cola(out)}'), seg)
        else:
            paso('node --test pruebas/js/', 'NO ESTÁ', 'no existe pruebas/js/ (se saltea)')

        # 7. A/B sobre todos los planos
        if con_ab:
            print('\n7. ab_planos.py (A/B sobre los planos de 1 - Planos)', flush=True)
            ab, base_ab = os.path.join(PRUEBAS, 'ab_planos.py'), os.path.join(PRUEBAS, 'bases', 'ab')
            if not os.path.exists(ab):
                paso('ab_planos', 'FALLA', 'pedido con --ab pero no existe pruebas/ab_planos.py')
            elif not os.path.isdir(base_ab):
                paso('ab_planos', 'FALLA', 'no existe la base pruebas/bases/ab/')
            else:
                cod, out, seg = correr([sys.executable, ab, os.path.join(tmp, 'ab')], os.path.join(LOGS, 'ab_planos.txt'), env)
                if cod:
                    paso('ab_planos (volcar)', 'FALLA', f'código {cod}\n{cola(out)}', seg)
                else:
                    paso('ab_planos (volcar)', 'OK', '', seg)
                    cod, out, seg = correr([sys.executable, ab, '--comparar', base_ab, os.path.join(tmp, 'ab')],
                                           os.path.join(LOGS, 'ab_planos_comparar.txt'), env)
                    paso('ab_planos --comparar', 'OK' if cod == 0 else 'FALLA', '' if cod == 0 else cola(out), seg)

        # 8. dependencia del orden de los sets
        if semillas:
            print('\n8. volcar_trabajo con PYTHONHASHSEED=1 (comparado con la corrida del paso 1, PYTHONHASHSEED=0)', flush=True)
            sal1 = os.path.join(tmp, 'salidas_semilla1')
            if volcar_todos(dirs, sal1, dict(env, PYTHONHASHSEED='1'), ' (semilla 1)'):
                cod, out, seg = correr([sys.executable, os.path.join(PRUEBAS, 'comparar_bases.py'), sal, '--entre', sal1],
                                       os.path.join(LOGS, 'comparar_semillas.txt'), env)
                print('\n'.join('          | ' + l for l in out.strip().splitlines()[1:]))
                paso('PYTHONHASHSEED 0 contra 1', 'OK' if cod == 0 else 'FALLA',
                     'iguales: no depende del orden de los sets' if cod == 0 else 'DIFIEREN: depende del orden de los sets (detalle arriba)', seg)
    except Exception:                                                      # noqa: BLE001
        import traceback
        paso('batería (error interno)', 'FALLA', traceback.format_exc())
    finally:
        # memoria OCR: si cambio, hubo OCR en vivo; se restaura
        with open(OCR, 'rb') as f:
            ocr_despues = f.read()
        if ocr_despues != ocr_antes:
            with open(OCR, 'wb') as f:
                f.write(ocr_antes)
            paso('memoria OCR (programa/ocr_cache.json)', 'AVISO', f'CAMBIÓ durante la batería ({len(ocr_antes)} -> {len(ocr_despues)} bytes): '
                 'hubo OCR en vivo. Restaurada a como estaba antes')
        else:
            paso('memoria OCR (programa/ocr_cache.json)', 'OK', 'sin cambios')
        firma_despues = {}
        for d in vigilar:
            firma_despues.update(firma_carpeta(d, sin=(os.path.abspath(OCR),)))
        cambios = sorted(k for k in set(firma_antes) | set(firma_despues) if firma_antes.get(k) != firma_despues.get(k))
        paso('programa/, planos y trabajos sin tocar', 'OK' if not cambios else 'FALLA',
             'sin cambios' if not cambios else 'cambiaron: ' + ', '.join(cambios[:10]) + (' …' if len(cambios) > 10 else ''))

    fallas = [r for r in resumen if r[1] == 'FALLA']
    print('\n' + '=' * 100 + '\nRESUMEN')
    for n, e, det, seg in resumen:
        print(f"  {e:8s} {n}{f'  ({seg:.0f} s)' if seg is not None else ''}{('  ' + det.splitlines()[0]) if det else ''}")
    print(f'tiempo total: {time.time() - t_total:.0f} s')
    if fallas or dejar:
        print(f'salidas y logs en: {tmp}')
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    avisos = [r for r in resumen if r[1] == 'AVISO']
    print('TODO OK' + (' (con avisos)' if avisos else '') if not fallas else f'FALLA: {len(fallas)} paso(s): ' + ', '.join(r[0] for r in fallas))
    return 1 if fallas else 0


if __name__ == '__main__':
    sys.exit(main())
