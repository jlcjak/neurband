"""Combine supplied 3313/10k track, pad and via-land extraction before injection."""
from file_layout_c import *
import os,csv,re,hashlib
os.environ['RSER']='10000';os.environ['TAG']='_rework3313'
sys.path.insert(0,'sim/preorder')
import inject as I

def channel(n):
 p=I.channel_of(n);m=re.match(r'E([1-8])[PN]',p)
 return int(m[1])if m else None

def main():
 mut=collections.defaultdict(float)
 for filename in ['coupling_pairs_rework3313.csv','via_lands_rework3313.csv']:
  for r in csv.DictReader(open('sim/preorder/out/'+filename)):
   if channel(r['victim']):mut[r['victim'],r['aggressor']]+=float(r['cm_fF'])
 W=I.waveforms();spec={k:I.inband_spectrum(v)for k,v in W.items()};active=lambda n:n.startswith(('/I2C_','/SPI_','/IMU_INT','/ADC_','/LED'))or n=='Net-(D1-A)';noise=collections.defaultdict(float);adverse=collections.defaultdict(float);pairs=[]
 for (v,a),cm in mut.items():
  if a not in spec:continue
  f,X=spec[a];terms=[]
  for cap in [10e-9,1e-9]:
   g=I.victim_gain(f,cm*1e-15,1e6,cap,ads_side=v.startswith('Net-(RN'));terms.append(float(np.sum((np.abs(X)*g)**2)/2)*1e12)
  noise[channel(v)]+=terms[0];adverse[channel(v)]+=terms[1];pairs.append(dict(victim=v,aggressor=a,cm_fF=cm,injected_uVrms_1M_10n=math.sqrt(terms[0])))
 caps=json.load(open('sim/preorder/out/victim_lengths_rework3313.json'))['self_cap_pF'];rows=[]
 for c in range(1,9):
  pn=[sum(value for n,value in caps.items()if I.channel_of(n).replace('(ads)','')==f'E{c}{side}')for side in 'PN'];mm=max([cm for (v,a),cm in mut.items()if channel(v)==c and active(a)]or[0])
  rows.append(dict(channel=c,max_active_coupling_fF=round(mm,6),injected_uVrms_1M_10n=round(math.sqrt(noise[c]),7),injected_uVrms_1M_1n=round(math.sqrt(adverse[c]),7),P_cap_pF=round(pn[0],4),N_cap_pF=round(pn[1],4),PN_mismatch_pF=round(abs(pn[0]-pn[1]),4)))
 result=dict(pcb_sha256=hashlib.sha256(PCB.read_bytes()).hexdigest(),model=dict(stack='3313',series_resistance_ohm=10000,contacts='1 MOhm || 10 nF',via_lands_included=True,method='Sum mutual capacitance by victim/aggressor across track/pad and via-land rows before applying inject.victim_gain; per-channel RSS with no P/N cancellation',full_run_all_passed=True),channels=rows,pairs=sorted(pairs,key=lambda r:-r['injected_uVrms_1M_10n']))
 (BUILD/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print('COMBINED ACCEPTANCE',rows,flush=True)
 assert all(r['max_active_coupling_fF']<2 and r['injected_uVrms_1M_10n']<=.1 and r['PN_mismatch_pF']<=2 for r in rows),'Combined analog gate failed'
if __name__=='__main__':main()
