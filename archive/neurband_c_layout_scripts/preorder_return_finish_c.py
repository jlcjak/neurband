"""Finish off-pad ground returns and keep two thermal spokes at bypass pads."""
from preorder_pair_layers_c import *
def main():
 t=load();save(t,BUILD/'before-return-finish.kicad_pcb');by={ref(f):f for f in kids(t,'footprint')}
 for c in kids(t,'segment'):
  if net(c)=='GND'and uq(get(c,'layer')[1])=='F.Cu'and shape(c)[0].distance(Point(15.525,11.25))<.351:setc(c,'width','.1')
 for p in kids(by['C13'],'pad'):
  if net(p)=='GND':setc(p,'thermal_gap','.1');setc(p,'thermal_bridge_angle','45')
 old=next(p for p in pad_data(t)if p['ref']=='C29'and p['num']=='1')['center'];move(by['C29'],14.85,1.1,90)
 ps=pad_data(t);r=InputRouter(t,width=.127);r.margin=0
 for n in list(r.geometry):r.refresh(n)
 p=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center']
 print('C29 SUPPLY',r.link('+3V3A',p('C29',1),[0],old,[0],False),flush=True)
 print('C29 GROUND',r.link('GND',p('C29',2),[0],p('C16',2),[0],False),flush=True)
 save(t);check('returns-finished')
if __name__=='__main__':main()
