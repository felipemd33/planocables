'use strict';
/* Regla de largos de la lista WPC del 2026-10-09 (decisión del taller), sobre el TPT con el constructivo
   (pruebas/bases/ins_tpt_constructivo.json, las dos laterales dibujadas). Con redondeo 1 (sin redondear) para ver las cuentas:
   - muere en una lateral: 75 + canaleta de la bandeja + la curva de ESA lateral (curva_LI / curva_LD) + canaleta de la
     lateral + 75 (canaleta → borne o aparato);
   - a la puerta / placa: 75 + canaleta de la bandeja + curva + canaleta de la lateral de la bisagra hasta la salida a la
     puerta (el tránsito de la E8, que hay solo con la bisagra elegida; sin él, 0) + puerta;
   - un aparato sin dibujar en el plano que no es de la puerta (zona hidráulica, batería...): como antes, 75 + canaleta de
     la bandeja + puerta. */
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const C = require('./comun.cjs');
const W = require(path.join(C.RAIZ, 'programa', 'web', 'nucleo', 'wpc_core.js'));
const CONFIG = C.leer(C.CONFIG_WPC);

const sinLado = t => String(t || '').replace(/ (ARRIBA|ABAJO)$/, '');
const filas = (ins, trabajo) => W.filas(ins, W.config(CONFIG, { producto: ins.producto, trabajo: Object.assign({ redondeo: 1 }, trabajo) }));
// la fila de la bandeja (E6) del cable de hacia_puerta x (misma punta en la bandeja)
const filaDe = (fs, x) => {
  const f = fs.find(f => f.tipo === 'bandeja' && f.l.num === x.num && sinLado(f.l.origen) === sinLado(x.origen));
  assert.ok(f, `FALLA: falta la fila de ${x.num} (${x.origen})`);
  return f;
};
const n = (como, re) => Number((re.exec(como) || [])[1]);

test('muere en una lateral: la curva de ESA lateral (curva_LD aparte) y 75 de la canaleta al borne', () => {
  const fs = filas(C.leer(C.TRABAJOS.tpt_constructivo), { curva_LD: 150 });
  const li = fs.filter(f => /curva a LI \d+ \+ canaleta de la bandeja lateral izquierda/.test(f.calc.como));
  const ld = fs.filter(f => /curva a LD \d+ \+ canaleta de la bandeja lateral derecha/.test(f.calc.como));
  assert.ok(li.length > 0 && ld.length > 0, 'FALLA: el TPT con el constructivo tiene cables que mueren en las dos laterales');
  for (const [f, curva, lat] of [...li.map(f => [f, 100, /lateral izquierda (\d+)/]), ...ld.map(f => [f, 150, /lateral derecha (\d+)/])]) {
    assert.match(f.calc.como, new RegExp(`^75 \\(borne → canaleta\\) \\+ canaleta de la bandeja \\d+ \\+ curva a L[ID] ${curva} \\+ .* \\+ 75 \\(canaleta → `), `FALLA: ${f.l.num}: ${f.calc.como}`);
    assert.equal(f.largo, 75 + n(f.calc.como, /canaleta de la bandeja (\d+)/) + curva + n(f.calc.como, lat) + 75, `FALLA: ${f.l.num}: ${f.calc.como}`);
  }
});

test('a la puerta / placa: sin bisagra elegida, 75 + canaleta de la bandeja + curva + puerta; con el tránsito, suma la canaleta de la lateral hasta la salida a la puerta', () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo), e8 = ins.estacion8;
  const x = (e8.hacia_puerta || []).find(h => h.desde === 'E6' && !h.sin_aparato);
  assert.ok(x, 'FALLA: el TPT con el constructivo tiene cables de la bandeja que siguen a la puerta');
  const antes = filaDe(filas(ins), x);
  assert.match(antes.calc.como, / \+ curva a LI 100 \(sin el recorrido por la lateral: falta elegir la bisagra en la E8\) \+ puerta \/ placa 1850 /);
  assert.equal(antes.largo, 75 + n(antes.calc.como, /canaleta de la bandeja (\d+)/) + 100 + 1850);
  // un tránsito de prueba por la lateral izquierda (la de la bisagra): a lo largo de su canaleta más ancha
  const L = e8.laterales.find(L => L.lado === 'LI');
  const d = L.ductos.filter(d => d.b).sort((a, b) => (b.b[2] - b.b[0]) - (a.b[2] - a.b[0]))[0], y = (d.b[1] + d.b[3]) / 2;
  L.transito = { ruta: [[d.b[0] + 1, y], [d.b[2] - 1, y]], cables: [x] };
  const can = W.canaleta(L.transito.ruta, L.ductos, L.escala);
  assert.ok(can > 0);
  const desp = filaDe(filas(ins), x);
  assert.match(desp.calc.como, new RegExp(` \\+ curva a LI 100 \\+ canaleta de la bandeja lateral izquierda hasta la puerta ${can} \\+ puerta / placa 1850 `));
  assert.equal(desp.largo - antes.largo, can);
});

test('no va a la puerta ni a la placa (sin dibujar o dibujado en el fondo): como antes, 75 + canaleta de la bandeja + puerta', () => {
  // TPT: un aparato sin dibujar (BH-01-ZV, ZY, PT 001: 'sin_aparato' en hacia_puerta); 75287: la batería 12PB1 y las
  // solenoides SP-n, dibujadas en el fondo (no están en hacia_puerta)
  const tpt = C.leer(C.TRABAJOS.tpt_constructivo);
  const x = (tpt.estacion8.hacia_puerta || []).find(h => h.desde === 'E6' && h.sin_aparato);
  assert.ok(x, 'FALLA: el TPT con el constructivo tiene cables a aparatos sin dibujar (BH-01-ZV, ZY, PT 001)');
  const fs75 = filas(C.leer(C.TRABAJOS['75287']));
  const casos = [filaDe(filas(tpt), x), ...['1217', '6204'].map(num => fs75.find(f => f.tipo === 'bandeja' && f.l.num === num))];
  for (const f of casos) {
    assert.ok(f);
    assert.match(f.calc.como, / \+ puerta \/ placa 1850 \(.*: no va a la puerta ni a la placa, como antes\)/, `FALLA: ${f.l.num}: ${f.calc.como}`);
    assert.doesNotMatch(f.calc.como, /curva/);
    assert.equal(f.largo, 75 + n(f.calc.como, /canaleta de la bandeja (\d+)/) + 1850);
  }
  // la placa del 75287 (21PCB01, sin etiqueta en el topográfico) sí va a la puerta
  const placa = fs75.find(f => f.tipo === 'bandeja' && /\(21PCB01 /.test(f.calc.como));
  assert.ok(placa && /curva a LI 100/.test(placa.calc.como), `FALLA: la placa del 75287 va a la puerta: ${placa && placa.calc.como}`);
});
