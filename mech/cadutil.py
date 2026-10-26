"""cadutil.py - small helpers shared by the neurband FreeCAD part scripts.

Run part scripts with the GUI offscreen so STEP files carry colours:
  QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/<part>.py
Messages go to mech/logs/<part>.log (GUI stdout is not shown).
"""
import os, sys, json, math, datetime
import FreeCAD, Part

V = FreeCAD.Vector
MECH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(MECH)
GUI = bool(FreeCAD.GuiUp)

# colours (0..1)
C_TPU = (0.20, 0.20, 0.22)
C_PA12_BLACK = (0.27, 0.27, 0.29)
C_PA12_GREY = (0.52, 0.53, 0.55)
C_GOLD = (0.85, 0.68, 0.22)
C_SKIN = (0.89, 0.70, 0.56)
C_PCB = (0.05, 0.42, 0.16)
C_POLYIMIDE = (0.88, 0.47, 0.06)
C_WEBBING = (0.12, 0.13, 0.17)
C_VELCRO = (0.22, 0.22, 0.26)
C_LIPO = (0.78, 0.79, 0.82)
C_CONN = (0.08, 0.08, 0.08)
C_METAL = (0.72, 0.72, 0.75)
C_CLEAR = (0.92, 0.92, 0.85)


class Log:
    def __init__(self, name):
        os.makedirs(os.path.join(MECH, 'logs'), exist_ok=True)
        self.path = os.path.join(MECH, 'logs', name + '.log')
        self.f = open(self.path, 'w')
        self(f"{name}: {datetime.datetime.now().isoformat(timespec='seconds')} gui={GUI}")

    def __call__(self, *a):
        msg = ' '.join(str(x) for x in a)
        self.f.write(msg + '\n')
        self.f.flush()
        if not GUI:
            print(msg)


def check(shape, name, log):
    ok = shape.isValid()
    log(f"  {name}: valid={ok} volume={shape.Volume/1000:.3f} cm3 solids={len(shape.Solids)}")
    if not ok:
        raise RuntimeError(f"{name}: shape is not valid")
    return shape


def save(stem, items, log, folder=MECH):
    """items: list of (name, shape, colour). Saves <stem>.FCStd and <stem>.step in folder."""
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
    fc = os.path.join(folder, stem + '.FCStd')
    st = os.path.join(folder, stem + '.step')
    doc.saveAs(fc)
    if GUI:
        import ImportGui
        ImportGui.export([o for o, _ in objs], st)
    else:
        import Import
        Import.export([o for o, _ in objs], st)
    log(f"  saved {os.path.relpath(fc, ROOT)} and {os.path.relpath(st, ROOT)}")
    FreeCAD.closeDocument(doc.Name)
    return st


def _split(shape):
    """One object per solid: multi-solid compounds lose their colour in some STEP viewers.
    Touching/overlapping solids are fused first."""
    sol = shape.Solids
    if len(sol) <= 1:
        return [shape]
    try:
        f = sol[0].fuse(sol[1:]).removeSplitter()
        sol = f.Solids
    except Exception:
        pass
    return sol


def features(shape):
    try:
        bb = shape.optimalBoundingBox()
    except Exception:
        bb = shape.BoundBox
    dims = sorted([bb.XLength, bb.YLength, bb.ZLength], reverse=True)
    # also try rotations about Z for a tighter box (parts are mostly axis aligned)
    best = dims
    for deg in range(5, 90, 5):
        s = shape.copy()
        s.rotate(V(0, 0, 0), V(0, 0, 1), deg)
        b = s.BoundBox
        d = sorted([b.XLength, b.YLength, b.ZLength], reverse=True)
        if d[0] * d[1] * d[2] < best[0] * best[1] * best[2] - 1e-6:
            best = d
    return {"volume_cm3": round(shape.Volume / 1000, 3), "area_cm2": round(shape.Area / 100, 2),
            "size_x_mm": round(best[0], 2), "size_y_mm": round(best[1], 2), "size_z_mm": round(best[2], 2)}


def fab(stem, name, shape, qty, process, material, color, log, extra=None):
    d = {"kind": "3dp", "name": name, "source": stem + ".step", "qty": qty,
         "options": {"process": process, "material": material, "color": color},
         "features": features(shape)}
    if extra:
        d.update(extra)
    p = os.path.join(MECH, stem + '.fab.json')
    with open(p, 'w') as f:
        json.dump(d, f, indent=2)
        f.write('\n')
    log(f"  fab {os.path.relpath(p, ROOT)}: {d['features']}")


def finish(log):
    log("done")
    log.f.close()
    if GUI:
        os._exit(0)


# ---------- geometry helpers ----------
def rrect(w, l, r, h, z0=0.0):
    """Rounded rectangle w (X) x l (Y), corner radius r, extruded h from z0, centred on origin."""
    r = min(r, w / 2 - 1e-3, l / 2 - 1e-3)
    if r <= 0.01:
        return Part.makeBox(w, l, h, V(-w / 2, -l / 2, z0))
    b = Part.makeBox(w - 2 * r, l, h, V(-w / 2 + r, -l / 2, z0))
    b = b.fuse(Part.makeBox(w, l - 2 * r, h, V(-w / 2, -l / 2 + r, z0)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            b = b.fuse(Part.makeCylinder(r, h, V(sx * (w / 2 - r), sy * (l / 2 - r), z0)))
    return b.removeSplitter()


def stadium_y(w, h, depth, cx, cz, y0):
    """Rounded slot in an XZ plane (width w along X, height h along Z), cut depth along +Y from y0."""
    r = min(w, h) / 2
    if w >= h:
        s = Part.makeBox(w - 2 * r, depth, h, V(cx - w / 2 + r, y0, cz - h / 2))
        for sx in (-1, 1):
            s = s.fuse(Part.makeCylinder(r, depth, V(cx + sx * (w / 2 - r), y0, cz), V(0, 1, 0)))
    else:
        s = Part.makeBox(w, depth, h - 2 * r, V(cx - w / 2, y0, cz - h / 2 + r))
        for sz in (-1, 1):
            s = s.fuse(Part.makeCylinder(r, depth, V(cx, y0, cz + sz * (h / 2 - r)), V(0, 1, 0)))
    return s


def beam(p0, p1, width, thick, ymid):
    """Flat strip between two points (x, z) in the XZ plane, centred on the line, width along Y."""
    (x0, z0), (x1, z1) = p0, p1
    L = math.hypot(x1 - x0, z1 - z0)
    if L < 1e-4:
        return None
    b = Part.makeBox(L, width, thick, V(0, -width / 2, -thick / 2))
    ang = math.degrees(math.atan2(z1 - z0, x1 - x0))
    b.rotate(V(0, 0, 0), V(0, 1, 0), -ang)
    b.translate(V(x0, ymid, z0))
    return b


def pod_placement(x, z, ang, y):
    """Placement mapping a pod-local frame (X tangent, Z outward normal) to the wrist frame."""
    return FreeCAD.Placement(V(x, y, z), FreeCAD.Rotation(V(0, 1, 0), -math.degrees(ang)))
