"""electrode_flex.py - VISUAL model of the 16-pod electrode flex (the real flex PCB is designed in
boards/). Not ordered from here.

Flat (as-worn, unrolled) frame: X = around the wrist, Y = along the arm (front/distal = -Y),
Z = away from the skin. The flex lies in z = [-0.2, 0]; gold domes protrude toward the skin (-Z).
Pod i (1..16) centre at x = (i - 4.5) * PITCH, so the tail (between pods 4 and 5) is at x = 0.
The tail (22 x 30 mm, tip 20.5 mm) leaves the distal (-Y) edge of the strip between pods 4 and
5 and is shown flat, as manufactured; it folds up into J2 (HCTL HC-FPC-05-09-40RLTAG, top side
of the main board). Matches boards/neurband_electrodes (continuous 34 mm strip).
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/electrode_flex.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import cadutil as U

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
N_PODS = 16
TAIL_AFTER = 4                 # tail between pod 4 and pod 5
PITCH = {'S': 8.6, 'M': 9.5, 'L': 10.8, 'XL': 12.4}   # flat pod pitch per size
POD_W = 7.0                    # pod width around the wrist (brief: 9.0; see docs/mech/mechanical.md)
POD_L = 34.0                   # pod length along the arm
FLEX_T = 0.2                   # polyimide
LINK_W = 34.0                  # continuous strip (boards/neurband_electrodes: no slits)
ELECTRODE_Y = (-10.0, 0.0, 10.0)   # outer pair = bipolar channel (20 mm), middle = bias/ground
DOME_D = 6.5
DOME_H = 1.2                   # protrusion below the flex
DOME_BASE_H = 0.3              # cylindrical part of the electrode
TAIL_W = 22.0
TAIL_L = 30.0                  # leaves the distal (-Y) strip edge, last 6 mm narrowed
TAIL_TIP_W, TAIL_TIP_L = 20.5, 6.0


def pod_flex():
    """One flex pod in pod-local coordinates (centre at origin, flex top at z = 0)."""
    return Part.makeBox(POD_W, POD_L, FLEX_T, V(-POD_W / 2, -POD_L / 2, -FLEX_T))


def domes():
    out = []
    r = DOME_D / 2
    cap = DOME_H - DOME_BASE_H
    rs = (r * r + cap * cap) / (2 * cap)
    z_tip = -FLEX_T - DOME_H
    for y in ELECTRODE_Y:
        base = Part.makeCylinder(r, DOME_BASE_H, V(0, y, -FLEX_T - DOME_BASE_H))
        sph = Part.makeSphere(rs, V(0, y, z_tip + rs))
        clip = Part.makeBox(DOME_D + 2, DOME_D + 2, cap, V(-r - 1, y - r - 1, z_tip))
        out.append(base.fuse(sph.common(clip)).removeSplitter())
    return out


def build(pitch):
    flex = []
    dm = []
    for i in range(1, N_PODS + 1):
        x = (i - TAIL_AFTER - 0.5) * pitch
        p = pod_flex()
        p.translate(V(x, 0, 0))
        flex.append(p)
        for d in domes():
            d.translate(V(x, 0, 0))
            dm.append(d)
        if i < N_PODS:
            L = pitch - POD_W
            flex.append(Part.makeBox(L + 0.02, LINK_W, FLEX_T, V(x + POD_W / 2 - 0.01, -LINK_W / 2, -FLEX_T)))
    y0 = -POD_L / 2
    tail = Part.makeBox(TAIL_W, TAIL_L - TAIL_TIP_L + 0.01, FLEX_T, V(-TAIL_W / 2, y0 - TAIL_L + TAIL_TIP_L - 0.01, -FLEX_T))
    tail = tail.fuse(Part.makeBox(TAIL_TIP_W, TAIL_TIP_L, FLEX_T, V(-TAIL_TIP_W / 2, y0 - TAIL_L, -FLEX_T)))
    flex = flex[0].fuse(flex[1:] + [tail]).removeSplitter()
    return flex, Part.makeCompound(dm)


if not getattr(sys, 'neurband_lib', False):
    log = U.Log('electrode_flex')
    for size, p in PITCH.items():
        flex, dm = build(p)
        U.check(flex, f'flex_{size}', log)
        U.check(dm, f'domes_{size}', log)
        span = (N_PODS - 1) * p + POD_W
        log(f"  {size}: pitch {p} mm, link {p - POD_W:.1f} mm, strip length {span:.1f} mm")
        U.save(f'electrode_flex_{size}', [('flex', flex, U.C_POLYIMIDE), ('electrodes', dm, U.C_GOLD)], log)
    U.finish(log)
