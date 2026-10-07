'use strict';
/* XML del .wpc (especificación para la etapa 3): el CSV que hoy baja wpc.js para el PAE del usuario
   (pruebas/fixtures/pae_usuario), con las reglas de importación de la WPC (wpc_xml.cjs), da el XML IDÉNTICO byte a byte
   al de adentro del .wpc real (pruebas/fixtures/wpc/, sacado de G: con el OK del usuario). */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const C = require('./comun.cjs');
const X = require('./wpc_xml.cjs');

const PROYECTO = path.basename(C.WPC_REAL, '.wpc');

test('.wpc real: zip de una sola entrada, que se llama como el archivo, con CRC bien', () => {
  const r = X.leerWpc(C.WPC_REAL);
  assert.equal(r.entradas, 1, 'FALLA: el .wpc tiene más de una entrada');
  assert.equal(r.nombre, path.basename(C.WPC_REAL), 'FALLA: la entrada no se llama como el archivo');
  assert.equal(r.metodo, 8, 'FALLA: la entrada no está comprimida con deflate');
  assert.ok(r.crcOk, 'FALLA: el CRC o el tamaño de la entrada no coinciden');
  assert.deepEqual({ ...X.atributosRaiz(r.xml) }, { Version: '1.0', ProjectName: PROYECTO, pdfFile: '', UserFilter: '-1' });
  assert.ok(r.bytes[0] === 0x3C, 'FALLA: el XML real empieza con BOM o declaración');
});

test('.wpc: el XML emulado desde el CSV del PAE del usuario es IDÉNTICO al real, byte a byte', async () => {
  const real = X.leerWpc(C.WPC_REAL);
  const r = await C.correrWpc(C.leer(C.TRABAJOS.pae_usuario));
  const xml = X.xmlDesdeCsv(r.csv, PROYECTO);
  if (!Buffer.from(xml, 'utf8').equals(real.bytes)) {
    const a = X.filasXml(xml), b = X.filasXml(real.xml);
    const i = a.findIndex((f, k) => JSON.stringify(f) !== JSON.stringify(b[k]));
    const cols = i < 0 ? [] : a[i].map((v, k) => (v !== (b[i] || [])[k] ? `Col${k + 1}: ${v} / ${(b[i] || [])[k]}` : null)).filter(Boolean);
    assert.fail(`FALLA: el XML emulado no es igual al .wpc real (${a.length} / ${b.length} filas)` +
      (i >= 0 ? `; primera fila distinta: ${i + 1} (cable ${a[i][11]}): ${cols.join(' · ')}` : '; las filas son iguales: cambia el encabezado o el formato'));
  }
});

test('.wpc: el PAE regenerado (salida del taller) solo cambia los largos de las filas del golden', async () => {
  const g = C.leer(C.ARCHIVO_XML_76884);
  const r = await C.correrWpc(C.leer(C.TRABAJOS['76884']));
  const a = X.filasXml(X.xmlDesdeCsv(r.csv, PROYECTO)), b = X.filasXml(X.leerWpc(C.WPC_REAL).xml);
  assert.equal(a.length, b.length, 'FALLA: cambió la cantidad de filas');
  const dif = [];
  a.forEach((f, i) => {
    const cols = {};
    f.forEach((v, k) => { if (v !== b[i][k]) cols['Col' + (k + 1)] = [v, b[i][k]]; });
    if (Object.keys(cols).length) dif.push({ fila: i + 1, cable: f[11], cols });
  });
  assert.deepEqual(dif, g.filas, 'FALLA: cambiaron las diferencias entre el PAE regenerado y el .wpc real');
  assert.ok(dif.every(d => Object.keys(d.cols).join() === 'Col7'), 'FALLA: el PAE regenerado cambia algo más que el largo');
});

test('.wpc: reglas de importación sobre un CSV chico (sección, marcador, ceros, CRLF, sin salto final)', async () => {
  const r = await C.correrWpc(C.cargarCaso('reemplazo_pae'), { cfg: { pendientes: true, otra: true } });
  const xml = X.xmlDesdeCsv(r.csv, 'PRUEBA & <1>');
  const lineas = xml.split('\r\n');
  assert.equal(lineas[0], '<WPC Version="1.0" ProjectName="PRUEBA &amp; &lt;1&gt;" pdfFile="" UserFilter="-1">');
  assert.equal(lineas.at(-1), '</WPC>', 'FALLA: el XML tiene que terminar en </WPC> sin salto final');
  assert.ok(!/(?<!\r)\n/.test(xml) && !xml.startsWith('﻿'), 'FALLA: saltos que no son CRLF, o BOM');
  const filas = X.filasXml(xml), csv = X.filasCsv(r.csv);
  assert.equal(filas.length, csv.length);
  assert.ok(lineas.slice(1, -1).every(l => /^ {2}<Row\d+ (Col\d+="[^"]*" ){48}Col49="[^"]*" \/>$/.test(l)), 'FALLA: formato de fila');
  filas.forEach((f, i) => {
    const c = csv[i], sec = parseFloat(c[8].replace(',', '.'));
    assert.equal(f[8], sec.toFixed(2), 'FALLA: la columna 9 va con 2 decimales y punto');
    assert.equal(f[20], sec <= 1 ? X.MARCADOR.chico : X.MARCADOR.grande, `FALLA: marcador de la fila ${i + 1} (${c[8]} mm²)`);
    assert.equal(f[28], '0'); assert.equal(f[29], '0');
    for (const k of [7, 8, ...Array.from({ length: 27 }, (_, j) => 23 + j)]) if (k !== 9 && k !== 21 && c[k - 1] === '') assert.equal(f[k - 1], '0', `FALLA: columna ${k} vacía no pasó a 0`);
    for (const k of [10, 12, 20, 22]) assert.equal(f[k - 1], c[k - 1], `FALLA: la columna ${k} tiene que quedar tal cual`);
  });
  // la fila 2 es 1002 (negro 4 → violeta 2,5 por la regla del PAE): marcador grande
  assert.deepEqual([filas[1][6], filas[1][8], filas[1][9], filas[1][11], filas[1][20]], ['350', '2.50', 'VT', '1002', X.MARCADOR.grande]);
  assert.equal(X.marcadorPorSeccion('1,5'), '', 'FALLA: 1,5 mm² no tiene marcador definido (no hay en los datos)');
});

test('.wpc: el XML del golden se lee igual desde los bytes del archivo y desde la ruta', () => {
  const a = X.leerWpc(C.WPC_REAL), b = X.leerWpc(fs.readFileSync(C.WPC_REAL));
  assert.ok(a.bytes.equals(b.bytes));
});
