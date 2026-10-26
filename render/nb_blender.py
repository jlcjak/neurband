"""neurband product renders - Blender side (run by render/make_renders.py).

  blender -b --python render/nb_blender.py -- --shots hero_arm,pcb_top [--quick] [--save-blend]

Every shot rebuilds its scene from scratch from the GLBs in render/build/ (re-exported by
make_renders.py on each run) and the CC0 human base mesh, then renders render/out/<shot>.png.
Frames: the band GLBs use the mech/rev_c frame (X radial, Y along the arm toward the elbow,
Z dorsal; right arm, palm down), in metres. The human arm is moved into that frame.
"""
import bpy, bmesh, math, os, sys, json, time, argparse
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build')
OUT = os.path.join(HERE, 'out')
SCENES = os.path.join(HERE, 'scenes')
LIB = os.path.join(ROOT, 'extra/render_assets/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend')
BAND_Y = 0.025          # band centre line, 25 mm proximal of the wrist crease (mech/fitgeom.py)
WRIST_C = 0.160         # band_assembly.step is fitted on the 160 mm wrist
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    print('[nb]', s, flush=True)
    LOG.append(s)


# ----------------------------------------------------------------------------- basics
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def link(o, coll=None):
    (coll or bpy.context.scene.collection).objects.link(o)
    return o


def import_glb(path, bake=False):
    """Import a GLB; return {name: object} of mesh objects, parents cleared (world transform kept).
    bake=True moves the world transform into (single-user) mesh data."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    mws = {o: o.matrix_world.copy() for o in meshes}
    for o in meshes:
        o.parent = None
        o.matrix_world = mws[o]
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    if bake:
        for o in meshes:
            if o.data.users > 1:
                o.data = o.data.copy()
            o.data.transform(o.matrix_world)
            o.matrix_world = Matrix.Identity(4)
    return {o.name: o for o in meshes}


def kind(name):
    """'pod_shells_003' -> 'pod_shells'"""
    p = name.split('.')[0].rsplit('_', 1)
    return p[0] if len(p) == 2 and p[1].isdigit() else name.split('.')[0]


def verts_np(o, world=True):
    a = np.empty(len(o.data.vertices) * 3)
    o.data.vertices.foreach_get('co', a)
    a = a.reshape(-1, 3)
    if world:
        M = np.array(o.matrix_world)
        a = a @ M[:3, :3].T + M[:3, 3]
    return a


def bbox(objs):
    pts = np.vstack([verts_np(o) for o in objs if o.type == 'MESH' and len(o.data.vertices)])
    return pts.min(0), pts.max(0)


def smooth(o, angle=None):
    """smooth shading; with an angle, edges sharper than it stay sharp (CAD parts)."""
    if o.data.has_custom_normals:
        return
    o.data.shade_smooth()
    if angle is not None:
        o.data.set_sharp_from_angle(angle=angle)


def kabsch(P, Q):
    """rigid R, t with R @ P + t ~= Q (rows are points)."""
    cp, cq = P.mean(0), Q.mean(0)
    H = (P - cp).T @ (Q - cq)
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1, 1, d])
    R = Vt.T @ D @ U.T
    t = cq - R @ cp
    M = Matrix.Identity(4)
    for i in range(3):
        for j in range(3):
            M[i][j] = R[i, j]
        M[i][3] = t[i]
    rms = float(np.sqrt(((P @ R.T + t - Q) ** 2).sum(1).mean()))
    return M, rms


# ----------------------------------------------------------------------------- materials
MATS = {}


def principled(name, base=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, **kw):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    names = {i.name.lower().replace(' ', '_'): i.name for i in b.inputs}
    for k, v in kw.items():
        if k in names:
            b.inputs[names[k]].default_value = v
        else:
            log('no input', k)
    MATS[name] = m
    return m


def bsdf(m):
    return m.node_tree.nodes.get('Principled BSDF')


def add_bump(m, scale=2000.0, strength=0.1, distance=0.0001, detail=2.0, kind='noise', coord='Object',
             wave_dir='Y', extra=None):
    """procedural micro surface on a material (object-space so it scales with real size)."""
    nt = m.node_tree
    b = bsdf(m)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    if kind == 'noise':
        t = nt.nodes.new('ShaderNodeTexNoise')
        t.inputs['Scale'].default_value = scale
        t.inputs['Detail'].default_value = detail
        nt.links.new(tc.outputs[coord], t.inputs['Vector'])
        out = t.outputs['Fac']
    elif kind == 'voronoi':
        t = nt.nodes.new('ShaderNodeTexVoronoi')
        t.feature = 'F1'
        t.inputs['Scale'].default_value = scale
        nt.links.new(tc.outputs[coord], t.inputs['Vector'])
        out = t.outputs['Distance']
    elif kind == 'wave':                              # knit / webbing ribs
        t = nt.nodes.new('ShaderNodeTexWave')
        t.wave_type = 'BANDS'
        t.bands_direction = wave_dir
        t.inputs['Scale'].default_value = scale
        t.inputs['Distortion'].default_value = 2.0
        t.inputs['Detail'].default_value = 1.0
        nt.links.new(tc.outputs[coord], t.inputs['Vector'])
        out = t.outputs['Fac']
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = distance
    nt.links.new(out, bp.inputs['Height'])
    if extra is not None:                             # chain a second bump
        nt.links.new(extra, bp.inputs['Normal'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    for name in ('Coat Normal',):
        pass
    return bp.outputs['Normal']


def rough_var(m, lo, hi, scale=300.0, detail=3.0):
    """noise-driven roughness variation (micro-roughness) in object space."""
    nt = m.node_tree
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = detail
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.3
    mr.inputs['From Max'].default_value = 0.7
    mr.inputs['To Min'].default_value = lo
    mr.inputs['To Max'].default_value = hi
    nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], bsdf(m).inputs['Roughness'])


def mat_housing(variant='graphite'):
    """MJF PA12: matte, bead-blasted grain, slightly varying micro-roughness."""
    name = 'PA12_' + variant
    if name in MATS:
        return MATS[name]
    if variant == 'graphite':
        m = principled(name, (0.032, 0.033, 0.036), 0.6, sheen_weight=0.3, sheen_roughness=0.45,
                       specular_ior_level=0.42)
        rough_var(m, 0.52, 0.68, scale=900.0)
    else:                                             # bone white MJF PA12 (dyed / natural light)
        m = principled(name, (0.70, 0.67, 0.61), 0.62, subsurface_weight=0.15,
                       subsurface_radius=(1.0, 0.8, 0.6), subsurface_scale=0.0006, specular_ior_level=0.4)
        rough_var(m, 0.55, 0.7, scale=900.0)
    n1 = add_bump(m, scale=9000.0, strength=0.22, distance=0.00003, detail=3.0)    # MJF grain
    add_bump(m, scale=1800.0, strength=0.05, distance=0.00008, detail=2.0, extra=n1)
    return m


def mat_xray():
    """clear resin housing (SLA clear, polished) for the x-ray shot."""
    if 'xray' in MATS:
        return MATS['xray']
    m = principled('xray', (0.90, 0.94, 1.0), 0.05, transmission_weight=1.0, ior=1.5,
                   specular_ior_level=0.5)
    return m


def mat_pod():
    """satin TPU / charcoal elastomer."""
    if 'pod' in MATS:
        return MATS['pod']
    m = principled('pod', (0.024, 0.024, 0.026), 0.38, sheen_weight=0.12, sheen_roughness=0.4,
                   specular_ior_level=0.5, coat_weight=0.1, coat_roughness=0.35)
    rough_var(m, 0.33, 0.45, scale=700.0)
    add_bump(m, scale=7000.0, strength=0.06, distance=0.00002, detail=2.0)
    return m


def _math(nt, op, a, b=None, v=None):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    for i, x in enumerate((a, b)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = x
        else:
            nt.links.new(x, n.inputs[i])
    return n.outputs[0]


def mat_strap():
    """woven elastic webbing: plain weave from the 'weave' attribute (s along the strap, t across),
    fine fibre noise, dark fabric with sheen."""
    if 'strap' in MATS:
        return MATS['strap']
    m = principled('strap', (0.030, 0.030, 0.032), 0.78, sheen_weight=0.7, sheen_roughness=0.3,
                   sheen_tint=(0.75, 0.75, 0.78, 1), specular_ior_level=0.35)
    nt = m.node_tree
    b = bsdf(m)
    at = nt.nodes.new('ShaderNodeAttribute')
    at.attribute_name = 'weave'
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(at.outputs['Vector'], sep.inputs[0])
    P = 0.00055                                       # thread pitch 0.55 mm
    k = 2 * math.pi / P
    ws = _math(nt, 'SINE', _math(nt, 'MULTIPLY', sep.outputs['X'], k))
    wt = _math(nt, 'SINE', _math(nt, 'MULTIPLY', sep.outputs['Y'], k))
    weave = _math(nt, 'MULTIPLY', ws, wt)            # over/under interlacing
    rib = _math(nt, 'ABSOLUTE', _math(nt, 'SINE', _math(nt, 'MULTIPLY', sep.outputs['Y'], k / 2)))
    h = _math(nt, 'ADD', _math(nt, 'MULTIPLY', weave, 0.6), _math(nt, 'MULTIPLY', rib, 0.6))
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.55
    bp.inputs['Distance'].default_value = 0.00012
    nt.links.new(h, bp.inputs['Height'])
    # fibre fuzz on top
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 9000.0
    nz.inputs['Detail'].default_value = 2.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp2 = nt.nodes.new('ShaderNodeBump')
    bp2.inputs['Strength'].default_value = 0.2
    bp2.inputs['Distance'].default_value = 0.00003
    nt.links.new(nz.outputs['Fac'], bp2.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], bp2.inputs['Normal'])
    nt.links.new(bp2.outputs['Normal'], b.inputs['Normal'])
    # threads slightly lighter on the crowns
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (0.022, 0.022, 0.024, 1)
    mix.inputs['B'].default_value = (0.045, 0.045, 0.048, 1)
    nt.links.new(_math(nt, 'MULTIPLY_ADD', weave, 0.5, 0.5) if False else _math(nt, 'ADD', _math(nt, 'MULTIPLY', weave, 0.5), 0.5), mix.inputs['Factor'])
    nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])
    return m


def add_weave_attr(o, R=0.03):
    """s = arc length around the wrist axis (seam at the dorsal centre, under the module), t = y."""
    V = verts_np(o, world=False)
    th = np.mod(np.arctan2(V[:, 0], V[:, 2]), 2 * math.pi)
    W = np.stack([th * R, V[:, 1], np.zeros(len(V))], 1)
    at = o.data.attributes.new('weave', 'FLOAT_VECTOR', 'POINT')
    at.data.foreach_set('vector', W.ravel())


def mat_gold():
    return principled('enig', (0.92, 0.72, 0.40), 0.27, metal=1.0)


def mat_flex():
    if 'polyimide' in MATS:
        return MATS['polyimide']
    m = principled('polyimide', (0.50, 0.21, 0.025), 0.45, coat_weight=0.1, coat_roughness=0.3, specular_ior_level=0.3,
                   subsurface_weight=0.3, subsurface_radius=(1.0, 0.5, 0.2), subsurface_scale=0.0003)
    return m


def mat_foam():
    m = principled('foam', (0.015, 0.015, 0.016), 0.95)
    return m


def mat_lipo():
    if 'lipo' in MATS:
        return MATS['lipo']
    m = principled('lipo', (0.62, 0.63, 0.65), 0.42, metal=1.0)
    add_bump(m, scale=600.0, strength=0.08, distance=0.0002, detail=1.0)
    return m


def mat_skin():
    """skin: random-walk SSS kept short (not waxy), mottled albedo, redness from the 'redness'
    vertex attribute (knuckles, fingertips, wrist crease), pores + micro normal, varying roughness."""
    if 'skin' in MATS:
        return MATS['skin']
    m = principled('skin', (0.55, 0.37, 0.29), 0.5, subsurface_weight=1.0,
                   subsurface_radius=(1.0, 0.36, 0.16), subsurface_scale=0.0009, subsurface_anisotropy=0.8,
                   specular_ior_level=0.5)
    nt = m.node_tree
    b = bsdf(m)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')               # blotches (cm scale)
    nz.inputs['Scale'].default_value = 45.0
    nz.inputs['Detail'].default_value = 4.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[0].color = (0.49, 0.32, 0.25, 1)
    ramp.color_ramp.elements[1].color = (0.57, 0.39, 0.30, 1)
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    fr = nt.nodes.new('ShaderNodeTexNoise')               # freckle-scale speckle (mm)
    fr.inputs['Scale'].default_value = 900.0
    fr.inputs['Detail'].default_value = 2.0
    nt.links.new(tc.outputs['Object'], fr.inputs['Vector'])
    sp = nt.nodes.new('ShaderNodeMix')
    sp.data_type = 'RGBA'
    sp.blend_type = 'MULTIPLY'
    nt.links.new(_math(nt, 'MULTIPLY', _math(nt, 'GREATER_THAN', fr.outputs['Fac'], 0.62), 0.25), sp.inputs['Factor'])
    nt.links.new(ramp.outputs['Color'], sp.inputs['A'])
    sp.inputs['B'].default_value = (0.85, 0.72, 0.65, 1)
    at = nt.nodes.new('ShaderNodeAttribute')
    at.attribute_name = 'redness'
    red = nt.nodes.new('ShaderNodeMix')
    red.data_type = 'RGBA'
    nt.links.new(_math(nt, 'MULTIPLY', at.outputs['Fac'], 0.4), red.inputs['Factor'])
    nt.links.new(sp.outputs['Result'], red.inputs['A'])
    red.inputs['B'].default_value = (0.58, 0.27, 0.22, 1)
    nt.links.new(red.outputs['Result'], b.inputs['Base Color'])
    rough_var(m, 0.40, 0.58, scale=60.0, detail=4.0)
    n1 = add_bump(m, scale=2600.0, strength=0.09, distance=0.00015, kind='voronoi')      # pores
    n2 = add_bump(m, scale=9000.0, strength=0.05, distance=0.00004, detail=3.0, extra=n1)   # micro normal
    add_bump(m, scale=300.0, strength=0.05, distance=0.0004, detail=5.0, extra=n2)
    return m


def mat_paper(color=(0.5, 0.48, 0.45), rough=0.85):
    key = 'paper_%.3f_%.3f_%.3f' % color
    if key in MATS:
        return MATS[key]
    m = principled(key, color, rough)
    add_bump(m, scale=400.0, strength=0.04, distance=0.0005, detail=4.0)
    return m


def mat_plaster(color=(0.62, 0.60, 0.57)):
    key = 'plaster_%.3f' % color[0]
    if key in MATS:
        return MATS[key]
    m = principled(key, color, 0.9)
    add_bump(m, scale=250.0, strength=0.12, distance=0.0006, detail=6.0)
    return m


def setmat(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)


# ----------------------------------------------------------------------------- band
BAND_MAT = {
    'module_base': 'housing', 'module_lid': 'housing', 'pod_shells': 'pod', 'strap_buckle': 'pod',
    'flex': 'flex', 'flex_pods_3_4': 'flex', 'tail': 'flex', 'pads': 'gold', 'foam': 'foam',
    'strap_long': 'strap', 'strap_short': 'strap', 'strap_loops': 'strap', 'lipo': 'lipo',
    'magnets': 'nickel', 'strap_bars': 'nylon', 'light_pipe': 'pmma', 'main_board': 'fr4',
    'board_parts': 'black', 'button_cap': 'housing', 'strap': 'strap', 'strap_loop': 'pod',
}
MODULE_KINDS = {'module_base', 'module_lid', 'main_board', 'board_parts', 'lipo', 'light_pipe',
                'magnets', 'strap_bars'}


def in_module(k):
    """parts that move rigidly with the module (incl. hidden spring bars in the lugs)."""
    return k in MODULE_KINDS or band_class(k) in ('housing', 'steel', 'lipo', 'nickel', 'pmma')


def band_class(k):
    """material class of a band part from its STEP name (robust to renamed / new parts)."""
    if k in BAND_MAT:
        return BAND_MAT[k]
    n = k.lower()
    for keys, cls in ((('lid', 'base', 'housing', 'module'), 'housing'), (('buckle', 'ring', 'keeper'), 'pod'),
                      (('spring', 'bar', 'pin'), 'steel'), (('strap', 'band', 'webbing', 'weave'), 'strap'),
                      (('pad', 'electrode', 'gold'), 'gold'), (('flex', 'tail', 'fpc'), 'flex'), (('foam',), 'foam'),
                      (('pod',), 'pod'), (('lipo', 'cell', 'battery'), 'lipo'), (('magnet',), 'nickel'),
                      (('pipe',), 'pmma')):
        if any(x in n for x in keys):
            return cls
    return 'black'


def is_strap(k):
    return band_class(k) == 'strap'


def band_material(k, housing='graphite'):
    return {
        'steel': lambda: principled('steel', (0.75, 0.75, 0.76), 0.22, metal=1.0),
        'housing': lambda: mat_housing(housing), 'pod': mat_pod, 'flex': mat_flex, 'gold': mat_gold,
        'foam': mat_foam, 'strap': mat_strap, 'lipo': mat_lipo,
        'nickel': lambda: principled('nickel', (0.72, 0.71, 0.68), 0.18, metal=1.0),
        'nylon': lambda: principled('nylon', (0.75, 0.74, 0.70), 0.45),
        'pmma': lambda: principled('pmma', (1, 1, 1), 0.05, transmission_weight=1.0, ior=1.49),
        'fr4': lambda: principled('fr4ph', (0.02, 0.02, 0.02), 0.4),
        'black': lambda: principled('blackplastic', (0.02, 0.02, 0.02), 0.45),
    }[band_class(k)]()


def load_band(path=None, housing='graphite'):
    objs = import_glb(path or os.path.join(BUILD, 'band_assembly.glb'), bake=True)
    for o in objs.values():
        k = kind(o.name)
        o['kind'] = k
        if is_strap(k):
            add_weave_attr(o)
        setmat(o, band_material(k, housing))
        smooth(o, math.radians(35))
    return objs


def load_module(housing='graphite'):
    objs = import_glb(os.path.join(BUILD, 'module_assy.glb'), bake=True)
    for o in objs.values():
        k = kind(o.name)
        o['kind'] = k
        setmat(o, band_material(k, housing))
        smooth(o, math.radians(35))
    return objs


# ----------------------------------------------------------------------------- PCB
def _lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def pcb_materials(objs, flex=False):
    """replace KiCad GLB materials with physically plausible ones."""
    soldermask = MATS.get('soldermask') or principled(
        'soldermask', (0.012, 0.012, 0.013), 0.32, coat_weight=0.6, coat_roughness=0.12,
        specular_ior_level=0.5, alpha=0.93)
    if flex:
        soldermask = principled('coverlay', (0.36, 0.13, 0.012), 0.25, coat_weight=0.6, coat_roughness=0.06,
                                subsurface_weight=0.2, subsurface_radius=(1.0, 0.4, 0.1), subsurface_scale=0.0003)
    fr4 = principled('fr4', (0.33, 0.30, 0.18), 0.6, subsurface_weight=0.2, subsurface_radius=(1, 0.8, 0.4),
                     subsurface_scale=0.0005) if not flex else mat_flex()
    silk = principled('silk', (0.85, 0.85, 0.83), 0.7)
    enig = mat_gold()
    tin = principled('tin', (0.80, 0.80, 0.78), 0.28, metal=1.0)
    blackp = principled('epoxy', (0.018, 0.018, 0.02), 0.42)
    ceramic = principled('ceramic', (0.16, 0.10, 0.06), 0.45)
    cache = {}
    for o in objs.values():
        new = []
        for i, m in enumerate(o.data.materials):
            if m is None:
                new.append(blackp)
                continue
            if m.name in cache:
                new.append(cache[m.name])
                continue
            b = m.node_tree.nodes.get('Principled BSDF') if m.node_tree else None
            c = tuple(b.inputs['Base Color'].default_value)[:3] if b else (0.1, 0.1, 0.1)
            met = b.inputs['Metallic'].default_value if b else 0
            ro = b.inputs['Roughness'].default_value if b else 1
            al = b.inputs['Alpha'].default_value if b else 1
            mx, mn = max(c), min(c)
            sat = (mx - mn) / mx if mx > 1e-4 else 0
            board_level = not (met == 1.0 and ro == 1.0)        # KiCad board items carry real PBR values
            if board_level:
                if met > 0.5:
                    r = enig                                   # exposed copper -> ENIG
                elif mn > 0.85:
                    r = silk
                elif al < 0.99:
                    r = soldermask
                else:
                    r = fr4
            else:                                              # component models (VRML colours)
                nm = o.name.lower()
                if 'cream' in nm or 'flipbar' in nm:
                    r = principled('fpc_actuator', (0.55, 0.48, 0.30), 0.55)
                elif _lum(c) < 0.08:
                    r = blackp
                elif sat < 0.2:
                    r = tin
                elif c[0] > c[1] > c[2] and sat > 0.5 and _lum(c) > 0.25:
                    r = enig
                elif c[1] > c[0] and c[1] > c[2]:
                    r = principled('led', (0.85, 0.95, 0.85), 0.1, transmission_weight=0.8)
                else:
                    r = ceramic
            cache[m.name] = r
            new.append(r)
        o.data.materials.clear()
        for r in new:
            o.data.materials.append(r)


def load_board(path=None, flex=False):
    path = path or os.path.join(BUILD, 'main_board.glb')
    objs = import_glb(path, bake=False)
    pcb_materials(objs, flex=flex)
    for o in objs.values():
        smooth(o, math.radians(30))
    # board body: the largest non-metal object starting at z ~ 0
    body = None
    best = 0
    for o in objs.values():
        mn, mx = bbox([o])
        a = (mx[0] - mn[0]) * (mx[1] - mn[1])
        if o.data.materials and o.data.materials[0].name in ('fr4', 'polyimide') and a > best:
            best, body = a, o
    return objs, body


def place_board_in_module(board_objs, body, module_objs):
    """KiCad GLB (x, -y, z) -> module frame: align the board-body bbox min with the placeholder's."""
    ph = [o for o in module_objs.values() if o['kind'] == 'main_board']
    pmin, pmax = bbox(ph)
    bmin, bmax = bbox([body])
    off = Matrix.Translation(Vector(pmin - bmin))
    for o in board_objs.values():
        o.matrix_world = off @ o.matrix_world
    log('board placed: placeholder', np.round(pmin * 1000, 2), np.round(pmax * 1000, 2),
        'kicad body size', np.round((bmax - bmin) * 1000, 2))
    return off


def module_to_band(module_objs, band_objs):
    """rigid transform module frame -> band frame from a part present in both GLBs."""
    for k in ('lipo', 'main_board', 'magnets', 'light_pipe'):
        a = [o for o in module_objs.values() if o['kind'] == k]
        b = [o for o in band_objs.values() if o['kind'] == k]
        if len(a) == 1 and len(b) == 1 and len(a[0].data.vertices) == len(b[0].data.vertices):
            M, rms = kabsch(verts_np(a[0]), verts_np(b[0]))
            if rms < 2e-5:
                log('module->band via', k, 'rms %.4f mm' % (rms * 1000))
                return M
    raise RuntimeError('module->band transform not found')


# ----------------------------------------------------------------------------- human arm
def _hull_perimeter(P):
    P = sorted(set(map(tuple, np.round(P, 6))))
    if len(P) < 3:
        return 0.0

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    H = np.array(lo[:-1] + up[:-1])
    return float(np.sum(np.linalg.norm(H - np.roll(H, 1, 0), axis=1)))


def _sections(A, c, ax, ts, half=0.0025, rmax=0.08):
    e1 = np.cross(ax, [0, 1, 0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)
    t = (A - c) @ ax
    d = A - c - np.outer(t, ax)
    r = np.linalg.norm(d, axis=1)
    out = []
    for tt in ts:
        S = A[(np.abs(t - tt) < half) & (r < rmax)]
        if len(S) < 8:
            out.append(None)
            continue
        P = np.stack([(S - c) @ e1, (S - c) @ e2], 1)
        per = _hull_perimeter(P)
        cen = c + tt * ax + P.mean(0)[0] * e1 + P.mean(0)[1] * e2
        w, v = np.linalg.eigh(np.cov((P - P.mean(0)).T))
        minor = v[0, 0] * e1 + v[1, 0] * e2
        out.append(dict(t=tt, per=per, cen=cen, minor=minor))
    return out


def build_arm(level=3, keep_prox=0.19, curl=65.0):
    """right forearm + hand of the CC0 realistic male base mesh, moved into the band frame and
    scaled so the wrist at the band centre is WRIST_C around."""
    with bpy.data.libraries.load(LIB, link=False) as (src, dst):
        dst.objects = ['GEO-body_male_realistic']
    body = dst.objects[0]
    link(body)
    body.parent = None
    body.location = (0, 0, 0)
    for m in body.modifiers:
        if m.type == 'MULTIRES':
            m.levels = m.render_levels = m.sculpt_levels = min(level, m.total_levels)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg))
    bpy.data.objects.remove(body)
    V = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', V); V = V.reshape(-1, 3)
    R0 = V[(V[:, 0] < -0.28) & (V[:, 2] > 0.88) & (V[:, 2] < 1.08)]
    c0 = R0.mean(0)
    ax = np.linalg.svd(R0 - c0, full_matrices=False)[2][0]
    if ax[2] < 0:
        ax = -ax
    A = V[(V[:, 0] < -0.25) & (V[:, 2] > 0.6)]
    secs = [s for s in _sections(A, c0, ax, np.arange(-0.15, -0.0, 0.005)) if s]
    smin = min(secs, key=lambda s: s['per'])
    tb = smin['t'] + 0.010
    # refine the axis on the band region: line through section centres
    sec2 = [s for s in _sections(A, c0, ax, tb + np.arange(-0.03, 0.06, 0.01)) if s]
    C = np.array([s['cen'] for s in sec2])
    cc = C.mean(0)
    ax2 = np.linalg.svd(C - cc, full_matrices=False)[2][0]
    if ax2 @ ax < 0:
        ax2 = -ax2
    O = cc + ((c0 + tb * ax) - cc) @ ax2 * ax2
    s_b = _sections(A, O, ax2, [0.0])[0]
    O = s_b['cen']
    dors = s_b['minor'] - (s_b['minor'] @ ax2) * ax2
    dors /= np.linalg.norm(dors)
    if dors[0] > 0:            # A-pose right arm: palm faces the thigh (+X), back of the hand -X
        dors = -dors
    rad = np.cross(ax2, dors)
    scale = WRIST_C / s_b['per']
    log('arm: wrist min per %.1f mm at t=%.3f; band at t=%.3f per %.1f mm -> scale %.3f; axis %s dorsal %s radial %s'
        % (smin['per'] * 1000, smin['t'], tb, s_b['per'] * 1000, scale, np.round(ax2, 3), np.round(dors, 3), np.round(rad, 3)))
    # crop: right arm only, up to keep_prox above the band
    t = (V - O) @ ax2
    d = V - O - np.outer(t, ax2)
    r = np.linalg.norm(d, axis=1)
    keep = (V[:, 0] < -0.25) & (r < np.where(t < -0.01, 0.16, 0.09)) & (t < keep_prox)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep[v.index]], context='VERTS')
    # into the band frame: X radial, Y proximal, Z dorsal, origin on the axis at y = BAND_Y
    Rm = np.stack([rad, ax2, dors])           # rows -> band axes
    M = Matrix.Identity(4)
    for i in range(3):
        for j in range(3):
            M[i][j] = Rm[i, j] * scale
    tvec = -(Rm @ O) * scale + np.array([0, BAND_Y, 0])
    for i in range(3):
        M[i][3] = tvec[i]
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    if curl:
        curl_fingers(me, curl)
    add_redness(me)
    arm = bpy.data.objects.new('arm', me)
    link(arm)
    smooth(arm)
    setmat(arm, mat_skin())
    return arm, dict(scale=scale, per=s_b['per'])


def curl_fingers(me, angle_deg=65.0, adduct=0.15):
    """relax the A-pose hand: bend everything distal of the knuckle line toward the palm (-Z) with
    constant curvature (more on the ulnar side), and close the finger spread a little."""
    n = len(me.vertices)
    V = np.empty(n * 3); me.vertices.foreach_get('co', V); V = V.reshape(-1, 3)
    ymin = V[:, 1].min()
    y0 = ymin + 0.092                       # MCP line ~ 9 cm from the middle fingertip
    near = np.abs(V[:, 1] - y0) < 0.003
    z0 = float(np.median(V[near, 2]))
    xm = float(np.median(V[near, 0]))
    u = y0 - V[:, 1]
    m = u > 0
    xs = V[:, 0] - xm
    ang = np.radians(angle_deg) * (1.0 + 0.35 * np.clip(-xs / 0.04, -1, 1))   # ulnar fingers curl more
    R = 0.092 / ang
    w = V[:, 2] - z0
    phi = u / R
    r = R + w
    un = r * np.sin(phi)
    wn = r * np.cos(phi) - R
    V[m, 1] = y0 - un[m]
    V[m, 2] = z0 + wn[m]
    k = np.clip(u / 0.06, 0, 1)
    V[m, 0] = xm + xs[m] * (1 - adduct * k[m])
    me.vertices.foreach_set('co', V.ravel())
    me.update()


def add_redness(me):
    """'redness' point attribute (0..1): convex bumps on the back of the hand (knuckles, finger
    joints), the palm and the wrist crease. Mesh is in the band frame (Z dorsal, crease at y ~ 0)."""
    n = len(me.vertices)
    V = np.empty(n * 3); me.vertices.foreach_get('co', V); V = V.reshape(-1, 3)
    N = np.empty(n * 3); me.vertex_normals.foreach_get('vector', N); N = N.reshape(-1, 3)
    E = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get('vertices', E); E = E.reshape(-1, 2)

    def nbmean(F):
        acc = np.zeros_like(F); deg = np.zeros(n)
        np.add.at(acc, E[:, 0], F[E[:, 1]]); np.add.at(acc, E[:, 1], F[E[:, 0]])
        np.add.at(deg, E[:, 0], 1); np.add.at(deg, E[:, 1], 1)
        return acc / np.maximum(deg, 1)[:, None] if F.ndim == 2 else acc / np.maximum(deg, 1)
    conv = ((V - nbmean(V)) * N).sum(1)
    hand = V[:, 1] < -0.02
    c = np.clip(conv / max(np.percentile(conv[hand], 96), 1e-9), 0, 1) * hand
    for _ in range(4):
        c = 0.5 * c + 0.5 * nbmean(c)
    c = np.clip(c * 1.6, 0, 1) * np.clip(N[:, 2] + 0.2, 0, 1)                 # dorsal side
    palm = 0.35 * np.clip(-N[:, 2], 0, 1) * (V[:, 1] < -0.01)
    crease = 0.45 * np.exp(-((V[:, 1] + 0.002) / 0.008) ** 2) * np.clip(-N[:, 2], 0, 1)
    r = np.clip(c + palm + crease, 0, 1)
    at = me.attributes.new('redness', 'FLOAT', 'POINT')
    at.data.foreach_set('value', r)


def _radii(bvh, ys, ths, rmax=0.08):
    R = np.full((len(ys), len(ths)), np.nan)
    for i, y in enumerate(ys):
        for j, th in enumerate(ths):
            d = Vector((math.sin(th), 0, math.cos(th)))
            hit = bvh.ray_cast(Vector((0, y, 0)), d, rmax)
            if hit[0] is not None:
                R[i, j] = hit[3]
    return R


def bvh_of(objs):
    vs, ps = [], []
    n = 0
    for o in objs:
        v = verts_np(o)
        vs.append(v)
        for p in o.data.polygons:
            ps.append([n + k for k in p.vertices])
        n += len(v)
    V = np.vstack(vs)
    return BVHTree.FromPolygons([tuple(x) for x in V], ps)


def fit_band_to_arm(band, arm):
    """radially warp the pod ring / strap so the band seated on the 160 mm CAD wrist sits the same
    way on this arm; the module and its internals move rigidly."""
    with_wrist = import_glb(os.path.join(BUILD, 'fit_160.glb'), bake=True)
    wrist = [o for o in with_wrist.values() if kind(o.name) == 'wrist']
    ys = np.arange(0.004, 0.0461, 0.003)
    ths = np.radians(np.arange(-180, 181, 3.0))
    Rw = _radii(bvh_of(wrist), ys, ths)
    Ra = _radii(bvh_of([arm]), ys, ths)
    for o in with_wrist.values():
        bpy.data.objects.remove(o)
    D = Ra - Rw
    D = np.where(np.isnan(D), np.nanmean(D), D)
    # smooth around the wrist a little (skin bumps should not wrinkle the strap)
    Ds = D.copy()
    for k in range(3):
        Ds = (np.roll(Ds, 1, 1) + 2 * Ds + np.roll(Ds, -1, 1)) / 4
    jm = np.abs(np.degrees(ths) - 15) < 4
    jp = np.abs(np.degrees(ths) + 15) < 4
    d0 = float(np.mean(D[:, jm | jp]))
    log('fit: arm-minus-model radius: module seat %.2f mm; ring min %.2f max %.2f mean %.2f mm'
        % (d0 * 1000, np.nanmin(D) * 1000, np.nanmax(D) * 1000, np.nanmean(D) * 1000))

    def interp(y, th):
        fi = np.clip((y - ys[0]) / (ys[1] - ys[0]), 0, len(ys) - 1.001)
        fj = np.clip((th - ths[0]) / (ths[1] - ths[0]), 0, len(ths) - 1.001)
        i0, j0 = fi.astype(int), fj.astype(int)
        a, b = fi - i0, fj - j0
        return ((1 - a) * (1 - b) * Ds[i0, j0] + a * (1 - b) * Ds[i0 + 1, j0]
                + (1 - a) * b * Ds[i0, j0 + 1] + a * b * Ds[i0 + 1, j0 + 1])
    for o in band.values():
        V = verts_np(o, world=False)
        if in_module(o['kind']):
            V[:, 2] += d0
        else:
            th = np.arctan2(V[:, 0], V[:, 2])
            dd = interp(V[:, 1], th)
            w = np.clip((np.abs(th) - math.radians(42)) / math.radians(25), 0, 1)
            w = w * w * (3 - 2 * w)
            V[:, 0] += w * dd * np.sin(th)
            V[:, 2] += w * dd * np.cos(th) + (1 - w) * d0
        o.data.vertices.foreach_set('co', V.ravel())
        o.data.update()
    # check: pads vs skin
    bv = bvh_of([arm])
    gaps = []
    for o in band.values():
        if band_class(o['kind']) == 'gold':
            c = verts_np(o).mean(0)
            th = math.atan2(c[0], c[2])
            hit = bv.ray_cast(Vector((0, c[1], 0)), Vector((math.sin(th), 0, math.cos(th))), 0.08)
            if hit[0] is not None:
                gaps.append(math.hypot(c[0], c[2]) - hit[3])
    if gaps:
        log('fit: pad centre minus skin radius: min %.2f max %.2f mm' % (min(gaps) * 1000, max(gaps) * 1000))
    return d0


# ----------------------------------------------------------------------------- stage
def setup_render(w, h, samples, quick, exposure=0.0, look='AgX - Medium High Contrast'):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'OPTIX'
    log('devices', [d.name for d in prefs.devices if d.use])
    sc.cycles.device = 'GPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02 if quick else 0.006
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPTIX'
    try:
        sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    except Exception:
        pass
    sc.cycles.max_bounces = 16
    sc.cycles.glossy_bounces = 8
    sc.cycles.transmission_bounces = 16
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.sample_clamp_indirect = 8.0
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 40 if quick else 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = look
    except Exception:
        try:
            sc.view_settings.look = look.replace('AgX - ', '')
        except Exception as e:
            log('look not set', e)
    sc.view_settings.exposure = exposure
    w_ = bpy.data.worlds.new('world')
    sc.world = w_
    try:
        w_.use_nodes = True
    except Exception:
        pass
    bg = w_.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (0.5, 0.5, 0.5, 1)
    bg.inputs['Strength'].default_value = 0.03
    return sc


def look_at(obj, target, loc):
    obj.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def camera(loc, target, lens=85, fstop=None, focus=None, sensor=36, shift=(0, 0)):
    cam = bpy.data.cameras.new('cam')
    cam.lens = lens
    cam.sensor_width = sensor
    cam.clip_start = 0.005
    cam.shift_x, cam.shift_y = shift
    o = link(bpy.data.objects.new('cam', cam))
    look_at(o, target, loc)
    bpy.context.scene.camera = o
    if fstop:
        cam.dof.use_dof = True
        cam.dof.aperture_fstop = fstop
        cam.dof.aperture_blades = 7
        cam.dof.focus_distance = (Vector(focus if focus is not None else target) - Vector(loc)).length
    return o


def area(name, loc, target, size=0.5, size_y=None, energy=20.0, color=(1, 1, 1), spread=180):
    L = bpy.data.lights.new(name, 'AREA')
    L.shape = 'RECTANGLE'
    L.size = size
    L.size_y = size_y or size
    L.energy = energy
    L.color = color
    L.spread = math.radians(spread)
    o = link(bpy.data.objects.new(name, L))
    look_at(o, target, loc)
    return o


def sweep(color=(0.5, 0.48, 0.45), width=3.0, depth=2.0, height=1.5, radius=0.5, z=0.0, yaw=0.0,
          origin=(0, 0, 0), mat=None):
    """seamless paper sweep: floor toward +Y, curved into a wall at y = depth (local), rotated by yaw."""
    verts, faces = [], []
    prof = [(-1.5, 0.0)]
    n = 24
    y0 = depth - radius
    prof += [(y, 0.0) for y in np.linspace(-1.0, y0, 6)[1:]]
    for i in range(1, n + 1):
        a = math.pi / 2 * i / n
        prof.append((y0 + radius * math.sin(a), radius - radius * math.cos(a)))
    prof += [(depth, radius + (height - radius) * k / 5) for k in range(1, 6)]
    nx = 4
    for xi in range(nx + 1):
        x = -width / 2 + width * xi / nx
        for (y, zz) in prof:
            verts.append((x, y, zz))
    np_ = len(prof)
    for xi in range(nx):
        for k in range(np_ - 1):
            a = xi * np_ + k
            faces.append((a, a + 1, a + 1 + np_, a + np_))
    me = bpy.data.meshes.new('sweep')
    me.from_pydata(verts, [], faces)
    me.shade_smooth()
    o = link(bpy.data.objects.new('sweep', me))
    sub = o.modifiers.new('sub', 'SUBSURF')
    sub.levels = sub.render_levels = 2
    o.rotation_euler = (0, 0, yaw)
    o.location = (origin[0], origin[1], z)
    setmat(o, mat or mat_paper(color))
    return o


def rig_objects(objs, name='rig'):
    rig = link(bpy.data.objects.new(name, None))
    for o in objs:
        o.parent = rig
    return rig


def world_bbox(objs):
    bpy.context.view_layer.update()
    return bbox([o for o in objs if o.type == 'MESH' and not o.hide_render])


def finish(name, save_blend, outdir=OUT):
    sc = bpy.context.scene
    os.makedirs(outdir, exist_ok=True)
    sc.render.filepath = os.path.join(outdir, name + '.png')
    t = time.time()
    if save_blend:
        os.makedirs(SCENES, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENES, name + '.blend'), compress=True)
    bpy.ops.render.render(write_still=True)
    if VIGNETTE.get('amount', 0) > 0:
        vignette(sc.render.filepath, VIGNETTE['amount'])
    log('rendered', name, '%.0f s' % (time.time() - t), sc.render.filepath)


VIGNETTE = {'amount': 0.18}


def vignette(path, amount):
    """soft radial vignette on the saved PNG (display-referred), like a lens falloff."""
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / math.sqrt(2)
    f = 1.0 - amount * np.clip((r - 0.35) / 0.65, 0, 1) ** 1.6
    px[:, :, :3] *= f[:, :, None]
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)


# ----------------------------------------------------------------------------- scene builders
def arm_scene(housing="graphite", real_board=False, curl=65.0):
    """arm + fitted band in the band frame; returns (rig, arm, band, extra objects)."""
    band = load_band(housing=housing)
    arm, info = build_arm(curl=curl)
    fit_band_to_arm(band, arm)
    objs = list(band.values()) + [arm]
    return arm, band, objs


def pose(rig, pitch=0.0, roll=0.0, yaw=0.0, floor_objs=None, floor=0.0):
    rig.rotation_mode = 'ZYX'
    rig.rotation_euler = (math.radians(pitch), math.radians(roll), math.radians(yaw))
    bpy.context.view_layer.update()
    if floor_objs:
        mn, mx = world_bbox(floor_objs)
        rig.location.z += floor - mn[2]
        bpy.context.view_layer.update()


def module_centre(band):
    lid = [o for o in band.values() if o['kind'] == 'module_lid']
    mn, mx = world_bbox(lid)
    return Vector(((mn + mx) / 2).tolist()), Vector(mn.tolist()), Vector(mx.tolist())


# ----------------------------------------------------------------------------- shots
def orbit(target, az, el, dist):
    """camera position around target: az from the -Y axis toward +X (deg), el above horizon."""
    az, el = math.radians(az), math.radians(el)
    return Vector(target) + dist * Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))


def studio(c, key=6.0, fill=1.5, rim=4.0, top=0.0, key_dir=(-0.45, -0.35, 0.6), fill_dir=(0.6, -0.5, 0.25),
           rim_dir=(0.25, 0.55, 0.35), key_size=0.6, warm=True, rim_color=(1.0, 0.98, 0.96)):
    c = Vector(c)
    kc = (1.0, 0.92, 0.82) if warm else (1, 1, 1)
    area('key', c + Vector(key_dir), c, size=key_size, energy=key, color=kc)
    area('fill', c + Vector(fill_dir), c, size=1.0, energy=fill, color=(0.94, 0.97, 1.0))
    area('rim', c + Vector(rim_dir), c, size=0.12, size_y=0.6, energy=rim, color=rim_color)
    if top:
        area('top', c + Vector((0, 0, 0.7)), c, size=0.9, energy=top)


def arm_shot(q, az, el, dist, roll=0.0, lens=85, fstop=4.0, arm_roll=0.0, pitch=-5.0, backdrop=(0.40, 0.37, 0.33),
             tgt_off=(0, -0.02, -0.015), lights=None, yaw_sweep=0.0, focus_off=(0, 0, 0.004), floor=0.0003,
             focus_kind='module_lid', curl=45.0):
    arm, band, objs = arm_scene(curl=curl)
    rig = rig_objects(objs)
    pose(rig, pitch=pitch, roll=arm_roll, floor_objs=objs, floor=floor)
    c, mn, mx = module_centre(band)
    fo = [o for o in band.values() if o['kind'] == focus_kind] or [o for o in band.values() if o['kind'] == 'module_lid']
    fmn, fmx = world_bbox(fo)
    fc = Vector(((fmn + fmx) / 2).tolist())
    tgt = c + rig.matrix_world.to_3x3() @ Vector(tgt_off)
    cam = camera(orbit(tgt, az, el, dist), tgt, lens=lens, fstop=fstop, focus=fc + Vector(focus_off))
    cam.rotation_euler.rotate_axis('Z', math.radians(roll))
    sweep(color=backdrop, depth=1.0, height=1.0, radius=0.35, origin=(0, 0, 0), yaw=math.radians(yaw_sweep))
    studio(c, **(lights or {}))
    return arm, band, c


def shot_hero_arm(q):
    # hand resting on the table on gently curled fingertips, forearm raised; seen from above, thumb side
    arm_shot(q, az=62, el=42, dist=0.56, pitch=8, curl=30, fstop=3.5, yaw_sweep=180 + 62, tgt_off=(0, -0.05, -0.02),
             lights=dict(key=7, fill=1.2, rim=5, top=2.0))


def shot_hero_crop(q):
    # confident 3/4 forearm crop, the module fills the frame
    arm_shot(q, az=72, el=36, dist=0.36, lens=100, pitch=-5, curl=45, fstop=4.0, yaw_sweep=180 + 72,
             tgt_off=(0, -0.012, -0.008), lights=dict(key=7, fill=1.2, rim=6, top=2.5))


def shot_hero_arm_wide(q):
    arm_shot(q, az=118, el=22, dist=0.62, lens=85, pitch=8, curl=30, fstop=3.2, yaw_sweep=180 + 118,
             tgt_off=(0, -0.05, -0.02),
             lights=dict(key=7, fill=1.2, rim=6, top=1.5, key_dir=(0.1, -0.6, 0.6)))


def shot_hero_dark(q, wide=False):
    """moody variant: deep charcoal sweep, warm key, cool rims from behind the subject, shallow DOF."""
    COOL = (0.68, 0.80, 1.0)
    az = 118 if wide else 62
    back = Vector((-math.sin(math.radians(az)), math.cos(math.radians(az)), 0))   # away from the camera
    side = Vector((back.y, -back.x, 0))
    kw = dict(pitch=8, curl=30, fstop=2.8, yaw_sweep=180 + az, tgt_off=(0, -0.05, -0.02),
              backdrop=(0.008, 0.008, 0.009))
    lights = dict(key=3.6, fill=0.12, rim=0.0, top=0.3, key_size=0.4, rim_color=COOL,
                  key_dir=(0.15, -0.55, 0.5) if wide else (-0.45, -0.3, 0.5),
                  rim_dir=tuple(back * 0.45 + side * 0.2 + Vector((0, 0, 0.22))))
    if wide:
        arm, band, c = arm_shot(q, az=az, el=22, dist=0.62, lens=85, lights=lights, **kw)
    else:
        arm, band, c = arm_shot(q, az=az, el=42, dist=0.56, lights=lights, **kw)
    # cool rims: tight beams (spread-limited) so they edge the arm and band without lighting the sweep
    # cool rims from behind, light-linked to the arm and band only so the charcoal sweep stays dark
    recv = bpy.data.collections.new('rim_receivers')
    for o in [arm] + list(band.values()):
        recv.objects.link(o)
    for name, pos, e in (('rim_cool', c + back * 0.40 + side * 0.15 + Vector((0, 0, 0.16)), 6.0),
                         ('rim_cool2', c + back * 0.40 - side * 0.25 + Vector((0, 0, 0.08)), 3.2)):
        L = area(name, pos, c, size=0.08, size_y=0.45, energy=e, color=COOL)
        L.light_linking.receiver_collection = recv
    # faint gradient on the sweep behind the subject (not linked: it only lights the backdrop)
    area('wallglow', c + back * 0.35 + Vector((0, 0, 0.35)), c + back * 1.1 + Vector((0, 0, 0.15)), size=0.7,
         energy=2.2, color=(0.85, 0.9, 1.0))


def shot_arm_volar(q):
    # palm up, held above the backdrop: buckle, strap and pods on the volar side
    arm, band, c = arm_shot(q, az=-105, el=42, dist=0.44, arm_roll=180, pitch=4, curl=40, fstop=4.0, yaw_sweep=180 - 105,
                            tgt_off=(0, -0.04, 0.0), focus_off=(0, 0, 0.0), roll=20, floor=0.075, focus_kind='strap_buckle',
                            lights=dict(key=7, fill=1.5, rim=6, top=2.0, key_dir=(-0.4, -0.4, 0.6)))


def product_band(housing='graphite', pedestal=True):
    band = load_band(housing=housing)
    objs = list(band.values())
    rig = rig_objects(objs)
    z0 = 0.03 if pedestal else 0.0
    pose(rig, floor_objs=objs, floor=z0)
    if pedestal:
        bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=0.055, depth=z0 + 0.001, location=(0, BAND_Y, z0 / 2 - 0.0005))
        p = bpy.context.active_object
        p.name = 'pedestal'
        bev = p.modifiers.new('bev', 'BEVEL')
        bev.width = 0.0015
        bev.segments = 4
        smooth(p, math.radians(30))
        setmat(p, mat_plaster((0.10, 0.098, 0.095)))
    c, mn, mx = module_centre(band)
    rmn, rmx = world_bbox(objs)
    return band, c, Vector(((rmn + rmx) / 2).tolist())


def shot_band_product(q):
    band, c, rc = product_band('graphite')
    tgt = rc + Vector((0, 0, -0.012))
    camera(orbit(tgt, 38, 16, 0.31), tgt, lens=85, fstop=5.6, focus=c)
    sweep(color=(0.018, 0.018, 0.018), depth=0.9, height=1.0, radius=0.35, origin=(0, BAND_Y, 0), yaw=math.radians(180 + 38))
    # small warm key, two thin rims to cut the silhouette out of the charcoal
    area('key', c + Vector((-0.30, -0.25, 0.40)), c, size=0.35, energy=3.0, color=(1.0, 0.92, 0.82))
    area('fill', c + Vector((0.5, -0.4, 0.2)), c, size=1.0, energy=0.6, color=(0.94, 0.97, 1.0))
    area('rim', c + Vector((0.3, 0.5, 0.3)), c, size=0.06, size_y=0.3, energy=2.5, color=(1.0, 0.98, 0.96))
    area('rim2', c + Vector((-0.45, 0.35, 0.2)), c, size=0.06, size_y=0.3, energy=2.0, color=(1.0, 0.97, 0.94))
    area('top', c + Vector((0, 0, 0.6)), c, size=0.5, energy=0.8)
    area('wallglow', Vector((0, BAND_Y + 0.35, 0.25)), Vector((0, BAND_Y + 0.9, 0.3)), size=0.6, energy=2.5)


def shot_band_bone(q):
    band, c, rc = product_band('bone', pedestal=False)
    tgt = rc + Vector((0.004, 0, -0.004))
    camera(orbit(tgt, -40, 16, 0.50), tgt, lens=85, fstop=5.0, focus=c)
    sweep(color=(0.34, 0.32, 0.30), depth=0.8, height=1.0, radius=0.3, origin=(0, BAND_Y, 0), yaw=math.radians(180 - 40))
    studio(c, key=5, fill=1.0, rim=7, top=1.5, key_dir=(0.45, -0.35, 0.55), rim_dir=(-0.35, 0.5, 0.3))


def board_into(module_objs):
    bobj, body = load_board()
    place_board_in_module(bobj, body, module_objs)
    for o in module_objs.values():
        if o['kind'] in ('main_board', 'board_parts'):
            o.hide_render = True
            o.hide_viewport = True
    return bobj


def shot_xray(q):
    band = load_band()
    mod = load_module()
    bobj = board_into(mod)
    T = module_to_band(mod, band)
    for o in bobj.values():
        o.matrix_world = T @ o.matrix_world
    for o in mod.values():
        bpy.data.objects.remove(o)
    for o in band.values():
        if o['kind'] in ('main_board', 'board_parts'):
            o.hide_render = True
        if o['kind'] in ('module_lid', 'module_base', 'button_cap'):
            setmat(o, mat_xray())
    objs = list(band.values()) + list(bobj.values())
    rig = rig_objects(objs)
    pose(rig, floor_objs=list(band.values()), floor=0.0)
    c, mn, mx = module_centre(band)
    tgt = c + Vector((0, -0.002, -0.006))
    camera(orbit(tgt, -36, 30, 0.21), tgt, lens=90, fstop=7.1, focus=c + Vector((0, -0.008, -0.002)))
    sweep(color=(0.035, 0.036, 0.038), depth=0.7, height=0.8, radius=0.3, origin=(0, BAND_Y, 0), yaw=math.radians(180 - 28))
    area('wallglow', c + Vector((0.3, 0.25, 0.2)), c + Vector((0.6, 0.6, 0.25)), size=0.5, energy=1.5)
    studio(c, key=4, fill=0.8, rim=10, top=1.0, key_dir=(0.35, -0.4, 0.5), rim_dir=(-0.3, 0.45, 0.25), warm=False)
    area('rim2', c + Vector((0.4, 0.4, 0.1)), c, size=0.1, size_y=0.5, energy=6)


EXPLODE = {'flex_pods_3_4': -0.014, 'tail': -0.014, 'pads': -0.014, 'foam': -0.014,
           'module_base': 0.0, 'magnets': 0.0, 'strap_bars': 0.0,
           'board': 0.013, 'lipo': 0.025, 'light_pipe': 0.040, 'module_lid': 0.040, 'button_cap': 0.040}


def shot_exploded(q):
    mod = load_module()
    bobj = board_into(mod)
    for o in mod.values():
        dz = EXPLODE.get(o['kind'], 0.0)
        o.location.z += dz
    for o in bobj.values():
        o.matrix_world = Matrix.Translation((0, 0, EXPLODE['board'])) @ o.matrix_world
    objs = [o for o in mod.values() if not o.hide_render] + list(bobj.values())
    rig = rig_objects(objs)
    pose(rig, floor_objs=objs, floor=0.025)
    mn, mx = world_bbox(objs)
    c = Vector(((mn + mx) / 2).tolist())
    camera(orbit(c, 32, 24, 0.23), c + Vector((0.003, 0, -0.001)), lens=85, fstop=9.0, focus=c)
    sweep(color=(0.52, 0.51, 0.49), depth=0.8, height=1.0, radius=0.3, origin=(0, 0, 0), yaw=math.radians(180 + 32))
    studio(c, key=5, fill=1.4, rim=5, top=2.0)


def board_scene(flip=False):
    bobj, body = load_board()
    objs = list(bobj.values())
    mn, mx = bbox(objs)
    root = link(bpy.data.objects.new('pcb', None))
    for o in objs:
        o.parent = root
        o.matrix_parent_inverse = Matrix.Translation(Vector((-(mn + mx) / 2).tolist()))
    if flip:
        root.rotation_euler = (0, math.pi, 0)
    bpy.context.view_layer.update()
    mn, mx = world_bbox(objs)
    root.location.z -= mn[2]
    bpy.context.view_layer.update()
    return bobj, root


def slate():
    m = principled('slate', (0.025, 0.025, 0.027), 0.6)
    add_bump(m, scale=180.0, strength=0.08, distance=0.0005, detail=6.0)
    return m


def shot_pcb_top(q):
    bobj, root = board_scene()
    c = Vector((0, 0, 0.0015))
    camera(orbit(c, 25, 36, 0.16), c + Vector((0, 0.001, 0)), lens=100, fstop=9.0, focus=c + Vector((0.0, 0.0, 0.001)))
    sweep(color=(0.05, 0.05, 0.052), depth=0.5, height=0.6, radius=0.2, origin=(0, 0, 0), yaw=math.radians(180 + 25),
          mat=slate())
    studio(c, key=1.6, fill=0.25, rim=2.5, top=1.2, key_dir=(-0.25, -0.15, 0.3), fill_dir=(0.3, -0.25, 0.12),
           rim_dir=(0.1, 0.3, 0.12), key_size=0.35, warm=True)


def shot_pcb_pair(q):
    """top and bottom side by side"""
    b1, r1 = board_scene()
    b2, r2 = board_scene(flip=True)
    r1.location.x -= 0.018
    r1.location.y += 0.004
    r1.rotation_euler.z = math.radians(-14)
    r2.location.x += 0.018
    r2.location.y -= 0.004
    r2.rotation_euler = (0, math.pi, math.radians(-14))
    c = Vector((0, 0, 0.001))
    camera(orbit(c, 18, 42, 0.24), c + Vector((0, 0.002, 0)), lens=100, fstop=10.0, focus=c)
    sweep(color=(0.05, 0.05, 0.052), depth=0.5, height=0.6, radius=0.2, origin=(0, 0, 0), yaw=math.radians(180 + 18),
          mat=slate())
    studio(c, key=1.8, fill=0.3, rim=2.5, top=1.4, key_dir=(-0.25, -0.2, 0.3), fill_dir=(0.3, -0.25, 0.12),
           rim_dir=(-0.1, 0.3, 0.12), key_size=0.35)


def flex_glb():
    p = os.path.join(BUILD, 'flex_board.glb')
    return p if os.path.exists(p) else None


def shot_flex_detail(q):
    p = flex_glb()
    if p:          # the real electrode flex (KiCad), skin side up, curled gently, looking along it
        bobj, body = load_board(p, flex=True)
        objs = list(bobj.values())
        bsdf(mat_gold()).inputs['Roughness'].default_value = 0.38   # broader highlight across the pads
        mn, mx = bbox(objs)
        ctr = (mn + mx) / 2
        # (laid flat: KiCad traces are long two-vertex quads, so bending the strip would make them float)
        for o in objs:
            o.matrix_world = Matrix.Translation(Vector((-ctr[0], -ctr[1], -mn[2]))) @ o.matrix_world
        tgt = Vector((0.0, 0.002, 0.002))
        cpos = orbit(tgt, 15, 40, 0.24)
        camera(cpos, tgt, lens=100, fstop=4.5, focus=tgt)
        sweep(color=(0.46, 0.45, 0.43), depth=0.6, height=0.6, radius=0.25, origin=(0, 0, 0), yaw=math.radians(180 + 15))
        studio(tgt, key=1.6, fill=0.35, rim=1.6, top=0.8, key_dir=(-0.25, -0.2, 0.35), key_size=0.35,
               fill_dir=(0.35, -0.2, 0.15), rim_dir=(0.1, 0.35, 0.15))
        # reflection card in the camera's mirror direction so the ENIG pads read as gold, not grey
        d = cpos - tgt
        mpos = tgt + Vector((-d.x, -d.y, d.z)).normalized() * 0.3
        area('card', mpos, tgt, size=0.5, size_y=0.25, energy=0.035, color=(1.0, 0.97, 0.92))
        return
    # fallback: the closed band lying on its side; look into the ring at the pods and gold pads
    band = load_band()
    objs = list(band.values())
    rig = rig_objects(objs)
    pose(rig, pitch=90, floor_objs=objs, floor=0.0)
    mn, mx = world_bbox(objs)
    rc = Vector(((mn + mx) / 2).tolist())
    pads = [o for o in band.values() if band_class(o['kind']) == 'gold']
    # focus on the pads farthest from the camera side
    cam_az = 200
    tgt = rc + Vector((0, 0, -0.004))
    cpos = orbit(tgt, cam_az, 60, 0.22)
    far = max(pads, key=lambda o: (Vector(world_bbox([o])[0].tolist()) - cpos).length)
    fmn, fmx = world_bbox([far])
    camera(cpos, tgt, lens=100, fstop=5.0, focus=Vector(((fmn + fmx) / 2).tolist()))
    sweep(color=(0.40, 0.39, 0.37), depth=0.7, height=0.8, radius=0.3, origin=(rc.x, rc.y, 0), yaw=math.radians(180 + cam_az))
    studio(rc, key=4, fill=1.0, rim=4, top=2.5, key_dir=(0.3, 0.45, 0.45))


def wrist_radius_profile(y=BAND_Y, step=0.5):
    w = import_glb(os.path.join(BUILD, 'fit_160.glb'), bake=True)
    wrist = [o for o in w.values() if kind(o.name) == 'wrist']
    ths = np.radians(np.arange(-180, 180, step))
    R = _radii(bvh_of(wrist), [y], ths)[0]
    for o in w.values():
        bpy.data.objects.remove(o)
    R = np.where(np.isnan(R), np.nanmean(R), R)
    return ths, R


def gap_centre_deg():
    try:
        d = json.load(open(os.path.join(ROOT, 'mech/rev_c/fit_results.json')))
        return float(d['160']['gap_centre_deg_from_dorsal'])
    except Exception:
        return 141.0


def densify(me, maxlen=0.0012, passes=6):
    """triangulate and split long edges until none is longer than maxlen."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for _ in range(passes):
        long = [e for e in bm.edges if e.calc_length() > maxlen]
        if not long:
            break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    me.update()


def components(me):
    """connected-component label per vertex (union-find over edges)."""
    n = len(me.vertices)
    E = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get('vertices', E)
    E = E.reshape(-1, 2)
    parent = np.arange(n)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in E:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    return np.array([find(i) for i in range(n)])


def unroll_band(band):
    """open the closed band flat, skin side up: arc-length unrolling around the CAD wrist, the module
    rigid at the centre, the strap draped down to the table either side, cut at the strap gap."""
    ths, R = wrist_radius_profile()
    thc = -math.radians(gap_centre_deg())                  # gap on the ulnar (-X) side
    # arc length from the cut, going round through the dorsal centre
    tp = np.mod(ths - thc, 2 * math.pi)
    order = np.argsort(tp)
    tps, Rs = tp[order], R[order]
    dR = np.gradient(Rs, tps)
    S = np.concatenate([[0], np.cumsum(np.sqrt(Rs[1:] ** 2 + dR[1:] ** 2) * np.diff(tps))])
    s0 = np.interp(np.mod(-thc, 2 * math.pi), tps, S)      # dorsal centre
    r0 = np.interp(np.mod(-thc, 2 * math.pi), tps, Rs)
    def fmap(V):
        th = np.arctan2(V[:, 0], V[:, 2])
        r = np.hypot(V[:, 0], V[:, 2])
        t = np.mod(th - thc, 2 * math.pi)
        F = np.stack([np.interp(t, tps, S) - s0, V[:, 1], r - np.interp(t, tps, Rs)], 1)
        Rg = np.stack([V[:, 0], V[:, 1], V[:, 2] - r0], 1)
        W = np.clip((np.abs(th) - math.radians(36)) / math.radians(44), 0, 1)
        W = W * W * (3 - 2 * W)
        return Rg * (1 - W)[:, None] + F * W[:, None], th, W
    RIGID = tuple(k for k in set(o['kind'] for o in band.values())
                  if band_class(k) in ('pod', 'gold', 'foam') or k == 'strap_buckle')
    flat = {}
    for o in band.values():
        V = verts_np(o, world=False)
        if in_module(o['kind']):
            N = np.stack([V[:, 0], V[:, 1], V[:, 2] - r0], 1)
            W = np.zeros(len(V))
        else:
            densify(o.data)                                  # so flat faces follow the unrolling
            V = verts_np(o, world=False)
            N, th, W = fmap(V)
            if band_class(o['kind']) == 'gold':
                N[:, 2] -= 0.0001                            # keep the thin ENIG discs proud of the flex
        N[:, 1] = -N[:, 1]                                   # flip: skin side up
        N[:, 2] = -N[:, 2]
        flat[o.name] = (N, W)
    # drape: everything off the module drops to the table
    zmod = min(flat[o.name][0][:, 2].min() for o in band.values() if o['kind'] in ('module_lid',))
    zring = min(flat[o.name][0][:, 2].min() for o in band.values() if is_strap(o['kind']))
    half = 0.5 * (max(flat[o.name][0][:, 0].max() for o in band.values() if o['kind'] == 'module_base')
                  - min(flat[o.name][0][:, 0].min() for o in band.values() if o['kind'] == 'module_base'))
    for o in band.values():
        N, W = flat[o.name]
        if not in_module(o['kind']):
            xa = np.abs(N[:, 0])
            d = np.clip((xa - half - 0.003) / 0.040, 0, 1)
            d = d * d * (3 - 2 * d)
            N[:, 2] += d * (zmod - zring)
        V0 = verts_np(o, world=False)
        o.data.vertices.foreach_set('co', N.ravel())
        o.data.update()
        # faces torn by the cut become long slivers: drop them
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bad = []
        for f in bm.faces:
            for e in f.edges:
                a, b = e.verts
                l1 = (a.co - b.co).length
                l0 = float(np.linalg.norm(V0[a.index] - V0[b.index]))
                if l1 > 0.008 and l1 > 3 * l0:
                    bad.append(f)
                    break
        if bad:
            bmesh.ops.delete(bm, geom=bad, context='FACES')
        bm.to_mesh(o.data)
        bm.free()
        o.data.update()


def shot_flatlay(q):
    band = load_band()
    for o in band.values():
        if o['kind'] in ('main_board', 'board_parts'):
            o.hide_render = True
    unroll_band(band)
    objs = [o for o in band.values()]
    rig = rig_objects(objs)
    rig.rotation_euler = (0, 0, math.radians(-10))
    bpy.context.view_layer.update()
    mn, mx = world_bbox(objs)
    rig.location.z -= mn[2]
    bpy.context.view_layer.update()
    mn, mx = world_bbox(objs)
    c = Vector(((mn + mx) / 2).tolist())
    camera(orbit(c, 8, 72, 0.42), c, lens=85, fstop=8.0, focus=c)
    sweep(color=(0.50, 0.48, 0.45), depth=1.0, height=1.0, radius=0.35, origin=(0, 0, 0), yaw=math.radians(188))
    studio(c, key=4.5, fill=1.2, rim=3, top=0.0, key_dir=(-0.4, -0.25, 0.45), fill_dir=(0.45, -0.3, 0.3),
           rim_dir=(0.2, 0.45, 0.25))
    cpos = orbit(c, 8, 72, 0.42)
    d = cpos - c
    area('card', c + Vector((-d.x, -d.y, d.z)).normalized() * 0.4, c, size=0.5, size_y=0.3, energy=0.15,
         color=(1.0, 0.9, 0.75))


def shot_pods_inside(q):
    """the closed band lying on its side; look into the ring at the gold pads on the far wall."""
    band = load_band()
    objs = list(band.values())
    rig = rig_objects(objs)
    pose(rig, pitch=90, floor_objs=objs, floor=0.0)
    mn, mx = world_bbox(objs)
    rc = Vector(((mn + mx) / 2).tolist())
    pads = [o for o in band.values() if band_class(o['kind']) == 'gold']
    cam_az = 140
    tgt = rc + Vector((0, 0, -0.004))
    cpos = orbit(tgt, cam_az, 52, 0.30)
    def dist(o):
        a, b = world_bbox([o])
        return (Vector(((a + b) / 2).tolist()) - cpos).length
    far = sorted(pads, key=dist)[-3:]
    fmn, fmx = world_bbox(far)
    fc = Vector(((fmn + fmx) / 2).tolist())
    camera(cpos, fc + Vector((0, 0, -0.006)), lens=150, fstop=6.3, focus=fc)
    sweep(color=(0.40, 0.39, 0.37), depth=0.7, height=0.8, radius=0.3, origin=(rc.x, rc.y, 0), yaw=math.radians(180 + cam_az))
    studio(rc, key=4, fill=1.0, rim=4, top=2.5, key_dir=(0.3, 0.45, 0.45))
    d = cpos - fc
    area('card', fc + Vector((-d.x, -d.y, d.z)).normalized() * 0.3, fc, size=0.3, size_y=0.2, energy=0.12,
         color=(1.0, 0.9, 0.75))


SHOTS = {
    'hero_arm': (shot_hero_arm, {}, (1638, 2048)),
    'hero_arm_wide': (shot_hero_arm_wide, {}, (2048, 1152)),
    'hero_crop': (shot_hero_crop, {}, (1638, 2048)),
    'hero_dark': (shot_hero_dark, {}, (1638, 2048)),
    'hero_dark_wide': (shot_hero_dark, {'wide': True}, (2048, 1152)),
    'flatlay': (shot_flatlay, {}, (2048, 1152)),
    'pods_inside': (shot_pods_inside, {}, (1638, 2048)),
    'arm_volar': (shot_arm_volar, {}, (1638, 2048)),
    'band_product': (shot_band_product, {}, (1638, 2048)),
    'band_bone': (shot_band_bone, {}, (2048, 1152)),
    'xray': (shot_xray, {}, (2048, 1152)),
    'exploded': (shot_exploded, {}, (1638, 2048)),
    'pcb_top': (shot_pcb_top, {}, (2048, 1152)),
    'pcb_pair': (shot_pcb_pair, {}, (2048, 1152)),
    'flex_detail': (shot_flex_detail, {}, (2048, 1152)),
}


# 16:9 versions for social posts (render/out/social/): same scene, the camera is re-fitted so the subject
# (every band mesh with a 'kind', or only the kinds listed; the board's meshes) sits centred and fills `fill` of the frame height.
SOCIAL_RES = (2048, 1152)
SOCIAL = {
    'hero_crop': dict(fill=0.46, kinds=('module_lid', 'module_base', 'button_cap')),
    'pods_inside': dict(fill=0.86),
    'pcb_top': dict(fill=0.72),
}


def subject_points(kinds=None):
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_render
            and (('kind' in o and (kinds is None or o['kind'] in kinds)) or (o.parent and o.parent.name == 'pcb'))]
    bpy.context.view_layer.update()
    return np.vstack([verts_np(o) for o in objs if len(o.data.vertices)])


def frame_subject(pts, fill=0.7, offset=(0.0, 0.0)):
    """re-fit the scene camera (lens shift + vertical sensor size, so perspective is unchanged) so the
    points' screen-space box is centred and spans `fill` of the frame height (or width, whichever binds)."""
    sc = bpy.context.scene
    cam = sc.camera
    aspect = sc.render.resolution_x / sc.render.resolution_y
    m = np.array(cam.matrix_world.inverted())
    pc = pts @ m[:3, :3].T + m[:3, 3]
    pc = pc[pc[:, 2] < -1e-4]
    u, v = pc[:, 0] / -pc[:, 2], pc[:, 1] / -pc[:, 2]
    uc, vc = (u.min() + u.max()) / 2, (v.min() + v.max()) / 2
    hy = max((v.max() - v.min()) / (2 * fill), (u.max() - u.min()) / (2 * fill * aspect))
    hx = hy * aspect
    cd = cam.data
    cd.shift_x, cd.shift_y = 0.0, 0.0
    cd.sensor_fit = 'VERTICAL'
    cd.sensor_height = 2 * hy * cd.lens
    cd.shift_x = uc / (2 * hy) + offset[0]     # with a vertical sensor fit, shift is in frame heights
    cd.shift_y = vc / (2 * hy) + offset[1]
    log('social frame: sensor_h %.2f mm, shift %.3f %.3f' % (cd.sensor_height, cd.shift_x, cd.shift_y))


TT_FRAMES = 135          # 4.5 s at 30 fps


def turntable(frames, quick, samples=0, social=False):
    """band_product look, the band spins once about the pedestal axis with a cosine ease (seamless loop).
    social=True: 1920 x 1080, camera fitted to the band over the whole turn, frames in build/turntable_social."""
    reset()
    MATS.clear()
    setup_render(*((1920, 1080) if social else (1080, 1350)), samples or (32 if quick else 256), quick)
    bpy.context.scene.render.resolution_percentage = 50 if quick else 100
    bpy.context.scene.render.use_persistent_data = True
    shot_band_product(quick)
    cam = bpy.context.scene.camera
    cam.data.dof.aperture_fstop = 11.0                    # keep the whole ring sharp while it turns
    rig = bpy.data.objects['rig']
    piv = link(bpy.data.objects.new('turntable', None))
    piv.location = (0, BAND_Y, 0)
    bpy.context.view_layer.update()
    rig.parent = piv
    rig.matrix_parent_inverse = piv.matrix_world.inverted()
    if social:
        pts = []
        for k in range(12):
            piv.rotation_euler.z = 2 * math.pi * k / 12
            bpy.context.view_layer.update()
            pts.append(subject_points())
        piv.rotation_euler.z = 0.0
        frame_subject(np.vstack(pts), fill=0.80)
    out = os.path.join(BUILD, 'turntable_social' if social else 'turntable')
    os.makedirs(out, exist_ok=True)
    for i in frames:
        t = i / TT_FRAMES
        piv.rotation_euler.z = 2 * math.pi * (0.5 - 0.5 * math.cos(math.pi * t))
        p = os.path.join(out, 'f_%04d.png' % i)
        bpy.context.scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        vignette(p, VIGNETTE['amount'])
        log('turntable frame', i)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', default=','.join(SHOTS))
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--samples', type=int, default=0)
    ap.add_argument('--save-blend', action='store_true')
    ap.add_argument('--turntable', default='', help='frames start:stop:step (exclusive stop)')
    ap.add_argument('--social', action='store_true', help='16:9 subject-centred versions -> render/out/social/')
    a = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    if a.turntable:
        st, sp, sd = (int(x) for x in a.turntable.split(':'))
        turntable(range(st, sp, sd), a.quick, a.samples, a.social)
        return
    for name in a.shots.split(','):
        fn, kw, (w, h) = SHOTS[name]
        if a.social:
            w, h = SOCIAL_RES
        reset()
        MATS.clear()
        t = time.time()
        samples = a.samples or (64 if a.quick else 768)
        setup_render(w, h, samples, a.quick)
        fn(a.quick, **kw)
        if a.social:
            cfg = dict(SOCIAL.get(name, {}))
            frame_subject(subject_points(cfg.pop('kinds', None)), **cfg)
        log('built', name, '%.1f s' % (time.time() - t))
        finish(name, a.save_blend, os.path.join(OUT, 'social') if a.social else OUT)


if __name__ == '__main__':
    main()
