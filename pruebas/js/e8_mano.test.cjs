'use strict';
/* Estación 8, etapa E8-6 (2026-10-09, pedido del taller): RUTEO A MANO POR GRUPOS en la pantalla (programa/web/
   estacion8.js y e8mano.js sin tocar, con los instructivos congelados de pruebas/bases/ins_*.json, armados con el ruteo a
   mano del fixture pruebas/fixtures/recorridos_e8.json).
   - Un cable con grupo (l.grupo_mano) no dibuja la ruta automática: sus puntas y, si el taller ya dibujó el recorrido del
     grupo en esa vista, ese recorrido; la tarjeta y las tablas dicen el grupo y si falta dibujarlo.
   - Los cables directos del cargador a la bornera de abajo (PAE) dicen «directo al borne».
   - E8M.efectivo (la cuenta de la pantalla) da los mismos grupos que el servidor (estacion8_mano.aplicar) y mover un
     cable o armar un grupo nuevo de placa lo cambia de grupo.
   - 🧲 Pegar al eje: un punto cerca de una canaleta va a su eje.
   - La lista WPC no usa el ruteo a mano: con o sin los grupos da IGUAL. */
const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('./comun.cjs');

function tarjeta(html, clave) {
  const partes = html.split('<div class="cab ').slice(1);
  const t = partes.find(p => p.split('>')[0].includes(`data-clave="${clave}"`));
  return t ? '<div class="cab ' + t : null;
}

test('E8-6 tpt_constructivo: tarjetas y mapa de la lateral izquierda con el ruteo a mano', async () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo);
  const R = ins.estacion8.ruteo_mano;
  assert.ok(R && R.grupos.length, 'FALLA: ins_tpt_constructivo sin ruteo_mano');
  const v = await C.vistaE8(ins);
  const iLI = ins.estacion8.laterales.findIndex(L => L.lado === 'LI');
  const h = v.laterales[iLI];
  // el recorrido de «Batería 35 mm²» dibujado (fixture) en la lateral izquierda
  assert.ok(h.includes('<g class="e8-mano"') && h.includes('Ruteo a mano: Batería 35 mm²'), 'FALLA: no se dibuja el recorrido del grupo en el mapa');
  const L = ins.estacion8.laterales[iLI];
  const l35 = L.pasos.flatMap(p => p.lineas).find(l => l.num === '1205');
  const c = tarjeta(h, l35.clave);
  assert.ok(c && c.includes('e8-manop ok') && c.includes('Batería 35 mm²') && !c.includes('falta dibujar'), 'FALLA: la tarjeta de 1205 no dice su grupo dibujado');
  assert.ok(c.includes('class="rt cur mano"') && !c.includes('<g class="rt cur"'), 'FALLA: la miniatura de 1205 dibuja la ruta automática');
  assert.ok(!c.includes(`≈${l35.largo_mm} mm`), 'FALLA: la tarjeta de un cable con ruteo a mano muestra el largo automático');
  const l46 = L.pasos.flatMap(p => p.lineas).find(l => l.num === '1204');
  const c46 = tarjeta(h, l46.clave);
  assert.ok(c46 && c46.includes('Batería 4 / 6 mm²') && c46.includes('falta dibujar'), 'FALLA: 1204 (batería 4 mm²) no dice que falta dibujar su recorrido');
  // los cables sin grupo siguen como antes (con su ruta automática)
  const sinG = L.pasos.flatMap(p => p.lineas).find(l => !l.grupo_mano && l.ruta);
  const cs = tarjeta(h, sinG.clave);
  assert.ok(cs && cs.includes('<g class="rt cur"') && !cs.includes('e8-manop'), 'FALLA: un cable sin grupo cambió');
  // tablas de puerta y placa: el grupo de cada cable
  assert.ok(v.afuera.includes('Placa 21PCB01 · bobinas 61KR') && v.afuera.includes('Placa 21PCB01') && v.afuera.includes('Selectoras'),
    'FALLA: las tablas de puerta y placa no dicen el grupo de cada cable');
});

test('E8-6 PAE: los cables del cargador a la bornera de abajo van directo (sin el ducto) y sin grupo', async () => {
  const ins = C.leer(C.TRABAJOS['76884']);
  const L = ins.estacion8.laterales[0];
  const ls = L.pasos.flatMap(p => p.lineas).filter(l => l.directo);
  assert.equal(ls.length, 10, `FALLA: ${ls.length} cables directos (se esperaban 10: 1221-1226 y el RS-485)`);
  const v = await C.vistaE8(ins);
  for (const l of ls) {
    const c = tarjeta(v.laterales[0], l.clave);
    assert.ok(c && c.includes('directo al borne') && !c.includes('e8-manop'), `FALLA: ${l.num} no dice «directo al borne»`);
  }
});

test('E8-6: los grupos de la pantalla (E8M.efectivo) son los del servidor, en los 5 trabajos', async () => {
  for (const t of ['tpt', 'tpt_constructivo', '66817', '75287', '76884']) {
    const ins = C.leer(C.TRABAJOS[t]);
    const R = ins.estacion8.ruteo_mano;
    const { E8M } = await C.manoE8(ins);
    const r = E8M.efectivo(JSON.parse(JSON.stringify(R)));
    assert.deepEqual(JSON.parse(JSON.stringify(r.miembro)), R.miembro, `FALLA: ${t}: miembro distinto`);
    const sin = gs => gs.map(g => ({ id: g.id, nombre: g.nombre, categoria: g.categoria, aparato: g.aparato, auto: g.auto, cables: g.cables, n: g.n, tramos: g.tramos, dibujado: g.dibujado }));
    assert.deepEqual(JSON.parse(JSON.stringify(sin(r.grupos))), sin(R.grupos), `FALLA: ${t}: grupos distintos`);
  }
});

test('E8-6: mover un cable de grupo, sacarlo y armar un grupo nuevo de placa', async () => {
  const ins = C.leer(C.TRABAJOS.tpt);
  const { E8M, D } = await C.manoE8(ins);
  const R = D.estacion8.ruteo_mano;
  const k = Object.keys(R.cables).find(x => R.cables[x].num === '6201');
  assert.equal(R.miembro[k], 'solenoides');
  R.manual.mover[k] = 'contactora';
  E8M.efectivo(R);
  assert.equal(R.miembro[k], 'contactora', 'FALLA: no se movió a la contactora');
  assert.ok(R.grupos.find(g => g.id === 'contactora').cables.includes(k) && !R.grupos.find(g => g.id === 'solenoides').cables.includes(k));
  R.manual.mover[k] = '';
  E8M.efectivo(R);
  assert.ok(!(k in R.miembro), 'FALLA: «sin grupo» no lo sacó (vuelve al ruteo automático)');
  R.manual.nuevos.push({ id: 'nuevo:prueba', nombre: 'Placa 21PCB01 · otro', categoria: 'placa', aparato: '21PCB01' });
  const k2 = Object.keys(R.cables).find(x => R.cables[x].num === '2111');
  R.manual.mover[k2] = 'nuevo:prueba';
  R.manual.grupos['nuevo:prueba'] = { tramos: [{ vista: 'FONDO', puntos: [[500, 500], [600, 500]] }, { vista: 'NO EXISTE', puntos: [[1, 1], [2, 2]] }] };
  E8M.efectivo(R);
  const g = R.grupos.find(x => x.id === 'nuevo:prueba');
  assert.ok(g && g.n === 1 && g.dibujado && g.tramos.length === 1 && !g.auto && R.grupos[R.grupos.length - 1] === g,
    'FALLA: el grupo nuevo de placa (con su cable, su recorrido en una vista que existe, al final de la lista)');
});

// (pulido 2026-10-09) «＋ Grupo de placa» con otro grupo elegido toma la placa del trabajo (no queda «Placa · grupo N»
// sin aparato antes del grupo del fixture); un grupo de placa sin aparato (trabajo sin placas) va al final de la lista
test('E8-6: ＋ Grupo de placa con otro grupo elegido toma la placa y queda al final', async () => {
  const { E8M, D, ctx } = await C.manoE8(C.leer(C.TRABAJOS.tpt_constructivo));
  const R = D.estacion8.ruteo_mano;
  E8M.abrir({ grupo: 'bateria_35' });
  const clic = a => ctx._elementos.get('#e8mGrupos')._eventos.click.forEach(fn => fn({ target: { closest: s => (s === '[data-a]' ? { dataset: { a } } : null), matches: () => false } }));
  const antes = R.grupos.map(g => g.id);
  clic('nuevo');
  const nuevo = R.grupos.find(g => !antes.includes(g.id));
  assert.ok(nuevo && nuevo.categoria === 'placa' && nuevo.aparato === '21PCB01' && nuevo.nombre === 'Placa 21PCB01 · grupo 3',
    `FALLA: el grupo nuevo de placa con «Batería 35 mm²» elegido (${JSON.stringify(nuevo)})`);
  const ids = R.grupos.map(g => g.id);
  assert.ok(ids.indexOf('nuevo:fixture1') < ids.indexOf(nuevo.id) && ids[ids.length - 1] === nuevo.id,
    `FALLA: el grupo nuevo no quedó al final, después del del fixture (${ids.join(', ')})`);
  assert.ok(ctx._elementos.get('#e8mGrupos').innerHTML.includes('＋ Grupo de placa 21PCB01'), 'FALLA: el botón no dice de qué placa es el grupo nuevo');
  // sin aparato (un trabajo sin placas): al final, después de los que tienen aparato aunque su id vaya antes
  R.manual.nuevos.push({ id: 'nuevo:000', nombre: 'Placa · grupo 1', categoria: 'placa', aparato: null });
  E8M.efectivo(R);
  assert.equal(R.grupos[R.grupos.length - 1].id, 'nuevo:000', 'FALLA: el grupo de placa sin aparato no va al final');
});

test('E8-6: el ruteo a mano abierto con un cable sin grupo lo busca en la lista (R desde el visor)', async () => {
  const { E8M, D, ctx } = await C.manoE8(C.leer(C.TRABAJOS.tpt_constructivo));
  const R = D.estacion8.ruteo_mano;
  const k = Object.keys(R.cables).find(x => !R.miembro[x]);
  let volvio = 0;
  E8M.abrir({ clave: k, buscar: R.cables[k].num, volver: () => { volvio++; } });
  assert.equal(ctx._elementos.get('#e8mQ').value, R.cables[k].num, 'FALLA: la lista no busca el cable');
  assert.ok(E8M.abierto());
  ctx._elementos.get('#e8mClose')._eventos.click.forEach(fn => fn({}));
  assert.ok(!E8M.abierto() && volvio === 1, 'FALLA: al cerrar no vuelve al visor');
});

test('E8-6: 🧲 pegar al eje de la canaleta', async () => {
  const { E8M } = await C.manoE8(C.leer(C.TRABAJOS.tpt_constructivo));
  const ductos = [{ b: [145.6, 520.0, 281.7, 542.7], h: true }, { b: [239.1, 392.4, 261.8, 520.0], h: false }];
  const im = p => { const q = E8M.iman(p, ductos); return q ? Array.from(q, v => Math.round(v * 100) / 100) : null; };
  assert.deepEqual(im([200, 545]), [200, 531.35], 'FALLA: un punto al lado de la horizontal no va a su eje');
  assert.deepEqual(im([245, 450]), [250.45, 450], 'FALLA: un punto sobre la vertical no va a su eje');
  assert.equal(im([200, 600]), null, 'FALLA: un punto lejos de las canaletas se pegó');
});

test('E8-6: la lista WPC no usa el ruteo a mano (con o sin los grupos da IGUAL)', async () => {
  for (const t of ['tpt_constructivo', '75287']) {
    const ins = C.leer(C.TRABAJOS[t]);
    const sin = JSON.parse(JSON.stringify(ins));
    delete sin.estacion8.ruteo_mano; delete sin.estacion8.fondo;
    const quitar = l => { delete l.grupo_mano; };
    sin.estacion8.laterales.forEach(L => L.pasos.forEach(p => p.lineas.forEach(quitar)));
    sin.estacion8.afuera.forEach(g => g.cables.forEach(quitar));
    if (sin.estacion8.puerta) sin.estacion8.puerta.pasos.forEach(p => p.lineas.forEach(quitar));
    const a = await C.correrWpc(ins, { cfg: C.VARIANTES.pend_otra }), b = await C.correrWpc(sin, { cfg: C.VARIANTES.pend_otra });
    assert.equal(a.csv, b.csv, `FALLA: ${t}: la WPC cambia con el ruteo a mano`);
  }
});
