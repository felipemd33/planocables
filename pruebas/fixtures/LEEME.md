# Fixtures de la red de seguridad (etapa 0 del plan modular)

Copias de **solo lectura** de datos reales, para las pruebas. No se regeneran: si el original cambia, se copia de nuevo
a propósito y se actualiza esta tabla. Copiadas el 2026-10-07 (con `cp -p`: conservan la fecha del original).

## `pae_usuario/`: el trabajo real del PAE (ZPL-76884) con las marcas del usuario

Origen: `C:\Buscar Termos en plano\3 - Historial web\ce9fc4d9fcbd\` (la copia del taller). Sin PNG ni PDF: el plano es
`1 - Planos/Producto nuevo/ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.pdf`, el mismo archivo (11 569 256 bytes).

| Archivo | Modificado (original) | Bytes | sha1 |
|---|---|---|---|
| `instructivo.json` | 2026-10-07 11:00:08 | 148 908 | `712ba2a80b6bd589c2139e68030ae4c48384da48` |
| `layout.json` | 2026-10-07 10:58:40 | 7 290 | `d8714e6cb1100c95fabaa573a6e3962ef62b010b` |
| `estado.json` | 2026-10-07 10:58:40 | 2 617 | `3eed34264f7135ba73c6857976a701d20df4eb2a` |

Qué tiene `instructivo.json` (generado el 06/10/2026 07:31, después guardado desde la web):
- 136 líneas E6 (18 marcadas «hecho»), 30 pendientes, 0 sueltos, 24 en otra estación, 0 quitados;
- **salidas elegidas a mano**: «Todos los LI» por `[573.3, 448]` y «Todos los LD» por `[579.81, 448.54]`;
- estación E8 con 36 `hechos`; `producto` = ZPL-76884 rev 1; `wpc` y `proyector` vacíos; auditoría empezada sin checks.

`layout.json`: lector `eplan 2026.10.06-e8-bateria`.

## `wpc/`: el `.wpc` real del PAE (autorizado por el usuario el 2026-10-07)

Origen: `G:\Unidades compartidas\Batfer - Taller\20-14-BTF-BATFER-taller\4-Instructivos de montaje de VECTOR\WPC\mSafe2 PAE - 76884-1\`

| Archivo | Modificado (original) | Bytes | sha1 |
|---|---|---|---|
| `ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.wpc` | 2026-10-06 07:34:10 | 2 156 | `a38603bc04a3b7a067d30b64f9e88aab01e33c2a` |

Es un zip con un solo XML adentro (`ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.wpc`, 57 747 bytes, 2026-10-06 07:34).

## `productos.json`: el catálogo de productos con el que se sacaron las bases (etapa 2, 2026-10-07)

Copia de `programa/productos.json` tal como sale en la etapa 2 (los 5 productos decididos el 2026-10-07: 75286-1,
66817-1, 72715-1, 76857-1 y 76572-1). `programa/productos.json` lo cambia la web cada vez que el taller confirma un
producto (✎ en la línea «Producto»), así que las pruebas que guardan o comparan el producto (`volcar_bases_nuevas.py`,
`ab_planos.py`, `probar_web_humo.py`, `probar_producto.py` y la batería) usan ESTA copia, con
`PLANOCABLES_PRODUCTOS`: las bases no cambian porque el taller confirme productos. Nunca se escribe (la parte C de
`probar_producto.py`, que confirma productos con PUT, trabaja sobre una copia temporal).

| Archivo | Bytes | sha1 |
|---|---|---|
| `productos.json` | 1 038 | `3fad8b18b97d07763943c7bdbe7a9c6789b97c66` |

## `wpc/wpc.json` y `wpc/wpc_etapa0.json`: la configuración de la lista WPC (etapa 3, 2026-10-07)

Desde la etapa 3 el taller cambia `programa/web/wpc.json` desde la pantalla (ventana «Lista WPC» → ⚙ Parámetros,
`PUT /api/config/wpc`). Por eso las pruebas de la WPC (`pruebas/js/`, por `cargar_visor.cjs`) usan copias fijas, como el
catálogo de productos: los goldens no fallan porque el taller cambie un parámetro. Nunca se escriben (el PUT de
`probar_web_humo.py` trabaja sobre una copia temporal, con `PLANOCABLES_CONFIG_WPC`). `wpc/.gitattributes` evita que
git les cambie los fines de línea (así el sha1 de abajo se mantiene).

- `wpc.json`: copia de `programa/web/wpc.json` tal como sale en la etapa 3: con `parametros` (el panel), `productos`
  vacío, `marcador` por sección, `archivo_wpc` y el reemplazo de 4 mm² para **todos** los productos (decidido el
  2026-10-07). Es con la que se sacaron los goldens de `pruebas/bases/wpc/`. **Copiada de nuevo a propósito el
  2026-10-09** con la regla de largos nueva (decisión del taller): `acometida_LI` 150 → 75, `curva_LD` 100 nueva, las
  acometidas fuera del panel (fijas), `extra_puerta` junto a `puerta` y la nota `_nota_salen_a_LI` (tabla de antes y
  después en `pruebas/bases/wpc/cambios_regla_2026-10-09.md`).
- `wpc_etapa0.json`: `programa/web/wpc.json` de la etapa 0 (`git show 0ba6ee9:programa/web/wpc.json`): la forma vieja,
  sin `parametros`, con el reemplazo solo para el documento ZPL-76884. `wpc_core.test.cjs` la usa para probar que la
  forma vieja se sigue leyendo, que con ella el XML del PAE del usuario sale como el `.wpc` real (salvo los largos que
  cambia la regla del 2026-10-09; con los del real puestos a mano, idéntico), y que pasar el reemplazo a todos los
  productos cambia **solo** las filas negras y rojas de 4 mm² (color y sección).

| Archivo | Bytes | sha1 |
|---|---|---|
| `wpc/wpc.json` | 16 603 | `c0e41e2bebc0720d530d4082a06bbf55fbbe3dee` |
| `wpc/wpc_etapa0.json` | 4 471 | `c262b8ab57831fb313ddb3b83fd4580e5605088f` |

## `recorridos_e8.json`: el ruteo a mano de la estación 8 por producto (etapa E8-6, 2026-10-09)

Desde la etapa E8-6 el taller dibuja en la web el recorrido de los grupos de ruteo a mano de E8 y corrige los grupos;
se guarda por producto en `programa/recorridos_e8.json` (lo escribe la web con `PUT /api/trabajo/<id>/e8/grupos`). Las
pruebas usan una COPIA de este fixture (`PLANOCABLES_RECORRIDOS_E8`: `volcar_bases_nuevas.py`, la batería,
`probar_e8.py` y `probar_web_humo.py`), así que las bases no cambian porque el taller dibuje. No es una copia de datos
del taller: lo armé para las pruebas (2026-10-09):
- producto 72715-1 con el topográfico 72887 rev. 8 (`pruebas/trabajos/tpt_constructivo`): «Batería 35 mm²» dibujado
  (un tramo en la bandeja lateral izquierda y otro en el fondo), un grupo nuevo de placa («Placa 21PCB01 · bobinas
  61KR», con un tramo en el fondo y otro en la puerta) con 2150-2155 movidos a mano, y un cable movido que no existe
  (aviso). El TPT de `pruebas/trabajos/tpt` es del mismo producto con el topográfico 72887 rev. 7: no lo toma.
- un producto que no existe en las pruebas (no se tiene que mezclar).

| Archivo | Bytes | sha1 |
|---|---|---|
| `recorridos_e8.json` | 2 178 | `4eea9b80e08254fc1264d4bc6ef683e2d032494f` |
