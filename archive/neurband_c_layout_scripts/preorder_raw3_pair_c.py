"""Route both channel-3 connector legs together on one signal layer."""
from preorder_pair_layers_c import *
def main():
 old=load();save(old,BUILD/'before-raw3-pair.kicad_pcb');ns=['/E3P','/E3N']
 for layer in [2,1,0]:
  for order in [ns,ns[::-1]]:
   for margin in [.003,0]:
    t=copy.deepcopy(old);remove_ids(t,{item_id(c)for c in copper(t)if net(c)in ns});r=InputRouter(t);r.margin=margin
    for nn in list(r.geometry):r.refresh(nn)
    ok=True
    for k,n in enumerate(order):
     ps=[p for p in pad_data(t)if p['net']==n];a=next(p for p in ps if p['ref']=='J1');b=next(p for p in ps if p['ref'].startswith('RN'))
     if layer==0:good=r.link(n,a['center'],[0],b['center'],[0],False)
     else:
      qa=viaescape(r,n,a['center'],(a['center'][0],23.2-k*.6),.9);qb=viaescape(r,n,b['center'],(b['center'][0],20.4-k*.45),.85)
      good=qa is not None and qb is not None and r.link(n,qa,[layer],qb,[layer],False)
     print('RAW3',n,LAYERS[layer],margin,good,flush=True)
     if not good:ok=False;break
    if not ok:continue
    save(t);d=check('raw3-pair');errors=[v for v in d['violations']if v['severity']=='error']
    if not errors:print('RAW3 ACCEPT',LAYERS[layer],flush=True);return
 save(old);check('raw3-retained')
if __name__=='__main__':main()
