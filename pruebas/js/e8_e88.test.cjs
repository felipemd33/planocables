'use strict';
/* Estación 8, etapa E8-8 (2026-10-13, pedido del taller): la pantalla (programa/web/estacion8.js, e8mano.js,
   instructivo.js y salidas.js sin tocar, con los instructivos congelados de pruebas/bases/ins_*.json).
   1. El visor de cablear de a uno dibuja SOLO el recorrido a mano del grupo del cable actual (los otros grupos, nunca);
      en el mapa de la pestaña quedan, tenues. En el visor de a uno del ruteo a mano (e8mano.js), lo mismo.
   2. Un punto de paso que se saltea (canaleta sin salida: el cable no va y vuelve) se avisa en el visor de E6, en el
      editor de salidas (🧭), en el visor de E8 y en su 🧭 Entrada / salida.
   3. Los cables de la placa en las laterales van por su ruta automática (se dibujan, con su largo; no «falta dibujar»);
      el cable de comunicación muestra el camino entero: el otro tramo y la punta marcada como el empalme (75287: el
      borne de 12XPS, terminal doble; TPT: el empalme de 12PS2). Sin la vista de la puerta (PAE), el grupo de la placa
      dice «sin vista de la puerta». */
const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('./comun.cjs');

const lineas = L => L.pasos.flatMap(p => p.lineas);
function tarjeta(html, clave) {
  const t = html.split('<div class="cab ').slice(1).find(p => p.split('>')[0].includes(`data-clave="${clave}"`));
  return t ? '<div class="cab ' + t : null;
}
// el visor de cablear de E8 abierto en la línea l de la lateral i (como un clic en la lista del visor)
function abrirVisorE8(ctx, i, l, L) {
  const ev = n => ctx._elementos.get(n)._eventos;
  ev('#e8Vistas').click.forEach(fn => fn({ target: { closest: () => ({ dataset: { v: String(i) } }) } }));
  ev('#e8Cablear').click.forEach(fn => fn({}));
  const k = lineas(L).indexOf(l);
  ev('#e8vList').click.forEach(fn => fn({ target: { closest: s => (s === '.cv-it' ? { dataset: { k: String(k) } } : null), matches: () => false } }));
  return { svg: ctx._elementos.get('#e8vSvg').innerHTML, deriv: ctx._elementos.get('#e8vDeriv') };
}
const gruposEnSvg = svg => [...svg.matchAll(/<title>Ruteo a mano: ([^(<]*) \(/g)].map(m => m[1].trim());

test('E8-8 (1) el visor de E8 dibuja solo el recorrido a mano del grupo del cable actual; el mapa, todos tenues', async () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo);
  const i = ins.estacion8.laterales.findIndex(L => L.lado === 'LI'), L = ins.estacion8.laterales[i];
  // (el taller dibujó también los solenoides en la lateral izquierda: otro grupo en la misma vista)
  const R = ins.estacion8.ruteo_mano;
  R.manual.grupos.solenoides = { tramos: [{ vista: L.clave_vista, puntos: [[250, 531.3], [300, 531.3]] }] };
  const { E8, E8M, ctx } = await C.manoE8(ins);
  E8M.efectivo(E8.int.RM()); E8.int.aplicarMano(E8.int.RM());
  E8.int.render();
  const sinG = lineas(L).find(l => !l.grupo_mano && l.ruta), l35 = lineas(L).find(l => l.num === '1205');
  const a = abrirVisorE8(ctx, i, sinG, L);
  assert.ok(!a.svg.includes('class="e8-mano'), `FALLA: el visor de ${sinG.num} (sin grupo) dibuja recorridos a mano: ${gruposEnSvg(a.svg)}`);
  const b = abrirVisorE8(ctx, i, l35, L);
  const gs = gruposEnSvg(b.svg);
  assert.ok(b.svg.includes('class="e8-mano on"') && gs.length && gs.every(g => g === 'Batería 35 mm²'),
    `FALLA: el visor de 1205 tendría que dibujar solo «Batería 35 mm²» (dibuja ${gs})`);
  // el mapa de la pestaña: todos los grupos, tenues
  const v = await C.vistaE8(ins);
  assert.ok(v.laterales[i].includes('<g class="e8-tenue"><g class="e8-mano"'), 'FALLA: el mapa de la lateral no muestra los recorridos a mano tenues');
});

test('E8-8 (1) el visor de a uno del ruteo a mano dibuja solo su grupo (al editar, los otros quedan finos)', async () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo);
  const L = ins.estacion8.laterales.find(L => L.lado === 'LI');
  ins.estacion8.ruteo_mano.manual.grupos.solenoides = { tramos: [{ vista: L.clave_vista, puntos: [[250, 531.3], [300, 531.3]] }] };
  const { E8M, ctx } = await C.manoE8(ins);
  E8M.abrir({ grupo: 'bateria_35', cablear: true });
  const svg = ctx._elementos.get('#e8mSvg').innerHTML;
  assert.ok(!svg.includes('e8-mano otro'), 'FALLA: el visor de a uno de «Batería 35 mm²» dibuja otros grupos');
  ctx._elementos.get('#e8mClose')._eventos.click.forEach(fn => fn({}));
  E8M.abrir({ grupo: 'bateria_35' });
  ctx._elementos.get('#e8mVistas')._eventos.click.forEach(fn => fn({ target: { closest: () => ({ dataset: { vk: L.clave_vista } }) } }));
  assert.ok(ctx._elementos.get('#e8mSvg').innerHTML.includes('e8-mano otro'), 'FALLA: al editar no se ven los otros grupos (finos)');
});

test('E8-8 (2) el punto de paso salteado se avisa en el visor de E6 y en el editor de salidas', async () => {
  const ins = C.leer(C.TRABAJOS['76884']);
  ins.salidas = { grupos: [{ aplica: 'LI', id: 'li', nombre: 'Todos los LI', puntos: [[807.82, 650.42], [566.33, 444.81]] }, { aplica: 'LD', id: 'ld', nombre: 'Todos los LD', puntos: [] }] };
  const ls = ins.pasos.flatMap(p => p.lineas), l = ls.find(x => x.num === '1161');
  for (const x of ls.filter(x => x.destino === 'LI' && !x.intrinseco)) x.salida = 'li';
  l.salteados = [1];
  const { Ins, Sal, ctx } = await C.visorE6(ins);
  Ins.openViewer(Ins.flat().findIndex(x => x.l.num === '1161'));
  const av = ctx._elementos.get('#cvAviso');
  assert.ok(!av.hidden && av.innerHTML.includes('El punto de paso 1 de «Todos los LI» queda en una canaleta sin salida: se saltea'),
    `FALLA: el visor de E6 no avisa el punto salteado (${av.innerHTML})`);
  const k2 = Ins.flat().findIndex(x => x.l.num !== '1161' && !x.l.salteados);
  Ins.openViewer(k2);
  assert.ok(av.hidden, 'FALLA: el aviso queda en un cable sin puntos salteados');
  Sal.open({ num: '1161' });
  const gs = ctx._elementos.get('#salGrupos').innerHTML, mk = ctx._elementos.get('#salMarcas').innerHTML;
  assert.ok(/El punto de paso 1 queda en una canaleta sin salida para 1 de sus \d+ cables: se saltea/.test(gs), 'FALLA: el editor de salidas no avisa el punto salteado');
  assert.ok(mk.includes(' salt"') && mk.includes('queda en una canaleta sin salida: se saltea'), 'FALLA: el punto salteado no se marca en el dibujo del editor');
});

test('E8-8 (2) el punto de paso salteado se avisa en el visor de E8 y en su 🧭 Entrada / salida', async () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo);
  const i = ins.estacion8.laterales.findIndex(L => L.lado === 'LD'), L = ins.estacion8.laterales[i];
  const l = lineas(L).find(x => !x.marca_d && !x.grupo_mano);
  ins.estacion8.recorridos = { preguntar: false, bisagra: null, vistas: { [L.clave_vista]: { entrada: [[900, 600], L.entrada_propuesta], puerta: [], grupos: [] } } };
  l.salteados = [1]; l.sale = 'entrada';
  const { ctx } = await C.manoE8(ins);
  const v = abrirVisorE8(ctx, i, l, L);
  assert.ok(!v.deriv.hidden && v.deriv.innerHTML.includes('El punto de paso 1 de la entrada queda en una canaleta sin salida: se saltea'),
    `FALLA: el visor de E8 no avisa el punto salteado (${v.deriv.innerHTML})`);
  ctx._elementos.get('#e8vEntrada')._eventos.click.forEach(fn => fn({}));
  const gs = ctx._elementos.get('#e8sGrupos').innerHTML;
  assert.ok(gs.includes('queda en una canaleta sin salida') && ctx._elementos.get('#e8sMarcas').innerHTML.includes(' salt"'),
    'FALLA: el 🧭 Entrada / salida de E8 no avisa (ni marca) el punto salteado');
});

test('E8-8 (3) los cables de la placa en las laterales se dibujan con su ruta automática (75287, TPT)', async () => {
  for (const t of ['75287', 'tpt_constructivo']) {
    const ins = C.leer(C.TRABAJOS[t]);
    const R = ins.estacion8.ruteo_mano, solo = new Set(R.grupos.filter(g => g.solo_puerta).map(g => g.id));
    const v = await C.vistaE8(ins);
    let n = 0;
    ins.estacion8.laterales.forEach((L, i) => lineas(L).filter(l => solo.has(R.miembro[l.clave])).forEach(l => {
      const c = tarjeta(v.laterales[i], l.clave); n++;
      assert.ok(c && c.includes('<g class="rt cur"') && !c.includes('e8-manop') && !c.includes('falta dibujar') && c.includes(`≈${l.largo_mm} mm`),
        `FALLA: ${t}: la tarjeta de ${l.num} (placa) en la lateral no se dibuja con su ruta automática`);
    }));
    assert.ok(n >= 2, `FALLA: ${t}: no hay cables de la placa en las laterales`);
    // en las tablas de «Puerta y placa» siguen con su grupo
    assert.ok(v.afuera.includes('Placa 21PCB01'), `FALLA: ${t}: las tablas de la puerta no dicen el grupo de la placa`);
  }
});

test('E8-8 (3) cable de comunicación: el visor muestra el camino entero y marca el empalme (75287: borne; TPT: empalme)', async () => {
  for (const [t, num, txt, borne] of [['75287', '2135', 'empalme en el borne', true], ['tpt_constructivo', '8105', 'en el mismo empalme', false]]) {
    const ins = C.leer(C.TRABAJOS[t]);
    const i = ins.estacion8.laterales.findIndex(L => L.lado === 'LI'), L = ins.estacion8.laterales[i];
    const l = lineas(L).find(x => x.num === num && x.a_puerta), otro = lineas(L).find(x => x.num === num && x !== l);
    assert.ok(l && otro, `FALLA: ${t}: ${num} sin sus dos tramos en la lateral izquierda`);
    const { ctx } = await C.manoE8(ins);
    const v = abrirVisorE8(ctx, i, l, L);
    const h = v.deriv.innerHTML;
    assert.ok(!v.deriv.hidden && h.includes(txt) && h.includes('el camino entero') && h.includes(otro.destino) && h.includes(l.destino),
      `FALLA: ${t}: el visor de ${num} no muestra el camino entero (${h})`);
    assert.ok(borne ? h.includes('terminal doble') && v.svg.includes('class="e8-union"') : !v.svg.includes('class="e8-union"') && v.svg.includes('e8-emp conf'),
      `FALLA: ${t}: la punta de ${num} no está marcada como el empalme`);
    // el otro tramo se ve como continuación (punteado) y el actual con su ruta
    assert.ok(v.svg.includes(`<g class="rt sib" data-clave="${otro.clave}"`) && v.svg.includes(`<g class="rt cur" data-clave="${l.clave}"`),
      `FALLA: ${t}: no se ven los dos tramos de ${num}`);
  }
});

test('E8-8 (3) PAE: el grupo de la placa sin la vista de la puerta no se cuenta como «sin dibujar»', async () => {
  const ins = C.leer(C.TRABAJOS['76884']);
  const g = ins.estacion8.ruteo_mano.grupos.find(x => x.id === 'placa:21PCB01');
  assert.ok(g && g.solo_puerta && g.sin_puerta, 'FALLA: el grupo de la placa del PAE no dice sin_puerta');
  const v = await C.vistaE8(ins);
  assert.ok(v.afuera.includes('Placa 21PCB01 · sin vista de la puerta') && !v.afuera.includes('Placa 21PCB01 · falta dibujar'),
    'FALLA: la tabla de 21PCB01 del PAE no dice «sin vista de la puerta»');
  const { ctx } = await C.manoE8(ins);
  const b = ctx._elementos.get('#e8Mano').innerHTML, n = ins.estacion8.ruteo_mano.grupos.filter(x => x.n && !x.sin_puerta).length;
  assert.ok(b.includes(` de ${n} sin dibujar`), `FALLA: el botón ✏ Ruteo a mano cuenta la placa del PAE (${b})`);
});
