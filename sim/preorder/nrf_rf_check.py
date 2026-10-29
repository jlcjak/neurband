"""nRF52832 RF / decoupling layout check against Nordic's QFN48 LDO-mode reference (PS v1.x, ref. circuitry).

Reports, from the saved board: pin-to-capacitor distances and connecting track length for DEC1/DEC3/DEC4/VDD,
each capacitor GND pad's distance to its nearest GND via (return path), the C21 return, L1 placement, crystal
Y1 + C19/C20 routing/ground, copper under the matching section on inner/bottom layers, post-match feed width
and pour spacing, and other-net copper near the crystal and the RF section.
Output: out/nrf_rf_check{TAG}.json; printed report.
"""
import heapq
import json
import math
import os
import sys
from collections import defaultdict

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pcbgeom import Board  # noqa: E402

PCB = os.environ.get("PCB") or os.path.join(HERE, "../../boards/neurband_c/neurband_c.kicad_pcb")
TAG = os.environ.get("TAG", "")


def track_path_length(b, net, a, z):
    """Shortest copper path (mm) along tracks/vias of `net` between pad positions a and z (any layer)."""
    nodes = defaultdict(list)
    def key(x, y):
        return (round(x, 3), round(y, 3))
    pts = []
    for t in b.tracks:
        if t["net"] != net:
            continue
        p, q = key(t["x1"], t["y1"]), key(t["x2"], t["y2"])
        L = math.hypot(p[0] - q[0], p[1] - q[1])
        nodes[p].append((q, L))
        nodes[q].append((p, L))
        pts += [p, q]
    # vias join layers at the same xy (keys already merge); pads: connect pad centre to track ends within the pad
    def attach(c, r=0.35):
        k = ("pad", c)
        for p in set(pts):
            d = math.hypot(p[0] - c[0], p[1] - c[1])
            if d <= r:
                nodes[k].append((p, d))
                nodes[p].append((k, d))
        return k
    s, e = attach(a), attach(z)
    dist = {s: 0.0}
    h = [(0.0, 0, s)]
    cnt = 1
    while h:
        d, _, u = heapq.heappop(h)
        if u == e:
            return d
        if d > dist.get(u, 1e9):
            continue
        for v, w in nodes[u]:
            nd = d + w
            if nd < dist.get(v, 1e9):
                dist[v] = nd
                heapq.heappush(h, (nd, cnt, v))
                cnt += 1
    return None


def main():
    b = Board(PCB)
    pads = defaultdict(list)
    for p in b.pads:
        pads[p["ref"]].append(p)
    def pad(ref, num):
        return next(p for p in pads[ref] if p["num"] == num)
    gv = [v for v in b.vias if v["net"] == "GND"]
    def nearest_gnd_via(p):
        return min(math.hypot(v["x"] - p["x"], v["y"] - p["y"]) for v in gv)
    u1 = {p["num"]: p for p in pads["U1"]}
    rep = {"pins": {}, "caps": [], "notes": []}
    for num in ("1", "13", "30", "31", "32", "33", "34", "35", "36", "45", "46", "47", "48"):
        if num in u1:
            p = u1[num]
            rep["pins"][num] = dict(net=p["net"], x=round(p["x"], 3), y=round(p["y"], 3))
    ep = [p for p in pads["U1"] if p["w"] > 3]
    ep_poly = b.pad_poly(ep[0]) if ep else None
    ep_vias = [v for v in gv if ep_poly is not None and ep_poly.contains(Point(v["x"], v["y"]))]
    rep["ep_vias"] = len(ep_vias)
    # capacitors on nRF supply/decoupling nets
    for net in ("/DEC1", "/DEC3", "/DEC4", "+3V3"):
        pins = [p for p in u1.values() if p["net"] == net]
        for ref, pl in pads.items():
            if not ref or ref[0] not in "C":
                continue
            sig = [p for p in pl if p["net"] == net]
            gnd = [p for p in pl if p["net"] == "GND"]
            if not sig or not gnd or not pins:
                continue
            s, g = sig[0], gnd[0]
            pin = min(pins, key=lambda q: math.hypot(q["x"] - s["x"], q["y"] - s["y"]))
            d = math.hypot(pin["x"] - s["x"], pin["y"] - s["y"])
            if net == "+3V3" and d > 6:
                continue
            L = track_path_length(b, net, (round(pin["x"], 3), round(pin["y"], 3)), (round(s["x"], 3), round(s["y"], 3)))
            # GND return: nearest GND via to the cap's GND pad, and to the U1 EP / pin 31/45
            rep["caps"].append(dict(ref=ref, net=net, pin=pin["num"], pin_to_pad_mm=round(d, 2),
                                    track_mm=None if L is None else round(L, 2),
                                    gnd_pad_to_gnd_via_mm=round(nearest_gnd_via(g), 2),
                                    gnd_pad_to_EP_edge_mm=round(ep_poly.distance(Point(g["x"], g["y"])), 2) if ep_poly else None))
    # C21 return, L1, matching section
    c21 = {p["num"]: p for p in pads["C21"]}
    rep["C21"] = {k: dict(net=v["net"], x=round(v["x"], 3), y=round(v["y"], 3)) for k, v in c21.items()}
    c21g = next(p for p in pads["C21"] if p["net"] == "GND")
    rep["C21"]["gnd_pad_to_nearest_GND_via_mm"] = round(nearest_gnd_via(c21g), 3)
    rep["C21"]["gnd_pad_to_U1_pin31_mm"] = round(math.hypot(c21g["x"] - u1["31"]["x"], c21g["y"] - u1["31"]["y"]), 3)
    # what GND copper touches the C21 GND pad on F.Cu: the fill polygon containing it, and its via ties
    fills = defaultdict(list)
    for z in b.zones:
        if z["net"] == "GND":
            for fl, pts in z["fills"]:
                g = make_valid(Polygon(pts))
                fills[fl] += list(g.geoms) if hasattr(g, "geoms") else [g]
    gtracks = [LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).buffer(t["w"] / 2)
               for t in b.tracks if t["net"] == "GND" and t["layer"] == "F.Cu" and (t["x1"], t["y1"]) != (t["x2"], t["y2"])]
    c21pad = b.pad_poly(c21g)
    touching = [f for f in fills["F.Cu"] if f.buffer(0.005).intersects(c21pad)]
    rep["C21"]["F_pour_touching_gnd_pad"] = len(touching)
    gt = [g for g in gtracks if g.intersects(c21pad.buffer(0.01))]
    rep["C21"]["GND_tracks_from_gnd_pad"] = len(gt)
    if gt:
        net_poly = unary_union(gt + [c21pad, b.pad_poly(u1["31"])])
        rep["C21"]["gnd_track_reaches_pin31"] = net_poly.buffer(0.01).intersects(b.pad_poly(u1["31"]))
        rep["C21"]["vias_on_that_gnd_track"] = [(v["x"], v["y"]) for v in gv if unary_union(gt).buffer(0.02).contains(Point(v["x"], v["y"]))]
    l1 = {p["num"]: p for p in pads["L1"]}
    rep["L1"] = {k: dict(net=v["net"], x=round(v["x"], 3), y=round(v["y"], 3)) for k, v in l1.items()}
    rep["L1"]["ANT_pin_to_L1_mm"] = round(min(math.hypot(v["x"] - u1["30"]["x"], v["y"] - u1["30"]["y"]) for v in l1.values()), 2)
    rep["C21_ANT_to_pin30_mm"] = round(min(math.hypot(v["x"] - u1["30"]["x"], v["y"] - u1["30"]["y"]) for v in c21.values() if v["net"] != "GND"), 2)
    # matching keepout zone and copper under it
    mz = [z for z in b.zones if "Nordic ANT" in z["name"]]
    if mz:
        kp = Polygon(mz[0]["outline"])
        rep["match_keepout_bbox"] = [round(x, 2) for x in kp.bounds]
        rep["match_keepout_layers"] = mz[0]["layers"]
        under = {}
        for ly in ("In1.Cu", "In2.Cu", "B.Cu"):
            a = sum(f.intersection(kp).area for f in fills[ly])
            tr = [t["net"] for t in b.tracks if t["layer"] == ly and LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).intersects(kp)]
            vi = [v["net"] for v in b.vias if kp.contains(Point(v["x"], v["y"]))]
            under[ly] = dict(gnd_fill_mm2=round(a, 4), tracks=sorted(set(tr)), vias=sorted(set(vi)))
        rep["copper_under_matching"] = under
        # does the keepout cover L1, C21 and the ANT pin?
        rep["keepout_covers"] = {r: all(kp.buffer(0.02).contains(Point(p["x"], p["y"])) for p in pads[r]) for r in ("L1", "C21")}
        rep["keepout_covers"]["U1.30"] = kp.buffer(0.02).contains(Point(u1["30"]["x"], u1["30"]["y"]))
    # feed: RF net tracks and their widths, spacing to other copper on F.Cu
    rf_nets = ("Net-(U1-ANT)", "Net-(C22-Pad1)", "Net-(AE1-A)")
    feed = {}
    others = []
    for t in b.tracks:
        if t["layer"] == "F.Cu" and t["net"] not in rf_nets:
            if (t["x1"], t["y1"]) != (t["x2"], t["y2"]):
                others.append((t["net"], LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).buffer(t["w"] / 2)))
    for p in b.pads:
        if "F.Cu" in p["layers"] and p["net"] not in rf_nets and p["ref"] not in ("AE1",):
            others.append((p["net"], b.pad_poly(p)))
    for f in fills["F.Cu"]:
        others.append(("GND pour", f))
    for net in rf_nets:
        ts = [t for t in b.tracks if t["net"] == net]
        geom = unary_union([LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).buffer(t["w"] / 2) for t in ts
                            if (t["x1"], t["y1"]) != (t["x2"], t["y2"])])
        L = sum(math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"]) for t in ts)
        dmin = {}
        for n, g in others:
            d = geom.distance(g)
            if d < 0.6:
                dmin[n] = round(min(d, dmin.get(n, 9)), 3)
        feed[net] = dict(widths=sorted({t["w"] for t in ts}), length_mm=round(L, 2), layers=sorted({t["layer"] for t in ts}),
                         nearest_other_copper_mm=dict(sorted(dmin.items(), key=lambda kv: kv[1])[:8]))
    rep["rf_feed"] = feed
    # crystal: XC1/XC2 track lengths, Y1 pads, caps, nearby other-net copper on all layers
    xc = {}
    for net in ("Net-(U1-XC1)", "Net-(U1-XC2)"):
        ts = [t for t in b.tracks if t["net"] == net]
        xc[net] = dict(length_mm=round(sum(math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"]) for t in ts), 2),
                       layers=sorted({t["layer"] for t in ts}), widths=sorted({t["w"] for t in ts}),
                       vias=sum(1 for v in b.vias if v["net"] == net))
    rep["crystal_nets"] = xc
    y1 = pads["Y1"]
    rep["Y1_pads"] = [dict(num=p["num"], net=p["net"], x=round(p["x"], 2), y=round(p["y"], 2)) for p in y1]
    for ref in ("C19", "C20"):
        g = next(p for p in pads[ref] if p["net"] == "GND")
        rep[f"{ref}_gnd_to_gnd_via_mm"] = round(nearest_gnd_via(g), 2)
    region = unary_union([b.pad_poly(p) for p in y1 + pads["C19"] + pads["C20"]] +
                         [LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).buffer(t["w"] / 2) for t in b.tracks
                          if t["net"] in ("Net-(U1-XC1)", "Net-(U1-XC2)") and (t["x1"], t["y1"]) != (t["x2"], t["y2"])])
    near = defaultdict(lambda: 9.0)
    for t in b.tracks:
        if t["net"] in ("GND", "Net-(U1-XC1)", "Net-(U1-XC2)") or (t["x1"], t["y1"]) == (t["x2"], t["y2"]):
            continue
        g = LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).buffer(t["w"] / 2)
        d = region.distance(g)
        if d < 1.0:
            k = (t["net"], t["layer"])
            near[k] = min(near[k], round(d, 3))
    for v in b.vias:
        if v["net"] in ("GND", "Net-(U1-XC1)", "Net-(U1-XC2)"):
            continue
        d = region.distance(Point(v["x"], v["y"]).buffer(v["size"] / 2))
        if d < 1.0:
            k = (v["net"], "via")
            near[k] = min(near[k], round(d, 3))
    rep["other_copper_within_1mm_of_crystal"] = {f"{k[0]} [{k[1]}]": v for k, v in sorted(near.items(), key=lambda kv: kv[1])}
    rep["in1_under_crystal_pct"] = round(100 * sum(f.intersection(region.envelope).area for f in fills["In1.Cu"]) / region.envelope.area, 1)
    # digital/power copper under the matching network and the crystal on In2/B.Cu
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    json.dump(rep, open(os.path.join(HERE, "out", f"nrf_rf_check{TAG}.json"), "w"), indent=1, default=str)
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
