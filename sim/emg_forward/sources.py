"""Motor-unit sources and MUAPs via reciprocity.

Each muscle fibre is a line carrying the impressed (intracellular axial) current
    I_a(u, t) = -sigma_i * pi * a^2 * dVm/du ,     Vm(u, t) = V_R(v t - |u - u_e|)
where V_R is Rosenfalck's (1969) intracellular action potential  V_R(s) = 96 s^3 e^-s - 90 mV
(s in mm, s<0 = resting).  The AP is born at the end-plate u_e, travels both ways at v and is
extinguished at the fibre ends (I_a = 0 outside [u_dist, u_prox]: sealed ends).  The bipolar
voltage is  V(t) = sum_k I_a(u_k+1/2, t) [psi(u_k+1) - psi(u_k)]  with psi the reciprocal lead
field for 1 A (exactly the discrete adjoint of injecting the membrane currents into the grid).
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from geometry import MUSCLES, muscle_fraction, _ell_rho, DILATE

SIG_I = 1.01          # S/m, intracellular conductivity
FIBRE_R = 25e-6       # m (50 um diameter)
CV = 4.0              # m/s == mm/ms
FS = 4000.0           # Hz
T_MUAP = 0.032        # s
DU = 0.25             # mm sampling along fibres
FIBRE_DENSITY = 300.0     # fibres / mm^2 of muscle (200-400 reported)
MU_FIBRE_DENSITY = 20.0   # fibres / mm^2 inside one MU territory (Fuglevand 1993)
MEAN_INNERV = 340.0       # fibres per MU on average (FDI: 41k fibres / 119 MUs, Feinstein 1955)
INNERV_RANGE = 50.0       # largest / smallest MU
N_SAMPLE_FIBRES = 24      # fibres simulated per MU (scaled to the true count)


def rosenfalck_dvds(s):
    """dVm/ds in mV/mm (= V/m); s in mm behind the front."""
    s = np.maximum(s, 0.0)
    return 96.0 * (3 * s ** 2 - s ** 3) * np.exp(-s)


@dataclass
class MotorUnit:
    muscle: int
    n_fibres: int
    centre: tuple
    radius: float
    # per sampled fibre
    fx: np.ndarray        # transverse coords (x,y) for z-fibres; (v, z) for PQ
    fy: np.ndarray
    u_dist: np.ndarray    # fibre ends along the fibre axis (mm)
    u_prox: np.ndarray
    u_e: np.ndarray       # end-plate position
    threshold: float = 0.0   # recruitment threshold (% MVC)


def _pq_frame(m):
    th = np.radians(m.angle)
    eu = np.array([np.cos(th), np.sin(th)])
    ev = np.array([-np.sin(th), np.cos(th)])
    return eu, ev


def build_pools(model, rng, muscles=MUSCLES, thr_max=60.0, thr_range=60.0):
    """Motor-unit pools for every compartment present in the cross-section."""
    pools = {}
    X, Y = np.meshgrid(model.x, model.y, indexing="ij")
    hx, hy = model.h[0], model.h[1]
    for k, m in enumerate(muscles):
        in2d = model.comp2d == k
        if not in2d.any():
            continue
        q = model.rho2d
        capable = in2d & (q >= 1 - m.f_max)
        area = capable.sum() * hx * hy
        if m.fibre_axis == "u":
            # PQ: fibres transverse; territory lives in the (v, z) plane; muscle area ~ thickness x length
            eu, ev = _pq_frame(m)
            vv = (X - m.centre[0]) * ev[0] + (Y - m.centre[1]) * ev[1]
            vlo, vhi = vv[in2d].min(), vv[in2d].max()
            area = (vhi - vlo) * (m.z_range[1] - m.z_range[0]) * 0.75
        n_tot = FIBRE_DENSITY * area
        n_mu = max(int(round(n_tot / MEAN_INNERV)), 4)
        sizes = np.exp(np.log(INNERV_RANGE) * np.arange(n_mu) / (n_mu - 1))
        sizes = np.round(sizes / sizes.sum() * n_tot).astype(int).clip(5)
        thr = thr_max * np.exp(np.log(thr_range) * np.arange(n_mu) / (n_mu - 1)) / thr_range
        mus = []
        cx, cy = X[capable], Y[capable]
        for i in range(n_mu):
            r = np.sqrt(sizes[i] / (MU_FIBRE_DENSITY * np.pi))
            if m.fibre_axis == "z":
                j = rng.integers(len(cx))
                c = (cx[j], cy[j])
                fx, fy = [], []
                tries = 0
                while len(fx) < N_SAMPLE_FIBRES and tries < 50:
                    tries += 1
                    rr = r * np.sqrt(rng.random(64)); ph = 2 * np.pi * rng.random(64)
                    px, py = c[0] + rr * np.cos(ph), c[1] + rr * np.sin(ph)
                    ix = np.clip(np.round((px - model.x[0]) / hx).astype(int), 0, len(model.x) - 1)
                    iy = np.clip(np.round((py - model.y[0]) / hy).astype(int), 0, len(model.y) - 1)
                    ok = capable[ix, iy]
                    fx += list(px[ok]); fy += list(py[ok])
                fx, fy = np.array(fx[:N_SAMPLE_FIBRES]), np.array(fy[:N_SAMPLE_FIBRES])
                ix = np.clip(np.round((fx - model.x[0]) / hx).astype(int), 0, len(model.x) - 1)
                iy = np.clip(np.round((fy - model.y[0]) / hy).astype(int), 0, len(model.y) - 1)
                qf = q[ix, iy]
                # distal end: where this fibre's position stops being tendon core
                u_d = m.z_mtj + m.ramp * (1 - qf) / m.f_max + rng.normal(0, 1.5, len(fx))
                L = m.fibre_len * rng.uniform(0.85, 1.15, len(fx))
                ue_mu = np.mean(u_d + L / 2) + rng.normal(0, 4.0)
                u_e = ue_mu + rng.normal(0, 1.0, len(fx))
                u_e = np.clip(u_e, u_d + 5, None)
                u_p = np.maximum(u_e + (u_e - u_d) * rng.uniform(0.8, 1.2, len(fx)), u_d + L)
                zlo, zhi = model.z[0] + 0.5, model.z[-1] - 0.5
                u_d, u_p, u_e = np.clip(u_d, zlo, zhi), np.clip(u_p, zlo, zhi), np.clip(u_e, zlo, zhi)
            else:
                eu, ev = _pq_frame(m)
                vv = (X - m.centre[0]) * ev[0] + (Y - m.centre[1]) * ev[1]
                vlo, vhi = vv[in2d].min(), vv[in2d].max()
                c = (rng.uniform(vlo, vhi), rng.uniform(m.z_range[0] + 2, m.z_range[1] - 2))
                rr = r * np.sqrt(rng.random(N_SAMPLE_FIBRES)); ph = 2 * np.pi * rng.random(N_SAMPLE_FIBRES)
                fx = np.clip(c[0] + rr * np.cos(ph), vlo + 0.3, vhi - 0.3)
                fy = np.clip(c[1] + rr * np.sin(ph), m.z_range[0] + 0.5, m.z_range[1] - 0.5)
                # fibre extent along u inside the PQ compartment at this v
                u_d = np.empty(len(fx)); u_p = np.empty(len(fx))
                us = np.arange(-30, 30, 0.25)
                for f in range(len(fx)):
                    px = m.centre[0] + us * eu[0] + fx[f] * ev[0]
                    py = m.centre[1] + us * eu[1] + fx[f] * ev[1]
                    ix = np.clip(np.round((px - model.x[0]) / hx).astype(int), 0, len(model.x) - 1)
                    iy = np.clip(np.round((py - model.y[0]) / hy).astype(int), 0, len(model.y) - 1)
                    inside = model.comp2d[ix, iy] == k
                    if inside.any():
                        u_d[f], u_p[f] = us[inside].min(), us[inside].max()
                    else:
                        u_d[f], u_p[f] = -5, 5
                u_e = 0.5 * (u_d + u_p) + rng.normal(0, 2.0) + rng.normal(0, 0.7, len(fx))
            mus.append(MotorUnit(k, int(sizes[i]), c, r, fx, fy, u_d, u_p, u_e, float(thr[i])))
        pools[m.name] = mus
    return pools


def fibre_currents(mu: MotorUnit, t):
    """Axial current I_a (A) per fibre on a common u-grid: returns u_mid (n_q-1,), I (n_f, n_q-1, n_t)."""
    u = np.arange(mu.u_dist.min() - DU, mu.u_prox.max() + 2 * DU, DU)
    um = 0.5 * (u[1:] + u[:-1])
    s = CV * t[None, None, :] * 1e3 - np.abs(um[None, :, None] - mu.u_e[:, None, None])  # mm (t in s)
    dv = rosenfalck_dvds(s)
    sign = np.sign(um[None, :] - mu.u_e[:, None])
    inside = (um[None, :] >= mu.u_dist[:, None]) & (um[None, :] <= mu.u_prox[:, None])
    I = SIG_I * np.pi * FIBRE_R ** 2 * (sign * inside)[:, :, None] * dv  # A
    return u, I


def muap(mu: MotorUnit, lfs, t=None):
    """Monopolar MUAPs at all electrodes of LeadFieldSet lfs: (n_el, n_t) in volts."""
    from geometry import MUSCLES as MM
    m = MM[mu.muscle]
    if t is None:
        t = np.arange(int(T_MUAP * FS)) / FS
    u, I = fibre_currents(mu, t)
    nf = len(mu.fx)
    if m.fibre_axis == "z":
        zq = np.broadcast_to(u, (nf, len(u)))
        psi = lfs.sample_lines(mu.fx, mu.fy, zq)          # (n_f, n_el, n_q)
    else:
        eu, ev = _pq_frame(m)
        P = np.empty((nf, len(u), 3))
        P[..., 0] = m.centre[0] + u[None, :] * eu[0] + mu.fx[:, None] * ev[0]
        P[..., 1] = m.centre[1] + u[None, :] * eu[1] + mu.fx[:, None] * ev[1]
        P[..., 2] = mu.fy[:, None]
        psi = lfs.sample_points(P.reshape(-1, 3)).reshape(nf, len(u), -1).transpose(0, 2, 1)
    dpsi = np.diff(psi, axis=2)                            # (n_f, n_el, n_q-1)  [V/A]
    A = dpsi.transpose(1, 0, 2).reshape(dpsi.shape[1], -1)  # (n_el, n_f*n_k)
    B = I.reshape(-1, I.shape[2])                          # (n_f*n_k, n_t)
    return (A @ B) * (mu.n_fibres / nf)


def membrane_sources(mu: MotorUnit, t_snap, model):
    """Point currents (positions mm, currents A) of the MU at one instant, for a forward solve."""
    from geometry import MUSCLES as MM
    m = MM[mu.muscle]
    u, I = fibre_currents(mu, np.array([t_snap]))
    I = I[:, :, 0] * (mu.n_fibres / len(mu.fx))
    # membrane current at node k = I_{k-1/2} - I_{k+1/2}  (current leaving the fibre)
    Ipad = np.pad(I, ((0, 0), (1, 1)))
    im = Ipad[:, :-1] - Ipad[:, 1:]                        # (n_f, n_q)
    nf = len(mu.fx)
    if m.fibre_axis == "z":
        P = np.stack([np.repeat(mu.fx, len(u)), np.repeat(mu.fy, len(u)), np.tile(u, nf)], 1)
    else:
        eu, ev = _pq_frame(m)
        P = np.stack([(m.centre[0] + u[None, :] * eu[0] + mu.fx[:, None] * ev[0]).ravel(),
                      (m.centre[1] + u[None, :] * eu[1] + mu.fx[:, None] * ev[1]).ravel(),
                      np.repeat(mu.fy, len(u))], 1)
    return P, im.ravel()


def deposit(model, P, cur):
    """Trilinear deposition of point currents onto the cell grid (adjoint of trilinear sampling)."""
    h = np.array(model.h)
    f = (P - np.array([model.x[0], model.y[0], model.z[0]])) / h
    i = np.clip(np.floor(f).astype(int), 0, np.array(model.shape) - 2)
    t = f - i
    b = np.zeros(model.shape)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = ((t[:, 0] if dx else 1 - t[:, 0]) * (t[:, 1] if dy else 1 - t[:, 1])
                     * (t[:, 2] if dz else 1 - t[:, 2]))
                np.add.at(b, (i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz), cur * w)
    return b
