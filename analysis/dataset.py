"""Recording + labels -> labelled feature windows."""
import numpy as np

from . import filters as F
from .align import device_events
from .features import FEATURES, feature_matrix, window_features
from .recording import load


def fractional_rotate(emg, shift):
    """Approximate a band rotation of `shift` pods (may be fractional) by linear interpolation
    between neighbouring channels. Crude (mixing two channels also averages their noise),
    but it covers the sub-pitch shifts that happen at every donning of an 8-pod band."""
    k = int(np.floor(shift))
    f = shift - k
    a = np.roll(emg, k, axis=1)
    return a if f == 0 else (1 - f) * a + f * np.roll(emg, k + 1, axis=1)


def window_labels(t, events, guard=0.05, classes=None):
    """Label for each window centre time t (device s): the trial's label if the centre lies in
    its movement interval, '' otherwise. Returns (labels [W] str, trial [W] int, -1 = none)."""
    lab = np.full(len(t), "", dtype=object)
    trial = np.full(len(t), -1, dtype=int)
    for e in events:
        if e["kind"] != "gesture" or (classes and e["label"] not in classes):
            continue
        if e["label"] == "rest":
            a, b = e["t_start"] + 0.3, e["t_end"]
        elif e["detected"]:
            a, b = e["onset"], e["offset"]
        else:
            continue  # no movement found: label is unreliable, skip the trial
        if b - a > 2 * guard + 0.1:
            a, b = a + guard, b - guard
        sel = (t >= a) & (t <= b)
        lab[sel] = e["label"]
        trial[sel] = e["step"]
    return lab, trial


def windows(rec, win_ms=200.0, hop_ms=50.0, mains=None, which=FEATURES, classes=None,
            rotations=(0.0,), refine=True):
    """Feature windows for one recording. Returns dict X [W, F*C], y [W] str, trial [W],
    t [W], session (str), events, plus counts. `rotations`: extra fractional band rotations
    to add as augmented copies (use only for training data)."""
    if isinstance(rec, str):
        rec = load(rec)
    mains = mains if mains is not None else rec.meta.get("mains", 50.0) or 50.0
    y = F.bandpass_notch(rec.emg, rec.fs, 20, 450, mains)
    events = device_events(rec, y=y, refine=refine)
    Xs, ys, trs, ts = [], [], [], []
    for r in rotations:
        yr = fractional_rotate(y, r) if r else y
        fe = window_features(yr, rec.fs, win_ms, hop_ms, which=which)
        lab, trial = window_labels(fe["t"], events, classes=classes)
        keep = lab != ""
        Xs.append(feature_matrix(fe, which)[keep])
        ys.append(lab[keep].astype(str))
        trs.append(trial[keep])
        ts.append(fe["t"][keep])
    n_trials = sum(e["kind"] == "gesture" for e in events)
    n_det = sum(e["kind"] == "gesture" and (e["detected"] or e["label"] == "rest") for e in events)
    session = str((rec.labels or {}).get("session", rec.path))
    return {"X": np.concatenate(Xs), "y": np.concatenate(ys), "trial": np.concatenate(trs),
            "t": np.concatenate(ts), "session": session, "events": events,
            "n_trials": n_trials, "n_used": n_det, "n_channels": rec.n_channels}
