import json
MOT_ARR = ("GS8512-EX.22: en la vista lateral acotada del manual CZ.GS8512-EX.11(S)E-5.0 (pag. 3, cotas 106.0/99.0 mm) "
           "el enchufe trasero inclinado [1 2] y el del medio [3 4] tienen el tornillo a la MISMA altura (193.26 y 192.72 pt del manual); "
           "la foto del fabricante muestra el [2 1] inclinado sobresaliendo igual que el del medio, y en la foto 3.0 el desnivel aparente "
           "entre [3 4] y [1 2] se explica solo por la profundidad (35 mm). La vista frontal del manual con 3 filas parejas es esquematica. "
           "Por eso el borne %s va en la fila EXTERIOR dibujada (la misma y que 1/2, tapado por detras), no una fila mas adentro. "
           "El punto de la referencia (y=560.22) cae justo sobre el enchufe delantero [5 6] (borne %s).")
MOT_56 = ("GS8512-EX.22: el enchufe delantero [5 6] (el de adelante, pegado a la etiqueta, fotos 3.1 y 12.35.42) esta UNA fila hacia adentro "
          "de la fila exterior dibujada, no dos: 12.33 pt del manual = 8.85 mm = 6.28 pt del topografico (vista lateral acotada del manual). "
          "y = 567.05 - 6.28. El punto de la referencia (y=553.58) queda debajo del borde superior del frente del aparato (muesca dibujada "
          "en y 555-559.5), sobre la tapa de la etiqueta, donde no hay bornes. Borne %s = tornillo %s del enchufe (foto: %s).")
C = [
 dict(texto="43DIB1 3", cable="1318", x=798.20, y=567.05, confianza="media", motivo=MOT_ARR % ("3", "5")),
 dict(texto="43DIB2 3", cable="1319", x=807.15, y=567.05, confianza="media", motivo=MOT_ARR % ("3", "5")),
 dict(texto="43DIB1 5", cable="2116", x=798.20, y=560.77, confianza="media", motivo=MOT_56 % ("5", "izquierdo", "2116 en el 5")),
 dict(texto="43DIB1 6", cable="2117", x=801.75, y=560.77, confianza="media", motivo=MOT_56 % ("6", "derecho", "2117 en el 6")),
 dict(texto="43DIB2 5", cable="2120", x=807.15, y=560.77, confianza="media", motivo=MOT_56 % ("5", "izquierdo", "2120 en el 5")),
 dict(texto="43DIB2 6", cable="2121", x=810.70, y=560.77, confianza="media", motivo=MOT_56 % ("6", "derecho", "2121 en el 6")),
]
json.dump({"familia": "barreras", "correcciones": C}, open('correcciones_barreras.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(C))
