"""Close electrical components, not an arbitrary nearest pair of DRC segments."""
from route_c import *
from shapely.strtree import STRtree
r=Router(existing=True);i=r.ipc
report=json.loads((BUILD/((sys.argv[1]if len(sys.argv)>1 else'closed1')+'.json')).read_text())
# Reserve top-side escape channels for every raw FPC terminal before any
# crossover can seal a later terminal into a three-layer copper cage.
for n,ps in r.nets.items():
 if not n.startswith('/E'):continue
 for p in ps:
  if p['ref']=='J1':
   x,y=p['center'];r.geometry[n][0].append(LineString([(x,20.35),(x,y)]).buffer(.05));r.refresh(n)
wanted=set()
for row in report['unconnected_items']:
 for q in row['items']:
  if q['uuid']in r.lookup:wanted.add(r.lookup[q['uuid']]['net'])
allc=i.get(['KOT_PCB_TRACE','KOT_PCB_VIA'])
for n in sorted(wanted-{'GND'},key=lambda n:(0,-int(n[2:-1]),n[-1])if n.startswith('/E')else(1,0,n)):
 nodes=[dict(p,shape=p['poly'],points=[p['center']])for p in r.nets[n]]
 for c in allc:
  if c.get('net',{}).get('name')!=n:continue
  if c['@type'].endswith('.Via'):
   p=coord(c['position']);g=Point(*p).buffer(int(c['pad_stack']['copper_layers'][0]['size']['x_nm'])*.5e-6);points=[p];ls=[0,1,2]
  else:
   points=[coord(c['start']),coord(c['end'])];g=LineString(points).buffer(int(c['width']['value_nm'])*.5e-6);ls=[LAYERS.index(c['layer'])]
  nodes.append({'id':c['id'],'shape':g,'points':points,'layers':ls})
 parent=list(range(len(nodes)))
 def root(k):
  while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
  return k
 for z in range(3):
  rows=[k for k,p in enumerate(nodes)if z in p['layers']];gs=[nodes[k]['shape']for k in rows];tree=STRtree(gs)
  for a,g in enumerate(gs):
   for b in tree.query(g.buffer(.0005),predicate='intersects'):
    ra,rb=root(rows[a]),root(rows[int(b)])
    if ra!=rb:parent[rb]=ra
 groups=collections.defaultdict(list)
 for k,p in enumerate(nodes):groups[root(k)].append(p)
 orphan=[p['id']['value']for ps in groups.values()if not any('ref'in p for p in ps)for p in ps]
 if orphan:
  i.begin();i.delete(orphan);i.end('REV C: remove unused disconnected copper');i.save();print('Pruned orphan copper',n,len(orphan),flush=True)
 groups=[ps for ps in groups.values()if any('ref'in p for p in ps)]
 print(n,'electrical components',len(groups),flush=True)
 def ends(ps):
  out={}
  for p in ps:
   for a in p['points']:
    for z in p['layers']:out[index(*a,z)]=a
  return out
 groups.sort(key=lambda ps:len(ps),reverse=True)
 if len(groups)<2:continue
 main=groups.pop(0);a=ends(main)
 for ps in groups:
  b=ends(ps);path=r.search(n,list(b),list(a),via=False)
  if path is None:path=r.search(n,list(b),list(a))
  if path is None:print('COMPONENT FAILED',n,'nodes',len(ps),'from',list(b.values())[:3],flush=True);r.failed.append(n);continue
  r.commit_path(n,path,b[path[0]],a[path[-1]]);a.update(b)
  for q in path[::max(1,len(path)//100)]:a[q]=position(q)[:2]
  print('Joined',n,'path nodes',len(path),flush=True)
r.save(incremental=True)
