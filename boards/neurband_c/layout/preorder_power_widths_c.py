"""Widen power routes where measured clearance and input separation allow it."""
from native_check_c import *
from shapely.strtree import STRtree

def main():
 old=load();save(old,BUILD/'before-power-widths.kicad_pcb');t=copy.deepcopy(old);ps=pad_data(t);input_shapes=collections.defaultdict(list)
 for c in kids(t,'segment'):
  if net(c).startswith('/E')or net(c).startswith('Net-(RN'):input_shapes[uq(get(c,'layer')[1])].append(shape(c)[0])
 inputs={ly:unary_union(gs)for ly,gs in input_shapes.items()};changed=[]
 for n in ['+3V3','VBAT','+3V3A']:
  for ly in LAYERS:
   foreign=[(p['poly'],'pad')for p in ps if p['net']!=n and LAYERS.index(ly)in p['layers']]
   foreign += [(shape(c)[0],c[0])for c in copper(t)if net(c)!=n and LAYERS.index(ly)in shape(c)[1]]
   geos=[g for g,_ in foreign];tree=STRtree(geos);holes=[(Point(*map(float,get(c,'at')[1:3])),float(get(c,'drill')[1])/2)for c in kids(t,'via')if net(c)!=n]
   for c in kids(t,'segment'):
    if net(c)!=n or uq(get(c,'layer')[1])!=ly or float(get(c,'width')[1])>=.25:continue
    line=LineString([tuple(map(float,get(c,k)[1:3]))for k in ['start','end']]);current=float(get(c,'width')[1]);ref='B.Cu'if ly=='In2.Cu'else'In2.Cu'if ly=='B.Cu'else'F.Cu'
    if ref in inputs and line.distance(inputs[ref])<1:continue
    limit=.25
    for i in tree.query(line.buffer(.4)):limit=min(limit,2*(line.distance(geos[int(i)])-.102))
    for q,rad in holes:
     if line.distance(q)<.6:limit=min(limit,2*(line.distance(q)-rad-.202))
    candidates=[w for w in [.25,.2,.15,.127]if w<=limit and w>current+.005]
    if not candidates:continue
    w=max(candidates)
    if line.buffer(w/2+.002).intersects(Polygon([(2,4.8),(6.35,4.8),(6.35,6.85),(2,6.85)])):continue
    area=box(1,1,27.7,26).buffer(1,quad_segs=32).buffer(-(.3+w/2+.002))
    if not area.covers(line):continue
    if ly=='B.Cu'and any(line.buffer(w/2+.002).intersects(Point(x,y).buffer(1.5))for x,y in [(1.6,1.6),(26.4,1.6),(1.6,25.4),(26.6,22.6)]):continue
    changed.append(dict(id=item_id(c),net=n,layer=ly,old_width_mm=current,new_width_mm=w,length_mm=line.length));setc(c,'width',num(w))
 save(t);d=check('power-widths')
 if d['unconnected_items']or any(v['severity']=='error'for v in d['violations']):save(old);check('power-widths-retained');changed=[]
 (BUILD/'power-width-changes.json').write_text(json.dumps(changed,indent=2)+'\n');print('POWER WIDTH CHANGES',len(changed),collections.Counter(r['new_width_mm']for r in changed),flush=True)
if __name__=='__main__':main()
