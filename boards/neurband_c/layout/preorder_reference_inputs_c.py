"""Route inner-layer input sections only where bottom ground can remain underneath."""
from preorder_pair_layers_c import *
class ReferenceRouter(InputRouter):
 def available(self,n):
  b,v=super().available(n);b[2]=1
  other=[g for nn,gs in self.geometry.items()if nn not in [n,'GND','']for g in gs[2]]
  forbidden=self.raster(unary_union(other).buffer(.155))
  boundary=box(1,1,27.7,26).buffer(1,quad_segs=32).buffer(-.56)
  forbidden|=~self.raster(boundary);forbidden|=self.raster(unary_union(self.supports).buffer(.06));b[1,forbidden]=1
  active=lambda nn:nn.startswith(('/I2C_','/SPI_','/IMU_INT','/ADC_','/LED'))or nn=='Net-(D1-A)'
  ag=[g for nn,gs in self.geometry.items()if active(nn)for g in gs[0]]
  guard=self.raster(unary_union(ag).buffer(.9));b[0,guard]=1;v[guard]=0
  v[self.raster(unary_union([p['poly']for p in self.pads]).buffer(.3501))]=0
  if self.vias:v[self.raster(unary_union([Point(x,y).buffer(.5501)for x,y,nn in self.vias]))]=0
  for x,y,nn in self.vias:
   if nn==n:v[round(y/.025),round(x/.025)]=1
  return b,v

def route_groups(t,r,n):
 ids,groups=connected(t,n)
 for _ in range(8):
  if len(groups)<=1:return True
  vv=[c for c in kids(t,'via')if net(c)==n];mask,_=r.available(n)
  def nodes(k):
   out=[]
   for c in vv:
    if ids[item_id(c)]==k:
     q=tuple(map(float,get(c,'at')[1:3]));i=r.idx(q,1)
     if not mask[1,round(q[1]/.025),round(q[0]/.025)]:out.append(i)
   if not out:
    for _,g,zs,ps in groups[k]:
     for q in ps:
      for z in zs:
       if z!=2 and not mask[z,round(q[1]/.025),round(q[0]/.025)]:out.append(r.idx(q,z))
   return list(set(out))
  keys=list(groups);starts=nodes(keys[0]);goals=[j for k in keys[1:]for j in nodes(k)];path=r.search(n,starts,goals,True)if starts and goals else None
  if not path:
   print('REFERENCE BLOCK',n,'groups',len(groups),'nodes',len(starts),len(goals),flush=True);return False
  p,q=r.coord(path[0]),r.coord(path[-1]);search=r.search;r.search=lambda *args,**kw:path;r.link(n,p[:2],[p[2]],q[:2],[q[2]]);r.search=search;ids,groups=connected(t,n)
 return False

def main():
 t=load();save(t,BUILD/'before-reference-inputs.kicad_pcb');rows=[]
 pairs=[['/E1P','/E1N'],['/E3P','/E3N'],['/E4P','/E4N'],['/E7P','/E7N'],['Net-(RN1A-R1.1)','Net-(RN1B-R2.1)'],['Net-(RN3C-R3.1)','Net-(RN3D-R4.1)'],['Net-(RN4A-R1.1)','Net-(RN4B-R2.1)']]
 for ns in pairs:
  old=copy.deepcopy(t);good=False
  for order in [ns,ns[::-1]]:
   tt=copy.deepcopy(old);remove_ids(tt,{item_id(c)for c in kids(tt,'segment')if net(c)in ns and uq(get(c,'layer')[1])=='In2.Cu'});r=ReferenceRouter(tt);r.margin=.001
   for n in list(r.geometry):r.refresh(n)
   ok=True
   for n in order:
    ok=route_groups(tt,r,n);print('REFERENCE ROUTE',n,ok,flush=True)
    if not ok:break
   if not ok:continue
   save(tt);d=check('input-reference')
   if not d['unconnected_items']and not any(v['severity']=='error'for v in d['violations']):t=load();good=True;break
  if not good:t=old;save(t)
  rows.append(dict(nets=ns,success=good));print('REFERENCE RESULT',ns,good,flush=True)
 save(t);(BUILD/'reference-input-results.json').write_text(json.dumps(rows,indent=2)+'\n');check('inputs-referenced')
if __name__=='__main__':main()
