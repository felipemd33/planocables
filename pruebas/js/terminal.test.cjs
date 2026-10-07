'use strict';
/* Golden del terminal (pino / doble y color de la pollera de cada punta): terminal() de programa/web/instructivo.js
   (bandeja, E6) y el de programa/web/estacion8.js (bandeja lateral, E8), sin tocarlos, contra pruebas/bases/wpc/. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const C = require('./comun.cjs');

const id = x => `${x.num} ${x.origen} → ${x.destino}`;
for (const [nombre, ins] of C.entradasTerminal()) {
  test(`terminal ${nombre}: E6 (instructivo.js) y E8 (estacion8.js) iguales al golden`, async () => {
    const p = C.archivoTerminal(nombre);
    assert.ok(fs.existsSync(p), `FALLA: falta el golden ${p} (node pruebas/js/generar_goldens.cjs)`);
    const g = C.leer(p);
    const e6 = await C.terminales(ins);
    assert.equal(C.difLista(e6, g.e6, id), null, `FALLA: cambió el terminal de E6: ${C.difLista(e6, g.e6, id)}`);
    const e8 = await C.terminalesE8(ins);
    assert.equal(C.difLista(e8, g.e8, id), null, `FALLA: cambió el terminal de E8: ${C.difLista(e8, g.e8, id)}`);
  });
}

test('terminal: reglas del taller en el instructivo chico (pino, doble mezclado, LI sin terminal)', async () => {
  const e6 = await C.terminales(C.cargarCaso('sin_producto'));
  const de = (num, o) => e6.find(x => x.num === num && x.origen === o);
  assert.equal(de('1001', '11A1 1').o.txt, 'Pino 2,5 mm² · pollera azul');
  assert.equal(de('1006', '11A1 4').o.pollera, 'rojo');
  // 1018: dos tramos con un borne en común (11A2 7) → terminal doble, por la sección mayor, con las dos secciones
  assert.equal(de('1018', '11A1 7').d.txt, 'Terminal doble 2,5 mm² · pollera gris (1 + 2,5 mm²)');
  assert.equal(de('1018', '11A2 7').o.tipo, 'doble');
  assert.equal(de('1007', '11A1 5').d, null, 'FALLA: la punta que sale a LI no lleva terminal en E6');
  assert.equal(de('1012', '12B1 5').o.pollera, null, 'FALLA: 0,32 mm² no tiene pollera en terminales.json');
});
