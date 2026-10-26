"""Reciprocal lead fields.

For every electrode e we solve  A psi_e = w_e - mean  (1 A spread uniformly over the pad
footprint, sink spread uniformly over the tissue).  The sink term cancels in any difference, so
the bipolar lead field of a P/N pair is exactly psi_P - psi_N (= the field produced by injecting
1 A at P and extracting it at N).  By reciprocity a source with impressed current density J^i
produces the pad-averaged voltage  V_P - V_N = integral J^i . grad(psi_P - psi_N) dV  (per 1 A).
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # one BLAS thread per worker (vdot oversubscription otherwise)
import time
import multiprocessing as mp
import numpy as np

from geometry import build_model, Electrode, electrode_weights, pod_positions
from solver import FVOperator, MGPreconditioner, pcg

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")

_G = {}


def model_tag(h, variant):
    return f"h{h[0]:g}x{h[1]:g}x{h[2]:g}" + (f"_{variant}" if variant else "")


def _init(h, variant_kwargs):
    m = build_model(h=h, **variant_kwargs)
    op = FVOperator.from_conductivity(m.sx, m.sy, m.sz, tuple(v * 1e-3 for v in m.h))
    _G.update(model=m, op=op, M=MGPreconditioner(op))


def _solve_one(args):
    el, path = args
    if os.path.exists(path):
        return path, 0, 0.0, 0.0
    m, op, M = _G["model"], _G["op"], _G["M"]
    idx, w, area = electrode_weights(el, m)
    b = np.zeros(m.shape)
    b.ravel()[idx] = w
    t = time.time()
    x, it, rr = pcg(op, b, M=M, tol=1e-8, maxit=400)
    np.save(path + ".tmp.npy", x.astype(np.float32))
    os.replace(path + ".tmp.npy", path)
    return path, it, rr, time.time() - t


def compute(electrodes, h=(0.5, 0.5, 1.0), variant="", variant_kwargs=None, nproc=6):
    """Compute (or load from cache) lead fields; returns dict key -> path."""
    variant_kwargs = variant_kwargs or {}
    d = os.path.join(CACHE, model_tag(h, variant))
    os.makedirs(d, exist_ok=True)
    jobs, out = [], {}
    for el in electrodes:
        p = os.path.join(d, el.key() + ".npy")
        out[el.key()] = p
        if not os.path.exists(p):
            jobs.append((el, p))
    jobs = list({j[1]: j for j in jobs}.values())
    if jobs:
        print(f"[leadfield] {len(jobs)} solves on {model_tag(h, variant)} with {nproc} workers", flush=True)
        t0 = time.time()
        ctx = mp.get_context("fork")
        with ctx.Pool(nproc, initializer=_init, initargs=(h, variant_kwargs)) as pool:
            for k, (p, it, rr, dt) in enumerate(pool.imap_unordered(_solve_one, jobs)):
                if k % 10 == 0 or rr > 1e-6:
                    print(f"  {k + 1}/{len(jobs)} it={it} res={rr:.1e} {dt:.1f}s  ({time.time() - t0:.0f}s)", flush=True)
    return out


class LeadFieldSet:
    """Loads monopolar lead fields (V per A) stacked as (nx, ny, n_el, nz) for fast fibre sampling."""

    def __init__(self, model, paths: dict, keys):
        self.model = model
        self.keys = list(keys)
        self.index = {k: i for i, k in enumerate(self.keys)}
        nx, ny, nz = model.shape
        self.L = np.empty((nx, ny, len(self.keys), nz), np.float32)
        for i, k in enumerate(self.keys):
            self.L[:, :, i, :] = np.load(paths[k])

    def sample_lines(self, xs, ys, zq):
        """psi at (xs[f], ys[f], zq[f, :]) for all electrodes -> (n_f, n_el, n_q).

        Bilinear in x, y; linear in z.  zq is per-fibre query positions (mm)."""
        m = self.model
        hx, hy, hz = m.h
        fx = (np.asarray(xs) - m.x[0]) / hx
        fy = (np.asarray(ys) - m.y[0]) / hy
        ix = np.clip(np.floor(fx).astype(int), 0, len(m.x) - 2)
        iy = np.clip(np.floor(fy).astype(int), 0, len(m.y) - 2)
        tx, ty = fx - ix, fy - iy
        col = (self.L[ix, iy] * ((1 - tx) * (1 - ty))[:, None, None]
               + self.L[ix + 1, iy] * (tx * (1 - ty))[:, None, None]
               + self.L[ix, iy + 1] * ((1 - tx) * ty)[:, None, None]
               + self.L[ix + 1, iy + 1] * (tx * ty)[:, None, None])  # (n_f, n_el, nz)
        fz = (zq - m.z[0]) / hz
        iz = np.clip(np.floor(fz).astype(int), 0, len(m.z) - 2)
        tz = fz - iz
        f_idx = np.arange(len(fx))[:, None]
        lo = col[f_idx, :, iz]          # (n_f, n_q, n_el)
        hi = col[f_idx, :, iz + 1]
        out = lo * (1 - tz)[..., None] + hi * tz[..., None]
        return np.transpose(out, (0, 2, 1))

    def sample_points(self, P):
        """psi at arbitrary 3D points P (n, 3) mm -> (n, n_el), trilinear."""
        m = self.model
        h = np.array(m.h)
        f = (P - np.array([m.x[0], m.y[0], m.z[0]])) / h
        i = np.clip(np.floor(f).astype(int), 0, np.array(m.shape) - 2)
        t = f - i
        out = 0.0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    w = ((t[:, 0] if dx else 1 - t[:, 0]) * (t[:, 1] if dy else 1 - t[:, 1])
                         * (t[:, 2] if dz else 1 - t[:, 2]))
                    out = out + self.L[i[:, 0] + dx, i[:, 1] + dy, :, i[:, 2] + dz] * w[:, None]
        return out


# ---------------------------------------------------------------- the electrode sets used by the study
IED_SET = (15.0, 20.0, 25.0)


def study_electrodes(outline, z_band=40.0):
    """All monopolar electrodes needed: rings for rotation / 16-channel / IED / pad-size studies."""
    s_mid = pod_positions(outline, 1, 0.0)[0]
    base = np.mod(s_mid + (np.arange(8) - 3.5) * 18.0, outline.circ)
    els = []
    offs = sorted(set(np.round(np.r_[np.arange(-81, 82, 9), (np.arange(16) - 7.5) * 9], 2)))
    for o in offs:
        for zz in (z_band - 10, z_band + 10):
            els.append(Electrode(round(float(np.mod(s_mid + o, outline.circ)), 2), zz, "disc6.5"))
    for s in base:
        for ied in IED_SET:
            for zz in (z_band - ied / 2, z_band + ied / 2):
                els.append(Electrode(round(float(s), 2), zz, "disc6.5"))
        for kind in ("disc2", "pins2x2"):
            for zz in (z_band - 10, z_band + 10):
                els.append(Electrode(round(float(s), 2), zz, kind))
    uniq = {e.key(): e for e in els}
    return list(uniq.values()), s_mid


if __name__ == "__main__":
    import sys
    h = tuple(float(v) for v in sys.argv[1].split(",")) if len(sys.argv) > 1 else (0.5, 0.5, 1.0)
    m = build_model(h=h)
    els, _ = study_electrodes(m.outline)
    print(len(els), "electrodes")
    compute(els, h=h, nproc=int(os.environ.get("NPROC", 6)))
