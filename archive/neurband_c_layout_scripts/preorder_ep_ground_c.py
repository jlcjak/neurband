"""Add ordinary-drill RF ground vias and paste windows clear of their lands."""
from native_check_c import *

def main():
 t=load();save(t,BUILD/'before-ep-grid-refresh.kicad_pcb');f=next(f for f in kids(t,'footprint')if ref(f)=='U1');fx,fy,fa=pos(f)
 sites=[(7.125,3.825),(7.175,5.425),(7.125,7.625),(9.675,3.825),(9.675,5.725),(8.275,7.675),(9.975,4.425),(11.025,5.625),(11.0,7.7)]
 ep=next(p for p in pad_data(t)if p['ref']=='U1'and p['num']=='49')['poly'];assert all(ep.covers(Point(q).buffer(.225))for q in sites)
 existing=[c for c in kids(t,'via')if net(c)=='GND'and ep.covers(shape(c)[0])]
 if existing:
  assert len(existing)==9
  used=set()
  for q in sites:
   c=min((c for c in existing if item_id(c)not in used),key=lambda c:math.dist(q,tuple(map(float,get(c,'at')[1:3]))));used.add(item_id(c));setc(c,'at',*q);get(c,'tenting')[:]=['tenting',['front','no'],['back','yes']]
 else:
  for q in sites:
   c=via(*q);get(c,'tenting')[:]=['tenting',['front','no'],['back','yes']];t.append(c)
 # Nine rounded windows, each clipped by a 0.335 mm paste exclusion radius.
 # Tiny disconnected corner flecks are removed from the stencil artwork.
 exclusions=unary_union([Point(q).buffer(.335,quad_segs=12)for q in sites]);apertures=[]
 for x in [7.5,9,10.5]:
  for y in [4.2,5.7,7.2]:
   g=box(x-.55,y-.55,x+.55,y+.55).buffer(.1,quad_segs=8).difference(exclusions)
   for pg in (g.geoms if hasattr(g,'geoms')else[g]):
    if pg.area>.02:assert not pg.interiors;apertures.append(pg)
 def paste_pad(pg,board=True):
  q=pg.representative_point();cx,cy=q.x,q.y;dx,dy=rotate(cx-fx,cy-fy,-fa);pts=[rotate(x-cx,y-cy,-fa)for x,y in list(pg.exterior.coords)[:-1]]
  return ['pad','""','smd','custom',['at',num(dx),num(dy),num(fa if board else 0)],['size','.001','.001'],['layers','"F.Paste"'],['options',['clearance','outline'],['anchor','rect']],['primitives',['gr_poly',['pts',*([ 'xy',num(x),num(y)]for x,y in pts)],['width','0'],['fill','yes']]],ident()]
 def clear_paste(fp):fp[:]=[c for c in fp if not(isinstance(c,list)and c[0]=='pad'and get(c,'layers')==['layers','"F.Paste"'])]
 clear_paste(f);f.extend(paste_pad(g)for g in apertures)
 path=PCB.parent/'layout/neurband.pretty'/('QFN-48-1EP_6x6mm_P0.4mm_EP4.6x4.6mm_FabZero.kicad_mod');local=load(path);clear_paste(local);local.extend(paste_pad(g,False)for g in apertures);save(local,path)
 save(t);min_clear=min(pg.distance(Point(q))-.225 for pg in apertures for q in sites);coverage=sum(g.area for g in apertures)/ep.area;assert .5<=coverage<=.65 and min_clear>=.1
 result=dict(via_centres_mm=sites,drill_mm=.3,land_mm=.45,bottom_tented=True,paste_apertures=len(apertures),paste_coverage_fraction=coverage,minimum_paste_to_via_land_mm=min_clear,ep_via_pad_min_edge_clearance_mm=min(ep.exterior.distance(Point(q))-.225 for q in sites));(BUILD/'ep-grid-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True);d=check('ep-grid');assert not d['unconnected_items']and not any(v['severity']=='error'for v in d['violations'])
if __name__=='__main__':main()
