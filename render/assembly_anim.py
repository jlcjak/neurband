#!/usr/bin/env python3
"""neurband rev C assembly animation (Blender 5.2 Cycles / OptiX), r2 mechanics.

  python3 render/assembly_anim.py                  # export inputs, render 1080 frames on GPUs 0,1, encode
  python3 render/assembly_anim.py --no-export      # reuse render/build/*.glb
  python3 render/assembly_anim.py --quick          # half size, 16 spp preview (render/build/assembly_quick/)
  python3 render/assembly_anim.py --encode-only    # captions + MP4 + GIF from existing frames

Outputs: docs/media/assembly_r2.mp4 (1920 x 1080, H.264) and docs/media/assembly_r2.gif (720 px wide,
6 fps). The build-guide figures (docs/build/img/) are made by render/guide_figures.py, which reuses the
scenes defined here and there.

Four scenes (SCENES), cross-faded where they overlap:
- board (0-6.4 s, board_scene): the bare main board bottom side up; wires on the SWD pads (flash once,
  then off), the cell's leads onto J2 under Kapton, the J3 charging wires to the magnetic connector;
- jig (6-12.4 s, render/guide_figures.py jig_scene): stage 1 on the bonding jig: the flex pads-down on
  its pins, foam dots into the pods, each pod turned over and pressed into its fence;
- pedestal (12-16.4 s, pedestal_scene): stage 2 on the base jig: the pod 3/4 part on the saddle, the
  base with its foam dots pressed on;
- ring (16-36 s, ring_scene below): the band as fitted on the 160 mm wrist (render/build/band_assembly.glb,
  real flex pod order), the real KiCad board (render/build/main_board.glb) placed with module.k2m, the
  flex tail as a ribbon of constant free length while the board folds down on it (the book fold), the
  cell's leads and the J3 wires, the magnetic connector into its bay, cell, button cap, lid, the strap
  (revealed round the pods, locked round bar A, through bar B and folded back) and the charging cable.
Frames go to render/build/assembly/ (git-ignored) as b_/j_/p_/r_NNNN.png, one Blender process per GPU
(even / odd frames). Captions are drawn afterwards (PIL, Noto Sans), so the 3D frames stay clean.
Blender side: blender -b --python render/assembly_anim.py -- --scene ring --frames 480:1080:2 [--quick]
"""
import os, sys, math, time, json, argparse, subprocess, glob, threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build')
LOGS = os.path.join(BUILD, 'logs')
BLENDER = '/usr/bin/blender'
FREECAD = '/usr/bin/freecad'
MEDIA = os.path.join(ROOT, 'docs', 'media')
FONT_DIR = '/usr/share/fonts/noto'

FPS = 30
DUR = 36.0
NF = int(round(DUR * FPS))
RES = (1920, 1080)
# r2 (Nov 2026): four scenes, cross-faded where they overlap (s)
SCENES = [('board', 0.0, 6.4), ('jig', 6.0, 12.4), ('pedestal', 12.0, 16.4), ('ring', 16.0, DUR)]
PREFIX = {'board': 'b', 'jig': 'j', 'pedestal': 'p', 'ring': 'r'}
SCENE_FRAMES = {n: (int(round(t0 * FPS)), min(NF, int(round(t1 * FPS)) + 1)) for n, t0, t1 in SCENES}
JIG_OFF = 6.2                                        # jig scene: local time = t - JIG_OFF (guide_figures.jig_scene)
OUT_NAME = 'assembly_r2'                             # docs/media/assembly_r2.mp4 / .gif

# ---------------------------------------------------------------- board timeline (seconds)
TB = dict(wires=(0.5, 1.3), wires_off=(2.9, 3.4), cell=(3.4, 4.1), kapton=(4.1, 4.4), conn=(4.6, 5.3))
# ---------------------------------------------------------------- pedestal timeline
TP = dict(flex=(12.1, 12.9), base=(13.1, 14.8))
# ---------------------------------------------------------------- ring timeline
TL = dict(board_in=(16.6, 17.6), board_swing=(18.0, 19.6), conn=(19.9, 20.7), cell=(21.0, 21.7), cap=(21.8, 22.3),
          lid=(22.4, 23.5), slides=(99.0, 99.5), strap=(23.9, 26.6), tails=(26.5, 27.5), pull=(27.6, 28.2),
          clip=(29.0, 30.2), clip_off=(32.0, 32.5))
CAPTIONS = [
    (0.3, 3.3, '1', 'Flash the bare board once through wires on its SWD pads, then unsolder them'),
    (3.5, 6.2, '2', 'Cell leads onto J2 under Kapton; charging wires from J3 to the magnetic connector'),
    (6.5, 9.0, '3', 'Bonding jig: flex pads-down on the pins, foam dots into the pods'),
    (9.1, 12.0, '', 'Turn each pod over and press it into its fence'),
    (12.4, 16.0, '4', 'Pedestal jig: foam dots in the base, tail through its slot, press it onto the saddle'),
    (16.6, 19.7, '5', 'Tail into J1, close the latch, fold the board down'),
    (19.8, 20.9, '', 'Magnetic connector into its bay, glued by its flange'),
    (21.0, 23.6, '6', 'Cell onto the board, button cap, lid snaps on'),
    (23.8, 28.4, '7', 'Strap into the pods, its cut end locked round bar A, the hook end through bar B and folded back'),
    (28.9, 31.9, '8', 'Charge: the magnetic cable clicks on one way round'),
    (32.6, 36.0, '', 'Ready to wear'),
]
TITLE = 'neurband rev C  ·  assembly (r2)'
# ring camera keys: (t, target, azimuth from -Y toward +X, elevation, distance m); R ring, M module,
# H hinge, C connector bay (proximal end)
CAM = [(16.0, 'R', 28, 30, 0.31), (16.8, 'H', 52, 18, 0.205), (18.6, 'H', 58, 20, 0.20), (19.8, 'C', 140, 30, 0.21),
       (20.8, 'C', 128, 36, 0.21), (21.6, 'M', 42, 36, 0.19), (23.0, 'M', 34, 38, 0.19), (23.9, 'R', 18, 24, 0.31),
       (26.2, 'R', 40, 22, 0.32), (27.0, 'L', 6, 18, 0.27), (28.2, 'L', -4, 18, 0.27), (29.0, 'C', 140, 24, 0.24),
       (30.6, 'C', 150, 26, 0.215), (32.6, 'R', 64, 22, 0.32), (36.0, 'R', 44, 20, 0.31)]


def clamp01(x):
    return max(0.0, min(1.0, x))


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ph(t, t0, t1):
    return clamp01((t - t0) / (t1 - t0))


def catmull(keys, t, targets):
    """camera (target, az, el, dist) at t from keys (t, target key, az, el, dist)."""
    import numpy as np
    from mathutils import Vector
    ts = [k[0] for k in keys]
    i = 0 if t < ts[0] else max(0, min(len(keys) - 2, max(j for j in range(len(keys)) if ts[j] <= t)))

    def val(j):
        j = max(0, min(len(keys) - 1, j))
        _, tg, az, el, d = keys[j]
        return np.array([*targets[tg], az, el, d])
    u = clamp01((t - ts[i]) / (ts[i + 1] - ts[i]))
    u = smooth(u) * 0.35 + u * 0.65
    p0, p1, p2, p3 = val(i - 1), val(i), val(i + 1), val(i + 2)
    v = 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
    return Vector([float(x) for x in v[:3]]), float(v[3]), float(v[4]), float(v[5])


# ================================================================ Blender side
def add_fade(m, reveal=False):
    """mix the material's surface with transparency by the object's alpha (Object Info);
    reveal=True also hides points whose 'rev' attribute is above a threshold (returned socket)."""
    nt = m.node_tree
    out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if out is None or not out.inputs['Surface'].links:
        return None
    src = out.inputs['Surface'].links[0].from_socket
    oi = nt.nodes.new('ShaderNodeObjectInfo')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    fac = oi.outputs['Alpha']
    thr = None
    if reveal:
        at = nt.nodes.new('ShaderNodeAttribute')
        at.attribute_name = 'rev'
        lt = nt.nodes.new('ShaderNodeMath')
        lt.operation = 'LESS_THAN'
        nt.links.new(at.outputs['Fac'], lt.inputs[0])
        thr = lt.inputs[1]
        thr.default_value = 0.0
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        nt.links.new(fac, mul.inputs[0])
        nt.links.new(lt.outputs[0], mul.inputs[1])
        fac = mul.outputs[0]
    nt.links.new(fac, mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(src, mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return thr


def mat_tool(NB):
    """light grey matte print (jigs and the charge clip: tools, not the product)."""
    if 'tool' in NB.MATS:
        return NB.MATS['tool']
    m = NB.principled('tool', (0.62, 0.62, 0.60), 0.55, specular_ior_level=0.4)
    NB.add_bump(m, scale=6000.0, strength=0.08, distance=0.00003, detail=2.0)
    return m


def curve_obj(NB, name, pts, radius, mat):
    import bpy
    from mathutils import Vector
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = Vector(p)
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    ob = NB.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return ob


class Scene:
    pass


def ring_scene(NB, clip=True):
    """the band ring, board, cell, lid, slides, webbing and charge clip; S.apply(t) poses it on the
    ring timeline (TL). Returns a Scene with the groups, transforms and camera helpers."""
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    S = Scene()
    band = NB.load_band()
    mod = NB.load_module()
    bobj = NB.board_into(mod)                       # real KiCad board, module frame (m)
    T = NB.module_to_band(mod, band)
    S.mag = []
    for o in list(mod.values()):
        if NB.kind(o.name) in ('mag_connector', 'mag_contacts'):   # r2: magnetic charging connector in its bay
            o['kind'] = NB.kind(o.name)
            o.matrix_world = T @ o.matrix_world
            S.mag.append(o)
        else:
            bpy.data.objects.remove(o)
    J1_PARTS = ('ClosedCreamFlipbar', 'DarkHousing', 'SolderAnchors', 'TwentyBottomContacts')
    S.j1 = [o for o in bobj.values() if o.name.split('.')[0] in J1_PARTS]
    for o in bobj.values():
        o.matrix_world = T @ o.matrix_world
    Ti = T.inverted()

    def to_mod(p):
        return Ti @ Vector(p)

    groups = {}
    for o in band.values():
        groups.setdefault(o['kind'], []).append(o)
    for o in groups.pop('main_board', []) + groups.pop('board_parts', []):
        bpy.data.objects.remove(o)
    flex = []
    for o in groups.get('flex', []):
        mn, mx = NB.bbox([o])
        c = to_mod((mn + mx) / 2) * 1000
        if abs(c.x) < 1 and c.y < -11 and c.z > 0.5:
            bpy.data.objects.remove(o)               # the installed U-turn tail (a ribbon is modelled)
        else:
            flex.append(o)
    groups['flex'] = flex
    # the webbing as five solids (strap_pieces.glb: band, two wraps, two tails)
    for o in groups.pop('strap', []):
        bpy.data.objects.remove(o)
    sp = NB.import_glb(os.path.join(BUILD, 'strap_pieces.glb'), bake=True)
    straps = {}
    for o in sp.values():
        k = NB.kind(o.name)
        o['kind'] = k
        NB.add_weave_attr(o)
        NB.setmat(o, NB.mat_strap())
        NB.smooth(o, math.radians(35))
        straps[k] = o
    # charge clip and its two pins (module frame) + USB lead
    S.clip = []
    if clip:                                         # r2: the magnetic charging cable's head and lead
        import guide_figures as GF
        mc = (0.5, 19.6, 3.35)                       # connector face centre, module frame (mm)
        head = GF.box_obj(NB, 'cable_head', (0, 0, 0), (0.0145, 0.0060, 0.0045),
                          NB.principled('cable_head', (0.03, 0.03, 0.032), 0.4), bevel=0.0010)
        head.matrix_world = T @ Matrix.Translation((mc[0] / 1000, (mc[1] + 3.05) / 1000, mc[2] / 1000))
        S.clip.append(head)
        usb = [(0.5, 25.0, 3.35), (0.5, 33.0, 2.0), (0.5, 50.0, -6.0), (0.5, 75.0, -22.0), (0.5, 110.0, -34.0)]
        cab = curve_obj(NB, 'usb_lead', [tuple(x / 1000 for x in p) for p in usb], 0.0016,
                        NB.principled('cable', (0.03, 0.03, 0.032), 0.45))
        cab.matrix_world = T.copy()
        S.clip.append(cab)
    # mirror the ring parts to the real flex's pod order
    if NB.MIRROR_RING:
        NB.mirror_ring(list(straps.values()))       # (load_band mirrors the band itself)

    # float the band 12 mm above the floor
    allobj = [o for o in bpy.data.objects if o.type == 'MESH']
    bpy.context.view_layer.update()
    mn, mx = NB.bbox([o for o in allobj if o not in S.clip])
    G = Matrix.Translation((0, 0, 0.012 - mn[2]))
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE'):
            o.matrix_world = G @ o.matrix_world
    T = G @ T
    Ti = T.inverted()
    z_axis = 0.012 - mn[2]                           # ring axis (x = 0, z = z_axis)
    bpy.context.view_layer.update()

    def centre(objs):
        a_, b_ = NB.bbox(objs)
        return Vector(((a_ + b_) / 2).tolist())

    def radial(o):
        c = centre([o])
        return Vector((c.x, 0, c.z - z_axis)).normalized()

    up = (T.to_3x3() @ Vector((0, 0, 1))).normalized()   # module +Z in the band frame
    prox = (T.to_3x3() @ Vector((0, 1, 0))).normalized()
    ring_c = Vector((0, 0.025, z_axis))

    # ------------------------------------------------------------ added parts
    def mat_wire(name, col):
        return NB.principled(name, col, 0.35, coat_weight=0.3, coat_roughness=0.2)

    def lead(name, pts_mm, col):
        ob = curve_obj(NB, name, [tuple(x / 1000 for x in p) for p in pts_mm], 0.00026, mat_wire(name, col))
        ob.matrix_world = T.copy()
        return ob

    # r2: the cell's own leads (module frame, mm): from the cell's lead end over the board to its +X (button
    # side) edge level with J2, down past the edge in the 0.6 mm gap to the wall, back under the board to the
    # J2 pads (VBAT at x 12.8, GND at x 9.8, y -6.6); the J3 charging wires under the board's +X edge to the
    # magnetic connector in the proximal bay
    vbat = [(6.0, -9.9, 5.0), (6.0, -10.6, 4.65), (9.0, -8.6, 4.65), (12.6, -7.0, 4.65), (14.0, -7.0, 3.05), (15.0, -7.0, 3.05),
            (15.0, -7.0, 1.3), (14.2, -7.0, 1.3), (12.8, -6.7, 1.45)]
    gnd = [(4.0, -9.9, 4.6), (4.0, -10.6, 4.05), (8.0, -8.0, 4.05), (12.6, -5.8, 4.05), (14.0, -5.8, 3.05), (15.0, -5.8, 3.05),
           (15.0, -5.8, 1.3), (14.2, -5.8, 1.3), (11.5, -6.1, 1.3), (9.8, -6.5, 1.45)]
    leads = [lead('lead_gnd', gnd, (0.02, 0.02, 0.022)), lead('lead_vbat', vbat, (0.55, 0.045, 0.035))]
    jr = [(9.9, -13.2, 1.6), (11.0, -12.6, 1.2), (12.9, -11.5, 1.2), (12.9, 11.0, 1.2), (11.0, 12.6, 1.4), (4.0, 13.2, 2.2),
          (1.75, 14.0, 3.35), (1.75, 14.3, 3.35)]
    jb = [(12.9, -13.2, 1.6), (13.2, -12.0, 1.2), (13.3, -11.0, 1.2), (13.3, 11.3, 1.2), (11.5, 13.0, 1.4), (2.0, 13.6, 2.2),
          (-0.75, 14.0, 3.35), (-0.75, 14.3, 3.35)]
    S.jwires = [lead('j3_red', jr, (0.55, 0.045, 0.035)), lead('j3_black', jb, (0.02, 0.02, 0.022))]

    # flex tail ribbon (module frame, mm): constant free length while the board folds on it
    TAIL_W, TAIL_T, L_TOT, L_S = 10.5, 0.22, 8.24, 3.8
    P0F = Vector((0, -15.0, 3.2))                    # start of the straight part in the final pose

    def tail_path(s):
        th = math.pi / 2 * s
        yv = -16.0 + 0.5 * (1 - s)
        r1 = -15.0 - yv
        Lv = L_TOT - L_S - th - math.pi / 2 * r1
        pts = []
        for k in range(9):                           # root bend: heading -Y -> +Z
            a = math.radians(270 - 90 * k / 8)
            pts.append((-15.0 + r1 * math.cos(a), -0.1 + r1 + r1 * math.sin(a)))
        z1 = -0.1 + r1 + Lv
        pts.append((yv, z1))
        for k in range(1, 11):                       # top bend: +Z turning toward +Y by th
            a = math.pi - th * k / 10
            pts.append((yv + 1 + math.cos(a), z1 + math.sin(a)))
        p0 = Vector((0, pts[-1][0], pts[-1][1]))
        d = Vector((0, math.sin(th), math.cos(th)))
        for k in range(1, 7):
            q = p0 + d * (L_S * k / 6)
            pts.append((q.y, q.z))
        return pts, p0, math.pi / 2 - th

    def ribbon_verts(pts):
        out = []
        n = len(pts)
        for i, (y, z) in enumerate(pts):
            ya, za = pts[max(i - 1, 0)]
            yb, zb = pts[min(i + 1, n - 1)]
            ty, tz = yb - ya, zb - za
            L = math.hypot(ty, tz) or 1
            ny, nz = -tz / L, ty / L
            for sx in (-1, 1):
                for st in (-1, 1):
                    out.append((sx * TAIL_W / 2 / 1000, (y + st * ny * TAIL_T / 2) / 1000, (z + st * nz * TAIL_T / 2) / 1000))
        return out

    pts0, _, _ = tail_path(1.0)
    vs = ribbon_verts(pts0)
    faces = []
    for i in range(len(pts0) - 1):
        a0, b0 = 4 * i, 4 * (i + 1)
        faces += [(a0 + 1, b0 + 1, b0 + 3, a0 + 3), (a0 + 0, a0 + 2, b0 + 2, b0 + 0),
                  (a0 + 0, b0 + 0, b0 + 1, a0 + 1), (a0 + 2, a0 + 3, b0 + 3, b0 + 2)]
    k = 4 * (len(pts0) - 1)
    faces += [(0, 1, 3, 2), (k, k + 2, k + 3, k + 1)]
    me = bpy.data.meshes.new('tail_ribbon')
    me.from_pydata(vs, [], faces)
    tail = NB.link(bpy.data.objects.new('tail_ribbon', me))
    NB.setmat(tail, NB.mat_flex())
    tail.matrix_world = T.copy()

    def set_tail(s):
        pts, p0, phi = tail_path(s)
        v = np.array(ribbon_verts(pts), dtype=np.float64).ravel()
        me.vertices.foreach_set('co', v)
        me.update()

    def board_H(s, dz_mm):
        p0, phi = tail_path(s)[1:]
        Hm = (Matrix.Translation((p0 + Vector((0, 0, dz_mm))) / 1000.0) @ Matrix.Rotation(phi, 4, 'X')
              @ Matrix.Translation(-P0F / 1000.0))
        return T @ Hm @ Ti

    # ------------------------------------------------------------ groups, final poses
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE'):
            o['M0'] = [list(r) for r in o.matrix_world]

    def M0(o):
        return Matrix(o['M0'])

    pods = groups.get('pod_shells', [])
    num = NB.pod_numbers(pods, z_axis)
    pods = sorted(pods, key=lambda o: num[o.name])
    S.pod_num = {o.name: num[o.name] for o in pods}
    S.pods = pods
    S.flex, S.pads, S.foam = flex, groups.get('pads', []), groups.get('foam', [])
    S.base = groups.get('module_base', [])
    S.lid = groups.get('module_lid', [])
    S.cap = groups.get('button_cap', [])
    S.cell = groups.get('lipo', [])
    S.slides = sorted(groups.get('strap_slide', []), key=lambda o: -centre([o]).x)    # A (+X, by pod 2), B
    S.board = list(bobj.values())
    S.leads = leads
    S.tail = tail
    S.straps = straps
    board_grp = S.board + leads + S.jwires

    # strap pieces: angle round the ring from slide A (+X) through pods 2, 1, 8 ... 5 to slide B
    def angles(o):
        V = NB.verts_np(o)
        return np.mod(np.degrees(np.arctan2(V[:, 0], V[:, 2] - z_axis)), 360.0)

    band_s = straps.get('strap_band')
    ends = [straps[k] for k in NB.STRAP_END_KINDS if k in straps]
    u = angles(band_s)
    r = (u - u.min()) / max(u.max() - u.min(), 1e-6)
    band_s.data.attributes.new('rev', 'FLOAT', 'POINT').data.foreach_set('value', r.astype(np.float32))

    # ------------------------------------------------------------ fade / reveal shaders
    m = band_s.data.materials[0].copy()
    m.name = 'strap_reveal'
    NB.setmat(band_s, m)
    reveal = add_fade(m, reveal=True)
    for m in list(bpy.data.materials):
        if m.name != 'strap_reveal' and m.node_tree is not None:
            add_fade(m)

    # ------------------------------------------------------------ studio
    sweep_mat = NB.mat_paper((0.52, 0.51, 0.49))
    NB.sweep(color=(0.52, 0.51, 0.49), depth=0.8, height=1.0, radius=0.3, origin=(0, 0.025, 0),
             yaw=math.radians(180 + 40), mat=sweep_mat)
    NB.studio(ring_c, key=5, fill=1.4, rim=5, top=2.0)
    cam = NB.camera(NB.orbit(ring_c, 30, 24, 0.33), ring_c, lens=85, fstop=16.0, focus=ring_c)

    mod_c = centre(S.lid)
    S.targets = {'R': ring_c + Vector((0, 0, 0.004)), 'M': mod_c + Vector((0, 0, -0.002)), 'L': T @ Vector((0, -0.010, -0.002)),
                 'H': T @ Vector((0.002, -0.010, 0.013)), 'C': T @ Vector((0.0, 0.016, -0.002)),
                 'A': centre(S.slides[:1]) if S.slides else T @ Vector((-0.0217, 0, 0)),     # r2: no slides; the bars A, B
                 'B': centre(S.slides[1:]) if S.slides else T @ Vector((0.0218, 0, 0))}

    def set_cam(tgt, az, el, d, lens=85):
        loc = NB.orbit(tgt, az, el, d)
        NB.look_at(cam, tgt, loc)
        cam.data.lens = lens
        cam.data.shift_x = cam.data.shift_y = 0.0
        cam.data.sensor_fit = 'AUTO'
        cam.data.sensor_width = 36
        cam.data.dof.focus_distance = (Vector(tgt) - loc).length

    # ------------------------------------------------------------ per-frame state
    def place(o, M, alpha):
        o.matrix_world = M
        o.color = (1, 1, 1, alpha)
        o.hide_render = alpha <= 0.002

    RAD = {o.name: radial(o) for o in bpy.data.objects if o.type == 'MESH'}

    def fly(objs, t, t0, t1, dist, direction=None, stagger=0.0, fade=0.18, out=False):
        n = len(objs)
        for k, o in enumerate(objs):
            s0 = t0 + (stagger * k / max(n - 1, 1) if n > 1 else 0)
            s1 = s0 + (t1 - t0 - stagger)
            p = ph(t, s0, s1)
            if out:                                  # leave instead of arrive
                p = 1 - p
            dvec = direction if direction is not None else RAD[o.name]
            off = dvec * (dist * (1 - ease_out(p)))
            alpha = smooth(p / fade) if (t >= s0 or out) else 0.0
            place(o, Matrix.Translation(off) @ M0(o), alpha)

    def apply(t):
        for o in S.flex + S.pads + S.foam + S.pods + S.base:
            place(o, M0(o), 1.0)
        pin = ph(t, *TL['board_in'])
        s = ease_io(ph(t, *TL['board_swing']))
        dz = 26.0 * (1 - ease_out(pin))
        Hb = board_H(s, dz)
        a_b = smooth(pin / 0.4) if t >= TL['board_in'][0] else 0.0
        for o in board_grp:
            place(o, Hb @ M0(o), a_b)
        set_tail(s)
        tail.matrix_world = M0(tail)
        tail.color = (1, 1, 1, 1)
        tail.hide_render = False
        fly(S.cell, t, *TL['cell'], 0.022, direction=up)
        fly(S.cap, t, *TL['cap'], 0.016, direction=up)
        fly(S.lid, t, *TL['lid'], 0.030, direction=up)
        fly(S.slides, t, *TL['slides'], 0.014, stagger=0.25)
        fly(S.mag, t, *TL['conn'], 0.012, direction=up)
        rs = ease_io(ph(t, *TL['strap']))
        reveal.default_value = rs * 1.002
        place(band_s, M0(band_s), 1.0 if rs > 0 else 0.0)
        fly(ends, t, *TL['tails'], 0.010, stagger=0.3)
        # tuck: each tail swings in round the friction bar and under it
        pp = 1 - ease_out(ph(t, *TL['pull']))
        for o in ends:
            if o.name.startswith('strap_tail') and t >= TL['tails'][0]:
                o.matrix_world = Matrix.Translation(RAD[o.name] * 0.003 * pp) @ M0(o)
        if S.clip:
            p_in = ph(t, *TL['clip'])
            p_out = ph(t, *TL['clip_off'])
            off = prox * 0.030 * (1 - ease_out(p_in)) + prox * 0.030 * ease_io(p_out)
            alpha = smooth(p_in / 0.3) * (1 - smooth(p_out / 0.8)) if t >= TL['clip'][0] else 0.0
            for o in S.clip:
                place(o, Matrix.Translation(off) @ M0(o), alpha)

    S.T, S.Ti, S.up, S.prox, S.z_axis, S.ring_c = T, Ti, up, prox, z_axis, ring_c
    S.cam, S.set_cam, S.apply, S.place, S.M0, S.centre, S.radial = cam, set_cam, apply, place, M0, centre, radial
    S.board_H, S.set_tail, S.reveal, S.band_s, S.ends, S.groups = board_H, set_tail, reveal, band_s, ends, groups
    S.cam_at = lambda t: catmull(CAM, t, S.targets)
    return S


def blender_main(argv):
    import bpy
    sys.path.insert(0, HERE)
    import nb_blender as NB
    import guide_figures as GF

    ap = argparse.ArgumentParser()
    ap.add_argument('--scene', default='ring', choices=('ring', 'jig', 'board', 'pedestal'))
    ap.add_argument('--frames', default='')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--samples', type=int, default=0)
    ap.add_argument('--out', default=os.path.join(BUILD, 'assembly'))
    ap.add_argument('--times', default='', help='debug: render these times (s) to <out>/t_<scene>_<t>.png')
    ap.add_argument('--save-blend', action='store_true')
    a = ap.parse_args(argv)

    NB.reset()
    NB.MATS.clear()
    samples = a.samples or (16 if a.quick else 40)
    sc = NB.setup_render(*RES, samples, a.quick)
    sc.render.resolution_percentage = 50 if a.quick else 100
    sc.render.use_persistent_data = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.max_bounces = 8
    sc.cycles.transparent_max_bounces = 24
    S = {'ring': lambda: ring_scene(NB), 'jig': lambda: jig_scene_r2(NB, GF), 'board': lambda: board_scene(NB),
         'pedestal': lambda: pedestal_scene(NB)}[a.scene]()
    pre = PREFIX[a.scene]

    def render_to(path):
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        NB.vignette(path, 0.14)

    def pose(t):
        S.apply(t)
        tg, az, el, d = S.cam_at(t)
        S.set_cam(tg, az, el, d)

    os.makedirs(a.out, exist_ok=True)
    if a.save_blend:
        pose(9.3 if a.scene == 'ring' else 4.0)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BUILD, 'assembly_%s.blend' % a.scene), compress=True)
    if a.frames:
        st, sp, sd = (int(x) for x in a.frames.split(':'))
        for i in range(st, sp, sd):
            p = os.path.join(a.out, '%s_%04d.png' % (pre, i))
            if os.path.exists(p) and os.path.getsize(p) > 0:
                continue
            pose(i / FPS)
            t1 = time.time()
            render_to(p)
            NB.log('frame %s %d %.1f s' % (pre, i, time.time() - t1))
    if a.times:
        for t in (float(x) for x in a.times.split(',')):
            pose(t)
            render_to(os.path.join(a.out, 't_%s_%05.2f.png' % (a.scene, t)))


# ================================================================ driver side
def run(cmd, log, timeout=3600, env=None):
    t = time.time()
    with open(log, 'w') as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=timeout, env=env)
    print('  %-40s exit %d  %.0f s' % (os.path.basename(log), p.returncode, time.time() - t), flush=True)
    return p.returncode


# ---------------------------------------------------------------- r2: bare board scene (steps 1-2)
def board_scene(NB):
    """the bare main board bottom side up: wires on the SWD pads (flash once, then off), the cell's leads
    onto J2 under Kapton, the J3 charging wires to the magnetic connector. Times: TB (global seconds)."""
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    import guide_figures as GF
    S = Scene()
    mm = 0.001
    bobj, body = NB.load_board()
    objs = list(bobj.values())
    bmn, bmx = NB.bbox([body])
    c = Vector(((bmn + bmx) / 2).tolist())
    Mf = Matrix.Translation(c) @ Matrix.Rotation(math.pi, 4, 'Y') @ Matrix.Translation(-c)
    for o in objs:
        o.matrix_world = Mf @ o.matrix_world
    a_, b_ = NB.bbox(objs)
    G = Matrix.Translation((-c.x, -c.y, 0.0025 - a_[2]))           # centre on the origin, 2.5 mm above the floor
    for o in objs:
        o.matrix_world = G @ o.matrix_world
    Mk = G @ Mf

    def kp(xk, yk, dz=0.0):
        return Mk @ Vector((bmn[0] + xk * mm, bmx[1] - yk * mm, bmn[2] - dz * mm))

    def wmat(name, col):
        return NB.principled(name, col, 0.35, coat_weight=0.3, coat_roughness=0.2)
    cols = {'red': (0.55, 0.045, 0.035), 'black': (0.02, 0.02, 0.022), 'yellow': (0.75, 0.55, 0.05), 'green': (0.05, 0.35, 0.10)}
    tp = [(1.1, 5.1), (2.0, 4.2), (2.9, 3.3), (3.79, 2.41), (4.69, 1.51)]
    swd = []
    for i, key in ((0, 'red'), (1, 'yellow'), (2, 'green'), (4, 'black')):
        x, y = tp[i]
        pts = [kp(x, y, 0.25), kp(x - 0.4, y - 1.6, 0.9), kp(x - 3.0 - 0.8 * i, -4.0 - 1.0 * i, 1.6), kp(-14.0 - 1.6 * i, -16.0 - 1.4 * i, 2.0),
               kp(-30.0 - 1.6 * i, -24.0 - 1.4 * i, 2.0)]
        swd.append(curve_obj(NB, 'swd_%d' % i, [tuple(p) for p in pts], 0.00028, wmat('w_' + key, cols[key])))
    cell = GF.box_obj(NB, 'cell', tuple(kp(28.7 + 4.0 + 12.5, 18.8, -1.4)), (0.025, 0.012, 0.004), NB.mat_lipo(), bevel=0.0006)
    leads = [curve_obj(NB, 'lead_r', [tuple(p) for p in (kp(32.8, 19.6, -1.0), kp(31.0, 19.8, 0.25), kp(28.0, 19.3, 0.25), kp(26.8, 18.9, 0.2))],
                       0.00026, wmat('l_red', cols['red'])),
             curve_obj(NB, 'lead_b', [tuple(p) for p in (kp(32.8, 18.0, -1.0), kp(31.0, 17.2, 0.25), kp(26.0, 17.4, 0.25), kp(23.8, 18.6, 0.2))],
                       0.00026, wmat('l_black', cols['black']))]
    kap = GF.box_obj(NB, 'kapton', tuple(kp(25.3, 18.8, 0.5)), (0.0062, 0.0042, 0.00008),
                     NB.principled('kapton', (0.85, 0.45, 0.05), 0.25, transmission_weight=0.4))
    conn = GF.box_obj(NB, 'connector', tuple(kp(14.5, -6.0, -1.5)), (0.0145, 0.004, 0.004),
                      NB.principled('conn', (0.03, 0.03, 0.032), 0.4), bevel=0.0004)
    jw = [curve_obj(NB, 'j3_r', [tuple(p) for p in (kp(23.9, 25.4, 0.2), kp(25.6, 24.0, 0.45), kp(27.2, 20.0, 0.45), kp(27.2, 3.0, 0.45),
                                                     kp(24.0, -1.0, 0.45), kp(15.75, -3.5, -0.6), kp(15.75, -4.0, -1.5))],
                    0.00026, wmat('j_red', cols['red'])),
          curve_obj(NB, 'j3_b', [tuple(p) for p in (kp(26.9, 25.4, 0.2), kp(27.8, 23.5, 0.45), kp(27.8, 20.0, 0.45), kp(27.8, 3.0, 0.45),
                                                     kp(25.0, -1.5, 0.45), kp(13.25, -3.5, -0.6), kp(13.25, -4.0, -1.5))],
                    0.00026, wmat('j_black', cols['black']))]
    for m in list(bpy.data.materials):
        if m.node_tree is not None:
            add_fade(m)
    tgt = kp(16.0, 10.0)
    NB.sweep(color=(0.52, 0.51, 0.49), depth=0.8, height=1.0, radius=0.3, origin=(0, 0.06, 0),
             yaw=math.radians(180), mat=NB.mat_paper((0.52, 0.51, 0.49)))
    NB.studio(tgt, key=5, fill=1.4, rim=5, top=2.0)
    cam = NB.camera(NB.orbit(tgt, -20, 52, 0.20), tgt, lens=85, fstop=16.0, focus=tgt)

    def place(o, alpha):
        o.color = (1, 1, 1, alpha)
        o.hide_render = alpha <= 0.002

    def apply(t):
        aw = smooth(ph(t, *TB['wires'])) * (1 - smooth(ph(t, *TB['wires_off'])))
        for o in swd:
            place(o, aw)
        for o in [cell] + leads:
            place(o, smooth(ph(t, *TB['cell'])))
        place(kap, smooth(ph(t, *TB['kapton'])))
        for o in [conn] + jw:
            place(o, smooth(ph(t, *TB['conn'])))

    def cam_at(t):
        u = smooth(ph(t, 0.0, 6.4))
        return tgt, -2 + 14 * u, 48 - 4 * u, 0.20

    def set_cam(tg, az, el, d, lens=85):
        loc = NB.orbit(tg, az, el, d)
        NB.look_at(cam, tg, loc)
        cam.data.lens = lens
        cam.data.dof.focus_distance = (Vector(tg) - loc).length
    S.apply, S.cam_at, S.set_cam, S.cam = apply, cam_at, set_cam, cam
    return S


# ---------------------------------------------------------------- r2: pedestal jig scene (stage 2)
def pedestal_scene(NB):
    """the base jig: the strip's pod 3/4 part pads-down on the saddle, then the base (foam dots in its
    pockets) pressed on. Times: TP (global seconds)."""
    import bpy
    from mathutils import Vector, Matrix
    S = Scene()
    jg = NB.import_glb(os.path.join(BUILD, 'base_jig_fit.glb'), bake=True)
    jig, base = [], []
    for o in jg.values():
        k = NB.kind(o.name)
        if k == 'module_base':
            NB.setmat(o, NB.mat_housing())
            base.append(o)
        else:
            NB.setmat(o, mat_tool(NB))
            jig.append(o)
        NB.smooth(o, math.radians(35))
    ma = NB.import_glb(os.path.join(BUILD, 'module_assy.glb'), bake=True)
    Mj = Matrix.Translation((0, 0, 0.02711)) @ Matrix.Rotation(math.pi, 4, 'Z')    # module frame -> jig (base_jig.py)
    flex, dots = [], []
    for o in list(ma.values()):
        k = NB.kind(o.name)
        if k in ('flex_pods_3_4', 'pads', 'tail', 'foam'):
            o.matrix_world = Mj @ o.matrix_world
            NB.setmat(o, {'pads': NB.mat_gold(), 'foam': NB.mat_foam()}.get(k, NB.mat_flex()))
            (dots if k == 'foam' else flex).append(o)
        else:
            bpy.data.objects.remove(o)
    for o in jig + base + flex + dots:
        o['M0'] = [list(r) for r in o.matrix_world]
    for m in list(bpy.data.materials):
        if m.node_tree is not None:
            add_fade(m)
    a_, b_ = NB.bbox(jig)
    tgt = Vector((0.0, 0.0, 0.022))
    NB.sweep(color=(0.52, 0.51, 0.49), depth=0.8, height=1.0, radius=0.3, origin=(0, 0.05, 0),
             yaw=math.radians(180 + 30), mat=NB.mat_paper((0.52, 0.51, 0.49)))
    NB.studio(tgt, key=5, fill=1.4, rim=5, top=2.0)
    cam = NB.camera(NB.orbit(tgt, -30, 26, 0.24), tgt, lens=85, fstop=16.0, focus=tgt)

    def place(o, M, alpha):
        o.matrix_world = M
        o.color = (1, 1, 1, alpha)
        o.hide_render = alpha <= 0.002

    def apply(t):
        pf = ph(t, *TP['flex'])
        for o in flex:
            place(o, Matrix.Translation((0, 0, 0.008 * (1 - ease_out(pf)))) @ Matrix(o['M0']), smooth(pf / 0.6))
        pb = ease_io(ph(t, *TP['base']))
        ab = smooth(ph(t, TP['base'][0] - 0.5, TP['base'][0]))
        for o in base + dots:
            place(o, Matrix.Translation((0, 0, 0.022 * (1 - pb))) @ Matrix(o['M0']), ab)
        for o in jig:
            place(o, Matrix(o['M0']), 1.0)

    def cam_at(t):
        u = smooth(ph(t, 12.0, 16.4))
        return tgt, -34 + 22 * u, 28 - 4 * u, 0.25

    def set_cam(tg, az, el, d, lens=85):
        loc = NB.orbit(tg, az, el, d)
        NB.look_at(cam, tg, loc)
        cam.data.lens = lens
        cam.data.dof.focus_distance = (Vector(tg) - loc).length
    S.apply, S.cam_at, S.set_cam, S.cam = apply, cam_at, set_cam, cam
    return S


def jig_scene_r2(NB, GF):
    """stage 1 on the bonding jig (guide_figures.jig_scene), shifted to global time; no base in r2."""
    S = GF.jig_scene(NB, anim=True, tail_up=False)
    loc_apply, loc_cam = S.apply, S.cam_at

    def apply(t):
        loc_apply(t - JIG_OFF)
        for o in [S.base] + list(S.bdots):
            o.hide_render = True

    S.apply = apply
    S.cam_at = lambda t: loc_cam(t - JIG_OFF)
    return S


def freecad_strap_pieces(step, dst):
    """(run under FreeCAD GUI offscreen) the webbing as five separate solids, rebuilt with
    mech/rev_c/fit.py for the 160 mm wrist exactly as assembly.py builds band_assembly.step (the STEP
    stores them fused): the loop between the slides, and at each slide the locking path (lock: under the
    friction bar, up through the slot, over the bar) and the tail (round the bar's end and back under it).
    _a is the -X slide, _b the +X one (before nb_blender.mirror_ring)."""
    import FreeCAD, ImportGui
    sys.path.insert(0, os.path.join(ROOT, 'mech', 'rev_c'))
    sys.neurband_lib = True
    sys.neurband_fit_lib = True
    import fit as F
    res, items, L = F.build_band(160.0, lambda *x: None, with_wrist=False, cad=False)
    shape = dict((n, sh) for n, sh, c in items)['strap']
    names = ['strap_band', 'strap_lock_a', 'strap_lock_b', 'strap_tail_b']   # r2: run, lock round bar A, wrap round bar B, folded tail
    doc = FreeCAD.newDocument('strap')
    feats = []
    for n, x in zip(names, shape.Solids):
        f = doc.addObject('Part::Feature', n)
        f.Shape = x
        feats.append(f)
    doc.recompute()
    if os.path.exists(dst):
        os.remove(dst)
    ImportGui.export(feats, dst)


def export():
    """STEP -> GLB for the band, module, board, flex, jigs and clip; the webbing pieces."""
    sys.path.insert(0, HERE)
    import make_renders
    make_renders.export()
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', ASSEMBLY_STRAP=os.path.join(ROOT, 'mech/rev_c/band_assembly.step')
               + '=' + os.path.join(BUILD, 'strap_pieces.glb'))
    run([FREECAD, os.path.abspath(__file__)], os.path.join(LOGS, 'strap_pieces.log'), timeout=600, env=env)
    pairs = []
    for n in ('bond_jig_fit', 'base_jig_fit', 'base_jig', 'pod', 'module_base', 'cell_spacer'):     # r2 tools and parts
        pairs.append(os.path.join(ROOT, 'mech/rev_c', n + '.step') + '=' + os.path.join(BUILD, n + '.glb'))
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', STEP2GLB=';'.join(pairs))
    run([FREECAD, os.path.join(HERE, 'step2glb.py')], os.path.join(LOGS, 'step2glb_tools.log'), timeout=900, env=env)


def render_frames(gpus, quick, samples, out):
    os.makedirs(out, exist_ok=True)

    def worker(k, g):
        for scene in [n for n, _, _ in SCENES]:
            f0, f1 = SCENE_FRAMES[scene]
            start = f0 + ((k - f0) % len(gpus))
            cmd = [BLENDER, '-b', '--python', os.path.abspath(__file__), '--', '--scene', scene,
                   '--frames', '%d:%d:%d' % (start, f1, len(gpus)), '--out', out]
            if quick:
                cmd.append('--quick')
            if samples:
                cmd += ['--samples', str(samples)]
            with open(os.path.join(LOGS, 'assembly_%s_gpu%d.log' % (scene, g)), 'w') as log:
                subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=4 * 3600,
                               env=dict(os.environ, CUDA_VISIBLE_DEVICES=str(g)))
    t = time.time()
    th = [threading.Thread(target=worker, args=(k, g)) for k, g in enumerate(gpus)]
    for x in th:
        x.start()
    for x in th:
        x.join()
    need = sum(f1 - f0 for f0, f1 in SCENE_FRAMES.values())
    have = len(glob.glob(os.path.join(out, '[bjpr]_*.png')))
    print('  frames %d/%d  %.1f min' % (have, need, (time.time() - t) / 60), flush=True)
    if have != need:
        sys.exit('assembly render incomplete, see render/build/logs/assembly_*_gpu*.log')


def caption_alpha(t, t0, t1, f=0.3):
    return clamp01((t - t0) / f) * clamp01((t1 - t) / f)


def _caption_frame(args):
    i, src, out = args
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    t = i / FPS
    live = [(n, t0, t1) for n, t0, t1 in SCENES if t0 <= t <= t1 and os.path.exists(os.path.join(src, '%s_%04d.png' % (PREFIX[n], i)))]
    im = Image.open(os.path.join(src, '%s_%04d.png' % (PREFIX[live[0][0]], i))).convert('RGBA')
    if len(live) > 1:                                # cross-fade: the later scene comes in over the overlap
        n2, t0b, _ = live[1]
        a = smooth((t - t0b) / max(live[0][2] - t0b, 1e-3))
        im = Image.blend(im, Image.open(os.path.join(src, '%s_%04d.png' % (PREFIX[n2], i))).convert('RGBA'), a)
    W, H = im.size
    k = W / 1920.0
    f_txt = ImageFont.truetype(os.path.join(FONT_DIR, 'NotoSans-Regular.ttf'), int(34 * k))
    f_num = ImageFont.truetype(os.path.join(FONT_DIR, 'NotoSans-Light.ttf'), int(34 * k))
    f_ttl = ImageFont.truetype(os.path.join(FONT_DIR, 'NotoSans-Light.ttf'), int(28 * k))
    ink = (34, 33, 32)
    x0, yb = int(96 * k), H - int(88 * k)
    layers = []
    for t0, t1, num, txt in CAPTIONS:
        a = caption_alpha(t, t0, t1)
        if a > 0:
            layers.append((a, num, txt))
    ttl = max(caption_alpha(t, -1, 3.0, 0.5), caption_alpha(t, DUR - 3.4, DUR + 1, 0.5))
    if layers or ttl > 0:
        ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
        bg = Image.new('RGBA', im.size, (0, 0, 0, 0))
        d, db = ImageDraw.Draw(ov), ImageDraw.Draw(bg)
        for a, num, txt in layers:
            x = x0
            w_num = int(50 * k) if num else 0
            w_txt = d.textlength(txt, font=f_txt)
            pad = int(20 * k)
            db.rounded_rectangle([x0 - pad, yb - int(40 * k), x0 + w_num + w_txt + pad, yb + int(16 * k)],
                                 radius=int(14 * k), fill=(214, 210, 204, int(200 * a)))
            if num:
                d.text((x, yb), num, font=f_num, fill=ink + (int(150 * a),), anchor='ls')
                x += w_num
                d.line([(x - int(16 * k), yb - int(28 * k)), (x - int(16 * k), yb + int(4 * k))],
                       fill=ink + (int(70 * a),), width=max(1, int(2 * k)))
            d.text((x, yb), txt, font=f_txt, fill=ink + (int(230 * a),), anchor='ls')
        if ttl > 0:
            d.text((x0, int(84 * k)), TITLE, font=f_ttl, fill=ink + (int(170 * ttl),), anchor='ls')
        bg = bg.filter(ImageFilter.GaussianBlur(1.2 * k))
        im = Image.alpha_composite(Image.alpha_composite(im, bg), ov)
    im.convert('RGB').save(os.path.join(out, 'f_%04d.png' % i), compress_level=1)


def encode(src, quick=False):
    from multiprocessing import Pool
    out = src + '_cap'
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, 'f_*.png')):
        os.remove(f)
    with Pool(min(12, os.cpu_count() or 4)) as pool:
        pool.map(_caption_frame, [(i, src, out) for i in range(NF)], chunksize=8)
    pat = os.path.join(out, 'f_%04d.png')
    dst = MEDIA if not quick else os.path.join(BUILD, 'assembly_quick_out')
    os.makedirs(dst, exist_ok=True)
    mp4 = os.path.join(dst, OUT_NAME + '.mp4')
    gif = os.path.join(dst, OUT_NAME + '.gif')
    run(['ffmpeg', '-y', '-framerate', str(FPS), '-i', pat, '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
         '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4], os.path.join(LOGS, 'assembly_mp4.log'))
    run(['ffmpeg', '-y', '-framerate', str(FPS), '-i', pat, '-vf',
         'fps=6,scale=720:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];'
         '[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle', '-loop', '0', gif],   # < 10 MB
        os.path.join(LOGS, 'assembly_gif.log'))
    for f in (mp4, gif):
        print('  %s %.1f MB' % (os.path.relpath(f, ROOT), os.path.getsize(f) / 1e6), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--no-export', action='store_true')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--samples', type=int, default=0)
    ap.add_argument('--gpus', default='0,1')
    ap.add_argument('--encode-only', action='store_true')
    a = ap.parse_args()
    os.makedirs(LOGS, exist_ok=True)
    gpus = [int(g) for g in a.gpus.split(',')]
    out = os.path.join(BUILD, 'assembly_quick' if a.quick else 'assembly')
    t = time.time()
    if not a.no_export and not a.encode_only:
        export()
    if not a.encode_only:
        for f in glob.glob(os.path.join(out, '*.png')):
            os.remove(f)
        render_frames(gpus, a.quick, a.samples, out)
    encode(out, a.quick)
    print('done in %.1f min' % ((time.time() - t) / 60))


if os.environ.get('ASSEMBLY_STRAP') and 'FreeCAD' in sys.modules:      # FreeCAD runs this file as a macro
    freecad_strap_pieces(*os.environ['ASSEMBLY_STRAP'].split('='))
    os._exit(0)
elif __name__ == '__main__':
    if 'bpy' in sys.modules or os.path.basename(sys.argv[0]).startswith('blender'):
        blender_main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    else:
        main()
