#!/usr/bin/env python3
"""neurband recorder: USB serial or UDP -> .npz

  python3 neurband_rec.py --udp -o rec.npz                   # on body: wait for the band's HELLO beacon
  python3 neurband_rec.py --udp 192.168.1.77 -o rec.npz     # on body: known device IP
  python3 neurband_rec.py --serial /dev/ttyACM0 -o rec.npz  # BENCH ONLY, never while worn

Needs numpy; pyserial only for --serial. Ctrl-C stops and saves.
Packet format: docs/firmware.md (must match firmware/src/packet.h).
"""
import argparse
import datetime
import json
import socket
import struct
import sys
import time
import zlib

import numpy as np

# ---------------------------------------------------------------- packet format
MAGIC = b"NB"  # uint16 0x424E little-endian
VERSION = 2  # v2: no IMU / battery fields
NUM_CH = 16
HDR = struct.Struct("<HBBIQHBBHHH")  # 26 bytes, see PacketHeader in packet.h
assert HDR.size == 26
CRC_LEN = 4
MAX_SAMPLES = 64

F_MARKER, F_LEADOFF, F_MODE_MASK, F_MISSED, F_STATUS_ERR = 0x01, 0x02, 0x0C, 0x20, 0x40
MODES = {0: "normal", 1: "shorted", 2: "test"}

VREF = 2.4


def lsb_volts(gain):
    """ADS1298 code weight: (2 * VREF / gain) / 2^24."""
    return 2.0 * VREF / gain / 2 ** 24


def packet_len(n_samples):
    return HDR.size + n_samples * NUM_CH * 3 + CRC_LEN


def decode_int24_be(raw, n_samples):
    b = np.frombuffer(raw, dtype=np.uint8).reshape(n_samples, NUM_CH, 3).astype(np.int32)
    v = (b[..., 0] << 16) | (b[..., 1] << 8) | b[..., 2]
    return (v ^ 0x800000) - 0x800000  # sign-extend 24 -> 32 bit


def parse_packet(buf):
    """Parse one complete packet (bytes). Returns dict or None if invalid."""
    if len(buf) < HDR.size + CRC_LEN:
        return None
    f = HDR.unpack_from(buf, 0)
    magic, ver, ns = f[0], f[1], f[2]
    if magic != 0x424E or ver != VERSION or not 0 < ns <= MAX_SAMPLES or len(buf) != packet_len(ns):
        return None
    (crc,) = struct.unpack_from("<I", buf, len(buf) - 4)
    if zlib.crc32(buf[:-4]) != crc:
        return None
    return {
        "seq": f[3], "t_us": f[4], "rate": f[5], "gain": f[6], "flags": f[7],
        "loff_p": f[8], "loff_n": f[9], "fw_drops": f[10],
        "codes": decode_int24_be(buf[HDR.size:HDR.size + ns * NUM_CH * 3], ns),
    }


def build_packet(seq, t_us, codes, rate=4000, gain=6, flags=0, loff_p=0, loff_n=0, fw_drops=0):
    """Encode a packet exactly like the firmware does (used by tests / simulators)."""
    codes = np.asarray(codes, dtype=np.int64)
    ns = codes.shape[0]
    u = (codes & 0xFFFFFF).astype(np.uint32)
    raw = np.stack([(u >> 16) & 0xFF, (u >> 8) & 0xFF, u & 0xFF], axis=-1).astype(np.uint8).tobytes()
    body = HDR.pack(0x424E, VERSION, ns, seq, t_us, rate, gain, flags, loff_p, loff_n, fw_drops) + raw
    return body + struct.pack("<I", zlib.crc32(body))


class StreamParser:
    """Byte-stream framer: finds packets by magic+CRC, collects '# ...' text lines."""

    def __init__(self):
        self.buf = bytearray()
        self.text = bytearray()
        self.bad_crc = 0
        self.lines = []

    def _junk(self, data):
        self.text += data
        while b"\n" in self.text:
            line, _, rest = self.text.partition(b"\n")
            self.text = bytearray(rest)
            s = line.decode("ascii", "replace").strip()
            if s.startswith("#"):
                self.lines.append(s)

    def feed(self, data):
        self.buf += data
        out = []
        while True:
            i = self.buf.find(MAGIC + bytes([VERSION]))
            if i < 0:
                keep = 2  # a magic may straddle the chunk boundary
                if len(self.buf) > keep:
                    self._junk(bytes(self.buf[:-keep]))
                    del self.buf[:-keep]
                return out
            if i:
                self._junk(bytes(self.buf[:i]))
                del self.buf[:i]
            if len(self.buf) < 4:
                return out
            ns = self.buf[3]
            if not 0 < ns <= MAX_SAMPLES:
                self._junk(bytes(self.buf[:1]))
                del self.buf[:1]
                continue
            n = packet_len(ns)
            if len(self.buf) < n:
                return out
            p = parse_packet(bytes(self.buf[:n]))
            if p is None:
                self.bad_crc += 1
                self._junk(bytes(self.buf[:1]))
                del self.buf[:1]
                continue
            out.append(p)
            del self.buf[:n]


class SeqTracker:
    """Counts missing packets from sequence numbers (seq restarts at 0 on `start`)."""

    def __init__(self):
        self.last = None
        self.lost = 0
        self.restarts = 0

    def update(self, seq):
        if self.last is not None:
            if seq == 0 and self.last != 0xFFFFFFFF:
                self.restarts += 1
            elif seq > self.last + 1:
                self.lost += seq - self.last - 1
        self.last = seq


# ---------------------------------------------------------------- filtering
def bandpass_notch(x, fs, lo=20.0, hi=450.0, mains=50.0, notch_bw=2.0):
    """Zero-phase FFT-domain band-pass (lo..hi Hz) with notches at mains harmonics.

    x: [N, C]. Linear detrend first so electrode DC offset/drift does not leak.
    Brick-wall in frequency; fine for RMS display and offline plots.
    """
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[0]
    if n < 8:
        return np.zeros_like(x)
    t = np.arange(n) - (n - 1) / 2.0
    x = x - x.mean(axis=0) - np.outer(t, (t @ (x - x.mean(axis=0))) / (t @ t))
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    keep = (f >= lo) & (f <= hi)
    if mains:
        for h in np.arange(mains, hi + mains, mains):
            keep &= np.abs(f - h) > notch_bw / 2
    X[~keep] = 0
    return np.fft.irfft(X, n=n, axis=0)


def live_rms(x, fs, mains=50.0):
    """Per-channel RMS of the band-passed signal over the central half of x.

    The FFT filter rings near the window edges (wrap-around), so filter a 2 s window
    and only use its middle 1 s (>60 dB rejection of mains and slow motion artifacts).
    """
    y = bandpass_notch(x, fs, mains=mains)
    n = len(y)
    return np.sqrt(np.mean(y[n // 4: n - n // 4] ** 2, axis=0))


def loff_string(p_bits, n_bits):
    """One char per channel: '.' ok, 'P'/'N' that side off, 'X' both."""
    s = []
    for ch in range(NUM_CH):
        p, n = (p_bits >> ch) & 1, (n_bits >> ch) & 1
        s.append("X" if p and n else "P" if p else "N" if n else ".")
    return "".join(s[:8]) + " " + "".join(s[8:])


# ---------------------------------------------------------------- transports
class SerialLink:
    def __init__(self, port):
        try:
            import serial
        except ImportError:
            sys.exit("pyserial missing: pip install pyserial")
        self.s = serial.Serial(port, 115200, timeout=0.05)
        self.name = f"serial:{port}"

    def send(self, cmd):
        self.s.write((cmd + "\n").encode())

    def recv(self):
        return self.s.read(max(1, self.s.in_waiting))

    def close(self):
        self.s.close()


class UdpLink:
    def __init__(self, device, port, local_port=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 << 20)
        self.sock.bind(("0.0.0.0", local_port or port))
        self.sock.settimeout(0.05)
        self.port = port
        if not device:
            print(f"waiting for NEURBAND HELLO on udp/{port} ...")
            while not device:
                try:
                    data, addr = self.sock.recvfrom(2048)
                except socket.timeout:
                    continue
                if b"NEURBAND HELLO" in data:
                    device = addr[0]
            print(f"found band at {device}")
        self.dev = (device, port)
        self.name = f"udp:{device}:{port}"

    def send(self, cmd):
        self.sock.sendto((cmd + "\n").encode(), self.dev)

    def recv(self):
        try:
            data, addr = self.sock.recvfrom(4096)
        except socket.timeout:
            return b""
        return data if addr[0] == self.dev[0] else b""

    def close(self):
        self.sock.close()


# ---------------------------------------------------------------- recorder
class Recorder:
    def __init__(self, mains):
        self.mains = mains
        self.codes, self.gains, self.t_us, self.seq = [], [], [], []
        self.flags, self.loff_p, self.loff_n = [], [], []
        self.markers = []
        self.n = 0
        self.seqs = SeqTracker()
        self.fw_drops = 0
        self.rate = None
        self.sec_lp, self.sec_ln = 0, 0
        self.live_buf = []  # recent packets in volts, ~2 s
        self.sec_start = time.time()

    def add(self, p):
        self.seqs.update(p["seq"])
        if self.rate is None:
            self.rate = p["rate"]
        elif p["rate"] != self.rate:
            print(f"! rate changed {self.rate} -> {p['rate']} mid-recording", file=sys.stderr)
            self.rate = p["rate"]
        c = p["codes"]
        self.codes.append(c)
        self.gains.append(np.full(len(c), p["gain"], np.uint8))
        self.t_us.append(p["t_us"])
        self.seq.append(p["seq"])
        self.flags.append(p["flags"])
        self.loff_p.append(p["loff_p"])
        self.loff_n.append(p["loff_n"])
        self.fw_drops = p["fw_drops"]
        if p["flags"] & F_MARKER:
            self.markers.append(self.n)
            print(f"\n* marker at sample {self.n}")
        self.n += len(c)
        self.live_buf.append(c * lsb_volts(p["gain"]))
        self.sec_lp |= p["loff_p"]
        self.sec_ln |= p["loff_n"]

    def live(self, parser):
        if time.time() - self.sec_start < 1.0 or sum(len(c) for c in self.live_buf) < self.rate // 2:
            return
        x = np.concatenate(self.live_buf)[-2 * self.rate:]
        self.live_buf = [x]
        rms = live_rms(x, self.rate, self.mains) * 1e6
        print(f"t={self.n / self.rate:7.1f}s  rms[uV] " + " ".join(f"{r:5.1f}" for r in rms))
        print(f"           loff [{loff_string(self.sec_lp, self.sec_ln)}]  "
              f"lost={self.seqs.lost} fw_drops={self.fw_drops} bad_crc={parser.bad_crc}")
        self.sec_lp, self.sec_ln = 0, 0
        self.sec_start = time.time()

    def save(self, path, meta):
        if not self.codes:
            print("nothing recorded")
            return
        codes = np.concatenate(self.codes)
        gains = np.concatenate(self.gains)
        emg = (codes * (2.0 * VREF / gains.astype(np.float64) / 2 ** 24)[:, None]).astype(np.float32)
        rate = self.rate
        t_us = np.array(self.t_us, dtype=np.int64)
        ns = np.array([len(c) for c in self.codes])
        # per-sample time: packet timestamp + i / rate (device clock, seconds from first sample)
        t = (np.repeat(t_us, ns) + np.concatenate([np.arange(k) for k in ns]) * 1e6 / rate - t_us[0]) / 1e6
        meta = dict(meta, rate=rate, gain=int(gains[-1]), vref=VREF, lsb_volts=lsb_volts(int(gains[-1])),
                    n_samples=int(len(emg)), lost_packets=self.seqs.lost, restarts=self.seqs.restarts,
                    fw_drops=self.fw_drops, packet_version=VERSION, channels=[f"ch{i + 1}" for i in range(NUM_CH)])
        np.savez(path, emg=emg, t=t, gain=gains,
                 pkt_t_us=t_us, pkt_seq=np.array(self.seq, np.uint32), pkt_flags=np.array(self.flags, np.uint8),
                 loff_p=np.array(self.loff_p, np.uint16), loff_n=np.array(self.loff_n, np.uint16),
                 markers=np.array(self.markers, np.int64), marker_t=t[np.array(self.markers, np.int64)],
                 meta=json.dumps(meta))
        print(f"saved {len(emg)} samples ({len(emg) / rate:.1f} s) to {path}; lost packets {self.seqs.lost}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--serial", metavar="PORT")
    src.add_argument("--udp", metavar="DEVICE_IP", nargs="?", const="")
    ap.add_argument("--port", type=int, default=5005, help="device UDP port (default 5005)")
    ap.add_argument("--local-port", type=int, help="local UDP port (default: same as --port)")
    ap.add_argument("-o", "--out", default=None, help="output .npz (default rec_<time>.npz)")
    ap.add_argument("--rate", type=int, choices=(2000, 4000))
    ap.add_argument("--gain", type=int, choices=(1, 2, 3, 4, 6, 8, 12))
    ap.add_argument("--mode", choices=("normal", "test", "short"), default="normal")
    ap.add_argument("--leadoff", choices=("on", "off"))
    ap.add_argument("--duration", type=float, default=0, help="seconds (0 = until Ctrl-C)")
    ap.add_argument("--mains", type=float, default=50.0, help="notch frequency 50 or 60 (0 = off)")
    a = ap.parse_args()
    out = a.out or datetime.datetime.now().strftime("rec_%Y%m%d_%H%M%S.npz")

    link = SerialLink(a.serial) if a.serial is not None else UdpLink(a.udp, a.port, a.local_port)
    parser, rec = StreamParser(), Recorder(a.mains)

    def cmd(c, wait=0.3):
        link.send(c)
        t_end = time.time() + wait
        while time.time() < t_end:
            parser.feed(link.recv())
        for line in parser.lines:
            print(line)
        parser.lines.clear()

    cmd("stop", 0.5)
    if a.rate:
        cmd(f"rate {a.rate}")
    if a.gain:
        cmd(f"gain {a.gain}")
    cmd(a.mode)
    if a.leadoff:
        cmd(f"leadoff {a.leadoff}")
    cmd("status", 0.5)
    parser.feed(b"")
    link.send("start")
    started = time.time()
    try:
        while not a.duration or time.time() - started < a.duration:
            for p in parser.feed(link.recv()):
                rec.add(p)
            for line in parser.lines:
                print(line)
            parser.lines.clear()
            if rec.rate:
                rec.live(parser)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            link.send("stop")
        except Exception:
            pass
        rec.save(out, {"transport": link.name, "mode": a.mode, "mains": a.mains,
                       "started": datetime.datetime.fromtimestamp(started).isoformat(),
                       "bad_crc": parser.bad_crc})
        link.close()


if __name__ == "__main__":
    main()
