"""Inspect/stitch isolated front-GND fill polygons to the dedicated L2 plane."""
from route_c import *
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args()
r=Router(existing=True);i=r.ipc;_,v=r.available('GND')
feed=LineString([(1.58,8.81),(1.58,9.7),(1.58,11.35),(6.9,11.35),(6.9,14.7),(5.9,14.7)])
v[r.raster(feed.buffer(.855,quad_segs=12))]=0
vias=[Point(x,y)for x,y,n in r.vias if n=='GND']
through=[p['poly']for p in r.nets['GND']if len(p['layers'])==3]
polys=[]
for z in i.get(['KOT_PCB_ZONE']):
 if z.get('type')!='ZT_COPPER'or'BL_F_Cu'not in z.get('layers',[]):continue
 for fill in z.get('filled_polygons',[]):
  if fill['layer']!='BL_F_Cu':continue
  for p in fill.get('shapes',{}).get('polygons',[]):
   points=[coord(q['point'])for q in p['outline']['nodes']if'point'in q]
   holes=[[coord(q['point'])for q in h['nodes']if'point'in q]for h in p.get('holes',[])]
   g=Polygon(points,holes)
   if not g.is_valid:g=g.buffer(0)
   if not g.is_empty:polys.append(g)
print('Front fill polygons',len(polys),flush=True)
for g in polys:
 if any(g.distance(p)<.276 for p in vias)or any(g.distance(p)<.001 for p in through):continue
 mask=r.raster(g)&v.astype(bool);yy,xx=np.nonzero(mask)
 print('No through-return',tuple(round(x,3)for x in g.bounds),'area',round(g.area,3),'normal-via candidates',len(xx),flush=True)
 if len(xx):
  c=g.centroid;key=(xx*STEP-c.x)**2+(yy*STEP-c.y)**2;k=int(np.argmin(key));x,y=xx[k]*STEP,yy[k]*STEP
  print('Stitch candidate',x,y,flush=True)
  if args.apply:r.add_via(x,y,'GND');vias.append(Point(x,y))
if args.apply:
 r.save(incremental=True);i.call('kiapi.board.commands.RefillZones',{'board':i.doc});i.save()
