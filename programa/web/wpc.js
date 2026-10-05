'use strict';
/* Lista de cables para el centro de cableado WPC: en el orden del instructivo, con largo, color y sección,
   y el .csv igual al que exporta la macro de la planilla (UTF-8 con BOM, ';', coma decimal, sin encabezado, 49 columnas).
   Lo que se edita acá (largos, colores, excluidos) se guarda en D.wpc del instructivo. */
const Wpc = (() => {
  let D = null, guardar = null, CFG = null;
  const cfgListo = fetch('/static/wpc.json', { cache: 'no-cache' }).then(r => r.json()).then(c => { CFG = c; }).catch(() => { CFG = {}; });
  const NCOL = 49;
  const key = l => `${l.num}|${l.origen ?? l.a}|${l.destino ?? l.b}`;
  // al regenerar el instructivo puede quedar wpc = {} (o a medias): se completa lo que falte
  const W = () => {
    const w = D.wpc || (D.wpc = {});
    w.largo ??= {}; w.color ??= {}; w.excluir ??= []; w.incluir ??= []; w.cfg ??= {};
    return w;
  };
  const P = k => { const c = W().cfg; return c[k] != null && c[k] !== '' ? +c[k] : +(CFG[k] ?? 0); };
  const secNum = l => String(l.secc || ((l.cable || '').match(/(\d+(?:[.,]\d+)?)MM/i) || [])[1] || '').replace(',', '.');
  const coma = v => String(v).replace('.', ',');

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
      f.sec = secNum(f.l);
      // sin seccion (malla de un cable armado): no es un conductor que corte la WPC, va afuera salvo que se tilde
      f.fuera = excl.has(f.k) || (!f.sec && !incl.has(f.k));
      f.calc = largoCalc(f); f.largo = w.largo[f.k] != null ? +w.largo[f.k] : f.calc.mm;
      f.color = w.color[f.k] || (CFG.colores || {})[f.l.color] || '';
    });
    return out;
  }
  // ---- adonde va de verdad un cable que sale a LI / LD, con la estacion E8 (D.estacion8): recorrido por las canaletas de
  // la bandeja lateral (dibujada en el topografico) o a la puerta / placa (pasa por la canaleta de la lateral)
  const sinLado = t => String(t || '').replace(/ (ARRIBA|ABAJO)$/, '');
  const claveE8 = (num, a, b) => [num, ...[sinLado(a), sinLado(b)].sort()].join('|');
  let E8L = null;
  function lateralInfo() {
    const e8 = D.estacion8 || {}, sale = {}, par = {}, canal = {};
    (e8.laterales || []).forEach(L => {
      // lo que recorre un cable de punta a punta de la lateral: la canaleta horizontal mas larga
      const mm = Math.max(0, ...(L.ductos || []).filter(d => d.h).map(d => Math.abs(d.b[2] - d.b[0]) * (L.escala || 1)));
      if (mm && !(canal[L.lado] > mm)) canal[L.lado] = Math.round(mm);
      L.pasos.forEach(p => p.lineas.forEach(x => {
        if (x.largo_mm == null) return;
        const v = { tipo: 'lateral', mm: x.largo_mm, donde: L.nombre.toLowerCase(), puerta: x.otra === 'puerta / placa' };
        if (x.otra === 'bandeja principal') sale[`${x.num}|${sinLado(x.destino)}`] ??= v;   // de la bandeja (E6) a la lateral
        else par[x.clave] = v;                                                         // misma lateral, o lateral ↔ puerta
      }));
    });
    (e8.afuera || []).forEach(g => g.zona === 'puerta / placa' && g.cables.forEach(x => {
      if (x.otra_donde === 'bandeja principal') sale[`${x.num}|${sinLado(x.otra)}`] ??= { tipo: 'puerta', donde: x.borne };
    }));
    return { sale, par, canal };
  }
  // largo = recorrido por las canaletas + margen (pelado, peinado) y, si sale de la bandeja, lo que necesita en LI/LD
  function largoCalc(f) {
    const l = f.l, r = P('redondeo') || 1, up = v => Math.ceil(v / r) * r;
    if (f.tipo === 'pendiente') {
      const x = E8L.par[claveE8(l.num, l.a, l.b)];
      if (x) {
        const ext = x.puerta ? P('extra_puerta') : P('margen_LI');
        return { mm: up(x.mm + ext), como: `canaleta de la ${x.donde} ${x.mm} + ${x.puerta ? 'puerta / placa' : 'margen'} ${ext}, redondeado a ${r}` };
      }
      return { mm: P('largo_pendiente'), como: 'pendiente LI↔LI (valor fijo)' };
    }
    if (!l.largo_mm) return { mm: P('largo_sin_ruta'), como: 'sin ruta en el topográfico: valor fijo', falta: true };
    const x = E8L.sale[`${l.num}|${sinLado(l.origen)}`];
    if (x && x.tipo === 'lateral')
      return { mm: up(l.largo_mm + x.mm + P('margen_LI')),
        como: `bandeja ${l.largo_mm} + canaleta de la ${x.donde} ${x.mm} + margen ${P('margen_LI')}, redondeado a ${r}` };
    if (x && x.tipo === 'puerta' && E8L.canal[l.destino])
      return { mm: up(l.largo_mm + E8L.canal[l.destino] + P('extra_puerta')),
        como: `bandeja ${l.largo_mm} + canaleta de ${l.destino} ${E8L.canal[l.destino]} + puerta / placa ${P('extra_puerta')} (${x.donde}), redondeado a ${r}` };
    const ext = l.destino === 'LI' ? P('extra_LI') : l.destino === 'LD' ? P('extra_LD') : 0;
    return { mm: up(l.largo_mm + P('margen_bandeja') + ext),
      como: `canaletas ${l.largo_mm} + margen ${P('margen_bandeja')}${ext ? ` + ${l.destino} ${ext}` : ''}, redondeado a ${r}` };
  }

  function csv(fs) {
    const fx = CFG.fijos || {};
    const lin = fs.map(f => {
      const c = new Array(NCOL).fill('');
      c[6] = f.largo; c[7] = 1; c[8] = coma(f.sec); c[9] = f.color; c[11] = f.l.num; c[19] = f.l.num;
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
    const faltan = fs.filter(f => !f.fuera && (f.calc.falta || !f.color || !f.sec)).length;
    M.querySelector('.wpc-cfg').innerHTML = [['margen_bandeja', 'Sobrante en bandeja (mm)'], ['margen_LI', 'Margen a LI (mm)'], ['extra_puerta', 'Puerta / placa (mm)'],
      ['extra_LI', 'A LI sin plano (mm)'], ['extra_LD', 'A LD sin plano (mm)'], ['redondeo', 'Redondeo'],
      ['largo_sin_ruta', 'Sin ruta'], ['largo_pendiente', 'Pendientes']].map(([k, t]) =>
      `<label class="small">${t} <input type="number" step="10" min="0" data-cfg="${k}" value="${P(k)}" style="width:70px"></label>`).join('') +
      `<label class="small"><input type="checkbox" data-cfg="pendientes" ${w.cfg.pendientes ? 'checked' : ''}> Pendientes LI↔LI</label>
       <label class="small"><input type="checkbox" data-cfg="otra" ${w.cfg.otra ? 'checked' : ''}> Otra estación</label>`;
    M.querySelector('.wpc-exp').innerHTML = `<span class="muted small">${fs.filter(f => !f.fuera).length} cables${faltan ? ` · <b style="color:#c0392b">${faltan} a revisar</b>` : ''}</span>
      <span class="grow"></span><button class="btn primary sm" data-exp>⭳ Exportar CSV</button>`;
    let g = null;
    M.querySelector('tbody').innerHTML = fs.map((f, i) => {
      const hdr = f.grupo !== g ? (g = f.grupo, `<tr class="wpc-g"><td colspan="8">${esc(f.grupo)}</td></tr>`) : '';
      const mal = f.calc.falta || !f.color || !f.sec;
      return hdr + `<tr data-k="${esc(f.k)}" class="${f.fuera ? 'wpc-fuera' : ''}">
        <td><input type="checkbox" data-a="usar" ${f.fuera ? '' : 'checked'} title="Incluir en el CSV"></td>
        <td class="small">${i + 1}</td>
        <td><b>${esc(f.l.num)}</b></td>
        <td><select data-a="color">${(f.color && !(CFG.codigos || []).includes(f.color) ? [f.color] : []).concat(CFG.codigos || []).concat(f.color ? [] : ['']).map(c => `<option ${c === f.color ? 'selected' : ''}>${c}</option>`).join('')}</select>
          <span class="muted small">${esc(f.l.color || '')}</span></td>
        <td>${esc(coma(f.sec))}</td>
        <td><input type="number" step="10" min="0" data-a="largo" value="${f.largo}" style="width:72px;${w.largo[f.k] != null ? 'font-weight:700' : ''}${mal ? ';background:#fde2e2' : ''}" title="${esc(f.calc.como)}${w.largo[f.k] != null ? ' · editado a mano (vacío = calculado ' + f.calc.mm + ')' : ''}"></td>
        <td class="small">${esc(f.l.origen ?? f.l.a)} → ${esc(f.l.destino ?? f.l.b)}</td>
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
        <div class="wpc-cfg"></div><div class="wpc-exp"></div>
        <div class="wpc-t"><table><thead><tr><th></th><th>#</th><th>Cable</th><th>Color</th><th>mm²</th><th>Largo</th><th>Origen → destino</th><th title="Recorrido por las canaletas">Canaleta</th></tr></thead><tbody></tbody></table></div></div>`;
      document.body.appendChild(M);
      M.addEventListener('click', e => { if (e.target === M || e.target.closest('[data-cerrar]')) M.hidden = true; else onEvt(e); });
      M.addEventListener('change', onEvt);
      document.addEventListener('keydown', e => { if (e.key === 'Escape' && !M.hidden) M.hidden = true; });
    }
    M.hidden = false; render();
  }
  return { abrir, csv: fs => csv(fs) };
})();
