# P5 – Ubicar bornes mirando la imagen del plano

Prototipo de método para ubicar cada borne en el plano topográfico **mirando el dibujo como una foto**. No lee
los trazos del PDF, así que sirve también para planos escaneados o hechos en otro CAD.

Tablero de prueba: CJ. CONTROLADOR mSafe2 (75286-1), topográfico 75441 REV.6, página PDF 8.

---

## 1. La idea

Los bornes que usa el taller son casi siempre los mismos, y en el topográfico cada tipo de boca o tornillo se ve
siempre igual: la boca push-in de un PT 6 QUATTRO, el tornillo con cruz de una MEAN WELL, la celda de un RIF-0.
Entonces:

1. Se guarda **una imagen chica (plantilla) de cada TIPO de boca o tornillo**. Es un recorte de unos 5 × 5 mm del
   plano.
2. En un plano nuevo, para cada etiqueta amarilla se busca esa plantilla **a la derecha de la etiqueta**, hasta la
   etiqueta siguiente del mismo riel (regla 1 del taller). Se usa `cv2.matchTemplate` de OpenCV, que marca cada
   lugar donde la imagen del plano se parece a la plantilla.
3. Las bocas encontradas se agrupan en **piezas** (columnas), **pisos** (arriba y abajo del riel) y **niveles**
   (boca extrema o interior). Después se **nombran por orden** con el mapa de nombres del modelo. Por ejemplo,
   en un QUATTRO `3.2` es la pieza 3 contando desde la etiqueta, boca interior de arriba.

La base de datos tiene tres cosas: la plantilla de cada tipo de boca, el mapa de nombres de cada modelo y sus
medidas (paso y alto en mm).

## 2. Qué hay en esta carpeta

| Archivo | Qué es |
|---|---|
| `mapear.py` | El programa: `python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json>` |
| `vision.py` | La parte de imagen: renderizar la página, encontrar las etiquetas amarillas por color, buscar plantillas (matchTemplate con supresión de no-máximos y ajuste sub-píxel) |
| `estructuras.py` | Cómo se agrupan y se nombran las bocas de cada tipo de aparato (bornera, relé, modular, fuente, barrera, aparato, espárragos) y cómo se lee el texto del instructivo |
| `base/modelos.json` | **La base de modelos**: 15 modelos, con la estructura, las plantillas, el paso, las medidas, el mapa de nombres, el radio del borne y de dónde sale cada dato |
| `base/recortes.json` | **De dónde sale cada plantilla**: de qué tag, qué boca y el clic aproximado |
| `base/plantillas/*.png` | Las 11 plantillas en escala de grises (10 px por punto) y su máscara |
| `base/plantillas.json` | Índice de las plantillas. Lo genera `hacer_base.py` y **no se edita a mano** |
| `base/plantillas_vista.png` | Hoja con todas las plantillas ampliadas, para mirarlas |
| `hacer_base.py` | Arma las plantillas a partir de `recortes.json` |
| `ver_zona.py` | Ayuda para agregar modelos: muestra una zona del plano con una grilla en puntos y prueba una plantilla en ella |
| `prueba_honesta.py` | Mide el acierto en los tags que **no** dieron plantilla. Lee la referencia y por eso va aparte |
| `prueba_escaneado.py` | Pasa el plano a imagen sucia (como un escaneo, sin vectores) y lo vuelve a mapear |
| `prueba_escala.py` | Achica y agranda el plano y lo vuelve a mapear con la misma base |
| `salida/bornes.json` | Resultado: 144 puntos, cada uno con `x`, `y`, `r`, confianza y la explicación de cómo se sacó (`como`) |
| `salida/control.png` | Imagen de control con cada punto marcado con un círculo del radio del borne y un número, más la leyenda |
| `salida/evaluacion.txt` | Salida de `evaluar.py` |
| `salida/evaluacion_sin_plantilla.txt`, `evaluacion_escaneado.txt`, `evaluacion_escala.txt` | Resultados de las tres pruebas |

## 3. Cómo funciona, paso a paso

Para cada componente de `usos_por_componente.json`:

1. **Imagen.** Se renderiza con pypdfium2, a 10 píxeles por punto, la zona que hace falta. Si el PDF es un
   escaneo, se mide su resolución y la comparación se suaviza para que se parezcan la plantilla (nítida) y el
   escaneo (borroso).
2. **Etiqueta.** Las etiquetas amarillas se buscan por **color** en la imagen. La posición que traen los usos
   indica cuál es cada una. Si una etiqueta no fuera amarilla, se usa una caja chica alrededor de esa posición.
3. **Modelo.** Primero quedan los modelos de la base que "entienden" los textos del instructivo: `12XP 1.4` solo
   lo entiende una bornera `N.p`, y `43KR2 A1` solo un relé. Entre esos, manda la **lista de materiales** si la
   imagen la confirma. Si la lista no dice nada, o dice un modelo que no encaja con el dibujo, gana el modelo
   cuya plantilla encaja mejor. Así se reconocieron 31XAI (la lista dice PTT 2,5-2MT, pero es un borne fusible
   HESI) y 43XCS, 46XC y 81XCM, que no traen modelo en la lista.
4. **Zona de búsqueda.**
   - Borneras y relés: desde la etiqueta hasta la etiqueta siguiente del mismo riel (regla del tag).
   - Aparatos que tienen la etiqueta encima (fuentes, termomagnéticas, barreras…): el ancho y el alto del
     aparato, con centro en la etiqueta.
5. **Búsqueda.** `cv2.matchTemplate` (correlación normalizada, con máscara) de cada plantilla del modelo, también
   espejada o girada 180° si el modelo lo permite. Por ejemplo, la boca de abajo de un borne es la de arriba
   dada vuelta. Después:
   - Se descartan los picos que se parecen poco.
   - Supresión de no-máximos: de dos picos pegados queda el mejor.
   - El centro se ajusta con precisión de décimas de píxel.
6. **Agrupar y nombrar** (`estructuras.py`):
   - **bornera**: columnas de bocas pegadas a la etiqueta y sin saltos (piezas). Las piezas verdes (PE) no se
     cuentan. Se ubica la altura del riel y, a cada lado, los niveles de boca: extremo e interior. Mapa de
     nombres:
     - QUATTRO: `N.p` (p1 = arriba extremo, p2 = arriba interior, p3 = abajo interior, p4 = abajo extremo).
     - PTT: `N ARRIBA/ABAJO`, con pieza ceil(N/2); N impar = boca extrema, N par = boca interior.
     - HESI: `k` = extrema, `Fk` = interior.
     - PT 2,5-DIO: ARRIBA = el lado donde está dibujado el puente.
   - **relé** (RIF-0): módulos en fila. El lado con 3 celdas es el de contactos (desde el extremo: 11, 14, 12) y el
     lado con 2 es la bobina (desde el extremo: A2, A1).
   - **modular** (termomagnéticas, diferenciales, DF101): los N polos más cercanos a la etiqueta, cada uno con su
     tornillo de arriba y de abajo.
   - **fuente** (MEAN WELL): la fila de 4 tornillos parejos de arriba es TB2 y la de 3 de abajo es TB1. Los pines
     van de izquierda a derecha, con la tabla de la hoja de datos.
   - **barrera** (CHENZHU): se ve el enchufe exterior de cada lado. Las filas que el dibujo no muestra se corren
     hacia adentro la medida de la hoja de datos.
   - **aparato** (toma IRAM): el dibujo no trae tornillos. Se busca el aparato entero y los bornes N, PE y L son
     puntos fijos de la plantilla, medidos en la foto.
   - **espárragos** (base MEGA): espárrago izquierdo y derecho.
7. **Errores del instructivo.** Dos arreglos para errores que se repiten:
   - Si un borne no existe en su tag (el instructivo pone `62XDIO 5 ARRIBA` y 62XDIO tiene 3 piezas), se busca
     el mismo borne en la etiqueta vecina del mismo riel.
   - En una boca push-in entra un solo cable. Si caen dos cables distintos en la misma boca, se queda el que
     más se parece a los cables de esa etiqueta y el otro pasa a la vecina.

   En los dos casos el punto sale con **confianza baja** y la explicación en `como`, para que alguien lo revise.
8. **Salida.** Por cada uso: `x`, `y` (punto PDF, origen abajo a la izquierda), `r` (radio del borne en pt),
   `confianza` (alta, media o baja), `modelo`, `tag_fisico` y `como`, que explica de dónde salió el punto
   (pieza, lado, nivel, plantilla, parecido NCC).

`mapear.py` no tiene coordenadas de este tablero y no lee `bornes_referencia.json`. Solo usa la imagen del
plano, los usos, la lista de materiales (si está al lado de los usos) y la base.

## 4. Cómo se usa

```
cd "C:\Buscar Termos en plano\prototipos\P5_vision_imagen"
python mapear.py ..\_referencia\topografico.pdf ..\_referencia\usos_por_componente.json salida\bornes.json
python ..\_referencia\evaluar.py salida\bornes.json
```

- La lista de materiales se toma sola si hay un `lista_materiales.txt` en la carpeta de los usos. Si está en
  otro lado se pasa con `--materiales <archivo>`.
- La imagen de control sale en `control.png`, al lado de la salida (o donde diga `--control`). **Siempre hay que
  mirarla**: los puntos verdes son de confianza alta, los naranjas de confianza media y los rojos de confianza
  baja.
- En pantalla se lista el modelo elegido para cada tag y por qué, y los usos que quedaron sin punto.
- Tarda entre 18 y 26 s en esta PC.

## 5. La base de datos de bornes

### Plantillas (una por TIPO de boca)

Todas salen de este mismo plano: todavía no había otro plano de la biblioteca Batfer para sacarlas. Por eso se
sacó **una sola plantilla por tipo de boca** y se usa en todos los tags de ese tipo. `base/recortes.json` dice
de qué tag y de qué boca sale cada una.

| Plantilla | Sale de | Qué boca | Modelos que la usan | Tags donde se aplica en este tablero |
|---|---|---|---|---|
| `boca_quattro` | 12XP | pieza 1, boca extrema de arriba | PT 6-QUATTRO | 12XP, 13XC1, 13X24 |
| `boca_octogono_u` | 43XCS | pieza 1, boca extrema de arriba | PTT 2,5-2MT, PT 2,5-DIO | 43XCS, 46XC, 81XCM, 31XEX, 43XDI, 62XDIO |
| `boca_octogono_cuadro` | 62XDO | pieza 1, boca extrema de arriba | PTT 2,5 | 62XDO |
| `boca_hesi` | 31XAI | boca extrema de arriba | PTTB 4-HESI | 31XAI |
| `celda_rif0` | 43KR | módulo 1, celda 11 | RIF-0 | 43KR, 46KR, 62KR |
| `tornillo_modular` | 11Q1 | polo izquierdo, arriba | EZ9R, EZ9F | 11Q1, 11Q2 |
| `tornillo_df101` | 12F1 | tornillo de arriba | DF101 | 12F1, 13F3 |
| `tornillo_meanwell` | 11PS1 | TB2 pin 1 | NDR, DDR (achicada a 0,6–0,75) | 11PS1, 13PS3 |
| `tornillo_barrera` | 31AIB1 | enchufe de arriba, tornillo izquierdo | GS8536, GS8512 | 31AIB1, 43DIB1, 43DIB2 |
| `esparrago_mega` | 12F2 | espárrago izquierdo | MEGA | 12F2 |
| `aparato_toma_iram` | 11SK1 | el toma entero | toma IRAM VIVION | 11SK1 |

Cada plantilla tiene una **máscara**: la mancha de la boca, un poco engordada. Con ella solo se compara lo que
está dentro de la boca, y no confunden el tope negro ni la pieza de al lado.

### Modelos (`base/modelos.json`)

Los 15 modelos de la bandeja de este tablero (algunos cubren variantes: 12 y 24 V del RIF-0, gris y BU del PTT 2,5-2MT, NDR-120 y NDR-240):

| Familia | Modelos |
|---|---|
| Borneras | PT 6-QUATTRO, PTT 2,5-2MT (gris y BU), PTT 2,5, PT 2,5-DIO/L-R, PTTB 4-HESI |
| Relés | RIF-0-RPT-12DC/21 y 24DC/21 |
| Protecciones | EZ9R36225, EZ9F34210 (vale igual para el ABB S202), DF101 |
| Fuentes | NDR-240-24 (igual NDR-120-24), DDR-120A-24 |
| Barreras | GS8512-EX.22, GS8536-EX |
| Otros | toma IRAM VIVION, base MEGA |

Cada modelo lleva `estructura`, `plantillas`, `variantes` (espejo o giro), `escalas`, `paso_mm`, `zona` (alto
y ancho en mm), `r_pt`, el **mapa de nombres** (`nombres`, `celdas`, `polos`, `filas` o `enchufes`), `alias`
(para reconocerlo en la lista de materiales) y `fuente`, que dice de dónde sale cada dato: hoja de datos, foto
del tablero o regla del taller.

## 6. Cómo se agrega un modelo nuevo a la base

Primero hay que mirar el modelo en el topográfico y decidir en cuál de estos tres casos está.

### Caso A: su boca se dibuja igual que una que ya está en la base (lo más común)

Por ejemplo, un borne PT 2,5 gris que se dibuja con la misma boca octogonal que el PTT 2,5-2MT. **No hace falta
recortar nada.** Se agrega una entrada en `base/modelos.json`, copiando la de un modelo parecido y cambiando los
datos:

```json
"PT 2,5": {
  "fabricante": "PHOENIX CONTACT", "codigo": "3209510", "alias": ["PT 2,5"],
  "estructura": "bornera", "zona": {"tipo": "derecha", "alto_mm": 61.5}, "paso_mm": 5.2,
  "plantillas": ["boca_octogono_u"], "variantes": ["normal", "espejo_v"], "escalas": [1.0],
  "bocas_por_lado": 1, "descartar_color": "verde", "r_pt": 1.3,
  "nombres": {"formato": "N LADO", "pieza": "N"},
  "fuente": "hoja de datos Phoenix 3209510"
}
```

Los números del ejemplo son solo ilustrativos: el paso, el alto y el radio se sacan de la hoja de datos, y el
radio también se puede medir con `ver_zona.py`.

Para comprobar que la plantilla encuentra sus bocas en el plano nuevo:

```
python ver_zona.py <plano.pdf> <pagina> x0 y0 x1 y1 --plantilla boca_octogono_u --variantes normal,espejo_v
```

Guarda `zona.png` con una grilla en puntos y un círculo con el parecido (NCC) en cada boca encontrada. Si el
modelo no está en la lista de materiales con un nombre que la base reconozca, se le agrega un `alias`.

### Caso B: su boca o tornillo se dibuja distinto (plantilla nueva)

1. Se busca un plano donde aparezca el modelo y se mira la zona con la grilla:
   `python ver_zona.py <plano.pdf> <pagina> x0 y0 x1 y1`
2. En `zona.png` se lee el centro **aproximado** de una boca (el "clic"). No tiene que ser exacto:
   `hacer_base.py` busca el centro solo, en la imagen.
3. Se agrega un renglón en `base/recortes.json`:
   ```json
   {"nombre": "boca_nueva", "tag": "XXTAG", "que": "pieza 1, boca extrema de arriba",
    "clic": [x, y], "r_pt": 2.0, "ancla": "contorno", "recorte_pt": [5.0, 5.2]}
   ```
   - `r_pt`: radio de la boca en pt.
   - `recorte_pt`: el tamaño del recorte, un poco más que la boca.
   - `ancla`: cómo se busca el centro. `contorno` sirve para la mayoría. `hueco` es para círculos
     concéntricos. `ancho_maximo` es para tornillos cortados por la carcasa.
   - Si la plantilla sale de otro plano, se agrega un bloque `plano` propio o se arma otro `recortes.json`.
     `hacer_base.py` acepta la ruta como argumento.
4. `python hacer_base.py`. Esto regenera `base/plantillas/*.png`, `base/plantillas.json` y
   `base/plantillas_vista.png`. Hay que mirar la vista: la cruz roja tiene que caer en el centro de la boca.
5. Se prueba con `ver_zona.py ... --plantilla boca_nueva` en **otro** tag del mismo tipo. Las bocas propias
   tienen que dar NCC de 0,8 o más, y lo que no es boca tiene que dar menos de 0,6.
6. Se agrega el modelo en `modelos.json`, como en el caso A, con `"plantillas": ["boca_nueva"]`.
7. Se corre `mapear.py` sobre ese plano y se mira `control.png`.

**Una plantilla por tipo de boca, no por tag.** Si se agregan plantillas de cada tag, el método "se encuentra a
sí mismo" y deja de ser una prueba.

### Caso C: tiene otra forma de agrupar las bocas

Si el aparato no encaja en ninguna estructura (bornera, relé, modular, fuente, barrera, aparato, espárragos),
hace falta programar una función nueva en `estructuras.py`, en `DETECTORES` y en `parsear`. Por ejemplo, una
bornera de 3 pisos con otra numeración. Esto lo hace quien mantiene el programa, no se resuelve con datos.

### Si cambia la escala del plano

Las plantillas guardan la escala del plano del que salieron (`mm_por_pt` en `recortes.json`). Si el plano nuevo
tiene otra escala (sale de `escala_mm_por_pt` de los usos), `mapear.py` agranda o achica las plantillas solo.
Está probado con el plano al 80 % y al 125 % (ver resultados).

## 7. Resultados

### Tablero de prueba (`salida/evaluacion.txt`)

```
BIEN (<= 1.5 pt ~ 2 mm): 139/140 = 99.3 %   |   con punto: 140/140   |   error mediano: 0.06 pt
barreras 20/20 · borneras_riel2 35/35 · borneras_riel3 26/26 · fuentes 10/10 · protecciones 18/18 · reles 30/31
```

Tarda entre 18 y 26 s. De los 144 puntos, 113 salen con confianza alta, 25 con media y 6 con baja.

La **única falla** es `43KR2 A2` (cable 1328), a 4,4 pt de la referencia. Es un error del instructivo, no de la
imagen:
- El instructivo dice 43KR**2** A2 y el punto se da en el A2 del módulo 2, que existe.
- El funcional y la foto 1.6 muestran el cable en el A2 del módulo 1. Los A2 están puenteados.

Con los datos de entrada (usos y plano) esto no se puede saber. Habría que corregir el instructivo.

Además quedan **2 usos sin punto**: `31XAI 2 ARRIBA` (3142) y `62XDO ARRIBA` (6202). Nombran bornes que no
existen: 31XAI tiene una sola pieza y 6202 no trae número. La referencia también los marca como dudosos y no se
evalúan.

### Prueba honesta: tags que NO dieron plantilla (`salida/evaluacion_sin_plantilla.txt`)

Las plantillas se recortaron de este mismo plano, y un tag que dio su plantilla se encuentra a sí mismo con
NCC 1,00. Por eso se mide aparte:

- **A. Tags que no dieron ninguna plantilla** (14 tags, 90 puntos): **90/90 = 100 %**.
- **B. Tags que sí dieron plantilla.** La plantilla se vuelve a recortar de **otro** tag del mismo tipo. El clic
  se corre 0,35 pt a propósito, como el de una persona. Se mide el tag original, que ahora no dio nada:

  | Plantilla | Recortada de | Tag medido | Resultado |
  |---|---|---|---|
  | `boca_quattro` | 13XC1 | 12XP | 4/4 |
  | `boca_octogono_u` | 43XDI | 43XCS | 4/4 |
  | `celda_rif0` | 46KR | 43KR | 12/13 (la falla es el 43KR2 A2 del instructivo) |
  | `tornillo_modular` | 11Q2 | 11Q1 | 4/4 |
  | `tornillo_df101` | 13F3 | 12F1 | 2/2 |
  | `tornillo_barrera` | 43DIB1 | 31AIB1 | 2/2 |
  | `tornillo_meanwell` | 13PS3 | 11PS1 | 4/4 (sacada de la DDR, que es más chica, y aplicada a la NDR) |

- **Acierto en tags sin plantilla propia: 122/123 = 99,2 %.**
- No se pueden probar así los 4 tags con un tipo de boca que aparece **una sola vez** en este plano: 11SK1,
  12F2, 31XAI y 62XDO, que suman 17 puntos. Con su propia plantilla dan 17/17, pero ese número no prueba nada.
  Se van a poder medir cuando haya otro plano con esos modelos.

### Sin lista de materiales

Solo se reconoce el modelo por la imagen: **135/140 = 96,4 %**. Las 4 fallas nuevas son de 11Q2. El dibujo de la
termomagnética y el del diferencial son iguales, y el orden de sus polos es distinto (F-N frente a N-F). Sin la
lista de materiales no hay forma de distinguirlos. Lo mismo pasa entre las barreras GS8512 y GS8536, pero ahí
los bornes que se usan caen en el mismo lugar. El programa avisa: "empata con … (el dibujo no los distingue)".

### Plano escaneado (`salida/evaluacion_escaneado.txt`)

El topográfico se pasa a una imagen sucia (desenfoque, ruido, JPEG) y se guarda como un PDF **sin vectores**. Se
mapea con la misma base:

| Imagen | Resultado |
|---|---|
| 300 dpi (4,2 px/pt), ruido 8, JPEG 70 (se usó para ajustar) | **139/140 = 99,3 %**, error mediano 0,09 pt |
| 200 dpi (2,8 px/pt), ruido 8, JPEG 70 (se usó para ajustar) | **139/140 = 99,3 %**, error mediano 0,11 pt |
| 250 dpi (3,5 px/pt), ruido 14, JPEG 50 (no se usó para ajustar) | **139/140 = 99,3 %**, error mediano 0,09 pt |
| 150 dpi (2,1 px/pt), ruido 8, JPEG 70 (no se usó para ajustar) | 110/140 = 78,6 %: fallan las borneras azules (31XEX, 43XDI), el HESI y parte de las barreras |

En todos los casos la única falla es la misma 43KR2 A2 del instructivo. A 150 dpi una boca de 2 mm ocupa unos 5
píxeles y ya no se reconoce bien. **Conclusión práctica: si hay que escanear un plano, que sea a 200 dpi o más.**

### Plano a otra escala (`salida/evaluacion_escala.txt`)

La página se achica o se agranda (sigue siendo vectorial) y se mapea con la misma base. Las plantillas se
escalan solas:

| Plano | Resultado |
|---|---|
| al 80 % (1,76 mm/pt) | **139/140 = 99,3 %**, 16 s |
| al 125 % (1,13 mm/pt) | **139/140 = 99,3 %**, 36 s |

## 8. Limitaciones

- **Las plantillas son del dibujo de la biblioteca Batfer.** Si un plano viene de otro CAD o de otro proveedor,
  y la boca se dibuja distinta, hay que recortar una plantilla nueva para ese tipo (caso B). Es un recorte por
  tipo de boca, no por tablero.
- **Solo se probó en un tablero.** Los tipos de boca que aparecen una sola vez (toma IRAM, MEGA, HESI, PTT 2,5)
  todavía no se probaron con una plantilla sacada de otro tag.
- **Orientación.** Las plantillas son para riel horizontal con los bornes de pie, que es como dibuja el taller.
  Se prueban espejadas y giradas 180°, pero no giradas 90°. Un riel vertical necesitaría agregar esa variante
  en `vision.Plantilla.variante`.
- **Lo que el dibujo no muestra sale de la hoja de datos, no de la imagen**: las filas escondidas de las
  barreras, que se corren una medida fija, y los bornes del toma IRAM, que son puntos proporcionales medidos en
  la foto (confianza media).
- **La plantilla del toma IRAM es el aparato entero** y trae adentro los textos "11SK1" y "220VAC". En otro
  tablero esos textos cambian y el parecido baja. No está probado cuánto. Cuando haya otro plano, conviene
  recortarla sin la etiqueta.
- **El dibujo no distingue algunos modelos**: termomagnética o diferencial, GS8512 o GS8536. Para esos manda la
  lista de materiales.
- **Errores del instructivo.** Cuando el texto nombra un borne que existe pero no es el real, la imagen no puede
  darse cuenta (43KR2 A2). Los arreglos de la etiqueta vecina y de la boca con dos cables son heurísticas: salen
  con confianza baja y alguien los tiene que revisar.
- **Etiquetas por color.** Si un escaneo es en blanco y negro, las etiquetas no se encuentran por color. En ese
  caso se usa la posición que traen los usos, con una caja chica, y la regla del tag pierde el límite de la
  etiqueta siguiente.
- **Tolerancias fijas en pt.** Hay algunas en `estructuras.py`, como el agrupamiento de columnas y niveles.
  Andan bien para escalas del 80 al 125 %. Más lejos de eso habría que pasarlas a mm.

## 9. Qué haría falta para llevarlo al programa

1. **Un módulo `bornes_imagen`** dentro del programa, con `vision.py` y `estructuras.py` y la base en una carpeta
   compartida del taller. El programa lo llamaría al cargar el topográfico, con los usos que ya arma para el
   instructivo, y guardaría el resultado junto al plano para no recalcularlo.
2. **Una pantalla de revisión en el visor.** Mostrar los puntos con su color de confianza y que el operario
   confirme o mueva los naranjas y rojos. Lo que se corrige a mano se guarda para ese plano.
3. **Agregar plantillas desde el visor.** Que el operario haga clic en una boca del topográfico, elija el tipo y
   el modelo, y el programa escriba `recortes.json` y corra `hacer_base.py`. Así no hace falta editar JSON a
   mano.
4. **Devolver al instructivo los avisos del mapeo**: bornes que no existen en su tag y dos cables en una boca
   push-in. Así se corrige el instructivo en lugar de adivinar.
5. **El ruteo necesita el punto de entrada del cable.** El punto de salida es el centro de la boca o tornillo.
   Si el ruteo necesita el borde por donde entra el cable, falta un dato por modelo: cuántos mm hacia afuera.
6. **Probar con 2 o 3 tableros más** antes de confiar en los modelos que aparecen una sola vez.

## 10. Cómo rehacer todo desde cero

```
python hacer_base.py                  (regenera las plantillas desde recortes.json)
python mapear.py ..\_referencia\topografico.pdf ..\_referencia\usos_por_componente.json salida\bornes.json
python ..\_referencia\evaluar.py salida\bornes.json
python prueba_honesta.py              (unos 3 minutos)
python prueba_escaneado.py            (unos 2 minutos)
python prueba_escala.py               (menos de 1 minuto)
```
