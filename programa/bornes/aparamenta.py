# -*- coding: utf-8 -*-
"""Aparamenta del taller (Excel "BOMs por estacion" de SAP) <-> catalogo de bornes.

aparamenta.json tiene cada material del Excel (codigo SAP, texto, estacion, productos) con lo que es: clase, fabricante,
modelo comercial, codigo del fabricante y el modelo de catalogo.json que lo ubica en el topografico ('catalogo').
El Excel se va actualizando (se retroalimenta solo): al importarlo de nuevo se conservan las identificaciones y los
codigos nuevos quedan para revisar.

uso:
    python aparamenta.py                      informe: que aparatos de la bandeja no tienen modelo en el catalogo
    python aparamenta.py "<BOMs Por Estacion.xlsx>"   importa el Excel (actualiza aparamenta.json) y da el informe
"""
import os
import re
import sys
import json
from datetime import date

AQUI = os.path.dirname(os.path.abspath(__file__))
APARAMENTA = os.path.join(AQUI, 'aparamenta.json')
CATALOGO = os.path.join(AQUI, 'catalogo.json')

# campos que vienen del Excel (se pisan al importar); el resto es la identificacion (se conserva)
CAMPOS_EXCEL = ('texto', 'estacion', 'pickeo', 'productos')

# clase por palabras del texto, para los codigos nuevos (gana la primera que coincide)
REGLAS_CLASE = [
    ('etiqueta', r'ETIQUETA|CARTEL|PLACA IDENT|JUEGO DE PLACAS'),
    ('hidraulica', r'MANIFOLD|MANG\.|RECTO |CODO|ADAPTADOR|TAP[OÓ]N|ORING|ARANDELA|ACUMULADOR|DESFOGUE|MAN[OÓ]M|'
                   r'FILTRO AIRE|VALV\. DE RETENCION|ORIFICIO|PASACHAPA|CETOP|TAPA CIEGA'),
    ('mecanica', r'GABINETE|SOPORTE|SEPARADOR|PRENSACABLE|PORTAPLANOS|CORREA|PROTECCION|VENTEO|CHAPA'),
    ('fusible', r'FUSIBLE'),
    ('cable', r'^CABLE|CUBRE TERMINAL|TERMINALES DE BATERIA'),
    ('accesorio de bornera', r'TAPA (FINAL|PARA BORNE)|EXTREMO|PUENTE'),
    ('bornera', r'BORNE'),
    ('puerta', r'PULSADOR|SELECTORA|HONGO|SECCIONADOR|BLOQUE CONTACTO|FINAL DE CARRERA'),
    ('campo', r'V[AÁ]LV|SENSOR|TRANS\.|TRANSMISOR|UNIDAD HIDR'),
    ('aparato', r'REL[EÉ]|FUENTE|INTERRUPTOR|DISYUNTOR|PORTAFUSIBLE|M[OÓ]DULO|TOMA|BARRERA|CARGADOR|MPPT|ELEVADOR|CONVERSOR'),
]

# clases con bornes que se cablean en la bandeja (E6): necesitan un modelo en el catalogo
CLASES_CON_BORNES = ('bornera', 'aparato')


def clase_por_texto(texto):
    t = str(texto or '').upper()
    for clase, rx in REGLAS_CLASE:
        if re.search(rx, t):
            return clase
    return None


def leer_excel(path):
    """Renglones del Excel: [{codigo, texto, estacion, pickeo, productos}] (primera hoja, encabezado en la fila 1)."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    filas = list(ws.iter_rows(values_only=True))
    enc = [str(c or '').strip().lower() for c in filas[0]]

    def col(*claves):
        for i, c in enumerate(enc):
            if any(k in c for k in claves):
                return i
        return None
    ic, it = col('material'), col('texto')
    ie, ip, ipr = col('estaci'), col('pickeo'), col('producto')
    out = []
    for f in filas[1:]:
        if ic is None or not f[ic]:
            continue
        estacion = str(f[ie] or '').strip() if ie is not None else ''
        out.append(dict(codigo=str(f[ic]).strip(), texto=str(f[it] or '').strip() if it is not None else '',
                        estacion=estacion, pickeo=str(f[ip] or '').strip() if ip is not None else '',
                        productos=[p.strip() for p in str(f[ipr] or '').split(',') if p.strip()] if ipr is not None else []))
    return out


def cargar(path=APARAMENTA):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def guardar(datos, path=APARAMENTA):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
        f.write('\n')


def importar(excel, datos):
    """Pasa el Excel a aparamenta.json: actualiza texto, estacion y productos; conserva la identificacion; los codigos
    nuevos entran con la clase por palabras y 'revisar'; los que ya no estan en el Excel quedan con 'en_excel': false.
    Devuelve (nuevos, quitados)."""
    mats = datos.setdefault('materiales', {})
    vistos, nuevos = set(), []
    for r in leer_excel(excel):
        c = r['codigo']
        vistos.add(c)
        m = mats.get(c)
        if m is None:
            m = mats[c] = dict(clase=clase_por_texto(r['texto']), catalogo=None, revisar=True,
                               nota='codigo nuevo del Excel: identificar (fabricante, modelo y modelo del catalogo)')
            nuevos.append(c)
        for k in CAMPOS_EXCEL:
            m[k] = r[k]
        m.pop('en_excel', None)
    quitados = [c for c in mats if c not in vistos]
    for c in quitados:
        mats[c]['en_excel'] = False
    datos['materiales'] = dict(sorted(mats.items()))
    datos['importado'] = dict(archivo=os.path.basename(excel), fecha=date.today().isoformat(), materiales=len(vistos))
    return nuevos, quitados


def informe(datos, catalogo):
    """Controles cruzados con catalogo.json. Devuelve una lista de renglones de texto."""
    modelos = {m['id']: m for m in catalogo['modelos']}
    mats = datos.get('materiales', {})
    out = []
    malos = [(c, m['catalogo']) for c, m in mats.items() if m.get('catalogo') and m['catalogo'] not in modelos]
    if malos:
        out.append('Materiales que apuntan a un modelo que no esta en catalogo.json:')
        out += [f'  {c}: {mid}' for c, mid in malos]
    sin_sap = [(c, m['catalogo']) for c, m in mats.items()
               if m.get('catalogo') in modelos and c not in (modelos[m['catalogo']].get('sap') or [])]
    if sin_sap:
        out.append('Codigos SAP que faltan en el campo "sap" de su modelo del catalogo:')
        out += [f'  {c} -> {mid}' for c, mid in sin_sap]
    sin_modelo = [(c, m) for c, m in mats.items() if m.get('clase') in CLASES_CON_BORNES and not m.get('catalogo')
                  and m.get('en_excel', True) and str(m.get('estacion', '')).upper() in ('E6', 'E4', '')]
    faltan = [(c, m) for c, m in sin_modelo if not m.get('motivo_sin_modelo')]
    if faltan:
        out.append('Aparatos con bornes de la bandeja (E6) SIN modelo en el catalogo (sus cables quedan en la etiqueta):')
        out += [f"  {c}: {m.get('texto')} -> {m.get('modelo') or '?'}" for c, m in faltan]
    a_proposito = [(c, m) for c, m in sin_modelo if m.get('motivo_sin_modelo')]
    if a_proposito:
        out.append('Sin modelo a proposito (no hace falta para el instructivo de la bandeja):')
        out += [f"  {c}: {m.get('modelo') or m.get('texto')}: {m['motivo_sin_modelo']}" for c, m in a_proposito]
    rev = [c for c, m in mats.items() if m.get('revisar')]
    if rev:
        out.append('Codigos para revisar (nuevos del Excel, sin identificar):')
        out += [f"  {c}: {mats[c].get('texto')} (clase por palabras: {mats[c].get('clase')})" for c in rev]
    viejos = [c for c, m in mats.items() if m.get('en_excel') is False]
    if viejos:
        out.append('Codigos que ya no estan en el Excel: ' + ', '.join(viejos))
    if not out:
        out.append('Todo en orden: cada aparato con bornes del Excel tiene su modelo en el catalogo.')
    return out


def modelo_de_sap(codigo, catalogo=None):
    """Modelo del catalogo de un codigo SAP (o None)."""
    catalogo = catalogo or json.load(open(CATALOGO, encoding='utf-8'))
    for m in catalogo['modelos']:
        if codigo in (m.get('sap') or []):
            return m
    return None


def main(argv):
    datos = cargar() if os.path.exists(APARAMENTA) else dict(materiales={})
    catalogo = json.load(open(CATALOGO, encoding='utf-8'))
    if len(argv) > 1:
        nuevos, quitados = importar(argv[1], datos)
        guardar(datos)
        print(f"Importado {argv[1]}: {datos['importado']['materiales']} materiales, {len(nuevos)} nuevos, "
              f"{len(quitados)} que ya no estan.")
    print('\n'.join(informe(datos, catalogo)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
