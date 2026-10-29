"""Per-unit-length capacitance tables for the rev C main-board stack and the electrode flex.

Main board (mm, y up from the bottom of B.Cu): B.Cu 0-0.035 | FR-4 0.1 | In2 | FR-4 0.64 | In1 (GND) |
FR-4 0.1 | F.Cu; 10 um mask (er 3.3) on both outer layers; er 4.3. Tracks 0.1 mm wide unless noted.
Flex: F.Cu (skin side) 12 um | PI core 25 um (er 3.4) | B.Cu 12 um; 25 um coverlay+adhesive (er 3.2) each side.

Output: sim/preorder/out/xsec_tables.json (fF/mm == pF/m). Takes a few minutes.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fd2d import XSection  # noqa: E402

H = 0.005
GAPS = [0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0, 1.5]
T = 0.035
# Stack selection: STACK=orig (0.1/0.64/0.1 mm, er 4.3, 35 um inner Cu; first review) or
# STACK=3313 (as-built 2026-10-29: 0.0994 mm 3313 prepreg er 4.1, 0.70 mm core er 4.4, 15.2 um inner Cu).
STACK = os.environ.get("STACK", "orig")
if STACK == "3313":
    TI = 0.0152
    PP, CORE, ER_PP, ER_CORE, ER_MASK = 0.0994, 0.700, 4.1, 4.4, 3.8
else:
    TI = 0.035
    PP, CORE, ER_PP, ER_CORE, ER_MASK = 0.100, 0.640, 4.3, 4.3, 3.3
# main-board layer copper bottoms (y up from the bottom of B.Cu)
YB = 0.0
YIN2 = T + PP
YIN1 = YIN2 + TI + CORE
YF = YIN1 + TI + PP
OUTFILE = "xsec_tables.json" if STACK == "orig" else f"xsec_tables_{STACK}.json"


def stack_dielectrics(xs, Y):
    xs.dielectric(Y(-0.01), Y(0.0), ER_MASK)
    xs.dielectric(Y(0.0), Y(YIN2 + TI), ER_PP)
    xs.dielectric(Y(YIN2 + TI), Y(YIN1), ER_CORE)
    xs.dielectric(Y(YIN1), Y(YF + T), ER_PP)
    xs.dielectric(Y(YF + T), Y(YF + T + 0.01), ER_MASK)


def board(width, pour_between=False, layer="F", ref_pour=True, wv=0.1, wa=0.1, g=0.2, outer_pour=True):
    """Two coplanar tracks (victim id1 at left, aggressor id2 at right) on `layer`; GND id0."""
    xs = XSection(width, 1.95, H)
    xs.x0 = -width / 2
    # y offset: domain y from -0.5 (air below B.Cu) to 1.45
    off = 0.5
    def Y(y):
        return y + off
    stack_dielectrics(xs, Y)
    xs.conductor(0, -width / 2, width / 2, Y(YIN1), Y(YIN1 + TI))  # In1 GND
    yl = {"F": YF, "In2": YIN2, "B": YB}[layer]
    tl = TI if layer == "In2" else T
    xv0, xv1 = -g / 2 - wv, -g / 2
    xa0, xa1 = g / 2, g / 2 + wa
    xs.conductor(1, xv0, xv1, Y(yl), Y(yl + tl))
    xs.conductor(2, xa0, xa1, Y(yl), Y(yl + tl))
    if outer_pour:
        xs.conductor(0, -width / 2, xv0 - 0.1, Y(yl), Y(yl + tl))
        xs.conductor(0, xa1 + 0.1, width / 2, Y(yl), Y(yl + tl))
    if pour_between and g >= 0.3:
        xs.conductor(0, xv1 + 0.1, xa0 - 0.1, Y(yl), Y(yl + tl))
    # reference pour on the adjacent signal layer (In2 for B, B for In2); none needed for F (In1 is solid)
    if ref_pour and layer in ("In2", "B"):
        ya, ta = (YB, T) if layer == "In2" else (YIN2, TI)
        xs.conductor(0, -width / 2, width / 2, Y(ya), Y(ya + ta))
    q = xs.solve(1, 3)
    return dict(c11=q[1] * 1e12, cm=-q[2] * 1e12)  # pF/m = fF/mm


def broadside(width, d, ref_pour=False, wv=0.1, wa=0.1):
    """Victim on In2 at x=0, aggressor on B.Cu with centre offset d (crossing / overlap per mm)."""
    xs = XSection(width, 1.95, H)
    off = 0.5
    def Y(y):
        return y + off
    stack_dielectrics(xs, Y)
    xs.conductor(0, -width / 2, width / 2, Y(YIN1), Y(YIN1 + TI))
    xs.conductor(1, -wv / 2, wv / 2, Y(YIN2), Y(YIN2 + TI))
    xs.conductor(2, d - wa / 2, d + wa / 2, Y(YB), Y(YB + T))
    if ref_pour:  # pours at 0.1 clearance on both layers beyond both tracks
        lo, hi = min(-wv / 2, d - wa / 2) - 0.1, max(wv / 2, d + wa / 2) + 0.1
        for yl, tl in ((YIN2, TI), (YB, T)):
            xs.conductor(0, -width / 2, lo, Y(yl), Y(yl + tl))
            xs.conductor(0, hi, width / 2, Y(yl), Y(yl + tl))
    q = xs.solve(1, 3)
    return dict(c11=q[1] * 1e12, cm=-q[2] * 1e12)


def flex_pair(g, w=0.1, hatch_fill=None, skin=False, width=2.0):
    """Flex F.Cu pair (skin side). hatch_fill: None = no B.Cu GND; else solid GND plane on B.Cu
    (the 0.2/0.8 hatch is ~36 % metal; bracketed by none/solid). skin: conductive skin plane 0.025 mm
    below the F.Cu copper (coverlay thickness) as a second electrode (id 3)."""
    xs = XSection(width, 1.2, 0.0025)
    off = 0.6
    def Y(y):
        return y + off
    # y=0 at F.Cu bottom face (skin side is -y)
    xs.dielectric(Y(-0.025), Y(0.0), 3.2)              # F coverlay (skin side)
    xs.dielectric(Y(0.0), Y(0.012 + 0.025 + 0.012), 3.4)
    xs.dielectric(Y(0.049), Y(0.074), 3.2)             # B coverlay
    xs.conductor(1, -g / 2 - w, -g / 2, Y(0.0), Y(0.012))
    xs.conductor(2, g / 2, g / 2 + w, Y(0.0), Y(0.012))
    n = 3
    if hatch_fill:
        xs.conductor(0, -width / 2, width / 2, Y(0.037), Y(0.049))
    if skin:
        xs.conductor(3, -width / 2, width / 2, Y(-0.0275), Y(-0.025))
        n = 4
    q = xs.solve(1, n)
    return dict(c11=q[1] * 1e12, cm=-q[2] * 1e12, c_skin=(-q[3] * 1e12 if skin else None),
                c_gnd=(-q[0] * 1e12))


def main():
    out = {"gaps_mm": GAPS, "units": "fF/mm (= pF/m)"}
    for layer in ("F", "In2", "B"):
        for refp in ((True, False) if layer != "F" else (True,)):
            for between in (False, True):
                key = f"{layer}_ref{int(refp)}_between{int(between)}"
                rows = []
                for g in GAPS:
                    r = board(3.2, pour_between=between, layer=layer, ref_pour=refp, g=g)
                    rows.append(r)
                    print(key, g, r, flush=True)
                out[key] = rows
    out["broadside_offsets_mm"] = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8]
    for refp in (False, True):
        rows = []
        for d in out["broadside_offsets_mm"]:
            r = broadside(3.2, d, ref_pour=refp)
            rows.append(r)
            print("broadside", refp, d, r, flush=True)
        out[f"broadside_pour{int(refp)}"] = rows
    # flex (unchanged by the board stack)
    fl = {}
    if STACK != "orig":
        os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
        json.dump(out, open(os.path.join(HERE, "out", OUTFILE), "w"), indent=1)
        return
    for hatch in (False, True):
        for skin in (False, True):
            r = flex_pair(0.1, hatch_fill=hatch, skin=skin)
            fl[f"hatch{int(hatch)}_skin{int(skin)}"] = r
            print("flex", hatch, skin, r, flush=True)
    out["flex_pair_g0.1"] = fl
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "out", OUTFILE), "w"), indent=1)


if __name__ == "__main__":
    main()
