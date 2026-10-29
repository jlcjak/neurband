"""fit_band.py - fit-check assemblies fit_S/M/L/XL.step: band wrapped on each wrist model.

Pods are rigid plates tangent to the wrist at their centres (dome tips on the skin), the flex
links are drawn as chords (their real bend radius is computed analytically), the housing sits on
the pod rails on the dorsal side, the strap is closed over the ulnar gap.
Writes mech/logs/fit_band.log and mech/fit_results.json (numbers used in docs/mech/mechanical.md).
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/fit_band.py
"""
import os, sys, math, json
MECH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(MECH)
sys.path.insert(0, MECH)
sys.path.insert(0, os.path.join(ROOT, 'extra', 'wrists'))
sys.neurband_lib = True
sys.neurband_fit = True
import FreeCAD, Part
import cadutil as U
import fitgeom as G
import housing as H
import pod_shell as PS
import electrode_flex as EF
import strap as S
import wrist as W

V = FreeCAD.Vector

# ---------------- parameters ----------------
SIZES = S.SIZES              # size: (model wrist mm, pitch mm, range mm)
POD_W = PS.POD_W
MIN_BEND_R = 3.0             # static bend radius limit for the 2-layer polyimide links
CHECK_INTERFERENCE = True
BAND_ONLY = ('S', 'M', 'XL')


def place(shape, p, y):
    s = shape.copy()
    s.Placement = U.pod_placement(p['x'], p['z'], p['ang'], y)
    return s


def numbers(c, pitch):
    f = G.fit(c, pitch, POD_W, housing_r=H.SEAT_R, housing_chord=2 * H.SEAT_HALF_W)
    L = S.layout(c, pitch)
    a, b = L['a'], L['b']
    # dorsal skin sagitta under a flat 34 mm board base
    skin = G.Curve(a, b, 0.0)
    xs, zs, _ = skin.at(0.0)
    # find s where x = PCB_W/2 on the skin
    lo, hi = 0.0, skin.P / 4
    for _ in range(50):
        m = (lo + hi) / 2
        if skin.at(m)[0] < H.SEAT_HALF_W:
            lo = m
        else:
            hi = m
    sag_flat = zs - skin.at(lo)[1]
    loads = L['loads']
    free = {i: v for i, v in loads.items() if L['kinds'].get(i) == 'strap'}
    return dict(
        wrist=c, pitch=pitch, a=round(a, 1), b=round(b, 1), ratio=round(a / b, 3),
        P_skin=round(f['P_skin'], 1), chain=round(f['chain'], 1),
        cover_skin=round(f['cover_skin'], 1), cover_pct=round(100 * f['cover_frac'], 1),
        gap=round(f['gap'], 1), gap_deg=round(f['gap_deg'], 0),
        link=round(f['link'], 2), rmin=round(f['rmin'], 2), overlap=f['overlap'] or f['gap'] < 0,
        sag_flat_board=round(sag_flat, 2), seat_r=H.SEAT_R,
        housing_lift=round(L['lift'], 2), seat_gaps={k: round(v, 2) for k, v in L['seat_gaps'].items()},
        max_seat_gap=round(max(L['seat_gaps'].values()), 2),
        under_housing=L['under'], kinds=L['kinds'],
        load_rel={k: round(v, 3) for k, v in sorted(loads.items())},
        free_load_ratio=round(max(free.values()) / min(free.values()), 2),
        strap_cut=S.cut_lengths(L)), L


def build_size(size, log):
    c, pitch, rng = SIZES[size]
    res, L = numbers(c, pitch)
    y = G.BAND_Y
    pods = L['pods']
    wrist, hand = W.build(c)
    shell0, flex0, domes0 = PS.build(), EF.pod_flex(), EF.domes()
    shells, flexes, domes = [], [], []
    for p in pods:
        shells.append(place(shell0, p, y))
        flexes.append(place(flex0, p, y))
        for d in domes0:
            domes.append(place(d, p, y))
    # links as chords between pod edges at the flex mid-plane
    links = []
    for k in range(len(pods) - 1):
        p0 = S.loc(pods[k], POD_W / 2, -G.FLEX_T / 2)
        p1 = S.loc(pods[k + 1], -POD_W / 2, -G.FLEX_T / 2)
        bm = U.beam(p0, p1, EF.LINK_W, G.FLEX_T, y)
        if bm is not None:
            links.append(bm)
    # housing, internals, tail
    hy = y + H.HOUSING_Y_OFFSET
    def hplace(s):
        s = s.copy()
        s.translate(V(0, hy, L['z0']))
        return s
    base, lid = hplace(H.build_base()), hplace(H.build_lid())
    inner = {k: (hplace(v[0]), v[1]) for k, v in H.build_internals().items()}
    flex_curve = G.Curve(L['a'], L['b'], G.D_FLEX)
    z_flex0 = flex_curve.at(0.0)[1] - L['z0']
    tail, tail_len = H.tail_shape(z_flex0)
    tail.translate(V(0, y, 0))
    tail.translate(V(0, H.HOUSING_Y_OFFSET, L['z0']))
    st = S.strap_shapes(L)
    res['tail_len_needed'] = round(tail_len, 1)
    res['hand'] = {k: round(v, 1) for k, v in hand.items()}
    res['range'] = rng
    # range ends
    for tag, cc in (('lo', rng[0]), ('hi', rng[1])):
        r2, _ = numbers(cc, pitch)
        res[tag] = {k: r2[k] for k in ('wrist', 'P_skin', 'cover_skin', 'cover_pct', 'gap', 'gap_deg', 'rmin',
                                       'overlap', 'sag_flat_board', 'housing_lift', 'max_seat_gap', 'free_load_ratio')}
    if CHECK_INTERFERENCE:
        def vol(a, bs):
            return round(sum(a.common(x).Volume for x in bs), 3)
        sh_c = Part.makeCompound(shells)
        inter = {}
        inter['shell_vs_shell'] = round(sum(shells[k].common(shells[k + 1]).Volume for k in range(len(shells) - 1)), 3)
        inter['shell_vs_wrist'] = vol(wrist, shells)
        inter['dome_vs_wrist'] = vol(wrist, domes)
        inter['housing_vs_shells'] = vol(base, shells)
        inter['housing_vs_wrist'] = vol(wrist, [base])
        inter['strap_vs_shells'] = round(sum(x.common(sh_c).Volume for x in (st['long'], st['short'])), 3)
        inter['tail_vs_housing'] = vol(tail, [base, lid])
        inter['housing_vs_strap'] = vol(base, [st['long'], st['short'], st['fold']])
        inter['lid_vs_board_parts'] = vol(lid, [inner['board_parts'][0]]) if 'board_parts' in inner else None
        inter['lipo_vs_board_parts'] = vol(inner['lipo'][0], [inner['board_parts'][0]]) if 'board_parts' in inner else None
        if 'main_board' in inner:
            inter['tail_vs_pcb'] = vol(tail, [inner['main_board'][0]])
        # radial overhang of the module beyond the band-wrapped wrist side
        res['module_overhang_radial'] = round(H.X_MAX - (L['a'] + G.D_POD_TOP), 1)
        res['module_overhang_ulnar'] = round(-H.X_MIN - (L['a'] + G.D_POD_TOP), 1)
        inter['tail_vs_shells'] = vol(tail, shells)
        res['interference_mm3'] = inter
    items = [('wrist', wrist, U.C_SKIN),
             ('pod_shells', Part.makeCompound(shells), U.C_PA12_GREY),
             ('flex', Part.makeCompound(flexes + links + [tail]), U.C_POLYIMIDE),
             ('electrodes', Part.makeCompound(domes), U.C_GOLD),
             ('housing_base', base, U.C_PA12_BLACK), ('housing_lid', lid, U.C_PA12_BLACK)]
    items += [(k, v[0], v[1]) for k, v in inner.items()]
    items += [('strap_long', Part.makeCompound([st['long'], st['fold']]), U.C_WEBBING),
              ('strap_short', st['short'], U.C_WEBBING), ('lug_loops', st['loops'], U.C_WEBBING),
              ('strap_ring', st['ring'], U.C_PA12_BLACK), ('strap_keeper', st['keeper'], U.C_TPU)]
    U.save(f'fit_{size}', items, log)
    if size in BAND_ONLY:
        U.save(f'band_{size}', items[1:], log)   # same assembly without the wrist, for close-up renders
    return res


if not getattr(sys, 'neurband_fit_lib', False):
    log = U.Log('fit_band')
    results = {}
    for size in SIZES:
        r = build_size(size, log)
        results[size] = r
        log(f"{size}: " + json.dumps(r))
    with open(os.path.join(MECH, 'fit_results.json'), 'w') as f:
        json.dump(results, f, indent=1)
    U.finish(log)
