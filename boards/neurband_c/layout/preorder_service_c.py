"""Give the two service nets dedicated bottom-edge exits outside the input fanout."""
from connect_components_c import *
def main():
 t=load();save(t,BUILD/'before-service-exits.kicad_pcb');keep=[];kill=set()
 for c in copper(t):
  n=net(c);g,z=shape(c)
  if n in ['/NRST','/SWDCLK']:
   # Retain only the known local nRF pin-to-via escapes.
   if c[0]=='via':retain=tuple(map(float,get(c,'at')[1:3]))in[(6.4,.65),(5.525,3)]
   else:retain=0 in z and g.bounds[2]<7 and g.bounds[3]<4
   if not retain:kill.add(item_id(c))
  if n=='/BIAS_E'and g.bounds[3]>23.5:kill.add(item_id(c))
 remove_ids(t,kill)
 for n,q,pts in [('/NRST',(7.4,26.1),[(19.81,25.7),(19.81,26.55),(7.4,26.55),(7.4,26.1)]),('/SWDCLK',(8.2,26.1),[(18.54,25.7),(18.54,26.35),(8.2,26.35),(8.2,26.1)])]:
  t.append(via(*q,n));wire(t,n,pts,'B.Cu',.1)
 save(t);d=check('service-exits');close_components(t,d);check('service-closed')
if __name__=='__main__':main()
