"""Flush, two-layer lid graphics in the worn orientation."""
import FreeCAD
import Part
import params as P

V = FreeCAD.Vector
DEPTH = 0.32  # X2D first layer 0.20 plus one 0.12 mm layer
FONT_DIR = '/usr/share/fonts/noto/'
# Redraw the back rail and three overlapping cards in mm so the black channels
# and the blue rail survive slicing at the original icon width.
LOGO_OUTLINES = (
    ((0, 1.80), (5.90, 0), (5.90, 0.80), (0.80, 2.37),
     (0.80, 7.18), (2.12, 6.78), (2.86, 7.32), (0, 8.20)),
    ((1.80, 2.85), (5.05, 5.20), (5.05, 8.20), (1.80, 5.85)),
    ((3.45, 2.20), (6.85, 4.65), (6.85, 7.65), (5.70, 6.82),
     (5.70, 4.87), (3.45, 3.24)),
    ((5.20, 1.60), (8.80, 4.22), (8.80, 7.22), (7.50, 6.28),
     (7.50, 4.32), (5.20, 2.66)),
)


def lid_inlay():
    faces = []
    for outline in LOGO_OUTLINES:
        points = [V(x, -y, 0) for x, y in outline]
        faces.append(Part.Face(Part.makePolygon(points + points[:1])))
    layout = [(Part.makeCompound(faces), 4.3)]
    for label, y in (('Backplane', -3.10), ('Neuro Band', -7.80)):
        letters = Part.makeWireString(label, FONT_DIR, 'NotoSans-Black.ttf', 1.90)
        glyphs = []
        for i, wires in enumerate(letters):
            if wires:
                face = Part.makeFace(wires, 'Part::FaceMakerBullseye')
                face.translate(V(i * 0.16, 0, 0))
                glyphs.append(face)
        layout.append((Part.makeCompound(glyphs), y))
    pieces = []
    for group, y in layout:
        centre = group.BoundBox.Center
        group.translate(V(P.XC - centre.x, y - centre.y, P.Z_TOP - DEPTH))
        pieces.extend(face.extrude(V(0, 0, DEPTH)) for face in group.Faces)
    mark = Part.makeCompound(pieces)
    centre = mark.BoundBox.Center
    mark.translate(V(P.XC - centre.x, -centre.y, 0))
    mark.rotate(V(P.XC, 0, 0), V(0, 0, 1), 180)
    return mark
