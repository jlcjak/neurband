"""Run the complete supplied analog suite and export a checked preorder release.

The gate uses 3313/10k tables and sums via-land coupling before injection.
Run from the repository root with the preorder simulation virtual environment.
"""
from pathlib import Path
import subprocess,sys,json,hashlib,os
BUILD=Path('boards/neurband_c/layout/build/preorder_20261029');PYTHON=sys.executable
PCB=Path('boards/neurband_c/neurband_c.kicad_pcb');POLISH=BUILD/'polish'
def job(name,args,env=None):
 with (BUILD/(name+'.log')).open('w')as f:p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=env)
 print(name,p.returncode,flush=True)
 if p.returncode:raise SystemExit(p.returncode)
def main():
 env=os.environ.copy();env['PY']=PYTHON
 analysed=hashlib.sha256(PCB.read_bytes()).hexdigest();log=POLISH/'run-all.log'
 with log.open('w')as f:p=subprocess.run(['sh','sim/preorder/run_all.sh'],stdout=f,stderr=subprocess.STDOUT,env=env)
 assert p.returncode==0,'Full analog suite failed'
 assert analysed==hashlib.sha256(PCB.read_bytes()).hexdigest(),'PCB changed while analog suite ran'
 (POLISH/'run-all-receipt.json').write_text(json.dumps(dict(command='sh sim/preorder/run_all.sh',exit_code=0,analysed_pcb_sha256=analysed,log=str(log),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()),indent=2)+'\n')
 for name,script in [('combined-acceptance','polish_acceptance_c.py'),('ground-final','audit_ground_c.py'),('audit-final','audit_release_c.py'),('export-final','export_preorder_c.py'),('polish-proof','polish_evidence_c.py'),('release-report','report_preorder_c.py'),('gerber-inspection','inspect_preorder_gerbers_c.py')]:
  job(name,[PYTHON,'boards/neurband_c/layout/'+script])
if __name__=='__main__':main()
