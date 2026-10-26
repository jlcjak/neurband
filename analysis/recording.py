"""Recording and label files.

A recording is the .npz written by host/neurband_rec.py (rev C keeps the same keys):
  emg [N, C] float32 volts, t [N] s (device clock), markers [K] sample index,
  marker_t [K] s, meta JSON string (rate, gain, vref, lost_packets, ...),
  optional loff_p/loff_n/pkt_* per packet.
Labels written by analysis.collect sit beside it as <name>.labels.json.
"""
import json
import os
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Recording:
    emg: np.ndarray                 # [N, C] volts
    fs: float                       # samples/s
    t: np.ndarray                   # [N] s, device clock
    markers: np.ndarray             # [K] sample indices of marker presses
    meta: dict = field(default_factory=dict)
    loff: np.ndarray = None         # [P, C] bool lead-off per packet, or None
    labels: dict = None             # contents of the .labels.json, or None
    path: str = ""
    marker_src: np.ndarray = None   # [K] 0 = band button, 1 = software (host) marker; None = all button

    @property
    def n_channels(self):
        return self.emg.shape[1]

    @property
    def duration(self):
        return len(self.emg) / self.fs

    @property
    def full_scale(self):
        """Input full scale in volts (+-VREF/gain), or None if unknown."""
        if "vref" in self.meta and "gain" in self.meta:
            return self.meta["vref"] / self.meta["gain"]
        return None

    @property
    def marker_t(self):
        return self.t[self.markers] if len(self.markers) else np.zeros(0)


def labels_path(npz_path):
    base = npz_path[:-4] if npz_path.endswith(".npz") else npz_path
    return base + ".labels.json"


def _unpack_bits(words, n_ch):
    words = np.asarray(words, dtype=np.int64)
    return ((words[:, None] >> np.arange(n_ch)) & 1).astype(bool)


def load(path, labels=True):
    """Load a recorder .npz (and its .labels.json if present)."""
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"])) if "meta" in z else {}
    emg = np.asarray(z["emg"])
    fs = float(meta.get("rate", 0)) or float(1.0 / np.median(np.diff(z["t"][:1000])))
    t = np.asarray(z["t"]) if "t" in z else np.arange(len(emg)) / fs
    markers = np.asarray(z["markers"], dtype=np.int64) if "markers" in z else np.zeros(0, np.int64)
    loff = None
    if "loff_p" in z and "loff_n" in z:
        c = emg.shape[1]
        loff = _unpack_bits(z["loff_p"], c) | _unpack_bits(z["loff_n"], c)
    lab = None
    lp = labels_path(path)
    if labels and os.path.exists(lp):
        with open(lp) as f:
            lab = json.load(f)
    msrc = np.asarray(z["marker_src"], dtype=np.int64) if "marker_src" in z else None
    return Recording(emg=emg, fs=fs, t=t, markers=markers, meta=meta, loff=loff, labels=lab, path=path,
                     marker_src=msrc)


def save(path, rec):
    """Write a Recording in the recorder's .npz format (used by the synthetic generator)."""
    meta = dict(rec.meta, rate=rec.fs, n_samples=int(len(rec.emg)))
    extra = {}
    if rec.loff is not None:
        w = (rec.loff.astype(np.int64) << np.arange(rec.loff.shape[1])).sum(1)
        extra = dict(loff_p=w.astype(np.uint16), loff_n=np.zeros_like(w, dtype=np.uint16))
    np.savez(path, emg=rec.emg.astype(np.float32), t=rec.t, markers=rec.markers.astype(np.int64),
             marker_t=rec.t[rec.markers] if len(rec.markers) else np.zeros(0), meta=json.dumps(meta), **extra)
    if rec.labels is not None:
        save_labels(labels_path(path), rec.labels)


def save_labels(path, labels):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(labels, f, indent=1)
    os.replace(tmp, path)
