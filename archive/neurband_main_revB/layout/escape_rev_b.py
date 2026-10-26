"""Pin-aligned ADC links and separate left/right raw-input through-via fields.
The two surfaces' raw signals escape to different fields, avoiding through-vias
on the opposite AFE's straight input copper. Native DRC rejects unsafe output.
"""
from close_rev_b import *

r=Router();paste=r.raster(unary_union([p['poly']for p in r.pads]).buffer(DRILL/2+.04));orig=r.available

def available(n):
 b,v=orig(n);v[paste]=0;return b,v
r.available=available
# All post-resistor routes are straight, symmetric, surface-local 0.127mm.
for n,ps in r.nets.items():
 if not n.startswith('Net-(RN'):continue
 a,b=ps;assert abs(a['center'][0]-b['center'][0])<1e-6 and a['layers']==b['layers']
 z=a['layers'][0];r.items.append(item_track(a['center'],b['center'],z,n,.127));r.geometry[n][z].append(LineString([a['center'],b['center']]).buffer(.127/2));r.refresh(n)
# Give connector signal pads access to a layer change before global copper exists.
for p in sorted([p for p in r.pads if p['ref']=='J2' and (p['net'].startswith('/E') or p['net']=='/BIAS_E')],key=lambda p:(p['center'][1],p['center'][0])):
 x,y=p['center'];n=p['net'];_,v=r.available(n);yy,xx=np.nonzero(v);ax=xx*STEP;ay=yy*STEP
 valid=(abs(ax-x)<.16)&(ay>1.3)&(ay<3.1)
 if y>2:valid|=(abs(ax-x)<.16)&(ay>4.15)&(ay<4.6)
 desired=1.55 if y<2 else 2.7
 score=(ax-x)**2+(ay-desired)**2
 ix=np.argsort(np.where(valid,score,1e9))[:100];goals=[index(ax[k],ay[k],2)for k in ix if valid[k]]
 path=r.search(n,[index(x,y,2)],goals,via=False)
 if path is None:raise RuntimeError(('J2 escape',p['num']))
 r.commit_path(n,path,(x,y));a,b,_=position(path[-1]);r.add_via(a,b,n);r.refresh(n)
 print('J2 escape',p['num'],(a,b),flush=True)
# Reserve every RN's upward stub before any of the long surface fanouts.
raw=[p for p in r.pads if p['ref'].startswith('RN') and p['net'].startswith('/E')]
for p in raw:
 x,y=p['center'];z=p['layers'][0];n=p['net'];end=(x,7.0)
 r.items.append(item_track((x,y),end,z,n,.1));r.geometry[n][z].append(LineString([(x,y),end]).buffer(.05));r.refresh(n)
 p['center']=end
plans=[]
for side in [0,2]:
 ps=sorted([p for p in raw if p['layers']==[side]],key=lambda p:p['center'][0],reverse=side==2)
 for k,p in enumerate(ps):
  row=3-k//4;col=k%4 if side==0 else 3-k%4
  target=((11.8+.9*col,2.9+.9*row)if side==0 else(28.5+.9*col,6.0+.9*row))
  _,v=r.available(p['net']);gx,gy=round(target[0]/STEP),round(target[1]/STEP)
  if not v[gy,gx]:
   yy,xx=np.nonzero(v);dist=(xx*STEP-target[0])**2+(yy*STEP-target[1])**2;ix=int(np.argmin(dist))
   if dist[ix]>.4**2:raise RuntimeError(('No legal header via',p['net'],target))
   target=(xx[ix]*STEP,yy[ix]*STEP)
  r.add_via(*target,p['net']);r.refresh(p['net']);plans.append((p,target,side))
for p,target,side in plans:
 n=p['net'];a=p['center'];path=r.search(n,[index(*a,side)],[index(*target,side)],via=False)
 if path is None:raise RuntimeError(('RN header fanout',p['ref'],p['num'],target))
 r.commit_path(n,path,a,target);print('RN escape',n,target,flush=True)
print('Local grounds',flush=True);r.ground();save_checked(r)
