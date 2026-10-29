"""Route between real connected copper components, including existing vias."""
from preorder_connect_c import *
from shapely.strtree import STRtree

def connected(t,n):
 objs=[]
 for p in pad_data(t):
  if p['net']==n:objs.append((p['id'],p['poly'],p['layers'],[p['center']]))
 for c in copper(t):
  if net(c)!=n:continue
  g,zs=shape(c)
  if c[0]=='via':points=[tuple(map(float,get(c,'at')[1:3]))]
  else:
   a,b=[tuple(map(float,get(c,k)[1:3]))for k in ['start','end']];L=math.dist(a,b);points=[(a[0]+(b[0]-a[0])*q,a[1]+(b[1]-a[1])*q)for q in np.linspace(0,1,max(2,math.ceil(L/.15)+1))]
  objs.append((item_id(c),g,zs,points))
 par=list(range(len(objs)))
 def root(i):
  while par[i]!=i:par[i]=par[par[i]];i=par[i]
  return i
 tree=STRtree([o[1]for o in objs])
 for i,(_,g,z,_)in enumerate(objs):
  for j in tree.query(g.buffer(.0001)):
   if i<j and set(z)&set(objs[j][2])and g.distance(objs[j][1])<.0001:par[root(i)]=root(j)
 groups=collections.defaultdict(list);ids={}
 for i,o in enumerate(objs):groups[root(i)].append(o);ids[o[0]]=root(i)
 return ids,groups

def close_components(t,d):
 r=ReleaseRouter(t)
 for row in d['unconnected_items']:
  aa=[r.lookup.get(q['uuid'])for q in row['items']]
  if not all(aa):continue
  n=aa[0]['net'];ids,groups=connected(t,n)
  a,b=[ids[q['uuid']]for q in row['items']]
  if a==b:continue
  mask,_=r.available(n)
  def points(k):
   return list({r.idx(p,z)for _,g,zs,ps in groups[k]for p in ps for z in zs if not mask[z,round(p[1]/r.step),round(p[0]/r.step)]})
  starts,goals=points(a),points(b)
  path=r.search(n,starts,goals,True)if starts and goals else None
  print('COMPONENT',n,len(groups[a]),len(groups[b]),'nodes',len(starts),len(goals),'route',bool(path),flush=True)
  if path:
   p,q=r.coord(path[0]),r.coord(path[-1]);search=r.search;r.search=lambda *args,**kw:path
   r.link(n,p[:2],[p[2]],q[:2],[q[2]]);r.search=search;save(t)
 save(t)
def main():
 t=load();save(t,BUILD/'before-component-closure.kicad_pcb')
 for c in copper(t):
  for key in (['at']if c[0]=='via'else['start','end']):
   q=get(c,key);xy=tuple(map(float,q[1:3]));n=net(c)
   if n=='/I2C_SCL'and math.dist(xy,(12.675,5.7))<.001:q[1:3]=['12.65','5.75']
   if n=='/I2C_SDA'and math.dist(xy,(12.675,6.3))<.001:q[1:3]=['12.65','6.325']
 save(t);d=json.loads((BUILD/'connect-all-drc.json').read_text());close_components(t,d);check('component-closure')
if __name__=='__main__':main()
