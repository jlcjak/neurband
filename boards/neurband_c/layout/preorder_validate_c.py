"""Run native cleanup and the supplied coupling/noise acceptance models sequentially."""
from pathlib import Path
import os, subprocess, sys
ROOT=Path('.');BUILD=ROOT/'boards/neurband_c/layout/build/preorder_20261029';PYTHON=sys.executable
jobs=[('prune-final',['boards/neurband_c/layout/preorder_prune_finish_c.py']),('coupling-current',['sim/preorder/coupling.py']),('inject-current',['sim/preorder/inject.py']),('ground-current',['boards/neurband_c/layout/audit_ground_c.py'])]
for name,args in jobs:
 with (BUILD/(name+'.log')).open('w')as log:p=subprocess.run([PYTHON,*args],stdout=log,stderr=subprocess.STDOUT)
 print(name,p.returncode,flush=True)
 if p.returncode:raise SystemExit(p.returncode)
