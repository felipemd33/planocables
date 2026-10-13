'use strict';
/* HAZ DE LA PLACA (estación 8, etapa E8-8, 2026-10-13, pedido del taller: «ir indicando puntos, poder hacer una curva y
   que al final el ruteo se pueda hacer algo automático, y al final se pueda ver como en la última foto»). La geometría
   del haz de un grupo de placa en la vista de la puerta y del ABANICO con que se abre al final: cada cable sale del haz
   y va solo a su pin, ordenados por la posición del pin para que no se crucen, con curvas suaves; los de la fila de más
   adentro pasan por el hueco entre dos pines de la fila de más afuera (sin taparla). Como la foto 9 del taller: el haz
   llega a la placa, se abre en abanico y cada cable lleva su terminal y la manga con el número.
   Núcleo sin DOM (como wpc_core.js): carga con <script> (global Haz) y con require (pruebas de node).
   Coordenadas: pt del topográfico, la y para arriba (como ins.estacion8; el SVG la invierte al dibujar).

   El haz guardado (programa/recorridos_e8.json, el tramo 'PUERTA' del grupo de placa): {vista: 'PUERTA', puntos: [[x, y],
   ...], curvas: [i, ...] (índices de 'puntos' cuya esquina va redondeada), desde: 'entrada' (arranca en la entrada a la
   puerta, que NO se guarda: si cambia la entrada o la bisagra, el haz la sigue)}. Un tramo de antes (E8-6 / E8-7: sin
   'desde' ni 'curvas') es el haz tal cual, de la punta más lejos de la placa a la más cerca.

   API
     polilinea(tramo, entrada, hacia) -> {pts, curvas: Set, desde}   los vértices del haz (con la entrada) y sus curvas
     suave(pts, curvas, R)            -> [[x, y]]   el haz con las esquinas curvas redondeadas (radio hasta R)
     paso(puntos)                     -> pt | null  la separación de los pines de una fila (mediana)
     ancho(n, paso)                   -> pt         el ancho dibujado del haz de n cables
     abanico(fin, dir, cables, pines, o) -> {ramas: {clave: {pts, t, fila, manga, terminal}}, orden, base, ext, lado,
                                         ya, paso, med, filas}
         fin = el final del haz; dir = el sentido del último tramo; cables = [{clave, num, fin: [x, y] (el pin o la
         franja), exacto}]; pines = todos los pines del aparato (las filas y sus huecos); o = {ancho}
     precintos(poly, cada)            -> [{p, t}]   dónde van los precintos (punto y tangente)
     largo(poly)                      -> pt
     cruces(ramas)                    -> [[clave, clave]]   pares de ramas que se cruzan (pruebas) */
const Haz = (() => {
  const VERSION = 1;
  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const N_CURVA = 10, N_RAMA = 22;

  /* ---- el haz ---- */
  // vértices del haz: con 'desde: entrada', la entrada y los puntos marcados (las curvas corren un lugar); un tramo de
  // antes, tal cual, con la punta más cerca de 'hacia' (los pines) al final
  function polilinea(tramo, entrada, hacia) {
    const P = ((tramo && tramo.puntos) || []).filter(p => p && p.length >= 2).map(p => [+p[0], +p[1]]);
    const cv = ((tramo && tramo.curvas) || []).filter(i => Number.isInteger(i) && i >= 0 && i < P.length);
    if (tramo && tramo.desde === 'entrada' && entrada)
      return { pts: [[+entrada[0], +entrada[1]], ...P], curvas: new Set(cv.map(i => i + 1)), desde: true };
    if (hacia && P.length > 1 && dist(P[0], hacia) < dist(P[P.length - 1], hacia)) {
      const n = P.length;
      return { pts: P.reverse(), curvas: new Set(cv.map(i => n - 1 - i)), desde: false };
    }
    return { pts: P, curvas: new Set(cv), desde: false };
  }
  // esquinas curvas: un arco (Bézier cuadrática con el vértice de control) de radio hasta R, que no pasa de la mitad del
  // tramo de al lado si la otra punta también es curva (si no, del 90 %)
  function suave(pts, curvas, R) {
    const n = pts.length;
    if (n < 3 || !curvas || !curvas.size) return pts.map(q => [q[0], q[1]]);
    const out = [[pts[0][0], pts[0][1]]];
    for (let i = 1; i < n - 1; i++) {
      const P = pts[i];
      if (!curvas.has(i)) { out.push([P[0], P[1]]); continue; }
      const A = pts[i - 1], B = pts[i + 1], la = dist(A, P), lb = dist(P, B);
      if (la < 1e-6 || lb < 1e-6) { out.push([P[0], P[1]]); continue; }
      const r = Math.min(R, (curvas.has(i - 1) ? 0.5 : 0.9) * la, (curvas.has(i + 1) ? 0.5 : 0.9) * lb);
      const q0 = [P[0] + (A[0] - P[0]) / la * r, P[1] + (A[1] - P[1]) / la * r], q1 = [P[0] + (B[0] - P[0]) / lb * r, P[1] + (B[1] - P[1]) / lb * r];
      for (let j = 0; j <= N_CURVA; j++) {
        const t = j / N_CURVA, a = (1 - t) * (1 - t), b = 2 * (1 - t) * t, c = t * t;
        out.push([a * q0[0] + b * P[0] + c * q1[0], a * q0[1] + b * P[1] + c * q1[1]]);
      }
    }
    out.push([pts[n - 1][0], pts[n - 1][1]]);
    return out;
  }
  function largo(poly) { let s = 0; for (let i = 1; i < (poly || []).length; i++) s += dist(poly[i - 1], poly[i]); return s; }
  // precintos (los de la foto): cada 'cada' a lo largo del haz y uno más cerca del final, antes del abanico
  function precintos(poly, cada) {
    const T = largo(poly), out = [];
    if (!(T > 0) || !(cada > 0)) return out;
    const marcas = [];
    if (T < 0.6 * cada) marcas.push(T / 2);
    else {
      for (let s = 0.5 * cada; s <= T - 0.6 * cada; s += cada) marcas.push(s);
      marcas.push(T - 0.25 * cada);
    }
    let i = 1, acc = 0;
    for (const s of marcas) {
      while (i < poly.length - 1 && acc + dist(poly[i - 1], poly[i]) < s) { acc += dist(poly[i - 1], poly[i]); i++; }
      const a = poly[i - 1], b = poly[i], l = dist(a, b) || 1, f = clamp((s - acc) / l, 0, 1);
      out.push({ p: [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f], t: [(b[0] - a[0]) / l, (b[1] - a[1]) / l] });
    }
    return out;
  }

  /* ---- los pines: filas y separación ---- */
  function paso(puntos) {
    const filas = new Map();
    for (const p of puntos || []) { const k = Math.round(p[1] * 2) / 2; if (!filas.has(k)) filas.set(k, []); filas.get(k).push(+p[0]); }
    const ds = [];
    for (const xs of filas.values()) { xs.sort((a, b) => a - b); for (let i = 1; i < xs.length; i++) if (xs[i] - xs[i - 1] > 0.05) ds.push(xs[i] - xs[i - 1]); }
    ds.sort((a, b) => a - b);
    return ds.length ? ds[Math.floor(ds.length / 2)] : null;
  }
  const ancho = (n, p) => clamp(0.5 * p * Math.sqrt(Math.max(1, n)), 1.2 * p, 2.6 * p);
  // medidas del dibujo, proporcionales a la separación de los pines (p): radio del pin, terminal, manga, cable
  const medidas = p => ({ rp: 0.3 * p, ferr: 0.7 * p, fs: 0.45 * p, wm: 0.62 * p, wc: 0.28 * p, sep: 0.15 * p });
  const largoManga = (num, p, med) => 0.6 * med.fs * String(num ?? '').length + 0.4 * p;
  // el hueco entre dos pines de la fila xs por donde pasa un cable que va a x (el de la derecha del pin que lo tapa);
  // x si no tapa ninguno
  function hueco(xs, x, p) {
    let k = -1, d = Infinity;
    xs.forEach((v, i) => { const e = Math.abs(v - x); if (e < d) { d = e; k = i; } });
    if (k < 0 || d > 0.42 * p) return x;
    const der = xs[k + 1];
    return der != null && der - xs[k] < 1.6 * p ? (xs[k] + der) / 2 : xs[k] + 0.5 * p;
  }

  /* ---- el abanico ---- */
  function abanico(fin, dir, cables, pines, o = {}) {
    const cs0 = (cables || []).filter(c => c && c.fin && c.fin.length >= 2);
    const exactos = cs0.filter(c => c.exacto).map(c => [+c.fin[0], +c.fin[1]]);
    const todos = [...(pines || []).map(q => [+q[0], +q[1]]), ...exactos];
    const p = o.paso || paso(todos) || 2.8, med = medidas(p), tolY = 0.35 * p;
    // filas de pines (de todo el aparato: los huecos se buscan también entre los pines sin cable)
    const filas = [];
    for (const q of todos) { let f = filas.find(x => Math.abs(x.y - q[1]) <= tolY); if (!f) filas.push(f = { y: q[1], xs: [] }); f.xs.push(q[0]); }
    filas.forEach(f => f.xs.sort((a, b) => a - b));
    const filaDe = q => filas.find(f => Math.abs(f.y - q[1]) <= tolY) || null;
    const enFila = cs0.filter(c => c.exacto && filaDe(c.fin));
    const ref = enFila.length ? enFila : cs0;
    const ym = ref.reduce((a, c) => a + c.fin[1], 0) / Math.max(1, ref.length);
    const E = [+fin[0], +fin[1]];
    const s = E[1] <= ym ? 1 : -1;                         // 1: los cables suben a los pines; -1: bajan
    // las filas entre el haz y el pin más lejano, de la más cercana a la más lejana
    const lejos = enFila.length ? Math.max(...enFila.map(c => s * c.fin[1])) : -Infinity;
    const fs = filas.filter(f => s * f.y <= lejos + tolY).sort((a, b) => s * a.y - s * b.y);
    const cerca = fs[0] || null;
    const Lmax = Math.max(largoManga('0000', p, med), ...cs0.map(c => largoManga(c.num, p, med)));
    const zona = med.rp + med.ferr + med.sep + Lmax + 0.5 * p;       // la acometida: terminal + manga, derecho al pin
    const yRef = cerca ? cerca.y : (s > 0 ? Math.min(...cs0.map(c => c.fin[1])) : Math.max(...cs0.map(c => c.fin[1])));
    const ya = yRef - s * zona;                           // de acá en adelante cada cable va derecho a su pin
    // cada cable: por dónde cruza la línea ya (t) y lo que sigue hasta el pin (cola)
    const cs = cs0.map(c => {
      const f = c.exacto ? filaDe(c.fin) : null, k = f ? fs.indexOf(f) : -1, F = [+c.fin[0], +c.fin[1]];
      let t = F[0], cola = [F], yEnd = ya;
      if (k > 0) {                       // fila de más adentro: pasa por el hueco de las filas de más afuera
        const xs = []; let x = F[0];
        for (let j = k - 1; j >= 0; j--) { x = hueco(fs[j].xs, x, p); xs[j] = x; }
        xs[k] = F[0]; t = xs[0]; cola = [];
        for (let j = 0; j < k; j++) {
          if (Math.abs(xs[j + 1] - xs[j]) < 1e-6) continue;
          const y1 = fs[j].y + s * (med.rp + 0.3 * p), y2 = y1 + s * 0.6 * p;
          cola.push([xs[j], y1], [xs[j + 1], y2]);
        }
        cola.push(F);
      } else if (!f && s * F[1] < s * ya + 0.5 * p) yEnd = F[1] - s * 0.5 * p;    // (sin pin: a la franja, más cerca)
      return { c, t, cola, yEnd, k, F };
    });
    // la base del abanico: el final del haz (si queda muy cerca de los pines, el haz sigue derecho hasta donde se puede
    // abrir: ext)
    const hmin = 2.5 * p, yTop = s > 0 ? Math.min(ya, ...cs.map(x => x.yEnd)) : Math.max(ya, ...cs.map(x => x.yEnd));
    let yb = E[1], ext = [], d = dir && (dir[0] || dir[1]) ? [dir[0] / Math.hypot(dir[0], dir[1]), dir[1] / Math.hypot(dir[0], dir[1])] : [0, s];
    if (s * (yTop - yb) < hmin) { yb = yTop - s * hmin; ext = [[E[0], yb]]; d = [0, Math.sign(yb - E[1]) || s]; }
    const Hc = Math.abs(ya - yb);
    // los cables salen del haz en el sentido del haz y terminan derechos hacia los pines: una curva comun a todos (B) que
    // no cambia el orden (a la misma altura, todos en el orden de sus pines: no se cruzan)
    const sy = s * d[1];
    const m0 = Math.abs(d[0]) < 1e-6 ? 0 : clamp(sy > 0.35 ? d[0] / sy : Math.sign(d[0]) * 2.7, -2.7, 2.7);
    const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
    const ord = cs.slice().sort((a, b) => (a.t - b.t) || (s * a.F[1] - s * b.F[1]) || cmp(String(a.c.clave), String(b.c.clave)));
    const n = ord.length, w = o.ancho || ancho(n, p), gl = n > 1 ? Math.min(w / n, 0.6 * p) : 0, x0 = E[0] - gl * (n - 1) / 2;
    const ramas = {};
    ord.forEach((x, i) => {
      const L = x0 + i * gl, h = x.yEnd - yb, pts = [];
      for (let j = 0; j <= N_RAMA; j++) {
        const u = j / N_RAMA, S = u * u * (3 - 2 * u), B = m0 * Hc * u * (1 - u) * (1 - u);
        pts.push([L + (x.t - L) * S + B, yb + h * u]);
      }
      for (const q of x.cola) { const z = pts[pts.length - 1]; if (dist(z, q) > 1e-6) pts.push([q[0], q[1]]); }
      const F = x.F, lm = largoManga(x.c.num, p, med);
      const ini = [F[0], F[1] - s * med.rp], term = [F[0], F[1] - s * (med.rp + med.ferr)];
      ramas[x.c.clave] = { pts, t: x.t, fila: x.k, base: [L, yb],
        terminal: { a: ini, b: term },
        manga: { p: [F[0], F[1] - s * (med.rp + med.ferr + med.sep + lm / 2)], largo: lm, ancho: med.wm } };
    });
    return { ramas, orden: ord.map(x => x.c.clave), base: [E[0], yb], ext, lado: s, ya, paso: p, med, ancho: w,
      filas: fs.map(f => ({ y: f.y, xs: f.xs.slice() })) };
  }

  /* ---- pruebas: ¿se cruzan dos ramas? (sin contar las que terminan en el mismo pin) ---- */
  function segCruzan(a, b, c, d) {
    const o = (p, q, r) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
    const d1 = o(c, d, a), d2 = o(c, d, b), d3 = o(a, b, c), d4 = o(a, b, d), e = 1e-9;
    return ((d1 > e && d2 < -e) || (d1 < -e && d2 > e)) && ((d3 > e && d4 < -e) || (d3 < -e && d4 > e));
  }
  function cruces(ramas) {
    const ks = Object.keys(ramas || {}), out = [];
    for (let i = 0; i < ks.length; i++) for (let j = i + 1; j < ks.length; j++) {
      const A = ramas[ks[i]].pts, B = ramas[ks[j]].pts;
      if (dist(A[A.length - 1], B[B.length - 1]) < 1e-6) continue;          // (dos cables al mismo pin)
      let x = false;
      for (let a = 1; a < A.length && !x; a++) for (let b = 1; b < B.length && !x; b++) x = segCruzan(A[a - 1], A[a], B[b - 1], B[b]);
      if (x) out.push([ks[i], ks[j]]);
    }
    return out;
  }

  return { VERSION, polilinea, suave, largo, precintos, paso, ancho, medidas, largoManga, hueco, abanico, cruces };
})();
if (typeof module === 'object' && module && module.exports) module.exports = Haz;
