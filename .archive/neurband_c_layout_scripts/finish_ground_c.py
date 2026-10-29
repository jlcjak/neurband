"""Reserve the final bypass return before the low-rate ADC divider route."""
from route_c import *
r=Router(existing=True);i=r.ipc
remove=[c['id']['value']for c in i.get(['KOT_PCB_TRACE','KOT_PCB_VIA'])if c.get('net',{}).get('name')=='/VBAT_SENSE']
i.begin();i.delete(remove);i.end('REV C: reopen battery-sense route to preserve C30 ground');i.save()
r=Router(existing=True)
g=r.pad('C30',2)['center']
if not any(n=='GND'and math.dist((x,y),(28.05,.8))<.01 for x,y,n in r.vias):
 r.wire('GND',[g,(28.05,.8)],width=.127);r.add_via(28.05,.8,'GND');r.refresh('GND')
n='/VBAT_SENSE';a=r.pad('C30',1)['center'];b=r.pad('R7',1)['center'];c=r.pad('R6',2)['center']
r.wire(n,[a,(a[0],1.735),(b[0],1.735),b],width=.1);r.wire(n,[b,c],width=.1)
p=r.pad('U1',4);end=(12.675,6.725);r.wire(n,[p['center'],end]);r.add_via(*end,n);r.refresh(n)
# Low-rate divider exits below its row, outside all four lid-support discs.
a=(22.7,1.5);_,v=r.available(n)
if not v[round(a[1]/STEP),round(a[0]/STEP)]:raise RuntimeError('Divider via site no longer clear')
path=r.search(n,[index(*b,0)],[index(*a,0)],via=False)
if path is None:raise RuntimeError('Divider exit blocked')
r.commit_path(n,path,b,a);r.add_via(*a,n);r.refresh(n)
path=r.search(n,[index(*a,z)for z in range(3)],[index(*end,z)for z in range(3)],via=False)
if path is None:path=r.search(n,[index(*a,z)for z in range(3)],[index(*end,z)for z in range(3)])
if path is None:raise RuntimeError('ADC divider trunk blocked')
r.commit_path(n,path,a,end);r.save(incremental=True)
