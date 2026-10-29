"""wallcheck.py - minimum wall thickness of the rev C printed parts, measured on the exported STEPs.

Method: on every face, sample a UV grid (kept 0.3 mm inside the face's parameter range), shoot a
ray from the sample point along the inward normal and intersect it exactly with the solid
(Shape.common with a line). The first inside segment's length is the local wall thickness; it
counts only where the ray leaves through a roughly opposite face (normals > 120 deg apart), so
acute rims and edge wedges are not reported as walls.
Reports the minimum, the 1st percentile and where the minimum is, writes
mech/rev_c/wall_check.json and adds "min_wall_mm" to each part's fab.json.
Run: /usr/bin/freecadcmd -c "exec(open('mech/rev_c/wallcheck.py').read())"
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.path.join(os.environ.get('NEURBAND_ROOT', os.path.expanduser('~/neurband')), 'mech/rev_c')
import FreeCAD, Part

V = FreeCAD.Vector
PARTS = [p for p in os.environ.get('WALL_PARTS', 'module_base,module_lid,button_cap,strap_slide,charge_clip,cell_spacer,pod,bond_jig,swd_jig').split(',')]
RAY = 8.0           # longest wall considered
GRID = 0.6          # mm between samples (approx.)
MAX_PER_FACE = 120
EDGE_MARGIN = 0.3   # mm kept away from face boundaries (corner artefacts)
OPPOSITE = -0.5     # count a ray only if it exits through a roughly opposite face (a real wall)


def samples(face):
    u0, u1, v0, v1 = face.ParameterRange
    try:
        su = face.Surface
        # approximate parameter scale: length along u / v at the face centre
        um, vm = (u0 + u1) / 2, (v0 + v1) / 2
        du = (face.valueAt(min(um + 1e-3, u1), vm) - face.valueAt(um, vm)).Length / 1e-3 or 1.0
        dv = (face.valueAt(um, min(vm + 1e-3, v1)) - face.valueAt(um, vm)).Length / 1e-3 or 1.0
    except Exception:
        du = dv = 1.0
    nu = max(2, min(int((u1 - u0) * du / GRID) + 1, 30))
    nv = max(2, min(int((v1 - v0) * dv / GRID) + 1, 30))
    mu, mv = EDGE_MARGIN / max(du, 1e-6), EDGE_MARGIN / max(dv, 1e-6)
    out = []
    for i in range(nu):
        for j in range(nv):
            u = u0 + mu + (u1 - u0 - 2 * mu) * (i + 0.5) / nu
            v = v0 + mv + (v1 - v0 - 2 * mv) * (j + 0.5) / nv
            if u <= u0 or u >= u1 or v <= v0 or v >= v1:
                continue
            p = face.valueAt(u, v)
            if not face.isInside(p, 1e-4, True):
                continue
            out.append((u, v, p))
    if len(out) > MAX_PER_FACE:
        step = len(out) / MAX_PER_FACE
        out = [out[int(k * step)] for k in range(MAX_PER_FACE)]
    return out


def wall_at(solid, face, u, v, p):
    n = face.normalAt(u, v)
    if solid.isInside(p - n * 0.002, 1e-4, True):     # n points outward
        pass
    elif solid.isInside(p + n * 0.002, 1e-4, True):   # n points inward: flip
        n = -n
    else:
        return None
    d = -n                                    # inward
    a = p + d * 0.002
    seg = solid.common(Part.makeLine(a, a + d * RAY))
    for e in seg.Edges:
        q0, q1 = e.Vertexes[0].Point, e.Vertexes[-1].Point
        if min((q0 - a).Length, (q1 - a).Length) < 1e-3:
            q = q1 if (q0 - a).Length < (q1 - a).Length else q0
            if (q - a).Length > RAY - 1e-3:
                return None
            # exit face normal: a wall only if it faces roughly opposite to the start face
            vq = Part.Vertex(q)
            for g in solid.Faces:
                bb = g.BoundBox
                if not (bb.XMin - 1e-3 <= q.x <= bb.XMax + 1e-3 and bb.YMin - 1e-3 <= q.y <= bb.YMax + 1e-3 and bb.ZMin - 1e-3 <= q.z <= bb.ZMax + 1e-3):
                    continue
                if g.distToShape(vq)[0] < 1e-3:
                    uu, vv = g.Surface.parameter(q)
                    m = g.normalAt(uu, vv)
                    if solid.isInside(q + m * 0.002, 1e-4, True):   # make m the outward normal at the exit
                        m = -m
                    if m.dot(n) > OPPOSITE:
                        return None
                    return e.Length + 0.002
            return e.Length + 0.002
    return None


def measure(stem):
    sh = Part.read(os.path.join(HERE, stem + '.step'))
    solid = sh.Solids[0] if len(sh.Solids) == 1 else sh
    vals = []
    for f in solid.Faces:
        for u, v, p in samples(f):
            w = wall_at(solid, f, u, v, p)
            if w is not None:
                vals.append((w, p))
    vals.sort(key=lambda t: t[0])
    ws = [w for w, _ in vals]
    p1 = ws[max(0, int(0.01 * len(ws)) - 1)] if ws else None
    w0, p0 = vals[0] if vals else (None, None)
    thin = []
    for w, p in vals:
        if w >= 0.995:
            break
        if all((p - q).Length > 1.5 for _, q in thin):
            thin.append((w, p))
    return dict(min_wall_mm=round(w0, 2), p1_wall_mm=round(p1, 2), samples=len(ws),
                thin_spots=[[round(w, 2), round(p.x, 1), round(p.y, 1), round(p.z, 1)] for w, p in thin[:25]],
                min_at=[round(p0.x, 1), round(p0.y, 1), round(p0.z, 1)],
                thin_under_1mm=len([w for w in ws if w < 0.995]))


res = {}
for stem in PARTS:
    r = measure(stem)
    res[stem] = r
    print('WALL', stem, json.dumps(r))
    fp = os.path.join(HERE, stem + '.fab.json')
    if os.path.exists(fp):
        d = json.load(open(fp))
        d['min_wall_mm'] = r['min_wall_mm']
        json.dump(d, open(fp, 'w'), indent=2)
        open(fp, 'a').write('\n')
json.dump(res, open(os.path.join(HERE, 'wall_check.json'), 'w'), indent=1)
