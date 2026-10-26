"""module.py - rev C electronics module: curved pebble = base (chassis) + lid (cosmetic shell).

Module frame: X across the wrist (radial +), Y along the arm (distal = -Y), Z up; origin = apex of
the curved underside on the band centre line (y = 0 = pod centre line, strap centre line).
- Underside: cylinder R_U (axis along Y) hugging the dorsal wrist. It carries flex pods 3 and 4
  (tail between them at x = 0): foam pockets behind their pads and locating pins, like pod.py.
  So the module itself is two electrode pods; the skin sees only the six pads plus the
  recessed charge window.
- Board (28 x 26 x 1.0, all parts on top) lies flat on 4 standoffs, J1 (FPC) on the distal edge
  facing distal. The flex tail leaves the strip's distal edge (y = -POD_L/2), bends up through a
  floor slot next to the distal wall (U-turn) and enters J1 heading proximal (fingers on the
  non-skin side of the flex).
- LiPo 401225 (4 x 12 x 25) lies on the low parts (TQFP) beside J1, away from the antenna edge
  (board -X edge, plastic only: no metal within ~5 mm, strap bars are 1.75 mm filament).
- Charging: 2 pogo pins of the charger press on the board's bottom pads VCHG/GND through a
  stadium window in the underside, 1.7 mm deep (>= 1.5 mm: skin cannot touch, so it cannot be
  charged while worn). Two 3 x 1 mm N52 disc magnets in floor pockets pull the charger puck in.
- Lid: crowned top (R_T) with R2.2 edge fillets, light pipe over D1, a living-hinge button
  tongue with a stem onto SW1 (top-actuated TS-1088), snap beads, pry notch. A 0.5 x 0.3 mm
  groove at the parting line is the subtle 'chamfer line'.
- Strap: two lug ears per side; 20 mm strap loops around 1.75 mm filament bars (no metal near
  the antenna; standard 1.5 mm spring bars also fit the 1.8 mm holes on the radial side).
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/module.py
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import rc as R
import cadutil as U

V = FreeCAD.Vector

# ---------------- outside (mm) ----------------
OUT_W = 31.9              # across the wrist (board 28.7 + 2 x 0.5 + walls)
CX_OFF = 0.35             # body centre X: board grows on +X only; underside/pods/tail stay at X = 0
Y_MIN, Y_MAX = -17.5, 16.8  # along the arm (distal end holds the tail U-turn)
PLAN_R = 5.5
R_U = 42.0                # underside radius (dorsal wrist 33-42 mm on 145-180 wrists)
H_TOP = 9.9               # top apex above the underside apex
R_T = 65.0                # top crown radius (soft pebble crown across the wrist)
TOP_FILLET = 2.5          # max that keeps the lid clear of the cell's proximal end
BOT_FILLET = 1.4
WALL = 1.1
FLOOR = 1.1
LID_T = 1.0
IN_FILLET = TOP_FILLET - 1.05
H_BASE = 2.0              # parting surface: constant height above the underside
GROOVE_H, GROOVE_D = 0.3, 0.12   # soft parting hairline
TONGUE_T, TONGUE_H = 0.6, 1.5
BEAD_R, BEAD_LEN = 0.3, 16.0
# ---------------- board (placeholder until boards/neurband_c/neurband_c.step) ----------------
BOARD_STEP = os.path.join(R.ROOT, 'boards', 'neurband_c', 'neurband_c.step')
PCB_W, PCB_L, PCB_T = 28.7, 27.0, 1.0          # KiCad x (across), y (along, KiCad +y = distal); outline 28.7 x 27
J1_KX = 14.0                                   # KiCad x of J1 = module X 0 (tail, dorsal centre)
UNDER_GAP = 0.6                                # bottom pads / wire joints
COMP_H = 2.0                                   # placeholder component envelope
TAIL_R = 1.0                                   # tail bends
Y_B0 = -R.POD_L / 2 + 0.2                      # board distal edge (J1 mouth flush with it)
Z_PCB = FLOOR + UNDER_GAP
Z_PCB_TOP = Z_PCB + PCB_T
J1_W, J1_D, J1_H = 14.4, 5.12, 2.0
J1_X = 0.0                                     # J1 centred on the distal edge (KiCad x = 14)
J1_SLOT_DZ = 0.5                               # flex in J1 above the board top
SW1_K = (24.8, 25.1)                           # KiCad (x, y), from neurband_c.kicad_pcb 01:58
D1_K = (2.0, 1.0)                              # KiCad
CHG_K = ((14.0, 6.0), (14.0, 9.0))             # KiCad: VCHG / GND bottom pads (moved off the flex spine)
SW1_H = 2.0


def k2m(x, y):
    """KiCad top view (x right, y down) -> module (X, Y): board distal edge (KiCad y = PCB_L) at Y_B0."""
    return x - J1_KX, Y_B0 + PCB_L - y


SW1 = k2m(*SW1_K)
D1 = k2m(*D1_K)
CHG_PADS_Y = tuple(k2m(*p)[1] for p in CHG_K)
ANT_X = (-14.0, -8.0)                          # antenna strip (KiCad x 0..6)
STANDOFFS_K = [(1.6, 1.6), (26.4, 1.6), (1.6, 25.4), (26.6, 22.6)]   # KiCad, board bottom (clear of J2/J3/TP pads)
STANDOFFS = [k2m(*p) for p in STANDOFFS_K]
STANDOFF_D = 2.0
# ---------------- battery ----------------
BAT_W, BAT_L, BAT_T = 12.0, 25.0, 4.0          # 401225, 25 along the arm
BAT_X0 = -3.5                                  # 4.5 mm from the antenna strip; clear of the crowned lid
BAT_Y0 = Y_B0 + J1_D + 0.15                    # just proximal of J1
COMP_UNDER_BAT = 1.3                           # TQFP-64 1.2 mm is the tallest part under it
BAT_TAPE = 0.15
BAT_SWELL = 0.3
# ---------------- lid features ----------------
LP_D, LP_TUBE = 1.6, 3.0                       # light pipe (1.5 mm PMMA rod or clear resin)
BTN_HOLE_D, BTN_GAP_R = 5.0, 0.1                # flush button cap in a 5.0 mm opening (0.1 mm hairline)
BTN_FLANGE_D, BTN_FLANGE_T = 6.0, 0.6
BTN_STEM_D, BTN_GAP = 2.0, 0.15
NOTCH_W = 3.0
# ---------------- underside features ----------------
CHG_WIN = (3.0, 6.0)                           # stadium window (X, Y) to the pads
CHG_CB = (4.0, 8.0, 0.4)                       # locating counterbore for the charger nose
CHG_Y = sum(CHG_PADS_Y) / 2
MAG_D, MAG_T, MAG_SKIN = 3.1, 1.05, 0.35
MAG_X = 3.6                                    # magnets beside the window (x = +/-3.6), clear of the spine and pods
TAIL_SLOT = (R.TAIL_W + 0.7, 1.8)              # X, Y
# ---------------- hidden strap lugs (slots in the module ends, integral bars) ----------------
SLOT_W = R.STRAP_W + 2.2                       # along the arm (webbing 25 + loop side links)
SLOT_D = 3.35                                  # depth into the body from each X end face
SLOT_TOP = 1.2                                 # slot roof (board bottom at 1.7 rests on the roof)
SLOT_WALL = 0.8
BAR_IN, BAR_Z = 0.7, -1.0                      # bar centre: from the end face (outer face ~flush), height; wrap clears paddle and link
BAR_T, BAR_H = 1.3, 1.6                        # integral PA12 bar section (X x Z), stadium (<= 5 N)
J2_RELIEF = ((23.2, 28.4), (24.4, 26.8))       # KiCad x, y under the J2 battery pads: no slot roof

YC = (Y_MIN + Y_MAX) / 2


def end_x(sx):
    return CX_OFF + sx * OUT_W / 2


def bar_x(sx):
    return end_x(sx) - sx * BAR_IN


OUT_L = Y_MAX - Y_MIN
IN_W, IN_L = OUT_W - 2 * WALL, OUT_L - 2 * WALL
Y_B1 = Y_B0 + PCB_L
POD_TH = 9.0 / R_U                             # pods 3/4 at arc +/-9 mm on the underside
Z_BAT = Z_PCB_TOP + COMP_UNDER_BAT + BAT_TAPE


def z_u(x):
    return math.sqrt(R_U ** 2 - x * x) - R_U


def z_top(x):
    return H_TOP - (R_T - math.sqrt(R_T ** 2 - x * x))


def ucyl(r):
    """Cylinder about the underside axis (0, -R_U), radius r."""
    return R.cyl_y(r, 0.0, -R_U)


def tcyl(r):
    return R.cyl_y(r, 0.0, H_TOP - R_T)


def prism(w, l, r, z0=-15.0, h=40.0):
    return R.rrect(w, l, r, h, z0, CX_OFF, YC)


def body(log=None):
    s = prism(OUT_W, OUT_L, PLAN_R).common(tcyl(R_T)).cut(ucyl(R_U))
    s = R.fillet_edges(s, TOP_FILLET, lambda e: e.BoundBox.ZMin > 4.0, log, 'top')
    s = R.fillet_edges(s, BOT_FILLET, lambda e: e.BoundBox.ZMax < 0.5 and e.BoundBox.ZMax - e.BoundBox.ZMin < 4.0
                       and (abs(e.BoundBox.XMax - CX_OFF) > OUT_W / 2 - 1.0 or abs(e.BoundBox.YMax - Y_MAX) < 0.5
                            or abs(e.BoundBox.YMin - Y_MIN) < 0.5), log, 'bottom')
    return s


def cavity(log=None):
    c = prism(IN_W, IN_L, PLAN_R - WALL).common(tcyl(R_T - LID_T)).cut(ucyl(R_U + FLOOR))
    return R.fillet_edges(c, IN_FILLET, lambda e: e.BoundBox.ZMin > 3.0, log, 'cavity')


def pod_place(sign):
    """Placement of a pod-local frame on the underside at arc sign*9 mm."""
    th = sign * POD_TH
    return FreeCAD.Placement(V(R_U * math.sin(th), 0, R_U * math.cos(th) - R_U),
                             FreeCAD.Rotation(V(0, 1, 0), math.degrees(th)))


def stadium_z(w, l, z0, h, cx=0.0, cy=0.0):
    """Stadium (rounded slot) in plan, long along Y, extruded along Z."""
    r = w / 2
    s = R.box(cx - r, cx + r, cy - l / 2 + r, cy + l / 2 - r, z0, z0 + h)
    for sy in (-1, 1):
        s = s.fuse(Part.makeCylinder(r, h, V(cx, cy + sy * (l / 2 - r), z0)))
    return s


def capsule_xz(p0, p1, r, y0, y1):
    (x0, z0), (x1, z1) = p0, p1
    c = Part.makeCylinder(r, y1 - y0, V(x0, y0, z0), V(0, 1, 0)).fuse(
        Part.makeCylinder(r, y1 - y0, V(x1, y0, z1), V(0, 1, 0)))
    L = math.hypot(x1 - x0, z1 - z0)
    b = Part.makeBox(L, y1 - y0, 2 * r, V(0, y0, -r))
    b.rotate(V(0, y0, 0), V(0, 1, 0), -math.degrees(math.atan2(z1 - z0, x1 - x0)))
    b.translate(V(x0, 0, z0))
    return c.fuse(b).removeSplitter()


def build_base(log=None):
    full = body(log)
    b = full.common(ucyl(R_U + H_BASE))
    lid_zone = full.cut(ucyl(R_U + H_BASE))
    cav = cavity(log)
    b = b.cut(cav)
    # tongue (inside the lid wall) with snap beads on the long sides; cut back over the tail riser
    ring = prism(IN_W, IN_L, PLAN_R - WALL).cut(prism(IN_W - 2 * TONGUE_T, IN_L - 2 * TONGUE_T, PLAN_R - WALL - TONGUE_T))
    tongue = ring.common(ucyl(R_U + H_BASE + TONGUE_H)).cut(ucyl(R_U + FLOOR - 0.01))
    tongue = tongue.cut(R.box(-R.TAIL_W / 2 - 1.5, R.TAIL_W / 2 + 1.5, Y_MIN - 1, Y_MIN + WALL + TONGUE_T + 0.5, -10, 20))
    b = b.fuse(tongue)
    for bx0, bx1, yw, zw in beads():
        b = b.fuse(Part.makeCylinder(BEAD_R, bx1 - bx0, V(bx0, yw, zw), V(1, 0, 0)))
    # board standoffs
    for x, y in STANDOFFS:
        b = b.fuse(Part.makeCylinder(STANDOFF_D / 2, Z_PCB - z_u(abs(x)) - 0.6, V(x, y, z_u(abs(x)) + 0.6)))
    # hidden lug slots: a block inside each X end (slot roof = board ledge, inner and side walls)
    for sx in (-1, 1):
        xe = end_x(sx)
        xa, xb_ = sorted((xe - sx * (WALL + 0.01), xe - sx * (SLOT_D + SLOT_WALL)))
        blk = R.box(xa, xb_, -SLOT_W / 2 - SLOT_WALL, SLOT_W / 2 + SLOT_WALL, -10, Z_PCB).common(cav)
        b = b.fuse(blk)
    b = b.removeSplitter()
    for sx in (-1, 1):
        b = b.cut(slot_void(sx))
        # integral bar (stadium section) across the slot
        xc = bar_x(sx)
        bar = R.box(xc - BAR_T / 2, xc + BAR_T / 2, -SLOT_W / 2 - 0.01, SLOT_W / 2 + 0.01, BAR_Z - BAR_H / 2 + BAR_T / 2, BAR_Z + BAR_H / 2 - BAR_T / 2)
        for dz in (-1, 1):
            bar = bar.fuse(Part.makeCylinder(BAR_T / 2, SLOT_W + 0.02, V(xc, -SLOT_W / 2 - 0.01, BAR_Z + dz * (BAR_H / 2 - BAR_T / 2)), V(0, 1, 0)))
        b = b.fuse(bar)
    # relief under the J2 battery pads (wire joints) in the +X slot roof
    (kx0, kx1), (ky0, ky1) = J2_RELIEF
    (mx0, my1), (mx1, my0) = k2m(kx0, ky0), k2m(kx1, ky1)
    b = b.cut(R.box(mx0, mx1, my0, my1, Z_PCB - 1.0, Z_PCB + 1))
    b = b.removeSplitter()
    # pods 3/4: foam pockets + locating pins on the underside
    for sgn in (-1, 1):
        pl = pod_place(sgn)
        for y in R.PAD_Y:
            p = Part.makeCylinder(R.FOAM_POCKET_D / 2, R.FOAM_POCKET_H, V(0, y, 0))
            p.Placement = pl.multiply(p.Placement)
            b = b.cut(p)
        for y in R.HOLE_Y:
            pin = Part.makeCylinder(0.525, 0.55 - 0.525 + 0.3, V(0, y, -0.55 + 0.525))
            pin = pin.fuse(Part.makeSphere(0.525, V(0, y, -0.55 + 0.525)).common(Part.makeCylinder(0.525, 0.525, V(0, y, -0.55))))
            pin.Placement = pl.multiply(pin.Placement)
            b = b.fuse(pin)
    # tail slot through the floor next to the distal wall
    b = b.cut(R.box(-TAIL_SLOT[0] / 2, TAIL_SLOT[0] / 2, Y_MIN + WALL, Y_MIN + WALL + TAIL_SLOT[1], -10, FLOOR + 2))
    # charge window + locating counterbore + magnet pockets (from inside)
    b = b.cut(stadium_z(CHG_WIN[0], CHG_WIN[1], -10, 20, 0, CHG_Y))
    b = b.cut(stadium_z(CHG_CB[0], CHG_CB[1], -10, 10 + CHG_CB[2], 0, CHG_Y))
    for sx in (-1, 1):
        b = b.cut(Part.makeCylinder(MAG_D / 2, 5, V(sx * MAG_X, CHG_Y, MAG_SKIN)))
    # parting-line groove (lower half)
    b = b.cut(groove())
    return b.removeSplitter()


def slot_void(sx):
    xe = end_x(sx)
    xa, xb_ = sorted((xe + sx * 2, xe - sx * SLOT_D))
    return R.box(xa, xb_, -SLOT_W / 2, SLOT_W / 2, -10, SLOT_TOP)


def beads():
    """Snap beads on the +/-Y walls (the X walls carry the lug slots): (x0, x1, y, z); z follows the
    curved parting surface over each short segment."""
    yp, yd = Y_MAX - WALL + BEAD_R - 0.25, Y_MIN + WALL - BEAD_R + 0.25
    out = []
    for x0, x1, yy in ((CX_OFF - 5, CX_OFF + 5, yp), (-10.0, -7.0, yd), (7.0, 10.0, yd)):
        xm = max(abs(x0), abs(x1)) if x0 * x1 > 0 else max(abs(x0), abs(x1))
        zlo = z_u(xm) + H_BASE                       # tongue bottom at the segment's outer end
        zhi = z_u(min(abs(x0), abs(x1)) if x0 * x1 > 0 else 0.0) + H_BASE + TONGUE_H
        out.append((x0, x1, yy, (zlo + zhi) / 2))
    return out


def groove():
    band = ucyl(R_U + H_BASE + GROOVE_H / 2).cut(ucyl(R_U + H_BASE - GROOVE_H / 2))
    return band.common(prism(OUT_W + 2, OUT_L + 2, PLAN_R).cut(prism(OUT_W - 2 * GROOVE_D, OUT_L - 2 * GROOVE_D, PLAN_R - GROOVE_D)))


def cavity_raw():
    return prism(IN_W, IN_L, PLAN_R - WALL).common(tcyl(R_T - LID_T)).cut(ucyl(R_U + FLOOR))


def build_button_cap(log=None):
    """Flush disc cap over SW1: top follows the lid surface, flange under the lid, stem onto SW1."""
    x, y = SW1
    top = Part.makeCylinder(BTN_HOLE_D / 2 - BTN_GAP_R, 30, V(x, y, -5)).common(body(log))
    zt = top.BoundBox.ZMax
    rf = BTN_FLANGE_D / 2                            # under the lid: below its lowest inner point over the flange
    z_in = min(z_top(x - rf), z_top(x + rf)) - LID_T - 0.5
    top = top.common(R.box(x - 5, x + 5, y - 5, y + 5, z_in, zt + 1))
    flange = Part.makeCylinder(BTN_FLANGE_D / 2, BTN_FLANGE_T, V(x, y, z_in - BTN_FLANGE_T))
    z_sw = Z_PCB_TOP + SW1_H + BTN_GAP
    stem = Part.makeCylinder(BTN_STEM_D / 2, z_in - BTN_FLANGE_T - z_sw + 0.01, V(x, y, z_sw))
    return top.fuse([flange, stem]).removeSplitter()


def build_lid(log=None):
    l = body(log).cut(ucyl(R_U + H_BASE))
    cav = cavity(log)
    l = l.cut(cav)
    for bx0, bx1, yw, zw in beads():
        l = l.cut(Part.makeCylinder(BEAD_R + 0.05, bx1 - bx0 + 1, V(bx0 - 0.5, yw, zw), V(1, 0, 0)))
    for sx in (-1, 1):
        l = l.cut(slot_void(sx))
    # light pipe: through hole + guide tube down to the LED
    x, y = D1
    zt = z_top(x)
    tube = Part.makeCylinder(LP_TUBE / 2, zt - (Z_PCB_TOP + 1.4), V(x, y, Z_PCB_TOP + 1.4)).common(cavity_raw())
    l = l.fuse(tube).cut(Part.makeCylinder(LP_D / 2, 20, V(x, y, Z_PCB_TOP + 0.5)))
    # flush button: round opening for the separate cap (button_cap), hairline gap
    x, y = SW1
    l = l.cut(Part.makeCylinder(BTN_HOLE_D / 2, 20, V(x, y, 0)))
    # pry notch at the proximal parting line
    zp = H_BASE
    l = l.cut(R.box(-NOTCH_W / 2, NOTCH_W / 2, Y_MAX - WALL - 0.1, Y_MAX + 1, zp - 0.1, zp + 0.6))
    l = l.cut(groove())
    return l.removeSplitter()


# ---------------- internals (visual + clash check) ----------------
def board_placeholder():
    pcb = R.rrect(PCB_W, PCB_L, 1.0, PCB_T, Z_PCB, PCB_W / 2 - J1_KX, Y_B0 + PCB_L / 2)
    parts = []
    def comp(cx, cy, w, l, h):
        parts.append(R.box(cx - w / 2, cx + w / 2, cy - l / 2, cy + l / 2, Z_PCB_TOP, Z_PCB_TOP + h))
    comp(J1_X, Y_B0 + J1_D / 2, J1_W, J1_D, J1_H)          # FPC connector
    comp(SW1[0], SW1[1], 3.0, 3.9, SW1_H)                   # TS-1088
    comp(D1[0], D1[1], 1.6, 0.8, 0.6)                       # LED 0603
    comp(*k2m(20.2, 10.1), 12.0, 12.0, 1.2)                 # U2 ADS1298 TQFP-64
    comp(*k2m(9.0, 5.7), 6.0, 6.0, 0.85)                    # U1 nRF52832 QFN-48
    return pcb, Part.makeCompound(parts), 'placeholder'


def board_real():
    sh = Part.read(BOARD_STEP)
    sols = [s for s in sh.Solids]
    pcb = max(sols, key=lambda s: s.BoundBox.XLength * s.BoundBox.YLength if s.BoundBox.ZLength < PCB_T + 0.1 else 0)
    bb = pcb.BoundBox
    dx, dy, dz = -(bb.XMin + J1_KX), Y_B0 - bb.YMin, Z_PCB - bb.ZMin     # KiCad STEP: X = x
    out = []
    for s in sols:
        s = s.copy()
        s.translate(V(dx, dy, dz))
        out.append(s)
    pcb = out[sols.index(pcb)]
    parts = [s for s in out if s is not pcb]
    return pcb, Part.makeCompound(parts), f'real ({os.path.relpath(BOARD_STEP, R.ROOT)})'


def board():
    if os.path.exists(BOARD_STEP):
        try:
            return board_real()
        except Exception:
            pass
    return board_placeholder()


def battery():
    b = R.box(BAT_X0, BAT_X0 + BAT_W, BAT_Y0, BAT_Y0 + BAT_L, Z_BAT, Z_BAT + BAT_T)
    try:   # pouch cell: rounded corners and top edges (~R1 in reality)
        b = b.makeFillet(0.8, [e for e in b.Edges if e.BoundBox.ZLength > BAT_T - 0.01])
        b = b.makeFillet(0.8, [e for e in b.Edges if e.BoundBox.ZMin > Z_BAT + BAT_T - 0.01])
    except Exception:
        pass
    swell = R.box(BAT_X0 + 2, BAT_X0 + BAT_W - 2, BAT_Y0 + 4, BAT_Y0 + BAT_L - 4, Z_BAT, Z_BAT + BAT_T + BAT_SWELL)
    return b, swell


def tail_shape():
    """Installed tail in module coords: from the strip's distal edge at the underside, U-turn up
    through the floor slot, into J1. Returns (shape, length)."""
    t, w, r = R.TAIL_T, R.TAIL_W, TAIL_R
    y_root = -R.POD_L / 2
    z0 = -R.FLEX_T / 2
    z1 = Z_PCB_TOP + J1_SLOT_DZ
    yr = y_root - r
    def arc(cy, cz, a0, a1):
        ring = Part.makeCylinder(r + t / 2, w, V(J1_X - w / 2, cy, cz), V(1, 0, 0)).cut(
            Part.makeCylinder(r - t / 2, w, V(J1_X - w / 2, cy, cz), V(1, 0, 0)))
        L = 3 * r
        pts = [V(J1_X - w / 2, cy, cz)] + [V(J1_X - w / 2, cy + L * math.cos(math.radians(a)), cz + L * math.sin(math.radians(a)))
                                          for a in (a0, (a0 + a1) / 2, a1)] + [V(J1_X - w / 2, cy, cz)]
        return ring.common(Part.Face(Part.makePolygon(pts)).extrude(V(w, 0, 0)))
    y_in = Y_B0 + 3.6                                     # inserted into J1
    segs = [arc(y_root, z0 + r, 180, 270),
            R.box(J1_X - w / 2, J1_X + w / 2, yr - t / 2, yr + t / 2, z0 + r, z1 - r),
            arc(y_root, z1 - r, 90, 180),
            R.box(J1_X - w / 2, J1_X + w / 2, y_root, y_in, z1 - t / 2, z1 + t / 2)]
    length = math.pi * r + (z1 - z0 - 2 * r) + (y_in - y_root)
    return segs[0].fuse(segs[1:]).removeSplitter(), length


def flex_on_module(lift=R.FOAM_PROUD):
    """Flex pods 3/4 (+ pads, foam) on the underside and the spine link between them."""
    poly, gold, foam = [], [], []
    p0, g0, f0 = R.flex_pod(lift)
    for sgn in (-1, 1):
        pl = pod_place(sgn)
        for src, dst in ((p0, poly), (g0, gold), (f0, foam)):
            for s in (src if isinstance(src, list) else [src]):
                s = s.copy()
                s.Placement = pl.multiply(s.Placement)
                dst.append(s)
    # spine link between pods 3 and 4 along the underside (arc), distal band
    a0 = -POD_TH + (R.POD_W / 2) / R_U
    y0, y1 = R.SPINE_Y
    ring = ucyl(R_U).cut(ucyl(R_U - R.FLEX_T)).common(R.box(-50, 50, y0, y1, -50, 50))
    wedge = Part.Face(Part.makePolygon([V(0, y0, -R_U), V(60 * math.sin(a0), y0, -R_U + 60 * math.cos(a0)),
                                        V(0, y0, 20), V(-60 * math.sin(a0), y0, -R_U + 60 * math.cos(a0)), V(0, y0, -R_U)])).extrude(V(0, y1 - y0, 0))
    poly.append(ring.common(wedge))
    return poly, gold, foam


def internals():
    pcb, parts, src = board()
    bat, swell = battery()
    tail, tl = tail_shape()
    mags = Part.makeCompound([Part.makeCylinder(1.5, 1.0, V(sx * MAG_X, CHG_Y, MAG_SKIN + 0.02)) for sx in (-1, 1)])
    lp = Part.makeCylinder(0.75, 20, V(D1[0], D1[1], Z_PCB_TOP + 1.3)).common(body())     # flush with the lid
    cap = build_button_cap()
    return dict(pcb=pcb, parts=parts, src=src, bat=bat, swell=swell, tail=tail, tail_len=tl, mags=mags, lp=lp, cap=cap)


if not getattr(sys, 'neurband_lib', False):
    log = R.Log('module')
    base = U.check(build_base(log), 'module_base', log)
    lid = U.check(build_lid(log), 'module_lid', log)
    I = internals()
    fpoly, fgold, ffoam = flex_on_module()
    log(f"  board: {I['src']}")
    log(f"  outside {OUT_W:.1f} (X) x {OUT_L:.1f} (Y {Y_MIN}..{Y_MAX}) mm, top apex {H_TOP:.1f} above the underside apex, "
        f"underside edge z {z_u(OUT_W / 2):.2f}; hidden lug slots {SLOT_W:.1f} x {SLOT_D} mm, no protrusions")
    log(f"  z: floor {FLOOR}, pcb {Z_PCB:.2f}-{Z_PCB_TOP:.2f}, cell {Z_BAT:.2f}-{Z_BAT + BAT_T:.2f} (+{BAT_SWELL}), "
        f"lid inner apex {H_TOP - LID_T:.2f}; charge pads recess depth {Z_PCB:.2f} mm")
    log(f"  tail path needed {I['tail_len']:.1f} mm from the strip edge")
    bb = I['parts'].BoundBox
    log(f"  tallest board part top z {bb.ZMax:.2f} ({bb.ZMax - Z_PCB_TOP:.2f} above the board)")
    def clash(a, b):
        try:
            return round(a.common(b).Volume, 3)
        except Exception:
            return None
    checks = {
        'pcb_vs_base': clash(I['pcb'], base), 'pcb_vs_lid': clash(I['pcb'], lid),
        'parts_vs_lid': clash(I['parts'], lid), 'parts_vs_base': clash(I['parts'], base),
        'bat_vs_lid': clash(I['bat'], lid), 'bat_swell_vs_lid': clash(I['swell'], lid),
        'bat_vs_parts': clash(I['bat'], I['parts']), 'bat_vs_base': clash(I['bat'], base),
        'tail_vs_base': clash(I['tail'], base), 'tail_vs_lid': clash(I['tail'], lid),
        'tail_vs_pcb': clash(I['tail'], I['pcb']), 'base_vs_lid': clash(base, lid),
        'flex_vs_base': clash(Part.makeCompound(fpoly), base),
        'cap_vs_lid': clash(I['cap'], lid), 'cap_vs_parts': clash(I['cap'], I['parts']),
    }
    log("  clash mm3: " + json.dumps(checks))
    xa = BAT_X0 - ANT_X[1]
    log(f"  cell edge to antenna strip {xa:.1f} mm; magnets to antenna strip {0 - 1.5 - ANT_X[1]:.1f} mm")
    with open(os.path.join(R.HERE, 'logs', 'module_checks.json'), 'w') as f:
        json.dump(dict(checks=checks, board=I['src'], tail_len=I['tail_len']), f, indent=1)
    R.save('module_base', [('module_base', base, R.C_HOUSING)], log)
    R.save('module_lid', [('module_lid', lid, R.C_HOUSING)], log)
    R.save('module_assy', [('module_base', base, R.C_HOUSING), ('module_lid', lid, R.C_HOUSING),
                           ('main_board', I['pcb'], R.C_PCB), ('board_parts', I['parts'], (0.15, 0.15, 0.15)),
                           ('lipo', I['bat'], R.C_LIPO), ('tail', I['tail'], R.C_FLEX),
                           ('flex_pods_3_4', Part.makeCompound(fpoly), R.C_FLEX),
                           ('pads', Part.makeCompound(fgold), R.C_GOLD), ('foam', Part.makeCompound(ffoam), R.C_FOAM),
                           ('magnets', I['mags'], R.C_METAL), ('button_cap', I['cap'], R.C_HOUSING),
                           ('light_pipe', I['lp'], (0.92, 0.92, 0.90))], log)
    R.save('button_cap', [('button_cap', I['cap'], R.C_HOUSING)], log)
    R.fab('module_base', 'neurband rev C module base (chassis, carries pods 3/4)', base, 3, 'mjf', 'pa12', 'gray', log)
    R.fab('module_lid', 'neurband rev C module lid (crowned shell)', lid, 3, 'mjf', 'pa12', 'gray', log)
    R.fab('button_cap', 'neurband rev C flush button cap', I['cap'], 4, 'mjf', 'pa12', 'gray', log)
    R.finish(log)
