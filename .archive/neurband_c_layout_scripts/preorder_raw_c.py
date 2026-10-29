"""Connector-side input banks: south/east In2 pairs and west B-side pairs.

Opposite-layer input projections are excluded, leaving a ground reference
between each bank and its adjacent layer. Crossovers use F.Cu over In1 GND.
"""
from file_layout_c import *
import re

def channel(n):
 m=re.fullmatch(r'/E([1-8])[PN]',n);return int(m[1])if m else None
class RawRouter(Router):
 def available(self,n):
  b,v=super().available(n);ch=channel(n)
  if ch:
   if ch<=4:
    b[2]=1
   else:
    b[1]=1;b[2,self.raster(box(9.5,22.65,14.1,24.8))]=1
   opposite=[g for nn,gs in self.geometry.items()if channel(nn)and(channel(nn)<=4)!=(ch<=4)for g in gs[2 if ch<=4 else 1]]
   if opposite:
    guard=self.raster(unary_union(opposite).buffer(.18));b[1 if ch<=4 else 2,guard]=1;v[guard]=0
  return b,v

def main():
 t=load();remove_ids(t,{item_id(c)for c in copper(t)if channel(net(c))})
 ps=pad_data(t);ends={};new=[]
 for ch in range(1,9):
  for pol in ('P','N'):
   n=f'/E{ch}{pol}';pp=[p for p in ps if p['net']==n]
   a=next(p for p in pp if p['ref']=='J1');b=next(p for p in pp if p['ref'].startswith('RN'))
   av=(a['center'][0],23.0+.7*(int(a['num'])%2));bv=(b['center'][0],b['center'][1]+.8)
   new.extend([track(a['center'],av,n,w=.1),via(*av,n),track(b['center'],bv,n,w=.1),via(*bv,n)])
   layer='In2.Cu'if ch<=4 else'B.Cu'
   if pol=='P':
    port=(av[0]+.5,24.6);new.append(track(av,port,n,layer,.1))
   else:
    port=(av[0]-.5,24.6);new.extend([track(av,(av[0],24.0),n,w=.1),track((av[0],24.0),port,n,w=.1),via(*port,n)])
   ends[n]=(port,bv)
 kill=set()
 for c in copper(t):
  if net(c).startswith('Net-(RN'):continue
  g,zs=shape(c)
  if any(net(c)!=net(a)and set(zs)&set(shape(a)[1])and g.distance(shape(a)[0])<(.13 if c[0]=='via'or a[0]=='via'else .101)for a in new):
   assert net(c)not in {'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'};kill.add(item_id(c))
 remove_ids(t,kill);t.extend(new);save(t)
 save(t,BUILD/'raw-prepared.kicad_pcb')
 (BUILD/'raw-endpoints.json').write_text(json.dumps(ends,indent=2)+'\n')
 if __import__('os').environ.get('PREPARE_ONLY'):return
 r=RawRouter(t);failed=[]
 for ch in [8,7,6,5,1,2,3,4]:
  for pol in ('P','N'):
   n=f'/E{ch}{pol}';a,b=ends[n];z=1 if ch<=4 else 2
   ok=r.link(n,a,[z],b,[z]);print(n,ok,flush=True)
   if not ok:failed.append(n)
  save(t)
 (BUILD/'raw-bank-routing.json').write_text(json.dumps({'endpoints':ends,'failures':failed},indent=2)+'\n')
if __name__=='__main__':main()
