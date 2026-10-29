"""Supplement to coupling.py: electrode-net VIA LANDS as victims (coupling.py samples only tracks and pads).

For every via of an electrode net (both sides of the arrays), the land perimeter on each outer/signal layer
is sampled; each perimeter element ds facing other-net copper at edge gap g contributes c_m(g)*ds from the
2D tables (no-pour-between case unless real GND fill sits between). This is an edge-coupling estimate
(per-mm values of two parallel 0.1 mm strips), adequate for sub-mm features to about a factor of 2.
Also lists active vias whose barrels pass within 0.6 mm (centre-to-centre gap) of an electrode via.
Output: out/via_lands{TAG}.csv; printed summary with in-band uV using inject.py's aggressor spectra.
"""
import csv
import json
import math
import os
import re
import sys
from collections import defaultdict

import numpy as np
from shapely.geometry import Point

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pcbgeom import Board  # noqa: E402
import coupling as C  # noqa: E402

TAG = os.environ.get("TAG", "")


def main():
    b = Board(C.PCB)
    items = C.items_from_board(b)
    gfill = C.gnd_fill(b)
    trees = {ly: C.STRtree([it["poly"] for it in items[ly]]) for ly in items}
    acc = defaultdict(lambda: dict(cm=0.0, gmin=9.0, where=None))
    for v in b.vias:
        if not C.is_victim(v["net"]):
            continue
        for ly in ("F.Cu", "In2.Cu", "B.Cu"):
            # a land exists on F/B always; on In2 only where a track of the same net ends at the via
            if ly == "In2.Cu" and not any(t["layer"] == ly and t["net"] == v["net"] and
                                          (math.hypot(t["x1"] - v["x"], t["y1"] - v["y"]) < 0.05 or
                                           math.hypot(t["x2"] - v["x"], t["y2"] - v["y"]) < 0.05) for t in b.tracks):
                continue
            r = v["size"] / 2
            n = 72
            ds = 2 * math.pi * r / n
            land = Point(v["x"], v["y"]).buffer(r, 32)
            for k in range(n):
                a = 2 * math.pi * k / n
                p = Point(v["x"] + r * math.cos(a), v["y"] + r * math.sin(a))
                best = {}
                for idx in trees[ly].query(p.buffer(1.0)):
                    ai = items[ly][idx]
                    if ai["net"] in (v["net"], "GND", ""):
                        continue
                    g = ai["poly"].distance(p)
                    if g > 1.0 or ai["poly"].distance(land) < 1e-9 and g > 0.0 and False:
                        continue
                    # only the facing side: the nearest aggressor point must be outward of the land
                    q = ai["poly"].exterior.interpolate(ai["poly"].exterior.project(p))
                    outward = (q.x - v["x"]) * math.cos(a) + (q.y - v["y"]) * math.sin(a)
                    if outward <= 0:
                        continue
                    if ai["net"] not in best or g < best[ai["net"]][0]:
                        best[ai["net"]] = (g, q)
                for anet, (g, q) in best.items():
                    g = max(g, 0.1)
                    mid = Point((p.x + q.x) / 2, (p.y + q.y) / 2)
                    between = g >= 0.3 and ly in gfill and gfill[ly].contains(mid)
                    refp = True
                    if ly in ("In2.Cu", "B.Cu"):
                        al = "B.Cu" if ly == "In2.Cu" else "In2.Cu"
                        refp = al in gfill and gfill[al].contains(p)
                    c = C.cm_same(ly, g, refp, between) * ds
                    e = acc[(v["net"], anet, ly, (round(v["x"], 2), round(v["y"], 2)))]
                    e["cm"] += c
                    e["gmin"] = min(e["gmin"], g)
    # in-band uV with inject.py spectra
    import inject as I
    W = I.waveforms()
    spec = {k: I.inband_spectrum(x) for k, x in W.items()}
    rows = []
    for (vn, an, ly, at), e in acc.items():
        if e["cm"] < 0.05:
            continue
        uv = {}
        if an in spec:
            f, X = spec[an]
            for name, (R, Cc) in I.ZS.items():
                g = I.victim_gain(f, e["cm"] * 1e-15, R, Cc, ads_side=vn.startswith("Net-(RN"))
                uv[name] = math.sqrt(np.sum((np.abs(X) * g) ** 2) / 2) * 1e6
        rows.append(dict(victim=vn, via=at, layer=ly, aggressor=an, cm_fF=round(e["cm"], 3), gap_min_mm=round(e["gmin"], 3),
                         uV_1M10n=round(uv.get("1M||10n", float("nan")), 4), uV_1M1n=round(uv.get("1M||1n (adverse)", float("nan")), 4)))
    rows.sort(key=lambda r: -r["cm_fF"])
    with open(os.path.join(HERE, "out", f"via_lands{TAG}.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    act = {"/I2C_SCL", "/I2C_SDA", "/IMU_INT", "/LED", "Net-(D1-A)", "/ADC_DRDY", "/ADC_CS", "/SPI_SCK", "/SPI_MISO"}
    print("electrode via lands vs ACTIVE nets (fF, uVrms 1M||10n / 1M||1n):")
    for r in rows:
        if r["aggressor"] in act:
            print("  ", r)
    print("largest via-land couplings to any net:")
    for r in rows[:12]:
        print("  ", r)
    # barrel proximity
    print("active-net vias within 0.6 mm (land edge to land edge) of an electrode via:")
    for v in b.vias:
        if not C.is_victim(v["net"]):
            continue
        for u in b.vias:
            if u["net"] in act:
                d = math.hypot(u["x"] - v["x"], u["y"] - v["y"]) - (u["size"] + v["size"]) / 2
                if d < 0.6:
                    print("  ", v["net"], (v["x"], v["y"]), u["net"], (u["x"], u["y"]), round(d, 3))


if __name__ == "__main__":
    main()
