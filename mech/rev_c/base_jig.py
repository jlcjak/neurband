"""base_jig.py - rev C bonding jig, stage 2 (r2): a pedestal for pressing the module base onto pods 3/4.

Why a second jig: the r2 base carries the two strap bars outboard of its ends. On the flat bonding
jig (bond_jig.py, stage 1) the free pods 2 and 5 lie right where those bars come down, so the base can
no longer be pressed on there. Stage 1 bonds the six free pods; stage 2 puts the strip on this pedestal:
the pod 3/4 section of the flex lies on the saddle (R42 underside minus the flex and the pressed dots)
with its four 1.2 mm holes on four pins, the rest of the strip hangs down both sides like on a wrist,
and the base drops onto the saddle between two Y fences and stops on four pads outside the flex.

Jig frame = the flex frame of bond_jig.py (X along the flex, Y distal, Z up), the base turned 180 deg
about Z from the module frame (X_mech = -X, Y_mech = -Y).
FDM PLA/PETG (or MJF PA12), saddle up, no supports.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/base_jig.py
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True
sys.neurband_jig_lib = True
import FreeCAD, Part
import rc as R
import cadutil as U
import module as M
import bond_jig as BJ

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
H_PED = 26.0                    # saddle crest above the table: the strip hangs clear below the bars
PED_HW_Y = R.POD_L / 2 + 0.5    # pedestal half length along Y (the flex paddles are 30 long)
EDGE_R = 2.0                    # rounded saddle edges (the edge links bend over them)
FOOT = (34.0, 60.0, 3.0)        # foot plate X x Y x Z (Y is the long direction: stable, clear of the hanging pods)
FENCE_T, FENCE_CLR = 1.6, 0.3


def build():
    dz = H_PED - BJ.z_saddle(0.0)               # lift the bond_jig saddle geometry to the pedestal top
    xe = BJ.X_E
    ped = R.box(-xe, xe, -PED_HW_Y, PED_HW_Y, 0.0, H_PED + 1)
    sad = Part.makeCylinder(BJ.RS, 60, V(0, -30, BJ.ZAX + dz), V(0, 1, 0))
    ped = ped.common(sad)                       # the saddle cylinder (axis far below) covers the pedestal under its arc
    ped = R.fillet_edges(ped, EDGE_R, lambda e: e.BoundBox.YLength > 2 * PED_HW_Y - 0.1 and e.BoundBox.ZMin > H_PED - 4.0)
    foot = R.box(-FOOT[0] / 2, FOOT[0] / 2, -FOOT[1] / 2, FOOT[1] / 2, 0.0, FOOT[2])
    s = ped.fuse(foot)
    # base stop pads on the R42 surface outside the flex paddles (as bond_jig, lifted)
    stop = Part.makeCylinder(M.R_U, 60, V(0, -30, BJ.ZAX + dz), V(0, 1, 0))
    # base Y fences (the X ends stay open: the strap bars overhang the pedestal there)
    by = -M.YC
    for sy in (-1, 1):
        yf = by + sy * (M.OUT_L / 2 + FENCE_CLR)
        ya, yb = sorted((yf, yf + sy * FENCE_T))
        f = R.box(-M.OUT_W / 2 + 4, M.OUT_W / 2 - 4, ya, yb, H_PED - 6, H_PED + 2.5)
        s = s.fuse(f)
        # fence posts down to the foot
        s = s.fuse(R.box(-M.OUT_W / 2 + 4, M.OUT_W / 2 - 4, ya, yb, 0.0, H_PED - 5.9).common(
            R.box(-60, 60, -FOOT[1] / 2, FOOT[1] / 2, 0, 60)))
    for sx in (-1, 1):
        for ya, yb in ((-15.0, BJ.SPINE_GAP[0]), (BJ.SPINE_GAP[1], 15.0)):
            pad = R.box(min(sx * 12.9, sx * 14.6), max(sx * 12.9, sx * 14.6), ya, yb, H_PED - 6, H_PED + 5).common(stop)
            pad = pad.fuse(R.box(min(sx * 12.0, sx * 14.6), max(sx * 12.0, sx * 14.6), ya, yb, H_PED - 6, H_PED - 1).common(
                stop.cut(Part.makeCylinder(M.R_U - 4, 60, V(0, -30, BJ.ZAX + dz), V(0, 1, 0)))))
            s = s.fuse(pad)
    # pins for the pod 3/4 holes
    for xd in (-9.0, 9.0):
        xc = BJ.x_of(xd)
        zb = BJ.z_saddle(xc) + dz
        for y in R.HOLE_Y:
            s = s.fuse(Part.makeCylinder(BJ.JIG_PIN_D / 2, BJ.PIN_ABOVE + 0.5, V(xc, y, zb - 0.5)))
    return s.removeSplitter(), dz


if not getattr(sys, 'neurband_lib2', False):
    log = R.Log('base_jig')
    jig, dz = build()
    jig = U.check(jig, 'base_jig', log)
    base = Part.read(os.path.join(R.HERE, 'module_base.step'))
    b2 = base.copy()
    b2.rotate(V(0, 0, 0), V(0, 0, 1), 180)
    b2.translate(V(0, 0, BJ.ZAX + dz + M.R_U))
    pod = Part.read(os.path.join(R.HERE, 'pod.step'))
    chk = dict(base_vs_jig=round(b2.common(jig).Volume, 3), saddle_crest_mm=round(H_PED, 2),
               base_bottom_of_bars_above_table=round(b2.BoundBox.ZMin, 2))
    bb = jig.BoundBox
    log("  base jig: %.1f x %.1f x %.1f mm; checks %s" % (bb.XLength, bb.YLength, bb.ZLength, json.dumps(chk)))
    R.save('base_jig', [('base_jig', jig, (0.85, 0.85, 0.80))], log)
    R.save('base_jig_fit', [('base_jig', jig, (0.85, 0.85, 0.80)), ('module_base', b2, R.C_HOUSING)], log)
    R.fab('base_jig', 'neurband rev C bonding jig stage 2: pedestal for the module base (print once)', jig, 1, 'fdm', 'pla', 'white', log)
    R.finish(log)
