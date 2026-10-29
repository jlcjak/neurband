"""Restore the electrically connected input artwork for bounded repair.
Only raw/post resistor nets are imported from the backed-up baseline.
"""
from file_layout_c import *
from shapely.strtree import STRtree
import re

def main():
 t=load();old=load(BUILD/'before/neurband_c.kicad_pcb')
 analog=lambda n:bool(re.fullmatch('/E[1-8][PN]',n)or n.startswith('Net-(RN'))
 remove_ids(t,{item_id(c)for c in copper(t)if analog(net(c))})
 new=[copy.deepcopy(c)for c in copper(old)if analog(net(c))]
 geoms=[shape(c)for c in new];tree=STRtree([g for g,z in geoms]);kill=set()
 for c in copper(t):
  g,zs=shape(c)
  for j in tree.query(g.buffer(.13)):
   a=new[int(j)];h,az=geoms[int(j)]
   if net(c)!=net(a)and set(zs)&set(az)and g.distance(h)<(.126 if c[0]=='via'or a[0]=='via'else .101):
    assert net(c)not in {'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'};kill.add(item_id(c));break
 remove_ids(t,kill);t.extend(new);save(t)
 print('Restored complete input artwork',len(new),'cleared foreign items',len(kill))
if __name__=='__main__':main()
