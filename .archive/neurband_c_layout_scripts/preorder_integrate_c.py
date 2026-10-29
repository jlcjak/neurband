"""Integrate audited stopped-work geometry, then repair local placement.

The earlier board is an input to this one-time migration, never a release.
The CPL bake must have been proven first. Native checks follow this save.
"""
from file_layout_c import *
import xml.etree.ElementTree as ET

def main():
    old=load(BUILD/'before/neurband_c.kicad_pcb')
    t=load('boards/neurband_c/layout/build/omp_partial_20261029/main/neurband_c.kicad_pcb')
    op=pad_data(old);npads=pad_data(t)
    fixed=['J1','J2','J3','SW1','D1','AE1','C21','L1','R3','C22','C23']+[f'TP{i}'for i in range(1,6)]
    def signature(ps,r):return sorted((p['num'],tuple(round(x,7)for x in p['center']),p['net'])for p in ps if p['ref']==r)
    for r in fixed:assert signature(op,r)==signature(npads,r),r
    assert {(p['num'],p['net'])for p in op if p['ref']=='U1'}=={(p['num'],p['net'])for p in npads if p['ref']=='U1'}
    rf={'Net-(U1-ANT)','Net-(C22-Pad1)','Net-(AE1-A)'}
    def cs(tree):return sorted(dump(c[:-1])for c in copper(tree)if net(c)in rf)
    assert cs(old)==cs(t),'RF copper changed'
    for z in kids(t,'zone'):
        if get(z,'keepout'):setc(z,'hatch','edge','0')
    assert [dump(z)for z in kids(old,'zone')if get(z,'keepout')]==[dump(z)for z in kids(t,'zone')if get(z,'keepout')],'exclusions changed'
    by={ref(f):f for f in kids(t,'footprint')}
    moves={'C18':(4.45,7.9,180),'C11':(13.075,6.1,90),'C13':(13.09,8.0,270),
           'C33':(13.075,9.9,270),'C3':(12.1,9.9,90),
           'C32':(13.075,11.75,90),'C9':(13.075,13.6,270),
           'U3':(8.6,18.95,180),'C27':(10.65,20.0,0),'C26':(11.6,18.95,0)}
    # Release all old local links for moved caps, but retain global power branches.
    quiet={'/DEC1','Net-(U2-VCAP3)'}
    removed=set()
    movedold=[p for p in npads if p['ref']in moves]
    for c in copper(t):
        n=net(c);g,zs=shape(c)
        if n in quiet:removed.add(item_id(c));continue
        if any(n==p['net'] and any(z in p['layers']for z in zs)and g.distance(p['poly'])<.25 for p in movedold):
            if n in rf:raise RuntimeError('RF local edit refused')
            removed.add(item_id(c))
    remove_ids(t,removed)
    for r,v in moves.items():move(by[r],*v)
    # Native source fields, including the coordinator's three consolidations.
    root=ET.parse(BUILD/'source.xml')
    for comp in root.findall('.//components/comp'):
        r=comp.attrib['ref']
        if r not in by:continue
        f=by[r];fields={q.attrib['name']:q.text or ''for q in comp.findall('./fields/field')}
        fields['Value']=comp.findtext('value')or''
        for k,v in fields.items():
            p=next((p for p in kids(f,'property')if uq(p[1])==k),None)
            if p:p[2]=json.dumps(v)
    # Remove conflicts with newly placed pads, preserving protected RF and fence.
    newpads=[p for p in pad_data(t)if p['ref']in moves]
    for c in copper(t):
        g,zs=shape(c);n=net(c)
        if any(p['net']!=n and any(z in p['layers']for z in zs)and g.distance(p['poly'])<.101 for p in newpads):
            assert n not in rf,(n,'protected RF conflict');removed.add(item_id(c))
    remove_ids(t,removed)
    save(t)
    (BUILD/'integration-audit.json').write_text(json.dumps({'fixed_pad_geometry_preserved':fixed,'nrf_pin_nets_preserved':True,'rf_copper_and_keepouts_preserved':True,'moves':moves,'removed_local_items':len(removed)},indent=2)+'\n')
    print('Saved audited integration and local placement repairs')

if __name__=='__main__':main()
