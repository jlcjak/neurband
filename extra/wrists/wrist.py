"""wrist.py - parametric forearm + simple hand for neurband fit checks (not ordered).

Frame: right forearm palm down. X radial(+)/ulnar(-), Y along the arm (hand toward -Y = front,
elbow +Y), Z dorsal(+) up. Wrist crease at y = 0. Sizes are wrist circumference at the band
position (BAND_Y mm proximal of the crease, see mech/fitgeom.py).
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad extra/wrists/wrist.py
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
MECH = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'mech')
sys.path.insert(0, MECH)
import FreeCAD, Part
import fitgeom as G
import cadutil as U

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
SIZES = {'140': 140.0, '145': 145.0, '160': 160.0, '180': 180.0, '200': 200.0}   # wrist circumference at band (145: rev C)
FOREARM_LEN = G.FOREARM_LEN        # 70 mm proximal of the crease
FOREARM_STATIONS = [0, 10, 22, 35, 50, 70]
HAND_BREADTH_M = 84.0              # knuckle breadth for a 160 mm wrist
HAND_BREADTH_SLOPE = 0.25          # mm breadth per mm wrist circumference
HAND_DEPTH_RATIO = 0.36            # knuckle depth / breadth
PALM_LEN_M = 100.0                 # crease -> knuckles for a 160 mm wrist
PALM_LEN_SLOPE = 0.30
FINGER_LEN = 75.0
THUMB_R = 10.5
THUMB_LEN = 52.0


def hand_dims(c):
    hb = HAND_BREADTH_M + HAND_BREADTH_SLOPE * (c - 160.0)
    hd = HAND_DEPTH_RATIO * hb
    pl = PALM_LEN_M + PALM_LEN_SLOPE * (c - 160.0)
    return hb, hd, pl


def ell(a, b, y, z0=0.0, n=48):
    """Closed periodic B-spline through an ellipse (a along X, b along Z) in the plane at y."""
    pts = [V(a * math.cos(2 * math.pi * k / n), y, z0 + b * math.sin(2 * math.pi * k / n)) for k in range(n)]
    bs = Part.BSplineCurve()
    bs.interpolate(pts, PeriodicFlag=True)
    return Part.Wire(bs.toShape())


def build(c):
    hb, hd, pl = hand_dims(c)
    # hand: finger block tip -> knuckles -> mid palm -> crease (lofted separately from the forearm)
    a0, b0 = G.section(c, 0.0)
    hand = [ell(0.40 * hb, 0.30 * hd, -pl - FINGER_LEN, -1.5),
            ell(hb / 2, hd / 2, -pl),
            ell(0.47 * hb, 0.52 * hd, -0.55 * pl),
            ell(a0, b0, 0.0)]
    fore = [ell(*G.section(c, y), float(y)) for y in FOREARM_STATIONS]
    parts = []
    for secs in (hand, fore):
        lo = Part.makeLoft(secs, True, False, False, 3)
        if lo.Volume < 0:
            lo.reverse()
        parts.append(lo)
    arm = parts[0].fuse(parts[1])
    # thumb hint on the radial (+X) side of the palm, pointing distally and outward
    a, b = G.section(c, 0.0)
    base = V(0.34 * hb, -0.28 * pl, -0.12 * hd)
    d = V(0.42, -0.85, -0.25)
    d.normalize()
    th = Part.makeCylinder(THUMB_R, THUMB_LEN, base, d)
    th = th.fuse(Part.makeSphere(THUMB_R, base + d * THUMB_LEN))
    th = th.fuse(Part.makeSphere(THUMB_R * 1.15, base))
    shape = arm.fuse(th).removeSplitter()
    if shape.Volume < 0:
        shape.reverse()
    girth = G.ellipse_perimeter(hb / 2, hd / 2)
    return shape, dict(hand_breadth=hb, hand_depth=hd, knuckle_girth=girth, palm_len=pl)


if not getattr(sys, 'neurband_lib', False):
    log = U.Log('wrist')
    for name, c in SIZES.items():
        s, info = build(c)
        U.check(s, f'wrist_{name}', log)
        a, b = G.section(c, G.BAND_Y)
        log(f"  wrist_{name}: band C={c} a={a:.1f} b={b:.1f}  hand breadth {info['hand_breadth']:.1f} "
            f"depth {info['hand_depth']:.1f} knuckle girth {info['knuckle_girth']:.0f} mm")
        U.save(f'wrist_{name}', [(f'wrist_{name}', s, U.C_SKIN)], log, folder=HERE)
    U.finish(log)
