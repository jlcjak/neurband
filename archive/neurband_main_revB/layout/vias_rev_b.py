"""Merge redundant same-net through-vias without expanding their copper envelope."""
from ipc_rev_b import *
from shapely.geometry import Point,LineString
from shapely import unary_union
import math

def pos(v):return tuple(int(v['position'].get(k,0))*1e-6 for k in ['x_nm','y_nm'])
def dia(v):return int(v['pad_stack']['copper_layers'][0]['size']['x_nm'])*1e-6
def drill(v):return int(v['pad_stack']['drill']['diameter']['x_nm'])*1e-6

i=IPC();vs=i.get(['KOT_PCB_VIA']);keep=[];remove=[];bridges=[]
for v in vs:
 a=pos(v);other=next((k for k in keep if math.dist(a,pos(k))<(drill(v)+drill(k))/2+.25-1e-6),None)
 if other is None:keep.append(v);continue
 if v.get('net',{}).get('name')!=other.get('net',{}).get('name'):raise RuntimeError(('Different-net drill collision',v['id'],other['id']))
 b=pos(other);g=LineString([a,b]).buffer(.05,quad_segs=32)
 old=unary_union([Point(*a).buffer(dia(v)/2,quad_segs=64),Point(*b).buffer(dia(other)/2,quad_segs=64)])
 if g.difference(old).area>1e-8:raise RuntimeError('Merge would expand proven copper envelope')
 remove.append(v['id']['value'])
 for layer in ['BL_F_Cu','BL_In2_Cu','BL_B_Cu']:
  bridges.append({'@type':'type.googleapis.com/kiapi.board.types.Track','id':uid(),'start':xy(*a),'end':xy(*b),'width':{'value_nm':'100000'},'layer':layer,'net':v['net']})
i.begin();i.delete(remove)
if bridges:i.create(bridges)
i.end('Rev B: merge redundant close-spaced same-net vias');i.call('kiapi.board.commands.RefillZones',{'board':i.doc});i.save()
print('Merged',len(remove),'redundant vias without expanding copper')
