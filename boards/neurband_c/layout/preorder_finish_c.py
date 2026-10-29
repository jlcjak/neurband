"""Local clearance repairs and ground anchors; refill with native KiCad afterwards."""
from file_layout_c import *
from native_check_c import check

def main():
 t=load();save(t,BUILD/'before-local-finish.kicad_pcb')
 old=[(4.5,7.2),(4.575,7.275)];vs=[]
 for c in copper(t):
  for key in (['at']if c[0]=='via'else['start','end']):
   q=get(c,key)
   if net(c)=='+3V3'and any(math.dist(tuple(map(float,q[1:3])),xy)<.001 for xy in old):q[1:3]=['4.8','7.15']
  if c[0]=='via'and net(c)=='+3V3'and tuple(map(float,get(c,'at')[1:3]))==(4.8,7.15):vs.append(item_id(c))
 remove_ids(t,set(vs[1:]))
 for p in pad_data(t):
  if p['ref']=='C9'and p['num']=='2':setc(p['node'],'thermal_bridge_angle',45);setc(p['node'],'thermal_gap',.1)
 save(t);r=Router(t,width=.2)
 for ref0 in ['C18','C20','C9','C32','C33']:
  p=next(p for p in r.pads if p['ref']==ref0 and p['net']=='GND');b,v=r.available('GND');x,y=p['center']
  sites=[(round((x+dx)/.025)*.025,round((y+dy)/.025)*.025)for dx in np.arange(-1.1,1.11,.1)for dy in np.arange(-1.1,1.11,.1)]
  sites=sorted(set(sites),key=lambda q:math.dist(q,p['center']))
  for q in sites:
   ix,iy=round(q[0]/.025),round(q[1]/.025)
   if not v[iy,ix]:continue
   if r.link('GND',p['center'],[0],q,[0],False):
    c=via(*q);t.append(c);g,zs=shape(c)
    for z in zs:r.geometry['GND'][z].append(g)
    r.vias.append((*q,'GND'));r.refresh('GND');print('GROUND',ref0,q,flush=True);break
  else:print('GROUND BLOCKED',ref0,flush=True)
 save(t);check('local-finish')
if __name__=='__main__':main()
