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
  2026-10-07). Es con la que se sacaron los goldens de `pruebas/bases/wpc/`.
- `wpc_etapa0.json`: `programa/web/wpc.json` de la etapa 0 (`git show 0ba6ee9:programa/web/wpc.json`): la forma vieja,
  sin `parametros`, con el reemplazo solo para el documento ZPL-76884. `wpc_core.test.cjs` la usa para probar que la
  forma vieja se sigue leyendo, que con ella el XML del PAE del usuario sale idéntico al `.wpc` real, y que pasar el
  reemplazo a todos los productos cambia **solo** las filas negras y rojas de 4 mm² (color y sección).

| Archivo | Bytes | sha1 |
|---|---|---|
| `wpc/wpc.json` | 15 917 | `ecdc0022a7fd04499eb755e6a38e748f3db84a93` |
| `wpc/wpc_etapa0.json` | 4 471 | `c262b8ab57831fb313ddb3b83fd4580e5605088f` |
