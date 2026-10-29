"""Move off-pad vias where ordinary drills fit; preserve RF and frozen interfaces."""
from preorder_pair_layers_c import *
def main():
 t=load();save(t,BUILD/'before-pad-clearance.kicad_pcb');report=json.loads((BUILD/'release-audit.json').read_text());rows=report['via_hole_to_pasted_pad_under_0p2_mm'];sites={}
 for row in rows:sites.setdefault((*row['via'],row['via_net']),[]).append(row)
 result=[]
 for (x,y,n),pads in sites.items():
  if any(p['pad'].split('.')[0]in ['C21','C22','C23','Y1']for p in pads):result.append(dict(old=[x,y],net=n,status='RF/crystal return retained'));continue
  old=load();vv=next((c for c in kids(old,'via')if net(c)==n and math.dist(tuple(map(float,get(c,'at')[1:3])),(x,y))<.001),None)
  if vv is None:continue
  # A redundant ground barrel can be removed without lengthening the return.
  near=any(net(c)=='GND'and item_id(c)!=item_id(vv)and math.dist(tuple(map(float,get(c,'at')[1:3])),(x,y))<.9 for c in kids(old,'via'))if n=='GND'else False
  if near:
   t=copy.deepcopy(old);remove_ids(t,{item_id(vv)});save(t);d=check('pad-clearance')
   if not d['unconnected_items']and not any(v['severity']=='error'for v in d['violations']):result.append(dict(old=[x,y],net=n,status='redundant ground via removed'));print('PAD VIA REMOVED',n,x,y,flush=True);continue
   save(old)
  t=copy.deepcopy(old);remove_ids(t,{item_id(vv)});r=InputRouter(t,width=.1);r.margin=.001
  for nn in list(r.geometry):r.refresh(nn)
  _,v=r.available(n);v[r.raster(unary_union([p['poly']for p in r.pads]).buffer(.3501))]=0
  if r.vias:v[r.raster(unary_union([Point(a,b).buffer(.5501)for a,b,_ in r.vias]))]=0
  ys,xs=np.where(v);cands=[(a*.025,b*.025)for b,a in zip(ys,xs)if math.dist((a*.025,b*.025),(x,y))<1.2];cands.sort(key=lambda q:math.dist(q,(x,y)))
  zs=set()
  for c in kids(t,'segment'):
   if net(c)==n and shape(c)[0].distance(Point(x,y))<.22501:zs.update(shape(c)[1])
  if n=='GND':zs.add(0)
  good=False
  for q in cands[:6]:
   tt=copy.deepcopy(t);rr=InputRouter(tt,width=.1);rr.margin=.001
   for nn in list(rr.geometry):rr.refresh(nn)
   ok=all(rr.link(n,(x,y),[z],q,[z],False)for z in zs)
   if not ok:continue
   tt.append(via(*q,n));save(tt);d=check('pad-clearance')
   if not d['unconnected_items']and not any(v['severity']=='error'for v in d['violations']):result.append(dict(old=[x,y],new=list(q),net=n,status='moved off mask'));good=True;print('PAD VIA MOVED',n,[x,y],q,flush=True);break
  if not good:save(old);result.append(dict(old=[x,y],net=n,status='no nearby legal route found'));print('PAD VIA RETAINED',n,x,y,flush=True)
 (BUILD/'pad-clearance-results.json').write_text(json.dumps(result,indent=2)+'\n');check('pads-corrected')
if __name__=='__main__':main()
