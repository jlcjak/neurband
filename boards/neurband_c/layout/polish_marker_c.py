"""Place DOWN using the actual KiCad stroke geometry, clear of pads and SW1 body."""
from polish_preorder_c import *
import xml.etree.ElementTree as ET,re

def glyphs():
 root=ET.parse(POLISH/'silk-svg').getroot();out=[]
 for g in root.iter():
  if any(c.tag.endswith('desc')and c.text=='DOWN'for c in g):
   for p in g:
    xy=[tuple(map(float,p))for p in re.findall(r'[ML]([\d.-]+) ([\d.-]+)',p.attrib.get('d',''))]
    if len(xy)>1:out.append(LineString(xy))
 return unary_union(out).buffer(.075,quad_segs=16)
def main():
 t=load();old=copy.deepcopy(t);g=glyphs();c=next(c for c in kids(t,'gr_text')if uq(c[1])=='DOWN');oldxy=tuple(map(float,get(c,'at')[1:3]));ps=unary_union([p['poly']for p in pad_data(t)if 0 in p['layers']]);options=[]
 for x in np.arange(22.15,22.401,.025):
  for y in np.arange(21.65,21.951,.025):
   gg=affinity.translate(affinity.rotate(g,-90,origin=oldxy),x-oldxy[0],y-oldxy[1]);gap=gg.distance(ps)
   if gap>=.15:options.append((gap,x,y,gg))
 assert options,'No pad-clear marker position'
 gap,x,y,gg=max(options,key=lambda q:q[0]);setc(c,'at',num(x),num(y),90)
 # Move the arrow above the unobstructed right end of the connector.
 for c in kids(t,'gr_line'):
  if uq(get(c,'layer')[1])!='F.SilkS':continue
  a,b=[tuple(map(float,get(c,k)[1:3]))for k in ['start','end']]
  if all(21.8<=xx<=22.3 and 21.99<=yy<=22.61 for xx,yy in [a,b]):
   for k in ['start','end']:
    q=get(c,k);q[1:3]=[num(float(q[1])-1.45),num(float(q[2])-2.0)]
 # Break the cell outline as well as respecting the existing pad cut-outs.
 for c in list(kids(t,'gr_line')):
  if uq(get(c,'layer')[1])!='F.SilkS':continue
  a,b=[tuple(map(float,get(c,k)[1:3]))for k in ['start','end']]
  if not (a[0]==b[0]and a[0]in [10.5,22.5]or a[1]==b[1]==21.7):continue
  line=LineString([a,b]);cut=line.difference(gg.buffer(.225))
  if cut.equals(line):continue
  t.remove(c)
  for q in (cut.geoms if hasattr(cut,'geoms')else[cut]):
   if q.length<.2:continue
   a,b=list(q.coords);t.append(['gr_line',['start',*map(num,a)],['end',*map(num,b)],['stroke',['width','.15'],['type','solid']],['layer','"F.SilkS"'],ident()])
 assert sorted(dump(c)for c in copper(t))==sorted(dump(c)for c in copper(old))
 assert accept(old,t,'polish-marker-final')
 proof=dict(center=[float(x),float(y)],rotation=90,minimum_stroke_to_front_pad_mm=gap,font_size_mm=1,stroke_mm=.15,source='Actual KiCad SVG stroked-text paths, buffered by half the 0.15 mm stroke',copper_unchanged=True)
 (POLISH/'marker-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('MARKER',proof,flush=True)
if __name__=='__main__':main()
