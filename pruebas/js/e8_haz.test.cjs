'use strict';
/* Estación 8, etapa E8-8 (2026-10-13, pedido del taller: «el ruteo a placa quiero que sea algo simple, ir indicando
   puntos, poder hacer una curva y que al final el ruteo se pueda hacer algo automático, y al final se pueda ver como en
   la última foto pero con la vista de plano»): el HAZ DE LA PLACA en la vista de la puerta.
   - nucleo/haz.js (la geometría): el haz arranca en la entrada (desde: 'entrada'), sus esquinas curvas se redondean; del
     final del haz cada cable va SOLO a su pin en ABANICO: cada rama termina en su pin, ninguna se cruza con otra, en el
     orden de los pines; los cables de la fila de más adentro pasan por el hueco entre dos pines de la de más afuera (sin
     taparlos). Con los pines de verdad de los planos (pruebas/bases/ins_*.json) y con el haz llegando de abajo, de un
     costado, muy cerca de los pines y de arriba (un recorrido de antes).
   - La pantalla (programa/web/estacion8.js y e8mano.js sin tocar): «Cómo queda» en «Puerta y placa» con las mangas y la
     aclaración del pin al pasar el mouse; el visor de a uno con el cable actual resaltado en el haz y en su rama (los
     demás tenues); el editor del haz (✏ Ruteo a mano): arranca en la entrada, puntos, curva (C), Retroceso, Esc
     (cancelar: vuelve como estaba) y «Usar la propuesta» (POST /e8/haz); el PAE sin vista de la puerta (no se puede
     dibujar); el formato de antes sigue cargando.
   - La lista WPC no usa el haz: con o sin él da IGUAL. */
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const C = require('./comun.cjs');
const Haz = require(path.join(C.WEB, 'nucleo', 'haz.js'));

const lineasP = ins => ins.estacion8.puerta.pasos.flatMap(p => p.lineas);
const copia = x => JSON.parse(JSON.stringify(x));
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// los cables de un grupo de placa en la puerta y los pines del aparato (como estacion8.js hazDe)
function datos(ins, gid) {
  const e8 = ins.estacion8, Pd = e8.puerta, g = e8.ruteo_mano.grupos.find(x => x.id === gid);
  const ls = new Map(lineasP(ins).map(l => [l.clave, l]));
  const cables = g.cables.map(k => ls.get(k)).filter(Boolean).map(l => ({ clave: l.clave, num: l.num, fin: [l.marca_o[0], l.marca_o[1]], exacto: !!l.exacto_o }));
  const pines = Object.values(((e8.pines_aparato || {})['21PCB01'] || {}).pines || {}).map(v => v.punto).filter(Boolean);
  return { Pd, g, cables, pines };
}
// el abanico desde el final de un haz (pts, con sus curvas), como lo arma la pantalla
function abanicoDe(pts, curvas, cables, pines, H) {
  const poly = Haz.suave(pts, new Set(curvas || []), H);
  const E = poly[poly.length - 1], A = poly[poly.length - 2];
  return { poly, ab: Haz.abanico(E, [E[0] - A[0], E[1] - A[1]], cables, pines, {}) };
}
// lo que se pide del abanico: cada rama termina en su pin, ninguna se cruza, el orden de las ramas es el de los pines y
// las de la fila de más adentro pasan entre los pines de la de más afuera
function revisar(nombre, ab, cables) {
  for (const c of cables) {
    const r = ab.ramas[c.clave];
    assert.ok(r, `FALLA: ${nombre}: ${c.num} sin rama`);
    assert.ok(dist(r.pts[r.pts.length - 1], c.fin) < 1e-6, `FALLA: ${nombre}: la rama de ${c.num} no termina en su pin ${c.fin}`);
  }
  const cr = Haz.cruces(ab.ramas);
  assert.deepEqual(cr, [], `FALLA: ${nombre}: ramas que se cruzan ${JSON.stringify(cr.slice(0, 4))}`);
  const ts = ab.orden.map(k => ab.ramas[k].t);
  assert.ok(ts.every((t, i) => !i || t >= ts[i - 1] - 1e-9), `FALLA: ${nombre}: las ramas no salen del haz en el orden de los pines`);
  const cerca = ab.filas[0], p = ab.paso;
  for (const k of ab.orden) {
    const r = ab.ramas[k];
    if (!(r.fila > 0)) continue;
    // a la altura de la fila de más afuera, la rama pasa lejos de sus pines (por un hueco)
    const q = r.pts.find((a, i) => i && (a[1] - cerca.y) * (r.pts[i - 1][1] - cerca.y) <= 0) || r.pts[0];
    const d = Math.min(...cerca.xs.map(x => Math.abs(x - q[0])));
    assert.ok(d >= 0.35 * p, `FALLA: ${nombre}: la rama de ${k} pasa sobre un pin de la fila de más afuera (a ${d.toFixed(2)} de un pin, paso ${p.toFixed(2)})`);
  }
}

test('E8-8 haz.js: el haz arranca en la entrada, sus curvas se redondean y un recorrido de antes se da vuelta hacia los pines', () => {
  const pl = Haz.polilinea({ puntos: [[10, 0], [10, 10]], curvas: [0], desde: 'entrada' }, [0, 0], null);
  assert.deepEqual(pl.pts, [[0, 0], [10, 0], [10, 10]]);
  assert.deepEqual([...pl.curvas], [1], 'FALLA: la curva no corre un lugar con la entrada');
  const s = Haz.suave(pl.pts, pl.curvas, 5);
  assert.ok(dist(s[0], [0, 0]) < 1e-9 && dist(s[s.length - 1], [10, 10]) < 1e-9 && !s.some(q => dist(q, [10, 0]) < 1), 'FALLA: la esquina curva no se redondea');
  assert.ok(Math.max(...s.map(q => Math.min(Math.abs(q[1]), Math.abs(q[0] - 10)))) < 5 * 0.3, 'FALLA: la curva se aleja demasiado de la esquina');
  const v = Haz.polilinea({ puntos: [[100, 0], [10, 0], [0, 0]] }, [999, 999], [100, 5]);
  assert.deepEqual(v.pts, [[0, 0], [10, 0], [100, 0]], 'FALLA: el recorrido de antes no termina del lado de los pines');
  assert.ok(!v.desde, 'FALLA: un recorrido de antes no arranca en la entrada');
  const pr = Haz.precintos([[0, 0], [100, 0]], 20);
  assert.ok(pr.length >= 4 && pr.every(x => x.p[1] === 0 && x.t[0] === 1), 'FALLA: los precintos');
});

for (const t of ['tpt_constructivo', 'tpt', '66817', '75287']) {
  test(`E8-8 ${t}: el abanico de la placa (cada cable a su pin, sin cruzarse) con el haz llegando de abajo, de un costado, muy cerca y de arriba`, () => {
    const ins = C.leer(C.TRABAJOS[t]);
    const { Pd, cables, pines } = datos(ins, 'placa:21PCB01');
    assert.ok(cables.length > 10 && cables.every(c => c.exacto) && pines.length > 60, `FALLA: ${t}: faltan los cables o los pines de 21PCB01`);
    const H = Pd.H, xs = cables.map(c => c.fin[0]), cx = (Math.min(...xs) + Math.max(...xs)) / 2, ymin = Math.min(...cables.map(c => c.fin[1]));
    const ymax = Math.max(...cables.map(c => c.fin[1]));
    const casos = {
      'de abajo, derecho': [[cx + 4 * H, ymin - 5 * H], [cx, ymin - 5 * H], [cx, ymin - 2.5 * H]],
      'de un costado (por el perfil)': [[cx + 6 * H, ymin - 2 * H], [cx, ymin - 2 * H]],
      'del otro costado': [[cx - 6 * H, ymin - 2.5 * H], [cx - 1.5 * H, ymin - 2.5 * H]],
      'muy cerca de los pines': [[cx + 3 * H, ymin - 3 * H], [cx, ymin - 0.2 * H]],
      'de arriba (un recorrido de antes)': [[cx + 4 * H, ymax + 3 * H], [cx, ymax + 1.5 * H]],
    };
    for (const [nombre, pts] of Object.entries(casos)) {
      const { ab } = abanicoDe([Pd.entrada, ...pts], [1], cables, pines, H);
      revisar(`${t} ${nombre}`, ab, cables);
      assert.equal(ab.lado, nombre.startsWith('de arriba') ? -1 : 1, `FALLA: ${t} ${nombre}: el lado del abanico`);
    }
  });
}

test('E8-8 haz.js: dos cables al mismo pin y un cable sin pin (a la franja) también llegan', () => {
  const pines = [0, 1, 2, 3, 4, 5].map(i => [100 + 3 * i, 50]).concat([0, 1, 2, 3, 4].map(i => [101.5 + 3 * i, 60]));
  const cables = [{ clave: 'a', num: '1', fin: [103, 50], exacto: true }, { clave: 'b', num: '2', fin: [103, 50], exacto: true },
    { clave: 'c', num: '3', fin: [104.5, 60], exacto: true }, { clave: 'd', num: '4', fin: [130, 45], exacto: false }];
  const ab = Haz.abanico([110, 10], [0, 1], cables, pines, {});
  for (const c of cables) { const r = ab.ramas[c.clave]; assert.ok(dist(r.pts[r.pts.length - 1], c.fin) < 1e-6, `FALLA: ${c.clave}`); }
  assert.deepEqual(Haz.cruces(ab.ramas), [], 'FALLA: se cruzan');
});

// el haz dibujado (formato nuevo) puesto en el grupo de placa, como lo deja el editor
function conHaz(ins, gid, haz) {
  const D = copia(ins), R = D.estacion8.ruteo_mano;
  R.manual = R.manual || { grupos: {}, nuevos: [], mover: {} };
  R.manual.grupos[gid] = { tramos: [haz] };
  const g = R.grupos.find(x => x.id === gid);
  g.tramos = [haz]; g.dibujado = true;
  return D;
}
const HAZ_TPT = { vista: 'PUERTA', puntos: [[881.8, 525.2], [881.8, 374.7], [783.9, 374.7], [783.9, 394.3]], curvas: [0, 1, 2], desde: 'entrada' };

test('E8-8 tpt_constructivo: «Cómo queda» en «Puerta y placa», con las mangas y la aclaración del pin al pasar el mouse', async () => {
  const ins = conHaz(C.leer(C.TRABAJOS.tpt_constructivo), 'placa:21PCB01', HAZ_TPT);
  const v = await C.vistaE8(ins);
  const h = v.afuera;
  assert.ok(h.includes('<div class="card e8-final">') && h.includes('Cómo queda'), 'FALLA: no está «Cómo queda»');
  const fin = h.slice(h.indexOf('<div class="card e8-final">'));
  const { cables } = datos(ins, 'placa:21PCB01');
  for (const c of cables) {
    const l = lineasP(ins).find(x => x.clave === c.clave);
    assert.ok(fin.includes(`dominant-baseline="central">${esc(l.num)}</text>`), `FALLA: falta la manga de ${l.num}`);
    assert.ok(fin.includes(`<title>${esc(l.num)} · ${esc(l.origen)} · ${esc(l.aclaracion)}</title>`), `FALLA: la aclaración de ${l.num} al pasar el mouse`);
  }
  assert.ok(fin.includes('stroke="#050505"'), 'FALLA: sin precintos');
  assert.ok(h.includes('Haz «Placa 21PCB01»: <b class="sal-eleg">dibujado</b>'), 'FALLA: el mapa no dice que el haz está dibujado');
  // el otro grupo de placa (del fixture, formato de antes) también se ve
  assert.ok((h.match(/<g class="e8-hz" data-grupo="nuevo:fixture1"/g) || []).length >= 1, 'FALLA: el haz del recorrido de antes no se dibuja');
});

test('E8-8 tpt_constructivo: el visor de a uno resalta el cable actual en el haz y en su rama; los demás tenues', async () => {
  const ins = conHaz(C.leer(C.TRABAJOS.tpt_constructivo), 'placa:21PCB01', HAZ_TPT);
  const l = lineasP(ins).find(x => x.num === '2142');
  const { ctx } = await C.manoE8(ins);
  ctx._elementos.get('#e8Vistas')._eventos.click.forEach(fn => fn({ target: { closest: () => ({ dataset: { v: 'afuera' } }) } }));
  ctx._elementos.get('#e8Afuera')._eventos.click.forEach(fn => fn({ target: { closest: s => (s === '[data-a]' ? { dataset: { a: 'ver' }, closest: () => ({ dataset: { clave: l.clave } }) } : null) } }));
  const E = s => ctx._elementos.get(s);
  const svg = E('#e8vSvg').innerHTML;
  assert.ok(!E('#e8Viewer').hidden && svg.includes(`<g class="e8-hzr cur" data-clave="${l.clave}">`), 'FALLA: el cable actual no está resaltado en el abanico');
  assert.ok((svg.match(/ opacity="\.3"/g) || []).length >= 10, 'FALLA: los demás cables no quedan tenues');
  assert.ok(svg.includes('stroke="#ff6a00" stroke-width'), 'FALLA: el cable actual no se marca adentro del haz');
  assert.ok(E('#e8vLen').innerHTML.includes('· del haz va a su pin 42'), `FALLA: ${E('#e8vLen').innerHTML}`);
});

test('E8-8 editor del haz: arranca en la entrada, puntos, curva (C), Retroceso, Esc cancela y «Usar la propuesta»', async () => {
  const prop = { entrada: [919.3, 525.2], puntos: [[881.8, 525.2], [881.8, 374.7], [783.9, 374.7], [783.9, 394.3]], curvas: [0, 1, 2], fin: [783.94, 394.27], lado: 1 };
  let pedido = null;
  const api = async (u, o) => { if (String(u).endsWith('/e8/haz')) { pedido = JSON.parse(o.body); return copia(prop); } return {}; };
  const { E8M, D, ctx } = await C.manoE8(C.leer(C.TRABAJOS.tpt_constructivo), { api });
  ctx.confirm = () => true;
  const R = D.estacion8.ruteo_mano, P = E8M.prueba;
  E8M.abrir({ grupo: 'placa:21PCB01' });
  P.setDib(true);
  const tr = () => copia((R.manual.grupos['placa:21PCB01'] || { tramos: [] }).tramos.filter(t => t.vista === 'PUERTA'));     // (copia: arreglos de otro contexto)
  assert.deepEqual(tr(), [{ vista: 'PUERTA', puntos: [], curvas: [], desde: 'entrada' }], 'FALLA: el haz no arranca en la entrada');
  P.agregarPunto([881.8, 450]); P.agregarPunto([881.8, 380]); P.curva(); P.agregarPunto([785, 380]); P.agregarPunto([700, 300]);
  P.deshacer();
  assert.deepEqual(tr()[0].puntos, [[881.8, 450], [881.8, 380], [785, 380]], 'FALLA: los puntos (y Retroceso)');
  assert.deepEqual(tr()[0].curvas, [1], 'FALLA: la curva del punto 2');
  const g = R.grupos.find(x => x.id === 'placa:21PCB01');
  assert.ok(g.dibujado && ctx._elementos.get('#e8mSvg').innerHTML.includes('<g class="e8-hz"'), 'FALLA: no se dibuja el haz con su abanico');
  assert.ok(ctx._elementos.get('#e8mSvg').innerHTML.includes('arranca en la entrada'), 'FALLA: no se marca la entrada');
  // Esc: vuelve a como estaba antes de dibujar (sin haz)
  P.cancelarHaz();
  assert.deepEqual(tr(), [], 'FALLA: Esc no cancela');
  // «Usar la propuesta»
  await P.propuestaHaz();
  assert.ok(pedido && pedido.claves.length === g.cables.length && pedido.recorridos, 'FALLA: el pedido de la propuesta (claves y recorridos)');
  assert.deepEqual(tr(), [{ vista: 'PUERTA', puntos: prop.puntos, curvas: prop.curvas, desde: 'entrada' }], 'FALLA: «Usar la propuesta» no llena el haz');
});

test('E8-8 PAE: sin vista de la puerta la pantalla lo dice y no se puede dibujar el haz', async () => {
  const ins = C.leer(C.TRABAJOS['76884']);
  assert.ok(!ins.estacion8.puerta, 'FALLA: el PAE trae vista de la puerta');
  const v = await C.vistaE8(ins);
  assert.ok(v.afuera.includes('El topográfico no trae la vista de la puerta: el haz de la placa no se puede dibujar acá'), 'FALLA: «Puerta y placa» no lo dice');
  const { E8M, D } = await C.manoE8(ins);
  const R = D.estacion8.ruteo_mano;
  E8M.abrir({ grupo: 'placa:21PCB01' });
  const antes = JSON.stringify(R.manual);
  E8M.prueba.setDib(true);
  assert.ok(!E8M.prueba.estado().dib && JSON.stringify(R.manual) === antes, 'FALLA: se pudo dibujar sin la vista de la puerta');
});

test('E8-8: la lista WPC no usa el haz de la placa (con o sin él da IGUAL)', async () => {
  for (const t of ['tpt_constructivo', '75287']) {
    const ins = C.leer(C.TRABAJOS[t]);
    const con = conHaz(ins, 'placa:21PCB01', HAZ_TPT);
    const a = await C.correrWpc(ins, { cfg: C.VARIANTES.pend_otra }), b = await C.correrWpc(con, { cfg: C.VARIANTES.pend_otra });
    assert.equal(a.csv, b.csv, `FALLA: ${t}: la WPC cambia con el haz`);
  }
});
