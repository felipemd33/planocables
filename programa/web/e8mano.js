'use strict';
/* Estación 8 · RUTEO A MANO POR GRUPOS (etapa E8-6, pedido del taller del 2026-10-08).
   Los cables de solenoides, contactora (bobina), batería (35 mm² y 4 / 6 mm², por separado), doorswitch, pulsadores,
   selectoras, llaves seccionadoras y los de cada placa NO se rutean solos: el recorrido lo DIBUJA el taller acá, con
   clics sobre las vistas de E8 (bandejas laterales, puerta y FONDO = la bandeja principal con la zona del fondo). Un
   recorrido es una secuencia de TRAMOS, uno por vista: dibujar en otra vista empieza un tramo nuevo (el cable pasa de una
   vista a la otra). Un clic cerca de una canaleta se pega a su eje (🧲, tecla I para apagarlo).
   - Los grupos se arman solos (programa/web/e8_grupos.json) y el taller los corrige: mover un cable a otro grupo (o
     sacarlo: vuelve al ruteo automático) y armar grupos nuevos de placa.
   - Se guarda POR PRODUCTO (código + número y revisión del topográfico): vale para todos los trabajos del mismo producto
     con el mismo topográfico (PUT /api/trabajo/<id>/e8/grupos). Si el producto no está confirmado se guarda en el trabajo.
   - «▶ Cablear de a uno» por grupo: cada cable del grupo con el recorrido dibujado (las marcas son las de la estación 8).
   - Pines de la placa (etapa E8-7): un cable de la placa con su pin exacto en la vista de la puerta (cables[k].pin_puerta)
     va del FINAL del tramo común dibujado a su pin, y en el visor de a uno su punta dice la aclaración del funcional
     (cables[k].aclaracion, en la punta cables[k].aclaracion_de). Sin dibujar, lo que falta es solo el tramo común.
   - Placa solo en la puerta (etapa E8-8, 2026-10-13): un grupo de una categoría 'solo_puerta' (la placa) se dibuja solo
     en la vista de la PUERTA; lo dibujado antes en otra vista no se usa (g.tramos_fuera) y sin la vista de la puerta
     (g.sin_puerta, el PAE) no hay nada que dibujar. El visor de a uno dibuja solo el grupo actual.
   - HAZ DE LA PLACA (etapa E8-8, 2026-10-13, pedido del taller: «algo simple, ir indicando puntos, poder hacer una curva
     y que al final el ruteo se pueda hacer algo automático»): en la puerta, el grupo de placa se dibuja como un HAZ que
     arranca solo en la entrada a la puerta (la flecha «Entrada»; no se guarda: el tramo lleva desde: 'entrada'); el
     taller marca los puntos por donde va; C o «↪ Curva» redondea la esquina del último punto (Mayús+clic en un punto:
     curva sí / no; el tramo lleva curvas: [índices]); Retroceso saca el último punto; Enter: listo; Esc: cancelar (vuelve
     como estaba). «Usar la propuesta» lo llena con el tramo común automático de E8-4 (POST /e8/haz). De su final cada
     cable va solo a su pin: el ABANICO (nucleo/haz.js, estacion8.js hazDe / hazG), que se ve «como la foto» con
     «👁 Cómo queda» y en el visor de a uno.
   Los datos: ins.estacion8.ruteo_mano (estacion8_mano.py): {categorias, vistas, auto, auto_info, cables, grupos, miembro,
   manual: {grupos: {id: {tramos: [{vista, puntos}], nombre}}, nuevos, mover}, clave_producto, por_producto, aviso,
   version_almacen, editado, avisos}. efectivo() es la copia en JS de estacion8_mano.aplicar (los grupos con lo del taller). */
const E8M = (() => {
  const I = () => E8.int;
  const R = () => I().RM();
  const M = { abierto: false, modo: 'editar', gi: null, vk: null, dib: false, nuevoTramo: false, iman: true, vb: null, drag: null,
    k: 0, volver: null, deEditar: false, seq: 0, t: null, guardando: false, pend: false, fantasma: null, estado: '', foco: null, apNuevo: null,
    snap: null, final: false };      // (haz de la placa: snap = cómo estaba antes de dibujar, para Esc; final = 👁 Cómo queda)
  const f2 = v => (+v).toFixed(2);
  const W = () => $('#e8mViewer');
  const VP = 'PUERTA';          // (clave de la vista de la puerta: estacion8_mano.VISTA_PUERTA)

  /* ---- grupos efectivos (la misma cuenta que estacion8_mano.aplicar) ---- */
  const natk = s => String(s ?? '').split(/(\d+)/).map((t, i) => (i % 2 ? +t : t));
  function cmpLista(a, b) {
    for (let i = 0; i < Math.min(a.length, b.length); i++) {
      const x = a[i], y = b[i];
      if (x === y) continue;
      if (typeof x === 'number' && typeof y === 'number') return x - y;
      return String(x) < String(y) ? -1 : 1;
    }
    return a.length - b.length;
  }
  function manual(r) {
    r = r || R();
    const m = r.manual = (r.manual && typeof r.manual === 'object') ? r.manual : {};
    if (!m.grupos || typeof m.grupos !== 'object' || Array.isArray(m.grupos)) m.grupos = {};
    if (!Array.isArray(m.nuevos)) m.nuevos = [];
    if (!m.mover || typeof m.mover !== 'object' || Array.isArray(m.mover)) m.mover = {};
    return m;
  }
  function efectivo(r) {
    const m = manual(r), cables = r.cables || {};
    const pos = new Map((r.categorias || []).map((c, i) => [c.id, i])), nom = new Map((r.categorias || []).map(c => [c.id, c.nombre]));
    const vistas = new Set((r.vistas || []).map(v => v.clave));
    const gs = new Map();
    for (const [gid, i] of Object.entries(r.auto_info || {}))
      gs.set(gid, { id: gid, categoria: i.categoria, aparato: i.aparato || null, auto: true, nombre: (nom.get(i.categoria) || gid) + (i.aparato ? ' ' + i.aparato : '') });
    for (const x of m.nuevos) if (!gs.has(x.id)) gs.set(x.id, { id: x.id, categoria: x.categoria, aparato: x.aparato || null, auto: false, nombre: x.nombre });
    const miembro = { ...(r.auto || {}) };
    for (const [k, gid] of Object.entries(m.mover)) {
      if (!cables[k] || (gid && !gs.has(gid))) continue;
      if (gid) miembro[k] = gid; else delete miembro[k];
    }
    // (como estacion8_mano.solo_puerta_de: la placa se dibuja a mano solo en la PUERTA. Un ruteo_mano armado antes, sin
    // la marca en sus categorías, la toma de los grupos que mandó el servidor, que la sacó de la tabla)
    const conMarca = (r.categorias || []).some(c => 'solo_puerta' in c);
    const solo = new Set(conMarca ? (r.categorias || []).filter(c => c.solo_puerta).map(c => c.id)
      : (r.grupos || []).filter(g => g.solo_puerta).map(g => g.categoria));
    const lista = [...gs.values()].map(g => {
      const mg = m.grupos[g.id] || {};
      let tramos = (mg.tramos || []).filter(t => vistas.has(t.vista) && (t.puntos || []).length);
      const extra = {};
      if (solo.has(g.categoria)) {
        const fuera = tramos.filter(t => t.vista !== VP);
        tramos = tramos.filter(t => t.vista === VP);
        extra.solo_puerta = true;
        if (!vistas.has(VP)) extra.sin_puerta = true;
        if (fuera.length) extra.tramos_fuera = fuera.length;
      }
      const cs = Object.keys(miembro).filter(k => miembro[k] === g.id)
        .sort((a, b) => cmpLista(natk((cables[a] || {}).num), natk((cables[b] || {}).num)) || (a < b ? -1 : a > b ? 1 : 0));
      return { ...g, nombre: mg.nombre || g.nombre, cables: cs, n: cs.length, tramos, dibujado: tramos.some(tramoDibujado), ...extra };
    });
    // (como estacion8_mano._orden_grupo: los automáticos primero, por categoría; un grupo sin aparato va después de los
    // que lo tienen)
    const key = g => [g.auto ? 0 : 1, pos.has(g.categoria) ? pos.get(g.categoria) : 99, g.aparato ? 0 : 1, natk(g.aparato || ''), natk(g.id)];
    lista.sort((a, b) => { const x = key(a), y = key(b); return (x[0] - y[0]) || (x[1] - y[1]) || (x[2] - y[2]) || cmpLista(x[3], y[3]) || cmpLista(x[4], y[4]); });
    r.grupos = lista; r.miembro = miembro;
    return r;
  }
  // (como estacion8_mano.tramo_dibujado: dos puntos, o uno en el haz que arranca en la entrada a la puerta)
  const tramoDibujado = t => (t.puntos || []).length + (t.desde === 'entrada' ? 1 : 0) >= 2;
  const grupo = id => ((R() || {}).grupos || []).find(g => g.id === id) || null;
  const G = () => grupo(M.gi);
  const vistaNom = ck => (((R() || {}).vistas || []).find(v => v.clave === ck) || {}).nombre || ck;
  const V = () => I().vistaDe(M.vk);
  const cab = k => ((R() || {}).cables || {})[k] || null;
  // (etapa E8-7) los cables del grupo llegan a su pin de la placa: lo que falta dibujar es solo el tramo común
  const conPines = g => !!g && (g.cables || []).some(k => (cab(k) || {}).pin_puerta);
  const faltaTxt = g => conPines(g) ? 'falta dibujar el haz (de su final cada cable va a su pin)' : 'falta dibujar el recorrido';
  const puntaTxt = (c, w) => (c[w] || '') + (c.aclaracion && c.aclaracion_de === w ? ' · ' + I().aclCorta(c.aclaracion) : '');

  /* ---- HAZ DE LA PLACA (etapa E8-8): el grupo de placa en la puerta ---- */
  const esHaz = g => !!g && I().esHazG(g) && !!I().vistaDe(VP);
  // el tramo del haz en lo guardado del grupo (el último de la puerta); crear: uno nuevo que arranca en la entrada
  function tramoHaz(gid, crear) {
    const m = manual(), mg = m.grupos[gid] = m.grupos[gid] || { tramos: [] };
    if (!Array.isArray(mg.tramos)) mg.tramos = [];
    let t = null;
    for (const x of mg.tramos) if (x.vista === VP) t = x;
    if (!t && crear) { t = { vista: VP, puntos: [], curvas: [], desde: 'entrada' }; mg.tramos.push(t); }
    if (t && !Array.isArray(t.curvas)) t.curvas = [];
    return t;
  }
  const entradaP = () => (I().P() || {}).entrada || null;
  const HAZ_AYUDA = 'El haz arranca solo en la entrada a la puerta (el punto verde). Clic por donde va, en orden; C o ↪ Curva: la esquina del último punto va redondeada (Mayús+clic en un punto: curva sí / no); Retroceso: saca el último punto; Enter: listo; Esc: cancelar. De su final cada cable va solo a su pin (abanico).';
  function hazEstado(g) {
    const t = (g.tramos || []).filter(x => x.vista === VP).slice(-1)[0];
    if (!g.dibujado || !t) return { ok: false, txt: 'Falta dibujar el haz: arranca solo en la entrada a la puerta; marcá por dónde va (o «Usar la propuesta»). De su final cada cable va solo a su pin.' };
    if (t.desde !== 'entrada') return { ok: true, viejo: true, txt: 'Haz dibujado antes (no arranca en la entrada a la puerta): de su final cada cable va solo a su pin. ✏ para empezarlo de nuevo desde la entrada.' };
    const np = t.puntos.length, nc = (t.curvas || []).length;
    return { ok: true, txt: `Haz: arranca en la entrada · ${np} punto${np === 1 ? '' : 's'}${nc ? ` · ${nc} curva${nc === 1 ? '' : 's'}` : ''} · de su final cada cable va solo a su pin (abanico)` };
  }

  /* ---- pegar al eje de la canaleta (🧲): un punto a menos de 0,6 anchos de una canaleta va a su eje ---- */
  function iman(p, ductos) {
    let best = null;
    for (const d of ductos || []) {
      const b = d && d.b; if (!b) continue;
      const h = d.h != null ? !!d.h : (b[2] - b[0]) >= (b[3] - b[1]);
      const tol = 0.6 * (h ? b[3] - b[1] : b[2] - b[0]);
      if (p[0] < b[0] - tol || p[0] > b[2] + tol || p[1] < b[1] - tol || p[1] > b[3] + tol) continue;
      const q = h ? [Math.min(Math.max(p[0], b[0]), b[2]), (b[1] + b[3]) / 2] : [(b[0] + b[2]) / 2, Math.min(Math.max(p[1], b[1]), b[3])];
      const dd = Math.hypot(p[0] - q[0], p[1] - q[1]);
      if (!best || dd < best.d) best = { d: dd, q };
    }
    return best ? best.q : null;
  }
  const ducts = Vv => (Vv && Vv.ductos) || [];

  /* ---- abrir / cerrar ---- */
  // o = {grupo, clave (un cable: se enfoca), cablear (visor de a uno del grupo), buscar (texto de la búsqueda de la
  // lista: un cable sin grupo, desde el visor), volver (al cerrar)}
  function abrir(o = {}) {
    const r = R(); if (!r) return;
    efectivo(r);
    const gs = r.grupos || [];
    if (!gs.length) { if (o.volver) o.volver(); return toast('No hay cables de E8 con ruteo a mano en este trabajo', 4000); }
    M.gi = (o.grupo && grupo(o.grupo)) ? o.grupo : (grupo(M.gi) ? M.gi : (gs.find(g => g.n && !g.dibujado && !g.sin_puerta) || gs.find(g => g.n) || gs[0]).id);
    M.modo = o.cablear ? 'cablear' : 'editar'; M.deEditar = false; M.dib = false; M.volver = o.volver || null;
    M.k = 0; M.foco = o.clave || null;
    if (o.clave) { const i = (G().cables || []).indexOf(o.clave); if (i >= 0) M.k = i; }
    M.q = ''; $('#e8mQ').value = o.buscar ? String(o.buscar) : '';
    M.abierto = true; W().hidden = false; document.body.style.overflow = 'hidden'; M.final = false; M.snap = null;
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    elegirVista(null, true);
    if (M.modo === 'cablear') encuadrarHaz();
    renderTodo();
    const on = $('#e8mGrupos').querySelector && $('#e8mGrupos').querySelector('.e8m-g.on');      // (el grupo elegido, a la vista)
    if (on && on.scrollIntoView) on.scrollIntoView({ block: 'nearest' });
  }
  function cerrar() {
    if (!M.abierto) return;
    if (M.dib) return esHaz(G()) ? cancelarHaz() : setDib(false);
    if (M.modo === 'cablear' && M.deEditar) { M.modo = 'editar'; M.deEditar = false; return renderTodo(); }
    M.abierto = false; W().hidden = true; document.body.style.overflow = '';
    clearTimeout(M.t); if (M.pend) guardar();
    const v = M.volver; M.volver = null;
    if (v) v(); else I().render();
  }

  // la vista a mostrar: la del último tramo del grupo (o del primero en el visor de a uno), o donde están sus cables
  function vistasDelGrupo() {
    const g = G(), r = R(); if (!g || !r) return [];
    if (g.solo_puerta) return I().vistaDe(VP) ? [VP] : [];     // (la placa: solo la puerta)
    const out = [];
    for (const t of g.tramos || []) if (!out.includes(t.vista)) out.push(t.vista);
    const ks = M.modo === 'cablear' ? [g.cables[M.k]].filter(Boolean) : g.cables;
    for (const k of ks) for (const v of Object.keys((cab(k) || {}).puntos || {})) if (!out.includes(v)) out.push(v);
    return out.filter(v => I().vistaDe(v));
  }
  // (el haz de la placa en el visor de a uno: encuadrado en el final del haz, el abanico y la placa)
  function encuadrarHaz() {
    const g = G(), info = esHaz(g) && M.vk === VP && I().hazDe(g), b = info && I().cajaHaz(info);
    if (!b) return;
    const m = 0.5 * ((I().P() || {}).H || 24.8);
    M.vb = I().vbOf([b[0] - m, b[1] - m, b[2] + m, b[3] + m]); $('#e8mSvg').setAttribute('viewBox', M.vb.map(f2).join(' '));
  }
  function elegirVista(ck, ajustar) {
    const todas = ((R() || {}).vistas || []).map(v => v.clave).filter(v => I().vistaDe(v));
    if (!ck || (G() && G().solo_puerta && ck !== VP && todas.includes(VP))) {
      const g = G(), ts = (g && g.tramos) || [];
      const pref = M.modo === 'cablear' ? (ts[0] && ts[0].vista) : (ts.length ? ts[ts.length - 1].vista : null);
      ck = (pref && todas.includes(pref)) ? pref : (vistasDelGrupo()[0] || (todas.includes(M.vk) ? M.vk : todas[0]));
    }
    if (!ck || !I().vistaDe(ck)) return;
    const cambia = ck !== M.vk;
    M.vk = ck;
    if (cambia || ajustar || !M.vb) { M.vb = I().vbOf(I().vistaDe(ck).region); $('#e8mSvg').setAttribute('viewBox', M.vb.map(f2).join(' ')); }
    if (cambia) M.nuevoTramo = true;      // (dibujar en otra vista empieza un tramo nuevo)
  }

  /* ---- pantalla ---- */
  function renderTodo() {
    if (!M.abierto || !R()) return;
    const g = G(); if (!g) { M.gi = (R().grupos[0] || {}).id; if (!G()) return cerrar(); }
    const cablear = M.modo === 'cablear';
    if (cablear) M.k = Math.max(0, Math.min(M.k, Math.max(0, G().n - 1)));
    $('#e8mCab').hidden = !cablear || !G().n; $('#e8mNav').hidden = !cablear || !G().n; $('#e8mOkW').hidden = !cablear || !G().n;
    $('#e8mVolver').hidden = !M.volver;
    $('#e8mIman').hidden = cablear;
    $('#e8mIman').classList.toggle('on', M.iman); $('#e8mIman').setAttribute('aria-pressed', M.iman);
    renderTop(); renderVistas(); renderProd(); renderGrupos(); renderLista(); dibujar(); hint();
  }
  function renderTop() {
    const g = G();
    if (M.modo === 'cablear' && g.n) {
      const k = g.cables[M.k], c = cab(k) || {}, H = I().hechos();
      $('#e8mTit').innerHTML = `<span class="mono">${esc(c.num)}</span> ${swatch(c.color)} <span class="secc big">${esc(Ins.secTxt(c))}</span>`;
      $('#e8mSub').textContent = `Ruteo a mano · ${g.nombre}${g.sin_puerta ? ' · sin vista de la puerta' : g.dibujado ? '' : ' · ' + faltaTxt(g)}`;
      $('#e8mOrig').textContent = puntaTxt(c, 'a'); $('#e8mDest').textContent = puntaTxt(c, 'b');
      $('#e8mPos').textContent = `${M.k + 1} / ${g.n}`;
      $('#e8mOk').checked = H.has(k);
    } else {
      $('#e8mTit').textContent = '✏ Ruteo a mano por grupos';
      $('#e8mSub').textContent = 'El recorrido de estos cables lo dibuja el taller: clic en el dibujo por donde pasan, vista por vista.';
    }
  }
  function renderVistas() {
    const r = R(), cablear = M.modo === 'cablear';
    const deG = new Set(vistasDelGrupo()), conT = new Set(((G() || {}).tramos || []).map(t => t.vista));
    // (un grupo de la placa se dibuja solo en la puerta: las otras vistas no se ofrecen)
    const vs = (r.vistas || []).filter(v => I().vistaDe(v.clave) && (!cablear || deG.has(v.clave)) && (!(G() || {}).solo_puerta || v.clave === VP));
    $('#e8mVistas').innerHTML = vs.map(v => `<button role="tab" data-vk="${esc(v.clave)}" class="${v.clave === M.vk ? 'on' : ''}" title="${esc(v.nombre)}${conT.has(v.clave) ? ': hay un tramo dibujado' : ''}">${esc(v.nombre)}${conT.has(v.clave) ? ' ✓' : ''}</button>`).join('');
  }
  function renderProd() {
    const r = R();
    let h = r.por_producto
      ? `<div>Se guarda para el producto <b class="mono">${esc((r.clave_producto || '').split('|')[0])}</b> con el topográfico <b class="mono">${esc((r.clave_producto || '').split('|').slice(1).join(' ').replace('rev', 'rev. '))}</b>: vale para todos los trabajos de ese producto con ese topográfico.</div>`
      : `<div class="warn-t">${esc(r.aviso || 'Se guarda en este trabajo')}</div>`;
    const ed = r.editado;
    if (r.por_producto && ed && ed.trabajo && ed.trabajo !== Ins.job)
      h += `<div class="warn-t">Lo cambió por última vez otro trabajo${ed.archivo ? ` («${esc(ed.archivo)}»)` : ''}${ed.fecha ? ` el ${esc(ed.fecha)}` : ''}. Lo que cambies acá también cambia allá.</div>`;
    else if (r.por_producto && (r.trabajos || []).filter(t => t !== Ins.job).length)
      h += `<div class="muted">También lo usan ${(r.trabajos || []).filter(t => t !== Ins.job).length} trabajo(s) más: lo que cambies acá cambia en todos.</div>`;
    h += (r.avisos || []).map(a => `<div class="warn-t">${esc(a)}</div>`).join('');
    if (M.estado) h += `<div class="muted">${esc(M.estado)}</div>`;
    $('#e8mProd').innerHTML = h;
  }
  function tramosTxt(g) {
    const vs = []; for (const t of g.tramos || []) if (vs[vs.length - 1] !== t.vista) vs.push(t.vista);
    return vs.map(vistaNom).join(' → ');
  }
  function renderGrupos() {
    const r = R(), H = I().hechos(), cablear = M.modo === 'cablear';
    const gs = cablear ? [G()] : r.grupos;
    $('#e8mGrupos').innerHTML = (cablear ? `<button class="btn ghost sm" data-a="grupos" title="Volver a la lista de grupos (Esc)">← Todos los grupos</button>` : '') +
      gs.map(g => {
        const on = g.id === M.gi, np = (g.tramos || []).reduce((a, t) => a + t.puntos.length, 0), hechos = g.cables.filter(k => H.has(k)).length;
        if (esHaz(g)) return grupoHazHtml(g, on, cablear, hechos);
        return `<div class="sal-g e8m-g ${on ? 'on' : ''}" data-g="${esc(g.id)}">
          <div class="sal-gh"><span class="e8m-sw" style="background:${I().colorGrupo(g.id)}"></span>${g.auto ? `<b>${esc(g.nombre)}</b>` : `<input class="sal-nom" data-nom="${esc(g.id)}" value="${esc(g.nombre)}" aria-label="Nombre del grupo" spellcheck="false">`}
            <span class="muted small">${g.n} cable${g.n === 1 ? '' : 's'}${g.n ? ` · ${hechos} cableado${hechos === 1 ? '' : 's'}` : ''}</span></div>
          ${g.sin_puerta ? `<div class="small muted">${esc(SIN_PUERTA)}</div>`
            : `<div class="small ${g.dibujado ? 'sal-eleg' : 'warn-t'}">${g.dibujado ? `Dibujado: ${esc(tramosTxt(g))}${conPines(g) ? ' · de su final cada cable va a su pin' : ''}` : np ? 'Falta terminar el recorrido (un solo punto)' : (conPines(g) ? 'Falta dibujar el tramo común: de ahí cada cable va a su pin de la placa' : 'Falta dibujar el recorrido')}</div>`}
          ${g.solo_puerta && !g.sin_puerta ? `<div class="small muted">${esc(SOLO_PUERTA)}</div>` : ''}
          ${g.tramos_fuera ? `<div class="small warn-t">${esc(fueraTxt(g))}</div>` : ''}
          ${on && !cablear ? `<div class="sal-acts">
            ${g.sin_puerta ? '' : `<button class="btn sm ${M.dib ? 'on' : ''}" data-a="dib" title="${M.dib ? 'Terminar de dibujar (Enter)' : 'Clic en el dibujo por donde pasan los cables, en orden; en otra vista sigue con un tramo nuevo'}">${M.dib ? '✓ Listo' : np ? '✏ Seguir dibujando' : '✏ Dibujar recorrido'}</button>`}
            ${np ? `<button class="btn ghost sm" data-a="deshacer" title="Sacar el último punto (Retroceso)">↶ Último punto</button>
            <button class="btn ghost sm" data-a="tramo" title="El próximo clic empieza otro tramo (el cable sigue por otro lado)">＋ Tramo nuevo</button>
            <button class="btn ghost sm" data-a="borrar" title="Borrar todo el recorrido de este grupo">🗑 Borrar</button>` : ''}
            ${g.n ? '<button class="btn ghost sm" data-a="cablear" title="Cablear de a uno los cables de este grupo">▶ Cablear de a uno</button>' : ''}
            ${g.auto ? '' : '<button class="btn ghost sm" data-a="del" title="Borrar este grupo: sus cables vuelven a su grupo automático">🗑 Borrar grupo</button>'}</div>` : ''}
        </div>`;
      }).join('') + (cablear ? '' : nuevoHtml());
  }
  // (etapa E8-8) la tarjeta de un grupo de placa en la puerta: el haz y sus botones
  function grupoHazHtml(g, on, cablear, hechos) {
    const st = hazEstado(g), t = (g.tramos || []).filter(x => x.vista === VP).slice(-1)[0], np = t ? t.puntos.length : 0;
    return `<div class="sal-g e8m-g ${on ? 'on' : ''}" data-g="${esc(g.id)}">
      <div class="sal-gh"><span class="e8m-sw" style="background:${I().colorGrupo(g.id)}"></span>${g.auto ? `<b>${esc(g.nombre)}</b>` : `<input class="sal-nom" data-nom="${esc(g.id)}" value="${esc(g.nombre)}" aria-label="Nombre del grupo" spellcheck="false">`}
        <span class="muted small">${g.n} cable${g.n === 1 ? '' : 's'}${g.n ? ` · ${hechos} cableado${hechos === 1 ? '' : 's'}` : ''}</span></div>
      <div class="small ${st.ok ? 'sal-eleg' : 'warn-t'}">${esc(st.txt)}</div>
      ${g.tramos_fuera ? `<div class="small warn-t">${esc(fueraTxt(g))}</div>` : ''}
      ${on && !cablear ? `<div class="sal-acts">
        <button class="btn sm ${M.dib ? 'on' : ''}" data-a="dib" title="${M.dib ? 'Terminar (Enter)' : 'Marcar por dónde va el haz: arranca en la entrada a la puerta'}">${M.dib ? '✓ Listo' : np && t.desde === 'entrada' ? '✏ Seguir el haz' : '✏ Dibujar el haz'}</button>
        ${M.dib ? '<button class="btn ghost sm" data-a="curva" title="La esquina del último punto va redondeada (C); se ve al marcar el siguiente">↪ Curva</button>' : ''}
        ${np ? '<button class="btn ghost sm" data-a="deshacer" title="Sacar el último punto (Retroceso)">↶ Último punto</button>' : ''}
        <button class="btn ghost sm" data-a="propuesta" title="Llenar el haz con el tramo común automático: de la entrada baja por la canaleta, corre por el perfil y sube a la placa">Usar la propuesta</button>
        ${g.dibujado ? `<button class="btn ghost sm ${M.final ? 'on' : ''}" data-a="final" title="Ver cómo queda: el haz con sus precintos y cada cable a su pin con su manga">👁 Cómo queda</button>` : ''}
        ${np ? '<button class="btn ghost sm" data-a="borrar" title="Borrar el haz de este grupo">🗑 Borrar</button>' : ''}
        ${g.n ? '<button class="btn ghost sm" data-a="cablear" title="Cablear de a uno los cables de este grupo">▶ Cablear de a uno</button>' : ''}
        ${g.auto ? '' : '<button class="btn ghost sm" data-a="del" title="Borrar este grupo: sus cables vuelven a su grupo automático">🗑 Borrar grupo</button>'}</div>
        ${M.dib ? `<div class="small muted">${esc(HAZ_AYUDA)}</div>` : ''}` : ''}
    </div>`;
  }
  // (2026-10-13, pedido del taller) un grupo de la PLACA ('solo_puerta' en e8_grupos.json) se dibuja a mano solo en la
  // vista de la puerta: en las laterales y el fondo sus cables van por el ruteo automático (hasta la salida a la puerta)
  const SOLO_PUERTA = 'Se dibuja solo en la puerta: en las bandejas laterales y el fondo estos cables van por el ruteo automático (por las canaletas hasta la salida a la puerta).';
  const SIN_PUERTA = 'El topográfico no trae la vista de la puerta: no hay recorrido para dibujar a mano. En las bandejas laterales estos cables van por el ruteo automático (por las canaletas hasta la salida a la puerta).';
  const fueraTxt = g => `${g.tramos_fuera} tramo${g.tramos_fuera > 1 ? 's' : ''} dibujado${g.tramos_fuera > 1 ? 's' : ''} antes fuera de la puerta: se conserva${g.tramos_fuera > 1 ? 'n' : ''} en el archivo pero no se usa${g.tramos_fuera > 1 ? 'n' : ''} (en las laterales y el fondo van por el ruteo automático).`;
  // ＋ Grupo de placa: de qué placa (el aparato del grupo de placa elegido; si no, la única placa del trabajo; con varias,
  // se elige en la lista de al lado). Sin placas en el trabajo queda sin aparato («Placa · grupo N»), al final de la lista
  function placas() {
    const r = R() || {}, s = new Set();
    for (const i of Object.values(r.auto_info || {})) if (i && i.categoria === 'placa' && i.aparato) s.add(i.aparato);
    for (const x of manual(r).nuevos) if (x.categoria === 'placa' && x.aparato) s.add(x.aparato);
    return [...s].sort((a, b) => cmpLista(natk(a), natk(b)));
  }
  function apNuevo() {
    const g = G(), aps = placas();
    if (M.apNuevo && aps.includes(M.apNuevo)) return M.apNuevo;         // (elegida en la lista)
    if (g && g.categoria === 'placa' && g.aparato) return g.aparato;
    return aps[0] || null;
  }
  function nuevoHtml() {
    const aps = placas(), ap = apNuevo(), tit = 'Un grupo más de cables de placa (después movés los cables a este grupo con la lista)';
    if (aps.length < 2) return `<button class="btn sm sal-nuevo" data-a="nuevo" title="${tit}">＋ Grupo de placa${ap ? ' ' + esc(ap) : ''}</button>`;
    return `<div class="e8m-nuevo"><button class="btn sm sal-nuevo" data-a="nuevo" title="${tit}">＋ Grupo de placa</button>
      <select data-ap aria-label="Placa del grupo nuevo" title="Placa del grupo nuevo">${aps.map(a => `<option value="${esc(a)}"${a === ap ? ' selected' : ''}>${esc(a)}</option>`).join('')}</select></div>`;
  }
  function opciones(sel) {
    const r = R();
    return `<option value=""${sel ? '' : ' selected'}>Sin grupo (ruteo automático)</option>` +
      r.grupos.map(g => `<option value="${esc(g.id)}"${g.id === sel ? ' selected' : ''}>${esc(g.nombre)}</option>`).join('');
  }
  function renderLista() {
    const r = R(), g = G(), H = I().hechos(), q = norm(($('#e8mQ').value || '').trim()), m = manual();
    const vh = $('#e8mQ').closest('.vs-h');
    if (M.modo === 'cablear') {
      if (vh) vh.hidden = true;
      $('#e8mList').innerHTML = g.cables.map((k, i) => { const c = cab(k) || {};
        return `<div class="vs-it cv-it${H.has(k) ? ' seen' : ''}${i === M.k ? ' on' : ''}" data-k="${i}" title="${esc(c.a)} → ${esc(c.b)}">
          <input type="checkbox" data-ok ${H.has(k) ? 'checked' : ''} aria-label="Cable ${esc(c.num)} cableado">
          <span class="n">${esc(c.num)}</span>${swatch(c.color)}<span class="sec">${esc(Ins.secTxt(c))}</span><span class="od mono">${esc(c.a)} → ${esc(c.b)}</span></div>`; }).join('')
        || '<div class="vs-empty muted small">Este grupo no tiene cables.</div>';
      $('#e8mCnt').textContent = `${g.cables.filter(k => H.has(k)).length} de ${g.n} cableados`;
      const cur = $('#e8mList').querySelector && $('#e8mList').querySelector('.cv-it.on'); if (cur && cur.scrollIntoView) cur.scrollIntoView({ block: 'nearest' });
      return;
    }
    if (vh) vh.hidden = false;
    const ks = Object.keys(r.cables || {}).filter(k => { const c = r.cables[k]; return !q || norm(`${c.num} ${c.a} ${c.b} ${c.color} ${c.secc} ${(grupo(r.miembro[k]) || {}).nombre || ''}`).includes(q); });
    const enG = ks.filter(k => r.miembro[k] === g.id), otros = ks.filter(k => r.miembro[k] !== g.id);
    const fila = k => { const c = r.cables[k], gid = r.miembro[k] || '', amano = k in m.mover;
      return `<div class="vs-it e8m-it${gid === g.id ? ' act' : ''}${k === M.foco ? ' on' : ''}" data-clave="${esc(k)}" title="${esc(c.a)} → ${esc(c.b)}">
        <span class="n">${esc(c.num)}</span><span class="od mono">${esc(c.a)} → ${esc(c.b)}</span>
        <select data-mover aria-label="Grupo del cable ${esc(c.num)}" title="${amano ? 'Movido a mano por el taller' : 'Grupo automático'}" class="${amano ? 'amano' : ''}">${opciones(gid)}</select></div>`; };
    $('#e8mList').innerHTML = (enG.length ? `<div class="cv-gh">En «${esc(g.nombre)}» (${enG.length})</div>` + enG.map(fila).join('') : '')
      + (otros.length ? `<div class="cv-gh">Otros cables de E8 (${otros.length}) · elegí el grupo para moverlos</div>` + otros.map(fila).join('') : '')
      || '<div class="vs-empty muted small">Ningún cable coincide.</div>';
    const nM = Object.keys(m.mover).length;
    $('#e8mCnt').textContent = `${Object.keys(r.cables || {}).length} cables en E8 · ${Object.keys(r.miembro || {}).length} con ruteo a mano${nM ? ` · ${nM} movido${nM === 1 ? '' : 's'} a mano` : ''}`;
  }
  const ppx = () => { const r = $('#e8mSvg').getBoundingClientRect(), vb = M.vb; return r.width && r.height && vb ? Math.max(vb[2] / r.width, vb[3] / r.height) : 0.3; };
  function dibujar() {
    if (!M.abierto) return;
    const Vv = V(); if (!Vv) { $('#e8mSvg').innerHTML = ''; return; }
    const r = R(), g = G(), u = ppx(), cablear = M.modo === 'cablear', ck = M.vk;
    let s = I().imgTag(Vv, true);
    // las canaletas de la vista, apenas marcadas (adónde se pega el punto)
    if (!cablear && M.dib && M.iman) s += ducts(Vv).map(d => `<rect x="${f2(d.b[0])}" y="${f2(-d.b[3])}" width="${f2(d.b[2] - d.b[0])}" height="${f2(d.b[3] - d.b[1])}" class="e8m-duct" stroke-width="${f2(0.6 * u)}"/>`).join('');
    // los otros grupos, finos; el grupo elegido, grueso con sus puntos numerados
    // (2026-10-13: en el visor de a uno, solo el recorrido del grupo del cable actual; al editar, los otros quedan finos)
    if (!cablear) s += `<g class="e8m-otros">${I().manoG(Vv, u * 0.6, { excluir: g.id }).replace(/<g class="e8-mano"/g, '<g class="e8-mano otro"')}</g>`;
    if (esHaz(g) && ck === VP) return dibujarHaz(s, g, u, cablear);         // (etapa E8-8: el haz de la placa)
    const ts = (g.tramos || []), col = I().colorGrupo(g.id);
    let n = 0;
    ts.forEach((t, ti) => {
      const pts = t.puntos;
      if (t.vista !== ck) { n += pts.length; return; }
      if (pts.length > 1) {
        const d = 'M' + pts.map(p => f2(p[0]) + ' ' + f2(-p[1])).join('L');
        s += `<path d="${d}" class="e8m-halo" stroke-width="${f2(9 * u)}"/><path d="${d}" stroke="${col}" stroke-width="${f2(3.6 * u)}" class="e8m-ruta"/>`;
      }
      const ant = ts[ti - 1], sig = ts[ti + 1];
      if (ant && ant.vista !== ck) s += rotulo(pts[0], `viene de: ${vistaNom(ant.vista)}`, u, col);
      if (sig && sig.vista !== ck) s += rotulo(pts[pts.length - 1], `sigue en: ${vistaNom(sig.vista)}`, u, col);
      if (!cablear) s += pts.map((p, i) => `<g class="sal-pt on${ti === ts.length - 1 && i === pts.length - 1 ? ' fin' : ''}"><circle cx="${f2(p[0])}" cy="${f2(-p[1])}" r="${f2(6.5 * u)}" stroke-width="${f2(1.4 * u)}" style="fill:${col}"/>
        <text x="${f2(p[0])}" y="${f2(-p[1])}" font-size="${f2(7.5 * u)}" text-anchor="middle" dominant-baseline="central">${n + i + 1}</text></g>`).join('');
      n += pts.length;
    });
    // las puntas de los cables del grupo en esta vista (en el visor de a uno: el cable actual, con su acometida)
    const enV = ts.filter(t => t.vista === ck);
    const actual = cablear ? g.cables[M.k] : null;
    for (const k of g.cables) {
      const c = cab(k); if (!c) continue;
      const pts = (c.puntos || {})[ck] || []; if (!pts.length) continue;
      const cur = k === actual, tenue = cablear && !cur;
      for (const p of pts) {
        // (etapa E8-7) al pin de la placa: del FINAL del tramo común; a otro aparato, del punto más cercano
        const q = enV.length && (c.pin_puerta && ck === 'PUERTA' ? I().finTramo(p, enV) : I().cercaDe(p, enV));
        if (q && (cur || !cablear)) s += `<path d="M${f2(p[0])} ${f2(-p[1])}L${f2(q[0])} ${f2(-q[1])}" stroke="${col}" stroke-width="${f2((cur ? 2 : 1) * u)}" stroke-dasharray="${f2(3 * u)} ${f2(2 * u)}" class="e8-mano-a"/>`;
        if (cur && c.aclaracion && c.pin_puerta && ck === 'PUERTA')
          s += `<text x="${f2(p[0] + 5 * u)}" y="${f2(-p[1] + 13 * u)}" class="e8-acl" font-size="${f2(8 * u)}" stroke-width="${f2(2 * u)}">${esc(I().aclCorta(c.aclaracion))}</text>`;
        s += `<g class="e8m-punta${cur ? ' cur' : ''}${tenue ? ' tenue' : ''}"><title>${esc(c.num)}: ${esc(c.a)} → ${esc(c.b)}</title>
          ${cur ? `<circle cx="${f2(p[0])}" cy="${f2(-p[1])}" r="${f2(9 * u)}" class="ori-p" stroke-width="${f2(0.9 * u)}"/>` : ''}
          <circle cx="${f2(p[0])}" cy="${f2(-p[1])}" r="${f2((cur ? 4 : 2.6) * u)}" stroke-width="${f2(0.9 * u)}"/>
          ${!tenue ? `<text x="${f2(p[0] + 5 * u)}" y="${f2(-p[1] - 5 * u)}" font-size="${f2((cur ? 10 : 7) * u)}" stroke-width="${f2(2 * u)}">${esc(c.num)}</text>` : ''}</g>`;
      }
    }
    if (M.fantasma && M.dib) {
      const p = M.fantasma;
      s += `<g class="e8m-fant${p.pegado ? ' peg' : ''}"><circle cx="${f2(p.q[0])}" cy="${f2(-p.q[1])}" r="${f2(5 * u)}" stroke-width="${f2(1.2 * u)}"/>${p.pegado ? `<text x="${f2(p.q[0] + 7 * u)}" y="${f2(-p.q[1] + 3 * u)}" font-size="${f2(8 * u)}" stroke-width="${f2(2 * u)}">al eje</text>` : ''}</g>`;
    }
    $('#e8mSvg').innerHTML = s;
    $('#e8mSvg').classList.toggle('pick', M.dib);
    // aviso grande: este grupo no tiene recorrido (en esta vista o en ninguna)
    const falta = $('#e8mFalta');
    falta.hidden = !(cablear && !g.dibujado) && !(cablear && g.dibujado && !enV.length);
    falta.innerHTML = g.sin_puerta ? esc(SIN_PUERTA) : !g.dibujado ? `${conPines(g) ? `Falta dibujar el tramo común de «${esc(g.nombre)}»: de ahí cada cable va a su pin (ya ubicado en la placa).` : `Falta dibujar el recorrido de «${esc(g.nombre)}».`} <button class="btn sm" data-a="dibujar">✏ Dibujarlo</button>`
      : `El recorrido de este grupo no pasa por esta vista: está en ${esc(tramosTxt(g))}.`;
  }
  // (etapa E8-8) el haz de un grupo de placa en la puerta: el haz con su abanico (con las mangas en «👁 Cómo queda» y en
  // el visor de a uno, con el cable actual resaltado) y, al editar, la entrada donde arranca y los puntos marcados
  function dibujarHaz(s, g, u, cablear) {
    const info = I().hazDe(g), ent = entradaP(), t = tramoHaz(g.id, false), col = I().colorGrupo(g.id);
    const actual = cablear ? g.cables[M.k] : null;
    if (info) s += I().hazG(info, { cur: actual, mangas: M.final || cablear });
    const desde = !t || t.desde === 'entrada';
    if (!cablear) {
      if (ent && desde) s += `<g class="e8m-ent"><title>El haz arranca en la entrada a la puerta (se cambia con 🧭 Entrada / recorrido)</title><circle cx="${f2(ent[0])}" cy="${f2(-ent[1])}" r="${f2(6.5 * u)}" stroke-width="${f2(1.4 * u)}"/>
        <text x="${f2(ent[0] - 9 * u)}" y="${f2(-ent[1] - 10 * u)}" font-size="${f2(9 * u)}" stroke-width="${f2(2.4 * u)}" text-anchor="end">arranca en la entrada</text></g>`;
      if (t && !info && t.puntos.length) {      // (un solo punto, o un tramo de antes sin dibujar: la línea)
        const pts = (desde && ent ? [ent] : []).concat(t.puntos);
        if (pts.length > 1) s += `<path d="M${pts.map(p => f2(p[0]) + ' ' + f2(-p[1])).join('L')}" stroke="${col}" stroke-width="${f2(3.6 * u)}" class="e8m-ruta"/>`;
      }
      if (t) {
        const cv = new Set(t.curvas || []), n = t.puntos.length;
        s += t.puntos.map((p, i) => `<g class="sal-pt on${i === n - 1 ? ' fin' : ''}${cv.has(i) ? ' curva' : ''}"><title>Punto ${i + 1}${cv.has(i) ? ' · esquina redondeada (curva)' : ''}${M.dib ? ' · Mayús+clic: curva sí / no' : ''}</title>
          ${cv.has(i) ? `<circle cx="${f2(p[0])}" cy="${f2(-p[1])}" r="${f2(10 * u)}" class="e8m-curva" stroke-width="${f2(1.6 * u)}"/>` : ''}
          <circle cx="${f2(p[0])}" cy="${f2(-p[1])}" r="${f2(6.5 * u)}" stroke-width="${f2(1.4 * u)}" style="fill:${col}"/>
          <text x="${f2(p[0])}" y="${f2(-p[1])}" font-size="${f2(7.5 * u)}" text-anchor="middle" dominant-baseline="central">${cv.has(i) ? '↪' : i + 1}</text></g>`).join('');
      }
      if (M.fantasma && M.dib) {
        const last = t && t.puntos.length ? t.puntos[t.puntos.length - 1] : (desde ? ent : null), q = M.fantasma.q;
        if (last) s += `<path d="M${f2(last[0])} ${f2(-last[1])}L${f2(q[0])} ${f2(-q[1])}" stroke="${col}" stroke-width="${f2(2 * u)}" stroke-dasharray="${f2(5 * u)} ${f2(4 * u)}" class="e8-mano-a"/>`;
        s += `<g class="e8m-fant${M.fantasma.pegado ? ' peg' : ''}"><circle cx="${f2(q[0])}" cy="${f2(-q[1])}" r="${f2(5 * u)}" stroke-width="${f2(1.2 * u)}"/>${M.fantasma.pegado ? `<text x="${f2(q[0] + 7 * u)}" y="${f2(-q[1] + 3 * u)}" font-size="${f2(8 * u)}" stroke-width="${f2(2 * u)}">al eje</text>` : ''}</g>`;
      }
    }
    // los pines de los cables del grupo (sin el haz dibujado) y, en el visor de a uno, el del cable actual con su aclaración
    for (const k of g.cables) {
      const c = cab(k); if (!c) continue;
      const cur = k === actual, p = ((c.puntos || {})[VP] || [])[0]; if (!p || (info && !cur)) continue;
      if (cur && c.aclaracion && c.pin_puerta)
        s += `<text x="${f2(p[0] + 5 * u)}" y="${f2(-p[1] + 13 * u)}" class="e8-acl" font-size="${f2(8 * u)}" stroke-width="${f2(2 * u)}">${esc(I().aclCorta(c.aclaracion))}</text>`;
      s += `<g class="e8m-punta${cur ? ' cur' : ''}${cablear && !cur ? ' tenue' : ''}"><title>${esc(c.num)}: ${esc(c.a)} → ${esc(c.b)}</title>
        ${cur ? `<circle cx="${f2(p[0])}" cy="${f2(-p[1])}" r="${f2(9 * u)}" class="ori-p" stroke-width="${f2(0.9 * u)}"/>` : ''}
        ${info ? '' : `<circle cx="${f2(p[0])}" cy="${f2(-p[1])}" r="${f2((cur ? 4 : 2.6) * u)}" stroke-width="${f2(0.9 * u)}"/>`}</g>`;
    }
    $('#e8mSvg').innerHTML = s;
    $('#e8mSvg').classList.toggle('pick', M.dib);
    const falta = $('#e8mFalta');
    falta.hidden = !(cablear && !g.dibujado);
    falta.innerHTML = `Falta dibujar el haz de «${esc(g.nombre)}»: arranca en la entrada a la puerta y de su final cada cable va solo a su pin (ya ubicado en la placa). <button class="btn sm" data-a="dibujar">✏ Dibujarlo</button>`;
  }
  function rotulo(p, txt, u, col) {
    return `<text x="${f2(p[0] + 8 * u)}" y="${f2(-p[1] + 12 * u)}" font-size="${f2(9 * u)}" class="e8m-rot" stroke-width="${f2(2.4 * u)}" style="fill:${col}">${esc(txt)}</text>`;
  }
  function hint() {
    $('#e8mHint').textContent = M.modo === 'cablear'
      ? '→ siguiente (marca el cable como cableado) · ← anterior · Espacio: marcar/desmarcar · V: otra vista · Rueda: zoom · Arrastrar: mover · 0: toda la vista · Esc: volver'
      : M.dib && esHaz(G()) ? `Haz de «${G().nombre}»: arranca en la entrada a la puerta (el punto verde) · clic por donde va, en orden · C: curva en el último punto (Mayús+clic en un punto: curva sí / no)${M.iman ? ' · cerca de una canaleta el punto se pega a su eje (I: apagar)' : ''} · Retroceso: sacar el último punto · Enter: listo · Esc: cancelar`
      : M.dib ? `Dibujando «${(G() || {}).nombre}»: clic por donde pasan los cables, en orden; en otra vista sigue con un tramo nuevo${M.iman ? ' · cerca de una canaleta el punto se pega a su eje (I: apagar)' : ''} · Retroceso: sacar el último punto · Enter: listo`
        : esHaz(G()) ? 'Grupo de placa: ✏ Dibujar el haz (arranca en la entrada a la puerta y de su final cada cable va solo a su pin) o «Usar la propuesta» · 👁 Cómo queda · cambiá un cable de grupo con la lista · Rueda: zoom · Arrastrar: mover · 0: toda la vista · Esc: cerrar'
        : 'Elegí un grupo y ✏ Dibujar recorrido · cambiá un cable de grupo con la lista · Rueda: zoom · Arrastrar: mover · 0: toda la vista · Esc: cerrar';
  }
  const redibujar = () => { cancelAnimationFrame(M.raf); M.raf = requestAnimationFrame(dibujar); };

  /* ---- cambios del taller: se aplican enseguida y se guardan en el servidor (por producto o en el trabajo) ---- */
  function cambio(rerender = true) {
    efectivo(R()); I().aplicarMano(R());
    if (rerender) renderTodo();
    programarGuardado();
  }
  function setEstado(t) { M.estado = t; const el = $('#e8mProd'); if (el && M.abierto) renderProd(); }
  function programarGuardado() { clearTimeout(M.t); M.pend = true; setEstado('Guardando…'); M.t = setTimeout(guardar, 450); }
  async function guardar() {
    if (M.guardando) { clearTimeout(M.t); M.t = setTimeout(guardar, 300); return; }
    const r = R(), job = Ins.job; if (!r) return;
    M.guardando = true; M.pend = false;
    let resp = null, data = null, err = null;
    try {
      resp = await fetch(`/api/trabajo/${job}/e8/grupos`, { method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manual: manual(r), version: r.por_producto ? (r.version_almacen || 0) : null }) });
      data = await resp.json().catch(() => null);
    } catch (e) { err = e; }
    M.guardando = false;
    if (job !== Ins.job || !R()) return;
    if (err || !resp || !resp.ok) {
      if (resp && resp.status === 409 && data && data.ruteo_mano) {
        efectivo(data.ruteo_mano); I().aplicarMano(data.ruteo_mano); setEstado('Recargado: lo cambió otro trabajo');
        toast(data.error || 'Otro trabajo del mismo producto cambió el ruteo a mano: se recargó', 7000);
        renderTodo(); return;
      }
      setEstado('No se pudo guardar'); toast('No se pudo guardar el ruteo a mano: ' + ((data && data.error) || (err && err.message) || ''), 6000); return;
    }
    const nuevo = data.ruteo_mano;
    if (M.pend) {            // (otro cambio mientras se guardaba: se guarda de nuevo, sin pisar lo de la pantalla)
      Object.assign(r, { version_almacen: nuevo.version_almacen, editado: nuevo.editado, trabajos: nuevo.trabajos, clave_producto: nuevo.clave_producto, por_producto: nuevo.por_producto, aviso: nuevo.aviso });
      return;
    }
    efectivo(nuevo); I().aplicarMano(nuevo);
    setEstado(nuevo.por_producto ? 'Guardado para el producto' : 'Guardado en este trabajo');
    if (M.abierto) renderTodo();
  }

  function setDib(on) {
    const g = G();
    if (on && g && g.sin_puerta) return toast(SIN_PUERTA, 6000);
    if (on && esHaz(g)) {               // (etapa E8-8) el haz de la placa: en la puerta, arranca en la entrada
      if (M.vk !== VP) elegirVista(VP, true);
      const snap = JSON.stringify(manual().grupos[g.id] || null), t = tramoHaz(g.id, false);
      if (t && t.puntos.length && t.desde !== 'entrada') {
        if (!confirm(`El haz de «${g.nombre}» se dibujó antes, sin arrancar en la entrada a la puerta. ¿Lo empezás de nuevo desde la entrada?

Aceptar: empezás de nuevo · Cancelar: queda como está`)) return;
        const mg = manual().grupos[g.id];
        mg.tramos = mg.tramos.filter(x => x.vista !== VP);
      }
      if (!M.dib) M.snap = snap;
      tramoHaz(g.id, true);
      M.dib = true; M.fantasma = null; M.final = false;
      return cambio();
    }
    if (!on) M.snap = null;
    M.dib = !!on; M.fantasma = null;
    if (M.dib) { const ts = (G().tramos || []); M.nuevoTramo = !ts.length || ts[ts.length - 1].vista !== M.vk; }
    renderTodo();
  }
  // (etapa E8-8) Esc mientras se dibuja el haz: vuelve a como estaba antes de empezar a dibujar
  function cancelarHaz() {
    const m = manual(), g = G(), snap = M.snap != null ? JSON.parse(M.snap) : null;
    if (snap) m.grupos[g.id] = snap; else delete m.grupos[g.id];
    M.snap = null; M.dib = false; M.fantasma = null;
    toast('Cancelado: el haz quedó como estaba', 3000);
    cambio();
  }
  // C / ↪ Curva: la esquina del punto i (por defecto el último) va redondeada, o deja de ir
  function curva(i) {
    const g = G(); if (!esHaz(g)) return;
    const t = tramoHaz(g.id, false);
    if (!t || !t.puntos.length) return toast('Primero marcá un punto: la curva redondea la esquina de ese punto', 4000);
    if (i == null) i = t.puntos.length - 1;
    const cv = new Set(t.curvas || []), on = !cv.has(i);
    if (on) cv.add(i); else cv.delete(i);
    t.curvas = [...cv].sort((a, b) => a - b);
    toast(on ? `Punto ${i + 1}: la esquina va en curva${i === t.puntos.length - 1 ? ' (se ve al marcar el siguiente punto)' : ''}` : `Punto ${i + 1}: esquina recta`, 3000);
    cambio();
  }
  // «Usar la propuesta»: el tramo común automático de E8-4 (de la entrada baja por la canaleta, corre por el perfil y
  // sube a la placa) hasta la base del abanico (el servidor, POST /e8/haz, con la entrada y la bisagra de la pantalla)
  async function propuestaHaz() {
    const g = G(); if (!esHaz(g)) return;
    const t0 = tramoHaz(g.id, false);
    if (t0 && t0.puntos.length && !confirm(`¿Reemplazar el haz dibujado de «${g.nombre}» por la propuesta?`)) return;
    let r = null;
    try {
      r = await api(`/api/trabajo/${Ins.job}/e8/haz`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ claves: g.cables, recorridos: I().REC() }) });
    } catch (e) { return toast('No se pudo armar la propuesta: ' + e.message, 6000); }
    if (!r || !Array.isArray(r.puntos) || !r.puntos.length || G() !== g) return toast('No hay propuesta para este grupo', 4000);
    if (!M.dib) M.snap = JSON.stringify(manual().grupos[g.id] || null);
    const mg = manual().grupos[g.id] = manual().grupos[g.id] || { tramos: [] };
    mg.tramos = (Array.isArray(mg.tramos) ? mg.tramos : []).filter(x => x.vista !== VP)
      .concat([{ vista: VP, puntos: r.puntos.map(p => [+p[0], +p[1]]), curvas: (r.curvas || []).filter(Number.isInteger), desde: 'entrada' }]);
    if (M.vk !== VP) elegirVista(VP, true);
    toast('Listo: el haz sigue el tramo común automático (baja por la canaleta, corre por el perfil y sube a la placa). Podés seguir marcando puntos o sacarlos con Retroceso', 6000);
    cambio();
  }
  function agregarPunto(p) {
    if (G().solo_puerta && M.vk !== VP) return toast(G().sin_puerta ? SIN_PUERTA : SOLO_PUERTA, 5000);
    if (esHaz(G())) {
      const t = tramoHaz(G().id, true);
      t.puntos.push([Math.round(p[0] * 100) / 100, Math.round(p[1] * 100) / 100]);
      return cambio();
    }
    const m = manual(), g = G(), mg = m.grupos[g.id] = m.grupos[g.id] || { tramos: [] };
    if (!Array.isArray(mg.tramos)) mg.tramos = [];
    const last = mg.tramos[mg.tramos.length - 1];
    const q = [Math.round(p[0] * 100) / 100, Math.round(p[1] * 100) / 100];
    if (!last || last.vista !== M.vk || M.nuevoTramo) mg.tramos.push({ vista: M.vk, puntos: [q] });
    else last.puntos.push(q);
    M.nuevoTramo = false;
    cambio();
  }
  function deshacer() {
    if (esHaz(G())) {                    // (el haz: el último punto marcado y su curva)
      const t = tramoHaz(G().id, false); if (!t || !t.puntos.length) return;
      t.puntos.pop(); t.curvas = (t.curvas || []).filter(i => i < t.puntos.length);
      return cambio();
    }
    const m = manual(), mg = m.grupos[M.gi]; if (!mg || !(mg.tramos || []).length) return;
    const t = mg.tramos[mg.tramos.length - 1]; t.puntos.pop();
    if (!t.puntos.length) mg.tramos.pop();
    if (mg.tramos.length && mg.tramos[mg.tramos.length - 1].vista !== M.vk) elegirVista(mg.tramos[mg.tramos.length - 1].vista, false);
    M.nuevoTramo = false;
    cambio();
  }
  function accion(a) {
    const g = G(), m = manual();
    if (a === 'dib') return setDib(!M.dib);
    if (a === 'deshacer') return deshacer();
    if (a === 'tramo') { M.nuevoTramo = true; if (!M.dib) setDib(true); return toast('El próximo clic empieza otro tramo del recorrido', 3000); }
    if (a === 'borrar') {
      if (!confirm(`¿Borrar ${esHaz(g) ? 'el haz' : 'todo el recorrido'} dibujado de «${g.nombre}»?${R().por_producto ? ' Se borra para todos los trabajos del producto.' : ''}`)) return;
      // (el haz: solo el de la puerta; lo dibujado antes en otra vista se conserva, como en estacion8_mano.aplicar)
      if (m.grupos[g.id]) { m.grupos[g.id].tramos = esHaz(g) ? (m.grupos[g.id].tramos || []).filter(x => x.vista !== VP) : []; if (!m.grupos[g.id].tramos.length && !m.grupos[g.id].nombre) delete m.grupos[g.id]; }
      M.dib = false; M.snap = null; M.final = false; return cambio();
    }
    if (a === 'curva') return curva();
    if (a === 'propuesta') return propuestaHaz();
    if (a === 'final') {               // 👁 Cómo queda: con las mangas, encuadrado en la placa
      M.final = !M.final;
      const info = M.final && I().hazDe(g), b = info && I().cajaHaz(info);
      if (b) { const mg = 0.35 * ((I().P() || {}).H || 24.8); setVb(I().vbOf([b[0] - mg, b[1] - mg, b[2] + mg, b[3] + mg])); }
      return renderTodo();
    }
    if (a === 'cablear') { M.modo = 'cablear'; M.deEditar = true; M.dib = false; M.k = 0; elegirVista(null, true); encuadrarHaz(); return renderTodo(); }
    if (a === 'grupos') { M.modo = 'editar'; M.deEditar = false; return renderTodo(); }
    if (a === 'dibujar') { M.modo = 'editar'; M.deEditar = false; return setDib(true); }
    if (a === 'del') {
      if (!confirm(`¿Borrar el grupo «${g.nombre}»? Sus cables vuelven a su grupo automático.`)) return;
      m.nuevos = m.nuevos.filter(x => x.id !== g.id); delete m.grupos[g.id];
      for (const [k, v] of Object.entries(m.mover)) if (v === g.id) delete m.mover[k];
      M.gi = null; M.dib = false; efectivo(R()); M.gi = (R().grupos[0] || {}).id; return cambio();
    }
    if (a === 'nuevo') {
      const ap = apNuevo();
      const n = R().grupos.filter(x => x.categoria === 'placa' && (x.aparato || null) === ap).length + 1;
      const id = 'nuevo:' + Date.now().toString(36);
      m.nuevos.push({ id, nombre: `Placa${ap ? ' ' + ap : ''} · grupo ${n}`, categoria: 'placa', aparato: ap || null });
      M.gi = id; M.dib = false;
      toast('Grupo nuevo de placa: elegí sus cables en la lista (columna del grupo) y después ✏ Dibujar recorrido', 5000);
      return cambio();
    }
  }
  function mover(k, gid) {
    const r = R(), m = manual(), auto = (r.auto || {})[k] || '';
    if (gid === auto) delete m.mover[k]; else m.mover[k] = gid;
    cambio();
  }

  /* ---- visor de a uno del grupo ---- */
  function irA(d, marca = d > 0) {
    const g = G(); if (!g.n) return;
    const k = g.cables[M.k];
    if (marca && !I().esHecho(k)) { I().marcar(k, true); if (g.cables.every(x => I().esHecho(x))) toast(`¡«${g.nombre}» cableado! Los ${g.n} cables están marcados.`, 6000); }
    M.k = Math.max(0, Math.min(g.n - 1, M.k + d));
    const vs = vistasDelGrupo(); if (!vs.includes(M.vk)) elegirVista(null, true);
    renderTodo();
  }
  function toggleOk() {
    const g = G(); if (!g.n) return;
    const k = g.cables[M.k], on = !I().esHecho(k); I().marcar(k, on);
    if (on && M.k < g.n - 1) irA(1, false); else renderTodo();
  }
  function otraVista() {
    const vs = [...$('#e8mVistas').querySelectorAll('[data-vk]')].map(b => b.dataset.vk);
    const todos = vs.length ? vs : vistasDelGrupo(); if (!todos.length) return;
    elegirVista(todos[(todos.indexOf(M.vk) + 1) % todos.length], true); renderTodo();
  }

  /* ---- eventos ---- */
  function svgPt(e) {
    const r = $('#e8mSvg').getBoundingClientRect(), vb = M.vb;
    const s = Math.max(vb[2] / r.width, vb[3] / r.height);
    const ox = (r.width * s - vb[2]) / 2, oy = (r.height * s - vb[3]) / 2;
    return [vb[0] - ox + (e.clientX - r.left) * s, vb[1] - oy + (e.clientY - r.top) * s, s];
  }
  const setVb = vb => { M.vb = vb; $('#e8mSvg').setAttribute('viewBox', vb.map(f2).join(' ')); redibujar(); };
  function punto(e) {
    const [x, y] = svgPt(e), p = [x, -y];
    const q = M.iman ? iman(p, ducts(V())) : null;
    return { q: q || p, pegado: !!q };
  }
  function init() {
    $('#e8mClose').addEventListener('click', () => { M.dib = false; M.deEditar = false; cerrar(); });
    $('#e8mVolver').addEventListener('click', () => { M.dib = false; M.deEditar = false; cerrar(); });
    $('#e8mFit').addEventListener('click', () => { const Vv = V(); if (Vv) setVb(I().vbOf(Vv.region)); });
    $('#e8mIman').addEventListener('click', () => { M.iman = !M.iman; renderTodo(); });
    $('#e8mPrev').addEventListener('click', () => irA(-1));
    $('#e8mNext').addEventListener('click', () => irA(1));
    $('#e8mOk').addEventListener('change', () => toggleOk());
    $('#e8mVistas').addEventListener('click', e => { const b = e.target.closest('[data-vk]'); if (!b) return; elegirVista(b.dataset.vk, true); renderTodo(); });
    $('#e8mFalta').addEventListener('click', e => { if (e.target.closest('[data-a="dibujar"]')) accion('dibujar'); });
    $('#e8mGrupos').addEventListener('click', e => {
      const b = e.target.closest('[data-a]');
      if (b) return accion(b.dataset.a);
      const c = e.target.closest('.e8m-g');
      if (c && !e.target.matches('.sal-nom') && c.dataset.g !== M.gi) { M.gi = c.dataset.g; M.dib = false; M.k = 0; M.apNuevo = null; elegirVista(null, false); renderTodo(); }
    });
    $('#e8mGrupos').addEventListener('change', e => {
      if (e.target.matches('[data-ap]')) { M.apNuevo = e.target.value || null; return; }        // (placa del grupo nuevo)
      if (!e.target.matches('.sal-nom')) return;
      const m = manual(), x = m.nuevos.find(y => y.id === e.target.dataset.nom), nom = e.target.value.trim();
      if (x && nom) { x.nombre = nom.slice(0, 80); cambio(); }
    });
    $('#e8mGrupos').addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.matches('.sal-nom')) { e.preventDefault(); e.target.blur(); } });
    $('#e8mList').addEventListener('change', e => {
      const s = e.target.closest('[data-mover]'); if (!s) return;
      const it = s.closest('[data-clave]'); if (it) mover(it.dataset.clave, s.value);
    });
    $('#e8mList').addEventListener('click', e => {
      const it = e.target.closest('.cv-it'); if (!it || M.modo !== 'cablear') return;
      const g = G(), k = g.cables[+it.dataset.k];
      if (e.target.matches('[data-ok]')) { I().marcar(k, e.target.checked); return renderTodo(); }
      M.k = +it.dataset.k; const vs = vistasDelGrupo(); if (!vs.includes(M.vk)) elegirVista(null, true); renderTodo();
    });
    let qT; $('#e8mQ').addEventListener('input', () => { clearTimeout(qT); qT = setTimeout(renderLista, 80); });
    $('#e8mQ').addEventListener('keydown', e => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); if (e.target.value) { e.target.value = ''; renderLista(); } else e.target.blur(); } });
    const svg = $('#e8mSvg');
    svg.addEventListener('wheel', e => {
      e.preventDefault(); if (!M.vb) return;
      const [px, py] = svgPt(e), f = Math.pow(1.0015, e.deltaY), vb = M.vb;
      setVb([px - (px - vb[0]) * f, py - (py - vb[1]) * f, vb[2] * f, vb[3] * f]);
    }, { passive: false });
    svg.addEventListener('pointerdown', e => {
      if (e.button !== 0 || !M.vb) return;
      const p = svgPt(e);
      M.drag = { x: e.clientX, y: e.clientY, vb: M.vb.slice(), s: p[2] };
      svg.setPointerCapture(e.pointerId); svg.classList.add('drag');
    });
    svg.addEventListener('pointermove', e => {
      const d = M.drag;
      if (!d) { if (M.dib) { M.fantasma = punto(e); redibujar(); } return; }
      setVb([d.vb[0] - (e.clientX - d.x) * d.s, d.vb[1] - (e.clientY - d.y) * d.s, d.vb[2], d.vb[3]]);
    });
    svg.addEventListener('pointerleave', () => { if (M.fantasma) { M.fantasma = null; redibujar(); } });
    svg.addEventListener('pointerup', e => {
      const d = M.drag; M.drag = null; svg.classList.remove('drag');
      if (!d || Math.hypot(e.clientX - d.x, e.clientY - d.y) >= 5) return;      // (fue un arrastre)
      if (!(M.dib && M.modo === 'editar')) return;
      if (e.shiftKey && esHaz(G())) {        // (el haz) Mayús+clic en un punto marcado: su esquina en curva sí / no
        const t = tramoHaz(G().id, false), [x, y, sc] = svgPt(e);
        let best = -1, bd = 12 * sc;
        ((t && t.puntos) || []).forEach((q, i) => { const d = Math.hypot(q[0] - x, q[1] + y); if (d < bd) { bd = d; best = i; } });
        if (best >= 0) return curva(best);
      }
      agregarPunto(punto(e).q);
    });
    window.addEventListener && window.addEventListener('resize', () => { if (M.abierto) redibujar(); });
    document.addEventListener('keydown', e => {
      if (!M.abierto) return;
      if (e.target.isContentEditable || (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox') || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
      const k = e.key;
      if (k === 'Escape') { e.preventDefault(); return cerrar(); }
      if (k === '0') { e.preventDefault(); const Vv = V(); if (Vv) setVb(I().vbOf(Vv.region)); return; }
      if (M.modo === 'cablear') {
        const keys = { ArrowRight: () => irA(1), ArrowLeft: () => irA(-1), ' ': toggleOk, Enter: toggleOk, v: otraVista, V: otraVista };
        if (keys[k]) { e.preventDefault(); keys[k](); }
        return;
      }
      if (k === 'Enter' && M.dib) { e.preventDefault(); return setDib(false); }
      if (k === 'Backspace' && M.dib) { e.preventDefault(); return deshacer(); }
      if ((k === 'c' || k === 'C') && M.dib && esHaz(G())) { e.preventDefault(); return curva(); }
      if (k === 'i' || k === 'I') { e.preventDefault(); M.iman = !M.iman; return renderTodo(); }
    });
  }
  // (pruebas de node: lo que hacen los botones y las teclas del haz de la placa)
  const prueba = { setDib, agregarPunto, deshacer, curva, propuestaHaz, cancelarHaz, accion, estado: () => M };
  return { abrir, init, abierto: () => M.abierto, efectivo, iman, prueba };
})();
E8M.init();
