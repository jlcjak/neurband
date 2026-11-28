"""pod.py - neurband rev C2 pod (x6): strap clip + two spring wings + a rigid middle pad.

The pod is one profile, drawn here in the pod frame (u along the arm, h from the plate toward the
skin; the strap side is at negative h) and printed on its side, so the profile lies on the bed and
the 8 mm width is the print height. Printed that way each wing is a single bead per layer that runs
the whole length of the blade, and the two strap ears are closed loops of filament.

  middle pad  rigid T: the bias electrode sits on it. It sets how far the pod stands off the skin
              and stops the wings from being pushed past flat.
  wings       0.6 mm blades from beside the trunk, low under the cap, then up to a 6.6 mm flat.
              Free, each flat stands about 0.9 mm further out than the middle pad and leans toward
              the skin; pressed flat they are level with it. A bump under each tip is the hard stop.
  ears        clip over the edges of the 22 mm strap, which slides in them. Outer corners R2.

Run: unset DISPLAY WAYLAND_DISPLAY; QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c2/pod.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import c2 as R
import params as P

V = FreeCAD.Vector
ROOT_FILLET = 0.40
ARC_N = 10


def _poly_face(pts):
    q = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, q[-1]) > 1e-6:
            q.append(p)
    if math.dist(q[0], q[-1]) < 1e-6:
        q.pop()
    w = Part.makePolygon([V(0, u, h) for u, h in q] + [V(0, q[0][0], q[0][1])])
    return Part.Face(w)


def _offset_path(path, t):
    """Closed outline of a strip of thickness t around a centre line given as (u, h) points."""
    left, right = [], []
    for k, p in enumerate(path):
        a, b = path[max(0, k - 1)], path[min(len(path) - 1, k + 1)]
        tu, th = b[0] - a[0], b[1] - a[1]
        n = math.hypot(tu, th)
        nu, nh = -th / n, tu / n
        # mitre correction at corners keeps the thickness
        if 0 < k < len(path) - 1:
            a1 = math.atan2(p[1] - a[1], p[0] - a[0])
            a2 = math.atan2(b[1] - p[1], b[0] - p[0])
            c = math.cos((a2 - a1) / 2)
            s = 1.0 / max(c, 0.5)
        else:
            s = 1.0
        left.append((p[0] + nu * t / 2 * s, p[1] + nh * t / 2 * s))
        right.append((p[0] - nu * t / 2 * s, p[1] - nh * t / 2 * s))
    return left + right[::-1]


def _arc(c, r, a0, a1, n=ARC_N):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def wing_profile(sgn=1, travel=0.0):
    """Faces (in the pod's u-h plane, on the +u side; sgn mirrors) of one wing: blade, pad and stop.
    travel > 0 draws the wing pressed in by that much (for assemblies; the printed part is travel 0)."""
    t = P.WING_T
    (a, b, tilt) = P.wing_free(travel)
    b_free = P.wing_free()[1]
    tl = math.radians(tilt)
    half = P.WING_PAD_T / 2
    # pad: skin face from a to b, thickness toward the plate
    nu, nh = math.sin(tl), -math.cos(tl)                    # from the skin face into the pad
    pad = [a, b, (b[0] + nu * P.WING_PAD_T, b[1] + nh * P.WING_PAD_T), (a[0] + nu * P.WING_PAD_T, a[1] + nh * P.WING_PAD_T)]
    p_in = (a[0] + nu * half, a[1] + nh * half)             # pad mid plane at its inner end
    # blade centre line: root post, low arm, ramp; rounded where it turns
    r1 = 0.55
    u0, h0 = P.WING_ROOT_U, P.WING_ARM_H
    path = [(u0, -0.3), (u0, h0 - r1)] + _arc((u0 + r1, h0 - r1), r1, 180, 90)[1:]
    ang = math.atan2(p_in[1] - h0, p_in[0] - P.WING_RAMP_U0)
    r2 = 1.2
    d = r2 * math.tan(ang / 2)
    c2 = (P.WING_RAMP_U0 - d, h0 + r2)
    path += [(P.WING_RAMP_U0 - d, h0)] + _arc(c2, r2, -90, -90 + math.degrees(ang))[1:]
    # into the pad: stop inside it so the union is clean
    path += [(p_in[0] + 0.5 * math.cos(tl), p_in[1] + 0.5 * math.sin(tl))]
    blade = _offset_path(path, t)
    # root fillets on both sides of the post
    f = ROOT_FILLET
    fil = []
    for s in (1, -1):
        x = u0 + s * t / 2
        fil.append([(x, 0.0), (x + s * f, 0.0)] + _arc((x + s * f, f), f, 270, 180 if s > 0 else 360, 6)[1:] + [(x, f)])
    # hard stop under the tip
    travel_out = P.WING_STOP * P.WING_OUT
    h_stop = b_free[1] - P.WING_PAD_T - travel_out
    u1 = min(b_free[0] - 0.1, P.POD_SHELL_L / 2 - 1.6)
    stop = [(u1 - 1.3, 0.0), (u1, 0.0), (u1, h_stop), (u1 - 0.9, h_stop)]
    faces = [_poly_face(blade), _poly_face(pad), _poly_face(stop)] + [_poly_face(q) for q in fil]
    if sgn < 0:
        faces = [fc.mirror(V(0, 0, 0), V(0, 1, 0)) for fc in faces]
    return faces, dict(h_stop=h_stop, tip=b, inner=a, tilt=tilt)


def build_pod(log=None, travel=0.0):
    """Pod frame for the solid: X along the band (the print height), Y = u, Z = -h (skin at -Z, strap at +Z),
    so Z = 0 is the skin side of the plate, as in rev C1."""
    hw, hl = P.POD_SHELL_W / 2, P.POD_SHELL_L / 2
    ys = P.POD_STRAP_W / 2
    ye = ys - P.POD_EAR_IN
    zf = P.POD_FLOOR_T
    zs = zf + P.POD_SLOT_H
    zt = P.POD_H
    r = P.POD_EAR_R
    # plate + ears, in (u, h) with h negative on the strap side
    body = [(-hl + 0.5, 0.0), (hl - 0.5, 0.0), (hl, -0.5)]
    body += [(hl, -(zt - r))] + [(hl - r + r * math.cos(math.radians(a)), -(zt - r) - r * math.sin(math.radians(a))) for a in range(10, 91, 10)]
    body += [(ye + 0.3, -zt), (ye, -(zt - 0.3)), (ye, -(zs + 0.28)), (ye + 0.35, -zs), (ys, -zs), (ys, -zf), (-ys, -zf), (-ys, -zs),
             (-ye - 0.35, -zs), (-ye, -(zs + 0.28)), (-ye, -(zt - 0.3)), (-ye - 0.3, -zt)]
    body += [(-hl + r - r * math.cos(math.radians(a)), -(zt - r) - r * math.sin(math.radians(a))) for a in range(90, 9, -10)] + [(-hl, -(zt - r)), (-hl, -0.5)]
    faces = [_poly_face(body)]
    # rigid middle pad
    cap0 = P.POD_HC - P.POD_CAP_T
    tr, ch = P.POD_TRUNK_HX, P.POD_CAP_HX
    faces.append(_poly_face([(-tr, -0.2), (tr, -0.2), (tr, cap0 - 0.35), (tr + 0.35, cap0), (ch, cap0), (ch, P.POD_HC - 0.25), (ch - 0.25, P.POD_HC),
                             (-ch + 0.25, P.POD_HC), (-ch, P.POD_HC - 0.25), (-ch, cap0), (-tr - 0.35, cap0), (-tr, cap0 - 0.35)]))
    info = None
    for sgn in (1, -1):
        fs, info = wing_profile(sgn, travel)
        faces += fs
    solids = [fc.extrude(V(P.POD_SHELL_W, 0, 0)) for fc in faces]
    s = solids[0].fuse(solids[1:]).removeSplitter()
    s.translate(V(-hw, 0, 0))
    # h -> -Z
    s = s.mirror(V(0, 0, 0), V(0, 0, 1))
    return s, info


def flex_on_pod(travel=None):
    """Paddle, electrodes and tape on a pod pressed to `travel` (default: flat). Pod frame of build_pod."""
    travel = P.WING_D0 if travel is None else travel
    w = P.POD_W
    z = -(P.POD_HC + P.TAPE_T)
    pad = R.box(-w / 2, w / 2, -P.POD_L / 2, P.POD_L / 2, z - P.FLEX_T, z)
    for y in P.HOLE_Y:
        pad = pad.cut(Part.makeCylinder(P.HOLE_D / 2, 2, V(0, y, z - 1)))
    gold = [Part.makeCylinder(P.PAD_D / 2, 0.04, V(0, y, z - P.FLEX_T - 0.04)) for y in P.PAD_Y]
    return pad, gold


if not getattr(sys, 'neurband_lib', False):
    log = R.Log('pod')
    pod, info = build_pod(log)
    pod = R.check(pod, 'pod', log)
    bb = pod.BoundBox
    (a, b, tilt) = P.wing_free()
    log(f"  pod {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.2f} (free); plate {P.POD_FLOOR_T}, middle pad {P.POD_HC}, "
        f"wing flats {a[1]:.2f} .. {b[1]:.2f} above the plate ({tilt:.1f} deg), stop bump {info['h_stop']:.2f}")
    log(f"  worn: strap bed {P.POD_HC + P.POD_FLOOR_T:.2f} above the skin, pod top {P.POD_HC + P.POD_H:.2f}; "
        f"wing gap to the cap {P.POD_HC - P.POD_CAP_T - (P.WING_ARM_H + P.WING_T / 2):.2f}, to the plate {P.WING_ARM_H - P.WING_T / 2:.2f}, "
        f"to the trunk {P.WING_ROOT_U - P.WING_T / 2 - P.POD_TRUNK_HX:.2f}")
    printed = pod.copy()
    printed.rotate(V(0, 0, 0), V(0, 1, 0), -90)
    printed = R.on_bed(printed)
    bed, worst, flat = R.bed_report(printed)
    log(f"  on its side: bed contact {bed:.0f} mm2, steepest overhang {worst:.0f} deg, flat ceilings {flat[:3]}")
    R.save('pod', [('pod', pod, R.C_POD)], log)
    fl, gold = flex_on_pod()
    worn, _ = build_pod(travel=P.WING_D0)                 # as worn: both wings level with the middle pad
    R.save('pod_with_flex', [('pod', worn, R.C_POD), ('flex', fl, R.C_FLEX), ('electrodes', Part.makeCompound(gold), R.C_GOLD)], log)
    R.finish(log)
