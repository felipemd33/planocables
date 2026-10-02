import pypdfium2 as pdfium
def words(doc, pg, gap=1.5):
    p=doc[pg]; tp=p.get_textpage(); n=tp.count_chars()
    out=[]; cur=None
    for i in range(n):
        c=tp.get_text_range(i,1)
        if c in '\r\n':
            if cur: out.append(cur); cur=None
            continue
        l,b,r,t=tp.get_charbox(i)
        if c==' ':
            if cur: out.append(cur); cur=None
            continue
        if cur and abs(cur['b']-b)<2 and l-cur['r']<gap*max(1,(t-b)*0.5) and l>=cur['r']-1:
            cur['s']+=c; cur['r']=max(cur['r'],r); cur['t']=max(cur['t'],t)
        else:
            if cur: out.append(cur)
            cur={'s':c,'l':l,'b':b,'r':r,'t':t}
    if cur: out.append(cur)
    return out
def lines(ws, ytol=2.5):
    ws=sorted(ws,key=lambda w:(-round(w['b']),w['l']))
    ls=[]
    for w in ws:
        for L in ls:
            if abs(L[0]['b']-w['b'])<ytol: L.append(w); break
        else: ls.append([w])
    ls=[sorted(L,key=lambda w:w['l']) for L in ls]
    ls.sort(key=lambda L:-L[0]['b'])
    return ls
