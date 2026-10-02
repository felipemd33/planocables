export const meta = {
  name: 'corregir-funcional-tpt',
  description: 'Diagnostica y corrige los errores de lectura del funcional en el plano TPT (72715): tramos falsos, modulo de rele mal tomado, bornes sin numero, uniones inexistentes; sin romper 75287 ni 66817',
  phases: [
    { title: 'Diagnosticar', detail: '3 agentes: reles/modulos, uniones/3 puntas, barrido completo contra el funcional' },
    { title: 'Corregir', detail: '1 agente: arreglos generales en el lector + regresiones' },
    { title: 'Verificar', detail: '2 verificadores: TPT contra el funcional y regresion/codigo' },
  ],
}
const SP = 'C:/Users/Taller/AppData/Local/Temp/claude/C--Buscar-Termos-en-plano/3f7759ac-e556-408b-8ca2-20e3d33cd1fc/scratchpad'
const PROG = 'C:/Buscar Termos en plano/programa'
const JT = SP + '/regr/jtpt'
const J66 = SP + '/regr/j66817'
const J75 = 'C:/Buscar Termos en plano/3 - Historial web/ac0f0949510a'
const FUNC = JT + '/72715 DIAGRAMA ELECTRICOmSafe expansor - REV.8.pdf'
const CTX = `
CONTEXTO: taller Batfer (Uruguay). Programa propio en ${PROG} (Python): core.process(pdf) lee el plano FUNCIONAL vectorial de AutoCAD (textos SHX por diccionario de trazos; wires.py reconstruye cables, numeros, uniones en T, flechas a otras hojas); instructivo.py arma el instructivo de cableado: describe_end() describe cada punta (tag, borne, punto QUATTRO, lado ARRIBA/ABAJO, modulo de rele...), conductors(res) arma los conductores (nodos y 'pares' origen-destino de cada numero de cable), fmt_terminal(e) el texto ('61KR1 11', 'XM1 3 ABAJO', '13XC1 2.2'), build(res, lay) las lineas, pendientes (LI <-> LI) y sueltos. Reglas del taller: el FUNCIONAL es la guia principal; un tag nombra los bornes a su DERECHA (o debajo, en columna) hasta el proximo tag; reles en modulos (61KR1, 61KR2, 61KR3: contactos 11/14/12 y bobina A1/A2; el numero de modulo sale del tag que esta junto a cada modulo en el funcional); QUATTRO N.p (segunda bornera del mismo numero N.5-N.8); doble piso 'N ARRIBA/ABAJO'; un mismo numero con 3+ puntas es un puente/derivacion a proposito (union en T junto a un borne); el resto de los conductores son 2 puntas.
EL USUARIO cargo un plano nuevo: mSafe TPT (expansor), funcional 72715 REV.8 + constructivo 72887 REV.7. COPIA de su trabajo para probar: ${JT} (funcional '${FUNC}', topografico.pdf, layout.json, instructivo.json, resultado.json). NO toques la carpeta original del usuario ('3 - Historial web/e548b195eb2a') ni ${J75}. Reporto: "realizo el mapeo bastante decente aunque hay algunos errores: 3 puntas que no existen, referencia mal tomada del funcional, uniones entre cables que no existen". Casos vistos en su instructivo:
- 1305: '61KR1 11 -> 61KR1 11' (tramo de un borne a si mismo) + '61KR1 11 -> 13XC1 2.2' -> falso cable de 3 puntas.
- 2152: '61KR1 A1 -> LI' y '61KR2 A1 -> LI'; 2154: '61KR2 A1 -> LI' y '61KR3 A1 -> LI' (y 2150 en 61KR1 A1): cada numero aparece en dos modulos -> modulo mal tomado.
- 6104: '61KR1 14 -> XM1 3 ARRIBA', '61KR2 14 -> XM1 3 ARRIBA', 'XM1 3 ARRIBA -> 61XDIO 2 ARRIBA' (y 6101 tambien sale de 61KR1 14).
- 6201 'XM1 ARRIBA -> XM1 3 ABAJO', 6202 'XM1 ABAJO -> XM1 4 ABAJO' (borne sin numero, union inexistente).
- 1310: 'XM1 2 ARRIBA -> XM1 4 ARRIBA' y 'XM1 2 ARRIBA -> 13XC1 3.8'.
- 2115: '43KR1 2 -> LI' y '43KR1 12 -> LI'.
- Pendientes de 1313 y 1314: TODAS las combinaciones de pares entre 4 puntas ('13PS3 +Vo -> 43DIB1 14/9/1 ABAJO', '43DIB1 14 -> 43DIB1 9', ...) en vez de la cadena real; destinos '? 4' y '? 6' (1604, 1606); sueltos 1101/1102/1103 con una sola punta (11XP 1/2/3 ARRIBA).
HERRAMIENTAS: volcado del instructivo con el codigo actual (no escribe en el trabajo con --sin-cache): python ${SP}/regr/volcar_trabajo.py <trabajo> <salida.json> --sin-cache. Bases de comparacion de HOY: ${SP}/regr/ahora_75287.json (75287, verificado por el taller: tiene que quedar IGUAL), ${SP}/regr/base_66817.json (66817: trabajo copia ${J66}; verificado contra una referencia con fotos: tiene que quedar igual salvo arreglos justificados), ${SP}/regr/base_tpt.json (TPT, el que tiene errores). Para mirar el funcional: renderiza las paginas con pypdfium2 y abri recortes ampliados con Read; los resultados intermedios de core.process (res.pages[i]['lines'] textos con bbox, res.detail apariciones de numeros con color/seccion/bbox, rutas) sirven para ubicar cada cable. Python con numpy, cv2, PIL, pypdfium2, pypdf, shapely (no instales paquetes).`

const DSCH = { type: 'object', properties: {
  casos: { type: 'array', items: { type: 'object', properties: {
    cable: { type: 'string' }, hoja: { type: 'string' }, programa: { type: 'string', description: 'lo que sale hoy' }, real: { type: 'string', description: 'lo que dice el funcional (puntas reales, ej 61KR2 A1 -> LI)' },
    causa: { type: 'string', description: 'causa en el codigo: archivo:funcion y por que' }, arreglo: { type: 'string', description: 'arreglo GENERAL propuesto' } },
    required: ['cable', 'hoja', 'programa', 'real', 'causa', 'arreglo'] } },
  resumen: { type: 'string' } }, required: ['casos', 'resumen'] }

phase('Diagnosticar')
const diags = await parallel([
  () => agent(`DIAGNOSTICO: RELES, MODULOS Y CONTACTOS. ${CTX}
Tu parte: 1305, 2150/2152/2154 (y 2151/2153/2155, 2160...), 6101/6104, 2115, y cualquier otro borne de rele (KR) del TPT. Para cada uno: mira la hoja del funcional, decide las puntas REALES (modulo correcto, contacto correcto) y encontra la CAUSA en el codigo (como se asigna el modulo al borne en describe_end / instructivo; como aparece un tramo de un borne a si mismo; por que un numero queda en dos modulos; '2' vs '12'). Proponer arreglos generales que no rompan el 75287 (46KR/43KR/62KR modulos) ni el 66817 (61KR1..3, 43KR1, 62KR1). No modifiques el programa: solo diagnostica (scripts en ${SP}/tpt_diag_reles/).`, { label: 'diag:reles', phase: 'Diagnosticar', schema: DSCH }),
  () => agent(`DIAGNOSTICO: UNIONES, BORNES SIN NUMERO Y CABLES DE VARIAS PUNTAS. ${CTX}
Tu parte: 6201/6202 (XM1 sin numero), 1310 (XM1 2/4 + 13XC1 3.8), 6104 en XM1 3 / 61XDIO 2, los pendientes 1313/1314 (todas las combinaciones de pares), '? 4' / '? 6' (1604, 1606) y los sueltos 1101/1102/1103. Para cada uno: decide la verdad en el funcional (uniones en T reales, cadena real de una derivacion, tag que nombra el borne) y la CAUSA en el codigo (wires.py uniones, conductors() armado de 'pares' de un numero de 3+ puntas, describe_end sin borne, tag no encontrado). Proponer arreglos generales: en particular, un cable de N puntas tiene que dar N-1 tramos siguiendo el dibujo (las uniones), NO todos los pares. No modifiques el programa (scripts en ${SP}/tpt_diag_uniones/).`, { label: 'diag:uniones', phase: 'Diagnosticar', schema: DSCH }),
  () => agent(`DIAGNOSTICO: BARRIDO COMPLETO. ${CTX}
Revisa TODAS las 48 lineas, los 82 pendientes y los 3 sueltos de ${SP}/regr/base_tpt.json contra el funcional, hoja por hoja (mira cada cable en su hoja: de donde sale, a donde llega, borne y lado). Lista CADA error (no solo los ya reportados): tramos que no existen, puntas faltantes, borne o modulo equivocado, ARRIBA/ABAJO mal, QUATTRO mal numerado, color/seccion mal, LI que en realidad esta en la bandeja o al reves, pendientes falsos. Para cada error: la verdad y una hipotesis de causa. Tambien lista los cables del funcional que NO aparecen en el instructivo. No modifiques el programa (scripts en ${SP}/tpt_diag_barrido/). Escribi ademas ${SP}/tpt_diag_barrido/verdad_tpt.json = {"cables": {num: {"puntas": [texto taller], "tramos": [[a, b]], "hoja": .., "nota": ..}}} con la verdad de TODOS los cables con numero del TPT (sirve de referencia para verificar el arreglo).`, { label: 'diag:barrido', phase: 'Diagnosticar', schema: DSCH }),
])

phase('Corregir')
const FSCH = { type: 'object', properties: {
  arreglos: { type: 'array', items: { type: 'object', properties: { que: { type: 'string' }, donde: { type: 'string' }, prueba: { type: 'string' } }, required: ['que', 'donde', 'prueba'] } },
  tpt: { type: 'string', description: 'como queda el TPT: cada caso reportado, y conteo contra verdad_tpt.json' },
  regresion_75287: { type: 'string' }, regresion_66817: { type: 'string' }, pendientes: { type: 'array', items: { type: 'string' } } },
  required: ['arreglos', 'tpt', 'regresion_75287', 'regresion_66817', 'pendientes'] }
const fix = await agent(`Eres el ingeniero que CORRIGE el lector del funcional. ${CTX}
DIAGNOSTICOS (independientes, pueden discrepar: decide con el funcional): ${JSON.stringify(diags.filter(Boolean)).slice(0, 14000)}
Verdad completa del TPT armada por el barrido: ${SP}/tpt_diag_barrido/verdad_tpt.json (si existe).
Backup del codigo de antes: ${SP}/backup_antes_tpt/ (ya hecho). Implementa arreglos GENERALES (sin tags ni coordenadas de este plano en el codigo) en ${PROG} (core.py, wires.py, instructivo.py segun corresponda) para que el TPT salga bien: sin tramos de un borne a si mismo, modulo de rele correcto, bornes con su numero, cables de N puntas con N-1 tramos reales (en lineas y en pendientes), sin uniones inexistentes. Despues: (1) TPT: volcar_trabajo sobre ${JT} --sin-cache y compara contra verdad_tpt.json: cuenta cuantos cables quedan bien y lista los que no, con motivo; (2) 75287: volcar_trabajo sobre ${J75} --sin-cache: lineas, pendientes, sueltos, otra estacion y extremos IGUALES a ${SP}/regr/ahora_75287.json (si cambia algo, deshacer o justificar con el funcional del 75287); (3) 66817: volcar_trabajo sobre ${J66} --sin-cache --relayout contra ${SP}/regr/base_66817.json: iguales salvo cambios justificados con el funcional. Itera hasta que las tres cosas esten bien. No toques web/*.js ni el paquete bornes salvo que haga falta para esto.`, { label: 'corregir', phase: 'Corregir', schema: FSCH })

phase('Verificar')
const VSCH = { type: 'object', properties: { ok: { type: 'boolean' }, problemas: { type: 'array', items: { type: 'object', properties: { que: { type: 'string' }, evidencia: { type: 'string' }, gravedad: { type: 'string', enum: ['alta', 'media', 'baja'] }, arreglo: { type: 'string' } }, required: ['que', 'evidencia', 'gravedad', 'arreglo'] } }, resumen: { type: 'string' } }, required: ['ok', 'problemas', 'resumen'] }
const fixTxt = JSON.stringify(fix || {}).slice(0, 6000)
const vs = await parallel([
  () => agent(`VERIFICADOR del TPT contra el FUNCIONAL (independiente). ${CTX}
Reporte del que corrigio: ${fixTxt}
Con el codigo actual vuelca el instructivo de ${JT} (volcar_trabajo --sin-cache) y revisa CADA linea, pendiente y suelto contra el funcional (hoja por hoja, recortes ampliados). Usa ${SP}/tpt_diag_barrido/verdad_tpt.json como ayuda pero comprobalo vos. Reporta todo lo que siga mal (con la hoja y lo que deberia ser). Comproba especialmente los casos reportados por el usuario: 1305, 2150/2152/2154, 6101/6104, 6201/6202, 1310, 2115, 1313/1314, 1604/1606, 1101-1103. No modifiques el programa.`, { label: 'verificar:tpt', phase: 'Verificar', schema: VSCH }),
  () => agent(`VERIFICADOR de REGRESION y CODIGO (independiente). ${CTX}
Reporte del que corrigio: ${fixTxt}
(1) Regresion: 75287 (${J75}, volcar_trabajo --sin-cache, no escribe) IGUAL a ${SP}/regr/ahora_75287.json en lineas/pendientes/sueltos/otra estacion/extremos; 66817 (${J66}, --sin-cache --relayout) contra ${SP}/regr/base_66817.json: lista cada diferencia y juzga con el funcional del 66817 si esta bien; ademas el mapeo de bornes del 66817 tiene que seguir 104/104: python "C:/Buscar Termos en plano/prototipos/_referencia_66817/evaluar2.py" sobre los puntos del volcado (arma el json en formato evaluar.py) --ref "C:/Buscar Termos en plano/prototipos/_referencia_66817/bornes_referencia.json". (2) Revisa el diff de ${SP}/backup_antes_tpt/ contra ${PROG} (core.py, wires.py, instructivo.py...): bugs, casos borde, reglas especificas de un plano metidas en el codigo, rendimiento. No modifiques el programa.`, { label: 'verificar:regresion', phase: 'Verificar', schema: VSCH }),
])
return { diags, fix, vs }
