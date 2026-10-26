"""Route the compact placement with KiCad's native collision-aware router.
Retain proven GND returns, clear experimental signal copper, route critical links first.
"""
from ipc_rev_b import *
import collections,sys,shutil

i=IPC();build=PCB.parent/'layout/build';shutil.copy2(PCB,build/'revB-before-native-routing.kicad_pcb')
fs=i.get(['KOT_PCB_FOOTPRINT']);nets=collections.defaultdict(list)
for f in fs:
 for p in f['definition']['items']:
  if not p['@type'].endswith('.Pad'):continue
  name=p.get('net',{}).get('name','')
  if name and name!='GND' and not name.startswith('unconnected-'):nets[name].append(p)
i.begin()
copper=i.get(['KOT_PCB_TRACE','KOT_PCB_VIA','KOT_PCB_ZONE'])
remove=[]
for c in copper:
 name=c.get('net',{}).get('name','')
 if c.get('type')=='ZT_COPPER':
  remove.append(c['id']['value'])
i.delete(remove)
i.end('Rev B: preserve verified local fanouts and route remaining signals')
i.save()
def rank(n):
 if n=='/SPI_SCLK':return 0
 if n.startswith('/ADC_') or n in ['/SPI_MOSI','/SPI_MISO']:return 1
 if 'VCAP'in n or 'VREFP'in n or 'RLD'in n:return 2
 if n.startswith('Net-(RN'):return 3
 if n.startswith('/E'):return 4
 if n in ['+3V0','+3V3','VBAT']:return 6
 return 5
results=[]
for n,ps in sorted(nets.items(),key=lambda p:(rank(p[0]),p[0])):
 if len(ps)<2:continue
 layers={('BL_B_Cu'if'BL_B_Cu'in p['pad_stack']['layers']else'BL_F_Cu')for p in ps}
 preferred=next(iter(layers))if len(layers)==1 else 'BL_In2_Cu'
 i.begin();r=i.call('kiapi.backplane.SketchRoute',{'board':i.doc,'items':[p['id']for p in ps],'preferred_layer':preferred,'disallow_vias':False,'time_limit_ms':2500});i.end('Rev B native route '+n);i.save()
 results.append({'net':n,'result':r});print(n,{k:v for k,v in r.items()if k!='created_items'},flush=True)
(build/'revB-native-routing.json').write_text(json.dumps(results,indent=2))
