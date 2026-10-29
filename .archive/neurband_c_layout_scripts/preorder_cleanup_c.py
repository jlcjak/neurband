"""Merge redundant overlapping drills and remove native-identified dead copper."""
from connect_components_c import *
def bridges(t,d):
 lookup={item_id(c):c for c in copper(t)};added=0
 for row in d['unconnected_items']:
  a,b=[lookup.get(i['uuid'])for i in row['items']]
  if a is None or b is None or a[0]!='segment'or b[0]!='segment'or get(a,'layer')!=get(b,'layer'):continue
  aa=[tuple(map(float,get(a,k)[1:3]))for k in ['start','end']];bb=[tuple(map(float,get(b,k)[1:3]))for k in ['start','end']];p,q=min(((p,q)for p in aa for q in bb),key=lambda pq:math.dist(*pq))
  if math.dist(p,q)<.35:wire(t,net(a),[p,q],uq(get(a,'layer')[1]),min(float(get(a,'width')[1]),float(get(b,'width')[1])));added+=1
 return added

def main():
 t=load();save(t,BUILD/'before-native-cleanup.kicad_pcb')
 merge=[('GND',(5.9,12.8),(5.9,12.6)),('GND',(2.925,7.6),(2.725,7.425)),('+3V3',(2.975,9.125),(3.0,9.125)),('VCHG',(10.725,9.45),(10.6,9.5)),('/SPI_MISO',(17.4,7.275),(17.375,7.25))]
 for n,old,q in merge:
  kill=set()
  for c in copper(t):
   if net(c)!=n:continue
   if c[0]=='via'and math.dist(tuple(map(float,get(c,'at')[1:3])),old)<.001:kill.add(item_id(c));continue
   if c[0]=='segment':
    for key in ['start','end']:
     p=get(c,key)
     if math.dist(tuple(map(float,p[1:3])),old)<.001:p[1:3]=list(map(num,q))
  remove_ids(t,kill)
 # Only the shorting land changes; the printed radiator and feed stay identical.
 for f in kids(t,'footprint'):
  if ref(f)=='AE1':
   for p in kids(f,'pad'):
    if uq(p[1])=='2':sz=get(p,'size');sz[1:]=[num(.6 if abs(float(v)-.5)<.0001 else float(v))for v in sz[1:]]
 save(t);d=check('cleanup')
 for k in range(50):
  ids={i['uuid']for v in d['violations']if v['type']in ['track_dangling','via_dangling']for i in v['items']if'[GND]'not in i['description']}
  if not ids:break
  before=load();t=copy.deepcopy(before);remove_ids(t,ids);save(t);d=check('cleanup')
  if bridges(t,d):save(t);d=check('cleanup')
  nonground=[row for row in d['unconnected_items']if not all('[GND]'in i['description']for i in row['items'])]
  errors=[v for v in d['violations']if v['severity']=='error']
  if nonground or errors:
   print('PRUNE ROLLBACK',k,len(nonground),len(errors),flush=True);save(before);d=check('cleanup');break
 print('CLEANUP PASSES',k,flush=True)
if __name__=='__main__':main()
