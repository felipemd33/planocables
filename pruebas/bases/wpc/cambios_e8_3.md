# Lista WPC: etapa E8-3 (WAGO del cargador y RS-485)

Lista WPC con «Pendientes LI↔LI» y «Otra estación» tildados (todas las filas), configuración fija de las pruebas
(`pruebas/fixtures/wpc/wpc.json`). «Largo» = el que va al CSV, en mm. «Fuera» = no va al arnés (destildado).

**Por qué cambia (etapa E8-3, «WAGO del cargador», 2026-10-08).** La regla de la WPC no cambia (la del 2026-10-06):
el cable que termina en un WAGO lleva la misma acometida que un borne (150 mm de la canaleta de la lateral al empalme).
Cambia lo que la estación 8 dice de esos cables, porque ahora está bien armada:

- **Cables del cargador con WAGO** (TPT: 1108, 1109, 1201, 1202; 66817: 1201, 1202). Antes el cable salía de la
  etiqueta del cargador y entraba a la canaleta horizontal de arriba. Ahora, como en la foto 2 del taller, baja por la
  canaleta vertical hasta su punta de abajo, donde queda el WAGO (debajo del cargador). La canaleta de la lateral pasa
  de unos 170 mm a unos 320-333 mm: **+150 o +200 mm por cable**.
- **RS-485 del cargador** (TPT: 8105 y 8106, «EMPALME con 12PS2»). El empalme está junto al cargador, en la lateral
  izquierda, no en la puerta. El tramo que viene de 33MX01 (E6, «→ LI») se medía como si siguiera a la puerta
  (+1850 mm); ahora se mide hasta el empalme en la lateral: **-1250 y -1300 mm**. El tramo del empalme a la placa
  21PCB01 (pendiente LI↔LI) tenía el valor fijo de un pendiente (2000 mm) y ahora se mide por la lateral hasta la
  puerta: **+200 mm**.
- **66817, 1101 y 1102** (del cargador en la lateral izquierda a 11XP en la derecha) no cambian: la WPC de un cable entre
  las dos laterales toma la canaleta de una sola (la derecha). Sigue para preguntar.
- **75287 y PAE:** sin cambios (el cargador va a la bornera 12XPS: no hay WAGO).

| Trabajo | Filas antes / después | Cambian de largo | Cambia solo el texto | Metros en el CSV (antes → después) |
|---|---|---:|---:|---|
| tpt_constructivo | 104 / 104 | 8 | 0 | 138.95 → 137.45 (-1.50) |
| tpt | 104 / 104 | 8 | 0 | 138.20 → 136.70 (-1.50) |
| 66817 | 86 / 86 | 2 | 0 | 114.85 → 115.15 (+0.30) |
| 75287 | 126 / 126 | 0 | 0 | 148.70 → 148.70 (+0.00) |
| 76884 | 190 / 190 | 0 | 0 | 168.05 → 168.05 (+0.00) |

## tpt_constructivo

Antes: `pruebas/bases/ins_tpt_constructivo.json` de la etapa E8-2 (commit adc66cc) · después: `pruebas/bases/ins_tpt_constructivo.json` (E8-3)

8 cables cambian de largo; 0 cambian solo el texto de «cómo» (o entran / salen).

| Cable | Origen → destino | Largo antes | Largo después | Diferencia | Cómo antes | Cómo después |
|---|---|---:|---:|---:|---|---|
| 1108 | 11PS1 + → LI | 600 | 800 | +200 | 75 (borne → canaleta) + canaleta de la bandeja 99 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 99 + curva a LI 100 + canaleta de la bandeja lateral izquierda 333 + 150 (canaleta → 12PS2 +), redondeado a 50 |
| 1109 | 11PS1 - → LI | 600 | 750 | +150 | 75 (borne → canaleta) + canaleta de la bandeja 87 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 87 + curva a LI 100 + canaleta de la bandeja lateral izquierda 326 + 150 (canaleta → 12PS2 -), redondeado a 50 |
| 1201 | 12F1 ARRIBA → LI | 800 | 950 | +150 | 75 (borne → canaleta) + canaleta de la bandeja 281 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 281 + curva a LI 100 + canaleta de la bandeja lateral izquierda 320 + 150 (canaleta → 12PS2 +), redondeado a 50 |
| 1202 | 12XP 2.1 → LI | 950 | 1100 | +150 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 + canaleta de la bandeja lateral izquierda 320 + 150 (canaleta → 12PS2 -), redondeado a 50 |
| 8105 | 21PCB01 32 → EMPALME con 12PS2 | 2000 | 2200 | +200 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral izquierda 340 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 8105 | 33MX01 D1+ → LI | 2150 | 850 | -1300 | 75 (borne → canaleta) + canaleta de la bandeja 176 + puerta / placa 1850 (EMPALME con 12PS2), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 176 + curva a LI 100 + canaleta de la bandeja lateral izquierda 327 + 150 (canaleta → EMPALME con 12PS2), redondeado a 50 |
| 8106 | 21PCB01 33 → EMPALME con 12PS2 | 2000 | 2200 | +200 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral izquierda 350 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 8106 | 33MX01 D1- → LI | 2450 | 1200 | -1250 | 75 (borne → canaleta) + canaleta de la bandeja 523 + puerta / placa 1850 (EMPALME con 12PS2), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 523 + curva a LI 100 + canaleta de la bandeja lateral izquierda 333 + 150 (canaleta → EMPALME con 12PS2), redondeado a 50 |

## tpt

Antes: `pruebas/bases/ins_tpt.json` de la etapa E8-2 (commit adc66cc) · después: `pruebas/bases/ins_tpt.json` (E8-3)

8 cables cambian de largo; 0 cambian solo el texto de «cómo» (o entran / salen).

| Cable | Origen → destino | Largo antes | Largo después | Diferencia | Cómo antes | Cómo después |
|---|---|---:|---:|---:|---|---|
| 1108 | 11PS1 + → LI | 600 | 800 | +200 | 75 (borne → canaleta) + canaleta de la bandeja 99 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 99 + curva a LI 100 + canaleta de la bandeja lateral izquierda 333 + 150 (canaleta → 12PS2 +), redondeado a 50 |
| 1109 | 11PS1 - → LI | 600 | 750 | +150 | 75 (borne → canaleta) + canaleta de la bandeja 87 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 87 + curva a LI 100 + canaleta de la bandeja lateral izquierda 326 + 150 (canaleta → 12PS2 -), redondeado a 50 |
| 1201 | 12F1 ARRIBA → LI | 800 | 950 | +150 | 75 (borne → canaleta) + canaleta de la bandeja 281 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 281 + curva a LI 100 + canaleta de la bandeja lateral izquierda 320 + 150 (canaleta → 12PS2 +), redondeado a 50 |
| 1202 | 12XP 2.1 → LI | 950 | 1100 | +150 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 + canaleta de la bandeja lateral izquierda 320 + 150 (canaleta → 12PS2 -), redondeado a 50 |
| 8105 | 21PCB01 32 → EMPALME con 12PS2 | 2000 | 2200 | +200 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral izquierda 340 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 8105 | 33MX01 D1+ → LI | 2150 | 850 | -1300 | 75 (borne → canaleta) + canaleta de la bandeja 176 + puerta / placa 1850 (EMPALME con 12PS2), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 176 + curva a LI 100 + canaleta de la bandeja lateral izquierda 327 + 150 (canaleta → EMPALME con 12PS2), redondeado a 50 |
| 8106 | 21PCB01 33 → EMPALME con 12PS2 | 2000 | 2200 | +200 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral izquierda 350 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 8106 | 33MX01 D1- → LI | 2450 | 1200 | -1250 | 75 (borne → canaleta) + canaleta de la bandeja 503 + puerta / placa 1850 (EMPALME con 12PS2), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 503 + curva a LI 100 + canaleta de la bandeja lateral izquierda 333 + 150 (canaleta → EMPALME con 12PS2), redondeado a 50 |

## 66817

Antes: `pruebas/bases/ins_66817.json` de la etapa E8-2 (commit adc66cc) · después: `pruebas/bases/ins_66817.json` (E8-3)

2 cables cambian de largo; 0 cambian solo el texto de «cómo» (o entran / salen).

| Cable | Origen → destino | Largo antes | Largo después | Diferencia | Cómo antes | Cómo después |
|---|---|---:|---:|---:|---|---|
| 1201 | 12F1 ARRIBA → LI | 800 | 950 | +150 | 75 (borne → canaleta) + canaleta de la bandeja 271 + curva a LI 100 + canaleta de la bandeja lateral izquierda 176 + 150 (canaleta → 12PS1 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 271 + curva a LI 100 + canaleta de la bandeja lateral izquierda 321 + 150 (canaleta → 12PS1 +), redondeado a 50 |
| 1202 | 12XP 4.1 → LI | 950 | 1100 | +150 | 75 (borne → canaleta) + canaleta de la bandeja 427 + curva a LI 100 + canaleta de la bandeja lateral izquierda 176 + 150 (canaleta → 12PS1 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 427 + curva a LI 100 + canaleta de la bandeja lateral izquierda 329 + 150 (canaleta → 12PS1 -), redondeado a 50 |

## 75287

Antes: `pruebas/bases/ins_75287.json` de la etapa E8-2 (commit adc66cc) · después: `pruebas/bases/ins_75287.json` (E8-3)

Sin cambios.

## 76884

Antes: `pruebas/bases/ins_76884.json` de la etapa E8-2 (commit adc66cc) · después: `pruebas/bases/ins_76884.json` (E8-3)

Sin cambios.
