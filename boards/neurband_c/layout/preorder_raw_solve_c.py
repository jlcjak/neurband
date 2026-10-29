"""Bounded routing-order search within the manually assigned input corridors.

Candidate trials stay in memory. Only an improved, connected milestone is
saved to the canonical board; the native CLI validates the resulting copper.
"""
from preorder_raw_c import *
import random, gc, itertools

def main():
    rng=random.Random(20261029);base=load(BUILD/'raw-prepared.kicad_pcb')
    ends=json.loads((BUILD/'raw-endpoints.json').read_text());records=[]
    for bank in ((5,6,7,8),(1,2,3,4)):
        best=-1;besttree=None;bestrow=None
        nets=[f'/E{ch}{pol}'for ch in bank for pol in ('P','N')]
        orders=[]
        # Both polarities and both bank directions before seeded permutations.
        for chs in (bank,tuple(reversed(bank))):
            for pols in (('P','N'),('N','P')):orders.append([f'/E{ch}{pol}'for ch in chs for pol in pols])
        for k in range(80):
            if k<len(orders):order=orders[k]
            elif k%2:
                chs=list(bank);rng.shuffle(chs)
                order=[]
                for ch in chs:
                    pols=['P','N'];rng.shuffle(pols);order.extend(f'/E{ch}{pol}'for pol in pols)
            else:order=nets[:];rng.shuffle(order)
            t=copy.deepcopy(base);r=RawRouter(t);ok=[]
            z=1 if bank[0]==1 else 2
            for n in order:
                a,b=ends[n]
                if r.link(n,tuple(a),[z],tuple(b),[z]):ok.append(n)
            row={'bank':list(bank),'attempt':k,'order':order,'connected':ok,'failed':sorted(set(nets)-set(ok))}
            print('BANK',bank,'attempt',k,'connected',len(ok),'failed',row['failed'],flush=True)
            if len(ok)>best:
                best=len(ok);besttree=t;bestrow=row
                save(t);save(t,BUILD/('raw-best-'+str(bank[0])+'.kicad_pcb'))
                (BUILD/'raw-search-current.json').write_text(json.dumps(row,indent=2)+'\n')
            del r;gc.collect()
            if best==len(nets):break
        records.append(bestrow);base=besttree
        (BUILD/'raw-search.json').write_text(json.dumps(records,indent=2)+'\n')
        if best<len(nets):print('BANK INCOMPLETE',bank,best,flush=True)
    save(base)

if __name__=='__main__':main()
