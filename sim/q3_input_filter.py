"""Q3: input filtering of one channel: in-band droop (850 Hz) and RF / modulator-band attenuation.

Path per line (gen_c_sch.py + ADS1298 Fig. 24): electrode R||C -> flex trace C -> 4.7k (RN array) ->
PCB pad -> package lead/bond L -> die pin C (ESD/mux) -> 5k + 10 pF EMI filter -> PGA input (1 GOhm).
Parasitics are bracketed (low/high); above ~500 MHz results are order-of-magnitude, layout-dependent.
Optional reserved RF caps at the ADS side of the 4.7k: differential (P-N) and/or common-mode (each to GND).
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import afe

PAR = {"low": dict(cpar_r=0.03e-12, esl_r=0.4e-9, cpad=0.2e-12, lpkg=2e-9, cpar_emi=0.01e-12),
       "high": dict(cpar_r=0.1e-12, esl_r=0.8e-9, cpad=0.5e-12, lpkg=5e-9, cpar_emi=0.05e-12)}
CAP_ESL, CAP_ESR = 0.4e-9, 0.1   # 0402 C0G


def net(par, cdiff=0.0, ccm=0.0, re=1e6, ce=4.7e-9, ctr=15e-12, src="dm", rsrc=None):
    """src: 'dm'/'cm' body-side electrode drive (in-band), or 'rf_dm'/'rf_cm' 50-ohm source at connector."""
    q = PAR[par]
    L = ["* one channel input path"]
    for k, sgn in ((0, 1), (1, -1)):
        s = sgn if src.endswith("dm") else 1
        if src.startswith("rf"):
            L.append(f"V{k} s{k} 0 AC {0.5 * s}")
            L.append(f"Rsrc{k} s{k} e{k} {rsrc or 50}")
        else:
            L.append(f"V{k} s{k} 0 AC {0.5 * s}")
            L.append(f"Re{k} s{k} e{k} {re}")
            L.append(f"Ce{k} s{k} e{k} {ce}")
            L.append(f"Ctr{k} e{k} 0 {ctr}")
        L.append(f"Rs{k} e{k} m{k} 4.7k")
        L.append(f"Ls{k} m{k} pcb{k} {q['esl_r']}")
        L.append(f"Cps{k} e{k} pcb{k} {q['cpar_r']}")
        L.append(f"Cpad{k} pcb{k} 0 {q['cpad']}")
        L.append(f"Lp{k} pcb{k} die{k} {q['lpkg']}")
        L.append(f"Cdie{k} die{k} 0 {afe.DS['c_pin']}")
        L.append(f"Remi{k} die{k} in{k} {afe.DS['r_emi']}")
        L.append(f"Cpe{k} die{k} in{k} {q['cpar_emi']}")
        L.append(f"Cemi{k} in{k} 0 {afe.DS['c_emi']}")
        L.append(f"Rin{k} in{k} 0 1G")
        if ccm:
            L.append(f"Ccm{k} pcb{k} c{k} {ccm}")
            L.append(f"Lcm{k} c{k} d{k} {CAP_ESL}")
            L.append(f"Rcm{k} d{k} 0 {CAP_ESR}")
    if cdiff:
        L.append(f"Cd pcb0 x1 {cdiff}")
        L.append(f"Ld x1 x2 {CAP_ESL}")
        L.append(f"Rd x2 pcb1 {CAP_ESR}")
    return "\n".join(L) + "\n"


def tf(netl, analysis="ac dec 50 1 6e9", node="in"):
    r = afe.run(netl, [f"v({node}0)", f"v({node}1)"], analysis)
    a, b = r[f"v({node}0)"], r[f"v({node}1)"]
    return r["f"], a - b, 0.5 * (a + b)


def sinc3(f, fdr, fmod=512e3):
    n = fmod / fdr
    x = np.pi * f / fmod
    with np.errstate(divide="ignore", invalid="ignore"):
        h = np.abs(np.sin(n * x) / (n * np.sin(x))) ** 3
    return np.where(f == 0, 1.0, h)


def db(x):
    return 20 * np.log10(np.abs(x))


def main():
    rows = []
    FQ = {"850 Hz": 850, "512 kHz (fMOD)": 512e3, "2.048 MHz (fCLK=4 fMOD)": 2.048e6, "2.4 GHz (BLE)": 2.44e9}
    opts = [("none", 0, 0), ("Cdiff 10p", 10e-12, 0), ("Cdiff 47p", 47e-12, 0), ("Cdiff 100p", 100e-12, 0),
            ("Ccm 10p", 0, 10e-12), ("Ccm 10p + Cdiff 100p", 100e-12, 10e-12)]
    print("RF attenuation (dB), 50-ohm source at the flex connector -> PGA input; DM | CM ; parasitics low/high")
    for name, cd, cc in opts:
        for par in PAR:
            out = dict(option=name, parasitics=par)
            for mode in ("rf_dm", "rf_cm"):
                for node, tag in (("in", ""), ("die", " @die pin"), ("pcb", " @pcb pad")):
                    f, d, c = tf(net(par, cd, cc, src=mode), node=node)
                    y = d if mode == "rf_dm" else c
                    for lab, f0 in FQ.items():
                        if f0 > 1e3 and (node == "in" or f0 > 1e9):
                            out[f"{mode} {lab}{tag}"] = db(afe.at(f, y, f0) / 1.0)
            rows.append(out)
            print(name, par, {k: round(v, 1) for k, v in out.items() if k.startswith("rf")})

    # In-band droop (DM, body-side source) vs electrode and option; includes ADS sinc3 at 4 kSPS
    print("\nIn-band DM droop at 450 / 850 Hz (dB), analog front end only (sinc3 4kSPS adds -0.54/-1.96 dB)")
    ELEC = [(100e3, 15e-9), (1e6, 4.7e-9), (1e6, 1e-9), (10e6, 1e-9)]
    droop = []
    for name, cd, cc in opts:
        s = []
        for re, ce in ELEC:
            f, d, _ = tf(net("low", cd, cc, re=re, ce=ce, ctr=20e-12, src="dm"), "ac dec 50 1 1e5")
            g10 = afe.at(f, d, 20)
            v = [db(afe.at(f, d, x) / g10) for x in (450, 850)]
            s.append(f"{re/1e3:g}k||{ce*1e9:g}n: {v[0]:.2f}/{v[1]:.2f}")
            droop.append(dict(option=name, re=re, ce_nF=ce * 1e9, droop450_dB=v[0], droop850_dB=v[1]))
        print(f"{name:22s}", " | ".join(s))
    for fdr in (2e3, 4e3):
        print(f"sinc3 at {fdr/1e3:g} kSPS: 450 Hz {db(sinc3(np.array([450.0]), fdr))[0]:.2f} dB, "
              f"850 Hz {db(sinc3(np.array([850.0]), fdr))[0]:.2f} dB")
    # Extra CM->DM conversion from CM caps (tolerance mismatch) at 50 Hz: compare Cin with/without 10 pF +-5 %
    w = 2 * np.pi * 50
    for cc in (0.0, 10e-12, 22e-12):
        zp, zn = 1e6 / (1 + 1j * w * 1e6 * 4.7e-9), 1.3e6 / (1 + 1j * w * 1.3e6 * 4.7e-9 / 1.3)
        cin = 15e-12 + 20e-12 + cc
        h = lambda z, c: 1 / (1 + (z + 4.7e3) * (1e-9 + 1j * w * c))
        k = abs(h(zp, cin + 0.05 * cc) - h(zn, cin - 0.05 * cc))
        print(f"Ccm {cc*1e12:g} pF (+-5 %): CM->DM conversion at 50 Hz {20*np.log10(k):.1f} dB (1M||4.7n, 30 % mismatch)")

    with open(os.path.join(afe.OUT, "q3_rf_attenuation.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    with open(os.path.join(afe.OUT, "q3_inband_droop.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(droop[0]))
        wr.writeheader()
        wr.writerows(droop)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    for name, cd, cc in opts:
        for par, ls in (("low", "-"), ("high", "--")):
            f, d, c = tf(net(par, cd, cc, src="rf_dm"))
            ax[0].semilogx(f, db(d), ls, label=f"{name} ({par} parasitics)" if True else None)
            f, d, c = tf(net(par, cd, cc, src="rf_cm"))
            ax[1].semilogx(f, db(c), ls)
    for a, t in zip(ax, ("Differential RF: connector (50 ohm) -> PGA input", "Common-mode RF: connector -> PGA input")):
        for x in (512e3, 2.048e6, 2.44e9):
            a.axvline(x, color="grey", lw=0.6)
        a.set_title(t, fontsize=9)
        a.set_xlabel("Hz")
        a.set_ylim(-110, 5)
        a.set_xlim(1e3, 6e9)
        a.grid(True, which="both", alpha=0.3)
    ax[0].set_ylabel("dB")
    ax[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(afe.OUT, "q3_input_filter.png"), dpi=130)


if __name__ == "__main__":
    main()
