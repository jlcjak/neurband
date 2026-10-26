"""Generates neurband_electrodes.kicad_sch: the passive electrode flex.

16 pods x 3 dry electrodes (P = proximal, B = middle bias/ground, N = distal) and the
40-finger tail that plugs into J2 of the main board. No components are assembled.
Run: python3 gen_electrodes_sch.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../tools"))
from schgen import Schematic  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
s = Schematic("neurband electrode flex: 16 pods x 3 dry electrodes", paper="A3", project="neurband_electrodes")

# tail: same pin map as main board J2
TAIL = {1: "GND", 2: "GND", 3: "BIAS_E", 36: "BIAS_E", 37: "GND", 38: "GND", 39: "GND"}
for ch in range(16):
    TAIL[4 + 2 * ch] = f"E{ch + 1:02d}P"
    TAIL[5 + 2 * ch] = f"E{ch + 1:02d}N"

j = s.add("Connector_Generic:Conn_01x39", "J1", "Tail 39 fingers 0.3mm", 299.72, 134.62,
          footprint="neurband:FPC_Tail_39_P0.3mm", fields={"MPN": "", "LCSC": ""})
j.ref_at = (299.72, 81.28, 0)
j.val_at = (309.88, 189.23, 0)
for n, net in sorted(TAIL.items()):
    if net != "GND":
        s.pin_label(j, str(n), net)
for grp in ([1, 2], [37, 38, 39]):
    pts = []
    for n in grp:
        x, y, _ = j.pin(str(n))
        s.wire([(x, y), (x - 5.08, y)])
        pts.append((x - 5.08, y))
    s.wire([pts[0], pts[-1]])
    for p in pts[1:-1]:
        s.junction(*p)
    if grp[0] == 1:
        s.junction(*pts[0])
        s.wire([pts[0], (pts[0][0] - 12.7, pts[0][1])])
        s.power("GND", pts[0][0] - 12.7, pts[0][1])
        s.flag(pts[0][0] - 12.7, pts[0][1], -5.08)
    else:
        s.power("GND", *pts[-1])
s.text("GND = shield pour on the outer (non-skin) layer\nand the tail stiffener side. Not a skin contact.", 279.4, 195.58)
s.rect(266.7, 71.12, 335.28, 203.2, fill="60 160 80", title="Tail -> main board J2")

# pods: 4 rows x 4 columns, each pod a column of P / B / N electrodes
for i in range(16):
    col, row = i % 4, i // 4
    x0, y0 = 30.48 + col * 55.88, 50.8 + row * 50.8
    s.rect(x0 - 5.08, y0 - 7.62, x0 + 43.18, y0 + 30.48, fill="200 150 40", title=f"Pod {i + 1}")
    for k, (kind, net) in enumerate((("P", f"E{i + 1:02d}P"), ("B", "BIAS_E"), ("N", f"E{i + 1:02d}N"))):
        y = y0 + 2.54 + k * 7.62
        tp = s.add("Connector:TestPoint", f"E{i + 1}{kind}", f"electrode {kind}", x0 + 7.62, y, 270,
                   footprint="neurband:Electrode_D6.5mm", fields={"MPN": "", "LCSC": ""})
        tp.ref_at = (x0 + 1.27, y - 1.27, 0, "left")
        tp.val_at = (x0 + 1.27, y + 1.27, 0, "left")
        tp.hide_value = True
        px, py, _ = tp.pin("1")
        s.wire([(px, py), (px + 7.62, py)])
        s.label(net, px + 7.62, py, 0)

s.text("Electrodes: 6.5 mm round ENIG/hard-gold pads on the skin layer (optional gold domes or pogo pins soldered on).\n"
       "P and N of a pod are 20 mm apart along the forearm (bipolar pair, Meta sEMG-RD geometry); B sits midway and is\n"
       "driven by the bias (right-leg) amplifier on the main board. Pod pitch around the wrist depends on the size variant.",
       25.4, 266.7)
s.write(os.path.join(HERE, "neurband_electrodes.kicad_sch"))
print("written")
