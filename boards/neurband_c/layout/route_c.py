"""Reuse the proven REV B exact-pad/grid engine, preserving L2 as GND.
Critical RF and local analog links are constrained before global signals.
"""
from ipc_c import *
import sys, importlib.util, math, collections
import numpy as np
from shapely.geometry import box, Point, LineString, Polygon
from shapely import unary_union
# Archived source and compiled engine are deliberately read-only reuse.
sys.modules['ipc_rev_b']=sys.modules['ipc_c']
archive=PCB.parents[2]/'archive/neurband_main_revB/layout/route_rev_b.py'
spec=importlib.util.spec_from_file_location('rev_b_grid',archive);core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
core.W=1149;core.H=1081;core.WH=core.W*core.H
core.TRACK=.1;core.VIA=.45;core.DRILL=.3;core.CLEAR=.1;core.SAFETY=.026
index=core.index;position=core.position;STEP=core.STEP;LAYERS=core.LAYERS
BUILD=PCB.parent/'layout/build'
class Router(core.Router):
 def __init__(self,existing=False):
  super().__init__()
  outer=box(1,1,27.7,26).buffer(1,quad_segs=16)
  self.edge[:]=~self.raster(outer.buffer(-(.3+core.TRACK/2+core.SAFETY)))
  self.vedge[:]=~self.raster(outer.buffer(-(.3+core.VIA/2+core.SAFETY)))
  # TI Fig.3 radiator exclusion; connection tabs remain on its ground side.
  antenna=box(0,11.65,5.65,27)
  self.ant=self.raster(antenna.buffer(core.TRACK/2+core.SAFETY));self.edge[:,self.ant]=True
  self.vedge[self.raster(antenna.buffer(core.VIA/2+core.SAFETY))]=True
  self.supports=[Point(x,y).buffer(1.5,quad_segs=32)for x,y in [(1.6,1.6),(26.4,1.6),(1.6,25.4),(26.6,22.6)]]
  for g in self.supports:
   self.edge[2,self.raster(g.buffer(core.TRACK/2+core.SAFETY))]=True
   self.vedge[self.raster(g.buffer(core.VIA/2+core.SAFETY))]=True
  self.lookup={p['id']['value']:p for p in self.pads}
  if existing:
   for c in self.ipc.get(['KOT_PCB_TRACE','KOT_PCB_VIA']):
    n=c.get('net',{}).get('name','');d={'net':n,'id':c['id']}
    if c['@type'].endswith('.Via'):
     a=coord(c['position']);diam=int(c['pad_stack']['copper_layers'][0]['size']['x_nm'])*1e-6;g=Point(*a).buffer(diam/2,quad_segs=16)
     for z in range(3):self.geometry[n][z].append(g)
     self.vias.append((*a,n));d.update(center=a,layers=[0,1,2])
    else:
     a,b=coord(c['start']),coord(c['end']);z=LAYERS.index(c['layer'])if c['layer']in LAYERS else None
     if z is None:raise RuntimeError('Signal copper on reserved GND layer')
     width=int(c['width']['value_nm'])*1e-6;self.geometry[n][z].append(LineString([a,b]).buffer(width/2,quad_segs=12));d.update(center=a,ends=[a,b],layers=[z])
    self.lookup[c['id']['value']]=d
   for n in self.geometry:self.refresh(n)
  self.paste=self.raster(unary_union([p['poly']for p in self.pads if p['ref'] not in ['AE1'] and not p['ref'].startswith('TP')]).buffer(.3/2+.04))
  self.critical={'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)','Net-(U1-XC1)','Net-(U1-XC2)','/DEC1','/DEC3','/DEC4'}
  match=Polygon([(2,4.8),(5.7,4.8),(5.7,5.3),(6.35,5.3),(6.35,6.85),(2,6.85)])
  self.match=self.raster(match.buffer(core.TRACK/2+core.SAFETY))
  self.matchvia=self.raster(match.buffer(core.VIA/2+core.SAFETY))
 def available(self,n):
  m=self.masks.get(n,np.zeros_like(self.total));v=self.vmasks.get(n,np.zeros_like(self.vtotal))
  b=np.ascontiguousarray(((self.total-m)>0)|self.edge,dtype=np.uint8)
  v=np.ascontiguousarray(((self.vtotal-v)==0)&~self.vedge,dtype=np.uint8);v[self.paste]=0
  if n.startswith('/SPI_')or n.startswith('/ADC_'):b[:,int(16.6/STEP):,int(10.5/STEP):]=1
  b[1:,self.match]=1
  if n not in self.critical and n!='GND':b[0,self.match]=1
  v[self.matchvia]=0
  for x,y,net in self.vias:
   if net==n:v[round(y/STEP),round(x/STEP)]=1
  return b,v
 def wire(self,n,points,z=0,width=.127):
  for a,b in zip(points,points[1:]):
   if math.dist(a,b)<1e-7:continue
   self.items.append(core.item_track(a,b,z,n,width));self.geometry[n][z].append(LineString([a,b]).buffer(width/2,quad_segs=12))
  self.refresh(n)
 def pad(self,ref,num):return next(p for p in self.pads if p['ref']==ref and p['num']==str(num))
 def ground(self):
  # C21 must return through VSS31; its direct-to-plane via is forbidden.
  ps=self.nets['GND'];skip=self.pad('C21',2);self.nets['GND']=[p for p in ps if p is not skip]
  super().ground();self.nets['GND']=ps
 def save(self,incremental=False):
  i=self.ipc;i.begin()
  if not incremental:i.delete([x['id']['value']for x in i.get(['KOT_PCB_TRACE','KOT_PCB_VIA'])])
  for k in range(0,len(self.items),200):i.create(self.items[k:k+200])
  i.end('REV C: controlled local fanout and three-signal-layer routing');i.save()
  (BUILD/'route-failures.json').write_text(json.dumps(self.failed,indent=2));print('Saved',len(self.items),'items;',len(self.vias),'vias; failed',self.failed,flush=True)

def critical(r):
 # Shunt ground only reaches plane after traversing the VSS31 pad.
 r.wire('GND',[(4.7,6.38),(5.0,6.38),(5.55,5.9),(6.05,5.9),(6.65,5.9)])
 r.add_via(6.65,5.9,'GND');r.refresh('GND')
 r.wire('Net-(U1-ANT)',[(6.05,5.5),(5.1,5.5),(4.7,5.42),(4.2,5.5),(3.71,5.5)])
 # Nominal 50ohm covered microstrip, per rf_geometry.md.
 r.wire('Net-(C22-Pad1)',[(2.69,5.5),(1.58,6.61),(1.58,6.9),(1.58,7.79)],width=.16)
 r.wire('Net-(AE1-A)',[(1.58,8.81),(1.58,9.7),(1.58,11.35),(6.9,11.35),(6.9,14.7),(5.9,14.7)],width=.16)
 # Clock and internal regulators have no layer changes.
 for n in ['/DEC1','/DEC3','/DEC4','Net-(U1-XC2)','Net-(U1-XC1)']:
  ps=sorted(r.nets[n],key=lambda p:0 if p['ref']=='U1'else 1 if p['ref']=='Y1'else 2);a=ps[0];tree=[(index(*a['center'],0),a['center'])]
  for b in ps[1:]:
   path=r.search(n,[index(*b['center'],0)],[q for q,_ in tree],via=False)
   if path is None:raise RuntimeError(('Critical top-only route blocked',n,b['ref']))
   end=next(c for q,c in tree if q==path[-1]);r.commit_path(n,path,b['center'],end)
   tree.extend((q,position(q)[:2])for q in path[::max(1,len(path)//20)])

def reserve(r):
 # Connector escapes inside the plastic body, never in its solder lands.
 for p in [p for p in r.pads if p['ref']=='J1' and str(p['num']or'').isdigit()]:
  x,y=p['center'];n=p['net'];end=(x,23.0+.7*(int(p['num'])%2))
  path=r.search(n,[index(x,y,0)],[index(*end,0)],via=False)
  if path is None:raise RuntimeError(('J1 escape',p['num']))
  r.commit_path(n,path,(x,y),end);r.add_via(*end,n);r.refresh(n)
  p['center']=end;p['layers']=[0,1,2]
 # Preserve bypass/reference links as local top-layer connections.
 for n in [n for n in r.nets if any(k in n for k in ['VCAP','VREFP','RLDINV','RLDOUT','RLDREF'])]:
  r.route_net(n);r.critical.add(n)
 # Local quiet bypass returns directly to AVDD59 before its inward via.
 r.wire('+3V3A',[r.pad('C9',1)['center'],r.pad('U2',59)['center']])
 # Monotonic outward field for SPI and any newly assigned right-side I2C.
 for num,y in [(5,5.7),(6,4.9),(8,4.1),(9,3.3),(10,2.5)]:
  p=r.pad('U1',num);n=p['net']
  if n.startswith('unconnected-'):continue
  a=p['center'];end=(15.4 if num==5 else 15.2,y);r.wire(n,[a,(12.6,a[1]),end])
  r.add_via(*end,n);r.refresh(n);p['center']=end;p['layers']=[0,1,2]
 p=r.pad('U1',4);a=p['center'];n=p['net'];end=(12.675,6.725)
 r.wire(n,[a,end]);r.add_via(*end,n);r.refresh(n);p['center']=end;p['layers']=[0,1,2]
 # Low-rate IMU interrupt exits above the matching island.
 p=r.pad('U1',29)
 if not p['net'].startswith('unconnected-'):
  n=p['net'];a=p['center'];end=(4.8,4.3)
  r.wire(n,[a,(5.5,5.1),(4.8,4.4),end]);r.add_via(*end,n);r.refresh(n)
  p['center']=end;p['layers']=[0,1,2]
 # Single outward via row fans 0.4mm GPIO pitch to 0.8mm via pitch.
 # Vertical starts clear the full pad length before the monotonic spread.
 for num,x in [(14,12.0),(15,11.2),(16,10.4),(17,9.6),(18,8.8),(19,8.0),(20,7.2),(24,6.4)]:
  p=r.pad('U1',num);a=p['center'];n=p['net'];end=(x,.65)
  r.wire(n,[a,(a[0],2.1),end]);r.add_via(*end,n);r.refresh(n)
  p['center']=end;p['layers']=[0,1,2]
 # IMU signal escapes use the empty LGA interior; INT leaves to the left.
 for num,end in [(13,(24.95,21.5)),(14,(24.15,21.5)),(4,(22.2,22.35)),(12,(25.0,20.1)),(5,(24.0,23.25))]:
  p=r.pad('U5',num);a=p['center'];n=p['net']
  points=[a,(a[0],21.15),end]if num in [13,14]else[a,end]
  r.wire(n,points);r.add_via(*end,n);r.refresh(n);p['center']=end;p['layers']=[0,1,2]
 r.wire('+3V3',[(25.6625,22.35),(26.8,22.35),(27.35,22.08)])
 # TQFP vias alternate two inward rows under the body, clearing all lead toes.
 for p in sorted([p for p in r.pads if p['ref']=='U2' and p['net'] not in r.critical and not p['net'].startswith('unconnected-')],key=lambda p:int(p['num'])):
  a=p['center'];x,y=a;n=p['net'];dx,dy=x-20.2,y-10.1
  dx,dy=((1 if dx>0 else -1),0)if abs(dx)>abs(dy)else(0,(1 if dy>0 else -1))
  ends=[(x-dx*d,y-dy*d)for d in ([1.0,1.7,2.4,3.1]if int(p['num'])%2 else[1.7,1.0,2.4,3.1])]
  path=None
  for end in ends:
   _,v=r.available(n)
   if not v[round(end[1]/STEP),round(end[0]/STEP)]:continue
   path=r.search(n,[index(*a,0)],[index(*end,0)],via=False)
   if path is not None:break
  if path is None and n=='GND':continue
  if path is None:raise RuntimeError(('TQFP escape blocked',p['num'],n))
  r.commit_path(n,path,a,end);r.add_via(*end,n);r.refresh(n);p['center']=end;p['layers']=[0,1,2]
 original=r.pads
 r.pads=[p for p in original if len(p['layers'])==1 and p['net'] not in r.critical and not(p['ref']=='U2' and p['net']=='GND')and not (p['ref']=='U1'and p['num']in ['31','49'])]
 core.reserve_fine_pad_escapes(r)
 r.pads=original
 # Supply and high-impedance passive endpoints get layer access before buses
 # can isolate a two-pad island. Keep every drill outside paste.
 local={'GND':False,'+3V3':True,'+3V3A':True,'VBAT':True,'VCHG':True,'/BIAS_E':True,'/VBAT_SENSE':True,'/I2C_SDA':True,'/I2C_SCL':True}
 for p in [p for p in r.pads if len(p['layers'])==1 and local.get(p['net'],False)and(p['ref'][0]in 'CR'or p['ref']in ['J2','J3'])]:
  a=p['center'];n=p['net'];_,v=r.available(n);px,py=round(a[0]/STEP),round(a[1]/STEP);rad=70
  x0=max(0,px-rad);x1=min(core.W,px+rad);y0=max(0,py-rad);y1=min(core.H,py+rad)
  yy,xx=np.nonzero(v[y0:y1,x0:x1]);xx+=x0;yy+=y0
  if not len(xx):continue
  ix=np.argsort((xx-px)**2+(yy-py)**2)[:150]
  goals=[index(xx[k]*STEP,yy[k]*STEP,z)for k in ix for z in p['layers']]
  path=r.search(n,[index(*a,z)for z in p['layers']],goals,via=False)
  if path is None:print('PASSIVE EXIT UNRESOLVED',p['ref'],p['num'],n,flush=True);continue
  r.commit_path(n,path,a);x,y,_=position(path[-1]);r.add_via(x,y,n);r.refresh(n)
  p['center']=(x,y);p['layers']=[0,1,2]
 print('Ground returns before global routes',flush=True);r.ground()

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--close');args=ap.parse_args()
 r=Router(existing=bool(args.close))
 if args.close:
  d=json.loads((BUILD/(args.close+'.json')).read_text())
  for row in d['unconnected_items']:
   if any(q['uuid']not in r.lookup for q in row['items']):continue
   a,b=[r.lookup[q['uuid']]for q in row['items']];n=a['net'];assert n==b['net']
   starts=[index(*p,z)for p in a.get('ends',[a['center']])for z in a['layers']]
   goals=[index(*p,z)for p in b.get('ends',[b['center']])for z in b['layers']]
   path=r.search(n,starts,goals,via=False)or r.search(n,starts,goals)
   if path is None:r.failed.append(n);print('FAILED',n,flush=True);continue
   start=min(a.get('ends',[a['center']]),key=lambda p:math.dist(p,position(path[0])[:2]));end=min(b.get('ends',[b['center']]),key=lambda p:math.dist(p,position(path[-1])[:2]))
   r.commit_path(n,path,start,end);print('Closed',n,len(path),flush=True)
  r.save(incremental=True);return
 critical(r);print('Critical routes',len(r.items),flush=True);reserve(r)
 # Analog post-resistor pairs precede the connector crossovers.
 nets=[n for n,ps in r.nets.items()if len(ps)>1 and n!='GND'and not n.startswith('unconnected-') and n not in r.critical]
 def rank(n):
  return (0 if n.startswith('Net-(RN')else 1 if n in ['/BIAS_E','/VBAT_SENSE']else 2 if n.startswith('/E')else 4 if n in ['+3V3','+3V3A','VBAT','VCHG']else 3,n)
 for n in sorted(nets,key=rank):print('Routing',n,flush=True);r.route_net(n)
 r.save()
if __name__=='__main__':main()
