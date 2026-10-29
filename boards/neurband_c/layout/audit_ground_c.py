"""Fast filled-copper reference and via-distance audit from the saved native board."""
from file_layout_c import *
sys.path.insert(0,'sim/preorder')
from pcbgeom import Board
from coupling import gnd_fill
from shapely import voronoi_polygons,get_coordinates
from shapely.geometry import MultiPoint
from scipy.spatial import cKDTree

def main():
 b=Board(str(PCB));fills=gnd_fill(b);gv=np.array([(v['x'],v['y'])for v in b.vias if v['net']=='GND']);ties=np.vstack([gv,np.array([(p['x'],p['y'])for p in b.pads if p['net']=='GND'and p['type']=='thru_hole']).reshape(-1,2)])
 xx,yy=np.meshgrid(np.arange(.5,28.25,.1),np.arange(.5,26.55,.1));pts=np.c_[xx.ravel(),yy.ravel()];area=unary_union(list(fills.values()));pts=pts[contains_xy(area,pts[:,0],pts[:,1])];ds=np.min(np.sum((pts[:,None,:]-gv[None,:,:])**2,axis=2),axis=1);i=np.argmax(ds);out={'ground_vias':len(gv),'max_pour_distance_mm':float(ds[i]**.5),'max_pour_point':pts[i].tolist(),'fragments':{},'inner_input_reference_gaps':{},'front_input_reference_gaps':{}}
 cells=voronoi_polygons(MultiPoint(gv),extend_to=box(-1,-1,30,29));vertices=np.vstack([get_coordinates(c.intersection(area))for c in cells.geoms]);dist,nearest=cKDTree(gv).query(vertices);j=int(np.argmax(dist))
 out['max_pour_distance_voronoi_mm']=float(dist[j]);out['max_pour_point_voronoi_mm']=vertices[j].tolist();out['nearest_via_voronoi_mm']=gv[nearest[j]].tolist()
 for ly,gg in fills.items():
  rows=[]
  for pg in (gg.geoms if hasattr(gg,'geoms')else[gg]):
   if pg.geom_type!='Polygon'or pg.area<.005:continue
   ti=ties[contains_xy(pg.buffer(.01),ties[:,0],ties[:,1])];lo,bo,hi,to=pg.bounds;x,y=np.meshgrid(np.arange(lo,hi,.15),np.arange(bo,to,.15));pp=np.c_[x.ravel(),y.ravel()];pp=pp[contains_xy(pg,pp[:,0],pp[:,1])]
   far=None
   if len(ti)and len(pp):far=float(np.max(np.min(np.sum((pp[:,None,:]-ti[None,:,:])**2,axis=2),axis=1))**.5)
   rows.append(dict(area_mm2=pg.area,ties=len(ti),max_distance_mm=far,bounds=list(pg.bounds),point=list(pg.representative_point().coords[0])))
  out['fragments'][ly]=sorted(rows,key=lambda r:-r['area_mm2'])
 for tr in b.tracks:
  n=tr['net']
  if not(n.startswith('/E')or n.startswith('Net-(RN')):continue
  ly=tr['layer'];refly='B.Cu'if ly=='In2.Cu'else'In1.Cu'if ly=='F.Cu'else None
  if refly:
   line=LineString([(tr['x1'],tr['y1']),(tr['x2'],tr['y2'])]);missing=line.difference(fills[refly]).length
   key='inner_input_reference_gaps'if ly=='In2.Cu'else'front_input_reference_gaps';out[key][n]=out[key].get(n,0)+missing
 out['inner_input_reference_gaps']={k:v for k,v in out['inner_input_reference_gaps'].items()if v>.001};out['front_input_reference_gaps']={k:v for k,v in out['front_input_reference_gaps'].items()if v>.001}
 (BUILD/'ground-audit.json').write_text(json.dumps(out,indent=2)+'\n');print('GND VIAS',len(gv),'MAX',out['max_pour_distance_mm'],out['max_pour_point'],flush=True)
 for ly,rows in out['fragments'].items():
  print('FRAG',ly,[(round(r['area_mm2'],3),r['ties'],None if r['max_distance_mm']is None else round(r['max_distance_mm'],2),r['point'])for r in rows if r['ties']<2 or(r['max_distance_mm']or 0)>3],flush=True)
 print('INPUT REFERENCE GAPS',out['inner_input_reference_gaps'],flush=True)
if __name__=='__main__':main()
