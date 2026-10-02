import pypdfium2 as pdfium, json
import sys; sys.path.insert(0, r'C:/Buscar Termos en plano/programa')
import pypdf
from pdfvec import layer_names, page_strokes
rd=pypdf.PdfReader('76884_proc.pdf'); ln=layer_names(rd)
d=pdfium.PdfDocument('76884_proc.pdf')
L=[('num',100,170),('d1',170,295),('d2',295,438),('color',438,518),('sec',518,565)]
R=[(n,a+578,b+578) for n,a,b in L]
rows=[]
for pg in range(46,50):
    st=page_strokes(rd,pg,ln,with_color=True)
    ys=set()
    for cap,op,pts,rgb in st:
        for (x0,y0),(x1,y1) in zip(pts,pts[1:]):
            if abs(y0-y1)<0.2 and abs(x1-x0)>300 and 95<y0<790 and (abs(min(x0,x1)-82)<3 or abs(min(x0,x1)-660)<3): ys.add(round(y0,1))
    ys=sorted(ys,reverse=True)
    tp=d[pg].get_textpage()
    for side in (L,R):
        for top,bot in zip(ys,ys[1:]):
            rec={}
            for n,a,b in side:
                t=tp.get_text_bounded(a,bot+0.5,b,top-0.5)
                parts=[s.strip() for s in t.replace('\r','').split('\n') if s.strip()]
                rec[n]=parts
            if not any(rec.values()): continue
            if rec['num']==['Conexión'] or rec['num'][:1]==['Conexión'] or 'Conexi' in ''.join(rec['num']): continue
            rec['page']=pg+1
            rows.append(rec)
json.dump(rows,open('conex_raw.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
print(len(rows))
for r in rows: print(r['page'], r['num'], r['d1'], r['d2'], r['color'], r['sec'])
