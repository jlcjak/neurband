"""fitgeom.py - shared wrist / band geometry for neurband (pure python, no FreeCAD).

Frame used everywhere (right forearm, palm down):
  X = radial(+) / ulnar(-)   (width of the wrist ellipse)
  Y = along the arm, hand toward -Y (front), elbow toward +Y; wrist crease at y = 0
  Z = dorsal(+) / volar(-)   (depth of the wrist ellipse), Z up
Arc length s on a cross-section curve starts at the dorsal centre (x=0, z>0) and runs
toward the radial side (+X), around the volar side, and back via the ulnar side.
"""
import math

# ---------------- wrist model parameters (mm) ----------------
FOREARM_LEN = 70.0        # crease -> proximal end of the model
RATIO_CREASE = 1.35       # width:depth at the wrist crease
RATIO_PROX = 1.18         # width:depth at 70 mm (rounder)
CIRC_GROWTH = 0.09        # circumference grows 9 % from crease to 70 mm
BAND_Y = 25.0             # band centre line, mm proximal of the crease

# ---------------- band stack parameters (mm) ----------------
DOME_H = 1.2              # electrode dome protrusion below the flex
FLEX_T = 0.2              # polyimide
SHELL_T = 2.5             # pod shell backing plate
STRAP_T = 1.3             # elastic webbing thickness
CHANNEL_H = 1.35          # snap channel clear height under the lips
LIP_T = 0.4               # lip thickness on top of the channel rails
D_FLEX = DOME_H + FLEX_T / 2                 # flex neutral plane above skin
D_SHELL_TOP = DOME_H + FLEX_T + SHELL_T      # top of the backing plate (channel floor)
D_STRAP = D_SHELL_TOP + STRAP_T / 2          # strap mid-plane (same on every pod)
D_POD_TOP = D_SHELL_TOP + CHANNEL_H + LIP_T  # top of the rails = housing seat

N_PODS = 16
TAIL_AFTER = 4            # tail leaves between pod 4 and pod 5 (dorsal centre)


def ellipse_perimeter(a, b):
    h = ((a - b) / (a + b)) ** 2
    return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))


def section(c_band, y):
    """Semi-axes (a = half width along X, b = half depth along Z) of the forearm at y."""
    c0 = c_band / (1 + CIRC_GROWTH * BAND_Y / FOREARM_LEN)
    t = y / FOREARM_LEN
    c = c0 * (1 + CIRC_GROWTH * t)
    r = RATIO_CREASE + (RATIO_PROX - RATIO_CREASE) * t
    # perimeter is linear in b for a fixed ratio
    b = c / ellipse_perimeter(r, 1.0)
    return r * b, b


class Curve:
    """Ellipse (a, b) offset outward by d, tabulated by arc length from the dorsal centre."""

    def __init__(self, a, b, d=0.0, n=4000):
        self.a, self.b, self.d = a, b, d
        pts = []
        for k in range(n + 1):
            phi = math.pi / 2 - 2 * math.pi * k / n   # dorsal top, toward +X first
            x, z = a * math.cos(phi), b * math.sin(phi)
            nx, nz = b * math.cos(phi), a * math.sin(phi)
            ln = math.hypot(nx, nz)
            pts.append((x + d * nx / ln, z + d * nz / ln))
        self.pts = pts
        s = [0.0]
        for k in range(1, len(pts)):
            s.append(s[-1] + math.dist(pts[k - 1], pts[k]))
        self.s = s
        self.P = s[-1]

    def at(self, s):
        """(x, z, tangent angle) at arc length s (wraps)."""
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

    def turn(self, s0, s1):
        """Tangent turning (rad, positive = convex) between s0 and s1."""
        a0, a1 = self.at(s0)[2], self.at(s1)[2]
        d = a0 - a1                     # clockwise travel -> angle decreases
        return (d + math.pi) % (2 * math.pi) - math.pi


def pod_s(i, pitch):
    """Arc position of pod i (1..16) centre on the flex curve; tail at s = 0."""
    return (i - TAIL_AFTER - 0.5) * pitch


def fit(c_band, pitch, pod_w, housing_r=44.0, housing_chord=34.0, min_link=None):
    a, b = section(c_band, BAND_Y)
    skin = Curve(a, b, 0.0)
    flex = Curve(a, b, D_FLEX)
    top = Curve(a, b, D_POD_TOP)
    strap = Curve(a, b, D_STRAP)
    link = pitch - pod_w
    ss = [pod_s(i, pitch) for i in range(1, N_PODS + 1)]
    # bend radius of every flex link (pods are rigid tangent plates, link = arc)
    radii = []
    for i in range(N_PODS - 1):
        th = flex.turn(ss[i], ss[i + 1])
        radii.append(link / th if th > 1e-9 else float('inf'))
    chain = (N_PODS - 1) * pitch + pod_w
    gap = flex.P - chain
    # gap centre, measured from dorsal centre toward the ulnar side (negative s)
    s_first_edge = ss[0] - pod_w / 2
    gap_mid = s_first_edge - gap / 2
    gap_deg = -gap_mid / flex.P * 360.0          # 90 deg = exactly at the ulnar apex
    # strap normal force per pod ~ T * turning of the strap over one pitch
    forces = [strap.turn(s - pitch / 2, s + pitch / 2) for s in ss]
    # rigid housing seat (chord across the wrist) vs. pod-top curve
    half = housing_chord / 2
    xs, zs, _ = top.at(0.0)
    xe, ze, _ = top.at(half)
    xw, zw, _ = top.at(-half)
    sag_wrist = zs - (ze + zw) / 2               # sagitta of the pod-top surface over the chord
    cx = (abs(xe) + abs(xw)) / 2
    sag_house = housing_r - math.sqrt(housing_r ** 2 - cx ** 2)
    # local radius of the pod-top surface at the dorsal centre
    r_top = top.a ** 2 / top.b if False else (cx ** 2 + sag_wrist ** 2) / (2 * sag_wrist)
    return dict(c=c_band, a=a, b=b, P_skin=skin.P, P_flex=flex.P, pitch=pitch, pod_w=pod_w,
                link=link, chain=chain, gap=gap, gap_deg=gap_deg,
                cover_frac=chain / flex.P, cover_skin=chain / flex.P * skin.P,
                rmin=min(radii), radii=radii, overlap=link < 0,
                force_ratio=max(forces) / min(forces), forces=forces,
                sag_wrist=sag_wrist, sag_house=sag_house, rock=sag_wrist - sag_house,
                r_dorsal_skin=a * a / b, r_seat=r_top, pod_s=ss)


if __name__ == '__main__':
    for c in (130, 140, 148, 160, 169, 180, 193, 200, 220):
        a, b = section(c, BAND_Y)
        print(f"C={c}: a={a:.1f} b={b:.1f} ratio={a/b:.3f} R_dorsal={a*a/b:.1f} R_side={b*b/a:.1f}")
