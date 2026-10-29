"""Remove power detours that isolate AFE bypass ground, then restore supply connectivity."""
from preorder_pair_layers_c import *
def main():
 t=load();save(t,BUILD/'before-open-return-lanes.kicad_pcb');cut=set()
 for c in copper(t):
  g,z=shape(c)
  if c[0]=='segment'and z==[0]and ((net(c)=='+3V3'and g.intersects(box(15.3,6.9,17,9.9)))or(net(c)=='+3V3A'and g.intersects(box(15.35,10.0,18.0,10.7)))):cut.add(item_id(c))
  if c[0]=='via'and net(c)=='+3V3'and any(math.dist(tuple(map(float,get(c,'at')[1:3])),q)<.001 for q in [(15.975,8.35),(16.675,9.65)]):cut.add(item_id(c))
 remove_ids(t,cut);print('POWER DETOURS REMOVED',len(cut),flush=True);r=InputRouter(t,width=.127);r.margin=.001
 for n in list(r.geometry):r.refresh(n)
 ps=pad_data(t)
 for nn,target in [(51,(16.6,7.3)),(53,(16.6,9)),(57,(16.2375,10.85)),(58,(16.2375,10.85))]:
  p=next(p for p in ps if p['ref']=='U2'and p['num']==str(nn));print('GROUND',nn,r.link('GND',p['center'],[0],target,[0],False),flush=True)
 save(t);d=check('return-lanes');close_components(t,d);check('return-lanes-closed')
if __name__=='__main__':main()
