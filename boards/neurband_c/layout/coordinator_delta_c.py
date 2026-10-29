"""Only the two coordinator-requested solderability and pin-1-marker corrections."""
from polish_preorder_c import *
import shutil,hashlib

def main():
 old=load(POLISH/'before-coordinator-delta.kicad_pcb');t=copy.deepcopy(old);vid='2f5600a1-0e9a-417d-89c6-8d29ff0eab78';dotid='40e41df5-79c4-4485-88c5-7a1cadbc9df0';q=(24.7,12.8)
 vv=next(c for c in kids(t,'via')if item_id(c)==vid);setc(vv,'at',*map(num,q))
 remove_ids(t,{item_id(c)for c in kids(t,'segment')if net(c)=='GND'and any(math.dist(tuple(map(float,get(c,k)[1:3])),(26.975,12.725))<.001 for k in ['start','end'])})
 wire(t,'GND',[(27.6125,12.725),(27.1,12.45),(26.3,12.45),(25.9,12.35),(24.7,12.35),q],'F.Cu',.15)
 dot=next(c for c in kids(t,'gr_circle')if item_id(c)==dotid);setc(dot,'center',9.075,20.65);setc(dot,'end',9.2,20.65)
 assert sorted(dump(f)for f in kids(t,'footprint'))==sorted(dump(f)for f in kids(old,'footprint'))
 assert accept(old,t,'coordinator-delta'),'Targeted corrections failed native gate'
 t=load();ps=pad_data(t);cp=next(p for p in ps if p['ref']=='C6'and p['num']=='2');holegap=cp['poly'].distance(Point(q))-.15;assert holegap>=.1
 glyph=Point(9.075,20.65).buffer(.125,quad_segs=32);front=[p for p in ps if 0 in p['layers']];distances=sorted((glyph.distance(p['poly']),p['ref'],p['num'])for p in front);assert distances[0][1:] == ('J1','1')and distances[0][0]>=.15
 proof=dict(C6=dict(via_id=vid,old_mm=[26.975,12.725],new_mm=list(q),hole_to_pad_mm=holegap,footprint_and_edge_track_unchanged=True),J1_dot=dict(id=dotid,old_mm=[8.75,20.35],new_mm=[9.075,20.65],radius_mm=.125,nearest_pads=[dict(gap_mm=d,ref=r,pad=n)for d,r,n in distances[:5]]),drc_errors=0,unconnected=0,parity=0)
 (POLISH/'coordinator-delta.json').write_text(json.dumps(proof,indent=2)+'\n');print('TARGETED PROOF',proof,flush=True)
 shutil.copyfile(PCB,POLISH/'analog-source.kicad_pcb');shutil.copyfile(BUILD/'positions.csv',POLISH/'before-delta-positions.csv')
if __name__=='__main__':main()
