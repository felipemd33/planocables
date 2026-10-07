'use strict';
/* Golden de la WPC: programa/web/wpc.js (con el núcleo nucleo/wpc_core.js desde la etapa 3) da el MISMO CSV, byte a
   byte, y las mismas filas que pruebas/bases/wpc/ en los 4 trabajos de regresión, el PAE del usuario y los casos de
   pruebas/js/casos/, con la configuración tal cual y con «Pendientes LI↔LI» y «Otra estación» tildados. La
   configuración es la copia fija pruebas/fixtures/wpc/wpc.json (la de programa/web la cambia el taller).
   Si un cambio a propósito cambia un resultado: node pruebas/js/generar_goldens.cjs y revisar el diff.
   (Etapa 3: los goldens se regeneraron UNA vez, por el reemplazo de 4 mm² para todos los productos; cambiaron solo las
   filas negras y rojas de 4 mm², color y sección: lo afirma wpc_core.test.cjs.) */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const C = require('./comun.cjs');

for (const [nombre, ins] of C.entradasWpc()) {
  for (const [variante, cfg] of Object.entries(C.VARIANTES)) {
    test(`WPC ${nombre} (${variante}): CSV byte a byte y filas iguales al golden`, async () => {
      const pCsv = C.archivoWpc(nombre, variante, 'csv'), pJson = C.archivoWpc(nombre, variante, 'json');
      assert.ok(fs.existsSync(pCsv) && fs.existsSync(pJson), `FALLA: falta el golden ${pCsv} (node pruebas/js/generar_goldens.cjs)`);
      const r = await C.correrWpc(ins, { cfg });
      const ahora = Buffer.from(r.csv, 'utf8'), golden = fs.readFileSync(pCsv);
      assert.ok(ahora.equals(golden), `FALLA: el CSV cambió: ${C.difCsv(r.csv, golden.toString('utf8'))}`);
      const g = C.leer(pJson);
      const dif = C.difLista(r.filas, g.filas, x => `${x.num} ${x.origen} → ${x.destino}`);
      assert.equal(dif, null, `FALLA: las filas cambiaron: ${dif}`);
      assert.equal(r.filas.filter(f => !f.fuera).length, g.filas_csv, 'FALLA: cambió la cantidad de filas del CSV');
    });
  }
}

test('WPC: correr dos veces da lo mismo y no toca el instructivo', async () => {
  const ins = C.leer(C.TRABAJOS.pae_usuario), antes = JSON.stringify(ins);
  const a = await C.correrWpc(ins, { cfg: { pendientes: true, otra: true } });
  const b = await C.correrWpc(ins, { cfg: { pendientes: true, otra: true } });
  assert.equal(a.csv, b.csv, 'FALLA: dos corridas dieron distinto CSV');
  assert.deepEqual(a.filas, b.filas, 'FALLA: dos corridas dieron distintas filas');
  assert.equal(JSON.stringify(ins), antes, 'FALLA: correrWpc cambió el instructivo de entrada');
  assert.equal(a.guardado, 0, 'FALLA: abrir la ventana WPC guardó el instructivo (no tiene que guardar sin una edición)');
});

test('WPC: el CSV tiene el formato de la planilla (BOM, 49 columnas, CRLF)', async () => {
  const r = await C.correrWpc(C.leer(C.TRABAJOS['76884']));
  assert.ok(r.csv.startsWith('﻿'), 'FALLA: falta el BOM');
  assert.ok(r.csv.endsWith('\r\n'), 'FALLA: la última fila no termina en CRLF');
  const filas = r.csv.slice(1).split('\r\n').slice(0, -1);
  assert.ok(filas.length > 0 && filas.every(l => l.split(';').length === 49), 'FALLA: alguna fila no tiene 49 columnas');
  assert.ok(!/\r(?!\n)|(?<!\r)\n/.test(r.csv), 'FALLA: hay saltos de línea que no son CRLF');
});
