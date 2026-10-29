"""Simplified C3 mechanical envelope; CAD (X,Y) = KiCad (X,-Y)."""
import os
import traceback
import FreeCAD as App
import Part
import ImportGui

WIDTH_MM = 13.2
DEPTH_MM = 16.6
HEIGHT_MM = 2.4
ANTENNA_DEPTH_MM = 5.4
SUBSTRATE_MM = 0.8  # illustrative internal split, not a shield specification
X_MIN_MM = -6.6
Y_MIN_MM = -5.6  # CAD; front faces -Y, antenna faces +Y
ROOT = os.path.join(os.environ.get('NEURBAND_ROOT', os.path.expanduser('~/neurband')), 'boards/neurband_main/layout/models')
log = open(ROOT + '/ESP32-C3-MINI-1.log', 'w', buffering=1)
try:
    doc = App.newDocument('ESP32_C3_MINI_1')
    objects = []
    for name, y, depth, z, height, color in [
        ('Substrate', Y_MIN_MM, DEPTH_MM, 0, SUBSTRATE_MM, (0.12, 0.30, 0.18)),
        ('SimplifiedShieldEnvelope', Y_MIN_MM, DEPTH_MM-ANTENNA_DEPTH_MM,
         SUBSTRATE_MM, HEIGHT_MM-SUBSTRATE_MM, (0.68, 0.70, 0.73)),
    ]:
        obj = doc.addObject('PartDesign::Feature', name)
        obj.Shape = Part.makeBox(WIDTH_MM, depth, height, App.Vector(X_MIN_MM, y, z))
        assert obj.Shape.isValid(), name
        objects.append(obj)
        log.write(name + ': shape.isValid()=True\n')
    doc.recompute()
    for obj, color in zip(objects, [(0.12, 0.30, 0.18), (0.68, 0.70, 0.73)]):
        obj.ViewObject.ShapeColor = color
    bounds = Part.makeCompound([o.Shape for o in objects]).BoundBox
    assert abs(bounds.XLength-WIDTH_MM)<1e-7
    assert abs(bounds.YLength-DEPTH_MM)<1e-7
    assert abs(bounds.ZLength-HEIGHT_MM)<1e-7
    log.write('CAD bounds mm: ' + str((bounds.XMin,bounds.XMax,bounds.YMin,bounds.YMax,bounds.ZMin,bounds.ZMax)) + '\n')
    doc.saveAs(ROOT + '/ESP32-C3-MINI-1.FCStd')
    ImportGui.export(objects, ROOT + '/ESP32-C3-MINI-1.step')
    log.write('PASS: nominal envelope 13.2 x 16.6 x 2.4 mm; colored STEP exported\n')
except BaseException:
    log.write(traceback.format_exc())
    log.close()
    os._exit(1)
log.close()
os._exit(0)
