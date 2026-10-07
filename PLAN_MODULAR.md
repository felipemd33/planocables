# Plan: programa modular (planocables)

> **Estado:** es un plan; no hay nada implementado. Rama `sistema_modular`, 2026-10-07.
> **De dónde sale:**
> - una lectura completa del programa, en 8 áreas;
> - un borrador armado a partir de esa lectura;
> - dos revisiones contra el código: una de hechos y otra de riesgos. Corrigieron 32 afirmaciones del borrador y agregaron unos 40 faltantes.
>
> **Convenciones:**
> - Las rutas `archivo:línea` son relativas a `programa/`, salvo que se indique otra carpeta.
> - «nuevo» marca algo que hoy no existe.
> - «a verificar» marca algo que todavía no se confirmó.
>
> **Regla de oro:** ninguna etapa de este plan cambia un resultado del taller (líneas, textos, largos, CSV). Lo que podría cambiar algo está en la sección 10 y necesita tu OK.

---

## Resumen

- **Se puede.** El núcleo (leer el plano, el topográfico y los bornes, rutear y armar el instructivo) ya está en Python y no usa Flask. Lo que falta es ordenarlo.
- **Hoy hay cuatro problemas:**
  1. **Los archivos se importan en círculo.** Por ejemplo, `core` ↔ `eplan`, `topo` ↔ `eplan`, `topo` ↔ `ruteo`, `core` → `instructivo` y `bornes` → `instructivo`. Si te llevás uno, te arrastrás casi todo.
  2. **La receta «plano → topográfico → bornes → instructivo» vive dentro de la web.** Está en `gen_instructivo`, unas 150 líneas de `web.py`, y está copiada a mano (con diferencias) en las pruebas y en `cli.py`.
  3. **Hay reglas del taller escritas en JavaScript:** la Lista WPC entera, el terminal y la pollera, las secciones de la auditoría y los grupos de salida. Fuera del navegador no existen.
  4. **Los módulos leen y escriben archivos por su cuenta:** `glyphdict.json`, la memoria del OCR, los mapeos verificados, `bornes_auto.json` y copias en `%TEMP%`.
- **La propuesta:** un paquete `programa/planocables/` armado en capas.
  - El **núcleo** no toca el disco ni usa Flask: recibe bytes y datos, y devuelve diccionarios (JSON).
  - Solo la capa `trabajo/` guarda en disco.
  - La web del taller queda **igual** y pasa a ser un «adaptador» más.
  - Para la otra app:
    - si es **Python**, se importa;
    - si es **Node**, se llama por línea de comandos con JSON, o a un servicio aparte.
- **Puentes:** los archivos de hoy (`core.py`, `topo.py`, `instructivo.py`…) quedan como puentes que reexportan desde el paquete. Así la web, los `.bat`, las pruebas y los scripts del mapeo del PAE siguen andando sin cambios.
- **La WPC va primero**, después de la red de seguridad:
  - un módulo `planocables/wpc/` sin dependencias pesadas;
  - parámetros configurables en tres niveles: global, por producto y por trabajo;
  - el CSV tiene que dar **byte a byte** igual que hoy.
- **Se trabaja en una copia aparte** (un git worktree, con otro puerto), para que el taller siga usando la web mientras tanto.

---

## 1. Cómo está hoy

### 1.1 Mapa del programa

| Archivo | Líneas | Qué hace | Dependencias pesadas |
|---|---:|---|---|
| `core.py` | 666 | Lector del funcional AutoCAD (`process`), listado, Excel, PDF buscable. Si el PDF es EPLAN, deriva a `eplan` | pypdf, reportlab (el buscable) y openpyxl (el Excel) |
| `wires.py` | 792 | Grafo de cables (`WireGraph`), asignación de números y etiquetas | arrastra numpy y cv2 por `textdec` |
| `textdec.py` | 472 | Letras SHX por firma (`Decoder`), memoria OCR | numpy y cv2 **al importarse** (los usa solo `render_line`) |
| `pdfvec.py` | 104 | Trazos del PDF por capa | pypdf |
| `ocr_raster.py` | 64 | OCR de hojas escaneadas y `PDFIUM_LOCK` | numpy, cv2, pypdfium2 y rapidocr |
| `eplan.py` | 1678 | EPLAN: detección, rótulo, lista de conexiones, textos, listado, bandejas, mapeo verificado y Excel | pypdfium2, numpy y cv2 |
| `topo.py` | 543 | Topográfico: rieles, etiquetas, escala, componentes | pypdf, pypdfium2 y numpy |
| `ruteo.py` | 410 | Canaletas (`ducts`), red (`Net`), `route_line`, `li_exit` | pypdf (solo para `ducts`) |
| `instructivo.py` | 2222 | Lectura de puntas y conductores (`:46-1416`), alternativas, armado (`build`, `:1531-2009`), salidas, quitados, usos, materiales y lectura de archivos del trabajo | — (arrastra todo por los imports) |
| `bornes/` | 2790 | Mapeo automático de bornes (`motor`, `primitivas`, `__init__`), más las herramientas `aparamenta` y `medir` | pypdf, pypdfium2, numpy y cv2 |
| `estacion8.py` | 242 | Estación 8: laterales y puerta / placa | — |
| `proyector.py` | 168 | Orificios de la placa para calibrar | pypdf |
| `web.py` | 797 | Flask: endpoints **y** la orquestación | flask y Pillow |
| `cli.py` / `app.py` | 55 / 110 | Línea de comandos y ventana Tk (copian la orquestación) | tkinter |
| `web/*.js` | 3593 | Interfaz, **más** la WPC, el terminal, la auditoría y los grupos de salida | — |

### 1.2 Lo que impide sacar módulos sueltos

1. **No es un paquete.** Todo se importa por nombre plano (`import eplan`, `from core import process`). Anda porque cada punto de entrada mete `programa/` en `sys.path`:
   - `web.py:6`, `cli.py:3` y `app.py:5`;
   - `bornes/motor.py:36-38` (y `bornes/medir.py:22-24`), que lo hace al importarse;
   - cada prueba.

   Nombres como `core`, `topo` o `web` chocan fácil dentro de otra app Python. Además, `bornes` importa módulos de `programa/` como si fueran de primer nivel. Desde otra app se podrían cargar dos `instructivo` y dos `PDFIUM_LOCK`.

2. **Ciclos y dependencias que no deberían existir.** Hoy se esquivan con imports «tardíos» (adentro de funciones):

   | De → a | Dónde | Qué se usa en realidad |
   |---|---|---|
   | core ↔ eplan | `core.py:111` / `eplan.py:902` | `es_eplan` y `process` / `zone_of` y `natkey` |
   | topo ↔ eplan | `topo.py:348,371` / `eplan.py:1375` | la decisión AutoCAD/EPLAN / `snap_escala` y `RIEL_MM` |
   | topo ↔ ruteo | `topo.py:537` / `ruteo.py:53` | `ducts` / `rail_bands` y `perfil` |
   | core → instructivo | `core.py:394`, dentro de un `try/except` amplio (`:396,411`) | alternativas y `hoja_base` |
   | eplan → instructivo | `eplan.py:833,955,1003` | `is_terminal_block` (función) y `COLOR_INI` (dict) |
   | eplan → wires | `eplan.py:100` | `norm_color` (por eso eplan necesita opencv) |
   | eplan → bornes → instructivo | `eplan.py:1586` → `bornes/__init__.py:215` | leer `bornes.json` y `correcciones.json` |
   | bornes → instructivo | `bornes/__init__.py:224` | `usos_bandeja` y `materiales_funcional` |
   | proyector → eplan | `proyector.py:22` | `copia_proceso` (PDF protegido) |
   | estacion8 → instructivo, ruteo | `estacion8.py:13,194,199` | `conductors`, `fmt_terminal`, `cable_desc` y `natk` |

3. **La orquestación vive en la web:**
   - `gen_instructivo` (`web.py:370-518`) mezcla reglas del taller con Flask y carpetas:
     - overrides y correcciones;
     - `bornes_usuario`;
     - mapeo EPLAN o automático, con fallback;
     - E6, y 35 mm² a E8;
     - salidas;
     - fusión con el instructivo anterior: marcas, fotos, accesorios, hechos de E8 y secciones del usuario.
   - Está **copiada con diferencias** en `pruebas/volcar_trabajo.py:19-69`:
     - usa el layout en memoria, mientras que la web lo escribe y lo vuelve a leer como JSON;
     - no convierte tipos en las correcciones (`web.py:419`);
     - con un `correcciones.json` roto se cae (la web avisa y sigue);
     - no tiene fallback del mapeo ni `topo_nuevo`;
     - no fusiona las marcas;
     - no corre `estacion8`;
     - en EPLAN usa el PDF original y no la copia `topografico.pdf`.
   - `run_job` (`web.py:74-127`) está copiada en `cli.run`. También arma sola el instructivo de EPLAN al terminar (`web.py:118-127`).
   - `gen_instructivo` **no pasa** `use_ocr` al releer el plano (`web.py:383`), pero `run_job` sí (`:87`).

4. **Reglas del taller en JavaScript**, sin equivalente en Python ni pruebas:
   - la Lista WPC (`web/wpc.js:28-184`);
   - el terminal y la pollera (`web/instructivo.js:22-33`), con una copia **distinta** en `web/estacion8.js:22-34`;
   - las secciones de la auditoría (`web/auditoria.js:14-120`);
   - los grupos de salida, duplicados en `web/salidas.js` y en `instructivo.py:1445-1484`;
   - el texto de la manga y `secNum` (`instructivo.js:14,16`);
   - el JSON «para nuestra app» (`instructivo.js:762-778`).

5. **El dominio toca el disco:**
   - `textdec` lee `glyphdict.json` y la memoria OCR en **cada** `Decoder`, y la reescribe (`textdec.py:172-222`);
   - `eplan` lee la carpeta de mapeos en cada llamada (`:560-575`), escribe copias en `%TEMP%` (`:282-300`) y lee `bornes.json` del trabajo (`:1594`);
   - `bornes` lee y escribe `bornes_auto.json`;
   - `Motor` abre el PDF;
   - `instructivo` lee archivos del trabajo (`:2165-2222`);
   - `core.write_excel` y `core.write_searchable_pdf` escriben archivos.

   Además, todo recibe **rutas** de PDF y nunca bytes.

6. **Dependencias pesadas que se arrastran sin necesidad:**
   - Como `textdec` importa numpy y cv2 al cargarse, sin opencv no cargan `wires`, `core`, `topo`, `ruteo`, `instructivo`, `eplan` ni `estacion8`.
   - En `requirements.txt` falta `reportlab`.
   - `requests` no se usa.
   - **`shapely` sí se usa**, en el script del mapeo verificado del PAE (`2 - Resultados/76884…/mapeo/codigo_geometria/cc.py:12`): no se saca.

7. **El resultado del lector AutoCAD no se puede pasar a JSON:** lleva el grafo y `id()` de Python (`textdec.py:276,416,451`). Por eso, para AutoCAD, la lectura del plano y el armado del instructivo tienen que correr en el **mismo proceso**. Hacia afuera solo salen el listado y los conductores ya armados.

8. **Protocolos por texto** (una frase que un módulo escribe y otro compara):
   - las regiones de E8 (`estacion8.py:17` contra `wpc.js:126-134`);
   - `'bornes.json ilegible'` (`eplan.py:1597` contra `instructivo.py:2177`);
   - `'Falta la lista de conexiones'` (`app.py:85` contra `eplan.py:370`);
   - el prefijo `'s/n '` y la estación `'CAMPO'` (`wpc.js:51`);
   - el log `'Hoja i/n'`, que leen `web.py:84` y `app.py:74-77`;
   - los avisos del motor que reparsea `bornes/__init__.py:181`.

   Si se cambia la frase en una punta y no en la otra, se rompe en silencio.

9. **Concurrencia:**
   - **Al regenerar el instructivo se pueden perder marcas.** La regeneración lee `instructivo.json` al empezar (`web.py:395-398`) y lo escribe minutos después (`:514`). Lo que se guarde en el medio (marcas «hecho», WPC, auditoría, quitados, salidas, hechos de E8) se pierde. Y el guardado diferido del navegador (600 ms, `instructivo.js:100-108`) puede pisar con datos viejos un instructivo recién regenerado.
   - Las cachés de `eplan` no tienen lock.
   - `Decoder._back` no es reentrante.
   - La memoria OCR se reescribe entera con un `.tmp` fijo: si la escriben dos procesos, el último borra lo que aprendió el otro.

10. **La red de seguridad tiene huecos:**
    - no hay base del listado completo (color, sección, obs, refs, a revisar), ni de E8, ni de la WPC;
    - ninguna prueba ejercita la fusión de marcas;
    - las bases y las pruebas actuales están **modificadas sin commitear** (`pruebas/bases/base_76884.json`, `base_tpt_ronda3.json`, `probar_*.py`).

### 1.3 Lo que ya está bien

- `bornes/primitivas.py` usa solo la biblioteca estándar.
- `pdfvec.page_strokes` y `WireGraph` son lectura pura.
- `ruteo` no toca el disco. Ojo: **`Net` tiene estado**. Cada cable ruteado agrega enganches a la red, así que la ruta de un cable depende de los anteriores (`ruteo.py:129-133,169-171`). Hay que conservar el orden y una sola red por instructivo.
- `instructivo.rutear_salidas` ya es JSON → JSON.
- `estacion8.py` no toca el disco.
- `proyector.orificios(..., segs=)` no toca el disco si recibe los segmentos.

---

## 2. Cómo queda

### 2.1 Capas

```
Adaptadores   web.py (Flask, igual que hoy) · cli.py / app.py · python -m planocables (CLI JSON) · api/v1 (servicio aparte, opcional)
Servicio      planocables/servicio/    cola, RUN_LOCK y progreso: leer → mapear → armar → guardar
Trabajo       planocables/trabajo/     ÚNICA capa con disco: carpeta del trabajo, JSON, cachés, memoria OCR
Exportar      planocables/exportar/    Excel, PDF buscable, JSON del instructivo → bytes (openpyxl y reportlab opcionales)
Armado        instructivo/, estacion8, terminales, wpc/, auditoria, proyector       dict → dict, solo biblioteca estándar
Lectores      lectura.py (fachada), funcional/, eplan/, topografico/, bornes/       bytes → dict, sin disco
Motores       pdf/, ocr/, shx/, ruteo/                                              bytes o listas → listas
Base          base/ (geometría, hojas, convenciones del taller, colores, escala, lado, lock) + datos/ (recursos)
```

### 2.2 Árbol

```
programa/
  planocables/
    __init__.py            versión + tabla «qué tocar» (sección 3.9)
    __main__.py            CLI JSON
    esquemas/              JSON de cada contrato: listado@1, layout@1, conductores@1, instructivo@1, wpc@1
    datos/                 cargador de recursos (sección 4)
    base/      geom.py hojas.py convenciones.py colores.py escala.py lado.py materiales.py pdfium_lock.py
    pdf/       vectores.py abrir.py render.py
    ocr/       motor.py raster.py
    shx/       decoder.py
    ruteo/     red.py canaleta.py
    funcional/ cables.py hoja_meta.py alternativas.py puntas.py conductores.py listado.py materiales.py lector.py serializar.py
    eplan/     __init__.py pdftexto.py deteccion.py rotulo.py conexiones.py textos_taller.py conductores.py listado.py
               bandejas.py azules.py mapeo_verificado.py excel.py
    topografico/ rieles.py etiquetas.py canaletas.py autocad.py layout.py
    lectura.py             fachada: decide AutoCAD o EPLAN (funcional y topográfico)
    bornes/    catalogo.py pagina_pdf.py motor.py primitivas.py componer.py firma.py
    instructivo/ armado.py puntos.py orden.py correcciones.py estaciones.py salidas.py quitados.py marcas.py
                 pasos.py panel.py usos.py regenerar.py
    estacion8.py  terminales.py  auditoria.py  proyector.py
    wpc/       __init__.py config.py largos.py fuera.py termos.py formato.py
    exportar/  excel_listado.py pdf_buscable.py instructivo_json.py
    trabajo/   rutas.py almacen.py recursos_usuario.py cache_bornes.py
    servicio/  procesar_plano.py generar_instructivo.py
    api/       v1.py
  core.py wires.py textdec.py pdfvec.py ocr_raster.py topo.py ruteo.py eplan.py
  instructivo.py estacion8.py proyector.py bornes/                     ← PUENTES (reexportan, mismas firmas)
  web.py cli.py app.py web/*.js                                       ← adaptadores
pyproject.toml                                                        ← nuevo: «pip install -e .» instala solo planocables
```

### 2.3 Quién puede importar a quién

| Paquete | Puede importar |
|---|---|
| `base`, `datos` | nada interno |
| `pdf`, `ocr`, `shx`, `ruteo` | `base` |
| `funcional` | `base`, `pdf` y `shx`; `ocr` llega inyectado como función |
| `eplan` | `base` y `pdf` |
| `topografico` | `base`, `pdf` y `shx` |
| `bornes` | `base` y `pdf` |
| `lectura` (fachada) | `funcional`, `eplan` y `topografico` |
| `instructivo`, `estacion8`, `terminales`, `wpc`, `auditoria`, `proyector` | `base` y `ruteo`; entre ellos, sin ciclos |
| `exportar` | `base` |
| `trabajo` | `base` y `datos` |
| `servicio` | todo lo anterior |
| adaptadores (`web.py`, `cli.py`, `__main__`, `api`) | `servicio`, `trabajo`, `datos`, `exportar` y las funciones de armado |
| puentes (`programa/*.py` de hoy) | cualquier cosa; **nada dentro de `planocables` importa un puente** |

**Correcciones de la revisión que entran en esta tabla:**
- `cable_desc` va a `base/convenciones` y recibe `detalle`, no `res`. Lo usan el armado y `estacion8`; si quedara en `funcional`, el armado importaría el lector.
- `fmt_terminal`, `is_terminal_block`, `FIELD_RE`, `COLOR_INI` y `norm_label` pasan a `base` **en la etapa 1**. Si no, `funcional/alternativas` (etapa 4) tendría que importar `instructivo`.
- **Las tres formas de calcular el lado van a `base/lado.py`, cada una con su nombre.** No son copias, son tres algoritmos distintos:
  - `lado_fisico_instructivo` (`instructivo.py:1615-1627`): decide solo si 3·kr < |dy| < 80·kr;
  - `lado_wpc` (`wpc.js:57-61`): usa el eje de la fila del tag; con |dy| < 1 pt no decide;
  - `lado_e8` (`estacion8.py:116-121`): toma el riel más cercano, sin umbral, y devuelve el riel.

  Unificarlas cambia resultados (sección 10).
- Pasa lo mismo con los dos `sin_lado`: el de `instructivo.py:1634` además corta `#cable`. Y con los dos `secNum`: el de `instructivo.js:14` saca los ceros finales y el de `wpc.js:29` no.

**Prohibido dentro de `planocables`:**
- Flask fuera de `api/`;
- escribir archivos fuera de `trabajo/` y de las herramientas;
- imports tardíos para esquivar ciclos (solo se permiten para dependencias pesadas opcionales);
- `sys.path.insert`.

**Control automático (nuevo, `pruebas/probar_capas.py`):**
- revisa los imports con `ast` contra la tabla;
- busca escrituras a disco prohibidas;
- importa `wpc`, `instructivo`, `estacion8`, `ruteo` y `terminales` **sin** numpy, cv2 ni pypdf instalados. Tienen que cargar.

### 2.4 Puentes: lo que tiene que seguir existiendo con el mismo nombre

Lo usan la web, las pruebas, `prototipos/` y los scripts de `2 - Resultados/76884…/mapeo/`:

- **`core`:**
  - `process(pdf_path, log, use_ocr, pages)`: `pages` también se le pasa a `eplan.process`;
  - `write_excel`, `write_searchable_pdf` y `sheet_name`.
- **`topo`:**
  - `layout`, `layout_al_dia`, `VERSION_LECTOR` y el texto de la versión (`'topo 2026.10.02-r3'`), para no forzar a releer todos los trabajos;
  - `rail_bands`, `perfil`, `rect_of`, `snap_escala`, `RIEL_MM`, `PT_MM`, `RX_PLACA`, `PLACA_MIN_H` y `FILA_H`;
  - `geo_con_etiquetas`, `unir_partidas` y `rieles_geometria`.
- **`ruteo`:**
  - `ducts`, `Net`, `ancho` y `route_line`;
  - `probar_arreglos_pae.py:36-46` **reemplaza** `ruteo.route_line` y lee el 6.º argumento posicional. El armado tiene que seguir llamándola por atributo de módulo, o se actualiza la prueba en la misma etapa, avisando.
- **`pdfvec`:** `page_strokes` y `layer_names` (unos 20 scripts).
- **`bornes`:**
  - `primitivas` (los scripts del mapeo del PAE lo importan con un `sys.path` absoluto);
  - `motor.Motor` y lo que usa `probar_ronda3.py`: `__new__`, `familias`, `familia_de_texto`, `cuerpos`, `red_de_seguridad`, `mapear` y el constructor con una ruta;
  - `materiales_de_lineas`, `puntos_automaticos`, `componer_bornes(lay, auto, {}, {}, {})` (hoy **cambia** `lay`) y `aplicar_al_layout`;
  - y los comandos `python programa/bornes/motor.py …` y `python programa/bornes/aparamenta.py "<Excel>"` (documentados en CLAUDE.md y en `bornes/LEEME.md`).
- **`web`:**
  - `app`, `WORK`, `INS` y `usar_mismo_pdf`;
  - `gen_instructivo(jid)`, que tiene que ser **sincrónica** (`probar_ronda3.py:199-203`);
  - `job_dir` tiene que leer `web.WORK` **en el momento de la llamada** (`probar_arreglos_pae.py:134-148` lo cambia).
- **`cli.run`:** su firma `(res, outs)` la usa `app.py:79`.

---

## 3. Módulos

> Resumen por módulo. Las líneas de origen son las de hoy.

### 3.1 `base/` (solo biblioteca estándar)

| Módulo | Qué tiene | Sale de |
|---|---|---|
| `geom` | `bbox`, `DSU`, `dist`, `dentro`, `rect_of`. Los `box_dist` viejos quedan como alias **con su orden de argumentos de hoy**, que no es el mismo en cada archivo | `textdec.py:15,24`; `wires.py:25-45`; `core.py:500-507`; `instructivo.py:38-43`; `topo.py:117` |
| `hojas` | `natkey`, `sheet_name`, `zone_of`, `hoja_base`, `stacked_ref`, `H_REF`. Las variantes `natk` (`instructivo.py:1385`), `ref_apilada` y `natKey` (JS) **no se unifican** | `core.py:13,89,184,449,510`; `instructivo.py:669,926` |
| `convenciones` | `is_terminal_block`, `fmt_terminal`, `side_of`, `norm_label`, `punta_sintetica`, `sin_lado` (y `sin_lado_clave`, el otro), `clave_borne`, `clave_par`, `cable_desc(num, a, b, detalle)`, `FIELD_RE`, `LATERAL_RE` | `instructivo.py:16-33,828-857,1389-1419,1501,1634`; `estacion8.py:20`; `eplan.py:35-36`; `topo.py:32` |
| `lado` | las tres funciones de lado, con su nombre (2.3) y `lado_de_texto` (port literal de `ladoTexto`, `wpc.js:62-67`) | `instructivo.py:1615-1627`; `wpc.js:57-67`; `estacion8.py:116-121` |
| `colores` | `norm_color`, `inicial` y `en_ingles`, con la tabla de hoy | `wires.py:11-18,700`; `eplan.py:88-100`; `core.py:19`; `instructivo.py:29` |
| `escala` | `snap_escala`, `RIEL_MM`, `PT_MM`, `ESCALAS` | `topo.py:34-36,338` |
| `materiales` | `materiales_de_lineas`; los dos `FABRICANTES_RE` quedan **separados** | `motor.py:215-231`; `instructivo.py:2128` |
| `pdfium_lock` | `PDFIUM_LOCK` y `documento(pdf)`, un *context manager* que toma el lock, abre, usa y cierra. Nunca devuelve un documento que se pueda usar fuera del lock | `ocr_raster.py:7` |

### 3.2 Motores

| Módulo | Qué tiene | Sale de | Pesadas |
|---|---|---|---|
| `pdf/vectores` | `layer_names`, `page_strokes`, `segmentos` | `pdfvec.py`; `proyector.py:18` | pypdf |
| `pdf/abrir` | `lector(pdf: bytes)`, `huella(pdf)` (sha1), `desproteger(pdf) -> bytes` en memoria (verificado: pypdfium2 5.13 guarda a `BytesIO`), sin `%TEMP%` | `eplan.py:44-69,267-302` y los `PdfReader` sueltos | pypdf y pypdfium2 |
| `pdf/render` | `pagina_png`, `region_png`, `pagina_rgb`, `recorte`. Tiran `ValueError` en lugar del `abort` de Flask. **Versión de render** en el nombre de los PNG en caché | `web.py:256-286,663-685`; `motor.py:79-87`; `eplan.py:1553`; `topo.py:94-111` | pypdfium2, Pillow y numpy |
| `ocr/motor` | **un solo** RapidOCR (hoy hay dos): `disponible()`, `leer(img)` | `textdec.py:186-191`; `ocr_raster.py:6-15` | rapidocr (opcional) |
| `ocr/raster` | `page_items(pdf, pi, motor)` | `ocr_raster.py:35` | rapidocr, numpy, cv2 y pypdfium2 |
| `shx/decoder` | `Decoder(glifos, memoria_ocr=None, ocr=None, use_ocr=True)`; `dec.memoria_nueva` (lo aprendido, para que lo guarde `trabajo/`); `page_text`. numpy y cv2 se cargan solo dentro de `render_line`. Se conserva que con `use_ocr=False` no se consulta la memoria | `textdec.py` | ninguna obligatoria |
| `ruteo/red` | `Net` (**con estado**, una por instructivo), `route_line` (misma firma), `length`, `ancho`, `li_exit`, `largo_mm` (nuevo: `int(round(length·escala/10)·10)`, con el `round` de Python de hoy) | `ruteo.py:40-409`; `instructivo.py:1488,1919` | ninguna |
| `ruteo/canaleta` | `canaleta_mm(ruta, ductos, escala, tol=0.6)`: la parte de la ruta que corre dentro de las canaletas, port de `wpc.js:114-122` con `floor(x+0.5)` | `wpc.js:114-122` | ninguna |

### 3.3 Lectores

**`funcional/` (AutoCAD).**

| Módulo | Qué tiene | Sale de |
|---|---|---|
| `cables` | `WireGraph`, `assign`, `is_wire_layer`, `ConfigCapas` (las capas de hoy por defecto) | `wires.py`; `core.py:12` |
| `hoja_meta` | `page_meta`, `text_scale`, `has_images` | `core.py:12-19,23,166,177` |
| `alternativas` | `alternativas_hoja`, `alternativa`, `alternativas`, `alternativas_del_cable` | `instructivo.py:28,932-1050` |
| `puntas` | lectura geométrica de las puntas: `Symbols`, `describe_end` y sus ayudantes | `instructivo.py:46-913` |
| `conductores` | `arbol`, `conductors(res)`; `conductores_a_json` / `conductores_desde_json` (nuevos). El memo devuelve **copia profunda**, porque `build` cambia `c['pares']` (`instructivo.py:1737`) | `instructivo.py:1053-1381` |
| `listado` | `build_cable_list`, `build_routes`, `puntas_reales`, `sheet_refs`, `route_refs`; **banderas estructuradas** que se suman a las frases de hoy (`revisar`, `nota_plano`, `derivacion`), sin cambiarlas | `core.py:188-472` |
| `materiales` | `materiales_funcional` | `instructivo.py:2133` |
| `lector` | `leer_autocad(pdf, *, recursos, use_ocr=True, pages=None, progreso=None, log=None) -> Result`. Se conserva el log `'Hoja i/n'` | `core.py:110-160` |
| `serializar` | `listado_json(res)`: lo que hoy es `resultado.json`, sin nombre ni fecha | `web.py:60-71` |

**`eplan/`.** La fachada `__init__` conserva las firmas de hoy y es la **única** con cachés, con lock. Ojo: `_ES` se indexa hoy por (ruta, tamaño, mtime) y no por sha1. Si se pasa a sha1, la detección se reutiliza en otros casos; se cambia avisando.

| Módulo | Sale de `eplan.py` |
|---|---|
| `pdftexto` (palabras y renglones por hoja) | `:118-264` |
| `deteccion` (`es_eplan`, lista sí/no, `FALTA_LISTA`) | `:305-371` |
| `rotulo` (rótulo, documento y revisión) | `:374-473` |
| `conexiones` (lista de conexiones → filas JSON) | `:29-114` (sin lo de 3.1), `:476-556` |
| `textos_taller` (tipo de bornera, texto general) | `:589-845` |
| `conductores` y `listado` (incluida la cabecera de `process` y `tag_base`) | `:848-1150` |
| `bandejas` (rieles, canaletas, placas, `VERSION_LECTOR`), con `_iou` y `_frac_dentro` | `:1153-1519` |
| `azules` (canaletas de intrínsecos sobre una imagen ya renderizada) | `:1520-1578` |
| `mapeo_verificado` (`elegir_mapeo(mapeos, doc, rev)`, `aplicar_puntos(..., manuales=…)` puro) | `:559-586,1582-1645` |
| `excel` (filas de la hoja «Lista de conexiones», en el mismo workbook, sin reabrir el archivo) | `:1648-1678` |

**`topografico/`:**
- `rieles`, `etiquetas` (el OCR del recorte llega como función) y `canaletas` (`ducts` sin pypdf);
- `autocad.leer_paginas(pdf: bytes, …)`, que abre el PDF **una sola vez**, y `armar_layout(paginas, known_tags)`, puro;
- `layout`: `aplicar_overrides`, `aplicar_correcciones` (copian, no cambian el original) y `topo_para_visor`.

**`lectura.py` (fachada).** Es la que decide entre AutoCAD y EPLAN, y así corta los ciclos:
- `es_eplan(pdf)`;
- `leer_plano(pdf, *, recursos, …)`;
- `leer_layout(pdf, known_tags, *, recursos)`;
- `version_lector(...)`, que da los **mismos textos de hoy**;
- `layout_al_dia(lay)`.

**`bornes/`:**
- `catalogo`: `modelo_por_materiales`. `familia_de_texto` es un método de `Motor` que usa `self.familias`: se mueve con una firma nueva, `familia_de_texto(texto, familias)`, y queda el método como alias.
- `pagina_pdf`: `leer_pagina(pdf: bytes, pagina) -> {trazos, etiquetas, W, H}`. Es el único con pypdf, pypdfium2, numpy y cv2.
- `motor`: `Motor(pagina_leida o pdf, usos, catalogo, materiales)`, sin disco ni `sys.path`.
- `componer`: devuelve un dict. El puente conserva `componer_bornes`, que cambia `lay` como hoy.
- `firma`: lista **explícita** de los módulos que calculan puntos (`motor`, `primitivas`, `pagina_pdf`, `catalogo`), con una prueba de que cambiar un byte obliga a recalcular. Si no, después del refactor se hashearían los puentes y la web usaría un mapeo viejo en silencio.
- `bornes.mapear(topo_bytes, usos, materiales, *, catalogo)` (nuevo, puro). `usos` y `materiales` los calcula el servicio: así `bornes` deja de importar `instructivo`.

### 3.4 Armado (dict → dict, solo biblioteca estándar)

| Módulo | Qué tiene | Sale de |
|---|---|---|
| `instructivo/armado` | `armar(conductores, detalle, lay, *, alternativas, con_lista, reglas, max_lineas=7) -> dict` (mismas claves que hoy). `build(res, lay)` queda en el puente | `instructivo.py:1531-2009` |
| `instructivo/puntos` | las closures de `build` (`base_txt`, `buscar`, `flip`, `exacto`, `confianza`, `lado`, `texto`, `funcional`, `lateral`, `en_bandeja`, `bandeja`) en un `Contexto(lay, reglas)`. `texto()` devuelve `(texto, cambio_de_lado)`, sin el acumulador oculto | `:1566-1679,1843-1857` |
| `instructivo/orden` | `clave_orden`, `mods` de los relés, encadenado de tramos, borrado de líneas repetidas, orden por `orden` | `:1687-1725,1839-1842,1920-1939` |
| `instructivo/correcciones` | `aplicar_correcciones`, `parsear_bornes_manuales` | `:1791-1833,2181-2222` |
| `instructivo/estaciones` | `estacion_de`, `separar_otra_estacion` | `:1556-1563,1940-1969` |
| `instructivo/salidas` | `puntos_salida`, `grupo_salida`, `sale_abajo`, `rutear_salidas`, más `es_intrinseco` y `miembros` (nuevos, para que `salidas.js` deje de duplicarlos) | `:1437-1490,1880-1919` |
| `instructivo/quitados` | `separar_quitados` | `:1493-1528` |
| `instructivo/marcas` | `fusionar_con_previo(ins, previo)`, con **los tres comparadores de hoy**, cada uno con su nombre (hechos por pertenencia, quitados uno a uno con tipo, fotos por número y origen del primer cable). Unificarlos cambia resultados (sección 10) | `web.py:462-513` |
| `instructivo/pasos` | `agrupar_pasos` | `:1974-1997` |
| `instructivo/panel` y `usos` | `known_tags`, `componentes_panel`, `usos_bandeja` (reciben los conductores ya calculados) | `:2016-2125` |
| `instructivo/regenerar` | `armar_instructivo(...)`: el pipeline puro (3.6) | `web.py:399-513` |
| `estacion8` | `build(conductores, detalle, lay, ins)`. Suma códigos estables (`otra_cod`, `zona_cod`) **además** de los textos de `DONDE`, y `canaleta_mm` por línea | `estacion8.py:38-242` |
| `terminales` | `terminal(linea, lado, lineas, tabla)` | `instructivo.js:18-33` |
| `auditoria` | `secciones(ins, reglas)` | `auditoria.js:14-120` |
| `proyector` | `orificios_de_segmentos(segs, pag, region, escala)`. `orificios(pdf_path, …)` queda en el puente | `proyector.py:12-168` |

### 3.5 `exportar/`, `trabajo/`, `servicio/`

- **`exportar/`:**
  - `excel_listado(res, *, fecha, hojas_extra) -> bytes`;
  - `pdf_buscable(pdf_bytes, res, raster_ocr) -> bytes`;
  - `instructivo_json(ins, nombre)`, el «⭳ JSON» de hoy.
- **`trabajo/`** (la única capa con disco):
  - `rutas`: `WORK` y `job_dir`. `job_dir` lee `web.WORK` al llamarse, para no romper `probar_arreglos_pae`. No valida el id ni recorta `archivo`: el trabajo del PAE usa una ruta relativa y el del TPT vive en la carpeta `tpt`.
  - `almacen.Trabajo(dir)`: estado, resultado, layout, instructivo, fotos y cachés de PNG.
  - **`instructivo.json` con número de versión (`rev`).** Un PUT con un `rev` viejo da 409 y el navegador recarga. La regeneración calcula sin lock y, **al final**, bajo el lock, vuelve a leer del disco las secciones del usuario (`hecho`, `foto`, `wpc`, `auditoria`, `quitados`, `salidas`, `estaciones`, `bornes_usuario`, `estacion8.hechos`, `proyector`) y las fusiona. Arregla la pérdida de marcas de 1.2.9.
  - `recursos_usuario`:
    - memoria OCR: vuelve a leer y fusiona antes de escribir, con `.tmp` único y `os.replace`; y un modo **solo lectura** para las pruebas y para la otra app;
    - mapeos verificados, con caché por mtime;
    - `bornes.json` y `correcciones.json` del trabajo.
  - `cache_bornes`: `bornes_auto.json` y la firma.
- **`servicio/`:**
  - `procesar_plano.procesar(trabajo, opciones, progreso)`. Junta `run_job` y `cli.run`, incluidas las reglas «EPLAN sin BUSCABLE» y «al terminar un EPLAN, armar el instructivo con las bandejas del mismo PDF».
  - `generar_instructivo.generar(...)`, con `RUN_LOCK`.

### 3.6 El pipeline puro

```python
armar_instructivo(res, lay_crudo, *, previo, correcciones, bornes_manual, overrides, topo_nuevo,
                  ubicar_bornes,   # función (res, lay, manuales) -> (mapeo, parche); EPLAN verificado o motor
                  meta,            # {generado, topografico}: la fecha entra acá
                  reglas) -> {'ins': dict, 'avisos': [...]}
```

Pasos:
1. Overrides y correcciones.
2. `ubicar_bornes`.
3. Valores por defecto: E6, 35 mm² → E8 y salidas (`topo_nuevo` → `salidas.preguntar`).
4. `armar`.
5. `estacion8.build`.
6. Fusión con el instructivo anterior.
7. Metadatos.

Lo usan la web **y** `volcar_trabajo.py`, así deja de haber dos copias. Antes de juntarlas hay que decidir si `volcar` pasa el layout por JSON como la web (etapa 11).

### 3.7 Contrato del mapeo (faltaba en el borrador)

`layout.json` se escribe **antes** de mapear los bornes, así que no trae `bornes`, `renombrar`, `bornes_conf`, `bornes_nota` ni `renombrar_auto`. Sin ellos, un instructivo armado afuera sale con puntos aproximados. Por eso hay un contrato aparte, **`layout_mapeado@1`**: el layout con los bornes ya puestos. Es lo que necesita la otra app para armar el mismo instructivo sin correr el motor.

### 3.8 Contratos en JSON

- **Coordenadas:** pt del PDF, con origen abajo a la izquierda; `largo_mm` múltiplo de 10; `escala` en mm/pt.
- **`listado@1`:** lo que hoy es `resultado.json`, sin nombre ni fecha. `stats` queda fuera de la comparación de las pruebas, porque depende de la memoria OCR.
- **`conductores@1`:** conductores, `detalle`, `alternativas` y `con_lista`. Que vaya y vuelva por JSON sin perder nada se verifica en la etapa 9.
- **`layout@1`** y **`layout_mapeado@1`**.
- **`instructivo@1`:** separa lo **calculado** de lo **del usuario**. Dos claves mezclan las dos cosas y se documentan como mixtas: `quitados` (`build` la recalcula) y `proyector` (los orificios automáticos los calcula y guarda un GET).
- **`wpc@1`:** las filas y el CSV.

**Primero hay que ver qué consume hoy la otra app** (seguramente el «⭳ JSON», `instructivo.js:762-778`, y/o `resultado.json`). Ese formato se versiona como primer contrato, en lugar de inventar uno paralelo.

### 3.9 «Qué tocar» (va en `planocables/__init__.py` y en CLAUDE.md)

| Quiero cambiar… | Dónde | Dato / parámetro |
|---|---|---|
| Letra SHX mal leída | `shx/decoder` | `glyphdict.json`, memoria OCR |
| Número que no se pega a su cable | `funcional/cables.assign` | `ConfigCapas` |
| Color o sección mal heredados | `funcional/listado` | — |
| Tag, borne, QUATTRO o ARRIBA/ABAJO (AutoCAD) | `funcional/puntas.describe_end` | — |
| Formato del texto de la punta | `base/convenciones.fmt_terminal` | — |
| N-1 tramos, unión en T | `funcional/conductores` | — |
| EPLAN: cabecera, tipo de bornera, rótulo | `eplan/conexiones`, `eplan/textos_taller`, `eplan/rotulo` | — |
| Rieles y canaletas | `topografico/rieles`, `topografico/canaletas`, `eplan/bandejas` | constantes de cada módulo |
| Modelo de bornera nuevo | — | `bornes/catalogo.json` |
| Producto EPLAN verificado | — | `mapeos_verificados/<doc>_rev<rev>.json` |
| Orden de cableado | `instructivo/orden` | `taller.json` |
| Lado físico, punto exacto o aproximado | `instructivo/puntos`, `base/lado` | `taller.json` |
| E8 y 35 mm² | `instructivo/estaciones` | `taller.json`, `estaciones_tag` del mapeo |
| Salida a LI / LD | `ruteo/red.li_exit`, `instructivo/salidas` | `taller.json` |
| Quitados y marcas al regenerar | `instructivo/quitados`, `instructivo/marcas` | — |
| Terminal o pollera | `terminales` | `terminales.json` |
| Largos, giros, «fuera» y columnas de la WPC | `wpc/` | `wpc.json` |
| Secciones de la auditoría | `auditoria` | `taller.json` |
| Frases que se comparan entre módulos | tabla de protocolos (1.2.8) | — |

---

## 4. Datos y configuración

**Mecanismo:**
1. El núcleo **recibe** los datos como argumentos: `Decoder(glifos=…)`, `elegir_mapeo(mapeos, …)`, `Motor(…, catalogo=…)`, `wpc.config(...)`, `terminal(…, tabla)` y `armar(…, reglas)`. No lee nada por su cuenta.
2. `planocables/datos/` es el único que lee los recursos, con caché por (ruta, mtime). Hoy `glyphdict.json` se parsea en cada `Decoder`, unos 0,26 s cada vez.
3. Prioridad de cada recurso:
   1. argumento explícito;
   2. la carpeta de `PLANOCABLES_DATOS`;
   3. **la ruta de hoy** (`programa/glyphdict.json`, `programa/bornes/catalogo.json`, `programa/web/wpc.json`…);
   4. la copia empaquetada.

   **No se mueve ningún archivo de datos salvo que lo pidas.**
4. Los recursos que cambian (memoria OCR, `bornes_auto.json`) los escribe solo `trabajo/`. `aparamenta.json` lo escribe solo su herramienta.

| Recurso | Hoy | Cómo llega al núcleo |
|---|---|---|
| `glyphdict.json` | se lee en cada `Decoder` | `Decoder(glifos=dict)` |
| `ocr_cache.json` (en git, 11 245 renglones) | se lee y se reescribe solo | `Decoder(memoria_ocr=dict)` → `memoria_nueva` → `trabajo` lo guarda; `PLANOCABLES_MEMORIA_OCR=solo-lectura` para pruebas y otra app |
| `bornes/catalogo.json` | se lee en cada cálculo | `Motor(…, catalogo=dict)` |
| `mapeos_verificados/*.json` | se leen en cada llamada | `elegir_mapeo(mapeos, doc, rev)` |
| `web/wpc.json` | solo JS | `wpc.config(base, producto, trabajo)`; se sigue sirviendo en `/static/wpc.json` |
| `web/terminales.json` | solo JS | `terminal(…, tabla)` |
| `taller.json` (nuevo) | constantes repartidas en el código | `armar(…, reglas)`, `estacion8.build`, `auditoria.secciones` |

`taller.json` sale con **exactamente los valores de hoy**:
- E6 por defecto, y 35 mm² → E8;
- la regla de 220 VAC (marrón / blanco);
- azul = intrínseco;
- `max_lineas` 7;
- el orden del relé;
- los umbrales del lado (3·kr, 80·kr…);
- las etapas fijas (`instructivo.js:285,397`);
- los umbrales de la auditoría (90 / 16 / 150 / 60 / 1,5 pt);
- las constantes de E8 sin escala: 12 pt entre rieles, 14 bornes y 3,5 pt, −12 pt y 3,0 pt. Ojo: hoy **E8 no escala con kr como E6**; está en las preguntas.

Cambiar un valor de `taller.json` es cambiar una convención del taller: **hay que preguntarte**.

---

## 5. Lista WPC en Python

### 5.1 API (sin dependencias pesadas: json, math y re)

```python
# planocables/wpc/
config(base: dict, producto: str|None = None, trabajo: dict|None = None) -> dict
lateral_info(estacion8: dict) -> {'sale': {...}, 'par': {...}}        # wpc.js:123-137
filas(ins: dict, cfg: dict) -> list[dict]                              # wpc.js:87-106
largo(fila, cfg, e8l, topo) -> {mm, como, falta?}                      # wpc.js:140-171
motivo_fuera(fila, cfg) ; reemplazo(linea, cfg, producto)              # wpc.js:35-53
giro(fila, cfg, topo)                                                  # wpc.js:57-84 (usa base/lado.lado_wpc)
csv(filas, cfg) -> str                                                 # wpc.js:173-184
archivo_wpc(filas, plantilla) -> bytes                                 # fase 2, si hace falta (preguntas)
```

**Entrada:** el instructivo completo, sin el layout crudo:
- `pasos[].lineas[]`, `pendientes[]` y `otra_estacion[]`;
- `topo` (`filas`, `comp`, `ductos`, `escala`) y `estacion8` (`laterales`, `afuera`);
- `producto.documento`;
- `wpc`: las ediciones a mano, con la clave `num|origen|destino`.

Si falta `producto`, se completa desde `layout.json`, como hace `web.py:594-595`. Si no, a los instructivos viejos del PAE no se les aplican los reemplazos.

**Salida:**
- las filas en orden de cableado: pasos, después pendientes y después otra estación;
- el CSV:
  - con BOM y sin encabezado;
  - columnas separadas por `;` y líneas terminadas en CRLF;
  - 49 columnas: 7 = largo, 9 = sección con coma, 10 = color, 12 y 20 = número, 22 = giro de los termos, y las `fijos`;
  - archivo `<plano sin .pdf> - WPC.csv`.

### 5.2 Parámetros configurables

Hoy `wpc.json` es global, y el trabajo puede pisar algunos valores (`ins.wpc.cfg`). Se propone sumar el **nivel producto**. Precedencia: **trabajo > producto > global**.

| Parámetro | Hoy | Qué es | En la pantalla |
|---|---:|---|---|
| `margen_bandeja` | 100 | sobrante sobre el recorrido (bandeja, y LI/LD sin E8) | sí |
| `agregado_bandeja` | 75 | agregado del taller (bandeja) | sí |
| `acometida` | 75 | borne → canaleta (sale a LI con E8) | sí |
| `curva_LI` | 100 | curva de la posterior → LI | sí |
| `acometida_LI` | 150 | canaleta de la lateral → borne | sí |
| `puerta` | 1850 | sigue a la puerta o la placa | sí |
| `margen_LI` | 200 | pendientes lateral ↔ lateral | sí |
| `extra_puerta` | 1500 | pendientes lateral → puerta | sí |
| `extra_LI` / `extra_LD` | 1500 / 400 | a LI / LD sin E8 | sí |
| `agregado_LI` | 200 | pendientes, y LI sin E8 | sí |
| `agregado_puerta` | 350 | solo en pendientes. La rama de `wpc.js:168` **nunca se alcanza** (preguntas) | sí |
| `redondeo` | 50 | `ceil(v/r)·r` | sí |
| `largo_sin_ruta` | 1000 | cable sin recorrido (también con largo 0) | sí |
| `largo_pendiente` | 2000 | pendiente sin dato de E8 | sí |
| `pendientes` / `otra` | false | incluir pendientes / otra estación | sí |
| `fuera.*` | 35 mm², ≤ 0,5 mm², regex | qué queda fuera del arnés | no |
| `termos.*` | `0\|0`, `180\|0`, `0\|180` | giro de los termos (columna 22) | no |
| `fijos.*` | todos 0 | columnas fijas (solo corta) | no |
| `colores` / `codigos` | 13 / 20 | color → código WPC | no |
| `reemplazos[documento]` | PAE: negro 4 → violeta 2,5; rojo 4 → naranja 2,5 | solo en la lista | no |

**Cosas de la configuración que hay que respetar:**
- **Qué puede pisar el trabajo:** hoy `ins.wpc.cfg` pisa **solo** los números (y `pendientes` / `otra`). `fuera`, `termos`, `fijos`, `colores` y `reemplazos` salen solo de `wpc.json`. `config()` hace lo mismo.
- **Los valores por defecto de `wpc.js`** se llevan tal cual, y `config()` avisa si falta una clave:
  - un parámetro que falta vale 0;
  - si `wpc.json` no trae `fijos`, el JS usa 10/1/1/8/10/8 (el archivo de hoy los trae en 0);
  - si no hay `redondeo`, vale 1.
- **Nueva sección `parametros` en `wpc.json`:** etiqueta, unidad, paso y mínimo de cada parámetro. Así un parámetro nuevo o uno por producto aparece en la pantalla sin tocar el JS (hoy las etiquetas están fijas en `wpc.js:195-199`).
- **Clave de producto:** en EPLAN es el documento del rótulo (`ZPL-76884`). **En AutoCAD hoy no hay** (`producto_de` da `None`): hay que definirla, por ejemplo con el número de plano (preguntas).

### 5.3 Que dé igual byte a byte

- `Math.round` → `floor(x + 0.5)`. Python redondea «al par», así que `round()` no sirve. `Math.ceil` → `math.ceil`.
- Un valor no numérico da `NaN` en JS y sale «NaN» en el CSV; en Python, `math.ceil(nan)` tira un error. Se replica o se avisa, pero no se cae.
- Números como en JS: `900` y no `900.0`; `1` y no `1.0`. `parseFloat` toma el número del principio del texto. `coma()` cambia **solo el primer** punto. `parseFloat(secc) === sec` es una comparación exacta.
- Las claves con `undefined` se escriben como `'undefined'`, igual que en JS.
- Las regex de `fuera` se compilan con `re.IGNORECASE`. Hay que avisar si una regex usa algo que JS y Python interpretan distinto. Hoy son solo ASCII, así que dan igual.
- `normC`: minúsculas, NFD y sin acentos.
- En `lateral_info`, en `sale` gana el primero y en `par` el último.
- `fuera` usa la sección **ya reemplazada**.
- Las ediciones a mano mandan: largo, color, giro, excluir e incluir.
- La rama de `:168` que nunca se alcanza, y el `ladoTexto` de N.5/N.6, se replican **tal cual**.
- El CSV se devuelve como texto con `﻿` y se codifica en `utf-8`, no en `utf-8-sig`, para no duplicar el BOM. No se usa el módulo `csv`, que agrega comillas.

### 5.4 Cómo queda la web

- **Endpoints nuevos:**
  - `POST /api/wpc/filas` recibe `{instructivo}` y devuelve `{filas, csv, cfg}`. No guarda nada: usa el instructivo que tiene el navegador, así no compite con el guardado diferido. **Es el mismo endpoint que puede usar la otra app**;
  - `GET /api/trabajo/<id>/wpc.csv`;
  - `GET /api/config/wpc`, con los parámetros y sus etiquetas.
- **Transición («modo doble»):** durante un tiempo, `wpc.js` calcula las dos cosas, la suya y la del servidor.
  - Si difieren, lo anota en la **consola**; el taller no ve el aviso.
  - Si el servidor no tiene el endpoint (no se reinició, o es la copia de Descargas), usa su propio cálculo.
  - Si las respuestas llegan desordenadas, usa la última pedida.
- **Después:** `wpc.js` queda solo como interfaz: la tabla, las ediciones y la descarga.

---

## 6. Lógica del taller que hoy está en JavaScript

| Lógica | Hoy | Destino | Cuándo |
|---|---|---|---|
| Lista WPC | `wpc.js:28-184` | `wpc/` | **etapa 2** |
| Ruta dentro de las canaletas | `wpc.js:114-122` | `ruteo/canaleta` | etapa 2 |
| Lado del punto y del texto (variante WPC) | `wpc.js:57-67` | `base/lado` | etapa 2 |
| Terminal y pollera | `instructivo.js:22-33`; copia distinta en `estacion8.js:22-34` | `terminales.py` (para la otra app). **El navegador sigue calculándolo**: si es pino o doble depende de las líneas que tiene en ese momento, que cambian al quitar o mover cables sin regenerar | etapa 13; depende de si la otra app es Node |
| Grupos de salida e intrínsecos | `salidas.js` | `instructivo/salidas` | etapa 13 |
| Secciones de la auditoría | `auditoria.js:14-120` | `auditoria.py`, o un módulo JS compartido si la otra app es Node | etapa 13 |
| «⭳ JSON» del instructivo | `instructivo.js:762-778` | `exportar/instructivo_json` | etapa 12 |
| «A revisar» por regex sobre frases | `app.js:231,249,285` | banderas del listado | etapa 8 (se suman) |
| Quitar, devolver, mover de estación, mover una punta | `instructivo.js:373-505` | **quedan en el navegador** (son instantáneas). Mover una punta y volver a rutear en el servidor cambia resultados: preguntas | — |
| Homografía y encuadre del proyector, TSV del listado | `proyector.js`, `app.js` | quedan (son de la interfaz) | — |

**Si la otra app es Node:** el terminal, la auditoría y los grupos de salida conviene sacarlos a **un módulo JS puro** que usen el navegador y Node, en lugar de pasarlos a Python. Si no, la otra app tendría que llamar a Python para algo que hoy corre en el cliente. Por eso la etapa 13 se decide cuando sepamos qué es.

---

## 7. La otra app (batfer.local:3001)

### 7.1 Qué necesita cada función

| Función | Módulos | Arrastra | Si es Python | Si es Node |
|---|---|---|---|---|
| **Listado** (ya lo tiene) | `lectura`, `funcional`, `eplan`, `shx`, `pdf`, `base`; datos: glifos y memoria OCR (solo lectura) | pypdf; pypdfium2 (EPLAN); rapidocr, numpy y cv2 solo con OCR; openpyxl y reportlab solo para el Excel y el buscable | `lectura.leer_plano(pdf)` → `listado_json(res)` | **No portarlo**: son más de 3 000 líneas de geometría con firmas exactas. CLI o servicio |
| **Visor del instructivo** (ya lo tiene) | Mostrar: nada (JSON + PNG). Armar desde JSON: `instructivo/*`, `ruteo`, `base`, con `conductores@1` y `layout_mapeado@1` | armar desde JSON: **nada pesado**; desde los PDF: todo, más el motor de bornes | `armar_instructivo(...)` | CLI o servicio; PNG por un render que no guarda nada (7.3) |
| **Auditoría** (ya la tiene) | `auditoria`, `terminales`, `base` | nada | import | módulo JS compartido o servicio (sección 6) |
| **WPC** (nueva) | `wpc`, `ruteo/canaleta`, `base`; dato: `wpc.json` | **nada** | `wpc.filas(ins, wpc.config(...))`, `wpc.csv(...)` | `python -m planocables wpc instructivo.json --config wpc.json` o `POST /api/wpc/filas` |

### 7.2 Si es Python

- `pip install -e "C:\Buscar Termos en plano"` (con el `pyproject.toml` nuevo) instala **solo** `planocables`. No hay que meter `programa/` en `sys.path` ni chocan los nombres.
- Extras opcionales: `[pdf]`, `[ocr]`, `[excel]`, `[web]`. La WPC sola no necesita ninguno.
- Versión mínima de Python: 3.10, a verificar con la de la otra app (en el taller hay 3.14).

### 7.3 Si es Node

**Opción A, línea de comandos (recomendada):** `python -m planocables {listado|layout|instructivo|wpc|salidas}`, llamada con `child_process`.
- La salida estándar lleva **solo JSON en UTF-8**. Los logs van a stderr: hoy `core.process`, `topo.layout` y `eplan` imprimen a stdout por defecto, y en Windows usarían cp1252, que rompe `→`, `²` y `↔`.
- `json.dumps(allow_nan=False)`, porque Node rechaza `NaN`.
- Códigos de salida claros; `cwd` o `PYTHONPATH` documentados.

**Opción B, servicio HTTP aparte**, en **otro puerto** y no en el servidor del taller:
- solo `/api/v1`, sin estado, con un token;
- `RUN_LOCK` (un plano a la vez) y la memoria OCR en solo lectura;
- un render de PNG que no guarda nada (recibe el PDF, la hoja y la región).

**No abrir el servidor del taller a la red.** Hoy lo protege el bind a `127.0.0.1` (`web.py:797`), más que `solo_local`, que mira el encabezado Host, que se puede falsificar. Si se abre, quedan expuestos sin clave:
- `/api/salir`, que cierra el programa;
- `DELETE /api/trabajo/<id>`, que borra la carpeta;
- «abrir carpeta», que lanza el Explorador.

---

## 8. Cómo se trabaja sin cortar al taller

- **Copia aparte:** un `git worktree` de `sistema_modular` en otra carpeta. El taller sigue corriendo `programa/web.py` del repo de siempre. Hoy la web y el desarrollo comparten carpeta, y un `.js` nuevo se ve con solo recargar: JS nuevo con Python viejo rompe la WPC en producción.
- **Pruebas en otro puerto**, con `PLANOCABLES_PORT` y un `PLANOCABLES_HISTORIAL` temporal (`launch.json` ya tiene configuraciones así). Nunca contra `3 - Historial web` del usuario.
- **`/api/version`** (nuevo): commit, ruta de `web.py` y versiones de los lectores, a la vista en la interfaz. Así se distingue el repo de la copia de Descargas.
- **Una etiqueta de git antes de cada etapa**, para volver atrás si el taller encuentra algo.
- **`pythonw`:** el `.bat` corre la web sin consola (stdout = None). Ningún módulo puede escribir en stdout al importarse. La prueba de humo incluye un arranque con `pythonw`.
- **Otros arreglos que entren mientras tanto** (por `pruebas`): se traen a `sistema_modular` al empezar cada etapa, no al final. `instructivo.py` (130 KB) es donde más van a chocar.

---

## 9. Etapas

Cada etapa es uno o pocos commits en `sistema_modular`. **Al terminar cada una, la web anda igual y la batería B da igual.**

### Batería B (después de cada etapa)

```
# 75287: sacar ac0f0949510a a una carpeta temporal con git archive (nunca al historial del usuario)
python pruebas/volcar_trabajo.py "<tmp>/3 - Historial web/ac0f0949510a" <tmp>/salida_75287.json --sin-cache
python pruebas/volcar_trabajo.py pruebas/trabajos/66817 <tmp>/salida_66817.json --sin-cache --relayout --puntos <tmp>/puntos_66817.json
python pruebas/volcar_trabajo.py pruebas/trabajos/76884 <tmp>/salida_76884.json --sin-cache --relayout
python pruebas/volcar_trabajo.py pruebas/trabajos/tpt   <tmp>/salida_tpt.json   --sin-cache --relayout
python pruebas/comparar_bases.py <tmp> pruebas/bases           # nuevo
python pruebas/evaluar_bornes.py <tmp>/puntos_66817.json --ref prototipos/_referencia_66817/bornes_referencia.json --no-guardar
python pruebas/probar_arreglos_pae.py ; python pruebas/probar_ronda2_topo.py ; python pruebas/probar_ronda3.py ; python pruebas/probar_proyector.py
python pruebas/probar_wpc.py ; python pruebas/probar_web_humo.py ; python pruebas/probar_capas.py          # nuevos
```

Todo con `PLANOCABLES_MEMORIA_OCR=solo-lectura` (desde la etapa 1).

Resultados esperados:
- **75287:** IGUAL a la base.
- **66817:** 75/75 puntas exactas y 104/104 bornes.
- **PAE:** 136 / 30 / 24 / 0.
- **TPT:** igual a la ronda 3.
- Todas las `probar_*`: TODO OK.

**`comparar_bases.py`** compara una lista explícita de campos e ignora los que cambian solos: `segundos`, tiempos, `stats`, `generado`, `fecha`, `mapeo.de_cache`, `log` y `ts`.

### Tabla

| # | Qué cambia | Cómo se verifica | Riesgo |
|---|---|---|---|
| **0** | **Red de seguridad, sin tocar `programa/`.** (a) Con tu OK, commit del estado actual **incluidas `pruebas/bases` y `probar_*.py`**, sin los borrados de tus datos. (b) Worktree aparte. (c) `comparar_bases.py`; `--puntos` en `volcar_trabajo`. (d) Bases nuevas, sacadas **antes** de mover nada: listado completo (extendiendo `volcar_cables.py`), layout y E8. (e) **Instructivos completos congelados** (con `estacion8`, `topo` y `producto`), generados con `web.gen_instructivo` sobre copias temporales; más una copia de solo lectura del instructivo del PAE con marcas reales (`ce9fc4d9fcbd`) y la del 75287 (111 líneas con «hecho»), para probar la fusión de marcas. (f) **Golden de la WPC y del terminal:** se corre `wpc.js` en Node con un DOM mínimo, o en el navegador del programa, sobre esos instructivos. Se suman casos sintéticos: reemplazo de 4 mm², `cfg` con textos (`'100'`, `''`, `'abc'`), pendientes y otra estación, ediciones a mano. (g) `probar_web_humo.py` con `test_client` sobre una copia temporal, más el arranque con `pythonw`. (h) B con `PYTHONHASHSEED=0` y `=1`, para saber si hoy algo depende del orden de los sets. (i) Regresión A/B: un worktree del commit base + `PLANOCABLES_PROGRAMA`, sobre **todos** los PDF de `1 - Planos/` (no solo los 4 con base) | B da como hoy; las bases nuevas quedan en `pruebas/bases/` | bajo |
| **1** | **Esqueleto y `base/`.** `pyproject.toml`; `planocables/` con `base/*` (incluidos `fmt_terminal`, `is_terminal_block`, `FIELD_RE`, `COLOR_INI`, `norm_label`, `cable_desc(detalle)` y `lado`); `PDFIUM_LOCK` en `base`; numpy y cv2 se cargan solo dentro de `render_line`; memoria OCR **en solo lectura** opcional; `probar_capas.py`. Los archivos de hoy importan de `base` con los mismos nombres | B + capas | bajo (cuidado con el orden de argumentos de `box_dist`) |
| **2** | **WPC en Python** (`wpc/`, `ruteo/canaleta`), endpoints, sección `parametros` en `wpc.json`, nivel producto, `wpc.js` en modo doble | `probar_wpc.py`: CSV **byte a byte** igual al golden, en todos los instructivos y casos; control a mano: 1161 → 900 | medio (redondeos y formato de números) |
| **3** | `wpc.js` queda solo como interfaz, después de un tiempo en el taller sin diferencias en la consola | `probar_wpc` + humo | bajo |
| **4** | **Cortar los ciclos:** `eplan` usa `base` (`zone_of`, `natkey`, `snap_escala`, `is_terminal_block`, `COLOR_INI`, `norm_color`); `funcional/alternativas`; `topografico/canaletas` (puente `ruteo.ducts`, `ruteo` sin pypdf); `lectura.py`, a la que delegan `core.process` y `topo.layout`; `proyector` usa `pdf/abrir`. Mientras tanto, el `except` amplio de `core.py:396,411` **anota** el error | B + listado + layout con la misma `version_lector` | medio-bajo |
| **5** | **Mover los motores:** `pdfvec` → `pdf/vectores`, `ocr_raster` → `ocr/`, `textdec` → `shx/decoder` (con recursos inyectados y `memoria_nueva`; la escritura de la memoria pasa a `trabajo/`), `ruteo` → `ruteo/red`. Los puentes conservan todos los nombres de 2.4, incluido el reemplazo de `route_line` | B + `probar_arreglos_pae` (que el reemplazo se siga llamando) | medio (OCR determinista) |
| **6** | **Bytes en lugar de rutas:** `pdf/abrir` (desprotección en memoria, PDFium siempre dentro de un `with`, nunca tomar un lock de caché con `PDFIUM_LOCK` tomado), cachés de `eplan` con lock | B; PAE (PDF protegido); nada en `%TEMP%\planocables_eplan`; memoria: el PAE pesa 11,5 MB y la copia unos 14 MB | medio (bloqueos y claves de caché) |
| **7** | **`eplan.py` → paquete `eplan/`**, con la fachada que reexporta. `aplicar_puntos` recibe los manuales ya leídos. **No cambia `VERSION_LECTOR`** | B (PAE) + `probar_arreglos_pae` + `probar_ronda3` | medio |
| **8** | **`core`, `wires` y `topo` → `funcional/` y `topografico/`**, con puentes; banderas estructuradas en el listado | B + listado + layout **idénticos** | medio |
| **9** | **Instructivo, en tres partes.** 9a: `funcional/puntas` y `conductores` (con ida y vuelta por JSON y copia en el memo). 9b: `instructivo/armado.armar` con `build` como puente; `salidas`, `quitados`, `panel` y `usos` a sus módulos. 9c: las closures de `build` a `puntos`, `orden`, `correcciones`, `estaciones` y `pasos`, sin cambiar valores; `taller.json` con los valores de hoy | B en cada parte; prueba nueva: `armar` desde `conductores@1` por JSON da lo mismo que desde `res` | **medio-alto** (orden de iteración, red de ruteo compartida) |
| **10** | **`bornes/` puro:** `catalogo`, `pagina_pdf`, `Motor` que acepta páginas leídas, `componer` que devuelve un dict (el puente sigue cambiando `lay`), `firma` con una lista explícita, `layout_mapeado@1`. `bornes` deja de importar `instructivo` | B (66817 104/104 y 75/75) + `probar_ronda3` | medio |
| **11** | **Pipeline, trabajo y servicio, en seis partes.** 11a: un harness nuevo que dé **idéntico** al `volcar` viejo con el código sin tocar. 11b: `armar_instructivo` compartido por la web y `volcar` (decidir y documentar si el layout pasa por JSON; si una base cambia por eso, se analiza antes de aceptarla). 11c: `trabajo/almacen` con `rev` y fusión al final bajo lock. 11d: `servicio` (`run_job` y `cli.run` encima, `gen_instructivo` sincrónica, `use_ocr` igual que hoy). 11e: `exportar/` a bytes. 11f: la firma nueva de `estacion8` y los códigos estables | B + E8 + humo + marcas reales (fixture de la etapa 0) | **alto-medio** |
| **12** | **Adaptador para la otra app:** `python -m planocables`, esquemas, `probar_contratos.py`, `exportar/instructivo_json`. Y, si hace falta, el servicio HTTP aparte (7.3, opción B) | los contratos se validan con un validador propio, no con `jsonschema` (no está instalado); el CSV por CLI tiene que ser igual al de la web | bajo |
| **13** | Terminal, auditoría y grupos de salida: en Python o en un módulo JS compartido, **según cómo sea la otra app** | golden de la etapa 0 | medio |
| **14** | **Limpieza:** `requirements` (agregar `reportlab`, sacar `requests`, **dejar `shapely`**, separar los extras); código muerto (`instructivo.linea_txt`, `eplan.tiene_lista`, `eplan.natk`, `CAB_DOC`, `topo.rails_of`, `TAG_TXT`); CLAUDE.md, `bornes/LEEME.md` y `LEEME.txt` actualizados con la tabla «qué tocar». Los puentes se retiran solo cuando nada los use | B + todas las bases | bajo |

**Orden:** primero la WPC, que es lo que pediste y no depende del resto. Después lo que más ordena (ciclos y motores), y lo más delicado (instructivo y pipeline) al final, con la red de seguridad completa.

---

## 10. Cambios que podrían cambiar resultados (cada uno necesita tu OK)

Ninguna etapa los hace. Se proponen después, de a uno, mostrando qué líneas cambian en cada producto:

1. Unificar las **tres formas de calcular el lado** (instructivo, WPC y E8).
2. Unificar los **comparadores de marcas** al regenerar (hechos, quitados y fotos).
3. Unificar `sin_lado`, el orden natural (`natk`, `natkey` y `natKey`), `stacked_ref` / `ref_apilada` y los dos `secNum`.
4. Un `FABRICANTES_RE` único: puede cambiar en qué planos se detecta la lista de materiales.
5. Una **precedencia única de puntos** (hoy hay 4 implementaciones) y que el punto aproximado de E8 sea igual al del instructivo.
6. Que E8 escale con kr como E6.
7. La regla del terminal en E8 (la del instructivo o la de E8).
8. `ladoTexto` para N.5/N.6.
9. Sumar el celeste del neutro a la regla de salida (pendiente de EPLAN).
10. Que la regeneración respete la opción de OCR del trabajo (`web.py:383`).
11. Pasar la caché `_ES` de `eplan` a sha1.

---

## 11. Riesgos

1. **AutoCAD en un solo proceso:** por los `id()`, el lector y el armado no se pueden separar. Hacia afuera salen el listado, los conductores y el layout mapeado.
2. **Las bases dependen de `ocr_cache.json`** (está en git y cambia). Por eso el modo solo lectura entra en la etapa 1.
3. **Pruebas atadas a detalles internos** (2.4). Los puentes los conservan; si algo se tiene que tocar, se avisa en la misma etapa.
4. **`Net` tiene estado:** hay que conservar el orden de ruteo y una sola red. `rutear_salidas` arma su propia red solo con los cables a LI, así que sus largos no son los del instructivo regenerado. La WPC usa los del instructivo.
5. **`build` cambia `c['pares']`:** memo con copia profunda.
6. **Redondeos JS ↔ Python** (5.3).
7. **Bloqueos:** `PDFIUM_LOCK` no es reentrante. Por eso se usa el `with` y nunca un lock de caché dentro de él.
8. **El taller y el desarrollo comparten la carpeta:** se evita con el worktree y otro puerto (sección 8).
9. **Memoria OCR entre procesos:** se fusiona antes de escribir; las pruebas y la otra app la usan en solo lectura.
10. **`pendiente/arreglos_mapeo_parciales/`** tiene copias divergentes de `motor.py` que no van a aplicar después del refactor.
11. **Rendimiento:** la copia profunda de los conductores, el sha1 de 11,5 MB y la doble lectura de bytes. `volcar` mide tiempos: no tienen que empeorar.

---

## 12. Preguntas para vos

**Sobre la otra app** (cuando tengas acceso):
1. ¿Es Python o Node? ¿Qué versión? ¿Corre en la misma PC que tiene los PDF?
2. ¿Qué consume hoy del listado, el instructivo y la auditoría: el «⭳ JSON» del instructivo, `resultado.json`, el Excel? Si nos pasás una muestra, ese formato es el primer contrato.
3. ¿Esa app **genera** el listado y el instructivo a partir de los PDF, o solo **muestra** lo que arma este programa?
4. ¿Cómo preferís conectarla: importando (Python), por línea de comandos o por un servicio aparte?

**Sobre la WPC:**

5. ¿Alcanza con el CSV, o el programa tiene que generar también el `.wpc` (zip con XML, plantilla `Template_5.0.11.xlsm`)?
6. ¿Qué parámetros tienen que poder cambiarse **por producto** y quién los cambia: el taller desde la pantalla o alguien en el archivo?
7. En AutoCAD no hay «documento» como en EPLAN. ¿Uso el número de plano (por ejemplo `75287`) como clave del producto?
8. `agregado_puerta` (350) nunca se suma a los que salen a la puerta sin E8, porque esa rama del JS nunca se alcanza. ¿Es un error o está bien así? Por ahora se copia igual.

**Sobre cómo trabajar:**

9. ¿Commiteo el estado actual (proyector, aparamenta, WPC, bases y pruebas modificadas) antes de empezar, sin los borrados de tus datos? ¿Sigo en `sistema_modular` y subo a `pruebas` como siempre?
10. ¿Te parece bien trabajar en una copia aparte (worktree) y probar en otro puerto, para no cortarle la web al taller?
11. La memoria del OCR (`ocr_cache.json`), ¿sigue en git dentro de `programa/`?
12. Los archivos de datos (`glyphdict.json`, `catalogo.json`, `wpc.json`, `terminales.json`), ¿quedan donde están (recomendado) o se mueven al paquete?
13. ¿Qué hacemos con `pendiente/arreglos_mapeo_parciales/`?

**Sobre reglas del taller** (no frenan el plan; quedan en la sección 10):

14. ¿El terminal en E8 sigue la regla del instructivo (la mayor sección de los tramos del borne) o la de E8 (la sección propia)?
15. Las ediciones en el navegador (quitar, mover de estación, mover una punta), ¿quedan instantáneas como hoy? Es lo recomendado.
16. Con un topográfico nuevo se borran las salidas, pero se conservan `bornes_usuario`, los overrides y la calibración. ¿Es el criterio que querés?
