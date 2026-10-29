"""Compact the VREFP tree and anchor the formerly isolated AVSS3 return."""
from preorder_pair_layers_c import *
def main():
 t=load();save(t,BUILD/'before-reference-return.kicad_pcb');n='Net-(U2-VREFP)';remove_ids(t,{item_id(c)for c in copper(t)if net(c)==n});r=InputRouter(t);r.margin=0
 for nn in list(r.geometry):r.refresh(nn)
 ps=pad_data(t);p=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center']
 print('AVSS3',r.link('GND',p('U2',23),[0],(24.25,10.25),[0],False),flush=True)
 print('VREF MAIN',r.link(n,p('U2',24),[0],p('C6',1),[0],False),flush=True)
 print('VREF BYPASS',r.link(n,p('C6',1),[0],p('C1',1),[0],False),flush=True)
 save(t);d=check('reference-return')
 if any(v['severity']=='error'for v in d['violations'])or d['unconnected_items']:
  print('RESTORE',flush=True);t=load(BUILD/'before-reference-return.kicad_pcb');save(t);check('reference-retained')
if __name__=='__main__':main()
