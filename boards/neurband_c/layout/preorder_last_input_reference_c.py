"""Try the remaining common-layer input pair without disturbing accepted routing."""
from preorder_reference_inputs_c import *
def main():
 save(load(),BUILD/'before-last-reference-pairs.kicad_pcb');rows=[]
 for ns in [['/E7P','/E7N'],['/E8P','/E8N']]:
  old=load();success=False
  for order in [ns,ns[::-1]]:
   t=copy.deepcopy(old);remove_ids(t,{item_id(c)for c in kids(t,'segment')if net(c)in ns and uq(get(c,'layer')[1])in ['In2.Cu','B.Cu']});r=ReferenceRouter(t);r.margin=.001
   for n in list(r.geometry):r.refresh(n)
   if not all(route_groups(t,r,n)for n in order):continue
   before_ids={item_id(c)for c in copper(old)};newlength=sum(LineString([tuple(map(float,get(c,k)[1:3]))for k in ['start','end']]).length for c in kids(t,'segment')if item_id(c)not in before_ids)
   if newlength>35:continue
   save(t);d=check('last-reference-pair');ok=not d['unconnected_items']and not any(v['severity']=='error'for v in d['violations'])
   if ok:success=True;break
   save(old)
  if not success:save(old)
  rows.append(dict(nets=ns,success=success));print('LAST PAIR',rows[-1],flush=True)
 (BUILD/'last-reference-pairs.json').write_text(json.dumps(rows,indent=2)+'\n');check('last-reference-final')
if __name__=='__main__':main()
