"""Attach missing package models and keep non-parts out of assembly positions."""
from ipc_c import *
i=IPC();fs=i.get(['KOT_PCB_FOOTPRINT']);i.begin()
models={'J1':'XUNPU_FPC-05F-20PH20.step','U1':'NRF52832_QFAA.step'}
for f in fs:
 name=ref(f)
 if name in models:
  f['definition']['items']=[p for p in f['definition']['items']if not p['@type'].endswith('.Footprint3DModel')]
  f['definition']['items'].append({'@type':'type.googleapis.com/kiapi.board.types.Footprint3DModel','filename':'${KIPRJMOD}/layout/models/'+models[name],'scale':{'x_nm':1,'y_nm':1,'z_nm':1},'offset':{},'rotation':{},'visible':True,'opacity':1})
 if name in ['AE1','J2','J3']or name.startswith('TP'):
  f.setdefault('attributes',{}).update(exclude_from_position_files=True,exclude_from_bill_of_materials=True)
 i.update([f])
i.end('REV C: complete component models and one-sided assembly metadata');i.save();print('Attached J1/nRF models; pads excluded from assembly')
