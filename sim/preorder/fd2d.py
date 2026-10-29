"""2D finite-difference electrostatic solver for PCB / flex cross-sections (per-unit-length capacitance).

Rectangular conductors on a uniform grid; cell-wise permittivity; Dirichlet on conductors, Neumann on
the box sides (box made wide enough), optional ground plane rows. Returns the Maxwell capacitance
row for the excited conductor, in F/m (2D). Used by coupling.py to tabulate c_m(gap) per layer.
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

EPS0 = 8.854e-12


class XSection:
    def __init__(self, width, height, h):
        self.h = h
        self.nx, self.ny = int(round(width / h)), int(round(height / h))
        self.eps = np.ones((self.ny, self.nx))           # cell permittivity (cell between nodes)
        self.cond = -np.ones((self.ny + 1, self.nx + 1), dtype=int)  # node conductor id, -1 = free
        self.x0 = -width / 2

    def _ix(self, x):
        return int(round((x - self.x0) / self.h))

    def _iy(self, y):
        return int(round(y / self.h))

    def dielectric(self, y0, y1, er, x0=None, x1=None):
        i0 = 0 if x0 is None else self._ix(x0)
        i1 = self.nx if x1 is None else self._ix(x1)
        self.eps[self._iy(y0):self._iy(y1), i0:i1] = er

    def conductor(self, cid, x0, x1, y0, y1):
        self.cond[self._iy(y0):self._iy(y1) + 1, self._ix(x0):self._ix(x1) + 1] = cid

    def solve(self, excite, ncond):
        """Potential 1 V on conductor `excite`, 0 on the rest; return charges (C/m) on all conductors."""
        ny, nx = self.ny + 1, self.nx + 1
        N = ny * nx
        idx = np.arange(N).reshape(ny, nx)
        e = self.eps
        # edge permittivities: horizontal edge between (j,i) and (j,i+1) averages cells above/below
        ep = np.pad(e, 1, mode="edge")  # (ny+2-1?) shape (ny+2, nx+2) of cells
        # cells indexed [cy, cx], cy in 0..ny-1 (=self.ny), node (j,i) touches cells (j-1..j, i-1..i)
        eh = 0.5 * (ep[0:ny, 1:nx] + ep[1:ny + 1, 1:nx])   # edge (j,i)-(j,i+1): cells (j-1,i),(j,i)
        ev = 0.5 * (ep[1:ny, 0:nx] + ep[1:ny, 1:nx + 1])   # edge (j,i)-(j+1,i): cells (j,i-1),(j,i)
        rows, cols, vals = [], [], []
        diag = np.zeros(N)
        a = idx[:, :-1].ravel(); b = idx[:, 1:].ravel(); w = eh.ravel()
        rows += [a, b]; cols += [b, a]; vals += [-w, -w]
        np.add.at(diag, a, w); np.add.at(diag, b, w)
        a = idx[:-1, :].ravel(); b = idx[1:, :].ravel(); w = ev.ravel()
        rows += [a, b]; cols += [b, a]; vals += [-w, -w]
        np.add.at(diag, a, w); np.add.at(diag, b, w)
        A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N))
        A = A + sp.diags(diag)
        c = self.cond.ravel()
        fixed = c >= 0
        V = np.zeros(N)
        V[c == excite] = 1.0
        free = ~fixed
        Aff = A[free][:, free]
        rhs = -A[free][:, fixed] @ V[fixed]
        V[free] = spla.spsolve(Aff.tocsc(), rhs)
        Q = A @ V  # residual = charge/eps0 at fixed nodes (2D, per metre since grid is isotropic)
        return np.array([EPS0 * Q[c == k].sum() for k in range(ncond)])
