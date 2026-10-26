"""Refresh source UUIDs/fields/nets without resetting reviewed layout footprints."""
from ipc_c import *
from place_c import BUILD
import subprocess,sys,xml.etree.ElementTree as ET
sch=PCB.with_suffix('.kicad_sch')
p=subprocess.run([sys.executable,str(PCB.parents[2]/'tools/netcheck.py'),str(sch)],capture_output=True,text=True,check=True)
(BUILD/'final-netcheck.log').write_text(p.stdout+p.stderr)
subprocess.run([str(RUNTIME/'bin/kicad-cli'),'sch','export','netlist','--format','kicadxml','-o',str(BUILD/'source.xml'),str(sch)],check=True,capture_output=True)
swaps={'J1':'neurband:XUNPU_FPC-05F-20PH20','J2':'neurband:WirePads_2x1.5x2mm_P3mm','J3':'neurband:WirePads_2x1.5x2mm_P3mm',**{f'TP{k}':'neurband:SWD_Pad_1x1_P1.27'for k in range(1,6)}}
data=PCB.with_suffix('.net').read_text()
for c in ET.parse(BUILD/'source.xml').findall('.//components/comp'):
 if c.attrib['ref']not in swaps:continue
 old=c.find('footprint').text;data=data.replace('(footprint "'+old+'")','(footprint "'+swaps[c.attrib['ref']]+'")')
path=BUILD/'layout-footprint-swaps.net';path.write_text(data)
i=IPC();i.begin();result=i.call('kiapi.board.commands.ImportNetlist',{'board':i.doc,'netlist_path':str(path),'match_mode':'NMM_REFERENCE','update_footprints':False,'override_locks':True})
if result.get('error_count'):raise RuntimeError(result)
i.end('REV C: final source identities and fields, preserve reviewed footprints');i.save()
(BUILD/'final-import.json').write_text(json.dumps(result,indent=2));print('Final source import',result,flush=True)
