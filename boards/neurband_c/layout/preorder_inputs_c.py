"""Paired input fanout on F.Cu/In2.Cu, with B.Cu reserved as its reference.

ADS-side links use inward vias under the TQFP and tented vias under the
array bodies, clear of soldered pads. ADS-side In2 routes reference B.Cu; connector-side B routes reference In2.
"""
from file_layout_c import *
def electrode(n):return n.startswith('/E')or n.startswith('Net-(RN')
class InputRouter(Router):
 def available(self,n):
  b,v=super().available(n)
  if n.startswith('Net-(RN'):
   b[2]=1;b[1,int(18.65/self.step):,:]=1
  elif n.startswith('/E'):
   b[1]=1;b[2,:int(18.7/self.step),:]=1
  return b,v

def main():
 t=load();remove_ids(t,{item_id(c)for c in copper(t)if electrode(net(c))})
 # Clear foreign copper from the two reference windows. GND vias stay.
 post_window=box(10.7,13.0,26.1,18.65);raw_window=box(9.7,18.7,25.7,24.6)
 clear=set()
 for c in copper(t):
  if net(c)=='GND':continue
  g,zs=shape(c)
  if (2 in zs and g.intersects(post_window))or(1 in zs and g.intersects(raw_window)):clear.add(item_id(c))
 remove_ids(t,clear)
 ps=pad_data(t);by={ref(f):f for f in kids(t,'footprint')}
 post={};raw={};new=[]
 def escape(n,p,q):
  new.append(track(p['center'],q,n,w=.1));new.append(via(*q,n))
 for n in sorted({p['net']for p in ps if electrode(p['net'])}):
  pp=[p for p in ps if p['net']==n]
  if n.startswith('Net-(RN'):
   a=next(p for p in pp if p['ref']=='U2');b=next(p for p in pp if p['ref'].startswith('RN'))
   x,y=a['center'];av=(x,y-(1.2 if int(a['num'])%2 else 1.9))
   x,y=b['center'];bv=(x,pos(by[b['ref']])[1])
   escape(n,a,av);escape(n,b,bv)
   ap=(av[0],15.0);bp=(bv[0],bv[1]-.6)
   new.extend([track(av,ap,n,'In2.Cu',.1),track(bv,bp,n,'In2.Cu',.1)])
   post[n]=(ap,bp)
  else:
   a=next(p for p in pp if p['ref']=='J1');b=next(p for p in pp if p['ref'].startswith('RN'))
   x,y=a['center'];av=(x,23.0+.7*(int(a['num'])%2))
   x,y=b['center'];bv=(x,y+.8)
   escape(n,a,av);escape(n,b,bv)
   ap=(av[0],24.6 if int(a['num'])%2 else 22.2);bp=(bv[0],19.1 if bv[1]>19 else 19.4)
   new.extend([track(av,ap,n,'B.Cu',.1),track(bv,bp,n,'B.Cu',.1)])
   raw[n]=(ap,bp)
 for c in new:
  n=net(c);g,zs=shape(c)
  if c[0]=='via':
   q=Point(tuple(map(float,get(c,'at')[1:3])))
   bad=[(p['ref'],p['num'],round(q.distance(p['poly']),4))for p in ps if q.distance(p['poly'])<.35-1e-6]
  else:bad=[(p['ref'],p['num'])for p in ps if p['net']!=n and any(z in p['layers']for z in zs)and g.distance(p['poly'])<.1-1e-6]
  assert not bad,(n,c[0],g.bounds,bad)
 kill=set();rf={'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'}
 for c in copper(t):
  n=net(c);g,zs=shape(c)
  for a in new:
   if n==net(a):continue
   h,az=shape(a)
   if not set(zs)&set(az):continue
   if g.distance(h)<(.13 if c[0]=='via'or a[0]=='via'else .101):
    assert n not in rf,(n,'RF protected')
    if c[0]=='via'and n=='GND':
     x,y=map(float,get(c,'at')[1:3]);assert not(abs(x-6)<.01 and y>12)and math.dist((x,y),(6.2,3))>.01
    kill.add(item_id(c));break
 remove_ids(t,kill);t.extend(new);save(t)
 r=InputRouter(t);failed=[]
 for n,(a,b)in sorted(post.items(),reverse=True):
  ok=r.link(n,a,[1],b,[1],False)
  if not ok:ok=r.link(n,a,[1],b,[1],True)
  print('POST',n,ok,flush=True)
  if not ok:failed.append(n)
 save(t)
 r=InputRouter(t)
 for ch in range(1,9):
  for pol in ('P','N'):
   n=f'/E{ch}{pol}';a,b=raw[n];ok=r.link(n,a,[2],b,[2])
   print('RAW',n,ok,flush=True)
   if not ok:failed.append(n)
  save(t)
 (BUILD/'input-rebuild.json').write_text(json.dumps({'post_vias':post,'raw_vias':raw,'failures':failed,'cleared_foreign_items':len(kill)},indent=2)+'\n')
 save(t)
if __name__=='__main__':main()
