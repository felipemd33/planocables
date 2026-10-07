'use strict';
/* Carga los .js de la web (programa/web/wpc.js, instructivo.js y estacion8.js) en Node, SIN MODIFICARLOS: cada uno corre
   tal cual dentro de node:vm, con un DOM falso mínimo (document, $, esc, S, api, fetch que lee wpc.json / terminales.json
   del disco). Es la base de las pruebas de la WPC y del terminal (etapa 0 del plan modular).

   API:
     correrWpc(ins, {cfg, wpcJson, web})  -> {filas, csv}   filas = las de Wpc.filas() normalizadas; csv = el texto que
                                                             baja el botón «⭳ Exportar CSV» (solo las que no quedan fuera)
     terminales(ins, {web})               -> [{g, i, num, origen, destino, o, d}]   terminal() de instructivo.js por línea
     terminalesE8(ins, {web})             -> [{lateral, g, i, clave, num, origen, destino, o, d}]   el de estacion8.js
     normalizarFila(f)                    -> la fila de wpc.js como JSON simple
   ins no se toca: se trabaja sobre una copia. cfg = lo que el taller cambia en la pantalla (ins.wpc.cfg), se suma encima.
   wpcJson = otro wpc.json en lugar del del disco (para pruebas). web = otra carpeta programa/web (para comparar); la
   variable de entorno PLANOCABLES_WEB cambia la carpeta por defecto (para correr los goldens contra otra copia).
   CONFIGURACIÓN DE LA WPC (desde la etapa 3): la de programa/web/wpc.json la cambia el taller desde la pantalla (panel
   ⚙ Parámetros), así que las pruebas usan la copia fija pruebas/fixtures/wpc/wpc.json (como el catálogo de productos con
   PLANOCABLES_PRODUCTOS): los goldens no fallan porque el taller cambie un parámetro. Con otra carpeta web (op.web o
   PLANOCABLES_WEB) se usa el wpc.json de esa carpeta. El núcleo (programa/web/nucleo/*.js) se carga antes de wpc.js. */
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');

const RAIZ = path.resolve(__dirname, '..', '..');
const WEB = process.env.PLANOCABLES_WEB ? path.resolve(process.env.PLANOCABLES_WEB) : path.join(RAIZ, 'programa', 'web');
const CONFIG_WPC = path.join(RAIZ, 'pruebas', 'fixtures', 'wpc', 'wpc.json');     // la configuración fija de las pruebas
const wpcJsonDe = web => (path.resolve(web) === path.join(RAIZ, 'programa', 'web') && !process.env.PLANOCABLES_WEB ? CONFIG_WPC : path.join(web, 'wpc.json'));

const copia = x => JSON.parse(JSON.stringify(x));
// números que no son finitos (NaN de un parámetro con texto) quedan como texto, para que el JSON no los pierda
const json = x => JSON.parse(JSON.stringify(x, (k, v) => (typeof v === 'number' && !Number.isFinite(v) ? String(v) : v)));
const esperar = () => new Promise(r => setImmediate(r));     // deja correr las promesas de carga (fetch de los .json)

// ---- DOM falso: cada selector es un elemento que guarda lo que se le asigna (innerHTML, hidden...) y sus eventos
function elemento(nombre, todos) {
  const props = { hidden: false, dataset: {}, style: {}, innerHTML: '', textContent: '', value: '' };
  const eventos = {};
  const hijos = new Map();
  const nada = () => {};
  const metodos = {
    addEventListener: (t, fn) => { (eventos[t] = eventos[t] || []).push(fn); },
    removeEventListener: nada, appendChild: x => x, remove: nada, click: nada, focus: nada, blur: nada,
    setAttribute: nada, removeAttribute: nada, getAttribute: () => null, setPointerCapture: nada, scrollIntoView: nada,
    querySelector: s => { if (!hijos.has(s)) hijos.set(s, elemento(nombre + ' ' + s, todos)); return hijos.get(s); },
    querySelectorAll: () => [], closest: () => null, matches: () => false, contains: () => false,
    getBoundingClientRect: () => ({ x: 0, y: 0, left: 0, top: 0, width: 0, height: 0, right: 0, bottom: 0 }),
    classList: { add: nada, remove: nada, toggle: nada, contains: () => false },
    _eventos: eventos, _nombre: nombre,
  };
  const el = new Proxy(props, {
    get: (t, k) => (k in metodos ? metodos[k] : k in t ? t[k] : undefined),
    set: (t, k, v) => { t[k] = v; return true; },
  });
  if (todos) todos.set(nombre, el);
  return el;
}

function contexto(extra) {
  const todos = new Map();
  const $ = s => todos.get(s) || elemento(s, todos);
  const document = {
    querySelector: $, querySelectorAll: () => [], getElementById: id => $('#' + id),
    createElement: t => elemento('<' + t + '>'), createElementNS: (ns, t) => elemento('<' + t + '>'),
    addEventListener: () => {}, removeEventListener: () => {}, body: elemento('body'), documentElement: elemento('html'),
  };
  const ctx = {
    console, setTimeout, clearTimeout, setInterval, clearInterval, URL, Blob,
    document, $, window: {}, navigator: {},
    requestAnimationFrame: () => 0, cancelAnimationFrame: () => {}, performance: { now: () => 0 },
    // los mismos que app.js (solo los usa el dibujo, no lo que se compara)
    esc: s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])),
    norm: s => String(s ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\./g, ','),
    fmtSec: s => (s === '' || s == null) ? '' : String(s).replace('.', ',') + ' mm²',
    swatch: () => '', toast: () => {}, LINE: {}, COLORS: {},
    S: { job: null, res: { nombre: 'prueba.pdf' } },
    _elementos: todos,
    ...extra,
  };
  vm.createContext(ctx);
  return ctx;
}

// fetch('/static/<archivo>.json') lee el archivo de la carpeta web (o el que se pase en 'propios'). GET /api/config/wpc
// (la configuración de la WPC, desde la etapa 3) es el mismo wpc.json
const fetchDe = (web, propios = {}) => async url => {
  const u = String(url).split('?')[0], nombre = u === '/api/config/wpc' ? 'wpc.json' : path.basename(u);
  const arch = nombre === 'wpc.json' ? wpcJsonDe(web) : path.join(web, nombre);
  const datos = nombre in propios ? copia(propios[nombre]) : JSON.parse(fs.readFileSync(arch, 'utf8'));
  return { ok: true, json: async () => datos, headers: { get: k => (String(k).toLowerCase() === 'content-type' ? 'application/json' : null) } };
};

function correr(ctx, web, archivo) {
  vm.runInContext(fs.readFileSync(path.join(web, archivo), 'utf8'), ctx, { filename: archivo });
}
// el núcleo de la web (programa/web/nucleo/, desde la etapa 3), en el orden de index.html. Una copia vieja de la web
// (PLANOCABLES_WEB) puede no tenerlo
const NUCLEO = ['zip.js', 'wpc_core.js'];
function correrNucleo(ctx, web) {
  for (const n of NUCLEO) if (fs.existsSync(path.join(web, 'nucleo', n))) correr(ctx, web, 'nucleo/' + n);
}

// ---- WPC (wpc.js): las filas y el CSV, igual que en la pantalla
function normalizarFila(f, i) {
  const l = f.l;
  return {
    n: i + 1, tipo: f.tipo, grupo: f.grupo, k: f.k, num: l.num,
    origen: l.origen ?? l.a, destino: l.destino ?? l.b, color_plano: l.color, secc_plano: l.secc,
    regla: f.rg ? { de: f.rg.de, a: f.rg.a } : null,
    sec: f.sec, color: f.color, largo: f.largo, calculado: f.calc.mm, como: f.calc.como, falta: !!f.calc.falta,
    giro: f.giro, giro_calc: f.giroCalc.v, lado_o: f.giroCalc.o, lado_d: f.giroCalc.d, giro_como: f.giroCalc.como,
    motivo: f.motivo, fuera: f.fuera,
  };
}

async function correrWpc(ins, op = {}) {
  const web = op.web || WEB;
  const ctx = contexto({ fetch: fetchDe(web, op.wpcJson ? { 'wpc.json': op.wpcJson } : {}) });
  correrNucleo(ctx, web);
  correr(ctx, web, 'wpc.js');
  const Wpc = vm.runInContext('Wpc', ctx);
  const D = copia(ins);
  if (op.cfg) { D.wpc = D.wpc || {}; D.wpc.cfg = Object.assign(D.wpc.cfg || {}, op.cfg); }
  let guardado = 0;
  await Wpc.abrir(D, () => { guardado++; });           // arma la ventana (DOM falso) y deja el instructivo cargado
  const todas = Wpc.filas();
  const csv = Wpc.csv(todas.filter(f => !f.fuera));     // lo mismo que el botón «⭳ Exportar CSV»
  return { filas: json(todas.map(normalizarFila)), csv, guardado };
}

// ---- terminal() de instructivo.js: pino o doble y la pollera de cada punta de las líneas de la bandeja (E6)
let nJob = 0;
async function terminales(ins, op = {}) {
  const web = op.web || WEB;
  const D = copia(ins);
  const job = 'prueba' + (++nJob);
  const api = async p => (String(p).endsWith('/estado') ? { hay_instructivo: true, estado: 'terminado' } : D);
  const ctx = contexto({ fetch: fetchDe(web), api });
  ctx.S.job = job;
  correr(ctx, web, 'instructivo.js');
  await esperar();
  const Ins = vm.runInContext('Ins', ctx);
  const cargado = await Ins.load();
  if (cargado !== D) throw new Error('instructivo.js no tomó el instructivo de prueba');
  const out = [];
  D.pasos.forEach((p, g) => p.lineas.forEach((l, i) => {
    out.push({ g, i, num: l.num, origen: l.origen, destino: l.destino, o: Ins.terminal(l, 'o'), d: Ins.terminal(l, 'd') });
  }));
  return json(out);
}

// ---- terminal() de estacion8.js (bandeja lateral): no se exporta, así que se lee de la tarjeta de cada cable.
// Ins.termChip(t) devuelve una marca ⟦Tn⟧ y guarda t; en el HTML de #e8Lat cada tarjeta (data-g, data-i) tiene la del
// origen y, si hay terminal de destino, la del destino.
async function terminalesE8(ins, op = {}) {
  const web = op.web || WEB;
  const D = copia(ins);
  const vistos = [];
  const Ins = {
    load: async () => D, job: 'prueba', dirty: () => {}, reset: () => {},
    termChip: t => { vistos.push(t); return `⟦T${vistos.length - 1}⟧`; },
    ferrule: () => '', mark: () => '', label: () => '', termLen: () => 1, LC: () => '#000', secTxt: () => '', secCorto: () => '',
  };
  const ctx = contexto({ fetch: fetchDe(web), api: async () => ({}), Ins });
  correr(ctx, web, 'estacion8.js');
  await esperar();
  const E8 = vm.runInContext('E8', ctx);
  const lats = ((D.estacion8 || {}).laterales || []);
  const out = [];
  for (let v = 0; v < lats.length; v++) {
    vistos.length = 0;
    if (v === 0) await E8.open();
    else ctx._elementos.get('#e8Vistas')._eventos.click.forEach(fn => fn({ target: { closest: () => ({ dataset: { v: String(v) } }) } }));
    const html = ctx._elementos.get('#e8Lat').innerHTML;
    const re = /<div class="cab [^"]*" data-g="(\d+)" data-i="(\d+)"[\s\S]*?<div class="cab-term small">⟦T(\d+)⟧(?: <span class="arr">→<\/span> ⟦T(\d+)⟧)?/g;
    const por = new Map();
    for (const m of html.matchAll(re)) por.set(`${m[1]}|${m[2]}`, { o: vistos[+m[3]], d: m[4] != null ? vistos[+m[4]] : null });
    lats[v].pasos.forEach((p, g) => p.lineas.forEach((l, i) => {
      const t = por.get(`${g}|${i}`);
      if (!t) throw new Error(`estacion8.js: no se encontró la tarjeta del cable ${l.num} (lateral ${v}, ${g}/${i})`);
      out.push({ lateral: v, g, i, clave: l.clave, num: l.num, origen: l.origen, destino: l.destino, o: t.o, d: t.d });
    }));
  }
  return json(out);
}

module.exports = { RAIZ, WEB, CONFIG_WPC, correrWpc, terminales, terminalesE8, normalizarFila, copia };
