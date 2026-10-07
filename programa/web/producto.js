'use strict';
/* Producto del tablero: el CÓDIGO DE PRODUCTO de SAP con su sufijo (75286-1), el plano funcional y el topográfico con su
   revisión. Lo detecta el servidor (programa/planocables/producto.py: rótulo, título del PDF, nombre del archivo y el
   catálogo programa/productos.json) y el taller lo confirma o lo corrige acá (✎): PUT /api/trabajo/<id>/producto guarda
   producto.json del trabajo (manda al regenerar) y suma el plano al catálogo.
   ASISTENTE: la primera vez que se abre el instructivo, si el producto no está confirmado y la detección no es segura o
   las fuentes no coinciden, el servidor deja ins.producto.preguntar y se pregunta una sola vez (como las salidas). */
const Prod = (() => {
  const FUENTE = { titulo_pdf: 'título del PDF', rotulo: 'rótulo', archivo: 'nombre del archivo', portada: 'portada',
    catalogo: 'catálogo de productos', confirmado: 'confirmado a mano', mismo_pdf: 'mismo PDF' };
  const CODIGO = /^\d{5}-\d{1,2}$/;
  const plano = (x, vacio) => x && x.numero ? `${x.numero}${x.revision != null && x.revision !== '' ? ' rev ' + x.revision : ''}` : vacio;
  const topoTxt = t => !t || !t.numero ? 'sin cargar' : t.mismo_pdf ? `hoja ${t.hoja ?? '?'} del mismo PDF` : plano(t);
  // estado del código: confirmado (a mano o por el catálogo), leído del plano o sugerido
  function estado(p) {
    if (p.confirmado) return { cls: 'ok', txt: p.fuente === 'confirmado' ? 'confirmado' : 'del catálogo',
      tit: p.fuente === 'confirmado' ? 'Código confirmado a mano en este trabajo' : 'Código del catálogo de productos (por el plano)' };
    if (!p.codigo) return { cls: 'warn', txt: 'sin código', tit: 'No se encontró el código de producto: cargalo con ✎' };
    return { cls: p.confianza === 'alta' ? '' : 'warn', txt: 'a confirmar',
      tit: `Código sacado del ${FUENTE[p.fuente] || p.fuente}${p.confianza === 'alta' ? ' (igual en varias hojas)' : ''}: confirmalo con ✎` };
  }
  // la línea «Producto: 75286-1 · mSafe2AC VISTA · funcional 75287 rev 6 · topográfico 75441 rev 6 ✎»
  function linea(p) {
    if (!p || !('funcional' in p)) return '';
    const e = estado(p), av = p.avisos || [];
    return `<b>Producto:</b> <span class="mono">${esc(p.codigo || '—')}</span>${p.nombre ? ' · ' + esc(p.nombre) : ''}
      · funcional ${esc(plano(p.funcional, '?'))} · topográfico ${esc(topoTxt(p.topografico))}
      <span class="pill ${e.cls}" title="${esc(e.tit)}">${esc(e.txt)}</span>
      ${av.length ? `<span class="prod-av" title="${esc(av.join('\n'))}">⚠ ${av.length} aviso${av.length > 1 ? 's' : ''}</span>` : ''}
      <button class="linkbtn" data-prod-editar title="Confirmar o corregir el código de producto">✎</button>`;
  }

  /* ---- diálogo: código y nombre, con sugerencias ---- */
  let M = null, act = null, cargando = false;     // act = {job, asistente, alGuardar, info}
  function modal() {
    if (M) return M;
    M = document.createElement('div'); M.className = 'prod-modal'; M.hidden = true;
    M.innerHTML = `<div class="prod-box" role="dialog" aria-label="Producto del tablero">
      <h2>Producto del tablero</h2>
      <p class="small muted prod-intro"></p>
      <div class="small prod-det"></div>
      <ul class="small prod-avisos"></ul>
      <label class="small prod-f">Código de producto <input id="prodCodigo" list="prodSug" placeholder="ej. 75286-1" autocomplete="off" spellcheck="false"></label>
      <datalist id="prodSug"></datalist>
      <label class="small prod-f">Nombre <input id="prodNombre" placeholder="ej. mSafe2AC VISTA" autocomplete="off" maxlength="80"></label>
      <div class="small prod-err" aria-live="polite"></div>
      <div class="prod-b"><button class="btn ghost sm" data-prod="cerrar"></button><button class="btn primary sm" data-prod="ok">✓ Confirmar</button></div></div>`;
    document.body.appendChild(M);
    M.addEventListener('click', e => {
      const b = e.target.closest('[data-prod]');
      if (e.target === M || (b && b.dataset.prod === 'cerrar')) return cerrar();
      if (b && b.dataset.prod === 'ok') confirmar();
    });
    M.querySelector('#prodCodigo').addEventListener('input', e => {
      const c = (act && act.info.catalogo || []).find(x => x.codigo === e.target.value.trim()), n = M.querySelector('#prodNombre');
      if (c && c.nombre && (!n.value || n.dataset.auto === '1')) { n.value = c.nombre; n.dataset.auto = '1'; }
    });
    M.querySelector('#prodNombre').addEventListener('input', e => { e.target.dataset.auto = '0'; });
    // las teclas no salen del diálogo (los atajos de la página: '/' busca, Escape cierra la WPC...)
    M.addEventListener('keydown', e => {
      e.stopPropagation();
      if (e.key === 'Escape') { e.preventDefault(); cerrar(); }
      else if (e.key === 'Enter' && e.target.tagName === 'INPUT') { e.preventDefault(); confirmar(); }
    });
    return M;
  }
  async function abrir(job, opts = {}) {
    if (abierto()) return;
    let info;
    cargando = true;
    try { info = await api(`/api/trabajo/${job}/producto`); } catch (e) { return toast('No se pudo leer el producto: ' + e.message, 4000); }
    finally { cargando = false; }
    const p = info.producto || {}, d = (p.detectado || {}).codigo || {};
    act = { job, info, asistente: !!opts.asistente, alGuardar: opts.alGuardar };
    modal();
    M.querySelector('.prod-intro').textContent = opts.asistente
      ? 'Confirmá el código de producto de SAP de este tablero (con su sufijo, como en G: y en la WPC). Se pregunta una sola vez; después se cambia con ✎ en la línea «Producto».'
      : 'El código de producto de SAP con su sufijo (como en G: y en la WPC). Queda guardado en este trabajo y en el catálogo de productos.';
    const fun = p.funcional || {};
    M.querySelector('.prod-det').innerHTML = [
      `Funcional: <b>${esc(plano(fun, 'sin número'))}</b>${fun.fuente ? ` <span class="muted">(${esc(FUENTE[fun.fuente] || fun.fuente)})</span>` : ''}`,
      `Topográfico: <b>${esc(topoTxt(p.topografico))}</b>`,
      d.rotulo ? `El rótulo dice <b class="mono">${esc(d.rotulo)}</b>${d.hojas ? ` (en ${d.hojas} hoja${d.hojas > 1 ? 's' : ''})` : ''}` : '',
      d.portada ? `La portada dice «Conjunto <b class="mono">${esc(d.portada)}</b>» (no siempre es el código del producto)` : '',
    ].filter(Boolean).join('<br>');
    M.querySelector('.prod-avisos').innerHTML = (p.avisos || []).map(a => `<li>⚠ ${esc(a)}</li>`).join('');
    M.querySelector('#prodSug').innerHTML = (info.sugerencias || []).map(s => `<option value="${esc(s.codigo)}">${esc([s.nombre, s.de].filter(Boolean).join(' · '))}</option>`).join('');
    const ci = M.querySelector('#prodCodigo'), ni = M.querySelector('#prodNombre');
    ci.value = p.codigo || ''; ni.value = p.nombre || ''; ni.dataset.auto = p.nombre ? '1' : '0';
    M.querySelector('.prod-err').textContent = '';
    M.querySelector('[data-prod=cerrar]').textContent = opts.asistente ? 'Después' : 'Cancelar';
    M.hidden = false; ci.focus(); ci.select();
  }
  function listo(prod) {
    const a = act; act = null; if (M) M.hidden = true;
    if (prod) mostrarEn('#resProd', prod);
    if (a && a.alGuardar && prod) a.alGuardar(prod);
  }
  async function cerrar() {
    if (!act) { if (M) M.hidden = true; return; }
    if (!act.asistente) return listo(null);
    // asistente cerrado sin confirmar: no se vuelve a preguntar
    const a = act;
    try { const r = await api(`/api/trabajo/${a.job}/producto`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ preguntado: true }) });
      listo(r.producto); toast('Queda sin confirmar. Para confirmarlo: ✎ en la línea «Producto»', 4500); }
    catch (e) { const p = { ...(a.info.producto || {}), preguntar: false }; listo(p); }
  }
  async function confirmar() {
    if (!act) return;
    const codigo = M.querySelector('#prodCodigo').value.trim(), nombre = M.querySelector('#prodNombre').value.trim();
    if (!CODIGO.test(codigo)) { M.querySelector('.prod-err').textContent = 'El código es el número de SAP con su sufijo, como 75286-1'; return; }
    try {
      const r = await api(`/api/trabajo/${act.job}/producto`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ codigo, nombre }) });
      listo(r.producto); toast(`Producto ${codigo} confirmado para este trabajo`, 3500);
    } catch (e) { M.querySelector('.prod-err').textContent = 'No se pudo guardar: ' + e.message; }
  }

  /* ---- la línea en una página: la del trabajo (#resProd), la del instructivo (#insProd) y la de la WPC (#wpcProd) ---- */
  function mostrarEn(sel, p) { const el = $(sel); if (el) { el.innerHTML = linea(p); el.hidden = !el.innerHTML; } }
  async function enTrabajo(job) {
    mostrarEn('#resProd', null);
    try { const r = await api(`/api/trabajo/${job}/producto`); if (S.job === job) mostrarEn('#resProd', r.producto); } catch (e) { }
  }
  // asistente: una sola vez (el servidor deja producto.preguntar)
  function asistente(job, p, alGuardar) { if (p && p.preguntar) abrir(job, { asistente: true, alGuardar }); }
  function abierto() { return cargando || !!(M && !M.hidden); }
  // ✎ en la página del trabajo y en la WPC (el del instructivo lo atiende instructivo.js): el producto guardado pasa
  // también al instructivo abierto (la WPC usa el mismo)
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-prod-editar]');
    if (!b || b.closest('#insProd')) return;
    const enIns = !b.closest('#resProd') && typeof Ins !== 'undefined' && Ins.D;
    const job = enIns ? Ins.job : S.job;
    if (!job) return;
    abrir(job, { alGuardar: p => {
      if (typeof Ins !== 'undefined' && Ins.D && Ins.job === job) { Ins.D.producto = p; Ins.mostrarProducto(); }
      mostrarEn('#wpcProd', p);
      if (typeof Wpc !== 'undefined') Wpc.refrescar();     // (los parámetros del producto y el nombre del archivo)
    } });
  });
  return { linea, abrir, asistente, enTrabajo, mostrarEn, abierto };
})();
