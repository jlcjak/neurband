"""Release raw-input crossovers while retaining endpoint fanouts."""
from route_c import *
r=Router(existing=True);i=r.ipc
ends={n:ps for n,ps in r.nets.items()if n.startswith('/E') and len(ps)==2}
keepvias={}
for n,ps in ends.items():
 rn=next(p for p in ps if p['ref'].startswith('RN'));j=next(p for p in ps if p['ref']=='J1')
 vs=[p for p in r.vias if p[2]==n]
 a=min(vs,key=lambda v:math.dist(v[:2],rn['center']))
 b=min(vs,key=lambda v:math.dist(v[:2],(j['center'][0],23+.7*(int(j['num'])%2))))
 keepvias[n]=[a,b]
remove=[]
for c in i.get(['KOT_PCB_TRACE','KOT_PCB_VIA']):
 n=c.get('net',{}).get('name')
 if n not in ends:continue
 if c['@type'].endswith('.Via'):
  a=coord(c['position']);keep=any(math.dist(a,p[:2])<.001 for p in keepvias[n])
 else:
  a,b=coord(c['start']),coord(c['end']);keep=False
  if c['layer']=='BL_F_Cu':
   for p in ends[n]:
    a0=p['center'];v=min(keepvias[n],key=lambda v:math.dist(v[:2],a0));g=LineString([a0,v[:2]])
    if g.distance(Point(*a))<.01 and g.distance(Point(*b))<.01:keep=True
 if not keep:remove.append(c['id']['value'])
i.begin();i.delete(remove);i.end('REV C: release raw-input crossovers for north FPC escapes');i.save();print('Released',len(remove),'copper items',flush=True)
r=Router(existing=True)
for n,x,y in [('/E7P',16.25,20.35),('/E7N',16.75,20.75),('/E8P',17.25,20.35)]:
 p=next(p for p in r.nets[n]if p['ref']=='J1');_,v=r.available(n);valid=bool(v[round(y/STEP),round(x/STEP)]);print('North exit',n,x,y,valid,flush=True)
 if not valid:continue
 path=r.search(n,[index(*p['center'],0)],[index(x,y,0)],via=False)
 if path is None:print('North path blocked',n,flush=True);continue
 r.commit_path(n,path,p['center'],(x,y));r.add_via(x,y,n);r.refresh(n)
r.save(incremental=True)
