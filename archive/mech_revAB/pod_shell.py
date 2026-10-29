"""pod_shell.py - printed backing for one electrode pod (16 per band, same part for all sizes).

Local frame: X = around the wrist (pod width), Y = along the arm (front/distal = -Y),
Z = away from the skin. z = 0 is the pocket floor where the flex pod is glued; the flex sits in
the 0.3 mm pocket below it and the gold domes protrude further toward the skin (-Z).
The strap runs along X in an open channel on the outer side (it snaps in under two short
lipped rails at the pod centre), centred along the arm, so its load lands on the middle
electrode and the stiff PA12 plate spreads it to the outer pair. The strap sits at the same
height on every pod, so the strap load per pod depends only on the local wrist curvature.
The pocket is open on the +/-X sides so the flex links leave freely (link bend length =
pitch - POD_W).
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/pod_shell.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import cadutil as U

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
POD_W = 7.0            # rigid pod width around the wrist (= flex pod width)
FLEX_POD_L = 34.0      # flex pod length along the arm
FLEX_CLEAR = 0.0       # no end walls: the tail leaves the strip's distal edge right at the shell end
END_WALL = 0.0         # (flex located by a bonding jig instead)
BASE_T = 2.5           # backing plate
POCKET_D = 0.3         # flex 0.2 + adhesive 0.1
ELECTRODE_Y = (-10.0, 0.0, 10.0)
RELIEF_D = 4.0         # pockets behind the electrodes for rivet/solder tails
RELIEF_H = 0.8
STRAP_W = 20.0         # elastic webbing width
STRAP_T = 1.3
CHANNEL_W = 20.6       # clear channel width along the arm
CHANNEL_H = 1.35       # clear height under the lips
RAIL_W = 1.4           # rail thickness (Y)
RAIL_LEN = 3.0         # rail length around the wrist (X), centred on the pod
LIP = 0.5              # lip overhang into the channel (webbing snaps in under it)
LIP_T = 0.4
FILLET = 0.4

SHELL_L = FLEX_POD_L + 2 * (FLEX_CLEAR + END_WALL)
TOP_Z = BASE_T + CHANNEL_H + LIP_T


def build():
    w, L = POD_W, SHELL_L
    s = Part.makeBox(w, L, BASE_T, V(-w / 2, -L / 2, 0))
    # end walls hang down around the flex ends
    for sy in (-1, 1) if END_WALL > 0 else ():
        y0 = sy * (FLEX_POD_L / 2 + FLEX_CLEAR) if sy > 0 else -L / 2
        s = s.fuse(Part.makeBox(w, END_WALL, POCKET_D, V(-w / 2, y0, -POCKET_D)))
    # snap rails with lips (strap channel)
    yi = CHANNEL_W / 2
    for sy in (-1, 1):
        y0 = yi if sy > 0 else -yi - RAIL_W
        s = s.fuse(Part.makeBox(RAIL_LEN, RAIL_W, CHANNEL_H + LIP_T, V(-RAIL_LEN / 2, y0, BASE_T)))
        yl = yi - LIP if sy > 0 else -yi
        s = s.fuse(Part.makeBox(RAIL_LEN, LIP, LIP_T, V(-RAIL_LEN / 2, yl, BASE_T + CHANNEL_H)))
    s = s.removeSplitter()
    # reliefs behind the electrodes
    for y in ELECTRODE_Y:
        s = s.cut(Part.makeCylinder(RELIEF_D / 2, RELIEF_H, V(0, y, 0)))
    # soften the plate ends
    try:
        edges = [e for e in s.Edges
                 if abs(e.Vertexes[0].Point.x - e.Vertexes[-1].Point.x) > w - 0.01
                 and abs(e.Vertexes[0].Point.z - BASE_T) < 1e-6 and abs(abs(e.Vertexes[0].Point.y) - L / 2) < 1e-6]
        s = s.makeFillet(FILLET, edges)
    except Exception:
        pass
    return s


if not getattr(sys, 'neurband_lib', False):
    log = U.Log('pod_shell')
    shell = U.check(build(), 'pod_shell', log)
    log(f"  size {POD_W} x {SHELL_L:.2f} x {TOP_Z + (POCKET_D if END_WALL > 0 else 0):.2f} mm (W x L x H)")
    U.save('pod_shell', [('pod_shell', shell, U.C_PA12_GREY)], log)
    U.fab('pod_shell', 'Electrode pod shell (16 per band)', shell, 36, 'mjf', 'pa12', 'grey', log)
    U.finish(log)
