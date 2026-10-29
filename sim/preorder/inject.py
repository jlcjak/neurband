"""In-band (20-850 Hz) interference injected into each electrode net by capacitive coupling.

Aggressor waveforms are synthesised from the firmware timing (firmware_c/src: SPI 8 MHz frame reads after
each 4 kSPS DRDY, LSM6DSL at 208 Hz with 75 us DRDY pulses and 12-byte 400 kHz I2C burst reads, LED flash
50 ms every 0.5 s while streaming, BLE events every 7.5 ms) and the q4 supply-ripple results. Their
spectra are combined with the extracted mutual capacitance (out/coupling_pairs.csv):

    V_victim(f) = V_agg(f) * |j w Cm Z(f)|,   Z = Zs || 1/(j w C_node),   Zs = R || C_e (dry contact)

Above the contact corner 1/(2 pi R C_e) this is ~ V_agg * Cm / C_e, independent of frequency. MHz content
is irrelevant in-band here: digital clocks are >=64 kHz from n*512 kHz (sinc^3 stop band, > 100 dB)
and the J1-side nodes are shorted to the body by C_e at MHz. ADS-side nodes are treated the same way
(4.7 kOhm << |Zs| in band; the 2026-10-29 re-check adds the real series resistor RSER on ADS-side nodes).
Output: out/inject_summary{TAG}.csv, printed table. Env: TAG (input/output suffix), RSER (default 4700).
"""
import csv
import math
import os
import re
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FS = 2_000_000
DUR = 2.0
rng = np.random.default_rng(1)
N = int(FS * DUR)
t = np.arange(N) / FS


def radio_mask(period=7.5e-3, length=2.5e-3, phase=0.3e-3):
    return ((t - phase) % period) < length


def frame_latency(nominal=15e-6, radio_extra=(0, 60e-6)):
    """Per-frame DRDY->SPI start latency (s): radio events delay the SPI start (MPSL preemption)."""
    nf = int(DUR * 4000)
    ts = np.arange(nf) / 4000.0
    lat = np.full(nf, nominal)
    inr = (((ts - 0.3e-3) % 7.5e-3) < 2.5e-3)
    lat[inr] += rng.uniform(*radio_extra, inr.sum())
    return ts, lat


def waveforms():
    w = {}
    # ---- LSM6DSL: 208 Hz (own oscillator, +-1 %), INT1 75 us pulse, I2C burst read 140 SCL @ 400 kHz
    f_imu = 208.0 * 1.003
    ph = (t * f_imu) % 1.0
    tau_int = 75e-6 * f_imu
    w["/IMU_INT"] = np.where(ph < tau_int, 3.3, 0.0)
    lat_i2c = 60e-6 * f_imu  # ISR -> thread -> TWIM start
    burst = 140 / 400e3 * f_imu
    inb = (ph >= lat_i2c) & (ph < lat_i2c + burst)
    scl = np.where(inb, np.where((t * 400e3) % 1.0 < 0.5, 0.0, 3.3), 3.3)
    w["/I2C_SCL"] = scl
    bits = rng.integers(0, 2, int(DUR * 400e3) + 2)
    sda = np.where(inb, 3.3 * bits[(t * 400e3).astype(int)], 3.3)
    w["/I2C_SDA"] = sda
    # ---- ADS frame read: DRDY low from conversion end until SPI start, CS low for the 27-byte read
    ts, lat = frame_latency()
    drdy = np.full(N, 3.3)
    cs = np.full(N, 3.3)
    sck = np.zeros(N)
    miso = np.zeros(N)
    for k, (t0, L) in enumerate(zip(ts, lat)):
        i0 = int(t0 * FS)
        i1 = int((t0 + L) * FS)
        i2 = int((t0 + L + 27e-6) * FS)
        drdy[i0:i1] = 0.0
        cs[i1 - 4:i2 + 4] = 0.0
        seg = np.arange(i1, min(i2, N))
        sck[seg] = np.where(((seg - i1) / FS * 8e6) % 1.0 < 0.5, 3.3, 0.0)
        miso[seg] = 3.3 * rng.integers(0, 2, len(seg) // 2 + 1).repeat(2)[:len(seg)]
    w["/ADC_DRDY"], w["/ADC_CS"], w["/SPI_SCK"], w["/SPI_MISO"] = drdy, cs, sck, miso
    w["/SPI_MOSI"] = np.zeros(N)         # RDATAC: DIN held low during frame reads
    # ---- LED: active-low cathode, 50 ms flash every 0.5 s while streaming; anode node swings 3.3 -> ~1.9 V
    led_on = (t % 0.5) < 0.05
    w["/LED"] = np.where(led_on, 0.05, 3.3)
    w["Net-(D1-A)"] = np.where(led_on, 1.9, 3.3)
    # ---- supplies (radio bursts 10 mA x 2.5 ms every 7.5 ms; q4 nominal LDO model)
    rm = radio_mask()
    w["VBAT"] = -0.006 * rm                # 10 mA x ~0.6 ohm (cell + protection + leads)
    w["+3V3"] = -0.020 * rm                # q4: 20 mVpp nominal (76 mV slow LDO)
    w["+3V3A"] = -0.005 * rm               # q4: 5.1 mVpp nominal (54 mV slow)
    w["/DEC4"] = -0.005 * rm
    w["/VBAT_SENSE"] = -0.003 * rm * 0.0   # 1M/1M + 100 nF: 8 Hz corner, ripple ~0
    for static in ("/BUTTON", "/NRST", "/SWDCLK", "/SWDIO", "/ADC_START", "/ADC_PWDN", "VCHG", "/CHG_N"):
        w[static] = np.zeros(N)
    return w


def inband_spectrum(x):
    X = np.fft.rfft(x - x.mean()) / len(x) * 2  # peak amplitude per bin
    f = np.fft.rfftfreq(len(x), 1 / FS)
    sel = (f >= 20) & (f <= 850)
    return f[sel], X[sel]


ZS = {"100k||10n": (100e3, 10e-9), "1M||10n": (1e6, 10e-9), "1M||1n (adverse)": (1e6, 1e-9)}
C_NODE = 35e-12
RSER = float(os.environ.get("RSER", "4700"))
TAG = os.environ.get("TAG", "")


def victim_gain(f, cm, R, C, ads_side=False):
    w = 2 * np.pi * f
    zs = R / (1 + 1j * w * R * C)
    if ads_side:  # ADS-side node: (contact + series R) || ADS input + trace (~25 pF)
        z = 1 / (1 / (zs + RSER) + 1j * w * 25e-12)
    else:
        z = 1 / (1 / zs + 1j * w * C_NODE)
    return np.abs(1j * w * cm * z)


def classify(v):
    if re.fullmatch(r"/E\d[PN]", v):
        return "electrode (J1 side)"
    if v.startswith("Net-(RN"):
        return "electrode (ADS side)"
    return "bias/RLD"


# ADS-side net -> channel (from the RN pad pairs: RNx pin k <-> pin 9-k)
RN_MAP = {"RN1A": "E1P", "RN1B": "E1N", "RN1C": "E2P", "RN1D": "E2N", "RN2A": "E3P", "RN2B": "E3N",
          "RN2C": "E4P", "RN2D": "E4N", "RN3A": "E5P", "RN3B": "E5N", "RN3C": "E6P", "RN3D": "E6N",
          "RN4A": "E7P", "RN4B": "E7N", "RN4C": "E8P", "RN4D": "E8N"}


def channel_of(v):
    m = re.fullmatch(r"/E(\d)([PN])", v)
    if m:
        return f"E{m.group(1)}{m.group(2)}"
    m = re.match(r"Net-\((RN\d[A-D])", v)
    if m:
        return RN_MAP[m.group(1)] + "(ads)"
    return v


def main():
    W = waveforms()
    spec = {k: inband_spectrum(v) for k, v in W.items()}
    agg_rms = {k: math.sqrt(np.sum(np.abs(X) ** 2) / 2) for k, (f, X) in spec.items()}
    print("Aggressor in-band (20-850 Hz) content, Vrms:")
    for k, v in sorted(agg_rms.items(), key=lambda kv: -kv[1]):
        print(f"  {k:14s} {v * 1e3:9.3f} mVrms")
    rows = list(csv.DictReader(open(os.path.join(HERE, "out", f"coupling_pairs{TAG}.csv"))))
    tot = defaultdict(float)
    for r in rows:
        if r["aggressor"] in spec:
            tot[(r["victim"], r["aggressor"])] += float(r["cm_fF"]) * 1e-15
    out = []
    for (v, a), cm in tot.items():
        f, X = spec[a]
        res = {}
        for name, (R, C) in ZS.items():
            g = victim_gain(f, cm, R, C, ads_side=v.startswith("Net-(RN"))
            res[name] = math.sqrt(np.sum((np.abs(X) * g) ** 2) / 2) * 1e6  # uVrms
        kind = classify(v)
        if kind == "bias/RLD":
            # BIAS_E/RLD nodes: injected current moves the body (CM), suppressed by the loop (|1+T| ~ 5
            # at 200 Hz, q1) and converted to DM at ~ -54 dB (q2, 30 % mismatch); node Z ~ 100k || Zs/8.
            res = {k: v_ * 0.2 * 0.002 * 0.125 for k, v_ in res.items()}
        out.append(dict(victim=v, channel=channel_of(v), kind=kind, aggressor=a, cm_fF=round(cm * 1e15, 2),
                         **{f"uV_{k}": round(x, 4) for k, x in res.items()}))
    out.sort(key=lambda r: -r["uV_1M||10n"])
    with open(os.path.join(HERE, "out", f"inject_summary{TAG}.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        wr.writeheader()
        wr.writerows(out)
    with open(os.path.join(HERE, "out", f"aggressor_inband{TAG}.csv"), "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["aggressor", "inband_20_850Hz_mVrms"])
        for k, v in sorted(agg_rms.items(), key=lambda kv: -kv[1]):
            wr.writerow([k, round(v * 1e3, 4)])
    print(f"\n{'victim':18s} {'ch':9s} {'aggressor':12s} {'Cm fF':>8s} {'100k||10n':>10s} {'1M||10n':>9s} {'1M||1n':>9s} uVrms")
    for r in out[:40]:
        print(f"{r['victim']:18s} {r['channel']:9s} {r['aggressor']:12s} {r['cm_fF']:8.2f} "
              f"{r['uV_100k||10n']:10.3f} {r['uV_1M||10n']:9.3f} {r['uV_1M||1n (adverse)']:9.3f}")
    # per-channel differential estimate (P minus N, worst case = no cancellation: RSS of P and N terms)
    ch = defaultdict(lambda: defaultdict(float))
    for r in out:
        if r["kind"].startswith("electrode"):
            c = r["channel"][:2]
            for k in ZS:
                ch[c][k] += r[f"uV_{k}"] ** 2
    print("\nPer channel RSS of all couplings (no P/N cancellation), uVrms:")
    for c in sorted(ch):
        print("  ", c, "  ".join(f"{k}: {math.sqrt(v):.3f}" for k, v in ch[c].items()))
    with open(os.path.join(HERE, "out", f"inject_per_channel{TAG}.csv"), "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["channel"] + [f"uVrms_{k}" for k in ZS])
        for c in sorted(ch):
            wr.writerow([c] + [round(math.sqrt(ch[c][k]), 4) for k in ZS])


if __name__ == "__main__":
    main()
