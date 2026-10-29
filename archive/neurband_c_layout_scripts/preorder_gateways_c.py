"""Reserve all-layer drill gateways before rerouting the crossing signals."""
from connect_components_c import *
def main():
 t=load();save(t,BUILD/'before-gateways.kicad_pcb');ps=pad_data(t)
 plans=[('/SPI_SCK','U1','9',(12.7,4.7),0),('/ADC_CS','U1','8',(13.4,4.7),0),('/ADC_START','U1','16',(10,1.7),0),('VBAT','R6','1',(20.2,1.5),0),('/NRST','TP4','1',(19,24.65),2),('/SWDCLK','TP3','1',(18.5,24.0),2)]
 sites=[]
 for n,rr,nn,q,z in plans:
  p=next(p for p in ps if p['ref']==rr and p['num']==nn)
  bad=[(p0['ref'],p0['num'],round(Point(q).distance(p0['poly'])-.15,4))for p0 in ps if p0['net']!=n and Point(q).distance(p0['poly'])<.34999]
  print('PAD CHECK',n,bad,flush=True)
  if not bad:sites.append((n,p,q,z))
 kill=set()
 for c in copper(t):
  for n,p,q,z in sites:
   if net(c)!=n and Point(q).distance(shape(c)[0])<.355:
    assert net(c)not in {'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'}
    kill.add(item_id(c))
 print('Rework obstructing copper',collections.Counter(net(c)for c in copper(t)if item_id(c)in kill),flush=True);remove_ids(t,kill)
 for n,p,q,z in sites:t.append(via(*q,n))
 save(t);r=ReleaseRouter(t)
 for n,p,q,z in sites:print('GATEWAY',n,q,r.link(n,p['center'],[z],q,[z],False),flush=True)
 save(t);d=check('gateways');close_components(t,d);check('gateways-closed')
if __name__=='__main__':main()
