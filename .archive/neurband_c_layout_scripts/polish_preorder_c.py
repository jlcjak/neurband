"""Final local preorder polish; ordinary drills and frozen interfaces remain fixed."""
from native_check_c import *
from shapely.ops import nearest_points
POLISH=BUILD/'polish';POLISH.mkdir(exist_ok=True)
def translate_via(t,vid,q):
 c=next(c for c in kids(t,'via')if item_id(c)==vid);p=tuple(map(float,get(c,'at')[1:3]));n=net(c);oldps=pad_data(t);layers=set()
 for tr in kids(t,'segment'):
  if net(tr)!=n:continue
  ly=uq(get(tr,'layer')[1]);line=LineString([tuple(map(float,get(tr,k)[1:3]))for k in ['start','end']]);ends=[]
  for k in ['start','end']:
   a=get(tr,k)
   if math.dist(tuple(map(float,a[1:3])),p)<.001:a[1:3]=list(map(num,q));ends.append(k)
  if ends:layers.add(ly)
  elif line.distance(Point(p))<.22501:
   near=nearest_points(line,Point(p))[0];wire(t,n,[tuple(near.coords[0]),q],ly,.1);layers.add(ly)
 for pd in oldps:
  if pd['net']==n and pd['poly'].distance(Point(p))<.22501:
   for z in pd['layers']:
    if LAYERS[z]not in layers and pd['poly'].distance(Point(q))>.225:wire(t,n,[pd['center'],q],LAYERS[z],.1)
 setc(c,'at',*map(num,q))
def move_passive(t,r,x,y,a=None):
 f=next(f for f in kids(t,'footprint')if ref(f)==r);oldps=[p for p in pad_data(t)if p['ref']==r];old=pos(f);move(f,x,y,a);newps={p['num']:p for p in pad_data(t)if p['ref']==r}
 for tr in kids(t,'segment'):
  for k in ['start','end']:
   at=get(tr,k);q=Point(*map(float,at[1:3]));ly=uq(get(tr,'layer')[1])
   p=next((p for p in oldps if p['net']==net(tr)and LAYERS.index(ly)in p['layers']and p['poly'].covers(q)),None)
   if p:
    nn=newps[p['num']];at[1:3]=[num(float(at[1])+nn['center'][0]-p['center'][0]),num(float(at[2])+nn['center'][1]-p['center'][1])]
def accept(old,t,name):
 # Delete collapsed zero-length pieces left by the edge retreat.
 remove_ids(t,{item_id(c)for c in kids(t,'segment')if get(c,'start')[1:]==get(c,'end')[1:]});save(t);d=check(name);ok=not d['unconnected_items']and not any(v['severity']=='error'for v in d['violations'])
 if not ok:save(old);check(name+'-retained')
 return ok

def core():
 old=load();t=copy.deepcopy(old)
 translate_via(t,'13954416-5887-474e-9d7a-823946ec70da',(25.675,19.8));translate_via(t,'66aabfa7-b441-44d4-bd5f-fcf855ecd937',(23.45,19.9))
 assert accept(old,t,'polish-imu-vias'),'IMU via move rejected'
 old=load();t=copy.deepcopy(old);move_passive(t,'C29',14.875,1.175);move_passive(t,'C6',27.625,11.95)
 for c in kids(t,'segment'):
  if net(c)=='+3V3A':
   for k in ['start','end']:
    at=get(c,k)
    if float(at[1])>28.25:at[1]=num(28.25)
   if any(float(get(c,k)[1])>=28.25 for k in ['start','end']):setc(c,'width',num(.1))
 translate_via(t,'773c839d-d9fd-465c-a40e-766a0e087d99',(25.1,26.35))
 assert accept(old,t,'polish-edge'),'Edge retreat rejected'

def pad_vias():
 result=[]
 # These ten existing barrels were identified independently in the manufacturing review.
 sites=[(22.7,3.575),(24.675,4.875),(11.95,15.55),(10.85,16.15),(10.85,17.95),(12.1,17.35),(14.15,17.95),(15.9,18.0),(14.65,17.4),(8.8,2.15)]
 for xy in sites:
  old=load();vv=next(c for c in kids(old,'via')if math.dist(tuple(map(float,get(c,'at')[1:3])),xy)<.001);n=net(vv);vid=item_id(vv);ps=[p for p in pad_data(old)if p['layers']and p['node'][2]=='smd'];other=unary_union([shape(c)[0]for c in copper(old)if net(c)!=n]+[p['poly']for p in ps if p['net']!=n]);own=unary_union([p['poly']for p in ps if p['net']==n]);av=[Point(*map(float,get(c,'at')[1:3]))for c in kids(old,'via')if item_id(c)!=vid];cands=[]
  for ix in range(-12,13):
   for iy in range(-12,13):
    q=(round(xy[0]+ix*.025,5),round(xy[1]+iy*.025,5));p=Point(q)
    if math.dist(q,xy)>.3 or p.distance(other)<.3501 or p.distance(own)<.255 or min(p.distance(g)for g in av)<.5501:continue
    cands.append(q)
  cands.sort(key=lambda q:math.dist(q,xy));ok=False
  for q in cands[:5]:
   t=copy.deepcopy(old);translate_via(t,vid,q)
   if accept(old,t,'polish-pad-via'):
    result.append(dict(net=n,old=list(xy),new=list(q),success=True));ok=True;break
  if not ok:result.append(dict(net=n,old=list(xy),success=False))
  print('PAD POLISH',result[-1],flush=True)
 (POLISH/'pad-via-moves.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 core();pad_vias();check('polish-core-final')
