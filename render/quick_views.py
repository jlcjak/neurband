#!/usr/bin/env python3
"""Quick preview renders of mech STEP files (iso / front / top / right PNGs in mech/rev_c/renders/),
used while the Backplane quick renderer could not mesh STEP files (Nov 2026).
STEP -> GLB with colours through FreeCAD (render/step2glb.py), then Blender Workbench (studio light,
object colours, outlines). Front = view from -Y (distal), right = from +X, top = from +Z.
  python3 render/quick_views.py mech/rev_c/module_assy.step mech/rev_c/pod.step
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build', 'quick')
OUT = os.path.join(ROOT, 'mech', 'rev_c', 'renders')

if __name__ == '__main__' and 'bpy' not in sys.modules:
    steps = [os.path.abspath(p) for p in sys.argv[1:]]
    os.makedirs(BUILD, exist_ok=True)
    pairs = [(s, os.path.join(BUILD, os.path.splitext(os.path.basename(s))[0] + '.glb')) for s in steps]
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', STEP2GLB=';'.join(a + '=' + b for a, b in pairs))
    subprocess.run(['/usr/bin/freecad', os.path.join(HERE, 'step2glb.py')], env=env, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=900)
    glbs = [b for _, b in pairs if os.path.exists(b)]
    missing = [a for a, b in pairs if not os.path.exists(b)]
    if missing:
        print('STEP -> GLB failed for', missing)
    subprocess.run(['blender', '-b', '--python', os.path.abspath(__file__), '--'] + glbs, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=1800)
    for b in glbs:
        n = os.path.splitext(os.path.basename(b))[0]
        print(n, [v for v in ('iso', 'front', 'top', 'right') if os.path.exists(os.path.join(OUT, f'{n}.{v}.png'))])
    sys.exit(0)

import bpy, mathutils, math  # noqa: E402

args = sys.argv[sys.argv.index('--') + 1:]
for glb in args:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    pts = [o.matrix_world @ mathutils.Vector(c) for o in objs for c in o.bound_box]
    lo = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr, size = (lo + hi) / 2, max((hi - lo).length, 1e-3)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_object_outline = True
    sc.display.shading.show_cavity = True
    sc.display.shading.cavity_type = 'BOTH'
    sc.render.resolution_x, sc.render.resolution_y = 1000, 750
    sc.render.film_transparent = False
    w = bpy.data.worlds.new('w'); sc.world = w
    sc.display.shading.background_type = 'VIEWPORT'
    sc.display.shading.background_color = (0.93, 0.93, 0.94)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'
    # glTF is Y-up; the importer converts to Blender Z-up, so CAD axes map directly
    views = {'iso': (1.0, -1.3, 0.9), 'front': (0, -1, 0), 'top': (0, 0, 1), 'right': (1, 0, 0)}
    name = os.path.splitext(os.path.basename(glb))[0]
    for v, d in views.items():
        dv = mathutils.Vector(d).normalized()
        cam.location = ctr + dv * size * 3
        up = mathutils.Vector((0, 1, 0)) if v == 'top' else mathutils.Vector((0, 0, 1))
        cam.rotation_euler = (-dv).to_track_quat('-Z', 'Y').to_euler() if v != 'top' else (0, 0, 0)
        cam.data.ortho_scale = size * 1.05
        cam.data.clip_end = size * 10
        sc.render.filepath = os.path.join(OUT, f'{name}.{v}.png')
        bpy.ops.render.render(write_still=True)
