"""Clearance-aware compact-board routing. Native IPC supplies exact pad polygons.
In1.Cu stays a solid GND plane. Analog/reference links precede buses and power.
"""
from ipc_rev_b import *
import numpy as np, ctypes, math, collections, argparse
from shapely.geometry import Polygon, Point, LineString, box
from shapely import contains_xy, unary_union

STEP=.025; W=1281; H=1041; WH=W*H; LAYERS=['BL_F_Cu','BL_In2_Cu','BL_B_Cu']
TRACK=.1; CLEAR=.1; SAFETY=.019; VIA=.45; DRILL=.2
LIB=ctypes.CDLL(str(Path(__file__).parent/'build/grid_rev_b.so'))
LIB.route.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int]

def coord(v):return (int(v.get('x_nm',0))*1e-6,int(v.get('y_nm',0))*1e-6)
def polygon(p):return Polygon([coord(n['point']) for n in p['outline']['nodes'] if 'point'in n])
def index(x,y,z):return z*WH+round(y/STEP)*W+round(x/STEP)
def position(n):return ((n%W)*STEP,(n//W%H)*STEP,n//WH)
def item_track(a,b,z,net,width=TRACK):return {'@type':'type.googleapis.com/kiapi.board.types.Track','id':uid(),'start':xy(*a),'end':xy(*b),'width':{'value_nm':str(nm(width))},'layer':LAYERS[z],'net':{'name':net}}
def item_via(x,y,net):return {'@type':'type.googleapis.com/kiapi.board.types.Via','id':uid(),'position':xy(x,y),'type':'VT_THROUGH','net':{'name':net},'pad_stack':{'type':'PST_NORMAL','layers':['BL_F_Cu','BL_In1_Cu','BL_In2_Cu','BL_B_Cu'],'drill':{'start_layer':'BL_F_Cu','end_layer':'BL_B_Cu','diameter':xy(DRILL,DRILL),'shape':'DS_CIRCLE'},'copper_layers':[{'layer':'BL_F_Cu','shape':'PSS_CIRCLE','size':xy(VIA,VIA)}]}}

class Router:
 def __init__(self,protect=False):
    self.ipc=IPC();self.fs=self.ipc.get(['KOT_PCB_FOOTPRINT']);self.pads=[];self.nets=collections.defaultdict(list);self.geometry=collections.defaultdict(lambda:[[],[],[]]);self.vias=[];self.items=[];self.failed=[]
    raw=[p for f in self.fs for p in f['definition']['items'] if p['@type'].endswith('.Pad') and p['pad_stack'].get('layers') and any(l in LAYERS for l in p['pad_stack']['layers'])]
    shapes=self.ipc.call('kiapi.board.commands.GetPadShapeAsPolygon',{'board':self.ipc.doc,'pads':[p['id'] for p in raw],'layer':'BL_F_Cu'})['polygons']
    refs={p['id']['value']:f['reference_field']['text']['text']['text'] for f in self.fs for p in f['definition']['items'] if p['@type'].endswith('.Pad')}
    for p,pol in zip(raw,shapes):
      net=p.get('net',{}).get('name') or '__mechanical_'+p['id']['value'];g=polygon(pol);layers=[z for z,l in enumerate(LAYERS) if l in p['pad_stack']['layers']]
      d={'ref':refs[p['id']['value']],'num':p.get('number'),'net':net,'poly':g,'center':coord(p['position']),'layers':layers,'id':p['id']}
      self.pads.append(d);self.nets[net].append(d)
      for z in layers:self.geometry[net][z].append(g)
    # Reserve a short outward escape at every fine-pitch terminal, so an earlier
    # net cannot legally clear a pad while sealing off its only usable exit.
    centers={f['reference_field']['text']['text']['text']:coord(f['position'])for f in self.fs}
    for p in self.pads:
      if not protect:continue
      ref=p['ref']
      if ref not in ['U1','U2','U3'] and not ref.startswith('RN'):continue
      if p['net'].startswith('unconnected-') or len(self.nets[p['net']])<2:continue
      x,y=p['center'];cx,cy=centers[ref];dx,dy=x-cx,y-cy
      if ref.startswith('RN'):dx=0;dy=1 if y>cy else -1;length=.5
      elif abs(dx)>abs(dy):dx=1 if dx>0 else -1;dy=0;length=.95 if ref!='U1' else .65
      else:dy=1 if dy>0 else -1;dx=0;length=.95 if ref!='U1' else .65
      g=LineString([(x,y),(x+length*dx,y+length*dy)]).buffer(TRACK/2,quad_segs=8)
      for z in p['layers']:self.geometry[p['net']][z].append(g)
    self.total=np.zeros((3,H,W),np.int16);self.vtotal=np.zeros((H,W),np.int16);self.masks={};self.vmasks={}
    self.edge=np.ones((3,H,W),bool);self.vedge=np.ones((H,W),bool)
    # 1mm rounded corners, 0.3 copper clearance; RF antenna is entirely outside x=0.
    outer=box(1,1,31,25).buffer(1,quad_segs=16)
    self.edge[:]=~self.raster(outer.buffer(-(.3+TRACK/2+SAFETY)))
    self.vedge[:]=~self.raster(outer.buffer(-(.3+VIA/2+SAFETY)))
    for net in self.geometry:self.refresh(net)
 def raster(self,g):
    out=np.zeros((H,W),bool)
    if g.is_empty:return out
    a,b,c,d=g.bounds;x0=max(0,math.floor(a/STEP));x1=min(W,math.ceil(c/STEP)+1);y0=max(0,math.floor(b/STEP));y1=min(H,math.ceil(d/STEP)+1)
    if x1>x0 and y1>y0:out[y0:y1,x0:x1]=contains_xy(g,np.arange(x0,x1)[None,:]*STEP,np.arange(y0,y1)[:,None]*STEP)
    return out
 def refresh(self,net):
    if net in self.masks:self.total-=self.masks[net];self.vtotal-=self.vmasks[net]
    geometries=self.geometry[net];m=np.zeros((3,H,W),bool)
    for z in range(3):
      if geometries[z]:m[z]=self.raster(unary_union(geometries[z]).buffer(CLEAR+TRACK/2+SAFETY,quad_segs=8))
    allg=unary_union([g for gs in geometries for g in gs]);v=self.raster(allg.buffer(CLEAR+VIA/2+SAFETY,quad_segs=8))
    self.masks[net]=m;self.vmasks[net]=v;self.total+=m;self.vtotal+=v
 def available(self,net):
    m=self.masks.get(net,np.zeros_like(self.total));v=self.vmasks.get(net,np.zeros_like(self.vtotal))
    blocked=((self.total-m)>0)|self.edge;via=((self.vtotal-v)==0)&~self.vedge
    # No digital or power signal routing in the connector/input fanout corridor on In2.
    if net.startswith('/SPI_') or net.startswith('/ADC_'):blocked[1,:int(8/STEP),:]=True
    return np.ascontiguousarray(blocked,dtype=np.uint8),np.ascontiguousarray(via,dtype=np.uint8)
 def search(self,net,starts,goals,via=True):
    blocked,v=self.available(net)
    if not via:v[:]=0
    s=np.array(starts,np.int32);g=np.array(goals,np.int32);out=np.empty(30000,np.int32)
    n=LIB.route(blocked.ctypes.data,v.ctypes.data,W,H,3,s.ctypes.data,len(s),g.ctypes.data,len(g),out.ctypes.data,len(out),45,2000000)
    return list(map(int,out[:n])) if n>0 else None
 def commit_path(self,net,path,start=None,end=None):
    # Compress equal-direction grid steps, preserving exact pad-center links.
    segments=[];via_positions=[];a=path[0];lastdir=None
    for k in range(1,len(path)):
      p,q=position(path[k-1]),position(path[k]);dr=(round((q[0]-p[0])/STEP),round((q[1]-p[1])/STEP),q[2]-p[2])
      if dr[2]:
        if a!=path[k-1]:segments.append((position(a),p))
        via_positions.append((q[0],q[1]));a=path[k];lastdir=None
      elif lastdir is not None and dr!=lastdir:
        segments.append((position(a),p));a=path[k-1];lastdir=dr
      else:lastdir=dr
    if a!=path[-1]:segments.append((position(a),position(path[-1])))
    if start is not None:
      x,y,z=position(path[0]);
      if math.dist((x,y),start)>1e-7:segments.insert(0,((*start,z),(x,y,z)))
    if end is not None:
      x,y,z=position(path[-1]);
      if math.dist((x,y),end)>1e-7:segments.append(((x,y,z),(*end,z)))
    for a,b in segments:
      if math.dist(a[:2],b[:2])<1e-7:continue
      self.items.append(item_track(a[:2],b[:2],a[2],net));self.geometry[net][a[2]].append(LineString([a[:2],b[:2]]).buffer(TRACK/2,quad_segs=8))
    for x,y in set(via_positions):self.add_via(x,y,net)
    self.refresh(net)
 def add_via(self,x,y,net):
    if any(n==net and math.dist((x,y),(a,b))<.01 for a,b,n in self.vias):return
    self.vias.append((x,y,net));self.items.append(item_via(x,y,net))
    g=Point(x,y).buffer(VIA/2,quad_segs=12)
    for z in range(3):self.geometry[net][z].append(g)
 def route_net(self,net):
    ps=self.nets[net];root=ps[0];tree=[(index(*root['center'],z),root['center'])for z in root['layers']];remaining=ps[1:]
    while remaining:
      best=min(remaining,key=lambda p:min(math.dist(p['center'],c) for _,c in tree));remaining.remove(best)
      starts=[index(*best['center'],z)for z in best['layers']]
      near=sorted(tree,key=lambda t:math.dist(best['center'],t[1]))[:40]
      path=self.search(net,starts,[n for n,_ in near],via=False)
      if path is None:path=self.search(net,starts,[n for n,_ in near])
      if path is None:self.failed.append((net,best['ref'],best['num']));print('FAILED',self.failed[-1],flush=True);continue
      end=next(c for n,c in near if n==path[-1]);self.commit_path(net,path,best['center'],end)
      tree.extend((n,position(n)[:2])for n in path[::max(1,len(path)//30)]);tree.append((path[-1],position(path[-1])[:2]));tree.extend((n,best['center'])for n in starts)
 def ground(self):
    net='GND'
    for p in self.nets[net]:
      if len(p['layers'])==3:continue
      blocked,v=self.available(net);x,y=p['center'];px,py=round(x/STEP),round(y/STEP)
      # Put ground vias outside paste where possible. Search shortest 32 nearby sites.
      yy,xx=np.nonzero(v);dist=(xx-px)**2+(yy-py)**2;ix=np.argsort(dist)[:80]
      goals=[]
      for k in ix:
        a,b=xx[k]*STEP,yy[k]*STEP
        # Avoid an untented via in any component's paste aperture.
        if any(q['poly'].distance(Point(a,b))<DRILL/2+.05 for q in self.pads):continue
        goals.extend(index(a,b,z)for z in p['layers'])
        if len(goals)>=30:break
      if not goals:
        # Center GND islands can use vias between their separated paste apertures.
        ix=np.argsort(dist)[:30];goals=[index(xx[k]*STEP,yy[k]*STEP,z)for k in ix for z in p['layers']]
      starts=[index(x,y,z)for z in p['layers']];path=self.search(net,starts,goals,via=False)
      if path is None:self.failed.append(('GND',p['ref'],p['num']));print('GROUND FAILED',p['ref'],p['num'],flush=True);continue
      self.commit_path(net,path,(x,y));a,b,_=position(path[-1]);self.add_via(a,b,net);self.refresh(net)
 def save(self):
    (PCB.parent/'layout/build/revB-routes.json').write_text(json.dumps(self.items))
    (PCB.parent/'layout/build/revB-route-failures.json').write_text(json.dumps(self.failed,indent=2))
    i=self.ipc;i.begin();old=i.get(['KOT_PCB_TRACE','KOT_PCB_VIA']);i.delete([x['id']['value']for x in old])
    for k in range(0,len(self.items),250):i.create(self.items[k:k+250])
    i.end('Rev B: local analog fanout, buses and grounded four-layer routing');i.save()

def connector_breakout(r):
 for p in [p for p in r.pads if p['ref']=='J2' and str(p['num']).isdigit()]:
    x,y=p['center'];alternate=(int(p['num'])//2)%2
    dest=(x,(1.25+.65*alternate) if y<2 else (4.2+.65*alternate));net=p['net']
    if p['num']=='35':dest=(x,1.25)
    starts=[index(x,y,2)];goals=[index(*dest,2)]
    path=r.search(net,starts,goals,via=False)
    if path is None:raise RuntimeError(('FPC breakout blocked',p['num'],dest))
    r.commit_path(net,path,(x,y),dest);r.add_via(*dest,net);r.refresh(net)
    p['center']=dest;p['layers']=[0,1,2]

def reserve_fine_pad_escapes(r):
 paste=r.raster(unary_union([p['poly'] for p in r.pads]).buffer(DRILL/2+.04))
 centers={f['reference_field']['text']['text']['text']:coord(f['position']) for f in r.fs}
 pads=[p for p in r.pads if p['ref'] in ['U1','U2','U3'] or p['ref'].startswith('RN')]
 pads=[p for p in pads if not p['net'].startswith('unconnected-') and (len(r.nets[p['net']])>1)]
 # Reserve peripheral escape channels before global routing can cut them off.
 for p in sorted(pads,key=lambda p:(0 if p['ref'].startswith('RN') else 1,0 if p['net'].startswith('/E') else 1,p['ref'],int(p['num']))):
    x,y=p['center'];net=p['net'];_,v=r.available(net);v=v.astype(bool)&~paste
    yy,xx=np.nonzero(v);ax=xx*STEP;ay=yy*STEP;dist=(ax-x)**2+(ay-y)**2
    if p['ref'] in ['U2','U3']:
      cx,cy=centers[p['ref']];valid=(abs(ax-cx)<4.7)&(abs(ay-cy)<4.7)
    elif p['ref'].startswith('RN'):
      cx,cy=centers[p['ref']];valid=((ay-cy)*(y-cy)>.2)&(abs(ax-x)<1.3)
    else:valid=dist<9
    ix=np.argsort(np.where(valid,dist,1e9))[:70]
    goals=[index(ax[k],ay[k],z) for k in ix if valid[k] for z in p['layers']]
    starts=[index(x,y,z) for z in p['layers']]
    path=r.search(net,starts,goals,via=False) if goals else None
    if path is None:
      # Retry all nearby exterior sites when the preferred inward corridor is full.
      ix=np.argsort(dist)[:3000:25]
      goals=[index(ax[k],ay[k],z)for k in ix for z in p['layers']]
      path=r.search(net,starts,goals,via=False)
    if path is None:
      Path('/tmp/revB-escape-debug.json').write_text(json.dumps({'items':r.items,'pad':{k:v for k,v in p.items()if k!='poly'}}))
      raise RuntimeError(('Cannot escape pad',p['ref'],p['num']))
    r.commit_path(net,path,(x,y));a,b,_=position(path[-1]);r.add_via(a,b,net);r.refresh(net)
    p['center']=(a,b);p['layers']=[0,1,2]
 print('Reserved',len(pads),'fine-pitch escapes',flush=True)

def main():
 r=Router();connector_breakout(r);print('Ground returns',flush=True);r.ground()
 nets=[n for n,ps in r.nets.items()if len(ps)>1 and n!='GND' and not n.startswith('unconnected-')]
 def priority(n):
    ps=r.nets[n];extent=max(math.dist(a['center'],b['center'])for a in ps for b in ps)
    rank=0 if n.startswith('/E') else 1 if n.startswith('Net-(RN') else 2 if 'VCAP'in n or 'VREFP'in n or 'RLD'in n else 4 if n in ['+3V0','+3V3','VBAT'] else 3
    return rank,extent,n
 for n in sorted(nets,key=priority):print('Routing',n,flush=True);r.route_net(n)
 r.save();print('Saved',len(r.items),'copper items;',len(r.vias),'vias; failures',r.failed,flush=True)
if __name__=='__main__':main()
