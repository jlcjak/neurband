"""FreeCAD (GUI offscreen) STEP -> GLB with colours and part names.
Usage: STEP2GLB="in1.step=out1.glb;in2.step=out2.glb" QT_QPA_PLATFORM=offscreen freecad render/step2glb.py
"""
import os, sys, traceback
import FreeCAD, ImportGui

pairs = [p.split('=') for p in os.environ.get('STEP2GLB', '').split(';') if '=' in p]
rc = 0
for src, dst in pairs:
    try:
        doc = FreeCAD.newDocument('conv')
        ImportGui.insert(src, doc.Name)
        doc.recompute()
        roots = [o for o in doc.Objects if not o.InList]
        print('STEP2GLB', src, '->', dst, 'roots', [o.Label for o in roots],
              'objects', [o.Label for o in doc.Objects if o.TypeId.startswith('Part::')][:40], flush=True)
        if os.path.exists(dst):
            os.remove(dst)
        ImportGui.export(roots, dst)
        print('STEP2GLB ok', dst, os.path.getsize(dst), flush=True)
        FreeCAD.closeDocument(doc.Name)
    except Exception:
        traceback.print_exc()
        rc = 1
sys.stdout.flush()
os._exit(rc)
