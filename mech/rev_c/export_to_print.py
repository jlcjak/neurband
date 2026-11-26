"""export_to_print.py - write the four printable parts into to_print/, each already lying on the bed (Z = 0).

Run: /usr/bin/freecadcmd -c "__file__='mech/rev_c/export_to_print.py'; exec(open(__file__).read())"
(or with the GUI offscreen like the other scripts).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True
sys.neurband_band_lib = True

import FreeCAD, Part
import rc as R
import module as M
import band as B

V = FreeCAD.Vector
OUT = os.path.join(R.HERE, 'to_print')
os.makedirs(OUT, exist_ok=True)


def on_bed(sh):
    c = sh.copy()
    bb = c.BoundBox
    c.translate(V(-bb.Center.x, -bb.Center.y, -bb.ZMin))
    return c


def bed_report(sh):
    """Area touching the bed and the steepest overhang (0 = vertical wall, 90 = flat ceiling)."""
    import math
    bed = sum(f.Area for f in sh.Faces if f.BoundBox.ZMax < 1e-4)
    worst, flat = 0.0, 0.0
    for f in sh.Faces:
        if f.BoundBox.ZMin < 1e-4 and f.BoundBox.ZMax < 1e-4:
            continue
        try:
            u0, u1, v0, v1 = f.ParameterRange
            n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        except Exception:
            continue
        if n.z < -1e-3:
            ang = 90.0 - math.degrees(math.acos(max(-1.0, min(1.0, -n.z))))   # 90 = facing straight down
            if ang > 89.0:
                flat = max(flat, min(f.BoundBox.XLength, f.BoundBox.YLength))   # bridge span
            else:
                worst = max(worst, ang)
    return bed, worst, flat


cradle = M.build_cradle().copy()
cradle.rotate(V(0, 0, 0), V(1, 0, 0), 180)        # flat top on the bed, curved underside up

holder = M.build_holder().copy()
holder.rotate(V(0, 0, 0), V(1, 0, 0), 180)        # flat battery deck (Z = Z_HOLDER) on the bed

lid = M.build_lid().copy()
lid.rotate(V(0, 0, 0), V(1, 0, 0), 180)           # flat top on the bed

lug_bar = M.build_lug_bar().copy()                # flat on the bed (Z = 0..BAR_H, continuous end-to-end strands!)

pod = B.build_pod().copy()
pod.rotate(V(0, 0, 0), V(0, 1, 0), -90)            # flat X = -4.0 mm side on Z = 0, +X teardrops UP -> 0 mm bridge!

jig = B.build_jig().copy()

def fab(stem, name, shape, qty, order=True):
    """Backplane fab file beside the as-worn STEP (measured here, never typed in)."""
    import json, cadutil as U
    d = {"kind": "3dp", "name": name, "source": stem + ".step", "qty": qty,
         "options": {"process": "mjf", "material": "pa12", "color": "black"}, "features": U.features(shape)}
    if not order:
        d["order"] = False
    with open(os.path.join(R.HERE, stem + '.fab.json'), 'w') as f:
        json.dump(d, f, indent=2)
        f.write('\n')


log = R.Log('to_print')
fab('cradle', 'Module cradle', M.build_cradle(), 1)
fab('holder', 'Board holder & battery deck', M.build_holder(), 1)
fab('lid', 'Module lid', M.build_lid(), 1)
fab('lug_bar', 'Slide-in strap cross-bar', M.build_lug_bar(), 2)
fab('pod', 'Pod link', B.build_pod(), 6)
fab('bond_jig', 'Bonding jig (tool)', B.build_jig(), 1, order=False)
for fname, sh in (('cradle.step', cradle), ('holder.step', holder), ('lid.step', lid), ('lug_bar_x2.step', lug_bar), ('pod_x6.step', pod), ('bond_jig.step', jig)):
    sh = on_bed(sh)
    if fname == 'lid.step':
        import Import
        doc = FreeCAD.newDocument('LidPrint')
        transform = sh.Placement
        objects = []
        for name, part, color in M.lid_materials(M.build_lid()):
            part.Placement = transform.multiply(part.Placement)
            obj = doc.addObject('Part::Feature', name)
            obj.Shape = part
            if FreeCAD.GuiUp:
                obj.ViewObject.ShapeColor = color
            objects.append(obj)
        doc.recompute()
        if FreeCAD.GuiUp:
            import ImportGui
            ImportGui.export(objects, os.path.join(OUT, fname))
        else:
            Import.export(objects, os.path.join(OUT, fname))
        FreeCAD.closeDocument(doc.Name)
    else:
        sh.exportStep(os.path.join(OUT, fname))
    bb = sh.optimalBoundingBox(False)
    bed, worst, flat = bed_report(sh)
    log(f"  {fname:14s} valid={sh.isValid()} solids={len(sh.Solids)}  {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.2f} mm  "
        f"volume {sh.Volume / 1000:.2f} cm3  bed contact {bed:.0f} mm2  steepest overhang {worst:.0f} deg  widest bridge {flat:.1f} mm")
R.finish(log)
