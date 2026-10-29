"""bond_jig.py - rev C bonding jig: lay the flex on it, put foam dots in the pods and the base, press
each part into its nest. No hole punch, no needles, no tape.

Jig frame = world frame of the flex (docs/layout/flex_c_layout.md): X along the flex (pod k at
X = -45 + 18 (k - 1) developed), Y distal, Z up; the flex lies SKIN SIDE DOWN (pads down), z = 0 is
the plate top. The module base goes on underside down, turned 180 deg about Z from the module frame
(X_mech = -X, Y_mech = -Y).
- 16 pins (JIG_PIN_D) come up through the flex's 1.2 mm holes: they locate the flex;
- each free pod drops into a fence and stops on two ledges along its long edges, so its foam dots are
  pressed to POD_PRESS proud (about 40 % of the dots' proud height);
- the module section lies on a saddle matching the R42 underside (minus the flex and the pressed dots);
  the base drops into a fence and stops on four pads on the R42 surface outside the flex;
- gaps in the fences let the spine links and the tail through; the tail goes up through the base's
  floor slot before the base is lowered.
FDM (PETG/PLA, 0.2 mm layers, flat on the bed, no supports) or MJF PA12.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/bond_jig.py
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True
import FreeCAD, Part
import rc as R
import cadutil as U
import module as M
import pod as P

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
FLEX_REAL = 0.11                    # finished flex laminate (fab build)
JIG_PIN_D = 1.0                     # pins for the 1.2 mm holes
PIN_ABOVE = FLEX_REAL + 0.4         # pin top above the surface the flex lies on
POD_PRESS = 0.6                     # pod face stops this far above the flex (dots 1.0 proud -> 0.6)
MOD_PRESS = 1.0                     # module underside stops this far above the flex (dots 1.4 proud -> 1.0)
PLATE_T = 3.0
FENCE_T, FENCE_H, FENCE_CLR = 1.2, 2.5, 0.25
SPINE_GAP = (-1.4, 7.8)             # Y band kept open in fences/ledges for the spine links (spine -0.6..7.0)
POD_X_DEV = [-45.0 + 18.0 * k for k in range(R.N_PODS)]      # pods 1..8, developed along the flex
RS = M.R_U - MOD_PRESS - FLEX_REAL  # saddle radius (the flex lies on it)
TH_E = (R.POD_W / 2 + 9.0) / RS     # module-pod paddle outer edge (developed 12.55) as an angle
ZAX = -RS * math.cos(TH_E)          # saddle axis height: the saddle meets the plate at the paddle edges
X_E = RS * math.sin(TH_E)           # horizontal half-width of the saddle (12.35)


def x_of(xd):
    """developed flex X -> jig X (on the saddle for |xd| <= 12.55, flat beyond)"""
    a = abs(xd)
    if a <= R.POD_W / 2 + 9.0:
        return math.copysign(RS * math.sin(a / RS), xd)
    return math.copysign(X_E + a - (R.POD_W / 2 + 9.0), xd)


def z_saddle(x):
    return ZAX + math.sqrt(RS * RS - x * x)


def build():
    x0, x1 = x_of(POD_X_DEV[0]) - P.SHELL_W / 2 - 4, x_of(POD_X_DEV[-1]) + P.SHELL_W / 2 + 4
    plate = R.box(x0, x1, -21.0, 25.5, -PLATE_T, 0.0)
    # module zone: recess so the base's filleted X edges clear the plate; saddle on it
    mz = (-M.OUT_W / 2 - 1.5, M.OUT_W / 2 + 1.5, -M.OUT_L / 2 - 1.5 + 0.35, M.OUT_L / 2 + 1.5 + 0.35)
    plate = plate.cut(R.box(mz[0], mz[1], mz[2], mz[3], -0.8, 0.01))
    axis = V(-50, 0, ZAX)
    saddle = Part.makeCylinder(RS, 100, axis, V(1, 0, 0)) if False else Part.makeCylinder(RS, 40, V(0, -20, ZAX), V(0, 1, 0))
    saddle = saddle.common(R.box(-X_E, X_E, -R.POD_L / 2 - 0.5, R.POD_L / 2 + 0.5, -0.8, 5))
    s = plate.fuse(saddle)
    # base stop pads on the R42 surface (outside the flex paddles, outside the spine band)
    stop = Part.makeCylinder(M.R_U, 40, V(0, -20, ZAX), V(0, 1, 0))
    for sx in (-1, 1):
        for ya, yb in ((-15.0, SPINE_GAP[0]), (SPINE_GAP[1], 15.0)):
            pad = R.box(min(sx * 12.9, sx * 14.6), max(sx * 12.9, sx * 14.6), ya, yb, -0.8, 5).common(stop)
            s = s.fuse(pad)
    # base fence (world: X = -X_mech, Y = -Y_mech) with gaps for the links and the tail
    bx, by = -M.CX_OFF, -M.YC
    fo = R.rrect(M.OUT_W + 2 * (FENCE_CLR + FENCE_T), M.OUT_L + 2 * (FENCE_CLR + FENCE_T), M.PLAN_R + FENCE_CLR + FENCE_T, FENCE_H + 0.8, -0.8, bx, by)
    fi = R.rrect(M.OUT_W + 2 * FENCE_CLR, M.OUT_L + 2 * FENCE_CLR, M.PLAN_R + FENCE_CLR, FENCE_H + 2, -1.0, bx, by)
    fence = fo.cut(fi).cut(R.box(-60, 60, SPINE_GAP[0], SPINE_GAP[1], -2, 10)).cut(R.box(-6.0, 6.0, 10, 30, -2, 10))
    s = s.fuse(fence)
    # free pods: fence + two ledges each, pins
    for k, xd in enumerate(POD_X_DEV):
        if k in (2, 3):
            continue
        xc = x_of(xd)
        fo = R.rrect(P.SHELL_W + 2 * (FENCE_CLR + FENCE_T), P.SHELL_L + 2 * (FENCE_CLR + FENCE_T), P.PLAN_R + FENCE_CLR + FENCE_T, FENCE_H, 0.0, xc, 0)
        fi = R.rrect(P.SHELL_W + 2 * FENCE_CLR, P.SHELL_L + 2 * FENCE_CLR, P.PLAN_R + FENCE_CLR, FENCE_H + 2, -1.0, xc, 0)
        f = fo.cut(fi).cut(R.box(xc - 10, xc + 10, SPINE_GAP[0], SPINE_GAP[1], -2, 10))
        s = s.fuse(f)
        zl = FLEX_REAL + POD_PRESS
        for sx in (-1, 1):
            xa, xb = sorted((xc + sx * (R.POD_W / 2 + 0.15), xc + sx * (P.SHELL_W / 2 + FENCE_CLR)))
            for ya, yb in ((-P.SHELL_L / 2 + 1.5, SPINE_GAP[0]), (SPINE_GAP[1], P.SHELL_L / 2 - 1.5)):
                s = s.fuse(R.box(xa, xb, ya, yb, 0.0, zl))
    # pins: flat pods on the plate, module pods on the saddle (vertical)
    for xd in POD_X_DEV:
        xc = x_of(xd)
        zb = z_saddle(xc) if abs(xd) < 10 else 0.0
        for y in R.HOLE_Y:
            s = s.fuse(Part.makeCylinder(JIG_PIN_D / 2, PIN_ABOVE + 0.5, V(xc, y, zb - 0.5)))
    return s.removeSplitter()


if not getattr(sys, 'neurband_jig_lib', False):
    log = R.Log('bond_jig')
    jig = U.check(build(), 'bond_jig', log)
    bb = jig.BoundBox
    # check: the base (underside down, turned 180 deg) dropped on its stops must not hit the jig, and its
    # underside must stand MOD_PRESS above the flex over the pod 3/4 pads
    base = Part.read(os.path.join(R.HERE, 'module_base.step'))
    b2 = base.copy()
    b2.rotate(V(0, 0, 0), V(0, 0, 1), 180)
    b2.translate(V(0, 0, ZAX + M.R_U))          # module underside apex onto the stop radius
    pod = Part.read(os.path.join(R.HERE, 'pod.step'))
    p2 = pod.copy()
    p2.translate(V(x_of(27.0), 0, FLEX_REAL + POD_PRESS))
    chk = dict(base_vs_jig=round(b2.common(jig).Volume, 3), pod5_vs_jig=round(p2.common(jig).Volume, 3),
               saddle_crest_mm=round(ZAX + RS, 2), saddle_half_width_mm=round(X_E, 2),
               pod_x_on_jig=[round(x_of(x), 2) for x in POD_X_DEV])
    log("  bond jig: %.1f x %.1f x %.1f mm; checks %s" % (bb.XLength, bb.YLength, bb.ZLength, json.dumps(chk)))
    R.save('bond_jig', [('bond_jig', jig, (0.85, 0.85, 0.80))], log)
    R.save('bond_jig_fit', [('bond_jig', jig, (0.85, 0.85, 0.80)), ('module_base', b2, R.C_HOUSING), ('pod', p2, R.C_POD)], log)
    R.fab('bond_jig', 'neurband rev C bonding jig (flex + pods + module base; print once)', jig, 1, 'fdm', 'pla', 'white', log)
    R.finish(log)
