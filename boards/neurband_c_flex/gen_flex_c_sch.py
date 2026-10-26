"""Generate the REV C passive eight-pod electrode flex schematic.

Adapted from boards/neurband_electrodes/gen_electrodes_sch.py.
Run: python3 boards/neurband_c_flex/gen_flex_c_sch.py
The 24 electrode contacts and 20 tail fingers are fabricated copper, not BOM parts.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../tools"))
from schgen import Schematic  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
s = Schematic("neurband REV C passive flex: 8 pods x 3 electrodes", paper="A3", project="neurband_c_flex")

# Matches boards/neurband_c/gen_c_sch.py J1_MAP; no zero-padded channel names.
TAIL = {1: "GND", 2: "BIAS_E", 19: "BIAS_E", 20: "GND"}
for ch in range(8):
    TAIL[3 + 2 * ch] = f"E{ch + 1}P"
    TAIL[4 + 2 * ch] = f"E{ch + 1}N"

j = s.add("Connector_Generic:Conn_01x20", "J1", "Fabricated tail 20 fingers 0.5mm", 309.88, 99.06,
          footprint="neurband_c_flex:FPC_Tail_20_P0.5mm", in_bom=False,
          fields={"MPN": "", "LCSC": ""})
j.ref_at = (309.88, 71.12, 0)
j.val_at = (317.5, 127.0, 0, "left")
j.fsize = 1.0
for n, net in sorted(TAIL.items()):
    if net == "GND":
        x, y, _ = j.pin(str(n))
        s.wire([(x, y), (x - 20.32, y)])
        s.power("GND", x - 20.32, y)
        if n == 20:
            # External main-board ground enters through this tail contact.
            s.flag(x - 20.32, y, -5.08)
    else:
        s.pin_label(j, str(n), net, stub=5.08)
s.rect(274.32, 60.96, 386.08, 139.7, fill="60 160 80", title="Tail -> REV C main J1")

# Four columns by two rows, each pod shows P / B / N skin contacts.
for i in range(8):
    col, row = i % 4, i // 4
    x0, y0 = 25.4 + col * 59.69, 73.66 + row * 55.88
    s.rect(x0 - 5.08, y0 - 10.16, x0 + 46.99, y0 + 30.48,
           fill="200 150 40", title=f"Pod {i + 1}")
    for k, (kind, net) in enumerate((("P", f"E{i + 1}P"), ("B", "BIAS_E"), ("N", f"E{i + 1}N"))):
        y = y0 + 2.54 + k * 7.62
        tp = s.add("Connector:TestPoint", f"E{i + 1}{kind}", f"Fabricated electrode {kind}",
                   x0 + 7.62, y, 270, footprint="neurband_c_flex:Electrode_D6.5mm",
                   in_bom=False, fields={"MPN": "", "LCSC": ""})
        tp.ref_at = (x0 + 1.27, y - 1.27, 0, "left")
        tp.val_at = (x0 + 1.27, y + 1.27, 0, "left")
        tp.hide_value = True
        px, py, _ = tp.pin("1")
        s.wire([(px, py), (px + 7.62, py)])
        s.label(net, px + 7.62, py, 0)

s.text("PASSIVE FLEX: 24 fabricated 6.5 mm skin electrodes + one fabricated 20-contact tail; no purchased parts.\n"
       "All eight B contacts share BIAS_E, driven by the main-board bias amplifier; no skin contact is GND.\n"
       "Each electrode is pin 1. GND is reserved for shield/return copper, not a skin electrode.", 20.32, 190.5)
s.text("TAIL ORIENTATION: exposed tail contacts on B.Cu; PI stiffener on F.Cu (skin side).\n"
       "Distal tail U-turns up the distal module wall, entering J1 proximally; maintain pin 1, no axial twist.\n"
       "Optional contact build: 2-3 SMD spring pins with 2 mm heads per electrode; not fitted or included in this flex BOM.\n"
       "If spring pins are selected, qualify attachment, travel, skin pressure and finish before assembly.", 20.32, 219.71)
s.write(os.path.join(HERE, "neurband_c_flex.kicad_sch"))
print("written neurband_c_flex.kicad_sch")
