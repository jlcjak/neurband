"""Resolve the remaining local escapes and restore compact RLD feedback."""
from connect_components_c import *

def escape(r,n,rr,nn,target,rad=.6,layer=0):
 p=next(p for p in r.pads if p['ref']==rr and p['num']==str(nn));ids,groups=connected(r.t,n);comp=groups[ids[p['id']]];b,v=r.available(n)
 starts=list({r.idx(q,z)for _,g,zs,ps in comp for q in ps for z in zs if z==layer and not b[z,round(q[1]/.025),round(q[0]/.025)]})
 ys,xs=np.where(v);sites=[(x*.025,y*.025)for y,x in zip(ys,xs)if math.dist((x*.025,y*.025),target)<rad];sites.sort(key=lambda q:math.dist(q,target))
 goals=[r.idx(q,layer)for q in sites[::2]]
 path=r.search(n,starts,goals,False)if starts and goals else None
 print('LOCAL ESCAPE',n,bool(path),flush=True)
 if path:
  a,q=r.coord(path[0]),r.coord(path[-1]);search=r.search;r.search=lambda *args,**kw:path;r.link(n,a[:2],[a[2]],q[:2],[q[2]]);r.search=search;addvia(r,n,q[:2]);save(r.t)
 return bool(path)
def main():
 t=load();save(t,BUILD/'before-local-close.kicad_pcb');by={ref(f):f for f in kids(t,'footprint')};old=[p for p in pad_data(t)if p['ref']in['C32','R6']];kill=set()
 for c in copper(t):
  g,z=shape(c)
  if c[0]=='segment'and 0 in z and any(net(c)==p['net']and g.distance(p['poly'])<.001 for p in old):kill.add(item_id(c))
 remove_ids(t,kill);move(by['C32'],12.35,11.8,180);move(by['R6'],20.7,.8,0)
 ps=pad_data(t);moved=[p for p in ps if p['ref']in['C32','R6']];kill=set()
 for c in copper(t):
  g,z=shape(c)
  if any(p['net']!=net(c)and set(z)&set(p['layers'])and g.distance(p['poly'])<(.126 if c[0]=='via'else .101)for p in moved):kill.add(item_id(c))
 remove_ids(t,kill);save(t);r=ReleaseRouter(t)
 for n,rr,nn,target,rad,ly in [('/SPI_SCK','U1',9,(12.7,4.7),.2,0),('/ADC_CS','U1',8,(13.35,4.65),.3,0),('/ADC_START','U1',16,(10.0,1.7),.5,0),('VBAT','R6',1,(20.2,1.5),.5,0),('/NRST','TP4',1,(19.0,24.6),1.4,2),('/SWDCLK','TP3',1,(18.3,24.3),1.4,2)]:
  try:escape(r,n,rr,nn,target,rad,ly)
  except (StopIteration,KeyError)as e:print('NO PAD',rr,nn,flush=True)
 save(t);r=ReleaseRouter(t,width=.127);p=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center']
 print('RLDREF LOCAL',r.link('/RLDREF',p('U2',60),[0],p('C32',1),[0],False),flush=True)
 print('RLDINV LOCAL',r.link('Net-(U2-RLDINV)',p('U2',61),[0],p('R1',2),[0],False),flush=True)
 save(t);d=check('local-close');close_components(t,d);check('local-close-all')
if __name__=='__main__':main()
