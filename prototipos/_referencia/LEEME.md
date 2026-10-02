# Datos de referencia para los prototipos de mapeo de bornes

Tablero de prueba: **CJ. CONTROLADOR mSafe2**. Funcional: 75287 REV.6. Topográfico: 75441 REV.6. Código del tablero: 75286-1. Se cablea en la estación **E6**.

## Qué hay en esta carpeta

| Archivo | Qué es |
|---|---|
| `topografico.pdf` | El plano topográfico. La bandeja está en la **página PDF 8** (índice 7). Región de la bandeja, en puntos PDF: x 520–1045, y 177–759. El origen está **abajo a la izquierda**. Escala: 1.4086 mm por punto. |
| `usos_por_componente.json` | Para cada componente de la bandeja: la posición de su etiqueta amarilla en el topográfico y los usos de sus bornes tal como los escribe el instructivo. Por ejemplo: texto `11PS1 1 (-)`, cable 1110, borne, punto, lado, parte ARRIBA/ABAJO. Es la **entrada** de todo prototipo. |
| `lista_materiales.txt` | Modelo de cada componente, sacado de la hoja de materiales del funcional. En un plano nuevo sale de ahí. |
| `bornes_referencia.json` | La **respuesta correcta** para este tablero: 145 puntos de conexión. Los armaron agentes con hoja de datos + geometría + fotos, y parte de ellos los revisó un segundo agente (`verificado`). Incluye los modelos, la regla que usó cada familia y las dudas. |
| `correcciones_<familia>.json` | Las correcciones de la verificación. `evaluar.py` las aplica solo. |
| `evaluar.py` | El **puntaje**: `python evaluar.py <salida.json>`. Un borne está BIEN si el punto queda a ≤ 1.5 pt (~2 mm) del de referencia. |
| `codigo_agentes\` | El código que usaron los agentes para cada familia. Sirve de inspiración, no hay que copiarlo tal cual. |
| `control_*.png` | Imágenes de control de la referencia: cada punto marcado sobre el dibujo. |

Otros datos, que se leen pero **no se tocan**:
- Funcional: `C:\Buscar Termos en plano\1 - Planos\75287 DIAGRAMA ELECTRICO mSafe2AC - REV.6.pdf`. La hoja de materiales es la página PDF 6.
- Fotos reales de este tablero ya cableado: `C:\Buscar Termos en plano\Cableado 75286-1\`.
- Programa: `C:\Buscar Termos en plano\programa\`. Se puede importar, pero **no se modifica**. `pdfvec.page_strokes(reader, 7, layer_names(reader), with_color=True)` devuelve `[(capa, op, [(x, y), ...], rgb)]`. Capas útiles: `COMPONENTES`/`00_COMPONENTS` (el dibujo de los aparatos), `Texto etiquetas` (las etiquetas amarillas), `RIEL DIN` y `CABLECANAL`.

## Reglas del taller (obligatorias)

1. **Una etiqueta (tag) nombra los bornes que tiene a su DERECHA, hasta la etiqueta siguiente del mismo riel.** Por ejemplo, las piezas de 13XC1 son las que están a la derecha de la etiqueta amarilla `13XC1` y antes de la próxima etiqueta. Se numeran de izquierda a derecha, sin contar los topes ni las piezas PE (verdes).
2. **Bornes de 4 puntos (PT 6 QUATTRO):** se escriben `N.p`. N es la pieza, contada desde la etiqueta. Los puntos 1 y 2 van arriba (1 es el extremo y 2 el interior) y los puntos 3 y 4 abajo (3 es el interior y 4 el extremo).
3. **Bornes de doble piso (PTT/PTTB 2,5):** se escriben `N ARRIBA` / `N ABAJO`. La pieza es ceil(N/2). Si N es impar es el piso de abajo, que tiene la entrada en el extremo, la más lejos del riel. Si N es par es el piso de arriba, con la entrada interior.
4. **Relés RIF-0 en módulos** (43KR1..4, 46KR1..2, 62KR1..3): los contactos 11/14/12 van arriba y A1/A2 abajo.
5. **Termomagnéticas y diferenciales:** tienen polos F y N, con tornillos arriba y abajo.
6. **Toma corriente 11SK1:** todos sus cables se conectan **por abajo**, porque se cambió el modelo del toma.
7. El ARRIBA/ABAJO del texto del instructivo a veces sale del **dibujo del funcional**, no de la posición física (pasa en barreras y en el borne con diodo). Lo que se mapea siempre es el **punto físico** del borne.

## Qué tiene que entregar cada prototipo

Cada prototipo va en su propia carpeta `prototipos\P<n>_<nombre>\` y lleva:
- `LEEME.md` en castellano, claro para la gente del taller: la idea, cómo funciona, cómo se usa, **cómo se agrega un modelo nuevo a la base**, los resultados, las limitaciones y lo que haría falta para llevarlo al programa.
- La **base de datos de bornes** del enfoque, en JSON o SQLite, con todos los modelos de este tablero.
- `mapear.py`, que se usa así: `python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json>`. Tarda menos de 60 s y no tiene coordenadas de este tablero escritas en el código.
- `salida\bornes.json`, en el formato de `evaluar.py`. Cada punto lleva además `r`, el radio del borne en pt, para dibujar la marca del tamaño del borne.
- `salida\control.png`, con los puntos marcados y rotulados.
- `salida\evaluacion.txt`, que es la salida de `evaluar.py`.
