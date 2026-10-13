'use strict';
/* El .wpc de LATERALES (2026-10-13, pedido del usuario): los cables que nacen y mueren en la MISMA bandeja lateral (en la
   E8, otra = 'misma bandeja'; en E6 son pendientes LI↔LI) van en un .wpc aparte, uno solo para las dos laterales, con el
   largo como en la bandeja (recorrido en la lateral + sobrante + agregado, redondeado), y no van en la lista principal
   aunque se tilden los pendientes:
   - golden del CSV y de las filas de laterales (pruebas/bases/wpc/wpc_<trabajo>_laterales.*) y la pantalla (wpc.js) igual
     al núcleo; los trabajos sin cables así (66817) no tienen archivo;
   - TPT: los 11 de la lateral derecha; PAE: los directos del cargador y los de comunicación fuera; 75287: 1101 / 1102 con la
     ruta automática de la línea (el grupo a mano no cambia el largo);
   - no están en la lista principal (ni con los pendientes tildados) y los demás pendientes siguen;
   - sin E8 no hay laterales y los pendientes siguen como antes; quitados a mano, cables repetidos, ediciones y termos;
   - el XML, el zip y el nombre del archivo ('<código> - <plano> Rev <rev> - Laterales.wpc', igual el ProjectName). */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const C = require('./comun.cjs');
const X = require('./wpc_xml.cjs');
const W = require(path.join(C.RAIZ, 'programa', 'web', 'nucleo', 'wpc_core.js'));
const CONFIG = C.leer(C.CONFIG_WPC);

const cfgDe = (ins, trabajo) => W.config(CONFIG, { producto: ins.producto, trabajo: Object.assign({}, (ins.wpc || {}).cfg, trabajo) });
const lat = (ins, trabajo) => W.laterales(ins, cfgDe(ins, trabajo));
const principal = (ins, trabajo) => W.filas(ins, cfgDe(ins, Object.assign({ pendientes: true, otra: true }, trabajo)));
const up = (v, r) => Math.ceil(v / r) * r;
// las líneas de la E8 de una misma lateral (otra = 'misma bandeja')
const lineasMisma = ins => ((ins.estacion8 || {}).laterales || []).flatMap(L => L.pasos.flatMap(p => p.lineas.filter(l => l.otra === 'misma bandeja').map(l => ({ l, L }))));
const normal = fs_ => JSON.parse(JSON.stringify(fs_.map(C.normalizarFila), (k, v) => (typeof v === 'number' && !Number.isFinite(v) ? String(v) : v)));

for (const [nombre, ins] of C.entradasWpc()) {
  test(`WPC laterales ${nombre}: CSV byte a byte y filas iguales al golden (o sin archivo si no hay cables de una misma lateral)`, async () => {
    const r = await C.correrWpc(ins);
    const pCsv = C.archivoLat(nombre, 'csv'), pJson = C.archivoLat(nombre, 'json');
    if (!r.laterales.length) {
      assert.ok(!fs.existsSync(pCsv) && !fs.existsSync(pJson), `FALLA: ${nombre} no tiene cables de una misma lateral y hay golden de laterales`);
      return;
    }
    assert.ok(fs.existsSync(pCsv) && fs.existsSync(pJson), `FALLA: falta el golden ${pCsv} (node pruebas/js/generar_goldens.cjs)`);
    const golden = fs.readFileSync(pCsv);
    assert.ok(Buffer.from(r.csvLat, 'utf8').equals(golden), `FALLA: el CSV de laterales cambió: ${C.difCsv(r.csvLat, golden.toString('utf8'))}`);
    const g = C.leer(pJson);
    const dif = C.difLista(r.laterales, g.filas, x => `${x.num} ${x.origen} → ${x.destino}`);
    assert.equal(dif, null, `FALLA: las filas de laterales cambiaron: ${dif}`);
    assert.equal(r.laterales.filter(f => !f.fuera).length, g.filas_csv);
    assert.equal(g.archivo, C.nombreLat(ins), 'FALLA: cambió el nombre del .wpc de laterales');
    // la pantalla (wpc.js) da lo mismo que el núcleo
    const cfg = cfgDe(ins), fl = W.laterales(ins, cfg);
    assert.deepEqual(normal(fl), r.laterales, `FALLA: ${nombre}: las filas de laterales del núcleo no son las de la pantalla`);
    assert.equal(W.csv(fl.filter(f => !f.fuera), cfg), r.csvLat);
  });
}

test('TPT (con el constructivo y el de prueba): los 11 cables de la lateral derecha, largo como en la bandeja', () => {
  for (const t of ['tpt_constructivo', 'tpt']) {
    const ins = C.leer(C.TRABAJOS[t]), fl = lat(ins), cfg = cfgDe(ins);
    assert.deepEqual(fl.map(f => f.l.num).sort(), ['1317', '1318', '1601', '1603', '1605', '1607', '1609', '1611', '1613', '1615', '1619'], `FALLA: ${t}`);
    const ls = new Map(lineasMisma(ins).map(x => [x.l.clave, x]));
    for (const f of fl) {
      assert.equal(f.tipo, 'lateral');
      assert.equal(f.donde, 'bandeja lateral derecha');
      assert.ok(!f.fuera && !f.motivo, `FALLA: ${t} ${f.l.num} va al arnés`);
      assert.equal(f.sec, '1');
      const x = ls.get(f.l.clave);
      assert.ok(x && x.L.lado === 'LD' && x.l.largo_mm > 0);
      assert.equal(f.largo, up(x.l.largo_mm + cfg.margen_bandeja + cfg.agregado_bandeja, cfg.redondeo), `FALLA: ${t} ${f.l.num}`);
      assert.equal(f.calc.como, `recorrido en la bandeja lateral derecha ${x.l.largo_mm} + sobrante 100 + agregado 75, redondeado a 50`);
      assert.match(f.grupo, /^Bandeja lateral derecha · Riel 1 · parte de (arriba|abajo)/);
    }
    // en el orden de cableado de la E8 (paso por paso)
    assert.deepEqual(fl.map(f => f.l.clave), lineasMisma(ins).map(x => x.l.clave));
    const f1317 = fl.find(f => f.l.num === '1317'), f1603 = fl.find(f => f.l.num === '1603'), f1601 = fl.find(f => f.l.num === '1601');
    assert.deepEqual([f1317.largo, f1603.largo, f1601.largo], [650, 700, 400]);
    // termos: el lado del riel de la lateral de cada punta (arriba / abajo → 0|0; las dos arriba → 0|180)
    assert.deepEqual([f1317.giro, f1603.giro, f1601.giro], ['0|0', '0|180', '0|0']);
    assert.deepEqual([f1603.giroCalc.o, f1603.giroCalc.d], ['arriba', 'arriba']);
  }
});

test('PAE: los directos del cargador con su largo directo; los de comunicación quedan fuera del arnés', () => {
  for (const t of ['76884', 'pae_usuario']) {
    const ins = C.leer(C.TRABAJOS[t]), fl = lat(ins);
    assert.equal(fl.length, 17, `FALLA: ${t}: ${fl.length}`);
    assert.deepEqual(fl.filter(f => !f.fuera).map(f => f.l.num).sort(),
      ['1156', '1157', '1158', '1159', '1181', '1182', '1221', '1222', '1223', '1224', '1225', '1226', '⏚11SK1'].sort(), `FALLA: ${t}`);
    const com = fl.filter(f => /^s\/n /.test(f.l.num));
    assert.equal(com.length, 4);
    for (const f of com) assert.ok(f.fuera && f.motivo === 'comunicación (sección fina)', `FALLA: ${t} ${f.l.num}: ${f.motivo}`);
    assert.ok(fl.every(f => f.donde === 'bandeja lateral izquierda'));
    if (t === '76884') {      // (la E8 de hoy: los cables directos del cargador a la bornera de abajo, E8-6)
      for (const n of ['1221', '1222', '1223', '1224', '1225', '1226']) {
        const f = fl.find(f => f.l.num === n);
        assert.ok(f.l.directo && f.sec === '6');
        assert.equal(f.calc.como, 'directo al borne 50 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50');
        assert.equal(f.largo, 250);
      }
    }
  }
});

test('75287: 1101 y 1102 (grupo a mano «seccionadoras») con la ruta automática de la línea, nunca la dibujada', () => {
  const ins = C.leer(C.TRABAJOS['75287']), fl = lat(ins);
  assert.deepEqual(fl.map(f => [f.l.num, f.largo, f.sec, f.l.grupo_mano]), [['1101', 450, '2.5', 'seccionadoras'], ['1102', 500, '2.5', 'seccionadoras']]);
  assert.match(fl[0].calc.como, /^recorrido en la bandeja lateral izquierda 270 \+ sobrante 100 \+ agregado 75, redondeado a 50$/);
  // aunque el ruteo a mano tenga puntos dibujados, el largo es el de la línea (largo_mm)
  const ins2 = C.copia(ins);
  ins2.estacion8.ruteo_mano = Object.assign({}, ins2.estacion8.ruteo_mano, { cables: { [fl[0].l.clave]: { num: '1101', puntos: { X: [[0, 0], [5000, 0]] } } } });
  assert.equal(lat(ins2)[0].largo, 450);
});

test('66817: sin cables de una misma lateral, sin archivo de laterales; la principal con pendientes igual que antes', () => {
  const ins = C.leer(C.TRABAJOS['66817']);
  assert.equal(lat(ins).length, 0);
  assert.equal(W.clavesLaterales(ins).size, 0);
  assert.equal(principal(ins).filter(f => f.tipo === 'pendiente').length, ins.pendientes.length);
});

test('la lista principal no los lleva aunque se tilden los pendientes; los demás pendientes siguen', () => {
  const casos = { tpt_constructivo: [16, 11], tpt: [16, 11], '76884': [30, 17], pae_usuario: [30, 17], '75287': [10, 2], '66817': [9, 0] };
  for (const [t, [nPend, nLat]] of Object.entries(casos)) {
    const ins = C.leer(C.TRABAJOS[t]);
    assert.equal(ins.pendientes.length, nPend);
    const fp = principal(ins), fl = lat(ins), kl = W.clavesLaterales(ins);
    assert.equal(fl.length, nLat, `FALLA: ${t}`);
    assert.equal(fp.filter(f => f.tipo === 'pendiente').length, nPend - nLat, `FALLA: ${t}: pendientes en la principal`);
    const sinLado = s => String(s || '').replace(/ (ARRIBA|ABAJO)$/, '');
    const clave = f => [f.l.num, ...[sinLado(f.l.origen ?? f.l.a), sinLado(f.l.destino ?? f.l.b)].sort()].join('|');
    for (const f of fp) assert.ok(!kl.has(clave(f)), `FALLA: ${t}: ${f.l.num} está en la principal y en laterales`);
    // sin tildar los pendientes la principal no cambia (los pasos de la bandeja no son de una lateral)
    assert.equal(W.filas(ins, cfgDe(ins)).length, ins.pasos.reduce((s, p) => s + p.lineas.length, 0));
  }
});

test('sin E8 (o una E8 que falló) no hay laterales y los pendientes siguen como antes', () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo);
  for (const e8 of [undefined, { version: 0 }, { version: 8, laterales: [] }]) {
    const i2 = C.copia(ins);
    if (e8 === undefined) delete i2.estacion8; else i2.estacion8 = e8;
    assert.equal(lat(i2).length, 0);
    assert.equal(principal(i2).filter(f => f.tipo === 'pendiente').length, ins.pendientes.length);
  }
});

test('quitados a mano, cables repetidos, tramos de un mismo número y ediciones de la ventana', () => {
  const ins = C.copia(C.leer(C.TRABAJOS.tpt_constructivo));
  // quitado a mano del instructivo (pendiente con a / b): no va en laterales (tampoco está en la principal)
  const p1317 = ins.pendientes.find(p => p.num === '1317');
  ins.quitados = [Object.assign({ pendiente: true }, p1317)];
  ins.pendientes = ins.pendientes.filter(p => p !== p1317);
  assert.deepEqual(lat(ins).map(f => f.l.num).includes('1317'), false);
  assert.equal(lat(ins).length, 10);
  // la misma línea dos veces (las dos puntas en la misma lateral): una sola fila
  const L = ins.estacion8.laterales.find(L => L.lado === 'LD'), l1603 = L.pasos.flatMap(p => p.lineas).find(l => l.num === '1603');
  L.pasos[L.pasos.length - 1].lineas.push(C.copia(Object.assign({}, l1603, { origen: l1603.destino, destino: l1603.origen })));
  assert.equal(lat(ins).filter(f => f.l.num === '1603').length, 1);
  // ediciones a mano (ins.wpc, por la clave de la fila): largo, excluir, giro
  const f = lat(ins).find(f => f.l.num === '1605');
  ins.wpc = { largo: { [f.k]: 999 }, excluir: [lat(ins).find(f => f.l.num === '1607').k], giro: { [f.k]: '180|180' } };
  const g = lat(ins);
  assert.deepEqual([g.find(f => f.l.num === '1605').largo, g.find(f => f.l.num === '1605').giro, g.find(f => f.l.num === '1607').fuera], [999, '180|180', true]);
  // sin el lado de una punta (E8 vieja, sin lado_d): termos sin dato (0|0)
  const i3 = C.copia(C.leer(C.TRABAJOS.tpt_constructivo));
  i3.estacion8.laterales.forEach(L => L.pasos.forEach(p => p.lineas.forEach(l => { delete l.lado_d; })));
  assert.ok(lat(i3).every(f => f.giro === '0|0' && f.giroCalc.d === null));
  // sin recorrido (sin canaletas en la lateral): el valor fijo, a revisar
  i3.estacion8.laterales.forEach(L => L.pasos.forEach(p => p.lineas.forEach(l => { l.largo_mm = null; })));
  const s = lat(i3)[0];
  assert.deepEqual([s.largo, s.calc.falta, s.calc.como], [cfgDe(i3).largo_sin_ruta, true, 'sin recorrido en la bandeja lateral derecha: valor fijo']);
  // un número con dos tramos en la misma lateral (instructivo chico: 1105 de 12L1 5 a 6 y de 6 a 7): las dos filas
  const chico = C.cargarCaso('sin_producto');
  assert.deepEqual(lat(chico).map(f => `${f.l.num} ${f.l.origen} → ${f.l.destino}`), ['1101 12L1 1 → 12L1 2', '1105 12L1 5 → 12L1 6', '1105 12L1 6 → 12L1 7']);
});

test('los parámetros por niveles valen igual (sobrante, agregado y redondeo del producto o del trabajo; reemplazos)', () => {
  const ins = C.leer(C.TRABAJOS.tpt_constructivo), x = lineasMisma(ins).find(x => x.l.num === '1317').l;
  let f = W.laterales(ins, W.config(CONFIG, { producto: ins.producto, trabajo: { margen_bandeja: 130, agregado_bandeja: 0, redondeo: 1 } })).find(f => f.l.num === '1317');
  assert.deepEqual([f.largo, f.calc.como], [x.largo_mm + 130, `recorrido en la bandeja lateral derecha ${x.largo_mm} + sobrante 130, redondeado a 1`]);
  const b = C.copia(CONFIG); b.productos = { [ins.producto.codigo]: { agregado_bandeja: 25 } };
  f = W.laterales(ins, W.config(b, { producto: ins.producto, trabajo: { redondeo: 1 } })).find(f => f.l.num === '1317');
  assert.equal(f.largo, x.largo_mm + 100 + 25);
  // reemplazo: rojo 1 mm² → otro color y sección (solo en la lista)
  const b2 = C.copia(CONFIG); b2.reemplazos = [{ de: { color: 'Rojo', secc: 1 }, a: { color: 'Naranja', secc: 2.5 } }];
  f = W.laterales(ins, W.config(b2, { producto: ins.producto })).find(f => f.l.num === '1317');
  assert.deepEqual([f.sec, f.color, f.l.color], ['2.5', CONFIG.colores.Naranja, 'Rojo']);
});

test('.wpc de laterales: XML (49 columnas, CRLF, UserFilter -1), zip de una entrada y nombre «… - Laterales»', async () => {
  const casos = [['tpt_constructivo', '72715-1 - 72715 Rev 8 - Laterales', 11], ['76884', '76857-1 - ZPL-76884 Rev 1 - Laterales', 13], ['75287', '75286-1 - 75287 Rev 6 - Laterales', 2]];
  for (const [t, proyecto, n] of casos) {
    const ins = C.leer(C.TRABAJOS[t]), cfg = cfgDe(ins), fl = W.laterales(ins, cfg).filter(f => !f.fuera);
    assert.equal(W.nombreArchivo(ins.producto, '', 'x', 'Laterales'), proyecto);
    assert.equal(W.nombreArchivo(ins.producto, '.wpc', 'x', 'Laterales'), proyecto + '.wpc');
    assert.equal(W.nombreArchivo(ins.producto, '.wpc', 'x'), proyecto.replace(' - Laterales', '') + '.wpc', 'FALLA: el nombre del principal no cambia');
    const xml = W.wpcXml(fl, cfg, proyecto);
    assert.deepEqual({ ...X.atributosRaiz(xml) }, { Version: '1.0', ProjectName: proyecto, pdfFile: '', UserFilter: '-1' });
    const filas = X.filasXml(xml);
    assert.equal(filas.length, n);
    assert.ok(filas.every(f => f.length === 49), 'FALLA: 49 columnas');
    assert.deepEqual(filas.map(f => f[11]), fl.map(f => f.l.num));
    assert.deepEqual(filas.map(f => +f[6]), fl.map(f => f.largo));
    assert.ok(!/\r(?!\n)|(?<!\r)\n/.test(xml) && !xml.endsWith('\n'), 'FALLA: CRLF entre líneas y sin salto al final');
    assert.equal(xml, X.xmlDesdeCsv(W.csv(fl, cfg), proyecto), 'FALLA: el XML no es el que arma la máquina desde el CSV');
    const z = Buffer.from(await W.wpcZip(proyecto + '.wpc', xml));
    const r = X.leerWpc(z);
    assert.deepEqual([r.entradas, r.nombre, r.crcOk, r.xml], [1, proyecto + '.wpc', true, xml]);
  }
  // sin código de producto: el respaldo, con la parte
  assert.equal(W.nombreArchivo(null, '.wpc', 'Mi plano', 'Laterales'), 'Mi plano - WPC - Laterales.wpc');
});
