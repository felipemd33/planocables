# Mapeo automático de bornes (programa/bornes)

## Qué hace

Cuando se genera el instructivo de cableado, el programa ubica **cada borne en el dibujo del topográfico**, para que cada cable salga del tornillo o de la boca correcta. Antes, en un plano nuevo, salía de la etiqueta amarilla del aparato.

1. Del **funcional** sale qué bornes usa cada cable: `instructivo.usos_bandeja`. También sale la **lista de materiales**, si el funcional la trae (`instructivo.materiales_funcional`, la hoja con PHOENIX, SCHNEIDER, MEAN WELL...).
2. El **motor** (`motor.py`) mira el dibujo a la derecha de cada etiqueta amarilla. Con el modelo del aparato (`catalogo.json`) reconoce sus bocas y las nombra.
3. El modelo sale de la lista de materiales. Si no figura, sale de la forma del dibujo.
   - Si la lista nombra un modelo (esté o no en el catálogo), la forma del dibujo **solo puede elegir un modelo de la
     misma familia** (tipo de aparato: bornera, relé, barrera, termomagnética, diferencial, base de fusible, fuente,
     módulo de E/S, toma...). La familia es la del modelo del catálogo que nombra la lista o, si no está, la que dice
     la descripción del renglón (patrones de `familias` en `catalogo.json`; un renglón sin familia reconocible de un tag
     de bornera, con X, cuenta como bornera).
   - Si el catálogo no tiene ningún modelo de esa familia (ej. el módulo MOXA ioLogik del TPT), el aparato queda **sin
     puntos** (en la etiqueta, confianza baja) con el aviso de modelo faltante. Antes se ubicaba como otro aparato
     (barrera) y sus bornes caían sobre la bornera de la fuente vecina.
   - Un modelo que no encontró su dibujo en la zona (ninguna pieza) no explica nada: sus bornes «desbordados» no le
     suman puntaje (antes una bornera con diodo sin piezas le ganaba a la bornera de la lista).
4. El resultado queda guardado en `bornes_auto.json`, en la carpeta del trabajo. Si no cambia nada (contenido del topográfico, funcional, lista de materiales, catálogo, código del motor —`motor.py`, `primitivas.py` y su versión—, componentes de la bandeja), la próxima vez no se vuelve a calcular. Cambiar solo la fecha del topográfico no lo recalcula.
5. Si **todos** los bornes del trabajo ya tienen punto manual (`bornes.json`, `correcciones.json` o ajustados en el visor), el motor no se corre: no cambiaría nada. La línea del mapeo dice «todos los bornes tienen punto verificado a mano en este trabajo».

Entran los mismos bornes que cablea el instructivo: los de cada conductor del funcional, los de los conductores con una sola punta en la bandeja y la otra afuera, y los de los conductores agregados a mano en `correcciones.json` (`agregar`).

**Orden de prioridad** de un punto, de menor a mayor (el que viene después manda):

1. mapeo automático;
2. `bornes.json` del trabajo (puntos hechos a mano o verificados);
3. `bornes` de `correcciones.json`;
4. puntos ajustados en el visor con 📍: mandan siempre. Si el punto se ajustó con el texto del funcional, el mapeo tampoco le cambia el texto (ver «Textos corregidos»).

Si el mapeo falla, el instructivo se arma igual, como antes (sin puntos exactos). Si falla un solo aparato (o no tiene la posición de su etiqueta), ese aparato queda sin punto y los demás siguen. En los dos casos queda un aviso. Un `bornes.json` o `correcciones.json` ilegible (JSON inválido) se ignora con el aviso «bornes.json ilegible, se ignora».

## Qué significa la confianza

| confianza | qué quiere decir | en la pantalla |
|---|---|---|
| **alta** | La boca o el tornillo se ven en el dibujo y el nombre sale directo de la regla del modelo. | Nada: el cable sale de ahí. |
| **media** | El borne no está dibujado y se ubica con una medida del catálogo. Ejemplos: enchufes de las barreras con bloque simbólico, toma sin tornillos dibujados. También entra acá lo que se ubicó con una regla de corrección: bornera vecina, común puenteado, texto sin módulo o dos cables en la misma boca. Y los bornes de un aparato cuyo dibujo coincide igual con dos modelos que los ubican distinto (sin lista de materiales, un diferencial y una termomagnética de 2 polos se dibujan igual pero con F y N cruzados). | Marca **«a confirmar»** en la tarjeta y en el visor. Pasando el mouse se ve por qué. Si no es ese borne, se corrige con 📍. |
| **baja** | No se pudo resolver (por ejemplo, el texto no trae número). | No se usa: el cable queda con «punto aprox.» y sale un aviso. |

En la pestaña del instructivo, la línea **«Mapeo automático de bornes: …»** se despliega y muestra los avisos. Ahí aparecen los modelos elegidos por la geometría, las bocas compartidas y los textos corregidos. También:

- **Modelos que no están en el catálogo**: la lista de materiales nombra para un tag un modelo que `catalogo.json` no tiene (por ejemplo `MOXA ioLogik E1240 (32AI1)`); sus bornes se ubicaron por la geometría como otro modelo **de la misma familia** o quedaron en la etiqueta. Es la lista de modelos para agregar al catálogo (queda en `ins['mapeo']['modelos_faltantes']`, con la familia de cada uno).
- **Textos con el lado físico distinto del dibujo del funcional**: puntas cuyo ARRIBA/ABAJO cambió por el punto real del borne (barreras 1/2 ABAJO → ARRIBA, 61XDIO) o por el lado forzado en «Componentes y orden». En el visor, pasando el mouse sobre el texto subrayado se ve lo que dice el funcional.

**Red de seguridad.** Un borne no puede caer sobre otro aparato. Antes de dar el resultado, el motor descarta (pasa a
confianza baja, en la etiqueta, con aviso «punto(s) descartado(s)…») los puntos que caen **dentro del cuerpo de otro
aparato** (el contorno cerrado más chico que contiene la etiqueta de ese aparato y alguno de sus bornes, o el cuerpo que
usó su modelo) y los que quedan **encima de un borne de otro tag** (a menos de `distancia_otro_tag_mm` del catálogo,
1,5 mm): de dos puntos encimados se descarta el de menor confianza, o los dos si tienen la misma. No cuentan los puntos
que el motor pasó a propósito al bloque vecino (desborde, boca compartida).

**Dos pisos del mismo borne en el mismo punto.** Si dos pisos (`N ARRIBA` / `N ABAJO`) o pines distintos del mismo
borne quedaron en el mismo punto con confianza media, ese punto no distingue el lado: el texto queda como en el
funcional (no se pasa al lado físico). Con confianza alta, o con el lado forzado en «Componentes y orden», sigue la
regla de siempre.

**Textos corregidos.** Si el punto quedó en otro bloque o en otro módulo, el texto de la línea se cambia por el que corresponde a donde quedó. Por ejemplo, `62XDIO 3` pasa a `62XDO 3` y `43KR2 A2` pasa a `43KR1 A2`, porque el A2 es común con puente FBS. El cambio también se avisa. Un texto corregido a mano en `bornes.json` (`renombrar`) manda sobre el automático, y un texto cuyo punto se ajustó en el visor con 📍 no se corrige. Un relé único sin número de módulo en el texto (`43KR 11`) queda como lo dice el funcional: solo se corrige el módulo si el bloque tiene más de un módulo o si es un común puenteado.

**ARRIBA/ABAJO.** Cuando el borne tiene punto exacto, el texto lleva el lado físico, que es la regla de siempre del programa. Por ejemplo, el `1 ABAJO` de las barreras del 66817 queda `1 ARRIBA`, porque el enchufe de alimentación está arriba.

## Cómo se agrega un modelo nuevo

No se toca el código: se agrega una entrada en `catalogo.json`. Todas las medidas van en **milímetros del tablero real**.

1. **Medir el bloque en el plano.** Con `medir.py` se ven las formas que hay a la derecha de la etiqueta, con sus medidas en mm:
   ```
   python medir.py <topografico.pdf> <usos_por_componente.json> <TAG> --png zona.png
   ```
   El json de usos se puede sacar con `instructivo.usos_bandeja`, o copiar de una prueba anterior.
2. **Copiar la entrada de un modelo parecido.** Para una bornera, `PT2.5-DIO` o `PTT2.5`; para un aparato modular, `DF101`; para una fuente, `MEANWELL-DDR`. Cambiar estos campos:
   - `id`;
   - `familia`: el tipo de aparato (una de las `familias` de `general`: `bornera`, `rele`, `barrera`, `termomagnetica`,
     `diferencial`, `portafusible`, `fuente`, `modulo_es`, `toma`...). Si es un tipo nuevo, agregar también su
     patrón en `familias` (el orden importa: gana el primero que aparece en el renglón);
   - `alias`: los textos de la lista de materiales, como el código comercial o el código de pedido;
   - `paso_mm` y `alto_mm`: salen de la hoja de datos;
   - `boca`: primitiva y rango de tamaño, el que dio `medir.py` ±10 %;
   - `disposicion`;
   - `nombres`;
   - `fuente`: de dónde salió la información.
   - `sap`: los códigos de material SAP del taller que corresponden a ese modelo (ver «Aparamenta» abajo). Un mismo
     código puede estar en dos modelos si el taller lo compra de dos marcas (la termomagnética 2x10A es Easy9 o ABB).
   - En las `filas` de un aparato con enchufes (relé de seguridad, módulos), `paso_mm` en el grupo hace que el motor
     busque la serie de tornillos con ese paso más cercana a la etiqueta: no mezcla el enchufe del aparato vecino y, si
     un tornillo está dibujado distinto y no se reconoce, lo completa con el paso (confianza media).
3. **Barrera u otro aparato que el bloque no dibuja.** Si el bloque del plano es de otra biblioteca y no dibuja un tornillo por borne, se agrega `cuerpo`:
   - `pines`, cada uno con `dx_mm` desde el centro y `dy_mm` desde el borde de arriba o de abajo (`desde`), en el aparato real;
   - el motor busca las **filas dibujadas** del bloque, como tornillos, ranuras o lengüetas;
   - cada enchufe va a la fila que le toca según el escalonado real: en cada lado, el `dy_mm` más chico es la fila de afuera.
4. **Probar** con el plano y mirar la imagen de control. Verde es alta, naranja media y rojo baja:
   ```
   python motor.py <topografico.pdf> <usos.json> salida.json --materiales no --control control.png
   ```
   Si el modelo nuevo no aparece en un aparato, el aviso lo dice; casi siempre hay que revisar el rango de tamaño de la boca.

Si un modelo necesita una forma de boca que no existe todavía, hay que agregar una primitiva en `primitivas.py`. Es el único caso en que se toca código. Al cambiar el motor, hay que subir `VERSION` en `motor.py` para que los trabajos recalculen el cache.

Los modelos nuevos van **al final** de `modelos`: sin lista de materiales, si dos modelos explican igual un dibujo, gana el
que está primero, y así un modelo nuevo no le cambia el resultado a un plano que ya andaba.

## Aparamenta (Excel «BOMs por estación» de SAP)

`aparamenta.json` tiene cada material del Excel del taller (código SAP, texto, estación, productos donde aparece) con lo
que es: clase (bornera, aparato, accesorio de bornera, fusible, componente, puerta, campo, cable, electrónica,
hidráulica, mecánica, etiqueta), fabricante, modelo comercial, código del fabricante y el modelo del catálogo que ubica
sus bornes (`catalogo`). Si un aparato con bornes no necesita modelo (va en la lateral, borne de tierra sin número),
`motivo_sin_modelo` dice por qué.

Cuando llega el Excel actualizado:

```
python aparamenta.py "C:\...\BOMs Por Estación .xlsx"
```

Actualiza texto, estación y productos, conserva lo identificado y deja los códigos nuevos con `revisar`. Después da el
informe: aparatos de la bandeja sin modelo en el catálogo, códigos SAP que faltan en el `sap` de su modelo y códigos para
revisar. Sin argumento solo da el informe. Para un código nuevo: identificarlo (hoja de datos), completar su renglón y,
si tiene bornes en la bandeja, cargar su modelo en `catalogo.json` (con el código en `sap`).

## Bandejas laterales (estación E8)

Desde el 2026-10-08 (etapa E8-5) el mismo motor ubica también los bornes de las **bandejas laterales**, para el visor de
la estación 8 (`estacion8.mapear_bornes` → `laterales.py`):

- Se corre una vez por lateral, con la **placa** de la lateral como región y sus aparatos (los usos salen de
  `instructivo.usos_bandeja` con `tags` y `region`; las puntas que llegan a un WAGO no entran: no son un borne).
- **Rieles:** los de la capa del riel; si en la placa no hay ninguno, los rectángulos con el perfil del riel de la bandeja
  en cualquier capa (en el TPT, el riel de arriba de la lateral derecha está en la capa `0`); y los ejes que el lector
  del topográfico da para la vista (`rieles_e8`) sin ningún tramo: el riel **tapado** por los aparatos, a lo ancho de
  las canaletas horizontales que lo encierran.
- **No cambia textos:** el resultado va a `lay['bornes_e8']` con el texto del funcional. Un borne que el motor ubica en
  otro bloque o en otro módulo queda con el punto aproximado y un aviso (en la bandeja el texto se corregiría, pero eso
  cambiaría E6 y sus pendientes).
- El cálculo se guarda en `<trabajo>/bornes_e8_auto.json`, una entrada por lateral, aparte de `bornes_auto.json`.
- Manda, en este orden: el punto ajustado a mano en el visor de E8 con 📍 (`bornes_usuario`, el mismo de E6), los
  manuales del trabajo (`bornes.json`, `correcciones.json`), el mapeo de la lateral y, por último, el punto aproximado.
  El aproximado de un borne de una bornera que tiene otros bornes con el punto exacto del mismo lado del riel sale de
  ellos, con el paso entre bornes (no de la etiqueta), para que el orden de izquierda a derecha cuadre (75287: el 11XP 3,
  la pieza PE que el motor no ubicó, queda a la derecha del 11XP 2).
- No cubre (quedan aproximadas, con aviso): un riel **vertical** (la lateral derecha del 66817) y los aparatos que no
  están en el catálogo (batería 12PB1, seccionador VBF1).

## Archivos

| archivo | qué es |
|---|---|
| `__init__.py` | Lo que usa el programa: `aplicar_al_layout` (todo junto), `mapear_trabajo` (motor con cache), `componer_bornes` (automático + manual). |
| `motor.py` | El motor (`Motor(pdf, usos, catalogo, materiales).mapear()`). Se puede correr suelto para pruebas. |
| `laterales.py` | El motor por bandeja lateral para la estación E8 (`MotorLateral`, `mapear_lateral`, con su cache). |
| `primitivas.py` | Formas genéricas: círculo, contorno, tornillo cortado, caja. |
| `catalogo.json` | Los modelos de bornes y aparatos (25 hoy), con sus medidas en mm, las reglas de nombres y sus códigos SAP. |
| `aparamenta.json`, `aparamenta.py` | El Excel «BOMs por estación» de SAP con lo que es cada material y su modelo del catálogo (ver «Aparamenta»). |
| `medir.py` | Ayuda para medir un bloque y agregar un modelo. |

Probado con el 75286/75287 (140 de 140 puntos con la lista de materiales del funcional; el instructivo sale igual al verificado) y con el 66817 (104 de 104).

Modelos agregados el 2026-10-06 con el Excel de aparamenta y las hojas de datos: PT4, PT6, PSR-SCP (relé de seguridad), ABB-SH202, EO-I-UT (toma Phoenix), DF141, MOXA-R1240 y EXEMYS-EGW1. Probados con el mSafe1 PP (76425/76426: 46KR, 33EXM) y el TPT (72715/72887: 11Q1 verificado con fotos, 33MX01). Los que tienen `solo_por_lista: true` se usan solo si la lista de materiales los nombra; nunca se eligen por el dibujo para otro aparato de su familia.

Corregido el 2026-10-07 con las fotos E06 del mSafe1 PP 76572 (`1.6.jpeg`, `1.2.jpeg`):
- **EXEMYS-EGW1:** tres enchufes, todos abajo; arriba no tiene bornes. El de adelante es el de más abajo (fila 0, el que dibuja el bloque): 1 +VIN, 2 PGND, 3 RGND, 4 IGND (1316 y 1317 en la foto). Detrás, hacia el riel: 5-8 (TXa, RXa, TRb+, TRb−) y el puerto HART (HTa, HGND). Al revés que en los Phoenix, acá el enchufe de afuera es el de adelante. El orden HTa / HGND y los corrimientos de 9 y 18 mm son supuestos: falta una foto del rótulo del costado.
- **PSR-SCP:** 13 y 14 en el enchufe de adentro de abajo (2114 / 2115 del 46KR1), como estaba.
