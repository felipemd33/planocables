import pickle, math
st=pickle.load(open('strokes_p8.pkl','rb'))
def circ(a,b,c):
    ax,ay=a;bx,by=b;cx,cy=c
    d=2*(ax*(by-cy)+bx*(cy-ay)+cx*(ay-by))
    if abs(d)<1e-9: return None
    ux=((ax*ax+ay*ay)*(by-cy)+(bx*bx+by*by)*(cy-ay)+(cx*cx+cy*cy)*(ay-by))/d
    uy=((ax*ax+ay*ay)*(cx-bx)+(bx*bx+by*by)*(ax-cx)+(cx*cx+cy*cy)*(bx-ax))/d
    return ux,uy,math.hypot(ax-ux,ay-uy)
for box in [(667.5,540,672.3,548.5),(667.5,514,672.3,522),(671.5,540,675.8,548.5),(675,540,679.5,548.5),(675,514,679.5,522),
            (687.4,548,692,555.5),(687.4,540,692,547),(687.4,512.5,692,519.5),(687.4,504,692,511.5)]:
    pts=[];cs=[]
    for lay,op,p,col in st:
        if lay!='COMPONENTES' or op!='S' or not p: continue
        if all(box[0]<=x<=box[2] and box[1]<=y<=box[3] for x,y in p):
            if len(p) in (3,4):
                c=circ(p[0],p[len(p)//2],p[-1])
                if c and 1.2<c[2]<3: cs.append(c); pts+=p
    if cs:
        xs=[q[0] for q in pts]; ys=[q[1] for q in pts]
        print(box, 'n',len(cs),'bbox center',round((min(xs)+max(xs))/2,2),round((min(ys)+max(ys))/2,2),'w',round(max(xs)-min(xs),2),'h',round(max(ys)-min(ys),2),
              'r med',round(sorted(c[2] for c in cs)[len(cs)//2],2), 'centros', sorted(set((round(c[0],1),round(c[1],1)) for c in cs))[:6])
