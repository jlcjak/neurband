"""Put prompt times (host clock, written by collect.py) onto the recording's device clock.

1. Clock fit. collect.py shows "press the band button" cues at the start and end of every
   run; each press arrives in the recording as a marker. A press follows its cue by a
   reaction time (~0.25 s). We find the host->device offset that matches the most
   cues to markers (robust to missed or extra presses), then fit offset (and drift, if
   the run is long enough) by least squares. Typical error: the spread of the reaction
   time, ~30-50 ms.
2. Onset refinement. Per trial, the EMG envelope says when the person really moved
   (reaction times vary 0.2-0.5 s). That moves each label onto the movement, a much
   simplified version of the time alignment Meta used for their discrete gestures.
"""
import datetime

import numpy as np


class Clock:
    """t_dev = a * (t_host - h0) + b."""

    def __init__(self, a, b, h0, method, n_pairs=0, resid_ms=float("nan")):
        self.a, self.b, self.h0, self.method = a, b, h0, method
        self.n_pairs, self.resid_ms = n_pairs, resid_ms

    def to_device(self, t_host):
        return self.a * (np.asarray(t_host, dtype=float) - self.h0) + self.b

    def __repr__(self):
        return (f"Clock({self.method}, pairs={self.n_pairs}, drift={(self.a - 1) * 1e6:+.1f} ppm, "
                f"resid={self.resid_ms:.1f} ms)")


def fit_clock(cue_host, marker_dev, rt=0.25, tol=0.35, min_span_for_drift=120.0):
    """Match sync cues (host s) to marker presses (device s)."""
    cue = np.asarray(cue_host, dtype=float)
    mk = np.asarray(marker_dev, dtype=float)
    if len(cue) == 0 or len(mk) == 0:
        return None
    h0 = cue[0]
    c = cue - h0 + rt
    cand = (mk[:, None] - c[None, :]).ravel()  # every cue/marker pairing proposes an offset
    best, best_n = None, 0
    for off in cand:
        d = np.abs(mk[:, None] - (c[None, :] + off))
        n = int(np.sum(d.min(axis=0) < tol))
        if n > best_n or (n == best_n and best is not None and
                          np.abs(d.min(axis=0)[d.min(axis=0) < tol]).sum() < best[1]):
            best_n, best = n, (off, np.abs(d.min(axis=0)[d.min(axis=0) < tol]).sum())
    off = best[0]
    d = np.abs(mk[:, None] - (c[None, :] + off))
    j = np.where(d.min(axis=0) < tol)[0]            # matched cues
    i = d[:, j].argmin(axis=0)                      # their markers
    x, y = c[j], mk[i]
    if len(j) >= 4 and np.ptp(x) >= min_span_for_drift:
        a, b = np.polyfit(x, y, 1)
    else:
        a, b = 1.0, float(np.median(y - x))
    resid = y - (a * x + b)
    # x was the host time of each press (cue + rt) - h0, so the fit maps host to device time
    return Clock(a, b, h0, "markers", len(j), float(np.std(resid) * 1e3))


def clock_from_meta(meta):
    """Fallback without markers: the recorder's start time (host wall clock) = device t 0.
    Error = command latency + first packet delay, typically tens of ms on a LAN."""
    if "started_host" in meta:
        h0 = float(meta["started_host"])
    elif "started" in meta:
        h0 = datetime.datetime.fromisoformat(meta["started"]).timestamp()
    else:
        return None
    return Clock(1.0, 0.0, h0, "recorder start time")


def make_clock(rec, rt=0.25):
    lab = rec.labels or {}
    cues = [e["t_start"] for e in lab.get("events", []) if e["kind"] == "sync"]
    mt = rec.marker_t
    src = rec.marker_src if rec.marker_src is not None and len(rec.marker_src) == len(mt) else np.zeros(len(mt), int)
    clk = None
    if len(cues) and np.any(src == 1):
        # software markers are stamped by the recorder at the cue itself: no human reaction time
        clk = fit_clock(cues, mt[src == 1], rt=0.0)
    if (clk is None or clk.n_pairs < 2) and len(cues) and np.any(src == 0):
        clk = fit_clock(cues, mt[src == 0], rt=rt)
    if clk is None or clk.n_pairs < 2:
        clk = clock_from_meta(rec.meta) or clk
    if clk is None:
        raise ValueError(f"{rec.path}: no sync markers and no start time; cannot align labels")
    return clk


def envelope(y, fs, smooth_ms=50.0):
    """Channel-averaged RMS envelope of band-passed EMG y [N, C]."""
    p = np.mean(np.asarray(y, dtype=float) ** 2, axis=1)
    k = max(1, int(smooth_ms * fs / 1000))
    e = np.convolve(p, np.ones(k) / k, mode="same")
    return np.sqrt(e)


def device_events(rec, clock=None, y=None, refine=True, search=(0.05, 1.2), frac=0.25):
    """Events with device-clock times: t_cue, t_start, t_end (prompt) and onset/offset
    (movement, refined from the EMG when `refine` and `y` (band-passed EMG) are given)."""
    clock = clock or make_clock(rec)
    env = envelope(y, rec.fs) if (refine and y is not None) else None
    out = []
    for e in (rec.labels or {}).get("events", []):
        d = dict(e)
        for k in ("t_cue", "t_start", "t_end"):
            d[k] = float(clock.to_device(e[k]))
        d["onset"], d["offset"], d["detected"] = d["t_start"] + 0.3, d["t_end"] + 0.25, False
        if env is not None and e["kind"] in ("gesture", "mvc", "ramp") and e["label"] != "rest":
            i_c, i_s, i_e = (int(d[k] * rec.fs) for k in ("t_cue", "t_start", "t_end"))
            pre = env[max(0, i_c): max(i_c + 1, i_s)]
            post = env[max(0, i_s): min(len(env), i_e + int(rec.fs))]
            if len(pre) and len(post):
                base, peak = np.median(pre), np.percentile(post, 95)
                if peak > 2.0 * base:
                    thr = base + frac * (peak - base)
                    a, b = i_s + int(search[0] * rec.fs), min(len(env), i_s + int(search[1] * rec.fs))
                    above = np.where(env[a:b] > thr)[0]
                    if len(above):
                        on = a + above[0]
                        seg = env[on: min(len(env), i_e + int(rec.fs))] > thr
                        off = on + (np.where(seg)[0][-1] if seg.any() else 0)
                        d["onset"], d["offset"], d["detected"] = on / rec.fs, off / rec.fs, True
        out.append(d)
    return out
