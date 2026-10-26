"""Windowed time-domain sEMG features (Hudgins et al. 2003 set + RMS).

Input: band-passed EMG [N, C] in volts. Output: [W, C] per feature, W windows.
Defaults 200 ms windows every 50 ms. Smith et al. 2011 (TNSRE 19:186) found TD+LDA error
plateaus for windows >= 150 ms, with 150-250 ms optimal. Farrell & Weir 2007 put the best
controller delay at ~100-125 ms.
"""
import numpy as np

FEATURES = ("rms", "mav", "wl", "zc", "ssc")


def frame(x, fs, win_ms=200.0, hop_ms=50.0):
    """Strided view [W, C, L] of x [N, C] and the window centre times [W] in seconds."""
    x = np.asarray(x, dtype=np.float64)
    L = int(round(win_ms * fs / 1000))
    H = int(round(hop_ms * fs / 1000))
    if len(x) < L:
        return np.zeros((0, x.shape[1], L)), np.zeros(0)
    v = np.lib.stride_tricks.sliding_window_view(x, L, axis=0)[::H]  # [W, C, L]
    centres = (np.arange(v.shape[0]) * H + L / 2) / fs
    return v, centres


def noise_threshold(x, fs, win_ms=200.0, pct=10):
    """Per-channel noise level: a low percentile of window RMS (the quietest windows)."""
    v, _ = frame(x, fs, win_ms, win_ms)
    if len(v) == 0:
        return np.full(np.shape(x)[1], 1e-6)
    return np.percentile(np.sqrt(np.mean(v ** 2, axis=-1)), pct, axis=0)


def window_features(x, fs, win_ms=200.0, hop_ms=50.0, thr=None, which=FEATURES):
    """Dict feature -> [W, C], plus 't' (window centres, s).

    thr: amplitude threshold (volts, scalar or per channel) for ZC and SSC so noise does
    not count; default = the channel's noise level (see noise_threshold).
    ZC and SSC are returned as rates (counts per second) so they do not depend on the window.
    """
    v, centres = frame(x, fs, win_ms, hop_ms)
    if thr is None:
        thr = noise_threshold(x, fs, win_ms)
    thr = np.broadcast_to(np.asarray(thr, dtype=float), (v.shape[1],))[None, :, None]
    dur = v.shape[-1] / fs
    out = {"t": centres}
    if "rms" in which:
        out["rms"] = np.sqrt(np.mean(v ** 2, axis=-1))
    if "mav" in which:
        out["mav"] = np.mean(np.abs(v), axis=-1)
    if "wl" in which or "zc" in which:
        d = np.diff(v, axis=-1)
    if "wl" in which:
        out["wl"] = np.sum(np.abs(d), axis=-1) / dur
    if "zc" in which:
        out["zc"] = np.sum((v[..., :-1] * v[..., 1:] < 0) & (np.abs(d) >= thr), axis=-1) / dur
    if "ssc" in which:
        a, b = v[..., 1:-1] - v[..., :-2], v[..., 1:-1] - v[..., 2:]
        # extremum whose two slopes beat those of a 150 Hz wave of amplitude thr: keeps the
        # meaning of thr the same at 2 and 4 kHz (a raw product threshold scales as fs^-4)
        s_thr = thr * 2 * np.pi * 150.0 / fs
        out["ssc"] = np.sum(a * b >= s_thr ** 2, axis=-1) / dur
    return out


def feature_matrix(feats, which=FEATURES, log_amp=True):
    """Stack a window_features dict into X [W, F*C] (feature-major). Amplitude features
    (RMS, MAV, WL) are log-transformed: closer to Gaussian, which suits LDA, and a
    per-channel contact gain change becomes an additive offset."""
    cols = []
    for k in which:
        a = feats[k]
        if log_amp and k in ("rms", "mav", "wl"):
            a = np.log(np.maximum(a, 1e-12))
        cols.append(a)
    return np.concatenate(cols, axis=1) if cols else np.zeros((0, 0))
