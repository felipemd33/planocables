'use strict';
/* Tabla de ANTES y DESPUÉS de la lista WPC entre dos instructivos del mismo trabajo (ej. la E8 de antes y la de
   después de un cambio): qué cables cambian de largo y por qué (la columna «cómo» de la ventana WPC), en Markdown.
   No es una prueba: es para mostrarle al taller qué cambia en la lista de corte antes de regenerar los goldens.
   Uso: node pruebas/js/tabla_wpc.cjs <salida.md> <título> <nombre> <ins_antes.json> <ins_después.json> [<nombre> ...]
        [--nota <archivo.md>]   (texto que va arriba de la tabla: por qué cambia)
   Corre programa/web/wpc.js en Node como los goldens (cargar_visor.cjs, configuración fija pruebas/fixtures/wpc/wpc.json),
   con «Pendientes LI↔LI» y «Otra estación» tildados (pend_otra: así entran todas las filas). */
const fs = require('node:fs'), path = require('node:path');
const C = require('./comun.cjs');

const fmt = v => (v == null ? '—' : String(v));
const celda = s => String(s ?? '').replace(/\|/g, '\\|').replace(/\s+/g, ' ');

(async () => {
  const args = process.argv.slice(2), iN = args.indexOf('--nota');      // --nota <archivo.md>: texto que va arriba de la tabla
  const nota = iN >= 0 ? fs.readFileSync(args.splice(iN, 2)[1], 'utf8').trim() : '';
  const [salida, titulo, ...resto] = args;
  if (!salida || !resto.length || resto.length % 3) { console.error('uso: node pruebas/js/tabla_wpc.cjs <salida.md> <título> <nombre> <antes.json> <después.json> ...'); process.exit(2); }
  const pares = [];
  for (let i = 0; i < resto.length; i += 3) pares.push(resto.slice(i, i + 3));
  const out = [`# ${titulo}`, '', 'Lista WPC con «Pendientes LI↔LI» y «Otra estación» tildados (todas las filas), configuración fija de las pruebas',
    '(`pruebas/fixtures/wpc/wpc.json`). «Largo» = el que va al CSV, en mm. «Fuera» = no va al arnés (destildado).', ''];
  const resumen = [];
  for (const [nombre, a, b] of pares) {
    const r0 = await C.correrWpc(C.leer(a), { cfg: C.VARIANTES.pend_otra }), r1 = await C.correrWpc(C.leer(b), { cfg: C.VARIANTES.pend_otra });
    const m0 = new Map(r0.filas.map(f => [f.k, f])), m1 = new Map(r1.filas.map(f => [f.k, f]));
    const filas = [];
    for (const k of new Set([...m0.keys(), ...m1.keys()])) {
      const x = m0.get(k), y = m1.get(k);
      if (x && y && x.largo === y.largo && x.fuera === y.fuera && x.como === y.como) continue;
      filas.push({ x, y, f: y || x });
    }
    const sumaCsv = r => r.filas.filter(f => !f.fuera).reduce((s, f) => s + (+f.largo || 0), 0);
    const cambianLargo = filas.filter(({ x, y }) => x && y && x.largo !== y.largo);
    const delta = sumaCsv(r1) - sumaCsv(r0);
    resumen.push(`| ${nombre} | ${r0.filas.length} / ${r1.filas.length} | ${cambianLargo.length} | ${filas.length - cambianLargo.length} | ${(sumaCsv(r0) / 1000).toFixed(2)} → ${(sumaCsv(r1) / 1000).toFixed(2)} (${delta >= 0 ? '+' : ''}${(delta / 1000).toFixed(2)}) |`);
    const ruta = p => { const r = path.relative(C.RAIZ, path.resolve(p)); return (r.startsWith('..') || path.isAbsolute(r) ? path.basename(p) : r).replace(/\\/g, '/'); };
    out.push(`## ${nombre}`, '', `Antes: \`${ruta(a)}\` · después: \`${ruta(b)}\``, '');
    if (!filas.length) { out.push('Sin cambios.', ''); continue; }
    out.push(`${cambianLargo.length} cables cambian de largo; ${filas.length - cambianLargo.length} cambian solo el texto de «cómo» (o entran / salen).`, '',
      '| Cable | Origen → destino | Largo antes | Largo después | Diferencia | Cómo antes | Cómo después |', '|---|---|---:|---:|---:|---|---|');
    filas.sort((p, q) => String(p.f.num).localeCompare(String(q.f.num), 'es', { numeric: true }) || String(p.f.k).localeCompare(String(q.f.k)));
    for (const { x, y, f } of filas) {
      const d = x && y && x.largo != null && y.largo != null ? y.largo - x.largo : null;
      out.push(`| ${celda(f.num)} | ${celda(f.origen)} → ${celda(f.destino)} | ${fmt(x && x.largo)}${x && x.fuera ? ' (fuera)' : ''} | ${fmt(y && y.largo)}${y && y.fuera ? ' (fuera)' : ''} | ${d == null ? '—' : (d > 0 ? '+' : '') + d} | ${celda(x ? x.como : '(no estaba)')} | ${celda(y ? y.como : '(ya no está)')} |`);
    }
    out.push('');
  }
  out.splice(5, 0, ...(nota ? [nota, ''] : []), '| Trabajo | Filas antes / después | Cambian de largo | Cambia solo el texto | Metros en el CSV (antes → después) |', '|---|---|---:|---:|---|', ...resumen, '');
  fs.writeFileSync(salida, out.join('\n'), 'utf8');
  console.log(resumen.join('\n'));
  console.log(`-> ${salida}`);
})().catch(e => { console.error('FALLA:', e); process.exit(1); });
