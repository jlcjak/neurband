"""Lift quiet bottom crossings off the reference below inner-layer electrodes."""
from preorder_reference_inputs_c import *
import connect_components_c as cc
from shapely.ops import linemerge
class CrossingRouter(InputRouter):
 def available(self,n):
  b,v=super().available(n);b[1]=1
  ins=[shape(c)[0]for c in kids(self.t,'segment')if (net(c).startswith('/E')or net(c).startswith('Net-(RN'))and uq(get(c,'layer')[1])=='In2.Cu'and net(c)!=n]
  forbidden=self.raster(unary_union(ins).buffer(.16));b[2,forbidden]=1
  # Ordinary drills clear all pasted lands and all existing barrels.
  pads=[p['poly']for p in self.pads if p['node'][2]=='smd'and 'Cu'in str(get(p['node'],'layers'))]
  v[self.raster(unary_union(pads).buffer(.3501))]=0
  if self.vias:v[self.raster(unary_union([Point(x,y).buffer(.5501)for x,y,nn in self.vias]))]=0
  for x,y,nn in self.vias:
   if nn==n:v[round(y/.025),round(x/.025)]=1
  return b,v

def main():
 t=load();save(t,BUILD/'before-reference-crossings.kicad_pcb');results=[]
 jobs=[('VBAT',box(13.7,10.7,17,14.5)),('/SWDCLK',box(17,9.0,22.1,18.0)),('/BIAS_E',box(16.7,20.0,18.2,21.9)),('/E8P',box(15.1,20.0,17.0,21.0)),('/E2N',box(10.7,18.8,12.1,21.5)),('/E2P',box(10.7,18.8,12.1,21.5))]
 for n,region in jobs:
  old=load();t=copy.deepcopy(old);removed=[c for c in kids(t,'segment')if net(c)==n and uq(get(c,'layer')[1])=='B.Cu'and shape(c)[0].intersects(region)];remove_ids(t,{item_id(c)for c in removed})
  if not removed:continue
  router=CrossingRouter(t);router.margin=.001
  for nn in list(router.geometry):router.refresh(nn)
  ids,groups=connected(t,n);ok=True
  for _ in range(8):
   if len(groups)<=1:break
   keys=list(groups);mask,_=router.available(n)
   def nodes(k):
    out=[]
    for _,g,zs,ps in groups[k]:
     for q in ps:
      for z in zs:
       if z!=1 and not mask[z,round(q[1]/.025),round(q[0]/.025)]:out.append(router.idx(q,z))
    return list(set(out))
   starts=nodes(keys[0]);goals=[i for k in keys[1:]for i in nodes(k)];path=router.search(n,starts,goals,True)if starts and goals else None
   if not path:ok=False;break
   p,q=router.coord(path[0]),router.coord(path[-1]);fn=router.search;router.search=lambda *args,**kw:path;router.link(n,p[:2],[p[2]],q[:2],[q[2]]);router.search=fn;ids,groups=connected(t,n)
  if len(groups)>1:ok=False
  before_ids={item_id(c)for c in copper(old)};new=[c for c in copper(t)if item_id(c)not in before_ids];newlength=sum(LineString([tuple(map(float,get(c,k)[1:3]))for k in ['start','end']]).length for c in new if c[0]=='segment')
  if newlength>25:ok=False
  if ok:
   save(t);d=check('reference-crossing');ok=not d['unconnected_items']and not any(v['severity']=='error'for v in d['violations'])
  if not ok:save(old)
  results.append(dict(net=n,success=ok,removed_segments=len(removed),new_length_mm=newlength));print('CROSSING',results[-1],flush=True)
 (BUILD/'reference-crossing-results.json').write_text(json.dumps(results,indent=2)+'\n');check('reference-crossings-final')
if __name__=='__main__':main()
