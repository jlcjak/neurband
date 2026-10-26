"""Keep compact-board silk legible; references remain on Fab/assembly documentation."""
from ipc_rev_b import *

def label(text,x,y,side='F',size=.8):
 return {'@type':'type.googleapis.com/kiapi.board.types.BoardText','id':uid(),'layer':'BL_'+side+'_SilkS','text':{'position':xy(x,y),'text':text,'attributes':{'horizontal_alignment':'HA_CENTER','vertical_alignment':'VA_CENTER','angle':{'value_degrees':0},'line_spacing':1,'stroke_width':{'value_nm':'150000'},'visible':True,'mirrored':side=='B','size':xy(size,size)}}}
i=IPC();fs=i.get(['KOT_PCB_FOOTPRINT']);i.begin()
for f in fs:
 r=f['reference_field']['text']['text']['text']
 for name in ['reference_field','value_field']:
  if name in f:
   f[name]['text']['text']['attributes']['visible']=False
  if name in f['definition']:
   f['definition'][name]['text']['text']['attributes']['visible']=False
 if r in ['U1','J1','J2'] or r.startswith('TP'):
  f['definition']['items']=[p for p in f['definition']['items']if p.get('layer') not in ['BL_F_SilkS','BL_B_SilkS']]
 if r=='J2':
  # Exact Hirose 0.1mm stencil apertures; keep verified stock copper unchanged.
  f['definition']['items']=[p for p in f['definition']['items']if p.get('layer')!='BL_B_Paste']
  apertures=[]
  for p in f['definition']['items']:
   if not p['@type'].endswith('.Pad'):continue
   p['pad_stack']['layers']=[l for l in p['pad_stack']['layers']if l!='BL_B_Paste']
   x=int(p['position'].get('x_nm',0))*1e-6;y=int(p['position'].get('y_nm',0))*1e-6
   number=p.get('number','')
   if number=='MP':sx,sy=.3,.9
   elif number.isdigit():
    odd=int(number)%2;sx,sy=.23,.65 if odd else .55
    if odd:y+=.025
   else:continue
   apertures.append({'@type':'type.googleapis.com/kiapi.board.types.BoardGraphicShape','id':uid(),'layer':'BL_B_Paste','shape':{'attributes':{'stroke':{'width':{'value_nm':'0'},'style':'SLS_SOLID'},'fill':{'fill_type':'GFT_FILLED'}},'rectangle':{'top_left':xy(x-sx/2,y-sy/2),'bottom_right':xy(x+sx/2,y+sy/2)}}})
  f['definition']['items'].extend(apertures)
 i.update([f])
i.end('Rev B: remove cramped assembly labels and edge-clipped silk')
i.begin();i.create([label('NEURBAND B',6.5,2.1,'F',1.0),label('J1',29,6.4),label('J2',30,2,'B'),label('1',15.4,1.9,'B')]+[label(str(n),6.2+(n-1)*1.27,23.8,'B')for n in range(1,10)]);i.end('Rev B: legible connector and pogo legends');i.save();print('Saved compact silk legends')
