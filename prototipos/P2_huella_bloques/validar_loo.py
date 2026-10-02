"""Validacion dejando-un-tag-afuera (LOO) del prototipo P2.

uso:  python validar_loo.py [salida/bornes_loo.json]

Para cada tag T del plano verificado: se aprende la base SIN T (no se usan sus bornes de referencia ni las
instancias de bloque de su zona), se mapea T con esa base, y se juntan los puntos. Asi se mide que pasaria en
un plano nuevo con un modelo que la base ya conoce de OTRO lugar. Los modelos que en este tablero aparecen en
un solo tag quedan sin aprender en su vuelta y no tienen punto (se informa).
Escribe salida/bornes_loo.json y salida/evaluacion_loo.txt (con evaluar.py de _referencia).
"""
import sys, os, time, json, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.dont_write_bytecode = True
import huellas as H
import aprender as AP
import mapear as MP

REF = r'C:\Buscar Termos en plano\prototipos\_referencia'


def main():
    t0 = time.time()
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, 'salida', 'bornes_loo.json')
    cat = H.cargar_json(os.path.join(AQUI, 'catalogo_modelos.json'))
    pv = cat['planos_verificados'][0]
    usos = H.cargar_json(pv['usos'])
    lista_p = os.path.join(os.path.dirname(os.path.abspath(pv['usos'])), 'lista_materiales.txt')
    lista = H.leer_lista_materiales(lista_p) if os.path.exists(lista_p) else None
    planos = {}
    P = AP.plano_de(pv, planos, usos)
    puntos, sin, filas = [], [], []
    for tag, mid in pv['tags'].items():
        t1 = time.time()
        base = AP.aprender(cat, excluir=tag, planos=planos, log=lambda *a: None)
        res = MP.mapear(P, base, usos, lista, solo=[tag])
        otros = [t for t, m in pv['tags'].items() if m == mid and t != tag]
        mb = base['modelos'][mid]
        puntos += res['puntos']; sin += res['sin_punto']
        filas.append(dict(tag=tag, modelo=mid, otros_tags=otros, aprendido=bool(mb.get('huella')),
                          bornes_en_base=sorted(mb.get('bornes', {})), usos=len(usos['componentes'][tag]['usos']),
                          con_punto=sum(1 for p in res['puntos'] if p['componente'] == tag),
                          eleccion=res['componentes'].get(tag, {}), segundos=round(time.time() - t1, 1)))
        print('%-7s %-15s otros=%-22s %2d/%2d con punto  (%.1f s)' % (tag, mid, ','.join(otros) or '-', filas[-1]['con_punto'], filas[-1]['usos'], time.time() - t1))
    seg = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    H.guardar_json(out, dict(modo='dejando-un-tag-afuera: para cada tag T la base se aprende sin T', segundos=seg,
                             puntos=puntos, sin_punto=sin, vueltas=filas))
    # ---------------------------------------------------------------- evaluacion
    sys.path.insert(0, REF)
    import evaluar as EV
    r = EV.evaluar(out)
    txt = EV.texto(r)
    unicos = [f for f in filas if not f['otros_tags']]
    L = ['VALIDACION DEJANDO-UN-TAG-AFUERA (LOO) - prototipo P2 huellas de bloques', '',
         'Para cada tag T la base se aprende SIN T (sin sus bornes de referencia ni las instancias de bloque de su zona)',
         'y se mapea T con esa base. Mide lo que pasaria en un plano nuevo con un modelo que la base conoce de otro lugar.',
         'Tiempo total: %.1f s (%d vueltas de aprender + mapear).' % (seg, len(filas)), '', txt, '',
         'Modelos que aparecen UNA SOLA VEZ en este tablero (en su vuelta no hay de donde aprenderlos: quedan sin punto):']
    for f in unicos:
        L.append('  %-7s %-15s %2d usos' % (f['tag'], f['modelo'], f['usos']))
    ev_unicos = [x for x in r['fallas'] if x['error_pt'] is None]
    L += ['', 'Evaluables sin punto en modo LOO: %d (casi todos de los modelos unicos de arriba).' % len(ev_unicos), '',
          'Detalle por tag (modelo, con que otros tags se aprendio, usos con punto / usos):']
    for f in filas:
        L.append('  %-7s %-15s aprendido de: %-22s %2d/%2d  %s' % (
            f['tag'], f['modelo'], ','.join(f['otros_tags']) or '(nadie)', f['con_punto'], f['usos'], f['eleccion'].get('nota', '')))
    tot_multi = sum(v['total'] for v in [r['por_familia'][k] for k in r['por_familia']])
    ref_multi = [x for x in EV.referencia() if x['confianza'] != 'baja' and pv['tags'].get(x['componente']) in
                 {f['modelo'] for f in filas if f['otros_tags']}]
    bien_multi = len(ref_multi) - len([x for x in r['fallas'] if pv['tags'].get(_comp(x['texto'], usos)) in {f['modelo'] for f in filas if f['otros_tags']}])
    L += ['', 'Solo los modelos que aparecen en 2 o mas tags: %d/%d BIEN = %.1f %%' % (bien_multi, len(ref_multi), 100.0 * bien_multi / max(1, len(ref_multi)))]
    with open(os.path.join(os.path.dirname(os.path.abspath(out)), 'evaluacion_loo.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L[6:9]))
    print(L[-1])


def _comp(texto, usos):
    for c, v in usos['componentes'].items():
        if any(u['texto'] == texto for u in v['usos']):
            return c
    return None


if __name__ == '__main__':
    main()
