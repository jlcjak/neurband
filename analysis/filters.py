"""Offline zero-phase filters for sEMG.

Two implementations give the same magnitude response:
  * scipy installed: Butterworth / iirnotch second-order sections run forward-backward
    (sosfiltfilt), edges handled by scipy's odd padding.
  * numpy only: the squared magnitude of the same filters applied in the FFT domain after
    reflect-padding. A forward-backward IIR filter has exactly |H|^2 and zero phase, so
    the two agree except within a few samples of the ends.
Both are for offline analysis. A real-time decoder needs causal filters (see docs).
"""
import numpy as np

try:  # optional
    from scipy import signal as _sig
except ImportError:  # pragma: no cover - depends on the environment
    _sig = None

HAVE_SCIPY = _sig is not None


# ------------------------------------------------------------------ responses
def _butter_mag2(f, fs, fc, order, kind):
    """|H|^2 of a digital Butterworth designed by the bilinear transform."""
    w = np.tan(np.pi * np.clip(f, 0, fs / 2 * 0.999999) / fs)
    wc = np.tan(np.pi * fc / fs)
    with np.errstate(divide="ignore"):
        r = w / wc if kind == "low" else wc / np.maximum(w, 1e-300)
    return 1.0 / (1.0 + np.minimum(r, 1e30) ** (2 * order))


def _notch_ba(f0, fs, q):
    """Same coefficients as scipy.signal.iirnotch(f0, q, fs)."""
    w0 = 2 * np.pi * f0 / fs
    beta = np.tan(w0 / q / 2)
    g = 1.0 / (1.0 + beta)
    return g * np.array([1.0, -2 * np.cos(w0), 1.0]), np.array([1.0, -2 * g * np.cos(w0), 2 * g - 1])


def _notch_mag2(f, fs, f0, q):
    b, a = _notch_ba(f0, fs, q)
    z = np.exp(-2j * np.pi * f / fs)
    h = (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
    return np.abs(h) ** 2


def mains_harmonics(mains, fs, f_max=None):
    f_max = min(f_max or fs / 2, fs / 2 * 0.98)
    return [] if not mains else list(np.arange(mains, f_max, mains))


def response(f, fs, lo=20.0, hi=450.0, mains=50.0, order=4, q=30.0, notch_max=None):
    """Zero-phase power response of `bandpass_notch` at frequencies f (for plots/tests)."""
    f = np.asarray(f, dtype=float)
    g = np.ones_like(f)
    if lo:
        g *= _butter_mag2(f, fs, lo, order, "high")
    if hi:
        g *= _butter_mag2(f, fs, hi, order, "low")
    for h in mains_harmonics(mains, fs, notch_max or hi or fs / 2):
        g *= _notch_mag2(f, fs, h, q)
    return g


# ------------------------------------------------------------------ filtering
def _fft_apply(x, fs, gain_fn, pad):
    n = x.shape[0]
    pad = min(pad, n - 1)
    out = np.empty(x.shape, dtype=np.float64)
    for c in range(x.shape[1]):  # one channel at a time keeps memory low
        v = x[:, c].astype(np.float64)
        v = v - v.mean()
        v = np.concatenate([2 * v[0] - v[pad:0:-1], v, 2 * v[-1] - v[-2:-pad - 2:-1]])  # odd reflection
        m = len(v)
        nfft = 1 << int(np.ceil(np.log2(m)))
        V = np.fft.rfft(v, nfft)
        V *= gain_fn(np.fft.rfftfreq(nfft, 1.0 / fs))
        out[:, c] = np.fft.irfft(V, nfft)[pad:pad + n]
    return out


def bandpass_notch(x, fs, lo=20.0, hi=450.0, mains=50.0, order=4, q=30.0, use_scipy=None):
    """Zero-phase band-pass (lo..hi Hz, Butterworth of `order` per edge, run forward-backward)
    plus notches at the mains frequency and its harmonics up to `hi`.

    x: [N, C] (or [N]) array in volts. lo/hi/mains = 0 or None disables that stage.
    Returns float64 of the same shape.
    """
    x = np.asarray(x)
    one_d = x.ndim == 1
    if one_d:
        x = x[:, None]
    if len(x) < 16:
        return np.zeros(x.shape)
    use_scipy = HAVE_SCIPY if use_scipy is None else use_scipy
    notches = mains_harmonics(mains, fs, hi or fs / 2)
    if use_scipy:
        y = x.astype(np.float64) - x.mean(axis=0)
        sos = []
        if lo:
            sos.append(_sig.butter(order, lo, "highpass", fs=fs, output="sos"))
        if hi:
            sos.append(_sig.butter(order, hi, "lowpass", fs=fs, output="sos"))
        for h in notches:
            sos.append(_sig.tf2sos(*_notch_ba(h, fs, q)))
        if sos:
            y = _sig.sosfiltfilt(np.vstack(sos), y, axis=0)
    else:
        pad = int(min(len(x) - 1, max(3 * fs / (lo or 10.0), q * fs / (mains or 50.0))))
        y = _fft_apply(x, fs, lambda f: response(f, fs, lo, hi, mains, order, q), pad)
    return y[:, 0] if one_d else y


def band_rms(x, fs, lo, hi):
    """RMS of x [N, C] in a frequency band, from the periodogram (no filtering edge effects)."""
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean(axis=0)
    X = np.fft.rfft(x * np.hanning(len(x))[:, None], axis=0)
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    p = np.abs(X) ** 2
    p[1:-1] *= 2
    p /= np.sum(np.hanning(len(x)) ** 2) * len(x)
    sel = (f >= lo) & (f <= hi)
    return np.sqrt(p[sel].sum(axis=0))


def line_rms(x, fs, mains=50.0, f_max=None, half_width=1.0):
    """RMS of the narrow-band mains content (fundamental + harmonics), per channel, volts."""
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean(axis=0)
    win = np.hanning(len(x))[:, None]
    X = np.fft.rfft(x * win, axis=0)
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    p = np.abs(X) ** 2 * 2 / (np.sum(win ** 2) * len(x))
    sel = np.zeros(len(f), bool)
    for h in mains_harmonics(mains, fs, f_max):
        sel |= np.abs(f - h) <= half_width
    return np.sqrt(p[sel].sum(axis=0))


# ------------------------------------------------------------------ resampling / channels
def decimate(x, factor):
    """Integer-factor downsampling with an FFT brick-wall anti-alias filter at 0.45 * new fs."""
    x = np.asarray(x, dtype=np.float64)
    if factor == 1:
        return x
    n = len(x) - len(x) % factor
    X = np.fft.rfft(x[:n], axis=0)
    f = np.fft.rfftfreq(n, 1.0)
    X[f > 0.45 / factor] = 0
    return np.fft.irfft(X, n, axis=0)[::factor]


def subsample_16_to_8(emg16, offset=0):
    """Meta's 16 bipolar channels -> 8, taking every other channel (offset 0 or 1).

    Their electrodes have the same size and 20 mm spacing as ours, at half our pitch, so
    alternate channels are the closest physical match to an 8-pod band. Using both offsets
    doubles the data and acts like a half-pitch rotation.
    """
    return np.asarray(emg16)[:, offset::2]


def rotate_channels(emg, shift):
    """Circular channel shift = band rotated by `shift` pods (data augmentation)."""
    return np.roll(emg, shift, axis=-1)
