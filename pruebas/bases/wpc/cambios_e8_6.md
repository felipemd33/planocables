# Lista WPC antes y después de la etapa E8-6 (ruteo a mano por grupos y cables directos del cargador)

Lista WPC con «Pendientes LI↔LI» y «Otra estación» tildados (todas las filas), configuración fija de las pruebas
(`pruebas/fixtures/wpc/wpc.json`). «Largo» = el que va al CSV, en mm. «Fuera» = no va al arnés (destildado).

Etapa E8-6 (2026-10-09): ruteo a mano por grupos y cables directos del cargador.

- **El ruteo a mano NO cambia la lista WPC** (decisión del taller: la WPC no usa estos largos). En el TPT (los dos),
  el 66817 y el 75287 la lista da IGUAL, aunque el TPT con el constructivo tiene recorridos dibujados y cables movidos
  de grupo (fixture de las pruebas). Las líneas de las laterales siguen con su ruta automática, que es la que lee la WPC.
- **Lo único que cambia es el PAE (ZPL-76884), por los cables DIRECTOS** (dato del taller del 2026-10-08: en el PAE y la
  Vista, debajo del cargador hay borneras para no usar WAGO, y los cables del cargador van conectados directo a los
  bornes, sin pasar por el ducto). Antes (desde antes de la etapa E8-1) estos cables bajaban hasta la canaleta de abajo
  de 12XPS y volvían a subir (310-320 mm en la lateral); ahora van derecho del cargador al borne (50-60 mm). Son
  pendientes LI↔LI: su largo en la WPC es «canaleta de la lateral + margen + agregado a LI».
  - 1221-1226 (6 mm²): 750 → 450 mm.
  - El RS-485 del cargador (s/n 12PS1 A, B, GND, VCC, 0,32 mm²) cambia igual, pero queda fuera del arnés (comunicación).
  - 1201 (12F3 → 12XPS 5 ABAJO): mismo largo (1100 mm); solo cambia el texto de «cómo» (canaleta de la lateral 261 → 260
    mm): antes la bajada se corría medio punto hacia el punto de la canaleta que había dejado el cable 1223, que ya no
    pasa por ahí.
- En el 75287 (la Vista) los cables del cargador a 12XPS no son cables numerados del funcional: no hay nada que cambiar.
- **Pulido del 2026-10-09 (solo el texto):** el «cómo» de los cables directos (1221-1226 y el RS-485) dice «directo al
  borne 50 + margen 200 + agregado a LI 200» en lugar de «canaleta de la bandeja lateral izquierda 50 + …» (no pasan por
  la canaleta). El largo y el CSV no cambian; en los goldens solo cambia ese texto en `wpc_76884_pend_otra.json` (las
  tablas de abajo quedan como se sacaron en la etapa E8-6).

| Trabajo | Filas antes / después | Cambian de largo | Cambia solo el texto | Metros en el CSV (antes → después) |
|---|---|---:|---:|---|
| 76884 | 190 / 190 | 10 | 1 | 168.05 → 166.25 (-1.80) |
| tpt_constructivo | 104 / 104 | 0 | 0 | 136.95 → 136.95 (+0.00) |
| tpt | 104 / 104 | 0 | 0 | 136.20 → 136.20 (+0.00) |
| 66817 | 86 / 86 | 0 | 0 | 115.15 → 115.15 (+0.00) |
| 75287 | 126 / 126 | 0 | 0 | 148.60 → 148.60 (+0.00) |

## 76884

Antes: `pruebas/bases/ins_76884.json` de la etapa E8-5 (commit a7af499) · después: `pruebas/bases/ins_76884.json`

10 cables cambian de largo; 1 cambian solo el texto de «cómo» (o entran / salen).

| Cable | Origen → destino | Largo antes | Largo después | Diferencia | Cómo antes | Cómo después |
|---|---|---:|---:|---:|---|---|
| 1201 | 12F3 ARRIBA → LI | 1100 | 1100 | 0 | 75 (borne → canaleta) + canaleta de la bandeja 492 + curva a LI 100 + canaleta de la bandeja lateral izquierda 261 + 150 (canaleta → 12XPS 5 ABAJO), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 492 + curva a LI 100 + canaleta de la bandeja lateral izquierda 260 + 150 (canaleta → 12XPS 5 ABAJO), redondeado a 50 |
| 1221 | 12PS1 +Pan → 12XPS 3 ARRIBA | 750 | 450 | -300 | canaleta de la bandeja lateral izquierda 310 + margen 200 + agregado a LI 200, redondeado a 50 | canaleta de la bandeja lateral izquierda 50 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1222 | 12PS1 -Pan → 12XPS 4 ARRIBA | 750 | 450 | -300 | canaleta de la bandeja lateral izquierda 310 + margen 200 + agregado a LI 200, redondeado a 50 | canaleta de la bandeja lateral izquierda 50 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1223 | 12PS1 +Bat → 12XPS 5 ARRIBA | 750 | 450 | -300 | canaleta de la bandeja lateral izquierda 320 + margen 200 + agregado a LI 200, redondeado a 50 | canaleta de la bandeja lateral izquierda 50 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1224 | 12PS1 -Bat → 12XPS 6 ARRIBA | 750 | 450 | -300 | canaleta de la bandeja lateral izquierda 320 + margen 200 + agregado a LI 200, redondeado a 50 | canaleta de la bandeja lateral izquierda 50 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1225 | 12PS1 +Car → 12XPS 8 ARRIBA | 750 | 450 | -300 | canaleta de la bandeja lateral izquierda 310 + margen 200 + agregado a LI 200, redondeado a 50 | canaleta de la bandeja lateral izquierda 50 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1226 | 12PS1 -Car → 12XPS 9 ARRIBA | 750 | 450 | -300 | canaleta de la bandeja lateral izquierda 310 + margen 200 + agregado a LI 200, redondeado a 50 | canaleta de la bandeja lateral izquierda 50 + margen 200 + agregado a LI 200, redondeado a 50 |
| s/n 12PS1 A | 12PS1 A → 12XPS 10 ARRIBA | 750 (fuera) | 500 (fuera) | -250 | canaleta de la bandeja lateral izquierda 320 + margen 200 + agregado a LI 200, redondeado a 50 | canaleta de la bandeja lateral izquierda 60 + margen 200 + agregado a LI 200, redondeado a 50 |
| s/n 12PS1 B | 12PS1 B → 12XPS 11 ARRIBA | 750 (fuera) | 450 (fuera) | -300 | canaleta de la bandeja lateral izquierda 310 + margen 200 + agregado a LI 200, redondeado a 50 | canaleta de la bandeja lateral izquierda 50 + margen 200 + agregado a LI 200, redondeado a 50 |
| s/n 12PS1 GND | 12PS1 GND → 12XPS 12 ARRIBA | 750 (fuera) | 450 (fuera) | -300 | canaleta de la bandeja lateral izquierda 310 + margen 200 + agregado a LI 200, redondeado a 50 | canaleta de la bandeja lateral izquierda 50 + margen 200 + agregado a LI 200, redondeado a 50 |
| s/n 12PS1 VCC | 12PS1 VCC → 12XPS 13 ARRIBA | 750 (fuera) | 500 (fuera) | -250 | canaleta de la bandeja lateral izquierda 320 + margen 200 + agregado a LI 200, redondeado a 50 | canaleta de la bandeja lateral izquierda 60 + margen 200 + agregado a LI 200, redondeado a 50 |

## tpt_constructivo

Antes: `pruebas/bases/ins_tpt_constructivo.json` de la etapa E8-5 (commit a7af499) · después: `pruebas/bases/ins_tpt_constructivo.json`

Sin cambios.

## tpt

Antes: `pruebas/bases/ins_tpt.json` de la etapa E8-5 (commit a7af499) · después: `pruebas/bases/ins_tpt.json`

Sin cambios.

## 66817

Antes: `pruebas/bases/ins_66817.json` de la etapa E8-5 (commit a7af499) · después: `pruebas/bases/ins_66817.json`

Sin cambios.

## 75287

Antes: `pruebas/bases/ins_75287.json` de la etapa E8-5 (commit a7af499) · después: `pruebas/bases/ins_75287.json`

Sin cambios.
