"""Open a local routing corridor, then repair the displaced conductor."""
from gateway_components_c import *
def main():
 t=load();save(t,BUILD/'before-corridor.kicad_pcb');n='/ADC_START';r=ReleaseRouter(t);mask,v=r.available(n);ids,groups=connected(t,n);gs=list(groups.values());f=ctypes.CDLL(str(BUILD/'flood3.so'));f.flood3.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p];seen=[];ps=[]
 for grp in gs:
  ss=list({r.idx(p,z)for _,g,zs,pts in grp for p in pts for z in zs if not mask[z,round(p[1]/.025),round(p[0]/.025)]});ps.append(ss);arr=np.array(ss,np.int32);o=np.zeros_like(mask);f.flood3(mask.ctypes.data,v.ctypes.data,r.W,r.H,arr.ctypes.data,len(arr),o.ctypes.data);seen.append(o)
 allowed={'+3V3','+3V3A','VBAT','/ADC_CS','/ADC_PWDN','/ADC_DRDY','/SPI_MISO','/SPI_MOSI','/SPI_SCK','/I2C_SDA','/I2C_SCL','/SWDCLK','/SWDIO','/NRST','/BUTTON'}
 candidates=[]
 for c in copper(t):
  if net(c)not in allowed or c[0]!='segment':continue
  a,b=[tuple(map(float,get(c,k)[1:3]))for k in ['start','end']];z=LAYERS.index(uq(get(c,'layer')[1]));L=math.dist(a,b)
  for q in np.linspace(0,1,max(2,math.ceil(L/.25)+1)):
   x,y=a[0]+(b[0]-a[0])*q,a[1]+(b[1]-a[1])*q;ix,iy=round(x/.025),round(y/.025);sl=(slice(max(0,iy-20),min(r.H,iy+21)),slice(max(0,ix-20),min(r.W,ix+21)))
   if seen[0][z][sl].any()and seen[1][z][sl].any():candidates.append((1 if net(c)in ['+3V3','+3V3A']else 2,net(c),(x,y)))
 candidates.sort();print('CORRIDOR CANDIDATES',len(candidates),candidates[:8],flush=True)
 tried=[]
 for _,nn,q in candidates:
  if any(nn==n0 and math.dist(q,q0)<.65 for n0,q0 in tried):continue
  tried.append((nn,q));trial=copy.deepcopy(t);disk=Point(q).buffer(.7);kill=set();tails=[]
  for c in copper(trial):
   if net(c)!=nn:continue
   if c[0]=='via':
    if Point(tuple(map(float,get(c,'at')[1:3]))).distance(Point(q))<.7:kill.add(item_id(c))
    continue
   a,b=[tuple(map(float,get(c,k)[1:3]))for k in ['start','end']];line=LineString([a,b])
   if not line.intersects(disk):continue
   kill.add(item_id(c));parts=line.difference(disk)
   for pp in (parts.geoms if hasattr(parts,'geoms')else[parts]):
    if pp.geom_type=='LineString'and pp.length>.01:tails.append(track(pp.coords[0],pp.coords[-1],nn,uq(get(c,'layer')[1]),float(get(c,'width')[1])))
  remove_ids(trial,kill);trial.extend(tails);rr=ReleaseRouter(trial)
  if pathadd(rr,n,ps[0],ps[1]):
   print('OPENED',nn,q,'removed',len(kill),flush=True);t=trial;save(t);break
 else:raise RuntimeError('No corridor found')
 gateway(t,'/E3P');d=check('corridor');close_components(t,d);check('corridor-closed')
if __name__=='__main__':main()
