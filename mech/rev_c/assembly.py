"""assembly.py - rev C assemblies with colours:
  band_assembly.step  the band closed as worn on a 160 mm wrist, without the wrist
  fit_160.step        the same on the 160 mm wrist model
(fit_145 / fit_180 and the numbers come from fit.py.)
Colours: housing matte grey PA12, pods charcoal, gold pads, amber flex, green PCB, LiPo silver.
Run: QT_QPA_PLATFORM=offscreen timeout 600 /usr/bin/freecad mech/rev_c/assembly.py
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.neurband_lib = True
sys.neurband_fit_lib = True
import rc as R
import fit as F

# ---------------- parameters ----------------
WRIST = 160.0

if True:
    log = R.Log('assembly')
    res, items, L = F.build_band(WRIST, log, with_wrist=True, cad=False)
    log(f"C={WRIST}: gap {res['gap_mm']} mm at {res['gap_centre_deg_from_dorsal']} deg, cover {res['electrode_cover_pct']} %")
    R.save(f'fit_{int(WRIST)}', items, log)
    R.save('band_assembly', items[1:], log)
    R.finish(log)
