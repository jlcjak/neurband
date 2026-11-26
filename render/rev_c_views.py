#!/usr/bin/env python3
"""Close-up views of the rev C housing (cradle + lid design) for checking and for the build notes.

STEP -> GLB with colours through FreeCAD (render/step2glb.py), then Blender. Two looks:
  default      Workbench: flat studio light, outlines, cavity shading. Fast, good for inspecting.
  --beauty     Cycles on the GPU: soft studio light, matte printed plastic. For pictures to show.
Writes mech/rev_c/renders/view_<shot>.png (Workbench) or shot_<shot>.png (Cycles).
  python3 render/rev_c_views.py [--beauty] [shot ...]
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build', 'rev_c')
MECH = os.path.join(ROOT, 'mech', 'rev_c')
OUT = os.path.join(MECH, 'renders')

# shot: (step file, camera direction (from the model toward the camera), zoom, hidden part-name prefixes)
SHOTS = {
    'band_on_wrist': ('band_assembly.step', (0.9, -1.25, 0.95), 1.0, ()),
    'band_volar': ('band_assembly.step', (0.55, -1.20, -1.05), 1.0, ()),
    'band_quickfit': ('band_assembly.step', (1.15, -0.75, 0.45), 1.55, ()),
    'band_from_hand': ('band_assembly.step', (0.0, -1.0, 0.12), 1.0, ()),
    'band_side': ('band_assembly.step', (1.0, -0.25, 0.25), 1.0, ()),
    'wrap_on_wrist': ('band_assembly_wrap.step', (0.9, -1.25, 0.95), 1.0, ()),
    'wrap_from_hand': ('band_assembly_wrap.step', (0.0, -1.0, 0.12), 1.0, ()),
    'module_top': ('module_assy.step', (0.8, -1.2, 1.0), 1.0, ()),
    'module_end': ('module_assy.step', (0.0, -1.0, 0.18), 1.0, ()),
    'module_under': ('module_assy.step', (0.7, -1.1, -1.0), 1.0, ()),
    'module_open': ('module_assy.step', (0.8, -1.2, 1.0), 1.0, ('lid',)),
    'module_nest': ('module_assy.step', (0.8, -1.2, 1.0), 1.0, ('lid', 'lipo', 'lipo_pcm')),
    'module_exploded': ('module_exploded.step', (1.0, -1.3, 0.55), 1.0, ()),
    'cradle_print': ('to_print/cradle.step', (0.8, -1.2, 1.0), 1.0, ()),
    'holder_print': ('to_print/holder.step', (0.8, -1.2, 1.0), 1.0, ()),
    'lug_bar_print': ('to_print/lug_bar_x2.step', (0.8, -1.2, 1.0), 1.0, ()),
    'lid_print': ('to_print/lid.step', (0.8, -1.2, 1.1), 1.0, ()),
    'pod_print': ('to_print/pod_x6.step', (1.0, -1.0, 0.8), 1.0, ()),
    'pod': ('pod.step', (0.9, -1.2, 0.9), 1.0, ()),
    'jig': ('bond_jig.step', (0.5, -1.2, 1.0), 1.0, ()),
    'jig_loaded': ('jig_loaded.step', (0.5, -1.2, 1.0), 1.0, ()),
    'jig_bonded': ('jig_bonded.step', (0.5, -1.2, 1.0), 1.0, ()),
    'section_xz': ('module_section_xz.step', (0.0, -1.0, 0.0), 1.0, ()),
    'section_yz': ('module_section_yz.step', (1.0, 0.0, 0.0), 1.0, ()),
}

if __name__ == '__main__' and 'bpy' not in sys.modules:
    argv = sys.argv[1:]
    cycles = '--beauty' in argv
    want = [a for a in argv if not a.startswith('--')] or list(SHOTS)
    os.makedirs(BUILD, exist_ok=True)
    steps = sorted({SHOTS[s][0] for s in want})
    pairs = [(os.path.join(MECH, s), os.path.join(BUILD, s.replace('/', '_').replace('.step', '.glb'))) for s in steps]
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='', STEP2GLB=';'.join(a + '=' + b for a, b in pairs))
    env.pop('DISPLAY', None); env.pop('WAYLAND_DISPLAY', None)
    subprocess.run(['/usr/bin/freecad', os.path.join(HERE, 'step2glb.py')], env=env, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=900)
    missing = [a for a, b in pairs if not os.path.exists(b)]
    if missing:
        print('STEP -> GLB failed for', missing)
    r = subprocess.run(['blender', '-b', '--python', os.path.abspath(__file__), '--'] + (['--beauty'] if cycles else []) + want,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=3600)
    pre = 'shot' if cycles else 'view'
    for s in want:
        p = os.path.join(OUT, f'{pre}_{s}.png')
        print(s, 'ok' if os.path.exists(p) else 'MISSING')
    if any(not os.path.exists(os.path.join(OUT, f'{pre}_{s}.png')) for s in want):
        print(r.stdout[-3000:])
    sys.exit(0)

import bpy, mathutils, math  # noqa: E402

args = sys.argv[sys.argv.index('--') + 1:]
CYCLES = '--beauty' in args
shots = [a for a in args if not a.startswith('--')]

MAT = {  # part-name prefix -> (base colour, roughness, metallic)
    'cradle': ((0.045, 0.16, 0.50, 1), 0.55, 0.0), 'holder': ((0.025, 0.095, 0.34, 1), 0.55, 0.0), 'lid': ((0.07, 0.24, 0.66, 1), 0.5, 0.0), 'pods': ((0.045, 0.16, 0.50, 1), 0.55, 0.0),
    'pod': ((0.045, 0.16, 0.50, 1), 0.55, 0.0), 'bond_jig': ((0.62, 0.62, 0.60, 1), 0.6, 0.0),
    'lug_bars': ((0.025, 0.095, 0.34, 1), 0.55, 0.0), 'lug_bar': ((0.025, 0.095, 0.34, 1), 0.55, 0.0),
    'strap_quickfit': ((0.035, 0.038, 0.044, 1), 0.35, 0.75), 'strap_buckle': ((0.035, 0.038, 0.044, 1), 0.32, 0.80),
    'lug_pins': ((0.72, 0.74, 0.78, 1), 0.25, 1.0), 'qf_screws': ((0.65, 0.67, 0.72, 1), 0.28, 1.0),
    'strap_keepers': ((0.018, 0.042, 0.13, 1), 0.92, 0.0), 'strap_stitch': ((0.03, 0.07, 0.20, 1), 0.90, 0.0),
    'strap_ring': ((0.75, 0.76, 0.78, 1), 0.3, 1.0), 'strap': ((0.015, 0.036, 0.115, 1), 0.92, 0.0),
    'flex': ((0.70, 0.25, 0.02, 1), 0.35, 0.0), 'tail': ((0.70, 0.25, 0.02, 1), 0.35, 0.0), 'electrodes': ((0.83, 0.61, 0.22, 1), 0.3, 1.0),
    'foam_dots': ((0.85, 0.85, 0.82, 1), 0.9, 0.0), 'main_board': ((0.01, 0.16, 0.04, 1), 0.4, 0.0), 'board_parts': ((0.02, 0.02, 0.02, 1), 0.5, 0.0),
    'lipo_pcm': ((0.72, 0.48, 0.03, 1), 0.4, 0.0), 'lipo': ((0.62, 0.63, 0.66, 1), 0.35, 0.6), 'leads': ((0.55, 0.02, 0.02, 1), 0.5, 0.0),
    'wrist': ((0.78, 0.52, 0.40, 1), 0.6, 0.0),
}


def material_for(name):
    key = max((k for k in MAT if name.lower().startswith(k)), key=len, default=None)
    if key is None:
        return None
    col, rough, metal = MAT[key]
    m = bpy.data.materials.get('nb_' + key)
    if m is None:
        m = bpy.data.materials.new('nb_' + key)
        m.use_nodes = True
        b = m.node_tree.nodes.get('Principled BSDF')
        b.inputs['Base Color'].default_value = col
        b.inputs['Roughness'].default_value = rough
        b.inputs['Metallic'].default_value = metal
        m.diffuse_color = col
    return m


for shot in shots:
    step, direction, zoom, hide = SHOTS[shot]
    glb = os.path.join(BUILD, step.replace('/', '_').replace('.step', '.glb'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    sc = bpy.context.scene
    objs = [o for o in sc.objects if o.type == 'MESH']
    for o in objs:
        if any(o.name.lower().startswith(h) for h in hide):
            o.hide_render = True
            continue
        m = material_for(o.name)
        if m is not None:
            o.data.materials.clear()
            o.data.materials.append(m)
        elif not o.data.materials or 'to_print' in step:
            g = bpy.data.materials.get('nb_plain') or bpy.data.materials.new('nb_plain')
            g.diffuse_color = (0.07, 0.24, 0.66, 1)
            g.use_nodes = True
            g.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.07, 0.24, 0.66, 1)
            g.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.5
            o.data.materials.clear()
            o.data.materials.append(g)
    vis = [o for o in objs if not o.hide_render]
    pts = [o.matrix_world @ mathutils.Vector(c) for o in vis for c in o.bound_box]
    lo = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr, size = (lo + hi) / 2, max((hi - lo).length, 1e-3)
    sc.render.resolution_x, sc.render.resolution_y = 1500, 1100
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'
    dv = mathutils.Vector(direction).normalized()
    cam.location = ctr + dv * size * 3
    cam.rotation_euler = (-dv).to_track_quat('-Z', 'Y').to_euler()
    # fit: project the bounding box corners on the camera plane
    right = dv.cross(mathutils.Vector((0, 0, 1)))
    right = right.normalized() if right.length > 1e-6 else mathutils.Vector((1, 0, 0))
    up = right.cross(dv).normalized()
    ex = max(abs((p - ctr).dot(right)) for p in pts)
    ey = max(abs((p - ctr).dot(up)) for p in pts)
    cam.data.ortho_scale = max(2 * ex, 2 * ey * 1500 / 1100) * 1.12 / zoom
    cam.data.clip_start = size * 0.05
    cam.data.clip_end = size * 10
    w = bpy.data.worlds.new('w'); sc.world = w
    if CYCLES:
        sc.render.engine = 'CYCLES'
        sc.cycles.samples = 96
        sc.cycles.use_denoising = True
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = 'OPTIX'
            prefs.get_devices()
            for d in prefs.devices:
                d.use = d.type == 'OPTIX'
            sc.cycles.device = 'GPU'
        except Exception as ex_:
            print('GPU setup failed, CPU render:', ex_)
        w.use_nodes = True
        w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.93, 0.93, 0.94, 1)
        w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55
        for k, (off, power, sz) in enumerate((((0.6, -0.5, 1.0), 9.0, 1.2), ((-1.0, -0.3, 0.5), 3.5, 1.6), ((0.2, 1.0, 0.6), 4.0, 1.4))):
            L = bpy.data.objects.new(f'L{k}', bpy.data.lights.new(f'L{k}', 'AREA'))
            sc.collection.objects.link(L)
            L.data.size = size * sz
            L.data.energy = power * size * size * 4.0
            basis = (dv * off[2] + right * off[0] + up * off[1])
            L.location = ctr + (dv * 1.0 + right * off[0] + up * (0.6 + off[1] * 0.4)).normalized() * size * 2.2
            L.rotation_euler = (ctr - L.location).to_track_quat('-Z', 'Y').to_euler()
        # shadow-catching floor under the model when looking from above
        if dv.z > 0.3:
            bpy.ops.mesh.primitive_plane_add(size=size * 40, location=(ctr.x, ctr.y, lo.z - 1e-4))
            fl = bpy.context.active_object
            fm = bpy.data.materials.new('floor'); fm.use_nodes = True
            fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.86, 0.86, 0.87, 1)
            fm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8
            fl.data.materials.append(fm)
        sc.view_settings.view_transform = 'Standard'
    else:
        sc.render.engine = 'BLENDER_WORKBENCH'
        sh = sc.display.shading
        sh.light = 'STUDIO'
        sh.color_type = 'MATERIAL'
        sh.show_object_outline = True
        sh.show_cavity = True
        sh.cavity_type = 'BOTH'
        sh.show_shadows = False
        sh.background_type = 'VIEWPORT'
        sh.background_color = (0.94, 0.94, 0.95)
        sc.display.render_aa = '16'
    sc.render.filepath = os.path.join(OUT, f"{'shot' if CYCLES else 'view'}_{shot}.png")
    bpy.ops.render.render(write_still=True)
