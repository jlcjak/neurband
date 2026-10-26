"""fit.py - rev C fit check: the one-size band on wrist models of 145, 160 and 180 mm.

Layout per wrist (cross-section at the band line, ellipse model from mech/fitgeom.py):
- the module sits centred on the dorsal apex, resting on the pads of pods 3/4 (foam at its
  nominal worn compression, STACK_LOADED);
- the free pods follow the flex: pod centres 18 mm apart along the shell-face curve (skin offset
  by STACK_LOADED), tangent to it, pads on the skin;
- the strap is taut: its path is the convex hull of the lug bars, the pod channel floors and the
  skin (in the gap): one continuous webbing from the hidden ulnar bar to the slim loop on the radial
  side, where it folds back onto itself.
Numbers: gap over the ulna (size and where), electrode coverage, pod collisions, module seat
gaps, spine bend radii, strap load per pod, strap lengths. Collisions are measured in CAD.
Writes mech/rev_c/fit_results.json and fit_145.step / fit_180.step (fit_160 and the closed band
come from assembly.py).
Run: QT_QPA_PLATFORM=offscreen timeout 600 /usr/bin/freecad mech/rev_c/fit.py
"""
import os, sys, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'extra', 'wrists'))
sys.neurband_lib = True
import FreeCAD, Part
import rc as R
import cadutil as U
import fitgeom as G
import module as M
import pod as P
import strap as S
import wrist as W

V = FreeCAD.Vector

# ---------------- parameters ----------------
SIZES = R.SIZES
STACK = R.STACK_LOADED          # shell face above the skin at a pad, worn
MIN_BEND_R = 3.0
CHECK_CAD = True
SAVE_STEP = (145.0, 180.0)


def loc(p, lx, lz):
    c, s = math.cos(p['ang']), math.sin(p['ang'])
    return (p['x'] + lx * c - lz * s, p['z'] + lx * s + lz * c)


def nearest_s(curve, x, z):
    best, bs = 1e9, 0.0
    for k, (px, pz) in enumerate(curve.pts):
        d = (px - x) ** 2 + (pz - z) ** 2
        if d < best:
            best, bs = d, curve.s[k]
    return bs if bs < curve.P / 2 else bs - curve.P


def hull(points):
    pts = sorted(set((round(x, 4), round(z, 4)) for x, z in points))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]       # counter-clockwise


def layout(c):
    a, b = G.section(c, R.BAND_Y)
    skin = G.Curve(a, b, 0.0)
    face = G.Curve(a, b, STACK)
    # module: pads of pods 3/4 on the skin
    th = M.POD_TH
    xp = (M.R_U - STACK) * math.sin(th)
    zp = (M.R_U - STACK) * math.cos(th) - M.R_U
    z0 = b * math.sqrt(1 - (xp / a) ** 2) - zp
    mod_pod = {3: dict(x=-M.R_U * math.sin(th), z=z0 + M.R_U * math.cos(th) - M.R_U, ang=th),
               4: dict(x=M.R_U * math.sin(th), z=z0 + M.R_U * math.cos(th) - M.R_U, ang=-th)}
    a2, b2 = G.section(c, R.BAND_Y + 5.0)
    a1, b1 = G.section(c, R.BAND_Y - 5.0)
    def taper_tilt(x, z, ang):
        """Forearm taper: outward growth of the surface per mm along the arm at (x, z) -> tilt (rad)."""
        t = math.atan2(z / b, x / a)
        dx, dz = (a2 - a1) * math.cos(t) / 10.0, (b2 - b1) * math.sin(t) / 10.0
        nx, nz = -math.sin(ang), math.cos(ang)          # outward normal of the curve
        return math.atan(dx * nx + dz * nz)
    mod_tilt = math.atan((b2 - b1) / 10.0)
    s4 = nearest_s(face, mod_pod[4]['x'], mod_pod[4]['z'])
    s3 = -s4
    pods = {}
    for i in range(1, R.N_PODS + 1):
        if i in (3, 4):
            d = dict(mod_pod[i]); d['s'] = s3 if i == 3 else s4; d['on_module'] = True
        else:
            s = s4 + (i - 4) * R.PITCH if i > 4 else s3 - (3 - i) * R.PITCH
            x, z, ang = face.at(s)
            d = dict(x=x, z=z, ang=ang, s=s, on_module=False)
        d['i'] = i
        d['tilt'] = mod_tilt if d['on_module'] else taper_tilt(d['x'], d['z'], d['ang'])
        pods[i] = d
    # gap (edge to edge along the face curve) and where it is
    s1, s8 = pods[1]['s'], pods[8]['s']
    chain = s8 - s1 + R.POD_W
    gap = face.P - chain
    gap_mid = s1 - R.POD_W / 2 - gap / 2
    gap_deg = -gap_mid / face.P * 360.0
    cover = chain / face.P
    # bend radius of each spine link: free length / turning (tangent angles of the pod faces)
    radii = {}
    for i in range(1, R.N_PODS):
        if (i, i + 1) == (3, 4):
            # along the module underside (R_U), between the pods on the module
            radii['3-4'] = round(M.R_U - STACK, 2)
            continue
        d = pods[i]['ang'] - pods[i + 1]['ang']
        d = (d + math.pi) % (2 * math.pi) - math.pi
        L = R.PITCH - R.POD_W
        radii[f'{i}-{i + 1}'] = round(L / d, 2) if d > 1e-6 else float('inf')
    # module-edge links: straight-line distance between the pod edges vs. the 11 mm link
    edge_slack = {}
    for i, j, si in ((4, 5, 1), (3, 2, -1)):
        e0 = loc(pods[i], si * R.POD_W / 2, -R.FLEX_T / 2)
        e1 = loc(pods[j], -si * R.POD_W / 2, -R.FLEX_T / 2)
        edge_slack[f'{i}-{j}'] = round(R.PITCH - R.POD_W - math.dist(e0, e1), 2)
    # module seat: gap between the underside and the skin across the module
    gaps = []
    for k in range(-30, 31):
        x = M.CX_OFF + k * (M.OUT_W / 2 - 0.5) / 30
        gaps.append(z0 + M.z_u(x) - b * math.sqrt(1 - (x / a) ** 2))
    seat = dict(centre=round(gaps[30], 2), min=round(min(gaps), 2), max=round(max(gaps), 2),
                edge=round((gaps[0] + gaps[-1]) / 2, 2))
    # ears / strap loops vs the skin (lowest point of the ear, module coords -> wrist)
    # ---- module-edge spine links (3-2, 4-5): leave the module underside and drape onto the skin
    # under the strap's wrap round the hidden bar ----
    lift = R.STACK_LOADED - R.FLEX_T
    lskin = G.Curve(a, b, R.FLEX_T / 2 + 0.12)
    far_pre, loop_dir = {}, {}
    for si, pj in ((-1, 2), (1, 5)):                 # slim loops on both hidden bars, reaching toward pods 2 / 5
        _c = loc(pods[pj], -si * (P.SHELL_W / 2 - 0.6), R.BASE_T + R.STRAP_T / 2)
        _bb = (M.bar_x(si), z0 + M.BAR_Z)
        _dl = math.dist(_bb, _c)
        loop_dir[si] = ((_c[0] - _bb[0]) / _dl, (_c[1] - _bb[1]) / _dl)
        far_pre[si] = (_bb[0] + S.LOOP_REACH * loop_dir[si][0], _bb[1] + S.LOOP_REACH * loop_dir[si][1])
    edge_links = {}
    bars_m = {-1: (M.bar_x(-1), z0 + M.BAR_Z), 1: (M.bar_x(1), z0 + M.BAR_Z)}
    wrap_r = {-1: S.CLIP_RO, 1: S.CLIP_RO}                  # loop clips on the hidden bars
    def hermite(p0, t0, p1, t1, n=30):
        m = math.dist(p0, p1)
        out = []
        for k in range(n + 1):
            u = k / n
            h00, h10, h01, h11 = 2*u**3 - 3*u**2 + 1, u**3 - 2*u**2 + u, -2*u**3 + 3*u**2, u**3 - u**2
            out.append((h00*p0[0] + h10*m*t0[0] + h01*p1[0] + h11*m*t1[0], h00*p0[1] + h10*m*t0[1] + h01*p1[1] + h11*m*t1[1]))
        return out
    rf_out = S.FAR_U / 2 + R.STRAP_T                     # strap wrap round the loop's far bar
    def spline(pts, t0, t1, n=16):
        """Tangent-continuous Catmull-Rom/Hermite through pts with end tangents t0, t1."""
        tans = [t0]
        for k in range(1, len(pts) - 1):
            dx, dz = pts[k + 1][0] - pts[k - 1][0], pts[k + 1][1] - pts[k - 1][1]
            d = math.hypot(dx, dz)
            tans.append((dx / d, dz / d))
        tans.append(t1)
        out = []
        for k in range(len(pts) - 1):
            seg = hermite(pts[k], tans[k], pts[k + 1], tans[k + 1], n)
            out += seg[:-1] if k < len(pts) - 2 else seg
        return out
    for i, j, si in ((3, 2, -1), (4, 5, 1)):
        # free link: leaves the paddle edge along the R42 seat, arrives along pod j's face (smooth,
        # tangent), passing under the strap wrap / loop clip / far-bar wrap (skin side)
        e0 = loc(pods[i], si * R.POD_W / 2, -R.FLEX_T / 2)
        e1 = loc(pods[j], -si * R.POD_W / 2, -lift - R.FLEX_T / 2)
        t0 = (si * math.cos(pods[i]['ang']), si * math.sin(pods[i]['ang']))
        t1 = (si * math.cos(pods[j]['ang']), si * math.sin(pods[j]['ang']))
        obst = [(bars_m[si], wrap_r[si]), (far_pre[si], rf_out)]
        vias = []
        q = hermite(e0, t0, e1, t1)
        for _ in range(4):
            bad = None
            for (cx, cz), r in obst:
                need = r + R.FLEX_T / 2 + 0.1
                dmin = min(math.dist(pt, (cx, cz)) for pt in q)
                if dmin < need - 0.02 and (bad is None or need - dmin > bad[2]):
                    bad = ((cx, cz), need, need - dmin)
            if bad is None:
                break
            (cx, cz), need, _ = bad
            rc0 = math.hypot(cx, cz)
            v = (cx - cx / rc0 * need, cz - cz / rc0 * need)
            sk = lskin.at(nearest_s(lskin, *v))
            if math.hypot(*v) < math.hypot(sk[0], sk[1]) + 0.05:   # do not go into the skin
                v = (sk[0] * 1.0, sk[1] * 1.0)
            vias = sorted([x for x in vias if math.dist(x, v) > 0.5] + [v], key=lambda p_: abs(p_[0]))
            q = spline([e0] + vias + [e1], t0, t1)
        edge_links[f'{i}-{j}'] = q
    def min_radius(q):
        q = S.resample(q, 0.25)
        best = 1e9
        for k in range(1, len(q) - 1):
            (x1, y1), (x2, y2), (x3, y3) = q[k - 1], q[k], q[k + 1]
            a_, b_, c_ = math.dist(q[k - 1], q[k]), math.dist(q[k], q[k + 1]), math.dist(q[k - 1], q[k + 1])
            area = abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) / 2
            if area > 1e-9:
                best = min(best, a_ * b_ * c_ / (4 * area))
        return best
    edge_link_r = {k: round(min_radius(v), 2) for k, v in edge_links.items()}
    # ---- strap: one continuous webbing, taut convex hull ----
    zc = R.BASE_T + R.STRAP_T / 2
    pts = []
    rb = S.FAR_U / 2 + R.STRAP_T / 2                   # strap centre line round each loop's far bar
    bar_a = (M.bar_x(-1), z0 + M.BAR_Z)
    bar_b = (M.bar_x(1), z0 + M.BAR_Z)
    far_a, far_b = far_pre[-1], far_pre[1]
    d = loop_dir[1]
    rf = rb
    circ = {}
    for key, (cx, cz), r in (('A', far_a, rb), ('B', far_b, rf)):
        circ[key] = []
        for k in range(24):
            t = 2 * math.pi * k / 24
            q = (cx + r * math.cos(t), cz + r * math.sin(t))
            circ[key].append(q)
            pts.append(q)
    pod_pts = {}
    for i, p in pods.items():
        if p['on_module']:
            continue
        pod_pts[i] = [loc(p, lx, zc) for lx in (-P.SHELL_W / 2 + 0.6, 0.0, P.SHELL_W / 2 - 0.6)]
        pts += pod_pts[i]
        hs = P.SHELL_W / 2 + R.STRAP_T / 2 + 0.05     # the strap wraps the pod sides where it drops to the skin
        pts += [loc(p, sx * hs, zz) for sx in (-1, 1) for zz in (R.BASE_T, 0.6, -R.STACK_LOADED + R.STRAP_T / 2 + 0.3)]
        rr = R.STRAP_T / 2 + 0.05
        pts += [loc(p, sx * (P.SHELL_W / 2 + rr * math.cos(t)), R.BASE_T + rr * math.sin(t))
                for sx in (-1, 1) for t in (0.0, 0.4, 0.8, 1.2, 1.5708)]
    # keep the webbing outside the draped module-edge links
    for q in edge_links.values():
        for k in range(1, len(q) - 1):
            x, z = q[k]
            if min(math.dist(q[k], bars_m[-1]), math.dist(q[k], bars_m[1])) < 3.5:
                continue                              # under the wrap / loop: not a strap support
            rr_ = math.hypot(x, z)
            off_ = R.FLEX_T / 2 + R.STRAP_T / 2 + 0.05
            pts.append((x + x / rr_ * off_, z + z / rr_ * off_))
    skin_s = G.Curve(a, b, R.STRAP_T / 2 + 0.15)      # +0.15: avoid tangent faces in the CAD Booleans
    for k in range(400):
        x, z, _ = skin_s.at(skin_s.P * k / 400)
        if z < z0 - 1.0 or abs(x) > M.OUT_W / 2 + 4:
            pts.append((x, z))
    H = hull(pts)[::-1]                               # clockwise (dorsal -> radial -> volar -> ulnar)
    def is_on(q, key):
        return any(math.dist(q, c) < 1e-3 for c in circ[key])
    n = len(H)
    # the top (A -> B over the module) is not strap: start at the B block that follows the A block
    ka = next(k for k in range(n) if is_on(H[k], 'A') and not is_on(H[(k + 1) % n], 'A'))
    H = H[ka + 1:] + H[:ka + 1]
    jb0 = next(k for k in range(n) if is_on(H[k], 'B'))
    jb = jb0
    while is_on(H[jb + 1], 'B'):
        jb += 1
    ja = next(k for k in range(jb, n) if is_on(H[k], 'A'))
    path = H[jb:ja + 1]                               # main band: far bar (radial) -> pods 5..8, 1, 2 -> bar A
    def ext(k):
        p0, p1, p2 = H[k - 1], H[k], H[(k + 1) % len(H)]
        a0 = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        a1 = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        return abs((a1 - a0 + math.pi) % (2 * math.pi) - math.pi)
    loads = {}
    for i, p in pods.items():
        if p['on_module']:
            continue
        c_, s_ = math.cos(p['ang']), math.sin(p['ang'])
        ks = []
        for k in range(len(H)):
            dx, dz = H[k][0] - p['x'], H[k][1] - p['z']
            lx, lz = dx * c_ + dz * s_, -dx * s_ + dz * c_
            if abs(lx) <= P.SHELL_W / 2 + R.STRAP_T and -R.STACK_LOADED - 0.1 <= lz <= R.BASE_T + R.STRAP_T + 0.2:
                ks.append(k)
        loads[i] = sum(ext(k) for k in ks)
    def path_len(seq):
        return sum(math.dist(seq[k], seq[k + 1]) for k in range(len(seq) - 1))
    loop_ang = math.atan2(d[1], d[0])
    loop_ang_a = math.atan2(loop_dir[-1][1], loop_dir[-1][0])
    loop_skin = min(math.hypot(far_b[0] - x, far_b[1] - z) for x, z in skin.pts[::4]) - S.FAR_W / 2
    return dict(c=c, a=a, b=b, z0=z0, mod_tilt=mod_tilt, pods=pods, face_P=face.P, skin_P=skin.P, chain=chain, gap=gap,
                gap_deg=gap_deg, cover=cover, radii=radii, edge_slack=edge_slack, seat=seat,
                ear_skin=loop_skin, loads=loads, path=path, path_len=path_len(path), bar_a=bar_a, bar_b=bar_b,
                far_b=far_b, far_a=far_a, rb=rb, rf=rf, loop_ang=loop_ang, loop_ang_a=loop_ang_a,
                edge_links=edge_links, edge_link_r=edge_link_r)


def numbers(L):
    free = {i: v for i, v in L['loads'].items()}
    mean = sum(free.values()) / len(free)
    rmin_free = min(v for k, v in L['radii'].items() if k != '3-4')
    T_3kpa = 3e-3 * math.pi * (R.PAD_D / 2) ** 2 * 3 / mean     # N strap tension for 3 kPa per pad on an average pod
    return dict(
        wrist_mm=L['c'], semi_axes_mm=[round(L['a'], 1), round(L['b'], 1)],
        module_taper_tilt_deg=round(math.degrees(L['mod_tilt']), 2),
        pod_taper_tilt_deg={i: round(math.degrees(p['tilt']), 2) for i, p in L['pods'].items()},
        R_dorsal_mm=round(L['a'] ** 2 / L['b'], 1), R_side_mm=round(L['b'] ** 2 / L['a'], 1),
        gap_mm=round(L['gap'], 1), gap_centre_deg_from_dorsal=round(L['gap_deg'], 0),
        electrode_cover_pct=round(100 * L['cover'], 1),
        electrode_arc_on_skin_mm=round(L['cover'] * L['skin_P'], 1),
        spine_bend_radius_mm=L['radii'], min_free_bend_radius_mm=round(rmin_free, 2),
        module_edge_link_slack_mm=L['edge_slack'], module_edge_link_min_bend_r_mm=L['edge_link_r'],
        module_seat_gap_mm=L['seat'], loop_clear_of_skin_mm=round(L['ear_skin'], 2),
        strap_load_rel={k: round(v / mean, 2) for k, v in sorted(L['loads'].items())},
        strap_load_max_min=round(max(free.values()) / min(free.values()), 2),
        strap_tension_for_3kPa_N=round(T_3kpa, 2),
        strap_path_mm=round(L['path_len'], 1),
    )


def strap_clearance(L):
    """Min distance from the strap's inner face to the skin, on the sections at both strap edges
    (the forearm tapers), sampling the long and short paths every 0.5 mm."""
    best = 1e9
    for dy in (-R.STRAP_W / 2, R.STRAP_W / 2):
        a, b = G.section(L['c'], R.BAND_Y + dy)
        skin = G.Curve(a, b, 0.0, n=3000)
        for path in (L['path'],):
            for k in range(len(path) - 1):
                (x0, z0), (x1, z1) = path[k], path[k + 1]
                n = max(1, int(math.dist(path[k], path[k + 1]) / 0.5))
                for j in range(n + 1):
                    x, z = x0 + (x1 - x0) * j / n, z0 + (z1 - z0) * j / n
                    if z > L['z0'] - 3 and abs(x) < 20:      # under the module: lug loops, not on skin
                        continue
                    d = min(math.hypot(px - x, pz - z) for px, pz in skin.pts[::3])
                    inside = (x / a) ** 2 + (z / b) ** 2 < 1
                    best = min(best, (-d if inside else d) - R.STRAP_T / 2)
    return round(best, 2)


def place_pod_shapes(L, shell0, flex0, gold0, foam0, use_tilt=True):
    y = R.BAND_Y
    out = dict(shells=[], flex=[], gold=[], foam=[])
    for i, p in L['pods'].items():
        if p['on_module']:
            continue
        pl = U.pod_placement(p['x'], p['z'], p['ang'], y).multiply(
            FreeCAD.Placement(V(0, 0, 0), FreeCAD.Rotation(V(1, 0, 0), math.degrees(p['tilt'] if use_tilt else 0.0))))
        for key, src in (('shells', [shell0]), ('flex', [flex0]), ('gold', gold0), ('foam', foam0)):
            for s in src:
                s = s.copy()
                s.Placement = pl.multiply(s.Placement)
                out[key].append(s)
    return out


def build_band(c, log, with_wrist=True, cad=True):
    L = layout(c)
    res = numbers(L)
    y = R.BAND_Y
    lift = STACK - R.FLEX_T
    shell0 = P.build()
    flex0, gold0, foam0 = R.flex_pod(lift)
    PS = place_pod_shapes(L, shell0, flex0, gold0, foam0)
    def mplace(s):
        s = s.copy()
        s.translate(V(0, y, L['z0']))
        s.rotate(V(0, y, L['z0']), V(1, 0, 0), math.degrees(L['mod_tilt']))
        return s
    base, lid = mplace(M.build_base()), mplace(M.build_lid())
    I = M.internals()
    mf, mg, mfo = M.flex_on_module(lift)
    mf, mg, mfo = [mplace(s) for s in mf], [mplace(s) for s in mg], [mplace(s) for s in mfo]
    tail = mplace(I['tail'])
    # spine links: follow the wrist between free pods (swept), chords at the module edges
    links = []
    ys = y + sum(R.SPINE_Y) / 2
    sw = R.SPINE_Y[1] - R.SPINE_Y[0]
    pods = L['pods']
    lcurve = G.Curve(L['a'], L['b'], 0.2)
    for i in range(1, R.N_PODS):
        if (i, i + 1) == (3, 4):
            continue
        if pods[i]['on_module'] or pods[i + 1]['on_module']:
            key = '3-2' if (i, i + 1) == (2, 3) else '4-5'
            bm = S.sweep_band(L['edge_links'][key], ys, w=sw, t=R.FLEX_T)
            if bm is not None:                         # leaves the tilted module, drapes on the tapered skin
                bm.rotate(V(0, y, L['z0']), V(1, 0, 0), math.degrees(L['mod_tilt']))
        else:
            s0, s1 = pods[i]['s'] + R.POD_W / 2, pods[i + 1]['s'] - R.POD_W / 2
            q = [lcurve.at(s0 + (s1 - s0) * k / 12)[:2] for k in range(13)]
            bm = S.sweep_band(q, ys, w=sw, t=R.FLEX_T)
        if bm is not None:
            links.append(bm)
    # strap: one continuous swept band + wraps + fold-back + slim loop
    path = L['path']
    band = S.sweep_band(path[::-1], y)                 # bar A -> pods 2, 1, gap, 8..5 -> loop far bar
    (ax, az), (fx, fz) = L['far_a'], L['far_b']
    wrap_a = S.wrap(ax, az, L['rb'] - R.STRAP_T / 2, y)
    sewn = S.sweep_band(S.offset(S.resample(S.smooth(path[::-1], 2), 0.8)[:18], -(R.STRAP_T + 0.05)), y)
    wrap_b = S.wrap(fx, fz, L['rf'] - R.STRAP_T / 2, y)
    fold_len = S.FOLD_MIN + (layout(SIZES[-1])['path_len'] - L['path_len'])
    fp, acc = [path[0]], 0.0
    for k in range(1, len(path)):
        acc += math.dist(path[k - 1], path[k])
        fp.append(path[k])
        if acc >= fold_len:
            break
    fold = S.sweep_band(S.offset(S.resample(S.smooth(fp, 2), 0.8), R.STRAP_T + 0.05), y)
    loop = S.placed_loop(L['bar_b'][0], L['bar_b'][1], L['loop_ang'], y).fuse(
        S.placed_loop(L['bar_a'][0], L['bar_a'][1], L['loop_ang_a'], y, flip=True))
    def tilt(sh):                                      # follow the module's taper tilt at its lugs
        if sh is None:
            return None
        sh = sh.copy()
        sh.rotate(V(0, y, L['z0']), V(1, 0, 0), math.degrees(L['mod_tilt']))
        return sh
    loop, wrap_a, sewn, wrap_b = tilt(loop), tilt(wrap_a), tilt(sewn), tilt(wrap_b)
    strap_parts = [x for x in (band, wrap_a, sewn, wrap_b, fold) if x is not None]
    res['fold_back_mm'] = round(fold_len, 1)
    items = []
    wrist = None
    if with_wrist:
        wrist, hand = W.build(c)
        items.append(('wrist', wrist, R.C_SKIN))
    items += [('module_base', base, R.C_HOUSING), ('module_lid', lid, R.C_HOUSING),
              ('main_board', mplace(I['pcb']), R.C_PCB), ('board_parts', mplace(I['parts']), (0.15, 0.15, 0.15)),
              ('lipo', mplace(I['bat']), R.C_LIPO), ('light_pipe', mplace(I['lp']), (0.92, 0.92, 0.90)),
              ('magnets', mplace(I['mags']), R.C_METAL), ('button_cap', mplace(I['cap']), R.C_HOUSING),
              ('pod_shells', Part.makeCompound(PS['shells']), R.C_POD),
              ('flex', Part.makeCompound(PS['flex'] + mf + links + [tail]), R.C_FLEX),
              ('pads', Part.makeCompound(PS['gold'] + mg), R.C_GOLD),
              ('foam', Part.makeCompound(PS['foam'] + mfo), R.C_FOAM),
              ('strap', Part.makeCompound(strap_parts), R.C_STRAP),
              ('strap_loop', loop, R.C_POD)]
    res['strap_min_clear_to_skin_mm'] = strap_clearance(L)
    if cad and CHECK_CAD:
        def vol(x, ys_):
            return round(sum(x.common(q).Volume for q in ys_), 3)
        sh = PS['shells']
        inter = {}
        inter['pod_vs_pod'] = round(sum(sh[k].common(sh[k + 1]).Volume for k in range(len(sh) - 1)), 3)
        inter['pods_vs_module'] = vol(Part.makeCompound(sh), [base, lid])
        inter['strap_vs_module'] = vol(band, [base, lid])
        sh0 = place_pod_shapes(L, shell0, flex0, [], [], use_tilt=False)['shells']
        inter['strap_vs_pods_untilted'] = vol(band, sh0)      # webbing twists <= 3 deg with the pods' taper tilt
        inter['loop_vs_module'] = vol(loop, [base, lid])
        inter['strap_vs_flex'] = vol(Part.makeCompound(strap_parts + [loop]), links)
        inter['loop_vs_pods'] = vol(loop, sh)
        if wrist is not None:
            inter['pods_vs_wrist'] = vol(wrist, sh)
            inter['module_vs_wrist'] = vol(wrist, [base, lid])
            inter['pads_vs_wrist'] = vol(wrist, PS['gold'] + mg)       # pads pressed in (foam takes it)
            # (strap vs the lofted wrist hangs OCC at 180 mm -> analytic clearance below instead)
        res['interference_mm3'] = inter
    return res, items, L


if not getattr(sys, 'neurband_fit_lib', False):
    log = R.Log('fit')
    results = {}
    for c in SIZES:
        res, items, L = build_band(c, log, with_wrist=True, cad=True)
        results[str(int(c))] = res
        log(f"C={c}: " + json.dumps(res))
        if c in SAVE_STEP:
            R.save(f'fit_{int(c)}', items, log)
        wf = os.path.join(R.ROOT, 'extra', 'wrists', f'wrist_{int(c)}.step')
        if not os.path.exists(wf):          # 145 mm wrist model (extra/wrists has 140..200 only)
            U.save(f'wrist_{int(c)}', [(f'wrist_{int(c)}', items[0][1], R.C_SKIN)], log,
                   folder=os.path.join(R.ROOT, 'extra', 'wrists'))
    # one strap for all sizes: cut length from the largest wrist
    lo, hi = results['145'], results['180']
    wrap_a = math.pi * 2 * (S.FAR_U / 2 + R.STRAP_T / 2)
    wrap_b = math.pi * (S.FAR_U / 2 + R.STRAP_T / 2)
    results['strap_cut_mm'] = dict(
        webbing=round(hi['strap_path_mm'] + wrap_a + S.SEW_OVERLAP + wrap_b + S.FOLD_MIN, 0),
        fold_back_at_145=lo['fold_back_mm'], fold_back_at_180=hi['fold_back_mm'],
        hook_tape=S.HOOK_L, loop_face='whole outer face (loop-fabric webbing) or 110 mm sew-on loop tape')
    with open(os.path.join(HERE, 'fit_results.json'), 'w') as f:
        json.dump(results, f, indent=1)
    log("strap cut: " + json.dumps(results['strap_cut_mm']))
    R.finish(log)
