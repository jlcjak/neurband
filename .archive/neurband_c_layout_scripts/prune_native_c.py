"""Remove dead non-ground route branches in one geometry pass, no editor."""
from file_layout_c import *
from shapely.strtree import STRtree
from collections import defaultdict, deque

def main():
    t=load();entries=defaultdict(list);nodes={};ends={}
    for p in pad_data(t):
        for z in p['layers']:entries[p['net'],z].append((p['id'],p['poly']))
    for c in copper(t):
        n=net(c);uid=item_id(c);g,zs=shape(c);nodes[uid]=c
        for z in zs:
            centerline=LineString([tuple(map(float,get(c,k)[1:3]))for k in ('start','end')])if c[0]=='segment'else g
            entries[n,z].append((uid,centerline))
        if c[0]=='segment'and n!='GND':ends[uid]=(n,zs[0],[Point(tuple(map(float,get(c,k)[1:3])))for k in ('start','end')])
    neighbors={};reverse=defaultdict(set)
    for key,es in entries.items():
        if key[0]=='GND':continue
        tree=STRtree([g for _,g in es])
        for uid,(n,z,ps)in ends.items():
            if key!=(n,z):continue
            nn=[]
            for p in ps:
                linked={es[int(i)][0]for i in tree.query(p.buffer(1e-6))if es[int(i)][0]!=uid and es[int(i)][1].distance(p)<1e-6}
                nn.append(linked)
                for other in linked:reverse[other].add(uid)
            neighbors[uid]=nn
    removed=set();queue=deque(neighbors)
    while queue:
        uid=queue.popleft()
        if uid in removed:continue
        if any(not(s-removed)for s in neighbors[uid]):
            removed.add(uid);queue.extend(reverse[uid])
    remove_ids(t,removed);save(t)
    print('Pruned dead branch segments',len(removed),flush=True)
if __name__=='__main__':main()
