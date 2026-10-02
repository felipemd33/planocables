# P1: catálogo de modelos + detector geométrico

Prototipo de mapeo de bornes para el topográfico de la bandeja. Tablero de prueba: CJ. CONTROLADOR mSafe2 (75286-1, topográfico 75441 REV.6).

## La idea en dos líneas

El taller usa casi siempre los mismos bornes y aparatos. Cada modelo se describe **una sola vez** en una base de datos (`catalogo.json`): cómo se ve su boca o tornillo en el bloque CAD de Batfer, cómo se ordenan las bocas en la pieza y cómo se llaman los pines. Después, un **motor único** (`mapear.py`) recorre el plano, busca esas formas a la derecha de cada etiqueta amarilla y nombra cada boca con las reglas del catálogo. No aprende nada ni necesita ejemplos: solo reglas y medidas.

**Para agregar un modelo se agrega una entrada al JSON. No se toca el código.**

## Resultado en este tablero

| | |
|---|---|
| **Puntaje (evaluar.py)** | **140 / 140 BIEN = 100 %** (a ≤ 1,5 pt ≈ 2 mm de la referencia) |
| Con punto | 140 / 140 |
| Error mediano | 0,01 pt |
| Tiempo | unos 15 a 20 s (el límite es 60 s) |
| Sin lista de materiales | 136 / 140 = 97,1 % (ver "Limitaciones") |

| familia | bien / total | error medio |
|---|---|---|
| barreras | 20 / 20 | 0,02 pt |
| borneras riel 2 | 35 / 35 | 0,02 pt |
| borneras riel 3 | 26 / 26 | 0,07 pt |
| fuentes | 10 / 10 | 0,00 pt |
| protecciones | 18 / 18 | 0,03 pt |
| relés | 31 / 31 | 0,01 pt |

Cada punto sale con una **confianza**:
- **alta** (116 puntos): la boca se vio en el dibujo y la regla de nombres es directa.
- **media** (28): la boca no está dibujada y se ubica con una medida del catálogo (enchufes ocultos de las barreras, bornes del toma), o se aplicó una regla de corrección del instructivo (etiqueta del bloque vecino, común puenteado, dos cables en la misma boca).
- **baja** (2): el uso no se puede resolver porque el instructivo está mal (`31XAI 2 ARRIBA`, que no existe, y `62XDO ARRIBA`, que no trae número). Quedan en la etiqueta, en rojo, para que alguien los mire. La referencia tampoco los evalúa.

Detalle en `salida/evaluacion.txt`. En `salida/control.png` está cada punto dibujado sobre el plano, con un círculo del tamaño de la boca y el rótulo `borne cable`. Verde es alta, naranja media y rojo baja. El recuadro celeste es la zona que se tomó para cada etiqueta, con el modelo elegido.

## Cómo se usa

```
python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json>
```

Opciones:
- `--materiales lista_materiales.txt`: por defecto se busca `lista_materiales.txt` en la misma carpeta que el json de usos.
- `--catalogo otro.json`: por defecto se usa `catalogo.json`, al lado de `mapear.py`.
- `--control imagen.png` (o `--control no`): por defecto se escribe `control.png` al lado de la salida.

Para este tablero:
```
cd "C:\Buscar Termos en plano\prototipos\P1_catalogo_geometrico"
python mapear.py ..\_referencia\topografico.pdf ..\_referencia\usos_por_componente.json salida\bornes.json
python ..\_referencia\evaluar.py salida\bornes.json
```

La salida tiene, para cada uso del instructivo: `texto`, `cables`, `x`, `y` (puntos PDF, origen abajo a la izquierda), `r` (radio de la boca en pt), `confianza`, `modelo` y `como`, que explica en palabras de dónde salió el punto (por ejemplo "PTT2.5: pieza 2 de 3, lado arriba, boca 0 (extremo)"). Además trae la lista de `avisos` para revisar: modelos que no coinciden con la lista de materiales, cables que comparten boca, etiquetas corregidas.

## Cómo funciona

1. **Lee el plano.** Toma los trazos vectoriales de la página con `programa/pdfvec.py`, las etiquetas amarillas de un render de la página y los tramos de riel de la capa `RIEL DIN`.
2. **Arma la zona de cada etiqueta.** Cada componente de `usos_por_componente.json` se asocia con su etiqueta amarilla y con su riel. La zona es lo que está **a la derecha de la etiqueta, hasta la etiqueta siguiente del mismo riel** (regla 1 del taller), con la altura del modelo. Los aparatos que llevan la etiqueta encima (fuentes, termomagnéticas, barreras) usan la zona alrededor de la etiqueta (`"anclaje": "sobre"`). Los que están fuera del riel (portafusible MEGA) usan `"anclaje": "libre"`.
3. **Elige el modelo.** Sale de la lista de materiales, buscando los alias del catálogo en el texto del renglón. Si el componente no figura, o si el modelo de la lista no aparece en el dibujo, se prueban todos los modelos del catálogo y se queda el que explica más usos. Si hay empate, desempata el color del dibujo (gris o azul). Siempre queda un aviso. Así se detectó que 31XAI no es un PTT 2,5-2MT, como dice la lista, sino un borne fusible PTTB 4-HESI.
4. **Busca las bocas con la firma del modelo.** Hay cuatro formas básicas en `primitivas.py`:
   - `circulo`: arcos agrupados por centro y radio. Sirve aunque la boca esté cortada por otras líneas o hecha con dos medias circunferencias. Se descartan los círculos con cruz en X, que son tornillos de tope.
   - `contorno`: lazo cerrado convexo de tal ancho y alto (rectángulo redondeado, octógono, abertura en U).
   - `tornillo_cortado`: la elipse de tornillo que la carcasa de las barreras corta por la mitad.
   - `caja`: el cuerpo del aparato, para bloques que no dibujan tornillos (el toma corriente).
   Las piezas PE (en verde) no se cuentan.
5. **Agrupa y nombra.** Según la `disposicion` del modelo:
   - `piezas` (bornes de riel, relés, modulares): las bocas se agrupan en columnas, que son las piezas contadas desde la etiqueta, y cada columna se parte en arriba y abajo del riel. Una pieza vale si tiene la cantidad de bocas del modelo. Así los topes y las piezas raras quedan afuera. Después, las reglas de nombres dicen pieza, lado y boca: en los QUATTRO, `N.p` va a la pieza N con el punto p; en los PTT, N va a la pieza ceil(N/2), con el extremo si N es impar y el interior si es par; en los relés, el lado de 3 bocas es contactos y el de 2 es bobina.
   - `filas` (fuentes, barreras, MEGA): se buscan filas de n tornillos iguales arriba y abajo, y cada pin tiene su grupo y su posición. En las barreras, los enchufes que el bloque no dibuja se ubican corridos la medida del manual (`filas_mm`).
   - `caja`: los bornes van en fracciones del ancho del cuerpo (toma IRAM: N, PE y L abajo).
6. **Controles de coherencia** (se activan por modelo en el catálogo):
   - `desborde`: si el borne no existe en el bloque (62XDIO tiene 3 piezas y el texto dice `62XDIO 5`), se busca en el bloque siguiente del mismo riel y de la misma hoja del funcional (62XDO). El instructivo a veces pone la etiqueta del bloque vecino.
   - `conductores_por_boca: 1`: en una boca push-in entra un solo cable. Si dos cables distintos caen en la misma boca, uno tiene la etiqueta equivocada. Se pasa al bloque siguiente el que deja todo coherente: ningún cable con dos puntas en el mismo bloque, porque eso se hace con puente y no con cable, y la boca de destino libre. Así se resolvieron `62XDIO 3 ARRIBA #6203` y `62XDIO 3 ABAJO #6204`, que en realidad van a 62XDO 3.
   - `comunes`: si un borne está cableado en menos módulos que su pareja (A2 en 1 módulo y A1 en 4), es un común unido con puente FBS, y el cable entra por el **primer módulo** del grupo. Así `43KR2 A2 #1328` queda en el A2 del módulo 1, como en la foto 1.6 y en el funcional. Lo mismo pasa con el 11 de 62KR y el cable 1308.
   - Dos cables en la misma boca de otros modelos: no se mueve nada, pero se avisa y se baja a confianza media. Puede ser un puente o derivación a propósito, o un error del instructivo (pasa en 12F2 y 31XAI).
7. **Escribe** `bornes.json` y la imagen de control.

## La base de datos: `catalogo.json`

Todas las medidas van en **milímetros del tablero real**. El motor las pasa a puntos PDF con la escala del plano (`escala_mm_por_pt` de los usos, 1,4086 mm/pt en este plano). Así la misma entrada sirve en planos con otra escala.

Modelos que tiene hoy (cubren todo este tablero):

| id | tipo | componentes de este tablero |
|---|---|---|
| `PT6-QUATTRO` | borne de riel, 1 piso, 4 bocas (`N.p`) | 12XP, 13XC1, 13X24 |
| `PTT2.5` | borne doble piso (impar/par) | 62XDO |
| `PTT2.5-2MT` | doble piso seccionable, gris | 43XCS, 46XC, 81XCM |
| `PTT2.5-2MT-BU` | doble piso seccionable, azul | 31XEX, 43XDI |
| `PT2.5-DIO` | borne con diodo, 1 boca por extremo | 62XDIO |
| `PTTB4-HESI` | borne fusible doble piso | 31XAI |
| `RIF-0-RPT` | relé modular (11/14/12 y A1/A2) | 43KR, 46KR, 62KR |
| `EASY9-RCCB-2P` | diferencial 2 polos (N, F) | 11Q1 |
| `MCB-2P` | termomagnética 2 polos (F, N) | 11Q2 |
| `DF101` | portafusible 10x38, 1 polo | 12F1, 13F3 |
| `MEANWELL-NDR` | fuente AC/DC (TB2 1-4 arriba, TB1 FG/N/L abajo) | 11PS1 |
| `MEANWELL-DDR` | conversor DC/DC | 13PS3 |
| `GS8512-EX` | barrera CHENZHU, entradas digitales | 43DIB1, 43DIB2 |
| `GS8536-EX` | barrera CHENZHU, entrada analógica | 31AIB1 |
| `TOMA-IRAM-DIN` | toma de riel sin tornillos dibujados (todo abajo) | 11SK1 |
| `MEGA-BASE` | portafusible MEGA de espárragos, fuera del riel | 12F2 |

Campos de cada modelo:

| campo | qué es |
|---|---|
| `id` | nombre corto, único |
| `alias` | textos que aparecen en la lista de materiales para este modelo (código comercial, código de pedido). Se compara sin espacios, sin mayúsculas y con `,` igual a `.` |
| `es_bornera` | `true` para bornes de riel; se cruza con el `es_bornera` de los usos |
| `anclaje` | `izquierda`: la etiqueta está a la izquierda y los bornes a su derecha (borneras, relés). `sobre`: la etiqueta está encima del aparato. `libre`: fuera del riel |
| `alto_mm`, `ancho_mm`, `paso_mm` | alto del aparato (para la zona), ancho (solo `libre`) y paso entre piezas |
| `polos` | en modulares `sobre`: cuántas columnas de tornillos, las más cercanas a la etiqueta |
| `color_dibujo` | color del dibujo del bloque (RGB 0-1), solo para desempatar modelos iguales de distinto color |
| `boca` | la **firma**: `primitiva` (`circulo`, `contorno`, `tornillo_cortado` o `caja`) y su tamaño (`r_mm` [mín, máx]; `w_mm`/`h_mm` [mín, máx]); `sin_x` descarta los círculos con cruz de tope; `color` exige un color |
| `disposicion` | `piezas` con `bocas` {arriba: n, abajo: n} (o `lados_por_cantidad` si los lados se reconocen por la cantidad, como en los relés); `filas` con `grupos` [{nombre, lado, n}]; o `caja` |
| `nombres` | cómo se pasa del texto del instructivo a la boca (ver abajo) |
| `fuente` | de dónde salió la información (hoja de datos, fotos) |

Reglas de `nombres` en disposición `piezas`: una lista `reglas`. Cada regla tiene un `patron`, que es una expresión regular sobre el borne; si el uso trae punto se escribe `borne.punto`. Además tiene:
- `pieza`: un número fijo, `"$1"` (el número del texto), `"ceil($1/2)"` o `"modulo"` (el número pegado a la etiqueta, como 43KR**2**).
- `lado`: `arriba`, `abajo`, `texto` (el ARRIBA/ABAJO del instructivo), `diodo` (según de qué lado está dibujado el puente) o el nombre de un lado (`contactos`, `bobina`).
- `boca`: 0 es la del extremo (lejos del riel), 1 es la interior, y así; `"paridad($1)"` da 0 si es impar y 1 si es par.

En disposición `filas`: `pines` {nombre: {grupo, pines: [..]}} o {grupo, fila, pin}, con `alias` de nombres ("V-" → "-V"). En `caja`: `pines` {nombre: {fx: fracción del ancho, desde: abajo/arriba, dy_mm}}.

## Cómo se agrega un modelo nuevo

Ejemplo: llega un tablero con bornes **Phoenix PT 4** (1 piso, 2 bocas push-in por pieza).

1. **Mirar el bloque en el plano.** Con `medir.py` se ven las formas que hay a la derecha de la etiqueta, con sus medidas en mm:
   ```
   python medir.py <topografico.pdf> <usos_por_componente.json> <TAG> --png zona.png
   ```
   Lista los círculos (radio, cantidad, columnas y paso), los contornos cerrados (ancho x alto) y los tornillos cortados. Con `--png` guarda un render ampliado de la zona para abrirlo y mirarlo. Por ejemplo, en 62XDO muestra 12 círculos de r 2,9 mm con paso 6,2 mm: esas son las bocas del PTT 2,5.
2. **Copiar la entrada de un modelo parecido** en `catalogo.json`. Para el PT 4 sirve el `PT2.5-DIO` o el `PTT2.5`. Cambiar:
   - `id`: `"PT4"`
   - `alias`: `["PT 4", "<código de pedido>"]`, tal como aparece en la lista de materiales.
   - `paso_mm` (ancho de la pieza, sale de la hoja de datos): 6,2.
   - `alto_mm` (alto del borne): el de la hoja de datos.
   - `boca`: la primitiva y el rango de tamaño que dio `medir.py`, con un margen de ±10 %. Por ejemplo `{"primitiva": "circulo", "r_mm": [2.4, 2.9]}`.
   - `disposicion`: `{"tipo": "piezas", "bocas": {"arriba": 1, "abajo": 1}}`.
   - `nombres`: `{"reglas": [{"patron": "^(\\d+)$", "pieza": "$1", "lado": "texto", "boca": 0}]}`, es decir, borne N = pieza N y el lado que diga el texto.
   - `fuente`: de dónde se sacó todo.
3. **Correr `mapear.py` y mirar `control.png`.** Si el modelo nuevo no aparece en un componente, el aviso lo dice ("la lista de materiales dice X pero el dibujo coincide mejor con Y"). En ese caso hay que revisar el rango de tamaño de la boca.

Que la firma no se confunda con otros modelos importa poco, porque la zona de cada etiqueta ya es chica. Lo que tiene que estar bien es el **rango de tamaño** (que no entren los LED, los tornillos de tope o los marcadores) y la **cantidad de bocas por pieza**, que es lo que descarta los topes y las piezas raras.

Si un modelo necesita una forma de boca que no está (por ejemplo, un borne de resorte con palanca), hay que agregar una primitiva nueva en `primitivas.py`. Es el único caso en que se toca código.

## Archivos

| archivo | qué es |
|---|---|
| `catalogo.json` | la base de datos de bornes (16 modelos) |
| `mapear.py` | el motor. Uso: `python mapear.py <topografico.pdf> <usos.json> <salida.json>` |
| `primitivas.py` | las formas básicas (círculo, contorno, tornillo cortado, rectángulo), genéricas y sin datos de ningún tablero |
| `medir.py` | ayuda para medir la firma de un modelo nuevo en la zona de una etiqueta |
| `salida/bornes.json` | los 146 puntos de este tablero (140 evaluables), con `r` |
| `salida/control.png` | la imagen de control |
| `salida/evaluacion.txt` | la salida de `evaluar.py` |

`mapear.py` no lee `bornes_referencia.json` ni tiene coordenadas de este tablero. Toma la región de la bandeja y la escala de `usos_por_componente.json`; todo lo demás sale del dibujo y del catálogo.

## Limitaciones

- **Termomagnética y diferencial se dibujan igual.** Sin lista de materiales el motor no los distingue, y el orden de los polos cambia (diferencial Easy9: N, F; termomagnética: F, N). Sin la lista, 11Q2 sale con los polos cambiados; es la única diferencia, 97,1 % contra 100 %. Con la lista de materiales anda bien.
- **Las barreras GS85xx y el toma dependen de medidas del catálogo.** El bloque dibuja solo el enchufe exterior de cada lado de la barrera; los interiores se ubican corridos lo que dice el manual (`filas_mm`). El toma no tiene tornillos dibujados y sus bornes van en fracciones del ancho del cuerpo, tomadas de la foto. Todos esos puntos salen con confianza media. Si Batfer cambia el bloque, hay que volver a medir.
- **Las reglas de corrección del instructivo** (`desborde`, `conductores_por_boca`, `comunes`) son generales, pero se calibraron con los casos de este tablero: 62XDIO/62XDO, 43KR y 62KR. En particular, lo de que "el cable del común entra por el primer módulo" es una convención (fotos 1.6 y 1.2) y no una ley eléctrica: si en otro tablero el cable entra por otro módulo del puente, el punto va a caer en el módulo 1. Estos puntos se marcan con confianza media y dejan un aviso.
- **El ARRIBA/ABAJO del texto** a veces sale del símbolo del funcional (regla 7). Para las barreras y el toma el catálogo lo ignora (`ignorar_lado_del_texto`). Para el diodo se usa el lado donde está dibujado el puente. Si aparece otro aparato con ese problema, hay que decirlo en su entrada.
- **La etiqueta amarilla** se busca por color en un render de la página. Si un plano usa otro color para las etiquetas, o las etiquetas se pisan, se usa la posición que trae `usos_por_componente.json` y queda un aviso.
- **Errores del instructivo que no se pueden deducir** (un borne que no existe y sin bloque vecino, un texto sin número) quedan con confianza baja, en la etiqueta.
- El punto que se entrega es el **centro de la boca o del tornillo**. En modulares y fuentes, el cable entra por el borde de arriba o de abajo del aparato, unos 5 a 9 pt más afuera. Si el ruteo necesita ese borde, hay que correr el punto en vertical según el lado.

## Qué haría falta para llevarlo al programa

1. Poner `catalogo.json`, `primitivas.py` y el motor dentro de `programa\` (por ejemplo `programa\bornes\`). El motor ya usa `pdfvec.page_strokes` del programa, y la entrada es la misma estructura de usos que arma el programa.
2. Llamar al motor después de armar el instructivo y antes del ruteo. El ruteo toma `x, y` de cada `texto#cable` en lugar del centro de la etiqueta. `r` sirve para dibujar la marca del borne.
3. Mostrar en la interfaz web los `avisos` y los puntos de confianza media o baja, para que el operario los confirme o los corra con un clic. Si se guarda esa corrección (por tablero), se puede volver a usar.
4. Que el generador del instructivo corrija lo que el motor detecta: la etiqueta del bloque vecino (62XDIO/62XDO), los comunes puenteados (43KR2 A2) y los textos sin número de módulo (`46KR A2`).
5. Una pantalla o comando para agregar modelos, que llame a `medir.py` sobre una etiqueta y proponga la entrada del JSON.
6. Probarlo con dos o tres tableros más, con otros modelos, para ajustar los rangos de tamaño y las reglas de corrección, que por ahora solo se validaron con este tablero.
