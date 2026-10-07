'use strict';
/* Para que ande «node --test pruebas/js/»: Node 24 toma la carpeta como un solo archivo de prueba y carga este index.js,
   que carga todas las pruebas *.test.cjs de la carpeta. (Con «node --test "pruebas/js/*.test.cjs"» corren igual, sin este
   archivo; en Node 20, que recorre la carpeta, este archivo no se carga porque no se llama *.test.*.) */
const fs = require('node:fs'), path = require('node:path');
for (const f of fs.readdirSync(__dirname).filter(f => f.endsWith('.test.cjs')).sort()) require(path.join(__dirname, f));
