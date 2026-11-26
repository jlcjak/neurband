"""fit.py - 2D fit of the band on wrist cross-sections (pure Python; matplotlib only for the plot).

What it answers, for the new cradle design and for the flat case it replaces:
  - how the module seats on the dorsal wrist (gap under each edge of the six module electrodes)
  - where the strap leaves the module and whether it presses pods 2 and 5 or bridges over them
  - how much of the strap tension each pod receives (strap turning angle over the pod)
  - clearance between the strap lugs and pods 2 / 5

Wrists: three ellipses (145 / 160 / 180 mm, the old size model), one shaped like the owner's
(small, flat across the back, read off the photo of 2026-11-26) and the same with the extensor
tendons raised (hand bent back). Run: python3 mech/rev_c/fit.py   -> logs/fit.log, renders/fit_*.png
"""
import os, sys, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import params as P


# ---------------- wrist cross-sections ----------------
class Wrist:
    """Closed convex-ish curve, tabulated by arc length from the dorsal centre toward +X."""

    def __init__(self, name, circ, ratio=1.35, n=2.0, ridge=0.0, ridge_w=3.5, ridge_x=(-2.0, 4.5), N=6000):
        self.name, self.circ = name, circ
        # unit shape, then scale to the circumference
        def shape(scale):
            pts = []
            for k in range(N + 1):
                phi = math.pi / 2 - 2 * math.pi * k / N
                c, s = math.cos(phi), math.sin(phi)
                x = scale * ratio * math.copysign(abs(c) ** (2.0 / n), c)
                z = scale * math.copysign(abs(s) ** (2.0 / n), s)
                if ridge and z > 0:                       # tendons standing up on the back of the wrist
                    z += sum(ridge * math.exp(-((x - x0) / ridge_w) ** 2) for x0 in ridge_x)
                pts.append((x, z))
            return pts
        def perim(pts):
            return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        ridge_mm, ridge = ridge, 0.0
        p1 = perim(shape(1.0))
        ridge = ridge_mm
        self.b = circ / p1
        self.a = ratio * self.b
        pts = shape(self.b)
        top = max(z for _, z in pts)
        self.pts = [(x, z - top) for x, z in pts]         # dorsal apex at z = 0
        self.s = [0.0]
        for i in range(1, len(self.pts)):
            self.s.append(self.s[-1] + math.dist(self.pts[i - 1], self.pts[i]))
        self.P = self.s[-1]

    def at(self, s):
        """(x, z, tangent angle) at arc length s; tangent points in the direction of increasing s."""
        s = s % self.P
        lo, hi = 0, len(self.s) - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            if self.s[m] <= s:
                lo = m
            else:
                hi = m
        f = (s - self.s[lo]) / max(self.s[hi] - self.s[lo], 1e-12)
        (x0, z0), (x1, z1) = self.pts[lo], self.pts[hi]
        return x0 + f * (x1 - x0), z0 + f * (z1 - z0), math.atan2(z1 - z0, x1 - x0)

    def frame(self, s):
        """Point, unit tangent and outward unit normal."""
        x, z, a = self.at(s)
        t = (math.cos(a), math.sin(a))
        n = (-t[1], t[0])
        # outward: for travel dorsal -> +X the outward normal is to the left of the tangent
        return (x, z), t, n

    def top_z(self, x):
        """Height of the dorsal surface at x (upper half), -inf outside the wrist."""
        best = -1e9
        half = len(self.pts) // 4 + 5
        for seg in (range(0, half), range(len(self.pts) - half - 1, len(self.pts) - 1)):
            for i in seg:
                (x0, z0), (x1, z1) = self.pts[i], self.pts[i + 1]
                if (x0 - x) * (x1 - x) <= 0 and x0 != x1:
                    best = max(best, z0 + (z1 - z0) * (x - x0) / (x1 - x0))
        return best

    def s_of_x(self, x):
        """Arc length of the dorsal point above x (signed: negative on the -X side)."""
        best, bs = 1e9, 0.0
        q = len(self.pts) // 4
        for i in list(range(0, q)) + list(range(len(self.pts) - q, len(self.pts))):
            px, pz = self.pts[i]
            if abs(px - x) < best:
                best, bs = abs(px - x), self.s[i]
        return bs if bs < self.P / 2 else bs - self.P


WRISTS = [
    Wrist('owner', 157.0, ratio=1.35, n=2.3),
    Wrist('owner_tendons', 157.0, ratio=1.35, n=2.3, ridge=1.5),
    Wrist('ellipse_145', 145.0, ratio=1.29),
    Wrist('ellipse_160', 160.0, ratio=1.29),
    Wrist('ellipse_180', 180.0, ratio=1.29),
]


# ---------------- the two designs, as 2D profiles in the module frame ----------------
def design_new():
    """Module-frame geometry of the cradle design."""
    e = []                                         # electrode faces: (x_inner, z_inner, x_outer, z_outer)
    phi = P.POD_TILT
    for sx in (1, -1):
        cx, cz = sx * P.R_DESIGN * math.sin(phi), P.SKIN_ZC + P.R_DESIGN * math.cos(phi)
        tx, tz = math.cos(phi), -math.sin(phi)
        r = P.PAD_D / 2
        e.append(((sx * (abs(cx) - r * tx), cz - r * tz), (sx * (abs(cx) + r * tx), cz + r * tz)))
    hard = []                                      # plastic that must stay off the skin: (x, z)
    for i in range(-80, 81):
        x = P.XC + P.BODY_HX * i / 80.0
        hard.append((x, P.facet_z(x)))
    anchors, lug_pts = {}, []
    for sx in (1, -1):
        x0 = P.XC + sx * P.BODY_HX
        for i in range(41):
            x = x0 + sx * (P.LUG_HX - P.BODY_HX) * i / 40
            z_ear = P.lug_under_z(x)
            hard.append((x, z_ear))
            lug_pts.append((x, z_ear))
        # Sewn 22 mm nylon loop wraps directly around the printed cross-bar (xp, BAR_ZC)
        xp = P.XC + sx * (P.BODY_HX + P.PIN_DX)
        zp = P.BAR_ZC
        anchors[sx] = (xp + sx * (P.BAR_W / 2), zp - P.BAR_H / 2 - P.STRAP_T)
    return dict(name='cradle (new)', electrodes=e, hard=hard, anchors=anchors, lugs=lug_pts,
                top=P.Z_TOP, half=P.BODY_HX, xc=P.XC, lug_hx=P.LUG_HX,
                pod_floor=P.STANDOFF + P.POD_FLOOR_T, pod_w=P.POD_SHELL_W, pod_h=P.STANDOFF + P.POD_FLOOR_T,
                outline=[(P.XC - P.BODY_HX, P.Z_TOP), (P.XC + P.BODY_HX, P.Z_TOP)])


def design_old():
    """The flat case of 2026-11-25: 33.6 wide, lugs to +/-24.35 at the base plane, TPU pad + mesas below."""
    carrier, mesa, standoff = 1.35, 0.60, 0.77
    zf = -(carrier + mesa + standoff)              # electrode plane below the flat base bottom (z = 0)
    e = [((sx * (9 - 3.25), zf), (sx * (9 + 3.25), zf)) for sx in (1, -1)]
    hard = [(x / 2.0, -(carrier + (mesa if 4.0 <= abs(x / 2.0) <= 14.0 else 0.0))) for x in range(-30, 31)]
    hard += [(sx * x, 0.0) for sx in (1, -1) for x in (16.8, 20.0, 24.35)]
    anchors = {1: (19.15, 3.55 - 1.2), -1: (-24.35, -1.9)}   # ring in the hook trough / strap under the closed bar
    return dict(name='flat case (old)', electrodes=e, hard=hard, anchors=anchors, lugs=[(sx * 24.35, 0.0) for sx in (1, -1)],
                top=10.5, half=16.8, xc=0.0, lug_hx=24.35,
                pod_floor=standoff + 1.35 + 1.0, pod_w=11.6, pod_h=standoff + 5.45,
                outline=[(-16.8, 10.5), (16.8, 10.5)])


# ---------------- solve the seat, the pods and the strap ----------------
def _pt_seg(p, a, b):
    L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
    t = max(0.0, min(1.0, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / L2))
    return math.hypot(p[0] - a[0] - t * (b[0] - a[0]), p[1] - a[1] - t * (b[1] - a[1]))


def _inside(p, poly):
    sgn = None
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        c = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        if sgn is None:
            sgn = c > 0
        elif (c > 0) != sgn:
            return False
    return True


FOAM_TRAVEL = 0.30        # how much further a foam dot can compress beyond its worn height


def seat(w, d):
    """Lower the module (level, centred on the dorsal apex) until the electrodes carry it.
    Returns z offset of the module frame and the gap under each electrode edge (inner, outer)."""
    pts = [p for el in d['electrodes'] for p in el]
    z0 = max(w.top_z(x) - z for x, z in pts)        # first electrode edge to touch
    gaps = [(z0 + el[0][1] - w.top_z(el[0][0]), z0 + el[1][1] - w.top_z(el[1][0])) for el in d['electrodes']]
    # plastic that would touch the skin before the electrodes do lifts the module instead
    lift = max((w.top_z(x) - (z0 + z) for x, z in d['hard'] if w.top_z(x) > -1e8), default=-1.0)
    return z0, gaps, lift


def solve(w, d):
    z0, gaps, lift = seat(w, d)
    if lift > 0:                                    # module rides on its plastic: electrodes lose that much
        z0 += lift
        gaps = [(a + lift, b + lift) for a, b in gaps]
    # pods: 3 and 4 are on the module; the others follow the flex, 18 mm apart along the skin
    s3 = w.s_of_x(sum(p[0] for p in d['electrodes'][0]) / 2)
    s4 = w.s_of_x(sum(p[0] for p in d['electrodes'][1]) / 2)
    pod_s = {3: s3, 4: s4, 2: s3 + P.PITCH, 1: s3 + 2 * P.PITCH}
    for k in range(5, 9):
        pod_s[k] = s4 - (k - 4) * P.PITCH
    pods = {}
    for k, s in pod_s.items():
        if k in (3, 4):
            continue
        c, t, n = w.frame(s)
        hw = d['pod_w'] / 2
        f = d['pod_floor']
        pods[k] = dict(s=s, c=c, t=t, n=n,
                       floor=[(c[0] + t[0] * u + n[0] * f, c[1] + t[1] * u + n[1] * f) for u in (-hw, hw)],
                       box=[(c[0] + t[0] * u + n[0] * v, c[1] + t[1] * u + n[1] * v)
                            for u, v in ((-hw, 0.3), (hw, 0.3), (hw, d['pod_h']), (-hw, d['pod_h']))])
    # strap: taut line from the +X anchor, over pods 2, 1, the bare skin of the gap, pods 8..5, to the -X anchor
    A = {sx: (x, z + z0) for sx, (x, z) in d['anchors'].items()}
    chain = [('A+', A[1])]
    for k in (2, 1):
        chain += [(k, pods[k]['floor'][0]), (k, pods[k]['floor'][1])]
    sa, sb = pod_s[1] + d['pod_w'] / 2 + 1.0, pod_s[8] + w.P - d['pod_w'] / 2 - 1.0
    m = max(2, int((sb - sa) / 2.0))
    for i in range(m + 1):
        c, t, n = w.frame(sa + (sb - sa) * i / m)
        chain.append(('skin', c))
    for k in (8, 7, 6, 5):
        chain += [(k, pods[k]['floor'][0]), (k, pods[k]['floor'][1])]
    chain.append(('A-', A[-1]))
    # travel is clockwise seen from the hand (dorsal -> +X -> volar): keep only right turns
    hull = []
    for item in chain:
        while len(hull) >= 2:
            (x0, y0), (x1, y1), (x2, y2) = hull[-2][1], hull[-1][1], item[1]
            if (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1) >= -1e-9:   # left turn or straight: point is slack
                hull.pop()
            else:
                break
        hull.append(item)
    # turning per support = share of the strap tension pressing it
    turn = {}
    for i in range(1, len(hull) - 1):
        (x0, y0), (x1, y1), (x2, y2) = hull[i - 1][1], hull[i][1], hull[i + 1][1]
        a0, a1 = math.atan2(y1 - y0, x1 - x0), math.atan2(y2 - y1, x2 - x1)
        dth = (a0 - a1 + math.pi) % (2 * math.pi) - math.pi
        turn[hull[i][0]] = turn.get(hull[i][0], 0.0) + dth
    # module: pulled by the two strands that leave the anchors
    def unit(p, q):
        L = math.dist(p, q)
        return ((q[0] - p[0]) / L, (q[1] - p[1]) / L)
    u1, u2 = unit(hull[0][1], hull[1][1]), unit(hull[-1][1], hull[-2][1])
    down = -(u1[1] + u2[1])                         # net pull toward the wrist, in units of strap tension
    force = {k: round(turn.get(k, 0.0), 3) for k in (1, 2, 5, 6, 7, 8)}
    force[3] = force[4] = round(down / 2, 3)
    # lug to pod 2 / 5 clearance
    lug_gap = {}
    for sx, k in ((1, 2), (-1, 5)):
        tip = [(x, z + z0) for x, z in d['lugs'] if x * sx > 0]
        box = pods[k]['box']
        g = min(_pt_seg(p, box[i], box[(i + 1) % 4]) for p in tip for i in range(4))
        inside = any(_inside(p, box) for p in tip)
        lug_gap[k] = round(-g if inside else g, 2)
    return dict(z0=z0, gaps=gaps, lift=lift, pods=pods, hull=hull, force=force,
                lug_gap=lug_gap, anchors=A, top_above_skin=z0 + d['top'])


def report(log):
    out = {}
    for d in (design_old(), design_new()):
        log(f"\n== {d['name']} ==")
        log("wrist           top above skin | module electrode gaps in/out (mm)      | lug-to-pod 2/5 | strap share per pod 1..8 (x tension) | min/max")
        for w in WRISTS:
            r = solve(w, d)
            g = r['gaps']
            f = r['force']
            vals = [f[k] for k in range(1, 9)]
            worst = max(max(a, b) for a, b in g)
            log(f"{w.name:15s} {r['top_above_skin']:6.2f}        | +X {g[0][0]:.2f}/{g[0][1]:.2f}  -X {g[1][0]:.2f}/{g[1][1]:.2f}  worst {worst:.2f} "
                f"| {r['lug_gap'][2]:+.2f} {r['lug_gap'][5]:+.2f}    | " + ' '.join(f"{v:.2f}" for v in vals) +
                f" | {min(vals):.2f}/{max(vals):.2f}" + (f"   RIDES ON PLASTIC +{r['lift']:.2f}" if r['lift'] > 0 else ''))
            out[(d['name'], w.name)] = r
    return out


def plot(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    os.makedirs(os.path.join(HERE, 'renders'), exist_ok=True)
    for w in WRISTS:
        fig, axes = plt.subplots(1, 2, figsize=(13, 6.2))
        for ax, d in zip(axes, (design_old(), design_new())):
            r = out[(d['name'], w.name)]
            xs, zs = zip(*w.pts)
            ax.fill(xs, zs, color='#e9c3a8', zorder=1)
            z0 = r['z0']
            # module body
            if 'new' in d['name']:
                under = [(x, P.facet_z(x) + z0) for x in [P.XC - P.BODY_HX + i * 2 * P.BODY_HX / 60 for i in range(61)]]
                body = [(P.XC - P.BODY_HX, z0 + P.Z_TOP), (P.XC + P.BODY_HX, z0 + P.Z_TOP)] + under[::-1]
                ax.fill(*zip(*body), color='#3d7fd9', zorder=3)
                for sx in (1, -1):
                    x0, x1 = P.XC + sx * (P.BODY_HX + P.SLOT_GAP), P.XC + sx * P.LUG_HX
                    bar = [(x0, z0), (x1, z0), (x1, z0 + P.bar_under_z(x1)), (x0, z0 + P.bar_under_z(x0))]
                    ax.fill(*zip(*bar), color='#2a5ea8', zorder=3)
            else:
                ax.fill([-16.8, 16.8, 16.8, -16.8], [z0, z0, z0 + 10.5, z0 + 10.5], color='#3d7fd9', zorder=3)
                ax.fill([-24.35, -20.2, -20.2, -24.35], [z0, z0, z0 + 4.9, z0 + 4.9], color='#2a5ea8', zorder=3)
                ax.fill([17.45, 24.35, 24.35, 20.85, 20.85, 17.45], [z0, z0, z0 + 7.6, z0 + 7.6, z0 + 1.85, z0 + 1.85], color='#2a5ea8', zorder=3)
                ax.fill([-14.8, 14.8, 14.8, -14.8], [z0 - 1.35, z0 - 1.35, z0, z0], color='#8a8f99', zorder=3)
            for el in d['electrodes']:
                ax.plot([el[0][0], el[1][0]], [el[0][1] + z0, el[1][1] + z0], color='#d4a017', lw=3, zorder=5)
            for k, pd in r['pods'].items():
                ax.fill(*zip(*pd['box']), color='#444a55', zorder=3)
                ax.text(pd['c'][0] + pd['n'][0] * 9, pd['c'][1] + pd['n'][1] * 9, f"{r['force'][k]:.2f}", ha='center', va='center', fontsize=8)
            ax.text(0, z0 + d['top'] + 3, f"3, 4: {r['force'][3]:.2f}", ha='center', fontsize=8)
            hx, hz = zip(*[p for _, p in r['hull']])
            ax.plot(hx, hz, color='#1b3a8a', lw=1.6, zorder=4)
            ax.set_aspect('equal')
            label = {'owner': 'owner\'s wrist (157 mm)', 'owner_tendons': 'owner\'s wrist (157 mm), tendons up'}.get(
                w.name, w.name.replace('ellipse_', 'elliptical wrist, ') + ' mm')
            ax.set_title(f"{d['name']}, {label}\ncase top {r['top_above_skin']:.1f} mm above the skin; "
                         f"gap under a module electrode edge up to {max(max(a, b) for a, b in r['gaps']):.2f} mm", fontsize=10)
            ax.set_xlim(-45, 45); ax.set_ylim(-2 * w.b - 14, 22)
            ax.axis('off')
        fig.suptitle("Cross-section at the band, seen from the hand. Numbers: how much of the strap tension presses each pod onto the skin.", fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, 'renders', f'fit_{w.name}.png'), dpi=110)
        plt.close(fig)


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'logs'), exist_ok=True)
    f = open(os.path.join(HERE, 'logs', 'fit.log'), 'w')
    def log(*a):
        s = ' '.join(str(x) for x in a)
        print(s); f.write(s + '\n')
    for w in WRISTS:
        log(f"{w.name}: circumference {w.circ:.0f}, width {2 * w.a:.1f}, depth {2 * w.b:.1f}, dorsal drop at x=9/15/20: "
            f"{-w.top_z(9):.2f} / {-w.top_z(15):.2f} / {-w.top_z(20):.2f}")
    out = report(log)
    if '--noplot' not in sys.argv:
        plot(out)
        log("plots: renders/fit_<wrist>.png")
    f.close()
