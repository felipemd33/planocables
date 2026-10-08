'use strict';
/* Pestaña "Estación 8 (gabinete)": lo que se cablea con la bandeja ya montada.
   - Bandeja lateral (izquierda en el PAE): los cables de sus aparatos sobre su vista del topográfico, en orden de cableado,
     con el visor "cablear de a uno" (como el instructivo de E6).
   - Puerta y placa: aparato por aparato, borne por borne, con adónde va la otra punta.
   - 🧭 Entrada / salida (tecla S, también desde el visor): por dónde entran a cada lateral los cables del fondo, por
     dónde salen los que siguen a la puerta (en la lateral de la bisagra) y el lado de la bisagra; asistente la primera
     vez (ver «ENTRADA / SALIDA» más abajo).
   Los datos vienen en ins.estacion8 (programa/estacion8.py); las marcas de cableado van en ins.estacion8.hechos y lo
   elegido de la entrada / salida en ins.estacion8.recorridos. */
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
    const r = L.region, i = E() ? E().laterales.indexOf(L) : -1;
    return `<image href="/api/trabajo/${Ins.job}/e8/lateral/${i < 0 ? vista : i}.png?v=${encodeURIComponent(D.generado || '')}${hd ? '&hd=1' : ''}" x="${r[0]}" y="${-r[3]}" width="${r[2] - r[0]}" height="${r[3] - r[1]}" preserveAspectRatio="none" opacity=".85"/>`;
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
    // la primera vez (o con un topografico nuevo): el asistente pregunta la bisagra y la entrada de cada lateral
    if (E().recorridos && E().recorridos.preguntar) setTimeout(() => { try { if (!W().hidden) asistente(); } catch (e) { console.error(e); } }, 0);
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
    $('#e8Entrada').hidden = vista === 'afuera' || !lat() || !(lat().ductos || []).length || !salientes(lat()).length;
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
    const ent = !L.sin_canaletas && salientes(L).length ? entradaTxt(L) : '';
    $('#e8Lat').innerHTML = `
      <div class="e8-mapa card"><div class="card-h"><h2>${esc(L.nombre)}</h2><span class="muted small">${tot} cables · ${exactos === tot ? 'todos con el punto del borne' : `${exactos} de ${tot} con el punto del borne`}${L.sin_canaletas ? ' · sin canaletas leídas: no hay recorrido' : ''}${L.sin_riel ? ' · sin riel dibujado: aparato por aparato' : ''}</span></div>
        <svg class="tsvg" id="e8Mapa" viewBox="${vbOf(L.region).map(v => v.toFixed(1)).join(' ')}" preserveAspectRatio="xMidYMid meet">${imgTag(L)}
          ${flat(L).map(x => routeG(x.l, 'sib', 0.9, { hecho: H.has(x.l.clave), fin: false })).join('')}${flechas(L, uMapa(L))}<g id="e8Sel"></g></svg>
        ${ent ? `<p class="small e8-ent">${ent} <button class="linkbtn" data-a="entrada" title="Elegir por dónde entran y salen los cables de esta bandeja lateral (S)">🧭 Cambiar</button></p>` : ''}
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
    $('#e8vSvg').innerHTML = imgTag(L, true) + flechas(L, 0.7 * uMapa(L)) + ss.map(s => routeG(s, 'sib', 1.3, { lab: fs })).join('') + routeG(l, 'cur', 1.6, { lab: fs, pulse: true });
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

  /* ---- ENTRADA / SALIDA de cada bandeja lateral y BISAGRA de la puerta (ins.estacion8.recorridos) ----
     Por dónde entran a la lateral los cables que vienen de la bandeja principal (E6), de la otra lateral o de la zona
     hidráulica («Entrada», del lado del fondo) y, en la lateral del lado de la bisagra, por dónde salen los que siguen a
     la puerta («Salida a la puerta»). Se marcan con clics sobre el dibujo: los puntos por donde pasan, en orden, y el
     último es por donde entran (o salen). Un grupo de cables elegidos manda sobre los dos. Sin marcar vale la propuesta
     (a la altura de la salida de E6 o la regla del taller), que se ve con una flecha.
     recorridos = {preguntar, bisagra: 'izq' | 'der' | null, vistas: {<L.clave_vista>: {entrada, puerta, grupos: [{id,
     nombre, cables, puntos}]}}}; el servidor rutea igual al regenerar (estacion8.rutear_lineas) y la vista previa es
     POST /e8/recorridos. ASISTENTE: la primera vez que se abre la estación 8 (o con un topográfico nuevo) pregunta el lado
     de la bisagra y la entrada de cada lateral. */
  const X = { li: 0, act: 0, modo: null, nuevo: false, vb: null, drag: null, rect: null, volver: null, foco: null, seq: 0, t: null, raf: 0, asis: null };
  const salientes = L => flat(L).map(x => x.l).filter(l => !l.marca_d);
  const ptsOf = a => (Array.isArray(a) ? a : []);
  const lado = b => (b === 'der' ? 'derecha' : 'izquierda');
  function REC() {
    const e = E();
    if (!e.recorridos || typeof e.recorridos !== 'object') e.recorridos = { preguntar: false, bisagra: null, vistas: {} };
    if (!e.recorridos.vistas || typeof e.recorridos.vistas !== 'object') e.recorridos.vistas = {};
    return e.recorridos;
  }
  function vrec(L) {
    const r = REC(), k = L.clave_vista || L.lado + '|';
    const v = r.vistas[k] = (r.vistas[k] && typeof r.vistas[k] === 'object') ? r.vistas[k] : {};
    for (const c of ['entrada', 'puerta', 'grupos']) if (!Array.isArray(v[c])) v[c] = [];
    return v;
  }
  const vrecVer = L => { const v = ((E() && E().recorridos) || {}).vistas || {}; return v[L.clave_vista || L.lado + '|'] || {}; };
  // grupos del panel: la entrada, la salida a la puerta (solo en la lateral de la bisagra) y los de cables elegidos
  function gruposEd(L) {
    const v = vrec(L), out = [{ id: 'entrada', nombre: 'Entrada (desde el fondo)', tipo: 'entrada', ref: v }];
    if (L.bisagra) out.push({ id: 'puerta', nombre: 'Salida a la puerta', tipo: 'puerta', ref: v });
    v.grupos.forEach(g => out.push({ id: g.id, nombre: g.nombre, tipo: 'seleccion', ref: g }));
    return out;
  }
  const puntosG = G => ptsOf(G.tipo === 'seleccion' ? G.ref.puntos : G.ref[G.tipo]);
  const setPuntos = (G, p) => { if (G.tipo === 'seleccion') G.ref.puntos = p; else G.ref[G.tipo] = p; };
  const propDe = (L, tipo) => (tipo === 'puerta' ? L.puerta_propuesta : tipo === 'entrada' ? L.entrada_propuesta : null) || null;
  const conRec = L => vrec(L).grupos.filter(g => ptsOf(g.puntos).length);
  // el grupo que manda en el recorrido del cable (como estacion8.rutear_lineas)
  function grupoDe(L, l) {
    const g = conRec(L).find(g => (g.cables || []).includes(l.num));
    return g ? gruposEd(L).find(G => G.ref === g) : gruposEd(L).find(G => G.tipo === (l.sale || 'entrada')) || null;
  }
  function miembros(L, G) {
    if (!G) return [];
    const sal = salientes(L);
    if (G.tipo === 'seleccion') return sal.filter(l => (G.ref.cables || []).includes(l.num));
    const tom = new Set(conRec(L).flatMap(g => g.cables || []));
    return sal.filter(l => (l.sale || 'entrada') === G.tipo && !tom.has(l.num));
  }
  // por donde entran (o salen): el ultimo punto elegido, o la propuesta
  function finDe(L, tipo) {
    const P = ptsOf(vrecVer(L)[tipo]);
    return P.length ? { p: P[P.length - 1], eleg: true } : (propDe(L, tipo) ? { p: propDe(L, tipo), eleg: false } : null);
  }
  // flechas de la entrada (o de la salida a la puerta): el punto elegido y, sin elegir (o para los que no llegan), los
  // finales de las rutas que siguen la propuesta (canaletas partidas: puede haber mas de uno)
  function finesDe(L, tipo) {
    const v = vrecVer(L), P = ptsOf(v[tipo]), out = [], vistos = new Set();
    const tom = new Set(ptsOf(v.grupos).filter(g => ptsOf(g.puntos).length).flatMap(g => g.cables || []));
    const add = (p, eleg) => { const k = `${Math.round(p[0] * 2)}|${Math.round(p[1] * 2)}`; if (!vistos.has(k)) { vistos.add(k); out.push({ p, eleg }); } };
    if (P.length) add(P[P.length - 1], true);
    for (const l of salientes(L)) {
      if ((l.sale || 'entrada') !== tipo || tom.has(l.num) || !(l.ruta && l.ruta.length > 1) || (P.length && !l.no_llega)) continue;
      add(l.ruta[l.ruta.length - 1], false);
    }
    if (!out.length && propDe(L, tipo)) add(propDe(L, tipo), false);
    return out;
  }
  function entradaTxt(L) {
    const e = finDe(L, 'entrada'), s = L.bisagra ? finDe(L, 'puerta') : null;
    const t = e ? `Entrada: <b>${e.eleg ? 'elegida' : 'propuesta'}</b>` : 'Entrada: sin canaletas para rutear';
    return t + (s ? ` · salida a la puerta: <b>${s.eleg ? 'elegida' : 'propuesta'}</b> (la bisagra está de este lado)` : '');
  }
  // flecha roja como la de la foto del taller: el sentido del cable va del fondo hacia la puerta (la entrada con la punta
  // en el punto, la salida a la puerta con la cola en el punto); la propuesta va punteada
  function flecha(p, dir, u, txt, dentro, prop) {
    const Lf = 34 * u, h = 7 * u, y = -p[1];
    const x0 = dentro ? p[0] - dir * Lf : p[0], x1 = dentro ? p[0] : p[0] + dir * Lf, hx = x1 - dir * h * 1.4;
    return `<g class="e8-flecha${prop ? ' prop' : ''}"><title>${esc(txt)}${prop ? ' (propuesta)' : ''}</title>
      <path d="M${f2(x0)} ${f2(y)}L${f2(hx)} ${f2(y)}" stroke-width="${f2(2.6 * u)}"${prop ? ` stroke-dasharray="${f2(5 * u)} ${f2(3 * u)}"` : ''}/>
      <path class="punta" d="M${f2(x1)} ${f2(y)}L${f2(hx)} ${f2(y - h)}L${f2(hx)} ${f2(y + h)}Z"/>
      <text x="${f2((x0 + x1) / 2)}" y="${f2(y - h - 3 * u)}" font-size="${f2(10 * u)}" text-anchor="middle" stroke-width="${f2(2.4 * u)}">${esc(txt)}</text></g>`;
  }
  const sentido = L => (L.hacia === 'izq' ? 1 : -1);
  function flechas(L, u) {
    if (!L || L.sin_canaletas || !salientes(L).length) return '';
    return finesDe(L, 'entrada').map(x => flecha(x.p, sentido(L), u, 'Entrada', true, !x.eleg)).join('')
      + (L.bisagra ? finesDe(L, 'puerta').map(x => flecha(x.p, sentido(L), u, 'A la puerta', false, !x.eleg)).join('') : '');
  }
  const uMapa = L => Math.max((L.region[2] - L.region[0]) / 480, (L.region[3] - L.region[1]) / 640);

  function abrirEd(o = {}) {
    const e8 = E(); if (!e8) return;
    const li = o.li != null ? o.li : (typeof vista === 'number' ? vista : 0), L = e8.laterales[li];
    if (!L) return toast('No hay bandejas laterales en el topográfico');
    if (!(L.ductos || []).length) return toast('Esta bandeja lateral no tiene canaletas leídas: no se puede elegir la entrada', 5000);
    if (!salientes(L).length) return toast('Ningún cable entra ni sale de esta bandeja lateral');
    X.li = li; X.volver = o.volver ?? null; X.modo = null; X.rect = null; X.foco = o.num || null; X.act = 0;
    const l = o.num && salientes(L).find(x => x.num === o.num);
    const g = l && grupoDe(L, l);
    if (g) X.act = Math.max(0, gruposEd(L).findIndex(G => G.ref === g.ref && G.tipo === g.tipo));
    $('#e8sViewer').hidden = false; document.body.style.overflow = 'hidden';
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    $('#e8sVolver').hidden = X.volver == null;
    $('#e8sQ').value = '';
    cargarLat();
  }
  function cargarLat() {
    const L = E().laterales[X.li];
    $('#e8sSvg').innerHTML = imgTag(L, true) + '<g id="e8sRutas"></g><g id="e8sMarcas"></g>';
    X.vb = vbOf(L.region); $('#e8sSvg').setAttribute('viewBox', X.vb.map(f2).join(' '));
    edRender();
  }
  function cerrarEd() {
    if ($('#e8sViewer').hidden) return;
    if (X.asis) return terminarAsis();
    X.modo = null;
    $('#e8sViewer').hidden = true; document.body.style.overflow = '';
    if (X.volver != null) { vista = X.li; openViewer(X.volver); }
    else if (!W().hidden) render();
  }

  /* asistente: una sola vez (la bisagra y la entrada de cada lateral con canaletas y cables que entran o salen) */
  function asistente() {
    const e8 = E(); if (!e8 || !(e8.recorridos && e8.recorridos.preguntar) || !$('#e8sViewer').hidden || !$('#e8Viewer').hidden) return;
    const lats = e8.laterales.map((L, i) => i).filter(i => (e8.laterales[i].ductos || []).length && salientes(e8.laterales[i]).length);
    if (!lats.length) { REC().preguntar = false; Ins.dirty(); return; }
    X.asis = { pasos: ['bisagra', ...lats], i: 0, bis: REC().bisagra || e8.bisagra_propuesta || 'izq' };
    abrirEd({ li: lats[0] });
    pasoAsis();
  }
  function pasoAsis() {
    const p = X.asis.pasos[X.asis.i];
    if (p === 'bisagra') {
      const i = E().laterales.findIndex(L => L.lado === (X.asis.bis === 'der' ? 'LD' : 'LI') && (L.ductos || []).length);
      if (i >= 0 && i !== X.li) { X.li = i; X.act = 0; X.modo = null; return cargarLat(); }
      X.modo = null; return edRender();
    }
    if (p !== X.li) { X.li = p; X.act = 0; X.modo = 'recorrido'; X.nuevo = true; return cargarLat(); }
    X.act = 0; X.modo = 'recorrido'; X.nuevo = true; edRender();
  }
  function sigAsis() {
    if (!X.asis) return;
    if (X.asis.pasos[X.asis.i] === 'bisagra' && REC().bisagra !== X.asis.bis) { REC().bisagra = X.asis.bis; rutear(); }
    if (X.asis.i < X.asis.pasos.length - 1) { X.asis.i++; return pasoAsis(); }
    terminarAsis();
  }
  function terminarAsis() {
    const r = REC(), bis = X.asis ? X.asis.bis : null;
    X.asis = null;
    if (!r.bisagra && bis) { r.bisagra = bis; rutear(); }
    r.preguntar = false;
    Ins.dirty();
    toast(`Listo: bisagra a la ${lado(r.bisagra)}. Para cambiar la entrada o la salida de una bandeja lateral: 🧭 Entrada / salida (S)`, 5000);
    cerrarEd();
  }
  function renderAsis() {
    const el = $('#e8sAsis'); el.hidden = !X.asis; if (!X.asis) { el.innerHTML = ''; return; }
    const { pasos, i, bis } = X.asis, p = pasos[i], ult = i === pasos.length - 1, n = pasos.length;
    const sig = ult ? '✓ Listo' : `Siguiente →`;
    if (p === 'bisagra') {
      const prop = E().bisagra_propuesta || 'izq';
      el.innerHTML = `<div class="sal-asis-t">Paso 1 de ${n} · ¿De qué lado está la <b>bisagra de la puerta</b>?</div>
        <div class="small">Depende del producto: se elige una vez por trabajo. Los cables que siguen a la puerta salen por la bandeja lateral de ese lado; los de la otra lateral cruzan por el fondo.</div>
        <div class="seg e8-bis" role="group" aria-label="Lado de la bisagra">${['izq', 'der'].map(b => `<button data-bis="${b}" class="${bis === b ? 'on' : ''}">${b === 'izq' ? '◧ Izquierda' : 'Derecha ◨'}${b === prop ? ' <span class="small">(propuesta)</span>' : ''}</button>`).join('')}</div>
        <div class="sal-asis-b"><button class="btn primary sm" data-asis="sig">${sig}</button></div>`;
      return;
    }
    const L = E().laterales[p], P = ptsOf(vrec(L).entrada), nc = miembros(L, gruposEd(L)[0]).length;
    const marcado = P.length ? (P.length === 1 ? 'Marcado: entran por el punto naranja' : `Marcado: pasan por ${P.length - 1} punto${P.length > 2 ? 's' : ''} y entran por el naranja`)
      : 'Sin marcar: queda la propuesta (la flecha roja punteada)';
    el.innerHTML = `<div class="sal-asis-t">Paso ${i + 1} de ${n} · ¿Por dónde entran a la <b>${esc(L.nombre.toLowerCase())}</b> los cables que vienen de la bandeja principal? <span class="muted small">${nc} cable${nc === 1 ? '' : 's'}</span></div>
      <div class="small">La flecha roja es la propuesta. Si está bien, tocá «Usar la propuesta». Si no, hacé clic en el dibujo por donde entran (en la punta de una canaleta o a su costado); si antes pasan por otro lado, marcá esos puntos primero: el último clic es la entrada.</div>
      <div class="small ${P.length ? 'sal-eleg' : 'muted'}">${marcado}</div>
      <div class="sal-asis-b">
        ${P.length ? '<button class="btn ghost sm" data-asis="deshacer" title="Sacar el último punto (Retroceso)">↶ Último punto</button>' : ''}
        <button class="btn ghost sm" data-asis="prop" title="Sin marcar: la entrada propuesta">Usar la propuesta</button>
        <button class="btn primary sm" data-asis="sig">${sig}</button></div>`;
  }

  /* panel del editor: lateral, bisagra, grupos y cables */
  function edRender() {
    if ($('#e8sViewer').hidden) return;
    const e8 = E(), L = e8.laterales[X.li], gs = gruposEd(L); X.act = Math.max(0, Math.min(X.act, gs.length - 1));
    $('#e8sTit').textContent = `🧭 Entrada / salida · ${L.nombre}`;
    $('#e8sLats').hidden = !!X.asis || e8.laterales.length < 2;
    $('#e8sLats').innerHTML = e8.laterales.map((x, i) => `<button role="tab" data-li="${i}" class="${i === X.li ? 'on' : ''}" ${(x.ductos || []).length ? '' : 'disabled title="Sin canaletas leídas"'}>${esc(x.nombre)}</button>`).join('');
    const r = REC();
    $('#e8sGrupos').hidden = !!X.asis && X.asis.pasos[X.asis.i] === 'bisagra';
    $('#e8sGrupos').innerHTML = (X.asis ? '' : `<div class="e8-bisg small">Bisagra de la puerta: <span class="seg e8-bis" role="group" aria-label="Lado de la bisagra">${['izq', 'der'].map(b => `<button data-bis="${b}" class="${r.bisagra === b ? 'on' : ''}" title="La puerta abre del lado de la bandeja lateral ${lado(b)}">${b === 'izq' ? 'Izquierda' : 'Derecha'}</button>`).join('')}</span>
        ${r.bisagra ? '' : '<span class="muted">sin elegir: los cables a la puerta salen por la entrada</span>'}</div>`) +
      gs.map((G, i) => {
        const n = miembros(L, G).length, sel = G.tipo === 'seleccion', on = i === X.act, P = puntosG(G);
        const rt = P.length ? (P.length === 1 ? `Elegida: ${G.tipo === 'puerta' ? 'salen' : 'entran'} por el punto marcado` : `Elegida: pasan por ${P.length - 1} punto${P.length > 2 ? 's' : ''} y ${G.tipo === 'puerta' ? 'salen' : 'entran'} por el último`)
          : sel ? 'Sin recorrido: siguen la entrada (o la salida a la puerta)' : G.tipo === 'puerta' ? 'Propuesta: por la canaleta de arriba, del lado de la puerta' : 'Propuesta (la flecha roja punteada)';
        return `<div class="sal-g ${on ? 'on' : ''}" data-g="${i}">
          <div class="sal-gh">${sel ? `<input class="sal-nom" data-g="${i}" value="${esc(G.nombre || '')}" aria-label="Nombre del grupo" spellcheck="false">` : `<b>${esc(G.nombre)}</b>`}
            <span class="muted small">${n} cable${n === 1 ? '' : 's'}</span></div>
          <div class="small ${P.length ? 'sal-eleg' : 'muted'}">${esc(rt)}</div>
          ${G.tipo === 'entrada' ? '<div class="small muted">Los que vienen de la bandeja principal (E6), de la otra lateral o del fondo' + (L.bisagra ? '' : ', y los que siguen a la puerta: cruzan por el fondo') + '.</div>' : ''}
          ${G.tipo === 'puerta' ? '<div class="small muted">Los que siguen a la puerta o a la placa (aparatos que no están dibujados en el topográfico).</div>' : ''}
          ${on ? `<div class="sal-acts">
            <button class="btn sm ${X.modo === 'recorrido' ? 'on' : ''}" data-a="rec" title="Clic en el dibujo por donde pasan los cables; el último clic es por donde ${G.tipo === 'puerta' ? 'salen' : 'entran'}">✎ Marcar recorrido</button>
            ${sel ? `<button class="btn sm ${X.modo === 'cables' ? 'on' : ''}" data-a="cab" title="Clic en un cable para sumarlo o sacarlo, o un recuadro con los que nacen adentro">☑ Elegir cables</button>` : ''}
            ${P.length ? `<button class="btn ghost sm" data-a="deshacer" title="Sacar el último punto (Retroceso)">↶ Último punto</button>
            <button class="btn ghost sm" data-a="prop" title="Borrar el recorrido elegido: vuelve a la propuesta">↺ Propuesta</button>` : ''}
            ${sel ? '<button class="btn ghost sm" data-a="del" title="Borrar este grupo">🗑 Borrar</button>' : ''}</div>` : ''}
        </div>`;
      }).join('') + (X.asis ? '' : '<button class="btn sm sal-nuevo" data-a="nuevo" title="Un grupo de cables elegidos, con su propio recorrido (manda sobre la entrada y la salida a la puerta)">＋ Grupo de cables elegidos</button>');
    edList(); edHint(); renderAsis(); edDraw();
  }
  function edList() {
    const L = E().laterales[X.li], G = gruposEd(L)[X.act], sel = G && G.tipo === 'seleccion';
    const q = norm($('#e8sQ').value.trim()), act = new Set(miembros(L, G));
    const ls = salientes(L).filter(l => !q || norm(`${l.num} ${l.origen} ${l.destino} ${l.otra} ${l.color} ${l.secc}`).includes(q));
    $('#e8sListAct').hidden = !sel;
    $('#e8sList').innerHTML = ls.map(l => {
      const gg = grupoDe(L, l), eleg = gg && puntosG(gg).length;
      return `<div class="vs-it sal-it ${act.has(l) ? 'act' : ''} ${X.foco === l.num ? 'on' : ''}" data-num="${esc(l.num)}" title="${esc(`${l.origen} → ${l.destino} (${l.otra})${l.largo_mm ? ' · ≈' + l.largo_mm + ' mm en la lateral' : ''}`)}">
        ${sel ? `<input type="checkbox" data-ck ${(G.ref.cables || []).includes(l.num) ? 'checked' : ''} aria-label="Cable ${esc(l.num)} en el grupo">` : '<span></span>'}
        <span class="n">${esc(l.num)}</span><span class="od mono">${esc(l.origen)} → ${esc(l.destino)}</span>
        <span class="sal-chip ${eleg ? 'eleg' : ''}" title="${l.no_llega ? 'No llega por las canaletas hasta el punto elegido: sale por la propuesta' : gg ? esc(gg.nombre) : ''}">${l.no_llega ? '⚠ ' : ''}${esc(gg ? (gg.tipo === 'entrada' ? 'entrada' : gg.tipo === 'puerta' ? 'a la puerta' : gg.nombre) : '')}${eleg ? '' : ' (prop.)'}</span></div>`;
    }).join('') || '<div class="vs-empty muted small">Ningún cable coincide.</div>';
    const n = salientes(L).length;
    $('#e8sCnt').textContent = `${n} cable${n === 1 ? '' : 's'} entran o salen de la lateral · ${salientes(L).filter(l => { const g = grupoDe(L, l); return g && puntosG(g).length; }).length} con recorrido elegido`;
  }
  function edHint() {
    const L = E().laterales[X.li], G = gruposEd(L)[X.act], nom = G ? `«${G.nombre}»` : '', ve = G && G.tipo === 'puerta' ? 'salen' : 'entran';
    $('#e8sHint').textContent = X.modo === 'recorrido'
      ? `Recorrido de ${nom}: hacé clic por donde pasan los cables, en orden; el último clic es por donde ${ve} (en la punta de una canaleta o a su costado)${X.nuevo && G && puntosG(G).length ? ' · el primer clic empieza un recorrido nuevo' : ''} · Retroceso: sacar el último punto · Enter: listo`
      : X.modo === 'cables'
        ? `Cables de ${nom}: clic en un cable para sumarlo o sacarlo · arrastrá un recuadro para sumar (o sacar) los que nacen adentro · Enter o Esc: listo`
        : 'Elegí un grupo a la izquierda y ✎ Marcar recorrido · Clic en un cable: ver su recorrido · Rueda: zoom · Arrastrar: mover · 0: toda la bandeja · Esc: cerrar';
    const svg = $('#e8sSvg'); svg.classList.toggle('pick', X.modo === 'recorrido'); svg.classList.toggle('cab', X.modo === 'cables');
  }
  const ppx = () => { const r = $('#e8sSvg').getBoundingClientRect(), vb = X.vb; return r.width && r.height && vb ? Math.max(vb[2] / r.width, vb[3] / r.height) : 0.3; };
  function edDraw() {
    if ($('#e8sViewer').hidden || !$('#e8sRutas')) return;
    const L = E().laterales[X.li], gs = gruposEd(L), G = gs[X.act], act = new Set(miembros(L, G)), u = ppx(), k = Math.max(0.5, 1.6 * u);
    const ls = salientes(L), foco = ls.find(l => l.num === X.foco);
    $('#e8sRutas').innerHTML = ls.filter(l => !act.has(l) && l !== foco).map(l => routeG(l, 'otro', k, { fin: false })).join('')
      + ls.filter(l => act.has(l) && l !== foco).map(l => routeG(l, 'cur', k, { fin: false })).join('')
      + (foco ? routeG(foco, 'cur', k * 1.3, { pulse: true }) : '');
    // la flecha de la entrada (y de la salida a la puerta) y los puntos del grupo activo, numerados (el ultimo = por donde
    // entran o salen); los de los otros grupos, chicos
    let m = flechas(L, u);
    for (const x of gs) {
      const P = puntosG(x); if (!P.length) continue;
      const on = x === G, r = (on ? 9 : 5) * u, n = P.length;
      if (n > 1) m += `<polyline points="${P.map(p => `${f2(p[0])},${f2(-p[1])}`).join(' ')}" class="sal-orden ${on ? 'on' : ''}" stroke-width="${f2(1.5 * u)}" stroke-dasharray="${f2(5 * u)} ${f2(4 * u)}"/>`;
      m += P.map((p, i) => `<g class="sal-pt ${i === n - 1 ? 'fin' : ''} ${on ? 'on' : ''}"><title>${esc(x.nombre)}: ${i === n - 1 ? (x.tipo === 'puerta' ? 'salen de la lateral por acá' : 'entran a la lateral por acá') : 'pasan por acá (' + (i + 1) + ')'}</title>
        <circle cx="${f2(p[0])}" cy="${f2(-p[1])}" r="${f2(r)}" stroke-width="${f2(1.6 * u)}"/>
        ${on ? `<text x="${f2(p[0])}" y="${f2(-p[1])}" font-size="${f2((i === n - 1 ? 8.5 : 10) * u)}" text-anchor="middle" dominant-baseline="central">${i === n - 1 ? '⇥' : i + 1}</text>` : ''}</g>`).join('');
    }
    if (X.rect) {
      const [a, b] = X.rect;
      m += `<rect x="${f2(Math.min(a[0], b[0]))}" y="${f2(Math.min(a[1], b[1]))}" width="${f2(Math.abs(b[0] - a[0]))}" height="${f2(Math.abs(b[1] - a[1]))}" class="sal-rect" stroke-width="${f2(1.2 * u)}"/>`;
    }
    $('#e8sMarcas').innerHTML = m;
  }
  const redibujar = () => { cancelAnimationFrame(X.raf); X.raf = requestAnimationFrame(edDraw); };

  /* recorrido nuevo: el servidor rutea con lo elegido (como al regenerar), con las canaletas de cada lateral */
  function rutear() {
    clearTimeout(X.t);
    X.t = setTimeout(async () => {
      const seq = ++X.seq, job = Ins.job;
      let r;
      try { r = await api(`/api/trabajo/${job}/e8/recorridos`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ recorridos: REC() }) }); }
      catch (e) { return toast('No se pudo calcular el recorrido: ' + e.message, 5000); }
      if (seq !== X.seq || job !== Ins.job || !E()) return;
      let mal = 0;
      for (const x of (r && r.laterales) || []) {
        const L = E().laterales[x.vista]; if (!L || L.clave_vista !== x.clave_vista) continue;
        Object.assign(L, { bisagra: x.bisagra, entrada_propuesta: x.entrada_propuesta, puerta_propuesta: x.puerta_propuesta });
        const sal = salientes(L);
        (x.lineas || []).forEach((y, i) => {
          const l = sal[i]; if (!l || l.clave !== y.clave) return;
          l.ruta = y.ruta; l.largo_mm = y.largo_mm;
          for (const k of ['sale', 'salida', 'no_llega']) { if (y[k] == null) delete l[k]; else l[k] = y[k]; }
        });
        mal += x.no_llegan || 0;
      }
      if (mal) toast(`${mal} cable${mal > 1 ? 's' : ''} no llega${mal > 1 ? 'n' : ''} por las canaletas hasta el punto marcado: sale${mal > 1 ? 'n' : ''} por la propuesta`, 5000);
      Ins.dirty(); edRender();
      if ($('#e8sViewer').hidden && !W().hidden) render();
    }, 60);
  }
  function cambio(reruta = true) { edRender(); if (reruta) rutear(); else Ins.dirty(); }
  function setModo(m) { X.modo = m; X.nuevo = m === 'recorrido'; X.rect = null; edRender(); }
  function accion(a, i) {
    const L = E().laterales[X.li], gs = gruposEd(L), G = gs[i];
    if (a === 'nuevo') {
      const v = vrec(L), n = v.grupos.length + 1;
      v.grupos.push({ id: 'g' + Date.now().toString(36), nombre: `Grupo ${n}`, cables: X.foco ? [X.foco] : [], puntos: [] });
      X.act = gruposEd(L).length - 1; X.modo = 'cables'; X.rect = null;
      cambio(false); return toast('Elegí los cables del grupo (clic o recuadro) y después ✎ Marcar recorrido', 4000);
    }
    if (!G) return;
    if (a === 'rec') return setModo(X.modo === 'recorrido' ? null : 'recorrido');
    if (a === 'cab') return setModo(X.modo === 'cables' ? null : 'cables');
    if (a === 'deshacer') { setPuntos(G, puntosG(G).slice(0, -1)); X.nuevo = false; return cambio(); }
    if (a === 'prop') { setPuntos(G, []); X.modo = null; return cambio(); }
    if (a === 'del') {
      if (!confirm(`¿Borrar el grupo «${G.nombre}»? Sus cables vuelven a la entrada (o a la salida a la puerta).`)) return;
      const v = vrec(L); v.grupos.splice(v.grupos.indexOf(G.ref), 1); X.act = 0; X.modo = null; return cambio();
    }
  }
  function agregarPunto(p) {
    const G = gruposEd(E().laterales[X.li])[X.act]; if (!G) return;
    setPuntos(G, X.nuevo ? [p] : [...puntosG(G), p]); X.nuevo = false;
    cambio();
  }
  function alternar(nums, forzar) {
    const L = E().laterales[X.li], G = gruposEd(L)[X.act]; if (!G || G.tipo !== 'seleccion') return;
    const s = new Set(G.ref.cables || []);
    const sumar = forzar ?? !nums.every(n => s.has(n));
    for (const n of nums) sumar ? s.add(n) : s.delete(n);
    G.ref.cables = [...new Set(salientes(L).map(l => l.num))].filter(n => s.has(n));
    cambio(puntosG(G).length > 0);
  }
  function distSeg(p, a, b) {
    const dx = b[0] - a[0], dy = b[1] - a[1], q = dx * dx + dy * dy;
    const t = q ? Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / q)) : 0;
    return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
  }
  // cable mas cercano al punto: primero por el borne, despues por el recorrido
  function cercano(p, u) {
    const tol = 8 * u, ls = salientes(E().laterales[X.li]); let best = null;
    for (const l of ls) {
      const o = l.marca_o || (l.ruta && l.ruta[0]); if (!o) continue;
      const d = Math.hypot(p[0] - o[0], p[1] - o[1]);
      if (d < tol && (!best || d < best.d)) best = { l, d };
    }
    if (best) return best.l;
    for (const l of ls) {
      const r = l.ruta || [];
      for (let i = 1; i < r.length; i++) { const d = distSeg(p, r[i - 1], r[i]); if (d < tol && (!best || d < best.d)) best = { l, d }; }
    }
    return best ? best.l : null;
  }
  function enfocar(l) {
    const L = E().laterales[X.li];
    X.foco = l ? l.num : null;
    if (l && !miembros(L, gruposEd(L)[X.act]).includes(l)) { const g = grupoDe(L, l); if (g) X.act = gruposEd(L).findIndex(G => G.ref === g.ref && G.tipo === g.tipo); }
    edRender();
    const it = l && [...$('#e8sList').querySelectorAll('.sal-it')].find(x => x.dataset.num === l.num); if (it) it.scrollIntoView({ block: 'nearest' });
  }
  function svgPtEd(e) {
    const r = $('#e8sSvg').getBoundingClientRect(), vb = X.vb;
    const s = Math.max(vb[2] / r.width, vb[3] / r.height);
    const ox = (r.width * s - vb[2]) / 2, oy = (r.height * s - vb[3]) / 2;
    return [vb[0] - ox + (e.clientX - r.left) * s, vb[1] - oy + (e.clientY - r.top) * s, s];
  }
  const setVb = vb => { X.vb = vb; $('#e8sSvg').setAttribute('viewBox', vb.map(f2).join(' ')); redibujar(); };
  function initEd() {
    $('#e8sAsis').addEventListener('click', e => {
      const b = e.target.closest('[data-asis],[data-bis]'); if (!b || !X.asis) return;
      if (b.dataset.bis) { X.asis.bis = b.dataset.bis; REC().bisagra = X.asis.bis; rutear(); return pasoAsis(); }
      if (b.dataset.asis === 'sig') return sigAsis();
      const L = E().laterales[X.li];
      if (b.dataset.asis === 'deshacer') return accion('deshacer', 0);
      if (b.dataset.asis === 'prop') { if (ptsOf(vrec(L).entrada).length) { vrec(L).entrada = []; rutear(); } return sigAsis(); }
    });
    $('#e8sClose').addEventListener('click', cerrarEd);
    $('#e8sVolver').addEventListener('click', cerrarEd);
    $('#e8sFit').addEventListener('click', () => setVb(vbOf(E().laterales[X.li].region)));
    $('#e8sLats').addEventListener('click', e => {
      const b = e.target.closest('[data-li]'); if (!b || X.asis || b.disabled) return;
      const i = +b.dataset.li, L = E().laterales[i];
      if (!L || !(L.ductos || []).length) return;
      X.li = i; X.act = 0; X.modo = null; X.foco = null; cargarLat();
    });
    $('#e8sGrupos').addEventListener('click', e => {
      const bb = e.target.closest('[data-bis]');
      if (bb) { REC().bisagra = bb.dataset.bis; X.act = 0; X.modo = null; edRender(); return rutear(); }
      const b = e.target.closest('[data-a]'), c = e.target.closest('.sal-g');
      if (b) return accion(b.dataset.a, c ? +c.dataset.g : -1);
      if (c && !e.target.matches('.sal-nom') && +c.dataset.g !== X.act) { X.act = +c.dataset.g; X.modo = null; edRender(); }
    });
    $('#e8sGrupos').addEventListener('change', e => {
      if (!e.target.matches('.sal-nom')) return;
      const G = gruposEd(E().laterales[X.li])[+e.target.dataset.g]; if (!G || G.tipo !== 'seleccion') return;
      G.ref.nombre = e.target.value.trim() || G.ref.nombre; cambio(false);
    });
    $('#e8sGrupos').addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.matches('.sal-nom')) { e.preventDefault(); e.target.blur(); } });
    $('#e8sList').addEventListener('click', e => {
      const it = e.target.closest('.sal-it'); if (!it) return;
      const l = salientes(E().laterales[X.li]).find(x => x.num === it.dataset.num); if (!l) return;
      if (e.target.matches('[data-ck]')) return alternar([l.num], e.target.checked);
      if (X.modo === 'cables') return alternar([l.num]);
      enfocar(X.foco === l.num ? null : l);
    });
    let qT; $('#e8sQ').addEventListener('input', () => { clearTimeout(qT); qT = setTimeout(edList, 80); });
    $('#e8sQ').addEventListener('keydown', e => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); if (e.target.value) { e.target.value = ''; edList(); } else e.target.blur(); } });
    const lista = () => [...$('#e8sList').querySelectorAll('.sal-it')].map(x => x.dataset.num);
    $('#e8sTodos').addEventListener('click', () => alternar(lista(), true));
    $('#e8sNinguno').addEventListener('click', () => alternar(lista(), false));
    const svg = $('#e8sSvg');
    svg.addEventListener('wheel', e => {
      e.preventDefault(); if (!X.vb) return;
      const [px, py] = svgPtEd(e), f = Math.pow(1.0015, e.deltaY), vb = X.vb;
      setVb([px - (px - vb[0]) * f, py - (py - vb[1]) * f, vb[2] * f, vb[3] * f]);
    }, { passive: false });
    svg.addEventListener('pointerdown', e => {
      if (e.button !== 0 || !X.vb) return;
      const p = svgPtEd(e);
      X.drag = { x: e.clientX, y: e.clientY, vb: X.vb.slice(), s: p[2], p0: [p[0], p[1]], rect: X.modo === 'cables' };
      svg.setPointerCapture(e.pointerId); if (!X.drag.rect) svg.classList.add('drag');
    });
    svg.addEventListener('pointermove', e => {
      const d = X.drag; if (!d) return;
      if (d.rect) { if (Math.hypot(e.clientX - d.x, e.clientY - d.y) >= 5) { const p = svgPtEd(e); X.rect = [d.p0, [p[0], p[1]]]; redibujar(); } return; }
      setVb([d.vb[0] - (e.clientX - d.x) * d.s, d.vb[1] - (e.clientY - d.y) * d.s, d.vb[2], d.vb[3]]);
    });
    svg.addEventListener('pointerup', e => {
      const d = X.drag; X.drag = null; svg.classList.remove('drag');
      if (!d) return;
      if (X.rect) {          // recuadro: los cables que nacen adentro
        const [a, b] = X.rect; X.rect = null;
        const x0 = Math.min(a[0], b[0]), x1 = Math.max(a[0], b[0]), y0 = -Math.max(a[1], b[1]), y1 = -Math.min(a[1], b[1]);
        const nums = salientes(E().laterales[X.li]).filter(l => { const o = l.marca_o || (l.ruta && l.ruta[0]); return o && o[0] >= x0 && o[0] <= x1 && o[1] >= y0 && o[1] <= y1; }).map(l => l.num);
        if (nums.length) alternar([...new Set(nums)]); else { edDraw(); toast('Ningún cable nace adentro del recuadro'); }
        return;
      }
      if (Math.hypot(e.clientX - d.x, e.clientY - d.y) >= 5) return;      // fue un arrastre
      const [x, y, s] = svgPtEd(e), p = [Math.round(x * 100) / 100, Math.round(-y * 100) / 100];
      if (X.modo === 'recorrido') return agregarPunto(p);
      const l = cercano(p, s);
      if (X.modo === 'cables') { if (l) alternar([l.num]); return; }
      enfocar(l);
    });
    window.addEventListener && window.addEventListener('resize', () => { if (!$('#e8sViewer').hidden) redibujar(); });
    document.addEventListener('keydown', e => {
      if ($('#e8sViewer').hidden) return;
      if (e.target.isContentEditable || (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox')) return;
      if (e.key === 'Escape') { e.preventDefault(); return X.modo && !X.asis ? setModo(null) : cerrarEd(); }
      if (e.key === 'Enter' && X.asis) { e.preventDefault(); return sigAsis(); }
      if (e.key === 'Enter' && X.modo) { e.preventDefault(); return setModo(null); }
      if (e.key === 'Backspace' && X.modo === 'recorrido') { e.preventDefault(); return accion('deshacer', X.act); }
      if (e.key === '0') { e.preventDefault(); setVb(vbOf(E().laterales[X.li].region)); }
    });
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
    $('#e8Entrada').addEventListener('click', () => abrirEd({}));
    $('#e8Print').addEventListener('click', imprimir);
    $('#e8Lat').addEventListener('click', e => {
      if (e.target.closest('[data-a="entrada"]')) return abrirEd({});
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
    $('#e8vEntrada').addEventListener('click', entradaDesdeVisor);
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
      if (!$('#e8sViewer').hidden) return;
      if (e.target.isContentEditable || (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox') || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
      if ($('#e8Viewer').hidden) {      // pestaña: S = entrada / salida de la lateral que se ve
        if ((e.key === 's' || e.key === 'S') && !e.ctrlKey && !e.metaKey && !e.altKey && !W().hidden && typeof vista === 'number' && E()
            && $('#viewer').hidden !== false) { e.preventDefault(); abrirEd({}); }
        return;
      }
      const keys = { ArrowRight: () => go(1), ArrowLeft: () => go(-1), Escape: closeViewer, ' ': () => toggleOk(true), Enter: () => toggleOk(true),
        '0': () => camera(vbOf(lat().region), 350), f: () => draw(), l: () => setSide($('#e8vSide').hidden), s: entradaDesdeVisor, S: entradaDesdeVisor };
      if (keys[e.key]) { e.preventDefault(); keys[e.key](); }
    });
    initEd();
  }
  // desde el visor de cablear: la entrada / salida de la lateral, con el cable actual enfocado; al cerrar vuelve al visor
  function entradaDesdeVisor() {
    const f = F(); if (!f.length) return;
    const l = f[V.k].l, k = V.k;
    $('#e8Viewer').hidden = true; document.body.style.overflow = '';
    abrirEd({ li: vista, volver: k, num: l.marca_d ? null : l.num });
    if ($('#e8sViewer').hidden) openViewer(k);       // (no se pudo abrir: sin canaletas o sin cables que salen)
  }
  return { open, init, hide: () => { W().hidden = true; }, asistente };
})();
E8.init();
