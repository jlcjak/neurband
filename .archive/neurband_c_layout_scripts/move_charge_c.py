"""Final mechanical change: J3 moves toward y=0; all other parts stay fixed."""
from route_c import *
from place_c import P
r=Router(existing=True);i=r.ipc;before={ref(f):(f['position'],f.get('orientation'),f['layer'])for f in r.fs};j=next(f for f in r.fs if ref(f)=='J3')
cs=i.get(['KOT_PCB_TRACE','KOT_PCB_VIA']);remove=[c['id']['value']for c in cs if c.get('net',{}).get('name')=='VCHG']
i.begin();i.delete(remove);i.update([{'@type':j['@type'],'id':j['id'],'position':xy(14,6)}]);i.end('REV C: charge window VCHG14,6 and GND14,9');i.save()
r=Router(existing=True);pad=r.pad('J3',1)['poly'];remove=[];oldvias=[]
for c in i.get(['KOT_PCB_TRACE','KOT_PCB_VIA']):
 n=c.get('net',{}).get('name')
 if n=='VCHG':continue
 if c['@type'].endswith('.Via'):
  p=coord(c['position'])
  if Point(*p).distance(pad)<.37:remove.append(c['id']['value']);oldvias.append((n,p))
 elif c['layer']=='BL_B_Cu':
  g=LineString([coord(c['start']),coord(c['end'])]).buffer(int(c['width']['value_nm'])*.5e-6)
  if g.distance(pad)<.13:remove.append(c['id']['value'])
i.begin();i.delete(remove);i.end('REV C: clear existing routing from relocated charge pad');i.save();print('Cleared pad conflicts',len(remove),'vias',oldvias,flush=True)
r=Router(existing=True)
for n,old,new in [('/VBAT_SENSE',(13,6.7),(12.675,6.725)),('/I2C_SDA',(15.2,5.7),(15.4,5.7))]:
 if not any(nn==n and math.dist(p,old)<.01 for nn,p in oldvias):continue
 _,v=r.available(n)
 if not v[round(new[1]/STEP),round(new[0]/STEP)]:print('Preferred replacement via blocked',n,new,flush=True);continue
 layers={LAYERS.index(c['layer'])for c in cs if c.get('net',{}).get('name')==n and c.get('layer')in LAYERS and LineString([coord(c['start']),coord(c['end'])]).distance(Point(*old))<.276}
 connected=False
 for z in layers:
  path=r.search(n,[index(*old,z)],[index(*new,z)],via=False)
  if path is not None:r.commit_path(n,path,old,new);connected=True
 if connected:r.add_via(*new,n);r.refresh(n)
r.route_net('VCHG');r.save(incremental=True)
after={ref(f):(f['position'],f.get('orientation'),f['layer'])for f in i.get(['KOT_PCB_FOOTPRINT'])}
assert set(before)==set(after)
assert [k for k in before if before[k]!=after[k]]==['J3']
assert coord(after['J3'][0])==(14.,6.)
(PCB.parent/'layout/placement.json').write_text(json.dumps(P,indent=2))
print('Verified ONLY J3 moved: VCHG14,6 GND14,9; all66 other placements fixed',flush=True)
