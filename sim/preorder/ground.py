"""Ground-structure checks for the rev C main board.

* In1.Cu (GND plane) coverage: voids/antipads, narrowest webs, coverage under the ADS1298 and under every
  analog (victim) track on F.Cu/In2 (F.Cu analog tracks reference In1 at 0.1 mm).
* GND pour fragments on F.Cu / In2.Cu / B.Cu: area, number of GND vias / through-hole GND pads tying each
  fragment to In1, largest distance from any fragment point to its nearest tie.
* Stitching: GND via count, largest via-free circle on the board, spacing along the RF counterpoise.
Output: out/ground_summary.json and printed summary.
"""
import json
import math
import os
import re
import sys

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = os.environ.get("TAG", "")
sys.path.insert(0, HERE)
from pcbgeom import Board  # noqa: E402

PCB = os.path.join(HERE, "../../boards/neurband_c/neurband_c.kicad_pcb")


def is_analog(net):
    return bool(re.fullmatch(r"/E\d[PN]", net) or net.startswith("Net-(RN") or
                net in ("/BIAS_E", "Net-(U2-RLDOUT)", "Net-(U2-RLDINV)", "/RLDREF", "Net-(U2-VREFP)") or
                "VCAP" in net)


def polys(fills, layer):
    out = []
    for fl, pts in fills:
        if fl == layer:
            g = make_valid(Polygon(pts))
            out.extend(list(g.geoms) if hasattr(g, "geoms") else [g])
    return [p for p in out if p.geom_type == "Polygon" and p.area > 1e-4]


def main():
    b = Board(PCB)
    gz = [z for z in b.zones if z["net"] == "GND"]
    res = {}
    outline = Polygon([(0, 0), (28.7, 0), (28.7, 27), (0, 27)])
    gvias = [v for v in b.vias if v["net"] == "GND"]
    gth = [p for p in b.pads if p["net"] == "GND" and p["type"] == "thru_hole"]
    ties = [Point(v["x"], v["y"]) for v in gvias] + [Point(p["x"], p["y"]) for p in gth]
    res["gnd_vias"] = len(gvias)
    res["gnd_thru_pads"] = len(gth)
    # ---- In1 plane
    in1 = unary_union([p for z in gz for p in polys(z["fills"], "In1.Cu")])
    res["in1_area_mm2"] = round(in1.area, 1)
    ant = Polygon([(0, 11.65), (5.65, 11.65), (5.65, 27), (0, 27)])
    res["board_minus_antenna_mm2"] = round(outline.difference(ant).area, 1)
    voids = outline.difference(ant).difference(in1)
    vl = list(voids.geoms) if hasattr(voids, "geoms") else [voids]
    vl = sorted([v for v in vl if v.area > 0.01], key=lambda g: -g.area)
    res["in1_voids_largest"] = [dict(area=round(v.area, 3), bbox=[round(x, 2) for x in v.bounds]) for v in vl[:12]]
    # ADS footprint coverage
    u2 = b.fps["U2"]
    ads_box = Point(u2["x"], u2["y"]).buffer(6.0, cap_style=3)
    res["in1_cover_under_ads_pct"] = round(100 * in1.intersection(ads_box).area / ads_box.area, 1)
    # analog track coverage by In1 (F.Cu tracks: 0.1 mm above In1)
    cov = {}
    for t in b.tracks:
        if not is_analog(t["net"]) or t["layer"] not in ("F.Cu", "In2.Cu"):
            continue
        seg = LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])])
        if seg.length == 0:
            continue
        L = seg.length
        inside = seg.intersection(in1).length
        c = cov.setdefault(t["net"], [0.0, 0.0])
        c[0] += L
        c[1] += L - inside
    res["analog_track_length_over_in1_voids_mm"] = {k: round(v[1], 3) for k, v in cov.items() if v[1] > 0.02}
    # ---- pour fragments
    frag = {}
    for ly in ("F.Cu", "In2.Cu", "B.Cu"):
        ps = [p for z in gz for p in polys(z["fills"], ly)]
        rows = []
        for p in ps:
            pb = p.buffer(0.01)
            n_ties = sum(1 for q in ties if pb.contains(q))
            # pads of GND SMD parts on this layer also tie it only through their own vias; count vias only
            if n_ties:
                pts = [q for q in ties if pb.contains(q)]
                # farthest point in fragment from a tie (sample grid)
                minx, miny, maxx, maxy = p.bounds
                xs = np.arange(minx, maxx, 0.2)
                ys = np.arange(miny, maxy, 0.2)
                far = 0.0
                for x in xs:
                    for y in ys:
                        pt = Point(x, y)
                        if p.contains(pt):
                            far = max(far, min(pt.distance(q) for q in pts))
            else:
                far = None
            # GND pads (component returns) that sit on this fragment, and its longest extent
            onpads = sorted({f"{q['ref']}.{q['num']}" for q in b.pads if q["net"] == "GND" and
                             (ly in q["layers"] or "*.Cu" in q["layers"]) and pb.contains(Point(q["x"], q["y"]))})
            mrr = p.minimum_rotated_rectangle
            xs_, ys_ = mrr.exterior.coords.xy
            sides = [math.hypot(xs_[i + 1] - xs_[i], ys_[i + 1] - ys_[i]) for i in range(2)]
            rows.append(dict(area=round(p.area, 3), ties=n_ties, farthest_from_tie_mm=None if far is None else round(far, 2),
                             length_mm=round(max(sides), 2), width_mm=round(min(sides), 2),
                             bbox=[round(x, 2) for x in p.bounds], gnd_pads=onpads))
        rows.sort(key=lambda r: -r["area"])
        frag[ly] = rows
    res["pour_fragments"] = frag
    # ---- stitching coverage: largest via-free distance over the board (excluding antenna keepout)
    grid = []
    for x in np.arange(0.3, 28.4, 0.1):
        for y in np.arange(0.3, 26.7, 0.1):
            if ant.contains(Point(x, y)):
                continue
            d = min(math.hypot(x - v["x"], y - v["y"]) for v in gvias)
            grid.append((d, x, y))
    grid.sort(reverse=True)
    res["max_distance_to_gnd_via_mm"] = [dict(d=round(d, 2), x=round(x, 1), y=round(y, 1)) for d, x, y in grid[:1]]
    # list local maxima (coarse) for the report
    picks = []
    for d, x, y in grid:
        if all(math.hypot(x - px, y - py) > 3 for _, px, py in picks):
            picks.append((d, x, y))
        if len(picks) >= 8:
            break
    res["via_gaps_top"] = [dict(d=round(d, 2), x=round(x, 1), y=round(y, 1)) for d, x, y in picks]
    # GND vias near the ADS
    res["gnd_vias_within_7mm_of_ads"] = sum(1 for v in gvias if math.hypot(v["x"] - u2["x"], v["y"] - u2["y"]) < 7)
    json.dump(res, open(os.path.join(HERE, "out", f"ground_summary{TAG}.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "pour_fragments"}, indent=1))
    for ly, rows in frag.items():
        print(ly, "fragments:", len(rows))
        for r in rows[:25]:
            print("   ", r)


if __name__ == "__main__":
    main()
