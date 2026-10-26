"""Normalize a native FlipItems/update-in-one-commit duplication; no electrical changes."""
from ipc_rev_b import *
import copy
from place_rev_b import P,ref

i=IPC();fs=i.get(['KOT_PCB_FOOTPRINT']);chosen={}
for f in fs:
    r=ref(f)
    pads=[p for p in f['definition']['items'] if p['@type'].endswith('.Pad') and p.get('type')=='PT_SMD']
    actual='B' if pads and 'BL_B_Cu' in pads[0]['pad_stack']['layers'] else 'F'
    if actual==P[r][3]:chosen[r]=copy.deepcopy(f)
assert len(chosen)==60,len(chosen)
Path('/tmp/revB-correct-footprints.json').write_text(json.dumps(chosen,indent=2))
for _ in range(3):
    old=i.get(['KOT_PCB_FOOTPRINT'])
    if not old:break
    i.begin();i.delete(list({f['id']['value'] for f in old}));i.end('Remove duplicated native flip instances')
assert not i.get(['KOT_PCB_FOOTPRINT'])
items=[]
for f in chosen.values():
    mapping={}
    def renew(o,skip=False):
        if isinstance(o,dict):
            for k,v in list(o.items()):
                if k=='symbol_path':continue
                if k=='value' and isinstance(v,str) and len(v)==36 and v.count('-')==4:
                    o[k]=mapping.setdefault(v,str(uuid.uuid4()))
                else:renew(v)
        elif isinstance(o,list):
            for v in o:renew(v)
    renew(f);items.append(f)
i.begin();i.create(items);i.end('Restore unique correctly mirrored rev B footprints');i.save()
fs=i.get(['KOT_PCB_FOOTPRINT']);assert len(fs)==60
(PCB.parent/'layout/build/revB-footprints.json').write_text(json.dumps(fs,indent=2))
print('Saved exactly',len(fs),'unique footprints')
