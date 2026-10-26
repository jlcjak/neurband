#!/usr/bin/env python3
"""Plot a neurband recording.

  python3 neurband_plot.py rec.npz                  # band-passed EMG + lead-off raster
  python3 neurband_plot.py rec.npz --raw --t0 5 --t1 8 -o fig.png
"""
import argparse
import json

import numpy as np
import matplotlib.pyplot as plt

from neurband_rec import bandpass_notch

INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
EMG = "#2a78d6"  # single series hue: channels are labelled on the axis


def style(ax):
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--raw", action="store_true", help="no band-pass/notch")
    ap.add_argument("--mains", type=float, default=None, help="notch (default: from recording)")
    ap.add_argument("--t0", type=float, default=None)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("-o", "--out", help="save figure instead of showing it")
    a = ap.parse_args()

    d = np.load(a.file)
    meta = json.loads(str(d["meta"]))
    fs = meta["rate"]
    t, emg = d["t"], d["emg"].astype(np.float64)
    if not a.raw:
        emg = bandpass_notch(emg, fs, mains=meta.get("mains", 50) if a.mains is None else a.mains)
    sel = np.ones(len(t), bool)
    if a.t0 is not None:
        sel &= t >= a.t0
    if a.t1 is not None:
        sel &= t <= a.t1
    t, emg = t[sel], emg[sel] * 1e6  # uV
    if a.raw:
        emg = emg - np.median(emg, axis=0)  # remove electrode offsets so traces stack

    fig, axs = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                            gridspec_kw={"height_ratios": [6, 1]})
    fig.patch.set_facecolor("#fcfcfb")

    # EMG, stacked with a common spacing (robust to one bad channel)
    ax = axs[0]
    spread = np.percentile(np.abs(emg), 99.5, axis=0) if len(emg) else np.ones(16)
    step = max(np.median(spread) * 2.5, 1.0)
    for ch in range(emg.shape[1]):
        ax.plot(t, emg[:, ch] - ch * step, color=EMG, lw=0.6)
    ax.set_yticks([-ch * step for ch in range(16)], [f"ch{ch + 1}" for ch in range(16)])
    ax.set_ylim(-15.8 * step, 0.8 * step)
    title = "raw (offset removed)" if a.raw else "band-pass 20-450 Hz + notch"
    ax.set_title(f"{a.file}  -  EMG {title}, trace spacing {step:.0f} uV, {fs} SPS, gain {meta['gain']}",
                 color=INK, fontsize=10, loc="left")

    # lead-off raster: one row per channel, dark = electrode off (P or N side)
    ax = axs[1]
    pt = (d["pkt_t_us"] - d["pkt_t_us"][0]) / 1e6
    bits = d["loff_p"].astype(np.uint32) | d["loff_n"].astype(np.uint32)
    raster = ((bits[None, :] >> np.arange(16)[:, None]) & 1).astype(float)
    if len(pt):
        ax.imshow(raster, aspect="auto", interpolation="nearest", cmap="Greys", vmin=0, vmax=1.5,
                  extent=(pt[0], pt[-1] if len(pt) > 1 else pt[0] + 0.01, 16.5, 0.5))
    ax.set_yticks([1, 8, 16], ["ch1", "ch8", "ch16"])
    ax.set_ylabel("lead-off\n(dark = off)", color=INK2, fontsize=9)
    ax.set_xlabel("time [s]", color=INK2)

    for ax in axs:
        style(ax)
        for mt in d["marker_t"]:
            if (a.t0 is None or mt >= a.t0) and (a.t1 is None or mt <= a.t1):
                ax.axvline(mt, color=INK2, lw=1.0, ls="--")
    if len(d["marker_t"]):
        axs[0].text(d["marker_t"][0], 0.75 * step, " marker", color=INK2, fontsize=8, va="top")
    if len(t):
        axs[-1].set_xlim(t[0], t[-1])
    fig.text(0.99, 0.005, f"lost packets {meta.get('lost_packets', 0)}, firmware drops {meta.get('fw_drops', 0)}",
             ha="right", fontsize=8, color=INK2)
    fig.tight_layout()
    if a.out:
        fig.savefig(a.out, dpi=120)
        print(f"wrote {a.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
