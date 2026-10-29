"""Measure polish changes and tie supplied analog outputs to the delivered copper."""
from file_layout_c import *
import hashlib,csv
POLISH=BUILD/'polish';FLEX=Path('boards/neurband_c_flex')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(n):
 if not isinstance(n,list):return n
 return [clean(c)for c in n if not(isinstance(c,list)and c[0]in ['uuid','tstamp'])]
def copper_signature(t):
 return sorted(dump(clean(c))for c in copper(t)),sorted((p['ref'],p['num'],p['net'],p['center'],tuple(p['layers']),p['poly'].wkt)for p in pad_data(t)if p['layers']),sorted(dump(clean(z))for z in kids(t,'zone'))
def main():
 t=load();ps=pad_data(t);base=load(POLISH/'analog-source.kicad_pcb')if (POLISH/'analog-source.kicad_pcb').exists()else load(POLISH/'before-c18.kicad_pcb');assert copper_signature(t)==copper_signature(base),'Copper changed after full analog run'
 a=json.loads((BUILD/'acceptance.json').read_text());analysed=json.loads((POLISH/'run-all-receipt.json').read_text())['analysed_pcb_sha256'];a['analysed_pcb_sha256']=analysed;a['pcb_sha256']=sha(PCB);a['post_analysis_changes']='Delivered tracks, vias, pad geometry and filled zones compare identical to the analog source save';(BUILD/'acceptance.json').write_text(json.dumps(a,indent=2)+'\n')
 fp=FLEX/'neurband_c_flex.kicad_pcb';f=load(fp);old=load(FLEX/'build/preorder_20261029/polish/before-polish.kicad_pcb');normal=lambda t,k:sorted(dump(clean(c))for c in kids(t,k));j=lambda t:next(z for z in kids(t,'footprint')if ref(z)=='J1')
 assert normal(f,'segment')==normal(old,'segment')and normal(f,'via')==normal(old,'via')and normal(j(f),'pad')==normal(j(old),'pad')
 rects=[c for c in kids(f,'gr_rect')if uq(get(c,'layer')[1])=='User.2'];assert len(rects)==1 and get(rects[0],'fill')[1]=='yes'
 fd=json.loads((FLEX/'build/preorder_20261029/polish/final-drc.json').read_text());fe=json.loads((FLEX/'build/preorder_20261029/polish/final-erc.json').read_text());assert not fd['violations']and not fd['unconnected_items']and not fd.get('schematic_parity',[])and not any(s['violations']for s in fe['sheets'])
 flexproof=dict(pcb_sha256=sha(fp),segments_unchanged=len(kids(f,'segment')),vias_unchanged=len(kids(f,'via')),fingers_unchanged=True,stiffener=dict(layer='User_2',closed=True,filled=True,bounds_mm=[59.75,54.8,70.25,58.5]),drc_errors=0,unconnected=0,parity=0,erc_violations=0,order=json.loads(fp.with_suffix('.fab.json').read_text())['order']);assert flexproof['order']is False
 (FLEX/'build/preorder_20261029/polish/proof.json').write_text(json.dumps(flexproof,indent=2)+'\n')
 imu=[]
 for name,vid in [('E1N','13954416-5887-474e-9d7a-823946ec70da'),('E2P','66aabfa7-b441-44d4-bd5f-fcf855ecd937')]:
  v=next(c for c in kids(t,'via')if item_id(c)==vid);g=shape(v)[0];q=list(map(float,get(v,'at')[1:3]));dd={p['num']:g.distance(p['poly'])for p in ps if p['ref']=='U5'and p['num']in ['13','14']};assert min(dd.values())>=.4;imu.append(dict(net=name,via_mm=q,land_gap_to_U5_pins_mm=dd))
 moves=json.loads((POLISH/'pad-via-moves.json').read_text());pasted=[p for p in ps if p['layers']and any('Paste'in uq(s)for s in get(p['node'],'layers')[1:])]
 for m in moves:
  q=m.get('new',m['old']);p=min(pasted,key=lambda p:p['poly'].distance(Point(q)));m['nearest_pasted_pad']=p['ref']+'.'+p['num'];m['minimum_hole_to_pasted_pad_mm']=p['poly'].distance(Point(q))-.15
 edge=lambda g:min(g.bounds[0],g.bounds[1],28.7-g.bounds[2],27-g.bounds[3])
 edgeproof={'C29_pad2_mm':edge(next(p['poly']for p in ps if p['ref']=='C29'and p['num']=='2')),'right_3V3A_track_mm':min(28.7-shape(c)[0].bounds[2]for c in kids(t,'segment')if net(c)=='+3V3A'and shape(c)[0].bounds[2]>28),'bottom_GND_via_mm':edge(shape(next(c for c in kids(t,'via')if item_id(c)=='773c839d-d9fd-465c-a40e-766a0e087d99'))[0]),'RF_DNP_pad_min_mm':{r:min(edge(p['poly'])for p in ps if p['ref']==r)for r in ['C22','C23']}}
 assert min(edgeproof[k]for k in ['C29_pad2_mm','right_3V3A_track_mm','bottom_GND_via_mm'])>=.39999
 cell=[];arrows=[]
 for c in kids(t,'gr_line'):
  if uq(get(c,'layer')[1])!='F.SilkS':continue
  a1,b1=[tuple(map(float,get(c,k)[1:3]))for k in ['start','end']];g=LineString([a1,b1]).buffer(.075)
  if a1[0]==b1[0]and a1[0]in [10.5,22.5]or a1[1]==b1[1]==21.7:cell.append(g)
  if all(20.3<=x<=20.9 and 19.99<=y<=20.61 for x,y in [a1,b1]):arrows.append(g)
 front=unary_union([p['poly']for p in ps if 0 in p['layers']]);cellgap=min(g.distance(front)for g in cell);arrowgap=min(g.distance(front)for g in arrows);assert cellgap>=.14999 and arrowgap>=.14999
 for p in ps:
  if p['ref']in ['C22','C23']:assert '"F.Paste"'not in get(p['node'],'layers')[1:]
 out=dict(pcb_sha256=sha(PCB),analysed_pcb_sha256=analysed,post_analysis_copper_and_fill_identical=True,full_run_all_log_sha256=sha(POLISH/'run-all.log'),model=a['model'],imu_vias=imu,via_clearance_trials=moves,C18=json.loads((POLISH/'c18-result.json').read_text()),edge_clearances=edgeproof,cell=dict(layer='F.SilkS',nominal_x_mm=[10.5,22.5],clipped_y_mm=[.2,21.7],minimum_stroke_pad_gap_mm=cellgap),marker=json.loads((POLISH/'marker-proof.json').read_text()),arrow_minimum_stroke_pad_gap_mm=arrowgap,J1_pin1_dot_mm=list(map(float,get(next(c for c in kids(t,'gr_circle')if item_id(c)=='40e41df5-79c4-4485-88c5-7a1cadbc9df0'),'center')[1:3])),DNP_C22_C23_paste_removed=True,flex=flexproof)
 out['coordinator_delta']=json.loads((POLISH/'coordinator-delta.json').read_text())if (POLISH/'coordinator-delta.json').exists()else None
 out['full_analog_run']=json.loads((POLISH/'run-all-receipt.json').read_text())
 artifacts=[PCB,fp,PCB.with_suffix('.step'),PCB.parent/'neurband_c_board_only.step',fp.with_suffix('.step'),PCB.parent/'neurband_c_bom.csv',BUILD/'positions.csv',Path('docs/media/board_layers.png'),Path('docs/media/board_top.png'),Path('docs/media/board_bottom.png')]
 out['artifact_sha256']={str(p):sha(p)for p in artifacts}
 (POLISH/'proof.json').write_text(json.dumps(out,indent=2)+'\n');print('POLISH PROOF',out,flush=True)
if __name__=='__main__':main()
