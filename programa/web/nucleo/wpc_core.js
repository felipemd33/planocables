'use strict';
/* Lista de cables para el centro de cableado WPC (Weidmüller): la lógica, sin pantalla (PLAN_MODULAR.md 5.2-5.5).
   Es el código que estaba en wpc.js, movido: el mismo CSV byte a byte. La pantalla (web/wpc.js) y la otra app (Node)
   usan este mismo archivo.
   Núcleo (programa/web/nucleo/): sin DOM, sin fetch y sin globales del visor (D, S, $): el instructivo y la
   configuración entran como argumentos. Carga con <script> (global WpcCore; antes nucleo/zip.js) y con require
   (module.exports).

   API
     config(base, {producto, trabajo}) -> cfg     la configuración que vale para un trabajo (ver NIVELES)
     filas(ins, cfg)                   -> [fila]  en el orden de cableado: la bandeja (pasos) y, si se piden, pendientes
                                                  LI↔LI y otra estación al final. fila = {l, tipo, grupo, k, rg, sec,
                                                  motivo, fuera, calc, largo, color, giroCalc, giro}
     lateralInfo(estacion8)            -> e8l     adónde va de verdad un cable que sale a LI / LD (estación E8)
     largo(fila, cfg, e8l, topo)       -> {mm, como, falta?}
     canaleta(ruta, ductos, escala)    -> mm      la parte de la ruta que corre DENTRO de las canaletas
     csv(filas, cfg)                   -> texto   el .csv de la planilla (UTF-8 con BOM, ';', coma decimal, sin
                                                  encabezado, 49 columnas, CRLF), igual que la macro
     wpcXml(filas, cfg, nombre)        -> texto   el XML de adentro del .wpc (como lo guarda la máquina al importar)
     wpcZip(nombre, xml, fecha?)       -> Promise<Uint8Array>   el .wpc: zip de una entrada que se llama como el archivo
     nombreArchivo(producto, ext, respaldo) -> '75286-1 - 75287 Rev 6.wpc' ('<respaldo> - WPC.wpc' sin código)
   (filas, csv y wpcXml son las que van al archivo: se les pasan solo las filas que no quedan fuera del arnés.)

   LARGO (regla del taller): en la bandeja, recorrido por las canaletas + sobrante + agregado del taller. Los que salen a
   LI / LD, con la estación E8 (adónde van de verdad), por la regla del 2026-10-09 (antes, 2026-10-06):
   - muere en la bandeja lateral: acometida (borne → canaleta, 75 fijo) + canaleta de la bandeja + la curva de la
     posterior a ESA lateral (curva_LI / curva_LD; sin curva_LD, la de LI) + canaleta de la lateral + acometida_LI
     (canaleta → borne o aparato, 75 fijo). A la lateral derecha los cables mueren siempre ahí;
   - sigue a la puerta / placa (un aparato de la puerta o de la placa: hacia_puerta de la E8 sin 'sin_aparato'):
     acometida + canaleta de la bandeja + la curva de la lateral por donde pasa + la canaleta de esa lateral hasta la
     salida a la puerta (el tránsito de la E8, que hay solo con la bisagra elegida; sin él, 0) + puerta;
   - lo demás de «puerta / placa» de la E8, que no va a la puerta ni a la placa (zona hidráulica, batería, solenoides,
     PT 001...: sin dibujar o dibujados en el fondo): como antes, acometida + canaleta de la bandeja + puerta (a
     confirmar con el taller). Una E8 de antes de E8-4 (sin hacia_puerta) no lo distingue: todo va a la puerta.
   Por producto se editan curva_LI, curva_LD, puerta y extra_puerta (de la lateral a la puerta); las acometidas son fijas.
   «Canaleta» = la parte de la ruta que corre DENTRO de las canaletas (sin la acometida del borne, que va con el fijo).
   Sin E8 (plano sin la lateral): recorrido + sobrante + lo fijo a LI / LD + agregado. Pendientes de la lateral: canaleta
   de la lateral + margen (o puerta / placa) + agregado. La WPC solo corta (columnas fijas sin pelar ni crimpar).
   REEMPLAZOS: un color y sección se cortan con otro (la WPC no tiene slots de 4 mm²); solo en esta lista, el
   instructivo no cambia. TERMOS (columna 22, "giro origen|giro destino" en grados) según el lado de cada punta: una
   aguas arriba y otra aguas abajo → 0|0; las dos abajo → 180|0; las dos arriba → 0|180. FUERA del arnés
   (destildados, con el motivo): 35 mm², comunicación, solenoides y campo.

   CONFIGURACIÓN (programa/web/wpc.json; la cambia el taller con el panel ⚙ Parámetros, PUT /api/config/wpc)
   NIVELES: wpc.json (todos los productos) < wpc.json → productos[código] < ins.wpc.cfg (este trabajo). Si no hay nada
   por código se busca por documento (productos["ZPL-76884"] sigue andando). Un valor null o '' en un nivel = «el de
   arriba». Un parámetro declarado en wpc.json → parametros se toma entero (las listas y tablas no se mezclan entre
   niveles); lo que no está declarado se mezcla clave por clave. cfg._de[clave] = de qué nivel viene cada parámetro
   declarado ('trabajo', 'producto', 'global' o 'defecto') y cfg._producto = {clave, por} (la entrada de productos usada).
   SECCIONES de wpc.json:
     <largos>            margen_bandeja, agregado_bandeja, acometida, curva_LI, curva_LD, acometida_LI, puerta, margen_LI,
                         extra_puerta, extra_LI, extra_LD, agregado_LI, agregado_puerta, redondeo, largo_sin_ruta,
                         largo_pendiente (mm); pendientes / otra (true / false: incluirlos en la lista)
     fuera               seccion_desde, comunicacion_seccion_hasta (mm²); comunicacion_re, solenoide_re, campo_re (regex,
                         sin distinguir mayúsculas, sobre «origen destino»)
     termos              mixto, abajo_abajo, arriba_arriba, sin_dato ("origen|destino"); opciones (las del menú)
     fijos               pelado_origen, proceso_origen, proceso_destino, crimpado_origen, dimension_origen,
                         crimpado_destino (columnas 24-26, 28, 46 y 47 del CSV)
     colores / codigos   color del plano → código de la WPC / los códigos que acepta la WPC (menú)
     reemplazos          [{de: {color, secc}, a: {color, secc}, motivo}] para todos los productos (en un producto se
                         cambia con productos[código].reemplazos; [] = ninguno). La forma vieja {documento: [reglas]}
                         se sigue leyendo (vale para ese documento o código)
     marcador            columna 21 del .wpc: modo 'seccion' (por la tabla [{desde, hasta, valor}], la primera fila que
                         incluye la sección; sin desde / hasta = sin límite) o 'vacio'
     archivo_wpc         la raíz del XML: UserFilter ('-1') y pdfFile ('')
     productos           {código o documento: {los parámetros que cambian en ese producto}}
     parametros          [{clave, etiqueta, unidad, paso, minimo, grupo, tipo, ayuda, opciones, opciones_de}]: lo que
                         muestra el panel ⚙ Parámetros (un parámetro nuevo aparece sin tocar el JS). tipo: numero,
                         si_no, texto, regex, opcion, lista, colores, reemplazos, marcador
     _nota*              notas para el que lee el archivo (no son parámetros)
   VALORES POR DEFECTO (cuando falta la clave en todos los niveles): un largo que falta vale 0; sin redondeo (o 0, o
   un texto) se redondea a 1 mm; sin fijos, 10/1/1/8/10/8; sin termos, 0|0, 180|0, 0|180 y 0|0; sin marcador, por
   sección con la tabla de abajo (MARCADOR); sin archivo_wpc, UserFilter -1 y pdfFile vacío. */
const WpcCore = (() => {
  const VERSION = '2026.10.09';
  const NCOL = 49;
  // marcador por sección (decidido el 2026-10-07): ≤ 1 mm² y de 2,5 a 6 mm²; otra sección, vacío
  const MARCADOR = { modo: 'seccion', tabla: [
    { desde: null, hasta: 1, valor: '1423340000; HSS-HF 1.6-3.2 EL W13M' },
    { desde: 2.5, hasta: 6, valor: '1423360000; HSS-HF 3.2-6.4 EL W13M' }] };
  const SECCIONES = new Set(['productos', 'parametros']);      // de wpc.json, que no son parámetros

  const key = l => `${l.num}|${l.origen ?? l.a}|${l.destino ?? l.b}`;
  const secNum = l => String(l.secc || ((l.cable || '').match(/(\d+(?:[.,]\d+)?)MM/i) || [])[1] || '').replace(',', '.');
  const coma = v => String(v).replace('.', ',');
  const LAT = d => d === 'LI' || d === 'LD';
  const normC = c => String(c ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const num = (cfg, k) => +(cfg[k] ?? 0);

  // ---- configuración: global < producto < trabajo
  const esObj = x => x != null && typeof x === 'object' && !Array.isArray(x);
  const hay = v => v !== undefined && v !== null && v !== '';
  const copia = x => (x === undefined ? x : JSON.parse(JSON.stringify(x)));
  const leer = (o, clave) => String(clave).split('.').reduce((a, k) => (esObj(a) ? a[k] : undefined), o);
  function poner(o, clave, v) {
    const ks = String(clave).split('.'); let a = o;
    ks.slice(0, -1).forEach(k => { if (!esObj(a[k])) a[k] = {}; a = a[k]; });
    a[ks[ks.length - 1]] = v;
  }
  function quitar(o, clave) {
    const ks = String(clave).split('.'), padre = ks.length > 1 ? leer(o, ks.slice(0, -1).join('.')) : o;
    if (esObj(padre)) delete padre[ks[ks.length - 1]];
    // (los objetos que quedan vacíos se sacan: el nivel no cambia nada ahí)
    for (let i = ks.length - 1; i > 0; i--) {
      const p = ks.slice(0, i).join('.'), x = leer(o, p);
      if (esObj(x) && !Object.keys(x).length) quitar(o, p); else break;
    }
  }
  const parametros = base => (esObj(base) && Array.isArray(base.parametros) ? base.parametros.filter(p => esObj(p) && p.clave) : []);
  // la entrada de wpc.json → productos para este producto: por código y, si no hay, por documento
  function productoDe(base, producto) {
    const P = esObj(base) && esObj(base.productos) ? base.productos : {}, p = producto || {};
    for (const [k, por] of [[p.codigo, 'codigo'], [p.documento, 'documento']]) if (hay(k) && esObj(P[k])) return { clave: k, por, valores: P[k] };
    return { clave: hay(p.codigo) ? p.codigo : hay(p.documento) ? p.documento : null, por: null, valores: null };
  }
  // un nivel encima de lo de abajo: lo declarado se toma entero; lo demás se mezcla clave por clave
  function encima(cfg, nivel, decl, ruta = '') {
    for (const [k, v] of Object.entries(nivel)) {
      if (!ruta && (SECCIONES.has(k) || k.startsWith('_'))) continue;
      if (!hay(v)) continue;
      const r = ruta ? ruta + '.' + k : k;
      if (!decl.has(r) && esObj(v) && esObj(cfg[k])) encima(cfg[k], v, decl, r);
      else cfg[k] = copia(v);
    }
  }
  // reemplazos: la lista para todos, o la forma vieja {documento o código: [reglas]}
  function reglasReemplazo(r, producto) {
    if (Array.isArray(r)) return r;
    if (esObj(r)) { const p = producto || {}; return [p.codigo, p.documento].map(k => (hay(k) ? r[k] : null)).find(Array.isArray) || []; }
    return [];
  }
  function config(base, op = {}) {
    base = esObj(base) ? base : {};
    const trabajo = esObj(op.trabajo) ? op.trabajo : {}, ps = parametros(base), decl = new Set(ps.map(p => p.clave));
    const cfg = {};
    for (const [k, v] of Object.entries(base)) if (!SECCIONES.has(k) && !k.startsWith('_')) cfg[k] = copia(v);
    const pr = productoDe(base, op.producto);
    if (pr.valores) encima(cfg, pr.valores, decl);
    encima(cfg, trabajo, decl);
    cfg.reemplazos = reglasReemplazo(cfg.reemplazos, op.producto).filter(r => r && r.de && r.a);
    const de = {};
    ps.forEach(p => {
      de[p.clave] = hay(leer(trabajo, p.clave)) ? 'trabajo' : pr.valores && hay(leer(pr.valores, p.clave)) ? 'producto'
        : leer(base, p.clave) !== undefined ? 'global' : 'defecto';
    });
    Object.defineProperty(cfg, '_de', { value: de, enumerable: false });
    Object.defineProperty(cfg, '_producto', { value: { clave: pr.clave, por: pr.por }, enumerable: false });
    return cfg;
  }
  const resuelta = (cfg, ins) => (cfg && cfg._de ? cfg : config(cfg, { producto: (ins || {}).producto, trabajo: ((ins || {}).wpc || {}).cfg }));

  // ---- reemplazo de color y sección (solo en esta lista: el instructivo y el listado no cambian)
  function reemplazo(l, reglas) {
    const sec = parseFloat(secNum(l)), col = normC(l.color);
    return (reglas || []).find(r => normC(r.de.color) === col && parseFloat(r.de.secc) === sec) || null;
  }
  // ---- cables que no van al arnés de la WPC (fuera): el motivo, o null si va
  function motivoFuera(f, cfg) {
    const FU = cfg.fuera || {}, l = f.l, sec = parseFloat(f.sec), txt = `${l.origen ?? l.a ?? ''} ${l.destino ?? l.b ?? ''}`;
    const re_ = k => { const s = FU[k]; try { return s ? new RegExp(s, 'i') : null; } catch (e) { return null; } };
    if (!f.sec) return 'sin sección (malla, tierra o cable de campo)';
    if (FU.seccion_desde != null && sec >= +FU.seccion_desde) return `${coma(f.sec)} mm²: no la corta la WPC`;
    if (FU.comunicacion_seccion_hasta != null && sec <= +FU.comunicacion_seccion_hasta) return 'comunicación (sección fina)';
    const rc = re_('comunicacion_re'), rs = re_('solenoide_re'), rk = re_('campo_re');
    if (rc && rc.test(txt)) return 'comunicación';
    if (rs && rs.test(txt)) return 'va a una solenoide';
    if (l.estacion === 'CAMPO' || (rk && rk.test(txt)) || /^s\/n\b/i.test(l.num || '')) return 'va a campo';
    return null;
  }
  // ---- giro de los termos (señalizadores) de las dos puntas, "origen|destino" en grados (columna 22 del CSV)
  // El lado de cada punta: arriba / abajo del eje de su riel por el punto exacto del borne (como el instructivo);
  // sin punto, por el texto (ARRIBA / ABAJO, QUATTRO .1 .2 arriba / .3 .4 abajo); la punta que sale a LI / LD, abajo.
  function ladoPunto(p, tag, topo) {
    const F = (topo || {}).filas || []; if (!p || !F.length) return null;
    const c = ((topo || {}).comp || {})[tag], eje = c && c.fila && c.fila <= F.length ? F[c.fila - 1] : F.reduce((a, e) => Math.abs(e - p[1]) < Math.abs(a - p[1]) ? e : a);
    return Math.abs(p[1] - eje) < 1 ? null : (p[1] > eje ? 'arriba' : 'abajo');
  }
  function ladoTexto(t) {
    t = String(t || '');
    if (/ ARRIBA$/.test(t)) return 'arriba';
    if (/ ABAJO$/.test(t)) return 'abajo';
    const m = /\.(\d)$/.exec(t); return m ? ('12'.includes(m[1]) ? 'arriba' : 'abajo') : null;
  }
  const tagDe = t => String(t || '').split(' ')[0];
  function lados(f, topo) {
    const l = f.l;
    if (f.tipo === 'pendiente') return { o: null, d: null };
    const o = l.lado || ladoPunto(l.marca_o, tagDe(l.origen), topo) || ladoTexto(l.origen);
    const d = LAT(l.destino) ? 'abajo' : (ladoPunto(l.marca_d, tagDe(l.destino), topo) || ladoTexto(l.destino));
    return { o, d };
  }
  function giroCalc(f, cfg, topo) {
    const T = cfg.termos || {}, { o, d } = lados(f, topo), txt = s => s === 'arriba' ? 'aguas arriba' : s === 'abajo' ? 'aguas abajo' : 'sin dato';
    let v, por;
    if (!o || !d) { v = T.sin_dato ?? '0|0'; por = 'no se sabe el lado de una punta'; }
    else if (o === 'abajo' && d === 'abajo') { v = T.abajo_abajo ?? '180|0'; por = 'las dos puntas aguas abajo: gira el primer termo'; }
    else if (o === 'arriba' && d === 'arriba') { v = T.arriba_arriba ?? '0|180'; por = 'las dos puntas aguas arriba: gira el segundo termo'; }
    else { v = T.mixto ?? '0|0'; por = 'una punta aguas arriba y otra aguas abajo: ningún termo gira'; }
    return { v, o, d, como: `origen ${txt(o)}${LAT(f.l.destino) ? ` · destino ${f.l.destino} (afuera: se toma aguas abajo)` : ` · destino ${txt(d)}`} → ${por}` };
  }

  // ---- filas en el orden de cableado: la bandeja (pasos) y, si se piden, pendientes LI↔LI y otra estación al final.
  // Las ediciones a mano (ins.wpc: largo, color, giro, excluir, incluir) mandan; ins no se cambia.
  function filas(ins, cfg) {
    ins = ins || {}; cfg = resuelta(cfg, ins);
    const w = ins.wpc || {}, out = [], topo = ins.topo || {}, e8l = lateralInfo(ins.estacion8);
    (ins.pasos || []).forEach(p => p.lineas.forEach(l => out.push({ l, tipo: 'bandeja', grupo: p.titulo })));
    if (cfg.pendientes) (ins.pendientes || []).forEach(l => out.push({ l, tipo: 'pendiente', grupo: 'Pendientes LI ↔ LI' }));
    if (cfg.otra) (ins.otra_estacion || []).forEach(l => out.push({ l, tipo: 'otra', grupo: 'Otra estación (' + (l.estacion || '') + ')' }));
    const excl = new Set(w.excluir || []), incl = new Set(w.incluir || []), mLargo = w.largo || {}, mColor = w.color || {}, mGiro = w.giro || {};
    out.forEach(f => {
      f.k = key(f.l);
      f.rg = reemplazo(f.l, cfg.reemplazos);       // regla: otro color y sección para la WPC
      f.sec = f.rg ? String(f.rg.a.secc).replace(',', '.') : secNum(f.l);
      // no va al arnés (sin sección, 35 mm², comunicación, solenoide, campo) salvo que se tilde a mano
      f.motivo = motivoFuera(f, cfg);
      f.fuera = excl.has(f.k) || (!!f.motivo && !incl.has(f.k));
      f.calc = largo(f, cfg, e8l, topo); f.largo = mLargo[f.k] != null ? +mLargo[f.k] : f.calc.mm;
      f.color = mColor[f.k] || (cfg.colores || {})[f.rg ? f.rg.a.color : f.l.color] || '';
      f.giroCalc = giroCalc(f, cfg, topo); f.giro = mGiro[f.k] || f.giroCalc.v;
    });
    return out;
  }
  // ---- adónde va de verdad un cable que sale a LI / LD, con la estación E8 (ins.estacion8): recorrido por las
  // canaletas de la bandeja lateral (dibujada en el topográfico) o a la puerta / placa (pasa por la canaleta de la lateral)
  const sinLado = t => String(t || '').replace(/ (ARRIBA|ABAJO)$/, '');
  const claveE8 = (num, a, b) => [num, ...[sinLado(a), sinLado(b)].sort()].join('|');
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
  function lateralInfo(estacion8) {
    const e8 = estacion8 || {}, sale = {}, par = {}, transito = {};
    // los que van DE VERDAD a la puerta o a la placa: los de hacia_puerta que no son 'sin_aparato' (aparato de la vista de la
    // puerta o de una categoría de la puerta de e8_grupos.json). Lo demás de «puerta / placa» (la zona hidráulica, la
    // batería, las solenoides, sin dibujar o dibujadas en el fondo) no va a la puerta. Una E8 de antes de E8-4 (sin
    // hacia_puerta) no lo distingue: todo va a la puerta, como entonces.
    const hp = Array.isArray(e8.hacia_puerta) ? e8.hacia_puerta : null;
    const aPuerta = hp ? new Set(hp.filter(x => !x.sin_aparato).map(x => x.clave)) : null;
    (e8.laterales || []).forEach(L => {
      L.pasos.forEach(p => p.lineas.forEach(x => {
        if (x.largo_mm == null) return;
        const v = { tipo: 'lateral', mm: x.largo_mm, can: canaleta(x.ruta, L.ductos, L.escala), borne: x.origen, donde: L.nombre.toLowerCase(), puerta: x.otra === 'puerta / placa',
          directo: !!x.directo, lado: L.lado };      // (directo: del cargador derecho a la bornera de abajo, sin el ducto: E8-6)
        if (x.otra === 'bandeja principal') sale[`${x.num}|${sinLado(x.destino)}`] ??= v;   // de la bandeja (E6) a la lateral
        else par[x.clave] = v;                                                         // misma lateral, o lateral ↔ puerta
      }));
      // tránsito hacia la puerta por la lateral de la bisagra (E8-4, solo con la bisagra elegida): la canaleta de la
      // entrada a la lateral hasta la salida a la puerta, para los que vienen de la bandeja principal
      const T = L.transito;
      if (T && T.ruta) {
        const can = canaleta(T.ruta, L.ductos, L.escala);
        (T.cables || []).forEach(x => { if (x.desde === 'E6') transito[x.clave] = { can, lado: L.lado, donde: L.nombre.toLowerCase() }; });
      }
    });
    (e8.afuera || []).forEach(g => g.zona === 'puerta / placa' && g.cables.forEach(x => {
      if (x.otra_donde !== 'bandeja principal') return;
      sale[`${x.num}|${sinLado(x.otra)}`] ??= aPuerta && !aPuerta.has(x.clave) ? { tipo: 'no_puerta', donde: x.borne }
        : { tipo: 'puerta', donde: x.borne, por: transito[x.clave] || null };
    }));
    return { sale, par };
  }
  // largo = recorrido por las canaletas + margen (pelado, peinado) y, si sale de la bandeja, lo que necesita en LI/LD,
  // más el AGREGADO del taller según adónde va (en bandeja / a LI / a puerta y placa), a más de los márgenes de siempre
  function largo(f, cfg, e8l, topo) {
    const P = k => num(cfg, k);
    e8l = e8l || { sale: {}, par: {} }; topo = topo || {};
    const l = f.l, r = P('redondeo') || 1, up = v => Math.ceil(v / r) * r;
    const AG = { bandeja: P('agregado_bandeja'), LI: P('agregado_LI'), puerta: P('agregado_puerta') };
    const mas = k => AG[k] ? ` + agregado ${k === 'LI' ? 'a LI' : k === 'puerta' ? 'puerta / placa' : 'en bandeja'} ${AG[k]}` : '';
    if (f.tipo === 'pendiente') {
      const x = e8l.par[claveE8(l.num, l.a, l.b)];
      if (x) {
        const ext = x.puerta ? P('extra_puerta') : P('margen_LI'), k = x.puerta ? 'puerta' : 'LI';
        // (un cable directo del cargador a la bornera de abajo no pasa por la canaleta: el largo es el mismo, cambia el texto)
        return { mm: up(x.mm + ext + AG[k]), como: `${x.directo ? 'directo al borne' : `canaleta de la ${x.donde}`} ${x.mm} + ${x.puerta ? 'puerta / placa' : 'margen'} ${ext}${mas(k)}, redondeado a ${r}` };
      }
      return { mm: P('largo_pendiente'), como: 'pendiente LI↔LI (valor fijo)' };
    }
    if (!l.largo_mm) return { mm: P('largo_sin_ruta'), como: 'sin ruta en el topográfico: valor fijo', falta: true };
    const x = e8l.sale[`${l.num}|${sinLado(l.origen)}`];
    if (x && (x.tipo === 'lateral' || x.tipo === 'puerta' || x.tipo === 'no_puerta')) {
      // regla del taller (2026-10-09): acometida fija del borne a la canaleta + lo que corre dentro de las canaletas de la bandeja
      const can = canaleta(l.ruta, topo.ductos, topo.escala), canT = can != null ? can : l.largo_mm;
      const b = `${P('acometida')} (borne → canaleta) + canaleta de la bandeja ${canT}${can == null ? ' (ruta entera)' : ''}`;
      // la curva de la posterior a la lateral por donde pasa (LI / LD; sin curva_LD en la configuración, la de LI)
      const lado = s => (s === 'LD' || s === 'LI') ? s : (l.destino === 'LD' ? 'LD' : 'LI');
      const curva = s => s === 'LD' && cfg.curva_LD != null && cfg.curva_LD !== '' ? P('curva_LD') : P('curva_LI');
      if (x.tipo === 'lateral') {
        const s = lado(x.lado), cl = x.can != null ? x.can : x.mm;
        return { mm: up(P('acometida') + canT + curva(s) + cl + P('acometida_LI')),
          como: `${b} + curva a ${s} ${curva(s)} + canaleta de la ${x.donde} ${cl} + ${P('acometida_LI')} (canaleta → ${x.borne || 'borne'}), redondeado a ${r}` };
      }
      if (x.tipo === 'puerta') {
        const s = lado(x.por && x.por.lado), cl = x.por && x.por.can != null ? x.por.can : 0;
        const tr = x.por && x.por.can != null ? ` + canaleta de la ${x.por.donde} hasta la puerta ${cl}` : ' (sin el recorrido por la lateral: falta elegir la bisagra en la E8)';
        return { mm: up(P('acometida') + canT + curva(s) + cl + P('puerta')),
          como: `${b} + curva a ${s} ${curva(s)}${tr} + puerta / placa ${P('puerta')} (${x.donde}), redondeado a ${r}` };
      }
      // no va a la puerta ni a la placa (zona hidráulica, batería, solenoides...): como antes (a confirmar con el taller)
      return { mm: up(P('acometida') + canT + P('puerta')),
        como: `${b} + puerta / placa ${P('puerta')} (${x.donde}: no va a la puerta ni a la placa, como antes), redondeado a ${r}` };
    }
    // queda en la bandeja, o sale a LI / LD sin saber adónde (sin estación E8): agregado según el caso
    const ext = l.destino === 'LI' ? P('extra_LI') : l.destino === 'LD' ? P('extra_LD') : 0;
    const k = !LAT(l.destino) ? 'bandeja' : (x && x.tipo === 'puerta') ? 'puerta' : 'LI';
    return { mm: up(l.largo_mm + P('margen_bandeja') + ext + AG[k]),
      como: `canaletas ${l.largo_mm} + margen ${P('margen_bandeja')}${ext ? ` + ${l.destino} ${ext}` : ''}${mas(k)}, redondeado a ${r}` };
  }

  // ---- columnas de una fila del CSV (índice 0 = columna 1)
  function columnas(f, cfg) {
    const fx = cfg.fijos || {};
    const c = new Array(NCOL).fill('');
    c[6] = f.largo; c[7] = 1; c[8] = coma(f.sec); c[9] = f.color; c[11] = f.l.num; c[19] = f.l.num;
    c[21] = f.giro;                      // giro de los termos: "origen|destino" en grados (Labeling Position)
    c[23] = fx.pelado_origen ?? 10; c[24] = fx.proceso_origen ?? 1; c[25] = fx.proceso_destino ?? 1;
    c[27] = fx.crimpado_origen ?? 8; c[45] = fx.dimension_origen ?? 10; c[46] = fx.crimpado_destino ?? 8;
    return c;
  }
  function csv(fs, cfg) {
    cfg = cfg || {};
    const lin = fs.map(f => columnas(f, cfg).join(';'));
    return '﻿' + lin.map(s => s + '\r\n').join('');
  }

  // ---- el .wpc (PLAN_MODULAR.md 5.5): lo que hace la máquina al importar el CSV y guardar
  // - columna 9 (sección) con 2 decimales y punto: '2,5' → '2.50';
  // - columna 21 (marcador) vacía → el de la sección (marcador), o vacía con modo 'vacio';
  // - columnas 29 y 30 (AWG y pulgadas) → '0'; vacío → '0' en las columnas 7-9 y 23-49;
  // - XML plano en UTF-8, sin BOM ni declaración: <WPC Version="1.0" ProjectName="…" pdfFile="" UserFilter="-1">, una
  //   fila por cable <RowN Col1="…" … Col49="…" />, sangría de 2 espacios, CRLF entre líneas y sin salto al final.
  const A_CERO = [7, 8, 9, ...Array.from({ length: NCOL - 23 + 1 }, (_, i) => 23 + i)];
  const escXml = v => String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  function marcador(sec, cfg) {
    const m = esObj((cfg || {}).marcador) ? cfg.marcador : MARCADOR;
    if ((m.modo ?? 'seccion') !== 'seccion') return '';
    const s = parseFloat(String(sec).replace(',', '.'));
    if (!Number.isFinite(s)) return '';
    const tabla = Array.isArray(m.tabla) ? m.tabla : MARCADOR.tabla;
    const t = tabla.find(x => esObj(x) && (!hay(x.desde) || s >= +x.desde) && (!hay(x.hasta) || s <= +x.hasta));
    return t ? String(t.valor ?? '') : '';
  }
  function wpcXml(fs, cfg, nombre) {
    cfg = cfg || {};
    const raiz = esObj(cfg.archivo_wpc) ? cfg.archivo_wpc : {};
    const out = [`<WPC Version="1.0" ProjectName="${escXml(nombre ?? '')}" pdfFile="${escXml(raiz.pdfFile ?? '')}" UserFilter="${escXml(raiz.UserFilter ?? '-1')}">`];
    fs.forEach((f, i) => {
      const v = columnas(f, cfg).map(x => (x == null ? '' : String(x)));     // (como en el CSV)
      if (v[8] !== '') v[8] = parseFloat(v[8].replace(',', '.')).toFixed(2);
      if (v[20] === '') v[20] = marcador(v[8], cfg);
      v[28] = '0'; v[29] = '0';
      for (const k of A_CERO) if (v[k - 1] === '') v[k - 1] = '0';
      out.push(`  <Row${i + 1} ` + v.map((x, j) => `Col${j + 1}="${escXml(x)}"`).join(' ') + ' />');
    });
    out.push('</WPC>');
    return out.join('\r\n');
  }
  // el .wpc: zip de una sola entrada (deflate) que se llama igual que el archivo. Entrada = nombre del archivo
  const zipLib = () => (typeof ZipMin !== 'undefined' ? ZipMin : require('./zip.js'));
  function wpcZip(nombre, xml, fecha) {
    return zipLib().zipUno(nombre, new TextEncoder().encode(xml), fecha);
  }
  // nombre del archivo y ProjectName: '<código> - <plano> Rev <rev>' en ASCII (decidido el 2026-10-07); sin código de
  // producto, el de antes: '<respaldo> - WPC' (respaldo = el nombre del PDF sin .pdf)
  const ascii = s => String(s ?? '').normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^\x20-\x7e]/g, '')
    .replace(/[\\/:*?"<>|]/g, '-').replace(/\s+/g, ' ').trim();
  function nombreArchivo(producto, ext = '', respaldo = 'plano') {
    const p = producto || {}, fun = p.funcional || {};
    const cod = ascii(p.codigo);
    if (!cod) return `${String(respaldo ?? 'plano').replace(/[\\/:*?"<>|]/g, '-')} - WPC${ext}`;
    const plano = ascii(fun.numero ?? p.documento), rev = ascii(fun.numero != null ? fun.revision : p.revision);
    return [cod, plano ? plano + (rev ? ' Rev ' + rev : '') : ''].filter(Boolean).join(' - ').replace(/[ .]+$/, '') + ext;
  }

  return {
    VERSION, NCOL, MARCADOR, config, filas, lateralInfo, largo, canaleta, csv, wpcXml, wpcZip, nombreArchivo,
    // (ayudantes para la pantalla y las pruebas)
    parametros, productoDe, leer, poner, quitar, hay, key, secNum, coma, marcador, reglasReemplazo,
  };
})();
if (typeof module === 'object' && module && module.exports) module.exports = WpcCore;
