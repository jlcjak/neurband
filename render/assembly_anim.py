#!/usr/bin/env python3
"""neurband rev C assembly animation and build-guide stills (Blender 5.2 Cycles / OptiX).

  python3 render/assembly_anim.py                  # export inputs, render 690 frames on GPUs 0,1, encode
  python3 render/assembly_anim.py --no-export      # reuse render/build/*.glb
  python3 render/assembly_anim.py --quick          # half size, 16 spp preview (render/build/assembly_quick/)
  python3 render/assembly_anim.py --stills         # build-guide images -> docs/build/img/*.jpg
  python3 render/assembly_anim.py --encode-only    # captions + MP4 + GIF from existing frames

Outputs: docs/media/assembly.mp4 (1920 x 1080, H.264) and docs/media/assembly.gif (960 px wide).
Frames go to render/build/assembly/ (git-ignored), one Blender process per GPU (even / odd frames).
Captions are drawn on the frames afterwards (PIL, Noto Sans), so the 3D frames stay clean.

The scene is the band as fitted on the 160 mm wrist (render/build/band_assembly.glb, from
mech/rev_c/band_assembly.step), the real KiCad board (render/build/main_board.glb) placed with
module.k2m, and two things modelled here: the flex tail (a ribbon whose free length is kept
constant while the board folds down on it, the 'book' fold of docs/build/assembly.md) and the
two 30 AWG battery leads round the board's distal +X corner through the lead gate.
Blender side: blender -b --python render/assembly_anim.py -- --frames 0:690:2 [--quick] [--samples N]
"""
import os, sys, math, time, json, argparse, subprocess, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build')
LOGS = os.path.join(BUILD, 'logs')
BLENDER = '/usr/bin/blender'
FREECAD = '/usr/bin/freecad'
MEDIA = os.path.join(ROOT, 'docs', 'media')
IMG = os.path.join(ROOT, 'docs', 'build', 'img')
FONT_DIR = '/usr/share/fonts/noto'

FPS = 30
DUR = 24.0
NF = int(round(DUR * FPS))
RES = (1920, 1080)

# ---------------------------------------------------------------- timeline (seconds)
TL = dict(flex=(0.0, 1.0), foam=(0.9, 2.8), pods=(2.9, 4.9), base=(5.1, 6.5),
          board_in=(6.7, 7.9), board_swing=(8.5, 10.2), cell=(10.8, 12.1), lpcap=(12.2, 13.4),
          lid=(13.5, 14.9), loop_a=(15.1, 16.0), strap=(16.3, 19.6), loop_b=(19.7, 20.5), fold=(20.4, 21.4))
CAPTIONS = [
    (0.2, 2.85, '1', 'Electrode flex, 24 double-sided foam discs behind the pads'),
    (2.95, 5.0, '2', 'Six TPU pods: locating pins through the flex holes'),
    (5.1, 6.6, '3', 'Module base onto the two middle pods, magnets glued in'),
    (6.7, 10.6, '4', 'Board: tail up into J1, latch closed, fold the board down'),
    (10.7, 12.1, '5', 'Cell taped on, its leads spliced to the board leads'),
    (12.2, 13.4, '6', 'Light pipe and button cap'),
    (13.5, 15.0, '7', 'Lid snaps on'),
    (15.1, 16.2, '8', 'Webbing end sewn round the ulnar loop, loop onto its hidden bar'),
    (16.3, 19.6, '9', 'Webbing through the six pod sleeves'),
    (19.7, 21.5, '10', 'Radial loop on, end through it, hook tab folded back'),
    (21.7, 24.0, '', 'Ready to wear'),
]
TITLE = 'neurband rev C  ·  assembly'
# camera keys: (t, target, azimuth from -Y toward +X, elevation, distance m); target R ring, M module, H hinge
CAM = [(0.0, 'R', 26, 24, 0.335), (2.8, 'R', 33, 25, 0.325), (4.8, 'R', 40, 26, 0.315),
       (6.3, 'M', 38, 30, 0.215), (7.5, 'H', 56, 18, 0.205), (8.8, 'H', 60, 20, 0.200),
       (10.3, 'M', 44, 34, 0.185), (12.0, 'M', 36, 40, 0.180), (14.0, 'M', 30, 32, 0.205),
       (15.3, 'R', -25, 26, 0.33), (16.4, 'R', -38, 24, 0.335), (19.4, 'R', 60, 22, 0.33),
       (20.8, 'R', 70, 20, 0.32), (22.4, 'R', 50, 20, 0.31), (24.0, 'R', 40, 19, 0.31)]

# build-guide stills: name -> (t, target, az, el, dist, lens) ; see docs/build/assembly.md
STILLS = {
    'pods_bond': (3.75, 'P6', 66, 24, 0.15, 85),
    'base_on': (6.3, 'M', 30, 34, 0.17, 85),
    'board_upright': (8.2, 'H', 62, 16, 0.19, 85),
    'board_fold': (9.35, 'H', 58, 22, 0.19, 85),
    'leads': (10.6, 'L', 52, 48, 0.12, 85),
    'j1_marks': (10.6, 'J', 8, 68, 0.085, 85),
    'cell_in': (12.15, 'M', 40, 46, 0.16, 85),
    'lid_on': (14.25, 'M', 34, 30, 0.19, 85),
    'webbing': (18.6, 'R', 62, 24, 0.32, 85),
    'loops': (20.35, 'B', 100, 24, 0.17, 85),
    'done': (24.0, 'R', 40, 20, 0.30, 85),
}


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


# ================================================================ Blender side
def blender_main(argv):
    import bpy, bmesh
    import numpy as np
    from mathutils import Vector, Matrix
    sys.path.insert(0, HERE)
    import nb_blender as NB

    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', default='')
    ap.add_argument('--stills', default='')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--samples', type=int, default=0)
    ap.add_argument('--out', default=os.path.join(BUILD, 'assembly'))
    ap.add_argument('--save-blend', action='store_true')
    ap.add_argument('--times', default='', help='debug: render these times (s) to <out>/t_<t>.png')
    a = ap.parse_args(argv)

    NB.reset()
    NB.MATS.clear()
    still_mode = bool(a.stills)
    samples = a.samples or (16 if a.quick else (160 if still_mode else 40))
    w, h = (1600, 1000) if still_mode else RES
    sc = NB.setup_render(w, h, samples, a.quick)
    sc.render.resolution_percentage = 50 if a.quick else 100
    sc.render.use_persistent_data = True
    sc.cycles.adaptive_threshold = 0.03 if not still_mode else 0.01
    sc.cycles.max_bounces = 8
    sc.cycles.transparent_max_bounces = 24

    # ------------------------------------------------------------ load
    band = NB.load_band()
    mod = NB.load_module()
    bobj = NB.board_into(mod)                       # real KiCad board, module frame (m)
    T = NB.module_to_band(mod, band)
    for o in list(mod.values()):
        bpy.data.objects.remove(o)
    for o in bobj.values():
        o.matrix_world = T @ o.matrix_world
    Ti = T.inverted()

    def to_mod(p):
        return Ti @ Vector(p)

    groups = {}
    for o in band.values():
        groups.setdefault(o['kind'], []).append(o)
    # drop the STEP board copy (the KiCad GLB board is used) and the CAD tail (a ribbon is modelled)
    for o in groups.pop('main_board', []) + groups.pop('board_parts', []):
        bpy.data.objects.remove(o)
    flex = []
    for o in groups.get('flex', []):
        mn, mx = NB.bbox([o])
        c = to_mod((mn + mx) / 2) * 1000
        if abs(c.x) < 1 and c.y < -11 and c.z > 0.5:
            bpy.data.objects.remove(o)               # the installed U-turn tail
        else:
            flex.append(o)

    # split the strap compound into its pieces (band, wraps, sewn end, fold-back)
    # the strap compound is one mesh in band_assembly.glb; strap_pieces.glb has its five solids
    # (band, fold-back, sewn end, two wraps; exported by this script under FreeCAD)
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

    # float the assembled band 12 mm above the floor
    allobj = [o for o in bpy.data.objects if o.type in ('MESH',)]
    bpy.context.view_layer.update()
    mn, mx = NB.bbox(allobj)
    G = Matrix.Translation((0, 0, 0.012 - mn[2]))
    for o in allobj:
        o.matrix_world = G @ o.matrix_world
    T = G @ T
    Ti = T.inverted()
    z_axis = 0.012 - mn[2]                           # wrist / ring axis (x = 0, z = z_axis)
    bpy.context.view_layer.update()

    def centre(objs):
        a_, b_ = NB.bbox(objs)
        return Vector(((a_ + b_) / 2).tolist())

    def radial(o):
        c = centre([o])
        v = Vector((c.x, 0, c.z - z_axis))
        return v.normalized()

    up = (T.to_3x3() @ Vector((0, 0, 1))).normalized()   # module +Z in the band frame
    ring_c = Vector((0, 0.025, z_axis))

    # ------------------------------------------------------------ added parts
    def mat_wire(name, col):
        return NB.principled(name, col, 0.35, coat_weight=0.3, coat_roughness=0.2)

    def lead(name, pts_mm, col):
        cu = bpy.data.curves.new(name, 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = 0.00026
        cu.bevel_resolution = 3
        cu.use_fill_caps = True
        sp = cu.splines.new('BEZIER')
        sp.bezier_points.add(len(pts_mm) - 1)
        for bp, p in zip(sp.bezier_points, pts_mm):
            bp.co = Vector(p) / 1000.0
            bp.handle_left_type = bp.handle_right_type = 'AUTO'
        ob = NB.link(bpy.data.objects.new(name, cu))
        cu.materials.append(mat_wire(name, col))
        ob.matrix_world = T.copy()
        return ob

    # 30 AWG leads from the bottom J2 pads (module frame, mm): under the board in the J2 relief, round
    # the distal edge through the lead gate (x >= 10.5), up past SW1's outer end, over U5 to the cell
    gnd = [(12.9, -12.8, 1.45), (12.9, -14.3, 1.45), (12.95, -15.0, 1.6), (13.0, -15.45, 2.2), (13.05, -15.35, 2.95),
           (13.85, -14.95, 3.0), (14.15, -13.6, 3.0), (14.15, -11.6, 3.0), (13.7, -10.5, 3.25), (12.3, -10.0, 3.75),
           (10.2, -9.9, 3.8), (8.9, -9.8, 4.6), (8.25, -9.7, 5.7)]
    vbat = [(9.7, -13.3, 1.45), (10.7, -13.4, 1.45), (11.3, -14.1, 1.45), (11.4, -14.95, 1.55), (11.45, -15.5, 2.2),
            (11.5, -15.55, 3.0), (12.6, -15.75, 3.55), (13.9, -15.4, 3.55), (14.5, -14.4, 3.5), (14.55, -12.6, 3.5),
            (14.45, -11.0, 3.55), (13.9, -10.2, 3.8), (12.2, -9.62, 4.3), (10.0, -9.55, 4.35), (8.9, -9.5, 5.2),
            (8.2, -9.6, 6.4)]
    leads = [lead('lead_gnd', gnd, (0.02, 0.02, 0.022)), lead('lead_vbat', vbat, (0.55, 0.045, 0.035))]

    # flex tail ribbon (module frame, mm): constant free length while the board folds on it
    TAIL_W, TAIL_T, L_TOT, L_S = 10.5, 0.22, 8.24, 3.8
    P0F = Vector((0, -15.0, 3.2))                    # start of the straight part in the final pose

    def tail_path(s):
        th = math.pi / 2 * s
        yv = -16.0 + 0.5 * (1 - s)                   # vertical run (a little proximal while upright)
        r1 = -15.0 - yv
        Lv = L_TOT - L_S - th - math.pi / 2 * r1
        pts = []
        for k in range(9):                           # root bend: heading -Y -> +Z
            a = math.radians(270 - 90 * k / 8)
            pts.append((-15.0 + r1 * math.cos(a), -0.1 + r1 + r1 * math.sin(a)))
        z1 = -0.1 + r1 + Lv
        pts.append((yv, z1))
        n2 = 10
        for k in range(1, n2 + 1):                   # top bend: +Z turning toward +Y by th
            a = math.pi - th * k / n2
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
        # verts per section: 0 (-x,-n) 1 (-x,+n) 2 (+x,-n) 3 (+x,+n)
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
        return p0, phi

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

    pods = sorted(groups.get('pod_shells', []), key=lambda o: math.atan2(centre([o]).x, centre([o]).z - z_axis))
    foams = groups.get('foam', [])
    pads = groups.get('pads', [])
    base = groups.get('module_base', []) + groups.get('magnets', [])
    lid = groups.get('module_lid', [])
    lp_cap = groups.get('light_pipe', []) + groups.get('button_cap', [])
    cell = groups.get('lipo', [])
    loops = groups.get('strap_loop', [])
    loops_x = {lp.name: centre([lp]).x for lp in loops}
    board_grp = list(bobj.values()) + leads

    # strap pieces: angle along the strap from the ulnar loop (u = 0) to the radial loop (u = 1)
    def angles(o):
        V = NB.verts_np(o)
        return np.mod(-np.degrees(np.arctan2(V[:, 0], V[:, 2] - z_axis)), 360.0), V

    band_s, fold_s = straps.get('strap_band'), straps.get('strap_fold')
    wraps = [straps[k] for k in ('strap_wrap1', 'strap_wrap2') if k in straps]
    ends_a = [o for o in wraps if centre([o]).x < 0] + ([straps['strap_sewn']] if 'strap_sewn' in straps else [])
    ends_b = [o for o in wraps if centre([o]).x >= 0]
    info = [(o.name, *[round(float(x)) for x in (angles(o)[0].min(), angles(o)[0].max())]) for o in straps.values()]

    def add_rev(o, reverse=False):
        u, V = angles(o)
        r = (u - u.min()) / max(u.max() - u.min(), 1e-6)
        if reverse:
            r = 1 - r
        at = o.data.attributes.new('rev', 'FLOAT', 'POINT')
        at.data.foreach_set('value', r.astype(np.float32))

    NB.log('strap pieces', info)
    add_rev(band_s)
    if fold_s is not None:
        add_rev(fold_s, reverse=True)

    # ------------------------------------------------------------ fade / reveal shaders
    def add_fade(m, reveal=False):
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

    reveal_thr = {}
    for o, key in ((band_s, 'band'), (fold_s, 'fold')):
        if o is None:
            continue
        m = o.data.materials[0].copy()
        m.name = 'strap_reveal_' + key
        NB.setmat(o, m)
        reveal_thr[key] = add_fade(m, reveal=True)
    done = set(m.name for m in bpy.data.materials if m.name.startswith('strap_reveal'))
    for m in list(bpy.data.materials):
        if m.name not in done and m.node_tree is not None:
            add_fade(m)

    # ------------------------------------------------------------ studio
    sweep_mat = NB.mat_paper((0.52, 0.51, 0.49))
    NB.sweep(color=(0.52, 0.51, 0.49), depth=0.8, height=1.0, radius=0.3, origin=(0, 0.025, 0),
             yaw=math.radians(180 + 40), mat=sweep_mat)
    NB.studio(ring_c, key=5, fill=1.4, rim=5, top=2.0)
    cam = NB.camera(NB.orbit(ring_c, 30, 24, 0.33), ring_c, lens=85, fstop=16.0, focus=ring_c)
    sw = bpy.data.objects.get('sweep')

    mod_c = centre(groups.get('module_lid', []))
    targets = {'R': ring_c + Vector((0, 0, 0.004)), 'M': mod_c + Vector((0, 0, -0.002)),
               'H': T @ Vector((0.002, -0.010, 0.013)), 'L': T @ Vector((0.010, -0.011, 0.004)),
               'J': T @ Vector((0.0015, -0.0115, 0.0027)),
               'P6': centre(pods[3:5]) if len(pods) > 4 else ring_c,
               'B': centre([lp for lp in loops if centre([lp]).x > 0]) if loops else ring_c}

    def cam_at(t):
        ts = [k[0] for k in CAM]
        i = max(0, min(len(CAM) - 2, max(j for j in range(len(CAM)) if ts[j] <= t) if t >= ts[0] else 0))
        def val(j):
            j = max(0, min(len(CAM) - 1, j))
            _, tg, az, el, d = CAM[j]
            return np.array([*targets[tg], az, el, d])
        u = clamp01((t - ts[i]) / (ts[i + 1] - ts[i]))
        u = smooth(u) * 0.35 + u * 0.65
        p0, p1, p2, p3 = val(i - 1), val(i), val(i + 1), val(i + 2)
        v = 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
        return Vector([float(x) for x in v[:3]]), float(v[3]), float(v[4]), float(v[5])

    def set_cam(tgt, az, el, d, lens=85):
        loc = NB.orbit(tgt, az, el, d)
        NB.look_at(cam, tgt, loc)
        cam.data.lens = lens
        cam.data.dof.focus_distance = (Vector(tgt) - loc).length

    # ------------------------------------------------------------ per-frame state
    def place(o, M, alpha):
        o.matrix_world = M
        o.color = (1, 1, 1, alpha)
        o.hide_render = alpha <= 0.002

    RAD = {}
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE') and o.type == 'MESH':
            RAD[o.name] = radial(o)
    foams_sorted = sorted(foams, key=lambda o: -centre([o]).z)

    def fly(objs, t, t0, t1, dist, direction=None, stagger=0.0, fade=0.18):
        n = len(objs)
        for k, o in enumerate(objs):
            s0 = t0 + (stagger * k / max(n - 1, 1) if n > 1 else 0)
            s1 = s0 + (t1 - t0 - stagger)
            p = ph(t, s0, s1)
            dvec = direction if direction is not None else RAD[o.name]
            off = dvec * (dist * (1 - ease_out(p)))
            alpha = smooth(p / fade) if t >= s0 else 0.0
            place(o, Matrix.Translation(off) @ M0(o), alpha)

    def apply(t):
        p = ph(t, *TL['flex'])
        for o in flex + pads:
            place(o, Matrix.Translation(-up * 0.010 * (1 - ease_out(p))) @ M0(o), smooth(p / 0.6))
        fly(foams_sorted, t, *TL['foam'], 0.016, stagger=1.0)
        fly(pods, t, *TL['pods'], 0.024, stagger=1.0)
        fly(base, t, *TL['base'], 0.030, direction=up)
        # board: down onto the upright tail, then the book fold
        pin = ph(t, *TL['board_in'])
        s = ease_io(ph(t, *TL['board_swing']))
        dz = 26.0 * (1 - ease_out(pin))
        Hb = board_H(s, dz)
        a_b = smooth(pin / 0.4) if t >= TL['board_in'][0] else 0.0
        for o in board_grp:
            place(o, Hb @ M0(o), a_b)
        set_tail(s)
        tail.matrix_world = Matrix.Translation(-up * 0.010 * (1 - ease_out(p))) @ T
        tail.color = (1, 1, 1, smooth(p / 0.6))
        tail.hide_render = p <= 0.0
        fly(cell, t, *TL['cell'], 0.022, direction=up)
        fly(lp_cap, t, *TL['lpcap'], 0.018, direction=up, stagger=0.3)
        fly(lid, t, *TL['lid'], 0.030, direction=up)
        # webbing
        rs = ease_io(ph(t, *TL['strap']))
        if 'band' in reveal_thr:
            reveal_thr['band'].default_value = rs * 1.002
            place(band_s, M0(band_s), 1.0 if rs > 0 else 0.0)
        fly([lp for lp in loops if loops_x[lp.name] < 0] + ends_a, t, *TL['loop_a'], 0.014)
        fly([lp for lp in loops if loops_x[lp.name] >= 0] + ends_b, t, *TL['loop_b'], 0.014)
        if fold_s is not None:
            rf = ease_io(ph(t, *TL['fold']))
            reveal_thr['fold'].default_value = rf * 1.002
            place(fold_s, M0(fold_s), 1.0 if rf > 0 else 0.0)

    def render_to(path):
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        NB.vignette(path, 0.14)

    os.makedirs(a.out, exist_ok=True)
    if a.save_blend:
        apply(9.3)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BUILD, 'assembly_anim.blend'), compress=True)
    if a.frames:
        st, sp, sd = (int(x) for x in a.frames.split(':'))
        for i in range(st, sp, sd):
            p = os.path.join(a.out, 'f_%04d.png' % i)
            if os.path.exists(p) and os.path.getsize(p) > 0:
                continue
            t = i / FPS
            apply(t)
            tg, az, el, d = cam_at(t)
            set_cam(tg, az, el, d)
            t1 = time.time()
            render_to(p)
            NB.log('frame %d t=%.2f %.1f s' % (i, t, time.time() - t1))
    if a.times:
        for t in (float(x) for x in a.times.split(',')):
            apply(t)
            tg, az, el, d = cam_at(t)
            set_cam(tg, az, el, d)
            t1 = time.time()
            render_to(os.path.join(a.out, 't_%05.2f.png' % t))
            NB.log('time %.2f %.1f s' % (t, time.time() - t1))
    if a.stills:
        sc.render.image_settings.file_format = 'JPEG'
        sc.render.image_settings.quality = 90
        for name in a.stills.split(','):
            t, tg, az, el, d, lens = STILLS[name]
            apply(t)
            tgt = targets[tg]
            set_cam(tgt, az, el, d, lens)
            cam.data.dof.aperture_fstop = 14.0
            p = os.path.join(a.out, name + '.jpg')
            sc.render.filepath = p
            t1 = time.time()
            bpy.ops.render.render(write_still=True)
            NB.log('still', name, '%.1f s' % (time.time() - t1), p)


# ================================================================ driver side
def run(cmd, log, timeout=3600, env=None):
    t = time.time()
    with open(log, 'w') as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=timeout, env=env)
    print('  %-40s exit %d  %.0f s' % (os.path.basename(log), p.returncode, time.time() - t), flush=True)
    return p.returncode


def freecad_strap_pieces(step, dst):
    """(run under FreeCAD GUI offscreen) the webbing as five separate solids (band, wrap at the ulnar
    loop, sewn end, wrap at the radial loop, fold-back), rebuilt with mech/rev_c/fit.py for the 160 mm
    wrist exactly as assembly.py builds band_assembly.step (the STEP stores them fused)."""
    import FreeCAD, ImportGui
    sys.path.insert(0, os.path.join(ROOT, 'mech', 'rev_c'))
    sys.neurband_lib = True
    sys.neurband_fit_lib = True
    import fit as F
    res, items, L = F.build_band(160.0, lambda *x: None, with_wrist=False, cad=False)
    shape = dict((n, sh) for n, sh, c in items)['strap']
    names = ['strap_band', 'strap_wrap1', 'strap_sewn', 'strap_wrap2', 'strap_fold']
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
    sys.path.insert(0, HERE)
    import make_renders
    make_renders.export()
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', ASSEMBLY_STRAP=os.path.join(ROOT, 'mech/rev_c/band_assembly.step')
               + '=' + os.path.join(BUILD, 'strap_pieces.glb'))
    run([FREECAD, os.path.abspath(__file__)], os.path.join(LOGS, 'strap_pieces.log'), timeout=600, env=env)


def render_frames(gpus, quick, samples, out):
    os.makedirs(out, exist_ok=True)
    procs = []
    for k, g in enumerate(gpus):
        cmd = [BLENDER, '-b', '--python', os.path.abspath(__file__), '--', '--frames', '%d:%d:%d' % (k, NF, len(gpus)),
               '--out', out]
        if quick:
            cmd.append('--quick')
        if samples:
            cmd += ['--samples', str(samples)]
        log = open(os.path.join(LOGS, 'assembly_gpu%d.log' % g), 'w')
        procs.append(subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                      env=dict(os.environ, CUDA_VISIBLE_DEVICES=str(g))))
    t = time.time()
    for p in procs:
        p.wait(timeout=4 * 3600)
    have = len(glob.glob(os.path.join(out, 'f_*.png')))
    print('  frames %d/%d  %.1f min' % (have, NF, (time.time() - t) / 60), flush=True)
    if have != NF:
        sys.exit('assembly render incomplete, see render/build/logs/assembly_gpu*.log')


def caption_alpha(t, t0, t1, f=0.3):
    return clamp01((t - t0) / f) * clamp01((t1 - t) / f)


def _caption_frame(args):
    p, out = args
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    i = int(os.path.basename(p)[2:6])
    t = i / FPS
    im = Image.open(p).convert('RGBA')
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
    ttl = max(caption_alpha(t, -1, 3.0, 0.5), caption_alpha(t, 21.6, DUR + 1, 0.5))
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
    im.convert('RGB').save(os.path.join(out, os.path.basename(p)), compress_level=1)


def encode(src, quick=False):
    from multiprocessing import Pool
    out = src + '_cap'
    os.makedirs(out, exist_ok=True)
    frames = sorted(glob.glob(os.path.join(src, 'f_*.png')))
    with Pool(min(12, os.cpu_count() or 4)) as pool:
        pool.map(_caption_frame, [(p, out) for p in frames], chunksize=8)
    pat = os.path.join(out, 'f_%04d.png')
    dst = MEDIA if not quick else os.path.join(BUILD, 'assembly_quick_out')
    os.makedirs(dst, exist_ok=True)
    mp4 = os.path.join(dst, 'assembly.mp4')
    gif = os.path.join(dst, 'assembly.gif')
    run(['ffmpeg', '-y', '-framerate', str(FPS), '-i', pat, '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
         '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4], os.path.join(LOGS, 'assembly_mp4.log'))
    run(['ffmpeg', '-y', '-framerate', str(FPS), '-i', pat, '-vf',
         'fps=10,scale=720:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];'
         '[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle', '-loop', '0', gif],   # < 10 MB
        os.path.join(LOGS, 'assembly_gif.log'))
    for f in (mp4, gif):
        print('  %s %.1f MB' % (os.path.relpath(f, ROOT), os.path.getsize(f) / 1e6), flush=True)


def stills(gpus, quick, samples):
    """the build-guide images, split over the GPUs."""
    os.makedirs(IMG, exist_ok=True)
    names = list(STILLS)
    ps = []
    for k, g in enumerate(gpus):
        part = names[k::len(gpus)]
        cmd = [BLENDER, '-b', '--python', os.path.abspath(__file__), '--', '--stills', ','.join(part), '--out', IMG]
        if quick:
            cmd.append('--quick')
        if samples:
            cmd += ['--samples', str(samples)]
        ps.append(subprocess.Popen(cmd, stdout=open(os.path.join(LOGS, 'assembly_stills_gpu%d.log' % g), 'w'),
                                   stderr=subprocess.STDOUT, env=dict(os.environ, CUDA_VISIBLE_DEVICES=str(g))))
    for p in ps:
        p.wait(timeout=3600)
    print('  stills:', sorted(os.path.basename(p) for p in glob.glob(os.path.join(IMG, '*.jpg'))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--no-export', action='store_true')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--samples', type=int, default=0)
    ap.add_argument('--gpus', default='0,1')
    ap.add_argument('--stills', action='store_true', help='only the build-guide stills (docs/build/img/)')
    ap.add_argument('--encode-only', action='store_true')
    a = ap.parse_args()
    os.makedirs(LOGS, exist_ok=True)
    gpus = [int(g) for g in a.gpus.split(',')]
    out = os.path.join(BUILD, 'assembly_quick' if a.quick else 'assembly')
    t = time.time()
    if not a.no_export and not a.encode_only:
        export()
    if a.stills:
        stills(gpus, a.quick, a.samples)
    else:
        if not a.encode_only:
            for f in glob.glob(os.path.join(out, 'f_*.png')):
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
