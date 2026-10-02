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
| `programa/web/*.js` | Interfaz: `app.js` (listado y visor del funcional), `instructivo.js` (pestaña instructivo y visor de cablear), `auditoria.js`. |
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
```

- **75287** (mSafe2AC, tablero 75286): verificado por el taller. Líneas, pendientes, sueltos, otra estación y extremos
  tienen que dar **IGUAL** a `pruebas/bases/base_75287.json`.
- **66817** (mSafe NC): tiene que dar como `pruebas/bases/base_66817.json`: 75/75 puntas exactas y 104/104 bornes contra
  `prototipos/_referencia_66817/bornes_referencia.json` (`python pruebas/evaluar_bornes.py <puntos.json> --ref ...`).
- **TPT** (72715, `3 - Historial web/e548b195eb2a`): `pruebas/bases/base_tpt.json` es el estado ANTES de corregir el
  lector (con errores).
- `--sin-cache` no escribe nada en el trabajo.

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

## Fuentes de verdad fuera de este repositorio (solo en la PC del taller, disco G:)

- Fotos reales de tableros cableados, con los números en las mangas:
  `G:\Unidades compartidas\Batfer - Taller\20-14-BTF-BATFER-taller\4-Instructivos de montaje de VECTOR\Fotos de referencia de VECTOR\Fotos soporte E06|E08\<producto>`.
- Órdenes de trabajo con planos: `...\3-Info. Tecnica\ORDENES DE TRABAJO\` y `OBSOLETO (NO USAR)\`.
- Instructivos WPC (`.wpc` = zip con XML): número, largo, sección y color, sin origen/destino.

## Pendientes

- **Corrección del lector del funcional con el TPT** (2026-10-02): ver "Estado".
- **Cargar el producto EPLAN en el programa:**
  - lector de la lista de conexiones de EPLAN → conductores → `build`;
  - layout desde la hoja de bandejas;
  - puntos desde el mapeo verificado.
  Así se puede ver en el visor de cablear.
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
- **E8 en 3D** (pausado por el usuario):
  - al cargar el plano, botones E6 / E8;
  - vista 3D tipo EPLAN del gabinete y la bandeja con three.js (placas con el dibujo del topográfico, puerta que abre, cables
    E8 de borne a borne);
  - piloto: 75286.
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
- **Corrección del TPT: DIAGNOSTICADA, FALTA CORREGIR.** El usuario la dejó para después.
  - En `pendiente/tpt_diagnostico/` están:
    - `LEEME.md`: cada error con la verdad del funcional, la causa en el código y el arreglo propuesto;
    - `diagnosticos.json`: 3 diagnósticos con 6, 22 y 7 casos;
    - `verdad_tpt.json`: la verdad de todos los cables del TPT según el funcional.
  - Próximo paso: corregir el lector con arreglos generales, probar en una COPIA del trabajo `e548b195eb2a` y verificar
    que el 75287 quede igual y el 66817 siga 104/104.
  - Después, el usuario cierra y abre el programa y aprieta ↻ Regenerar en el TPT.
