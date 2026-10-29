"""Finish legal standard-drill ground coverage without cutting signal copper."""
from preorder_stitch_c import *
def main():
 t=load();save(t,BUILD/'before-stitch-finish.kicad_pcb');r=Router(t);_,v=r.available('GND');fills=gnd_fill(Board(str(PCB)));area=unary_union(list(fills.values()))
 ys,xs=np.where(v[::4,::4]);cands=np.c_[xs*.1,ys*.1];keep=contains_xy(fills['In1.Cu'],cands[:,0],cands[:,1]);cands=cands[keep]
 rf=unary_union([shape(c)[0]for c in copper(t)if net(c)in {'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'}]).buffer(.73);cands=cands[~contains_xy(rf,cands[:,0],cands[:,1])]
 allvias=np.array([list(map(float,get(c,'at')[1:3]))for c in kids(t,'via')]);gv=np.array([list(map(float,get(c,'at')[1:3]))for c in kids(t,'via')if net(c)=='GND']);added=[];uncovered=[]
 def legal():return np.min(np.sum((cands[:,None,:]-allvias[None,:,:])**2,axis=2),axis=1)>.56**2
 def add(q,reason):
  nonlocal allvias,gv
  q=np.array(q);t.append(via(*q));allvias=np.vstack([allvias,q]);gv=np.vstack([gv,q]);added.append(dict(x=round(q[0],4),y=round(q[1],4),reason=reason))
 xx,yy=np.meshgrid(np.arange(.5,28.25,.2),np.arange(.5,26.55,.2));pts=np.c_[xx.ravel(),yy.ravel()];pts=pts[contains_xy(area,pts[:,0],pts[:,1])]
 for _ in range(500):
  ds=np.min(np.sum((pts[:,None,:]-gv[None,:,:])**2,axis=2),axis=1);i=np.argmax(ds)
  if ds[i]<2.8**2:break
  scores=np.sum((cands-pts[i])**2,axis=1);scores[~legal()]=np.inf;j=np.argmin(scores)
  if scores[j]>2.8**2:
   uncovered.append(pts[i].tolist());pts=np.delete(pts,i,axis=0);continue
  add(cands[j],'coverage')
 for ly,gg in fills.items():
  for pg in (gg.geoms if hasattr(gg,'geoms')else[gg]):
   if pg.geom_type!='Polygon'or pg.area<.2:continue
   for _ in range(max(0,2-int(contains_xy(pg.buffer(.01),gv[:,0],gv[:,1]).sum()))):
    ok=contains_xy(pg,cands[:,0],cands[:,1])&legal()
    if not ok.any():break
    scores=np.sum((cands-np.array(pg.representative_point().coords[0]))**2,axis=1);scores[~ok]=np.inf;add(cands[np.argmin(scores)],'second anchor '+ly)
 save(t);(BUILD/'ground-stitch-finish.json').write_text(json.dumps(dict(added=added,uncoverable_samples=uncovered),indent=2)+'\n');print('ADDED',len(added),'UNCOVERABLE',len(uncovered),flush=True);check('stitch-finished')
if __name__=='__main__':main()
