'use strict';
/* Pestaña "Estación 8 (gabinete)": lo que se cablea con la bandeja ya montada.
   - Bandeja lateral (izquierda en el PAE): los cables de sus aparatos sobre su vista del topográfico, en orden de cableado,
     con el visor "cablear de a uno" (como el instructivo de E6).
   - Puerta y placa: aparato por aparato, borne por borne, con adónde va la otra punta.
   Los datos vienen en ins.estacion8 (programa/estacion8.py); las marcas de cableado van en ins.estacion8.hechos. */
const E8 = (() => {
  let D = null, vista = null;          // D = instructivo (el mismo objeto que Ins.D); vista = índice de lateral o 'afuera'
  const W = () => $('#e8Wrap');
  const E = () => (D && D.estacion8) || null;
  const f2 = v => (+v).toFixed(2);
  const hechos = () => new Set((E() && E().hechos) || []);
  const esHecho = k => hechos().has(k);
  function marcar(k, on) {
    const s = hechos(); if (on) s.add(k); else s.delete(k);
    E().hechos = [...s]; Ins.dirty();
  }
  const lat = () => (typeof vista === 'number' && E() && E().laterales[vista]) || null;
  const flat = L => (L ? L.pasos.flatMap((p, g) => p.lineas.map((l, i) => ({ g, i, l }))) : []);
  const secTxt = l => Ins.secTxt(l), secCorto = l => Ins.secCorto(l);

  /* ---- terminales: pino o doble (otro tramo del mismo cable llega al mismo borne) ---- */
  let TERM = { pino: {}, doble: {}, colores: {} };
  fetch('/static/terminales.json', { cache: 'no-cache' }).then(r => r.json()).then(t => { TERM = t; }).catch(() => { });
  function terminal(l, which) {
    const txt = which === 'o' ? l.origen : l.destino;
    if (!txt || (which === 'd' && !l.marca_d)) return null;
    const otros = flat(lat()).map(x => x.l).filter(x => x !== l && x.num === l.num && (x.origen === txt || x.destino === txt));
    const tipo = otros.length ? 'doble' : 'pino';
    const sec = String(l.secc || '').replace(',', '.');
    const pollera = (TERM[tipo] || {})[sec] || null;
    return { tipo, sec, pollera, hex: pollera ? ((TERM.colores || {})[pollera] || '#999') : null,
      txt: `${tipo === 'doble' ? 'Terminal doble' : 'Pino'} ${sec.replace('.', ',')} mm² · ${pollera ? 'pollera ' + pollera : 'color a definir'}` };
  }
  // adonde va la otra punta, en corto (para el rotulo al final del recorrido)
  const otraCorta = l => l.otra === 'misma bandeja' ? '' : l.otra === 'bandeja principal' ? 'A la bandeja principal' : l.otra === 'puerta / placa' ? 'A la puerta / placa'
    : /^bandeja lateral/.test(l.otra || '') ? 'A la ' + l.otra : l.otra || '';      // (cable a la otra lateral)
  const otraPill = l => l.otra === 'misma bandeja' ? '' :
    `<span class="pill e8-${l.viene_de_e6 ? 'e6' : 'fuera'}" title="${esc(l.viene_de_e6 ? 'La otra punta está en la bandeja principal y se cableó en E6: el cable ya está tirado, acá se conecta esta punta' : 'La otra punta va a ' + l.otra)}">${esc(l.viene_de_e6 ? 'viene de E6 (bandeja principal)' : l.otra)}</span>`;

  /* ---- dibujo (SVG en puntos del topográfico, con la y invertida, como en E6) ---- */
  const vbOf = b => [b[0], -b[3], b[2] - b[0], b[3] - b[1]];
  function imgTag(L, hd) {
    const r = L.region;
    return `<image href="/api/trabajo/${Ins.job}/e8/lateral/${vista}.png?v=${encodeURIComponent(D.generado || '')}${hd ? '&hd=1' : ''}" x="${r[0]}" y="${-r[3]}" width="${r[2] - r[0]}" height="${r[3] - r[1]}" preserveAspectRatio="none" opacity=".85"/>`;
  }
  function puntos(l) {
    if (l.ruta && l.ruta.length > 1) return l.ruta;
    const o = l.marca_o; if (!o) return null;
    return l.marca_d ? [o, l.marca_d] : [o];
  }
  function routeG(l, cls, k = 1, o = {}) {
    const ruta = puntos(l); if (!ruta) return '';
    const pts = ruta.map(p => [p[0], -p[1]]), n = pts.length;
    const col = Ins.LC(l.color), white = ['blanco', 'amarillo'].includes(norm(l.color));
    const w = (cls === 'sib' ? 1.3 : 1.8) * k, ro = (l.marca_o || [])[2], rd = (l.marca_d || [])[2];
    const st = pts[0], end = pts[n - 1];
    let s = `<g class="rt ${cls}${o.hecho ? ' hecho' : ''}" data-clave="${esc(l.clave)}"><title>${esc(l.num)} (${esc(secTxt(l))}): ${esc(l.origen)} → ${esc(l.destino)}${l.otra && l.otra !== 'misma bandeja' ? ' (' + esc(l.otra) + ')' : ''}${l.largo_mm ? ' · ≈' + l.largo_mm + ' mm' : ''}</title>`;
    if (n > 1) {
      const d = 'M' + pts.map(p => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('L');
      if (cls === 'cur') s += `<path d="${d}" class="halo" stroke-width="${6 * k}"/>`;
      if (white) s += `<path d="${d}" stroke="#333" stroke-width="${w + 1 * k}"/>`;
      s += `<path d="${d}" stroke="${col}" stroke-width="${w}"${cls === 'sib' ? ` stroke-dasharray="${f2(4 * k)} ${f2(1.6 * k)}"` : ''}/>`;
      s += Ins.ferrule(st, [pts[1][0] - st[0], pts[1][1] - st[1]], ro, terminal(l, 'o'), k);
      if (l.marca_d) s += Ins.ferrule(end, [pts[n - 2][0] - end[0], pts[n - 2][1] - end[1]], rd, terminal(l, 'd'), k);
    }
    s += Ins.mark(st, ro, 'ori', k, o.pulse);
    if (l.marca_d) s += Ins.mark(end, rd, 'des', k, o.pulse);
    else if (n > 1 && o.fin !== false) {
      const der = end[0] >= pts[n - 2][0];
      s += `<text x="${(end[0] + (der ? 3 : -3)).toFixed(1)}" y="${(end[1] + 2.5).toFixed(1)}" class="li" font-size="${f2(6 * Math.min(k, 1.2))}" text-anchor="${der ? 'start' : 'end'}">${esc(otraCorta(l))}</text>`;
    }
    if (o.lab && n > 1) {
      s += Ins.label(st, pts[1], Ins.termLen(ro) + 0.3, l.num, secCorto(l), o.lab, cls);
      if (l.marca_d) s += Ins.label(end, pts[n - 2], Ins.termLen(rd) + 0.3, l.num, secCorto(l), o.lab, cls);
    }
    return s + '</g>';
  }
  function boxOf(L, lines, pad = 22, minW = 120, minH = 80) {
    const pts = lines.flatMap(l => puntos(l) || []);
    if (!pts.length) return L.region.slice();
    let x0 = Math.min(...pts.map(p => p[0])) - pad, x1 = Math.max(...pts.map(p => p[0])) + pad;
    let y0 = Math.min(...pts.map(p => p[1])) - pad, y1 = Math.max(...pts.map(p => p[1])) + pad;
    if (x1 - x0 < minW) { const c = (x0 + x1) / 2; x0 = c - minW / 2; x1 = c + minW / 2; }
    if (y1 - y0 < minH) { const c = (y0 + y1) / 2; y0 = c - minH / 2; y1 = c + minH / 2; }
    return [x0, y0, x1, y1];
  }
  const sibs = (L, l) => flat(L).map(x => x.l).filter(x => x !== l && x.num === l.num);
  function thumb(L, l) {
    const vb = vbOf(boxOf(L, [l, ...sibs(L, l)]));
    return `<svg class="tsvg" viewBox="${vb.map(v => v.toFixed(1)).join(' ')}" preserveAspectRatio="xMidYMid meet">${imgTag(L)}${sibs(L, l).map(s => routeG(s, 'sib', 1.1, { fin: false })).join('')}${routeG(l, 'cur', 1.2)}</svg>`;
  }

  /* ---- pestaña ---- */
  async function open() {
    W().hidden = false;
    try { D = await Ins.load(); } catch (e) { D = null; }
    if (!D) return empty('Primero armá el <b>instructivo de cableado</b> (pestaña 🧰 Instructivo de cableado): la estación 8 sale del mismo topográfico.', false);
    if (!E() || !E().version) return empty('Este instructivo se armó antes de que existiera la vista de la estación 8 (o no se pudo armar). Tocá <b>↻ Regenerar</b> para armarla: se conservan las marcas de cableado de E6, los puntos ajustados y los cables quitados.', true);
    if (vista == null || (vista !== 'afuera' && !E().laterales[vista])) vista = E().laterales.length ? 0 : 'afuera';
    render();
  }
  function empty(html, regen) {
    $('#e8Main').hidden = true; const el = $('#e8Empty'); el.hidden = false;
    el.innerHTML = `<h2>Estación 8 · gabinete</h2><p class="muted">${html}</p>${(E() && E().avisos || []).map(a => `<p class="small warn-t">${esc(a)}</p>`).join('')}
      ${regen ? '<button class="btn primary" id="e8Regen">↻ Regenerar</button>' : ''}`;
    if (regen) $('#e8Regen').onclick = regenerar;
  }
  async function regenerar() {
    try { await api(`/api/trabajo/${Ins.job}/instructivo/regenerar`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }); }
    catch (e) { return toast(e.message, 5000); }
    $('#e8Empty').innerHTML = '<div class="proc-h"><div class="spinner" aria-hidden="true"></div><div><h2>Armando la estación 8…</h2><div class="muted" id="e8Msg"></div></div></div>';
    const job = Ins.job;
    const tick = async () => {
      if (W().hidden || Ins.job !== job) return;
      let st; try { st = await api(`/api/trabajo/${job}/instructivo/estado`); } catch (e) { return setTimeout(tick, 1500); }
      if ($('#e8Msg')) $('#e8Msg').textContent = st.mensaje || '…';
      if (st.estado === 'terminado') { Ins.reset(); return open(); }
      if (st.estado === 'error') return toast('Error: ' + (st.error || ''), 7000);
      setTimeout(tick, 900);
    };
    tick();
  }
  function render() {
    $('#e8Empty').hidden = true; $('#e8Main').hidden = false;
    const e8 = E(), H = hechos();
    const nLat = e8.laterales.reduce((a, L) => a + L.n, 0);
    const nAf = e8.afuera.reduce((a, g) => a + g.cables.length, 0);
    const claves = new Set([...e8.laterales.flatMap(L => flat(L).map(x => x.l.clave)), ...e8.afuera.flatMap(g => g.cables.map(x => x.clave))]);
    const hechosN = [...claves].filter(k => H.has(k)).length;
    $('#e8Vistas').innerHTML = e8.laterales.map((L, i) => `<button role="tab" data-v="${i}" class="${vista === i ? 'on' : ''}">${esc(L.nombre)} <span class="cnt">${flat(L).filter(x => H.has(x.l.clave)).length}/${L.n}</span></button>`).join('') +
      `<button role="tab" data-v="afuera" class="${vista === 'afuera' ? 'on' : ''}">Puerta y placa <span class="cnt">${e8.afuera.reduce((a, g) => a + g.cables.filter(x => H.has(x.clave)).length, 0)}/${nAf}</span></button>`;
    $('#e8Cablear').hidden = vista === 'afuera';
    $('#e8Info').innerHTML = `Estación <b>E8</b> (gabinete) · ${nLat} cables en ${e8.laterales.length === 1 ? 'la bandeja lateral' : e8.laterales.length + ' bandejas laterales'} · ${nAf} puntas en la puerta, la placa y la zona hidráulica · <b>${hechosN}</b> de ${claves.size} cableados` +
      (e8.campo ? ` · ${e8.campo} cables de campo no van en E8 (los conecta el cliente)` : '');
    $('#e8Bar').style.width = (claves.size ? hechosN / claves.size * 100 : 0) + '%';
    $('#e8Avisos').innerHTML = (e8.avisos || []).map(a => `<div class="note small">${esc(a)}</div>`).join('');
    $('#e8Lat').hidden = vista === 'afuera'; $('#e8Afuera').hidden = vista !== 'afuera';
    if (vista === 'afuera') renderAfuera(); else renderLat();
  }

  /* ---- vista de la bandeja lateral: mapa con todos los cables + pasos ---- */
  function renderLat() {
    const L = lat(); if (!L) { $('#e8Lat').innerHTML = '<p class="muted">No hay bandejas laterales en el topográfico.</p>'; return; }
    const H = hechos(); let n = 0;
    const exactos = L.exactos, tot = L.n;
    $('#e8Lat').innerHTML = `
      <div class="e8-mapa card"><div class="card-h"><h2>${esc(L.nombre)}</h2><span class="muted small">${tot} cables · ${exactos === tot ? 'todos con el punto del borne' : `${exactos} de ${tot} con el punto del borne`}${L.sin_canaletas ? ' · sin canaletas leídas: no hay recorrido' : ''}${L.sin_riel ? ' · sin riel dibujado: aparato por aparato' : ''}</span></div>
        <svg class="tsvg" id="e8Mapa" viewBox="${vbOf(L.region).map(v => v.toFixed(1)).join(' ')}" preserveAspectRatio="xMidYMid meet">${imgTag(L)}
          ${flat(L).map(x => routeG(x.l, 'sib', 0.9, { hecho: H.has(x.l.clave), fin: false })).join('')}<g id="e8Sel"></g></svg>
        <p class="muted small">Pasá el mouse por un cable de la lista para verlo en la bandeja. Los cables que vienen de la bandeja principal ya están tirados desde E6: acá se conecta la punta de la lateral.</p></div>
      <div class="e8-pasos">${L.pasos.map((p, g) => `<div class="grp"><div class="grp-h"><b class="e8-pt">${esc(p.titulo)}</b>
          <span class="muted small">${p.lineas.filter(l => H.has(l.clave)).length}/${p.lineas.length}</span></div>
        ${p.lineas.map((l, i) => cardLat(L, l, g, i, ++n, H.has(l.clave))).join('')}</div>`).join('')}</div>`;
  }
  function cardLat(L, l, g, i, n, ok) {
    const aprox = !l.exacto_o || (l.marca_d && !l.exacto_d);
    const t = terminal(l, 'o'), td = terminal(l, 'd');
    return `<div class="cab ${ok ? 'ok' : ''}" data-g="${g}" data-i="${i}" data-clave="${esc(l.clave)}">
      <div class="cab-n">${n}</div>
      <div class="cab-topo" title="Cablear desde este cable (visor)">${thumb(L, l)}</div>
      <div class="cab-body">
        <div class="cab-t mono"><b>${esc(l.num)}</b> ${swatch(l.color)} <span class="secc">${esc(secTxt(l))}</span> ${otraPill(l)}
          ${aprox ? '<span class="pill warn" title="Punto del borne aproximado (no está en el mapeo)">punto aprox.</span>' : ''}
          ${l.largo_mm ? `<span class="muted small">≈${l.largo_mm} mm</span>` : ''}</div>
        <div class="cab-od mono"><span>${esc(l.origen)}</span><span class="arr">→</span><span>${esc(l.destino)}</span></div>
        <div class="cab-term small">${Ins.termChip(t)}${td ? ` <span class="arr">→</span> ${Ins.termChip(td)}` : ` <span class="muted">→ ${esc(l.otra === 'bandeja principal' ? 'ya cableado en E6' : l.otra)}</span>`}</div>
      </div>
      <div class="cab-acts">
        <label class="chk small" title="Marcar como cableado"><input type="checkbox" data-a="ok" ${ok ? 'checked' : ''}> OK</label>
        <div><button class="mini" data-a="ver" title="Cablear desde este cable (visor)">▶</button>
          <button class="mini" data-a="plano" title="Ver en el plano eléctrico">⚡</button></div>
      </div></div>`;
  }
  function resaltar(clave) {
    const L = lat(), g = $('#e8Sel'); if (!L || !g) return;
    const l = clave && flat(L).map(x => x.l).find(x => x.clave === clave);
    g.innerHTML = l ? routeG(l, 'cur', 1.2) : '';
  }

  /* ---- puerta y placa: aparato por aparato ---- */
  function renderAfuera() {
    const H = hechos(), gs = E().afuera;
    const zonas = [...new Set(gs.map(g => g.zona))];
    $('#e8Afuera').innerHTML = gs.length ? zonas.map(z => `<h2 class="e8-zona">${z === 'puerta / placa' ? 'Puerta y placa' : 'Zona hidráulica (placa principal)'}</h2>
      ${z === 'puerta / placa' ? '<p class="muted small">Aparatos que no están en ninguna bandeja del topográfico (puerta, placa, botones, solenoides). Cada borne con su cable y adónde va la otra punta.</p>'
        : '<p class="muted small">Lo que queda del otro lado de la placa divisoria (regla del taller: se cablea en E8), con los empalmes del sensor de nivel.</p>'}
      <div class="e8-aps">${gs.filter(g => g.zona === z).map(g => `<div class="card e8-ap">
        <div class="card-h"><h3 class="mono">${esc(g.tag)}</h3><span class="muted small">${g.cables.filter(x => H.has(x.clave)).length}/${g.cables.length}</span></div>
        <table class="e8-tab"><thead><tr><th></th><th>Borne</th><th>Cable</th><th>Va a</th><th></th></tr></thead><tbody>
        ${g.cables.map(x => `<tr class="${H.has(x.clave) ? 'ok' : ''}" data-clave="${esc(x.clave)}">
          <td><input type="checkbox" data-a="ok" ${H.has(x.clave) ? 'checked' : ''} aria-label="Cable ${esc(x.num)} cableado"></td>
          <td class="mono"><b>${esc(x.pin || x.borne)}</b></td>
          <td class="mono">${esc(x.num)} ${swatch(x.color)} <span class="secc">${esc(secTxt(x))}</span></td>
          <td class="mono">${esc(x.otra)} <span class="muted small">· ${esc(x.otra_donde)}</span></td>
          <td><button class="mini" data-a="plano" data-num="${esc(x.num)}" title="Ver en el plano eléctrico">⚡</button></td></tr>`).join('')}
        </tbody></table></div>`).join('')}</div>`).join('') : '<p class="muted">No hay cables a la puerta ni a la placa.</p>';
  }

  /* ---- visor "cablear de a uno" de la bandeja lateral ---- */
  const V = { k: 0, vb: null, anim: null, drag: null };
  const F = () => flat(lat());
  function openViewer(k) {
    const f = F(); if (!f.length) return toast('No hay cables en esta bandeja');
    const H = hechos();
    if (k == null) { k = f.findIndex(x => !H.has(x.l.clave)); if (k < 0) k = 0; }
    V.k = Math.max(0, Math.min(k, f.length - 1));
    $('#e8Viewer').hidden = false; document.body.style.overflow = 'hidden';
    if (document.activeElement) document.activeElement.blur();
    renderList(); draw(true);
  }
  function closeViewer() { $('#e8Viewer').hidden = true; document.body.style.overflow = ''; if (!W().hidden) render(); }
  function draw(first) {
    const L = lat(), f = F(); if (!f.length) return closeViewer();
    V.k = Math.max(0, Math.min(V.k, f.length - 1));
    const { g, l } = f[V.k], H = hechos(), ss = sibs(L, l);
    $('#e8vPos').textContent = `${V.k + 1} / ${f.length}`;
    $('#e8vGrp').textContent = `${L.nombre} · ${L.pasos[g].titulo}`;
    $('#e8vNum').innerHTML = `<span class="mono">${esc(l.num)}</span> ${swatch(l.color)} <span class="secc big">${esc(secTxt(l))}</span>`;
    $('#e8vOrig').textContent = l.origen;
    $('#e8vDest').innerHTML = esc(l.destino) + ' ' + otraPill(l);
    $('#e8vLen').textContent = l.largo_mm ? `≈ ${l.largo_mm} mm en la lateral` : '';
    $('#e8vOk').checked = H.has(l.clave);
    $('#e8vBar').style.width = (f.filter(x => H.has(x.l.clave)).length / f.length * 100) + '%';
    const target = vbOf(roomForLupas(boxOf(L, [l, ...ss], 36, 200, 140)));
    const fs = Ins.fontFor('#e8vSvg', target, 14);
    $('#e8vSvg').innerHTML = imgTag(L, true) + ss.map(s => routeG(s, 'sib', 1.3, { lab: fs })).join('') + routeG(l, 'cur', 1.6, { lab: fs, pulse: true });
    lupas(L, l, ss);
    camera(target, first ? 0 : 420);
    markList();
  }
  function roomForLupas(b) {
    const s = $('#e8vSvg').getBoundingClientRect(); if (!s.width || !s.height) return b;
    const f = Math.min(0.45, ($('#e8Viewer .cv-lupas').offsetWidth + 24) / s.width), A = s.width / s.height;
    const Wd = b[2] - b[0], H = b[3] - b[1], dispW = Math.max(Wd, H * A);
    let e = Math.max(0, 2 * dispW * f - (dispW - Wd));
    if ((Wd + e) / H > A) e = Wd * f / (1 - f);
    return [b[0], b[1], b[2] + e, b[3]];
  }
  function lupas(L, l, ss) {
    const Wd = 30, H = Wd * 175 / 250, r = puntos(l) || [];
    const set = (id, p, show) => {
      const s = $(id); s.parentElement.hidden = !show; if (!show) return;
      s.setAttribute('viewBox', `${(p[0] - Wd / 2).toFixed(2)} ${(-p[1] - H / 2).toFixed(2)} ${Wd} ${H}`);
      s.innerHTML = imgTag(L, true) + ss.map(x => routeG(x, 'sib', 0.4, { lab: 1.5, fin: false })).join('') + routeG(l, 'cur', 0.45, { lab: 1.6, fin: false });
    };
    const to = terminal(l, 'o'), td = terminal(l, 'd');
    set('#e8vLupaO', r[0] || [0, 0], !!r.length); $('#e8vLupaOt').textContent = `${l.num} · ${l.origen} · ${to ? to.txt : secTxt(l)}`;
    set('#e8vLupaD', l.marca_d || [0, 0], !!l.marca_d); $('#e8vLupaDt').textContent = `Destino · ${l.num} · ${l.destino} · ${td ? td.txt : secTxt(l)}`;
  }
  function camera(target, ms) {
    cancelAnimationFrame(V.anim);
    const from = V.vb || target, t0 = performance.now();
    const ease = t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const step = now => {
      const t = ms ? Math.min(1, (now - t0) / ms) : 1, e = ease(t);
      V.vb = from.map((v, i) => v + (target[i] - v) * e);
      $('#e8vSvg').setAttribute('viewBox', V.vb.map(v => v.toFixed(2)).join(' '));
      if (t < 1) V.anim = requestAnimationFrame(step);
    };
    V.anim = requestAnimationFrame(step);
  }
  // pasar al siguiente marca el cable actual como cableado (como en E6); volver no desmarca
  function go(d, marca = d > 0) {
    const f = F(); if (!f.length) return;
    if (marca && !esHecho(f[V.k].l.clave)) {
      marcar(f[V.k].l.clave, true);
      if (f.every(x => esHecho(x.l.clave))) toast(`¡${lat().nombre} cableada! Los ${f.length} cables están marcados.`, 6000);
    }
    V.k = Math.max(0, Math.min(f.length - 1, V.k + d));
    draw();
  }
  function toggleOk(adv) {
    const f = F(), l = f[V.k].l, on = !esHecho(l.clave);
    marcar(l.clave, on);
    if (adv && on && V.k < f.length - 1) go(1, false); else draw();
  }
  function svgPoint(e) {
    const svg = $('#e8vSvg'), r = svg.getBoundingClientRect(), vb = V.vb;
    const s = Math.max(vb[2] / r.width, vb[3] / r.height);
    const ox = (r.width * s - vb[2]) / 2, oy = (r.height * s - vb[3]) / 2;
    return [vb[0] - ox + (e.clientX - r.left) * s, vb[1] - oy + (e.clientY - r.top) * s, s];
  }
  function renderList() {
    const q = norm($('#e8vQ').value.trim()), f = F(), L = lat(), H = hechos();
    let html = '', lastG = -1;
    f.forEach((x, k) => {
      const l = x.l;
      if (q && !norm(`${l.num} ${l.origen} ${l.destino} ${l.color} ${l.secc}`).includes(q)) return;
      if (x.g !== lastG) { html += `<div class="cv-gh">${esc(L.pasos[x.g].titulo)}</div>`; lastG = x.g; }
      html += `<div class="vs-it cv-it${H.has(l.clave) ? ' seen' : ''}" data-k="${k}" role="option" title="${esc(l.origen)} → ${esc(l.destino)}">
        <input type="checkbox" data-ok ${H.has(l.clave) ? 'checked' : ''} aria-label="Cable ${esc(l.num)} cableado">
        <span class="n">${esc(l.num)}</span>${swatch(l.color)}<span class="sec">${esc(secTxt(l))}</span>
        <span class="od mono">${esc(l.origen)} → ${esc(l.destino)}</span></div>`;
    });
    $('#e8vList').innerHTML = html || '<div class="vs-empty muted small">Ningún cable coincide.</div>';
    markList();
  }
  function markList() {
    if ($('#e8Viewer').hidden) return;
    const f = F(), H = hechos(); let cur = null;
    for (const b of $('#e8vList').querySelectorAll('.cv-it')) {
      const l = f[+b.dataset.k]?.l; if (!l) continue;
      b.classList.toggle('seen', H.has(l.clave)); b.querySelector('[data-ok]').checked = H.has(l.clave);
      const on = +b.dataset.k === V.k; b.classList.toggle('on', on); b.setAttribute('aria-selected', on);
      if (on) cur = b;
    }
    $('#e8vCnt').textContent = `${f.filter(x => H.has(x.l.clave)).length} de ${f.length} cableados`;
    if (cur && !$('#e8vSide').hidden) cur.scrollIntoView({ block: 'nearest' });
  }
  function setSide(on) {
    $('#e8vSide').hidden = !on; $('#e8vSideBtn').classList.toggle('on', on); $('#e8vSideBtn').setAttribute('aria-pressed', on);
    try { localStorage.setItem('listadoE8', on ? '1' : '0'); } catch (e) { }
    if (!$('#e8Viewer').hidden) draw(true);
  }
  function aFuncional(num) {
    const occ = S.byNum[num] || [];
    if (!occ.length) return toast(`El cable ${num} no tiene etiquetas en el funcional`);
    $('#e8Viewer').hidden = true; document.body.style.overflow = '';
    openCable(num, 0);
  }

  /* ---- imprimir: la bandeja lateral paso por paso y la puerta / placa en tablas ---- */
  function imprimir() {
    const w = window.open('', '_blank'); if (!w) return toast('El navegador bloqueó la ventana de impresión');
    const base = location.origin, e8 = E(), vSel = vista;
    let html = '';
    e8.laterales.forEach((L, i) => {
      vista = i; let n = 0;
      html += `<h2>${esc(L.nombre)}</h2>` + L.pasos.map(p => `<h3>${esc(p.titulo)}</h3><div class="g">${p.lineas.map(l => `<div class="c"><div class="n">${++n}</div>${thumb(L, l).replace(/href="\//g, `href="${base}/`)}
        <div class="t"><b>${esc(l.num)}</b>: ${esc(l.cable)} · ${esc(secTxt(l))}<br>${esc(l.origen)} → ${esc(l.destino)}${l.otra !== 'misma bandeja' ? `<br><span style="color:#555">${esc(l.viene_de_e6 ? 'viene de la bandeja principal (E6)' : l.otra)}</span>` : ''}</div><div class="ok">☐</div></div>`).join('')}</div>`).join('');
    });
    vista = vSel;
    html += `<h2>Puerta, placa y zona hidráulica</h2><div class="g">` + e8.afuera.map(g => `<table><caption>${esc(g.tag)} <span>(${esc(g.zona)})</span></caption>
      ${g.cables.map(x => `<tr><td>☐</td><td><b>${esc(x.pin || x.borne)}</b></td><td>${esc(x.num)} · ${esc(secTxt(x))}</td><td>→ ${esc(x.otra)} <span style="color:#666">(${esc(x.otra_donde)})</span></td></tr>`).join('')}</table>`).join('') + '</div>';
    w.document.write(`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Estación 8 — ${esc(S.res.nombre)}</title>
      <style>body{font:12px/1.35 "Segoe UI",Arial,sans-serif;margin:16px;color:#111} h1{font-size:18px;margin:0 0 4px} h2{font-size:15px;margin:16px 0 6px;color:#1f5fbf} h3{font-size:13px;margin:10px 0 4px}
      .m{color:#555;margin-bottom:10px} .g{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
      .c{display:flex;gap:10px;border:1px solid #ccc;border-radius:8px;padding:6px;page-break-inside:avoid;align-items:center}
      .n{width:26px;height:26px;border-radius:50%;background:#1f5fbf;color:#fff;display:grid;place-items:center;font-weight:700;flex:none;font-size:11px}
      svg{width:170px;height:115px;border:1px solid #ddd;border-radius:6px;flex:none} ${Ins.PRINT_CSS}
      .t{font:12px Consolas,monospace} .t b{font-size:13px} .ok{margin-left:auto;font-size:14px}
      table{border-collapse:collapse;font:12px Consolas,monospace;page-break-inside:avoid;width:100%} caption{text-align:left;font:700 13px "Segoe UI",Arial;padding:4px 0} caption span{font-weight:400;color:#666}
      td{border-bottom:1px solid #ddd;padding:2px 6px}</style></head><body>
      <h1>Estación 8 · gabinete</h1><div class="m">${esc(S.res.nombre)} · ${new Date().toLocaleDateString()}</div>${html}
      <script>window.onload=()=>setTimeout(()=>print(),600)<\/script></body></html>`);
    w.document.close();
  }

  function init() {
    $('#e8Vistas').addEventListener('click', e => { const b = e.target.closest('[data-v]'); if (!b) return; vista = b.dataset.v === 'afuera' ? 'afuera' : +b.dataset.v; render(); });
    $('#e8Cablear').addEventListener('click', () => openViewer(null));
    $('#e8Print').addEventListener('click', imprimir);
    $('#e8Lat').addEventListener('click', e => {
      const cab = e.target.closest('.cab'); if (!cab) return;
      const L = lat(), l = L.pasos[+cab.dataset.g].lineas[+cab.dataset.i];
      const k = F().findIndex(x => x.l === l);
      if (e.target.closest('.cab-topo')) return openViewer(k);
      const b = e.target.closest('[data-a]'); if (!b) return;
      if (b.dataset.a === 'ok') { marcar(l.clave, b.checked); render(); }
      if (b.dataset.a === 'ver') openViewer(k);
      if (b.dataset.a === 'plano') aFuncional(l.num);
    });
    $('#e8Lat').addEventListener('mouseover', e => { const cab = e.target.closest('.cab'); resaltar(cab ? cab.dataset.clave : null); });
    $('#e8Afuera').addEventListener('click', e => {
      const b = e.target.closest('[data-a]'); if (!b) return;
      if (b.dataset.a === 'ok') { marcar(b.closest('tr').dataset.clave, b.checked); render(); }
      if (b.dataset.a === 'plano') aFuncional(b.dataset.num);
    });
    // visor
    $('#e8vClose').addEventListener('click', closeViewer);
    $('#e8vPrev').addEventListener('click', () => go(-1));
    $('#e8vNext').addEventListener('click', () => go(1));
    $('#e8vFit').addEventListener('click', () => camera(vbOf(lat().region), 350));
    $('#e8vFocus').addEventListener('click', () => draw());
    $('#e8vOk').addEventListener('change', () => toggleOk(true));
    $('#e8vPlano').addEventListener('click', () => aFuncional(F()[V.k].l.num));
    $('#e8vSideBtn').addEventListener('click', () => setSide($('#e8vSide').hidden));
    { let on = true; try { on = localStorage.getItem('listadoE8') !== '0'; } catch (e) { } $('#e8vSide').hidden = !on; $('#e8vSideBtn').classList.toggle('on', on); }
    $('#e8vList').addEventListener('click', e => {
      const it = e.target.closest('.cv-it'); if (!it) return;
      const k = +it.dataset.k, l = F()[k].l;
      if (e.target.matches('[data-ok]')) { marcar(l.clave, e.target.checked); if (k === V.k) $('#e8vOk').checked = e.target.checked; markList(); return; }
      V.k = k; draw();
    });
    let qT; $('#e8vQ').addEventListener('input', () => { clearTimeout(qT); qT = setTimeout(renderList, 80); });
    $('#e8vQ').addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); const it = $('#e8vList .cv-it'); if (it) { V.k = +it.dataset.k; draw(); } e.target.blur(); }
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); if (e.target.value) { e.target.value = ''; renderList(); } else e.target.blur(); }
    });
    const svg = $('#e8vSvg');
    svg.addEventListener('wheel', e => {
      e.preventDefault(); if (!V.vb) return;
      const [px, py] = svgPoint(e), f = Math.pow(1.0015, e.deltaY);
      V.vb = [px - (px - V.vb[0]) * f, py - (py - V.vb[1]) * f, V.vb[2] * f, V.vb[3] * f];
      svg.setAttribute('viewBox', V.vb.join(' '));
    }, { passive: false });
    svg.addEventListener('pointerdown', e => { V.drag = { x: e.clientX, y: e.clientY, vb: V.vb.slice(), s: svgPoint(e)[2] }; svg.setPointerCapture(e.pointerId); svg.classList.add('drag'); });
    svg.addEventListener('pointermove', e => { if (!V.drag) return; const d = V.drag;
      V.vb = [d.vb[0] - (e.clientX - d.x) * d.s, d.vb[1] - (e.clientY - d.y) * d.s, d.vb[2], d.vb[3]]; svg.setAttribute('viewBox', V.vb.join(' ')); });
    svg.addEventListener('pointerup', () => { V.drag = null; svg.classList.remove('drag'); });
    document.addEventListener('keydown', e => {
      if ($('#e8Viewer').hidden) return;
      if (e.target.isContentEditable || e.target.tagName === 'INPUT' && e.target.type !== 'checkbox') return;
      const keys = { ArrowRight: () => go(1), ArrowLeft: () => go(-1), Escape: closeViewer, ' ': () => toggleOk(true), Enter: () => toggleOk(true),
        '0': () => camera(vbOf(lat().region), 350), f: () => draw(), l: () => setSide($('#e8vSide').hidden) };
      if (keys[e.key]) { e.preventDefault(); keys[e.key](); }
    });
  }
  return { open, init, hide: () => { W().hidden = true; } };
})();
E8.init();
