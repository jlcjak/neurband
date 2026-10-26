"""Shared ngspice model of the neurband rev C analog front end (AC small-signal).

Circuit source of truth: boards/neurband_c/gen_c_sch.py
  - every electrode line: 4.7 kOhm (RN1-RN4) in series to INxP/INxN
  - RLD: 1 MOhm || Cf (4.7 nF fitted) RLDOUT->RLDINV, 100 kOhm RLDOUT->BIAS_E, BIAS_E also to RLDIN
  - RLDREF pin NC -> internal (AVDD+AVSS)/2 reference (RLDREF_INT=1)
ADS1298 values: docs/datasheets/ads1298.txt (SBAS459K) - see DS below.
Device GND (AVSS) is SPICE node 0. "earth" is a separate node reached only through capacitances.
"""
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np

TWO_PI = 2 * np.pi

# ---- ADS1298 datasheet values (SBAS459K, docs/datasheets/ads1298.txt) ----
DS = dict(
    gbw=100e3,        # RLD amp gain-bandwidth, 50k||10p load, G=1 (EC table "RLD amplifier")
    a0=1e5,           # open-loop DC gain: NOT in datasheet -> assumed 100 dB (single-pole model)
    rout=100.0,       # output resistance: datasheet lists 100 ohm for pace amp only -> assumed for RLD
    rsum=220e3,       # internal RLD summing resistor per selected input (Fig. 43; EC table quotes "200 kOhm")
    f_pga=64e3,       # PGA small-signal BW at gain 6 (Table 5); used as CM sense-path pole
    r_emi=5e3,        # input protection/EMI series R (Fig. 24), 5k*10p = 3.2 MHz ~ "approx. 3 MHz" (9.3.1.1)
    c_emi=10e-12,     # internal EMI shunt C (Fig. 24)
    c_pin=10e-12,     # remaining input C so that total = 20 pF typ (EC table "Input capacitance 20 pF")
    r_in=1e9,         # DC input impedance, no lead-off, min 1000 MOhm (EC table)
    c_rldinv=5e-12,   # RLDINV pin + pad parasitic (assumed)
    c_rldin=10e-12,   # RLDIN mux pin on BIAS_E (assumed, same order as an input pin)
)

# ---- rev C board values (gen_c_sch.py) ----
BOARD = dict(rf=1e6, cf=4.7e-9, rprot=100e3, rser=4.7e3, n_pads_bias=8, n_lines=16)


def default_params(**kw):
    p = dict(
        # electrodes (per 6.5 mm pad), R || C
        re=1e6, ce=4.7e-9,
        re_bias=None, ce_bias=None,     # bias pads (default: same skin as sensing pads)
        ctr=15e-12,                     # flex trace capacitance to GND hatch, per line
        ctr_bias=20e-12,                # BIAS_E bus trace (connects 8 pads)
        # body / environment
        cb=200e-12,                     # body to earth
        cge=10e-12,                     # device GND to earth (battery, floating)  -> 1 for "bench grounded"
        cbg=50e-12,                     # body to device GND directly (PCB + flex hatch through coverlay)
        cm=2e-12,                       # mains to body
        cmd=0.0,                        # mains to device GND directly
        vm=0.0,                         # mains AC amplitude (V rms); 0 for loop-gain runs
        vref_ac=0.0,                    # AC on the RLD reference (AVDD/2 ripple) for supply analysis
        # RLD configuration
        cf=BOARD["cf"], rf=BOARD["rf"], rprot=BOARD["rprot"], nsense=16,
        mode="closed",                  # closed | broken (loop gain) | off (RLD amp powered down)
        gbw=DS["gbw"], rsum=DS["rsum"],
        # per-line overrides {line_index: dict(re=..., ce=..., ctr=...)}; line 0 = CH1 P, 1 = CH1 N, ...
        line=None,
    )
    p.update(kw)
    return p


def netlist(p, analysis="ac dec 40 1 1e6", probes=("v(drv)", "v(rldout)", "v(body)", "v(in0)", "v(in1)")):
    L = ["* neurband rev C AFE"]
    a = L.append
    big = "1e13"
    # environment
    a(f"Vmains mains earth AC {p['vm']}")
    a(f"Cm mains body {p['cm']}")
    if p["cmd"] > 0:
        a(f"Cmd mains 0 {p['cmd']}")
    a(f"Cb body earth {p['cb']}")
    a(f"Cge earth 0 {p['cge']}")
    a(f"Rge earth 0 {big}")
    a(f"Cbg body 0 {p['cbg']}")
    a(f"Rbody body 0 {big}")
    # bias electrode network: 8 pads in parallel
    nb = BOARD["n_pads_bias"]
    reb = p["re_bias"] or p["re"]
    ceb = p["ce_bias"] or p["ce"]
    a(f"Rprot drv bias_e {p['rprot']}")
    a(f"Cbias bias_e 0 {p['ctr_bias'] + DS['c_rldin']}")
    a(f"Rpb bias_e body {reb / nb}")
    a(f"Cpb bias_e body {ceb * nb}")
    # 16 electrode lines
    for k in range(BOARD["n_lines"]):
        q = dict(re=p["re"], ce=p["ce"], ctr=p["ctr"])
        if p["line"] and k in p["line"]:
            q.update(p["line"][k])
        a(f"Re{k} body e{k} {q['re']}")
        a(f"Ce{k} body e{k} {q['ce']}")
        a(f"Ctr{k} e{k} 0 {q['ctr']}")
        a(f"Rs{k} e{k} pin{k} {BOARD['rser']}")
        a(f"Cp{k} pin{k} 0 {DS['c_pin']}")
        a(f"Remi{k} pin{k} in{k} {DS['r_emi']}")
        a(f"Cemi{k} in{k} 0 {DS['c_emi']}")
        a(f"Rin{k} in{k} 0 {DS['r_in']}")
        if k < p["nsense"] and p["mode"] != "off":
            cpga = 1 / (TWO_PI * 1e3 * DS["f_pga"])
            a(f"Ea{k} a{k} 0 in{k} 0 1")
            a(f"Rpg{k} a{k} b{k} 1k")
            a(f"Cpg{k} b{k} 0 {cpga}")
            a(f"Eo{k} o{k} 0 b{k} 0 1")
            a(f"Rsum{k} o{k} inv {p['rsum']}")
    if p["mode"] == "off":
        a(f"Rdrv drv 0 {big}")          # RLD amp powered down: RLDOUT high impedance
    else:
        # RLD amplifier: single-pole op-amp, A0, GBW; output resistance
        a(f"Vref ref 0 AC {p['vref_ac']}")
        a(f"Cinv inv 0 {DS['c_rldinv']}")
        a(f"Rinv inv 0 {big}")
        a(f"Rf rldout inv {p['rf']}")
        a(f"Cf rldout inv {p['cf']}")
        a("Gop 0 n1 ref inv 1")
        a(f"R1 n1 0 {DS['a0']}")
        a(f"C1 n1 0 {1 / (TWO_PI * p['gbw'])}")
        a("Eout x 0 n1 0 1")
        a(f"Rout x rldout {DS['rout']}")
        if p["mode"] == "broken":
            a("Vt drv 0 AC 1")            # loop broken between amplifier output and the 100k
        else:
            a("Vlink rldout drv 0")
    return "\n".join(L) + "\n", list(probes), analysis


def run(net, probes, analysis):
    with tempfile.TemporaryDirectory() as td:
        cir = os.path.join(td, "c.cir")
        dat = os.path.join(td, "o.dat")
        with open(cir, "w") as f:
            f.write(net)
            f.write(".control\nset wr_singlescale\nset wr_vecnames\n")
            f.write(f"{analysis}\nwrdata {dat} {' '.join(probes)}\nquit\n.endc\n.end\n")
        r = subprocess.run(["ngspice", "-b", cir], capture_output=True, text=True)
        if not os.path.exists(dat):
            raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
        d = np.loadtxt(dat, skiprows=1)
    d = np.atleast_2d(d)
    f = d[:, 0]
    out = {"f": f}
    for i, pr in enumerate(probes):
        out[pr] = d[:, 1 + 2 * i] + 1j * d[:, 2 + 2 * i]
    return out


def simulate(p, analysis="ac dec 40 1 1e6", probes=None):
    args = netlist(p, analysis, probes) if probes else netlist(p, analysis)
    return run(*args)


def pmap(fn, items, workers=16):
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(fn, items))


def margins(f, T):
    """Return (fc, PM deg, GM dB, Ms dB) for return ratio T (negative feedback => T>0 at DC)."""
    mag = np.abs(T)
    ph = np.degrees(np.unwrap(np.angle(T)))
    ms = 20 * np.log10(np.max(np.abs(1 / (1 + T))))
    above = mag >= 1
    if not above.any():
        fc, pm = np.nan, np.inf
    else:
        i = np.where(above)[0][-1]          # last frequency with |T|>=1
        if i == len(f) - 1:
            fc, pm = f[i], np.nan
        else:
            x = np.log(mag[i]) / (np.log(mag[i]) - np.log(mag[i + 1]))
            fc = np.exp(np.log(f[i]) + x * (np.log(f[i + 1]) - np.log(f[i])))
            phc = ph[i] + x * (ph[i + 1] - ph[i])
            pm = 180 + phc
    j = np.where(ph <= -180)[0]
    gm = -20 * np.log10(mag[j[0]]) if len(j) else np.inf
    return fc, pm, gm, ms


def at(f, y, f0):
    """Complex value of y at f0 (log-frequency interpolation)."""
    lf = np.log(f)
    return np.interp(np.log(f0), lf, y.real) + 1j * np.interp(np.log(f0), lf, y.imag)


OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
