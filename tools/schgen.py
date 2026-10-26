"""Tiny KiCad schematic generator.

Builds a .kicad_sch from Python: library symbols are copied (flattened) from the
KiCad stock libraries, symbols are placed on a 1.27 mm grid, and connections are
made with labels, power symbols and short wires computed from real pin positions.
"""
import math
import os
import re
import uuid as _uuid

KICAD_SYM = os.environ.get('KICAD_SYMBOL_DIR', os.path.expanduser('~/.backplane-bend/kicad/10.99.0-bp.4/share/kicad/symbols'))
LOCAL_LIBS = {}  # lib nickname -> path of a .kicad_sym file (project libraries)


# ---------------------------------------------------------------- s-expressions
def parse(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()"]+', text)
    stack, cur = [], []
    for t in tokens:
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            cur.append(t)
    return cur[0]


def dump(node, indent=0):
    if not isinstance(node, list):
        return node
    return "(" + " ".join(dump(x) for x in node) + ")"


def q(s):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return '"' + s + '"'


def uq(s):
    return s[1:-1] if s.startswith('"') else s


def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None


_UID = {"seed": "neurband", "n": 0}


def uid():
    """Deterministic UUIDs: same script -> byte-identical schematic (clean git diffs)."""
    _UID["n"] += 1
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"{_UID['seed']}/item/{_UID['n']}"))


# ---------------------------------------------------------------- library access
_cache = {}


def _load_symbol(lib, name):
    key = (lib, name)
    if key in _cache:
        return _cache[key]
    if lib in LOCAL_LIBS:
        tree = parse(open(LOCAL_LIBS[lib]).read())
        sym = [s for s in find(tree, "symbol") if uq(s[1]) == name][0]
    else:
        path = os.path.join(KICAD_SYM, lib + ".kicad_symdir", name + ".kicad_sym")
        tree = parse(open(path).read())
        sym = find(tree, "symbol")[0]
    ext = find1(sym, "extends")
    if ext:
        parent = _load_symbol(lib, uq(ext[1]))
        flat = [x for x in sym if not (isinstance(x, list) and x[0] == "extends")]
        props = {uq(p[1]) for p in find(flat, "property")}
        for x in parent[2:]:
            if isinstance(x, list) and x[0] == "property" and uq(x[1]) in props:
                continue
            if isinstance(x, list) and x[0] == "symbol":
                sub = list(x)
                sub[1] = q(uq(x[1]).replace(uq(parent[1]), name, 1))
                flat.append(sub)
            elif isinstance(x, list) and x[0] not in ("property",):
                if not find(flat, x[0]):
                    flat.append(x)
            elif isinstance(x, list):
                flat.append(x)
        sym = flat
    _cache[key] = sym
    return sym


def lib_symbol(lib_id):
    lib, name = lib_id.split(":")
    sym = [list(x) if isinstance(x, list) else x for x in _load_symbol(lib, name)]
    sym[1] = q(lib_id)
    return sym


def pins_of(lib_id):
    """Return {number: (x, y, angle, name)} in symbol coordinates (y up)."""
    lib, name = lib_id.split(":")
    sym = _load_symbol(lib, name)
    pins = {}

    def walk(n, unit):
        for x in n:
            if isinstance(x, list):
                if x[0] == "pin":
                    at = find1(x, "at")
                    num = uq(find1(x, "number")[1])
                    nm = uq(find1(x, "name")[1])
                    pins.setdefault(num, (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, nm, unit))
                elif x[0] == "symbol":
                    m = re.search(r"_(\d+)_\d+$", uq(x[1]))
                    walk(x, int(m.group(1)) if m else unit)
                else:
                    walk(x, unit)

    walk(sym, 0)
    return pins


# ---------------------------------------------------------------- schematic
def snap(v, g=1.27):
    return round(round(v / g) * g, 4)


def fmt(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class Sym:
    def __init__(self, sch, lib_id, ref, value, x, y, rot=0, footprint=None, fields=None, unit=1, dnp=False, mirror=None, in_bom=True):
        self.sch, self.lib_id, self.ref, self.value = sch, lib_id, ref, value
        self.x, self.y, self.rot, self.unit, self.mirror = snap(x), snap(y), rot, unit, mirror
        self.footprint = footprint
        self.fields = fields or {}
        self.dnp = dnp
        self.in_bom = in_bom
        self.pins = {k: v for k, v in pins_of(lib_id).items() if v[4] in (0, unit)}
        # deterministic symbol UUIDs (from project + reference + unit) so regenerating the schematic
        # keeps the board's footprint links; power symbols/flags get fresh ones
        if ref.startswith("#"):
            self.uuid = uid()
        else:
            self.uuid = str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"neurband/{sch.project}/{ref}/{unit}"))
        self.ref_at = None
        self.val_at = None
        self.hide_value = False
        self.hide_ref = False
        self.fsize = 1.27

    def _xf(self, px, py):
        if self.mirror == "y":
            px = -px
        a = math.radians(self.rot)
        rx = px * math.cos(a) - py * math.sin(a)
        ry = px * math.sin(a) + py * math.cos(a)
        return snap(self.x + rx, 0.01), snap(self.y - ry, 0.01)

    def pin(self, key):
        """Pin position by number or (unique) name -> (x, y, outward_angle)."""
        if key in self.pins:
            px, py, pa = self.pins[key][:3]
        else:
            hits = [v for v in self.pins.values() if v[3] == key]
            if len(hits) != 1:
                raise KeyError(f"{self.ref}: pin {key!r} -> {len(hits)} matches")
            px, py, pa = hits[0][:3]
        x, y = self._xf(px, py)
        if self.mirror == "y":
            pa = 180 - pa
        out = (pa + 180 + self.rot) % 360  # direction pointing away from the body
        return x, y, out

    def pin_numbers(self, key):
        return [n for n, v in self.pins.items() if v[3] == key or n == key]

    def sexpr(self, project, root):
        props = [("Reference", self.ref), ("Value", self.value), ("Footprint", self.footprint or ""), ("Datasheet", "")]
        props += list(self.fields.items())
        out = [f'(symbol (lib_id {q(self.lib_id)}) (at {fmt(self.x)} {fmt(self.y)} {self.rot})']
        if self.mirror:
            out.append(f"(mirror {self.mirror})")
        out.append(f"(unit {self.unit}) (exclude_from_sim no) (in_bom {'yes' if self.in_bom else 'no'}) (on_board yes) (dnp {'yes' if self.dnp else 'no'})")
        out.append(f"(uuid {q(self.uuid)})")
        for i, (k, v) in enumerate(props):
            if k == "Reference" and self.ref_at:
                at = self.ref_at
            elif k == "Value" and self.val_at:
                at = self.val_at
            else:
                at = (self.x, self.y + 2 * i, 0)
            hide = k not in ("Reference", "Value") or (k == "Value" and self.hide_value) or (k == "Reference" and self.hide_ref)
            just = at[3] if len(at) > 3 else None
            fs = fmt(self.fsize)
            eff = f"(effects (font (size {fs} {fs}))" + (f" (justify {just})" if just else "") + (" (hide yes)" if hide else "") + ")"
            ang = (at[2] + self.rot) % 180  # field angles are stored in symbol orientation
            out.append(f"(property {q(k)} {q(v)} (at {fmt(at[0])} {fmt(at[1])} {ang}) {eff})")
        for n in self.pins:
            out.append(f"(pin {q(n)} (uuid {q(uid())}))")
        out.append(f"(instances (project {q(project)} (path {q('/' + root)} (reference {q(self.ref)}) (unit {self.unit}))))")
        out.append(")")
        return "\n".join(out)


class Schematic:
    def __init__(self, title, paper="A2", project="proj"):
        self.title, self.paper, self.project = title, paper, project
        self.syms, self.items, self.lib_ids = [], [], []
        self.root = str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"neurband/{project}/root"))
        _UID["seed"], _UID["n"] = f"neurband/{project}", 0
        self._pwr = 0

    # placement ---------------------------------------------------------
    def add(self, lib_id, ref, value, x, y, rot=0, **kw):
        s = Sym(self, lib_id, ref, value, x, y, rot, **kw)
        self.syms.append(s)
        if lib_id not in self.lib_ids:
            self.lib_ids.append(lib_id)
        return s

    def power(self, kind, x, y, rot=0, lib=None):
        """Power symbol whose pin sits at (x, y). kind: GND, +3V3, VBUS, ... (net name = kind)."""
        self._pwr += 1
        lib_id = lib or {"VBAT": "power:+BATT", "+3V3A": "power:+3V3", "VCHG": "power:VBUS"}.get(kind, "power:" + kind)
        s = self.add(lib_id, f"#PWR{self._pwr:03d}", kind, x, y, rot)
        px, py, _ = s.pin("1")
        # move so the pin lands exactly on (x, y)
        s.x, s.y = snap(s.x + (x - px), 0.01), snap(s.y + (y - py), 0.01)
        down = kind.startswith("GND")
        s.val_at = (s.x, s.y + (3.81 if down else -3.81), 0)
        s.ref_at = (s.x, s.y, 0)
        s.hide_ref = True
        return s

    def wire(self, pts, color=None):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            stroke = f"(stroke (width 0) (type default)" + (f" (color {color} 1)" if color else "") + ")"
            self.items.append(f"(wire (pts (xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)})) {stroke} (uuid {q(uid())}))")

    def junction(self, x, y):
        self.items.append(f"(junction (at {fmt(x)} {fmt(y)}) (diameter 0) (color 0 0 0 0) (uuid {q(uid())}))")

    def label(self, name, x, y, angle=0, size=1.27):
        just = "right" if angle in (180, 270) else "left"
        self.items.append(
            f"(label {q(name)} (at {fmt(x)} {fmt(y)} {angle}) (fields_autoplaced yes) "
            f"(effects (font (size {size} {size})) (justify {just} bottom)) (uuid {q(uid())}))"
        )

    def noconnect(self, x, y):
        self.items.append(f"(no_connect (at {fmt(x)} {fmt(y)}) (uuid {q(uid())}))")

    def text(self, s, x, y, size=1.27, bold=False, angle=0):
        b = " (bold yes)" if bold else ""
        self.items.append(
            f"(text {q(s)} (exclude_from_sim no) (at {fmt(x)} {fmt(y)} {angle}) "
            f"(effects (font (size {size} {size}){b}) (justify left bottom)) (uuid {q(uid())}))"
        )

    def rect(self, x1, y1, x2, y2, fill=None, color=None, title=None):
        fc = f"(fill (type color) (color {fill} 0.12))" if fill else "(fill (type none))"
        sc = f"(stroke (width 0.25) (type dash) (color {color or fill or '0 0 0'} 1))"
        self.items.append(f"(rectangle (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) {sc} {fc} (uuid {q(uid())}))")
        if title:
            self.text(title, x1 + 1.27, y1 + 3.81, size=2.54, bold=True)

    # connection helpers -------------------------------------------------
    def pin_label(self, sym, pin, net, stub=2.54):
        """Short wire stub out of a pin plus a net label at its end."""
        x, y, a = sym.pin(pin)
        dx, dy = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}[int(a) % 360]
        ex, ey = snap(x + dx * stub, 0.01), snap(y + dy * stub, 0.01)
        self.wire([(x, y), (ex, ey)])
        la = {0: 0, 90: 90, 180: 180, 270: 270}[int(a) % 360]
        self.label(net, ex, ey, la)
        return ex, ey

    def pin_power(self, sym, pin, kind, stub=2.54):
        x, y, a = sym.pin(pin)
        dx, dy = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}[int(a) % 360]
        ex, ey = snap(x + dx * stub, 0.01), snap(y + dy * stub, 0.01)
        if stub:
            self.wire([(x, y), (ex, ey)])
        down = kind.startswith("GND")
        self.power(kind, ex, ey)
        return ex, ey

    def flag(self, x, y, dx=5.08):
        """PWR_FLAG on a short wire to the right of (x, y)."""
        self.wire([(x, y), (x + dx, y)])
        f = self.add("power:PWR_FLAG", f"#FLG{len(self.syms):03d}", "PWR_FLAG", x + dx, y)
        f.hide_ref = True
        f.ref_at = (x + dx, y, 0)
        f.val_at = (x + dx, y - 3.81, 0)
        return f

    def pin_nc(self, sym, pin):
        x, y, _ = sym.pin(pin)
        self.noconnect(x, y)

    def connect(self, a, b, via="hv"):
        """Orthogonal wire between two points."""
        (x1, y1), (x2, y2) = a[:2], b[:2]
        if x1 == x2 or y1 == y2:
            self.wire([(x1, y1), (x2, y2)])
        elif via == "hv":
            self.wire([(x1, y1), (x2, y1), (x2, y2)])
        else:
            self.wire([(x1, y1), (x1, y2), (x2, y2)])

    # output -------------------------------------------------------------
    def _paper(self):
        if self.paper.startswith("User"):
            _, w, h = self.paper.split()
            return f'(paper "User" {w} {h})'
        return f"(paper {q(self.paper)})"

    def write(self, path):
        libs = "\n".join(dump(lib_symbol(l), 1) for l in self.lib_ids)
        body = "\n".join(s.sexpr(self.project, self.root) for s in self.syms)
        items = "\n".join(self.items)
        txt = f"""(kicad_sch
(version 20250114)
(generator "neurband_schgen")
(generator_version "9.0")
(uuid {q(self.root)})
{self._paper()}
(title_block (title {q(self.title)}) (company "neurband"))
(lib_symbols
{libs}
)
{items}
{body}
(sheet_instances (path "/" (page "1")))
(embedded_fonts no)
)
"""
        with open(path, "w") as f:
            f.write(txt)
