# Arreglos del mapeo automatico de bornes que quedaron a medias (2026-10-02)

El usuario pauso esta tanda. El programa quedo en la version integrada y verificada (66817 104/104, 75286 140/140,
75287 identico). Estos archivos son la version A MEDIO HACER, SIN VERIFICAR: no copiarlos al programa tal cual.
Sirven para retomar los arreglos: comparar con programa/ (diff) y rehacer cada uno con su prueba.

Hallazgos que motivaron los arreglos (de los verificadores):
- Sin lista de materiales, diferencial y termomagnetica empatan: 11Q2 sale con F/N cambiados y confianza alta (deberia ser media).
- Rele UNICO sin numero de modulo ('43KR 11') se renombra a '43KR1 11'.
- bornes_usuario (puntos ajustados a mano con 📍) se ignoran si el mapeo renombra ese texto#cable.
- Etiqueta con x/y None en los usos tumba el mapeo entero.
- bornes.json / correcciones.json con JSON invalido tumban gen_instructivo.
- La firma del cache usa tamano+fecha del topografico (no el contenido) y solo VERSION del motor.
- Aviso enganoso cuando la lista de materiales trae un modelo que no esta en el catalogo.
- usos_bandeja no incluye conductores sin 'pares' ni las lineas 'agregar' de correcciones.json.
- 32XAIB/43XDIB (borneras azules) se toman como banco de barreras ('IB').
- Falta avisar los textos cuyo ARRIBA/ABAJO difiere del funcional (lado fisico).
- ruteo.py: cables azules intrinsecos salen en horizontal por encima de otros bornes (parece que salen de otro borne).
