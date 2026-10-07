'use strict';
/* Lo que comparten generar_goldens.cjs y las pruebas *.test.cjs: qué instructivos, qué variantes y cómo se llaman los
   goldens (pruebas/bases/wpc/). */
const fs = require('node:fs'), path = require('node:path');
const V = require('./cargar_visor.cjs');

const PRUEBAS = path.join(V.RAIZ, 'pruebas');
const GOLDENS = path.join(PRUEBAS, 'bases', 'wpc');
const CASOS = path.join(__dirname, 'casos');
const WPC_REAL = path.join(PRUEBAS, 'fixtures', 'wpc', 'ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.wpc');

// instructivos completos congelados (volcar_bases_nuevas.py) y el del PAE con las marcas y salidas del usuario
const TRABAJOS = {
  '75287': path.join(PRUEBAS, 'bases', 'ins_75287.json'),
  '66817': path.join(PRUEBAS, 'bases', 'ins_66817.json'),
  '76884': path.join(PRUEBAS, 'bases', 'ins_76884.json'),
  'tpt': path.join(PRUEBAS, 'bases', 'ins_tpt.json'),
  'pae_usuario': path.join(PRUEBAS, 'fixtures', 'pae_usuario', 'instructivo.json'),
};
// variantes de la configuración: tal cual (wpc.json + lo que tenga ins.wpc.cfg: pendientes y otra en false) y con
// «Pendientes LI↔LI» y «Otra estación» tildados en la pantalla
const VARIANTES = { tal_cual: null, pend_otra: { pendientes: true, otra: true } };

const leer = p => JSON.parse(fs.readFileSync(p, 'utf8'));

// caso sintético: {"de": "chico.json", <claves que reemplaza>}; una clave en null se borra
function cargarCaso(nombre) {
  const c = leer(path.join(CASOS, nombre + '.json'));
  const ins = c.de ? leer(path.join(CASOS, c.de)) : {};
  for (const [k, v] of Object.entries(c)) {
    if (k === '_nota' || k === 'de') continue;
    if (v === null) delete ins[k]; else ins[k] = v;
  }
  delete ins._nota;
  return ins;
}
const casos = () => fs.readdirSync(CASOS).filter(f => f.endsWith('.json') && f !== 'chico.json').map(f => f.slice(0, -5)).sort();

// todo lo que tiene golden de la WPC: [nombre, instructivo]
function entradasWpc() {
  return [...Object.entries(TRABAJOS).map(([t, p]) => [t, leer(p)]), ...casos().map(c => ['caso_' + c, cargarCaso(c)])];
}
// todo lo que tiene golden del terminal: los trabajos y el instructivo chico
function entradasTerminal() {
  return [...Object.entries(TRABAJOS).map(([t, p]) => [t, leer(p)]), ['caso_chico', cargarCaso('sin_producto')]];
}

const archivoWpc = (nombre, variante, ext) => path.join(GOLDENS, `wpc_${nombre}_${variante}.${ext}`);
const archivoTerminal = nombre => path.join(GOLDENS, `terminal_${nombre}.json`);
const ARCHIVO_XML_76884 = path.join(GOLDENS, 'xml_76884_vs_real.json');

// el JSON de un golden: estable (claves en el orden en que se arman) y una fila por línea, para que el diff de git se lea
const texto = x => '{\n' + Object.entries(x).map(([k, v]) => ` ${JSON.stringify(k)}: ` + (Array.isArray(v) && v.length && v[0] && typeof v[0] === 'object'
  ? '[\n' + v.map(e => '  ' + JSON.stringify(e)).join(',\n') + '\n ]' : JSON.stringify(v))).join(',\n') + '\n}\n';

// primera diferencia entre dos CSV (para el mensaje de error)
function difCsv(a, b) {
  const fa = a.split('\r\n'), fb = b.split('\r\n');
  for (let i = 0; i < Math.max(fa.length, fb.length); i++) {
    if (fa[i] !== fb[i]) {
      const ca = (fa[i] || '').split(';'), cb = (fb[i] || '').split(';');
      const cols = [];
      for (let k = 0; k < Math.max(ca.length, cb.length); k++) if (ca[k] !== cb[k]) cols.push(`col ${k + 1}: ${JSON.stringify(ca[k])} (ahora) / ${JSON.stringify(cb[k])} (golden)`);
      return `fila ${i + 1} (cable ${ca[11] ?? cb[11]}): ${cols.join(' · ') || 'fin de línea distinto'} (${fa.length - 1} filas ahora, ${fb.length - 1} en el golden)`;
    }
  }
  return 'mismo texto, distinto en bytes (¿BOM o fin de línea?)';
}
// primera diferencia entre dos listas de objetos (filas o terminales)
function difLista(a, b, id = x => x.num) {
  if (a.length !== b.length) return `${a.length} elementos ahora, ${b.length} en el golden`;
  for (let i = 0; i < a.length; i++) {
    const sa = JSON.stringify(a[i]), sb = JSON.stringify(b[i]);
    if (sa !== sb) {
      const ks = [...new Set([...Object.keys(a[i] || {}), ...Object.keys(b[i] || {})])].filter(k => JSON.stringify((a[i] || {})[k]) !== JSON.stringify((b[i] || {})[k]));
      return `#${i + 1} (${id(a[i] || b[i])}): ${ks.map(k => `${k}: ${JSON.stringify((a[i] || {})[k])} (ahora) / ${JSON.stringify((b[i] || {})[k])} (golden)`).join(' · ')}`;
    }
  }
  return null;
}

module.exports = {
  ...V, PRUEBAS, GOLDENS, CASOS, WPC_REAL, TRABAJOS, VARIANTES, leer, cargarCaso, casos, entradasWpc, entradasTerminal,
  archivoWpc, archivoTerminal, ARCHIVO_XML_76884, texto, difCsv, difLista,
};
