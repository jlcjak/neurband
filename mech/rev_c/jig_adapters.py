"""Drop-on seats for the released bonding jigs. All models have their bed face at Z=0."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = sys.neurband_band_lib = True

import FreeCAD, Part
import band as B
import module as M
import params as P
import rc as R

V = FreeCAD.Vector
SHIM_H = 1.68                   # clears the original 1.50 mm lug guides
CAP_H = 2 * SHIM_H              # lifts each clip above the original wide pedestal
PIN_SOCKET_CLR = 0.16           # radial clearance over the original locating pin


def cradle_shim():
    # The wire-bay key locates the bottom on the jig. The wire and test-pad
    # keys register the cradle above it. Matching sockets let two shims stack.
    s = R.rrect(2 * P.BODY_HX - 0.5, 2 * P.BODY_HY - 0.5, 2.4, SHIM_H, 0, P.XC, 0)
    s = s.cut(R.box(-6.15, 6.15, 14.65, P.BODY_HY + 1, -0.1, SHIM_H + 0.1))
    for pocket, height in ((M.WIRE_BAY, 0.95), (M.TP_POCKET, 0.30)):
        x0, x1, y0, y1, depth = pocket
        # The jig faces the cradle's PCB side, mirrored about the X axis.
        s = s.cut(R.box(x0 + 0.10, x1 - 0.10, -y1 + 0.10, -y0 - 0.10,
                        -0.1, min(depth, height + 0.20)))
        s = s.fuse(R.box(x0 + 0.24, x1 - 0.24, -y1 + 0.24, -y0 - 0.24,
                         SHIM_H - 0.05, SHIM_H + height))
    return s.removeSplitter()


def pod_cap():
    # Fits over the two existing pins. The new pins are coaxial with them.
    s = R.rrect(P.POD_SHELL_W - 0.60, P.POD_STRAP_W - 2 * P.POD_EAR_IN - 0.70,
                0.8, CAP_H, 0)
    shoulder = CAP_H + P.POD_FLOOR_T
    for y in P.HOLE_Y:
        s = s.cut(Part.makeCylinder(B.PIN_D0 / 2 + PIN_SOCKET_CLR,
                                    B.JIG_POD_T + B.PIN_UP + 0.24, V(0, y, -0.04)))
        s = s.fuse(Part.makeCylinder(B.PIN_D0 / 2, P.POD_FLOOR_T + 0.05, V(0, y, CAP_H - 0.05)))
        s = s.fuse(Part.makeCone(B.PIN_D0 / 2, B.PIN_D1 / 2, 0.50, V(0, y, shoulder)))
        s = s.fuse(Part.makeCylinder(B.PIN_D1 / 2, B.PIN_UP - 0.50, V(0, y, shoulder + 0.50)))
    return s.removeSplitter()


if not getattr(sys, 'neurband_adapter_lib', False):
    log = R.Log('jig_adapters')
    for stem, shape in [('jig_cradle_shim', cradle_shim()), ('jig_pod_cap', pod_cap())]:
        assert shape.isValid() and len(shape.Solids) == 1
        R.save(stem, [(stem, shape, R.C_JIG)], log)
        shape.exportStep(os.path.join(R.HERE, 'to_print', stem + '.step'))
    R.finish(log)
