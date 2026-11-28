"""params.py - every dimension of the neurband rev C housing, mechanical revision 2 (pure Python, no FreeCAD).

Design (2026-11-28):
  tub    one rigid part: floor, walls, the four strap lugs and, on the wrist side, two flat runners
         that carry flex paddles 3 and 4 on six raised pads. The wrist side is flat. It prints upright
         on those pads, without supports, so everything inside (board nest, battery shelves, wire
         trough) is an open pocket. The strap pulls on the tub only: no joint is in the load path.
  lid    flat cap printed top down. It goes on 1.3 mm toward the elbow and slides toward the hand to lock:
         four pegs under ledges in the long walls, behind the lugs, and a detent on each side.
  pod    x6, printed on its side: a strap clip with two spring wings (the P and N electrodes) and a
         rigid middle pad (the shared bias electrode, also the travel stop of the wings).
  tray   flat bonding tray: the flex lies electrodes down on pins, the tub and pods are pressed on.

Frames (mm):
  module frame  X across the wrist, Y along the arm (flex tail and J1 at -Y, toward the hand), Z up.
                Z = 0 is the floor the main board lies on (the underside of the board).
                X = 0 is the centre of the flex tail and of the pod row; the board (28.7 wide,
                J1 at 14.0) is 0.35 off that, so the body outline is centred on XC = +0.35.
  pod frame     u along the arm (= module Y), h from the pod plate toward the skin.
"""
import math

# ---------------- fabricated parts (frozen) ----------------
N_PODS = 8
PITCH = 18.0                    # pod pitch along the flex
POD_W, POD_L = 7.1, 30.0        # flex paddle
PAD_D = 6.5                     # gold electrode
PAD_Y = (-10.0, 0.0, 10.0)      # N (tail side), bias, P
HOLE_D = 1.2                    # flex alignment holes
HOLE_Y = (-5.0, 5.0)
SPINE_Y = (-7.0, 0.6)           # flex link strip between pods
ROOT_HX = 12.55                 # paddles 3, 4 and the tail root are one sheet: |x| <= this for y in -15 .. +0.6
TAIL_W = 10.5
TAIL_T = 0.30                   # at the stiffener
TAIL_FREE_L = 8.50              # paddle end line (y = -15) to the tail tip
TAIL_STIFF_L = 3.70             # stiffened tip
TAIL_INSERT = 3.6               # tail length inside J1
FLEX_T = 0.15
TAPE_T = 0.15                   # double sided tape under the flex (0.1 .. 0.25 is fine)
TAIL_R = 0.9                    # smallest bend radius allowed in the tail

PCB_W, PCB_L, PCB_T = 28.7, 27.0, 1.0
J1_KX = 14.0                    # KiCad x of J1 = module X 0
PCB_SHIFT = 1.5                 # the board sits this much toward +Y of where rev C1 had it (tail budget, see tail_need)
PCB_X0, PCB_X1 = -J1_KX, PCB_W - J1_KX          # -14.0 .. +14.7
PCB_Y0 = -POD_L / 2 + 0.2 + PCB_SHIFT           # -13.3
PCB_Y1 = PCB_Y0 + PCB_L                         # +13.7
J1_H = 2.08                     # J1 and SW1 tops above the board
J1_HX = 7.2
J1_SLOT_DZ = 0.50               # tail plane above the board top
SW1 = (10.8, -12.9 + PCB_SHIFT)
SW1_BOX = (8.3, 13.3, -14.4 + PCB_SHIFT, -11.4 + PCB_SHIFT)
D1 = (-12.0, 11.2 + PCB_SHIFT)  # status LED
ANT_X1 = -8.35                  # printed antenna strip: X < this
J2 = ((9.8, -6.6 + PCB_SHIFT), (12.8, -6.6 + PCB_SHIFT))        # battery pads (board underside)
J3 = ((9.9, -13.2 + PCB_SHIFT), (12.9, -13.2 + PCB_SHIFT))      # charge pads (board underside)
TP_BOX = (-13.2, -9.0, 6.8 + PCB_SHIFT, 11.0 + PCB_SHIFT)       # SWD pads (board underside)

# 302030 LiPo, measured by the owner: about 20 x 32 x 3, 4 mm at the protection board
BAT_W, BAT_L = 20.4, 31.4
BAT_L_MAX = 32.0                # longest cell the bay takes
BAT_T = 3.3                     # cell body incl. 0.25 swell
BAT_PCM_T = 4.2                 # at the protection board (last BAT_PCM_L of the +Y end)
BAT_PCM_L = 6.0
BAT_X0 = -6.7                   # 1.65 mm clear of the antenna strip (the tested position)
BAT_Y0 = -BAT_L / 2

# bought: Tech-Protect Nylon Classic, QuickFit 22 (22 mm wide, measured by the owner), clips popped off
STRAP_W = 22.0
STRAP_T = 1.85
STRAP_COLLAR = 9.0              # stiff sewn double layer at each loop (estimate; not measured)

# ---------------- tub ----------------
XC = (PCB_X0 + PCB_X1) / 2                      # +0.35
WALL = 1.00
PCB_CLR = 0.15
BODY_HX = PCB_W / 2 + PCB_CLR + WALL            # 15.50 (31.0 wide)
BODY_HY = 18.00                                 # 36.0 long: 1 mm more than rev C1, for a 32 mm cell between two end stops
IN_HX = BODY_HX - WALL                          # 14.50
IN_HY = BODY_HY - WALL                          # 17.00
PLAN_R = 2.8
T_FLOOR = 1.50                                  # floor under the board (rev C1: 1.14 web, 0.86 at the thinnest)
H_RIDGE = 2.30                                  # electrode pads below the floor: "about two foam dots" (see tail_need)
Z_SKIN = -(T_FLOOR + H_RIDGE)                   # -3.80: the plane of the six pads = bed plane of the print
RIDGE_IN = 5.25                                 # inner edge of both runners (|x|)
RIDGE_OUT = 13.90                               # outer edge of both runners (|x|); 45 deg bevels from here up to the walls
RIDGE_HY = 16.80                                # runner ends (|y|); 1.2 mm bevel up to the end walls
Z_WALL0 = Z_SKIN + (XC + BODY_HX - RIDGE_OUT)   # -1.85: where the +X wall starts; the lug undersides start here on both sides
TUNNEL_TOP_HX = RIDGE_IN - H_RIDGE              # 2.95: 5.9 mm bridge between the runners
GROOVE_Y = (-5.0, 5.0)                          # V grooves across the runners, between the pads (flex holes are here)
GROOVE_W, GROOVE_D = 3.0, 1.5
# where the flex leaves the pad plane toward J1
BEND_Y = -12.75                                 # 0.5 mm inside the edge of the N electrodes
STRIP_POCKET = (BEND_Y, -15.05, 2.10)           # y0, y1, height: room for the paddle ends that lift with the tail
CHIMNEY = (-5.75, 5.75, -15.20, -12.50)         # tail passage through runners and floor

Z_SHELF_A = 3.35                                # -Y battery shelf: 0.34 above the SW1 cap
Z_SHELF_B = 2.45                                # +Y shelf, under the protection board (cell lies flat with the bump down)
Z_ROOF = 7.05                                   # inside of the lid top
ROOF_T = 0.90
Z_TOP = Z_ROOF + ROOF_T                         # 7.95
TOP_CHAM = 1.0
Z_SEAM = 6.00                                   # tub wall top / lid skirt bottom
LIP_T, LIP_H, LIP_CLR = 0.70, 2.30, 0.10        # lid lip inside each long wall: carries the pegs and covers the detent slit
BLOCK_A_X0 = 7.5                                # -Y stop blocks start here (J1 passes between them when the board folds down)

# recesses in the floor (open pockets; x0, x1, y0, y1, depth)
WIRE_TROUGH = (10.9, 13.1, -8.0 + PCB_SHIFT, 14.2, 1.30)
WIRE_BAY = (10.8, 14.4, PCB_Y1 - 0.3, IN_HY - 0.2, 1.30)
J2_POCKET = (8.9, 13.6, -7.7 + PCB_SHIFT, -3.6 + PCB_SHIFT, 1.10)
J3_POCKET = (9.0, 13.7, -14.4 + PCB_SHIFT, -12.1 + PCB_SHIFT, 0.90)
J3_RISER = (10.4, 12.4, -14.9, -12.1 + PCB_SHIFT, 0.90)        # charge leads: channel, then up beside the shelf
TP_POCKET = (-13.3, -8.9, 6.7 + PCB_SHIFT, 11.1 + PCB_SHIFT, 0.50)

# ---------------- strap lugs (on the tub) and printed cross-bars ----------------
SLOT_W = STRAP_W + 0.50         # bay between the lugs
BAR_W = 2.65
BAR_H = 2.50
BAR_CLR = 0.14
Z_BAR = 4.40                    # bar axis above the floor: mid height of the case (rev C1: 2.65 BELOW the floor)
SLOT_GAP = 2.00                 # wall to bar: the sewn loop passes here
LUG_OUT_WALL = 1.75             # closed end beyond the bar (the part that broke once on rev C1)
LUG_FLANGE = 1.30               # above the bar
LUG_W = 4.50                    # along the bar, per lug (rev C1: 3.70)
LUG_X = SLOT_GAP + BAR_W + 2 * BAR_CLR + LUG_OUT_WALL          # 6.68 beyond the wall
LUG_HX = BODY_HX + LUG_X                        # 22.18 from XC (44.4 over the lugs)
LUG_HY = SLOT_W / 2 + LUG_W                     # 15.75
PIN_DX = SLOT_GAP + BAR_W / 2 + BAR_CLR         # bar centre outside BODY_HX
LUG_UNDER_DEG = 50.0            # overhang of the lug underside, from vertical
LUG_TOP_Z = Z_BAR + BAR_H / 2 + BAR_CLR + LUG_FLANGE            # 7.09

# ---------------- lid ----------------
LID_SLIDE = 1.30                # the lid goes on this far toward +Y (the elbow) and slides toward the hand to lock
PEG_Y = (11.70, -14.60)         # -Y end of the two pegs on each long side, lid closed (both slots are behind a lug)
PEG_L, PEG_Z = 1.60, (3.90, 4.90)       # peg: bottom, and top at its root; the top falls at 45 deg toward the tip
PEG_REACH = 0.60                # peg beyond the lip; 0.5 mm of it is under the ledge
TAB_T = LIP_T
SLOT_DEPTH = 0.75               # L slot in the 1.0 mm wall, backed by the lug
DETENT_Y = (-10.0, 10.0)        # slit under a strip of each long wall: the strip is the detent spring
DETENT_SLIT_Z = (4.20, 5.00)
DETENT_BUMP = 0.35              # bump on the lid lip (0.25 mm interference outside the dimple)
DETENT_BUMP_Y = (-0.60, 0.60)
DETENT_DIMPLE = 0.30
BAY_HY = 16.05                  # cell bay: stops on both shelves
LED_SLIT_X = (D1[0] - 0.7, D1[0] + 1.5)
LED_SLIT_Y = (D1[1] - 0.55, D1[1] + 0.75)
FENCE_X = (BAT_X0 - 1.00, BAT_X0 - 0.20)

# ---------------- pod (x6) ----------------
POD_SHELL_W = 8.0               # along the band
POD_SHELL_L = 30.2
POD_FLOOR_T = 1.40
POD_STRAP_W = STRAP_W + 0.60
POD_SLOT_H = STRAP_T + 0.30
POD_EAR_T = 1.20
POD_EAR_IN = 2.60
POD_EAR_R = 2.0                 # the two rounded outer corners
POD_HC = 2.50                   # rigid middle pad above the plate = worn standoff of the pod
POD_CAP_HX = 3.30
POD_CAP_T = 0.90
POD_TRUNK_HX = 0.80
WING_T = 0.60                   # one 0.6 mm bead, 8 mm wide
WING_ROOT_U = 1.70
WING_ARM_H = 0.80               # centre line of the low arm under the cap
WING_RAMP_U0 = 3.90
WING_PAD_U0 = 6.70
WING_PAD_L = 6.60
WING_PAD_T = 0.90
WING_D0 = 0.90                  # travel from free to flat (level with the middle pad)
WING_STOP = 1.40                # travel at the stop
# from springs.py (frame model, E = 3.3 GPa): per mm of travel at the pad centre
WING_K = 2.05                   # N/mm
WING_STRAIN = 0.0106            # surface strain per mm
WING_TILT = 9.4                 # deg per mm
WING_IN, WING_OUT = 0.47, 1.54  # drop of the inner / outer pad end per mm
WING_SHIFT = 0.30               # outward shift of the pad per mm
POD_H = POD_FLOOR_T + POD_SLOT_H + POD_EAR_T

SIZES = (145.0, 160.0, 180.0)


def wing_free(travel=0.0):
    """Pad of a wing, free (travel 0) or pressed in by `travel`: (u_in, h_in), (u_out, h_out) of the skin face, and the tilt in degrees."""
    d = WING_D0 - travel
    h_in = POD_HC + d * WING_IN
    h_out = POD_HC + d * WING_OUT
    tilt = math.atan2(h_out - h_in, WING_PAD_L)
    uc = WING_PAD_U0 + WING_PAD_L / 2 - WING_SHIFT * d
    return ((uc - WING_PAD_L / 2 * math.cos(tilt), h_in), (uc + WING_PAD_L / 2 * math.cos(tilt), h_out), math.degrees(tilt))


def tail_need(tape=TAPE_T, r=TAIL_R):
    """Flex length needed from the bend line to the start of the stiffener, and what the flex has.
    Path: quarter-ish arc up from the pad plane, a straight run, an arc into J1 (both radius r)."""
    z_s = Z_SKIN - tape - FLEX_T / 2
    y_e, z_e = PCB_Y0 - (TAIL_STIFF_L - TAIL_INSERT), PCB_T + J1_SLOT_DZ
    dy, h = BEND_Y - y_e, z_e - z_s
    s = math.hypot(dy, h - 2 * r)
    have = (-POD_L / 2 - BEND_Y) * -1 + TAIL_FREE_L - TAIL_STIFF_L
    return math.pi * r + s, have


def tail_path(tape=TAPE_T, r=TAIL_R):
    """Centre line of the tail from the bend line to the tip, as (y, z) points."""
    z_s = Z_SKIN - tape - FLEX_T / 2
    y_e, z_e = PCB_Y0 - (TAIL_STIFF_L - TAIL_INSERT), PCB_T + J1_SLOT_DZ
    dy, h = BEND_Y - y_e, z_e - z_s
    s = math.hypot(dy, h - 2 * r)
    a = math.atan2(h - 2 * r, dy)                 # direction of the straight run above the -Y axis
    pts = []
    for k in range(13):                           # first arc: heading -Y, turning up by a
        t = a * k / 12
        pts.append((BEND_Y - r * math.sin(t), z_s + r * (1 - math.cos(t))))
    p = pts[-1]
    q = (p[0] - s * math.cos(a), p[1] + s * math.sin(a))
    pts.append(q)
    cy, cz = y_e, z_e - r
    for k in range(1, 13):                        # second arc into J1
        t = a + (math.pi - a) * k / 12
        pts.append((cy - r * math.sin(t), cz - r * math.cos(t)))
    pts.append((y_e + TAIL_STIFF_L, z_e))
    return pts


if __name__ == '__main__':
    need, have = tail_need()
    print(f"body {2 * BODY_HX:.1f} x {2 * BODY_HY:.1f} x {Z_TOP - Z_SKIN:.2f} (pads to top), {2 * LUG_HX:.1f} over the lugs")
    print(f"bar axis {Z_BAR - Z_SKIN:.2f} above the pad plane; lug top {LUG_TOP_Z:.2f}, underside meets the wall at {Z_WALL0:.2f}")
    print(f"flex tail: needs {need:.2f} of {have:.2f} mm (tape {TAPE_T}); with 0.25 mm tape {tail_need(0.25)[0]:.2f}")
    (a, b, tilt) = wing_free()
    print(f"pod: middle pad {POD_HC:.2f}, wing pad free {a[1]:.2f} .. {b[1]:.2f} ({tilt:.1f} deg), "
          f"{WING_K * WING_D0:.2f} N and {100 * WING_STRAIN * WING_D0:.2f} % when flat, {100 * WING_STRAIN * WING_STOP:.2f} % at the stop")
