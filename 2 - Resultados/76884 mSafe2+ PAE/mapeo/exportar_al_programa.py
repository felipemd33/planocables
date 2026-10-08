"""Exporta el mapeo verificado del mSafe2+ PAE (ZPL-76884 rev 1) al formato que usa el programa:
programa/mapeos_verificados/ZPL-76884_rev1.json (dato del producto, no codigo).
Fuente: conexiones.json, puntos_*.json (+ correcciones_*.json de los verificadores) y bandejas.json de esta carpeta.
Uso: python exportar_al_programa.py"""
import json, os, glob, re, datetime

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(D))), 'programa', 'mapeos_verificados', 'ZPL-76884_rev1.json')
con = json.load(open(os.path.join(D, 'conexiones.json'), encoding='utf-8'))
band = json.load(open(os.path.join(D, 'bandejas.json'), encoding='utf-8'))

clave = lambda d, num: f'{d}#{num or "s/n"}'
puntas = {}
for f in sorted(glob.glob(os.path.join(D, 'puntos_*.json'))):
    zona = os.path.basename(f)[7:-5]
    data = json.load(open(f, encoding='utf-8'))
    corr = {}
    cf = os.path.join(D, f'correcciones_{zona}.json')
    if os.path.exists(cf):
        for c in json.load(open(cf, encoding='utf-8')).get('correcciones', []):
            corr[(c['d'], str(c['cable']))] = c
    for p in data['puntos']:
        for c in p.get('cables') or []:
            num = c if re.fullmatch(r'\d+[A-Z]?', str(c)) else None
            q = dict(texto=p['texto_taller'], x=p['x'], y=p['y'], r=p.get('r'), conf=p.get('confianza'), lado=p.get('lado'),
                     como=p.get('como', ''), zona=zona)
            k = corr.get((p['d'], str(c)))
            if k:
                q.update(x=k['x'], y=k['y'], corregido=k.get('motivo', ''))
                if k.get('texto_taller'):
                    q['texto'] = k['texto_taller']
                if k.get('confianza'):          # correccion confirmada por el taller
                    q['conf'] = k['confianza']
            puntas[clave(p['d'], num)] = q
            if p.get('d_usada'):
                puntas.setdefault(clave(p['d_usada'], num), dict(q))
# textos verificados de las puntas fuera de las bandejas:
# - las que tienen texto propuesto desde el esquema: el pin que EPLAN no da ('11MS1:1/L1' -> '11MS1 1/L1') y los
#   empalmes X1 del sensor de nivel ('empalme con LS001A:3 Negro' -> 'empalme con LS001A 3 Negro');
# - las de la zona hidraulica (E8): la designacion tal cual ('-PT001:x1' -> 'PT001 x1', '-12F2:1' -> '12F2 1').
# Asi la lista de otra estacion (E8) dice el destino real. Si varios renglones comparten la clave '<d>#<cable>' con
# distinto texto (los 4 empalmes '-X1:2' sin numero), la clave lleva la otra punta: '<d>#<cable>@<otra designacion>'.
# Zona hidraulica y empalmes (E8). Desde el 2026-10-06 (regla del taller) tambien la bateria (12PB1) y las solenoides
# (SP_1, SP_2, SP_3): sus cables no se cablean en E6, van con la estacion E8.
ZONA_E8 = ('12F2', 'BH', 'BH_01_ZV', 'BH-01-M', 'PT001', 'LS001A', 'X1', '12PB1', 'SP_1', 'SP_2', 'SP_3')


def texto_desig(d):
    m = re.match(r'^(?:=[^+\-\s:]*)?(?:\+[^\-\s:]+)?-([^\s:]+)(?::(\S*))?$', d or '')
    if not m:
        return None
    return ' '.join([m.group(1)] + [p for p in (m.group(2) or '').split(':') if p])


cand = {}
for c in con['conexiones']:
    for k, o in (('d1', 'd2'), ('d2', 'd1')):
        d = c[k]
        if not d or clave(d, c.get('num')) in puntas:
            continue
        prop = c.get(f'{k}_propuesto')
        if prop:
            t = re.sub(r'\s+', ' ', prop.lstrip('-').replace(':', ' ')).strip()
        elif (c.get(f'{k}_tag') or (texto_desig(d) or '').split(' ')[0]) in ZONA_E8:
            t = texto_desig(d)
        else:
            continue
        if t:
            cand.setdefault(clave(d, c.get('num')), []).append((c[o], t))
textos = {}
for k, vs in cand.items():
    if len({t for _, t in vs}) == 1:
        textos[k] = vs[0][1]
    else:
        for otra, t in vs:
            textos[f'{k}@{otra or ""}'] = t
intr = [cn['b'] for cn in band['principal']['canaletas'] if 'intrinseca' in cn.get('tipo', '')]
avisos = [
    'Doble piso PTT 2,5-2MT (15XR, 32XEX, 41XEX, 42XC, 81XCM): impar en la boca del extremo, par en la interior (convención del taller). Confirmar en el primer tablero.',
    '42KS1 (PSR 2963802), filas de abajo: 43-44-13-14 en la fila interior y 33-34-23-24 en la exterior (rótulo del aparato). Confirmar mirando el relé.',
    '42KS1 y 11MS1: EPLAN no exporta 12 pines; salen del esquema (hojas 42 y 11).',
    '61KR1 a 61KR4: la hoja 8 rotula solo "-61KR"; se supuso KR1 a KR4 de izquierda a derecha.',
    '15DIB3: las hojas 15 y 41 dicen que va sin barrera (bornes cuchilla); se mapeó sobre la barrera dibujada.',
    'Barreras GS85xx: el enchufe [1 2] no está dibujado; va detrás del [3 4], arriba (confianza media).',
    '61XDIO: el texto usa el lado FÍSICO (cátodo ARRIBA, ánodo ABAJO). ¿Lado físico o del funcional?',
    '12XPS 10 y 11 (2135, 2136): los dos tramos de cada cable van juntos en la boca de abajo, con terminal doble.',
    'Tierra del gabinete a 11XPVAC 3.1 y R1 120 Ω en 81XCM 7/8: están en el esquema pero no en la lista de conexiones.',
    'Zona hidráulica (12F2, BH, BH_01_ZV, BH-01-M, PT001, LS001A) y empalmes X1 del sensor de nivel: se cablean en E8.',
]
out = dict(documento='ZPL-76884', revision='1', producto='mSafe2+ PAE (EPLAN)', pagina_bandejas=band.get('pagina', 8),
           escala_mm_por_pt=band.get('escala_mm_por_pt'),
           fuente='2 - Resultados/76884 mSafe2+ PAE/mapeo (conexiones.json, puntos_*.json + correcciones_*.json, bandejas.json), verificado por agentes el 2026-10-02',
           exportado=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
           unidades='x, y, r en pt de la hoja de bandejas (pagina PDF 8), origen abajo a la izquierda',
           clave='<designacion EPLAN tal cual en la lista de conexiones>#<numero de cable> ("#s/n" si el renglon no tiene numero)',
           estaciones_tag={t: 'E8' for t in ZONA_E8},
           canaletas_intrinsecas=intr, avisos=avisos, puntas=puntas, textos=textos)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok', OUT, len(puntas), 'puntas', len(textos), 'textos', len(intr), 'canaletas de intrinsecos')
