# P4 - Base de bornes que aprende de tableros verificados

## La idea en pocas palabras

En el taller siempre se usan los mismos aparatos: PT 6 QUATTRO, PTT 2,5, relés RIF-0, fuentes MEAN WELL, etc.
Una vez que en un tablero se ubicó bien un borne, por ejemplo "el punto 2 de un PT 6 QUATTRO", no hace falta volver a
calcularlo en el próximo plano. Alcanza con **recordar dónde está ese borne dentro del dibujo del aparato**.

La base guarda **ejemplos verificados**. Cada ejemplo es un aparato ya auditado, con la posición de cada uno de sus
bornes medida **en proporción al recuadro del aparato**: `u` va de 0 (borde izquierdo) a 1 (borde derecho) y `v` va de
0 (abajo) a 1 (arriba). Como son proporciones y no coordenadas del plano, valen en cualquier topográfico.

En un plano nuevo, `mapear.py` hace cuatro cosas:

1. Encuentra el recuadro de cada aparato en el dibujo.
2. Elige el ejemplo más parecido del mismo modelo.
3. Pasa las proporciones de ese ejemplo al recuadro nuevo.
4. **Ajusta** el punto al centro de la boca o tornillo dibujado más cercano (lo llamamos *snap*).

Cada tablero que se audita **agranda la base**. Los puntos que el operario corrige a mano en el visor del programa
se vuelven ejemplos nuevos.

**Resultado en el tablero de prueba (75286-1, 140 bornes evaluados):**

| Modo | BIEN (≤ 1,5 pt ≈ 2 mm) | Con punto | Tiempo |
|---|---|---|---|
| Normal (la base tiene los ejemplos de este tablero) | **140/140 = 100 %** | 140/140 | ~14 s |
| **Dejando-un-tag-afuera** (cada tag se mapea sin sus propios puntos) | **135/140 = 96,4 %** | 140/140 | ~14 s |

El número honesto es el segundo. El modo normal da 100 % porque la base ya aprendió este tablero; sirve para
comprobar que aprender y volver a aplicar no pierde precisión. El modo **dejando-un-tag-afuera** (LOO) mide cómo
andaría en un plano nuevo: por ejemplo, 13XC1 se ubica con los ejemplos de 12XP y 13X24, sin usar los suyos.

---

## Qué hay en la carpeta

| Archivo | Qué es |
|---|---|
| `modelos_base.json` | **Hoja de datos de cada modelo**, escrita a mano y **sin coordenadas**. Tiene el alias con que aparece en la lista de materiales, cómo se busca en el dibujo, la regla para traducir el texto del instructivo a un borne, los nombres de los bornes, la disposición de la hoja de datos y la simetría. |
| `base_bornes.json` | **La base de datos de bornes.** Son los modelos de arriba más los **ejemplos aprendidos**: por recuadro, los `u, v` de cada borne, el radio `r`, el círculo dibujado, un parche del dibujo para el ajuste fino y un descriptor del recuadro. También guarda la *memoria del instructivo* (ver más abajo). Hoy cubre los 16 modelos de este tablero, con 140 puntos de 48 recuadros. |
| `tableros/75286-1/modelos.json` | Modelo real de cada tag de este tablero, revisado en la auditoría. Corrige errores de la lista de materiales: 31XAI es PTTB 4-HESI, 13PS3 figura como 13PS2 y 43XCS no figura. |
| `nucleo.py` | Funciones comunes: lee el PDF, arma los recuadros, calcula el descriptor, detecta bocas y tornillos (círculos y "estadios"), detecta los puentes FBS y hace el ajuste fino. |
| `agregar_tablero.py` | **Aprende.** Suma a la base los puntos verificados de un tablero. |
| `mapear.py` | **Aplica.** Ubica los bornes del instructivo en un topográfico. |
| `salida/bornes.json` | Resultado en modo normal, en el formato de `evaluar.py`. Cada punto tiene `r`, `confianza`, `modelo`, `ajuste` y `nota`. |
| `salida/bornes_programa.json` | El mismo resultado en el formato del `bornes.json` que ya lee el programa (`puntos` + `renombrar`). |
| `salida/control.png` | Imagen de control del modo normal: cada punto marcado sobre el dibujo con un círculo del tamaño del borne y su rótulo `borne #cable`. Verde = confianza alta, naranja = media, rojo = baja. |
| `salida/evaluacion.txt` | Puntaje del modo normal (`evaluar.py`). |
| `salida/bornes_loo.json`, `salida/control_loo.png`, `salida/evaluacion_loo.txt` | Lo mismo, pero en modo dejando-un-tag-afuera. |

---

## Cómo funciona

### 1. El recuadro de cada aparato

En los topográficos de Batfer cada aparato es un bloque de CAD que trae un **polígono blanco de relleno** (la
máscara) del tamaño del aparato, de la pieza de bornera o del módulo de relé. `nucleo.py` junta todas esas
máscaras. Si falta la máscara, usa los contornos dibujados. Así se consigue un recuadro por pieza sin saber nada del
tablero.

De ahí sale el recuadro de cada componente:

- **Borneras y relés** (`"busqueda": "serie"`): son las piezas **a la derecha de la etiqueta amarilla, hasta la
  etiqueta siguiente del mismo riel** (regla del taller). Se reconocen por el tamaño de las piezas de los ejemplos,
  con 4 % de tolerancia. Las piezas PE (verdes) no se cuentan y un hueco grande corta el grupo.
- **Aparatos sueltos** (`"busqueda": "contiene"`): fuentes, termomagnéticas, portafusibles, barreras y toma. Es el
  recuadro que contiene la etiqueta y tiene el tamaño de los ejemplos.

### 2. El modelo

El modelo sale de la lista de materiales, con los alias de `modelos_base.json`. Si hay un
`tableros/<tablero>/modelos.json`, ese manda. `mapear.py` **comprueba que el dibujo coincida** con el modelo:

- Si la lista dice un modelo pero el dibujo es de otro, usa el del dibujo y lo avisa en la `nota`. Así pasó con 31XAI.
- Si un tag del plano no está en la lista pero hay uno parecido, usa ese. Es el caso de 13PS3, que la lista nombra 13PS2.

### 3. Del texto del instructivo al borne

Cada modelo tiene su **regla**, y las reglas son las del taller:

| Regla | Modelos | Ejemplo |
|---|---|---|
| `quattro` | PT 6 QUATTRO | `13XC1 3.2` = pieza 3, punto 2. El 1 es arriba extremo, el 2 arriba interior, el 3 abajo interior y el 4 abajo extremo. |
| `doble_piso` | PTT 2,5, PTT 2,5-2MT, -2MT BU | `81XCM 5 ARRIBA` = pieza ceil(5/2) = 3. Como 5 es impar va en el piso de abajo, con entrada extrema; ARRIBA es el extremo de arriba. |
| `dio` | PT 2,5-DIO/L-R | `62XDIO 2 ABAJO` = pieza 2, cátodo (ver *polaridad*). |
| `modulos` | RIF-0 | `43KR2 14` = módulo 2, borne 14. Si el texto no dice el módulo (`46KR A2`), se usa el módulo del cable de número más cercano. |
| `polos` | termomagnéticas, diferenciales, DF101 | `11Q1 N ARRIBA` = polo N, tornillo de arriba. |
| `tabla` | fuentes, barreras, toma, MEGA, PTTB-HESI | Una tabla texto → borne. Por ejemplo, en la fuente NDR `-V` es TB2.1 o TB2.2: dos cables con el mismo nombre se reparten por número de cable, de izquierda a derecha. |

Si el número de pieza pasa las piezas que tiene el componente (`62XDIO 5 ARRIBA`, cuando 62XDIO tiene 3), se
prueba en la **bornera vecina** con la misma regla. En la salida queda el `texto_correcto` para el `renombrar` del
programa.

### 4. Transferencia desde los ejemplos

De los ejemplos del mismo modelo que tienen ese borne, se eligen los 3 más parecidos según el **descriptor del
dibujo**: tamaño en mm, cantidad de trazos, largo de trazo por área, densidad de tinta y fracción de trazo verde y
azul. Se promedian sus `u, v`, pesados por parecido, y se llevan al recuadro nuevo.

Si ningún ejemplo tiene ese borne todavía, hay tres salidas:

- Se usa el borne gemelo por **simetría** (arriba ↔ abajo) espejado.
- Se busca un **pariente**: el mismo dibujo con otro nombre, o la misma familia.
- Se usa la **disposición de la hoja de datos**: se buscan las filas de bocas o tornillos dibujados dentro del
  recuadro y se asignan en el orden de la hoja.

### 5. Ajuste fino (snap)

El punto transferido se corre al centro del **círculo dibujado del mismo radio** que tenía el ejemplo (hasta
1,2 pt). Si el borne no es un círculo, se corre a donde el dibujo **coincide con el parche** guardado del ejemplo,
por correlación, hasta 1 pt. Esto corrige las pequeñas diferencias de dibujo entre un plano y otro.

### 6. Radio y confianza

- `r` es el radio de la boca o tornillo dibujado. Nunca pasa la mitad de la distancia al borne vecino.
- `confianza`:
  - **alta**: ejemplos del mismo modelo.
  - **media**: mismo dibujo de otro modelo, simetría, hoja de datos, texto resuelto con una heurística o con la memoria.
  - **baja**: pariente de dibujo distinto, o posición estimada.

### Memoria del instructivo

Cuando `agregar_tablero.py` encuentra un punto verificado que **no está donde dice el texto**, guarda esa
*reasignación*. Por ejemplo, `43KR2 A2 #1328` está en el módulo 1 y `62XDIO 3 ABAJO #6204` está en 62XDO. Si en otro
plano aparece **el mismo texto con el mismo cable** (el mismo funcional reutilizado), se aplica sola y queda con
confianza media, con la nota `memoria: ...`, para que el operario la mire.

---

## Cómo se usa

Todos los comandos se corren desde esta carpeta. `R` es la carpeta de los datos
(`C:\Buscar Termos en plano\prototipos\_referencia`).

### A. Plano nuevo: ubicar los bornes

```
python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json>
```

- La lista de materiales se toma de `lista_materiales.txt`, junto a los usos. También se puede pasar con `--lista`.
- `--modelos tableros/<tablero>/modelos.json` fuerza el modelo de algún tag, si la lista está mal.
- Deja `<salida.json>`, `bornes_programa.json` y `control.png` en la carpeta de la salida.
- **Mirar `control.png`**: lo naranja y lo rojo es lo primero que hay que revisar en el visor.

Ejemplo con este tablero:

```
python mapear.py %R%\topografico.pdf %R%\usos_por_componente.json salida\bornes.json
python %R%\evaluar.py salida\bornes.json
```

### B. Después de auditar un tablero: que la base aprenda

Los puntos buenos de un tablero se suman a la base. Se le pueden pasar varios archivos, y si un borne está en más de
uno manda el **último**:

```
python agregar_tablero.py <topografico.pdf> <usos_por_componente.json> <bornes.json del programa> <instructivo.json> --tablero 75xxx-1 [--modelos tableros\75xxx-1\modelos.json]
```

- `bornes.json` del programa (o una salida de `mapear.py`): son los puntos del mapeo. Los de confianza `baja` no se aprenden.
- `instructivo.json` del programa: se toman los **`bornes_usuario`**, que son los puntos que el operario ajustó a
  mano en el visor. Mandan sobre el mapeo. Si el texto ya estaba renombrado (`43KR1 A2#1328`), se reconoce por el
  número de cable.
- También acepta `bornes_referencia.json`, con sus `correcciones_*.json` al lado, o un diccionario simple
  `{"texto#cable": [x, y]}`.
- Si el tablero ya estaba en la base, sus ejemplos **se reemplazan**, no se duplican.
- Solo hay que agregar tableros **auditados**: la base aprende lo que se le da.

Así se armó la base actual:

```
python agregar_tablero.py %R%\topografico.pdf %R%\usos_por_componente.json %R%\bornes_referencia.json --tablero 75286-1 --modelos tableros\75286-1\modelos.json
```

### C. Medir cómo andaría en un plano nuevo (dejando-un-tag-afuera)

```
python mapear.py %R%\topografico.pdf %R%\usos_por_componente.json salida\bornes_loo.json --loo
python %R%\evaluar.py salida\bornes_loo.json
```

Con `--loo` cada componente se mapea con una base **sin sus propios ejemplos**: ni los de sus piezas, ni los que
otro tag dejó en sus piezas, ni su memoria del instructivo. `evaluar.py` siempre escribe `evaluacion.txt`, así que
hay que renombrarlo a `evaluacion_loo.txt`. Con `--sin-memoria` se apaga la memoria del instructivo también en el
modo normal.

---

## Cómo se agrega un MODELO NUEVO a la base

Cuando aparece un aparato que la base no conoce, `mapear.py` lo avisa en `no_ubicados` con el mensaje
`modelo desconocido: agregarlo a modelos_base.json`.

**Paso 1. Escribir la hoja de datos en `modelos_base.json`.** Esto se hace una sola vez por modelo y sin coordenadas.
Ejemplo de una fuente:

```json
"MEAN WELL NDR": {
  "familia": "fuente",
  "forma": "meanwell_ndr",
  "alias": ["NDR\\s*-"],
  "busqueda": "contiene",
  "regla": {"tipo": "tabla", "ignorar_lado": true,
            "tabla": {"-V": ["TB2.1", "TB2.2"], "+V": ["TB2.3", "TB2.4"], "N": "TB1.2", "L": "TB1.3"}},
  "bornes": ["TB2.1", "TB2.2", "TB2.3", "TB2.4", "TB1.1", "TB1.2", "TB1.3"],
  "disposicion": [["TB2.1", "TB2.2", "TB2.3", "TB2.4"], ["TB1.1", "TB1.2", "TB1.3"]],
  "nota": "Hoja de datos: TB2 (salida, arriba) ..., TB1 (entrada, abajo) ..."
}
```

| Campo | Qué poner |
|---|---|
| `familia` | `bornera`, `rele`, `fuente`, `proteccion`, `barrera`, `toma`... Los parientes se buscan en la misma familia. |
| `forma` | Nombre del **dibujo**. Si dos modelos tienen el mismo dibujo (diferencial y termomagnética 2P), se pone la misma `forma` y se prestan ejemplos entre ellos. |
| `alias` | Expresiones que lo reconocen en la lista de materiales. |
| `busqueda` | `serie` para piezas a la derecha de la etiqueta; `contiene` para un aparato que contiene la etiqueta. |
| `regla` | Una de `quattro`, `doble_piso`, `dio`, `modulos`, `polos` (con `"polos": ["N", "F"]`) o `tabla` (texto → borne). |
| `bornes` | Nombres de los bornes. |
| `disposicion` | Filas de bornes tal como se ven de frente, de arriba hacia abajo y de izquierda a derecha. **Es lo que se usa mientras no haya ejemplos**: se buscan las filas de bocas o tornillos dibujados y se asignan en ese orden. |
| `simetria_vertical` (opcional) | Pares arriba ↔ abajo. Sirven para deducir un borne que ningún ejemplo tiene todavía. |
| `polaridad` (opcional) | Para piezas con diodo: `{"borne_lado_puente": "ARRIBA"}` quiere decir que ese borne es la boca más cercana al puente FBS dibujado. |
| `franja` (opcional) | Para aparatos que no traen tornillos dibujados: `{"lado": "abajo", "orden": ["N", "PE", "L"]}`. Los bornes se reparten parejo en la franja del borde. Es una estimación y queda con confianza baja. |

**Paso 2. Mapear el plano.** El modelo nuevo sale con la disposición de la hoja de datos (confianza media) o con un
pariente (confianza baja).

**Paso 3. Revisar en el visor** del programa y corregir a mano los puntos que estén mal.

**Paso 4. Correr `agregar_tablero.py`** con el `bornes.json` y el `instructivo.json` de ese tablero. Desde ese
momento el modelo tiene ejemplos, y en los planos siguientes sale con confianza alta, transferido y ajustado.

---

## Resultados

`salida/evaluacion.txt`, modo normal:

```
BIEN (<= 1.5 pt ~ 2 mm): 140/140 = 100.0 %   |   con punto: 140/140   |   error mediano: 0.0 pt
barreras 20/20 · borneras_riel2 35/35 · borneras_riel3 26/26 · fuentes 10/10 · protecciones 18/18 · reles 31/31
```

`salida/evaluacion_loo.txt`, dejando-un-tag-afuera:

```
BIEN (<= 1.5 pt ~ 2 mm): 135/140 = 96.4 %   |   con punto: 140/140   |   error mediano: 0.01 pt
barreras 20/20 · borneras_riel2 33/35 · borneras_riel3 26/26 · fuentes 8/10 · protecciones 18/18 · reles 30/31
```

En LOO, 17 de los 25 tags se ubicaron con ejemplos del mismo modelo de **otros** tags. En el caso de 11Q1 ↔ 11Q2
fue con ejemplos de otro modelo con el mismo dibujo. Los otros 8 tags son de un modelo que en este tablero aparece
una sola vez:

- Con la hoja de datos: 11PS1, 13PS3, 11SK1, 12F2, 31AIB1 y 62XDIO.
- Con un pariente: 31XAI y 62XDO.

Es lo mismo que va a pasar la primera vez que aparezca un modelo nuevo. Aun así, quedan bien todos salvo los 5 de
abajo.

**Las 5 fallas de LOO, y por qué:**

| Borne | Error | Por qué |
|---|---|---|
| `43KR2 A2 #1328` | 4,3 pt | Error del instructivo: el cable va en el A2 del **módulo 1** (los A2 están puenteados). Sin la memoria de este tablero no se puede saber. En modo normal lo resuelve la memoria. |
| `62XDIO 3 ABAJO #6204` | 40 pt | Error del instructivo: es **62XDO** 3. El texto dice un borne que sí existe en 62XDIO, así que no hay forma de sospecharlo. En modo normal lo resuelve la memoria. |
| `62XDIO 3 ARRIBA #6203` | 38 pt | Lo mismo: es 62XDO 3. |
| `11SK1 N ABAJO`, `11SK1 L ARRIBA` | 2,8 pt | El toma no tiene tornillos en el dibujo y es el único del tablero. Sin su ejemplo, los bornes se reparten parejo en la franja de abajo, con confianza baja. Van en el lado y el orden correctos, pero corridos unos 2 mm. |

Lo que sí resolvió el enfoque sin ejemplos propios:

- **62XDIO**, el borne con diodo: el ARRIBA/ABAJO del texto es ánodo/cátodo, no la posición física. La hoja de datos
  dice que el ánodo está del lado de las ranuras del puente, y el programa busca el **puente FBS dibujado** para saber
  de qué lado está. Ubica bien los 4 bornes propios.
- **31XAI**: la lista dice PTT 2,5-2MT, pero el dibujo no coincide. Se ubicó con parientes doble piso.
- **62XDO**: se ubicó con el pariente PTT 2,5-2MT, porque tiene el mismo tipo de pieza.
- **31AIB1**: se ubicó con la barrera pariente GS8512, porque tiene los mismos números de borne.
- **Fuentes y MEGA**: se ubicaron con la disposición de la hoja de datos, buscando las filas de tornillos dibujados.

Tiempos: `mapear.py` tarda unos 14 s (normal o LOO) y `agregar_tablero.py` unos 20 s.

---

## Limitaciones

- **El 100 % del modo normal no es mérito del método**: la base ya tiene este tablero. Hay que mirar el 96,4 % de LOO.
  Además, este es el único tablero de la base, así que la prueba de "plano nuevo" es la LOO dentro del mismo plano.
  En un plano de otro dibujante los bloques pueden variar más.
- **Depende de que el aparato tenga su máscara blanca, o un contorno, del tamaño de siempre.** Si un bloque se dibuja
  a otra escala o girado, el tamaño no coincide y cae al camino "pariente/hoja de datos", que es menos preciso. Hoy no
  maneja aparatos girados 90°.
- **La base aprende lo que se le da.** Un punto mal verificado se copia en los planos siguientes. Por eso solo se
  agregan tableros auditados, y los puntos `baja` no se aprenden.
- **Los errores del instructivo** (tag o módulo equivocado) solo se corrigen si ya se vieron en otro tablero con el
  mismo texto y cable, que es la memoria. Si no, el punto sale donde dice el texto.
- **Aparatos sin tornillos dibujados** (el toma): la primera vez la posición es estimada.
- Textos que ninguna regla entiende quedan en `no_ubicados` con el motivo. En este tablero son 2 usos dudosos que la
  referencia tampoco evalúa: `31XAI 2 ARRIBA #3142` y `62XDO ARRIBA #6202`.
- El descriptor es simple (tamaño, trazos, tinta, colores). Con muchos ejemplos de un modelo alcanza para elegir el
  más parecido, pero no reconoce un aparato sin ayuda de la lista de materiales.

## Qué haría falta para llevarlo al programa

1. **Llamarlo desde el programa** cuando se carga un topográfico. Hay que armar `usos_por_componente.json` con los
   datos que el programa ya tiene (etiquetas del topográfico y usos del instructivo), correr `mapear.py` y guardar
   `bornes_programa.json` como el `bornes.json` del trabajo. Ese formato ya lo lee `web.py`: `puntos` y `renombrar`.
2. **Un botón "Aprender de este tablero"** en el visor, que corra `agregar_tablero.py` con el `bornes.json` y el
   `instructivo.json` del trabajo (sus `bornes_usuario`) cuando el operario termina la auditoría.
3. **Pintar la confianza en el visor**, de modo que lo naranja y lo rojo quede para revisar primero, y mostrar la
   `nota` de cada punto: por qué lo puso ahí, de qué ejemplo salió y si fue memoria o bornera vecina.
4. **Guardar la base en un lugar compartido** de la red del taller, con copia de seguridad, para que todas las
   estaciones aprendan de todos los tableros.
5. **Una pantalla para cargar modelos nuevos** (`modelos_base.json`) sin editar JSON a mano: nombre, alias, regla y
   filas de bornes.
6. Con varios tableros en la base, conviene **repetir la prueba LOO por tablero** (sacar un tablero entero y mapearlo
   con los demás), que es la medida real de cómo anda en un plano nuevo.
