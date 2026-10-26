"""Q4: shared 3.3 V rail, nRF52832 radio bursts -> AVDD ripple -> input-referred error.

Transient (ngspice): LiPo (Rint) -> XC6206 behavioural LDO (output impedance R0 + (L || Rol), i.e. a loop
with unity-gain frequency fu) -> +3V3 rail caps (gen_c_sch.py) -> {10 ohm | 47 ohm | ferrite | separate LDO}
-> +3V3A caps -> ADS1298 AVDD (2.8 mA). Input-referred paths:
  (a) ADS1298 PSRR (90 dB typ at 50/60 Hz, gain 6; 80 dB conservative)
  (b) internal RLDREF = (AVDD+AVSS)/2 -> RLD loop moves the body -> CM->DM conversion (afe.py model).
"""
import csv
import itertools
import os
import subprocess
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import afe

LDO = {"nominal": dict(r0=0.2, rol=3.0, fu=30e3, psrr_db=50), "slow": dict(r0=0.3, rol=10.0, fu=5e3, psrr_db=40)}
FILT = ["10R", "47R", "ferrite", "separate LDO"]
BURST = [(5e-3, 1e-3, 7.5e-3), (10e-3, 2e-3, 7.5e-3), (10e-3, 2e-3, 30e-3), (15e-3, 3.75e-3, 7.5e-3)]
T0, T1, DT = 60e-3, 300e-3, 10e-6


def netlist(ldo, filt, burst, derated=True):
    q = LDO[ldo]
    ib, tw, tp = burst
    k = 10 ** (-q["psrr_db"] / 20)
    lz = q["rol"] / (2 * np.pi * q["fu"])
    d = (lambda c, fac: c * fac) if derated else (lambda c, fac: c)
    L = ["* supply"]
    a = L.append
    a("Vb vb0 0 3.8")
    a("Rbat vb0 vbat 0.5")
    a(f"Cvb vbat vbc {d(5.7e-6, 0.6)}")
    a("Rvb vbc 0 0.01")
    a(f"Bldo lo 0 V=3.3+{k}*(V(vbat)-3.8)")
    a("Vsns lo lo2 0")
    a("Fin vbat 0 Vsns 1")
    a(f"R0 lo2 l1 {q['r0']}")
    a(f"Lz l1 p3 {lz}")
    a(f"Rol l1 p3 {q['rol']}")
    # +3V3 caps: LDO out 1u, ADS DVDD 1u+100n, nRF 4.7u+2x100n (X5R derating at 3.3 V assumed 0.8 / 0.6)
    for i, (c, fac) in enumerate([(1e-6, 0.8), (1.1e-6, 0.8), (4.7e-6, 0.6), (0.2e-6, 0.9)]):
        a(f"C3_{i} p3 c3_{i} {d(c, fac)}")
        a(f"R3_{i} c3_{i} 0 0.01")
    a(f"Inrf p3 0 PULSE(3m {3e-3 + ib} 1m 10u 10u {tw} {tp})")
    a("Idvdd p3 0 0.8m")
    if filt == "separate LDO":
        a(f"Bldo2 la 0 V=3.3+0.001*(V(vbat)-3.8)")           # analog LDO, 60 dB PSRR at burst frequencies
        a("Fin2 vbat 0 Vsn2 1")
        a("Vsn2 la la2 0")
        a("Ra la2 p3a 0.1")
    elif filt == "ferrite":
        a("Rfb p3 fb 0.3")                                    # 600 ohm@100 MHz 0402 bead: ~0.3 ohm DCR, ~1.5 uH low-f
        a("Lfb fb p3a 1.5u")
    else:
        a(f"Rflt p3 p3a {10 if filt == '10R' else 47}")
    # +3V3A caps: 10u (0402 6.3 V: ~0.4 at 3.3 V) + 1u + 3x100n
    for i, (c, fac) in enumerate([(10e-6, 0.4), (1e-6, 0.8), (0.3e-6, 0.9)]):
        a(f"CA_{i} p3a ca_{i} {d(c, fac)}")
        a(f"RA_{i} ca_{i} 0 0.01")
    a("Iavdd p3a 0 2.8m")
    return "\n".join(L) + "\n"


def tran(netl):
    with tempfile.TemporaryDirectory() as td:
        cir, dat = os.path.join(td, "s.cir"), os.path.join(td, "s.dat")
        with open(cir, "w") as f:
            f.write(netl + f".control\nset wr_singlescale\nset wr_vecnames\noption interp\n"
                    f"tran {DT} {T1} 0 {DT}\nlinearize v(p3) v(p3a) v(vbat)\n"
                    f"wrdata {dat} v(p3) v(p3a) v(vbat)\nquit\n.endc\n.end\n")
        subprocess.run(["ngspice", "-b", cir], capture_output=True, text=True)
        d = np.loadtxt(dat, skiprows=1)
    t = d[:, 0]
    m = t >= T0
    return t[m], d[m, 1], d[m, 2], d[m, 3]


def sinc3(f, fdr=4e3, fmod=512e3):
    n = fmod / fdr
    x = np.pi * np.maximum(f, 1e-9) / fmod
    return np.abs(np.sin(n * x) / (n * np.sin(x))) ** 3


def ref_transfer(cfg):
    """|CH1 differential| per volt of AVDD (RLDREF = AVDD/2), 1M||4.7n/pad, 30 % P/N mismatch, 5 pF trace mismatch."""
    line = {0: dict(re=1e6, ce=4.7e-9, ctr=15e-12), 1: dict(re=1.3e6, ce=4.7e-9 / 1.3, ctr=20e-12)}
    p = afe.default_params(vref_ac=0.5, line=line, cge=1e-6, cb=200e-12, **cfg)
    r = afe.simulate(p, "ac dec 50 1 1e5", ("v(in0)", "v(in1)", "v(body)"))
    return r["f"], np.abs(r["v(in0)"] - r["v(in1)"])


def inband(f, spec_v, h, fs=4e3, bands=((20, 450), (20, 850))):
    """spec_v: one-sided amplitude (V rms per bin). h: input-referral magnitude per bin. Fold through sinc3."""
    p = (spec_v * h * sinc3(f, fs)) ** 2
    fa = np.abs(((f + fs / 2) % fs) - fs / 2)
    return [np.sqrt(p[(fa >= lo) & (fa < hi)].sum()) for lo, hi in bands]


def main():
    refs = {"passive bias": dict(nsense=0), "RLD N=8, 4.7 nF": dict(nsense=8, cf=4.7e-9),
            "RLD N=16, 10 nF": dict(nsense=16, cf=10e-9)}
    rt = {k: ref_transfer(v) for k, v in refs.items()}
    rows = []
    waves = {}
    print("ldo | filter | burst (A, width, period) | AVDD DC | +3V3 pk-pk mV | AVDD pk-pk mV | AVDD rms 20-850 uV |"
          " in-ref PSRR90 uV | via RLDREF (N=8) uV 20-450/20-850")
    for ldo, filt, burst in itertools.product(LDO, FILT, BURST):
        t, v3, va, vb = tran(netlist(ldo, filt, burst))
        n = len(t)
        win = np.hanning(n)
        X = np.fft.rfft((va - va.mean()) * win) / (win.sum() / 2) / np.sqrt(2)   # rms amplitude per bin
        f = np.fft.rfftfreq(n, DT)
        X = np.abs(X)
        band = (f >= 20) & (f <= 850)
        avdd_rms = np.sqrt((X[band] ** 2).sum() / 1.5)       # Hann ENBW 1.5 bins
        row = dict(ldo=ldo, filter=filt, i_burst_mA=burst[0] * 1e3, t_burst_ms=burst[1] * 1e3,
                   period_ms=burst[2] * 1e3, avdd_dc=va.mean(), p3v3_pp_mV=np.ptp(v3) * 1e3,
                   avdd_pp_mV=np.ptp(va) * 1e3, vbat_pp_mV=np.ptp(vb) * 1e3, avdd_rms_20_850_uV=avdd_rms * 1e6)
        for psrr in (90, 80):
            a = inband(f, X / np.sqrt(1.5), np.full_like(f, 10 ** (-psrr / 20)))
            row[f"psrr{psrr}_20_450_uV"], row[f"psrr{psrr}_20_850_uV"] = a[0] * 1e6, a[1] * 1e6
        for k, (fr, hr) in rt.items():
            h = np.interp(f, fr, hr, left=hr[0], right=hr[-1])
            a = inband(f, X / np.sqrt(1.5), h)
            row[f"rldref[{k}]_20_450_uV"], row[f"rldref[{k}]_20_850_uV"] = a[0] * 1e6, a[1] * 1e6
        rows.append(row)
        if burst == BURST[1]:
            waves[(ldo, filt)] = (t, v3, va)
        print(f"{ldo:7s} | {filt:12s} | {burst[0]*1e3:4.0f} mA {burst[1]*1e3:4.2f}/{burst[2]*1e3:4.1f} ms | "
              f"{row['avdd_dc']:.3f} | {row['p3v3_pp_mV']:6.2f} | {row['avdd_pp_mV']:7.3f} | {row['avdd_rms_20_850_uV']:8.1f} | "
              f"{row['psrr90_20_850_uV']:.4f} | {row['rldref[RLD N=8, 4.7 nF]_20_450_uV']:.3f}/"
              f"{row['rldref[RLD N=8, 4.7 nF]_20_850_uV']:.3f}")
    with open(os.path.join(afe.OUT, "q4_supply.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for k, (fr, hr) in rt.items():
        print(f"RLDREF path {k}: |dV_diff/dAVDD| at 50/133/500 Hz = "
              + ", ".join(f"{20*np.log10(np.interp(x, fr, hr)):.1f} dB" for x in (50, 133, 500)))

    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    for (ldo, filt), (t, v3, va) in waves.items():
        if ldo != "nominal":
            continue
        m = (t > 0.1) & (t < 0.1225)
        ax[0].plot((t[m] - 0.1) * 1e3, (va[m] - va.mean()) * 1e3, label=f"AVDD, {filt}")
    t, v3, va = waves[("nominal", "10R")]
    m = (t > 0.1) & (t < 0.1225)
    ax[0].plot((t[m] - 0.1) * 1e3, (v3[m] - v3.mean()) * 1e3, "k:", label="+3V3 (shared rail)")
    ax[0].set_xlabel("ms")
    ax[0].set_ylabel("mV (AC)")
    ax[0].set_title("10 mA x 2 ms radio bursts every 7.5 ms, nominal LDO model", fontsize=9)
    ax[0].legend(fontsize=7)
    ax[0].grid(alpha=0.3)
    for k, (fr, hr) in rt.items():
        ax[1].semilogx(fr, 20 * np.log10(hr), label=f"RLDREF path, {k}")
    ax[1].axhline(-90, color="k", ls="--", label="ADS1298 PSRR 90 dB (gain 6, 50/60 Hz)")
    ax[1].set_xlim(10, 1e4)
    ax[1].set_xlabel("Hz")
    ax[1].set_ylabel("dB (input-referred differential / AVDD ripple)")
    ax[1].set_title("AVDD ripple -> CH1 differential, 1M||4.7nF pads, 30 % mismatch", fontsize=9)
    ax[1].legend(fontsize=7)
    ax[1].grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(afe.OUT, "q4_supply.png"), dpi=130)


if __name__ == "__main__":
    main()
