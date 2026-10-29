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

# ---------------- compliant contact (bought: pre-cut round double-sided foam dots) ----------------
FOAM_D = 6.0            # pre-cut double-sided foam dot, nominal diameter (sourcing: 6 mm dots)
FOAM_T = 2.0            # dot thickness (sourcing: pre-cut 6 x 2.0 mm double-sided EVA dots); pocket depth follows
PAD_PROUD = 1.0         # target: pad stands 1.0 mm proud of the shell face when free (~0.65 worn)
FOAM_POCKET_D = FOAM_D + 0.4                # dot diameter tolerance +/-0.2
FOAM_POCKET_H = max(FOAM_T - PAD_PROUD, 0.0)  # 1.0 for the 2.0 mm dots (0.5 for 1.5, 0 for 1.0)
MODULE_POCKET_H = min(FOAM_POCKET_H, 0.6)   # module pods 3/4 + root: floor 1.1 + 0.6 gap to the board leave 0.6 (1.4 proud with 2.0 dots)
FOAM_PROUD = FOAM_T - FOAM_POCKET_H         # 1.0 mm free, ~0.6-0.7 mm at 2-5 kPa
STACK = FOAM_PROUD + FLEX_T                  # shell face above the skin at a pad (free foam)
STACK_LOADED = 0.65 + FLEX_T                 # nominal worn (foam ~35 % compressed)

# ---------------- strap (bought: plain woven elastic webbing) ----------------
STRAP_W = 20.0          # webbing width (sourcing: 20.0 +/-0.5 mm polyester elastic); sleeves, slides, slots follow
STRAP_W_TOL = 0.6       # clearance over the nominal width in the pod sleeves and the slide (20.6)
STRAP_T = 1.5           # webbing thickness, sourced nominal: the fit model uses this
STRAP_T_MAX = 1.8       # design maximum (sourcing allows 1.2-1.8): every slot and sleeve clears this
STRAP_T_MIN = 1.2
CHANNEL_W = STRAP_W + STRAP_W_TOL
CHANNEL_H = STRAP_T_MAX + 0.1   # clear sleeve height (1.9)
BASE_T = FOAM_POCKET_H + 1.0  # pod shell face -> sleeve floor (foam pocket + 1.0 floor)
LIP_T = 1.0             # sleeve rims (>= 1.0 for FDM TPU)

# ---------------- pogo pins (bought; charger clip and SWD jig) ----------------
POGO_D = 0.68           # P50 barrel diameter (sourcing); plunger 0.48
POGO_L = 16.2           # overall length, plunger extended (sourcing 16.0-16.35)
POGO_TRAVEL = 2.6       # full plunger travel
POGO_WORK = 1.3         # working compression (half travel)
POGO_F_WORK = 0.74      # N per pin (~75 g, sourcing; taken as the force at the working point)
POGO_HOLE = 0.72        # printed hole for a glued pin (sourcing: 0.70-0.75; a drop of CA from below)
POGO_TIP_FREE = 1.7 + POGO_WORK   # charger: tip above the clip's contact face at rest (window depth + working)

# ---------------- cell (bought; sourcing) ----------------
CELL_MAX = (12.0, 25.0, 4.0)    # 401223-class protected cell, incl. board and tabs (pocket 12.4 x 25.5 x 4.2)
CELL_FALLBACK = (11.0, 21.0, 4.0)   # 401120-class: held by the cell_spacer

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


def flex_pod(lift=FOAM_PROUD, pocket=None):
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
    pocket = FOAM_POCKET_H if pocket is None else pocket
    for y in PAD_Y:
        foam.append(Part.makeCylinder(FOAM_D / 2, lift + pocket, V(0, y, -lift)))
    return poly, gold, foam
