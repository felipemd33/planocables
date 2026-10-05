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
| `programa/core.py`, `wires.py`, `textdec.py`, `pdfvec.py` | Lector del funcional: textos SHX, cables, números, uniones en T y flechas a otras hojas. |
| `programa/instructivo.py` | Puntas (`describe_end`), conductores (`conductors`), textos (`fmt_terminal`) e instructivo (`build`): orden, pasos, pendientes LI↔LI y estaciones. Además `usos_bandeja` y `materiales_funcional`. |
| `programa/topo.py`, `ruteo.py` | Topográfico (página de la bandeja, rieles, canaletas, escala, componentes) y ruteo por canaletas (Dijkstra). |
| `programa/bornes/` | Mapeo automático del **punto exacto de cada borne**: `motor.py` + `catalogo.json` (modelos en mm) + `primitivas.py`. Ver `programa/bornes/LEEME.md`. |
| `programa/eplan.py` | Planos de **EPLAN** (PDF con texto real): `es_eplan`, `process` (lista de conexiones → conductores y listado, misma interfaz que `core.process`), `layout` (hoja de bandejas: rieles, canaletas, placas, etiquetas → mismo formato que `topo.layout`) y `aplicar_puntos` (mapeo verificado). `core.process` y `topo.layout` derivan solos a este módulo. |
| `programa/mapeos_verificados/` | **Dato** por producto EPLAN: `<documento>_rev<revisión>.json` con el punto exacto y el texto del taller de cada punta (`'<designación EPLAN>#<cable>'`), la zona hidráulica (E8) y las canaletas de intrínsecos. Se elige por el documento y la revisión del rótulo. Se arma con `2 - Resultados/76884 mSafe2+ PAE/mapeo/exportar_al_programa.py`. |
| `programa/web/*.js` | Interfaz: `app.js` (listado y visor del funcional), `instructivo.js` (pestaña instructivo y visor de cablear), `auditoria.js`, `salidas.js` (editor de salidas a LI / LD). |
| `programa/gabinete.py`, `web/e8.js`, `web/e8.css` | **E8 (gabinete en 3D)**: `leer_gabinete` (contorno, laterales desplegados, puerta, aparatos y canaletas de cada vista del topográfico; cache `e8_gabinete.json` del trabajo) y `armar_e8` (cables de E8 con puntas y recorrido 3D). Visor con three.js (cdnjs, import map de `index.html`). Marcas en `instructivo.json['e8']`. |
| `1 - Planos/` | Planos originales. `Catalogo (referencia)/`: 8 productos con su orden de montaje SAP. `Producto nuevo/`: mSafe2+ PAE (EPLAN). |
| `2 - Resultados/` | Salidas. `76884 mSafe2+ PAE/`: mapeo verificado del producto EPLAN (ver abajo). |
| `3 - Historial web/<id>/` | Trabajos de la web (plano, `layout.json`, `instructivo.json` con las marcas del usuario, `bornes.json` manual, `correcciones.json`, `bornes_auto.json`). **No pisar las marcas del usuario.** |
| `prototipos/` | Los 5 prototipos de mapeo de bornes. `_referencia/` es la referencia del 75286; `_referencia_66817/` la del 66817. |
| `pruebas/` | Regresión: `volcar_trabajo.py`, `volcar_cables.py`, `evaluar_bornes.py` y `bases/`. |
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
    - la **zona hidráulica** (MEGA, bomba, válvula, PT001, nivel) y los empalmes del sensor de nivel.
- **Toma 11SK1 del 75286:** todos sus cables se cablean por abajo.
- **No escribir coordenadas ni tags de un plano en el código.** Todo tiene que ser general; los modelos se cargan en
  `programa/bornes/catalogo.json`, en mm.
- **Preguntar al usuario antes de cambiar una convención del taller.**

## Pruebas de regresión (correrlas después de cada cambio en el lector o el instructivo)

```
python pruebas/volcar_trabajo.py "3 - Historial web/ac0f0949510a" salida_75287.json --sin-cache     # 75287
python pruebas/volcar_trabajo.py pruebas/trabajos/66817 salida_66817.json --sin-cache --relayout     # 66817
python pruebas/volcar_trabajo.py pruebas/trabajos/76884 salida_76884.json --sin-cache --relayout     # PAE (EPLAN)
```

- **75287** (mSafe2AC, tablero 75286): verificado por el taller. Líneas, pendientes, sueltos, otra estación y extremos
  tienen que dar **IGUAL** a `pruebas/bases/base_75287.json`.
- **66817** (mSafe NC): tiene que dar como `pruebas/bases/base_66817.json`: 75/75 puntas exactas y 104/104 bornes contra
  `prototipos/_referencia_66817/bornes_referencia.json` (`python pruebas/evaluar_bornes.py <puntos.json> --ref ...`).
- **PAE** (ZPL-76884, EPLAN): `pruebas/trabajos/76884` usa el PDF original de `1 - Planos/Producto nuevo/` (no lo copia).
  Tiene que dar como `pruebas/bases/base_76884.json`: 143 líneas E6, 31 pendientes, 16 en otra estación (E8), 0 sueltos,
  igual al Excel del mapeo verificado.
- **TPT** (72715; trabajo de prueba `pruebas/trabajos/tpt`, el del usuario `e548b195eb2a` ya no está en el historial): `pruebas/bases/base_tpt.json` es el estado ANTES de corregir el
  lector (con errores). Con `--relayout`, el estado actual es `pruebas/bases/base_tpt_ronda3.json` (2026-10-02 noche).
- `--sin-cache` no escribe nada en el trabajo. Como la web, `volcar_trabajo.py` vuelve a leer el topográfico si
  `layout.json` es de otra versión del lector (`topo.VERSION_LECTOR` / `eplan.VERSION_LECTOR`: subirlas al cambiar la
  lectura del topográfico; al regenerar, la web relee los trabajos viejos y conserva lo del usuario).
- Pruebas de arreglos: `python pruebas/probar_arreglos_pae.py`, `python pruebas/probar_ronda2_topo.py` y
  `python pruebas/probar_ronda3.py` (familias del catálogo, red de seguridad del mapeo, topográfico sin capa de riel,
  versión del lector) tienen que dar TODO OK.

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
    bandejas de este mismo PDF» si hace falta). Da 143 líneas E6, 31 pendientes LI↔LI, 16 en E8, 0 sueltos: igual que el
    Excel del mapeo, con cada punta en el punto verificado y ruta por las canaletas.
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
- **Catálogo de aparatos:**
  - el usuario va a pasar un **Excel de aparamenta** de todos los productos, que se retroalimenta solo: usarlo como referencia;
  - **no** armar el catálogo desde los planos;
  - `catalogo/productos/` tiene lecturas parciales de 7 órdenes SAP, solo para comparar.
- **E8 en 3D** (hecho el 2026-10-03, piloto 75286; para revisar con el usuario):
  - botones **E6 · Bandeja** / **E8 · Gabinete** en la página del trabajo; E8 abre el visor 3D (`#/trabajo/<id>/e8[/<n>]`);
  - el otro extremo de cada «→ LI» sale de `destino_e8` (nuevo en `instructivo.build`): un instructivo viejo pide ↻ Regenerar;
  - lo que el topográfico no etiqueta (21PCB01, 41DS) se deduce (recuadro sin etiqueta de la puerta, «a confirmar») o se
    ubica a mano con 📍 (`ins['e8']['ubicaciones']`);
  - supuestos: caras de montaje (fondo 20 mm, laterales 25 mm), puerta 30 mm, bisagras del lado contrario a la cerradura;
  - faltan: conductores sin número del funcional (12PS2 → 12XPS, tierras de puerta) y el orden fino del relevamiento
    (`2 - Resultados/E8 75286/cables_e8.json`).
  - Arreglos del 2026-10-03 (verificador): 66 de los 68 numerados del relevamiento con las dos puntas iguales (los 2 que
    faltan son el texto del empalme de mallas de 2137). Lector: bornera en FILA (tag a la izquierda del borne 1: 12XPS 4-10
    en la hoja 12), borne atravesado por el recorrido = union (12XPS 7/8 en la hoja 81), pines redondos de la placa con su
    numero (hoja 21) y solenoides `SP-1`/`SP-2` (FIELD_RE). `base_75287.json` regenerada solo en `extremos` (42 cables,
    lista en el reporte). E8: zona hidráulica ADENTRO (abajo; lo sin etiqueta junto a lo ubicado del mismo equipo), clave
    estable de las marcas (`num|origen E6` o `num|par ordenado`; las viejas se migran al leer), descarte solo con UN
    recuadro libre, `filas_pin` (build) para el orden y el dibujo de 21PCB01, `destino_campo` (EPLAN) fuera de E8.
- **Para confirmar con el usuario:**
  - escribir el pin en textos repetidos (`13PS2 -Vo (1)`);
  - barreras `1 ABAJO` (el texto viene del funcional, el enchufe está arriba);
  - 61XDIO/62XDIO: ¿lado físico o del funcional?;
  - código `LD` para el lateral derecho;
  - en el RS-485, los blanco/azul de 0,32 mm² no salen por la salida de abajo.

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
  - **Modelos que faltan en el catálogo de bornes** (para el Excel de aparamenta):
    - TPT: ABB SH 202 C10, Phoenix PT 4, ABB E 91/32, MOXA ioLogik R1240-T.
    - Varios productos: EPEVER Tracer, Schneider VBF1, ODOT, EXEMYS, PSR-SCP, ABB DS201, Red Lion E3, P+F KCD2, OMRON
      HL-5200, ZBE-101, etc.
    - Detalle: `scratchpad` del 2026-10-02 (`reg3/faltantes.json`), a rehacer con el Excel.
- (Historia) La corrección del TPT se había diagnosticado y pausado antes; el diagnóstico sigue en `pendiente/tpt_diagnostico/`.
  - En `pendiente/tpt_diagnostico/` están:
    - `LEEME.md`: cada error con la verdad del funcional, la causa en el código y el arreglo propuesto;
    - `diagnosticos.json`: 3 diagnósticos con 6, 22 y 7 casos;
    - `verdad_tpt.json`: la verdad de todos los cables del TPT según el funcional.
  - Próximo paso: corregir el lector con arreglos generales, probar en `pruebas/trabajos/tpt` y verificar
    que el 75287 quede igual y el 66817 siga 104/104.
  - Después, el usuario cierra y abre el programa y aprieta ↻ Regenerar en el TPT.
