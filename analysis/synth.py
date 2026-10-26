"""Synthetic 8-channel wrist sEMG with a known ground truth, for testing the pipeline.

Model (deliberately simple; not a physiological simulator):
  * C channels evenly around the wrist; channel c sits at (c + 0.5) / C turns from the
    ulnar gap, going over the dorsum, the radial side, the palm side and back.
  * A handful of muscle/tendon "sources" at fixed angles. Each gesture activates a mix
    of them. A source reaches channel c with a von Mises spatial spread (~1.2 pitches
    FWHM) plus a little volume-conducted crosstalk on every channel.
  * Source signal = band-limited noise with a typical sEMG spectrum (peak ~80-100 Hz)
    times an activation envelope. Channels also get independent EMG noise, amplifier
    noise, mains pickup and a drifting DC offset of tens of mV (DC-coupled dry electrodes).
  * Per session: band rotation (fraction of a pitch), per-channel contact gain, onset
    reaction times, trial-to-trial strength variation. Optional faults per channel.
The host clock runs at an offset (and 20 ppm drift) from the device clock, and marker
presses come ~250 ms after each sync cue, as with a real person.
"""
import numpy as np

from . import protocol as P
from .recording import Recording

# source name -> angle in turns from the ulnar gap (dorsal side first)
SOURCES = {"ECU": 0.06, "EDC": 0.22, "ECR": 0.36, "APL": 0.46, "FPL": 0.56,
           "FDS2": 0.64, "FDS3": 0.70, "FDP": 0.74, "FCR": 0.60, "FCU": 0.88}
SRC = list(SOURCES)

GESTURE_SOURCES = {
    "rest": {},
    "fist": {"FDS2": .7, "FDS3": .7, "FDP": .8, "FCU": .4, "FCR": .4, "EDC": .3, "ECR": .3},
    "open": {"EDC": .8, "ECR": .3, "APL": .5, "ECU": .3},
    "wrist_flex": {"FCR": .7, "FCU": .6, "FDS3": .3},
    "wrist_ext": {"ECR": .7, "ECU": .6, "EDC": .4},
    "radial_dev": {"ECR": .5, "FCR": .5, "APL": .6},
    "ulnar_dev": {"ECU": .6, "FCU": .7},
    "index_pinch": {"FDS2": .35, "FPL": .4, "APL": .1},
    "middle_pinch": {"FDS3": .35, "FPL": .4, "APL": .1},
    "thumb_click": {"FPL": .3, "APL": .25},
    "thumb_in": {"FPL": .35, "APL": .1, "FDS2": .1},
    "thumb_out": {"APL": .35, "FPL": .15, "EDC": .1},
    "thumb_up": {"APL": .4, "EDC": .2},
    "thumb_down": {"FPL": .4, "FDS2": .15},
    "mvc_fist": {"FDS2": 1, "FDS3": 1, "FDP": 1, "FCU": .7, "FCR": .7, "EDC": .5, "ECR": .5},
    "mvc_open": {"EDC": 1, "ECR": 1, "ECU": .9, "APL": .8},
    "pinch_ramp_index": {"FDS2": .8, "FPL": .9, "APL": .2},
    "pinch_ramp_middle": {"FDS3": .8, "FPL": .9, "APL": .2},
}
TAP_GESTURES = set(P.GESTURES_META)


def emg_noise(rng, n, m, fs, fl=60.0, fh=120.0):
    """[n, m] unit-RMS noise with the Shwedyk-type sEMG spectrum fh^4 f^2/((f^2+fl^2)(f^2+fh^2)^2)."""
    nfft = 1 << int(np.ceil(np.log2(max(n, 2))))
    f = np.fft.rfftfreq(nfft, 1.0 / fs)
    h = np.sqrt(fh ** 4 * f ** 2 / ((f ** 2 + fl ** 2) * (f ** 2 + fh ** 2) ** 2))
    out = np.empty((n, m))
    for j in range(m):
        w = np.fft.rfft(rng.standard_normal(nfft))
        v = np.fft.irfft(w * h, nfft)[:n]
        out[:, j] = v / v.std()
    return out


def spatial_weights(n_ch, rotation=0.0, kappa=6.0, crosstalk=0.05):
    """[C, M] gain from each source to each channel; rotation in channel pitches."""
    ang = (np.arange(n_ch) + 0.5 + rotation) / n_ch
    phi = np.array([SOURCES[s] for s in SRC])
    d = 2 * np.pi * (ang[:, None] - phi[None, :])
    return np.exp(kappa * (np.cos(d) - 1)) + crosstalk


def _envelope(n, fs, i0, i1, rise=0.08, fall=0.10):
    """Trapezoid 0..1 over samples [i0, i1) with smooth edges; returns (slice, values)."""
    r, f = int(rise * fs), int(fall * fs)
    a, b = max(0, i0), min(n, i1 + f)
    if b <= a:
        return slice(0, 0), np.zeros(0)
    k = np.arange(a, b)
    e = np.clip((k - i0) / max(r, 1), 0, 1) * np.clip((i1 + f - k) / max(f, 1), 0, 1)
    return slice(a, b), 0.5 - 0.5 * np.cos(np.pi * e)


def simulate(steps, fs=2000, n_ch=8, seed=0, rotation=0.0, faults=None, mvc_uv=250.0,
             host_offset=None, gain=6, vref=2.4, mains=50.0, session=0):
    """Play a protocol (list of steps from protocol.build) on a synthetic wrist.

    Returns a Recording with .labels filled exactly as analysis.collect would write them
    (host-clock times) plus a 'truth' entry with the true onsets on the device clock.
    faults: {channel: 'flat' | 'leadoff' | 'clip' | 'noisy' | 'line'}.
    """
    rng = np.random.default_rng(seed)
    host_offset = 1.7e9 + rng.uniform(0, 1e6) if host_offset is None else host_offset
    ppm = 20e-6
    to_host = lambda td: float(host_offset + td * (1 + ppm))

    # ---- timeline (device clock) -------------------------------------------------
    t = 2.0  # recorder runs a bit before the first prompt
    events, truth, marker_t, acts = [], [], [], []
    for i, s in enumerate(steps):
        k = s["kind"]
        ev = {"kind": k, "label": s["label"], "step": i, "rep": s.get("rep", 0)}
        if k == "sync":
            ev.update(t_cue=to_host(t), t_start=to_host(t), t_end=to_host(t + s["dur"]))
            marker_t.append(t + rng.normal(0.25, 0.04))
            t += s["dur"]
        elif k == "rest":
            ev.update(t_cue=to_host(t), t_start=to_host(t), t_end=to_host(t + s["dur"]))
            t += s["dur"]
        elif k in ("gesture", "mvc", "ramp"):
            go = t + s["prep"]
            ev.update(t_cue=to_host(t), t_start=to_host(go), t_end=to_host(go + s["hold"]))
            rt = max(0.12, rng.normal(0.30, 0.08))
            on = go + rt
            if s["label"] in TAP_GESTURES:
                off = on + rng.uniform(0.15, 0.35)
            else:
                off = go + s["hold"] + max(0.1, rng.normal(0.25, 0.06))
            scale = rng.uniform(0.8, 1.2) * (s.get("peak", 1.0))
            if s["label"] != "rest":
                acts.append((s["label"], on, off, scale, k == "ramp"))
            truth.append({"step": i, "label": s["label"], "onset": on, "offset": off})
            t = go + s["hold"] + s["rest"]
        else:  # text/typing: not simulated, just leave a gap
            ev.update(t_cue=to_host(t), t_start=to_host(t), t_end=to_host(t + 5.0))
            t += 5.0
        events.append(ev)
    T = t + 2.0
    n = int(T * fs)

    # ---- source envelopes [n, M] ---------------------------------------------------
    M = len(SRC)
    env = np.full((n, M), 0.003)  # tonic background
    for lab, on, off, scale, ramp in acts:
        sl, e = _envelope(n, fs, int(on * fs), int(off * fs))
        if ramp:  # triangular force ramp up to the peak and back
            u = np.linspace(0, 1, len(e))
            e = e * (1 - np.abs(2 * u - 1))
        for src, a in GESTURE_SOURCES[lab].items():
            jit = rng.uniform(0.85, 1.15)
            env[sl, SRC.index(src)] += a * scale * jit * e

    # ---- signals -------------------------------------------------------------------
    W = spatial_weights(n_ch, rotation)                       # [C, M]
    contact = np.exp(rng.normal(0, 0.2, n_ch))                # per-channel contact gain
    src_sig = emg_noise(rng, n, M, fs) * env                  # [n, M]
    shared = src_sig @ W.T                                    # [n, C]
    indep = emg_noise(rng, n, n_ch, fs) * (env @ W.T)
    amp = mvc_uv * 1e-6 / W.max()
    x = amp * contact * (0.7 * shared + 0.7 * indep)
    tt = np.arange(n) / fs
    x += rng.uniform(1.5, 3.0, n_ch) * 1e-6 * rng.standard_normal((n, n_ch))      # amp + contact noise
    line_amp = rng.uniform(2, 15, n_ch) * 1e-6
    ph = rng.uniform(0, 2 * np.pi, n_ch)
    x += line_amp * (np.sin(2 * np.pi * mains * tt[:, None] + ph) + 0.3 * np.sin(6 * np.pi * mains * tt[:, None] + ph))
    drift_f = rng.uniform(0.005, 0.1, (4, n_ch))                                 # slow half-cell drift
    dc_drift = (rng.uniform(1e-3, 4e-3, (4, n_ch)) * np.sin(2 * np.pi * drift_f * tt[:, None, None] +
                                                         rng.uniform(0, 6.3, (4, n_ch)))).sum(1)
    x += rng.uniform(-0.1, 0.1, n_ch) + dc_drift                                     # DC offset + drift

    fs_v = vref / gain
    loff = None
    for c, kind in (faults or {}).items():
        if kind == "flat":
            x[:, c] = 0.01 + 2e-8 * rng.standard_normal(n)
        elif kind == "leadoff":
            x[:, c] = fs_v * (1 - 2 ** -23)
            n_pkt = n // 20
            loff = np.zeros((n_pkt, n_ch), bool) if loff is None else loff
            loff[:, c] = True
        elif kind == "clip":
            k0 = int(n * 0.3)
            x[k0:k0 + int(fs * 2), c] += 0.6
        elif kind == "noisy":
            x[:, c] += 40e-6 * rng.standard_normal(n)
        elif kind == "line":
            x[:, c] += 400e-6 * np.sin(2 * np.pi * mains * tt + 0.3)
    x = np.clip(x, -fs_v, fs_v * (1 - 2 ** -23))
    lsb = 2 * vref / gain / 2 ** 24
    x = np.round(x / lsb) * lsb

    markers = np.array([int(round(m * fs)) for m in marker_t], dtype=np.int64)
    labels = {"version": 1, "protocol": "synthetic", "session": session, "clock": "host time.time()",
              "events": events, "truth": truth, "rotation": rotation}
    meta = {"rate": fs, "gain": gain, "vref": vref, "lsb_volts": lsb, "lost_packets": 0,
            "mode": "normal", "mains": mains, "transport": "synthetic", "started_host": to_host(0.0),
            "channels": [f"ch{i + 1}" for i in range(n_ch)]}
    return Recording(emg=x.astype(np.float32), fs=float(fs), t=tt, markers=markers, meta=meta,
                     loff=loff, labels=labels)


def make_dataset(out_dir, n_sessions=3, protocol="quick", fs=2000, seed=0, **kw):
    """Write n_sessions synthetic recordings (each a separate 'donning' with its own band
    rotation and contact gains) to out_dir; returns the paths."""
    import os
    from .recording import save
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    paths = []
    for s in range(n_sessions):
        steps = P.build(protocol, seed=seed * 100 + s)
        rec = simulate(steps, fs=fs, seed=seed * 100 + s, rotation=rng.normal(0, 0.25), session=s, **kw)
        rec.labels["protocol"] = protocol
        p = os.path.join(out_dir, f"synth_s{s:02d}.npz")
        save(p, rec)
        paths.append(p)
    return paths
