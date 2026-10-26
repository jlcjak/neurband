#!/usr/bin/env python3
"""Round-trip synthetic packets through the parser:  python3 -m unittest -v test_packet"""
import struct
import unittest
import zlib

import numpy as np

import neurband_rec as nr


class PacketTest(unittest.TestCase):
    def make(self, seq=7, ns=20):
        rng = np.random.default_rng(seq)
        codes = rng.integers(-(1 << 23), 1 << 23, size=(ns, 16))
        codes[0, :4] = [-(1 << 23), (1 << 23) - 1, -1, 0]  # int24 extremes
        pkt = nr.build_packet(seq, 123456789012, codes, rate=4000, gain=6,
                              flags=nr.F_MARKER | nr.F_LEADOFF, loff_p=0x8001, loff_n=0x0100, fw_drops=3)
        return codes, pkt

    def test_layout(self):
        _, pkt = self.make()
        self.assertEqual(len(pkt), 26 + 20 * 16 * 3 + 4)  # 990 bytes, as in packet.h
        self.assertEqual(pkt[:3], b"NB\x02")
        # first channel value is big-endian int24 right after the 26-byte header
        self.assertEqual(pkt[26:29], b"\x80\x00\x00")

    def test_roundtrip(self):
        codes, pkt = self.make()
        p = nr.parse_packet(pkt)
        self.assertIsNotNone(p)
        np.testing.assert_array_equal(p["codes"], codes)
        self.assertEqual((p["seq"], p["t_us"], p["rate"], p["gain"]), (7, 123456789012, 4000, 6))
        self.assertEqual((p["loff_p"], p["loff_n"], p["fw_drops"]), (0x8001, 0x0100, 3))
        self.assertEqual(p["flags"], nr.F_MARKER | nr.F_LEADOFF)

    def test_rejects_v1(self):
        _, pkt = self.make()
        old = bytearray(pkt)
        old[2] = 1  # a v1 (IMU-era) header must not be accepted
        self.assertIsNone(nr.parse_packet(bytes(old)))

    def test_stream_resync_and_crc(self):
        c0, p0 = self.make(0)
        c1, p1 = self.make(1)
        _, p2 = self.make(2)
        bad = bytearray(p2)
        bad[100] ^= 0xFF  # corrupt payload -> CRC must reject
        c3, p3 = self.make(3)
        stream = b"garbage\n# OK start rate=4000\n" + p0 + b"NB" + p1 + bytes(bad) + p3
        parser = nr.StreamParser()
        got = []
        for i in range(0, len(stream), 37):  # awkward chunking
            got += parser.feed(stream[i:i + 37])
        self.assertEqual([p["seq"] for p in got], [0, 1, 3])
        np.testing.assert_array_equal(got[1]["codes"], c1)
        np.testing.assert_array_equal(got[2]["codes"], c3)
        self.assertIn("# OK start rate=4000", parser.lines)
        self.assertGreaterEqual(parser.bad_crc, 1)
        tr = nr.SeqTracker()
        for p in got:
            tr.update(p["seq"])
        self.assertEqual(tr.lost, 1)

    def test_volts_and_filter(self):
        self.assertAlmostEqual(nr.lsb_volts(6), 2 * 2.4 / 6 / 2 ** 24)
        fs = 4000
        t = np.arange(2 * fs) / fs  # live display uses a 2 s window
        x = np.stack([np.sin(2 * np.pi * 50 * t + 0.3), np.sin(2 * np.pi * 120 * t),
                      np.sin(2 * np.pi * 5 * t + 1) + 0.3 + 0.2 * t], 1)
        rms = nr.live_rms(x, fs, mains=50)
        self.assertLess(rms[0], 1e-3)                            # mains: > 60 dB down
        self.assertAlmostEqual(rms[1] / (1 / np.sqrt(2)), 1, 3)  # in band, untouched
        self.assertLess(rms[2], 1e-3)                            # 5 Hz + offset + drift removed

    def test_crc_matches_firmware_definition(self):
        # firmware: reflected 0xEDB88320, init/xorout 0xFFFFFFFF == zlib.crc32
        def crc(b):
            c = 0xFFFFFFFF
            for x in b:
                c ^= x
                for _ in range(8):
                    c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
            return c ^ 0xFFFFFFFF
        _, pkt = self.make()
        self.assertEqual(crc(pkt[:-4]), struct.unpack("<I", pkt[-4:])[0])
        self.assertEqual(crc(b"123456789"), zlib.crc32(b"123456789"))


if __name__ == "__main__":
    unittest.main()
