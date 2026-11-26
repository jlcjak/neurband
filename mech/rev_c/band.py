"""band.py - neurband rev C (22 mm Nylon Classic strap + 100% 3D-printed lug bars + open-back side-ear clip pods).

pod           Sleek open-back side-ear clip pod (x6, 8.0 x 30.2 mm; 1.26 mm thick across the 17.4 mm open
              centre, 4.46 mm only at the two +/-Y edge C-clips). Prints on its flat X = -4.0 mm side edge
              so continuous filament loops wrap around both C-ears (zero supports, zero bridges).
              Lets the 22 mm strap slide freely ~5.2 mm relative to the inelastic flex as the band bends!
bond_jig      Flat alignment jig: seats the cradle and the six pods (with side-ear clearance pockets) on
              stepped pins through the flex's 1.2 mm alignment holes while pressing the flex onto 24 foam dots.
band_assembly Detailed CAD of the full wearable on the owner's 157 mm wrist:
                - compact 31.0 x 35.0 mm cradle + holder + buttonless lid + 3D-printed slide-in lug bars,
                - sewn 22 mm nylon lug loops (with factory QuickFit clips popped off),
                - 92 mm woven nylon buckle half (-X lug -> Pods 5, 6, 7, 8 -> volar tang buckle),
                - 125 mm woven nylon hole half (+X lug -> Pods 2, 1 -> 12 cut-through oval tang holes,
                  buckled through Hole #3 and tucked over the ear clips through two keeper loops).

Run: unset DISPLAY WAYLAND_DISPLAY; QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/band.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True

import FreeCAD, Part
import rc as R
import params as P
import cadutil as U
import fit as F
import module as M

V = FreeCAD.Vector
BAND_Y = 0.0

# ---------------- jig layout ----------------
JIG_T = 3.0
JIG_MARGIN = 3.0
SEAT_H = 1.6                                         # raised flat pedestals for the 1.26 mm pod plates
PIN_D0, PIN_D1 = P.POD_PIN_HOLE_D - 0.25, P.HOLE_D - 0.20
JIG_POD_T = 1.10                                     # released tool, pin shoulder measured from pedestal
PIN_UP = 1.7                                         # pin height above pod skin face
TAIL_CHAN = (-5.9, 5.9, 2.4)


def jig_pod_x():
    """Released jig pin stations, measured on the saved pre-revision jig STEP."""
    x2 = 26.606193
    xs = {2: x2, 1: x2 + P.PITCH}
    for k in range(5, 9):
        xs[k] = -x2 - (k - 5) * P.PITCH
    return xs


def _teardrop_z(r, y, z0, z1):
    """Cylinder of radius r along Z (from z0 to z1) at (0, y) with a 45-deg teardrop crown toward +X
    so the hole prints with <=45 deg overhang and 0 mm bridge when X = -POD_SHELL_W/2 lies on the bed."""
    cyl = Part.makeCylinder(r, z1 - z0, V(0, y, z0))
    s2 = math.sqrt(0.5)
    pts = [V(r * s2, y - r * s2, z0), V(r * math.sqrt(2.0), y, z0), V(r * s2, y + r * s2, z0), V(0.0, y, z0)]
    roof = Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, z1 - z0))
    return cyl.fuse(roof)


# ---------------- sleek open-back side-ear clip pod (x6, zero glue) ----------------
def build_pod(log=None):
    """Pod frame: Z = 0 is the skin-side plastic face (foam dimples cut into +Z), Z = POD_FLOOR_T is the
    strap bed across the 17.4 mm open centre, and +/-Y C-ears (Z = 1.26..4.46) clip around the 22 mm strap edges
    so the strap slides freely along X without buckling the flex."""
    hw = P.POD_SHELL_W / 2                              # 4.00
    hl = P.POD_SHELL_L / 2                              # 15.10
    ys = P.POD_STRAP_W / 2
    ye = ys - P.POD_EAR_IN
    zf = P.POD_FLOOR_T
    zs = zf + P.POD_SLOT_H
    zt = P.POD_H
    yz_pts = [
        (-hl + 0.35, 0.0), (hl - 0.35, 0.0),
        (hl, 0.35), (hl, zt - 0.45), (hl - 0.45, zt),
        (ye + 0.30, zt), (ye, zt - 0.30), (ye, zs + 0.28), (ye + 0.35, zs),
        (ys, zs), (ys, zf),
        (-ys, zf), (-ys, zs),
        (-ye - 0.35, zs), (-ye, zs + 0.28), (-ye, zt - 0.30), (-ye - 0.30, zt),
        (-hl + 0.45, zt), (-hl, zt - 0.45), (-hl, 0.35),
    ]
    s = R.prism_yz(yz_pts, -hw, hw)
    # Soften +X top skin edge slightly (X = -hw stays dead flat on the print bed!)
    s = R.chamfer_edges(s, 0.28, lambda e: e.BoundBox.XMin > hw - 1e-4 and e.BoundBox.ZMax < 0.05, log, 'pod +X skin edge')
    # 3 foam-dot dimples on the skin face (Z = 0 .. +0.30, teardrop toward +X for 45-deg printability)
    for y in P.PAD_Y:
        s = s.cut(_teardrop_z(P.FOAM_POCKET_D / 2, y, -0.5, P.FOAM_POCKET_H))
    # 2 alignment pinholes through the 1.26 mm floor
    for y in P.HOLE_Y:
        s = s.cut(_teardrop_z(P.POD_PIN_HOLE_D / 2, y, -0.5, zf + 0.5))
    return s.removeSplitter()


# ---------------- bonding jig ----------------
def build_jig(log=None):
    xs = jig_pod_x()
    x0 = xs[8] - P.POD_SHELL_W / 2 - JIG_MARGIN
    x1 = xs[1] + P.POD_SHELL_W / 2 + JIG_MARGIN
    hy = P.BODY_HY + JIG_MARGIN
    j = R.box(x0, x1, -hy, hy, -JIG_T, 0.0)
    j = R.fillet_edges(j, 3.0, lambda e: e.BoundBox.ZLength > JIG_T - 0.01, log, 'jig corners')
    # two tongues that locate the cradle by its strap bays (between the lug ears)
    for sx in (1, -1):
        xa = M.XC + sx * (P.BODY_HX + 0.25)
        xb = M.XC + sx * (P.LUG_HX - 0.4)
        j = j.fuse(R.box(min(xa, xb), max(xa, xb), -P.SLOT_W / 2 + 0.35, P.SLOT_W / 2 - 0.35, -0.1, 1.5))
    # asymmetric key in the cradle's wire bay so cradle only seats one way round
    kx0, kx1, ky0, ky1, kd = M.WIRE_BAY
    j = j.fuse(R.box(kx0 + 0.25, kx1 - 0.25, -ky1 + 0.25, -ky0 - 0.25, -0.1, kd - 0.3))
    # tail ramp & channel
    tx0, tx1, td = TAIL_CHAN
    ys = -(M.TAIL_SLOT[2] + M.TAIL_SLOT[3]) / 2
    j = j.cut(R.prism_yz([(ys - 1.3, 1.0), (ys - 1.3, -0.5), (ys + 1.2, -td), (hy + 1, -td), (hy + 1, 1.0)], tx0, tx1))
    # centre pedestals (between +/-Y ears) + side-ear clearance pockets + stepped alignment pins for the 6 pods
    ye_in = P.POD_STRAP_W / 2 - P.POD_EAR_IN - 0.35     # 8.35 mm half-width fits inside 17.4 mm open back
    ye_out = P.POD_SHELL_L / 2 + 0.35                   # 15.45 mm outer clearance for C-ears
    z_ear_bot = (SEAT_H + P.POD_FLOOR_T) - P.POD_H - 0.30   # -1.90 mm pocket floor (1.10 mm solid jig base below)
    for k, x in xs.items():
        for sy in (1, -1):
            j = j.cut(R.box(x - P.POD_SHELL_W / 2 - 0.30, x + P.POD_SHELL_W / 2 + 0.30,
                            min(sy * ye_in, sy * ye_out), max(sy * ye_in, sy * ye_out), z_ear_bot, 0.5))
        j = j.fuse(R.box(x - P.POD_SHELL_W / 2 + 0.2, x + P.POD_SHELL_W / 2 - 0.2, -ye_in, ye_in, -0.1, SEAT_H))
        for y in P.HOLE_Y:
            j = j.fuse(Part.makeCylinder(PIN_D0 / 2, JIG_POD_T + 0.1, V(x, y, SEAT_H - 0.1)))
            j = j.fuse(Part.makeCone(PIN_D0 / 2, PIN_D1 / 2, 0.5, V(x, y, SEAT_H + JIG_POD_T)))
            j = j.fuse(Part.makeCylinder(PIN_D1 / 2, PIN_UP - 0.5, V(x, y, SEAT_H + JIG_POD_T + 0.5)))
    for sy in (1, -1):
        j = j.cut(Part.makeCylinder(6.0, JIG_T + 1, V(M.XC, sy * (hy + 1.5), -JIG_T - 0.5)))
    return j.removeSplitter()


def jig_fit(jig, cradle, pod):
    xs = jig_pod_x()
    placed = []
    for k, x in xs.items():
        p = pod.copy()
        p.rotate(V(0, 0, 0), V(1, 0, 0), 180)                # open back down on pedestal, dimples up, ears in pockets
        p.translate(V(x, 0, SEAT_H + P.POD_FLOOR_T))
        placed.append(p)
    c = cradle.copy()
    c.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    return c, placed, R.clash(jig, c), sum(R.clash(jig, p) for p in placed), sum(R.clash(c, p) for p in placed)


def jig_flex():
    xs = jig_pod_x()
    pad0, gold0, foam0 = R.flex_pod_visual(P.FOAM_WORN)
    flex, gold, foam = [], [], []

    def put(pl):
        for src, dst in ((pad0, flex), (gold0, gold), (foam0, foam)):
            for sh in (src if isinstance(src, list) else [src]):
                c = sh.copy()
                c.Placement = pl.multiply(c.Placement)
                dst.append(c)
    flip = FreeCAD.Rotation(V(1, 0, 0), 180)
    zp_top = SEAT_H + P.POD_FLOOR_T
    for k, x in xs.items():
        put(FreeCAD.Placement(V(x, 0, zp_top), flip))
    zf = -P.DIMPLE_Z
    for sx in (1, -1):
        put(FreeCAD.Placement(V(sx * P.DIMPLE_X, 0, zf), FreeCAD.Rotation(V(0, 1, 0), math.degrees(-sx * P.POD_TILT)).multiply(flip)))
    ya, yb = -P.SPINE_Y[1], -P.SPINE_Y[0]
    zp = zp_top + P.FOAM_WORN
    for a, b in ((8, 7), (7, 6), (6, 5), (2, 1)):
        flex.append(R.box(xs[a] + P.POD_W / 2 - 0.3, xs[b] - P.POD_W / 2 + 0.3, ya, yb, zp, zp + P.FLEX_T))
    on_facet = P.POD_ARC + P.POD_W / 2 - P.BEND_X
    xe = P.BEND_X + on_facet * math.cos(P.POD_TILT)
    ze = -P.facet_z(xe) + P.FOAM_WORN
    for sx, k in ((1, 2), (-1, 5)):
        x0, x1 = sx * (xe - 0.3), xs[k] - sx * (P.POD_W / 2 - 0.3)
        flex.append(_ribbon([(x0, ze), ((x0 + x1) / 2, (ze + zp) / 2 + 0.25), (x1, zp)], ya, yb, P.FLEX_T, side=sx * 1.0, smooth=2))
    zr = -P.facet_z(P.BEND_X) + P.FOAM_WORN
    flex.append(R.box(-P.BEND_X - 0.2, P.BEND_X + 0.2, 3.0, P.POD_L / 2, zr, zr + P.FLEX_T))
    flex.append(R.box(-P.BEND_X - 0.2, P.BEND_X + 0.2, ya, yb, zr, zr + P.FLEX_T))
    w2 = P.TAIL_W / 2
    ys = -(M.TAIL_SLOT[2] + M.TAIL_SLOT[3]) / 2
    flex.append(R.prism_yz([(P.POD_L / 2, zr), (ys - 0.1, zr), (ys - 0.1, -0.6), (ys + 1.4, -TAIL_CHAN[2] + 0.1),
                            (ys + 6.5, -TAIL_CHAN[2] + 0.1), (ys + 6.5, -TAIL_CHAN[2] + 0.4), (ys + 1.5, -TAIL_CHAN[2] + 0.4),
                            (ys + 0.2, -0.5), (ys + 0.2, zr + P.FLEX_T), (P.POD_L / 2, zr + P.FLEX_T)], -w2, w2))
    return flex, gold, foam


# ---------------- geometry helpers for detailed 22 mm strap ----------------
def _ribbon(pts, y0, y1, thick, side=1.0, smooth=2):
    """Solid strip following a 2D polyline in XZ, extruded along Y from y0 to y1."""
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
    loop = a + b[::-1] + [a[0]]
    return Part.Face(Part.makePolygon(loop)).extrude(V(0, y1 - y0, 0))


def _poly_resample(pts, step=0.75):
    """Uniform arc-length table [(s, (x, z), (tx, tz), (nx_out, nz_out))] along a clockwise wrist path."""
    dense = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        d = math.dist(a, b)
        n = max(1, int(math.ceil(d / step)))
        for k in range(1, n + 1):
            f = k / n
            dense.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])))
    # Light smoothing so tangent/normal vectors vary smoothly over pod edges
    for _ in range(3):
        dense = [dense[0]] + [((dense[i - 1][0] + 2 * dense[i][0] + dense[i + 1][0]) / 4,
                               (dense[i - 1][1] + 2 * dense[i][1] + dense[i + 1][1]) / 4)
                              for i in range(1, len(dense) - 1)] + [dense[-1]]
    out, s = [], 0.0
    for i, p in enumerate(dense):
        if i > 0:
            s += math.dist(dense[i - 1], p)
        p0, p1 = dense[max(0, i - 1)], dense[min(len(dense) - 1, i + 1)]
        tx, tz = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(tx, tz) or 1.0
        tx, tz = tx / L, tz / L
        # For clockwise path (+X -> volar -> -X), outward normal is (-tz, tx); for CCW (-X -> volar -> +X) flip when needed
        out.append((s, p, (tx, tz), (-tz, tx)))
    return out


def _at_arc(tab, s_target):
    """Interpolate (point, tangent, normal) at arc-length s_target along a resampled table."""
    if s_target <= 0:
        return tab[0][1], tab[0][2], tab[0][3]
    if s_target >= tab[-1][0]:
        return tab[-1][1], tab[-1][2], tab[-1][3]
    for i in range(len(tab) - 1):
        s0, p0, t0, n0 = tab[i]
        s1, p1, t1, n1 = tab[i + 1]
        if s0 <= s_target <= s1:
            f = (s_target - s0) / max(s1 - s0, 1e-9)
            p = (p0[0] + f * (p1[0] - p0[0]), p0[1] + f * (p1[1] - p0[1]))
            tx, tz = t0[0] + f * (t1[0] - t0[0]), t0[1] + f * (t1[1] - t0[1])
            L = math.hypot(tx, tz) or 1.0
            tx, tz = tx / L, tz / L
            return p, (tx, tz), (-tz, tx)
    return tab[-1][1], tab[-1][2], tab[-1][3]


def build_sewn_lug_loop(xp, zp, sx, p_first):
    """Sewn 22 mm woven nylon loop (QuickFit clip removed) wrapping 360 deg around the printed
    slide-in cross-bar at (xp, zp), folding back on top of the strap with two stitched bar-tack seams!"""
    t = P.STRAP_T * 0.85                                    # nylon compresses slightly in the sewn fold (~1.57 mm)
    hw_s = P.STRAP_W / 2                                    # 13.0 mm
    hw_b, hh_b = P.BAR_W / 2 + 0.12, P.BAR_H / 2 + 0.12
    dx, dz = p_first[0] - (xp + sx * hw_b), p_first[1] - (zp - hh_b)
    L = math.hypot(dx, dz) or 1.0
    tx, tz = dx / L, dz / L
    # Outward normal from wrist along launch tangent
    nx, nz = (-tz, tx) if sx > 0 else (tz, -tx)

    # Outer wrap loop going from under the bar -> inner gap -> over the bar -> folded collar on top (8.5 mm long)
    collar_len = 8.2
    p_under = (xp + sx * hw_b, zp - hh_b)
    p_end_in = (p_under[0] + tx * collar_len + nx * P.STRAP_T, p_under[1] + tz * collar_len + nz * P.STRAP_T)
    p_end_out = (p_end_in[0] + nx * t, p_end_in[1] + nz * t)
    loop_poly = [
        (xp + sx * hw_b, zp - hh_b - 0.1),
        (xp - sx * hw_b, zp - hh_b - 0.1),
        (xp - sx * hw_b, zp + hh_b),
        (xp + sx * hw_b, zp + hh_b),
        p_end_in,
        p_end_out,
        (xp + sx * (hw_b + t * 0.8), zp + hh_b + t),
        (xp - sx * (hw_b + t), zp + hh_b + t),
        (xp - sx * (hw_b + t), zp - hh_b - t * 0.85),
        (xp + sx * hw_b, zp - hh_b - t * 0.85),
    ]
    collar = R.prism_xz(loop_poly, BAND_Y - hw_s, BAND_Y + hw_s)

    # Two stitched bar-tack seams across the folded collar
    stitches = []
    for d_s in (2.5, 6.6):
        ps0 = (p_under[0] + tx * (d_s - 0.5) + nx * (P.STRAP_T + t - 0.05),
               p_under[1] + tz * (d_s - 0.5) + nz * (P.STRAP_T + t - 0.05))
        ps1 = (p_under[0] + tx * (d_s + 0.5) + nx * (P.STRAP_T + t - 0.05),
               p_under[1] + tz * (d_s + 0.5) + nz * (P.STRAP_T + t - 0.05))
        stitches.append(_ribbon([ps0, ps1], BAND_Y - hw_s + 1.1, BAND_Y + hw_s - 1.1, 0.38,
                                side=1.0 if sx > 0 else -1.0, smooth=0))
    return collar, stitches, p_under


def build_tang_buckle(pb, tb, nb):
    """Detailed matte-black PVD tang buckle frame + angled tongue pin passing through Hole #3."""
    # Frame local axes: u along strap (+X -> -X clockwise or along buckle half toward tip), v outward normal, y across
    tx, tz = tb
    vx, vz = nb

    def B(u, y, v):
        return V(pb[0] + u * tx + v * vx, BAND_Y + y, pb[1] + u * tz + v * vz)

    hw_out = P.STRAP_W / 2 + 2.3                        # 15.30 (30.6 mm outer width)
    hw_in = P.STRAP_W / 2 + 0.25                        # buckle loop inside clearance
    # Curved side-rail profile from u = -1.5 (hinge bar) to u = +11.2 (front lip)
    prof_out = [(-2.0, -0.4), (-2.0, 2.0), (4.5, 3.2), (11.4, 2.8), (11.8, 0.9), (9.8, 0.4), (4.5, 0.9), (-0.5, -0.4)]
    rail_face = Part.Face(Part.makePolygon([B(u, -hw_out, v) for u, v in prof_out] + [B(prof_out[0][0], -hw_out, prof_out[0][1])]))
    frame = rail_face.extrude(V(0, 2 * hw_out, 0))
    # Cut central window (u = 0.6 .. 8.8, y = -hw_in .. +hw_in) so the 125 mm strap passes cleanly through!
    win = Part.Face(Part.makePolygon([B(0.6, -hw_in, -2.0), B(0.6, -hw_in, 5.0), B(8.8, -hw_in, 5.0),
                                      B(8.8, -hw_in, -2.0), B(0.6, -hw_in, -2.0)])).extrude(V(0, 2 * hw_in, 0))
    frame = frame.cut(win)
    # Cylindrical rear hinge bar at (u = 0.0, v = 0.8)
    hinge = Part.makeCylinder(0.95, 2 * hw_out - 0.4, B(0.0, -hw_out + 0.2, 0.8), V(0, 1, 0))
    frame = frame.fuse(hinge)
    # Angled center tang tongue (u = 0.0, v = 0.8 -> pokes up through the hole strap to rest on front bar at u = 10.2, v = 2.5!)
    p_a, p_b = B(0.0, -1.6, 0.8), B(10.3, -1.6, 2.55)
    tang_pts = [B(-0.4, -1.5, 0.4), B(0.0, -1.5, 1.5), B(10.4, -1.5, 3.05), B(10.6, -1.5, 2.15), B(0.2, -1.5, 0.2)]
    tang = Part.Face(Part.makePolygon(tang_pts + [tang_pts[0]])).extrude(V(0, 3.0, 0))
    # Subtle notch in front bar for the tang tip
    frame = frame.fuse(tang).removeSplitter()
    return frame


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
    d = F.design_new()
    r = F.solve(w, d)
    z0 = r['z0']

    def mod(sh):
        c = sh.copy()
        c.translate(V(0, BAND_Y, z0))
        return c

    cradle, holder = mod(M.build_cradle()), mod(M.build_holder())
    pins = mod(M.lug_pins_visual())
    pcb, parts = M.board_real()
    bat, pcm, _ = M.battery_solids()
    pod0 = build_pod()
    pad0, gold0, foam0 = R.flex_pod_visual(P.FOAM_WORN)

    pods, flex, gold, foam = [], [], [], []

    def put(src, pl, dst):
        for sh in (src if isinstance(src, list) else [src]):
            c = sh.copy()
            c.Placement = pl.multiply(c.Placement)
            dst.append(c)

    for k, pd in r['pods'].items():
        beta = -math.atan2(pd['t'][1], pd['t'][0])
        o = (pd['c'][0] + pd['n'][0] * P.STANDOFF, pd['c'][1] + pd['n'][1] * P.STANDOFF)
        pl = FreeCAD.Placement(V(o[0], BAND_Y, o[1]), FreeCAD.Rotation(V(0, 1, 0), math.degrees(beta)))
        put(pod0, pl, pods)
        put(pad0, pl, flex); put(gold0, pl, gold); put(foam0, pl, foam)

    for sx in (1, -1):
        beta = sx * P.POD_TILT
        pl = FreeCAD.Placement(V(sx * P.DIMPLE_X, BAND_Y, P.DIMPLE_Z + z0), FreeCAD.Rotation(V(0, 1, 0), math.degrees(beta)))
        put(pad0, pl, flex); put(gold0, pl, gold); put(foam0, pl, foam)

    # flex links between paddles
    def skin_strip(sa, sb, lift=0.05):
        n = max(6, int(abs(sb - sa) / 1.5))
        pts = []
        for i in range(n + 1):
            c, t_, nn = w.frame(sa + (sb - sa) * i / n)
            pts.append((c[0] + nn[0] * lift, c[1] + nn[1] * lift))
        return _ribbon(pts, BAND_Y + P.SPINE_Y[0], BAND_Y + P.SPINE_Y[1], P.FLEX_T, smooth=0)

    order = [1, 2, 3, 4, 5, 6, 7, 8]
    s_of = {k: pd['s'] for k, pd in r['pods'].items()}
    s_of[3] = w.s_of_x(P.R_DESIGN * math.sin(P.POD_TILT))
    s_of[4] = -s_of[3]
    for a, b in zip(order, order[1:]):
        sa, sb = sorted((s_of[a], s_of[b]))
        flex.append(skin_strip(sa + P.POD_W / 2 - 0.4, sb - P.POD_W / 2 + 0.4))

    # ---- Detailed 22 mm Two-Piece Nylon Classic Strap (QuickFit clips removed -> sewn loops on printed bars!) ----
    hull_cw = [p for _, p in r['hull']]
    hull_ccw = hull_cw[::-1]
    t = P.STRAP_T
    hw_s = P.STRAP_W / 2

    bar_pos = {sx: (M.XC + sx * (P.BODY_HX + P.PIN_DX), P.BAR_ZC + z0) for sx in (1, -1)}
    p_next = {1: hull_cw[1], -1: hull_ccw[1]}
    woven_parts, stitch_parts = [], []
    loop_exit = {}
    for sx in (1, -1):
        xp, zp = bar_pos[sx]
        col_sh, st_sh, p_under = build_sewn_lug_loop(xp, zp, sx, p_next[sx])
        woven_parts.append(col_sh)
        stitch_parts.extend(st_sh)
        # Inner skin-side face of main strap starts right under the cross-bar
        loop_exit[sx] = (p_under[0], p_under[1] - t)

    # 1) -X Buckle Half (92 mm): starts right under -X cross-bar, wraps CCW over Pods 5, 6, 7, 8 to volar buckle
    ccw_pts = [loop_exit[-1]] + hull_ccw[1:]
    tab_ccw_raw = _poly_resample(ccw_pts, step=0.7)
    tab_ccw = [(s, p, tt, (-nn[0], -nn[1])) for s, p, tt, nn in tab_ccw_raw]

    s_buckle = min(P.STRAP_BUCKLE_L - 2.0, tab_ccw[-1][0] - 12.0)
    pts_92 = [p for s, p, _, _ in tab_ccw if s <= s_buckle]
    pb, tb_ccw, nb_out = _at_arc(tab_ccw, s_buckle)
    pts_92.append(pb)
    woven_parts.append(_ribbon(pts_92, BAND_Y - hw_s, BAND_Y + hw_s, t, side=-1.0, smooth=1))

    # Stitched reinforcement collar near the buckle hinge on 92 mm half
    sub_b = [(p[0] + nn[0] * t, p[1] + nn[1] * t) for s, p, _, nn in tab_ccw if s_buckle - 7.5 <= s <= s_buckle - 0.5]
    if len(sub_b) >= 2:
        woven_parts.append(_ribbon(sub_b, BAND_Y - hw_s + 0.15, BAND_Y + hw_s - 0.15, 0.75, side=-1.0, smooth=1))
    for st_s in (s_buckle - 6.0, s_buckle - 1.8):
        ps, ts, ns = _at_arc(tab_ccw, st_s)
        p0 = (ps[0] + ns[0] * (t + 0.55) - ts[0] * 0.55, ps[1] + ns[1] * (t + 0.55) - ts[1] * 0.55)
        p1 = (ps[0] + ns[0] * (t + 0.55) + ts[0] * 0.55, ps[1] + ns[1] * (t + 0.55) + ts[1] * 0.55)
        stitch_parts.append(_ribbon([p0, p1], BAND_Y - hw_s + 1.2, BAND_Y + hw_s - 1.2, 0.42, side=-1.0, smooth=0))

    # 2) +X Hole Half (125 mm): starts right under +X cross-bar, wraps CW over Pods 2 & 1, passes through buckle
    cw_pts = [loop_exit[1]] + hull_cw[1:]
    tab_cw = _poly_resample(cw_pts, step=0.7)
    best_i = min(range(len(tab_cw)), key=lambda i: math.dist(tab_cw[i][1], pb))
    s_meet = tab_cw[best_i][0]
    s_total_125 = P.STRAP_HOLE_L - 2.0
    pts_125, hole_frames = [], []
    n_steps = 180
    outer_lift = P.POD_SLOT_H + P.POD_EAR_T + 0.20              # 3.40 mm: glides cleanly above the 1.05 mm ear clips!
    for i in range(n_steps + 1):
        s_cur = s_total_125 * i / n_steps
        if s_cur <= s_meet - 6.0:
            p, tt, nn = _at_arc(tab_cw, s_cur)
            lift = 0.0
        elif s_cur <= s_meet + 4.0:
            u = (s_cur - (s_meet - 6.0)) / 10.0
            blend = u * u * (3.0 - 2.0 * u)
            p, tt, nn = _at_arc(tab_cw, min(s_cur, tab_cw[-1][0]))
            lift = blend * outer_lift
        else:
            s_back = max(4.0, s_buckle - (s_cur - s_meet))
            p, tt_ccw, nn = _at_arc(tab_ccw, s_back)
            tt = (-tt_ccw[0], -tt_ccw[1])
            lift = outer_lift
        q = (p[0] + nn[0] * lift, p[1] + nn[1] * lift)
        pts_125.append(q)
        hole_frames.append((s_cur + 2.0, q, tt, nn))

    strap_125 = _ribbon(pts_125, BAND_Y - hw_s, BAND_Y + hw_s, t, side=1.0, smooth=1)

    # Rounded tapered tip at the far end of the 125 mm strap (chamfer the two outer Y corners at the tip)
    _, p_tip, t_tip, n_tip = hole_frames[-1]
    for sy in (1, -1):
        c_pts = [
            V(p_tip[0] + t_tip[0] * 1.0 - n_tip[0] * 1.0, BAND_Y + sy * (hw_s + 0.5), p_tip[1] + t_tip[1] * 1.0 - n_tip[1] * 1.0),
            V(p_tip[0] - t_tip[0] * 5.5 - n_tip[0] * 1.0, BAND_Y + sy * (hw_s + 0.5), p_tip[1] - t_tip[1] * 5.5 - n_tip[1] * 1.0),
            V(p_tip[0] + t_tip[0] * 1.0 - n_tip[0] * 1.0, BAND_Y + sy * (hw_s - 4.2), p_tip[1] + t_tip[1] * 1.0 - n_tip[1] * 1.0),
        ]
        prism_tip = Part.Face(Part.makePolygon(c_pts + [c_pts[0]])).extrude(V(n_tip[0] * (t + 2.5), 0, n_tip[1] * (t + 2.5)))
        strap_125 = strap_125.cut(prism_tip)

    # Cut all 12 real oval adjustment holes (33.4 .. 104.9 mm from +X pin) right through the 125 mm strap!
    for sh in P.STRAP_HOLES:
        best_hf = min(hole_frames, key=lambda hf: abs(hf[0] - sh))
        _, ph, th, nh = best_hf
        # Oval slot: length STRAP_HOLE_LEN (2.2 mm) along tangent th, width STRAP_HOLE_W (4.6 mm) along Y
        r_slot = P.STRAP_HOLE_LEN / 2
        hw_slot = P.STRAP_HOLE_W / 2 - r_slot
        p_in = V(ph[0] - nh[0] * 1.0, BAND_Y, ph[1] - nh[1] * 1.0)
        n_vec = V(nh[0], 0, nh[1])
        slot = Part.makeBox(1e-3, 1e-3, 1e-3)               # dummy replaced below
        c1 = Part.makeCylinder(r_slot, t + 2.5, V(p_in.x, BAND_Y - hw_slot, p_in.z), n_vec)
        c2 = Part.makeCylinder(r_slot, t + 2.5, V(p_in.x, BAND_Y + hw_slot, p_in.z), n_vec)
        bx_pts = [
            V(p_in.x - th[0] * r_slot, BAND_Y - hw_slot, p_in.z - th[1] * r_slot),
            V(p_in.x + th[0] * r_slot, BAND_Y - hw_slot, p_in.z + th[1] * r_slot),
            V(p_in.x + th[0] * r_slot, BAND_Y + hw_slot, p_in.z + th[1] * r_slot),
            V(p_in.x - th[0] * r_slot, BAND_Y + hw_slot, p_in.z - th[1] * r_slot),
        ]
        mid_box = Part.Face(Part.makePolygon(bx_pts + [bx_pts[0]])).extrude(V(nh[0] * (t + 2.5), 0, nh[1] * (t + 2.5)))
        strap_125 = strap_125.cut(c1.fuse([c2, mid_box]))

    woven_parts.append(strap_125)

    # 3) Matte-black PVD Tang Buckle + Tongue at s_buckle (oriented so front lip faces back along the 92 mm strap!)
    buckle_solid = build_tang_buckle(pb, (-tb_ccw[0], -tb_ccw[1]), nb_out)

    # 4) Two woven nylon Keeper Loops wrapping BOTH layers on the 92 mm side (at 14 mm and 34 mm back from the buckle;
    #    note: on wrist they sit on the OUTSIDE of the strap, only a thin 1.1 mm inner band passes between Pod 7/8!)
    keepers = []
    # Place keepers cleanly in the inter-pod gaps on the 92 mm half:
    #   keeper 1 right between Buckle (s_buckle ~ 75) and Pod 8 (s ~ 56): at s = s_buckle - 10.5 (~65 mm)
    #   keeper 2 right in the gap between Pod 7 and Pod 8 (around s = s_buckle - 27.5 ~ 48 mm)!
    for sk in (s_buckle - 9.5, s_buckle - 27.5):
        pk, tk, nk = _at_arc(tab_ccw, sk)
        kw = 5.4                                            # keeper band width along strap
        ky = hw_s + 1.35                                    # 28.7 mm outer width
        h_in, h_out = -0.15, outer_lift + t + 0.25          # wraps inner + outer strap layers cleanly above ear clips
        t_k = 1.15

        def K(u, y, v):
            return V(pk[0] + u * tk[0] + v * nk[0], BAND_Y + y, pk[1] + u * tk[1] + v * nk[1])

        outer_loop = Part.Face(Part.makePolygon([
            K(-kw / 2, -ky - t_k, h_in - t_k), K(-kw / 2, ky + t_k, h_in - t_k),
            K(-kw / 2, ky + t_k, h_out + t_k), K(-kw / 2, -ky - t_k, h_out + t_k),
            K(-kw / 2, -ky - t_k, h_in - t_k),
        ])).extrude(V(tk[0] * kw, 0, tk[1] * kw))
        inner_hole = Part.Face(Part.makePolygon([
            K(-kw, -ky, h_in), K(-kw, ky, h_in), K(-kw, ky, h_out), K(-kw, -ky, h_out), K(-kw, -ky, h_in),
        ])).extrude(V(tk[0] * 3 * kw, 0, tk[1] * 3 * kw))
        keepers.append(outer_loop.cut(inner_hole).removeSplitter())

    pod_solids = Part.makeCompound(pods)
    pod_clash = sum(R.clash(pods[i], pods[j]) for i in range(len(pods)) for j in range(i + 1, len(pods)))
    cradle_clash = sum(R.clash(cradle, p) for p in pods)
    if log:
        f = r['force']
        log(f"  {w.name}: module top {r['top_above_skin']:.2f} above the skin; electrode gaps "
            + ' '.join(f"{a:.2f}/{b:.2f}" for a, b in r['gaps'])
            + f"; strap share pods 1..8 " + ' '.join(f"{f[k]:.2f}" for k in range(1, 9))
            + f"; buckle engages at {s_meet + 2.0:.1f} mm from +X bar (Hole #{round((s_meet + 2.0 - 33.4)/6.5) + 1}); "
            + f"pod-pod clash {pod_clash:.3f}, cradle-pod clash {cradle_clash:.3f} mm3")

    items = [
        ('cradle', cradle, R.C_CRADLE), ('holder', holder, R.C_HOLDER),
        *((n, mod(s), color) for n, s, color in M.lid_materials(M.build_lid())),
        ('lug_bars', pins, R.C_HOLDER),
        ('pods', pod_solids, R.C_POD),
        ('strap_buckle', buckle_solid, R.C_QF),
        ('strap', Part.makeCompound(woven_parts), R.C_STRAP),
        ('strap_stitch', Part.makeCompound(stitch_parts), R.C_STITCH),
        ('strap_keepers', Part.makeCompound(keepers), R.C_STITCH),
        ('flex', Part.makeCompound(flex), R.C_FLEX),
        ('electrodes', Part.makeCompound(gold), R.C_GOLD),
        ('foam_dots', Part.makeCompound(foam), R.C_FOAM),
        ('main_board', mod(pcb), R.C_PCB), ('lipo', mod(bat), R.C_LIPO),
    ]
    if with_wrist:
        items.append(('wrist', wrist_solid(w), R.C_SKIN))
    return items, pod_clash, cradle_clash


if not getattr(sys, 'neurband_band_lib', False):
    log = R.Log('band')
    pod = U.check(build_pod(log), 'pod', log)
    jig = U.check(build_jig(log), 'bond_jig', log)
    cradle = M.build_cradle()
    bb_p, bb_j = pod.BoundBox, jig.BoundBox
    log(f"  pod plate: {bb_p.XLength:.1f} x {bb_p.YLength:.1f} x {bb_p.ZLength:.2f}   jig: {bb_j.XLength:.1f} x {bb_j.YLength:.1f} x {bb_j.ZLength:.2f}")
    xs = jig_pod_x()
    log("  jig pod centres: " + ', '.join(f"{k}: {xs[k]:+.2f}" for k in sorted(xs)))
    c_on, pods_on, cj, pj, cp = jig_fit(jig, cradle, pod)
    log(f"  on the jig: cradle-jig clash {cj:.3f}, pods-jig clash {pj:.3f}, cradle-pods clash {cp:.3f} mm3; "
        f"gap lug tip to pod 2 {xs[2] - P.POD_SHELL_W / 2 - (M.XC + P.LUG_HX):.2f}, to pod 5 {(M.XC - P.LUG_HX) - (xs[5] + P.POD_SHELL_W / 2):.2f}")

    R.save('pod', [('pod', pod, R.C_POD)], log)
    R.save('bond_jig', [('bond_jig', jig, R.C_JIG)], log)
    R.save('jig_loaded', [('bond_jig', jig, R.C_JIG), ('cradle', c_on, R.C_CRADLE), ('pods', Part.makeCompound(pods_on), R.C_POD)], log)
    fl, gd, fm = jig_flex()
    R.save('jig_bonded', [('bond_jig', jig, R.C_JIG), ('cradle', c_on, R.C_CRADLE), ('pods', Part.makeCompound(pods_on), R.C_POD),
                          ('flex', Part.makeCompound(fl), R.C_FLEX), ('electrodes', Part.makeCompound(gd), R.C_GOLD),
                          ('foam_dots', Part.makeCompound(fm), R.C_FOAM)], log)
    for w in F.WRISTS:
        items, pc, cc = build_band(w, log)
        if w.name == 'owner':
            R.save('band_assembly', items, log)
    R.finish(log)
