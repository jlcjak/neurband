"""Bake the verified assembly rotations without moving board artwork.
Run from the repository root; preserves every unaffected token and board item.
"""
from pathlib import Path
import re, math, json, copy
PCB=Path('boards/neurband_c/neurband_c.kicad_pcb')
BUILD=Path('boards/neurband_c/layout/build/preorder_20261029')
LIB=PCB.parent/'layout/neurband.pretty'
TOK=re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')
def parse(text):
    stack=[]; cur=[]
    for m in TOK.finditer(text):
        t=m.group()
        if t=='(': stack.append(cur);cur=[]
        elif t==')': done=cur;cur=stack.pop();cur.append(done)
        else:cur.append(t)
    return cur[0]
def dump(n,depth=0):
    if not isinstance(n,list):return str(n)
    if not any(isinstance(v,list) for v in n):return '('+' '.join(map(str,n))+')'
    return '('+' '.join(str(v) for v in n if not isinstance(v,list))+''.join('\n'+'\t'*(depth+1)+dump(v,depth+1) for v in n if isinstance(v,list))+'\n'+'\t'*depth+')'
def kids(n,k):return [v for v in n if isinstance(v,list) and v[0]==k]
def get(n,k):return next(iter(kids(n,k)),None)
def num(v):return f'{v:.9f}'.rstrip('0').rstrip('.') if abs(v)>1e-10 else '0'
def rotate(x,y,a):
    a=math.radians(a);return x*math.cos(a)+y*math.sin(a),-x*math.sin(a)+y*math.cos(a)
def geometry(node,a,shift=0):
    for c in node:
        if not isinstance(c,list):continue
        if c[0] in ('at','start','end','mid','center','xy') and len(c)>=3:
            x,y=rotate(float(c[1]),float(c[2]),a);c[1:3]=[num(x),num(y-shift)]
            # Native pad/property angles are absolute on a board; do not change them.
        elif c[0]=='model':
            off=get(get(c,'offset'),'xyz');x,y=rotate(float(off[1]),float(off[2]),-a);off[1:3]=[num(x),num(y+shift)]
            z=get(get(c,'rotate'),'xyz');z[3]=num(float(z[3])-a)  # Model Z has the opposite sign to the footprint's planar rotation.
        else:geometry(c,a,shift)
def pads(tree):
    out={}
    for f in kids(tree,'footprint'):
        ref=next(p[2].strip('"') for p in kids(f,'property') if p[1]=='"Reference"')
        t=get(f,'transform');xy=get(t,'translate');a=float(get(t,'rotate')[1])
        for i,p in enumerate(kids(f,'pad')):
            q=get(p,'at');x,y=rotate(float(q[1]),float(q[2]),a)
            out[f'{ref}:{i}']=[round(float(xy[1])+x,8),round(float(xy[2])+y,8),float(q[3])%360 if len(q)>3 else 0,get(p,'size')[1:],get(p,'layers')[1:]]
    return out
def main():
    tree=parse(PCB.read_text());before=pads(tree);mapping={}
    deltas={'U1':-90,'U2':-90,'U3':180,'U4':-90,**{f'RN{i}':-90 for i in range(1,5)}}
    for f in kids(tree,'footprint'):
        ref=next(p[2].strip('"') for p in kids(f,'property') if p[1]=='"Reference"')
        if ref not in deltas and ref!='J1':continue
        old=f[1].strip('"');name=old.split(':')[1]+'_FabZero' if ref!='J1' else 'XUNPU_FPC-05F-20PH20_Centroid'
        assert not old.endswith(('FabZero','Centroid')), 'Already baked'
        delta=deltas.get(ref,0);t=get(f,'transform');a=get(t,'rotate');a[1]=num((float(a[1])+delta)%360)
        for item in f[2:]:
            if isinstance(item,list) and item[0] not in ('transform',):geometry([item],-delta,1.6 if ref=='J1' else 0)
        if ref=='J1':get(t,'translate')[2]=num(float(get(t,'translate')[2])+1.6)
        f[1]=json.dumps('neurband:'+name);mapping[old]='neurband:'+name
        local=copy.deepcopy(f);local[1]=json.dumps(name)
        local[:]=[v for v in local if not(isinstance(v,list) and v[0] in ('transform','path','sheetname','sheetfile'))]
        # Library pad angles are relative; board pad angles above remain absolute.
        for p in kids(local,'pad'):
            at=get(p,'at');angle=(float(at[3]) if len(at)>3 else 0)-float(a[1]);at[3:]=[num(angle%360)]
        (LIB/(name+'.kicad_mod')).write_text(dump(local)+'\n')
    after=pads(tree);assert before==after,[(k,before[k],after[k]) for k in before if before[k]!=after[k]][:10]
    PCB.write_text(dump(tree)+'\n')
    (BUILD/'cpl-pad-proof.json').write_text(json.dumps({'pads_compared':len(before),'maximum_position_delta_mm':0,'maximum_rotation_delta_deg':0,'library_ids':mapping},indent=2)+'\n')
    print(json.dumps(mapping,indent=2));print('Unmoved pads:',len(before))
if __name__=='__main__':main()
