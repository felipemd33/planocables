# Referencia de puntos de borne del tablero 66817 (mSafe NC)

Topografico 66817-1.08, bandeja en la pagina PDF 4, escala 1.7639 mm/pt. Funcional 66817-1.07.
Planos en G:\...\ORDENES DE TRABAJO\20061911 - mSafe NC - 14un\.

- `bornes_referencia.json`: 104 puntos (uno por uso texto + cable de la bandeja). Los armaron agentes el 2026-10-02 con
  el dibujo vectorial, el funcional, las fotos reales del tablero cableado (G:\...\Fotos soporte E06\66817-1) y las hojas
  de datos. Cada punto explica en `como` de donde sale.
- `correcciones_<familia>.json`: lo que corrigio el verificador de cada familia. evaluar2.py las aplica solo.
- `ref_<familia>.json`: lo que armo cada constructor, con sus dudas.
- `control_*.png` / `verif_*.png`: cada punto marcado sobre el dibujo.
- `usos_por_componente.json`: la entrada de los mapeadores (que borne lleva cable).

Puntaje de un mapeo: `python evaluar2.py <salida.json> --ref bornes_referencia.json --no-guardar`.
Sin `--ref` usa la referencia del 75286 (`..\_referencia`).

Ojo: las barreras 32AIB1 y 43DIB1 estan dibujadas con un bloque simbolico que no muestra sus bornes. Sus 20 puntos son
una convencion (centro de la carcasa + posicion real del borne con paso de 5 mm, fila dibujada segun el escalonado real),
con confianza media. El lado, el enchufe y el orden estan confirmados con fotos.
