"""fit.py - 2D fit of the rev C2 band on wrist cross-sections (pure Python; matplotlib only for the plots).

What it answers, for rev C2 and for the rev C1 cradle it replaces:
  - how the module seats on the back of the wrist: gap under the edges of its six electrodes and
    whether any plastic (the lugs of rev C1) reaches the skin first
  - how the strap leaves the bars: how much of the strap tension pushes the module down, and how
    much presses pods 2 and 5, the two next to the module
  - how much room the stiff sewn end of the strap has between a bar and the first pod

Wrists: the owner's 157 mm wrist as it was read off a photo for rev C1, the same wrist with a flat
back (what the owner reported after wearing rev C1), and three ellipses (145 / 160 / 180 mm).
Run: python3 mech/rev_c2/fit.py   -> logs/fit.log, renders/fit_<wrist>.png
"""
import os, sys, math, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import params as P


# ---------------- wrist cross-sections ----------------
class Wrist:
    """Closed curve, tabulated by arc length from the middle of the back of the wrist toward +X.
    A superellipse: n = 2 is an ellipse, larger n is flatter on that half."""

    def __init__(self, name, circ, ratio=1.35, n_dorsal=2.0, n_volar=None, N=6000):
        self.name, self.circ = name, circ
        n_volar = n_dorsal if n_volar is None else n_volar

        def shape(scale):
            pts = []
            for k in range(N + 1):
                phi = math.pi / 2 - 2 * math.pi * k / N
                c, s = math.cos(phi), math.sin(phi)
                n = n_dorsal if s > 0 else n_volar
                pts.append((scale * ratio * math.copysign(abs(c) ** (2.0 / n), c), scale * math.copysign(abs(s) ** (2.0 / n), s)))
            return pts

        def perim(pts):
            return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        self.b = circ / perim(shape(1.0))
        self.a = ratio * self.b
        pts = shape(self.b)
        top = max(z for _, z in pts)
        self.pts = [(x, z - top) for x, z in pts]         # back of the wrist at z = 0
        self.s = [0.0]
        for i in range(1, len(self.pts)):
            self.s.append(self.s[-1] + math.dist(self.pts[i - 1], self.pts[i]))
        self.P = self.s[-1]

    def at(self, s):
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
        return (x, z), t, (-t[1], t[0])

    def top_z(self, x):
        best = -1e9
        half = len(self.pts) // 4 + 5
        for seg in (range(0, half), range(len(self.pts) - half - 1, len(self.pts) - 1)):
            for i in seg:
                (x0, z0), (x1, z1) = self.pts[i], self.pts[i + 1]
                if (x0 - x) * (x1 - x) <= 0 and x0 != x1:
                    best = max(best, z0 + (z1 - z0) * (x - x0) / (x1 - x0))
        return best

    def s_of_x(self, x):
        best, bs = 1e9, 0.0
        q = len(self.pts) // 4
        for i in list(range(0, q)) + list(range(len(self.pts) - q, len(self.pts))):
            px, pz = self.pts[i]
            if abs(px - x) < best:
                best, bs = abs(px - x), self.s[i]
        return bs if bs < self.P / 2 else bs - self.P


WRISTS = [
    Wrist('owner_flat', 157.0, ratio=1.45, n_dorsal=3.0, n_volar=2.2),
    Wrist('owner_photo', 157.0, ratio=1.35, n_dorsal=2.3),
    Wrist('ellipse_145', 145.0, ratio=1.29),
    Wrist('ellipse_160', 160.0, ratio=1.29),
    Wrist('ellipse_180', 180.0, ratio=1.29),
]
LABEL = {'owner_flat': "owner's wrist, flat back (157 mm)", 'owner_photo': "owner's wrist as read off the photo (157 mm)",
         'ellipse_145': 'elliptical wrist, 145 mm', 'ellipse_160': 'elliptical wrist, 160 mm', 'ellipse_180': 'elliptical wrist, 180 mm'}


# ---------------- the designs, as 2D profiles in the module frame ----------------
def tub_under(x):
    """Wrist side of the rev C2 tub at module X (y = 0 section): runners, tunnel, bevels. None outside the body."""
    if abs(x - P.XC) > P.BODY_HX:
        return None
    ax = abs(x)
    if ax <= P.TUNNEL_TOP_HX:
        return -P.T_FLOOR
    if ax < P.RIDGE_IN:
        return -P.T_FLOOR - (ax - P.TUNNEL_TOP_HX)
    if ax <= P.RIDGE_OUT:
        return P.Z_SKIN
    return P.Z_SKIN + (ax - P.RIDGE_OUT)


def lug_under(x):
    return P.Z_WALL0 + (abs(x - P.XC) - P.BODY_HX) / math.tan(math.radians(P.LUG_UNDER_DEG))


def design_c2():
    ze = P.Z_SKIN - P.TAPE_T - P.FLEX_T                       # electrode faces
    r = P.PAD_D / 2
    e = [((sx * (P.PITCH / 2 - r), ze), (sx * (P.PITCH / 2 + r), ze)) for sx in (1, -1)]
    hard = [(P.XC + P.BODY_HX * i / 80.0, tub_under(P.XC + P.BODY_HX * i / 80.0)) for i in range(-80, 81)]
    lugs = []
    for sx in (1, -1):
        for i in range(21):
            x = P.XC + sx * (P.BODY_HX + P.LUG_X * i / 20)
            lugs.append((x, lug_under(x)))
    hard += lugs
    anchors = {sx: (P.XC + sx * (P.BODY_HX + P.PIN_DX + P.BAR_W / 2), P.Z_BAR - P.BAR_H / 2 - P.STRAP_T) for sx in (1, -1)}
    lift = P.TAPE_T + P.FLEX_T
    return dict(name='rev C2', electrodes=e, hard=hard, anchors=anchors, lugs=lugs, top=P.Z_TOP, half=P.BODY_HX, xc=P.XC, lug_hx=P.LUG_HX,
                pod_floor=P.POD_HC + lift + P.POD_FLOOR_T, pod_w=P.POD_SHELL_W, pod_h=P.POD_HC + lift + P.POD_H, pod_gap=P.POD_HC + lift,
                bar_c={sx: (P.XC + sx * (P.BODY_HX + P.PIN_DX), P.Z_BAR) for sx in (1, -1)}, bar_w=P.BAR_W)


def design_c1():
    """The rev C1 cradle, taken from its own scripts (mech/rev_c) so nothing is retyped."""
    code = ("import json, fit as F, params as P\n"
            "d = F.design_new()\n"
            "u = [(P.XC + P.BODY_HX * i / 80.0, P.facet_z(P.XC + P.BODY_HX * i / 80.0)) for i in range(-80, 81)]\n"
            "print(json.dumps(dict(electrodes=d['electrodes'], hard=d['hard'], anchors={str(k): v for k, v in d['anchors'].items()},\n"
            "    lugs=d['lugs'], top=d['top'], half=d['half'], xc=d['xc'], lug_hx=d['lug_hx'], pod_floor=d['pod_floor'], pod_w=d['pod_w'],\n"
            "    pod_h=d['pod_h'], under=u, bar=[P.XC, P.BODY_HX + P.PIN_DX, P.BAR_ZC, P.BAR_W, P.BAR_H], standoff=P.STANDOFF)))\n")
    out = subprocess.run([sys.executable, '-c', code], cwd=os.path.join(os.path.dirname(HERE), 'rev_c'), capture_output=True, text=True, check=True)
    d = json.loads(out.stdout.strip().splitlines()[-1])
    d['anchors'] = {int(k): tuple(v) for k, v in d['anchors'].items()}
    d['electrodes'] = [tuple(tuple(p) for p in el) for el in d['electrodes']]
    d['hard'] = [tuple(p) for p in d['hard']]
    d['lugs'] = [tuple(p) for p in d['lugs']]
    d['name'] = 'rev C1 cradle'
    d['pod_gap'] = d['standoff']
    xc, dx, zc, bw, bh = d['bar']
    d['bar_c'] = {sx: (xc + sx * dx, zc) for sx in (1, -1)}
    d['bar_w'] = bw
    return d


# ---------------- solve the seat, the pods and the strap ----------------
def _pt_seg(p, a, b):
    L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
    t = max(0.0, min(1.0, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / L2))
    return math.hypot(p[0] - a[0] - t * (b[0] - a[0]), p[1] - a[1] - t * (b[1] - a[1]))


def seat(w, d):
    """Lower the module (level, centred on the back of the wrist) until its electrodes carry it.
    Returns the module's z offset, the gap under each electrode edge (inner, outer), and how far any
    plastic would have dug in (positive: it touches before the electrodes and lifts them by that much)."""
    pts = [p for el in d['electrodes'] for p in el]
    z0 = max(w.top_z(x) - z for x, z in pts)
    gaps = [(z0 + el[0][1] - w.top_z(el[0][0]), z0 + el[1][1] - w.top_z(el[1][0])) for el in d['electrodes']]
    lift = max((w.top_z(x) - (z0 + z) for x, z in d['hard'] if z is not None and w.top_z(x) > -1e8), default=-1.0)
    return z0, gaps, lift


def solve(w, d):
    z0, gaps, lift = seat(w, d)
    if lift > 0:
        z0 += lift
        gaps = [(a + lift, b + lift) for a, b in gaps]
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
        hw, f, g = d['pod_w'] / 2, d['pod_floor'], d['pod_gap']
        pods[k] = dict(s=s, c=c, t=t, n=n,
                       floor=[(c[0] + t[0] * u + n[0] * f, c[1] + t[1] * u + n[1] * f) for u in (-hw, hw)],
                       box=[(c[0] + t[0] * u + n[0] * v, c[1] + t[1] * u + n[1] * v) for u, v in ((-hw, g), (hw, g), (hw, d['pod_h']), (-hw, d['pod_h']))])
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
    hull = []
    for item in chain:
        while len(hull) >= 2:
            (x0, y0), (x1, y1), (x2, y2) = hull[-2][1], hull[-1][1], item[1]
            if (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1) >= -1e-9:
                hull.pop()
            else:
                break
        hull.append(item)
    turn = {}
    for i in range(1, len(hull) - 1):
        (x0, y0), (x1, y1), (x2, y2) = hull[i - 1][1], hull[i][1], hull[i + 1][1]
        a0, a1 = math.atan2(y1 - y0, x1 - x0), math.atan2(y2 - y1, x2 - x1)
        turn[hull[i][0]] = turn.get(hull[i][0], 0.0) + (a0 - a1 + math.pi) % (2 * math.pi) - math.pi

    def unit(p, q):
        L = math.dist(p, q)
        return ((q[0] - p[0]) / L, (q[1] - p[1]) / L)
    u1, u2 = unit(hull[0][1], hull[1][1]), unit(hull[-1][1], hull[-2][1])
    force = {k: round(turn.get(k, 0.0), 3) for k in (1, 2, 5, 6, 7, 8)}
    force[3] = round(-u1[1], 3)                           # the +X strand's pull toward the wrist, per unit of strap tension
    force[4] = round(-u2[1], 3)
    # how far each pod's strap bed lies below the taut strap (0 when the strap rests on it)
    slack = {}
    for k, pd in pods.items():
        mid = ((pd['floor'][0][0] + pd['floor'][1][0]) / 2, (pd['floor'][0][1] + pd['floor'][1][1]) / 2)
        slack[k] = min(_pt_seg(mid, hull[i][1], hull[i + 1][1]) for i in range(len(hull) - 1))
    room = {}
    for sx, k in ((1, 2), (-1, 5)):                      # from the surface of the bar to the near edge of the pod's strap bed
        bc = (d['bar_c'][sx][0], d['bar_c'][sx][1] + z0)
        near = min(pods[k]['floor'], key=lambda p: math.dist(p, bc))
        mid = (near[0], near[1] + P.STRAP_T / 2)
        room[k] = (math.dist(mid, bc) - d['bar_w'] / 2, math.degrees(math.atan2(bc[1] - mid[1], abs(mid[0] - bc[0]))))
    lug_skin = min(((z0 + z) - w.top_z(x) for x, z in d['lugs'] if w.top_z(x) > -1e8), default=99.0)
    return dict(z0=z0, gaps=gaps, lift=lift, pods=pods, hull=hull, force=force, slack=slack, room=room, lug_skin=lug_skin,
                anchors=A, top_above_skin=z0 + d['top'])


def report(log):
    out = {}
    for d in (design_c1(), design_c2()):
        log(f"\n== {d['name']} ==")
        log("wrist          case top | module electrode gaps in/out  | plastic first | lug to skin | module pull +X/-X | pods 1 2 5 6 7 8 (x tension) "
            "| bar to pod 2 / 5: room, strap angle")
        for w in WRISTS:
            r = solve(w, d)
            g, f = r['gaps'], r['force']
            log(f"{w.name:13s} {r['top_above_skin']:6.2f}   | +X {g[0][0]:.2f}/{g[0][1]:.2f}  -X {g[1][0]:.2f}/{g[1][1]:.2f} | "
                f"{('lifts %.2f' % r['lift']) if r['lift'] > 0 else 'no':>13s} | {r['lug_skin']:6.2f}      | {f[3]:.2f} / {f[4]:.2f}       | "
                + ' '.join(f"{f[k]:.2f}" for k in (1, 2, 5, 6, 7, 8))
                + f"  | {r['room'][2][0]:.1f} mm {r['room'][2][1]:.0f} deg / {r['room'][5][0]:.1f} mm {r['room'][5][1]:.0f} deg")
            out[(d['name'], w.name)] = (r, d)
    log(f"\nThe stiff sewn end of the strap is taken as {P.STRAP_COLLAR:.0f} mm long: it needs at least that much room between a bar and the first pod.")
    return out


def plot(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    os.makedirs(os.path.join(HERE, 'renders'), exist_ok=True)
    for w in WRISTS:
        fig, axes = plt.subplots(1, 2, figsize=(13, 6.2))
        for ax, name in zip(axes, ('rev C1 cradle', 'rev C2')):
            r, d = out[(name, w.name)]
            xs, zs = zip(*w.pts)
            ax.fill(xs, zs, color='#e9c3a8', zorder=1)
            z0 = r['z0']
            if name == 'rev C2':
                under = [(x, tub_under(x) + z0) for x in [P.XC - P.BODY_HX + i * 2 * P.BODY_HX / 120 for i in range(121)]]
                body = [(P.XC - P.BODY_HX, z0 + P.Z_TOP), (P.XC + P.BODY_HX, z0 + P.Z_TOP)] + under[::-1]
                ax.fill(*zip(*body), color='#3d7fd9', zorder=3)
                for sx in (1, -1):
                    xw, xt = P.XC + sx * P.BODY_HX, P.XC + sx * P.LUG_HX
                    lug = [(xw, z0 + P.Z_WALL0), (xt, z0 + lug_under(xt)), (xt, z0 + P.LUG_TOP_Z), (xw, z0 + P.LUG_TOP_Z)]
                    ax.fill(*zip(*lug), color='#2a5ea8', zorder=2)
                    xb = P.XC + sx * (P.BODY_HX + P.PIN_DX)
                    ax.add_patch(plt.Rectangle((xb - P.BAR_W / 2, z0 + P.Z_BAR - P.BAR_H / 2), P.BAR_W, P.BAR_H, color='#0f2a55', zorder=4))
            else:
                body = [(d['xc'] - d['half'], z0 + d['top']), (d['xc'] + d['half'], z0 + d['top'])] + [(x, z + z0) for x, z in d['under']][::-1]
                ax.fill(*zip(*body), color='#3d7fd9', zorder=3)
                xc, dx, zc, bw, bh = d['bar']
                for sx in (1, -1):
                    pts = sorted([(x, z) for x, z in d['lugs'] if (x - xc) * sx > 0], key=lambda p: abs(p[0] - xc))
                    lug = [(pts[0][0], z0)] + [(x, z + z0) for x, z in pts] + [(pts[-1][0], z0)]
                    ax.fill(*zip(*lug), color='#2a5ea8', zorder=2)
                    ax.add_patch(plt.Rectangle((xc + sx * dx - bw / 2, z0 + zc - bh / 2), bw, bh, color='#0f2a55', zorder=4))
            for el in d['electrodes']:
                ax.plot([el[0][0], el[1][0]], [el[0][1] + z0, el[1][1] + z0], color='#d4a017', lw=3, zorder=5)
            for k, pd in r['pods'].items():
                ax.fill(*zip(*pd['box']), color='#444a55', zorder=3)
                ax.text(pd['c'][0] + pd['n'][0] * 12, pd['c'][1] + pd['n'][1] * 12, f"{r['force'][k]:.2f}", ha='center', va='center', fontsize=8)
            ax.text(0, z0 + d['top'] + 3, f"module: {r['force'][3] + r['force'][4]:.2f}", ha='center', fontsize=8)
            hx, hz = zip(*[p for _, p in r['hull']])
            ax.plot(hx, hz, color='#1b3a8a', lw=1.6, zorder=4)
            ax.set_aspect('equal')
            note = f"lugs touch first, electrodes lifted {r['lift']:.1f} mm" if r['lift'] > 0 else \
                f"electrodes carry it; gap under an electrode edge up to {max(max(a, b) for a, b in r['gaps']):.2f} mm"
            ax.set_title(f"{name}, {LABEL[w.name]}\ncase top {r['top_above_skin']:.1f} mm above the skin; {note}", fontsize=9.5)
            ax.set_xlim(-46, 46)
            ax.set_ylim(-2 * w.b - 14, 24)
            ax.axis('off')
        fig.suptitle("Cross-section at the band, seen from the hand. Numbers: share of the strap tension pressing each pod and the module onto the skin.", fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, 'renders', f'fit_{w.name}.png'), dpi=110)
        plt.close(fig)


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'logs'), exist_ok=True)
    f = open(os.path.join(HERE, 'logs', 'fit.log'), 'w')

    def log(*a):
        s = ' '.join(str(x) for x in a)
        print(s)
        f.write(s + '\n')
    for w in WRISTS:
        log(f"{w.name}: circumference {w.circ:.0f}, width {2 * w.a:.1f}, depth {2 * w.b:.1f}, the back drops at x = 9 / 15 / 20 / 25: "
            + ' / '.join(f"{-w.top_z(x):.2f}" for x in (9, 15, 20, 25)))
    out = report(log)
    if '--noplot' not in sys.argv:
        plot(out)
        log("plots: renders/fit_<wrist>.png")
    f.close()
