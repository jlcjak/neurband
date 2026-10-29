"""Refill/save and report the canonical board; optionally prune orphan stubs."""
from file_layout_c import *
import os, subprocess, collections
CLI=Path(os.environ.get('KICAD_CLI',str(Path.home()/'.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli')))
def check(name='current'):
    output=BUILD/(name+'-drc.json')
    p=subprocess.run([str(CLI),'pcb','drc','--refill-zones','--save-board','--schematic-parity','--format','json','-o',str(output),str(PCB)],capture_output=True,text=True)
    (BUILD/(name+'-drc.log')).write_text(p.stdout+'\n'+p.stderr)
    assert output.exists(),p.stderr
    d=json.loads(output.read_text())
    print(name,collections.Counter((v['severity'],v['type'])for v in d['violations']),'unconnected',len(d['unconnected_items']),'parity',len(d.get('schematic_parity',[])),flush=True)
    for v in d['violations']:
        if v['severity']=='error':print(v['description'],[(i['description'],i.get('pos'))for i in v['items']],flush=True)
    return d
def prune(name):
    for k in range(60):
        d=check(name);ids={i['uuid']for v in d['violations']if v['type']in ('track_dangling','via_dangling')for i in v['items']}
        if not ids:return d
        t=load();remove_ids(t,ids);save(t)
    raise RuntimeError('Pruning did not converge')
if __name__=='__main__':
    name=sys.argv[1]if len(sys.argv)>1 else'current'
    prune(name)if'--prune'in sys.argv else check(name)
