"""Fill ground planes and export native rev B review evidence."""
from ipc_rev_b import *
import subprocess,sys

def ground():
 i=IPC();i.begin();zs=i.get(['KOT_PCB_ZONE']);i.delete([z['id']['value']for z in zs if z.get('type')=='ZT_COPPER'])
 items=[]
 for layer in ['BL_F_Cu','BL_In1_Cu','BL_In2_Cu','BL_B_Cu']:
  items.append({'@type':'type.googleapis.com/kiapi.board.types.Zone','id':uid(),'type':'ZT_COPPER','layers':[layer],'name':'Continuous GND '+layer,'outline':{'polygons':[{'outline':{'closed':True,'nodes':[{'point':xy(x,y)}for x,y in [(.3,.3),(31.7,.3),(31.7,25.7),(.3,25.7)]]}}]},'copper_settings':{'connection':{'zone_connection':'ZCS_FULL'},'clearance':{'value_nm':'100000'},'min_thickness':{'value_nm':'100000'},'island_mode':'IRM_ALWAYS','fill_mode':'ZFM_SOLID','net':{'name':'GND'}}})
 i.create(items);i.end('Rev B: continuous inner ground plane and outer ground pours');i.call('kiapi.board.commands.RefillZones',{'board':i.doc});i.save();print('Filled four GND zones')
def run(args,log):
 p=subprocess.run([str(RUNTIME/'bin/kicad-cli')]+args,capture_output=True,text=True);log.write_text(p.stdout+'\n'+p.stderr);print(' '.join(args[:3]),'exit',p.returncode,flush=True)
 if p.returncode:raise RuntimeError(log)
def export():
 d=PCB.parent/'renders';d.mkdir(exist_ok=True);build=PCB.parent/'layout/build'
 run(['pcb','export','stats','--format','json','-o',str(build/'board-stats.json'),str(PCB)],build/'stats.log')
 for name,side,extra in [('top','top',[]),('bottom','bottom',[]),('3d','top',['--rotate','-35,0,35'])]:
  run(['pcb','render','--width','1600','--height','1200','--quality','basic','--background','opaque','--side',side,'-o',str(d/(name+'.png'))]+extra+[str(PCB)],build/('render-'+name+'.log'))
 run(['pcb','export','png','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu','--common-layers','Edge.Cuts','--dpi','600','-o',str(d/'layers'),str(PCB)],build/'layers.log')
if __name__=='__main__':
 if len(sys.argv)==1 or sys.argv[1]=='ground':ground()
 if len(sys.argv)==1 or sys.argv[1]=='export':export()
