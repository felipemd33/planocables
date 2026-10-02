'use strict';
/* Auditoría cruzada de la bandeja: otro operario verifica por SECCIONES (conjuntos de aparatos) que en cada
   borne marcado esté el cable con ese número, sin seguir cada cable de punta a punta. Como cada cable tiene
   sus dos puntas en alguna sección, al verificar todas las secciones queda verificado todo el cableado. */
const Aud = (() => {
  const A = { secs: [], k: 0, vb: null, anim: null, drag: null };
  const D = () => Ins.D;
  const st = () => { const d = D(); d.auditoria = d.auditoria || {}; d.auditoria.secciones = d.auditoria.secciones || {}; d.auditoria.obs = d.auditoria.obs || {};
    d.auditoria.checks = d.auditoria.checks || {}; return d.auditoria; };
  // claves de lo que se chequea en un paso: cada borne con su cable, cada cable del mazo a LI/LD o cada accesorio
  const keysDe = s => s.acc ? s.acc.map(x => 'ACC|' + x.id) : s.li ? s.li.flatMap(o => o.lineas.map(l => `${s.key}|${l.num}`)) : s.ends.map(e => e.key);
  const f2 = v => (+v).toFixed(2);

  /* ---- puntas de cable en la bandeja ---- */
  function puntas() {
    const out = new Map();
    const dirDe = (ruta, fin) => {
      if (!ruta || ruta.length < 2) return null;
      const a = fin ? ruta[ruta.length - 1] : ruta[0], b = fin ? ruta[ruta.length - 2] : ruta[1];
      return [b[0] - a[0], b[1] - a[1]];
    };
    for (const { l } of Ins.flat()) {
      const add = (txt, m, fin, exacto) => {
        if (!m || !txt || Ins.LAT(txt)) return;
        const key = `${txt}|${l.num}`;
        if (out.has(key)) return;             // mismo cable en el mismo borne (puente de 3 puntas): una sola marca
        out.set(key, { key, num: l.num, texto: txt, x: m[0], y: m[1], r: m[2] || 1.6, color: l.color, secc: l.secc, cable: l.cable,
          term: Ins.terminal(l, fin ? 'd' : 'o'),
          exacto: exacto !== false, dir: dirDe(l.ruta, fin), ruta: fin ? (l.ruta || []).slice().reverse() : (l.ruta || []), hecho: !!l.hecho });
      };
      add(l.origen, l.marca_o || (l.ruta && l.ruta[0]), false, l.exacto_o);
      if (!Ins.LAT(l.destino)) add(l.destino, l.marca_d || (l.ruta && l.ruta[l.ruta.length - 1]), true, l.exacto_d);
    }
    return [...out.values()];
  }
  /* ---- secciones: por riel y lado, cortando en grupos de aparatos contiguos ---- */
  function secciones() {
    const d = D(); const comp = d.topo.comp || {};
    let filas = d.topo.filas;
    if (!filas || !filas.length) {        // instructivos viejos: eje del riel = promedio de las etiquetas de ese riel
      const by = {}; for (const c of Object.values(comp)) if (c.fila) (by[c.fila] = by[c.fila] || []).push(c.y);
      filas = Object.keys(by).sort((a, b) => a - b).map(f => by[f].reduce((a, b) => a + b, 0) / by[f].length);
    }
    const tagDe = t => { const b = t.split(' ')[0]; return comp[b] ? b : comp[b.replace(/\d+$/, '')] ? b.replace(/\d+$/, '') : b; };
    const ductos = d.topo.ductos || [];
    const zonaDe = (x, fila) => { const eje = filas[fila - 1];
      return ductos.filter(q => !q.h && q.b[1] <= eje && eje <= q.b[3] && (q.b[0] + q.b[2]) / 2 < x).length; };
    const E = puntas();
    for (const e of E) {
      e.tag = tagDe(e.texto); const c = comp[e.tag];
      e.fila = c && c.fila ? c.fila : null;
      const eje = e.fila ? filas[e.fila - 1] : null;
      if (eje == null || Math.abs(e.y - eje) > 90) { e.fila = null; e.lado = 'otros'; e.zona = 0; }
      else { e.lado = e.y >= eje ? 'arriba' : 'abajo'; e.zona = zonaDe(c.x, e.fila); e.dist = Math.abs(e.y - eje); }
    }
    const zonasFila = {};
    for (const e of E) if (e.fila) (zonasFila[e.fila] = zonasFila[e.fila] || new Set()).add(e.zona);
    const grupos = new Map();
    for (const e of E) { const k = e.fila ? `${e.fila}|${e.zona}|${e.lado}` : 'otros'; if (!grupos.has(k)) grupos.set(k, []); grupos.get(k).push(e); }
    const orden = [...grupos.keys()].sort((a, b) => {
      if (a === 'otros') return 1; if (b === 'otros') return -1;
      const [fa, za, la] = a.split('|'), [fb, zb, lb] = b.split('|');
      return (+fa - +fb) || (+za - +zb) || (la === 'arriba' ? -1 : 1) - (lb === 'arriba' ? -1 : 1);
    });
    const S = [];
    for (const k of orden) {
      const comps = [];
      for (const e of grupos.get(k)) {
        let c = comps.find(c => c.tag === e.tag);
        if (!c) comps.push(c = { tag: e.tag, ends: [], x0: e.x, x1: e.x });
        c.ends.push(e); c.x0 = Math.min(c.x0, e.x); c.x1 = Math.max(c.x1, e.x);
      }
      comps.sort((a, b) => a.x0 - b.x0);
      let cur = null;
      for (const c of comps) {
        if (!cur || cur.ends.length + c.ends.length > 16 || c.x1 - cur.x0 > 150 || c.x0 - cur.x1 > 60) {
          const [fila, zona, lado] = k === 'otros' ? [null, 0, 'otros'] : [+k.split('|')[0], +k.split('|')[1], k.split('|')[2]];
          cur = { fila, zona, lado, comps: [], ends: [], x0: c.x0, x1: c.x1 }; S.push(cur);
        }
        cur.comps.push(c.tag); cur.ends.push(...c.ends); cur.x1 = Math.max(cur.x1, c.x1);
      }
    }
    // CAPAS: en cada columna de bornes (misma vertical, mismo lado) el cable de afuera queda DEBAJO de los de adentro.
    // La auditoria muestra primero la capa de abajo y al avanzar la siguiente (como se cablea)
    const pasos = [];
    for (const s of S) {
      s.ends.sort((a, b) => a.x - b.x || b.y - a.y);
      const zt = s.fila && zonasFila[s.fila] && zonasFila[s.fila].size > 1 ? ` · zona ${[...zonasFila[s.fila]].sort((a, b) => a - b).indexOf(s.zona) + 1}` : '';
      s.key = `${s.fila || 'x'}-${s.zona || 0}-${s.lado}-${s.comps[0]}`;
      s.nombre = s.fila ? `Riel ${s.fila}${zt} · parte de ${s.lado} · ${s.comps.join(', ')}` : `Fuera de los rieles · ${s.comps.join(', ')}`;
      // capa = fila fisica del aparato contada desde afuera (rele: 11 -> 14 -> 12; QUATTRO: 1 -> 2; doble piso: impar -> par)
      const porTag = new Map();
      for (const e of s.ends) { if (!porTag.has(e.tag)) porTag.set(e.tag, []); porTag.get(e.tag).push(e); }
      for (const es of porTag.values()) {
        const filasT = [];
        for (const dd of es.map(e => e.dist || 0).sort((a, b) => b - a)) if (!filasT.length || filasT[filasT.length - 1] - dd > 1.5) filasT.push(dd);
        for (const e of es) e.capa = filasT.findIndex(dd => Math.abs(dd - (e.dist || 0)) <= 1.5);
      }
      const n = Math.max(1, ...s.ends.map(e => (e.capa || 0) + 1));
      for (let c = 0; c < n; c++) {
        const ends = s.ends.filter(e => (e.capa || 0) === c);
        if (!ends.length) continue;
        pasos.push({ ...s, ends, todos: s.ends, capa: c, ncapas: n, base: s.nombre, key: n > 1 ? `${s.key}#${c + 1}` : s.key,
          nombre: n > 1 ? `${s.nombre} · capa ${c + 1} de ${n}${c === 0 ? ' (la de abajo)' : c === n - 1 ? ' (la de arriba)' : ''}` : s.nombre });
      }
    }
    // salida a LI: el mazo que sale por el lateral izquierdo (se verifica que esten todos los numeros)
    for (const [cod, lat] of [['LI', 'lateral izquierdo'], ['LD', 'lateral derecho']]) {
    const li = Ins.flat().map(x => x.l).filter(l => l.destino === cod && l.ruta && l.ruta.length);
    if (li.length) {
      const ys = [...new Set(li.map(l => Math.round(l.ruta[l.ruta.length - 1][1])))].sort((a, b) => b - a);
      const salidas = ys.map((y, i) => ({ y, nombre: ys.length > 1 ? (i === 0 ? 'salida de arriba' : i === ys.length - 1 ? 'salida de abajo' : `salida ${i + 1}`) : 'salida',
        lineas: li.filter(l => Math.round(l.ruta[l.ruta.length - 1][1]) === y) }));
      pasos.push({ key: cod, lado: cod, li: salidas, nombre: `Salida a ${cod} (${lat}) · ${li.length} cables`, base: `Salida a ${cod}`, ends: [], comps: [cod], capa: 0, ncapas: 1 });
    }
    }
    if ((d.accesorios || []).length)
      pasos.push({ key: 'ACC', lado: 'ACC', acc: d.accesorios, nombre: `Puentes y accesorios · ${d.accesorios.length}`, base: 'Puentes y accesorios', ends: [], comps: ['ACC'], capa: 0, ncapas: 1 });
    return pasos;
  }

  /* ---- dibujo de una sección ---- */
  function stub(ruta, largo = 22) {        // primer tramo del cable desde el borne (hacia la canaleta)
    if (!ruta || ruta.length < 2) return [];
    const out = [ruta[0]]; let rest = largo;
    for (let i = 1; i < ruta.length && rest > 0; i++) {
      const a = ruta[i - 1], b = ruta[i], L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (L <= rest) { out.push(b); rest -= L; } else { const t = rest / L; out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]); rest = 0; }
    }
    return out;
  }
  function boxOf(s) {
    let pts;
    if (s.acc) { const r = D().topo.region; return [r[0], r[1], r[2], r[3]]; }
    if (s.li) pts = s.li.flatMap(o => o.lineas.map(l => l.ruta[l.ruta.length - 1]));
    else pts = (s.todos || s.ends).flatMap(e => [[e.x, e.y], ...stub(e.ruta, 14)]);
    const r = D().topo.region;
    if (!pts.length) return [r[0], r[1], r[2], r[3]];
    let x0 = Math.min(...pts.map(p => p[0])) - 16, x1 = Math.max(...pts.map(p => p[0])) + 16;
    let y0 = Math.min(...pts.map(p => p[1])) - 16, y1 = Math.max(...pts.map(p => p[1])) + 16;
    if (s.li) { x0 -= 30; x1 += 70; y0 -= 20; y1 += 20; }
    if (x1 - x0 < 90) { const c = (x0 + x1) / 2; x0 = c - 45; x1 = c + 45; }
    if (y1 - y0 < 60) { const c = (y0 + y1) / 2; y0 = c - 30; y1 = c + 30; }
    return [x0, y0, x1, y1];
  }
  // letra de los rotulos: la pedida, pero sin pasar el paso entre bornes vecinos (los rotulos van uno al lado del otro)
  function fsSec(s, want) {
    let paso = 99; const E = s.todos || s.ends;
    for (let i = 0; i < E.length; i++) for (let j = i + 1; j < E.length; j++) {
      const d = Math.hypot(E[i].x - E[j].x, E[i].y - E[j].y); if (d > 0.3) paso = Math.min(paso, d);
    }
    return Math.max(1.1, Math.min(want, paso * 0.9));
  }
  function secSvg(s, fs, obs, chk = {}) {
    let g = '';
    if (s.acc) return g;
    if (s.li) {
      for (const o of s.li) {
        for (const l of o.lineas) {
          const pts = stub(l.ruta.slice().reverse(), 40).map(p => [p[0], -p[1]]);
          const k = `${s.key}|${l.num}`;
          if (pts.length > 1) g += `<g class="au-end${chk[k] ? ' chk' : ''}" data-key="${esc(k)}"><title>${esc(l.num)} · ${esc(Ins.secTxt(l))} · ${esc(l.color)}</title>`
            + `<path d="M${pts.map(p => f2(p[0]) + ' ' + f2(p[1])).join('L')}" stroke="${Ins.LC(l.color)}" stroke-width="0.9" fill="none" opacity=".8"/></g>`;
        }
        const p = o.lineas[0].ruta[o.lineas[0].ruta.length - 1];
        const der = s.key === 'LD';
        g += `<text x="${f2(p[0] + (der ? 4 : -4))}" y="${f2(-p[1])}" text-anchor="${der ? 'start' : 'end'}" dominant-baseline="central" font-size="${f2(fs * 1.3)}" class="lbl li-lbl" stroke-width="${f2(fs * 0.35)}">${s.key} · ${esc(o.nombre)} · ${o.lineas.length}</text>`;
      }
      return g;
    }
    // direccion del cable en cada borne (hacia la canaleta)
    for (const e of s.ends) {
      e._p = [e.x, -e.y];
      e._sp = stub(e.ruta).map(q => [q[0], -q[1]]);
      const q = e._sp.length > 1 ? e._sp[1] : [e.x, -e.y + (e.lado === 'abajo' ? 5 : -5)];
      const dx = q[0] - e._p[0], dy = q[1] - e._p[1];
      e._vert = Math.abs(dy) >= Math.abs(dx); e._sgn = (e._vert ? Math.sign(dy) : Math.sign(dx)) || -1;
      e._dir = e._vert ? [0, e._sgn] : [e._sgn, 0]; e._per = e._vert ? [1, 0] : [0, 1];
      e._lf = Ins.termLen(e.r);
    }
    // varios numeros en el mismo borne (puente entre numeros distintos): se corren de costado
    const pos = new Map();
    for (const e of s.ends) { const k = `${Math.round(e.x * 3)},${Math.round(e.y * 3)}`; const n = pos.get(k) || 0; pos.set(k, n + 1); e._off = n; }
    // bornes en la misma linea con el cable hacia el mismo lado (contactos 11 y 14 de un rele, puntos 1 y 2 de un
    // QUATTRO, piso de abajo y de arriba de una bornera doble): el cable de adentro pasa por el borne de afuera.
    // Cada cable va por su CARRIL (corrido de costado) y su rotulo mas lejos que el del de afuera (como las mangas)
    const cols = new Map();
    for (const e of s.ends) {
      const k = e._vert ? `v${Math.round(e.x / 1.2)}|${e._sgn}` : `h${Math.round(e.y / 1.2)}|${e._sgn}`;
      if (!cols.has(k)) cols.set(k, []); cols.get(k).push(e);
    }
    const ejes = [...new Set(s.ends.map(e => Math.round((e._vert ? e.x : e.y) * 2) / 2))].sort((a, b) => a - b);
    let paso = 99; for (let i = 1; i < ejes.length; i++) if (ejes[i] - ejes[i - 1] > 1) paso = Math.min(paso, ejes[i] - ejes[i - 1]);
    // carril: el cable de afuera sigue recto; los de adentro se corren para pasar al costado del terminal de afuera
    const carrilAncho = r0 => Math.max(0.8, Math.min(r0 * 0.5 + 0.9, paso * 0.42));
    const largo = e => Ins.labelLen(e.num, Ins.secCorto(e), fs);
    const afuera = e => e._vert ? e._p[1] * e._sgn : e._p[0] * e._sgn;      // mayor = mas cerca de la canaleta
    for (const c of cols.values()) {
      c.sort((a, b) => afuera(b) - afuera(a) || a._off - b._off);
      let cum = 0; const o0 = afuera(c[0]);
      c.forEach((e, i) => {
        const L = carrilAncho(c[0].r);
        e._lane = i === 0 ? 0 : (i % 2 ? 1 : -1) * Math.ceil(i / 2) * L;
        e._r = Math.max(i ? (o0 - afuera(e)) + c[0]._lf + 0.6 + cum : e._lf + 0.4, e._lf + 0.4);
        cum += largo(e) + fs * 0.5;
      });
    }
    // el tramo de cable dibujado llega mas alla de su manga (la manga siempre queda sobre el cable)
    for (const e of s.ends) {
      const hace = e._r + fs * 0.25 + largo(e) + Math.abs(e._lane) + 3;
      if (hace > 22) e._sp = stub(e.ruta, hace).map(q => [q[0], -q[1]]);
    }
    // recorrido del cable por su carril: sale recto del borne (con el terminal) y despues se corre al carril
    const carril = e => {
      const sp = e._sp, p0 = e._p, dr = e._dir, pr = e._per, o = e._lane, lf = e._lf;
      const pts = [p0, [p0[0] + dr[0] * lf, p0[1] + dr[1] * lf]];
      if (!o) return sp.length > 1 ? [p0, ...sp.slice(1)] : pts;
      const j = lf + Math.abs(o) * 0.8;      // se corre en diagonal apenas termina el terminal
      pts.push([p0[0] + dr[0] * j + pr[0] * o, p0[1] + dr[1] * j + pr[1] * o]);
      for (let i = 1; i < sp.length; i++) {
        const q = [sp[i][0] + pr[0] * o, sp[i][1] + pr[1] * o];
        if (i > 1 || (q[0] - p0[0]) * dr[0] + (q[1] - p0[1]) * dr[1] > j) pts.push(q);
      }
      return pts;
    };
    let cables = '', marcas = '', rotulos = '';
    for (const e of s.ends) {
      const col = Ins.LC(e.color), white = ['blanco', 'amarillo'].includes(norm(e.color));
      const bad = obs[e.key] ? ' bad' : '', ck = chk[e.key] ? ' chk' : '';
      const pts = carril(e);
      if (pts.length > 1) {
        const dd = 'M' + pts.map(q => f2(q[0]) + ' ' + f2(q[1])).join('L');
        cables += `<g class="au-end au-cab${bad}${ck}" data-key="${esc(e.key)}">`;
        cables += `<path d="${dd}" stroke="${white ? '#333' : '#fff'}" stroke-width="1.7" fill="none" class="casing"/>`;
        cables += `<path d="${dd}" stroke="${col}" stroke-width="0.9" fill="none"/></g>`;
      }
      const p = e._p, off = e._lane + e._off * fs * 1.05;
      const a2 = e._vert ? [p[0] + off, p[1]] : [p[0], p[1] + off];
      const b2 = e._vert ? [a2[0], a2[1] + e._sgn] : [a2[0] + e._sgn, a2[1]];
      marcas += `<g class="au-end${bad}${ck}" data-key="${esc(e.key)}"><title>${esc(e.num)} · ${esc(Ins.secTxt(e))} · ${esc(e.color)} — ${esc(e.texto)}${e.term ? ' · ' + esc(e.term.txt) : ''}</title>`
        + Ins.ferrule(p, e._dir, e.r, e.term, 0.6) + Ins.mark(p, e.r, bad ? 'bad' : 'aud', 0.6) + '</g>';
      rotulos += `<g class="au-end${bad}${ck}" data-key="${esc(e.key)}">${Ins.label(a2, b2, e._r, e.num, Ins.secCorto(e), fs, 'au')}</g>`;
    }
    g += cables + marcas + rotulos;
    return g;
  }

  /* ---- visor ---- */
  // donde: {num, texto} = abrir en el paso que tiene ese borne (al venir del visor de cablear)
  async function open(donde) {
    try { await Ins.load(); } catch (e) { return toast('No se pudo cargar el instructivo: ' + e.message, 5000); }
    if (!D()) return toast('Primero hay que armar el instructivo (cargá el topográfico)', 5000);
    A.secs = secciones();
    if (!A.secs.length) return toast('No hay cables en la bandeja para auditar');
    const s = st();
    if (!s.inicio) { s.inicio = new Date().toLocaleString(); Ins.dirty(); }
    A.k = Math.max(0, A.secs.findIndex(x => !(s.secciones[x.key] || {}).ok));
    if (donde && donde.num) {
      const tiene = (x, exacto) => x.ends.some(e => e.num === donde.num && (!exacto || e.texto === donde.texto))
        || (!exacto && !!x.li && x.li.some(o => o.lineas.some(l => l.num === donde.num)));
      let i = A.secs.findIndex(x => tiene(x, true)); if (i < 0) i = A.secs.findIndex(x => tiene(x, false));
      if (i >= 0) A.k = i;
    }
    $('#audViewer').hidden = false; document.body.style.overflow = 'hidden';
    if (document.activeElement) document.activeElement.blur();
    $('#auQuien').value = s.auditor || '';
    const falta = Ins.flat().filter(x => !x.l.hecho).length;
    if (falta) toast(`Ojo: ${falta} cable${falta === 1 ? '' : 's'} todavía sin marcar como cableado en el instructivo`, 5000);
    draw(true);
  }
  function close() { $('#audViewer').hidden = true; document.body.style.overflow = ''; if (!$('#insWrap').hidden) Ins.render(); }
  // boton 🧰 Instructivo: vuelve al visor de cablear, en el primer cable sin chequear de este paso
  function aCablear() {
    const s = A.secs[A.k], a = st(), F = Ins.flat();
    let k = -1;
    if (s && s.li) {
      const ls = s.li.flatMap(o => o.lineas), l = ls.find(l => !a.checks[`${s.key}|${l.num}`]) || ls[0];
      k = F.findIndex(x => x.l === l);
    } else if (s && s.ends.length) {
      const e = s.ends.find(e => !a.checks[e.key]) || s.ends[0];
      k = F.findIndex(x => x.l.num === e.num && (x.l.origen === e.texto || x.l.destino === e.texto));
      if (k < 0) k = F.findIndex(x => x.l.num === e.num);
    }
    $('#audViewer').hidden = true;
    Ins.openViewer(k < 0 ? null : k);
  }
  // clic en un cable (dibujo o lista): queda translucido = chequeado. Con todos chequeados, el paso queda verificado
  function toggleCheck(key) {
    const a = st(), s = A.secs[A.k];
    if (a.checks[key]) delete a.checks[key]; else a.checks[key] = true;
    const ks = keysDe(s), todos = ks.length > 0 && ks.every(k => a.checks[k]);
    const ok = !!(a.secciones[s.key] || {}).ok;
    if (todos && !ok) { setOk(true, false); toast('✓ Todos los cables de este paso chequeados: paso verificado (→ para seguir)', 3500); return; }
    if (!todos && ok) a.secciones[s.key] = { ok: false };
    Ins.dirty(); draw();
  }
  function draw(first) {
    const s = A.secs[A.k], a = st(), obs = a.obs;
    const ok = A.secs.filter(x => (a.secciones[x.key] || {}).ok).length;
    const nobs = Object.values(obs).filter(Boolean).length;
    $('#auTit').textContent = `Auditoría cruzada · ${Ins.est()} · ${s.nombre}`;
    $('#auSub').textContent = `${ok} de ${A.secs.length} pasos verificados${s.ncapas > 1 ? ` · capa ${s.capa + 1} de ${s.ncapas}: ${s.capa === 0 ? 'primero los cables que quedan abajo' : 'los que van encima de la capa anterior'}` : ''}${nobs ? ` · ⚠ ${nobs} observación${nobs === 1 ? '' : 'es'}` : ''}${a.inicio ? ' · inicio ' + a.inicio : ''}`;
    $('#auPos').textContent = `${A.k + 1} / ${A.secs.length}`;
    $('#auOk').checked = !!(a.secciones[s.key] || {}).ok;
    $('#auBar').style.width = (ok / A.secs.length * 100) + '%';
    $('#auCnt').innerHTML = `<b>${ok}/${A.secs.length}</b> pasos · ${A.secs.reduce((n, x) => n + x.ends.length, 0)} bornes`;
    $('#auList').innerHTML = A.secs.map((x, i) => {
      const e = a.secciones[x.key] || {}, bad = x.ends.some(q => obs[q.key]);
      const txt = x.ncapas > 1 ? (x.capa === 0 ? `${x.base} · capa 1 de ${x.ncapas} (abajo)` : `↳ capa ${x.capa + 1} de ${x.ncapas}${x.capa === x.ncapas - 1 ? ' (arriba)' : ''}`) : x.nombre;
      return `<div class="vs-it au-it${e.ok ? ' seen' : ''}${i === A.k ? ' on' : ''}${bad ? ' rev' : ''}${x.capa ? ' au-capa' : ''}" data-i="${i}" role="option">
        <span class="ck">${bad ? '⚠' : '✓'}</span><span class="t">${esc(txt)}</span><span class="sec">${x.li ? x.li.reduce((n, o) => n + o.lineas.length, 0) : x.ends.length}</span></div>`;
    }).join('');
    const on = $('#auList .on'); if (on) on.scrollIntoView({ block: 'nearest' });
    const box = boxOf(s), vb = [box[0], -box[3], box[2] - box[0], box[3] - box[1]];
    const fs = fsSec(s, Ins.fontFor('#auSvg', vb, 14));
    $('#auSvg').innerHTML = Ins.imgTag(true) + secSvg(s, fs, obs, a.checks);
    const ks = keysDe(s), nchk = ks.filter(k => a.checks[k]).length;
    const cuenta = ks.length ? `<div class="au-chk small"><b>${nchk} / ${ks.length}</b> chequeados${nchk === ks.length ? ' ✓' : ''} · tocá cada cable (en el dibujo o en la lista) al verlo: queda translúcido</div>` : '';
    camera(vb, first ? 0 : 380);
    // lista de bornes de la seccion (sin origen/destino: solo que esten)
    if (s.acc) {
      $('#auEnds').innerHTML = `<div class="au-h"><b>Puentes y accesorios</b><div class="muted small">Verificá que estén colocados (no son cables con número).</div>${cuenta}</div>` +
        s.acc.map((x, i) => `<div class="au-row${obs['ACC|' + x.id] ? ' bad' : ''}${a.checks['ACC|' + x.id] ? ' chk' : ''}" data-key="ACC|${esc(x.id)}"><span class="t" style="grid-column:1/4;color:var(--text)">${esc(x.texto)}${x.hecho ? ' <span class="pill ok">colocado</span>' : ''}</span>
          <button class="mini" data-obs title="Anotar un problema">⚠</button>${obs['ACC|' + x.id] ? `<div class="obs">⚠ ${esc(obs['ACC|' + x.id])}</div>` : ''}</div>`).join('');
    } else if (s.li) {
      $('#auEnds').innerHTML = `<div class="au-h"><b>Salida a ${s.key}</b><div class="muted small">Verificá que en el mazo que sale por el ${s.key === 'LD' ? 'lateral derecho' : 'lateral izquierdo'} estén todos estos números.</div>${cuenta}</div>` +
        s.li.map(o => `<div class="au-sub">${esc(o.nombre)} (${o.lineas.length})</div>` + o.lineas.slice().sort((p, q) => natKey(p.num).localeCompare(natKey(q.num))).map(l => row({ key: `${s.key}|${l.num}`, num: l.num, color: l.color, secc: l.secc, cable: l.cable, texto: `${l.origen} → ${s.key}` }, obs, a.checks)).join('')).join('');
    } else {
      $('#auEnds').innerHTML = `<div class="au-h"><b>${s.ends.length} bornes con cable${s.ncapas > 1 ? ` · capa ${s.capa + 1} de ${s.ncapas}` : ''}</b><div class="muted small">${s.ncapas > 1 ? (s.capa === 0 ? 'Primero la capa de abajo: los cables de afuera de cada columna (quedan debajo de los otros). ' : 'Ahora los que van encima de la capa anterior. ') : ''}Mirá que en cada borne marcado esté el cable con ese número y esa sección. Si algo no coincide, tocá ⚠ y anotalo.</div>${cuenta}</div>` +
        s.ends.map(e => row(e, obs, a.checks)).join('');
    }
  }
  function row(e, obs, chk = {}) {
    const o = obs[e.key];
    return `<div class="au-row${o ? ' bad' : ''}${chk[e.key] ? ' chk' : ''}" data-key="${esc(e.key)}" title="Clic: chequeado / sin chequear">
      <span class="n mono">${esc(e.num)}</span>${e.color ? swatch(e.color) : '<span class="muted small">malla</span>'}<span class="sec">${esc(Ins.secTxt(e))}</span>
      <button class="mini" data-obs title="Anotar un problema en este borne">⚠</button>
      <span class="t mono">${esc(e.texto)}${e.exacto === false ? ' <span class="pill warn" title="Punto aproximado en el dibujo">aprox.</span>' : ''}</span>
      ${e.term ? Ins.termChip(e.term) : ''}
      ${o ? `<div class="obs">⚠ ${esc(o)}</div>` : ''}</div>`;
  }
  function camera(target, ms) {
    cancelAnimationFrame(A.anim);
    const from = A.vb || target; const t0 = performance.now();
    const ease = t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const step = now => {
      const t = ms ? Math.min(1, (now - t0) / ms) : 1, e = ease(t);
      A.vb = from.map((v, i) => v + (target[i] - v) * e);
      $('#auSvg').setAttribute('viewBox', A.vb.map(v => v.toFixed(2)).join(' '));
      if (t < 1) A.anim = requestAnimationFrame(step);
    };
    A.anim = requestAnimationFrame(step);
  }
  function go(d) { A.k = Math.max(0, Math.min(A.secs.length - 1, A.k + d)); draw(); }
  function setOk(v, adv) {
    const a = st(), s = A.secs[A.k];
    a.secciones[s.key] = v ? { ok: true, fecha: new Date().toLocaleString(), quien: a.auditor || '' } : { ok: false };
    for (const k of keysDe(s)) { if (v) a.checks[k] = true; else delete a.checks[k]; }
    Ins.dirty();
    if (A.secs.every(x => (a.secciones[x.key] || {}).ok)) {
      a.fin = new Date().toLocaleString();
      const nobs = Object.values(a.obs).filter(Boolean).length;
      toast(nobs ? `Todos los pasos revisados, con ${nobs} observación${nobs === 1 ? '' : 'es'} para corregir` : '✓ Auditoría completa: todo el cableado de la bandeja verificado', 6000);
    }
    if (adv && v && A.k < A.secs.length - 1) go(1); else draw();
  }
  function anotar(key) {
    const a = st(); const prev = a.obs[key] || '';
    const t = prompt('¿Qué pasa en este borne? (ej.: falta el cable, número equivocado, borne equivocado). Dejalo vacío para quitar la observación.', prev);
    if (t === null) return;
    if (t.trim()) a.obs[key] = t.trim(); else delete a.obs[key];
    const s = A.secs[A.k]; if (t.trim() && a.secciones[s.key]) a.secciones[s.key].ok = false;
    Ins.dirty(); draw();
  }
  function svgPoint(e) {
    const svg = $('#auSvg'); const r = svg.getBoundingClientRect(); const vb = A.vb;
    const s = Math.max(vb[2] / r.width, vb[3] / r.height);
    const ox = (r.width * s - vb[2]) / 2, oy = (r.height * s - vb[3]) / 2;
    return [vb[0] - ox + (e.clientX - r.left) * s, vb[1] - oy + (e.clientY - r.top) * s, s];
  }
  function imprimir() {
    const w = window.open('', '_blank'); if (!w) return toast('El navegador bloqueó la ventana de impresión');
    const base = location.origin, a = st();
    const hoja = s => {
      const b = boxOf(s), vb = [b[0], -b[3], b[2] - b[0], b[3] - b[1]], fs = fsSec(s, vb[2] / 55);
      const svg = `<svg viewBox="${vb.map(f2).join(' ')}" preserveAspectRatio="xMidYMid meet">${Ins.imgTag(true)}${secSvg(s, fs, a.obs)}</svg>`.replace(/href="\//g, `href="${base}/`);
      if (s.acc) return `<section><h2>Puentes y accesorios</h2><table><thead><tr><th>Qué</th><th>Dónde</th><th>OK</th></tr></thead><tbody>${s.acc.map(x => `<tr><td>${esc(x.texto)}</td><td>${esc(x.zona || '')}</td><td>${a.checks['ACC|' + x.id] ? '☑' : '☐'}</td></tr>`).join('')}</tbody></table></section>`;
      const bx = k => a.checks[k] ? '☑' : '☐';
      const filas = s.li ? s.li.flatMap(o => o.lineas.map(l => `<tr><td>${esc(l.num)}</td><td>${esc(Ins.secTxt(l))}</td><td>${esc(l.color)}</td><td>${s.key} · ${esc(o.nombre)}</td><td>—</td><td>${bx(`${s.key}|${l.num}`)}</td></tr>`))
        : s.ends.slice().sort((p, q) => (p.capa || 0) - (q.capa || 0) || p.x - q.x).map(e => `<tr><td>${esc(e.num)}</td><td>${esc(Ins.secTxt(e))}</td><td>${esc(e.color)}</td><td>${esc(e.texto)}</td><td>${(e.capa || 0) + 1}</td><td>${esc(e.term ? e.term.txt : '')}</td><td>${bx(e.key)}</td></tr>`);
      const ok = s.li ? (a.secciones[s.key] || {}).ok : A.secs.filter(x => x.base === s.nombre).every(x => (a.secciones[x.key] || {}).ok);
      return `<section><h2>${esc(s.nombre)} ${ok ? '<span class="okk">✓ verificada</span>' : ''}</h2>${svg}
        <table><thead><tr><th>Cable</th><th>Sección</th><th>Color</th><th>Borne</th>${s.li ? '' : '<th>Capa</th>'}<th>Terminal</th><th>OK</th></tr></thead><tbody>${filas.join('')}</tbody></table>
        <div class="firma">Observaciones: ______________________________________________ &nbsp; Verificó: ____________</div></section>`;
    };
    w.document.write(`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Auditoría cruzada — ${esc(S.res.nombre)}</title>
      <style>body{font:12px/1.35 "Segoe UI",Arial,sans-serif;margin:14px;color:#111} h1{font-size:18px;margin:0 0 2px} h2{font-size:14px;margin:0 0 6px;color:#1f5fbf}
      .m{color:#555;margin-bottom:10px} section{page-break-inside:avoid;border:1px solid #ccc;border-radius:8px;padding:8px;margin-bottom:10px}
      svg{width:100%;height:300px;border:1px solid #ddd;border-radius:6px} ${Ins.PRINT_CSS} .aud{fill:#ff6a00} .aud-r{fill:none;stroke:#ff6a00} .bad{fill:#d00} .bad-r{fill:none;stroke:#d00} .aud-p,.bad-p{display:none}
      table{border-collapse:collapse;width:100%;margin-top:6px;font:11px Consolas,monospace} td,th{border:1px solid #ccc;padding:2px 6px;text-align:left} .okk{color:#1a7f37;font-size:12px}
      .firma{margin-top:6px;color:#444}</style></head><body>
      <h1>Auditoría cruzada · estación ${esc(Ins.est())}</h1>
      <div class="m">${esc(S.res.nombre)} · Auditor: ${esc(a.auditor || '________________')} · Fecha: ${new Date().toLocaleDateString()} · ${A.secs.length} secciones</div>
      ${A.secs.filter(x => !x.capa).map(x => x.li || x.acc ? x : { ...x, ends: x.todos || x.ends, nombre: x.base }).map(hoja).join('')}
      <div class="firma">Firma del auditor: ______________________ &nbsp; Firma del operario de ${esc(Ins.est())}: ______________________</div>
      <script>window.onload=()=>setTimeout(()=>print(),900)<\/script></body></html>`);
    w.document.close();
  }

  function init() {
    $('#insAudit').addEventListener('click', () => open());
    $('#auClose').addEventListener('click', close);
    $('#auCablear').addEventListener('click', aCablear);
    $('#auPrev').addEventListener('click', () => go(-1));
    $('#auNext').addEventListener('click', () => go(1));
    $('#auFit').addEventListener('click', () => draw());
    $('#auOk').addEventListener('change', e => setOk(e.target.checked, true));
    $('#auPrint').addEventListener('click', imprimir);
    $('#auQuien').addEventListener('change', e => { st().auditor = e.target.value.trim(); Ins.dirty(); });
    $('#auList').addEventListener('click', e => { const it = e.target.closest('.au-it'); if (it) { A.k = +it.dataset.i; draw(); } });
    $('#auEnds').addEventListener('click', e => {
      const b = e.target.closest('[data-obs]'); if (b) return anotar(b.closest('.au-row').dataset.key);
      const r = e.target.closest('.au-row'); if (r && r.dataset.key) toggleCheck(r.dataset.key);
    });
    $('#auEnds').addEventListener('mouseover', e => {
      const r = e.target.closest('.au-row'); $('#auSvg').querySelectorAll('.au-end.hl').forEach(x => x.classList.remove('hl'));
      if (r) [...$('#auSvg').querySelectorAll('.au-end')].filter(x => x.dataset.key === r.dataset.key).forEach(g => g.classList.add('hl'));
    });
    const svg = $('#auSvg');
    svg.addEventListener('wheel', e => {
      e.preventDefault(); if (!A.vb) return;
      const [px, py] = svgPoint(e); const f = Math.pow(1.0015, e.deltaY);
      A.vb = [px - (px - A.vb[0]) * f, py - (py - A.vb[1]) * f, A.vb[2] * f, A.vb[3] * f];
      svg.setAttribute('viewBox', A.vb.join(' '));
    }, { passive: false });
    svg.addEventListener('pointerdown', e => {
      const g = e.target.closest && e.target.closest('.au-end');
      A.drag = { x: e.clientX, y: e.clientY, vb: A.vb.slice(), s: svgPoint(e)[2], key: g ? g.dataset.key : null };
      svg.setPointerCapture(e.pointerId); svg.classList.add('drag');
    });
    svg.addEventListener('pointermove', e => { if (!A.drag) return; const d = A.drag;
      A.vb = [d.vb[0] - (e.clientX - d.x) * d.s, d.vb[1] - (e.clientY - d.y) * d.s, d.vb[2], d.vb[3]]; svg.setAttribute('viewBox', A.vb.join(' ')); });
    svg.addEventListener('pointerup', e => {
      const d = A.drag; A.drag = null; svg.classList.remove('drag');
      if (d && d.key && Math.hypot(e.clientX - d.x, e.clientY - d.y) < 5) toggleCheck(d.key);    // clic (sin arrastre) sobre un cable
    });
    document.addEventListener('keydown', e => {
      if ($('#audViewer').hidden) return;
      if (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox') { if (e.key === 'Escape') e.target.blur(); return; }
      const keys = { ArrowRight: () => go(1), ArrowLeft: () => go(-1), Escape: close, ' ': () => setOk(!$('#auOk').checked, true), '0': () => draw(), i: aCablear };
      if (keys[e.key]) { e.preventDefault(); keys[e.key](); }
    });
  }
  return { init, open };
})();
Aud.init();
