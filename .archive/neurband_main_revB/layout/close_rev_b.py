"""Close residual native ratsnest pairs on a 25um grid, preserving proven copper.
Every new batch is checked by native DRC and rejected if it adds any errors.
"""
from route_rev_b import *
import subprocess,sys

def load_router():
 r=Router();i=r.ipc;existing=i.get(['KOT_PCB_TRACE','KOT_PCB_VIA']);lookup={}
 for p in r.pads:lookup[p['id']['value']]=p
 for c in existing:
  net=c.get('net',{}).get('name') or '__none_'+c['id']['value']
  if c['@type'].endswith('.Via'):
   a=coord(c['position']);diam=int(c['pad_stack']['copper_layers'][0]['size']['x_nm'])*1e-6
   g=Point(*a).buffer(diam/2,quad_segs=16)
   for z in range(3):r.geometry[net][z].append(g)
   r.vias.append((*a,net));lookup[c['id']['value']]={'center':a,'layers':[0,1,2],'net':net}
  else:
   a,b=coord(c['start']),coord(c['end']);z=LAYERS.index(c['layer']) if c['layer']in LAYERS else None
   if z is None:continue
   width=int(c['width']['value_nm'])*1e-6;r.geometry[net][z].append(LineString([a,b]).buffer(width/2,quad_segs=8))
   lookup[c['id']['value']]={'center':a,'ends':[a,b,((a[0]+b[0])/2,(a[1]+b[1])/2)],'layers':[z],'net':net}
 for net in r.geometry:r.refresh(net)
 paste=r.raster(unary_union([p['poly']for p in r.pads]).buffer(DRILL/2+.04))
 original_available=r.available
 def available(net):
  b,v=original_available(net);v[paste]=0
  for x,y,n in r.vias:
   if n==net:v[round(y/STEP),round(x/STEP)]=1
  return b,v
 r.available=available
 return r,lookup

def save_checked(r):
 i=r.ipc;new=r.items;i.begin()
 for k in range(0,len(new),200):i.create(new[k:k+200])
 i.end('Rev B: residual connections with exact obstacle masks');i.call('kiapi.board.commands.RefillZones',{'board':i.doc});i.save()
 out=PCB.parent/'layout/build/revB-incremental.json'
 subprocess.run([str(RUNTIME/'bin/kicad-cli'),'pcb','drc','--format','json','--schematic-parity','-o',str(out),str(PCB)],capture_output=True,text=True,check=True)
 report=json.loads(out.read_text());errors=[e for e in report['violations']if e['severity']=='error']
 if errors:
  i.begin();i.delete([x['id']['value']for x in new]);i.end('Reject residual router batch with native DRC errors');i.call('kiapi.board.commands.RefillZones',{'board':i.doc});i.save()
  raise RuntimeError(('Rejected unsafe router batch',errors))
 (PCB.parent/'layout/build/revB-incremental-copper.json').write_text(json.dumps(new))
 print('Native DRC: zero errors;',len(report['unconnected_items']),'unconnected; added',len(new),'items; failed',r.failed,flush=True)

def main():
 r,lookup=load_router()
 name=sys.argv[1]if len(sys.argv)>1 else 'aligned-routed'
 d=json.loads((PCB.parent/'layout/build'/('revB-'+name+'.json')).read_text())
 for row in d['unconnected_items']:
  a,b=[lookup[q['uuid']]for q in row['items']];net=a['net'];assert net==b['net']
  starts=[index(*p,z)for p in a.get('ends',[a['center']])for z in a['layers']]
  goals=[index(*p,z)for p in b.get('ends',[b['center']])for z in b['layers']]
  path=r.search(net,starts,goals,via=False)
  if path is None:path=r.search(net,starts,goals)
  if path is None:r.failed.append(net);print('FAILED',net,[q['description']for q in row['items']],flush=True);continue
  start=min(a.get('ends',[a['center']]),key=lambda p:math.dist(p,position(path[0])[:2]));end=min(b.get('ends',[b['center']]),key=lambda p:math.dist(p,position(path[-1])[:2]))
  r.commit_path(net,path,start,end);print('Closed',net,'steps',len(path),flush=True)
 save_checked(r)
if __name__=='__main__':main()
