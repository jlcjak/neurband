"""Import REV C connectivity and place a one-sided four-layer wristband core."""
from ipc_c import *
import xml.etree.ElementTree as ET
import copy
BUILD=PCB.parent/'layout/build'; BUILD.mkdir(exist_ok=True)
W,H=28.7,27
P={
 'AE1':(5.9,14.7,90,'F'), 'U1':(9,5.7,180,'F'), 'U2':(20.2,10.1,90,'F'),
 'J1':(14,21.5925,0,'F'), 'J2':(23.9,25.6,0,'B'), 'J3':(14,6,270,'B'),
 'SW1':(24.8,25.1,0,'F'), 'D1':(2,1.0,0,'F'), 'R8':(5.0,1.0,0,'F'),
 'RN1':(23.9,18.3,270,'F'), 'RN2':(20.1,18.3,270,'F'),
 'RN3':(16.3,18.3,270,'F'), 'RN4':(12.5,17.05,270,'F'),
 'C1':(27.37,11.4,270,'F'), 'C6':(27.37,13.4,270,'F'),
 'C2':(27.37,9.4,270,'F'), 'C5':(26.4,4.4,90,'F'), 'C4':(27.37,7.4,270,'F'),
 'C7':(27.37,15.4,270,'F'), 'C8':(25.8,16,0,'F'), 'C9':(13.09,11.7,270,'F'),
 'C3':(13.09,9.85,270,'F'), 'R1':(12.9,13.55,90,'F'), 'C12':(11.8,13.55,90,'F'), 'R2':(13.0,15.0,0,'F'),
 'C10':(16.45,2.45,90,'F'), 'C11':(18.3,2.45,90,'F'),
 'R5':(21.8,2.2,0,'F'), 'C28':(24.2,2.2,0,'F'), 'C29':(26.1,2.2,0,'F'),
 'C13':(13.09,8.0,270,'F'), 'C15':(9.6,10.25,270,'F'), 'C16':(11.8,10.9,270,'F'),
 'C17':(13.2,1.15,0,'F'), 'C18':(6.9,10.25,270,'F'), 'C14':(3.2,6.9,180,'F'),
 'Y1':(4.35,9.9,90,'F'), 'C19':(2.55,10.2,270,'F'), 'C20':(7.6,12.1,90,'F'),
 'C21':(4.7,5.9,270,'F'), 'L1':(3.2,5.5,0,'F'),
 'C22':(1.1,6.9,180,'F'), 'R3':(1.58,8.3,90,'F'), 'C23':(1.1,9.7,180,'F'),
 'U3':(8.6,18.95,0,'F'), 'C26':(11.5,20.2,0,'F'), 'C27':(11.6,19.1,0,'F'),
 'U4':(8.6,15.2,90,'F'), 'C24':(8.6,12.15,90,'F'), 'C25':(2.3,2.8,0,'F'), 'R4':(10.85,14.2,90,'F'),
 'R6':(21.6,.8,0,'F'), 'R7':(23.8,.8,0,'F'), 'C30':(26.0,.8,0,'F'),
 'U5':(24.5,21.6,0,'F'), 'C31':(27.35,21.6,90,'F'),
 'R9':(16.5,.8,0,'F'), 'R10':(18.8,.8,0,'F'), 'R11':(25.0,3.62,270,'F'),
 'R12':(10.6,10.3,90,'F'), 'R13':(9.6,12.2,90,'F'), 'C32':(10.6,12.3,270,'F'),
}
for k in range(1,6): P[f'TP{k}']=(16+(k-1)*1.27,25.7,0,'B')
def shape(kind,data):
 return {'@type':'type.googleapis.com/kiapi.board.types.BoardGraphicShape','id':uid(),'layer':'BL_Edge_Cuts','shape':{'attributes':{'stroke':{'width':{'value_nm':'50000'},'style':'SLS_SOLID'},'fill':{'fill_type':'GFT_UNFILLED'}},kind:data}}
def outline(w=W,h=H,r=1):
 out=[]
 for a,b in [((r,0),(w-r,0)),((w,r),(w,h-r)),((w-r,h),(r,h)),((0,h-r),(0,r))]:out.append(shape('segment',{'start':xy(*a),'end':xy(*b)}))
 d=r*(1-2**-.5)
 for a,m,b in [((0,r),(d,d),(r,0)),((w-r,0),(w-d,d),(w,r)),((w,h-r),(w-d,h-d),(w-r,h)),((r,h),(d,h-d),(0,h-r))]:out.append(shape('arc',{'start':xy(*a),'mid':xy(*m),'end':xy(*b)}))
 return out

def setup(i):
 s=i.call('kiapi.board.commands.GetBoardStackup',{'board':i.doc})['stackup']
 # 1.000mm finished stack: 4x35um Cu + .10/.64/.10mm dielectric
 # and two10um mask layers. The RF reference spacing stays100um.
 ds=iter([.10,.64,.10])
 for l in s['layers']:
  if l['type']=='BSLT_DIELECTRIC':
   t=next(ds); l['thickness']={'value_nm':str(nm(t))}
   l['dielectric']['layer'][0].update(thickness={'value_nm':str(nm(t))},epsilon_r=4.3,material_name='FR4')
  if l['type']=='BSLT_SOLDERMASK':l['color']={'r':.025,'g':.025,'b':.025,'a':1}
 s['finish']={'type_name':'ENIG'}
 (BUILD/'intended-stackup.json').write_text(json.dumps(s,indent=2))
 # bp.4 advertises the message but has no stackup update handler. Apply the
 # intended native stackup while the document is closed, after placement.
 rules=i.call('kiapi.board.commands.GetBoardDesignRules',{'board':i.doc})['rules']
 rules['constraints']['min_through_drill']={'value_nm':'300000'}
 rules['constraints']['min_via_size']={'value_nm':'450000'}
 i.call('kiapi.board.commands.SetBoardDesignRules',{'board':i.doc,'rules':rules})
 nc=i.call('kiapi.common.commands.GetNetClasses',{'project':i.doc['project']})['net_classes']
 nc[0]['board'].update(track_width={'value_nm':'127000'},clearance={'value_nm':'100000'})
 nc[0]['board']['via_stack']['drill']['diameter']=xy(.3,.3)
 nc[0]['board']['via_stack']['copper_layers'][0]['size']=xy(.45,.45)
 i.call('kiapi.common.commands.SetNetClasses',{'project':i.doc['project'],'net_classes':nc})

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--import-netlist',action='store_true');ap.add_argument('--setup',action='store_true');ap.add_argument('--outline',action='store_true');args=ap.parse_args();i=IPC()
 if args.import_netlist:
  tree=ET.parse(BUILD/'source.xml')
  swaps={'J1':'neurband:XUNPU_FPC-05F-20PH20','J2':'neurband:WirePads_2x1.5x2mm_P3mm','J3':'neurband:WirePads_2x1.5x2mm_P3mm'}
  swaps.update({f'TP{k}':'neurband:SWD_Pad_1x1_P1.27' for k in range(1,6)})
  data=PCB.with_suffix('.net').read_text()
  replacements={c.find('footprint').text:swaps[c.attrib['ref']] for c in tree.findall('.//components/comp') if c.attrib['ref'] in swaps}
  for old,new in replacements.items():
   assert '(footprint \"'+old+'\")' in data
   data=data.replace('(footprint \"'+old+'\")','(footprint \"'+new+'\")')
  temp=BUILD/'layout-footprint-swaps.net';temp.write_text(data)
  r=i.call('kiapi.board.commands.ImportNetlist',{'board':i.doc,'netlist_path':str(temp),'match_mode':'NMM_REFERENCE','update_footprints':True,'override_locks':True})
  (BUILD/'import.json').write_text(json.dumps(r,indent=2)); print('Import errors',r.get('error_count',0));assert not r.get('error_count'),r
 if args.setup:setup(i)
 fs=i.get(['KOT_PCB_FOOTPRINT']);assert set(P)=={ref(f)for f in fs},set(P)^{ref(f)for f in fs}
 flips=[]
 for f in fs:
  pads=[p for p in f['definition']['items'] if p['@type'].endswith('.Pad') and p.get('type')=='PT_SMD']
  if pads and ('B'if'BL_B_Cu'in pads[0]['pad_stack']['layers']else'F')!=P[ref(f)][3]:flips.append(f['id'])
 if flips:
  i.begin();i.call('kiapi.board.commands.FlipItems',{'header':{'document':i.doc},'items':flips,'direction':'BFD_LEFT_RIGHT'});i.end('REV C: bottom test and wire pads')
 i.begin()
 if args.outline:
  i.delete([x['id']['value']for x in i.get(['KOT_PCB_SHAPE'])]);i.create(outline())
 updates=[]
 for f in fs:
  x,y,a,side=P[ref(f)];updates.append({'@type':f['@type'],'id':f['id'],'position':xy(x,y),'orientation':{'value_degrees':a},'layer':'BL_'+side+'_Cu'})
 i.update(updates);i.end('REV C: compact top-side placement');i.save()
 fs=i.get(['KOT_PCB_FOOTPRINT']);(BUILD/'placed-footprints.json').write_text(json.dumps(fs));(PCB.parent/'layout/placement.json').write_text(json.dumps(P,indent=2))
 print('Saved',len(fs),'footprints;',W,'x',H,'mm')
if __name__=='__main__': main()
