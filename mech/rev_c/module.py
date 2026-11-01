"""module.py - rev C electronics module, r2: slim tapered pebble = base (chassis with two integral
strap bars) + crowned lid (cosmetic shell), for the re-placed main board (boards/neurband_c, Nov 2026).

Module frame: X across the wrist (radial / button side +, ulnar / antenna side -), Y along the arm
(distal = J1 end = -Y), Z up; origin = apex of the curved underside on the band centre line.
- Underside: cylinder R_U (axis along Y) hugging the dorsal wrist. It carries flex pods 3 and 4
  (tail between them at x = 0): foam pockets behind their pads, like pod.py, and the root dot.
- Outside: three profiles intersected (no fragile lofts): across the wrist, vertical lower sides up to
  Z_TC, then sides that lean in (SIDE_TAPER) with a large shoulder blend (R_SH) into a shallow crown
  (R_T) whose apex height H_TOP is solved from the cell clearance; the ends along the arm are vertical
  with a soft top blend (R_SHY); plan corners R3.8.
- Board (exported fresh from the KiCad file into mech/rev_c/ref/neurband_c_parts.step) rests on
  solid ledges along its X edges; J1 (front-flip FPC) on the distal edge, the flex tail U-turns up
  the distal wall through a floor slot.
- Battery pads J2 (board bottom, KiCad (26.8 / 23.8, 18.8)): the leads cross the board to its +X
  edge, pass it in the 0.6 mm gap to the wall (LEAD_CH) and run back under the board (relief).
- Charging: J3 (board bottom, KiCad (23.9 / 26.9, 25.4)) is wired along the +X ledge (J3_CH) to a
  2-pin magnetic connector (bought) glued into a bay in the proximal wall (mag_pocket, bay_block):
  boss in a 2.0 mm wall window, face flush; its pins reach under the cell's overhang.
- SWD pads TP1-TP5 (board bottom, -X proximal corner): flashed once with soldered wires; a shallow
  relief in the -X ledge clears leftover solder.
- Strap: each X end of the base carries a thick integral bar (bar_profile: trapezoid 4.6 x 7.2 with
  R1.2 edges) outboard of a slot that leans out SLOT_TILT at the top and starts under the body's
  lower edge (slot A 4.4 mm for the pinch lock, slot B 3.5 mm for the hook end); see strap.py for the
  strap and the strength log.
- Lid: crowned top, light hole over D1 and opening for the button cap over SW1 (both on the sloped
  shoulder, drilled along the shell's normal so no rim is a knife edge), four square snap ribs on
  the +/-Y walls, pry notch in its edge above the connector bay (no parting groove: it would thin the 1.0 mm walls).
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/module.py
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import rc as R
import cadutil as U

V = FreeCAD.Vector

# ---------------- outside (mm) ----------------
OUT_W = 31.6              # across the wrist at the parting: board 28.7 + 0.3 (-X) / 0.6 (+X, cell leads) + 2 x 1.0 walls
CX_OFF = 0.5              # body centre X (board -14..14.7; +X gap wider for the cell leads)
Y_MIN, Y_MAX = -17.45, 19.6   # along the arm (distal end: tail U-turn; proximal end: magnetic connector bay)
PLAN_R_D, PLAN_R_P = 3.8, 3.8  # plan corner radii, distal / proximal
R_U = 42.0                # underside radius (dorsal wrist 33-42 mm on 145-180 wrists)
R_T = 110.0               # top crown radius across the wrist
H_TOP = None              # top apex above the underside apex: computed from the cell clearance (below)
SIDE_TAPER = 3.4          # the X sides lean in this much from Z_TC to the crown
Z_TC = 4.0                # the X sides are vertical up to about here (board edge + cell leads clear the wall)
R_SH, R_TS = 5.5, 4.5     # shoulder blend (side -> crown), taper-start blend (vertical -> leaning side)
Z_SY, R_SHY = 4.6, 2.6    # Y ends: vertical up to here, then a blend R_SHY into the crown (above the connector bay's top)
WALL = 1.0
FLOOR = 1.0
LID_T = 1.0
BOT_FILLET = 1.2
H_BASE = 2.0              # parting surface: constant height above the underside (ucyl(R_U + H_BASE));
                          # the X end walls of the base rise to the board top (they carry the bars)
GROOVE_H, GROOVE_D = 0.3, 0.12   # (parting hairline groove: not applied in r2, it took the 1.0 mm walls to 0.88)
TONGUE_T, TONGUE_H = 1.4, 1.5     # tongue zone 1.4 deep inside the lid wall (1.3 of plastic + TONGUE_CLR)
TONGUE_CLR = 0.1
TAIL_CUT = 7.5                    # tongue cut back over the tail U-turn and J1 (J1 is 14.4 wide)
# ---------------- board ----------------
BOARD_STEP = os.path.join(R.HERE, 'ref', 'neurband_c_parts.step')   # kicad-cli pcb export step (fresh, with parts)
PCB_W, PCB_L, PCB_T = 28.7, 27.0, 1.0
J1_KX = 14.0                                   # KiCad x of J1 = module X 0 (tail, dorsal centre)
Y_B0 = -R.POD_L / 2 + 0.2                      # board distal edge (J1 mouth flush with it)
Z_PCB = 1.75                                   # board bottom: 0.15 over the root-dot boss (top 1.6)
Z_PCB_TOP = Z_PCB + PCB_T
TAIL_R = 1.0
J1_W, J1_D, J1_H = 14.4, 5.12, 2.08
J1_X = 0.0
J1_SLOT_DZ = 0.5
SW1_K = (24.8, 25.1)                           # KiCad (x, y), neurband_c.kicad_pcb (Nov 2026)
D1_K = (2.0, 1.0)
J2_K = ((26.8, 18.8), (23.8, 18.8))            # VBAT, GND (bottom), 1.5 x 2.0 pads
J3_K = ((23.9, 25.4), (26.9, 25.4))            # VCHG 5 V, GND (bottom)
TP_K = ((1.1, 5.1), (2.0, 4.2), (2.9, 3.3), (3.79, 2.41), (4.69, 1.51))   # TP1..TP5 (bottom)
SW1_H = 2.08


def k2m(x, y):
    """KiCad top view (x right, y down) -> module (X, Y): board distal edge (KiCad y = PCB_L) at Y_B0."""
    return x - J1_KX, Y_B0 + PCB_L - y


SW1 = k2m(*SW1_K)
D1 = k2m(*D1_K)
ANT_X = (-14.0, -7.75)                         # antenna strip (KiCad x 0..6.25), plastic only
# ---------------- battery ----------------
BAT_W, BAT_L, BAT_T = 12.0, 25.0, 4.0          # 401223 class incl. protection board
BAT_X0 = -3.5                                  # KiCad x 10.5..22.5
BAT_Y0 = k2m(0, 21.73)[1]                      # lead end at KiCad y 21.73 (just proximal of J1)
COMP_UNDER_BAT = 1.2                           # TQFP-64 top 1.19 above the board (fresh STEP)
CELL_POCKET = (12.4, 25.5, 4.2)
CELL_X0 = BAT_X0 - (CELL_POCKET[0] - BAT_W) / 2
BAT_TAPE = 0.1
BAT_SWELL = 0.3
CELL_CLR = 0.1                                 # lid inner surface over the swollen cell
# ---------------- lid features ----------------
LP_D, LP_TUBE = 1.6, 3.6
BTN_HOLE_D, BTN_GAP_R = 4.6, 0.15
BTN_FLANGE_D, BTN_FLANGE_T = 6.0, 1.0
BTN_STEM_D, BTN_GAP = 2.0, 0.15
NOTCH_W, NOTCH_H = 3.5, 0.8
# ---------------- underside features ----------------
MODULE_EXTRA = R.FOAM_POCKET_H - R.MODULE_POCKET_H
MODULE_POCKET_D = R.FOAM_D + 0.2
ROOT_DOT = (0.0, -10.4)
TAIL_SLOT = (R.TAIL_W + 0.7, 1.8)
LEDGE_X = 12.0                                 # |x - CX_OFF| from here out the base is solid up to the board (ledges)
# ---------------- strap bars (integral, one per X end; strap.py has the strap and the strength log) ----------
SLOT_L = R.STRAP_W + 0.8                       # slot length along the arm (20 mm strap +/-0.5); shorter span = stronger bar
SLOT_GAP = R.SLOT_GAP                          # (end A) slot width across the wrist


def slot_gap(sx):
    return R.SLOT_GAP_A if sx < 0 else R.SLOT_GAP_B


ARM_T = 3.6                                    # lug arms either side of the slot (along Y); strap.py checks them
LUG_HW = SLOT_L / 2 + ARM_T
SLOT_TILT = 20.0                               # deg: the slots lean out at the top; they start under the body's lower edge
SLOT_U0, SLOT_Z0 = -1.4, -4.2                  # slot inner face at the bottom: 1.4 mm inside the end face, at z -4.2
BAR_ZB, BAR_ZT = -4.2, 3.0                     # bar bottom / top (at its inner face)
BAR_W = 4.6                                    # bar underside length (outboard of the slot)
BAR_BETA = 0.0                                 # deg: underside slope (0 = flat: the band leaves the lower inner corner below it)
BAR_LEAN = 10.0
BAR_R = 1.2                                    # rounding of the lug / bar edges (2D profile)
BAR_TOP_DROP = 1.8                             # the bar's top falls this much outward (soft, sloped lug top)
LUG_PLAN_R = 4.5                               # plan rounding of the lug's outer corners
BAR_TILT = SLOT_TILT                           # (kept for the logs)
BAR_U, BAR_V = BAR_W, BAR_ZT - BAR_ZB          # nominal bar section size (logs)
LUG_TOP0 = Z_PCB_TOP - 0.05                    # lug top where it leaves the end wall (at the lid edge)
# ---------------- magnetic charge connector (bought; device side glued into the distal wall) ----------------
MAG_X = CX_OFF                                 # centred on the proximal face
MAG_Z0 = 1.35                                  # connector bottom: the pocket keeps 1.0 of floor on the centre line; top MAG_Z0 + 4.0 is below the
                                               # cell's bottom where its pins reach under the cell's overhang
MAG_CLR = 0.15
BAY_Z = 6.55                                   # the base rises to here around the connector (1.0 over it; lid edge above)
BAY_HW = R.MAG_FLANGE[0] / 2 + MAG_CLR + 1.0   # bay block half width (X)
J2_RELIEF = ((22.6, 28.7), (17.1, 20.8))       # KiCad x, y under the J2 pads (wire joints): 1.0 deep in the ledge
J3_RELIEF = ((22.8, 27.8), (24.0, 27.0))       # under the J3 pads (wires to the magnetic connector); clear of the corner tongue
J3_CH = ((26.3, 27.6), 1.0)                    # J3 wire channel under the board's +X edge (KiCad x), depth below the board
TP_RELIEF = ((0.0, 5.6), (0.6, 6.0))           # SWD pads: leftover solder after the one-time flash
LEAD_CH = ((-8.6, -5.0), 0.75)                 # cell-lead route: module Y range where the leads pass the board's +X edge

YC = (Y_MIN + Y_MAX) / 2


def end_x(sx):
    return CX_OFF + sx * OUT_W / 2


OUT_L = Y_MAX - Y_MIN
Y_B1 = Y_B0 + PCB_L
POD_TH = 9.0 / R_U
Z_BAT = Z_PCB_TOP + COMP_UNDER_BAT + BAT_TAPE


def z_u(x):
    return math.sqrt(R_U ** 2 - x * x) - R_U


def ucyl(r):
    """Cylinder about the underside axis (0, -R_U), radius r."""
    return R.cyl_y(r, 0.0, -R_U)


def _crown_drop(dx, r):
    return r - math.sqrt(r * r - dx * dx)


def solve_h_top():
    """Lowest top apex that keeps the lid's inner surface CELL_CLR over the swollen cell (middle) and
    over the cell's rounded long edges."""
    need = 0.0
    ri = R_T - LID_T
    for x, z in ((BAT_X0 + 2.0, Z_BAT + BAT_T + BAT_SWELL), (BAT_X0 + BAT_W - 2.0, Z_BAT + BAT_T + BAT_SWELL),
                 (BAT_X0 + 0.6, Z_BAT + BAT_T), (BAT_X0 + BAT_W - 0.6, Z_BAT + BAT_T)):
        need = max(need, z + CELL_CLR + LID_T + _crown_drop(x - CX_OFF, ri))
    return math.ceil(need * 20) / 20


H_TOP = solve_h_top()


def z_top(x):
    return H_TOP - _crown_drop(x - CX_OFF, R_T)


# ---------------- outside shape ----------------
def _prof_xz(log=None):
    """Cross-section across the wrist (XZ), extruded along Y: vertical lower sides, leaning upper
    sides with big blends, crown on top."""
    B, c = OUT_W / 2, CX_OFF
    xi = B - SIDE_TAPER
    zt = H_TOP - _crown_drop(xi, R_T)
    y0 = -60.0
    P = lambda x, z: V(x, y0, z)
    arc = Part.Arc(P(c + xi, zt), P(c, H_TOP), P(c - xi, zt)).toShape()
    w = Part.Wire([Part.makeLine(P(c - B, -20), P(c + B, -20)), Part.makeLine(P(c + B, -20), P(c + B, Z_TC)),
                   Part.makeLine(P(c + B, Z_TC), P(c + xi, zt)), arc,
                   Part.makeLine(P(c - xi, zt), P(c - B, Z_TC)), Part.makeLine(P(c - B, Z_TC), P(c - B, -20))])
    s = Part.Face(w).extrude(V(0, 120, 0))
    s = s.makeFillet(R_SH, [e for e in s.Edges if e.BoundBox.YLength > 100 and e.BoundBox.ZMin > Z_TC + 0.5])
    s = s.makeFillet(R_TS, [e for e in s.Edges if e.BoundBox.YLength > 100 and abs(e.BoundBox.ZMin - Z_TC) < 0.02
                            and e.BoundBox.ZLength < 0.01])
    return s


def _prof_yz():
    """Section along the arm (YZ), extruded along X: near-vertical ends, soft top blend; its top is
    above the crown, so the crown alone shapes the top."""
    x0 = -60.0
    P = lambda y, z: V(x0, y, z)
    zt = H_TOP + 3.0
    w = Part.Wire(Part.makePolygon([P(Y_MIN, -20), P(Y_MAX, -20), P(Y_MAX, zt), P(Y_MIN, zt), P(Y_MIN, -20)]))
    s = Part.Face(w).extrude(V(120, 0, 0))
    return s


def _plan_face(inset=0.0):
    """Plan outline (rounded rectangle, distal / proximal corner radii), z = 0 plane."""
    x0, x1 = CX_OFF - OUT_W / 2 + inset, CX_OFF + OUT_W / 2 - inset
    y0, y1 = Y_MIN + inset, Y_MAX - inset
    rd, rp = PLAN_R_D - inset, PLAN_R_P - inset
    e = [Part.makeLine(V(x0 + rd, y0, 0), V(x1 - rd, y0, 0)),
         Part.Arc(V(x1 - rd, y0, 0), V(x1 - rd + rd * math.sin(math.pi / 4), y0 + rd - rd * math.cos(math.pi / 4), 0), V(x1, y0 + rd, 0)).toShape(),
         Part.makeLine(V(x1, y0 + rd, 0), V(x1, y1 - rp, 0)),
         Part.Arc(V(x1, y1 - rp, 0), V(x1 - rp + rp * math.cos(math.pi / 4), y1 - rp + rp * math.sin(math.pi / 4), 0), V(x1 - rp, y1, 0)).toShape(),
         Part.makeLine(V(x1 - rp, y1, 0), V(x0 + rp, y1, 0)),
         Part.Arc(V(x0 + rp, y1, 0), V(x0 + rp - rp * math.cos(math.pi / 4), y1 - rp + rp * math.sin(math.pi / 4), 0), V(x0, y1 - rp, 0)).toShape(),
         Part.makeLine(V(x0, y1 - rp, 0), V(x0, y0 + rd, 0)),
         Part.Arc(V(x0, y0 + rd, 0), V(x0 + rd - rd * math.cos(math.pi / 4), y0 + rd - rd * math.sin(math.pi / 4), 0), V(x0 + rd, y0, 0)).toShape()]
    return Part.Face(Part.Wire(e))


def _plan(inset=0.0, z0=-20.0, h=60.0):
    f = _plan_face(inset)
    f.translate(V(0, 0, z0))
    return f.extrude(V(0, 0, h))


def _section_offset(solid, normal, d, extrude):
    """Inner version of a profile extrusion: slice at the origin plane, 2D offset by -d, extrude."""
    sl = solid.slice(normal, 0.0)
    f = Part.Face(Part.Wire(sl[0].Edges) if len(sl) == 1 else sl[0])
    fo = f.makeOffset2D(-d)
    return fo.extrude(extrude)


_CACHE = {}


def profiles():
    if 'p' not in _CACHE:
        xz = _prof_xz()
        yz = _prof_yz()
        xz_in = _section_offset(xz, V(0, 1, 0), WALL, V(0, 120, 0))
        xz_in.translate(V(0, -60, 0))
        xz_in2 = _section_offset(xz, V(0, 1, 0), LID_T, V(0, 120, 0))
        xz_in2.translate(V(0, -60, 0))
        _CACHE['p'] = (xz, yz, xz_in)
    return _CACHE['p']


def body(log=None):
    """Outside of the module (base + lid together, no lugs)."""
    if 'body' in _CACHE:
        return _CACHE['body']
    xz, yz, _ = profiles()
    s = xz.common(yz).common(_plan()).cut(ucyl(R_U))
    # soft Y-end top edges (the crown meets the end walls) and the plan corners above the board
    s = R.fillet_edges(s, R_SHY, lambda e: e.BoundBox.ZMin > Z_SY - 0.5 and (abs(e.BoundBox.YMin - Y_MIN) < 0.3 and abs(e.BoundBox.YMax - Y_MIN) < 0.3
                                                                          or abs(e.BoundBox.YMin - Y_MAX) < 0.3 and abs(e.BoundBox.YMax - Y_MAX) < 0.3), log, 'Y-end top')
    s = R.fillet_edges(s, BOT_FILLET, lambda e: e.BoundBox.ZMax < 0.5 and e.BoundBox.ZMax - e.BoundBox.ZMin < 4.0
                       and abs(e.BoundBox.YMin - Y_MIN) > 0.5 and abs(e.BoundBox.YMax - Y_MAX) > 0.5
                       and (abs(abs(e.BoundBox.XMax - CX_OFF) - OUT_W / 2) < 0.5 or abs(abs(e.BoundBox.XMin - CX_OFF) - OUT_W / 2) < 0.5),
                       log, 'bottom')
    _CACHE['body'] = s
    return s


def cavity_raw():
    """Inside of the shell: the outside profiles offset inward by WALL / LID_T, above the floor."""
    if 'cav' in _CACHE:
        return _CACHE['cav']
    xz, yz, xz_in = profiles()
    yz_in = R.box(-60, 60, Y_MIN + WALL, Y_MAX - WALL, -20, H_TOP + 2)
    c = xz_in.common(yz_in).common(_plan(WALL)).cut(ucyl(R_U + FLOOR))
    # soft inner Y-end top edges (follow the outside blend, LID_T inside it)
    c = R.fillet_edges(c, max(R_SHY - LID_T, 0.5), lambda e: e.BoundBox.ZMin > Z_SY - 1.5 and (
        abs(e.BoundBox.YMin - (Y_MIN + WALL)) < 0.3 and abs(e.BoundBox.YMax - (Y_MIN + WALL)) < 0.3
        or abs(e.BoundBox.YMin - (Y_MAX - WALL)) < 0.3 and abs(e.BoundBox.YMax - (Y_MAX - WALL)) < 0.3))
    _CACHE['cav'] = c
    return c


def cavity(log=None):
    return cavity_raw()


def plan_ring(o0, o1, z0=-20.0, h=60.0):
    """Band between the plan outline inset o0 and inset o1 (o1 > o0)."""
    return _plan(o0, z0, h).cut(_plan(o1, z0 - 1, h + 2))


def pod_place(sign):
    """Placement of a pod-local frame on the underside at arc sign*9 mm."""
    th = sign * POD_TH
    return FreeCAD.Placement(V(R_U * math.sin(th), 0, R_U * math.cos(th) - R_U),
                             FreeCAD.Rotation(V(0, 1, 0), math.degrees(th)))


def stadium_xz(cx, cz, u, v, tilt_deg, y0, y1):
    """Stadium (u across, v long, long axis tilted tilt_deg from +Z toward +X) extruded along Y."""
    r = u / 2
    L = v - u
    s = R.box(-r, r, y0, y1, -L / 2, L / 2)
    for sz in (-1, 1):
        s = s.fuse(Part.makeCylinder(r, y1 - y0, V(0, y0, sz * L / 2), V(0, 1, 0)))
    s = s.removeSplitter()
    s.rotate(V(0, 0, 0), V(0, 1, 0), tilt_deg)
    s.translate(V(cx, 0, cz))
    return s


def u_in(sx, z):
    """Slot inner face, outboard distance from the end face (u) at height z."""
    return SLOT_U0 + (z - SLOT_Z0) * math.tan(math.radians(SLOT_TILT))


def u_out(sx, z):
    return u_in(sx, z) + slot_gap(sx) / math.cos(math.radians(SLOT_TILT))


def x_of(sx, u):
    return end_x(sx) + sx * u


def bar_profile(sx):
    """Bar section outboard of the slot as (u, z) points, in order lower-inner, lower-outer, upper-outer,
    upper-inner: inner face = slot outer face (leans out SLOT_TILT), underside rising outward BAR_BETA,
    outer face leaning out BAR_LEAN, top flat."""
    b = math.radians(BAR_BETA)
    li = (u_out(sx, BAR_ZB), BAR_ZB)
    lo = (li[0] + BAR_W * math.cos(b), BAR_ZB + BAR_W * math.sin(b))
    zt = BAR_ZT - BAR_TOP_DROP
    uo = (lo[0] + (zt - lo[1]) * math.tan(math.radians(BAR_LEAN)), zt)
    zt = BAR_ZT
    ui = (u_out(sx, zt), zt)
    return [li, lo, uo, ui]


def bar_center(sx):
    pts = bar_profile(sx)
    uc = sum(p[0] for p in pts) / 4
    zc = sum(p[1] for p in pts) / 4
    return x_of(sx, uc), zc


def bar_x(sx):
    return bar_center(sx)[0]


BAR_Z = (BAR_ZB + BAR_ZT) / 2


def bar_geom(sx):
    """Bar corners (x, z) as the fit model uses them: li (lower inner: where the band bends), lo, uo, ui,
    their rounding centres (BAR_R inside each corner), and the outward normal angle (deg) of each face."""
    pts = bar_profile(sx)
    X = [(x_of(sx, u), z) for u, z in pts]
    n = len(X)
    cen = []
    for k in range(n):
        p0, p1, p2 = X[k - 1], X[k], X[(k + 1) % n]
        a = (p0[0] - p1[0], p0[1] - p1[1]); la = math.hypot(*a); a = (a[0] / la, a[1] / la)
        c = (p2[0] - p1[0], p2[1] - p1[1]); lc = math.hypot(*c); c = (c[0] / lc, c[1] / lc)
        bis = (a[0] + c[0], a[1] + c[1]); lb = math.hypot(*bis); bis = (bis[0] / lb, bis[1] / lb)
        half = math.acos(max(-1.0, min(1.0, a[0] * c[0] + a[1] * c[1]))) / 2
        d = BAR_R / math.sin(half)
        cen.append((p1[0] + bis[0] * d, p1[1] + bis[1] * d))
    normals = []
    for k in range(n):                                   # face k from X[k] to X[k+1]; outward = away from the centroid
        p1, p2 = X[k], X[(k + 1) % n]
        tx, tz = p2[0] - p1[0], p2[1] - p1[1]
        nx, nz = tz, -tx
        cx = sum(q[0] for q in X) / n; cz = sum(q[1] for q in X) / n
        mx, mz = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        if nx * (mx - cx) + nz * (mz - cz) < 0:
            nx, nz = -nx, -nz
        normals.append(math.degrees(math.atan2(nz, nx)))
    return dict(c=bar_center(sx), li=X[0], lo=X[1], uo=X[2], ui=X[3], r=BAR_R, cen=dict(li=cen[0], lo=cen[1], uo=cen[2], ui=cen[3]),
                n_bottom=normals[0], n_outer=normals[1], n_top=normals[2], n_slot=normals[3], top=X[3], bot=X[0], tilt=SLOT_TILT, u=(0, 1))


def _xz_face(pts_xz, y0):
    poly = [V(x, y0, z) for x, z in pts_xz] + [V(pts_xz[0][0], y0, pts_xz[0][1])]
    return Part.Face(Part.makePolygon(poly))


def _round2d(face, r):
    """Round convex and concave corners of a planar face by r (offset out, in, out)."""
    try:
        f = face.makeOffset2D(-r).makeOffset2D(2 * r).makeOffset2D(-r)
        return f if f.isValid() and f.Area > 0.5 * face.Area else face
    except Exception:
        return face


def lug(sx, log=None):
    """Integral strap lug at one X end: a web from the base's solid end (below the board) and end wall,
    out to a thick trapezoid bar; the tilted slot is cut afterwards (slot_void). Edges rounded BAR_R."""
    xe = end_x(sx)
    bp = bar_profile(sx)
    (ub0, zb0), (uo0, zo0), (uo1, zo1), (ui1, zi1) = bp
    ui = -(OUT_W / 2 - LEDGE_X)                       # inside the body: the ledge (solid below the board)
    zb_end = z_u(OUT_W / 2) + 0.2
    pts_u = [(ui, z_u(OUT_W / 2 + ui) + 0.3), (ui, Z_PCB - 0.3), (-WALL, Z_PCB - 0.3), (-WALL, LUG_TOP0),
             (0.15, LUG_TOP0), (ui1, zi1), (uo1, zo1), (uo0, zo0), (ub0, zb0), (0.0, zb0), (0.0, zb_end)]
    f = _xz_face([(x_of(sx, u), z) for u, z in pts_u], -LUG_HW)
    f = _round2d(f, BAR_R)
    l = f.extrude(V(0, 2 * LUG_HW, 0))
    # plan: round the outer corners of the lug (R2.5)
    xo = x_of(sx, uo1 + 1.0)
    xa, xb = sorted((x_of(sx, ui - 1.0), xo))
    pl = U.rrect(xb - xa, 2 * LUG_HW, LUG_PLAN_R, 40, -20)
    pl.translate(V((xa + xb) / 2, 0, 0))
    return l.common(pl)


def slot_void(sx):
    """Tilted through slot between the end and the bar, SLOT_L along the arm (it nicks the body's
    lower outer edge, below the board)."""
    z0, z1 = -12.0, 12.0
    pts = [(x_of(sx, u_in(sx, z0)), z0), (x_of(sx, u_out(sx, z0)), z0), (x_of(sx, u_out(sx, z1)), z1), (x_of(sx, u_in(sx, z1)), z1)]
    f = _xz_face(pts, -SLOT_L / 2)
    return f.extrude(V(0, SLOT_L, 0))


def lug_shapes(log=None):
    if 'lugs' not in _CACHE:
        out = []
        for sx in (-1, 1):
            l = lug(sx, log)
            l = l.cut(slot_void(sx))
            out.append(l)
        _CACHE['lugs'] = out
    return _CACHE['lugs']


def mag_geom():
    """Connector solids in module coords: boss (in the proximal wall, face flush with the outside),
    flange (behind the wall), pins (toward the board, under the cell's overhang)."""
    bw, bd, bh = R.MAG_BOSS
    fw, fd, fh = R.MAG_FLANGE
    zc = MAG_Z0 + bh / 2
    boss = R.box(MAG_X - bw / 2, MAG_X + bw / 2, Y_MAX - bd, Y_MAX, zc - bh / 2, zc + bh / 2)
    flange = R.box(MAG_X - fw / 2, MAG_X + fw / 2, Y_MAX - bd - fd, Y_MAX - bd, zc - fh / 2, zc + fh / 2)
    pins = [Part.makeCylinder(0.35, R.MAG_PIN_L, V(MAG_X + sx * R.MAG_PITCH / 2, Y_MAX - bd - fd, zc), V(0, -1, 0)) for sx in (-1, 1)]
    return boss, flange, pins, zc


def mag_pocket():
    """Pocket for the connector: boss window through the 2.0 mm wall, flange recess behind it, pin and
    wire space toward the board."""
    boss, flange, pins, zc = mag_geom()
    c = MAG_CLR
    bb, fb = boss.BoundBox, flange.BoundBox
    p = R.box(bb.XMin - c, bb.XMax + c, bb.YMin - 0.01, Y_MAX + 1, bb.ZMin - c, bb.ZMax + c)
    p = p.fuse(R.box(fb.XMin - c, fb.XMax + c, fb.YMin - 0.3, fb.YMax + 0.01, fb.ZMin - c, fb.ZMax + c))
    p = p.fuse(R.box(MAG_X - 3.0, MAG_X + 3.0, Y_B1 + 0.2, fb.YMin, fb.ZMin - c, fb.ZMax + c))   # pins + solder joints
    return p.removeSplitter()


def bay_block():
    """Base material around the connector: rises to BAY_Z at the proximal end, beyond the cell's end
    (the lid's edge sits on it)."""
    return R.box(MAG_X - BAY_HW, MAG_X + BAY_HW, BAT_Y0 + BAT_L + 0.1, Y_MAX + 1, -20, BAY_Z)


def mag_body():
    boss, flange, pins, zc = mag_geom()
    return boss.fuse([flange] + pins).removeSplitter()


def mag_contacts():
    zc = MAG_Z0 + R.MAG_BOSS[2] / 2
    out = []
    for sx in (-1, 1):
        out.append(Part.makeCylinder(R.MAG_PAD_D / 2, 0.05, V(MAG_X + sx * R.MAG_PITCH / 2, Y_MAX, zc), V(0, 1, 0)))
    for sx in (-1, 1):
        out.append(Part.makeCylinder(1.4, 0.05, V(MAG_X + sx * R.MAG_MAG_C / 2, Y_MAX, zc), V(0, 1, 0)))
    return out


END_X = OUT_W / 2 - PLAN_R_D                    # |x - CX_OFF| from which the base's walls rise to the board top (X ends and corners)


def end_walls():
    """Zones of the base that rise to the board top: both X ends including the plan corners (outboard of
    the corner tangents). The lid reaches down to the curved parting only along the straight Y walls,
    so every base / lid split is a planar cut through a straight wall."""
    out = []
    for sx in (-1, 1):
        xa, xb = sorted((CX_OFF + sx * END_X, CX_OFF + sx * (OUT_W / 2 + 1)))
        out.append(R.box(xa, xb, Y_MIN - 1, Y_MAX + 1, -20, Z_PCB_TOP))
    return out


def build_base(log=None):
    full = body(log)
    # base = body below the parting cylinder, plus the X end zones up to the board top
    ends = end_walls()
    keep = ucyl(R_U + H_BASE).fuse(ends + [bay_block()]).removeSplitter()
    b = full.common(keep)
    # square bottom edge along the straight part of both Y walls: the bottom blend propagates round the
    # whole tangent-continuous loop, which would thin the distal wall behind the tail slot and the
    # proximal wall under the connector window below 1.0 mm
    fills = []
    for ya, yb in ((Y_MIN, Y_MIN + WALL), (Y_MAX - WALL, Y_MAX)):
        fills.append(R.box(CX_OFF - OUT_W / 2 + PLAN_R_D, CX_OFF + OUT_W / 2 - PLAN_R_D, ya, yb, -10, H_BASE + 0.5)
                     .common(_plan()).common(ucyl(R_U + H_BASE)).cut(ucyl(R_U)))
    b = b.fuse(fills).removeSplitter()
    cav = cavity_raw()
    # ledges: the cavity stops LEDGE_X from the centre below the board (solid ends carry the board and the lugs)
    ledge_cut = R.box(CX_OFF - LEDGE_X, CX_OFF + LEDGE_X, Y_MIN - 1, Y_MAX + 1, -20, 30).fuse(
        R.box(-60, 60, Y_MIN - 1, Y_MAX + 1, Z_PCB, 30))
    b = b.cut(cav.common(ledge_cut).cut(bay_block()))
    b = b.removeSplitter()
    # bosses inside the floor behind the pod 3/4 foam pockets: >= 1.0 mm behind each pocket
    for sgn in (-1, 1):
        pl = pod_place(sgn)
        for y in R.PAD_Y:
            bo = Part.makeCylinder(MODULE_POCKET_D / 2 + 0.6, R.MODULE_POCKET_H + 0.7, V(0, y, 0.3))
            bo.Placement = pl.multiply(bo.Placement)
            b = b.fuse(bo.common(full))
    b = b.removeSplitter()
    # tongue (inside the lid wall) on the +/-Y walls, with snap risers; cut back over the tail / J1
    c = TONGUE_CLR
    ring_lo = plan_ring(WALL, WALL + TONGUE_T).common(ucyl(R_U + H_BASE))
    ring_hi = plan_ring(WALL + c, WALL + TONGUE_T).common(ucyl(R_U + H_BASE + TONGUE_H)).cut(ucyl(R_U + H_BASE))
    tongue = ring_lo.fuse(ring_hi).removeSplitter().cut(ucyl(R_U + FLOOR - 0.01))
    tongue = tongue.cut(R.box(-TAIL_CUT, TAIL_CUT, Y_MIN - 1, Y_MIN + WALL + TONGUE_T + 0.5, -10, 20))
    tongue = tongue.cut(R.box(CX_OFF - LEDGE_X, CX_OFF + LEDGE_X, Y_MIN + WALL + TONGUE_T + 0.3, Y_MAX - WALL - TONGUE_T - 0.3, -20, 20))
    tongue = tongue.cut(bay_block().fuse(R.box(MAG_X - BAY_HW - 0.3, MAG_X + BAY_HW + 0.3, Y_B1, Y_MAX + 1, -20, 30)))
    for sx in (-1, 1):                    # no tongue where the base's walls rise to the board top (X ends, corners)
        xa, xb = sorted((CX_OFF + sx * (END_X - 0.5), CX_OFF + sx * 40))
        tongue = tongue.cut(R.box(xa, xb, -60, 60, -20, 30))
    tongue = tongue.cut(R.box(-60, 60, -60, 60, Z_PCB_TOP, 30).common(
        R.box(-60, CX_OFF - LEDGE_X, -60, 60, -30, 30).fuse(R.box(CX_OFF + LEDGE_X, 60, -60, 60, -30, 30))))
    b = b.fuse(tongue.common(full))
    for x0, x1, yf, sy, zb in snaps():       # tongue risers with a square snap groove (1.0+ all round)
        y0, y1 = sorted((yf - sy * c, yf - sy * TONGUE_T))
        zt = zb + SNAP_GROOVE_H + 1.0 + SNAP_CHAMFER
        riser = R.box(x0, x1, y0, y1, -5, zt).common(full)
        yo = yf - sy * c
        ch = Part.Face(Part.makePolygon([V(x0 - 1, yo + sy * 0.01, zt - SNAP_CHAMFER), V(x0 - 1, yo + sy * 0.01, zt + 0.01),
                                         V(x0 - 1, yo - sy * SNAP_CHAMFER, zt + 0.01), V(x0 - 1, yo + sy * 0.01, zt - SNAP_CHAMFER)])).extrude(V(x1 - x0 + 2, 0, 0))
        riser = riser.cut(ch)
        b = b.fuse(riser)
        g0, g1 = sorted((yo, yo - sy * SNAP_DEPTH))
        b = b.cut(R.box(x0, x1, g0, g1, zb, zb + SNAP_GROOVE_H))
    b = b.removeSplitter()
    # strap lugs (integral bars)
    for l in lug_shapes(log):
        b = b.fuse(l)
    b = b.removeSplitter()
    for sx in (-1, 1):
        b = b.cut(slot_void(sx))
    # reliefs under the bottom-side pads (wire joints) in the ledges, cell-lead channel in the +X wall
    for (kx0, kx1), (ky0, ky1), dz in ((J2_RELIEF[0], J2_RELIEF[1], 1.0), (J3_RELIEF[0], J3_RELIEF[1], 1.0),
                                       (TP_RELIEF[0], TP_RELIEF[1], 0.5)):
        (mx0, my1), (mx1, my0) = k2m(kx0, ky0), k2m(kx1, ky1)
        b = b.cut(R.box(mx0, mx1, my0, my1, Z_PCB - dz, Z_PCB + 1))
    (ly0, ly1), ld = LEAD_CH
    xw = CX_OFF + OUT_W / 2 - WALL
    b = b.cut(R.box(xw - 1.0, xw, ly0, ly1, Z_PCB - 1.0, Z_PCB + 0.01))     # under the board (the 0.6 gap at the edge passes the leads)
    # magnetic connector pocket (proximal wall) and the J3 wire channel under the board's +X edge
    b = b.cut(mag_pocket())
    (kx0, kx1), dch = J3_CH
    mx0, mx1 = kx0 - J1_KX, kx1 - J1_KX
    b = b.cut(R.box(mx0, mx1, Y_B0 + 0.4, Y_B1 + 0.6, Z_PCB - dch, Z_PCB + 0.5))

    b = b.removeSplitter()
    # pods 3/4: foam pockets on the underside
    for sgn in (-1, 1):
        pl = pod_place(sgn)
        for y in R.PAD_Y:
            p = Part.makeCylinder(MODULE_POCKET_D / 2, R.MODULE_POCKET_H + 0.6, V(0, y, -0.6))
            p.Placement = pl.multiply(p.Placement)
            b = b.cut(p)
    # tail slot through the floor next to the distal wall
    b = b.cut(R.box(-TAIL_SLOT[0] / 2, TAIL_SLOT[0] / 2, Y_MIN + WALL, Y_MIN + WALL + TAIL_SLOT[1], -10, FLOOR + 2))
    # flex-root foam dot at the apex: pocket from below, boss inside for 1.0 behind it
    rx, ry = ROOT_DOT
    b = b.fuse(Part.makeCylinder(MODULE_POCKET_D / 2 + 0.6, R.MODULE_POCKET_H + 0.7, V(rx, ry, 0.3)))
    b = b.cut(Part.makeCylinder(MODULE_POCKET_D / 2, R.MODULE_POCKET_H + 0.6, V(rx, ry, -0.6)))
    return b.removeSplitter()


SNAP_SEGS = ((-11.0, -8.2, 1), (9.2, 11.4, 1), (-11.0, -TAIL_CUT, -1), (TAIL_CUT, 11.0, -1))   # (x0, x1, +1 proximal / -1 distal)
SNAP_DEPTH, SNAP_GROOVE_H, SNAP_RIB_H = 0.3, 1.2, 1.0
SNAP_RIB_D = TONGUE_CLR + 0.25
SNAP_CHAMFER = 0.3


def snaps():
    """Snap segments on the +/-Y walls, clear of the cell, J1, the tail, the connector and the light
    pipe: (x0, x1, y_inner_face, sign, z_groove_bottom). The groove sits >= 1.0 above the parting."""
    out = []
    for x0, x1, sy in SNAP_SEGS:
        yf = (Y_MAX - WALL) if sy > 0 else (Y_MIN + WALL)
        zb = z_u(min(abs(x0), abs(x1))) + H_BASE + 1.0
        out.append((x0, x1, yf, sy, zb))
    return out


def groove():
    """Parting hairline: on the curved parting and along the X end walls' top edge."""
    band = ucyl(R_U + H_BASE + GROOVE_H / 2).cut(ucyl(R_U + H_BASE - GROOVE_H / 2))
    ends = R.box(-60, 60, -60, 60, Z_PCB_TOP - GROOVE_H / 2, Z_PCB_TOP + GROOVE_H / 2).common(
        R.box(-60, CX_OFF - OUT_W / 2 + WALL, -60, 60, -30, 30).fuse(R.box(CX_OFF + OUT_W / 2 - WALL, 60, -60, 60, -30, 30)))
    band = band.cut(R.box(-60, CX_OFF - OUT_W / 2 + WALL, -60, 60, -30, 30)).cut(R.box(CX_OFF + OUT_W / 2 - WALL, 60, -60, 60, -30, 30))
    return band.fuse(ends).common(plan_ring(-1.0, GROOVE_D))


def build_button_cap(log=None):
    """Flush cap over SW1, along the shell's normal at the opening (button_axis): plug through the opening
    with its top following the lid surface, a flange disc square to the axis 0.3 under the shell, and a
    stem with a domed end that presses SW1's plunger (it moves along the axis, a few degrees off SW1's)."""
    p0, n = button_axis()
    rt = BTN_HOLE_D / 2 - BTN_GAP_R
    cav = cavity_raw()
    hit = cav.common(Part.makeLine(p0, p0 + n * 20.0))
    d_in = max((v.Point - p0).dot(n) for v in hit.Vertexes) if hit.Vertexes else 4.0   # p0 -> shell inside, along n
    shell = body(log).cut(cavity_raw())
    flange = None
    for dz in (0.3, 0.45, 0.6, 0.8, 1.0, 1.2):         # flange square to the axis, 0.2 clear of the shell
        for rf in (BTN_FLANGE_D / 2, 2.8, 2.6, 2.45):
            d_f1 = d_in - dz
            d_f0 = d_f1 - BTN_FLANGE_T
            test = Part.makeCylinder(rf + 0.2, BTN_FLANGE_T + 0.2, p0 + n * (d_f0 - 0.1), n)
            if test.common(shell).Volume < 1e-4:
                flange = Part.makeCylinder(rf, BTN_FLANGE_T, p0 + n * d_f0, n)
                break
        if flange is not None:
            break
    if flange is None:
        raise RuntimeError('button cap flange: no size clears the shell')
    if log:
        log(f"  button cap: axis tilted {math.degrees(math.acos(n.z)):.0f} deg (shell normal), flange r {rf:.2f}, {dz:.2f} under the shell")
    plug = Part.makeCylinder(rt, 20.0, p0 + n * d_f0, n).common(body(log))
    r_st = BTN_STEM_D / 2
    stem = Part.makeSphere(r_st, p0 + n * r_st)        # domed end on SW1's plunger
    if d_f0 > r_st:
        stem = stem.fuse(Part.makeCylinder(r_st, d_f0 - r_st + 0.01, p0 + n * r_st, n))
    return plug.fuse([flange, stem]).removeSplitter()


def surface_point_normal(p, d):
    """Where the line p + t d meets the outside of the body (the last hit going along d), and the outward
    surface normal there."""
    ln = Part.makeLine(p - d * 20.0, p + d * 20.0)
    c = body().common(ln)
    pts = [v.Point for v in c.Vertexes]
    q = max(pts, key=lambda v: (v - p).dot(d))
    best = None
    for f in body().Faces:
        dd = f.distToShape(Part.Vertex(q))[0]
        if best is None or dd < best[0]:
            best = (dd, f)
    f = best[1]
    u, v = f.Surface.parameter(q)
    n = f.normalAt(u, v)
    if n.dot(V(0, 0, 1)) < 0:
        n = -n
    return q, n


def led_axis():
    """Axis of the LED light hole: through D1's top, along the shell's normal where it exits."""
    x, y = D1
    p0 = V(x, y, Z_PCB_TOP + 0.6)
    n = V(0, 0, 1)
    for _ in range(4):
        q, n = surface_point_normal(p0, n)
    return p0, n


def button_axis():
    """Axis of the button opening and cap: through SW1's plunger, along the shell's normal where it exits
    (iterated). Returns (point on the axis just above SW1, unit direction)."""
    x, y = SW1
    z_sw = Z_PCB_TOP + SW1_H + BTN_GAP
    p0 = V(x, y, z_sw)
    n = V(0, 0, 1)
    for _ in range(4):
        q, n = surface_point_normal(p0, n)
    return p0, n


def build_lid(log=None):
    full = body(log)
    ends = end_walls()
    l = full.cut(ucyl(R_U + H_BASE)).cut(ends[0]).cut(ends[1]).cut(bay_block())
    l = l.cut(cavity_raw())
    for x0, x1, yf, sy, zb in snaps():       # square snap ribs on the lid's inner face
        r0, r1 = sorted((yf + sy * 0.01, yf - sy * SNAP_RIB_D))
        l = l.fuse(R.box(x0 + 0.3, x1 - 0.3, r0, r1, zb + 0.05, zb + 0.05 + SNAP_RIB_H))
    # light hole + guide tube down to the LED, all on one axis through D1 along the shell's normal
    p_led, n_led = led_axis()
    hit = cavity_raw().common(Part.makeLine(p_led, p_led + n_led * 20.0))
    d_in = max((v.Point - p_led).dot(n_led) for v in hit.Vertexes)
    d0 = 1.4                                            # tube starts this far up the axis (clear of the LED and board parts)
    tube = Part.makeCylinder(LP_TUBE / 2, d_in - d0 + 0.5, p_led + n_led * d0, n_led).common(cavity_raw())
    hole = Part.makeCylinder(LP_D / 2, 20.0, p_led + n_led * 0.5, n_led)
    l = l.fuse(tube).cut(hole)
    # flush button: opening along the shell's normal (it sits on the sloped shoulder: no knife-edge rim)
    p0, n = button_axis()
    l = l.cut(Part.makeCylinder(BTN_HOLE_D / 2, 14.0, p0, n))
    # cell cage: two ribs from the crown flank the cell's long sides
    for x0, x1 in ((CELL_X0 - 1.0, CELL_X0), (CELL_X0 + CELL_POCKET[0], CELL_X0 + CELL_POCKET[0] + 1.0)):
        rib = R.box(x0, x1, BAT_Y0 + 0.2, BAT_Y0 + BAT_L, Z_BAT + BAT_T - 1.8, 20).common(full).cut(ucyl(R_U + H_BASE))
        l = l.fuse(rib)
    # pry notch in the lid's edge above the connector bay (elbow end, centre): only the bay block is behind it
    zp = BAY_Z
    l = l.cut(R.box(MAG_X - NOTCH_W / 2, MAG_X + NOTCH_W / 2, Y_MAX - WALL - 0.1, Y_MAX + 1, zp - 0.1, zp + NOTCH_H - 0.1))
    return l.removeSplitter()


# ---------------- internals (visual + clash check) ----------------
def build_cell_spacer():
    """Spacer for the shorter fallback cell (401120 class, ~21 mm): fills the cage from the cell's
    proximal end to the lid's proximal wall."""
    y0 = BAT_Y0 + R.CELL_FALLBACK[1] + 0.2
    y1 = BAT_Y0 + BAT_L
    return R.box(CELL_X0 + 0.3, CELL_X0 + CELL_POCKET[0] - 0.3, y0, y1, Z_BAT - 0.4, Z_BAT + BAT_T - 0.6).common(cavity_raw())


def board_real():
    sh = Part.read(BOARD_STEP)
    sols = [s for s in sh.Solids]
    pcb = max(sols, key=lambda s: s.BoundBox.XLength * s.BoundBox.YLength if s.BoundBox.ZLength < PCB_T + 0.1 else 0)
    bb = pcb.BoundBox
    dx, dy, dz = -(bb.XMin + J1_KX), Y_B0 - bb.YMin, Z_PCB - bb.ZMin
    out = []
    for s in sols:
        s = s.copy()
        s.translate(V(dx, dy, dz))
        out.append(s)
    ip = sols.index(pcb)
    pcb = out[ip]
    parts = [s for k, s in enumerate(out) if k != ip]
    return pcb, Part.makeCompound(parts), f'real ({os.path.relpath(BOARD_STEP, R.ROOT)})'


def board():
    return board_real()


def battery():
    b = R.box(BAT_X0, BAT_X0 + BAT_W, BAT_Y0, BAT_Y0 + BAT_L, Z_BAT, Z_BAT + BAT_T)
    try:
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
    y_in = Y_B0 + 3.6
    segs = [arc(y_root, z0 + r, 180, 270),
            R.box(J1_X - w / 2, J1_X + w / 2, yr - t / 2, yr + t / 2, z0 + r, z1 - r),
            arc(y_root, z1 - r, 90, 180),
            R.box(J1_X - w / 2, J1_X + w / 2, y_root, y_in, z1 - t / 2, z1 + t / 2)]
    length = math.pi * r + (z1 - z0 - 2 * r) + (y_in - y_root)
    return segs[0].fuse(segs[1:]).removeSplitter(), length


def flex_on_module(lift=R.FOAM_PROUD):
    """Flex pods 3/4 (+ pads, foam) on the underside and the spine link between them."""
    poly, gold, foam = [], [], []
    p0, g0, f0 = R.flex_pod(lift + MODULE_EXTRA, pocket=R.MODULE_POCKET_H)
    for sgn in (-1, 1):
        pl = pod_place(sgn)
        for src, dst in ((p0, poly), (g0, gold), (f0, foam)):
            for s in (src if isinstance(src, list) else [src]):
                s = s.copy()
                s.Placement = pl.multiply(s.Placement)
                dst.append(s)
    a0 = -POD_TH + (R.POD_W / 2) / R_U
    y0, y1 = R.SPINE_Y
    ring = ucyl(R_U).cut(ucyl(R_U - R.FLEX_T)).common(R.box(-50, 50, y0, y1, -50, 50))
    wedge = Part.Face(Part.makePolygon([V(0, y0, -R_U), V(60 * math.sin(a0), y0, -R_U + 60 * math.cos(a0)),
                                        V(0, y0, 20), V(-60 * math.sin(a0), y0, -R_U + 60 * math.cos(a0)), V(0, y0, -R_U)])).extrude(V(0, y1 - y0, 0))
    poly.append(ring.common(wedge))
    return poly, gold, foam


def leads():
    """Cell leads (visual + clash): from the cell's lead end over the board to the +X edge, down the
    lead channel and back under the board to the J2 pads."""
    out = []
    xw = CX_OFF + OUT_W / 2 - WALL
    for k, (kx, ky) in enumerate(J2_K):
        px, py = k2m(kx, ky)
        yl = (LEAD_CH[0][0] + LEAD_CH[0][1]) / 2 + (k - 0.5) * 1.2
        z_t = Z_PCB_TOP + 1.9 if k == 0 else Z_PCB_TOP + 1.3
        pts = [V(BAT_X0 + BAT_W - 2.5 - 2 * k, BAT_Y0 - 0.3, Z_BAT + 1.0), V(BAT_X0 + BAT_W - 2.5 - 2 * k, BAT_Y0 - 1.0, z_t),
               V(12.6, yl, z_t), V(14.0, yl, Z_PCB_TOP + 0.3), V(xw - 0.3, yl, Z_PCB_TOP + 0.3), V(xw - 0.3, yl, Z_PCB - 0.45),
               V(xw - 1.0, yl, Z_PCB - 0.45), V(px, py, Z_PCB - 0.35)]
        for a, b_ in zip(pts[:-1], pts[1:]):
            d = b_ - a
            if d.Length < 1e-3:
                continue
            out.append(Part.makeCylinder(0.25, d.Length, a, d))
    return out


def internals():
    pcb, parts, src = board()
    bat, swell = battery()
    tail, tl = tail_shape()
    cap = build_button_cap()
    return dict(pcb=pcb, parts=parts, src=src, bat=bat, swell=swell, tail=tail, tail_len=tl, cap=cap,
                mag=mag_body(), leads=leads())


def outside_numbers(base, lid):
    bb = base.fuse(lid).optimalBoundingBox()
    lb = lid.optimalBoundingBox()
    body_bb = body().optimalBoundingBox()
    xz = body().slice(V(0, 1, 0), 0.0)
    return dict(overall_x=round(bb.XLength, 1), overall_y=round(bb.YLength, 1), overall_z=round(bb.ZLength, 2),
                body_x=round(body_bb.XLength, 1), body_y=round(body_bb.YLength, 1),
                top_apex_above_underside=round(H_TOP, 2), lid_bbox=[round(lb.XLength, 1), round(lb.YLength, 1), round(lb.ZLength, 1)])


if not getattr(sys, 'neurband_lib', False):
    log = R.Log('module')
    log(f"  H_TOP solved {H_TOP:.2f} (cell top {Z_BAT + BAT_T:.2f}, swollen {Z_BAT + BAT_T + BAT_SWELL:.2f})")
    base = U.check(build_base(log), 'module_base', log)
    lid = U.check(build_lid(log), 'module_lid', log)
    I = internals()
    fpoly, fgold, ffoam = flex_on_module()
    log(f"  board: {I['src']}")
    on = outside_numbers(base, lid)
    log("  outside: " + json.dumps(on))
    log(f"  z: floor {FLOOR}, pcb {Z_PCB:.2f}-{Z_PCB_TOP:.2f}, cell {Z_BAT:.2f}-{Z_BAT + BAT_T:.2f} (+{BAT_SWELL}), top apex {H_TOP:.2f}")
    log(f"  tail path needed {I['tail_len']:.1f} mm from the strip edge")
    bb = I['parts'].BoundBox
    log(f"  tallest board part top z {bb.ZMax:.2f} ({bb.ZMax - Z_PCB_TOP:.2f} above the board)")

    def clash(a, b):
        try:
            return round(a.common(b).Volume, 3)
        except Exception:
            return None
    LD = Part.makeCompound(I['leads'])
    checks = {
        'pcb_vs_base': clash(I['pcb'], base), 'pcb_vs_lid': clash(I['pcb'], lid),
        'parts_vs_lid': clash(I['parts'], lid), 'parts_vs_base': clash(I['parts'], base),
        'bat_vs_lid': clash(I['bat'], lid), 'bat_swell_vs_lid': clash(I['swell'], lid),
        'bat_vs_parts': clash(I['bat'], I['parts']), 'bat_vs_base': clash(I['bat'], base),
        'tail_vs_base': clash(I['tail'], base), 'tail_vs_lid': clash(I['tail'], lid),
        'tail_vs_pcb': clash(I['tail'], I['pcb']), 'base_vs_lid': clash(base, lid),
        'flex_vs_base': clash(Part.makeCompound(fpoly), base),
        'cap_vs_lid': clash(I['cap'], lid), 'cap_vs_parts': clash(I['cap'], I['parts']),
        'mag_vs_base': clash(I['mag'], base), 'mag_vs_lid': clash(I['mag'], lid), 'mag_vs_pcb': clash(I['mag'], I['pcb']),
        'mag_vs_parts': clash(I['mag'], I['parts']), 'mag_vs_tail': clash(I['mag'], I['tail']),
        'leads_vs_base': clash(LD, base), 'leads_vs_lid': clash(LD, lid), 'leads_vs_pcb': clash(LD, I['pcb']),
    }
    log("  clash mm3: " + json.dumps(checks))
    log(f"  cell edge to antenna strip {BAT_X0 - ANT_X[1]:.1f} mm; no metal near the antenna strip (connector at x {MAG_X:+.1f})")
    with open(os.path.join(R.HERE, 'logs', 'module_checks.json'), 'w') as f:
        json.dump(dict(checks=checks, board=I['src'], tail_len=I['tail_len'], outside=on), f, indent=1)
    R.save('module_base', [('module_base', base, R.C_HOUSING)], log)
    R.save('module_lid', [('module_lid', lid, R.C_HOUSING)], log)
    R.save('module_assy', [('module_base', base, R.C_HOUSING), ('module_lid', lid, R.C_HOUSING),
                           ('main_board', I['pcb'], R.C_PCB), ('board_parts', I['parts'], (0.15, 0.15, 0.15)),
                           ('lipo', I['bat'], R.C_LIPO), ('tail', I['tail'], R.C_FLEX),
                           ('flex_pods_3_4', Part.makeCompound(fpoly), R.C_FLEX),
                           ('pads', Part.makeCompound(fgold), R.C_GOLD), ('foam', Part.makeCompound(ffoam), R.C_FOAM),
                           ('button_cap', I['cap'], R.C_HOUSING), ('mag_connector', I['mag'], (0.08, 0.08, 0.09)),
                           ('mag_contacts', Part.makeCompound(mag_contacts()), R.C_GOLD),
                           ('cell_leads', LD, (0.75, 0.12, 0.10))], log)
    R.save('button_cap', [('button_cap', I['cap'], R.C_HOUSING)], log)
    spacer = U.check(build_cell_spacer(), 'cell_spacer', log)
    log("  cell spacer vs lid / parts / base mm3:", clash(spacer, lid), clash(spacer, I['parts']), clash(spacer, base))
    R.save('cell_spacer', [('cell_spacer', spacer, R.C_HOUSING)], log)
    R.fab('cell_spacer', 'neurband rev C cell spacer (only for the shorter 401120-class fallback cell)', spacer, 2, 'mjf', 'pa12', 'gray', log)
    R.fab('module_base', 'neurband rev C module base r2 (chassis with two integral strap bars, carries pods 3/4)', base, 3, 'mjf', 'pa12', 'black', log)
    R.fab('module_lid', 'neurband rev C module lid r2 (tapered, crowned shell)', lid, 3, 'mjf', 'pa12', 'black', log)
    R.fab('button_cap', 'neurband rev C flush button cap', I['cap'], 4, 'mjf', 'pa12', 'black', log)
    R.finish(log)
