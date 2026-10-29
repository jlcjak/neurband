"""Put each formerly mixed-layer differential pair on a common signal/reference layer."""
from connect_components_c import *
class InputRouter(ReleaseRouter):
 margin=.01
 def available(self,n):
  b,v=super().available(n)
  vv=[Point(x,y).buffer(.3999999,quad_segs=32)for x,y,nn in self.vias if nn!=n]
  if vv:b[:,self.raster(unary_union(vv))]=1
  return b,v
 def refresh(self,n):
  if n in self.masks:self.total-=self.masks[n];self.vtotal-=self.vmasks[n]
  gs=self.geometry[n];m=np.zeros_like(self.total,dtype=bool)
  for z in range(3):
   if gs[z]:m[z]=self.raster(unary_union(gs[z]).buffer(.1+self.width/2+self.margin,quad_segs=12))
  v=self.raster(unary_union([g for ll in gs for g in ll]).buffer(.35+.01,quad_segs=12));self.masks[n]=m;self.vmasks[n]=v;self.total+=m;self.vtotal+=v

def viaescape(r,n,p,target,rad):
 mask,v=r.available(n);ys,xs=np.where(v);sites=[(x*.025,y*.025)for y,x in zip(ys,xs)if math.dist((x*.025,y*.025),target)<rad];sites.sort(key=lambda q:math.dist(q,target));goals=[r.idx(q,0)for q in sites]
 path=r.search(n,[r.idx(p,0)],goals,False)if goals else None
 if not path:return None
 a,q=r.coord(path[0]),r.coord(path[-1]);search=r.search;r.search=lambda *args,**kw:path;r.link(n,p,[0],q[:2],[0]);r.search=search;addvia(r,n,q[:2]);return q[:2]
def try_net(t,n,layer):
 old=copy.deepcopy(t);save(t,BUILD/('before-pair-'+n.replace('/','').replace('(','_').replace(')','_')+'.kicad_pcb'))
 for margin in [.01,.003,0]:
  t=copy.deepcopy(old);remove_ids(t,{item_id(c)for c in copper(t)if net(c)==n});r=InputRouter(t);r.margin=margin
  # Rebuild with the chosen obstacle margin before searching.
  for nn in list(r.geometry):r.refresh(nn)
  ps=[p for p in pad_data(t)if p['net']==n];assert len(ps)==2,(n,ps);a,b=ps
  if layer==0:ok=r.link(n,a['center'],[0],b['center'],[0],False)
  else:
   # Existing top-side packages stay in place; the two standard vias sit off their masks.
   pa=next(p for p in ps if p['ref']=='J1');pb=next(p for p in ps if p['ref'].startswith('RN'))
   qa=viaescape(r,n,pa['center'],(pa['center'][0],23.2),.65);qb=viaescape(r,n,pb['center'],(pb['center'][0],20.4),.6)
   ok=qa is not None and qb is not None and r.link(n,qa,[layer],qb,[layer],False)
  print('PAIR ROUTE',n,LAYERS[layer],margin,ok,flush=True)
  if not ok:continue
  save(t);d=check('pair-layers');errors=[v for v in d['violations']if v['severity']=='error']
  if not errors:return t,True
 save(old);return old,False

def main():
 t=load();save(t,BUILD/'before-pair-layer-corrections.kicad_pcb');out=[]
 for n,z in [('/E5P',0),('Net-(RN1D-R4.1)',0),('Net-(RN2B-R2.1)',0),('/E3P',2)]:
  t,ok=try_net(t,n,z);out.append(dict(net=n,layer=LAYERS[z],success=ok))
 save(t);(BUILD/'pair-layer-corrections.json').write_text(json.dumps(out,indent=2)+'\n');check('pairs-corrected')
if __name__=='__main__':main()
