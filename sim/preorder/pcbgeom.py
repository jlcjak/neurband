"""Minimal no-SWIG reader for KiCad 10 .kicad_pcb files (s-expression).

Extracts footprints/pads (absolute positions), tracks, vias and filled zone polygons so that the
pre-order analog review can measure coupling geometry. Read-only: never writes a board file.
"""
import math
import re

_TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def parse_sexpr(text):
    stack, cur = [], []
    for m in _TOK.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            if t[0] == '"':
                t = t[1:-1]
            cur.append(t)
    return cur[0]


def child(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def children(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def rot(x, y, deg):
    """KiCad rotation (degrees, CCW on screen with +y down)."""
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


class Board:
    def __init__(self, path):
        self.tree = parse_sexpr(open(path).read())
        self.pads, self.tracks, self.vias, self.zones, self.fps = [], [], [], [], {}
        for fp in children(self.tree, "footprint"):
            tr = child(fp, "transform")
            if tr is not None:
                t, r = child(tr, "translate"), child(tr, "rotate")
                fx, fy, frot = float(t[1]), float(t[2]), float(r[1]) if r else 0.0
            else:
                at = child(fp, "at")
                fx, fy = float(at[1]), float(at[2])
                frot = float(at[3]) if len(at) > 3 else 0.0
            layer = child(fp, "layer")[1]
            ref = None
            for p in children(fp, "property"):
                if p[1] == "Reference":
                    ref = p[2]
            self.fps[ref] = dict(x=fx, y=fy, rot=frot, layer=layer)
            for pad in children(fp, "pad"):
                pat = child(pad, "at")
                px, py = float(pat[1]), float(pat[2])
                prot = float(pat[3]) if len(pat) > 3 else 0.0
                dx, dy = rot(px, py, frot)
                size = child(pad, "size")
                net = child(pad, "net")
                layers = child(pad, "layers")[1:]
                self.pads.append(dict(ref=ref, num=pad[1], type=pad[2], shape=pad[3], x=fx + dx, y=fy + dy,
                                      w=float(size[1]), h=float(size[2]), rot=prot, layers=layers,
                                      net=net[-1] if net else ""))
        for s in children(self.tree, "segment"):
            st, en = child(s, "start"), child(s, "end")
            self.tracks.append(dict(x1=float(st[1]), y1=float(st[2]), x2=float(en[1]), y2=float(en[2]),
                                    w=float(child(s, "width")[1]), layer=child(s, "layer")[1],
                                    net=child(s, "net")[-1]))
        for v in children(self.tree, "via"):
            at = child(v, "at")
            self.vias.append(dict(x=float(at[1]), y=float(at[2]), size=float(child(v, "size")[1]),
                                  drill=float(child(v, "drill")[1]), net=child(v, "net")[-1],
                                  layers=child(v, "layers")[1:]))
        for z in children(self.tree, "zone"):
            net = child(z, "net")
            name = child(z, "name")
            lay = child(z, "layer")
            lays = child(z, "layers")
            zl = [lay[1]] if lay else list(lays[1:])
            fills = []
            for fpoly in children(z, "filled_polygon"):
                fl = child(fpoly, "layer")[1]
                pts = [(float(p[1]), float(p[2])) for p in child(fpoly, "pts") if p[0] == "xy"]
                fills.append((fl, pts))
            outline = child(z, "polygon")
            opts = [(float(p[1]), float(p[2])) for p in child(outline, "pts") if p[0] == "xy"] if outline else []
            self.zones.append(dict(net=net[-1] if net else None, name=name[1] if name else "", layers=zl,
                                   keepout=child(z, "keepout") is not None, fills=fills, outline=opts))

    def pad_poly(self, p, grow=0.0):
        """Shapely polygon for a pad (rect/roundrect/oval/circle approximated)."""
        from shapely.geometry import Point, Polygon
        from shapely import affinity
        w, h = p["w"] + 2 * grow, p["h"] + 2 * grow
        if p["shape"] == "circle":
            return Point(p["x"], p["y"]).buffer(w / 2, 16)
        if p["shape"] == "oval":
            r = min(w, h) / 2
            from shapely.geometry import LineString
            L = max(w, h) / 2 - r
            line = LineString([(-L, 0), (L, 0)]) if w >= h else LineString([(0, -L), (0, L)])
            g = line.buffer(r, 16)
        else:
            g = Polygon([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)])
        g = affinity.rotate(g, -p["rot"], origin=(0, 0))  # KiCad CCW with y down -> shapely sign flip
        return affinity.translate(g, p["x"], p["y"])
