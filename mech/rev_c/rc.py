"""rc.py - shared parameters and helpers for the neurband rev C mechanics (8 pods, one size M).

Wrist frame (same as mech/fitgeom.py): right forearm palm down, X radial(+)/ulnar(-), Y along the
arm (hand toward -Y = front), Z dorsal (up); wrist crease at y = 0, band centre line at
y = BAND_Y. Pod-local frame: X around the wrist (pod width), Y along the arm, Z away from the
skin; z = 0 is the shell face the flex lies on, the skin is at -STACK.
Rev C stack at a pad (skin -> out): gold pad on 0.2 mm flex, a foam disk that pushes the pad
FOAM_PROUD mm beyond the shell face, the PA12 shell, the 20 mm elastic strap in a channel.
"""
import os, sys, math, json, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
MECH = os.path.dirname(HERE)
ROOT = os.path.dirname(MECH)
sys.path.insert(0, MECH)
import FreeCAD, Part
import cadutil as U
import fitgeom as G

V = FreeCAD.Vector

# ---------------- band / flex (from the flex brief; update from docs/layout/flex_c_layout.md) -------
N_PODS = 8
PITCH = 18.0            # pod centre to centre along the flat flex
POD_W = 7.1             # flex pod width (around the wrist), flex_c_layout.md
POD_L = 30.0            # flex pod length along the arm (coordinator: <= 31, likely 30)
PAD_D = 6.5
PAD_Y = (-10.0, 0.0, 10.0)      # P, bias, N
HOLE_D = 1.2
HOLE_Y = (-5.0, 5.0)            # alignment holes on the pod centre line, between the pads
SPINE_Y = (-7.0, 0.6)   # spine band (flex native Y -0.6..+7.0, +Y distal there; distal = -y here)
TAIL_AFTER = 3          # tail leaves between pod 3 and pod 4 (dorsal centre)
TAIL_W = 10.5           # 20 fingers x 0.5 mm, (N+1)*0.5
TAIL_T = 0.3            # at the stiffened end (connector wants 0.3)
FLEX_T = 0.2

# ---------------- compliant contact ----------------
FOAM_D = 6.0            # self-adhesive PU/EVA foam disk behind each 6.5 mm pad (6 mm punch)
FOAM_T = 1.5            # free thickness
FOAM_POCKET_D = 6.2     # 1.0+ mm walls to the pod sides and to the module's strap slots
FOAM_POCKET_H = 0.5     # pocket depth in the shell face -> pad stands FOAM_T - FOAM_POCKET_H proud
FOAM_PROUD = FOAM_T - FOAM_POCKET_H         # 1.0 mm free, ~0.6-0.7 mm at 2-5 kPa
STACK = FOAM_PROUD + FLEX_T                  # shell face above the skin at a pad (free foam)
STACK_LOADED = 0.65 + FLEX_T                 # nominal worn (foam ~35 % compressed)

# ---------------- strap ----------------
STRAP_W = 22.0          # one continuous 22 mm (7/8 in) elastic woven webbing (slot walls >= 1.0 at R3.4 corners)
STRAP_T = 1.2           # elastic woven webbing 1.2 mm (thin: the sewn wrap must clear the flex link)
CHANNEL_W = STRAP_W + 0.4
CHANNEL_H = 1.4         # clear sleeve height (STRAP_T + 0.2)
BASE_T = 1.5            # pod shell face -> sleeve floor (0.5 foam pocket + 1.0 floor)
LIP_T = 1.0             # sleeve rims (>= 1.0 for FDM TPU)

# ---------------- wrist sizes for the fit check ----------------
SIZES = (145.0, 160.0, 180.0)
BAND_Y = G.BAND_Y

# ---------------- colours ----------------
C_HOUSING = (0.62, 0.63, 0.65)     # matte grey MJF PA12 (natural); dyed black also fine
C_POD = (0.20, 0.20, 0.22)         # charcoal TPU
C_GOLD = U.C_GOLD
C_FLEX = (0.85, 0.50, 0.10)        # amber polyimide
C_PCB = U.C_PCB
C_FOAM = (0.10, 0.10, 0.11)
C_STRAP = (0.30, 0.31, 0.34)       # graphite woven webbing
C_LIPO = U.C_LIPO
C_METAL = U.C_METAL
C_SKIN = U.C_SKIN
C_CLEAR = (0.95, 0.75, 0.55)


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


def fab(stem, name, shape, qty, process, material, color, log, extra=None):
    d = {"kind": "3dp", "name": name, "source": stem + ".step", "qty": qty,
         "options": {"process": process, "material": material, "color": color},
         "features": U.features(shape)}
    if extra:
        d.update(extra)
    p = os.path.join(HERE, stem + '.fab.json')
    with open(p, 'w') as f:
        json.dump(d, f, indent=2)
        f.write('\n')
    log(f"  fab {os.path.relpath(p, ROOT)}: {d['features']}")
    return d


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


def cyl_y(r, cx, cz, y0=-100.0, length=200.0):
    """Cylinder with its axis along Y through (cx, cz)."""
    return Part.makeCylinder(r, length, V(cx, y0, cz), V(0, 1, 0))


def fillet_edges(shape, r, pick, log=None, tag=''):
    edges = [e for e in shape.Edges if pick(e)]
    if not edges:
        return shape
    try:
        s = shape.makeFillet(r, edges)
        if s.isValid():
            return s
    except Exception as ex:
        if log:
            log(f"  fillet {tag} r={r} failed on {len(edges)} edges: {ex}")
    return shape


def flex_pod(lift=FOAM_PROUD):
    """Flex pod (visual) in the pod-local frame with the pads lifted `lift` by the foam
    (FOAM_PROUD free, STACK_LOADED - FLEX_T worn): returns (polyimide, gold pads, foam disks).
    The flex between pads bridges at pad height and ramps down to the face at the pod ends."""
    L, w = POD_L, POD_W
    yp = PAD_Y[-1] + PAD_D / 2           # outer pad edge
    # side profile (Y, Z) of the flex underside (skin side), extruded across X
    prof = [(-L / 2, -0.25), (-yp, -lift), (yp, -lift), (L / 2, -0.25)]
    pts = [V(-w / 2, y, z - FLEX_T) for y, z in prof] + [V(-w / 2, y, z) for y, z in reversed(prof)]
    pts.append(pts[0])
    face = Part.Face(Part.makePolygon(pts))
    poly = face.extrude(V(w, 0, 0))
    for y in HOLE_Y:
        poly = poly.cut(Part.makeCylinder(HOLE_D / 2, 5, V(0, y, -3)))
    gold = []
    for y in PAD_Y:
        gold.append(Part.makeCylinder(PAD_D / 2, 0.04, V(0, y, -lift - FLEX_T - 0.04)))
    foam = []
    for y in PAD_Y:
        foam.append(Part.makeCylinder(FOAM_D / 2, lift + FOAM_POCKET_H, V(0, y, -lift)))
    return poly, gold, foam
