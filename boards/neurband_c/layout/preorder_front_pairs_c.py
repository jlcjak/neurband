"""Keep paired input legs on F.Cu over the dedicated inner ground plane where routable."""
from preorder_pair_layers_c import *
def front_pair(old,ns):
 for order in [ns,ns[::-1]]:
  for margin in [.003,0]:
   t=copy.deepcopy(old);remove_ids(t,{item_id(c)for c in copper(t)if net(c)in ns});r=InputRouter(t);r.margin=margin
   for nn in list(r.geometry):r.refresh(nn)
   ok=True
   for n in order:
    ps=[p for p in pad_data(t)if p['net']==n];assert len(ps)==2,(n,len(ps));a,b=ps
    good=r.link(n,a['center'],[0],b['center'],[0],False);print('FRONT',n,margin,good,flush=True)
    if not good:ok=False;break
   if not ok:continue
   save(t);d=check('front-pairs')
   if not any(v['severity']=='error'for v in d['violations'])and not d['unconnected_items']:return load(),True
 save(old);return old,False
def main():
 t=load();save(t,BUILD/'before-front-input-pairs.kicad_pcb');rows=[]
 pairs=[['Net-(RN3A-R1.1)','Net-(RN3B-R2.1)'],['Net-(RN4C-R3.1)','Net-(RN4D-R4.1)'],['Net-(RN1A-R1.1)','Net-(RN1B-R2.1)'],['Net-(RN2C-R3.1)','Net-(RN2D-R4.1)'],['Net-(RN3C-R3.1)','Net-(RN3D-R4.1)'],['Net-(RN4A-R1.1)','Net-(RN4B-R2.1)'],['/E2P','/E2N'],['/E8P','/E8N'],['/E3P','/E3N'],['/E1P','/E1N'],['/E4P','/E4N'],['/E7P','/E7N']]
 for ns in pairs:
  t,ok=front_pair(t,ns);rows.append(dict(nets=ns,front=ok));print('FRONT PAIR RESULT',ns,ok,flush=True)
 save(t);(BUILD/'front-pair-results.json').write_text(json.dumps(rows,indent=2)+'\n');check('front-inputs')
if __name__=='__main__':main()
