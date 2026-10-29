"""Free the right-hand nRF escape without changing package pin assignment."""
from file_layout_c import *
from native_check_c import check

def main():
 t=load();save(t,BUILD/'before-nrf-escape.kicad_pcb');by={ref(f):f for f in kids(t,'footprint')}
 old=[p for p in pad_data(t)if p['ref']in ['C11','C13']]
 kill=set()
 for c in copper(t):
  g,z=shape(c)
  if net(c)=='/DEC1'or(c[0]=='segment'and net(c)in ['+3V3','GND']and 0 in z and any(p['net']==net(c)and g.distance(p['poly'])<.01 for p in old)):kill.add(item_id(c))
  if net(c)=='+3V3':
   for key in (['at']if c[0]=='via'else['start','end']):
    q=get(c,key)
    if math.dist(tuple(map(float,q[1:3])),(4.8,7.15))<.001:q[1:3]=['5.15','7.275']
 remove_ids(t,kill);move(by['C11'],13,7.2,0);move(by['C13'],12.5,8.6,0)
 ps=pad_data(t);moved=[p for p in ps if p['ref']in ['C11','C13']];kill=set()
 for c in copper(t):
  g,z=shape(c)
  if any(p['net']!=net(c)and set(z)&set(p['layers'])and g.distance(p['poly'])<(.126 if c[0]=='via'else .101)for p in moved):kill.add(item_id(c))
 remove_ids(t,kill);save(t);r=Router(t);p=lambda rr,nn:next(p for p in ps if p['ref']==rr and p['num']==str(nn))['center']
 for n,nn,q in [('/VBAT_SENSE',4,(13.2,6.45)),('/I2C_SDA',5,(12.8,5.9)),('/I2C_SCL',6,(12.8,5.25))]:
  b,v=r.available(n);print('VIA LEGAL',n,v[round(q[1]/.025),round(q[0]/.025)],flush=True)
  ok=r.link(n,p('U1',nn),[0],q,[0],False);print('ESCAPE',n,ok,flush=True)
  if ok:
   c=via(*q,n);t.append(c);g,zs=shape(c)
   for z in zs:r.geometry[n][z].append(g)
   r.vias.append((*q,n));r.refresh(n)
 save(t);r=Router(t,width=.127)
 for n,aa,bb in [('/DEC1',p('U1',1),p('C13',1)),('+3V3',p('C11',1),p('U2',50)),('+3V3',p('C11',1),p('U2',52)),('Net-(U2-RLDINV)',p('U2',61),p('R1',2))]:print('LOCAL',n,aa,bb,r.link(n,aa,[0],bb,[0],False),flush=True)
 save(t);check('nrf-escape')
if __name__=='__main__':main()
