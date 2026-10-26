#!/usr/bin/env python3
"""Rev C BLE packet parser / recorder tests (no bleak needed):  python3 -m unittest -v test_ble_packet"""
import json
import os
import re
import sys
import tempfile
import unittest

import numpy as np

import neurband_ble as nb

HERE = os.path.dirname(os.path.abspath(__file__))


class PacketTest(unittest.TestCase):
    def test_i16_roundtrip(self):
        counts = np.arange(14 * 8, dtype=np.int64).reshape(14, 8) * 37 - 2000
        counts[0, :2] = [-32768, 32767]
        pkt = nb.build_packet(65535, 123456, nb.T_I16, counts, flags=nb.F_MARKER | nb.F_LOFF_EN,
                              gain=6, hp=40, loff_p=0x81, loff_n=0x02)
        self.assertEqual(len(pkt), 12 + 14 * 16)  # 236 bytes <= 244 (MTU 247)
        p = nb.parse_packet(pkt)
        self.assertEqual((p["seq"], p["sample"], p["type"], p["rate"], p["gain"], p["hp"]),
                         (65535, 123456, nb.T_I16, 2000, 6, 40))
        self.assertEqual((p["flags"], p["loff_p"], p["loff_n"]), (nb.F_MARKER | nb.F_LOFF_EN, 0x81, 0x02))
        np.testing.assert_allclose(p["volts"], counts * 0.25e-6)

    def test_i24_roundtrip(self):
        rng = np.random.default_rng(1)
        codes = rng.integers(-(1 << 23), 1 << 23, size=(9, 8))
        codes[0, :4] = [-(1 << 23), (1 << 23) - 1, -1, 0]
        pkt = nb.build_packet(7, 99, nb.T_I24, codes, gain=12, rate4k=True)
        self.assertEqual(len(pkt), 12 + 9 * 24)
        self.assertEqual(pkt[12:15], b"\x80\x00\x00")  # big-endian int24, as shifted out of the ADS
        p = nb.parse_packet(pkt)
        self.assertEqual((p["rate"], p["gain"]), (4000, 12))
        np.testing.assert_array_equal(p["codes"], codes)
        np.testing.assert_allclose(p["volts"], codes * 4.8 / 12 / 2 ** 24)

    def test_diag(self):
        dc = [100000, -200000, 0, 1, -1, 7969178, -7969178, 42]
        pkt = nb.build_packet(3, 2000, nb.T_DIAG, diag=dict(dc=dc, rail=0x60, clip=0x01, rld_cfg=3,
                              rld_active=1, vbat_mv=3812, overruns=5, drops=2), loff_p=0x02)
        self.assertEqual(len(pkt), 12 + 44)
        p = nb.parse_packet(pkt)
        np.testing.assert_allclose(p["dc"], np.array(dc) * nb.lsb_volts(6))
        self.assertEqual((p["rail"], p["clip"], p["rld_active"], p["vbat_mv"], p["overruns"], p["drops"]),
                         (0x60, 0x01, 1, 3812, 5, 2))

    def test_rejects_malformed(self):
        good = nb.build_packet(1, 0, nb.T_I16, np.zeros((14, 8)))
        self.assertIsNone(nb.parse_packet(good[:-1]))
        self.assertIsNone(nb.parse_packet(good[:5]))
        bad_type = bytearray(good)
        bad_type[6] = 9
        self.assertIsNone(nb.parse_packet(bytes(bad_type)))

    def test_seq_wrap_and_gap(self):
        s = nb.SeqTracker()
        for q in (65534, 65535, 0, 1, 3):
            s.update(q)
        self.assertEqual(s.lost, 1)

    def test_firmware_layout_matches(self):
        src = open(os.path.join(HERE, "..", "firmware_c", "src", "packet.h")).read()
        defs = dict(re.findall(r"#define (\w+)\s+(0x[0-9A-Fa-f]+|\d+)", src))
        self.assertEqual(int(defs["PKT_HDR_LEN"]), nb.HDR.size)
        self.assertLessEqual(12 + int(defs["PKT_I16_MAX_SAMPLES"]) * 16, int(defs["PKT_MAX_LEN"]))
        self.assertLessEqual(12 + int(defs["PKT_I24_MAX_SAMPLES"]) * 24, int(defs["PKT_MAX_LEN"]))
        for name, bit in (("PF_MARKER", nb.F_MARKER), ("PF_MISSED", nb.F_MISSED), ("PF_TEST", nb.F_TEST)):
            self.assertEqual(int(defs[name], 0), bit)
        self.assertIn("4e420c0", open(os.path.join(HERE, "..", "firmware_c", "src", "ble.c")).read())


class RecorderTest(unittest.TestCase):
    def test_save_load_with_gap_and_markers(self):
        rec = nb.Recorder()
        t0 = 1_000_000_000
        n = 14
        rng = np.random.default_rng(0)
        for k in range(30):
            if k == 10:
                continue  # one packet lost in the air: seq and sample index both jump
            counts = rng.integers(-400, 400, size=(n, 8))
            flags = nb.F_MARKER if k == 20 else 0
            pkt = nb.build_packet(k, k * n, nb.T_I16, counts, flags=flags)
            rec.add(nb.parse_packet(pkt), t_mono_ns=t0 + int((k + 1) * n / 2000 * 1e9) + 8_000_000, t_wall=1e9 + k)
        rec.add(nb.parse_packet(nb.build_packet(30, 30 * n, nb.T_DIAG, diag=dict(dc=[1000] * 8))))
        imu = [(0, 100, -100, 0, 0, 0, 8197), (10, 0, 0, 0, 0, 0, 8197)]  # az = 8197 x 0.122 mg ~ 1 g
        rec.add(nb.parse_packet(nb.build_packet(31, 50, nb.T_IMU, imu)))
        # software marker 0.1 s after t0 (host clock); packets arrive 8 ms after their last
        # sample, so device sample 0 was at t0 + 8 ms -> marker at sample (0.1 - 0.008) * 2000
        rec.software_marker("cue", t_mono_ns=t0 + 100_000_000)
        self.assertEqual(rec.seqs.lost, 1)
        self.assertEqual(rec.missed_samples, n)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.npz")
            rec.save(path, {"transport": "test"})
            z = np.load(path, allow_pickle=False)
            self.assertEqual(z["emg"].shape, (29 * n, 8))
            self.assertEqual(z["emg"].dtype, np.float32)
            self.assertAlmostEqual(z["t"][10 * n], 11 * n / 2000)  # time jumps over the gap
            self.assertEqual(len(z["pkt_rx_mono_ns"]), 29)
            src = list(z["marker_src"])
            self.assertEqual(sorted(src), [0, 1])
            sw = int(z["markers"][src.index(1)])
            self.assertLess(abs(int(z["sample_index"][sw]) - 184), 2)
            bt = int(z["markers"][src.index(0)])
            self.assertEqual(int(z["sample_index"][bt]), 20 * n)
            meta = json.loads(str(z["meta"]))
            self.assertEqual((meta["rate"], meta["n_channels"], meta["lost_packets"]), (2000, 8, 1))
            np.testing.assert_allclose(z["diag_dc"][0], 1000 * nb.lsb_volts(6), rtol=1e-6)
            self.assertEqual(z["imu"].shape, (2, 6))
            np.testing.assert_array_equal(z["imu_sample"], [50, 60])
            np.testing.assert_allclose(z["imu"][0], [0, 0, 1.0, 1.75, -1.75, 0], atol=2e-3)
            self.assertEqual(meta["imu"]["columns"][2], "az")
            # the analysis package loads it unchanged
            sys.path.insert(0, os.path.join(HERE, ".."))
            from analysis.recording import load
            r = load(path)
            self.assertEqual((r.n_channels, r.fs), (8, 2000.0))
            self.assertEqual(len(r.markers), 2)
            self.assertEqual(r.loff.shape, (29, 8))


if __name__ == "__main__":
    unittest.main()
