"""export_to_print.py - write the printable parts into to_print/, each already lying on the bed (Z = 0),
and the Backplane fab files beside the as-worn STEP files.

  tub.step          upright, standing on its six electrode pads (no supports)
  lid.step          top down; two bodies: 'lid' and the 0.32 mm 'blue_inlay' (logo and text) for a second colour
  lug_bar_x2.step   flat
  pod_x6.step       on its side: the profile on the bed, 8 mm tall
  bond_tray.step    flat (tool)

Run: unset DISPLAY WAYLAND_DISPLAY; QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c2/export_to_print.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True
sys.neurband_tray_lib = True

import FreeCAD, Part
import c2 as R
import params as P
import case as C
import pod as PD
import tray as T

V = FreeCAD.Vector
OUT = os.path.join(R.HERE, 'to_print')
os.makedirs(OUT, exist_ok=True)


def fab(stem, name, shape, qty, order=True):
    d = {"kind": "3dp", "name": name, "source": stem + ".step", "qty": qty,
         "options": {"process": "fdm", "material": "pla", "color": "black"}, "features": R.features(shape)}
    if not order:
        d["order"] = False
    with open(os.path.join(R.HERE, stem + '.fab.json'), 'w') as f:
        json.dump(d, f, indent=2)
        f.write('\n')


def export(objs, path):
    doc = FreeCAD.newDocument('ToPrint')
    feats = []
    for name, shape, color in objs:
        o = doc.addObject('Part::Feature', name)
        o.Shape = shape
        if R.GUI:
            o.ViewObject.ShapeColor = color
        feats.append(o)
    doc.recompute()
    if R.GUI:
        import ImportGui
        ImportGui.export(feats, path)
    else:
        import Import
        Import.export(feats, path)
    FreeCAD.closeDocument(doc.Name)


log = R.Log('to_print')
tub, lid, bar = C.build_tub(), C.build_lid(), C.build_lug_bar()
pod, _ = PD.build_pod()
tray = T.build_tray()
fab('tub', 'Module tub', tub, 1)
fab('lid', 'Module lid', lid, 1)
fab('lug_bar', 'Strap cross-bar', bar, 2)
fab('pod', 'Pod with spring wings', pod, 6)
fab('bond_tray', 'Bonding tray (tool)', tray, 1, order=False)

# bed orientation
tub_p = R.on_bed(tub)
lid_r = lid.copy()
lid_r.rotate(V(0, 0, 0), V(1, 0, 0), 180)
bb = lid_r.BoundBox
shift = V(-bb.Center.x, -bb.Center.y, -bb.ZMin)
lid_bodies = []
for name, part, color in C.lid_materials(lid):
    c = part.copy()
    c.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    c.translate(shift)
    lid_bodies.append((name, c, color))
lid_p = R.moved(lid_r, shift.x, shift.y, shift.z)
bar_p = R.on_bed(bar)
pod_r = pod.copy()
pod_r.rotate(V(0, 0, 0), V(0, 1, 0), -90)
pod_p = R.on_bed(pod_r)
tray_p = R.on_bed(tray)

for fname, sh, objs in (('tub.step', tub_p, [('tub', tub_p, R.C_TUB)]), ('lid.step', lid_p, lid_bodies),
                        ('lug_bar_x2.step', bar_p, [('lug_bar', bar_p, R.C_BAR)]), ('pod_x6.step', pod_p, [('pod', pod_p, R.C_POD)]),
                        ('bond_tray.step', tray_p, [('bond_tray', tray_p, R.C_TRAY)])):
    export(objs, os.path.join(OUT, fname))
    bb = sh.BoundBox
    bed, worst, flat = R.bed_report(sh)
    log(f"  {fname:16s} valid={sh.isValid()} solids={len(sh.Solids)}  {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.2f} mm  "
        f"volume {sh.Volume / 1000:.2f} cm3  bed contact {bed:.0f} mm2  steepest overhang {worst:.0f} deg  "
        f"widest flat ceiling {flat[0][0] if flat else 0:.1f} mm ({len(flat)} in all)")
log(f"  lid inlay: {lid_bodies[1][1].Volume:.2f} mm3 in the first {0.32} mm")
R.finish(log)
