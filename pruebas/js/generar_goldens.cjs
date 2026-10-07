'use strict';
/* Arma los goldens de la WPC, del terminal y del XML del .wpc con el código de HOY (programa/web/wpc.js,
   instructivo.js y estacion8.js sin modificar, corridos en Node).
   Uso: node pruebas/js/generar_goldens.cjs [<carpeta de salida>]     (por defecto pruebas/bases/wpc)
   Solo se corre a propósito: si un cambio del programa cambia un resultado y está bien, se regenera y se revisa el diff.
   Escribe:
     wpc_<nombre>_<variante>.csv   el CSV que baja «⭳ Exportar CSV», byte a byte (BOM, ';', CRLF)
     wpc_<nombre>_<variante>.json  las filas de la ventana WPC (también las que quedan fuera del arnés, con el motivo)
     terminal_<nombre>.json        terminal() de las dos puntas: e6 (instructivo.js) y e8 (estacion8.js, bandeja lateral)
     xml_76884_vs_real.json        qué cambia entre el XML emulado del PAE regenerado (salida del taller) y el .wpc real
   <nombre> = 75287, 66817, 76884, tpt, pae_usuario o caso_<archivo de pruebas/js/casos>; <variante> = tal_cual, pend_otra. */
const fs = require('node:fs'), path = require('node:path');
const C = require('./comun.cjs');
const X = require('./wpc_xml.cjs');

(async () => {
  const t0 = Date.now();
  const dir = path.resolve(process.argv[2] || C.GOLDENS);
  fs.mkdirSync(dir, { recursive: true });
  const en = p => path.join(dir, path.basename(p));
  let n = 0;
  const resumen = [];
  for (const [nombre, ins] of C.entradasWpc()) {
    for (const [variante, cfg] of Object.entries(C.VARIANTES)) {
      const r = await C.correrWpc(ins, { cfg });
      fs.writeFileSync(en(C.archivoWpc(nombre, variante, 'csv')), r.csv, 'utf8');
      const enCsv = r.filas.filter(f => !f.fuera).length;
      fs.writeFileSync(en(C.archivoWpc(nombre, variante, 'json')), C.texto({ variante, cfg, filas_total: r.filas.length, filas_csv: enCsv, filas: r.filas }), 'utf8');
      resumen.push(`${nombre} ${variante}: ${r.filas.length} filas, ${enCsv} en el CSV (${Buffer.byteLength(r.csv, 'utf8')} bytes)`);
      n += 2;
    }
  }
  for (const [nombre, ins] of C.entradasTerminal()) {
    const e6 = await C.terminales(ins), e8 = await C.terminalesE8(ins);
    fs.writeFileSync(en(C.archivoTerminal(nombre)), C.texto({ e6, e8 }), 'utf8');
    const dobles = e6.filter(x => (x.o && x.o.tipo === 'doble') || (x.d && x.d.tipo === 'doble')).length;
    resumen.push(`terminal ${nombre}: ${e6.length} líneas E6 (${dobles} con terminal doble), ${e8.length} de la bandeja lateral (E8)`);
    n++;
  }
  // XML del PAE regenerado (salida a LI / LD por la regla del taller) contra el .wpc real (salidas elegidas a mano)
  const real = X.leerWpc(C.WPC_REAL), proyecto = path.basename(C.WPC_REAL, '.wpc');
  const r76 = await C.correrWpc(C.leer(C.TRABAJOS['76884']));
  const a = X.filasXml(X.xmlDesdeCsv(r76.csv, proyecto)), b = X.filasXml(real.xml);
  const filas = [];
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const cols = {};
    for (let k = 0; k < 49; k++) if ((a[i] || [])[k] !== (b[i] || [])[k]) cols['Col' + (k + 1)] = [(a[i] || [])[k] ?? null, (b[i] || [])[k] ?? null];
    if (Object.keys(cols).length) filas.push({ fila: i + 1, cable: (a[i] || b[i])[11], cols });
  }
  fs.writeFileSync(en(C.ARCHIVO_XML_76884), C.texto({
    nota: 'Filas del XML emulado desde el CSV del PAE regenerado (ins_76884.json, salida a LI / LD por la regla del taller) que no coinciden con el .wpc real (hecho desde el trabajo del usuario, con las salidas elegidas a mano). Cada columna: [regenerado, real].',
    filas_regenerado: a.length, filas_real: b.length, distintas: filas.length, filas,
  }), 'utf8');
  resumen.push(`xml 76884 regenerado contra el .wpc real: ${filas.length} filas distintas de ${b.length}`);
  n++;
  console.log(resumen.join('\n'));
  console.log(`${n} archivos en ${dir} (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
})().catch(e => { console.error('FALLA:', e); process.exit(1); });
