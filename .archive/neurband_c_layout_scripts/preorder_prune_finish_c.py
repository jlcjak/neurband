"""Remove native-identified obsolete copper while preserving a fully connected milestone."""
from preorder_cleanup_c import *
def main():
 t=load();save(t,BUILD/'before-final-native-prune.kicad_pcb');d=check('prune-finish');assert not d['unconnected_items'];assert not any(v['severity']=='error'for v in d['violations'])
 for k in range(180):
  ids={i['uuid']for v in d['violations']if v['type']in ['track_dangling','via_dangling']for i in v['items']}
  if not ids:print('PRUNE COMPLETE',k,flush=True);return
  old=load();t=copy.deepcopy(old);remove_ids(t,ids);save(t);d=check('prune-finish')
  if d['unconnected_items']:
   t=load();added=bridges(t,d)
   if added:save(t);d=check('prune-finish')
  if d['unconnected_items']or any(v['severity']=='error'for v in d['violations']):
   print('PRUNE ROLLBACK',k,flush=True);save(old);check('prune-finish');return
 raise RuntimeError('Native prune did not converge')
if __name__=='__main__':main()
