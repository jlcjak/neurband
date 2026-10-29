"""Give nRF VDD36 a pin-facing bypass and its own ground anchor."""
from polish_preorder_c import *
from preorder_pair_layers_c import InputRouter

def main():
 original=load();save(original,POLISH/'before-c18.kicad_pcb');result=[]
 for x,y in [(4.1,7.9),(4.2,8.1)]:
  t=copy.deepcopy(original);ps=[p for p in pad_data(t)if p['ref']=='C18'];kill={item_id(c)for c in kids(t,'segment')if uq(get(c,'layer')[1])=='F.Cu'and any(p['net']==net(c)and shape(c)[0].distance(p['poly'])<.105 for p in ps)};remove_ids(t,kill)
  f=next(f for f in kids(t,'footprint')if ref(f)=='C18');move(f,x,y,180);new={p['num']:p for p in pad_data(t)if p['ref']=='C18'};q=(round(x-1.125,3),y);t.append(via(*q));wire(t,'GND',[new['2']['center'],q],'F.Cu',.2)
  r=InputRouter(t,width=.127);r.margin=.001
  for n in list(r.geometry):r.refresh(n)
  count=len(kids(t,'segment'));ok=r.link('+3V3',new['1']['center'],[0],(6.05,7.9),[0],False)
  added=kids(t,'segment')[count:];length=sum(LineString([tuple(map(float,get(c,k)[1:3]))for k in ['start','end']]).length for c in added)
  print('C18 TRIAL',x,y,ok,'SUPPLY LINK',length,flush=True)
  if not ok or length>4:continue
  if accept(original,t,'polish-c18'):
   result=dict(center=[x,y],rotation=180,supply_link_length_mm=length,ground_via=list(q),ground_pad_to_via_mm=math.dist(new['2']['center'],q),success=True);break
 else:result=dict(success=False,reason='Neither pin-facing placement achieved a clearance-clean short F.Cu link');save(original)
 (POLISH/'c18-result.json').write_text(json.dumps(result,indent=2)+'\n');print('C18 RESULT',result,flush=True);check('polish-c18-final')
if __name__=='__main__':main()
