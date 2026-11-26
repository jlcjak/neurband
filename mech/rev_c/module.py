"""module.py - neurband rev C compact module: cradle + holder + lid (dimensions in params.py).

cradle   The part against the wrist. Its top (Z = 0) is one flat plane: it is the print bed face
         and the board lies on it. Everything shaped is on the underside, which prints facing up:
         a reinforced centre web over the flex root, two pod facets tilted 13 deg with the foam dimples
         for flex pods 3 and 4, bevelled ends, and two slotted strap lugs that droop with the wrist.
         Four blind key-slots locate the holder. Two end pockets retain its spring tabs.
holder   A slim 1-piece collar printed upside-down (Z = Z_HOLDER on the bed, deck on bed). Two end tabs hold it down while four locating keys provide:
           - a 4-corner +/-0.15 mm centering nest for the main PCB before closing the lid,
           - a flat battery deck at Z = 3.35 mm with an open guard ring around SW1 so the cell
             slides forward over J1/SW1 without ever actuating the button,
           - open chutes for the flex tail (-Y) and battery leads (+X/+Y).
lid      A clean, buttonless tub printed top-down: unbroken flat top with only the status-LED slit,
         internal antenna-keepout fence and cell stops, and two +/-X snap wings that hook under the
         cradle inside the strap slots (so a tight strap locks the whole sandwich shut).

Run: unset DISPLAY WAYLAND_DISPLAY; QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/module.py
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import rc as R
import params as P
import cadutil as U
from lid_mark import lid_inlay

V = FreeCAD.Vector
BOARD_STEP = os.path.join(R.HERE, 'ref', 'neurband_c_parts.step')

XC = P.XC
IN_HX = P.BODY_HX - P.WALL                 # 14.50 inside of the lid/holder walls
LUG_R = 0.40
EAR_SIDE_FILLET = 0.65
EDGE_CHAM = 0.5                            # chamfer on the bars' outer lower edge
RIM_Z_BODY, RIM_Z_LUG = -2.8, -3.5         # below these depths the outline tapers in at 45 deg
ARM_STEP = 0.8                             # lug arms hang this much below the bar: side guides for the strap
END_BEVEL_Y = 15.3                         # underside bevel starts just beyond the flex paddles
END_BEVEL_T = 1.25                         # cradle thickness left at the +/-Y end faces

# tail slot through the cradle (tail rises at y = -15 - r, r = 0.85 -> outer arc at -16.00)
TAIL_R = 0.85
TAIL_SLOT = (-5.5, 5.5, -16.25, -15.30)


# recesses in the top face (bed side; all bridges <= 4.7 mm)
WIRE_TROUGH = (10.9, 13.1, -8.0, 14.2, 1.30)        # battery leads from J2 to the bay behind the board
WIRE_BAY = (10.9, 14.3, 12.6, 15.8, 1.30)           # where the leads turn up beside the cell
J2_POCKET = (8.9, 13.6, -7.7, -3.6, 1.10)           # solder on the two battery pads
J3_POCKET = (9.0, 13.7, -14.4, -12.1, 0.90)
J3_PORT = (10.4, 12.4, -P.BODY_HY + 0.6, -12.1, 0.90)   # charge-lead channel; 0.6 mm skin left at the end face
TP_POCKET = (-13.3, -8.9, 6.7, 11.1, 0.50)

# asymmetric locating slots in cradle (x0, x1, y0, y1) and matching keys on holder (poka-yoke)
KEY_SLOT_DEPTH = 0.75
KEY_DEPTH = 0.65
KEY_CLR = 0.08
HOLDER_KEYS = (
    (-12.4, -8.2, -16.30, -15.10),          # front-left (clear of TAIL_SLOT and dimples)
    (6.4, 9.6, -16.30, -15.10),             # front-right (clear of TAIL_SLOT and J3_PORT)
    (-12.4, -8.2, 13.10, 14.35),            # rear-left (clear of TP_POCKET and dimples)
    (7.6, 10.5, 13.10, 14.35),              # rear-right (clear of WIRE_BAY and dimples; asymmetric to front)
)

# End-wall cantilevers, on opposite corners to resist rocking. Both spring outward.
# The locating keys carry side loads. The tabs carry pull-off loads at the end faces.
HOLDER_CATCHES = ((-10.7, -1), (11.5, 1))
TAB_WIDTH = 4.4
TAB_WALL = 0.85
TAB_RELIEF = 0.45
TAB_ROOT_Z = 2.80
TAB_TIP_Z = -1.52
TAB_LEDGE_Z = -0.62
TAB_GAP = 0.13
TAB_BITE = 0.30

# mid-seam split: holder forms front/rear corners (|Y| >= SPLIT_Y) up to Z_HOLDER;
# lid side wings occupy |Y| <= WING_HY down to Z = -LIP_H inside the strap slots.
SPLIT_Y = 11.05                             # end of the holder corners
WING_HY = 10.90                             # 0.15 mm relief gap to holder at +/-SPLIT_Y
LID_SEAM_Z = P.Z_HOLDER + 0.05              # 3.40: lid rests over holder with 0.05 mm vertical clearance

# holder: PCB nest & battery deck (printed upside-down, Z = Z_HOLDER on the bed)
NEST_X0, NEST_X1 = P.PCB_X0 - P.PCB_CLR, P.PCB_X1 + P.PCB_CLR      # -14.15 .. +14.85
NEST_Y0, NEST_Y1 = P.PCB_Y0 - P.PCB_CLR, P.PCB_Y1 + P.PCB_CLR      # -14.95 .. +12.35
RAIL_L_X = (P.BAT_X0 - 1.10, P.BAT_X0 + 0.85)                      # supports the antenna-side edge of the cell
RAIL_R_X = (13.75, NEST_X1)                                        # +13.75 .. +14.85 (clears all +X passives)
RAIL_Z0 = 2.36                                                     # underside of the reinforced deck
SW1_DECK_X = (7.35, NEST_X1)                                       # bridges over SW1 shoulders
SW1_DECK_Y = (NEST_Y0, -11.15)
SW1_HOLE_X = (9.40, 12.20)                                         # open window around SW1's 1.8 mm cap
SW1_HOLE_Y = (-14.30, -11.50)
SW1_PILLAR_L = (7.35, 8.15, -14.85, -11.30)                        # bare PCB between J1 and SW1
SW1_PILLAR_R = (13.50, NEST_X1, -14.85, -11.00)                    # bare PCB to +X of SW1
TAIL_ARCH_X = (-5.65, 5.65)
TAIL_ARCH_Z = 1.95                                                 # >= 0.30 mm above flex tail arc

# lid: LED slit and baffle (button access removed)
LED_SLIT_X = (P.D1[0] - 0.7, P.D1[0] + 1.5)
LED_SLIT_Y = (10.65, 11.95)
LED_BAFFLE_T = 0.7
LED_BAFFLE_Z = P.Z_HOLDER + 0.15            # stops cleanly above holder/board plane
# lid: internal cell fence and end stops
FENCE_X = (P.BAT_X0 - 1.00, P.BAT_X0 - 0.20)                       # keeps cell 1.65 mm clear of antenna strip
FENCE_Y = (-15.5, 15.5)
FENCE_Z = P.Z_HOLDER + 0.15
LEAD_RELIEF = (12.2, 16.0, 0.45)            # y0, y1, depth: +X wall relief for battery leads beside PCM
HINGE_Z = (5.0, 7.1)                        # thinned flex band in the +/-X walls
SLOT_CROWN_Z = 4.60                        # highest point of the rounded side-wing relief
HINGE_Y = 11.2
PRY_W = 5.0
LIP_Z0 = -0.32                              # where the catch face starts below the seam


def under_body(x):
    return P.facet_z(x)


# ---------------- cradle ----------------
def build_cradle(log=None):
    D = 14.0
    body = R.rrect(2 * P.BODY_HX, 2 * P.BODY_HY, P.PLAN_R, D, -D, XC, 0)
    lug = R.rrect(2 * P.LUG_HX, 2 * P.LUG_HY, LUG_R, D, -D, XC, 0)
    c = body.fuse(lug).removeSplitter()
    c = R.chamfer_edges(c, P.SEAM_CHAM, lambda e: e.BoundBox.ZMin > -1e-6, log, 'cradle top edge')

    # underside: centre flat, two pod facets, and curved wrist-following underside under each lug ear
    xb0, xb1 = XC - P.BODY_HX, XC + P.BODY_HX
    xs0, xs1 = XC - (P.BODY_HX + P.SLOT_GAP), XC + (P.BODY_HX + P.SLOT_GAP)
    xl0, xl1 = XC - P.LUG_HX - 1.0, XC + P.LUG_HX + 1.0
    breaks = (P.WEB_HALF_FLAT, P.BEND_X, P.SEAT_OUTER_X, P.SEAT_BLEND_X)
    facet_x = [-x for x in reversed(breaks)] + list(breaks)
    prof = [(xl0, P.lug_under_z(xl0, False)), (xs0, P.EAR_MID_Z), (xb0, P.facet_z(xb0))]
    prof.extend((x, P.facet_z(x)) for x in facet_x)
    prof.extend([(xb1, P.facet_z(xb1)), (xs1, P.EAR_MID_Z), (xl1, P.lug_under_z(xl1, False))])
    c = c.cut(R.prism_xz(prof + [(xl1, -D - 1), (xl0, -D - 1)], -P.BODY_HY - 1, P.BODY_HY + 1))

    # bevelled ends of the underside (room for the back of the hand when the wrist bends)
    for sy in (1, -1):
        y0, y1 = sy * END_BEVEL_Y, sy * (P.BODY_HY + 1.0)
        z0 = min(under_body(xb0), under_body(xb1)) - 0.3
        slope = (-END_BEVEL_T - z0) / (P.BODY_HY - END_BEVEL_Y)
        z1 = z0 + slope * (P.BODY_HY + 1.0 - END_BEVEL_Y)
        c = c.cut(R.prism_yz([(y0, z0), (y1, z1), (y1, -D - 1), (y0, -D - 1)], xb0 - 1, xb1 + 1))
    c = c.removeSplitter()

    # soften the skin-side rim
    def tapered(hx, hy, r, z_start, k=1.1):
        top = R.rrect(2 * hx, 2 * hy, r, -z_start + 1.0, z_start, XC, 0)
        f0 = R.rrect(2 * hx, 2 * hy, r, 1.0, z_start - 1.0, XC, 0)
        f1 = R.rrect(2 * (hx - k), 2 * (hy - k), r - k, 1.0, z_start - k - 1.0, XC, 0)
        w0 = max((f for f in f0.Faces if abs(f.BoundBox.ZMin - z_start) < 1e-6 and f.BoundBox.ZLength < 1e-6), key=lambda f: f.Area).OuterWire
        w1 = max((f for f in f1.Faces if abs(f.BoundBox.ZMin - (z_start - k)) < 1e-6 and f.BoundBox.ZLength < 1e-6), key=lambda f: f.Area).OuterWire
        return top.fuse(Part.makeLoft([w0, w1], True, True))
    env = tapered(P.BODY_HX, P.BODY_HY, P.PLAN_R, RIM_Z_BODY).fuse(lug)
    c = c.common(env).removeSplitter()

    # QuickFit strap bay between the two lug ears (-SLOT_W/2 .. +SLOT_W/2); inside it the body edge
    # carries the dovetail catch for the lid's +/-X snap wings (centered on +/-LIP_LEN/2)
    for sx in (1, -1):
        xi = XC + sx * (IN_HX - 0.08)
        rec = P.LIP_ENGAGE + 0.25
        xr = XC + sx * (IN_HX - 0.08 - rec)
        x_out = XC + sx * (P.LUG_HX + 1.0)
        zk = LIP_Z0 + 0.05
        # full-width QuickFit bay cut outside the body wall
        xb = XC + sx * P.BODY_HX
        c = c.cut(R.box(min(xb, x_out), max(xb, x_out), -P.SLOT_W / 2, P.SLOT_W / 2, -D - 1, 1.0))
        # dovetail catch recessed into the body edge along the snap-wing span
        pts = [(xi - sx * 0.22, 1.0), (xi - sx * 0.22, 0.0), (xi, -0.22), (xi, zk), (xr, zk - rec * 0.50), (xr, -D - 1),
               (xb + sx * 0.5, -D - 1), (xb + sx * 0.5, 1.0)]
        c = c.cut(R.prism_xz(pts, -P.LIP_LEN / 2 - 0.25, P.LIP_LEN / 2 + 0.25))

        # rectangular cross-bar slot through both lug ears (octagonal chamfered corners -> tiny 2.4 mm bridge on bed)
        xp = XC + sx * (P.BODY_HX + P.PIN_DX)
        hw = P.BAR_W / 2 + P.BAR_CLR
        hh = P.BAR_H / 2 + P.BAR_CLR
        zc = P.BAR_ZC
        ch = 0.45
        s_pts = [
            (xp - hw + ch, zc + hh), (xp + hw - ch, zc + hh), (xp + hw, zc + hh - ch), (xp + hw, zc - hh + ch),
            (xp + hw - ch, zc - hh), (xp - hw + ch, zc - hh), (xp - hw, zc - hh + ch), (xp - hw, zc + hh - ch),
        ]
        c = c.cut(R.prism_xz(s_pts, -P.LUG_HY - 1.0, P.LUG_HY + 1.0))

    # Round the wrist-facing toe in radial section. The cutter is a tangent
    # quarter-round between the sloped underside and the vertical end wall.
    radius = P.EAR_TIP_FILLET
    cx, cz = P.EAR_ARC_X, P.EAR_ARC_Z
    slope = P.EAR_SLOPE
    for sx in (-1, 1):
        y0 = -P.LUG_HY - 1
        x0, x1 = sorted((XC + sx * P.EAR_TANGENT_X,
                         XC + sx * (P.LUG_HX + 1)))
        corner = R.box(x0, x1, y0, -y0, -D, cz)
        roll = Part.makeCylinder(radius, -2 * y0, V(XC + sx * cx, y0, cz), V(0, 1, 0))
        c = c.cut(corner.cut(roll))
    c = c.removeSplitter()
    # Round both edges across each ear where its wrist surface meets the sides.
    for sx in (-1, 1):
        along = V(sx, 0, slope)
        along.normalize()
        normal = V(-sx * slope, 0, 1)
        normal.normalize()
        for sy in (-1, 1):
            for y_edge, inward in ((sy * P.LUG_HY, -sy), (sy * P.SLOT_W / 2, sy)):
                origin = V(XC + sx * P.BODY_HX, y_edge, P.EAR_MID_Z - slope * P.SLOT_GAP)
                def point(y, z):
                    return origin + V(0, inward * y, 0) + normal * z
                r = EAR_SIDE_FILLET
                corners = [point(-1, -D), point(r, -D), point(r, 0)]
                arc = Part.Arc(corners[-1], point(r * (1 - 2**-0.5), r * (1 - 2**-0.5)),
                               point(0, r)).toShape()
                rest = [point(0, r), point(-1, r), corners[0]]
                edges = Part.makePolygon(corners).Edges + [arc] + Part.makePolygon(rest).Edges
                cutter = Part.Face(Part.Wire(edges)).extrude(along * (P.LUG_HX - P.BODY_HX + 2))
                c = c.cut(cutter)

    # foam dimples on the two pod facets (cut square to the facet)
    for sx in (1, -1):
        nx, nz = sx * math.sin(P.POD_TILT), math.cos(P.POD_TILT)
        for y in P.PAD_Y:
            p = V(sx * P.DIMPLE_X - nx * 2.0, y, P.DIMPLE_Z - nz * 2.0)
            c = c.cut(Part.makeCylinder(P.FOAM_POCKET_D / 2, 2.0 + P.FOAM_POCKET_H, p, V(nx, 0, nz)))

    # flex tail slot
    x0, x1, y0, y1 = TAIL_SLOT
    c = c.cut(R.box(x0, x1, y0, y1, -D, 1.0))
    c = c.cut(R.prism_yz([(y1 - 0.01, -P.T_WEB - 0.1), (y1 + 0.55, -P.T_WEB - 0.1), (y1 - 0.01, -P.T_WEB + 0.46)], x0, x1))

    # recesses in the top face (wire routing, solder pockets, test pads)
    for x0, x1, y0, y1, dz in (WIRE_TROUGH, WIRE_BAY, J2_POCKET, J3_POCKET, J3_PORT, TP_POCKET):
        c = c.cut(R.box(x0, x1, y0, y1, -dz, 1.0))

    # asymmetric locating slots for the snap-in board-centering holder
    for x0, x1, y0, y1 in HOLDER_KEYS:
        c = c.cut(R.box(x0, x1, y0, y1, -KEY_SLOT_DEPTH, 1.0))

    for x, sy in HOLDER_CATCHES:
        # Leave the ledge at the entrance and a pocket below it for the tooth.
        lip = P.BODY_HY - TAB_WALL - TAB_GAP
        pocket = lip - TAB_BITE - TAB_GAP
        end = P.BODY_HY + 1
        profile = [(end, 0.2), (lip - 0.22, 0.2), (lip - 0.22, 0),
                   (lip, -0.22), (lip, TAB_LEDGE_Z), (pocket, TAB_LEDGE_Z - 0.20),
                   (pocket, -D), (end, -D)]
        c = c.cut(R.prism_yz([(sy*y, z) for y, z in profile],
                             x - TAB_WIDTH/2 - TAB_GAP, x + TAB_WIDTH/2 + TAB_GAP))
    return c.removeSplitter()


# ---------------- holder (board-centering collar + SW1 guard + battery deck) ----------------
def build_holder(log=None):
    """Printed with the battery deck on the bed and the spring tab tips facing up."""
    # solid outer envelope from Z = 0 to Z = Z_HOLDER, trimmed to the front & rear ends (|Y| >= SPLIT_Y)
    shell = R.rrect(2 * P.BODY_HX, 2 * P.BODY_HY, P.PLAN_R, P.Z_HOLDER, 0.0, XC, 0)
    shell = R.chamfer_edges(shell, P.SEAM_CHAM, lambda e: e.BoundBox.ZMax < 1e-6, log, 'holder bottom edge')
    ends = shell.cut(R.box(XC - P.BODY_HX - 1.0, XC + P.BODY_HX + 1.0, -SPLIT_Y, SPLIT_Y, -1.0, P.Z_HOLDER + 1.0))

    # carve the 4-corner PCB nest (-14.15..+14.85 x -14.95..+12.35) + 0.45 mm 45-deg self-centering lead-in funnel at Z=0..0.45
    h = ends.cut(R.box(NEST_X0, NEST_X1, NEST_Y0, NEST_Y1, -1.0, P.Z_HOLDER + 1.0))
    wf0 = Part.makePolygon([V(NEST_X0 - 0.45, NEST_Y0 - 0.45, 0.0), V(NEST_X1 + 0.45, NEST_Y0 - 0.45, 0.0),
                            V(NEST_X1 + 0.45, NEST_Y1 + 0.45, 0.0), V(NEST_X0 - 0.45, NEST_Y1 + 0.45, 0.0),
                            V(NEST_X0 - 0.45, NEST_Y0 - 0.45, 0.0)])
    wf1 = Part.makePolygon([V(NEST_X0, NEST_Y0, 0.45), V(NEST_X1, NEST_Y0, 0.45),
                            V(NEST_X1, NEST_Y1, 0.45), V(NEST_X0, NEST_Y1, 0.45), V(NEST_X0, NEST_Y0, 0.45)])
    funnel = Part.makeLoft([wf0, wf1], True, True).fuse(R.box(NEST_X0 - 0.45, NEST_X1 + 0.45, NEST_Y0 - 0.45, NEST_Y1 + 0.45, -1.0, 0.01))
    # keep funnel clear of the four locating keys
    for x0, x1, y0, y1 in HOLDER_KEYS:
        funnel = funnel.cut(R.box(x0 - 0.1, x1 + 0.1, y0 - 0.1, y1 + 0.1, -1.5, 1.0))
    h = h.cut(funnel)
    h = h.cut(R.box(P.BAT_X0 - 0.15, P.BAT_X0 + P.BAT_W + 0.15, NEST_Y1 - 0.1, 15.70, 2.30, P.Z_HOLDER + 1.0))

    # open flex-tail tunnel inside the front bar (keeps outer -Y wall solid down to Z = 0; deck above Z = TAIL_ARCH_Z)
    h = h.cut(R.box(TAIL_ARCH_X[0], TAIL_ARCH_X[1], -P.IN_HY, NEST_Y0 + 0.1, -1.0, TAIL_ARCH_Z))

    # open rear-right battery wire chute inside the rear bar (keeps outer +Y and +X walls solid)
    h = h.cut(R.box(10.75, NEST_X1 + 0.01, NEST_Y1 - 0.1, P.IN_HY - 0.20, -1.0, P.Z_HOLDER + 1.0))

    # longitudinal battery-support rails + mid crossbar (all flat on Z = Z_HOLDER print bed; clear of J1 & U1)
    rails = R.box(RAIL_L_X[0], RAIL_L_X[1], -P.IN_HY + 0.05, P.IN_HY - 0.05, RAIL_Z0, P.Z_HOLDER)
    rails = rails.fuse(R.box(RAIL_R_X[0], RAIL_R_X[1], -P.IN_HY + 0.05, NEST_Y1 + 0.10, RAIL_Z0, P.Z_HOLDER))
    rails = rails.fuse(R.box(RAIL_L_X[0], RAIL_R_X[1], 4.50, 8.50, RAIL_Z0, P.Z_HOLDER))
    rails = rails.cut(R.box(-7.35, 7.35, -14.95, -9.50, 0.0, 3.12))   # clear J1 housing (ZMax = 3.014)
    rails = rails.fuse(R.box(12.85, RAIL_R_X[1], -11.5, 9.2, RAIL_Z0, P.Z_HOLDER))
    rails = rails.fuse(R.box(RAIL_L_X[0], RAIL_R_X[1], -6.0, -3.5, RAIL_Z0, P.Z_HOLDER))
    # Keep the rear of the deck open below a cell installed with its protection board down.
    rails = rails.cut(R.box(P.BAT_X0, P.BAT_X0 + P.BAT_W,
                            P.BAT_Y0 + P.BAT_L - P.BAT_PCM_L - 0.15, P.IN_HY,
                            RAIL_Z0 - 0.05, P.Z_HOLDER + 0.05))
    h = h.fuse(rails)

    # SW1 protective deck + flanking load-bearing pillars onto bare PCB (0.34 mm clearance over SW1 cap)
    sw_deck = R.box(SW1_DECK_X[0], SW1_DECK_X[1], SW1_DECK_Y[0] - 0.2, SW1_DECK_Y[1], 2.65, P.Z_HOLDER)
    sw_deck = sw_deck.cut(R.box(SW1_HOLE_X[0], SW1_HOLE_X[1], SW1_HOLE_Y[0], SW1_HOLE_Y[1], 2.0, P.Z_HOLDER + 1.0))
    h = h.fuse(sw_deck)
    for x0, x1, y0, y1 in (SW1_PILLAR_L, SW1_PILLAR_R):
        h = h.fuse(R.box(x0, x1, y0, y1, P.PCB_T + 0.10, P.Z_HOLDER))

    # four asymmetric locating keys in the cradle slots
    for x0, x1, y0, y1 in HOLDER_KEYS:
        h = h.fuse(R.box(x0 + KEY_CLR, x1 - KEY_CLR, y0 + KEY_CLR, y1 - KEY_CLR, -KEY_DEPTH, 0.05))

    for x, sy in HOLDER_CATCHES:
        y_outer = P.BODY_HY
        y_inner = y_outer - TAB_WALL
        x0, x1 = x - TAB_WIDTH / 2, x + TAB_WIDTH / 2
        ys = sorted((sy*(y_inner - TAB_RELIEF), sy*(y_outer + 1)))
        h = h.cut(R.box(x0 - TAB_RELIEF, x1 + TAB_RELIEF, *ys, -0.01, TAB_ROOT_Z))
        tooth = y_inner - TAB_GAP - TAB_BITE
        profile = [(y_outer, TAB_ROOT_Z + 0.10), (y_inner - 0.28, TAB_ROOT_Z + 0.10),
                   (y_inner - 0.28, TAB_ROOT_Z), (y_inner, TAB_ROOT_Z - 0.65),
                   (y_inner, TAB_LEDGE_Z - 0.10), (tooth, TAB_LEDGE_Z - 0.34),
                   (tooth, TAB_LEDGE_Z - 0.48), (y_inner, TAB_TIP_Z),
                   (y_outer - 0.22, TAB_TIP_Z), (y_outer, TAB_TIP_Z + 0.22)]
        h = h.fuse(R.prism_yz([(sy*y, z) for y, z in profile], x0, x1))
    return h.removeSplitter()


# ---------------- lid ----------------
def _lid_outer():
    s = R.rrect(2 * P.BODY_HX, 2 * P.BODY_HY, P.PLAN_R, P.Z_TOP, 0.0, XC, 0)
    s = R.chamfer_edges(s, P.TOP_CHAM, lambda e: e.BoundBox.ZMin > P.Z_TOP - 1e-6)
    return s


def _lid_cavity():
    return R.rrect(2 * IN_HX, 2 * P.IN_HY, P.PLAN_R - P.WALL, P.Z_ROOF + 1.0, -1.0, XC, 0)


def build_lid(log=None):
    l = _lid_outer().cut(_lid_cavity())
    roof0 = P.Z_ROOF

    # step the front & rear ends up to LID_SEAM_Z (resting over holder); +/-X snap wings stay full height
    l = l.cut(R.box(XC - P.BODY_HX - 1.0, XC + P.BODY_HX + 1.0, -P.BODY_HY - 1.0, -WING_HY, -1.0, LID_SEAM_Z))
    l = l.cut(R.box(XC - P.BODY_HX - 1.0, XC + P.BODY_HX + 1.0, WING_HY, P.BODY_HY + 1.0, -1.0, LID_SEAM_Z))

    # snap lips: the +/-X side wings continue below Z = 0 inside the strap slots and hook under the cradle edge
    for sx in (1, -1):
        xo, xi = XC + sx * P.BODY_HX, XC + sx * IN_HX
        e = P.LIP_ENGAGE
        pts = [(xo, 0.05), (xi, 0.05), (xi, LIP_Z0), (xi - sx * e, LIP_Z0 - e * 0.50), (xi - sx * e, LIP_Z0 - e * 0.50 - 0.20),
               (xi + sx * 0.05, -P.LIP_H), (xo - sx * 0.35, -P.LIP_H), (xo, -P.LIP_H + 0.35)]
        l = l.fuse(R.prism_xz(pts, -P.LIP_LEN / 2, P.LIP_LEN / 2))
        # Slits isolate the hook from the stiff end walls while the roof carries its root.
        for sy in (-1, 1):
            y = sy * (P.LIP_LEN / 2 + 0.30)
            xs = sorted((xi - sx * 0.1, xo + sx * 0.1))
            root_z = SLOT_CROWN_Z - 0.30
            slit = R.box(*xs, y - 0.30, y + 0.30, -0.1, root_z)
            crown = Part.makeCylinder(0.30, xs[1] - xs[0], V(xs[0], y, root_z), V(1, 0, 0))
            l = l.cut(slit.fuse(crown))
        d = P.WALL - P.HINGE_T
        z0, z1 = HINGE_Z
        groove = [(xi - sx * 0.01, z0 - d - 0.01), (xi + sx * d, z0), (xi + sx * d, z1), (xi - sx * 0.01, z1 + d + 0.01)]
        l = l.cut(R.prism_xz(groove, -HINGE_Y, HINGE_Y))

    # room for the battery leads to come up beside the cell PCM
    ly0, ly1, ld = LEAD_RELIEF
    l = l.cut(R.box(XC + IN_HX - 0.01, XC + IN_HX + ld, ly0, ly1, LID_SEAM_Z - 0.1, roof0))

    # cell fence on the antenna side (keeps cell 1.65 mm clear of the printed antenna strip)
    l = l.fuse(R.box(FENCE_X[0], FENCE_X[1], FENCE_Y[0], FENCE_Y[1], FENCE_Z, roof0 + 0.2))

    # subtle end-stop ribs on the roof to keep the cell centred along Y
    l = l.fuse(R.box(-4.0, 10.0, -P.IN_HY - 0.05, P.BAT_Y0 - 0.20, P.Z_HOLDER + 0.30, roof0 + 0.2))
    l = l.fuse(R.box(-4.0, 9.5, P.BAT_Y0 + P.BAT_L + 0.25, P.IN_HY + 0.05, P.Z_HOLDER + 0.30, roof0 + 0.2))

    # LED slit with a baffle down to just above the holder plane
    bt = LED_BAFFLE_T
    bx0, bx1, by0, by1 = LED_SLIT_X[0] - bt, LED_SLIT_X[1] + bt, LED_SLIT_Y[0] - bt, LED_SLIT_Y[1] + bt
    l = l.fuse(R.box(bx0, bx1, by0, by1, LED_BAFFLE_Z, roof0 + 0.2))
    lr = (LED_SLIT_Y[1] - LED_SLIT_Y[0]) / 2
    ly = (LED_SLIT_Y[0] + LED_SLIT_Y[1]) / 2
    slit = R.box(LED_SLIT_X[0] + lr, LED_SLIT_X[1] - lr, LED_SLIT_Y[0], LED_SLIT_Y[1], LED_BAFFLE_Z - 1.0, P.Z_TOP + 1.0)
    for x in (LED_SLIT_X[0] + lr, LED_SLIT_X[1] - lr):
        slit = slit.fuse(Part.makeCylinder(lr, P.Z_TOP + 2.0 - LED_BAFFLE_Z, V(x, ly, LED_BAFFLE_Z - 1.0)))
    l = l.cut(slit)

    # pry notch in the +Y end wall right at the mid-seam
    l = l.cut(R.prism_yz([(P.BODY_HY + 0.1, LID_SEAM_Z - 0.1), (P.BODY_HY - 0.65, LID_SEAM_Z - 0.1),
                          (P.BODY_HY + 0.1, LID_SEAM_Z + 0.65)], XC - PRY_W / 2, XC + PRY_W / 2))
    return l.removeSplitter()


def lid_materials(envelope):
    blue = lid_inlay()
    shell = envelope.cut(blue).removeSplitter()
    assert shell.isValid() and len(shell.Solids) == 1 and blue.isValid()
    assert abs(shell.Volume + blue.Volume - envelope.Volume) < 1e-4
    return [('lid', shell, R.C_LID), ('blue_inlay', blue, R.C_INLAY)]


# ---------------- what goes inside ----------------
def board_real():
    sh = Part.read(BOARD_STEP)
    sols = list(sh.Solids)
    pcb = max(sols, key=lambda s: s.BoundBox.XLength * s.BoundBox.YLength if s.BoundBox.ZLength < P.PCB_T + 0.1 else 0)
    bb = pcb.BoundBox
    dx, dy, dz = -(bb.XMin + P.J1_KX), P.PCB_Y0 - bb.YMin, -bb.ZMin
    out = []
    for s in sols:
        sc = s.copy()
        sc.translate(V(dx, dy, dz))
        out.append(sc)
    ip = sols.index(pcb)
    return out[ip], Part.makeCompound([s for k, s in enumerate(out) if k != ip])


BAT_Z0 = P.Z_HOLDER + 0.03                  # rests flat on holder's Z = 3.35 mm deck (0.37 mm above SW1 cap)
BAT_TILT = 0.0


def battery_solids():
    """Flat cell body on holder deck, plus the protection-board bump on either face (both are clash-checked)."""
    y0, y1 = P.BAT_Y0, P.BAT_Y0 + P.BAT_L
    z0 = BAT_Z0
    x0, x1 = P.BAT_X0, P.BAT_X0 + P.BAT_W
    body = R.box(x0, x1, y0, y1, z0, z0 + P.BAT_T)
    body = R.fillet_edges(body, 1.0, lambda e: e.BoundBox.ZLength > P.BAT_T - 0.01)
    bump = P.BAT_PCM_T - P.BAT_T
    up = R.box(x0 + 0.3, x1 - 0.3, y1 - P.BAT_PCM_L, y1 - 0.2, z0 + P.BAT_T, z0 + P.BAT_T + bump)
    down = R.box(x0 + 0.3, x1 - 0.3, y1 - P.BAT_PCM_L, y1 - 0.2, z0 - bump, z0)
    return body, up, down


def tail_shape(r=TAIL_R):
    t, w = P.TAIL_T, P.TAIL_W
    y_root = -P.POD_L / 2
    z0 = P.facet_z(P.BEND_X) - P.FOAM_WORN - P.FLEX_T / 2
    z1 = P.PCB_T + P.J1_SLOT_DZ
    yr = y_root - r

    def arc(cy, cz, a0, a1):
        ring = Part.makeCylinder(r + t / 2, w, V(-w / 2, cy, cz), V(1, 0, 0)).cut(
            Part.makeCylinder(r - t / 2, w, V(-w / 2, cy, cz), V(1, 0, 0)))
        L = 3 * r
        pts = [V(-w / 2, cy, cz)] + [V(-w / 2, cy + L * math.cos(math.radians(a)), cz + L * math.sin(math.radians(a)))
                                     for a in (a0, (a0 + a1) / 2, a1)] + [V(-w / 2, cy, cz)]
        return ring.common(Part.Face(Part.makePolygon(pts)).extrude(V(w, 0, 0)))

    y_in = P.PCB_Y0 + P.TAIL_INSERT
    segs = [arc(y_root, z0 + r, 180, 270),
            R.box(-w / 2, w / 2, yr - t / 2, yr + t / 2, z0 + r, z1 - r),
            arc(y_root, z1 - r, 90, 180),
            R.box(-w / 2, w / 2, y_root, y_in, z1 - t / 2, z1 + t / 2)]
    return segs[0].fuse(segs[1:]).removeSplitter(), P.tail_path(True, r)


def wires_visual():
    """Battery leads: J2 -> trough under the board -> bay -> up beside the cell (two 1.0 mm wires)."""
    out = []
    for k, (jx, jy) in enumerate(P.J2):
        xw = WIRE_TROUGH[0] + 0.55 + 1.1 * k
        zt = -WIRE_TROUGH[4] + 0.56
        pts = [V(jx, jy, -0.55), V(xw, jy + 2.2, -0.55), V(xw, jy + 3.6, zt), V(xw, 12.6, zt),
               V(12.6 + 0.9 * k, 13.5 + 1.1 * k, zt), V(13.2 + 0.7 * k, 13.7 + 1.1 * k, 1.0),
               V(14.3, 13.7 + 1.2 * k, 3.6), V(14.3, 13.7 + 1.2 * k, 5.2)]
        for a, b in zip(pts, pts[1:]):
            d = b.sub(a)
            out.append(Part.makeCylinder(0.5, d.Length, a, d))
            out.append(Part.makeSphere(0.5, b))
    return Part.makeCompound(out)


def build_lug_bar(log=None):
    """100% 3D-printed slide-in strap cross-bar (x2). Prints FLAT on the bed (Z = 0..BAR_H, 0 deg overhang!)
    so continuous filament perimeters run end-to-end along its length.
    Has an external T-head stop at -Y and a pinch-release split snap-barb at +Y — zero metal hardware needed!"""
    hw, hh = P.BAR_W / 2, P.BAR_H / 2
    y_head1 = -P.LUG_HY
    y_head0 = y_head1 - 0.70
    y_ear_out = P.LUG_HY + 0.08
    y_tip = P.LUG_HY + 1.35
    ch = 0.40
    # Main shaft with octagonal chamfered edges (slides smoothly through sewn nylon loop & lug slots)
    prof = [
        (-hw + ch, hh), (hw - ch, hh), (hw, hh - ch), (hw, -hh + ch),
        (hw - ch, -hh), (-hw + ch, -hh), (-hw, -hh + ch), (-hw, hh - ch),
    ]
    shaft = R.prism_xz(prof, y_head1 - 0.15, y_tip)
    # The head bears on the full end face so the slot needs no counterbore.
    hw_hd = hw + 0.50
    head = R.prism_xz([
        (-hw_hd + ch * 0.5, hh), (hw_hd - ch * 0.5, hh), (hw_hd, hh - ch * 0.5), (hw_hd, -hh + ch * 0.5),
        (hw_hd - ch * 0.5, -hh), (-hw_hd + ch * 0.5, -hh), (-hw_hd, -hh + ch * 0.5), (-hw_hd, hh - ch * 0.5),
    ], y_head0, y_head1)
    bar = shaft.fuse(head)
    # Self-locking split snap-barb at +Y (lies in XY plane -> prints flat with 0 deg overhang!)
    barb_d = 0.42
    for sx in (1, -1):
        b_pts = [
            V(sx * (hw - 0.45), y_ear_out, -hh + ch),
            V(sx * (hw + barb_d), y_ear_out + 0.28, -hh + ch),
            V(sx * (hw - 0.45), y_tip, -hh + ch),
        ]
        bar = bar.fuse(Part.Face(Part.makePolygon(b_pts + [b_pts[0]])).extrude(V(0, 0, 2 * (hh - ch))))
    # Centre flex-slit at the +Y end so the two barbs pinch inward smoothly during insertion/removal
    bar = bar.cut(R.box(-0.42, 0.42, P.SLOT_W / 2 + 0.3, y_tip + 0.5, -hh - 0.5, hh + 0.5))
    # Shift Z so when lying flat in print frame its bottom is Z = 0; here return centred at Z = 0
    return bar.removeSplitter()


def lug_pins_visual():
    """Two printed slide-in cross-bars seated in the cradle's +/-X lug ears."""
    b0 = build_lug_bar()
    bars = []
    for sx in (1, -1):
        c = b0.copy()
        xp = XC + sx * (P.BODY_HX + P.PIN_DX)
        c.translate(V(xp, 0, P.BAR_ZC))
        bars.append(c)
    return Part.makeCompound(bars)


def min_wall(shape, pts_dirs):
    """Thickness of the part along a ray from each probe point (inside or on the surface)."""
    out = []
    for (x, y, z), (dx, dy, dz) in pts_dirs:
        ln = Part.makeLine(V(x, y, z), V(x + dx * 30, y + dy * 30, z + dz * 30))
        try:
            seg = shape.common(ln)
            out.append(round(sum(e.Length for e in seg.Edges), 2))
        except Exception:
            out.append(-1)
    return out


if not getattr(sys, 'neurband_lib', False):
    log = R.Log('module')
    cradle = U.check(build_cradle(log), 'cradle', log)
    holder = U.check(build_holder(log), 'holder', log)
    lid = U.check(build_lid(log), 'lid', log)
    lug_bar = U.check(build_lug_bar(log), 'lug_bar', log)
    pcb, parts = board_real()
    bat, pcm_up, pcm_down = battery_solids()
    tail, tail_len = tail_shape()
    wires = wires_visual()

    pins = lug_pins_visual()
    checks = dict(
        cradle_vs_holder=R.clash(cradle, holder),
        cradle_vs_lid=R.clash(cradle, lid),
        holder_vs_lid=R.clash(holder, lid),
        pins_vs_cradle=R.clash(pins, cradle),
        pcb_vs_cradle=R.clash(pcb, cradle), pcb_vs_holder=R.clash(pcb, holder), pcb_vs_lid=R.clash(pcb, lid),
        parts_vs_cradle=R.clash(parts, cradle), parts_vs_holder=R.clash(parts, holder), parts_vs_lid=R.clash(parts, lid),
        bat_vs_holder=R.clash(bat, holder), bat_vs_lid=R.clash(bat, lid), bat_vs_parts=R.clash(bat, parts), bat_vs_pcb=R.clash(bat, pcb),
        pcm_up_vs_lid=R.clash(pcm_up, lid), pcm_down_vs_holder=R.clash(pcm_down, holder),
        pcm_down_vs_board=R.clash(pcm_down, pcb) + R.clash(pcm_down, parts),
        tail_vs_cradle=R.clash(tail, cradle), tail_vs_holder=R.clash(tail, holder), tail_vs_lid=R.clash(tail, lid), tail_vs_pcb=R.clash(tail, pcb),
        wires_vs_cradle=R.clash(wires, cradle), wires_vs_holder=R.clash(wires, holder),
        wires_vs_pcb=R.clash(wires, pcb), wires_vs_lid=R.clash(wires, lid), wires_vs_bat=R.clash(wires, bat),
    )
    bb_c, bb_h, bb_l = (shape.optimalBoundingBox(False) for shape in (cradle, holder, lid))
    log(f"  cradle: {bb_c.XLength:.1f} x {bb_c.YLength:.1f} x {bb_c.ZLength:.2f}   "
        f"holder: {bb_h.XLength:.1f} x {bb_h.YLength:.1f} x {bb_h.ZLength:.2f}   "
        f"lid: {bb_l.XLength:.1f} x {bb_l.YLength:.1f} x {bb_l.ZLength:.2f}")
    log(f"  module: body {2 * P.BODY_HX:.1f} x {2 * P.BODY_HY:.1f}, {2 * P.LUG_HX:.1f} over the lugs, "
        f"{P.Z_TOP + P.T_WEB:.2f} thick at the centre, top {P.Z_TOP - P.SKIN_APEX_Z:.2f} above the design skin")
    log(f"  cell: flat at Z={BAT_Z0:.2f}..{BAT_Z0 + P.BAT_T:.2f} (PCM top {BAT_Z0 + P.BAT_PCM_T:.2f}), "
        f"roof at {P.Z_ROOF:.2f}; SW1 clearance {BAT_Z0 - 3.014:.2f}; antenna gap {P.BAT_X0 - P.ANT_X1:.2f}")
    log(f"  flex tail: needs {tail_len:.2f} worn / {P.tail_path(False, TAIL_R):.2f} unloaded (fabricated {P.TAIL_MAX_L:.2f})")
    probes = [((9.1, 0.0, -0.01), (0, 0, -1)), ((12.3, 0.0, -WIRE_TROUGH[4] - 0.01), (0, 0, -1)), ((11.3, 0.0, -WIRE_TROUGH[4] - 0.01), (0, 0, -1)),
              ((0.0, 0.0, -0.01), (0, 0, -1)), ((10.0, -13.0, -J3_POCKET[4] - 0.01), (0, 0, -1)), ((-11.0, 9.0, -TP_POCKET[4] - 0.01), (0, 0, -1)),
              ((-10.3, -15.7, -KEY_SLOT_DEPTH - 0.01), (0, 0, -1)), ((9.0, 13.7, -KEY_SLOT_DEPTH - 0.01), (0, 0, -1)),
              ((XC + P.BODY_HX + P.PIN_DX, P.SLOT_W / 2 + 1.5, P.BAR_ZC + P.BAR_H / 2 + P.BAR_CLR + 0.02), (0, 0, 1)),
              ((XC + P.BODY_HX + P.PIN_DX, P.SLOT_W / 2 + 1.5, P.BAR_ZC - P.BAR_H / 2 - P.BAR_CLR - 0.02), (0, 0, -1))]
    names = ['under dimple', 'under wire trough', 'trough over dimple edge', 'centre web', 'under J3 pocket',
             'under TP pocket', 'under front key', 'under rear key', 'ear above bar', 'ear below bar']
    log("  cradle thickness: " + ', '.join(f"{n} {v}" for n, v in zip(names, min_wall(cradle, probes))))
    log(f"  clash mm3: {json.dumps(checks)}")

    R.save('cradle', [('cradle', cradle, R.C_CRADLE)], log)
    R.save('holder', [('holder', holder, R.C_HOLDER)], log)
    lid_parts = lid_materials(lid)
    R.save('lid', lid_parts, log)
    R.save('lug_bar', [('lug_bar', lug_bar, R.C_CRADLE)], log)
    def lift(sh, dz):
        c = sh.copy()
        c.translate(V(0, 0, dz))
        return c
    R.save('module_exploded', [
        ('cradle', cradle, R.C_CRADLE),
        ('main_board', lift(pcb, 7), R.C_PCB), ('board_parts', lift(parts, 7), R.C_PARTS),
        ('holder', lift(holder, 14), R.C_HOLDER),
        ('lipo', lift(bat, 21), R.C_LIPO), ('lipo_pcm', lift(pcm_up, 21), R.C_PCM),
        *((name, lift(shape, 30), color) for name, shape, color in lid_parts),
    ], log)
    R.save('module_assy', [
        ('cradle', cradle, R.C_CRADLE), ('holder', holder, R.C_HOLDER), *lid_parts,
        ('lug_bars', pins, R.C_HOLDER),
        ('main_board', pcb, R.C_PCB), ('board_parts', parts, R.C_PARTS),
        ('lipo', bat, R.C_LIPO), ('lipo_pcm', pcm_up, R.C_PCM), ('leads', wires, R.C_WIRE),
        ('tail', tail, R.C_FLEX),
    ], log)
    R.finish(log)
