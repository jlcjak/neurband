"""pod.py - rev C electrode pod shell, low-profile TPU (6 per band: pods 1, 2, 5, 6, 7, 8; pods 3
and 4 sit in the module underside).

Pod-local frame: X = around the wrist (pod width), Y = along the arm (distal = -Y), Z = away from
the skin. z = 0 is the shell face the flex paddle (7.1 x 30) lies on; the skin is below (-Z).
- Soft rounded pebble, 9.0 x 32.0 x 3.2 mm (covers the whole 30 mm paddle), ends tapering to
  2.0 mm under the band edges, R1.2 top blends, R0.8 face blends (strain relief where
  the flex spine leaves at +/-X, y -7..+0.6).
- Compliant contact: 7.0 x 0.5 mm pockets behind the pads (y = -10/0/+10) hold 6.6 x 1.5 mm foam
  disks -> pads stand 1.0 mm proud (about 0.65 mm worn). Two 1.0 mm pins at y = +/-5 locate the
  flex's 1.2 mm holes during bonding (0.2 mm clearance, not a press fit).
- Captive edge sleeve for the continuous 25 mm webbing: a 25.4 x 1.6 mm slot through the pod
  (along X) whose roof is open over the middle 22.4 mm. The fabric stays visible on the outside;
  two 1.5 mm rounded rims hold its edges. The webbing slides freely, so its stretch never
  loads the flex links (the flex sets the 18 mm pitch). It presses on the whole pad span, so a
  soft TPU shell still loads all three pads evenly.
Print: TPU 95A, on its side (the sleeve vertical), no supports; or MJF TPU from a fab.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/pod.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import rc as R
import cadutil as U

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
SHELL_W = 9.0                   # around the wrist (flex paddle 7.1)
SHELL_L = 32.0                  # along the arm: covers the 30 mm flex paddle completely
END_H = 2.0                     # shell height at the tips (ends taper under the band edges)
PLAN_R = 3.6
H = 3.2                         # total shell height above the face
BASE_T = R.BASE_T               # face -> sleeve floor
SLEEVE_W = R.CHANNEL_W          # 25.4
SLEEVE_H = R.CHANNEL_H          # 1.6
RIM = 1.5                       # rim overlap over each webbing edge
TOP_FILLET = 1.2
FACE_FILLET = 0.8
RIM_FILLET = 0.3
FOAM_POCKET_D = R.FOAM_POCKET_D
FOAM_POCKET_H = R.FOAM_POCKET_H
PIN_D = 1.0
PIN_H = 0.55                    # < free foam proud (1.0): disengages when worn
TOP_Z = H


def build(log=None):
    w, L = SHELL_W, SHELL_L
    s = R.rrect(w, L, PLAN_R, H, 0.0)
    # taper the ends: cylinder (axis X) through (y_rim, H) and (L/2, END_H)
    y1, y2 = SLEEVE_W / 2, L / 2
    zc = ((y2 ** 2 + END_H ** 2) - (y1 ** 2 + H ** 2)) / (2 * (END_H - H))
    rc_ = (y1 ** 2 + (H - zc) ** 2) ** 0.5
    s = s.common(Part.makeCylinder(rc_, 4 * w, V(-2 * w, 0, zc), V(1, 0, 0)))
    s = R.fillet_edges(s, TOP_FILLET, lambda e: e.BoundBox.ZMin > 1.2, log, 'top')
    s = R.fillet_edges(s, FACE_FILLET, lambda e: e.BoundBox.ZMax < 1e-6, log, 'face')
    # sleeve (through along X) and the open roof over the middle of the webbing
    s = s.cut(R.box(-w, w, -SLEEVE_W / 2, SLEEVE_W / 2, BASE_T, BASE_T + SLEEVE_H))
    yo = SLEEVE_W / 2 - RIM
    s = s.cut(R.box(-w, w, -yo, yo, BASE_T + SLEEVE_H - 0.2, H + 1))
    s = s.removeSplitter()
    s = R.fillet_edges(s, RIM_FILLET, lambda e: e.BoundBox.ZMin > BASE_T + SLEEVE_H - 0.01
                       and abs(abs(e.BoundBox.YMin) - yo) < 0.05 and e.BoundBox.YLength < 0.05, log, 'rim')
    # foam pockets behind the pads
    for y in R.PAD_Y:
        s = s.cut(Part.makeCylinder(FOAM_POCKET_D / 2, FOAM_POCKET_H, V(0, y, 0)))
    # locating pins with domed tips
    for y in R.HOLE_Y:
        p = Part.makeCylinder(PIN_D / 2, PIN_H - PIN_D / 2 + 0.01, V(0, y, -PIN_H + PIN_D / 2))
        p = p.fuse(Part.makeSphere(PIN_D / 2, V(0, y, -PIN_H + PIN_D / 2)).common(
            Part.makeCylinder(PIN_D / 2, PIN_D / 2, V(0, y, -PIN_H))))
        s = s.fuse(p)
    return s.removeSplitter()


if not getattr(sys, 'neurband_lib', False):
    log = R.Log('pod')
    shell = U.check(build(log), 'pod', log)
    bb = shell.BoundBox
    log(f"  pod shell {bb.XLength:.2f} x {bb.YLength:.2f} x {bb.ZLength:.2f} mm (W x L x H incl. pins); "
        f"top {TOP_Z:.2f} above the face, {TOP_Z + R.STACK_LOADED:.2f} above the skin worn")
    poly, gold, foam = R.flex_pod()
    web = R.box(-6, 6, -R.STRAP_W / 2, R.STRAP_W / 2, BASE_T + 0.1, BASE_T + 0.1 + R.STRAP_T)
    R.save('pod', [('pod', shell, R.C_POD)], log)
    R.save('pod_with_flex', [('pod', shell, R.C_POD), ('foam', Part.makeCompound(foam), R.C_FOAM),
                             ('flex', poly, R.C_FLEX), ('pads', Part.makeCompound(gold), R.C_GOLD),
                             ('webbing', web, R.C_STRAP)], log)
    R.fab('pod', 'Electrode pod shell rev C, TPU (6 per band)', shell, 16, 'fdm', 'tpu', 'black', log,
          extra={"notes": "TPU 95A, print on its side; 6 per band + spares; foam disks 6.6 x 1.5 mm bought separately"})
    R.finish(log)
