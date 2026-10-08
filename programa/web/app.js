'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const norm = s => String(s ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\./g, ',');
const natKey = s => String(s ?? '').split(/(\d+)/).map(t => /^\d+$/.test(t) ? t.padStart(8, '0') : t.toLowerCase()).join('');
const fmtSec = s => (s === '' || s == null) ? '' : String(s).replace('.', ',') + ' mm²';

const COLORS = {
  rojo: '#d62828', negro: '#1b1b1b', azul: '#1f5fd6', blanco: '#ffffff', marron: '#7a4a26', gris: '#8d8d8d',
  verde: '#2e8b3e', amarillo: '#f2c200', naranja: '#f07c00', violeta: '#7b3fb3', celeste: '#4fb3e8', rosa: '#e87aa8',
};
const LINE = {
  rojo: '#e0262b', negro: '#141414', azul: '#1f63e0', blanco: '#ffffff', marron: '#8a5a2b', gris: '#8d8d8d',
  verde: '#2e9a44', amarillo: '#f2c200', naranja: '#f07c00', violeta: '#7b3fb3', celeste: '#4fb3e8', rosa: '#e87aa8',
};
function swatch(c) {
  const k = norm(c);
  let bg = COLORS[k];
  if (k.includes('verde') && k.includes('amarillo')) bg = 'repeating-linear-gradient(45deg,#2e8b3e 0 4px,#f2c200 4px 8px)';
  return `<span class="sw"><i style="background:${bg || 'transparent'}"></i>${esc(c || '—')}</span>`;
}

const S = { job: null, res: null, tab: 'cables', sort: { key: null, desc: false }, file: null, polling: null, rows: [] };

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    let m = r.statusText;
    try { m = (await r.json()).error || m; } catch (e) { }
    throw new Error(m);
  }
  return r.headers.get('content-type')?.includes('json') ? r.json() : r;
}
function toast(msg, ms = 2200) {
  const t = $('#toast'); t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => t.hidden = true, ms);
}
function show(view) {
  for (const v of ['vInicio', 'vProceso', 'vResultado']) $('#' + v).hidden = v !== view;
  $('#btnNuevo').hidden = view === 'vInicio';
}

/* ---------------- enrutado ---------------- */
function route() {
  const m = location.hash.match(/^#\/trabajo\/([0-9a-f]{12})/);
  clearTimeout(S.polling);
  closeViewer();
  if (m) openJob(m[1]); else { S.job = null; show('vInicio'); loadHistory(); }
}
const current = id => S.job === id && location.hash.includes(id);
window.addEventListener('hashchange', route);

/* ---------------- inicio: elegir archivo ---------------- */
const drop = $('#drop'), fileInput = $('#fileInput');
function setFile(f) {
  if (!f) return;
  if (!/\.pdf$/i.test(f.name)) { toast('El archivo tiene que ser un PDF'); return; }
  S.file = f; drop.classList.add('has');
  $('#dropName').textContent = `${f.name} · ${(f.size / 1048576).toFixed(1)} MB`;
  $('#btnProcesar').disabled = false;
}
fileInput.addEventListener('change', () => setFile(fileInput.files[0]));
drop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); } });
['dragenter', 'dragover'].forEach(ev => document.addEventListener(ev, e => { e.preventDefault(); if (!$('#vInicio').hidden) drop.classList.add('over'); }));
['dragleave', 'drop'].forEach(ev => document.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('over'); }));
document.addEventListener('drop', e => {
  const f = e.dataTransfer?.files?.[0];
  if (f) { if ($('#vInicio').hidden) location.hash = '#/'; setTimeout(() => setFile(f), 0); }
});
$('#btnProcesar').addEventListener('click', async () => {
  if (!S.file) return;
  const fd = new FormData();
  fd.append('plano', S.file);
  fd.append('pdf', $('#optPdf').checked ? '1' : '0');
  fd.append('excel', $('#optExcel').checked ? '1' : '0');
  fd.append('ocr', $('#optOcr').checked ? '1' : '0');
  $('#btnProcesar').disabled = true;
  show('vProceso'); $('#procNombre').textContent = S.file.name; $('#procMsg').textContent = 'Subiendo archivo…';
  $('#procBar').style.width = '2%'; $('#procLog').textContent = '';
  try {
    const r = await api('/api/procesar', { method: 'POST', body: fd });
    S.file = null; drop.classList.remove('has'); $('#dropName').textContent = 'Ningún archivo elegido'; fileInput.value = '';
    location.hash = '#/trabajo/' + r.id;
  } catch (e) { toast('Error: ' + e.message, 4000); show('vInicio'); $('#btnProcesar').disabled = false; }
});
$('#homeLink').addEventListener('click', e => { e.preventDefault(); location.hash = '#/'; });
$('#btnNuevo').addEventListener('click', () => location.hash = '#/');

/* ---------------- historial ---------------- */
async function loadHistory() {
  let list = [];
  try { list = await api('/api/trabajos'); } catch (e) { }
  const html = list.length ? list.map(j => `
    <div class="hist-item" data-id="${j.id}">
      <b title="${esc(j.nombre)}">${esc(j.nombre)}</b>
      <div class="acts"><button class="icon" data-del="${j.id}" aria-label="Borrar" title="Borrar">🗑</button></div>
      <span class="muted small">${esc(j.creado || '')} ·
        ${j.estado === 'terminado' ? `<span class="pill ok">${j.cables} cables</span>${j.revisar ? ` <span class="pill warn">${j.revisar} a revisar</span>` : ''}`
      : j.estado === 'error' ? '<span class="pill warn">error</span>' : `<span class="pill">${esc(j.estado)}</span>`}</span>
    </div>`).join('') : '<div class="muted small">Todavía no hay planos procesados.</div>';
  $('#histList').innerHTML = html;
  $('#recientes').innerHTML = html;
  $('#recientesCard').hidden = !list.length;
}
function histClick(e) {
  const del = e.target.closest('[data-del]');
  if (del) {
    e.stopPropagation();
    if (confirm('¿Borrar este plano y sus resultados del historial?')) {
      api('/api/trabajo/' + del.dataset.del, { method: 'DELETE' }).then(() => { toast('Borrado'); loadHistory(); }).catch(er => toast(er.message));
    }
    return;
  }
  const it = e.target.closest('.hist-item');
  if (it) { $('#drawer').hidden = true; location.hash = '#/trabajo/' + it.dataset.id; }
}
$('#histList').addEventListener('click', histClick);
$('#recientes').addEventListener('click', histClick);
$('#btnHistorial').addEventListener('click', () => { loadHistory(); $('#drawer').hidden = !$('#drawer').hidden; });
$('#closeDrawer').addEventListener('click', () => $('#drawer').hidden = true);
$('#btnSalir').addEventListener('click', async () => {
  let activos = 0;
  try { activos = (await api('/api/trabajos')).filter(j => ['procesando', 'en cola'].includes(j.estado)).length; } catch (e) { }
  if (!confirm((activos ? `Hay ${activos} plano(s) procesándose y se perderán.\n` : '') + '¿Cerrar el programa? Para volver a usarlo, abre otra vez «Listado de cables (web).bat».')) return;
  try { await api('/api/salir', { method: 'POST' }); } catch (e) { }
  document.body.innerHTML = '<main><div class="card" style="max-width:520px;margin:60px auto"><h2>Programa cerrado</h2><p class="muted">Para volver a usarlo, abre «Listado de cables (web).bat».</p></div></main>';
});

/* ---------------- proceso ---------------- */
async function openJob(id) {
  S.job = id;
  let st;
  try { st = await api(`/api/trabajo/${id}/estado`); } catch (e) { toast('No se encontró ese plano'); location.hash = '#/'; return; }
  if (!current(id)) return;
  if (st.estado === 'terminado') return loadResult(id, st);
  show('vProceso'); $('#procNombre').textContent = st.nombre; procError(null);
  const tick = async () => {
    if (!current(id)) return;
    try { st = await api(`/api/trabajo/${id}/estado`); } catch (e) { if (current(id)) S.polling = setTimeout(tick, 1500); return; }
    if (!current(id)) return;
    $('#procBar').style.width = Math.max(2, (st.progreso || 0) * 100) + '%';
    $('#procMsg').textContent = st.estado === 'en cola' ? 'En cola (hay otro plano procesándose)…' : (st.mensaje || '…');
    $('#procTiempo').textContent = st.transcurrido != null ? st.transcurrido + ' s' : '';
    const log = $('#procLog'); log.textContent = (st.log || []).join('\n'); log.scrollTop = log.scrollHeight;
    if (st.estado === 'terminado') return loadResult(id, st);
    if (st.estado === 'error') return procError(st);
    S.polling = setTimeout(tick, 700);
  };
  tick();
}

function procError(st) {
  $('#vProceso .spinner').hidden = !!st;
  $('#procBar').parentElement.classList.toggle('err', !!st);
  $('#procErr').hidden = !st;
  $('#procLog').hidden = !!st;   // el detalle tecnico queda en una linea; el volcado completo no hace falta
  if (!st) return;
  const e = st.error || '';
  const msg = /interrumpido|Falta la lista de conexiones/i.test(e) ? e
    : /pdf|stream|xref|eof|header|trailer/i.test(e) ? 'El archivo no parece un PDF válido o está dañado.'
    : 'No se pudo procesar el plano.';
  $('#procMsg').textContent = msg;
  $('#procErrDet').textContent = e;
}
$('#procVolver').addEventListener('click', () => location.hash = '#/');
$('#procBorrar').addEventListener('click', async () => {
  if (!S.job || !confirm('¿Borrar este plano del historial?')) return;
  try { await api('/api/trabajo/' + S.job, { method: 'DELETE' }); toast('Borrado'); location.hash = '#/'; } catch (e) { toast(e.message, 4000); }
});

async function loadResult(id, st) {
  const res = await api(`/api/trabajo/${id}/resultado`);
  if (!current(id)) return;
  S.res = res; S.st = st;
  $('#q').value = ''; $('#fRev').checked = false; S.tab = 'cables';
  S.byNum = {};
  res.detalle.forEach((d, i) => { d._i = i; (S.byNum[d.num] ||= []).push(d); });
  for (const k in S.byNum) S.byNum[k].sort((a, b) => a.pag - b.pag || natKey(a.zona).localeCompare(natKey(b.zona)));
  S.pages = Object.fromEntries(res.paginas.map(p => [p.index, p]));
  show('vResultado');
  $('#resNombre').textContent = res.nombre;
  $('#resNota').hidden = !!res.rutas;
  $('#resNota').innerHTML = 'Este plano se procesó con una versión anterior del programa: pulsa <b>↻ Reprocesar</b> para ver el recorrido coloreado de cada cable y sus puntas.';
  $('#resInfo').textContent = `Procesado ${res.fecha} · ${res.paginas.length} páginas · ${res.segundos} s` + (res.nota ? ` · Nota del plano: “${res.nota}”` : '');
  if (typeof Prod !== 'undefined') Prod.enTrabajo(id);      // línea «Producto: 75286-1 · ... ✎» (web/producto.js)
  const dlp = $('#dlPdf'), dle = $('#dlExcel');
  dlp.href = `/api/trabajo/${id}/descargar/pdf`; dlp.classList.toggle('disabled', !st.pdf);
  dle.href = `/api/trabajo/${id}/descargar/excel`; dle.classList.toggle('disabled', !st.excel);
  const nNums = new Set(res.cables.map(c => c.num)).size;
  const nRev = res.revisar.length;
  $('#kpis').innerHTML = [
    [res.cables.length !== nNums ? `Números de cable (${res.cables.length - nNums} con 2 secciones → ${res.cables.length} filas)` : 'Números de cable', nNums, 'cables'], ['Etiquetas encontradas', res.detalle.length, 'detalle'],
    ['Tramos sin número', res.sin_numero.length, 'sinnum'], ['A revisar', nRev, 'revisar', nRev ? 'warn' : ''],
    ['Hojas con cables', res.paginas.filter(p => p.cables).length, 'hojas'],
  ].map(([l, v, t, c]) => `<div class="kpi click ${c || ''}" data-tab="${t}"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');
  $('#cntCables').textContent = res.cables.length !== nNums ? `${nNums} nº · ${res.cables.length} filas` : nNums;
  $('#cntDetalle').textContent = res.detalle.length;
  $('#cntSinnum').textContent = res.sin_numero.length; $('#cntRevisar').textContent = nRev || '';
  $('#cntHojas').textContent = res.paginas.length;
  $('#vPage').innerHTML = res.paginas.map(p => `<option value="${p.index}">Hoja ${esc(p.sheet)} · ${esc((p.title || '').replace(/^DIAGRAMA EL[ÉE]CTRICO\s+\S+\s*/i, '') || 'pág. ' + p.index)}</option>`).join('');
  setTab(S.tab || 'cables');
  $('#vsQ').value = ''; loadSeen(); renderSide();
}
$('#kpis').addEventListener('click', e => { const k = e.target.closest('[data-tab]'); if (k) setTab(k.dataset.tab); });
$('#btnReproc').addEventListener('click', async () => {
  if (!S.job || !confirm('¿Volver a procesar este plano con la versión actual del programa? Se reemplazan su PDF buscable y su Excel. '
    + 'Si el trabajo tiene topográfico, también se vuelve a armar el instructivo (como ↻ Regenerar: se conservan las marcas de cableado, '
    + 'los puntos ajustados, las estaciones, los cables quitados y la auditoría; se pierden los textos editados a mano).')) return;
  try { await api(`/api/trabajo/${S.job}/reprocesar`, { method: 'POST' }); openJob(S.job); } catch (e) { toast(e.message, 4000); }
});
$('#btnCarpeta').addEventListener('click', () => api(`/api/trabajo/${S.job}/abrir-carpeta`, { method: 'POST' }).catch(e => toast(e.message)));

/* ---------------- tablas ---------------- */
const chipsFor = c => {
  const occ = S.byNum[c.num] || [];
  return `<div class="chips">${occ.map((d, i) => [d, i]).filter(([d]) => d.color === c.color && String(d.sec) === String(c.sec))
    .map(([d, i]) => `<button class="chip" data-num="${esc(c.num)}" data-idx="${i}" title="Ver en el plano">${esc(d.hoja)}:${esc(d.zona)}</button>`).join('')}</div>`;
};
const TABS = {
  cables: {
    rows: () => S.res.cables,
    cols: [
      { k: 'num', l: 'Nº cable', cls: 'num', v: c => c.num, h: c => hl(c.num) },
      { k: 'color', l: 'Color', v: c => c.color, h: c => swatch(c.color) },
      { k: 'sec', l: 'Sección', v: c => parseFloat(String(c.sec).replace(',', '.')) || 0, h: c => `<span class="sec">${esc(fmtSec(c.sec))}</span>` },
      { k: 'hojas', l: 'Hojas', v: c => natKey(c.hojas), h: c => esc(c.hojas) },
      { k: 'ubic', l: 'Ubicación (hoja:zona)', v: c => natKey(c.ubic), h: chipsFor },
      { k: 'n', l: 'Etiq.', v: c => c.n, h: c => c.n },
      { k: 'puntas', l: 'Puntas', v: c => c.puntas || 0, h: c => c.puntas >= 3 ? `<span class="pill puntas" title="Puente o derivación en bornera">${c.puntas}</span>` : (c.puntas || '') },
      { k: 'refs', l: 'Continúa en', v: c => c.refs || '', h: c => esc(c.refs || '') },
      { k: 'obs', l: 'Observaciones', cls: 'obs', v: c => c.obs || '', h: c => obsHtml(c.obs) },
    ],
    text: c => [c.color, c.sec, fmtSec(c.sec), c.hojas, c.ubic, c.refs, c.obs].join(' '),
    rev: c => /revisar/i.test(c.obs || ''),
    open: c => openCable(c.num, Math.max(0, (S.byNum[c.num] || []).findIndex(d => d.color === c.color && String(d.sec) === String(c.sec)))),
    tsv: ['Nº cable', 'Color', 'Sección (mm²)', 'Hojas', 'Ubicación', 'Nº etiquetas', 'Puntas', 'Continúa en', 'Observaciones'],
    tsvRow: c => [c.num, c.color, String(c.sec).replace('.', ','), c.hojas, c.ubic, c.n, c.puntas || '', c.refs || '', c.obs || ''],
  },
  detalle: {
    rows: () => S.res.detalle,
    cols: [
      { k: 'num', l: 'Nº cable', cls: 'num', v: d => d.num, h: d => hl(d.num) },
      { k: 'hoja', l: 'Hoja', v: d => natKey(d.hoja), h: d => esc(d.hoja) },
      { k: 'zona', l: 'Zona', v: d => natKey(d.zona), h: d => esc(d.zona) },
      { k: 'color', l: 'Color', v: d => d.color, h: d => swatch(d.color) },
      { k: 'sec', l: 'Sección', v: d => parseFloat(String(d.sec).replace(',', '.')) || 0, h: d => `<span class="sec">${esc(fmtSec(d.sec))}</span>` },
      { k: 'origen', l: 'De dónde sale el color/sección', cls: 'obs', v: d => d.origen, h: d => esc(d.origen) },
      { k: 'corte', l: 'Raya', v: d => d.corte ? 1 : 0, h: d => d.corte ? 'Sí' : '—' },
      { k: 'refs', l: 'Continúa en', v: d => (d.refs || []).join(', '), h: d => esc((d.refs || []).join(', ')) },
    ],
    text: d => [d.hoja, d.zona, d.color, d.sec, fmtSec(d.sec), d.origen, (d.refs || []).join(' ')].join(' '),
    rev: d => /hay varias/.test(d.origen || '') || S.res.cables.some(c => c.num === d.num && c.color === d.color && String(c.sec) === String(d.sec) && /revisar/i.test(c.obs || '')),
    open: d => openCable(d.num, S.byNum[d.num].indexOf(d)),
    tsv: ['Nº cable', 'Hoja', 'Página PDF', 'Zona', 'Color', 'Sección (mm²)', 'Origen', 'Raya de corte', 'Continúa en'],
    tsvRow: d => [d.num, d.hoja, d.pag, d.zona, d.color, String(d.sec).replace('.', ','), d.origen, d.corte ? 'Sí' : 'No', (d.refs || []).join(', ')],
  },
  sinnum: {
    rows: () => S.res.sin_numero,
    cols: [
      { k: 'color', l: 'Color', v: u => u.color, h: u => swatch(u.color) },
      { k: 'sec', l: 'Sección', v: u => parseFloat(String(u.sec).replace(',', '.')) || 0, h: u => `<span class="sec">${esc(fmtSec(u.sec))}</span>` },
      { k: 'hoja', l: 'Hoja', v: u => natKey(u.hoja), h: u => esc(u.hoja) },
      { k: 'zona', l: 'Zona', v: u => natKey(u.zona), h: u => esc(u.zona) },
      { k: 'refs', l: 'Continúa en', v: u => u.refs || '', h: u => esc(u.refs || '') },
      { k: 'texto', l: 'Etiqueta leída', v: u => u.texto, h: u => `<span class="mono">${esc(u.texto)}</span>` },
    ],
    text: u => [u.color, u.sec, fmtSec(u.sec), u.hoja, u.zona, u.refs, u.texto].join(' '),
    open: u => openItem(u.pag, u.bbox, `Tramo sin número · ${u.color} ${fmtSec(u.sec)}`, `Hoja ${u.hoja} · zona ${u.zona}`),
    tsv: ['Color', 'Sección (mm²)', 'Hoja', 'Zona', 'Continúa en', 'Etiqueta'],
    tsvRow: u => [u.color, String(u.sec).replace('.', ','), u.hoja, u.zona, u.refs || '', u.texto],
  },
  revisar: {
    rows: () => S.res.revisar,
    cols: [
      { k: 'tipo', l: 'Qué pasa', v: r => r.tipo, h: r => esc(r.tipo) },
      { k: 'texto', l: 'Texto', v: r => r.texto, h: r => `<span class="mono">${esc(r.texto)}</span>` },
      { k: 'hoja', l: 'Hoja', v: r => natKey(r.hoja), h: r => esc(r.hoja) },
      { k: 'zona', l: 'Zona', v: r => natKey(r.zona), h: r => esc(r.zona) },
    ],
    text: r => [r.tipo, r.texto, r.hoja, r.zona].join(' '),
    open: r => r.num && S.byNum[r.num] ? openCable(r.num, 0) : openItem(r.pag, r.bbox, r.tipo, `${r.texto} · hoja ${r.hoja} · zona ${r.zona}`),
    tsv: ['Tipo', 'Texto', 'Hoja', 'Zona'],
    tsvRow: r => [r.tipo, r.texto, r.hoja, r.zona],
  },
};
function obsHtml(o) {
  if (!o) return '';
  return esc(o).replace(/(Cable de \d+ puntas[^;]*)/, '<span class="tag pt">$1</span>').replace(/(revisar)/gi, '<b style="color:var(--warn)">$1</b>').replace(/(según la nota del plano)/, '<span class="tag def">$1</span>');
}
let QN = '';
function hl(num) {
  const s = esc(num);
  if (!QN || !/^\d+$/.test(QN)) return s;
  const i = s.indexOf(QN);
  return i < 0 ? s : s.slice(0, i) + '<mark>' + s.slice(i, i + QN.length) + '</mark>' + s.slice(i + QN.length);
}

function setTab(t) {
  const same = ['cables', 'detalle'];
  if (!(same.includes(S.tab) && same.includes(t)) && S.tab !== t) {   // la búsqueda solo se conserva entre Cables y Detalle
    $('#q').value = ''; $('#fColor').value = ''; $('#fSec').value = ''; $('#fRev').checked = false;
  }
  S.tab = t; S.sort = { key: null, desc: false };
  document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab === t));
  const isSheets = t === 'hojas', isIns = t === 'instructivo', isE8 = t === 'e8';
  $('#tableWrap').hidden = isSheets || isIns || isE8; $('#sheets').hidden = !isSheets; $('#toolbar').hidden = isSheets || isIns || isE8;
  if (!isE8 && typeof E8 !== 'undefined') E8.hide();
  if (isIns) { if (typeof Ins !== 'undefined') Ins.open(); return; }
  if (typeof Ins !== 'undefined') Ins.hide();
  if (isE8) { if (typeof E8 !== 'undefined') E8.open(); return; }
  $('#fColor').hidden = $('#fSec').hidden = !['cables', 'detalle', 'sinnum'].includes(t);
  $('#fRevWrap').hidden = !TABS[t]?.rev;
  if (!isSheets && ['cables', 'detalle', 'sinnum'].includes(t)) fillFilters(TABS[t].rows());
  if (isSheets) renderSheets(); else renderTable();
}
$('#tabs').addEventListener('click', e => { const b = e.target.closest('button'); if (b) setTab(b.dataset.tab); });

function fillFilters(rows) {
  const fc = $('#fColor').value, fs = $('#fSec').value;
  const colors = [...new Set(rows.map(c => c.color).filter(Boolean))].sort();
  const secs = [...new Set(rows.map(c => String(c.sec)).filter(Boolean))].sort((a, b) => parseFloat(a.replace(',', '.')) - parseFloat(b.replace(',', '.')));
  $('#fColor').innerHTML = '<option value="">Todos los colores</option>' + colors.map(c => `<option>${esc(c)}</option>`).join('');
  $('#fSec').innerHTML = '<option value="">Todas las secciones</option>' + secs.map(s => `<option value="${esc(s)}">${esc(fmtSec(s))}</option>`).join('');
  if (colors.includes(fc)) $('#fColor').value = fc;
  if (secs.includes(fs)) $('#fSec').value = fs;
}
function filtered() {
  const T = TABS[S.tab];
  const q = norm($('#q').value.trim()); QN = q;
  const fc = $('#fColor').value, fs = $('#fSec').value, fr = $('#fRev').checked;
  let rows = T.rows().filter(r => {
    if (fc && !$('#fColor').hidden && r.color !== fc) return false;
    if (fs && !$('#fSec').hidden && String(r.sec) !== fs) return false;
    if (fr && T.rev && !T.rev(r)) return false;
    if (!q) return true;
    const mh = q.match(/^(?:hoja|h|sh)\s*(\d+)$/);
    if (mh) {
      const hs = norm(r.hojas || r.hoja || '').split(/[ ,]+/);
      return hs.some(h => h === mh[1] || h.replace(/^0+/, '') === mh[1].replace(/^0+/, ''));
    }
    if (/^\d+$/.test(q) && r.num != null) {
      if (String(r.num).includes(q)) return true;
      return norm(r.hojas || r.hoja || '').split(/[ ,]+/).includes(q);
    }
    return q.split(/\s+/).every(w => norm((r.num || '') + ' ' + T.text(r)).includes(w));
  });
  if (S.sort.key) {
    const col = T.cols.find(c => c.k === S.sort.key);
    rows = rows.slice().sort((a, b) => {
      const x = col.v(a), y = col.v(b);
      const r = typeof x === 'number' && typeof y === 'number' ? x - y : natKey(x).localeCompare(natKey(y));
      return S.sort.desc ? -r : r;
    });
  } else if (/^\d+$/.test(q) && T.rows()[0]?.num != null) {
    rows = rows.slice().sort((a, b) => (String(b.num).startsWith(q) - String(a.num).startsWith(q)) || natKey(a.num).localeCompare(natKey(b.num)));
  }
  return rows;
}
function renderTable() {
  const T = TABS[S.tab];
  const rows = S.rows = filtered();
  const head = '<thead><tr>' + T.cols.map(c => `<th data-k="${c.k}" class="${S.sort.key === c.k ? 'sorted' + (S.sort.desc ? ' desc' : '') : ''}">${c.l}</th>`).join('') + '</tr></thead>';
  const body = rows.length ? rows.map((r, i) => `<tr data-i="${i}" class="${T.rev && T.rev(r) ? 'rev' : ''}">` +
    T.cols.map(c => `<td class="${c.cls || ''}">${c.h(r)}</td>`).join('') + '</tr>').join('')
    : `<tr><td colspan="${T.cols.length}" class="empty">Nada coincide con la búsqueda. <button class="btn sm" id="clearQ">Quitar filtros</button></td></tr>`;
  $('#tbl').innerHTML = head + '<tbody>' + body + '</tbody>';
  $('#nRows').textContent = `${rows.length} de ${T.rows().length}`;
}
$('#tbl').addEventListener('click', e => {
  if (e.target.id === 'clearQ') {
    $('#q').value = ''; $('#fColor').value = ''; $('#fSec').value = ''; $('#fRev').checked = false; return renderTable();
  }
  const th = e.target.closest('th');
  if (th) {
    const k = th.dataset.k;
    S.sort = S.sort.key === k ? { key: k, desc: !S.sort.desc } : { key: k, desc: false };
    return renderTable();
  }
  const chip = e.target.closest('.chip');
  if (chip) { e.stopPropagation(); return openCable(chip.dataset.num, +chip.dataset.idx); }
  const tr = e.target.closest('tr[data-i]');
  if (tr) TABS[S.tab].open(S.rows[+tr.dataset.i]);
});
let qT;
$('#q').addEventListener('input', () => { clearTimeout(qT); qT = setTimeout(renderTable, 80); });
$('#q').addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  clearTimeout(qT); renderTable();
  if (S.rows.length) TABS[S.tab].open(S.rows[0]);
});
['#fColor', '#fSec', '#fRev'].forEach(s => $(s).addEventListener('change', renderTable));
document.addEventListener('keydown', e => {
  if ($('#viewer').hidden && !$('#vResultado').hidden && (e.key === '/' || (e.ctrlKey && e.key.toLowerCase() === 'k')) && document.activeElement !== $('#q')) {
    e.preventDefault(); if (S.tab === 'hojas') setTab('cables'); $('#q').focus(); $('#q').select();
  }
});
$('#btnCopiar').addEventListener('click', async () => {
  const T = TABS[S.tab];
  const tsv = [T.tsv, ...S.rows.map(T.tsvRow)].map(r => r.map(v => String(v ?? '').replace(/\t|\n/g, ' ')).join('\t')).join('\n');
  try { await navigator.clipboard.writeText(tsv); toast(`${S.rows.length} filas copiadas: pégalas en Excel`); }
  catch (e) { toast('No se pudo copiar'); }
});
$('#btnImprimir').addEventListener('click', () => window.print());

function renderSheets() {
  const cnt = {};
  S.res.detalle.forEach(d => cnt[d.pag] = (cnt[d.pag] || 0) + 1);
  $('#sheets').innerHTML = S.res.paginas.map(p => `
    <div class="sheet" data-pag="${p.index}">
      <div class="n">Hoja ${esc(p.sheet)} <span class="muted">· pág. ${p.index}</span></div>
      <div class="t">${esc((p.title || '').replace(/^DIAGRAMA EL[ÉE]CTRICO\s+\S+\s*/i, '') || '—')}</div>
      <div class="muted small">${cnt[p.index] ? cnt[p.index] + ' etiquetas de cable' : 'sin números de cable'}</div>
    </div>`).join('');
}
$('#sheets').addEventListener('click', e => { const s = e.target.closest('.sheet'); if (s) openPage(+s.dataset.pag); });

/* ---------------- visor ---------------- */
const V = { mode: null, num: null, idx: 0, pag: null, bbox: null, s: 1, x: 0, y: 0, k: 1, W: 0, H: 0 };
const stage = $('#stage'), world = $('#world'), img = $('#vImg'), ov = $('#ov');

function openCable(num, idx) {
  const occ = S.byNum[num]; if (!occ || !occ.length) return;
  if (V.mode !== 'cable') setAll(false);
  V.mode = 'cable'; V.num = num; V.idx = Math.max(0, Math.min(idx || 0, occ.length - 1));
  showOcc();
}
function showOcc() {
  const occ = S.byNum[V.num], d = occ[V.idx];
  const c = S.res.cables.find(c => c.num === V.num && c.color === d.color && String(c.sec) === String(d.sec)) || {};
  $('#vTitle').innerHTML = `Cable <span class="mono">${esc(V.num)}</span> · ${swatch(d.color)} <span class="sec">${esc(fmtSec(d.sec))}</span>`;
  const rt = S.res.rutas?.[d.pag]?.[V.num];
  const pt = rt && rt.puntas >= 3 && rt.uniones.length ? ` · ${rt.puntas} puntas (puente/derivación${rt.junto?.length ? ' junto a ' + rt.junto.join(', ') : ''})` : '';
  $('#vSub').textContent = `Hoja ${d.hoja} · zona ${d.zona}${pt} · ${d.origen}` + (c.obs && !pt ? ' · ' + c.obs : '');
  $('#vNav').hidden = false; $('#vPos').textContent = `${V.idx + 1} / ${occ.length}`; $('#vIns').hidden = false;
  V.ck = cKey(d); S.seen.add(V.ck); saveSeen(); markSide();
  loadPage(d.pag, () => { drawBoxes(); focusBox(d.bbox); });
}
function openItem(pag, bbox, title, sub) {
  V.mode = 'item'; V.ck = null; markSide(); V.bbox = bbox; $('#vIns').hidden = true;
  $('#vTitle').textContent = title; $('#vSub').textContent = sub || ''; $('#vNav').hidden = true;
  loadPage(pag, () => { drawBoxes(); bbox ? focusBox(bbox) : fit(); });
}
function openPage(pag) {
  V.mode = 'page'; V.ck = null; markSide(); setAll(true); $('#vIns').hidden = true;
  const p = S.pages[pag];
  $('#vTitle').textContent = `Hoja ${p.sheet}`; $('#vSub').textContent = (p.title || '') + ' · haz clic en un número para ver ese cable';
  $('#vNav').hidden = true;
  loadPage(pag, () => { drawBoxes(); fit(); });
}
function loadPage(pag, cb) {
  $('#viewer').hidden = false; document.body.style.overflow = 'hidden';
  $('#vPage').value = pag;
  if (document.activeElement && !['vPage', 'vsQ'].includes(document.activeElement.id)) document.activeElement.blur();   // que las teclas no escriban en el buscador
  if (V.job === S.job && V.pag === pag && img.complete && img.naturalWidth) { cb(); return; }
  V.job = S.job; V.pag = pag; $('#vLoad').hidden = false;
  img.onload = () => {
    $('#vLoad').hidden = true;
    V.W = img.naturalWidth; V.H = img.naturalHeight; V.k = V.W / S.pages[pag].w;
    world.style.width = V.W + 'px'; world.style.height = V.H + 'px';
    cb();
  };
  img.onerror = () => { $('#vLoad').hidden = true; toast('No se pudo cargar la hoja'); };
  img.src = `/api/trabajo/${S.job}/pagina/${pag}.png`;
}
function boxStyle(bb, pad = 3) {
  const p = S.pages[V.pag], k = V.k, x0 = p.x0 || 0, top = (p.y0 || 0) + p.h;
  const l = (bb[0] - x0) * k - pad, t = (top - bb[3]) * k - pad, w = (bb[2] - bb[0]) * k + 2 * pad, h = (bb[3] - bb[1]) * k + 2 * pad;
  return `left:${l}px;top:${t}px;width:${w}px;height:${h}px`;
}
function routeSvg(num, rt, strong) {
  const p = S.pages[V.pag], k = V.k, x0 = p.x0 || 0, top = (p.y0 || 0) + p.h;
  const X = x => ((x - x0) * k).toFixed(1), Y = y => ((top - y) * k).toFixed(1);
  const w = (strong ? 2.4 : 1.7) * k;
  let out = `<g class="rt${strong ? ' sel' : ''}" data-num="${esc(num)}"><title>Cable ${esc(num)}</title>`;
  for (const t of rt.tramos) {
    const d = t.segs.map(s => `M${X(s[0])} ${Y(s[1])}L${X(s[2])} ${Y(s[3])}`).join('');
    const key = norm(t.color), va = key.includes('verde') && key.includes('amarillo');
    const col = va ? LINE.verde : (LINE[key] || '#ff00c8');
    if (strong) out += `<path d="${d}" class="halo" stroke-width="${(w * 3.2).toFixed(1)}"/>`;
    if (['blanco', 'amarillo'].includes(key) || va) out += `<path d="${d}" stroke="#2b2b2b" stroke-width="${(w + 1.2 * k).toFixed(1)}"/>`;
    out += `<path d="${d}" stroke="${col}" stroke-width="${w.toFixed(1)}"/>`;
    if (va) out += `<path d="${d}" stroke="${LINE.amarillo}" stroke-width="${w.toFixed(1)}" stroke-dasharray="${(3 * k).toFixed(1)} ${(3 * k).toFixed(1)}"/>`;
  }
  if (strong) {
    for (const e of rt.fines) out += `<circle cx="${X(e[0])}" cy="${Y(e[1])}" r="${(3.4 * k).toFixed(1)}" class="fin" stroke-width="${(1.1 * k).toFixed(1)}"/>`;
    for (const j of rt.uniones) out += `<circle cx="${X(j[0])}" cy="${Y(j[1])}" r="${(2.8 * k).toFixed(1)}" class="union"/>`;
  }
  return out + '</g>';
}
function setAll(on) { V.all = on; $('#vAll').classList.toggle('on', on); $('#vAll').setAttribute('aria-pressed', on); }
function drawBoxes() {
  const onPage = S.res.detalle.filter(d => d.pag === V.pag);
  const rutas = S.res.rutas?.[V.pag] || {};
  let svg = '';
  if (V.all) for (const [n, rt] of Object.entries(rutas)) if (!(V.mode === 'cable' && n === V.num)) svg += routeSvg(n, rt, false);
  if (V.mode === 'cable' && rutas[V.num]) svg += routeSvg(V.num, rutas[V.num], true);
  let html = `<svg class="rsvg" width="${V.W}" height="${V.H}" viewBox="0 0 ${V.W} ${V.H}">${svg}</svg>`;
  for (const d of onPage) {
    let cls = 'all';
    if (V.mode === 'cable' && d.num === V.num) cls = S.byNum[V.num][V.idx] === d ? 'cur' : 'same';
    html += `<div class="box ${cls}" style="${boxStyle(d.bbox)}" data-num="${esc(d.num)}" data-i="${d._i}" title="Cable ${esc(d.num)} · ${esc(d.color)} ${esc(fmtSec(d.sec))}"></div>`;
  }
  if (V.mode === 'item' && V.bbox) html += `<div class="box cur" style="${boxStyle(V.bbox, 5)}"></div>`;
  ov.innerHTML = html;
}
ov.addEventListener('click', e => {
  const b = e.target.closest('.box[data-num]');
  if (b && !V.dragged) { const occ = S.byNum[b.dataset.num]; openCable(b.dataset.num, Math.max(0, occ.findIndex(d => d._i === +b.dataset.i))); }
});
function apply(anim) {
  world.style.transition = anim ? 'transform .35s ease' : 'none';
  world.style.transform = `translate(${V.x}px,${V.y}px) scale(${V.s})`;
}
function fitScale() { return Math.min(stage.clientWidth / V.W, stage.clientHeight / V.H) * 0.97; }
function fit(anim = true) {
  V.s = fitScale();
  V.x = (stage.clientWidth - V.W * V.s) / 2; V.y = (stage.clientHeight - V.H * V.s) / 2; apply(anim);
}
function focusBox(bb) {
  const p = S.pages[V.pag], x0 = p.x0 || 0, top = (p.y0 || 0) + p.h;
  const cx = ((bb[0] + bb[2]) / 2 - x0) * V.k, cy = (top - (bb[1] + bb[3]) / 2) * V.k;
  V.s = Math.min(Math.max(stage.clientWidth / (650 * V.k), fitScale()), 2.2);
  V.x = stage.clientWidth / 2 - cx * V.s; V.y = stage.clientHeight / 2 - cy * V.s; apply(true);
}
function zoomAt(f, px, py) {
  const ns = Math.min(Math.max(V.s * f, fitScale() * 0.5), 4);
  f = ns / V.s; V.x = px - (px - V.x) * f; V.y = py - (py - V.y) * f; V.s = ns; apply(false);
}
stage.addEventListener('wheel', e => {
  e.preventDefault();
  const r = stage.getBoundingClientRect();
  zoomAt(Math.pow(1.0018, -e.deltaY), e.clientX - r.left, e.clientY - r.top);
}, { passive: false });
let drag = null;
stage.addEventListener('pointerdown', e => {
  if (e.button !== 0) return;
  drag = { x: e.clientX, y: e.clientY, ox: V.x, oy: V.y }; V.dragged = false;
  stage.setPointerCapture(e.pointerId); stage.classList.add('drag');
});
stage.addEventListener('pointermove', e => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (Math.abs(dx) + Math.abs(dy) > 4) V.dragged = true;
  V.x = drag.ox + dx; V.y = drag.oy + dy; apply(false);
});
stage.addEventListener('pointerup', e => {
  drag = null; stage.classList.remove('drag');
  if (!V.dragged) {  // clic sin arrastre: dejar que el recuadro reciba el clic
    const hit = document.elementsFromPoint(e.clientX, e.clientY);
    const el = hit.find(x => x.classList?.contains('box') && x.dataset.num);
    if (el) el.click();
    else {
      const g = hit.map(x => x.closest?.('g.rt[data-num]')).find(Boolean);
      if (g && (g.dataset.num !== V.num || V.mode !== 'cable')) openCable(g.dataset.num, Math.max(0, S.byNum[g.dataset.num].findIndex(d => d.pag === V.pag)));
    }
  }
  setTimeout(() => V.dragged = false, 0);
});
stage.addEventListener('dblclick', e => { const r = stage.getBoundingClientRect(); zoomAt(2, e.clientX - r.left, e.clientY - r.top); });
$('#zIn').addEventListener('click', () => zoomAt(1.5, stage.clientWidth / 2, stage.clientHeight / 2));
$('#zOut').addEventListener('click', () => zoomAt(1 / 1.5, stage.clientWidth / 2, stage.clientHeight / 2));
$('#zFit').addEventListener('click', () => fit());
$('#vAll').addEventListener('click', () => { setAll(!V.all); drawBoxes(); });
$('#vPrev').addEventListener('click', () => step(-1));
$('#vNext').addEventListener('click', () => step(1));
$('#vPage').addEventListener('change', () => { openPage(+$('#vPage').value); $('#vPage').blur(); });
function step(d) {
  if (V.mode !== 'cable') return;
  const n = S.byNum[V.num].length; V.idx = (V.idx + d + n) % n; showOcc();
}
function closeViewer() { if (!$('#viewer').hidden) { $('#viewer').hidden = true; document.body.style.overflow = ''; } }
$('#vClose').addEventListener('click', closeViewer);
// mismo lugar que '⚡ Funcional' en el visor de cableado: ida y vuelta entre los dos visores
$('#vIns').addEventListener('click', () => { if (V.mode === 'cable' && typeof Ins !== 'undefined') Ins.desdeFuncional(V.num); });
document.addEventListener('keydown', e => {
  if ($('#viewer').hidden) { if (e.key === 'Escape') $('#drawer').hidden = true; return; }
  if (e.key === 'Escape') { e.preventDefault(); return closeViewer(); }
  if (e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT') return;
  const keys = { ArrowRight: () => step(1), ArrowLeft: () => step(-1), '+': () => $('#zIn').click(), '=': () => $('#zIn').click(),
                 '-': () => $('#zOut').click(), '0': () => fit(), c: () => $('#vAll').click(),
                 ArrowDown: () => sideStep(1), ArrowUp: () => sideStep(-1), l: () => $('#vSideBtn').click(), i: () => $('#vIns').hidden || $('#vIns').click() };
  if (keys[e.key]) { e.preventDefault(); keys[e.key](); }
});
/* ---------------- listado lateral del visor ---------------- */
const cKey = c => `${c.num}|${c.color}|${c.sec}`;
S.seen = new Set();
function loadSeen() {
  S.seen = new Set();
  try { S.seen = new Set(JSON.parse(localStorage.getItem('vistos:' + S.job) || '[]')); } catch (e) { }
}
function saveSeen() { try { localStorage.setItem('vistos:' + S.job, JSON.stringify([...S.seen])); } catch (e) { } }
function sideRows() {
  const q = norm($('#vsQ').value.trim());
  return S.res.cables.filter(c => !q || (/^\d+$/.test(q) ? String(c.num).includes(q)
    : q.split(/\s+/).every(w => norm(c.num + ' ' + TABS.cables.text(c)).includes(w))))
    .sort((a, b) => natKey(a.num).localeCompare(natKey(b.num)));
}
function renderSide() {
  if (!S.res) return;
  S.side = sideRows();
  $('#vsList').innerHTML = S.side.length ? S.side.map((c, i) => `<button class="vs-it${TABS.cables.rev(c) ? ' rev' : ''}" role="option" data-i="${i}" data-k="${esc(cKey(c))}"
    title="${esc(c.obs || '')}"><span class="ck">✓</span><span class="n">${esc(c.num)}</span>${swatch(c.color)}<span class="sec">${esc(fmtSec(c.sec))}</span></button>`).join('')
    : '<div class="vs-empty muted small">Ningún cable coincide.</div>';
  markSide();
}
function markSide() {
  if (!S.res) return;
  let cur = null;
  for (const b of $('#vsList').children) {
    if (!b.dataset.k) continue;
    b.classList.toggle('seen', S.seen.has(b.dataset.k));
    const on = b.dataset.k === V.ck; b.classList.toggle('on', on); b.setAttribute('aria-selected', on);
    if (on) cur = b;
  }
  const n = S.res.cables.filter(c => S.seen.has(cKey(c))).length;
  $('#vsCnt').textContent = `${n} de ${S.res.cables.length} vistos`;
  if (cur && !$('#vSide').hidden) cur.scrollIntoView({ block: 'nearest' });
}
function sideStep(d) {
  if (!S.side?.length) return;
  const i = S.side.findIndex(c => cKey(c) === V.ck);
  const j = i < 0 ? (d > 0 ? 0 : S.side.length - 1) : Math.max(0, Math.min(S.side.length - 1, i + d));
  if (j !== i) TABS.cables.open(S.side[j]);
}
$('#vsList').addEventListener('click', e => { const b = e.target.closest('.vs-it'); if (b) TABS.cables.open(S.side[+b.dataset.i]); });
let vsT;
$('#vsQ').addEventListener('input', () => { clearTimeout(vsT); vsT = setTimeout(renderSide, 80); });
$('#vsQ').addEventListener('keydown', e => {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); e.stopPropagation(); sideStep(e.key === 'ArrowDown' ? 1 : -1); }
  else if (e.key === 'Enter') { e.preventDefault(); clearTimeout(vsT); renderSide(); if (S.side.length) TABS.cables.open(S.side[0]); }
  else if (e.key === 'Escape' && e.target.value) { e.preventDefault(); e.stopPropagation(); e.target.value = ''; renderSide(); }
});
$('#vsReset').addEventListener('click', () => {
  if (!confirm('¿Quitar todas las marcas de cables vistos de este plano?')) return;
  S.seen.clear(); if (V.ck) S.seen.add(V.ck); saveSeen(); markSide();
});
function setSide(on, keepCenter = true) {
  const w0 = stage.clientWidth;
  $('#vSide').hidden = !on; $('#vSideBtn').classList.toggle('on', on); $('#vSideBtn').setAttribute('aria-pressed', on);
  try { localStorage.setItem('listadoVisor', on ? '1' : '0'); } catch (e) { }
  if (keepCenter && !$('#viewer').hidden && V.W) { V.x += (stage.clientWidth - w0) / 2; apply(false); }
  if (on) markSide();
}
$('#vSideBtn').addEventListener('click', () => setSide($('#vSide').hidden));
{ let on = true; try { on = localStorage.getItem('listadoVisor') !== '0'; } catch (e) { } setSide(on, false); }

window.addEventListener('resize', () => { if (!$('#viewer').hidden && V.W) apply(false); });

route();
