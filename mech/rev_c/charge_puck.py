"""charge_puck.py - rev C charger: a printed puck with two spring pogo pins and two 3 x 1 mm
magnets. The band is taken off and laid module-down on the puck (only possible off the wrist):
the nose drops into the module's underside counterbore, the magnets (polarity keyed, N/S
opposite to the module's) pull it in, and the pins press on the board's VCHG/GND bottom pads
through the 1.7 mm deep window. Wired to a USB cable (5 V, GND) through the slot at the back.
Puck frame: Z up toward the module (the module is placed upside down on it), Y = module Y.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/charge_puck.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True
import FreeCAD, Part
import rc as R
import cadutil as U
import module as M

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
BASE_W, BASE_L, BASE_H, BASE_R = 26.0, 30.0, 5.0, 6.0
PLAT_W, PLAT_L = 10.4, 20.4         # fits between the pod 3/4 pads (|x| >= 5.4); carries the magnets
PLAT_H = 2.0                        # above the base (clears the lug ears and pods)
SPOT_D = 4.6                        # flat spot face around each magnet (no acute pocket rims)
PIN_BARREL_D = 2.05                 # 2.0 x 6 mm spring pogo pins (1 mm travel), solder cup below
PIN_Y = [y - M.CHG_Y for y in M.CHG_PADS_Y]      # relative to the window centre
PIN_X = [-0.5, 0.5]                 # staggered on the 2 mm-wide pads: 1.1 mm web between the holes
MAG_D, MAG_T, MAG_SKIN = 3.2, 1.05, 0.35
CABLE_SLOT = (4.0, 2.5)


def build():
    top_z = BASE_H + PLAT_H
    base = R.rrect(BASE_W, BASE_L, BASE_R, BASE_H, 0)
    base = R.fillet_edges(base, 1.5, lambda e: e.BoundBox.ZMin > BASE_H - 0.01, None, 'base')
    # plateau with a convex top matching the module underside (R_U), then the locating nose
    plat = R.rrect(PLAT_W, PLAT_L, 2.0, PLAT_H + 2, BASE_H - 0.01)
    plat = plat.common(R.cyl_y(M.R_U, 0, top_z - M.R_U))
    s = base.fuse(plat).removeSplitter()
    zt = top_z
    for x, y in zip(PIN_X, PIN_Y):
        s = s.cut(Part.makeCylinder(PIN_BARREL_D / 2, zt + 1, V(x, y, -0.5)))
    for sx in (-1, 1):   # magnets glued flush into pockets under a flat spot face
        zf = top_z - 0.25
        s = s.cut(Part.makeCylinder(SPOT_D / 2, 2, V(sx * M.MAG_X, M.MAG_DY, zf)))
        s = s.cut(Part.makeCylinder(MAG_D / 2, MAG_T + 2, V(sx * M.MAG_X, M.MAG_DY, zf - MAG_T)))
    # wiring cavity + cable exit
    s = s.cut(R.box(-4, 4, -8, 8, -0.01, 2.5))
    s = s.cut(R.box(-CABLE_SLOT[0] / 2, CABLE_SLOT[0] / 2, 0, BASE_L, -0.01, CABLE_SLOT[1]))
    return s.removeSplitter()


if not getattr(sys, 'neurband_puck_lib', False):
    log = R.Log('charge_puck')
    p = U.check(build(), 'charge_puck', log)
    bb = p.BoundBox
    log(f"  puck {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm; pins at y {PIN_Y} (3.0 mm pitch), "
        f"pin tip must stand {M.Z_PCB + 0.3:.2f} mm above the plateau (0.3 preload)")
    R.save('charge_puck', [('charge_puck', p, R.C_POD)], log)
    R.fab('charge_puck', 'neurband rev C charger puck', p, 2, 'mjf', 'pa12', 'black', log)
    R.finish(log)
