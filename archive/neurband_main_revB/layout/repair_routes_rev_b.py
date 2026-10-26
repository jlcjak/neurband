"""Use KiCad's native shove router to close residual DRC ratsnest connections."""
from ipc_rev_b import *
import sys

i=IPC()
project=i.doc['project']
classes=i.call('kiapi.common.commands.GetNetClasses',{'project':project})['net_classes']
default=next(c for c in classes if c['name']=='Default')
default['board']['track_width']={'value_nm':'100000'}
default['board']['via_stack']['drill']['diameter']=xy(.2,.2)
default['board']['via_stack']['copper_layers'][0]['size']=xy(.45,.45)
i.call('kiapi.common.commands.SetNetClasses',{'project':project,'net_classes':classes,'merge_mode':'MMM_MERGE'})
if '--move-via' in sys.argv:
 vs=i.get(['KOT_PCB_VIA']);v=next(v for v in vs if v.get('net',{}).get('name')=='/E16N' and int(v['position'].get('x_nm',0))==26500000 and int(v['position'].get('y_nm',0))==1900000)
 v['position']=xy(26.5,1.25);i.begin();i.update([v]);i.end('Clear electrode escape via from battery GND pad');i.save()
path=PCB.parent/'layout/build'/('revB-'+(sys.argv[1] if len(sys.argv)>1 else 'routed2')+'.json')
d=json.loads(path.read_text());results=[]
for k,e in enumerate(d['unconnected_items']):
 pair=e['items'];print(k,[p['description']for p in pair],flush=True)
 for layer in ['BL_In2_Cu','BL_F_Cu','BL_B_Cu']:
  i.begin()
  try:
   r=i.call('kiapi.backplane.SketchRoute',{'board':i.doc,'items':[{'value':p['uuid']}for p in pair],'preferred_layer':layer,'disallow_vias':False,'time_limit_ms':600})
   print(layer,r,flush=True);results.append(r)
   i.end('Rev B native residual routing');i.save()
   if r.get('routed',0)>0:break
  except Exception:
   i.call('kiapi.common.commands.EndCommit',{'header':{'document':i.doc},'id':i.commit,'action':'CMA_DROP'});raise
(PCB.parent/'layout/build/native-route-repair.json').write_text(json.dumps(results,indent=2))
i.call('kiapi.board.commands.RefillZones',{'board':i.doc});i.save()
