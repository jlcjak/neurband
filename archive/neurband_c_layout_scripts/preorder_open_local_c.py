"""Free the RC-feed star and move a bias barrel clear of the input escape."""
from preorder_pair_layers_c import *
def main():
 t=load();save(t,BUILD/'before-local-openings.kicad_pcb');ps=pad_data(t);by={ref(f):f for f in kids(t,'footprint')};old=[p for p in ps if p['ref']=='C29'];kill=set()
 for c in copper(t):
  g,z=shape(c)
  if c[0]=='segment'and 0 in z and any(net(c)==p['net']and g.distance(p['poly'])<.01 for p in old):kill.add(item_id(c))
  if net(c)=='+3V3A'and(c[0]=='via'and math.dist(tuple(map(float,get(c,'at')[1:3])),(21.075,1.5))<.001 or c[0]=='segment'and 0 in z and g.intersects(box(19.5,1.2,21.5,2.7))):kill.add(item_id(c))
 remove_ids(t,kill);move(by['C29'],14.85,2,90)
 moved=[p for p in pad_data(t)if p['ref']=='C29'];kill=set()
 for c in copper(t):
  g,z=shape(c)
  if any(net(c)!=p['net']and set(z)&set(p['layers'])and g.distance(p['poly'])<(.126 if c[0]=='via'else .101)for p in moved):kill.add(item_id(c))
 remove_ids(t,kill);save(t);r=Router(t);b,v=r.available('/BIAS_E');oldq=(13.925,20.4);ys,xs=np.where(v);sites=[(x*.025,y*.025)for y,x in zip(ys,xs)if math.dist((x*.025,y*.025),oldq)<.2];sites.sort(key=lambda q:math.dist(q,(13.8,20.4)))
 if sites:
  newq=sites[0];print('BIAS BARREL',oldq,newq,flush=True);lys=set();kill=set()
  for c in copper(t):
   if net(c)!='/BIAS_E':continue
   if c[0]=='via'and math.dist(tuple(map(float,get(c,'at')[1:3])),oldq)<.001:kill.add(item_id(c))
   elif c[0]=='segment'and Point(oldq).distance(shape(c)[0])<.001:lys.add(uq(get(c,'layer')[1]))
  remove_ids(t,kill);t.append(via(*newq,'/BIAS_E'))
  for ly in lys:wire(t,'/BIAS_E',[oldq,newq],ly,.1)
 save(t);d=check('local-openings');close_components(t,d);check('local-openings-closed')
 t=load();t,ok=try_net(t,'/E5P',0);save(t);print('E5 F ROUTE',ok,flush=True);check('local-openings-final')
if __name__=='__main__':main()
