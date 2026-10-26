"""Q2: mains common-mode -> differential conversion on CH1 with P/N electrode and trace mismatch.

Full circuit (afe.py) driven by a mains source through capacitive coupling to the body; reports the
differential voltage at the PGA inputs of CH1 (after the 4.7k and the internal EMI filter).
"""
import csv
import itertools
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import afe

# environment: name, cm (mains->body), cb (body->earth), cge (device->earth), cmd (mains->device)
ENV = {
    "battery_typ": dict(cm=2e-12, cb=200e-12, cge=10e-12, cmd=0.0),
    "battery_adv": dict(cm=3e-12, cb=100e-12, cge=30e-12, cmd=0.2e-12),
    "grounded": dict(cm=2e-12, cb=200e-12, cge=1e-6, cmd=0.0),        # bench phantom / USB-scope ground
    "grounded_adv": dict(cm=3e-12, cb=100e-12, cge=1e-6, cmd=0.0),
}
ELEC = [(100e3, 15e-9), (330e3, 4.7e-9), (1e6, 4.7e-9), (3.3e6, 1e-9)]   # per pad R || C
MISMATCH = [0.1, 0.3, 0.5]
DCTR = [0.0, 5e-12]
RLD = [("off", dict(mode="off")), ("passive", dict(nsense=0)),
       ("N2_4.7n", dict(nsense=2, cf=4.7e-9)), ("N8_4.7n", dict(nsense=8, cf=4.7e-9)),
       ("N16_4.7n", dict(nsense=16, cf=4.7e-9)), ("N16_10n", dict(nsense=16, cf=10e-9))]
MAINS = [(230.0, 50.0), (120.0, 60.0)]


def case(args):
    env, (re, ce), d, dctr, (rname, rkw) = args
    ctr = 15e-12
    line = {0: dict(re=re, ce=ce, ctr=ctr), 1: dict(re=re * (1 + d), ce=ce / (1 + d), ctr=ctr + dctr)}
    p = afe.default_params(re=re, ce=ce, ctr=ctr, vm=1.0, line=line, **ENV[env], **rkw)
    r = afe.simulate(p, "ac lin 11 50 60", ("v(body)", "v(in0)", "v(in1)", "v(drv)"))
    out = []
    for i, (vm, fm) in zip((0, -1), MAINS):
        vd = abs(r["v(in0)"][i] - r["v(in1)"][i]) * vm
        vcm = abs(0.5 * (r["v(in0)"][i] + r["v(in1)"][i])) * vm
        out.append(dict(env=env, re=re, ce_nF=ce * 1e9, mismatch=d, dctr_pF=dctr * 1e12, rld=rname,
                        mains=f"{vm:.0f}V/{fm:.0f}Hz", vcm_mV=vcm * 1e3, vdiff_uV=vd * 1e6,
                        conv_dB=20 * np.log10(vd / vcm), vrld_mV=abs(r["v(drv)"][i]) * vm * 1e3))
    return out


def review_check():
    """Reproduce the review's formula Vi/Vbody = 1/[1+(Zi+4.7k)(1/Rin+jwCi)] at 60 Hz, 100k/200k, 50 pF."""
    w = 2 * np.pi * 60
    h = [1 / (1 + (z + 4.7e3) * (1 / 1e9 + 1j * w * 50e-12)) for z in (100e3, 200e3)]
    return abs(h[0] - h[1])


def main():
    grid = list(itertools.product(ENV, ELEC, MISMATCH, DCTR, RLD))
    res = [row for rows in afe.pmap(case, grid) for row in rows]
    with open(os.path.join(afe.OUT, "q2_cm_dm.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0]))
        w.writeheader()
        w.writerows(res)
    print(f"{len(res)} rows")
    k = review_check()
    print(f"review check: conversion {k:.5f} ({20*np.log10(k):.1f} dB) -> {k*10e-3*1e6:.1f} uV per 10 mV CM")

    def get(**c):
        return [r for r in res if all(r[a] == b for a, b in c.items())]

    # Table A: CM level (mV rms) at the inputs vs RLD mode and environment (1 Mohm||4.7nF, 30 % mismatch)
    print("\nCM at inputs (mV rms), R=1M||4.7nF/pad, 230V/50Hz | 120V/60Hz")
    for env in ENV:
        s = []
        for rname, _ in RLD:
            a = get(env=env, re=1e6, mismatch=0.3, dctr_pF=0.0, rld=rname)
            s.append(f"{rname}: {a[0]['vcm_mV']:.3g}|{a[1]['vcm_mV']:.3g}")
        print(env, "  ".join(s))
    # Table B: differential residual (uV rms) at 230V/50 Hz
    print("\nDifferential residual uVrms, 230V/50Hz, dCtr=5pF")
    for env in ENV:
        for (re, ce) in ELEC:
            for d in MISMATCH:
                s = []
                for rname, _ in RLD:
                    a = get(env=env, re=re, mismatch=d, dctr_pF=5.0, rld=rname)[0]
                    s.append(f"{a['vdiff_uV']:.3g}")
                print(f"{env:13s} R={re:8.3g} Ce={ce*1e9:4.1f}n d={d:.0%}: " + " / ".join(s))
    # max RLD output amplitude
    print("max RLD output amplitude mV rms:", max(r["vrld_mV"] for r in res if r["rld"] not in ("off",)))

    # Plot: residual vs RLD mode for each environment, 30 % mismatch, 5 pF trace mismatch
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3), sharey=True)
    names = [n for n, _ in RLD]
    for k, mains in enumerate(["230V/50Hz", "120V/60Hz"]):
        for env, c in zip(ENV, ["C0", "C1", "C2", "C3"]):
            for (re, ce), ls in zip(ELEC, ["-", "--", "-.", ":"]):
                y = [get(env=env, re=re, mismatch=0.3, dctr_pF=5.0, rld=n)[k]["vdiff_uV"] for n in names]
                ax[k].semilogy(range(len(names)), y, ls, color=c, marker="o", ms=3,
                               label=f"{env}, {re/1e3:g}k||{ce*1e9:g}nF" if k == 0 else None)
        ax[k].axhline(5, color="k", lw=1)
        ax[k].text(0, 5.5, "5 uVrms goal", fontsize=8)
        ax[k].set_xticks(range(len(names)), names, fontsize=8)
        ax[k].set_title(f"CH1 differential mains residual, {mains}, P/N mismatch 30 %, dCtrace 5 pF", fontsize=9)
        ax[k].grid(True, which="both", alpha=0.3)
    ax[0].set_ylabel("uV rms at ADS input")
    ax[0].legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(afe.OUT, "q2_mains_residual.png"), dpi=130)


if __name__ == "__main__":
    main()
