#!/usr/bin/env python3
"""Tests for the analysis package. From the project root:
    python3 -m unittest discover -s analysis/tests -v      (numpy only)
    python3 -m pytest analysis/tests                       (if pytest is installed)
"""
import json
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analysis import align, collect, dataset, features, filters, model, protocol, quality, synth  # noqa: E402
from analysis.recording import load, save  # noqa: E402


class FilterTest(unittest.TestCase):
    fs = 2000.0

    def tone_gain(self, f, use_scipy=False, mains=50.0):
        t = np.arange(int(self.fs * 10)) / self.fs
        x = np.sin(2 * np.pi * f * t)[:, None]
        y = filters.bandpass_notch(x, self.fs, mains=mains, use_scipy=use_scipy)
        m = slice(int(self.fs), -int(self.fs))
        return np.sqrt(np.mean(y[m] ** 2) / np.mean(x[m] ** 2))

    def test_passband_and_stopbands(self):
        self.assertGreater(self.tone_gain(125.0), 0.95)
        self.assertLess(self.tone_gain(50.0), 1e-3)       # notch
        self.assertLess(self.tone_gain(150.0), 1e-3)      # harmonic notch
        self.assertLess(self.tone_gain(3.0), 1e-3)        # motion / drift
        self.assertLess(self.tone_gain(800.0), 0.01)      # above 450 Hz
        self.assertLess(self.tone_gain(60.0, mains=60.0), 1e-3)  # 60 Hz grids
        self.assertGreater(self.tone_gain(56.0, mains=60.0), 0.85)

    def test_dc_offset_removed_without_edge_blowup(self):
        t = np.arange(int(self.fs * 4)) / self.fs
        x = 0.2 + 1e-3 * t[:, None] + 5e-6 * np.sin(2 * np.pi * 120 * t)[:, None]  # 200 mV offset + drift
        y = filters.bandpass_notch(x, self.fs, use_scipy=False)
        self.assertLess(np.max(np.abs(y)), 2e-5)

    @unittest.skipUnless(filters.HAVE_SCIPY, "scipy not installed")
    def test_numpy_matches_scipy(self):
        rng = np.random.default_rng(0)
        x = rng.standard_normal((20000, 3))
        a = filters.bandpass_notch(x, self.fs, use_scipy=False)
        b = filters.bandpass_notch(x, self.fs, use_scipy=True)
        m = slice(3000, -3000)
        self.assertLess(np.std(a[m] - b[m]) / np.std(b[m]), 0.02)

    def test_subsample_and_rotate(self):
        x = np.tile(np.arange(16), (5, 1))
        np.testing.assert_array_equal(filters.subsample_16_to_8(x, 1)[0], np.arange(1, 16, 2))
        np.testing.assert_array_equal(filters.rotate_channels(np.arange(8)[None], 1)[0], [7, 0, 1, 2, 3, 4, 5, 6])
        r = dataset.fractional_rotate(np.eye(8), 0.5)
        np.testing.assert_allclose(r.sum(axis=1), 1.0)


class FeatureTest(unittest.TestCase):
    def test_known_values(self):
        fs, f0, A = 2000.0, 50.0, 1e-4
        t = np.arange(4000) / fs
        x = (A * np.sin(2 * np.pi * f0 * t + 0.1))[:, None]
        fe = features.window_features(x, fs, 200, 100, thr=1e-6)
        np.testing.assert_allclose(fe["rms"], A / np.sqrt(2), rtol=0.01)
        np.testing.assert_allclose(fe["mav"], 2 * A / np.pi, rtol=0.01)
        np.testing.assert_allclose(fe["zc"], 2 * f0, rtol=0.06)           # 2 crossings per period, per s
        np.testing.assert_allclose(fe["ssc"], 2 * f0, rtol=0.06)          # 2 slope changes per period
        np.testing.assert_allclose(fe["wl"], 4 * A * f0, rtol=0.02)       # length per s of a sine
        self.assertEqual(features.feature_matrix(fe).shape, (len(fe["t"]), 5))

    def test_threshold_suppresses_noise_counts(self):
        rng = np.random.default_rng(1)
        x = 1e-6 * rng.standard_normal((4000, 1))
        lo = features.window_features(x, 2000.0, thr=0.0)["zc"].mean()
        hi = features.window_features(x, 2000.0, thr=5e-6)["zc"].mean()
        self.assertGreater(lo, 10 * max(hi, 1))


class QualityTest(unittest.TestCase):
    def test_faults_are_flagged(self):
        rec = synth.simulate(protocol.build("quick"), seed=3,
                             faults={1: "flat", 3: "leadoff", 4: "line", 5: "noisy", 6: "clip"})
        r = quality.report(rec)
        st = {c["ch"]: c for c in r["channels"]}
        self.assertTrue(st[2]["flat"])
        self.assertEqual(st[4]["grades"]["loff_frac"], "FAIL")
        self.assertEqual(st[5]["grades"]["line_uv"], "FAIL")
        self.assertEqual(st[6]["grades"]["noise_uv"], "FAIL")
        self.assertIn(st[7]["grades"]["clip_frac"], ("WARN", "FAIL"))
        self.assertEqual(r["verdict"], "REJECT")
        self.assertIn("verdict", quality.format_report(r))

    def test_clean_recording_passes(self):
        rec = synth.simulate(protocol.build("quick"), seed=4)
        r = quality.report(rec)
        self.assertEqual(r["n_fail"], 0)
        for c in r["channels"]:
            self.assertLess(c["metrics"]["noise_uv"], 5)
            self.assertGreater(c["metrics"]["mvc_snr_db"], 20)


class AlignTest(unittest.TestCase):
    def test_clock_fit_with_missed_and_extra_presses(self):
        rng = np.random.default_rng(5)
        cues = 1.7e9 + np.array([0, 4, 8, 600, 604, 608.0])
        true_off, drift = -1.7e9 + 3.0, 30e-6
        presses = (cues - cues[0]) * (1 + drift) + (cues[0] + true_off) + 0.25 + rng.normal(0, 0.03, 6)
        presses = np.sort(np.r_[np.delete(presses, 4), 300.0])   # one press missed, one stray press
        clk = align.fit_clock(cues, presses)
        self.assertEqual(clk.n_pairs, 5)
        np.testing.assert_allclose(clk.to_device(cues), (cues - cues[0]) * (1 + drift) + cues[0] + true_off, atol=0.06)

    def test_onsets_recovered_from_emg(self):
        rec = synth.simulate(protocol.build("quick"), seed=6)
        y = filters.bandpass_notch(rec.emg, rec.fs)
        ev = align.device_events(rec, y=y)
        truth = {d["step"]: d["onset"] for d in rec.labels["truth"]}
        err = [e["onset"] - truth[e["step"]] for e in ev if e["detected"]]
        self.assertGreater(len(err), 15)
        self.assertLess(np.median(np.abs(err)), 0.08)


class EndToEndTest(unittest.TestCase):
    def test_save_load_train_loso(self):
        with tempfile.TemporaryDirectory() as d:
            paths = synth.make_dataset(d, n_sessions=3, protocol="quick", seed=7)
            rec = load(paths[0])
            self.assertEqual(rec.emg.shape[1], 8)
            self.assertEqual(rec.emg.dtype, np.float32)
            self.assertIsNotNone(rec.labels)
            sessions = [dataset.windows(p) for p in paths]
            r = model.loso(sessions, "lda")
            self.assertGreater(r["window_acc"], 0.8)
            r2 = model.loso(sessions, "logreg")
            self.assertGreater(r2["trial_acc"], 0.8)
            self.assertIn("confusion", model.format_loso(r))

    def test_lda_on_separable_blobs(self):
        rng = np.random.default_rng(8)
        X = np.r_[rng.normal(0, 1, (100, 4)), rng.normal(3, 1, (100, 4))]
        y = np.array(["a"] * 100 + ["b"] * 100)
        self.assertGreater(np.mean(model.LDA().fit(X, y).predict(X) == y), 0.95)


try:
    import h5py
except ImportError:
    h5py = None


@unittest.skipUnless(h5py is not None, "h5py not installed")
class MetaDataTest(unittest.TestCase):
    def test_reads_all_three_layouts(self):
        from analysis.meta_data import NOISE_UNIT, load_meta_hdf5
        n, t = 2000, 1.6e9 + np.arange(2000) / 2000.0
        emg = np.tile(np.arange(16, dtype="<f4"), (n, 1))
        layouts = {
            "gni": (None, "data", [("emg", "<f4", (16,)), ("time", "<f8")]),
            "q": ("emg2qwerty", "timeseries", [("emg_right", "<f4", (16,)), ("time", "<f8"), ("emg_left", "<f4", (16,))]),
            "p": ("emg2pose", "timeseries", [("time", "<f8"), ("joint_angles", "<f4", (20,)), ("emg", "<f4", (16,))]),
        }
        with tempfile.TemporaryDirectory() as d:
            for name, (group, dset, fields) in layouts.items():
                a = np.zeros(n, np.dtype(fields))
                a[fields[0][0] if fields[0][0] != "time" else fields[2][0]] = emg
                a["time"] = t
                p = os.path.join(d, name + ".hdf5")
                with h5py.File(p, "w") as f:
                    (f.create_group(group) if group else f).create_dataset(dset, data=a)
                r = load_meta_hdf5(p, offset=1)
                self.assertEqual(r.fs, 2000.0)
                np.testing.assert_allclose(r.emg[0], np.arange(1, 16, 2) * NOISE_UNIT, rtol=1e-6)


class FakeUI:
    """Headless UI with a simulated clock, for running collect.run instantly."""

    def __init__(self):
        self.t = 1000.0
        self.shown = []

    def now(self):
        return self.t

    def show(self, title, sub="", style="info"):
        self.shown.append(title)

    def beep(self):
        pass

    def wait(self, dur, bar=None):
        if bar is not None:
            assert 0 <= bar(0.5) <= 1
        self.t += dur

    def wait_enter(self, msg=""):
        self.t += 3.0
        return self.t

    def type_text(self, text):
        keys = []
        for ch in text:
            keys.append((ch, self.t, self.t + 0.08))
            self.t += 0.2
        return keys


class CollectTest(unittest.TestCase):
    def test_run_writes_labels(self):
        for name in protocol.PROTOCOLS:
            steps = protocol.build(name)
            with tempfile.TemporaryDirectory() as d:
                out = os.path.join(d, "s1")
                marks = []
                lab = collect.run(steps, FakeUI(), out, {"protocol": name}, mark=marks.append)
                with open(out + ".labels.json") as f:
                    disk = json.load(f)
                self.assertEqual(len(disk["events"]), len(steps))
                self.assertEqual(len(marks), len(steps))
                for e in lab["events"]:
                    self.assertLessEqual(e["t_cue"], e["t_start"])
                    self.assertLessEqual(e["t_start"], e["t_end"])
                if name == "typing":
                    self.assertEqual(len(disk["events"][3]["keys"]), len(steps[3]["text"]))

    def test_collected_labels_align_with_recording(self):
        """Labels from collect.run + a synthetic recording of the same steps line up."""
        steps = protocol.build("quick")
        rec = synth.simulate(steps, seed=9)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.npz")
            save(p, rec)
            back = load(p)
            clk = align.make_clock(back)
            self.assertEqual(clk.method, "markers")
            self.assertLess(clk.resid_ms, 80)


if __name__ == "__main__":
    unittest.main()
