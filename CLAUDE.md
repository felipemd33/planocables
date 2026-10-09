# Listado de cables e instructivo de cableado (taller Batfer)

Herramienta propia del taller de Batfer (Uruguay), que arma tableros eléctricos. El usuario es Spanish-speaking: **toda la
interfaz, los textos para el taller y los mensajes van en castellano rioplatense** (vos, "tocá", "cargá").

Lee planos eléctricos vectoriales y hace dos cosas:
1. Un **PDF buscable** y el **listado de cables** (número, color, sección), sin OCR. En AutoCAD las letras son trazos SHX y
   se reconocen por firma exacta (`programa/glyphdict.json`).
2. El **instructivo de cableado de la bandeja** (estación E6): cada cable sale del punto exacto del borne en el
   topográfico y va por los cablecanales. Incluye el visor "cablear de a uno" y la auditoría cruzada.

## Estructura

| Carpeta / archivo | Qué es |
|---|---|
| `programa/web.py` | Interfaz web (Flask, `http://127.0.0.1:8765`). `PLANOCABLES_PORT` cambia el puerto; `--no-abrir` no abre el navegador. |
| `programa/planocables/` | Paquete del **plan modular** (`PLAN_MODULAR.md`, etapas 0-3 hechas): `base/` (geom, hojas, convenciones, colores, escala, pdfium_lock: funciones puras, solo biblioteca estándar; los módulos viejos las reexportan con el mismo nombre) y `producto.py` (código de producto, plano y revisión, sin disco). `pyproject.toml` (en la raíz) instala solo este paquete. |
| `programa/productos.json` | Catálogo de productos: `{código: {nombre, alias: {planos, documentos, codigo_rotulo}}}`. Lo actualiza la web cuando el taller confirma un producto (✎ en la línea «Producto»). |
| `programa/estacion8.py`, `estacion8_mano.py`, `web/estacion8.js`, `web/e8mano.js` | **Estación 8** (gabinete): bandejas laterales, puerta y placa (`estacion8.build`), y el **ruteo a mano por grupos** (E8-6): tabla editable `web/e8_grupos.json` y lo dibujado por producto en `recorridos_e8.json` (lo escribe la web; `PLANOCABLES_RECORRIDOS_E8` en las pruebas). |
| `programa/core.py`, `wires.py`, `textdec.py`, `pdfvec.py` | Lector del funcional: textos SHX, cables, números, uniones en T y flechas a otras hojas. |
| `programa/instructivo.py` | Puntas (`describe_end`), conductores (`conductors`), textos (`fmt_terminal`) e instructivo (`build`): orden, pasos, pendientes LI↔LI y estaciones. Además `usos_bandeja` y `materiales_funcional`. |
| `programa/topo.py`, `ruteo.py` | Topográfico (página de la bandeja, rieles, canaletas, escala, componentes) y ruteo por canaletas (Dijkstra). |
| `programa/bornes/` | Mapeo automático del **punto exacto de cada borne**: `motor.py` + `catalogo.json` (modelos en mm, con sus códigos SAP) + `primitivas.py`. `aparamenta.json` / `aparamenta.py`: el Excel de SAP «BOMs por estación» con lo que es cada material. `pines_repetidos.json`: nombre del n-ésimo pin repetido por familia (cargador: panel, batería, carga; lo usa la E8 para los WAGO). Ver `programa/bornes/LEEME.md`. |
| `programa/eplan.py` | Planos de **EPLAN** (PDF con texto real): `es_eplan`, `process` (lista de conexiones → conductores y listado, misma interfaz que `core.process`), `layout` (hoja de bandejas: rieles, canaletas, placas, etiquetas → mismo formato que `topo.layout`) y `aplicar_puntos` (mapeo verificado). `core.process` y `topo.layout` derivan solos a este módulo. |
| `programa/mapeos_verificados/` | **Dato** por producto EPLAN: `<documento>_rev<revisión>.json` con el punto exacto y el texto del taller de cada punta (`'<designación EPLAN>#<cable>'`), los aparatos que se cablean en E8 (zona hidráulica, batería, solenoides) y las canaletas de intrínsecos. Se elige por el documento y la revisión del rótulo. Se arma con `2 - Resultados/76884 mSafe2+ PAE/mapeo/exportar_al_programa.py`. |
| `programa/web/*.js` | Interfaz: `app.js` (listado y visor del funcional), `instructivo.js` (pestaña instructivo y visor de cablear), `auditoria.js`, `salidas.js` (editor de salidas a LI / LD), `producto.js` (línea «Producto» y su asistente), `wpc.js` (pantalla de la lista WPC). |
| `programa/web/nucleo/` | Núcleo JS sin DOM (carga con `<script>` en el navegador y con `require` en Node): `wpc_core.js` (la lógica de la lista WPC: configuración por niveles, filas, largos, `canaleta()`, CSV, XML y nombre del `.wpc`) y `zip.js` (zip mínimo de una entrada para el `.wpc`). |
| `programa/proyector.py`, `web/proyector.html`, `proyector.js`, `proyector.css` | **Pestaña 📽 Proyector** (`/proyector/<id>`, botón 📽 en el instructivo y en el visor, tecla P): proyecta sobre la bandeja REAL solo las canaletas y el cable actual (origen verde lima, destino cian). Sigue al visor «cablear de a uno» por `BroadcastChannel('planocables')` y le devuelve las teclas → ← Espacio. Calibración por homografía (`matrix3d`) con los 4 **orificios de montaje** de la placa: `proyector.orificios` los busca en el dibujo (símbolo de cada esquina; centro = mediana de las mediatrices de sus segmentos), con 🎯 en el visor se marcan a mano. Ventana de texto (puntas, terminal, a dónde va) movible y de tamaño ajustable, que arranca en la parte vacía de la bandeja. Todo se guarda en `ins['proyector']` por `GET/PUT /api/trabajo/<id>/proyector` (la ventana principal no pisa esa sección). |
| `1 - Planos/` | Planos originales. `Catalogo (referencia)/`: 8 productos con su orden de montaje SAP. `Producto nuevo/`: mSafe2+ PAE (EPLAN). |
| `2 - Resultados/` | Salidas. `76884 mSafe2+ PAE/`: mapeo verificado del producto EPLAN (ver abajo). |
| `3 - Historial web/<id>/` | Trabajos de la web (plano, `layout.json`, `instructivo.json` con las marcas del usuario, `bornes.json` manual, `correcciones.json`, `bornes_auto.json`, `bornes_e8_auto.json` de las laterales). **No pisar las marcas del usuario.** |
| `prototipos/` | Los 5 prototipos de mapeo de bornes. `_referencia/` es la referencia del 75286; `_referencia_66817/` la del 66817. |
| `pruebas/` | Regresión: `volcar_trabajo.py`, `volcar_cables.py`, `evaluar_bornes.py` y `bases/`. Red de seguridad del plan modular: `bateria.py` (corre todo), `comparar_bases.py`, `volcar_bases_nuevas.py`, `ab_planos.py` (A/B sobre todos los planos de `1 - Planos`), `probar_capas.py` (capas de `planocables`), `probar_puentes.py` (los nombres viejos siguen), `probar_producto.py`, `probar_web_humo.py` (la web con Flask y con pythonw), `js/` (`node --test`: WPC, terminal, XML del `.wpc`) y `fixtures/` (copias fijas de solo lectura: el PAE del usuario, el `.wpc` real, `productos.json` y `wpc.json`; ver `fixtures/LEEME.md`). |
| `PLAN_MODULAR.md` | Plan de la modularización: capas, contratos, producto, WPC por producto, etapas y batería B. |
| `pendiente/` | Trabajo empezado y pausado (ver "Pendientes"). |

Correr la web: `python programa/web.py --no-abrir` (requisitos en `requirements.txt`). En Windows: `Listado de cables (web).bat`.
**Los cambios en Python necesitan reiniciar el servidor; los .js/.css se ven recargando la página.**

## Reglas del taller (obligatorias)

- **El FUNCIONAL es la guía principal.** El instructivo y la auditoría tienen que coincidir siempre con él.
- **Formato de línea:** `1110: N2.5MM 11PS1 1 (-) → LI`. Es número, inicial del color + sección + MM, origen y destino.
  Más ejemplos: `1106: M2.5MM 11Q2 F ARRIBA → 11Q1 F ABAJO`, `2118: N0.75MM 43KR1 11 → LI`.
- **LI** = lateral izquierdo, puerta, campo: todo lo que no está en la bandeja. **LD** = lateral derecho.
  - Cables LI↔LI: no van en el instructivo de la bandeja. Van a "pendientes" y se cablean al montar.
  - **Salida a LI / LD:** sin elegir, la regla del taller (`ruteo.li_exit`: por el lateral, arriba; marrón y blanco
    de 220 VAC por abajo; intrínsecos por su canaleta). En la web se elige a mano por grupo (botón 🧭 Salidas LI / LD,
    o 🧭 Salida / tecla S en el visor): «Todos los LI», «Todos los LD» o un grupo de cables elegidos (manda sobre el de
    su lateral). Recorrido = puntos por donde pasan y, el último, por donde salen. Se guarda en `ins['salidas']`, se
    conserva al regenerar (`instructivo.grupo_salida`) y la vista previa usa `/instructivo/salidas`
    (`instructivo.rutear_salidas`, sin rearmar). Los intrínsecos no entran en «todos»: se cambian eligiéndolos en un grupo.
    Al cargar un topográfico (o las bandejas del mismo PDF de EPLAN) se borran las salidas viejas y queda
    `salidas.preguntar`: la primera vez que se abre el instructivo, un asistente pregunta una sola vez la salida de LI y la de LD.
- **Un tag nombra los bornes que tiene a su DERECHA** hasta el próximo tag. En el funcional, con la bornera en columna,
  vale para los de abajo.
- **QUATTRO:** `N.p`, con 1 y 2 arriba (1 = extremo, 2 = interior) y 3 y 4 abajo (3 = interior, 4 = extremo).
  - Si un número tiene dos borneras, la de la izquierda es N.1-N.4 y la segunda N.5-N.8.
- **Doble piso / 2 puntos:** `N ARRIBA` / `N ABAJO`. Impar = piso de abajo (boca del extremo), par = piso de arriba.
  - En el funcional, un borne dibujado en horizontal tiene la izquierda = ARRIBA.
  - Con punto exacto, el texto lleva el **lado físico**.
- **Relés en módulos:** `43KR1 11`, `A1`. Contactos 11/14/12 de un lado y bobina A1/A2 del otro.
- **Pines con el mismo nombre en varios tornillos** (ej. TB2 `-Vo -Vo +Vo +Vo`): el n-ésimo borne de ese nombre en el
  símbolo del funcional va al n-ésimo tornillo.
- **Un número con 3 o más puntas NO es un error:** es un puente o derivación a propósito en un borne (unión en T).
  - Va con terminal doble.
  - En una unión con tramo en diagonal, la unión va en el borne hacia donde apunta la diagonal.
  - Un cable de N puntas son N-1 tramos reales, no todos los pares.
- **Orden de cableado: primero los cables que quedan DEBAJO de otros.**
  - Relé: 11 → 14 → 12; abajo A2 → A1.
  - QUATTRO: 1 → 2 y 4 → 3.
  - Doble piso: impar → par.
  - Barreras: el enchufe de afuera primero.
  - Riel por riel de arriba abajo; en cada riel, primero la parte de arriba de izquierda a derecha y después la de abajo.
  - Los bancos de módulos iguales van capa por capa; las borneras, aparato por aparato.
- **Terminales (pollera):** pino 0,5 blanco · 0,75 celeste · 1 rojo · 2,5 azul · 4 naranja · 6 verde. Doble 1 mm² rojo,
  doble 2,5 mm² gris. Tabla editable en `programa/web/terminales.json`.
- **Estaciones:**
  - **E6** = bandeja.
  - **E8** = gabinete. Incluye:
    - el cableado entre bandejas, placa, puerta, botones y selectora;
    - los **cables de 35 mm²**;
    - la **zona hidráulica** (MEGA, bomba, válvula, PT001, nivel) y los empalmes del sensor de nivel;
    - la **batería** (12PB1) y las **solenoides** (SP_1/2/3) del PAE (2026-10-06, pedido del usuario): sus cables no se
      cablean en E6 ni van a la lista WPC. Mecanismo: `estaciones_tag` del mapeo verificado (`ZONA_E8` en
      `exportar_al_programa.py`); en los planos de AutoCAD las solenoides `SP-n` ya salen como campo (`FIELD_RE`).
  - **Visor de E8, etapa E8-1 «laterales completas» (2026-10-08, pedido del taller):** cada bandeja lateral es su PLACA
    entera (`topo.vistas_e8`, claves aparte de cada vista: `placa`, `ductos`, `titulo`, `rieles_e8`; la bandeja de E6 no
    cambia): rectángulo cerrado de cualquier capa que junta más canaletas y aparatos de afuera de la bandeja; riel
    TAPADO por los aparatos = fila de 3 o más etiquetas alineadas entre dos canaletas (solo E8); lateral SIN riel = placa
    con título lateral y canaletas o aparatos (`rails: []`, pasos aparato por aparato). Punto aproximado del borne del
    lado de `side_of` (como E6) y medidas escaladas con kr. Un cable de una lateral a la otra sale en las dos (misma
    marca); con canaletas partidas sale por la horizontal de su parte de la red. Cambian los largos de la WPC de los
    cables a las laterales (decisión del taller: directo; tabla en `pruebas/bases/wpc/cambios_e8.md`).
  - **Etapa E8-2 «entrada a las laterales y bisagra» (2026-10-08, decisiones del taller):** la bisagra de la puerta
    depende del producto (se elige una vez por trabajo) y la entrada a cada lateral se pregunta la primera vez. Dato:
    `ins['estacion8']['recorridos'] = {preguntar, bisagra: 'izq'|'der'|None, vistas: {<clave_vista>: {entrada, puerta,
    grupos: [{id, nombre, cables, puntos}]}}}` (clave estable = lado + título normalizado, `estacion8.clave_vista`).
    Se conserva al regenerar (`lay['recorridos_e8']`, después de `instructivo.build`) y un topográfico nuevo lo borra y
    pone `preguntar` (la primera vez también). Ruteo (`estacion8.rutear_lineas`): manda un grupo de cables elegidos;
    en la lateral del lado de la bisagra los que siguen a la puerta (`a_puerta` = la otra punta es de «puerta / placa» y
    su aparato NO está dibujado en el topográfico) salen por `puerta` (o la propuesta: la regla del taller por el borde
    del lado de la puerta); el resto (de E6, de la otra lateral, del fondo; y los de la otra lateral que van a la
    puerta: cruzan el fondo) por `entrada` (o la propuesta: a la altura de la salida de E6 del mismo lado si las vistas
    están alineadas en la hoja y hay canaleta a esa altura; si no, `li_exit` del lado del fondo). Sin bisagra elegida no
    hay salida a la puerta. Si lo elegido no llega por las canaletas, sale por la propuesta (`no_llega`, con aviso).
    Vista previa: `POST /api/trabajo/<id>/e8/recorridos` (`estacion8.rutear_guardado`, sin rearmar). Pantalla: asistente
    (bisagra con la propuesta `BISAGRA_PROPUESTA` = izquierda, como el TPT; después la entrada de cada lateral con la
    flecha roja de la propuesta y clics sobre el dibujo: «Usar la propuesta», «Siguiente», «Listo») y botón
    «🧭 Entrada / salida» (tecla S, también en el visor) con la bisagra, los grupos y un grupo de cables elegidos. Sin
    elegir, las rutas son las de E8-1 (`e8_*` igual salvo las claves nuevas) y la WPC no cambia; elegir la entrada SÍ
    cambia el largo de la WPC de los cables a esa lateral (canaleta de la lateral).
  - **Etapa E8-3 «WAGO del cargador» (2026-10-08, decisiones del taller; regla: manda el DIBUJO del funcional, no el
    aparato):** un cable numerado que llega al pin de un aparato a través de un empalme dibujado se empalma con un
    **WAGO** con el cable propio del aparato; **la punta va pelada (sin pino)**. Lector (`instructivo.py`): campo nuevo
    en la punta `'empalme_dibujado': {tipo: 'wago', simbolo: 'relleno' | 'partido', p, orden, de, aparato_txt}` (el
    TEXTO de la punta y todo E6 no cambian): ■ al final del recorrido (`describe_end` con `_seguir_empalme`, Shell 75206)
    o atravesado por el recorrido entre el pin y el primer número del cable (`empalme_en_tramo`: ■ = relleno chico como
    el de `seguir_empalme`, 66817; ⊟ = rectángulo partido por una raya perpendicular al cable, sin texto adentro, TPT;
    `seguir_empalme` no se agrandó; el punto relleno de una unión en T, cuadrado bajo un círculo, no cuenta). En los
    planos de `1 - Planos`: TPT (3 versiones), 66817 y Shell = los 4 cables del cargador; 75287, PP, FCS, dFRAC y PAE = 0.
    E8 (`estacion8.py`, versión 4): línea con `empalme` (`empalme_d` en la otra punta de un cable de la misma lateral) =
    {tipo, texto, aparato, pin, n, confirmar, pelado, simbolo, p, fin, entra}; tarjeta «WAGO con el cable propio de
    12PS2 · + panel», terminal «pelado (sin pino)», sin «punto aprox.». El pin, por la regla de los pines repetidos
    (`instructivo.pin_en_simbolo`: el n-ésimo pin con ese rótulo en la fila de pines del recuadro del aparato) con los
    nombres de su familia en `programa/bornes/pines_repetidos.json` (cargador: panel, batería, carga; la familia sale del
    renglón de la lista de materiales o de los textos del recuadro del aparato, con los patrones de `catalogo.json`). El
    WAGO queda **debajo del aparato, a la salida de la canaleta**: la punta libre de canaleta más cercana por debajo de
    su etiqueta (`estacion8.punto_empalme`); el recorrido va por las canaletas hasta ahí (`ruteo.route_line` con
    `o_red`/`d_red`: arranca en la punta de la canaleta) y un trazo punteado del WAGO al aparato es el cable propio. Los
    empalmes del mismo aparato van uno al lado del otro, en el orden de los pines. La punta EMPALME del RS-485
    (`empalme_en_rama`, «EMPALME con 12PS2») va junto a su aparato en la lateral; con 3 conductores (2 tramos numerados +
    el cable propio) queda **«Empalme de 3, a confirmar»** (terminal a confirmar). Los pines sin cable no se muestran;
    `e8_clave` y las marcas no cambian. WPC: misma regla (la acometida del WAGO es la de un borne, 150); cambian los
    largos por la E8 bien armada (tabla en `pruebas/bases/wpc/cambios_e8_3.md`).
  - **Etapa E8-4 «puerta» (2026-10-08, foto 3 del taller):** lectura general de la vista de la PUERTA
    (`topo.puerta_e8`, versión del lector `2026.10.08-e8p`): hoja sin rieles (o vista de la hoja de la bandeja que no
    la toca) con un título `PUERTA` arriba de un rectángulo cerrado (lado corto > 5 perfiles) que tiene canaletas o
    etiquetas del funcional; la exterior y el índice no cuentan. Los títulos se buscan sin OCR (`_texto_sin_ocr`) y la
    hoja elegida se relee con OCR. Va en una clave aparte, `lay['puerta'] = {pag, box, titulo, ductos, rieles, comp:
    {tag: {x, y, leido, etiqueta, cuerpo}}}` (cuerpo = el rectángulo cerrado más chico que contiene la etiqueta; no suma
    cotas ni compite por la hoja de la bandeja). TPT (los dos) y 66817: hoja 8 «PUERTA DETALLE DE RIELES Y DUCTOS»
    (canaleta 40x40, 21PCB01 con su placa, 13SH1); 75287 (75441): hoja 5 «VISTA POSTERIOR PUERTA» (13SH1, 46DB1; la
    placa no tiene etiqueta); PAE: no (EPLAN, después). E8 (`estacion8.py`, versión 5): `e8['puerta']` con la forma de
    una lateral (pasos por aparato, líneas con las MISMAS claves que su tabla de «Puerta y placa», que sigue igual con
    `en_puerta`); cada cable entra del lado de la bisagra (vista INTERIOR: bisagra izquierda = borde DERECHO del dibujo,
    `estacion8.borde_bisagra`; sin elegir la bisagra, la propuesta), por arriba de la punta de la canaleta, y llega a la
    **franja de bornes** de su aparato (el lado de abajo o de arriba del cuerpo que mira al tramo común; sin cuerpo, la
    etiqueta): no se inventan bornes, el borne está en la tabla. Elegido a mano en `recorridos['vistas']['PUERTA'] =
    {entrada: [p], paso: [puntos de paso del tramo común, libres: también fuera de las canaletas], grupos}`; cada cable
    sale del tramo común en el punto más cercano a su aparato (foto 3: baja por la canaleta, corre por el perfil de abajo
    y sube a la placa). Vista previa: el mismo `POST /e8/recorridos` devuelve además `puerta`
    (`estacion8.rutear_guardado_puerta`); imagen `/api/trabajo/<id>/e8/puerta.png`. En la lateral de la bisagra, capa
    **«Pasan hacia la puerta (N)»** (`L['transito']`, fuera de los pasos): el haz de los que siguen a la puerta desde la
    bandeja principal o la otra lateral (`e8['hacia_puerta']`), de la entrada a la salida a la puerta. «Sigue a la
    puerta» = aparato de la vista de la puerta o sin dibujar en el topográfico (con lo que no está dibujado en ninguna
    hoja, como BH-01-M o ZY, sigue la regla de E8-2). Pantalla: «Puerta y placa» con el dibujo arriba de las tablas,
    ▶ Cablear de a uno en la puerta y 🧭 Entrada / recorrido (S). **La WPC NO usa la vista de la puerta** (sigue el
    1850 fijo; con y sin `lay['puerta']` las laterales y las tablas dan igual).
  - **Etapa E8-5 «puntos exactos en las laterales» (2026-10-08, propuesta B.4):** el motor de `bornes/` corre por cada
    lateral (`estacion8.mapear_bornes` → `bornes/laterales.py`, `MotorLateral`: region = la PLACA de la lateral; rieles =
    los de la capa del riel o, si no hay, los rectángulos con el perfil del riel de la bandeja en cualquier capa
    (`topo.rieles_geometria`: el riel 1 de la LD del TPT en la capa '0'), más los ejes de la vista sin tramo (el riel
    TAPADO, `rieles_e8`) a lo ancho de las canaletas horizontales que lo encierran). Usos: `instructivo.usos_bandeja(...,
    tags=<los de la lateral>, region=<placa>)` sin las puntas con WAGO. Resultado en claves aparte, DESPUÉS de
    `instructivo.build` (no entran al layout de las bases): `lay['bornes_e8']` ('texto del funcional#cable' → [x, y, r]),
    `bornes_e8_conf` (alta / media), `bornes_e8_nota`; **no renombra textos** (un borne que el motor ubica en otro bloque
    o módulo queda aproximado con aviso): E6 y sus pendientes no cambian. Caché aparte: `<trabajo>/bornes_e8_auto.json`
    (una entrada por lateral, con su firma). EPLAN no lo usa (manda su mapeo verificado). `estacion8.punto` (versión 6):
    `bornes_usuario` (ajustado a mano) > `lay['bornes']` (bornes.json, correcciones, mapeo verificado) > `bornes_e8` >
    aproximado. El aproximado de un borne de una **bornera** (tag con X, número solo) con otros bornes exactos del mismo
    lado del riel sale de ellos con su paso (`afinar_aproximados`, `aprox_o` / `aprox_d` = 'vecinos'), no de la
    etiqueta: el orden de izquierda a derecha cuadra (75287: 11XP 3, la PE, a la derecha del 11XP 2; 1101 → 1102 →
    1103). La línea lleva `conf_o` / `conf_d` ('usuario', 'alta', 'media') y `nota_o` / `nota_d`, y `lado_d` en
    los cables de la misma lateral; `e8['mapeo']` = {vistas: [{clave, nombre, puntos: {alta, media, baja}, usados,
    modelos (solo los aparatos con algún borne ubicado: el plegable «Mapeo automático de bornes» no nombra el modelo que
    el motor eligió para un aparato sin ningún punto), rieles, rieles_agregados, avisos (con tildes: `_tildes`; el motor
    no se toca)}]}; aviso por lateral de las puntas que siguen aproximadas. Resultado:
    TPT LD 0 → 42 de 42 (LI: 12PB1 aproximada, la batería no está en el catálogo; el cargador va con WAGO); 75287 LI
    0 → 12 de 15 (11MS1, seccionador sin modelo, y 11XP 3, la pieza PE, aproximados); 66817 igual (LD con el riel VERTICAL: el motor no lo cubre,
    aproximada con aviso); PAE igual. **Ajuste a mano** en el visor de E8: 📍 Origen / 📍 Destino (clic en el borne o
    arrastrar el punto; Esc cancela), se guarda en `ins['bornes_usuario']` como en E6 y manda al regenerar; el recorrido
    lo recalcula `POST /api/trabajo/<id>/e8/punto` (`estacion8.rutear_punto`, sin rearmar). La WPC cambia por las rutas
    nuevas (tabla en `pruebas/bases/wpc/cambios_e8_5.md`).
  - **Etapa E8-6 «ruteo a mano por grupos» (2026-10-09, pedido del taller):** los cables de **solenoides, contactora
    (la BOBINA del contactor de la bomba: el cable de 1 mm² que hace de llave de paso), batería 35 mm², batería 4 / 6 mm²,
    doorswitch, pulsadores, selectoras, llaves seccionadoras y cada placa** NO se rutean solos: el recorrido lo DIBUJA el
    taller (clics) y hasta entonces el visor dice «falta dibujar el recorrido» (sin ruta inventada; los demás cables de
    E8 siguen como antes). `programa/estacion8_mano.py` + tabla EDITABLE `programa/web/e8_grupos.json` (categorías en
    orden: un cable cae en la PRIMERA que le corresponde y en una sola; criterios: sección, pines A1/A2, texto del aparato
    = renglón de la lista de materiales del funcional + el material de `bornes/aparamenta.json` que nombra su código de
    fabricante, familias del catálogo y, SIN texto, las letras del tag de la tabla: PB, ZY/ZV/SP-n, DS, DB, SH, MS, PCB;
    una bornera nunca es el aparato del grupo; la contactora se reconoce por sus cables: 35 mm² + la bobina chica).
    `estacion8.build` (versión 7) arma `e8['ruteo_mano']` = {categorias, vistas (las laterales por `clave_vista`,
    'PUERTA', 'FONDO'), auto, auto_info, cables: {clave: {num, a, b, puntos: {vista: [[x, y]]}}}} y `e8['fondo']` (la
    bandeja principal con lo dibujado alrededor: la zona hidráulica; imagen `/e8/fondo.png`); `web.gen_instructivo` le
    suma lo del taller (`estacion8_mano.cargar_y_aplicar`: grupos, miembro, manual, avisos) y marca `grupo_mano` en las
    líneas (laterales, puerta y tablas). **La ruta automática de las laterales queda en la línea (la usa la WPC); el visor
    no la dibuja para un cable con grupo. La WPC no usa estos largos.** Recorrido = TRAMOS por vista ({vista, puntos}),
    con 🧲 pegar al eje de la canaleta. Correcciones: `mover` {clave: grupo | '' = sin grupo, ruteo automático} y
    `nuevos` (grupos de placa). **Se guarda POR PRODUCTO** (código + número y revisión del topográfico de
    `ins['producto']`) en `programa/recorridos_e8.json` (`PLANOCABLES_RECORRIDOS_E8` en las pruebas; escritura atómica con
    `.bak` y `version`: si otro trabajo lo cambió, 409 y la pantalla recarga), `GET / PUT /api/trabajo/<id>/e8/grupos`;
    con el producto sin confirmar o sin el topográfico, en el trabajo (`estacion8.mano_trabajo`, lo escribe solo
    /e8/grupos) y pasa al producto al confirmarlo. Pantalla: botón **✏ Ruteo a mano** (tecla R, también desde el visor;
    `programa/web/e8mano.js`): grupos con su estado y cantidad, dibujar / borrar / listo, mover un cable con la lista,
    ＋ Grupo de placa, «▶ Cablear de a uno» por grupo; la tarjeta, la tabla y el visor dicen el grupo de cada cable.
    El tránsito «Pasan hacia la puerta» (E8-4) no cambia. **Cables DIRECTOS** (dato del taller: en el PAE y la Vista,
    debajo del cargador hay borneras para no usar WAGO): un cable de la misma lateral entre un cargador (`directo` en
    e8_grupos.json; sin lista de materiales, letras PS) y una bornera a menos de 2 perfiles, sin canaleta en el medio, va
    derecho al borne (`directo`, sin grupo): PAE 1221-1226 y el RS-485 a 12XPS. Cambia la WPC del PAE (750 → 450 mm,
    tabla en `pruebas/bases/wpc/cambios_e8_6.md`); el 75287 no tiene esos cables numerados.
- **Cables quitados a mano** (2026-10-05, pedido del usuario: se ven en el instructivo pero no se cablean en E6): 🗑 en la
  tarjeta, 🗑 Quitar / tecla Supr en el visor, «quitar» en los pendientes. Van a `ins['quitados']` (la línea entera; los
  pendientes con `pendiente: True`), salen de los pasos, el visor, la auditoría y la WPC, y se vuelven con «volver a E6» a
  su lugar (`seq`). Al regenerar los respeta `instructivo.separar_quitados` (mismas puntas, sin ARRIBA/ABAJO, o único
  tramo en los mismos aparatos); los que ya no se reconocen vuelven al instructivo y se avisan en `quitados_vueltos`.
  El listado de cables del funcional no cambia.
- **Toma 11SK1 del 75286:** todos sus cables se cablean por abajo.
- **Producto (2026-10-07, pedido del usuario):** la clave es el **código de producto SAP con su sufijo** (75286-1; PAE =
  76857-1, que no está en el PDF: la portada dice 76860-1; PP STD = 76572-1, el rótulo dice 76571-1), y además el plano
  funcional y el topográfico con su revisión (texto: `0A`, `4(A)`). Plano y revisión salen del `/Title` del PDF y del
  rótulo (en EPLAN, documento y revisión del rótulo); el código, del catálogo `programa/productos.json` o del `CODE:` del
  rótulo (`planocables/producto.py`). Va en `resultado.json` y en `ins['producto']` (`documento` / `revision` quedan por
  compatibilidad con `wpc.json` y los mapeos verificados). El taller lo **confirma a mano** (✎ en la línea «Producto»,
  `GET/PUT /api/trabajo/<id>/producto`): queda en `producto.json` del trabajo, que **manda** al regenerar, y suma los alias
  al catálogo. Si la detección no es segura o las fuentes no coinciden, un asistente pregunta una sola vez.
- **Lista WPC (2026-10-05 / 06):** los que quedan en la bandeja: recorrido por canaletas + sobrante (`wpc.json`:
  `margen_bandeja` 100) + agregado del taller (`agregado_bandeja` 75; después se ajusta el largo y se suma un factor de
  corrección). **Los que salen a LI** (regla del taller del 2026-10-06, con la estación E8 para saber adónde van de verdad;
  «canaleta» = la parte de la ruta que corre DENTRO de las canaletas, sin la acometida del borne: `wpc_core.js canaleta()`):
  - muere en la bandeja lateral (ej. 1161 → 12XPS 4): `acometida` 75 (borne → canaleta) + canaleta de la bandeja +
    `curva_LI` 100 (curva posterior → LI) + canaleta de la lateral + `acometida_LI` 150 (canaleta → borne). 1161 = 75 + 297 +
    100 + 269 + 150 = 891 → 900;
  - sigue a la puerta / placa (21PCB01, 13MS1, 42DB1…): `acometida` 75 + canaleta de la bandeja + `puerta` 1850.
  Pendientes de la lateral y planos sin E8 (sin la lateral dibujada): como antes (`margen_LI` / `extra_puerta` / `extra_LI` +
  `agregado_*`). La WPC **solo corta**: columnas fijas sin pelar ni crimpar (`fijos` en 0). **Reemplazos** (solo en la
  lista, el instructivo no cambia): negro 4 mm² → violeta 2,5 y rojo 4 mm² → naranja 2,5 (la WPC no tiene slots de 4 mm²).
  Al principio solo en el PAE (ZPL-76884, donde la rev 1 no tiene cables de 4 mm²); desde el 2026-10-07 valen para **TODOS
  los productos** (`wpc.json → reemplazos`; se pueden apagar en un producto desde el panel de parámetros).
  **Parámetros por producto (2026-10-07):** todos (largos, `fuera`, `termos`, `fijos`, colores, códigos, reemplazos,
  `marcador`) en tres niveles: `wpc.json` (todos los productos) < `wpc.json → productos[código]` (si no hay, por documento)
  < `ins.wpc.cfg` (este trabajo). Los cambia el taller desde el panel **⚙ Parámetros** de la ventana WPC (Este trabajo /
  Producto / Todos; se arma con la sección `parametros` de `wpc.json`); «Producto» y «Todos» se guardan con
  `PUT /api/config/wpc`, que escribe atómico y deja un respaldo con fecha en `respaldos_wpc/`. Botón **⭳ .wpc**: un archivo
  por producto con todos los cables en orden de cableado (zip de una entrada con el XML como lo guarda la máquina al
  importar el CSV; columna 21 = `marcador`, por sección), nombre `'<código> - <plano> Rev <rev>'` (ej.
  `75286-1 - 75287 Rev 6.wpc`, igual que el `ProjectName`). El CSV (⭳ CSV) sigue.
  **Termos (señalizadores):** columna 22 del CSV («Labeling Position», en el .wpc `Col22="giro origen|giro destino"` en
  grados): una punta aguas arriba y otra aguas abajo → `0|0`; las dos aguas abajo → `180|0` (gira el primero); las dos
  aguas arriba → `0|180` (gira el segundo). Lado = arriba / abajo del eje del riel por el punto exacto (`lado`, `marca_*`,
  `topo.comp[tag].fila`), o por el texto; la punta que sale a LI / LD se toma como aguas abajo (coincide con lo que el
  taller puso a mano en los .wpc del 66817). **Fuera del arnés** (destildados, con el motivo, `wpc.json → fuera`): 35 mm²,
  comunicación (≤ 0,5 mm² o XCM / RS-485), solenoides (SP-n, ZV, YV), campo (CAMPO, ROTORK, PIT, IP_). Formato de la WPC
  (Weidmüller): plantilla `Template_5.0.11.xlsm` y archivos `.wpc` (zip con XML, `Col1..Col49`) en
  `G:\...\4-Instructivos de montaje de VECTOR\WPC\`; «sin terminal» = pelado, proceso y crimpado en 0 (col. 24-26, 28, 46, 47).
- **Proyector (2026-10-05, pedido del usuario):** se proyecta sobre la bandeja solo lo necesario (canaletas y el cable, nunca
  la imagen del topográfico); la referencia para escalar son los **orificios de las esquinas de la placa** (PAE: tuercas a
  17,5 mm de los lados y 12,5 mm de arriba/abajo, 700 × 845 mm entre centros; AutoCAD: círculos con cruz a ~12 mm). La
  calibración y la ventana se guardan por trabajo (`instructivo.json` → `proyector`). **La bandeja se cablea acostada
  (en horizontal):** el encuadre inicial va girado 90° en sentido horario (opción `giro`, ⚙ Ver o tecla G: 0 / 90 / 180 / 270;
  al cambiarlo hay que calibrar de nuevo). Los textos (mangas, «← LI») se dan vuelta solos para leerse en la pantalla.
- **No escribir coordenadas ni tags de un plano en el código.** Todo tiene que ser general; los modelos se cargan en
  `programa/bornes/catalogo.json`, en mm.
- **Preguntar al usuario antes de cambiar una convención del taller.**

## Pruebas de regresión (correrlas después de cada cambio en el lector o el instructivo)

**Forma corta:** `python pruebas/bateria.py` corre todo en una carpeta temporal (los 4 `volcar_trabajo`, 104/104 y 75/75
del 66817, todos los `probar_*.py`, `volcar_bases_nuevas.py`, `comparar_bases.py` contra `pruebas/bases/` y
`node --test pruebas/js/`) y termina en TODO OK; `--ab` suma el A/B de todos los planos de `1 - Planos` (`ab_planos.py`
contra `pruebas/bases/ab/`; contra otra copia del programa: `--programa <copia>/programa` y
`--comparar <A> <B> --ignorar producto`), `--dejar` no borra la carpeta. La lista WPC sola: `node --test pruebas/js/`.
Las bases nuevas (`listado_` / `layout_` / `e8_` / `ins_<t>.json`, `ab/`, `web/humo_*`, `wpc/`) se regeneran solo a
propósito, con su generador (`volcar_bases_nuevas.py`, `ab_planos.py`, `probar_web_humo.py --crear`,
`node pruebas/js/generar_goldens.cjs`), revisando el diff. Variables: `PLANOCABLES_MEMORIA_OCR=solo-lectura` (no reescribe
`programa/ocr_cache.json`), `PLANOCABLES_PRODUCTOS` (otro catálogo de productos; las pruebas usan
`pruebas/fixtures/productos.json`), `PLANOCABLES_CONFIG_WPC` (otro `wpc.json`; las pruebas usan una copia),
`PLANOCABLES_HISTORIAL` y `PLANOCABLES_PORT` (puertos de prueba, nunca el 8765). Los comandos de siempre siguen valiendo:

```
python pruebas/volcar_trabajo.py "3 - Historial web/ac0f0949510a" salida_75287.json --sin-cache     # 75287
python pruebas/volcar_trabajo.py pruebas/trabajos/66817 salida_66817.json --sin-cache --relayout     # 66817
python pruebas/volcar_trabajo.py pruebas/trabajos/76884 salida_76884.json --sin-cache --relayout     # PAE (EPLAN)
```

- **75287**: el trabajo `ac0f0949510a` está en git, pero el usuario lo borró del historial el 2026-10-05. Si no está en la
  carpeta, sacarlo a una carpeta temporal (`git archive HEAD "3 - Historial web/ac0f0949510a" | tar -x -C <tmp>`) y
  correr `volcar_trabajo.py` sobre esa copia; no volver a ponerlo en el historial del usuario sin preguntar.
- **75287** (mSafe2AC, tablero 75286): verificado por el taller. Líneas, pendientes, sueltos, otra estación y extremos
  tienen que dar **IGUAL** a `pruebas/bases/base_75287.json`.
- **66817** (mSafe NC): tiene que dar como `pruebas/bases/base_66817.json`: 75/75 puntas exactas y 104/104 bornes contra
  `prototipos/_referencia_66817/bornes_referencia.json` (`python pruebas/evaluar_bornes.py <puntos.json> --ref ...`).
- **PAE** (ZPL-76884, EPLAN): `pruebas/trabajos/76884` usa el PDF original de `1 - Planos/Producto nuevo/` (no lo copia).
  Tiene que dar como `pruebas/bases/base_76884.json`: 136 líneas E6, 30 pendientes, 24 en otra estación (E8), 0 sueltos
  (desde el 2026-10-06, con la batería y las solenoides en E8; antes 143 / 31 / 16, igual al Excel del mapeo verificado).
- **TPT** (72715; trabajo de prueba `pruebas/trabajos/tpt`, el del usuario `e548b195eb2a` ya no está en el historial): `pruebas/bases/base_tpt.json` es el estado ANTES de corregir el
  lector (con errores). Con `--relayout`, el estado actual es `pruebas/bases/base_tpt_ronda3.json` (2026-10-02 noche;
  regenerada el 2026-10-06 con el catálogo nuevo: mismas líneas, solo pasan a punto exacto 11Q1 —ABB SH 202, verificado
  con fotos— y 33MX01 —MOXA—; y otra vez el 2026-10-07: mismas 83 líneas, los 16 cables del MOXA, bornera en columna al
  frente, van seguidos de arriba a abajo y salen en horizontal a la canaleta de la derecha, y pasan a punto exacto
  13PS3 ±Vin y 43XDIB 1-4).
- `--sin-cache` no escribe nada en el trabajo. Como la web, `volcar_trabajo.py` vuelve a leer el topográfico si
  `layout.json` es de otra versión del lector (`topo.VERSION_LECTOR` / `eplan.VERSION_LECTOR`: subirlas al cambiar la
  lectura del topográfico; al regenerar, la web relee los trabajos viejos y conserva lo del usuario).
- Pruebas de arreglos: `python pruebas/probar_arreglos_pae.py`, `python pruebas/probar_ronda2_topo.py` y
  `python pruebas/probar_ronda3.py` (familias del catálogo, red de seguridad del mapeo, topográfico sin capa de riel,
  versión del lector) tienen que dar TODO OK.
- Proyector: `python pruebas/probar_proyector.py` (orificios del PAE = rectángulo de 700 × 845 mm, mediatrices, placa sin
  orificios, endpoints `/proyector`) tiene que dar TODO OK.
- **TPT del usuario** (72715-1 con su «72715-1 Constructivo», copia del trabajo `ce304e99d4ea` sin las marcas):
  `pruebas/trabajos/tpt_constructivo`, con `--relayout`. E6 tiene que dar como `pruebas/bases/base_tpt_constructivo.json`
  (83 líneas, 16 pendientes, 0 sueltos; sacada con el código de d12fa6d). Está en la batería y en los golden de la WPC.
- E8: `python pruebas/probar_e8.py` (arma la E8 de tpt_constructivo, tpt, 66817, 75287 y PAE y mira lo esperado de cada
  etapa, y que E6 dé igual que `pruebas/bases`; desde E8-2 además la vista previa de la entrada / bisagra / grupos y que
  regenerar conserve lo elegido y un topográfico nuevo lo borre; desde E8-3 los WAGO del cargador y el RS-485 «empalme de
  3, a confirmar»; desde E8-4 la vista de la puerta, sus recorridos, el tránsito «Pasan hacia la puerta» y que la WPC no
  la use; desde E8-5 los puntos exactos de las laterales, el ajuste a mano y que el punto ajustado mande al regenerar sin
  tocar E6; desde E8-6 los grupos de ruteo a mano de cada plano (revisados contra el funcional), lo del fixture
  `pruebas/fixtures/recorridos_e8.json` (el tpt_constructivo, 72887 rev. 8, lo toma; el tpt, rev. 7, no), GET / PUT
  /e8/grupos entre trabajos del mismo producto y topográfico, el conflicto de versión, el producto sin confirmar y los
  cables directos del PAE; `--bases pruebas/bases` solo mira los `e8_*.json` y la vista previa sobre los `ins_*.json`)
  tiene que dar TODO OK. Las pruebas usan una COPIA del fixture (`PLANOCABLES_RECORRIDOS_E8`): nunca
  `programa/recorridos_e8.json`. La pantalla de E8: `node --test pruebas/js/` (`e8_empalme`, `e8_puerta`, `e8_puntos`,
  `e8_mano.test.cjs`, con `vistaE8` y `manoE8` de `cargar_visor.cjs`).
  Tabla de antes y después de la WPC: `node pruebas/js/tabla_wpc.cjs <salida.md> <título> <nombre> <ins_antes> <ins_después>`.

## Productos trabajados

- **75286 / 75287 + 75441** (mSafe2AC): el de referencia. Su `bornes.json` está hecho a mano y verificado.
- **66817** (mSafe NC): funcional A3, topográfico con capas `_IGV_*`, sin lista de materiales. Mapeo automático 104/104,
  validado con fotos reales.
- **72715 + 72887** (mSafe TPT): el usuario lo cargó el 2026-10-02 y encontró errores de lectura del funcional:
  - tramos falsos (1305 de un borne a sí mismo);
  - módulo de relé mal tomado (2152 y 2154 en dos módulos, 6104);
  - bornes sin número (6201 y 6202 `XM1 ARRIBA/ABAJO`);
  - todas las combinaciones de pares en cables de 4 puntas (1313, 1314);
  - destinos `? 4`.

  Ver "Estado" abajo.
- **ZPL-76884 mSafe2+ PAE (EPLAN)**: un solo PDF de 50 hojas con texto real, protegido con AES (para pypdf hay que
  sacar una copia con `pypdfium2 save(flags=FPDF_REMOVE_SECURITY)`; el original no se toca).
  - Hojas 47-50: lista de conexiones (origen/destino de cada cable). Hojas 32-39: hileras de bornes. Hojas 40-46: artículos.
    Hoja 8: bandejas.
  - Mapeo verificado en `2 - Resultados/76884 mSafe2+ PAE/`: 194 conexiones, 260 puntas.
    - Excel: `Mapeo de cables mSafe2+ PAE (ZPL-76884).xlsx`.
    - JSON: `mapeo/conexiones.json`, `aparatos.json`, `bandejas.json`, `puntos_*.json` (+ `correcciones_*.json`).
  - Las dudas a confirmar están en la hoja "Dudas a confirmar" del Excel.
  - **Cargado en el programa (2026-10-02):** se sube el PDF como plano eléctrico y sale el listado, el Excel (con la hoja
    "Lista de conexiones (EPLAN)") y el instructivo E6 solo, con la hoja 8 del mismo PDF como topográfico (botón «Usar las
    bandejas de este mismo PDF» si hace falta). Daba 143 líneas E6, 31 pendientes LI↔LI, 16 en E8, 0 sueltos, igual que el
    Excel del mapeo; desde el 2026-10-06 son 136 / 30 / 24 (batería 12PB1 y solenoides SP_x en E8), con cada punta en el
    punto verificado y ruta por las canaletas.
  - Lo general (sirve para otros EPLAN): lista de conexiones leída por contenido (número, destino 1/2, color, sección),
    renglones sin número con nombre propio (`⏚11PS1`, `MALLA 21PCB01 34`, `s/n ROTORK 1`), `-61KR1 -61KR1` = unión interna
    (no es cable), rieles DIN por el patrón de líneas del perfil, canaletas = franjas vacías de ancho normalizado, placas,
    etiquetas `-TAG`, lo que está en la placa principal fuera de rieles y canaletas → E8, canaletas de intrínsecos de la
    vista a color de las bandejas (coincide con el mapeo). Sin mapeo verificado: texto general y punto aproximado, con aviso.
  - Corregido el 2026-10-02 tarde (`pruebas/probar_arreglos_pae.py` = TODO OK):
    - el cajetín del rótulo solo con el bloque de `Cont:`: la hoja 13 tiene sus 44 números; `base_76884` trae
      `detalle_por_pag`;
    - PDF de EPLAN sin hoja de bandejas → aviso claro;
    - sin lista de conexiones → mensaje "Falta la lista de conexiones" (se detecta EPLAN con 3 hojas de 8 o más `-TAG`, o
      40 o más en total; AutoCAD llega a 7/18);
    - textos sin mapeo: el tipo de bornera sale de las hileras de bornes y lo dudoso queda «a confirmar»;
    - Excel con números;
    - las puntas con la hoja del esquema, para el botón ⚡ Funcional;
    - cli/app sin BUSCABLE para EPLAN;
    - E8 con el destino real (empalmes X1, PT001, BH_01_ZV);
    - cables de campo de borneras intrínsecas por la canaleta azul (por zona, solo EPLAN);
    - deduplicación por par de designaciones.

## Fuentes de verdad fuera de este repositorio (solo en la PC del taller, disco G:)

- Fotos reales de tableros cableados, con los números en las mangas:
  `G:\Unidades compartidas\Batfer - Taller\20-14-BTF-BATFER-taller\4-Instructivos de montaje de VECTOR\Fotos de referencia de VECTOR\Fotos soporte E06|E08\<producto>`.
- Órdenes de trabajo con planos: `...\3-Info. Tecnica\ORDENES DE TRABAJO\` y `OBSOLETO (NO USAR)\`.
- Instructivos WPC (`.wpc` = zip con XML): número, largo, sección y color, sin origen/destino.

## Pendientes

- **Corrección del lector del funcional con el TPT** (2026-10-02): ver "Estado".
- **Visor de E8 (2026-10-08), después de la etapa E8-4 (puerta):** «sigue a la puerta» sigue incluyendo lo que no está
  dibujado en ninguna hoja (en el 75441 la placa 21PCB01 de la puerta no tiene etiqueta: con «solo lo de la hoja de la
  puerta» sus 37 cables saldrían por el fondo); por eso en el TPT / 66817 el 1206 / 1205 a BH-01-M (y los de ZY, que el
  lector no lee) siguen yendo hacia la puerta con la bisagra de ese lado (se corrige con un grupo de cables elegidos).
  La puerta del PAE (EPLAN, «INTERIOR DE PUERTA», hoja 31) queda para después. Para confirmar: la vista de la puerta se
  toma como INTERIOR (bisagra izquierda = borde derecho del dibujo; vale en el TPT, el 66817 y el 75441); la franja de
  bornes es el lado de abajo (o de arriba) del cuerpo del aparato que mira al tramo común. Para confirmar: en la WPC un cable de una lateral a la otra (66817: 1101 / 1102) toma la canaleta de
  una sola lateral (la derecha: su WAGO en la izquierda no suma la vertical); el RS-485 de 3 conductores en un empalme
  (WAGO de 3 vías, dos WAGO u otra forma); los nombres de los pines del cargador (panel / batería / carga, en
  `bornes/pines_repetidos.json`); el cable propio punteado llega al punto del aparato (la etiqueta), no a su borde de
  abajo (el topográfico no da el cuerpo del aparato).
- **Ruteo a mano de E8 (2026-10-09, etapa E8-6), para confirmar con el usuario:** las letras de la tabla
  `programa/web/e8_grupos.json` que no salen de una lista de materiales: **13SH1 (OFF / ON) tomado como selectora** (en
  el 75287 podría ser el seccionador de emergencia VCF01), DB = pulsador (parada de emergencia hongo), DS = doorswitch,
  MS = seccionadora; «Batería 35 mm²» = todos los de 35 mm² (batería, MEGA, contactor y bomba); «Batería 4 / 6 mm²» =
  los que tocan la batería (no los del cargador a 12F1 / 12XP); los cables de una seccionadora que está en la lateral
  (11MS1 del 75287) también van a mano. La capa «Pasan hacia la puerta» de E8-4 sigue igual aunque esos cables tengan
  grupo. En el PAE, el cargador sin lista de materiales se reconoce por las letras PS para los cables directos.
- **EPLAN (PAE), para confirmar con el usuario:**
  - el neutro es **celeste**: la regla de ruteo «marrón y blanco salen a LI por abajo» separa L (marrón, abajo) de N
    (celeste, arriba); ¿sumar celeste a la regla?;
  - los cables de campo (ROTORK, PIT01F, IP_x) y las mallas salen en E6 como «→ LI» (regla del usuario: campo = LI),
    sin color ni sección (EPLAN no los da);
  - las dudas del mapeo verificado (hoja «Dudas a confirmar» del Excel) salen como avisos en el instructivo.
- **Arreglos del mapeo automático que quedaron a medias** (`pendiente/arreglos_mapeo_parciales/`, sin verificar):
  - diferencial/termomagnética sin lista → confianza media;
  - relé único sin módulo no se renombra;
  - `bornes_usuario` manda aun con renombre;
  - etiqueta None;
  - bornes.json roto;
  - firma del caché con el contenido del topográfico;
  - aviso de modelos que no están en el catálogo;
  - `usos_bandeja` con conductores sin pares y `agregar`;
  - 32XAIB/43XDIB no son banco de barreras;
  - avisos de lado físico;
  - azules intrínsecos que salen en horizontal por encima de otros bornes (`ruteo.py`).
- **Catálogo de aparatos (Excel de aparamenta, 2026-10-06):** el usuario pasó `BOMs Por Estación .xlsx` (164 materiales SAP
  de los mSafe SHELL / PP / 2 PAE / TECPE / 2 Vista / YPF, con estación y productos; se retroalimenta solo).
  - Está en `programa/bornes/aparamenta.json`: cada código SAP con clase, fabricante, modelo comercial, código del
    fabricante y el modelo del catálogo (`catalogo`) o `motivo_sin_modelo`. Al llegar el Excel nuevo:
    `python programa/bornes/aparamenta.py "<Excel>"` (conserva lo identificado, marca los nuevos con `revisar` y da el
    informe). Excel para el taller: `2 - Resultados/Aparamenta (BOMs por estación)/`.
  - Catálogo de bornes: 25 modelos, cada uno con sus códigos SAP en `sap`. Nuevos: PT4 (+PT 4-PE), PT6, PSR-SCP (relé de
    seguridad, familia `rele_seguridad`), ABB-SH202, EO-I-UT (toma Phoenix), DF141, MOXA-R1240 (disposición `cuerpo`)
    y EXEMYS-EGW1. `solo_por_lista: true` = el modelo se usa solo si la lista de materiales lo nombra (aparatos puntuales:
    nunca se adivinan por el dibujo). Los modelos nuevos van al final de `modelos`.
  - Sin modelo: ODOT B32-MR-3B-00 (sin plano acotado; el funcional del PP no nombra sus bornes). A propósito: Tracer BP
    (va en la lateral; no tiene bornera, salen cables propios), bornes y barra de tierra (cables sin número).
  - **no** armar el catálogo desde los planos; `catalogo/productos/` tiene lecturas parciales de 7 órdenes SAP, solo para
    comparar.
- **E8 en 3D: ELIMINADO el 2026-10-05 a pedido del usuario** (visor del gabinete, `gabinete.py`, `web/e8.js`, `e8.css`,
  endpoints `/e8`, botones E6/E8 y `destino_e8` / `filas_pin` / `destino_campo` del instructivo). Está en git (commit
  `5698cf0`). No volver a proponerlo sin que el usuario lo pida. La estación E8 sigue: «Se cablean en otra estación».
  Del mismo trabajo quedan los arreglos del lector: bornera en FILA (tag a la izquierda del borne 1: 12XPS 4-10 en la
  hoja 12), borne atravesado por el recorrido = unión (12XPS 7/8 en la hoja 81), pines redondos de la placa con su número
  (hoja 21) y solenoides `SP-1`/`SP-2` (FIELD_RE); `base_75287.json` regenerada solo en `extremos` (42 cables).
- **Para confirmar con el usuario:**
  - escribir el pin en textos repetidos (`13PS2 -Vo (1)`);
  - barreras `1 ABAJO` (el texto viene del funcional, el enchufe está arriba);
  - 61XDIO/62XDIO: ¿lado físico o del funcional?;
  - código `LD` para el lateral derecho;
  - en el RS-485, los blanco/azul de 0,32 mm² no salen por la salida de abajo.
  - (2026-10-06, del Excel de aparamenta; detalle en la hoja «Para confirmar» del Excel de `2 - Resultados/Aparamenta
    (BOMs por estación)/`):
    - EXEMYS EGW1 (2026-10-07, del taller: «3 niveles, todos abajo»): tres enchufes abajo. El de adelante es el de más
      abajo (1-4, verificado con la foto 1.6 del 76572), detrás 5-8 y más atrás HART. Falta una foto del rótulo del
      costado para el orden de HTa / HGND. El lector del funcional no lee los nombres de borne escritos en tablas
      (PP: 1317, 3301, 3302 sin borne; 2135/2136 no llegan al 33EXM).
  - Resuelto el 2026-10-07: toma 11SK1 del PAE = N – PE – L de izquierda a derecha (el taller, con la foto de Phoenix):
    1181 (L) y 1182 (N) intercambiados con `correcciones_riel3_lateral.json` del mapeo (una corrección puede traer
    `confianza`) y reexportado; `base_76884` igual (son pendientes LI↔LI). Bornera 41XEX del PAE: el taller la arma
    de 1 a 12 en orden aunque la hoja 8 y la pág. 38 dibujen las piezas 1 3 5 9 7 11 (el mapeo había seguido el número
    dibujado y cruzaba 4122/4123 con 4124/4125): 8 correcciones en `correcciones_riel3_lateral.json`, aviso quitado del
    exportador; `base_76884` regenerada (mismas 136 líneas, cambia el orden de 4 cables de campo). PSR-SCP en AutoCAD, 13/14 en el enchufe de
    adentro de abajo (foto 1.6 del 76572: 2114 / 2115);
    parada de emergencia del mSafe1 PP = NC (ZBE102): **cuando la lista de materiales y el dibujo del funcional no
    coinciden, manda el dibujo del funcional** (regla del taller).

## Estado (2026-10-02)

- Mapeo automático de bornes integrado: 66817 = 104/104, 75286 = 140/140 con la lista de materiales del funcional,
  75287 idéntico.
- Interfaz del 2026-10-02:
  - botón 🔍 Auditoría en el visor de cablear (tecla A) y 🧰 Instructivo en la auditoría (tecla I);
  - en la auditoría, clic en un cable = chequeado y translúcido;
  - mangas con `2,5mm²`;
  - el tramo punteado de un cable de 3 puntas va al costado del cable actual donde comparten canaleta.
- **Corrección del TPT: HECHA (2026-10-02).** Contra `pendiente/tpt_diagnostico/verdad_tpt.json`: 96/98 cables iguales; los 2
  restantes son la convención de pines de barrera (`43DIB1 1 ABAJO`), sin confirmar. Nueva base: `pruebas/bases/base_tpt_corregido.json`.
  - Reglas nuevas del lector:
    - recuadro del módulo de relé de 5u a 20u, y `61KR.3`;
    - hojas con letra (43A/61B);
    - ALTERNATIVAS: se cablea una, la que nombra la lista de materiales, o la primera (`ins['alternativas']`);
    - cables de N puntas = N-1 tramos reales;
    - `tag_de_columna`;
    - polos F/N de interruptores Q sin número;
    - salidas a CAMPO por la línea de trazo y punto: estación 'CAMPO', sin confirmar con el usuario;
    - EMPALME en ramas sin número;
    - rótulos `V+`, `NC(12)`.
  - Rondas 2 y 3 (2026-10-02, hechas y verificadas):
    - **Topográfico:** rieles por geometría (con capa de riel, o con 3 o más etiquetas apoyadas si no hay capa), etiquetas
      partidas ('1','1','XP'), versión del lector `VERSION_LECTOR` (Regenerar relee el topográfico si cambió).
    - **Listado:** 'Puntas' sin alternativas ni flechas de la misma hoja; 1204 sin el 35 falso; 8104 asociado.
    - **Mapeo:** familia del modelo (no se elige un modelo de otra familia; lo que no está en el catálogo queda aproximado
      con aviso); red de seguridad (puntos sobre otro aparato se descartan); arreglos que estaban pausados (a-o).
    - **Alternativas:** se ven en la interfaz.
    - **Marcas al regenerar:** se pasan por número solo si las puntas siguen en los mismos aparatos.
    - **Base TPT:** `pruebas/bases/base_tpt_ronda3.json` (83 líneas, 16 pendientes, 0 sueltos). Pruebas:
      `pruebas/probar_ronda2_topo.py` y `pruebas/probar_ronda3.py`.
    - **`base_66817.json` regenerada:** 32XAIB/43XDIB aparato por aparato.
  - **Modelos que faltaban en el catálogo de bornes:** cargados el 2026-10-06 con el Excel de aparamenta (ver
    «Catálogo de aparatos» en Pendientes). Quedan afuera los de productos que no están en el Excel (FCS / dFRAC: ABB
    DS201, Red Lion E3, P+F KCD2, Turck...) y los de puerta (VBF1, ZBE10x, HL-5200), que se cablean en E8.
- (Historia) La corrección del TPT se había diagnosticado y pausado antes; el diagnóstico sigue en `pendiente/tpt_diagnostico/`.
  - En `pendiente/tpt_diagnostico/` están:
    - `LEEME.md`: cada error con la verdad del funcional, la causa en el código y el arreglo propuesto;
    - `diagnosticos.json`: 3 diagnósticos con 6, 22 y 7 casos;
    - `verdad_tpt.json`: la verdad de todos los cables del TPT según el funcional.
  - Próximo paso: corregir el lector con arreglos generales, probar en `pruebas/trabajos/tpt` y verificar
    que el 75287 quede igual y el 66817 siga 104/104.
  - Después, el usuario cierra y abre el programa y aprieta ↻ Regenerar en el TPT.
