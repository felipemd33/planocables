# Lista WPC: el .wpc de laterales (2026-10-13)

Pedido del usuario: los cables que nacen y mueren en la MISMA bandeja lateral (en la E8, `otra = 'misma bandeja'`; en E6
son pendientes LI↔LI) van en un `.wpc` aparte, uno solo para las dos laterales (`<código> - <plano> Rev <rev> - Laterales.wpc`),
con el largo como en la bandeja: recorrido en la lateral (`largo_mm` de la línea de la E8; un cable directo, su largo directo)
+ sobrante (`margen_bandeja`, 100) + agregado (`agregado_bandeja`, 75), redondeado a 50. La lista principal ya no los lleva,
aunque se tilden los pendientes.

Cambian SOLO los goldens de la lista principal con «Pendientes LI↔LI» tildado (`*_pend_otra`, y los casos `ediciones` y
`wpc_a_medias`, que traen los pendientes tildados en su `ins.wpc.cfg`): salen esas filas y nada más (las demás filas, sus
largos y su orden quedan iguales; solo se renumera la columna `n`). Configuración fija de las pruebas
(`pruebas/fixtures/wpc/wpc.json`). Goldens nuevos: `wpc_<trabajo>_laterales.csv` / `.json`.

| Trabajo | Filas de la principal con pendientes (antes → ahora) | Pasan al .wpc de laterales | En el CSV de laterales | Metros en el CSV principal (antes → ahora) | Metros en el CSV de laterales |
|---|---|---:|---:|---|---:|
| 75287 | 126 → 124 | 2 | 2 de 2 | 130.20 → 128.80 | 0.95 |
| 76884 | 190 → 173 | 17 | 13 de 17 | 168.95 → 160.10 | 6.10 |
| tpt | 104 → 93 | 11 | 11 de 11 | 119.95 → 111.20 | 6.15 |
| tpt_constructivo | 104 → 93 | 11 | 11 de 11 | 120.85 → 112.10 | 6.15 |
| pae_usuario | 190 → 173 | 17 | 13 de 17 | 178.15 → 167.45 | 7.55 |
| caso_cfg_redondeo_abc | 25 → 24 | 1 | 3 de 3 | 13.82 → 13.24 | 0.89 |
| caso_cfg_texto_100 | 25 → 24 | 1 | 3 de 3 | 17.50 → 16.90 | 1.00 |
| caso_cfg_texto_abc | 25 → 24 | 1 | 3 de 3 | 11.30 → 10.70 | 0.00 |
| caso_cfg_texto_vacio | 25 → 24 | 1 | 3 de 3 | 17.50 → 16.90 | 1.00 |
| caso_ediciones | 25 → 24 | 1 | 3 de 3 | 18.13 → 18.13 | 0.60 |
| caso_ediciones (tal cual, con los pendientes tildados en el caso) | 25 → 24 | 1 | 3 de 3 | 18.13 → 18.13 | 0.60 |
| caso_producto_vacio | 25 → 24 | 1 | 3 de 3 | 17.50 → 16.90 | 1.00 |
| caso_reemplazo_otro_documento | 25 → 24 | 1 | 3 de 3 | 17.50 → 16.90 | 1.00 |
| caso_reemplazo_pae | 25 → 24 | 1 | 3 de 3 | 17.50 → 16.90 | 1.00 |
| caso_sin_producto | 25 → 24 | 1 | 3 de 3 | 17.50 → 16.90 | 1.00 |
| caso_wpc_a_medias | 25 → 24 | 1 | 3 de 3 | 17.50 → 16.90 | 1.00 |
| caso_wpc_a_medias (tal cual, con los pendientes tildados en el caso) | 23 → 22 | 1 | 3 de 3 | 16.95 → 16.35 | 1.00 |

66817: sin cables de una misma lateral (sin archivo de laterales; los goldens no cambian).

## 75287

Archivo de laterales: `75286-1 - 75287 Rev 6 - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 11XP 1 ABAJO → 11MS1 ABAJO | 700 | 450 | recorrido en la bandeja lateral izquierda 270 + sobrante 100 + agregado 75, redondeado a 50 | 180\|0 |
| 1102 | 11XP 2 ABAJO → 11MS1 ABAJO | 700 | 500 | recorrido en la bandeja lateral izquierda 280 + sobrante 100 + agregado 75, redondeado a 50 | 180\|0 |

## 76884

Archivo de laterales: `76857-1 - ZPL-76884 Rev 1 - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1156 | 11Q1 F ABAJO → 11Q2 F ARRIBA | 1200 | 950 | recorrido en la bandeja lateral izquierda 770 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1157 | 11Q1 N ABAJO → 11Q2 N ARRIBA | 1200 | 950 | recorrido en la bandeja lateral izquierda 770 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1158 | 11Q2 F ABAJO → 11X220V 1.3 | 750 | 500 | recorrido en la bandeja lateral izquierda 310 + sobrante 100 + agregado 75, redondeado a 50 | 180\|0 |
| 1159 | 11Q2 N ABAJO → 11X220V 2.3 | 700 | 500 | recorrido en la bandeja lateral izquierda 300 + sobrante 100 + agregado 75, redondeado a 50 | 180\|0 |
| 1181 | 11SK1 L ABAJO → 11X220V 1.4 | 750 | 550 | recorrido en la bandeja lateral izquierda 350 + sobrante 100 + agregado 75, redondeado a 50 | 180\|0 |
| 1182 | 11SK1 N ABAJO → 11X220V 2.4 | 800 | 600 | recorrido en la bandeja lateral izquierda 380 + sobrante 100 + agregado 75, redondeado a 50 | 180\|0 |
| 1221 | 12PS1 +Pan → 12XPS 3 ARRIBA | 450 | 250 | directo al borne 50 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1222 | 12PS1 -Pan → 12XPS 4 ARRIBA | 450 | 250 | directo al borne 50 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1223 | 12PS1 +Bat → 12XPS 5 ARRIBA | 450 | 250 | directo al borne 50 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1224 | 12PS1 -Bat → 12XPS 6 ARRIBA | 450 | 250 | directo al borne 50 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1225 | 12PS1 +Car → 12XPS 8 ARRIBA | 450 | 250 | directo al borne 50 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1226 | 12PS1 -Car → 12XPS 9 ARRIBA | 450 | 250 | directo al borne 50 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| s/n 12PS1 A | 12PS1 A → 12XPS 10 ARRIBA | 500 (fuera) | 250 (fuera: comunicación (sección fina)) | directo al borne 60 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| s/n 12PS1 B | 12PS1 B → 12XPS 11 ARRIBA | 450 (fuera) | 250 (fuera: comunicación (sección fina)) | directo al borne 50 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| s/n 12PS1 GND | 12PS1 GND → 12XPS 12 ARRIBA | 450 (fuera) | 250 (fuera: comunicación (sección fina)) | directo al borne 50 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| s/n 12PS1 VCC | 12PS1 VCC → 12XPS 13 ARRIBA | 500 (fuera) | 250 (fuera: comunicación (sección fina)) | directo al borne 60 (bandeja lateral izquierda, sin la canaleta) + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| ⏚11SK1 | 11SK1 PE ABAJO → 11XPVAC 3.4 | 750 | 550 | recorrido en la bandeja lateral izquierda 350 + sobrante 100 + agregado 75, redondeado a 50 | 180\|0 |

## tpt

Archivo de laterales: `72715-1 - 72715 Rev 8 - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1317 | 16XC 1 ARRIBA → 13XC2 1.3 | 900 | 650 | recorrido en la bandeja lateral derecha 460 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1318 | 16XC 2 ARRIBA → 13XC2 2.3 | 900 | 650 | recorrido en la bandeja lateral derecha 470 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1601 | 16XC 1 ABAJO → 33XAI F1 ARRIBA | 600 | 400 | recorrido en la bandeja lateral derecha 180 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1603 | 16XC 3 ARRIBA → 33XAI F2 ARRIBA | 950 | 700 | recorrido en la bandeja lateral derecha 510 + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1605 | 16XC 3 ABAJO → 33XAI F3 ARRIBA | 600 | 350 | recorrido en la bandeja lateral derecha 170 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1607 | 16XC 5 ARRIBA → 33XAI F4 ARRIBA | 900 | 700 | recorrido en la bandeja lateral derecha 490 + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1609 | 16XC 5 ABAJO → 33XAI F5 ARRIBA | 600 | 350 | recorrido en la bandeja lateral derecha 160 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1611 | 16XC 7 ARRIBA → 33XAI F6 ARRIBA | 900 | 650 | recorrido en la bandeja lateral derecha 470 + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1613 | 16XC 7 ABAJO → 33XAI F7 ARRIBA | 600 | 350 | recorrido en la bandeja lateral derecha 160 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1615 | 16XC 9 ARRIBA → 33XAI F8 ARRIBA | 850 | 650 | recorrido en la bandeja lateral derecha 450 + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1619 | 16XC 11 ARRIBA → 32XAI F1 ARRIBA | 950 | 700 | recorrido en la bandeja lateral derecha 510 + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |

## tpt_constructivo

Archivo de laterales: `72715-1 - 72715 Rev 8 - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1317 | 16XC 1 ARRIBA → 13XC2 1.3 | 900 | 650 | recorrido en la bandeja lateral derecha 460 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1318 | 16XC 2 ARRIBA → 13XC2 2.3 | 900 | 650 | recorrido en la bandeja lateral derecha 470 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1601 | 16XC 1 ABAJO → 33XAI F1 ARRIBA | 600 | 400 | recorrido en la bandeja lateral derecha 180 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1603 | 16XC 3 ARRIBA → 33XAI F2 ARRIBA | 950 | 700 | recorrido en la bandeja lateral derecha 510 + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1605 | 16XC 3 ABAJO → 33XAI F3 ARRIBA | 600 | 350 | recorrido en la bandeja lateral derecha 170 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1607 | 16XC 5 ARRIBA → 33XAI F4 ARRIBA | 900 | 700 | recorrido en la bandeja lateral derecha 490 + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1609 | 16XC 5 ABAJO → 33XAI F5 ARRIBA | 600 | 350 | recorrido en la bandeja lateral derecha 160 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1611 | 16XC 7 ARRIBA → 33XAI F6 ARRIBA | 900 | 650 | recorrido en la bandeja lateral derecha 470 + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1613 | 16XC 7 ABAJO → 33XAI F7 ARRIBA | 600 | 350 | recorrido en la bandeja lateral derecha 160 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1615 | 16XC 9 ARRIBA → 33XAI F8 ARRIBA | 850 | 650 | recorrido en la bandeja lateral derecha 450 + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |
| 1619 | 16XC 11 ARRIBA → 32XAI F1 ARRIBA | 950 | 700 | recorrido en la bandeja lateral derecha 510 + sobrante 100 + agregado 75, redondeado a 50 | 0\|180 |

## pae_usuario

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1156 | 11Q1 F ABAJO → 11Q2 F ARRIBA | 1200 | 950 | recorrido en la bandeja lateral izquierda 770 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1157 | 11Q1 N ABAJO → 11Q2 N ARRIBA | 1200 | 950 | recorrido en la bandeja lateral izquierda 770 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1158 | 11Q2 F ABAJO → 11X220V 1.3 | 750 | 500 | recorrido en la bandeja lateral izquierda 310 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1159 | 11Q2 N ABAJO → 11X220V 2.3 | 700 | 500 | recorrido en la bandeja lateral izquierda 300 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1181 | 11SK1 L ABAJO → 11X220V 1.4 | 800 | 550 | recorrido en la bandeja lateral izquierda 370 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1182 | 11SK1 N ABAJO → 11X220V 2.4 | 800 | 550 | recorrido en la bandeja lateral izquierda 360 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1221 | 12PS1 +Pan → 12XPS 3 ARRIBA | 750 | 500 | recorrido en la bandeja lateral izquierda 310 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1222 | 12PS1 -Pan → 12XPS 4 ARRIBA | 750 | 500 | recorrido en la bandeja lateral izquierda 310 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1223 | 12PS1 +Bat → 12XPS 5 ARRIBA | 750 | 500 | recorrido en la bandeja lateral izquierda 320 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1224 | 12PS1 -Bat → 12XPS 6 ARRIBA | 750 | 500 | recorrido en la bandeja lateral izquierda 320 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1225 | 12PS1 +Car → 12XPS 8 ARRIBA | 750 | 500 | recorrido en la bandeja lateral izquierda 310 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1226 | 12PS1 -Car → 12XPS 9 ARRIBA | 750 | 500 | recorrido en la bandeja lateral izquierda 310 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| s/n 12PS1 A | 12PS1 A → 12XPS 10 ARRIBA | 750 (fuera) | 500 (fuera: comunicación (sección fina)) | recorrido en la bandeja lateral izquierda 320 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| s/n 12PS1 B | 12PS1 B → 12XPS 11 ARRIBA | 750 (fuera) | 500 (fuera: comunicación (sección fina)) | recorrido en la bandeja lateral izquierda 310 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| s/n 12PS1 GND | 12PS1 GND → 12XPS 12 ARRIBA | 750 (fuera) | 500 (fuera: comunicación (sección fina)) | recorrido en la bandeja lateral izquierda 310 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| s/n 12PS1 VCC | 12PS1 VCC → 12XPS 13 ARRIBA | 750 (fuera) | 500 (fuera: comunicación (sección fina)) | recorrido en la bandeja lateral izquierda 320 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| ⏚11SK1 | 11SK1 PE ABAJO → 11XPVAC 3.4 | 750 | 550 | recorrido en la bandeja lateral izquierda 350 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |

## caso_cfg_redondeo_abc

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 12L1 1 → 12L1 2 | 580 | 355 | recorrido en la bandeja lateral izquierda 180 + sobrante 100 + agregado 75, redondeado a 1 | 0\|0 |
| 1105 | 12L1 5 → 12L1 6 | (no estaba: no es pendiente en E6) | 265 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 1 | 0\|0 |
| 1105 | 12L1 6 → 12L1 7 | (no estaba: no es pendiente en E6) | 265 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 1 | 0\|0 |

## caso_cfg_texto_100

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 12L1 1 → 12L1 2 | 600 | 400 | recorrido en la bandeja lateral izquierda 180 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 5 → 12L1 6 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 6 → 12L1 7 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |

## caso_cfg_texto_abc

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 12L1 1 → 12L1 2 | 600 | NaN | recorrido en la bandeja lateral izquierda 180 + sobrante NaN + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 5 → 12L1 6 | (no estaba: no es pendiente en E6) | NaN | recorrido en la bandeja lateral izquierda 90 + sobrante NaN + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 6 → 12L1 7 | (no estaba: no es pendiente en E6) | NaN | recorrido en la bandeja lateral izquierda 90 + sobrante NaN + agregado 75, redondeado a 50 | 0\|0 |

## caso_cfg_texto_vacio

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 12L1 1 → 12L1 2 | 600 | 400 | recorrido en la bandeja lateral izquierda 180 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 5 → 12L1 6 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 6 → 12L1 7 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |

## caso_ediciones

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 12L1 1 → 12L1 2 | 0 | 0 | recorrido en la bandeja lateral izquierda 180 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 5 → 12L1 6 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 6 → 12L1 7 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |

## caso_producto_vacio

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 12L1 1 → 12L1 2 | 600 | 400 | recorrido en la bandeja lateral izquierda 180 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 5 → 12L1 6 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 6 → 12L1 7 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |

## caso_reemplazo_otro_documento

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 12L1 1 → 12L1 2 | 600 | 400 | recorrido en la bandeja lateral izquierda 180 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 5 → 12L1 6 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 6 → 12L1 7 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |

## caso_reemplazo_pae

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 12L1 1 → 12L1 2 | 600 | 400 | recorrido en la bandeja lateral izquierda 180 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 5 → 12L1 6 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 6 → 12L1 7 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |

## caso_sin_producto

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 12L1 1 → 12L1 2 | 600 | 400 | recorrido en la bandeja lateral izquierda 180 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 5 → 12L1 6 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 6 → 12L1 7 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |

## caso_wpc_a_medias

Archivo de laterales: `prueba - WPC - Laterales.wpc`

| Cable | Origen → destino | Antes: lista principal (pendiente) | Ahora: .wpc de laterales | Cómo (ahora) | Termos |
|---|---|---:|---:|---|---|
| 1101 | 12L1 1 → 12L1 2 | 600 | 400 | recorrido en la bandeja lateral izquierda 180 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 5 → 12L1 6 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
| 1105 | 12L1 6 → 12L1 7 | (no estaba: no es pendiente en E6) | 300 | recorrido en la bandeja lateral izquierda 90 + sobrante 100 + agregado 75, redondeado a 50 | 0\|0 |
