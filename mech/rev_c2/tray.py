"""tray.py - neurband rev C2 bonding tray (a printed tool, not worn).

The tray's top is the skin plane. The flex lies on it electrodes down, located by sixteen low pins
through its alignment holes. The tub and the six pods, with tape on their pads, are then pressed
straight down onto it: the tub between four posts that stand in its strap bays, each pod between
four corner posts. Pressing a pod down until its middle pad touches flattens both wings, so the
flex is bonded with the wings level, which leaves it slack in every other state.

Run: unset DISPLAY WAYLAND_DISPLAY; QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c2/tray.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True
import FreeCAD, Part
import c2 as R
import params as P
import case as C
import pod as PD

V = FreeCAD.Vector
TRAY_T = 2.4
MARGIN = 3.5
PIN_D, PIN_H, PIN_TIP = P.HOLE_D - 0.20, 0.40, 0.20          # low pins: 0.6 mm in all, 0.3 mm above the tape, so they do not lift it
POST_H_POD, POST_H_TUB = 5.0, 5.5
CLR = 0.20
POD_X = {1: 2.5 * P.PITCH, 2: 1.5 * P.PITCH, 3: 0.5 * P.PITCH, 4: -0.5 * P.PITCH,
         5: -1.5 * P.PITCH, 6: -2.5 * P.PITCH, 7: -3.5 * P.PITCH, 8: -4.5 * P.PITCH}
LIFT = P.TAPE_T + P.FLEX_T                    # the parts sit this much above the tray when the flex is under them
FONT = '/usr/share/fonts/noto/NotoSans-Black.ttf'


def pins():
    out = []
    for k, x in POD_X.items():
        for y in P.HOLE_Y:
            out.append(Part.makeCylinder(PIN_D / 2, PIN_H + 0.1, V(x, y, -0.1)))
            out.append(Part.makeCone(PIN_D / 2, PIN_D / 2 - 0.15, PIN_TIP, V(x, y, PIN_H)))
    return out


def build_tray(log=None):
    hw, hl = P.POD_SHELL_W / 2, P.POD_SHELL_L / 2
    x0, x1 = POD_X[8] - hw - MARGIN - 1.5, POD_X[1] + hw + MARGIN + 1.5
    y0, y1 = -P.POD_L / 2 - P.TAIL_FREE_L - 2.0, hl + MARGIN + 1.5
    t = R.box(x0, x1, y0, y1, -TRAY_T, 0.0)
    t = R.fillet_edges(t, 3.0, lambda e: e.BoundBox.ZLength > TRAY_T - 0.01, log, 'tray corners')
    add = pins()                                  # through the flex holes of all eight paddles
    # corner posts for the six pods
    for k, x in POD_X.items():
        if k in (3, 4):
            continue
        for sx in (1, -1):
            for sy in (1, -1):
                xa, ya = x + sx * (hw + CLR), sy * (hl + CLR)
                pts = [(xa, ya - sy * 3.0), (xa, ya), (xa - sx * 2.6, ya), (xa - sx * 2.6, ya + sy * 1.5), (xa + sx * 1.5, ya + sy * 1.5), (xa + sx * 1.5, ya - sy * 3.0)]
                add.append(R.prism_xy(pts, -0.1, POST_H_POD))
    # posts in the tub's strap bays (clear of the flex links); their ends, 0.2 mm from the lugs, locate the tub along the arm
    for sx in (1, -1):
        xa = P.XC + sx * (P.BODY_HX + CLR)
        xb = xa + sx * 2.6
        for ya, yb in ((P.SPINE_Y[1] + 1.6, P.SLOT_W / 2 - CLR), (-P.SLOT_W / 2 + CLR, P.SPINE_Y[0] - 1.4)):
            add.append(R.box(min(xa, xb), max(xa, xb), ya, yb, -0.1, POST_H_TUB))
    t = t.fuse(add).removeSplitter()
    # engraved pod numbers and a mark for the hand side
    cuts = []
    for k, x in POD_X.items():
        try:
            wires = Part.makeWireString(str(k), FONT, '', 3.6) if False else Part.makeWireString(str(k), os.path.dirname(FONT) + '/', os.path.basename(FONT), 3.6)
        except Exception:
            wires = []
        faces = [Part.makeFace(w, 'Part::FaceMakerBullseye') for w in wires if w]
        if faces:
            g = Part.makeCompound(faces)
            c = g.BoundBox.Center
            g.translate(V(x - c.x, y1 - 2.6 - c.y, -0.4))
            cuts.extend(f.extrude(V(0, 0, 0.6)) for f in g.Faces)
    if cuts:
        try:
            t2 = t.cut(Part.makeCompound(cuts))
            if t2.isValid() and len(t2.Solids) == 1:
                t = t2
        except Exception as ex:
            if log:
                log(f"  numbers skipped: {ex}")
    return t.removeSplitter()


def loaded(tray):
    """Tray with the flex, the tub and the six pods pressed on (wings flat)."""
    tub = R.moved(C.build_tub(), 0, 0, -P.Z_SKIN + LIFT)
    pod0, _ = PD.build_pod(travel=P.WING_D0)          # pressed until the middle pad touches: wings flat
    pods = []
    for k, x in POD_X.items():
        if k in (3, 4):
            continue
        pods.append(R.moved(pod0, x, 0, P.POD_HC + LIFT))
    # flex, flat on the tray
    w = P.POD_W
    flex = [R.box(x - w / 2, x + w / 2, -P.POD_L / 2, P.POD_L / 2, 0.0, P.FLEX_T) for x in POD_X.values()]
    flex.append(R.box(POD_X[8], POD_X[1], P.SPINE_Y[0], P.SPINE_Y[1], 0.0, P.FLEX_T))
    flex.append(R.box(-P.TAIL_W / 2, P.TAIL_W / 2, -P.POD_L / 2 - P.TAIL_FREE_L, -3.0, 0.0, P.FLEX_T))
    f = flex[0].fuse(flex[1:]).removeSplitter()
    for x in POD_X.values():
        for y in P.HOLE_Y:
            f = f.cut(Part.makeCylinder(P.HOLE_D / 2, 1.0, V(x, y, -0.5)))
    return tub, Part.makeCompound(pods), f


if not getattr(sys, 'neurband_tray_lib', False):
    log = R.Log('tray')
    tray = R.check(build_tray(log), 'bond_tray', log)
    bb = tray.BoundBox
    log(f"  tray {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.2f}; 16 pins {PIN_D:.2f} x {PIN_H + PIN_TIP:.2f}; pod posts {POST_H_POD}, tub posts {POST_H_TUB}")
    tub, pods, flex = loaded(tray)
    pin_c = Part.makeCompound(pins())
    log(f"  pins: {PIN_H + PIN_TIP - LIFT:.2f} above the pad planes; nearest plastic above them: tub {pin_c.distToShape(tub)[0]:.2f}, pods {pin_c.distToShape(pods)[0]:.2f} mm")
    need, have = P.tail_need()
    log(f"  tub between its posts: +-{CLR:.2f} mm along the arm; the tail has {have - need:.2f} mm to spare, so slide the tub toward the elbow before pressing")
    pod1 = pods.Solids if hasattr(pods, 'Solids') else []
    log(f"  on the tray: tub-tray {R.clash(tub, tray):.3f}, pods-tray {R.clash(pods, tray):.3f}, flex-tray {R.clash(flex, tray):.3f}, "
        f"tub-pods {R.clash(tub, pods):.3f}, pods-flex {R.clash(pods, flex):.3f} mm3 (pods drawn pressed flat)")
    bed, worst, flat = R.bed_report(R.on_bed(tray))
    log(f"  on the bed: contact {bed:.0f} mm2, steepest overhang {worst:.0f} deg, flat ceilings {flat[:3]}")
    R.save('bond_tray', [('bond_tray', tray, R.C_TRAY)], log)
    R.save('tray_loaded', [('bond_tray', tray, R.C_TRAY), ('flex', flex, R.C_FLEX), ('tub', tub, R.C_TUB), ('pods', pods, R.C_POD)], log)
    R.finish(log)
