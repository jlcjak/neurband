"""fit.py - rev C fit check: the one-size band on wrist models of 145, 160 and 180 mm (r2: open
hook-and-loop strap on the module's two integral bars).

Layout per wrist (cross-section at the band line, ellipse model from mech/fitgeom.py):
- the module sits centred on the dorsal apex, resting on the pads of pods 3/4 (foam at its
  nominal worn compression, STACK_LOADED);
- the free pods follow the flex: pod centres 18 mm apart along the shell-face curve (skin offset
  by STACK_LOADED), tangent to it, pads on the skin;
- the strap is taut: the band is the convex hull of the bars' lower ends, the pod channel floors
  and the skin (in the gap); at end A it rises through slot A to the end cap on the ears, at end
  B it wraps round bar B's lower end, rises through slot B, goes over the bar and folds back over
  the band (the tail, lifted over the pod lips it crosses).
Numbers: gap over the ulna (size and where), electrode coverage, pod collisions, module seat
gaps, spine bend radii, strap load per pod, strap lengths, bar clearance to the skin. Collisions
are measured in CAD. Writes mech/rev_c/fit_results.json and fit_145.step / fit_180.step
(fit_160 and the closed band come from assembly.py).
Run: QT_QPA_PLATFORM=offscreen timeout 900 /usr/bin/freecad mech/rev_c/fit.py
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
    SM = STACK + M.MODULE_EXTRA                     # the module's pads stand prouder (shallower pockets)
    xp = (M.R_U - SM) * math.sin(th)
    zp = (M.R_U - SM) * math.cos(th) - M.R_U
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
    # ---- the two bars (2D, wrist frame: module coords + z0): rounding centres of their four corners ----
    t = R.STRAP_T
    bars = {}
    for si in (-1, 1):
        g = M.bar_geom(si)
        sh = lambda q: (q[0], z0 + q[1])
        bars[si] = dict(li=sh(g['cen']['li']), lo=sh(g['cen']['lo']), uo=sh(g['cen']['uo']), ui=sh(g['cen']['ui']), r=g['r'],
                        n=dict(bottom=g['n_bottom'], outer=g['n_outer'], top=g['n_top'], slot=g['n_slot']),
                        xe=M.end_x(si), gap=M.slot_gap(si), corner=(M.end_x(si) - si * 0.6, z0 + M.z_u(M.OUT_W / 2 - 0.6) + 0.6))
    rb = 1.0 + t / 2 + 0.05                           # band centre line round a bar corner (rounding R1)
    # ---- module-edge spine links (3-2, 4-5): leave the module underside and drape onto the skin under
    # the band's wrap round the bar's lower end ----
    lift = R.STACK_LOADED - R.FLEX_T
    lskin = G.Curve(a, b, R.FLEX_T / 2 + 0.12)

    def hermite(p0, t0, p1, t1, n=30):
        m = math.dist(p0, p1)
        out = []
        for k in range(n + 1):
            u = k / n
            h00, h10, h01, h11 = 2*u**3 - 3*u**2 + 1, u**3 - 2*u**2 + u, -2*u**3 + 3*u**2, u**3 - u**2
            out.append((h00*p0[0] + h10*m*t0[0] + h01*p1[0] + h11*m*t1[0], h00*p0[1] + h10*m*t0[1] + h01*p1[1] + h11*m*t1[1]))
        return out

    def spline(pts, t0, t1, n=16):
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
    # ---- strap: the taut band is the convex hull of the bars' lower ends, the pod channel floors and the skin ----
    zc = R.BASE_T + t / 2
    pts = []
    circ = {}
    rA = 1.0 + 1.5 * t + 0.1                          # (kept for the edge-link obstacles)

    def contour(si, d):
        """Band centre line round bar si: the bar section (module.bar_profile) offset by d, clockwise (x, z)."""
        poly = [(M.x_of(si, u), z0 + z) for u, z in M.bar_profile(si)]
        f = Part.Face(Part.makePolygon([V(x, 0, z) for x, z in poly] + [V(poly[0][0], 0, poly[0][1])]))
        w = f.makeOffset2D(d).OuterWire
        q = [(v.x, v.z) for v in w.discretize(Distance=0.25)]
        if q[0] == q[-1]:
            q = q[:-1]
        area = sum(q[k][0] * q[(k + 1) % len(q)][1] - q[(k + 1) % len(q)][0] * q[k][1] for k in range(len(q)))
        return q[::-1] if area > 0 else q             # clockwise

    def seg(q, p_from, p_to):
        i = min(range(len(q)), key=lambda k: math.dist(q[k], p_from))
        j = min(range(len(q)), key=lambda k: math.dist(q[k], p_to))
        out = [q[i]]
        k = i
        while k != j:
            k = (k + 1) % len(q)
            out.append(q[k])
        return out
    zb_bar = z0 + M.BAR_ZB
    cB = contour(1, t / 2 + 0.1)
    cA1 = contour(-1, t / 2 + 0.1)                    # end A: the tail's layer on bar A
    cA2 = contour(-1, 1.5 * t + 0.2)                  # end A: the loaded band over it
    for key, cq in (('A', cA2), ('B', cB)):
        # the band runs UNDER the bar to reach its slot: only the bar's underside supports it
        circ[key] = [q for q in cq if q[1] < zb_bar + 0.05]
        pts += circ[key]
    pod_pts = {}
    for i, p in pods.items():
        if p['on_module']:
            continue
        pod_pts[i] = [loc(p, lx, zc) for lx in (-P.SHELL_W / 2 + 0.6, 0.0, P.SHELL_W / 2 - 0.6)]
        pts += pod_pts[i]
        hs = P.SHELL_W / 2 + t / 2 + 0.05
        pts += [loc(p, sx * hs, zz) for sx in (-1, 1) for zz in (R.BASE_T, 0.6, -R.STACK_LOADED + t / 2 + 0.3)]
        rr = t / 2 + 0.05
        pts += [loc(p, sx * (P.SHELL_W / 2 + rr * math.cos(th_)), R.BASE_T + rr * math.sin(th_))
                for sx in (-1, 1) for th_ in (0.0, 0.4, 0.8, 1.2, 1.5708)]
    skin_s = G.Curve(a, b, t / 2 + 0.15)
    for k in range(400):
        x, z, _ = skin_s.at(skin_s.P * k / 400)
        if z < z0 - 1.0 or abs(x) > M.OUT_W / 2 + 10:
            pts.append((x, z))
    H = hull(pts)[::-1]                               # clockwise (dorsal -> radial -> volar -> ulnar)

    def is_on(q, key):
        return any(math.dist(q, c_) < 1e-3 for c_ in circ[key])
    n = len(H)
    ka = next(k for k in range(n) if is_on(H[k], 'A') and not is_on(H[(k + 1) % n], 'A'))
    H = H[ka + 1:] + H[:ka + 1]
    jb0 = next(k for k in range(n) if is_on(H[k], 'B'))
    jb = jb0
    while is_on(H[jb + 1], 'B'):
        jb += 1
    ja = next(k for k in range(jb, n) if is_on(H[k], 'A'))
    hull_path = H[jb:ja + 1]                          # B's lower end -> pods 5..8, gap, 1, 2 -> A's lower end

    def ang(c_, q):
        return math.degrees(math.atan2(q[1] - c_[1], q[0] - c_[0]))

    def arc_to(c_, r_, q0, a1, cw):
        """arc round c_ from point q0's angle to a1 (deg), clockwise if cw."""
        a0 = ang(c_, q0)
        if cw:
            while a1 > a0:
                a1 -= 360
        else:
            while a1 < a0:
                a1 += 360
        return S.arc_pts(c_, r_, a0, a1, 0.3)
    # end A (pinch lock), in band order from the tail tip: the tip lies in slot A against bar A's inner face,
    # the band goes down, round bar A's lower corners, up its outer face, over its top, down slot A on the
    # end-wall side and round the tail's wrap at the lower-inner corner (the pinch) to pod 2
    def ray(p0, ang_deg, d):
        return (p0[0] + d * math.cos(math.radians(ang_deg)), p0[1] + d * math.sin(math.radians(ang_deg)))
    bA, bB = bars[-1], bars[1]
    nA, nB = bA['n'], bB['n']

    def cw_arc(c_, r_, a0, a1):
        while a1 > a0:
            a1 -= 360.0
        return S.arc_pts(c_, r_, a0, a1, 0.3)
    # end A (pinch lock), in band order from the tail tip: up slot A against bar A's inner face, round the whole
    # bar (tail layer, cA1), then the loaded band down slot A on the end-wall side and under the bar over the tail
    # (cA2) to the hull
    inner = [q for q in cA1 if zb_bar + 4.0 < q[1] < zb_bar + 6.5]
    p_tip = max(inner, key=lambda q: q[0])
    p_end = min([q for q in cA1 if q[1] > zb_bar + 6.0 and q[0] > p_tip[0] - 3.0], key=lambda q: -q[0] + 0.1 * q[1])
    lockA = seg(cA1, p_tip, p_end)
    uw = lambda z: M.end_x(-1) - (M.u_in(-1, z - z0) + t / 2 + 0.25)
    lockA += [(uw(z0 + M.BAR_ZT), z0 + M.BAR_ZT), (uw(zb_bar), zb_bar)]
    lockA += seg(cA2, lockA[-1], hull_path[-1])[1:]
    # end B: from the hull start (under the bar) round the inner corner, up slot B, over the top, down the outer face
    p_out = max([q for q in cB if zb_bar + 0.5 < q[1] < zb_bar + 2.5], key=lambda q: q[0])
    pre = seg(cB, hull_path[0], p_out)
    over = []
    path_full = lockA[:-1] + list(reversed(hull_path)) + pre[1:] + over
    cap_ax, cap_az = p_tip
    # the tail: from the outer side of bar B back down over the band (outside it, one thickness out), lifted over
    # the pod lips it crosses, TAB_L of hook zone
    tail0 = path_full[-1]
    back = list(reversed(hull_path))                  # A -> B along the band (outer side is the hull's outside)
    band_out = []
    for k in range(len(back) - 1, 0, -1):             # walk from B toward A
        (x1, z1), (x2, z2) = back[k], back[k - 1]
        nx_, nz_ = x1, z1
        rr_ = math.hypot(nx_, nz_) or 1.0
        band_out.append((x1 + nx_ / rr_ * t, z1 + nz_ / rr_ * t))
    tail = [tail0]
    for q in band_out:
        qq = q
        for i in (5, 6, 7, 8):                        # over a pod: ride on its lips
            p = pods[i]
            c_, s_ = math.cos(p['ang']), math.sin(p['ang'])
            dx, dz = qq[0] - p['x'], qq[1] - p['z']
            lx, lz = dx * c_ + dz * s_, -dx * s_ + dz * c_
            if abs(lx) <= P.SHELL_W / 2 + 0.3:
                lz = max(lz, P.H + t / 2 + 0.05)
                qq = (p['x'] + lx * c_ - lz * s_, p['z'] + lx * s_ + lz * c_)
        if math.dist(tail[-1], qq) > 0.3:
            tail.append(qq)
        if S.plen(tail) > R.TAB_L + 12.0:
            break
    tail = S.resample(S.smooth(tail, 2), 0.6)
    # loads per pod (turning of the hull at each pod)

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
            if abs(lx) <= P.SHELL_W / 2 + t and -R.STACK_LOADED - 0.1 <= lz <= R.BASE_T + t + 0.2:
                ks.append(k)
        loads[i] = sum(ext(k) for k in ks)
    # edge links: from the module pod edge to pod 2 / 5, under the band's wrap round the bar's lower end
    edge_links = {}
    for i, j, si in ((3, 2, -1), (4, 5, 1)):
        e0 = loc(pods[i], si * R.POD_W / 2, -R.FLEX_T / 2)
        e1 = loc(pods[j], -si * R.POD_W / 2, -lift - R.FLEX_T / 2)
        t0 = (si * math.cos(pods[i]['ang']), si * math.sin(pods[i]['ang']))
        t1 = (si * math.cos(pods[j]['ang']), si * math.sin(pods[j]['ang']))
        obst = [(bars[si]['li'], (rA if si < 0 else rb) + t / 2), (bars[si]['lo'], 1.0 + 0.3), (bars[si]['corner'], 1.2)]
        near = [q for q in hull_path if math.dist(q, bars[si]['li']) < 16.0]     # the band's run from the bar to pod 2 / 5
        obst += [(q, t / 2 + 0.15) for q in S.densify(near, 0.8)]
        vias = []
        q = hermite(e0, t0, e1, t1)
        for _ in range(5):
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
            if math.hypot(*v) < math.hypot(sk[0], sk[1]) + 0.05:
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
    bar_skin = min(min(math.hypot(bars[si][k_][0] - x, bars[si][k_][1] - z) for x, z in skin.pts[::2]) - bars[si]['r']
                   for si in (-1, 1) for k_ in ('li', 'lo'))
    return dict(c=c, a=a, b=b, z0=z0, mod_tilt=mod_tilt, pods=pods, face_P=face.P, skin_P=skin.P, chain=chain, gap=gap,
                gap_deg=gap_deg, cover=cover, radii=radii, edge_slack=edge_slack, seat=seat,
                bar_skin=bar_skin, loads=loads, path=hull_path, band=path_full, tail=tail,
                band_len=S.plen(path_full), tail_len=S.plen(tail), hull_len=S.plen(hull_path), lock_len=S.plen(lockA),
                edge_links=edge_links, edge_link_r=edge_link_r, bars=bars, cap=(cap_ax, cap_az))


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
        module_seat_gap_mm=L['seat'], bar_clear_of_skin_mm=round(L['bar_skin'], 2),
        strap_load_rel={k: round(v / mean, 2) for k, v in sorted(L['loads'].items())},
        strap_load_max_min=round(max(free.values()) / max(min(free.values()), 1e-6), 2),
        strap_tension_for_3kPa_N=round(T_3kpa, 2),
        strap_bar_to_bar_mm=round(L['hull_len'], 1),
        strap_cap_to_fold_mm=round(L['band_len'], 1),
        strap_needed_mm=round(L['band_len'] + R.TAB_L + 5.0, 1), strap_lock_A_mm=round(L['lock_len'], 1),
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
                    if z > L['z0'] - 8 and abs(x) < 27:      # at the module and its bars: not on skin
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
    # strap: the band (end cap -> slot A -> pods -> round bar B) and the folded-back tail; the parts at the
    # module follow its taper tilt, the run through the pods does not (the pods tilt by their own)
    def tilt(sh):
        if sh is None:
            return None
        sh = sh.copy()
        sh.rotate(V(0, y, L['z0']), V(1, 0, 0), math.degrees(L['mod_tilt']))
        return sh
    band_run = S.sweep_band(L['path'][::-1], y)
    nA = len(L['band']) - len(L['path'])
    full = L['band']
    k0 = full.index(L['path'][-1]) if L['path'][-1] in full else None
    ends_a = full[:k0 + 1] if k0 else full[:12]
    k1 = full.index(L['path'][0]) if L['path'][0] in full else None
    ends_b = full[k1:] if k1 else full[-20:]
    band_a = tilt(S.sweep_band(ends_a, y, step=0.4))
    band_b = tilt(S.sweep_band(ends_b, y, step=0.4))
    strap_tail = tilt(S.sweep_band(L['tail'], y, step=0.6))
    strap_parts = [x for x in (band_run, band_a, band_b, strap_tail) if x is not None]
    res['strap_cap_to_fold_mm'] = round(L['band_len'], 1)
    res['strap_tail_modelled_mm'] = round(L['tail_len'], 1)
    items = []
    wrist = None
    if with_wrist:
        wrist, hand = W.build(c)
        items.append(('wrist', wrist, R.C_SKIN))
    items += [('module_base', base, R.C_HOUSING), ('module_lid', lid, R.C_HOUSING),
              ('main_board', mplace(I['pcb']), R.C_PCB), ('board_parts', mplace(I['parts']), (0.15, 0.15, 0.15)),
              ('lipo', mplace(I['bat']), R.C_LIPO), ('button_cap', mplace(I['cap']), R.C_HOUSING),
              ('pod_shells', Part.makeCompound(PS['shells']), R.C_POD),
              ('flex', Part.makeCompound(PS['flex'] + mf + links + [tail]), R.C_FLEX),
              ('pads', Part.makeCompound(PS['gold'] + mg), R.C_GOLD),
              ('foam', Part.makeCompound(PS['foam'] + mfo), R.C_FOAM),
              ('strap', Part.makeCompound(strap_parts), R.C_STRAP)]
    res['strap_min_clear_to_skin_mm'] = strap_clearance(L)
    if cad and CHECK_CAD:
        def vol(x, ys_):
            return round(sum(x.common(q).Volume for q in ys_), 3)
        sh = PS['shells']
        inter = {}
        inter['pod_vs_pod'] = round(sum(sh[k].common(sh[k + 1]).Volume for k in range(len(sh) - 1)), 3)
        inter['pods_vs_module'] = vol(Part.makeCompound(sh), [base, lid])
        inter['band_ends_vs_module'] = vol(Part.makeCompound([x for x in (band_a, band_b) if x]), [base, lid])
        inter['band_run_vs_module'] = vol(band_run, [base, lid]) if band_run else None
        inter['tail_vs_module'] = vol(strap_tail, [base, lid]) if strap_tail else None
        sh0 = place_pod_shapes(L, shell0, flex0, [], [], use_tilt=False)['shells']
        inter['band_vs_pods_untilted'] = vol(band_run, sh0) if band_run else None   # the band twists <= 3 deg with the pods
        inter['tail_vs_pods_untilted'] = vol(strap_tail, sh0) if strap_tail else None
        inter['strap_vs_flex'] = vol(Part.makeCompound(strap_parts), links)
        inter['module_vs_flex_links'] = vol(Part.makeCompound(links), [base])
        if wrist is not None:
            inter['pods_vs_wrist'] = vol(wrist, sh)
            inter['module_vs_wrist'] = vol(wrist, [base, lid])
            inter['pads_vs_wrist'] = vol(wrist, PS['gold'] + mg)       # pads pressed in (foam takes it)
        res['interference_mm3'] = inter
        res['strap_to_module_min_mm'] = round(min(x.distToShape(Part.makeCompound([base, lid]))[0] for x in (band_run, strap_tail) if x), 2)
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
    # one strap for all sizes: the single-pass hook-and-loop strap, size L (rc.STRAP_*): 302 mm, loop panel
    # 127-202 mm and hook tab 258-302 mm from the ring end. Cut c mm off the ring end (at least the ring's
    # sewn loop, RING_CUT) so that the hook tab, folded back at bar B, lands on the loop panel.
    def cut_range(F):
        L0, (p0, p1), (h0, h1) = R.STRAP_L, R.STRAP_PANEL, R.STRAP_HOOK
        # positions from the cut end (the lock tip); the fold at F folds the tail back onto the band
        lo = (p0 - (2 * F - L0)) / 2 + 0.0           # hook start on the panel start
        hi = (p1 - (2 * F - h0)) / 2                   # hook end on the panel end
        return round(lo, 1), round(hi, 1)
    results['strap_length_mm'] = dict(
        strap=R.STRAP_L, ring_cut_min=R.RING_CUT,
        fold_from_lock_tip={k: results[k]['strap_cap_to_fold_mm'] for k in ('145', '160', '180')},
        cut_from_ring_end_mm={k: cut_range(results[k]['strap_cap_to_fold_mm']) for k in ('145', '160', '180')},
        note='open strap: ring end cut off and locked round bar A (pinch lock), band through the pods, up through '
             'slot B, folded back so the hook tab lands on the loop panel; cut c inside the range (at least the '
             'ring loop); where the range ends below the ring cut, part of the hook still lands on the panel')
    with open(os.path.join(HERE, 'fit_results.json'), 'w') as f:
        json.dump(results, f, indent=1)
    log("strap length: " + json.dumps(results['strap_length_mm']))
    R.finish(log)
