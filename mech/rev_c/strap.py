"""strap.py - rev C strap: ONE plain woven elastic webbing (rc.STRAP_W x rc.STRAP_T, no hook-and-loop,
no sewing, no glue) as a closed loop that is slipped over the hand.

  Both ends are anchored at the module by the same printed SLIDE (strap_slide, 2 per band), clipped onto
  the hidden bar in each module end. A slide is a two-bar slide: the hinge clip, one slot and a
  friction bar. Locking path (lock_paths, modelled in fit.py): the webbing comes from the pods UNDER
  the friction bar (skin side), goes UP through the slot, OVER the bar toward the pods, round the bar's
  pod-side end and back UNDER it, between the bar and the loaded strand; the tail tip stops at the slot.
  The loaded strand bends up into the slot round the bar's corner and pinches the tail tip against the
  bar with a force that grows with the load (self-locking), on top of about 360 deg of wrap friction.
  The slide pivots freely on its clip, so it swings until the loaded strand points at the hinge axis:
  about LOCK_SWING (41 deg) outward of the hinge-to-pod line. That lifts the bar clear of the flex edge
  link (one layer would fit under the unswung bar, two would not). The clip's opening (CLIP_OPEN_DEG)
  faces away from where the bar bears on it at that pose. Set once: untuck the tip, pull it to tighten,
  tuck it back under the bar; to loosen, untuck it and push webbing back through the slot.
  Why not a tri-glide / ladder lock at the module ends: there is 8.1-9.3 mm from the hidden bar to the
  pod 2/5 sleeve (fit.py), and a three-bar device for 1.6 mm webbing needs 9-12 mm. The two-bar slide
  needs 6.3 mm plus the webbing wrap.
  The webbing slides in the pod sleeves, so its stretch never loads the flex (the flex keeps the
  18 mm pitch) and the tension equalises.
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
LINK_T, LINK_H = 1.0, 2.0       # side links outside the webbing edges
LOOP_W = STRAP_W + 0.4 + 2 * LINK_T   # overall along the arm (22.4 for 20 mm webbing; module slot STRAP_W + 2.8)
CLIP_RI, CLIP_RO = 0.9, 1.9     # C-clip round the 1.3 x 1.6 stadium bar (1.0 mm wall)
CLIP_OPEN_DEG = None            # opening centre in the slide frame (local +X = toward the friction bar, +Z away
                                # from the wrist): set below to 130 - LOCK_SWING, so that on the swung slide it
                                # still faces the slot roof and the bar still bears 10 deg from its edge
CLIP_OPEN_HALF = 40.0           # half opening: chord 1.16 over the 1.3 bar = 0.14 snap; clears the slot roof when worn
CLIP_GAP = 1.2 + 0.4            # split round the module's centre rib (rc BAR_RIB 1.2)
SLIDE_GAP = R.STRAP_T_MAX + 0.1 # slot between the clip and the friction bar (one layer of webbing, 1.9)
FAR_U, FAR_W = 2.2, 2.4         # friction bar section (along the strap x thickness)
LOOP_REACH = CLIP_RO + SLIDE_GAP + FAR_U / 2   # hinge axis -> friction bar centre (5.15)
WRAP_R = FAR_W / 2              # webbing wrap radius round the friction bar (its thickness)
TAIL_L = 12.0                   # (rev C.1 tail allowance; the locking path length is computed by lock_paths)
LOOP_T = LINK_H
LOCK_CLR = 0.05                 # webbing to bar clearance in the modelled locking path
BAR_U0, BAR_FIL = CLIP_RO + SLIDE_GAP, 0.5     # friction bar from u 3.8 to 6.0, v +/-1.2, 0.5 fillets


def build_loop():
    """strap_slide. Local frame: hinge axis = Y axis through the origin, the slide reaches along +X,
    thickness Z. Split clip | slot | friction bar, joined by two side links."""
    hw = LOOP_W / 2
    clip = Part.makeCylinder(CLIP_RO, LOOP_W, V(0, -hw, 0), V(0, 1, 0)).cut(
        Part.makeCylinder(CLIP_RI, LOOP_W + 2, V(0, -hw - 1, 0), V(0, 1, 0)))
    c0, half = math.radians(CLIP_OPEN_DEG), math.radians(CLIP_OPEN_HALF)
    L_ = 3 * CLIP_RO
    pts = [V(0, -hw - 1, 0)] + [V(L_ * math.cos(c0 + t), -hw - 1, L_ * math.sin(c0 + t)) for t in (-half, 0.0, half)] + [V(0, -hw - 1, 0)]
    clip = clip.cut(Part.Face(Part.makePolygon(pts)).extrude(V(0, LOOP_W + 2, 0)))
    clip = clip.cut(R.box(-5, 5, -CLIP_GAP / 2, CLIP_GAP / 2, -5, 5))          # gap for the module's centre rib
    x_bar0 = CLIP_RO + SLIDE_GAP
    bar = R.box(x_bar0, x_bar0 + FAR_U, -hw, hw, -FAR_W / 2, FAR_W / 2)
    bar = R.fillet_edges(bar, 0.5, lambda e: e.BoundBox.YLength > 5.0, None, 'bar')
    links = [R.box(CLIP_RI + 0.2, x_bar0 + FAR_U, sy * hw - (LINK_T if sy > 0 else 0), sy * hw + (0 if sy > 0 else LINK_T),
                   -LINK_H / 2, LINK_H / 2) for sy in (-1, 1)]
    s = clip.fuse(links + [bar]).removeSplitter()
    return s


def placed_loop(hx, hz, ang, y, flip=False):
    """Loop hinged on (hx, hz) at band line y, reaching along direction ang (rad, XZ plane). flip turns
    the part over (the ulnar loop), so its opening still points up."""
    s = build_loop()
    if flip:
        s.rotate(V(0, 0, 0), V(1, 0, 0), 180)
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


def sweep_band(path, y, w=STRAP_W, t=STRAP_T, side=1, n_smooth=0, step=0.8):
    """Smooth webbing solid along a polyline (x, z) at band line y: B-spline faces interpolated
    through the (convex, taut) path points, so the band never cuts inside the path; thickness t
    centred on the path, width w along Y."""
    p = resample(smooth(path, n_smooth) if n_smooth else densify(path, min(1.2, 1.5 * step)), step)
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


def lock_geom(t=STRAP_T):
    """slide-frame (u along the slide from the hinge, v away from the wrist) numbers of the locking path."""
    u0, u1, hv = BAR_U0, BAR_U0 + FAR_U, FAR_W / 2
    uc0, uc1, vc = u0 + BAR_FIL, u1 - BAR_FIL, hv - BAR_FIL       # fillet centres (4.3 / 5.5, +/-0.7)
    r1 = BAR_FIL + LOCK_CLR + t / 2                              # first layer round a fillet (1.30)
    return dict(u0=u0, u1=u1, hv=hv, uc0=uc0, uc1=uc1, vc=vc, r1=r1, r2=r1 + t, us=u0 - LOCK_CLR - t / 2,
                v1=hv + LOCK_CLR + t / 2, v2=hv + LOCK_CLR + 1.5 * t)


def lock_swing(t=STRAP_T):
    """angle (rad) between the slide axis and the loaded strand when the strand's line passes through
    the hinge axis (the slide's free pivot): the strand bears on the tail tip's lower corner, which is
    where it pinches the tail against the bar."""
    g = lock_geom(t)
    vt = g['v1'] + t / 2
    return math.atan2(vt, g['uc0']) + math.asin((t / 2) / math.hypot(g['uc0'], vt))


LOCK_SWING = math.degrees(lock_swing())        # 41 deg
CLIP_OPEN_DEG = 130.0 - LOCK_SWING


def lock_paths(bar, d, n, p0, t=STRAP_T, step=0.25):
    """Centre line of the webbing end round one slide (band XZ plane), the locking path:
    incoming = from p0 (tangent point of the loaded strand on the outer layer under the bar) under the
    friction bar, up through the slot, over the bar to its pod-side end;
    tail = round the pod-side end and back under the bar (inner layer, between the bar and the loaded
    strand) to the tip at the slot edge, where the loaded strand bends up past it.
    bar: hinge axis (x, z); d: unit vector along the slide; n: unit normal away from the wrist."""
    g = lock_geom(t)
    P = lambda u, v: (bar[0] + u * d[0] + v * n[0], bar[1] + u * d[1] + v * n[1])
    def arc(cu, cv, r, a0, a1):
        k = max(2, int(abs(math.radians(a1 - a0)) * r / step) + 1)
        return [(cu + r * math.cos(math.radians(a0 + (a1 - a0) * j / k)), cv + r * math.sin(math.radians(a0 + (a1 - a0) * j / k)))
                for j in range(k + 1)]
    def line(a, b):
        k = max(1, int(math.dist(a, b) / step))
        return [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k + 1)]
    q = ((p0[0] - bar[0]) * d[0] + (p0[1] - bar[1]) * d[1], (p0[0] - bar[0]) * n[0] + (p0[1] - bar[1]) * n[1])
    vt = g['v1'] + t / 2                                         # tail tip's lower corner at (uc0, -vt)
    a0 = math.degrees(math.atan2(q[1] + vt, q[0] - g['uc0']))  # where the loaded strand meets it
    gam = math.degrees(math.asin((g['r1'] - t / 2) / (vt - g['vc'])))
    inc = [q] + arc(g['uc0'], -vt, t / 2, a0, -180.0 + gam)[1:]                # round the tail tip (the pinch)
    f0 = (g['uc0'] + g['r1'] * math.cos(math.radians(180 + gam)), -g['vc'] + g['r1'] * math.sin(math.radians(180 + gam)))
    inc += line(inc[-1], f0)[1:]
    inc += arc(g['uc0'], -g['vc'], g['r1'], 180.0 + gam, 180.0)[1:]
    inc += line((g['us'], -g['vc']), (g['us'], g['vc']))[1:]                   # up through the slot
    inc += arc(g['uc0'], g['vc'], g['r1'], 180.0, 90.0)[1:]
    inc += line((g['uc0'], g['v1']), (g['uc1'], g['v1']))[1:]                  # over the bar
    tail = arc(g['uc1'], g['vc'], g['r1'], 90.0, 0.0)                            # round its pod-side end
    tail += line((g['uc1'] + g['r1'], g['vc']), (g['uc1'] + g['r1'], -g['vc']))[1:]
    tail += arc(g['uc1'], -g['vc'], g['r1'], 0.0, -90.0)[1:]
    tail += line((g['uc1'], -g['v1']), (g['uc0'], -g['v1']))[1:]                # back under it to the tip
    return [P(*x) for x in inc], [P(*x) for x in tail]


def plen(pts):
    return sum(math.dist(pts[k - 1], pts[k]) for k in range(1, len(pts)))


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
    loop = U.check(build_loop(), 'strap_slide', log)
    bb = loop.BoundBox
    log(f"  strap_slide {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm, slot {SLIDE_GAP:.1f} x {LOOP_W - 2 * LINK_T:.1f} mm, "
        f"reach (hinge -> bar outer edge) {CLIP_RO + SLIDE_GAP + FAR_U:.2f} mm")
    # friction bar in bending, 20 N band tension, webbing wrapped round it -> ~2T, ends partly fixed (wL/10)
    T = 20.0
    span = LOOP_W - 2 * LINK_T
    M_ = 1.5 * T * span / 10            # load ~1.5 T: the standing part wraps it, the tail is only pinched
    S_ = FAR_W * FAR_U ** 2 / 6
    log(f"  friction bar: 1.5 T = {1.5 * T:.0f} N over {span:.1f} mm, M = {M_:.0f} N mm, S = {S_:.2f} mm3, sigma = {M_ / S_:.0f} MPa "
        f"(MJF PA12 ~48 MPa)")
    R.save('strap_slide', [('strap_slide', loop, R.C_POD)], log)
    R.fab('strap_slide', 'neurband rev C strap slide (2 per band, clips onto the hidden bars, anchors the webbing ends)',
          loop, 5, 'mjf', 'pa12', 'black', log)
    R.finish(log)
