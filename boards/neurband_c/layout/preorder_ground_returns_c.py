"""Join AFE ground pins to the existing return vias beneath the package."""
from preorder_pair_layers_c import *

def main():
 t=load();save(t,BUILD/'before-explicit-ground-returns.kicad_pcb');ps=pad_data(t);r=InputRouter(t);r.margin=.003
 for nn in list(r.geometry):r.refresh(nn)
 c29=next(p for p in ps if p['ref']=='C29'and p['num']=='1');q=viaescape(r,'+3V3A',c29['center'],(14.3,3.3),.6);print('FILTER CAP VIA',q,flush=True)
 # The nRF EP remains free of via holes and solder-mask openings.
 t.append(via(9,9.375));save(t);r=InputRouter(t,width=.25);r.margin=.01
 for n in list(r.geometry):r.refresh(n)
 for nn,target in [(51,(16.6,7.3)),(53,(16.6,9.0)),(57,(16.6,9.0)),(58,(16.6,9.0))]:
  p=next(p for p in ps if p['ref']=='U2'and p['num']==str(nn));print('AFE GROUND',nn,r.link('GND',p['center'],[0],target,[0],False),flush=True)
 save(t);r=InputRouter(t,width=.127);r.margin=.001
 for n in list(r.geometry):r.refresh(n)
 p=next(p for p in ps if p['ref']=='C3'and p['num']=='2');g=next(p for p in ps if p['ref']=='U2'and p['num']=='57');print('BYPASS GROUND',r.link('GND',p['center'],[0],g['center'],[0],False),flush=True)
 save(t);d=check('explicit-ground');close_components(t,d);check('explicit-ground-closed')
if __name__=='__main__':main()
