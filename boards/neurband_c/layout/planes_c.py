"""Enforce TI/Nordic copper exclusions and fill four GND pours."""
from ipc_c import *
from shapely.geometry import box, LineString, Polygon, Point
from shapely.ops import unary_union
ALL=['BL_F_Cu','BL_In1_Cu','BL_In2_Cu','BL_B_Cu']
def poly(g):
 return {'polygons':[{'outline':{'closed':True,'nodes':[{'point':xy(x,y)}for x,y in list(g.exterior.coords)[:-1]]}}]}
def keepout(name,g,layers,tracks=False,vias=False,pads=False):
 return {'@type':'type.googleapis.com/kiapi.board.types.Zone','id':uid(),'type':'ZT_RULE_AREA','layers':layers,'name':name,'outline':poly(g),'rule_area_settings':{'keepout_copper':True,'keepout_tracks':tracks,'keepout_vias':vias,'keepout_pads':pads,'keepout_footprints':False}}
i=IPC();i.begin();i.delete([z['id']['value']for z in i.get(['KOT_PCB_ZONE'])])
items=[]
# TI Fig.3 radiator bounds, extended to the adjacent board edges. Its feed
# and grounded short at x=5.9 are on the ground-plane side, not in this area.
items.append(keepout('TI SWRA117D all-layer radiator exclusion',box(0,11.65,5.65,27),ALL,True,True))
match=Polygon([(2,4.8),(5.7,4.8),(5.7,5.3),(6.35,5.3),(6.35,6.85),(2,6.85)])
items.append(keepout('Nordic ANT/C21/L1 no underlying copper',match,ALL[1:],True,True))
items.append(keepout('C21 ground exclusively through VSS31',match,['BL_F_Cu']))
feed=LineString([(1.58,8.81),(1.58,9.7),(1.58,11.35),(6.9,11.35),(6.9,14.7),(5.9,14.7)])
pre=LineString([(2.69,5.5),(1.58,6.61),(1.58,6.9),(1.58,7.79)])
for k,g in enumerate([feed.buffer(.58,quad_segs=12),pre.buffer(.58,quad_segs=12)]):
 items.append(keepout('Microstrip top-ground gap 0.50mm '+str(k),g,['BL_F_Cu']))
for x,y in [(1.6,1.6),(26.4,1.6),(1.6,25.4),(26.6,22.6)]:
 items.append(keepout('Bottom support clearance '+str((x,y)),Point(x,y).buffer(1.5,quad_segs=48),['BL_B_Cu'],True,True,True))
for layer in ALL:
 items.append({'@type':'type.googleapis.com/kiapi.board.types.Zone','id':uid(),'type':'ZT_COPPER','layers':[layer],'name':'GND '+('dedicated L2 plane'if layer=='BL_In1_Cu'else layer),'outline':poly(box(.3,.3,28.4,26.7)),'copper_settings':{'connection':{'zone_connection':'ZCS_FULL'},'clearance':{'value_nm':'100000'},'min_thickness':{'value_nm':'100000'},'island_mode':'IRM_ALWAYS','fill_mode':'ZFM_SOLID','net':{'name':'GND'}}})
i.create(items);i.end('REV C: enforced antenna/matching exclusions and solid L2 GND');i.call('kiapi.board.commands.RefillZones',{'board':i.doc});i.save();print('Saved enforced RF keepouts and four ground pours')
