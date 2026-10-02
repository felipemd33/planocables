# P3 — Mapeo de bornes con una base de medidas en milímetros

## La idea

Los aparatos que usa el taller son casi siempre los mismos. De cada **modelo** se guarda una vez en una base de datos (SQLite, `bornes.db`):

- el **tamaño del cuerpo** en mm (ancho × alto, vista de frente, con el riel horizontal);
- la **posición de cada borne** en mm, medida desde la esquina de **arriba a la izquierda** del cuerpo, y su radio.

Los datos salen de la hoja de datos del fabricante, o, si la hoja no trae la posición de los bornes, de medir una vez el bloque CAD de la biblioteca.

En cada plano nuevo, `mapear.py` busca el **contorno del cuerpo** de cada aparato junto a su etiqueta amarilla. Lo reconoce porque tiene el ancho y el alto del modelo, pasados a puntos con la escala del plano. Después calcula cada borne con una cuenta:

```
x_borne = borde izquierdo del cuerpo + x_mm / escala
y_borne = borde de arriba del cuerpo − y_mm / escala        (escala = 1.4086 mm por punto en este plano)
```

No necesita que el dibujo tenga los tornillos o las bocas: le alcanza con el contorno. Por eso funciona también con símbolos simplificados, como el toma 11SK1. La prueba sin detalle lo confirma: se borran del plano los 7297 trazos de tornillos, bocas y pulsadores y el resultado no cambia.

## Resultado en este tablero (CJ. CONTROLADOR mSafe2, topográfico 75441 REV.6)

`salida/evaluacion.txt` (salida de `evaluar.py`):

| | |
|---|---|
| **BIEN (≤ 1,5 pt ≈ 2 mm)** | **137 / 140 = 97,9 %** |
| Con punto (cobertura) | 140 / 140 = 100 % |
| Error mediano | 0,04 pt (0,06 mm) |
| Tiempo | ~17 s (7 s de ese tiempo es leer el PDF) |

| familia | bien | total | error medio |
|---|---|---|---|
| barreras | 20 | 20 | 0,03 pt |
| borneras riel 2 | 33 | 35 | (2 errores del instructivo) |
| borneras riel 3 | 26 | 26 | 0,09 pt |
| fuentes | 10 | 10 | 0,04 pt |
| protecciones | 18 | 18 | 0,06 pt |
| relés | 30 | 31 | (1 error del instructivo) |

**Las 3 fallas son errores del instructivo, no del método.** La referencia los corrigió mirando el funcional, algo que este programa no hace:
- `43KR2 A2` (cable 1328): según el funcional va en 43KR1 A2. El programa lo pone donde dice el texto, en el módulo 2.
- `62XDIO 3 ARRIBA` (6203) y `62XDIO 3 ABAJO` (6204): según el funcional son de 62XDO 3. El programa los pone en 62XDIO 3, **pero los marca para revisar**, porque esas bocas quedan con dos cables distintos (ver "Controles" más abajo).

**Error según de dónde sale la posición del borne:**

| origen del dato en la base | puntos | bien | error medio |
|---|---|---|---|
| hoja de datos (vista frontal vectorial MEAN WELL) | 18 | 18 | 0,02 pt |
| hoja de datos + bloque (barreras CHENZHU) | 10 | 10 | 0,03 pt |
| bloque CAD medido una vez (Phoenix, Schneider, DF101, relés, MEGA) | 110 | 107 | 0,10 pt (sin las 3 fallas del instructivo) |
| foto (toma 11SK1, bloque simplificado) | 2 | 2 | 0,12 pt |

**Pruebas de robustez** (se corren igual y se evalúan con `evaluar.py`):

| prueba | resultado |
|---|---|
| Escala sacada del riel DIN (35 mm) en vez del valor de los usos (`--escala 1.41304`) | 137/140 = 97,9 % |
| **Sin lista de materiales**: el modelo se elige solo por las medidas del cuerpo | 133/140 = 95,0 % (solo falla 11Q2: la termomagnética y la diferencial miden igual y el orden F-N sale de la lista) |
| **Sin detalle** (`prueba_sin_detalle.py`): se borran los 7297 trazos de tornillos, bocas, pulsadores y textos | 137/140 = 97,9 % |
| Caso extremo (`--agresivo`): se borran también los tramos rectos cortos, o sea pedazos del contorno | 133/140. Las 2 últimas piezas de 43XCS y 46XC no se reconocen y sus 4 usos quedan en la etiqueta con confianza baja, **sin mandarlos por error a otra bornera** |

No hay "dejando un tag afuera", porque la base no aprende de la referencia. Las medidas vienen de las hojas de datos y de los bloques CAD, y `mapear.py` no lee `bornes_referencia.json`.

## Cómo se usa

```
python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json>
```

Ejemplo, desde esta carpeta:

```
python mapear.py ..\_referencia\topografico.pdf ..\_referencia\usos_por_componente.json salida\bornes.json
python ..\_referencia\evaluar.py salida\bornes.json
```

Opciones:
- `--materiales lista.txt`: la lista de materiales. Si no se indica, se busca `lista_materiales.txt` al lado del JSON de usos. Sin lista también funciona, eligiendo el modelo por las medidas.
- `--escala 1.4086`: mm por punto. Si no se indica, se usa la de los usos, o si no la del riel DIN, que mide 35 mm.
- `--pagina 8`: página del PDF. Por defecto, la de los usos.
- `--base otra.db`, `--control imagen.png`.

Qué deja:
- `salida.json`: un punto por uso, con `texto`, `cables`, `x`, `y` (en puntos PDF, origen abajo a la izquierda) y `r` (radio del borne en pt). También lleva `confianza` (alta, media o baja), `componente`, `modelo`, `pieza`, `borne_modelo`, `lado_fisico`, `como` (explicación en castellano) y, si hay algo raro, `revisar`. Además trae `componentes`, con el modelo elegido y los cuerpos ubicados, y `avisos`.
- `control.png`: un panel por riel. En verde, los cuerpos ubicados por medidas. Cada borne va con un círculo del tamaño del borne y su rótulo vertical: texto del instructivo sin el tag, más el cable. Rojo es confianza alta, naranja media y violeta baja. "!" quiere decir que la boca recibe dos cables distintos.
- `control_general.png`: toda la bandeja, sin rótulos.

## Cómo funciona, paso a paso

1. **Base.** Lee `bornes.db`. Si las planillas `datos/*.csv` son más nuevas, la rearma sola.
2. **Plano.** Lee los trazos de la página con `pdfvec` del programa, sin modificarlo. Encuentra los rieles DIN (capa `RIEL DIN`; el ancho dibujado sirve para controlar la escala) y todos los recuadros de etiqueta amarilla. El tamaño y la capa de las etiquetas los aprende de las que trae el JSON de usos.
3. **Modelo de cada componente.** Busca el tag en la lista de materiales y compara con los alias de cada modelo de la base; si hay alias uno dentro de otro, gana el más largo. Con ese modelo busca el cuerpo en el dibujo. **Si la lista dice un modelo que no entra en el dibujo, prueba con todos los de la base y se queda con el que coincide en medidas**, y lo avisa. Así se detectaron solos tres errores de la lista:
   - 11PS1: la lista dice NDR-120 (40 mm), pero el dibujo es de 63 mm, o sea NDR-240;
   - 31XAI: la lista dice PTT 2,5-2MT, pero el dibujo es un borne fusible PTTB 4-HESI (6 × 102 mm);
   - 13PS3: la lista lo llama 13PS2.
4. **Cuerpo.** Un cuerpo es un par de lados verticales separados por el ancho del modelo, con el alto del modelo (± la tolerancia de la base). Hay tres casos que también se aceptan:
   - uno de los lados es más largo porque lo comparte con un vecino más alto (11Q1 al lado de la fuente);
   - los lados son más cortos por esquinas redondeadas; entonces el alto se toma de las líneas de arriba y de abajo (portafusible MEGA);
   - los lados tienen huecos; eso cuenta como error, para no confundir las líneas interiores con el contorno.
5. **Regla del tag.**
   - Aparatos: el cuerpo que contiene la etiqueta, o el primero a su derecha.
   - Borneras y módulos de relé: las piezas del modelo que quedan a la **derecha** de la etiqueta y antes de la etiqueta siguiente del mismo riel. No se cuentan las verdes (PE) ni los topes, que tienen otras medidas. Se numeran de izquierda a derecha.
6. **Borne de cada uso**, según la regla del modelo (columna `regla`):

   | regla | modelos | cómo se lee el texto |
   |---|---|---|
   | `nombre` | fuentes, termomagnéticas, diferenciales, DF101, toma, MEGA, barreras | se busca el nombre del borne y sus alias (`1 (-)`, `L-3`, `-Vo`, `F ARRIBA`, `9`...). Si varios bornes tienen el mismo nombre (dos `-Vo`), se reparten de izquierda a derecha por número de cable |
   | `cuatro_puntos` | PT 6-QUATTRO | `N.p`: pieza N; p1 arriba extremo, p2 arriba interior, p3 abajo interior, p4 abajo extremo |
   | `dos_pisos` | PTT 2,5 / PTT 2,5-2MT (gris y azul) | `N ARRIBA/ABAJO`: pieza ceil(N/2); impar = boca del extremo, par = boca interior |
   | `fusible` | PTTB 4-HESI | `N` = paso directo (boca del extremo), `FN` = nivel del fusible (boca interior) |
   | `diodo` | PT 2,5-DIO/L-R | pieza N; texto ARRIBA = ánodo (lado del puente), ABAJO = cátodo. Mira de qué lado está dibujado el puente FBS; si está del otro lado, da vuelta la pieza |
   | `modulo` | RIF-0 | `43KR2 14`: módulo 2, borne 14. Si el texto no dice el módulo (`46KR A2`), toma el módulo cuyos otros cables tienen el número más parecido, con confianza baja |

   Los modelos con `ignora_lado_texto = 1` (barreras, toma) no usan el ARRIBA/ABAJO del texto, que ahí sale del símbolo del funcional (regla 7 del taller). Por ejemplo, `11SK1 L ARRIBA` va al borne L de abajo.
7. **Número que no existe.** Si el texto nombra un borne que la bornera no tiene (`62XDIO 5`, cuando 62XDIO tiene 3 piezas), se busca en la bornera vecina de la derecha del mismo riel, con confianza baja. Eso solo pasa si:
   - entre la última pieza y la etiqueta siguiente no entra otra pieza, o sea que no puede faltar una pieza sin reconocer;
   - la bornera vecina no usa esa boca con otro cable.

   Si no se cumplen las dos condiciones, el punto queda en la etiqueta, con confianza baja.

### Controles que trae la salida

- `revisar`: la boca recibe **dos cables distintos**. En este tablero marca justo los errores del instructivo que la referencia encontró con el funcional: 12F2 (1215/1216), 62XDIO 3 (1315/6203 y 6204/6206), 31XAI 1 ARRIBA (2142/3141) y 62XDO 1 ARRIBA (6201/6202).
- Aviso de **hueco entre piezas**, cuando entre dos piezas de una bornera entra otra: puede haber una pieza que no se reconoció, y desde ahí la numeración queda corrida y baja la confianza. En este tablero no hubo.
- Avisos de lista de materiales que no coincide con el dibujo, y de modelos que empatan en medidas.

## La base de datos

Se edita en dos planillas (Excel o bloc de notas, separador `;`, UTF-8) y se arma con `python cargar_base.py`:

**`datos/modelos.csv`**: una fila por modelo.

| campo | qué es |
|---|---|
| `codigo` | código del modelo, único (ej. `NDR-240-24`) |
| `fabricante`, `descripcion`, `fuente` | texto libre; en `fuente` va de dónde salen las medidas (URL de la hoja de datos) |
| `tipo` | `aparato` (un cuerpo por tag) o `pieza` (borneras y módulos: varias piezas pegadas a la derecha del tag) |
| `regla` | cómo se lee el texto del instructivo: `nombre`, `cuatro_puntos`, `dos_pisos`, `fusible`, `diodo`, `modulo` |
| `ancho_mm`, `alto_mm` | **medidas del cuerpo tal como está dibujado** (vista frontal, riel horizontal). Con esto se busca el cuerpo |
| `ancho_hoja_mm`, `alto_hoja_mm` | medidas de la hoja de datos, solo como control (`cargar_base.py` avisa si difieren más de 3 %) |
| `tol_pct` | tolerancia de las medidas en % (4 a 6) |
| `ignora_lado_texto` | 1 si el ARRIBA/ABAJO del texto no es físico (barreras, toma) |
| `lado_puente` | solo en el borne con diodo: de qué lado queda el puente en la orientación normal |
| `alias_bom` | cómo puede aparecer en la lista de materiales, separado por `|` (ej. `NDR-240-24|NDR-240`) |

**`datos/bornes.csv`**: una fila por borne.

| campo | qué es |
|---|---|
| `modelo` | el `codigo` de modelos.csv |
| `nombre` | nombre del borne (`TB2-1`, `11`, `impar_ARRIBA`, `3`...) |
| `alias` | cómo lo escribe el instructivo, separado por `|` (ej. `1 (-)|1(-)|-V`) |
| `x_mm` | desde el borde **izquierdo** del cuerpo |
| `y_mm` | desde el borde de **arriba**, hacia abajo; puede ser negativo o mayor que el alto si el borne sobresale |
| `radio_mm` | radio del tornillo o boca; sale como `r` en la salida |
| `lado` | `ARRIBA` / `ABAJO` (físico) |
| `fuente` | `hoja`, `bloque`, `bloque+hoja`, `foto`, `estimado` (si es `foto` o `estimado`, la confianza baja a media) |

En SQLite quedan las tablas `modelo` y `borne`, y la vista `bornes_mm`. `python cargar_base.py --listar` muestra lo que hay.

**Modelos cargados (18)**. Cubren todos los aparatos de este tablero:

| fabricante | código | tipo / regla | cuerpo (mm) | hoja de datos (mm) | bornes | origen de las posiciones |
|---|---|---|---|---|---|---|
| MEAN WELL | NDR-240-24 | aparato / nombre | 63 × 125,2 | 63 × 125,2 | 7 | hoja (vista frontal vectorial) |
| MEAN WELL | NDR-120-24 | aparato / nombre | 40 × 125,2 | 40 × 125,2 | 7 | hoja |
| MEAN WELL | DDR-120A-24 (B/C/D) | aparato / nombre | 32 × 125,2 | 32 × 125,2 | 7 | hoja (pág. 9) |
| SCHNEIDER | EZ9R36225 (diferencial 2P) | aparato / nombre | 35 × 85 | 36 × 81 | 4 | bloque; orden N-F |
| SCHNEIDER | EZ9F34210 (termomagnética 2P; alias ABB S202) | aparato / nombre | 35 × 85 | 36 × 81 | 4 | bloque; orden F-N |
| SCHNEIDER | DF101 | aparato / nombre | 17,5 × 84 | 17,5 × 88,5 | 2 | bloque |
| VIVION | TOMA-IRAM-VIVION | aparato / nombre | 32,2 × 68,8 | ~45 × – | 3 | foto (N-PE-L abajo) |
| GENÉRICO | MEGA-BASE | aparato / nombre | 84,8 × 24 | – | 2 | bloque |
| CHENZHU | GS8512-EX.22 | aparato / nombre | 12,6 × 99 | 12,5 × 99 | 10 | manual (vista lateral acotada) + bloque |
| CHENZHU | GS8536-EX | aparato / nombre | 18 × 98,9 | 17,5 × 99 | 14 | bloque (1, 2) + estimado (3 a 14) |
| PHOENIX | PT 6-QUATTRO 3212934 | pieza / cuatro_puntos | 8,2 × 90,5 | 8,2 × 90,5 | 4 | bloque |
| PHOENIX | PTT 2,5-2MT 3210258 | pieza / dos_pisos | 5,2 × 92,4 | 5,2 × 92,4 | 4 | bloque |
| PHOENIX | PTT 2,5-2MT BU 3210265 | pieza / dos_pisos | 5,2 × 92,4 | 5,2 × 92,4 | 4 | bloque |
| PHOENIX | PTT 2,5 (bloque Batfer) | pieza / dos_pisos | 6,2 × 76,9 | 5,2 × 68 | 4 | bloque |
| PHOENIX | PT 2,5-DIO/L-R 3210224 | pieza / diodo | 5,2 × 48,6 | 5,2 × 48,5 | 2 | bloque |
| PHOENIX | PTTB 4-HESI 3211886 | pieza / fusible | 6,0 × 101,9 | 6,2 × 102,9 | 4 | bloque |
| PHOENIX | RIF-0-RPT-12DC/21 | pieza / modulo | 6,1 × 91,7 | 6,2 × 93 | 5 | bloque; orden por la carcasa (fotos) |
| PHOENIX | RIF-0-RPT-24DC/21 | pieza / modulo | 6,1 × 91,7 | 6,2 × 93 | 5 | bloque |

Las hojas de datos descargadas están en `hojas_de_datos/`: MEAN WELL NDR-120, NDR-240, DDR-120 y el manual CHENZHU GS8512. Las hojas de Phoenix y Schneider dan el tamaño pero no la posición de los bornes; por eso esas posiciones se midieron una vez sobre el bloque CAD de la biblioteca Batfer.

## Cómo se agrega un modelo nuevo a la base

1. **Medidas del cuerpo.** Sacar ancho × alto de la hoja de datos. Si en el plano el bloque está dibujado con otra medida, poner en `ancho_mm`/`alto_mm` la **del bloque** y la de la hoja en `ancho_hoja_mm`/`alto_hoja_mm`. El programa busca lo que está dibujado.

2. **Posición de los bornes.** Hay tres caminos, de mejor a peor:

   a) **La hoja de datos trae la vista frontal vectorial** (MEAN WELL, muchas fuentes y barreras). Se mide con:
   ```
   python medir.py hoja hojas_de_datos\NDR-120-SPEC.pdf 4 270 420 325 555 --ancho_mm 40
   ```
   Los argumentos son: página 4 y el recuadro de la vista frontal en puntos PDF (x0 y0 x1 y1, origen abajo a la izquierda). La escala sale del ancho acotado. La salida es una tabla lista para copiar:
   ```
    n   x_mm    y_mm   radio_mm
    1    7.80    9.15    2.76
    2   14.26    9.03    2.15      <- TB2 pines 1..4 arriba
   ...
    7   14.10  116.84    3.25      <- TB1 pines 1..3 abajo
   ```
   Además deja `medir_control.png`, con cada círculo numerado, para saber cuál es cuál.

   b) **La hoja no trae posiciones, pero el bloque CAD sí las dibuja** (Phoenix, Schneider). Se abre un topográfico donde esté el aparato y se mide sobre el bloque:
   ```
   python medir.py plano ..\_referencia\topografico.pdf 8 836.9 675.5 --ancho_mm 6.1 --alto_mm 91.7 --pieza 2
   ```
   Los argumentos son la x y la y de la etiqueta amarilla, las medidas del cuerpo y qué pieza medir. Busca el cuerpo a la derecha de la etiqueta y lista los círculos de adentro en mm.

   c) **No hay nada:** se toman las proporciones de una foto o del catálogo (como en el toma 11SK1) y se pone `fuente = foto` o `estimado`.

3. **Cargar las filas:**
   - una fila en `datos/modelos.csv`: `tipo`, `regla`, `alias_bom` como figura en las listas de materiales, y `ignora_lado_texto` si el ARRIBA/ABAJO del funcional no es físico;
   - una fila por borne en `datos/bornes.csv`: `nombre`, `alias` como lo escribe el instructivo, `x_mm`, `y_mm`, `radio_mm`, `lado` y `fuente`.

   Ejemplo, un borne de una fuente:
   ```
   NDR-120-24;TB2-1;1 (-)|1(-)|-V;7.80;9.05;2.15;ARRIBA;hoja
   ```

4. **Armar la base:** `python cargar_base.py`. Controla que cada borne quede dentro del cuerpo y que no haya nombres repetidos, tipos o reglas desconocidos ni modelos sin bornes. Si hay errores, no toca la base.

5. **Probar:** correr `mapear.py` en un plano que tenga el aparato y mirar `control.png`: el cuerpo en verde y cada círculo sobre su tornillo o boca.

Si el modelo es una variante con la misma geometría (otra tensión, otro color), alcanza con copiar las filas y cambiar el código y los alias, o agregar el código nuevo a `alias_bom` del modelo que ya está.

## Archivos de esta carpeta

| archivo | qué es |
|---|---|
| `mapear.py` | el programa: plano + usos → puntos de borne |
| `geometria.py` | lectura del plano: rieles, etiquetas, cuerpos por medidas, círculos (para medir) |
| `bornes.db` | la base SQLite (se rearma desde los CSV) |
| `datos/modelos.csv`, `datos/bornes.csv` | la base en planillas: **lo que se edita** |
| `cargar_base.py` | arma y controla `bornes.db` (`--listar` para verla) |
| `medir.py` | mide un modelo nuevo sobre la hoja de datos o sobre el bloque CAD |
| `prueba_sin_detalle.py` | prueba de robustez: mapea con el dibujo sin tornillos ni bocas |
| `hojas_de_datos/` | hojas de datos usadas |
| `salida/bornes.json`, `salida/control.png`, `salida/control_general.png`, `salida/evaluacion.txt` | resultado en este tablero |
| `salida/prueba_sin_detalle/` | resultado de la prueba sin detalle |

## Limitaciones

- **El modelo tiene que estar en la base.** Si falta, o si el bloque del plano tiene otras medidas, el componente queda sin puntos y sale un aviso ("no encontré ningún cuerpo de la base junto a la etiqueta").
- **Muchas posiciones se midieron sobre el bloque CAD de la biblioteca Batfer** (todo Phoenix, Schneider, DF101, relés y MEGA), porque sus hojas no dan la posición de los bornes. En planos hechos con la misma biblioteca van a dar lo mismo que acá. Si otro dibujante usa otro bloque del mismo aparato, puede tener otras medidas, y hay que medirlo y cargarlo (el programa avisa porque no encuentra el cuerpo).
- **Modelos que miden igual** (diferencial y termomagnética 2P, relé de 12 y de 24 V, PTT gris y azul) se distinguen solo por la lista de materiales. Sin lista, el orden de los polos F-N de un 2P puede salir cambiado.
- **Orientación:** se supone la orientación normal (la de la hoja de datos, riel horizontal). Solo el borne con diodo se controla por el puente dibujado. Un aparato girado 180° o un riel vertical darían los bornes espejados.
- **Errores del instructivo** (módulo o tag mal puesto, como 43KR2 A2 o 62XDIO 3): el programa pone el punto donde dice el texto. Muchos se detectan con el control de "dos cables en la misma boca", pero para corregirlos hay que mirar el funcional.
- Hay reglas que son **convenciones** y salen con confianza baja o media:
  - bornes con nombre repetido (`-Vo`): se reparten de izquierda a derecha por número de cable; eléctricamente son iguales;
  - `46KR A2` sin número de módulo: se toma el módulo del cable de número más parecido;
  - el número que no existe se busca en la bornera vecina;
  - en el MEGA, ARRIBA = espárrago derecho.
- **Toma 11SK1:** el bloque es simplificado (32 mm, el real mide ~45 mm) y la posición de N-PE-L sale de proporciones medidas en una foto: confianza media. **GS8536:** los enchufes de 3 bornes (3 a 14) son estimados.
- El punto es el **centro del tornillo o boca**, no el borde por donde entra el cable. Si el ruteo necesita el borde, habría que agregar a la base el desplazamiento de entrada.
- Las etiquetas se reconocen por el tamaño y la capa de las que trae el JSON de usos, y los rieles por la capa `RIEL DIN`.

## Qué haría falta para llevarlo al programa

1. Un módulo `bornes_mm.py` en el programa que cargue `bornes.db` (una sola base compartida por todos los planos, guardada con versiones) y, para cada etiqueta del topográfico, devuelva los puntos con la función `mapear()` de este prototipo. El resto del programa sigue igual: el ruteo toma `x`, `y` y `r` de cada uso.
2. Que el programa pase el **modelo de cada tag desde la hoja de materiales del funcional**, que ya lee, y muestre los avisos: lista que no coincide con el dibujo, modelo que falta en la base, dos cables en una boca, hueco entre piezas.
3. Una pantalla para **dar de alta un modelo**: el formulario de las dos planillas más `medir.py` (elegir la vista frontal en la hoja de datos o el bloque en un plano, poner el nombre a cada círculo y guardar).
4. Soportar aparatos girados 180° y rieles verticales: guardar en la base un rasgo asimétrico del contorno, o pedir la orientación cuando haya duda.
5. Agregar a la base el punto de entrada del cable (borde del enchufe), si el ruteo lo necesita.
6. Revisar con el funcional los usos marcados `revisar` y los de confianza baja, antes de cablear.
