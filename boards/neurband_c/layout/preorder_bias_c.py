"""Place bypass and bias reference in the order of the ADS left-hand pins."""
from connect_components_c import *
def main():
 t=load();save(t,BUILD/'before-bias-reorder.kicad_pcb');by={ref(f):f for f in kids(t,'footprint')};old=[p for p in pad_data(t)if p['ref']in['C9','C32']];kill=set()
 for c in copper(t):
  g,z=shape(c)
  if c[0]=='segment'and 0 in z and any(net(c)==p['net']and g.distance(p['poly'])<.001 for p in old):kill.add(item_id(c))
 remove_ids(t,kill);move(by['C9'],13.075,11.75,270);move(by['C32'],11.65,12.0,180)
 ps=pad_data(t);moved=[p for p in ps if p['ref']in['C9','C32']];kill=set()
 for c in copper(t):
  g,z=shape(c)
  if any(p['net']!=net(c)and set(z)&set(p['layers'])and g.distance(p['poly'])<(.126 if c[0]=='via'else .101)for p in moved):kill.add(item_id(c))
 remove_ids(t,kill);save(t);r=ReleaseRouter(t);p=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center']
 for n,aa,bb in [('+3V3A',p('C9',1),p('U2',59)),('/RLDREF',p('C32',1),p('U2',60)),('Net-(U2-RLDINV)',p('R1',2),p('U2',61))]:print('BIAS LOCAL',n,r.link(n,aa,[0],bb,[0],False),flush=True)
 save(t);d=check('bias-reorder');close_components(t,d);check('bias-closed')
if __name__=='__main__':main()
