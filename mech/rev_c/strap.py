"""strap.py - rev C strap: ONE continuous 25 mm elastic woven webbing (off the shelf, loop-fabric
face, e.g. 1 in elastic hook-and-loop-compatible band) around the whole wrist, outside the pods.

  ulnar end (A, -X): sewn around the integral bar hidden in the module's ulnar lug slot (fixed).
  radial end (B, +X): passes through the slim printed loop (strap_loop) that snaps onto the
      hidden radial bar, turns around the loop's far bar and folds back over its own outer face;
      a 40 mm sew-on hook tab on the end closes on the loop-fabric face. Opens fully, adjusts
      continuously over 145-180 mm.
  The webbing slides in the pod sleeves, so its stretch never loads the flex (the flex keeps the
  18 mm pitch) and the tension equalises.
Printed part: strap_loop (PA12). Bought: elastic webbing 25 x 1.2-1.5 mm, 25 mm sew-on hook tape.
The webbing itself is modelled as a smooth swept band (sweep_band) from the path in fit.py.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/strap.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import rc as R
import cadutil as U

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
STRAP_W, STRAP_T = R.STRAP_W, R.STRAP_T
LOOP_W = STRAP_W + 1.8          # overall along the arm (fits the 27.2 mm lug slot)
LINK_T = 0.7                    # side links outside the webbing edges
CLIP_RI, CLIP_RO = 0.95, 1.45   # C-clip around the 1.3 x 1.6 integral bar
CLIP_SLIT = 1.1                 # snaps over the bar's 1.3 mm side
LOOP_REACH = 4.2                # hinge axis -> far bar centre (short: keeps pod 5 loaded)
FAR_U, FAR_W = 1.3, 1.6         # far bar section (along the strap x thickness)
LOOP_T = 1.6
SEW_OVERLAP = 12.0
HOOK_L = 40.0
FOLD_MIN = 45.0                 # fold-back on the largest wrist (hook 40 + 5)


def build_loop():
    """Local frame: hinge axis = Y axis through the origin, the loop reaches along +X, thickness Z."""
    hw = LOOP_W / 2
    clip = Part.makeCylinder(CLIP_RO, LOOP_W, V(0, -hw, 0), V(0, 1, 0)).cut(
        Part.makeCylinder(CLIP_RI, LOOP_W + 2, V(0, -hw - 1, 0), V(0, 1, 0)))
    clip = clip.cut(R.box(-CLIP_RO - 1, 0, -hw - 1, hw + 1, -CLIP_SLIT / 2, CLIP_SLIT / 2))   # slit faces away
    links = [R.box(CLIP_RI, LOOP_REACH + FAR_U / 2, sy * hw - (LINK_T if sy > 0 else 0), sy * hw + (0 if sy > 0 else LINK_T),
                   -LOOP_T / 2, LOOP_T / 2) for sy in (-1, 1)]
    far = R.box(LOOP_REACH - FAR_U / 2, LOOP_REACH + FAR_U / 2, -hw, hw, -FAR_W / 2, FAR_W / 2)
    s = clip.fuse(links + [far]).removeSplitter()
    s = R.fillet_edges(s, 0.35, lambda e: e.BoundBox.XMin > CLIP_RO - 0.01 and e.BoundBox.YLength > 1.0, None, 'loop')
    return s


def placed_loop(hx, hz, ang, y):
    """Loop hinged on (hx, hz) at band line y, reaching along direction ang (rad, XZ plane)."""
    s = build_loop()
    s.rotate(V(0, 0, 0), V(0, 1, 0), -math.degrees(ang))
    s.translate(V(hx, y, hz))
    return s


def smooth(pts, n_iter=3):
    """Chaikin corner cutting of an open polyline (keeps the end points)."""
    for _ in range(n_iter):
        out = [pts[0]]
        for k in range(len(pts) - 1):
            (x0, z0), (x1, z1) = pts[k], pts[k + 1]
            out.append((0.75 * x0 + 0.25 * x1, 0.75 * z0 + 0.25 * z1))
            out.append((0.25 * x0 + 0.75 * x1, 0.25 * z0 + 0.75 * z1))
        out.append(pts[-1])
        pts = out
    return pts


def densify(pts, step=1.2):
    out = [pts[0]]
    for k in range(1, len(pts)):
        d = math.dist(pts[k - 1], pts[k])
        m = max(1, int(d / step))
        for j in range(1, m + 1):
            out.append((pts[k - 1][0] + (pts[k][0] - pts[k - 1][0]) * j / m, pts[k - 1][1] + (pts[k][1] - pts[k - 1][1]) * j / m))
    return out


def resample(pts, step=0.8):
    out = [pts[0]]
    acc = 0.0
    for k in range(1, len(pts)):
        d = math.dist(pts[k - 1], pts[k])
        acc += d
        if acc >= step:
            out.append(pts[k]); acc = 0.0
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out


def offset(pts, d):
    """Offset an open polyline by d along its left normal (travel direction rotated +90 deg)."""
    out = []
    for k in range(len(pts)):
        a, b = pts[max(k - 1, 0)], pts[min(k + 1, len(pts) - 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        n = math.hypot(tx, tz) or 1.0
        out.append((pts[k][0] - tz / n * d, pts[k][1] + tx / n * d))
    return out


def sweep_band(path, y, w=STRAP_W, t=STRAP_T, side=1, n_smooth=0):
    """Smooth webbing solid along a polyline (x, z) at band line y: B-spline faces interpolated
    through the (convex, taut) path points, so the band never cuts inside the path; thickness t
    centred on the path, width w along Y."""
    p = resample(smooth(path, n_smooth) if n_smooth else densify(path, 1.2), 0.8)
    if len(p) < 4:
        return None
    o, i = offset(p, side * t / 2), offset(p, -side * t / 2)
    def bs(q):
        c = Part.BSplineCurve()
        c.interpolate([V(x, y - w / 2, z) for x, z in q])
        return c.toShape()
    e_o, e_i = bs(o), bs(i)
    l0 = Part.makeLine(V(o[0][0], y - w / 2, o[0][1]), V(i[0][0], y - w / 2, i[0][1]))
    l1 = Part.makeLine(V(o[-1][0], y - w / 2, o[-1][1]), V(i[-1][0], y - w / 2, i[-1][1]))
    wire = Part.Wire(Part.__sortEdges__([e_o, l1, e_i, l0]))
    sol = Part.Face(wire).extrude(V(0, w, 0))
    if sol.Volume < 0:
        sol.reverse()
    return sol


def wrap(cx, cz, r_in, y, a0=0.0, a1=360.0, w=STRAP_W, t=STRAP_T):
    """Webbing wrapped around a bar of radius r_in (partial ring from a0 to a1 deg, XZ plane)."""
    ring = Part.makeCylinder(r_in + t, w, V(cx, y - w / 2, cz), V(0, 1, 0)).cut(
        Part.makeCylinder(r_in, w, V(cx, y - w / 2, cz), V(0, 1, 0)))
    if a1 - a0 >= 359:
        return ring
    L = 3 * (r_in + t)
    pts = [V(cx, y - w / 2 - 1, cz)]
    for k in range(9):
        a = math.radians(a0 + (a1 - a0) * k / 8)
        pts.append(V(cx + L * math.cos(a), y - w / 2 - 1, cz - L * math.sin(a)))
    pts.append(pts[0])
    wedge = Part.Face(Part.makePolygon(pts)).extrude(V(0, w + 2, 0))
    return ring.common(wedge)


if not getattr(sys, 'neurband_lib', False):
    log = R.Log('strap')
    loop = U.check(build_loop(), 'strap_loop', log)
    bb = loop.BoundBox
    log(f"  strap_loop {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm, opening "
        f"{LOOP_REACH - FAR_U / 2 - CLIP_RO:.1f} x {STRAP_W + 1.8 - 2 * LINK_T:.1f} mm")
    R.save('strap_loop', [('strap_loop', loop, R.C_POD)], log)
    R.fab('strap_loop', 'neurband rev C slim strap loop (snaps on the hidden radial bar)', loop, 4, 'mjf', 'pa12', 'black', log)
    R.finish(log)
