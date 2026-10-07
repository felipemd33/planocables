"""Colores de los cables: nombre del programa, inicial del instructivo ('N2.5MM') y nombres en ingles de los planos.
Solo biblioteca estandar. (EPLAN tiene ademas su tabla de alias en eplan.COLOR_ALIAS; se pasa aca en la etapa 4.)"""

COLORES = {'rojo': 'Rojo', 'negro': 'Negro', 'azul': 'Azul', 'blanco': 'Blanco', 'marron': 'Marrón', 'marrón': 'Marrón',
           'gris': 'Gris', 'verde': 'Verde', 'amarillo': 'Amarillo', 'a-v': 'Verde-Amarillo', 'v-a': 'Verde-Amarillo',
           'violeta': 'Violeta', 'naranja': 'Naranja', 'celeste': 'Celeste', 'rosa': 'Rosa',
           # planos en ingles (66817): mismos nombres que usa el instructivo (N/R/B/A... y Azul = intrinsecamente seguro)
           'red': 'Rojo', 'black': 'Negro', 'blue': 'Azul', 'white': 'Blanco', 'brown': 'Marrón', 'grey': 'Gris', 'gray': 'Gris',
           'green': 'Verde', 'yellow': 'Amarillo', 'g-y': 'Verde-Amarillo', 'y-g': 'Verde-Amarillo', 'green-yellow': 'Verde-Amarillo',
           'yellow-green': 'Verde-Amarillo', 'gn-ye': 'Verde-Amarillo', 'violet': 'Violeta', 'purple': 'Violeta', 'orange': 'Naranja',
           'pink': 'Rosa', 'light blue': 'Celeste', 'lightblue': 'Celeste'}
# la nota del plano en ingles ('not indicated will be black 1 mm'): core.page_meta
COLOR_EN = {'black': 'Negro', 'red': 'Rojo', 'blue': 'Azul', 'white': 'Blanco', 'brown': 'Marrón', 'grey': 'Gris', 'gray': 'Gris'}
# inicial del color en el texto del cable del instructivo ('N2.5MM')
COLOR_INI = {'Negro': 'N', 'Rojo': 'R', 'Blanco': 'B', 'Marrón': 'M', 'Azul': 'A', 'Gris': 'G', 'Verde': 'V',
             'Amarillo': 'AM', 'Verde-Amarillo': 'VA', 'Naranja': 'NA', 'Violeta': 'VI', 'Celeste': 'C', 'Rosa': 'RS'}


def una_letra(a, b):
    """a y b difieren en una sola letra (cambiada, de mas, de menos) o en dos letras vecinas cambiadas de lugar"""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def norm_color(c):
    k = c.strip().lower().replace(' ', '')
    if k in COLORES:
        return COLORES[k]
    # error de tipeo del plano ('Balck' = Black): el color conocido que difiere en una letra, si hay uno solo
    cand = {v for n, v in COLORES.items() if len(n) >= 4 and len(k) >= 4 and una_letra(k, n)}
    return cand.pop() if len(cand) == 1 else c.strip().capitalize()


def inicial(color):
    """inicial del color para el texto del cable ('Negro' -> 'N'); un color fuera de la tabla, su primera letra"""
    return COLOR_INI.get(color, (color or '?')[:1].upper())
