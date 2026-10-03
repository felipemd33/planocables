'use strict';
/* E8 · Gabinete: el cableado DENTRO del gabinete en 3D (como EPLAN): las placas con su vista del topográfico, la puerta
   que se abre, los aparatos y los cables de E8 de a uno (como "Cablear de a uno" de E6).
   Datos: GET /api/trabajo/<id>/e8 (gabinete.py). Marcas: POST /api/trabajo/<id>/e8/marcas -> instructivo.json['e8'].
   three.js se carga de cdnjs (import map de index.html); sin internet se usa la lista igual. */
const E8 = (() => {
  let D = null, job = null, poll = null, k = 0, abierto = false;
  let T = null;                 // { THREE, Orbit }
  let R = null;                 // escena: { scene, camera, renderer, controls, puerta, ... }
  let todos = true, puertaAbierta = true, ubicando = null, anim = null, raf = 0;
  const el = id => document.getElementById(id);
  const secTxt = c => fmtSec(c.secc || ((c.cable || '').match(/(\d+(?:[.,]\d+)?)MM/i) || [])[1] || '');
  const ZONA_TXT = { bandeja: 'bandeja (E6)', fondo: 'fondo del gabinete', 'lateral izq': 'lateral izquierdo', 'lateral der': 'lateral derecho',
    puerta: 'puerta', otro: 'zona hidráulica (sin ubicar)', 'sin ubicar': 'sin ubicar' };
  const COL_DESDE = 0xff6a00, COL_HASTA = 0x1565c0;

  /* ---------------- three.js (cdnjs) ---------------- */
  let threeP = null;
  function cargarThree() {
    if (!threeP) threeP = (async () => {
      const THREE = await import('three');
      let Orbit = null;
      try { Orbit = (await import('three/addons/controls/OrbitControls.js')).OrbitControls; } catch (e) { Orbit = null; }
      return { THREE, Orbit };
    })();
    return threeP;
  }

  /* ---------------- abrir / cerrar ---------------- */
  let entroConPush = false;      // E8 se abrio con el boton (pushState): al cerrar se vuelve con history.back()
  async function open(_ev, n, cerrada) {
    if (!S.job) return;
    if (job !== S.job) { D = null; job = S.job; k = null; }
    if (n) k = n - 1;
    if (cerrada) puertaAbierta = false;
    abierto = true;
    // la direccion lleva /e8: al recargar la pagina se vuelve a abrir E8 (#/trabajo/<id>/e8)
    // (con pushState el boton Atras del navegador vuelve a la pagina del trabajo)
    if (!/\/e8(\/|$)/.test(location.hash)) { history.pushState(null, '', `#/trabajo/${job}/e8`); entroConPush = true; }
    el('e8Viewer').hidden = false; document.body.style.overflow = 'hidden';
    try { setSide(localStorage.getItem('listadoE8') !== '0', false); } catch (e) { setSide(true, false); }
    el('e8Avisos').hidden = true;
    mensaje('Cargando el gabinete…', 0.02);
    // (sin internet el import falla y queda guardado en el modulo: threeP = null para que se pueda reintentar)
    const tp = cargarThree().then(t => { T = t; }).catch(e => { T = { error: e }; threeP = null; });
    await cargar();
    await tp;
    if (!abierto || !D) return;
    if (T.error) {
      mensaje(`<b>No se pudo cargar el visor 3D</b> (three.js se baja de internet: cdnjs.cloudflare.com).<br>
        La lista de cables de E8 se puede usar igual. Con internet, recargá la página (F5).`, null, true);
      el('e8Stage').classList.add('sin3d');
    } else {
      el('e8Stage').classList.remove('sin3d');
      try { construir(); } catch (e) { console.error(e); mensaje('No se pudo armar la vista 3D: ' + esc(e.message), null, true); }
    }
    ir(k ?? primero(), false);
    if (cerrada && R) vistaGeneral(false);     // (#…/e8/<n>/cerrada: el gabinete cerrado, de afuera)
  }
  function close() {
    if (el('e8Viewer').hidden) return;
    abierto = false; clearTimeout(poll); cancelAnimationFrame(raf); raf = 0; setUbicar(null);
    el('e8Viewer').hidden = true; document.body.style.overflow = '';
    if (/\/e8(\/|$)/.test(location.hash) && job) {
      if (entroConPush) history.back(); else history.replaceState(null, '', `#/trabajo/${job}`);
    }
    entroConPush = false;
  }
  // #/trabajo/<id>/e8[/<n>]: abrir E8 (en el cable n) cuando la pagina del trabajo ya esta cargada
  function porDireccion() {
    const m = location.hash.match(/^#\/trabajo\/([0-9a-f]{12})\/e8(?:\/(\d+))?(\/cerrada)?/);
    if (!m || abierto) return;
    let n = 0;
    const t = setInterval(() => {
      if (++n > 300 || !location.hash.includes(m[1])) return clearInterval(t);
      if (S.job === m[1] && S.res && !el('vResultado').hidden) { clearInterval(t); open(null, m[2] ? +m[2] : null, !!m[3]); }
    }, 200);
  }
  function mensaje(html, prog, quieto) {
    const m = el('e8Msg');
    if (html == null) { m.hidden = true; return; }
    m.hidden = false;
    m.innerHTML = `<div class="e8-msg-c">${quieto ? '' : '<div class="spinner"></div>'}<div>${html}</div></div>
      ${prog != null ? `<div class="bar"><i style="width:${Math.max(3, prog * 100)}%"></i></div>` : ''}`;
  }

  async function cargar(releer) {
    clearTimeout(poll);
    const j = job;
    for (;;) {
      let r;
      try {
        const resp = await fetch(`/api/trabajo/${j}/e8${releer ? '?releer=1' : ''}`, { cache: 'no-store' });
        r = await resp.json();
      } catch (e) { r = { estado: 'error', error: e.message }; }
      releer = false;
      if (!abierto || job !== j) return;
      if (r.estado === 'listo') { D = prep(r); mensaje(null); avisos(); renderList(); return; }
      if (r.estado === 'sin_instructivo') {
        mensaje(`${esc(r.error)}<div class="e8-msg-b"><button class="btn primary sm" data-a="e6">Ir a E6 · Bandeja</button></div>`, null, true);
        D = null; el('e8List').innerHTML = ''; return;
      }
      if (r.estado === 'error') {
        mensaje(`No se pudo leer el gabinete: ${esc(r.error || '')}<div class="e8-msg-b"><button class="btn sm" data-a="releer">↻ Volver a leer</button></div>`, null, true);
        return;
      }
      mensaje(esc(r.mensaje || 'Leyendo el gabinete…') + '<div class="muted small">La primera vez lee las vistas del topográfico (menos de un minuto); después queda guardado.</div>', r.progreso || 0.05);
      await new Promise(res => { poll = setTimeout(res, 900); });
      if (!abierto || job !== j) return;
    }
  }
  function prep(r) {
    r.grupoDe = Object.fromEntries(r.grupos.map(g => [g.id, g]));
    r.vistas = Object.fromEntries(r.modelo.vistas.map(v => [v.id, v]));
    return r;
  }
  const primero = () => { try { const s = localStorage.getItem('e8:' + job); const i = buscarId(s); if (i >= 0) return i; } catch (e) { }
    const i = D.cables.findIndex(c => !c.hecho); return i >= 0 ? i : 0; };
  // cable por su clave (estable: 'num|origen de E6' o 'num|par ordenado de puntas'); una clave de antes
  // ('num|desde|hasta', guardada en este navegador) se busca por el numero y sus puntas, en cualquier orden
  function buscarId(id) {
    if (!D || !id) return -1;
    const i = D.cables.findIndex(c => c.id === id);
    if (i >= 0) return i;
    const [n, a, b] = id.split('|');
    const ts = c => [c.desde.texto, c.hasta.texto];
    return D.cables.findIndex(c => c.num === n && ts(c).includes(a) && (b === undefined || ts(c).includes(b)));
  }
  function avisos() {
    const av = D.avisos || [];
    const box = el('e8Avisos');
    box.hidden = !av.length;
    const regen = av.some(a => /Regenerar/.test(a));
    box.innerHTML = `<details${regen ? ' open' : ''}><summary>${av.length} aviso${av.length > 1 ? 's' : ''} del gabinete${regen ? ' · <b>falta la otra punta de los cables a LI</b>' : ''}</summary>
      <ul>${av.map(a => `<li>${esc(a)}</li>`).join('')}</ul>
      ${(D.modelo.supuestos || []).length ? `<div class="muted">Supuestos: ${(D.modelo.supuestos || []).map(esc).join(' · ')}</div>` : ''}
      <div class="e8-av-b">${regen ? '<button class="btn primary sm" data-a="e6">Ir a E6 y tocar ↻ Regenerar</button>' : ''}
        <button class="btn ghost sm" data-a="releer" title="Volver a leer las vistas del gabinete en el topográfico">↻ Releer el gabinete</button></div></details>`;
  }

  /* ---------------- lista ---------------- */
  function renderList() {
    if (!D) return;
    const q = norm(el('e8Q').value.trim());
    let html = '', lastG = null;
    D.cables.forEach((c, i) => {
      if (q && !norm(`${c.num} ${c.desde.texto} ${c.hasta.texto} ${c.color} ${c.secc} ${c.cable}`).includes(q)) return;
      if (c.grupo !== lastG) { const g = D.grupoDe[c.grupo]; html += `<div class="cv-gh" title="${esc(g.por_que)}">${esc(g.titulo)} (${g.n})</div>`; lastG = c.grupo; }
      const warn = c.avisos.length ? ' rev' : '';
      html += `<div class="vs-it cv-it e8-it${c.hecho ? ' seen' : ''}${warn}" data-i="${i}" role="option" title="${esc(lineaTxt(c))}">
        <input type="checkbox" data-ok ${c.hecho ? 'checked' : ''} aria-label="Cable ${esc(c.num)} cableado">
        <span class="n">${esc(c.num)}</span>${swatch(c.color)}<span class="sec">${esc(secTxt(c))}</span>
        <span class="od mono">${esc(c.desde.texto)} → ${esc(c.hasta.texto)}</span></div>`;
    });
    el('e8List').innerHTML = html || '<div class="vs-empty muted small">Ningún cable coincide.</div>';
    marcarLista();
  }
  function marcarLista() {
    if (!D) return;
    let cur = null;
    for (const b of el('e8List').querySelectorAll('.e8-it')) {
      const c = D.cables[+b.dataset.i]; if (!c) continue;
      b.classList.toggle('seen', !!c.hecho); b.querySelector('[data-ok]').checked = !!c.hecho;
      const on = +b.dataset.i === k; b.classList.toggle('on', on); b.setAttribute('aria-selected', on);
      if (on) cur = b;
    }
    const h = D.cables.filter(c => c.hecho).length, n = D.cables.length;
    el('e8Cnt').textContent = `${h} de ${n} cableados`;
    el('e8Bar').style.width = (n ? h / n * 100 : 0) + '%';
    if (cur && !el('e8Side').hidden) cur.scrollIntoView({ block: 'nearest' });
  }
  const lineaTxt = c => `${c.num}: ${c.cable || ''} ${c.desde.texto} → ${c.hasta.texto}`.replace(/\s+/g, ' ');
  function setSide(on, redraw = true) {
    el('e8Side').hidden = !on; el('e8SideBtn').classList.toggle('on', on); el('e8SideBtn').setAttribute('aria-pressed', on);
    try { localStorage.setItem('listadoE8', on ? '1' : '0'); } catch (e) { }
    if (redraw) setTimeout(tam, 0);
  }

  /* ---------------- cable actual ---------------- */
  function ir(i, animar = true) {
    if (!D || !D.cables.length) { el('e8Pos').textContent = '0 / 0'; return; }
    k = Math.max(0, Math.min(D.cables.length - 1, i));
    const c = D.cables[k];
    try { localStorage.setItem('e8:' + job, c.id); } catch (e) { }
    el('e8Tit').innerHTML = `<b>${esc(c.num)}</b>: ${esc(c.cable || '')} ${swatch(c.color)} <span class="secc">${esc(secTxt(c))}</span>`;
    el('e8Grp').textContent = D.grupoDe[c.grupo]?.titulo || '';
    el('e8Desde').textContent = c.desde.texto; el('e8Hasta').textContent = c.hasta.texto;
    el('e8Pos').textContent = `${k + 1} / ${D.cables.length}`;
    el('e8Ok').checked = !!c.hecho;
    info(c);
    marcarLista();
    if (R) { resaltar(); if (c.tramos.some(t => t.tipo === 'puerta') || [c.desde.zona, c.hasta.zona].includes('puerta')) puerta(true, false); encuadrar(animar); }
  }
  function info(c) {
    const punta = (p, cls, lbl) => `<div class="e8-p ${cls}"><b>${lbl}</b> <span class="mono">${esc(p.texto)}</span>
      <span class="muted">· ${esc(ZONA_TXT[p.zona] || p.zona)}${p.fuente ? ' · ' + esc(p.fuente) : ''}</span>
      ${p.a_confirmar ? '<span class="pill conf">a confirmar</span>' : ''}${p.zona === 'sin ubicar' ? '<span class="pill warn">sin ubicar</span>' : ''}</div>`;
    const de = { linea: 'línea de E6 (la punta LI)', pendiente: 'pendiente LI ↔ LI', otra: `otra estación (${c.estacion || 'E8'})` }[c.de] || c.de;
    el('e8Info').innerHTML = `${punta(c.desde, 'd', 'Desde')}${punta(c.hasta, 'h', 'Hasta')}
      <div class="muted">${esc(de)}${c.e6_hecho ? ' · <span class="e8-ok">la punta de la bandeja ya está cableada en E6</span>' : ''}${c.agregado ? ' · ' + esc(c.agregado) : ''}</div>
      ${c.avisos.map(a => `<div class="e8-warn">⚠ ${esc(a)}</div>`).join('')}<div class="e8-save" id="e8Save"></div>`;
  }
  async function marcar(i, v, avanzar) {
    const c = D.cables[i]; if (!c) return;
    c.hecho = v === undefined ? !c.hecho : !!v;
    if (i === k) el('e8Ok').checked = c.hecho;
    marcarLista(); if (R) resaltar();
    const s = el('e8Save'); if (s) s.textContent = 'Guardando…';
    try {
      await api(`/api/trabajo/${job}/e8/marcas`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ hechos: { [c.id]: c.hecho } }) });
      const s2 = el('e8Save'); if (s2) s2.textContent = 'Guardado';
    } catch (e) { toast('No se pudo guardar: ' + e.message, 5000); const s2 = el('e8Save'); if (s2) s2.textContent = 'No se pudo guardar'; }
    if (avanzar && c.hecho && i < D.cables.length - 1) ir(i + 1);
  }

  /* ---------------- escena 3D ---------------- */
  const a3d = (v, X, Y, h = 0) => [0, 1, 2].map(i => v.o_mm[i] + v.esc * ((X - v.o_pt[0]) * v.ex[i] + (Y - v.o_pt[1]) * v.ey[i]) + h * v.normal[i]);
  function construir() {
    const { THREE } = T; const M = D.modelo, G = M.gabinete;
    if (!R) {
      const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
      renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
      el('e8Stage').prepend(renderer.domElement); renderer.domElement.className = 'e8-canvas';
      const camera = new THREE.PerspectiveCamera(38, 1, 5, 40000);
      const controls = T.Orbit ? new T.Orbit(camera, renderer.domElement) : miniOrbit(camera, renderer.domElement);
      controls.enableDamping = true; controls.dampingFactor = 0.12; controls.screenSpacePanning = true;
      if (controls.addEventListener) controls.addEventListener('change', () => pedirRender());   // girar / mover / zoom
      R = { renderer, camera, controls };
      renderer.domElement.addEventListener('pointerdown', e => { R.down = [e.clientX, e.clientY]; });
      renderer.domElement.addEventListener('pointerup', clic);
      renderer.domElement.addEventListener('contextmenu', e => e.preventDefault());
      new ResizeObserver(tam).observe(el('e8Stage'));
    }
    if (R.scene) limpiar(R.scene);
    const scene = new THREE.Scene(); scene.background = new THREE.Color(0xe8ecf1);
    R.scene = scene; R.cab = []; R.vistas = []; R.marcas = null;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8892a0, 1.1));
    const dl = new THREE.DirectionalLight(0xffffff, 1.1); dl.position.set(G.ancho * 1.5, G.alto * 2.5, G.prof * 5); scene.add(dl);
    const t = 1.5, W = G.ancho, H = G.alto, P = G.prof;
    // cuerpo: paredes translucidas y aristas
    const matPared = new THREE.MeshLambertMaterial({ color: 0xc3ccd6, transparent: true, opacity: 0.16, side: THREE.DoubleSide, depthWrite: false });
    const caja = (w, h, d, x, y, z, mat) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); m.position.set(x, y, z); scene.add(m); return m; };
    caja(W, H, t, W / 2, H / 2, t / 2, matPared);
    caja(t, H, P, t / 2, H / 2, P / 2, matPared); caja(t, H, P, W - t / 2, H / 2, P / 2, matPared);
    caja(W, t, P, W / 2, t / 2, P / 2, matPared); caja(W, t, P, W / 2, H - t / 2, P / 2, matPared);
    const aristas = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(W, H, P)), new THREE.LineBasicMaterial({ color: 0x46505c }));
    aristas.position.set(W / 2, H / 2, P / 2); scene.add(aristas);
    // piso de referencia
    const grid = new THREE.GridHelper(Math.max(W, P) * 3, 24, 0xb8c0ca, 0xd3d9e0); grid.position.set(W / 2, -1, P / 2); scene.add(grid);
    // puerta: grupo que gira en el eje de las bisagras
    const piv = new THREE.Group(); piv.position.set(G.eje.x, 0, G.eje.z); scene.add(piv); R.puerta = piv;
    const local = p => new THREE.Vector3(p[0] - G.eje.x, p[1], p[2] - G.eje.z);
    const pz = G.puerta || 30;
    const matPuerta = new THREE.MeshLambertMaterial({ color: 0xb9c3ce, transparent: true, opacity: 0.22, side: THREE.DoubleSide, depthWrite: false });
    const pg = new THREE.Mesh(new THREE.BoxGeometry(W - 6, H - 6, pz), matPuerta);
    pg.position.copy(local([W / 2, H / 2, P + pz / 2])); piv.add(pg);
    const pa = new THREE.LineSegments(new THREE.EdgesGeometry(pg.geometry), new THREE.LineBasicMaterial({ color: 0x46505c }));
    pa.position.copy(pg.position); piv.add(pa);
    for (const yb of [0.16 * H, 0.84 * H]) {     // bisagras
      const b = new THREE.Mesh(new THREE.CylinderGeometry(7, 7, 60, 12), new THREE.MeshLambertMaterial({ color: 0x59626e }));
      b.position.set(G.eje.x, yb, G.eje.z); scene.add(b);
    }
    // vistas (placas con su dibujo del topografico)
    const loader = new THREE.TextureLoader();
    for (const v of M.vistas) {
      const enP = !!v.en_puerta;
      const b = v.box, h = v.id === 'fondo' ? 0.6 : 0.4;
      const pts = [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]].map(([X, Y]) => a3d(v, X, Y, h));
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(pts.flatMap(p => enP ? local(p).toArray() : p), 3));
      g.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 1, 1, 0, 1], 2));
      g.setIndex([0, 1, 2, 0, 2, 3]); g.computeVertexNormals();
      const mat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide, transparent: v.id === 'pared_fondo', opacity: v.id === 'pared_fondo' ? 0.85 : 1 });
      if (v.imagen) {
        const tex = loader.load(`/api/trabajo/${job}/e8/vista/${v.id}.png?v=${encodeURIComponent(D.generado || '')}`, () => pedirRender());
        tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = R.renderer.capabilities.getMaxAnisotropy();
        mat.map = tex;
      } else { mat.color.set(0xf4f6f8); }
      const m = new THREE.Mesh(g, mat); m.userData.vista = v; m.renderOrder = v.id === 'pared_fondo' ? -2 : -1;
      (enP ? piv : scene).add(m); R.vistas.push(m);
      if (v.id === 'fondo' || v.zona.startsWith('lateral')) {   // borde de la placa
        const lp = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts.map(p => new THREE.Vector3(...p))), new THREE.LineBasicMaterial({ color: 0x6b7480 }));
        scene.add(lp);
      }
    }
    // canaletas
    const matCan = new THREE.MeshLambertMaterial({ color: 0x9aa3ae, transparent: true, opacity: 0.45, depthWrite: false });
    const matCanEx = new THREE.MeshLambertMaterial({ color: 0x5a72e8, transparent: true, opacity: 0.45, depthWrite: false });
    for (const c of M.canaletas || []) {
      const s = [0, 1, 2].map(i => Math.max(1, c.max[i] - c.min[i])), ctr = [0, 1, 2].map(i => (c.max[i] + c.min[i]) / 2);
      const m = new THREE.Mesh(new THREE.BoxGeometry(...s), c.ex ? matCanEx : matCan);
      if (c.en_puerta) { m.position.copy(local(ctr)); piv.add(m); } else { m.position.set(...ctr); scene.add(m); }
    }
    // aparatos: etiquetas
    for (const a of D.aparatos || []) {
      const fuera = a.zona === 'sin ubicar', otro = a.zona === 'otro';
      const txt = !fuera ? (otro ? `${a.tag} · zona hidráulica (sin ubicar)` : a.tag) : a.tag === 'LI' || a.tag === 'LD' ? `${a.tag} · sin la otra punta`
        : a.tag.startsWith('?') ? 'aparato no leído (?)' : `${a.tag} · sin ubicar 📍`;
      const sp = etiqueta(txt, { fondo: fuera ? '#ffe3e0' : otro ? '#fff1d6' : a.a_confirmar ? '#fff6c8' : '#fffbe6',
        borde: fuera ? '#c62828' : otro ? '#b26a00' : '#7a6400', alto: a.zona === 'bandeja' ? 14 : 17 });
      const p = a.p;
      if (a.en_puerta) { sp.position.copy(local(p)); piv.add(sp); } else { sp.position.set(...p); scene.add(sp); }
      if (a.caja && a.vista && D.vistas[a.vista]) {      // recuadro del aparato (ubicado por descarte)
        const v = D.vistas[a.vista], b = a.caja;
        const pts = [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]].map(([X, Y]) => a3d(v, X, Y, 6));
        const lp = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts.map(q => a.en_puerta ? local(q) : new THREE.Vector3(...q))),
          new THREE.LineDashedMaterial({ color: 0xb26a00, dashSize: 12, gapSize: 6 }));
        lp.computeLineDistances(); (a.en_puerta ? piv : scene).add(lp);
      }
    }
    // cables
    D.cables.forEach((c, i) => {
      const meshes = [];
      for (const tr of c.tramos) {
        if (tr.pts.length < 2) continue;
        const enP = tr.tipo === 'puerta';
        const vs = tr.pts.map(p => enP ? local(p) : new THREE.Vector3(...p));
        const grupo = tubo(vs, c, tr.tipo);
        grupo.userData = { i, tipo: tr.tipo };
        (enP ? piv : scene).add(grupo); meshes.push(grupo);
      }
      R.cab.push(meshes);
    });
    R.local = local;
    puerta(puertaAbierta, false);
    vistaGeneral(false);
    tam(); pedirRender();
  }
  // tubo del cable: polilinea con las esquinas redondeadas; blanco y amarillo con borde oscuro; verde-amarillo a rayas
  const TEX = {};
  function tubo(vs, c, tipo) {
    const { THREE } = T;
    const path = new THREE.CurvePath();
    const r = (s => 2.0 + 0.85 * Math.sqrt(s || 0.75))(parseFloat(String(c.secc || '').replace(',', '.')));
    let prev = vs[0];
    for (let j = 1; j < vs.length; j++) {
      const a = vs[j - 1], b = vs[j], n = vs[j + 1];
      if (!n) { path.add(new THREE.LineCurve3(prev, b)); break; }
      const f = Math.min(18, a.distanceTo(b) / 2.5, b.distanceTo(n) / 2.5);
      const p1 = b.clone().add(a.clone().sub(b).setLength(f)), p2 = b.clone().add(n.clone().sub(b).setLength(f));
      if (prev.distanceTo(p1) > 0.01) path.add(new THREE.LineCurve3(prev, p1));
      path.add(new THREE.QuadraticBezierCurve3(p1, b, p2));
      prev = p2;
    }
    const L = path.getLength(); const seg = Math.min(900, Math.max(12, Math.round(L / 6)));
    const g = new THREE.Group();
    const k0 = norm(c.color || '');
    let col = (k0.includes('verde') && k0.includes('amarillo')) ? '#2e9a44' : (LINE[k0] || (k0 ? '#ff00c8' : '#a3a9b1'));
    const mat = new THREE.MeshLambertMaterial({ color: col, transparent: true, opacity: 1 });
    if (k0.includes('verde') && k0.includes('amarillo')) {
      if (!TEX.va) {
        const cv = document.createElement('canvas'); cv.width = 64; cv.height = 8; const x = cv.getContext('2d');
        x.fillStyle = '#2e9a44'; x.fillRect(0, 0, 64, 8); x.fillStyle = '#f2c200'; x.fillRect(0, 0, 32, 8);
        TEX.va = new THREE.CanvasTexture(cv); TEX.va.wrapS = THREE.RepeatWrapping; TEX.va.colorSpace = THREE.SRGBColorSpace;
      }
      const tx = TEX.va.clone(); tx.repeat.set(Math.max(1, L / 30), 1); tx.needsUpdate = true;
      mat.map = tx; mat.color.set(0xffffff);
    }
    const tg = new THREE.TubeGeometry(path, seg, r, 8, false);
    const m = new THREE.Mesh(tg, mat); m.userData.cable = true; g.add(m);
    if (['blanco', 'amarillo'].includes(k0) || !k0) {      // borde oscuro
      const b = new THREE.Mesh(new THREE.TubeGeometry(path, seg, r + 0.9, 8, false), new THREE.MeshBasicMaterial({ color: 0x333333, side: THREE.BackSide, transparent: true }));
      g.add(b);
    }
    const halo = new THREE.Mesh(new THREE.TubeGeometry(path, seg, r + 5, 8, false),
      new THREE.MeshBasicMaterial({ color: 0xff8c00, transparent: true, opacity: 0.28, depthWrite: false }));
    halo.visible = false; halo.userData.halo = true; g.add(halo);
    g.userData.mats = g.children.map(x => x.material);
    return g;
  }
  function etiqueta(texto, o = {}) {
    const { THREE } = T;
    const fs = 44, cv = document.createElement('canvas'), x = cv.getContext('2d');
    x.font = `700 ${fs}px Consolas, "Cascadia Mono", monospace`;
    const w = Math.ceil(x.measureText(texto).width) + 26;
    cv.width = w; cv.height = fs + 20;
    x.font = `700 ${fs}px Consolas, "Cascadia Mono", monospace`;
    x.fillStyle = o.fondo || '#fffbe6'; x.strokeStyle = o.borde || '#7a6400'; x.lineWidth = 4;
    const rr = 10; x.beginPath(); x.roundRect ? x.roundRect(2, 2, w - 4, cv.height - 4, rr) : x.rect(2, 2, w - 4, cv.height - 4); x.fill(); x.stroke();
    x.fillStyle = o.color || '#111'; x.textBaseline = 'middle'; x.fillText(texto, 13, cv.height / 2 + 2);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    // tamaño fijo en la pantalla (o.alto en px, para una vista de ~820 px de alto): se leen igual de cerca y de lejos
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true, sizeAttenuation: false }));
    const alto = (o.alto || 20) / 820 * 2 * Math.tan(19 * Math.PI / 180);
    sp.scale.set(alto * cv.width / cv.height, alto, 1); sp.renderOrder = 20;
    // (las puntas del cable actual van al costado: o.lado = 'izq' | 'der'; las etiquetas de los aparatos, arriba)
    if (o.lado) sp.center.set(o.lado === 'izq' ? 1.12 : -0.12, 0.5); else sp.center.set(0.5, -0.15);
    return sp;
  }
  function limpiar(obj) {
    obj.traverse(o => {
      if (o.geometry) o.geometry.dispose();
      const ms = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
      for (const m of ms) { if (m.map) m.map.dispose(); m.dispose(); }
    });
  }

  // resalta el cable actual (y atenua o esconde el resto)
  function resaltar() {
    if (!R || !R.cab) return;
    const { THREE } = T;
    R.cab.forEach((meshes, i) => {
      const cur = i === k, c = D.cables[i];
      for (const g of meshes) {
        const e6 = g.userData.tipo === 'e6';
        g.visible = cur || (todos && !e6);
        for (const ch of g.children) {
          if (ch.userData.halo) { ch.visible = cur && !e6; continue; }
          ch.material.opacity = cur ? (e6 ? 0.55 : 1) : (c.hecho ? 0.5 : 0.22);
          ch.material.depthWrite = cur;
        }
        g.renderOrder = cur ? 5 : 0;
      }
    });
    // puntas del cable actual
    if (R.marcas) { for (const m of R.marcas) { m.parent.remove(m); limpiar(m); } }
    R.marcas = [];
    const c = D.cables[k]; if (!c) return;
    const G = D.modelo.gabinete;
    const enPuerta = p => p.zona === 'puerta';
    for (const [p, col, lbl, lado] of [[c.desde, COL_DESDE, c.desde.texto, 'izq'], [c.hasta, COL_HASTA, c.hasta.texto, 'der']]) {
      const g = new THREE.Group();
      const s = new THREE.Mesh(new THREE.SphereGeometry(6, 20, 14), new THREE.MeshBasicMaterial({ color: col, depthTest: false, transparent: true, opacity: 0.9 }));
      s.renderOrder = 30; s.userData.pulso = true; g.add(s);
      g.add(etiqueta(lbl, { fondo: col === COL_DESDE ? '#ff6a00' : '#1565c0', borde: '#ffffff', color: '#ffffff', alto: 22, lado }));
      if (enPuerta(p)) { g.position.copy(R.local(p.p)); R.puerta.add(g); } else { g.position.set(...p.p); R.scene.add(g); }
      R.marcas.push(g);
    }
    pulsar();
  }

  /* ---------------- camara ---------------- */
  function vistaGeneral(animar = true) {
    const G = D.modelo.gabinete, { THREE } = T;
    const tgt = new THREE.Vector3(G.ancho / 2, G.alto / 2, G.prof / 2);
    const dir = new THREE.Vector3(G.bisagra === 'der' ? -0.62 : 0.62, 0.38, 1).normalize();   // del lado de la cerradura
    mover(tgt, tgt.clone().add(dir.multiplyScalar(Math.max(G.ancho, G.alto) * 2.0)), animar);
  }
  function encuadrar(animar = true) {
    const { THREE } = T; const c = D.cables[k]; if (!c || !R.cab[k]) return;
    R.scene.updateMatrixWorld(true);
    const box = new THREE.Box3();
    for (const g of R.cab[k]) if (g.userData.tipo !== 'e6' || R.cab[k].length === 1) box.expandByObject(g.children[0]);
    for (const m of R.marcas || []) box.expandByPoint(m.getWorldPosition(new THREE.Vector3()));
    if (box.isEmpty()) return vistaGeneral(animar);
    const ctr = box.getCenter(new THREE.Vector3()), rad = Math.max(120, box.getSize(new THREE.Vector3()).length() / 2);
    const z = c.hasta.zona, zd = c.desde.zona;
    let dir;
    if (z === 'puerta' || zd === 'puerta') {
      const n = new THREE.Vector3(0, 0, -1).applyQuaternion(R.puerta.quaternion);
      dir = n.add(new THREE.Vector3(0, 0.35, 0.55));
      if (c.tramos.some(t => t.tipo === 'e8')) dir.add(new THREE.Vector3(0.25, 0, 0.6));
    } else {
      // un lateral se mira desde adentro, del otro costado; del lado de las bisagras, casi de frente (si no, la puerta
      // abierta queda entre la camara y el gabinete)
      const bis = D.modelo.gabinete.bisagra === 'der' ? 1 : -1;
      const lat = z === 'lateral izq' || (zd === 'lateral izq' && z !== 'lateral der') ? 1 : z === 'lateral der' || zd === 'lateral der' ? -1 : 0;
      dir = lat ? new THREE.Vector3(lat * (lat === bis ? 0.42 : 0.9), 0.3, lat === bis ? 1 : 0.75) : new THREE.Vector3(0.3, 0.3, 1);
    }
    dir.normalize();
    const d = rad / Math.sin((R.camera.fov * Math.PI / 180) / 2) * 1.05;
    mover(ctr, ctr.clone().add(dir.multiplyScalar(d)), animar);
  }
  function mover(tgt, pos, animar) {
    const ctl = R.controls, cam = R.camera;
    if (!animar) { ctl.target.copy(tgt); cam.position.copy(pos); ctl.update(); pedirRender(); return; }
    const t0 = performance.now(), dur = 520, a0 = ctl.target.clone(), p0 = cam.position.clone();
    anim = now => {
      const u = Math.min(1, (now - t0) / dur), e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
      ctl.target.lerpVectors(a0, tgt, e); cam.position.lerpVectors(p0, pos, e);
      if (u >= 1) anim = null;
    };
    pedirRender();
  }
  function puerta(abrir, animar = true) {
    puertaAbierta = abrir;
    el('e8Puerta').textContent = abrir ? '🚪 Cerrar puerta' : '🚪 Abrir puerta';
    if (!R || !R.puerta) return;
    const G = D.modelo.gabinete;
    const fin = abrir ? (G.bisagra === 'der' ? 1 : -1) * (G.apertura || 110) * Math.PI / 180 : 0;
    if (!animar) { R.puerta.rotation.y = fin; pedirRender(); return; }
    const ini = R.puerta.rotation.y, t0 = performance.now();
    R.animPuerta = now => { const u = Math.min(1, (now - t0) / 600); R.puerta.rotation.y = ini + (fin - ini) * (1 - Math.pow(1 - u, 3)); if (u >= 1) R.animPuerta = null; };
    pedirRender();
  }
  /* ---------------- render ---------------- */
  // se dibuja SOLO cuando algo cambia (no en cada cuadro: el visor abierto sin tocar no gasta CPU ni GPU): una escena
  // sucia, la animacion de la camara o de la puerta, los controles que siguen moviendose (amortiguacion) o el pulso de las
  // puntas del cable actual (1,5 s al elegirlo)
  let sucio = true, pulsoHasta = 0, pulsando = false;
  const pedirRender = () => { sucio = true; if (!raf && abierto && R) raf = requestAnimationFrame(loop); };
  const pulsar = () => { pulsoHasta = performance.now() + 1500; pedirRender(); };
  function loop() {
    raf = 0;
    if (!abierto || !R) return;
    const now = performance.now();
    if (anim) anim(now);
    if (R.animPuerta) R.animPuerta(now);
    const movio = R.controls.update();      // (OrbitControls con amortiguacion: true mientras sigue moviendose)
    const pulso = now < pulsoHasta;
    if (pulso || pulsando) {
      for (const m of R.marcas || []) m.children[0].scale.setScalar(pulso ? 1 + 0.3 * Math.sin(now / 220) : 1);
      pulsando = pulso; sucio = true;
    }
    if (sucio || movio) R.renderer.render(R.scene, R.camera);
    sucio = false;
    if (!raf && (anim || R.animPuerta || movio || pulso)) raf = requestAnimationFrame(loop);
  }
  function tam() {
    if (!R) return;
    const st = el('e8Stage'), w = st.clientWidth, h = st.clientHeight;
    if (!w || !h) return;
    R.renderer.setSize(w, h, false); R.renderer.domElement.style.width = w + 'px'; R.renderer.domElement.style.height = h + 'px';
    R.camera.aspect = w / h; R.camera.updateProjectionMatrix(); pedirRender();
  }
  // controles de respaldo si no se pudo bajar OrbitControls: rueda = zoom, arrastrar = girar, clic derecho = mover
  function miniOrbit(cam, dom) {
    const { THREE } = T;
    const c = { target: new THREE.Vector3(), enableDamping: false, update() { cam.lookAt(this.target); return false; } };
    let drag = null;
    dom.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY, b: e.button }; dom.setPointerCapture(e.pointerId); });
    dom.addEventListener('pointerup', () => { drag = null; });
    dom.addEventListener('pointermove', e => {
      if (!drag) return;
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
      const off = cam.position.clone().sub(c.target);
      if (drag.b === 2) {
        const d = off.length() * 0.0015, right = new THREE.Vector3().crossVectors(cam.up, off).normalize(), up = cam.up.clone();
        const m = right.multiplyScalar(dx * d).add(up.multiplyScalar(dy * d));
        c.target.add(m); cam.position.add(m);
      } else {
        const sp = new THREE.Spherical().setFromVector3(off);
        sp.theta -= dx * 0.006; sp.phi = Math.min(Math.PI - 0.05, Math.max(0.05, sp.phi - dy * 0.006));
        cam.position.copy(c.target).add(new THREE.Vector3().setFromSpherical(sp));
      }
      pedirRender();
    });
    dom.addEventListener('wheel', e => { e.preventDefault(); const off = cam.position.clone().sub(c.target); off.multiplyScalar(e.deltaY > 0 ? 1.12 : 0.89); cam.position.copy(c.target).add(off); pedirRender(); }, { passive: false });
    return c;
  }

  /* ---------------- clic en la escena: elegir un cable o ubicar un aparato ---------------- */
  function clic(e) {
    if (!R || !R.down || Math.hypot(e.clientX - R.down[0], e.clientY - R.down[1]) > 4 || e.button !== 0) return;
    const { THREE } = T;
    const r = R.renderer.domElement.getBoundingClientRect();
    const ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1), R.camera);
    if (ubicando) {
      const hit = ray.intersectObjects(R.vistas, false)[0];
      if (!hit || !hit.uv) return toast('Hacé clic sobre una placa, un lateral o la puerta');
      const v = hit.object.userData.vista, b = v.box;
      const X = b[0] + hit.uv.x * (b[2] - b[0]), Y = b[1] + hit.uv.y * (b[3] - b[1]);
      return guardarUbicacion(ubicando, { vista: v.id, pt: [X, Y] });
    }
    const objs = []; R.cab.forEach(ms => ms.forEach(g => { if (g.visible) objs.push(g.children[0]); }));
    const hit = ray.intersectObjects(objs, false)[0];
    if (hit) { const i = hit.object.parent.userData.i; if (i != null && i !== k) ir(i); }
  }
  function setUbicar(tag) {
    ubicando = tag;
    el('e8Stage').classList.toggle('ubicando', !!tag);
    el('e8UbiBox').hidden = !tag && !el('e8UbiBox').dataset.abierto;
  }
  function abrirUbicar() {
    if (!D) return;
    const c = D.cables[k];
    const fuera = new Set(D.resumen.sin_ubicar || []);
    const ap = (D.aparatos || []).filter(a => a.zona !== 'bandeja').map(a => a.tag);
    const delCable = c ? [c.desde, c.hasta].filter(p => p.zona !== 'bandeja' && p.tag).map(p => p.tag) : [];
    const tags = [...new Set([...delCable, ...fuera, ...ap])].filter(t => t && !/^(LI|LD|\?)/.test(t));
    const ub = (D.e8 && D.e8.ubicaciones) || {};
    el('e8UbiBox').dataset.abierto = '1';
    el('e8UbiBox').hidden = false;
    el('e8UbiBox').innerHTML = `<b>📍 Ubicar un aparato</b>
      <label>Aparato <select id="e8UbiTag">${tags.map(t => `<option value="${esc(t)}">${esc(t)}${fuera.has(t) ? ' (sin ubicar)' : ub[t] ? ' (a mano)' : ''}</option>`).join('')}</select></label>
      <div class="muted">Después hacé clic en su lugar en la placa, el lateral o la puerta (sobre el dibujo). Queda guardado en el trabajo.</div>
      <div class="e8-ubi-b"><button class="btn sm" data-u="quitar" title="Volver a la ubicación del topográfico">Quitar la ubicación a mano</button>
        <button class="btn ghost sm" data-u="cerrar">Cancelar (Esc)</button></div>`;
    const sel = el('e8UbiTag');
    const upd = () => { setUbicar(sel.value); el('e8UbiBox').querySelector('[data-u="quitar"]').disabled = !ub[sel.value]; };
    sel.addEventListener('change', upd); upd();
  }
  function cerrarUbicar() { delete el('e8UbiBox').dataset.abierto; el('e8UbiBox').hidden = true; setUbicar(null); }
  async function guardarUbicacion(tag, u) {
    try {
      await api(`/api/trabajo/${job}/e8/marcas`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ubicacion: { tag, ...u } }) });
      toast(u.borrar ? `${tag}: vuelve a la ubicación del topográfico` : `${tag} ubicado`);
    } catch (e) { return toast('No se pudo guardar: ' + e.message, 5000); }
    cerrarUbicar();
    // (el cable actual se vuelve a buscar por su clave, que no cambia al ubicar el aparato; el indice solo si ya no esta)
    const id = D.cables[k]?.id;
    await cargar();
    if (D && T && !T.error) construir();
    const i = buscarId(id);
    ir(i >= 0 ? i : k, false);
  }

  /* ---------------- eventos ---------------- */
  function init() {
    el('e8BtnE8').addEventListener('click', open);
    el('e8BtnE6').addEventListener('click', aE6);
    el('e8Close').addEventListener('click', close);
    el('e8E6').addEventListener('click', aE6);
    el('e8Prev').addEventListener('click', () => ir(k - 1));
    el('e8Next').addEventListener('click', () => siguiente());
    el('e8Ok').addEventListener('change', () => marcar(k, el('e8Ok').checked));
    el('e8SideBtn').addEventListener('click', () => setSide(el('e8Side').hidden));
    el('e8Puerta').addEventListener('click', () => puerta(!puertaAbierta));
    el('e8Todos').addEventListener('click', () => { todos = !todos; el('e8Todos').classList.toggle('on', todos); el('e8Todos').setAttribute('aria-pressed', todos);
      el('e8Todos').textContent = todos ? 'Todos los cables' : 'Solo el actual'; resaltar(); });
    el('e8Fit').addEventListener('click', () => R && vistaGeneral());
    el('e8Ubicar').addEventListener('click', () => el('e8UbiBox').hidden ? abrirUbicar() : cerrarUbicar());
    el('e8UbiBox').addEventListener('click', e => {
      const b = e.target.closest('[data-u]'); if (!b) return;
      if (b.dataset.u === 'cerrar') cerrarUbicar();
      if (b.dataset.u === 'quitar') guardarUbicacion(el('e8UbiTag').value, { borrar: true });
    });
    el('e8List').addEventListener('click', e => {
      const it = e.target.closest('.e8-it'); if (!it) return;
      const i = +it.dataset.i;
      if (e.target.matches('[data-ok]')) { marcar(i, e.target.checked); return; }
      ir(i);
    });
    let qT;
    el('e8Q').addEventListener('input', () => { clearTimeout(qT); qT = setTimeout(renderList, 120); });
    el('e8Q').addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); const it = el('e8List').querySelector('.e8-it'); if (it) ir(+it.dataset.i); e.target.blur(); }
      if (e.key === 'Escape') { e.preventDefault(); e.target.value = ''; renderList(); e.target.blur(); }
    });
    el('e8Viewer').addEventListener('click', e => {
      const b = e.target.closest('[data-a]'); if (!b) return;
      if (b.dataset.a === 'e6') aE6();
      if (b.dataset.a === 'releer') { mensaje('Volviendo a leer el gabinete…', 0.02); cargar(true).then(() => { if (D && T && !T.error) { construir(); ir(k ?? primero(), false); } }); }
    });
    // teclas: en captura, para que no lleguen a los otros visores ni a la busqueda de la pagina
    window.addEventListener('keydown', e => {
      if (el('e8Viewer').hidden) return;
      if (e.target.tagName === 'SELECT' || (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox')) { if (e.key !== 'Escape') return; }
      const keys = {
        ArrowRight: () => siguiente(), ArrowLeft: () => ir(k - 1), ' ': () => marcar(k, undefined, true), Enter: () => marcar(k, undefined, true),
        Escape: () => ubicando || !el('e8UbiBox').hidden ? cerrarUbicar() : close(), p: () => puerta(!puertaAbierta), t: () => el('e8Todos').click(),
        '0': () => R && vistaGeneral(), f: () => R && encuadrar(), l: () => setSide(el('e8Side').hidden),
      };
      const f = keys[e.key] || keys[e.key.toLowerCase?.()];
      if (f) { e.preventDefault(); e.stopPropagation(); f(); }
      else if (e.key === '/' ) { e.preventDefault(); e.stopPropagation(); el('e8Q').focus(); }
    }, true);
  }
  function siguiente() { if (!D) return; const c = D.cables[k]; if (c && !c.hecho) marcar(k, true, true); else ir(k + 1); }
  function aE6() {
    close();
    if (typeof setTab === 'function') setTab('instructivo');
    setTimeout(() => el('tabs')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60);
  }
  init();
  // boton Atras del navegador (o un link a otra parte): si la direccion ya no es la de E8 de ESTE trabajo, E8 se cierra
  window.addEventListener('hashchange', () => {
    const m = location.hash.match(/^#\/trabajo\/([0-9a-f]{12})\/e8(?:\/(\d+))?(?:\/|$)/);
    if (abierto && (!m || m[1] !== job)) close();
    else if (abierto && m[2] && D && +m[2] - 1 !== k) ir(+m[2] - 1);      // (#…/e8/<n> con E8 abierto: ir al cable n)
    porDireccion();
  });
  porDireccion();
  return { open, close, get D() { return D; }, get R() { return R; } };
})();
