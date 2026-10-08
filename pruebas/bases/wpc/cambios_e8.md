# Lista WPC: antes y después de la etapa E8-1 (laterales completas)

Lista WPC con «Pendientes LI↔LI» y «Otra estación» tildados (todas las filas), configuración fija de las pruebas
(`pruebas/fixtures/wpc/wpc.json`). «Largo» = el que va al CSV, en mm. «Fuera» = no va al arnés (destildado).

**Por qué cambia (etapa E8-1 «laterales completas», 2026-10-08).** La regla de la WPC no cambió (la del 2026-10-06):
lo que cambió es la estación E8, que ahora lee las bandejas laterales enteras (placa, canaletas, riel tapado por los
aparatos y la lateral sin riel). Por decisión del taller los largos nuevos se aplican directo y se regeneraron los
goldens de la WPC (`pruebas/bases/wpc/`). «Antes» = `pruebas/bases/ins_<trabajo>.json` del commit d12fa6d (en el TPT
del usuario, el instructivo armado con ese mismo código); «después» = el de hoy.

- **Cables de la bandeja a un aparato de la lateral** que antes se medían como «puerta / placa» (+1850 mm): ahora se
  miden con la fórmula de la lateral (75 + canaleta de la bandeja + 100 + canaleta de la lateral + 150). Ej. TPT: 3301 a
  33XAI (riel 2 de la LD, que antes quedaba afuera de la vista) 2300 → 1250; 1108 / 1201 al cargador 12PS2 (LI, que
  antes no existía) 2050 / 2250 → 600 / 800; 66817: 1201, 1202 (cargador), 1225, 1216 (12CB1), 4305, 4306 (43XDI).
- **Cables a la lateral que antes no tenían recorrido** (la lateral sin canaletas leídas): pasan de la fórmula «sin E8»
  (canaletas + 100 + LI 1500 / LD 400 + 200) a la de la lateral. Ej. 75287: los 10 de 12XPS y 11MS1; TPT: 1311, 1617...
- **Pendientes de la lateral** (solo con «Pendientes LI↔LI» tildado): de 2000 fijo a canaleta de la lateral + margen
  (200) + agregado (200), o + puerta / placa (1500 + 350) si el otro extremo está en la puerta (TPT: 2105, 8103, 8104).
- **Cables de una lateral a la otra** (66817: 1101, 1102, de 11XP en la LD al cargador en la LI): la WPC toma la
  canaleta de una sola de las dos laterales (la última, la LD); queda anotado como pendiente para confirmar.
- **PAE**: sin cambios (su E8 da igual).

| Trabajo | Filas antes / después | Cambian de largo | Cambia solo el texto | Metros en el CSV (antes → después) |
|---|---|---:|---:|---|
| TPT del usuario (tpt_constructivo, 72715-1) | 104 / 104 | 45 | 3 | 176.35 → 138.95 (-37.40) |
| TPT de pruebas (tpt, topográfico 72887) | 104 / 104 | 44 | 4 | 175.35 → 138.20 (-37.15) |
| 66817 | 86 / 86 | 13 | 0 | 128.60 → 114.85 (-13.75) |
| 75287 | 126 / 126 | 14 | 0 | 161.95 → 148.70 (-13.25) |
| PAE (76884) | 190 / 190 | 0 | 0 | 168.05 → 168.05 (+0.00) |

## TPT del usuario (tpt_constructivo, 72715-1)

Antes: `ins_tpt_constructivo.json` · después: `pruebas/bases/ins_tpt_constructivo.json`

45 cables cambian de largo; 3 cambian solo el texto de «cómo» (o entran / salen).

| Cable | Origen → destino | Largo antes | Largo después | Diferencia | Cómo antes | Cómo después |
|---|---|---:|---:|---:|---|---|
| 1104 | 11Q1 F ARRIBA → LD | 2650 | 1650 | -1000 | 75 (borne → canaleta) + canaleta de la bandeja 688 + puerta / placa 1850 (11XP 1 ABAJO), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 688 + curva a LD 100 + canaleta de la bandeja lateral derecha 609 + 150 (canaleta → 11XP 1 ABAJO), redondeado a 50 |
| 1105 | 11Q1 N ARRIBA → LD | 2600 | 1600 | -1000 | 75 (borne → canaleta) + canaleta de la bandeja 670 + puerta / placa 1850 (11XP 2 ABAJO), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 670 + curva a LD 100 + canaleta de la bandeja lateral derecha 604 + 150 (canaleta → 11XP 2 ABAJO), redondeado a 50 |
| 1108 | 11PS1 + → LI | 2050 | 600 | -1450 | 75 (borne → canaleta) + canaleta de la bandeja 99 + puerta / placa 1850 (12PS2 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 99 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 +), redondeado a 50 |
| 1109 | 11PS1 - → LI | 2050 | 600 | -1450 | 75 (borne → canaleta) + canaleta de la bandeja 87 + puerta / placa 1850 (12PS2 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 87 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 -), redondeado a 50 |
| 1201 | 12F1 ARRIBA → LI | 2250 | 800 | -1450 | 75 (borne → canaleta) + canaleta de la bandeja 281 + puerta / placa 1850 (12PS2 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 281 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 +), redondeado a 50 |
| 1202 | 12XP 2.1 → LI | 2350 | 950 | -1400 | 75 (borne → canaleta) + canaleta de la bandeja 417 + puerta / placa 1850 (12PS2 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 -), redondeado a 50 |
| 1204 | 12XP 1.4 → LI | 2550 | 1100 | -1450 | 75 (borne → canaleta) + canaleta de la bandeja 622 + puerta / placa 1850 (12PB1 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 622 + curva a LI 100 + canaleta de la bandeja lateral izquierda 116 + 150 (canaleta → 12PB1 +), redondeado a 50 |
| 1206 | 12XP 2.4 → LI | 2600 | 1300 | -1300 | 75 (borne → canaleta) + canaleta de la bandeja 632 + puerta / placa 1850 (12PB1 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 632 + curva a LI 100 + canaleta de la bandeja lateral izquierda 317 + 150 (canaleta → 12PB1 -), redondeado a 50 |
| 1311 | 13PS3 +Vo → LD | 1150 | 800 | -350 | canaletas 410 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 361 + curva a LD 100 + canaleta de la bandeja lateral derecha 94 + 150 (canaleta → 13XC2 1.1), redondeado a 50 |
| 1312 | 13PS3 -Vo → LD | 1150 | 800 | -350 | canaletas 420 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 371 + curva a LD 100 + canaleta de la bandeja lateral derecha 99 + 150 (canaleta → 13XC2 2.1), redondeado a 50 |
| 1315 | 33MX01 V+ → LD | 1100 | 1200 | +100 | canaletas 380 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 338 + curva a LD 100 + canaleta de la bandeja lateral derecha 497 + 150 (canaleta → 13XC2 1.4), redondeado a 50 |
| 1316 | 33MX01 V- → LD | 1100 | 1200 | +100 | canaletas 380 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 338 + curva a LD 100 + canaleta de la bandeja lateral derecha 492 + 150 (canaleta → 13XC2 2.4), redondeado a 50 |
| 1317 | 16XC 1 ARRIBA → 13XC2 1.3 | 2000 | 900 | -1100 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 480 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1318 | 16XC 2 ARRIBA → 13XC2 2.3 | 2000 | 900 | -1100 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 470 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1319 | 13XC1 3.3 → LD | 1500 | 1150 | -350 | canaletas 780 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 703 + curva a LD 100 + canaleta de la bandeja lateral derecha 99 + 150 (canaleta → 13XC2 2.2), redondeado a 50 |
| 1601 | 16XC 1 ABAJO → 33XAI F1 ARRIBA | 2000 | 600 | -1400 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 200 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1602 | 33MX01 2 → LD | 1150 | 1150 | 0 | canaletas 430 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 362 + curva a LD 100 + canaleta de la bandeja lateral derecha 461 + 150 (canaleta → 16XC 2 ABAJO), redondeado a 50 |
| 1603 | 16XC 3 ARRIBA → 33XAI F2 ARRIBA | 2000 | 950 | -1050 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 530 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1604 | 33MX01 4 → LD | 1150 | 850 | -300 | canaletas 440 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 369 + curva a LD 100 + canaleta de la bandeja lateral derecha 139 + 150 (canaleta → 16XC 4 ARRIBA), redondeado a 50 |
| 1605 | 16XC 3 ABAJO → 33XAI F3 ARRIBA | 2000 | 650 | -1350 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 210 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1606 | 33MX01 6 → LD | 1150 | 1200 | +50 | canaletas 450 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 377 + curva a LD 100 + canaleta de la bandeja lateral derecha 452 + 150 (canaleta → 16XC 4 ABAJO), redondeado a 50 |
| 1607 | 16XC 5 ARRIBA → 33XAI F4 ARRIBA | 2000 | 950 | -1050 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 520 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1608 | 33MX01 8 → LD | 1200 | 900 | -300 | canaletas 460 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 385 + curva a LD 100 + canaleta de la bandeja lateral derecha 149 + 150 (canaleta → 16XC 6 ARRIBA), redondeado a 50 |
| 1609 | 16XC 5 ABAJO → 33XAI F5 ARRIBA | 2000 | 650 | -1350 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 220 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1610 | 33MX01 10 → LD | 1200 | 1200 | 0 | canaletas 460 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 392 + curva a LD 100 + canaleta de la bandeja lateral derecha 442 + 150 (canaleta → 16XC 6 ABAJO), redondeado a 50 |
| 1611 | 16XC 7 ARRIBA → 33XAI F6 ARRIBA | 2000 | 950 | -1050 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 510 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1612 | 33MX01 12 → LD | 1200 | 900 | -300 | canaletas 470 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 400 + curva a LD 100 + canaleta de la bandeja lateral derecha 159 + 150 (canaleta → 16XC 8 ARRIBA), redondeado a 50 |
| 1613 | 16XC 7 ABAJO → 33XAI F7 ARRIBA | 2000 | 650 | -1350 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 230 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1614 | 33MX01 14 → LD | 1200 | 1200 | 0 | canaletas 480 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 409 + curva a LD 100 + canaleta de la bandeja lateral derecha 432 + 150 (canaleta → 16XC 8 ABAJO), redondeado a 50 |
| 1615 | 16XC 9 ARRIBA → 33XAI F8 ARRIBA | 2000 | 900 | -1100 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 500 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1616 | 33MX01 16 → LD | 1200 | 950 | -250 | canaletas 490 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 416 + curva a LD 100 + canaleta de la bandeja lateral derecha 168 + 150 (canaleta → 16XC 10 ARRIBA), redondeado a 50 |
| 1617 | 31XAI F1 ARRIBA → LD | 950 | 900 | -50 | canaletas 220 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 126 + curva a LD 100 + canaleta de la bandeja lateral derecha 427 + 150 (canaleta → 16XC 9 ABAJO), redondeado a 50 |
| 1619 | 16XC 11 ARRIBA → 32XAI F1 ARRIBA | 2000 | 950 | -1050 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 510 + margen 200 + agregado a LI 200, redondeado a 50 |
| 2105 | 21PCB01 5 → 32XAI 1 ARRIBA | 2000 | 2500 | +500 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 620 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 3301 | 33MX01 1 → LD | 2300 | 1250 | -1050 | 75 (borne → canaleta) + canaleta de la bandeja 358 + puerta / placa 1850 (33XAI 1 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 358 + curva a LD 100 + canaleta de la bandeja lateral derecha 536 + 150 (canaleta → 33XAI 1 ARRIBA), redondeado a 50 |
| 3303 | 33MX01 3 → LD | 2300 | 1250 | -1050 | 75 (borne → canaleta) + canaleta de la bandeja 365 + puerta / placa 1850 (33XAI 2 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 365 + curva a LD 100 + canaleta de la bandeja lateral derecha 532 + 150 (canaleta → 33XAI 2 ARRIBA), redondeado a 50 |
| 3305 | 33MX01 5 → LD | 2300 | 1250 | -1050 | 75 (borne → canaleta) + canaleta de la bandeja 373 + puerta / placa 1850 (33XAI 3 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 373 + curva a LD 100 + canaleta de la bandeja lateral derecha 527 + 150 (canaleta → 33XAI 3 ARRIBA), redondeado a 50 |
| 3307 | 33MX01 7 → LD | 2350 | 1250 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 381 + puerta / placa 1850 (33XAI 4 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 381 + curva a LD 100 + canaleta de la bandeja lateral derecha 522 + 150 (canaleta → 33XAI 4 ARRIBA), redondeado a 50 |
| 3309 | 33MX01 9 → LD | 2350 | 1250 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 388 + puerta / placa 1850 (33XAI 5 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 388 + curva a LD 100 + canaleta de la bandeja lateral derecha 517 + 150 (canaleta → 33XAI 5 ARRIBA), redondeado a 50 |
| 3311 | 33MX01 11 → LD | 2350 | 1250 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 396 + puerta / placa 1850 (33XAI 6 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 396 + curva a LD 100 + canaleta de la bandeja lateral derecha 512 + 150 (canaleta → 33XAI 6 ARRIBA), redondeado a 50 |
| 3313 | 33MX01 13 → LD | 2350 | 1250 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 405 + puerta / placa 1850 (33XAI 7 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 405 + curva a LD 100 + canaleta de la bandeja lateral derecha 507 + 150 (canaleta → 33XAI 7 ARRIBA), redondeado a 50 |
| 3315 | 33MX01 15 → LD | 2350 | 1250 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 412 + puerta / placa 1850 (33XAI 8 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 412 + curva a LD 100 + canaleta de la bandeja lateral derecha 502 + 150 (canaleta → 33XAI 8 ARRIBA), redondeado a 50 |
| 4305 | 43KR1 A1 → LD | 2550 | 1400 | -1150 | 75 (borne → canaleta) + canaleta de la bandeja 593 + puerta / placa 1850 (43XDI 1 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 593 + curva a LD 100 + canaleta de la bandeja lateral derecha 476 + 150 (canaleta → 43XDI 1 ARRIBA), redondeado a 50 |
| 4306 | 43KR1 A2 → LD | 2550 | 1400 | -1150 | 75 (borne → canaleta) + canaleta de la bandeja 593 + puerta / placa 1850 (43XDI 2 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 593 + curva a LD 100 + canaleta de la bandeja lateral derecha 471 + 150 (canaleta → 43XDI 2 ARRIBA), redondeado a 50 |
| 8101 | 61KR3 11 → LD | 2150 | 1000 | -1150 | 75 (borne → canaleta) + canaleta de la bandeja 182 + puerta / placa 1850 (81XCM 3 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 182 + curva a LD 100 + canaleta de la bandeja lateral derecha 451 + 150 (canaleta → 81XCM 3 ARRIBA), redondeado a 50 |
| 8102 | 61KR3 12 → LD | 2150 | 1000 | -1150 | 75 (borne → canaleta) + canaleta de la bandeja 182 + puerta / placa 1850 (81XCM 4 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 182 + curva a LD 100 + canaleta de la bandeja lateral derecha 446 + 150 (canaleta → 81XCM 4 ARRIBA), redondeado a 50 |
| 8103 | 21PCB01 35 → 81XCM 1 ARRIBA | 2000 | 2400 | +400 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 530 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 8104 | 21PCB01 36 → 81XCM 2 ARRIBA | 2000 | 2400 | +400 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 520 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |

## TPT de pruebas (tpt, topográfico 72887)

Antes: `ins_tpt.json` · después: `pruebas/bases/ins_tpt.json`

44 cables cambian de largo; 4 cambian solo el texto de «cómo» (o entran / salen).

| Cable | Origen → destino | Largo antes | Largo después | Diferencia | Cómo antes | Cómo después |
|---|---|---:|---:|---:|---|---|
| 1104 | 11Q1 F ARRIBA → LD | 2600 | 1650 | -950 | 75 (borne → canaleta) + canaleta de la bandeja 668 + puerta / placa 1850 (11XP 1 ABAJO), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 668 + curva a LD 100 + canaleta de la bandeja lateral derecha 609 + 150 (canaleta → 11XP 1 ABAJO), redondeado a 50 |
| 1105 | 11Q1 N ARRIBA → LD | 2600 | 1600 | -1000 | 75 (borne → canaleta) + canaleta de la bandeja 650 + puerta / placa 1850 (11XP 2 ABAJO), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 650 + curva a LD 100 + canaleta de la bandeja lateral derecha 604 + 150 (canaleta → 11XP 2 ABAJO), redondeado a 50 |
| 1108 | 11PS1 + → LI | 2050 | 600 | -1450 | 75 (borne → canaleta) + canaleta de la bandeja 99 + puerta / placa 1850 (12PS2 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 99 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 +), redondeado a 50 |
| 1109 | 11PS1 - → LI | 2050 | 600 | -1450 | 75 (borne → canaleta) + canaleta de la bandeja 87 + puerta / placa 1850 (12PS2 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 87 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 -), redondeado a 50 |
| 1201 | 12F1 ARRIBA → LI | 2250 | 800 | -1450 | 75 (borne → canaleta) + canaleta de la bandeja 281 + puerta / placa 1850 (12PS2 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 281 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 +), redondeado a 50 |
| 1202 | 12XP 2.1 → LI | 2350 | 950 | -1400 | 75 (borne → canaleta) + canaleta de la bandeja 417 + puerta / placa 1850 (12PS2 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 417 + curva a LI 100 + canaleta de la bandeja lateral izquierda 170 + 150 (canaleta → 12PS2 -), redondeado a 50 |
| 1204 | 12XP 1.4 → LI | 2550 | 1050 | -1500 | 75 (borne → canaleta) + canaleta de la bandeja 602 + puerta / placa 1850 (12PB1 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 602 + curva a LI 100 + canaleta de la bandeja lateral izquierda 116 + 150 (canaleta → 12PB1 +), redondeado a 50 |
| 1206 | 12XP 2.4 → LI | 2550 | 1300 | -1250 | 75 (borne → canaleta) + canaleta de la bandeja 612 + puerta / placa 1850 (12PB1 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 612 + curva a LI 100 + canaleta de la bandeja lateral izquierda 317 + 150 (canaleta → 12PB1 -), redondeado a 50 |
| 1311 | 13PS3 +Vo → LD | 1150 | 800 | -350 | canaletas 410 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 361 + curva a LD 100 + canaleta de la bandeja lateral derecha 94 + 150 (canaleta → 13XC2 1.1), redondeado a 50 |
| 1312 | 13PS3 -Vo → LD | 1150 | 800 | -350 | canaletas 420 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 371 + curva a LD 100 + canaleta de la bandeja lateral derecha 99 + 150 (canaleta → 13XC2 2.1), redondeado a 50 |
| 1315 | 33MX01 V+ → LD | 1100 | 1200 | +100 | canaletas 380 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 338 + curva a LD 100 + canaleta de la bandeja lateral derecha 497 + 150 (canaleta → 13XC2 1.4), redondeado a 50 |
| 1316 | 33MX01 V- → LD | 1100 | 1200 | +100 | canaletas 380 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 338 + curva a LD 100 + canaleta de la bandeja lateral derecha 492 + 150 (canaleta → 13XC2 2.4), redondeado a 50 |
| 1317 | 16XC 1 ARRIBA → 13XC2 1.3 | 2000 | 900 | -1100 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 480 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1318 | 16XC 2 ARRIBA → 13XC2 2.3 | 2000 | 900 | -1100 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 470 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1319 | 13XC1 3.3 → LD | 1450 | 1150 | -300 | canaletas 750 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 683 + curva a LD 100 + canaleta de la bandeja lateral derecha 99 + 150 (canaleta → 13XC2 2.2), redondeado a 50 |
| 1601 | 16XC 1 ABAJO → 33XAI F1 ARRIBA | 2000 | 600 | -1400 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 200 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1602 | 33MX01 2 → LD | 1150 | 1150 | 0 | canaletas 430 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 355 + curva a LD 100 + canaleta de la bandeja lateral derecha 461 + 150 (canaleta → 16XC 2 ABAJO), redondeado a 50 |
| 1603 | 16XC 3 ARRIBA → 33XAI F2 ARRIBA | 2000 | 950 | -1050 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 530 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1604 | 33MX01 4 → LD | 1150 | 850 | -300 | canaletas 430 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 363 + curva a LD 100 + canaleta de la bandeja lateral derecha 139 + 150 (canaleta → 16XC 4 ARRIBA), redondeado a 50 |
| 1605 | 16XC 3 ABAJO → 33XAI F3 ARRIBA | 2000 | 650 | -1350 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 210 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1606 | 33MX01 6 → LD | 1150 | 1150 | 0 | canaletas 440 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 371 + curva a LD 100 + canaleta de la bandeja lateral derecha 452 + 150 (canaleta → 16XC 4 ABAJO), redondeado a 50 |
| 1607 | 16XC 5 ARRIBA → 33XAI F4 ARRIBA | 2000 | 950 | -1050 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 520 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1608 | 33MX01 8 → LD | 1150 | 900 | -250 | canaletas 450 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 378 + curva a LD 100 + canaleta de la bandeja lateral derecha 149 + 150 (canaleta → 16XC 6 ARRIBA), redondeado a 50 |
| 1609 | 16XC 5 ABAJO → 33XAI F5 ARRIBA | 2000 | 650 | -1350 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 220 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1610 | 33MX01 10 → LD | 1200 | 1200 | 0 | canaletas 460 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 386 + curva a LD 100 + canaleta de la bandeja lateral derecha 442 + 150 (canaleta → 16XC 6 ABAJO), redondeado a 50 |
| 1611 | 16XC 7 ARRIBA → 33XAI F6 ARRIBA | 2000 | 950 | -1050 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 510 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1612 | 33MX01 12 → LD | 1200 | 900 | -300 | canaletas 460 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 394 + curva a LD 100 + canaleta de la bandeja lateral derecha 159 + 150 (canaleta → 16XC 8 ARRIBA), redondeado a 50 |
| 1613 | 16XC 7 ABAJO → 33XAI F7 ARRIBA | 2000 | 650 | -1350 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 230 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1614 | 33MX01 14 → LD | 1200 | 1200 | 0 | canaletas 470 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 402 + curva a LD 100 + canaleta de la bandeja lateral derecha 432 + 150 (canaleta → 16XC 8 ABAJO), redondeado a 50 |
| 1615 | 16XC 9 ARRIBA → 33XAI F8 ARRIBA | 2000 | 900 | -1100 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 500 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1616 | 33MX01 16 → LD | 1200 | 950 | -250 | canaletas 480 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 410 + curva a LD 100 + canaleta de la bandeja lateral derecha 168 + 150 (canaleta → 16XC 10 ARRIBA), redondeado a 50 |
| 1617 | 31XAI F1 ARRIBA → LD | 950 | 900 | -50 | canaletas 210 + margen 100 + LD 400 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 126 + curva a LD 100 + canaleta de la bandeja lateral derecha 427 + 150 (canaleta → 16XC 9 ABAJO), redondeado a 50 |
| 1619 | 16XC 11 ARRIBA → 32XAI F1 ARRIBA | 2000 | 950 | -1050 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 510 + margen 200 + agregado a LI 200, redondeado a 50 |
| 2105 | 21PCB01 5 → 32XAI 1 ARRIBA | 2000 | 2500 | +500 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 620 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 3301 | 33MX01 1 → LD | 2300 | 1250 | -1050 | 75 (borne → canaleta) + canaleta de la bandeja 352 + puerta / placa 1850 (33XAI 1 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 352 + curva a LD 100 + canaleta de la bandeja lateral derecha 536 + 150 (canaleta → 33XAI 1 ARRIBA), redondeado a 50 |
| 3303 | 33MX01 3 → LD | 2300 | 1250 | -1050 | 75 (borne → canaleta) + canaleta de la bandeja 359 + puerta / placa 1850 (33XAI 2 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 359 + curva a LD 100 + canaleta de la bandeja lateral derecha 532 + 150 (canaleta → 33XAI 2 ARRIBA), redondeado a 50 |
| 3305 | 33MX01 5 → LD | 2300 | 1250 | -1050 | 75 (borne → canaleta) + canaleta de la bandeja 367 + puerta / placa 1850 (33XAI 3 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 367 + curva a LD 100 + canaleta de la bandeja lateral derecha 527 + 150 (canaleta → 33XAI 3 ARRIBA), redondeado a 50 |
| 3307 | 33MX01 7 → LD | 2300 | 1250 | -1050 | 75 (borne → canaleta) + canaleta de la bandeja 374 + puerta / placa 1850 (33XAI 4 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 374 + curva a LD 100 + canaleta de la bandeja lateral derecha 522 + 150 (canaleta → 33XAI 4 ARRIBA), redondeado a 50 |
| 3309 | 33MX01 9 → LD | 2350 | 1250 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 382 + puerta / placa 1850 (33XAI 5 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 382 + curva a LD 100 + canaleta de la bandeja lateral derecha 517 + 150 (canaleta → 33XAI 5 ARRIBA), redondeado a 50 |
| 3311 | 33MX01 11 → LD | 2350 | 1250 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 390 + puerta / placa 1850 (33XAI 6 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 390 + curva a LD 100 + canaleta de la bandeja lateral derecha 512 + 150 (canaleta → 33XAI 6 ARRIBA), redondeado a 50 |
| 3313 | 33MX01 13 → LD | 2350 | 1250 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 398 + puerta / placa 1850 (33XAI 7 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 398 + curva a LD 100 + canaleta de la bandeja lateral derecha 507 + 150 (canaleta → 33XAI 7 ARRIBA), redondeado a 50 |
| 3315 | 33MX01 15 → LD | 2350 | 1250 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 406 + puerta / placa 1850 (33XAI 8 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 406 + curva a LD 100 + canaleta de la bandeja lateral derecha 502 + 150 (canaleta → 33XAI 8 ARRIBA), redondeado a 50 |
| 4305 | 43KR1 A1 → LD | 2500 | 1400 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 573 + puerta / placa 1850 (43XDI 1 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 573 + curva a LD 100 + canaleta de la bandeja lateral derecha 476 + 150 (canaleta → 43XDI 1 ARRIBA), redondeado a 50 |
| 4306 | 43KR1 A2 → LD | 2500 | 1400 | -1100 | 75 (borne → canaleta) + canaleta de la bandeja 573 + puerta / placa 1850 (43XDI 2 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 573 + curva a LD 100 + canaleta de la bandeja lateral derecha 471 + 150 (canaleta → 43XDI 2 ARRIBA), redondeado a 50 |
| 8101 | 61KR3 11 → LD | 2150 | 1000 | -1150 | 75 (borne → canaleta) + canaleta de la bandeja 182 + puerta / placa 1850 (81XCM 3 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 182 + curva a LD 100 + canaleta de la bandeja lateral derecha 451 + 150 (canaleta → 81XCM 3 ARRIBA), redondeado a 50 |
| 8102 | 61KR3 12 → LD | 2150 | 1000 | -1150 | 75 (borne → canaleta) + canaleta de la bandeja 182 + puerta / placa 1850 (81XCM 4 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 182 + curva a LD 100 + canaleta de la bandeja lateral derecha 446 + 150 (canaleta → 81XCM 4 ARRIBA), redondeado a 50 |
| 8103 | 21PCB01 35 → 81XCM 1 ARRIBA | 2000 | 2400 | +400 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 530 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 8104 | 21PCB01 36 → 81XCM 2 ARRIBA | 2000 | 2400 | +400 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 520 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |

## 66817

Antes: `ins_66817.json` · después: `pruebas/bases/ins_66817.json`

13 cables cambian de largo; 0 cambian solo el texto de «cómo» (o entran / salen).

| Cable | Origen → destino | Largo antes | Largo después | Diferencia | Cómo antes | Cómo después |
|---|---|---:|---:|---:|---|---|
| 1101 | 11XP 1 ABAJO → 12PS1 + | 2000 | 800 | -1200 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 380 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1102 | 11XP 2 ABAJO → 12PS1 - | 2000 | 800 | -1200 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 370 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1201 | 12F1 ARRIBA → LI | 2200 | 800 | -1400 | 75 (borne → canaleta) + canaleta de la bandeja 271 + puerta / placa 1850 (12PS1 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 271 + curva a LI 100 + canaleta de la bandeja lateral izquierda 176 + 150 (canaleta → 12PS1 +), redondeado a 50 |
| 1202 | 12XP 4.1 → LI | 2400 | 950 | -1450 | 75 (borne → canaleta) + canaleta de la bandeja 427 + puerta / placa 1850 (12PS1 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 427 + curva a LI 100 + canaleta de la bandeja lateral izquierda 176 + 150 (canaleta → 12PS1 -), redondeado a 50 |
| 1204 | 12XP 1.4 → LI | 2550 | 1050 | -1500 | 75 (borne → canaleta) + canaleta de la bandeja 598 + puerta / placa 1850 (12PB1 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 598 + curva a LI 100 + canaleta de la bandeja lateral izquierda 116 + 150 (canaleta → 12PB1 +), redondeado a 50 |
| 1205 | 12XP 4.4 → LI | 2550 | 1300 | -1250 | 75 (borne → canaleta) + canaleta de la bandeja 622 + puerta / placa 1850 (12PB1 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 622 + curva a LI 100 + canaleta de la bandeja lateral izquierda 317 + 150 (canaleta → 12PB1 -), redondeado a 50 |
| 1216 | 12XP 4.3 → LD | 2600 | 1100 | -1500 | 75 (borne → canaleta) + canaleta de la bandeja 652 + puerta / placa 1850 (12CB1 -), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 652 + curva a LD 100 + canaleta de la bandeja lateral derecha 103 + 150 (canaleta → 12CB1 -), redondeado a 50 |
| 1225 | 12F3 ABAJO → LD | 2550 | 1050 | -1500 | 75 (borne → canaleta) + canaleta de la bandeja 610 + puerta / placa 1850 (12CB1 +), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 610 + curva a LD 100 + canaleta de la bandeja lateral derecha 103 + 150 (canaleta → 12CB1 +), redondeado a 50 |
| 4305 | 43KR1 A1 → LD | 2500 | 1050 | -1450 | 75 (borne → canaleta) + canaleta de la bandeja 563 + puerta / placa 1850 (43XDI 1 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 563 + curva a LD 100 + canaleta de la bandeja lateral derecha 139 + 150 (canaleta → 43XDI 1 ARRIBA), redondeado a 50 |
| 4306 | 43KR1 A2 → LD | 2500 | 1050 | -1450 | 75 (borne → canaleta) + canaleta de la bandeja 563 + puerta / placa 1850 (43XDI 2 ARRIBA), redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 563 + curva a LD 100 + canaleta de la bandeja lateral derecha 144 + 150 (canaleta → 43XDI 2 ARRIBA), redondeado a 50 |
| 8101 | 21PCB01 35 → 81XCM 1 ARRIBA | 2000 | 2050 | +50 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 170 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 8102 | 21PCB01 36 → 81XCM 2 ARRIBA | 2000 | 2050 | +50 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 170 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 8103 | 21PCB01 37 → 81XCM 3 ARRIBA | 2000 | 2050 | +50 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral derecha 180 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |

## 75287

Antes: `ins_75287.json` · después: `pruebas/bases/ins_75287.json`

14 cables cambian de largo; 0 cambian solo el texto de «cómo» (o entran / salen).

| Cable | Origen → destino | Largo antes | Largo después | Diferencia | Cómo antes | Cómo después |
|---|---|---:|---:|---:|---|---|
| 1101 | 11XP 1 ABAJO → 11MS1 ABAJO | 2000 | 700 | -1300 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral izquierda 270 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1102 | 11XP 2 ABAJO → 11MS1 ABAJO | 2000 | 700 | -1300 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral izquierda 270 + margen 200 + agregado a LI 200, redondeado a 50 |
| 1104 | 11Q1 F ARRIBA → LI | 2450 | 1100 | -1350 | canaletas 630 + margen 100 + LI 1500 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 567 + curva a LI 100 + canaleta de la bandeja lateral izquierda 205 + 150 (canaleta → 11MS1 ARRIBA), redondeado a 50 |
| 1105 | 11Q1 N ARRIBA → LI | 2450 | 1100 | -1350 | canaletas 610 + margen 100 + LI 1500 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 549 + curva a LI 100 + canaleta de la bandeja lateral izquierda 205 + 150 (canaleta → 11MS1 ARRIBA), redondeado a 50 |
| 1110 | 11PS1 1 (-) → LI | 2150 | 850 | -1300 | canaletas 340 + margen 100 + LI 1500 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 298 + curva a LI 100 + canaleta de la bandeja lateral izquierda 208 + 150 (canaleta → 12XPS 2 ABAJO), redondeado a 50 |
| 1111 | 11PS1 3 (+) → LI | 2200 | 850 | -1350 | canaletas 360 + margen 100 + LI 1500 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 310 + curva a LI 100 + canaleta de la bandeja lateral izquierda 213 + 150 (canaleta → 12XPS 1 ABAJO), redondeado a 50 |
| 1201 | 12F1 ARRIBA → LI | 2400 | 1100 | -1300 | canaletas 590 + margen 100 + LI 1500 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 524 + curva a LI 100 + canaleta de la bandeja lateral izquierda 203 + 150 (canaleta → 12XPS 3 ABAJO), redondeado a 50 |
| 1203 | 13XC1 3.4 → LI | 2200 | 850 | -1350 | canaletas 380 + margen 100 + LI 1500 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 320 + curva a LI 100 + canaleta de la bandeja lateral izquierda 188 + 150 (canaleta → 12XPS 6 ABAJO), redondeado a 50 |
| 1205 | 12XP 2.1 → LI | 1950 | 650 | -1300 | canaletas 140 + margen 100 + LI 1500 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 81 + curva a LI 100 + canaleta de la bandeja lateral izquierda 198 + 150 (canaleta → 12XPS 4 ABAJO), redondeado a 50 |
| 1206 | 13F3 ARRIBA → LI | 2450 | 1100 | -1350 | canaletas 610 + margen 100 + LI 1500 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 541 + curva a LI 100 + canaleta de la bandeja lateral izquierda 193 + 150 (canaleta → 12XPS 5 ABAJO), redondeado a 50 |
| 2135 | 21PCB01 35 → 12XPS 7 ABAJO | 2000 (fuera) | 2100 (fuera) | +100 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral izquierda 250 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 2135 | 81XCM 11 ARRIBA → LI | 2300 (fuera) | 1000 (fuera) | -1300 | canaletas 500 + margen 100 + LI 1500 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 465 + curva a LI 100 + canaleta de la bandeja lateral izquierda 183 + 150 (canaleta → 12XPS 7 ABAJO), redondeado a 50 |
| 2136 | 21PCB01 36 → 12XPS 8 ABAJO | 2000 (fuera) | 2100 (fuera) | +100 | pendiente LI↔LI (valor fijo) | canaleta de la bandeja lateral izquierda 250 + puerta / placa 1500 + agregado puerta / placa 350, redondeado a 50 |
| 2136 | 81XCM 12 ARRIBA → LI | 2400 (fuera) | 1100 (fuera) | -1300 | canaletas 600 + margen 100 + LI 1500 + agregado a LI 200, redondeado a 50 | 75 (borne → canaleta) + canaleta de la bandeja 549 + curva a LI 100 + canaleta de la bandeja lateral izquierda 178 + 150 (canaleta → 12XPS 8 ABAJO), redondeado a 50 |

## PAE (76884)

Antes: `ins_76884.json` · después: `pruebas/bases/ins_76884.json`

Sin cambios.
