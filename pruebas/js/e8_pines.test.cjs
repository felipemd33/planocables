'use strict';
/* Estación 8, etapa E8-7 (2026-10-09, pedido del usuario): PINES DE LA PLACA en la pantalla (programa/web/estacion8.js y
   e8mano.js sin tocar, con los instructivos congelados de pruebas/bases/ins_*.json).
   - «Puerta y placa»: el encabezado dice cuántos cables llegan a su pin; la tabla de 21PCB01 dice, debajo de cada pin, la
     aclaración del funcional ('Signal AI5 · AP Analog Input #5'); la placa sin etiqueta del 75441 (75287) lleva su tag.
   - La punta de un cable de la placa (resaltada con el mouse o en el visor de a uno) está en SU pin, con la aclaración al
     lado y sin la franja; con el grupo de placa sin dibujar, el texto dice que falta solo el tramo común; con el tramo
     común dibujado (fixture: «Placa 21PCB01 · bobinas 61KR»), la acometida sale del FINAL del tramo hasta el pin.
   - El visor de a uno de la puerta y el del grupo (ruteo a mano) dicen la aclaración en la punta.
   - En la tabla, la pastilla del grupo de un cable que llega a su pin (pin_puerta) dice «falta el tramo común», no
     «falta dibujar».
   - La lista WPC no usa los pines: sin ellos da IGUAL. */
const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('./comun.cjs');

const lineasP = ins => ins.estacion8.puerta.pasos.flatMap(p => p.lineas);
const corta = a => String(a || '').replace(/^pin [^·]*·\s*/, '').trim();
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const clicVista = (ctx, v) => ctx._elementos.get('#e8Vistas')._eventos.click.forEach(fn => fn({ target: { closest: () => ({ dataset: { v } }) } }));
const hover = (ctx, clave) => ctx._elementos.get('#e8Afuera')._eventos.mouseover.forEach(fn => fn({ target: { closest: s => (s === 'tr[data-clave]' ? { dataset: { clave } } : null) } }));
// ▶ de la fila de la tabla: el visor de a uno de la puerta desde ese cable
const ver = (ctx, clave) => ctx._elementos.get('#e8Afuera')._eventos.click.forEach(fn => fn({ target: {
  closest: s => (s === '[data-a]' ? { dataset: { a: 'ver' }, closest: () => ({ dataset: { clave } }) } : null) } }));
function fila(html, clave) {
  const t = html.split('<tr ').slice(1).find(p => p.split('>')[0].includes(`data-clave="${esc(clave)}"`));
  return t ? '<tr ' + t.split('</tr>')[0] : null;
}

for (const t of ['tpt_constructivo', 'tpt', '66817', '75287']) {
  test(`E8-7 ${t}: «Puerta y placa» con los cables de la placa en su pin y la aclaración en la tabla`, async () => {
    const ins = C.leer(C.TRABAJOS[t]);
    const ls = lineasP(ins).filter(l => l.aparato === '21PCB01');
    assert.ok(ls.length && ls.every(l => l.exacto_o && l.aclaracion), `FALLA: ${t}: los cables de 21PCB01 no tienen su pin en ins_${t}.json`);
    const h = (await C.vistaE8(ins)).afuera;
    assert.ok(h.includes('llegan a su pin de la placa'), 'FALLA: el encabezado no dice que los cables llegan a su pin');
    const tabla = ins.estacion8.afuera.find(g => g.tag === '21PCB01');
    for (const x of tabla.cables.filter(x => x.aclaracion)) {
      const f = fila(h, x.clave);
      assert.ok(f && f.includes('class="small e8-acl-t"') && f.includes(esc(corta(x.aclaracion))),
        `FALLA: la fila de ${x.num} no dice la aclaración del pin (${x.aclaracion})`);
    }
    if (t === '75287') {
      assert.ok(h.includes('21PCB01?</text>') && h.includes('a confirmar'), 'FALLA: la placa sin etiqueta reconocida no lleva su tag ni dice «a confirmar»');
    }
  });
}

// (E8-7) la tabla de «Puerta y placa»: la pastilla del grupo de placa de un cable que llega a su pin dice «falta el tramo
// común» (no «falta dibujar»); la fila trae pin_puerta
for (const t of ['tpt_constructivo', '75287']) {
  test(`E8-7 ${t}: en la tabla, la pastilla del grupo de placa dice que falta solo el tramo común`, async () => {
    const ins = C.leer(C.TRABAJOS[t]);
    const v = await C.vistaE8(ins);
    const cards = v.afuera.split('<div class="card e8-ap">').slice(1);
    const card = tag => cards.find(c => c.includes(`<h3 class="mono">${esc(tag)}</h3>`)) || '';
    const h = card('21PCB01');
    const R = ins.estacion8.ruteo_mano || {};
    const dib = id => { const g = (R.grupos || []).find(x => x.id === id); return !!(g && g.dibujado); };
    const tabla = ins.estacion8.afuera.find(g => g.tag === '21PCB01');
    const xs = tabla.cables.filter(x => x.pin_puerta && x.grupo_mano && !dib(x.grupo_mano));
    assert.ok(xs.length, `FALLA: ${t}: no hay cables de 21PCB01 con pin_puerta y su grupo sin dibujar en ins_${t}.json`);
    for (const x of xs) {
      const f = fila(h, x.clave);
      assert.ok(f && f.includes(' · falta el tramo común</span>') && !f.includes(' · falta dibujar</span>') && f.includes('Falta dibujar el tramo común (✏ Ruteo a mano)'),
        `FALLA: ${t}: la pastilla de ${x.num} en la tabla no dice «falta el tramo común» (${f && f.slice(0, 400)})`);
    }
    // un cable con grupo y SIN pin en la placa sigue diciendo «falta dibujar»
    const gOtro = ins.estacion8.afuera.find(g => g.cables.some(x => x.grupo_mano && !x.pin_puerta && !dib(x.grupo_mano)));
    const otro = gOtro && gOtro.cables.find(x => x.grupo_mano && !x.pin_puerta && !dib(x.grupo_mano));
    if (otro) {
      const f = fila(card(gOtro.tag), otro.clave);
      assert.ok(f && f.includes(' · falta dibujar</span>') && !f.includes('falta el tramo común'), `FALLA: ${t}: ${otro.num} (sin pin) cambió`);
    }
  });
}

test('E8-7 tpt_constructivo: la punta del cable resaltado en su pin, con la aclaración (grupo de placa sin dibujar)', async () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo);
  const l = lineasP(ins).find(x => x.num === '2142');
  assert.equal(l.aclaracion, 'pin 42 · Signal AI5 · AP Analog Input #5');
  const { ctx } = await C.manoE8(ins);
  clicVista(ctx, 'afuera');
  hover(ctx, l.clave);
  const g = ctx._elementos.get('#e8SelP').innerHTML;
  assert.ok(g.includes('class="e8-acl"') && g.includes('>pin 42 · Signal AI5 · AP Analog Input #5</text>'), 'FALLA: no se ve la aclaración junto al pin');
  assert.ok(g.includes('<circle class="ori"/>') && !g.includes('e8-franja'), 'FALLA: la punta no está en el pin (sigue la franja)');
  assert.ok(g.includes('>falta dibujar el tramo común</text>') && g.includes('falta dibujar el tramo común</title>'), 'FALLA: no dice que falta dibujar solo el tramo común');
  // 13SH1 (selectora, sin pines numerados) sigue a la franja
  const s = lineasP(ins).find(x => x.aparato === '13SH1');
  hover(ctx, s.clave);
  const g2 = ctx._elementos.get('#e8SelP').innerHTML;
  assert.ok(g2.includes('e8-franja') && !g2.includes('class="e8-acl"'), 'FALLA: 13SH1 cambió');
});

test('E8-7 tpt_constructivo: con el tramo común dibujado, cada cable va del FINAL del tramo a su pin', async () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo);
  const l = lineasP(ins).find(x => x.num === '2150');
  const R = ins.estacion8.ruteo_mano;
  const gr = R.grupos.find(g => g.id === l.grupo_mano);
  const tr = (gr.tramos || []).find(x => x.vista === 'PUERTA');
  assert.ok(tr && tr.puntos.length > 1, 'FALLA: el fixture no trae el tramo común de «Placa 21PCB01 · bobinas 61KR» en la puerta');
  const fin = tr.puntos[tr.puntos.length - 1];
  const { ctx } = await C.manoE8(ins);
  clicVista(ctx, 'afuera');
  hover(ctx, l.clave);
  const g = ctx._elementos.get('#e8SelP').innerHTML;
  const f2 = v => (+v).toFixed(2);
  assert.ok(g.includes(`M${f2(l.marca_o[0])} ${f2(-l.marca_o[1])}L${f2(fin[0])} ${f2(-fin[1])}`),
    `FALLA: la acometida de 2150 no sale del final del tramo común ${fin} hasta su pin ${l.marca_o}`);
  assert.ok(g.includes('>pin 50 · DO 1+ · Solenoid Valve #1</text>') && !g.includes('falta dibujar'), 'FALLA: la aclaración del pin 50 o el texto del tramo');
});

test('E8-7 tpt_constructivo: el visor de a uno de la puerta dice la aclaración y llega al pin', async () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo);
  const l = lineasP(ins).find(x => x.num === '2142');
  const { ctx } = await C.manoE8(ins);
  clicVista(ctx, 'afuera');
  ver(ctx, l.clave);
  const E = s => ctx._elementos.get(s);
  assert.ok(!E('#e8Viewer').hidden, 'FALLA: no se abrió el visor de la puerta');
  assert.ok(E('#e8vOrig').innerHTML.includes('21PCB01 42') && E('#e8vOrig').innerHTML.includes('· Signal AI5 · AP Analog Input #5'),
    `FALLA: la punta del visor no dice la aclaración (${E('#e8vOrig').innerHTML})`);
  assert.ok(E('#e8vLen').innerHTML.includes('· falta el tramo común</span>') && E('#e8vLen').innerHTML.includes('· de ahí va a su pin 42</span>'), `FALLA: ${E('#e8vLen').innerHTML}`);
  assert.ok(E('#e8vSvg').innerHTML.includes('>pin 42 · Signal AI5 · AP Analog Input #5</text>'), 'FALLA: el dibujo del visor no tiene la aclaración junto al pin');
  assert.ok(E('#e8vLupaOt').textContent.includes('Signal AI5 · AP Analog Input #5'), 'FALLA: la lupa del origen no dice la aclaración');
});

test('E8-7 tpt_constructivo: el visor de a uno del grupo de placa (ruteo a mano) dice la aclaración en la punta', async () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo);
  const { E8M, D, ctx } = await C.manoE8(ins);
  const R = D.estacion8.ruteo_mano;
  const k = Object.keys(R.cables).find(x => R.cables[x].num === '2142');
  const c = R.cables[k];
  assert.ok(c.aclaracion === 'pin 42 · Signal AI5 · AP Analog Input #5' && c.pin_puerta && c[c.aclaracion_de] === '21PCB01 42',
    `FALLA: el cable 2142 del ruteo a mano no trae la aclaración (${JSON.stringify(c)})`);
  E8M.abrir({ grupo: R.miembro[k], clave: k, cablear: true });
  const E = s => ctx._elementos.get(s);
  const punta = E(c.aclaracion_de === 'a' ? '#e8mOrig' : '#e8mDest').textContent;
  assert.equal(punta, '21PCB01 42 · Signal AI5 · AP Analog Input #5', 'FALLA: la punta del visor del grupo');
  assert.ok(E('#e8mFalta').innerHTML.includes('Falta dibujar el tramo común de «Placa 21PCB01»: de ahí cada cable va a su pin'),
    `FALLA: el aviso del visor del grupo (${E('#e8mFalta').innerHTML})`);
  E('#e8mVistas')._eventos.click.forEach(fn => fn({ target: { closest: () => ({ dataset: { vk: 'PUERTA' } }) } }));
  assert.ok(E('#e8mSvg').innerHTML.includes('>Signal AI5 · AP Analog Input #5</text>'), 'FALLA: en la vista de la puerta no se ve la aclaración del cable actual');
});

test('E8-7: la lista WPC no usa los pines de la placa (sin ellos da IGUAL)', async () => {
  for (const t of ['tpt_constructivo', '75287']) {
    const ins = C.leer(C.TRABAJOS[t]);
    const sin = JSON.parse(JSON.stringify(ins));
    const quitar = l => { for (const k of ['aclaracion', 'aclaracion_d', 'pin_p', 'pin_p_d', 'conf_pin', 'conf_pin_d', 'exacto_o', 'exacto_d', 'conf_o', 'conf_d', 'pin_puerta']) delete l[k]; };
    sin.estacion8.afuera.forEach(g => { delete g.en_puerta; g.cables.forEach(quitar); });
    if (sin.estacion8.puerta) sin.estacion8.puerta.pasos.forEach(p => p.lineas.forEach(quitar));
    delete sin.estacion8.pines_aparato;
    const a = await C.correrWpc(ins, { cfg: C.VARIANTES.pend_otra }), b = await C.correrWpc(sin, { cfg: C.VARIANTES.pend_otra });
    assert.equal(a.csv, b.csv, `FALLA: ${t}: la WPC cambia con los pines de la placa`);
  }
});

// (E8-7) la aclaración no cambia lo demás del dibujo: un cable de la misma lateral (con las dos puntas) no lleva el rótulo
// del final del recorrido («A la bandeja principal»), y uno que sale de la lateral sí
test('E8-7 tpt_constructivo: el rótulo del final del recorrido sigue solo en los cables que salen de la lateral', async () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo);
  const v = await C.vistaE8(ins);
  ins.estacion8.laterales.forEach((L, i) => {
    const h = v.laterales[i];
    for (const l of L.pasos.flatMap(p => p.lineas).filter(x => !x.grupo_mano && x.ruta && x.ruta.length > 1)) {
      const t = h.split('<div class="cab ').slice(1).find(p => p.split('>')[0].includes(`data-clave="${esc(l.clave)}"`));
      assert.ok(t, `FALLA: no está la tarjeta de ${l.num}`);
      const g = t.slice(t.indexOf('<g class="rt cur"'), t.indexOf('</svg>'));      // (la miniatura: el cable actual)
      assert.equal(g.includes('class="li"'), !l.marca_d,
        `FALLA: ${L.nombre} ${l.num}: el rótulo del final del recorrido ${l.marca_d ? 'aparece en un cable de la misma lateral' : 'falta'}`);
    }
  });
});
