"""Distal-forearm anatomy, voxel model and electrode geometry.

Coordinates (mm), right forearm in anatomical position (palm up):
    x : lateral / radial (+)  <->  medial / ulnar (-)
    y : volar / palmar (+)     <->  dorsal (-)
    z : proximal distance from the distal wrist crease (z = 0); band centre at z = 40 mm.

The cross-section is prismatic (no taper).  What changes along z is which part of each
compartment is muscle (active, anisotropic, carries fibres) and which is tendon (passive).
All numbers marked ASSUMED are engineering choices; sources are listed in
docs/science/emg_forward_model.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

# ---------------------------------------------------------------- conductivities (S/m)
SIG = dict(
    muscle_L=0.5,     # along fibres
    muscle_T=0.1,     # across fibres
    fat=0.04,
    skin=0.2,         # dermis/epidermis below the stratum corneum (SC handled at the electrode interface)
    tendon=0.37,      # IT'IS LF tendon/ligament 0.368
    connective=0.25,  # septa, sheaths, neurovascular bundles, interosseous membrane
    bone_cortical=0.02,
    bone_cancellous=0.08,
)

# ---------------------------------------------------------------- outer shape
CIRC = 155.0          # mm, circumference at the band (owner: small male wrist)
ASPECT = 1.35         # width : depth
T_SKIN = 1.0          # mm
T_FAT = 3.0           # mm (2-5 mm range; 3 mm baseline for a lean adult)
DILATE = 1.3          # compartment growth factor to fill sub-fascial space
Z_BAND = 40.0         # band centre above the wrist crease
DOMAIN = dict(x=(-32.0, 32.0), y=(-24.0, 24.0), z=(-20.0, 120.0))


def ellipse_axes(circ=CIRC, aspect=ASPECT):
    """Semi-axes (a along x, b along y) of an ellipse with given perimeter (Ramanujan II)."""
    def perim(b):
        a = aspect * b
        h = ((a - b) / (a + b)) ** 2
        return np.pi * (a + b) * (1 + 3 * h / (10 + np.sqrt(4 - 3 * h)))
    lo, hi = 5.0, 60.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if perim(mid) < circ else (lo, mid)
    b = 0.5 * (lo + hi)
    return aspect * b, b


@dataclass
class Muscle:
    name: str
    group: str            # 'flexor' | 'extensor' | 'pronator'
    centre: tuple         # (x, y) mm
    axes: tuple           # (semi-axis u, semi-axis v) mm
    angle: float          # deg, rotation of the u axis from +x
    z_mtj: float          # distal end of the most distal muscle fibres (mm above crease)
    ramp: float           # mm over which muscle fraction rises from 0 to f_max going proximally
    f_max: float          # max muscle fraction of the compartment area (rest = internal tendon)
    fibre_len: float      # mm, optimal fibre length (Holzbaur 2005 Table 1 from Lieber 1990/92, Jacobson 1992)
    z_range: tuple = (-1e9, 1e9)   # z extent of the compartment itself (pronator quadratus only)
    fibre_axis: str = "z"          # 'z' longitudinal, 'u' along the compartment's u axis (PQ, transverse)
    label: str = ""
    role: str = ""


# Compartments at ~4 cm above the wrist crease.  Ellipses are a schematic of published axial
# sections / MRI at the pronator-quadratus level (see the doc for sources).  Voxels claimed by
# several ellipses go to the one with the smallest normalised radius (a Voronoi-like split).
MUSCLES = [
    # ---- volar, deep
    Muscle("PQ", "pronator", (-2.5, 2.6), (15.5, 2.6), 11.0, z_mtj=-1e9, ramp=1, f_max=1.0, fibre_len=28,
           z_range=(8.0, 56.0), fibre_axis="u", label="pronator quadratus", role="forearm pronation"),
    Muscle("FPL", "flexor", (7.5, 8.6), (6.0, 3.0), 12.0, z_mtj=15, ramp=35, f_max=0.9, fibre_len=55,
           label="flexor pollicis longus", role="thumb IP flexion"),
    Muscle("FDP", "flexor", (-8.5, 7.2), (8.5, 3.8), 18.0, z_mtj=15, ramp=40, f_max=0.9, fibre_len=78,
           label="flexor digitorum profundus", role="finger DIP flexion"),
    # ---- volar, superficial / intermediate
    Muscle("FDS", "flexor", (-1.5, 12.3), (10.5, 3.3), 0.0, z_mtj=20, ramp=45, f_max=0.9, fibre_len=70,
           label="flexor digitorum superficialis", role="finger PIP flexion"),
    Muscle("FCU", "flexor", (-17.5, 6.0), (4.3, 5.8), -35.0, z_mtj=10, ramp=40, f_max=0.85, fibre_len=50,
           label="flexor carpi ulnaris", role="wrist flexion/ulnar dev."),
    Muscle("FCR", "flexor", (11.5, 12.6), (2.9, 2.4), 0.0, z_mtj=105, ramp=30, f_max=0.9, fibre_len=63,
           label="flexor carpi radialis (tendon)", role="wrist flexion/radial dev."),
    Muscle("PL", "flexor", (2.5, 15.4), (2.6, 1.2), 0.0, z_mtj=110, ramp=30, f_max=0.9, fibre_len=64,
           label="palmaris longus (tendon)", role="wrist flexion (absent in ~15%)"),
    # ---- dorsal / radial
    Muscle("APL_EPB", "extensor", (19.5, -5.5), (3.4, 5.2), 35.0, z_mtj=25, ramp=30, f_max=0.9, fibre_len=70,
           label="abductor pollicis longus + EPB", role="thumb abduction/extension"),
    Muscle("ECR", "extensor", (13.0, -11.8), (4.6, 2.2), -28.0, z_mtj=95, ramp=30, f_max=0.9, fibre_len=70,
           label="ECRL + ECRB (tendons)", role="wrist extension/radial dev."),
    Muscle("EPL", "extensor", (4.8, -12.4), (3.4, 2.2), -10.0, z_mtj=30, ramp=35, f_max=0.9, fibre_len=54,
           label="extensor pollicis longus", role="thumb extension"),
    Muscle("EDC", "extensor", (-2.0, -14.6), (7.0, 2.1), 0.0, z_mtj=40, ramp=40, f_max=0.9, fibre_len=68,
           label="extensor digitorum (communis)", role="finger extension"),
    Muscle("EIP", "extensor", (-4.5, -10.6), (4.0, 2.0), 15.0, z_mtj=5, ramp=30, f_max=0.9, fibre_len=59,
           label="extensor indicis", role="index extension"),
    Muscle("EDM", "extensor", (-10.2, -13.2), (2.6, 2.2), 20.0, z_mtj=30, ramp=30, f_max=0.9, fibre_len=68,
           label="extensor digiti minimi", role="little-finger extension"),
    Muscle("ECU", "extensor", (-13.8, -12.8), (3.4, 2.1), 35.0, z_mtj=20, ramp=40, f_max=0.9, fibre_len=62,
           label="extensor carpi ulnaris", role="wrist extension/ulnar dev."),
]

# Bones (ellipses): radius (distal metaphysis) and ulna, ~4 cm above the crease.
BONES = dict(
    radius=dict(centre=(8.5, -3.2), axes=(11.5, 6.4), angle=-8.0, cortex=1.5),
    ulna=dict(centre=(-15.3, -5.4), axes=(5.4, 5.4), angle=0.0, cortex=1.5),
)


def _ell_rho(X, Y, centre, axes, angle):
    c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    dx, dy = X - centre[0], Y - centre[1]
    u = c * dx + s * dy
    v = -s * dx + c * dy
    return np.sqrt((u / axes[0]) ** 2 + (v / axes[1]) ** 2)


def muscle_fraction(m: Muscle, z):
    z = np.asarray(z, float)
    return np.clip((z - m.z_mtj) / m.ramp, 0.0, 1.0) * m.f_max


class Outline:
    """Outer skin ellipse, arc-length parametrisation and distance-to-skin."""

    def __init__(self, circ=CIRC, aspect=ASPECT):
        self.a, self.b = ellipse_axes(circ, aspect)
        t = np.linspace(0, 2 * np.pi, 20001)
        # start at the volar midline (0, +b) and run towards the radial side (+x)
        tt = np.pi / 2 - t
        self.bx, self.by = self.a * np.cos(tt), self.b * np.sin(tt)
        seg = np.hypot(np.diff(self.bx), np.diff(self.by))
        self.s = np.concatenate([[0], np.cumsum(seg)])
        self.circ = self.s[-1]
        nx_, ny_ = self.bx / self.a ** 2, self.by / self.b ** 2
        nn = np.hypot(nx_, ny_)
        self.nx, self.ny = nx_ / nn, ny_ / nn

    def point(self, s):
        s = np.mod(s, self.circ)
        return (np.interp(s, self.s, self.bx), np.interp(s, self.s, self.by),
                np.interp(s, self.s, self.nx), np.interp(s, self.s, self.ny))

    def depth(self, X, Y):
        """Unsigned distance (mm) from points to the skin ellipse, sign + inside."""
        pts = np.stack([self.bx[::4], self.by[::4]], 1)
        P = np.stack([X.ravel(), Y.ravel()], 1)
        d = np.empty(len(P))
        for i in range(0, len(P), 4096):
            q = P[i:i + 4096]
            d[i:i + 4096] = np.sqrt(((q[:, None, :] - pts[None]) ** 2).sum(-1)).min(1)
        inside = (X / self.a) ** 2 + (Y / self.b) ** 2 < 1
        return np.where(inside.ravel(), d, -d).reshape(X.shape)

    def arc_of(self, x, y):
        """Arc length of the boundary point closest to (x, y)."""
        i = np.argmin((self.bx - x) ** 2 + (self.by - y) ** 2)
        return self.s[i]


# Tissue labels
AIR, SKIN, FAT, CONN, TENDON, MUSCLE, BONE_C, BONE_S = range(8)
LABEL_NAMES = ["air", "skin", "fat", "connective", "tendon", "muscle", "cortical bone", "cancellous bone"]


@dataclass
class Model:
    h: tuple                       # voxel size (mm) x, y, z
    x: np.ndarray                  # cell centres
    y: np.ndarray
    z: np.ndarray
    outline: Outline
    label2d: np.ndarray            # (nx, ny) tissue labels of the static layers (skin/fat/bone/conn/compartment)
    comp2d: np.ndarray             # (nx, ny) compartment index (-1 none)
    rho2d: np.ndarray              # (nx, ny) area quantile of the voxel inside its compartment (0 core, 1 edge)
    depth2d: np.ndarray            # (nx, ny) distance to skin (mm)
    sx: np.ndarray = field(repr=False, default=None)
    sy: np.ndarray = field(repr=False, default=None)
    sz: np.ndarray = field(repr=False, default=None)
    labels3d: np.ndarray = field(repr=False, default=None)
    comp3d: np.ndarray = field(repr=False, default=None)  # compartment index where muscle (active), else -1

    @property
    def shape(self):
        return (len(self.x), len(self.y), len(self.z))


def build_model(h=(0.5, 0.5, 1.0), circ=CIRC, t_fat=T_FAT, t_skin=T_SKIN, sig=None, muscles=MUSCLES,
                homogeneous=None):
    sig = dict(SIG if sig is None else sig)
    hx, hy, hz = h
    x = np.arange(DOMAIN["x"][0] + hx / 2, DOMAIN["x"][1], hx)
    y = np.arange(DOMAIN["y"][0] + hy / 2, DOMAIN["y"][1], hy)
    z = np.arange(DOMAIN["z"][0] + hz / 2, DOMAIN["z"][1], hz)
    ol = Outline(circ)
    X, Y = np.meshgrid(x, y, indexing="ij")
    dep = ol.depth(X, Y)
    lab = np.full(X.shape, AIR, np.int8)
    lab[dep > 0] = SKIN
    lab[dep > t_skin] = FAT
    sub = dep > t_skin + t_fat
    lab[sub] = CONN
    comp = np.full(X.shape, -1, np.int16)
    rho = np.full(X.shape, np.inf)
    for k, m in enumerate(muscles):
        # compartments are dilated by DILATE and split Voronoi-style so they fill the
        # sub-fascial space as in axial MRI; rho is normalised so that rho = 1 at the dilated edge
        r = _ell_rho(X, Y, m.centre, m.axes, m.angle) / DILATE
        take = sub & (r < 1) & (r < rho)
        comp[take] = k
        rho[take] = r[take]
    for b in BONES.values():
        r = _ell_rho(X, Y, b["centre"], b["axes"], b["angle"])
        inner = _ell_rho(X, Y, b["centre"], (b["axes"][0] - b["cortex"], b["axes"][1] - b["cortex"]), b["angle"])
        lab[r < 1] = BONE_C
        lab[inner < 1] = BONE_S
        comp[r < 1] = -1
    rho[comp < 0] = np.inf
    # replace rho by its area quantile inside each compartment (0 = centre, 1 = edge), so that
    # 'muscle where q >= 1 - f(z)' makes f exactly the muscle area fraction of the compartment
    q = np.full(X.shape, np.inf)
    for k in range(len(muscles)):
        idx = np.flatnonzero(comp.ravel() == k)
        if len(idx):
            order = np.argsort(rho.ravel()[idx])
            qq = np.empty(len(idx)); qq[order] = (np.arange(len(idx)) + 0.5) / len(idx)
            q.ravel()[idx] = qq
    rho = q
    model = Model(h, x, y, z, ol, lab, comp, rho, dep)
    if homogeneous is not None:
        return model
    nx, ny, nz = model.shape
    lab3 = np.repeat(lab[:, :, None], nz, 2)
    comp3 = np.full((nx, ny, nz), -1, np.int16)
    for k, m in enumerate(muscles):
        in2d = comp == k
        if not in2d.any():
            continue
        zin = (z >= m.z_range[0]) & (z <= m.z_range[1])
        f = muscle_fraction(m, z) if m.z_mtj > -1e8 else np.ones_like(z)
        # muscle where area-quantile q >= 1 - f  (central tendon core shrinks proximally)
        musc = (rho[in2d][:, None] >= 1.0 - f[None, :]) & (f[None, :] > 0) & zin[None, :]
        sub3 = np.where(musc, MUSCLE, TENDON).astype(np.int8)
        if m.z_range[0] > -1e8:  # compartment absent outside its z range -> connective tissue
            sub3[:, ~zin] = CONN
        lab3[in2d] = sub3
        cc = np.where(musc, k, -1).astype(np.int16)
        comp3[in2d] = cc
    model.labels3d, model.comp3d = lab3, comp3
    iso = {SKIN: sig["skin"], FAT: sig["fat"], CONN: sig["connective"], TENDON: sig["tendon"],
           BONE_C: sig["bone_cortical"], BONE_S: sig["bone_cancellous"], AIR: 0.0}
    sx = np.zeros((nx, ny, nz)); sy = np.zeros_like(sx); sz = np.zeros_like(sx)
    for L, v in iso.items():
        msk = lab3 == L
        sx[msk] = sy[msk] = sz[msk] = v
    for k, m in enumerate(muscles):
        msk = comp3 == k
        if m.fibre_axis == "z":
            sx[msk], sy[msk], sz[msk] = sig["muscle_T"], sig["muscle_T"], sig["muscle_L"]
        else:  # transverse fibres (PQ), ~x-aligned
            sx[msk], sy[msk], sz[msk] = sig["muscle_L"], sig["muscle_T"], sig["muscle_T"]
    model.sx, model.sy, model.sz = sx, sy, sz
    return model


# ---------------------------------------------------------------- electrodes
@dataclass
class Electrode:
    s: float          # arc position (mm) along the skin from the volar midline towards radial
    z: float          # mm above the crease
    kind: str = "disc6.5"   # 'disc6.5', 'disc2', 'pins2x2'

    def key(self):
        return f"{self.kind}_s{self.s:+.2f}_z{self.z:.2f}"


def electrode_points(el: Electrode, outline: Outline, dsub=0.1):
    """Sub-sampled contact points (s, z) of an electrode footprint on the skin surface."""
    if el.kind.startswith("disc"):
        r = float(el.kind[4:]) / 2
        cs = [(0.0, 0.0, r)]
    elif el.kind == "pins2x2":   # four 2 mm pins on a 3.5 mm square, connected together
        cs = [(dx, dz, 1.0) for dx in (-1.75, 1.75) for dz in (-1.75, 1.75)]
    else:
        raise ValueError(el.kind)
    pts = []
    for dx, dz, r in cs:
        g = np.arange(-r + dsub / 2, r, dsub)
        U, V = np.meshgrid(g, g, indexing="ij")
        m = U ** 2 + V ** 2 <= r ** 2
        pts.append(np.stack([el.s + dx + U[m], el.z + dz + V[m]], 1))
    return np.concatenate(pts)


def electrode_weights(el: Electrode, model: Model):
    """Uniform current density over the footprint -> per-voxel weights (sum to 1).

    Dry contacts have interface impedance >> tissue spreading resistance, so the current density
    under a pad is ~uniform; by reciprocity the pad then reads the area-average skin potential."""
    pts = electrode_points(el, model.outline)
    bx, by, nxv, nyv = model.outline.point(pts[:, 0])
    hx, hy, hz = model.h
    # step inward from the true surface until a tissue voxel is hit
    lab = model.label2d
    out = {}
    ix = iy = None
    for step in np.arange(0.25, 3.0, 0.25):
        qx, qy = bx - nxv * step, by - nyv * step
        ix = np.floor((qx - (model.x[0] - hx / 2)) / hx).astype(int)
        iy = np.floor((qy - (model.y[0] - hy / 2)) / hy).astype(int)
        ok = lab[ix, iy] != AIR
        if step == 0.25:
            fx, fy = ix.copy(), iy.copy(); found = ok.copy()
        else:
            new = ok & ~found
            fx[new], fy[new] = ix[new], iy[new]; found |= ok
        if found.all():
            break
    iz = np.floor((pts[:, 1] - (model.z[0] - hz / 2)) / hz).astype(int)
    lin = np.ravel_multi_index((fx, fy, iz), model.shape)
    u, c = np.unique(lin, return_counts=True)
    return u, c / c.sum(), len(pts) * 0.01  # voxel indices, weights, area mm^2


def pod_positions(outline: Outline, n=8, pitch=18.0, offset=0.0):
    """Arc positions of n pods, evenly pitched, centred opposite the ulna (gap over the ulna)."""
    bu = BONES["ulna"]["centre"]
    s_ulna = outline.arc_of(*bu)
    s_mid = s_ulna + outline.circ / 2
    return np.mod(s_mid + (np.arange(n) - (n - 1) / 2) * pitch + offset, outline.circ)
