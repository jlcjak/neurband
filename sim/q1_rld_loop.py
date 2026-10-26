"""Q1: RLD (bias) loop stability and 50/60 Hz common-mode suppression, swept.

Loop gain T = -v(rldout)/v(drv) with the loop broken between the RLD amplifier output and the
100 kOhm series resistor (amp output impedance << 100 kOhm, so the break is clean).
"""
import csv
import itertools
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import afe

CF = [1.5e-9, 2.2e-9, 4.7e-9, 10e-9]
NS = [2, 4, 8, 16]
RE = [100e3, 330e3, 1e6, 3.3e6, 10e6]
CE = [1e-9, 4.7e-9, 15e-9, 50e-9]
CTR = [10e-12, 20e-12]
# environments: (name, cb, cge). "bench" = device GND tied to earth (USB/scope/phantom) -> body C loads the loop
ENV = [("bench100", 100e-12, 1e-6), ("bench300", 300e-12, 1e-6), ("battery", 200e-12, 10e-12),
       ("stress1n", 1e-9, 1e-6)]
GBW = [100e3, 50e3]
BIASPADS = [8, 1]   # bias pads in contact


def case(args):
    cf, ns, re, ce, ctr, (env, cb, cge), gbw, nbp = args
    p = afe.default_params(mode="broken", cf=cf, nsense=ns, re=re, ce=ce, ctr=ctr, cb=cb, cge=cge, gbw=gbw,
                           re_bias=re * 8 / nbp, ce_bias=ce * nbp / 8)
    r = afe.simulate(p, "ac dec 40 1 1e6", ("v(drv)", "v(rldout)"))
    T = -r["v(rldout)"] / r["v(drv)"]
    fc, pm, gm, ms = afe.margins(r["f"], T)
    t50, t60 = afe.at(r["f"], T, 50), afe.at(r["f"], T, 60)
    return dict(cf_nF=cf * 1e9, nsense=ns, re=re, ce_nF=ce * 1e9, ctr_pF=ctr * 1e12, env=env, gbw=gbw, bias_pads=nbp,
                fc_Hz=fc, pm_deg=pm, gm_dB=gm, ms_dB=ms,
                sup50_dB=20 * np.log10(abs(1 + t50)), sup60_dB=20 * np.log10(abs(1 + t60)))


def main():
    grid = list(itertools.product(CF, NS, RE, CE, CTR, ENV, GBW, BIASPADS))
    res = afe.pmap(case, grid)
    path = os.path.join(afe.OUT, "q1_loop_sweep.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0]))
        w.writeheader()
        w.writerows(res)
    print(f"{len(res)} cases -> {path}")

    def sel(**c):
        return [r for r in res if all((r[k] in v) if isinstance(v, (list, tuple, set)) else r[k] == v
                                      for k, v in c.items())]

    def pm_of(rows):
        return np.array([r["pm_deg"] for r in rows], float)

    # Summary per (Cf, N)
    print("\nCf nF | N  | 50Hz suppression dB | fc Hz (range) | PM min: nominal grid / battery / +GBW50k,1 bias pad / 1nF stress"
          " | Ms max dB nominal")
    summary = []
    for cf, ns in itertools.product(CF, NS):
        base = dict(cf_nF=cf * 1e9, nsense=ns)
        nom = sel(**base, env=["bench100", "bench300", "battery"], gbw=100e3, bias_pads=8)
        bat = sel(**base, env="battery", gbw=100e3, bias_pads=8)
        deg = sel(**base, env=["bench100", "bench300", "battery"])
        st = sel(**base, env="stress1n", gbw=100e3, bias_pads=8)
        sup = np.array([r["sup50_dB"] for r in nom])
        fcs = np.array([r["fc_Hz"] for r in nom])
        row = dict(cf_nF=cf * 1e9, nsense=ns, sup50_min=sup.min(), sup50_max=sup.max(),
                   fc_min=np.nanmin(fcs), fc_max=np.nanmax(fcs),
                   pm_nom=np.nanmin(pm_of(nom)), pm_bat=np.nanmin(pm_of(bat)), pm_deg=np.nanmin(pm_of(deg)),
                   pm_stress=np.nanmin(pm_of(st)), ms_nom=max(r["ms_dB"] for r in nom),
                   frac_lt45=np.mean(pm_of(nom) < 45))
        summary.append(row)
        print(f"{row['cf_nF']:5.1f} | {ns:2d} | {row['sup50_min']:5.1f}-{row['sup50_max']:5.1f} | "
              f"{row['fc_min']:6.0f}-{row['fc_max']:6.0f} | {row['pm_nom']:6.1f} / {row['pm_bat']:6.1f} / "
              f"{row['pm_deg']:6.1f} / {row['pm_stress']:6.1f} | {row['ms_nom']:5.1f} | <45deg: {row['frac_lt45']:.0%}")
    with open(os.path.join(afe.OUT, "q1_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)

    # Which electrode/env combination is the worst case for the recommended configs?
    for cf, ns in [(4.7e-9, 2), (4.7e-9, 4), (4.7e-9, 8), (10e-9, 8), (4.7e-9, 16), (10e-9, 16), (2.2e-9, 4)]:
        rows = sel(cf_nF=cf * 1e9, nsense=ns, env=["bench100", "bench300", "battery"], gbw=100e3, bias_pads=8)
        w = min(rows, key=lambda r: r["pm_deg"])
        print(f"worst nominal Cf={cf*1e9}nF N={ns}: PM={w['pm_deg']:.1f} at R={w['re']:.3g} C={w['ce_nF']}nF "
              f"Ctr={w['ctr_pF']}pF {w['env']} fc={w['fc_Hz']:.0f}")

    # ---- plots ----
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for k, (key, title) in enumerate([("pm_nom", "Worst-case phase margin, nominal grid (deg)"),
                                       ("sup50_min", "Min. 50 Hz CM suppression |1+T| (dB)")]):
        M = np.array([[next(s[key] for s in summary if s["cf_nF"] == cf * 1e9 and s["nsense"] == ns) for ns in NS]
                      for cf in CF])
        im = ax[k].imshow(M, cmap="RdYlGn", origin="lower", vmin=(-30 if k == 0 else 0), vmax=(90 if k == 0 else 40))
        ax[k].set_xticks(range(len(NS)), [str(n) for n in NS])
        ax[k].set_yticks(range(len(CF)), [f"{c*1e9:g}" for c in CF])
        ax[k].set_xlabel("RLD_SENS inputs")
        ax[k].set_ylabel("Cf (nF), Rf = 1 MOhm")
        ax[k].set_title(title, fontsize=10)
        for i in range(len(CF)):
            for j in range(len(NS)):
                ax[k].text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=10)
        fig.colorbar(im, ax=ax[k], shrink=0.8)
    fig.tight_layout()
    fig.savefig(os.path.join(afe.OUT, "q1_pm_heatmap.png"), dpi=130)

    # Bode plots at a nominal and an adverse electrode
    fig, ax = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    for col, (re, ce, lab) in enumerate([(1e6, 4.7e-9, "1 MOhm || 4.7 nF per pad"), (10e6, 1e-9, "10 MOhm || 1 nF per pad")]):
        for cf, ns, c in [(1.5e-9, 16, "C3"), (4.7e-9, 16, "C1"), (4.7e-9, 8, "C0"), (4.7e-9, 2, "C2"), (10e-9, 8, "C4")]:
            p = afe.default_params(mode="broken", cf=cf, nsense=ns, re=re, ce=ce, ctr=20e-12, cb=300e-12, cge=1e-6)
            r = afe.simulate(p, "ac dec 40 1 1e6", ("v(drv)", "v(rldout)"))
            T = -r["v(rldout)"] / r["v(drv)"]
            fc, pm, _, _ = afe.margins(r["f"], T)
            ax[0, col].semilogx(r["f"], 20 * np.log10(abs(T)), c, label=f"Cf {cf*1e9:g} nF, N={ns}: PM {pm:.0f} deg")
            ax[1, col].semilogx(r["f"], np.degrees(np.unwrap(np.angle(T))), c)
        ax[0, col].axhline(0, color="k", lw=0.6)
        ax[1, col].axhline(-180, color="k", lw=0.6)
        ax[0, col].set_title(f"Loop gain T, {lab}, bench-grounded, Cbody 300 pF", fontsize=9)
        ax[0, col].set_ylim(-40, 45)
        ax[1, col].set_ylim(-270, 10)
        ax[0, col].legend(fontsize=7)
        ax[1, col].set_xlabel("Hz")
        ax[0, col].grid(True, which="both", alpha=0.3)
        ax[1, col].grid(True, which="both", alpha=0.3)
    ax[0, 0].set_ylabel("|T| dB")
    ax[1, 0].set_ylabel("phase deg")
    ax[0, 0].set_xlim(1, 1e5)
    fig.tight_layout()
    fig.savefig(os.path.join(afe.OUT, "q1_bode.png"), dpi=130)

    # PM vs electrode R for each Ce, recommended config and the fitted all-16 config
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
    for k, (cf, ns) in enumerate([(4.7e-9, 16), (4.7e-9, 8), (4.7e-9, 4)]):
        for ce in CE:
            for env, ls in [("bench300", "-"), ("battery", ":")]:
                rows = sel(cf_nF=cf * 1e9, nsense=ns, ce_nF=ce * 1e9, ctr_pF=20, env=env, gbw=100e3, bias_pads=8)
                rows.sort(key=lambda r: r["re"])
                ax[k].semilogx([r["re"] for r in rows], [r["pm_deg"] for r in rows], ls,
                               label=f"Ce {ce*1e9:g} nF {env}")
        ax[k].axhline(45, color="k", lw=0.6)
        ax[k].set_title(f"Cf {cf*1e9:g} nF, N={ns}", fontsize=10)
        ax[k].set_xlabel("pad R (ohm)")
        ax[k].grid(True, which="both", alpha=0.3)
    ax[0].set_ylabel("phase margin (deg)")
    ax[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(afe.OUT, "q1_pm_vs_electrode.png"), dpi=130)


if __name__ == "__main__":
    main()
