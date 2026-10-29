"""Input-network options for rev C: series R (4.7/10/22 kOhm), C0G common-mode caps to AVSS and a
differential cap at the ADS pins, an RF/ESD shunt on BIAS_E, and low-capacitance TVS arrays.

Reuses sim/afe.py (same ngspice model as q1-q4) and adds the extra elements to its netlist:
  Cx{k}  pin{k}-0       CM cap after the series R (tolerance applied with opposite sign on P and N)
  Cd{c}  pin{2c}-pin{2c+1}  differential cap
  Cbx    bias_e-0       extra shunt on BIAS_E (at J1)
  Ctvs{k} e{k}-0        TVS capacitance at the J1 side (P/N mismatch applied)
Outputs: out/q5_loop.csv, out/q5_cmdm.csv, out/q5_noise_droop.csv; printed summary.
"""
import csv
import itertools
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import afe  # noqa: E402

K = 1.380649e-23
T = 300.0


def build(p, rser=4.7e3, ccm=0.0, ccm_tol=0.0, cdiff=0.0, cbias=0.0, ctvs=0.0, ctvs_mis=0.0,
          analysis="ac dec 40 1 1e6", probes=("v(drv)", "v(rldout)", "v(in0)", "v(in1)", "v(body)")):
    old = afe.BOARD["rser"]
    afe.BOARD["rser"] = rser
    try:
        net, pr, an = afe.netlist(p, analysis, probes)
    finally:
        afe.BOARD["rser"] = old
    extra = []
    for k in range(afe.BOARD["n_lines"]):
        if ccm > 0:
            sgn = 1 if k % 2 == 0 else -1
            extra.append(f"Cx{k} pin{k} 0 {ccm * (1 + sgn * ccm_tol)}")
        if ctvs > 0:
            sgn = 1 if k % 2 == 0 else -1
            extra.append(f"Ctvs{k} e{k} 0 {ctvs + sgn * ctvs_mis / 2}")
    if cdiff > 0:
        for c in range(afe.BOARD["n_lines"] // 2):
            extra.append(f"Cd{c} pin{2 * c} pin{2 * c + 1} {cdiff}")
    if cbias > 0:
        extra.append(f"Cbx bias_e 0 {cbias}")
    return net + "\n".join(extra) + "\n", list(pr), an


def loop_case(args):
    rser, ccm, cbias, (re, ce), (env, cb, cge), ctr = args
    p = afe.default_params(mode="broken", cf=4.7e-9, nsense=8, re=re, ce=ce, ctr=ctr, cb=cb, cge=cge)
    r = afe.run(*build(p, rser=rser, ccm=ccm, cbias=cbias, probes=("v(drv)", "v(rldout)")))
    Tl = -r["v(rldout)"] / r["v(drv)"]
    fc, pm, gm, ms = afe.margins(r["f"], Tl)
    return dict(rser=rser, ccm_pF=ccm * 1e12, cbias_pF=cbias * 1e12, re=re, ce_nF=ce * 1e9, env=env,
                ctr_pF=ctr * 1e12, fc_Hz=round(fc, 1), pm_deg=round(pm, 1), ms_dB=round(ms, 2),
                sup50_dB=round(20 * np.log10(abs(1 + afe.at(r["f"], Tl, 50))), 2))


ENV_CM = {"battery_typ": dict(cm=2e-12, cb=200e-12, cge=10e-12, cmd=0.0),
          "battery_adv": dict(cm=3e-12, cb=100e-12, cge=30e-12, cmd=0.2e-12),
          "grounded": dict(cm=2e-12, cb=200e-12, cge=1e-6, cmd=0.0)}


def cmdm_case(args):
    env, (re, ce), (name, kw) = args
    d = 0.3
    ctr = 25e-12          # flex pad-to-hatch (~15-18 pF) + traces + board, per line (this review)
    dctr = 2e-12          # P/N mismatch estimate (flex P traces ~20 mm longer, board up to 1.4 pF)
    line = {0: dict(re=re, ce=ce, ctr=ctr), 1: dict(re=re * (1 + d), ce=ce / (1 + d), ctr=ctr + dctr)}
    p = afe.default_params(re=re, ce=ce, ctr=ctr, vm=1.0, line=line, nsense=8, cf=4.7e-9, **ENV_CM[env])
    r = afe.run(*build(p, analysis="ac lin 1 50 50", probes=("v(in0)", "v(in1)"), **kw))
    vd = abs(r["v(in0)"][0] - r["v(in1)"][0]) * 230
    vcm = abs(0.5 * (r["v(in0)"][0] + r["v(in1)"][0])) * 230
    return dict(env=env, re=re, ce_nF=ce * 1e9, option=name, vcm_mV=round(vcm * 1e3, 4),
                vdiff_uV=round(vd * 1e6, 4), conv_dB=round(20 * np.log10(vd / vcm), 2))


def zs(f, R, C):
    return R / (1 + 2j * np.pi * f * R * C)


def noise_droop(rser, ccm, cdiff, R, C, ileak=0.0):
    """Thermal noise (electrode real parts + 2 rser) and TVS leakage shot noise over 20-850 Hz,
    brick wall, plus DM droop at 850 Hz with the given caps (ADS 20 pF/line). Returns uVrms, dB."""
    f = np.linspace(20, 850, 4000)
    z = zs(f, R, C)
    v2 = 4 * K * T * (2 * z.real + 2 * rser)
    i2 = 2 * 1.602e-19 * ileak * np.abs(z + rser) ** 2 * 2   # two lines, uncorrelated
    vn = math.sqrt(np.trapezoid(v2, f)) * 1e6
    vi = math.sqrt(np.trapezoid(i2, f)) * 1e6
    w = 2 * np.pi * 850
    zsrc = zs(850, R, C) + rser
    cin = 20e-12 + ccm
    # DM: each side source zsrc into (cin) to ground, plus cdiff across: differential load = 2/(jw(cin+2cdiff))
    h = 1 / (1 + 1j * w * zsrc * (cin + 2 * cdiff))
    return vn, vi, 20 * np.log10(abs(h))


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    # ---------------- 1. RLD loop margin with the options
    grid = list(itertools.product([4.7e3, 10e3, 22e3], [0.0, 10e-12, 22e-12], [0.0, 100e-12, 220e-12, 470e-12, 1e-9],
                                  [(100e3, 15e-9), (330e3, 4.7e-9), (1e6, 10e-9), (3.3e6, 1e-9)],
                                  [("bench300", 300e-12, 1e-6), ("battery", 200e-12, 10e-12),
                                   ("bench1n", 1e-9, 1e-6)], [20e-12]))
    rows = afe.pmap(loop_case, grid)
    with open(os.path.join(HERE, "out", "q5_loop.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("RLD loop, N=8, Cf=4.7 nF: worst PM over pads x env (bench300/battery | bench 1 nF stress)")
    for rser in (4.7e3, 10e3, 22e3):
        for ccm in (0.0, 10e-12, 22e-12):
            s = []
            for cb in (0.0, 100e-12, 220e-12, 470e-12, 1e-9):
                sel = [r for r in rows if r["rser"] == rser and r["ccm_pF"] == ccm * 1e12 and r["cbias_pF"] == cb * 1e12]
                nom = min(r["pm_deg"] for r in sel if r["env"] != "bench1n")
                st = min(r["pm_deg"] for r in sel if r["env"] == "bench1n")
                s.append(f"Cbias {cb * 1e12:5.0f}p: {nom:5.1f}/{st:5.1f}")
            print(f"  Rs {rser / 1e3:4.1f}k Ccm {ccm * 1e12:3.0f}p  " + " | ".join(s))
    # ---------------- 2. CM -> DM at 50 Hz with the options
    opts = [("baseline 4.7k", dict()),
            ("Ccm 10p 5% (opposite)", dict(ccm=10e-12, ccm_tol=0.05)),
            ("Ccm 10p 0.25pF (2.5%)", dict(ccm=10e-12, ccm_tol=0.025)),
            ("Ccm 22p 5%", dict(ccm=22e-12, ccm_tol=0.05)),
            ("Ccm 47p 5%", dict(ccm=47e-12, ccm_tol=0.05)),
            ("Cdiff 47p", dict(cdiff=47e-12)),
            ("Rs 10k", dict(rser=10e3)),
            ("Rs 22k", dict(rser=22e3)),
            ("Rs 10k + Ccm 10p 5%", dict(rser=10e3, ccm=10e-12, ccm_tol=0.05)),
            ("Cbias 100p", dict(cbias=100e-12)),
            ("TVS 0.5pF, 0.07pF mis", dict(ctvs=0.5e-12, ctvs_mis=0.07e-12)),
            ("TVS 1.0pF, 0.1pF mis", dict(ctvs=1.0e-12, ctvs_mis=0.1e-12))]
    grid2 = list(itertools.product(ENV_CM, [(330e3, 10e-9), (1e6, 10e-9), (1e6, 1e-9), (3.3e6, 1e-9)], opts))
    rows2 = afe.pmap(cmdm_case, grid2)
    with open(os.path.join(HERE, "out", "q5_cmdm.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows2[0].keys()))
        w.writeheader()
        w.writerows(rows2)
    print("\nCM->DM at 230 V/50 Hz, CH1 30 % pad mismatch + 2 pF line mismatch, 25 pF/line, N8/4.7 nF (uVrms)")
    for env in ENV_CM:
        for (re, ce) in [(1e6, 10e-9), (3.3e6, 1e-9)]:
            s = []
            for name, _ in opts:
                r = next(x for x in rows2 if x["env"] == env and x["re"] == re and x["ce_nF"] == ce * 1e9 and x["option"] == name)
                s.append(f"{name}: {r['vdiff_uV']:.3f}")
            print(f"  {env:12s} {re / 1e3:6.0f}k||{ce * 1e9:g}n  " + "; ".join(s))
    # ---------------- 3. noise and droop
    rows3 = []
    for rser, ccm, cdiff in [(4.7e3, 0, 0), (10e3, 0, 0), (22e3, 0, 0), (4.7e3, 10e-12, 0), (10e3, 10e-12, 0),
                             (22e3, 22e-12, 0), (4.7e3, 0, 47e-12), (22e3, 0, 47e-12)]:
        for R, C in [(100e3, 10e-9), (1e6, 10e-9), (1e6, 1e-9)]:
            for il in (0.0, 0.1e-9, 1e-9, 10e-9):
                vn, vi, dr = noise_droop(rser, ccm, cdiff, R, C, il)
                rows3.append(dict(rser=rser, ccm_pF=ccm * 1e12, cdiff_pF=cdiff * 1e12, re=R, ce_nF=C * 1e9,
                                  ileak_nA=il * 1e9, thermal_uV=round(vn, 3), shot_uV=round(vi, 3),
                                  droop850_dB=round(dr, 3)))
    with open(os.path.join(HERE, "out", "q5_noise_droop.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows3[0].keys()))
        w.writeheader()
        w.writerows(rows3)
    print("\nThermal noise 20-850 Hz (2 contacts + 2 Rs), uVrms; ADS alone 1.21 uVrms at 4 kSPS (signal_chain.md)")
    for r in rows3:
        if r["ileak_nA"] == 0:
            tot = math.sqrt(r["thermal_uV"] ** 2 + 1.21 ** 2)
            print(f"  Rs {r['rser'] / 1e3:4.1f}k Ccm {r['ccm_pF']:4.0f}p Cd {r['cdiff_pF']:3.0f}p  {r['re'] / 1e3:5.0f}k||{r['ce_nF']:g}n:"
                  f" thermal {r['thermal_uV']:.3f}, total with ADS {tot:.3f}, droop@850 {r['droop850_dB']:.3f} dB")
    print("\nTVS leakage shot noise (two lines), uVrms, Rs 4.7k")
    for r in rows3:
        if r["rser"] == 4.7e3 and r["ccm_pF"] == 0 and r["cdiff_pF"] == 0 and r["ileak_nA"] > 0:
            print(f"  {r['re'] / 1e3:5.0f}k||{r['ce_nF']:g}n  I_leak {r['ileak_nA']:5.1f} nA: {r['shot_uV']:.3f} uVrms;"
                  f" DC offset per 1 nA mismatch through the contact: {r['ileak_nA'] * 1e-9 * r['re'] * 1e3:.2f} mV")
    # ---------------- 4. ESD peak current into an ADS input pin (IEC 61000-4-2 contact: 150 pF / 330 ohm)
    print("\nESD into a pad of the floating band (IEC contact, 150 pF/330 ohm source; pad-hatch 17 pF absorbs the first ns)")
    for v in (2e3, 4e3, 8e3):
        for rs in (4.7e3, 10e3, 22e3):
            print(f"  {v / 1e3:.0f} kV, Rs {rs / 1e3:4.1f}k: I_pk into pin <= {v / (rs + 330):.2f} A "
                  f"(HBM 2 kV rating = 1.33 A pk); charge <= {150e-12 * v * 1e9:.0f} nC")
        print(f"  {v / 1e3:.0f} kV into a BIAS pad -> RLDIN with no series R: I_pk <= {v / 330:.1f} A")


if __name__ == "__main__":
    main()
