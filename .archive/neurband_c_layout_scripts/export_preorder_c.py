"""Generate review and assembly outputs from the checked canonical preorder save."""
from native_check_c import *
import csv,re,shutil
ROOT=Path('.');RENDERS=PCB.parent/'layout/renders';MFG=ROOT/'mfg/20261029_preorder';RENDERS.mkdir(exist_ok=True,parents=True)
env=os.environ.copy();env['KICAD10_3DMODEL_DIR']=str(CLI.parent.parent/'share/kicad/3dmodels')
def run(args,name):
 p=subprocess.run([str(CLI),*map(str,args)],capture_output=True,text=True,env=env);(BUILD/(name+'.log')).write_text(p.stdout+'\n'+p.stderr);print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(name)
def references(value):
 out=set()
 for token in value.split(','):
  m=re.fullmatch(r'([A-Z]+)(\d+)-([A-Z]+)(\d+)',token)
  if m:
   assert m[1]==m[3]
   out.update(m[1]+str(i)for i in range(int(m[2]),int(m[4])+1))
  else:out.add(token)
 return out
def main():
 d=check('release-final');other=[v for v in d['violations']if v['type']!='lib_footprint_mismatch'];assert not other and not d['unconnected_items']and not d.get('schematic_parity',[]),('Native release gate',other,d['unconnected_items'])
 sch=PCB.with_suffix('.kicad_sch');fields='Reference,Value,Footprint,MPN,LCSC,QUANTITY'
 run(['sch','erc','--format','json','-o',BUILD/'main-erc.json',sch],'main-erc')
 erc=json.loads((BUILD/'main-erc.json').read_text());assert not any(v['severity']=='error'for s in erc['sheets']for v in s['violations'])
 run(['sch','export','bom','--fields',fields,'--labels',fields,'--group-by','Value,Footprint,MPN,LCSC','--exclude-dnp','-o',PCB.parent/'neurband_c_bom.csv',sch],'release-bom')
 run(['pcb','export','pos','--format','csv','--units','mm','--side','front','--exclude-dnp','-o',BUILD/'positions.csv',PCB],'release-pos')
 bom=list(csv.DictReader((PCB.parent/'neurband_c_bom.csv').open()));posrows=list(csv.DictReader((BUILD/'positions.csv').open()));br={r for row in bom for r in references(row['Reference'])};pr={r['Ref']for r in posrows};assert br==pr,(br-pr,pr-br);assert all(r['MPN']for r in bom)
 (BUILD/'bom-position-check.json').write_text(json.dumps(dict(assembled_parts=len(br),unique_bom_lines=len(bom),all_mpn=True,reference_sets_match=True),indent=2)+'\n')
 run(['pcb','export','stats','--format','json','-o',BUILD/'release-stats.json',PCB],'release-stats');st=json.loads((BUILD/'release-stats.json').read_text());val=lambda s:float(s.split()[0]);board=st['board'];fabpath=PCB.with_suffix('.fab.json');fab=json.loads(fabpath.read_text());fab['features'].update(width_mm=val(board['width']),height_mm=val(board['height']),min_drill_mm=min(val(h['x_size'])for h in st['drill_holes']if h['plated']));fabpath.write_text(json.dumps(fab,indent=2)+'\n')
 for name,path,layers in [('main',PCB,'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts'),('flex',Path('boards/neurband_c_flex/neurband_c_flex.kicad_pcb'),'F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts,User.2')]:
  folder=MFG/name;folder.mkdir(parents=True,exist_ok=True);run(['pcb','export','gerbers','--layers',layers,'--subtract-soldermask','-o',folder/'gerbers',path],name+'-gerbers');run(['pcb','export','drill','--format','excellon','--drill-origin','absolute','--excellon-units','mm','-o',folder/'gerbers',path],name+'-drills')
 shutil.copyfile(BUILD/'positions.csv',MFG/'main/positions.csv');shutil.copyfile(PCB.parent/'neurband_c_bom.csv',MFG/'main/bom.csv')
 for name,side,extra in [('top','top',[]),('bottom','bottom',[]),('3d','top',['--rotate','-35,0,35','--zoom','.72'])]:
  run(['pcb','render','--width','1600','--height','1400','--quality','basic','--background','opaque','--use-board-stackup-colors','--side',side,'-o',RENDERS/(name+'.png'),*extra,PCB],'release-render-'+name)
  legacy=PCB.parent/'renders';legacy.mkdir(exist_ok=True);shutil.copyfile(RENDERS/(name+'.png'),legacy/(name+'.png'))
 for side in ['top','bottom']:shutil.copyfile(RENDERS/(side+'.png'),ROOT/('docs/media/board_'+side+'.png'))
 run(['pcb','export','svg','--mode-multi','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu','--common-layers','Edge.Cuts','--page-size-mode','2','--exclude-drawing-sheet','-o',RENDERS/'layers',PCB],'release-layer-svg')
 for svg in (RENDERS/'layers').glob('*.svg'):subprocess.run(['rsvg-convert','-w','1600','-o',str(svg.with_suffix('.png')),str(svg)],check=True)
 subprocess.run([sys.executable,'tools/copper_layers.py'],check=True,env=env)
 run(['pcb','export','step','--force','--subst-models','--no-dnp','-o',PCB.with_suffix('.step'),PCB],'release-step')
 run(['pcb','export','step','--force','--board-only','-o',PCB.parent/'neurband_c_board_only.step',PCB],'release-board-only-step')
 print('EXPORTS COMPLETE',len(br),'parts',fab['features'],flush=True)
if __name__=='__main__':main()
