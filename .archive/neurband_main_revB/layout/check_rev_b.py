"""Run selected KiCad DRC and print a concise actionable report."""
from pathlib import Path
import subprocess,json,collections,sys
from ipc_rev_b import PCB,RUNTIME
out=PCB.parent/'layout/build'/('revB-'+(sys.argv[1] if len(sys.argv)>1 else 'drc')+'.json')
p=subprocess.run([str(RUNTIME/'bin/kicad-cli'),'pcb','drc','--format','json','--schematic-parity','-o',str(out),str(PCB)],capture_output=True,text=True)
print(p.stdout);d=json.loads(out.read_text());print(collections.Counter((x['type'],x['severity'])for x in d['violations']))
print('Unconnected',len(d.get('unconnected_items',[])),'parity',len(d.get('schematic_parity',[])))
for x in d['violations']:
 if x['severity']=='error':print(x['type'],x['description'],[(y['description'],y['pos'])for y in x['items']])
