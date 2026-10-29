"""External 50 Hz E-field pickup on electrode-flex traces (2D FD).

A far plate at height H above the skin (body = 0 V reference) sets a uniform field E0 at the skin.
The P/N traces (held at body potential through their contacts) intercept displacement current
i = j w eps0 E0 * w_eff * L, where w_eff is the induced charge per unit length divided by the bare-skin
surface charge density eps0*E0. Cases: free link on skin (no shield; the single 0.1 mm GND return is
off to the side), link lifted 0.65 mm, pod under the 0.2/0.8 mm 45 deg hatch (2D grating 0.28 mm lines,
1.41 mm pitch, averaged over trace position) and under a solid plane.
Output: out/flex_field.json; printed table with uV for given field strengths.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fd2d import XSection  # noqa: E402

H = 0.005
TOP = 3.0


def case(lift=0.0, shield="none", xoff=0.0, width=14.0):
    xs = XSection(width, TOP + 0.2, H)
    # y: skin conductor at y=0..0.01 (id 0 -> body), flex bottom at lift
    y0 = 0.01 + lift
    xs.conductor(0, -width / 2, width / 2, 0.0, 0.01)
    xs.dielectric(y0, y0 + 0.025, 3.2)
    xs.dielectric(y0 + 0.025, y0 + 0.074, 3.4)
    xs.dielectric(y0 + 0.074, y0 + 0.099, 3.2)
    yc = y0 + 0.025
    xs.conductor(1, xoff - 0.15, xoff - 0.05, yc, yc + 0.012)   # P
    xs.conductor(2, xoff + 0.05, xoff + 0.15, yc, yc + 0.012)   # N
    yb = y0 + 0.062
    if shield == "solid":
        xs.conductor(3, -3.55, 3.55, yb, yb + 0.012)
    elif shield == "hatch":
        pitch, lw = 1.414, 0.283
        for k in range(-5, 6):
            c = k * pitch
            xs.conductor(3, c - lw / 2, c + lw / 2, yb, yb + 0.012)
    elif shield == "return":  # single 0.1 mm GND return 0.4 mm beside the pair, B.Cu
        xs.conductor(3, xoff + 0.45, xoff + 0.55, yb, yb + 0.012)
    xs.conductor(4, -width / 2, width / 2, TOP, TOP + 0.01)    # field source plate
    q = xs.solve(4, 5)
    # analytic bare-skin charge per mm of width: eps0 * (1 V / gap) * 1 mm (gap in mm cancels units)
    sigma0 = 8.854e-12 / (TOP - 0.01)
    return dict(wP=-q[1] / sigma0, wN=-q[2] / sigma0)


def main():
    res = {}
    res["link_on_skin"] = case(0.0, "none")
    res["link_on_skin_return"] = case(0.0, "return")
    res["link_lifted_0.65"] = case(0.65, "none")
    res["pod_solid"] = case(0.65, "solid")
    hs = [case(0.65, "hatch", xoff=x) for x in np.linspace(0, 0.707, 4)]
    res["pod_hatch_avg"] = dict(wP=float(np.mean([h["wP"] for h in hs])), wN=float(np.mean([h["wN"] for h in hs])),
                                wP_minmax=[float(min(h["wP"] for h in hs)), float(max(h["wP"] for h in hs))])
    for k, v in res.items():
        print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items()})
    # pickup: i = w eps0 E0 w_eff L ; V = i |Zs|; DM ~ |wP - wN| plus 30 % contact mismatch on the common part
    eps0 = 8.854e-12
    w = 2 * math.pi * 50
    zs = abs(1e6 / (1 + 1j * w * 1e6 * 10e-9))
    print(f"\n|Zs(50 Hz)| for 1M||10n = {zs / 1e3:.0f} kOhm")
    out = []
    for E0 in (10.0, 100.0):
        for name, L_mm, key in (("pod 8 traces: 4 free links on skin", 48.0, "link_on_skin"),
                                ("pod 8 traces: 4 free links lifted 0.65 mm", 48.0, "link_lifted_0.65"),
                                ("pod 5 traces: 1 free link on skin", 12.0, "link_on_skin"),
                                ("pod 8 traces over pods 5-7 under hatch (3 x 7 mm)", 21.0, "pod_hatch_avg")):
            r = res[key]
            iP = w * eps0 * E0 * r["wP"] * 1e-3 * L_mm * 1e-3
            iN = w * eps0 * E0 * r["wN"] * 1e-3 * L_mm * 1e-3
            vcm = iP * zs
            vdm = abs(iP - iN) * zs + 0.3 * min(iP, iN) * zs
            out.append(dict(E0=E0, case=name, per_trace_uV=round(vcm * 1e6, 3), dm_uV=round(vdm * 1e6, 3)))
            print(f"E0 {E0:5.0f} V/m, {name}: per trace {vcm * 1e6:.3f} uV, DM (geometry + 30 % contact mismatch) {vdm * 1e6:.3f} uV")
    res["pickup"] = out
    json.dump(res, open(os.path.join(HERE, "out", "flex_field.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
