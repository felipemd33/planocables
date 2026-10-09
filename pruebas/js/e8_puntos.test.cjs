'use strict';
/* Estación 8, etapa E8-5 (2026-10-08): puntos exactos de los bornes de las bandejas laterales en la pantalla
   (programa/web/estacion8.js sin tocar, con los instructivos congelados de pruebas/bases/ins_*.json).
   - TPT: la lateral derecha dice «todos con el punto del borne» y ninguna tarjeta dice «punto aprox.»; la línea plegable
     «Mapeo automático de bornes» con los modelos; la izquierda sigue con la batería 12PB1 aproximada;
   - 75287: los cables de 12XPS sin «punto aprox.»; 11MS1 (seccionador sin modelo) aproximado;
   - un punto ubicado con confianza media dice «a confirmar»;
   - PAE (EPLAN): sin la línea del mapeo automático (manda su mapeo verificado), todo con el punto del borne. */
const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('./comun.cjs');

function tarjetas(html) {
  return html.split('<div class="cab ').slice(1).map(p => '<div class="cab ' + p);
}
const claveDe = c => (c.match(/data-clave="([^"]*)"/) || [])[1];

for (const t of ['tpt', 'tpt_constructivo']) {
  test(`E8-5 ${t}: la lateral derecha con todos los puntos de los bornes; la batería aproximada`, async () => {
    const ins = C.leer(C.TRABAJOS[t]);
    const v = await C.vistaE8(ins);
    const iLD = ins.estacion8.laterales.findIndex(L => L.lado === 'LD'), iLI = ins.estacion8.laterales.findIndex(L => L.lado === 'LI');
    const ld = v.laterales[iLD];
    assert.ok(ld.includes('todos con el punto del borne'), 'FALLA: la lateral derecha no dice «todos con el punto del borne»');
    const cs = tarjetas(ld);
    assert.equal(cs.length, 42, `FALLA: ${cs.length} tarjetas en la lateral derecha`);
    assert.ok(cs.every(c => !c.includes('punto aprox.')), `FALLA: tarjetas con «punto aprox.»: ${cs.filter(c => c.includes('punto aprox.')).map(claveDe)}`);
    assert.ok(ld.includes('Mapeo automático de bornes') && ld.includes('33XAI</span> = PTTB4-HESI'), 'FALLA: falta la línea del mapeo automático con los modelos');
    const li = tarjetas(v.laterales[iLI]);
    const bat = li.filter(c => /12PB1 [+-]/.test(c));
    assert.ok(bat.length && bat.every(c => c.includes('punto aprox.')), 'FALLA: la batería 12PB1 tendría que seguir aproximada');
    assert.ok(li.filter(c => c.includes('WAGO con el cable propio')).every(c => !c.includes('punto aprox.')), 'FALLA: un WAGO dice «punto aprox.»');
  });
}

test('E8-5 75287: los cables de 12XPS con el punto del borne; 11MS1 aproximado', async () => {
  const ins = C.leer(C.TRABAJOS['75287']);
  const v = await C.vistaE8(ins);
  const cs = tarjetas(v.laterales[0]);
  const xps = cs.filter(c => />12XPS \d+ ABAJO</.test(c)), ms = cs.filter(c => />11MS1 (ARRIBA|ABAJO)</.test(c));
  assert.ok(xps.length >= 8 && xps.every(c => !c.includes('punto aprox.')), `FALLA: 12XPS con «punto aprox.» (${xps.length} tarjetas)`);
  assert.ok(ms.length && ms.every(c => c.includes('punto aprox.')), 'FALLA: 11MS1 tendría que seguir aproximado');
});

test('E8-5: un punto con confianza media dice «a confirmar» (con el porqué) y uno ajustado a mano no', async () => {
  const ins = C.leer(C.TRABAJOS['tpt']);
  const L = ins.estacion8.laterales.find(L => L.lado === 'LD');
  const ls = L.pasos.flatMap(p => p.lineas);
  ls[0].conf_o = 'media'; ls[0].nota_o = 'PTT2.5-2MT: medida del catálogo';
  ls[1].conf_o = 'usuario';
  const v = await C.vistaE8(ins);
  const cs = tarjetas(v.laterales[ins.estacion8.laterales.indexOf(L)]);
  const c0 = cs.find(c => claveDe(c) === ls[0].clave), c1 = cs.find(c => claveDe(c) === ls[1].clave);
  assert.ok(c0 && c0.includes('>a confirmar<') && c0.includes('PTT2.5-2MT: medida del catálogo'), 'FALLA: el punto «media» no dice «a confirmar» con el porqué');
  assert.ok(c1 && !c1.includes('>a confirmar<') && !c1.includes('punto aprox.'), 'FALLA: el punto ajustado a mano no tendría que decir nada');
});

test('E8-5: «Modelos» del plegable solo con los aparatos que tienen algún borne ubicado (66817, batería del TPT)', async () => {
  // 66817: el motor no ubica ningún borne en las laterales (la LD tiene el riel vertical): sin «Modelos:» (antes decía
  // «12PB1 = DF101», la batería como portafusible, contra el aviso de abajo)
  const i6 = C.leer(C.TRABAJOS['66817']);
  const v6 = await C.vistaE8(i6);
  let vistas = 0;
  v6.laterales.forEach((h, k) => {
    const nom = i6.estacion8.laterales[k].nombre;
    if (!h.includes('Mapeo automático de bornes')) return;
    vistas++;
    const pleg = h.split('Mapeo automático de bornes')[1].split('</details>')[0];
    assert.ok(!pleg.includes('Modelos:') && !/DF101|PTT2\.5-2MT/.test(pleg), `FALLA: ${nom} del 66817 nombra un modelo sin ningún borne ubicado`);
    assert.ok(!/ningun |catalogo/.test(pleg) && pleg.includes('ningún modelo del catálogo'), `FALLA: ${nom} del 66817 con avisos sin tildes`);
  });
  assert.equal(vistas, 2, `FALLA: el 66817 tendría que tener el plegable en las 2 laterales (${vistas})`);
  // TPT: la lateral izquierda (batería sin modelo) sin «Modelos:»; la derecha con los suyos
  const it = C.leer(C.TRABAJOS['tpt']);
  const vt = await C.vistaE8(it);
  const li = vt.laterales[it.estacion8.laterales.findIndex(L => L.lado === 'LI')];
  const ld = vt.laterales[it.estacion8.laterales.findIndex(L => L.lado === 'LD')];
  assert.ok(li.includes('Mapeo automático de bornes') && !li.includes('Modelos:'), 'FALLA: la lateral izquierda del TPT nombra un modelo para la batería');
  assert.ok(ld.includes('Modelos:') && ld.includes('13XC2</span> = PT6-QUATTRO'), 'FALLA: la lateral derecha del TPT perdió sus modelos');
});

test('E8-5 PAE: sin el mapeo automático de las laterales (manda el mapeo verificado)', async () => {
  const ins = C.leer(C.TRABAJOS['76884']);
  const v = await C.vistaE8(ins);
  assert.ok(!v.laterales[0].includes('Mapeo automático de bornes') && v.laterales[0].includes('todos con el punto del borne'),
    'FALLA: el PAE no tendría que tener la línea del mapeo automático y tiene que seguir con todos los puntos');
});
