"""Prune each native orphan independently, retaining necessary junctions."""
from native_check_c import *
def main():
 save(load(),BUILD/'before-single-prune.kicad_pcb'); rejected=set()
 for k in range(150):
  d=check('single-prune'); candidates=[i['uuid']for v in d['violations']if v['type']in ['track_dangling','via_dangling']for i in v['items']if i['uuid']not in rejected]
  if not candidates:break
  i=candidates[0];old=load();t=copy.deepcopy(old);remove_ids(t,{i});save(t);dd=check('single-prune-trial')
  if dd['unconnected_items']or any(v['severity']=='error'for v in dd['violations']):
   save(t,BUILD/('rejected-prune-'+i+'.kicad_pcb'));print('NEEDED JUNCTION',i,dd['unconnected_items'],flush=True);rejected.add(i);save(old)
 check('single-prune');print('REJECTED',sorted(rejected),flush=True)
if __name__=='__main__':main()
