import os
import bpy, math, mathutils
LIB = os.path.join(os.environ.get('NEURBAND_ROOT', os.path.expanduser('~/neurband')), 'extra/render_assets/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend')
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(LIB, link=False) as (src, dst):
    dst.objects = ["Hand  - Realistic"]
hand = dst.objects[0]
bpy.context.scene.collection.objects.link(hand)
for m in hand.modifiers:
    if m.type == 'MULTIRES':
        m.levels = m.render_levels = m.total_levels
hand.parent = None
hand.location = (0, 0, 0)
bpy.context.view_layer.update()
print("dims", hand.dimensions, "loc", hand.location, "rot", hand.rotation_euler)
bb = [hand.matrix_world @ mathutils.Vector(c) for c in hand.bound_box]
print("bbox min", [min(v[i] for v in bb) for i in range(3)], "max", [max(v[i] for v in bb) for i in range(3)])
mat = bpy.data.materials.new("skin"); mat.use_nodes = True
b = mat.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.80, 0.56, 0.45, 1)
b.inputs["Subsurface Weight"].default_value = 0.25
b.inputs["Subsurface Radius"].default_value = (0.012, 0.004, 0.002)
b.inputs["Roughness"].default_value = 0.45
hand.data.materials.clear(); hand.data.materials.append(mat)
bpy.ops.object.shade_smooth()
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'GPU'; sc.cycles.samples = 128
sc.view_settings.view_transform = "AgX"
prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'
prefs.get_devices(); [setattr(d, 'use', True) for d in prefs.devices]
sc.render.resolution_x, sc.render.resolution_y = 1000, 800
c = [ (min(v[i] for v in bb)+max(v[i] for v in bb))/2 for i in range(3)]
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (c[0]+0.35, c[1]-0.45, c[2]+0.25)
d = mathutils.Vector(c) - cam.location; cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()
for i,(loc,e) in enumerate([((0.5,-0.5,0.6),25),((-0.6,-0.2,0.3),8),((0,0.6,0.5),15)]):
    l = bpy.data.objects.new(f"L{i}", bpy.data.lights.new(f"L{i}", 'AREA')); l.data.energy = e; l.data.size = 0.5
    l.location = (c[0]+loc[0], c[1]+loc[1], c[2]+loc[2]); dd = mathutils.Vector(c)-l.location; l.rotation_euler = dd.to_track_quat('-Z','Y').to_euler()
    sc.collection.objects.link(l)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.05,0.055,0.06,1)
sc.render.filepath = "/tmp/hand_test.png"
bpy.ops.render.render(write_still=True)
