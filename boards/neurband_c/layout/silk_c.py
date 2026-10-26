"""Sparse user-facing legends; all assembly information stays on Fab."""
from ipc_c import *
def label(text,x,y,side='F',size=.8,angle=0):
 return {'@type':'type.googleapis.com/kiapi.board.types.BoardText','id':uid(),'layer':'BL_'+side+'_SilkS','text':{'position':xy(x,y),'text':text,'attributes':{'horizontal_alignment':'HA_CENTER','vertical_alignment':'VA_CENTER','angle':{'value_degrees':angle},'line_spacing':1,'stroke_width':{'value_nm':'150000'},'visible':True,'multiline':True,'mirrored':side=='B','size':xy(size,size)}}}
i=IPC();fs=i.get(['KOT_PCB_FOOTPRINT']);i.begin()
for f in fs:
 for name in ['reference_field','value_field','datasheet_field','description_field']:
  if name in f:
   f[name]['visible']=False
   f[name]['text']['text']['attributes']['visible']=False
   f[name]['text']['layer']='BL_B_Fab'if f['layer']=='BL_B_Cu'else'BL_F_Fab'
 for item in f['definition']['items']:
  if item['@type'].endswith('.Field'):
   item['visible']=False;item['text']['text']['attributes']['visible']=False;item['text']['layer']='BL_F_Fab'
 # Library silk is dense at this scale; custom pin-1 and actuator legends below.
 f['definition']['items']=[p for p in f['definition']['items'] if p.get('layer') not in ['BL_F_SilkS','BL_B_SilkS']]
 i.update([f])
i.delete([p['id']['value']for p in i.get(['KOT_PCB_TEXT'])])
i.create([label('neurband',3.0,18.4,size=.8),label('rev C',3.0,19.7,size=.8),label('1',8.3,21.4),label('neurband / C',14,19.8,'B',1.0),label('BAT +',24.5,23.5,'B'),label('5V',14,4,'B'),label('GND',14,11.7,'B')]+[label(t,16+1.27*k,24.3,'B',.8)for k,t in enumerate(['V','D','C','R','G'])])
i.end('REV C: restrained branding and accessible-pad legends');i.save();print('Saved compact legends')
