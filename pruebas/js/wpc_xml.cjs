'use strict';
/* Ayudante de prueba (NO es del programa): emula lo que hace el programa de la WPC (Weidmüller) al importar el CSV y
   guardar el .wpc, y lee el XML de un .wpc real. Es la especificación del archivo .wpc para la etapa 3 del plan modular.

   Reglas de la importación (sacadas de los .wpc reales del taller, PLAN_MODULAR.md 5.5):
   - columna 9 (sección) con 2 decimales y punto: '2,5' → '2.50';
   - columna 21 (marcador) vacía → por sección: ≤ 1 mm² → MARCADOR.chico; de 2,5 a 6 mm² → MARCADOR.grande;
     otra sección (no hay en los datos de hoy) → vacía;
   - columnas 29 y 30 (AWG y pulgadas) → '0';
   - vacío → '0' en las columnas 7-9 y 23-49; el resto tal cual;
   - XML plano en UTF-8, sin BOM ni declaración: raíz <WPC Version="1.0" ProjectName="…" pdfFile="" UserFilter="-1">,
     una fila por cable <RowN Col1="…" … Col49="…" />, sangría de 2 espacios, CRLF entre líneas y sin salto al final.
   El .wpc es un zip con una sola entrada (deflate) que se llama igual que el archivo.

   API: xmlDesdeCsv(csv, proyecto, {userFilter, marcador}) · leerWpc(rutaOBytes) -> {nombre, xml, bytes, crcOk, ...}
        atributosRaiz(xml) · filasXml(xml) -> [[Col1..Col49]] */
const fs = require('node:fs'), zlib = require('node:zlib');

const NCOL = 49;
const MARCADOR = { chico: '1423340000; HSS-HF 1.6-3.2 EL W13M', grande: '1423360000; HSS-HF 3.2-6.4 EL W13M' };
const A_CERO = new Set([7, 8, 9, ...Array.from({ length: 49 - 23 + 1 }, (_, i) => 23 + i)]);

function marcadorPorSeccion(sec) {
  const s = parseFloat(String(sec).replace(',', '.'));
  if (!Number.isFinite(s)) return '';
  if (s <= 1) return MARCADOR.chico;
  if (s >= 2.5 && s <= 6) return MARCADOR.grande;
  return '';
}
const escXml = v => String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// filas del CSV de wpc.js: BOM, ';' y CRLF al final de cada fila
function filasCsv(csv) {
  return String(csv).replace(/^﻿/, '').split('\r\n').filter(l => l !== '').map(l => l.split(';'));
}

function xmlDesdeCsv(csv, proyecto, op = {}) {
  const uf = op.userFilter ?? '-1', marcador = op.marcador || marcadorPorSeccion;
  const out = [`<WPC Version="1.0" ProjectName="${escXml(proyecto)}" pdfFile="" UserFilter="${escXml(uf)}">`];
  filasCsv(csv).forEach((c, i) => {
    const v = c.concat(new Array(NCOL).fill('')).slice(0, NCOL);      // v[k-1] = columna k
    if (v[8] !== '') v[8] = parseFloat(v[8].replace(',', '.')).toFixed(2);
    if (v[20] === '') v[20] = marcador(v[8]);
    v[28] = '0'; v[29] = '0';
    for (const k of A_CERO) if (v[k - 1] === '') v[k - 1] = '0';
    out.push(`  <Row${i + 1} ` + v.map((x, j) => `Col${j + 1}="${escXml(x)}"`).join(' ') + ' />');
  });
  out.push('</WPC>');
  return out.join('\r\n');
}

// ---- lectura de un .wpc (zip de una entrada), sin bibliotecas: directorio central + inflateRaw + CRC-32
function leerWpc(arch) {
  const b = Buffer.isBuffer(arch) ? arch : fs.readFileSync(arch);
  let fin = -1;
  for (let i = b.length - 22; i >= Math.max(0, b.length - 22 - 65535); i--) if (b.readUInt32LE(i) === 0x06054b50) { fin = i; break; }
  if (fin < 0) throw new Error('no es un zip (falta el fin del directorio central)');
  const entradas = b.readUInt16LE(fin + 10), cen = b.readUInt32LE(fin + 16);
  if (b.readUInt32LE(cen) !== 0x02014b50) throw new Error('directorio central roto');
  const metodo = b.readUInt16LE(cen + 10), crc = b.readUInt32LE(cen + 16), comp = b.readUInt32LE(cen + 20), tam = b.readUInt32LE(cen + 24);
  const nl = b.readUInt16LE(cen + 28), nombre = b.toString('latin1', cen + 46, cen + 46 + nl), loc = b.readUInt32LE(cen + 42);
  if (b.readUInt32LE(loc) !== 0x04034b50) throw new Error('encabezado local roto');
  const ini = loc + 30 + b.readUInt16LE(loc + 26) + b.readUInt16LE(loc + 28);
  const crudo = b.subarray(ini, ini + comp);
  const datos = metodo === 8 ? zlib.inflateRawSync(crudo) : metodo === 0 ? Buffer.from(crudo) : null;
  if (!datos) throw new Error('compresión no soportada: ' + metodo);
  return { nombre, entradas, metodo, tam, crcOk: datos.length === tam && zlib.crc32(datos) === crc, bytes: datos, xml: datos.toString('utf8') };
}

function atributosRaiz(xml) {
  const m = /^<WPC ([^>]*)>/.exec(xml);
  return m ? Object.fromEntries([...m[1].matchAll(/(\w+)="([^"]*)"/g)].map(x => [x[1], x[2]])) : null;
}
const desEsc = v => v.replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
function filasXml(xml) {
  return xml.split('\r\n').filter(l => /^ {2}<Row\d+ /.test(l)).map(l => [...l.matchAll(/Col(\d+)="([^"]*)"/g)].map(m => desEsc(m[2])));
}

module.exports = { MARCADOR, marcadorPorSeccion, xmlDesdeCsv, filasCsv, leerWpc, atributosRaiz, filasXml };
