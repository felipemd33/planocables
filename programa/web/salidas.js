'use strict';
/* Salidas a LI / LD: por dónde salen de la bandeja los cables que van al lateral izquierdo (LI) o al derecho (LD).
   Se eligen a mano por GRUPO de cables: todos los de un lateral, o un grupo de cables elegidos (manda sobre el de su
   lateral). El recorrido son los puntos por donde pasan los cables, en orden, y el último es por donde salen de la
   bandeja. Sin recorrido vale la regla del taller (por el lateral, arriba; los marrones y blancos de 220 VAC por abajo;
   los intrínsecos por su canaleta). Los intrínsecos no entran en «todos»: se cambian eligiéndolos en un grupo.
   Se guarda en ins.salidas = {grupos: [{id, nombre, aplica: 'LI' | 'LD' | 'seleccion', cables, puntos}]} y el
   servidor rutea igual al regenerar (instructivo.grupo_salida).
   ASISTENTE: al cargar el topográfico el servidor deja ins.salidas.preguntar y, la primera vez que se ve el
   instructivo, se pregunta una sola vez por dónde salen los de LI y después los de LD (un paso por lateral). */
const Sal = (() => {
  const E = { act: 0, modo: null, nuevo: false, vb: null, drag: null, rect: null, volver: null, foco: null, seq: 0, t: null, raf: 0, asis: null };
  const D = () => Ins.D;
  const LATS = [['LI', 'Todos los LI'], ['LD', 'Todos los LD']];
  const f2 = v => (+v).toFixed(2);
  const pts = g => (g && Array.isArray(g.puntos)) ? g.puntos : [];
  const lat = l => l.lateral || l.destino;
  const intr = l => ('intrinseco' in l) ? !!l.intrinseco : norm(l.color) === 'azul';    // (instructivo viejo: por el color)
  // cables de la bandeja que salen a un lateral, y los de otra estación (E8) o quitados del instructivo que arrancan en
  // la bandeja (se rutean igual: si vuelven al instructivo, ya salen por donde se eligió)
  const cables = () => Ins.flat().map(x => x.l).filter(l => Ins.LAT(l.destino));
  const deOtra = () => [...((D() || {}).otra_estacion || []), ...((D() || {}).quitados || []).filter(l => !l.pendiente)]
    .filter(l => Ins.LAT(l.lateral) && l.ruta && l.marca_o);
  function grupos() {
    const d = D();
    if (!d.salidas || typeof d.salidas !== 'object') d.salidas = {};
    if (!Array.isArray(d.salidas.grupos)) d.salidas.grupos = [];
    return d.salidas.grupos;
  }
  // los grupos de todos los cables de cada lateral siempre estan, primero
  function asegurar() {
    const gs = grupos();
    LATS.forEach(([a, nombre], i) => { if (!gs.some(g => g.aplica === a)) gs.splice(i, 0, { id: a.toLowerCase(), nombre, aplica: a, puntos: [] }); });
  }
  const conRec = () => grupos().filter(g => pts(g).length);
  // el grupo que manda en el recorrido del cable (como instructivo.grupo_salida): null = regla del taller
  const grupoDe = l => conRec().find(g => g.aplica === 'seleccion' && (g.cables || []).includes(l.num))
    || (!intr(l) && conRec().find(g => g.aplica === lat(l))) || null;
  // cables de un grupo: los elegidos, o los de su lateral (sin los intrínsecos ni los que se llevó un grupo de elegidos)
  function miembros(g) {
    if (!g) return [];
    if (g.aplica === 'seleccion') return cables().filter(l => (g.cables || []).includes(l.num));
    const otros = new Set(conRec().filter(s => s.aplica === 'seleccion').flatMap(s => s.cables || []));
    return cables().filter(l => lat(l) === g.aplica && !intr(l) && !otros.has(l.num));
  }
  const latDe = g => g.aplica !== 'seleccion' ? g.aplica : (s => s.size === 1 ? [...s][0] : 'salida')(new Set(miembros(g).map(lat)));
  function recTxt(g) {
    const n = pts(g).length;
    if (!n) return g.aplica === 'seleccion' ? 'Sin recorrido: siguen la salida de su lateral' : 'Automático (regla del taller)';
    return n === 1 ? 'Elegido: salen por el punto marcado' : `Elegido: pasan por ${n - 1} punto${n > 2 ? 's' : ''} y salen por el último`;
  }

  /* ---- abrir y cerrar ---- */
  function open(o = {}) {
    const d = D();
    if (!d) return toast('Todavía no hay instructivo');
    if (!(d.topo && (d.topo.ductos || []).length)) return toast('El topográfico no tiene cablecanales: no se puede elegir la salida', 5000);
    if (!cables().length) return toast('Ningún cable de la bandeja sale a LI o LD');
    asegurar();
    const gs = grupos();
    E.volver = o.volver ?? null; E.foco = o.num || null; E.modo = null; E.rect = null; E.asis = null;
    const l = o.num && cables().find(x => x.num === o.num);
    let k = -1;
    if (l) k = gs.indexOf(grupoDe(l) || gs.find(g => g.aplica === lat(l)));
    else if (!cables().some(x => lat(x) === 'LI')) k = gs.findIndex(g => g.aplica === 'LD');
    E.act = Math.max(0, k);
    $('#salViewer').hidden = false; document.body.style.overflow = 'hidden';
    if (document.activeElement) document.activeElement.blur();
    $('#salVolver').hidden = E.volver == null;
    $('#salQ').value = '';
    $('#salSvg').innerHTML = Ins.imgTag(true) + '<g id="salRutas"></g><g id="salMarcas"></g>';
    E.vb = fit(); $('#salSvg').setAttribute('viewBox', E.vb.map(f2).join(' '));
    render();
  }
  function close() {
    if ($('#salViewer').hidden) return;
    if (E.asis) return terminarAsis();
    setModo(null);
    $('#salViewer').hidden = true; document.body.style.overflow = '';
    if (E.volver != null) Ins.openViewer(E.volver);
    else if (!$('#insWrap').hidden) Ins.render();
  }
  // encuadre: las canaletas, los recorridos a LI / LD y los puntos elegidos (no toda la hoja de la bandeja)
  function fit() {
    const d = D(), r = d.topo.region, p = 14;
    const xs = [], ys = [];
    for (const c of d.topo.ductos || []) { xs.push(c.b[0], c.b[2]); ys.push(c.b[1], c.b[3]); }
    for (const l of cables()) for (const q of l.ruta || []) { xs.push(q[0]); ys.push(q[1]); }
    for (const g of grupos()) for (const q of pts(g)) { xs.push(q[0]); ys.push(q[1]); }
    if (!xs.length) return Ins.vbOf([r[0] - p, r[1] - p, r[2] + p, r[3] + p]);
    return Ins.vbOf([Math.min(...xs) - p, Math.min(...ys) - p, Math.max(...xs) + p, Math.max(...ys) + p]);
  }

  /* ---- asistente: una sola vez, al cargar el topográfico (un paso por lateral con cables) ---- */
  function asistente() {
    const d = D(); if (!d || !(d.salidas && d.salidas.preguntar) || !$('#salViewer').hidden) return;
    const lats = LATS.map(x => x[0]).filter(a => cables().some(l => lat(l) === a));
    if (!(d.topo && (d.topo.ductos || []).length) || !lats.length) { delete d.salidas.preguntar; Ins.dirty(); return; }
    open({});
    E.asis = { pasos: lats, i: 0 };
    pasoAsis();
  }
  function pasoAsis() {
    const gs = grupos(), a = E.asis.pasos[E.asis.i];
    E.act = Math.max(0, gs.findIndex(g => g.aplica === a)); E.foco = null;
    setModo('recorrido');
  }
  function sigAsis() {
    if (!E.asis) return;
    if (E.asis.i < E.asis.pasos.length - 1) { E.asis.i++; return pasoAsis(); }
    terminarAsis();
  }
  function terminarAsis() {
    const d = D(); E.asis = null;
    if (d.salidas) delete d.salidas.preguntar;
    Ins.dirty();
    const n = cables().filter(grupoDe).length;
    toast(n ? `Listo: ${n} cable${n === 1 ? '' : 's'} a LI / LD salen por donde marcaste. Para cambiarlo: 🧭 Salidas LI / LD`
      : 'Quedó la salida automática (regla del taller). Para elegirla: 🧭 Salidas LI / LD', 5000);
    close();
  }
  function renderAsis() {
    const el = $('#salAsis'); el.hidden = !E.asis; if (!E.asis) { el.innerHTML = ''; return; }
    const { pasos, i } = E.asis, a = pasos[i], g = grupos().find(x => x.aplica === a), n = miembros(g).length, P = pts(g);
    const nombre = a === 'LI' ? 'lateral izquierdo' : 'lateral derecho', ult = i === pasos.length - 1;
    const marcado = P.length ? (P.length === 1 ? 'Marcado: salen por el punto naranja' : `Marcado: pasan por ${P.length - 1} punto${P.length > 2 ? 's' : ''} y salen por el naranja`)
      : 'Todavía sin marcar: si seguís, queda la salida automática (regla del taller)';
    el.innerHTML = `<div class="sal-asis-t">${pasos.length > 1 ? `Paso ${i + 1} de ${pasos.length} · ` : ''}¿Por dónde salen de la bandeja los cables a <b>${a}</b> (${nombre})? <span class="muted small">${n} cable${n === 1 ? '' : 's'}</span></div>
      <div class="small">Hacé clic en el dibujo por donde salen: en la punta de una canaleta o a su costado. Si antes tienen que pasar por otro lado, marcá esos puntos primero: el último clic es la salida.</div>
      <div class="small ${P.length ? 'sal-eleg' : 'muted'}">${marcado}</div>
      <div class="sal-asis-b">
        ${P.length ? '<button class="btn ghost sm" data-asis="deshacer" title="Sacar el último punto (Retroceso)">↶ Último punto</button>' : ''}
        <button class="btn ghost sm" data-asis="auto" title="Sin elegir: la regla del taller">Dejar automático</button>
        <button class="btn primary sm" data-asis="sig">${ult ? '✓ Listo' : `Siguiente: ${pasos[i + 1]} →`}</button></div>`;
  }

  /* ---- panel: grupos y cables ---- */
  function render() {
    const gs = grupos(); E.act = Math.min(E.act, gs.length - 1);
    $('#salGrupos').innerHTML = gs.map((g, i) => {
      const n = miembros(g).length, sel = g.aplica === 'seleccion', on = i === E.act;
      const nIntr = sel ? 0 : cables().filter(l => lat(l) === g.aplica && intr(l)).length;
      return `<div class="sal-g ${on ? 'on' : ''}" data-g="${i}">
        <div class="sal-gh">${sel ? `<input class="sal-nom" data-g="${i}" value="${esc(g.nombre || '')}" aria-label="Nombre del grupo" spellcheck="false">` : `<b>${esc(g.nombre)}</b>`}
          <span class="muted small">${n} cable${n === 1 ? '' : 's'}</span></div>
        <div class="small ${pts(g).length ? 'sal-eleg' : 'muted'}">${esc(recTxt(g))}</div>
        ${nIntr ? `<div class="small muted">${nIntr === 1 ? 'El intrínseco (azul) sale' : `Los ${nIntr} intrínsecos (azules) salen`} por su canaleta: para cambiar${nIntr === 1 ? 'lo' : 'los'}, elegi${nIntr === 1 ? 'lo' : 'los'} en un grupo.</div>` : ''}
        ${on ? `<div class="sal-acts">
          <button class="btn sm ${E.modo === 'recorrido' ? 'on' : ''}" data-a="rec" title="Clic en el dibujo por donde pasan los cables; el último clic es por donde salen de la bandeja">✎ Marcar recorrido</button>
          ${sel ? `<button class="btn sm ${E.modo === 'cables' ? 'on' : ''}" data-a="cab" title="Clic en un cable para sumarlo o sacarlo, o un recuadro con los que nacen adentro">☑ Elegir cables</button>` : ''}
          ${pts(g).length ? `<button class="btn ghost sm" data-a="deshacer" title="Sacar el último punto del recorrido (Retroceso)">↶ Último punto</button>
          <button class="btn ghost sm" data-a="auto" title="Borrar el recorrido elegido: vuelve a la regla del taller">↺ Automático</button>` : ''}
          ${sel ? `<button class="btn ghost sm" data-a="del" title="Borrar este grupo">🗑 Borrar</button>` : ''}</div>` : ''}
      </div>`;
    }).join('') + `<button class="btn sm sal-nuevo" data-a="nuevo" title="Un grupo de cables elegidos, con su propio recorrido (manda sobre el de su lateral)">＋ Grupo de cables elegidos</button>`;
    renderList(); hint(); renderAsis(); draw();
  }
  function renderList() {
    const g = grupos()[E.act], sel = g && g.aplica === 'seleccion';
    const q = norm($('#salQ').value.trim()), act = new Set(miembros(g));
    const ls = cables().filter(l => !q || norm(`${l.num} ${l.origen} ${l.destino} ${l.color} ${l.secc}`).includes(q));
    $('#salListAct').hidden = !sel;
    $('#salList').innerHTML = ls.map(l => {
      const gg = grupoDe(l);
      return `<div class="vs-it sal-it ${act.has(l) ? 'act' : ''} ${E.foco === l.num ? 'on' : ''}" data-num="${esc(l.num)}" title="${esc(`${l.origen} → ${l.destino}${l.largo_mm ? ' · ≈' + l.largo_mm + ' mm' : ''}`)}">
        ${sel ? `<input type="checkbox" data-ck ${(g.cables || []).includes(l.num) ? 'checked' : ''} aria-label="Cable ${esc(l.num)} en el grupo">` : '<span></span>'}
        <span class="n">${esc(l.num)}</span><span class="od mono">${esc(l.origen)} → ${esc(l.destino)}</span>
        <span class="sal-chip ${gg ? 'eleg' : ''}" title="${gg ? 'Recorrido del grupo «' + esc(gg.nombre) + '»' : 'Regla del taller'}">${esc(gg ? gg.nombre : 'automático')}</span></div>`;
    }).join('') || '<div class="vs-empty muted small">Ningún cable coincide.</div>';
    const n = cables().length;
    $('#salCnt').textContent = `${n} cable${n === 1 ? '' : 's'} a LI / LD · ${cables().filter(grupoDe).length} con salida elegida`;
  }
  function hint() {
    const g = grupos()[E.act], nom = g ? `«${g.nombre}»` : '';
    $('#salHint').textContent = E.modo === 'recorrido'
      ? `Recorrido de ${nom}: hacé clic por donde pasan los cables, en orden; el último clic es por donde salen de la bandeja (en la punta de una canaleta o a su costado)${E.nuevo && pts(g).length ? ' · el primer clic empieza un recorrido nuevo' : ''} · Retroceso: sacar el último punto · Enter o Esc: listo`
      : E.modo === 'cables'
        ? `Cables de ${nom}: clic en un cable para sumarlo o sacarlo · arrastrá un recuadro para sumar (o sacar) los que nacen adentro · Enter o Esc: listo`
        : 'Elegí un grupo a la izquierda y ✎ Marcar recorrido · Clic en un cable: ver por dónde sale · Rueda: zoom · Arrastrar: mover · 0: toda la bandeja · Esc: cerrar';
    const svg = $('#salSvg'); svg.classList.toggle('pick', E.modo === 'recorrido'); svg.classList.toggle('cab', E.modo === 'cables');
  }

  /* ---- dibujo ---- */
  const ppx = () => { const r = $('#salSvg').getBoundingClientRect(), vb = E.vb; return r.width && r.height ? Math.max(vb[2] / r.width, vb[3] / r.height) : 0.3; };
  function draw() {
    if ($('#salViewer').hidden || !$('#salRutas')) return;
    const gs = grupos(), g = gs[E.act], act = new Set(miembros(g)), u = ppx(), k = 2.2 * u;
    const ls = cables(), foco = ls.find(l => l.num === E.foco);
    const fs = Ins.fontFor('#salSvg', E.vb, 13);
    $('#salRutas').innerHTML = ls.filter(l => !act.has(l) && l !== foco).map(l => Ins.routeG(l, 'otro', k)).join('')
      + ls.filter(l => act.has(l) && l !== foco).map(l => Ins.routeG(l, 'cur', k)).join('')
      + (foco ? Ins.routeG(foco, 'cur', k * 1.3, { lab: fs, pulse: true }) : '');
    // recorridos: el del grupo activo con sus puntos numerados (el ultimo = salida); los de los otros grupos, chicos
    let m = '';
    for (const x of gs) {
      const P = pts(x); if (!P.length) continue;
      const on = x === g, r = (on ? 9 : 5) * u, n = P.length;
      if (n > 1) m += `<polyline points="${P.map(p => `${f2(p[0])},${f2(-p[1])}`).join(' ')}" class="sal-orden ${on ? 'on' : ''}" stroke-width="${f2(1.5 * u)}" stroke-dasharray="${f2(5 * u)} ${f2(4 * u)}"/>`;
      m += P.map((p, i) => `<g class="sal-pt ${i === n - 1 ? 'fin' : ''} ${on ? 'on' : ''}"><title>${esc(x.nombre)}: ${i === n - 1 ? 'salen de la bandeja por acá' : 'pasan por acá (' + (i + 1) + ')'}</title>
        <circle cx="${f2(p[0])}" cy="${f2(-p[1])}" r="${f2(r)}" stroke-width="${f2(1.6 * u)}"/>
        ${on ? `<text x="${f2(p[0])}" y="${f2(-p[1])}" font-size="${f2((i === n - 1 ? 8.5 : 10) * u)}" text-anchor="middle" dominant-baseline="central">${i === n - 1 ? esc(latDe(x) === 'salida' ? '⇥' : latDe(x)) : i + 1}</text>` : ''}</g>`).join('');
    }
    if (E.rect) {
      const [a, b] = E.rect;
      m += `<rect x="${f2(Math.min(a[0], b[0]))}" y="${f2(Math.min(a[1], b[1]))}" width="${f2(Math.abs(b[0] - a[0]))}" height="${f2(Math.abs(b[1] - a[1]))}" class="sal-rect" stroke-width="${f2(1.2 * u)}"/>`;
    }
    $('#salMarcas').innerHTML = m;
  }
  const redibujar = () => { cancelAnimationFrame(E.raf); E.raf = requestAnimationFrame(draw); };

  /* ---- recorrido nuevo: el servidor rutea con las salidas elegidas (como al regenerar) ---- */
  function rutear() {
    clearTimeout(E.t);
    E.t = setTimeout(async () => {
      const seq = ++E.seq, job = Ins.job;
      const ls = [...cables(), ...deOtra()];
      const body = { salidas: { grupos: grupos() }, lineas: ls.map(l => ({ num: l.num, destino: l.destino, lateral: l.lateral, marca_o: l.marca_o || (l.ruta && l.ruta[0]),
        lado: l.lado, color: l.color, secc: l.secc, ...('intrinseco' in l ? { intrinseco: l.intrinseco } : {}),
        // bornera en columna al frente (MOXA): sale en horizontal a la canaleta del costado, como en build
        ...(l.sale_hacia ? { sale_hacia: l.sale_hacia } : {}) })) };
      let r;
      try { r = await api(`/api/trabajo/${job}/instructivo/salidas`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); }
      catch (e) { return toast('No se pudo calcular el recorrido: ' + e.message, 5000); }
      if (seq !== E.seq || job !== Ins.job) return;
      let mal = 0;
      ls.forEach((l, i) => {
        const x = (r.rutas || [])[i]; if (!x) return;
        if (x.ruta) { l.ruta = x.ruta; l.largo_mm = x.largo_mm; } else mal++;
        if (x.salida) l.salida = x.salida; else delete l.salida;
      });
      if (mal) toast(`${mal} cable${mal > 1 ? 's' : ''} no encuentra${mal > 1 ? 'n' : ''} camino por las canaletas hasta ese punto: queda${mal > 1 ? 'n' : ''} como estaba${mal > 1 ? 'n' : ''}`, 5000);
      Ins.dirty(); renderList(); renderAsis(); draw();
    }, 60);
  }
  function cambio(reruta = true) { render(); if (reruta) rutear(); else Ins.dirty(); }

  /* ---- acciones ---- */
  function setModo(m) {
    E.modo = m; E.nuevo = m === 'recorrido'; E.rect = null;
    if (!$('#salViewer').hidden) render();
  }
  function accion(a, i) {
    const gs = grupos(), g = gs[i];
    if (a === 'nuevo') {
      const n = gs.filter(x => x.aplica === 'seleccion').length + 1;
      gs.push({ id: 'g' + Date.now().toString(36), nombre: `Grupo ${n}`, aplica: 'seleccion', cables: E.foco ? [E.foco] : [], puntos: [] });
      E.act = gs.length - 1; E.modo = 'cables'; E.rect = null;
      cambio(false); return toast('Elegí los cables del grupo (clic o recuadro) y después ✎ Marcar recorrido', 4000);
    }
    if (!g) return;
    if (a === 'rec') return setModo(E.modo === 'recorrido' ? null : 'recorrido');
    if (a === 'cab') return setModo(E.modo === 'cables' ? null : 'cables');
    if (a === 'deshacer') { g.puntos = pts(g).slice(0, -1); E.nuevo = false; return cambio(); }
    if (a === 'auto') { g.puntos = []; E.modo = null; return cambio(); }
    if (a === 'del') {
      if (!confirm(`¿Borrar el grupo «${g.nombre}»? Sus cables vuelven a la salida de su lateral.`)) return;
      gs.splice(i, 1); E.act = 0; E.modo = null; return cambio();
    }
  }
  function agregarPunto(p) {
    const g = grupos()[E.act]; if (!g) return;
    g.puntos = E.nuevo ? [p] : [...pts(g), p]; E.nuevo = false;
    cambio();
  }
  function alternar(nums, forzar) {
    const g = grupos()[E.act]; if (!g || g.aplica !== 'seleccion') return;
    const s = new Set(g.cables || []);
    const sumar = forzar ?? !nums.every(n => s.has(n));
    for (const n of nums) sumar ? s.add(n) : s.delete(n);
    g.cables = cables().map(l => l.num).filter(n => s.has(n));
    cambio(pts(g).length > 0);
  }
  // cable mas cercano al punto (pt): primero por el borne de origen, despues por el recorrido
  function cercano(p, u) {
    const tol = 8 * u; let best = null;
    for (const l of cables()) {
      const o = l.marca_o || (l.ruta && l.ruta[0]); if (!o) continue;
      const d = Math.hypot(p[0] - o[0], p[1] - o[1]);
      if (d < tol && (!best || d < best.d)) best = { l, d };
    }
    if (best) return best.l;
    for (const l of cables()) {
      const r = l.ruta || [];
      for (let i = 1; i < r.length; i++) {
        const d = distSeg(p, r[i - 1], r[i]);
        if (d < tol && (!best || d < best.d)) best = { l, d };
      }
    }
    return best ? best.l : null;
  }
  function distSeg(p, a, b) {
    const dx = b[0] - a[0], dy = b[1] - a[1], L = dx * dx + dy * dy;
    const t = L ? Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L)) : 0;
    return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
  }
  function enfocar(l) {
    E.foco = l ? l.num : null;
    if (l && !miembros(grupos()[E.act]).includes(l)) {
      const gs = grupos(), g = grupoDe(l) || gs.find(x => x.aplica === lat(l));
      if (g) E.act = gs.indexOf(g);
    }
    render();
    const it = l && $(`#salList .sal-it[data-num="${CSS.escape(l.num)}"]`); if (it) it.scrollIntoView({ block: 'nearest' });
  }
  function svgPt(e) {
    const r = $('#salSvg').getBoundingClientRect(), vb = E.vb;
    const s = Math.max(vb[2] / r.width, vb[3] / r.height);
    const ox = (r.width * s - vb[2]) / 2, oy = (r.height * s - vb[3]) / 2;
    return [vb[0] - ox + (e.clientX - r.left) * s, vb[1] - oy + (e.clientY - r.top) * s, s];
  }
  const setVb = vb => { E.vb = vb; $('#salSvg').setAttribute('viewBox', vb.map(f2).join(' ')); redibujar(); };

  function init() {
    $('#salAsis').addEventListener('click', e => {
      const b = e.target.closest('[data-asis]'); if (!b || !E.asis) return;
      const g = grupos().find(x => x.aplica === E.asis.pasos[E.asis.i]);
      if (b.dataset.asis === 'sig') return sigAsis();
      if (b.dataset.asis === 'deshacer') return accion('deshacer', grupos().indexOf(g));
      if (b.dataset.asis === 'auto') { if (pts(g).length) { g.puntos = []; rutear(); } return sigAsis(); }
    });
    $('#salClose').addEventListener('click', close);
    $('#salVolver').addEventListener('click', close);
    $('#salFit').addEventListener('click', () => setVb(fit()));
    $('#salGrupos').addEventListener('click', e => {
      const b = e.target.closest('[data-a]'), c = e.target.closest('.sal-g');
      if (b) return accion(b.dataset.a, c ? +c.dataset.g : -1);
      if (c && !e.target.matches('.sal-nom') && +c.dataset.g !== E.act) { E.act = +c.dataset.g; E.modo = null; render(); }
    });
    $('#salGrupos').addEventListener('focusin', e => {
      if (e.target.matches('.sal-nom') && +e.target.dataset.g !== E.act) { E.act = +e.target.dataset.g; E.modo = null; renderList(); hint(); draw();
        $('#salGrupos').querySelectorAll('.sal-g').forEach(x => x.classList.toggle('on', +x.dataset.g === E.act)); }
    });
    $('#salGrupos').addEventListener('change', e => {
      if (!e.target.matches('.sal-nom')) return;
      const g = grupos()[+e.target.dataset.g]; if (!g) return;
      g.nombre = e.target.value.trim() || g.nombre; cambio(false);
    });
    $('#salGrupos').addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.matches('.sal-nom')) { e.preventDefault(); e.target.blur(); } });
    $('#salList').addEventListener('click', e => {
      const it = e.target.closest('.sal-it'); if (!it) return;
      const l = cables().find(x => x.num === it.dataset.num); if (!l) return;
      if (e.target.matches('[data-ck]')) return alternar([l.num], e.target.checked);
      if (E.modo === 'cables') return alternar([l.num]);
      enfocar(E.foco === l.num ? null : l);
    });
    let qT; $('#salQ').addEventListener('input', () => { clearTimeout(qT); qT = setTimeout(renderList, 80); });
    $('#salQ').addEventListener('keydown', e => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); if (e.target.value) { e.target.value = ''; renderList(); } else e.target.blur(); } });
    const lista = () => [...$('#salList').querySelectorAll('.sal-it')].map(x => x.dataset.num);
    $('#salTodos').addEventListener('click', () => alternar(lista(), true));
    $('#salNinguno').addEventListener('click', () => alternar(lista(), false));
    const svg = $('#salSvg');
    svg.addEventListener('wheel', e => {
      e.preventDefault(); if (!E.vb) return;
      const [px, py] = svgPt(e), f = Math.pow(1.0015, e.deltaY), vb = E.vb;
      setVb([px - (px - vb[0]) * f, py - (py - vb[1]) * f, vb[2] * f, vb[3] * f]);
    }, { passive: false });
    svg.addEventListener('pointerdown', e => {
      if (e.button !== 0) return;
      const p = svgPt(e);
      E.drag = { x: e.clientX, y: e.clientY, vb: E.vb.slice(), s: p[2], p0: [p[0], p[1]], rect: E.modo === 'cables' };
      svg.setPointerCapture(e.pointerId); if (!E.drag.rect) svg.classList.add('drag');
    });
    svg.addEventListener('pointermove', e => {
      const d = E.drag; if (!d) return;
      if (d.rect) { if (Math.hypot(e.clientX - d.x, e.clientY - d.y) >= 5) { const p = svgPt(e); E.rect = [d.p0, [p[0], p[1]]]; redibujar(); } return; }
      setVb([d.vb[0] - (e.clientX - d.x) * d.s, d.vb[1] - (e.clientY - d.y) * d.s, d.vb[2], d.vb[3]]);
    });
    svg.addEventListener('pointerup', e => {
      const d = E.drag; E.drag = null; svg.classList.remove('drag');
      if (!d) return;
      if (E.rect) {          // recuadro: los cables que nacen adentro
        const [a, b] = E.rect; E.rect = null;
        const x0 = Math.min(a[0], b[0]), x1 = Math.max(a[0], b[0]), y0 = -Math.max(a[1], b[1]), y1 = -Math.min(a[1], b[1]);
        const nums = cables().filter(l => { const o = l.marca_o || (l.ruta && l.ruta[0]); return o && o[0] >= x0 && o[0] <= x1 && o[1] >= y0 && o[1] <= y1; }).map(l => l.num);
        if (nums.length) alternar(nums); else { draw(); toast('Ningún cable nace adentro del recuadro'); }
        return;
      }
      if (Math.hypot(e.clientX - d.x, e.clientY - d.y) >= 5) return;      // fue un arrastre
      const [x, y, s] = svgPt(e), p = [Math.round(x * 100) / 100, Math.round(-y * 100) / 100];
      if (E.modo === 'recorrido') return agregarPunto(p);
      const l = cercano(p, s);
      if (E.modo === 'cables') { if (l) alternar([l.num]); return; }
      enfocar(l);
    });
    window.addEventListener('resize', () => { if (!$('#salViewer').hidden) redibujar(); });
    document.addEventListener('keydown', e => {
      if ($('#salViewer').hidden) return;
      if (e.target.isContentEditable || (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox')) return;
      if (e.key === 'Escape') { e.preventDefault(); return E.modo && !E.asis ? setModo(null) : close(); }
      if (e.key === 'Enter' && E.asis) { e.preventDefault(); return sigAsis(); }
      if (e.key === 'Enter' && E.modo) { e.preventDefault(); return setModo(null); }
      if (e.key === 'Backspace' && E.modo === 'recorrido') { e.preventDefault(); return accion('deshacer', E.act); }
      if (e.key === '0') { e.preventDefault(); setVb(fit()); }
    });
  }
  return { open, init, close, grupoDe, asistente };
})();
Sal.init();
