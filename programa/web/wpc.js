'use strict';
/* Lista de cables para el centro de cableado WPC: en el orden del instructivo, con largo, color y sección,
   y el .csv igual al que exporta la macro de la planilla (UTF-8 con BOM, ';', coma decimal, sin encabezado, 49 columnas).
   Lo que se edita acá (largos, colores, excluidos) se guarda en D.wpc del instructivo.
   Largo (wpc.json): en la bandeja, recorrido por las canaletas + sobrante + agregado del taller (75 mm). Los que salen a
   LI, con la estación E8 (D.estacion8: adónde van de verdad), por la regla del taller del 2026-10-06:
   - muere en la bandeja lateral: 75 (borne → canaleta) + canaleta de la bandeja + 100 (curva posterior → LI) + canaleta
     de la lateral + 150 (canaleta → borne);
   - sigue a la puerta / placa: 75 (borne → canaleta) + canaleta de la bandeja + 1850.
   "Canaleta" = la parte de la ruta que corre DENTRO de las canaletas (sin la acometida del borne, que va con el fijo).
   Sin E8 (plano sin la lateral): recorrido + sobrante + lo fijo a LI / LD + agregado. Pendientes de la lateral: canaleta
   de la lateral + margen (o puerta / placa) + agregado. La WPC solo corta (columnas fijas sin pelar ni crimpar). Reemplazos por producto
   (wpc.json → reemplazos[documento]): un color y sección se cortan con otro (PAE: sin slots de 4 mm²); solo acá, el
   instructivo no cambia. Giro de los TERMOS (columna 22, "giro origen|giro destino" en grados) según el lado de cada
   punta: una aguas arriba y otra aguas abajo → 0|0; las dos abajo → 180|0; las dos arriba → 0|180 (regla del taller).
   No van al arnés (destildados, con el motivo): 35 mm², comunicación, solenoides y campo (wpc.json → fuera). */
const Wpc = (() => {
  let D = null, guardar = null, CFG = null;
  const cfgListo = fetch('/static/wpc.json', { cache: 'no-cache' }).then(r => r.json()).then(c => { CFG = c; }).catch(() => { CFG = {}; });
  const NCOL = 49;
  const key = l => `${l.num}|${l.origen ?? l.a}|${l.destino ?? l.b}`;
  // al regenerar el instructivo puede quedar wpc = {} (o a medias): se completa lo que falte
  const W = () => {
    const w = D.wpc || (D.wpc = {});
    w.largo ??= {}; w.color ??= {}; w.excluir ??= []; w.incluir ??= []; w.cfg ??= {}; w.giro ??= {};
    return w;
  };
  const P = k => { const c = W().cfg; return c[k] != null && c[k] !== '' ? +c[k] : +(CFG[k] ?? 0); };
  const secNum = l => String(l.secc || ((l.cable || '').match(/(\d+(?:[.,]\d+)?)MM/i) || [])[1] || '').replace(',', '.');
  const coma = v => String(v).replace('.', ',');
  const LAT = d => d === 'LI' || d === 'LD';
  // reemplazos por producto (wpc.json → reemplazos[documento del rótulo]): el cable se corta con otro color y sección
  // porque la WPC no tiene slot para el original. Solo en esta lista: el instructivo y el listado no cambian
  const normC = c => String(c ?? '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const reglas = () => ((CFG.reemplazos || {})[(D.producto || {}).documento] || []).filter(r => r && r.de && r.a);
  function reemplazo(l) {
    const sec = parseFloat(secNum(l)), col = normC(l.color);
    return reglas().find(r => normC(r.de.color) === col && parseFloat(r.de.secc) === sec) || null;
  }
  // ---- cables que no van al arnés de la WPC (wpc.json → fuera): el motivo, o null si va
  const FU = () => CFG.fuera || {};
  const re_ = k => { const s = FU()[k]; try { return s ? new RegExp(s, 'i') : null; } catch (e) { return null; } };
  function motivoFuera(f) {
    const l = f.l, sec = parseFloat(f.sec), txt = `${l.origen ?? l.a ?? ''} ${l.destino ?? l.b ?? ''}`;
    if (!f.sec) return 'sin sección (malla, tierra o cable de campo)';
    if (FU().seccion_desde != null && sec >= +FU().seccion_desde) return `${coma(f.sec)} mm²: no la corta la WPC`;
    if (FU().comunicacion_seccion_hasta != null && sec <= +FU().comunicacion_seccion_hasta) return 'comunicación (sección fina)';
    const rc = re_('comunicacion_re'), rs = re_('solenoide_re'), rk = re_('campo_re');
    if (rc && rc.test(txt)) return 'comunicación';
    if (rs && rs.test(txt)) return 'va a una solenoide';
    if (l.estacion === 'CAMPO' || (rk && rk.test(txt)) || /^s\/n\b/i.test(l.num || '')) return 'va a campo';
    return null;
  }
  // ---- giro de los termos (señalizadores) de las dos puntas, "origen|destino" en grados (columna 22 del CSV)
  // El lado de cada punta: arriba / abajo del eje de su riel por el punto exacto del borne (como el instructivo);
  // sin punto, por el texto (ARRIBA / ABAJO, QUATTRO .1 .2 arriba / .3 .4 abajo); la punta que sale a LI / LD, abajo.
  function ladoPunto(p, tag) {
    const F = (D.topo || {}).filas || []; if (!p || !F.length) return null;
    const c = ((D.topo || {}).comp || {})[tag], eje = c && c.fila && c.fila <= F.length ? F[c.fila - 1] : F.reduce((a, e) => Math.abs(e - p[1]) < Math.abs(a - p[1]) ? e : a);
    return Math.abs(p[1] - eje) < 1 ? null : (p[1] > eje ? 'arriba' : 'abajo');
  }
  function ladoTexto(t) {
    t = String(t || '');
    if (/ ARRIBA$/.test(t)) return 'arriba';
    if (/ ABAJO$/.test(t)) return 'abajo';
    const m = /\.(\d)$/.exec(t); return m ? ('12'.includes(m[1]) ? 'arriba' : 'abajo') : null;
  }
  const tagDe = t => String(t || '').split(' ')[0];
  function lados(f) {
    const l = f.l;
    if (f.tipo === 'pendiente') return { o: null, d: null };
    const o = l.lado || ladoPunto(l.marca_o, tagDe(l.origen)) || ladoTexto(l.origen);
    const d = LAT(l.destino) ? 'abajo' : (ladoPunto(l.marca_d, tagDe(l.destino)) || ladoTexto(l.destino));
    return { o, d };
  }
  function giroCalc(f) {
    const T = CFG.termos || {}, { o, d } = lados(f), txt = s => s === 'arriba' ? 'aguas arriba' : s === 'abajo' ? 'aguas abajo' : 'sin dato';
    let v, por;
    if (!o || !d) { v = T.sin_dato ?? '0|0'; por = 'no se sabe el lado de una punta'; }
    else if (o === 'abajo' && d === 'abajo') { v = T.abajo_abajo ?? '180|0'; por = 'las dos puntas aguas abajo: gira el primer termo'; }
    else if (o === 'arriba' && d === 'arriba') { v = T.arriba_arriba ?? '0|180'; por = 'las dos puntas aguas arriba: gira el segundo termo'; }
    else { v = T.mixto ?? '0|0'; por = 'una punta aguas arriba y otra aguas abajo: ningún termo gira'; }
    return { v, o, d, como: `origen ${txt(o)}${LAT(f.l.destino) ? ` · destino ${f.l.destino} (afuera: se toma aguas abajo)` : ` · destino ${txt(d)}`} → ${por}` };
  }

  // filas en el orden de cableado: la bandeja (pasos) y, si se piden, pendientes LI↔LI y otra estación al final
  function filas() {
    const w = W(), out = [];
    E8L = lateralInfo();
    D.pasos.forEach(p => p.lineas.forEach(l => out.push({ l, tipo: 'bandeja', grupo: p.titulo })));
    if (w.cfg.pendientes) (D.pendientes || []).forEach(l => out.push({ l, tipo: 'pendiente', grupo: 'Pendientes LI ↔ LI' }));
    if (w.cfg.otra) (D.otra_estacion || []).forEach(l => out.push({ l, tipo: 'otra', grupo: 'Otra estación (' + (l.estacion || '') + ')' }));
    const excl = new Set(w.excluir), incl = new Set(w.incluir || []);
    out.forEach((f, i) => {
      f.k = key(f.l);
      f.rg = reemplazo(f.l);                      // regla del producto: otro color y sección para la WPC
      f.sec = f.rg ? String(f.rg.a.secc).replace(',', '.') : secNum(f.l);
      // no va al arnés (sin sección, 35 mm², comunicación, solenoide, campo) salvo que se tilde a mano
      f.motivo = motivoFuera(f);
      f.fuera = excl.has(f.k) || (!!f.motivo && !incl.has(f.k));
      f.calc = largoCalc(f); f.largo = w.largo[f.k] != null ? +w.largo[f.k] : f.calc.mm;
      f.color = w.color[f.k] || (CFG.colores || {})[f.rg ? f.rg.a.color : f.l.color] || '';
      f.giroCalc = giroCalc(f); f.giro = w.giro[f.k] || f.giroCalc.v;
    });
    return out;
  }
  // ---- adonde va de verdad un cable que sale a LI / LD, con la estacion E8 (D.estacion8): recorrido por las canaletas de
  // la bandeja lateral (dibujada en el topografico) o a la puerta / placa (pasa por la canaleta de la lateral)
  const sinLado = t => String(t || '').replace(/ (ARRIBA|ABAJO)$/, '');
  const claveE8 = (num, a, b) => [num, ...[sinLado(a), sinLado(b)].sort()].join('|');
  let E8L = null;
  // ---- parte de la ruta que corre DENTRO de las canaletas (mm): desde el primer punto que cae en una canaleta hasta el
  // final (la salida de la bandeja). Lo que va antes es la acometida del borne, que la regla del taller pone como fijo.
  const dentro = (p, b) => b[0] - 0.6 <= p[0] && p[0] <= b[2] + 0.6 && b[1] - 0.6 <= p[1] && p[1] <= b[3] + 0.6;
  function canaleta(ruta, ductos, escala) {
    if (!ruta || ruta.length < 2 || !escala) return null;
    const i = ruta.findIndex(p => (ductos || []).some(d => d.b && dentro(p, d.b)));
    if (i < 0) return null;
    let mm = 0;
    for (let k = i; k < ruta.length - 1; k++) mm += Math.hypot(ruta[k + 1][0] - ruta[k][0], ruta[k + 1][1] - ruta[k][1]);
    return Math.round(mm * escala);
  }
  function lateralInfo() {
    const e8 = D.estacion8 || {}, sale = {}, par = {};
    (e8.laterales || []).forEach(L => {
      L.pasos.forEach(p => p.lineas.forEach(x => {
        if (x.largo_mm == null) return;
        const v = { tipo: 'lateral', mm: x.largo_mm, can: canaleta(x.ruta, L.ductos, L.escala), borne: x.origen, donde: L.nombre.toLowerCase(), puerta: x.otra === 'puerta / placa' };
        if (x.otra === 'bandeja principal') sale[`${x.num}|${sinLado(x.destino)}`] ??= v;   // de la bandeja (E6) a la lateral
        else par[x.clave] = v;                                                         // misma lateral, o lateral ↔ puerta
      }));
    });
    (e8.afuera || []).forEach(g => g.zona === 'puerta / placa' && g.cables.forEach(x => {
      if (x.otra_donde === 'bandeja principal') sale[`${x.num}|${sinLado(x.otra)}`] ??= { tipo: 'puerta', donde: x.borne };
    }));
    return { sale, par };
  }
  // largo = recorrido por las canaletas + margen (pelado, peinado) y, si sale de la bandeja, lo que necesita en LI/LD,
  // más el AGREGADO del taller según adónde va (en bandeja / a LI / a puerta y placa), a más de los márgenes de siempre
  function largoCalc(f) {
    const l = f.l, r = P('redondeo') || 1, up = v => Math.ceil(v / r) * r;
    const AG = { bandeja: P('agregado_bandeja'), LI: P('agregado_LI'), puerta: P('agregado_puerta') };
    const mas = k => AG[k] ? ` + agregado ${k === 'LI' ? 'a LI' : k === 'puerta' ? 'puerta / placa' : 'en bandeja'} ${AG[k]}` : '';
    if (f.tipo === 'pendiente') {
      const x = E8L.par[claveE8(l.num, l.a, l.b)];
      if (x) {
        const ext = x.puerta ? P('extra_puerta') : P('margen_LI'), k = x.puerta ? 'puerta' : 'LI';
        return { mm: up(x.mm + ext + AG[k]), como: `canaleta de la ${x.donde} ${x.mm} + ${x.puerta ? 'puerta / placa' : 'margen'} ${ext}${mas(k)}, redondeado a ${r}` };
      }
      return { mm: P('largo_pendiente'), como: 'pendiente LI↔LI (valor fijo)' };
    }
    if (!l.largo_mm) return { mm: P('largo_sin_ruta'), como: 'sin ruta en el topográfico: valor fijo', falta: true };
    const x = E8L.sale[`${l.num}|${sinLado(l.origen)}`];
    if (x && (x.tipo === 'lateral' || x.tipo === 'puerta')) {
      // regla del taller (2026-10-06): acometida fija del borne a la canaleta + lo que corre dentro de las canaletas de la bandeja
      const can = canaleta(l.ruta, (D.topo || {}).ductos, (D.topo || {}).escala), canT = can != null ? can : l.largo_mm;
      const b = `${P('acometida')} (borne → canaleta) + canaleta de la bandeja ${canT}${can == null ? ' (ruta entera)' : ''}`;
      if (x.tipo === 'lateral') {
        const cl = x.can != null ? x.can : x.mm;
        return { mm: up(P('acometida') + canT + P('curva_LI') + cl + P('acometida_LI')),
          como: `${b} + curva a ${l.destino} ${P('curva_LI')} + canaleta de la ${x.donde} ${cl} + ${P('acometida_LI')} (canaleta → ${x.borne || 'borne'}), redondeado a ${r}` };
      }
      return { mm: up(P('acometida') + canT + P('puerta')),
        como: `${b} + puerta / placa ${P('puerta')} (${x.donde}), redondeado a ${r}` };
    }
    // queda en la bandeja, o sale a LI / LD sin saber adónde (sin estación E8): agregado según el caso
    const ext = l.destino === 'LI' ? P('extra_LI') : l.destino === 'LD' ? P('extra_LD') : 0;
    const k = !LAT(l.destino) ? 'bandeja' : (x && x.tipo === 'puerta') ? 'puerta' : 'LI';
    return { mm: up(l.largo_mm + P('margen_bandeja') + ext + AG[k]),
      como: `canaletas ${l.largo_mm} + margen ${P('margen_bandeja')}${ext ? ` + ${l.destino} ${ext}` : ''}${mas(k)}, redondeado a ${r}` };
  }

  function csv(fs) {
    const fx = CFG.fijos || {};
    const lin = fs.map(f => {
      const c = new Array(NCOL).fill('');
      c[6] = f.largo; c[7] = 1; c[8] = coma(f.sec); c[9] = f.color; c[11] = f.l.num; c[19] = f.l.num;
      c[21] = f.giro;                      // giro de los termos: "origen|destino" en grados (Labeling Position)
      c[23] = fx.pelado_origen ?? 10; c[24] = fx.proceso_origen ?? 1; c[25] = fx.proceso_destino ?? 1;
      c[27] = fx.crimpado_origen ?? 8; c[45] = fx.dimension_origen ?? 10; c[46] = fx.crimpado_destino ?? 8;
      return c.join(';');
    });
    return '﻿' + lin.map(s => s + '\r\n').join('');
  }
  function bajar(nombre, txt) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([txt], { type: 'text/csv;charset=utf-8' }));
    a.download = nombre; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  const base = () => (S.res?.nombre || 'plano').replace(/\.pdf$/i, '');

  function render() {
    const fs = filas(), w = W(), M = $('#wpcModal');
    if (typeof Prod !== 'undefined') Prod.mostrarEn('#wpcProd', D.producto);     // línea «Producto» (web/producto.js)
    const faltan = fs.filter(f => !f.fuera && (f.calc.falta || !f.color || !f.sec)).length;
    M.querySelector('.wpc-cfg').innerHTML = [['margen_bandeja', 'Sobrante en bandeja (mm)'], ['agregado_bandeja', '+ agregado en bandeja (mm)'],
      ['acometida', 'Borne → canaleta (mm)'], ['curva_LI', 'Curva posterior → LI (mm)'], ['acometida_LI', 'Canaleta → borne en LI (mm)'], ['puerta', 'Sigue a puerta / placa (mm)'],
      ['margen_LI', 'Pendientes lateral ↔ lateral: margen (mm)'], ['extra_puerta', 'Pendientes lateral → puerta (mm)'],
      ['extra_LI', 'A LI sin plano (mm)'], ['extra_LD', 'A LD sin plano (mm)'], ['agregado_LI', '+ agregado a LI / LD (mm)'], ['agregado_puerta', '+ agregado puerta / placa (mm)'],
      ['redondeo', 'Redondeo'], ['largo_sin_ruta', 'Sin ruta'], ['largo_pendiente', 'Pendientes']].map(([k, t]) =>
      `<label class="small">${t} <input type="number" step="10" min="0" data-cfg="${k}" value="${P(k)}" style="width:70px"></label>`).join('') +
      `<label class="small"><input type="checkbox" data-cfg="pendientes" ${w.cfg.pendientes ? 'checked' : ''}> Pendientes LI↔LI</label>
       <label class="small"><input type="checkbox" data-cfg="otra" ${w.cfg.otra ? 'checked' : ''}> Otra estación</label>`;
    const nRg = fs.filter(f => !f.fuera && f.rg).length, nFuera = fs.filter(f => f.fuera && f.motivo && !w.excluir.includes(f.k)).length;
    const nGiro = fs.filter(f => !f.fuera && f.giro !== '0|0').length, nSin = fs.filter(f => !f.fuera && (!f.giroCalc.o || !f.giroCalc.d)).length;
    M.querySelector('.wpc-exp').innerHTML = `<span class="muted small">${fs.filter(f => !f.fuera).length} cables${faltan ? ` · <b style="color:#c0392b">${faltan} a revisar</b>` : ''}${nRg ? ` · <b>${nRg}</b> con otro color y sección por regla del producto (${esc((D.producto || {}).documento || '')})` : ''}${nFuera ? ` · ${nFuera} fuera del arnés por regla (35 mm², comunicación, solenoides, campo)` : ''} · termos: ${nGiro} con giro${nSin ? ` (${nSin} sin el lado de una punta)` : ''} · la WPC solo corta (sin pelar ni crimpar)</span>
      <span class="grow"></span><button class="btn primary sm" data-exp>⭳ Exportar CSV</button>`;
    let g = null;
    M.querySelector('tbody').innerHTML = fs.map((f, i) => {
      const hdr = f.grupo !== g ? (g = f.grupo, `<tr class="wpc-g"><td colspan="9">${esc(f.grupo)}</td></tr>`) : '';
      const mal = f.calc.falta || !f.color || !f.sec;
      const giros = (CFG.termos || {}).opciones || ['0|0', '180|0', '0|180', '180|180'];
      return hdr + `<tr data-k="${esc(f.k)}" class="${f.fuera ? 'wpc-fuera' : ''}">
        <td><input type="checkbox" data-a="usar" ${f.fuera ? '' : 'checked'} title="${esc(f.motivo ? 'Fuera del arnés: ' + f.motivo + ' (tildalo para incluirlo igual)' : 'Incluir en el CSV')}"></td>
        <td class="small">${i + 1}</td>
        <td><b>${esc(f.l.num)}</b></td>
        <td><select data-a="color">${(f.color && !(CFG.codigos || []).includes(f.color) ? [f.color] : []).concat(CFG.codigos || []).concat(f.color ? [] : ['']).map(c => `<option ${c === f.color ? 'selected' : ''}>${c}</option>`).join('')}</select>
          ${f.rg ? `<span class="small wpc-rg" title="${esc(`Regla WPC del producto: ${f.l.color} ${coma(secNum(f.l))} mm² se corta en ${f.rg.a.color} ${coma(f.rg.a.secc)} mm²${f.rg.motivo ? ' (' + f.rg.motivo + ')' : ''}. El instructivo no cambia`)}">${esc(f.l.color)} ${esc(coma(secNum(f.l)))} → <b>${esc(f.rg.a.color)} ${esc(coma(f.rg.a.secc))}</b></span>` : `<span class="muted small">${esc(f.l.color || '')}</span>`}</td>
        <td>${esc(coma(f.sec))}${f.rg ? ` <span class="muted small" title="Sección del plano">(era ${esc(coma(secNum(f.l)))})</span>` : ''}</td>
        <td><input type="number" step="10" min="0" data-a="largo" value="${f.largo}" style="width:72px;${w.largo[f.k] != null ? 'font-weight:700' : ''}${mal ? ';background:#fde2e2' : ''}" title="${esc(f.calc.como)}${w.largo[f.k] != null ? ' · editado a mano (vacío = calculado ' + f.calc.mm + ')' : ''}"></td>
        <td class="small">${esc(f.l.origen ?? f.l.a)} → ${esc(f.l.destino ?? f.l.b)}${f.motivo ? `<br><span class="wpc-mot">${esc(f.motivo)}</span>` : ''}</td>
        <td><select data-a="giro" class="wpc-giro${w.giro[f.k] ? ' manual' : ''}${!f.giroCalc.o || !f.giroCalc.d ? ' sin' : ''}" title="${esc('Giro de los termos (origen|destino): ' + f.giroCalc.como + (w.giro[f.k] ? ' · elegido a mano (calculado ' + f.giroCalc.v + ')' : ''))}">${giros.concat(giros.includes(f.giro) ? [] : [f.giro]).map(g => `<option ${g === f.giro ? 'selected' : ''}>${g}</option>`).join('')}</select></td>
        <td class="small muted">${f.l.largo_mm ? f.l.largo_mm : '—'}</td></tr>`;
    }).join('');
  }
  function onEvt(e) {
    const t = e.target, w = W();
    if (t.dataset.cfg) {
      if (e.type !== 'change') return;
      w.cfg[t.dataset.cfg] = t.type === 'checkbox' ? t.checked : t.value;
      guardar(); render(); return;
    }
    const exp = t.closest('[data-exp]');
    if (exp && e.type === 'click') {
      bajar(`${base()} - WPC.csv`, csv(filas().filter(f => !f.fuera)));
      return;
    }
    const tr = t.closest('tr[data-k]'); if (!tr) return;
    const k = tr.dataset.k, a = (t.closest('[data-a]') || {}).dataset?.a;
    if (a === 'usar' && e.type === 'change') {
      w.incluir = w.incluir || [];
      w.excluir = w.excluir.filter(x => x !== k); w.incluir = w.incluir.filter(x => x !== k);
      (t.checked ? w.incluir : w.excluir).push(k);
    }
    else if (a === 'color' && e.type === 'change') { w.color[k] = t.value; }
    else if (a === 'giro' && e.type === 'change') { const f = filas().find(x => x.k === k); if (f && t.value === f.giroCalc.v) delete w.giro[k]; else w.giro[k] = t.value; }
    else if (a === 'largo' && e.type === 'change') { if (t.value === '') delete w.largo[k]; else w.largo[k] = Math.max(0, Math.round(+t.value)); }
    else return;
    guardar(); render();
  }

  async function abrir(d, fnGuardar) {
    D = d; guardar = fnGuardar;
    await cfgListo;
    let M = $('#wpcModal');
    if (!M) {
      M = document.createElement('div'); M.id = 'wpcModal'; M.className = 'wpc-modal';
      M.innerHTML = `<div class="wpc-box" role="dialog" aria-label="Lista de cables para WPC">
        <div class="wpc-h"><h2>Lista de cables para WPC</h2><span class="muted small">En el orden del instructivo. Todo en un solo CSV. El largo editado a mano queda en negrita.</span>
          <span class="grow"></span><button class="btn ghost sm" data-cerrar>✕ Cerrar</button></div>
        <div class="small prod-linea" id="wpcProd" hidden></div>
        <div class="wpc-cfg"></div><div class="wpc-exp"></div>
        <div class="wpc-t"><table><thead><tr><th></th><th>#</th><th>Cable</th><th>Color</th><th>mm²</th><th>Largo</th><th>Origen → destino</th><th title="Giro de los termos (señalizadores): origen|destino en grados. Una punta arriba y otra abajo: 0|0 · las dos abajo: 180|0 · las dos arriba: 0|180">Termos</th><th title="Recorrido por las canaletas">Canaleta</th></tr></thead><tbody></tbody></table></div></div>`;
      document.body.appendChild(M);
      M.addEventListener('click', e => { if (e.target === M || e.target.closest('[data-cerrar]')) M.hidden = true; else onEvt(e); });
      M.addEventListener('change', onEvt);
      document.addEventListener('keydown', e => { if (e.key === 'Escape' && !M.hidden) M.hidden = true; });
    }
    M.hidden = false; render();
  }
  return { abrir, csv: fs => csv(fs), filas: () => filas() };
})();
