"""Extract victim/aggressor parallel runs, crossings and mutual capacitance from the rev C main board.

Victims: the 16 electrode nets on both sides of RN1-RN4, BIAS_E, RLDOUT, RLDINV, RLDREF (and the
reference/VCAP nets for information). Aggressors: every other non-GND net.

Method (2.5D): victim copper (tracks, pads as their long-axis centre line) is sampled every 25 um.
 * same layer: edge-to-edge gap to every aggressor item within 1.5 mm; c_m(gap) from the 2D FD tables
   (out/xsec_tables.json) choosing "GND pour between / not between" from the real filled zones at the
   midpoint and "reference pour present / absent" on the adjacent layer for In2/B.Cu;
 * In2 <-> B.Cu (0.1 mm FR-4): parallel broadside runs use the 2D broadside table vs centre offset;
   crossings (>30 deg) count a lumped crossing capacitance;
 * F.Cu <-> In2 and In1 are shielded by the solid In1 GND (antipads ignored).
Outputs: out/coupling_pairs.csv (one row per victim/aggressor/layer), build/coupling_samples.json.
"""
import csv
import json
import math
import os
import re
import sys
from collections import defaultdict

import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pcbgeom import Board  # noqa: E402

PCB = os.path.join(HERE, "../../boards/neurband_c/neurband_c.kicad_pcb")
# XSEC selects the cross-section tables (xsec_tables.json = first-review stack, xsec_tables_3313.json = as-built);
# TAG suffixes the outputs so runs on different boards/stacks do not overwrite each other.
TAB = json.load(open(os.path.join(HERE, "out", os.environ.get("XSEC", "xsec_tables.json"))))
TAGS = os.environ.get("TAG", "")
STEP = 0.025
GMAX = 1.5
EPS0 = 8.854e-12


def is_victim(net):
    return bool(re.fullmatch(r"/E\d[PN]", net) or net.startswith("Net-(RN") or
                net in ("/BIAS_E", "Net-(U2-RLDOUT)", "/RLD_DRV", "Net-(U2-RLDINV)", "/RLDREF"))


def interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return 0.0
    return float(np.interp(x, xs, ys))


def cm_same(layer, gap, ref_pour, between):
    key = {"F.Cu": "F", "In2.Cu": "In2", "B.Cu": "B"}[layer]
    rk = f"{key}_ref{int(ref_pour) if key != 'F' else 1}_between{int(between)}"
    rows = TAB[rk]
    return interp(TAB["gaps_mm"], [r["cm"] for r in rows], gap)


def cm_broadside(offset, pour):
    rows = TAB[f"broadside_pour{int(pour)}"]
    return interp(TAB["broadside_offsets_mm"], [r["cm"] for r in rows], offset)


def items_from_board(b):
    """Copper items per layer: dict(layer -> list of (geom_centreline, width, net, kind, ref))."""
    items = defaultdict(list)
    for t in b.tracks:
        g = LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]) if (t["x1"], t["y1"]) != (t["x2"], t["y2"]) \
            else Point(t["x1"], t["y1"])
        items[t["layer"]].append(dict(cl=g, w=t["w"], net=t["net"], kind="track", ref=""))
    for p in b.pads:
        lays = []
        for ly in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"):
            if ly in p["layers"] or "*.Cu" in p["layers"]:
                lays.append(ly)
        if not lays or not p["net"]:
            continue
        w, h = p["w"], p["h"]
        a = math.radians(p["rot"])
        if p["shape"] == "circle" or abs(w - h) < 1e-6:
            cl = Point(p["x"], p["y"])
            width = w
        else:
            L = (max(w, h) - min(w, h)) / 2
            ux, uy = (math.cos(a), -math.sin(a)) if w > h else (math.sin(a), math.cos(a))
            cl = LineString([(p["x"] - L * ux, p["y"] - L * uy), (p["x"] + L * ux, p["y"] + L * uy)])
            width = min(w, h)
        for ly in lays:
            items[ly].append(dict(cl=cl, w=width, net=p["net"], kind="pad", ref=f"{p['ref']}.{p['num']}"))
    for v in b.vias:
        for ly in ("F.Cu", "In2.Cu", "B.Cu"):
            items[ly].append(dict(cl=Point(v["x"], v["y"]), w=v["size"], net=v["net"], kind="via", ref=""))
    for ly in items:
        for it in items[ly]:
            it["poly"] = it["cl"].buffer(it["w"] / 2, 8)
    return items


def gnd_fill(b):
    fills = defaultdict(list)
    for z in b.zones:
        if z["net"] != "GND":
            continue
        for fl, pts in z["fills"]:
            from shapely.geometry import Polygon
            pg = make_valid(Polygon(pts))
            fills[fl].append(pg)
    return {ly: unary_union(v) for ly, v in fills.items()}


def direction(cl):
    if cl.geom_type != "LineString":
        return None
    (x1, y1), (x2, y2) = cl.coords[0], cl.coords[-1]
    return math.atan2(y2 - y1, x2 - x1)


def angle_between(a, b):
    if a is None or b is None:
        return 0.0
    d = abs(a - b) % math.pi
    return min(d, math.pi - d)


def main():
    b = Board(PCB)
    items = items_from_board(b)
    gfill = gnd_fill(b)
    adj = {"In2.Cu": "B.Cu", "B.Cu": "In2.Cu"}
    trees = {ly: STRtree([it["poly"] for it in items[ly]]) for ly in items}
    agg = defaultdict(lambda: dict(len_close=0.0, gmin=9.0, cm=0.0, cross=0, cross_c=0.0, kind="same"))
    netlen = defaultdict(float)
    netcap = defaultdict(float)  # self capacitance estimate per victim (board only)
    seen_cross = set()
    c11 = {"F.Cu": TAB["F_ref1_between0"][-1]["c11"], "In2.Cu": TAB["In2_ref1_between0"][-1]["c11"],
           "B.Cu": TAB["B_ref1_between0"][-1]["c11"]}
    for ly in ("F.Cu", "In2.Cu", "B.Cu"):
        for vi in items[ly]:
            vnet = vi["net"]
            if not is_victim(vnet):
                continue
            cl = vi["cl"]
            L = cl.length if cl.geom_type == "LineString" else 0.0
            n = max(1, int(math.ceil(L / STEP))) if L > 0 else 1
            dl = L / n if L > 0 else vi["w"]
            if vi["kind"] == "via":
                dl = 0.0  # via barrels: coupling via their pads is captured on the tracks
            netlen[(vnet, ly)] += L
            netcap[vnet] += c11[ly] * (L if L > 0 else vi["w"]) * 1e-3  # pF (rough, pads/vias approx.)
            vdir = direction(cl)
            for k in range(n):
                p = cl.interpolate((k + 0.5) / n, normalized=True) if L > 0 else cl
                # ---- same layer: nearest item per aggressor net only
                best = {}
                if dl > 0:
                    for idx in trees[ly].query(p.buffer(GMAX + vi["w"] / 2)):
                        ai = items[ly][idx]
                        if ai["net"] in (vnet, "GND", ""):
                            continue
                        th = angle_between(vdir, direction(ai["cl"])) if ai["kind"] == "track" else 0.0
                        if th > math.radians(45):
                            continue
                        gap = ai["poly"].distance(p) - vi["w"] / 2
                        if gap > GMAX:
                            continue
                        if ai["net"] not in best or gap < best[ai["net"]][0]:
                            best[ai["net"]] = (gap, ai)
                for anet, (gap, ai) in best.items():
                    gap = max(gap, 0.1)
                    q = ai["poly"].exterior.interpolate(ai["poly"].exterior.project(p))
                    mid = Point((p.x + q.x) / 2, (p.y + q.y) / 2)
                    between = gap >= 0.3 and ly in gfill and gfill[ly].contains(mid)
                    if not between and gap >= 0.3:
                        # any third conductor (driven line, rail, other victim) between the two shields
                        seg = LineString([(p.x, p.y), (q.x, q.y)])
                        for j in trees[ly].query(seg):
                            o = items[ly][j]
                            if o["net"] not in (vnet, anet) and o["poly"].intersects(seg):
                                between = True
                                break
                    refp = True
                    if ly in adj:
                        refp = adj[ly] in gfill and gfill[adj[ly]].contains(p)
                    c = cm_same(ly, gap, refp, between) * dl  # fF
                    a = agg[(vnet, anet, ly, "same")]
                    a["cm"] += c
                    a["gmin"] = min(a["gmin"], gap)
                    if gap <= 0.5:
                        a["len_close"] += dl
                # ---- adjacent layer (broadside): nearest parallel item per net; crossings lumped
                if ly in adj and dl > 0:
                    al = adj[ly]
                    bestb = {}
                    for idx in trees[al].query(p.buffer(0.8 + vi["w"] / 2)):
                        ai = items[al][idx]
                        if ai["net"] in (vnet, "GND", ""):
                            continue
                        key = (vnet, ai["net"], ly + "/" + al, "broadside")
                        th = angle_between(vdir, direction(ai["cl"])) if ai["kind"] == "track" else 0.0
                        if ai["kind"] == "track" and th > math.radians(30):
                            if cl.geom_type == "LineString" and cl.intersects(ai["cl"]):
                                x = cl.intersection(ai["cl"])
                                ck = (vnet, ai["net"], round(x.centroid.x, 2), round(x.centroid.y, 2))
                                if ck not in seen_cross:
                                    seen_cross.add(ck)
                                    ww = (vi["w"] + 0.1) * (ai["w"] + 0.1) / max(math.sin(th), 0.3)
                                    c = EPS0 * 4.3 * ww * 1e-6 / 0.1e-3 * 1e15  # fF, 0.05 mm fringe each edge
                                    a = agg[key]
                                    a["cross"] += 1
                                    a["cross_c"] += c
                                    a["cm"] += c
                                    a["gmin"] = 0.0
                            continue
                        off = ai["cl"].distance(p)
                        if ai["kind"] in ("pad", "via"):
                            if ai["poly"].distance(p) < vi["w"] / 2 + 0.05:
                                c = EPS0 * 4.3 * (vi["w"] + 0.1) * dl * 1e-6 / 0.1e-3 * 1e15
                                cur = bestb.get(ai["net"])
                                if cur is None or c > cur[0]:
                                    bestb[ai["net"]] = (c, 0.0, dl)
                            continue
                        if off <= 0.8:
                            c = cm_broadside(off, True) * dl
                            if off >= 0.3:
                                q = ai["cl"].interpolate(ai["cl"].project(p)) if ai["cl"].geom_type == "LineString" else ai["cl"]
                                mid = Point((p.x + q.x) / 2, (p.y + q.y) / 2)
                                nf = sum(1 for l2 in (ly, al) if l2 in gfill and gfill[l2].contains(mid))
                                cb = interp(TAB["broadside_offsets_mm"], [r["cm"] for r in TAB["broadside_between"]], off) * dl
                                c = c if nf == 0 else (math.sqrt(max(c, 1e-12) * max(cb, 1e-12)) if nf == 1 else cb)
                            cur = bestb.get(ai["net"])
                            if cur is None or c > cur[0]:
                                bestb[ai["net"]] = (c, max(off - (vi["w"] + ai["w"]) / 2, 0.0), dl if off < 0.3 else 0.0)
                    for anet, (c, g, lc) in bestb.items():
                        a = agg[(vnet, anet, ly + "/" + al, "broadside")]
                        a["cm"] += c
                        a["gmin"] = min(a["gmin"], g)
                        a["len_close"] += lc
    rows = []
    for (v, an, ly, kind), a in sorted(agg.items()):
        if a["cm"] < 0.01:
            continue
        rows.append(dict(victim=v, aggressor=an, layer=ly, kind=kind, cm_fF=round(a["cm"], 3),
                         len_close_mm=round(a["len_close"], 2), gap_min_mm=round(a["gmin"], 3),
                         crossings=a["cross"], cross_fF=round(a["cross_c"], 2)))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "out", f"coupling_pairs{TAGS}.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    lens = defaultdict(dict)
    for (n, ly), L in netlen.items():
        lens[n][ly] = round(L, 2)
    json.dump(dict(lengths=lens, self_cap_pF={k: round(v, 3) for k, v in netcap.items()}),
              open(os.path.join(HERE, "out", f"victim_lengths{TAGS}.json"), "w"), indent=1)
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
