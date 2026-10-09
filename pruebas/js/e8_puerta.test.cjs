'use strict';
/* Estación 8, etapa E8-4 (2026-10-08, foto 3 del taller): la vista de la PUERTA en la pantalla (programa/web/estacion8.js
   sin tocar, con los instructivos congelados de pruebas/bases/ins_*.json).
   - TPT (los dos), 66817 y 75287: «Puerta y placa» dibuja la vista de la puerta (imagen /e8/puerta.png) con el recorrido
     de cada cable hasta la FRANJA de bornes de su aparato (sin terminal dibujado: el borne está en la tabla), la flecha
     de la entrada, y las tablas de sus aparatos con ▶ (cablear de a uno desde ese cable); los otros aparatos siguen en
     tablas aparte.
   - PAE: sin vista de la puerta (como antes: solo tablas).
   - La capa «Pasan hacia la puerta (N)» de la lateral de la bisagra (L.transito) se dibuja como un haz con su lista. */
const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('./comun.cjs');

for (const t of ['tpt', 'tpt_constructivo', '66817', '75287']) {
  test(`E8-4 ${t}: «Puerta y placa» con la vista de la puerta y los recorridos hasta la franja de bornes`, async () => {
    const ins = C.leer(C.TRABAJOS[t]);
    const P = ins.estacion8.puerta;
    assert.ok(P && P.pasos.length, `FALLA: ${t} sin vista de la puerta en ins_${t}.json`);
    const v = await C.vistaE8(ins);
    const h = v.afuera;
    assert.ok(h.includes('id="e8MapaP"') && h.includes('/e8/puerta.png'), 'FALLA: no se dibuja la vista de la puerta');
    const n = P.pasos.reduce((a, p) => a + p.lineas.length, 0);
    assert.equal((h.match(/class="rt sib/g) || []).length, n, `FALLA: no están los ${n} recorridos de la puerta`);
    assert.ok((h.match(/class="e8-franja"/g) || []).length >= n, 'FALLA: los cables no llegan a la franja de bornes');
    assert.ok(!h.slice(h.indexOf('id="e8MapaP"'), h.indexOf('id="e8SelP"')).includes('<g class="term"/>'), 'FALLA: se dibuja un terminal en la franja (no hay borne dibujado)');
    assert.ok(h.includes('e8-flecha') && h.includes('Entrada'), 'FALLA: falta la flecha de la entrada a la puerta');
    assert.equal((h.match(/data-a="ver"/g) || []).length, n, 'FALLA: cada cable de la puerta tiene ▶ en su tabla');
    for (const a of P.aparatos) assert.ok(h.includes(`<h3 class="mono">${a.tag}</h3>`), `FALLA: falta la tabla de ${a.tag}`);
    const otros = ins.estacion8.afuera.filter(g => !g.en_puerta);
    if (otros.some(g => g.zona === 'puerta / placa')) assert.ok(h.includes('Otros aparatos fuera de las bandejas'), 'FALLA: los otros aparatos no están aparte');
  });
}

test('E8-4 76884 (PAE): sin vista de la puerta, solo las tablas', async () => {
  const ins = C.leer(C.TRABAJOS['76884']);
  assert.ok(!ins.estacion8.puerta, 'FALLA: el PAE no tiene que tener vista de la puerta (EPLAN: después)');
  const v = await C.vistaE8(ins);
  assert.ok(!v.afuera.includes('e8MapaP') && v.afuera.includes('<h2 class="e8-zona">Puerta y placa</h2>'), 'FALLA: el PAE cambió «Puerta y placa»');
});

test('E8-4 tpt_constructivo: capa «Pasan hacia la puerta (N)» en la lateral de la bisagra', async () => {
  const ins = C.copia(C.leer(C.TRABAJOS.tpt_constructivo));
  const iLI = ins.estacion8.laterales.findIndex(L => L.lado === 'LI');
  const L = ins.estacion8.laterales[iLI];
  const todos = (ins.estacion8.hacia_puerta || []).filter(x => x.desde !== 'LI');
  // (pulido 2026-10-09) cuentan solo los que van de verdad a la puerta; los de un aparato sin dibujar que no es de la
  // puerta (BH-01-M, ZY en el TPT) van aparte, «Sin aparato en el plano»
  const cs = todos.filter(x => !x.sin_aparato), sin = todos.filter(x => x.sin_aparato);
  assert.ok(cs.length && sin.length, 'FALLA: ins_tpt_constructivo sin cables hacia la puerta (hacia_puerta) o sin los «sin aparato»');
  assert.ok(sin.every(x => !['21PCB01', '13SH1'].includes(x.aparato)) && cs.every(x => ['21PCB01', '13SH1'].includes(x.aparato)),
    `FALLA: hacia la puerta ${[...new Set(cs.map(x => x.aparato))]} / sin aparato ${[...new Set(sin.map(x => x.aparato))]}`);
  L.transito = { n: cs.length, cables: cs, ruta: [L.entrada_propuesta, [L.placa[0], L.entrada_propuesta[1]]], propios: 3,
    n_sin: sin.length, sin_aparato: sin, propios_sin: 1 };
  const v = await C.vistaE8(ins);
  const h = v.laterales[iLI];
  assert.ok(h.includes('class="e8-haz"') && h.includes(`Pasan hacia la puerta (${cs.length})`), 'FALLA: no se dibuja el haz que pasa hacia la puerta');
  assert.ok(h.includes('de la bandeja principal:') && h.includes('de la bandeja lateral derecha:') && h.includes('además 3 de esta lateral'),
    'FALLA: la lista de los que pasan no dice de dónde vienen');
  const i = h.indexOf(`Sin aparato en el plano (${sin.length + 1})`);     // el título cuenta también los de esta lateral (propios_sin)
  assert.ok(i > h.indexOf('Pasan hacia la puerta') && h.includes('además 1 de esta lateral'), 'FALLA: los sin aparato no van aparte con su rótulo');
  const pasan = h.slice(h.indexOf('Pasan hacia la puerta'), i);
  for (const x of sin) assert.ok(!pasan.includes(`>${x.num}</span>`) && h.slice(i).includes(`>${x.num}</span>`), `FALLA: ${x.num} (${x.aparato}) cuenta como que pasa hacia la puerta`);
  const iLD = ins.estacion8.laterales.findIndex(x => x.lado === 'LD');
  assert.ok(!v.laterales[iLD].includes('class="e8-haz"'), 'FALLA: la otra lateral no tiene la capa');
});

// (pulido 2026-10-09) la flecha de la entrada a la puerta (34·u) y su rótulo «Entrada» entran en el dibujo aunque el
// margen de la imagen sea de un perfil: la vista (viewBox) se agranda; la imagen sigue siendo la de la región
for (const t of ['tpt_constructivo', '75287']) {
  test(`E8-4 ${t}: la flecha de la entrada a la puerta y su rótulo entran en el dibujo`, async () => {
    const ins = C.leer(C.TRABAJOS[t]);
    const P = ins.estacion8.puerta;
    const h = (await C.vistaE8(ins)).afuera;
    const svg = h.slice(h.indexOf('id="e8MapaP"'), h.indexOf('id="e8SelP"'));
    const vb = svg.match(/viewBox="([^"]+)"/)[1].split(' ').map(Number);
    const fl = svg.slice(svg.indexOf('<g class="e8-flecha'));
    const m = fl.match(/<path d="M([\d.-]+) ([\d.-]+)L([\d.-]+) [\d.-]+"/), tx = fl.match(/<text x="([\d.-]+)" y="([\d.-]+)" font-size="([\d.-]+)"/);
    assert.ok(m && tx, 'FALLA: no se encontró la flecha de la entrada');
    const fs = +tx[3], ancho = 0.6 * fs * 'Entrada'.length;
    const xs = [+m[1], +m[3], +tx[1] - ancho / 2, +tx[1] + ancho / 2];
    assert.ok(xs.every(x => x >= vb[0] - 0.05 && x <= vb[0] + vb[2] + 0.05) && +tx[2] - fs >= vb[1] - 0.05,
      `FALLA: la flecha o «Entrada» quedan afuera del dibujo (viewBox ${vb}, flecha ${xs.map(x => x.toFixed(1))})`);
    const r = P.region;
    assert.ok(vb[0] + vb[2] > r[2] + 0.05 || vb[0] < r[0] - 0.05, 'FALLA: la vista no se agrandó (la flecha sale del margen de la imagen)');
    assert.ok(svg.includes(`x="${r[0]}" y="${-r[3]}" width="${r[2] - r[0]}"`), 'FALLA: la imagen de la puerta cambió de lugar');
  });
}
