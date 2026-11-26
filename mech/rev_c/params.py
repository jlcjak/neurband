"""params.py - every dimension of the neurband rev C housing (pure Python, no FreeCAD).

Design (2026-11-26, "cradle + lid"):
  cradle   rigid, printed with its flat top on the bed. The flat top is the board seat; the
           underside (printed facing up, so any shape is support-free) is a faceted saddle that
           follows the wrist: a centre flat under the flex root and two pod facets tilted
           POD_TILT that carry flex pods 3 and 4. Two low slotted lugs droop with the wrist.
  lid      rigid tub printed top-down: flat top, living-hinge button over SW1, LED slit.
           It snaps onto the cradle with two lips that sit inside the strap slots.
  pod      rigid link, printed on its side, x6: foam dimples on the skin face, strap channel behind.
  jig      flat bonding jig: holds the cradle and the six pods and pins the flex by its holes.

Frames (mm):
  module frame  X across the wrist (+X = radial for a right arm), Y along the arm (flex tail and
                J1 at -Y), Z up. Z = 0 is the cradle's flat top = the underside of the main board.
                X = 0 is the centre of the flex tail and of the pod row; the board (28.7 wide,
                J1 at 14.0) is 0.35 off that, so the body outline is centred on XC = +0.35.
"""
import math

# ---------------- fabricated parts (frozen) ----------------
N_PODS = 8
PITCH = 18.0                    # pod pitch along the flex
POD_W, POD_L = 7.1, 30.0        # flex paddle
PAD_D = 6.5                     # gold electrode
PAD_Y = (-10.0, 0.0, 10.0)
HOLE_D = 1.2                    # flex alignment holes
HOLE_Y = (-5.0, 5.0)
SPINE_Y = (-7.0, 0.6)           # flex link strip between pods
TAIL_W = 10.5
TAIL_T = 0.30                   # at the stiffener
TAIL_MAX_L = 8.50               # pod end (y = -15) to the tail tip
TAIL_INSERT = 3.6               # tail length inside J1
FLEX_T = 0.15

PCB_W, PCB_L, PCB_T = 28.7, 27.0, 1.0
J1_KX = 14.0                    # KiCad x of J1 = module X 0
PCB_X0, PCB_X1 = -J1_KX, PCB_W - J1_KX          # -14.0 .. +14.7
PCB_Y0 = -POD_L / 2 + 0.2                       # -14.8, J1 mouth at the pod ends
PCB_Y1 = PCB_Y0 + PCB_L                         # +12.2
J1_H = 2.08                     # J1 and SW1 tops above the board
J1_Y1 = -9.68                   # back of J1
J1_SLOT_DZ = 0.50               # tail plane above the board top
SW1 = (10.8, -12.9)             # actuator centre (TS-1088, top push)
SW1_ACT_D = 1.9
D1 = (-12.0, 11.2)              # status LED
ANT_X1 = -8.35                  # printed antenna strip: X < this, Y < +0.6
J2 = ((9.8, -6.6), (12.8, -6.6))        # battery pads (board underside)
J3 = ((9.9, -13.2), (12.9, -13.2))      # charge pads (board underside)
TP_BOX = (-13.2, -9.0, 6.8, 11.0)       # SWD pads (board underside): x0, x1, y0, y1

# 302030 LiPo, measured by the owner: about 20 x 32 x 3, 4 mm at the protection board
BAT_W, BAT_L = 20.4, 31.4
BAT_T = 3.3                     # cell body incl. 0.25 swell
BAT_PCM_T = 4.2                 # at the protection board (last BAT_PCM_L of the +Y end)
BAT_PCM_L = 6.0
BAT_X0 = -6.7                   # 1.65 mm clear of the antenna strip (the tested position)

# bought: 1.27 mm foam tape punched to 5 mm dots; Tech-Protect Nylon Classic for Garmin fenix 5/6/7/8 47 mm:
# 2-piece nylon buckle strap, QuickFit 22 (measured 22 mm wide by the owner, 2026-11-26). The shop's page mixed it up
# with the 26 mm / 51 mm version; the piece lengths below (92 + 125 mm) come from that page and are NOT yet measured.
FOAM_D, FOAM_T = 5.0, 1.27
FOAM_POCKET_D, FOAM_POCKET_H = 5.4, 0.30
FOAM_FREE = FOAM_T - FOAM_POCKET_H      # 0.97 proud, unloaded
FOAM_WORN = 0.62                        # proud when worn
STANDOFF = FOAM_WORN + FLEX_T           # pod face above the skin when worn (0.77)
STRAP_W = 22.0
STRAP_T = 1.85                  # woven nylon thickness
STRAP_BUCKLE_L = 80.0           # 92 mm half: lug pin to buckle tongue bar (~80 mm nylon + ~12 mm buckle)
STRAP_HOLE_L = 120.0            # 125 mm half: lug pin to tapered tip
STRAP_HOLES = tuple(33.4 + 6.5 * i for i in range(12))   # 12 oval tang slots (33.4 .. 104.9 mm)
STRAP_HOLE_W, STRAP_HOLE_LEN = 4.6, 2.2

# ---------------- body (cradle + holder + lid) ----------------
XC = (PCB_X0 + PCB_X1) / 2                      # +0.35
WALL = 1.00                                     # thinner walls (2 solid perimeters + Arachne)
PCB_CLR = 0.15                                  # tight slip fit inside the holder's 4-corner PCB nest
BODY_HX = PCB_W / 2 + PCB_CLR + WALL            # 15.50 half width (31.0 wide)
BAT_Y0 = -15.80                                 # cell slides forward over J1 & SW1 (button access removed)
BAT_END_CLR = 0.70                              # clearance to +/-Y inner walls (room for PCM leads at +Y)
BODY_HY = 17.50                                 # 17.50 half length (35.0 long, down from 41.4)
IN_HY = BODY_HY - WALL                          # 16.50 inner half length (33.0 clear for 31.4 cell)
PLAN_R = 2.8                                    # crisp watch-like corner radius (clears PCB corners by 0.15)
ROOF_T = 0.90
Z_PCB_TOP = PCB_T
Z_J1_TOP = PCB_T + J1_H                         # 3.08
Z_HOLDER = 3.35                                 # flat battery deck top (0.34 above SW1 actuator cap)
Z_ROOF = 7.80                                   # inside of the lid top: clears flat cell with PCM up or down
Z_TOP = Z_ROOF + ROOF_T                         # 8.70
TOP_CHAM = 1.1
SEAM_CHAM = 0.25

# ---------------- cradle underside: faceted saddle ----------------
R_DESIGN = 39.0                 # skin radius the two module pods are tangent to
POD_ARC = PITCH / 2             # pods 3 and 4 sit 9 mm of flex either side of the tail
POD_TILT = POD_ARC / R_DESIGN   # rad (13.2 deg)
BEND_X = 5.35                   # facet starts between the tail edge (5.25) and the paddle (5.45)
SEAT_RISE = 0.28                # vertical projection toward the wrist under the two flex paddles
T_CENTRE = 0.80 + SEAT_RISE     # cradle thickness at the facet bends
T_WEB = 1.14                    # wrist-facing centre web, blended into the original electrode facets
WEB_HALF_FLAT = 3.65

# ---------------- strap lugs (100% 3D-printed slide-in cross-bar through the strap's sewn loop) ----------------
SLOT_W = STRAP_W + 0.50         # centred sewn loop with 0.25 mm nominal clearance per side
BAR_W = 2.65                    # narrower radial section leaves material behind the pin
BAR_H = 2.50                    # cross-bar vertical thickness (Z) — prints flat on bed along continuous grain
BAR_CLR = 0.14                  # slip fit inside the lug ear slots
BAR_ZC = -2.65                  # bar axis, relative to the board seat
EAR_MID_Z = -5.18               # lug ear underside at inner edge of bar (clears 145..180 mm wrists)
EAR_BOT_Z = -6.00               # lug ear underside at outer tip (curves down with wrist -> stout floor under bar)
SLOT_GAP = 2.00                 # clear gap between body wall and bar inner face (passes 1.85 mm sewn loop + lid snap)
BAR_T = BAR_W
PIN_DX = SLOT_GAP + BAR_W / 2   # bar centre outside BODY_HX
ARM_W = 3.70                    # bearing length along the pin, per ear
LUG_HX = BODY_HX + SLOT_GAP + BAR_W + 1.85      # 22.00 from XC (clears Pod 2 on bond_jig by 0.26 mm; 44.0 over tips)
LUG_HY = SLOT_W / 2 + ARM_W                     # 14.20
EAR_TIP_FILLET = 1.45
EAR_SLOPE = (EAR_BOT_Z - EAR_MID_Z) / (LUG_HX - BODY_HX - SLOT_GAP)
EAR_ARC_X = LUG_HX - EAR_TIP_FILLET
EAR_ARC_Z = EAR_BOT_Z - EAR_SLOPE * EAR_TIP_FILLET + EAR_TIP_FILLET * math.hypot(1, EAR_SLOPE)
EAR_TANGENT_X = EAR_ARC_X + EAR_TIP_FILLET * EAR_SLOPE / math.hypot(1, EAR_SLOPE)
BAR_CLEAR = 3.2

# lid snap lips (inside the QuickFit gap between the lug ears)
LIP_ENGAGE = 0.72               # how far the lip reaches in under the cradle edge
LIP_H = 2.30                    # lid tab below Z = 0 (long, shallow lead-in)
HINGE_T = 0.80                  # lid side wall thinned to this in a band under the roof, so the lips can spring
LIP_LEN = 15.0

# ---------------- open-back side-ear clip pod (x6, zero glue — free strap slip) ----------------
POD_SHELL_W = 8.0               # along the band
POD_SHELL_L = 30.2              # covers the 30.0 mm flex paddle; 3.80 mm side blocks outside the 22.6 mm slot
POD_FLOOR_T = 1.26              # skin-to-strap plate across the 17.4 mm open centre
POD_STRAP_W = STRAP_W + 0.60    # 22.60 mm clear between side walls for the 22.0 mm strap
POD_SLOT_H = STRAP_T + 0.30     # 2.15 mm clear slot height so the 1.85 mm strap slides freely as it curves
POD_EAR_T = 1.05                # low-profile C-ear lip thickness at +/-Y edges
POD_EAR_IN = 2.60               # hooks 2.30 mm over each edge of the strap (leaves 17.4 mm open back)
POD_H = POD_FLOOR_T + POD_SLOT_H + POD_EAR_T    # 4.46 mm at the side-ear clips
POD_PIN_HOLE_D = 1.65           # alignment pinholes for bonding jig

SIZES = (145.0, 160.0, 180.0)


# ---------------- derived saddle geometry (module frame, XZ plane) ----------------
def _saddle():
    """Design skin circle and facet line. Returns (zc, z_facet_at_bend, dimple centre (x, z))."""
    phi = POD_TILT
    # facet point behind the pod centre, STANDOFF outside the skin circle, measured along the normal
    xf = (R_DESIGN + STANDOFF) * math.sin(phi)
    # facet passes through (BEND_X, -T_CENTRE) with slope -tan(phi)
    zf = -T_CENTRE - math.tan(phi) * (xf - BEND_X)
    zc = zf - (R_DESIGN + STANDOFF) * math.cos(phi)
    return zc, xf, zf


SKIN_ZC, DIMPLE_X, DIMPLE_Z = _saddle()         # skin circle centre height; dimple centre on the +X facet
SKIN_APEX_Z = SKIN_ZC + R_DESIGN
# Carry the full inclined paddle, then blend the raised seat back into the lug root.
SEAT_OUTER_X = DIMPLE_X + POD_W / 2 * math.cos(POD_TILT) + 0.20
SEAT_BLEND_X = SEAT_OUTER_X + 1.2


def facet_z(x):
    """Cradle underside (plastic) at module X: centre flat, then the pod facets."""
    ax = abs(x)
    if ax <= WEB_HALF_FLAT:
        return -T_WEB
    if ax < BEND_X:
        return -T_WEB + (T_WEB - T_CENTRE) * (ax - WEB_HALF_FLAT) / (BEND_X - WEB_HALF_FLAT)
    blend = max(0.0, min(1.0, (ax - SEAT_OUTER_X) / (SEAT_BLEND_X - SEAT_OUTER_X)))
    return -T_CENTRE - math.tan(POD_TILT) * (ax - BEND_X) + SEAT_RISE * blend


def lug_under_z(x, rounded=True):
    radial = abs(x - XC)
    start = BODY_HX + SLOT_GAP
    if radial <= start:
        root_z = facet_z(XC + math.copysign(BODY_HX, x - XC))
        return root_z + (EAR_MID_Z - root_z) * (radial - BODY_HX) / SLOT_GAP
    if rounded and radial > EAR_TANGENT_X:
        return EAR_ARC_Z - math.sqrt(max(0, EAR_TIP_FILLET**2 - (radial - EAR_ARC_X)**2))
    return EAR_MID_Z + EAR_SLOPE * (radial - start)


def _bar_circle(x):
    r = R_DESIGN + BAR_CLEAR
    return SKIN_ZC + math.sqrt(max(r * r - x * x, 0.0))


def bar_under_z(x):
    """Underside of the slide-in cross-bar (where the sewn nylon loop exits toward Pods 2 / 5)."""
    return BAR_ZC - BAR_H / 2


def tail_path(worn=True, r=0.9):
    """Flex tail length needed from the pod end to its tip inside J1."""
    foam = FOAM_WORN if worn else FOAM_FREE
    z_flex = facet_z(BEND_X) - foam - FLEX_T / 2
    h = (Z_PCB_TOP + J1_SLOT_DZ) - z_flex
    return math.pi * r + (h - 2 * r) + (PCB_Y0 + TAIL_INSERT + POD_L / 2)


if __name__ == '__main__':
    print(f"body {2 * BODY_HX:.1f} x {2 * BODY_HY:.1f} x {Z_TOP + T_WEB:.2f} (centre), over lugs {2 * LUG_HX:.1f}")
    print(f"pod tilt {math.degrees(POD_TILT):.1f} deg, dimple ({DIMPLE_X:.2f}, {DIMPLE_Z:.2f}), skin apex z {SKIN_APEX_Z:.2f}")
    print(f"underside at body edge {facet_z(XC + BODY_HX):.2f} / {facet_z(XC - BODY_HX):.2f}")
    print(f"bar underside {bar_under_z(XC + BODY_HX + SLOT_GAP):.2f} .. {bar_under_z(XC + LUG_HX):.2f}")
    print(f"tail path worn {tail_path(True):.2f}, free {tail_path(False):.2f} (max {TAIL_MAX_L})")
    print(f"top above skin apex {Z_TOP - SKIN_APEX_Z:.2f}")
