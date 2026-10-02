import pypdfium2 as pdfium, json, re
d=pdfium.PdfDocument('76884_proc.pdf')
# columns in pt (x)
cols={'tag':(76,209),'cant':(209,263),'desig':(263,602),'tipo':(602,760),'fab':(760,906),'art':(906,1123),'pos':(1123,1160)}
rows=[]
for pg in range(39,46):
    p=d[pg]; W,H=p.get_size(); tp=p.get_textpage()
    n=tp.count_chars()
    # pos numbers: chars in pos column, below header
    chs=[]
    for i in range(n):
        c=tp.get_text_range(i,1)
        l,b,r,t=tp.get_charbox(i)
        chs.append((c,l,b,r,t))
    posc=[x for x in chs if cols['pos'][0]<x[1]<cols['pos'][1] and x[0].isdigit() and 100<x[4]<H-90]
    # group pos chars by y
    ys=sorted(set(round(x[4]) for x in posc),reverse=True)
    # merge close
    yy=[]
    for y in ys:
        if not yy or abs(yy[-1]-y)>5: yy.append(y)
    print(pg+1, yy)
    tops=[y+11 for y in yy]  # row top approx
    for k,top in enumerate(tops):
        bot = tops[k+1] if k+1<len(tops) else top-34
        rec={'page':pg+1}
        for cn,(x0,x1) in cols.items():
            txt=tp.get_text_bounded(x0,bot+1,x1,top)
            rec[cn]=' | '.join(s.strip() for s in txt.replace('\r','').split('\n') if s.strip())
        rows.append(rec)
json.dump(rows,open('lista_art_raw.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
for r in rows: print(r['pos'],'#',r['tag'],'#',r['cant'],'#',r['tipo'],'#',r['fab'],'#',r['art'],'#',r['desig'])
