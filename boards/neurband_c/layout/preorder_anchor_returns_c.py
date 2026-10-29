"""Anchor isolated bypass and AFE ground copper with ordinary off-pad vias."""
from preorder_pair_layers_c import *
class GroundRouter(InputRouter):
 def available(self,n):
  b,v=super().available(n)
  if self.vias:v[self.raster(unary_union([Point(x,y).buffer(.56)for x,y,_ in self.vias]))]=0
  return b,v
def main():
 t=load();save(t,BUILD/'before-anchor-returns.kicad_pcb');r=GroundRouter(t,width=.127);r.margin=.001
 for n in list(r.geometry):r.refresh(n)
 ps=pad_data(t)
 for rr,nn in [('C29','2'),('U2','51'),('U2','53'),('U2','57'),('U2','58')]:
  p=next(p for p in ps if p['ref']==rr and p['num']==nn);q=viaescape(r,'GND',p['center'],p['center'],2.2);print('RETURN ANCHOR',rr,nn,q,flush=True)
 save(t);check('anchored-returns')
if __name__=='__main__':main()
