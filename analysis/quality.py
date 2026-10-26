"""Per-channel signal-quality report with pass / warn / fail gates.

Thresholds are judgment calls for this hardware (ADS1298, gain 6, dry gold pads) and are
explained in docs/science/data_and_models.md section (d). Change GATES to tune them.

Rest and MVC segments come from the labels (kind 'rest' / 'mvc') when available,
otherwise from the quietest / loudest 1 s windows of the recording.
"""
import numpy as np

from . import filters as F

# metric: (warn_if_worse_than, fail_if_worse_than, higher_is_better)
GATES = {
    "noise_uv": (5.0, 10.0, False),      # rest RMS, 20-450 Hz, after notch
    "line_uv": (30.0, 200.0, False),     # raw mains + harmonics RMS at rest (before notch)
    "lf_uv": (300.0, 2000.0, False),     # 1-15 Hz RMS at rest: motion / contact instability
    "dc_frac": (0.5, 0.9, False),        # |DC offset| / full scale
    "clip_frac": (1e-5, 1e-3, False),    # fraction of samples at the rails
    "loff_frac": (0.001, 0.01, False),   # fraction of packets with lead-off flagged
    "mvc_snr_db": (20.0, 12.0, True),    # MVC RMS / rest RMS, 20-450 Hz
}
FLAT_STD_V = 0.5e-6   # raw (detrended) std below this = dead / shorted channel


def _grade(metric, v):
    warn, fail, higher = GATES[metric]
    if v is None or not np.isfinite(v):
        return "n/a"
    bad = (lambda a, b: a < b) if higher else (lambda a, b: a > b)
    return "FAIL" if bad(v, fail) else "WARN" if bad(v, warn) else "ok"


def _segments(rec, kind, events=None):
    if events is None and rec.labels:
        from .align import device_events
        try:
            events = device_events(rec, refine=False)
        except ValueError:
            events = []
    segs = []
    for e in events or []:
        if e["kind"] == kind and (kind != "gesture" or e["label"] == "rest"):
            a, b = (e["t_start"], e["t_end"]) if kind == "rest" else (e["t_start"] + 0.5, e["t_end"])
            segs.append((int(a * rec.fs), int(b * rec.fs)))
    return [(max(0, a), min(len(rec.emg), b)) for a, b in segs if b - a > rec.fs * 0.3]


def _auto_windows(y, fs, pct):
    """Indices of the 1 s windows whose total power is at a percentile (quiet or loud)."""
    L = int(fs)
    nw = len(y) // L
    if nw < 3:
        return [(0, len(y))]
    p = np.array([np.mean(y[i * L:(i + 1) * L] ** 2) for i in range(nw)])
    if pct < 50:
        sel = np.where(p <= np.percentile(p, pct))[0]
    else:
        sel = np.where(p >= np.percentile(p, pct))[0]
    return [(i * L, (i + 1) * L) for i in sel]


def _cat(x, segs):
    return np.concatenate([x[a:b] for a, b in segs]) if segs else x[:0]


def report(rec, mains=None, events=None):
    """Return dict: per-channel metrics + grades, recording-level summary and a verdict."""
    mains = mains if mains is not None else rec.meta.get("mains", 50.0) or 50.0
    fs, x = rec.fs, rec.emg.astype(np.float64)
    C = x.shape[1]
    y = F.bandpass_notch(x, fs, 20, 450, mains)
    edge = int(0.5 * fs)                      # ignore filter edges
    y[:edge] = 0
    y[-edge:] = 0
    auto = lambda pct: [(a + edge, b + edge) for a, b in _auto_windows(y[edge:-edge], fs, pct)]
    rest = _segments(rec, "rest", events) or auto(10)
    mvc = _segments(rec, "mvc", events)
    mvc_auto = not mvc
    mvc = mvc or auto(98)

    yr, ym = _cat(y, rest), _cat(y, mvc)
    xr = _cat(x, rest)
    noise = np.sqrt(np.mean(yr ** 2, axis=0)) if len(yr) else np.full(C, np.nan)
    mvc_rms = np.sqrt(np.mean(ym ** 2, axis=0)) if len(ym) else np.full(C, np.nan)
    seg = xr if len(xr) >= 2 * fs else (x[edge:-edge] if len(x) > 4 * edge else x)
    line = F.line_rms(seg[: int(fs * 60)], fs, mains)   # at rest, so EMG near 50 Hz does not count
    lf = F.band_rms(xr[: int(fs * 30)], fs, 1, 15) if len(xr) > fs else np.full(C, np.nan)
    fsv = rec.full_scale or np.max(np.abs(x)) or 1.0
    dc = np.abs(np.median(x, axis=0)) / fsv
    clip = np.mean(np.abs(x) >= fsv * 0.999, axis=0)
    loff = rec.loff.mean(axis=0) if rec.loff is not None and len(rec.loff) else np.zeros(C)
    t = np.arange(len(x)) - (len(x) - 1) / 2
    xd = x - x.mean(0) - np.outer(t, (t @ (x - x.mean(0))) / (t @ t))
    flat = xd.std(axis=0) < FLAT_STD_V
    with np.errstate(divide="ignore", invalid="ignore"):
        snr = 20 * np.log10(mvc_rms / noise)

    chans = []
    for c in range(C):
        m = {"noise_uv": noise[c] * 1e6, "line_uv": line[c] * 1e6, "lf_uv": lf[c] * 1e6,
             "dc_frac": dc[c], "clip_frac": clip[c], "loff_frac": loff[c], "mvc_snr_db": snr[c]}
        g = {k: _grade(k, v) for k, v in m.items()}
        if mvc_auto and g["mvc_snr_db"] == "FAIL":
            g["mvc_snr_db"] = "WARN"  # no labelled MVC: the loudest windows may be weak gestures
        if flat[c]:
            g["flat"] = "FAIL"
        worst = "FAIL" if "FAIL" in g.values() else "WARN" if "WARN" in g.values() else "ok"
        chans.append({"ch": c + 1, "metrics": m, "grades": g, "flat": bool(flat[c]), "status": worst})

    # neighbouring channels that are nearly identical at rest: sweat bridge / shorted pads
    bridged = []
    if len(yr) > fs:
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.corrcoef(yr.T)
        for c in range(C):
            if np.isfinite(r[c, (c + 1) % C]) and r[c, (c + 1) % C] > 0.95:
                bridged.append((c + 1, (c + 1) % C + 1))

    n_pkt = rec.meta.get("n_samples", len(x)) / 20
    loss = rec.meta.get("lost_packets", 0) / max(1.0, n_pkt)
    n_fail = sum(ch["status"] == "FAIL" for ch in chans)
    if loss > 0.01 or n_fail > 1:
        verdict = "REJECT"
    elif loss > 0.001 or n_fail == 1 or bridged or any(ch["status"] == "WARN" for ch in chans):
        verdict = "USABLE WITH WARNINGS"
    else:
        verdict = "GOOD"
    return {"path": rec.path, "fs": fs, "duration_s": rec.duration, "channels": chans,
            "packet_loss": loss, "bridged_pairs": bridged, "rest_s": len(yr) / fs, "mvc_s": len(ym) / fs,
            "mvc_auto": mvc_auto, "verdict": verdict, "n_fail": n_fail}


def format_report(r):
    cols = [("noise_uv", "noise uV", "{:8.2f}"), ("line_uv", "line uV", "{:8.1f}"), ("lf_uv", "1-15Hz uV", "{:9.0f}"),
            ("dc_frac", "DC/FS", "{:6.2f}"), ("clip_frac", "clip", "{:7.1e}"), ("loff_frac", "loff", "{:6.3f}"),
            ("mvc_snr_db", "MVC SNR dB", "{:10.1f}")]
    lines = [f"{r['path']}: {r['duration_s']:.1f} s at {r['fs']:.0f} Hz, packet loss {r['packet_loss'] * 100:.2f} %, "
             f"rest {r['rest_s']:.0f} s, MVC {r['mvc_s']:.0f} s{' (auto: loudest 2 %)' if r['mvc_auto'] else ''}",
             "ch  " + " ".join(h.rjust(len(fmt.format(0))) + " " for _, h, fmt in cols) + " status"]
    mark = {"FAIL": "!", "WARN": "?"}
    for ch in r["channels"]:
        cells = [fmt.format(ch["metrics"][k]) + mark.get(ch["grades"][k], " ") for k, _, fmt in cols]
        lines.append(f"{ch['ch']:<3} " + " ".join(cells) + f" {ch['status']}{' FLAT' if ch['flat'] else ''}")
    if r["bridged_pairs"]:
        lines.append(f"possible electrode bridges (rest correlation > 0.95): {r['bridged_pairs']}")
    lines.append(f"verdict: {r['verdict']}   (! = fail, ? = warn; gates in analysis/quality.py)")
    return "\n".join(lines)
