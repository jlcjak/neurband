"""DC resistance of the rev C power paths on the saved board (tracks + vias), and drops at the stated currents.

Copper: F/B 35 um, In1/In2 15.2 um (as-built 3313 stack, docs/layout/main_c_layout.md), rho = 1.72e-8 ohm m;
plated via 0.30 mm drill, 1.0 mm long, 20 um plating -> ~0.9 mOhm. Pads are joined to track ends inside them.
The lowest-resistance path is reported (parallel paths would lower it slightly).
Output: out/power_paths{TAG}.json; printed table.
"""
import heapq
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pcbgeom import Board  # noqa: E402

PCB = os.environ.get("PCB") or os.path.join(HERE, "../../boards/neurband_c/neurband_c.kicad_pcb")
TAG = os.environ.get("TAG", "")
RHO = 1.72e-8
TCU = {"F.Cu": 35e-6, "B.Cu": 35e-6, "In1.Cu": 15.2e-6, "In2.Cu": 15.2e-6}
if os.environ.get("INNER35"):
    TCU["In2.Cu"] = TCU["In1.Cu"] = 35e-6
R_VIA = RHO * 1.0e-3 / (math.pi * 0.30e-3 * 20e-6)


def graph(b, net):
    G = defaultdict(list)
    def k(x, y, ly):
        return (round(x, 3), round(y, 3), ly)
    ends = []
    for t in b.tracks:
        if t["net"] != net:
            continue
        a, c = k(t["x1"], t["y1"], t["layer"]), k(t["x2"], t["y2"], t["layer"])
        L = math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"]) * 1e-3
        R = RHO * L / (t["w"] * 1e-3 * TCU[t["layer"]]) if L > 0 else 1e-6
        G[a].append((c, R))
        G[c].append((a, R))
        ends += [a, c]
    for v in b.vias:
        if v["net"] != net:
            continue
        pts = [e for e in ends if math.hypot(e[0] - v["x"], e[1] - v["y"]) < v["size"] / 2 + 1e-3]
        hub = ("via", round(v["x"], 3), round(v["y"], 3))
        for e in pts:
            G[hub].append((e, R_VIA / 2))
            G[e].append((hub, R_VIA / 2))
    return G, ends


def attach(G, ends, p, tag):
    hub = ("pad", tag)
    poly_r = max(p["w"], p["h"]) / 2 + 0.01
    for e in ends:
        if (e[2] in p["layers"] or "*.Cu" in p["layers"]) and math.hypot(e[0] - p["x"], e[1] - p["y"]) <= poly_r:
            G[hub].append((e, 1e-5))
            G[e].append((hub, 1e-5))
    return hub


def rpath(G, s, e):
    dist = {s: 0.0}
    h = [(0.0, 0, s)]
    n = 1
    while h:
        d, _, u = heapq.heappop(h)
        if u == e:
            return d
        if d > dist.get(u, 1e9):
            continue
        for v, w in G[u]:
            nd = d + w
            if nd < dist.get(v, 1e9):
                dist[v] = nd
                heapq.heappush(h, (nd, n, v))
                n += 1
    return None


def main():
    b = Board(PCB)
    pads = {(p["ref"], p["num"]): p for p in b.pads}
    def P(ref, net):
        return [p for p in b.pads if p["ref"] == ref and p["net"] == net]
    cases = [
        ("VBAT", ("J2", "VBAT"), ("U3", "VBAT"), 0.025, "battery -> LDO input (radio peak ~25 mA)"),
        ("VBAT", ("J2", "VBAT"), ("C26", "VBAT"), 0.025, "battery -> LDO input cap"),
        ("VBAT", ("J2", "VBAT"), ("U4", "VBAT"), 0.10, "battery <-> charger BAT (100 mA charging, off-body)"),
        ("+3V3", ("U3", "+3V3"), ("C27", "+3V3"), 0.025, "LDO out -> C27"),
        ("+3V3", ("U3", "+3V3"), ("U1", "+3V3"), 0.020, "LDO out -> nRF VDD (nearest pin)"),
        ("+3V3", ("U3", "+3V3"), ("R5", "+3V3"), 0.003, "LDO out -> AVDD filter R5"),
        ("+3V3", ("U3", "+3V3"), ("U2", "+3V3"), 0.001, "LDO out -> ADS DVDD"),
        ("+3V3", ("U3", "+3V3"), ("U5", "+3V3"), 0.001, "LDO out -> IMU"),
        ("+3V3A", ("R5", "+3V3A"), ("U2", "+3V3A"), 0.003, "R5 -> ADS AVDD (nearest pin)"),
    ]
    out = []
    for net, (ra, na), (rb, nb), I, desc in cases:
        G, ends = graph(b, net)
        best = None
        for pa in P(ra, na):
            for pb in P(rb, nb):
                s = attach(G, ends, pa, f"{ra}.{pa['num']}")
                e = attach(G, ends, pb, f"{rb}.{pb['num']}")
                r = rpath(G, s, e)
                if r is not None and (best is None or r < best):
                    best = r
        out.append(dict(net=net, path=desc, R_mohm=None if best is None else round(best * 1e3, 1),
                        I_mA=I * 1e3, drop_mV=None if best is None else round(best * I * 1e3, 2)))
    # shared segment between the radio current and the AVDD tap: LDO -> nRF vs LDO -> R5
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "out", f"power_paths{TAG}.json"), "w"), indent=1)
    for r in out:
        print(f"{r['net']:6s} {r['path']:52s} R {r['R_mohm']} mOhm  @ {r['I_mA']:.0f} mA -> {r['drop_mV']} mV")
    # track widths used per power net and layer
    w = defaultdict(lambda: defaultdict(float))
    for t in b.tracks:
        if t["net"] in ("VBAT", "+3V3", "+3V3A", "VCHG"):
            w[t["net"]][(t["layer"], t["w"])] += math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"])
    for n, d in w.items():
        print(n, {f"{k[0]} {k[1]}": round(v, 1) for k, v in sorted(d.items())})


if __name__ == "__main__":
    main()
