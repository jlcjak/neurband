"""strap.py - chosen strap: 20 mm elastic nylon webbing + hook-and-loop, two pieces sewn to the
housing lugs, threaded through the pod-shell tunnels, closed over the ulnar gap through a printed
ring. Also holds the band layout (pod positions, housing seat, strap path) used by fit_band.py.

Pieces per band:
  short strap  (ulnar side): sewn around the -X lug bar, through the free ulnar pods, ends in a
                sewn loop that holds the ring just past pod 1 (edge of the gap).
  long strap   (radial side): sewn around the +X lug bar, through the radial / volar pods,
                rides over the roofs of the last CLOSURE_PODS pods, crosses the gap, passes
                through the ring and folds back on itself (hook tape on the fold-back, loop
                tape on the outer face) - the band opens fully, nothing passes over the hand.
  ring (printed PA12) and keeper (printed TPU) are ordered parts; webbing/tape are bought.
Frame: as fitgeom.py (X radial, Y along the arm, Z dorsal). Strap STEP files are per size.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/strap.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True
import FreeCAD, Part
import cadutil as U
import fitgeom as G
import housing as H
import pod_shell as PS

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
# size: (model wrist circumference, pod pitch, size range)
SIZES = {'S': (140.0, 8.6, (130, 148)), 'M': (160.0, 9.5, (148, 169)),
         'L': (180.0, 10.8, (169, 193)), 'XL': (200.0, 12.4, (193, 220))}
POD_W = PS.POD_W
STRAP_W = 20.0
STRAP_T = 1.3
CLOSURE_PODS = 3            # fold-back covers the gap and these pods (14-16) = hook-and-loop zone
LUG_LOOP = 14.0             # webbing used by the sewn loop around a lug bar
SEW_OVERLAP = 15.0
RING_LOOP = 14.0
RING_IN_W, RING_IN_H, RING_BAR = 21.5, 3.2, 2.4   # printed ring: opening (Y x radial), bar section
KEEPER_IN_W, KEEPER_IN_H, KEEPER_WALL, KEEPER_LEN = 21.0, 3.0, 1.2, 6.0

STRAP_LOCAL_Z = PS.BASE_T + STRAP_T / 2             # strap mid-plane in the pod channel (pod local)
FOLD_GAP = 0.5                                       # fold-back drapes over the rail lips


def loc(p, lx, lz):
    c, s = math.cos(p['ang']), math.sin(p['ang'])
    return (p['x'] + lx * c - lz * s, p['z'] + lx * s + lz * c)


def layout(c, pitch):
    a, b = G.section(c, G.BAND_Y)
    cur = G.Curve(a, b, G.DOME_H + G.FLEX_T)   # pod-local origin (shell pocket floor)
    pods = []
    for i in range(1, G.N_PODS + 1):
        s = G.pod_s(i, pitch)
        x, z, ang = cur.at(s)
        pods.append(dict(i=i, s=s, x=x, z=z, ang=ang))
    # housing body (not the relieved lugs) rests on the highest pod-roof corners under it
    x_body = H.SEAT_HALF_W
    x_lug_out = H.SEAT_HALF_W + H.LUG_OUT
    z0 = -1e9
    under = []
    for p in pods:
        cs = [loc(p, sx * POD_W / 2, PS.TOP_Z) for sx in (-1, 1)]
        if p['z'] > 0 and min(abs(cx) for cx, _ in cs) < x_body:
            under.append(p)
            for cx, cz in cs:
                if abs(cx) < x_body:
                    z0 = max(z0, cz - H.seat_z(cx))
    seat_gaps = {}
    for p in under:
        g = [z0 + H.seat_z(abs(cx)) - cz for cx, cz in (loc(p, sx * POD_W / 2, PS.TOP_Z) for sx in (-1, 1)) if abs(cx) < x_body]
        seat_gaps[p['i']] = min(g)
    z_nom = b + G.D_POD_TOP
    # strap paths: same height (channel floor) on every pod; ends wrap the lug bars
    def lug_pt(sign):
        x = sign * (H.SEAT_HALF_W + H.STRAP_SLOT_W / 2)
        return (x, z0 + H.seat_z(abs(x)) - (PS.TOP_Z - STRAP_LOCAL_Z))
    paths, kinds, pidx = {}, {}, {}
    for side, order, sign in (('long', range(5, 17), 1), ('short', range(4, 0, -1), -1)):
        pts = [lug_pt(sign)]
        slot_x = abs(pts[0][0])
        for i in order:
            p = pods[i - 1]
            xe = [loc(p, sx * POD_W / 2, 0)[0] for sx in (-1, 1)]
            dorsal = p['z'] > 0
            if dorsal and max(abs(x) for x in xe) <= x_body + 0.5:
                kinds[i] = 'housing'
                continue
            xs = (-POD_W / 2, POD_W / 2) if side == 'long' else (POD_W / 2, -POD_W / 2)
            first = len(pts)
            for lx in xs:
                q = loc(p, lx, STRAP_LOCAL_Z)
                if not (dorsal and abs(q[0]) < slot_x + 0.5):
                    pts.append(q)
            kinds[i] = 'lug' if dorsal and min(abs(x) for x in xe) < x_lug_out else 'strap'
            if len(pts) > first:
                pidx[i] = (side, first, len(pts) - 1)
        paths[side] = pts
    # ring just past pod 1 on the short strap
    p1 = pods[0]
    ring_c = loc(p1, -POD_W / 2 - 5.0, STRAP_LOCAL_Z + 0.6)
    paths['short'].append(loc(p1, -POD_W / 2 - 3.5, STRAP_LOCAL_Z))
    paths['long'].append(ring_c)
    # fold-back: back over the gap and the closure pods, offset outward by one strap thickness
    fold = []
    n_back = 2 * CLOSURE_PODS + 2
    src = paths['long'][-n_back:][::-1]
    for k in range(len(src)):
        if k == 0:
            dx, dz = src[1][0] - src[0][0], src[1][1] - src[0][1]
        else:
            dx, dz = src[k][0] - src[k - 1][0], src[k][1] - src[k - 1][1]
        L = math.hypot(dx, dz)
        # travelling backwards (decreasing s): outward normal is the right-hand normal
        nx, nz = dz / L, -dx / L
        fold.append((src[k][0] + nx * (STRAP_T + FOLD_GAP), src[k][1] + nz * (STRAP_T + FOLD_GAP)))
    paths['fold'] = fold
    # per-pod strap load ~ turning angle of the strap at the pod (tension x angle)
    loads = {}
    def ang(p, q):
        return math.atan2(q[1] - p[1], q[0] - p[0])
    for i, (side, f, l) in pidx.items():
        pts = paths[side]
        if f < 1 or l + 1 >= len(pts):
            continue
        d = ang(pts[f - 1], pts[f]) - ang(pts[l], pts[l + 1])
        if side == 'short':
            d = -d
        loads[i] = (d + math.pi) % (2 * math.pi) - math.pi
    lens = {k: sum(math.dist(v[j], v[j + 1]) for j in range(len(v) - 1)) for k, v in paths.items()}
    return dict(a=a, b=b, pods=pods, z0=z0, lift=z0 - z_nom, under=[p['i'] for p in under],
                seat_gaps=seat_gaps, paths=paths, kinds=kinds, ring_c=ring_c, ring_ang=p1['ang'],
                loads=loads, lens=lens)


def strap_shapes(L):
    """Webbing pieces, ring and keeper for a layout, in the wrist frame."""
    y = G.BAND_Y
    out = {}
    for side in ('long', 'short', 'fold'):
        pts = L['paths'][side]
        segs = [U.beam(pts[k], pts[k + 1], STRAP_W, STRAP_T, y) for k in range(len(pts) - 1)]
        segs = [s for s in segs if s is not None]
        for p in pts[1:-1]:
            segs.append(Part.makeCylinder(STRAP_T / 2, STRAP_W, V(p[0], y - STRAP_W / 2, p[1]), V(0, 1, 0)))
        out[side] = Part.makeCompound(segs)
    # sewn loops around the lug bars (housing frame -> wrist frame)
    loops = []
    for sign in (-1, 1):
        x_in = sign * (H.SEAT_HALF_W + H.STRAP_SLOT_W / 2)
        x_out = sign * (H.SEAT_HALF_W + H.LUG_OUT + STRAP_T / 2)
        ztop = L['z0'] + H.LUG_TOP + STRAP_T / 2
        dz = PS.TOP_Z - STRAP_LOCAL_Z
        zi = L['z0'] + H.seat_z(abs(x_in)) - dz
        zo = L['z0'] + H.seat_z(abs(x_out)) - dz
        for p, q in (((x_in, zi), (x_in, ztop)), ((x_in, ztop), (x_out, ztop)),
                     ((x_out, ztop), (x_out, zo)), ((x_out, zo), (x_in, zi))):
            loops.append(U.beam(p, q, STRAP_W, STRAP_T, y))
        for p in ((x_in, ztop), (x_out, ztop), (x_out, zo)):
            loops.append(Part.makeCylinder(STRAP_T / 2, STRAP_W, V(p[0], y - STRAP_W / 2, p[1]), V(0, 1, 0)))
    out['loops'] = Part.makeCompound(loops)
    out['ring'] = place_tangent(ring(), L['ring_c'], L['ring_ang'], y)
    fold = L['paths']['fold']
    kp = fold[-2]
    kang = math.atan2(fold[-1][1] - fold[-2][1], fold[-1][0] - fold[-2][0])
    k = keeper()
    k.translate(V(0, 0, -STRAP_T / 2))
    out['keeper'] = place_tangent(k, kp, kang, y)
    return out


def ring():
    """Printed ring, local frame: X = strap direction (thin), Y = across the strap, Z = radial."""
    ow, oh = RING_IN_W + 2 * RING_BAR, RING_IN_H + 2 * RING_BAR
    r = Part.makeBox(RING_BAR, ow, oh, V(-RING_BAR / 2, -ow / 2, -oh / 2))
    r = r.cut(Part.makeBox(RING_BAR + 2, RING_IN_W, RING_IN_H, V(-RING_BAR / 2 - 1, -RING_IN_W / 2, -RING_IN_H / 2)))
    try:
        r = r.makeFillet(0.5, r.Edges)
    except Exception:
        pass
    return r


def keeper():
    """Printed TPU keeper that holds the folded-back tail on the strap (two layers)."""
    ow, oh = KEEPER_IN_W + 2 * KEEPER_WALL, KEEPER_IN_H + 2 * KEEPER_WALL
    k = Part.makeBox(KEEPER_LEN, ow, oh, V(-KEEPER_LEN / 2, -ow / 2, -oh / 2 + KEEPER_IN_H / 2 - STRAP_T / 2))
    k = k.cut(Part.makeBox(KEEPER_LEN + 2, KEEPER_IN_W, KEEPER_IN_H,
                           V(-KEEPER_LEN / 2 - 1, -KEEPER_IN_W / 2, -STRAP_T / 2 - (KEEPER_IN_H - 2 * STRAP_T) / 2)))
    return k


def place_tangent(shape, p, ang, y):
    s = shape.copy()
    s.rotate(V(0, 0, 0), V(0, 1, 0), -math.degrees(ang))
    s.translate(V(p[0], y, p[1]))
    return s


def cut_lengths(L):
    return dict(short=L['lens']['short'] + LUG_LOOP + RING_LOOP + 2 * SEW_OVERLAP,
                long=L['lens']['long'] + L['lens']['fold'] + LUG_LOOP + SEW_OVERLAP + 10.0)


if not getattr(sys, 'neurband_fit', False):
    log = U.Log('strap')
    r = U.check(ring(), 'strap_ring', log)
    k = U.check(keeper(), 'strap_keeper', log)
    U.save('strap_ring', [('strap_ring', r, U.C_PA12_BLACK)], log)
    U.save('strap_keeper', [('strap_keeper', k, U.C_TPU)], log)
    U.fab('strap_ring', 'Strap closure ring (20 mm webbing)', r, 4, 'mjf', 'pa12', 'black', log)
    U.fab('strap_keeper', 'Strap keeper loop', k, 4, 'fdm', 'tpu', 'black', log)
    for size, (c, pitch, rng) in SIZES.items():
        L = layout(c, pitch)
        sh = strap_shapes(L)
        cl = cut_lengths(L)
        log(f"  {size}: wrist {c} pitch {pitch}: housing lift {L['lift']:.2f} under {L['under']} "
            f"kinds {L['kinds']} cut short {cl['short']:.0f} mm long {cl['long']:.0f} mm")
        items = [('strap_long', Part.makeCompound([sh['long'], sh['fold']]), U.C_WEBBING),
                 ('strap_short', sh['short'], U.C_WEBBING), ('lug_loops', sh['loops'], U.C_WEBBING),
                 ('ring', sh['ring'], U.C_PA12_BLACK), ('keeper', sh['keeper'], U.C_TPU)]
        U.save(f'strap_{size}', items, log)
    U.finish(log)
