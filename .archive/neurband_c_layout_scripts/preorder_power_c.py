"""Local supply loops and capacitor-origin distribution on the frozen outline."""
from file_layout_c import *

def main():
    t=load();remove_ids(t,{item_id(c)for c in copper(t)if net(c)in ('+3V3','VBAT')})
    ps=pad_data(t);pads={(p['ref'],p['num']):p for p in ps}
    p=lambda r,k:pads[r,str(k)]['center']
    # The short supply links take precedence over low-rate digital escapes.
    links=[('+3V3',[p('U3',2),(7.8,20.0),p('C27',1)],.3),
           ('VBAT',[p('U3',3),p('C26',1)],.25),
           ('VBAT',[p('U4',3),p('C25',1)],.25),
           ('+3V3',[p('U1',36),p('C18',1)],.127),
           ('+3V3',[p('U2',48),p('C10',1)],.15),
           ('+3V3',[p('C11',1),(13.6,6.58),(13.6,6.85),p('U2',50)],.127),
           ('+3V3',[(13.6,6.85),(13.6,7.85),p('U2',52)],.1),
           ('+3V3',[p('U1',48),(11.2,9.3),(11.35,9.5),(10.9,10.0),p('C17',1)],.127),
           ('+3V3',[p('C16',1),(11.2,1.5),p('U1',13)],.25),
           ('+3V3',[p('U5',12),(25.2,20.4),(26.2,20.4),(26.2,22.35),p('C31',1)],.15),
           ('+3V3',[p('U5',5),(24.0125,21.825)],.1),
           ('+3V3',[p('U5',8),(26.2,22.35)],.15)]
    reserved=[]
    for n,pts,w in links:
        for a,b in zip(pts,pts[1:]):
            c=track(a,b,n,w=w);g,zs=shape(c)
            bad=[(q['ref'],q['num'])for q in ps if q['net']!=n and 0 in q['layers']and g.distance(q['poly'])<.0999]
            assert not bad,(n,a,b,bad)
            reserved.append(c)
    kill=set()
    protected={'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'}
    for c in copper(t):
        g,zs=shape(c)
        for q in reserved:
            if net(c)==net(q):continue
            h,_=shape(q)
            if (c[0]=='via' or 0 in zs)and g.distance(h)<(.126 if c[0]=='via'else .101):
                assert net(c)not in protected
                # Counterpoise and the moved VSS31/EP anchor stay fixed.
                if c[0]=='via'and net(c)=='GND':
                    x,y=map(float,get(c,'at')[1:3]);assert not(abs(x-6)<.01 and y>12)and math.dist((x,y),(6.2,3))>.01
                kill.add(item_id(c))
    remove_ids(t,kill);t.extend(reserved);save(t)
    r=Router(t,width=.127)
    def link(n,r1,k1,r2,k2):
        a,b=pads[r1,str(k1)],pads[r2,str(k2)]
        ok=r.link(n,a['center'],a['layers'],b['center'],b['layers'],False)
        print('LOCAL',n,r1,k1,r2,k2,ok,flush=True);return ok
    assert link('/DEC1','U1',1,'C13',1)
    assert link('Net-(U2-VCAP3)','U2',55,'C3',1)
    assert link('/RLDREF','U2',60,'C32',1)
    save(t)
    # Route explicit branches from C27. Trunks are wide, outside the input field.
    trunks=[('+3V3',p('C27',1),[0],p('C17',1),[0],.25),
            ('+3V3',p('C27',1),[0],p('R5',1),[0],.25),
            ('+3V3',p('C17',1),[0],p('C16',1),[0],.25),
            ('+3V3',p('C17',1),[0],p('C18',1),[0],.25),
            ('+3V3',p('C17',1),[0],p('C11',1),[0],.25),
            ('+3V3',p('C11',1),[0],p('C10',1),[0],.25),
            ('+3V3',p('C27',1),[0],p('C31',1),[0],.25)]
    failed=[]
    for n,a,az,b,bz,w in trunks:
        r=Router(t,width=w)
        ok=r.link(n,a,az,b,bz);print('TRUNK',n,a,b,ok,flush=True)
        if not ok:failed.append((n,a,b,w))
        save(t)
    # Battery trunk is physically south/left of the sensitive field.
    # It meets the local VIN capacitor from the left, without a tour of the AFE.
    r=Router(t,width=.3)
    way=[(p('J2',1),[2]),((23.9,26.45),[2]),((7.0,26.45),[2]),((7.0,21.0),[2]),(p('C26',1),[0])]
    for (a,az),(b,bz) in zip(way,way[1:]):
        ok=r.link('VBAT',a,az,b,bz);print('BATTERY',a,b,ok,flush=True)
        if not ok:failed.append(('VBAT',a,b,.3))
        save(t)
    (BUILD/'power-tree.json').write_text(json.dumps({'trunks':trunks,'battery_waypoints':way,'failures':failed},indent=2)+'\n')

if __name__=='__main__':main()
