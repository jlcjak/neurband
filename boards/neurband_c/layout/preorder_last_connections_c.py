"""Finish the top-row and service-pin gateways and the RLD reference stub."""
from connect_components_c import *
def main():
 t=load();save(t,BUILD/'before-last-connections.kicad_pcb');ps=pad_data(t);by={ref(f):f for f in kids(t,'footprint')}
 for n in {net(c)for c in copper(t)}-{'GND'}:
  ids,gs=connected(t,n);pads={p['id']for p in ps if p['net']==n};remove_ids(t,{o[0]for os in gs.values()if not any(o[0]in pads for o in os)for o in os})
 old=next(p for p in ps if p['ref']=='C32'and p['num']=='1')['center'];move(by['C32'],11.5,12,180)
 for c in copper(t):
  if c[0]!='segment'or net(c)not in ['/RLDREF','GND']:continue
  for key in ['start','end']:
   q=get(c,key);xy=tuple(map(float,q[1:3]))
   for oldxy in [old,(11.17,12)]:
    if math.dist(xy,oldxy)<.001:q[1]=num(xy[0]-.15)
 for p in pad_data(t):
  if p['ref']=='C9'and p['net']=='GND':setc(p['node'],'thermal_bridge_angle',0)
 ps=pad_data(t);getp=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center']
 plans=[('/SPI_MISO',getp('U2',43),(18.95,3.15),0),('/ADC_START',getp('U2',38),(21.45,3.3),0),('/ADC_PWDN',getp('U1',17),(9.4,1.0),0),('/SWDCLK',(18.5,24),(19.25,22.4),0)]
 kill=set()
 for n,a,q,z in plans:
  bad=[(p['ref'],p['num'])for p in ps if p['net']!=n and Point(q).distance(p['poly'])<.34999];print('SITE',n,bad,flush=True)
  assert not bad,(n,bad)
  for c in copper(t):
   if net(c)!=n and Point(q).distance(shape(c)[0])<.355:kill.add(item_id(c))
 remove_ids(t,kill)
 # The front-layer reference crosses the insulating body gap between C9 lands.
 quiet=[getp('U2',60),(13.6,11.85),(13.5,11.75),(12.5,11.75),getp('C32',1)]
 g=LineString(quiet).buffer(.05)
 for c in copper(t):
  h,z=shape(c)
  if 0 in z and net(c)not in ['/RLDREF','GND']and g.distance(h)<.10001:
   print('REF REWORK',net(c),flush=True);kill.add(item_id(c))
 remove_ids(t,kill);wire(t,'/RLDREF',quiet,w=.1)
 for n,a,q,z in plans:t.append(via(*q,n))
 save(t);r=ReleaseRouter(t)
 for n,a,q,z in plans:print('GATEWAY',n,r.link(n,a,[z],q,[z],False),flush=True)
 save(t);d=check('last-connections');close_components(t,d);check('last-connected')
if __name__=='__main__':main()
