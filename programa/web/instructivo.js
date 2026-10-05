'use strict';
/* Pestaña "Instructivo de cableado": de a un cable, con el ruteo sobre el topográfico */
const Ins = (() => {
  let D = null, job = null, poll = null, saveT = null;
  const W = () => $('#insWrap');
  const LC = c => { const k = norm(c); if (k.includes('verde') && k.includes('amarillo')) return LINE.verde; return LINE[k] || '#ff00c8'; };
  // lista plana de cables en orden: [{g (grupo), i (indice en el grupo), l (linea)}]
  const flat = () => D.pasos.flatMap((p, g) => p.lineas.map((l, i) => ({ g, i, l })));
  // la punta queda fuera de la bandeja: LI (lateral izquierdo, puerta) o LD (lateral derecho)
  const LAT = d => d === 'LI' || d === 'LD';
  const est = () => (D && D.estacion) || 'E6';
  // seccion del cable: '2,5 mm²' (del campo secc, o de 'N2.5MM' en instructivos viejos)
  const secTxt = l => fmtSec(l.secc || ((l.cable || '').match(/(\d+(?:[.,]\d+)?)MM/i) || [])[1] || '');
  const secNum = l => String(l.secc || ((l.cable || '').match(/(\d+(?:[.,]\d+)?)MM/i) || [])[1] || '').replace(',', '.').replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
  // seccion corta para la manga del cable: '1mm²', '2,5mm²', '0,75mm²'
  const secCorto = l => { const n = secNum(l); return n ? n.replace('.', ',') + 'mm²' : ''; };

  /* ---- terminales (punteras) de cada punta: tabla editable en web/terminales.json ---- */
  let TERM = { pino: {}, doble: {}, colores: {} };
  const termListo = fetch('/static/terminales.json', { cache: 'no-cache' }).then(r => r.json()).then(t => { TERM = t; }).catch(() => { });
  // pino (simple) o doble: doble cuando otro tramo del MISMO cable llega al mismo borne (cable de 3 puntas: union en el borne)
  function terminal(l, which) {
    const txt = which === 'o' ? l.origen : l.destino;
    if (!txt || LAT(txt) || !D) return null;
    const otros = flat().map(x => x.l).filter(x => x !== l && x.num === l.num && (x.origen === txt || x.destino === txt));
    const tipo = otros.length ? 'doble' : 'pino';
    const secs = [l, ...otros].map(secNum).filter(Boolean);
    const sec = secs.slice().sort((a, b) => parseFloat(b) - parseFloat(a))[0] || '';
    const pollera = (TERM[tipo] || {})[sec] || null;
    const mix = new Set(secs).size > 1 ? ` (${secs.map(s => s.replace('.', ',')).join(' + ')} mm²)` : '';
    return { tipo, sec, pollera, hex: pollera ? ((TERM.colores || {})[pollera] || '#999') : null,
      txt: `${tipo === 'doble' ? 'Terminal doble' : 'Pino'} ${sec.replace('.', ',')} mm² · ${pollera ? 'pollera ' + pollera : 'color a definir'}${mix}` };
  }
  // dibujo del terminal: caño metalico en el borne + pollera del color, a lo largo del cable (dir = hacia la canaleta)
  function ferrule(p, dir, r, t, k = 1) {
    if (!t) return '';
    r = r || 1.6;
    const L = Math.hypot(dir[0], dir[1]) || 1, ang = Math.atan2(dir[1] / L, dir[0] / L) * 180 / Math.PI;
    const w = (t.tipo === 'doble' ? 1.75 : 1.0) * r, lm = 1.25 * r, lc = 1.15 * r, sw = Math.max(0.08, 0.1 * k);
    const col = t.hex || 'url(#rayasTerm)';
    return `<g class="term" transform="translate(${f2(p[0])} ${f2(p[1])}) rotate(${f2(ang)})"><title>${esc(t.txt)}</title>
      <rect x="${f2(-0.15 * r)}" y="${f2(-w / 2)}" width="${f2(lm + 0.15 * r)}" height="${f2(w)}" class="term-m" stroke-width="${f2(sw)}"/>
      <rect x="${f2(lm)}" y="${f2(-w / 2 - 0.1 * r)}" width="${f2(lc)}" height="${f2(w + 0.2 * r)}" rx="${f2(0.2 * r)}" fill="${col}" class="term-c" stroke-width="${f2(sw)}"/>
      ${t.tipo === 'doble' ? `<line x1="${f2(-0.15 * r)}" y1="0" x2="${f2(lm + lc)}" y2="0" class="term-d" stroke-width="${f2(sw * 1.2)}"/>` : ''}</g>`;
  }
  const termLen = r => 2.4 * (r || 1.6);
  const rayasDef = `<defs><pattern id="rayasTerm" width="0.8" height="0.8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="0.8" height="0.8" fill="#fff"/><rect width="0.4" height="0.8" fill="#999"/></pattern></defs>`;

  async function load() {
    await termListo;
    if (job !== S.job) { D = null; job = S.job; }
    if (D) return D;
    let st; try { st = await api(`/api/trabajo/${job}/instructivo/estado`); } catch (e) { st = {}; }
    if (st.hay_instructivo && !['procesando', 'en cola'].includes(st.estado)) D = await api(`/api/trabajo/${job}/instructivo`);
    return D;
  }
  async function open() {
    await termListo;
    if (job !== S.job) { D = null; job = S.job; }
    W().hidden = false;
    let st;
    try { st = await api(`/api/trabajo/${job}/instructivo/estado`); } catch (e) { st = {}; }
    if (['procesando', 'en cola'].includes(st.estado)) return progress();
    if (st.hay_instructivo) { if (!D) D = await api(`/api/trabajo/${job}/instructivo`); return render(); }
    show('insEmpty');
    $('#insEplan').hidden = !st.eplan;      // plano de EPLAN: las bandejas vienen en el mismo PDF
    if (st.estado === 'error') toast('No se pudo generar el instructivo: ' + (st.error || ''), 6000);
  }
  function show(id) { for (const k of ['insEmpty', 'insProg', 'insMain']) $('#' + k).hidden = k !== id; }

  /* ---- topográfico ---- */
  async function uploadTopo(f) {
    if (!f || !/\.pdf$/i.test(f.name)) return toast('Elegí el plano topográfico en PDF');
    const fd = new FormData(); fd.append('plano', f);
    try { await api(`/api/trabajo/${job}/topografico`, { method: 'POST', body: fd }); D = null; progress(); }
    catch (e) { toast(e.message, 5000); }
  }
  async function usarMismo() {
    try { await api(`/api/trabajo/${job}/topografico/mismo`, { method: 'POST' }); D = null; progress(); }
    catch (e) { toast(e.message, 5000); }
  }
  async function progress() {
    show('insProg'); clearTimeout(poll);
    const tick = async () => {
      if (S.job !== job || W().hidden) return;
      let st; try { st = await api(`/api/trabajo/${job}/instructivo/estado`); } catch (e) { poll = setTimeout(tick, 1500); return; }
      $('#insMsg').textContent = st.mensaje || '…';
      $('#insBar').style.width = Math.max(3, (st.progreso || 0) * 100) + '%';
      if (st.estado === 'terminado') { D = await api(`/api/trabajo/${job}/instructivo`); return render(); }
      if (st.estado === 'error') {
        toast('Error: ' + (st.error || ''), 7000);
        if (st.hay_instructivo) return show('insMain');
        $('#insEplan').hidden = !st.eplan;      // plano de EPLAN: se puede volver a probar con las bandejas del mismo PDF
        return show('insEmpty');
      }
      poll = setTimeout(tick, 900);
    };
    tick();
  }
  function dirty() {
    $('#insSave').textContent = 'Guardando…';
    clearTimeout(saveT);
    const j = job, data = D;
    saveT = setTimeout(async () => {
      try { await api(`/api/trabajo/${j}/instructivo`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        $('#insSave').textContent = 'Cambios guardados'; }
      catch (e) { $('#insSave').textContent = 'No se pudo guardar: ' + e.message; toast('No se pudo guardar: ' + e.message, 5000); }
    }, 600);
  }

  /* ---- dibujo del ruteo (SVG en puntos del topográfico, y invertida) ---- */
  function routeBox(lines, pad = 26, minW = 150, minH = 100) {
    const pts = lines.flatMap(l => l.ruta || []);
    const r = D.topo.region;
    if (!pts.length) return [r[0], r[1], r[2], r[3]];
    let x0 = Math.min(...pts.map(p => p[0])) - pad, x1 = Math.max(...pts.map(p => p[0])) + pad;
    let y0 = Math.min(...pts.map(p => p[1])) - pad, y1 = Math.max(...pts.map(p => p[1])) + pad;
    if (x1 - x0 < minW) { const c = (x0 + x1) / 2; x0 = c - minW / 2; x1 = c + minW / 2; }
    if (y1 - y0 < minH) { const c = (y0 + y1) / 2; y0 = c - minH / 2; y1 = c + minH / 2; }
    return [x0, y0, x1, y1];
  }
  const vbOf = b => [b[0], -b[3], b[2] - b[0], b[3] - b[1]];
  const f2 = v => (+v).toFixed(2);
  // marca del borne, del tamaño del borne: anillo hueco (no tapa a los vecinos) + punto en el tornillo
  function mark(p, r, cls, k, pulse) {
    r = r || 1.6;
    return `${pulse ? `<circle cx="${f2(p[0])}" cy="${f2(p[1])}" r="${f2(r * 2.3)}" class="${cls}-p" stroke-width="${f2(0.35 * k)}"/>` : ''}
      <circle cx="${f2(p[0])}" cy="${f2(p[1])}" r="${f2(r)}" class="${cls}-r" stroke-width="${f2(Math.min(r * 0.3, 0.3 * k + 0.12))}"/>
      <circle cx="${f2(p[0])}" cy="${f2(p[1])}" r="${f2(Math.max(0.25, r * 0.26))}" class="${cls}"/>`;
  }
  // rotulo del cable como una MANGA: rectangulo blanco centrado sobre el cable, con el numero y la seccion,
  // a lo largo del cable, empezando a 'r' del borne (despues del terminal)
  const MG = { pad: 0.35, alto: 1.3 };
  function labelLen(txt, sub, fs) {
    const n = String(txt).length, m = sub ? String(sub).length : 0;
    return (n * 0.6 + (m ? 0.45 + m * 0.6 * 0.8 : 0)) * fs + 2 * MG.pad * fs;
  }
  function label(a, b, r, txt, sub, fs, cls = '') {
    const dx = b[0] - a[0], dy = b[1] - a[1];
    const vert = Math.abs(dy) >= Math.abs(dx), sgn = vert ? (dy < 0 ? -1 : 1) : (dx > 0 ? 1 : -1);
    const Lm = labelLen(txt, sub, fs), c = (r || 1.6) + fs * 0.25 + Lm / 2, H = fs * MG.alto;
    const cx = vert ? a[0] : a[0] + sgn * c, cy = vert ? a[1] + sgn * c : a[1];
    const t = `<tspan>${esc(txt)}</tspan>${sub ? `<tspan class="lsub" font-size="${f2(fs * 0.8)}" dx="${f2(fs * 0.45)}">${esc(sub)}</tspan>` : ''}`;
    return `<g class="lbl-g ${cls}" transform="translate(${f2(cx)} ${f2(cy)})${vert ? ' rotate(-90)' : ''}">
      <rect x="${f2(-Lm / 2)}" y="${f2(-H / 2)}" width="${f2(Lm)}" height="${f2(H)}" rx="${f2(H * 0.28)}" class="manga" stroke-width="${f2(fs * 0.07)}"/>
      <text x="0" y="${f2(fs * 0.04)}" text-anchor="middle" dominant-baseline="central" font-size="${f2(fs)}" class="lbl ${cls}">${t}</text></g>`;
  }
  // otro tramo del mismo cable (3 puntas) que va por la misma canaleta que el que se cablea: se corre al COSTADO
  // (en paralelo, por fuera del resaltado) en los tramos compartidos, para que no quede tapado. El primer y el
  // ultimo tramo (los que salen del borne) no se mueven: el cable sigue naciendo del tornillo correcto.
  function alLado(ruta, ref, dist) {
    const n = ruta.length;
    if (!ref || ref.length < 2 || n < 4) return ruta;
    const seg = (a, b) => { const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy); return { a, b, L, u: L ? [dx / L, dy / L] : [0, 0] }; };
    const R = ref.slice(1).map((p, i) => seg(ref[i], p)).filter(s => s.L > 0.3);
    // corrimiento de cada tramo: a la izquierda del tramo del cable actual con el que se superpone
    const off = ruta.slice(1).map((p, i) => {
      const s = seg(ruta[i], p);
      if (i === 0 || i === n - 2 || s.L < 0.3) return [0, 0];
      for (const c of R) {
        if (Math.abs(s.u[0] * c.u[1] - s.u[1] * c.u[0]) > 0.02) continue;                     // no paralelos
        const w = [s.a[0] - c.a[0], s.a[1] - c.a[1]];
        if (Math.abs(w[0] * c.u[1] - w[1] * c.u[0]) > 0.6) continue;                           // no en la misma linea
        const t = q => (q[0] - c.a[0]) * c.u[0] + (q[1] - c.a[1]) * c.u[1];
        const lo = Math.max(Math.min(t(s.a), t(s.b)), 0), hi = Math.min(Math.max(t(s.a), t(s.b)), c.L);
        if (hi - lo > 1) return [-c.u[1] * dist, c.u[0] * dist];
      }
      return [0, 0];
    });
    if (off.every(v => !v[0] && !v[1])) return ruta;
    // vertices: interseccion de los dos tramos corridos (en las rutas por canaleta los tramos son ortogonales)
    const out = [ruta[0]];
    for (let i = 1; i < n - 1; i++) {
      const a = off[i - 1], b = off[i], s0 = seg(ruta[i - 1], ruta[i]), s1 = seg(ruta[i], ruta[i + 1]);
      const ort = Math.abs(s0.u[0] * s1.u[0] + s0.u[1] * s1.u[1]) < 0.05;
      out.push(ort ? [ruta[i][0] + a[0] + b[0], ruta[i][1] + a[1] + b[1]] : [ruta[i][0] + b[0], ruta[i][1] + b[1]]);
    }
    out.push(ruta[n - 1]);
    return out;
  }
  // cls: 'cur' (el cable que se esta cableando) o 'sib' (otro tramo del mismo numero: cable de 3 puntas)
  // o.al = {ref: ruta del cable actual, d: separacion}: correr este tramo al costado donde comparte canaleta
  function routeG(l, cls, k = 1, o = {}) {
    if (!l.ruta || l.ruta.length < 2) return '';
    const ruta = o.al ? alLado(l.ruta, o.al.ref, o.al.d) : l.ruta;
    const pts = ruta.map(p => [p[0], -p[1]]), n = pts.length;
    const d = 'M' + pts.map(p => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('L');
    const col = LC(l.color), white = ['blanco', 'amarillo'].includes(norm(l.color));
    const w = (cls === 'sib' ? 1.3 : 1.8) * k;
    const ro = (l.marca_o || [])[2], rd = (l.marca_d || [])[2];
    const st = pts[0], end = pts[n - 1], sec = secTxt(l), secM = secCorto(l);
    const fz = [funcTxt(l, 'o') && `Origen: ${funcTxt(l, 'o')}`, funcTxt(l, 'd') && `Destino: ${funcTxt(l, 'd')}`].filter(Boolean);
    let s = `<g class="rt ${cls}"><title>${esc(l.num)} (${esc(sec)}): ${esc(l.origen)} → ${esc(l.destino)}${l.largo_mm ? ' · ≈' + l.largo_mm + ' mm' : ''}${fz.length ? '\n' + esc(fz.join('\n')) : ''}</title>`;
    if (cls === 'cur') s += `<path d="${d}" class="halo" stroke-width="${6 * k}"/>`;
    if (white) s += `<path d="${d}" stroke="#333" stroke-width="${w + 1 * k}"/>`;
    s += `<path d="${d}" stroke="${col}" stroke-width="${w}"${cls === 'sib' ? ` stroke-dasharray="${f2(4 * k)} ${f2(1.6 * k)}"` : ''}/>`;
    s += ferrule(st, [pts[1][0] - st[0], pts[1][1] - st[1]], ro, terminal(l, 'o'), k);
    if (!LAT(l.destino)) s += ferrule(end, [pts[n - 2][0] - end[0], pts[n - 2][1] - end[1]], rd, terminal(l, 'd'), k);
    s += mark(st, ro, 'ori', k, o.pulse);
    if (LAT(l.destino)) s += `<text x="${(end[0] + (l.destino === 'LD' ? 4 : -4)).toFixed(1)}" y="${(end[1] + 3).toFixed(1)}" class="li" font-size="${8 * Math.min(k, 1.2)}" text-anchor="${l.destino === 'LD' ? 'start' : 'end'}">${l.destino}</text>`;
    else s += mark(end, rd, 'des', k, o.pulse);
    if (o.lab) {
      s += label(st, pts[1], termLen(ro) + 0.3, l.num, secM, o.lab, cls);
      if (!LAT(l.destino)) s += label(end, pts[n - 2], termLen(rd) + 0.3, l.num, secM, o.lab, cls);
    }
    return s + '</g>';
  }
  const imgTag = (hd) => { const r = D.topo.region;
    return rayasDef + `<image href="/api/trabajo/${job}/topo.png?v=${encodeURIComponent(D.generado || '')}${hd ? '&hd=1' : ''}" x="${r[0]}" y="${-r[3]}" width="${r[2] - r[0]}" height="${r[3] - r[1]}" preserveAspectRatio="none" opacity=".85"/>`; };
  const siblings = l => flat().map(x => x.l).filter(x => x !== l && x.num === l.num);
  // separacion del tramo punteado: por fuera del resaltado del cable actual (kc) y de los otros tramos (j)
  const ladoDe = (l, kc, ks, j) => ({ ref: l.ruta, d: 3 * kc + 0.65 * ks + 0.4 + j * (1.3 * ks + 0.8) });
  function thumb(l) {
    const sib = siblings(l);
    const vb = vbOf(routeBox([l, ...sib]));
    return `<svg class="tsvg" viewBox="${vb.map(v => v.toFixed(1)).join(' ')}" preserveAspectRatio="xMidYMid meet">${imgTag()}${sib.map((s, j) => routeG(s, 'sib', 1.1, { al: ladoDe(l, 1.2, 1.1, j) })).join('')}${routeG(l, 'cur', 1.2)}</svg>`;
  }

  /* ---- puntos del mapeo automatico con confianza media: 'a confirmar' (el motivo va en el title) ---- */
  const aConfirmar = (l, w) => (w === 'o' ? l.conf_o : (LAT(l.destino) ? null : l.conf_d)) === 'media';
  const motivoConf = (l, w) => (w === 'o' ? l.nota_o : l.nota_d) || 'punto ubicado por el mapeo automático con confianza media';
  const confPill = (l, w) => aConfirmar(l, w)
    ? ` <span class="pill conf" title="${esc('A confirmar: ' + motivoConf(l, w) + '. Si no es ese borne, ajustalo con 📍')}">a confirmar</span>` : '';
  // texto del FUNCIONAL de la punta cuando el instructivo dice otra cosa (lado físico del borne o texto corregido)
  const sinLado = t => String(t || '').replace(/ (ARRIBA|ABAJO)$/, '');
  const funcTxt = (l, w) => {
    const f = w === 'o' ? l.func_o : l.func_d, t = w === 'o' ? l.origen : l.destino;
    if (!f || f === t) return '';
    return sinLado(f) === sinLado(t) ? `En el funcional: ${f} (el instructivo lleva el lado físico del borne en el topográfico)` : `En el funcional: ${f}`;
  };
  // ALTERNATIVAS (hojas 'ALTERNATIVA n' del funcional): el cable cambia según la que se monte
  const altPill = (x, corto) => x.confirmar_montaje
    ? ` <span class="pill conf" title="${esc((x.alternativa || 'Este cable está solo en una alternativa que no es la elegida') + '. Confirmá si se monta antes de cablearlo')}">${corto ? '¿se monta?' : 'a confirmar si se monta'}</span>`
    : (x.alternativa ? ` <span class="pill alt" title="${esc(x.alternativa)}">alternativa</span>` : '');

  // salida a LI / LD elegida a mano (editor de salidas): el grupo que manda en el recorrido
  const salPill = l => { const g = LAT(l.destino) && l.salida && typeof Sal !== 'undefined' ? Sal.grupoDe(l) : null;
    return g ? ` <span class="pill sal" title="${esc(`Sale de la bandeja por el recorrido elegido para «${g.nombre}» (🧭 Salida para cambiarlo)`)}">salida elegida</span>` : ''; };

  /* ---- lista (un cable por paso) ---- */
  function cardHtml(l, g, i, n) {
    const warn = /\?/.test(l.origen + l.destino);
    const aprox = (!l.exacto_o || (!LAT(l.destino) && l.exacto_d === false)) && l.marca_o;
    const conf = ['o', 'd'].filter(w => aConfirmar(l, w));
    const confTit = conf.map(w => `${w === 'o' ? 'Origen ' + l.origen : 'Destino ' + l.destino}: ${motivoConf(l, w)}`).join('\n');
    return `<div class="cab ${l.hecho ? 'ok' : ''} ${warn ? 'rev' : ''}" data-g="${g}" data-i="${i}">
      <div class="cab-n">${n}</div>
      <div class="cab-topo" title="Ver en el topográfico">${D.topo && D.topo.region ? thumb(l) : ''}</div>
      <div class="cab-body">
        <div class="cab-t mono"><b>${esc(l.num)}</b> ${swatch(l.color)} <span class="secc">${esc(secTxt(l))}</span>
          ${l.puente ? '<span class="pill puntas" title="Cable de 3 o más puntas (puente/derivación): el visor muestra todos sus tramos">3 puntas</span>' : ''}
          ${aprox ? '<span class="pill warn" title="Punto del borne aproximado: ajustalo en el visor con 📍">punto aprox.</span>' : ''}
          ${conf.length ? `<span class="pill conf" title="${esc('A confirmar en el visor (mapeo automático, confianza media)\n' + confTit)}">a confirmar</span>` : ''}
          ${l.agregado ? `<span class="pill agr" title="${esc(l.agregado)}">agregado (verificación con el funcional)</span>` : ''}${altPill(l)}
          ${l.largo_mm ? `<span class="muted small">≈${l.largo_mm} mm</span>` : ''}</div>
        <div class="cab-od mono"><span contenteditable="true" spellcheck="false" data-f="origen" class="${funcTxt(l, 'o') ? 'func' : ''}" title="${esc(['Origen (editable)', funcTxt(l, 'o')].filter(Boolean).join('\n'))}">${esc(l.origen)}</span>
          <span class="arr">→</span><span contenteditable="true" spellcheck="false" data-f="destino" class="${funcTxt(l, 'd') ? 'func' : ''}" title="${esc(['Destino (editable)', funcTxt(l, 'd')].filter(Boolean).join('\n'))}">${esc(l.destino)}</span></div>
        <div class="cab-term small">${termChip(terminal(l, 'o'))}${!LAT(l.destino) ? ` <span class="arr">→</span> ${termChip(terminal(l, 'd'))}` : ` <span class="muted">→ ${esc(l.destino)} (se termina después)</span>`}</div>
      </div>
      <div class="cab-acts">
        <label class="chk small" title="Marcar como cableado"><input type="checkbox" data-a="ok" ${l.hecho ? 'checked' : ''}> OK</label>
        <div>
          <button class="mini" data-a="ver" title="Cablear desde este cable (visor)">▶</button>
          <button class="mini" data-a="plano" title="Ver en el plano eléctrico">⚡</button>
          <button class="mini" data-a="est" title="Se cablea en otra estación (ej. E8, gabinete): sacarlo de ${esc(est())}">⇄</button>
          <button class="mini" data-a="up" title="Subir">↑</button>
          <button class="mini" data-a="down" title="Bajar">↓</button>
          <button class="mini" data-a="del" title="Quitar">✕</button>
        </div>
      </div></div>`;
  }
  const termChip = t => t ? `<span class="tchip" title="${esc(t.txt)}"><i style="background:${t.hex || '#fff'}" class="${t.hex ? '' : 'nd'}"></i>${t.tipo === 'doble' ? 'doble ' : 'pino '}${esc(t.sec.replace('.', ','))}${t.pollera ? '' : ' ?'}</span>` : '';
  function render() {
    show('insMain');
    const F = flat(); const nl = F.length; const hechos = F.filter(x => x.l.hecho).length;
    const tot = F.reduce((a, x) => a + (x.l.largo_mm || 0), 0);
    $('#insEstacion').value = est();
    $('#insInfo').innerHTML = `Estación <b>${esc(est())}</b> · ${nl} cables en la bandeja · <b>${hechos}</b> cableados${tot ? ` · ≈${(tot / 1000).toFixed(1)} m de cable por canaleta` : ''} · topográfico: ${esc(D.topografico || '')} (hoja ${esc(D.hoja_topo ?? '?')}) · generado ${esc(D.generado || '')}`;
    $('#insProgBar').style.width = (nl ? hechos / nl * 100 : 0) + '%';
    renderMapeo();
    $('#insSave').textContent = D.editado ? 'Con cambios guardados' : '';
    let n = 0;
    $('#insPasos').innerHTML = D.pasos.map((p, g) => p.lineas.length ? `
      <div class="grp"><div class="grp-h"><input class="paso-tit" data-g="${g}" value="${esc(p.titulo || '')}" aria-label="Título del grupo">
        <select class="paso-et" data-g="${g}">${['Etapa 1', 'Etapa 2', 'Etapa 3', 'Lateral izquierdo'].map(e => `<option ${e === p.etapa ? 'selected' : ''}>${e}</option>`).join('')}</select>
        <span class="muted small">${p.lineas.filter(l => l.hecho).length}/${p.lineas.length}</span></div>
        ${p.lineas.map((l, i) => cardHtml(l, g, i, ++n)).join('')}</div>` : '').join('');
    const pend = D.pendientes || [];
    $('#insPend').innerHTML = `<div class="card-h"><h2>Pendientes: LI → LI (${pend.length})</h2></div>
      <p class="muted small">Estos cables tienen los dos extremos fuera de la bandeja: se dejan tirados donde salen los cables a LI y se cablean después de montar la bandeja en el gabinete.</p>
      <div class="plist">${pend.map(x => `<div class="mono small">${esc(x.num)}: <b>${esc(x.cable)}</b> ${x.secc ? `<span class="secc">${esc(fmtSec(x.secc))}</span>` : ''} &nbsp; ${esc(x.a)} ↔ ${esc(x.b)}${altPill(x)}</div>`).join('') || '<span class="muted">Ninguno</span>'}</div>`;
    const ot = D.otra_estacion || [];
    $('#insOtra').hidden = !ot.length;
    $('#insOtra').innerHTML = `<div class="card-h"><h2>Se cablean en otra estación (${ot.length})</h2></div>
      <p class="muted small">No se cablean en ${esc(est())}: quedan fuera de los pasos, del visor y de la auditoría. Se recuerdan al regenerar.</p>
      <div class="plist">${ot.map(l => `<div class="mono small ot-row">${esc(l.num)}: <b>${esc(l.cable)}</b> <span class="secc">${esc(secTxt(l))}</span> &nbsp; ${esc(l.origen)} → ${esc(l.destino)}
        <span class="pill">${esc(l.estacion)}</span>${altPill(l)} <button class="linkbtn" data-volver="${esc(l.num)}">volver a ${esc(est())}</button></div>`).join('')}</div>`;
    const acc = D.accesorios || [];
    $('#insAcc').hidden = !acc.length;
    $('#insAcc').innerHTML = `<div class="card-h"><h2>Puentes y accesorios (${acc.filter(a => a.hecho).length}/${acc.length})</h2></div>
      <p class="muted small">No son cables con número pero se colocan en ${esc(est())}: tildalos al ponerlos. Salen del funcional.</p>
      ${acc.map((a, i) => `<label class="chk acc-row"><input type="checkbox" data-acc="${i}" ${a.hecho ? 'checked' : ''}> <span>${esc(a.texto)}</span>
        ${a.zona ? `<span class="muted small">· ${esc(a.zona)}</span>` : ''}</label>`).join('')}`;
    const su = D.sueltos || [];
    $('#insSueltos').hidden = !su.length;
    $('#insSueltos').innerHTML = `<div class="card-h"><h2>Sin emparejar (${su.length})</h2></div>
      <p class="muted small">No se encontró el otro extremo de estos cables en el funcional: revisalos en el plano.</p>
      ${su.map(x => `<div class="mono small">${esc(x.num)}: ${esc((x.extremos || []).join(' · '))}</div>`).join('')}`;
    renderComps();
    // topografico recien cargado: preguntar una sola vez por donde salen los cables a LI / LD
    if (D.salidas && D.salidas.preguntar && typeof Sal !== 'undefined' && $('#cabViewer').hidden) setTimeout(() => Sal.asistente(), 0);
  }
  // linea plegable con el resultado del mapeo automatico de bornes (ins.mapeo) y sus avisos para revisar
  function renderMapeo() {
    let mp = $('#insMapeo');
    if (!mp) { mp = document.createElement('details'); mp.id = 'insMapeo'; mp.className = 'ins-mapeo small'; $('#insInfo').after(mp); }
    renderAlternativas();
    const m = D.mapeo, av = (m && m.avisos) || [];
    const falt = (m && m.modelos_faltantes) || [], lf = (m && m.lado_fisico) || [];
    mp.hidden = !m || (!av.length && !m.error && !falt.length && !lf.length);
    if (mp.hidden) { mp.innerHTML = ''; return; }
    const n = m.n_puntos || {}, tot = (n.alta || 0) + (n.media || 0) + (n.baja || 0);
    const partes = [`alta ${n.alta || 0}`, `media ${n.media || 0}`].concat(n.baja ? [`sin ubicar ${n.baja}`] : []);
    const verif = m.materiales === 'mapeo verificado del producto';
    if (m.sin_bandejas) mp.open = true;          // PDF de EPLAN sin hoja de bandejas: el aviso tiene que verse
    mp.innerHTML = `<summary>${esc(m.titulo || 'Mapeo automático de bornes')}: ${m.error ? 'no se pudo calcular' : `${tot} puntos (${partes.join(', ')})`}${m.manuales ? ` · ${m.manuales} con punto manual del trabajo` : ''}${falt.length ? ` · ${falt.length} modelo${falt.length > 1 ? 's' : ''} fuera del catálogo` : ''}${lf.length ? ` · ${lf.length} con el lado cambiado` : ''} · ver avisos (${av.length})</summary>
      <ul>${av.map(a => `<li>${esc(a)}</li>`).join('')}</ul>
      ${falt.length ? `<div><b>Modelos de la lista de materiales que no están en el catálogo de bornes</b> (cargalos en el catálogo para ubicarlos por su modelo):</div>
      <ul>${falt.map(f => `<li><span class="mono">${esc(f.tag)}</span>: ${esc(f.modelo || f.texto_de_la_lista || '')}${f.familia ? ` · <b>${esc(f.familia)}</b>` : ''}${f.modelo && f.texto_de_la_lista && f.texto_de_la_lista !== f.modelo ? ` <span class="muted">(${esc(f.texto_de_la_lista)})</span>` : ''}</li>`).join('')}</ul>` : ''}
      ${lf.length ? `<div><b>ARRIBA/ABAJO distinto del funcional</b> (el instructivo lleva el lado físico del borne en el topográfico):</div>
      <ul>${lf.map(x => `<li class="mono">${esc(x.num)}: ${esc(x.funcional)} → ${esc(x.instructivo)}</li>`).join('')}</ul>` : ''}
      <div class="muted">${verif ? 'puntos del mapeo verificado del producto · media = punto con una duda anotada: confirmalo en el visor (marca «a confirmar»)'
        : `alta = el borne se vio en el dibujo · media = medida del catálogo o regla de corrección: confirmalo en el visor (marca «a confirmar») ·
        ${m.de_cache ? 'resultado guardado (no cambió nada desde el último cálculo)' : `calculado en ${esc(m.segundos ?? '?')} s`}`}</div>`;
  }
  // ALTERNATIVAS del plano (hojas 'ALTERNATIVA n' del funcional: se monta una): cuál se tomó en cada hoja y por qué,
  // y los cables que cambian según la alternativa (los que están solo en una que no es la elegida: confirmar si se montan)
  function renderAlternativas() {
    let el = $('#insAlt');
    const alts = D.alternativas || [];
    const conNota = [];
    for (const p of D.pasos || []) for (const l of p.lineas) if (l.alternativa) conNota.push({ x: l, txt: `${l.origen} → ${l.destino}` });
    for (const x of D.pendientes || []) if (x.alternativa) conNota.push({ x, txt: `${x.a} ↔ ${x.b} (pendiente)` });
    for (const x of D.otra_estacion || []) if (x.alternativa) conNota.push({ x, txt: `${x.origen} → ${x.destino} (${x.estacion || 'otra estación'})` });
    if (!alts.length && !conNota.length) { if (el) { el.hidden = true; el.innerHTML = ''; } return; }
    const conf = conNota.filter(c => c.x.confirmar_montaje);
    // abierto si hay cables a confirmar (despues queda como lo deje el usuario)
    if (!el) { el = document.createElement('details'); el.id = 'insAlt'; el.className = 'ins-mapeo ins-alt small'; el.open = conf.length > 0; ($('#insMapeo') || $('#insInfo')).after(el); }
    el.hidden = false;
    const opc = a => Object.entries(a.opciones || {}).filter(([n]) => String(n) !== String(a.elegida))
      .map(([n, m]) => `${esc(n)}${m ? ' (' + esc(m) + ')' : ''}`).join(', ');
    el.innerHTML = `<summary>Alternativas del plano (se cablea una por hoja): ${alts.map(a => `hoja ${esc(a.hoja)} → <b>ALTERNATIVA ${esc(a.elegida)}</b>`).join(', ') || 'ver los cables'}${conf.length ? ` · <b class="warn-t">${conf.length} cable${conf.length > 1 ? 's' : ''} a confirmar si se monta${conf.length > 1 ? 'n' : ''}</b>` : ''}${conNota.length ? ` · ${conNota.length} cable${conNota.length > 1 ? 's' : ''} que cambian según la alternativa` : ''}</summary>
      <ul>${alts.map(a => `<li>Hoja ${esc(a.hoja)}: se tomó la <b>ALTERNATIVA ${esc(a.elegida)}</b>${(a.opciones || {})[String(a.elegida)] ? ' (' + esc(a.opciones[String(a.elegida)]) + ')' : ''}, ${esc(a.por === 'la primera' ? 'la primera (la lista de materiales no dice cuál)' : a.por)}${opc(a) ? ` · las otras: ${opc(a)}` : ''}</li>`).join('')}</ul>
      ${conNota.length ? `<ul>${conNota.map(c => `<li><span class="mono">${esc(c.x.num)}: ${esc(c.txt)}</span>${c.x.confirmar_montaje ? ' <b class="warn-t">a confirmar si se monta</b>' : ''} <span class="muted">— ${esc(c.x.alternativa)}</span></li>`).join('')}</ul>` : ''}`;
  }
  function renderComps() {
    const filas = Math.max(3, ...D.componentes.map(c => c.fila || 0));
    const ov = D.overrides || {};
    $('#insCompsBody').innerHTML = D.componentes.map((c, i) => {
      const o = ov[c.tag] || {}; const ubic = o.ubic || c.ubic, fila = o.fila || c.fila || '', lado = o.lado || '';
      return `<tr data-i="${i}" class="${c.encontrado ? '' : 'rev'}"><td class="mono"><b>${esc(c.tag)}</b></td>
        <td><select data-c="ubic">${['BANDEJA', 'LI'].map(u => `<option ${u === ubic ? 'selected' : ''}>${u}</option>`).join('')}</select></td>
        <td><select data-c="fila" ${ubic === 'BANDEJA' ? '' : 'disabled'}>${Array.from({ length: filas }, (_, k) => k + 1).map(f => `<option ${String(f) === String(fila) ? 'selected' : ''}>${f}</option>`).join('')}</select></td>
        <td><input data-c="x" type="number" step="1" value="${esc(o.x ?? c.x ?? '')}" ${ubic === 'BANDEJA' ? '' : 'disabled'}></td>
        <td><select data-c="lado" ${ubic === 'BANDEJA' ? '' : 'disabled'} title="Forzar que todos los cables de este aparato se conecten por arriba o por abajo">
          ${[['', 'según plano'], ['ARRIBA', 'todo arriba'], ['ABAJO', 'todo abajo']].map(([v, t]) => `<option value="${v}" ${v === lado ? 'selected' : ''}>${t}</option>`).join('')}</select></td>
        <td class="muted small">${c.encontrado ? 'leído «' + esc(c.leido) + '»' : 'no aparece en el topográfico'}</td></tr>`;
    }).join('');
  }

  /* ---- estaciones: cables que se cablean en otra estacion ---- */
  function moverEstacion(num) {
    const e = prompt(`¿En qué estación se cablea el cable ${num}? Se saca del instructivo de ${est()}.`, 'E8');
    if (!e || !e.trim()) return;
    D.estaciones = D.estaciones || {}; D.estaciones[num] = e.trim().toUpperCase();
    D.otra_estacion = D.otra_estacion || [];
    for (const p of D.pasos) p.lineas = p.lineas.filter(l => l.num === num ? (D.otra_estacion.push({ ...l, estacion: D.estaciones[num] }), false) : true);
    D.pasos = D.pasos.filter(p => p.lineas.length);
    dirty(); render(); toast(`Cable ${num}: se cablea en ${D.estaciones[num]}`);
  }
  function volverEstacion(num) {
    D.estaciones = D.estaciones || {}; D.estaciones[num] = est();     // se queda en esta estacion (aunque una regla lo mande a otra)
    const vuelve = (D.otra_estacion || []).filter(l => l.num === num);
    D.otra_estacion = (D.otra_estacion || []).filter(l => l.num !== num);
    for (const l of vuelve) {
      delete l.estacion;
      const p = D.pasos.find(p => p.fila === l.fila && p.lado === l.lado) || D.pasos[D.pasos.length - 1];
      if (p) p.lineas.push(l); else D.pasos.push({ fila: l.fila, lado: l.lado, titulo: 'Vueltos', etapa: 'Etapa 1', lineas: [l] });
    }
    dirty(); render(); toast(`Cable ${num} de vuelta en ${est()} (al final de su grupo; ↻ Regenerar lo pone en orden)`, 4000);
  }

  /* ---- visor "cablear de a uno" ---- */
  const V = { k: 0, vb: null, anim: null, drag: null, adjust: null };
  const plen = r => r.reduce((a, p, i) => i ? a + Math.hypot(p[0] - r[i - 1][0], p[1] - r[i - 1][1]) : 0, 0);
  function moveEnd(ruta, p, fin) {
    // cambia el punto del borne y rehace la bajada/subida recta hasta la canaleta
    let r = ruta.map(q => q.slice()); if (fin) r.reverse();
    const duct = r[1] || r[0];
    r = [[p[0], p[1]], [p[0], duct[1]], ...r.slice(1)];
    const out = [r[0]];
    for (let i = 1; i < r.length; i++) if (Math.hypot(r[i][0] - out[out.length - 1][0], r[i][1] - out[out.length - 1][1]) > 0.3) out.push(r[i]);
    if (fin) out.reverse();
    return out.map(q => [Math.round(q[0] * 10) / 10, Math.round(q[1] * 10) / 10]);
  }
  // punto ajustado a mano: vale para ESTE cable en ese borne (texto#cable); si otro tramo del mismo cable usa el mismo borne, tambien
  function setPoint(texto, num, p) {
    D.bornes_usuario = D.bornes_usuario || {};
    const q = [Math.round(p[0] * 100) / 100, Math.round(p[1] * 100) / 100];
    D.bornes_usuario[`${texto}#${num}`] = q;
    let n = 0;
    for (const { l } of flat()) {
      if (l.num !== num || !l.ruta) continue;
      if (l.origen === texto) { l.ruta = moveEnd(l.ruta, q, false); l.marca_o = [q[0], q[1], (l.marca_o || [])[2] || null]; l.exacto_o = true; l.conf_o = 'usuario'; delete l.nota_o; n++; }
      if (l.destino === texto) { l.ruta = moveEnd(l.ruta, q, true); l.marca_d = [q[0], q[1], (l.marca_d || [])[2] || null]; l.exacto_d = true; l.conf_d = 'usuario'; delete l.nota_d; n++; }
      if (D.topo.escala) l.largo_mm = Math.round(plen(l.ruta) * D.topo.escala / 10) * 10;
    }
    dirty(); toast(`Punto de «${texto}» ajustado para el cable ${num}`);
  }
  function startAdjust(which) {
    V.adjust = V.adjust === which ? null : which;
    $('#cvSvg').classList.toggle('pick', !!V.adjust);
    $('#cvAdjO').classList.toggle('on', V.adjust === 'o'); $('#cvAdjD').classList.toggle('on', V.adjust === 'd');
    if (V.adjust) toast('Hacé clic en el dibujo sobre el borne correcto (Esc para cancelar)', 3500);
  }
  function openViewer(k) {
    const F = flat(); if (!F.length) return toast('No hay cables en el instructivo');
    if (k == null) { k = F.findIndex(x => !x.l.hecho); if (k < 0) k = 0; }
    V.k = Math.max(0, Math.min(k, F.length - 1));
    $('#cabViewer').hidden = false; document.body.style.overflow = 'hidden';
    if (document.activeElement) document.activeElement.blur();
    renderList(); drawViewer(true);
  }
  function closeViewer() { $('#cabViewer').hidden = true; document.body.style.overflow = ''; if (!W().hidden) render(); }
  // boton 🧭 Salida del visor (cables a LI / LD): por donde salen de la bandeja este cable y los de su grupo
  function aSalidas() {
    const l = flat()[V.k].l; if (!LAT(l.destino)) return;
    $('#cabViewer').hidden = true;
    Sal.open({ num: l.num, volver: V.k });
  }
  // boton 🔍 Auditoria del visor: pasa a la auditoria cruzada, en la seccion donde esta este cable
  function aAuditoria() {
    const F = flat(); const l = F.length ? F[V.k].l : null;
    $('#cabViewer').hidden = true;
    Aud.open(l ? { num: l.num, texto: l.origen } : null);
  }
  function drawViewer(first) {
    const F = flat(); if (!F.length) return closeViewer();
    V.k = Math.max(0, Math.min(V.k, F.length - 1));
    const { g, l } = F[V.k];
    const sibs = siblings(l);
    $('#cvPos').textContent = `${V.k + 1} / ${F.length}`;
    $('#cvGrp').textContent = D.pasos[g].titulo || '';
    $('#cvNum').innerHTML = `<span class="mono">${esc(l.num)}</span> ${swatch(l.color)} <span class="secc big">${esc(secTxt(l))}</span>`;
    $('#cvOrig').innerHTML = esc(l.origen) + confPill(l, 'o'); $('#cvDest').innerHTML = esc(l.destino) + confPill(l, 'd') + altPill(l, true) + salPill(l);
    $('#cvOrig').title = funcTxt(l, 'o'); $('#cvDest').title = funcTxt(l, 'd');
    $('#cvLen').textContent = l.largo_mm ? `≈ ${l.largo_mm} mm por canaleta` : '';
    $('#cvOk').checked = !!l.hecho;
    $('#cvAdjD').disabled = LAT(l.destino);
    $('#cvAdjD').hidden = LAT(l.destino); $('#cvSal').hidden = !LAT(l.destino);   // a LI / LD: en su lugar, la salida
    V.adjust = null; $('#cvSvg').classList.remove('pick'); $('#cvAdjO').classList.remove('on'); $('#cvAdjD').classList.remove('on');
    $('#cvPuente').hidden = !(l.puente || sibs.length);
    $('#cvDeriv').hidden = !sibs.length;
    $('#cvDeriv').innerHTML = sibs.length ? `<b>Cable ${esc(l.num)} de ${sibs.length + 2} puntas</b> — se ven todos sus tramos (el que estás cableando en línea llena, los otros punteados): ` +
      [l, ...sibs].map(s => `<span class="mono ${s === l ? 'cur' : ''}">${esc(s.origen)} → ${esc(s.destino)} <span class="secc">${esc(secTxt(s))}</span></span>`).join(' · ') +
      (() => { const u = [l, ...sibs].flatMap(s => [['o', s.origen], ['d', s.destino]].map(([w, t]) => [t, terminal(s, w)])).find(([t, x]) => x && x.tipo === 'doble');
               return u ? ` · <b>unión en ${esc(u[0])}: ${esc(u[1].txt)}</b>` : ''; })() : '';
    const bar = $('#cvBar'); const done = F.filter(x => x.l.hecho).length; bar.style.width = (done / F.length * 100) + '%';
    // solo el cable que se esta cableando (y los otros tramos del mismo numero si tiene 3 puntas)
    const target = vbOf(roomForLupas(routeBox([l, ...sibs], 40, 220, 150)));
    const fs = fontFor('#cvSvg', target, 14);
    $('#cvSvg').innerHTML = imgTag(true) + sibs.map((s, j) => routeG(s, 'sib', 1.3, { lab: fs, al: ladoDe(l, 1.6, 1.3, j) })).join('') + routeG(l, 'cur', 1.6, { lab: fs, pulse: true });
    lupas(l, sibs);
    camera(target, first ? 0 : 420);
    markList();
  }
  // tamaño de letra (en pt del plano) para que el rotulo se vea de ~px pixeles con ese encuadre
  function fontFor(sel, vb, px) {
    const s = $(sel).getBoundingClientRect();
    const ppt = s.width && s.height ? Math.min(s.width / vb[2], s.height / vb[3]) : 3;
    return Math.max(1.2, px / ppt);
  }
  // agranda el encuadre hacia la derecha para que las lupas (arriba a la derecha) no tapen el cable
  function roomForLupas(b) {
    const s = $('#cvSvg').getBoundingClientRect(); if (!s.width || !s.height) return b;
    const f = Math.min(0.45, ($('.cv-lupas').offsetWidth + 24) / s.width), A = s.width / s.height;
    const Wd = b[2] - b[0], H = b[3] - b[1], dispW = Math.max(Wd, H * A);
    let e = Math.max(0, 2 * dispW * f - (dispW - Wd));
    if ((Wd + e) / H > A) e = Wd * f / (1 - f);
    return [b[0], b[1], b[2] + e, b[3]];
  }
  // lupas: el borne de origen y el de destino bien de cerca (se ve en que tornillo va)
  function lupas(l, sibs) {
    const r = l.ruta; const Wd = 30, H = Wd * 175 / 250;
    const set = (id, p, show) => {
      const s = $(id); s.parentElement.hidden = !show; if (!show) return;
      s.setAttribute('viewBox', `${(p[0] - Wd / 2).toFixed(2)} ${(-p[1] - H / 2).toFixed(2)} ${Wd} ${H}`);
      s.innerHTML = imgTag(true) + sibs.map((x, j) => routeG(x, 'sib', 0.4, { lab: 1.5, al: ladoDe(l, 0.45, 0.4, j) })).join('') + routeG(l, 'cur', 0.45, { lab: 1.6 });
    };
    const ok = r && r.length > 1, sec = secTxt(l);
    const to = terminal(l, 'o'), td = terminal(l, 'd');
    set('#cvLupaO', ok ? r[0] : [0, 0], ok); $('#cvLupaOt').textContent = `Origen · ${l.num} · ${l.origen} · ${to ? to.txt : sec}`;
    set('#cvLupaD', ok ? r[r.length - 1] : [0, 0], ok && !LAT(l.destino)); $('#cvLupaDt').textContent = `Destino · ${l.num} · ${l.destino} · ${td ? td.txt : sec}`;
  }
  function camera(target, ms) {
    cancelAnimationFrame(V.anim);
    const from = V.vb || target; const t0 = performance.now();
    const ease = t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const step = now => {
      const t = ms ? Math.min(1, (now - t0) / ms) : 1, e = ease(t);
      V.vb = from.map((v, i) => v + (target[i] - v) * e);
      $('#cvSvg').setAttribute('viewBox', V.vb.map(v => v.toFixed(2)).join(' '));
      if (t < 1) V.anim = requestAnimationFrame(step);
    };
    V.anim = requestAnimationFrame(step);
  }
  // pasar al siguiente marca el cable actual como cableado (pedido del taller); volver no desmarca
  function go(d, marcar = d > 0) {
    const F = flat(); const n = F.length; if (!n) return;
    if (marcar && !F[V.k].l.hecho) {
      F[V.k].l.hecho = true; dirty();
      if (F.every(x => x.l.hecho)) toast(`¡Bandeja cableada! Los ${n} cables de ${est()} están marcados. Siguiente paso: 🔍 Auditoría cruzada`, 6000);
    }
    V.k = Math.max(0, Math.min(n - 1, V.k + d));
    drawViewer();
  }
  function toggleOk(adv) {
    const F = flat(); const x = F[V.k]; x.l.hecho = !x.l.hecho; dirty();
    if (adv && x.l.hecho && V.k < F.length - 1) go(1, false); else drawViewer();
  }
  function svgPoint(e) {
    const svg = $('#cvSvg'); const r = svg.getBoundingClientRect(); const vb = V.vb;
    const s = Math.max(vb[2] / r.width, vb[3] / r.height);
    const ox = (r.width * s - vb[2]) / 2, oy = (r.height * s - vb[3]) / 2;
    return [vb[0] - ox + (e.clientX - r.left) * s, vb[1] - oy + (e.clientY - r.top) * s, s];
  }
  /* listado lateral del visor (como el del funcional): marcar / desmarcar y saltar a un cable */
  function renderList() {
    const q = norm($('#cvQ').value.trim()); const F = flat();
    let html = '', lastG = -1;
    F.forEach((x, k) => {
      const l = x.l;
      if (q && !norm(`${l.num} ${l.origen} ${l.destino} ${l.color} ${l.secc}`).includes(q)) return;
      if (x.g !== lastG) { html += `<div class="cv-gh">${esc(D.pasos[x.g].titulo || '')}</div>`; lastG = x.g; }
      html += `<div class="vs-it cv-it${l.hecho ? ' seen' : ''}" data-k="${k}" role="option" title="${esc(l.origen)} → ${esc(l.destino)}">
        <input type="checkbox" data-ok ${l.hecho ? 'checked' : ''} aria-label="Cable ${esc(l.num)} cableado">
        <span class="n">${esc(l.num)}</span>${swatch(l.color)}<span class="sec">${esc(secTxt(l))}</span>
        <span class="od mono">${esc(l.origen)} → ${esc(l.destino)}</span></div>`;
    });
    $('#cvList').innerHTML = html || '<div class="vs-empty muted small">Ningún cable coincide.</div>';
    markList();
  }
  function markList() {
    if ($('#cabViewer').hidden || !D) return;
    const F = flat(); let cur = null;
    for (const b of $('#cvList').querySelectorAll('.cv-it')) {
      const l = F[+b.dataset.k]?.l; if (!l) continue;
      b.classList.toggle('seen', !!l.hecho); b.querySelector('[data-ok]').checked = !!l.hecho;
      const on = +b.dataset.k === V.k; b.classList.toggle('on', on); b.setAttribute('aria-selected', on);
      if (on) cur = b;
    }
    $('#cvCnt').textContent = `${F.filter(x => x.l.hecho).length} de ${F.length} cableados`;
    if (cur && !$('#cvSide').hidden) cur.scrollIntoView({ block: 'nearest' });
  }
  function setSide(on) {
    $('#cvSide').hidden = !on; $('#cvSideBtn').classList.toggle('on', on); $('#cvSideBtn').setAttribute('aria-pressed', on);
    try { localStorage.setItem('listadoCablear', on ? '1' : '0'); } catch (e) { }
    if (!$('#cabViewer').hidden) drawViewer(true);
  }

  /* ---- ida y vuelta con el visor del funcional (el boton esta en el mismo lugar en los dos visores) ---- */
  function aFuncional() {
    const l = flat()[V.k].l; const occ = S.byNum[l.num] || [];
    if (!occ.length) return toast(`El cable ${l.num} no tiene etiquetas en el funcional`);
    S.insVolver = { job, k: V.k, num: l.num };
    $('#cabViewer').hidden = true;
    openCable(l.num, Math.max(0, occ.findIndex(d => (l.hojas || []).includes(d.hoja))));
  }
  async function desdeFuncional(num) {
    try { await load(); } catch (e) { return toast('No se pudo cargar el instructivo: ' + e.message, 5000); }
    if (!D) return toast('Todavía no hay instructivo: cargá el topográfico en la pestaña 🧰 Instructivo de cableado', 5000);
    const F = flat(); const v = S.insVolver;
    let k = v && v.job === job && F[v.k] && F[v.k].l.num === num ? v.k : F.findIndex(x => x.l.num === num);
    if (k < 0) {
      const ot = (D.otra_estacion || []).find(l => l.num === num), pe = (D.pendientes || []).find(x => x.num === num);
      return toast(ot ? `El cable ${num} se cablea en ${ot.estacion}, no en ${est()}` : pe ? `El cable ${num} es LI → LI: se cablea al montar la bandeja` : `El cable ${num} no está en el instructivo de la bandeja`, 5000);
    }
    $('#viewer').hidden = true;
    openViewer(k);
  }

  /* ---- acciones de la lista ---- */
  function onClick(e) {
    const cab = e.target.closest('.cab'); if (!cab) return;
    const g = +cab.dataset.g, i = +cab.dataset.i, P = D.pasos[g], L = P.lineas[i];
    const kOf = () => flat().findIndex(x => x.g === g && x.i === i);
    if (e.target.closest('.cab-topo')) return openViewer(kOf());
    const b = e.target.closest('[data-a]'); if (!b) return;
    const a = b.dataset.a;
    if (a === 'ok') { L.hecho = b.checked; dirty(); render(); return; }
    if (a === 'ver') return openViewer(kOf());
    if (a === 'plano') { const occ = S.byNum[L.num] || []; S.insVolver = { job, k: kOf(), num: L.num }; return openCable(L.num, Math.max(0, occ.findIndex(d => (L.hojas || []).includes(d.hoja)))); }
    if (a === 'est') return moverEstacion(L.num);
    if (a === 'up') { if (i > 0) [P.lineas[i - 1], P.lineas[i]] = [P.lineas[i], P.lineas[i - 1]]; else if (g > 0) { P.lineas.splice(i, 1); D.pasos[g - 1].lineas.push(L); } }
    if (a === 'down') { if (i < P.lineas.length - 1) [P.lineas[i + 1], P.lineas[i]] = [P.lineas[i], P.lineas[i + 1]]; else if (g < D.pasos.length - 1) { P.lineas.splice(i, 1); D.pasos[g + 1].lineas.unshift(L); } }
    if (a === 'del') { if (!confirm(`¿Quitar el cable ${L.num} del instructivo?`)) return; P.lineas.splice(i, 1); }
    D.pasos = D.pasos.filter(p => p.lineas.length); render(); dirty();
  }
  function onEdit(e) {
    const f = e.target.closest('[data-f]');
    if (f && f.isContentEditable) { const cab = f.closest('.cab'); D.pasos[+cab.dataset.g].lineas[+cab.dataset.i][f.dataset.f] = f.textContent.trim(); dirty(); return; }
    if (e.target.classList.contains('paso-tit')) { D.pasos[+e.target.dataset.g].titulo = e.target.value; dirty(); }
    if (e.target.classList.contains('paso-et')) { D.pasos[+e.target.dataset.g].etapa = e.target.value; dirty(); }
  }
  function regenerar(body) {
    return api(`/api/trabajo/${job}/instructivo/regenerar`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(() => progress()).catch(e => toast(e.message, 5000));
  }
  function applyComps() {
    const ov = {};
    $('#insCompsBody').querySelectorAll('tr').forEach(tr => {
      const c = D.componentes[+tr.dataset.i];
      const ubic = tr.querySelector('[data-c=ubic]').value, fila = +tr.querySelector('[data-c=fila]').value, x = tr.querySelector('[data-c=x]').value;
      const lado = tr.querySelector('[data-c=lado]').value;
      if (ubic !== c.ubic || (ubic === 'BANDEJA' && (fila !== c.fila || String(x) !== String(c.x ?? '') || lado)))
        ov[c.tag] = { ubic, fila, x: x === '' ? null : +x, ...(lado ? { lado } : {}) };
    });
    if (D.editado && !confirm('Regenerar vuelve a armar el instructivo. Se conservan las marcas de cableado, los puntos ajustados, las estaciones y la auditoría; se pierden los textos editados a mano. ¿Continuar?')) return;
    regenerar({ overrides: ov });
  }
  function textoPlano() {
    let n = 0;
    return `Instructivo de cableado · estación ${est()}\n\n` + D.pasos.map(p => `${p.titulo} [${p.etapa}]\n` + p.lineas.map(l => `${++n}. ${l.num}: ${l.cable} (${secTxt(l)})\t${l.origen}\t→\t${l.destino}${l.largo_mm ? '\t≈' + l.largo_mm + ' mm' : ''}`).join('\n')).join('\n\n');
  }
  const PRINT_CSS = `path{fill:none;stroke-linecap:round;stroke-linejoin:round} .halo{stroke:rgba(255,140,0,.55)}
      .ori{fill:#ff6a00} .des{fill:#1565c0} .ori-r{fill:none;stroke:#ff6a00} .des-r{fill:none;stroke:#1565c0;stroke-dasharray:1.2 .8} .ori-p,.des-p{display:none}
      .li{fill:#ff6a00;font-weight:700;font-family:Arial} .lbl{font-family:Consolas,monospace;font-weight:700;fill:#111;paint-order:stroke;stroke:#fff}
      .term-m{fill:#d9dde2;stroke:#333} .term-c{stroke:#222} .term-d{stroke:#333} .casing{stroke:#fff}
      .manga{fill:#fff;stroke:#333} .lbl-g .lbl{stroke:none;font-family:"Segoe UI",Arial,sans-serif;font-weight:700} .lsub{fill:#1f4f9f}`;
  function imprimir() {
    const w = window.open('', '_blank'); if (!w) return toast('El navegador bloqueó la ventana de impresión');
    const base = location.origin; let n = 0;
    const svgAbs = l => thumb(l).replace(/href="\//g, `href="${base}/`);
    w.document.write(`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Instructivo de cableado — ${esc(S.res.nombre)}</title>
      <style>body{font:12px/1.35 "Segoe UI",Arial,sans-serif;margin:16px;color:#111} h1{font-size:18px;margin:0 0 4px} h2{font-size:14px;margin:14px 0 6px;color:#1f5fbf}
      .m{color:#555;margin-bottom:10px} .g{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
      .c{display:flex;gap:10px;border:1px solid #ccc;border-radius:8px;padding:6px;page-break-inside:avoid;align-items:center}
      .n{width:26px;height:26px;border-radius:50%;background:#1f5fbf;color:#fff;display:grid;place-items:center;font-weight:700;flex:none;font-size:11px}
      svg{width:170px;height:115px;border:1px solid #ddd;border-radius:6px;flex:none} ${PRINT_CSS}
      .t{font:12px Consolas,monospace} .t b{font-size:13px} .ok{margin-left:auto;font-size:14px}</style></head><body>
      <h1>Instructivo de cableado · estación ${esc(est())}</h1><div class="m">${esc(S.res.nombre)} · topográfico ${esc(D.topografico || '')} · ${new Date().toLocaleDateString()}</div>
      ${D.pasos.map(p => `<h2>${esc(p.titulo)} · ${esc(p.etapa)}</h2><div class="g">${p.lineas.map(l => `<div class="c"><div class="n">${++n}</div>${svgAbs(l)}
        <div class="t"><b>${esc(l.num)}</b>: ${esc(l.cable)} · ${esc(secTxt(l))}<br>${esc(l.origen)} → ${esc(l.destino)}<br><span style="color:#555">${esc((terminal(l, 'o') || {}).txt || '')}${!LAT(l.destino) ? ' → ' + esc((terminal(l, 'd') || {}).txt || '') : ''}</span>${l.largo_mm ? `<br><span style="color:#666">≈${l.largo_mm} mm</span>` : ''}</div><div class="ok">☐</div></div>`).join('')}</div>`).join('')}
      <h2>Pendientes LI → LI (se cablean al montar la bandeja)</h2>
      <div class="t">${(D.pendientes || []).map(x => `${esc(x.num)}: ${esc(x.cable)} ${esc(x.a)} ↔ ${esc(x.b)}`).join('<br>')}</div>
      ${(D.otra_estacion || []).length ? `<h2>Se cablean en otra estación</h2><div class="t">${D.otra_estacion.map(l => `${esc(l.num)}: ${esc(l.cable)} ${esc(l.origen)} → ${esc(l.destino)} (${esc(l.estacion)})`).join('<br>')}</div>` : ''}
      <script>window.onload=()=>setTimeout(()=>print(),600)<\/script></body></html>`);
    w.document.close();
  }
  function descargarJSON() {
    let n = 0;
    const out = { plano: S.res.nombre, estacion: est(), generado: D.generado, topografico: D.topografico, escala_mm_por_pt: D.topo?.escala,
      cables: D.pasos.flatMap(p => p.lineas.map(l => ({ paso: ++n, grupo: p.titulo, etapa: p.etapa, cable: l.num, tipo: l.cable, color: l.color, seccion_mm2: l.secc,
        origen: l.origen, destino: l.destino, terminal_origen: terminal(l, 'o'), terminal_destino: terminal(l, 'd'), punto_origen_pt: l.marca_o, punto_destino_pt: l.marca_d || null, largo_mm: l.largo_mm, ruta_pt: l.ruta, hecho: !!l.hecho,
        texto: `${l.num}: ${l.cable} ${l.origen} → ${l.destino}` }))),
      pendientes_LI: D.pendientes, otra_estacion: D.otra_estacion || [], auditoria: D.auditoria || {} };
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 2)], { type: 'application/json' }));
    a.download = (S.res.nombre || 'plano').replace(/\.pdf$/i, '') + ' - instructivo.json'; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  function init() {
    const dz = $('#insDrop'), fi = $('#insTopoFile');
    dz.addEventListener('click', () => fi.click());
    dz.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fi.click(); } });
    fi.addEventListener('change', () => { uploadTopo(fi.files[0]); fi.value = ''; });
    dz.addEventListener('dragover', e => { e.preventDefault(); e.stopPropagation(); dz.classList.add('over'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('over'));
    dz.addEventListener('drop', e => { e.preventDefault(); e.stopPropagation(); dz.classList.remove('over'); uploadTopo(e.dataTransfer.files[0]); });
    $('#insPasos').addEventListener('click', onClick);
    $('#insPasos').addEventListener('input', onEdit);
    $('#insPasos').addEventListener('change', e => { if (!e.target.matches('[data-a=ok]')) onEdit(e); });
    $('#insPasos').addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.isContentEditable) { e.preventDefault(); e.target.blur(); } });
    $('#insOtra').addEventListener('click', e => { const b = e.target.closest('[data-volver]'); if (b) volverEstacion(b.dataset.volver); });
    $('#insAcc').addEventListener('change', e => { const i = e.target.dataset.acc; if (i == null) return; D.accesorios[+i].hecho = e.target.checked; dirty(); render(); });
    $('#insEstacion').addEventListener('change', e => { D.estacion = e.target.value.trim().toUpperCase() || 'E6'; dirty(); render(); });
    $('#insBtnComps').addEventListener('click', () => { $('#insComps').hidden = !$('#insComps').hidden; });
    $('#insCompsBody').addEventListener('change', e => { const tr = e.target.closest('tr'); if (e.target.dataset.c === 'ubic') tr.querySelectorAll('[data-c=fila],[data-c=x],[data-c=lado]').forEach(x => x.disabled = e.target.value !== 'BANDEJA'); });
    $('#insApply').addEventListener('click', applyComps);
    $('#insPrint').addEventListener('click', imprimir);
    $('#insJson').addEventListener('click', descargarJSON);
    $('#insWpc').addEventListener('click', () => D && Wpc.abrir(D, dirty));
    $('#insCopy').addEventListener('click', async () => { try { await navigator.clipboard.writeText(textoPlano()); toast('Instructivo copiado como texto'); } catch (e) { toast('No se pudo copiar'); } });
    $('#insRegen').addEventListener('click', () => {
      if (!confirm('¿Volver a armar el instructivo desde los planos? Se conservan las marcas de cableado, los puntos ajustados, las estaciones y la auditoría; se pierden los textos editados a mano.')) return;
      regenerar({});
    });
    $('#insNewTopo').addEventListener('click', () => $('#insTopoFile').click());
    $('#insMismo').addEventListener('click', usarMismo);
    $('#insCablear').addEventListener('click', () => openViewer(null));
    // visor
    $('#cvClose').addEventListener('click', closeViewer);
    $('#cvPrev').addEventListener('click', () => go(-1));
    $('#cvNext').addEventListener('click', () => go(1));
    $('#cvFit').addEventListener('click', () => camera(vbOf(D.topo.region), 350));
    $('#cvFocus').addEventListener('click', () => drawViewer());
    $('#cvOk').addEventListener('change', () => toggleOk(true));
    $('#cvPlano').addEventListener('click', aFuncional);
    $('#cvAudit').addEventListener('click', aAuditoria);
    $('#cvSal').addEventListener('click', aSalidas);
    $('#insSalidas').addEventListener('click', () => Sal.open({}));
    $('#cvSideBtn').addEventListener('click', () => setSide($('#cvSide').hidden));
    { let on = true; try { on = localStorage.getItem('listadoCablear') !== '0'; } catch (e) { } $('#cvSide').hidden = !on; $('#cvSideBtn').classList.toggle('on', on); }
    $('#cvList').addEventListener('click', e => {
      const it = e.target.closest('.cv-it'); if (!it) return;
      const k = +it.dataset.k, l = flat()[k].l;
      if (e.target.matches('[data-ok]')) { l.hecho = e.target.checked; dirty(); if (k === V.k) $('#cvOk').checked = l.hecho; markList(); $('#cvBar').style.width = (flat().filter(x => x.l.hecho).length / flat().length * 100) + '%'; return; }
      V.k = k; drawViewer();
    });
    let qT; $('#cvQ').addEventListener('input', () => { clearTimeout(qT); qT = setTimeout(renderList, 80); });
    $('#cvQ').addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); const it = $('#cvList .cv-it'); if (it) { V.k = +it.dataset.k; drawViewer(); } e.target.blur(); }
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); if (e.target.value) { e.target.value = ''; renderList(); } else e.target.blur(); }
    });
    const svg = $('#cvSvg');
    svg.addEventListener('wheel', e => {
      e.preventDefault(); if (!V.vb) return;
      const [px, py] = svgPoint(e); const f = Math.pow(1.0015, e.deltaY);
      V.vb = [px - (px - V.vb[0]) * f, py - (py - V.vb[1]) * f, V.vb[2] * f, V.vb[3] * f];
      svg.setAttribute('viewBox', V.vb.join(' '));
    }, { passive: false });
    svg.addEventListener('pointerdown', e => { V.drag = { x: e.clientX, y: e.clientY, vb: V.vb.slice(), s: svgPoint(e)[2] }; svg.setPointerCapture(e.pointerId); svg.classList.add('drag'); });
    svg.addEventListener('pointermove', e => { if (!V.drag) return; const d = V.drag;
      V.vb = [d.vb[0] - (e.clientX - d.x) * d.s, d.vb[1] - (e.clientY - d.y) * d.s, d.vb[2], d.vb[3]]; svg.setAttribute('viewBox', V.vb.join(' ')); });
    svg.addEventListener('pointerup', e => {
      const d = V.drag; V.drag = null; svg.classList.remove('drag');
      if (V.adjust && d && Math.hypot(e.clientX - d.x, e.clientY - d.y) < 5) {   // clic (sin arrastre) en modo ajuste
        const [x, y] = svgPoint(e); const l = flat()[V.k].l;
        setPoint(V.adjust === 'o' ? l.origen : l.destino, l.num, [x, -y]);
        V.adjust = null; drawViewer();
      }
    });
    $('#cvAdjO').addEventListener('click', () => startAdjust('o'));
    $('#cvAdjD').addEventListener('click', () => startAdjust('d'));
    document.addEventListener('keydown', e => {
      if ($('#cabViewer').hidden) return;
      if (e.target.isContentEditable || e.target.tagName === 'INPUT' && e.target.type !== 'checkbox') return;
      if (e.key === 'Escape' && V.adjust) { e.preventDefault(); return startAdjust(null); }
      const keys = { ArrowRight: () => go(1), ArrowLeft: () => go(-1), Escape: closeViewer, ' ': () => toggleOk(true), Enter: () => toggleOk(true),
        '0': () => camera(vbOf(D.topo.region), 350), f: () => drawViewer(), l: () => setSide($('#cvSide').hidden), a: aAuditoria, s: aSalidas };
      if (keys[e.key]) { e.preventDefault(); keys[e.key](); }
    });
  }
  return { open, init, hide: () => { W().hidden = true; clearTimeout(poll); }, desdeFuncional,
    // para la auditoria
    get D() { return D; }, get job() { return job; }, load, flat, dirty, imgTag, LC, mark, label, vbOf, secTxt, est, PRINT_CSS, render, fontFor,
    terminal, ferrule, termLen, termChip, labelLen, LAT, secCorto, openViewer, routeG };
})();
Ins.init();
