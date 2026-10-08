'use strict';
/* Estación 8, etapa E8-3 (2026-10-08): el empalme con el cable propio de un aparato en la pantalla (programa/web/
   estacion8.js sin tocar, con los instructivos congelados de pruebas/bases/ins_*.json).
   - TPT: la tarjeta de 1108 dice «WAGO con el cable propio de 12PS2 · + panel», la punta va «pelado (sin pino)» (sin
     terminal dibujado), no dice «punto aprox.» y la miniatura tiene el WAGO y el cable propio punteado; el RS-485
     (8105 / 8106) es «Empalme de 3, a confirmar» con el terminal a confirmar; «Puerta y placa» ya no tiene EMPALME.
   - 66817: los 4 cables del cargador 12PS1 con WAGO y su pin.
   - 75287 y PAE: ningún WAGO (el cargador va a la bornera 12XPS). */
const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('./comun.cjs');

// la tarjeta de un cable (por su clave) en el HTML de una lateral
function tarjeta(html, clave) {
  const partes = html.split('<div class="cab ').slice(1);
  const t = partes.find(p => /^[^"]*" data-g="\d+" data-i="\d+" data-clave="/.test(p) && p.split('>')[0].includes(`data-clave="${clave}"`));
  return t ? '<div class="cab ' + t : null;
}

for (const t of ['tpt', 'tpt_constructivo']) {
  test(`E8-3 ${t}: WAGO del cargador y RS-485 «empalme de 3, a confirmar» en la pantalla`, async () => {
    const ins = C.leer(C.TRABAJOS[t]);
    const v = await C.vistaE8(ins);
    const iLI = ins.estacion8.laterales.findIndex(L => L.lado === 'LI');
    const html = v.laterales[iLI];
    const pins = { '1108|11PS1 +|12PS2 +': '+ panel', '1109|11PS1 -|12PS2 -': '- panel', '1201|12F1|12PS2 +': '+ batería', '1202|12PS2 -|12XP 2.1': '- batería' };
    for (const [clave, pin] of Object.entries(pins)) {
      const c = tarjeta(html, clave);
      assert.ok(c, `FALLA: no está la tarjeta de ${clave}`);
      assert.ok(c.includes(`WAGO con el cable propio de 12PS2 · ${pin}`), `FALLA: ${clave} sin «WAGO con el cable propio de 12PS2 · ${pin}»`);
      assert.ok(c.includes('⟦pelado⟧'), `FALLA: ${clave}: la punta no va pelada (sin pino)`);
      assert.ok(!c.includes('punto aprox.'), `FALLA: ${clave}: el empalme no es un punto aproximado`);
      assert.ok(c.includes('e8-wago-i') && c.includes('e8-propio'), `FALLA: ${clave}: la miniatura no tiene el WAGO y el cable propio`);
      // (en la miniatura solo puede haber terminal dibujado en los otros tramos del mismo cable, no en el WAGO)
      assert.ok(!c.includes('<g class="term"/>') || ins.estacion8.laterales[iLI].pasos.flatMap(p => p.lineas).filter(l => l.num === clave.split('|')[0]).length > 1,
        `FALLA: ${clave}: se dibuja un terminal en la punta del WAGO`);
    }
    const rs = ['8105|21PCB01 32|EMPALME con 12PS2', '8105|33MX01 D1+|EMPALME con 12PS2', '8106|21PCB01 33|EMPALME con 12PS2', '8106|33MX01 D1-|EMPALME con 12PS2'];
    for (const clave of rs) {
      const c = tarjeta(html, clave);
      assert.ok(c && c.includes('Empalme de 3, a confirmar') && c.includes('⟦confirmar⟧') && c.includes('empalme a confirmar'),
        `FALLA: ${clave}: no dice «Empalme de 3, a confirmar» con el terminal a confirmar`);
    }
    assert.ok(!/<h3 class="mono">EMPALME<\/h3>/.test(v.afuera), 'FALLA: el EMPALME sigue en «Puerta y placa»');
  });
}

test('E8-3 66817: los 4 cables del cargador 12PS1 con WAGO y su pin', async () => {
  const ins = C.leer(C.TRABAJOS['66817']);
  const v = await C.vistaE8(ins);
  const iLI = ins.estacion8.laterales.findIndex(L => L.lado === 'LI');
  const pins = { '1101|11XP 1|12PS1 +': '+ panel', '1102|11XP 2|12PS1 -': '- panel', '1201|12F1|12PS1 +': '+ batería', '1202|12PS1 -|12XP 4.1': '- batería' };
  for (const [clave, pin] of Object.entries(pins)) {
    const c = tarjeta(v.laterales[iLI], clave);
    assert.ok(c && c.includes(`WAGO con el cable propio de 12PS1 · ${pin}`) && c.includes('⟦pelado⟧'), `FALLA: ${clave} sin WAGO ${pin}`);
  }
  // en la otra lateral, el mismo cable (1101 al 11XP) no tiene empalme en su punta
  const iLD = ins.estacion8.laterales.findIndex(L => L.lado === 'LD');
  const c = tarjeta(v.laterales[iLD], '1101|11XP 1|12PS1 +');
  assert.ok(c && !c.includes('e8-emp-t') && !c.includes('⟦pelado⟧'), 'FALLA: 1101 en la lateral derecha no lleva empalme en el 11XP');
});

for (const t of ['75287', '76884']) {
  test(`E8-3 ${t}: ningún WAGO (el cargador va a la bornera 12XPS)`, async () => {
    const v = await C.vistaE8(C.leer(C.TRABAJOS[t]));
    for (const h of [...v.laterales, v.afuera]) {
      assert.ok(!h.includes('e8-wago') && !h.includes('e8-emp') && !h.includes('⟦pelado⟧'), `FALLA: ${t} tiene un empalme con un cable propio`);
    }
  });
}
