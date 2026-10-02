"""Arma la base de datos de bornes (bornes.db, SQLite) a partir de las planillas de datos/.

    python cargar_base.py            -> recrea bornes.db desde datos/modelos.csv y datos/bornes.csv
    python cargar_base.py --listar   -> muestra lo que hay en la base

Las planillas se editan con Excel o con el bloc de notas (separador ';', UTF-8). Despues de agregar o
corregir un modelo se vuelve a correr este script. Controla que:
  * cada modelo tenga medidas y al menos un borne;
  * cada borne quede dentro del cuerpo (se admite hasta 15 mm afuera: enchufes que sobresalen);
  * no haya dos bornes con el mismo nombre en un modelo;
  * el tipo y la regla sean de los conocidos.

Tablas:
  modelo(codigo, fabricante, tipo, regla, ancho_mm, alto_mm, ancho_hoja_mm, alto_hoja_mm, tol_pct, color,
         ignora_lado_texto, lado_puente, alias_bom, descripcion, fuente)
  borne(modelo, nombre, alias, x_mm, y_mm, radio_mm, lado, fuente)
x_mm se mide desde el borde IZQUIERDO del cuerpo e y_mm desde el borde de ARRIBA (hacia abajo), en la vista
frontal tal como se dibuja en el topografico (riel horizontal).
"""
import csv, os, sqlite3, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(AQUI, 'bornes.db')
TIPOS = {'aparato', 'pieza'}
REGLAS = {'nombre', 'cuatro_puntos', 'dos_pisos', 'diodo', 'fusible', 'modulo'}


def _num(v, campo, fila, obligatorio=True):
    v = (v or '').strip().replace(',', '.') if campo.endswith('_mm') or campo == 'tol_pct' else (v or '').strip()
    if v == '':
        if obligatorio:
            raise ValueError('fila %s: falta %s' % (fila, campo))
        return None
    return float(v)


def leer_csv(nombre):
    with open(os.path.join(AQUI, 'datos', nombre), encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter=';'))


def armar(base=BASE):
    modelos = leer_csv('modelos.csv')
    bornes = leer_csv('bornes.csv')
    errores, avisos = [], []
    M = {}
    for i, m in enumerate(modelos, 2):
        c = m['codigo'].strip()
        if not c:
            continue
        if c in M:
            errores.append('modelos.csv fila %d: codigo repetido %s' % (i, c))
        if m['tipo'] not in TIPOS:
            errores.append('modelos.csv fila %d (%s): tipo "%s" no es %s' % (i, c, m['tipo'], sorted(TIPOS)))
        if m['regla'] not in REGLAS:
            errores.append('modelos.csv fila %d (%s): regla "%s" no es %s' % (i, c, m['regla'], sorted(REGLAS)))
        try:
            fila = dict(codigo=c, fabricante=m['fabricante'].strip(), tipo=m['tipo'].strip(), regla=m['regla'].strip(),
                        ancho_mm=_num(m['ancho_mm'], 'ancho_mm', i), alto_mm=_num(m['alto_mm'], 'alto_mm', i),
                        ancho_hoja_mm=_num(m['ancho_hoja_mm'], 'ancho_hoja_mm', i, False),
                        alto_hoja_mm=_num(m['alto_hoja_mm'], 'alto_hoja_mm', i, False),
                        tol_pct=_num(m['tol_pct'], 'tol_pct', i, False) or 5.0, color=(m['color'] or '').strip(),
                        ignora_lado_texto=int((m['ignora_lado_texto'] or '0').strip() or 0),
                        lado_puente=(m['lado_puente'] or '').strip(), alias_bom=(m['alias_bom'] or '').strip(),
                        descripcion=(m['descripcion'] or '').strip(), fuente=(m['fuente'] or '').strip())
        except ValueError as e:
            errores.append('modelos.csv ' + str(e)); continue
        for dh, db_, nom in ((fila['ancho_hoja_mm'], fila['ancho_mm'], 'ancho'), (fila['alto_hoja_mm'], fila['alto_mm'], 'alto')):
            if dh and abs(dh - db_) / dh > 0.03:
                avisos.append('%s: el %s del bloque (%.1f mm) no es el de la hoja de datos (%.1f mm)' % (c, nom, db_, dh))
        M[c] = fila
    B, vistos = [], set()
    for i, b in enumerate(bornes, 2):
        mod = b['modelo'].strip()
        if not mod:
            continue
        if mod not in M:
            errores.append('bornes.csv fila %d: el modelo %s no esta en modelos.csv' % (i, mod)); continue
        k = (mod, b['nombre'].strip())
        if k in vistos:
            errores.append('bornes.csv fila %d: borne repetido %s %s' % (i, *k))
        vistos.add(k)
        try:
            x, y = _num(b['x_mm'], 'x_mm', i), _num(b['y_mm'], 'y_mm', i)
            r = _num(b['radio_mm'], 'radio_mm', i, False) or 1.5
        except ValueError as e:
            errores.append('bornes.csv ' + str(e)); continue
        m = M[mod]
        if not (-15 <= x <= m['ancho_mm'] + 15 and -15 <= y <= m['alto_mm'] + 15):
            errores.append('bornes.csv fila %d: %s %s queda fuera del cuerpo (%.1f, %.1f mm)' % (i, mod, k[1], x, y))
        B.append(dict(modelo=mod, nombre=k[1], alias=(b['alias'] or '').strip(), x_mm=x, y_mm=y, radio_mm=r,
                      lado=(b['lado'] or '').strip().upper(), fuente=(b['fuente'] or '').strip()))
    for c in M:
        if not any(b['modelo'] == c for b in B):
            errores.append('el modelo %s no tiene bornes en bornes.csv' % c)
    if errores:
        print('ERRORES (no se armo la base):'); print('\n'.join('  ' + e for e in errores))
        sys.exit(1)
    if os.path.exists(base):
        os.remove(base)
    con = sqlite3.connect(base)
    con.executescript('''
      CREATE TABLE modelo(codigo TEXT PRIMARY KEY, fabricante TEXT, tipo TEXT, regla TEXT,
        ancho_mm REAL, alto_mm REAL, ancho_hoja_mm REAL, alto_hoja_mm REAL, tol_pct REAL, color TEXT,
        ignora_lado_texto INTEGER, lado_puente TEXT, alias_bom TEXT, descripcion TEXT, fuente TEXT);
      CREATE TABLE borne(modelo TEXT REFERENCES modelo(codigo), nombre TEXT, alias TEXT, x_mm REAL, y_mm REAL,
        radio_mm REAL, lado TEXT, fuente TEXT, PRIMARY KEY(modelo, nombre));
      CREATE VIEW bornes_mm AS SELECT m.fabricante, m.codigo, b.nombre, b.alias, b.x_mm, b.y_mm, b.radio_mm, b.lado,
        m.ancho_mm, m.alto_mm FROM borne b JOIN modelo m ON m.codigo = b.modelo;
    ''')
    cols = list(next(iter(M.values())).keys())
    con.executemany('INSERT INTO modelo(%s) VALUES(%s)' % (','.join(cols), ','.join('?' * len(cols))),
                    [tuple(m[c] for c in cols) for m in M.values()])
    bc = list(B[0].keys())
    con.executemany('INSERT INTO borne(%s) VALUES(%s)' % (','.join(bc), ','.join('?' * len(bc))),
                    [tuple(b[c] for c in bc) for b in B])
    con.commit(); con.close()
    print('Base %s: %d modelos, %d bornes' % (base, len(M), len(B)))
    for a in avisos:
        print('  aviso: ' + a)


def listar(base=BASE):
    con = sqlite3.connect(base)
    for cod, fab, tipo, regla, an, al in con.execute('SELECT codigo, fabricante, tipo, regla, ancho_mm, alto_mm FROM modelo ORDER BY fabricante, codigo'):
        n = con.execute('SELECT COUNT(*) FROM borne WHERE modelo=?', (cod,)).fetchone()[0]
        print('%-16s %-24s %-8s %-13s %6.2f x %6.2f mm  %2d bornes' % (fab, cod, tipo, regla, an, al, n))


if __name__ == '__main__':
    if '--listar' in sys.argv:
        listar()
    else:
        armar()
