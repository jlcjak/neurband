"""Assembly-manual figures for docs/build/assembly.md (driven by render/guide_figures.py).

One technical-illustration system for every figure:
- Blender Workbench (studio light, object outlines, cavity), a light neutral background, low AA,
  orthographic cameras; one fixed colour per part (COL; the legend is on figure 0.1);
- the parts being ADDED are drawn in full colour and get an orange outline (from a mask render);
  parts already assembled are context (full colour) or ghosted (pale, see-through); parts not yet
  relevant are hidden;
- PIL then adds the title, labels with leader lines, dashed travel arrows, step numbers, zoom insets
  (circular) and 2D section diagrams drawn to the CAD dimensions.

Blender side: render(fid, out) builds the scene for one figure and writes <out>/<fid>/*.png + meta.json.
PIL side: compose(fid, src, dst).
"""
import os, sys, math, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build')
FONT_DIR = '/usr/share/fonts/noto'

MANUAL = [                                            # r2 (Nov 2026): open hook-and-loop strap, magnetic charging
    ('0.1', 'kit', 'Kit of parts'),
    ('0.2', 'names', 'Names and directions'),
    ('0.3', 'exploded', 'Exploded overview'),
    ('0.4', 'section', 'One pod on the skin'),
    ('1.1', 'swd_wires', 'Wires on the SWD pads'),
    ('2.1', 'cell_leads', 'Cell leads onto J2'),
    ('2.2', 'j3_wires', 'Charging wires from J3'),
    ('3.1', 'jig', 'The bonding jig (stage 1)'),
    ('3.2', 'flex_on', 'Flex onto the jig'),
    ('3.3', 'dots_pod', 'Foam dots into a pod'),
    ('3.4', 'pods_in', 'Pods into their fences'),
    ('3.5', 'strip', 'The strip after stage 1'),
    ('4.1', 'dots_base', 'Foam dots into the base'),
    ('4.2', 'base_jig', 'Base onto the pedestal (stage 2)'),
    ('5.1', 'j1', 'Tail into J1'),
    ('5.2', 'fold', 'Book-fold the board down'),
    ('5.3', 'bay', 'Connector, leads and wires'),
    ('6.1', 'lid', 'Button cap and lid'),
    ('7.2', 'cut', 'Cutting the strap'),
    ('7.3', 'lock_a', 'Locking the cut end round bar A'),
    ('7.4', 'press', 'Pressing the strap into the pods'),
    ('7.5', 'fold_b', 'Through bar B and fold back'),
    ('8.1', 'wear', 'On the wrist'),
    ('9.1', 'cable', 'The charging cable'),
    ('9.2', 'charge', 'Charging'),
    ('10.1', 'open', 'Opening and re-flashing'),
]
IDS = [m[0] for m in MANUAL]
TITLE = {m[0]: m[2] for m in MANUAL}


def fname(fid):
    slug = dict((m[0], m[1]) for m in MANUAL)[fid]
    return 'm%s_%s' % (fid.replace('.', '-'), slug)


# one colour per part, the whole manual (sRGB 0..1)
COL = dict(base=(0.56, 0.57, 0.58), lid=(0.84, 0.85, 0.86), cap=(0.20, 0.46, 0.86), pod=(0.25, 0.25, 0.27),
           flex=(0.88, 0.58, 0.16), pad=(0.96, 0.82, 0.36), dot=(0.99, 0.94, 0.55), web=(0.15, 0.22, 0.46),
           slide=(0.08, 0.60, 0.60), board=(0.12, 0.36, 0.22), comp=(0.16, 0.16, 0.17), cell=(0.78, 0.79, 0.82),
           jig=(0.90, 0.84, 0.70), clip=(0.50, 0.66, 0.66), pin=(0.82, 0.64, 0.26), red=(0.82, 0.10, 0.08),
           black=(0.10, 0.10, 0.10), kapton=(0.95, 0.60, 0.12), skin=(0.94, 0.80, 0.70), spacer=(0.66, 0.58, 0.78),
           usb=(0.28, 0.28, 0.30), silk=(0.95, 0.95, 0.93), tin=(0.80, 0.80, 0.80), j1=(0.94, 0.92, 0.84),
           wire_y=(0.92, 0.75, 0.10), wire_g=(0.15, 0.55, 0.20), mag=(0.08, 0.60, 0.60), hook=(0.55, 0.30, 0.65),
           ring=(0.70, 0.71, 0.74))
LEGEND = [('base', 'Module base'), ('lid', 'Lid'), ('cap', 'Button cap'), ('board', 'Main board'), ('cell', 'Cell'),
          ('flex', 'Electrode flex'), ('pad', 'Gold pads'), ('dot', 'Foam dots'), ('pod', 'Pods'), ('web', 'Strap'),
          ('hook', 'Strap hook tab'), ('mag', 'Connector'), ('spacer', 'Cell spacer'), ('jig', 'Jigs (tools)'),
          ('kapton', 'Kapton tape'), ('wire_y', 'Wires')]
GHOST = (0.80, 0.81, 0.82)
BG = (0.965, 0.962, 0.955)
W0, H0 = 1400, 900

# module-frame numbers (mm) from mech/rev_c/module.py (r2)
Y_MIN, Y_MAX = -17.45, 19.6
Y_B0 = -14.8
BAT_Y0 = -9.53
D1 = (-12.0, 11.2)
SW1 = (10.8, -12.9)
SNAP_SEGS = ((-11.0, -8.2, 1), (9.2, 11.4, 1), (-11.0, -7.5, -1), (7.5, 11.0, -1))
ROOT_DOT = (0.0, -10.4)
BT_POD = 2.0                     # pod face -> channel floor (rc.BASE_T, r2)
TAIL_SLOT_Y = (-16.45, -14.65)
BAR_A = (-21.72, -0.1)           # bar centres (x, z), module frame; slot A 4.4 mm, slot B 3.5 mm
BAR_B = (21.76, -0.1)
MAG_C = (0.5, 19.6, 3.35)        # magnetic connector face centre
NOTCH = (0.5, 19.6, 6.85)        # pry notch, lid edge above the connector bay
J2_K = ((26.8, 18.8), (23.8, 18.8))       # VBAT (+), GND (-), board bottom
TP_K = [(1.1, 5.1), (2.0, 4.2), (2.9, 3.3), (3.79, 2.41), (4.69, 1.51)]
TP_NAMES = ['TP1 +3V3', 'TP2 SWDIO', 'TP3 SWDCLK', 'TP4 NRST', 'TP5 GND']
J3_K = ((23.9, 25.4), (26.9, 25.4))       # VCHG 5 V (+), GND, board bottom


# ============================================================== Blender side
class Rec:
    def __init__(self, fid, out):
        self.fid, self.out, self.shots = fid, out, {}
        os.makedirs(out, exist_ok=True)


def wb_scene():
    import bpy
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'OBJECT'
    sh.show_object_outline = True
    sh.object_outline_color = (0.08, 0.08, 0.09)
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    sh.show_shadows = False
    sc.display.render_aa = '8'
    sc.view_settings.view_transform = 'Standard'
    try:
        sc.view_settings.look = 'None'
    except Exception:
        pass
    if sc.world is None:
        sc.world = bpy.data.worlds.new('w')
    sc.world.color = tuple(c ** 2.2 for c in BG)
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.resolution_percentage = 100
    for n in ('sweep', 'pedestal'):
        o = bpy.data.objects.get(n)
        if o:
            o.hide_render = True
    return sc


def lin(c):
    return tuple(x ** 2.2 for x in c)


def paint(objs, key, mode='on'):
    """mode: 'on' full colour, 'ghost' pale and see-through, 'hide'."""
    c = COL[key] if isinstance(key, str) else key
    for o in objs:
        if o is None:
            continue
        if mode == 'hide':
            o.hide_render = True
            o['mode'] = 'hide'
            continue
        o.hide_render = False
        if mode == 'ghost':
            g = tuple(0.35 * a + 0.65 * b for a, b in zip(c, GHOST))
            o.color = (*lin(g), 0.30)
        else:
            o.color = (*lin(tuple(min(1.0, 0.06 + 1.18 * x) for x in c)), 1.0)
        o['mode'] = mode
        o['rgba'] = list(o.color)


def paint_board(objs, mode='on', flex=False):
    for o in objs:
        m = o.data.materials[0].name.lower() if (o.type == 'MESH' and o.data.materials) else ''
        if any(k in m for k in ('fr4', 'polyimide', 'coverlay', 'mask')):
            key = 'flex' if flex else 'board'
        elif 'enig' in m or 'gold' in m:
            key = 'pad'
        elif 'silk' in m:
            key = 'silk'
        elif 'tin' in m or 'solder' in m:
            key = 'tin'
        elif 'actuator' in m:
            key = 'j1'
        else:
            key = 'comp'
        paint([o], key, mode)


def ortho(cam, target, az, el, dist=1.0):
    import bpy
    from mathutils import Vector
    import nb_blender as NB
    NB.look_at(cam, Vector(target), NB.orbit(Vector(target), az, el, dist))
    cam.data.type = 'ORTHO'
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.shift_x = cam.data.shift_y = 0.0
    cam.data.clip_start = 0.001
    cam.data.clip_end = 10.0
    bpy.context.view_layer.update()


def fit(cam, pts, w, h, margin=1.12, off=(0.0, 0.0)):
    """ortho scale and shift so the points fill the frame (margin > 1 leaves room)."""
    import bpy
    import numpy as np
    bpy.context.view_layer.update()
    M = np.array(cam.matrix_world.inverted())
    P = np.asarray(pts, dtype=float)
    q = P @ M[:3, :3].T + M[:3, 3]
    x0, x1, y0, y1 = q[:, 0].min(), q[:, 0].max(), q[:, 1].min(), q[:, 1].max()
    asp = w / h
    width = max(x1 - x0, (y1 - y0) * asp) * margin
    cam.data.ortho_scale = width
    cam.data.shift_x = (x0 + x1) / 2 / width + off[0]
    cam.data.shift_y = (y0 + y1) / 2 / width + off[1]
    bpy.context.view_layer.update()


def pts_of(objs):
    import numpy as np
    import nb_blender as NB
    return np.vstack([NB.verts_np(o) for o in objs if o.type == 'MESH' and len(o.data.vertices)])


def ctr(objs):
    from mathutils import Vector
    import nb_blender as NB
    a, b = NB.bbox([o for o in objs if o.type == 'MESH'])
    return Vector(((a + b) / 2).tolist())


def shot(R, name, cam, w, h, anchors=None, paths=None, hi=None):
    """render the current state to <out>/<name>.png; anchors/paths (world points) projected to pixels;
    hi: objects for the orange outline (mask render: hi white, opaque non-ghost objects black)."""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = w, h
    for o in bpy.data.objects:                         # scene helpers may reset colours / visibility
        if 'mode' in o.keys():
            o.hide_render = o['mode'] == 'hide'
            if 'rgba' in o.keys() and o['mode'] != 'hide':
                o.color = tuple(o['rgba'])
    p = os.path.join(R.out, name + '.png')
    sc.render.filepath = p
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)

    def pr(q):
        v = world_to_camera_view(sc, cam, Vector(q))
        return [round(v.x * w, 1), round((1 - v.y) * h, 1)]
    rec = dict(file=name + '.png', size=[w, h], pts={k: pr(v) for k, v in (anchors or {}).items()},
               paths={k: [pr(q) for q in v] for k, v in (paths or {}).items()})
    if hi:
        sh = sc.display.shading
        st = (sh.light, sh.show_object_outline, sh.show_cavity, tuple(sc.world.color))
        saved = {}
        names = set(o.name for o in hi)
        for o in bpy.data.objects:
            if o.type not in ('MESH', 'CURVE') or o.hide_render:
                continue
            saved[o.name] = (tuple(o.color), o.hide_render)
            if o.name in names:
                o.color = (1, 1, 1, 1)
            elif o.get('mode') == 'ghost' or o.color[3] < 0.99:
                o.hide_render = True
            else:
                o.color = (0, 0, 0, 1)
        sh.light, sh.show_object_outline, sh.show_cavity = 'FLAT', False, False
        sc.world.color = (0, 0, 0)
        mp = os.path.join(R.out, name + '_mask.png')
        sc.render.filepath = mp
        bpy.ops.render.render(write_still=True)
        sh.light, sh.show_object_outline, sh.show_cavity = st[0], st[1], st[2]
        sc.world.color = st[3]
        for o in bpy.data.objects:
            if o.name in saved:
                o.color, o.hide_render = saved[o.name]
        rec['mask'] = name + '_mask.png'
    R.shots[name] = rec


def save_meta(R):
    with open(os.path.join(R.out, 'meta.json'), 'w') as f:
        json.dump(R.shots, f, indent=1)


def new_cam():
    import bpy
    import nb_blender as NB
    c = bpy.data.cameras.new('mcam')
    o = NB.link(bpy.data.objects.new('mcam', c))
    return o


# ---------------------------------------------------------------- scenes
def ring(NB, clip=False):
    """assembly_anim.ring_scene in its final state (no motion), all parts in their manual colours."""
    import assembly_anim as AA
    S = AA.ring_scene(NB, clip=clip)
    S.apply(23.9 if not clip else 20.9)
    wb_scene()
    S.webs = [S.band_s] + list(S.ends)
    colour_ring(S)
    return S


def colour_ring(S, modes=None):
    m = modes or {}
    paint(S.flex + [S.tail], 'flex', m.get('flex', 'on'))
    paint(S.pads, 'pad', m.get('flex', 'on'))
    paint(S.foam, 'dot', m.get('foam', 'on'))
    paint(S.pods, 'pod', m.get('pods', 'on'))
    paint(S.base, 'base', m.get('base', 'on'))
    paint(S.lid, 'lid', m.get('lid', 'on'))
    paint(S.cap, 'cap', m.get('cap', 'on'))
    paint(S.cell, 'cell', m.get('cell', 'on'))
    paint(S.slides, 'slide', m.get('slides', 'on'))
    paint(S.webs, 'web', m.get('web', 'on'))
    paint_board(S.board, m.get('board', 'on'))
    paint([S.leads[0]], 'black', m.get('leads', 'on'))
    paint([S.leads[1]], 'red', m.get('leads', 'on'))
    paint(getattr(S, 'mag', []), 'mag', m.get('mag', 'on'))
    for o, k in zip(getattr(S, 'jwires', []), ('red', 'black')):
        paint([o], k, m.get('jwires', m.get('leads', 'on')))
    if S.clip:
        for o in S.clip:
            paint([o], 'pin' if o.get('kind') == 'pogo_pins' else ('usb' if o.type == 'CURVE' else 'clip'), m.get('clip', 'on'))


def mod_pt(S, p):
    """module-frame point (mm) -> band world (m)"""
    from mathutils import Vector
    return S.T @ Vector((p[0] / 1000, p[1] / 1000, p[2] / 1000))


def place_board(S, s, dz):
    """book-fold state of the board group + tail (s 0 upright .. 1 folded down; dz mm lift)."""
    Hb = S.board_H(s, dz)
    for o in S.board + S.leads:
        o.matrix_world = Hb @ S.M0(o)
    S.set_tail(s)
    return Hb


# ---------------------------------------------------------------- figures
def f_kit(R, NB):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    import guide_figures as GF
    wb_scene()
    mm = 0.001
    items = {}

    def imp(fn, kinds=None):
        objs = NB.import_glb(os.path.join(BUILD, fn), bake=True)
        out = {}
        for o in list(objs.values()):
            k = NB.kind(o.name)
            if kinds and k not in kinds:
                bpy.data.objects.remove(o)
                continue
            out.setdefault(k, []).append(o)
        return out

    def put(objs, x, y, rot_z=0.0, flip=False, z0=None):
        """move objs so their bbox centre (xy) is at (x, y) mm and they rest on z = 0."""
        bpy.context.view_layer.update()
        for o in objs:
            if o.data.users > 1:
                o.data = o.data.copy()
            o.data.transform(o.matrix_world)
            o.matrix_world = Matrix.Identity(4)
        for o in objs:
            if flip:
                o.data.transform(Matrix.Rotation(math.pi, 4, 'Y'))
            if rot_z:
                o.data.transform(Matrix.Rotation(rot_z, 4, 'Z'))
        a, b = NB.bbox(objs)
        c = (a + b) / 2
        for o in objs:
            o.data.transform(Matrix.Translation((x * mm - c[0], y * mm - c[1], -a[2])))
            o.data.update()
        return objs
    ma = imp('module_assy.glb', ('module_base', 'module_lid', 'button_cap', 'lipo'))
    items['base'] = put(ma['module_base'], 222, 82)
    items['lid'] = put(ma['module_lid'], 266, 82, flip=False)
    items['cap'] = put(ma['button_cap'], 150, 28)
    items['cell'] = put(ma['lipo'], 305, 82)
    for k in ('base', 'lid', 'cap', 'cell'):
        paint(items[k], k)
    jg = imp('bond_jig.glb')
    items['bond_jig'] = put(sum(jg.values(), []), 75, 140)
    sj = imp('swd_jig.glb')
    items['swd_jig'] = put(sum(sj.values(), []), 188, 140)
    cc = imp('charge_clip.glb')
    items['clip'] = put(sum(cc.values(), []), 240, 140)
    cs = imp('cell_spacer.glb')
    items['spacer'] = put(sum(cs.values(), []), 285, 140)
    paint(items['bond_jig'] + items['swd_jig'], 'jig')
    paint(items['clip'], 'clip')
    paint(items['spacer'], 'spacer')
    pods = []
    for i in range(6):
        pp = imp('pod.glb')
        pods.append(put(sum(pp.values(), []), 8 + 17 * i, 28))
        paint(pods[-1], 'pod')
    items['pods'] = sum(pods, [])
    sls = []
    for i in range(2):
        sp = imp('strap_slide.glb')
        sls.append(put(sum(sp.values(), []), 118 + 13 * i, 28, rot_z=math.pi / 2))
        paint(sls[-1], 'slide')
    items['slides'] = sum(sls, [])
    bobj, body = NB.load_board()
    items['board'] = put(list(bobj.values()), 178, 82)
    paint_board(items['board'])
    fl, _ = NB.load_board(os.path.join(BUILD, 'flex_board.glb'), flex=True)
    items['flex'] = put(list(fl.values()), 75, 82)
    paint_board(items['flex'], flex=True)
    dots = []
    for i in range(25):
        d = GF.dot_obj(NB, 'kdot%d' % i, NB.mat_foam())
        d.data.transform(d.matrix_world)
        d.matrix_world = Matrix.Identity(4)
        d.data.transform(Matrix.Translation((mm * (170 + 8 * (i % 5)), mm * (44 - 8 * (i // 5)), 0.001)))
        dots.append(d)
    paint(dots, 'dot')
    items['dots'] = dots
    pins = []
    for i in range(7):
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.00034, depth=0.0162,
                                            location=(mm * (222 + 3.2 * i), mm * 28, 0.00034), rotation=(math.pi / 2, 0, 0))
        pins.append(bpy.context.active_object)
    paint(pins, 'pin')
    items['pins'] = pins
    bpy.ops.mesh.primitive_cube_add(size=1, location=(mm * 115, mm * -14, mm * 0.75))
    web = bpy.context.active_object
    web.scale = (0.220, 0.020, 0.0015)
    paint([web], 'web')
    import assembly_anim as AA
    usb = AA.curve_obj(NB, 'usb', [(mm * 256, mm * 24, 0.0016), (mm * 268, mm * 30, 0.0016), (mm * 280, mm * 26, 0.0016),
                                   (mm * 290, mm * 32, 0.0016)], 0.0018, NB.mat_foam())
    rw = AA.curve_obj(NB, 'usbr', [(mm * 290, mm * 32, 0.0016), (mm * 298, mm * 36, 0.0008), (mm * 304, mm * 36, 0.0008)], 0.0005, NB.mat_foam())
    bw = AA.curve_obj(NB, 'usbb', [(mm * 290, mm * 32, 0.0016), (mm * 299, mm * 29, 0.0008), (mm * 305, mm * 29, 0.0008)], 0.0005, NB.mat_foam())
    paint([usb], 'usb')
    paint([rw], 'red')
    paint([bw], 'black')
    cam = new_cam()
    ortho(cam, (0.15, 0.04, 0), 0, 90)
    allp = pts_of([o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render])
    fit(cam, allp, W0, 840, margin=1.04, off=(0, 0.01))

    def bot(objs):
        a, b = NB.bbox(objs)
        return Vector(((a[0] + b[0]) / 2, a[1], b[2]))
    anchors = {k: bot(v) for k, v in items.items()}
    anchors['web'] = Vector((mm * 115, mm * -24, 0.0015))
    anchors['webr'] = Vector((mm * 225, mm * -14, 0.0015))
    anchors['usb'] = Vector((mm * 280, mm * 20, 0.002))
    shot(R, 'main', cam, W0, 840, anchors)


def f_names(R, NB):
    import bpy
    from mathutils import Vector
    S = ring(NB)
    cam = new_cam()
    ortho(cam, S.ring_c, 12, 18)
    fit(cam, pts_of(S.pods + S.lid + S.slides + [S.band_s]), 980, 860, margin=1.25)
    a = {}
    for o in S.pods:
        a['pod%d' % S.pod_num[o.name]] = ctr([o]) + Vector((0, -0.017, 0))
    a['pod3'] = mod_pt(S, (9, -16, -1))
    a['pod4'] = mod_pt(S, (-9, -16, -1))
    a['lid'] = ctr(S.lid) + S.up * 0.004
    a['j1end'] = mod_pt(S, (0, Y_MIN - 0.5, 4))
    a['button'] = ctr(S.cap) + S.up * 0.001
    a['antenna'] = mod_pt(S, (-15.5, -8, 5))
    a['slideA'] = ctr(S.slides[:1])
    a['slideB'] = ctr(S.slides[1:])
    p1 = [o for o in S.pods if S.pod_num[o.name] == 1][0]
    p8 = [o for o in S.pods if S.pod_num[o.name] == 8][0]
    gp = (ctr([p1]) + ctr([p8])) / 2
    a['gap'] = Vector((gp.x * 0.85, gp.y - 0.015, S.z_axis + (gp.z - S.z_axis) * 0.85))
    shot(R, 'main', cam, 980, 860, a)


def f_exploded(R, NB):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    import guide_figures as GF
    S = ring(NB)
    up, rad = S.up, S.radial
    rd = GF.dot_obj(NB, 'root_dot', NB.mat_foam())
    rd.matrix_world = S.T @ Matrix.Translation((0, -0.0104, -0.0004))
    rd['M0'] = [list(r) for r in rd.matrix_world]
    paint([rd], 'dot')
    for o in S.leads:
        o.hide_render = True
    moves = [(o, rad(o) * 0.007) for o in S.foam + [rd]] + [(o, rad(o) * 0.016) for o in S.pods] + \
            [(o, rad(o) * 0.026) for o in S.slides] + [(o, up * 0.012) for o in S.base] + \
            [(o, up * 0.023) for o in S.board] + [(o, up * 0.033) for o in S.cell] + \
            [(o, up * 0.044) for o in S.lid] + [(o, up * 0.054) for o in S.cap]
    a, paths = {}, {}
    for o, v in moves:
        o.matrix_world = Matrix.Translation(v) @ S.M0(o)
    for o in S.webs:
        V = NB.verts_np(o, world=False)
        th = np.arctan2(V[:, 0], V[:, 2] - S.z_axis)
        V[:, 0] += 0.025 * np.sin(th)
        V[:, 2] += 0.025 * np.cos(th)
        o.data.vertices.foreach_set('co', V.ravel())
        o.data.update()
    bpy.context.view_layer.update()
    for key, grp, v in (('lid', S.lid, up * 0.044), ('cap', S.cap, up * 0.054), ('cell', S.cell, up * 0.033),
                        ('board', [S.board[0]], up * 0.023), ('base', S.base, up * 0.012)):
        c = ctr(grp)
        a[key] = c
        paths['t_' + key] = [c - v + up * 0.002, c]
    p1 = [o for o in S.pods if S.pod_num[o.name] == 2][0]
    a['pod'] = ctr([p1])
    paths['t_pod'] = [ctr([p1]) - rad(p1) * 0.016, ctr([p1])]
    a['slide'] = ctr(S.slides[:1])
    fo = max(S.foam, key=lambda o: ctr([o]).x + 0.2 * ctr([o]).z)
    a['foam'] = ctr([fo])
    fl = max(S.flex, key=lambda o: ctr([o]).x - 0.3 * ctr([o]).z)
    a['flex'] = ctr([fl])
    a['tail'] = ctr([S.tail])
    V = NB.verts_np(S.band_s)
    a['web'] = Vector(V[np.argmax(V[:, 0] - V[:, 2])].tolist())
    cam = new_cam()
    ortho(cam, S.ring_c + up * 0.02, 18, 14)
    fit(cam, pts_of(S.pods + S.lid + S.cap + [S.band_s] + S.slides), 1000, 900, margin=1.08)
    shot(R, 'main', cam, 1000, 900, a, paths)


def f_section(R, NB):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    wb_scene()
    objs = NB.import_glb(os.path.join(BUILD, 'guide_xsec.glb'), bake=True)
    by = {}
    for o in objs.values():
        k = NB.kind(o.name)
        by[k] = o
        paint([o], {'skin': 'skin', 'pad': 'pad', 'flex': 'flex', 'foam': 'dot', 'pod': 'pod', 'webbing': 'web'}.get(k, 'pod'))
    mn, mx = NB.bbox(list(objs.values()))
    ymax = mx[1]
    pb, fb, padb, sb, wbx = (NB.bbox([by[k]]) for k in ('pod', 'foam', 'pad', 'skin', 'webbing'))
    z0 = pb[0][2]
    F = lambda x, z: Vector((x, ymax, z))
    a = dict(pod=F(-0.0040, z0 + 0.0013), web=F(-0.0010, z0 + 0.00285), foam=F(0.0010, (fb[0][2] + fb[1][2]) / 2),
             flex=F(-0.0018, padb[1][2] + 0.0001), pad=F(0.0020, (padb[0][2] + padb[1][2]) / 2), skin=F(0.007, sb[1][2] - 0.003))
    zc = sb[1][2] - 0.030
    rr = z0 + 0.0036 - zc + 0.0024
    paths = dict(slide=[Vector((rr * math.sin(t), ymax, zc + rr * math.cos(t))) for t in np.linspace(-0.42, 0.42, 30)])
    Vf = NB.verts_np(by['flex'])
    a['link'] = Vector((Vf[:, 0].max() - 0.002, ymax, Vf[Vf[:, 0].argmax()][2] + 0.0006))
    cam = new_cam()
    tgt = Vector((0, ymax, (z0 + mn[2]) / 2))
    ortho(cam, tgt, 172, 8)
    fit(cam, pts_of(list(objs.values())), W0, 820, margin=1.10, off=(0, 0.02))
    shot(R, 'main', cam, W0, 820, a, paths)


# --- SWD jig
def swd_scene(NB):
    import bpy
    from mathutils import Vector, Matrix
    import assembly_anim as AA
    wb_scene()
    objs = NB.import_glb(os.path.join(BUILD, 'swd_jig_fit.glb'), bake=True)
    jig, pins = None, []
    for o in objs.values():
        if NB.kind(o.name) == 'swd_jig':
            jig = o
        else:
            pins.append(o)
    pins.sort(key=lambda o: ctr([o]).x)
    bobj, body = NB.load_board()
    bmn, bmx = NB.bbox([body])
    M = Matrix.Translation((-bmn[0], -bmx[1], 0.0165 - bmn[2]))
    for o in bobj.values():
        o.matrix_world = M @ o.matrix_world
    wires = []
    cols = ['red', 'wire_y', 'wire_g', None, 'black']
    mm = 0.001
    for i, x in enumerate([16.00 + 1.27 * k for k in range(5)]):
        if cols[i] is None:
            continue
        sx = -1 if i % 2 else 1
        p = [(x * mm + sx * 0.0004, -0.0257, 0.0019), (x * mm + sx * 0.0004, -0.0270, 0.0012), (x * mm, -0.031, 0.0008),
             (x * mm - 0.002, -0.040, 0.0008), (x * mm - 0.010 + i * 0.002, -0.058, 0.0009)]
        wv = AA.curve_obj(NB, 'wire%d' % i, p, 0.0005, NB.mat_foam())
        paint([wv], cols[i])
        wires.append(wv)
    paint([jig], 'jig')
    paint(pins, 'pin')
    paint_board(list(bobj.values()))
    return jig, pins, list(bobj.values()), body, wires, M


def f_swd_pins(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    jig, pins, board, body, wires, M = swd_scene(NB)
    paint(board + wires, 'board', 'hide')
    paint([jig], 'jig', 'ghost')
    for o in pins:
        o.matrix_world = Matrix.Translation((0, 0, -0.012)) @ o.matrix_world
    cam = new_cam()
    tgt = ctr([jig])
    ortho(cam, tgt, 24, -24)
    fit(cam, pts_of([jig] + pins), 1000, 860, margin=1.12)
    a, paths = {}, {}
    for i, o in enumerate(pins):
        a['pin%d' % i] = ctr([o])
        top = Vector((ctr([o]).x, ctr([o]).y, NB.bbox([o])[1][2]))
        paths['t%d' % i] = [top, top + Vector((0, 0, 0.010))]
    a['jig'] = Vector((0.004, -0.028, 0.010))
    a['pocket'] = Vector((0.0185, -0.031, 0.0005))
    a['nest'] = Vector((0.010, -0.010, 0.0165))
    shot(R, 'main', cam, 1000, 860, a, paths, hi=pins)


def f_swd_wiring(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    wb_scene()
    bobj, body = NB.load_board()
    objs = list(bobj.values())
    paint_board(objs)
    bmn, bmx = NB.bbox([body])
    cam = new_cam()
    c = (bmn + bmx) / 2
    ortho(cam, Vector(c.tolist()), 0, -90)                 # from below: the bottom side
    fit(cam, pts_of([body]), 560, 540, margin=1.10)
    mm = 0.001
    kp = lambda xk, yk: Vector((bmn[0] + xk * mm, bmx[1] - yk * mm, bmn[2]))
    a = {('tp%d' % i): kp(*TP_K[i]) for i in range(5)}
    a['j2p'], a['j2m'] = kp(*J2_K[0]), kp(*J2_K[1])
    a['j1'] = kp(14.0, 26.8)
    shot(R, 'board', cam, 560, 540, a)


def f_swd_board(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    jig, pins, board, body, wires, M = swd_scene(NB)
    lift = Matrix.Translation((0, 0, 0.010))
    for o in board:
        o.matrix_world = lift @ o.matrix_world
    paint([jig], 'jig')
    cam = new_cam()
    tgt = Vector((0.014, -0.014, 0.017))
    ortho(cam, tgt, 28, 34)
    fit(cam, pts_of([jig, body]), 1000, 860, margin=1.10)
    bmn, bmx = NB.bbox([body])
    a, paths = {}, {}
    for k, (x, y) in enumerate(((bmn[0] + 0.001, bmx[1] - 0.001), (bmx[0] - 0.001, bmx[1] - 0.001), (bmn[0] + 0.001, bmn[1] + 0.001))):
        paths['t%d' % k] = [Vector((x, y, bmn[2])), Vector((x, y, 0.0167))]
    a['board'] = Vector(((bmn[0] + bmx[0]) / 2, (bmn[1] + bmx[1]) / 2, bmx[2]))
    a['j1'] = Vector((0.014, bmn[1] + 0.0015, bmx[2] + 0.001))
    a['pins'] = Vector((0.0185, -0.0257, 0.0179))
    a['wires'] = Vector((0.017, -0.045, 0.0009))
    a['jig'] = Vector((0.032, -0.010, 0.012))
    shot(R, 'main', cam, 1000, 860, a, paths, hi=board)


# --- cell leads (board bottom up)
def f_cell_leads(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    import assembly_anim as AA
    import guide_figures as GF
    wb_scene()
    bobj, body = NB.load_board()
    objs = list(bobj.values())
    bmn, bmx = NB.bbox([body])
    mm = 0.001
    # bottom side up: rotate 180 deg about the board's long (y) axis
    c = Vector(((bmn + bmx) / 2).tolist())
    Mf = Matrix.Translation(c) @ Matrix.Rotation(math.pi, 4, 'Y') @ Matrix.Translation(-c)
    for o in objs:
        o.matrix_world = Mf @ o.matrix_world
    paint_board(objs)
    kp = lambda xk, yk: Mf @ Vector((bmn[0] + xk * mm, bmx[1] - yk * mm, bmn[2]))
    pv, pg = kp(*J2_K[0]), kp(*J2_K[1])
    edge = kp(25.4, 27.0)
    cy = edge.y - 0.004 - 0.0125
    cx = (pv.x + pg.x) / 2
    zb = pv.z
    cell = GF.box_obj(NB, 'cell', (cx, cy, zb - 0.0013), (0.012, 0.025, 0.004), NB.mat_lipo(), bevel=0.0006)
    paint([cell], 'cell')
    yl = cy + 0.0125
    zt = zb + 0.0002
    red = AA.curve_obj(NB, 'lr', [(pv.x + 0.0013, yl, zb - 0.0005), (pv.x + 0.0006, yl + 0.002, zt), (pv.x, pv.y + 0.0016, zt), (pv.x, pv.y - 0.0004, zt)], 0.00028, NB.mat_foam())
    blk = AA.curve_obj(NB, 'lb', [(pg.x - 0.0013, yl, zb - 0.0005), (pg.x - 0.0006, yl + 0.002, zt), (pg.x, pg.y + 0.0016, zt), (pg.x, pg.y - 0.0004, zt)], 0.00028, NB.mat_foam())
    paint([red], 'red')
    paint([blk], 'black')
    kap = GF.box_obj(NB, 'kap', ((pv.x + pg.x) / 2, pv.y + 0.0004, zt + 0.0004), (0.0062, 0.0050, 0.00006), NB.mat_foam())
    paint([kap], 'kapton')
    kap.color = (*lin(COL['kapton']), 0.55)
    kap['rgba'] = list(kap.color)
    cam = new_cam()
    ortho(cam, c, 0, 90)
    fit(cam, pts_of([body, cell]), 1000, 860, margin=1.10)
    a = {('tp%d' % i): kp(*TP_K[i]) for i in range(5)}
    a['j2p'], a['j2m'] = pv, pg
    a['j3v'], a['j3g'] = kp(*J3_K[0]), kp(*J3_K[1])
    a['edge'] = kp(8.0, 27.0)
    a['cell'] = Vector((cx, cy - 0.004, zb))
    a['kap'] = Vector(((pv.x + pg.x) / 2 + 0.002, pv.y + 0.0018, zt))
    a['red'] = Vector((pv.x, (yl + pv.y) / 2, zt))
    a['blk'] = Vector((pg.x, (yl + pg.y) / 2, zt))
    shot(R, 'main', cam, 1000, 860, a, hi=[red, blk, kap])


# --- bonding jig
def jig(NB, tail_up=False):          # r2 stage 1: no base on this jig, the tail lies flat
    import guide_figures as GF
    S = GF.jig_scene(NB, tail_up=tail_up)
    wb_scene()
    paint([S.jig], 'jig')
    paint(S.flex, 'flex')
    paint_board(S.flex, flex=True)
    paint(list(S.pods.values()), 'pod')
    for k in S.dots:
        paint(S.dots[k], 'dot')
    paint([S.base], 'base')
    paint(S.bdots, 'dot')
    S.pose_flex()
    for k in S.pods:
        S.pose_pod(k)
    S.pose_base()
    return S


def jig_x(xd):
    import guide_figures as GF
    return GF.x_of(xd) * 0.001


def f_jig(R, NB):
    from mathutils import Vector
    S = jig(NB)
    paint(S.flex + list(S.pods.values()) + sum(S.dots.values(), []) + [S.base] + S.bdots, 'pod', 'hide')
    cam = new_cam()
    ortho(cam, ctr([S.jig]), -14, 44)
    fit(cam, pts_of([S.jig]), W0, 820, margin=1.12)
    a = {}
    for k, xd in zip((1, 2, 5, 6, 7, 8), (-45, -27, 27, 45, 63, 81)):
        a['n%d' % k] = Vector((jig_x(xd), -0.023, 0.002))
    a['saddle'] = Vector((0.0, -0.004, 0.0019))
    a['pin'] = Vector((jig_x(-45), 0.005, 0.0006))
    a['gap'] = Vector((0.0, 0.019, 0.0025))
    a['fence'] = Vector((jig_x(81) + 0.0053, 0.0, 0.0025))
    a['ledge'] = Vector((jig_x(63) + 0.0042, -0.012, 0.0008))
    a['stops'] = Vector((0.0137, -0.010, 0.0005))
    shot(R, 'main', cam, W0, 820, a)


def f_flex_on(R, NB):
    from mathutils import Vector, Matrix
    S = jig(NB, tail_up=False)
    paint(list(S.pods.values()) + sum(S.dots.values(), []) + [S.base] + S.bdots, 'pod', 'hide')
    cam2 = new_cam()
    p = Vector((jig_x(-45), 0.005, 0.0))
    ortho(cam2, p, -20, 55)
    cam2.data.ortho_scale = 0.0045
    shot(R, 'zoom', cam2, 500, 500, {'c': p})
    S.pose_flex(dz=0.008)
    cam = new_cam()
    ortho(cam, ctr([S.jig]), -14, 40)
    fit(cam, pts_of([S.jig]), W0, 820, margin=1.12)
    a, paths = {}, {}
    for k, x in enumerate((-45, 27, 81)):
        q = Vector((jig_x(x), 0.005, 0.0006))
        paths['t%d' % k] = [q + Vector((0, 0, 0.008)), q]
    a['pinhole'] = Vector((jig_x(-45), 0.005, 0.0086))
    a['flex'] = Vector((jig_x(-36), -0.004, 0.0082))
    a['tail'] = Vector((0.0, 0.020, 0.0082))
    a['short'] = Vector((jig_x(-36), -0.016, 0.0082))
    a['long'] = Vector((jig_x(54), -0.016, 0.0082))
    shot(R, 'main', cam, W0, 820, a, paths, hi=S.flex)


def f_dots_pod(R, NB):
    from mathutils import Vector
    S = jig(NB)
    pod = S.pods[6]
    paint([S.jig] + S.flex + [S.base] + S.bdots, 'pod', 'hide')
    for k in S.pods:
        if k != 6:
            paint([S.pods[k]] + S.dots[k], 'pod', 'hide')
    W = S.pose_pod(6, h=0.0, phi=math.pi, drop=0.0)
    seated = [ctr([d]) for d in S.dots[6]]
    cam2 = new_cam()
    ortho(cam2, seated[2], 20, 32)
    cam2.data.ortho_scale = 0.011
    shot(R, 'zoom', cam2, 500, 500, {'c': seated[2]})
    S.pose_pod(6, h=0.0, phi=math.pi, drop=0.009)
    cam = new_cam()
    ortho(cam, ctr([pod]), 24, 34)
    fit(cam, pts_of([pod] + S.dots[6]), 1000, 860, margin=1.35)
    a, paths = {}, {}
    for i, d in enumerate(S.dots[6]):
        c = ctr([d])
        a['d%d' % i] = c
        paths['t%d' % i] = [c, seated[i] + Vector((0, 0, 0.0012))]
    a['pod'] = ctr([pod]) + Vector((0.004, 0.0, 0.0))
    a['pocket'] = seated[0]
    a['sleeve'] = ctr([pod]) + Vector((0.0045, 0.006, -0.001))
    shot(R, 'main', cam, 1000, 860, a, paths, hi=S.dots[6])


def f_dots_base(R, NB):
    from mathutils import Vector
    S = jig(NB)
    paint([S.jig] + S.flex + list(S.pods.values()) + sum(S.dots.values(), []), 'pod', 'hide')
    S.pose_base(h=0.0, phi=math.pi, drop=0.0)
    seated = {d.name: ctr([d]) for d in S.bdots}
    S.pose_base(h=0.0, phi=math.pi, drop=0.009)
    cam = new_cam()
    ortho(cam, ctr([S.base]), 18, 40)
    fit(cam, pts_of([S.base] + S.bdots), 1000, 860, margin=1.25)
    a, paths = {}, {}
    for d in S.bdots:
        c = ctr([d])
        paths['t_' + d.name] = [c, seated[d.name] + Vector((0, 0, 0.0012))]
    root = [d for d in S.bdots if d.name.startswith('bdot_root')][0]
    a['root'] = seated[root.name]
    a['rootdot'] = ctr([root])
    a['base'] = ctr([S.base]) + Vector((0.012, 0.010, 0.0))
    a['slot'] = ctr([S.base]) + Vector((0.0, 0.0155, 0.004))
    a['dots'] = ctr([S.bdots[0]])
    shot(R, 'main', cam, 1000, 860, a, paths, hi=S.bdots)


def f_pods_in(R, NB):
    from mathutils import Vector
    S = jig(NB)
    paint([S.base] + S.bdots, 'pod', 'hide')
    for k in (6, 7, 8):
        paint([S.pods[k]] + S.dots[k], 'pod', 'hide')
    S.pose_pod(5, h=0.013)
    cam = new_cam()
    ortho(cam, ctr([S.jig]) + Vector((0.01, 0, 0)), -16, 34)
    fit(cam, pts_of([S.jig, S.pods[5]]), W0, 820, margin=1.08)
    c5 = ctr([S.pods[5]])
    a = dict(pod5=c5 + Vector((0, 0, 0.002)), pod1=ctr([S.pods[1]]) + Vector((0, 0, 0.002)),
             pod2=ctr([S.pods[2]]) + Vector((0, 0, 0.002)), sleeve=c5 + Vector((0.0045, 0.0, 0.0012)),
             nest6=Vector((jig_x(45), -0.004, 0.0012)), nest5=Vector((jig_x(27), 0.006, 0.0012)))
    for k, xd in zip((1, 2, 5, 6, 7, 8), (-45, -27, 27, 45, 63, 81)):
        a['n%d' % k] = Vector((jig_x(xd), -0.023, 0.002))
    paths = dict(t0=[c5 + Vector((-0.0035, -0.012, -0.002)), Vector((c5.x - 0.0035, -0.012, 0.0025))],
                 t1=[c5 + Vector((0.0035, 0.012, -0.002)), Vector((c5.x + 0.0035, 0.012, 0.0025))])
    shot(R, 'main', cam, W0, 820, a, paths, hi=[S.pods[5]])


def f_base_on(R, NB):
    from mathutils import Vector
    S = jig(NB)
    for k in S.pods:
        paint([S.pods[k]] + S.dots[k], 'pod', 'ghost')
    paint([S.jig], 'jig', 'ghost')
    S.pose_base()
    cam2 = new_cam()
    tz = ctr([S.base]) + Vector((0, 0.0152, 0.002))
    ortho(cam2, tz, 200, 48)
    cam2.data.ortho_scale = 0.022
    shot(R, 'zoom', cam2, 500, 500, {'c': tz})
    S.pose_base(h=0.016)
    cam = new_cam()
    ortho(cam, Vector((0, 0.002, 0.008)), -22, 30)
    fit(cam, pts_of([S.base] + S.flex), 1100, 860, margin=1.05)
    cb = ctr([S.base])
    a = dict(base=cb + Vector((0.008, -0.008, 0.004)), tail=Vector((0.0, 0.0160, 0.0075)), saddle=Vector((0.0, -0.004, 0.0019)),
             slot=cb + Vector((0, 0.0152, -0.0025)))
    paths = dict(t0=[cb + Vector((-0.012, -0.012, -0.004)), Vector((cb.x - 0.012, -0.012, 0.004))],
                 t1=[cb + Vector((0.012, -0.012, -0.004)), Vector((cb.x + 0.012, -0.012, 0.004))],
                 tail=[Vector((0, 0.0150, 0.0021)), Vector((0, 0.0160, 0.003)), Vector((0, 0.016, 0.009)), Vector((0, 0.016, 0.020))])
    shot(R, 'main', cam, 1100, 860, a, paths, hi=[S.base])


def f_strip(R, NB):
    from mathutils import Vector, Matrix
    S = jig(NB)
    paint([S.jig], 'jig', 'hide')
    cam = new_cam()
    ortho(cam, Vector((0.018, 0, 0.003)), -14, 38)
    objs = S.flex + list(S.pods.values()) + [S.base]
    fit(cam, pts_of(objs), W0, 760, margin=1.06)
    a = {}
    for k in S.pods:
        a['p%d' % k] = ctr([S.pods[k]]) + Vector((0, -0.012, 0.002))
    a['base'] = ctr([S.base]) + Vector((0.006, -0.006, 0.003))
    a['tail'] = Vector((0.0, 0.016, 0.008))
    a['spine'] = Vector((jig_x(18), 0.003, 0.0003))
    shot(R, 'main', cam, W0, 760, a)


# --- module steps on the ring scene
def module_view(S, modes):
    colour_ring(S, modes)


def f_j1(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    S = ring(NB)
    colour_ring(S, dict(pods='hide', foam='hide', web='hide', slides='hide', lid='hide', cap='hide', cell='hide',
                        base='ghost', flex='on', leads='hide', mag='hide', jwires='hide'))
    paint(S.flex + S.pads, 'flex', 'hide')
    S.tail.hide_render = False
    latch = [o for o in S.j1 if o.name.startswith('ClosedCreamFlipbar')]
    hinge = mod_pt(S, (0, -12.53, 3.85))
    ax = (S.T.to_3x3() @ Vector((1, 0, 0))).normalized()
    Rl = Matrix.Translation(hinge) @ Matrix.Rotation(-math.radians(100), 4, ax) @ Matrix.Translation(-hinge)
    # a: latch open, tail just below the mouth
    Hb = place_board(S, 0.0, 2.5)
    for o in latch:
        o.matrix_world = Hb @ Rl @ S.M0(o)
    j1c = Hb @ ctr(S.j1)
    cam = new_cam()
    ortho(cam, j1c, 70, 12)
    pts = pts_of(S.j1 + [S.tail])
    fit(cam, pts, 680, 700, margin=1.9, off=(0, -0.08))
    mark = Hb @ mod_pt(S, (-6.0, -12.4, 2.75))
    a = dict(latch=Hb @ (Rl @ ctr(latch)), mouth=Hb @ mod_pt(S, (0, -14.8, 3.5)), tail=ctr([S.tail]),
             fingers=Hb @ mod_pt(S, (3.0, -15.3, 3.0)), board=Hb @ mod_pt(S, (8, -8, 2.7)), down=mark)
    paths = dict(t0=[ctr([S.tail]) + S.up * -0.001, ctr([S.tail]) + (Hb.to_3x3() @ S.T.to_3x3() @ Vector((0, 1, 0))).normalized() * -0.004])
    shot(R, 'a', cam, 680, 700, a, paths, hi=[S.tail])
    # b: inserted, latch closed
    Hb = place_board(S, 0.0, 0.0)
    for o in latch:
        o.matrix_world = Hb @ S.M0(o)
    a = dict(latch=Hb @ ctr(latch), tail=ctr([S.tail]))
    shot(R, 'b', cam, 680, 700, a, hi=latch)


def f_fold(R, NB):
    import bpy
    from mathutils import Vector
    S = ring(NB)
    colour_ring(S, dict(pods='hide', foam='hide', web='hide', slides='hide', lid='hide', cap='hide', cell='hide',
                        base='ghost', leads='hide', mag='hide', jwires='hide'))
    paint(S.flex + S.pads, 'flex', 'hide')
    cam = new_cam()
    tgt = mod_pt(S, (0, -4, 8))
    ortho(cam, tgt, 74, 14)
    import numpy as np
    allp = [pts_of(S.base)]
    for s_ in (0.0, 0.55, 1.0):
        place_board(S, s_, 0.0)
        allp.append(pts_of(S.board[:1]))
    fit(cam, np.vstack(allp), 600, 640, margin=1.10)
    P = mod_pt(S, (0.0, 10.0, 2.6))
    for name, s in (('a', 0.0), ('b', 0.55), ('c', 1.0)):
        Hb = place_board(S, s, 0.0)
        a = dict(board=Hb @ mod_pt(S, (0, 0, 2.7)), tail=ctr([S.tail]), j1=Hb @ mod_pt(S, (0, -12.5, 4.0)),
                 base=mod_pt(S, (12, 6, -1)), wall=mod_pt(S, (0, -17.0, 1.5)))
        paths = {}
        if name == 'b':
            arc = [S.board_H(float(t), 0.0) @ P for t in np.linspace(0.05, 0.95, 18)]
            paths['fold'] = arc
        shot(R, name, cam, 600, 640, a, paths, hi=[S.tail] if name != 'b' else S.board[:1])


def f_leads(R, NB):
    import bpy
    from mathutils import Vector
    S = ring(NB)
    colour_ring(S, dict(pods='hide', foam='hide', web='hide', slides='hide', lid='hide', cap='hide', cell='ghost',
                        base='ghost', board='ghost', flex='hide'))
    paint(S.flex + S.pads, 'flex', 'hide')
    cam2 = new_cam()
    gate = mod_pt(S, (13.4, -15.2, 2.6))
    ortho(cam2, gate, 120, 35)
    cam2.data.ortho_scale = 0.009
    shot(R, 'zoom', cam2, 500, 500, {'c': gate})
    cam = new_cam()
    c = mod_pt(S, (2, 0, 3))
    ortho(cam, c, 0, 90, 0.5)
    import mathutils
    cam.matrix_world = S.T @ mathutils.Matrix.Translation((0.002, 0, 0.3)) @ mathutils.Matrix.Identity(4)
    import bpy as _b
    _b.context.view_layer.update()
    import numpy as np
    fit(cam, np.array([list(mod_pt(S, (x, y, 3))) for x in (-4, 17) for y in (-18.5, -4)]), 1000, 860, margin=1.05)
    a = dict(j2=mod_pt(S, (11.3, -12.9, 1.5)), gate=gate, cellend=mod_pt(S, (8.2, -9.6, 6.0)), corner=mod_pt(S, (14.6, -14.8, 2.5)),
             j1=mod_pt(S, (0, -12.2, 3.6)), red=mod_pt(S, (14.5, -12.6, 3.5)), blk=mod_pt(S, (13.0, -15.4, 2.2)))
    shot(R, 'main', cam, 1000, 860, a, hi=S.leads)


def f_cell(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    import guide_figures as GF
    S = ring(NB)
    colour_ring(S, dict(pods='hide', foam='hide', web='hide', slides='hide', lid='hide', cap='hide', base='ghost', flex='hide'))
    paint(S.flex + S.pads, 'flex', 'hide')
    for o in S.cell:
        o.matrix_world = Matrix.Translation(S.up * 0.012) @ S.M0(o)
    cam = new_cam()
    c = mod_pt(S, (2, -1, 5))
    ortho(cam, c, 38, 40)
    fit(cam, pts_of(S.base + S.cell), 1000, 860, margin=1.08)
    cc = ctr(S.cell)
    a = dict(cell=cc + S.up * 0.002, leadend=mod_pt(S, (2.5, -9.5, 18.0)), outline=mod_pt(S, (-3.5, 2.0, 2.75)),
             j1=mod_pt(S, (0, -12.5, 4.2)), leads=mod_pt(S, (12.5, -10.0, 3.8)))
    paths = dict(t0=[mod_pt(S, (-3.5, -6, 16)), mod_pt(S, (-3.5, -6, 8.5))], t1=[mod_pt(S, (8.5, 12, 16)), mod_pt(S, (8.5, 12, 8.5))])
    shot(R, 'main', cam, 1000, 860, a, paths, hi=S.cell)
    # b: the 401120 fallback with the printed spacer
    for o in S.cell:
        o.hide_render = True
    short = GF.box_obj(NB, 'short_cell', (0, 0, 0), (0.011, 0.021, 0.004), NB.mat_lipo(), bevel=0.0005)
    short.matrix_world = S.T @ Matrix.Translation((0.0025, (BAT_Y0 + 10.5) / 1000, 0.0062))
    paint([short], 'cell')
    sp = NB.import_glb(os.path.join(BUILD, 'cell_spacer.glb'), bake=True)
    spo = list(sp.values())
    for o in spo:
        o.matrix_world = S.T @ o.matrix_world
    paint(spo, 'spacer')
    cam2 = new_cam()
    ortho(cam2, mod_pt(S, (2.5, 3, 6)), 30, 55)
    fit(cam2, pts_of([short] + spo + S.base), 560, 480, margin=1.08)
    shot(R, 'b', cam2, 560, 480, dict(spacer=ctr(spo), short=ctr([short])), hi=spo)


def f_lid(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    S = ring(NB)
    colour_ring(S, dict(pods='hide', foam='hide', web='hide', slides='hide', base='on', flex='hide'))
    paint(S.flex + S.pads, 'flex', 'hide')
    for o in S.cap:
        o.matrix_world = Matrix.Translation(S.up * 0.006) @ S.M0(o)
    for o in S.lid:
        o.matrix_world = Matrix.Translation(S.up * 0.020) @ S.M0(o)
    cam = new_cam()
    ortho(cam, mod_pt(S, (0, 0, 10)), 32, 30)
    fit(cam, pts_of(S.base + S.lid), 1000, 860, margin=1.06)
    U = S.up * 0.020
    a = dict(cap=ctr(S.cap) + S.up * 0.001, sw1=mod_pt(S, (SW1[0], SW1[1], 4.7)), led=mod_pt(S, (D1[0], D1[1], 9.6)) + U,
             d1=mod_pt(S, (D1[0], D1[1], 2.9)), lid=ctr(S.lid) + S.up * 0.004)
    for i, (x0, x1, sy) in enumerate(SNAP_SEGS):
        a['snap%d' % i] = mod_pt(S, ((x0 + x1) / 2, sy * (16.4 if sy > 0 else 17.1), 3.4))
    paths = dict(t0=[mod_pt(S, (-14, -15, 3)) + U, mod_pt(S, (-14, -15, 4))], t1=[mod_pt(S, (14, 15, 3)) + U, mod_pt(S, (14, 15, 4))],
                 t2=[ctr(S.cap), ctr(S.cap) - S.up * 0.005])
    shot(R, 'main', cam, 1000, 860, a, paths, hi=S.cap + S.lid)


def f_slides(R, NB):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    S = ring(NB)
    colour_ring(S, dict(pods='hide', foam='hide', web='hide', flex='hide', base='ghost', lid='ghost', cap='hide', cell='hide', board='hide', leads='hide'))
    paint(S.flex + S.pads, 'flex', 'hide')
    sl = S.slides[0]                                       # slide A, +X, by pod 2
    hinge = mod_pt(S, (BAR[0], 0.0, BAR[1]))
    ax = (S.T.to_3x3() @ Vector((0, 1, 0))).normalized()
    # snap-on pose: turned so the clip opening faces out of the slot, then pushed onto the bar
    import bpy as _b
    gh = sl.copy()
    gh.data = sl.data.copy()
    NB.link(gh)
    out = (S.T.to_3x3() @ Vector((1, 0, 0))).normalized()
    gh.matrix_world = Matrix.Translation(-S.up * 0.0050) @ S.M0(sl)
    paint([gh], 'slide', 'ghost')
    paint([S.slides[1]], 'slide', 'hide')
    cam = new_cam()
    ortho(cam, hinge + out * 0.004, 0, 0)
    fit(cam, np.vstack([pts_of([sl, gh]), np.array([list(hinge - out * 0.006), list(hinge + out * 0.010), list(hinge + S.up * 0.006)])]), 760, 700, margin=1.30)
    a = dict(bar=hinge, slide=ctr([sl]), ghost=ctr([gh]), module=mod_pt(S, (8, -17.6, 5)))
    paths = dict(push=[hinge - S.up * 0.0068, hinge - S.up * 0.0026])
    shot(R, 'a', cam, 760, 700, a, paths, hi=[sl])
    paint([gh], 'slide', 'hide')
    paint([S.slides[1]], 'slide')
    cam2 = new_cam()
    ortho(cam2, mod_pt(S, (0, 0, 2)), 90, 20)
    fit(cam2, pts_of(S.base + S.slides), 760, 700, margin=1.10)
    a2 = dict(A=ctr(S.slides[:1]), B=ctr(S.slides[1:]), rib=mod_pt(S, (BAR[0] + 1.5, 0.0, BAR[1])))
    shot(R, 'b', cam2, 760, 700, a2, hi=S.slides)


def f_lock(R, NB):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    S = ring(NB)
    colour_ring(S, dict(pods='ghost', foam='hide', flex='hide', base='ghost', lid='ghost', cap='hide', cell='hide', board='hide',
                        leads='hide', slides='ghost'))
    paint(S.flex + S.pads, 'flex', 'hide')
    lk = [S.straps.get('strap_lock_a'), S.straps.get('strap_tail_a')]
    paint(lk, 'web')
    paint([S.band_s], 'web', 'ghost')
    for o in S.ends:
        if o not in lk:
            o.hide_render = True
    sl = S.slides[0]
    paint([sl], 'slide')
    yc = ctr([sl]).y
    import bpy
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ctr([sl]).x, yc - 0.02, ctr([sl]).z))
    cutter = bpy.context.active_object
    cutter.scale = (0.08, 0.04, 0.08)
    cutter.hide_render = True
    cutter['mode'] = 'hide'
    for o in [sl] + lk:
        m = o.modifiers.new('cut', 'BOOLEAN')
        m.operation = 'DIFFERENCE'
        m.object = cutter
        m.solver = 'EXACT'
    for o in S.pods + S.base + S.lid:
        o.hide_render = True
        o['mode'] = 'hide'
    cam = new_cam()
    t = ctr([sl]) + Vector((0.002, 0, -0.003))
    ortho(cam, t, 18, 14)
    fit(cam, pts_of([sl] + lk), 620, 560, margin=1.25)
    a = dict(slide=ctr([sl]), tail=ctr(lk[1:]), lock=ctr(lk[:1]))
    shot(R, '3d', cam, 620, 560, a, hi=lk)


def f_thread(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    import guide_figures as GF
    S = jig(NB)
    paint([S.jig], 'jig', 'hide')
    mm = 0.001
    # a webbing strip through pod 2's sleeve (for the inset) and slides beside the base ends
    p2 = S.pods[7]                                     # close-up pod: away from the slides
    c2 = ctr([p2])
    zs = 0.00071 + 0.00285
    web = GF.box_obj(NB, 'web2', (c2.x, c2.y, zs), (0.028, 0.020, 0.0015), NB.mat_foam())
    paint([web], 'web')
    sls = []
    for sx in (-1, 1):
        sp = NB.import_glb(os.path.join(BUILD, 'strap_slide.glb'), bake=True)
        o = list(sp.values())[0]
        o.data.transform(Matrix.Rotation(math.pi / 2, 4, 'Z') if False else Matrix.Identity(4))
        a_, b_ = NB.bbox([o])
        cc = (a_ + b_) / 2
        o.data.transform(Matrix.Translation((-cc[0], -cc[1], 0.004 - cc[2])))
        if sx > 0:
            o.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
        o.data.transform(Matrix.Translation((sx * 0.0185, 0, 0)))
        sls.append(o)
    paint(sls, 'slide')
    web.scale = (0.80, 1.0, 1.0)
    others = [S.pods[k] for k in S.pods if k != 7] + [S.base] + sls + sum(S.dots.values(), []) + S.bdots
    for o in others:
        o['mode_keep'] = o.get('mode', 'on')
    paint(others, 'pod', 'hide')
    cam2 = new_cam()
    ortho(cam2, c2 + Vector((-0.002, 0, 0.0015)), -74, 9)
    cam2.data.ortho_scale = 0.021
    shot(R, 'zoom', cam2, 600, 600, {'c': c2})
    for o in others:
        o['mode'] = o['mode_keep']
    paint([web], 'web', 'hide')
    cam = new_cam()
    ortho(cam, Vector((0.018, 0, 0.003)), 0, 90)
    fit(cam, pts_of(S.flex + list(S.pods.values()) + [S.base] + sls), W0, 420, margin=1.04)
    a = {}
    for k in S.pods:
        a['p%d' % k] = ctr([S.pods[k]])
        a['b%d' % k] = ctr([S.pods[k]]) + Vector((0, -0.0165, 0))
    a['A'] = ctr(sls[:1])
    a['B'] = ctr(sls[1:])
    a['base'] = ctr([S.base])
    shot(R, 'main', cam, W0, 420, a)


def f_wear(R, NB):
    import bpy
    from mathutils import Vector
    wb_scene()
    band = NB.load_band()
    arm, info = NB.build_arm(curl=30)
    NB.fit_band_to_arm(band, arm)
    objs = list(band.values()) + [arm]
    rig = NB.rig_objects(objs)
    NB.pose(rig, pitch=8, floor_objs=objs, floor=0.0003)
    bpy.context.view_layer.update()
    paint([arm], 'skin')
    kmap = dict(module_base='base', module_lid='lid', button_cap='cap', pod_shells='pod', strap='web', strap_slide='slide',
                flex='flex', pads='pad', foam='dot', lipo='cell')
    for o in band.values():
        k = o['kind']
        if k in ('main_board', 'board_parts'):
            paint([o], 'board', 'hide')
        else:
            paint([o], kmap.get(k, 'pod'))
    c, mn, mx = NB.module_centre(band)
    cam = new_cam()
    tgt = c + rig.matrix_world.to_3x3() @ Vector((0, -0.04, -0.02))
    ortho(cam, tgt, 62, 34)
    fit(cam, pts_of([o for o in band.values() if o['kind'] == 'module_lid']) .tolist() + [list(tgt + Vector((-0.09, -0.06, -0.03))), list(tgt + Vector((0.06, 0.08, 0.03)))], W0, 820, margin=1.0)
    lid = [o for o in band.values() if o['kind'] == 'module_lid']
    capo = [o for o in band.values() if o['kind'] == 'button_cap']
    sl = [o for o in band.values() if o['kind'] == 'strap_slide']
    ax = rig.matrix_world.to_3x3() @ Vector((0, 1, 0))
    st = [o for o in band.values() if o['kind'] == 'strap']
    import numpy as np
    V = NB.verts_np(st[0])
    a = dict(module=ctr(lid) + Vector((0, 0, 0.004)), cap=ctr(capo), slide=ctr(sl[:1]), crease=c + ax * -0.026 + Vector((0, 0, -0.012)),
             web=Vector(V[np.argmax(V[:, 0])].tolist()))
    paths = dict(slip=[c + ax * -0.080 + Vector((0, 0, 0.026)), c + ax * -0.030 + Vector((0, 0, 0.026))])
    shot(R, 'main', cam, W0, 820, a, paths)


def f_clip_build(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    import assembly_anim as AA
    wb_scene()
    cc = NB.import_glb(os.path.join(BUILD, 'charge_clip_fit.glb'), bake=True)
    clip, pins = [], []
    for o in list(cc.values()):
        k = NB.kind(o.name)
        if k == 'charge_clip':
            clip.append(o)
        elif k == 'pogo_pins':
            pins.append(o)
        else:
            bpy.data.objects.remove(o)
    paint(clip, 'clip', 'ghost')
    clip[0].color = (*lin(COL['clip']), 0.45)
    clip[0]['rgba'] = list(clip[0].color)
    paint(pins, 'pin')
    pins.sort(key=lambda o: -ctr([o]).y)                   # VCHG (y 6.2) first, nearer the back plate
    for o in pins:
        o.matrix_world = Matrix.Translation((0, 0, -0.010)) @ o.matrix_world
    mm = 0.001
    rw = AA.curve_obj(NB, 'red', [tuple(x * mm for x in p) for p in ((0, 6.2, -24.5), (0.0, 9, -26.5), (0, 16, -27), (0, 24, -26))], 0.0004, NB.mat_foam())
    bw = AA.curve_obj(NB, 'blk', [tuple(x * mm for x in p) for p in ((0, 3.2, -24.5), (1.0, 7, -27.5), (1.0, 16, -28), (1, 24, -27))], 0.0004, NB.mat_foam())
    paint([rw], 'red')
    paint([bw], 'black')
    cam = new_cam()
    tgt = ctr(clip) + Vector((0, 0, -0.006))
    ortho(cam, tgt, 90, -12)
    import numpy as np
    fit(cam, np.vstack([pts_of(clip + pins), np.array([[0, 0.024, -0.029], [0, 0.0, -0.029]])]), 1000, 860, margin=1.12)
    a = dict(vchg=ctr(pins[:1]), gnd=ctr(pins[1:]), back=ctr(clip) + Vector((0, 0.009, 0.004)), key=Vector((0, 0.0166, 0.0028)),
             hook=Vector((0.004, 0.0170, 0.0105)), exit=Vector((0, 0.021, -0.012)), red=Vector((0, 0.016, -0.027)))
    paths = {('t%d' % i): [ctr([o]) + Vector((0, 0, -0.004)), ctr([o]) + Vector((0, 0, 0.008))] for i, o in enumerate(pins)}
    shot(R, 'main', cam, 1000, 860, a, paths, hi=pins + [rw, bw])


def f_clip_on(R, NB):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    S = ring(NB, clip=True)
    colour_ring(S, dict(pods='hide', foam='hide', web='hide', slides='hide', flex='hide'))
    paint(S.flex + S.pads, 'flex', 'hide')
    clipm = [o for o in S.clip if o.type == 'MESH']
    body = [o for o in clipm if o.get('kind') == 'charge_clip']
    pins = [o for o in clipm if o.get('kind') == 'pogo_pins']
    # side view (small): the clip a little proximal of home, sliding on
    off = S.prox * 0.008
    for o in S.clip:
        o.matrix_world = Matrix.Translation(off) @ S.M0(o)
    cam = new_cam()
    ortho(cam, mod_pt(S, (0, 14, 0)), 118, 6)
    fit(cam, pts_of(clipm + S.lid + S.base), 760, 620, margin=1.18)
    key = mod_pt(S, (0, 17.0, 2.6))
    a = dict(key=key + off, hook=mod_pt(S, (4, 15.8, 10.4)) + off, clip=ctr(body))
    paths = dict(slide=[mod_pt(S, (0, 31, -9)), mod_pt(S, (0, 23, -9))], drop=[key + off + S.up * 0.004, key + off])
    shot(R, 'main', cam, 760, 620, a, paths, hi=body)
    # cutaway through the pins (module x = 0), clip home: the lower arm under the module between the pads
    # of pods 3 and 4, both pins up through the charge window onto the pads
    import nb_blender as _NB
    for o in S.clip:
        o.matrix_world = S.M0(o)
    paint([o for o in S.clip if o.type == 'CURVE'], 'usb', 'hide')
    bodyb = [o for o in S.board if o.type == 'MESH' and o.data.materials and o.data.materials[0].name.lower().startswith('fr4')]
    paint([o for o in S.board if o not in bodyb], 'comp', 'hide')
    paint(bodyb, 'board')
    paint(S.cell + S.cap, 'cell', 'hide')

    def in_module(o):
        c = S.Ti @ ctr([o])
        return abs(c.x) < 0.0145 and abs(c.y) < 0.018 and c.z < 0.002
    modflex = [o for o in S.flex + S.pads + S.foam if in_module(o)]
    paint([o for o in modflex if o in S.flex], 'flex')
    paint([o for o in modflex if o in S.pads], 'pad')
    paint([o for o in modflex if o in S.foam], 'dot')
    bpy.ops.mesh.primitive_cube_add(size=1)
    cutter = bpy.context.active_object
    cutter.matrix_world = S.T @ Matrix.Translation((0.050, 0, 0)) @ Matrix.Scale(0.1, 4)
    cutter['mode'] = 'hide'
    cutter.hide_render = True
    for o in S.base + S.lid + body + pins + bodyb:
        m = o.modifiers.new('cut', 'BOOLEAN')
        m.operation = 'DIFFERENCE'
        m.object = cutter
        m.solver = 'EXACT'
    cam2 = new_cam()
    tgt = mod_pt(S, (0, 8, -2))
    _NB.look_at(cam2, tgt, mod_pt(S, (600, 8, -2)))
    cam2.data.clip_start = 0.001
    cam2.data.clip_end = 10.0
    cam2.data.type = 'ORTHO'
    cam2.data.sensor_fit = 'HORIZONTAL'
    bpy.context.view_layer.update()
    fit(cam2, np.array([list(mod_pt(S, (0, y, z))) for y in (-18, 25) for z in (-16, 12)]), 860, 800, margin=1.04)
    pins.sort(key=lambda o: -(S.Ti @ ctr([o])).y)
    a2 = dict(arm=mod_pt(S, (0, 13, -9)), vchg=mod_pt(S, (0, 6.2, -1.2)), gnd=mod_pt(S, (0, 3.2, -1.2)),
              window=mod_pt(S, (0, 1.4, 0.4)), pads=mod_pt(S, (0, 4.7, 1.75)), pod4=mod_pt(S, (-9, -6, -2.6)),
              back=mod_pt(S, (0, 21.5, -6)), key=mod_pt(S, (0, 16.9, 2.5)))
    shot(R, 'below', cam2, 860, 800, a2, {}, hi=pins)


def f_open(R, NB):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    S = ring(NB)
    colour_ring(S, dict(pods='ghost', foam='hide', web='ghost', slides='ghost', flex='ghost'))
    cam = new_cam()
    tgt = mod_pt(S, (0, 14, 5))
    ortho(cam, tgt, 160, 22)
    fit(cam, pts_of(S.lid + S.base), 700, 640, margin=1.30)
    a = dict(notch=mod_pt(S, (0, 16.9, 2.6)), lid=ctr(S.lid) + S.up * 0.004, base=mod_pt(S, (8, 16, 0.5)))
    lev = [mod_pt(S, (0, 22 - 4 * math.cos(t), 2.6 + 6 * math.sin(t))) for t in np.linspace(0.2, 1.6, 12)]
    shot(R, 'a', cam, 700, 640, a, dict(lever=lev), hi=S.lid)
    # b: board out, in the SWD jig (cell resting on it)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    jig_, pins, board, body, wires, M = swd_scene(NB)
    import guide_figures as GF
    bmn, bmx = NB.bbox([body])
    cell = GF.box_obj(NB, 'cellb', ((bmn[0] + bmx[0]) / 2 + 0.002, (bmn[1] + bmx[1]) / 2 - 0.001, bmx[2] + 0.0035), (0.012, 0.025, 0.004), NB.mat_lipo(), bevel=0.0005)
    paint([cell], 'cell')
    paint([wires[0]], 'red', 'hide')
    cam2 = new_cam()
    ortho(cam2, Vector((0.014, -0.014, 0.017)), 28, 34)
    fit(cam2, pts_of([jig_, body, cell]), 700, 640, margin=1.12)
    a2 = dict(board=Vector(((bmn[0] + bmx[0]) / 2, bmn[1] + 0.004, bmx[2])), cell=ctr([cell]), wires=Vector((0.017, -0.045, 0.0009)),
              notch=Vector((0.026, bmn[1] - 0.001, 0.0172)))
    shot(R, 'b', cam2, 700, 640, a2, hi=[cell])


# ================================================================== r2 figures (Nov 2026)
def _board_bottom(NB):
    """the bare board, bottom side up (turned over about its long axis). Returns (objs, body, kp, c):
    kp(x, y) maps a KiCad point (mm) of the bottom face to the world."""
    from mathutils import Vector, Matrix
    wb_scene()
    bobj, body = NB.load_board()
    objs = list(bobj.values())
    bmn, bmx = NB.bbox([body])
    mm = 0.001
    c = Vector(((bmn + bmx) / 2).tolist())
    Mf = Matrix.Translation(c) @ Matrix.Rotation(math.pi, 4, 'Y') @ Matrix.Translation(-c)
    for o in objs:
        o.matrix_world = Mf @ o.matrix_world
    paint_board(objs)
    kp = lambda xk, yk, dz=0.0: Mf @ Vector((bmn[0] + xk * mm, bmx[1] - yk * mm, bmn[2] - dz * mm))
    return objs, body, kp, c


def _wire(NB, name, pts, key, r=0.00028):
    import assembly_anim as AA
    o = AA.curve_obj(NB, name, [tuple(p) for p in pts], r, NB.mat_foam())
    paint([o], key)
    return o


def f_swd_wires(R, NB):
    objs, body, kp, c = _board_bottom(NB)
    keys = ['red', 'wire_y', 'wire_g', None, 'black']
    wires = []
    for i, (x, y) in enumerate(TP_K):
        if keys[i] is None:
            continue
        pts = [kp(x, y, 0.3), kp(x - 0.4, y - 2.0, 0.6), kp(x - 1.5 - 0.6 * i, -4.0 - 1.2 * i, 0.6), kp(-6.0 - 1.4 * i, -9.0 - 1.4 * i, 0.4)]
        wires.append(_wire(NB, 'w%d' % i, pts, keys[i]))
    cam = new_cam()
    ortho(cam, c, 0, 90)
    import numpy as np
    pts = np.vstack([pts_of([body]), np.array([list(kp(-14, -16)), list(kp(30, 29))])])
    fit(cam, pts, 980, 860, margin=1.05)
    a = {('tp%d' % i): kp(*TP_K[i]) for i in range(5)}
    a['board'] = kp(18, 12)
    a['j1'] = kp(14, 27)
    a['wires'] = kp(-8.5, -11.5, 0.4)
    shot(R, 'main', cam, 980, 860, a, hi=wires)


def f_cell_leads(R, NB):
    import guide_figures as GF
    objs, body, kp, c = _board_bottom(NB)
    pv, pg = kp(*J2_K[0]), kp(*J2_K[1])
    ce = kp(28.7 + 4.0 + 12.5, 18.8, -1.4)            # cell beyond the button-side edge, lead end toward the board
    cell = GF.box_obj(NB, 'cell', (ce.x, ce.y, ce.z), (0.025, 0.012, 0.004), NB.mat_lipo(), bevel=0.0006)
    paint([cell], 'cell')
    red = _wire(NB, 'lr', [kp(32.8, 19.6, -1.0), kp(31.0, 19.8, 0.2), kp(28.0, 19.3, 0.2), kp(26.8, 18.9, 0.15)], 'red')
    blk = _wire(NB, 'lb', [kp(32.8, 18.0, -1.0), kp(31.0, 17.2, 0.2), kp(26.0, 17.4, 0.2), kp(23.8, 18.6, 0.15)], 'black')
    k0 = kp(25.3, 18.8, 0.45)
    kap = GF.box_obj(NB, 'kap', (k0.x, k0.y, k0.z), (0.0062, 0.0042, 0.00006), NB.mat_foam())
    paint([kap], 'kapton')
    kap.color = (*lin(COL['kapton']), 0.55)
    kap['rgba'] = list(kap.color)
    cam = new_cam()
    ortho(cam, c, 0, 90)
    fit(cam, pts_of([body, cell]), 980, 860, margin=1.08)
    a = dict(j2p=pv, j2m=pg, cell=ce, kap=kp(25.3, 18.0, 0.5), tp=kp(*TP_K[2]), j3v=kp(*J3_K[0]), edge=kp(28.7, 9.0),
             red=kp(30.0, 19.7, 0.2), blk=kp(30.0, 17.3, 0.2))
    shot(R, 'main', cam, 980, 860, a, hi=[red, blk, kap])


def f_j3_wires(R, NB):
    import guide_figures as GF
    objs, body, kp, c = _board_bottom(NB)
    cc = kp(14.5, -6.0, -1.5)                          # connector where it will sit: beyond the proximal edge, centred
    conn = GF.box_obj(NB, 'conn', (cc.x, cc.y, cc.z), (0.0145, 0.004, 0.004), NB.mat_foam(), bevel=0.0004)
    paint([conn], 'mag')
    red = _wire(NB, 'jr', [kp(23.9, 25.4, 0.2), kp(25.6, 24.0, 0.4), kp(27.2, 20.0, 0.4), kp(27.2, 3.0, 0.4), kp(24.0, -1.0, 0.4),
                           kp(15.75, -3.5, -0.6), kp(15.75, -4.0, -1.5)], 'red')
    blk = _wire(NB, 'jb', [kp(26.9, 25.4, 0.2), kp(27.8, 23.5, 0.4), kp(27.8, 20.0, 0.4), kp(27.8, 3.0, 0.4), kp(25.0, -1.5, 0.4),
                           kp(13.25, -3.5, -0.6), kp(13.25, -4.0, -1.5)], 'black')
    cam = new_cam()
    ortho(cam, c, 0, 90)
    import numpy as np
    fit(cam, np.vstack([pts_of([body, conn])]), 980, 860, margin=1.08)
    a = dict(j3v=kp(*J3_K[0]), j3g=kp(*J3_K[1]), conn=cc, wires=kp(27.5, 10.0, 0.4), j1=kp(14, 27), j2=kp(*J2_K[0]))
    shot(R, 'main', cam, 980, 860, a, hi=[red, blk, conn])


def f_strip(R, NB):
    from mathutils import Vector
    S = jig(NB)
    paint([S.jig, S.base] + S.bdots, 'jig', 'hide')
    cam = new_cam()
    ortho(cam, Vector((0.018, 0, 0.003)), -14, 38)
    objs = S.flex + list(S.pods.values())
    fit(cam, pts_of(objs), W0, 760, margin=1.06)
    a = {}
    for k in S.pods:
        a['p%d' % k] = ctr([S.pods[k]]) + Vector((0, -0.012, 0.002))
    a['mid'] = Vector((0.0, -0.004, 0.0005))
    a['tail'] = Vector((0.0, 0.016, 0.0010))
    a['spine'] = Vector((jig_x(18), 0.003, 0.0003))
    shot(R, 'main', cam, W0, 760, a)


def f_base_jig(R, NB):
    """stage 2: the pedestal; the pod 3/4 part of the flex on the saddle, the base lowered onto it."""
    import bpy
    from mathutils import Vector, Matrix
    wb_scene()
    jg = NB.import_glb(os.path.join(BUILD, 'base_jig_fit.glb'), bake=True)
    jig_o, base = [], []
    for o in jg.values():
        (base if NB.kind(o.name) == 'module_base' else jig_o).append(o)
    paint(jig_o, 'jig')
    paint(base, 'base')
    ma = NB.import_glb(os.path.join(BUILD, 'module_assy.glb'), bake=True)
    fl = []
    Mj = Matrix.Translation((0, 0, 0.02711)) @ Matrix.Rotation(math.pi, 4, 'Z')    # module frame -> jig (base_jig.py)
    for o in list(ma.values()):
        k = NB.kind(o.name)
        if k in ('flex_pods_3_4', 'pads', 'foam', 'tail'):
            o.matrix_world = Mj @ o.matrix_world
            paint([o], {'flex_pods_3_4': 'flex', 'pads': 'pad', 'foam': 'dot', 'tail': 'flex'}[k])
            fl.append(o)
        else:
            bpy.data.objects.remove(o)
    lift = Vector((0, 0, 0.014))
    dots = [o for o in fl if NB.kind(o.name) == 'foam']
    for o in base + dots:
        o.matrix_world = Matrix.Translation(lift) @ o.matrix_world
    cam = new_cam()
    c = ctr(jig_o)
    ortho(cam, c + Vector((0, 0, 0.012)), -28, 22)
    fit(cam, pts_of(jig_o + base + fl), 1100, 860, margin=1.08)
    cb = ctr(base)
    a = dict(base=cb + Vector((0.006, 0.0, 0.004)), saddle=Vector((0.0, -0.004, 0.0262)), pins=Vector((0.0089, 0.005, 0.0266)),
             fence=Vector((0.0, -0.0205, 0.0262)), pedestal=c + Vector((0.0, -0.016, -0.004)), flex=Vector((-0.009, 0.004, 0.0265)),
             bar=cb + Vector((0.021, 0.0, -0.003)))
    paths = dict(t0=[cb + Vector((-0.010, -0.012, 0.0)), cb + Vector((-0.010, -0.012, 0.0)) - lift * 0.8],
                 t1=[cb + Vector((0.010, -0.012, 0.0)), cb + Vector((0.010, -0.012, 0.0)) - lift * 0.8])
    shot(R, 'main', cam, 1100, 860, a, paths, hi=base)


def f_bay(R, NB):
    """lid off, top view: the connector in its bay, the J3 wires along the button-side edge, the cell leads."""
    import bpy
    import mathutils
    from mathutils import Vector
    S = ring(NB)
    colour_ring(S, dict(pods='hide', foam='hide', web='hide', slides='hide', lid='hide', cap='hide', cell='ghost',
                        base='on', board='ghost', flex='hide'))
    paint(S.flex + S.pads, 'flex', 'hide')
    paint(S.mag, 'mag')
    paint([S.jwires[0]], 'red')
    paint([S.jwires[1]], 'black')
    cam = new_cam()
    cam.matrix_world = S.T @ mathutils.Matrix.Translation((0.0, 0.001, 0.3))
    cam.data.type = 'ORTHO'
    cam.data.clip_start, cam.data.clip_end = 0.001, 10.0
    bpy.context.view_layer.update()
    import numpy as np
    fit(cam, np.array([list(mod_pt(S, (x, y, 3))) for x in (-24, 24) for y in (-18.5, 20.5)]), W0, 860, margin=1.02)
    a = dict(conn=mod_pt(S, (MAG_C[0], MAG_C[1] - 1.5, 5.4)), j3=mod_pt(S, (11.4, -13.2, 1.7)), wires=mod_pt(S, (13.1, 2.0, 1.2)),
             leads=mod_pt(S, (15.0, -6.4, 2.0)), j2=mod_pt(S, (11.3, -6.6, 1.5)), cellend=mod_pt(S, (5.0, -10.0, 5.0)),
             barA=mod_pt(S, (BAR_A[0], 0, 3.0)), barB=mod_pt(S, (BAR_B[0], 0, 3.0)))
    shot(R, 'main', cam, W0, 860, a, hi=S.mag + S.jwires + S.leads)


def f_lock_a(R, NB):
    import bpy
    from mathutils import Vector
    S = ring(NB)
    colour_ring(S, dict(pods='on', foam='hide', web='on', slides='hide', lid='on', cap='on', base='on', flex='on', board='hide', cell='hide', leads='hide'))
    lk = S.straps.get('strap_lock_a')
    cam = new_cam()
    tgt = mod_pt(S, (BAR_A[0], 0.0, BAR_A[1]))
    ortho(cam, tgt, 0, 6)
    fit(cam, pts_of([lk]) if lk else [list(tgt)], 450, 430, margin=2.2, off=(0.05, 0.0))
    a = dict(bar=tgt, lock=ctr([lk]) if lk else tgt, wall=mod_pt(S, (-15.6, -10.0, 1.0)))
    shot(R, '3d', cam, 450, 430, a, hi=[lk] if lk else None)


def f_fold_b(R, NB):
    import bpy
    from mathutils import Vector
    S = ring(NB)
    colour_ring(S, dict(pods='on', foam='hide', web='on', slides='hide', lid='on', cap='on', base='on', flex='on', board='hide', cell='hide', leads='hide'))
    pieces = [S.straps[k] for k in ('strap_lock_b', 'strap_tail_b') if k in S.straps]
    if 'strap_tail_b' in S.straps:
        paint([S.straps['strap_tail_b']], 'hook')
    lk = S.straps.get('strap_lock_b')
    cam = new_cam()
    tgt = mod_pt(S, (BAR_B[0], 0.0, BAR_B[1]))
    ortho(cam, tgt, 0, 6)
    fit(cam, pts_of([lk]) if lk else [list(tgt)], 450, 430, margin=2.4, off=(-0.05, 0.08))
    import numpy as np
    tb = S.straps.get('strap_tail_b')
    tpt = tgt
    if tb is not None:
        V = NB.verts_np(tb)
        d = np.linalg.norm(V - np.array(list(tgt)), axis=1)
        tpt = Vector(V[np.argmin(np.abs(d - 0.010))].tolist())
    a = dict(bar=mod_pt(S, (BAR_B[0], 0.0, BAR_B[1])), tail=tpt)
    shot(R, '3d', cam, 450, 430, a, hi=pieces)


def f_press(R, NB):
    from mathutils import Vector, Matrix
    import guide_figures as GF
    wb_scene()
    pp = NB.import_glb(os.path.join(BUILD, 'pod.glb'), bake=True)
    pod = list(pp.values())
    paint(pod, 'pod')
    pmn, pmx = NB.bbox(pod)
    pc = Vector(((pmn + pmx) / 2).tolist())
    mm = 0.001
    zf = pmn[2] + mm * (BT_POD + 1.0)                      # strap mid-plane when seated
    c0 = Vector((pc.x, pc.y, zf))
    hinge = Vector((pc.x, pc.y - 0.0095, zf - 0.0004))     # -y edge already under its lip
    web = GF.box_obj(NB, 'web', tuple(c0), (0.012, 0.020, 0.002), NB.mat_foam())
    tilt = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(13), 4, 'X') @ Matrix.Translation(-hinge)
    web.matrix_world = tilt @ web.matrix_world
    paint([web], 'web')
    cam = new_cam()
    ortho(cam, pc, 90, 12)
    fit(cam, pts_of(pod + [web]), 1100, 860, margin=1.10)
    ey = tilt @ Vector((pc.x, pc.y + 0.0100, zf + 0.001))
    a = dict(pod=Vector((pc.x, pc.y + 0.006, pmn[2] + 0.0012)), lip=Vector((pc.x, pc.y - 0.0115, pmx[2])),
             lip2=Vector((pc.x, pc.y + 0.0115, pmx[2])), web=tilt @ Vector((pc.x, pc.y + 0.005, zf + 0.001)),
             floor=Vector((pc.x, pc.y + 0.004, pmn[2] + mm * BT_POD)))
    paths = dict(t0=[ey + Vector((0, 0, 0.003)), Vector((pc.x, pc.y + 0.0100, zf + 0.0012))])
    shot(R, 'main', cam, 1100, 860, a, paths, hi=[web])


def f_charge(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    import guide_figures as GF
    S = ring(NB)
    colour_ring(S, dict(pods='ghost', foam='hide', web='ghost', slides='hide', flex='ghost', board='hide', cell='hide', leads='hide'))
    paint(S.mag, 'mag')
    head = GF.box_obj(NB, 'head', (0, 0, 0), (0.0145, 0.006, 0.0045), NB.mat_foam(), bevel=0.0008)
    head.matrix_world = S.T @ Matrix.Translation(((MAG_C[0]) / 1000, (MAG_C[1] + 9.0) / 1000, MAG_C[2] / 1000)) @ Matrix.Identity(4)
    paint([head], 'usb')
    import assembly_anim as AA
    cab = AA.curve_obj(NB, 'cab', [tuple(S.T @ Vector((MAG_C[0] / 1000, (MAG_C[1] + 12 + 6 * k) / 1000, (MAG_C[2] - 2 * k * k) / 1000))) for k in range(6)],
                       0.0016, NB.mat_foam())
    paint([cab], 'usb')
    cam = new_cam()
    tgt = mod_pt(S, (0, 16, 2))
    ortho(cam, tgt, 150, 24)
    fit(cam, pts_of(S.lid + S.base + [head]), 1000, 860, margin=1.25)
    a = dict(bay=mod_pt(S, MAG_C), head=ctr([head]), lid=ctr(S.lid) + S.up * 0.004, j1=mod_pt(S, (0, Y_MIN, 4)))
    paths = dict(t0=[ctr([head]) + (S.T.to_3x3() @ Vector((0, 0.004, 0))), mod_pt(S, (MAG_C[0], MAG_C[1] + 1.5, MAG_C[2]))])
    shot(R, 'main', cam, 1000, 860, a, paths, hi=[head])


def f_open(R, NB):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    S = ring(NB)
    colour_ring(S, dict(pods='ghost', foam='hide', web='ghost', slides='hide', flex='ghost'))
    paint(S.mag, 'mag')
    cam = new_cam()
    tgt = mod_pt(S, (0, 16, 5))
    ortho(cam, tgt, 160, 22)
    fit(cam, pts_of(S.lid + S.base), 690, 640, margin=1.30)
    a = dict(notch=mod_pt(S, NOTCH), lid=ctr(S.lid) + S.up * 0.004, conn=mod_pt(S, MAG_C))
    lev = [mod_pt(S, (0.5, 24 - 4 * math.cos(t), NOTCH[2] + 6 * math.sin(t))) for t in np.linspace(0.2, 1.6, 12)]
    shot(R, 'a', cam, 690, 640, a, dict(lever=lev), hi=S.lid)
    # b: lid and cell off, board folded out (upright) for the SWD wires
    colour_ring(S, dict(pods='ghost', foam='hide', web='ghost', slides='hide', flex='ghost', lid='hide', cap='hide', cell='hide'))
    paint(S.jwires, 'red', 'hide')
    Hb = place_board(S, 0.0, 6.0)
    import assembly_anim as AA
    wires, allq = [], []
    for i, key in ((1, 'wire_y'), (2, 'wire_g'), (4, 'black')):
        tx, ty = TP_K[i][0] - 14.0, 12.2 - TP_K[i][1]
        q = [Hb @ mod_pt(S, (tx, ty, 1.6)), Hb @ mod_pt(S, (tx - 0.5, ty + 0.5, -0.5)), Hb @ mod_pt(S, (tx - 2.0 - i, ty - 2.0, -6.0)),
             Hb @ mod_pt(S, (tx - 3.0 - 2 * i, ty - 9.0, -9.0))]
        w = AA.curve_obj(NB, 'rw%d' % i, [tuple(v) for v in q], 0.00028, NB.mat_foam())
        paint([w], key)
        wires.append(w)
        allq += [list(v) for v in q]
    cam2 = new_cam()
    ortho(cam2, mod_pt(S, (0, -6, 14)), 125, 18)
    fit(cam2, np.vstack([pts_of(S.base + S.board), np.array(allq)]), 690, 640, margin=1.10)
    a2 = dict(board=Hb @ mod_pt(S, (0, 0, 1.6)), tp=Hb @ mod_pt(S, (TP_K[2][0] - 14.0, 12.2 - TP_K[2][1], 1.6)),
              base=mod_pt(S, (10, 8, 0)))
    shot(R, 'b', cam2, 690, 640, a2, hi=wires)


# ---------------------------------------------------------------- r2 versions of the figures shared with r1
def f_kit(R, NB):
    import bpy
    from mathutils import Vector, Matrix
    import guide_figures as GF
    import assembly_anim as AA
    wb_scene()
    mm = 0.001
    items = {}

    def imp(fn, kinds=None):
        objs = NB.import_glb(os.path.join(BUILD, fn), bake=True)
        out = {}
        for o in list(objs.values()):
            k = NB.kind(o.name)
            if kinds and k not in kinds:
                bpy.data.objects.remove(o)
                continue
            out.setdefault(k, []).append(o)
        return out

    def put(objs, x, y, rot_z=0.0, flip=False):
        bpy.context.view_layer.update()
        for o in objs:
            if o.data.users > 1:
                o.data = o.data.copy()
            o.data.transform(o.matrix_world)
            o.matrix_world = Matrix.Identity(4)
        for o in objs:
            if flip:
                o.data.transform(Matrix.Rotation(math.pi, 4, 'Y'))
            if rot_z:
                o.data.transform(Matrix.Rotation(rot_z, 4, 'Z'))
        a, b = NB.bbox(objs)
        c = (a + b) / 2
        for o in objs:
            o.data.transform(Matrix.Translation((x * mm - c[0], y * mm - c[1], -a[2])))
            o.data.update()
        return objs
    ma = imp('module_assy.glb', ('module_base', 'module_lid', 'button_cap', 'lipo', 'mag_connector', 'mag_contacts'))
    items['base'] = put(ma['module_base'], 226, 84)
    items['lid'] = put(ma['module_lid'], 270, 84)
    items['cap'] = put(ma['button_cap'], 150, 30)
    items['cell'] = put(ma['lipo'], 306, 84)
    for k in ('base', 'lid', 'cap', 'cell'):
        paint(items[k], k)
    fem = put(ma.get('mag_connector', []) + ma.get('mag_contacts', []), 228, 30, rot_z=0.0)
    male = []
    for o in fem:
        c = o.copy()
        c.data = o.data.copy()
        NB.link(c)
        male.append(c)
    male = put(male, 252, 30)
    paint(fem + male, 'mag')
    items['conn'] = fem + male
    jg = imp('bond_jig.glb')
    items['bond_jig'] = put(sum(jg.values(), []), 75, 148)
    bj = imp('base_jig.glb')
    items['base_jig'] = put(sum(bj.values(), []), 180, 148, rot_z=math.pi / 2)
    cs = imp('cell_spacer.glb')
    items['spacer'] = put(sum(cs.values(), []), 236, 148)
    paint(items['bond_jig'] + items['base_jig'], 'jig')
    paint(items['spacer'], 'spacer')
    pods = []
    for i in range(6):
        pp = imp('pod.glb')
        pods.append(put(sum(pp.values(), []), 8 + 17 * i, 30))
        paint(pods[-1], 'pod')
    items['pods'] = sum(pods, [])
    bobj, body = NB.load_board()
    items['board'] = put(list(bobj.values()), 182, 84)
    paint_board(items['board'])
    fl, _ = NB.load_board(os.path.join(BUILD, 'flex_board.glb'), flex=True)
    items['flex'] = put(list(fl.values()), 75, 84)
    paint_board(items['flex'], flex=True)
    dots = []
    for i in range(25):
        d = GF.dot_obj(NB, 'kdot%d' % i, NB.mat_foam())
        d.data.transform(d.matrix_world)
        d.matrix_world = Matrix.Identity(4)
        d.data.transform(Matrix.Translation((mm * (172 + 8 * (i % 5)), mm * (46 - 8 * (i // 5)), 0.001)))
        dots.append(d)
    paint(dots, 'dot')
    items['dots'] = dots
    # the strap, laid flat: ring end left, loop panel, hook tab at the right
    x0s, ys = 6.0, -16.0
    st = GF.box_obj(NB, 'strap', (mm * (x0s + 151), mm * ys, mm * 1.0), (0.302, 0.020, 0.002), NB.mat_foam())
    lp = GF.box_obj(NB, 'panel', (mm * (x0s + 164.5), mm * ys, mm * 2.05), (0.075, 0.0196, 0.0001), NB.mat_foam())
    hk = GF.box_obj(NB, 'hooktab', (mm * (x0s + 280), mm * ys, mm * 2.1), (0.044, 0.0196, 0.0002), NB.mat_foam())
    paint([st], 'web')
    paint([lp], tuple(0.78 * c + 0.22 for c in COL['web']))
    paint([hk], 'hook')
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0115, minor_radius=0.0011, location=(mm * (x0s - 4), mm * ys, 0.0011))
    ring_o = bpy.context.active_object
    ring_o.scale = (0.45, 1.0, 1.0)
    paint([ring_o], 'ring')
    items['strap'] = [st]
    # USB-A lead to the male half
    usb = AA.curve_obj(NB, 'usb', [(mm * 262, mm * 30, 0.0016), (mm * 276, mm * 36, 0.0016), (mm * 290, mm * 28, 0.0016),
                                   (mm * 304, mm * 34, 0.0016)], 0.0018, NB.mat_foam())
    paint([usb], 'usb')
    cam = new_cam()
    ortho(cam, (0.155, 0.06, 0), 0, 90)
    allp = pts_of([o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render])
    fit(cam, allp, W0, 860, margin=1.03, off=(0, 0.0))

    def bot(objs):
        a, b = NB.bbox(objs)
        return Vector(((a[0] + b[0]) / 2, a[1], b[2]))
    anchors = {k: bot(v) for k, v in items.items()}
    anchors['conn'] = bot(fem)
    anchors['strap'] = Vector((mm * (x0s + 60), mm * (ys - 10), 0.002))
    anchors['hook'] = Vector((mm * (x0s + 280), mm * (ys - 10), 0.002))
    anchors['ringe'] = Vector((mm * (x0s - 4), mm * (ys - 11), 0.002))
    anchors['usb'] = Vector((mm * 290, mm * 25, 0.002))
    shot(R, 'main', cam, W0, 860, anchors)


def _bar_pt(S, bar, dz=0.0):
    return mod_pt(S, (bar[0], 0.0, bar[1] + dz))


def f_names(R, NB):
    from mathutils import Vector
    S = ring(NB)
    cam = new_cam()
    ortho(cam, S.ring_c, 12, 18)
    fit(cam, pts_of(S.pods + S.lid + [S.band_s] + S.ends), 980, 860, margin=1.25)
    a = {}
    for o in S.pods:
        a['pod%d' % S.pod_num[o.name]] = ctr([o]) + Vector((0, -0.017, 0))
    a['pod3'] = mod_pt(S, (9, -16, -1))
    a['pod4'] = mod_pt(S, (-9, -16, -1))
    a['lid'] = ctr(S.lid) + S.up * 0.004
    a['j1end'] = mod_pt(S, (0, Y_MIN - 0.5, 4))
    a['button'] = ctr(S.cap) + S.up * 0.001
    a['antenna'] = mod_pt(S, (-12.5, -8, 6))
    a['barA'] = mod_pt(S, (BAR_A[0], Y_MIN, BAR_A[1] + 2.0))
    a['barB'] = mod_pt(S, (BAR_B[0], Y_MIN, BAR_B[1] + 2.0))
    a['conn'] = mod_pt(S, MAG_C)
    p1 = [o for o in S.pods if S.pod_num[o.name] == 1][0]
    p8 = [o for o in S.pods if S.pod_num[o.name] == 8][0]
    gp = (ctr([p1]) + ctr([p8])) / 2
    a['gap'] = Vector((gp.x, gp.y - 0.012, gp.z))
    shot(R, 'main', cam, 980, 860, a)


def f_exploded(R, NB):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    import guide_figures as GF
    S = ring(NB)
    paint(S.mag, 'mag')
    up, rad = S.up, S.radial
    rd = GF.dot_obj(NB, 'root_dot', NB.mat_foam())
    rd.matrix_world = S.T @ Matrix.Translation((0, -0.0104, -0.0004))
    rd['M0'] = [list(r) for r in rd.matrix_world]
    paint([rd], 'dot')
    for o in S.leads + S.jwires:
        o.hide_render = True
        o['mode'] = 'hide'
    for o in S.mag:
        o['M0'] = [list(r) for r in o.matrix_world]
    moves = [(o, rad(o) * 0.007) for o in S.foam + [rd]] + [(o, rad(o) * 0.016) for o in S.pods] + \
            [(o, up * 0.012) for o in S.base] + [(o, up * 0.012 + S.prox * 0.012) for o in S.mag] + \
            [(o, up * 0.023) for o in S.board] + [(o, up * 0.033) for o in S.cell] + \
            [(o, up * 0.044) for o in S.lid] + [(o, up * 0.054) for o in S.cap]
    a, paths = {}, {}
    for o, v in moves:
        M0 = Matrix(o['M0']) if 'M0' in o.keys() and o in S.mag else S.M0(o)
        o.matrix_world = Matrix.Translation(v) @ M0
    for o in S.webs:
        V = NB.verts_np(o, world=False)
        th = np.arctan2(V[:, 0], V[:, 2] - S.z_axis)
        V[:, 0] += 0.025 * np.sin(th)
        V[:, 2] += 0.025 * np.cos(th)
        o.data.vertices.foreach_set('co', V.ravel())
        o.data.update()
    bpy.context.view_layer.update()
    for key, grp, v in (('lid', S.lid, up * 0.044), ('cap', S.cap, up * 0.054), ('cell', S.cell, up * 0.033),
                        ('board', [S.board[0]], up * 0.023), ('base', S.base, up * 0.012)):
        c = ctr(grp)
        a[key] = c
        paths['t_' + key] = [c - v + up * 0.002, c]
    cm = ctr(S.mag)
    a['conn'] = cm
    paths['t_conn'] = [cm - S.prox * 0.010, cm]
    p1 = [o for o in S.pods if S.pod_num[o.name] == 2][0]
    a['pod'] = ctr([p1])
    paths['t_pod'] = [ctr([p1]) - rad(p1) * 0.016, ctr([p1])]
    fo = max(S.foam, key=lambda o: ctr([o]).x + 0.2 * ctr([o]).z)
    a['foam'] = ctr([fo])
    fl = max(S.flex, key=lambda o: ctr([o]).x - 0.3 * ctr([o]).z)
    a['flex'] = ctr([fl])
    a['tail'] = ctr([S.tail])
    V = NB.verts_np(S.band_s)
    a['web'] = Vector(V[np.argmax(V[:, 0] - V[:, 2])].tolist())
    hb = S.straps.get('strap_tail_b')
    if hb is not None:
        paint([hb], 'hook')
        Vh = NB.verts_np(hb)
        a['hook'] = Vector(Vh[np.argmax(Vh[:, 0] - 0.3 * Vh[:, 2])].tolist())
    a['barA'] = mod_pt(S, (BAR_A[0], Y_MIN, BAR_A[1])) + up * 0.012
    cam = new_cam()
    ortho(cam, S.ring_c + up * 0.02, 18, 14)
    fit(cam, pts_of(S.pods + S.lid + S.cap + [S.band_s] + S.ends), 1000, 900, margin=1.08)
    shot(R, 'main', cam, 1000, 900, a, paths)


def f_lid(R, NB):
    from mathutils import Matrix
    S = ring(NB)
    colour_ring(S, dict(pods='hide', foam='hide', web='hide', slides='hide', base='on', flex='hide'))
    paint(S.flex + S.pads, 'flex', 'hide')
    paint(S.mag, 'mag')
    for o in S.cap:
        o.matrix_world = Matrix.Translation(S.up * 0.008) @ S.M0(o)
    for o in S.lid:
        o.matrix_world = Matrix.Translation(S.up * 0.020) @ S.M0(o)
    cam = new_cam()
    ortho(cam, mod_pt(S, (0, 0, 10)), 32, 30)
    fit(cam, pts_of(S.base + S.lid), 1000, 860, margin=1.06)
    U = S.up * 0.020
    a = dict(cap=ctr(S.cap) + S.up * 0.001, sw1=mod_pt(S, (SW1[0], SW1[1], 4.7)), led=mod_pt(S, (D1[0], D1[1], 9.6)) + U,
             d1=mod_pt(S, (D1[0], D1[1], 2.9)), lid=ctr(S.lid) + S.up * 0.004, bay=mod_pt(S, MAG_C))
    for i, (x0, x1, sy) in enumerate(SNAP_SEGS):
        a['snap%d' % i] = mod_pt(S, ((x0 + x1) / 2, 18.6 if sy > 0 else -16.45, 3.6))
    paths = dict(t0=[mod_pt(S, (-13, -15, 3)) + U, mod_pt(S, (-13, -15, 4))], t1=[mod_pt(S, (13, 17, 3)) + U, mod_pt(S, (13, 17, 4))],
                 t2=[ctr(S.cap), ctr(S.cap) - S.up * 0.007])
    shot(R, 'main', cam, 1000, 860, a, paths, hi=S.cap + S.lid)


def f_wear(R, NB):
    import bpy
    import numpy as np
    from mathutils import Vector
    wb_scene()
    band = NB.load_band()
    arm, info = NB.build_arm(curl=30)
    NB.fit_band_to_arm(band, arm)
    objs = list(band.values()) + [arm]
    rig = NB.rig_objects(objs)
    NB.pose(rig, pitch=8, floor_objs=objs, floor=0.0003)
    bpy.context.view_layer.update()
    paint([arm], 'skin')
    kmap = dict(module_base='base', module_lid='lid', button_cap='cap', pod_shells='pod', strap='web', flex='flex', pads='pad',
                foam='dot', lipo='cell', mag_connector='mag', mag_contacts='mag')
    for o in band.values():
        k = o['kind']
        if k in ('main_board', 'board_parts', 'cell_leads'):
            paint([o], 'board', 'hide')
        else:
            paint([o], kmap.get(k, 'pod'))
    c, mn, mx = NB.module_centre(band)
    cam = new_cam()
    tgt = c + rig.matrix_world.to_3x3() @ Vector((0, -0.04, -0.02))
    ortho(cam, tgt, 62, 34)
    fit(cam, pts_of([o for o in band.values() if o['kind'] == 'module_lid']).tolist() + [list(tgt + Vector((-0.09, -0.06, -0.03))), list(tgt + Vector((0.06, 0.08, 0.03)))], W0, 820, margin=1.0)
    lid = [o for o in band.values() if o['kind'] == 'module_lid']
    capo = [o for o in band.values() if o['kind'] == 'button_cap']
    base = [o for o in band.values() if o['kind'] == 'module_base']
    ax = rig.matrix_world.to_3x3() @ Vector((0, 1, 0))
    st = [o for o in band.values() if o['kind'] == 'strap']
    V = NB.verts_np(st[0])
    Vb = NB.verts_np(base[0])
    a = dict(module=ctr(lid) + Vector((0, 0, 0.004)), cap=ctr(capo), crease=c + ax * -0.026 + Vector((0, 0, -0.012)),
             web=Vector(V[np.argmax(V[:, 0])].tolist()), bar=Vector(Vb[np.argmax(Vb[:, 0])].tolist()))
    paths = dict(slip=[c + ax * -0.080 + Vector((0, 0, 0.026)), c + ax * -0.030 + Vector((0, 0, 0.026))])
    shot(R, 'main', cam, W0, 820, a, paths)


# --------------------------------------------------------------- r2 2D diagrams
def dg_cut(C, box):
    """the single-pass strap laid flat, ring end left: where to cut for each wrist, the loop panel and the hook tab."""
    d = C.d
    F = fonts()
    frame_box(d, box, 'The strap laid flat, ring end left (size L, 302 mm)')
    x, y, w, h = box
    L = 302.0
    x0, x1 = x + 200, x + w - 70
    sx = (x1 - x0) / L
    yb = y + 110
    hb = 34
    X = lambda mm: x0 + mm * sx
    d.rectangle([X(0), yb, X(L), yb + hb], fill=col255('web'), outline=INK, width=2)
    d.rectangle([X(127), yb, X(202), yb + hb], fill=tuple(int(0.75 * c + 0.25 * 255) for c in col255('web')), outline=INK, width=1)
    d.rectangle([X(258), yb, X(L), yb + hb], fill=col255('hook'), outline=INK, width=2)
    d.rounded_rectangle([X(-9), yb - 8, X(1), yb + hb + 8], radius=5, outline=col255('ring'), width=6)
    T(d, (X(164.5), yb + hb / 2), 'loop panel', font=F['small'], fill=(255, 255, 255), anchor='mm')
    T(d, (X(280), yb + hb / 2), 'hook tab', font=F['small'], fill=(255, 255, 255), anchor='mm')
    T(d, (X(-12), yb + hb / 2), 'steel ring', font=F['small'], fill=SUB, anchor='rm')
    for mm, lab in ((0, '0'), (127, '127'), (202, '202'), (258, '258'), (302, '302 mm')):
        d.line([(X(mm), yb + hb), (X(mm), yb + hb + 12)], fill=INK, width=1)
        T(d, (X(mm), yb + hb + 14), lab, font=F['small'], fill=SUB, anchor='ma')
    rows = [('145 mm wrist', 18, 33, 'cut off 18-33 mm (about 25)'), ('160 mm wrist', 10, 21, 'cut off 10-21 mm (about 13)'),
            ('180 mm wrist', 10, 10, 'cut off the ring only (10 mm); about 30 of the 44 mm hook tab lands on the panel')]
    for i, (name, c0, c1, txt) in enumerate(rows):
        yy = yb + hb + 70 + i * 50
        d.text((x0 - 20, yy), name, font=F['lab'], fill=INK, anchor='rm')
        d.rectangle([X(0), yy - 8, X(c1), yy + 8], fill=(250, 220, 200), outline=ACC, width=2)
        if c0 != c1:
            d.rectangle([X(c0), yy - 8, X(c1), yy + 8], fill=ACC)
        d.line([(X(c1), yy - 15), (X(c1), yy + 15)], fill=ACC, width=3)
        d.text((X(c1) + 16, yy), txt, font=F['sub'], fill=INK, anchor='lm')
    T(d, (x + 30, y + h - 26), 'Measure from the ring end. The pale part always comes off; cut square across the strap inside the solid '
      'range (a smaller wrist cuts more), then heat-seal the cut with a quick pass of a lighter flame.', font=F['small'], fill=SUB, anchor='lm')


def _band(d, pts, col, w=9):
    d.line(pts, fill=col, width=w, joint='curve')


def _marker(d, xy, n, F):
    cx, cy = xy
    r = 14
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACC, outline=(255, 255, 255), width=2)
    d.text((cx, cy + 1), str(n), font=F['num'], fill=(255, 255, 255), anchor='mm')


def dg_lock(C, box):
    """section through bar A (seen from the J1 end): the pinch lock, numbered."""
    d = C.d
    F = fonts()
    frame_box(d, box, 'Section at bar A (antenna side), seen from the J1 end')
    x, y, w, h = box
    M = MM(box, 30, (w * 0.60, h * 0.55))
    d.polygon([M(0.0, 4.0), M(1.6, -4.2), M(6.0, -4.2), M(6.0, 4.0)], fill=col255('base'), outline=INK)
    d.polygon([M(-4.4, 3.0), M(-2.9, -4.2), M(-7.5, -4.2), M(-8.6, 1.2), M(-7.9, 3.0)], fill=col255('base'), outline=INK)
    web, tail = col255('web'), tuple(int(0.6 * c + 0.4 * 255) for c in col255('web'))
    _band(d, [M(-13, -9.5), M(-6, -6.3), M(-1.4, -5.4), M(0.6, -3.6), M(-0.4, 2.0), M(-1.2, 4.6), M(-4.6, 5.2), M(-8.6, 3.6),
              M(-9.7, 1.0), M(-8.8, -4.6), M(-6.0, -5.0), M(-3.0, -4.9)], web)
    _band(d, [M(-3.0, -4.9), M(-2.1, -3.6), M(-2.7, -0.6)], tail)
    for n, (px, py) in enumerate(((0.1, -1.0), (-3.0, 5.4), (-9.9, -1.5), (-2.6, -1.4))):
        _marker(d, M(px, py), n + 1, F)
    T(d, M(-12.6, -10.4), 'band from pod 5', font=F['small'], fill=SUB, anchor='lt')
    T(d, M(3.8, 1.5), 'end wall\n(base)', font=F['small'], fill=(255, 255, 255), anchor='mm')
    T(d, M(-5.6, -1.6), 'bar A', font=F['small'], fill=(255, 255, 255), anchor='mm')
    steps = ['From under the module, push the cut end up\nthrough slot A, on the end-wall side.', 'Over bar A.',
             'Down its outer face and under it.', 'Tuck the end back up the slot, between\nthe bar and the band, about 6 mm.']
    ty = y + 46
    for n, t in enumerate(steps):
        _marker(d, (x + 34, ty + 12), n + 1, F)
        T(d, (x + 58, ty), t, font=F['sub'], fill=INK, anchor='la')
        ty += 30 if '\n' not in t else 54


def dg_fold(C, box):
    """section through bar B: up the slot, over the bar, the hook tab folded back onto the loop panel."""
    d = C.d
    F = fonts()
    frame_box(d, box, 'Section at bar B (button side), seen from the J1 end')
    x, y, w, h = box
    M = MM(box, 26, (w * 0.30, h * 0.54))
    d.polygon([M(0.0, 4.0), M(-1.6, -4.2), M(-6.0, -4.2), M(-6.0, 4.0)], fill=col255('base'), outline=INK)
    d.polygon([M(3.5, 3.0), M(2.3, -4.2), M(6.9, -4.2), M(8.0, 1.2), M(7.3, 3.0)], fill=col255('base'), outline=INK)
    web, hook = col255('web'), col255('hook')
    inc = [(17.0, -11.6), (9.5, -7.4), (6.0, -6.2), (1.6, -5.4), (0.2, -3.6), (1.0, 2.0), (1.6, 4.6), (4.6, 5.3), (8.4, 3.7),
           (9.4, 0.5), (9.7, -3.0)]
    _band(d, [M(*p) for p in inc], web)
    nx, ny = 0.491, 0.871                                # normal (outward) of the incoming run
    back = [(10.2, -5.6)] + [(px + 0.55 * nx, py + 0.55 * ny) for px, py in ((11.2, -8.3), (17.0, -11.6))]
    _band(d, [M(9.7, -3.0)] + [M(*p) for p in back[:1]], web)
    _band(d, [M(*p) for p in back], hook, w=8)
    for n, (px, py) in enumerate(((0.2, -1.0), (4.6, 6.0), (13.6, -8.0))):
        _marker(d, M(px, py), n + 1, F)
    T(d, M(15.0, -12.6), 'band from pod 2', font=F['small'], fill=SUB, anchor='rt')
    T(d, M(-3.0, 1.5), 'end wall', font=F['small'], fill=(255, 255, 255), anchor='mm')
    T(d, M(5.0, -1.5), 'bar B', font=F['small'], fill=(255, 255, 255), anchor='mm')
    steps = ['Push the hook end up through slot B\nfrom under the module.', 'Over bar B, and fold it back down\nover the band.',
             'Pull it snug and press the hook tab\nonto the loop panel.']
    ty = y + 46
    for n, t in enumerate(steps):
        _marker(d, (x + w - 420, ty + 12), n + 1, F)
        T(d, (x + w - 396, ty), t, font=F['sub'], fill=INK, anchor='la')
        ty += 58
    T(d, (x + w - 396, ty + 8), 'To loosen: peel the tab and pull.', font=F['sub'], fill=ACC, anchor='la')


def dg_channel(C, box):
    """pod section along the arm (across the strap), to pod.py: floor, 20.8 x 2.5 channel, 0.8 mm lips."""
    d = C.d
    F = fonts()
    frame_box(d, box, 'Pod, cut across the strap')
    x, y, w, h = box
    M = MM(box, 14.5, (w * 0.5, h * 0.80))
    bt, ch, lt = BT_POD, 2.5, 1.0
    top = bt + ch + lt
    a_, y1_, y2_, eh = 8.0, 10.4, 16.0, 2.0                 # pod.py r2.1 end dome (quarter ellipse, tangent at the crest)
    r_ = math.sqrt(1 - ((y2_ - y1_) / a_) ** 2)
    zc_ = (eh - r_ * top) / (1 - r_)
    dome = [(y1_ + (y2_ - y1_) * k / 16, zc_ + (top - zc_) * math.sqrt(max(0.0, 1 - ((y2_ - y1_) * k / 16 / a_) ** 2))) for k in range(17)]
    half = [(16.0, 0.0)] + dome[::-1] + [(9.6, top), (9.6, bt + ch), (10.4, bt + ch), (10.4, bt)]
    pts = half + [(-u, v) for u, v in reversed(half)]
    d.polygon([M(u, v) for u, v in pts], fill=col255('pod'), outline=INK)
    M.rect(d, -10.0, bt + 0.05, 10.0, bt + 2.05, fill=col255('web'), outline=None, width=0)
    T(d, M(0, bt + 1.05), 'strap (20 mm)', font=F['small'], fill=(255, 255, 255), anchor='mm')
    T(d, M(-9.0, top + 1.6), 'lip', font=F['small'], fill=INK, anchor='mm')
    T(d, M(9.0, top + 1.6), 'lip', font=F['small'], fill=INK, anchor='mm')
    arrow(d, M(-9.0, top + 1.0), M(-9.9, top - 0.3), col=INK, w=2, head=8)
    arrow(d, M(9.0, top + 1.0), M(9.9, top - 0.3), col=INK, w=2, head=8)
    dim(d, M(-10.4, -1.0), M(10.4, -1.0), '', side=1)
    T(d, M(0, -1.6), 'channel 20.8 x 2.5 mm, lips 0.8 mm over each edge', font=F['small'], fill=SUB, anchor='mt')
    T(d, M(0, bt * 0.45), 'foam dots and flex below', font=F['small'], fill=(225, 225, 225), anchor='mm')


def dg_cable(C, box):
    """the cable: male half of the magnetic pair (sprung pins) to a USB-A lead, red to +5 V."""
    d = C.d
    F = fonts()
    frame_box(d, box)
    x, y, w, h = box
    cx, cy = x + 210, y + h / 2
    d.rounded_rectangle([cx - 150, cy - 40, cx + 150, cy + 40], radius=14, fill=col255('mag'), outline=INK, width=2)
    for sx_, lab in ((-110, 'N'), (110, 'S')):
        d.ellipse([cx + sx_ - 22, cy - 22, cx + sx_ + 22, cy + 22], fill=(150, 150, 155), outline=INK, width=2)
        d.text((cx + sx_, cy), lab, font=F['small'], fill=INK, anchor='mm')
    for sx_ in (-32, 32):
        d.ellipse([cx + sx_ - 11, cy - 11, cx + sx_ + 11, cy + 11], fill=col255('pad'), outline=INK, width=2)
    d.text((cx - 150, cy - 64), 'Male half: 2 sprung pins between 2 magnets (2.5 mm pitch)', font=F['sub'], fill=INK, anchor='lm')
    ux = x + w - 230
    d.rounded_rectangle([ux, cy - 30, ux + 150, cy + 30], radius=6, fill=col255('usb'), outline=INK, width=2)
    d.rectangle([ux + 150, cy - 20, ux + 200, cy + 20], fill=(200, 200, 205), outline=INK, width=2)
    d.text((ux + 75, cy), 'USB-A lead', font=F['small'], fill=(255, 255, 255), anchor='mm')
    for sx_, key, dy, lab in ((32, 'red', -16, 'red: +5 V'), (-32, 'black', 16, 'black: GND')):
        d.line([(cx + sx_, cy + 11), (cx + sx_, cy + 60 + dy), (ux - 40, cy + 60 + dy), (ux - 40, cy + dy / 2), (ux, cy + dy / 2)],
               fill=col255(key), width=5, joint='curve')
        d.text((ux - 50, cy + 60 + dy + (14 if dy > 0 else -14)), lab, font=F['small'], fill=INK, anchor='rm')
    T(d, (x + 30, y + h - 30), 'Mark the red pin on the housing. The magnets only let the cable on one way round.', font=F['sub'], fill=SUB, anchor='lm')


def dg_wiring_r2(C, box):
    d = C.d
    F = fonts()
    frame_box(d, box)
    x, y, w, h = box
    px = x + 230
    rows = [(0, 'TP1  +3V3', 'red', '3V3(OUT)  pin 36', 'bare board only,\nnever with the cell'), (1, 'TP2  SWDIO', 'wire_y', 'GP3  pin 5', ''),
            (2, 'TP3  SWDCLK', 'wire_g', 'GP2  pin 4', ''), (3, 'TP4  NRST', None, 'not connected', ''), (4, 'TP5  GND', 'black', 'GND  pin 3', '')]
    pico_x = x + w - 300
    d.rounded_rectangle([pico_x, y + 40, pico_x + 120, y + h - 40], radius=10, fill=(30, 110, 60), outline=INK, width=2)
    d.text((pico_x + 60, y + 60), 'Pico 2', font=F['lab'], fill=(255, 255, 255), anchor='ma')
    T(d, (pico_x + 60, y + 92), '(debugprobe\nfirmware)', font=F['small'], fill=(225, 240, 230), anchor='ma', align='center')
    d.text((px, y + 24), 'wires soldered to the pads', font=F['sub'], fill=SUB, anchor='ma')
    for i, name, colk, pin, note in rows:
        yy = y + 120 + i * ((h - 170) / 4)
        d.ellipse([px - 7, yy - 7, px + 7, yy + 7], fill=col255('pad'), outline=INK, width=1)
        d.text((px - 16, yy), name, font=F['lab'], fill=INK, anchor='rm')
        if colk:
            c = col255(colk)
            d.line([(px, yy), (pico_x, yy)], fill=c, width=5)
            d.ellipse([pico_x - 6, yy - 6, pico_x + 6, yy + 6], fill=(220, 200, 120), outline=INK, width=1)
            d.text((pico_x + 132, yy), pin, font=F['sub'], fill=INK, anchor='lm')
            if note:
                T(d, (px - 16, yy + 18), note, font=F['small'], fill=ACC, anchor='ra')
        else:
            d.text((px + 30, yy), 'not needed', font=F['small'], fill=SUB, anchor='lm')


def dg_wrist_r2(C, box):
    d = C.d
    frame_box(d, box, 'Right forearm, back of the hand up')
    x, y, w, h = box
    cx = x + w / 2
    sk = (238, 214, 196)
    d.rounded_rectangle([cx - 60, y + 230, cx + 60, y + h - 20], radius=40, fill=sk, outline=INK, width=2)
    d.ellipse([cx - 78, y + 50, cx + 78, y + 250], fill=sk, outline=INK, width=2)
    d.rounded_rectangle([cx - 150, y + 120, cx - 70, y + 160], radius=18, fill=sk, outline=INK, width=2)
    for i in range(4):
        fx = cx - 54 + i * 36
        d.rounded_rectangle([fx, y + 34, fx + 28, y + 110], radius=12, fill=sk, outline=INK, width=2)
    by = y + 300
    d.rectangle([cx - 66, by - 14, cx + 66, by + 14], fill=col255('web'))
    d.rounded_rectangle([cx - 40, by - 26, cx + 40, by + 26], radius=8, fill=col255('lid'), outline=INK, width=2)
    d.rectangle([cx - 52, by - 18, cx - 42, by + 18], fill=col255('base'), outline=INK)
    d.rectangle([cx + 42, by - 18, cx + 52, by + 18], fill=col255('base'), outline=INK)
    d.ellipse([cx - 34, by - 18, cx - 22, by - 6], fill=col255('cap'))
    F = fonts()
    d.text((cx - 70, by - 44), 'button, bar B', font=F['small'], fill=INK, anchor='rm')
    d.line([(cx - 68, by - 42), (cx - 30, by - 14)], fill=INK, width=1)
    T(d, (cx, by + 44), 'module on the back,\nJ1 end toward the hand', font=F['small'], fill=INK, anchor='ma', align='center')
    d.text((cx - 112, y + 172), 'thumb', font=F['small'], fill=SUB, anchor='mm')
    T(d, (cx + 70, by + 6), 'bar A on the\nlittle-finger side', font=F['small'], fill=SUB, anchor='lm')
    d.text((cx, y + h - 34), '~25 mm above the wrist crease', font=F['small'], fill=SUB, anchor='mm')


FIG_FUNCS = {'0.1': f_kit, '0.2': f_names, '0.3': f_exploded, '0.4': f_section, '1.1': f_swd_wires, '2.1': f_cell_leads,
             '2.2': f_j3_wires, '3.1': f_jig, '3.2': f_flex_on, '3.3': f_dots_pod, '3.4': f_pods_in, '3.5': f_strip,
             '4.1': f_dots_base, '4.2': f_base_jig, '5.1': f_j1, '5.2': f_fold, '5.3': f_bay, '6.1': f_lid, '7.2': None,
             '7.3': f_lock_a, '7.4': f_press, '7.5': f_fold_b, '8.1': f_wear, '9.1': None, '9.2': f_charge, '10.1': f_open}


def render(fid, out_root):
    import bpy
    sys.path.insert(0, HERE)
    import nb_blender as NB
    NB.reset()
    NB.MATS.clear()
    R = Rec(fid, os.path.join(out_root, fname(fid)))
    fn = FIG_FUNCS.get(fid)
    if fn is not None:
        fn(R, NB)
    save_meta(R)
    return R


# ============================================================== PIL side
INK = (32, 31, 30)
SUB = (96, 94, 90)
ACC = (226, 96, 36)
PAPER = tuple(int(c * 255) for c in BG)
TITLE_H = 64


def _font(name, size):
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(size))


FT = None


def fonts():
    global FT
    if FT is None:
        FT = dict(lab=_font('NotoSans-Medium.ttf', 24), sub=_font('NotoSans-Regular.ttf', 20), small=_font('NotoSans-Regular.ttf', 17),
                  num=_font('NotoSans-Bold.ttf', 19), title=_font('NotoSans-Medium.ttf', 30), tnum=_font('NotoSans-Bold.ttf', 28),
                  panel=_font('NotoSans-Bold.ttf', 22), dim=_font('NotoSans-Regular.ttf', 16))
    return FT


def col255(key):
    c = COL[key] if isinstance(key, str) else key
    return tuple(int(255 * x) for x in c)


def arrow(d, p0, p1, col=ACC, w=4, head=16, dashed=False, both=False):
    x0, y0 = p0
    x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    e0 = (x0 + ux * head * 0.8, y0 + uy * head * 0.8) if both else (x0, y0)
    e1 = (x1 - ux * head * 0.8, y1 - uy * head * 0.8)
    if dashed:
        n = max(1, int(L / 14))
        for i in range(n):
            a, b = i / n, (i + 0.55) / n
            d.line([(e0[0] + (e1[0] - e0[0]) * a, e0[1] + (e1[1] - e0[1]) * a),
                    (e0[0] + (e1[0] - e0[0]) * min(b, 1), e0[1] + (e1[1] - e0[1]) * min(b, 1))], fill=col, width=w)
    else:
        d.line([e0, e1], fill=col, width=w)
    for (ex, ey, sx, sy) in [(x1, y1, ux, uy)] + ([(x0, y0, -ux, -uy)] if both else []):
        d.polygon([(ex, ey), (ex - sx * head - sy * head * 0.45, ey - sy * head + sx * head * 0.45),
                   (ex - sx * head + sy * head * 0.45, ey - sy * head - sx * head * 0.45)], fill=col)


def polyarrow(d, pts, col=ACC, w=4, head=16, dashed=False):
    if len(pts) < 2:
        return
    if dashed:
        acc = 0
        for i in range(len(pts) - 2):
            if (acc // 1) % 2 == 0:
                d.line([tuple(pts[i]), tuple(pts[i + 1])], fill=col, width=w)
            acc += 1
    else:
        d.line([tuple(p) for p in pts[:-1]], fill=col, width=w, joint='curve')
    arrow(d, pts[-2], pts[-1], col, w, head)


def text_block(d, xy, text, anchor='la', font=None, sub=None, col=INK, halo=True):
    F = fonts()
    lines = text.split('\n')
    x, y = xy
    hs = []
    for i, ln in enumerate(lines):
        f = font or (F['lab'] if i == 0 else F['sub'])
        if sub is not None and i > 0:
            f = sub
        bb = d.textbbox((0, 0), ln, font=f)
        hs.append((bb[2] - bb[0], bb[3] - bb[1] + 6, f))
    H = sum(h for _, h, _ in hs)
    if anchor[1] == 'm':
        y -= H / 2
    elif anchor[1] == 'b':
        y -= H
    for i, ln in enumerate(lines):
        w_, h_, f = hs[i]
        xx = x if anchor[0] == 'l' else (x - w_ if anchor[0] == 'r' else x - w_ / 2)
        c = col if i == 0 else SUB
        if halo:
            d.text((xx, y), ln, font=f, fill=c, stroke_width=4, stroke_fill=PAPER)
        else:
            d.text((xx, y), ln, font=f, fill=c)
        y += h_
    return max(w for w, _, _ in hs), H


def outline_mask(im, mask_path, box_xform):
    """orange outline round the white pixels of the mask (already scaled to the panel)."""
    from PIL import Image, ImageFilter, ImageChops
    m = Image.open(mask_path).convert('L')
    sc, ox, oy = box_xform
    m = m.resize((int(m.size[0] * sc), int(m.size[1] * sc)))
    a = m.point(lambda v: 255 if v > 100 else 0)
    big = a.filter(ImageFilter.MaxFilter(7))
    ring = ImageChops.subtract(big, a)
    lay = Image.new('L', im.size, 0)
    lay.paste(ring, (int(ox), int(oy)))
    im.paste(Image.new('RGB', im.size, ACC), (0, 0), lay)


class Ctx:
    def __init__(self, fid, meta, src):
        from PIL import Image, ImageDraw
        self.fid, self.meta, self.src = fid, meta, src
        spec = SPECS.get(fid, {})
        self.spec = spec
        W, H = spec.get('canvas', (W0, 900))
        self.im = Image.new('RGB', (W, H + TITLE_H), PAPER)
        self.d = ImageDraw.Draw(self.im)
        self.xf = {}

    def P(self, shot, key):
        s = self.meta[shot]
        sc, ox, oy = self.xf[shot]
        x, y = s['pts'][key]
        return (ox + x * sc, oy + y * sc)

    def path(self, shot, key):
        s = self.meta[shot]
        sc, ox, oy = self.xf[shot]
        return [(ox + x * sc, oy + y * sc) for x, y in s['paths'][key]]


def place_panels(C):
    from PIL import Image
    for shot, box, *rest in C.spec.get('panels', []):
        if shot not in C.meta:
            continue
        s = C.meta[shot]
        img = Image.open(os.path.join(C.src, s['file'])).convert('RGB')
        x, y, w, h = box
        y += TITLE_H
        sc = min(w / img.size[0], h / img.size[1])
        img2 = img.resize((int(img.size[0] * sc), int(img.size[1] * sc)), Image.LANCZOS)
        ox, oy = x + (w - img2.size[0]) / 2, y + (h - img2.size[1]) / 2
        C.im.paste(img2, (int(ox), int(oy)))
        C.xf[shot] = (sc, ox, oy)
        if s.get('mask') and shot not in C.spec.get('no_outline', []):
            outline_mask(C.im, os.path.join(C.src, s['mask']), (sc, ox, oy))
        if rest and rest[0]:
            text_block(C.d, (x + 14, y + 10), rest[0], font=fonts()['panel'])
        if len(rest) > 1 and rest[1]:
            C.d.rectangle([x + 2, y + 2, x + w - 2, y + h - 2], outline=(200, 197, 190), width=2)


def draw_insets(C):
    from PIL import Image, ImageDraw
    for ins in C.spec.get('insets', []):
        x, y = ins['at']
        y += TITLE_H
        r = ins.get('r', 130)
        if 'shot' in ins and ins['shot'] in C.meta:
            s = C.meta[ins['shot']]
            img = Image.open(os.path.join(C.src, s['file'])).convert('RGB')
            if s.get('mask'):
                pass
            sz = 2 * r
            img = img.resize((sz, int(sz * img.size[1] / img.size[0])))
            cy = img.size[1] // 2
            img = img.crop((0, cy - r, sz, cy + r))
            mk = Image.new('L', (sz, sz), 0)
            ImageDraw.Draw(mk).ellipse([0, 0, sz - 1, sz - 1], fill=255)
            C.im.paste(img, (int(x - r), int(y - r)), mk)
        elif 'draw' in ins:
            C.d.ellipse([x - r, y - r, x + r, y + r], fill=(252, 251, 248))
            ins['draw'](C.d, (x - r * 0.78, y - r * 0.62, r * 1.56, r * 1.24))
        C.d.ellipse([x - r, y - r, x + r, y + r], outline=INK, width=3)
        if ins.get('anchor'):
            ax, ay = C.P(*ins['anchor'])
            rr = ins.get('ar', 26)
            C.d.ellipse([ax - rr, ay - rr, ax + rr, ay + rr], outline=INK, width=3)
            L = math.hypot(x - ax, y - ay) or 1
            ux, uy = (x - ax) / L, (y - ay) / L
            C.d.line([(ax + ux * rr, ay + uy * rr), (x - ux * r, y - uy * r)], fill=INK, width=2)
        if ins.get('caption'):
            text_block(C.d, (x, y + r + 8), ins['caption'], anchor='ma', font=fonts()['sub'])


def draw_arrows(C):
    for a in C.spec.get('travel', []):
        shot, key = a[0], a[1]
        if shot in C.xf and key in C.meta[shot]['paths']:
            pts = C.path(shot, key)
            if len(pts) == 2:
                arrow(C.d, pts[0], pts[1], dashed=True, w=3, head=15)
            else:
                polyarrow(C.d, pts, w=4)
    for a in C.spec.get('curve', []):
        shot, key = a[0], a[1]
        if shot in C.xf and key in C.meta[shot]['paths']:
            polyarrow(C.d, C.path(shot, key), w=5, head=20)


def label_size(d, text):
    """(w, h) of a label block (first line medium, the rest regular)."""
    F = fonts()
    w = h = 0
    for i, ln in enumerate(text.split('\n')):
        f = F['lab'] if i == 0 else F['sub']
        bb = d.textbbox((0, 0), ln, font=f)
        w = max(w, bb[2] - bb[0])
        h += bb[3] - bb[1] + 6
    return w, h


def _rect_hit(r, q, pad=0):
    return not (r[2] + pad <= q[0] or q[2] + pad <= r[0] or r[3] + pad <= q[1] or q[3] + pad <= r[1])


def _seg_rect(p0, p1, r, shrink=1.0):
    """does segment p0-p1 pass through rectangle r (shrunk a little, so touching an edge is fine)?"""
    x0, y0, x1, y1 = r[0] + shrink, r[1] + shrink, r[2] - shrink, r[3] - shrink
    if x0 >= x1 or y0 >= y1:
        return False
    (ax, ay), (bx, by) = p0, p1
    t0, t1 = 0.0, 1.0
    dx, dy = bx - ax, by - ay
    for pp, qq in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if pp == 0:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def _nearest_on_rect(p, r):
    """the leader end: the point of rectangle r nearest to p (on its edge)."""
    x = min(max(p[0], r[0]), r[2])
    y = min(max(p[1], r[1]), r[3])
    if r[0] < x < r[2] and r[1] < y < r[3]:            # inside: go to the nearest edge
        dl, dr, dt, db = x - r[0], r[2] - x, y - r[1], r[3] - y
        m = min(dl, dr, dt, db)
        if m == dl:
            x = r[0]
        elif m == dr:
            x = r[2]
        elif m == dt:
            y = r[1]
        else:
            y = r[3]
    return (x, y)


def blocked_regions(C):
    """rectangles labels must not cover: the title bar, 2D diagrams, insets, panel captions."""
    W, H = C.im.size
    R = [(0, 0, W, TITLE_H)]
    for fn, box in C.spec.get('diagrams', []):
        x, y, w, h = box
        R.append((x, y + TITLE_H, x + w, y + TITLE_H + h))
    for ins in C.spec.get('insets', []):
        x, y = ins['at']
        y += TITLE_H
        r = ins.get('r', 130)
        R.append((x - r, y - r, x + r, y + r + (30 if ins.get('caption') else 0)))
    for shot, box, *rest in C.spec.get('panels', []):
        if rest and rest[0]:
            R.append((box[0], box[1] + TITLE_H, box[0] + 260, box[1] + TITLE_H + 36))
    if C.spec.get('note'):
        R.append((0, H - 44, W, H))
    return R


def draw_labels(C):
    """place every label so that its box stays on the image, overlaps no other label or blocked region,
    and no leader crosses any label; leaders end on the nearest edge of their own label's box."""
    from PIL import Image
    d = C.d
    W, H = C.im.size
    labs = [(C.P(s, k), t, pl, s, k) for s, k, t, pl in C.spec.get('labels', []) if s in C.xf and k in C.meta[s]['pts']]
    blocked = blocked_regions(C)
    placed = []                                        # (rect, anchor, leader_end, text)
    PAD = 5

    def rect_at(tx, ty, w, h, ax):                     # ax: 'l' text starts at tx, 'r' ends at tx, 'm' centred
        x0 = tx if ax == 'l' else (tx - w if ax == 'r' else tx - w / 2)
        return (x0 - PAD, ty - PAD, x0 + w + PAD, ty + h + PAD)

    def ok(r, p):
        if r[0] < 4 or r[1] < TITLE_H + 2 or r[2] > W - 4 or r[3] > H - 4:
            return False
        for q in blocked:
            if _rect_hit(r, q):
                return False
        e = _nearest_on_rect(p, r)
        for q, pa, pe, _ in placed:
            if _rect_hit(r, q, 4):
                return False
            if _seg_rect(pa, pe, r) or _seg_rect(p, e, q):
                return False
        return True

    def candidates(p, pl, s, w, h):
        box = [b for sh, b, *r in C.spec['panels'] if sh == s][0]
        out = []
        if pl in ('L', 'R'):
            tx = box[0] + 16 if pl == 'L' else box[0] + box[2] - 16
            for dy in (0, 30, -30, 60, -60, 90, -90, 130, -130, 180, -180, 240, -240):
                out.append((tx, p[1] - h / 2 + dy, 'l' if pl == 'L' else 'r'))
        else:
            dx, dy = pl[0], pl[1]
            anc = pl[2] if len(pl) > 2 else 'lm'
            base = [(dx, dy, anc)]
            for rr in (90, 140, 200, 260, 330):
                for ang in (-60, -120, 60, 120, 0, 180, -90, 90, -30, -150, 30, 150):
                    ex, ey = rr * math.cos(math.radians(ang)), rr * math.sin(math.radians(ang))
                    base.append((ex, ey, ('l' if ex > 20 else ('r' if ex < -20 else 'm')) + ('m' if abs(ey) < 30 else ('t' if ey > 0 else 'b'))))
            for dx_, dy_, an in base:
                tx, ty = p[0] + dx_, p[1] + dy_
                ty0 = ty - h / 2 if an[1] == 'm' else (ty if an[1] == 't' else ty - h)
                out.append((tx + (6 if an[0] == 'l' else (-6 if an[0] == 'r' else 0)), ty0, an[0]))
        return out

    hits = []
    for p, t, pl, s, k in labs:
        w, h = label_size(d, t)
        cands = candidates(p, pl, s, w, h)
        chosen = None
        for tx, ty, ax in cands:
            r = rect_at(tx, ty, w, h, ax)
            if r[0] - 1 <= p[0] <= r[2] + 1 and r[1] - 1 <= p[1] <= r[3] + 1:
                continue                               # the anchor must not sit under its own label
            if ok(r, p):
                chosen = (tx, ty, ax, r)
                break
        if chosen is None:
            tx, ty, ax = cands[0]
            chosen = (tx, ty, ax, rect_at(tx, ty, w, h, ax))
            hits.append('%s: no free place for "%s"' % (C.fid, t.split(chr(10))[0]))
        tx, ty, ax, r = chosen
        e = _nearest_on_rect(p, r)
        placed.append((r, p, e, t))
        C.label_meta = getattr(C, 'label_meta', []) + [(r, p, e, t, tx, ty, ax)]
    # light box behind each label, then leaders, text, anchor dots
    C.label_meta = getattr(C, 'label_meta', [])
    for r, p, e, t, tx, ty, ax in C.label_meta:
        reg = C.im.crop(tuple(int(v) for v in r))
        C.im.paste(Image.blend(reg, Image.new('RGB', reg.size, PAPER), 0.78), (int(r[0]), int(r[1])))
    d = ImageDraw_(C)
    for r, p, e, t, tx, ty, ax in C.label_meta:
        d.line([p, e], fill=INK, width=2)
    for r, p, e, t, tx, ty, ax in C.label_meta:
        text_block(d, (tx, ty), t, anchor=ax + 'a', halo=False)
    for r, p, e, t, tx, ty, ax in C.label_meta:
        d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], fill=(255, 255, 255), outline=INK, width=2)
    C.label_hits = hits + check_labels(C)


def ImageDraw_(C):
    from PIL import ImageDraw
    C.d = ImageDraw.Draw(C.im)
    return C.d


def check_labels(C):
    """automatic check: no leader crosses a label box, no two label boxes overlap, nothing off the image."""
    W, H = C.im.size
    L = getattr(C, 'label_meta', [])
    out = []
    for i, (r, p, e, t, *_x) in enumerate(L):
        name = t.split('\n')[0]
        if r[0] < 0 or r[1] < 0 or r[2] > W or r[3] > H:
            out.append('%s: "%s" runs off the image' % (C.fid, name))
        for j, (q, pq, eq, tq, *_y) in enumerate(L):
            if j == i:
                continue
            if j > i and _rect_hit(r, q):
                out.append('%s: "%s" overlaps "%s"' % (C.fid, name, tq.split('\n')[0]))
            if _seg_rect(pq, eq, r):
                out.append('%s: leader of "%s" crosses "%s"' % (C.fid, tq.split('\n')[0], name))
        if _seg_rect(p, e, r, shrink=2.0):
            out.append('%s: leader of "%s" crosses its own text' % (C.fid, name))
    return out


def draw_nums(C):
    F = fonts()
    for s, k, n in C.spec.get('nums', []):
        if s in C.xf and k in C.meta[s]['pts']:
            x, y = C.P(s, k)
            r = 15
            C.d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255), outline=INK, width=2)
            C.d.text((x, y + 1), str(n), font=F['num'], fill=INK, anchor='mm')


def draw_title(C):
    F = fonts()
    d = C.d
    d.rectangle([0, 0, C.im.size[0], TITLE_H], fill=(236, 233, 226))
    d.text((24, TITLE_H / 2), C.fid, font=F['tnum'], fill=ACC, anchor='lm')
    d.text((24 + 70, TITLE_H / 2), TITLE[C.fid], font=F['title'], fill=INK, anchor='lm')
    if C.spec.get('note'):
        text_block(d, (24, C.im.size[1] - 14), C.spec['note'], anchor='lb', font=F['sub'])


def compose(fid, src_root, dst_dir):
    src = os.path.join(src_root, fname(fid))
    mp = os.path.join(src, 'meta.json')
    meta = json.load(open(mp)) if os.path.exists(mp) else {}
    C = Ctx(fid, meta, src)
    place_panels(C)
    for fn, box in C.spec.get('diagrams', []):
        x, y, w, h = box
        fn(C, (x, y + TITLE_H, w, h))
    draw_arrows(C)
    draw_insets(C)
    draw_nums(C)
    draw_labels(C)
    for fn in C.spec.get('post', []):
        fn(C)
    draw_title(C)
    dst = os.path.join(dst_dir, fname(fid) + '.png')
    C.im.save(dst, optimize=True)
    for h in getattr(C, 'label_hits', []):
        print('  LABEL CHECK', h)
    return dst


# ---------------------------------------------------------------- 2D diagrams (to the CAD dimensions)
def T(d, xy, txt, font=None, fill=INK, anchor='la', **kw):
    """d.text that also takes vertical anchors for multi-line text."""
    font = font or fonts()['dim']
    if '\n' not in txt:
        d.text(xy, txt, font=font, fill=fill, anchor=anchor)
        return
    bb = d.multiline_textbbox((0, 0), txt, font=font, spacing=4)
    hh = bb[3] - bb[1]
    x, y = xy
    y -= hh / 2 if anchor[1] == 'm' else (hh if anchor[1] in ('b', 's', 'd') else 0)
    d.multiline_text((x, y), txt, font=font, fill=fill, anchor=anchor[0] + 'a', spacing=4,
                     align={'l': 'left', 'm': 'center', 'r': 'right'}[anchor[0]])


class MM:
    """mm -> px inside a box; origin at (ox, oy) px, y up."""
    def __init__(self, box, s, origin):
        self.x, self.y, self.w, self.h = box
        self.s = s
        self.ox, self.oy = self.x + origin[0], self.y + origin[1]

    def __call__(self, u, v):
        return (self.ox + u * self.s, self.oy - v * self.s)

    def rect(self, d, u0, v0, u1, v1, fill=None, outline=INK, width=2, r=0):
        u0, u1 = min(u0, u1), max(u0, u1)
        v0, v1 = min(v0, v1), max(v0, v1)
        a, b = self(u0, v1), self(u1, v0)
        if r:
            d.rounded_rectangle([a, b], radius=r * self.s, fill=fill, outline=outline, width=width)
        else:
            d.rectangle([a, b], fill=fill, outline=outline, width=width)


def frame_box(d, box, title=None):
    x, y, w, h = box
    d.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=(252, 251, 248), outline=(190, 186, 178), width=2)
    if title:
        text_block(d, (x + 14, y + 8), title, font=fonts()['sub'], col=SUB, halo=False)


def dim(d, p0, p1, text, side=1, col=SUB):
    arrow(d, p0, p1, col=col, w=2, head=9, both=True)
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    T(d, (mx + 8 * side, my), text, fill=col, anchor='lm' if side > 0 else 'rm')


def strand(d, M, pts, col, t):
    q = [M(*p) for p in pts]
    w = max(2, int(t * M.s))
    d.line(q, fill=col, width=w)
    for x, y in q:
        d.ellipse([x - w / 2 + 0.5, y - w / 2 + 0.5, x + w / 2 - 0.5, y + w / 2 - 0.5], fill=col)


def arcp(cu, cv, r, a0, a1, n=20):
    return [(cu + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cv + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def dg_legend(C, box):
    d = C.d
    frame_box(d, box, 'Colours used in every figure')
    x, y, w, h = box
    n = len(LEGEND)
    cols = 8
    cw = (w - 28) / cols
    for i, (k, name) in enumerate(LEGEND):
        cx = x + 14 + (i % cols) * cw
        cy = y + 44 + (i // cols) * 34
        d.rounded_rectangle([cx, cy, cx + 26, cy + 20], radius=4, fill=col255(k), outline=INK, width=1)
        d.text((cx + 34, cy + 10), name, font=fonts()['small'], fill=INK, anchor='lm')
    # tools
    tx = x + 14
    ty = y + h - 40
    d.text((tx, ty + 12), 'You also need:', font=fonts()['sub'], fill=SUB, anchor='lm')
    tx += 150
    for name, icon in (('soldering iron + thin solder', 'iron'), ('thin CA glue', 'ca'), ('Kapton tape', 'kap'),
                       ('lighter', 'light'), ('flush cutter', 'cut'), ('multimeter', 'meter')):
        _icon(d, icon, tx, ty)
        d.text((tx + 44, ty + 12), name, font=fonts()['small'], fill=INK, anchor='lm')
        tx += 50 + d.textlength(name, font=fonts()['small']) + 26


def _icon(d, kind, x, y):
    c = INK
    if kind == 'iron':
        d.line([(x, y + 22), (x + 26, y + 4)], fill=c, width=6)
        d.line([(x + 26, y + 4), (x + 36, y - 2)], fill=c, width=2)
    elif kind == 'ca':
        d.rounded_rectangle([x + 6, y + 6, x + 22, y + 26], radius=3, outline=c, width=2)
        d.polygon([(x + 10, y + 6), (x + 18, y + 6), (x + 14, y - 4)], outline=c)
    elif kind == 'kap':
        d.ellipse([x + 2, y, x + 30, y + 26], outline=col255('kapton'), width=6)
    elif kind == 'light':
        d.rounded_rectangle([x + 8, y + 8, x + 22, y + 26], radius=2, outline=c, width=2)
        d.polygon([(x + 15, y - 4), (x + 11, y + 5), (x + 19, y + 5)], fill=ACC)
    elif kind == 'cut':
        d.line([(x + 4, y + 26), (x + 16, y + 6)], fill=c, width=3)
        d.line([(x + 28, y + 26), (x + 16, y + 6)], fill=c, width=3)
    elif kind == 'meter':
        d.rounded_rectangle([x + 4, y, x + 28, y + 26], radius=3, outline=c, width=2)
        d.rectangle([x + 8, y + 4, x + 24, y + 11], outline=c, width=1)


def dg_wrist(C, box):
    """pictogram: right forearm seen from above (back of the hand), module on the back, button to the thumb."""
    d = C.d
    frame_box(d, box, 'Right forearm, back of the hand up')
    x, y, w, h = box
    cx = x + w / 2
    sk = (238, 214, 196)
    d.rounded_rectangle([cx - 60, y + 230, cx + 60, y + h - 20], radius=40, fill=sk, outline=INK, width=2)     # forearm
    d.ellipse([cx - 78, y + 50, cx + 78, y + 250], fill=sk, outline=INK, width=2)                          # hand
    d.rounded_rectangle([cx - 150, y + 120, cx - 70, y + 160], radius=18, fill=sk, outline=INK, width=2)  # thumb (left on a right hand, back up)
    for i in range(4):
        fx = cx - 54 + i * 36
        d.rounded_rectangle([fx, y + 34, fx + 28, y + 110], radius=12, fill=sk, outline=INK, width=2)
    by = y + 300
    d.rectangle([cx - 66, by - 14, cx + 66, by + 14], fill=col255('web'))
    d.rounded_rectangle([cx - 40, by - 26, cx + 40, by + 26], radius=8, fill=col255('lid'), outline=INK, width=2)
    d.ellipse([cx - 34, by - 18, cx - 22, by - 6], fill=col255('cap'))
    F = fonts()
    d.text((cx - 70, by - 44), 'button', font=F['small'], fill=INK, anchor='rm')
    d.line([(cx - 68, by - 42), (cx - 30, by - 14)], fill=INK, width=1)
    T(d, (cx, by + 44), 'module on the back,\nJ1 end toward the hand', font=F['small'], fill=INK, anchor='ma', align='center')
    d.text((cx - 112, y + 172), 'thumb', font=F['small'], fill=SUB, anchor='mm')
    T(d, (cx + 86, by + 6), 'gap on the\npalm side,\nby the thumb', font=F['small'], fill=SUB, anchor='lm')
    d.text((cx, y + h - 34), '~25 mm above the wrist crease', font=F['small'], fill=SUB, anchor='mm')


def dg_wiring(C, box):
    d = C.d
    F = fonts()
    frame_box(d, box)
    x, y, w, h = box
    # jig pin tails (left), Pico 2 (right)
    px = x + 230
    rows = [(0, 'TP1  +3V3', 'red', '3V3(OUT)  pin 36', 'only while no cell is fitted'), (1, 'TP2  SWDIO', 'wire_y', 'GP3  pin 5', ''),
            (2, 'TP3  SWDCLK', 'wire_g', 'GP2  pin 4', ''), (3, 'TP4  NRST', None, 'not connected', ''), (4, 'TP5  GND', 'black', 'GND  pin 3', '')]
    pico_x = x + w - 300
    d.rounded_rectangle([pico_x, y + 40, pico_x + 120, y + h - 40], radius=10, fill=(30, 110, 60), outline=INK, width=2)
    d.text((pico_x + 60, y + 60), 'Pico 2', font=F['lab'], fill=(255, 255, 255), anchor='ma')
    T(d, (pico_x + 60, y + 92), '(debugprobe\nfirmware)', font=F['small'], fill=(225, 240, 230), anchor='ma', align='center')
    d.text((px, y + 24), 'jig pin tails', font=F['sub'], fill=SUB, anchor='ma')
    for i, name, colk, pin, note in rows:
        yy = y + 120 + i * ((h - 170) / 4)
        d.ellipse([px - 7, yy - 7, px + 7, yy + 7], fill=col255('pin'), outline=INK, width=1)
        d.text((px - 16, yy), name, font=F['lab'], fill=INK, anchor='rm')
        if colk:
            c = col255(colk)
            pts = [(px, yy), (px + 280, yy), (pico_x - 40, yy), (pico_x, yy)]
            if i == 0:
                for k in range(0, int(pico_x - px), 22):
                    d.line([(px + k, yy), (px + min(k + 12, pico_x - px), yy)], fill=c, width=5)
            else:
                d.line([(px, yy), (pico_x, yy)], fill=c, width=5)
            d.ellipse([pico_x - 6, yy - 6, pico_x + 6, yy + 6], fill=(220, 200, 120), outline=INK, width=1)
            d.text((pico_x + 132, yy), pin, font=F['sub'], fill=INK, anchor='lm')
            if note:
                d.text((px + 30, yy + 10), note, font=F['small'], fill=ACC, anchor='la')
        else:
            d.text((px + 30, yy), 'not needed', font=F['small'], fill=SUB, anchor='lm')


def dg_pin_lean(C, box):
    """section ACROSS the pin row (seen along it): neighbouring pins lean +/-12 deg, tips together in the
    common slot 1.4 mm above the nest floor, a drop of CA where each pin leaves its hole underneath."""
    d = C.d
    frame_box(d, box, 'Section across the row (seen along it)')
    x, y, w, h = box
    M = MM(box, 17, (w * 0.40, h * 0.88))
    floor, slot, cav = 16.5, 14.0, 3.0
    jc = col255('jig')
    M.rect(d, -7, cav, 7, slot, fill=jc)
    M.rect(d, -7, slot, -0.8, floor, fill=jc)
    M.rect(d, 0.8, slot, 7, floor, fill=jc)
    for sgn in (1, -1):
        lean = math.radians(12) * sgn
        xb = -math.tan(lean) * (17.9 - 1.9)
        d.line([M(xb, 1.9), M(0, 17.9)], fill=col255('pin'), width=max(3, int(0.68 * M.s)))
        d.ellipse([M(xb * 0.92 - 0.45, cav + 0.45), M(xb * 0.92 + 0.45, cav - 0.45)], fill=ACC)
    d.line([M(-7, floor + 1.4), M(7, floor + 1.4)], fill=SUB, width=1)
    dim(d, M(2.0, floor), M(2.0, floor + 1.4), 'tips 1.4 mm\nabove the floor')
    T(d, M(-6.8, floor + 0.3), 'nest floor', fill=SUB, anchor='lb')
    T(d, M(-6.8, cav - 0.6), 'CA drop where each\npin leaves its hole', fill=ACC, anchor='la')
    T(d, M(-6.8, 9.5), 'pins lean\n12 deg, alternately', fill=SUB, anchor='la')


def dg_tp_section(C, box):
    d = C.d
    frame_box(d, box, 'Pins on the test pads (from below)')
    x, y, w, h = box
    M = MM(box, 34, (w * 0.12, h * 0.42))
    M.rect(d, -1, 0, 8, 1.0, fill=col255('board'))
    for i in range(5):
        u = 0.3 + 1.27 * i
        M.rect(d, u - 0.45, -0.05, u + 0.45, 0.0, fill=col255('pad'))
        d.line([M(u, -0.05), M(u + (0.3 if i % 2 else -0.3), -4.5)], fill=col255('pin'), width=max(3, int(0.6 * M.s)))
    M.rect(d, -1, -4.4, 8, -3.0, fill=col255('jig'))
    T(d, M(-1, 1.6), 'board bottom, TP1 ... TP5', font=fonts()['dim'], fill=INK, anchor='lb')
    T(d, M(-1, -5.0), 'each pin pressed in 1.3 mm', font=fonts()['dim'], fill=SUB, anchor='la')


def dg_joint(C, box):
    d = C.d
    frame_box(d, box, 'J2 joint, side section (installed)')
    x, y, w, h = box
    M = MM(box, 28, (w * 0.10, h * 0.40))
    M.rect(d, -1, 0, 9, 1.0, fill=col255('board'))
    M.rect(d, 1.0, -0.05, 3.0, 0.0, fill=col255('pad'))
    d.line([M(-1, -0.35), M(1.2, -0.35)], fill=col255('red'), width=int(0.6 * M.s))
    d.ellipse([M(1.0, -0.05), M(2.8, -0.75)], fill=(200, 200, 200), outline=INK)
    M.rect(d, 0.5, -0.86, 3.6, -0.80, fill=col255('kapton'), outline=None)
    M.rect(d, -1, -1.6, 9, -3.2, fill=col255('base'))
    M.rect(d, 0.0, -1.6, 4.4, -0.6, fill=(252, 251, 248), outline=INK, width=1)
    dim(d, M(5.0, 0.0), M(5.0, -1.6), 'joint + Kapton\nunder 1.6 mm', side=1)
    d.text(M(-1, -3.7), 'base: 0.6 mm gap + the 1.0 mm relief under J2', font=fonts()['dim'], fill=SUB, anchor='la')
    d.text(M(1.2, -1.0), 'Kapton', font=fonts()['dim'], fill=ACC, anchor='la')


def dg_dot_pocket(C, box):
    d = C.d
    frame_box(d, box, 'One dot, seated')
    x, y, w, h = box
    M = MM(box, 26, (w * 0.40, h * 0.66))
    M.rect(d, -4.5, 0, 4.5, 4.9, fill=col255('pod'), r=0.4)
    M.rect(d, -3.2, 0, 3.2, 1.0, fill=(252, 251, 248), outline=INK)
    M.rect(d, -3.0, -1.0, 3.0, 1.0, fill=col255('dot'))
    d.line([M(-3.0, -1.05), M(3.0, -1.05)], fill=(150, 150, 150), width=3)
    T(d, M(3.4, -0.6), 'top liner: peel\nit after pressing', font=fonts()['dim'], fill=ACC, anchor='la')
    dim(d, M(-4.0, 0.0), M(-4.0, -1.0), '1.0 mm proud', side=-1)


def dg_pod_ledge(C, box):
    d = C.d
    frame_box(d, box, 'Pod pressed home (section)')
    x, y, w, h = box
    M = MM(box, 26, (w * 0.5, h * 0.72))
    jc = col255('jig')
    M.rect(d, -7.5, -3.0, 7.5, 0.0, fill=jc)
    M.rect(d, -7.0, 0.0, -5.7, 2.5, fill=jc)
    M.rect(d, 5.7, 0.0, 7.0, 2.5, fill=jc)
    M.rect(d, -5.5, 0.0, -4.5, 0.71, fill=jc)
    M.rect(d, 4.5, 0.0, 5.5, 0.71, fill=jc)
    M.rect(d, -3.6, 0.0, 3.6, 0.11, fill=col255('flex'), outline=None)
    M.rect(d, -3.0, 0.11, 3.0, 1.71, fill=col255('dot'))
    M.rect(d, -4.5, 0.71, 4.5, 5.61, fill=col255('pod'), r=0.4)
    M.rect(d, -3.2, 0.71, 3.2, 1.71, fill=col255('dot'), outline=INK, width=1)
    T(d, M(-7.5, 6.6), 'the pod stops on the ledges', font=fonts()['dim'], fill=SUB, anchor='lb')
    d.text(M(-7.5, -3.5), 'flex on the plate, dot squeezed to 1.6 mm', font=fonts()['dim'], fill=SUB, anchor='la')


def dg_j1(C, box):
    d = C.d
    frame_box(d, box, 'J1 section, latch closed')
    x, y, w, h = box
    M = MM(box, 34, (w * 0.30, h * 0.66))
    M.rect(d, -1, -1.0, 6, 0.0, fill=col255('board'))
    M.rect(d, 0.0, 0.0, 5.1, 2.0, fill=(60, 60, 62))
    M.rect(d, 0.3, 0.30, 4.6, 0.75, fill=(252, 251, 248), outline=None)
    for u in (1.0, 2.0, 3.0):
        d.polygon([M(u, 0.30), M(u + 0.4, 0.55), M(u + 0.8, 0.30)], fill=col255('pad'))
    M.rect(d, -2.5, 0.42, 4.2, 0.62, fill=col255('flex'), outline=None)
    M.rect(d, 0.4, 0.38, 4.2, 0.42, fill=col255('pad'), outline=None)
    M.rect(d, -0.6, 2.0, 2.0, 2.6, fill=col255('j1'))
    T(d, M(-2.5, -1.5), 'J1 contacts are at the bottom (board side):\nthe tail\'s gold fingers face them', font=fonts()['dim'], fill=INK, anchor='la')
    T(d, M(-2.5, 1.2), 'tail', font=fonts()['dim'], fill=ACC, anchor='lb')
    d.text(M(2.2, 2.9), 'latch down', font=fonts()['dim'], fill=SUB, anchor='lb')


def dg_snap(C, box):
    d = C.d
    frame_box(d, box, 'Snap catch (section)')
    x, y, w, h = box
    M = MM(box, 30, (w * 0.42, h * 0.78))
    M.rect(d, -4, -2.0, 0.0, 4.0, fill=col255('base'))
    M.rect(d, -0.30, 1.6, 0.0, 2.8, fill=(252, 251, 248), outline=INK, width=1)
    M.rect(d, 0.1, -0.5, 1.1, 6.0, fill=col255('lid'))
    d.polygon([M(0.1, 1.75), M(-0.25, 1.75), M(-0.25, 2.65), M(0.1, 2.65)], fill=col255('lid'), outline=INK)
    T(d, M(1.4, 2.2), 'rib on the lid\nclicks into the\ngroove in the base', font=fonts()['dim'], fill=INK, anchor='lm')
    d.text(M(-4, -2.4), 'base wall', font=fonts()['dim'], fill=SUB, anchor='la')


LOCK_STEPS = ['UNDER the friction bar', 'UP through the slot', 'OVER the bar', 'ROUND and back UNDER:\ntip at the slot']


def _lock_geo(stage):
    """slide-frame strand for the lock sequence (mm); stage 1..4 shows how far the end has gone."""
    tip = (4.3, -2.75)
    sw = 41.0
    tp = (tip[0] + 0.75 * math.cos(math.radians(270 - sw)), tip[1] + 0.75 * math.sin(math.radians(270 - sw)))
    far = (tp[0] + 5.0 * math.cos(math.radians(-sw)), tp[1] + 5.0 * math.sin(math.radians(-sw)))
    p1 = [far, tp, (3.6, -2.4)]
    p2 = arcp(4.3, -2.75, 0.75, 270 - sw - 360, -164.4)[1:] + [(3.05, -1.05)] + arcp(4.3, -0.7, 1.3, 195.6, 180)[1:] + [(3.0, 0.7)]
    p3 = arcp(4.3, 0.7, 1.3, 180, 90)[1:] + [(5.5, 2.0)]
    p4 = arcp(5.5, 0.7, 1.3, 90, 0)[1:] + [(6.8, -0.7)] + arcp(5.5, -0.7, 1.3, 0, -90)[1:] + [(4.3, -2.0)]
    segs = [p1, p2, p3, p4]
    if stage == 1:
        return [far, tp, (3.2, -2.3)], []
    inc = [far, tp] + p2 + (p3 if stage >= 3 else [])
    tail = p4 if stage >= 4 else []
    return inc, tail


def _lock_panel(d, box, stage, label):
    M = MM(box, 18, (box[2] * 0.22, box[3] * 0.50))
    dark = (70, 70, 74)
    r_o, r_i = 1.9 * M.s, 0.9 * M.s
    c = M(0, 0)
    d.pieslice([c[0] - r_o, c[1] - r_o, c[0] + r_o, c[1] + r_o], start=-(89 - 40), end=360 - (89 + 40), fill=col255('slide'))
    d.ellipse([c[0] - r_i, c[1] - r_i, c[0] + r_i, c[1] + r_i], fill=(252, 251, 248))
    d.ellipse([c[0] - 0.65 * M.s, c[1] - 0.8 * M.s, c[0] + 0.65 * M.s, c[1] + 0.8 * M.s], fill=col255('base'))
    M.rect(d, 3.8, -1.2, 6.0, 1.2, fill=col255('slide'), outline=INK, r=0.5)
    inc, tail = _lock_geo(stage)
    if tail:
        strand(d, M, tail, (120, 138, 180), 1.1)
    strand(d, M, inc, col255('web'), 1.1)
    end = (tail or inc)[-1]
    prev = (tail or inc)[-2]
    arrow(d, M(*prev), M(end[0] + (end[0] - prev[0]) * 2.0, end[1] + (end[1] - prev[1]) * 2.0), w=3, head=12)
    text_block(d, (box[0] + 10, box[1] + 8), '%d  %s' % (stage, label), font=fonts()['sub'])
    if stage == 4:
        arrow(d, M(5.8, -4.6), M(4.5, -3.3), w=3, head=11)
        d.text(M(6.0, -4.9), 'pinched', font=fonts()['dim'], fill=ACC, anchor='la')
        arrow(d, M(8.6, -6.4), M(10.2, -7.8), col=SUB, w=3, head=11)
        d.text(M(10.4, -6.6), 'load', font=fonts()['dim'], fill=SUB, anchor='la')


def dg_lock4(C, box):
    d = C.d
    x, y, w, h = box
    pw = w / 4
    for i in range(4):
        b = (x + i * pw + 4, y, pw - 8, h)
        frame_box(d, b)
        _lock_panel(d, b, i + 1, LOCK_STEPS[i])
    F = fonts()
    lx = x + 10
    d.text((lx, y + h + 14), 'side section of slide A, hinge (module) left, friction bar right, band toward the bottom right',
           font=F['small'], fill=SUB, anchor='la')


def dg_length(C, box):
    d = C.d
    F = fonts()
    x, y, w, h = box
    steps = [('Untuck', 'slide the tip out from\nunder the friction bar'), ('Pull or feed', 'pull the tail to tighten,\npush it back to loosen'),
             ('Trim', 'cut so the tucked tip will\njust reach the slot'), ('Seal', 'quick pass of a lighter\nflame over the cut end'),
             ('Tuck', 'back under the bar,\ntip to the slot')]
    pw = (w - 20) / 5
    for i, (t, s) in enumerate(steps):
        b = (x + 10 + i * pw, y, pw - 12, 270)
        frame_box(d, b)
        M = MM(b, 12, (b[2] * 0.30, 120))
        M.rect(d, 3.8, -1.2, 6.0, 1.2, fill=col255('slide'), outline=INK, r=0.5)
        c = M(0, 0)
        rr = 1.9 * M.s
        d.ellipse([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr], fill=col255('slide'))
        inc, tail = _lock_geo(4 if i in (2, 4) else 3)
        if i == 4:
            strand(d, M, tail, (120, 138, 180), 1.1)
        strand(d, M, inc, col255('web'), 1.1)
        if i == 0:
            arrow(d, M(5.0, 2.0), M(9.5, 2.0), w=3, head=10)
        if i == 1:
            arrow(d, M(6.0, 2.0), M(10.5, 2.0), w=3, head=10)
            arrow(d, M(6.5, -6.0), M(4.0, -3.4), col=SUB, w=2, head=9)
        if i == 2:
            d.line([M(8.0, 3.2), M(8.0, -0.8)], fill=ACC, width=3)
            d.text(M(8.2, 3.2), 'cut', font=F['dim'], fill=ACC, anchor='la')
        if i == 3:
            d.polygon([M(7.4, 3.6), M(6.9, 2.6), M(7.9, 2.6)], fill=ACC)
        text_block(d, (b[0] + b[2] / 2, b[1] + 8), '%d  %s' % (i + 1, t), anchor='ma', font=F['sub'])
        text_block(d, (b[0] + b[2] / 2, b[1] + 214), s, anchor='ma', font=F['small'], halo=False)
    # table
    ty = y + 290
    frame_box(d, (x + 10, ty, w - 20, h - 290), 'Lengths (fit.py on the CAD wrist)')
    rows = [('Wrist', '145 mm', '160 mm', '180 mm'), ('Finished piece, tip to tip', '155 mm', '169 mm', '188 mm'),
            ('Webbing between the slides (through the pods)', '127 mm', '141 mm', '159 mm'),
            ('Cut (one length for all wrists)', '220 mm', '', '')]
    cx = [x + 30, x + 640, x + 820, x + 1000]
    for r, row in enumerate(rows):
        yy = ty + 50 + r * 34
        for c, txt in enumerate(row):
            d.text((cx[c], yy), txt, font=F['lab'] if r == 0 or c == 0 else F['sub'], fill=INK, anchor='la')


def dg_clip_tip(C, box):
    d = C.d
    frame_box(d, box, 'Pin height')
    x, y, w, h = box
    M = MM(box, 22, (w * 0.25, h * 0.80))
    M.rect(d, -2.5, -6, 6.5, 0.0, fill=col255('clip'))
    for u in (0.5, 3.5):
        d.line([M(u, -7.5), M(u, 3.0)], fill=col255('pin'), width=max(3, int(0.68 * M.s)))
    dim(d, M(5.0, 0.0), M(5.0, 3.0), '3.0 mm above\nthe top face')
    d.text(M(-2.5, -7.0), 'CA drop underneath', font=fonts()['dim'], fill=ACC, anchor='la')


def dg_window(C, box):
    d = C.d
    frame_box(d, box, 'Pins on the charge pads (section)')
    x, y, w, h = box
    M = MM(box, 24, (w * 0.18, h * 0.60))
    M.rect(d, -2, 1.7, 9, 2.7, fill=col255('board'))
    for u, lab in ((1.0, 'GND'), (4.0, 'VCHG +')):
        M.rect(d, u - 0.8, 1.65, u + 0.8, 1.7, fill=col255('pad'))
        d.text(M(u, 3.1), lab, font=fonts()['dim'], fill=INK, anchor='mb')
    M.rect(d, -2, -1.4, -0.2, 1.1, fill=col255('base'))
    M.rect(d, 5.8, -1.4, 9, 1.1, fill=col255('base'))
    M.rect(d, -1, -6, 6.6, -1.6, fill=col255('clip'))
    for u in (1.0, 4.0):
        d.line([M(u, -5.5), M(u, 1.65)], fill=col255('pin'), width=max(3, int(0.68 * M.s)))
    T(d, M(9.2, 0.0), 'window\nin the\nbase', font=fonts()['dim'], fill=SUB, anchor='lm')


# ---------------------------------------------------------------- figure specs (layout, labels)
L, Rr = 'L', 'R'
B = (0, 14, 'mt')


def _post_text(xy, text):
    return lambda C: text_block(C.d, (xy[0], TITLE_H + xy[1]), text, font=fonts()['sub'])


SPECS = {
    '0.1': dict(canvas=(W0, 1060), panels=[('main', (0, 0, W0, 860))],
                labels=[('main', 'bond_jig', 'Bonding jig  x1\nFDM, tool (stage 1)', B),
                        ('main', 'base_jig', 'Base jig  x1\nFDM, tool (stage 2)', B),
                        ('main', 'spacer', 'Cell spacer\n401120 cell only', B),
                        ('main', 'flex', 'Electrode flex  x1\nbought, pads up here', B),
                        ('main', 'board', 'Main board  x1\nbought, assembled', B),
                        ('main', 'base', 'Module base\nwith bars A, B', B),
                        ('main', 'lid', 'Lid', B),
                        ('main', 'cell', 'LiPo cell\n401223', B),
                        ('main', 'pods', 'Pods  x6\nprinted, TPU', B),
                        ('main', 'cap', 'Button\ncap', B),
                        ('main', 'dots', 'Foam dots  x25\n6 x 2 mm', B),
                        ('main', 'conn', 'Magnetic 2-pin\nconnector pair', B),
                        ('main', 'usb', 'USB-A lead', B),
                        ('main', 'strap', 'Hook-and-loop strap, 20 mm, size L (302 mm)', B),
                        ('main', 'hook', 'Hook tab', B),
                        ('main', 'ringe', 'Steel ring\n(cut off)', B)],
                diagrams=[(lambda C, b: dg_legend(C, b), (20, 860, W0 - 40, 190))]),
    '0.2': dict(canvas=(W0, 900), panels=[('main', (0, 0, 980, 900))],
                labels=[('main', 'lid', 'Module (lid on top)', L), ('main', 'j1end', 'J1 end: toward the hand', (40, 150, 'lt')),
                        ('main', 'antenna', 'Antenna side\n(little finger)', L), ('main', 'barA', 'Bar A: the strap end\nis locked round it', L),
                        ('main', 'button', 'Button side (thumb)', Rr), ('main', 'barB', 'Bar B: the hook end goes\nthrough and folds back', Rr),
                        ('main', 'gap', 'The gap (pods 1 and 8)', Rr)],
                nums=[('main', 'pod%d' % k, k) for k in range(1, 9)],
                diagrams=[(dg_wrist_r2, (990, 20, 390, 860))],
                note='Seen from the hand end. Pods 3 and 4 are under the module.'),
    '0.3': dict(canvas=(W0, 900), panels=[('main', (200, 0, 1000, 900))],
                labels=[('main', 'cap', 'Button cap', L), ('main', 'lid', 'Lid', L), ('main', 'cell', 'Cell', L),
                        ('main', 'board', 'Main board', L), ('main', 'base', 'Module base', L), ('main', 'tail', 'Flex tail', L),
                        ('main', 'pod', 'Pod  x6', Rr), ('main', 'foam', 'Foam dots  x25', Rr),
                        ('main', 'flex', 'Electrode flex', Rr), ('main', 'web', 'Strap', Rr), ('main', 'hook', 'Hook tab', Rr)],
                travel=[('main', 't_' + k) for k in ('lid', 'cap', 'cell', 'board', 'base', 'pod')]),
    '0.4': dict(canvas=(W0, 820), panels=[('main', (0, 0, W0, 820))],
                labels=[('main', 'web', 'Strap in the open channel:\nit slides freely', L), ('main', 'flex', 'Flex (0.11 mm)', L),
                        ('main', 'skin', 'Skin', L), ('main', 'pod', 'TPU pod: two lips\nhold the strap in', Rr),
                        ('main', 'foam', 'Foam dot: the spring', Rr), ('main', 'pad', 'Gold pad on the skin', Rr),
                        ('main', 'link', 'Flex link to the next pod:\nsets the 18 mm spacing', Rr)],
                curve=[('main', 'slide')],
                note='Section through the middle pad of one pod, worn. The gold pad is drawn thicker than it is.'),
    '1.1': dict(canvas=(W0, 860), panels=[('main', (0, 0, 600, 860))],
                labels=[('main', 'tp0', 'TP1  +3V3', (90, 70, 'lt')), ('main', 'tp4', 'TP5  GND', (-60, -110, 'rb')),
                        ('main', 'board', 'Bare board,\nbottom side up', (60, 90, 'lt')), ('main', 'j1', 'J1 edge', (0, 60, 'mt')),
                        ('main', 'wires', '30 AWG wires,\n10 cm', (-30, 90, 'rt'))],
                diagrams=[(dg_wiring_r2, (610, 20, 780, 820))],
                note='TP4 (NRST) is not needed. Pico 2 pin numbers are the physical pins.'),
    '2.1': dict(canvas=(W0, 860), panels=[('main', (0, 0, 980, 860))],
                labels=[('main', 'j2p', 'J2 +  (VBAT): red lead', (-60, -130, 'rb')), ('main', 'j2m', 'J2 -  (GND): black lead', (60, -130, 'lb')),
                        ('main', 'cell', 'Cell', L), ('main', 'kap', 'Kapton over both joints', Rr),
                        ('main', 'tp', 'TP1-TP5 (step 1)', L), ('main', 'j3v', 'J3 charge pads (2.2)', L), ('main', 'edge', 'Button-side edge', Rr)],
                diagrams=[(dg_joint, (990, 20, 390, 330))],
                note='Board bottom side up. Do one lead at a time, so they never touch.'),
    '2.2': dict(canvas=(W0, 860), panels=[('main', (0, 0, 980, 860))],
                labels=[('main', 'j3v', 'J3 pad 1 (5 V): red', (-60, 80, 'rt')), ('main', 'j3g', 'J3 pad 2 (GND): black', (60, 80, 'lt')),
                        ('main', 'conn', 'Female connector: red to the pin\nthat meets the cable\'s red', (0, -90, 'mb')),
                        ('main', 'wires', 'Flat along the button-side edge,\nKapton every 10 mm', Rr),
                        ('main', 'j2', 'J2 (cell leads, 2.1)', (-60, -90, 'rb'))],
                note='Board bottom side up; the cell is left out of the picture. 50 mm of 30 AWG per wire.'),
    '3.1': dict(canvas=(W0, 820), panels=[('main', (0, 0, W0, 820))],
                labels=[('main', 'saddle', 'Saddle for the pod 3/4 part\n(the base goes on in step 4)', (-60, 150, 'mt')),
                        ('main', 'pin', '16 pins for the flex holes', (-20, 190, 'mt')),
                        ('main', 'gap', 'Fence gap for the tail', (-120, -170, 'mb')), ('main', 'fence', 'Fence', (40, -150, 'lb')),
                        ('main', 'ledge', 'Ledges: the pod stops here', (-60, -230, 'mb'))],
                nums=[('main', 'n%d' % k, k) for k in (1, 2, 5, 6, 7, 8)]),
    '3.2': dict(canvas=(W0, 820), panels=[('main', (0, 0, W0, 820))],
                labels=[('main', 'flex', 'Flex, gold pads DOWN', L), ('main', 'short', 'Pods 1-2: the short side', L),
                        ('main', 'tail', 'Tail fingers face UP', (60, -120, 'lb')), ('main', 'long', 'Pods 5-8', Rr)],
                travel=[('main', 't%d' % i) for i in range(3)],
                insets=[dict(shot='zoom', at=(1200, 600), r=150, anchor=('main', 'pinhole'), caption='each hole over its pin')]),
    '3.3': dict(canvas=(W0, 860), panels=[('main', (0, 0, 980, 860))],
                labels=[('main', 'pod', 'Pod, pocket side up', L), ('main', 'd1', 'Foam dot  x3', Rr), ('main', 'sleeve', 'Strap channel', L)],
                travel=[('main', 't%d' % i) for i in range(3)],
                diagrams=[(dg_dot_pocket, (990, 20, 390, 330))],
                insets=[dict(shot='zoom', at=(1185, 600), r=150, caption='pressed in, flush round the edge')]),
    '3.4': dict(canvas=(W0, 820), panels=[('main', (0, 0, W0, 820))],
                labels=[('main', 'pod5', 'Pod, pocket side DOWN', (60, -150, 'lb')),
                        ('main', 'sleeve', 'Channel runs along the strip\n(around the wrist)', Rr), ('main', 'pod1', 'Pods 1, 2 already in', L)],
                nums=[('main', 'n%d' % k, k) for k in (1, 2, 5, 6, 7, 8)],
                travel=[('main', 't0'), ('main', 't1')],
                diagrams=[(dg_pod_ledge, (1010, 470, 370, 310))],
                note='Order: 1, 2, 5, 6, 7, 8. Press straight down until the pod stops on its ledges; hold 10 s.'),
    '3.5': dict(canvas=(W0, 760), panels=[('main', (0, 0, W0, 760))],
                labels=[('main', 'mid', 'Pod 3/4 part: the base\ngoes on in step 4', (0, 110, 'mt')), ('main', 'tail', 'Tail', (-80, -80, 'rb')),
                        ('main', 'spine', 'Flex links between the pods', L)],
                nums=[('main', 'p%d' % k, k) for k in (1, 2, 5, 6, 7, 8)],
                note='Lift it off the pins after 10 minutes. The gold pads are underneath.'),
    '4.1': dict(canvas=(W0, 860), panels=[('main', (0, 0, 1100, 860))],
                labels=[('main', 'base', 'Base, upside down', L), ('main', 'dots', '6 dots: the pad pockets', L),
                        ('main', 'rootdot', '+ the root dot by the tail slot\n(it holds the flex root)', Rr),
                        ('main', 'slot', 'Tail slot', Rr)],
                note='Peel the top liner of each dot after pressing it in.'),
    '4.2': dict(canvas=(W0, 860), panels=[('main', (0, 0, 1100, 860))],
                labels=[('main', 'base', 'Base, right way up,\ntail through its floor slot', Rr), ('main', 'saddle', 'Saddle', L),
                        ('main', 'pins', '4 pins in the\nflex holes', Rr), ('main', 'fence', 'Fence', L),
                        ('main', 'pedestal', 'Pedestal: the free pods\nhang down its sides', L),
                        ('main', 'flex', 'Pod 3/4 part,\ngold pads down', L), ('main', 'bar', 'Bars overhang\nthe ends', Rr)],
                travel=[('main', 't0'), ('main', 't1')],
                note='The free pods are left out of the picture. Press until the base stops; hold 10 s, wait 10 minutes.'),
    '5.1': dict(canvas=(W0, 760), panels=[('a', (0, 0, 520, 700), 'a  latch up, tail in'), ('b', (520, 0, 520, 700), 'b  latch down')],
                labels=[('a', 'latch', 'Latch flipped up', L), ('a', 'fingers', 'Gold fingers\ntoward the board', L),
                        ('a', 'down', 'DOWN mark', L), ('b', 'latch', 'Latch pressed down', Rr)],
                travel=[('a', 't0')],
                diagrams=[(dg_j1, (1050, 20, 340, 330))],
                note='Board upright above the base, J1 at the bottom. Push the tail in square until it stops.'),
    '5.2': dict(canvas=(W0, 700), panels=[('a', (0, 0, 460, 640), 'a  upright'), ('b', (470, 0, 460, 640), 'b  fold down'),
                                          ('c', (940, 0, 460, 640), 'c  seated')],
                labels=[('a', 'j1', 'J1, tail in', (60, -60, 'lb')), ('a', 'base', 'Base (see-through)', (20, 90, 'lt')),
                        ('c', 'wall', 'Tail U along the end wall', (60, -120, 'lb'))],
                curve=[('b', 'fold')]),
    '5.3': dict(canvas=(W0, 860), panels=[('main', (0, 0, W0, 860))],
                labels=[('main', 'conn', 'Female connector in its bay:\nface flush, glued by its flange', Rr),
                        ('main', 'wires', 'J3 wires in the channel\nunder the board edge', Rr), ('main', 'j3', 'J3', Rr),
                        ('main', 'leads', 'Cell leads past the board\nedge, level with J2', Rr),
                        ('main', 'cellend', 'Cell lead end\ntoward J1', L), ('main', 'barA', 'Bar A', L), ('main', 'barB', 'Bar B', Rr)],
                note='Top view, lid off; the board and cell are drawn see-through.'),
    '6.1': dict(canvas=(W0, 860), panels=[('main', (0, 0, 1000, 860))],
                labels=[('main', 'cap', 'Button cap in the lid,\ndomed stem on SW1', L), ('main', 'lid', 'Lid', L), ('main', 'led', 'LED hole over D1', Rr),
                        ('main', 'snap1', 'Snap catch', Rr), ('main', 'snap2', 'Snap catch', L),
                        ('main', 'snap3', 'Snap catch', L), ('main', 'bay', 'Connector bay', Rr)],
                travel=[('main', 't0'), ('main', 't1'), ('main', 't2')],
                diagrams=[(dg_snap, (1010, 20, 370, 330))],
                note='Press the lid down at all four corners until each catch clicks.'),
    '7.2': dict(canvas=(W0, 470), diagrams=[(dg_cut, (0, 10, W0, 450))]),
    '7.3': dict(canvas=(W0, 760), panels=[('3d', (930, 10, 460, 440), 'finished lock', True)],
                labels=[('3d', 'bar', 'Bar A', (-40, -80, 'rb')), ('3d', 'lock', 'tucked end', (40, 90, 'lt'))],
                diagrams=[(dg_lock, (10, 10, 900, 730))],
                post=[_post_text((940, 480), 'Why it holds: the loaded band bends\nround the tucked end at the bar\'s\n'
                                             'lower inner corner and pinches it\nagainst the bar. The harder it pulls,\n'
                                             'the harder it pinches. It can only\nslip, never break.')]),
    '7.4': dict(canvas=(W0, 800), panels=[('main', (0, 0, 820, 760))],
                labels=[('main', 'pod', 'Pod (on the flex)', (60, 120, 'lt')), ('main', 'lip', '1  this edge under\n    one lip first', (-40, -150, 'rb')),
                        ('main', 'lip2', '2  push this edge down\n    past the other lip', (-10, -230, 'rb')),
                        ('main', 'web', 'Strap, loop panel out', (-30, -130, 'mb')), ('main', 'floor', 'Channel floor', (-60, 120, 'rt'))],
                travel=[('main', 't0')],
                diagrams=[(dg_channel, (830, 20, 550, 420))],
                post=[_post_text((850, 560), 'Order: pods 5, 6, 7, 8, across the gap,\nthen 1 and 2.\n\n'
                                             'Press one edge of the strap under one lip,\nthen push the other edge down past the\n'
                                             'other lip until it clicks in.')]),
    '7.5': dict(canvas=(W0, 760), panels=[('3d', (930, 10, 460, 440), 'finished', True)],
                labels=[('3d', 'bar', 'Bar B', (40, -80, 'lb')), ('3d', 'tail', 'Hook tab on the panel', (-40, 90, 'rt'))],
                diagrams=[(dg_fold, (10, 10, 900, 730))],
                post=[_post_text((940, 480), 'Up through slot B from under the\nmodule, over bar B, fold back and\n'
                                             'press the hook tab onto the loop panel.\nTo take it off, peel the tab and pull\n'
                                             'the end out of slot B.')]),
    '8.1': dict(canvas=(W0, 820), panels=[('main', (0, 0, W0, 820))],
                labels=[('main', 'module', 'Module on the back of the forearm', L), ('main', 'cap', 'Button toward the thumb', Rr),
                        ('main', 'crease', '~25 mm above the wrist crease', L), ('main', 'web', 'A finger fits under the strap', Rr),
                        ('main', 'bar', 'Bar B: pull the tail\nhere to tighten', Rr)],
                note='Snug, not tight: every pod touches the skin.'),
    '9.1': dict(canvas=(W0, 460), diagrams=[(dg_cable, (0, 10, W0, 440))]),
    '9.2': dict(canvas=(W0, 860), panels=[('main', (0, 0, 1000, 860))],
                labels=[('main', 'bay', 'Connector in the\nelbow end', L), ('main', 'head', 'Cable head: the magnets\npull it on, one way round', Rr),
                        ('main', 'lid', 'Lid', L)],
                travel=[('main', 't0')],
                note='Band off the wrist. The LED stays solid while it charges.'),
    '10.1': dict(canvas=(W0, 720), panels=[('a', (0, 0, 690, 660), 'a  open the lid'), ('b', (700, 0, 690, 660), 'b  board out, wires on')],
                 labels=[('a', 'notch', 'Pry notch above\nthe connector', (-40, 90, 'rt')), ('a', 'conn', 'Connector', (60, 60, 'lt')),
                         ('b', 'board', 'Board folded out\n(reverse 5.2)', (-30, -100, 'rb')),
                         ('b', 'tp', 'TP1-TP5: re-attach\nthe wires', (60, 40, 'lt'))],
                 curve=[('a', 'lever')],
                 note='Re-flash with SWDIO, SWDCLK and GND only: the cell powers the board, so never connect TP1.'),
}
