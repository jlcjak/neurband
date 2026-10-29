"""Route VBAT through the south/left corridor with short local charger/LDO branches."""
from preorder_pair_layers_c import *
class BatteryRouter(InputRouter):
 def available(self,n):
  b,v=super().available(n)
  v[self.raster(unary_union([p['poly']for p in self.pads]).buffer(.3501))]=0
  if self.vias:v[self.raster(unary_union([Point(x,y).buffer(.5501)for x,y,_ in self.vias]))]=0
  return b,v
class QuietBatteryRouter(BatteryRouter):
 def __init__(self,t,width=.1):
  super().__init__(t,width);inner=[];bottom=[]
  for c in kids(t,'segment'):
   if net(c).startswith('/E')or net(c).startswith('Net-(RN'):
    if uq(get(c,'layer')[1])=='In2.Cu':inner.append(shape(c)[0])
    if uq(get(c,'layer')[1])=='B.Cu':bottom.append(shape(c)[0])
  self.blockB=self.raster(unary_union(inner).buffer(1.0));self.blockI=self.raster(unary_union(bottom+inner).buffer(.65))
 def available(self,n):
  b,v=super().available(n)
  if n=='VBAT':
   own=self.raster(unary_union([p['poly']for p in self.pads if p['net']==n]).buffer(1.0));bb=self.blockB&~own;bi=self.blockI&~own;b[2,bb]=1;b[1,bi]=1;v[bb|bi]=0
  return b,v

def main():
 old=load();save(old,BUILD/'before-battery-trunk.kicad_pcb')
 for width in [.25,.127]:
  t=copy.deepcopy(old);remove_ids(t,{item_id(c)for c in copper(t)if net(c)=='VBAT'});ps=pad_data(t);p=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center'];r=QuietBatteryRouter(t,width=width);r.margin=.003
  for n in list(r.geometry):r.refresh(n)
  steps=[(p('J2',1),[2],(22.1,26.3),[0],True),((22.1,26.3),[0],(8.3,26.3),[0],True),((8.3,26.3),[0],p('U3',3),[0],True)]
  good=True
  for a,az,b,bz,v in steps:
   ok=r.link('VBAT',a,az,b,bz,v);print('BATTERY TRUNK',width,a,b,ok,flush=True)
   if not ok:good=False;break
  if not good:continue
  r=QuietBatteryRouter(t,width=width);r.margin=.003
  for n in list(r.geometry):r.refresh(n)
  for a,b in [(p('U3',3),p('C26',1)),(p('U3',3),p('C25',1)),(p('C25',1),p('U4',3))]:
   ok=r.link('VBAT',a,[0],b,[0],True);print('BATTERY LOCAL',a,b,ok,flush=True)
   if not ok:good=False;break
  if not good:continue
  save(t);d=check('battery-trunk')
  import connect_components_c as cc
  cc.ReleaseRouter=QuietBatteryRouter;cc.close_components(t,d);d=check('battery-trunk-closed')
  if not d['unconnected_items']and not any(v['severity']=='error'for v in d['violations']):print('BATTERY ACCEPT',width,flush=True);return
 save(old);check('battery-retained')
if __name__=='__main__':main()
