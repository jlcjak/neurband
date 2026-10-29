"""housing.py - module housing (base + lid) for the real neurband main board (54 x 34 mm,
boards/neurband_main, see docs/layout/main_board_layout.md) and a 402030 LiPo.

Local frame = wrist frame shifted to the housing: X = around the wrist (radial +), Y = along the
arm (front/distal = -Y), Z up; origin = apex of the curved seat on the band centre line, so
x = 0 is the dorsal centre and the flex tail (between pods 4 and 5).
The flex tail leaves the DISTAL edge of the electrode strip, so J2 (top side, on the board's
upper long edge, opening outward) must face distal: the board's 54 mm side runs ACROSS the wrist.
The board is rotated 180 deg about Z from the KiCad top view (antenna end radial, J1 end
ulnar) and shifted so that J2 is centred on the tail (x = 0).
Underside: a 38 mm wide curved seat (R44 on the pod rails) with the strap lugs on its ends,
and flat wings beyond it. The board sits flat on bosses; the cell sits above the AFE half of
the board (away from the antenna). The lid snaps off for charging and programming.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/housing.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import cadutil as U

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
PCB_L, PCB_W, PCB_T = 54.0, 34.0, 1.6     # KiCad x (across the wrist here), y (along the arm)
ANT_OVERHANG = 5.05                        # ESP32-S3-MINI antenna beyond KiCad x = 0
ANT_CLEAR = 1.0                            # plastic only around the antenna
J2_X_PCB, J2_OPEN_Y_PCB = 34.6, 0.5        # J2 centre x, cable opening y (KiCad)
J2_SLOT_DZ = 0.5                           # cable centre above the board top
H_HOLES_PCB = [(3.0, 3.0), (3.0, 31.0)]    # M2 NPTH (use nylon screws: next to the antenna)
SW1_PCB = (8.5, 31.0)                      # BOOT button (top actuated)
J1_PCB = (50.8, 29.0)                      # battery JST-SH, 2.96 mm tall
TP_ROW_PCB = (23.0, 33.2, 32.3)            # programming pads x0..x1 at y (lid off for access)
BOARD_STEP = 'main_board.step'             # kicad-cli pcb export step (components included)
PCB_CLEAR = 0.4
UNDER_GAP = 0.6                            # bosses: board bottom above the floor
COMP_UNDER_CELL = 1.6                      # tallest part under the cell (SOT-23-5 1.55)
CELL_FOAM = 0.4
BAT_T, BAT_X, BAT_Y = 4.0, 32.4, 20.0      # 402030 incl. PCM along KiCad x
BAT_PCB = (15.6, 10.0)                     # cell corner (KiCad x, y): >= 15 mm from the antenna
BAT_SWELL = 0.4
WALL = 1.6
FLOOR = 1.4
LID_T = 1.4
CORNER_R = 4.0
SEAT_R = 44.0                              # seat radius on top of the pod rails (fit check)
SEAT_HALF_W = 19.0                         # curved seat |x| <= 19 mm; flat wings beyond
HOUSING_Y_OFFSET = 0.0                     # housing frame Y = band centre line
POD_HALF_L = 17.0                          # pods / strip edge at y = +/-17
TAIL_R1, TAIL_R2 = 1.5, 1.5                # tail bends: off the strip edge, into J2
TAIL_W, TAIL_T = 22.0, 0.3
BTN_HOLE_D = 2.4
# strap lugs (under the floor at the seat ends)
LUG_OUT = 4.5
STRAP_SLOT_W = 2.0
STRAP_SLOT_L = 21.0
LUG_L = 28.0
LUG_TOP = -1.65        # top of the lug bar; webbing passes over it below the floor
BAR_RELIEF = 0.5
SNAP_L, SNAP_R = 24.0, 0.35

# ---------------- derived ----------------
TAIL_RISER_Y = -POD_HALF_L - TAIL_R1
BOARD_Y0 = TAIL_RISER_Y + TAIL_R2 - J2_OPEN_Y_PCB - 0.3     # board distal edge (housing Y)
Z_FLOOR = FLOOR
Z_PCB = Z_FLOOR + UNDER_GAP
Z_PCB_TOP = Z_PCB + PCB_T
Z_BAT = Z_PCB_TOP + COMP_UNDER_CELL + CELL_FOAM
Z_TOP_BASE = Z_BAT + BAT_T + BAT_SWELL
Z_TOP = Z_TOP_BASE + LID_T
Z_TAIL = Z_PCB_TOP + J2_SLOT_DZ


def pcb_to_h(x, y):
    """KiCad (x right, y down, top view) -> housing (X, Y): 180 deg about Z."""
    return J2_X_PCB - x, BOARD_Y0 + y


X_MIN = pcb_to_h(PCB_L, 0)[0] - PCB_CLEAR - WALL
X_MAX = pcb_to_h(-ANT_OVERHANG, 0)[0] + ANT_CLEAR + WALL
Y_MIN = TAIL_RISER_Y - TAIL_T / 2 - 0.55 - WALL
Y_MAX = BOARD_Y0 + PCB_W + PCB_CLEAR + WALL
OUT_W, OUT_L = X_MAX - X_MIN, Y_MAX - Y_MIN
CX, CY = (X_MAX + X_MIN) / 2, (Y_MAX + Y_MIN) / 2
TAIL_Y = TAIL_RISER_Y


def seat_cyl(r):
    return Part.makeCylinder(r, 200, V(0, -100, -SEAT_R), V(0, 1, 0))


def seat_z(x):
    return math.sqrt(SEAT_R ** 2 - x * x) - SEAT_R


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def build_base():
    s = U.rrect(OUT_W, OUT_L, CORNER_R, Z_TOP_BASE, 0.0)
    s.translate(V(CX, CY, 0))
    # curved seat keel under the middle 38 mm, over the pods only (not over the tail bend)
    keel = box(-SEAT_HALF_W, SEAT_HALF_W, -POD_HALF_L, Y_MAX - 0.5, -8, 0.01).cut(seat_cyl(SEAT_R))
    s = s.fuse(keel)
    # strap lugs: bar under the floor at each seat end, ears at the strap-width ends
    for sx in (-1, 1):
        x0, x1 = sorted((sx * SEAT_HALF_W, sx * (SEAT_HALF_W + LUG_OUT)))
        lug = box(x0, x1, -LUG_L / 2, LUG_L / 2, -12, 0.01)
        lug = lug.cut(seat_cyl(SEAT_R + BAR_RELIEF))
        xs0, xs1 = sorted((sx * SEAT_HALF_W, sx * (SEAT_HALF_W + STRAP_SLOT_W)))
        lug = lug.cut(box(xs0, xs1, -STRAP_SLOT_L / 2, STRAP_SLOT_L / 2, -20, 0.0))
        xg0, xg1 = sorted((sx * SEAT_HALF_W, sx * (SEAT_HALF_W + LUG_OUT + 1)))
        lug = lug.cut(box(xg0, xg1, -STRAP_SLOT_L / 2, STRAP_SLOT_L / 2, LUG_TOP, 0.0))
        s = s.fuse(lug)
    s = s.removeSplitter()
    # cavity
    cav = U.rrect(OUT_W - 2 * WALL, OUT_L - 2 * WALL, 1.0, 30, Z_FLOOR)
    cav.translate(V(CX, CY, 0))
    s = s.cut(cav)
    # tail slot through the floor next to the distal wall
    s = s.cut(box(-TAIL_W / 2 - 0.6, TAIL_W / 2 + 0.6, TAIL_RISER_Y - 0.6, TAIL_RISER_Y + 0.6, -20, 5))
    # bosses: M2 nylon screws at H1/H2 (extend below the wing), plain bosses elsewhere
    for xp, yp in H_HOLES_PCB:
        x, y = pcb_to_h(xp, yp)
        b = Part.makeCylinder(2.6, Z_PCB + 3.0, V(x, y, -3.0)).cut(Part.makeCylinder(0.85, 6, V(x, y, Z_PCB - 4.8)))
        s = s.fuse(b).cut(Part.makeCylinder(0.85, 4.8, V(x, y, Z_PCB - 4.8)))
    for xp, yp in ((51.5, 2.0), (51.5, 32.0), (20.0, 2.0), (20.0, 32.0)):
        x, y = pcb_to_h(xp, yp)
        s = s.fuse(Part.makeCylinder(2.0, UNDER_GAP + 0.01, V(x, y, Z_FLOOR - 0.01)))
    # snap grooves for the lid lip on the two long (+/-Y) walls
    for sy in (-1, 1):
        yw = (Y_MAX - WALL) if sy > 0 else (Y_MIN + WALL - 0.4)
        s = s.cut(box(CX - SNAP_L / 2, CX + SNAP_L / 2, yw, yw + 0.4, Z_TOP_BASE - 1.6, Z_TOP_BASE - 0.7))
    return s.removeSplitter()


def build_lid():
    s = U.rrect(OUT_W, OUT_L, CORNER_R, LID_T, Z_TOP_BASE)
    s.translate(V(CX, CY, 0))
    try:
        top = [e for e in s.Edges if abs(e.BoundBox.ZMin - Z_TOP) < 1e-6 and abs(e.BoundBox.ZMax - Z_TOP) < 1e-6]
        s = s.makeFillet(1.0, top)
    except Exception:
        pass
    iw, il = OUT_W - 2 * WALL - 0.2, OUT_L - 2 * WALL - 0.2
    lip = U.rrect(iw, il, 0.9, 2.2 + 0.01, Z_TOP_BASE - 2.2).cut(U.rrect(iw - 1.8, il - 1.8, 0.1, 3, Z_TOP_BASE - 2.5))
    lip.translate(V(CX, CY, 0))
    s = s.fuse(lip)
    for sy in (-1, 1):
        y = (Y_MAX - WALL - 0.1) if sy > 0 else (Y_MIN + WALL + 0.1)
        s = s.fuse(Part.makeCylinder(SNAP_R, SNAP_L, V(CX - SNAP_L / 2, y, Z_TOP_BASE - 1.15), V(1, 0, 0)))
    # posts that clamp the J1-end corners of the board (H1/H2 end is screwed)
    for xp, yp in ((52.6, 1.4), (52.6, 32.6)):
        x, y = pcb_to_h(xp, yp)
        s = s.fuse(box(x - 1.2, x + 1.2, y - 1.2, y + 1.2, Z_PCB_TOP + 0.05, Z_TOP_BASE + 0.01))
    # BOOT button access (pin)
    x, y = pcb_to_h(*SW1_PCB)
    s = s.cut(Part.makeCylinder(BTN_HOLE_D / 2, 10, V(x, y, Z_TOP_BASE - 3)))
    return s.removeSplitter()


def board_shapes():
    """Real board from KiCad STEP, moved into the housing frame: (pcb, parts)."""
    p = os.path.join(U.MECH, BOARD_STEP)
    sh = Part.read(p)
    pcb, parts = [], []
    for so in sh.Solids:
        so = so.copy()
        # KiCad STEP: X = x, Y = -y, board bottom z = 0 -> rotate 180 deg about Z, translate
        so.rotate(V(0, 0, 0), V(0, 0, 1), 180)
        so.translate(V(J2_X_PCB, BOARD_Y0, Z_PCB))
        bb = so.BoundBox
        (pcb if (bb.ZMax - Z_PCB < PCB_T + 0.05 and bb.XLength > 40) else parts).append(so)
    return Part.makeCompound(pcb), Part.makeCompound(parts)


def build_internals(real_board=True):
    out = {}
    if real_board and os.path.exists(os.path.join(U.MECH, BOARD_STEP)):
        pcb, parts = board_shapes()
        out['main_board'] = (pcb, U.C_PCB)
        out['board_parts'] = (parts, U.C_METAL)
    xa, ya = pcb_to_h(BAT_PCB[0] + BAT_X, BAT_PCB[1])
    out['lipo'] = (box(xa, xa + BAT_X, ya, ya + BAT_Y, Z_BAT, Z_BAT + BAT_T), U.C_LIPO)
    return out


def tail_shape(z_flex):
    """Installed tail (wrist frame of the housing): leaves the strip edge at y = -17 heading -Y,
    bends up (R1), rises, bends toward +Y (R2) and runs into J2. Returns (shape, length)."""
    t, w = TAIL_T, TAIL_W
    def arc(cy, cz, r, a0, a1):
        ring = Part.makeCylinder(r + t / 2, w, V(-w / 2, cy, cz), V(1, 0, 0)).cut(
            Part.makeCylinder(r - t / 2, w, V(-w / 2, cy, cz), V(1, 0, 0)))
        # keep the quadrant between angles a0..a1 (deg, in the YZ plane from +Y toward +Z)
        L = r + t + 1
        wedge = Part.makePolygon([V(-w / 2, cy, cz)] + [V(-w / 2, cy + L * 1.5 * math.cos(math.radians(a)), cz + L * 1.5 * math.sin(math.radians(a)))
                                                       for a in (a0, (a0 + a1) / 2, a1)] + [V(-w / 2, cy, cz)])
        wedge = Part.Face(wedge).extrude(V(w, 0, 0))
        return ring.common(wedge)
    y0 = -POD_HALF_L
    z_up0 = z_flex + TAIL_R1
    z_up1 = Z_TAIL - TAIL_R2
    y_j2 = BOARD_Y0 + J2_OPEN_Y_PCB + 3.5
    parts = [arc(y0, z_up0, TAIL_R1, 180, 270),
             box(-w / 2, w / 2, TAIL_RISER_Y - t / 2, TAIL_RISER_Y + t / 2, z_up0, z_up1),
             arc(TAIL_RISER_Y + TAIL_R2, z_up1, TAIL_R2, 90, 180),
             box(-w / 2, w / 2, TAIL_RISER_Y + TAIL_R2, y_j2, Z_TAIL - t / 2, Z_TAIL + t / 2)]
    length = math.pi / 2 * (TAIL_R1 + TAIL_R2) + (z_up1 - z_up0) + (y_j2 - TAIL_RISER_Y - TAIL_R2)
    return parts[0].fuse(parts[1:]).removeSplitter(), length


if not getattr(sys, 'neurband_lib', False):
    log = U.Log('housing')
    base = U.check(build_base(), 'housing_base', log)
    lid = U.check(build_lid(), 'housing_lid', log)
    inner = build_internals()
    log(f"  outer {OUT_W:.1f} (X, across the wrist, x {X_MIN:.1f}..{X_MAX:.1f}) x {OUT_L:.1f} (Y, {Y_MIN:.1f}..{Y_MAX:.1f}) mm; "
        f"lugs at x = +/-{SEAT_HALF_W + LUG_OUT:.1f}; height above seat apex {Z_TOP:.1f} mm")
    log(f"  z: floor {Z_FLOOR}, pcb {Z_PCB:.2f}-{Z_PCB_TOP:.2f}, cell {Z_BAT:.2f}-{Z_BAT + BAT_T:.2f} (+{BAT_SWELL} swell), lid {Z_TOP_BASE:.2f}-{Z_TOP:.2f}")
    xa, _ = pcb_to_h(BAT_PCB[0], 0)
    log(f"  cell to antenna edge (KiCad x = 0): {BAT_PCB[0]:.1f} mm; board distal edge y = {BOARD_Y0:.2f}")
    for name, (sh, _) in inner.items():
        log(f"  {name} clash base={sh.common(base).Volume:.3f} lid={sh.common(lid).Volume:.3f} mm3")
    if 'board_parts' in inner:
        bat = inner['lipo'][0]
        log(f"  lipo vs board parts {bat.common(inner['board_parts'][0]).Volume:.3f} mm3; "
            f"tallest part top z {inner['board_parts'][0].BoundBox.ZMax:.2f}")
    U.save('housing_base', [('housing_base', base, U.C_PA12_BLACK)], log)
    U.save('housing_lid', [('housing_lid', lid, U.C_PA12_BLACK)], log)
    U.save('housing_assy', [('housing_base', base, U.C_PA12_BLACK), ('housing_lid', lid, U.C_PA12_BLACK)] +
           [(k, v[0], v[1]) for k, v in inner.items()], log)
    U.fab('housing_base', 'Module housing base', base, 2, 'mjf', 'pa12', 'black', log)
    U.fab('housing_lid', 'Module housing lid', lid, 2, 'mjf', 'pa12', 'black', log)
    U.finish(log)
