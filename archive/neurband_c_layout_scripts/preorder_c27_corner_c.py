"""Put the LDO output bypass in J1's physically empty upper-left corner.

J1's drawing/body envelope starts at y=21.88. Its contact row begins at
x=9.10. The refined courtyard preserves those features with at least
0.25 mm allowance; the local copies retain identical pads and models.
"""
from preorder_pair_layers_c import *
from preorder_power_guard_c import PowerRouter
class CornerRouter(InputRouter):
 def available(self,n):
  b,v=super().available(n);v[self.raster(unary_union([p['poly']for p in self.pads]).buffer(.3501))]=0
  if self.vias:v[self.raster(unary_union([Point(x,y).buffer(.5501)for x,y,_ in self.vias]))]=0
  return b,v
class StarRouter(PowerRouter):
 def available(self,n):
  b,v=super().available(n)
  if n=='+3V3':
   corridor=self.raster(box(8.75,19.4,11.6,21.0));b[0,corridor]=1;v[corridor]=0
  return b,v

def notch(f):
 f[:]=[c for c in f if not(isinstance(c,list)and c[0].startswith('fp_')and get(c,'layer')and uq(get(c,'layer')[1])=='F.CrtYd')]
 pts=[(8.85,20.6925),(21.7,20.6925),(21.7,27.2925),(6.3,27.2925),(6.3,21.63),(8.85,21.63),(8.85,20.6925)]
 for a,b in zip(pts,pts[1:]):f.append(['fp_line',['start',num(a[0]-14),num(a[1]-23.1925)],['end',num(b[0]-14),num(b[1]-23.1925)],['stroke',['width','.05'],['type','solid']],['layer','"F.CrtYd"'],ident()])
def main():
 t=load();save(t,BUILD/'before-c27-corner.kicad_pcb');by={ref(f):f for f in kids(t,'footprint')}
 # The routing helper produced two overlapping same-net barrels. Keep one.
 a=(14.325,16.1);b=(14.525,15.9);n='Net-(RN4A-R1.1)';bad=[c for c in kids(t,'via')if net(c)==n and math.dist(tuple(map(float,get(c,'at')[1:3])),a)<.001]
 if bad:
  remove_ids(t,{item_id(c)for c in bad});wire(t,n,[a,b],'F.Cu',.1);wire(t,n,[a,b],'In2.Cu',.1)
 save(t);check('reference-barrel-merged');t=load();save(t,BUILD/'before-c27-placement.kicad_pcb');by={ref(f):f for f in kids(t,'footprint')};notch(by['J1']);move(by['C27'],7.75,21.12,0)
 remove_ids(t,{item_id(c)for c in copper(t)if(c[0]=='via'and net(c)=='GND'and math.dist(tuple(map(float,get(c,'at')[1:3])),(7.6,21.3))<.001)or(c[0]=='segment'and net(c)=='+3V3'and uq(get(c,'layer')[1])=='F.Cu'and shape(c)[0].intersects(box(7.0,19.5,11.6,20.6)))})
 t[:]=[c for c in t if not(isinstance(c,list)and c[0]=='gr_text'and uq(c[1])=='1'and get(c,'at')[1:3]==['8.3','21.4'])]
 ps=pad_data(t);p=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center'];r=CornerRouter(t,width=.25);r.margin=.001
 for nn in list(r.geometry):r.refresh(nn)
 print('C27 OUTPUT',r.link('+3V3',p('U3',2),[0],p('C27',1),[0],False),flush=True)
 for n,nn,target in [('+3V3',1,(8.7,20.45)),('GND',2,(8.5,21.95))]:print('C27 VIA',n,viaescape(r,n,p('C27',nn),target,.85),flush=True)
 save(t);d=check('c27-corner')
 import connect_components_c as cc
 cc.ReleaseRouter=StarRouter;cc.close_components(t,d);d=check('c27-star-closed')
 if d['unconnected_items']or any(v['severity']=='error'for v in d['violations']):
  print('C27 RESTORE',flush=True);save(load(BUILD/'before-c27-placement.kicad_pcb'));check('c27-retained');return
 lib=Path('boards/neurband_c/layout/neurband.pretty/XUNPU_FPC-05F-20PH20_Centroid.kicad_mod');f=parse(lib.read_text());notch(f);lib.write_text(dump(f)+'\n');print('C27 ACCEPT',flush=True)
if __name__=='__main__':main()
