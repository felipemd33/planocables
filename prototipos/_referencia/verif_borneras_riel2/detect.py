import pickle, numpy as np, cv2, json, math
st=pickle.load(open('strokes_p8.pkl','rb'))
X0,Y0,X1,Y1=585,495,705,570
S=20.0
W=int((X1-X0)*S); H=int((Y1-Y0)*S)
img=np.full((H,W),255,np.uint8)
def P(x,y): return (int(round((x-X0)*S)), int(round((Y1-y)*S)))
for lay,op,pts,col in st:
    if lay not in ('COMPONENTES','00_COMPONENTS') or op!='S' or not pts: continue
    if not any(X0-5<=x<=X1+5 and Y0-5<=y<=Y1+5 for x,y in pts): continue
    arr=np.array([P(x,y) for x,y in pts],np.int32)
    cv2.polylines(img,[arr],False,0,2)
cv2.imwrite('comp_raster.png',img)
# regions: connected components of white
n,lab,stats,cent=cv2.connectedComponentsWithStats((img>128).astype(np.uint8),connectivity=4)
res=[]
for i in range(1,n):
    x,y,w,h,a=stats[i]
    wpt,hpt=w/S,h/S
    if 2.0<=wpt<=6.5 and 2.0<=hpt<=6.5:
        cx=X0+(x+w/2)/S; cy=Y1-(y+h/2)/S
        fill=a/(w*h)
        res.append((round(cx,2),round(cy,2),round(wpt,2),round(hpt,2),round(fill,2)))
res.sort(key=lambda r:(r[0],-r[1]))
for r in res: print(r)
