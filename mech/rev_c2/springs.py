"""springs.py - the pod's spring wing as a 2D frame (pure Python + numpy; matplotlib only for the plot).

The wing is a 0.6 mm PLA blade printed on its side, so every layer is one bead that runs the
length of the blade. It leaves the plate beside the middle pad, runs low under the pad's cap, ramps
up and ends in the flat that carries one electrode. This model gives stiffness, surface strain, tilt
and shift per millimetre of travel; params.py holds the rounded results (WING_K, WING_STRAIN, ...).

Run: python3 mech/rev_c2/springs.py   -> logs/springs.log, renders/pod_spring.png
"""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import params as P

E_PLA = 3300.0          # MPa along the beads (2800 .. 3500 for printed PLA)


def frame(nodes, elems, fixed, loads, E=E_PLA):
    """Linear Euler-Bernoulli frame. nodes (n, 2); elems (i, j, thickness, width); loads node -> (Fu, Fh, M)."""
    n = len(nodes)
    K = np.zeros((3 * n, 3 * n))
    geo = []
    for i, j, t, w in elems:
        (x0, y0), (x1, y1) = nodes[i], nodes[j]
        L = math.hypot(x1 - x0, y1 - y0)
        c, s = (x1 - x0) / L, (y1 - y0) / L
        A, I = w * t, w * t ** 3 / 12
        k = np.zeros((6, 6))
        a, b = E * A / L, E * I / L ** 3
        k[0, 0] = k[3, 3] = a
        k[0, 3] = k[3, 0] = -a
        kb = b * np.array([[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L],
                           [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]])
        idx = [1, 2, 4, 5]
        for p in range(4):
            for q in range(4):
                k[idx[p], idx[q]] = kb[p, q]
        R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
        T = np.zeros((6, 6))
        T[:3, :3] = R
        T[3:, 3:] = R
        dof = [3 * i, 3 * i + 1, 3 * i + 2, 3 * j, 3 * j + 1, 3 * j + 2]
        K[np.ix_(dof, dof)] += T.T @ k @ T
        geo.append((L, R, dof, t))
    F = np.zeros(3 * n)
    for nd, (fu, fh, m) in loads.items():
        F[3 * nd:3 * nd + 3] += (fu, fh, m)
    free = [d for d in range(3 * n) if d // 3 not in fixed]
    U = np.zeros(3 * n)
    U[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
    strain = []
    for L, R, dof, t in geo:
        ui, uj = R @ U[dof[:3]], R @ U[dof[3:]]
        v0, th0, v1, th1 = ui[1], ui[2], uj[1], uj[2]
        k0 = (-6 * v0 - 4 * L * th0 + 6 * v1 - 2 * L * th1) / L ** 2
        k1 = (6 * v0 + 2 * L * th0 - 6 * v1 + 4 * L * th1) / L ** 2
        strain.append(max(abs(k0), abs(k1)) * t / 2 + abs(uj[0] - ui[0]) / L)
    return U, strain


def wing_centre_line(t=P.WING_T, w=P.POD_SHELL_W, n=30):
    """Free-state centre line of one wing: root post, low arm, ramp, pad. Returns nodes, elems, ids."""
    (a, b, tilt) = P.wing_free()
    tl = math.radians(tilt)
    half = P.WING_PAD_T / 2
    p_in = (a[0] + half * math.sin(tl), a[1] - half * math.cos(tl))        # pad mid-plane
    p_out = (b[0] + half * math.sin(tl), b[1] - half * math.cos(tl))
    nodes, elems = [(P.WING_ROOT_U, 0.0)], []

    def run(p1, tt, m):
        p0 = nodes[-1]
        for k in range(1, m + 1):
            nodes.append((p0[0] + (p1[0] - p0[0]) * k / m, p0[1] + (p1[1] - p0[1]) * k / m))
            elems.append((len(nodes) - 2, len(nodes) - 1, tt, w))
    run((P.WING_ROOT_U, P.WING_ARM_H), t, 6)
    run((P.WING_RAMP_U0, P.WING_ARM_H), t, n)
    run(p_in, t, n)
    i_in = len(nodes) - 1
    run(p_out, P.WING_PAD_T, 30)
    i_out = len(nodes) - 1
    return np.array(nodes), elems, dict(i_in=i_in, i_out=i_out, pad=list(range(i_in, i_out + 1)))


def solve(t=P.WING_T, w=P.POD_SHELL_W, E=E_PLA):
    nodes, elems, ids = wing_centre_line(t, w)
    pad = ids['pad']
    U, strain = frame(nodes, elems, [0], {p: (0.0, -1.0 / len(pad), 0.0) for p in pad}, E)
    pc = pad[len(pad) // 2]
    d = -U[3 * pc + 1]
    return dict(k=1 / d, strain=max(strain) / d, tilt=-math.degrees(U[3 * pc + 2]) / d, shift=U[3 * pc] / d,
                d_in=-U[3 * ids['i_in'] + 1] / d, d_out=-U[3 * ids['i_out'] + 1] / d,
                nodes=nodes, U=U / 1.0, d=d, ids=ids, elems=elems)


def report(log):
    r = solve()
    log(f"wing {P.WING_T} x {P.POD_SHELL_W} mm PLA (E {E_PLA:.0f} MPa), pressure spread over the pad:")
    log(f"  stiffness {r['k']:.2f} N/mm, strain {100 * r['strain']:.2f} % per mm, tilt {r['tilt']:.1f} deg per mm, "
        f"pad ends drop {r['d_in']:.2f} / {r['d_out']:.2f} per mm, pad shifts outward {r['shift']:.2f} mm per mm")
    for name, travel in (('flat (level with the middle pad)', P.WING_D0), ('at the stop', P.WING_STOP)):
        log(f"  {name}: travel {travel:.2f} mm, force {r['k'] * travel:.2f} N, strain {100 * r['strain'] * travel:.2f} %")
    for a, b, what in ((r['k'], P.WING_K, 'WING_K'), (r['strain'], P.WING_STRAIN, 'WING_STRAIN'), (r['tilt'], P.WING_TILT, 'WING_TILT'),
                       (r['d_in'], P.WING_IN, 'WING_IN'), (r['d_out'], P.WING_OUT, 'WING_OUT'), (r['shift'], P.WING_SHIFT, 'WING_SHIFT')):
        if abs(a - b) > 0.06 * abs(b):
            log(f"  NOTE params.{what} = {b} but the model gives {a:.4g}")
    log("other blade thicknesses (same shape):")
    for t in (0.45, 0.5, 0.6, 0.7, 0.84):
        q = solve(t)
        log(f"  t {t:.2f}: {q['k']:.2f} N/mm, {100 * q['strain'] * P.WING_D0:.2f} % flat, {100 * q['strain'] * P.WING_STOP:.2f} % at the stop, "
            f"{q['k'] * P.WING_D0:.2f} N per electrode when flat")
    log("softer or stiffer plastic (0.6 mm blade): " + ', '.join(
        f"E {e:.0f}: {solve(E=e)['k']:.2f} N/mm" for e in (2000.0, 2800.0, 3300.0, 3500.0)))
    # what the strap gives: radial force per pod = tension * pitch / wrist radius
    for T in (3.0, 5.0, 8.0):
        f_pod = T * P.PITCH / (157.0 / (2 * math.pi))
        d = min(f_pod / (2 * r['k']), P.WING_D0)
        rest = max(0.0, f_pod - 2 * r['k'] * P.WING_D0)
        log(f"  strap tension {T:.0f} N on a 157 mm wrist: {f_pod:.1f} N per pod -> wings travel {d:.2f} mm, middle pad carries {rest:.1f} N")
    return r


def plot(r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    nodes, U = r['nodes'], r['U']
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.fill_between([-15.1, 15.1], [-P.POD_FLOOR_T] * 2, [0, 0], color='#444a55')
    ax.fill([-P.POD_TRUNK_HX, P.POD_TRUNK_HX, P.POD_TRUNK_HX, P.POD_CAP_HX, P.POD_CAP_HX, -P.POD_CAP_HX, -P.POD_CAP_HX, -P.POD_TRUNK_HX],
            [0, 0, P.POD_HC - P.POD_CAP_T, P.POD_HC - P.POD_CAP_T, P.POD_HC, P.POD_HC, P.POD_HC - P.POD_CAP_T, P.POD_HC - P.POD_CAP_T], color='#444a55')
    for sgn in (1, -1):
        for travel, col, lab in ((0.0, '#1f5fbf', 'free'), (P.WING_D0, '#d9801a', f'flat ({P.WING_D0} mm)'), (P.WING_STOP, '#b02020', f'stop ({P.WING_STOP} mm)')):
            f = travel / r['d']
            x = sgn * (nodes[:, 0] + U[0::3] * f)
            y = nodes[:, 1] + U[1::3] * f
            ax.plot(x, y, color=col, lw=2.2, label=lab if sgn == 1 else None)
    ax.axhline(P.POD_HC, color='#999', lw=0.6, ls='--')
    ax.set_aspect('equal')
    ax.set_xlim(-16, 16)
    ax.set_ylim(-2, 4.6)
    ax.set_xlabel('along the arm, mm')
    ax.set_ylabel('toward the skin, mm')
    ax.set_title('Pod spring wings, centre lines: free, flat and at the stop (skin side up)', fontsize=10)
    ax.legend(loc='upper center', ncol=3, fontsize=8, frameon=False)
    fig.tight_layout()
    os.makedirs(os.path.join(HERE, 'renders'), exist_ok=True)
    fig.savefig(os.path.join(HERE, 'renders', 'pod_spring.png'), dpi=130)
    plt.close(fig)


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'logs'), exist_ok=True)
    f = open(os.path.join(HERE, 'logs', 'springs.log'), 'w')

    def log(*a):
        s = ' '.join(str(x) for x in a)
        print(s)
        f.write(s + '\n')
    r = report(log)
    if '--noplot' not in sys.argv:
        plot(r)
        log("plot: renders/pod_spring.png")
    f.close()
