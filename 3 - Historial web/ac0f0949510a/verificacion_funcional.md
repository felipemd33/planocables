# Verificación del instructivo de la bandeja (E6) contra el funcional 75287 REV.6

Revisé una por una las diferencias que marcaron los revisores. En cada caso miré la hoja del funcional (recortes ampliados en `verfun/verif/`), seguí las flechas entre hojas y usé las fotos del tablero para desempatar. Las diferencias repetidas entre grupos quedaron en una sola fila.

Formato de línea del taller: `nº: <color><sección>MM origen → destino`. LI = sale por el lateral izquierdo. Un pendiente es LI↔LI.

## Diferencias reales

### Gravedad ALTA

| Cable | Tipo | En el instructivo | Cómo tiene que quedar | Evidencia |
|---|---|---|---|---|
| 1204 | estación | Línea de E6 `1204: R35MM 12F2 → LI`, sin decir de qué lado del fusible | Se saca de E6. En otra_estacion **E8**: `1204: R35MM 12F2 (borne lado BH-01-ZV) → BH-01-ZV (contacto del arrancador)` | Hoja 12 E2-E4: 1204 (Rojo/35mm2) une el lado izquierdo del fusible mega 12F2 150A con el contacto de BH-01-ZV. Regla del usuario: los cables de 35 mm se cablean en la estación 8. |
| 1215 | estación | Línea de E6 `1215: R35MM 12F2 → LI` | Se saca de E6. En otra_estacion **E8**: `1215: R35MM 12F2 (borne lado 12PB1) → 12PB1 +` | Hoja 12 E4: 1215 (Rojo/35mm2) va del lado derecho de 12F2 al borne + de 12PB1. Es de 35 mm2, así que va en E8. |
| 1216 | estación + punta | Pendiente `1216: 12PB1 ABAJO ↔ BH-01` (N35MM) | Se saca de pendientes. En otra_estacion **E8**: `1216: N35MM 12PB1 - → BH-01-M (GND del motor)` | Hoja 12 E3-F5: 1216 (Negro/35mm2) va del borne - de 12PB1 al GND de BH-01-M. El aparato se llama BH-01-M, no "BH-01". |
| 2134 | falta cable | No tiene ninguna línea. En `sueltos` figura con la punta falsa `46DB1 ABAJO` | `2134: MALLA 81XCM 3 ARRIBA → LI` y `2134: MALLA 81XCM 7 ARRIBA → LI`. Es un cable de 3 puntas y la unión está en 21PCB01 34 (Return, en la puerta). | Hoja 21 D7: 34 Return → 2134 → flecha `81XCM:3 (Sh81:B5)`. Hoja 81 B2-B5: la línea a trazos sale de Return 34, une las mallas de los dos cables Marlew del Port #2 y termina en 81XCM 3 (cable de 81XCM 1/2) y en 81XCM 7 (cable de 81XCM 5/6), del lado izquierdo, que es ARRIBA. En la foto 12.35.44 (3) se ve un drenaje pelado con puntera gris en el módulo 2, fila de arriba (81XCM 3), y otro en el módulo 4 (81XCM 7). |
| 2137 | falta cable | No tiene ninguna línea. En `sueltos` figura con la punta falsa `46DB1 ABAJO` | `2137: MALLA 81XCM 13 ARRIBA → LI`. Además, un pendiente: `2137: MALLA 21PCB01 37 ↔ empalme con la malla del tramo 12XPS–81XCM (junto a 12XPS)` | Hoja 21 D8: 37 Return → 2137 → `81XCM:13 (Sh81:D5)`. Hoja 81: los trazos van de Return 37 a la malla del cable que baja a 12XPS. Esa malla se empalma con la del cable 12XPS→81XCM, sin tocar ningún borne de 12XPS, y termina en 81XCM 13 del lado izquierdo. |

Sobre la sección de 2134 y 2137: el programa les puso Negro 0,75 por la nota general del plano. En la hoja 81 están dibujados a trazos, sin color ni sección: son la malla (drenaje) del cable Marlew 1x2x22 AWG. El usuario tiene que confirmar cómo se escriben (por ejemplo "MALLA") y qué puntera llevan.

### Gravedad MEDIA

| Cable | Tipo | En el instructivo | Cómo tiene que quedar | Evidencia |
|---|---|---|---|---|
| 1108 | punta equivocada | `1108: M1MM 11PS1 L-3 → 11SK1 L ABAJO` (el programa puso la unión en la fuente) | `1108: M2.5MM 11Q2 F ABAJO → 11PS1 L-3` (queda igual) y `1108: M1MM 11Q2 F ABAJO → 11SK1 L ABAJO`. La terminal doble va en 11Q2 F ABAJO. | Hoja 11 C6: el tramo en diagonal del Marrón/1mm2 sube hacia 11Q2 borne 2. Es el mismo criterio que el 6201 de la hoja 62, donde la diagonal apunta al borne de la unión. En las fotos 1.4 y 12.35.38, 1108 tiene puntera GRIS (doble 2,5) en 11Q2 abajo y puntera azul simple en 11PS1 L. |
| 1109 | punta equivocada | `1109: B1MM 11PS1 N-2 → 11SK1 N ABAJO` | `1109: B2.5MM 11Q2 N ABAJO → 11PS1 N-2` (queda igual) y `1109: B1MM 11Q2 N ABAJO → 11SK1 N ABAJO`. La terminal doble va en 11Q2 N ABAJO. | Hoja 11 C6: la diagonal del Blanco/1mm2 sube hacia 11Q2 borne 4. En la foto 1.4, 11Q2 abajo tiene puntera gris doble y se ve un segundo conductor blanco detrás. |
| 2135 | falta punta | Solo la línea `2135: B0.32MM 81XCM 11 ARRIBA → LI`, que está bien | Hay que agregar el pendiente `2135: B0.32MM 21PCB01 35 ↔ 12XPS 7 ABAJO`. Es un cable de 3 puntas y la unión está en 12XPS 7 ABAJO. | Hoja 81 C2-E3: 2135 baja desde 21PCB01 35 y entra a 12XPS 7 por la derecha (ABAJO). De ese mismo borne sale otro 2135 hacia 81XCM 11. Hoja 12 B7: dos tramos de 2135 llegan a 12XPS 7 por el punto de abajo. 21PCB01 y 12XPS están fuera de la bandeja. |
| 2136 | falta punta | Solo la línea `2136: A0.32MM 81XCM 12 ARRIBA → LI`, que está bien | Hay que agregar el pendiente `2136: A0.32MM 21PCB01 36 ↔ 12XPS 8 ABAJO`. La unión está en 12XPS 8 ABAJO. | Es el mismo dibujo que el 2135, en las hojas 81 y 12, con 12XPS 8. |
| ⏚TOMA (sin nº) | sin número | No figura. XPE tampoco está en `componentes_bandeja` | `⏚TOMA: VA1MM 11SK1 PE ABAJO → XPE 1 ARRIBA` | Hoja 11 C4: el (A-V/1mm2) va de la tierra de 11SK1 al círculo izquierdo de XPE 1. La bornera está dibujada en horizontal, así que el izquierdo es ARRIBA. Todo 11SK1 se cablea por abajo. En el topográfico (pág. 7, riel 1), XPE está en la bandeja, a la derecha de 62KR. |
| ⏚11PS1 (sin nº) | sin número | No figura en las líneas (sí está en `sin_numero`, hoja 11 C5) | `⏚11PS1: VA2.5MM 11PS1 ⏚-1 → XPE 1 ABAJO` | Hoja 11 C5: el (A-V/2,5mm2) va del círculo derecho de XPE 1 (ABAJO) al borne de tierra "1" de 11PS1. En las fotos 1.4 y 12.35.38 hay un verde-amarillo con puntera azul en la tierra de 11PS1. |
| ⏚13PS3 (sin nº) | sin número | No figura (el programa lo detectó en `sin_numero`, hoja 13 B7) | `⏚13PS3: VA1MM 13PS3 ⏚ → XPE 2 ARRIBA` | Hoja 13 B7: el (A-V/1mm2) une el borne de tierra de la entrada 12VDC de 13PS3 con el círculo izquierdo de XPE 2 (ARRIBA). Falta confirmar en el tablero: en la foto 1.6 hay verde-amarillos que entran a XPE por abajo. |
| 1306 | sobra | Pendiente fantasma `1306: 21PCB01 48 ↔ 21PCB01` (R1MM) | Hay que borrarlo. La línea `1306: R1MM 13XC1 2.4 → LI` (a 21PCB01 48) está bien. | Hoja 14 B3-B5: un solo 1306, que viene de Sh13:D3 y va a 21PCB01 48 (+Battery). La hoja 21 muestra ese mismo borne otra vez y el programa lo tomó como una segunda punta. |
| 1307 | sobra | Pendiente fantasma `1307: 21PCB01 49 ↔ 21PCB01` (N1MM) | Hay que borrarlo. La línea `1307: N1MM 13XC1 3.3 → LI` (a 21PCB01 49) está bien. | Hoja 14: un solo 1307, que va de Sh13:D5 a 21PCB01 49 (-Battery). |
| 2165 | sobra | Pendiente fantasma `2165: 21PCB01 ↔ 21PCB01 65` (N0.75MM) | Hay que borrarlo. La línea `2165: N0.75MM 81XCM 10 ARRIBA → LI` (a 21PCB01 65) está bien. | Hoja 62 F2-F4: DO8(NO) 65 → 2165 → `81XCM (Sh81:C4)`. Hoja 81: Sh62:F4 → 2165 → 81XCM 10. El borne 65 está dibujado en las hojas 21 y 62. |
| R 120 Ω (sin nº) | sin número | No figura | `R120Ω: 81XCM 11 ABAJO ↔ 81XCM 12 ABAJO` (resistencia de terminación del lado campo) | Hoja 81 E6: una resistencia de 120 Ω une 81XCM 11 y 12 del lado derecho (ABAJO). En la foto 12.35.44 (3) se ve una pata de la resistencia que entra por abajo en el módulo 11/12 de 81XCM. |

### Gravedad BAJA

| Cable | Tipo | En el instructivo | Cómo tiene que quedar | Evidencia |
|---|---|---|---|---|
| 1103 | falta punta | Pendiente `1103: ? ↔ 11XP 3 ABAJO` (VA2.5MM) | `1103: VA2.5MM 11XP 3 ABAJO ↔ TIERRA GABINETE (conexión interior)` | Hoja 11 C3-E3: el 1103 (A-V/2,5mm2) baja desde el círculo derecho de 11XP 3 hasta el punto "TIERRA GABINETE / CONEXIÓN INTERIOR". |
| 2128 | falta borne | Pendiente `2128: 41DS ↔ 21PCB01 28` | `2128: N0.75MM 41DS 1 ↔ 21PCB01 28` | Hoja 41 A3-A6: DI7+ 28 → 2128 → borne 1 (NC) de 41DS. La hoja 21 dice `41DS:1`. |
| 2129 | falta borne | Pendiente `2129: 41DS ↔ 21PCB01 29` | `2129: N0.75MM 41DS 2 ↔ 21PCB01 29` | Hoja 41 B3-B6: DI7- 29 → 2129 → borne 2 de 41DS. La hoja 21 dice `41DS:2`. |
| FBS 3-6 ROJO | puente sin nº | No figura | Check: `colocar FBS 3-6 ROJO en 62KR1/62KR2/62KR3 11 (C)` | Hoja 62 A5-D5: la vertical "FBS 3-6 ROJO" une C(11) de los 3 relés. El 1308 solo entra a 62KR1 11. El topográfico también lo muestra. |
| FBS 3-5 AZUL (62XDO) | puente sin nº | No figura | Check: `colocar FBS 3-5 AZUL en 62XDO 2-4-6` | Hoja 62 B6-D6: une 62XDO 2, 4 y 6 (común -0V). El 1321 solo entra a 62XDO 2. En la foto 12.35.39 (2) el puente es azul. **El topográfico lo dibuja ROJO: es un error del topográfico.** |
| FBS 3-5 AZUL (62XDIO) | puente sin nº | No figura | Check: `colocar FBS 3-5 AZUL en 62XDIO 1-2-3, del lado del ánodo (ABAJO, donde entra el 1315)` | Hoja 62 B6-D6: une el lado del ánodo de 62XDIO 1, 2 y 3. En la foto 12.35.39 (2) se ve el puente azul abajo. |
| FBS 4-6 AZUL | puente sin nº | No figura | Check: `colocar FBS 4-6 AZUL en 43KR1..43KR4 A2` | Hoja 43 B4-E4: une A2 de los 4 módulos 43KR. El 1328 solo entra a 43KR1 A2. |
| FBS 2-8 ROJO / FBS 2-8 AZUL | puente sin nº (lo encontré yo) | No figura | Check: `colocar FBS 2-8 ROJO en 13XC1 1-2` y `FBS 2-8 AZUL en 13XC1 3-4` | Hoja 13 C2-C5: 13XC1 1 y 2 (+12V) están unidos por un "FBS-2-8 ROJO", y 3 y 4 (-0V) por un "FBS-2-8 AZUL". El topográfico (pág. 7) los muestra igual. |

Los puentes FBS no son conductores y ya figuran en el topográfico, así que puede que se coloquen en el montaje. Pero si faltan, los circuitos no funcionan: 62KR2 y 62KR3 se quedan sin +12V, 43KR2 a 43KR4 sin -0V, etc. Convendría un check en el instructivo. Esto lo tiene que decidir el usuario.

## Diferencias descartadas

| Cable | Motivo |
|---|---|
| 2142 (31XAI 1 o 2) | El instructivo está bien porque sigue la hoja 31, que es el detalle: 2142 va al borne rotulado "1" y el fusible es "F1". La hoja 21 lo referencia como `31XAI:2`, seguramente porque cuenta F1 como la posición 1. Es una inconsistencia del propio plano y no hay que cambiar nada. |
| "Malla RS-485 Port #2 (sin número)" (h62_81) | Está repetida: esa malla es el cable **2134** (hoja 21, borne 34). Quedó unida a la fila del 2134. |
| "Malla RS-485 Port #1 (sin número)" (h62_81) | Está repetida: es el cable **2137** (hoja 21, borne 37). Quedó unida a la fila del 2137. |
| 1204/1215/1216 (reportados también por h21, h31_41 y h62_81) | Están repetidos y quedaron unidos. El "origen sin lado del fusible" está incluido en la línea corregida. |
| 2135/2136 (h21 y h62_81; h62_81 los marcó como "falta_cable") | Están repetidos. No falta el cable, falta una punta: el tramo 21PCB01↔12XPS. |
| 1306/1307 (h21), 2165 (h62_81), 2128/2129 (h31_41) | Están repetidos y quedaron unidos. |
| 2134/2137 "sección" (h21) | Quedó incluido en las filas de 2134 y 2137, como nota de sección para que la confirme el usuario. |

## Otras observaciones (no cambian el instructivo de E6)

- Hoja 21 contra hojas 62 y 81: las referencias de flecha de 2164 (`13XC1:3`) y 2165 (`62KR.2:A2`) están mal en la hoja 21. El destino real es 81XCM 9 y 10, y así está en el instructivo. La hoja 21 también manda 2135 y 2136 directo a 81XCM, sin pasar por 12XPS.
- En las hojas 12 y 81, los conductores 0,32 (Blanco, Amarillo, Negro y Rojo) de 12PS2 COM a 12XPS 7-10 no tienen número. Las dos puntas están fuera de la bandeja, así que no van en E6.
- En la hoja 14, la tierra A-V/1mm2 del display va a un tornillo en la puerta. Está fuera de la bandeja.
- La terminal doble en 12XPS 7 y 8 (0,32) y la puntera de la malla todavía no están en la tabla de terminales.json.

## Recortes usados
`verfun/verif/`: h11_tj.png, h11_xpe.png, h11_1103.png, h12_bat.png, h12_xps.png, h81_pcb.png, h81_xcm.png, h81_xps.png, h21_bot.png, h21_top.png, h13_ps3.png, h13_xc1.png, h43_z.png, h62_z.png, h41_z.png, h31_xai.png, topo7_r1.png, topo7_r2.png, ph14_q2.png, ph_xcm_top.png, ph_xcm_bot.png.
