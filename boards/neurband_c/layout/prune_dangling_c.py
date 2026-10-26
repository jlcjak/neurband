"""Remove native-identified unused holes and dead-end track branches."""
from ipc_c import *
import sys
build=PCB.parent/'layout/build';stem=sys.argv[1]if len(sys.argv)>1 else'final-linked'
d=json.loads((build/(stem+'.json')).read_text());ids={q['uuid']for v in d['violations']if v['type']in ['via_dangling','track_dangling']for q in v['items']}
i=IPC();items=[c for c in i.get(['KOT_PCB_TRACE','KOT_PCB_VIA'])if c['id']['value']in ids]
(build/('pruned-'+stem+'.json')).write_text(json.dumps(items,indent=2))
i.begin();i.delete([c['id']['value']for c in items]);i.end('REV C: remove unused routing vias and dead-end copper');i.save();print('Pruned',len(items),'unused copper items')
