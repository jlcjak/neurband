"""rc.py - FreeCAD helpers and colours shared by the neurband rev C part scripts.

Dimensions live in params.py (pure Python, also used by fit.py). Printed parts:
  cradle.step     x1  rigid (PETG / ABS / PC)  flat top on the bed, curved underside up
  lid.step        x1  rigid                    flat top on the bed
  pod_x6.step     x6  rigid                    on its side
  bond_jig.step   x1  PLA / PETG               flat
"""
import os, sys, math, json, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
MECH = os.path.dirname(HERE)
ROOT = os.path.dirname(MECH)
sys.path.insert(0, MECH)
sys.path.insert(0, HERE)

import FreeCAD, Part
import cadutil as U
import params as P

V = FreeCAD.Vector

# ---------------- colours ----------------
C_CRADLE = C_HOLDER = C_LID = C_POD = (0.13, 0.14, 0.15)
C_INLAY = (0.11, 0.49, 0.96)
C_JIG = (0.80, 0.80, 0.78)
C_STRAP = (0.11, 0.19, 0.36)    # Midnight Blue woven nylon (Tech-Protect Nylon Classic 51mm)
C_STITCH = (0.16, 0.27, 0.48)   # nylon stitching & keeper detail
C_QF = (0.13, 0.14, 0.16)       # matte black PVD QuickFit latch & tang buckle
C_PIN = (0.76, 0.78, 0.82)      # stainless QuickFit lug pins & Torx screws
C_RING = (0.80, 0.82, 0.85)
C_GOLD = U.C_GOLD
C_FLEX = (0.85, 0.50, 0.10)
C_PCB = U.C_PCB
C_PARTS = (0.15, 0.15, 0.15)
C_FOAM = (0.94, 0.94, 0.92)
C_LIPO = U.C_LIPO
C_PCM = (0.86, 0.70, 0.12)
C_SKIN = U.C_SKIN
C_WIRE = (0.75, 0.12, 0.10)


class Log:
    def __init__(self, name):
        os.makedirs(os.path.join(HERE, 'logs'), exist_ok=True)
        self.path = os.path.join(HERE, 'logs', name + '.log')
        self.f = open(self.path, 'w')
        self(f"{name}: {datetime.datetime.now().isoformat(timespec='seconds')} gui={U.GUI}")

    def __call__(self, *a):
        msg = ' '.join(str(x) for x in a)
        self.f.write(msg + '\n')
        self.f.flush()
        if not U.GUI:
            print(msg)


def save(stem, items, log):
    return U.save(stem, items, log, folder=HERE)


def finish(log):
    log("done")
    log.f.close()
    if U.GUI:
        os._exit(0)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def rrect(w, l, r, h, z0=0.0, cx=0.0, cy=0.0):
    s = U.rrect(w, l, r, h, z0)
    s.translate(V(cx, cy, 0))
    return s


def prism_xz(pts, y0, y1):
    """Polygon given in (x, z), extruded along Y from y0 to y1."""
    w = Part.makePolygon([V(x, y0, z) for x, z in pts] + [V(pts[0][0], y0, pts[0][1])])
    return Part.Face(w).extrude(V(0, y1 - y0, 0))


def prism_yz(pts, x0, x1):
    """Polygon given in (y, z), extruded along X from x0 to x1."""
    w = Part.makePolygon([V(x0, y, z) for y, z in pts] + [V(x0, pts[0][0], pts[0][1])])
    return Part.Face(w).extrude(V(x1 - x0, 0, 0))


def fillet_edges(shape, r, pick, log=None, tag=''):
    edges = [e for e in shape.Edges if pick(e)]
    if not edges:
        return shape
    try:
        s = shape.makeFillet(r, edges)
        if s.isValid() and s.Volume > 0:
            return s
    except Exception as ex:
        if log:
            log(f"  fillet {tag} r={r} skipped on {len(edges)} edges: {ex}")
    return shape


def chamfer_edges(shape, d, pick, log=None, tag=''):
    edges = [e for e in shape.Edges if pick(e)]
    if not edges:
        return shape
    try:
        s = shape.makeChamfer(d, edges)
        if s.isValid() and s.Volume > 0:
            return s
    except Exception as ex:
        if log:
            log(f"  chamfer {tag} d={d} skipped on {len(edges)} edges: {ex}")
    return shape


def clash(a, b):
    try:
        return round(a.common(b).Volume, 3)
    except Exception:
        return -1.0


def flex_pod_visual(lift):
    """One flex paddle with its three gold pads and foam dots, pod frame (Z = 0 is the pod face, skin at -Z)."""
    w, L = P.POD_W, P.POD_L
    pad = box(-w / 2, w / 2, -L / 2, L / 2, -lift - P.FLEX_T, -lift)
    pad = fillet_edges(pad, 0.8, lambda e: e.BoundBox.ZLength > P.FLEX_T - 0.01)
    for y in P.HOLE_Y:
        pad = pad.cut(Part.makeCylinder(P.HOLE_D / 2, 3, V(0, y, -lift - 1.5)))
    gold = [Part.makeCylinder(P.PAD_D / 2, 0.04, V(0, y, -lift - P.FLEX_T - 0.04)) for y in P.PAD_Y]
    foam = [Part.makeCylinder(P.FOAM_D / 2, lift + P.FOAM_POCKET_H, V(0, y, -lift)) for y in P.PAD_Y]
    return pad, gold, foam
