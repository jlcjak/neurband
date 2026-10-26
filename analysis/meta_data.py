"""Read Meta's open sEMG datasets (needs h5py; pandas only for GNI prompt tables) into the
same Recording type as our band, optionally reduced to our 8-channel layout.

  generic-neuromotor-interface  HDF5 dataset 'data': fields emg (16,), time [, wrist_angles (2,)]
                                + pandas tables 'prompts', 'stages'
  emg2qwerty                    group 'emg2qwerty', dataset 'timeseries': emg_left/emg_right (16,),
                                time; attrs incl. 'keystrokes' (JSON)
  emg2pose                      group 'emg2pose', dataset 'timeseries': emg (16,), joint_angles (20,), time

All three store EMG at 2 kHz, 40 Hz high-passed, scaled so the noise floor has std ~1
(i.e. units of ~2.46 uV, the sEMG-RD's input noise); left-hand data are sign-flipped.
We multiply by NOISE_UNIT to get approximate volts, so thresholds and features computed
on our recordings mean the same thing on theirs. Channel 0 and 15 sit either side of the
ulnar gap; indices increase around the wrist (the direction relative to our pod 1 must be
checked, see docs/science/data_and_models.md section b).
"""
import json

import numpy as np

from .filters import subsample_16_to_8
from .recording import Recording

NOISE_UNIT = 2.46e-6  # volts per dataset unit (inferred, not stated by Meta)


def load_meta_hdf5(path, band="right", n_channels=8, offset=0, max_samples=None):
    """Return a Recording (emg in approximate volts) plus dataset labels in rec.meta['extra'].
    n_channels: 16 keeps everything, 8 takes every other channel starting at `offset`."""
    import h5py
    extra = {}
    with h5py.File(path, "r") as f:
        if "emg2qwerty" in f:
            g = f["emg2qwerty"]
            ts = g["timeseries"][:max_samples]
            emg = ts["emg_right" if band == "right" else "emg_left"]
            attrs = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in g.attrs.items()}
            if "keystrokes" in attrs:
                extra["keystrokes"] = json.loads(attrs["keystrokes"])
            source = "emg2qwerty"
        elif "emg2pose" in f:
            g = f["emg2pose"]
            ts = g["timeseries"][:max_samples]
            emg = ts["emg"]
            extra["joint_angles"] = np.asarray(ts["joint_angles"])
            attrs = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in g.attrs.items()}
            source = "emg2pose"
        elif "data" in f:
            ts = f["data"][:max_samples]
            emg = ts["emg"]
            if "wrist_angles" in ts.dtype.names:
                extra["wrist_angles"] = np.asarray(ts["wrist_angles"])
            attrs = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in f["data"].attrs.items()}
            source = "generic-neuromotor-interface"
            if "prompts" in f:
                try:
                    import pandas as pd
                    extra["prompts"] = pd.read_hdf(path, "prompts").to_dict("records")
                except ImportError:
                    extra["prompts"] = "install pandas + tables to read"
        else:
            raise ValueError(f"{path}: not a recognised Meta sEMG file")
        t_abs = np.asarray(ts["time"], dtype=np.float64)
    emg = np.asarray(emg, dtype=np.float32) * NOISE_UNIT
    if n_channels == 8:
        emg = subsample_16_to_8(emg, offset)
    fs = float(round(1.0 / np.median(np.diff(t_abs[: min(len(t_abs), 10000)]))))
    meta = {"rate": fs, "source": source, "t0_unix": float(t_abs[0]), "noise_unit_v": NOISE_UNIT,
            "channel_offset": offset, "attrs": {k: str(v)[:200] for k, v in attrs.items()}, "extra": extra,
            "mains": 0.0}  # already high-passed at 40 Hz; mains not an issue in their data
    return Recording(emg=emg, fs=fs, t=t_abs - t_abs[0], markers=np.zeros(0, np.int64), meta=meta,
                     path=str(path))
