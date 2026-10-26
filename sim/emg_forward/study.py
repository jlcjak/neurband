"""Run the neurband forward-model study: MUAPs, sensitivity matrices, coverage, rotation,
electrode size / IED / noise, expected amplitudes.  Results -> cache/results.json + cache/study.npz.

    python3 study.py            (needs the lead fields from leadfield.py; computes missing ones)
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "4")
import json
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geometry import build_model, MUSCLES, Electrode, Z_BAND  # noqa: E402
from leadfield import study_electrodes, compute, LeadFieldSet, CACHE  # noqa: E402
from sources import build_pools, muap, FS, T_MUAP  # noqa: E402

BAND = (20.0, 450.0)
NFFT = 1024                       # 256 ms analysis window at 4 kHz
FREQ = np.fft.rfftfreq(NFFT, 1 / FS)
INB = (FREQ >= BAND[0]) & (FREQ <= BAND[1])
NB = INB.sum()
K_B = 1.380649e-23
T_K = 305.0

# ---------------------------------------------------------------- noise budget inputs (signal_chain.md)
ADS_NOISE_UV = 1.5          # ADS1298 HR 4 kSPS typical total shorted-input noise (datasheet Table 1)
RES_NOISE_UV = 0.26         # 2 x 4.7 kOhm input resistors, 20-450 Hz
MAINS_GATE_UV = 5.0         # on-body acceptance gate for differential mains residual
VIS = ["FDS", "FDP", "FPL", "FCU", "PQ", "APL_EPB", "EPL", "EDC", "EIP", "EDM", "ECU"]   # muscle at the band
ALL = [m.name for m in MUSCLES]


def rate(E, thr):
    """Firing rate (Hz) at excitation E (% MVC): Fuglevand-style, 8 Hz at threshold, +1 Hz/%, cap 30 Hz."""
    return np.where(thr <= E, np.minimum(8.0 + 1.0 * (E - thr), 30.0), 0.0)


class Study:
    def __init__(self, h=(0.5, 0.5, 1.0), seed=1, variant="", variant_kwargs=None, pool_model=None,
                 electrodes=None):
        self.model = build_model(h=h, **(variant_kwargs or {}))
        els, self.s_mid = study_electrodes(self.model.outline)
        if electrodes is not None:
            els = electrodes(els)
        self.els = els
        paths = compute(els, h=h, variant=variant, variant_kwargs=variant_kwargs)
        self.lfs = LeadFieldSet(self.model, paths, [e.key() for e in els])
        pm = pool_model or self.model
        self.pools = build_pools(pm, np.random.default_rng(seed))
        self.t = np.arange(int(T_MUAP * FS)) / FS
        self._mono = {}
        default = (tuple(h) == (0.5, 0.5, 1.0) and not variant and electrodes is None and pool_model is None
                   and seed == 1)
        self._mono_path = os.path.join(CACHE, "mono_baseline.npz") if default else None
        if self._mono_path and os.path.exists(self._mono_path):
            z = np.load(self._mono_path)
            if z["n_el"] == len(self.els):
                self._mono = {k: z[k] for k in z.files if k != "n_el"}

    # ---------------------------------------------------------------- electrodes / configurations
    def find(self, s, z, kind="disc6.5"):
        C = self.model.outline.circ
        best, bd = None, 1e9
        for i, e in enumerate(self.els):
            if e.kind != kind or abs(e.z - z) > 1e-6:
                continue
            d = abs((e.s - s + C / 2) % C - C / 2)
            if d < bd:
                best, bd = i, d
        if bd > 0.05:
            raise KeyError((s, z, kind, bd))
        return best

    def config(self, n=8, pitch=18.0, offset=0.0, ied=20.0, kind="disc6.5"):
        C = self.model.outline.circ
        s = np.mod(self.s_mid + (np.arange(n) - (n - 1) / 2) * pitch + offset, C)
        P = [self.find(si, Z_BAND + ied / 2, kind) for si in s]
        N = [self.find(si, Z_BAND - ied / 2, kind) for si in s]
        return np.array(P), np.array(N), s

    # ---------------------------------------------------------------- MUAPs
    def mono(self, name):
        if name not in self._mono:
            self._mono[name] = np.stack([muap(mu, self.lfs, self.t) for mu in self.pools[name]]).astype(np.float32)
        return self._mono[name]          # (n_mu, n_el, n_t) volts

    def all_mono(self):
        missing = [m for m in self.pools if m not in self._mono]
        for m in self.pools:
            self.mono(m)
        if missing and self._mono_path:
            np.savez(self._mono_path, n_el=len(self.els), **self._mono)

    def bip(self, name, cfg):
        P, N, _ = cfg
        M = self.mono(name)
        return M[:, P] - M[:, N]           # (n_mu, n_ch, n_t)

    @staticmethod
    def band_energy(x):
        """Energy (V^2 s) of x[..., t] inside BAND (one-sided Parseval, zero-padded to NFFT)."""
        X = np.fft.rfft(x, NFFT, axis=-1)
        return 2.0 * (np.abs(X[..., INB]) ** 2).sum(-1) / NFFT / FS

    def thresholds(self, name):
        return np.array([mu.threshold for mu in self.pools[name]])

    def rms(self, name, cfg, E):
        """Interference-EMG RMS (V) per channel, BAND-limited, muscle `name` alone at E % MVC (Campbell)."""
        en = self.band_energy(self.bip(name, cfg))          # (n_mu, n_ch)
        r = rate(E, self.thresholds(name))
        return np.sqrt((r[:, None] * en).sum(0))

    def psd(self, name, cfg, E):
        X = np.fft.rfft(self.bip(name, cfg), NFFT, axis=-1)
        r = rate(E, self.thresholds(name))
        return (r[:, None, None] * np.abs(X) ** 2).sum(0) * 2 / FS   # V^2/Hz one-sided (Campbell)

    def sens(self, cfg, E=10.0, names=ALL):
        return np.stack([self.rms(n, cfg, E) for n in names], 1)    # (n_ch, n_mus)

    # ---------------------------------------------------------------- trial synthesis (all electrodes at once)
    def spectra_cache(self, names):
        self._F = {n: np.fft.rfft(self.mono(n), NFFT, axis=-1)[..., INB].astype(np.complex64) for n in names}

    def synth(self, name, E, rng):
        """Monopolar band-limited spectra (n_el, NB) of one 256 ms window, muscle `name` at E % MVC."""
        thr = self.thresholds(name)
        r = rate(E, thr)
        act = np.flatnonzero(r > 0)
        f = FREQ[INB]
        T = NFFT / FS
        S = np.zeros((len(act), NB), np.complex64)
        for j, i in enumerate(act):
            isi = 1.0 / r[i]
            n = int(T / isi) + 3
            ts = rng.uniform(0, isi) + np.cumsum(np.r_[0, isi * (1 + 0.2 * rng.standard_normal(n - 1)).clip(0.3)])
            ts = ts[ts < T]
            S[j] = np.exp(-2j * np.pi * np.outer(ts, f)).sum(0)
        F = self._F[name][act]                                   # (n_act, n_el, NB)
        return np.einsum("af,aef->ef", S, F)

    def features(self, Xmono, cfg, noise_uv, rng, gain_jitter=0.0):
        """log RMS (uV) per channel of one window with white in-band noise of `noise_uv` RMS."""
        P, N, _ = cfg
        X = Xmono[P] - Xmono[N]
        sig = noise_uv * 1e-6 * NFFT / np.sqrt(2 * NB)
        X = X + sig / np.sqrt(2) * (rng.standard_normal(X.shape) + 1j * rng.standard_normal(X.shape))
        p = 2.0 * (np.abs(X) ** 2).sum(-1) / NFFT ** 2
        g = 1.0 + gain_jitter * rng.standard_normal(len(P)) if gain_jitter else 1.0
        return np.log(np.sqrt(p) * 1e6 * g)


# ---------------------------------------------------------------- classifier
def lda_fit(X, y, shrink=0.05):
    cls = np.unique(y)
    mu = np.stack([X[y == c].mean(0) for c in cls])
    Xc = X - mu[np.searchsorted(cls, y)]
    S = Xc.T @ Xc / (len(X) - len(cls))
    S = (1 - shrink) * S + shrink * np.trace(S) / S.shape[0] * np.eye(S.shape[0])
    W = np.linalg.solve(S, mu.T)
    b = -0.5 * (mu * W.T).sum(1)
    return cls, W, b


def lda_predict(model, X):
    cls, W, b = model
    return cls[np.argmax(X @ W + b, 1)]


def confusion_mi(y, yp, ncls):
    C = np.zeros((ncls, ncls))
    np.add.at(C, (y, yp), 1)
    P = C / C.sum()
    px, py = P.sum(1, keepdims=True), P.sum(0, keepdims=True)
    nz = P > 0
    return float((P[nz] * np.log2(P[nz] / (px @ py)[nz])).sum()), C


# ---------------------------------------------------------------- electrode / contact noise
def rc_from_two_points(z1, f1, z2, f2):
    """Fit R||C to two |Z| magnitudes."""
    w1, w2 = 2 * np.pi * f1, 2 * np.pi * f2
    tau2 = (z1 ** 2 - z2 ** 2) / (z2 ** 2 * w2 ** 2 - z1 ** 2 * w1 ** 2)
    tau = np.sqrt(tau2)
    R = z1 * np.sqrt(1 + (w1 * tau) ** 2)
    return R, tau / R


# Yamagami et al. 2018: 5x1 mm gold, settled: 252 kOhm @53 Hz, 139 kOhm @151 Hz (0.05 cm^2)
_R, _C = rc_from_two_points(252e3, 53, 139e3, 151)
CONTACT = {
    "settled gold (Yamagami 2018 fit)": dict(RA=_R * 0.05, CA=_C / 0.05),      # Ohm*cm^2, F/cm^2
    "fresh dry metal (Goyal 2022 fit)": dict(RA=2.0e6, CA=41e-9),
}


def contact_noise_uv(area_cm2, RA, CA, band=BAND):
    """Thermal noise of one R||C contact, sqrt(4kT int Re Z df) over band (uV)."""
    R, C = RA / area_cm2, CA * area_cm2
    f = np.linspace(band[0], band[1], 4000)
    reZ = R / (1 + (2 * np.pi * f * R * C) ** 2)
    return np.sqrt(4 * K_B * T_K * np.trapezoid(reZ, f)) * 1e6, R, C


def zmag(area_cm2, RA, CA, f):
    R, C = RA / area_cm2, CA * area_cm2
    return R / np.sqrt(1 + (2 * np.pi * f * R * C) ** 2)


def cm_to_dm_uv(area_cm2, RA, CA, vcm_mv=10.0, mismatch=0.5, cin=50e-12, f=50.0):
    """Differential mains from common-mode via contact-impedance mismatch (signal_chain.md model)."""
    dz = mismatch * zmag(area_cm2, RA, CA, f)
    return vcm_mv * 1e-3 * 2 * np.pi * f * cin * dz * 1e6


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    st = Study()
    st.all_mono()
    print(f"MUAPs done ({sum(len(p) for p in st.pools.values())} MUs) {time.time() - t0:.0f}s", flush=True)
    res = dict(muscles=ALL, visible=VIS, band=BAND,
               pools={n: dict(n_mu=len(p), n_fibres=int(sum(mu.n_fibres for mu in p))) for n, p in st.pools.items()})
    out = {}
    C8 = st.config()
    C16 = st.config(16, 9.0)
    res["pods_s"] = C8[2].tolist()
    res["circ"] = st.model.outline.circ

    # ---- single-MU MUAP amplitudes (peak-to-peak, max channel) for calibration
    mu_pp = {}
    for n in ALL:
        b = st.bip(n, C8)
        pp = (b.max(-1) - b.min(-1)).max(-1) * 1e6
        mu_pp[n] = dict(median=float(np.median(pp)), p90=float(np.percentile(pp, 90)), max=float(pp.max()))
    res["muap_pp_uv"] = mu_pp

    # ---- sensitivity matrices (uV RMS at 10% MVC, single muscle)
    S8 = st.sens(C8) * 1e6
    S16 = st.sens(C16) * 1e6
    out["S8"], out["S16"] = S8, S16
    for E in (5.0, 10.0, 20.0, 40.0):
        out[f"S8_E{int(E)}"] = st.sens(C8, E) * 1e6
    res["amplitude_max_channel_uv"] = {f"E{int(E)}": {n: float(out[f'S8_E{int(E)}'][:, i].max()) for i, n in enumerate(ALL)}
                                       for E in (5.0, 10.0, 20.0, 40.0)}
    # co-contraction scenarios (independent MUs add in power)
    scen = {"grip (all flexors + PQ)": ["FDS", "FDP", "FPL", "FCU", "PQ", "FCR", "PL"],
            "finger/wrist extension": ["EDC", "EIP", "EDM", "EPL", "APL_EPB", "ECU", "ECR"],
            "thumb (FPL + APL/EPB + EPL)": ["FPL", "APL_EPB", "EPL"]}
    res["scenarios_uv"] = {}
    for E in (5.0, 20.0):
        SE = out[f"S8_E{int(E)}"]
        for sname, mus in scen.items():
            idx = [ALL.index(m) for m in mus]
            r = np.sqrt((SE[:, idx] ** 2).sum(1))
            res["scenarios_uv"][f"{sname} @ {int(E)}%"] = dict(per_channel=r.round(2).tolist(), max=float(r.max()),
                                                               median=float(np.median(r)))

    # ---- spectra (channel with max RMS, 10% MVC)
    spec = {}
    for i, n in enumerate(ALL):
        ch = int(np.argmax(S8[:, i]))
        p = st.psd(n, C8, 10.0)[ch]
        spec[n] = p
        res.setdefault("mean_freq_hz", {})[n] = float((FREQ[INB] * p[INB]).sum() / p[INB].sum())
    out["spec_f"] = FREQ
    out["spec"] = np.stack([spec[n] for n in ALL])

    # ---- coverage: SVD / condition number of column-normalised signature matrices
    def svd_stats(S, names):
        idx = [ALL.index(m) for m in names]
        A = S[:, idx] / np.linalg.norm(S[:, idx], axis=0)
        sv = np.linalg.svd(A, compute_uv=False)
        cos = A.T @ A
        np.fill_diagonal(cos, 0)
        p = sv ** 2 / (sv ** 2).sum()
        erank = float(np.exp(-(p * np.log(p)).sum()))
        k, l_ = np.unravel_index(np.argmax(cos), cos.shape)
        return dict(singular_values=sv.round(4).tolist(), cond=float(sv[0] / sv[-1]), effective_rank=erank,
                    max_cos=float(cos.max()), most_similar=[names[k], names[l_]])
    res["coverage"] = {f"{tag}_{set_}": svd_stats(S, names)
                       for tag, S in (("8ch", S8), ("16ch", S16))
                       for set_, names in (("visible11", VIS), ("main6", ["FDS", "FDP", "FPL", "FCU", "EDC", "ECU"]))}
    for tag, S in (("8ch", S8), ("16ch", S16)):
        A = S[:, [ALL.index(m) for m in VIS]]
        A = A / np.linalg.norm(A, axis=0)
        out[f"cos_{tag}"] = A.T @ A

    # ---- rotation: signature shift
    offs = [-18.0, -9.0, -4.5, 0.0, 4.5, 9.0, 18.0]
    cfg_rot = {o: st.config(offset=o) for o in offs}
    Srot = {o: st.sens(cfg_rot[o]) * 1e6 for o in offs}
    out["S_rot"] = np.stack([Srot[o] for o in offs])
    rot = {}
    for o in offs:
        d = {}
        for i, n in enumerate(VIS):
            j = ALL.index(n)
            a, b = Srot[0.0][:, j], Srot[o][:, j]
            d[n] = dict(corr=float(np.corrcoef(a, b)[0, 1]), rel_change=float(np.linalg.norm(b - a) / np.linalg.norm(a)))
            if abs(o) == 18.0:   # compare with the circularly shifted unrotated signature
                bs = np.roll(a, -int(np.sign(o)))   # +1 pitch: channel k sits where k+1 was
                d[n]["rel_change_vs_shifted"] = float(np.linalg.norm(b - bs) / np.linalg.norm(a))
        rot[str(o)] = dict(per_muscle=d,
                           median_corr=float(np.median([v["corr"] for v in d.values()])),
                           median_rel_change=float(np.median([v["rel_change"] for v in d.values()])))
    res["rotation_signature"] = rot

    # ---- electrode size / IED amplitude + spectral effects
    cfgs = {"disc6.5_ied20": C8, "disc2_ied20": st.config(kind="disc2"), "pins2x2_ied20": st.config(kind="pins2x2"),
            "disc6.5_ied15": st.config(ied=15.0), "disc6.5_ied25": st.config(ied=25.0)}
    ecomp = {}
    for cname, cfg in cfgs.items():
        S = st.sens(cfg) * 1e6
        out[f"S_{cname}"] = S
        mf = {}
        for i, n in enumerate(VIS):
            ch = int(np.argmax(S[:, ALL.index(n)]))
            p = st.psd(n, cfg, 10.0)[ch]
            mf[n] = float((FREQ[INB] * p[INB]).sum() / p[INB].sum())
        ecomp[cname] = dict(max_rms={n: float(S[:, ALL.index(n)].max()) for n in VIS},
                            mean_freq=mf,
                            coverage=svd_stats(S, VIS))
    res["electrode_configs"] = ecomp
    # contact noise / mains table
    areas = {"disc6.5": np.pi * 0.325 ** 2, "disc2": np.pi * 0.1 ** 2, "pins2x2": 4 * np.pi * 0.1 ** 2}
    noise = {}
    for scen_name, p in CONTACT.items():
        for k, A in areas.items():
            en, R, C = contact_noise_uv(A, p["RA"], p["CA"])
            pair = np.sqrt(2) * en
            tot = np.sqrt(pair ** 2 + ADS_NOISE_UV ** 2 + RES_NOISE_UV ** 2)
            noise[f"{scen_name} | {k}"] = dict(area_mm2=A * 100, R_kohm=R / 1e3, C_nF=C * 1e9,
                                               Z50_kohm=float(zmag(A, p["RA"], p["CA"], 50) / 1e3),
                                               Z1k_kohm=float(zmag(A, p["RA"], p["CA"], 1000) / 1e3),
                                               thermal_pair_uv=float(pair), total_uv=float(tot),
                                               mains_dm_per_10mVcm_uv=float(cm_to_dm_uv(A, p["RA"], p["CA"])))
    res["contact_noise"] = noise
    res["contact_rc_fit"] = {k: dict(R_kohm_cm2=v["RA"] / 1e3, C_nF_per_cm2=v["CA"] * 1e9) for k, v in CONTACT.items()}
    print(f"deterministic part done {time.time() - t0:.0f}s", flush=True)

    # ---- classification: (A) single muscle 3-15 % MVC; (B) subtle 1-4 % MVC + co-activation of all others
    st.spectra_cache(ALL)
    allcfg = dict(cfgs)
    allcfg["16ch"] = C16
    for o in offs:
        allcfg[f"rot{o:+.1f}"] = cfg_rot[o]

    def make_feats(scenario, classes, ntr, rng):
        feats = {(c, nz): [] for c in allcfg for nz in (1.5, 5.0)}
        labels = []
        for ci, n in enumerate(classes):
            for k in range(2 * ntr):
                if scenario == "A":
                    X = st.synth(n, rng.uniform(3.0, 15.0), rng)
                else:
                    Et = rng.uniform(1.0, 4.0)
                    X = st.synth(n, Et, rng)
                    for o_ in VIS:
                        if o_ != n:
                            Eo = rng.uniform(0.0, 0.6) * Et
                            if Eo > 1.0:
                                X = X + st.synth(o_, Eo, rng)
                for cname, cfg in allcfg.items():
                    for nz in (1.5, 5.0):
                        feats[(cname, nz)].append(st.features(X, cfg, nz, rng, gain_jitter=0.05))
                labels.append(ci)
        return {k: np.array(v) for k, v in feats.items()}, np.array(labels)

    def knn_fit(X, y):
        mu, sd = X.mean(0), X.std(0) + 1e-9
        return (X - mu) / sd, y, mu, sd

    def knn_predict(m, X, k=7):
        Xt, yt, mu, sd = m
        Z = (X - mu) / sd
        d = (Z ** 2).sum(1)[:, None] + (Xt ** 2).sum(1)[None, :] - 2 * Z @ Xt.T
        nn = np.argpartition(d, k, axis=1)[:, :k]
        votes = yt[nn]
        return np.array([np.bincount(v).argmax() for v in votes])

    def interp_aug(F, rng, maxshift=1.0, n_aug=4):
        """Virtual rotation: shift the RMS pattern by a random fraction of a channel (circular)."""
        R = np.exp(F)
        outF = [F]
        idx = np.arange(F.shape[1])
        rows = np.arange(len(F))[:, None]
        for _ in range(n_aug):
            d = rng.uniform(-maxshift, maxshift, len(F))
            k = np.floor(d).astype(int); fr = d - k
            a = R[rows, (idx[None, :] + k[:, None]) % F.shape[1]]
            b = R[rows, (idx[None, :] + k[:, None] + 1) % F.shape[1]]
            outF.append(np.log((1 - fr)[:, None] * a + fr[:, None] * b))
        return np.concatenate(outF)

    clf, rotgen = {}, {}
    for scen_name, classes, ntr, seed in (("A", VIS + ["FCR", "ECR"], 80, 7), ("B", VIS, 80, 8)):
        rng = np.random.default_rng(seed)
        t1 = time.time()
        feats, y = make_feats(scen_name, classes, ntr, rng)
        split = np.tile(np.r_[np.zeros(ntr, bool), np.ones(ntr, bool)], len(classes))   # first half train
        print(f"scenario {scen_name}: features {time.time() - t1:.0f}s", flush=True)
        subsets = (("all13", classes), ("visible11", VIS)) if scen_name == "A" else (("visible11", VIS),)
        for (cname, nz), F in feats.items():
            for sub_name, cl in subsets:
                msk = np.isin(y, [classes.index(c) for c in cl])
                tr, te = msk & ~split, msk & split
                m = lda_fit(F[tr], y[tr])
                yp = lda_predict(m, F[te])
                yk = knn_predict(knn_fit(F[tr], y[tr]), F[te])
                mi, C = confusion_mi(np.searchsorted(m[0], y[te]), np.searchsorted(m[0], yp), len(m[0]))
                clf[f"{scen_name}|{cname}|noise{nz}|{sub_name}"] = dict(
                    acc=float((yp == y[te]).mean()), acc_knn=float((yk == y[te]).mean()),
                    mi_bits=mi, h_max=float(np.log2(len(cl))))
                if cname in ("disc6.5_ied20", "16ch") and nz == 5.0 and sub_name == "visible11":
                    out[f"confusion_{scen_name}_{cname}"] = C
        # rotation generalisation (8 ch): train at 0 / at -9,0,+9 / at 0 + virtual-rotation augmentation
        for nz in (1.5, 5.0):
            msk = np.isin(y, [classes.index(c) for c in VIS])
            tr, te = msk & ~split, msk & split
            F0 = feats[("rot+0.0", nz)]
            Fm = np.concatenate([feats[(f"rot{o:+.1f}", nz)][tr] for o in (-9.0, 0.0, 9.0)])
            Fa = interp_aug(F0[tr], np.random.default_rng(3))
            models = {"train0": (F0[tr], y[tr]), "train_multi": (Fm, np.tile(y[tr], 3)),
                      "train_interp_aug": (Fa, np.tile(y[tr], 5))}
            for o in offs:
                Ft = feats[(f"rot{o:+.1f}", nz)][te]
                d = {}
                for mn, (Xtr, ytr) in models.items():
                    d[mn] = float((lda_predict(lda_fit(Xtr, ytr), Ft) == y[te]).mean())
                    d[mn + "_knn"] = float((knn_predict(knn_fit(Xtr, ytr), Ft) == y[te]).mean())
                rotgen[f"{scen_name}|noise{nz}|{o:+.1f}"] = d
    res["classification"] = clf
    res["rotation_classification"] = rotgen
    res["runtime_s"] = time.time() - t0
    with open(os.path.join(CACHE, "results.json"), "w") as f:
        json.dump(res, f, indent=1)
    np.savez(os.path.join(CACHE, "study.npz"), offs=np.array(offs), **out)
    # example MUAPs for figures: largest-amplitude MU per muscle, all 8 bipolar channels
    ex = {}
    for n in ALL:
        b = st.bip(n, C8)
        i = int(np.argmax(np.abs(b).max(axis=(1, 2))))
        med = int(np.argsort(np.abs(b).max(axis=(1, 2)))[len(b) // 2])
        ex[n + "_max"] = b[i]
        ex[n + "_med"] = b[med]
    np.savez(os.path.join(CACHE, "muaps.npz"), t=st.t, **ex)
    print(json.dumps({k: res[k] for k in ("amplitude_max_channel_uv", "coverage")}, indent=1))
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
