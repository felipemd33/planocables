"""Vuelca el listado de cables (core.process) de un plano: para comparar que un cambio no rompa la lectura.
uso: python volcar_cables.py <plano.pdf> <salida.json>"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'programa'))
from core import process
res = process(sys.argv[1], log=lambda m: None)
det = sorted((d['num'], d['pag'], d['color'], str(d['sec']), [round(v) for v in d['bbox']]) for d in res.detail)
json.dump(dict(detalle=det, cables=[(c['num'], c['color'], str(c['sec'])) for c in res.cables]), open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
print(len(det), 'apariciones,', len(res.cables), 'cables ->', sys.argv[2])
