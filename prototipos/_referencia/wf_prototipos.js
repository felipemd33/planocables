export const meta = {
  name: 'prototipos-mapeo-bornes',
  description: 'Verifica los bornes pendientes con la regla del tag a la derecha y construye 5 prototipos distintos de mapeo de bornes con base de datos, evaluados y comparados',
  phases: [
    { title: 'Verificar', detail: '4 verificadores escepticos: protecciones, borneras riel 2, borneras riel 3, barreras' },
    { title: 'Prototipos', detail: '5 enfoques distintos de mapeo con base de datos de bornes' },
    { title: 'Comparar', detail: 'critico: re-ejecuta, re-puntua, revisa honestidad y escribe COMPARACION.md' },
  ],
}

const REF = 'C:/Buscar Termos en plano/prototipos/_referencia'
const PROTO = 'C:/Buscar Termos en plano/prototipos'
const COMUN = `
CONTEXTO: taller Batfer (Uruguay) que arma tableros electricos. Hay un programa propio (C:/Buscar Termos en plano/programa, NO SE MODIFICA) que arma un instructivo de cableado a partir del funcional y dibuja el ruteo de cada cable sobre el plano TOPOGRAFICO de la bandeja. Para que el cable salga del punto exacto del borne hace falta ubicar cada borne en el dibujo. Hoy se hizo a mano con agentes para este tablero; el taller quiere un METODO reutilizable con una BASE DE DATOS DE BORNES (siempre usan los mismos modelos: Phoenix PT 6 QUATTRO, PTT 2,5, PTT 2,5-2MT, PT 2,5-DIO, reles RIF-0, fuentes MEAN WELL NDR/DDR, termomagneticas/diferenciales Schneider/ABB, portafusibles DF101, barreras CHENZHU GS85xx, etc.) para que en cada plano nuevo sea rapido.
LEE PRIMERO: ${REF}/LEEME.md (datos, reglas del taller obligatorias, formato de entrega). Datos: ${REF}/topografico.pdf (pagina PDF 8), ${REF}/usos_por_componente.json (entrada), ${REF}/lista_materiales.txt (modelos), ${REF}/bornes_referencia.json (respuesta de referencia, 145 puntos), ${REF}/evaluar.py (puntaje), ${REF}/codigo_agentes/ (codigo de los agentes que armaron la referencia), fotos reales en C:/Buscar Termos en plano/Cableado 75286-1/ .
REGLA MUY IMPORTANTE DEL TALLER: en el topografico una etiqueta (tag amarillo) nombra los bornes que estan a su DERECHA, hasta la etiqueta siguiente del mismo riel.
HERRAMIENTAS: Python con numpy, cv2 (OpenCV 5), PIL, pypdfium2, pypdf, shapely, sqlite3, onnxruntime (NO hay scipy/sklearn/skimage; NO instales paquetes). sys.path.insert(0, 'C:/Buscar Termos en plano/programa'); from pdfvec import page_strokes, layer_names. Para mirar: pypdfium2 render de la zona ampliada y abrir el PNG con Read; las fotos tambien con Read. Internet permitido solo lectura (hojas de datos/fotos de modelos): carga WebSearch/WebFetch con ToolSearch query "select:WebSearch,WebFetch"; no descargues ni ejecutes programas.
NO modifiques nada fuera de tu carpeta asignada. Escribe en castellano.`

const VERIF = [
  { key: 'protecciones', comps: '11Q1, 11Q2, 12F1, 13F3, 12F2, 31XAI' },
  { key: 'borneras_riel2', comps: '12XP, 13XC1, 13X24, 62XDIO, 62XDO' },
  { key: 'borneras_riel3', comps: '43XCS, 46XC, 81XCM, 31XEX, 43XDI' },
  { key: 'barreras', comps: '31AIB1, 43DIB1, 43DIB2' },
]
const VERIF_SCHEMA = {
  type: 'object',
  properties: {
    confirmados: { type: 'integer' },
    correcciones: { type: 'array', items: { type: 'object', properties: { texto: { type: 'string' }, cable: { type: 'string' }, x: { type: 'number' }, y: { type: 'number' }, confianza: { type: 'string' }, motivo: { type: 'string' } }, required: ['texto', 'cable', 'x', 'y', 'motivo'] } },
    errores_instructivo: { type: 'array', description: 'textos del instructivo que no coinciden con el funcional/fotos', items: { type: 'object', properties: { cable: { type: 'string' }, texto_instructivo: { type: 'string' }, correcto: { type: 'string' }, motivo: { type: 'string' } }, required: ['cable', 'texto_instructivo', 'correcto', 'motivo'] } },
    archivo_correcciones: { type: 'string' },
    comentario: { type: 'string' },
  },
  required: ['confirmados', 'correcciones', 'errores_instructivo', 'archivo_correcciones', 'comentario'],
}

const PROTOS = [
  { key: 'P1_catalogo_geometrico', idea: `CATALOGO DE MODELOS + DETECTOR GEOMETRICO GENERICO (reglas, sin aprendizaje). Base de datos JSON (catalogo.json) donde cada modelo describe: tipo (modular DIN, borne de riel por piezas, rele modular, fuente, barrera, toma), la FIRMA GEOMETRICA de sus bocas/tornillos en los bloques CAD de Batfer (primitiva: circulo de radio tal, poligono de n lados, abertura en U, elipse cortada; rangos de tamano), paso entre piezas en mm, cantidad y orden de bocas por pieza (extremo/interior, arriba/abajo), y el MAPA DE NOMBRES de pines (ej. NDR-120 TB2 = ['1 (-)','2 (-)','3 (+)','4 (+)']; QUATTRO N.p; PTT impar/par). Un motor unico: para cada tag toma la zona a la derecha hasta el proximo tag del mismo riel, detecta las bocas con la firma del modelo, agrupa por pieza/columna y nombra segun el catalogo. Agregar un modelo = agregar una entrada al JSON, sin tocar codigo.` },
  { key: 'P2_huella_bloques', idea: `HUELLAS DE BLOQUES CAD (reconocimiento vectorial). El topografico se dibuja con los mismos bloques de biblioteca (cada modelo tiene siempre el mismo dibujo). Base de datos: por modelo (o por PIEZA de bornera) una huella vectorial normalizada del bloque (por ejemplo conjunto de segmentos/arcos relativos a un ancla, histograma de largos/angulos, hashing geometrico) + los desplazamientos de cada borne respecto del ancla, aprendidos de un plano verificado (aprender.py lee bornes_referencia.json y genera la base; mapear.py SOLO lee la base). En un plano nuevo: busca instancias del bloque por coincidencia de huella (traslacion, y si se puede rotacion 90), y transfiere los bornes. HONESTIDAD: entrega ademas salida/bornes_loo.json + salida/evaluacion_loo.txt con validacion dejando-un-tag-afuera (para mapear el tag T, la base se aprende sin T; los modelos que aparecen una sola vez quedan sin punto en ese modo, y se informa).` },
  { key: 'P3_dimensiones_mm', idea: `HOJAS DE DATOS EN MILIMETROS (base SQLite). Base bornes.db con tablas modelo(fabricante, codigo, tipo, ancho_mm, alto_mm, paso_mm, ...) y borne(modelo, nombre, x_mm, y_mm respecto de una referencia del cuerpo, radio_mm, lado), cargadas con datos de las hojas de datos del fabricante (busca en internet: Phoenix, MEAN WELL, Schneider, ABB, CHENZHU) y medidas reales. mapear.py ubica el CUERPO del aparato en el dibujo (contorno junto al tag en su riel, regla del tag a la derecha), convierte mm a pt con la escala del plano (1.4086 mm/pt, o calculada de las cotas) y calcula cada borne. Es independiente del detalle del dibujo: sirve aunque el simbolo sea simplificado (como 11SK1). Incluye un CSV o script para cargar un modelo nuevo desde la hoja de datos.` },
  { key: 'P4_aprende_ejemplos', idea: `BASE QUE APRENDE DE TABLEROS VERIFICADOS (ejemplos). Base de ejemplos (JSON o SQLite): por modelo, las posiciones de los bornes NORMALIZADAS al recuadro del componente detectado en el dibujo (0..1) + un descriptor simple del dibujo (tamano, conteo de trazos). agregar_tablero.py suma a la base los puntos verificados de un tablero (por ejemplo los ajustados a mano en el visor del programa, que quedan en instructivo.json como bornes_usuario, o bornes_referencia.json); asi la base crece con cada tablero auditado. mapear.py detecta el recuadro de cada componente, elige el ejemplo mas parecido del mismo modelo y transfiere, y despues AJUSTA cada punto al centro de la boca/tornillo dibujado mas cercano (snap). HONESTIDAD: entrega salida/bornes_loo.json + salida/evaluacion_loo.txt dejando-un-tag-afuera (el tag evaluado no puede usar sus propios puntos).` },
  { key: 'P5_vision_imagen', idea: `VISION POR IMAGEN (OpenCV, sin depender de la estructura vectorial). Renderiza la pagina a alta resolucion; base de datos = plantillas de imagen chicas de cada TIPO de boca/tornillo (por modelo) + mapa de nombres + paso. Busca con cv2.matchTemplate + supresion de no-maximos dentro de la zona a la derecha de cada tag (regla del tag), agrupa por piezas y nombra por orden. Sirve para planos escaneados o de otro CAD. Las etiquetas de los tags se pueden tomar de usos_por_componente.json. HONESTIDAD: si las plantillas se recortan de este mismo plano, usa una plantilla por TIPO de boca aplicada a muchos tags, y documenta de que tag salio cada plantilla; informa el acierto en los tags que NO aportaron plantilla.` },
]
const PROTO_SCHEMA = {
  type: 'object',
  properties: {
    carpeta: { type: 'string' }, enfoque: { type: 'string' },
    acierto: { type: 'number', description: 'fraccion BIEN segun evaluar.py (modo normal)' },
    acierto_loo: { type: 'number', description: 'si aplica, acierto dejando-un-tag-afuera' },
    cobertura: { type: 'number' }, segundos: { type: 'number' },
    base_de_datos: { type: 'string', description: 'ruta y formato' },
    como_agregar_modelo: { type: 'string' }, limitaciones: { type: 'string' }, siguiente_paso: { type: 'string' },
  },
  required: ['carpeta', 'enfoque', 'acierto', 'cobertura', 'segundos', 'base_de_datos', 'como_agregar_modelo', 'limitaciones', 'siguiente_paso'],
}

// verificacion en paralelo con los prototipos (el critico la necesita toda)
const verifP = parallel(VERIF.map(v => () => agent(`Eres VERIFICADOR ESCEPTICO de puntos de conexion de bornes en un plano topografico. Familia: ${v.key} (componentes ${v.comps}).
${COMUN}
Los puntos a verificar son los de ${REF}/bornes_referencia.json con familia == "${v.key}" (lee tambien sus 'como', 'reglas' y 'dudas' de esa familia). Nadie los reviso todavia.
TU TRABAJO: comprobar INDEPENDIENTEMENTE cada punto: renderiza tu mismo la zona ampliada, extrae la geometria con page_strokes, consulta la hoja de datos del modelo si hace falta y mira las fotos reales. Verifica que cada punto cae sobre la boca/tornillo correcto: (1) REGLA DEL TAG: las piezas de cada componente son las que estan a la DERECHA de su etiqueta hasta la etiqueta siguiente del mismo riel (revisa que no se hayan asignado piezas del componente vecino); (2) numeracion de piezas desde la etiqueta, sin topes ni PE; (3) punto dentro de la pieza (QUATTRO p1..p4, doble piso impar/par, arriba/abajo); (4) posicion fisica real (el toma 11SK1 se cablea TODO por abajo; en barreras y bornes con diodo el ARRIBA/ABAJO del texto puede venir del dibujo del funcional). Para cada punto equivocado da la correccion con coordenadas exactas (centro de la boca) y el motivo.
ESCRIBE el archivo ${REF}/correcciones_${v.key}.json con {"familia": "${v.key}", "correcciones": [{"texto", "cable", "x", "y", "confianza", "motivo"}]} (lista vacia si todo esta bien). Tu carpeta de trabajo para scripts/imagenes: ${REF}/verif_${v.key}/ . Ademas lista en errores_instructivo los textos del instructivo que no coinciden con el funcional (tag o borne equivocado, lado, cables que faltan), con el texto correcto.`,
  { label: `verificar:${v.key}`, phase: 'Verificar', schema: VERIF_SCHEMA })))

phase('Prototipos')
const protos = await pipeline(PROTOS, p => agent(`Eres un ingeniero que construye un PROTOTIPO de metodo de mapeo de bornes. Tu prototipo: ${p.key}.
ENFOQUE (obligatorio, es distinto de los otros 4 prototipos que hacen otras personas): ${p.idea}
${COMUN}
IMPORTANTE: si tu carpeta ${PROTO}/${p.key}/ ya tiene trabajo de un intento anterior (se corto por limite de uso), CONTINUALO: lee lo que hay, corre evaluar.py y completa solo lo que falta; no empieces de cero ni rehagas lo que ya funciona.
ENTREGA en la carpeta ${PROTO}/${p.key}/ exactamente lo que pide la seccion "Que tiene que entregar cada prototipo" de ${REF}/LEEME.md: LEEME.md (castellano claro para el taller: idea, como funciona, como se usa, COMO SE AGREGA UN MODELO NUEVO a la base, resultados con el puntaje, limitaciones, que haria falta para llevarlo al programa), la base de datos de bornes de tu enfoque cubriendo todos los modelos de este tablero, mapear.py (uso: python mapear.py <topografico.pdf> <usos_por_componente.json> <salida.json>, menos de 60 s, sin coordenadas de este tablero en el codigo), salida/bornes.json (con r = radio del borne en pt para cada punto), salida/control.png (mira la imagen para comprobar) y salida/evaluacion.txt (python ${REF}/evaluar.py salida/bornes.json). mapear.py NO puede leer bornes_referencia.json (salvo que tu enfoque lo diga explicitamente para aprender, y entonces en un paso aparte). Itera hasta que el puntaje sea lo mejor posible SIN hacer trampa (nada de copiar coordenadas de la referencia). Al final corre todo de nuevo desde cero para confirmar que funciona.`,
  { label: `prototipo:${p.key}`, phase: 'Prototipos', schema: PROTO_SCHEMA }))

const verifs = await verifP
phase('Comparar')
const resumenV = verifs.map((v, i) => v ? { familia: VERIF[i].key, confirmados: v.confirmados, correcciones: v.correcciones.length, archivo: v.archivo_correcciones } : { familia: VERIF[i].key, error: 'fallo' })
const final = await agent(`Eres el CRITICO que compara 5 prototipos (si ${PROTO}/_critico/ o COMPARACION.md ya tienen trabajo de un intento anterior, continualo) de mapeo de bornes y le deja al jefe de taller un informe para revisar manana (no va a estar para responder preguntas).
${COMUN}
Prototipos (carpetas en ${PROTO}/): ${JSON.stringify(protos.map((r, i) => r ? { ...r, key: PROTOS[i].key } : { key: PROTOS[i].key, error: 'el agente fallo' }))}
Verificacion de la referencia: ${JSON.stringify(resumenV)} (las correcciones quedaron en ${REF}/correcciones_*.json y evaluar.py ya las aplica).
TU TRABAJO: (1) para cada prototipo, RE-EJECUTA mapear.py desde cero en una carpeta temporal tuya (${PROTO}/_critico/), mide el tiempo y puntua con evaluar.py (con las correcciones ya aplicadas); (2) revisa la HONESTIDAD: que mapear.py no lea bornes_referencia.json ni tenga coordenadas del tablero escritas (busca numeros tipo 612.95 en el codigo y en la base), y en los que aprenden, usa el puntaje dejando-un-tag-afuera; (3) prueba de robustez: copia la base de cada prototipo y sacale un modelo; mapear.py no debe romperse (debe avisar); (4) mira las imagenes de control; (5) escribe ${PROTO}/COMPARACION.md en castellano claro: tabla (acierto, acierto honesto, cobertura, tiempo, que hace falta para agregar un modelo, fortalezas, debilidades), por que falla cada uno donde falla, y una RECOMENDACION concreta de que combinar para llevar al programa (por ejemplo catalogo + medidas + aprendizaje de los ajustes manuales del visor), con los pasos. Tambien ${PROTO}/LEEME.md cortito: que es cada carpeta y por donde empezar a leer. Devuelve un resumen.`,
  { label: 'comparar', phase: 'Comparar', schema: { type: 'object', properties: { ranking: { type: 'array', items: { type: 'object', properties: { prototipo: { type: 'string' }, acierto: { type: 'number' }, acierto_honesto: { type: 'number' }, segundos: { type: 'number' }, honesto: { type: 'boolean' }, nota: { type: 'string' } }, required: ['prototipo', 'acierto', 'honesto', 'nota'] } }, recomendacion: { type: 'string' }, informe: { type: 'string' } }, required: ['ranking', 'recomendacion', 'informe'] } })

return { verificacion: verifs.map((v, i) => ({ familia: VERIF[i].key, ...(v || { error: 'fallo' }) })), prototipos: protos, comparacion: final }
