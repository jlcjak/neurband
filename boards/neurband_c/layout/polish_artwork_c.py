"""Move service artwork to clear pads; move the cell envelope to its top face."""
from native_check_c import *
def main():
 t=load();save(t,BUILD/'polish/before-artwork.kicad_pcb');ps=[p['poly']for p in pad_data(t)if 0 in p['layers']];excluded=unary_union(ps).buffer(.2255)
 t[:]=[c for c in t if not(isinstance(c,list)and c[0]=='gr_line'and uq(get(c,'layer')[1])=='B.SilkS'and (float(get(c,'start')[1])in [11,23]or float(get(c,'start')[2])==21.7))]
 for c in kids(t,'gr_text'):
  if uq(c[1])=='CELL':setc(c,'at',20.2,10.1,0);setc(c,'layer','"F.SilkS"');ef=get(c,'effects');ef[:]=[e for e in ef if not(isinstance(e,list)and e[0]=='justify')]
  if uq(c[1])=='DOWN':setc(c,'at',23.8,23.5625,0)
 def line(a,b):t.append(['gr_line',['start',*map(num,a)],['end',*map(num,b)],['stroke',['width','.15'],['type','solid']],['layer','"F.SilkS"'],ident()])
 for a,b in [((10.5,.2),(10.5,21.7)),((10.5,21.7),(22.5,21.7)),((22.5,21.7),(22.5,.2))]:
  g=LineString([a,b]).difference(excluded)
  for part in (g.geoms if hasattr(g,'geoms')else[g]):
   if part.length>=.2:line(*list(part.coords))
 # Replace the old arrow above the crowded array-to-connector channel.
 kill=[]
 for c in kids(t,'gr_line'):
  if uq(get(c,'layer')[1])!='F.SilkS':continue
  pp=[tuple(map(float,get(c,k)[1:3]))for k in ['start','end']]
  if all(21.3<=x<=22.1 and 19.8<=y<=20.8 for x,y in pp):kill.append(c)
 for c in kill:t.remove(c)
 for a,b in [((22.05,22.0),(22.05,22.6)),((21.85,22.4),(22.05,22.6)),((22.05,22.6),(22.25,22.4))]:line(a,b)
 t.append(['gr_circle',['center','8.75','20.35'],['end','8.875','20.35'],['stroke',['width','0'],['type','solid']],['fill','yes'],['layer','"F.SilkS"'],ident()])
 for f in kids(t,'footprint'):
  if ref(f)in ['C22','C23']:
   for p in kids(f,'pad'):
    ls=get(p,'layers');ls[:]=[v for v in ls if v!='"F.Paste"']
 save(t);d=check('polish-artwork');assert not d['unconnected_items']and not any(v['severity']=='error'for v in d['violations'])
 print('CELL FRAGMENTS',sum(1 for c in kids(t,'gr_line')if uq(get(c,'layer')[1])=='F.SilkS'),'ARROW REPLACED',len(kill),flush=True)
if __name__=='__main__':main()
