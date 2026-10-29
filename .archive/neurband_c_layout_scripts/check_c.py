"""Run selected native DRC and print actionable geometry/connectivity findings."""
from ipc_c import *
import subprocess,sys,collections
name=sys.argv[1] if len(sys.argv)>1 else 'drc'
out=PCB.parent/'layout/build'/f'{name}.json'
p=subprocess.run([str(RUNTIME/'bin/kicad-cli'),'pcb','drc','--format','json','--schematic-parity','-o',str(out),str(PCB)],capture_output=True,text=True)
out.with_suffix('.log').write_text(p.stdout+'\n'+p.stderr)
if p.returncode:raise RuntimeError((p.returncode,str(out.with_suffix('.log'))))
d=json.loads(out.read_text());print('Violations',dict(collections.Counter((x['severity'],x['type'])for x in d['violations'])),'unconnected',len(d['unconnected_items']),'parity',len(d.get('schematic_parity',[])))
for v in d['violations']:
 if v['severity']=='error':print(v['type'],v['description'],[(x.get('description'),x.get('pos'))for x in v['items']])
