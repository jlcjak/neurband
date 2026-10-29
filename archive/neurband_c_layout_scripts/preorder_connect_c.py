"""Close remaining native nets with explicit pad escape and analog partition."""
from file_layout_c import *
from native_check_c import check
class ReleaseRouter(Router):
 def available(self,n):
  m=self.masks.get(n,np.zeros_like(self.total));v=self.vmasks.get(n,np.zeros_like(self.vtotal))
  b=np.ascontiguousarray(((self.total-m)>0)|self.edge,dtype=np.uint8)
  # Keep the ordinary 0.20 hole-to-copper rule; permit the fixed package/pogo
  # bottleneck to be measured separately instead of imposing it on own pads.
  padmask=self.raster(unary_union([p['poly'].buffer(.325 if p['net']!=n else .25)for p in self.pads]))
  hard=self.vedge.copy();hard&=~self.raster(unary_union([p['poly']for p in self.pads if p['ref']!='AE1']).buffer(.355))
  hard|=self.raster(unary_union([self.ant,self.match]).buffer(.24));hard|=self.raster(unary_union(self.supports).buffer(.24));hard|=~self.raster(box(1,1,27.7,26).buffer(1).buffer(-.54))
  vs=np.ascontiguousarray(((self.vtotal-v)==0)&~hard&~padmask,dtype=np.uint8)
  if n.startswith(('/I2C_','/SPI_','/IMU_INT','/ADC_','/LED'))or n=='Net-(D1-A)':
   own=unary_union([p['poly']for p in self.pads if p['net']==n]).buffer(.85)
   exempt=self.raster(own)
   g0=self.guard0&~exempt;g12=self.guard12&~exempt
   b[0,g0]=1;b[1:,g12]=1;vs[g0|g12]=0
  if n.startswith(('/SPI_','/ADC_')):b[:,int(16.6/self.step):,int(10.5/self.step):]=1
  if 'VCAP'in n or 'VREFP'in n or n in ('/RLD_DRV','Net-(U2-RLDINV)'):b[1:]=1;vs[:]=0
  return b,vs

def addvia(r,n,q):
 c=via(*q,n);r.t.append(c);g,zs=shape(c)
 for z in zs:r.geometry[n][z].append(g)
 r.vias.append((*q,n));r.refresh(n)
def main():
 t=load();save(t,BUILD/'before-connect.kicad_pcb');ps=pad_data(t);by={ref(f):f for f in kids(t,'footprint')}
 # Remove the previous attempted long SCL escape. Other nets stay in place.
 kill={item_id(c)for c in copper(t)if net(c)in ['/I2C_SCL','/I2C_SDA','/VBAT_SENSE']}
 # Flip the VDD36 capacitor so its supply escapes west, away from the crystal.
 olds=[p for p in ps if p['ref']in ['C11','C18']]
 for c in copper(t):
  g,z=shape(c)
  if c[0]=='segment'and net(c)in ['+3V3','GND']and 0 in z and any(p['net']==net(c)and g.distance(p['poly'])<.01 for p in olds):kill.add(item_id(c))
 remove_ids(t,kill);move(by['C11'],13.075,3.5,90);move(by['C18'],4.1,7.9,0)
 ps=pad_data(t);moved=[p for p in ps if p['ref']in ['C11','C18']];kill=set()
 for c in copper(t):
  g,z=shape(c)
  if any(p['net']!=net(c)and set(z)&set(p['layers'])and g.distance(p['poly'])<(.126 if c[0]=='via'else .101)for p in moved):kill.add(item_id(c))
 remove_ids(t,kill);save(t);r=ReleaseRouter(t);p=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center']
 for n,nn,q in [('/I2C_SCL',6,(12.675,5.7)),('/I2C_SDA',5,(12.675,6.3)),('/VBAT_SENSE',4,(12.675,6.9))]:
  ok=r.link(n,p('U1',nn),[0],q,[0],False);print('ESCAPE',n,ok,flush=True)
  if ok:addvia(r,n,q)
 save(t);r=ReleaseRouter(t,width=.127)
 for nn in [50,52]:print('DVDD',nn,r.link('+3V3',p('C11',1),[0],p('U2',nn),[0],False),flush=True)
 b,v=r.available('+3V3');sites=[(x*.025,y*.025)for y,x in zip(*np.where(v))if 2.4<x*.025<6.5 and 6.8<y*.025<9.3];sites.sort(key=lambda q:math.dist(q,p('C18',1)))
 for q in sites[::3]:
  if r.link('+3V3',p('C18',1),[0],q,[0],False):
   addvia(r,'+3V3',q);print('VDD36',q,r.link('+3V3',q,[1],(6.05,9.3),[1]),flush=True);break
 save(t);d=check('connect-local');r=ReleaseRouter(t)
 r.close(d);save(t);check('connect-all')
if __name__=='__main__':main()
