'use strict';
/* Pestaña 📽 Proyector: proyecta sobre la bandeja REAL las canaletas y el recorrido del cable que se está cableando.
   Se abre desde el instructivo (📽 Proyector) en una pestaña aparte, para llevarla a la pantalla del proyector.
   - Sigue al visor «Cablear de a uno» de la ventana principal por BroadcastChannel('planocables'): la ventana principal
     manda el cable actual (con sus terminales) cada vez que lo dibuja, y esta pestaña le devuelve las teclas → ← Espacio,
     que allá avanzan y marcan el cable como cableado (igual que en el visor).
   - Calibración: cuatro miras, una por orificio de montaje de la placa (programa/proyector.py los busca en el dibujo de
     la bandeja). Se arrastran hasta el orificio real y la capa se deforma (homografía en CSS matrix3d) para que las
     canaletas proyectadas caigan sobre las de verdad. Se guarda en instructivo.json (proyector.calibracion).
   - Ventana de texto: origen y destino del cable con su terminal y a dónde va cada punta. Se mueve por el título y se
     agranda por la esquina; arranca en la parte vacía de la bandeja. También se guarda (proyector.ventana).
   - Giro: el taller cablea la bandeja ACOSTADA (en horizontal), así que el encuadre inicial va girado 90° en sentido
     horario (el borde de arriba del dibujo queda a la derecha); ⚙ Ver o la tecla G lo cambian (0 / 90 / 180 / 270).
   Solo se dibuja lo que hay que proyectar: fondo negro, canaletas, recorrido, origen en verde lima y destino en cian. */
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const norm = s => String(s ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
const f2 = v => (+v).toFixed(2);
const LAT = d => d === 'LI' || d === 'LD';
const JOB = (location.pathname.match(/\/proyector\/([0-9a-f]{12})/) || [])[1];
const NOMBRES = ['arriba a la izquierda', 'arriba a la derecha', 'abajo a la derecha', 'abajo a la izquierda'];
// colores de cable aclarados para proyectar (el negro y el marrón no se ven proyectados sobre la bandeja)
const LINE = { rojo: '#ff3b3b', negro: '#ffffff', azul: '#4f8dff', blanco: '#ffffff', marron: '#d08a4a', gris: '#c0c0c0', verde: '#3ddc5a',
  amarillo: '#ffe600', naranja: '#ff9a1f', violeta: '#c07bff', celeste: '#6fd3ff', rosa: '#ff8ac8' };
const SWATCH = { rojo: '#d62828', negro: '#1b1b1b', azul: '#1f5fd6', blanco: '#ffffff', marron: '#7a4a26', gris: '#8d8d8d', verde: '#2e8b3e',
  amarillo: '#f2c200', naranja: '#f07c00', violeta: '#7b3fb3', celeste: '#4fb3e8', rosa: '#e87aa8' };
const colorDe = (tabla, c) => { const k = norm(c); if (k.includes('verde') && k.includes('amarillo')) return tabla.verde; return tabla[k] || null; };
const fmtSec = s => (s === '' || s == null) ? '' : String(s).replace('.', ',') + ' mm²';
const secNum = l => String(l.secc || ((l.cable || '').match(/(\d+(?:[.,]\d+)?)MM/i) || [])[1] || '').replace(',', '.').replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
const secTxt = l => fmtSec(secNum(l));
const secCorto = l => { const n = secNum(l); return n ? n.replace('.', ',') + 'mm²' : ''; };

const OPC = { rotulos: true, rieles: false, borde: false, colorCable: false, extremos: true, grosor: 1, brillo: 1, letra: 1, ventana: true, giro: 90 };
const GIROS = { 0: 'sin girar, como en el dibujo', 90: 'acostada: el borde de arriba del dibujo queda a la derecha', 180: 'dada vuelta',
  270: 'acostada: el borde de arriba del dibujo queda a la izquierda' };
const giro = () => (((+P.opc.giro || 0) % 360) + 360) % 360;
const P = { info: null, cable: null, abierto: false, src: null, dst: null, H: null, calib: false, pin: 0, conectado: 0, bc: null, pend: null, saveT: 0,
  listo: false, pantalla: [innerWidth, innerHeight], opc: { ...OPC } };
const topo = () => (P.info && P.info.topo) || {};
const reg = () => topo().region;
const loc = p => { const r = reg(); return [p[0] - r[0], r[3] - p[1]]; };      // pt del plano (y hacia arriba) -> px locales de la capa
const orificiosActuales = () => (P.info.orificios_usuario && P.info.orificios_usuario.length === 4) ? P.info.orificios_usuario : ((P.info.orificios || {}).puntos || []);

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).error || m; } catch (e) { } throw new Error(m); }
  return r.headers.get('content-type')?.includes('json') ? r.json() : r;
}
function toast(msg, ms = 2600) { const t = $('#toast'); t.textContent = msg; t.hidden = false; clearTimeout(toast._t); toast._t = setTimeout(() => t.hidden = true, ms); }
// lo que se guarda en instructivo.json (proyector.*), juntando lo que cambie en medio segundo
function guardar(parte) {
  P.pend = Object.assign(P.pend || {}, parte); clearTimeout(P.saveT);
  P.saveT = setTimeout(async () => {
    const d = P.pend; P.pend = null;
    try { await api(`/api/trabajo/${JOB}/proyector`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) }); }
    catch (e) { toast('No se pudo guardar: ' + e.message, 4000); }
  }, 500);
}

/* ---- carga ---- */
async function cargar(primera) {
  P.info = await api(`/api/trabajo/${JOB}/proyector`);
  if (primera) Object.assign(P.opc, P.info.opciones || {});
  const r = reg();
  if (!r) { $('#espMsg').textContent = 'Este trabajo no tiene la bandeja del topográfico: no hay nada que proyectar. Cargá el topográfico en la pestaña 🧰 Instructivo de la ventana principal.'; return; }
  const W = r[2] - r[0], H = r[3] - r[1], svg = $('#svg');
  svg.setAttribute('width', f2(W)); svg.setAttribute('height', f2(H)); svg.setAttribute('viewBox', `${f2(r[0])} ${f2(-r[3])} ${f2(W)} ${f2(H)}`);
  Object.assign($('#capa').style, { width: W + 'px', height: H + 'px' });
  P.src = orificiosActuales().map(loc);
  if (primera || !P.dst) P.dst = calibracionGuardada() || encuadre();
  document.title = `📽 ${P.info.nombre || 'Proyector'}`;
  aplicar(); dibujarFijo(); dibujarCable(); opcionesUI();
  if (primera) { ventanaColocar(false); ventana(); P.listo = true; }
  const o = P.info.orificios || {};
  $('#calibOrif').innerHTML = P.info.orificios_usuario ? 'Miras: orificios <b>marcados a mano</b> en el dibujo (🎯 en el visor de la ventana principal).'
    : o.fuente === 'dibujo' ? `Miras: los 4 orificios de montaje encontrados en el dibujo de la bandeja.${(o.avisos || []).length ? ' ⚠ ' + esc(o.avisos.join(' · ')) : ''}`
      : `⚠ ${esc((o.avisos || [])[0] || 'sin orificios en el dibujo')}. Las miras van en las <b>esquinas de la placa</b>.`;
  if (primera && !P.info.calibracion) toast('Sin calibrar todavía: apretá C (o 🎯 Calibrar) y llevá cada mira al orificio real de su esquina', 7000);
}
// la calibracion guardada, llevada al tamaño actual de la pantalla si cambio (otra resolucion, pantalla completa)
function calibracionGuardada() {
  const c = P.info.calibracion; if (!c || !Array.isArray(c.dst) || c.dst.length !== 4) return null;
  const [pw, ph] = c.pantalla || [innerWidth, innerHeight], kx = innerWidth / pw, ky = innerHeight / ph;
  return c.dst.map(([x, y]) => [x * kx, y * ky]);
}
// un punto de la capa (u a la derecha, v hacia abajo) con el dibujo girado g grados en sentido horario
function girar(u, v, W, H, g) {
  switch (g) {
    case 90: return [H - v, u];
    case 180: return [W - u, H - v];
    case 270: return [v, W - u];
    default: return [u, v];
  }
}
// sin calibrar: la placa entera centrada en la pantalla, con margen, girada como se cablea (opción 'giro')
function encuadre() {
  const r = reg(), W = r[2] - r[0], H = r[3] - r[1], g = giro(), m = 0.06;
  const [Wr, Hr] = g % 180 ? [H, W] : [W, H];
  const s = Math.min(innerWidth * (1 - 2 * m) / Wr, innerHeight * (1 - 2 * m) / Hr), ox = (innerWidth - Wr * s) / 2, oy = (innerHeight - Hr * s) / 2;
  return P.src.map(([u, v]) => { const [x, y] = girar(u, v, W, H, g); return [ox + x * s, oy + y * s]; });
}
// girar la bandeja en la pantalla: las miras vuelven al encuadre inicial girado (hay que calibrar de nuevo)
function setGiro(g) {
  P.opc.giro = ((g % 360) + 360) % 360;
  P.dst = encuadre(); aplicar(); guardarCalib();
  opcionesUI(); dibujarCable(); guardar({ opciones: P.opc });
  ventanaColocar(true);
  toast(`Bandeja girada ${P.opc.giro}° (${GIROS[P.opc.giro]}). Las miras volvieron al encuadre inicial: calibrá de nuevo con C`, 6000);
}

/* ---- homografía: 4 orificios del dibujo (px locales) -> 4 miras en la pantalla ---- */
function homografia(src, dst) {
  const A = [], b = [];
  for (let i = 0; i < 4; i++) {
    const [x, y] = src[i], [X, Y] = dst[i];
    A.push([x, y, 1, 0, 0, 0, -X * x, -X * y]); b.push(X);
    A.push([0, 0, 0, x, y, 1, -Y * x, -Y * y]); b.push(Y);
  }
  const h = resolver(A, b); if (!h) return null;
  return [h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1];
}
function resolver(A, b) {           // Gauss con pivoteo parcial
  const n = b.length, M = A.map((row, i) => [...row, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    if (Math.abs(M[p][c]) < 1e-12) return null;
    [M[c], M[p]] = [M[p], M[c]];
    for (let r = 0; r < n; r++) { if (r === c) continue; const f = M[r][c] / M[c][c]; if (!f) continue; for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
  }
  return M.map((row, i) => row[n] / row[i]);
}
const conH = (H, [x, y]) => { const w = H[6] * x + H[7] * y + H[8]; return [(H[0] * x + H[1] * y + H[2]) / w, (H[3] * x + H[4] * y + H[5]) / w]; };
function aplicar() {
  const H = homografia(P.src, P.dst);
  if (!H) return;        // miras degeneradas (tres en línea): queda la última buena
  P.H = H;
  $('#capa').style.transform = `matrix3d(${H[0]},${H[3]},0,${H[6]},${H[1]},${H[4]},0,${H[7]},0,0,1,0,${H[2]},${H[5]},0,${H[8]})`;
  $$('.pin').forEach((el, i) => { el.style.left = P.dst[i][0] + 'px'; el.style.top = P.dst[i][1] + 'px'; });
}

/* ---- lo fijo: canaletas (solo el contorno), rieles y borde opcionales, miras de los orificios al calibrar ---- */
function dibujarFijo() {
  const t = topo(), r = reg(), g = P.opc.grosor;
  if (!r) return;
  let s = '';
  for (const d of t.ductos || []) {
    const [x0, y0, x1, y1] = d.b;
    s += `<rect x="${f2(x0)}" y="${f2(-y1)}" width="${f2(x1 - x0)}" height="${f2(y1 - y0)}" class="can${d.ex ? ' ex' : ''}" stroke-width="${f2(1.2 * g)}"/>`;
  }
  if (P.opc.rieles) {
    const xs = (t.ductos || []).flatMap(d => [d.b[0], d.b[2]]);
    const x0 = xs.length ? Math.min(...xs) : r[0], x1 = xs.length ? Math.max(...xs) : r[2];
    for (const y of t.filas || []) s += `<line x1="${f2(x0)}" y1="${f2(-y)}" x2="${f2(x1)}" y2="${f2(-y)}" class="riel" stroke-width="${f2(0.8 * g)}"/>`;
  }
  if (P.opc.borde || P.calib) s += `<rect x="${f2(r[0])}" y="${f2(-r[3])}" width="${f2(r[2] - r[0])}" height="${f2(r[3] - r[1])}" class="borde" stroke-width="${f2(0.8 * g)}"/>`;
  if (P.calib) for (const p of orificiosActuales()) {
    const x = f2(p[0]), y = f2(-p[1]);
    s += `<g class="orif"><circle cx="${x}" cy="${y}" r="6" stroke-width="1"/><circle cx="${x}" cy="${y}" r=".9" class="pt"/>
      <line x1="${f2(p[0] - 11)}" y1="${y}" x2="${f2(p[0] + 11)}" y2="${y}" stroke-width=".7"/><line x1="${x}" y1="${f2(-p[1] - 11)}" x2="${x}" y2="${f2(-p[1] + 11)}" stroke-width=".7"/></g>`;
  }
  $('#gFijo').innerHTML = s;
}

/* ---- el cable: recorrido, origen (verde lima) y destino (cian), rótulos ---- */
function dibujarCable() {
  const c = P.cable, g = P.opc.grosor;
  if (!c || !c.l || !reg()) { $('#gCable').innerHTML = ''; return; }
  const l = c.l, col = P.opc.colorCable ? (colorDe(LINE, l.color) || 'var(--ruta)') : 'var(--ruta)';
  let s = '';
  for (const sb of c.sibs || []) s += ruta(sb, col, 1.8 * g, true);
  s += ruta(l, col, 3 * g, false);
  const r = l.ruta || [];
  if (r.length) {
    const o = r[0], d = r[r.length - 1];
    if (P.opc.rotulos && r.length > 1) {
      const fs = 7 * g * P.opc.letra;
      s += rotulo(o, r[1], 7 * g, l.num, secCorto(l), fs);
      if (!LAT(l.destino)) s += rotulo(d, r[r.length - 2], 7 * g, l.num, secCorto(l), fs);
    }
    s += mira(o, 'ori', g);
    s += LAT(l.destino) ? salida(d, l.destino, g) : mira(d, 'des', g);
  }
  $('#gCable').innerHTML = s;
}
function ruta(l, col, w, sib) {
  if (!l.ruta || l.ruta.length < 2) return '';
  const d = 'M' + l.ruta.map(p => f2(p[0]) + ' ' + f2(-p[1])).join('L');
  let s = `<g class="rt${sib ? ' sib' : ''}">`;
  if (!sib) s += `<path d="${d}" class="halo" stroke-width="${f2(w * 2.4)}"/>`;
  s += `<path d="${d}" stroke="${col}" stroke-width="${f2(w)}"${sib ? ` stroke-dasharray="${f2(3 * w)} ${f2(1.6 * w)}"` : ''}/>`;
  if (sib && P.opc.extremos) for (const p of [l.ruta[0], l.ruta[l.ruta.length - 1]])
    s += `<circle cx="${f2(p[0])}" cy="${f2(-p[1])}" r="${f2(2.2 * w)}" class="sib-end" stroke-width="${f2(0.6 * w)}"/>`;
  return s + '</g>';
}
// marca de la punta: anillo que late + anillo fijo + punto, del color del origen o del destino
function mira(p, cls, g) {
  const x = f2(p[0]), y = f2(-p[1]), r = 5.5 * g;
  return `<g class="${cls}"><circle cx="${x}" cy="${y}" r="${f2(r)}" class="anillo" stroke-width="${f2(1.6 * g)}">
      <animate attributeName="r" values="${f2(r)};${f2(r * 2.6)};${f2(r)}" dur="1.6s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="1;0;1" dur="1.6s" repeatCount="indefinite"/></circle>
    <circle cx="${x}" cy="${y}" r="${f2(r)}" class="anillo" stroke-width="${f2(1.6 * g)}"/>
    <circle cx="${x}" cy="${y}" r="${f2(1.8 * g)}" class="punto"/></g>`;
}
// destino fuera de la bandeja (LI / LD): la salida por el borde, con el lateral escrito del lado por donde sale el
// cable y derecho en la pantalla (el dibujo está girado 'giro' grados en sentido horario)
function salida(p, lat, g) {
  const x = p[0], y = -p[1], fs = 9 * g * P.opc.letra, gi = giro();
  let d = [lat === 'LD' ? 1 : -1, 0];                       // hacia afuera, en el dibujo
  for (let k = 0; k < gi / 90; k++) d = [-d[1], d[0]];        // y en la pantalla
  const flecha = d[0] < 0 ? '←' : d[0] > 0 ? '→' : d[1] < 0 ? '↑' : '↓';
  const txt = d[0] < 0 || d[1] < 0 ? `${flecha} ${lat}` : `${lat} ${flecha}`;
  const horiz = d[0] !== 0;
  const tx = horiz ? d[0] * 7 * g : 0, ty = horiz ? fs * 0.36 : (d[1] < 0 ? -7 * g : 7 * g + fs * 0.8);
  return `<g class="des"><circle cx="${f2(x)}" cy="${f2(y)}" r="${f2(4 * g)}" class="anillo" stroke-width="${f2(1.4 * g)}"/>
    <g transform="translate(${f2(x)} ${f2(y)}) rotate(${-gi})"><text x="${f2(tx)}" y="${f2(ty)}" font-size="${f2(fs)}" text-anchor="${horiz ? (d[0] < 0 ? 'end' : 'start') : 'middle'}" class="lat">${txt}</text></g></g>`;
}
// manga con el número (y la sección) a lo largo del cable, después de la marca de la punta
function rotulo(a, b, off, txt, sub, fs) {
  const dx = b[0] - a[0], dy = -(b[1] - a[1]);          // en coordenadas del svg (y invertida)
  const vert = Math.abs(dy) >= Math.abs(dx), sgn = vert ? (dy < 0 ? -1 : 1) : (dx > 0 ? 1 : -1);
  const n = String(txt).length, m = sub ? String(sub).length : 0, pad = 0.4 * fs;
  const L = (n * 0.62 + (m ? 0.5 + m * 0.5 : 0)) * fs + 2 * pad, Hh = 1.35 * fs, c = off + fs * 0.3 + L / 2;
  const cx = vert ? a[0] : a[0] + sgn * c, cy = vert ? -a[1] + sgn * c : -a[1];
  // en la pantalla el texto tiene que leerse de izquierda a derecha o de abajo hacia arriba: si con el giro de la
  // bandeja quedaría al revés, la manga se da vuelta (180°) en su lugar
  let rot = vert ? -90 : 0;
  const th = (((rot + giro()) % 360) + 360) % 360;
  if (th >= 90 && th < 270) rot += 180;
  return `<g class="manga" transform="translate(${f2(cx)} ${f2(cy)})${rot ? ` rotate(${rot})` : ''}">
    <rect x="${f2(-L / 2)}" y="${f2(-Hh / 2)}" width="${f2(L)}" height="${f2(Hh)}" rx="${f2(Hh * 0.25)}"/>
    <text x="0" y="${f2(fs * 0.05)}" text-anchor="middle" dominant-baseline="central" font-size="${f2(fs)}">${esc(txt)}${sub ? `<tspan class="sub" font-size="${f2(fs * 0.78)}" dx="${f2(fs * 0.45)}">${esc(sub)}</tspan>` : ''}</text></g>`;
}

/* ---- ventana de texto ---- */
function ventana() {
  const c = P.cable, v = $('#ventana');
  v.hidden = !P.opc.ventana || P.calib;
  if (!c || !c.l) { $('#vB').innerHTML = '<div class="nota">Esperando el cable del instructivo…</div>'; return; }
  const l = c.l;
  const term = (t, lat) => lat ? `<div class="term lat">se termina después (${esc(lat)}: fuera de la bandeja)</div>`
    : t ? `<div class="term"><i style="background:${t.hex || '#777'}"></i>${esc(t.txt)}</div>` : '';
  $('#vNum').textContent = l.num; $('#vSw').style.background = colorDe(SWATCH, l.color) || '#777';
  $('#vCol').textContent = l.color || ''; $('#vSec').textContent = secTxt(l); $('#vPos').textContent = `${c.n} / ${c.total}`;
  $('#vB').innerHTML = `<div class="punta ori"><div class="rot">Origen</div><div class="txt">${esc(l.origen)}</div>${term(c.to)}<div class="va">va a <b>${esc(l.destino)}</b></div></div>
    <div class="punta des"><div class="rot">Destino</div><div class="txt">${esc(l.destino)}</div>${term(c.td, LAT(l.destino) ? l.destino : null)}<div class="va">viene de <b>${esc(l.origen)}</b></div></div>
    ${(c.sibs || []).length ? `<div class="nota">Cable de ${c.sibs.length + 2} puntas, los otros tramos van punteados: ${c.sibs.map(s => esc(s.origen) + ' → ' + esc(s.destino)).join(' · ')}</div>` : ''}
    ${l.largo_mm || l.hecho ? `<div class="nota">${l.largo_mm ? `≈ ${l.largo_mm} mm por canaleta` : ''}${l.largo_mm && l.hecho ? ' · ' : ''}${l.hecho ? 'ya marcado como cableado' : ''}</div>` : ''}`;
  v.classList.toggle('hecho', !!l.hecho);
  $('#bOk').textContent = l.hecho ? '☑ Cableado' : '☐ Cableado';
  letra();
}
// tamaño de letra según el tamaño de la ventana, para que entren las dos puntas (A− / A+ lo ajustan)
function letra() {
  const v = $('#ventana'), w = v.offsetWidth || 400, h = v.offsetHeight || 240;
  v.style.fontSize = Math.max(11, Math.min(96, Math.min(w / 17, h / 10.5) * P.opc.letra)) + 'px';
}
// la parte vacía de la bandeja: la franja más grande entre la zona de canaletas y el borde de la placa, sin aparatos
function zonaLibre() {
  const t = topo(), r = reg(), ds = t.ductos || []; if (!ds.length || !P.H) return null;
  const D = [Math.min(...ds.map(d => d.b[0])), Math.min(...ds.map(d => d.b[1])), Math.max(...ds.map(d => d.b[2])), Math.max(...ds.map(d => d.b[3]))];
  const comps = Object.values(P.info.comp || {}).filter(c => c.x != null && c.y != null);
  const franjas = [[D[0], r[1], D[2], D[1]], [D[0], D[3], D[2], r[3]], [r[0], D[1], D[0], D[3]], [D[2], D[1], r[2], D[3]]];
  const min = 60 / (t.escala || 1);
  let mejor = null;
  for (const f of franjas) {
    const w = f[2] - f[0], h = f[3] - f[1];
    if (w < min || h < min) continue;
    if (comps.some(c => f[0] <= c.x && c.x <= f[2] && f[1] <= c.y && c.y <= f[3])) continue;
    if (!mejor || w * h > (mejor[2] - mejor[0]) * (mejor[3] - mejor[1])) mejor = f;
  }
  if (!mejor) return null;
  const pts = [[mejor[0], mejor[1]], [mejor[2], mejor[1]], [mejor[2], mejor[3]], [mejor[0], mejor[3]]].map(p => conH(P.H, loc(p)));
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys), mx = (x1 - x0) * 0.06, my = (y1 - y0) * 0.08;
  return { x: x0 + mx, y: y0 + my, w: x1 - x0 - 2 * mx, h: y1 - y0 - 2 * my };
}
function ventanaColocar(reset) {
  const v = $('#ventana'), s = P.info.ventana; let r = null;
  if (!reset && s && s.w) {
    const [pw, ph] = s.pantalla || [innerWidth, innerHeight], kx = innerWidth / pw, ky = innerHeight / ph;
    r = { x: s.x * kx, y: s.y * ky, w: s.w * kx, h: s.h * ky };
  }
  if (!r) r = zonaLibre() || { x: 24, y: Math.max(24, innerHeight - 320), w: Math.min(560, innerWidth - 48), h: 280 };
  r.w = Math.max(220, Math.min(r.w, innerWidth - 10)); r.h = Math.max(120, Math.min(r.h, innerHeight - 10));
  r.x = Math.max(0, Math.min(r.x, innerWidth - r.w)); r.y = Math.max(0, Math.min(r.y, innerHeight - r.h));
  Object.assign(v.style, { left: r.x + 'px', top: r.y + 'px', width: r.w + 'px', height: r.h + 'px' });
  letra();
  if (reset) ventanaGuardar();
}
function ventanaGuardar() {
  const v = $('#ventana'); if (v.hidden || !v.offsetWidth || !P.listo) return;
  guardar({ ventana: { x: v.offsetLeft, y: v.offsetTop, w: v.offsetWidth, h: v.offsetHeight, pantalla: [innerWidth, innerHeight] } });
}

/* ---- calibración con los orificios ---- */
function calibrar(on) {
  P.calib = on; document.body.classList.toggle('calib', on);
  $('#pins').hidden = !on; $('#calib').hidden = !on; $('#bCalib').classList.toggle('on', on);
  if (on) { pinsMarcar(); actividad(); } else guardarCalib();
  $('#ventana').hidden = on || !P.opc.ventana;
  dibujarFijo(); aplicar();
}
function pinsCrear() {
  $('#pins').innerHTML = [0, 1, 2, 3].map(i => `<div class="pin" data-i="${i}" title="Mira ${i + 1}: orificio ${NOMBRES[i]}"><span>${i + 1}</span></div>`).join('');
  $$('.pin').forEach(el => el.addEventListener('pointerdown', e => {
    e.preventDefault(); e.stopPropagation();
    const i = +el.dataset.i; P.pin = i; pinsMarcar();
    const d0 = P.dst[i].slice(), x = e.clientX, y = e.clientY;
    el.setPointerCapture(e.pointerId);
    const mv = ev => { P.dst[i] = [d0[0] + ev.clientX - x, d0[1] + ev.clientY - y]; aplicar(); };
    const up = () => { el.removeEventListener('pointermove', mv); el.removeEventListener('pointerup', up); el.removeEventListener('pointercancel', up); guardarCalib(); };
    el.addEventListener('pointermove', mv); el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
  }));
}
function pinsMarcar() { $$('.pin').forEach((el, i) => el.classList.toggle('on', i === P.pin)); }
function guardarCalib() {
  guardar({ calibracion: { dst: P.dst.map(p => [Math.round(p[0] * 10) / 10, Math.round(p[1] * 10) / 10]), pantalla: [innerWidth, innerHeight], orificios: orificiosActuales() } });
}
function moverPin(dx, dy) { P.dst[P.pin] = [P.dst[P.pin][0] + dx, P.dst[P.pin][1] + dy]; aplicar(); guardarCalib(); }

/* ---- conexión con la ventana principal ---- */
function conectar() {
  if (typeof BroadcastChannel === 'undefined') { $('#estado').textContent = 'Este navegador no puede conectarse con la ventana principal'; return; }
  P.bc = new BroadcastChannel('planocables');
  P.bc.onmessage = e => {
    const m = e.data || {}; if (m.job !== JOB) return;
    if (m.t === 'cable') { P.cable = m; P.abierto = !!m.abierto; P.conectado = Date.now(); dibujarCable(); ventana(); estado(); }
    else if (m.t === 'estado') { P.abierto = !!m.abierto; P.conectado = Date.now(); estado(); }
    else if (m.t === 'orificios') cargar(false).then(() => toast('Orificios del dibujo actualizados: revisá la calibración (C)', 5000)).catch(() => { });
  };
  hola(); setInterval(() => { hola(); estado(); }, 4000);
}
function hola() { if (P.bc) P.bc.postMessage({ t: 'hola', job: JOB }); }
// las teclas de cablear van a la ventana principal (que avanza, marca y devuelve el cable nuevo)
function tecla(key) {
  if (!P.bc) return;
  P.bc.postMessage({ t: 'tecla', job: JOB, key, k: P.cable ? P.cable.k : null });
  if (Date.now() - P.conectado > 10000) toast('Sin conexión con la ventana principal: abrí allá el instructivo de este plano', 4000);
}
function estado() {
  const ok = Date.now() - P.conectado < 10000, el = $('#estado');
  el.className = 'estado ' + (ok ? 'ok' : 'no');
  el.textContent = !ok ? 'Sin conexión con la ventana principal: abrí allá el instructivo de este plano (pestaña 🧰)'
    : P.abierto ? '● Siguiendo al visor ▶ Cablear de a uno' : '● Conectado · con → arranca el visor en la ventana principal';
  $('#espera').hidden = !!P.cable;
  if (!P.cable) $('#espMsg').textContent = ok ? 'Conectado con la ventana principal, esperando el cable…' : 'Esperando a la ventana principal (abrí allá el instructivo de este plano)…';
}

/* ---- opciones, barra y teclas ---- */
function opcionesUI() {
  $('#oRotulos').checked = !!P.opc.rotulos; $('#oRieles').checked = !!P.opc.rieles; $('#oBorde').checked = !!P.opc.borde;
  $('#oColor').checked = !!P.opc.colorCable; $('#oExtremos').checked = !!P.opc.extremos;
  $('#oGrosor').textContent = (+P.opc.grosor).toFixed(1).replace('.', ','); $('#oBrillo').textContent = Math.round(P.opc.brillo * 100) + ' %';
  $('#capa').style.filter = P.opc.brillo < 0.999 ? `brightness(${P.opc.brillo})` : '';
  $('#bVent').classList.toggle('on', !!P.opc.ventana);
  $$('#oGiro [data-g]').forEach(b => b.classList.toggle('on', +b.dataset.g === giro()));
  $('#calibGiro').innerHTML = `Bandeja girada <b>${giro()}°</b> (${esc(GIROS[giro()])}). La mira 1 es el orificio de arriba a la izquierda <b>del dibujo</b>. `
    + `<button class="vb" id="calibGirar" title="Girar la bandeja 90° más (G)">↻ Girar 90° más</button>`;
}
function opcion(k, v) {
  P.opc[k] = v === undefined ? !P.opc[k] : v;
  opcionesUI(); dibujarFijo(); dibujarCable(); ventana();
  guardar({ opciones: P.opc });
}
function pantallaCompleta() {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen().catch(() => toast('No se pudo pasar a pantalla completa: probá con F11', 4000));
}
let idleT = 0;
function actividad() {
  document.body.classList.remove('idle'); clearTimeout(idleT);
  idleT = setTimeout(() => { if (!P.calib && !$('#opc').open) document.body.classList.add('idle'); }, 3500);
}

async function init() {
  pinsCrear(); conectar(); actividad();
  try { await cargar(true); } catch (e) { $('#espMsg').textContent = 'No se pudo cargar el trabajo: ' + e.message; return; }
  window.addEventListener('pointermove', actividad);
  // barra
  $('#bPrev').addEventListener('click', () => tecla('ArrowLeft'));
  $('#bNext').addEventListener('click', () => tecla('ArrowRight'));
  $('#bOk').addEventListener('click', () => tecla(' '));
  $('#bCalib').addEventListener('click', () => calibrar(!P.calib));
  $('#bFull').addEventListener('click', pantallaCompleta);
  $('#bVent').addEventListener('click', () => opcion('ventana'));
  $('#oRotulos').addEventListener('change', e => opcion('rotulos', e.target.checked));
  $('#oRieles').addEventListener('change', e => opcion('rieles', e.target.checked));
  $('#oBorde').addEventListener('change', e => opcion('borde', e.target.checked));
  $('#oColor').addEventListener('change', e => opcion('colorCable', e.target.checked));
  $('#oExtremos').addEventListener('change', e => opcion('extremos', e.target.checked));
  $('#oGrosorMenos').addEventListener('click', () => opcion('grosor', Math.max(0.4, Math.round((P.opc.grosor - 0.2) * 10) / 10)));
  $('#oGrosorMas').addEventListener('click', () => opcion('grosor', Math.min(3, Math.round((P.opc.grosor + 0.2) * 10) / 10)));
  $('#oBrilloMenos').addEventListener('click', () => opcion('brillo', Math.max(0.3, Math.round((P.opc.brillo - 0.1) * 10) / 10)));
  $('#oBrilloMas').addEventListener('click', () => opcion('brillo', Math.min(1, Math.round((P.opc.brillo + 0.1) * 10) / 10)));
  $('#oGiro').addEventListener('click', e => { const b = e.target.closest('[data-g]'); if (b) setGiro(+b.dataset.g); });
  $('#calib').addEventListener('click', e => { if (e.target.closest('#calibGirar')) setGiro(giro() + 90); });
  // calibración
  $('#calibReset').addEventListener('click', () => { P.dst = encuadre(); aplicar(); guardarCalib(); });
  $('#calibOk').addEventListener('click', () => calibrar(false));
  $('#fondo').addEventListener('pointerdown', e => {
    if (!P.calib) return; e.preventDefault();
    const d0 = P.dst.map(p => p.slice()), x = e.clientX, y = e.clientY, el = e.currentTarget; el.setPointerCapture(e.pointerId);
    const mv = ev => { P.dst = d0.map(p => [p[0] + ev.clientX - x, p[1] + ev.clientY - y]); aplicar(); };
    const up = () => { el.removeEventListener('pointermove', mv); el.removeEventListener('pointerup', up); guardarCalib(); };
    el.addEventListener('pointermove', mv); el.addEventListener('pointerup', up);
  });
  window.addEventListener('wheel', e => {
    if (!P.calib || e.target.closest('.calib, .barra')) return; e.preventDefault();
    const f = Math.pow(1.0015, -e.deltaY);
    P.dst = P.dst.map(([x, y]) => [e.clientX + (x - e.clientX) * f, e.clientY + (y - e.clientY) * f]); aplicar(); guardarCalib();
  }, { passive: false });
  // ventana de texto: mover por el título, agrandar por la esquina (resize del navegador)
  $('#vH').addEventListener('pointerdown', e => {
    if (e.target.closest('button')) return; e.preventDefault();
    const v = $('#ventana'), x0 = v.offsetLeft, y0 = v.offsetTop, x = e.clientX, y = e.clientY, h = e.currentTarget; h.setPointerCapture(e.pointerId);
    const mv = ev => { v.style.left = Math.max(40 - v.offsetWidth, Math.min(innerWidth - 40, x0 + ev.clientX - x)) + 'px'; v.style.top = Math.max(0, Math.min(innerHeight - 30, y0 + ev.clientY - y)) + 'px'; };
    const up = () => { h.removeEventListener('pointermove', mv); h.removeEventListener('pointerup', up); ventanaGuardar(); };
    h.addEventListener('pointermove', mv); h.addEventListener('pointerup', up);
  });
  let rsT = 0; new ResizeObserver(() => { letra(); clearTimeout(rsT); rsT = setTimeout(ventanaGuardar, 300); }).observe($('#ventana'));
  $('#vMenos').addEventListener('click', () => opcion('letra', Math.max(0.5, Math.round((P.opc.letra - 0.1) * 10) / 10)));
  $('#vMas').addEventListener('click', () => opcion('letra', Math.min(2.5, Math.round((P.opc.letra + 0.1) * 10) / 10)));
  $('#vLugar').addEventListener('click', () => ventanaColocar(true));
  $('#vCerrar').addEventListener('click', () => opcion('ventana', false));
  // la pestaña cambió de tamaño (pantalla completa, otra pantalla): todo proporcional
  window.addEventListener('resize', () => {
    const [pw, ph] = P.pantalla, kx = innerWidth / pw, ky = innerHeight / ph;
    P.pantalla = [innerWidth, innerHeight];
    if (!P.dst || !isFinite(kx) || !isFinite(ky) || (kx === 1 && ky === 1)) return;
    P.dst = P.dst.map(([x, y]) => [x * kx, y * ky]); aplicar();
    const v = $('#ventana'); v.style.left = parseFloat(v.style.left || 0) * kx + 'px'; v.style.top = parseFloat(v.style.top || 0) * ky + 'px';
    v.style.width = parseFloat(v.style.width || v.offsetWidth) * kx + 'px'; v.style.height = parseFloat(v.style.height || v.offsetHeight) * ky + 'px';
    letra(); guardarCalib(); ventanaGuardar();
  });
  // teclas: → ← Espacio van a la ventana principal (también PageDown / PageUp de un control de presentaciones)
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT') return;
    const k = e.key === 'PageDown' ? 'ArrowRight' : e.key === 'PageUp' ? 'ArrowLeft' : e.key;
    if (P.calib) {
      const paso = e.shiftKey ? 10 : e.altKey ? 0.2 : 1;
      const mv = { ArrowRight: [paso, 0], ArrowLeft: [-paso, 0], ArrowUp: [0, -paso], ArrowDown: [0, paso] }[k];
      if (mv) { e.preventDefault(); return moverPin(mv[0], mv[1]); }
      if (/^[1-4]$/.test(k)) { P.pin = +k - 1; return pinsMarcar(); }
      if (k === 'r' || k === 'R') { P.dst = encuadre(); aplicar(); return guardarCalib(); }
      if (k === 'g' || k === 'G') return setGiro(giro() + 90);
      if (k === 'Enter' || k === 'Escape' || k === 'c' || k === 'C') { e.preventDefault(); return calibrar(false); }
      return;
    }
    if (['ArrowRight', 'ArrowLeft', ' ', 'Enter'].includes(k)) { e.preventDefault(); return tecla(k); }
    const acc = { c: () => calibrar(true), f: pantallaCompleta, v: () => opcion('ventana'), l: () => opcion('rotulos'), r: () => opcion('rieles'), b: () => opcion('borde'),
      g: () => setGiro(giro() + 90),
      Escape: () => { if (document.fullscreenElement) document.exitFullscreen(); } };
    const fn = acc[k] || acc[k.toLowerCase()];
    if (fn) { e.preventDefault(); fn(); }
  });
}
init();
