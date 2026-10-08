"""Pruebas de la estacion E8 (gabinete): lo esperado de cada etapa del visor de E8 en el TPT, el 66817, el 75287 y el
PAE. No escribe nada en los trabajos ni en el historial (todo corre en una carpeta temporal). Termina con TODO OK, o con
error si alguna falla.
uso: python pruebas/probar_e8.py [--bases <carpeta>] [-j N]
  Sin --bases: arma la E8 de los 5 trabajos con el codigo de HOY (pruebas/volcar_bases_nuevas.py, como «Regenerar» en
  la web, con --relayout salvo el 75287; N en paralelo, 3 por defecto) y ademas verifica que E6 no cambio: el listado,
  el layout de la bandeja (todo salvo 'vistas' y 'version_lector') y el instructivo (todo salvo 'estacion8') dan IGUAL
  que pruebas/bases. Con --bases: solo mira lo esperado de E8 en los e8_<t>.json de esa carpeta (ej. pruebas/bases).
  Trabajos: tpt_constructivo (el TPT 72715-1 del usuario con su topografico «72715-1 Constructivo»), tpt (TPT de
  pruebas, topografico 72887), 66817, 75287 (ac0f0949510a; si no esta en la carpeta, se saca de git) y 76884 (PAE).

ETAPA E8-1 «laterales completas» (2026-10-08):
  - cada lateral es su PLACA entera (la imagen la contiene), con sus canaletas, y todos sus cables tienen recorrido;
  - TPT: LD con 4 canaletas y 2 rieles (el de abajo, tapado por los aparatos, sale de la fila de etiquetas) con 32XAI,
    33XAI, 43XDI, 81XCM y 11XP adentro, con cables de la parte de arriba y de abajo (no todo «parte de abajo»); LI sin
    riel con 12PS2 y 12PB1 y sus 2 canaletas, aparato por aparato; «Puerta y placa» con 21PCB01 y 13SH1 y sin ningun
    aparato de las laterales; las salidas: la LD sale hacia el fondo por su izquierda y la LI por su derecha;
  - 66817: las dos laterales sin riel (LI: 12PS1, 12PB1; LD: 11XP, 43XDI, 81XCM, 12CB1); los cables de una lateral a
    la otra (1101, 1102) estan en las DOS, cada uno diciendo a que lateral va;
  - 75287: la lateral con sus 2 canaletas y sus 2 rieles, todo con recorrido;
  - PAE (EPLAN): su E8 igual que antes de la etapa (36 cables en la lateral izquierda, 36 con el punto del borne y 36
    con recorrido, 3 canaletas; la misma puerta / placa y zona hidraulica)."""
import os, sys, io, json, glob, shutil, tarfile, tempfile, subprocess, concurrent.futures as cf

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASES = os.path.join(RAIZ, 'pruebas', 'bases')
sys.stdout.reconfigure(encoding='utf-8')
sys.dont_write_bytecode = True
J75287 = os.path.join('3 - Historial web', 'ac0f0949510a')
TRABAJOS = {'tpt_constructivo': (os.path.join('pruebas', 'trabajos', 'tpt_constructivo'), True),
            'tpt': (os.path.join('pruebas', 'trabajos', 'tpt'), True),
            '66817': (os.path.join('pruebas', 'trabajos', '66817'), True),
            '75287': (J75287, False),
            '76884': (os.path.join('pruebas', 'trabajos', '76884'), True)}
fallas = []


def chequear(ok, msg):
    print(('  ok    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)
    return ok


def trabajo_dir(rel, tmp):
    d = os.path.join(RAIZ, rel)
    if os.path.isdir(d):
        return d
    p = subprocess.run(['git', '-C', RAIZ, 'archive', 'HEAD', rel.replace(os.sep, '/')], capture_output=True)
    if p.returncode:
        raise RuntimeError(f"git archive {rel}: {p.stderr.decode('utf-8', 'replace').strip()}")
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as t:
        t.extractall(os.path.join(tmp, 'git'), filter='data')
    return os.path.join(tmp, 'git', rel)


def armar(t, tmp, env):
    rel, relayout = TRABAJOS[t]
    args = [sys.executable, os.path.join(RAIZ, 'pruebas', 'volcar_bases_nuevas.py'), trabajo_dir(rel, tmp), os.path.join(tmp, 'sal'),
            '--nombre', t] + (['--relayout'] if relayout else [])
    p = subprocess.run(args, cwd=RAIZ, env=env, capture_output=True, timeout=30 * 60)
    return t, p.returncode, (p.stdout + p.stderr).decode('utf-8', 'replace')


def cargar(d, pre, t):
    p = os.path.join(d, f'{pre}_{t}.json')
    if not os.path.exists(p):
        return None
    with open(p, encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------------ ayudas sobre la E8
lineas = lambda L: [l for p in L['pasos'] for l in p['lineas']]
comps = lambda L: {l['componente'] for l in lineas(L)}
tags_de = lambda L: {str(c).split(' ')[0] for c in comps(L)} | {c.rstrip('0123456789') for c in comps(L) if 'KR' in c}
contiene = lambda a, b: a[0] <= b[0] + 0.01 and a[1] <= b[1] + 0.01 and a[2] >= b[2] - 0.01 and a[3] >= b[3] - 0.01


def lateral(e8, lado):
    xs = [L for L in e8.get('laterales') or [] if L['lado'] == lado]
    return xs[0] if len(xs) == 1 else None


def comunes(t, e8):
    """lo que vale para toda lateral de AutoCAD: placa entera en la imagen, canaletas y todo con recorrido"""
    for L in e8.get('laterales') or []:
        ls = lineas(L)
        chequear(L.get('placa') and contiene(L['region'], L['placa']),
                 f"{t} {L['nombre']}: la imagen ({L['region']}) muestra la placa entera ({L.get('placa')})")
        chequear(L['ductos'] and not L.get('sin_canaletas'), f"{t} {L['nombre']}: {len(L['ductos'])} canaletas leídas")
        chequear(ls and all(l.get('ruta') for l in ls), f"{t} {L['nombre']}: {sum(1 for l in ls if l.get('ruta'))} de {len(ls)} cables con recorrido")
        if L.get('sin_riel'):
            chequear(all(p['titulo'].startswith('Aparato ') for p in L['pasos']), f"{t} {L['nombre']}: sin riel, los pasos van aparato por aparato")


def salida_al_fondo(t, L, por_izq):
    """los cables que salen de la lateral (no van a la misma lateral) terminan del lado del fondo: a la izquierda de las
    canaletas en la LD, a la derecha en la LI"""
    x0 = min(d['b'][0] for d in L['ductos']); x1 = max(d['b'][2] for d in L['ductos'])
    sal = [l for l in lineas(L) if l['otra'] != 'misma bandeja' and l.get('ruta')]
    ok = sal and all((l['ruta'][-1][0] < x0) if por_izq else (l['ruta'][-1][0] > x1) for l in sal)
    chequear(ok, f"{t} {L['nombre']}: los {len(sal)} cables que salen de la lateral salen hacia el fondo, por su {'izquierda' if por_izq else 'derecha'}")


def esperado_tpt(t, e8):
    comunes(t, e8)
    ld, li = lateral(e8, 'LD'), lateral(e8, 'LI')
    if chequear(ld is not None, f'{t}: hay una lateral derecha'):
        chequear(ld['nombre'] == 'Bandeja lateral derecha' and 'LATERAL DERECHA' in (ld.get('titulo') or ''),
                 f"{t} LD: nombre {ld['nombre']!r}, título {ld.get('titulo')!r}")
        chequear(len(ld['ductos']) == 4 and len(ld['rieles']) == 2 and not ld.get('sin_riel'),
                 f"{t} LD: 4 canaletas y 2 rieles ({len(ld['ductos'])} y {ld['rieles']})")
        falta = {'32XAI', '33XAI', '43XDI', '81XCM', '11XP', '13XC2', '16XC'} - tags_de(ld)
        chequear(not falta, f"{t} LD: 32XAI, 33XAI, 43XDI, 81XCM, 11XP (riel 2) y 13XC2, 16XC (riel 1) adentro (faltan {sorted(falta)})")
        lados = {l['lado'] for l in lineas(ld)}
        chequear(lados == {'arriba', 'abajo'}, f"{t} LD: cables de la parte de arriba y de la de abajo ({sorted(lados)})")
        chequear({p['titulo'].split(' · ')[0] for p in ld['pasos']} == {'Riel 1', 'Riel 2'}, f"{t} LD: pasos de los rieles 1 y 2")
        salida_al_fondo(t, ld, True)
    if chequear(li is not None, f'{t}: hay una lateral izquierda'):
        chequear(li.get('sin_riel') and len(li['ductos']) == 2 and {'12PS2', '12PB1'} <= tags_de(li),
                 f"{t} LI: sin riel, 2 canaletas, con 12PS2 y 12PB1 ({len(li['ductos'])}, {sorted(tags_de(li))})")
        salida_al_fondo(t, li, False)
    puerta = {g['tag'] for g in e8['afuera'] if g['zona'] == 'puerta / placa'}
    de_lat = {'32XAI', '33XAI', '43XDI', '81XCM', '11XP', '13XC2', '16XC', '12PS2', '12PB1'}
    chequear({'21PCB01', '13SH1'} <= puerta and not (puerta & de_lat),
             f"{t}: «Puerta y placa» con 21PCB01 y 13SH1 y sin aparatos de las laterales ({sorted(puerta)})")


def esperado_66817(t, e8):
    comunes(t, e8)
    ld, li = lateral(e8, 'LD'), lateral(e8, 'LI')
    if not chequear(ld is not None and li is not None, f"{t}: las dos laterales ({[L['nombre'] for L in e8['laterales']]})"):
        return
    chequear(li.get('sin_riel') and {'12PS1', '12PB1'} <= tags_de(li), f"{t} LI: sin riel, con 12PS1 y 12PB1 ({sorted(tags_de(li))})")
    chequear(ld.get('sin_riel') and {'11XP', '43XDI', '81XCM', '12CB1'} <= tags_de(ld),
             f"{t} LD: sin riel, con 11XP, 43XDI, 81XCM y 12CB1 ({sorted(tags_de(ld))})")
    for num in ('1101', '1102'):
        a = [l for l in lineas(ld) if l['num'] == num]; b = [l for l in lineas(li) if l['num'] == num]
        chequear(len(a) == 1 and len(b) == 1 and a[0]['otra'] == li['nombre'].lower() and b[0]['otra'] == ld['nombre'].lower()
                 and a[0]['clave'] == b[0]['clave'],
                 f"{t}: {num} (de una lateral a la otra) está en las dos, cada una dice a cuál va, con la misma marca "
                 f"({[x['otra'] for x in a]} / {[x['otra'] for x in b]})")
    salida_al_fondo(t, ld, True)
    salida_al_fondo(t, li, False)
    puerta = {g['tag'] for g in e8['afuera']}
    chequear(not (puerta & (tags_de(ld) | tags_de(li))), f"{t}: «Puerta y placa» sin aparatos de las laterales ({sorted(puerta)})")


def esperado_75287(t, e8):
    comunes(t, e8)
    if chequear(len(e8['laterales']) == 1, f"{t}: una lateral ({[L['nombre'] for L in e8['laterales']]})"):
        L = e8['laterales'][0]
        chequear(len(L['ductos']) == 2 and len(L['rieles']) == 2, f"{t} {L['nombre']}: 2 canaletas y 2 rieles ({len(L['ductos'])}, {L['rieles']})")
        chequear({'12XPS', '11XP'} <= tags_de(L), f"{t} {L['nombre']}: con 12XPS y 11XP ({sorted(tags_de(L))})")


# PAE antes de la etapa E8-1 (pruebas/bases/e8_76884.json del 2026-10-07): no puede empeorar
PAE_AFUERA = {('21PCB01', 'puerta / placa', 44), ('11MS1', 'puerta / placa', 4), ('13MS1', 'puerta / placa', 4), ('42DB1', 'puerta / placa', 4),
              ('42DS', 'puerta / placa', 2), ('X1', 'zona hidráulica', 8), ('12PB1', 'zona hidráulica', 4), ('BH_01_ZV', 'zona hidráulica', 4),
              ('LS001A', 'zona hidráulica', 4), ('BH-01-M', 'zona hidráulica', 3), ('12F2', 'zona hidráulica', 2), ('PT001', 'zona hidráulica', 2),
              ('SP_1', 'zona hidráulica', 2), ('SP_2', 'zona hidráulica', 2), ('SP_3', 'zona hidráulica', 2)}


def esperado_76884(t, e8):
    if chequear(len(e8['laterales']) == 1, f"{t}: una lateral ({[L['nombre'] for L in e8['laterales']]})"):
        L = e8['laterales'][0]; ls = lineas(L)
        chequear(L['nombre'] == 'Bandeja lateral izquierda' and L['lado'] == 'LI', f"{t}: {L['nombre']!r} ({L['lado']})")
        chequear(L['n'] == 36 and L['exactos'] == 36 and sum(1 for l in ls if l.get('ruta')) == 36 and len(L['ductos']) == 3,
                 f"{t}: 36 cables, {L['exactos']} con el punto del borne, {sum(1 for l in ls if l.get('ruta'))} con recorrido, {len(L['ductos'])} canaletas")
    af = {(g['tag'], g['zona'], len(g['cables'])) for g in e8['afuera']}
    chequear(af == PAE_AFUERA, f"{t}: puerta / placa y zona hidráulica como antes ({len(af)} aparatos)"
             + ('' if af == PAE_AFUERA else f': sobran {sorted(af - PAE_AFUERA)}, faltan {sorted(PAE_AFUERA - af)}'))


ESPERADO = {'tpt_constructivo': esperado_tpt, 'tpt': esperado_tpt, '66817': esperado_66817, '75287': esperado_75287, '76884': esperado_76884}


def e6_igual(t, sal):
    """E6 no cambia: listado, layout de la bandeja (sin 'vistas' ni 'version_lector') e instructivo (sin 'estacion8')
    iguales a pruebas/bases"""
    sys.path.insert(0, os.path.join(RAIZ, 'pruebas'))
    import comparar_bases as cb
    for pre, sin in (('listado', ()), ('layout', ()), ('ins', ('estacion8',))):
        a, b = cargar(BASES, pre, t), cargar(sal, pre, t)
        if a is None:
            chequear(False, f'{t}: no está la base pruebas/bases/{pre}_{t}.json')
            continue
        if b is None:
            chequear(False, f'{t}: no se armó {pre}_{t}.json')
            continue
        if pre == 'layout':
            a = dict(a, layout={k: v for k, v in a['layout'].items() if k not in ('vistas', 'version_lector')})
            b = dict(b, layout={k: v for k, v in b['layout'].items() if k not in ('vistas', 'version_lector')})
        a = {k: v for k, v in a.items() if k not in sin}; b = {k: v for k, v in b.items() if k not in sin}
        difs = []
        cb.comparar(a, b, '', difs, 0)
        chequear(not difs, f'{t}: E6 igual: {pre}_{t}.json' + (f" sin {', '.join(sin)}" if sin else '') + (' sin vistas ni version_lector' if pre == 'layout' else '')
                 + ('' if not difs else f": {len(difs)} diferencia(s), ej. {difs[0][0]} {cb.corto(difs[0][2])} | {cb.corto(difs[0][3])}"))


def main():
    a = sys.argv[1:]
    bases = a[a.index('--bases') + 1] if '--bases' in a else None
    j = int(a[a.index('-j') + 1]) if '-j' in a else 3
    tmp = tempfile.mkdtemp(prefix='probar_e8_')
    try:
        if bases:
            sal = bases
            print(f'E8 de {bases} (sin volver a armar)')
        else:
            sal = os.path.join(tmp, 'sal'); os.makedirs(sal)
            env = dict(os.environ, PYTHONIOENCODING='utf-8', PLANOCABLES_MEMORIA_OCR='solo-lectura',
                       PLANOCABLES_PRODUCTOS=os.path.join(RAIZ, 'pruebas', 'fixtures', 'productos.json'),
                       PLANOCABLES_HISTORIAL=os.path.join(tmp, 'historial'), PLANOCABLES_PORT='8796')
            print(f'Armando la E8 de {len(TRABAJOS)} trabajos con el código de hoy ({j} a la vez)…', flush=True)
            with cf.ThreadPoolExecutor(j) as ex:
                for t, cod, out in ex.map(lambda t: armar(t, tmp, env), TRABAJOS):
                    chequear(cod == 0, f'{t}: volcar_bases_nuevas' + ('' if cod == 0 else f' (código {cod})\n' + out[-1500:]))
        for t, fn in ESPERADO.items():
            print(f'\n{t}')
            e8 = cargar(sal, 'e8', t)
            if not chequear(isinstance(e8, dict) and e8.get('version'), f'{t}: hay E8 armada (e8_{t}.json)'):
                continue
            chequear(not e8.get('detalle') and e8.get('version', 0) >= 2, f"{t}: E8 versión {e8.get('version')} sin errores")
            fn(t, e8)
            if not bases:
                e6_igual(t, sal)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('\nTODO OK' if not fallas else f'\nFALLA: {len(fallas)} prueba(s)')
    return 1 if fallas else 0


if __name__ == '__main__':
    sys.exit(main())
