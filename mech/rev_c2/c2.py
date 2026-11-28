"""c2.py - FreeCAD helpers and colours shared by the rev C2 part scripts (dimensions are in params.py).

Run a part script with the GUI offscreen so the STEP files keep their colours:
  unset DISPLAY WAYLAND_DISPLAY; QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c2/<part>.py
or, quicker and without colours:
  /usr/bin/freecadcmd -c "__file__='mech/rev_c2/<part>.py'; exec(open(__file__).read())"
Messages go to logs/<part>.log.
"""
import os, sys, math, json, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
MECH = os.path.dirname(HERE)
ROOT = os.path.dirname(MECH)
sys.path.insert(0, HERE)

import FreeCAD, Part
import params as P

V = FreeCAD.Vector
GUI = bool(FreeCAD.GuiUp)

C_TUB = C_LID = C_POD = C_BAR = (0.13, 0.14, 0.15)
C_INLAY = (0.11, 0.49, 0.96)
C_TRAY = (0.80, 0.80, 0.78)
C_STRAP = (0.11, 0.19, 0.36)
C_GOLD = (0.85, 0.68, 0.22)
C_FLEX = (0.85, 0.50, 0.10)
C_PCB = (0.05, 0.42, 0.16)
C_PARTS = (0.15, 0.15, 0.15)
C_LIPO = (0.78, 0.79, 0.82)
C_PCM = (0.86, 0.70, 0.12)
C_SKIN = (0.89, 0.70, 0.56)
C_WIRE = (0.75, 0.12, 0.10)


class Log:
    def __init__(self, name):
        os.makedirs(os.path.join(HERE, 'logs'), exist_ok=True)
        self.f = open(os.path.join(HERE, 'logs', name + '.log'), 'w')
        self(f"{name}: {datetime.datetime.now().isoformat(timespec='seconds')} gui={GUI}")

    def __call__(self, *a):
        msg = ' '.join(str(x) for x in a)
        self.f.write(msg + '\n')
        self.f.flush()
        if not GUI:
            print(msg)


def finish(log):
    log("done")
    log.f.close()
    if GUI:
        os._exit(0)


def check(shape, name, log, solids=1):
    ok = shape.isValid()
    log(f"  {name}: valid={ok} volume={shape.Volume / 1000:.3f} cm3 solids={len(shape.Solids)}")
    if not ok:
        raise RuntimeError(f"{name}: shape is not valid")
    if solids and len(shape.Solids) != solids:
        raise RuntimeError(f"{name}: {len(shape.Solids)} solids, expected {solids}")
    return shape


def _split(shape):
    sol = shape.Solids
    return [shape] if len(sol) <= 1 else sol


def save(stem, items, log, folder=HERE):
    """items: (name, shape, colour). Writes <stem>.FCStd and <stem>.step into folder."""
    doc = FreeCAD.newDocument(os.path.basename(stem).replace('-', '_'))
    objs = []
    for name, shape, col in items:
        for k, sh in enumerate(_split(shape)):
            o = doc.addObject('Part::Feature', name if k == 0 else f'{name}_{k:03d}')
            o.Shape = sh
            objs.append((o, col))
    doc.recompute()
    if GUI:
        for o, col in objs:
            o.ViewObject.ShapeColor = col
    fc, st = os.path.join(folder, stem + '.FCStd'), os.path.join(folder, stem + '.step')
    doc.saveAs(fc)
    if GUI:
        import ImportGui
        ImportGui.export([o for o, _ in objs], st)
    else:
        import Import
        Import.export([o for o, _ in objs], st)
    log(f"  saved {os.path.relpath(st, ROOT)}")
    FreeCAD.closeDocument(doc.Name)
    return st


# ---------------- solids ----------------
def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def rrect_wire(w, l, r, z, cx=0.0, cy=0.0):
    """Closed wire of a rounded rectangle w (X) x l (Y) at height z."""
    r = max(min(r, w / 2 - 1e-3, l / 2 - 1e-3), 0.0)
    hx, hy = w / 2, l / 2
    if r < 0.02:
        pts = [V(cx - hx, cy - hy, z), V(cx + hx, cy - hy, z), V(cx + hx, cy + hy, z), V(cx - hx, cy + hy, z)]
        return Part.makePolygon(pts + [pts[0]])
    edges = []
    cs = [(cx + hx - r, cy + hy - r, 0), (cx - hx + r, cy + hy - r, 90), (cx - hx + r, cy - hy + r, 180), (cx + hx - r, cy - hy + r, 270)]
    pts = []
    for (px, py, a0) in cs:
        a, b = math.radians(a0), math.radians(a0 + 90)
        m = math.radians(a0 + 45)
        p0 = V(px + r * math.cos(a), py + r * math.sin(a), z)
        pm = V(px + r * math.cos(m), py + r * math.sin(m), z)
        p1 = V(px + r * math.cos(b), py + r * math.sin(b), z)
        pts.append((p0, pm, p1))
    for k, (p0, pm, p1) in enumerate(pts):
        edges.append(Part.Arc(p0, pm, p1).toShape())
        q = pts[(k + 1) % 4][0]
        if p1.distanceToPoint(q) > 1e-6:
            edges.append(Part.makeLine(p1, q))
    return Part.Wire(edges)


def rrect(w, l, r, z0, z1, cx=0.0, cy=0.0):
    return Part.Face(rrect_wire(w, l, r, z0, cx, cy)).extrude(V(0, 0, z1 - z0))


def frustum(w0, l0, r0, z0, w1, l1, r1, z1, cx=0.0, cy=0.0):
    """Loft between two rounded rectangles (a 45 deg bevel when the size grows by 2 x the height)."""
    return Part.makeLoft([rrect_wire(w0, l0, r0, z0, cx, cy), rrect_wire(w1, l1, r1, z1, cx, cy)], True, True)


def prism_xz(pts, y0, y1):
    """Polygon given in (x, z), extruded along Y from y0 to y1."""
    w = Part.makePolygon([V(x, y0, z) for x, z in pts] + [V(pts[0][0], y0, pts[0][1])])
    return Part.Face(w).extrude(V(0, y1 - y0, 0))


def prism_yz(pts, x0, x1):
    """Polygon given in (y, z), extruded along X from x0 to x1."""
    w = Part.makePolygon([V(x0, y, z) for y, z in pts] + [V(x0, pts[0][0], pts[0][1])])
    return Part.Face(w).extrude(V(x1 - x0, 0, 0))


def prism_xy(pts, z0, z1):
    w = Part.makePolygon([V(x, y, z0) for x, y in pts] + [V(pts[0][0], pts[0][1], z0)])
    return Part.Face(w).extrude(V(0, 0, z1 - z0))


def octagon(hw, hh, ch):
    return [(-hw + ch, hh), (hw - ch, hh), (hw, hh - ch), (hw, -hh + ch), (hw - ch, -hh), (-hw + ch, -hh), (-hw, -hh + ch), (-hw, hh - ch)]


def fillet_edges(shape, r, pick, log=None, tag=''):
    edges = [e for e in shape.Edges if pick(e)]
    if not edges:
        if log:
            log(f"  fillet {tag}: no edges picked")
        return shape
    try:
        s = shape.makeFillet(r, edges)
        if s.isValid() and s.Volume > 0:
            return s
    except Exception as ex:
        if log:
            log(f"  fillet {tag} r={r} skipped on {len(edges)} edges: {ex}")
        return shape
    if log:
        log(f"  fillet {tag} r={r} gave an invalid shape, skipped")
    return shape


def chamfer_edges(shape, d, pick, log=None, tag=''):
    edges = [e for e in shape.Edges if pick(e)]
    if not edges:
        if log:
            log(f"  chamfer {tag}: no edges picked")
        return shape
    try:
        s = shape.makeChamfer(d, edges)
        if s.isValid() and s.Volume > 0:
            return s
    except Exception as ex:
        if log:
            log(f"  chamfer {tag} d={d} skipped on {len(edges)} edges: {ex}")
        return shape
    if log:
        log(f"  chamfer {tag} d={d} gave an invalid shape, skipped")
    return shape


def clash(a, b):
    try:
        return round(a.common(b).Volume, 3)
    except Exception:
        return -1.0


def moved(sh, dx=0.0, dy=0.0, dz=0.0):
    c = sh.copy()
    c.translate(V(dx, dy, dz))
    return c


def on_bed(sh):
    c = sh.copy()
    bb = c.BoundBox
    c.translate(V(-bb.Center.x, -bb.Center.y, -bb.ZMin))
    return c


def bed_report(sh, tol=1e-4):
    """Bed contact area, steepest overhang (deg from vertical; 90 = flat ceiling) and the widest flat ceiling.
    The part must already lie on Z = 0."""
    bed = sum(f.Area for f in sh.Faces if f.BoundBox.ZMax < tol)
    worst, flat = 0.0, []
    for f in sh.Faces:
        if f.BoundBox.ZMax < tol:
            continue
        try:
            u0, u1, v0, v1 = f.ParameterRange
            samples = [f.normalAt(u0 + (u1 - u0) * a, v0 + (v1 - v0) * b) for a in (0.2, 0.5, 0.8) for b in (0.2, 0.5, 0.8)]
        except Exception:
            continue
        nz = min(n.z for n in samples)
        if nz < -1e-3:
            ang = math.degrees(math.asin(min(1.0, -nz)))            # 0 = vertical wall, 90 = ceiling
            if ang > 89.0:
                bb = f.BoundBox
                flat.append((round(min(bb.XLength, bb.YLength), 2), round(max(bb.XLength, bb.YLength), 2), round(bb.ZMin, 2)))
            else:
                worst = max(worst, ang)
    flat.sort(reverse=True)
    return bed, worst, flat


def features(shape):
    bb = shape.BoundBox
    d = sorted([bb.XLength, bb.YLength, bb.ZLength], reverse=True)
    return {"volume_cm3": round(shape.Volume / 1000, 3), "area_cm2": round(shape.Area / 100, 2),
            "size_x_mm": round(d[0], 2), "size_y_mm": round(d[1], 2), "size_z_mm": round(d[2], 2)}
