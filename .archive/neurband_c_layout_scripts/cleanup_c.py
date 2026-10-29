"""Remove obsolete support-conflict stubs; merge same-net close drill pairs."""
from route_c import *
r=Router(existing=True);i=r.ipc;cs=i.get(['KOT_PCB_TRACE','KOT_PCB_VIA']);byid={c['id']['value']:c for c in cs}
report=json.loads((BUILD/'release2.json').read_text());removed=set()
for c in cs:
 if c.get('layer')=='BL_F_Cu'and c.get('net',{}).get('name')=='GND':
  a,b=coord(c['start']),coord(c['end'])
  if all(24.1<x<24.9 and .7<y<2.3 for x,y in [a,b]):removed.add(c['id']['value'])
for row in report['violations']:
 if row['type']!='hole_to_hole':continue
 ids=[q['uuid']for q in row['items']]
 if any(k in removed or k not in byid for k in ids):continue
 a,b=[byid[k]for k in ids]
 assert a['@type'].endswith('.Via')and b['@type'].endswith('.Via')
 assert a['net']['name']==b['net']['name']
 n=a['net']['name'];keep,drop=a,b;p,q=coord(keep['position']),coord(drop['position'])
 assert math.dist(p,q)<.551
 removed.add(drop['id']['value'])
 layers={c['layer']for c in cs if c.get('net',{}).get('name')==n and'layer'in c and c['layer']in LAYERS and LineString([coord(c['start']),coord(c['end'])]).distance(Point(*q))<.276}
 if n=='GND':layers.add('BL_F_Cu')
 for layer in layers:r.wire(n,[q,p],z=LAYERS.index(layer),width=.1)
 print('Merged close drills',n,q,'into',p,'layers',sorted(layers),flush=True)
i.begin();i.delete(list(removed));i.end('REV C: remove obsolete stubs and redundant close drilled holes');i.save();r.save(incremental=True)
print('Removed',len(removed),'obsolete copper items',flush=True)
