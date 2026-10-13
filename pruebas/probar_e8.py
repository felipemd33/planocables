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
    bisagra) y las rutas terminan ahi; un topografico nuevo lo BORRA y vuelve a preguntar (rutas a la propuesta).

ETAPA E8-3 «WAGO del cargador» (2026-10-08; regla del taller: manda el dibujo del funcional):
  - TPT: 1108, 1109, 1201 y 1202 (el cargador 12PS2, con un ⊟ dibujado entre el pin y el cable) llevan «WAGO con el
    cable propio de 12PS2» con su pin por la regla de los pines repetidos (+ panel, - panel, + bateria, - bateria), la
    punta pelada (sin pino), el empalme DEBAJO del cargador a la salida de una canaleta (fuera de las canaletas, la
    ruta sale de ahi y entra a la canaleta), un empalme al lado del otro, y el texto de la punta y la clave de la marca
    como antes; el RS-485 (8105 / 8106, EMPALME con 12PS2) va en la lateral del cargador como «empalme de 3, a
    confirmar» y ya no esta en «Puerta y placa» (la fila de 21PCB01 dice que va a la lateral);
  - 66817: lo mismo con 1101, 1102, 1201 y 1202 (12PS1, con ■ dibujados);
  - 75287 y PAE: ningun empalme (el cargador va a la bornera 12XPS);
  - la vista previa (rutear_guardado) rutea los cables con WAGO desde el empalme, igual que lo armado.

ETAPA E8-4 «puerta» (2026-10-08; foto 3 del taller):
  - el topografico trae la vista de la PUERTA (lay['puerta'], clave aparte; hoja con titulo PUERTA y canaletas o
    etiquetas del funcional, no la exterior): TPT (los dos) y 66817 en la hoja 8 «PUERTA DETALLE DE RIELES Y DUCTOS» con
    la canaleta 40x40, 21PCB01 (con su cuerpo: la placa) y 13SH1; 75287 (75441) en la hoja 5 «VISTA POSTERIOR PUERTA»
    con 13SH1 y 46DB1; el PAE (EPLAN) sin puerta (queda para despues);
  - e8['puerta']: cada cable de un aparato de la puerta (las mismas claves que su tabla en «Puerta y placa», que sigue
    igual) va de la entrada del lado de la bisagra (vista interior: bisagra izquierda = borde DERECHO del dibujo; sin
    elegir, la propuesta) por la canaleta hasta la FRANJA de bornes de su aparato (en la placa 21PCB01, el lado de abajo:
    no se inventan bornes);
  - vista previa (rutear_guardado_puerta): sin elegir = lo armado; con la bisagra a la derecha entran por el borde
    izquierdo; con puntos de paso (el perfil de abajo, como la foto 3) todos pasan por ahi y suben a su franja; un grupo
    de cables elegidos con su punto manda; una entrada elegida;
  - capa «Pasan hacia la puerta» en la lateral de la bisagra (rutear_guardado con la bisagra): los cables de la bandeja
    principal y de la otra lateral que siguen a la puerta, con el haz de la entrada a la salida a la puerta; la otra
    lateral no la tiene;
  - la lista WPC no usa la puerta: las laterales y las tablas de «Puerta y placa» dan IGUAL con y sin la vista de la
    puerta (regenerar sin lay['puerta']); regenerar conserva la entrada y los puntos de paso de la puerta.

ETAPA E8-5 «puntos exactos en las laterales» (2026-10-08; propuesta B.4):
  - el motor de bornes corre por cada lateral (su placa y sus rieles, incluido el riel tapado por las etiquetas) y deja
    los puntos en claves aparte (bornes_e8), sin renombrar textos: E6 IGUAL (e6_igual) y los textos de las puntas de E8
    salen del funcional;
  - TPT (los dos): la lateral derecha pasa de 0 a 42 de 42 con el punto del borne (el riel 1 por geometria en la capa
    '0', el riel 2 por la fila de etiquetas), con el lado del borne (33XAI 1 ARRIBA arriba del riel 2, 11XP 1 ABAJO abajo,
    13XC2 1.1 arriba del riel 1, 16XC 1 ABAJO abajo); la izquierda queda aproximada (12PB1: la bateria no esta en el
    catalogo; el cargador va con WAGO) con aviso;
  - 75287: la lateral izquierda pasa de 0 a 12 de 15 (12XPS y 11XP 1 / 2); 11MS1 (seccionador, sin modelo) aproximado;
    el 11XP 3 (la pieza PE, sin punto del mapeo) aproximado con sus vecinos exactos (aprox_o 'vecinos': a la derecha del
    11XP 2) y el 11XP en orden 1101 -> 1102 -> 1103, como antes de E8-5;
  - 66817: igual o mejor (la lateral derecha tiene el riel VERTICAL: el motor no la cubre y queda aproximada con aviso);
  - PAE (EPLAN): sin mapeo automatico de las laterales (manda su mapeo verificado), 36 de 36 como antes;
  - cada punto exacto cae dentro de la placa de su lateral y dos bornes distintos no caen en el mismo punto;
  - ajuste a mano (estacion8.rutear_punto, la de POST /e8/punto): el recorrido sale del punto nuevo; con el mismo punto da
    lo armado; regenerar con el punto en bornes_usuario lo deja exacto ('usuario') y E6 no cambia.

ETAPA E8-6 «ruteo a mano por grupos» (2026-10-09, pedido del taller):
  - grupos automáticos con la tabla programa/web/e8_grupos.json, revisados contra el funcional de cada plano (GRUPOS_AUTO):
    batería 35 mm², contactora (la bobina del contactor de la bomba: BH-01-ZV / BH_01_ZV por sus cables), batería 4 / 6
    mm², solenoides (ZY, SP-n, SP_n), doorswitch (DS), pulsadores (DB, hongo), selectoras (13SH1, OFF / ON), llaves
    seccionadoras (11MS1, 13MS1) y la placa 21PCB01; cada línea de E8 marcada con su grupo (grupo_mano) y cada cable en
    un solo grupo; las líneas de las laterales con grupo conservan su ruta automática (la usa la WPC, que no cambia);
  - por producto (código + número y revisión del topográfico) con el fixture pruebas/fixtures/recorridos_e8.json: el
    tpt_constructivo (72887 rev. 8) toma el recorrido dibujado y el grupo nuevo de placa; el tpt (72887 rev. 7, mismo
    producto, otro topográfico) NO; ningún otro plano tiene nada dibujado;
  - GET / PUT /e8/grupos (web_e86): lo guardado en un trabajo aparece en otro del mismo producto y topográfico y no en
    uno de otro topográfico; 409 con una versión vieja; producto sin confirmar = se guarda en el trabajo; archivo
    atómico con respaldo; regenerar (y volver a cargar el mismo topográfico) conserva el recorrido y el cable movido;
  - cables DIRECTOS del cargador a la bornera de abajo (PAE: 1221-1226 y el RS-485 sin número a 12XPS): derecho al
    borne, sin canaleta en el medio y sin grupo; los demás planos no tienen.

ETAPA E8-7 «pines de la placa» (2026-10-09, pedido del taller: «las referencias son las mismas; a la punta del cable
agregarle la aclaración del pin», hoja 21):
  - el topográfico trae las filas de tornillos de la placa (lay['puerta']['comp']['21PCB01']['bornera']: 37 abajo y 32
    arriba, con el hueco entre el 53 y el 54) y el funcional las filas de pines numerados con su nombre y su grupo
    (e8['pines_aparato']);
  - TPT (los dos): los 22 cables de 21PCB01 llegan a SU pin (el n-ésimo tornillo de la fila del mismo largo, confianza
    alta) con la aclaración del funcional (PLACA_TPT, revisada contra la hoja 21: 'pin 42 · Signal AI5 · AP Analog Input
    #5'), en la línea de la puerta, en la tabla y en el cable del ruteo a mano (su punto en la vista de la puerta es el
    pin); 13SH1 sigue a la franja; 66817: los 27 de 21PCB01 igual (PLACA_66817);
  - 75287 (75441): la placa sin etiqueta del topográfico se reconoce como 21PCB01 (sus filas de 37 y 32 tornillos) y
    sus 35 cables de la vista de la puerta llegan a su pin, a confirmar (confianza media), con aviso;
  - PAE: sin vista de la puerta, sin pines (EPLAN: el funcional no trae pines dibujados);
  - la vista previa de la puerta (rutear_guardado_puerta) llega a los mismos pines, también con puntos de paso;
  - la tabla de «Puerta y placa» marca pin_puerta en los cables que llegan a su pin (la pastilla dice «falta el tramo
    común»), la aclaración se compara letra por letra ('RX(O)', con O: el '0' del OCR pasa a O por el contexto) y el
    grupo de los pines 13-15 del 75287 es 'Plunger Arrival Sensor / ED#11' (espacio del OCR y la barra suelta);
  - reglas sueltas (pines_e87_reglas): el '0' / 'O' por el contexto, la aclaración '(texto incompleto)' y que la E8 se
    arme igual sin el módulo pines_aparato.py (una copia del motor que no lo trae: los cables quedan en la franja, con
    aviso).

ETAPA E8-8 «placa en las laterales y sin idas y vueltas» (2026-10-13, pedido del taller):
  - ruteo.Net.por_paradas en una red de prueba (red_e88): un punto de paso en una canaleta sin salida se saltea (la ruta
    queda igual que sin el punto y se avisa su número), uno sobre el camino no cambia nada y un recorrido que da la
    vuelta por otro camino (un ciclo) no se toca;
  - las salidas a LI del PAE con el recorrido que dibujó el taller (punto de paso al costado de la canaleta del medio):
    el 1161 baja derecho a LI (550 mm, antes 1140, sin el tramo de ida y vuelta) con el punto 1 salteado; ninguna ruta
    va y vuelve; los que pasan por ese punto de camino no cambian (salidas_e88);
  - E8, entrada elegida con un punto de paso en una canaleta sin salida: se saltea en la vista previa (entrada_e88);
  - los cables de la placa (grupo 'solo_puerta' de e8_grupos.json) van en las laterales por su ruta automática (sin
    grupo_mano, con ruta y largo) y siguen con su grupo en la puerta y las tablas; sin vista de la puerta (PAE) el grupo
    lleva sin_puerta (esperado_e88);
  - el cable de comunicación (75287 y PAE: 2135 / 2136 de 12XPS; TPT: 8105 / 8106 del empalme de 12PS2): dos tramos
    con la misma punta en la lateral; sin bisagra los dos salen por la entrada; con la bisagra izquierda el de la placa
    sale por la salida a la puerta y el del fondo por la entrada (comunicacion_e88);
  - lo dibujado antes para la placa fuera de la puerta se conserva pero no se usa, con aviso (mano_fuera_e88);
  - HAZ DE LA PLACA en la puerta: «Usar la propuesta» (estacion8.haz_propuesta) arranca en la entrada a la puerta (con la
    bisagra a la derecha, por el borde izquierdo), pasa por la canaleta y sube derecho a la base del abanico, debajo de
    los pines (haz_e88); sin vista de la puerta (PAE), nada; el formato guardado (curvas, desde: 'entrada') se conserva,
    lo roto se descarta y lo de antes carga igual (formato_haz_e88); POST /e8/haz y PUT / GET /e8/grupos con el haz
    nuevo (web_haz_e88). El abanico (cada cable a su pin, sin cruzarse) lo prueban las de node (e8_haz.test.cjs)."""
import os, sys, io, json, glob, math, shutil, tarfile, tempfile, subprocess, collections, concurrent.futures as cf

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


# ------------------------------------------------------------------ etapa E8-3: empalmes con el cable propio (WAGO)
WAGOS = {   # trabajo -> (aparato, {cable: (texto de la punta, pin)})
    'tpt_constructivo': ('12PS2', {'1108': ('12PS2 +', '+ panel'), '1109': ('12PS2 -', '- panel'), '1201': ('12PS2 +', '+ batería'), '1202': ('12PS2 -', '- batería')}),
    'tpt': ('12PS2', {'1108': ('12PS2 +', '+ panel'), '1109': ('12PS2 -', '- panel'), '1201': ('12PS2 +', '+ batería'), '1202': ('12PS2 -', '- batería')}),
    '66817': ('12PS1', {'1101': ('12PS1 +', '+ panel'), '1102': ('12PS1 -', '- panel'), '1201': ('12PS1 +', '+ batería'), '1202': ('12PS1 -', '- batería')}),
}
# claves de las marcas de esos cables (antes de la etapa: no cambian, las marcas hechas se conservan)
CLAVES_WAGO = {'tpt_constructivo': {'1108|11PS1 +|12PS2 +', '1109|11PS1 -|12PS2 -', '1201|12F1|12PS2 +', '1202|12PS2 -|12XP 2.1'},
               'tpt': {'1108|11PS1 +|12PS2 +', '1109|11PS1 -|12PS2 -', '1201|12F1|12PS2 +', '1202|12PS2 -|12XP 2.1'},
               '66817': {'1101|11XP 1|12PS1 +', '1102|11XP 2|12PS1 -', '1201|12F1|12PS1 +', '1202|12PS1 -|12XP 4.1'}}
dentro_de = lambda p, b, m=0.6: b[0] - m <= p[0] <= b[2] + m and b[1] - m <= p[1] <= b[3] + m


def esperado_e83(t, e8, ins):
    con = [(L, l) for L in e8['laterales'] for l in lineas(L) if l.get('empalme') or l.get('empalme_d')]
    fil = [x for g in e8['afuera'] for x in g['cables'] if x.get('empalme')]
    if t not in WAGOS:
        chequear(not con and not fil, f"{t}: ningún empalme con un cable propio ({len(con)} en las laterales, {len(fil)} en la puerta / placa)")
        return
    ap, esp = WAGOS[t]
    ws = [(L, l) for L, l in con if (l.get('empalme') or {}).get('tipo') == 'wago']
    got = {l['num']: (l['origen'], l['empalme'].get('pin')) for L, l in ws}
    chequear(got == esp, f"{t}: WAGO con el cable propio de {ap} en {sorted(got)} con su pin {got}")
    chequear(all(l['empalme'].get('pelado') and l['empalme'].get('aparato') == ap and l['empalme'].get('texto') == f"WAGO con el cable propio de {ap} · {l['empalme']['pin']}"
                 for L, l in ws), f"{t}: la tarjeta dice «WAGO con el cable propio de {ap} · <pin>» y la punta va pelada (sin pino)")
    chequear({l['clave'] for L, l in ws if l['num'] in esp} >= CLAVES_WAGO[t], f"{t}: las claves de las marcas no cambian ({sorted(l['clave'] for L, l in ws)})")
    # el empalme: debajo del aparato, afuera de las canaletas, a la salida de una canaleta; la ruta sale de ahi
    ok = []
    for L, l in ws:
        em, r, mo = l['empalme'], l.get('ruta') or [], l.get('marca_o')
        bien = (em.get('p') and r and cerca(r[0], em['p'], 0.15) and em['p'][1] < mo[1]
                and not any(dentro_de(em['p'], d['b'], 0.3) for d in L['ductos'])
                and any(dentro_de(em['fin'], d['b']) for d in L['ductos']) and any(dentro_de(r[1], d['b']) for d in L['ductos']))
        ok.append(bien)
    chequear(ws and all(ok), f"{t}: los {len(ws)} WAGO quedan debajo de {ap}, a la salida de una canaleta, y el cable va por las canaletas hasta ahí ({sum(ok)}/{len(ws)})")
    ps = {(L['nombre'], tuple(l['empalme']['p'])) for L, l in ws}
    chequear(len(ps) == len({(L['nombre'], l['num']) for L, l in ws}), f"{t}: un WAGO al lado del otro ({len(ps)} lugares)")
    if t.startswith('tpt'):
        rs = [(L, l) for L, l in con if l['origen'].startswith('EMPALME')]
        chequear(len(rs) == 4 and all(l['empalme'].get('tipo') == 'empalme' and l['empalme'].get('n') == 3 and l['empalme'].get('confirmar')
                                      and 'empalme de 3, a confirmar' in l['empalme'].get('texto', '').lower() and L['lado'] == 'LI' for L, l in rs),
                 f"{t}: RS-485 (8105 / 8106) en la lateral del cargador como «empalme de 3, a confirmar» ({[(l['num'], l['destino']) for L, l in rs]})")
        pcb = [x for g in e8['afuera'] if g['tag'] == '21PCB01' for x in g['cables'] if x['otra'].startswith('EMPALME')]
        chequear(not any(g['tag'] == 'EMPALME' for g in e8['afuera']) and pcb and all(x['otra_donde'] == 'bandeja lateral izquierda' for x in pcb),
                 f"{t}: «Puerta y placa» sin EMPALME; 21PCB01 32 / 33 van a la bandeja lateral izquierda ({[x['otra_donde'] for x in pcb]})")
    # vista previa: los cables con WAGO salen del empalme, igual que lo armado
    if ins:
        E8 = e8_modulo()
        prev = {(x['clave_vista'], y['clave']): y for x in E8.rutear_guardado(ins, {}) for y in x['lineas']}
        lw = [(L['clave_vista'], l) for L, l in ws if 'marca_d' not in l]
        chequear(lw and all(prev.get((v, l['clave'])) and prev[(v, l['clave'])]['ruta'] == l['ruta'] for v, l in lw),
                 f"{t}: vista previa = lo armado para los {len(lw)} cables con WAGO que salen de la lateral")


# ------------------------------------------------------------------ etapa E8-4: puerta
PUERTAS = {   # trabajo -> (hoja, texto del titulo, {aparato: (cables, con cuerpo)}, canaletas)
    'tpt_constructivo': (8, 'PUERTA DETALLE DE RIELES Y DUCTOS', {'21PCB01': (22, True), '13SH1': (2, False)}, 1),
    'tpt': (8, 'PUERTA DETALLE DE RIELES Y DUCTOS', {'21PCB01': (22, True), '13SH1': (2, False)}, 1),
    '66817': (8, 'PUERTA DETALLE DE RIELES Y DUCTOS', {'21PCB01': (27, True), '13SH1': (2, False)}, 1),
    # (etapa E8-7: la placa sin etiqueta del 75441, reconocida por sus filas de tornillos, es 21PCB01)
    '75287': (5, 'VISTA POSTERIOR PUERTA', {'21PCB01': (35, True), '13SH1': (2, False), '46DB1': (2, False)}, 1),
}
lineas_p = lambda Pd: [l for p in Pd['pasos'] for l in p['lineas']]
en_caja = lambda p, b, m=0.6: b[0] - m <= p[0] <= b[2] + m and b[1] - m <= p[1] <= b[3] + m


def esperado_e84(t, e8):
    Pd = e8.get('puerta')
    if t not in PUERTAS:
        chequear(Pd is None, f"{t}: sin vista de la puerta (EPLAN: la hoja de la puerta queda para después)")
        return
    hoja, titulo, aps, nd = PUERTAS[t]
    if not chequear(isinstance(Pd, dict), f"{t}: hay vista de la puerta"):
        return
    chequear(Pd['pag'] == hoja and Pd.get('titulo') == titulo and len(Pd['ductos']) == nd,
             f"{t}: puerta en la hoja {Pd['pag']} «{Pd.get('titulo')}» con {len(Pd['ductos'])} canaleta(s)")
    got = {a['tag']: (a['n'], a['cuerpo']) for a in Pd['aparatos']}
    chequear(got == aps, f"{t}: aparatos de la puerta {got}")
    ls = lineas_p(Pd)
    afu = {x['clave'] for g in e8['afuera'] if g['tag'] in aps for x in g['cables']}
    chequear({l['clave'] for l in ls} == afu and all(g.get('en_puerta') == (g['tag'] in aps or None) for g in e8['afuera']),
             f"{t}: los {len(ls)} cables de la puerta son los de las tablas de sus aparatos (misma marca) y las tablas dicen cuáles están en la puerta")
    caja = {a['tag']: a['caja'] for a in Pd['aparatos']}
    box, ent = Pd['box'], Pd['entrada_propuesta']
    # (un cable entre dos aparatos de la puerta va de uno al otro, no entra por la entrada: desde E8-7, en el 75287 el
    # pulsador 46DB1 a la placa 21PCB01 reconocida)
    adentro = [l for l in ls if l.get('aparato_d')]
    ls = [l for l in ls if not l.get('aparato_d')]
    chequear(all(l.get('ruta') and cerca(l['ruta'][0], l['marca_o'], 0.15) and cerca(l['ruta'][-1], l['marca_d'], 0.15) for l in adentro),
             f"{t}: los {len(adentro)} cables entre dos aparatos de la puerta van de uno al otro")
    # (desde E8-7 un cable con el pin exacto de la placa llega a su pin, adentro de la placa, subiendo derecho desde la
    # franja de abajo; los demas terminan en la franja)
    franja_ok = lambda l, c: (abs(l['ruta'][0][1] - (c[1] if l['lado_franja'] == 'abajo' else c[3])) <= 0.15 if not l.get('exacto_o') else
                              (en_caja(l['ruta'][0], c, 0.15) and abs(l['ruta'][1][0] - l['ruta'][0][0]) <= 0.15 and l['ruta'][1][1] <= c[1] + 0.15))
    bien = [l for l in ls if l.get('ruta') and cerca(l['ruta'][-1], ent, 0.15) and cerca(l['ruta'][0], l['marca_o'], 0.15)
            and franja_ok(l, caja[l['aparato']]) and caja[l['aparato']][0] - 0.2 <= l['ruta'][0][0] <= caja[l['aparato']][2] + 0.2]
    chequear(len(bien) == len(ls) and abs(ent[0] - box[2]) <= 0.15 and Pd['hacia'] == 'der',
             f"{t}: los {len(bien)}/{len(ls)} cables van de la entrada propuesta {ent} (borde derecho del dibujo: bisagra a la izquierda, vista interior) a la franja de su aparato (o a su pin)")
    por_can = [l for l in ls if any(en_caja(p, d['b']) for p in l['ruta'] for d in Pd['ductos'])]
    chequear(len(por_can) == len(ls), f"{t}: los {len(por_can)}/{len(ls)} cables pasan por la canaleta de la puerta")
    cu = [a for a in Pd['aparatos'] if a['cuerpo']]
    chequear(all(l['lado_franja'] == 'abajo' for l in ls if l['aparato'] in {a['tag'] for a in cu}),
             f"{t}: a {[a['tag'] for a in cu]} (la placa) los cables llegan por la franja de abajo")


# aparatos de los cables que siguen hacia la puerta pero que la capa «Pasan hacia la puerta» lista aparte, «Sin aparato en
# el plano» (sin dibujar en el topografico y no son de la puerta: la zona hidraulica). 21PCB01 del 75287 no esta dibujado
# en la vista de la puerta pero es una placa (categoria de la puerta): pasa hacia la puerta
SIN_APARATO = {'tpt_constructivo': {'BH-01-M', 'ZY'}, 'tpt': {'BH-01-M', 'ZY'}, '66817': {'81TM01', 'BH-01-M', 'ZY'},
               '75287': {'BH-01-ZV', 'PT 001'}, '76884': set()}


def ruteo_e84(t, ins):
    """vista previa de la puerta (rutear_guardado_puerta) y transito en la lateral de la bisagra (rutear_guardado)"""
    E8 = e8_modulo()
    e8 = ins['estacion8']
    Pd = e8.get('puerta')
    if Pd:
        ls = lineas_p(Pd)
        afuera = {l['clave'] for l in ls if not l.get('aparato_d')}       # (los que entran por la entrada)
        r = E8.rutear_guardado_puerta(ins, {})
        chequear(r and [y['ruta'] for y in r['lineas']] == [l['ruta'] for l in ls] and r['entrada_propuesta'] == Pd['entrada_propuesta'],
                 f"{t} puerta: vista previa sin elegir = lo armado ({len(ls)} rutas)")
        r = E8.rutear_guardado_puerta(ins, {'bisagra': 'der'})
        chequear(r['hacia'] == 'izq' and abs(r['entrada_propuesta'][0] - Pd['box'][0]) <= 0.15
                 and all(cerca(y['ruta'][-1], r['entrada_propuesta'], 0.15) for y in r['lineas'] if y['clave'] in afuera),
                 f"{t} puerta con la bisagra a la derecha: entran por el borde izquierdo del dibujo {r['entrada_propuesta']}")
        # puntos de paso por debajo de todos los aparatos (como el perfil de abajo de la foto 3)
        H = Pd['H']; cajas = [a['caja'] for a in Pd['aparatos']]
        yp = round(min(c[1] for c in cajas) - 2 * H, 1)
        d = min(Pd['ductos'], key=lambda d: abs(d['b'][2] - Pd['box'][2]))
        xs = [round((d['b'][0] + d['b'][2]) / 2, 1), round(min(c[0] for c in cajas) - H, 1)]
        r = E8.rutear_guardado_puerta(ins, {'vistas': {'PUERTA': {'paso': [[xs[0], yp], [xs[1], yp]]}}})
        # (con el pin exacto de la placa, E8-7, el primer punto es el pin y sube derecho desde la franja: el mismo x)
        ok = [y for y in r['lineas'] if y['clave'] in afuera and y['lado_franja'] == 'abajo' and len(y['ruta']) >= 3
              and abs(y['ruta'][1][1] - yp) <= 0.15 and abs(y['ruta'][1][0] - y['ruta'][0][0]) <= 0.15]
        chequear(len(ok) == len(afuera) and not r['no_llegan'],
                 f"{t} puerta con puntos de paso a la altura {yp}: los {len(ok)}/{len(afuera)} pasan por ahí y suben derecho a su franja (o a su pin)")
        q = [round(Pd['box'][2], 1), round((Pd['box'][1] + Pd['box'][3]) / 2, 1)]
        r = E8.rutear_guardado_puerta(ins, {'vistas': {'PUERTA': {'entrada': [q]}}})
        chequear(r['entrada'] == q and all(cerca(y['ruta'][-1], q, 0.15) for y in r['lineas'] if y['clave'] in afuera), f"{t} puerta con la entrada elegida en {q}: entran ahí")
        g = [l for l in ls if l['clave'] in afuera][-1]
        cg = next(a['caja'] for a in Pd['aparatos'] if a['tag'] == g['aparato'])
        pg = [round((cg[0] + cg[2]) / 2 + 2 * H, 1), round(cg[1] - 3 * H, 1)]       # (debajo de su aparato, al costado)
        r = E8.rutear_guardado_puerta(ins, {'vistas': {'PUERTA': {'grupos': [{'id': 'g1', 'nombre': 'G', 'cables': [g['num']], 'puntos': [pg]}]}}})
        x = {y['clave']: y for y in r['lineas']}
        # (el cable se separa del tramo de su grupo en el punto mas cercano a su aparato: va hacia el punto, a su altura
        # o en su vertical)
        chequear(x[g['clave']]['salida'] == 'g1' and x[g['clave']]['ruta'] != g['ruta']
                 and any(abs(p[1] - pg[1]) <= 0.15 or abs(p[0] - pg[0]) <= 0.15 for p in x[g['clave']]['ruta'])
                 and all(x[l['clave']]['ruta'] == l['ruta'] for l in ls if l['num'] != g['num']),
                 f"{t} puerta: un grupo con el cable {g['num']} va por su punto de paso {pg} y el resto no cambia")
    # capa «Pasan hacia la puerta» en la lateral de la bisagra: cuenta solo los que van de verdad a la puerta (aparato de
    # la vista de la puerta o de una categoria de la puerta); los de un aparato sin dibujar que no es de la puerta (la zona
    # hidraulica que el topografico no dibuja) van aparte, «Sin aparato en el plano» (pulido del 2026-10-09)
    hp = e8.get('hacia_puerta') or []
    sin_esp = SIN_APARATO.get(t)
    if sin_esp is not None:
        sin = {x['aparato'] for x in hp if x.get('sin_aparato')}
        en_p = {a['tag'] for a in (Pd or {}).get('aparatos') or []}
        chequear(sin == sin_esp and not (sin & en_p),
                 f"{t}: hacia la puerta, «sin aparato en el plano» = {sorted(sin)} (se esperaba {sorted(sin_esp)}); los de la puerta: "
                 f"{sorted({x['aparato'] for x in hp if not x.get('sin_aparato')})}")
    for bis, lado in (('izq', 'LI'), ('der', 'LD')):
        L = lateral(e8, lado)
        if not (L and L['ductos']):
            continue
        r = {x['clave_vista']: x for x in E8.rutear_guardado(ins, {'bisagra': bis})}
        tr = r[L['clave_vista']].get('transito')
        n = sum(1 for x in hp if x['desde'] != lado and not x.get('sin_aparato'))
        n_sin = sum(1 for x in hp if x['desde'] != lado and x.get('sin_aparato'))
        chequear(tr and tr['n'] == n and n and tr.get('n_sin') == n_sin and len(tr.get('sin_aparato') or []) == n_sin
                 and not any(x.get('sin_aparato') for x in tr['cables'])
                 and tr['ruta'] and cerca(tr['ruta'][0], r[L['clave_vista']]['entrada_propuesta'], 0.15)
                 and cerca(tr['ruta'][-1], r[L['clave_vista']]['puerta_propuesta'], 0.15)
                 and not any(x.get('transito') for k, x in r.items() if k != L['clave_vista']),
                 f"{t} {L['nombre']} (bisagra a la {'izquierda' if bis == 'izq' else 'derecha'}): pasan hacia la puerta {tr and tr['n']} "
                 f"(de la bandeja principal {sum(1 for x in hp if x['desde'] == 'E6' and not x.get('sin_aparato'))}, de la otra lateral "
                 f"{sum(1 for x in hp if x['desde'] not in ('E6', lado) and not x.get('sin_aparato'))}) de la entrada a la salida a la "
                 f"puerta y {tr and tr.get('n_sin')} sin aparato en el plano, aparte; la otra lateral sin capa")


# ------------------------------------------------------------------ etapa E8-5: puntos exactos en las laterales
EXACTOS_E85 = {   # trabajo -> {lado: (minimo de cables con el punto del borne, total)}
    'tpt_constructivo': {'LD': (42, 42), 'LI': (0, 12)},
    'tpt': {'LD': (42, 42), 'LI': (0, 12)},
    '75287': {'LI': (12, 15)},
    '66817': {'LI': (0, 8), 'LD': (0, 9)},
    '76884': {'LI': (36, 36)},
}
# (cable, texto de la punta) -> (riel, lado del eje): el lado fisico del punto exacto coincide con el texto del funcional
LADOS_E85 = {('3301', '33XAI 1 ARRIBA'): (2, 'arriba'), ('1104', '11XP 1 ABAJO'): (2, 'abajo'),
             ('1311', '13XC2 1.1'): (1, 'arriba'), ('1601', '16XC 1 ABAJO'): (1, 'abajo'), ('2105', '32XAI 1 ARRIBA'): (2, 'arriba')}


def puntas_e85(L):
    """[(num, texto, [x, y], exacto, conf)] de las puntas de la lateral que son bornes (sin los empalmes)"""
    out = []
    for l in lineas(L):
        if not l.get('empalme'):
            out.append((l['num'], l['origen'], l['marca_o'], l['exacto_o'], l.get('conf_o')))
        if l.get('marca_d') and not l.get('empalme_d'):
            out.append((l['num'], l['destino'], l['marca_d'], l.get('exacto_d'), l.get('conf_d')))
    return out


def esperado_e85(t, e8):
    lats = e8.get('laterales') or []
    m = e8.get('mapeo') or {}
    for lado, (minimo, tot) in EXACTOS_E85.get(t, {}).items():
        L = lateral(e8, lado)
        if chequear(L is not None, f"{t}: hay lateral {lado}"):
            chequear(L['n'] == tot and L['exactos'] >= minimo and L['exactos'] == sum(1 for l in lineas(L) if l['exacto_o']),
                     f"{t} {L['nombre']}: {L['exactos']} de {L['n']} con el punto del borne (se esperaba al menos {minimo} de {tot})")
    if t == '76884':
        chequear(not m.get('vistas') and all('conf_o' not in l for L in lats for l in lineas(L)),
                 f"{t}: EPLAN sin mapeo automático de las laterales (manda el mapeo verificado del producto)")
        return
    chequear(isinstance(m.get('vistas'), list) and {v['clave'] for v in m['vistas']} == {L['clave_vista'] for L in lats} and not m.get('error'),
             f"{t}: mapeo automático de bornes de las {len(lats)} laterales ({[(v['nombre'], v['puntos']) for v in m.get('vistas') or []]})")
    # «Modelos» del plegable: solo los aparatos con algún borne ubicado (no el modelo que el motor eligió para un aparato
    # sin ningún punto, ej. la batería 12PB1 tomada como portafusible en el 66817), nunca '?'
    for v in m.get('vistas') or []:
        mods = v.get('modelos') or {}
        chequear('?' not in mods.values() and set(mods) <= set(v.get('componentes') or []) and (v.get('usados') or not mods),
                 f"{t} {v['nombre']}: «Modelos» solo de los aparatos con algún borne ubicado ({mods}; {v.get('usados')} puntas usadas)")
        sin = [a for a in v.get('avisos') or [] if any(w in a for w in ('catalogo', 'ningun ', 'geometria', 'no esta en', 'se encontro'))]
        chequear(not sin, f"{t} {v['nombre']}: los avisos del mapeo con tildes ({sin[:1]})")
    if t == '66817':
        chequear(all(not v.get('modelos') for v in m.get('vistas') or []),
                 f"{t}: sin ningún borne ubicado en las laterales, el plegable no nombra modelos ({[v.get('modelos') for v in m.get('vistas') or []]})")
    if t.startswith('tpt'):
        v = next((v for v in m.get('vistas') or [] if v['clave'].startswith('LD|')), {})
        chequear(set(v.get('modelos') or {}) == {'11XP', '13XC2', '16XC', '32XAI', '33XAI', '43XDI', '81XCM'},
                 f"{t} LD: los modelos de los 7 aparatos con sus bornes ubicados ({sorted(v.get('modelos') or {})})")
    for L in lats:
        ps = puntas_e85(L)
        ex = [p for p in ps if p[3]]
        chequear(all(dentro_de(p[2], L['placa']) for p in ex), f"{t} {L['nombre']}: los {len(ex)} puntos exactos caen dentro de la placa")
        por_punto = {}
        for num, txt, xy, _, _ in ex:
            por_punto.setdefault((round(xy[0], 1), round(xy[1], 1)), set()).add(txt)
        dobles = {k: v for k, v in por_punto.items() if len(v) > 1}
        chequear(not dobles, f"{t} {L['nombre']}: dos bornes distintos no caen en el mismo punto ({dobles})")
        chequear(all(c in ('alta', 'media', 'usuario') for _, _, _, e, c in ps if e), f"{t} {L['nombre']}: cada punto exacto dice de dónde sale (alta / media)")
        aprox = [p for p in ps if not p[3]]
        if aprox:
            chequear(any(a.startswith(L['nombre'] + ':') and 'punto aproximado' in a for a in e8.get('avisos') or []),
                     f"{t} {L['nombre']}: aviso de las {len(aprox)} puntas con el punto aproximado")
    if t.startswith('tpt'):
        ld = lateral(e8, 'LD')
        v = next((v for v in m.get('vistas') or [] if ld and v['clave'] == ld['clave_vista']), {})
        ag = {(r['origen'], round(r['yc'])) for r in v.get('rieles_agregados') or []}
        chequear({('geometria', 593), ('etiquetas', 504)} <= ag, f"{t} LD: el riel 1 por geometría (capa '0') y el riel 2 por la fila de etiquetas ({sorted(ag)})")
        for (num, txt), (riel, lado) in LADOS_E85.items():
            l = next((l for l in lineas(ld) if l['num'] == num and l['origen'] == txt), None) if ld else None
            ok = l is not None and l['exacto_o'] and l['riel'] == riel and l['lado'] == lado and (
                (l['marca_o'][1] > ld['rieles'][riel - 1]) == (lado == 'arriba'))
            chequear(ok, f"{t} LD: {num} {txt}: punto exacto en el riel {riel}, {lado} del eje "
                         f"({(l or {}).get('marca_o')}, riel {(l or {}).get('riel')}, {(l or {}).get('lado')})")
    if t == '75287':
        L = lateral(e8, 'LI')
        xps = [l for l in lineas(L)] if L else []
        chequear(xps and all(l['exacto_o'] for l in xps if l['origen'].startswith('12XPS')),
                 f"{t}: los {sum(1 for l in xps if l['origen'].startswith('12XPS'))} cables de 12XPS con el punto del borne")
        # el 11XP 3 (la pieza PE, sin punto del mapeo) sale de sus vecinos exactos 11XP 1 y 2: a la derecha del 2, y el orden
        # de cableado queda 1101 -> 1102 -> 1103 (de izquierda a derecha, como antes de E8-5)
        x11 = [l for l in xps if l['origen'].startswith('11XP ')]
        o11 = [l['num'] for l in x11]
        l2 = next((l for l in x11 if l['origen'].startswith('11XP 2 ')), None)
        l3 = next((l for l in x11 if l['origen'].startswith('11XP 3 ')), None)
        chequear(o11 == ['1101', '1102', '1103'] and l2 and l3 and not l3['exacto_o'] and l3.get('aprox_o') == 'vecinos'
                 and l2['exacto_o'] and l3['marca_o'][0] > l2['marca_o'][0] + 3 and abs(l3['marca_o'][1] - l2['marca_o'][1]) < 1,
                 f"{t}: 11XP en orden 1101 -> 1102 -> 1103 ({o11}); el 11XP 3 aproximado con los vecinos, a la derecha del 11XP 2 "
                 f"({(l3 or {}).get('marca_o')} vs {(l2 or {}).get('marca_o')}, {(l3 or {}).get('aprox_o')})")
    # un aproximado sacado de los vecinos exactos: sigue aproximado (con aviso) y cae dentro de la placa
    for L in lats:
        vs = [(l['num'], l['marca_o' if w == 'o' else 'marca_d'], l.get('exacto_' + w)) for l in lineas(L) for w in ('o', 'd') if l.get('aprox_' + w) == 'vecinos']
        if vs:
            chequear(all(not ex and dentro_de(m, L['placa']) for _, m, ex in vs),
                     f"{t} {L['nombre']}: {len(vs)} punta(s) aproximada(s) con los bornes vecinos, dentro de la placa y sin marcarse exactas ({[v[0] for v in vs]})")




def ruteo_e85(t, ins):
    """ajuste a mano (estacion8.rutear_punto, la de POST /e8/punto): con el mismo punto da lo armado; con otro punto el
    recorrido sale de ahi (y el destino de un cable de la misma lateral)"""
    E8 = e8_modulo()
    for i, L in enumerate(ins['estacion8']['laterales']):
        ls = [l for l in lineas(L) if l.get('ruta') and not l.get('empalme')]
        if not ls:
            continue
        l = ls[0]
        r0 = E8.rutear_punto(ins, {}, i, l['clave'], 'o', l['marca_o'][:2])
        igual = r0 and r0['largo_mm'] == l['largo_mm'] and len(r0['ruta']) == len(l['ruta']) and all(cerca(a, b, 0.5) for a, b in zip(r0['ruta'], l['ruta']))
        chequear(igual, f"{t} {L['nombre']}: {l['num']} con el mismo punto da el recorrido armado")
        q = [round(l['marca_o'][0] + 1.5, 2), l['marca_o'][1]]
        r1 = E8.rutear_punto(ins, {}, i, l['clave'], 'o', q)
        chequear(r1 and r1['ruta'] and cerca(r1['ruta'][0], q, 0.06) and r1['marca'] == q and r1['largo_mm'],
                 f"{t} {L['nombre']}: {l['num']} con el punto corrido a {q}: el recorrido sale de ahí ({(r1 or {}).get('ruta', [None])[0]})")
        ld = next((x for x in lineas(L) if x.get('marca_d') and x.get('ruta') and not x.get('empalme_d')), None)
        if ld:
            qd = [round(ld['marca_d'][0] - 1.5, 2), ld['marca_d'][1]]
            rd = E8.rutear_punto(ins, {}, i, ld['clave'], 'd', qd)
            chequear(rd and rd['ruta'] and cerca(rd['ruta'][-1], qd, 0.06) and cerca(rd['ruta'][0], ld['marca_o'], 0.06),
                     f"{t} {L['nombre']}: {ld['num']} (de la misma lateral) con el destino corrido a {qd}: el recorrido termina ahí")
        emp = next((x for x in lineas(L) if x.get('empalme')), None)
        if emp:
            chequear(E8.rutear_punto(ins, {}, i, emp['clave'], 'o', emp['marca_o'][:2]) is None, f"{t} {L['nombre']}: la punta de un empalme no se ajusta ({emp['num']})")
    chequear(E8.rutear_punto(ins, {}, 99, 'x', 'o', [0, 0]) is None, f"{t}: rutear_punto de una lateral que no existe: None")


# ------------------------------------------------------------------ etapa E8-6: ruteo a mano por grupos
FIXTURE_REC = os.path.join(RAIZ, 'pruebas', 'fixtures', 'recorridos_e8.json')
PLACA_RELES = {'2150', '2151', '2152', '2153', '2154', '2155'}        # (fixture: grupo nuevo de placa del tpt_constructivo)
# grupos automaticos esperados (revisados contra el funcional de cada plano): grupo -> numeros de cable
GRUPOS_TPT = {'bateria_35': {'1205', '1206'}, 'contactora': {'6102', '6103'}, 'bateria_4_6': {'1204', '1206'}, 'solenoides': {'6201', '6202'},
              'selectoras': {'1302', '1303'},
              'placa:21PCB01': {'1306', '1307', '2105', '2111', '2112', '2114', '2115', '2116', '2117', '2118', '2119', '2142', '2150', '2151',
                                '2152', '2153', '2154', '2155', '8103', '8104', '8105', '8106'}}
GRUPOS_AUTO = {
    'tpt': GRUPOS_TPT, 'tpt_constructivo': GRUPOS_TPT,
    '66817': {'bateria_35': {'1204', '1205'}, 'contactora': {'6102'}, 'bateria_4_6': {'1204', '1205'}, 'solenoides': {'6201', '6202'},
              'selectoras': {'1301', '1303'},
              'placa:21PCB01': {'1401', '1402', '2102', '2103', '2105', '2106', '2114', '2115', '2116', '2117', '2118', '2119', '2139', '2142',
                                '2150', '2151', '2152', '2153', '2160', '2161', '8101', '8102', '8103', '8104', '8105'}},
    '75287': {'bateria_35': {'1204', '1215', '1216'}, 'contactora': {'6202'}, 'bateria_4_6': {'1217', '1218'},
              'solenoides': {'6204', '6205', '6207', '6208'}, 'doorswitch': {'2128', '2129'}, 'pulsadores': {'2130', '2131'},
              'selectoras': {'1301', '1303'}, 'seccionadoras': {'1101', '1102', '1104', '1105'},
              'placa:21PCB01': {'1306', '1307', '2105', '2106', '2114', '2115', '2116', '2117', '2118', '2119', '2120', '2121', '2122', '2123',
                                '2132', '2133', '2135', '2136', '2139', '2140', '2142', '2150', '2151', '2152', '2153', '2154', '2155',
                                '2164', '2165', '2168', '2169'}},
    '76884': {'bateria_35': {'1208', '1209', '1211', '1218'}, 'contactora': {'1218', '6151'}, 'bateria_4_6': {'1202', '1206'},
              'solenoides': {'6152', '6153', '6154', '6162', '6163', '6164'}, 'doorswitch': {'2128', '2129'},
              'pulsadores': {'2130', '2131', '4211', '4212'}, 'seccionadoras': {'1101', '1102', '1154', '1155', '1301', '1302', '1303', '1304'},
              'placa:21PCB01': {'1254', '1353', '2105', '2106', '2114', '2115', '2116', '2117', '2118', '2119', '2120', '2121', '2122', '2123',
                                '2124', '2125', '2126', '2127', '2132', '2133', '2135', '2136', '2139', '2140', '2142', '2150', '2151', '2152',
                                '2153', '2154', '2155', '2156', '2157', '2166', '2167', 'MALLA 21PCB01 34', 'MALLA 21PCB01 34 (2)', 'MALLA 21PCB01 37'}},
}
CLAVE_PRODUCTO = {'tpt': '72715-1|72887|rev7', 'tpt_constructivo': '72715-1|72887|rev8', '66817': '66817-1|75775|rev8',
                  '75287': '75286-1|75441|rev6', '76884': '76857-1|ZPL-76884|rev1'}
DIRECTOS = {'76884': {'1221', '1222', '1223', '1224', '1225', '1226', 's/n 12PS1 A', 's/n 12PS1 B', 's/n 12PS1 GND', 's/n 12PS1 VCC'}}


def lineas_e8(e8):
    """todas las lineas de E8 (laterales, puerta y tablas de puerta y placa)"""
    return [l for L in e8['laterales'] for l in lineas(L)] + [l for p in (e8.get('puerta') or {}).get('pasos') or [] for l in p['lineas']] \
        + [x for g in e8['afuera'] for x in g['cables']]


def esperado_e86(t, e8):
    """grupos automaticos de cada plano, las lineas marcadas con su grupo, lo del fixture (por producto y topografico) y
    los cables directos del cargador a la bornera de abajo"""
    R = e8.get('ruteo_mano')
    if not chequear(isinstance(R, dict) and R.get('version') and e8.get('version', 0) >= 7, f"{t}: E8 versión {e8.get('version')} con el ruteo a mano"):
        return
    E8 = e8_modulo()
    import estacion8_mano as E8M
    cfg = E8M.leer_config()
    chequear([c['id'] for c in R['categorias']] == [c['id'] for c in cfg['categorias']],
             f"{t}: las categorías de la tabla e8_grupos.json ({[c['id'] for c in R['categorias']]})")
    vs = [v['clave'] for v in R['vistas']]
    esp = [L['clave_vista'] for L in e8['laterales']] + (['PUERTA'] if e8.get('puerta') else []) + ['FONDO']
    fo = e8.get('fondo') or {}
    chequear(vs == esp and fo.get('region') and fo['region'][0] < fo['region'][2] and fo['region'][1] < fo['region'][3],
             f"{t}: vistas donde se dibuja {vs} (el fondo: {fo.get('region')} con {[a['tag'] for a in fo.get('aparatos') or []]})")
    # grupos automaticos (sin lo del taller)
    nums = lambda ks: {R['cables'][k]['num'] for k in ks}
    auto = collections.defaultdict(set)
    for k, g in R['auto'].items():
        auto[g].add(k)
    got = {g: nums(ks) for g, ks in auto.items()}
    want = GRUPOS_AUTO.get(t)
    if want is not None:
        chequear(got == want, f"{t}: grupos automáticos " + ('como los del funcional: ' + ', '.join(f'{g} {len(v)}' for g, v in got.items()) if got == want else
                 f"distintos: sobran {[(g, sorted(got.get(g, set()) - want.get(g, set()))) for g in set(got) | set(want) if got.get(g, set()) - want.get(g, set())]}, "
                 f"faltan {[(g, sorted(want.get(g, set()) - got.get(g, set()))) for g in set(got) | set(want) if want.get(g, set()) - got.get(g, set())]}"))
    # cada linea de E8 marcada con su grupo (el efectivo) y nada mas
    ls = lineas_e8(e8)
    # (desde E8-8: en las laterales, un cable de un grupo 'solo_puerta' —la placa— va por el ruteo automatico, sin grupo)
    solo = {g['id'] for g in R['grupos'] if g.get('solo_puerta')}
    en_lat = {id(l) for L in e8['laterales'] for l in lineas(L)}
    esp_g = lambda l: None if id(l) in en_lat and R['miembro'].get(l['clave']) in solo else R['miembro'].get(l['clave'])
    mal = [l['num'] for l in ls if l.get('grupo_mano') != esp_g(l)]
    sin = [k for k in R['miembro'] if not any(l['clave'] == k for l in ls)]
    chequear(not mal and not sin, f"{t}: {sum(1 for l in ls if l.get('grupo_mano'))} líneas de E8 marcadas con su grupo de ruteo a mano"
             + (f'; mal: {mal[:6]}' if mal else '') + (f'; sin línea: {sin[:6]}' if sin else ''))
    chequear(all(set(g['cables']) == {k for k, v in R['miembro'].items() if v == g['id']} and g['n'] == len(g['cables']) for g in R['grupos']),
             f"{t}: cada cable en un solo grupo ({len(R['grupos'])} grupos, {len(R['miembro'])} cables)")
    # la WPC no usa estos largos: las lineas de las laterales con grupo siguen con su ruta automatica (la lee la WPC)
    gl = [l for L in e8['laterales'] for l in lineas(L) if l.get('grupo_mano')]
    chequear(all(l.get('ruta') and l.get('largo_mm') for l in gl), f"{t}: las {len(gl)} líneas de las laterales con grupo conservan la ruta automática (la usa la WPC)")
    # por producto: la clave y lo del fixture (solo el tpt_constructivo: producto 72715-1 con el topografico 72887 rev. 8)
    chequear(R.get('clave_producto') == CLAVE_PRODUCTO[t] and R.get('por_producto'), f"{t}: se guarda por producto ({R.get('clave_producto')})")
    dib = sorted(g['id'] for g in R['grupos'] if g['dibujado'])
    if t == 'tpt_constructivo':
        b35 = next((g for g in R['grupos'] if g['id'] == 'bateria_35'), {})
        nu = next((g for g in R['grupos'] if g['id'] == 'nuevo:fixture1'), {})
        pl = next((g for g in R['grupos'] if g['id'] == 'placa:21PCB01'), {})
        chequear(R.get('version_almacen') == 3 and dib == ['bateria_35', 'nuevo:fixture1']
                 and [x['vista'] for x in b35.get('tramos') or []] == ['LI|vista lateral izquierda interior', 'FONDO'],
                 f"{t}: el recorrido dibujado del producto (fixture): {dib}, tramos de «Batería 35 mm²» en {[x['vista'] for x in b35.get('tramos') or []]}")
        chequear(nums(nu.get('cables') or []) == PLACA_RELES and nums(pl.get('cables') or []) == GRUPOS_TPT['placa:21PCB01'] - PLACA_RELES and not nu.get('auto'),
                 f"{t}: el grupo nuevo de placa del taller con {sorted(nums(nu.get('cables') or []))} (movidos a mano) y «Placa 21PCB01» con {pl.get('n')}")
        chequear(any('ya no está en este trabajo' in a for a in R.get('avisos') or []), f"{t}: aviso del cable movido que no está en el trabajo ({R.get('avisos')})")
        # (pulido 2026-10-09) un grupo nuevo de placa sin aparato (trabajo sin placas) va al final, después de los que
        # tienen aparato aunque su id vaya antes (como E8M.efectivo de la pantalla)
        R2 = json.loads(json.dumps(R))
        man = json.loads(json.dumps(R2.get('manual') or {}))
        man.setdefault('nuevos', []).append({'id': 'nuevo:000', 'nombre': 'Placa · grupo 1', 'categoria': 'placa', 'aparato': None})
        E8M.aplicar(R2, man)
        chequear([g['id'] for g in R2['grupos']][-2:] == ['nuevo:fixture1', 'nuevo:000'],
                 f"{t}: un grupo de placa sin aparato va al final ({[g['id'] for g in R2['grupos']][-3:]})")
        # en la lateral izquierda: 1205 (35 mm², bateria) marcado con su grupo, que esta dibujado
        li = lateral(e8, 'LI')
        l35 = [l for l in lineas(li) if l['num'] == '1205'] if li else []
        chequear(l35 and all(l.get('grupo_mano') == 'bateria_35' for l in l35), f"{t} LI: 1205 (batería 35 mm²) con su grupo dibujado")
    else:
        chequear(not dib and not any(g['id'].startswith('nuevo:') for g in R['grupos']) and R.get('version_almacen') == 0,
                 f"{t}: nada dibujado ni corregido para este producto y topográfico (el fixture es de otro: {dib})")
    # cables directos del cargador a la bornera de abajo (PAE): derecho al borne, sin canaleta en el medio, sin grupo
    dl =[(L, l) for L in e8['laterales'] for l in lineas(L) if l.get('directo')]
    esp_d = DIRECTOS.get(t, set())
    ok = {l['num'] for _, l in dl} == esp_d and all(
        l['ruta'] and cerca(l['ruta'][0], l['marca_o'], 0.06) and cerca(l['ruta'][-1], l['marca_d'], 0.06) and len(l['ruta']) <= 4
        and E8.sin_canaleta_en_medio(L['ductos'], l['marca_o'], l['marca_d']) and l['largo_mm'] <= 100 and not l.get('grupo_mano') for L, l in dl)
    chequear(ok, f"{t}: {len(dl)} cables directos del cargador al borne, sin el ducto" + (f" ({sorted(l['num'] for _, l in dl)[:4]}…, {sorted({l['largo_mm'] for _, l in dl})} mm)" if dl else ''))


# ------------------------------------------------------------------ etapa E8-7: pines de la placa
# cable -> (pin, nombre, grupo) de la placa 21PCB01, revisado contra la hoja 21 de cada funcional (letra por letra: el
# 'RX(O)' del pin 33 va con O)
PLACA_TPT = {
    '2142': ('42', 'Signal AI5', 'AP Analog Input #5'), '1306': ('48', 'Battery +', 'Feeder'), '1307': ('49', 'Battery -', 'Feeder'),
    '2150': ('50', 'DO 1+', 'Solenoid Valve #1'), '2151': ('51', 'DO 1-', 'Solenoid Valve #1'), '2152': ('52', 'DO 2+', 'Solenoid Valve #1'),
    '2153': ('53', 'DO 2-', 'Solenoid Valve #1'), '2154': ('54', 'DO 3+', 'Solenoid Valve #2'), '2155': ('55', 'DO 3-', 'Solenoid Valve #2'),
    '2105': ('5', 'Signal AI2', 'LP Analog Input #2'), '2111': ('11', 'Signal AI6', 'PB *Analog Input #6*'),
    '2112': ('12', 'Return', 'PB *Analog Input #6*'), '2114': ('14', 'Signal', 'Plunger Arrival Sensor / ED#11'),
    '2115': ('15', 'Return', 'Plunger Arrival Sensor / ED#11'), '2116': ('16', 'DI 1+', 'Position Sensor #1'),
    '2117': ('17', 'DI 1-', 'Position Sensor #1'), '2118': ('18', 'DI 2+', 'Position Sensor #1'), '2119': ('19', 'DI 2-', 'Position Sensor #1'),
    '8105': ('32', 'RS485 A / RS232 TX(I)', 'Comunication Port #2'), '8106': ('33', 'RS485 B / RS232 RX(O)', 'Comunication Port #2'),
    '8103': ('35', 'RS485 A', 'Comunication Port #1'), '8104': ('36', 'RS485 B', 'Comunication Port #1')}
PLACA_66817 = {   # (algunos; los 27 llegan a su pin)
    '2102': ('2', 'Signal AI1', 'WP Analog Input #1'), '2114': ('14', 'Signal', 'External Permisive ED#11'),
    '2139': ('39', 'Signal AI3', 'Analog Input #3'), '1401': ('48', 'Battery +', 'Feeder'), '2161': ('61', 'DO 6-', 'Solenoid Valve #3'),
    '8104': ('32', 'RS485 A / RS232 TX(I)', 'Comunication Port #2'), '8103': ('37', 'Return', 'Comunication Port #1')}
PLACA_75287 = {   # (algunos; la placa sin etiqueta reconocida: los 35 de la vista de la puerta, a confirmar)
    '2105': ('5', 'Signal AI2', 'LP Analog Input #2'), '2142': ('42', 'Signal AI5', 'AP Analog Input #5'), '1306': ('48', 'Battery +', 'Feeder'),
    '2128': ('28', 'DI 7+', 'Position Sensor #4'), '2135': ('35', 'RS485 A', 'Comunication Port #1'), '2169': ('69', 'DI 10-', 'DI#10')}
PINES_E87 = {   # trabajo -> (cables de 21PCB01 en la vista de la puerta con su pin, confianza, reconocida sin etiqueta, esperado)
    'tpt_constructivo': (22, 'alta', False, PLACA_TPT), 'tpt': (22, 'alta', False, PLACA_TPT),
    '66817': (27, 'alta', False, PLACA_66817), '75287': (35, 'media', True, PLACA_75287)}
# pin -> (nombre, grupo) del funcional, con o sin cable (e8['pines_aparato']): el 'RX(O)' con O y el grupo de los pines
# 13-15 con el espacio y la barra (en el 75287 la barra sube hasta el renglon de arriba y las letras van casi tan
# separadas como las palabras)
FUNCIONAL_E87 = {
    'tpt_constructivo': {'33': ('RS485 B / RS232 RX(O)', 'Comunication Port #2'), '14': ('Signal', 'Plunger Arrival Sensor / ED#11')},
    'tpt': {'33': ('RS485 B / RS232 RX(O)', 'Comunication Port #2')},
    '66817': {'33': ('RS485 B / RS232 RX(O)', 'Comunication Port #2')},
    '75287': {'33': ('RS485 B / RS232 RX(O)', 'Comunication Port #2'), '13': ('Power Sup.', 'Plunger Arrival Sensor / ED#11'),
              '14': ('Signal', 'Plunger Arrival Sensor / ED#11'), '11': ('Signal AI6', 'PB Analog Input #6')}}


def esperado_e87(t, e8, lay):
    """pines de la placa: el punto de cada pin en el dibujo y la aclaracion del funcional"""
    if t not in PINES_E87:
        chequear(not e8.get('pines_aparato') and not e8.get('puerta'), f"{t}: sin vista de la puerta ni pines de la placa (EPLAN)")
        return
    n, conf, reco, esp = PINES_E87[t]
    pa = (e8.get('pines_aparato') or {}).get('21PCB01')
    if not chequear(isinstance(pa, dict), f"{t}: e8['pines_aparato'] trae la placa 21PCB01"):
        return
    chequear(pa['hoja'] == '21' and [f['n'] for f in pa['filas']] == [32, 37] and sum(1 for x in pa['pines'].values() if x.get('punto')) == 69
             and bool(pa['reconocido']) == reco,
             f"{t}: el funcional (hoja {pa['hoja']}) da las filas de pines {[(f['n'], f['de'], f['a']) for f in pa['filas']]} y los 69 tienen su punto"
             + (' (placa sin etiqueta reconocida)' if reco else ''))
    Pd = e8.get('puerta') or {}
    ap = next((a for a in Pd.get('aparatos') or [] if a['tag'] == '21PCB01'), None)
    if not chequear(ap is not None, f"{t}: 21PCB01 está en la vista de la puerta"):
        return
    chequear(bool(ap.get('reconocido')) == reco, f"{t}: 21PCB01 {'sin etiqueta, reconocida por su bornera' if reco else 'con su etiqueta'}")
    if reco:
        chequear(any('placa dibujada sin etiqueta es 21PCB01' in a for a in e8.get('avisos') or []), f"{t}: aviso de la placa reconocida sin etiqueta")
    comp = ((lay or {}).get('puerta') or {}).get('comp') or {}
    bor = (comp.get('21PCB01') or {}).get('bornera') or next((g['bornera'] for g in ((lay or {}).get('puerta') or {}).get('sin_etiqueta') or []
                                                              if sorted(len(f['xs']) for f in g['bornera']) == [32, 37]), [])
    filas = {len(f['xs']): f for f in bor}
    chequear(37 in filas and 32 in filas and filas[32]['y'] > filas[37]['y'],
             f"{t}: el topográfico trae las filas de tornillos de la placa (37 abajo, 32 arriba): {[(len(f['xs']), f['y']) for f in bor]}")
    ls = [l for p in Pd['pasos'] for l in p['lineas'] if l['aparato'] == '21PCB01']
    mal = []
    for l in ls:
        pin = str(l.get('pin'))
        fila, i = (filas.get(37), int(pin) - 1) if int(pin) <= 37 else (filas.get(32), int(pin) - 38)
        tor = [fila['xs'][i], fila['y']] if fila and 0 <= i < len(fila['xs']) else None
        if not (l.get('exacto_o') and l.get('conf_o') == conf and tor and cerca(l['marca_o'], tor, 0.06) and cerca(l['ruta'][0], tor, 0.1)
                and l.get('aclaracion', '').startswith(f'pin {pin} · ')):
            mal.append(l['num'])
    chequear(len(ls) == n and not mal, f"{t}: los {len(ls)} cables de 21PCB01 llegan a su tornillo (el n-ésimo de su fila), confianza {conf}, con la aclaración"
             + (f'; mal: {mal[:6]}' if mal else ''))
    por_num = {}
    for l in ls:
        por_num.setdefault(l['num'], l)
    tab = {x['num']: x for g in e8['afuera'] if g['tag'] == '21PCB01' for x in g['cables']}
    R = e8.get('ruteo_mano') or {}
    for num, (pin, nom, gru) in esp.items():
        l, x = por_num.get(num), tab.get(num)
        txt = f'pin {pin} · {nom} · {gru}'
        cb = next((c for k, c in (R.get('cables') or {}).items() if c['num'] == num and c.get('aclaracion')), None)
        chequear(l is not None and l.get('aclaracion') == txt and str(l.get('pin')) == pin and x is not None and x.get('aclaracion') == txt
                 and x.get('pin_puerta') and cb is not None and cb['aclaracion'] == txt and cb.get('pin_puerta')
                 and cerca((cb['puntos'].get('PUERTA') or [[0, 0]])[0], l['marca_o'], 0.06),
                 f"{t}: {num} → {txt}" + ('' if l is not None and l.get('aclaracion') == txt else f" (salió {l and l.get('aclaracion')!r})"))
    # la tabla de «Puerta y placa»: pin_puerta (la pastilla del grupo dice «falta el tramo común») en los cables de la placa
    # que llegan a su pin, y en ningun otro
    con_pin = {l['num'] for l in ls if l.get('exacto_o')} | {      # (75287: 46DB1 → 21PCB01 30 / 31, la otra punta)
        l['num'] for p in Pd['pasos'] for l in p['lineas'] if l.get('aparato_d') == '21PCB01' and l.get('exacto_d')}
    filas_tab = [x for g in e8['afuera'] for x in g['cables']]
    mal_t = [x['num'] for x in filas_tab if bool(x.get('pin_puerta')) != (x['num'] in con_pin and any(
        g['tag'] == '21PCB01' and x in g['cables'] for g in e8['afuera']))]
    chequear(not mal_t and sum(1 for x in filas_tab if x.get('pin_puerta')) >= len(con_pin),
             f"{t}: la tabla marca pin_puerta en los {sum(1 for x in filas_tab if x.get('pin_puerta'))} cables de 21PCB01 que llegan a su pin"
             + (f'; mal: {mal_t[:6]}' if mal_t else ''))
    for pin, (nom, gru) in FUNCIONAL_E87.get(t, {}).items():
        x = pa['pines'].get(pin) or {}
        chequear(x.get('nombre') == nom and x.get('grupo') == gru and not x.get('incompleto'),
                 f"{t}: el funcional da el pin {pin} = «{nom}» ({gru})" + ('' if x.get('nombre') == nom and x.get('grupo') == gru
                                                                        else f" (salió «{x.get('nombre')}» ({x.get('grupo')}))"))
    chequear(not any(x.get('incompleto') for x in pa['pines'].values()), f"{t}: con el OCR de apoyo ningún pin queda con el texto incompleto")
    otros = [l for p in Pd['pasos'] for l in p['lineas'] if l['aparato'] != '21PCB01']
    chequear(all(not l.get('exacto_o') and not l.get('aclaracion') and l.get('franja') for l in otros),
             f"{t}: los {len(otros)} cables de los otros aparatos de la puerta siguen llegando a la franja")


def pines_e87_reglas():
    """reglas sueltas de los pines de la placa: el '0' / 'O' por el contexto, la aclaracion con el texto incompleto y la E8
    sin el modulo pines_aparato.py (VECTOR copia el motor archivo por archivo)"""
    print('\npines de la placa: reglas sueltas')
    E8 = e8_modulo()
    import pines_aparato as PA
    casos = {('RX(0)', None): 'RX(O)', ('RS232 RX(0)', None): 'RS232 RX(O)', ('C0M', None): 'COM', ('AI0', None): 'AI0',
             ('DI 10+', None): 'DI 10+', ('DO 0+', None): 'DO 0+', ('RX(0)', ('R', 'X', '(', '0', ')')): 'RX(0)',
             ('RX(0)', ('R', None, '(', None, ')')): 'RX(O)'}
    mal = [(t, labs, PA._cero_o(t, labs)) for (t, labs), esp in casos.items() if PA._cero_o(t, list(labs) if labs else None) != esp]
    chequear(not mal, "el '0' que puso el OCR es O entre paréntesis después de letras o entre mayúsculas; el que leyó el diccionario, "
             "o al final o junto a cifras, queda" + (f'; mal: {mal}' if mal else ''))
    chequear(PA.aclaracion('42', {'nombre': 'Signal AI5', 'grupo': 'AP Analog Input #5'}) == 'pin 42 · Signal AI5 · AP Analog Input #5'
             and PA.aclaracion('46', {'nombre': 'AUX +', 'grupo': 'Feed', 'incompleto': True}) == 'pin 46 · AUX + · Feed · (texto incompleto)'
             and PA.aclaracion('3', {'nombre': 'Return'}) == 'pin 3 · Return',
             "la aclaración: 'pin N · nombre · grupo', sin grupo sin esa parte, y con letras sin leer «(texto incompleto)»")
    # sin el modulo: la E8 se arma igual, los cables de la placa quedan en la franja, con aviso
    viejo = sys.modules.get('pines_aparato')
    sys.modules['pines_aparato'] = None                 # (import pines_aparato -> ModuleNotFoundError)
    try:
        P, info, av = E8.pines_puerta(None, {'1': {'nodes': {}}}, {'comp': {'21PCB01': {'bornera': [{'y': 0, 'xs': [1, 2, 3]}]}}}, {}, {'21PCB01'})
        chequear(P and not info and any('pines_aparato' in a and 'quedan en la franja' in a for a in av),
                 f"sin pines_aparato.py la E8 no se cae: los cables de la placa quedan en la franja, con aviso ({av[:1]})")
    except Exception as ex:                                                # noqa: BLE001
        chequear(False, f'sin pines_aparato.py la E8 no se cae ({type(ex).__name__}: {ex})')
    finally:
        if viejo is not None:
            sys.modules['pines_aparato'] = viejo
        else:
            sys.modules.pop('pines_aparato', None)


def ruteo_e87(t, ins):
    """la vista previa de la puerta llega a los mismos pines (sin elegir y con puntos de paso)"""
    if t not in PINES_E87:
        return
    E8 = e8_modulo()
    Pd = ins['estacion8'].get('puerta') or {}
    ls = {l['clave']: l for p in Pd.get('pasos') or [] for l in p['lineas'] if l.get('exacto_o')}
    H = Pd.get('H') or 24.8
    cajas = [a['caja'] for a in Pd.get('aparatos') or []]
    yp = round(min(c[1] for c in cajas) - 2 * H, 1)
    for rec, nom in (({}, 'sin elegir'), ({'vistas': {'PUERTA': {'paso': [[round(Pd['box'][2] - H, 1), yp], [round(min(c[0] for c in cajas) - H, 1), yp]]}}}, 'con puntos de paso')):
        r = E8.rutear_guardado_puerta(ins, rec)
        ys = [y for y in r['lineas'] if y['clave'] in ls]
        chequear(len(ys) == len(ls) and all(cerca(y['ruta'][0], ls[y['clave']]['marca_o'], 0.1) and cerca(y['marca_o'], ls[y['clave']]['marca_o'], 0.06) for y in ys),
                 f"{t} puerta, vista previa {nom}: los {len(ys)} cables con pin siguen llegando a su pin")


# ------------------------------------------------------------------ etapa E8-8: placa en las laterales y sin idas y vueltas
def retroceso(r):
    """la ruta va y vuelve por el mismo camino en algun vertice (A -> B -> A: un tramo vuelve sobre el anterior)"""
    for a, b, c in zip(r or [], (r or [])[1:], (r or [])[2:]):
        u, v = (b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])
        if abs(u[0] * v[1] - u[1] * v[0]) < 0.5 and u[0] * v[0] + u[1] * v[1] < 0:
            return True
    return False


def sobre(r, q, tol=0.15):
    """el punto q esta sobre la polilinea r (en algun tramo)"""
    for a, b in zip(r or [], (r or [])[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L2)) if L2 else 0.0
        if math.dist(q, (a[0] + t * dx, a[1] + t * dy)) <= tol:
            return True
    return False


def red_e88():
    """ruteo.Net.por_paradas en una red de prueba: V (vertical, de y 0 a 200), H (horizontal a la altura 100, con la punta
    derecha SIN SALIDA) y B (horizontal abajo, a la altura 10). El cable sale de arriba de V y sale de la red por la
    izquierda de abajo"""
    print('\nsin idas y vueltas: ruteo.Net.por_paradas (red de prueba)')
    e8_modulo()
    from ruteo import Net, route_line
    V = dict(b=[0, 0, 20, 200], h=False, ex=False)
    H = dict(b=[20, 90, 200, 110], h=True, ex=False)
    B = dict(b=[20, 0, 200, 20], h=True, ex=False)

    def ruta(ductos, por):
        sal = []
        r = route_line(Net(ductos), (10, 190), 0, None, None, False, True, False, por=por, o_red=True, salteados=sal)
        return r, sal
    r0, s0 = ruta([V, H, B], [[-30, 10]])
    chequear(r0 == [[10.0, 190.0], [10.0, 10.0], [-30.0, 10.0]] and s0 == [], f'sin puntos de paso: baja derecho por V y sale ({r0})')
    r1, s1 = ruta([V, H, B], [[180, 100], [-30, 10]])
    chequear(r1 == r0 and s1 == [1] and not retroceso(r1),
             f'un punto de paso en la punta sin salida de H: se saltea (punto {s1}) y la ruta queda como sin el punto, sin ir y volver ({r1})')
    r2, s2 = ruta([V, H, B], [[185, 130], [-30, 10]])
    chequear(r2 == r0 and s2 == [1], f'un punto al costado de H (fuera de la canaleta): igual, se saltea ({s2})')
    r3, s3 = ruta([V, H, B], [[10, 50], [-30, 10]])
    chequear(r3 == r0 and s3 == [], f'un punto de paso sobre el camino no cambia nada ({s3})')
    r4, s4 = ruta([V, H, B], [[180, 100], [10, 50], [-30, 10]])
    chequear(r4 == r0 and s4 == [1], f'dos puntos: el de la canaleta sin salida se saltea y el del camino queda ({s4})')
    # con una vertical a la derecha que une H y B, H ya no es sin salida: un punto en esa vertical hace dar la vuelta (un
    # ciclo por otro camino, no ida y vuelta): no se toca
    V2 = dict(b=[180, 0, 200, 110], h=False, ex=False)
    r5, s5 = ruta([V, H, B, V2], [[190, 50], [-30, 10]])
    chequear(s5 == [] and [190.0, 50.0] not in (r5 or []) and r5 and any(p[0] == 190.0 for p in r5) and not retroceso(r5),
             f'un recorrido que da la vuelta por otra canaleta (ciclo) no se recorta ({r5})')


# el recorrido de «Todos los LI» que dibujo el taller en el PAE (trabajo 6a5c9cb6a473, 2026-10-13): el primer punto cae al
# costado de la canaleta horizontal del medio; el 1161 iba hasta (807,8; 582,8) y volvia (1140 mm)
SALIDA_PAE_TALLER = [{'aplica': 'LI', 'id': 'li', 'nombre': 'Todos los LI', 'puntos': [[807.82, 650.42], [566.33, 444.81]]},
                     {'aplica': 'LD', 'id': 'ld', 'nombre': 'Todos los LD', 'puntos': []}]
RUTA_1161 = [[637.3, 696.4], [637.3, 731.7], [601.8, 731.7], [601.8, 444.8], [566.3, 444.8]]


def salidas_e88(d=BASES):
    """las salidas a LI del PAE con el recorrido del taller (instructivo.rutear_salidas sobre las lineas del PAE de las
    bases, el mismo topografico)"""
    print('\nsin idas y vueltas: salidas a LI del PAE con el recorrido del taller')
    e8_modulo()
    from instructivo import rutear_salidas
    from ruteo import Net
    ins = cargar(d, 'ins', '76884')
    if not chequear(isinstance(ins, dict), 'hay ins_76884.json'):
        return
    ls = [l for p in ins['pasos'] for l in p['lineas'] if l['destino'] in ('LI', 'LD')]
    r = rutear_salidas(ls, ins['topo'], SALIDA_PAE_TALLER)
    x = next((y for l, y in zip(ls, r) if l['num'] == '1161'), None)
    chequear(x and x['ruta'] == RUTA_1161 and x['salteados'] == [1] and x['largo_mm'] == 550,
             f"1161: baja derecho a LI, sin el tramo de ida y vuelta en la canaleta del medio ({x and x['largo_mm']} mm, punto salteado {x and x['salteados']})")
    malas = [l['num'] for l, y in zip(ls, r) if retroceso(y['ruta'])]
    chequear(not malas, f'ninguna de las {len(ls)} rutas a LI / LD va y vuelve por el mismo camino ({malas[:6]})')
    # los que pasan por el punto de camino (vienen de la derecha de la canaleta del medio) no lo saltean y pasan por ahi
    net = Net(ins['topo']['ductos'])
    q = net.nodes[net.en_red(SALIDA_PAE_TALLER[0]['puntos'][0])[0]]
    pasan = [l['num'] for l, y in zip(ls, r) if y['salida'] == 'li' and not y['salteados']]
    por_ahi = [n for n, y in zip([l['num'] for l in ls], r) if y['salida'] == 'li' and not y['salteados'] and sobre(y['ruta'], q)]
    salt = [l['num'] for l, y in zip(ls, r) if y['salteados']]
    chequear(salt and pasan and len(por_ahi) == len(pasan),
             f'{len(salt)} saltean el punto 1 y los otros {len(pasan)} de «Todos los LI» pasan por él de camino ({por_ahi[:4]}…)')
    # sin el punto de paso: los que lo saltean dan IGUAL que con la salida sola
    r0 = rutear_salidas(ls, ins['topo'], [dict(SALIDA_PAE_TALLER[0], puntos=SALIDA_PAE_TALLER[0]['puntos'][-1:]), SALIDA_PAE_TALLER[1]])
    dif = [l['num'] for l, y, y0 in zip(ls, r, r0) if y['salteados'] and y['ruta'] != y0['ruta']]
    chequear(not dif, f'los que saltean el punto quedan igual que con la salida sola ({dif[:6]})')


def entrada_e88(t, ins):
    """E8: una entrada elegida con un punto de paso en una canaleta sin salida (la punta libre de una canaleta de la
    lateral, antes de la entrada propuesta): se saltea, ninguna ruta va y vuelve y la vista previa dice los salteados"""
    E8 = e8_modulo()
    for L in ins['estacion8']['laterales']:
        ss = salen(L)
        if not (L['ductos'] and ss and L.get('entrada_propuesta')):
            continue
        ok = None
        for fin_, dr, _ in E8.puntas_libres(L['ductos']):
            rec = {'vistas': {L['clave_vista']: {'entrada': [list(fin_), L['entrada_propuesta']]}}}
            r = [x for x in E8.rutear_guardado(ins, rec) if x['clave_vista'] == L['clave_vista']][0]
            if any(y.get('salteados') for y in r['lineas']):
                ok = (fin_, r)
                break
        if not chequear(ok, f"{t} {L['nombre']}: hay una punta de canaleta que hace ir y volver a algún cable"):
            continue
        fin_, r = ok
        salt = [y for y in r['lineas'] if y.get('salteados')]
        chequear(all(y['salteados'] == [1] for y in salt) and not any(retroceso(y['ruta']) for y in r['lineas']),
                 f"{t} {L['nombre']}: entrada elegida con un punto en la punta sin salida {[round(v, 1) for v in fin_]}: "
                 f"{len(salt)} de {len(r['lineas'])} lo saltean (punto 1) y ninguna ruta va y vuelve")


def esperado_e88(t, e8):
    """los cables de la placa (grupo 'solo_puerta') en las laterales van por su ruta automatica (sin grupo_mano); en la
    puerta y las tablas siguen con su grupo; sin la vista de la puerta, el grupo lleva sin_puerta"""
    R = e8.get('ruteo_mano') or {}
    cats = {c['id']: c for c in R.get('categorias') or []}
    chequear(cats.get('placa', {}).get('solo_puerta') is True and all(not c.get('solo_puerta') for k, c in cats.items() if k != 'placa'),
             f"{t}: la categoría placa es 'solo_puerta' (y ninguna otra)")
    gs = {g['id']: g for g in R.get('grupos') or []}
    pl = [g for g in gs.values() if g.get('categoria') == 'placa']
    chequear(pl and all(g.get('solo_puerta') and bool(g.get('sin_puerta')) == (not e8.get('puerta')) and all(x['vista'] == 'PUERTA' for x in g['tramos']) for g in pl),
             f"{t}: los grupos de placa ({[g['id'] for g in pl]}) solo con tramos en la puerta"
             + (' y sin_puerta (el topográfico no trae la vista de la puerta)' if not e8.get('puerta') else ''))
    solo = {g['id'] for g in pl}
    lat = [l for L in e8['laterales'] for l in lineas(L) if R.get('miembro', {}).get(l['clave']) in solo]
    chequear(lat and all(not l.get('grupo_mano') and l.get('ruta') and len(l['ruta']) > 1 and l.get('largo_mm') for l in lat),
             f"{t}: los {len(lat)} cables de la placa en las laterales van por su ruta automática (sin grupo, con ruta y largo: {sorted({l['num'] for l in lat})[:6]}…)")
    resto = [l for p in (e8.get('puerta') or {}).get('pasos') or [] for l in p['lineas']] + [x for g in e8['afuera'] for x in g['cables']]
    mal = [l['num'] for l in resto if l.get('grupo_mano') != R.get('miembro', {}).get(l['clave'])]
    chequear(not mal, f"{t}: en la puerta y las tablas de «Puerta y placa» cada cable sigue con su grupo ({mal[:6]})")


# cable de comunicacion: dos tramos con la misma punta en la lateral (el del fondo y el de la placa)
COMUNICACION = {'75287': ('2135', '2136'), '76884': ('2135', '2136'), 'tpt': ('8105', '8106'), 'tpt_constructivo': ('8105', '8106')}


def comunicacion_e88(t, ins):
    """el cable de comunicacion entra a la lateral izquierda, se empalma en la punta de la lateral (la bornera del
    cargador o el empalme de 12PS2) y sigue a la placa: sin bisagra los dos tramos salen por la entrada; con la bisagra
    izquierda el de la placa sale por la salida a la puerta (del lado de la puerta) y el del fondo por la entrada"""
    if t not in COMUNICACION:
        return
    E8 = e8_modulo()
    i, L = next(((i, L) for i, L in enumerate(ins['estacion8']['laterales']) if L['lado'] == 'LI'), (None, None))
    if not chequear(L, f'{t}: hay lateral izquierda'):
        return
    for num in COMUNICACION[t]:
        ts = [l for l in salen(L) if l['num'] == num]
        pl = [l for l in ts if l.get('a_puerta')]
        fo = [l for l in ts if l.get('viene_de_e6')]
        if not chequear(len(ts) == 2 and len(pl) == 1 and len(fo) == 1 and ts[0]['origen'] == ts[1]['origen'] and not pl[0].get('grupo_mano'),
                        f"{t}: {num} tiene dos tramos con la misma punta en la lateral ({ts[0]['origen'] if ts else '—'}): a la placa y a la bandeja principal"):
            continue
        borde = min(d['b'][0] for d in L['ductos'])
        b0 = None
        for bis in (None, 'izq'):
            r = E8.rutear_guardado(ins, {'bisagra': bis})[i]
            y = {x['clave']: x for x in r['lineas']}
            a, b = y[pl[0]['clave']], y[fo[0]['clave']]
            if bis:     # (el del fondo, igual que sin bisagra)
                ok = a['sale'] == 'puerta' and fin(a['ruta'])[0] < borde and b['sale'] == 'entrada' and b['ruta'] == b0
            else:       # (los dos por la entrada: el mismo recorrido; 75287: canaletas partidas, no siempre la propuesta)
                ok = a['sale'] == 'entrada' and b['sale'] == 'entrada' and a['ruta'] == b['ruta']
                b0 = b['ruta']
            chequear(ok and cerca(a['ruta'][0], b['ruta'][0], 0.15),
                     f"{t}: {num} {'con la bisagra a la izquierda: entra por la entrada, se empalma en ' + ts[0]['origen'] + ' y sale por la salida a la puerta' if bis else 'sin bisagra: los dos tramos por la entrada (regla de E8-2)'}"
                     f" ({a['largo_mm']} / {b['largo_mm']} mm)")


def mano_fuera_e88(d=BASES):
    """lo dibujado antes para la placa fuera de la puerta (el PAE del taller: un punto en el fondo y otro en la lateral)
    se conserva pero no se usa, con aviso; en la puerta (tpt_constructivo) se usa"""
    print('\nruteo a mano de la placa: solo en la puerta')
    e8_modulo()
    import estacion8_mano as E8M
    for t in ('76884', 'tpt_constructivo'):
        ins = cargar(d, 'ins', t)
        R = json.loads(json.dumps(((ins or {}).get('estacion8') or {}).get('ruteo_mano') or {}))
        if not chequear(R.get('grupos'), f'{t}: hay ruteo a mano'):
            continue
        lat = next(v['clave'] for v in R['vistas'] if v['tipo'] == 'lateral')
        man = {'grupos': {'placa:21PCB01': {'tramos': [{'vista': 'FONDO', 'puntos': [[564.8, 446.55]]}, {'vista': lat, 'puntos': [[172.8, 454.55]]}]
                                            + ([{'vista': 'PUERTA', 'puntos': [[400.0, 300.0], [420.0, 300.0]]}] if t != '76884' else [])}}}
        E8M.aplicar(R, man)
        g = next(x for x in R['grupos'] if x['id'] == 'placa:21PCB01')
        guardado = R['manual']['grupos']['placa:21PCB01']['tramos']
        if t == '76884':
            ok = g['tramos'] == [] and g.get('sin_puerta') and not g['dibujado']
        else:
            ok = [x['vista'] for x in g['tramos']] == ['PUERTA'] and g['dibujado'] and not g.get('sin_puerta')
        chequear(ok and g.get('tramos_fuera') == 2 and len(guardado) == len(man['grupos']['placa:21PCB01']['tramos'])
                 and any('fuera de la puerta' in a and 'no se usa' in a for a in R.get('avisos') or []),
                 f"{t}: los 2 tramos de la placa fuera de la puerta se conservan en lo guardado pero no se usan, con aviso"
                 + (' (sin vista de la puerta: nada para dibujar)' if t == '76884' else ' (el de la puerta sí)'))
        # el resumen de lo que falta dibujar no cuenta la placa de un trabajo sin la vista de la puerta
        gs, falta = E8M.resumen(R)
        chequear(all(not x.get('sin_puerta') for x in gs), f'{t}: el resumen de lo que falta dibujar no cuenta los grupos sin vista de la puerta')


# ------------------------------------------------------------------ etapa E8-8: el haz de la placa en la puerta
def dentro_canaleta(p, ductos, tol=0.6):
    return any(d['b'][0] - tol <= p[0] <= d['b'][2] + tol and d['b'][1] - tol <= p[1] <= d['b'][3] + tol for d in ductos or [])


def haz_e88(t, ins):
    """«Usar la propuesta» del haz de la placa (estacion8.haz_propuesta, la de POST /e8/haz): arranca en la entrada a la
    puerta (la que se usa; con la bisagra a la derecha, por el borde izquierdo del dibujo), pasa por la canaleta y termina
    en la base del abanico, debajo de los pines y entre el primero y el ultimo, llegando derecho (el ultimo tramo
    vertical); las esquinas son curvas. Sin vista de la puerta (PAE) o sin cables de la puerta: None"""
    E8 = e8_modulo()
    e8 = ins['estacion8']
    R = e8.get('ruteo_mano') or {}
    pl = [g for g in R.get('grupos') or [] if g.get('categoria') == 'placa' and g.get('n')]
    if not e8.get('puerta'):
        chequear(pl and all(E8.haz_propuesta(ins, e8.get('recorridos'), g['cables']) is None for g in pl),
                 f'{t}: sin vista de la puerta no hay propuesta del haz de la placa')
        return
    Pd = e8['puerta']
    ls = {l['clave']: l for l in lineas_p(Pd)}
    for g in pl:
        r = E8.haz_propuesta(ins, e8.get('recorridos'), g['cables'])
        fins = [ls[k]['marca_o'] for k in g['cables'] if k in ls and ls[k].get('exacto_o')]
        if not chequear(r and fins, f"{t}: «{g['nombre']}»: hay propuesta del haz ({len(fins)} cables con su pin en la puerta)"):
            continue
        pts = [r['entrada']] + r['puntos']
        xs = [f[0] for f in fins]
        ult = (pts[-2], pts[-1])
        chequear(cerca(r['entrada'], Pd['entrada'], 0.06) and any(dentro_canaleta(p, Pd['ductos']) for p in r['puntos'])
                 and r['lado'] == 1 and r['fin'][1] < min(f[1] for f in fins) and min(xs) <= r['fin'][0] <= max(xs)
                 and abs(ult[0][0] - ult[1][0]) < 0.05 and ult[1][1] > ult[0][1]
                 and r['curvas'] == list(range(len(r['puntos']) - 1)),
                 f"{t}: «{g['nombre']}»: la propuesta arranca en la entrada {Pd['entrada']}, pasa por la canaleta y sube derecho a la base "
                 f"del abanico {r['fin']} (debajo de los pines, entre {min(xs):.1f} y {max(xs):.1f}), con las {len(r['curvas'])} esquinas en curva")
        r2 = E8.haz_propuesta(ins, {'bisagra': 'der'}, g['cables'])
        chequear(r2 and abs(r2['entrada'][0] - Pd['box'][0]) < 0.06 and cerca(r2['fin'], r['fin'], 0.06),
                 f"{t}: con la bisagra a la derecha la propuesta entra por el borde izquierdo del dibujo ({r2 and r2['entrada']}) y llega a la misma base")
    chequear(E8.haz_propuesta(ins, e8.get('recorridos'), ['no existe']) is None, f'{t}: sin cables de la puerta: sin propuesta')


def formato_haz_e88():
    """el formato del haz en programa/recorridos_e8.json: 'curvas' (indices de 'puntos') y 'desde': 'entrada' se
    conservan; lo roto se descarta (curvas que no son de un punto valido; los indices se corren si se descarta un punto);
    lo de antes (sin curvas ni desde) carga igual; con 'desde' un punto ya es un recorrido"""
    print('\nhaz de la placa: el formato guardado (nuevo y viejo)')
    e8_modulo()
    import estacion8_mano as E8M
    nuevo = {'vista': 'PUERTA', 'puntos': [[881.8, 451.0], [881.8, 379.94], [784.72, 379.94], [784.72, 405.97]], 'curvas': [1, 2], 'desde': 'entrada'}
    viejo = {'vista': 'PUERTA', 'puntos': [[880.0, 500.0], [800.0, 500.0], [779.75, 485.85]]}
    man, err = E8M.normalizar_manual({'grupos': {'placa:21PCB01': {'tramos': [nuevo]}, 'nuevo:fixture1': {'tramos': [viejo]}}})
    chequear(not err and man['grupos']['placa:21PCB01']['tramos'] == [nuevo] and man['grupos']['nuevo:fixture1']['tramos'] == [viejo],
             'el haz nuevo (curvas, desde) y el recorrido de antes se guardan tal cual')
    roto = {'vista': 'PUERTA', 'puntos': [[1, 1], 'x', [3, 3], [4, 4]], 'curvas': [0, 1, 2, True, 'a', 9, 2, -1], 'desde': 'otra'}
    man, _ = E8M.normalizar_manual({'grupos': {'g': {'tramos': [roto]}}})
    t = man['grupos']['g']['tramos'][0]
    chequear(t == {'vista': 'PUERTA', 'puntos': [[1, 1], [3, 3], [4, 4]], 'curvas': [0, 1]},
             f'lo roto se descarta: el punto inválido, las curvas que no son de un punto (y se corren), un desde desconocido ({t})')
    for desde, n, dib in (('entrada', 1, True), (None, 1, False), (None, 2, True)):
        tr = dict({'vista': 'PUERTA', 'puntos': [[1.0, 1.0], [2.0, 2.0]][:n]}, **({'desde': desde} if desde else {}))
        chequear(E8M.tramo_dibujado(tr) == dib, f"{n} punto{'s' if n > 1 else ''}{' con desde: entrada' if desde else ''}: {'dibujado' if dib else 'sin dibujar'}")
    # aplicar: el haz con desde y un solo punto cuenta como dibujado; en el PAE (sin puerta) no se usa
    for t in ('tpt_constructivo', '76884'):
        ins = cargar(BASES, 'ins', t)
        R = json.loads(json.dumps(((ins or {}).get('estacion8') or {}).get('ruteo_mano') or {}))
        if not chequear(R.get('grupos'), f'{t}: hay ruteo a mano en pruebas/bases'):
            continue
        E8M.aplicar(R, {'grupos': {'placa:21PCB01': {'tramos': [{'vista': 'PUERTA', 'puntos': [[784.0, 400.0]], 'curvas': [0], 'desde': 'entrada'}]}}})
        g = next(x for x in R['grupos'] if x['id'] == 'placa:21PCB01')
        ok = (g['dibujado'] and g['tramos'][0].get('desde') == 'entrada' and g['tramos'][0].get('curvas') == [0]) if t != '76884' else (not g['dibujado'] and g.get('sin_puerta'))
        chequear(ok, f"{t}: aplicar con el haz nuevo ({'dibujado, con desde y curvas' if t != '76884' else 'sin vista de la puerta: no se usa'})")


def web_haz_e88(tmp, d=BASES):
    """POST /e8/haz («Usar la propuesta») y el haz nuevo guardado por PUT /e8/grupos vuelve tal cual en GET; el de antes
    (fixture) sigue cargando; sin vista de la puerta (PAE): 404; datos invalidos: 400"""
    print('\nhaz de la placa: POST /e8/haz y PUT / GET /e8/grupos con el formato nuevo')
    hist = os.path.join(tmp, 'hist_haz')
    alm = os.path.join(tmp, 'recorridos_haz.json')
    shutil.copyfile(FIXTURE_REC, alm)
    os.environ.update(PLANOCABLES_RECORRIDOS_E8=alm, PLANOCABLES_HISTORIAL=hist, PLANOCABLES_MEMORIA_OCR='solo-lectura', PLANOCABLES_PORT='8796',
                      PLANOCABLES_PRODUCTOS=os.path.join(RAIZ, 'pruebas', 'fixtures', 'productos.json'))
    e8_modulo()
    import web
    web.WORK = hist
    ins_c, ins_p = cargar(d, 'ins', 'tpt_constructivo'), cargar(d, 'ins', '76884')
    if not chequear(ins_c and ins_p, f'hay instructivos en {d}'):
        return
    for j, ins in (('bbbbbbbbbb01', ins_c), ('bbbbbbbbbb02', ins_p)):
        os.makedirs(os.path.join(hist, j))
        with open(os.path.join(hist, j, 'instructivo.json'), 'w', encoding='utf-8') as f:
            json.dump(ins, f, ensure_ascii=False)
    cl = Cliente(web)
    R = ins_c['estacion8']['ruteo_mano']
    g = next(x for x in R['grupos'] if x['id'] == 'placa:21PCB01')
    r = cl.c.post('/api/trabajo/bbbbbbbbbb01/e8/haz', base_url=cl.b, json={'claves': g['cables'], 'recorridos': ins_c['estacion8']['recorridos']})
    p = r.get_json() or {}
    chequear(r.status_code == 200 and p.get('puntos') and p.get('entrada') and isinstance(p.get('curvas'), list),
             f"POST /e8/haz: {r.status_code}, {len(p.get('puntos') or [])} puntos desde la entrada {p.get('entrada')}")
    r1 = cl.c.post('/api/trabajo/bbbbbbbbbb01/e8/haz', base_url=cl.b, json={'claves': 'x'})
    r2 = cl.c.post('/api/trabajo/bbbbbbbbbb02/e8/haz', base_url=cl.b, json={'claves': g['cables']})
    chequear(r1.status_code == 400 and r2.status_code == 404 and 'vista de la puerta' in ((r2.get_json() or {}).get('error') or ''),
             f'datos inválidos: 400; PAE sin vista de la puerta: 404 con el motivo ({r1.status_code}, {r2.status_code})')
    get = lambda: (cl.get('/api/trabajo/bbbbbbbbbb01/e8/grupos').get_json() or {}).get('ruteo_mano') or {}
    R0 = get()
    man = json.loads(json.dumps(R0['manual']))
    haz = {'vista': 'PUERTA', 'puntos': p.get('puntos') or [], 'curvas': p.get('curvas') or [], 'desde': 'entrada'}
    man['grupos']['placa:21PCB01'] = {'tramos': [haz]}
    r = cl.put('/api/trabajo/bbbbbbbbbb01/e8/grupos', json={'manual': man, 'version': R0.get('version_almacen')})
    R1 = get()
    g1 = {x['id']: x for x in R1.get('grupos') or []}
    chequear(r.status_code == 200 and g1['placa:21PCB01']['dibujado'] and g1['placa:21PCB01']['tramos'] == [haz]
             and g1.get('nuevo:fixture1', {}).get('dibujado') and 'desde' not in g1['nuevo:fixture1']['tramos'][0],
             'PUT /e8/grupos con el haz nuevo (curvas, desde) y GET lo devuelve tal cual; el recorrido de antes del fixture sigue cargando')
    with open(alm, encoding='utf-8') as f:
        e = json.load(f)['productos'].get('72715-1|72887|rev8') or {}
    chequear(((e.get('manual') or {}).get('grupos') or {}).get('placa:21PCB01', {}).get('tramos') == [haz],
             'en programa/recorridos_e8.json (la copia) el haz queda con sus curvas y desde: entrada')


class Cliente:
    """test_client de la web con el Host local (la web responde 403 a otro Host)"""
    def __init__(self, web):
        self.c, self.b = web.app.test_client(), f'http://127.0.0.1:{web.PORT}'

    def get(self, u, **kw):
        return self.c.get(u, base_url=self.b, **kw)

    def put(self, u, **kw):
        return self.c.put(u, base_url=self.b, **kw)


def web_e86(tmp, d=BASES):
    """GET / PUT /e8/grupos sobre copias de los instructivos (sin rearmar): lo guardado en un trabajo aparece en otro del
    mismo producto y topografico y NO en uno de otro topografico; conflicto de version; producto sin confirmar = se guarda
    en el trabajo; archivo atomico con respaldo"""
    print('\nruteo a mano por producto (GET / PUT /e8/grupos)')
    import hashlib
    hist = os.path.join(tmp, 'hist_mano')
    alm = os.path.join(tmp, 'recorridos_mano.json')
    shutil.copyfile(FIXTURE_REC, alm)
    os.environ.update(PLANOCABLES_RECORRIDOS_E8=alm, PLANOCABLES_HISTORIAL=hist, PLANOCABLES_MEMORIA_OCR='solo-lectura', PLANOCABLES_PORT='8796',
                      PLANOCABLES_PRODUCTOS=os.path.join(RAIZ, 'pruebas', 'fixtures', 'productos.json'))
    e8_modulo()
    import web
    web.WORK = hist
    ins_c, ins_t = cargar(d, 'ins', 'tpt_constructivo'), cargar(d, 'ins', 'tpt')
    if not chequear(ins_c and ins_t and (ins_c.get('estacion8') or {}).get('ruteo_mano'), f'hay instructivos con el ruteo a mano en {d}'):
        return
    jobs = {'aaaaaaaaaa01': ins_c, 'aaaaaaaaaa02': ins_c, 'aaaaaaaaaa03': ins_t,
            'aaaaaaaaaa04': dict(ins_c, producto=dict(ins_c['producto'], confirmado=False, fuente='rotulo'))}
    for j, ins in jobs.items():
        os.makedirs(os.path.join(hist, j))
        with open(os.path.join(hist, j, 'instructivo.json'), 'w', encoding='utf-8') as f:
            json.dump(ins, f, ensure_ascii=False)
    cl = Cliente(web)
    get = lambda j: cl.get(f'/api/trabajo/{j}/e8/grupos')
    r = get('aaaaaaaaaa01')
    R = (r.get_json() or {}).get('ruteo_mano') or {}
    if not chequear(r.status_code == 200 and R.get('version_almacen') == 3, f"GET /e8/grupos: {r.status_code}, versión {R.get('version_almacen')}"):
        return
    k1302 = next(k for k, c in R['cables'].items() if c['num'] == '1302')
    man = json.loads(json.dumps(R['manual']))
    man['grupos']['solenoides'] = {'tramos': [{'vista': 'FONDO', 'puntos': [[500.0, 511.5], [620.0, 511.5]]}]}
    man['mover'][k1302] = ''                 # (sacarlo de su grupo: vuelve al ruteo automatico)
    r = cl.put('/api/trabajo/aaaaaaaaaa01/e8/grupos', json={'manual': man, 'version': 3})
    R1 = (r.get_json() or {}).get('ruteo_mano') or {}
    with open(alm, encoding='utf-8') as f:
        st = json.load(f)
    e = st['productos'].get('72715-1|72887|rev8') or {}
    chequear(r.status_code == 200 and R1.get('version_almacen') == 4 and e.get('version') == 4 and os.path.exists(alm + '.bak')
             and e.get('editado', {}).get('trabajo') == 'aaaaaaaaaa01' and '99999-1|11111|rev1' in st['productos'],
             f"PUT en un trabajo: guardado para el producto (versión {e.get('version')}, respaldo {os.path.exists(alm + '.bak')}, los otros productos quedan)")
    with open(os.path.join(hist, 'aaaaaaaaaa01', 'instructivo.json'), encoding='utf-8') as f:
        e8a = json.load(f)['estacion8']
    chequear(all(not l.get('grupo_mano') for l in lineas_e8(e8a) if l['clave'] == k1302)
             and any(l.get('grupo_mano') == 'solenoides' for l in lineas_e8(e8a)),
             'el instructivo del trabajo queda con las líneas marcadas con su grupo (1302 sin grupo)')
    RB = (get('aaaaaaaaaa02').get_json() or {}).get('ruteo_mano') or {}
    gB = {g['id']: g for g in RB.get('grupos') or []}
    chequear(gB.get('solenoides', {}).get('dibujado') and k1302 not in RB.get('miembro', {}) and (RB.get('editado') or {}).get('trabajo') == 'aaaaaaaaaa01',
             'otro trabajo del MISMO producto y topográfico ve el recorrido nuevo y el cable movido (y quién lo cambió)')
    RC = (get('aaaaaaaaaa03').get_json() or {}).get('ruteo_mano') or {}
    gC = {g['id']: g for g in RC.get('grupos') or []}
    chequear(not gC.get('solenoides', {}).get('dibujado') and not gC.get('bateria_35', {}).get('dibujado') and RC.get('miembro', {}).get(k1302) == 'selectoras',
             f"un trabajo del mismo producto con OTRO topográfico ({RC.get('clave_producto')}) no lo toma")
    r = cl.put('/api/trabajo/aaaaaaaaaa02/e8/grupos', json={'manual': man, 'version': 3})
    chequear(r.status_code == 409 and (r.get_json() or {}).get('ruteo_mano', {}).get('version_almacen') == 4,
             f'guardar con una versión vieja (lo cambió otro trabajo): 409 con lo de hoy ({r.status_code})')
    h0 = hashlib.sha1(open(alm, 'rb').read()).hexdigest()
    r = cl.put('/api/trabajo/aaaaaaaaaa04/e8/grupos', json={'manual': {'grupos': {'contactora': {'tramos': [{'vista': 'FONDO', 'puntos': [[600, 450], [669, 450]]}]}}}, 'version': None})
    RD = (r.get_json() or {}).get('ruteo_mano') or {}
    with open(os.path.join(hist, 'aaaaaaaaaa04', 'instructivo.json'), encoding='utf-8') as f:
        e8d = json.load(f)['estacion8']
    chequear(r.status_code == 200 and not RD.get('por_producto') and 'no está confirmado' in (RD.get('aviso') or '')
             and (e8d.get('mano_trabajo') or {}).get('grupos', {}).get('contactora') and hashlib.sha1(open(alm, 'rb').read()).hexdigest() == h0,
             'con el producto sin confirmar se guarda en el trabajo (mano_trabajo), con el aviso, sin tocar el archivo del producto')
    # (PUT /instructivo de la pantalla con una copia vieja: mano_trabajo lo escribe solo /e8/grupos)
    viejo = json.loads(json.dumps(jobs['aaaaaaaaaa04']))
    viejo['estacion8'].pop('mano_trabajo', None)
    cl.put('/api/trabajo/aaaaaaaaaa04/instructivo', json=viejo)
    with open(os.path.join(hist, 'aaaaaaaaaa04', 'instructivo.json'), encoding='utf-8') as f:
        chequear((json.load(f)['estacion8'].get('mano_trabajo') or {}).get('grupos', {}).get('contactora'),
                 'PUT /instructivo con una copia vieja no pisa el ruteo a mano guardado en el trabajo')
    r1 = cl.put('/api/trabajo/aaaaaaaaaa01/e8/grupos', json={'manual': {'nuevos': [{'id': 'malo id'}]}})
    r2 = cl.put('/api/trabajo/aaaaaaaaaa01/e8/grupos', json={'x': 1})
    r3 = cl.get('/api/trabajo/noexiste0000/e8/grupos')
    chequear(r1.status_code == 400 and r2.status_code == 400 and r3.status_code == 404, f'datos inválidos: 400 / 400; trabajo que no existe: 404 ({r1.status_code}, {r2.status_code}, {r3.status_code})')


def regenerar_e82(tmp):
    """regenerar conserva lo elegido; un topografico nuevo lo borra (web.gen_instructivo sobre una copia del TPT del
    constructivo, en un historial temporal). E8-6: el ruteo a mano (por producto) se conserva al regenerar y con un
    topografico nuevo del mismo producto"""
    print('\nregenerar y topográfico nuevo (tpt_constructivo)')
    hist = os.path.join(tmp, 'hist_regen')
    jid = 'e8e8e8e8e8e8'
    shutil.copytree(os.path.join(RAIZ, TRABAJOS['tpt_constructivo'][0]), os.path.join(hist, jid), ignore=shutil.ignore_patterns('*.png'))
    shutil.copyfile(FIXTURE_REC, os.path.join(tmp, 'recorridos_regen.json'))
    os.environ.update(PLANOCABLES_HISTORIAL=hist, PLANOCABLES_MEMORIA_OCR='solo-lectura', PLANOCABLES_PORT='8796',
                      PLANOCABLES_PRODUCTOS=os.path.join(RAIZ, 'pruebas', 'fixtures', 'productos.json'),
                      PLANOCABLES_RECORRIDOS_E8=os.path.join(tmp, 'recorridos_regen.json'))
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
    Pd = e8.get('puerta') or {}
    pp = [[round(Pd['box'][2] - 40, 1), 330.0], [round(Pd['box'][0] + 60, 1), 330.0]] if Pd else []     # (la puerta: puntos de paso)
    rec = {'preguntar': False, 'bisagra': 'izq', 'vistas': {
        ld['clave_vista']: {'entrada': [p], 'puerta': [], 'grupos': [{'id': 'g1', 'nombre': 'Grupo 1', 'cables': [g], 'puntos': [q]}]},
        li['clave_vista']: {'entrada': [], 'puerta': [], 'grupos': []},
        'PUERTA': {'entrada': [], 'puerta': [], 'grupos': [], 'paso': pp}}}
    ins1['estacion8']['recorridos'] = rec          # (como la pestaña: PUT /instructivo con lo elegido)
    # (E8-5) un punto ajustado a mano con 📍 en el visor de E8: la punta de la bateria (aproximada) de la lateral izquierda
    lu = next((l for l in lineas(li) if not l['exacto_o'] and not l.get('empalme')), None)
    pu_ = [round(lu['marca_o'][0] + 2.0, 2), round(lu['marca_o'][1] + 3.0, 2)] if lu else None
    if lu:
        ins1['bornes_usuario'] = dict(ins1.get('bornes_usuario') or {}, **{f"{lu['origen']}#{lu['num']}": pu_})
    with open(pj, 'w', encoding='utf-8') as f:
        json.dump(ins1, f, ensure_ascii=False)
    # (E8-6) ruteo a mano: el del fixture ya esta; el taller dibuja otro grupo y saca un cable de su grupo (PUT /e8/grupos)
    R1 = e8.get('ruteo_mano') or {}
    chequear(sorted(g['id'] for g in R1.get('grupos') or [] if g['dibujado']) == ['bateria_35', 'nuevo:fixture1'],
             f"regenerar toma el ruteo a mano guardado para el producto ({sorted(g['id'] for g in R1.get('grupos') or [] if g['dibujado'])})")
    k1303 = next((k for k, c in (R1.get('cables') or {}).items() if c['num'] == '1303'), None)
    man = json.loads(json.dumps(R1.get('manual') or {}))
    man.setdefault('grupos', {})['solenoides'] = {'tramos': [{'vista': li['clave_vista'], 'puntos': [[250.0, 531.3], [300.0, 531.3]]},
                                                            {'vista': 'FONDO', 'puntos': [[480.0, 511.5], [560.0, 511.5]]}]}
    man.setdefault('mover', {})[k1303] = 'nuevo:fixture1'
    r = Cliente(web).put(f'/api/trabajo/{jid}/e8/grupos', json={'manual': man, 'version': R1.get('version_almacen')})
    chequear(r.status_code == 200, f'PUT /e8/grupos antes de regenerar: {r.status_code} {(r.get_json() or {}).get("error") or ""}')
    ins2 = gen()
    if not ins2:
        return
    R2 = ins2['estacion8'].get('ruteo_mano') or {}
    g2 = {g['id']: g for g in R2.get('grupos') or []}
    chequear(g2.get('solenoides', {}).get('dibujado') and [t['vista'] for t in g2['solenoides']['tramos']] == [li['clave_vista'], 'FONDO']
             and R2.get('miembro', {}).get(k1303) == 'nuevo:fixture1'
             and all(l.get('grupo_mano') == 'nuevo:fixture1' for l in lineas_e8(ins2['estacion8']) if l['clave'] == k1303),
             'regenerar conserva el recorrido dibujado (dos tramos: lateral y fondo) y el cable movido de grupo')
    e8b = ins2['estacion8']
    ld2, li2 = lateral(e8b, 'LD'), lateral(e8b, 'LI')
    chequear(e8b.get('recorridos') == rec, f"regenerar conserva la entrada, el grupo y la bisagra ({e8b.get('recorridos')})")
    if chequear(lu is not None, 'hay una punta aproximada en la lateral izquierda para ajustar a mano'):
        lu2 = next((l for l in lineas(li2) if l['clave'] == lu['clave']), None)
        chequear(lu2 and lu2['exacto_o'] and lu2.get('conf_o') == 'usuario' and lu2['marca_o'][:2] == pu_ and lu2.get('ruta') and cerca(lu2['ruta'][0], pu_, 0.06)
                 and li2['exactos'] == li['exactos'] + 1,
                 f"regenerar con el punto ajustado a mano de {lu['origen']} #{lu['num']} en bornes_usuario: exacto ('usuario') en {pu_} "
                 f"({(lu2 or {}).get('marca_o')}, {(lu2 or {}).get('conf_o')}; {li2['exactos']} con el punto del borne)")
    ok = [l for l in salen(ld2) if (cerca(fin(l.get('ruta')), q) if l['num'] == g else cerca(fin(l.get('ruta')), p))]
    chequear(len(ok) == len(salen(ld2)) and all(l.get('salida') == 'g1' for l in salen(ld2) if l['num'] == g),
             f"LD: {len(ok)} de {len(salen(ld2))} terminan en la entrada elegida {p} (y el {g}, del grupo, en {q})")
    borde_li = min(d['b'][0] for d in li2['ductos'])
    ap = [l for l in salen(li2) if l.get('a_puerta')]
    chequear(li2.get('bisagra') and li2.get('puerta_propuesta') and ap and all(l.get('sale') == 'puerta' and fin(l['ruta'])[0] < borde_li for l in ap)
             and all(l.get('sale') == 'entrada' and cerca(fin(l['ruta']), li2['entrada_propuesta']) for l in salen(li2) if not l.get('a_puerta')),
             f"LI (bisagra a la izquierda): {len(ap)} a la puerta salen por el lado de la puerta {li2.get('puerta_propuesta')}, el resto por la entrada")
    chequear(not any('no llega' in a for a in e8b.get('avisos') or []), f"sin avisos de recorridos que no llegan ({e8b.get('avisos')})")
    # la puerta: regenerar conserva sus puntos de paso (los cables pasan por ahi) y la capa «Pasan hacia la puerta» de la LI
    P2 = e8b.get('puerta') or {}
    chequear(Pd and P2 and all(any(abs(x[1] - pp[0][1]) <= 0.15 for x in l['ruta']) for l in lineas_p(P2)),
             f"regenerar conserva los puntos de paso de la puerta {pp}: los {len(lineas_p(P2)) if P2 else 0} cables pasan por ahí")
    chequear((li2.get('transito') or {}).get('n') and not ld2.get('transito'),
             f"la LI (bisagra) muestra los que pasan hacia la puerta ({(li2.get('transito') or {}).get('n')}) y la LD no")
    # la lista WPC no usa la puerta: sin la vista de la puerta (layout.json sin 'puerta') las laterales y las tablas dan igual
    pl = os.path.join(hist, jid, 'layout.json')
    with open(pl, encoding='utf-8') as f:
        lay = json.load(f)
    if chequear('puerta' in lay, "el layout.json releído trae la vista de la puerta ('puerta')"):
        lay.pop('puerta')
        with open(pl, 'w', encoding='utf-8') as f:
            json.dump(lay, f, ensure_ascii=False)
        insS = gen()
        if insS:
            e8s = insS['estacion8']
            # (en_puerta y, desde E8-7, pin_puerta: el cable llega a su pin EN EL DIBUJO de la puerta; la WPC no los usa)
            sin_ep = lambda gs: [dict({k: v for k, v in g_.items() if k not in ('en_puerta', 'cables')},
                                      cables=[{k: v for k, v in x.items() if k != 'pin_puerta'} for x in g_['cables']]) for g_ in gs]
            chequear('puerta' not in e8s and e8s['laterales'] == [{k: v for k, v in L.items()} for L in e8b['laterales']]
                     and sin_ep(e8s['afuera']) == sin_ep(e8b['afuera']),
                     'sin la vista de la puerta las laterales (rutas y largos) y las tablas de «Puerta y placa» dan igual: la WPC no la usa')
    ins3 = gen(topo_nuevo=True)
    if not ins3:
        return
    e8c = ins3['estacion8']
    chequear(e8c.get('recorridos') == {'preguntar': True, 'bisagra': None, 'vistas': {}}, f"un topográfico nuevo borra lo elegido y vuelve a preguntar ({e8c.get('recorridos')})")
    ld3 = lateral(e8c, 'LD')
    chequear(all(cerca(fin(l.get('ruta')), ld3['entrada_propuesta'], 0.15) for l in salen(ld3)),
             f"y la LD vuelve a la entrada propuesta {ld3['entrada_propuesta']}")
    R3 = e8c.get('ruteo_mano') or {}
    chequear(any(g['id'] == 'solenoides' and g['dibujado'] for g in R3.get('grupos') or []) and R3.get('miembro', {}).get(k1303) == 'nuevo:fixture1',
             'el ruteo a mano es del PRODUCTO (código + topográfico): se conserva al volver a cargar el mismo topográfico')
    # (el instructivo de E6 no cambia con lo elegido en E8)
    sin = lambda d: {k: v for k, v in d.items() if k not in ('estacion8', 'generado', 'mapeo', 'salidas', 'producto', 'bornes_usuario')}
    chequear(sin(ins1) == sin(ins2), 'lo elegido en E8 (y el punto de una lateral ajustado a mano) no cambia el instructivo de E6')


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
            # (la bandeja: sin las vistas de E8, la puerta de E8 ni la version del lector)
            a = dict(a, layout={k: v for k, v in a['layout'].items() if k not in ('vistas', 'version_lector', 'puerta')})
            b = dict(b, layout={k: v for k, v in b['layout'].items() if k not in ('vistas', 'version_lector', 'puerta')})
        a = {k: v for k, v in a.items() if k not in sin}; b = {k: v for k, v in b.items() if k not in sin}
        difs = []
        cb.comparar(a, b, '', difs, 0)
        chequear(not difs, f'{t}: E6 igual: {pre}_{t}.json' + (f" sin {', '.join(sin)}" if sin else '') + (' sin vistas, puerta ni version_lector' if pre == 'layout' else '')
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
                       PLANOCABLES_HISTORIAL=os.path.join(tmp, 'historial'), PLANOCABLES_PORT='8796',
                       PLANOCABLES_RECORRIDOS_E8=os.path.join(tmp, 'recorridos_armar.json'))
            shutil.copyfile(FIXTURE_REC, env['PLANOCABLES_RECORRIDOS_E8'])
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
            esperado_e83(t, e8, ins if isinstance(ins, dict) and (ins.get('estacion8') or {}).get('laterales') is not None else None)
            esperado_e84(t, e8)
            if isinstance(ins, dict) and (ins.get('estacion8') or {}).get('laterales') is not None:
                ruteo_e84(t, ins)
            esperado_e85(t, e8)
            if isinstance(ins, dict) and (ins.get('estacion8') or {}).get('laterales') is not None:
                ruteo_e85(t, ins)
            esperado_e86(t, e8)
            lay = cargar(sal, 'layout', t) or (cargar(BASES, 'layout', t) if bases else None)
            esperado_e87(t, e8, (lay or {}).get('layout'))
            if isinstance(ins, dict) and (ins.get('estacion8') or {}).get('laterales') is not None:
                ruteo_e87(t, ins)
            esperado_e88(t, e8)
            if isinstance(ins, dict) and (ins.get('estacion8') or {}).get('laterales') is not None:
                entrada_e88(t, ins)
                comunicacion_e88(t, ins)
                haz_e88(t, ins)
            if not bases:
                e6_igual(t, sal)
        if not bases:
            regenerar_e82(tmp)
        web_e86(tmp, sal)
        pines_e87_reglas()
        red_e88()
        salidas_e88(sal)
        mano_fuera_e88(sal)
        formato_haz_e88()
        web_haz_e88(tmp, sal)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('\nTODO OK' if not fallas else f'\nFALLA: {len(fallas)} prueba(s)')
    return 1 if fallas else 0


if __name__ == '__main__':
    sys.exit(main())
