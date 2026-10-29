"""Repair the crystal/VDD36 escape and give the bias shunt a clear drill web."""
from file_layout_c import *
class TopRouter(Router):
 def available(self,n):
  b,v=super().available(n)
  if n in {'Net-(U1-XC1)','Net-(U1-XC2)'}:b[1:]=1;v[:]=0
  return b,v

def main():
 t=load();by={ref(f):f for f in kids(t,'footprint')};ps=pad_data(t)
 oldpads=[p for p in ps if p['ref']in ['C18','C20']]
 remove_ids(t,{item_id(c)for c in copper(t)if net(c)in ['Net-(U1-XC1)','Net-(U1-XC2)']or(c[0]=='segment'and net(c)in ['+3V3','GND']and any(p['net']==net(c)and shape(c)[0].distance(p['poly'])<.1 for p in oldpads))})
 for ref0,xyz in {'C18':(4.1,7.9,180),'C20':(6.8,10.4,0),'C34':(11.3,14.8,180)}.items():move(by[ref0],*xyz)
 for c in copper(t):
  if c[0]!='segment'or net(c)not in ['/BIAS_E','GND']:continue
  for k in ['start','end']:
   q=get(c,k)
   if math.dist(tuple(map(float,q[1:3])),(11.78,15.0)if net(c)=='/BIAS_E'else(10.82,15.0))<.01:q[2]='14.8'
 ps=pad_data(t);moved=[p for p in ps if p['ref']in ['C18','C20']];kill=set()
 for c in copper(t):
  g,zs=shape(c)
  if any(p['net']!=net(c)and set(zs)&set(p['layers'])and g.distance(p['poly'])<(.126 if c[0]=='via'else .101)for p in moved):
   assert net(c)not in {'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'};kill.add(item_id(c))
 remove_ids(t,kill);save(t);r=TopRouter(t)
 for n in ['Net-(U1-XC2)','Net-(U1-XC1)']:
  pps=[p for p in ps if p['net']==n];a=next(p for p in pps if p['ref']=='U1');b=next(p for p in pps if p['ref']=='Y1');c=next(p for p in pps if p['ref'].startswith('C'))
  assert r.link(n,a['center'],[0],b['center'],[0],False),(n,'crystal')
  assert r.link(n,b['center'],[0],c['center'],[0],False),(n,'load')
  print('CLOCK',n,'connected on F.Cu',flush=True)
 save(t);r=Router(t,width=.127);ps=pad_data(t);p=lambda ref0,k:next(p for p in ps if p['ref']==ref0 and p['num']==str(k))['center']
 print('VDD36 local stub',r.link('+3V3',p('U1',36),[0],(6.05,9.3),[0],False),flush=True)
 wire(t,'+3V3',[p('C18',1),(4.5,7.2)],w=.127)
 t.extend([via(6.05,9.3,'+3V3'),via(4.5,7.2,'+3V3')])
 save(t);r=Router(t,width=.127)
 print('VDD36 capacitor link',r.link('+3V3',(6.05,9.3),[1],(4.5,7.2),[1]),flush=True)
 save(t)
if __name__=='__main__':main()
