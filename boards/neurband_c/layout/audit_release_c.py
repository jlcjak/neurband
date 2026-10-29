"""Measure final native routing, assembly interfaces, and explicit acceptance exceptions."""
from file_layout_c import *
import hashlib,re,csv
sys.path.insert(0,'sim/preorder')
from pcbgeom import Board
from coupling import gnd_fill
from shapely.ops import linemerge

def main():
 t=load();ps=pad_data(t);gv=[c for c in kids(t,'via')if net(c)=='GND'];fills=gnd_fill(Board(str(PCB)));out={'pcb_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest()}
 # Pads and explicit links belong to the ground geometry as well as filled zones.
 ground={ly:[g]for ly,g in fills.items()}
 for p in ps:
  if p['net']=='GND':
   for z in p['layers']:ground[LAYERS[z]].append(p['poly'])
 for c in copper(t):
  if net(c)=='GND':
   g,zs=shape(c)
   for z in zs:ground[LAYERS[z]].append(g)
 ground={ly:unary_union(gs)for ly,gs in ground.items()};ties=np.array([list(map(float,get(c,'at')[1:3]))for c in gv]+[list(p['center'])for p in ps if p['node'][2]=='thru_hole'and p['net']=='GND'])
 frags={}
 for ly,gg in ground.items():
  rows=[]
  for pg in (gg.geoms if hasattr(gg,'geoms')else[gg]):
   if pg.geom_type!='Polygon'or pg.area<.2:continue
   anchors=int(contains_xy(pg.buffer(.001),ties[:,0],ties[:,1]).sum());rows.append(dict(area_mm2=round(pg.area,4),anchors=anchors,bounds=list(pg.bounds)))
  frags[ly]=sorted(rows,key=lambda q:-q['area_mm2'])
 out['ground_components']=frags
 gaps=collections.defaultdict(list)
 for n in {net(c)for c in kids(t,'segment')if net(c).startswith('/E')or net(c).startswith('Net-(RN')}:
  vs=[Point(*map(float,get(c,'at')[1:3])).buffer(.352)for c in kids(t,'via')if net(c)==n]
  own=unary_union(vs);lines=[]
  for c in kids(t,'segment'):
   if net(c)==n and uq(get(c,'layer')[1])=='In2.Cu':lines.append(LineString([tuple(map(float,get(c,k)[1:3]))for k in ['start','end']]))
  if not lines:continue
  missing=unary_union(lines).difference(ground['B.Cu']).difference(own)
  missing=linemerge(missing)if missing.geom_type=='MultiLineString'else missing
  parts=list(missing.geoms)if hasattr(missing,'geoms')else[missing];parts=[g for g in parts if g.length>.001]
  if parts:gaps[n]=dict(total_length_mm=round(sum(g.length for g in parts),4),max_gap_mm=round(max(g.length for g in parts),4),bounds=[list(g.bounds)for g in parts])
 out['in2_reference_gaps_excluding_own_via_antipads']=dict(gaps)
 pasted=[p for p in ps if p['node'][2]=='smd'and any('Paste'in uq(s)for s in get(p['node'],'layers')[1:])];near=[]
 for c in kids(t,'via'):
  q=tuple(map(float,get(c,'at')[1:3]));rad=float(get(c,'drill')[1])/2
  for p in pasted:
   d=p['poly'].distance(Point(q))-rad
   if d<.1999:near.append(dict(via=list(q),via_net=net(c),pad=p['ref']+'.'+p['num'],pad_net=p['net'],hole_pad_gap_mm=round(d,4)))
 out['via_hole_to_pasted_pad_under_0p2_mm']=sorted(near,key=lambda q:q['hole_pad_gap_mm'])
 active=lambda n:n.startswith(('/I2C_','/SPI_','/IMU_INT','/ADC_','/LED'))or n=='Net-(D1-A)'
 ret=[];gxy=np.array([list(map(float,get(c,'at')[1:3]))for c in gv])
 for c in kids(t,'via'):
  if not active(net(c)):continue
  q=np.array(list(map(float,get(c,'at')[1:3])))
  if math.dist(q,(20.2,10.1))<=8:ret.append(dict(net=net(c),via=q.tolist(),ground_distance_mm=round(float(np.min(np.sum((gxy-q)**2,axis=1))**.5),4)))
 out['digital_transition_ground']=sorted(ret,key=lambda q:-q['ground_distance_mm'])
 # Check broadside projection on every pair of disjoint copper layers, including lands/barrels.
 from shapely.strtree import STRtree
 its=[(net(c),*shape(c))for c in copper(t)]+[(p['net'],p['poly'],p['layers'])for p in ps if p['layers']]
 analog=lambda n:n.startswith('/E')or n.startswith('Net-(RN')
 digital=[v for v in its if active(v[0])];electrodes=[v for v in its if analog(v[0])];tree=STRtree([g for n,g,z in electrodes]);overlaps=[]
 for n,g,z in digital:
  for i in tree.query(g):
   nn,gg,zz=electrodes[int(i)]
   if set(z).isdisjoint(zz)and g.intersection(gg).area>1e-6:overlaps.append(dict(digital=n,electrode=nn,digital_layers=z,electrode_layers=zz,projected_overlap_mm2=g.intersection(gg).area))
 out['active_digital_electrode_projected_overlap_count']=len(overlaps);out['active_digital_electrode_projected_overlaps']=overlaps

 rf={'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'};before=load(BUILD/'cpl_baked.kicad_pcb')
 normalize=lambda c:dump([e for e in c if not(isinstance(e,list)and e[0]=='uuid')])
 out['rf_tracks_unchanged']=sorted(normalize(c)for c in copper(t)if net(c)in rf)==sorted(normalize(c)for c in copper(before)if net(c)in rf)
 a=next(f for f in kids(t,'footprint')if ref(f)=='AE1');b=next(f for f in kids(before,'footprint')if ref(f)=='AE1')
 out['radiator_unchanged']=pos(a)==pos(b)and sorted(dump(c)for c in kids(a,'fp_poly'))==sorted(dump(c)for c in kids(b,'fp_poly'))
 frozen={'J1','J2','J3','SW1','D1',*['TP'+str(i)for i in range(1,6)]};oldpads=collections.defaultdict(list)
 for p in pad_data(before):
  if p['ref']in frozen:oldpads[(p['ref'],p['num'])].append(p['center'])
 out['fixed_pad_max_delta_mm']=max(min(math.dist(p['center'],q)for q in oldpads[(p['ref'],p['num'])])for p in ps if p['ref']in frozen)
 ep=next(p for p in ps if p['ref']=='U1'and p['num']=='49')['poly'];ep_vias=[c for c in kids(t,'via')if net(c)=='GND'and ep.covers(shape(c)[0])]
 out['intentional_ep_vias']=len(ep_vias);out['nearest_other_via_hole_to_ep_mm']=round(min(ep.distance(Point(*map(float,get(c,'at')[1:3])))-float(get(c,'drill')[1])/2 for c in kids(t,'via')if c not in ep_vias),4)
 (BUILD/'release-audit.json').write_text(json.dumps(out,indent=2)+'\n');print('PAD EXCEPTIONS',len(near),near,flush=True);print('REFERENCE GAPS',out['in2_reference_gaps_excluding_own_via_antipads'],flush=True);print('DIGITAL RETURN',out['digital_transition_ground'][:8],flush=True);print('RF/FROZEN',out['rf_tracks_unchanged'],out['radiator_unchanged'],out['fixed_pad_max_delta_mm'],'EP',out['nearest_other_via_hole_to_ep_mm'],flush=True)
if __name__=='__main__':main()
