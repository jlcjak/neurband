"""Measure filled ground and add standard-drill ties in legal copper sites."""
from file_layout_c import *
from native_check_c import check
sys.path.insert(0,'sim/preorder')
from pcbgeom import Board
from coupling import gnd_fill
from shapely.validation import make_valid

def main():
 t=load();save(t,BUILD/'before-stitch.kicad_pcb');r=Router(t);_,v=r.available('GND');b=Board(str(PCB));fills=gnd_fill(b);area=unary_union(list(fills.values()))
 ys,xs=np.where(v[::4,::4]);cands=np.c_[xs*.1,ys*.1];keep=contains_xy(fills['In1.Cu'],cands[:,0],cands[:,1]);cands=cands[keep]
 rf=unary_union([shape(c)[0]for c in copper(t)if net(c)in {'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'}]).buffer(.73)
 cands=cands[~contains_xy(rf,cands[:,0],cands[:,1])]
 allvias=np.array([list(map(float,get(c,'at')[1:3]))for c in kids(t,'via')]);gv=np.array([list(map(float,get(c,'at')[1:3]))for c in kids(t,'via')if net(c)=='GND']);added=[]
 def legal():return np.min(np.sum((cands[:,None,:]-allvias[None,:,:])**2,axis=2),axis=1)>.56**2
 def add(q,reason):
  nonlocal allvias,gv
  q=np.array(q);t.append(via(*q));allvias=np.vstack([allvias,q]);gv=np.vstack([gv,q]);added.append(dict(x=round(q[0],4),y=round(q[1],4),reason=reason))
 # Cover every existing ground-pour point, including the dedicated inner plane.
 xx,yy=np.meshgrid(np.arange(.5,28.25,.2),np.arange(.5,26.55,.2));pts=np.c_[xx.ravel(),yy.ravel()];pts=pts[contains_xy(area,pts[:,0],pts[:,1])]
 for _ in range(100):
  dist=np.min(np.sum((pts[:,None,:]-gv[None,:,:])**2,axis=2),axis=1);i=np.argmax(dist)
  if dist[i]<2.8**2:break
  legal0=legal();scores=np.sum((cands-pts[i])**2,axis=1);scores[~legal0]=np.inf;j=np.argmin(scores)
  if scores[j]>2.8**2:print('UNCOVERABLE',pts[i].tolist(),float(dist[i]**.5),flush=True);break
  add(cands[j],'pour coverage')
 # Add a second tie to meaningful filled fragments where a standard via fits.
 for ly,gg in fills.items():
  polys=list(gg.geoms)if hasattr(gg,'geoms')else[gg]
  for pg in polys:
   if pg.geom_type!='Polygon'or pg.area<.2:continue
   ties=contains_xy(pg.buffer(.01),gv[:,0],gv[:,1]);need=2-int(ties.sum())
   for _ in range(max(0,need)):
    ok=contains_xy(pg,cands[:,0],cands[:,1])&legal()
    if not ok.any():break
    scores=np.sum((cands-np.array(pg.representative_point().coords[0]))**2,axis=1);scores[~ok]=np.inf;add(cands[np.argmin(scores)],'fragment '+ly)
 # Keep the digital signal's layer-change return close to its barrel.
 active=lambda n:n.startswith(('/I2C_','/SPI_','/IMU_INT','/ADC_','/LED'))or n=='Net-(D1-A)'
 for c in kids(t,'via')[:]:
  if not active(net(c)):continue
  q=np.array(list(map(float,get(c,'at')[1:3])))
  if math.dist(q,(20.2,10.1))>8:continue
  if np.min(np.sum((gv-q)**2,axis=1))<=1.0**2:continue
  scores=np.sum((cands-q)**2,axis=1);scores[~legal()]=np.inf;j=np.argmin(scores)
  if scores[j]<=1.3**2:add(cands[j],'digital return '+net(c))
  else:print('RETURN GAP',net(c),q.tolist(),flush=True)
 save(t);(BUILD/'ground-vias-added.json').write_text(json.dumps(added,indent=2)+'\n');print('GND VIAS ADDED',len(added),flush=True);check('stitched')
if __name__=='__main__':main()
