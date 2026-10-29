"""Broadside (In2 victim / B.Cu aggressor) coupling with GND pour filled between them on both layers
(0.1 mm clearance), for centre offsets >= 0.3 mm. Appends 'broadside_between' to out/xsec_tables.json."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fd2d import XSection
from xsec_tables import YB, YIN2, YIN1, YF, T, TI, H, OUTFILE, stack_dielectrics

def bs_between(d, width=3.2, wv=0.1, wa=0.1):
    xs = XSection(width, 1.95, H)
    off = 0.5
    Y = lambda y: y + off
    stack_dielectrics(xs, Y)
    xs.conductor(0, -width / 2, width / 2, Y(YIN1), Y(YIN1 + TI))
    xs.conductor(1, -wv / 2, wv / 2, Y(YIN2), Y(YIN2 + TI))
    xs.conductor(2, d - wa / 2, d + wa / 2, Y(YB), Y(YB + T))
    # In2 pour everywhere except +-0.1 around the victim; B.Cu pour everywhere except +-0.1 around the aggressor
    xs.conductor(0, -width / 2, -wv / 2 - 0.1, Y(YIN2), Y(YIN2 + TI)); xs.conductor(0, wv / 2 + 0.1, width / 2, Y(YIN2), Y(YIN2 + TI))
    xs.conductor(0, -width / 2, d - wa / 2 - 0.1, Y(YB), Y(YB + T)); xs.conductor(0, d + wa / 2 + 0.1, width / 2, Y(YB), Y(YB + T))
    q = xs.solve(1, 3)
    return dict(c11=q[1] * 1e12, cm=-q[2] * 1e12)

d = json.load(open(os.path.join(HERE, "out", OUTFILE)))
rows = []
for o in d["broadside_offsets_mm"]:
    r = bs_between(o); rows.append(r); print(o, r, flush=True)
d["broadside_between"] = rows
json.dump(d, open(os.path.join(HERE, "out", OUTFILE), "w"), indent=1)
