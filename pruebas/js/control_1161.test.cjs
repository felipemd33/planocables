'use strict';
/* Control del cable 1161 del PAE (11PS1 TB2 1 (-V) → LI, muere en 12XPS 4 de la bandeja lateral). Regla del taller del
   2026-10-09: acometida 75 + canaleta de la bandeja + curva_LI 100 + canaleta de la lateral + acometida_LI 75 (canaleta →
   borne o aparato; hasta el 2026-10-06 eran 150).
   - PAE regenerado (pruebas/bases/ins_76884.json, sin salidas elegidas: sale por la regla del taller, por arriba):
     75 + 297 + 100 + 269 + 75 = 816 → 850 (antes 891 → 900);
   - PAE del usuario (fixtures/pae_usuario, «Todos los LI» elegido a mano por [573.3, 448], más abajo): la canaleta de la
     bandeja da 490 → 75 + 490 + 100 + 269 + 75 = 1009 → 1050 (antes 1084 → 1100). */
const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('./comun.cjs');

// los números del texto «como» de la fila: acometida, canaleta de la bandeja, curva, canaleta de la lateral, acometida LI
function partes(f) {
  const m = /^(\d+) \(borne → canaleta\) \+ canaleta de la bandeja (\d+) \+ curva a LI (\d+) \+ canaleta de la bandeja lateral izquierda (\d+) \+ (\d+) \(canaleta → 12XPS 4 ABAJO\), redondeado a (\d+)$/.exec(f.como);
  assert.ok(m, `FALLA: el 1161 no sale por la regla de la bandeja lateral: ${f.como}`);
  return m.slice(1).map(Number);
}
const fila1161 = async ins => {
  const r = await C.correrWpc(ins);
  const fs = r.filas.filter(f => f.num === '1161');
  assert.equal(fs.length, 1, 'FALLA: tiene que haber un solo 1161');
  return fs[0];
};

test('1161 del PAE regenerado (salida del taller) = 75 + 297 + 100 + 269 + 75 = 816 → 850', async () => {
  const ins = C.leer(C.TRABAJOS['76884']);
  assert.deepEqual(ins.salidas.grupos || [], [], 'FALLA: el PAE regenerado no tiene que tener salidas elegidas');
  const f = await fila1161(ins);
  const [ac, can, curva, lat, acLI, red] = partes(f);
  assert.deepEqual([ac, can, curva, lat, acLI, red], [75, 297, 100, 269, 75, 50]);
  assert.equal(ac + can + curva + lat + acLI, 816);
  assert.equal(f.largo, 850);
  assert.equal(f.largo, Math.ceil(816 / red) * red);
});

test('1161 del PAE del usuario (salida a LI elegida a mano) = 75 + 490 + 100 + 269 + 75 = 1009 → 1050', async () => {
  const ins = C.leer(C.TRABAJOS.pae_usuario);
  const li = (ins.salidas.grupos || []).find(g => g.aplica === 'LI');
  assert.ok(li && JSON.stringify(li.puntos) === '[[573.3,448]]', 'FALLA: el fixture tiene que tener «Todos los LI» por [573.3, 448]');
  const l = ins.pasos.flatMap(p => p.lineas).find(x => x.num === '1161');
  assert.equal(l.salida, 'li');
  const f = await fila1161(ins);
  const [ac, can, curva, lat, acLI] = partes(f);
  assert.deepEqual([ac, can, curva, lat, acLI], [75, 490, 100, 269, 75]);
  assert.equal(f.largo, 1050);
});
