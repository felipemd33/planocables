# Mapeo automático de bornes (programa/bornes)

## Qué hace

Cuando se genera el instructivo de cableado, el programa ubica **cada borne en el dibujo del topográfico**, para que cada cable salga del tornillo o de la boca correcta. Antes, en un plano nuevo, salía de la etiqueta amarilla del aparato.

1. Del **funcional** sale qué bornes usa cada cable: `instructivo.usos_bandeja`. También sale la **lista de materiales**, si el funcional la trae (`instructivo.materiales_funcional`, la hoja con PHOENIX, SCHNEIDER, MEAN WELL...).
2. El **motor** (`motor.py`) mira el dibujo a la derecha de cada etiqueta amarilla. Con el modelo del aparato (`catalogo.json`) reconoce sus bocas y las nombra.
3. El modelo sale de la lista de materiales. Si no figura, sale de la forma del dibujo.
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

- **Modelos que no están en el catálogo**: la lista de materiales nombra para un tag un modelo que `catalogo.json` no tiene (por ejemplo `MOXA ioLogik E1240 (32AI1)`); sus bornes se ubicaron por la geometría como otro modelo o quedaron en la etiqueta. Es la lista de modelos para agregar al catálogo (queda en `ins['mapeo']['modelos_faltantes']`).
- **Textos con el lado físico distinto del dibujo del funcional**: puntas cuyo ARRIBA/ABAJO cambió por el punto real del borne (barreras 1/2 ABAJO → ARRIBA, 61XDIO) o por el lado forzado en «Componentes y orden». En el visor, pasando el mouse sobre el texto subrayado se ve lo que dice el funcional.

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
   - `alias`: los textos de la lista de materiales, como el código comercial o el código de pedido;
   - `paso_mm` y `alto_mm`: salen de la hoja de datos;
   - `boca`: primitiva y rango de tamaño, el que dio `medir.py` ±10 %;
   - `disposicion`;
   - `nombres`;
   - `fuente`: de dónde salió la información.
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

## Archivos

| archivo | qué es |
|---|---|
| `__init__.py` | Lo que usa el programa: `aplicar_al_layout` (todo junto), `mapear_trabajo` (motor con cache), `componer_bornes` (automático + manual). |
| `motor.py` | El motor (`Motor(pdf, usos, catalogo, materiales).mapear()`). Se puede correr suelto para pruebas. |
| `primitivas.py` | Formas genéricas: círculo, contorno, tornillo cortado, caja. |
| `catalogo.json` | Los modelos de bornes y aparatos (17 hoy), con sus medidas en mm y las reglas de nombres. |
| `medir.py` | Ayuda para medir un bloque y agregar un modelo. |

Probado con el 75286/75287 (140 de 140 puntos con la lista de materiales del funcional; el instructivo sale igual al verificado) y con el 66817 (104 de 104).
