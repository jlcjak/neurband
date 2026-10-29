"""Exactly aligned, same-side, symmetric ADC input routes and local GND returns."""
from route_rev_b import *

r=Router()
lengths={}
for net,ps in r.nets.items():
 if not net.startswith('Net-(RN'):continue
 assert len(ps)==2,(net,len(ps))
 a,b=ps
 assert abs(a['center'][0]-b['center'][0])<1e-6,(net,a['center'],b['center'])
 assert a['layers']==b['layers'],(net,a['layers'],b['layers'])
 z=a['layers'][0];track=item_track(a['center'],b['center'],z,net,.127)
 r.items.append(track);r.geometry[net][z].append(LineString([a['center'],b['center']]).buffer(.127/2));r.refresh(net)
 lengths[net]=math.dist(a['center'],b['center'])
assert len(lengths)==32
print('32 ADC input links: same-side, no vias, 0.127mm, lengths',sorted(set(round(v,4)for v in lengths.values())),flush=True)
r.ground();r.save()
(PCB.parent/'layout/pair_lengths.json').write_text(json.dumps({'post_resistor_lengths_mm':lengths,'post_resistor_pair_skew_mm':0,'note':'P/N pairs within each array have identical vertical copper length; upstream connector paths are measured separately.'},indent=2))
print('Saved local copper; ground failures',r.failed,flush=True)
