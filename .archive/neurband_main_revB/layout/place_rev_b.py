"""Build rev B placement on the canonical board after importing the rev B netlist."""
from ipc_rev_b import *
import copy

def ref(f): return f['reference_field']['text']['text']['text']
def shape(kind,data):
    return {'@type':'type.googleapis.com/kiapi.board.types.BoardGraphicShape','id':uid(),'layer':'BL_Edge_Cuts','shape':{'attributes':{'stroke':{'width':{'value_nm':'50000'},'style':'SLS_SOLID'},'fill':{'fill_type':'GFT_UNFILLED'}},kind:data}}
def outline(w=32,h=26,r=1):
    out=[]
    for a,b in [((r,0),(w-r,0)),((w,r),(w,h-r)),((w-r,h),(r,h)),((0,h-r),(0,r))]:out.append(shape('segment',{'start':xy(*a),'end':xy(*b)}))
    d=r*(1-2**-.5)
    for a,m,b in [((0,r),(d,d),(r,0)),((w-r,0),(w-d,d),(w,r)),((w,h-r),(w-d,h-d),(w-r,h)),((r,h),(d,h-d),(0,h-r))]:out.append(shape('arc',{'start':xy(*a),'mid':xy(*m),'end':xy(*b)}))
    return out

P={
'U1':(5.6,13.1,90,'F'), 'U2':(23,13.3,-90,'F'),'U3':(23,13.3,-90,'B'),
'J2':(22,2.1,270,'B'),'J1':(28.8,23.3,90,'F'),
'C1':(14.85,13.05,180,'F'),'C2':(14.85,11.55,180,'F'),'C3':(14.85,14.25,180,'F'),
'C4':(30.7,14.05,0,'F'),'C5':(14.85,17.7,180,'F'),'C6':(14.85,16.1,180,'F'),
'C7':(30.7,10.55,0,'F'),'R1':(30.7,9.35,0,'F'),'R2':(30.7,7.85,0,'F'),
'C14':(14.85,8.1,180,'F'),'C15':(14.85,9.55,180,'F'),'C16':(30.7,15.25,0,'F'),
'C20':(30.7,18,0,'F'),'C21':(30.7,19.2,0,'F'),
'U4':(7,23,0,'F'),'C27':(4.2,23,90,'F'),'C29':(10,23,90,'F'),
'U5':(22.8,22.5,0,'F'),'C28':(19.8,22.5,0,'F'),'C30':(25.1,23.5,90,'F'),
'C24':(2.0,4.5,0,'F'),'R3':(4.0,4.5,0,'F'),'C25':(1.8,21.1,90,'F'),'C26':(3.1,21.1,90,'F'),
'R4':(11.6,21.8,90,'F'),'R5':(13.1,21.8,90,'F'),'R6':(14.6,21.8,90,'F'),
}
# Allow a full 2mm array courtyard between J2 and the lower AFE.
for name in ['U2','C1','C2','C3','C4','C5','C6','C7','R1','R2','C14','C15','C16','C20','C21']:
    x,y,a,s=P[name];P[name]=(x,y+1.0,a,s)
P['U3']=(23,14.3,-90,'B')
# Mirror each slave analog support group about X=23, keeping the input row facing J2.
for old,new in [('C1','C8'),('C2','C9'),('C3','C10'),('C4','C11'),('C5','C12'),('C6','C13'),('C14','C17'),('C15','C18'),('C16','C19'),('C20','C22'),('C21','C23')]:
    x,y,a,_=P[old];P[new]=(min(30.6,46-x),y,180-a,'B')
for k,x in enumerate([20,22,24,26],1):P[f'RN{k}']=(x,5.45 if k%2 else 7.5,90,'F')
for k,x in enumerate([26,24,22,20],5):P[f'RN{k}']=(x,5.45 if k%2 else 7.5,90,'B')
for k in range(1,10):P[f'TP{k}']=(3.0+(k-1)*1.27,24.8,0,'B')
P.update({'J1':(28.6,2.75,90,'F'),'C21':(30.7,20.1,0,'F'),
          'U4':(7.8,23,0,'F'),'C29':(10.8,23,90,'F'),
          'C27':(4.6,23,90,'F'),'U5':(6,21.8,0,'B'),
          'C28':(2.8,21.8,90,'B'),'C30':(9,21.8,0,'B'),
          'C8':(30.6,12.9,0,'B'),'C9':(30.6,11.7,0,'B'),
          'C10':(30.6,14.1,0,'B'),'C12':(30.6,18.15,0,'B'),
          'C13':(30.6,16.1,270,'B'),'C17':(30.6,9.3,0,'B'),
          'C18':(30.6,10.5,0,'B'),'R4':(11.9,21.8,90,'F')})
# Preserve native 0.25mm component courtyards: stagger neighbouring arrays,
# align all output pads exactly with ADC input X coordinates, move both AFEs down.
for name in ['U2','U3','C1','C2','C3','C4','C5','C6','C7','R1','R2',
             'C8','C9','C10','C11','C12','C13','C14','C15','C16','C17','C18','C19','C20','C21','C22','C23']:
    x,y,a,s=P[name];P[name]=(x,y+3.55,a,s)
for name in [f'RN{k}'for k in range(1,9)]:
    x,y,a,s=P[name];P[name]=(x,y+2.7,a,s)
for name in ['R4','R5','R6']:
    x,y,a,s=P[name];P[name]=(x,23.8,a,s)

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--reset',action='store_true');ap.add_argument('--import-netlist',action='store_true');args=ap.parse_args()
    i=IPC()
    if args.import_netlist:
        r=i.call('kiapi.board.commands.ImportNetlist',{'board':i.doc,'netlist_path':str(PCB.with_suffix('.net')),'match_mode':'NMM_REFERENCE','delete_extra_footprints':True,'update_footprints':True,'override_locks':True})
        (PCB.parent/'layout/build/revB-netlist-import.json').write_text(json.dumps(r,indent=2));print('Import',r.get('error_count',0),r.get('warning_count',0));
        if r.get('error_count'):raise RuntimeError(r)
    i.begin()
    if args.reset:
        items=i.get(['KOT_PCB_TRACE','KOT_PCB_VIA','KOT_PCB_ZONE','KOT_PCB_SHAPE','KOT_PCB_TEXT'])
        i.delete([x['id']['value'] for x in items]);i.create(outline())
    fs=i.get(['KOT_PCB_FOOTPRINT']);updates=[]
    # SetLayer alone does not mirror a footprint's pads. Use KiCad's native flip.
    flips=[]
    for f in fs:
        pads=[p for p in f['definition']['items'] if p['@type'].endswith('.Pad') and p.get('type')=='PT_SMD']
        if not pads:continue
        actual='B' if 'BL_B_Cu' in pads[0]['pad_stack']['layers'] else 'F'
        if f['layer']!='BL_'+actual+'_Cu':
            i.update([{'@type':f['@type'],'id':f['id'],'layer':'BL_'+actual+'_Cu'}])
        if actual!=P[ref(f)][3]:flips.append(f['id'])
    if flips:
        i.call('kiapi.board.commands.FlipItems',{'header':{'document':i.doc},'items':flips,'direction':'BFD_LEFT_RIGHT'})
        i.end('Rev B: native side flips')
        i.begin()
    for f in fs:
        name=ref(f)
        if name not in P:raise ValueError(f'Unexpected footprint {name}')
        x,y,a,side=P[name]
        updates.append({'@type':f['@type'],'id':f['id'],'position':xy(x,y),'orientation':{'value_degrees':a},'layer':'BL_'+side+'_Cu','locked':'LS_UNLOCKED'})
    result=i.update(updates)
    bad=[x.get('status') for x in result.get('updated_items',[]) if x.get('status',{}).get('code')!='ISC_OK']
    if bad:raise RuntimeError(bad)
    i.end('Rev B: compact two-sided component placement');i.save()
    fs=i.get(['KOT_PCB_FOOTPRINT']);(PCB.parent/'layout/build/revB-footprints.json').write_text(json.dumps(fs,indent=2))
    (PCB.parent/'layout/placement.json').write_text(json.dumps({r:{'x_mm':p[0],'y_mm':p[1],'rotation_deg':p[2],'side':p[3]} for r,p in P.items()},indent=2)+'\n')
    print('Saved',len(fs),'footprints on 32 x 26 outline')
if __name__=='__main__':main()
