'use strict';
/* Núcleo de la WPC (programa/web/nucleo/wpc_core.js y zip.js, etapa 3 del plan modular), sin la pantalla:
   - carga en Node sin DOM (require y un contexto vacío) y no usa document, window ni fetch;
   - la pantalla (wpc.js) y el núcleo dan lo mismo (filas y CSV) en todos los goldens;
   - precedencia de la configuración: todos los productos < producto (por código y, si no hay, por documento) < trabajo;
   - wpcXml del PAE del usuario, con la configuración de la etapa 0 (reemplazo solo PAE) y con la de hoy: respecto del
     .wpc real (pruebas/fixtures/wpc/, armado con la regla de largos del 2026-10-06) cambia solo el largo de los que salen
     a una lateral o a la puerta (regla del 2026-10-09), y con los largos del real es IDÉNTICO byte a byte; coincide con la
     emulación desde el CSV (wpc_xml.cjs);
   - wpcZip: lo abren el lector de wpc_xml.cjs y Python zipfile, la entrada se llama como el archivo y el CRC da;
   - nombreArchivo para 75287, PAE, TPT, 66817 y sin código; el 1161 en 850 / 1050 (regla del 2026-10-09);
   - el reemplazo de 4 mm² para todos los productos (decidido el 2026-10-07) cambia SOLO las filas negras y rojas de 4 mm²
     (color y sección) respecto de la configuración de la etapa 0;
   - programa/web/wpc.json (el que cambia el taller) es válido y el panel ⚙ Parámetros cubre todos sus parámetros, salvo
     los fijos (las acometidas de 75). */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), os = require('node:os');
const zlib = require('node:zlib'), cp = require('node:child_process');
const C = require('./comun.cjs');
const X = require('./wpc_xml.cjs');

const NUCLEO = path.join(C.RAIZ, 'programa', 'web', 'nucleo');
const W = require(path.join(NUCLEO, 'wpc_core.js'));
const Z = require(path.join(NUCLEO, 'zip.js'));
const CONFIG = C.leer(C.CONFIG_WPC);                                                   // la de hoy (copia fija)
const ETAPA0 = C.leer(path.join(C.PRUEBAS, 'fixtures', 'wpc', 'wpc_etapa0.json'));     // la de la etapa 0
const VIVA = path.join(C.RAIZ, 'programa', 'web', 'wpc.json');                         // la del taller
const PROYECTO = path.basename(C.WPC_REAL, '.wpc');

// el instructivo con la variante de la pantalla (Pendientes / Otra estación tildados) y su configuración
function preparar(ins, variante, base) {
  const D = C.copia(ins);
  if (variante) { D.wpc = D.wpc || {}; D.wpc.cfg = Object.assign(D.wpc.cfg || {}, variante); }
  return { D, cfg: W.config(base, { producto: D.producto, trabajo: (D.wpc || {}).cfg }) };
}
const normal = fs => C.copia(fs.map(C.normalizarFila).map(f => JSON.parse(JSON.stringify(f, (k, v) => (typeof v === 'number' && !Number.isFinite(v) ? String(v) : v)))));

test('wpc_core: carga en Node sin DOM (require y un contexto vacío) y no usa document, window ni fetch', () => {
  for (const f of ['config', 'filas', 'largo', 'lateralInfo', 'canaleta', 'csv', 'wpcXml', 'wpcZip', 'nombreArchivo']) assert.equal(typeof W[f], 'function', `FALLA: falta ${f}`);
  assert.equal(typeof Z.zipUno, 'function');
  for (const n of fs.readdirSync(NUCLEO).filter(n => n.endsWith('.js'))) {
    const src = fs.readFileSync(path.join(NUCLEO, n), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').replace(/ \/\/ .*$/gm, '');
    for (const re of [/\bdocument\./, /\bwindow\./, /\bfetch\(/, /\blocalStorage\b/, /(^|[^\w.])\$\(/, /\bD\.(pasos|wpc|producto)\b/, /\bS\.(res|job)\b/])
      assert.ok(!re.test(src), `FALLA: nucleo/${n} usa ${re} (el núcleo no puede tocar la pantalla ni los globales del visor)`);
  }
  // en un contexto vacío (sin require, module, window ni document): el mismo resultado que con require
  const ctx = vm.createContext({});
  for (const n of ['zip.js', 'wpc_core.js']) vm.runInContext(fs.readFileSync(path.join(NUCLEO, n), 'utf8'), ctx, { filename: n });
  const Wv = vm.runInContext('WpcCore', ctx);
  const ins = C.leer(C.TRABAJOS['76884']);
  const cv = Wv.config(CONFIG, { producto: ins.producto }), cr = W.config(CONFIG, { producto: ins.producto });
  assert.equal(Wv.csv(Wv.filas(ins, cv).filter(f => !f.fuera), cv), W.csv(W.filas(ins, cr).filter(f => !f.fuera), cr));
});

test('wpc_core: la pantalla (wpc.js) y el núcleo dan las mismas filas y el mismo CSV en todos los goldens', async () => {
  for (const [nombre, ins] of C.entradasWpc()) {
    for (const [variante, cfgV] of Object.entries(C.VARIANTES)) {
      const r = await C.correrWpc(ins, { cfg: cfgV });
      const { D, cfg } = preparar(ins, cfgV, CONFIG);
      const fs_ = W.filas(D, cfg);
      assert.equal(W.csv(fs_.filter(f => !f.fuera), cfg), r.csv, `FALLA: ${nombre} ${variante}: el CSV del núcleo no es el de la pantalla`);
      assert.deepEqual(normal(fs_), r.filas, `FALLA: ${nombre} ${variante}: las filas del núcleo no son las de la pantalla`);
    }
  }
});

test('wpc_core: precedencia de la configuración (todos < producto por código o documento < trabajo)', () => {
  const base = {
    _nota: 'x', margen_bandeja: 100, acometida: 75, redondeo: 50, pendientes: false,
    fuera: { seccion_desde: 35, campo_re: 'CAMPO' }, colores: { Negro: 'BK', Rojo: 'RD' }, reemplazos: [{ de: { color: 'Negro', secc: 4 }, a: { color: 'Violeta', secc: 2.5 } }],
    parametros: ['margen_bandeja', 'acometida', 'redondeo', 'pendientes', 'puerta', 'fuera.seccion_desde', 'fuera.campo_re', 'colores', 'reemplazos'].map(clave => ({ clave, tipo: 'numero' })),
    productos: {
      '75286-1': { margen_bandeja: 120, fuera: { seccion_desde: 25 }, colores: { Negro: 'VT' }, reemplazos: [] },
      'ZPL-76884': { acometida: 90, margen_bandeja: null, pendientes: true },
    },
  };
  const antes = JSON.stringify(base);
  // todos los productos
  let c = W.config(base, {});
  assert.deepEqual([c.margen_bandeja, c.acometida, c._de.margen_bandeja, c._de.puerta, c._producto.clave], [100, 75, 'global', 'defecto', null]);
  assert.ok(!('productos' in c) && !('parametros' in c) && !('_nota' in c), 'FALLA: productos, parametros y las notas no son parámetros');
  assert.equal(c.reemplazos.length, 1, 'FALLA: el reemplazo de todos los productos vale sin producto');
  // producto por código: lo declarado se toma entero (colores), lo de adentro de fuera se mezcla clave por clave
  c = W.config(base, { producto: { codigo: '75286-1', documento: '75287' } });
  assert.deepEqual([c.margen_bandeja, c.acometida, c.fuera, c.colores, c.reemplazos], [120, 75, { seccion_desde: 25, campo_re: 'CAMPO' }, { Negro: 'VT' }, []]);
  assert.deepEqual([c._de.margen_bandeja, c._de['fuera.seccion_desde'], c._de['fuera.campo_re'], c._de.colores, c._de.reemplazos], ['producto', 'producto', 'global', 'producto', 'producto']);
  assert.deepEqual({ ...c._producto }, { clave: '75286-1', por: 'codigo' });
  // alias por documento (sin entrada por código): ZPL-76884 sigue andando; null en un nivel = el de arriba
  c = W.config(base, { producto: { codigo: '76857-1', documento: 'ZPL-76884' } });
  assert.deepEqual([c.acometida, c.margen_bandeja, c.pendientes, c._de.acometida, c._de.margen_bandeja], [90, 100, true, 'producto', 'global']);
  assert.deepEqual({ ...c._producto }, { clave: 'ZPL-76884', por: 'documento' });
  // con entrada por código, el código manda (no se mezcla con la del documento)
  const b2 = C.copia(base); b2.productos['76857-1'] = { acometida: 95 };
  c = W.config(b2, { producto: { codigo: '76857-1', documento: 'ZPL-76884' } });
  assert.deepEqual([c.acometida, c.pendientes, c._producto.clave], [95, false, '76857-1']);
  // el trabajo manda sobre todo; '' o null = el de arriba; un texto queda como texto (la cuenta da NaN, como siempre)
  c = W.config(base, { producto: { codigo: '75286-1' }, trabajo: { margen_bandeja: '', acometida: '80', redondeo: 'abc', colores: { Rojo: 'X' }, fuera: { campo_re: 'ROTORK' }, pendientes: null } });
  assert.deepEqual([c.margen_bandeja, c.acometida, c.redondeo, c.colores, c.fuera, c.pendientes],
    [120, '80', 'abc', { Rojo: 'X' }, { seccion_desde: 25, campo_re: 'ROTORK' }, false]);
  assert.deepEqual([c._de.margen_bandeja, c._de.acometida, c._de['fuera.campo_re'], c._de['fuera.seccion_desde'], c._de.pendientes], ['producto', 'trabajo', 'trabajo', 'producto', 'global']);
  assert.equal(JSON.stringify(base), antes, 'FALLA: config() cambió la configuración de entrada');
  // la forma vieja de los reemplazos ({documento: [reglas]}, etapa 0) se sigue leyendo
  assert.equal(W.config(ETAPA0, { producto: { documento: 'ZPL-76884' } }).reemplazos.length, 2);
  assert.equal(W.config(ETAPA0, { producto: { codigo: '76857-1', documento: 'ZPL-76884' } }).reemplazos.length, 2);
  assert.equal(W.config(ETAPA0, { producto: { documento: '75287' } }).reemplazos.length, 0);
  assert.equal(W.config(ETAPA0, {}).reemplazos.length, 0);
  // la de hoy: para todos los productos; un producto lo puede apagar
  assert.equal(W.config(CONFIG, { producto: { documento: '75287' } }).reemplazos.length, 2);
  const b3 = C.copia(CONFIG); b3.productos = { '75286-1': { reemplazos: [] } };
  assert.equal(W.config(b3, { producto: { codigo: '75286-1' } }).reemplazos.length, 0);
  // filas() con la configuración cruda la resuelve con el producto y el trabajo del instructivo
  const ins = C.leer(C.TRABAJOS['75287']); ins.wpc = { cfg: { margen_bandeja: 130, pendientes: true } };
  const cfg = W.config(CONFIG, { producto: ins.producto, trabajo: ins.wpc.cfg });
  assert.equal(W.csv(W.filas(ins, CONFIG), cfg), W.csv(W.filas(ins, cfg), cfg));
  assert.ok(W.filas(ins, CONFIG).some(f => f.tipo === 'pendiente'));
});

// El .wpc real del PAE del usuario se armó el 2026-10-06, con la regla de largos de entonces (acometida_LI 150 y la puerta
// sin la curva). Con la regla del 2026-10-09 cambia SOLO la columna 7 (largo) de los cables que salen a una lateral o a
// la puerta; con los largos del .wpc real puestos a mano (ins.wpc.largo, como en la ventana) el XML es IDÉNTICO.
for (const [nombre, base] of [['de la etapa 0 (reemplazo solo PAE)', ETAPA0], ['de hoy (reemplazo para todos)', CONFIG]]) {
  test(`.wpc: wpcXml del PAE del usuario con la configuración ${nombre}: solo cambia el largo de los que salen a una lateral o a la puerta, y con los largos del .wpc real es IDÉNTICO byte a byte`, () => {
    const ins = C.leer(C.TRABAJOS.pae_usuario);
    const { D, cfg } = preparar(ins, null, base);
    const real = X.leerWpc(C.WPC_REAL), b = X.filasXml(real.xml);
    const fs0 = W.filas(D, cfg).filter(f => !f.fuera), a = X.filasXml(W.wpcXml(fs0, cfg, PROYECTO));
    assert.equal(a.length, b.length, 'FALLA: cambió la cantidad de filas');
    a.forEach((f, i) => {
      const ks = f.map((v, k) => (v !== b[i][k] ? k + 1 : 0)).filter(Boolean);
      if (!ks.length) return;
      assert.deepEqual(ks, [7], `FALLA: fila ${i + 1} (${fs0[i].l.num}): cambian las columnas ${ks}`);
      assert.match(fs0[i].calc.como, /curva a L[ID] /, `FALLA: fila ${i + 1} (${fs0[i].l.num}): cambia el largo y no sale a una lateral ni a la puerta: ${fs0[i].calc.como}`);
    });
    D.wpc = Object.assign({}, D.wpc); D.wpc.largo = Object.assign({}, D.wpc.largo);
    fs0.forEach((f, i) => { D.wpc.largo[f.k] = +b[i][6]; });
    const xml = W.wpcXml(W.filas(D, cfg).filter(f => !f.fuera), cfg, PROYECTO);
    if (!Buffer.from(xml, 'utf8').equals(real.bytes)) {
      const a = X.filasXml(xml), b = X.filasXml(real.xml), i = a.findIndex((f, k) => JSON.stringify(f) !== JSON.stringify(b[k]));
      assert.fail(`FALLA: el XML no es igual al del .wpc real (${a.length} / ${b.length} filas; primera distinta: ${i + 1})`);
    }
  });
}

test('.wpc: wpcXml da lo mismo que la emulación desde el CSV (wpc_xml.cjs) en todos los goldens; marcador y raíz por configuración', () => {
  for (const [nombre, ins] of C.entradasWpc()) {
    for (const [variante, cfgV] of Object.entries(C.VARIANTES)) {
      const { D, cfg } = preparar(ins, cfgV, CONFIG), fs_ = W.filas(D, cfg).filter(f => !f.fuera);
      assert.equal(W.wpcXml(fs_, cfg, 'P & <1>'), X.xmlDesdeCsv(W.csv(fs_, cfg), 'P & <1>'), `FALLA: ${nombre} ${variante}`);
    }
  }
  const ins = C.leer(C.TRABAJOS['76884']);
  const b = C.copia(CONFIG); b.marcador.modo = 'vacio'; b.archivo_wpc = { UserFilter: '0', pdfFile: 'a.pdf' };
  const { cfg } = preparar(ins, null, b), xml = W.wpcXml(W.filas(ins, cfg).filter(f => !f.fuera), cfg, 'X');
  assert.deepEqual({ ...X.atributosRaiz(xml) }, { Version: '1.0', ProjectName: 'X', pdfFile: 'a.pdf', UserFilter: '0' });
  assert.ok(X.filasXml(xml).every(f => f[20] === ''), 'FALLA: con el marcador «vacio» la columna 21 queda vacía');
  // sin marcador ni archivo_wpc (configuración de la etapa 0): por sección, UserFilter -1
  assert.equal(W.marcador('0,75', {}), X.MARCADOR.chico); assert.equal(W.marcador('2.50', {}), X.MARCADOR.grande);
  assert.equal(W.marcador('1.5', {}), ''); assert.equal(W.marcador('', {}), ''); assert.equal(W.marcador('10', {}), '');
  assert.equal(W.marcador('6', { marcador: { modo: 'seccion', tabla: [{ desde: 5, valor: 'G' }] } }), 'G');
});

test('.wpc: wpcZip arma un zip de una entrada que se llama como el archivo; lo abren wpc_xml.cjs y Python zipfile', async t => {
  const ins = C.leer(C.TRABAJOS['76884']), { cfg } = preparar(ins, null, CONFIG);
  const nom = W.nombreArchivo(ins.producto, '.wpc', 'x');
  assert.equal(nom, '76857-1 - ZPL-76884 Rev 1.wpc');
  const xml = W.wpcXml(W.filas(ins, cfg).filter(f => !f.fuera), cfg, W.nombreArchivo(ins.producto, '', 'x'));
  const z = Buffer.from(await W.wpcZip(nom, xml, new Date(2026, 9, 7, 12, 34, 56)));
  const r = X.leerWpc(z), datos = Buffer.from(xml, 'utf8');
  assert.deepEqual([r.entradas, r.nombre, r.metodo, r.crcOk, r.tam], [1, nom, 8, true, datos.length]);
  assert.equal(r.xml, xml);
  assert.equal(X.atributosRaiz(r.xml).ProjectName, '76857-1 - ZPL-76884 Rev 1');
  assert.equal(z.readUInt32LE(14), zlib.crc32(datos), 'FALLA: el CRC del encabezado no es el de zlib');
  assert.equal(Z.crc32(datos), zlib.crc32(datos));
  // encabezados como los .wpc reales: versión 20, sin banderas (nombre ASCII), deflate, sin extras ni comentario, atributos 0
  const real = fs.readFileSync(C.WPC_REAL), cenR = real.readUInt32LE(real.length - 22 + 16), cen = z.readUInt32LE(z.length - 22 + 16);
  assert.deepEqual([z.readUInt16LE(4), z.readUInt16LE(6), z.readUInt16LE(8), z.readUInt16LE(28)], [real.readUInt16LE(4), real.readUInt16LE(6), real.readUInt16LE(8), real.readUInt16LE(28)]);
  for (const o of [4, 6, 8, 10, 30, 32, 34, 36]) assert.equal(z.readUInt16LE(cen + o), real.readUInt16LE(cenR + o), `FALLA: directorio central, desplazamiento ${o}`);
  assert.equal(z.readUInt32LE(cen + 38), real.readUInt32LE(cenR + 38));
  // Python zipfile (otro lector, el de la biblioteca estándar)
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'wpczip_')), arch = path.join(tmp, nom);
  try {
    fs.writeFileSync(arch, z);
    const py = 'import zipfile, sys, json, hashlib\nz = zipfile.ZipFile(sys.argv[1])\ni = z.infolist()\n' +
      'print(json.dumps(dict(nombres=[x.filename for x in i], tam=[x.file_size for x in i], crc=[x.CRC for x in i], metodo=[x.compress_type for x in i],' +
      ' fecha=list(i[0].date_time), prueba=z.testzip(), sha1=hashlib.sha1(z.read(i[0])).hexdigest())))';
    const p = cp.spawnSync(process.env.PYTHON || 'python', ['-I', '-c', py, arch], { encoding: 'utf8' });
    if (p.error) return t.skip(`no hay Python (${p.error.message})`);
    assert.equal(p.status, 0, `FALLA: Python zipfile no abrió el .wpc: ${p.stderr}`);
    const j = JSON.parse(p.stdout);
    assert.deepEqual(j, { nombres: [nom], tam: [datos.length], crc: [zlib.crc32(datos)], metodo: [8], fecha: [2026, 10, 7, 12, 34, 56], prueba: null,
      sha1: require('node:crypto').createHash('sha1').update(datos).digest('hex') });
    // con acentos en el nombre: bandera UTF-8 y Python lo lee igual
    const n2 = 'Prueba ñandú.wpc', z2 = Buffer.from(await Z.zipUno(n2, datos));
    assert.equal(z2.readUInt16LE(6), 0x0800);
    const a2 = path.join(tmp, 'acentos.wpc'); fs.writeFileSync(a2, z2);
    const p2 = cp.spawnSync(process.env.PYTHON || 'python', ['-I', '-c', 'import zipfile, sys; sys.stdout.reconfigure(encoding="utf-8"); print(zipfile.ZipFile(sys.argv[1]).namelist()[0])', a2], { encoding: 'utf8' });
    assert.equal(p2.stdout.trim(), n2);
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
});

test('nombreArchivo: «<código> - <plano> Rev <rev>» en ASCII; sin código, «<plano> - WPC» como antes', () => {
  const p = n => C.leer(C.TRABAJOS[n]).producto;
  assert.equal(W.nombreArchivo(p('75287'), '.wpc', 'x'), '75286-1 - 75287 Rev 6.wpc');
  assert.equal(W.nombreArchivo(p('76884'), '.wpc', 'x'), '76857-1 - ZPL-76884 Rev 1.wpc');
  assert.equal(W.nombreArchivo(p('76884'), '.csv', 'x'), '76857-1 - ZPL-76884 Rev 1.csv');
  assert.equal(W.nombreArchivo(p('66817'), '', 'x'), '66817-1 - 74676 Rev 7');
  assert.equal(W.nombreArchivo(p('tpt'), '.wpc', 'x'), '72715-1 - 72715 Rev 8.wpc');
  // sin código (el PAE del usuario guardó solo documento y revisión): el nombre de antes
  assert.equal(W.nombreArchivo(p('pae_usuario'), '.wpc', PROYECTO), PROYECTO + ' - WPC.wpc');
  assert.equal(W.nombreArchivo(null, '.csv', '75287 DIAGRAMA ELECTRICO mSafe2AC - REV.6'), '75287 DIAGRAMA ELECTRICO mSafe2AC - REV.6 - WPC.csv');
  assert.equal(W.nombreArchivo({ codigo: '', documento: 'X' }, '.csv'), 'plano - WPC.csv');
  // ASCII y caracteres que no van en un nombre de archivo
  assert.equal(W.nombreArchivo({ codigo: '75286-1', funcional: { numero: '7528É/1', revision: '4(Á)' } }, '.wpc'), '75286-1 - 7528E-1 Rev 4(A).wpc');
  assert.equal(W.nombreArchivo({ codigo: '75286-1', funcional: { numero: '75287', revision: null } }, '.wpc'), '75286-1 - 75287.wpc');
  assert.equal(W.nombreArchivo({ codigo: '75286-1' }, '.wpc'), '75286-1.wpc');
  assert.equal(W.nombreArchivo({ codigo: '76857-1', documento: 'ZPL-76884', revision: '0A' }, '.wpc'), '76857-1 - ZPL-76884 Rev 0A.wpc');
  assert.ok(/^[\x20-\x7e]+$/.test(W.nombreArchivo({ codigo: '7528ñ-1', funcional: { numero: 'Ω²', revision: 'é' } }, '.wpc')));
});

test('1161 con el núcleo: 850 con la salida del taller (PAE regenerado) y 1050 con la salida elegida a mano (PAE del usuario)', () => {
  for (const [n, mm] of [['76884', 850], ['pae_usuario', 1050]]) {
    const ins = C.leer(C.TRABAJOS[n]), { cfg } = preparar(ins, null, CONFIG);
    const f = W.filas(ins, cfg).filter(x => x.l.num === '1161');
    assert.equal(f.length, 1);
    assert.equal(f[0].largo, mm, `FALLA: 1161 de ${n}: ${f[0].calc.como}`);
  }
});

test('reemplazo de 4 mm² para todos (2026-10-07): respecto de la etapa 0 cambian SOLO las filas negras y rojas de 4 mm² (color y sección)', () => {
  const es4 = f => ['negro', 'rojo'].includes(String(f.l.color ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')) && parseFloat(W.secNum(f.l)) === 4;
  const resumen = {};
  for (const [nombre, ins] of C.entradasWpc()) {
    for (const [variante, cfgV] of Object.entries(C.VARIANTES)) {
      // (B = la etapa 0 con SOLO los reemplazos de hoy: los largos de la regla del 2026-10-09 no entran en esta comparación)
      const A = preparar(ins, cfgV, ETAPA0), B = preparar(ins, cfgV, Object.assign(C.copia(ETAPA0), { reemplazos: C.copia(CONFIG.reemplazos) }));
      const fa = W.filas(A.D, A.cfg), fb = W.filas(B.D, B.cfg), na = normal(fa), nb = normal(fb);
      assert.equal(fa.length, fb.length);
      const cambian = [], esperadas = [];
      fa.forEach((f, i) => {
        if (es4(f) && !f.rg && !(ins.wpc && ins.wpc.color && ins.wpc.color[f.k])) esperadas.push(i);
        const ks = Object.keys(na[i]).filter(k => JSON.stringify(na[i][k]) !== JSON.stringify(nb[i][k]));
        if (ks.length) {
          cambian.push(i);
          assert.ok(ks.every(k => ['regla', 'sec', 'color'].includes(k)), `FALLA: ${nombre} ${variante} ${f.l.num}: cambia ${ks.join(', ')}`);
          assert.deepEqual([nb[i].sec, nb[i].color], ['2.5', f.l.color && /rojo/i.test(f.l.color) ? 'OG' : 'VT'], `FALLA: ${nombre} ${variante} ${f.l.num}`);
        }
      });
      assert.deepEqual(cambian, esperadas, `FALLA: ${nombre} ${variante}: cambian ${cambian.map(i => fa[i].l.num)} y se esperaban ${esperadas.map(i => fa[i].l.num)}`);
      // en el CSV, solo las columnas 9 (sección) y 10 (color) de esas filas
      const ca = W.csv(fa.filter(f => !f.fuera), A.cfg).split('\r\n'), cb = W.csv(fb.filter(f => !f.fuera), B.cfg).split('\r\n');
      ca.forEach((l, i) => {
        if (l === cb[i]) return;
        const x = l.split(';'), y = cb[i].split(';');
        assert.deepEqual(x.map((v, k) => (v !== y[k] ? k + 1 : 0)).filter(Boolean), [9, 10], `FALLA: ${nombre} ${variante}: fila ${i + 1} del CSV`);
      });
      resumen[nombre] = Math.max(resumen[nombre] || 0, cambian.length);
    }
  }
  // los PAE (sin 4 mm² en la rev 1) y los casos que ya tenían la regla del PAE no cambian
  for (const n of ['76884', 'pae_usuario', 'caso_reemplazo_pae', 'caso_ediciones']) assert.equal(resumen[n], 0, `FALLA: ${n} no tiene que cambiar`);
  for (const n of ['75287', '66817', 'tpt', 'caso_sin_producto', 'caso_producto_vacio', 'caso_reemplazo_otro_documento']) assert.ok(resumen[n] > 0, `FALLA: ${n} tiene filas de 4 mm²`);
});

test('programa/web/wpc.json (el del taller) es válido y el panel ⚙ Parámetros cubre todos sus parámetros', () => {
  const v = C.leer(VIVA), ps = W.parametros(v), claves = new Set(ps.map(p => p.clave));
  assert.ok(ps.length > 0, 'FALLA: wpc.json sin «parametros»');
  const TIPOS = ['numero', 'si_no', 'texto', 'regex', 'opcion', 'lista', 'colores', 'reemplazos', 'marcador', 'largos'];
  for (const p of ps) {
    assert.ok(TIPOS.includes(p.tipo), `FALLA: ${p.clave}: tipo ${p.tipo}`);
    assert.ok(p.etiqueta && p.grupo, `FALLA: ${p.clave} sin etiqueta o grupo`);
    if (p.tipo === 'regex') for (const nivel of [v, ...Object.values(v.productos || {})]) { const s = W.leer(nivel, p.clave); if (s) new RegExp(s, 'i'); }
  }
  // todo lo que no es nota ni sección (productos, parametros) está en el panel (entero o clave por clave), salvo los
  // FIJOS que el taller no edita (2026-10-09: las acometidas de 75 de los cables a las laterales)
  const FIJOS = ['acometida', 'acometida_LI'];
  const faltan = [];
  const recorrer = (o, ruta) => Object.entries(o).forEach(([k, x]) => {
    const r = ruta ? ruta + '.' + k : k;
    if ((!ruta && (k === 'productos' || k === 'parametros')) || k.startsWith('_') || claves.has(r) || FIJOS.includes(r)) return;
    if (x && typeof x === 'object' && !Array.isArray(x)) recorrer(x, r); else faltan.push(r);
  });
  recorrer(v, '');
  assert.deepEqual(faltan, [], 'FALLA: parámetros de wpc.json que no aparecen en el panel');
  for (const k of FIJOS) {
    assert.ok(!claves.has(k), `FALLA: ${k} es fijo y no va en el panel`);
    assert.equal(v[k], 75, `FALLA: ${k} tiene que ser 75 (fijo)`);
  }
  // los largos que usa la cuenta, todos en el panel (menos los fijos)
  for (const k of ['margen_bandeja', 'agregado_bandeja', 'curva_LI', 'curva_LD', 'puerta', 'margen_LI', 'extra_puerta', 'extra_LI',
    'extra_LD', 'agregado_LI', 'agregado_puerta', 'redondeo', 'largo_sin_ruta', 'largo_pendiente', 'pendientes', 'otra']) assert.ok(claves.has(k), `FALLA: ${k} no está en el panel`);
  const cfg = W.config(v, { producto: { codigo: '75286-1' } });
  assert.ok(Array.isArray(cfg.reemplazos) && cfg.colores && cfg.fijos && cfg.termos);
});
