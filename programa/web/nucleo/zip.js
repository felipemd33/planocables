'use strict';
/* Zip mínimo de UNA entrada (deflate), sin bibliotecas: lo que necesita el archivo .wpc del centro de cableado
   (PLAN_MODULAR.md 5.5). CRC-32 propio y CompressionStream('deflate-raw'), que existe en el navegador y en Node 24.
   Encabezados como los .wpc reales del taller: versión 20, sin extras, sin comentario, atributos en 0; nombre con
   acentos → bandera UTF-8 (los reales son ASCII).
   Núcleo (programa/web/nucleo/): sin DOM, sin fetch y sin globales del visor. Carga con <script> (global ZipMin) y con
   require (module.exports).
   API: ZipMin.crc32(bytes) -> número · ZipMin.zipUno(nombre, bytes, fecha?) -> Promise<Uint8Array> */
const ZipMin = (() => {
  const TABLA = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
    return t;
  })();
  function crc32(b) {
    let c = 0xFFFFFFFF;
    for (let i = 0; i < b.length; i++) c = TABLA[(c ^ b[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }
  // deflate crudo (sin encabezado zlib), leyendo mientras se escribe (si no, un archivo grande se traba)
  async function deflateRaw(bytes) {
    const cs = new CompressionStream('deflate-raw'), w = cs.writable.getWriter();
    const escrito = w.write(bytes).then(() => w.close());
    const r = cs.readable.getReader(), partes = [];
    let n = 0;
    for (;;) { const { value, done } = await r.read(); if (done) break; partes.push(value); n += value.length; }
    await escrito;
    const out = new Uint8Array(n);
    let o = 0;
    for (const p of partes) { out.set(p, o); o += p.length; }
    return out;
  }
  async function zipUno(nombre, datos, fecha = new Date()) {
    const nom = new TextEncoder().encode(nombre);
    datos = datos instanceof Uint8Array ? datos : new TextEncoder().encode(String(datos));
    const comp = await deflateRaw(datos), crc = crc32(datos);
    // fecha y hora de MS-DOS (hora local, segundos de a 2)
    const hora = ((fecha.getHours() << 11) | (fecha.getMinutes() << 5) | (fecha.getSeconds() >> 1)) & 0xFFFF;
    const dia = (((Math.max(fecha.getFullYear(), 1980) - 1980) << 9) | ((fecha.getMonth() + 1) << 5) | fecha.getDate()) & 0xFFFF;
    const utf8 = /[^\x00-\x7f]/.test(nombre) ? 0x0800 : 0;
    const out = new Uint8Array(30 + nom.length + comp.length + 46 + nom.length + 22), v = new DataView(out.buffer);
    const campos = (base, lista) => lista.forEach(([o, x, n]) => (n === 4 ? v.setUint32(base + o, x, true) : v.setUint16(base + o, x, true)));
    // encabezado local
    campos(0, [[0, 0x04034b50, 4], [4, 20, 2], [6, utf8, 2], [8, 8, 2], [10, hora, 2], [12, dia, 2], [14, crc, 4],
      [18, comp.length, 4], [22, datos.length, 4], [26, nom.length, 2], [28, 0, 2]]);
    out.set(nom, 30); out.set(comp, 30 + nom.length);
    // directorio central
    const cen = 30 + nom.length + comp.length;
    campos(cen, [[0, 0x02014b50, 4], [4, 20, 2], [6, 20, 2], [8, utf8, 2], [10, 8, 2], [12, hora, 2], [14, dia, 2], [16, crc, 4],
      [20, comp.length, 4], [24, datos.length, 4], [28, nom.length, 2], [30, 0, 2], [32, 0, 2], [34, 0, 2], [36, 0, 2], [38, 0, 4], [42, 0, 4]]);
    out.set(nom, cen + 46);
    // fin del directorio central
    const fin = cen + 46 + nom.length;
    campos(fin, [[0, 0x06054b50, 4], [4, 0, 2], [6, 0, 2], [8, 1, 2], [10, 1, 2], [12, 46 + nom.length, 4], [16, cen, 4], [20, 0, 2]]);
    return out;
  }
  return { crc32, zipUno };
})();
if (typeof module === 'object' && module && module.exports) module.exports = ZipMin;
