"""openEMS FDTD model of the neurband rev C 2.4 GHz printed IFA (TI SWRA117D / AN043).

Geometry comes from the native board via kicad_geom.py (build/geom.json): the
antenna copper polygon, the four filled GND layers and the GND vias.  Mechanics
(cell, housing, flex pods, wrist) are simple boxes taken from docs/mech/mechanical_c.md
and docs/layout/flex_c_layout.md.

Frame: x = KiCad x, y = KiCad y (mm), z up, z = 0 at the board bottom copper.  Using
KiCad y without flipping makes the model a mirror image of the real board, which
does not change S11 or efficiency.

    python sim/antenna/model.py --case fs|enc|flex|worn|worn_nohatch|mono_fs|mono_worn
                                [--res 0.25] [--threads 12]

Raw openEMS output goes to sim/antenna/build/<case>_r<res>/, the reduced
result (S11, Zin, efficiency) to sim/antenna/results/<case>_r<res>.json.
"""
import argparse, json, os, sys, time
import numpy as np
from matplotlib.path import Path

from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import C0, EPS0

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
RESULTS = os.path.join(HERE, 'results')
GEOM = json.load(open(os.environ.get('OE_GEOM', os.path.join(BUILD, 'geom.json'))))
TAG_SUFFIX = os.environ.get('OE_TAG', '')     # e.g. '_v2' for the reworked-ground board

F0, FC = 2.45e9, 1.2e9          # Gaussian excitation: centre, 20 dB half-width
F_EFF = [2.40e9, 2.44e9, 2.48e9]
W = 2 * np.pi * 2.44e9

# ---- stack (mm) -------------------------------------------------------------
Z_B, Z_IN2, Z_IN1, Z_F = 0.0, 0.135, 0.865, 1.0     # copper sheets (centre planes)
LAYER_Z = {'B.Cu': Z_B, 'In2.Cu': Z_IN2, 'In1.Cu': Z_IN1, 'F.Cu': Z_F}
BOARD = (0.0, 0.0, 28.7, 27.0)
# housing (KiCad x,y; module = (x-14, 12.2-y)); module 31.9 x 34.3, walls 1.1
HX0, HX1, HY0, HY1 = 14 - 15.95, 14 + 15.95, 12.2 - 17.15, 12.2 + 17.15
Z_FLOOR0, Z_FLOOR1 = -1.7, -0.6            # floor 1.1 mm, 0.6 mm gap to board bottom
Z_LID0, Z_LID1 = 7.2, 8.2                  # lid top (module z 8.9..9.9)
WALL = 1.1
CELL = (11.0, -3.3, 23.0, 21.7, Z_F + 1.3, Z_F + 1.3 + 4.0)   # LiPo as PEC box
# flex pods (2.8 mm below top copper); hatch on board-facing side
Z_PAD = Z_F - 2.8          # -1.8
Z_HATCH = Z_PAD + 0.1      # -1.7 (real PI core is 25 um; see EPS_FLEX)
EPS_FLEX = 3.4 * 0.1 / 0.025   # keeps the real pad-to-hatch capacitance with a 0.1 mm cell
POD3_X, POD4_X = (1.45, 8.55), (19.45, 26.55)
POD_Y = (12.2 - 15.0, 12.2 + 15.0)      # 30 mm paddle
PAD_Y = (22.2, 12.2, 2.2)
PAD_R = 3.25
SPINE_Y = (11.6, 19.2)                   # flex spine under module centre strip
TAIL_X = (11.5, 16.5)                    # tail to J1 at the y = 27 edge
# wrist: 0.65 mm foam/air below the pads, then skin / fat / muscle
Z_SKIN1 = Z_PAD - 0.65
SKIN_GAP = {'worn_far': 2.15}       # sensitivity case: skin 1.5 mm farther (wrist curving away)


def skin_top(case):
    return Z_PAD - SKIN_GAP.get(case, 0.65)
TISSUE = [('skin', 1.5, 38.0, 1.46), ('fat', 3.0, 5.3, 0.10), ('muscle', 20.0, 52.7, 1.74)]
PH_X = (14 - 35.0, 14 + 35.0)            # 70 x 80 mm flat phantom centred on the module
PH_Y = (12.2 - 40.0, 12.2 + 40.0)

ANT_KEEP = (0.0, 11.65, 5.65, 27.0)      # all-layer radiator exclusion
ANT_COURT = (0.30, 11.50, 6.25, 27.0)    # rotated stock courtyard
FEED = (5.9, 14.7)
SHORT = (5.9, 12.6)


def kappa(eps_r, tand, w=W):
    return w * EPS0 * eps_r * tand


REGION = []      # (a, b, res) of graded regions, filled in by lines_region


def lines_region(a, b, res):
    a, b = min(a, b), max(a, b)
    n = max(1, int(np.ceil((b - a) / res)))
    return [('r', v, res) for v in np.linspace(a, b, n + 1)]


def merge_lines(v):
    """Fixed lines (floats) are kept (deduped at 0.04 mm); region lines (tuples) are added
    only where they are not closer than 0.45*res to a line already kept."""
    fixed = dedupe([u for u in v if not isinstance(u, tuple)], 0.04)
    reg = sorted([u for u in v if isinstance(u, tuple)], key=lambda t: t[2])
    out = list(fixed)
    for _, x, r in reg:
        if np.min(np.abs(np.asarray(out) - x)) > 0.6 * r:
            out.append(x)
    return sorted(out)


def dedupe(v, tol):
    v = np.sort(np.asarray(v, float))
    out = [v[0]]
    for x in v[1:]:
        if x - out[-1] > tol:
            out.append(x)
    return out


def build_mesh(case, res):
    """Fixed lines + region resolutions, then graded with SmoothMeshLines."""
    ant = np.array(GEOM['antenna']['copper_polys'][0])
    fine, mid, tis = res, 2 * res, 1.0
    mono = case.startswith('mono')
    x = [0, 28.7, 5.65, FEED[0], 11, 23, HX0, HX0 + WALL, HX1 - WALL, HX1]
    y = [0, 27, 11.65, FEED[1], SHORT[1], -3.3, HY0, HY0 + WALL, HY1 - WALL, HY1]
    if not mono:
        # antenna polygon edges (skip the tiny drill-keyhole arc vertices)
        x += [v for v in ant[:, 0] if abs(v - 5.9) > 0.32 or v in (5.65, 6.15)]
        y += [v for v in ant[:, 1] if abs(v - 12.6) > 0.32]
    else:
        x += MONO_X
        y += MONO_Y
    x += lines_region(-0.5, 7.0, fine) + lines_region(7.0, 28.7, mid)
    y += lines_region(11.0, 27.5, fine) + lines_region(-3.3, 11.0, mid) + lines_region(27.5, 29.35, mid)
    if case in ('flex', 'worn', 'worn_nohatch', 'mono_worn', 'worn_far'):
        x += list(TAIL_X)   # pods/pads snap to the board mesh
        y += [27.6]
    # phantom region at 1 mm (always meshed so every case shares the same grid)
    worn = case in ('worn', 'worn_nohatch', 'mono_worn', 'worn_far')
    zs = skin_top(case)
    if worn:   # 1 mm in tissue within ~10 mm of the module, 1.6 mm beyond (lambda_muscle/9.5 at 2.7 GHz)
        x += (lines_region(PH_X[0], -12.0, 1.6) + lines_region(-12.0, -2.0, tis) +
              lines_region(30.5, 40.0, tis) + lines_region(40.0, PH_X[1], 1.6) + list(PH_X))
        y += (lines_region(PH_Y[0], -15.0, 1.6) + lines_region(-15.0, -5.0, tis) +
              lines_region(29.5, 39.5, tis) + lines_region(39.5, PH_Y[1], 1.6) + list(PH_Y))
    # air to the PML
    pad_xy, pad_zb, pad_zt = 46.0, 46.0, 46.0
    x += [PH_X[0] - pad_xy, PH_X[1] + pad_xy, PH_X[0] - 5, PH_X[1] + 5]
    y += [PH_Y[0] - pad_xy, PH_Y[1] + pad_xy, PH_Y[0] - 5, PH_Y[1] + 5]
    zt = [zs - sum(t[1] for t in TISSUE[:k + 1]) for k in range(len(TISSUE))]
    z = [Z_B, Z_IN2, 0.5, Z_IN1, Z_F, Z_FLOOR0, Z_FLOOR1, -0.3, Z_PAD, Z_HATCH, zs,
         CELL[4], CELL[5], Z_LID0, Z_LID1, 2.0, 3.0]
    if worn:
        z += (lines_region(zs, zs - 1.5, 0.5) + lines_region(zt[0], zt[1], 1.0) +
              lines_region(zt[1], zt[1] - 8.0, tis) + lines_region(zt[1] - 8.0, zt[2], 1.6))
    z += list(np.linspace(Z_FLOOR0, Z_FLOOR1, 3))
    z += [zt[2] - pad_zb, Z_LID1 + pad_zt, zt[2] - 5, Z_LID1 + 6]
    return merge_lines(x), merge_lines(y), merge_lines(z)


# small-monopole stand-in for a chip antenna: an L-shaped 0.5 mm strip fed at the
# ground edge, 1.5 mm off the y = 27 board edge corner (chip-antenna-like volume and
# placement at the open end of the board); resonated with an ideal L network in post.
# Fix 2026-10-29: the first version (feed at y = 24.5) was shorted by the fence via at
# (6.0, 24.2), which snapped onto the feed tab, and by the F.Cu pour under the tab. The feed
# now sits midway between fence vias (y = 25.2) with a local F.Cu pour cut-out.
MONO_FEED = (5.9, 25.2)
MONO_TAB = (24.95, 25.45)
MONO_CUT = (5.65, 24.7, 6.4, 25.7)        # F.Cu pour cut-out around the feed tab
MONO_X = [5.65, 5.9, 6.4, 1.0, 1.5]
MONO_Y = [24.7, 24.95, 25.2, 25.45, 25.7, 26.0, 26.5, 20.0]


def raster_cells(xl, yl, polys):
    """Mask of mesh cells whose centre lies in any polygon (KiCad fills are fractured)."""
    xc, yc = 0.5 * (xl[1:] + xl[:-1]), 0.5 * (yl[1:] + yl[:-1])
    X, Y = np.meshgrid(xc, yc, indexing='ij')
    pts = np.c_[X.ravel(), Y.ravel()]
    m = np.zeros(len(pts), bool)
    for p in polys:
        pa = np.asarray(p)
        sel = ((pts[:, 0] >= pa[:, 0].min()) & (pts[:, 0] <= pa[:, 0].max()) &
               (pts[:, 1] >= pa[:, 1].min()) & (pts[:, 1] <= pa[:, 1].max()))
        if sel.any():
            m[sel] |= Path(pa).contains_points(pts[sel])
    return m.reshape(X.shape)


def mask_to_boxes(mask):
    """Greedy rectangle cover of a cell mask: list of (i0, i1, j0, j1) node ranges."""
    m = mask.copy()
    boxes = []
    nx, ny = m.shape
    for j in range(ny):
        i = 0
        while i < nx:
            if not m[i, j]:
                i += 1
                continue
            i0 = i
            while i < nx and m[i, j]:
                i += 1
            i1 = i
            j1 = j + 1
            while j1 < ny and m[i0:i1, j1].all():
                j1 += 1
            m[i0:i1, j:j1] = False
            boxes.append((i0, i1, j, j1))
    return boxes


def add_raster(prop, xl, yl, polys, z, keep_out=None, prio=10):
    xl, yl = np.asarray(xl), np.asarray(yl)
    sx = (xl >= BOARD[0] - 0.01) & (xl <= BOARD[2] + 0.01)
    sy = (yl >= BOARD[1] - 0.01) & (yl <= BOARD[3] + 0.01)
    xs, ys = xl[sx], yl[sy]
    mask = raster_cells(xs, ys, polys)
    if keep_out is not None:
        rects = [keep_out] if np.ndim(keep_out[0]) == 0 else keep_out
        xc, yc = 0.5 * (xs[1:] + xs[:-1]), 0.5 * (ys[1:] + ys[:-1])
        for x0, y0, x1, y1 in rects:
            mask[np.ix_((xc > x0) & (xc < x1), (yc > y0) & (yc < y1))] = False
    boxes = mask_to_boxes(mask)
    for i0, i1, j0, j1 in boxes:
        prop.AddBox([xs[i0], ys[j0], z], [xs[i1], ys[j1], z], priority=prio)
    return len(boxes), float(mask.sum())


def circle(cx, cy, r, n=24):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return [list(cx + r * np.cos(a)), list(cy + r * np.sin(a))]


def build(case, res, sim_path):
    FDTD = openEMS(NrTS=400000, EndCriteria=float(os.environ.get("OE_END", "3e-4")))
    FDTD.SetGaussExcite(F0, FC)
    FDTD.SetBoundaryCond(['PML_8'] * 6)
    CSX = ContinuousStructure()
    FDTD.SetCSX(CSX)
    mesh = CSX.GetGrid()
    mesh.SetDeltaUnit(1e-3)
    xl, yl, zl = build_mesh(case, res)
    mesh.SetLines('x', xl)
    mesh.SetLines('y', yl)
    mesh.SetLines('z', zl)
    mesh.SmoothMeshLines('x', 4.0, 1.4)
    mesh.SmoothMeshLines('y', 4.0, 1.4)
    mesh.SmoothMeshLines('z', 4.0, 1.4)
    xl, yl, zl = (np.array(mesh.GetLines(d)) for d in 'xyz')
    info = {'case': case, 'res': res, 'n_cells': int(len(xl) * len(yl) * len(zl)),
            'n_lines': [len(xl), len(yl), len(zl)]}

    worn = case in ('worn', 'worn_nohatch', 'mono_worn', 'worn_far')
    flex = case in ('flex', 'worn', 'worn_nohatch', 'mono_worn', 'worn_far')
    enc = case not in ('fs', 'mono_fs')
    mono = case.startswith('mono')

    # board dielectric (FR-4 4.3 / tan d 0.02), outline with 1 mm corner radius ignored
    fr4 = CSX.AddMaterial('FR4', epsilon=4.3, kappa=kappa(4.3, 0.02))
    fr4.AddBox([0, 0, Z_B], [28.7, 27.0, Z_F], priority=3)

    gnd = CSX.AddMetal('GND')
    nb = {}
    for lay, z in LAYER_Z.items():
        polys = GEOM['gnd_fill'].get(lay, [])
        ko = [ANT_KEEP, MONO_CUT] if (mono and lay == 'F.Cu') else [ANT_KEEP]
        nb[lay] = add_raster(gnd, xl, yl, polys, z, keep_out=ko)[0]
    info['gnd_boxes'] = nb
    # GND vias (incl. the 7 counterpoise stitches) as z lines, snapped to the nearest
    # mesh node (zero-width primitives off the grid are silently dropped by openEMS)
    for v in GEOM['gnd_vias']:
        vx, vy = xl[np.argmin(abs(xl - v['x']))], yl[np.argmin(abs(yl - v['y']))]
        if mono and MONO_CUT[0] <= vx <= MONO_CUT[2] and MONO_CUT[1] <= vy <= MONO_CUT[3]:
            continue     # never let a snapped via land on the stand-in's feed
        gnd.AddBox([vx, vy, Z_B], [vx, vy, Z_F], priority=10)

    if not mono:
        ant = CSX.AddMetal('antenna')
        poly = np.array(GEOM['antenna']['copper_polys'][0])
        ant.AddPolygon([list(poly[:, 0]), list(poly[:, 1])], 'z', Z_F, priority=11)
        # short-to-ground through-hole (pad 2)
        gnd.AddBox([SHORT[0], SHORT[1], Z_B], [SHORT[0], SHORT[1], Z_F], priority=10)
        port = FDTD.AddLumpedPort(1, 50, [FEED[0], FEED[1], Z_IN1], [FEED[0], FEED[1], Z_F], 'z',
                                  excite=1.0, priority=20)
    else:
        ant = CSX.AddMetal('antenna')
        # feed tab over the ground edge, then L-shaped 0.5 mm strip in the clearance
        t0, t1 = MONO_TAB
        ant.AddBox([5.65, t0, Z_F], [MONO_FEED[0], t1, Z_F], priority=11)
        ant.AddBox([1.5, t0, Z_F], [5.65, t1, Z_F], priority=11)
        ant.AddBox([1.0, 20.0, Z_F], [1.5, 26.5, Z_F], priority=11)
        port = FDTD.AddLumpedPort(1, 50, [MONO_FEED[0], MONO_FEED[1], Z_IN1],
                                  [MONO_FEED[0], MONO_FEED[1], Z_F], 'z', excite=1.0, priority=20)

    if enc:
        pa12 = CSX.AddMaterial('PA12', epsilon=2.95, kappa=kappa(2.95, 0.02))
        pa12.AddBox([HX0, HY0, Z_FLOOR0], [HX1, HY1, Z_FLOOR1], priority=2)       # floor
        pa12.AddBox([HX0, HY0, Z_LID0], [HX1, HY1, Z_LID1], priority=2)           # lid top
        for b in ([HX0, HY0, HX0 + WALL, HY1], [HX1 - WALL, HY0, HX1, HY1],
                  [HX0, HY0, HX1, HY0 + WALL], [HX0, HY1 - WALL, HX1, HY1]):
            pa12.AddBox([b[0], b[1], Z_FLOOR0], [b[2], b[3], Z_LID1], priority=2)
        air = CSX.AddMaterial('air_inside', epsilon=1.0)
        air.AddBox([HX0 + WALL, HY0 + WALL, Z_FLOOR1], [HX1 - WALL, HY1 - WALL, Z_LID0], priority=1)
        cell = CSX.AddMetal('cell')
        cell.AddBox(CELL[0:2] + (CELL[4],), CELL[2:4] + (CELL[5],), priority=5)

    if flex:
        sh = CSX.AddMetal('flex_gnd')
        pi = CSX.AddMaterial('flex_PI_equiv', epsilon=EPS_FLEX, kappa=kappa(3.4, 0.005))
        hatch_rects = []
        for (x0, x1) in (POD3_X, POD4_X):
            hatch_rects.append((x0, POD_Y[0], x1, POD_Y[1]))
        if case == 'worn_nohatch':
            # cut pod 3 hatch under the antenna courtyard (x <= 6.25, y >= 11.5)
            x0, y0, x1, y1 = hatch_rects[0]
            hatch_rects[0] = (x0, y0, x1, ANT_COURT[1])
            hatch_rects.append((ANT_COURT[2], ANT_COURT[1], x1, y1))
        hatch_rects.append((POD3_X[1], SPINE_Y[0], POD4_X[0], SPINE_Y[1]))     # spine
        hatch_rects.append((TAIL_X[0], SPINE_Y[1], TAIL_X[1], 27.6))          # tail
        for r in hatch_rects:
            sh.AddBox([r[0], r[1], Z_HATCH], [r[2], r[3], Z_HATCH], priority=12)
            pi.AddBox([r[0], r[1], Z_PAD], [r[2], r[3], Z_HATCH], priority=3)
        # tail U-turn up to J1 GND on the top side (pins 1/20 + shield), y = 27.6
        sh.AddBox([TAIL_X[0], 27.6, Z_HATCH], [TAIL_X[1], 27.6, Z_F], priority=12)
        sh.AddBox([TAIL_X[0], 26.4, Z_F], [TAIL_X[1], 27.6, Z_F], priority=12)
        pads = CSX.AddMetal('flex_pads')
        for cx in (5.0, 23.0):
            for cy in PAD_Y:
                pads.AddPolygon(circle(cx, cy, PAD_R), 'z', Z_PAD, priority=12)
        info['hatch_rects'] = hatch_rects

    if worn:
        zt = skin_top(case)
        for k, (name, t, er, sig) in enumerate(TISSUE):
            m = CSX.AddMaterial(name, epsilon=er, kappa=sig)
            m.AddBox([PH_X[0], PH_Y[0], zt - t], [PH_X[1], PH_Y[1], zt], priority=4)
            zt -= t

    # NF2FF box in air, 6 cells inside the PML start
    zbot = skin_top(case) - sum(t[1] for t in TISSUE)
    nf_start = [PH_X[0] - 5, PH_Y[0] - 5, zbot - 5]
    nf_stop = [PH_X[1] + 5, PH_Y[1] + 5, Z_LID1 + 6]
    for d, L in enumerate((xl, yl, zl)):     # keep >= 8 cells clear of the 8-cell PML
        assert nf_start[d] > L[10] and nf_stop[d] < L[-11], (d, nf_start[d], L[16], nf_stop[d], L[-17])
    nf = FDTD.CreateNF2FFBox(start=nf_start, stop=nf_stop, frequency=F_EFF)
    os.makedirs(sim_path, exist_ok=True)
    CSX.Write2XML(os.path.join(sim_path, 'model.xml'))
    return FDTD, port, nf, info, (xl, yl, zl)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True)
    ap.add_argument('--res', type=float, default=0.25)
    ap.add_argument('--threads', type=int, default=12)
    ap.add_argument('--setup-only', action='store_true')
    ap.add_argument('--post-only', action='store_true')
    a = ap.parse_args()
    tag = f'{a.case}_r{a.res:g}{TAG_SUFFIX}'
    sim_path = os.path.join(BUILD, tag)
    FDTD, port, nf, info, lines = build(a.case, a.res, sim_path)
    print(json.dumps({k: v for k, v in info.items() if k != 'hatch_rects'}), flush=True)
    if a.setup_only:
        return
    t0 = time.time()
    if not a.post_only:
        FDTD.Run(sim_path, cleanup=True, numThreads=a.threads, verbose=1)
    info['run_s'] = time.time() - t0
    f = np.linspace(2.2e9, 2.7e9, 501)
    port.CalcPort(sim_path, f)
    Zin = port.uf_tot / port.if_tot
    s11 = port.uf_ref / port.uf_inc
    port.CalcPort(sim_path, np.array(F_EFF))
    Pacc = np.real(port.P_acc)
    Pinc = np.real(port.P_inc)
    th = np.arange(0, 181, 3.0)
    ph = np.arange(0, 361, 5.0)
    r = nf.CalcNF2FF(sim_path, F_EFF, th, ph, center=[14e-3, 12.2e-3, 0], read_cached=False)
    Prad = np.array(r.Prad)
    out = dict(info)
    out.update({'f': list(f), 'Zin_re': list(Zin.real), 'Zin_im': list(Zin.imag),
                's11_re': list(s11.real), 's11_im': list(s11.imag),
                'f_eff': F_EFF, 'Pacc': list(Pacc), 'Pinc': list(Pinc), 'Prad': list(Prad),
                'eta_rad': list(Prad / Pacc), 'eta_tot': list(Prad / Pinc),
                'Dmax_dBi': list(10 * np.log10(np.array(r.Dmax)))})
    os.makedirs(RESULTS, exist_ok=True)
    json.dump(out, open(os.path.join(RESULTS, tag + '.json'), 'w'))
    i = np.argmin(np.abs(f - 2.44e9))
    print(f'{tag}: S11(2.44)={20*np.log10(abs(s11[i])):.2f} dB Zin={Zin[i]:.1f} '
          f'fmin={f[np.argmin(abs(s11))]/1e9:.3f} GHz  eta_rad={Prad/Pacc}  eta_tot={Prad/Pinc} '
          f'run {info["run_s"]:.0f} s', flush=True)


if __name__ == '__main__':
    main()
