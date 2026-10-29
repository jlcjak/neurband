"""DRC-gated mechanical and visual exports from the canonical REV C board."""
from ipc_c import *
import subprocess,os,re
BUILD=PCB.parent/'layout/build';RENDERS=PCB.parent/'renders';RENDERS.mkdir(exist_ok=True)
env=os.environ.copy();env['KICAD10_3DMODEL_DIR']=str(RUNTIME/'share/kicad/3dmodels')
def run(args,name):
 p=subprocess.run([str(RUNTIME/'bin/kicad-cli')]+args,capture_output=True,text=True,env=env)
 (BUILD/(name+'.log')).write_text(p.stdout+'\n'+p.stderr)
 print(name,'exit',p.returncode,flush=True)
 if p.returncode:raise RuntimeError((name,p.returncode))
run(['pcb','drc','--format','json','--schematic-parity','-o',str(BUILD/'final-drc.json'),str(PCB)],'final-drc')
d=json.loads((BUILD/'final-drc.json').read_text())
errors=[v for v in d['violations']if v['severity']=='error']
parity=[v for v in d.get('schematic_parity',[])if v['type']!='footprint_symbol_mismatch']
if errors or d['unconnected_items'] or parity:raise RuntimeError(('Release blocked',len(errors),len(d['unconnected_items']),parity))
run(['pcb','export','stats','--format','json','-o',str(BUILD/'board-stats.json'),str(PCB)],'stats')
s=json.loads((BUILD/'board-stats.json').read_text());b=s['board']
value=lambda text:float(text.split()[0])
fab={'kind':'pcb','name':'neurband rev C main board','source':PCB.name,'qty':5,'options':{'layers':4,'thickness_mm':value(b['board_thickness']),'color':'black','finish':'enig'},'features':{'width_mm':value(b['width']),'height_mm':value(b['height']),'min_drill_mm':min(value(h['x_size'])for h in s['drill_holes']if h['plated'])}}
(PCB.with_suffix('.fab.json')).write_text(json.dumps(fab,indent=2)+'\n')
for name,side,extra in [('top','top',[]),('bottom','bottom',[]),('3d','top',['--rotate','-35,0,35','--zoom','.72'])]:
 run(['pcb','render','--width','1600','--height','1400','--quality','basic','--background','opaque','--use-board-stackup-colors','--side',side,'-o',str(RENDERS/(name+'.png'))]+extra+[str(PCB)],'render-'+name)
run(['pcb','export','svg','--mode-multi','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu','--common-layers','Edge.Cuts','--page-size-mode','2','--exclude-drawing-sheet','-o',str(RENDERS/'layers'),str(PCB)],'layer-renders')
for svg in (RENDERS/'layers').glob('*.svg'):
 subprocess.run(['/usr/bin/rsvg-convert','-w','1600','-o',str(svg.with_suffix('.png')),str(svg)],check=True)
run(['pcb','export','step','--force','--subst-models','--no-dnp','-o',str(PCB.with_suffix('.step')),str(PCB)],'step-components')
run(['pcb','export','step','--force','--board-only','-o',str(PCB.parent/'neurband_c_board_only.step'),str(PCB)],'step-board-only')
print('Final exports and measured fab metadata complete',fab,flush=True)
