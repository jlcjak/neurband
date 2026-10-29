"""Render actual fabrication Gerbers for visual inspection; does not edit copper."""
from pathlib import Path
import subprocess,sys
ROOT=Path('mfg/20261029_preorder');OUT=Path('boards/neurband_c/layout/build/preorder_20261029/gerber-review');OUT.mkdir(parents=True,exist_ok=True)
exe=str(Path(sys.executable).with_name('pygerber'))
for name in ['main','flex']:
 for p in (ROOT/name/'gerbers').iterdir():
  if p.suffix not in ['.gtl','.gbl','.g1','.g2','.gts','.gbs','.gtp','.gbp','.gto','.gbo','.gm1','.gbr']:continue
  style='solder_mask'if 'Mask'in p.stem else'paste_mask'if 'Paste'in p.stem else'silk'if'Silkscreen'in p.stem else'copper'
  dest=OUT/(p.stem+'.png');r=subprocess.run([exe,'render','raster',str(p),'-o',str(dest),'-d','60'if name=='main'else'16'],capture_output=True,text=True)
  print(p,r.returncode,flush=True)
  if r.returncode:print(r.stdout,r.stderr);raise SystemExit(r.returncode)
print('GERBER RENDERS COMPLETE',flush=True)
