'use strict';
/* Lista de cables para el centro de cableado WPC: la PANTALLA. La lógica (filas en el orden del instructivo, largo por
   la regla del taller, reemplazos, fuera del arnés, giro de los termos, CSV y archivo .wpc) está en nucleo/wpc_core.js
   (WpcCore), el mismo archivo que usa la otra app; la configuración, en wpc.json (GET /api/config/wpc).
   Lo que se edita en la lista (largos, colores, giros, excluidos) y los parámetros de «Este trabajo» se guardan en D.wpc
   del instructivo, como siempre.
   Panel ⚙ PARÁMETROS, con tres niveles: «Todos los productos» (wpc.json) < «Producto <código>» (wpc.json → productos)
   < «Este trabajo» (D.wpc.cfg). Se arma solo desde wpc.json → parametros (un parámetro nuevo aparece sin tocar este
   archivo). Cada campo dice de qué nivel sale su valor y tiene «volver al de arriba». Lo de «Producto» y «Todos» queda
   como borrador (la lista ya lo muestra) hasta «Guardar»: confirmación y PUT /api/config/wpc (con respaldo).
   Archivos: «⭳ CSV» (la entrada documentada de la WPC) y «⭳ .wpc» (el archivo de la máquina), con el nombre
   '<código> - <plano> Rev <rev>' (sin código de producto, '<plano> - WPC'). */
const Wpc = (() => {
  const C = WpcCore;
  let D = null, guardar = null, BASE = null, VERSION = null, borrador = null;
  const par = { abierto: false, nivel: 'trabajo', error: '' };
  // configuración: GET /api/config/wpc (con su versión, para no pisar lo que otro guardó); si falla, el archivo estático
  async function leerConfig() {
    try {
      const r = await fetch('/api/config/wpc', { cache: 'no-cache' });
      if (!r.ok) throw new Error(r.statusText);
      const c = await r.json();
      VERSION = r.headers.get('X-Version');
      return c && typeof c === 'object' ? c : {};
    } catch (e) {
      VERSION = null;
      try { return await (await fetch('/static/wpc.json', { cache: 'no-cache' })).json(); } catch (e2) { return {}; }
    }
  }
  // al regenerar el instructivo puede quedar wpc = {} (o a medias): se completa lo que falte
  const W = () => {
    const w = D.wpc || (D.wpc = {});
    w.largo ??= {}; w.color ??= {}; w.excluir ??= []; w.incluir ??= []; w.cfg ??= {}; w.giro ??= {};
    return w;
  };
  const baseAct = () => borrador || BASE || {};        // con un borrador sin guardar, la lista ya lo muestra
  const CFG = () => C.config(baseAct(), { producto: D.producto, trabajo: W().cfg });
  const filas = () => C.filas(D, CFG());
  const nombrePlano = () => (S.res?.nombre || 'plano').replace(/\.pdf$/i, '');
  const coma = C.coma, secNum = C.secNum;
  function bajar(nombre, datos, tipo) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([datos], { type: tipo }));
    a.download = nombre; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  /* ---------------- panel ⚙ Parámetros ---------------- */
  const NIVEL_TXT = { trabajo: 'este trabajo', producto: 'producto', global: 'todos los productos', defecto: 'por defecto del programa' };
  const claveProducto = () => C.productoDe(baseAct(), D.producto).clave;
  const txtDe = de => (de === 'producto' ? `producto ${claveProducto() || ''}`.trim() : NIVEL_TXT[de] || de);
  // la configuración que se ve en cada pestaña (sin los niveles de abajo)
  function cfgDe(nivel) {
    if (nivel === 'trabajo') return CFG();
    return C.config(baseAct(), nivel === 'producto' ? { producto: D.producto } : {});
  }
  // los valores propios de un nivel (crear: con un borrador, para editarlos)
  function nivelObj(nivel, crear) {
    if (nivel === 'trabajo') return W().cfg;
    if (crear && !borrador) borrador = JSON.parse(JSON.stringify(BASE || {}));
    const b = baseAct();
    if (nivel === 'global') return b;
    const k = claveProducto();
    if (!k) return null;
    if (!crear) return (b.productos || {})[k] || null;
    if (!b.productos || typeof b.productos !== 'object' || Array.isArray(b.productos)) b.productos = {};
    return (b.productos[k] ??= {});
  }
  // lo que cambia el borrador respecto de wpc.json: todos los productos y / o qué productos
  function cambios() {
    if (!borrador) return { global: false, prods: [], hay: false };
    const a = BASE || {}, b = borrador, sin = o => JSON.stringify(Object.fromEntries(Object.entries(o).filter(([k]) => k !== 'productos')));
    const pa = a.productos || {}, pb = b.productos || {};
    const prods = [...new Set([...Object.keys(pa), ...Object.keys(pb)])].filter(k => JSON.stringify(pa[k]) !== JSON.stringify(pb[k]));
    const global = sin(a) !== sin(b);
    return { global, prods, hay: global || prods.length > 0 };
  }
  // defecto del programa (cuando ningún nivel lo tiene): solo para mostrarlo
  function defecto(p) {
    if (p.clave === 'marcador.modo') return C.MARCADOR.modo;
    if (p.clave === 'marcador.tabla') return C.MARCADOR.tabla;
    if (p.clave === 'archivo_wpc.UserFilter') return '-1';
    if (p.tipo === 'numero') return p.clave === 'redondeo' ? 1 : ({ 'fijos.pelado_origen': 10, 'fijos.proceso_origen': 1, 'fijos.proceso_destino': 1,
      'fijos.crimpado_origen': 8, 'fijos.dimension_origen': 10, 'fijos.crimpado_destino': 8 })[p.clave] ?? 0;
    if (p.tipo === 'si_no') return false;
    if (/^termos\.(mixto|sin_dato)$/.test(p.clave)) return '0|0';
    if (p.clave === 'termos.abajo_abajo') return '180|0';
    if (p.clave === 'termos.arriba_arriba') return '0|180';
    return p.tipo === 'lista' || p.tipo === 'reemplazos' || p.tipo === 'marcador' || p.tipo === 'largos' ? [] : p.tipo === 'colores' ? {} : '';
  }
  const valor = (p, cfg) => { const v = C.leer(cfg, p.clave); return v === undefined ? defecto(p) : v; };
  function opciones(p, cfg) {
    const ops = Array.isArray(p.opciones) ? p.opciones : p.opciones_de ? (C.leer(cfg, p.opciones_de) || []) : [];
    return ops.map(o => (o && typeof o === 'object' ? { v: o.valor, t: o.etiqueta ?? o.valor } : { v: o, t: o }));
  }
  // tablas: filas de texto para editar y vuelta al valor
  const numONull = s => (String(s ?? '').trim() === '' ? null : Number(String(s).replace(',', '.')));
  const TABLAS = {
    colores: { cols: ['Color del plano', 'Código WPC'], nueva: () => ['', ''],
      filas: v => Object.entries(v || {}), valor: fs => Object.fromEntries(fs.filter(f => String(f[0]).trim()).map(f => [String(f[0]).trim(), f[1]])) },
    reemplazos: { cols: ['Color', 'mm²', '→ color', '→ mm²', 'Motivo'], nueva: () => ['', '', '', '', ''],
      filas: v => (v || []).map(r => [r.de?.color ?? '', r.de?.secc ?? '', r.a?.color ?? '', r.a?.secc ?? '', r.motivo ?? '']),
      valor: fs => fs.map(f => Object.assign({ de: { color: String(f[0]).trim(), secc: numONull(f[1]) }, a: { color: String(f[2]).trim(), secc: numONull(f[3]) } },
        String(f[4]).trim() ? { motivo: String(f[4]).trim() } : {})) },
    marcador: { cols: ['Desde mm²', 'Hasta mm²', 'Marcador (columna 21)'], nueva: () => ['', '', ''],
      filas: v => (v || []).map(t => [t.desde ?? '', t.hasta ?? '', t.valor ?? '']),
      valor: fs => fs.map(f => ({ desde: numONull(f[0]), hasta: numONull(f[1]), valor: String(f[2]) })) },
    // largo total de cada cable de comunicación (se carga por producto)
    largos: { cols: ['Cable (número, o número|origen|destino para un tramo)', 'Largo total (mm)'], nueva: () => ['', ''],
      filas: v => (v || []).map(t => [t.cable ?? '', t.mm ?? '']),
      valor: fs => fs.map(f => ({ cable: String(f[0]).trim(), mm: numONull(f[1]) })) },
  };
  function tabla(p, v, cfg) {
    const T = TABLAS[p.tipo], fs = T.filas(v), cod = cfg.codigos || [];
    const celda = (f, i, c) => {
      const at = `data-par-tabla="${esc(p.clave)}" data-fila="${i}" data-col="${c}"`;
      if (p.tipo === 'colores' && c === 1) {
        const ops = cod.includes(f[1]) || !f[1] ? cod : [f[1], ...cod];
        return `<select ${at}>${(f[1] ? [] : ['']).concat(ops).map(o => `<option ${o === f[1] ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
      }
      const numero = (p.tipo === 'reemplazos' && (c === 1 || c === 3)) || (p.tipo === 'marcador' && c < 2) || (p.tipo === 'largos' && c === 1);
      const ancho = numero ? 'inputmode="decimal" style="width:60px"' : p.tipo === 'largos' ? 'list="wpcComL" style="width:260px"'
        : p.tipo === 'reemplazos' && c !== 4 ? 'list="wpcColoresL" style="width:96px"'
        : p.tipo === 'marcador' ? 'style="width:300px"' : p.tipo === 'reemplazos' ? 'style="width:240px"' : '';
      return `<input ${at} value="${esc(f[c])}" ${ancho}>`;
    };
    return `<table class="wpc-tabla"><thead><tr>${T.cols.map(t => `<th>${esc(t)}</th>`).join('')}<th></th></tr></thead><tbody>${
      fs.map((f, i) => `<tr>${T.cols.map((_, c) => `<td>${celda(f, i, c)}</td>`).join('')}<td><button class="linkbtn" data-par-menos="${esc(p.clave)}" data-fila="${i}" title="Borrar la fila">✕</button></td></tr>`).join('')
    }</tbody></table><button class="linkbtn small" data-par-mas="${esc(p.clave)}">+ fila</button>`;
  }
  function campo(p, cfg, propios) {
    const v = valor(p, cfg), de = cfg._de[p.clave] || 'defecto', propio = !!propios && C.hay(C.leer(propios, p.clave));
    const at = `data-par="${esc(p.clave)}"`;
    let ent;
    if (p.tipo === 'si_no') ent = `<input type="checkbox" ${at} ${v ? 'checked' : ''}>`;
    else if (p.tipo === 'numero') ent = `<input type="number" ${at} value="${esc(v)}" step="${esc(p.paso ?? 'any')}"${p.minimo != null ? ` min="${esc(p.minimo)}"` : ''} style="width:84px">`;
    else if (p.tipo === 'opcion') {
      const ops = opciones(p, cfg); if (!ops.some(o => o.v === v)) ops.push({ v, t: v });
      ent = `<select ${at}>${ops.map(o => `<option value="${esc(o.v)}" ${o.v === v ? 'selected' : ''}>${esc(o.t)}</option>`).join('')}</select>`;
    }
    else if (p.tipo === 'lista') ent = `<input ${at} value="${esc((Array.isArray(v) ? v : []).join(', '))}" class="mono" spellcheck="false" title="Separados por coma">`;
    else if (TABLAS[p.tipo]) ent = tabla(p, v, cfg);
    else ent = `<input ${at} value="${esc(v)}"${p.tipo === 'regex' ? ' class="mono" spellcheck="false"' : ''}>`;
    const arriba = par.nivel === 'trabajo' ? (claveProducto() ? 'el del producto (o el de todos)' : 'el de todos los productos') : 'el de todos los productos';
    return `<div class="wpc-campo${TABLAS[p.tipo] ? ' ancho tabla' : p.tipo === 'regex' || p.tipo === 'lista' ? ' ancho' : ''}">
      <label title="${esc(p.ayuda || '')}">${esc(p.etiqueta || p.clave)}${p.unidad ? ` <span class="muted">(${esc(p.unidad)})</span>` : ''}</label>
      <span class="wpc-ent">${ent}</span>
      <span class="pill wpc-de ${esc(de)}" title="El valor sale de: ${esc(txtDe(de))}">${esc(txtDe(de))}</span>
      ${par.nivel !== 'global' && propio ? `<button class="linkbtn small" data-par-volver="${esc(p.clave)}" title="Sacar el valor de ${esc(par.nivel === 'trabajo' ? 'este trabajo' : 'este producto')} y usar ${esc(arriba)}">↺ volver al de arriba</button>` : ''}</div>`;
  }
  function panel() {
    const b = baseAct(), ps = C.parametros(b), kp = claveProducto();
    if (par.nivel === 'producto' && !kp) par.nivel = 'trabajo';
    const cfg = cfgDe(par.nivel), propios = nivelObj(par.nivel, false), ch = cambios();
    const tabs = [['trabajo', 'Este trabajo'], ['producto', kp ? `Producto ${kp}` : 'Producto (sin código)'], ['global', 'Todos los productos']];
    const expl = {
      trabajo: 'Vale solo para este trabajo y se guarda con el instructivo.',
      producto: kp ? `Vale para todos los trabajos del producto ${kp}${C.productoDe(b, D.producto).por === 'documento' ? ' (cargado por el plano)' : ''}. Se guarda en wpc.json con «Guardar».`
        : 'Este trabajo no tiene código de producto: cargalo con ✎ en la línea «Producto».',
      global: 'Vale para todos los productos (salvo lo que cambie un producto o un trabajo). Se guarda en wpc.json con «Guardar».',
    }[par.nivel];
    const grupos = [];
    ps.forEach(p => { let g = grupos.find(x => x.n === (p.grupo || 'Otros')); if (!g) grupos.push(g = { n: p.grupo || 'Otros', ps: [] }); g.ps.push(p); });
    return `<div class="wpc-par-tabs">${tabs.map(([n, t]) => `<button data-par-tab="${n}" class="${n === par.nivel ? 'on' : ''}" ${n === 'producto' && !kp ? 'disabled' : ''}>${esc(t)}</button>`).join('')}
        <span class="grow"></span><button class="linkbtn small" data-par-abrir>Cerrar el panel</button></div>
      <div class="small muted wpc-par-expl">${esc(expl)}</div>
      ${par.error ? `<div class="small wpc-par-err" role="alert">⚠ ${esc(par.error)}</div>` : ''}
      ${ps.length ? '' : '<div class="small">wpc.json no trae la sección «parametros»: no hay nada para mostrar.</div>'}
      <datalist id="wpcColoresL">${Object.keys(cfg.colores || {}).map(c => `<option value="${esc(c)}">`).join('')}</datalist>
      <datalist id="wpcComL">${(fc => [...new Set(fc.map(f => f.l.num)), ...fc.map(f => f.k)])(C.filas(D, cfg).filter(f => /^comunicación/.test(f.motivo || '')))
        .map(n => `<option value="${esc(n)}">`).join('')}</datalist>
      ${grupos.map(g => `<fieldset><legend>${esc(g.n)}</legend>${g.ps.map(p => campo(p, cfg, propios)).join('')}</fieldset>`).join('')}
      ${ch.hay ? `<div class="wpc-par-pie"><span class="small"><b>Sin guardar:</b> ${esc([ch.global ? 'todos los productos' : '', ...ch.prods.map(k => 'producto ' + k)].filter(Boolean).join(' · '))}
          (la lista ya lo muestra)</span><span class="grow"></span>
          <button class="btn ghost sm" data-par-descartar>Descartar</button><button class="btn primary sm" data-par-guardar>✓ Guardar en wpc.json</button></div>` : ''}`;
  }
  // un valor nuevo en el nivel de la pestaña
  function ponerValor(clave, v) {
    par.error = '';
    if (par.nivel === 'trabajo') { C.poner(W().cfg, clave, v); guardar(); }
    else C.poner(nivelObj(par.nivel, true), clave, v);
    render();
  }
  function volverArriba(clave) {
    par.error = '';
    if (par.nivel === 'trabajo') { C.quitar(W().cfg, clave); guardar(); }
    else if (par.nivel === 'producto') {
      const o = nivelObj('producto', true), k = claveProducto();
      C.quitar(o, clave);
      if (!Object.keys(o).length) delete borrador.productos[k];
    }
    if (borrador && !cambios().hay) borrador = null;
    render();
  }
  function error(m) { par.error = m; render(); }
  function editarCampo(t) {
    const p = C.parametros(baseAct()).find(x => x.clave === t.dataset.par); if (!p) return;
    const s = String(t.value ?? '');
    if (p.tipo === 'si_no') return ponerValor(p.clave, t.checked);
    // vacío = «el de arriba» (en «Todos los productos» no hay nada arriba: un número no puede quedar vacío)
    if (s.trim() === '' && par.nivel !== 'global') return volverArriba(p.clave);
    if (p.tipo === 'numero') {
      if (s.trim() === '') return error(`«${p.etiqueta}» no puede quedar vacío en «Todos los productos»`);
      const n = Number(s.replace(',', '.'));
      if (!Number.isFinite(n)) return error(`«${p.etiqueta}»: «${s}» no es un número`);
      if (p.minimo != null && n < +p.minimo) return error(`«${p.etiqueta}»: tiene que ser ${p.minimo} o más`);
      return ponerValor(p.clave, n);
    }
    if (p.tipo === 'regex') {
      try { new RegExp(s, 'i'); } catch (e) { return error(`«${p.etiqueta}»: la expresión no es válida (${e.message}). No se guardó`); }
      return ponerValor(p.clave, s);
    }
    if (p.tipo === 'lista') return ponerValor(p.clave, s.split(/[,;\s]+/).map(x => x.trim()).filter(Boolean));
    return ponerValor(p.clave, s);
  }
  // tablas: se parte del valor que se ve en la pestaña (el de arriba, la primera vez) y se cambia entero en este nivel
  function editarTabla(clave, cambiar) {
    const p = C.parametros(baseAct()).find(x => x.clave === clave), T = p && TABLAS[p.tipo]; if (!T) return;
    const fs = T.filas(valor(p, cfgDe(par.nivel))).map(f => f.slice());
    cambiar(fs, T);
    ponerValor(clave, T.valor(fs));
  }
  async function guardarConfig() {
    const ch = cambios();
    if (!ch.hay) { borrador = null; return render(); }
    const qué = [ch.global ? 'Esto cambia todos los trabajos de todos los productos.' : '', ...ch.prods.map(k => `Esto cambia todos los trabajos del producto ${k}.`)];
    if (!confirm(qué.filter(Boolean).join('\n') + '\n\n¿Guardar los parámetros en wpc.json? (queda un respaldo del archivo anterior)')) return;
    try {
      const r = await fetch('/api/config/wpc', { method: 'PUT', headers: Object.assign({ 'Content-Type': 'application/json' }, VERSION ? { 'X-Version': VERSION } : {}), body: JSON.stringify(borrador) });
      let j = {}; try { j = await r.json(); } catch (e) { }
      if (!r.ok) throw new Error((j.error || r.statusText) + (j.errores ? ': ' + j.errores.slice(0, 4).join(' · ') : ''));
      BASE = j.config; VERSION = j.version || null; borrador = null; par.error = '';
      toast('Parámetros guardados en wpc.json (con respaldo)', 3500);
      render();
    } catch (e) { error('No se pudo guardar: ' + e.message); }
  }

  /* ---------------- la ventana ---------------- */
  function render() {
    const cfg = CFG(), fs = C.filas(D, cfg), w = W(), M = $('#wpcModal');
    if (typeof Prod !== 'undefined') Prod.mostrarEn('#wpcProd', D.producto);     // línea «Producto» (web/producto.js)
    const faltan = fs.filter(f => !f.fuera && (f.calc.falta || !f.color || !f.sec)).length;
    const nT = Object.values(cfg._de).filter(x => x === 'trabajo').length, nP = Object.values(cfg._de).filter(x => x === 'producto').length;
    const ch = cambios();
    M.querySelector('.wpc-cfg').innerHTML = `<label class="small"><input type="checkbox" data-cfg="pendientes" ${cfg.pendientes ? 'checked' : ''}> Pendientes LI↔LI</label>
       <label class="small"><input type="checkbox" data-cfg="otra" ${cfg.otra ? 'checked' : ''}> Otra estación</label>
       <span class="grow"></span>
       <span class="small muted">${nT ? `${nT} parámetro${nT > 1 ? 's' : ''} de este trabajo` : ''}${nT && nP ? ' · ' : ''}${nP ? `${nP} del producto ${esc(claveProducto() || '')}` : ''}${ch.hay ? ` · <b style="color:var(--warn)">parámetros sin guardar</b>` : ''}</span>
       <button class="btn sm${par.abierto ? ' on' : ''}" data-par-abrir title="Largos, fuera del arnés, termos, colores, reemplazos y el archivo .wpc: de este trabajo, del producto o de todos">⚙ Parámetros</button>`;
    const Pn = M.querySelector('.wpc-par');
    Pn.hidden = !par.abierto;
    if (par.abierto) Pn.innerHTML = panel();
    const nRg = fs.filter(f => !f.fuera && f.rg).length, nFuera = fs.filter(f => f.fuera && f.motivo && !w.excluir.includes(f.k)).length;
    const nGiro = fs.filter(f => !f.fuera && f.giro !== '0|0').length, nSin = fs.filter(f => !f.fuera && (!f.giroCalc.o || !f.giroCalc.d)).length;
    const nom = C.nombreArchivo(D.producto, '', nombrePlano());
    M.querySelector('.wpc-exp').innerHTML = `<span class="muted small">${fs.filter(f => !f.fuera).length} cables${faltan ? ` · <b style="color:#c0392b">${faltan} a revisar</b>` : ''}${nRg ? ` · <b>${nRg}</b> con otro color y sección por la regla de reemplazos (${esc(txtDe(cfg._de.reemplazos || 'global'))})` : ''}${nFuera ? ` · ${nFuera} fuera del arnés por regla (35 mm², comunicación, solenoides, campo)` : ''} · termos: ${nGiro} con giro${nSin ? ` (${nSin} sin el lado de una punta)` : ''} · la WPC solo corta (sin pelar ni crimpar)</span>
      <span class="grow"></span>
      <span class="small wpc-nom" title="Nombre del archivo y del proyecto (ProjectName del .wpc)"><span class="mono">${esc(nom)}</span>${D.producto && D.producto.codigo ? '' : ' <span class="muted">(sin código de producto)</span>'}</span>
      <button class="btn sm" data-exp="csv" title="El .csv para importar en el programa de la WPC">⭳ CSV</button>
      <button class="btn primary sm" data-exp="wpc" title="El archivo de la máquina: se abre directo en la WPC">⭳ .wpc</button>
      <span class="small wpc-aviso">No renombres el .wpc: la máquina lo abre por el nombre de adentro${ch.hay ? ' · ⚠ con parámetros sin guardar' : ''}</span>`;
    let g = null;
    const giros = (cfg.termos || {}).opciones || ['0|0', '180|0', '0|180', '180|180'], cods = cfg.codigos || [];
    M.querySelector('.wpc-t tbody').innerHTML = fs.map((f, i) => {      // (el panel también tiene tablas)
      const hdr = f.grupo !== g ? (g = f.grupo, `<tr class="wpc-g"><td colspan="9">${esc(f.grupo)}</td></tr>`) : '';
      const mal = f.calc.falta || !f.color || !f.sec;
      return hdr + `<tr data-k="${esc(f.k)}" class="${f.fuera ? 'wpc-fuera' : ''}">
        <td><input type="checkbox" data-a="usar" ${f.fuera ? '' : 'checked'} title="${esc(f.motivo ? 'Fuera del arnés: ' + f.motivo + ' (tildalo para incluirlo igual)' : 'Incluir en el CSV')}"></td>
        <td class="small">${i + 1}</td>
        <td><b>${esc(f.l.num)}</b></td>
        <td><select data-a="color">${(f.color && !cods.includes(f.color) ? [f.color] : []).concat(cods).concat(f.color ? [] : ['']).map(c => `<option ${c === f.color ? 'selected' : ''}>${c}</option>`).join('')}</select>
          ${f.rg ? `<span class="small wpc-rg" title="${esc(`Regla de reemplazo de la WPC (${txtDe(cfg._de.reemplazos || 'global')}): ${f.l.color} ${coma(secNum(f.l))} mm² se corta en ${f.rg.a.color} ${coma(f.rg.a.secc)} mm²${f.rg.motivo ? ' (' + f.rg.motivo + ')' : ''}. El instructivo no cambia`)}">${esc(f.l.color)} ${esc(coma(secNum(f.l)))} → <b>${esc(f.rg.a.color)} ${esc(coma(f.rg.a.secc))}</b></span>` : `<span class="muted small">${esc(f.l.color || '')}</span>`}</td>
        <td>${esc(coma(f.sec))}${f.rg ? ` <span class="muted small" title="Sección del plano">(era ${esc(coma(secNum(f.l)))})</span>` : ''}</td>
        <td><input type="number" step="10" min="0" data-a="largo" value="${f.largo}" style="width:72px;${w.largo[f.k] != null ? 'font-weight:700' : ''}${mal ? ';background:#fde2e2' : ''}" title="${esc(f.calc.como)}${w.largo[f.k] != null ? ' · editado a mano (vacío = calculado ' + f.calc.mm + ')' : ''}"></td>
        <td class="small">${esc(f.l.origen ?? f.l.a)} → ${esc(f.l.destino ?? f.l.b)}${f.motivo ? `<br><span class="wpc-mot">${esc(f.motivo)}</span>` : ''}</td>
        <td><select data-a="giro" class="wpc-giro${w.giro[f.k] ? ' manual' : ''}${!f.giroCalc.o || !f.giroCalc.d ? ' sin' : ''}" title="${esc('Giro de los termos (origen|destino): ' + f.giroCalc.como + (w.giro[f.k] ? ' · elegido a mano (calculado ' + f.giroCalc.v + ')' : ''))}">${giros.concat(giros.includes(f.giro) ? [] : [f.giro]).map(g => `<option ${g === f.giro ? 'selected' : ''}>${g}</option>`).join('')}</select></td>
        <td class="small muted">${f.l.largo_mm ? f.l.largo_mm : '—'}</td></tr>`;
    }).join('');
  }
  function exportar(tipo) {
    const cfg = CFG(), fs = C.filas(D, cfg).filter(f => !f.fuera), nom = C.nombreArchivo(D.producto, '', nombrePlano());
    if (tipo === 'csv') return bajar(nom + '.csv', C.csv(fs, cfg), 'text/csv;charset=utf-8');
    C.wpcZip(nom + '.wpc', C.wpcXml(fs, cfg, nom)).then(z => bajar(nom + '.wpc', z, 'application/octet-stream'))
      .catch(e => toast('No se pudo armar el .wpc: ' + e.message, 4500));
  }
  function onEvt(e) {
    const t = e.target, w = W(), clic = e.type === 'click', cambio = e.type === 'change';
    // panel de parámetros
    const pb = t.closest('[data-par-abrir],[data-par-tab],[data-par-volver],[data-par-mas],[data-par-menos],[data-par-guardar],[data-par-descartar]');
    if (pb && clic) {
      const d = pb.dataset;
      if ('parAbrir' in d) { par.abierto = !par.abierto; par.error = ''; }
      else if (d.parTab) { par.nivel = d.parTab; par.error = ''; }
      else if (d.parVolver) return volverArriba(d.parVolver);
      else if (d.parMas) return editarTabla(d.parMas, (fs, T) => fs.push(T.nueva()));
      else if (d.parMenos) return editarTabla(d.parMenos, fs => fs.splice(+d.fila, 1));
      else if ('parGuardar' in d) return guardarConfig();
      else if ('parDescartar' in d) { borrador = null; par.error = ''; }
      return render();
    }
    if (t.dataset.par) { if (cambio) editarCampo(t); return; }
    if (t.dataset.parTabla) { if (cambio) editarTabla(t.dataset.parTabla, fs => { fs[+t.dataset.fila][+t.dataset.col] = t.value; }); return; }
    // pendientes / otra estación (este trabajo)
    if (t.dataset.cfg) {
      if (!cambio) return;
      w.cfg[t.dataset.cfg] = t.type === 'checkbox' ? t.checked : t.value;
      guardar(); render(); return;
    }
    const exp = t.closest('[data-exp]');
    if (exp && clic) return exportar(exp.dataset.exp);
    const tr = t.closest('tr[data-k]'); if (!tr) return;
    const k = tr.dataset.k, a = (t.closest('[data-a]') || {}).dataset?.a;
    if (a === 'usar' && cambio) {
      w.incluir = w.incluir || [];
      w.excluir = w.excluir.filter(x => x !== k); w.incluir = w.incluir.filter(x => x !== k);
      (t.checked ? w.incluir : w.excluir).push(k);
    }
    else if (a === 'color' && cambio) { w.color[k] = t.value; }
    else if (a === 'giro' && cambio) { const f = filas().find(x => x.k === k); if (f && t.value === f.giroCalc.v) delete w.giro[k]; else w.giro[k] = t.value; }
    else if (a === 'largo' && cambio) { if (t.value === '') delete w.largo[k]; else w.largo[k] = Math.max(0, Math.round(+t.value)); }
    else return;
    guardar(); render();
  }
  function cerrar(M) {
    if (cambios().hay && !confirm('Hay parámetros de «Producto» o «Todos los productos» sin guardar. Quedan como borrador hasta que los guardes o descartes. ¿Cerrar igual?')) return;
    M.hidden = true;
  }

  async function abrir(d, fnGuardar) {
    D = d; guardar = fnGuardar;
    if (!borrador) BASE = await leerConfig();          // (otro pudo cambiar los parámetros)
    let M = $('#wpcModal');
    if (!M) {
      M = document.createElement('div'); M.id = 'wpcModal'; M.className = 'wpc-modal';
      M.innerHTML = `<div class="wpc-box" role="dialog" aria-label="Lista de cables para WPC">
        <div class="wpc-h"><h2>Lista de cables para WPC</h2><span class="muted small">En el orden del instructivo. Todo en un solo archivo. El largo editado a mano queda en negrita.</span>
          <span class="grow"></span><button class="btn ghost sm" data-cerrar>✕ Cerrar</button></div>
        <div class="small prod-linea" id="wpcProd" hidden></div>
        <div class="wpc-cfg"></div><div class="wpc-par" hidden></div><div class="wpc-exp"></div>
        <div class="wpc-t"><table><thead><tr><th></th><th>#</th><th>Cable</th><th>Color</th><th>mm²</th><th>Largo</th><th>Origen → destino</th><th title="Giro de los termos (señalizadores): origen|destino en grados. Una punta arriba y otra abajo: 0|0 · las dos abajo: 180|0 · las dos arriba: 0|180">Termos</th><th title="Recorrido por las canaletas">Canaleta</th></tr></thead><tbody></tbody></table></div></div>`;
      document.body.appendChild(M);
      M.addEventListener('click', e => { if (e.target === M || e.target.closest('[data-cerrar]')) cerrar(M); else onEvt(e); });
      M.addEventListener('change', onEvt);
      // lo que se escribe en los campos no dispara los atajos de la página ('/' busca...); Escape cierra la ventana
      M.addEventListener('keydown', e => { if (e.key !== 'Escape' && e.target.matches('input, select, textarea')) e.stopPropagation(); });
      document.addEventListener('keydown', e => { if (e.key === 'Escape' && !M.hidden && !(typeof Prod !== 'undefined' && Prod.abierto())) cerrar(M); });
    }
    M.hidden = false; render();
  }
  // el producto cambió (✎ en la línea «Producto»): la configuración y el nombre del archivo dependen del código
  function refrescar() { const M = $('#wpcModal'); if (D && M && !M.hidden) render(); }
  return { abrir, refrescar, csv: fs => C.csv(fs, CFG()), filas: () => filas() };
})();
