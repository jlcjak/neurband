"""strap.py - rev C strap, r2: an OPEN 20 mm hook-and-loop watch strap (bought) on two thick bars
integral with the module base. Nothing printed in the strap path apart from the pods.

Strap (sourcing.md): a one-piece "single pass" hook-and-loop strap for fixed lug bars, 20 mm: a steel
ring sewn on one end, a plain end with a hook tab (44 mm) on the other, a loop panel in the middle.
  End A (module -X, the antenna side; the real flex has pod 5 next to it), set once: cut the ring off (and as much more as the length table in the
  build guide says for your wrist), heat-seal the end. The band comes up through slot A on the
  end-wall side, goes over bar A, down its outer face, under it and back up into slot A between the
  bar and the loaded band (tip about 6 mm up the slot). The loaded band bends round the tail at the
  bar's lower inner corner and pinches it against the bar: the harder the pull, the harder the pinch
  (the lock of the old printed slide, now on the module's own thick bar). It fails by slipping.
  End B (module +X, the button side; real pod 2 next to it): after the pods (pressed into their snap-in
  channels in the order 5, 6, 7, 8, 1, 2, real flex numbering) the hook end goes UP through slot B, over bar B and back down over the band, where the
  hook tab grips the loop panel. Pull the tail to tighten; peel it to loosen or take the band off.
The slots lean out 20 deg at the top (module.SLOT_TILT): they start under the body's lower edge so the
band leaves the module low enough to press pods 2 and 5.
Strength (logs/strap_strength.log, written by this script from the CAD sections): bar B carries both
strands of the fold (1.39 x band tension with friction, 2 x as the upper bound), bar A the band.
The strap itself is modelled as a smooth swept band (sweep_band) from the path in fit.py.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/strap.py   (reads module_base.step: run module.py first)
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import rc as R
import cadutil as U

V = FreeCAD.Vector

# ---------------- parameters (mm, N, MPa) ----------------
STRAP_W, STRAP_T = R.STRAP_W, R.STRAP_T
F_BAND = 100.0                  # design band pull (strap tension at the module): stretch/snag case
SIGMA_PA12 = 48.0               # MJF PA12 tensile strength (fab data sheet, XY); Z is ~10 % lower
SIGMA_PA12_Z = 43.0
HL_SHEAR = (5.5, 8.0)           # hook-and-loop peak shear, N/cm2 (typical nylon hook on woven loop)
HL_AREA_CM2 = (2.0 * 1.5, 2.0 * 2.5)   # engaged hook area: 15-25 mm of the 44 mm tab (the tab bridges the pod lips it crosses)
MU_BAR = 0.3                    # nylon webbing on PA12 (friction over bar B)
M_FACTOR = (10.0, 8.0)          # bar moment w L^2 / k: k = 10 (ends partly fixed by the arms), 8 (pinned, upper bound)


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
    """Smooth webbing solid along a polyline (x, z) at band line y: B-spline faces through the path
    offset +/- t/2, width w along Y."""
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


def plen(pts):
    return sum(math.dist(pts[k - 1], pts[k]) for k in range(1, len(pts)))


def arc_pts(c, r, a0, a1, step=0.3):
    k = max(2, int(abs(math.radians(a1 - a0)) * r / step) + 1)
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * j / k)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * j / k)))
            for j in range(k + 1)]


# ---------------- strength of the anchor (from the CAD) ----------------
def section_props(face, d):
    """Second moment of a planar XZ section about the axis through its centroid perpendicular to the
    unit load direction d = (dx, dz); returns (area, I, c, S, centroid)."""
    cm = face.CenterOfMass
    # numeric integration over a fine grid (robust for any shape)
    bb = face.BoundBox
    n = 220
    hx, hz = bb.XLength / n, bb.ZLength / n
    A = 0.0; I = 0.0; c = 0.0
    y0 = bb.YMin
    pts = []
    for i in range(n):
        for j in range(n):
            x, z = bb.XMin + (i + 0.5) * hx, bb.ZMin + (j + 0.5) * hz
            if face.isInside(V(x, y0, z), 1e-6, True):
                pts.append((x, z))
    A = len(pts) * hx * hz
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    for x, z in pts:
        r = (x - cx) * d[0] + (z - cz) * d[1]
        I += r * r * hx * hz
        c = max(c, abs(r))
    return A, I, c, I / c, (cx, cz)


def strength_log(log):
    sys.neurband_lib = True
    import module as M
    out = {}
    base = Part.read(os.path.join(R.HERE, 'module_base.step'))
    L = M.SLOT_L
    hl_lo = HL_SHEAR[0] * HL_AREA_CM2[0]
    hl_hi = HL_SHEAR[1] * HL_AREA_CM2[1]
    cap = math.exp(MU_BAR * math.pi)
    log(f"  inputs: band pull F = {F_BAND:.0f} N; MJF PA12 {SIGMA_PA12:.0f} MPa (XY) / {SIGMA_PA12_Z:.0f} (Z); bar span {L:.1f} mm; "
        f"moment w L^2/{M_FACTOR[0]:.0f} (arms fix the ends partly), w L^2/{M_FACTOR[1]:.0f} as the pinned upper bound")
    for sx, name, k_load in ((1, 'B', 2.0), (-1, 'A', 1.0)):
        sl = base.slice(V(0, 1, 0), 0.0)
        faces = []
        for w in sl:
            try:
                f = Part.Face(w)
                if f.Area > 1.0:
                    faces.append(f)
            except Exception:
                pass
        bx, bz = M.bar_center(sx)
        bar = [f for f in faces if f.BoundBox.isInside(V(bx, 0, bz))]
        if not bar:
            log(f"  bar {name}: section not found"); continue
        f = min(bar, key=lambda q: q.Area)
        # load direction: along the strap leaving the bar toward the wrist (down-outward at ~45 deg)
        a = math.radians(45.0)
        d = (sx * math.cos(a), -math.sin(a))
        res = {}
        dirs = {'30deg': 30.0, '45deg': 45.0, '60deg': 60.0, 'vertical': 90.0}
        for lab, deg in dirs.items():
            dd = (sx * math.cos(math.radians(deg)), -math.sin(math.radians(deg)))
            A, I, c, S, cm = section_props(f, dd)
            res[lab] = (A, I, c, S)
        A, I, c, S = min(res.values(), key=lambda t: t[3])
        cap_f = math.exp(MU_BAR * math.pi)
        # bar load at band pull F: B carries the band (F) and the folded tail (F / e^(mu pi) with friction over
        # the bar, F without): 1.39 F nominal, 2 F upper bound; A carries the end cap (F)
        W_nom = F_BAND * (1 + 1 / cap_f) if name == 'B' else F_BAND
        W = k_load * F_BAND
        sig = {kf: W * L / kf / S for kf in M_FACTOR}
        sig_nom = W_nom * L / M_FACTOR[0] / S
        W_break = SIGMA_PA12_Z * S * M_FACTOR[0] / L
        W_break_pin = SIGMA_PA12_Z * S * M_FACTOR[1] / L
        F_break = W_break / ((1 + 1 / cap_f) if name == 'B' else 1.0)
        F_break_lo = W_break_pin / k_load
        out[name] = dict(section_area_mm2=round(A, 2), S_min_mm3=round(S, 2), S_by_dir={k: round(v[3], 2) for k, v in res.items()},
                         bar_load_N=dict(nominal=round(W_nom), upper=W), sigma_MPa={'nominal_wL2/10': round(sig_nom, 1),
                         'upper_wL2/10': round(sig[M_FACTOR[0]], 1), 'upper_pinned': round(sig[M_FACTOR[1]], 1)},
                         bar_break_load_N=dict(wL2_10=round(W_break), pinned=round(W_break_pin)),
                         band_pull_at_bar_failure_N=dict(nominal=round(F_break), worst=round(F_break_lo)))
        log(f"  bar {name}: section {A:.1f} mm2 (trapezoid {M.BAR_W} wide at the bottom, {M.BAR_ZT - M.BAR_ZB:.1f} tall, R{M.BAR_R} edges), "
            f"S min {S:.2f} mm3 over load directions 30-90 deg below horizontal (" + ', '.join(f"{k} {v[3]:.1f}" for k, v in res.items()) + f"); at F = {F_BAND:.0f} N "
            f"the bar load is {W_nom:.0f} N (upper bound {W:.0f} N) over {L:.1f} mm -> sigma {sig_nom:.1f} MPa (upper {sig[M_FACTOR[0]]:.1f}, "
            f"pinned {sig[M_FACTOR[1]]:.1f}); safety {SIGMA_PA12_Z / sig_nom:.2f} (upper {SIGMA_PA12_Z / sig[M_FACTOR[0]]:.2f}, "
            f"pinned {SIGMA_PA12_Z / sig[M_FACTOR[1]]:.2f}) on {SIGMA_PA12_Z:.0f} MPa; the bar breaks at {W_break:.0f} N bar load "
            f"({W_break_pin:.0f} pinned) = band pull {F_break:.0f} N nominal, {F_break_lo:.0f} N worst case")
        # arms: each carries half the bar load as a short cantilever from the end wall
        ya = M.SLOT_L / 2 + M.ARM_T / 2
        xe = M.end_x(sx)
        lever = abs(bx - xe)
        sl2 = base.slice(V(1, 0, 0), xe + sx * 0.3)
        hz = []
        for w in sl2:
            try:
                ff = Part.Face(w)
            except Exception:
                continue
            bb = ff.BoundBox
            if bb.YMin < ya < bb.YMax and bb.ZMin < 0 and bb.XLength < 1e-6:
                ln = Part.makeLine(V(xe + sx * 0.3, ya, -20), V(xe + sx * 0.3, ya, 20)).common(ff)
                hz.append(ln.Length)
        h = max(hz) if hz else 4.5
        Wv = W / 2 * math.sin(a)
        Wh = W / 2 * math.cos(a)
        S_arm = M.ARM_T * h * h / 6
        sig_arm = Wv * lever / S_arm + Wh / (M.ARM_T * h)
        out[name]['arm'] = dict(height_mm=round(h, 2), lever_mm=round(lever, 2), sigma_MPa=round(sig_arm, 1))
        log(f"    arms: {M.ARM_T:.1f} wide x {h:.1f} tall at the end wall, lever {lever:.1f} mm, each {W / 2:.0f} N at 45 deg -> "
            f"sigma {sig_arm:.1f} MPa (bending + tension); the arms are part of the solid end block of the base")
    # pinch lock at A: 360+ deg of wrap (capstan) plus the pinch; it slips, it does not break
    wrap_a = math.exp(MU_BAR * 2 * math.pi)
    log(f"  end A pinch lock: the band wraps bar A about 360 deg (capstan e^(mu 2 pi) = {wrap_a:.1f}) and the loaded band pinches "
        f"the tail at the bar's lower inner corner; the tail tip needs to hold only F / {wrap_a:.1f} = {F_BAND / wrap_a:.0f} N at F = "
        f"{F_BAND:.0f} N, so it holds well past the hook-and-loop at B; beyond that it slips (no part breaks)")
    # the fuse: hook-and-loop slip at B
    T_lo, T_hi = hl_lo * cap, hl_hi * cap
    log(f"  hook-and-loop at B: {HL_SHEAR[0]}-{HL_SHEAR[1]} N/cm2 on {HL_AREA_CM2[0]:.0f}-{HL_AREA_CM2[1]:.0f} cm2 holds the tail with "
        f"{hl_lo:.0f}-{hl_hi:.0f} N; the wrap over bar B multiplies it by e^(mu pi) = {cap:.2f} -> the band slips at a pull of "
        f"{T_lo:.0f}-{T_hi:.0f} N")
    out['hook_and_loop_slip_band_pull_N'] = [round(T_lo), round(T_hi)]
    out['failure_order'] = ['B: the hook tab slips on the loop panel (reversible: press it back)',
                            'A: the pinch lock slips (reversible: re-tuck the end)',
                            'bar B in bending (integral to the base): only beyond the slip loads, see the numbers above']
    log("  failure order: " + ' | '.join(out['failure_order']))
    with open(os.path.join(R.HERE, 'logs', 'strap_strength.json'), 'w') as f:
        json.dump(out, f, indent=1)
    return out


if not getattr(sys, 'neurband_lib', False):
    log = R.Log('strap_strength')
    strength_log(log)
    R.finish(log)
