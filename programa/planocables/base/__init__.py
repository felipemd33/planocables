"""Capa base de planocables: lo que usan todos los demas. SOLO biblioteca estandar y sin imports de otras partes del
paquete ni de los modulos viejos de programa/ (lo controla pruebas/probar_capas.py).

  geom          bbox, DSU, distancias (punto, segmento, caja), dentro, rect_of
  hojas         numero de hoja, zona, referencias (ShNN:XX), orden natural, H_REF
  convenciones  texto de las puntas (fmt_terminal), borneras, lado, 'N2.5MM' (cable_desc), claves de tramo
  colores       nombres de color, inicial del instructivo, colores en ingles
  escala        mm/pt normalizado (snap_escala), riel TS35
  pdfium_lock   el candado unico de PDFium"""
