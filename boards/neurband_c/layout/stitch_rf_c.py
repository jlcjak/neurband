"""Stitch the antenna-side counterpoise; never intrude on its radiator or line gap."""
from route_c import *
r=Router(existing=True)
feed=LineString([(1.58,8.81),(1.58,9.7),(1.58,11.35),(6.9,11.35),(6.9,14.7),(5.9,14.7)])
candidates=[(6,13.4)]+[(6,y)for y in [16.2,18.2,20.2,22.2,24.2,26.2]]+[(7.8,10.5),(8.1,11.8)]
for x,y in candidates:
 if feed.distance(Point(x,y))<.805:continue
 if any(math.dist((x,y),(a,b))<.56 for a,b,n in r.vias):continue
 if any(math.dist((x,y),p['center'])<.56 for p in r.pads if len(p['layers'])==3):continue
 _,v=r.available('GND')
 if not v[round(y/STEP),round(x/STEP)]:continue
 r.add_via(x,y,'GND');r.refresh('GND');print('RF ground stitch',x,y,flush=True)
r.save(incremental=True)
