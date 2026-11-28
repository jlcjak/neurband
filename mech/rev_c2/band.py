"""band.py - the rev C2 band on the owner's wrist (assembly for looking at, not for printing).

Module (tub, lid, bars), six pods pressed flat on the skin, the flex along the skin and the 22 mm
strap in two halves: each sewn loop round its printed bar, down over the pods to a plain buckle
block under the wrist. Positions come from fit.py (wrist 'owner_flat').

Run: unset DISPLAY WAYLAND_DISPLAY; QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c2/band.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True
import FreeCAD, Part
import c2 as R
import params as P
import fit as F
import case as C
import pod as PD

V = FreeCAD.Vector
LIFT = P.TAPE_T + P.FLEX_T


def _ribbon(pts, y0, y1, thick, side=1.0, smooth=2):
    """Solid strip along a 2D polyline in XZ, thickened to one side, extruded along Y."""
    q = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, q[-1]) > 1e-6:
            q.append(p)
    for _ in range(smooth):
        nxt = [q[0]]
        for k in range(len(q) - 1):
            nxt.append((0.75 * q[k][0] + 0.25 * q[k + 1][0], 0.75 * q[k][1] + 0.25 * q[k + 1][1]))
            nxt.append((0.25 * q[k][0] + 0.75 * q[k + 1][0], 0.25 * q[k][1] + 0.75 * q[k + 1][1]))
        nxt.append(q[-1])
        q = nxt
    a, b = [], []
    for k in range(len(q)):
        p0, p1 = q[max(0, k - 1)], q[min(len(q) - 1, k + 1)]
        tx, tz = p1[0] - p0[0], p1[1] - p0[1]
        n = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / n * side, tx / n * side
        a.append(V(q[k][0], y0, q[k][1]))
        b.append(V(q[k][0] + nx * thick, y0, q[k][1] + nz * thick))
    return Part.Face(Part.makePolygon(a + b[::-1] + [a[0]])).extrude(V(0, y1 - y0, 0))


def wrist_solid(w, y0=-42.0, y1=58.0):
    secs = []
    for y in (y0, y0 / 2, 0.0, y1 / 2, y1):
        k = 1.0 + 0.09 * y / 70.0
        pts = [V(x * k, y, z * k) for x, z in w.pts[::60]][:-1]
        bs = Part.BSplineCurve()
        bs.interpolate(pts, PeriodicFlag=True)
        secs.append(Part.Wire(bs.toShape()))
    lo = Part.makeLoft(secs, True, False, False, 3)
    if lo.Volume < 0:
        lo.reverse()
    return lo


def build_band(w, log=None, with_wrist=True):
    d = F.design_c2()
    r = F.solve(w, d)
    z0 = r['z0']

    def mod(sh):
        return R.moved(sh, 0, 0, z0)
    tub = mod(C.build_tub())
    lid_parts = [(n, mod(s), c) for n, s, c in C.lid_materials(C.build_lid())]
    bars = mod(C.lug_bars_placed())
    sheet, gold_m, tail, strip = C.flex_solids()
    pod0, _ = PD.build_pod(travel=P.WING_D0)
    pad0, gold0 = PD.flex_on_pod()
    pods, flex, gold = [], [mod(sheet)], [mod(gold_m)]

    def put(src, pl, dst):
        for sh in (src if isinstance(src, list) else [src]):
            c = sh.copy()
            c.Placement = pl.multiply(c.Placement)
            dst.append(c)
    for k, pd in r['pods'].items():
        beta = -math.atan2(pd['t'][1], pd['t'][0])
        h = P.POD_HC + LIFT
        o = (pd['c'][0] + pd['n'][0] * h, pd['c'][1] + pd['n'][1] * h)
        pl = FreeCAD.Placement(V(o[0], 0, o[1]), FreeCAD.Rotation(V(0, 1, 0), math.degrees(beta)))
        put(pod0, pl, pods)
        put(pad0, pl, flex)
        put(gold0, pl, gold)

    # flex links along the skin between neighbouring paddles
    s_of = {k: pd['s'] for k, pd in r['pods'].items()}
    s_of[3], s_of[4] = w.s_of_x(P.PITCH / 2), w.s_of_x(-P.PITCH / 2)
    order = [1, 2, 3, 4, 5, 6, 7, 8]
    for a, b in zip(order, order[1:]):
        sa, sb = sorted((s_of[a], s_of[b]))
        sa, sb = sa + P.POD_W / 2 - 0.4, sb - P.POD_W / 2 + 0.4
        n = max(6, int((sb - sa) / 1.5))
        pts = []
        for i in range(n + 1):
            c, t_, nn = w.frame(sa + (sb - sa) * i / n)
            pts.append((c[0] + nn[0] * 0.05, c[1] + nn[1] * 0.05))
        flex.append(_ribbon(pts, P.SPINE_Y[0], P.SPINE_Y[1], P.FLEX_T, smooth=0))

    # strap: the taut line of fit.py is its skin-side face; split it under the wrist
    hull = [p for _, p in r['hull']]
    hw = P.STRAP_W / 2
    i_low = min(range(len(hull)), key=lambda i: hull[i][1])
    strap, loops = [], []
    for sx, pts in ((1, hull[:i_low + 1]), (-1, hull[i_low:][::-1])):
        side = 1.0 if sx > 0 else -1.0
        strap.append(_ribbon(pts, -hw, hw, P.STRAP_T, side=-side, smooth=1))
        xb, zb = P.XC + sx * (P.BODY_HX + P.PIN_DX), P.Z_BAR + z0
        g, t = 0.12, P.STRAP_T * 0.85
        ring = R.prism_xz([(xb + x, zb + z) for x, z in R.octagon(P.BAR_W / 2 + g + t, P.BAR_H / 2 + g + t, 0.9)], -hw, hw)
        ring = ring.cut(R.prism_xz([(xb + x, zb + z) for x, z in R.octagon(P.BAR_W / 2 + g, P.BAR_H / 2 + g, 0.45)], -hw - 1, hw + 1))
        loops.append(ring)
    pb = hull[i_low]
    buckle = R.box(pb[0] - 6.0, pb[0] + 6.0, -hw - 2.3, hw + 2.3, pb[1] - P.STRAP_T - 2.6, pb[1] - P.STRAP_T + 0.4)
    buckle = R.fillet_edges(buckle, 1.2, lambda e: e.BoundBox.YLength > 2 * hw)

    pod_solids = Part.makeCompound(pods)
    clash_pp = sum(R.clash(pods[i], pods[j]) for i in range(len(pods)) for j in range(i + 1, len(pods)))
    clash_tp = sum(R.clash(tub, p) for p in pods)
    if log:
        f = r['force']
        log(f"  {w.name}: case top {r['top_above_skin']:.2f} above the skin; module pull {f[3]:.2f} + {f[4]:.2f}, pods 1 2 5 6 7 8: "
            + ' '.join(f"{f[k]:.2f}" for k in (1, 2, 5, 6, 7, 8))
            + f"; lug to skin {r['lug_skin']:.2f}; strap room at pods 2 / 5: {r['room'][2][0]:.1f} / {r['room'][5][0]:.1f} mm; "
            + f"pod-pod clash {clash_pp:.3f}, tub-pod clash {clash_tp:.3f} mm3")
    items = [('tub', tub, R.C_TUB), *lid_parts, ('lug_bars', bars, R.C_BAR), ('pods', pod_solids, R.C_POD),
             ('strap', Part.makeCompound(strap + loops), R.C_STRAP), ('buckle', buckle, (0.13, 0.14, 0.16)),
             ('flex', Part.makeCompound(flex), R.C_FLEX), ('electrodes', Part.makeCompound(gold), R.C_GOLD)]
    if with_wrist:
        items.append(('wrist', wrist_solid(w), R.C_SKIN))
    return items


if not getattr(sys, 'neurband_band_lib', False):
    log = R.Log('band')
    for w in F.WRISTS:
        items = build_band(w, log)
        if w.name == 'owner_flat':
            R.save('band_assembly', items, log)
    R.finish(log)
