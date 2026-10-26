"""Solver validation.

1. Current dipole in a homogeneous half-space with an insulating surface (isotropic and muscle-like
   anisotropic sigma), solved in a finite Neumann box, compared with the analytic image solution
   (images of the box walls summed to 3rd order; anisotropic case via coordinate scaling).
2. Reciprocity in the full forearm model: forward solve of a dipole vs the lead-field integral.
Writes results to cache/validation.json and a figure.
"""
from __future__ import annotations

import json
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver import FVOperator, MGPreconditioner, pcg  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def analytic_box(P, charges, sig, box, K=3):
    """Potential of point currents in an anisotropic Neumann box via image lattice (same-sign images)."""
    sx, sy, sz = sig
    (x0, x1), (y0, y1), (z0, z1) = box
    L = np.array([x1 - x0, y1 - y0, z1 - z0])
    lo = np.array([x0, y0, z0])
    out = np.zeros(len(P))
    for q, r in charges:
        r = np.asarray(r, float)
        imgs = []
        for ax in range(3):
            base = [r[ax], 2 * lo[ax] - r[ax]]
            imgs.append(np.array([b + 2 * k * L[ax] for b in base for k in range(-K, K + 1)]))
        IX, IY, IZ = np.meshgrid(*imgs, indexing="ij")
        im = np.stack([IX.ravel(), IY.ravel(), IZ.ravel()], 1)
        for i in range(0, len(P), 512):
            d = P[i:i + 512, None, :] - im[None]
            R = np.sqrt(d[..., 0] ** 2 / sx + d[..., 1] ** 2 / sy + d[..., 2] ** 2 / sz)
            out[i:i + 512] += q / (4 * np.pi * np.sqrt(sx * sy * sz)) * (1.0 / R).sum(1)
    return out


def analytic_halfspace(P, charges, sig, ysurf):
    sx, sy, sz = sig
    out = np.zeros(len(P))
    for q, r in charges:
        for ry in (r[1], 2 * ysurf - r[1]):
            d = P - np.array([r[0], ry, r[2]])
            R = np.sqrt(d[:, 0] ** 2 / sx + d[:, 1] ** 2 / sy + d[:, 2] ** 2 / sz)
            out += q / (4 * np.pi * np.sqrt(sx * sy * sz)) / R
    return out


def halfspace_case(sig, h, depth=6.25, sep=3.0, box=((-50, 50), (-50, 0), (-60, 60))):
    hx, hy, hz = h
    x = np.arange(box[0][0] + hx / 2, box[0][1], hx)
    y = np.arange(box[1][0] + hy / 2, box[1][1], hy)
    z = np.arange(box[2][0] + hz / 2, box[2][1], hz)
    shp = (len(x), len(y), len(z))
    S = [np.full(shp, s) for s in sig]
    op = FVOperator.from_conductivity(*S, tuple(v * 1e-3 for v in h))
    M = MGPreconditioner(op)
    # dipole along z (fibre direction) centred at depth `depth`, monopoles placed on cell centres
    ix = np.argmin(abs(x - 0.0)); iy = np.argmin(abs(y + depth))
    iz1 = np.argmin(abs(z - sep / 2)); iz2 = np.argmin(abs(z + sep / 2))
    b = np.zeros(shp); b[ix, iy, iz1] = 1.0; b[ix, iy, iz2] = -1.0
    t = time.time()
    phi, it, rr = pcg(op, b, M=M, tol=1e-10, maxit=600)
    dt = time.time() - t
    # compare on the top cell layer within |x|<=30, |z|<=40 mm
    jx = np.flatnonzero(abs(x) <= 30); jz = np.flatnonzero(abs(z) <= 40)
    PX, PZ = np.meshgrid(x[jx], z[jz], indexing="ij")
    P = np.stack([PX.ravel(), np.full(PX.size, y[-1]), PZ.ravel()], 1) * 1e-3
    ch = [(1.0, np.array([x[ix], y[iy], z[iz1]]) * 1e-3), (-1.0, np.array([x[ix], y[iy], z[iz2]]) * 1e-3)]
    boxm = tuple((a * 1e-3, b_ * 1e-3) for a, b_ in box)
    an = analytic_box(P, ch, sig, boxm)
    hs = analytic_halfspace(P, ch, sig, 0.0)
    num = phi[np.ix_(jx, [len(y) - 1], jz)].ravel()

    def err(ref):
        c = (num - ref).mean()
        return float(np.sqrt(((num - ref - c) ** 2).mean() / ((ref - ref.mean()) ** 2).mean()))
    # bipolar 20 mm pair on the surface above the dipole (P at z=+10, N at z=-10) and max
    def at(arr, xx, zz):
        k = np.argmin((PX.ravel() - xx) ** 2 + (PZ.ravel() - zz) ** 2)
        return arr[k]
    bip_n = at(num, 0, 10) - at(num, 0, -10)
    bip_a = at(an, 0, 10) - at(an, 0, -10)
    return dict(sigma=list(sig), h=list(h), iters=it, rel_res=rr, seconds=dt,
                rel_rms_err_vs_box_images=err(an), rel_rms_err_vs_pure_halfspace=err(hs),
                bipolar_num=float(bip_n), bipolar_analytic=float(bip_a),
                bipolar_rel_err=float(abs(bip_n - bip_a) / abs(bip_a)),
                peak_num=float(np.abs(num - num.mean()).max()), peak_an=float(np.abs(an - an.mean()).max())), \
        (x[jx], z[jz], num.reshape(PX.shape), an.reshape(PX.shape))


def reciprocity_case():
    from geometry import build_model, Electrode, electrode_weights, pod_positions
    m = build_model()
    op = FVOperator.from_conductivity(m.sx, m.sy, m.sz, tuple(v * 1e-3 for v in m.h))
    M = MGPreconditioner(op)
    s0 = pod_positions(m.outline)[1]
    eP, eN = Electrode(s0, 50.0), Electrode(s0, 30.0)
    iP, wP, _ = electrode_weights(eP, m)
    iN, wN, _ = electrode_weights(eN, m)
    # dipole inside FDS muscle near z = 45
    k = 3
    cand = np.argwhere(m.comp3d[:, :, 85] == k)
    ix, iy = cand[len(cand) // 2]
    b = np.zeros(m.shape); b[ix, iy, 86] = 1e-6; b[ix, iy, 84] = -1e-6
    phi, _, _ = pcg(op, b, M=M, tol=1e-10, maxit=600)
    v_fwd = (phi.ravel()[iP] * wP).sum() - (phi.ravel()[iN] * wN).sum()
    bP = np.zeros(m.shape); bP.ravel()[iP] = wP
    bN = np.zeros(m.shape); bN.ravel()[iN] = wN
    psiP, _, _ = pcg(op, bP, M=M, tol=1e-10, maxit=600)
    psiN, _, _ = pcg(op, bN, M=M, tol=1e-10, maxit=600)
    lf = psiP - psiN
    v_rec = 1e-6 * (lf[ix, iy, 86] - lf[ix, iy, 84])
    return dict(v_forward=float(v_fwd), v_reciprocal=float(v_rec), rel_diff=float(abs(v_fwd - v_rec) / abs(v_fwd)))


if __name__ == "__main__":
    res = {}
    figdata = {}
    for name, sig in (("isotropic_0.3", (0.3, 0.3, 0.3)), ("anisotropic_muscle", (0.1, 0.1, 0.5))):
        for h in ((1.0, 1.0, 1.0), (0.5, 0.5, 1.0)):
            r, fd = halfspace_case(sig, h)
            key = f"{name}_h{h[0]}"
            res[key] = r
            figdata[key] = fd
            print(key, json.dumps(r, indent=None), flush=True)
    res["reciprocity_forearm"] = reciprocity_case()
    print("reciprocity", res["reciprocity_forearm"], flush=True)
    os.makedirs(os.path.join(HERE, "cache"), exist_ok=True)
    with open(os.path.join(HERE, "cache", "validation.json"), "w") as f:
        json.dump(res, f, indent=1)
    np.savez(os.path.join(HERE, "cache", "validation_maps.npz"),
             **{k + "_" + n: v for k, fd in figdata.items() for n, v in zip(("x", "z", "num", "an"), fd)})
