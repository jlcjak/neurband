"""Legal standard-drill digital escapes around the fixed bottom charging lands."""
from file_layout_c import *
from native_check_c import check

def addvia(r,n,q):
 c=via(*q,n);r.t.append(c);g,zs=shape(c)
 for z in zs:r.geometry[n][z].append(g)
 r.vias.append((*q,n));r.refresh(n)
def main():
 t=load();save(t,BUILD/'failed-escape-trial.kicad_pcb');t=load(BUILD/'before-nrf-escape.kicad_pcb');by={ref(f):f for f in kids(t,'footprint')};old=[p for p in pad_data(t)if p['ref']=='C11'];kill=set()
 for c in copper(t):
  g,z=shape(c)
  if net(c)=='/ADC_START':kill.add(item_id(c))
  if c[0]=='segment'and net(c)in ['+3V3','GND']and 0 in z and any(p['net']==net(c)and g.distance(p['poly'])<.01 for p in old):kill.add(item_id(c))
  if c[0]=='via'and net(c)=='+3V3'and math.dist(tuple(map(float,get(c,'at')[1:3])),(4.8,7.15))<.01:kill.add(item_id(c))
 remove_ids(t,kill);move(by['C11'],13.075,5.0,90)
 ps=pad_data(t);moved=[p for p in ps if p['ref']=='C11'];kill=set()
 for c in copper(t):
  g,z=shape(c)
  if any(p['net']!=net(c)and set(z)&set(p['layers'])and g.distance(p['poly'])<(.126 if c[0]=='via'else .101)for p in moved):kill.add(item_id(c))
 remove_ids(t,kill);save(t);r=Router(t);p=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center']
 for n,nn,q in [('/VBAT_SENSE',4,(12.65,6.75)),('/I2C_SDA',5,(12.65,6.2))]:
  g=Point(q);bad=[(pp['ref'],pp['num'])for pp in ps if pp['net']!=n and g.distance(pp['poly'])<.3501-1e-6];badc=[net(c)for c in copper(t)if net(c)!=n and g.distance(shape(c)[0])<.35]
  print('VIA OBSTACLES',n,bad,badc,flush=True)
  if bad or badc:continue
  ok=r.link(n,p('U1',nn),[0],q,[0],False);print('ESCAPE',n,ok,flush=True)
  if ok:addvia(r,n,q)
 # Find an unconstrained northern SCL landing rather than guessing a position.
 n='/I2C_SCL';b,v=r.available(n);sites=[(x*.025,y*.025)for y,x in zip(*np.where(v))if 12.6<x*.025<15.5 and 2.3<y*.025<4.2];sites.sort(key=lambda q:math.dist(q,(13.5,3.7)))
 for q in sites[::3]:
  if r.link(n,p('U1',6),[0],q,[0],False):addvia(r,n,q);print('SCL ESCAPE',q,flush=True);break
 else:print('SCL BLOCKED',flush=True)
 save(t);r=Router(t,width=.127)
 for nn in [50,52]:print('DVDD',nn,r.link('+3V3',p('C11',1),[0],p('U2',nn),[0],False),flush=True)
 # Place the western VDD36 landing using the actual all-layer clearance mask.
 b,v=r.available('+3V3');sites=[(x*.025,y*.025)for y,x in zip(*np.where(v))if 2.4<x*.025<6.5 and 6.8<y*.025<9.3];sites.sort(key=lambda q:math.dist(q,p('C18',1)))
 for q in sites[::4]:
  if r.link('+3V3',p('C18',1),[0],q,[0],False):
   addvia(r,'+3V3',q);print('VDD36',q,r.link('+3V3',q,[1],(6.05,9.3),[1]),flush=True);break
 else:print('VDD36 BLOCKED',flush=True)
 save(t);check('nrf-escape2')
if __name__=='__main__':main()
