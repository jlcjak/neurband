"""Figures for docs/science/emg_forward_model.md (reads cache/results.json, cache/study.npz)."""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "4")
import json
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap, LogNorm, TwoSlopeNorm, LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Circle, Ellipse  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geometry import (MUSCLES, BONES, Z_BAND, AIR, SKIN, FAT, CONN, TENDON, MUSCLE, BONE_C, BONE_S)  # noqa: E402
from leadfield import CACHE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.abspath(os.path.join(HERE, "..", "..", "docs", "science", "figures"))
os.makedirs(FIG, exist_ok=True)

# reference palette (dataviz skill): categorical order, blue sequential, blue<->red diverging w/ gray mid
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQ = ["#fcfcfb", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]
SURF, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#9a9893"
CMAP_SEQ = LinearSegmentedColormap.from_list("seqblue", SEQ)
CMAP_DIV = LinearSegmentedColormap.from_list("div", ["#104281", "#3987e5", "#9ec5f4", "#f0efec", "#f2a3a2", "#e34948", "#9c1f1f"])
TISSUE_COL = {AIR: SURF, SKIN: "#e9c9b0", FAT: "#f4e3b5", CONN: "#ebe7df", TENDON: "#d6d0c2",
              MUSCLE: "#c0574f", BONE_C: "#f7f5ef", BONE_S: "#e2dbc9"}
SHORT = {"APL_EPB": "APL/EPB", "ECR": "ECRL/B"}

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": False, "grid.color": "#e6e4df", "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10,
    "axes.titleweight": "bold", "legend.frameon": False, "lines.linewidth": 1.6,
})


def short(n):
    return SHORT.get(n, n)


def load():
    with open(os.path.join(CACHE, "results.json")) as f:
        res = json.load(f)
    d = dict(np.load(os.path.join(CACHE, "study.npz")))
    return res, d


def tissue_rgb(lab):
    from matplotlib.colors import to_rgb
    img = np.zeros(lab.shape + (3,))
    for k, c in TISSUE_COL.items():
        img[lab == k] = to_rgb(c)
    return img


def surface_values(model, phi, s, z):
    """phi on the skin: voxel just inside the surface for each (s, z)."""
    S, Z = np.meshgrid(s, z, indexing="ij")
    bx, by, nx, ny = model.outline.point(S.ravel())
    hx, hy, hz = model.h
    lab = model.label2d
    out = np.full(S.size, np.nan)
    found = np.zeros(S.size, bool)
    iz = np.clip(np.floor((Z.ravel() - (model.z[0] - hz / 2)) / hz).astype(int), 0, len(model.z) - 1)
    for step in np.arange(0.25, 3.0, 0.25):
        ix = np.floor((bx - nx * step - (model.x[0] - hx / 2)) / hx).astype(int)
        iy = np.floor((by - ny * step - (model.y[0] - hy / 2)) / hy).astype(int)
        ok = (lab[ix, iy] != AIR) & ~found
        out[ok] = phi[ix[ok], iy[ok], iz[ok]]
        found |= ok
    return out.reshape(S.shape)


def fig_anatomy(st, res):
    """README figure: cross-section anatomy + pods, lead-field sensitivity map, longitudinal lead field."""
    m = st.model
    iz = int(np.argmin(abs(m.z - Z_BAND)))
    lab = m.labels3d[:, :, iz]
    C8 = st.config()
    P, N, s = C8
    L = st.lfs.L
    fig = plt.figure(figsize=(15, 5.0))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 1.0], wspace=0.45)
    ext = [m.x[0] - m.h[0] / 2, m.x[-1] + m.h[0] / 2, m.y[0] - m.h[1] / 2, m.y[-1] + m.h[1] / 2]

    ax = fig.add_subplot(gs[0])
    ax.imshow(np.transpose(tissue_rgb(lab), (1, 0, 2)), origin="lower", extent=ext, interpolation="nearest")
    for k, mu in enumerate(MUSCLES):
        reg = m.comp2d == k
        if not reg.any():
            continue
        X, Y = np.meshgrid(m.x, m.y, indexing="ij")
        cx, cy = X[reg].mean(), Y[reg].mean()
        musc = (m.comp3d[:, :, iz] == k).sum() > 0
        ax.text(cx, cy, short(mu.name), ha="center", va="center", fontsize=6.5,
                color="white" if musc and mu.name not in ("EPL", "EDM", "ECU") else INK, fontweight="bold")
    for i, si in enumerate(s):
        bx, by, nx, ny = m.outline.point(si)
        ax.add_patch(Circle((bx + 1.6 * nx, by + 1.6 * ny), 1.6, color=CAT[0], zorder=5))
        ax.text(bx + 4.6 * nx, by + 4.6 * ny, str(i + 1), ha="center", va="center", fontsize=8, color=INK, fontweight="bold")
    ax.text(0, -23.2, "dorsal", ha="center", color=INK2, fontsize=8)
    ax.text(9, 19.2, "volar", ha="center", color=INK2, fontsize=8)
    ax.text(31, 0, "radial", rotation=-90, va="center", color=INK2, fontsize=8)
    ax.text(-29.6, -8, "ulnar", rotation=90, va="center", color=INK2, fontsize=8)
    ax.text(-15.3, -5.4, "ulna", ha="center", va="center", fontsize=7, color=INK2)
    ax.text(8.5, -3.2, "radius", ha="center", va="center", fontsize=7, color=INK2)
    ax.set_xlim(-33, 33); ax.set_ylim(-25, 25); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"Right forearm {Z_BAND:.0f} mm above the wrist crease\n(palm up, thumb side right; 8 pods on a {res['circ']:.0f} mm ring)",
                 fontsize=9.5, pad=16)
    # legend swatches
    for xl, (k, nm) in zip((-32, -21, -10.5, 4, 12, 21), [(MUSCLE, "muscle"), (TENDON, "tendon"), (CONN, "connective"),
                                                          (FAT, "fat"), (SKIN, "skin"), (BONE_S, "bone")]):
        ax.add_patch(plt.Rectangle((xl, -27.8), 2.2, 1.6, color=TISSUE_COL[k], clip_on=False, ec=MUTED, lw=0.3))
        ax.text(xl + 2.8, -27.0, nm, fontsize=7, va="center", color=INK2, clip_on=False)

    # panel 2: sensitivity to fibre-direction dipoles, max over the 8 channels (dB re global max)
    ax = fig.add_subplot(gs[1])
    G = []
    for p, n in zip(P, N):
        lf = L[:, :, p, :].astype(float) - L[:, :, n, :]
        G.append(np.abs(lf[:, :, iz + 1] - lf[:, :, iz - 1]) / (2 * m.h[2]))
    G = np.stack(G)
    tissue = lab != AIR
    Gm = G.max(0)
    db = 20 * np.log10(Gm / Gm[tissue].max() + 1e-12)
    db[~tissue] = np.nan
    im = ax.imshow(db.T, origin="lower", extent=ext, cmap=CMAP_SEQ.reversed(), vmin=-40, vmax=0)
    arg = np.argmax(G, 0).astype(float); arg[~tissue] = np.nan
    ax.contour(m.x, m.y, arg.T, levels=np.arange(0.5, 8, 1), colors="white", linewidths=0.5, alpha=0.7)
    for b in BONES.values():
        ax.add_patch(Ellipse(b["centre"], 2 * b["axes"][0], 2 * b["axes"][1], angle=b["angle"], fill=False, ec=INK2, lw=0.8))
    ax.contour(m.x, m.y, (m.comp3d[:, :, iz] >= 0).T.astype(float), levels=[0.5], colors=[INK], linewidths=0.6)
    for i, si in enumerate(s):
        bx, by, nx, ny = m.outline.point(si)
        ax.text(bx + 3.4 * nx, by + 3.4 * ny, str(i + 1), ha="center", va="center", fontsize=8, fontweight="bold")
    ax.set_xlim(-33, 33); ax.set_ylim(-25, 25); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Sensitivity to fibre-direction sources\n(best channel, dB; white: channel territories; black: muscle)",
                 fontsize=9.5, pad=16)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.01)
    cb.set_label("dB re. maximum", color=INK2)

    # panel 3: longitudinal (y-z) section through channel 2's pods
    ax = fig.add_subplot(gs[2])
    ch = 1
    bx, by, nx, ny = m.outline.point(s[ch])
    ix = int(np.argmin(abs(m.x - bx)))
    lf = L[ix, :, P[ch], :].astype(float) - L[ix, :, N[ch], :]
    dz = np.gradient(lf, m.h[2], axis=1)
    labs = m.labels3d[ix]
    dz[labs == AIR] = np.nan
    vmax = np.nanpercentile(np.abs(dz), 99.5)
    from matplotlib.colors import SymLogNorm
    im = ax.imshow(dz, origin="lower", aspect="auto", extent=[m.z[0], m.z[-1], m.y[0], m.y[-1]],
                   cmap=CMAP_DIV, norm=SymLogNorm(linthresh=vmax / 300, vmin=-vmax, vmax=vmax))
    ax.contour(m.z, m.y, (labs == MUSCLE).astype(float), levels=[0.5], colors=[INK], linewidths=0.6)
    ax.contour(m.z, m.y, np.isin(labs, [BONE_C, BONE_S]).astype(float), levels=[0.5], colors=[INK2], linewidths=0.6, linestyles="--")
    ys = by
    for zz, lbl in ((Z_BAND + 10, "P"), (Z_BAND - 10, "N")):
        ax.plot([zz - 3.25, zz + 3.25], [ys + 0.6] * 2, color=CAT[1], lw=4, solid_capstyle="butt")
        ax.text(zz, ys + 2.0, lbl, ha="center", fontsize=9, fontweight="bold", color=INK)
    ax.set_xlim(-5, 100); ax.set_ylim(by - 32, by + 3.5)
    ax.set_xlabel("distance above wrist crease (mm)"); ax.set_ylabel("y (mm)")
    ax.set_title(f"Channel {ch + 1} lead field, longitudinal section (x = {bx:.0f} mm)\n"
                 "(dψ/dz, log colour; black = muscle, dashed = bone)", fontsize=9.5)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.01)
    cb.set_label("V/(A·m) per A injected", color=INK2)
    fig.savefig(os.path.join(FIG, "emgfwd_cross_section.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_skinmap(st, res, name="FDS", times_ms=(3.0, 6.0, 9.0)):
    """README figure: skin potential map of one motor unit (forward solve), unrolled skin, + 8 bipolar traces."""
    from solver import FVOperator, MGPreconditioner, pcg
    from sources import membrane_sources, deposit
    m = st.model
    op = FVOperator.from_conductivity(m.sx, m.sy, m.sz, tuple(v * 1e-3 for v in m.h))
    M = MGPreconditioner(op)
    C8 = st.config()
    P, N, s_pods = C8
    B = st.bip(name, C8)
    amp = np.abs(B).max(axis=(1, 2))
    order = np.argsort(amp)
    i_mu = int(order[int(0.8 * len(order))])   # an 80th-percentile MU
    mu = st.pools[name][i_mu]
    C = m.outline.circ
    from geometry import BONES
    s_ulna = m.outline.arc_of(*BONES["ulna"]["centre"])
    sp = np.arange(0, C, 0.5)                    # plot coordinate: arc from the ulna (pod gap)
    s = np.mod(sp + s_ulna, C)
    z = np.arange(-5, 100, 1.0)
    ol = m.outline
    marks = {"volar": ol.s[np.argmax(ol.by)], "radial": ol.s[np.argmax(ol.bx)], "dorsal": ol.s[np.argmin(ol.by)]}
    maps = []
    for tm in times_ms:
        Pp, cur = membrane_sources(mu, tm * 1e-3, m)
        b = deposit(m, Pp, cur)
        phi, it, rr = pcg(op, b, M=M, tol=1e-8, maxit=300)
        maps.append(surface_values(m, phi, s, z) * 1e6)
    vmax = max(np.nanpercentile(np.abs(mm), 99.8) for mm in maps)
    fig = plt.figure(figsize=(13, 6.6))
    gs = fig.add_gridspec(2, len(times_ms), height_ratios=[1.35, 1], hspace=0.38, wspace=0.12)
    for j, (tm, mp) in enumerate(zip(times_ms, maps)):
        ax = fig.add_subplot(gs[0, j])
        im = ax.imshow(mp.T, origin="lower", aspect="auto", extent=[sp[0], sp[-1], z[0], z[-1]], cmap=CMAP_DIV,
                       norm=TwoSlopeNorm(0, -vmax, vmax))
        for k, spk in enumerate(np.mod(s_pods - s_ulna, C)):
            for zz in (Z_BAND - 10, Z_BAND + 10):
                ax.add_patch(Ellipse((spk, zz), 6.5, 6.5, fill=False, ec=INK, lw=0.8))
            ax.text(spk, Z_BAND + 15, str(k + 1), ha="center", fontsize=7.5, fontweight="bold")
        for nm, sm in marks.items():
            ax.text(np.mod(sm - s_ulna, C), z[-1] - 5, nm, ha="center", fontsize=7.5, color=INK2)
        ax.set_title(f"t = {tm:.0f} ms after firing", fontsize=9.5)
        if j == 1:
            ax.set_xlabel("arc length around the forearm, starting at the ulna (mm)")
        if j == 0:
            ax.set_ylabel("mm above wrist crease")
        else:
            ax.set_yticklabels([])
    cb = fig.colorbar(im, ax=fig.axes[:len(times_ms)], fraction=0.015, pad=0.01)
    cb.set_label("skin potential (µV)", color=INK2)
    ax = fig.add_subplot(gs[1, :])
    t = st.t * 1e3
    b = B[i_mu] * 1e6
    off = np.abs(b).max() * 1.1
    for k in range(b.shape[0]):
        ax.plot(t, b[k] - k * off, color=CAT[0] if k % 2 == 0 else CAT[6], lw=1.3)
        ax.text(t[-1] + 0.4, -k * off, f"ch {k + 1}", va="center", fontsize=8, color=INK2)
    for tm in times_ms:
        ax.axvline(tm, color=MUTED, lw=0.8, ls=":")
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    bar = float(10 ** np.floor(np.log10(off)))
    ax.plot([t[-1] - 4, t[-1] - 4], [-6.5 * off, -6.5 * off + bar], color=INK, lw=2)
    ax.text(t[-1] - 4.5, -6.5 * off + bar / 2, f"{bar:.0f} µV", ha="right", va="center", fontsize=8)
    ax.set_xlabel("time (ms)")
    ax.set_xlim(t[0], t[-1] + 3)
    ax.set_title(f"Bipolar signals (P−N, 20 mm, 6.5 mm dry pads) of the same {name} motor unit "
                 f"({mu.n_fibres} fibres), all 8 channels", fontsize=9.5)
    fig.suptitle(f"One {name} motor unit seen from the skin: action potentials start at the end-plate zone "
                 f"(~{np.mean(mu.u_e):.0f} mm), travel at 4 m/s and die at the tendon", fontsize=10.5, fontweight="bold", y=0.995)
    fig.savefig(os.path.join(FIG, "emgfwd_skin_map.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return dict(mu_index=i_mu, n_fibres=mu.n_fibres, u_e=float(np.mean(mu.u_e)), map_peak_uv=float(vmax))


def fig_sensitivity(res, d):
    """README figure: sensitivity matrices (uV RMS at 10% MVC) for 8 and 16 channels."""
    names = res["visible"] + ["FCR", "PL", "ECR"]
    idx = [res["muscles"].index(n) for n in names]
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw=dict(width_ratios=[1, 1.0], wspace=0.25))
    norm = LogNorm(0.3, 300)
    for ax, key, title in ((axs[0], "S8", "neurband: 8 channels, 18 mm pitch"),
                           (axs[1], "S16", "Meta-like: 16 channels, 9 mm pitch")):
        S = d[key][:, idx]
        im = ax.imshow(S, cmap=CMAP_SEQ, norm=norm, aspect="auto")
        for i in range(S.shape[0]):
            for j in range(S.shape[1]):
                v = S[i, j]
                ax.text(j, i, f"{v:.0f}" if v >= 9.5 else f"{v:.1f}", ha="center", va="center",
                        fontsize=6.5 if S.shape[0] > 8 else 7.5, color="white" if v > 25 else INK)
        ax.set_xticks(range(len(names)), [short(n) for n in names], rotation=45, ha="right")
        ax.set_yticks(range(S.shape[0]), [str(i + 1) for i in range(S.shape[0])])
        ax.set_ylabel("channel (1 ulnar, 3 volar, 5 radial, 7 dorsal)")
        ax.set_title(title)
        ax.axvline(len(res["visible"]) - 0.5, color=INK, lw=1)
        ax.set_xlabel("muscle (right of the black line: only tendon under the band)")
    cb = fig.colorbar(im, ax=axs, fraction=0.02, pad=0.01)
    cb.set_label("µV RMS (20–450 Hz), muscle alone at 10% MVC", color=INK2)
    fig.suptitle("Which channel sees which muscle: simulated EMG amplitude for single-muscle contractions",
                 fontsize=11, fontweight="bold")
    fig.savefig(os.path.join(FIG, "emgfwd_sensitivity_matrix.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_validation():
    v = json.load(open(os.path.join(CACHE, "validation.json")))
    mp = dict(np.load(os.path.join(CACHE, "validation_maps.npz")))
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, key, title in ((axs[0], "isotropic_0.3_h0.5", "isotropic 0.3 S/m"),
                           (axs[1], "anisotropic_muscle_h0.5", "anisotropic 0.5 / 0.1 S/m")):
        x, z, num, an = mp[key + "_x"], mp[key + "_z"], mp[key + "_num"], mp[key + "_an"]
        ix = int(np.argmin(abs(x)))
        c = (num - an).mean()
        ax.plot(z, (an[ix] + c) * 1e3, color=CAT[0], lw=2.5, label="analytic (images)")
        ax.plot(z, num[ix] * 1e3, color=CAT[1], lw=1.2, ls="--", label="FV + MG-PCG")
        r = v[key]
        ax.set_title(f"{title}: dipole 6.25 mm deep, surface profile\nrel. RMS error {100 * r['rel_rms_err_vs_box_images']:.1f}%, "
                     f"20 mm bipolar error {100 * r['bipolar_rel_err']:.1f}%", fontsize=9)
        ax.set_xlabel("z along fibre (mm)")
        ax.set_ylabel("surface potential (mV per mA·(3 mm))")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "emgfwd_validation.png"), dpi=140)
    plt.close(fig)


def fig_rotation(res, d):
    offs = list(d["offs"])
    names = res["muscles"]
    fig, axs = plt.subplots(1, 3, figsize=(14, 3.9), gridspec_kw=dict(wspace=0.3))
    for ax, n in zip(axs[:2], ("FDS", "EIP")):
        j = names.index(n)
        for o, col in zip((0.0, 9.0, 18.0), (CAT[0], CAT[1], CAT[2])):
            k = offs.index(o)
            ax.plot(np.arange(1, 9), d["S_rot"][k][:, j], marker="o", ms=5, color=col,
                    label=f"rotated {o:+.0f} mm ({o / 18:+.1f} pitch)")
        ax.set_xlabel("channel"); ax.set_ylabel("µV RMS at 10% MVC")
        ax.set_title(f"{short(n)} signature as the band rotates")
        ax.legend(fontsize=7.5)
        ax.grid(True, axis="y")
    ax = axs[2]
    rc = res["rotation_classification"]
    for scen, ls in (("A", "-"), ("B", "--")):
        for key, lbl, col in (("train0_knn", "trained at 0 only", CAT[7]), ("train_multi_knn", "trained at \u22129, 0, +9 mm", CAT[0]),
                              ("train_interp_aug_knn", "trained at 0 + virtual-rotation aug.", CAT[2])):
            acc = [rc[f"{scen}|noise5.0|{o:+.1f}"][key] * 100 for o in offs]
            ax.plot(offs, acc, marker="o" if scen == "A" else "s", ms=4.5, color=col, ls=ls,
                    label=lbl if scen == "A" else None, lw=1.4 if scen == "A" else 1.0)
    ax.plot([], [], color=INK2, ls="-", label="A: one muscle, 3\u201315 % MVC")
    ax.plot([], [], color=INK2, ls="--", label="B: 1\u20134 % MVC + co-activation")
    ax.axhline(100 / len(res["visible"]), color=MUTED, ls=":", lw=1)
    ax.set_xlabel("band rotation at test (mm; pitch = 18 mm)")
    ax.set_ylabel("11-muscle accuracy (%)")
    ax.set_ylim(0, 102)
    ax.set_title("k-NN on log-RMS, 5 \u00b5V noise")
    ax.legend(fontsize=6.8, loc="lower center", ncol=1)
    ax.grid(True, axis="y")
    fig.savefig(os.path.join(FIG, "emgfwd_rotation.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_electrodes(res, d):
    ec = res["electrode_configs"]
    vis = res["visible"]
    fig, axs = plt.subplots(1, 3, figsize=(14.5, 3.9), gridspec_kw=dict(wspace=0.32))
    ax = axs[0]
    base = np.array([ec["disc6.5_ied20"]["max_rms"][n] for n in vis])
    xs = np.arange(len(vis))
    w = 0.2
    for j, (c, lbl, col) in enumerate((("disc2_ied20", "2 mm pin", CAT[1]), ("pins2x2_ied20", "2×2 cluster of 2 mm pins", CAT[2]),
                                      ("disc6.5_ied15", "6.5 mm, IED 15 mm", CAT[6]), ("disc6.5_ied25", "6.5 mm, IED 25 mm", CAT[3]))):
        r = np.array([ec[c]["max_rms"][n] for n in vis]) / base
        ax.bar(xs + (j - 1.5) * w, (r - 1) * 100, w * 0.9, color=col, label=lbl)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(xs, [short(n) for n in vis], rotation=45, ha="right")
    ax.set_ylabel("amplitude change vs 6.5 mm / 20 mm (%)")
    ax.set_title("Signal amplitude (best channel)")
    ax.legend(fontsize=7)
    ax = axs[1]
    for c, lbl, col in (("disc6.5_ied15", "IED 15", CAT[6]), ("disc6.5_ied20", "IED 20", CAT[0]), ("disc6.5_ied25", "IED 25", CAT[3])):
        mf = [ec[c]["mean_freq"][n] for n in vis]
        ax.plot(xs, mf, marker="o", ms=5, color=col, label=lbl, lw=1.2)
    ax.set_xticks(xs, [short(n) for n in vis], rotation=45, ha="right")
    ax.set_ylabel("mean frequency (Hz), 20–450 Hz")
    ax.set_title("Bipolar spatial filter shifts the spectrum")
    ax.legend(fontsize=7.5); ax.grid(True, axis="y")
    ax = axs[2]
    cn = res["contact_noise"]
    kinds = ["disc6.5", "pins2x2", "disc2"]
    scen = list(res["contact_rc_fit"].keys())
    for j, sc in enumerate(scen):
        tot = [cn[f"{sc} | {k}"]["thermal_pair_uv"] for k in kinds]
        mains = [cn[f"{sc} | {k}"]["mains_dm_per_10mVcm_uv"] for k in kinds]
        ax.bar(np.arange(3) + (j - 0.5) * 0.38, mains, 0.34, color=[CAT[0], CAT[1]][j], label=f"mains per 10 mV CM: {sc.split(' (')[0]}")
        ax.plot(np.arange(3) + (j - 0.5) * 0.38, tot, "D", color=INK, ms=5, label="contact thermal noise (pair)" if j == 0 else None)
    ax.axhline(1.5, color=CAT[7], ls="--", lw=1); ax.text(-0.55, 1.6, "ADS1298 1.5 µV", fontsize=7, ha="left", color=INK2)
    ax.axhline(5.0, color=MUTED, ls=":", lw=1); ax.text(-0.55, 5.4, "5 µV mains gate", fontsize=7, ha="left", color=INK2); ax.set_ylim(0.1, 2000)
    ax.set_yscale("log")
    ax.set_xticks(range(3), ["6.5 mm disc", "2×2 pins", "2 mm pin"])
    ax.set_ylabel("µV RMS")
    ax.set_title("Pad area sets impedance → noise and mains")
    ax.legend(fontsize=6.5, loc="upper left")
    fig.savefig(os.path.join(FIG, "emgfwd_electrodes.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_amplitude(res, d):
    vis = res["visible"] + ["FCR", "ECR"]
    names = res["muscles"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    xs = np.arange(len(vis))
    for j, (E, col) in enumerate(((5, CAT[2]), (10, CAT[0]), (20, CAT[6]), (40, CAT[1]))):
        S = d[f"S8_E{E}"]
        mx = [S[:, names.index(n)].max() for n in vis]
        med = [np.median(S[:, names.index(n)]) for n in vis]
        ax.plot(xs + (j - 1.5) * 0.12, mx, "o", color=col, ms=6, label=f"{E}% MVC, best channel")
        ax.plot(xs + (j - 1.5) * 0.12, med, "_", color=col, ms=9, mew=2, label=f"{E}% MVC, median channel" if j == 0 else None)
    ax.axhspan(0.01, 1.5, color="#ebe7df", zorder=0)
    ax.axhline(1.5, color=CAT[7], ls="--", lw=1)
    ax.text(len(vis) - 0.5, 1.65, "ADS1298 noise 1.5 µV (4 kSPS)", ha="right", fontsize=7.5, color=INK2)
    ax.axhline(5.0, color=MUTED, ls=":", lw=1)
    ax.text(len(vis) - 0.5, 5.5, "5 µV: on-body baseline / mains gate", ha="right", fontsize=7.5, color=INK2)
    ax.set_yscale("log"); ax.set_ylim(0.1, 2000)
    ax.set_xticks(xs, [short(n) for n in vis], rotation=30, ha="right")
    ax.set_ylabel("µV RMS, 20–450 Hz")
    ax.set_title("Expected per-channel EMG for single-muscle contractions (8-channel band)")
    ax.legend(fontsize=7, ncol=3, loc="upper right")
    ax.grid(True, axis="y", which="major")
    fig.savefig(os.path.join(FIG, "emgfwd_amplitudes.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_muaps(res, d):
    mu = dict(np.load(os.path.join(CACHE, "muaps.npz")))
    t = mu["t"] * 1e3
    show = ["FDS", "FDP", "PQ", "FCU", "EIP", "APL_EPB"]
    fig, axs = plt.subplots(2, len(show), figsize=(15, 5.6), gridspec_kw=dict(height_ratios=[1.6, 1], hspace=0.45, wspace=0.35))
    for j, n in enumerate(show):
        ax = axs[0, j]
        b = mu[n + "_med"] * 1e6
        off = max(np.abs(b).max() * 1.05, 1e-3)
        for k in range(8):
            ax.plot(t, b[k] - k * off, color=CAT[0] if k % 2 == 0 else CAT[6], lw=1.1)
        ax.set_yticks(-np.arange(8) * off, [str(k + 1) for k in range(8)])
        ax.set_xlabel("ms")
        ax.set_title(f"{short(n)}: median MU\n(spacing {off:.1f} µV)", fontsize=9)
        ax = axs[1, j]
        i = res["muscles"].index(n)
        f = d["spec_f"]
        p = d["spec"][i]
        msk = (f >= 10) & (f <= 1000)
        ax.plot(f[msk], p[msk] / p[msk].max(), color=CAT[0])
        ax.axvspan(20, 450, color="#ebe7df", zorder=0)
        ax.set_xscale("log"); ax.set_xlabel("Hz"); ax.set_yticks([0, 0.5, 1])
        ax.set_title(f"PSD, mean freq {res['mean_freq_hz'][n]:.0f} Hz", fontsize=9)
    axs[1, 0].set_ylabel("normalised PSD")
    axs[0, 0].set_ylabel("channel")
    fig.savefig(os.path.join(FIG, "emgfwd_muaps_spectra.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_coverage(res, d):
    vis = res["visible"]
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw=dict(width_ratios=[1, 1.25], wspace=0.35))
    ax = axs[0]
    C = d["cos_8ch"]
    im = ax.imshow(C, cmap=CMAP_SEQ, vmin=0, vmax=1)
    for i in range(len(vis)):
        for j in range(len(vis)):
            ax.text(j, i, "1" if C[i, j] >= 0.995 else f"{C[i, j]:.2f}"[1:], ha="center", va="center", fontsize=6.5,
                    color="white" if C[i, j] > 0.6 else INK)
    ax.set_xticks(range(len(vis)), [short(n) for n in vis], rotation=45, ha="right")
    ax.set_yticks(range(len(vis)), [short(n) for n in vis])
    ax.set_title("Similarity of 8-channel signatures (cosine)\n1 = indistinguishable pattern")
    fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    ax = axs[1]
    c = res["classification"]
    cfgs = [("rot+0.0", "8 ch\nrev C"), ("rot+9.0", "8 ch\n+\u00bd pitch"), ("rot-9.0", "8 ch\n\u2212\u00bd pitch"),
            ("16ch", "16 ch\n9 mm"), ("disc6.5_ied15", "8 ch\nIED 15"), ("disc6.5_ied25", "8 ch\nIED 25"),
            ("disc2_ied20", "8 ch\n2 mm pin"), ("pins2x2_ied20", "8 ch\n2\u00d72 pins")]
    xs = np.arange(len(cfgs))
    for j, (scen, nz, col, lbl) in enumerate((("A", "noise5.0", CAT[2], "A: one muscle 3\u201315 % MVC, 5 \u00b5V"),
                                               ("B", "noise1.5", CAT[0], "B: 1\u20134 % MVC + co-activation, 1.5 \u00b5V"),
                                               ("B", "noise5.0", CAT[6], "B: same, 5 \u00b5V"))):
        acc = [max(c[f"{scen}|{k}|{nz}|visible11"]["acc"], c[f"{scen}|{k}|{nz}|visible11"]["acc_knn"]) * 100 for k, _ in cfgs]
        ax.bar(xs + (j - 1) * 0.27, acc, 0.25, color=col, label=lbl)
    ax.set_xticks(xs, [l for _, l in cfgs], fontsize=7.5)
    ax.set_ylabel("11-muscle accuracy (%), best of LDA / k-NN")
    ax.set_ylim(0, 122)
    ax.set_yticks(range(0, 101, 20))
    ax.axhline(100 / 11, color=MUTED, ls=":", lw=1)
    ax.legend(fontsize=6.8, loc="upper center", ncol=3, columnspacing=0.8, handlelength=1.2)
    ax.grid(True, axis="y")
    ax.set_title("Can the channels tell single muscles apart?")
    fig.savefig(os.path.join(FIG, "emgfwd_coverage.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    from study import Study
    res, d = load()
    what = sys.argv[1:] or ["sens", "rot", "cov", "elec", "amp", "muap", "val", "anat", "skin"]
    if "sens" in what: fig_sensitivity(res, d)
    if "rot" in what: fig_rotation(res, d)
    if "cov" in what: fig_coverage(res, d)
    if "elec" in what: fig_electrodes(res, d)
    if "amp" in what: fig_amplitude(res, d)
    if "muap" in what: fig_muaps(res, d)
    if "val" in what and os.path.exists(os.path.join(CACHE, "validation.json")): fig_validation()
    if "anat" in what or "skin" in what:
        st = Study()
        st.all_mono()
        if "anat" in what: fig_anatomy(st, res)
        if "skin" in what:
            info = fig_skinmap(st, res)
            with open(os.path.join(CACHE, "skinmap.json"), "w") as f:
                json.dump(info, f)
            print(info)
