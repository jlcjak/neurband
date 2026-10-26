"""Cell-centred finite-volume solver for the quasi-static volume conductor.

    div( sigma grad phi ) = -s        in tissue,   sigma grad phi . n = 0 at the skin/air (sigma = 0 outside)

sigma is a diagonal tensor per voxel (sx, sy, sz): fibres are aligned with a grid axis, so no
cross terms are needed.  Face conductances use the harmonic mean of the two voxels, so a face
with air on one side has zero conductance (natural Neumann boundary).

The discrete operator A (A phi = I, I = injected current per voxel in A) is symmetric positive
semidefinite; its null space is the constant over the (connected) tissue.  We solve it with
preconditioned conjugate gradients.  Preconditioner: a symmetric V-cycle of an aggregation
multigrid (2x2x2 piecewise-constant aggregation, exact Galerkin coarse operator, damped-Jacobi
smoothing) or plain Jacobi.  numpy only.
"""
from __future__ import annotations

import time
import numpy as np


def _hmean(a, b):
    s = a + b
    out = np.zeros_like(s)
    m = s > 0
    out[m] = 2.0 * a[m] * b[m] / s[m]
    return out


class FVOperator:
    """7-point FV operator defined by face conductances (S) on an (nx, ny, nz) cell grid."""

    def __init__(self, gx, gy, gz, shape):
        self.shape = shape
        self.gx, self.gy, self.gz = gx, gy, gz  # (nx-1,ny,nz), (nx,ny-1,nz), (nx,ny,nz-1)
        d = np.zeros(shape)
        d[:-1] += gx; d[1:] += gx
        d[:, :-1] += gy; d[:, 1:] += gy
        d[:, :, :-1] += gz; d[:, :, 1:] += gz
        self.diag = d
        self.active = d > 0
        self.inv_diag = np.where(self.active, 1.0 / np.where(self.active, d, 1.0), 0.0)

    @classmethod
    def from_conductivity(cls, sx, sy, sz, h):
        hx, hy, hz = h
        gx = _hmean(sx[:-1], sx[1:]) * (hy * hz / hx)
        gy = _hmean(sy[:, :-1], sy[:, 1:]) * (hx * hz / hy)
        gz = _hmean(sz[:, :, :-1], sz[:, :, 1:]) * (hx * hy / hz)
        return cls(gx, gy, gz, sx.shape)

    def matvec(self, x):
        y = self.diag * x
        gx, gy, gz = self.gx, self.gy, self.gz
        y[:-1] -= gx * x[1:]
        y[1:] -= gx * x[:-1]
        y[:, :-1] -= gy * x[:, 1:]
        y[:, 1:] -= gy * x[:, :-1]
        y[:, :, :-1] -= gz * x[:, :, 1:]
        y[:, :, 1:] -= gz * x[:, :, :-1]
        return y

    def coarsen(self):
        """Galerkin coarse operator for 2x2x2 piecewise-constant aggregation.
        Coarse conductance between aggregates = sum of fine conductances joining them."""
        nx, ny, nz = self.shape
        cx, cy, cz = (nx + 1) // 2, (ny + 1) // 2, (nz + 1) // 2

        def pad(a, shp):
            out = np.zeros(shp)
            out[: a.shape[0], : a.shape[1], : a.shape[2]] = a
            return out

        # x faces: only fine faces between cells 2i+1 and 2i+2 cross aggregate boundaries
        gx = pad(self.gx, (2 * cx - 1, 2 * cy, 2 * cz))[1::2]  # (cx-1, 2cy, 2cz)
        gx = gx.reshape(cx - 1, cy, 2, cz, 2).sum(axis=(2, 4))
        gy = pad(self.gy, (2 * cx, 2 * cy - 1, 2 * cz))[:, 1::2]
        gy = gy.reshape(cx, 2, cy - 1, cz, 2).sum(axis=(1, 4))
        gz = pad(self.gz, (2 * cx, 2 * cy, 2 * cz - 1))[:, :, 1::2]
        gz = gz.reshape(cx, 2, cy, 2, cz - 1).sum(axis=(1, 3))
        return FVOperator(gx, gy, gz, (cx, cy, cz))


def restrict(r, cshape):
    nx, ny, nz = r.shape
    cx, cy, cz = cshape
    p = np.zeros((2 * cx, 2 * cy, 2 * cz))
    p[:nx, :ny, :nz] = r
    return p.reshape(cx, 2, cy, 2, cz, 2).sum(axis=(1, 3, 5))


def prolong(e, fshape):
    f = np.repeat(np.repeat(np.repeat(e, 2, 0), 2, 1), 2, 2)
    return f[: fshape[0], : fshape[1], : fshape[2]]


class MGPreconditioner:
    """Symmetric V-cycle; aggregation coarse grids; damped Jacobi smoother; dense coarsest solve."""

    def __init__(self, op: FVOperator, nsmooth=2, omega=0.7, coarse_scale=1.6, min_cells=600):
        self.levels = [op]
        while np.prod(self.levels[-1].shape) > min_cells and min(self.levels[-1].shape) > 2:
            self.levels.append(self.levels[-1].coarsen())
        self.nsmooth, self.omega, self.cs = nsmooth, omega, coarse_scale
        c = self.levels[-1]
        n = int(np.prod(c.shape))
        A = np.zeros((n, n))
        eye = np.zeros(c.shape)
        for k in range(n):  # tiny: build dense coarsest matrix column by column
            eye.flat[k] = 1.0
            A[:, k] = c.matvec(eye).ravel()
            eye.flat[k] = 0.0
        act = c.active.ravel()
        self._cidx = np.flatnonzero(act)
        self._cpinv = np.linalg.pinv(A[np.ix_(self._cidx, self._cidx)], rcond=1e-10)

    def _vcycle(self, lev, r):
        op = self.levels[lev]
        if lev == len(self.levels) - 1:
            x = np.zeros(op.shape)
            x.flat[self._cidx] = self._cpinv @ r.ravel()[self._cidx]
            return x
        w, D = self.omega, op.inv_diag
        x = w * D * r
        for _ in range(self.nsmooth - 1):
            x += w * D * (r - op.matvec(x))
        res = r - op.matvec(x)
        cshape = self.levels[lev + 1].shape
        x += self.cs * prolong(self._vcycle(lev + 1, restrict(res, cshape)), op.shape)
        for _ in range(self.nsmooth):
            x += w * D * (r - op.matvec(x))
        return x

    def __call__(self, r):
        return self._vcycle(0, r)


def pcg(op: FVOperator, b, M=None, tol=1e-8, maxit=5000, x0=None, verbose=False):
    """PCG for the singular consistent Neumann problem. b is projected to zero mean on active cells."""
    act = op.active
    b = np.where(act, b, 0.0)
    b = b - act * (b[act].mean())
    if M is None:
        M = lambda r: op.inv_diag * r  # noqa: E731
    x = np.zeros_like(b) if x0 is None else x0.copy()
    r = b - op.matvec(x)
    z = M(r)
    p = z.copy()
    rz = np.vdot(r, z)
    bn = np.sqrt(np.vdot(b, b))
    t0 = time.time()
    for it in range(1, maxit + 1):
        Ap = op.matvec(p)
        alpha = rz / np.vdot(p, Ap)
        x += alpha * p
        r -= alpha * Ap
        rn = np.sqrt(np.vdot(r, r))
        if rn < tol * bn:
            break
        z = M(r)
        rz_new = np.vdot(r, z)
        p = z + (rz_new / rz) * p
        rz = rz_new
        if verbose and it % 50 == 0:
            print(f"  it {it} rel res {rn / bn:.2e}  {time.time() - t0:.1f}s", flush=True)
    x = np.where(act, x - x[act].mean(), 0.0)
    return x, it, rn / bn
