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
    con recorrido, 3 canaletas; la misma puerta / placa y zona hidraulica).

ETAPA E8-2 «entrada a las laterales y bisagra» (2026-10-08):
  - la primera vez: recorridos = {preguntar: True, bisagra: None, vistas: {}} (el asistente de la web pregunta); cada
    lateral con su clave estable (lado|titulo) y su entrada propuesta; SIN ELEGIR, el resultado es la propuesta: los
    cables que salen de la lateral terminan en la entrada propuesta (75287, canaletas partidas: los de la otra parte en la
    punta de su horizontal) y, sin bisagra, nada sale hacia la puerta;
  - vista previa (estacion8.rutear_guardado, la de POST /e8/recorridos) sobre el instructivo armado: sin elegir da lo
    mismo que el armado; con la bisagra de un lado, los que siguen a la puerta (a_puerta) en la lateral de ese lado salen
    por el lado de la puerta y el resto no cambia (los de la otra lateral cruzan el fondo); con una ENTRADA ELEGIDA (la
    punta de otra horizontal del borde del fondo) las rutas terminan ahi (las que no llegan quedan marcadas no_llega y
    salen por la propuesta); un GRUPO de cables elegidos manda; la propuesta va a la altura de la salida de E6 solo si
    las vistas estan alineadas;
  - regenerar (web.gen_instructivo sobre una copia del TPT del constructivo) CONSERVA lo elegido (entrada, grupo,
    bisagra) y las rutas terminan ahi; un topografico nuevo lo BORRA y vuelve a preguntar (rutas a la propuesta)."""
import os, sys, io, json, glob, math, shutil, tarfile, tempfile, subprocess, concurrent.futures as cf

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


# ------------------------------------------------------------------ etapa E8-2: entrada a las laterales y bisagra
salen = lambda L: [l for l in lineas(L) if 'marca_d' not in l]
cerca = lambda p, q, tol=0.6: p is not None and q is not None and abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol
fin = lambda r: r[-1] if r else None


def e8_modulo():
    if os.path.join(RAIZ, 'programa') not in sys.path:
        sys.path.insert(0, os.path.join(RAIZ, 'programa'))
    import estacion8
    return estacion8


def otra_entrada(L):
    """la punta (del lado del fondo) de otra canaleta horizontal del borde que no es la de la propuesta, o None"""
    from ruteo import ancho, SALIDA_W, BORDE_W
    hs = [d for d in L['ductos'] if d['h'] and not d.get('ex')]
    if not hs:
        return None
    W = ancho(L['ductos']); izq = L['hacia'] == 'izq'
    borde = min(d['b'][0] for d in L['ductos']) if izq else max(d['b'][2] for d in L['ductos'])
    for d in sorted(hs, key=lambda d: -(d['b'][1] + d['b'][3])):
        x = d['b'][0] if izq else d['b'][2]
        cy = round((d['b'][1] + d['b'][3]) / 2, 1)
        if abs(x - borde) <= BORDE_W * W and abs(cy - L['entrada_propuesta'][1]) > W:
            return [round(x - SALIDA_W * W if izq else x + SALIDA_W * W, 1), cy]
    return None


def esperado_e82(t, e8):
    """la primera vez, sin elegir nada: preguntar, la clave de cada vista y las rutas a la propuesta"""
    rec = e8.get('recorridos')
    chequear(rec == {'preguntar': True, 'bisagra': None, 'vistas': {}} and e8.get('bisagra_propuesta') in ('izq', 'der'),
             f"{t}: la primera vez el asistente pregunta (recorridos {rec}, bisagra propuesta {e8.get('bisagra_propuesta')})")
    claves = [L.get('clave_vista') for L in e8['laterales']]
    chequear(all(c and c.startswith(L['lado'] + '|') for c, L in zip(claves, e8['laterales'])) and len(set(claves)) == len(claves),
             f'{t}: cada lateral con su clave estable {claves}')
    for L in e8['laterales']:
        ss = salen(L)
        if not (L['ductos'] and ss):
            continue
        p = L.get('entrada_propuesta')
        en = sum(1 for l in ss if cerca(fin(l.get('ruta')), p, 0.15))
        chequear(p and (en == len(ss) if t != '75287' else en >= len(ss) / 2),
                 f"{t} {L['nombre']}: sin elegir, {en} de {len(ss)} salen por la entrada propuesta {p}"
                 + (' (canaletas partidas: el resto por la punta de su horizontal)' if t == '75287' else ''))
        chequear(not L.get('bisagra') and not L.get('puerta_propuesta') and all(l.get('sale') == 'entrada' and not l.get('salida') for l in ss),
                 f"{t} {L['nombre']}: sin bisagra elegida nada sale hacia la puerta ({sum(1 for l in ss if l.get('a_puerta'))} siguen a la puerta)")


def ruteo_e82(t, ins):
    """vista previa (estacion8.rutear_guardado, la de POST /e8/recorridos) con bisagra, entrada elegida y un grupo"""
    E8 = e8_modulo()
    e8 = ins['estacion8']
    lats = e8['laterales']
    base = E8.rutear_guardado(ins, {})
    for x, L in zip(base, lats):
        ss = salen(L)
        par = sum(1 for y, l in zip(x['lineas'], ss) if y['clave'] == l['clave'] and y['largo_mm'] == l.get('largo_mm')
                  and (y['ruta'] is None) == (l.get('ruta') is None) and (y['ruta'] is None or len(y['ruta']) == len(l['ruta'])
                  and all(cerca(a, b, 0.5) for a, b in zip(y['ruta'], l['ruta']))))
        chequear(len(x['lineas']) == len(ss) and par == len(ss) and x['entrada_propuesta'] == L['entrada_propuesta'],
                 f"{t} {L['nombre']}: vista previa sin elegir = lo armado ({par}/{len(ss)} rutas a menos de 0,5 pt)")
    # bisagra de cada lado: los que siguen a la puerta salen por el lado de la puerta en la lateral de ese lado
    for bis in ('izq', 'der'):
        r = E8.rutear_guardado(ins, {'bisagra': bis})
        for x, x0, L in zip(r, base, lats):
            if not L['ductos']:
                continue
            aqui = L['lado'] == ('LI' if bis == 'izq' else 'LD')
            ss = salen(L)
            borde = (min(d['b'][0] for d in L['ductos']) if L['hacia'] == 'der' else max(d['b'][2] for d in L['ductos']))
            al_frente = lambda p: p is not None and (p[0] < borde if L['hacia'] == 'der' else p[0] > borde)
            ap = [(y, l) for y, l in zip(x['lineas'], ss) if l.get('a_puerta')]
            otros = [(y, y0) for y, y0, l in zip(x['lineas'], x0['lineas'], ss) if not (aqui and l.get('a_puerta'))]
            ok = x['bisagra'] == aqui and (bool(x['puerta_propuesta']) == aqui) and all(y0['ruta'] == y['ruta'] for y, y0 in otros)
            if aqui:
                ok = ok and all(y['sale'] == 'puerta' and al_frente(fin(y['ruta'])) for y, l in ap)
            else:
                ok = ok and all(y['sale'] == 'entrada' for y, l in ap)
            chequear(ok, f"{t} {L['nombre']} con la bisagra a la {'izquierda' if bis == 'izq' else 'derecha'}: "
                         + (f"{len(ap)} a la puerta salen por el lado de la puerta, el resto igual" if aqui else f"{len(ap)} a la puerta cruzan el fondo (como sin bisagra)"))
    # entrada elegida y un grupo de cables elegidos
    for x0, L in zip(base, lats):
        ss = salen(L)
        if not (L['ductos'] and ss):
            continue
        p = otra_entrada(L)
        if p:
            r = [x for x in E8.rutear_guardado(ins, {'vistas': {L['clave_vista']: {'entrada': [p]}}}) if x['clave_vista'] == L['clave_vista']][0]
            llegan = [y for y in r['lineas'] if cerca(fin(y['ruta']), p)]
            no = [y for y in r['lineas'] if y.get('no_llega')]
            chequear(llegan and len(llegan) + len(no) == len(ss) and r['no_llegan'] == len(no)
                     and all(cerca(fin(y['ruta']), fin(y0['ruta'])) for y, y0 in zip(r['lineas'], x0['lineas']) if y.get('no_llega')),
                     f"{t} {L['nombre']}: con la entrada elegida en {p} terminan ahí {len(llegan)} de {len(ss)}"
                     + (f" (los {len(no)} que no llegan por las canaletas salen por la propuesta)" if no else ''))
        g = ss[0]['num']
        q = p or [L['entrada_propuesta'][0], L['entrada_propuesta'][1]]
        rec = {'vistas': {L['clave_vista']: {'grupos': [{'id': 'g1', 'nombre': 'Grupo 1', 'cables': [g], 'puntos': [q]}]}}}
        r = [x for x in E8.rutear_guardado(ins, rec) if x['clave_vista'] == L['clave_vista']][0]
        en = [y for y, l in zip(r['lineas'], ss) if l['num'] == g]
        resto = [(y, y0) for y, y0, l in zip(r['lineas'], x0['lineas'], ss) if l['num'] != g]
        chequear(en and all(y['salida'] == 'g1' and (cerca(fin(y['ruta']), q) or y.get('no_llega')) for y in en)
                 and all(y['ruta'] == y0['ruta'] and not y.get('salida') for y, y0 in resto),
                 f"{t} {L['nombre']}: un grupo con el cable {g} sale por su punto {q} y el resto no cambia")
    # propuesta a la altura de la salida de E6: solo con las vistas alineadas (misma hoja y misma altura)
    tp = ins.get('topo') or {}
    for L in lats:
        p = otra_entrada(L) if L['ductos'] else None
        if not p:
            continue
        a = E8.propuestas(L['ductos'], L['lado'], False, [0, p[1]], L['placa'], L['pag'], tp.get('region'), tp.get('pag'))
        b = E8.propuestas(L['ductos'], L['lado'], False, [0, p[1]], L['placa'], (L['pag'] or 0) + 1, tp.get('region'), tp.get('pag'))
        lejos = [L['placa'][0], L['placa'][1] - 5 * (L['placa'][3] - L['placa'][1]), L['placa'][2], L['placa'][1] - 4 * (L['placa'][3] - L['placa'][1])]
        c = E8.propuestas(L['ductos'], L['lado'], False, [0, p[1]], lejos, L['pag'], tp.get('region'), tp.get('pag'))
        chequear(cerca(a['entrada'], p, 0.15) and a['por_entrada'] == [a['entrada']] and b['entrada'] == L['entrada_propuesta'] and not b['por_entrada']
                 and c['entrada'] == L['entrada_propuesta'] and not c['por_entrada'],
                 f"{t} {L['nombre']}: con la salida de E6 a la altura {p[1]} la entrada propuesta es {a['entrada']}; en otra hoja o a otra altura, la regla {b['entrada']}")


def regenerar_e82(tmp):
    """regenerar conserva lo elegido; un topografico nuevo lo borra (web.gen_instructivo sobre una copia del TPT del
    constructivo, en un historial temporal)"""
    print('\nregenerar y topográfico nuevo (tpt_constructivo)')
    hist = os.path.join(tmp, 'hist_regen')
    jid = 'e8e8e8e8e8e8'
    shutil.copytree(os.path.join(RAIZ, TRABAJOS['tpt_constructivo'][0]), os.path.join(hist, jid), ignore=shutil.ignore_patterns('*.png'))
    os.environ.update(PLANOCABLES_HISTORIAL=hist, PLANOCABLES_MEMORIA_OCR='solo-lectura', PLANOCABLES_PORT='8796',
                      PLANOCABLES_PRODUCTOS=os.path.join(RAIZ, 'pruebas', 'fixtures', 'productos.json'))
    if os.path.join(RAIZ, 'programa') not in sys.path:
        sys.path.insert(0, os.path.join(RAIZ, 'programa'))
    import web
    web.WORK = hist
    pj = os.path.join(hist, jid, 'instructivo.json')

    def gen(**kw):
        web.INS[jid] = dict(estado='en cola', mensaje='', progreso=0.0)
        web.gen_instructivo(jid, **kw)
        st = web.INS[jid]
        if not chequear(st.get('estado') == 'terminado', f"gen_instructivo {kw or ''}: {st.get('estado')} {st.get('error') or ''}"):
            return None
        with open(pj, encoding='utf-8') as f:
            return json.load(f)

    ins1 = gen()
    if not ins1:
        return
    e8 = ins1['estacion8']
    ld = lateral(e8, 'LD'); li = lateral(e8, 'LI')
    p = otra_entrada(ld) if ld else None
    if not chequear(ld and li and p, f'hay LD con otra canaleta para entrar ({p}) y LI'):
        return
    g = salen(ld)[0]['num']
    q = ld['entrada_propuesta']
    rec = {'preguntar': False, 'bisagra': 'izq', 'vistas': {
        ld['clave_vista']: {'entrada': [p], 'puerta': [], 'grupos': [{'id': 'g1', 'nombre': 'Grupo 1', 'cables': [g], 'puntos': [q]}]},
        li['clave_vista']: {'entrada': [], 'puerta': [], 'grupos': []}}}
    ins1['estacion8']['recorridos'] = rec          # (como la pestaña: PUT /instructivo con lo elegido)
    with open(pj, 'w', encoding='utf-8') as f:
        json.dump(ins1, f, ensure_ascii=False)
    ins2 = gen()
    if not ins2:
        return
    e8b = ins2['estacion8']
    ld2, li2 = lateral(e8b, 'LD'), lateral(e8b, 'LI')
    chequear(e8b.get('recorridos') == rec, f"regenerar conserva la entrada, el grupo y la bisagra ({e8b.get('recorridos')})")
    ok = [l for l in salen(ld2) if (cerca(fin(l.get('ruta')), q) if l['num'] == g else cerca(fin(l.get('ruta')), p))]
    chequear(len(ok) == len(salen(ld2)) and all(l.get('salida') == 'g1' for l in salen(ld2) if l['num'] == g),
             f"LD: {len(ok)} de {len(salen(ld2))} terminan en la entrada elegida {p} (y el {g}, del grupo, en {q})")
    borde_li = min(d['b'][0] for d in li2['ductos'])
    ap = [l for l in salen(li2) if l.get('a_puerta')]
    chequear(li2.get('bisagra') and li2.get('puerta_propuesta') and ap and all(l.get('sale') == 'puerta' and fin(l['ruta'])[0] < borde_li for l in ap)
             and all(l.get('sale') == 'entrada' and cerca(fin(l['ruta']), li2['entrada_propuesta']) for l in salen(li2) if not l.get('a_puerta')),
             f"LI (bisagra a la izquierda): {len(ap)} a la puerta salen por el lado de la puerta {li2.get('puerta_propuesta')}, el resto por la entrada")
    chequear(not any('no llega' in a for a in e8b.get('avisos') or []), f"sin avisos de recorridos que no llegan ({e8b.get('avisos')})")
    ins3 = gen(topo_nuevo=True)
    if not ins3:
        return
    e8c = ins3['estacion8']
    chequear(e8c.get('recorridos') == {'preguntar': True, 'bisagra': None, 'vistas': {}}, f"un topográfico nuevo borra lo elegido y vuelve a preguntar ({e8c.get('recorridos')})")
    ld3 = lateral(e8c, 'LD')
    chequear(all(cerca(fin(l.get('ruta')), ld3['entrada_propuesta'], 0.15) for l in salen(ld3)),
             f"y la LD vuelve a la entrada propuesta {ld3['entrada_propuesta']}")
    # (el instructivo de E6 no cambia con lo elegido en E8)
    sin = lambda d: {k: v for k, v in d.items() if k not in ('estacion8', 'generado', 'mapeo', 'salidas', 'producto')}
    chequear(sin(ins1) == sin(ins2), 'lo elegido en E8 no cambia el instructivo de E6')


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
            chequear(not e8.get('detalle') and e8.get('version', 0) >= 3, f"{t}: E8 versión {e8.get('version')} sin errores")
            fn(t, e8)
            esperado_e82(t, e8)
            ins = cargar(sal, 'ins', t) or (cargar(BASES, 'ins', t) if bases else None)
            if chequear(isinstance(ins, dict) and (ins.get('estacion8') or {}).get('laterales') is not None, f'{t}: hay instructivo armado (ins_{t}.json)'):
                ruteo_e82(t, ins)
            if not bases:
                e6_igual(t, sal)
        if not bases:
            regenerar_e82(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('\nTODO OK' if not fallas else f'\nFALLA: {len(fallas)} prueba(s)')
    return 1 if fallas else 0


if __name__ == '__main__':
    sys.exit(main())
