"""Re-check of the RLD loop and the noise budget for the reworked board (2026-10-29).

Changes vs q1/q5: RN1-RN4 = 10 kOhm; C34 = 12 pF C0G BIAS_E -> GND at R2; RLDIN (pin 62) moved from BIAS_E to
RLD_DRV (amplifier side of R2), i.e. its ~10 pF pin capacitance leaves the bias node; BIAS_E carries the flex
bias bus, 8 pads x ~16 pF pad-to-hatch + ~10 pF bus (flex_c review) = ~140 pF, swept 20-200 pF.
Uses sim/afe.py and q5's netlist extension. Output: out/q6_loop.csv; printed summary.
"""
import csv
import itertools
import os
import sys

import threading

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import afe  # noqa: E402
import q5_input_options as q5  # noqa: E402

CF = [4.7e-9, 10e-9]
NS = [8, 16]
PADS = [(100e3, 15e-9), (330e3, 4.7e-9), (1e6, 10e-9), (1e6, 1e-9), (3.3e6, 1e-9), (10e6, 1e-9)]
ENV = [("bench100", 100e-12, 1e-6), ("bench300", 300e-12, 1e-6), ("battery", 200e-12, 10e-12),
       ("bench1n", 1e-9, 1e-6)]
GBW = [100e3, 50e3]
BIASPADS = [8, 1]
# (label, rser, C34, bias-bus C, RLDIN on bias node?)
VARIANTS = [("first review: 4.7k, no C34, bus 20 pF, RLDIN on BIAS_E", 4.7e3, 0.0, 20e-12, True),
            ("as built: 10k, C34 12 pF, bus 20 pF, RLDIN on RLD_DRV", 10e3, 12e-12, 20e-12, False),
            ("as built, realistic flex bus 140 pF", 10e3, 12e-12, 140e-12, False),
            ("as built, bus 200 pF (stress)", 10e3, 12e-12, 200e-12, False)]


LOCK = threading.Lock()


def case(args):
    (label, rser, c34, cbus, rldin_on_bias), cf, ns, (re, ce), (env, cb, cge), gbw, nbp = args
    # afe puts ctr_bias + c_rldin on the bias node; with RLDIN on RLD_DRV the pin C sits on the amplifier output
    # (100 ohm, no effect on the loop), so remove it from the bias node instead of mutating afe.DS.
    cb_node = cbus if rldin_on_bias else cbus - afe.DS["c_rldin"]
    p = afe.default_params(mode="broken", cf=cf, nsense=ns, re=re, ce=ce, ctr=25e-12, cb=cb, cge=cge, gbw=gbw,
                           re_bias=re * 8 / nbp, ce_bias=ce * nbp / 8, ctr_bias=cb_node)
    with LOCK:  # q5.build temporarily changes afe.BOARD["rser"]
        net = q5.build(p, rser=rser, cbias=c34, probes=("v(drv)", "v(rldout)"))
    r = afe.run(*net)
    T = -r["v(rldout)"] / r["v(drv)"]
    fc, pm, gm, ms = afe.margins(r["f"], T)
    return dict(variant=label, cf_nF=cf * 1e9, nsense=ns, re=re, ce_nF=ce * 1e9, env=env, gbw=gbw, bias_pads=nbp,
                fc_Hz=round(fc, 1), pm_deg=round(pm, 1), ms_dB=round(ms, 2),
                sup50_dB=round(20 * np.log10(abs(1 + afe.at(r["f"], T, 50))), 2))


def main():
    grid = list(itertools.product(VARIANTS, CF, NS, PADS, ENV, GBW, BIASPADS))
    rows = afe.pmap(case, grid)
    with open(os.path.join(HERE, "out", "q6_loop.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("Worst phase margin (deg): nominal grid (bench100/300 + battery, GBW 100k, 8 bias pads) | "
          "any GBW/bias-pad case | 1 nF body stress; 50 Hz suppression range")
    for v in VARIANTS:
        for cf in CF:
            for ns in NS:
                sel = [r for r in rows if r["variant"] == v[0] and r["cf_nF"] == cf * 1e9 and r["nsense"] == ns]
                nom = [r for r in sel if r["env"] != "bench1n" and r["gbw"] == 100e3 and r["bias_pads"] == 8]
                allc = [r for r in sel if r["env"] != "bench1n"]
                st = [r for r in sel if r["env"] == "bench1n"]
                print(f"  {v[0]:56s} Cf {cf * 1e9:4.1f} nF N{ns:2d}: {min(r['pm_deg'] for r in nom):5.1f} | "
                      f"{min(r['pm_deg'] for r in allc):5.1f} | {min(r['pm_deg'] for r in st):5.1f};  "
                      f"sup50 {min(r['sup50_dB'] for r in nom):.1f}-{max(r['sup50_dB'] for r in nom):.1f} dB")


if __name__ == "__main__":
    main()
