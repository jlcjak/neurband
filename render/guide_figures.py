#!/usr/bin/env python3
"""Build-guide figures for docs/build/assembly.md: a Blender pass (Cycles / OptiX, the docs/media look,
nb_blender helpers) renders each figure plus a highlight mask and writes the 2D positions of its anchor
points; a PIL pass then draws the annotations (leader lines, dot anchors, Noto Sans labels, step
numbers, motion arrows, highlight outlines).

  python3 render/guide_figures.py                    # cross-section GLB (FreeCAD), Blender on GPUs 0,1, PIL
  python3 render/guide_figures.py --only s3_bond,xsec
  python3 render/guide_figures.py --annotate-only    # PIL pass only, from render/build/guide/
  python3 render/guide_figures.py --quick            # 40 % size, 16 spp (render/build/guide_quick/)

Inputs: render/build/*.glb (python3 render/assembly_anim.py exports them; it also makes
strap_pieces.glb), plus render/build/guide_xsec.glb, which this script builds under FreeCAD from
mech/rev_c (pod, flex, pad, foam dot, webbing and a skin slab, cut at the pod's middle pad).
Raw renders, masks and anchor JSON go to render/build/guide/ (git-ignored); the annotated figures to
docs/build/img/<name>.jpg (1600 px wide, JPEG q88). Figures no longer listed here are deleted from
docs/build/img/.
Blender side: blender -b --python render/guide_figures.py -- --figs hero,exploded [--quick]
"""
import os, sys, math, json, time, argparse, subprocess, glob, threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build')
LOGS = os.path.join(BUILD, 'logs')
IMG = os.path.join(ROOT, 'docs', 'build', 'img')
BLENDER = '/usr/bin/blender'
FREECAD = '/usr/bin/freecad'
FONT_DIR = '/usr/share/fonts/noto'
RES = (1600, 1000)
FIGS = ['hero', 'exploded', 'xsec', 'strap_path', 's1_swd', 's2_cell', 's3_bond', 's4_fold', 's5_close',
        's6_strap', 's7_wear', 's8_charge']

# bonding jig geometry (mech/rev_c/bond_jig.py), mm
R_U, MOD_PRESS, FLEX_REAL, POD_W, POD_PRESS = 42.0, 1.0, 0.11, 7.1, 0.6
RS = R_U - MOD_PRESS - FLEX_REAL
EDGE = POD_W / 2 + 9.0
TH_E = EDGE / RS
ZAX = -RS * math.cos(TH_E)
X_E = RS * math.sin(TH_E)
POD_X_DEV = [-45.0 + 18.0 * k for k in range(8)]
POD_Z0 = FLEX_REAL + POD_PRESS
TAIL_Y0, TAIL_R = 15.0, 1.0                          # the tail bends up through the base's floor slot here


def x_of(xd):
    a = abs(xd)
    if a <= EDGE:
        return math.copysign(RS * math.sin(a / RS), xd)
    return math.copysign(X_E + a - EDGE, xd)


# ================================================================ FreeCAD: cross-section solids
def freecad_xsec(dst):
    """pod on the wrist, cut at its middle pad (pod frame y = 0; the y <= 0 half is kept):
    skin slab (R 30), gold pad (thickened to 0.1 mm to be visible), flex paddle and spine link (0.2 mm),
    foam dot (worn, 1.65 mm), pod shell, webbing in the sleeve and on to the next pods."""
    import FreeCAD, Part, ImportGui
    sys.path.insert(0, os.path.join(ROOT, 'mech', 'rev_c'))
    sys.neurband_lib = True
    import rc as R
    import pod as P
    V = FreeCAD.Vector
    lift = R.STACK_LOADED - R.FLEX_T                  # worn: foam ~35 % compressed
    shell = P.build()
    poly, gold, foam = R.flex_pod(lift)
    zs = -lift - R.FLEX_T - 0.04                       # pad face = skin surface
    Rs = 30.0
    zc = zs - Rs
    half = R.box(-40, 40, -40, 0.0, -40, 40)
    skin = Part.makeCylinder(Rs, 40, V(0, -20, zc), V(0, 1, 0)).cut(Part.makeCylinder(Rs - 7, 40, V(0, -20, zc), V(0, 1, 0)))
    skin = skin.common(R.box(-17, 17, -14, 0, zs - 9, zs + 0.01))
    pads = [Part.makeCylinder(R.PAD_D / 2, 0.1, V(0, y, zs)) for y in R.PAD_Y]
    # webbing: straight in the sleeve, then concentric with the skin toward the next pods
    zw0 = P.BASE_T + 0.1
    zw1 = zw0 + R.STRAP_T
    xe = P.SHELL_W / 2 + 0.5

    def prof(z, n=24, x_max=17.0):
        r = math.hypot(xe, z - zc)
        a0 = math.atan2(xe, z - zc)
        pts = []
        for k in range(n, 0, -1):
            a = a0 + (math.asin(min(x_max / r, 0.99)) - a0) * k / n
            pts.append((-r * math.sin(a), zc + r * math.cos(a)))
        pts += [(-xe, z), (xe, z)]
        for k in range(1, n + 1):
            a = a0 + (math.asin(min(x_max / r, 0.99)) - a0) * k / n
            pts.append((r * math.sin(a), zc + r * math.cos(a)))
        return pts
    lo, hi = prof(zw0), prof(zw1)
    pl = [V(x, 0, z) for x, z in lo] + [V(x, 0, z) for x, z in reversed(hi)]
    pl.append(pl[0])
    web = Part.Face(Part.makePolygon(pl)).extrude(V(0, -R.STRAP_W / 2, 0))
    # spine links (pod y -7.0 .. 0.6) leaving the paddle sides and draping onto the skin
    links = []
    for sx in (-1, 1):
        pts = []
        for k in range(26):
            x = R.POD_W / 2 - 0.3 + (17.0 - R.POD_W / 2 + 0.3) * k / 25
            zpad = -lift - R.FLEX_T / 2
            zsk = zc + math.sqrt((Rs + 0.15) ** 2 - x * x)
            u = min(1.0, max(0.0, (x - R.POD_W / 2) / 2.0))
            u = u * u * (3 - 2 * u)
            pts.append((sx * x, zpad * (1 - u) + zsk * u))
        top = [V(x, 0, z + R.FLEX_T / 2) for x, z in pts]
        bot = [V(x, 0, z - R.FLEX_T / 2) for x, z in reversed(pts)]
        ring = top + bot + [top[0]]
        links.append(Part.Face(Part.makePolygon(ring)).extrude(V(0, R.SPINE_Y[0], 0)))
    flex = poly.fuse(links).removeSplitter()
    items = [('skin', skin), ('pad', Part.makeCompound(pads)), ('flex', flex), ('foam', Part.makeCompound(foam)),
             ('pod', shell), ('webbing', web)]
    doc = FreeCAD.newDocument('xsec')
    feats = []
    for n, sh in items:
        f = doc.addObject('Part::Feature', n)
        f.Shape = sh.common(half)
        feats.append(f)
    doc.recompute()
    if os.path.exists(dst):
        os.remove(dst)
    ImportGui.export(feats, dst)


# ================================================================ Blender side
class Fig:
    """anchors (3D points projected after the camera is final), paths and the highlight set."""

    def __init__(self, name):
        self.name, self.pts, self.paths, self.hi = name, {}, {}, []

    def a(self, key, p):
        self.pts[key] = p

    def path(self, key, pts):
        self.paths[key] = pts


def vis_point(o, p, cam):
    """a visible point of object o near p: ray from the camera toward p; the first hit on o, else p."""
    import bpy
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    org = cam.matrix_world.translation
    d = (Vector(p) - org)
    hit, loc, nrm, idx, ob, mtx = bpy.context.scene.ray_cast(dg, org, d.normalized(), distance=d.length + 0.02)
    if hit and ob is not None and ob.name == o.name:
        return loc
    return Vector(p)


def project(fig, sc, cam, w, h):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector

    def pr(p):
        v = world_to_camera_view(sc, cam, Vector(p))
        return [round(v.x * w, 1), round((1 - v.y) * h, 1)]
    return dict(size=[w, h], pts={k: pr(p) for k, p in fig.pts.items()},
                paths={k: [pr(p) for p in v] for k, v in fig.paths.items()})


def mask_render(NB, objs, path, samples=4):
    """white = the highlighted objects where visible, black elsewhere (holdout for everything else)."""
    import bpy
    sc = bpy.context.scene
    hold = bpy.data.materials.new('mask_hold')
    hold.use_nodes = True
    nt = hold.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    hn = nt.nodes.new('ShaderNodeHoldout')
    nt.links.new(hn.outputs[0], out.inputs['Surface'])
    emi = bpy.data.materials.new('mask_emit')
    emi.use_nodes = True
    nt = emi.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    en = nt.nodes.new('ShaderNodeEmission')
    en.inputs['Strength'].default_value = 1.0
    nt.links.new(en.outputs[0], out.inputs['Surface'])
    saved = {}
    names = set(o.name for o in objs)
    for o in bpy.data.objects:
        if o.type not in ('MESH', 'CURVE') or o.hide_render:
            continue
        saved[o.name] = [s.material for s in o.material_slots]
        m = emi if o.name in names else hold
        if not o.material_slots:
            o.data.materials.append(m)
        for s in o.material_slots:
            s.link = 'DATA'
            s.material = m
    st = (sc.cycles.samples, sc.cycles.use_denoising, sc.view_settings.view_transform, sc.view_settings.look,
          sc.render.film_transparent, sc.camera.data.dof.use_dof, sc.render.filepath)
    sc.cycles.samples, sc.cycles.use_denoising = samples, False
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.film_transparent = True
    sc.camera.data.dof.use_dof = False
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    sc.render.image_settings.color_mode = 'RGB'
    (sc.cycles.samples, sc.cycles.use_denoising, sc.view_settings.view_transform, sc.view_settings.look,
     sc.render.film_transparent, sc.camera.data.dof.use_dof, sc.render.filepath) = st
    for o in bpy.data.objects:
        if o.name in saved:
            for s, m in zip(o.material_slots, saved[o.name]):
                s.material = m


def frame(NB, pts, **kw):
    import bpy
    bpy.context.view_layer.update()
    NB.frame_subject(pts, **kw)
    bpy.context.view_layer.update()


def box_obj(NB, name, c, size, mat, bevel=0.0):
    import bpy
    bpy.ops.mesh.primitive_cube_add(size=1, location=c)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        b = o.modifiers.new('bev', 'BEVEL')
        b.width = bevel
        b.segments = 3
    NB.setmat(o, mat)
    return o


def dot_obj(NB, name, mat, h=0.002, r=0.003):
    """a foam dot, centred on its axis, z from -h/2 to h/2 (local)."""
    import bpy
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=r, depth=h, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    b = o.modifiers.new('bev', 'BEVEL')
    b.width = 0.0002
    b.segments = 2
    NB.setmat(o, mat)
    NB.smooth(o, math.radians(40))
    return o


def mat_foam_light(NB):
    """the EVA dots are white (the sourced 6 x 2 mm dots): readable against the black pods."""
    return NB.principled('eva', (0.80, 0.80, 0.78), 0.9)


# ---------------------------------------------------------------- bonding jig scene
def jig_scene(NB, anim=False):
    import bpy, bmesh
    import numpy as np
    from mathutils import Vector, Matrix
    import assembly_anim as AA
    S = AA.Scene()
    mm = 0.001
    fit = NB.import_glb(os.path.join(BUILD, 'bond_jig_fit.glb'), bake=True)
    jig = pod_t = base = None
    for o in fit.values():
        k = NB.kind(o.name)
        o['kind'] = k
        if k == 'bond_jig':
            jig = o
            NB.setmat(o, AA.mat_tool(NB))
        elif k == 'pod':
            pod_t = o
            NB.setmat(o, NB.mat_pod())
        elif k == 'module_base':
            base = o
            NB.setmat(o, NB.mat_housing())
        NB.smooth(o, math.radians(35))
    x5 = (NB.bbox([pod_t])[0][0] + NB.bbox([pod_t])[1][0]) / 2
    # flex: KiCad GLB (x, -y, F side up) -> jig/world frame (x - 65, y_kicad - 35, F side down), on the saddle
    fl, _ = NB.load_board(os.path.join(BUILD, 'flex_board.glb'), flex=True)
    flex = list(fl.values())
    for o in flex:
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        cuts = [(Vector((x * mm, 0, 0)), Vector((1, 0, 0))) for x in np.arange(-77.0, -52.0, 1.0)]
        cuts += [(Vector((0, -(TAIL_Y0 + 35 + d) * mm, 0)), Vector((0, 1, 0))) for d in np.arange(0.0, 2.0, 0.2)]
        for co, no in cuts:
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co + Vector((0.065, 0, 0)) if no.x else co, plane_no=no)
        bm.to_mesh(o.data)
        bm.free()
        V = NB.verts_np(o, world=False) / mm
        x, y, z = V[:, 0] - 65.0, -V[:, 1] - 35.0, -V[:, 2] + 0.08
        # tail: bend up through the base's floor slot
        s_ = y - TAIL_Y0
        tl = (s_ > 0) & (np.abs(x) < 5.6)
        q = np.pi * TAIL_R / 2
        sb = np.clip(s_, 0, q)
        yy = np.where(tl, TAIL_Y0 + TAIL_R * np.sin(sb / TAIL_R) + 0.0, y)
        zz = np.where(tl, z + TAIL_R * (1 - np.cos(sb / TAIL_R)) + np.clip(s_ - q, 0, None), z)
        yy = np.where(tl & (s_ > q), TAIL_Y0 + TAIL_R - z, yy)
        # saddle
        a = np.abs(x)
        on = a <= EDGE
        ang = np.where(on, a / RS, 0)
        X = np.where(on, np.sign(x) * (RS + zz) * np.sin(ang), np.sign(x) * (X_E + a - EDGE))
        Z = np.where(on, ZAX + (RS + zz) * np.cos(ang), zz)
        o.data.vertices.foreach_set('co', (np.stack([X, yy, Z], 1) * mm).ravel())
        o.data.flip_normals()
        o.data.update()
        if o.data.has_custom_normals:
            try:
                o.data.attributes.remove(o.data.attributes['custom_normal'])
            except Exception:
                pass
        NB.smooth(o, math.radians(30))
    # pods 1, 2, 5-8 from the fitted pod (pod 5), dots in their pockets
    eva = mat_foam_light(NB)
    pods, dots = {}, {}
    for k in (1, 2, 5, 6, 7, 8):
        if k == 5:
            p = pod_t
        else:
            p = pod_t.copy()
            p.data = pod_t.data.copy()
            NB.link(p)
        p.name = 'pod_%d' % k
        pods[k] = p
        dots[k] = []
        for j, y in enumerate((-10.0, 0.0, 10.0)):
            d = dot_obj(NB, 'dot_%d_%d' % (k, j), eva)
            d['local'] = [0.0, y * mm, 0.0]
            dots[k].append(d)
    # base dots: six at the module pads (module_assy foam) and the root dot, in the module frame
    ma = NB.import_glb(os.path.join(BUILD, 'module_assy.glb'), bake=True)
    mfoam = [o for o in ma.values() if NB.kind(o.name) == 'foam']
    mbase = [o for o in ma.values() if NB.kind(o.name) == 'module_base'][0]
    bm0, bm1 = NB.bbox([mbase])
    fb0, fb1 = NB.bbox([base])
    Rz = Matrix.Rotation(math.pi, 4, 'Z')
    cm = Rz @ Vector(((bm0 + bm1) / 2).tolist())
    B = Matrix.Translation(Vector(((fb0 + fb1) / 2).tolist()) - cm) @ Rz      # module frame -> jig
    bdots = []
    for i, o in enumerate(mfoam):
        c = Vector(((NB.bbox([o])[0] + NB.bbox([o])[1]) / 2).tolist())
        d = dot_obj(NB, 'bdot_%d' % i, eva)
        th = math.atan2(c.x, R_U)
        d['M_mod'] = [list(r) for r in (Matrix.Translation(c) @ Matrix.Rotation(-th, 4, 'Y'))]
        bdots.append(d)
    hit = mbase.ray_cast(Vector((0, -0.0104, -0.02)), Vector((0, 0, 1)))
    zr = hit[1].z if hit[0] else 0.0006
    NB.log('root dot pocket z', hit[0], zr)
    d = dot_obj(NB, 'bdot_root', eva)
    d['M_mod'] = [list(r) for r in Matrix.Translation((0, -0.0104, zr - 0.001))]
    bdots.append(d)
    for o in list(ma.values()):
        bpy.data.objects.remove(o)
    # studio
    c = Vector((0.018, 0.002, 0.004))
    NB.sweep(color=(0.52, 0.51, 0.49), depth=0.8, height=1.0, radius=0.3, origin=(0.018, 0.0, -0.003),
             yaw=math.radians(180), mat=NB.mat_paper((0.52, 0.51, 0.49)))
    jig.location.z = 0.0
    NB.studio(c, key=5, fill=1.4, rim=5, top=2.0)
    cam = NB.camera(NB.orbit(c, -10, 38, 0.40), c, lens=85, fstop=16.0, focus=c)
    for m in list(bpy.data.materials):
        if m.node_tree is not None:
            AA.add_fade(m)

    def Lrot(phi, zc_):
        return Matrix.Translation((0, 0, zc_)) @ Matrix.Rotation(phi, 4, 'Y') @ Matrix.Translation((0, 0, -zc_))

    def pose_pod(k, h=0.0, phi=0.0, drop=0.0, alpha=1.0, dot_alpha=1.0):
        xc = x_of(POD_X_DEV[k - 1]) * mm
        W = Matrix.Translation((xc, 0, POD_Z0 * mm + h)) @ Lrot(phi, 2.45 * mm)
        p = pods[k]
        p.matrix_world = W @ Matrix.Translation((-x5, 0, -POD_Z0 * mm))
        p.color = (1, 1, 1, alpha)
        p.hide_render = alpha < 0.002
        for d in dots[k]:
            lx, ly, lz = d['local']
            d.matrix_world = W @ Matrix.Translation((lx, ly, lz - drop))
            d.color = (1, 1, 1, dot_alpha)
            d.hide_render = dot_alpha < 0.002
        return W

    bc = Vector(((fb0 + fb1) / 2).tolist())

    def pose_base(h=0.0, phi=0.0, drop=0.0, alpha=1.0, dot_alpha=1.0, dy=0.0):
        W = Matrix.Translation((0, dy, h)) @ Matrix.Translation(bc) @ Matrix.Rotation(phi, 4, 'Y') @ Matrix.Translation(-bc)
        base.matrix_world = W
        base.color = (1, 1, 1, alpha)
        base.hide_render = alpha < 0.002
        for d in bdots:
            d.matrix_world = W @ B @ Matrix.Translation((0, 0, drop if phi > 1.5 else -drop)) @ Matrix(d['M_mod'])
            d.color = (1, 1, 1, dot_alpha)
            d.hide_render = dot_alpha < 0.002
        return W

    def pose_flex(dz=0.0, alpha=1.0):
        for o in flex:
            o.matrix_world = Matrix.Translation((0, 0, dz))
            o.color = (1, 1, 1, alpha)
            o.hide_render = alpha < 0.002

    H, HB = 0.016, 0.022
    order = (1, 2, 5, 6, 7, 8)

    def apply(t):
        ph, sm, eo = AA.ph, AA.smooth, AA.ease_out
        p = ph(t, 0.1, 1.0)
        pose_flex(0.012 * (1 - eo(p)), sm(p / 0.5))
        a_in = sm(ph(t, 0.9, 1.4))
        flip = AA.ease_io(ph(t, 2.8, 3.6))
        phi = math.pi * (1 - flip)
        for i, k in enumerate(order):
            pd = ph(t, 1.4 + 0.12 * i, 2.2 + 0.12 * i)
            pp = AA.ease_io(ph(t, 3.7 + 0.25 * i, 4.5 + 0.25 * i))
            pose_pod(k, h=H * (1 - pp), phi=phi, drop=0.014 * (1 - eo(pd)), alpha=a_in,
                     dot_alpha=sm(pd / 0.3) if t >= 1.4 + 0.12 * i else 0.0)
        pd = ph(t, 1.4 + 0.12 * 6, 2.3 + 0.12 * 6)
        pb = AA.ease_io(ph(t, 5.4, 6.2))
        pose_base(h=HB * (1 - pb), phi=phi, drop=0.014 * (1 - eo(pd)), alpha=a_in,
                  dot_alpha=sm(pd / 0.3) if t >= 2.12 else 0.0)

    JCAM = [(0.0, 'J', -16, 42, 0.42), (3.0, 'J', -8, 38, 0.40), (5.5, 'J', 2, 34, 0.39), (7.0, 'J', 8, 32, 0.39)]
    S.targets = {'J': c}
    S.cam_at = lambda t: AA.catmull(JCAM, t, S.targets)

    def set_cam(tgt, az, el, d, lens=85):
        loc = NB.orbit(tgt, az, el, d)
        NB.look_at(cam, tgt, loc)
        cam.data.lens = lens
        cam.data.dof.focus_distance = (Vector(tgt) - loc).length
    S.apply, S.set_cam, S.cam = apply, set_cam, cam
    S.pose_pod, S.pose_base, S.pose_flex = pose_pod, pose_base, pose_flex
    S.pods, S.dots, S.base, S.bdots, S.flex, S.jig, S.H, S.HB, S.x5 = pods, dots, base, bdots, flex, jig, H, HB, x5
    return S


# ---------------------------------------------------------------- figure scenes
def fig_ring(NB, F, which):
    """figures on the ring scene: hero, exploded, strap_path, s4_fold, s5_close, s6_strap, s8_charge."""
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    import assembly_anim as AA
    S = AA.ring_scene(NB, clip=(which == 's8_charge'))
    cam = S.cam
    mm = 0.001
    c_of = S.centre
    up = S.up
    if which in ('hero', 'exploded', 'strap_path', 's6_strap'):
        S.apply(23.9)
    if which == 'hero':
        tgt = S.ring_c + Vector((0, 0, 0.002))
        S.set_cam(tgt, 36, 24, 0.30)
        frame(NB, np.vstack([NB.verts_np(o) for o in S.pods + S.lid + [S.band_s]]), fill=0.8)
        return S
    if which == 'exploded':
        for o in S.leads:
            o.hide_render = True
        # root dot (not in the CAD assembly): module frame (0, -10.4), under the base
        rd = dot_obj(NB, 'root_dot', NB.mat_foam())
        rd.matrix_world = S.T @ Matrix.Translation((0, -0.0104, -0.0004))
        rd['M0'] = [list(r) for r in rd.matrix_world]
        rad = S.radial
        moves = []
        for o in S.foam + [rd]:
            moves.append((o, rad(o) * 0.007))
        for o in S.pods:
            moves.append((o, rad(o) * 0.015))
        for o in [S.band_s] + S.ends:
            moves.append((o, None))
        for o in S.slides:
            moves.append((o, rad(o) * 0.026))
        for o in S.base:
            moves.append((o, up * 0.012))
        for o in S.board:
            moves.append((o, up * 0.022))
        S.tail.matrix_world = S.M0(S.tail)
        for o in S.cell:
            moves.append((o, up * 0.031))
        for o in S.lid:
            moves.append((o, up * 0.042))
        for o in S.cap:
            moves.append((o, up * 0.051))
        for o, v in moves:
            if v is None:
                continue
            o.matrix_world = Matrix.Translation(v) @ S.M0(o)
        # webbing: scale the loop out radially by 22 mm (about the ring axis)
        for o in [S.band_s] + S.ends:
            V = NB.verts_np(o, world=False)
            th = np.arctan2(V[:, 0], V[:, 2] - S.z_axis)
            V[:, 0] += 0.025 * np.sin(th)
            V[:, 2] += 0.025 * np.cos(th)
            o.data.vertices.foreach_set('co', V.ravel())
            o.data.update()
        bpy.context.view_layer.update()
        tgt = S.ring_c + up * 0.02
        S.set_cam(tgt, 14, 10, 0.42)
        objs = S.pods + S.lid + S.cap + [S.band_s] + S.slides
        frame(NB, np.vstack([NB.verts_np(o) for o in objs]), fill=0.95, offset=(0.0, -0.01))
        P = lambda o: c_of([o])
        F.a('lid', vis_point(S.lid[0], P(S.lid[0]) + Vector((0.006, 0, 0.004)), cam))
        F.a('cap', vis_point(S.cap[0], P(S.cap[0]) + Vector((0, 0, 0.0015)), cam))
        F.a('cell', vis_point(S.cell[0], P(S.cell[0]) + Vector((-0.002, -0.004, 0.002)), cam))
        bb = NB.bbox(S.board)
        F.a('board', Vector(((bb[0] + bb[1]) / 2).tolist()) + up * 0.001 + Vector((-0.008, 0, 0)))
        F.a('base', vis_point(S.base[0], P(S.base[0]) + Vector((-0.012, -0.012, -0.001)), cam))
        F.a('tail', c_of([S.tail]))
        fl = max(S.flex, key=lambda o: c_of([o]).x - 0.3 * c_of([o]).z)
        F.a('flex', vis_point(fl, c_of([fl]), cam))
        fo = max(S.foam, key=lambda o: c_of([o]).x + 0.2 * c_of([o]).z)
        F.a('foam', vis_point(fo, c_of([fo]), cam))
        F.a('root_dot', c_of([rd]))
        p1 = [o for o in S.pods if S.pod_num[o.name] == 2][0]
        F.a('pod', vis_point(p1, c_of([p1]), cam))
        p7 = [o for o in S.pods if S.pod_num[o.name] == 7][0]
        F.a('pod7', vis_point(p7, c_of([p7]), cam))
        V = NB.verts_np(S.band_s)
        i = np.argmax(V[:, 0] - 1.0 * V[:, 2])
        F.a('webbing', Vector(V[i].tolist()))
        F.a('slide', vis_point(S.slides[0], c_of(S.slides[:1]), cam))
        F.a('slide_b', vis_point(S.slides[1], c_of(S.slides[1:]), cam))
        return S
    if which == 'strap_path':
        # end view from the distal side, orthographic, on a flat light background
        sw = bpy.data.objects.get('sweep')
        if sw:
            bpy.data.objects.remove(sw)
        bg = bpy.context.scene.world.node_tree.nodes.get('Background')
        bg.inputs['Color'].default_value = (0.80, 0.79, 0.77, 1)
        bg.inputs['Strength'].default_value = 1.0
        tgt = S.ring_c + Vector((0, 0, 0.004))
        S.set_cam(tgt, 0, 0, 0.5)
        cam.data.type = 'ORTHO'
        cam.data.dof.use_dof = False
        bb = NB.bbox(S.pods + S.lid + [S.band_s] + S.ends)
        cam.data.ortho_scale = (bb[1][0] - bb[0][0]) * 1.0 / 0.52 * 1.0
        cam.location.z = (bb[0][2] + bb[1][2]) / 2
        V = NB.verts_np(S.band_s)
        th = np.mod(np.degrees(np.arctan2(V[:, 0], V[:, 2] - S.z_axis)), 360)
        r = np.hypot(V[:, 0], V[:, 2] - S.z_axis)
        y0 = V[:, 1].min() - 0.002
        path = []
        for a in np.arange(th.min() + 2, th.max() - 1, 4.0):
            sel = np.abs(th - a) < 2.0
            if sel.any():
                rr = r[sel].max() + 0.0045
                path.append(Vector((rr * math.sin(math.radians(a)), y0, S.z_axis + rr * math.cos(math.radians(a)))))
        F.path('loop', path)
        for o in S.pods:
            F.a('pod%d' % S.pod_num[o.name], c_of([o]) + Vector((0, -0.01, 0)))
        F.a('slideA', c_of(S.slides[:1]) + Vector((0, -0.01, 0)))
        F.a('slideB', c_of(S.slides[1:]) + Vector((0, -0.01, 0)))
        F.a('module', c_of(S.lid) + Vector((0, -0.01, 0.002)))
        p1 = [o for o in S.pods if S.pod_num[o.name] == 1][0]
        p8 = [o for o in S.pods if S.pod_num[o.name] == 8][0]
        a1 = math.atan2(c_of([p1]).x, c_of([p1]).z - S.z_axis)
        a8 = math.atan2(c_of([p8]).x, c_of([p8]).z - S.z_axis) + 2 * math.pi
        ag = (a1 + a8) / 2
        rg = 0.022
        F.a('gap', Vector((rg * math.sin(ag), y0, S.z_axis + rg * math.cos(ag))))
        F.a('axis', Vector((0, y0, S.z_axis)))
        for key, o, sl in (('tailA', S.straps.get('strap_tail_a'), S.slides[0]), ('tailB', S.straps.get('strap_tail_b'), S.slides[1])):
            if o is None:
                continue
            V = NB.verts_np(o)
            cs = np.array(c_of([sl]))
            i = np.argmax(np.linalg.norm(V - cs, axis=1))
            e = Vector(V[i].tolist())
            d = (e - Vector(cs.tolist()))
            d.y = 0
            F.a(key + '_end', e + Vector((0, -0.01, 0)))
            F.a(key + '_pull', e + d.normalized() * 0.010 + Vector((0, -0.01, 0)))
        return S
    if which == 's4_fold':
        S.apply(8.35)
        xr = NB.principled('j1_ghost', (0.75, 0.80, 0.85), 0.2, transmission_weight=0.0, alpha=0.28)
        for o in S.j1:
            NB.setmat(o, xr)
        for o in S.lid + S.cap + S.cell + S.slides + [S.band_s] + S.ends:
            o.hide_render = True
        hz = S.T @ Vector((0.0, -0.0145, 0.0075))
        S.set_cam(hz + Vector((0, 0.002, -0.001)), 58, 20, 0.15)
        cam.data.dof.aperture_fstop = 28
        bb = NB.bbox(S.board)
        frame(NB, np.vstack([NB.verts_np(o) for o in S.board + S.base] + [NB.verts_np(S.tail)]), fill=0.82,
                         offset=(-0.06, 0.0))
        F.hi = [S.tail]
        j1c = c_of(S.j1)
        F.a('j1', j1c + S.prox * 0.0015)
        F.a('tail', vis_point(S.tail, c_of([S.tail]) + up * -0.001, cam))
        lat = [o for o in S.j1 if o.name.startswith('ClosedCreamFlipbar')]
        if lat:
            F.a('latch', c_of(lat))
        F.a('base', vis_point(S.base[0], c_of(S.base) + Vector((0.008, -0.004, 0.003)), cam))
        F.a('board', vis_point(S.board[0], c_of(S.board) + up * 0.002, cam) if False else c_of(S.board))
        P = Vector((0.0, 0.010, 0.0026))
        arc = []
        for s in np.linspace(0.05, 0.95, 16):
            Hm = S.board_H(float(s), 0.0)
            arc.append(Hm @ (S.T @ P) + up * 0.004)
        F.path('fold', arc)
        return S
    if which == 's5_close':
        S.apply(10.35)
        for o in S.slides + [S.band_s] + S.ends:
            pass
        for o, dz in [(x, 0.016) for x in S.cell] + [(x, 0.030) for x in S.cap] + [(x, 0.040) for x in S.lid]:
            S.place(o, Matrix.Translation(up * dz) @ S.M0(o), 1.0)
        tgt = c_of(S.base) + up * 0.018
        S.set_cam(tgt, 36, 30, 0.24)
        cam.data.dof.aperture_fstop = 24
        frame(NB, np.vstack([NB.verts_np(o) for o in S.base + S.lid + S.cell + S.cap]), fill=0.86, offset=(-0.05, 0))
        F.hi = list(S.cell)
        F.a('cell', vis_point(S.cell[0], c_of(S.cell) + up * 0.002, cam))
        F.a('cell_down', c_of(S.cell) - up * 0.003)
        F.a('cell_land', c_of(S.cell) - up * 0.012)
        F.a('cap', vis_point(S.cap[0], c_of(S.cap) + up * 0.0015, cam))
        F.a('cap_land', c_of(S.cap) - up * 0.010)
        F.a('lid', vis_point(S.lid[0], c_of(S.lid) + up * 0.004 + Vector((-0.006, 0, 0)), cam))
        F.a('lid_down', c_of(S.lid) - up * 0.004 + Vector((-0.009, 0, 0)))
        F.a('lid_land', c_of(S.lid) - up * 0.016 + Vector((-0.009, 0, 0)))
        F.a('base', vis_point(S.base[0], c_of(S.base) + Vector((-0.010, -0.012, 0.0)), cam))
        F.a('j1', c_of(S.j1))
        F.a('board', c_of(S.board) + up * 0.0015 + Vector((0.006, 0.004, 0)))
        return S
    if which == 's6_strap':
        # end view along the band (from the hand side) at slide A: the webbing's edge shows the locking path
        sl = S.slides[0]
        p2 = [o for o in S.pods if S.pod_num[o.name] == 2][0]
        lk, tl = S.straps.get('strap_lock_a'), S.straps.get('strap_tail_a')
        tgt = (c_of([sl]) + c_of([p2])) / 2 + Vector((0.004, 0, 0.002))
        S.set_cam(tgt, 84, 30, 0.17)
        cam.data.dof.aperture_fstop = 24
        frame(NB, np.vstack([NB.verts_np(o) for o in [sl, p2] + S.lid]), fill=0.80, offset=(0.20, 0.0))
        F.hi = [sl]
        y0 = NB.bbox([lk])[0][1]
        front = lambda o: Vector(((NB.bbox([o])[0] + NB.bbox([o])[1]) / 2).tolist())
        F.a('slide', vis_point(sl, front(sl), cam))
        F.a('tail_mid', front(tl))
        F.a('webbing', vis_point(lk, front(lk) + up * 0.002, cam))
        F.a('pod2', vis_point(p2, front(p2), cam))
        F.a('module', vis_point(S.lid[0], c_of(S.lid) + Vector((0.006, 0, 0.004)), cam))
        return S
    if which == 's8_charge':
        S.apply(20.25)
        for o in S.cap:
            pass
        tgt = S.targets['C'] + Vector((0, 0.006, -0.002))
        S.set_cam(tgt, 140, 22, 0.20)
        cam.data.dof.aperture_fstop = 14
        clip = [o for o in S.clip if o.type == 'MESH']
        frame(NB, np.vstack([NB.verts_np(o) for o in clip + S.lid + S.base]), fill=0.8, offset=(-0.04, 0.02))
        F.hi = [o for o in clip if o['kind'] == 'charge_clip']
        cc = c_of(F.hi)
        F.a('clip', vis_point(F.hi[0], cc + Vector((0.004, 0, 0)), cam))
        F.a('clip_from', cc + S.prox * 0.004)
        F.a('clip_to', cc - S.prox * 0.008)
        pins = [o for o in clip if o['kind'] == 'pogo_pins']
        if pins:
            F.a('pins', c_of(pins) + up * 0.004)
        F.a('key', S.T @ Vector((0.0, 0.0172, 0.0026)))
        F.a('notch', S.T @ Vector((0.0, 0.0168, 0.0026)))
        F.a('hook', vis_point(F.hi[0], S.T @ Vector((0.004, 0.0185, 0.0112)) + S.prox * 0.0058, cam))
        F.a('usb', S.T @ Vector((0.0, 0.045, -0.021)) + S.prox * 0.0)
        F.a('lid', vis_point(S.lid[0], c_of(S.lid) + up * 0.004, cam))
        return S
    raise KeyError(which)


def fig_charge(NB, F):
    """the module alone, seen from below and behind: the charge clip (see-through) sliding on from the
    proximal end, its two pogo pins, the key into the pry notch and the USB lead."""
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    import assembly_anim as AA
    mod = NB.load_module()
    bobj = NB.board_into(mod)
    cc = NB.import_glb(os.path.join(BUILD, 'charge_clip_fit.glb'), bake=True)
    ghost = NB.principled('clip_ghost', (0.80, 0.80, 0.78), 0.45, alpha=0.25)
    clip, pins = [], []
    for o in list(cc.values()):
        k = NB.kind(o.name)
        if k == 'charge_clip':
            NB.setmat(o, ghost)
            clip.append(o)
        elif k == 'pogo_pins':
            NB.setmat(o, NB.mat_gold())
            pins.append(o)
        else:
            bpy.data.objects.remove(o)
            continue
        NB.smooth(o, math.radians(35))
    mm = 0.001
    usb = [(0, 19.6, -13.0), (0, 24.0, -13.3), (0, 33.0, -15.5), (0, 50.0, -24.0), (0, 75.0, -40.0)]
    cab = AA.curve_obj(NB, 'usb_lead', [tuple(x * mm for x in q) for q in usb], 0.0016,
                       NB.principled('cable', (0.03, 0.03, 0.032), 0.45))
    G = Matrix.Translation((0, 0, 0.085))
    off = Matrix.Translation((0, 0.007, 0))
    for o in list(mod.values()) + list(bobj.values()):
        if o.name in bpy.data.objects:
            o.matrix_world = G @ o.matrix_world
    for o in clip + pins + [cab]:
        o.matrix_world = G @ off @ o.matrix_world
    bpy.context.view_layer.update()
    W = lambda q, moving=False: (G @ off if moving else G) @ Vector(q)
    tgt = W((0.0, 0.010, -0.002))
    NB.sweep(color=(0.52, 0.51, 0.49), depth=0.8, height=1.0, radius=0.3, origin=(0, 0, 0), yaw=math.radians(180 + 128),
             mat=NB.mat_paper((0.52, 0.51, 0.49)))
    NB.studio(tgt, key=5, fill=1.8, rim=5, top=1.5, key_dir=(0.45, 0.2, -0.25), fill_dir=(0.3, 0.6, 0.1))
    cam = NB.camera(NB.orbit(tgt, 150, -9, 0.20), tgt, lens=85, fstop=24.0, focus=tgt)
    objs = [o for o in mod.values() if o.name in bpy.data.objects and not o.hide_render] + clip
    frame(NB, np.vstack([NB.verts_np(o) for o in objs]), fill=0.78, offset=(-0.06, -0.02))
    F.hi = clip
    F.a('clip', vis_point(clip[0], W((0.006, 0.0215, -0.004), True), cam))
    if pins:
        a_, b_ = NB.bbox(pins)
        F.a('pins', Vector((float((a_[0] + b_[0]) / 2), float((a_[1] + b_[1]) / 2), float(b_[2]) - 0.0015)))
    F.a('key', W((0.0, 0.0166, 0.0026), True))
    F.a('hook', W((0.005, 0.0160, 0.0104), True))
    F.a('usb', W((0.0, 0.0285, -0.0138), True))
    F.a('clip_from', W((0.0, 0.034, -0.018)))
    F.a('clip_to', W((0.0, 0.022, -0.018)))
    lid = [o for o in mod.values() if o.name in bpy.data.objects and o['kind'] == 'module_lid']
    if lid:
        F.a('module', vis_point(lid[0], W((-0.012, 0.0, 0.006)), cam))
    return None


def fig_xsec(NB, F):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    objs = NB.import_glb(os.path.join(BUILD, 'guide_xsec.glb'), bake=True)
    web = NB.principled('web_sec', (0.13, 0.15, 0.20), 0.8, sheen_weight=0.5, sheen_roughness=0.3)
    NB.add_bump(web, scale=2400.0, strength=0.25, distance=0.00008, detail=2.0)
    mats = {'skin': NB.mat_skin(), 'pad': NB.mat_gold(), 'flex': NB.mat_flex(), 'foam': mat_foam_light(NB),
            'pod': NB.principled('pod_sec', (0.045, 0.045, 0.05), 0.4), 'webbing': web}
    by = {}
    for o in objs.values():
        k = NB.kind(o.name)
        o['kind'] = k
        by[k] = o
        NB.setmat(o, mats.get(k, NB.mat_pod()))
        if k == 'webbing':
            NB.add_weave_attr(o)
        NB.smooth(o, math.radians(30))
    allo = list(objs.values())
    mn, mx = NB.bbox(allo)
    G = Matrix.Translation((0, 0, 0.004 - mn[2]))
    for o in allo:
        o.matrix_world = G
    bpy.context.view_layer.update()
    mn, mx = NB.bbox(allo)
    c = Vector(((mn + mx) / 2).tolist())
    pc = NB.bbox([by['pod']])
    podc = Vector(((pc[0] + pc[1]) / 2).tolist())
    NB.sweep(color=(0.52, 0.51, 0.49), depth=0.5, height=0.6, radius=0.2, origin=(0, 0.04, 0), yaw=math.radians(0),
             mat=NB.mat_paper((0.52, 0.51, 0.49)))
    tgt = podc + Vector((0, 0, -0.002))
    cam = NB.camera(NB.orbit(tgt, 174, 8, 0.16), tgt, lens=85, fstop=28.0, focus=podc)
    NB.studio(tgt, key=5, fill=1.6, rim=4, top=2.0, key_dir=(0.35, 0.5, 0.55), fill_dir=(-0.6, 0.5, 0.25),
              rim_dir=(-0.25, -0.55, 0.35))
    frame(NB, np.vstack([NB.verts_np(o) for o in allo]), fill=0.84, offset=(0.0, 0.03))
    ymax = mx[1]

    def face_pt(o, x, z):
        """a point on the cut face (y = ymax) of o at (x, z) in the figure frame (m)."""
        return Vector((x, ymax, z))
    zs = podc.z
    pb = NB.bbox([by['pod']])
    fb = NB.bbox([by['foam']])
    flb = NB.bbox([by['flex']])
    padb = NB.bbox([by['pad']])
    wb = NB.bbox([by['webbing']])
    sb = NB.bbox([by['skin']])
    z0 = pb[0][2]                                    # pod face
    F.a('pod', face_pt(by['pod'], -0.0040, z0 + 0.0013))
    F.a('webbing', face_pt(by['webbing'], -0.0010, z0 + 0.00285))
    F.a('foam', face_pt(by['foam'], 0.0010, (fb[0][2] + fb[1][2]) / 2))
    F.a('flex', face_pt(by['flex'], -0.0018, padb[1][2] + 0.0001))
    F.a('pad', face_pt(by['pad'], 0.0020, (padb[0][2] + padb[1][2]) / 2))
    F.a('skin', face_pt(by['skin'], 0.007, sb[1][2] - 0.003))
    zc_f = sb[1][2] - 0.030
    rr = z0 + 0.0036 - zc_f + 0.0024
    F.path('slide', [Vector((rr * math.sin(a), ymax, zc_f + rr * math.cos(a))) for a in np.linspace(-0.42, 0.42, 30)])
    Vf = NB.verts_np(by['flex'])
    F.a('link_r', Vector((Vf[:, 0].max() - 0.001, ymax, Vf[Vf[:, 0].argmax()][2])))
    F.a('link_l', Vector((Vf[:, 0].min() + 0.001, ymax, Vf[Vf[:, 0].argmin()][2])))
    F.hi = []
    return None


def fig_swd(NB, F):
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    import assembly_anim as AA
    objs = NB.import_glb(os.path.join(BUILD, 'swd_jig_fit.glb'), bake=True)
    jig, pins = None, []
    for o in objs.values():
        k = NB.kind(o.name)
        if k == 'swd_jig':
            jig = o
            NB.setmat(o, AA.mat_tool(NB))
        else:
            pins.append(o)
            NB.setmat(o, NB.mat_gold())
        NB.smooth(o, math.radians(35))
    bobj, body = NB.load_board()
    bmn, bmx = NB.bbox([body])
    hover = 0.009
    M = Matrix.Translation((-bmn[0], -bmx[1], 0.0165 - bmn[2] + hover))
    for o in bobj.values():
        o.matrix_world = M @ o.matrix_world
    mm = 0.001
    TP_X = (16.00, 17.27, 18.54, 19.81, 21.08)
    cols = [(0.60, 0.04, 0.03), (0.75, 0.60, 0.05), (0.08, 0.35, 0.10), (0.75, 0.75, 0.72), (0.02, 0.02, 0.022)]
    wires = []
    for i, x in enumerate(TP_X):
        sx = -1 if i % 2 else 1
        p0 = (x * mm + sx * 0.0004, -0.0257, 0.0019)
        pts = [p0, (x * mm + sx * 0.0004, -0.0270, 0.0012), (x * mm, -0.031, 0.0008), (x * mm - 0.002, -0.040, 0.0008),
               (x * mm - 0.010 + i * 0.002, -0.062, 0.0009), (x * mm - 0.030 + i * 0.003, -0.085, 0.0009)]
        wires.append(AA.curve_obj(NB, 'wire_%d' % i, pts, 0.0005, NB.principled('w%d' % i, cols[i], 0.35, coat_weight=0.3)))
    c = Vector((0.016, -0.016, 0.012))
    NB.sweep(color=(0.52, 0.51, 0.49), depth=0.6, height=0.8, radius=0.25, origin=(0.016, 0.0, 0), yaw=math.radians(180 + 30),
             mat=NB.mat_paper((0.52, 0.51, 0.49)))
    NB.studio(c, key=5, fill=1.4, rim=5, top=2.0)
    cam = NB.camera(NB.orbit(c, 30, 40, 0.20), c, lens=85, fstop=14.0, focus=c)
    frame(NB, np.vstack([NB.verts_np(jig), NB.verts_np(body)] + [NB.verts_np(p) for p in pins]), fill=0.80,
                     offset=(-0.04, 0.02))
    F.hi = [body]
    F.a('board', vis_point(body, Vector(((bmn + bmx) / 2).tolist()) + Vector((-bmn[0], -bmx[1], 0.0165 - bmn[2] + hover))
                           + Vector((-0.004, 0.004, 0.0)), cam))
    F.a('board_from', Vector((-0.0035, -0.010, 0.0165 + hover + 0.002)))
    F.a('board_to', Vector((-0.0035, -0.010, 0.0172)))
    F.a('pins', Vector((18.54 * mm, -0.0257, 0.0178)))
    F.a('jig', vis_point(jig, Vector((0.002, -0.028, 0.012)), cam))
    F.a('wires', Vector((TP_X[2] * mm - 0.003, -0.044, 0.0009)))
    F.a('press', Vector((0.010, -0.008, 0.0165 + hover + 0.0012)))
    F.a('tp_edge', Vector((18.54 * mm, -0.0262, 0.0165 + hover)))
    return None


def fig_cell(NB, F):
    """bare board bottom-up, the cell beyond its distal edge, its leads soldered flat on J2, Kapton."""
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix
    import assembly_anim as AA
    bobj, body = NB.load_board()
    objs = list(bobj.values())
    mn, mx = NB.bbox(objs)
    bmn, bmx = NB.bbox([body])
    cc = Vector(((mn + mx) / 2).tolist())
    R = Matrix.Rotation(math.pi, 4, 'Y')
    M = Matrix.Translation((0, 0, 0)) @ R @ Matrix.Translation(-cc)
    for o in objs:
        o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    a, b = NB.bbox(objs)
    Lz = Matrix.Translation((0, 0, -a[2]))
    for o in objs:
        o.matrix_world = Lz @ o.matrix_world
    M = Lz @ M
    mm = 0.001

    def kp(xk, yk, top=False):
        return M @ Vector((bmn[0] + xk * mm, bmx[1] - yk * mm, bmx[2] if top else bmn[2]))
    pv, pg = kp(23.9, 25.6), kp(26.9, 25.6)
    edge = kp(25.4, 27.0)
    # the cell: 12 x 25 x 4 mm, lead end toward the board's distal edge, lying on the mat beyond it
    cy = edge.y - 0.004 - 0.0125
    cx = (pv.x + pg.x) / 2
    cell = box_obj(NB, 'cell', (cx, cy, 0.002), (0.012, 0.025, 0.004), NB.mat_lipo(), bevel=0.0008)
    pcm = box_obj(NB, 'pcm', (cx, cy + 0.0118, 0.002), (0.0118, 0.0016, 0.0036),
                  NB.principled('pcm', (0.55, 0.32, 0.05), 0.4, coat_weight=0.4))
    zt = pv.z + 0.0002
    yl = cy + 0.0127
    red = AA.curve_obj(NB, 'lead_red', [(pv.x + 0.0013, yl, 0.0024), (pv.x + 0.0008, yl + 0.002, 0.0026), (pv.x, (yl + pv.y) / 2, zt + 0.0002),
                                         (pv.x, pv.y + 0.0016, zt), (pv.x, pv.y - 0.0004, zt)], 0.00028,
                       NB.principled('red', (0.55, 0.045, 0.035), 0.35, coat_weight=0.3))
    blk = AA.curve_obj(NB, 'lead_black', [(pg.x - 0.0013, yl, 0.0024), (pg.x - 0.0008, yl + 0.002, 0.0026), (pg.x, (yl + pg.y) / 2, zt + 0.0002),
                                           (pg.x, pg.y + 0.0016, zt), (pg.x, pg.y - 0.0004, zt)], 0.00028,
                       NB.principled('black', (0.02, 0.02, 0.022), 0.35, coat_weight=0.3))
    kap = box_obj(NB, 'kapton', ((pv.x + pg.x) / 2, pv.y + 0.0004, zt + 0.0004), (0.0062, 0.0050, 0.00006),
                  NB.principled('kapton', (0.85, 0.45, 0.06), 0.25, transmission_weight=0.0, alpha=0.55))
    c = Vector(((pv.x + pg.x) / 2, (pv.y + cy) / 2 - 0.002, 0.002))
    NB.sweep(color=(0.20, 0.30, 0.26), depth=0.6, height=0.8, radius=0.25, origin=(c.x, 0.0, 0), yaw=math.radians(180 + 25),
             mat=NB.mat_paper((0.16, 0.25, 0.22), rough=0.9))
    NB.studio(c, key=5, fill=1.4, rim=5, top=2.0)
    cam = NB.camera(NB.orbit(c, 22, 52, 0.20), c, lens=85, fstop=14.0, focus=c)
    frame(NB, np.vstack([NB.verts_np(body), NB.verts_np(cell)]), fill=0.86, offset=(-0.05, 0.0))
    F.hi = []
    F.a('vbat', pv + Vector((0, -0.0008, 0.0003)))
    F.a('gnd', pg + Vector((0, -0.0008, 0.0003)))
    F.a('red', Vector((pv.x, (yl + pv.y) / 2 - 0.001, zt)))
    F.a('black', Vector((pg.x, (yl + pg.y) / 2 - 0.001, zt)))
    F.a('kapton', Vector(((pv.x + pg.x) / 2 + 0.002, pv.y + 0.0018, zt + 0.0005)))
    F.a('cell', vis_point(cell, Vector((cx - 0.002, cy - 0.004, 0.004)), cam))
    F.a('edge', edge + Vector((-0.006, 0, 0.0)))
    F.a('board', vis_point(body, kp(10.0, 12.0) + Vector((0, 0, 0.0002)), cam))
    F.a('tps', kp(18.5, 25.7) + Vector((0, 0, 0.0002)))
    F.a('fold_from', Vector((cx - 0.004, cy - 0.006, 0.006)))
    F.a('fold_mid', Vector((cx - 0.004, edge.y + 0.002, 0.016)))
    F.a('fold_to', Vector((cx - 0.004, edge.y + 0.014, 0.008)))
    F.path('fold', [Vector((cx - 0.004, cy - 0.004 + (edge.y - cy + 0.004) * u + 0.012 * u, 0.004 + 0.014 * math.sin(math.pi * u)))
                    for u in np.linspace(0, 1, 14)])
    return None


def fig_wear(NB, F):
    import bpy
    import numpy as np
    from mathutils import Vector
    band = NB.load_band()                            # pod ring mirrored to the real flex order
    arm, info = NB.build_arm(curl=30)
    NB.fit_band_to_arm(band, arm)
    objs = list(band.values()) + [arm]
    rig = NB.rig_objects(objs)
    NB.pose(rig, pitch=8, floor_objs=objs, floor=0.0003)
    c, mn, mx = NB.module_centre(band)
    tgt = c + rig.matrix_world.to_3x3() @ Vector((0, -0.05, -0.02))
    cam = NB.camera(NB.orbit(tgt, 62, 40, 0.56), tgt, lens=85, fstop=4.5, focus=c + Vector((0, 0, 0.004)))
    NB.sweep(color=(0.40, 0.37, 0.33), depth=1.0, height=1.0, radius=0.35, origin=(0, 0, 0), yaw=math.radians(180 + 62))
    NB.studio(c, key=7, fill=1.2, rim=5, top=2.0)
    bpy.context.view_layer.update()
    lid = [o for o in band.values() if o['kind'] == 'module_lid'][0]
    capo = [o for o in band.values() if o['kind'] == 'button_cap']
    F.a('module', vis_point(lid, c + Vector((0, 0, 0.004)), cam))
    if capo:
        a_, b_ = NB.world_bbox(capo)
        F.a('cap', Vector(((a_ + b_) / 2).tolist()) + Vector((0, 0, 0.001)))
    sl = [o for o in band.values() if o['kind'] == 'strap_slide']
    if sl:
        s0 = max(sl, key=lambda o: NB.world_bbox([o])[0][0])
        a_, b_ = NB.world_bbox([s0])
        F.a('slide', Vector(((a_ + b_) / 2).tolist()))
    pods = [o for o in band.values() if o['kind'] == 'pod_shells']
    vp = [o for o in pods if NB.world_bbox([o])[1][2] > c.z - 0.03]
    if vp:
        p = max(vp, key=lambda o: NB.world_bbox([o])[1][0])
        a_, b_ = NB.world_bbox([p])
        F.a('pod', vis_point(p, Vector(((a_ + b_) / 2).tolist()), cam))
    ax = rig.matrix_world.to_3x3() @ Vector((0, 1, 0))
    F.a('slip_from', c + ax * -0.075 + Vector((0, 0, 0.022)))
    F.a('slip_to', c + ax * -0.030 + Vector((0, 0, 0.022)))
    F.a('crease', c + ax * -0.025 + Vector((0.0, 0, -0.004)))
    return None


def fig_bond(NB, F):
    import bpy
    import numpy as np
    from mathutils import Vector
    S = jig_scene(NB)
    S.pose_flex()
    mm = 0.001
    for k in (1, 2):
        S.pose_pod(k)
    S.pose_pod(5, h=0.010)
    for k in (6, 7, 8):
        S.pose_pod(k, h=S.H, phi=math.pi)
    S.pose_base(h=S.HB * 0.75, phi=math.pi, dy=-0.030)
    bpy.context.view_layer.update()
    c = Vector((0.016, 0.0, 0.006))
    S.set_cam(c, -12, 40, 0.40)
    S.cam.data.dof.aperture_fstop = 28
    frame(NB, np.vstack([NB.verts_np(S.jig), NB.verts_np(S.base)] + [NB.verts_np(S.pods[k]) for k in S.pods]),
                     fill=0.86, offset=(0.0, 0.05))
    cam = S.cam
    F.hi = [S.pods[5]]
    ctr = lambda o: Vector(((NB.bbox([o])[0] + NB.bbox([o])[1]) / 2).tolist())
    F.a('flex', vis_point(S.flex[0], Vector((x_of(-36.0) * mm, -0.004, 0.0002)), cam))
    F.a('pin', Vector((x_of(-45.0) * mm, 0.005, 0.0006)))
    F.a('pin2', Vector((x_of(63.0) * mm, -0.005, 0.0006)))
    F.a('dots', ctr(S.dots[6][1]) + Vector((0, 0, 0.0008)))
    F.a('dots_up', ctr(S.pods[8]) + Vector((0, 0, 0.003)))
    F.a('pod5', vis_point(S.pods[5], ctr(S.pods[5]) + Vector((0, 0, 0.002)), cam))
    F.a('pod5_from', ctr(S.pods[5]) + Vector((0, -0.020, 0.006)))
    F.a('pod5_to', ctr(S.pods[5]) + Vector((0, -0.020, -0.004)))
    F.a('pod1', vis_point(S.pods[1], ctr(S.pods[1]) + Vector((0, 0, 0.002)), cam))
    F.a('base', vis_point(S.base, ctr(S.base) + Vector((0.006, 0.0, 0.004)), cam))
    F.a('tail', Vector((0.0, (TAIL_Y0 + 1.0) * mm, 0.0085)))
    F.a('fence', vis_point(S.jig, Vector((x_of(81.0) * mm + 0.0052, 0.012, 0.0022)), cam))
    for k in (1, 2, 5, 6, 7, 8):
        F.a('n%d' % k, ctr(S.pods[k]) + Vector((0, -0.020, 0.0)))
    F.a('n3', Vector((x_of(-9.0) * mm, -0.022, 0.003)))
    F.a('n4', Vector((x_of(9.0) * mm, -0.022, 0.003)))
    return S


def blender_main(argv):
    import bpy
    sys.path.insert(0, HERE)
    import nb_blender as NB
    ap = argparse.ArgumentParser()
    ap.add_argument('--figs', default=','.join(FIGS))
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--samples', type=int, default=0)
    ap.add_argument('--out', default=os.path.join(BUILD, 'guide'))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    for name in a.figs.split(','):
        t0 = time.time()
        NB.reset()
        NB.MATS.clear()
        samples = a.samples or (16 if a.quick else 128)
        sc = NB.setup_render(*RES, samples, a.quick)
        sc.render.resolution_percentage = 40 if a.quick else 100
        sc.cycles.transparent_max_bounces = 24
        bg = sc.world.node_tree.nodes.get('Background')
        bg.inputs['Color'].default_value = (0.62, 0.61, 0.59, 1)
        bg.inputs['Strength'].default_value = 0.35
        F = Fig(name)
        if name in ('hero', 'exploded', 'strap_path', 's4_fold', 's5_close', 's6_strap'):
            fig_ring(NB, F, name)
        elif name == 'xsec':
            fig_xsec(NB, F)
        elif name == 's1_swd':
            fig_swd(NB, F)
        elif name == 's2_cell':
            fig_cell(NB, F)
        elif name == 's3_bond':
            fig_bond(NB, F)
        elif name == 's7_wear':
            fig_wear(NB, F)
        elif name == 's8_charge':
            fig_charge(NB, F)
        bpy.context.view_layer.update()
        w = int(RES[0] * sc.render.resolution_percentage / 100)
        h = int(RES[1] * sc.render.resolution_percentage / 100)
        meta = project(F, sc, sc.camera, w, h)
        raw = os.path.join(a.out, name + '.png')
        sc.render.filepath = raw
        bpy.ops.render.render(write_still=True)
        if F.hi:
            mask_render(NB, F.hi, os.path.join(a.out, name + '_mask.png'))
            meta['mask'] = name + '_mask.png'
        with open(os.path.join(a.out, name + '.json'), 'w') as f:
            json.dump(meta, f, indent=1)
        NB.log('figure', name, '%.0f s' % (time.time() - t0))


# ================================================================ PIL annotation pass
INK = (30, 29, 28)
SUB = (88, 86, 82)
ACC = (214, 92, 42)                                   # motion arrows, highlight outline
HALO = (240, 237, 232)

# label: (anchor, text, placement); placement 'L' / 'R' (column at the frame edge), or (dx, dy) in px
# from the anchor (1600 px frame), with an optional third item: the text anchor ('lm', 'rm', 'mb', 'mt').
# arrows: ('arrow', from, to) | ('darrow', a, b) | ('path', key[, 'both'])
SPEC = {
    'hero': dict(labels=[]),
    'exploded': dict(labels=[
        ('cap', 'Button cap', 'L'), ('lid', 'Lid\nfour snap catches, cell cage ribs inside', 'L'),
        ('cell', 'Cell\n401223 LiPo, its leads soldered to J2', 'L'), ('board', 'Main board\nflashed and tested first', 'L'),
        ('base', 'Module base\ncarries the pads of pods 3 and 4', 'L'),
        ('slide', 'Strap slide  x2\nclips onto the hidden bar', 'R'),
        ('tail', 'Flex tail\ninto J1', 'L'),
        ('webbing', 'Webbing\n20 mm elastic, one closed loop', 'R'),
        ('pod', 'Pod  x6\nTPU, slides on the webbing', 'R'),
        ('foam', 'Foam dots  x25\n6 x 2 mm EVA, double-sided', 'R'),
        ('flex', 'Electrode flex\n24 gold pads on the skin side', 'R')]),
    'xsec': dict(labels=[
        ('webbing', 'Webbing in its sleeve\nslides freely through the pod', 'L'),
        ('pod', 'TPU pod\nholds the dots, rides on the webbing', 'R'),
        ('foam', 'Foam dot\npushes the pad onto the skin', 'R'),
        ('flex', 'Flex (0.11 mm polyimide)\nsets the 18 mm pod spacing', 'L'),
        ('pad', 'Gold pad\non the skin', 'R'),
        ('skin', 'Skin', 'L')],
        arrows=[('path', 'slide', 'both')],
        note='Section through the middle pad of one pod, worn. Not to scale: the gold pad is drawn thicker.'),
    'strap_path': dict(labels=[], special='strap_path'),
    's1_swd': dict(step=1, title='Flash and test the bare board', labels=[
        ('board', 'Bare board, top up', 'L'), ('pins', 'Five pogo pins on TP1-TP5\n(underside test pads)', 'R'),
        ('jig', 'SWD jig', 'L'), ('wires', 'To the Pico / Debug Probe\nTP2 SWDIO, TP3 SWDCLK, TP5 GND, TP1 3V3', 'R'),
        ('press', 'Hold it down with a finger\nwhile flashing', 'R')],
        arrows=[('arrow', 'board_from', 'board_to')]),
    's2_cell': dict(step=2, title='Solder the cell leads', labels=[
        ('vbat', 'J2 +  (VBAT)\nred lead', 'L'), ('gnd', 'J2 -  (GND)\nblack lead', 'L'),
        ('kapton', 'Kapton tape over both joints', 'R'), ('cell', 'Cell, beyond the J1 edge', 'L'),
        ('board', 'Board, bottom side up', 'R')],
        note='In step 5 the cell folds over the J1 edge onto the top of the board.'),
    's3_bond': dict(step=3, title='Bond the flex in the jig', labels=[
        ('flex', '1  Flex pads-down, its holes over the pins', (70, 150, 'mt')),
        ('dots', '2  Foam dots into every pocket\n(3 per pod, 7 in the base)', (-60, -200, 'mb')),
        ('pod5', '3  Turn the pod over, press it into\nits fence until it stops', (330, 330, 'mt')),
        ('base', '4  Base last: the tail goes up\nthrough its floor slot', 'L'),
        ('tail', 'Tail', 'L')],
        arrows=[('arrow', 'pod5_from', 'pod5_to')],
        numbers=['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'n7', 'n8']),
    's4_fold': dict(step=4, title='Book-fold the tail into J1', labels=[
        ('tail', 'Tail: gold fingers toward the board\n(the DOWN marker side)', 'L'),
        ('j1', 'J1 (drawn see-through): latch up, push the\ntail in square until it stops, latch down', 'R'),
        ('base', 'Module base (flex bonded in step 3)', 'L'),
        ('board', 'Board, upright', 'R')],
        arrows=[('path', 'fold')],
        note='Then fold the board down onto the base like closing a book.'),
    's5_close': dict(step=5, title='Seat the board, cell and lid', labels=[
        ('cell', 'Cell: lead end toward J1, flat on the board\n401120 cell: add the printed spacer', 'L'),
        ('cap', 'Button cap: stem down onto SW1', 'R'),
        ('lid', 'Lid: press until all four catches click\n(its ribs cage the cell)', 'R'),
        ('base', 'Folded board in the base', 'L')],
        arrows=[('arrow', 'cell_down', 'cell_land'), ('arrow', 'lid_down', 'lid_land')]),
    's6_strap': dict(step=6, title='Webbing and slides: set the length', labels=[
        ('slide', 'Slide on the hidden bar\n(swings out in line with the band)', 'L'),
        ('webbing', 'Webbing over the friction bar', 'L'),
        ('tail_mid', 'Tail tucked under the bar\n(hidden here)', 'L'),
        ('pod2', 'Pod 2', 'L'), ('module', 'Module', 'L')],
        special='slide_inset'),
    's7_wear': dict(step=7, title='First wear and signal check', labels=[
        ('module', 'Module on the back of the wrist', 'L'),
        ('cap', 'Button toward the thumb', 'R'),
        ('slide', 'Snug, not tight: set at the slides', 'R'),
        ('pod', 'Pods on the skin all round', 'L')],
        arrows=[('arrow', 'slip_from', 'slip_to')],
        note='Slip it over the hand like a bracelet; the gap between pods 1 and 8 opens.'),
    's8_charge': dict(step=8, title='Charging with the clip', labels=[
        ('clip', 'Charge clip (drawn see-through)', 'L'),
        ('pins', 'Two pogo pins on the charge pads', 'L'),
        ('key', 'Key fits the pry notch: one way only', 'R'),
        ('hook', 'Hook over the lid edge', 'R'),
        ('usb', 'USB 5 V lead: red to the pin\nnearer the cable exit', 'R')],
        arrows=[('arrow', 'clip_from', 'clip_to')],
        note='Band off the wrist. LED solid while charging.'),
}


def _fonts(k):
    from PIL import ImageFont
    f = lambda n, s: ImageFont.truetype(os.path.join(FONT_DIR, n), max(8, int(s * k)))
    return dict(lab=f('NotoSans-Medium.ttf', 30), sub=f('NotoSans-Regular.ttf', 24), num=f('NotoSans-Bold.ttf', 34),
                title=f('NotoSans-Medium.ttf', 36), note=f('NotoSans-Regular.ttf', 25), small=f('NotoSans-Bold.ttf', 24))


def _text_block(d, F, text):
    lines = text.split('\n')
    sizes = []
    for i, ln in enumerate(lines):
        f = F['lab'] if i == 0 else F['sub']
        bb = d.textbbox((0, 0), ln, font=f, anchor='la')
        sizes.append((bb[2] - bb[0], (bb[3] - bb[1]) if i == 0 else (bb[3] - bb[1])))
    return lines, sizes


def _arrow(d, p0, p1, k, col=ACC, width=7, head=26, both=False):
    x0, y0 = p0
    x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    hw = head * k
    d.line([(x0 + (ux * hw * 0.8 if both else 0), y0 + (uy * hw * 0.8 if both else 0)),
            (x1 - ux * hw * 0.8, y1 - uy * hw * 0.8)], fill=col, width=max(2, int(width * k)))
    for (ex, ey, sx, sy) in ([(x1, y1, ux, uy)] + ([(x0, y0, -ux, -uy)] if both else [])):
        d.polygon([(ex, ey), (ex - sx * hw - sy * hw * 0.5, ey - sy * hw + sx * hw * 0.5),
                   (ex - sx * hw + sy * hw * 0.5, ey - sy * hw - sx * hw * 0.5)], fill=col)


def _path_arrow(d, pts, k, col=ACC, width=7, head=26, both=False, heads_every=0):
    if len(pts) < 2:
        return
    d.line([tuple(p) for p in pts[:-1]], fill=col, width=max(2, int(width * k)), joint='curve')
    _arrow(d, pts[-2], pts[-1], k, col, width, head)
    if both:
        _arrow(d, pts[1], pts[0], k, col, width, head)
    if heads_every:
        for i in range(heads_every, len(pts) - 2, heads_every):
            _arrow(d, pts[i - 1], pts[i], k, col, width, head * 0.85)


def _halo_text(im, xy, text, font, fill, anchor='la', halo=HALO, r=4):
    from PIL import ImageDraw
    ImageDraw.Draw(im).text(xy, text, font=font, fill=fill, anchor=anchor, stroke_width=r, stroke_fill=halo + (235,))


def _highlight(im, mask_path, k):
    from PIL import Image, ImageFilter, ImageChops
    m = Image.open(mask_path).convert('RGBA')
    if m.size != im.size:
        m = m.resize(im.size)
    a = m.split()[3].point(lambda v: 255 if v > 100 else 0)
    r, g, b, _ = m.split()
    a = ImageChops.multiply(a, r.point(lambda v: 255 if v > 100 else 0))
    big = a.filter(ImageFilter.MaxFilter(2 * int(3 * k) + 1))
    ring = ImageChops.subtract(big, a).filter(ImageFilter.GaussianBlur(0.8 * k))
    glow = ImageChops.subtract(big.filter(ImageFilter.GaussianBlur(5 * k)), a).point(lambda v: int(v * 0.5))
    im.paste(Image.new('RGBA', im.size, ACC + (255,)), (0, 0), glow)
    im.paste(Image.new('RGBA', im.size, ACC + (255,)), (0, 0), ring)


def _strap_path(im, d, meta, k, F):
    P = meta['pts']
    loop = meta['paths'].get('loop', [])
    _path_arrow(d, loop, k, heads_every=6)
    for n in (1, 2, 5, 6, 7, 8):
        key = 'pod%d' % n
        if key in P:
            x, y = P[key]
            r = 22 * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 248, 244), outline=INK, width=max(1, int(2 * k)))
            d.text((x, y + 1), str(n), font=F['small'], fill=INK, anchor='mm')
    for key, txt in (('slideA', 'A'), ('slideB', 'B')):
        if key in P:
            x, y = P[key]
            r = 24 * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=ACC, outline=(255, 255, 255), width=max(1, int(2 * k)))
            d.text((x, y + 1), txt, font=F['small'], fill=(255, 255, 255), anchor='mm')
    out = []
    if 'slideA' in P:
        out.append((P['slideA'], 'Start: slide A, by pod 2\nthe end locked round its friction bar', 'R'))
    if 'slideB' in P:
        out.append((P['slideB'], 'End: slide B, by pod 5\nlocked the same way', 'L'))
    if 'gap' in P:
        out.append((P['gap'], 'Gap between pods 1 and 8:\nopens to slip over the hand', 'R'))
    if 'module' in P:
        out.append((P['module'], 'Module (pods 3 and 4 under it)', (0, -120, 'mb')))
    return out


def _slide_inset(im, d, k, F):
    """2D side section of a slide (bottom-right corner), in the slide's own frame (hinge left, friction
    bar right, outward up), positions to scale, strands drawn a little thinner: the locking path."""
    import math as m
    W, H = im.size
    s = 24 * k                                        # px per mm
    bw, bh = 640 * k, 440 * k
    x0, y0 = W - bw - 30 * k, H - bh - 40 * k
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=16 * k, fill=(247, 245, 241), outline=(196, 192, 186),
                        width=max(1, int(2 * k)))
    d.text((x0 + 20 * k, y0 + 14 * k), 'How the webbing locks (side section)', font=F['sub'], fill=SUB, anchor='la')
    ox, oy = x0 + 92 * k, y0 + 168 * k

    def P(u, v):
        return (ox + u * s, oy - v * s)

    def thick(pts, col, w):
        q = [P(*x) for x in pts]
        d.line(q, fill=col, width=w)
        for x, y in q:
            d.ellipse([x - w / 2 + 0.5, y - w / 2 + 0.5, x + w / 2 - 0.5, y + w / 2 - 0.5], fill=col)

    def arc(cu, cv, r, a0, a1, n=24):
        return [(cu + r * m.cos(m.radians(a0 + (a1 - a0) * i / n)), cv + r * m.sin(m.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    dark, mid, web, tail_c = (62, 62, 66), (170, 170, 170), (40, 52, 82), (112, 130, 172)
    wv = int(1.1 * s)
    sw = 41.0                                         # the slide swings until the loaded strand points at the hinge
    tip = (4.3, -2.75)
    tp = (tip[0] + 0.75 * m.cos(m.radians(270 - sw)), tip[1] + 0.75 * m.sin(m.radians(270 - sw)))
    far = (tp[0] + 5.5 * m.cos(m.radians(-sw)), tp[1] + 5.5 * m.sin(m.radians(-sw)))
    inc = [far, tp] + arc(tip[0], tip[1], 0.75, 270 - sw - 360, -164.4)[1:]
    inc += [(3.05, -1.05)] + arc(4.3, -0.7, 1.3, 195.6, 180)[1:] + [(3.0, 0.7)] + arc(4.3, 0.7, 1.3, 180, 90)[1:] + [(5.5, 2.0)]
    tl = arc(5.5, 0.7, 1.3, 90, 0) + [(6.8, -0.7)] + arc(5.5, -0.7, 1.3, 0, -90)[1:] + [(4.3, -2.0)]
    r_o, r_i = 1.9 * s, 0.9 * s
    c = P(0, 0)
    d.pieslice([c[0] - r_o, c[1] - r_o, c[0] + r_o, c[1] + r_o], start=-(89 - 40), end=360 - (89 + 40), fill=dark)
    d.ellipse([c[0] - r_i, c[1] - r_i, c[0] + r_i, c[1] + r_i], fill=(247, 245, 241))
    d.ellipse([c[0] - 0.65 * s, c[1] - 0.8 * s, c[0] + 0.65 * s, c[1] + 0.8 * s], fill=mid)
    d.rounded_rectangle([*P(3.8, 1.2), *P(6.0, -1.2)], radius=0.5 * s, fill=dark)
    thick(tl, tail_c, wv)
    thick(inc, web, wv)
    _arrow(d, P(6.6, -3.9), P(4.75, -3.05), k, width=4, head=14)
    _arrow(d, P(8.4, -7.1), P(9.6, -8.15), k, col=SUB, width=3, head=12)
    f = F['sub']
    d.text(P(-2.4, 3.3), 'slide clip', font=f, fill=SUB, anchor='lb')
    d.text(P(-2.4, -2.3), 'hidden bar\n(module)', font=f, fill=SUB, anchor='la', spacing=2)
    d.text(P(3.1, 3.9), 'friction bar', font=f, fill=SUB, anchor='lb')
    d.text(P(7.8, 1.7), 'tail: round the end,\nback under the bar,\ntip at the slot', font=f, fill=tail_c, anchor='la', spacing=2)
    d.text(P(-2.4, -8.7), 'pull on the band and the strand pinches the tip harder', font=f, fill=ACC, anchor='la')
    d.text(P(6.8, -3.5), 'tail tip, pinched', font=f, fill=ACC, anchor='la')
    d.text(P(9.2, -5.6), 'from the pods\n(loaded)', font=f, fill=SUB, anchor='la', spacing=2)


def annotate(name, src, dst):
    from PIL import Image, ImageDraw
    raw = os.path.join(src, name + '.png')
    meta = json.load(open(os.path.join(src, name + '.json')))
    spec = SPEC.get(name, {})
    im = Image.open(raw).convert('RGBA')
    if im.size[0] != RES[0]:
        im = im.resize(RES, Image.LANCZOS)
        sx = RES[0] / meta['size'][0]
        meta['pts'] = {kk: [v[0] * sx, v[1] * sx] for kk, v in meta['pts'].items()}
        meta['paths'] = {kk: [[p[0] * sx, p[1] * sx] for p in v] for kk, v in meta['paths'].items()}
    W, H = im.size
    k = W / 1600.0
    F = _fonts(k)
    if meta.get('mask') and os.path.exists(os.path.join(src, meta['mask'])):
        _highlight(im, os.path.join(src, meta['mask']), k)
    d = ImageDraw.Draw(im)
    P = meta['pts']
    for ar in spec.get('arrows', []):
        if ar[0] in ('arrow', 'darrow') and ar[1] in P and ar[2] in P:
            _arrow(d, P[ar[1]], P[ar[2]], k, both=ar[0] == 'darrow')
        elif ar[0] == 'path' and ar[1] in meta['paths']:
            _path_arrow(d, meta['paths'][ar[1]], k, both=len(ar) > 2)
    labels = [(P[a], t, pl) for a, t, pl in spec.get('labels', []) if a in P]
    if spec.get('special') == 'strap_path':
        labels += _strap_path(im, d, meta, k, F)
    if spec.get('special') == 'slide_inset':
        _slide_inset(im, d, k, F)
    for key in spec.get('numbers', []):
        if key in P:
            x, y = P[key]
            r = 20 * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 248, 244), outline=INK, width=max(1, int(2 * k)))
            d.text((x, y + 1), key[1:], font=F['small'], fill=INK, anchor='mm')
    # columns: de-overlap labels on each side
    margin = 34 * k
    top0 = (130 if spec.get('step') else 40) * k
    for side in ('L', 'R'):
        items = sorted([l for l in labels if l[2] == side], key=lambda l: l[0][1])
        hs = []
        for p, t, _ in items:
            lines, sizes = _text_block(d, F, t)
            hs.append(sum(sz[1] for sz in sizes) + 12 * k * (len(lines) - 1))
        ys = [min(max(p[1] - h / 2, top0), H - 60 * k - h) for (p, t, _), h in zip(items, hs)]
        for _ in range(60):
            for i in range(1, len(ys)):
                if ys[i] < ys[i - 1] + hs[i - 1] + 26 * k:
                    ys[i] = ys[i - 1] + hs[i - 1] + 26 * k
            over = ys[-1] + hs[-1] - (H - 40 * k) if ys else 0
            if over > 0:
                ys = [y - over for y in ys]
            for i in range(len(ys) - 2, -1, -1):
                if ys[i + 1] < ys[i] + hs[i] + 26 * k:
                    ys[i] = ys[i + 1] - hs[i] - 26 * k
            if ys and ys[0] < top0:
                ys = [y + (top0 - ys[0]) for y in ys]
        for (p, t, _), y, h in zip(items, ys, hs):
            lines, sizes = _text_block(d, F, t)
            wmax = max(sz[0] for sz in sizes)
            if side == 'L':
                tx, anchor_x, lx = margin, 'la', margin + wmax + 14 * k
            else:
                tx, anchor_x, lx = W - margin, 'ra', W - margin - wmax - 14 * k
            ly = y + sizes[0][1] / 2 + 6 * k
            d.line([(lx, ly), (p[0], p[1])], fill=INK + (230,), width=max(1, int(3 * k)))
            yy = y
            for i, ln in enumerate(lines):
                _halo_text(im, (tx, yy), ln, F['lab'] if i == 0 else F['sub'], INK if i == 0 else SUB, anchor=anchor_x)
                yy += sizes[i][1] + 12 * k
            d = ImageDraw.Draw(im)
    for p, t, pl in labels:
        if pl in ('L', 'R'):
            continue
        dx, dy = pl[0] * k, pl[1] * k
        anc = pl[2] if len(pl) > 2 else 'lm'
        tx, ty = p[0] + dx, p[1] + dy
        d.line([(p[0], p[1]), (tx, ty + (14 * k if anc == 'mb' else 0))], fill=INK + (230,), width=max(1, int(3 * k)))
        lines = t.split('\n')
        yy = ty - (len(lines) - 1) * 36 * k if anc == 'mb' else ty
        for i, ln in enumerate(lines):
            _halo_text(im, (tx + (10 * k if anc[0] == 'l' else 0), yy), ln, F['lab'] if i == 0 else F['sub'], INK if i == 0 else SUB,
                       anchor={'lm': 'lm', 'rm': 'rm', 'mb': 'ms', 'mt': 'mt'}.get(anc, 'lm'))
            yy += 36 * k
        d = ImageDraw.Draw(im)
    # anchor dots last (on top of the leaders)
    for p, t, pl in labels:
        r = 6 * k
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(255, 255, 255), outline=INK, width=max(1, int(2.5 * k)))
    if spec.get('step'):
        r = 34 * k
        cx, cy = 34 * k + r, 34 * k + r
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACC)
        d.text((cx, cy + 1), str(spec['step']), font=F['num'], fill=(255, 255, 255), anchor='mm')
        _halo_text(im, (cx + r + 20 * k, cy), spec['title'], F['title'], INK, anchor='lm')
    if spec.get('note'):
        _halo_text(im, (34 * k, H - 34 * k), spec['note'], F['note'], SUB, anchor='ls')
    im.convert('RGB').save(dst, quality=88, optimize=True)


# ================================================================ driver
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only', default='')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--samples', type=int, default=0)
    ap.add_argument('--gpus', default='0,1')
    ap.add_argument('--annotate-only', action='store_true')
    ap.add_argument('--xsec', action='store_true', help='rebuild render/build/guide_xsec.glb')
    a = ap.parse_args()
    os.makedirs(LOGS, exist_ok=True)
    figs = a.only.split(',') if a.only else FIGS
    src = os.path.join(BUILD, 'guide_quick' if a.quick else 'guide')
    t = time.time()
    if not a.annotate_only:
        xg = os.path.join(BUILD, 'guide_xsec.glb')
        if 'xsec' in figs and (a.xsec or not os.path.exists(xg)):
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', GUIDE_XSEC=xg)
            with open(os.path.join(LOGS, 'guide_xsec.log'), 'w') as f:
                subprocess.run([FREECAD, os.path.abspath(__file__)], stdout=f, stderr=subprocess.STDOUT, env=env, timeout=600)
        gpus = [int(g) for g in a.gpus.split(',')]
        cost = {'s7_wear': 3, 'exploded': 2, 'hero': 2}
        parts = [[] for _ in gpus]
        for n in sorted(figs, key=lambda n: -cost.get(n, 1)):
            j = min(range(len(gpus)), key=lambda i: sum(cost.get(x, 1) for x in parts[i]))
            parts[j].append(n)
        ps = []
        for g, part in zip(gpus, parts):
            if not part:
                continue
            cmd = [BLENDER, '-b', '--python', os.path.abspath(__file__), '--', '--figs', ','.join(part), '--out', src]
            if a.quick:
                cmd.append('--quick')
            if a.samples:
                cmd += ['--samples', str(a.samples)]
            ps.append(subprocess.Popen(cmd, stdout=open(os.path.join(LOGS, 'guide_gpu%d.log' % g), 'w'),
                                       stderr=subprocess.STDOUT, env=dict(os.environ, CUDA_VISIBLE_DEVICES=str(g))))
        for p in ps:
            p.wait(timeout=3600)
    dst = os.path.join(BUILD, 'guide_quick_out') if a.quick else IMG
    os.makedirs(dst, exist_ok=True)
    for n in figs:
        if os.path.exists(os.path.join(src, n + '.json')):
            annotate(n, src, os.path.join(dst, n + '.jpg'))
            print('  %s' % os.path.relpath(os.path.join(dst, n + '.jpg'), ROOT))
        else:
            print('  missing render for', n)
    if not a.quick and not a.only:
        keep = set(n + '.jpg' for n in FIGS)
        for f in glob.glob(os.path.join(IMG, '*')):
            if os.path.basename(f) not in keep:
                os.remove(f)
                print('  removed', os.path.relpath(f, ROOT))
    print('done in %.1f min' % ((time.time() - t) / 60))


if os.environ.get('GUIDE_XSEC') and 'FreeCAD' in sys.modules:
    freecad_xsec(os.environ['GUIDE_XSEC'])
    os._exit(0)
elif __name__ == '__main__':
    if 'bpy' in sys.modules or os.path.basename(sys.argv[0]).startswith('blender'):
        blender_main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    else:
        main()
