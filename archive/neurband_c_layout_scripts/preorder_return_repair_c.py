"""Complete local bypass supply/return links without altering the fixed interface."""
from preorder_pair_layers_c import *
def main():
 t=load();save(t,BUILD/'before-return-repair.kicad_pcb')
 remove_ids(t,{item_id(c)for c in kids(t,'via')if math.dist(tuple(map(float,get(c,'at')[1:3])),(9,9.375))<.001})
 f=next(f for f in kids(t,'footprint')if ref(f)=='C29');move(f,24,3.2,0)
 ps=pad_data(t);p=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center']
 r=InputRouter(t,width=.127);r.margin=.001
 for n in list(r.geometry):r.refresh(n)
 print('C29 SUPPLY',r.link('+3V3A',p('C29',1),[0],p('C28',1),[0],False),flush=True)
 for nn,target in [(51,(16.6,7.3)),(53,(16.6,9.0)),(57,(16.6,9.0)),(58,(16.6,9.0))]:print('GROUND',nn,r.link('GND',p('U2',nn),[0],target,[0],False),flush=True)
 save(t);check('return-repaired')
if __name__=='__main__':main()
