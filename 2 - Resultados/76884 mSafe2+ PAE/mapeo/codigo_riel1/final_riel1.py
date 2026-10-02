# -*- coding: utf-8 -*-
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_riel1 as B

OUT = os.path.join(B.MAPEO, 'puntos_riel1.json')
pts = B.main()
dudas = [
    "42KS1 (Phoenix PSR-SCP-24UC/ESA2/4X1/1X2/B, 2963802): la disposicion fisica NO es la del esquema de caja (13 23 33 43 arriba / 14 24 34 44 abajo) que usa aparatos.json. "
    "Fotos del aparato real (enchufes rotulados y rotulo frontal de la carcasa): ARRIBA enchufe trasero (fila exterior, y=687.10) A1 S34 S33 S11 y enchufe delantero (fila interior, y=680.58) S12 51 52 A2; "
    "ABAJO los 8 contactos de habilitacion: rotulo 43|44|13|14 sobre 33|34|23|24. Tome 43 44 13 14 = fila interior (y=634.23) y 33 34 23 24 = fila exterior (y=627.10) leyendo el rotulo como mapa (igual que arriba, donde la fila de arriba del rotulo es el enchufe de mas arriba). "
    "Si en el aparato es al reves, se intercambian las dos filas de abajo (1394/1395/4294/4295 <-> 2114/2115/1396/4296). Por eso esos 8 puntos van con confianza media. Habria que corregir puntos_eplan de aparatos.json. Fotos: https://industrialpartsrus.com/phoenix-contact-psr-scp-24uc-esa2-4x1-1x2-b-safety-relay-250v-ac-24v-ac-dc/ y https://sigmasurplus.com/phoenix-contact-psr-scp-24uc-esa2-4x1-1x2-b-relay/ (rotulo 'PSR-SCP- 24UC/ESA2/4X1/1X2/B Ord.No. 2963802' en el costado).",
    "42KS1: 8 filas de la lista dicen solo '-42KS1' (2114, 2115, 1394, 1395, 1396, 4294, 4295, 4296); el pin sale del esquema hoja 42 (13, 14, 23, 33, 43, 24, 34, 44). En cada punto queda 'd' tal cual y 'd_usada' con el pin.",
    "4221 (Negro 0,75) es un puente S33-S34 del mismo 42KS1: los dos tornillos son vecinos en el enchufe trasero de arriba (x 834.95 y 838.49). Va como cable corto (2 puntos).",
    "61KR1..61KR4: la hoja 8 solo rotula '-61KR' sobre el tope; el orden de los modulos de izquierda a derecha (61KR1 el primero) es supuesto, como en el 75286 y el 66817. Confianza media en los 20 puntos de 61KR; dentro de cada modulo la boca (11/14/12 arriba, A1/A2 abajo) es segura.",
    "Las filas '-61KRn -61KRn' de la lista (sin numero ni color) son los puentes internos del zocalo RIF-0 (segundo punto de A2- y de 11 del simbolo, hoja 61): no son cables y no tienen punto.",
    "13PS1 -Vo y (-Vo): el plano (hoja 13) llama a los dos tornillos -Vo de TB2 '-Vo' y '(-Vo)'. Se uso la regla del n-esimo pin (66817): 1312 (-Vo, a 13X24V 3.1) en el pin 1 y 1235 ((-Vo), a 12XP 1.2) en el pin 2. Son el mismo potencial; confianza media.",
    "32XAI (PTTB 4-HESI): EPLAN no da el punto ('-32XAI:F1' y '-32XAI:1' en las dos puntas). Lado por la hoja 32 (cable del tablero arriba, PT001 abajo); piso por la referencia 75286 (31XAI, mismo articulo, foto con 2142 en la boca de mas arriba): 1 = bocas del extremo, F1 = bocas interiores.",
    "3221 y 3222 (32XAI F1 ABAJO y 1 ABAJO) van a PT001 x1/x2 en la zona hidraulica: se mapea la punta de 32XAI y el otro extremo es E8 (campo otro_zona).",
    "1202 (Rojo 6 mm2, 12F3 ABAJO -> 12PB1 (+), bateria): 12PB1 no esta en el topografico (piso del gabinete). Lo deje como 'LI'; confirmar si este cable se hace en E8 como los de 35 mm2.",
    "XPE: la tierra de 13PS1 (PE abajo, en TB1) llega a XPE 1.1 (ARRIBA extremo) segun la lista y el simbolo de la hoja 13; las de 11PS1/11PS2 (FG abajo) a XPE 1.4 y 2.4 (ABAJO extremo). Los 4 puntos de cada pieza son PE; si el taller prefiere entrar 13PS1 por abajo (1.3/1.4) es solo cambiar el punto.",
    "11PS1/11PS2 TB2 pins 2 (-V) y 4 (+V) y 13PS1 (+Vo) quedan libres (la lista usa siempre el primer tornillo de cada polaridad).",
    "Radios r: tornillos de fuentes 1.52 (TB2 NDR) / 1.81 (TB1 NDR) / 1.42-1.52 (DDR), portafusibles 2.13 (DF101) y 2.5 (DF141), 42KS1 1.42, RIF-0 1.45, PTTB 2.06, QUATTRO-PE 1.70 (medidos en el dibujo).",
]
meta = {
    "documento": "ZPL-76884 Rev 1 - mSafe2+ PAE (EPLAN), pagina PDF 8 'Detalle bandejas'",
    "zona": "BANDEJA PRINCIPAL, riel 1 (U10, eje y=657.25): 11PS1, 11PS2, 13PS1, 11F1, 11F2, 12F3, 13F4, 13F5, 13F6, 42KS1, 42KR1, 61KR1-61KR4, 32XAI, XPE",
    "unidades": "x, y = centro de la boca push-in o del tornillo en pt de la pagina 8 (1192.04 x 851.39), origen abajo-izquierda; r = radio de la boca en pt",
    "fuente_conexiones": "conexiones.json (lista de conexiones pags 47-50); un punto por (designacion, cable)",
    "otro_zona": "riel1 = el otro extremo tambien es de este riel; bandeja = otro riel de la bandeja principal; LI = fuera de la bandeja principal (lateral izquierda, puerta, bateria); E8 = zona hidraulica (se cablea en E8)",
    "n_puntos": len(pts),
    "control": "control_riel1.png",
}
json.dump({"_meta": meta, "puntos": pts, "dudas": dudas}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(OUT, len(pts))
