"""pod.py - rev C electrode pod shell, low-profile TPU (6 per band: pods 1, 2, 5, 6, 7, 8; pods 3
and 4 sit in the module underside). r2: snap-in channel for the 20 mm hook-and-loop strap.

Pod-local frame: X = around the wrist (pod width), Y = along the arm (distal = -Y), Z = away from
the skin. z = 0 is the shell face the flex paddle (7.1 x 30) lies on; the skin is below (-Z).
- Soft rounded pebble, 9.0 x 32.0 mm (covers the whole 30 mm paddle), walls >= 1.0 mm (1.0 floor
  behind the foam, 1.0 lips). r2.1: the ends beyond the strap edges are smooth domes: the top runs on
  from the lip crest tangentially (quarter ellipse down to 2.0 mm at the tips, no barb at the crest),
  the plan ends are nearly semicircular and the domes' side edges are rounded R0.6; the lips' inner
  top edges are rounded R0.25 (outside the lips' full-thickness 1.0 mm span).
- Compliant contact: pockets behind the pads (y = -10/0/+10) for pre-cut round double-sided foam
  dots (rc.FOAM_D x rc.FOAM_T); the pocket depth puts the pads 1.0 mm proud (about 0.65 mm worn).
- Snap-in channel for the strap (rc.CHANNEL_W x rc.CHANNEL_H, along X): the strap is pressed in
  from above past two TPU lips (RIM overlap), so it is never threaded and the
  thick hook end and end cap never have to pass a pod. The strap's tension presses the pod onto the
  skin through the channel floor; the lips only keep the pod on the strap when the band is off.
Print: TPU 95A, on its side (the channel vertical), no supports.
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
PLAN_R = 4.3                    # nearly semicircular plan ends (r2.1; was 3.6)
EAR_A = 8.0                     # end dome: quarter-ellipse semi-axis along the arm (tangent at the lip crest)
EAR_SIDE_R = 0.6                # rounds the domes' side edges and the lips' sides (one radius: OCC can't blend 2 here)
H = R.BASE_T + R.CHANNEL_H + R.LIP_T   # 3.9: 1.0 floor behind the foam + sleeve + 1.0 rims
BASE_T = R.BASE_T               # face -> sleeve floor
SLEEVE_W = R.CHANNEL_W          # 20.8
SLEEVE_H = R.CHANNEL_H          # 2.5
RIM = 0.8                       # lip overlap over each strap edge (snap-in)
LEADIN = 0.0                    # (no lead-in chamfer: it thinned the 1.0 mm lips; TPU lips flex enough)
TOP_FILLET = 0.6                # keeps the 1.0 mm rims >= 1.0 through the blend
FACE_FILLET = 0.8
RIM_FILLET = 0.25               # lip inner top edge; inside the 0.3 mm the lip needs beyond its 1.0 mm span
FOAM_POCKET_D = R.FOAM_POCKET_D
FOAM_POCKET_H = R.FOAM_POCKET_H
PIN_D = 1.0
PIN_H = 0.55                    # < free foam proud (1.0): disengages when worn
TOP_Z = H


def ear_profile():
    """the shell's side profile (Y, Z) as a solid extruded across X: flat at H over the channel, then a
    quarter ellipse from the lip crest (horizontal tangent at y = SLEEVE_W / 2) down to END_H at the tips."""
    import math
    y1, y2, a = SLEEVE_W / 2, SHELL_L / 2, EAR_A
    r_ = math.sqrt(1 - ((y2 - y1) / a) ** 2)
    zc = (END_H - r_ * H) / (1 - r_)
    b = H - zc

    def ez(y):
        u = (abs(y) - y1) / a
        return zc + b * math.sqrt(max(0.0, 1 - u * u))
    yb = y2 + 0.5
    ys = [y1 + (yb - y1) * i / 30 for i in range(31)]
    right = Part.BSplineCurve()
    right.interpolate([V(0, y, ez(y)) for y in ys])
    left = Part.BSplineCurve()
    left.interpolate([V(0, -y, ez(y)) for y in reversed(ys)])
    edges = [left.toShape(), Part.LineSegment(V(0, -y1, H), V(0, y1, H)).toShape(), right.toShape(),
             Part.LineSegment(V(0, yb, ez(yb)), V(0, yb, -1)).toShape(), Part.LineSegment(V(0, yb, -1), V(0, -yb, -1)).toShape(),
             Part.LineSegment(V(0, -yb, -1), V(0, -yb, ez(yb))).toShape()]
    sol = Part.Face(Part.Wire(edges)).extrude(V(4 * SHELL_W, 0, 0))
    sol.translate(V(-2 * SHELL_W, 0, 0))
    return sol


def fillet_map(shape, radius, log=None, tag=''):
    """fillet with a radius per edge (radius(edge) -> r, 0 = none) in one OCC pass (Part::Fillet)."""
    edges = [(i + 1, r, r) for i, e in enumerate(shape.Edges) for r in (radius(e),) if r > 0]
    if not edges:
        return shape
    doc = FreeCAD.newDocument('pod_fillet')
    try:
        f = doc.addObject('Part::Feature', 'base')
        f.Shape = shape
        fil = doc.addObject('Part::Fillet', 'fillet')
        fil.Base = f
        fil.Edges = edges
        doc.recompute()
        out = fil.Shape.copy()
    finally:
        FreeCAD.closeDocument(doc.Name)
    if out.isNull() or not out.isValid() or len(out.Solids) != 1:
        if log:
            log(f"  fillet {tag} failed on {len(edges)} edges; left sharp")
        return shape
    return out


def build(log=None):
    w, L = SHELL_W, SHELL_L
    y1 = SLEEVE_W / 2
    s = R.rrect(w, L, PLAN_R, H, 0.0).common(ear_profile())
    # one fillet pass on the domes' side edges and the flat top's side edges (which become the lips'
    # sides); the crest seams are tangent (no fillet)
    dome = lambda e: e.BoundBox.ZMin > 1.2 and e.BoundBox.YLength > 1.0 and (e.BoundBox.YMin >= y1 - 0.05 or e.BoundBox.YMax <= -y1 + 0.05)
    flat = lambda e: e.BoundBox.ZMin > H - 0.02 and e.BoundBox.YLength > 1.0 and e.BoundBox.XLength < 0.05 and not dome(e)
    s = fillet_map(s, lambda e: EAR_SIDE_R if (dome(e) or flat(e)) else 0.0, log, 'top')
    s = R.fillet_edges(s, FACE_FILLET, lambda e: e.BoundBox.ZMax < 1e-6, log, 'face')
    # sleeve (through along X) and the open roof over the middle of the webbing
    s = s.cut(R.box(-w, w, -SLEEVE_W / 2, SLEEVE_W / 2, BASE_T, BASE_T + SLEEVE_H))
    yo = SLEEVE_W / 2 - RIM
    s = s.cut(R.box(-w, w, -yo, yo, BASE_T + SLEEVE_H - 0.2, H + 1))
    s = s.removeSplitter()
    if RIM_FILLET > 0:
        s = R.fillet_edges(s, RIM_FILLET, lambda e: e.BoundBox.ZMin > H - 0.02 and abs(abs(e.BoundBox.Center.y) - yo) < 0.05
                           and e.BoundBox.XLength > 1.0, log, 'lip rim')
    # foam pockets behind the pads
    for y in R.PAD_Y:
        s = s.cut(Part.makeCylinder(FOAM_POCKET_D / 2, FOAM_POCKET_H, V(0, y, 0)))
    # (no locating pins: the bonding jig's pins go through the flex holes; mech/rev_c/bond_jig.py)
    return s.removeSplitter()


if not getattr(sys, 'neurband_lib', False):
    log = R.Log('pod')
    shell = U.check(build(log), 'pod', log)
    bb = shell.BoundBox
    log(f"  pod shell {bb.XLength:.2f} x {bb.YLength:.2f} x {bb.ZLength:.2f} mm (W x L x H incl. pins); "
        f"top {TOP_Z:.2f} above the face, {TOP_Z + R.STACK_LOADED:.2f} above the skin worn")
    poly, gold, foam = R.flex_pod()
    web = R.box(-6, 6, -R.STRAP_W / 2, R.STRAP_W / 2, BASE_T + 0.05, BASE_T + 0.05 + R.STRAP_T)
    R.save('pod', [('pod', shell, R.C_POD)], log)
    R.save('pod_with_flex', [('pod', shell, R.C_POD), ('foam', Part.makeCompound(foam), R.C_FOAM),
                             ('flex', poly, R.C_FLEX), ('pads', Part.makeCompound(gold), R.C_GOLD),
                             ('webbing', web, R.C_STRAP)], log)
    R.fab('pod', 'Electrode pod shell rev C, TPU (6 per band)', shell, 14, 'fdm', 'tpu', 'black', log,
          extra={"notes": "TPU 95A, print on its side (channel vertical), no supports; 6 per band, 12 for two bands + 2 spares; "
                          "snap-in channel for the 20 mm strap; 6 x 2.0 mm EVA foam dots bought separately (docs/build/sourcing.md)"})
    R.finish(log)
