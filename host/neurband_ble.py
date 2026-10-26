#!/usr/bin/env python3
"""neurband rev C BLE recorder: scan, connect, stream, save .npz (same format as neurband_rec.py).

  python3 neurband_ble.py -o rec.npz                     # default: 2 kSPS, 16-bit, HP 20 Hz
  python3 neurband_ble.py --fmt 24 --rate 4000 -o raw.npz  # raw 24-bit at 4 kSPS (bring-up)
  python3 neurband_ble.py --mode short --duration 60       # shorted-input noise
  python3 neurband_ble.py --adapter hci1 ...               # Linux: use a second adapter (nRF52840 dongle)
  python3 -m analysis collect basic --out data/x --mark-udp 127.0.0.1:5006   # software markers

Needs numpy and bleak (pip install bleak). Ctrl-C stops and saves.
Packet format: docs/firmware_c.md (must match firmware_c/src/packet.h).
"""
import argparse
import asyncio
import collections
import datetime
import json
import socket
import struct
import sys
import time

import numpy as np

from neurband_rec import live_rms  # same live filter as the rev A/B recorder

NAME = "neurband"
_UUID = "4e420c0{}-6e65-7572-6261-6e6420726576"
SVC_UUID, DATA_UUID, CTRL_UUID, STATUS_UUID = (_UUID.format(i) for i in range(4))

NUM_CH = 8
VREF = 2.4
UV_PER_COUNT = 0.25
HDR = struct.Struct("<HIBBBBBB")  # seq, sample, type, n, flags, cfg, loff_p, loff_n
assert HDR.size == 12
DIAG = struct.Struct("<8iBBBBHHHH")
assert DIAG.size == 44
T_I16, T_I24, T_DIAG, T_IMU = 0, 1, 2, 3
IMU_SAMPLE = struct.Struct("<H6h")  # dt, gyro xyz, accel xyz (LSM6DSL register order)
IMU_G_PER_LSB, IMU_DPS_PER_LSB = 0.122e-3, 17.5e-3  # +-4 g, +-500 dps
IMU_META = {"model": "LSM6DSL", "odr_hz": 208, "accel_fs_g": 4, "gyro_fs_dps": 500,
            "columns": ["ax", "ay", "az", "gx", "gy", "gz"], "units": ["g", "g", "g", "dps", "dps", "dps"]}
F_MARKER, F_CHARGING, F_LOFF_EN, F_LOFF_ANY, F_MISSED, F_CLIP, F_LOWBAT, F_TEST = (1 << i for i in range(8))
PACKET_VERSION = "c1"


def lsb_volts(gain):
    """ADS1298 code weight: (2 * VREF / gain) / 2^24."""
    return 2.0 * VREF / gain / 2 ** 24


def parse_packet(buf):
    """Parse one notification. Returns a dict or None if malformed."""
    if len(buf) < HDR.size:
        return None
    seq, sample, typ, n, flags, cfg, lp, ln = HDR.unpack_from(buf, 0)
    gain = cfg & 0x0F
    p = {"seq": seq, "sample": sample, "type": typ, "flags": flags, "gain": gain,
         "loff_p": lp, "loff_n": ln, "hp": (0, 20, 40, 0)[(cfg >> 5) & 3]}
    body = memoryview(buf)[HDR.size:]
    if typ == T_I16:
        if len(body) != n * NUM_CH * 2 or n == 0:
            return None
        p["rate"] = 2000
        p["volts"] = np.frombuffer(body, "<i2").reshape(n, NUM_CH) * (UV_PER_COUNT * 1e-6)
    elif typ == T_I24:
        if len(body) != n * NUM_CH * 3 or n == 0 or gain == 0:
            return None
        p["rate"] = 4000 if cfg & 0x10 else 2000
        b = np.frombuffer(body, np.uint8).reshape(n, NUM_CH, 3).astype(np.int32)
        codes = (((b[..., 0] << 16) | (b[..., 1] << 8) | b[..., 2]) ^ 0x800000) - 0x800000
        p["codes"] = codes
        p["volts"] = codes * lsb_volts(gain)
    elif typ == T_DIAG:
        if len(body) != DIAG.size or gain == 0:
            return None
        f = DIAG.unpack_from(body, 0)
        p.update(dc=np.array(f[:8], np.int64) * lsb_volts(gain), rail=f[8], clip=f[9], rld_cfg=f[10],
                 rld_active=f[11], vbat_mv=f[12], overruns=f[13], drops=f[14], status_err=f[15])
    elif typ == T_IMU:
        if len(body) != n * IMU_SAMPLE.size or n == 0:
            return None
        r = np.frombuffer(body, np.dtype([("dt", "<u2"), ("v", "<i2", 6)]))
        p["imu_sample"] = sample + r["dt"].astype(np.int64)
        v = r["v"].astype(np.float32)
        p["imu"] = np.concatenate([v[:, 3:] * IMU_G_PER_LSB, v[:, :3] * IMU_DPS_PER_LSB], axis=1)
    else:
        return None
    return p


def build_packet(seq, sample, typ, data=None, flags=0, gain=6, rate4k=False, hp=20, loff_p=0, loff_n=0, diag=None):
    """Encode a packet exactly like firmware_c/src/acq.c / imu.c (tests / simulators).
    data: int16 counts [n, 8] (T_I16), int24 codes [n, 8] (T_I24), or [n, 7] rows of
    (dt, gx, gy, gz, ax, ay, az) raw LSM6DSL values (T_IMU); diag: dict for T_DIAG."""
    cfg = (gain & 0x0F) | (0x10 if rate4k else 0) | ({0: 0, 20: 1, 40: 2}[hp] << 5 if typ == T_I16 else 0)
    if typ == T_I16:
        body = np.asarray(data, "<i2").tobytes()
    elif typ == T_IMU:
        body = b"".join(IMU_SAMPLE.pack(*[int(x) for x in row]) for row in data)
    elif typ == T_I24:
        u = (np.asarray(data, np.int64) & 0xFFFFFF).astype(np.uint32)
        body = np.stack([(u >> 16) & 0xFF, (u >> 8) & 0xFF, u & 0xFF], -1).astype(np.uint8).tobytes()
    else:
        d = diag or {}
        body = DIAG.pack(*[int(v) for v in d.get("dc", [0] * 8)], d.get("rail", 0), d.get("clip", 0),
                         d.get("rld_cfg", 3), d.get("rld_active", 3), d.get("vbat_mv", 3900),
                         d.get("overruns", 0), d.get("drops", 0), d.get("status_err", 0))
    n = 0 if data is None else len(data)
    return HDR.pack(seq & 0xFFFF, sample, typ, n, flags, cfg, loff_p, loff_n) + body


class SeqTracker:
    """Lost notifications from the 16-bit sequence number (wraps every 65536 packets)."""

    def __init__(self):
        self.last = None
        self.lost = 0

    def update(self, seq):
        if self.last is not None:
            self.lost += (seq - self.last - 1) & 0xFFFF
        self.last = seq


class MarkerClock:
    """Maps host monotonic time to the device sample index from recent packets.
    The smallest (receive time - device time) over the last few seconds is the least-delayed
    packet; error ~ the minimum BLE latency (one connection interval, ~10 ms)."""

    def __init__(self, window_s=5.0):
        self.win = collections.deque()
        self.window_s = window_s
        self.rate = None

    def update(self, t_rx, end_sample, rate):
        if rate != self.rate:
            self.win.clear()
            self.rate = rate
        self.win.append((t_rx, t_rx - end_sample / rate))
        while self.win and t_rx - self.win[0][0] > self.window_s:
            self.win.popleft()

    def sample_at(self, t_host):
        if not self.win:
            return None
        off = min(d for _, d in self.win)
        return int(round((t_host - off) * self.rate))


class Recorder:
    def __init__(self, mains=50.0):
        self.mains = mains
        self.volts, self.samples, self.gains = [], [], []
        self.pk = collections.defaultdict(list)  # per-packet arrays
        self.diag = collections.defaultdict(list)
        self.imu, self.imu_sample = [], []
        self.markers = []  # (sample index, source 0 button / 1 software, label)
        self.seqs = SeqTracker()
        self.rate = None
        self.n = 0
        self.missed_samples = 0
        self.live_buf, self.sec_start = [], time.monotonic()
        self.last_diag = None
        self.clock = MarkerClock()
        self.next_sample = None

    def add(self, p, t_mono_ns=None, t_wall=None):
        t_mono_ns = time.monotonic_ns() if t_mono_ns is None else t_mono_ns
        t_wall = time.time() if t_wall is None else t_wall
        self.seqs.update(p["seq"])
        if p["type"] == T_DIAG:
            self.last_diag = p
            for k in ("dc", "rail", "clip", "rld_cfg", "rld_active", "vbat_mv", "overruns", "drops", "loff_p", "loff_n"):
                self.diag[k].append(p[k])
            self.diag["sample"].append(p["sample"])
            self.diag["rx_mono_ns"].append(t_mono_ns)
            return
        if p["type"] == T_IMU:
            self.imu.append(p["imu"])
            self.imu_sample.append(p["imu_sample"])
            return
        v = p["volts"]
        if self.rate is None:
            self.rate = p["rate"]
        elif p["rate"] != self.rate:
            print(f"! rate changed {self.rate} -> {p['rate']} mid-recording", file=sys.stderr)
            self.rate = p["rate"]
        if self.next_sample is not None and p["sample"] != self.next_sample:
            self.missed_samples += max(0, p["sample"] - self.next_sample)
        self.next_sample = p["sample"] + len(v)
        self.volts.append(v.astype(np.float32))
        self.samples.append(p["sample"] + np.arange(len(v), dtype=np.int64))
        self.gains.append(np.full(len(v), p["gain"], np.uint8))
        for k in ("seq", "sample", "flags", "loff_p", "loff_n"):
            self.pk[k].append(p[k])
        self.pk["rx_mono_ns"].append(t_mono_ns)
        self.pk["rx_wall"].append(t_wall)
        self.pk["type"].append(p["type"])
        self.pk["hp"].append(p["hp"])
        if p["flags"] & F_MARKER:
            self.markers.append((p["sample"], 0, "button"))
            print(f"\n* button marker at sample {p['sample']}")
        self.clock.update(t_mono_ns / 1e9, p["sample"] + len(v), self.rate)
        self.n += len(v)
        self.live_buf.append(v)

    def software_marker(self, label, t_mono_ns=None):
        t = (time.monotonic_ns() if t_mono_ns is None else t_mono_ns) / 1e9
        s = self.clock.sample_at(t)
        if s is None:
            print(f"! marker '{label}' before the first packet, ignored", file=sys.stderr)
            return
        self.markers.append((s, 1, label))

    def live(self):
        if not self.rate or time.monotonic() - self.sec_start < 1.0 or sum(map(len, self.live_buf)) < self.rate // 2:
            return
        x = np.concatenate(self.live_buf)[-2 * self.rate:]
        self.live_buf = [x]
        rms = live_rms(x, self.rate, self.mains) * 1e6
        line = f"t={self.n / self.rate:7.1f}s rms[uV] " + " ".join(f"{r:6.1f}" for r in rms)
        d = self.last_diag
        if d:
            lo = "".join("X" if (d["loff_p"] >> c) & (d["loff_n"] >> c) & 1 else "P" if (d["loff_p"] >> c) & 1
                         else "N" if (d["loff_n"] >> c) & 1 else "." for c in range(NUM_CH))
            line += (f"\n           dc[mV] " + " ".join(f"{v * 1e3:6.1f}" for v in d["dc"])
                     + f"  loff[{lo}] rail=0x{d['rail']:02x} clip=0x{d['clip']:02x} rld=0x{d['rld_active']:02x}"
                     f" vbat={d['vbat_mv']} ovr={d['overruns']} fw_drops={d['drops']}")
        print(line + f"  lost_pkts={self.seqs.lost} gap_samples={self.missed_samples}")
        self.sec_start = time.monotonic()

    def save(self, path, meta):
        if not self.volts:
            print("nothing recorded")
            return
        emg = np.concatenate(self.volts)
        idx = np.concatenate(self.samples)
        rate = self.rate
        t = (idx - idx[0]) / rate  # device clock; jumps over lost samples (never interpolated)
        mk = sorted(self.markers)
        markers = np.array([np.searchsorted(idx, m[0]).clip(0, len(idx) - 1) for m in mk], np.int64)
        pk = {k: np.array(v) for k, v in self.pk.items()}
        pkt_t_us = ((pk["sample"] - idx[0]) * 1e6 / rate).astype(np.int64)
        gains = np.concatenate(self.gains)
        meta = dict(meta, rate=rate, gain=int(gains[-1]), vref=VREF, lsb_volts=lsb_volts(int(gains[-1])),
                    n_samples=int(len(emg)), n_channels=NUM_CH, channels=[f"ch{i + 1}" for i in range(NUM_CH)],
                    lost_packets=self.seqs.lost, missed_samples=self.missed_samples, restarts=0,
                    fw_drops=int(self.diag["drops"][-1]) if self.diag["drops"] else 0,
                    packet_version=PACKET_VERSION, board="neurband_c",
                    # fmt 16: the 127-tap FIR delays the EMG by 15.75 ms relative to its index
                    emg_delay_s=0.01575 if self.pk["type"] and self.pk["type"][0] == T_I16 else 0.0)
        out = dict(emg=emg, t=t, gain=gains, sample_index=idx,
                   pkt_seq=pk["seq"].astype(np.uint16), pkt_sample=pk["sample"].astype(np.int64),
                   pkt_t_us=pkt_t_us, pkt_flags=pk["flags"].astype(np.uint8),
                   pkt_rx_mono_ns=pk["rx_mono_ns"].astype(np.int64), pkt_rx_wall=pk["rx_wall"].astype(np.float64),
                   loff_p=pk["loff_p"].astype(np.uint16), loff_n=pk["loff_n"].astype(np.uint16),
                   markers=markers, marker_t=t[markers] if len(markers) else np.zeros(0),
                   marker_src=np.array([m[1] for m in mk], np.uint8),
                   marker_label=np.array([m[2] for m in mk], dtype=str),
                   meta=json.dumps(meta))
        if self.diag["sample"]:
            out.update(diag_sample=np.array(self.diag["sample"], np.int64),
                       diag_t=(np.array(self.diag["sample"]) - idx[0]) / rate,
                       diag_dc=np.array(self.diag["dc"], np.float32),
                       diag_loff_p=np.array(self.diag["loff_p"], np.uint8),
                       diag_loff_n=np.array(self.diag["loff_n"], np.uint8),
                       diag_rail=np.array(self.diag["rail"], np.uint8),
                       diag_clip=np.array(self.diag["clip"], np.uint8),
                       diag_rld_active=np.array(self.diag["rld_active"], np.uint8),
                       diag_vbat_mv=np.array(self.diag["vbat_mv"], np.uint16),
                       diag_rx_mono_ns=np.array(self.diag["rx_mono_ns"], np.int64))
        if self.imu:
            isamp = np.concatenate(self.imu_sample)
            out.update(imu=np.concatenate(self.imu).astype(np.float32), imu_sample=isamp,
                       imu_t=(isamp - idx[0]) / rate)
            meta["imu"] = IMU_META
            out["meta"] = json.dumps(meta)
        np.savez(path, **out)
        print(f"saved {len(emg)} samples ({len(emg) / rate:.1f} s) to {path}; lost packets {self.seqs.lost}, "
              f"missing samples {self.missed_samples}, markers {len(mk)}")


def parse_status(s):
    """'key=value key=value ...' from the status characteristic -> dict of strings."""
    return dict(kv.split("=", 1) for kv in s.split() if "=" in kv)


class MarkerProtocol(asyncio.DatagramProtocol):
    """Receives 'MARK <label>' datagrams from analysis.collect (--mark-udp HOST:PORT)."""

    def __init__(self, rec):
        self.rec = rec

    def datagram_received(self, data, addr):
        t = time.monotonic_ns()
        msg = data.decode("utf-8", "replace").strip()
        if msg.startswith("MARK"):
            self.rec.software_marker(msg[4:].strip() or "mark", t)


def try_linux_2m(adapter):
    """Best effort: allow LE 2M in the adapter's PHY selection (BlueZ btmgmt, needs root)."""
    import subprocess
    idx = adapter[3:] if adapter and adapter.startswith("hci") else "0"
    cmd = ["btmgmt", "--index", idx, "phy", "LE1MTX", "LE1MRX", "LE2MTX", "LE2MRX"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        print("btmgmt phy:", (r.stdout + r.stderr).strip()[:200])
    except (OSError, subprocess.SubprocessError) as e:
        print(f"btmgmt not usable ({e}); the band still requests 2M itself")


async def run(a):
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        sys.exit("bleak missing: pip install bleak")
    kw = {"adapter": a.adapter} if a.adapter else {}
    if sys.platform.startswith("linux"):
        try_linux_2m(a.adapter)
    print(f"scanning for '{a.name}' ...")
    if a.address:
        dev = await BleakScanner.find_device_by_address(a.address, timeout=15, **kw)
    else:
        dev = await BleakScanner.find_device_by_filter(
            lambda d, ad: (ad.local_name or d.name) == a.name or SVC_UUID in (ad.service_uuids or []),
            timeout=15, **kw)
    if dev is None:
        sys.exit("band not found (is it advertising? LED flashes once per second)")
    rec = Recorder(a.mains)
    loop = asyncio.get_running_loop()
    if a.mark_udp:
        host, port = a.mark_udp.rsplit(":", 1) if ":" in a.mark_udp else ("127.0.0.1", a.mark_udp)
        await loop.create_datagram_endpoint(lambda: MarkerProtocol(rec), local_addr=(host, int(port)))
        print(f"software markers: listening on udp {host}:{port}")
    stop = asyncio.Event()
    started = time.time()
    meta = {"transport": "ble", "mode": a.mode, "mains": a.mains, "fmt": a.fmt,
            "started": datetime.datetime.fromtimestamp(started).isoformat(), "started_host": started,
            "started_mono_ns": time.monotonic_ns()}

    def on_data(_, data):
        p = parse_packet(bytes(data))
        if p is None:
            rec.pk_bad = getattr(rec, "pk_bad", 0) + 1
            return
        rec.add(p)

    async with BleakClient(dev, disconnected_callback=lambda c: stop.set(), **kw) as client:
        print(f"connected to {dev.address}, host-side ATT MTU {client.mtu_size}")

        async def cmd(c, wait=0.3):
            await client.write_gatt_char(CTRL_UUID, c.encode(), response=True)
            await asyncio.sleep(wait)
            st = (await client.read_gatt_char(STATUS_UUID)).decode("ascii", "replace")
            return parse_status(st)

        st = await cmd("stop", 1.0)  # the band powers the AFE on connect (~0.6 s)
        settings = [f"fmt {a.fmt}", f"gain {a.gain}", f"hp {a.hp}", f"rld {a.rld}",
                    f"test {'on' if a.mode == 'test' else 'off'}", f"short {'on' if a.mode == 'short' else 'off'}"]
        if a.rate:
            settings.append(f"rate {a.rate}")
        if a.leadoff:
            settings.append(f"leadoff {a.leadoff}")
        for c in settings:
            st = await cmd(c)
            if st.get("last", "").startswith("err"):
                print(f"! band rejected '{c}'", file=sys.stderr)
        print("status:", " ".join(f"{k}={v}" for k, v in st.items()))
        if st.get("chg") == "1":
            sys.exit("band is charging: streaming is disabled (never wear it while charging)")
        if st.get("ads") != "0x92":
            print(f"! ADS1298 ID {st.get('ads')} (expected 0x92)", file=sys.stderr)
        meta.update(firmware=st.get("fw"), status_start=st)
        await client.start_notify(DATA_UUID, on_data)
        st = await cmd("start", 0.8)
        print("link:", {k: st.get(k) for k in ("mtu", "phy", "dle", "ci")}, "last:", st.get("last"))
        meta["link"] = {k: st.get(k) for k in ("mtu", "phy", "dle", "ci")}
        try:
            while not stop.is_set() and (not a.duration or time.time() - started < a.duration):
                await asyncio.sleep(0.1)
                rec.live()
        except asyncio.CancelledError:
            pass
        finally:
            if client.is_connected:
                try:
                    meta["status_end"] = await cmd("stop", 0.2)
                    await client.stop_notify(DATA_UUID)
                except Exception as e:  # noqa: BLE001 - save the data whatever happens
                    print(f"stop failed: {e}", file=sys.stderr)
            meta["bad_packets"] = getattr(rec, "pk_bad", 0)
            rec.save(a.out, meta)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default=None, help="output .npz (default rec_<time>.npz)")
    ap.add_argument("--name", default=NAME)
    ap.add_argument("--address", help="connect to this BLE address instead of scanning by name")
    ap.add_argument("--adapter", help="Linux only: hciN (e.g. an nRF52840 dongle running hci_usb)")
    ap.add_argument("--fmt", type=int, choices=(16, 24), default=16,
                    help="16: 4 kSPS acquisition, FIR -> 2 kSPS, HP, 0.25 uV/count (default); 24: raw")
    ap.add_argument("--rate", type=int, choices=(2000, 4000), help="raw 24-bit stream rate")
    ap.add_argument("--gain", type=int, choices=(1, 2, 3, 4, 6, 8, 12), default=6)
    ap.add_argument("--hp", type=int, choices=(20, 40), default=20, help="high-pass of the 16-bit stream, Hz")
    ap.add_argument("--rld", default="0x03", help="RLD sense channel mask (P+N), e.g. 0x03, 0 = mid-supply bias only")
    ap.add_argument("--mode", choices=("normal", "test", "short"), default="normal")
    ap.add_argument("--leadoff", choices=("on", "off"))
    ap.add_argument("--duration", type=float, default=0, help="seconds (0 = until Ctrl-C)")
    ap.add_argument("--mains", type=float, default=50.0, help="notch for the live RMS: 50 or 60 (0 = off)")
    ap.add_argument("--mark-udp", default="127.0.0.1:5006", metavar="[HOST:]PORT",
                    help="UDP port for 'MARK <label>' from analysis.collect (default 127.0.0.1:5006, '' = off)")
    a = ap.parse_args()
    a.out = a.out or datetime.datetime.now().strftime("rec_%Y%m%d_%H%M%S.npz")
    try:
        asyncio.run(run(a))
    except KeyboardInterrupt:
        pass  # run() saves in its finally block


if __name__ == "__main__":
    main()
