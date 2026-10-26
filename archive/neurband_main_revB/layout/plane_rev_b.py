"""Move native-router fallback copper off In1, preserving its dedicated GND plane."""
from ipc_rev_b import *
from shapely.geometry import LineString

def polygon(t):
 def c(v):return int(v.get('x_nm',0))*1e-6,int(v.get('y_nm',0))*1e-6
 return LineString([c(t['start']),c(t['end'])]).buffer(int(t['width']['value_nm'])*.5e-6,quad_segs=16)
i=IPC();tracks=i.get(['KOT_PCB_TRACE']);target=[t for t in tracks if t['layer']=='BL_In2_Cu'];moves=[];remove=[]
for t in tracks:
 if t['layer']!='BL_In1_Cu':continue
 p=polygon(t);net=t['net'].get('name')
 if any(x['net'].get('name')!=net and p.distance(polygon(x))<.1-1e-7 for x in target):remove.append(t['id']['value']);continue
 t['layer']='BL_In2_Cu';moves.append(t);target.append(t)
i.begin()
if moves:i.update(moves)
i.delete(remove);i.end('Rev B: keep In1 exclusively a continuous GND reference');i.call('kiapi.board.commands.RefillZones',{'board':i.doc});i.save()
print('Moved',len(moves),'tracks to In2; removed',len(remove),'conflicting fallback segments for rerouting')
