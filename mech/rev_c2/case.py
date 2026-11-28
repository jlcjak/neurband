"""case.py - neurband rev C2 module: tub + lid + printed strap bars (dimensions in params.py).

tub   The one structural part. Prints upright, standing on its six electrode pads, without supports.
        outside  flat wrist side: two runners with three raised pads each (flex paddles 3 and 4),
                 45 deg bevels up to the walls, four strap lugs at mid height with the bar tunnels.
        inside   the board drops between the walls and four stop faces; two wedge lips hold its
                 J1 edge down; battery shelf A (-Y, beside SW1) and shelf B (+Y, under the
                 protection board); wire trough and solder pockets in the floor; tail chimney.
lid   Flat cap printed top down. A lip inside each long wall carries two pegs. The lid goes on 1.3 mm
      toward the elbow, slides toward the hand and clicks: the four pegs sit under ledges in the long
      walls, right behind the lugs, and a bump on each lip sits in a dimple of a wall strip that works
      as the spring. Peg tops and ledge undersides are 45 deg faces, so neither part has an unsupported
      overhang where they meet. Inside: cell fence, two cell ribs, two board feet, LED slit with baffle.
bar   Printed strap cross-bar (x2), flat on the bed: head at -Y, split snap barb at +Y.

Run: unset DISPLAY WAYLAND_DISPLAY; QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c2/case.py
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import c2 as R
import params as P
from lid_mark import lid_inlay

V = FreeCAD.Vector
XC = P.XC
BOARD_STEP = os.path.join(R.HERE, 'ref', 'neurband_c_parts.step')
NEST_Y0, NEST_Y1 = P.PCB_Y0 - P.PCB_CLR, P.PCB_Y1 + P.PCB_CLR          # -13.45 .. +13.85
WX0, WX1 = XC - P.IN_HX, XC + P.IN_HX                                   # inner faces of the long walls
RIM_HX = P.IN_HX - P.LIP_CLR                                            # outside of the lid lips
RIM_Y = (-(P.IN_HY - (P.PLAN_R - P.WALL)), P.IN_HY - (P.PLAN_R - P.WALL) - P.LID_SLIDE)   # lid lips: -15.2 .. +13.9
LUG_SLOPE = 1.0 / math.tan(math.radians(P.LUG_UNDER_DEG))               # rise per mm of reach
BAR_HW, BAR_HH, BAR_CH = P.BAR_W / 2 + P.BAR_CLR, P.BAR_H / 2 + P.BAR_CLR, 0.45
LIP_Y = (NEST_Y0, 0.45)                                                  # wedge lips over the J1 edge of the board
LIP_X = ((P.BLOCK_A_X0, 8.15), (13.45, WX1))
STOP_Z = 5.0                                                             # top of the cell end stops
STOP_B_X = (P.BAT_X0 + 0.3, P.BAT_X0 + 5.3)                              # +Y stop: away from where the leads leave the cell
RIB_Y = (-12.0, -7.0)                                                    # cell ribs under the lid
RIB_Z = P.Z_SHELF_A + 0.03 + P.BAT_T + 0.20
FOOT_Z = P.PCB_T + 0.15
FOOT_FENCE = (P.FENCE_X[0], P.FENCE_X[1], P.PCB_Y1 - 2.5, P.PCB_Y1 - 1.6)       # between the nRF's pins and shelf B
FOOT_EDGE = (13.85, XC + RIM_HX, P.PCB_Y1 - 5.1, P.PCB_Y1 - 3.1)
FENCE_Y = (-15.2, 14.7)
SLOT_CLR = 0.15                                                          # pegs in their slots, along the slide and below
LEDGE_CLR = 0.25                                                         # how far the closed lid can lift before the pegs meet the ledges
LEDGE_LEAD = 0.30                                                        # lead-in on the entry edge of each ledge


# ---------------- tub ----------------
def lug_profile():
    """Lug section in (reach beyond the wall, Z)."""
    x1, zt = P.LUG_X, P.LUG_TOP_Z
    return [(-0.4, P.Z_WALL0 - 0.4 * LUG_SLOPE), (x1, P.Z_WALL0 + x1 * LUG_SLOPE), (x1, zt - 0.8), (x1 - 0.8, zt),
            (0.15, zt), (0.15, P.Z_SEAM), (-0.4, P.Z_SEAM)]


def peg_slots(sx):
    """L slots in one long wall: the lid's pegs drop in from the top, then slide toward -Y under the ledge.
    The underside of the ledge rises at 45 deg toward the cavity, parallel to the tops of the pegs, so it
    prints without support; its entry edge is cut back as a lead-in."""
    xw = XC + sx * P.IN_HX
    xa, xb = xw - sx * 0.05, xw + sx * P.SLOT_DEPTH
    z0 = P.PEG_Z[0] - SLOT_CLR
    zc = P.PEG_Z[1] + LEDGE_CLR - P.LIP_CLR                # ledge underside at the inner face of the wall
    za, zb = zc + 0.05, zc - P.SLOT_DEPTH                  # ... at xa and at xb
    out = []
    for y0 in P.PEG_Y:
        y_led = y0 + P.LID_SLIDE - SLOT_CLR                # the ledge ends here and the entry shaft begins
        y_end = y0 + P.PEG_L + P.LID_SLIDE + SLOT_CLR
        out.append(R.prism_xz([(xa, z0), (xb, z0), (xb, zb), (xa, za)], y0 - SLOT_CLR, y_end))
        out.append(R.box(min(xa, xb), max(xa, xb), y_led, y_end, z0, P.Z_SEAM + 0.5))
        c = LEDGE_LEAD
        tri = [Part.makePolygon([V(x, y_led - c, z), V(x, y_led + 0.01, z), V(x, y_led + 0.01, z + c + 0.01), V(x, y_led - c, z)])
               for x, z in ((xa, za), (xb, zb))]
        out.append(Part.makeLoft(tri, True, True))
    return out


def build_tub(log=None):
    zs, zf = P.Z_SKIN, -P.T_FLOOR
    t = R.rrect(2 * P.BODY_HX, 2 * P.BODY_HY, P.PLAN_R, zs, P.Z_SEAM, XC, 0)
    big = 8.0                                   # 45 deg bevels from the runner edges up to the walls
    for s in (1, -1):
        x0, y0 = s * P.RIDGE_OUT, s * P.RIDGE_HY
        t = t.cut(R.prism_xz([(x0, zs - 0.01), (x0 + s * big, zs - 0.01), (x0 + s * big, zs + big)], -P.BODY_HY - 1, P.BODY_HY + 1))
        t = t.cut(R.prism_yz([(y0, zs - 0.01), (y0 + s * big, zs - 0.01), (y0 + s * big, zs + big)], XC - P.BODY_HX - 1, XC + P.BODY_HX + 1))

    # strap lugs
    for sx in (1, -1):
        prof = [(XC + sx * (P.BODY_HX + x), z) for x, z in lug_profile()]
        for sy in (1, -1):
            y0, y1 = sorted((sy * P.SLOT_W / 2, sy * P.LUG_HY))
            lug = R.prism_xz(prof, y0, y1)
            xa, xb = sorted((XC + sx * (P.BODY_HX - 4.0), XC + sx * P.LUG_HX))
            mask = R.rrect(xb - xa, y1 - y0, 1.2, -10.0, 12.0, (xa + xb) / 2, (y0 + y1) / 2)
            t = t.fuse(lug.common(mask))
    t = t.removeSplitter()
    for sx in (1, -1):
        xp = XC + sx * (P.BODY_HX + P.PIN_DX)
        tun = [(xp + x, P.Z_BAR + z) for x, z in R.octagon(BAR_HW, BAR_HH, BAR_CH)]
        t = t.cut(R.prism_xz(tun, -P.LUG_HY - 1.0, P.LUG_HY + 1.0))

    # wrist side: tunnel between the runners, grooves between the pads, room for the tail
    t = t.cut(R.prism_xz([(-P.RIDGE_IN, zs - 1), (P.RIDGE_IN, zs - 1), (P.RIDGE_IN, zs), (P.TUNNEL_TOP_HX, zf),
                          (-P.TUNNEL_TOP_HX, zf), (-P.RIDGE_IN, zs)], -P.BODY_HY - 1, P.BODY_HY + 1))
    for y0 in P.GROOVE_Y:
        hw = P.GROOVE_W / 2
        t = t.cut(R.prism_yz([(y0 - hw, zs - 1), (y0 + hw, zs - 1), (y0 + hw, zs), (y0, zs + P.GROOVE_D), (y0 - hw, zs)],
                             XC - P.BODY_HX - 1, XC + P.BODY_HX + 1))
    ya, yb, hp = P.STRIP_POCKET
    for sx in (1, -1):
        xa, xb = sorted((sx * (P.RIDGE_IN - 0.1), sx * (P.ROOT_HX + 0.20)))
        t = t.cut(R.box(xa, xb, yb, ya, zs - 1, zs + hp))
    cx0, cx1, cy0, cy1 = P.CHIMNEY
    t = t.cut(R.box(cx0, cx1, cy0, cy1, zs - 1, 0.5))
    t = t.cut(R.box(cx0, cx1, -P.BODY_HY - 1, cy0 + 0.01, zs - 1, zf))      # same width out to the hand end: the tail lies here on the tray

    # inside
    t = t.cut(R.rrect(2 * P.IN_HX, 2 * P.IN_HY, P.PLAN_R - P.WALL, 0.0, P.Z_SEAM + 1.0, XC, 0))
    inner = R.rrect(2 * P.IN_HX, 2 * P.IN_HY, P.PLAN_R - P.WALL, -0.01, P.Z_SEAM, XC, 0)
    add = [R.box(P.BLOCK_A_X0, WX1, -P.IN_HY, NEST_Y0, -0.01, P.Z_SHELF_A),                 # shelf A, beside SW1
           R.box(P.BLOCK_A_X0, WX1, -P.IN_HY, -P.BAY_HY, -0.01, STOP_Z),                    # cell stop on shelf A
           R.box(WX0, -P.BLOCK_A_X0, NEST_Y0 - 1.0, NEST_Y0, -0.01, 1.60),                 # -X stop rib for the board
           R.box(WX0, 10.6, NEST_Y1, P.IN_HY, -0.01, P.Z_SHELF_B),                         # shelf B and the +Y board stop
           R.box(STOP_B_X[0], STOP_B_X[1], P.BAY_HY, P.IN_HY, -0.01, STOP_Z)]              # cell stop on shelf B
    y0, dy = LIP_Y
    for xa, xb in LIP_X:                                                                   # wedge lips over the board edge
        add.append(R.prism_yz([(y0 - 0.2, 0.90 - 0.2), (y0 + dy, 0.90 + dy), (y0 + dy, 2.10), (y0 - 0.2, 2.10)], xa, xb))
    t = t.fuse(add[0].fuse(add[1:]).common(inner))

    # pockets in the floor (all open upward)
    below = R.rrect(2 * P.IN_HX, 2 * P.IN_HY, P.PLAN_R - P.WALL, -3.0, 0.01, XC, 0)
    for x0, x1, y0, y1, dz in (P.WIRE_TROUGH, P.WIRE_BAY, P.J2_POCKET, P.J3_POCKET, P.J3_RISER, P.TP_POCKET):
        t = t.cut(R.box(x0, x1, y0, y1, -dz, 0.01).common(below))
    x0, x1, y0, y1, dz = P.J3_RISER
    t = t.cut(R.box(x0, x1, y0, NEST_Y0 + 0.01, -dz, P.Z_SHELF_A + 1.0))                   # charge leads rise through shelf A

    # long walls: peg slots behind the lugs; a slit under the detent strip, the dimple in it and a lead-in on its edge
    for sx in (1, -1):
        for s in peg_slots(sx):
            t = t.cut(s)
        xa, xb = sorted((XC + sx * (P.IN_HX - 0.1), XC + sx * (P.BODY_HX + 0.1)))
        t = t.cut(R.box(xa, xb, P.DETENT_Y[0], P.DETENT_Y[1], P.DETENT_SLIT_Z[0], P.DETENT_SLIT_Z[1]))
        xi = XC + sx * P.IN_HX
        d, ya, yb = P.DETENT_DIMPLE, P.DETENT_BUMP_Y[0] - 0.15, P.DETENT_BUMP_Y[1] + 0.15
        t = t.cut(R.prism_xy([(xi - sx * 0.02, ya - d - 0.02), (xi + sx * d, ya), (xi + sx * d, yb), (xi - sx * 0.02, yb + d + 0.02)],
                             P.DETENT_SLIT_Z[1] - 0.01, P.Z_SEAM + 0.5))
        t = t.cut(R.prism_xz([(xi - sx * 0.02, P.Z_SEAM + 0.1), (xi - sx * 0.02, P.Z_SEAM - 0.45), (xi + sx * 0.45, P.Z_SEAM + 0.1)],
                             P.DETENT_BUMP_Y[0] - 1.0, P.DETENT_BUMP_Y[1] + P.LID_SLIDE + 1.0))
    # thumb notch under the lid edge at the hand end: push the lid toward the elbow here to open it
    t = t.cut(R.prism_yz([(-P.BODY_HY - 0.1, P.Z_SEAM + 0.1), (-P.BODY_HY - 0.1, P.Z_SEAM - 0.9), (-P.BODY_HY + 0.8, P.Z_SEAM + 0.1)],
                         XC - 6.0, XC + 6.0))
    return t.removeSplitter()


# ---------------- lid ----------------
def build_lid(log=None):
    l = R.rrect(2 * P.BODY_HX, 2 * P.BODY_HY, P.PLAN_R, P.Z_SEAM, P.Z_TOP, XC, 0)
    l = R.chamfer_edges(l, P.TOP_CHAM, lambda e: e.BoundBox.ZMin > P.Z_TOP - 1e-6, log, 'lid top')
    l = l.cut(R.rrect(2 * P.IN_HX, 2 * P.IN_HY, P.PLAN_R - P.WALL, P.Z_SEAM - 1.0, P.Z_ROOF, XC, 0))
    roof = P.Z_ROOF + 0.2
    zl = P.Z_SEAM - P.LIP_H
    add = []
    for sx in (1, -1):
        xo, xi = XC + sx * RIM_HX, XC + sx * (RIM_HX - P.LIP_T)
        # lip inside the long wall, with a lead-in; joined to the skirt above the seam
        add.append(R.prism_xz([(xo, zl + 0.3), (xo - sx * 0.3, zl), (xi, zl), (xi, roof), (xo, roof)], RIM_Y[0], RIM_Y[1]))
        xa, xb = sorted((xo - sx * 0.05, XC + sx * (P.IN_HX + 0.2)))
        add.append(R.box(xa, xb, RIM_Y[0], RIM_Y[1], P.Z_SEAM, roof))
        # two pegs: flat below, the top falls at 45 deg from the lip to the tip
        r, (z0, z1) = P.PEG_REACH, P.PEG_Z
        for y0 in P.PEG_Y:
            add.append(R.prism_xz([(xo - sx * 0.35, z0), (xo + sx * r, z0), (xo + sx * r, z1 - r), (xo, z1), (xo - sx * 0.35, z1)], y0, y0 + P.PEG_L))
        # detent bump
        b, (ya, yb) = P.DETENT_BUMP, P.DETENT_BUMP_Y
        add.append(R.prism_xy([(xo - sx * 0.05, ya - b - 0.05), (xo + sx * b, ya), (xo + sx * b, yb), (xo - sx * 0.05, yb + b + 0.05)],
                              P.DETENT_SLIT_Z[1] + 0.15, P.Z_SEAM - 0.15))
    # cell fence, cell ribs, board feet
    add.append(R.box(P.FENCE_X[0], P.FENCE_X[1], FENCE_Y[0], FENCE_Y[1], P.Z_SHELF_A + 0.25, roof))
    for y in RIB_Y:
        add.append(R.box(P.BAT_X0 + 0.8, P.BAT_X0 + P.BAT_W - 0.8, y - 0.4, y + 0.4, RIB_Z, roof))
    # board feet with 45 deg gussets, so that neither is a bare pin
    x0, x1, y0, y1 = FOOT_FENCE
    zt = P.Z_SHELF_A + 0.3
    za, zb = P.PCB_T + 1.20, P.Z_SHELF_B + 0.40          # the gussets start above the nRF (-Y) and above shelf B (+Y, lid at its offset)
    add.append(R.prism_yz([(y0, FOOT_Z), (y1, FOOT_Z), (y1, zb), (y1 + (zt - zb), zt), (y0 - (zt - za), zt), (y0, za)], x0, x1))
    x0, x1, y0, y1 = FOOT_EDGE
    add.append(R.box(x0, x1, y0, y1, FOOT_Z, roof))
    zg = zl + 0.35                                       # ends inside the lip, above its lead-in
    add.append(R.prism_yz([(y1 - 0.01, FOOT_Z), (y1 + zg - FOOT_Z, zg), (y1 - 0.01, zg)], XC + RIM_HX - P.LIP_T, x1))
    # LED baffle
    bt = 0.7
    add.append(R.box(P.LED_SLIT_X[0] - bt, P.LED_SLIT_X[1] + bt, P.LED_SLIT_Y[0] - bt, P.LED_SLIT_Y[1] + bt, 3.0, roof))
    l = l.fuse(add).removeSplitter()

    lr = (P.LED_SLIT_Y[1] - P.LED_SLIT_Y[0]) / 2
    ly = (P.LED_SLIT_Y[0] + P.LED_SLIT_Y[1]) / 2
    slit = R.box(P.LED_SLIT_X[0] + lr, P.LED_SLIT_X[1] - lr, P.LED_SLIT_Y[0], P.LED_SLIT_Y[1], 2.0, P.Z_TOP + 1.0)
    for x in (P.LED_SLIT_X[0] + lr, P.LED_SLIT_X[1] - lr):
        slit = slit.fuse(Part.makeCylinder(lr, P.Z_TOP - 1.0, V(x, ly, 2.0)))
    return l.cut(slit).removeSplitter()


def lid_materials(envelope):
    blue = lid_inlay()
    shell = envelope.cut(blue).removeSplitter()
    assert shell.isValid() and len(shell.Solids) == 1 and blue.isValid()
    assert abs(shell.Volume + blue.Volume - envelope.Volume) < 1e-4
    return [('lid', shell, R.C_LID), ('blue_inlay', blue, R.C_INLAY)]


# ---------------- strap bar ----------------
def build_lug_bar(log=None):
    """Lies flat for printing (Z = -BAR_H/2 .. +BAR_H/2 here), so the beads run end to end."""
    hw, hh = P.BAR_W / 2, P.BAR_H / 2
    y_head1 = -P.LUG_HY
    y_head0 = y_head1 - 0.70
    y_ear_out = P.LUG_HY + 0.08
    y_tip = P.LUG_HY + 1.35
    ch = 0.40
    bar = R.prism_xz(R.octagon(hw, hh, ch), y_head1 - 0.15, y_tip)
    bar = bar.fuse(R.prism_xz(R.octagon(hw + 0.50, hh, ch * 0.5), y_head0, y_head1))
    for sx in (1, -1):
        pts = [V(sx * (hw - 0.45), y_ear_out, -hh + ch), V(sx * (hw + 0.42), y_ear_out + 0.28, -hh + ch), V(sx * (hw - 0.45), y_tip, -hh + ch)]
        bar = bar.fuse(Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, 2 * (hh - ch))))
    bar = bar.cut(R.box(-0.42, 0.42, P.SLOT_W / 2 + 0.3, y_tip + 0.5, -hh - 0.5, hh + 0.5))
    return bar.removeSplitter()


def lug_bars_placed():
    b0 = build_lug_bar()
    return Part.makeCompound([R.moved(b0, XC + sx * (P.BODY_HX + P.PIN_DX), 0, P.Z_BAR) for sx in (1, -1)])


# ---------------- what goes inside ----------------
def board_real():
    sh = Part.read(BOARD_STEP)
    sols = list(sh.Solids)
    pcb = max(sols, key=lambda s: s.BoundBox.XLength * s.BoundBox.YLength if s.BoundBox.ZLength < P.PCB_T + 0.1 else 0)
    bb = pcb.BoundBox
    dx, dy, dz = -(bb.XMin + P.J1_KX), P.PCB_Y0 - bb.YMin, -bb.ZMin
    out = [R.moved(s, dx, dy, dz) for s in sols]
    ip = sols.index(pcb)
    return out[ip], Part.makeCompound([s for k, s in enumerate(out) if k != ip])


def battery_solids(pcm_up=False):
    """Cell on the two shelves. Bump down: the cell lies flat. Bump up: its +Y end sits 0.9 lower."""
    y0, y1 = P.BAT_Y0, P.BAT_Y0 + P.BAT_L
    z0 = P.Z_SHELF_A + 0.03
    x0, x1 = P.BAT_X0, P.BAT_X0 + P.BAT_W
    body = R.box(x0, x1, y0, y1, z0, z0 + P.BAT_T)
    body = R.fillet_edges(body, 1.0, lambda e: e.BoundBox.ZLength > P.BAT_T - 0.01)
    bump = P.BAT_PCM_T - P.BAT_T
    if pcm_up:
        pcm = R.box(x0 + 0.3, x1 - 0.3, y1 - P.BAT_PCM_L, y1 - 0.2, z0 + P.BAT_T, z0 + P.BAT_T + bump)
        ang = math.degrees(math.atan2(z0 - (P.Z_SHELF_B + 0.03), y1 - NEST_Y0))
        for s in (body, pcm):
            s.rotate(V(0, NEST_Y0, z0), V(1, 0, 0), -ang)
    else:
        pcm = R.box(x0 + 0.3, x1 - 0.3, y1 - P.BAT_PCM_L, y1 - 0.2, z0 - bump, z0)
    return body, pcm


def flex_solids():
    """Root sheet on the runners, both paddles with their electrodes, and the tail on its way into J1."""
    t = P.FLEX_T
    zt = P.Z_SKIN - P.TAPE_T                              # top face of the flex
    sheet = R.box(-P.ROOT_HX, P.ROOT_HX, P.BEND_Y, P.SPINE_Y[1], zt - t, zt)
    for sx in (1, -1):
        xa, xb = sorted((sx * (P.PITCH / 2 - P.POD_W / 2), sx * (P.PITCH / 2 + P.POD_W / 2)))
        sheet = sheet.fuse(R.box(xa, xb, P.SPINE_Y[1] - 0.1, P.POD_L / 2, zt - t, zt))
    gold = [Part.makeCylinder(P.PAD_D / 2, 0.04, V(sx * P.PITCH / 2, y, zt - t - 0.04)) for sx in (1, -1) for y in P.PAD_Y]
    path = P.tail_path()
    stiff0 = path[-2]

    def ribbon(pts, th, hx):
        up, dn = [], []
        for k, p in enumerate(pts):
            a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
            n = math.hypot(b[0] - a[0], b[1] - a[1])
            ny, nz = -(b[1] - a[1]) / n, (b[0] - a[0]) / n
            up.append((p[0] + ny * th / 2, p[1] + nz * th / 2))
            dn.append((p[0] - ny * th / 2, p[1] - nz * th / 2))
        return R.prism_yz(up + dn[::-1], -hx, hx)
    tail = ribbon(path[:-1], t, P.TAIL_W / 2)
    tip = R.box(-P.TAIL_W / 2, P.TAIL_W / 2, stiff0[0], path[-1][0], stiff0[1] - P.TAIL_T / 2, stiff0[1] + P.TAIL_T / 2)
    # the paddle ends beyond the bend line lift with the tail (same first arc), drawn over the full sheet width
    strip = ribbon(path[:14], t, P.ROOT_HX)
    keep = R.box(-P.ROOT_HX - 1, P.ROOT_HX + 1, P.BEND_Y - 1.2, P.BEND_Y + 0.01, P.Z_SKIN - 1, P.Z_SKIN + 1.75)
    return sheet, Part.makeCompound(gold), tail.fuse(tip), strip.common(keep)


def leads_visual():
    """Battery leads: J2 -> trough under the board -> bay behind the board -> up the +Y wall to the end of the cell."""
    out = []
    for k, (jx, jy) in enumerate(P.J2):
        xw = P.WIRE_TROUGH[0] + 0.55 + 1.1 * k
        zt = -P.WIRE_TROUGH[4] + 0.56
        ye = P.IN_HY - 0.65
        pts = [V(jx, jy, -0.55), V(xw, jy + 2.2, -0.55), V(xw, jy + 3.6, zt), V(xw, P.PCB_Y1 + 0.6, zt),
               V(xw + 0.15, ye, 0.2), V(xw + 0.15, ye, 3.3)]
        for a, b in zip(pts, pts[1:]):
            d = b.sub(a)
            out.append(Part.makeCylinder(0.5, d.Length, a, d))
            out.append(Part.makeSphere(0.5, b))
    return Part.makeCompound(out)


def lid_travel(lid, tub, others, log):
    """The lid's way on: straight down at the offset, then the slide. Reports what it touches.
    Only the two detent bumps may overlap the tub (they push the wall strips out by that much)."""
    s = P.LID_SLIDE
    zone = R.box(XC - P.BODY_HX - 1, XC + P.BODY_HX + 1, P.DETENT_BUMP_Y[0] - 1.5, P.DETENT_BUMP_Y[1] + s + 1.5, P.DETENT_SLIT_Z[1] - 0.2, P.Z_SEAM + 20)
    rows = []
    for name, dy, dz in [('3 mm up', s, 3.0), ('1.5 mm up', s, 1.5), ('0.5 mm up', s, 0.5), ('down, offset', s, 0.0),
                         ('half slid', s * 0.5, 0.0), ('0.25 before closed', 0.25, 0.0), ('closed', 0.0, 0.0), ('pushed past', -0.3, 0.0)]:
        c = R.moved(lid, 0, dy, dz)
        com = c.common(tub)
        bump = com.common(zone).Volume if com.Volume > 1e-7 else 0.0
        rows.append(f"{name}: {com.Volume - bump:.3f}/{bump:.3f}/{sum(R.clash(c, o) for o in others):.3f}")
    log("  lid going on (tub overlap mm3 / of the detent bumps / cell and board): " + ', '.join(rows))
    # closed lid pulled straight up: free within the play, then the four pegs meet their ledges
    lift = ', '.join(f"{dz:.2f} mm: {R.clash(R.moved(lid, 0, 0, dz), tub):.3f}" for dz in (LEDGE_CLR - 0.05, LEDGE_CLR + 0.05, 0.5))
    log(f"  closed lid lifted (overlap with the tub, mm3): {lift}")
    # ... and with the lid 0.3 mm short of closed (the detent holds it closer than that)
    log(f"  lid 0.3 mm short of closed, lifted 0.5 mm: {R.clash(R.moved(lid, 0, 0.3, 0.5), tub):.3f} mm3")


def wall_probe(shape, p, d):
    ln = Part.makeLine(V(*p), V(p[0] + d[0] * 30, p[1] + d[1] * 30, p[2] + d[2] * 30))
    try:
        return round(sum(e.Length for e in shape.common(ln).Edges), 2)
    except Exception:
        return -1


def printed(tub=None, lid=None, bar=None):
    """The parts as they lie on the bed."""
    out = {}
    if tub is not None:
        out['tub'] = R.on_bed(tub)
    if lid is not None:
        c = lid.copy()
        c.rotate(V(0, 0, 0), V(1, 0, 0), 180)
        out['lid'] = R.on_bed(c)
    if bar is not None:
        out['lug_bar'] = R.on_bed(bar)
    return out


if not getattr(sys, 'neurband_lib', False):
    log = R.Log('case')
    tub = R.check(build_tub(log), 'tub', log)
    lid = R.check(build_lid(log), 'lid', log)
    bar = R.check(build_lug_bar(log), 'lug_bar', log)
    pcb, parts = board_real()
    sheet, gold, tail, strip = flex_solids()
    bars = lug_bars_placed()
    leads = leads_visual()
    need, have = P.tail_need()
    log(f"  module: body {2 * P.BODY_HX:.1f} x {2 * P.BODY_HY:.1f}, {2 * P.LUG_HX:.1f} over the lugs, {P.Z_TOP - P.Z_SKIN:.2f} from the pads to the top; "
        f"floor {P.T_FLOOR}, pads {P.H_RIDGE} below it; bar axis {P.Z_BAR - P.Z_SKIN:.2f} above the pad plane")
    log(f"  flex tail: needs {need:.2f} of {have:.2f} mm with {P.TAPE_T} mm tape ({P.tail_need(0.25)[0]:.2f} with 0.25 mm tape)")
    for name, up in (('bump down', False), ('bump up', True)):
        bat, pcm = battery_solids(up)
        cell = bat.fuse(pcm)
        ck = dict(tub=R.clash(cell, tub), lid=R.clash(cell, lid), board=R.clash(cell, pcb) + R.clash(cell, parts), leads=R.clash(cell, leads))
        bb = cell.BoundBox
        log(f"  cell, {name}: z {bb.ZMin:.2f} .. {bb.ZMax:.2f} (roof {P.Z_ROOF:.2f}, SW1 top {P.PCB_T + P.J1_H:.2f}), "
            f"y {bb.YMin:.2f} .. {bb.YMax:.2f} (bay {-P.BAY_HY:.2f} .. {P.BAY_HY:.2f}); clash mm3 {json.dumps(ck)}")
    bat, pcm = battery_solids(False)
    checks = dict(
        tub_lid=R.clash(tub, lid), tub_bars=R.clash(tub, bars), lid_bars=R.clash(lid, bars),
        pcb_tub=R.clash(pcb, tub), pcb_lid=R.clash(pcb, lid), parts_tub=R.clash(parts, tub), parts_lid=R.clash(parts, lid),
        tail_tub=R.clash(tail, tub), tail_lid=R.clash(tail, lid), tail_pcb=R.clash(tail, pcb), strip_tub=R.clash(strip, tub),
        sheet_tub=R.clash(sheet, tub), leads_tub=R.clash(leads, tub), leads_lid=R.clash(leads, lid), leads_pcb=R.clash(leads, pcb),
    )
    log(f"  clash mm3: {json.dumps(checks)}")
    cells = [battery_solids(False), battery_solids(True)]
    lid_travel(lid, tub, [c[0].fuse(c[1]) for c in cells] + [pcb, parts, leads], log)
    probes = [('floor under the board centre', (0.0, 2.0, -0.01), (0, 0, -1)), ('floor over a pad', (9.0, 0.0, -0.01), (0, 0, -1)),
              ('under the wire trough', (12.0, 2.0, -P.WIRE_TROUGH[4] - 0.01), (0, 0, -1)),
              ('trough over a groove', (12.0, 5.0, -P.WIRE_TROUGH[4] - 0.01), (0, 0, -1)),
              ('over the strip pocket', (9.0, -14.0, -0.01), (0, 0, -1)),
              ('lug below the bar', (XC + P.BODY_HX + P.SLOT_GAP + 2.4, 13.5, P.Z_BAR - BAR_HH - 0.02), (0, 0, -1)),
              ('lug above the bar', (XC + P.BODY_HX + P.PIN_DX, 13.5, P.Z_BAR + BAR_HH + 0.02), (0, 0, 1)),
              ('lug beyond the bar', (XC + P.BODY_HX + P.SLOT_GAP + 2 * BAR_HW + 0.02, 13.5, P.Z_BAR), (1, 0, 0)),
              ('ledge over a peg', (XC + P.IN_HX + 0.3, P.PEG_Y[0] + 0.3, P.PEG_Z[1] + LEDGE_CLR - P.LIP_CLR - 0.3 + 0.02), (0, 0, 1)),
              ('behind a peg slot', (XC + P.IN_HX + P.SLOT_DEPTH + 0.02, P.PEG_Y[0] + 0.3, (P.PEG_Z[0] + P.PEG_Z[1]) / 2), (1, 0, 0)),
              ('detent strip', (XC + P.IN_HX + 0.5, 5.0, P.DETENT_SLIT_Z[1] + 0.02), (0, 0, 1))]
    log("  tub thickness: " + ', '.join(f"{n} {wall_probe(tub, p, d)}" for n, p, d in probes))
    for name, sh in printed(tub, lid, bar).items():
        bed, worst, flat = R.bed_report(sh)
        bb = sh.BoundBox
        log(f"  {name} on the bed: {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.2f}, contact {bed:.0f} mm2, steepest overhang {worst:.0f} deg, "
            f"flat ceilings (span, length, height): {flat[:10]}")

    R.save('tub', [('tub', tub, R.C_TUB)], log)
    lid_parts = lid_materials(lid)
    R.save('lid', lid_parts, log)
    R.save('lug_bar', [('lug_bar', bar, R.C_BAR)], log)
    inside = [('main_board', pcb, R.C_PCB), ('board_parts', parts, R.C_PARTS), ('lipo', bat, R.C_LIPO), ('lipo_pcm', pcm, R.C_PCM),
              ('leads', leads, R.C_WIRE), ('flex', sheet.fuse([tail, strip]), R.C_FLEX), ('electrodes', gold, R.C_GOLD)]
    R.save('module_assy', [('tub', tub, R.C_TUB), *lid_parts, ('lug_bars', bars, R.C_BAR), *inside], log)
    R.save('module_open', [('tub', tub, R.C_TUB), ('lug_bars', bars, R.C_BAR), *inside,
                           *((n, R.moved(s, 0, P.LID_SLIDE, 14), c) for n, s, c in lid_parts)], log)
    R.save('module_exploded', [('tub', tub, R.C_TUB), ('lug_bars', bars, R.C_BAR),
                               ('flex', R.moved(sheet.fuse([tail, strip]), 0, 0, -6), R.C_FLEX), ('electrodes', R.moved(gold, 0, 0, -6), R.C_GOLD),
                               ('main_board', R.moved(pcb, 0, 0, 9), R.C_PCB), ('board_parts', R.moved(parts, 0, 0, 9), R.C_PARTS),
                               ('lipo', R.moved(bat, 0, 0, 17), R.C_LIPO), ('lipo_pcm', R.moved(pcm, 0, 0, 17), R.C_PCM),
                               *((n, R.moved(s, 0, 0, 27), c) for n, s, c in lid_parts)], log)
    R.finish(log)
