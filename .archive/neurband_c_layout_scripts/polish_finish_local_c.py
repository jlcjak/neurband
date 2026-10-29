"""Remaining local clearance trials, accepted only after native checks."""
from polish_preorder_c import *
def main():
 old=load();t=copy.deepcopy(old);p=next(p for p in pad_data(t)if p['ref']=='C18'and p['num']=='2');q=(4.58,7.15);t.append(via(*q));wire(t,'GND',[p['center'],q],'F.Cu',.2)
 ok=accept(old,t,'polish-c18-ground');r=json.loads((POLISH/'c18-result.json').read_text());r.update(ground_anchor_added=ok,ground_via=list(q)if ok else None,ground_link_mm=.75 if ok else None);(POLISH/'c18-result.json').write_text(json.dumps(r,indent=2)+'\n')
 rows=json.loads((POLISH/'pad-via-moves.json').read_text())
 for row in rows:
  if row['success']:continue
  xy=tuple(row['old']);old=load();vv=next(c for c in kids(old,'via')if math.dist(tuple(map(float,get(c,'at')[1:3])),xy)<.001);n=net(vv);vid=item_id(vv);ps=[p for p in pad_data(old)if p['layers']and p['node'][2]=='smd'];foreign=unary_union([shape(c)[0]for c in copper(old)if net(c)!=n]+[p['poly']for p in ps if p['net']!=n]);own=unary_union([p['poly']for p in ps if p['net']==n]);av=[Point(*map(float,get(c,'at')[1:3]))for c in kids(old,'via')if item_id(c)!=vid];cands=[]
  for ix in range(-24,25):
   for iy in range(-24,25):
    q=(round(xy[0]+ix*.025,5),round(xy[1]+iy*.025,5));p=Point(q)
    if math.dist(q,xy)>.6 or p.distance(foreign)<.3251 or p.distance(own)<.255 or min(p.distance(g)for g in av)<.5501:continue
    cands.append(q)
  cands.sort(key=lambda q:math.dist(q,xy));print('CLEARANCE CANDIDATES',n,xy,len(cands),cands[:4],flush=True)
  for q in cands[:4]:
   t=copy.deepcopy(old);translate_via(t,vid,q)
   if accept(old,t,'polish-pad-via-wide'):
    row.update(success=True,new=list(q));break
 (POLISH/'pad-via-moves.json').write_text(json.dumps(rows,indent=2)+'\n');print('RESULT',rows,flush=True)
if __name__=='__main__':main()
