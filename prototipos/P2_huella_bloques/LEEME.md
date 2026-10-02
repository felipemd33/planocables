# P2 · Huellas de bloques CAD

Prototipo de método para ubicar cada borne en el plano topográfico de la bandeja, usando una **base de datos de bornes** que se aprende una vez y sirve para los planos siguientes.

## La idea en pocas palabras

El topográfico se dibuja con **bloques de biblioteca**. Todos los PT 6 QUATTRO son el mismo dibujo. Lo mismo pasa con todos los RIF-0 y con la fuente NDR-240. Cada vez que el dibujante inserta el bloque, el PDF trae exactamente los mismos segmentos, corridos de lugar y a veces girados.

Entonces alcanza con guardar, para cada modelo:

1. su **huella**, que es la lista de segmentos del bloque medida desde su centro (el *ancla*), más el color del trazo;
2. dónde está **cada borne**, medido desde esa misma ancla. Por ejemplo, el contacto 11 del RIF-0 está 29,10 pt arriba del ancla.

En un plano nuevo se buscan en el dibujo todas las copias de cada huella. Cuando aparece una, sus bornes quedan ubicados sin medir nada a mano.

No se usan imágenes ni se lee texto. Se trabaja con los trazos vectoriales del PDF, así que la precisión es la del propio dibujo: el error mediano da **0,0 pt**.

## Cómo funciona

### Aprender (`aprender.py`, se corre una vez por cada plano verificado)

Parte de un plano cuyos bornes ya están bien puestos. En este caso es `bornes_referencia.json` de este tablero, con las correcciones de la verificación. Para cada modelo hace lo siguiente:

1. **Semilla.** Toma una instancia del bloque. Casi todos los bloques del taller traen un *wipeout*, una máscara blanca del tamaño del aparato. La semilla es la máscara más chica que contiene los bornes verificados. En las borneras y los relés se toma **una pieza** o **un módulo**. Si el bloque no tiene máscara, como la base MEGA, usa la tanda de trazos seguidos del PDF alrededor de los bornes.
2. **Huella.** Guarda los segmentos de la semilla medidos desde el centro de la máscara, que es el ancla.
3. **Huella de consenso.** Busca en el mismo plano las otras copias del bloque, por ejemplo los 9 módulos RIF-0 o las 11 piezas PTT gris. Se queda con los segmentos que aparecen en todas. Así saca rayas que no son del bloque, como un cable o una cota que pasa por arriba.
4. **Bornes.** Cada borne verificado se lleva a coordenadas del bloque y se guarda con un **nombre genérico**, igual para todos los tableros:
   - borneras: `ARRIBA_ext`, `ARRIBA_int`, `ABAJO_int`, `ABAJO_ext`;
   - relés: `11`, `14`, `12`, `A1`, `A2`;
   - protecciones: `polo1_ARRIBA` y los demás polos con su lado;
   - fuentes: `TB2_1` … `TB1_3`.

   Si un borne aparece en varias copias, se guarda la mediana. La dispersión en este plano fue menor a 0,02 pt.
5. **Bornes que el plano no usó.** Se completan de dos maneras:
   - **Por fila.** El dibujito de un borne se repite, sea un tornillo o una boca push-in. Se buscan sus copias alineadas dentro del bloque y se asignan en orden. Así salieron el `TB2_2`/`TB2_4`/`TB1_1` de las fuentes, el contacto `12` del RIF-0 y los pisos de abajo de las PTT.
   - **Derivados.** Son reglas de la hoja de datos escritas en el catálogo. Por ejemplo, el PE del toma IRAM está en el medio de N y L.
6. **Radio `r`.** Mide el hueco libre del dibujo alrededor del punto, sin pasar la mitad de la distancia al borne vecino.

### Mapear (`mapear.py`, cada plano nuevo, ~14 s)

`mapear.py` **solo lee la base**. No lee la referencia y no tiene coordenadas de ningún tablero.

1. Lee los trazos de la página de la bandeja con `pdfvec` del programa.
2. **Busca cada huella por hashing geométrico.**
   - Cada segmento del dibujo se indexa por su vector (dx, dy).
   - Cada segmento de la huella que encuentra su igual en el dibujo *vota* por una posición del ancla. Donde se juntan muchos votos hay una copia del bloque.
   - Se prueban giros de 0/90/180/270° y espejo.
   - Cada candidato se verifica sobre una imagen de las líneas con dos puntajes:
     - **directo:** qué parte de la huella cae sobre líneas dibujadas (tiene que ser ≥ 0,92);
     - **inverso:** qué parte de lo dibujado dentro de la caja explica la huella.
   - También se verifica el **color**. Así se distingue la PTT gris de la PTT azul, que tienen el mismo dibujo.
   - Si dos modelos se pisan, gana el que mejor explica el dibujo.
3. **Zona de cada tag (regla del taller).** La etiqueta amarilla nombra lo que tiene **a su derecha** hasta la etiqueta siguiente del mismo riel. Las piezas de la zona se cuentan de izquierda a derecha y los topes y los PE no cuentan, porque no son bloques de bornera de la base.
4. **Qué modelo es cada tag.**
   - Si el modelo de la lista de materiales está en la base y su bloque aparece en la zona, se usa ese. Es confianza **alta**.
   - Si no, se usa el bloque que se reconoció en la zona. Es confianza **media**. Esto corrige solo los errores de la lista de este tablero:
     - 11PS1: la lista dice NDR-120, pero el dibujo es el de la NDR-240;
     - 31XAI: la lista dice PTT 2,5-2MT, pero el dibujo es el borne fusible PTTB;
     - 13PS3 figura en la lista como 13PS2;
     - 43XCS no está en la lista.
5. **Cada uso del instructivo se traduce** a (pieza, borne genérico) según el esquema del modelo:

   | Esquema | Cómo se lee |
   |---|---|
   | `cuatro_puntos` | `N.p`, con 1 y 2 arriba y 3 y 4 abajo |
   | `doble_piso` | `N ARRIBA/ABAJO`, pieza = ceil(N/2), impar = extremo |
   | `fusible_doble_piso` | `N` / `FN` |
   | `modulos` | `43KR2 A1` = módulo 2, borne A1 |
   | `aparato` | pines con nombre, con alias como `1 (-)`, `L-3`, `+Vo` |

   Después se aplica el desplazamiento aprendido del borne, con el giro de la copia hallada.
6. **Errores típicos del instructivo** (salen con confianza **baja** y en rojo en `control.png`):
   - **Desborde.** El número no existe en la bornera. Por ejemplo, 62XDIO tiene 3 piezas y el instructivo pide la 5. Se usa el mismo número en la bornera siguiente del riel.
   - **Boca doble.** Dos cables distintos van a la misma boca push-in. Se pasa a la bornera siguiente el cable que respeta el orden de numeración de esa bornera.
   - **Pines con el mismo nombre.** Por ejemplo, dos `-Vo` en la DDR. Se reparten de izquierda a derecha por número de cable.
7. Escribe `bornes.json`, donde cada punto lleva `x`, `y`, `r`, `confianza` y `como` (qué bloque, qué giro, qué borne). También escribe `control.png`.

## Archivos

| Archivo | Qué es |
|---|---|
| `catalogo_modelos.json` | **Lo escribe una persona.** Por cada modelo dice cómo se llaman sus bornes (esquema), cómo aparece en la lista de materiales (patrones), las reglas de la hoja de datos (filas, derivados) y de qué plano verificado se aprende. No tiene coordenadas. |
| `base_bornes.json` | **La base de datos de bornes.** La genera `aprender.py`. Tiene los 16 modelos de este tablero, cada uno con su huella (segmentos, caja, color, hash, histograma de largos y ángulos) y sus 68 bornes en total (dx, dy, r, de dónde salió). |
| `huellas.py` | La biblioteca común: lectura del plano, hashing geométrico, verificación, zonas de tag y lectura del instructivo. |
| `aprender.py` | Genera la base a partir de los planos verificados. |
| `mapear.py` | Mapea un plano nuevo. Solo lee la base. |
| `validar_loo.py` | Validación dejando un tag afuera (ver Resultados). |
| `prueba_giro.py` | Gira todo el dibujo 90° y comprueba que se reencuentran los mismos bloques y bornes. |
| `salida/bornes.json`, `salida/control.png`, `salida/evaluacion.txt` | Resultado de este tablero. |
| `salida/bornes_loo.json`, `salida/evaluacion_loo.txt` | Resultado de la validación dejando un tag afuera. |
| `salida/prueba_giro.txt` | Resultado de la prueba de giro. |

## Cómo se usa

```
cd "C:\Buscar Termos en plano\prototipos\P2_huella_bloques"

rem 1. (una vez, o cuando se agrega un plano verificado) aprender la base
python aprender.py

rem 2. mapear un plano
python mapear.py <topografico.pdf> <usos_por_componente.json> salida\bornes.json
rem    opciones: --base otra_base.json  --materiales lista_materiales.txt  --control control.png
rem    la lista de materiales, si no se indica, es lista_materiales.txt de la carpeta de los usos

rem 3. puntaje (solo en este tablero, que tiene referencia)
python ..\_referencia\evaluar.py salida\bornes.json

rem 4. controles
python validar_loo.py
python prueba_giro.py <topografico.pdf> <usos_por_componente.json>
```

Hay que **mirar siempre `salida/control.png`**:

- los rectángulos de color son los bloques que se reconocieron;
- el círculo es el borne, dibujado con su radio `r`;
- verde es confianza alta, naranja media y rojo baja (revisar);
- lo que no tiene punto se lista en `sin_punto` dentro de `bornes.json`, con el motivo.

## Cómo se agrega un modelo nuevo a la base

La geometría **no se escribe a mano**: se aprende de un plano donde el modelo ya está bien ubicado. Hacen falta tres pasos.

**1. Escribir el modelo en `catalogo_modelos.json`.** Se agrega una entrada en `modelos`. Solo se escriben *nombres*, sin coordenadas. Los comentarios `//` del ejemplo son solo explicación y no van en el archivo:

```json
"PT4_TWIN": {
  "nombre": "PHOENIX PT 4-TWIN (borne de paso, 3 puntos)",
  "tipo": "pieza",                    // pieza (bornera), modulo (rele) o aparato
  "esquema": "cuatro_puntos",         // como escribe el instructivo sus bornes (ver tabla de esquemas)
  "patrones": ["PT ?4.?TWIN"],        // como aparece en la lista de materiales (expresion regular)
  "fuente": "hoja de datos / foto de donde sale la regla"
}
```

- Para un **aparato** se pone `"clave"`:
  - `"lado"` si tiene un tornillo arriba y otro abajo;
  - `"polos"` con la lista de polos de izquierda a derecha;
  - `"borne"` con la lista de números;
  - `"pin"` con la tabla de pines y sus nombres, como en las fuentes MEAN WELL.
- Si el plano verificado no usa todos los bornes, se pueden agregar:
  - `"filas"`: los bornes que van en fila y en qué orden, para que se completen copiando el dibujito del borne;
  - `"derivados"`: una regla de la hoja de datos, por ejemplo «el PE está en el medio de N y L».

**2. Ubicar sus bornes en un plano, una sola vez.** Se mapea el plano nuevo con `mapear.py`. Los usos del modelo nuevo salen en `sin_punto`. Alguien del taller marca esos puntos en un `bornes_referencia.json` con el mismo formato del de `_referencia`: `componente`, `texto`, `cables`, `x`, `y`. Alcanza con **un** tag de ese modelo y con los bornes que se usan.

**3. Agregar ese plano a `planos_verificados`** del catálogo. Se ponen las rutas del topográfico, de los usos y de la referencia, y en `tags` se dice qué modelo es cada tag. Después se corre `python aprender.py`, que lee el plano, busca el bloque, arma la huella y guarda los bornes.

Desde ese momento el modelo se reconoce solo en todos los planos que usen el mismo bloque de biblioteca.

- Si un modelo ya está aprendido de un plano anterior, no se vuelve a aprender: gana el primer plano de la lista.
- Para **corregir** un borne, se corrige el punto en la referencia de ese plano y se vuelve a correr `aprender.py`.

## Resultados (este tablero, 75441 REV.6)

**Modo normal** (`salida/evaluacion.txt`): **139 de 140 = 99,3 % BIEN**. Todos los usos evaluables tienen punto, el error mediano es 0,0 pt y tarda ~14 s.

| Familia | Bien / total |
|---|---|
| Barreras | 20/20 |
| Borneras riel 2 | 35/35 |
| Borneras riel 3 | 26/26 |
| Fuentes | 10/10 |
| Protecciones | 18/18 |
| Relés | 30/31 |

- **La única falla es `43KR2 A2` (cable 1328), a 4,3 pt.** El método lo pone en el A2 del módulo 2, que es lo que dice el instructivo. La referencia lo pone en el A2 del **módulo 1**, porque el funcional y la foto 1.6 lo muestran ahí: los A2 están puenteados con un FBS 4-6 y el cable entra por el primero. Esto no se puede sacar del topográfico ni de la base. Se dejó así a propósito: arreglarlo con una regla hecha para este caso sería trampa. Lo que conviene es corregir el rótulo en el instructivo.
- Salen 144 puntos, contando los 4 que la referencia deja como dudosos y no evalúa. Hay 2 usos sin punto:
  - `31XAI 2 ARRIBA`: la bornera tiene una sola pieza;
  - `62XDO ARRIBA`: el texto no trae número de borne.

**Validación dejando un tag afuera** (`salida/evaluacion_loo.txt`, la medida honesta de un plano nuevo). Para mapear cada tag T, la base se aprende **sin** T: sin sus bornes verificados y sin las copias del bloque que están en su zona.

- **Modelos que en este tablero aparecen en 2 o más tags: 100 de 101 = 99,0 % BIEN.** Son los RIF-0, PT 6 QUATTRO, PTT gris y azul, DF101 y GS8512. La falla es la misma 43KR2 A2. Esto es lo que va a pasar en un plano nuevo con un modelo que la base ya conoce.
- **Total: 100 de 140 = 71,4 %.** Los 39 usos sin punto son todos de modelos que en este tablero aparecen **una sola vez**. En su vuelta no hay de dónde aprenderlos, así que quedan sin punto y se informa el motivo: NDR-240, DDR-120, toma IRAM, diferencial, termomagnética, base MEGA, PTTB, PT 2,5-DIO, PTT de 6,2 mm y GS8536.
- **No inventa**: cuando no conoce el modelo, no pone el punto en otro lado. Hay un caso que conviene conocer. En la vuelta de 11Q2 la base no tiene la termomagnética, y el método avisa que en la zona hay un bloque parecido, el diferencial. No lo usa.

**Prueba de giro** (`salida/prueba_giro.txt`): con todo el dibujo girado 90°, se reencuentran las **52 de 52** copias de bloques con el mismo modelo. Los **220 de 220** puntos de borne caen en el mismo lugar, a menos de 0,2 pt. En este tablero todos los bloques están sin girar, así que esta prueba es la que muestra que el reconocimiento funciona también con bloques girados.

## Limitaciones

- **Sirve si el bloque es el mismo.** Si el dibujante usa otra versión del bloque, lo escala o lo dibuja a mano, la huella no coincide y ese tag sale *sin punto*, con el motivo. Hay que aprender esa versión como un modelo más. Un bloque *parecido* no alcanza.
- **La base se aprendió de un solo plano.** Cada modelo tiene una sola huella. Cuantos más planos verificados se agreguen, más versiones de bloque va a conocer.
- **Faltan bornes que este tablero no usa.** Algunos modelos solo tienen los bornes que se usaron acá:
  - GS8536 solo tiene el 1 y el 2;
  - PT 2,5-DIO tiene los dos lados;
  - DF101 y MEGA tienen arriba y abajo.

  Un uso de un borne que la base no tiene sale sin punto y dice «no se aprendió». Se completa con `filas` o `derivados` en el catálogo, o con otro plano verificado.
- **El ARRIBA/ABAJO del instructivo se aprende tal como viene.** En las barreras y en el borne con diodo, ese dato sale del funcional y no de la posición física (regla 7 del taller). La base guarda la relación entre el texto y el punto físico tal como la vio en el plano verificado. Si otro funcional dibuja el símbolo al revés, el punto sale en el otro lado.
- **Rieles horizontales.** El reconocimiento de bloques funciona girado. La regla de «bornes a la derecha de la etiqueta», en cambio, supone rieles horizontales, igual que los topográficos actuales.
- **Errores del instructivo.** El desborde y la boca doble se resuelven con reglas generales y salen marcados en rojo para revisar. Otros errores, como el 43KR2 A2, no se detectan.
- **El color cuenta.** Dos modelos con el mismo dibujo y distinto color, como la PTT gris y la azul, se separan por el color. Si el dibujante cambia el color de la capa, puede tomar uno por el otro. En ese caso decide la lista de materiales, si nombra el modelo.

## Qué haría falta para llevarlo al programa

1. Copiar `huellas.py` y `mapear.py` al programa, o importarlos. La función `mapear(plano, base, usos, lista)` devuelve los puntos con `x`, `y`, `r`, `confianza` y `como`, y los usos sin punto con su motivo. Es lo que el programa necesita para arrancar el cable en el borne.
2. Guardar `base_bornes.json` y `catalogo_modelos.json` en una carpeta común del taller, por ejemplo junto al programa. Si se quiere, la base se puede pasar a SQLite con una tabla de modelos, una de segmentos y una de bornes. El JSON ocupa 640 kB y carga en centésimas de segundo.
3. Una pantalla para **marcar los bornes que faltan**: mostrar el plano con los usos *sin punto*, hacer clic en cada borne y guardarlo como `bornes_referencia.json` de ese plano. Después se corre `aprender.py`. Así la base crece con cada tablero nuevo y el trabajo a mano se hace una vez por modelo, no una vez por plano.
4. Mostrar en el visor lo que salió con confianza baja o media (rojo o naranja) para que alguien lo confirme antes de imprimir el instructivo.
5. Correr `validar_loo.py` y `prueba_giro.py` cada vez que se toque la base, como prueba de que no se rompió nada.
