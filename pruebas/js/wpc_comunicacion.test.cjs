'use strict';
/* Largo total de los cables de comunicación por producto (2026-10-09, el taller): wpc.json → largos_comunicacion =
   [{cable, mm}], con cable = el número solo (todos sus tramos) o el tramo «número|origen|destino» (manda). Un cable de
   comunicación que está en la tabla lleva ese largo, sin redondear, y sigue fuera del arnés; los demás cables, igual.
   Sobre el 75287 (pruebas/bases/ins_75287.json): el 2132 tiene dos tramos (81XCM 1 y 81XCM 5 → LI) y el 2135 uno en la
   bandeja (81XCM 11 → LI) y un pendiente de la lateral (21PCB01 35 → 12XPS 7 ABAJO). */
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const C = require('./comun.cjs');
const W = require(path.join(C.RAIZ, 'programa', 'web', 'nucleo', 'wpc_core.js'));
const CONFIG = C.leer(C.CONFIG_WPC);

const ins75 = () => C.leer(C.TRABAJOS['75287']);
const filas = (ins, base, trabajo) => W.filas(ins, W.config(base, { producto: ins.producto, trabajo: Object.assign({ pendientes: true }, trabajo) }));
const conProducto = (ins, tabla) => { const b = C.copia(CONFIG); b.productos = { [ins.producto.codigo]: { largos_comunicacion: tabla } }; return b; };

test('wpc.json trae la tabla vacía en todos los productos: la lista no cambia', () => {
  assert.deepEqual(CONFIG.largos_comunicacion, []);
  assert.ok(W.parametros(CONFIG).some(p => p.clave === 'largos_comunicacion' && p.tipo === 'largos'), 'FALLA: falta el campo en el panel');
});

test('por producto: el número solo vale para todos sus tramos; el tramo manda; sigue fuera del arnés', () => {
  const ins = ins75();
  assert.equal(ins.producto.codigo, '75286-1');
  const antes = filas(ins, CONFIG);
  const t2135 = antes.filter(f => f.l.num === '2135');
  assert.equal(t2135.length, 2, 'FALLA: el 2135 del 75287 tiene un tramo en la bandeja y un pendiente');
  const kPend = t2135.find(f => f.tipo === 'pendiente').k;
  const desp = filas(ins, conProducto(ins, [{ cable: '2132', mm: 3100 }, { cable: '2135', mm: 1234 }, { cable: kPend, mm: 777 }, { cable: '1110', mm: 5 }, { cable: '', mm: null }]));
  for (const [i, f] of desp.entries()) {
    const a = antes[i];
    if (f.l.num === '2132') {
      assert.equal(f.largo, 3100); assert.equal(f.calc.como, 'largo total del cable de comunicación 3100 (cargado en el producto)');
    } else if (f.l.num === '2135') assert.equal(f.largo, f.k === kPend ? 777 : 1234, `FALLA: ${f.k}`);
    else assert.equal(f.largo, a.largo, `FALLA: ${f.k} no es de comunicación (o no está en la tabla) y cambió de largo`);
    assert.equal(f.fuera, a.fuera, `FALLA: ${f.k}: fuera del arnés no cambia`);
    if (/^comunicación/.test(a.motivo || '')) assert.ok(f.fuera, `FALLA: ${f.k}: el cable de comunicación sigue fuera del arnés`);
  }
  assert.equal(desp.filter(f => f.l.num === '2132').length, 2);
  // el CSV (lo que corta la WPC) no cambia: los de comunicación no van
  const cfgA = W.config(CONFIG, { producto: ins.producto, trabajo: { pendientes: true } });
  const cfgB = W.config(conProducto(ins, [{ cable: '2132', mm: 3100 }]), { producto: ins.producto, trabajo: { pendientes: true } });
  assert.equal(W.csv(desp.filter(f => !f.fuera), cfgB), W.csv(antes.filter(f => !f.fuera), cfgA));
});

test('este trabajo manda sobre el producto; sin el producto, el largo calculado de siempre', () => {
  const ins = ins75();
  const base = conProducto(ins, [{ cable: '2132', mm: 3100 }]);
  const f = filas(ins, base, { largos_comunicacion: [{ cable: '2132', mm: 2900 }] }).find(x => x.l.num === '2132');
  assert.equal(f.largo, 2900);
  assert.match(f.calc.como, /cargado en este trabajo/);
  const otro = C.copia(ins); otro.producto = Object.assign({}, otro.producto, { codigo: '99999-1', documento: 'X' });
  const g = filas(otro, base).find(x => x.l.num === '2132');
  assert.doesNotMatch(g.calc.como, /comunicación/, 'FALLA: la tabla de un producto no vale para otro');
});
