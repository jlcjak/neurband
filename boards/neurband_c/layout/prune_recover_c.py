"""Prune dead branches while preserving every original connected pad group."""
from connect_components_c import *
import heapq

def padgroups(t,n):
 ids,gs=connected(t,n);pads={p['id']for p in pad_data(t)if p['net']==n};return [os for os in gs.values()if any(o[0]in pads for o in os)]
def recover(t,old,n):
 target=len(padgroups(old,n));objs=[];oldnodes={item_id(c):c for c in copper(old)if net(c)==n}
 for p in pad_data(old):
  if p['net']==n:objs.append((p['id'],p['poly'],p['layers']))
 for c in oldnodes.values():g,z=shape(c);objs.append((item_id(c),g,z))
 tree=STRtree([o[1]for o in objs]);adj=[[]for _ in objs];idx={o[0]:i for i,o in enumerate(objs)}
 for i,(_,g,zs)in enumerate(objs):
  for j in tree.query(g.buffer(.000001)):
   if i<j and set(zs)&set(objs[j][2])and g.distance(objs[j][1])<.000001:adj[i].append(int(j));adj[j].append(i)
 restored=0
 for _ in range(20):
  groups=padgroups(t,n)
  if len(groups)<=target:break
  alive={p['id']for p in pad_data(t)if p['net']==n}|{item_id(c)for c in copper(t)if net(c)==n};starts={idx[o[0]]for o in groups[0]};goals={idx[o[0]]for os in groups[1:]for o in os};dist={i:0 for i in starts};prev={};q=[(0,i)for i in starts];heapq.heapify(q);end=None
  while q:
   d,i=heapq.heappop(q)
   if d!=dist[i]:continue
   if i in goals:end=i;break
   for j in adj[i]:
    c=oldnodes.get(objs[j][0]);cost=0 if objs[j][0]in alive else(max(.001,shape(c)[0].length/2)if c[0]=='segment'else .01);dd=d+cost
    if dd<dist.get(j,float('inf')):dist[j]=dd;prev[j]=i;heapq.heappush(q,(dd,j))
  assert end is not None,('No original pad path',n)
  j=end
  while j not in starts:
   uid=objs[j][0]
   if uid not in alive:t.append(copy.deepcopy(oldnodes[uid]));alive.add(uid);restored+=1
   j=prev[j]
 print('RECOVER',n,restored,flush=True)
def main():
 old=load();save(old,BUILD/'before-connectivity-preserving-prune.kicad_pcb')
 import prune_native_c;prune_native_c.main();t=load()
 for n in {net(c)for c in copper(t)}-{'GND'}:
  if len(padgroups(t,n))>len(padgroups(old,n)):recover(t,old,n)
 # Floating fragments have no electrical role; delete them as complete objects.
 ps=pad_data(t)
 for n in {net(c)for c in copper(t)}-{'GND'}:
  ids,gs=connected(t,n);pads={p['id']for p in ps if p['net']==n};remove_ids(t,{o[0]for os in gs.values()if not any(o[0]in pads for o in os)for o in os})
 save(t);check('safe-pruned')
if __name__=='__main__':main()
