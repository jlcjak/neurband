"""Select a drill gateway joining disconnected all-layer reachable regions."""
from connect_components_c import *
from shapely.strtree import STRtree
import ctypes

def pathadd(r,n,starts,goals):
 path=r.search(n,starts,goals,True)
 if not path:return False
 a,b=r.coord(path[0]),r.coord(path[-1]);search=r.search;r.search=lambda *args,**kw:path;r.link(n,a[:2],[a[2]],b[:2],[b[2]]);r.search=search;return True

def gateway(t,n):
 r=ReleaseRouter(t);ids,groups=connected(t,n);pads={p['id']for p in r.pads if p['net']==n};gs=[v for v in groups.values()if any(o[0]in pads for o in v)]
 if len(gs)<2:return True
 mask,vs=r.available(n)
 def points(g):return list({r.idx(p,z)for _,g,zs,ps in g for p in ps for z in zs if not mask[z,round(p[1]/r.step),round(p[0]/r.step)]})
 starts,goals=points(gs[0]),points(gs[1]);f=ctypes.CDLL(str(BUILD/'flood3.so'));f.flood3.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]
 seen=[]
 for ss in [starts,goals]:
  arr=np.array(ss,np.int32);o=np.zeros_like(mask);f.flood3(mask.ctypes.data,vs.ctypes.data,r.W,r.H,arr.ctypes.data,len(arr),o.ctypes.data);seen.append(o)
 overlap=seen[0].any(axis=0)&seen[1].any(axis=0)
 # Ordinary pad/drill clearance and all immutable board exclusions.
 legal=~r.vedge
 overlap&=legal
 ys,xs=np.where(overlap[::4,::4]);sites=[(int(x)*.1,int(y)*.1)for y,x in zip(ys,xs)]
 cs=copper(t);geos=[shape(c)[0]for c in cs];tree=STRtree(geos);rank=[]
 for q in sites:
  pt=Point(q);hits=[int(i)for i in tree.query(pt.buffer(.355))if net(cs[int(i)])!=n and pt.distance(geos[int(i)])<.355]
  if any(net(cs[i])in {'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'}for i in hits):continue
  if any(cs[i][0]=='via'and net(cs[i])=='GND'and float(get(cs[i],'at')[1])<=6.3 for i in hits):continue
  cost=sum(1000 if net(cs[i]).startswith(('/E','Net-(RN'))else 20 if net(cs[i]).startswith(('/SPI','/ADC','/I2C','/IMU'))else 10 if net(cs[i])in ['+3V3','+3V3A','VBAT']else 2 for i in hits)
  # Prefer a small number of reworked objects and a short geometric join.
  rank.append((cost+len(hits)*.05,q,hits))
 rank.sort(key=lambda a:a[0]);print('GATEWAY OPTIONS',n,[(a[0],a[1],[net(cs[i])for i in a[2]])for a in rank[:5]],flush=True)
 if not rank:return False
 _,q,hits=rank[0];remove_ids(t,{item_id(cs[i])for i in hits});t.append(via(*q,n));save(t);r=ReleaseRouter(t)
 # All original source points remain on this net; only foreign items were removed.
 ok1=pathadd(r,n,starts,[r.idx(q,z)for z in range(3)]);ok2=pathadd(r,n,goals,[r.idx(q,z)for z in range(3)]);print('GATEWAY RESULT',n,q,ok1,ok2,flush=True);save(t);return ok1 and ok2

def main():
 t=load();save(t,BUILD/'before-region-gateways.kicad_pcb')
 # Clear the moved reference land, preserving the quiet front-layer stub.
 p=next(p for p in pad_data(t)if p['ref']=='C32'and p['num']=='1');kill=set()
 for c in copper(t):
  g,z=shape(c)
  if net(c)!=p['net']and 0 in z and g.distance(p['poly'])<(.126 if c[0]=='via'else .101):kill.add(item_id(c))
 remove_ids(t,kill)
 for p in pad_data(t):
  if p['ref']=='C32'and p['net']=='GND':setc(p['node'],'thermal_bridge_angle',45);setc(p['node'],'thermal_gap',.1);setc(p['node'],'thermal_bridge_width',.2)
 save(t)
 for n in ['/ADC_START','/SWDCLK']:gateway(t,n)
 d=check('region-gateways');close_components(t,d);check('region-closed')
if __name__=='__main__':main()
