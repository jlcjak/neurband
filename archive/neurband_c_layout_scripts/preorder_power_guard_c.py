"""Remove power broadside runs below inner-layer electrodes and reconnect with shielding."""
from connect_components_c import *
class PowerRouter(ReleaseRouter):
 def __init__(self,t,width=.1):
  super().__init__(t,width);inputs=[shape(c)[0]for c in copper(t)if c[0]=='segment'and (net(c).startswith('/E')or net(c).startswith('Net-(RN'))]
  inner=[shape(c)[0]for c in copper(t)if c[0]=='segment'and (net(c).startswith('/E')or net(c).startswith('Net-(RN'))and uq(get(c,'layer')[1])=='In2.Cu']
  self.powerbottom=self.raster(unary_union(inner).buffer(1.0));self.powerinner=self.raster(unary_union(inputs).buffer(.65))
 def available(self,n):
  b,v=super().available(n)
  if n in ['+3V3','VBAT','+3V3A']:
   b[2,self.powerbottom]=1;b[1,self.powerinner]=1;v[self.powerbottom|self.powerinner]=0
  return b,v

def main():
 t=load();save(t,BUILD/'before-power-guard.kicad_pcb');inner=unary_union([shape(c)[0]for c in copper(t)if c[0]=='segment'and(net(c).startswith('/E')or net(c).startswith('Net-(RN'))and uq(get(c,'layer')[1])=='In2.Cu']);kill=set()
 for c in kids(t,'segment'):
  if net(c)in ['+3V3','VBAT','+3V3A']and uq(get(c,'layer')[1])=='B.Cu'and shape(c)[0].distance(inner)<.85:kill.add(item_id(c))
 print('Removed bottom power near electrodes',len(kill),flush=True);remove_ids(t,kill);save(t);d=check('power-guard')
 # Reuse component routing with the more conservative power/reference partition.
 import connect_components_c as cc
 cc.ReleaseRouter=PowerRouter
 cc.close_components(t,d);save(t);d=check('power-guard-closed')
 # Resolve ordinary non-power gaps after dead-branch cleanup.
 cc.ReleaseRouter=ReleaseRouter
 cc.close_components(t,d);check('power-guard-final')
if __name__=='__main__':main()
