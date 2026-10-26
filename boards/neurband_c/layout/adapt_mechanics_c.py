"""Preserve placements; widen right edge for ordinary drills and clear lid supports."""
from route_c import *
from place_c import outline
r=Router(existing=True);i=r.ipc;remove=[]
for c in i.get(['KOT_PCB_TRACE','KOT_PCB_VIA']):
 if c['@type'].endswith('.Via'):
  p=coord(c['position']);g=Point(*p).buffer(int(c['pad_stack']['copper_layers'][0]['size']['x_nm'])*.5e-6)
 elif c.get('layer')=='BL_B_Cu':
  p=coord(c['start']);g=LineString([p,coord(c['end'])]).buffer(int(c['width']['value_nm'])*.5e-6)
 else:continue
 if any(g.distance(s)<.06 for s in r.supports):
  remove.append(c['id']['value']);print('Removing support conflict',c['@type'].split('.')[-1],c.get('net',{}).get('name'),p,flush=True)
i.begin();i.delete([s['id']['value']for s in i.get(['KOT_PCB_SHAPE'])]);i.create(outline());i.delete(remove)
i.create([core.item_via(28.05,y,'GND')for y in [7.88,11.88]])
i.end('REV C: 28.7mm surcharge-free outline and bottom support clearance');i.save()
print('Removed',len(remove),'conflicting copper items; retained every component/pad coordinate')
