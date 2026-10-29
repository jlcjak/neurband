"""Close measured ground coverage gaps, reworking only non-electrode copper."""
from preorder_power_guard_c import *
from shapely.strtree import STRtree
sys.path.insert(0,'sim/preorder')
from pcbgeom import Board
from coupling import gnd_fill

def main():
 t=load();save(t,BUILD/'before-ground-complete.kicad_pcb');r=Router(t);_,legalvia=r.available('GND');fills=gnd_fill(Board(str(PCB)));area=unary_union(list(fills.values()));in1=fills['In1.Cu']
 rf=unary_union([shape(c)[0]for c in copper(t)if net(c)in {'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'}]).buffer(.73)
 electrodes=unary_union([shape(c)[0]for c in copper(t)if net(c).startswith('/E')or net(c).startswith('Net-(RN')]).buffer(.36)
 xx,yy=np.meshgrid(np.arange(.5,28.25,.1),np.arange(.5,26.55,.1));cands=np.c_[xx.ravel(),yy.ravel()];ix=np.rint(cands[:,0]/.025).astype(int);iy=np.rint(cands[:,1]/.025).astype(int)
 ok=~r.vedge[iy,ix]&contains_xy(in1,cands[:,0],cands[:,1])&~contains_xy(rf,cands[:,0],cands[:,1])&~contains_xy(electrodes,cands[:,0],cands[:,1]);cands=cands[ok]
 allvias=np.array([list(map(float,get(c,'at')[1:3]))for c in kids(t,'via')]);gv=np.array([list(map(float,get(c,'at')[1:3]))for c in kids(t,'via')if net(c)=='GND']);added=[];kill=set();cs=copper(t);geos=[shape(c)[0]for c in cs];tree=STRtree(geos)
 def legal():return np.min(np.sum((cands[:,None,:]-allvias[None,:,:])**2,axis=2),axis=1)>.56**2
 def choose(target,maxdist):
  scores=np.sum((cands-target)**2,axis=1);ok=legal()&(scores<=maxdist**2);inds=np.where(ok)[0];rank=[]
  for j in inds:
   q=cands[j];pt=Point(q);hits=[int(i)for i in tree.query(pt.buffer(.355))if item_id(cs[int(i)])not in kill and net(cs[int(i)])!='GND'and pt.distance(geos[int(i)])<.355]
   if any(cs[i][0]=='via'for i in hits):continue
   if any(net(cs[i]).startswith('/E')or net(cs[i]).startswith('Net-(RN')for i in hits):continue
   cost=sum(20 if net(cs[i]).startswith(('/ADC','/SPI','/I2C','/IMU'))else 5 if net(cs[i])in ['+3V3','+3V3A','VBAT']else 3 for i in hits)
   rank.append((cost+scores[j],j,hits))
  return min(rank,default=None)
 def add(choice,reason):
  nonlocal allvias,gv
  cost,j,hits=choice;q=cands[j];kill.update(item_id(cs[i])for i in hits);t.append(via(*q));allvias=np.vstack([allvias,q]);gv=np.vstack([gv,q]);added.append(dict(x=round(q[0],4),y=round(q[1],4),reason=reason,reworked=sorted(set(net(cs[i])for i in hits))))
 xx,yy=np.meshgrid(np.arange(.5,28.25,.2),np.arange(.5,26.55,.2));pts=np.c_[xx.ravel(),yy.ravel()];pts=pts[contains_xy(area,pts[:,0],pts[:,1])]
 for _ in range(100):
  ds=np.min(np.sum((pts[:,None,:]-gv[None,:,:])**2,axis=2),axis=1);j=np.argmax(ds)
  if ds[j]<2.8**2:break
  choice=choose(pts[j],2.8)
  if choice is None:print('NO GROUND SITE',pts[j].tolist(),flush=True);break
  add(choice,'coverage')
 active=lambda n:n.startswith(('/I2C_','/SPI_','/IMU_INT','/ADC_','/LED'))or n=='Net-(D1-A)'
 for c in cs:
  if c[0]!='via'or not active(net(c)):continue
  q=np.array(list(map(float,get(c,'at')[1:3])))
  if math.dist(q,(20.2,10.1))>8 or np.min(np.sum((gv-q)**2,axis=1))<=1**2:continue
  choice=choose(q,1.2)
  if choice:add(choice,'return '+net(c))
  else:print('NO RETURN SITE',net(c),q.tolist(),flush=True)
 remove_ids(t,kill);save(t);(BUILD/'ground-complete-vias.json').write_text(json.dumps(added,indent=2)+'\n');print('Ground additions',len(added),'reworked',collections.Counter(net(c)for c in cs if item_id(c)in kill),flush=True)
 d=check('ground-complete');close_components(t,d);check('ground-complete-closed')
if __name__=='__main__':main()
