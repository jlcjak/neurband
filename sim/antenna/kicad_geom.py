"""Extract the RF-relevant geometry of neurband rev C from the native .kicad_pcb.

No pcbnew module is needed: the file is parsed as an s-expression.  Output is
sim/antenna/build/geom.json in KiCad board coordinates (mm, y down).

Run: python sim/antenna/kicad_geom.py
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PCB = os.path.join(ROOT, 'boards', 'neurband_c', 'neurband_c.kicad_pcb')
OUT = os.path.join(HERE, 'build', 'geom.json')

TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def parse(text):
    stack, cur = [], []
    for m in TOK.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append(cur)
            cur = []
        elif t == ')':
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            if t[0] == '"':
                t = t[1:-1]
            cur.append(t)
    return cur[0]


def kids(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def kid(node, name):
    k = kids(node, name)
    return k[0] if k else None


def pts(node):
    p = kid(node, 'pts')
    return [(float(c[1]), float(c[2])) for c in p if isinstance(c, list) and c[0] == 'xy']


def fp_xform(fp):
    """(x0, y0, rot_deg) of a footprint; KiCad 10 uses (transform (translate) (rotate))."""
    tr = kid(fp, 'transform')
    if tr is not None:
        t = kid(tr, 'translate')
        r = kid(tr, 'rotate')
        return float(t[1]), float(t[2]), float(r[1]) if r else 0.0
    at = kid(fp, 'at')
    return float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0


def to_global(x0, y0, rot, lx, ly):
    # KiCad: positive rotation is counter-clockwise on screen with y down.
    a = math.radians(rot)
    return (x0 + lx * math.cos(a) + ly * math.sin(a),
            y0 - lx * math.sin(a) + ly * math.cos(a))


def main():
    root = parse(open(PCB).read())
    out = {'source': 'boards/neurband_c/neurband_c.kicad_pcb'}

    # board outline
    segs = []
    for g in kids(root, 'gr_line') + kids(root, 'gr_rect'):
        if kid(g, 'layer')[1] != 'Edge.Cuts':
            continue
        s, e = kid(g, 'start'), kid(g, 'end')
        segs.append([g[0], float(s[1]), float(s[2]), float(e[1]), float(e[2])])
    for g in kids(root, 'gr_arc'):
        if kid(g, 'layer')[1] == 'Edge.Cuts':
            s, m_, e = kid(g, 'start'), kid(g, 'mid'), kid(g, 'end')
            segs.append(['arc', float(s[1]), float(s[2]), float(e[1]), float(e[2])])
    xs = [v for s in segs for v in (s[1], s[3])]
    ys = [v for s in segs for v in (s[2], s[4])]
    out['edge_segments'] = segs
    out['board_bbox'] = [min(xs), min(ys), max(xs), max(ys)]

    # footprints: antenna polygon, pads of RF nets
    rf_fps = {}
    for fp in kids(root, 'footprint'):
        name = fp[1]
        x0, y0, rot = fp_xform(fp)
        ref = None
        for p in kids(fp, 'property'):
            if p[1] == 'Reference':
                ref = p[2]
        pads = []
        for pad in kids(fp, 'pad'):
            at = kid(pad, 'at')
            sz = kid(pad, 'size')
            net = kid(pad, 'net')
            lay = kid(pad, 'layers')
            gx, gy = to_global(x0, y0, rot, float(at[1]), float(at[2]))
            prot = (float(at[3]) if len(at) > 3 else 0.0)
            pads.append({'num': pad[1], 'type': pad[2], 'shape': pad[3], 'x': gx, 'y': gy,
                         'rot': prot, 'w': float(sz[1]), 'h': float(sz[2]),
                         'net': net[1] if net else '', 'layers': lay[1:] if lay else []})
        rec = {'name': name, 'x': x0, 'y': y0, 'rot': rot, 'pads': pads}
        if 'SWRA117D' in name:
            polys = []
            for fpp in kids(fp, 'fp_poly'):
                if kid(fpp, 'layer')[1] == 'F.Cu':
                    polys.append([to_global(x0, y0, rot, x, y) for x, y in pts(fpp)])
            rec['copper_polys'] = polys
            out['antenna'] = rec
        if any(p['net'] not in ('', 'GND') and ('AE1' in p['net'] or 'ANT' in p['net'].upper()
               or 'RF' in p['net'].upper()) for p in pads):
            rf_fps[ref] = rec
    out['rf_footprints'] = rf_fps

    # nets of the RF chain
    rfnets = sorted({p['net'] for r in rf_fps.values() for p in r['pads']
                     if p['net'] not in ('', 'GND')})
    out['rf_nets'] = rfnets

    # tracks
    tracks = []
    for t in kids(root, 'segment'):
        net = kid(t, 'net')[1]
        s, e = kid(t, 'start'), kid(t, 'end')
        tracks.append({'net': net, 'layer': kid(t, 'layer')[1], 'w': float(kid(t, 'width')[1]),
                       'x1': float(s[1]), 'y1': float(s[2]), 'x2': float(e[1]), 'y2': float(e[2])})
    out['rf_tracks'] = [t for t in tracks if t['net'] in rfnets]

    vias = []
    for v in kids(root, 'via'):
        at = kid(v, 'at')
        vias.append({'net': kid(v, 'net')[1], 'x': float(at[1]), 'y': float(at[2]),
                     'd': float(kid(v, 'size')[1]), 'drill': float(kid(v, 'drill')[1])})
    out['gnd_vias'] = [v for v in vias if v['net'] == 'GND']

    # zones: filled GND polygons per layer, keepouts
    gnd, keep = {}, []
    for z in kids(root, 'zone'):
        name = kid(z, 'name')[1] if kid(z, 'name') else ''
        layers = kid(z, 'layers')[1:] if kid(z, 'layers') else [kid(z, 'layer')[1]]
        if kid(z, 'keepout') is not None:
            keep.append({'name': name, 'layers': layers, 'outline': pts(kid(z, 'polygon'))})
            continue
        net = kid(z, 'net')[1] if kid(z, 'net') else ''
        for fpoly in kids(z, 'filled_polygon'):
            lay = kid(fpoly, 'layer')[1]
            gnd.setdefault(lay, []).append(pts(fpoly))
    out['gnd_fill'] = gnd
    out['keepouts'] = keep
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'))
    print('bbox', out['board_bbox'])
    print('rf nets', rfnets)
    print('rf fps', {k: (v['name'], round(v['x'], 2), round(v['y'], 2), v['rot']) for k, v in rf_fps.items()})
    for t in out['rf_tracks']:
        print('trk', t)
    print('gnd fill', {k: (len(v), sum(len(p) for p in v)) for k, v in gnd.items()})
    print('keepouts', [(k['name'], k['layers']) for k in keep])
    print('antenna polys', [len(p) for p in out['antenna']['copper_polys']])


if __name__ == '__main__':
    main()
