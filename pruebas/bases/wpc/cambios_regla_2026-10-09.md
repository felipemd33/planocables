# Lista WPC antes y después de la regla de largos del 2026-10-09 (cables a las laterales y a la puerta)

Lista WPC con «Pendientes LI↔LI» y «Otra estación» tildados (todas las filas), configuración fija de las pruebas
(`pruebas/fixtures/wpc/wpc.json`). «Largo» = el que va al CSV, en mm. «Fuera» = no va al arnés (destildado).

Regla del taller del 2026-10-09 (antes, la del 2026-10-06), para los cables que salen de la bandeja con la estación E8:

- **Muere en una lateral** (LI o LD; a la LD los cables mueren siempre ahí): 75 (borne → canaleta) + canaleta de la
  bandeja + la curva de la posterior a **esa** lateral (`curva_LI` / `curva_LD`, 100) + canaleta de la lateral + **75**
  (canaleta → borne o aparato; antes 150). Por eso bajan 50 mm casi todos (el redondeo a 50 se come los 75).
- **A la puerta / placa** (solo un aparato de la puerta o de la placa: 21PCB01, 13SH1, 13MS1, 42DB1): 75 + canaleta de
  la bandeja + **curva** (100) + **canaleta de la lateral de la bisagra hasta la salida a la puerta** + puerta (1850).
  En las bases no hay bisagra elegida, así que no hay tránsito por la lateral: suben **100 mm** (la curva). Con la
  bisagra elegida en la E8 suben además lo que corre por la lateral (lo prueba `pruebas/js/wpc_regla_lateral.test.cjs`).
- **No va a la puerta ni a la placa** (zona hidráulica, batería 12PB1, solenoides SP-n, PT 001, ZY, 81TM01: sin dibujar
  o dibujados en el fondo): **como antes** (75 + canaleta de la bandeja + 1850), a confirmar con el taller. Cambia solo
  el texto del «cómo».
- Editables por producto en ⚙ Parámetros: `curva_LI`, `curva_LD`, `puerta` y `extra_puerta` (de la lateral a la
  puerta). Las acometidas de 75 quedan fijas (fuera del panel).
- Sin cambios: los pendientes LI↔LI, los cables de una lateral a la otra o de una lateral a la puerta, y los planos
  sin las laterales dibujadas.
- El 1161 del PAE: 75 + 297 + 100 + 269 + 75 = 816 → 850 (antes 900); en el PAE del usuario, 1050 (antes 1100). El
  `.wpc` real del PAE (fixture) se armó con la regla vieja: con la nueva cambia solo la columna 7 de los cables que salen
  a una lateral o a la puerta, y con sus largos puestos a mano el XML sigue IDÉNTICO byte a byte.

| Trabajo | Filas | Cambian de largo | Cambia solo el texto | Metros en el CSV (antes → después) | Por tipo |
|---|---:|---:|---:|---|---|
| 75287 | 126 | 43 | 11 | 148.60 → 151.00 (+2.40) | a la puerta / placa: 33, muere en LI: 10 |
| 66817 | 86 | 30 | 7 | 115.15 → 116.85 (+1.70) | a la puerta / placa: 22, muere en LD: 4, muere en LI: 4 |
| 76884 | 190 | 53 | 0 | 166.25 → 168.95 (+2.70) | a la puerta / placa: 41, muere en LI: 12 |
| tpt | 104 | 55 | 6 | 136.20 → 135.05 (-1.15) | a la puerta / placa: 19, muere en LD: 28, muere en LI: 8 |
| tpt_constructivo | 104 | 55 | 6 | 136.95 → 136.15 (-0.80) | a la puerta / placa: 19, muere en LD: 28, muere en LI: 8 |
| pae_usuario | 190 | 53 | 0 | 175.45 → 178.15 (+2.70) | a la puerta / placa: 41, muere en LI: 12 |

### 75287

| Cable | Origen → destino | Fuera | Antes | Después | Diferencia | Cómo (después) |
|---|---|---|---:|---:|---:|---|
| 1110 | 11PS1 1 (-) → LI |  | 850 | 800 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 298 + curva a LI 100 + canaleta de la bandeja lateral izquierda 203 + 75 (canaleta → 12XPS 2 ABAJO), redondeado a 50 |
| 1111 | 11PS1 3 (+) → LI |  | 850 | 800 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 310 + curva a LI 100 + canaleta de la bandeja lateral izquierda 209 + 75 (canaleta → 12XPS 1 ABAJO), redondeado a 50 |
| 1105 | 11Q1 N ARRIBA → LI |  | 1100 | 1050 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 549 + curva a LI 100 + canaleta de la bandeja lateral izquierda 205 + 75 (canaleta → 11MS1 ARRIBA), redondeado a 50 |
| 1104 | 11Q1 F ARRIBA → LI |  | 1100 | 1050 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 567 + curva a LI 100 + canaleta de la bandeja lateral izquierda 205 + 75 (canaleta → 11MS1 ARRIBA), redondeado a 50 |
| 1201 | 12F1 ARRIBA → LI |  | 1050 | 1000 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 524 + curva a LI 100 + canaleta de la bandeja lateral izquierda 197 + 75 (canaleta → 12XPS 3 ABAJO), redondeado a 50 |
| 1206 | 13F3 ARRIBA → LI |  | 1100 | 1000 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 541 + curva a LI 100 + canaleta de la bandeja lateral izquierda 185 + 75 (canaleta → 12XPS 5 ABAJO), redondeado a 50 |
| 2142 | 31XAI 1 ARRIBA → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 563 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 42), redondeado a 50 |
| 2118 | 43KR1 11 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 621 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 16), redondeado a 50 |
| 2122 | 43KR3 11 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 633 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 20), redondeado a 50 |
| 2168 | 46KR1 11 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 656 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 68), redondeado a 50 |
| 2114 | 46KR2 11 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 662 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 14), redondeado a 50 |
| 2119 | 43KR1 14 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 621 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 17), redondeado a 50 |
| 2123 | 43KR3 14 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 633 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 21), redondeado a 50 |
| 2169 | 46KR1 14 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 656 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 69), redondeado a 50 |
| 2115 | 46KR2 14 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 662 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 15), redondeado a 50 |
| 1301 | 13F3 ABAJO → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 341 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13SH1 ARRIBA), redondeado a 50 |
| 2151 | 62KR1 A2 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 478 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 51), redondeado a 50 |
| 2153 | 62KR2 A2 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 484 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 53), redondeado a 50 |
| 2155 | 62KR3 A2 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 490 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 55), redondeado a 50 |
| 2150 | 62KR1 A1 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 478 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 50), redondeado a 50 |
| 2152 | 62KR2 A1 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 484 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 52), redondeado a 50 |
| 2154 | 62KR3 A1 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 490 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 54), redondeado a 50 |
| 1205 | 12XP 2.1 → LI |  | 600 | 550 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 81 + curva a LI 100 + canaleta de la bandeja lateral izquierda 191 + 75 (canaleta → 12XPS 4 ABAJO), redondeado a 50 |
| 1303 | 13XC1 1.4 → LI |  | 2250 | 2350 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 301 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13SH1 ABAJO), redondeado a 50 |
| 1306 | 13XC1 2.4 → LI |  | 2250 | 2350 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 310 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 48), redondeado a 50 |
| 1203 | 13XC1 3.4 → LI |  | 850 | 750 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 320 + curva a LI 100 + canaleta de la bandeja lateral izquierda 178 + 75 (canaleta → 12XPS 6 ABAJO), redondeado a 50 |
| 1307 | 13XC1 3.3 → LI |  | 2250 | 2350 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 320 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 49), redondeado a 50 |
| 2139 | 31AIB1 3 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 340 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 39), redondeado a 50 |
| 2140 | 31AIB1 4 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 346 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 40), redondeado a 50 |
| 2105 | 31AIB1 6 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 340 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 5), redondeado a 50 |
| 2106 | 31AIB1 7 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 346 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 6), redondeado a 50 |
| 2116 | 43DIB1 5 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 359 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 18), redondeado a 50 |
| 2117 | 43DIB1 6 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 364 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 19), redondeado a 50 |
| 2120 | 43DIB2 5 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 371 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 22), redondeado a 50 |
| 2121 | 43DIB2 6 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 376 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 23), redondeado a 50 |
| 2132 | 81XCM 1 ARRIBA → LI | sí | 2400 | 2500 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 439 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 32), redondeado a 50 |
| 2132 | 81XCM 5 ARRIBA → LI | sí | 2400 | 2500 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 449 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 32), redondeado a 50 |
| 2164 | 81XCM 9 ARRIBA → LI |  | 2400 | 2500 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 460 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 64), redondeado a 50 |
| 2135 | 81XCM 11 ARRIBA → LI | sí | 1000 | 900 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 465 + curva a LI 100 + canaleta de la bandeja lateral izquierda 172 + 75 (canaleta → 12XPS 7 ABAJO), redondeado a 50 |
| 2133 | 81XCM 2 ARRIBA → LI | sí | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 574 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 33), redondeado a 50 |
| 2133 | 81XCM 6 ARRIBA → LI | sí | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 564 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 33), redondeado a 50 |
| 2165 | 81XCM 10 ARRIBA → LI |  | 2400 | 2500 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 460 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 65), redondeado a 50 |
| 2136 | 81XCM 12 ARRIBA → LI | sí | 1050 | 1000 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 549 + curva a LI 100 + canaleta de la bandeja lateral izquierda 166 + 75 (canaleta → 12XPS 8 ABAJO), redondeado a 50 |

### 66817

| Cable | Origen → destino | Fuera | Antes | Después | Diferencia | Cómo (después) |
|---|---|---|---:|---:|---:|---|
| 1216 | 12XP 4.3 → LD |  | 1100 | 1050 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 652 + curva a LD 100 + canaleta de la bandeja lateral derecha 103 + 75 (canaleta → 12CB1 -), redondeado a 50 |
| 1225 | 12F3 ABAJO → LD |  | 1050 | 1000 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 610 + curva a LD 100 + canaleta de la bandeja lateral derecha 103 + 75 (canaleta → 12CB1 +), redondeado a 50 |
| 1201 | 12F1 ARRIBA → LI |  | 950 | 850 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 271 + curva a LI 100 + canaleta de la bandeja lateral izquierda 321 + 75 (canaleta → 12PS1 +), redondeado a 50 |
| 2114 | 43KR1 11 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 338 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 14), redondeado a 50 |
| 2115 | 43KR1 12 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 338 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 15), redondeado a 50 |
| 2142 | 31XAI 1 ARRIBA → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 376 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 42), redondeado a 50 |
| 2139 | 31XAI 2 ARRIBA → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 384 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 39), redondeado a 50 |
| 1202 | 12XP 4.1 → LI |  | 1100 | 1050 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 427 + curva a LI 100 + canaleta de la bandeja lateral izquierda 329 + 75 (canaleta → 12PS1 -), redondeado a 50 |
| 2151 | 61KR1 A2 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 505 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 51), redondeado a 50 |
| 2153 | 61KR2 A2 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 511 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 53), redondeado a 50 |
| 2161 | 61KR3 A2 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 517 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 61), redondeado a 50 |
| 4306 | 43KR1 A2 → LD |  | 1050 | 1000 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 563 + curva a LD 100 + canaleta de la bandeja lateral derecha 144 + 75 (canaleta → 43XDI 2 ARRIBA), redondeado a 50 |
| 2150 | 61KR1 A1 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 505 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 50), redondeado a 50 |
| 2152 | 61KR2 A1 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 511 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 52), redondeado a 50 |
| 2160 | 61KR3 A1 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 517 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 60), redondeado a 50 |
| 4305 | 43KR1 A1 → LD |  | 1050 | 1000 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 563 + curva a LD 100 + canaleta de la bandeja lateral derecha 139 + 75 (canaleta → 43XDI 1 ARRIBA), redondeado a 50 |
| 1204 | 12XP 1.4 → LI |  | 1050 | 1000 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 598 + curva a LI 100 + canaleta de la bandeja lateral izquierda 116 + 75 (canaleta → 12PB1 +), redondeado a 50 |
| 1205 | 12XP 4.4 → LI |  | 1300 | 1200 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 622 + curva a LI 100 + canaleta de la bandeja lateral izquierda 317 + 75 (canaleta → 12PB1 -), redondeado a 50 |
| 1301 | 13XC1 1.4 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 643 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13SH1 ARRIBA), redondeado a 50 |
| 1303 | 13XC1 2.4 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 653 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13SH1 ABAJO), redondeado a 50 |
| 1402 | 13XC1 3.4 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 671 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 49), redondeado a 50 |
| 1401 | 13XC1 2.3 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 653 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 48), redondeado a 50 |
| 2105 | 32AIB1 3 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 610 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 5), redondeado a 50 |
| 2106 | 32AIB1 4 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 606 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 6), redondeado a 50 |
| 2118 | 43DIB1 3 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 585 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 18), redondeado a 50 |
| 2119 | 43DIB1 4 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 580 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 19), redondeado a 50 |
| 2102 | 32AIB1 6 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 610 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 2), redondeado a 50 |
| 2103 | 32AIB1 7 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 606 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 3), redondeado a 50 |
| 2116 | 43DIB1 5 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 585 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 16), redondeado a 50 |
| 2117 | 43DIB1 6 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 580 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 17), redondeado a 50 |

### 76884

| Cable | Origen → destino | Fuera | Antes | Después | Diferencia | Cómo (después) |
|---|---|---|---:|---:|---:|---|
| 1161 | 11PS1 TB2 1 (-V) → LI |  | 900 | 850 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 297 + curva a LI 100 + canaleta de la bandeja lateral izquierda 269 + 75 (canaleta → 12XPS 4 ABAJO), redondeado a 50 |
| 1201 | 12F3 ARRIBA → LI |  | 1100 | 1050 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 492 + curva a LI 100 + canaleta de la bandeja lateral izquierda 260 + 75 (canaleta → 12XPS 5 ABAJO), redondeado a 50 |
| 1230 | 13F4 ARRIBA → LI |  | 1100 | 1000 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 514 + curva a LI 100 + canaleta de la bandeja lateral izquierda 236 + 75 (canaleta → 12XPS 8 ABAJO), redondeado a 50 |
| 1232 | 13F5 ARRIBA → LI |  | 1100 | 1050 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 531 + curva a LI 100 + canaleta de la bandeja lateral izquierda 244 + 75 (canaleta → 12XPS 7 ABAJO), redondeado a 50 |
| 4211 | 42KS1 S11 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 586 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (42DB1 1), redondeado a 50 |
| 4212 | 42KR1 14 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 602 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (42DB1 2), redondeado a 50 |
| 2142 | 32XAI 1 ARRIBA → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 652 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 42), redondeado a 50 |
| 1186 | 11PS1 TB1 2 (N) → LI |  | 550 | 450 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 102 + curva a LI 100 + canaleta de la bandeja lateral izquierda 75 + 75 (canaleta → 11X220V 2.1), redondeado a 50 |
| 1185 | 11PS1 TB1 3 (L) → LI |  | 750 | 650 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 300 + curva a LI 100 + canaleta de la bandeja lateral izquierda 83 + 75 (canaleta → 11X220V 1.1), redondeado a 50 |
| 1184 | 11PS2 TB1 2 (N) → LI |  | 600 | 500 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 165 + curva a LI 100 + canaleta de la bandeja lateral izquierda 75 + 75 (canaleta → 11X220V 2.2), redondeado a 50 |
| 1183 | 11PS2 TB1 3 (L) → LI |  | 800 | 700 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 363 + curva a LI 100 + canaleta de la bandeja lateral izquierda 83 + 75 (canaleta → 11X220V 1.2), redondeado a 50 |
| 1162 | 11F1 ABAJO → LI |  | 850 | 800 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 243 + curva a LI 100 + canaleta de la bandeja lateral izquierda 277 + 75 (canaleta → 12XPS 3 ABAJO), redondeado a 50 |
| 1301 | 13F4 ABAJO → LI |  | 2250 | 2350 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 304 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13MS1 1/L1), redondeado a 50 |
| 1302 | 13F5 ABAJO → LI |  | 2250 | 2350 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 321 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13MS1 3/L2), redondeado a 50 |
| 2114 | 42KS1 13 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 371 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 14), redondeado a 50 |
| 2115 | 42KS1 14 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 376 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 15), redondeado a 50 |
| 2151 | 61KR1 A2 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 408 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 51), redondeado a 50 |
| 2153 | 61KR2 A2 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 414 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 53), redondeado a 50 |
| 2155 | 61KR3 A2 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 420 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 55), redondeado a 50 |
| 2157 | 61KR4 A2 → LI |  | 2400 | 2500 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 426 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 57), redondeado a 50 |
| 2150 | 61KR1 A1 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 408 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 50), redondeado a 50 |
| 2152 | 61KR2 A1 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 414 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 52), redondeado a 50 |
| 2154 | 61KR3 A1 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 420 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 54), redondeado a 50 |
| 2156 | 61KR4 A1 → LI |  | 2400 | 2500 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 426 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 56), redondeado a 50 |
| 1231 | 12XP 1.1 → LI |  | 650 | 550 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 70 + curva a LI 100 + canaleta de la bandeja lateral izquierda 228 + 75 (canaleta → 12XPS 9 ABAJO), redondeado a 50 |
| 1303 | 13X12V 1.1 → LI |  | 2050 | 2150 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 107 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13MS1 2/T1), redondeado a 50 |
| 1304 | 13X12V 2.1 → LI |  | 2050 | 2150 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 115 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13MS1 4/T2), redondeado a 50 |
| 1353 | 13X12V 1.2 → LI |  | 2050 | 2150 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 107 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 48), redondeado a 50 |
| 1254 | 12XP 1.4 → LI |  | 2200 | 2300 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 260 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 49), redondeado a 50 |
| 2139 | 15AIB1 3 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 350 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 39), redondeado a 50 |
| 2140 | 15AIB1 4 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 355 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 40), redondeado a 50 |
| 2118 | 15DIB1 3 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 368 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 18), redondeado a 50 |
| 2119 | 15DIB1 4 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 373 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 19), redondeado a 50 |
| 2122 | 15DIB2 3 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 380 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 22), redondeado a 50 |
| 2123 | 15DIB2 4 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 385 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 23), redondeado a 50 |
| 2126 | 15DIB3 3 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 393 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 26), redondeado a 50 |
| 2127 | 15DIB3 4 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 398 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 27), redondeado a 50 |
| 2105 | 15AIB1 6 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 350 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 5), redondeado a 50 |
| 2106 | 15AIB1 7 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 355 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 6), redondeado a 50 |
| 2116 | 15DIB1 5 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 368 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 16), redondeado a 50 |
| 2117 | 15DIB1 6 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 373 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 17), redondeado a 50 |
| 2120 | 15DIB2 5 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 380 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 20), redondeado a 50 |
| 2121 | 15DIB2 6 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 385 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 21), redondeado a 50 |
| 2124 | 15DIB3 5 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 393 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 24), redondeado a 50 |
| 2125 | 15DIB3 6 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 398 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 25), redondeado a 50 |
| 2132 | 81XCM 1 ARRIBA → LI | sí | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 401 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 32), redondeado a 50 |
| 2132 | 81XCM 5 ARRIBA → LI | sí | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 412 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 32), redondeado a 50 |
| MALLA 21PCB01 34 (2) | 81XCM 3 ARRIBA → LI | sí | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 407 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 34), redondeado a 50 |
| 2135 | 81XCM 7 ARRIBA → LI | sí | 1000 | 900 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 + canaleta de la bandeja lateral izquierda 220 + 75 (canaleta → 12XPS 10 ABAJO), redondeado a 50 |
| 2133 | 81XCM 2 ARRIBA → LI | sí | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 401 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 33), redondeado a 50 |
| 2133 | 81XCM 6 ARRIBA → LI | sí | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 412 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 33), redondeado a 50 |
| MALLA 21PCB01 34 | 81XCM 4 ARRIBA → LI | sí | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 407 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 34), redondeado a 50 |
| 2136 | 81XCM 8 ARRIBA → LI | sí | 1000 | 900 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 + canaleta de la bandeja lateral izquierda 212 + 75 (canaleta → 12XPS 11 ABAJO), redondeado a 50 |

### tpt

| Cable | Origen → destino | Fuera | Antes | Después | Diferencia | Cómo (después) |
|---|---|---|---:|---:|---:|---|
| 1104 | 11Q1 F ARRIBA → LD |  | 1600 | 1550 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 668 + curva a LD 100 + canaleta de la bandeja lateral derecha 604 + 75 (canaleta → 11XP 1 ABAJO), redondeado a 50 |
| 1105 | 11Q1 N ARRIBA → LD |  | 1600 | 1500 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 650 + curva a LD 100 + canaleta de la bandeja lateral derecha 596 + 75 (canaleta → 11XP 2 ABAJO), redondeado a 50 |
| 1109 | 11PS1 - → LI |  | 750 | 700 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 87 + curva a LI 100 + canaleta de la bandeja lateral izquierda 326 + 75 (canaleta → 12PS2 -), redondeado a 50 |
| 1108 | 11PS1 + → LI |  | 800 | 700 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 99 + curva a LI 100 + canaleta de la bandeja lateral izquierda 333 + 75 (canaleta → 12PS2 +), redondeado a 50 |
| 1312 | 13PS3 -Vo → LD |  | 850 | 750 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 371 + curva a LD 100 + canaleta de la bandeja lateral derecha 108 + 75 (canaleta → 13XC2 2.1), redondeado a 50 |
| 1311 | 13PS3 +Vo → LD |  | 800 | 750 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 361 + curva a LD 100 + canaleta de la bandeja lateral derecha 98 + 75 (canaleta → 13XC2 1.1), redondeado a 50 |
| 8105 | 33MX01 D1+ → LI |  | 850 | 800 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 176 + curva a LI 100 + canaleta de la bandeja lateral izquierda 327 + 75 (canaleta → EMPALME con 12PS2), redondeado a 50 |
| 8106 | 33MX01 D1- → LI |  | 1200 | 1100 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 503 + curva a LI 100 + canaleta de la bandeja lateral izquierda 333 + 75 (canaleta → EMPALME con 12PS2), redondeado a 50 |
| 1315 | 33MX01 V+ → LD |  | 1200 | 1100 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 338 + curva a LD 100 + canaleta de la bandeja lateral derecha 493 + 75 (canaleta → 13XC2 1.4), redondeado a 50 |
| 1316 | 33MX01 V- → LD |  | 1150 | 1100 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 338 + curva a LD 100 + canaleta de la bandeja lateral derecha 482 + 75 (canaleta → 13XC2 2.4), redondeado a 50 |
| 3301 | 33MX01 1 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 352 + curva a LD 100 + canaleta de la bandeja lateral derecha 533 + 75 (canaleta → 33XAI 1 ARRIBA), redondeado a 50 |
| 1602 | 33MX01 2 → LD |  | 1150 | 1100 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 355 + curva a LD 100 + canaleta de la bandeja lateral derecha 463 + 75 (canaleta → 16XC 2 ABAJO), redondeado a 50 |
| 3303 | 33MX01 3 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 359 + curva a LD 100 + canaleta de la bandeja lateral derecha 527 + 75 (canaleta → 33XAI 2 ARRIBA), redondeado a 50 |
| 1604 | 33MX01 4 → LD |  | 850 | 750 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 363 + curva a LD 100 + canaleta de la bandeja lateral derecha 133 + 75 (canaleta → 16XC 4 ARRIBA), redondeado a 50 |
| 3305 | 33MX01 5 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 367 + curva a LD 100 + canaleta de la bandeja lateral derecha 521 + 75 (canaleta → 33XAI 3 ARRIBA), redondeado a 50 |
| 1606 | 33MX01 6 → LD |  | 1200 | 1100 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 371 + curva a LD 100 + canaleta de la bandeja lateral derecha 458 + 75 (canaleta → 16XC 4 ABAJO), redondeado a 50 |
| 3307 | 33MX01 7 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 374 + curva a LD 100 + canaleta de la bandeja lateral derecha 515 + 75 (canaleta → 33XAI 4 ARRIBA), redondeado a 50 |
| 1608 | 33MX01 8 → LD |  | 850 | 800 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 378 + curva a LD 100 + canaleta de la bandeja lateral derecha 138 + 75 (canaleta → 16XC 6 ARRIBA), redondeado a 50 |
| 3309 | 33MX01 9 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 382 + curva a LD 100 + canaleta de la bandeja lateral derecha 509 + 75 (canaleta → 33XAI 5 ARRIBA), redondeado a 50 |
| 1610 | 33MX01 10 → LD |  | 1200 | 1100 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 386 + curva a LD 100 + canaleta de la bandeja lateral derecha 453 + 75 (canaleta → 16XC 6 ABAJO), redondeado a 50 |
| 3311 | 33MX01 11 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 390 + curva a LD 100 + canaleta de la bandeja lateral derecha 503 + 75 (canaleta → 33XAI 6 ARRIBA), redondeado a 50 |
| 1612 | 33MX01 12 → LD |  | 900 | 800 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 394 + curva a LD 100 + canaleta de la bandeja lateral derecha 143 + 75 (canaleta → 16XC 8 ARRIBA), redondeado a 50 |
| 3313 | 33MX01 13 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 398 + curva a LD 100 + canaleta de la bandeja lateral derecha 497 + 75 (canaleta → 33XAI 7 ARRIBA), redondeado a 50 |
| 1614 | 33MX01 14 → LD |  | 1200 | 1100 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 402 + curva a LD 100 + canaleta de la bandeja lateral derecha 448 + 75 (canaleta → 16XC 8 ABAJO), redondeado a 50 |
| 3315 | 33MX01 15 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 406 + curva a LD 100 + canaleta de la bandeja lateral derecha 491 + 75 (canaleta → 33XAI 8 ARRIBA), redondeado a 50 |
| 1616 | 33MX01 16 → LD |  | 900 | 850 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 410 + curva a LD 100 + canaleta de la bandeja lateral derecha 148 + 75 (canaleta → 16XC 10 ARRIBA), redondeado a 50 |
| 1201 | 12F1 ARRIBA → LI |  | 950 | 900 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 281 + curva a LI 100 + canaleta de la bandeja lateral izquierda 320 + 75 (canaleta → 12PS2 +), redondeado a 50 |
| 8101 | 61KR3 11 → LD |  | 1000 | 900 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 182 + curva a LD 100 + canaleta de la bandeja lateral derecha 452 + 75 (canaleta → 81XCM 3 ARRIBA), redondeado a 50 |
| 2114 | 43KR1 11 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 348 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 14), redondeado a 50 |
| 8102 | 61KR3 12 → LD |  | 1000 | 900 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 182 + curva a LD 100 + canaleta de la bandeja lateral derecha 452 + 75 (canaleta → 81XCM 4 ARRIBA), redondeado a 50 |
| 2115 | 43KR1 12 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 348 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 15), redondeado a 50 |
| 2142 | 31XAI 1 ARRIBA → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 388 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 42), redondeado a 50 |
| 1617 | 31XAI F1 ARRIBA → LD |  | 900 | 850 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 126 + curva a LD 100 + canaleta de la bandeja lateral derecha 443 + 75 (canaleta → 16XC 9 ABAJO), redondeado a 50 |
| 1202 | 12XP 2.1 → LI |  | 1100 | 1000 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 + canaleta de la bandeja lateral izquierda 320 + 75 (canaleta → 12PS2 -), redondeado a 50 |
| 2112 | 12XP 2.2 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 12), redondeado a 50 |
| 2151 | 61KR1 A2 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 515 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 51), redondeado a 50 |
| 2153 | 61KR2 A2 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 521 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 53), redondeado a 50 |
| 2155 | 61KR3 A2 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 527 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 55), redondeado a 50 |
| 4306 | 43KR1 A2 → LD |  | 1400 | 1300 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 573 + curva a LD 100 + canaleta de la bandeja lateral derecha 473 + 75 (canaleta → 43XDI 2 ARRIBA), redondeado a 50 |
| 2150 | 61KR1 A1 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 515 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 50), redondeado a 50 |
| 2152 | 61KR2 A1 → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 521 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 52), redondeado a 50 |
| 2154 | 61KR3 A1 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 527 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 54), redondeado a 50 |
| 4305 | 43KR1 A1 → LD |  | 1400 | 1300 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 573 + curva a LD 100 + canaleta de la bandeja lateral derecha 473 + 75 (canaleta → 43XDI 1 ARRIBA), redondeado a 50 |
| 1204 | 12XP 1.4 → LI |  | 1050 | 1000 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 602 + curva a LI 100 + canaleta de la bandeja lateral izquierda 116 + 75 (canaleta → 12PB1 +), redondeado a 50 |
| 1206 | 12XP 2.4 → LI |  | 1300 | 1200 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 612 + curva a LI 100 + canaleta de la bandeja lateral izquierda 317 + 75 (canaleta → 12PB1 -), redondeado a 50 |
| 2111 | 12XP 1.3 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 602 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 11), redondeado a 50 |
| 1302 | 13XC1 1.4 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 632 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13SH1 ARRIBA), redondeado a 50 |
| 1303 | 13XC1 2.4 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 643 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13SH1 ABAJO), redondeado a 50 |
| 1307 | 13XC1 3.4 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 653 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 49), redondeado a 50 |
| 1306 | 13XC1 2.3 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 643 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 48), redondeado a 50 |
| 1319 | 13XC1 3.3 → LD |  | 1150 | 1050 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 683 + curva a LD 100 + canaleta de la bandeja lateral derecha 108 + 75 (canaleta → 13XC2 2.2), redondeado a 50 |
| 2116 | 43DIB1 3 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 591 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 16), redondeado a 50 |
| 2117 | 43DIB1 4 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 586 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 17), redondeado a 50 |
| 2118 | 43DIB1 5 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 591 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 18), redondeado a 50 |
| 2119 | 43DIB1 6 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 586 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 19), redondeado a 50 |

### tpt_constructivo

| Cable | Origen → destino | Fuera | Antes | Después | Diferencia | Cómo (después) |
|---|---|---|---:|---:|---:|---|
| 1104 | 11Q1 F ARRIBA → LD |  | 1650 | 1550 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 688 + curva a LD 100 + canaleta de la bandeja lateral derecha 604 + 75 (canaleta → 11XP 1 ABAJO), redondeado a 50 |
| 1105 | 11Q1 N ARRIBA → LD |  | 1600 | 1550 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 670 + curva a LD 100 + canaleta de la bandeja lateral derecha 596 + 75 (canaleta → 11XP 2 ABAJO), redondeado a 50 |
| 1109 | 11PS1 - → LI |  | 750 | 700 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 87 + curva a LI 100 + canaleta de la bandeja lateral izquierda 326 + 75 (canaleta → 12PS2 -), redondeado a 50 |
| 1108 | 11PS1 + → LI |  | 800 | 700 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 99 + curva a LI 100 + canaleta de la bandeja lateral izquierda 333 + 75 (canaleta → 12PS2 +), redondeado a 50 |
| 1312 | 13PS3 -Vo → LD |  | 850 | 750 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 371 + curva a LD 100 + canaleta de la bandeja lateral derecha 108 + 75 (canaleta → 13XC2 2.1), redondeado a 50 |
| 1311 | 13PS3 +Vo → LD |  | 800 | 750 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 361 + curva a LD 100 + canaleta de la bandeja lateral derecha 98 + 75 (canaleta → 13XC2 1.1), redondeado a 50 |
| 8105 | 33MX01 D1+ → LI |  | 850 | 800 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 176 + curva a LI 100 + canaleta de la bandeja lateral izquierda 327 + 75 (canaleta → EMPALME con 12PS2), redondeado a 50 |
| 8106 | 33MX01 D1- → LI |  | 1200 | 1150 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 523 + curva a LI 100 + canaleta de la bandeja lateral izquierda 333 + 75 (canaleta → EMPALME con 12PS2), redondeado a 50 |
| 1315 | 33MX01 V+ → LD |  | 1200 | 1100 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 338 + curva a LD 100 + canaleta de la bandeja lateral derecha 493 + 75 (canaleta → 13XC2 1.4), redondeado a 50 |
| 1316 | 33MX01 V- → LD |  | 1150 | 1100 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 338 + curva a LD 100 + canaleta de la bandeja lateral derecha 482 + 75 (canaleta → 13XC2 2.4), redondeado a 50 |
| 3301 | 33MX01 1 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 358 + curva a LD 100 + canaleta de la bandeja lateral derecha 533 + 75 (canaleta → 33XAI 1 ARRIBA), redondeado a 50 |
| 1602 | 33MX01 2 → LD |  | 1150 | 1100 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 362 + curva a LD 100 + canaleta de la bandeja lateral derecha 463 + 75 (canaleta → 16XC 2 ABAJO), redondeado a 50 |
| 3303 | 33MX01 3 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 365 + curva a LD 100 + canaleta de la bandeja lateral derecha 527 + 75 (canaleta → 33XAI 2 ARRIBA), redondeado a 50 |
| 1604 | 33MX01 4 → LD |  | 850 | 800 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 369 + curva a LD 100 + canaleta de la bandeja lateral derecha 133 + 75 (canaleta → 16XC 4 ARRIBA), redondeado a 50 |
| 3305 | 33MX01 5 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 373 + curva a LD 100 + canaleta de la bandeja lateral derecha 521 + 75 (canaleta → 33XAI 3 ARRIBA), redondeado a 50 |
| 1606 | 33MX01 6 → LD |  | 1200 | 1100 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 377 + curva a LD 100 + canaleta de la bandeja lateral derecha 458 + 75 (canaleta → 16XC 4 ABAJO), redondeado a 50 |
| 3307 | 33MX01 7 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 381 + curva a LD 100 + canaleta de la bandeja lateral derecha 515 + 75 (canaleta → 33XAI 4 ARRIBA), redondeado a 50 |
| 1608 | 33MX01 8 → LD |  | 850 | 800 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 385 + curva a LD 100 + canaleta de la bandeja lateral derecha 138 + 75 (canaleta → 16XC 6 ARRIBA), redondeado a 50 |
| 3309 | 33MX01 9 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 388 + curva a LD 100 + canaleta de la bandeja lateral derecha 509 + 75 (canaleta → 33XAI 5 ARRIBA), redondeado a 50 |
| 1610 | 33MX01 10 → LD |  | 1200 | 1100 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 392 + curva a LD 100 + canaleta de la bandeja lateral derecha 453 + 75 (canaleta → 16XC 6 ABAJO), redondeado a 50 |
| 3311 | 33MX01 11 → LD |  | 1250 | 1150 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 396 + curva a LD 100 + canaleta de la bandeja lateral derecha 503 + 75 (canaleta → 33XAI 6 ARRIBA), redondeado a 50 |
| 1612 | 33MX01 12 → LD |  | 900 | 800 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 400 + curva a LD 100 + canaleta de la bandeja lateral derecha 143 + 75 (canaleta → 16XC 8 ARRIBA), redondeado a 50 |
| 3313 | 33MX01 13 → LD |  | 1250 | 1200 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 405 + curva a LD 100 + canaleta de la bandeja lateral derecha 497 + 75 (canaleta → 33XAI 7 ARRIBA), redondeado a 50 |
| 1614 | 33MX01 14 → LD |  | 1200 | 1150 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 409 + curva a LD 100 + canaleta de la bandeja lateral derecha 448 + 75 (canaleta → 16XC 8 ABAJO), redondeado a 50 |
| 3315 | 33MX01 15 → LD |  | 1250 | 1200 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 412 + curva a LD 100 + canaleta de la bandeja lateral derecha 491 + 75 (canaleta → 33XAI 8 ARRIBA), redondeado a 50 |
| 1616 | 33MX01 16 → LD |  | 900 | 850 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 416 + curva a LD 100 + canaleta de la bandeja lateral derecha 148 + 75 (canaleta → 16XC 10 ARRIBA), redondeado a 50 |
| 1201 | 12F1 ARRIBA → LI |  | 950 | 900 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 281 + curva a LI 100 + canaleta de la bandeja lateral izquierda 320 + 75 (canaleta → 12PS2 +), redondeado a 50 |
| 8101 | 61KR3 11 → LD |  | 1000 | 900 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 182 + curva a LD 100 + canaleta de la bandeja lateral derecha 452 + 75 (canaleta → 81XCM 3 ARRIBA), redondeado a 50 |
| 2114 | 43KR1 11 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 348 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 14), redondeado a 50 |
| 8102 | 61KR3 12 → LD |  | 1000 | 900 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 182 + curva a LD 100 + canaleta de la bandeja lateral derecha 452 + 75 (canaleta → 81XCM 4 ARRIBA), redondeado a 50 |
| 2115 | 43KR1 12 → LI |  | 2300 | 2400 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 348 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 15), redondeado a 50 |
| 2142 | 31XAI 1 ARRIBA → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 388 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 42), redondeado a 50 |
| 1617 | 31XAI F1 ARRIBA → LD |  | 900 | 850 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 126 + curva a LD 100 + canaleta de la bandeja lateral derecha 443 + 75 (canaleta → 16XC 9 ABAJO), redondeado a 50 |
| 1202 | 12XP 2.1 → LI |  | 1100 | 1000 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 + canaleta de la bandeja lateral izquierda 320 + 75 (canaleta → 12PS2 -), redondeado a 50 |
| 2112 | 12XP 2.2 → LI |  | 2350 | 2450 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 12), redondeado a 50 |
| 2151 | 61KR1 A2 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 535 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 51), redondeado a 50 |
| 2153 | 61KR2 A2 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 541 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 53), redondeado a 50 |
| 2155 | 61KR3 A2 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 547 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 55), redondeado a 50 |
| 4306 | 43KR1 A2 → LD |  | 1400 | 1350 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 593 + curva a LD 100 + canaleta de la bandeja lateral derecha 473 + 75 (canaleta → 43XDI 2 ARRIBA), redondeado a 50 |
| 2150 | 61KR1 A1 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 535 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 50), redondeado a 50 |
| 2152 | 61KR2 A1 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 541 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 52), redondeado a 50 |
| 2154 | 61KR3 A1 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 547 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 54), redondeado a 50 |
| 4305 | 43KR1 A1 → LD |  | 1400 | 1350 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 593 + curva a LD 100 + canaleta de la bandeja lateral derecha 473 + 75 (canaleta → 43XDI 1 ARRIBA), redondeado a 50 |
| 1204 | 12XP 1.4 → LI |  | 1100 | 1000 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 622 + curva a LI 100 + canaleta de la bandeja lateral izquierda 116 + 75 (canaleta → 12PB1 +), redondeado a 50 |
| 1206 | 12XP 2.4 → LI |  | 1300 | 1200 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 632 + curva a LI 100 + canaleta de la bandeja lateral izquierda 317 + 75 (canaleta → 12PB1 -), redondeado a 50 |
| 2111 | 12XP 1.3 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 622 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 11), redondeado a 50 |
| 1302 | 13XC1 1.4 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 652 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13SH1 ARRIBA), redondeado a 50 |
| 1303 | 13XC1 2.4 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 663 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13SH1 ABAJO), redondeado a 50 |
| 1307 | 13XC1 3.4 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 673 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 49), redondeado a 50 |
| 1306 | 13XC1 2.3 → LI |  | 2600 | 2700 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 663 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 48), redondeado a 50 |
| 1319 | 13XC1 3.3 → LD |  | 1150 | 1100 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 703 + curva a LD 100 + canaleta de la bandeja lateral derecha 108 + 75 (canaleta → 13XC2 2.2), redondeado a 50 |
| 2116 | 43DIB1 3 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 611 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 16), redondeado a 50 |
| 2117 | 43DIB1 4 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 606 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 17), redondeado a 50 |
| 2118 | 43DIB1 5 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 611 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 18), redondeado a 50 |
| 2119 | 43DIB1 6 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 606 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 19), redondeado a 50 |

### pae_usuario

| Cable | Origen → destino | Fuera | Antes | Después | Diferencia | Cómo (después) |
|---|---|---|---:|---:|---:|---|
| 1161 | 11PS1 TB2 1 (-V) → LI |  | 1100 | 1050 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 490 + curva a LI 100 + canaleta de la bandeja lateral izquierda 269 + 75 (canaleta → 12XPS 4 ABAJO), redondeado a 50 |
| 1201 | 12F3 ARRIBA → LI |  | 1300 | 1200 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 686 + curva a LI 100 + canaleta de la bandeja lateral izquierda 261 + 75 (canaleta → 12XPS 5 ABAJO), redondeado a 50 |
| 1230 | 13F4 ARRIBA → LI |  | 1300 | 1200 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 707 + curva a LI 100 + canaleta de la bandeja lateral izquierda 236 + 75 (canaleta → 12XPS 8 ABAJO), redondeado a 50 |
| 1232 | 13F5 ARRIBA → LI |  | 1300 | 1250 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 725 + curva a LI 100 + canaleta de la bandeja lateral izquierda 244 + 75 (canaleta → 12XPS 7 ABAJO), redondeado a 50 |
| 4211 | 42KS1 S11 → LI |  | 2750 | 2850 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 779 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (42DB1 1), redondeado a 50 |
| 4212 | 42KR1 14 → LI |  | 2750 | 2850 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 796 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (42DB1 2), redondeado a 50 |
| 2142 | 32XAI 1 ARRIBA → LI |  | 2800 | 2900 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 845 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 42), redondeado a 50 |
| 1186 | 11PS1 TB1 2 (N) → LI |  | 700 | 650 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 295 + curva a LI 100 + canaleta de la bandeja lateral izquierda 75 + 75 (canaleta → 11X220V 2.1), redondeado a 50 |
| 1185 | 11PS1 TB1 3 (L) → LI |  | 750 | 650 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 303 + curva a LI 100 + canaleta de la bandeja lateral izquierda 83 + 75 (canaleta → 11X220V 1.1), redondeado a 50 |
| 1184 | 11PS2 TB1 2 (N) → LI |  | 800 | 700 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 358 + curva a LI 100 + canaleta de la bandeja lateral izquierda 75 + 75 (canaleta → 11X220V 2.2), redondeado a 50 |
| 1183 | 11PS2 TB1 3 (L) → LI |  | 800 | 700 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 366 + curva a LI 100 + canaleta de la bandeja lateral izquierda 83 + 75 (canaleta → 11X220V 1.2), redondeado a 50 |
| 1162 | 11F1 ABAJO → LI |  | 1050 | 1000 | -50 | 75 (borne → canaleta) + canaleta de la bandeja 436 + curva a LI 100 + canaleta de la bandeja lateral izquierda 277 + 75 (canaleta → 12XPS 3 ABAJO), redondeado a 50 |
| 1301 | 13F4 ABAJO → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 497 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13MS1 1/L1), redondeado a 50 |
| 1302 | 13F5 ABAJO → LI |  | 2450 | 2550 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 515 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13MS1 3/L2), redondeado a 50 |
| 2114 | 42KS1 13 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 564 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 14), redondeado a 50 |
| 2115 | 42KS1 14 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 569 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 15), redondeado a 50 |
| 2151 | 61KR1 A2 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 601 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 51), redondeado a 50 |
| 2153 | 61KR2 A2 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 607 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 53), redondeado a 50 |
| 2155 | 61KR3 A2 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 613 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 55), redondeado a 50 |
| 2157 | 61KR4 A2 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 619 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 57), redondeado a 50 |
| 2150 | 61KR1 A1 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 601 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 50), redondeado a 50 |
| 2152 | 61KR2 A1 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 607 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 52), redondeado a 50 |
| 2154 | 61KR3 A1 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 613 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 54), redondeado a 50 |
| 2156 | 61KR4 A1 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 619 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 56), redondeado a 50 |
| 1231 | 12XP 1.1 → LI |  | 850 | 750 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 264 + curva a LI 100 + canaleta de la bandeja lateral izquierda 228 + 75 (canaleta → 12XPS 9 ABAJO), redondeado a 50 |
| 1303 | 13X12V 1.1 → LI |  | 2250 | 2350 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 300 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13MS1 2/T1), redondeado a 50 |
| 1304 | 13X12V 2.1 → LI |  | 2250 | 2350 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 308 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (13MS1 4/T2), redondeado a 50 |
| 1353 | 13X12V 1.2 → LI |  | 2250 | 2350 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 300 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 48), redondeado a 50 |
| 1254 | 12XP 1.4 → LI |  | 2000 | 2100 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 74 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 49), redondeado a 50 |
| 2139 | 15AIB1 3 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 543 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 39), redondeado a 50 |
| 2140 | 15AIB1 4 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 548 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 40), redondeado a 50 |
| 2118 | 15DIB1 3 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 561 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 18), redondeado a 50 |
| 2119 | 15DIB1 4 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 566 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 19), redondeado a 50 |
| 2122 | 15DIB2 3 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 573 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 22), redondeado a 50 |
| 2123 | 15DIB2 4 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 579 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 23), redondeado a 50 |
| 2126 | 15DIB3 3 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 586 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 26), redondeado a 50 |
| 2127 | 15DIB3 4 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 591 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 27), redondeado a 50 |
| 2105 | 15AIB1 6 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 543 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 5), redondeado a 50 |
| 2106 | 15AIB1 7 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 548 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 6), redondeado a 50 |
| 2116 | 15DIB1 5 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 561 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 16), redondeado a 50 |
| 2117 | 15DIB1 6 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 566 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 17), redondeado a 50 |
| 2120 | 15DIB2 5 → LI |  | 2500 | 2600 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 573 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 20), redondeado a 50 |
| 2121 | 15DIB2 6 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 579 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 21), redondeado a 50 |
| 2124 | 15DIB3 5 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 586 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 24), redondeado a 50 |
| 2125 | 15DIB3 6 → LI |  | 2550 | 2650 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 591 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 25), redondeado a 50 |
| 2132 | 81XCM 1 ARRIBA → LI | sí | 2150 | 2250 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 215 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 32), redondeado a 50 |
| 2132 | 81XCM 5 ARRIBA → LI | sí | 2150 | 2250 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 225 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 32), redondeado a 50 |
| MALLA 21PCB01 34 (2) | 81XCM 3 ARRIBA → LI | sí | 2150 | 2250 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 220 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 34), redondeado a 50 |
| 2135 | 81XCM 7 ARRIBA → LI | sí | 800 | 700 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 230 + curva a LI 100 + canaleta de la bandeja lateral izquierda 220 + 75 (canaleta → 12XPS 10 ABAJO), redondeado a 50 |
| 2133 | 81XCM 2 ARRIBA → LI | sí | 2150 | 2250 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 215 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 33), redondeado a 50 |
| 2133 | 81XCM 6 ARRIBA → LI | sí | 2150 | 2250 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 225 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 33), redondeado a 50 |
| MALLA 21PCB01 34 | 81XCM 4 ARRIBA → LI | sí | 2150 | 2250 | +100 | 75 (borne → canaleta) + canaleta de la bandeja 220 + curva a LI 100 (sin el recorrido por la lateral: falta elegir la bisagra en la E8) + puerta / placa 1850 (21PCB01 34), redondeado a 50 |
| 2136 | 81XCM 8 ARRIBA → LI | sí | 800 | 700 | -100 | 75 (borne → canaleta) + canaleta de la bandeja 230 + curva a LI 100 + canaleta de la bandeja lateral izquierda 212 + 75 (canaleta → 12XPS 11 ABAJO), redondeado a 50 |
