import pypdfium2 as pdfium, sys
PDF=r'C:/Buscar Termos en plano/1 - Planos/Producto nuevo/ZPL-76884 - mSafe2+ PAE - Rev 1 - FABRIC.pdf'
def words(pi, box=None):
    d=pdfium.PdfDocument(PDF); tp=d[pi].get_textpage()
    n=tp.count_chars(); out=[]; cur=None
    for i in range(n):
        ch=tp.get_text_range(i,1); b=tp.get_charbox(i)
        if ch.strip()=='' :
            if cur: out.append(cur); cur=None
            continue
        if cur and abs(b[1]-cur[2])<0.5 and b[0]-cur[3]<1.5 and b[0]>=cur[1]-0.5:
            cur[0]+=ch; cur[3]=b[2]; cur[4]=max(cur[4],b[3])
        else:
            if cur: out.append(cur)
            cur=[ch,b[0],b[1],b[2],b[3]]
    if cur: out.append(cur)
    if box:
        x0,y0,x1,y1=box; out=[w for w in out if x0<=w[1]<=x1 and y0<=w[2]<=y1]
    return out
if __name__=='__main__':
    pi=int(sys.argv[1]); box=tuple(map(float,sys.argv[2:6])) if len(sys.argv)>2 else None
    for w in words(pi,box): print('%-20s x %.2f-%.2f y %.2f-%.2f'%(w[0],w[1],w[3],w[2],w[4]))
