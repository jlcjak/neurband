"""Find an off-mask return-safe escape for the analog RC bypass."""
from preorder_pair_layers_c import *
def main():
 t=load(BUILD/'before-return-repair.kicad_pcb');remove_ids(t,{item_id(c)for c in kids(t,'via')if math.dist(tuple(map(float,get(c,'at')[1:3])),(9,9.375))<.001});r=InputRouter(t);r.margin=.001
 for n in list(r.geometry):r.refresh(n)
 p=next(p for p in pad_data(t)if p['ref']=='C29'and p['num']=='1');q=viaescape(r,'+3V3A',p['center'],p['center'],3.0);print('C29 ESCAPE',q,flush=True)
 save(t);d=check('c29-escape');close_components(t,d);check('c29-closed')
if __name__=='__main__':main()
