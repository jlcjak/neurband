"""Anchor the crowded AFE bypass/reference region with a standard drill."""
from preorder_pair_layers_c import *
import connect_components_c as cc
class AnchorRouter(InputRouter):
 def available(self,n):
  b,v=super().available(n)
  if n=='/RLDREF':b[1:]=1;v[:]=0
  if n=='VCHG':
   ins=[shape(c)[0]for c in kids(self.t,'segment')if (net(c).startswith('/E')or net(c).startswith('Net-(RN'))and uq(get(c,'layer')[1])=='In2.Cu']
   b[2,self.raster(unary_union(ins).buffer(.16))]=1
  v[self.raster(unary_union([p['poly']for p in self.pads if 'Cu'in str(get(p['node'],'layers'))]).buffer(.3501))]=0
  if self.vias:v[self.raster(unary_union([Point(x,y).buffer(.5501)for x,y,nn in self.vias]))]=0
  for x,y,nn in self.vias:
   if nn==n:v[round(y/.025),round(x/.025)]=1
  return b,v

def main():
 old=load();save(old,BUILD/'before-afe-anchor.kicad_pcb');q=(11.6,11.35);t=copy.deepcopy(old);remove_ids(t,{item_id(c)for c in kids(t,'via')if net(c)=='GND'and math.dist(tuple(map(float,get(c,'at')[1:3])),(11.6,11.35))<.001});kill=[c for c in copper(t)if net(c)!='GND'and shape(c)[0].distance(Point(q))<.351];assert all(c[0]=='segment'and net(c)in ['VCHG','/RLDREF']for c in kill);remove_ids(t,{item_id(c)for c in kill});t.append(via(*q));save(t);d=check('afe-anchor-open');cc.ReleaseRouter=AnchorRouter
 try:
  cc.close_components(t,d);d=check('afe-anchor-closed');ok=not d['unconnected_items']and not any(v['severity']=='error'for v in d['violations'])
 except Exception as e:print('ANCHOR ROUTE',e,flush=True);ok=False
 if not ok:save(old);check('afe-anchor-retained')
 print('AFE ANCHOR',ok,'REWORK',collections.Counter(net(c)for c in kill),flush=True)
if __name__=='__main__':main()
