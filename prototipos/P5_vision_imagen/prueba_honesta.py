"""Prueba honesta del prototipo P5: acierto en los tags que NO aportaron plantilla.

uso:  python prueba_honesta.py [carpeta_referencia] [salida.txt]
      (por defecto ../_referencia y salida/evaluacion_sin_plantilla.txt)

Las plantillas de la base se recortaron de ESTE mismo plano (base/recortes.json dice de que tag salio cada una).
Un tag que dio su plantilla "se encuentra a si mismo" con NCC 1.00, asi que su acierto no prueba nada. Esta
prueba hace dos cosas:

  A. Con la base normal: separa el acierto de los tags que dieron plantilla y el de los que no.
  B. Plantilla sacada de otro tag: para cada plantilla cuyo tipo de boca aparece en otro tag, se vuelve a
     recortar de ese OTRO tag (el 'clic' es el punto que dio la corrida normal para esa boca, corrido 0,35 pt a
     proposito, como el clic de una persona; hacer_base.py vuelve a buscar el centro en la imagen), se arma una
     base temporal, se corre mapear y se mide el tag que habia dado la plantilla original, que ahora no dio nada.

acierto_sin_plantilla = (BIEN de los tags sin plantilla en A + BIEN de los tags donantes en B) / (total de ambos).
Los donantes cuyo tipo de boca no aparece en ningun otro tag de este plano (MEGA, toma IRAM, borne fusible HESI,
PTT 2,5) no se pueden probar asi y se informan aparte.

Este script SI lee la referencia (a traves de evaluar.py): es un paso de evaluacion, aparte de mapear.py.
"""
import collections
import copy
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import mapear  # noqa: E402

# plantilla -> (tag del que se vuelve a recortar, texto del uso cuya boca es la misma que la original)
ALTERNATIVAS = {
    'boca_quattro': ('13XC1', '13XC1 1.1'),            # original 12XP, pieza 1 boca extrema de arriba
    'boca_octogono_u': ('43XDI', '43XDI 1 ARRIBA'),    # original 43XCS, pieza 1 boca extrema de arriba
    'celda_rif0': ('46KR', '46KR1 11'),                # original 43KR, modulo 1 celda 11
    'tornillo_modular': ('11Q2', '11Q2 F ARRIBA'),     # original 11Q1, polo izquierdo tornillo de arriba
    'tornillo_df101': ('13F3', '13F3 ARRIBA'),         # original 12F1, tornillo de arriba
    'tornillo_barrera': ('43DIB1', '43DIB1 1 ABAJO'),  # original 31AIB1, enchufe de arriba tornillo izquierdo
    'tornillo_meanwell': ('13PS3', '13PS3 -Vo'),       # original 11PS1 (NDR), TB2 pin 1; 13PS3 es DDR (tornillos mas chicos)
}
CORRIDO_CLIC = (0.35, -0.25)
TOL = 1.5


def evaluar_contra(ref, puntos):
    """Por cada punto de referencia evaluable: dict(componente, tag_fisico, bien, err)."""
    out = []
    for r in ref:
        if r['confianza'] == 'baja':
            continue
        cand = [g for g in puntos if g['texto'] == r['texto'] and set(g['cables']) & set(r['cables'])]
        if not cand:
            out.append(dict(componente=r['componente'], tag_fisico=r['componente'], bien=False, err=None, texto=r['texto'], cables=r['cables']))
            continue
        g = min(cand, key=lambda g: math.hypot(g['x'] - r['x'], g['y'] - r['y']))
        e = math.hypot(g['x'] - r['x'], g['y'] - r['y'])
        out.append(dict(componente=r['componente'], tag_fisico=g.get('tag_fisico', g.get('tag')), bien=e <= TOL, err=e,
                        texto=r['texto'], cables=r['cables']))
    return out


def resumen(ev):
    n = len(ev)
    b = sum(e['bien'] for e in ev)
    return b, n


def main():
    refdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, '..', '_referencia')
    txt = sys.argv[2] if len(sys.argv) > 2 else os.path.join(AQUI, 'salida', 'evaluacion_sin_plantilla.txt')
    sys.path.insert(0, refdir)
    import evaluar  # noqa: E402
    ref = evaluar.referencia()
    pdf = os.path.join(refdir, 'topografico.pdf')
    usos = os.path.join(refdir, 'usos_por_componente.json')
    rec = json.load(open(os.path.join(AQUI, 'base', 'recortes.json'), encoding='utf-8'))
    donante = {p['nombre']: p['tag'] for p in rec['plantillas']}
    donantes = set(donante.values())
    L = []

    def pr(s=''):
        print(s)
        L.append(s)

    # ---------------- A. corrida normal
    tmp = tempfile.mkdtemp(prefix='p5_honesta_')
    try:
        t0 = time.time()
        normal = mapear.mapear(pdf, usos, os.path.join(tmp, 'normal.json'), control=None)
        ev = evaluar_contra(ref, normal['puntos'])
        modelo_tag = {t: c.get('modelo') for t, c in normal['componentes'].items()}
        pr('PRUEBA HONESTA P5 - acierto en los tags que NO aportaron plantilla')
        pr(f'Referencia: {refdir}  (tolerancia {TOL} pt; no se evaluan los puntos de referencia dudosos)')
        pr('')
        pr('Tags que dieron plantilla (base/recortes.json): ' + ', '.join(f'{t} ({n})' for n, t in donante.items()))
        pr('')
        pr('A. Base normal')
        a_don = [e for e in ev if e['tag_fisico'] in donantes]
        a_no = [e for e in ev if e['tag_fisico'] not in donantes]
        b, n = resumen(ev)
        pr(f'   todos los tags ............................ {b}/{n} = {100 * b / n:.1f} %')
        b, n = resumen(a_don)
        pr(f'   tags que dieron plantilla ................. {b}/{n} = {100 * b / n:.1f} %   (se encuentran a si mismos: no prueba nada)')
        b_no, n_no = resumen(a_no)
        pr(f'   tags que NO dieron plantilla .............. {b_no}/{n_no} = {100 * b_no / n_no:.1f} %')
        for e in a_no:
            if not e['bien']:
                pr(f"      falla: {e['texto']} {e['cables']}  err {e['err'] if e['err'] is None else round(e['err'], 2)} pt")
        pr('')

        # ---------------- B. cada plantilla recortada de otro tag
        pr('B. Plantilla recortada de OTRO tag del mismo tipo (el donante original pasa a ser un tag sin plantilla)')
        b_loo = n_loo = 0
        probados = set()
        for nombre, (tag_alt, texto_alt) in ALTERNATIVAS.items():
            tag_orig = donante[nombre]
            p_alt = [p for p in normal['puntos'] if p['texto'] == texto_alt and p['tag'] == tag_alt]
            if not p_alt:
                pr(f'   {nombre}: no hay punto de {texto_alt} en la corrida normal; no se prueba')
                continue
            p_alt = p_alt[0]
            # factor de tamano entre las bocas del tag nuevo y las del original (distinto de 1 solo si son modelos
            # de distinto tamano de tornillo, p. ej. DDR frente a NDR): sale de las escalas de la base
            mod = json.load(open(os.path.join(AQUI, 'base', 'modelos.json'), encoding='utf-8'))
            def esc_media(tag):
                m = mod['modelos'][modelo_tag[tag]]
                return sum(m.get('escalas', [1.0])) / len(m.get('escalas', [1.0]))
            k = esc_media(tag_alt) / esc_media(tag_orig)
            rec2 = copy.deepcopy(rec)
            for p in rec2['plantillas']:
                if p['nombre'] == nombre:
                    p['tag'] = tag_alt
                    p['clic'] = [round(p_alt['x'] + CORRIDO_CLIC[0] * k, 2), round(p_alt['y'] + CORRIDO_CLIC[1] * k, 2)]
                    p['que'] = f'PRUEBA: misma boca recortada de {tag_alt} ({texto_alt})'
                    p['r_pt'] = round(p['r_pt'] * k, 2)
                    p['recorte_pt'] = [round(v * k, 2) for v in p['recorte_pt']]
            if abs(k - 1) > 0.02:
                for m in mod['modelos'].values():
                    if nombre in m['plantillas']:
                        m['escalas'] = [round(e / k, 3) for e in m.get('escalas', [1.0])]
            bdir = os.path.join(tmp, 'base_' + nombre)
            os.makedirs(bdir, exist_ok=True)
            json.dump(mod, open(os.path.join(bdir, 'modelos.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            rpath = os.path.join(tmp, 'recortes_' + nombre + '.json')
            json.dump(rec2, open(rpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            subprocess.run([sys.executable, os.path.join(AQUI, 'hacer_base.py'), rpath, bdir], check=True, capture_output=True)
            res = mapear.mapear(pdf, usos, os.path.join(tmp, 'loo_' + nombre + '.json'), control=None, base_dir=bdir)
            ev2 = evaluar_contra(ref, res['puntos'])
            orig = [e for e in ev2 if e['tag_fisico'] == tag_orig]
            b, n = resumen(orig)
            bt, nt = resumen(ev2)
            b_loo += b; n_loo += n
            probados.add(tag_orig)
            nota = f', escalas de la base / {k:.2f}' if abs(k - 1) > 0.02 else ''
            pr(f'   {nombre:18s} recortada de {tag_alt:6s} -> {tag_orig:6s} {b}/{n} BIEN   (todo el tablero {bt}/{nt}{nota})')
            for e in orig:
                if not e['bien']:
                    pr(f"      falla: {e['texto']} {e['cables']}  err {e['err'] if e['err'] is None else round(e['err'], 2)} pt")
        sin_alt = sorted(donantes - probados)
        pr('')
        pr('   Donantes sin otro tag del mismo tipo en este plano (no se pueden probar asi): ' + ', '.join(sin_alt))
        a_sin = [e for e in a_don if e['tag_fisico'] in sin_alt]
        b, n = resumen(a_sin)
        pr(f'   (con su propia plantilla dan {b}/{n}; ese numero no cuenta para el acierto honesto)')
        pr('')
        bt, nt = b_no + b_loo, n_no + n_loo
        pr(f'ACIERTO EN TAGS SIN PLANTILLA PROPIA: {bt}/{nt} = {100 * bt / nt:.1f} %   '
           f'({b_no}/{n_no} de A + {b_loo}/{n_loo} de B)')
        pr(f'Tiempo de la prueba: {time.time() - t0:.0f} s')
        resumen_json = dict(acierto_sin_plantilla=round(bt / nt, 3), bien=bt, total=nt,
                            a=dict(bien=b_no, total=n_no), b=dict(bien=b_loo, total=n_loo), donantes_sin_alternativa=sin_alt)
        pr('JSON ' + json.dumps(resumen_json, ensure_ascii=False))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.dirname(os.path.abspath(txt)), exist_ok=True)
    open(txt, 'w', encoding='utf-8').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
