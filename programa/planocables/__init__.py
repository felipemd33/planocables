"""planocables: listado de cables e instructivo de cableado del taller Batfer, como paquete (PLAN_MODULAR.md).

Se arma por etapas. Hoy (etapa 1) el paquete tiene solo la capa base/; el resto sigue en los modulos viejos de
programa/ (core, wires, textdec, topo, ruteo, eplan, instructivo, estacion8, bornes/, web), que importan de base/ lo
que se movio con el MISMO nombre de siempre (core.natkey, instructivo.fmt_terminal, topo.snap_escala...). Nada de
planocables importa un modulo viejo ni toca sys.path (pruebas/probar_capas.py).

QUE TOCAR (tabla «que tocar» del plan, seccion 3.9, con lo que existe hoy; [viejo] = todavia en el modulo viejo)

  Quiero cambiar...                          Donde                                                  Dato / parametro
  ------------------------------------------ ------------------------------------------------------ -------------------------------
  Letra SHX mal leida                        textdec.Decoder [viejo]                                glyphdict.json, ocr_cache.json
  Memoria OCR sin escribir (pruebas)         textdec.Decoder.save_cache [viejo]                     PLANOCABLES_MEMORIA_OCR=solo-lectura
  Numero que no se pega a su cable           wires.assign [viejo]                                   capas NON_WIRE_* de wires
  Color o seccion mal heredados              core.build_cable_list [viejo]                          -
  Nombre de un color, inicial ('N2.5MM')     planocables.base.colores                               -
  Hoja, zona, referencias (ShNN:XX), orden   planocables.base.hojas                                 -
  Tag, borne, QUATTRO o ARRIBA/ABAJO         instructivo.describe_end [viejo]                       -
  Formato del texto de la punta              planocables.base.convenciones.fmt_terminal             -
  Lado sin punto exacto (rele, fuente...)    planocables.base.convenciones.side_of                  -
  Color + seccion del tramo ('N2.5MM')       planocables.base.convenciones.cable_desc               -
  N-1 tramos, union en T                     instructivo.conductors [viejo]                         -
  EPLAN: cabecera, tipo de bornera, rotulo   eplan [viejo]                                          -
  Rieles y canaletas                         topo, ruteo.ducts, eplan.layout [viejos]               constantes de cada modulo
  Escala mm/pt, riel TS35                    planocables.base.escala                                -
  Modelo de bornera nuevo                    -                                                      bornes/catalogo.json
  Producto EPLAN verificado                  -                                                      mapeos_verificados/<doc>_rev<rev>.json
  Orden de cableado                          instructivo.build [viejo]                              -
  Lado fisico, punto exacto o aproximado     instructivo.build (lado_fisico, exacto) [viejo]        -
  E8 y 35 mm2                                instructivo.build, estacion8, web.gen_instructivo      estaciones_tag del mapeo
                                             [viejos]
  Salida a LI / LD                           ruteo.li_exit, instructivo.grupo_salida [viejos]       -
  Quitados y marcas al regenerar             instructivo.separar_quitados, web.gen_instructivo      -
                                             [viejos]
  Terminal o pollera                         web/instructivo.js (copia distinta en estacion8.js)    web/terminales.json
  Largos, giros, «fuera» de la WPC           web/wpc.js                                             web/wpc.json
  Secciones de la auditoria                  web/auditoria.js                                       -
  Candado de PDFium (uno solo)               planocables.base.pdfium_lock                           -
  Frases que se comparan entre modulos       tabla de protocolos (PLAN_MODULAR 1.2.8)               -

Cambiar una convencion del taller (formato de linea, lado, orden, estaciones...) hay que preguntarlo antes al usuario."""

__version__ = '0.1.0'
