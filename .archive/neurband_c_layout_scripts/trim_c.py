"""Iteratively trim native dead ends, retaining a clean-connectivity checkpoint."""
from ipc_c import *
import subprocess,sys
build=PCB.parent/'layout/build';here=Path(__file__).parent;stem=sys.argv[1]if len(sys.argv)>1 else'release8'
for k in range(64):
 d=json.loads((build/(stem+'.json')).read_text());left=[v for v in d['violations']if v['type']in ['via_dangling','track_dangling']]
 if not left:print('No dangling copper after',k,'passes',flush=True);break
 print('Trim pass',k,'endpoints',len(left),flush=True)
 subprocess.run([sys.executable,str(here/'prune_dangling_c.py'),stem],check=True)
 nxt='trim-'+str(k);subprocess.run([sys.executable,str(here/'check_c.py'),nxt],check=True)
 after=json.loads((build/(nxt+'.json')).read_text())
 if after['unconnected_items']or any(v['severity']=='error'for v in after['violations']):
  i=IPC();i.begin();i.create(json.loads((build/('pruned-'+stem+'.json')).read_text()));i.end('REV C: retain essential copper at trim checkpoint');i.save()
  raise RuntimeError('Native dangling flag included essential partial segment; retained checkpoint')
 stem=nxt
else:raise RuntimeError('Dead-end chain exceeded bounded cleanup passes')
subprocess.run([sys.executable,str(here/'planes_c.py')],check=True)
subprocess.run([sys.executable,str(here/'check_c.py'),'clean'],check=True)
