"""swd_jig.py - rev C flashing jig: a nest for the main board (top up) with five P50 pogo pins on the
bottom SWD pads TP1-TP5 (KiCad (16.00..21.08, 25.7), 1.27 mm pitch), wired to a Raspberry Pi Pico.
Used for the first flash of the bare board and for re-flashing after the board is folded out of the
base (the cell, taped to nothing, rides on the board; its leads leave at the J2 corner notch).
P50 barrels (0.68 mm) at 1.27 mm pitch would leave 0.6 mm webs, so the pins fan out: they lean
+/-PIN_TILT alternately across the row, the tips meet the pads, and the holes are >= 1.0 mm apart
below a common 2.5 mm slot. Press the board down with a finger while flashing (5 x 0.74 N).
Frame: X = KiCad x, Y = -KiCad y (top view), Z up; the board's bottom rests on the nest floor.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/swd_jig.py
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import rc as R
import cadutil as U

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
PCB = (28.7, 27.0, 1.0)
TP_X = (16.00, 17.27, 18.54, 19.81, 21.08)    # TP1 +3V3, TP2 SWDIO, TP3 SWDCLK, TP4 NRST, TP5 GND
TP_Y = 25.7
PIN_TILT = 12.0                     # deg, alternate +/-
FLOOR_Z = 16.5                      # nest floor (board bottom)
WALL_H = 1.5                        # nest walls above the floor (the cell overhang passes above)
SLOT_D = 2.5                        # common slot under the pin tips
CAV_H = 3.0                         # wiring pocket under the pins, open below
CLR = 0.2


def axis(i):
    t = math.radians(PIN_TILT) * (1 if i % 2 == 0 else -1)
    tip = V(TP_X[i], -TP_Y, FLOOR_Z + R.POGO_WORK)
    d = V(0, math.sin(t), -math.cos(t))
    return tip, d


def build():
    w, l, t = PCB
    blk = R.box(-4.0, w + 4.0, -l - 4.5, 4.0, 0.0, FLOOR_Z + WALL_H)
    blk = blk.cut(R.box(-CLR, w + CLR, -l - CLR, CLR, FLOOR_Z, 30))                       # nest
    blk = blk.cut(R.box(22.0, w + 5, -l - 6, -l + 1.0, FLOOR_Z - 0.01, 30))               # J2 lead notch
    blk = blk.cut(R.box(-5, w + 5, 0.0, 6.0, FLOOR_Z, 30))                                # cell overhang side open
    blk = blk.cut(R.box(TP_X[0] - 0.9, TP_X[-1] + 0.9, -TP_Y - 0.8, -TP_Y + 0.8, FLOOR_Z - SLOT_D, 30))   # common slot
    for i in range(len(TP_X)):
        tip, d = axis(i)
        blk = blk.cut(Part.makeCylinder(R.POGO_HOLE / 2, R.POGO_L + 4, tip - d * 0.5, d))
    blk = blk.cut(R.box(TP_X[0] - 6, TP_X[-1] + 6, -TP_Y - 7, -TP_Y + 7, -0.01, CAV_H))     # wiring pocket
    return blk.removeSplitter()


def pins():
    out = []
    for i in range(len(TP_X)):
        tip, d = axis(i)
        out.append(Part.makeCylinder(R.POGO_D / 2, R.POGO_L, tip, d))
    return Part.makeCompound(out)


if not getattr(sys, 'neurband_jig_lib', False):
    log = R.Log('swd_jig')
    jig = U.check(build(), 'swd_jig', log)
    pp = pins()
    gaps = []
    for i in range(len(TP_X) - 1):
        a, b = pp.Solids[i], pp.Solids[i + 1]
        gaps.append(round(a.distToShape(b)[0], 2))
    tips_z = [round(s.BoundBox.ZMax, 2) for s in pp.Solids]
    bot_z = [round(s.BoundBox.ZMin, 2) for s in pp.Solids]
    log(f"  swd jig {jig.BoundBox.XLength:.1f} x {jig.BoundBox.YLength:.1f} x {jig.BoundBox.ZLength:.1f} mm; pin gaps at the tips {gaps} mm "
        f"(tips {tips_z}, tails {bot_z}, pocket top {CAV_H}); board hold-down force {5 * R.POGO_F_WORK:.1f} N")
    R.save('swd_jig', [('swd_jig', jig, (0.85, 0.85, 0.80))], log)
    R.save('swd_jig_fit', [('swd_jig', jig, (0.85, 0.85, 0.80)), ('pogo_pins', pp, R.C_GOLD)], log)
    R.fab('swd_jig', 'neurband rev C SWD flashing jig (5 x P50 pogo pins on TP1-TP5)', jig, 1, 'mjf', 'pa12', 'white', log)
    R.finish(log)
