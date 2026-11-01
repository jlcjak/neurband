#!/usr/bin/env python3
"""REV C.2 deterministic flex artwork: every track is placed explicitly, in straight 0/45/90 degree segments.

Paired trunks run on F.Cu through the pod gaps; each proximal (P) electrode crosses under its pod's bias
electrode on B.Cu; in the housing-captured root every line drops to B.Cu in two staggered via rows and runs
straight down the tail to its finger. Which pod lands on which finger is flex_pinmap.TAIL, chosen so that
nothing crosses (firmware maps the channels). KiCad is the connectivity/DRC acceptance gate.
"""
from __future__ import annotations
import os
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import uuid
import pyclipper
import shapely
from shapely.geometry import box
from shapely.ops import unary_union
from KicadModTree import Footprint, FootprintType, Pad, Polygon, Property, KicadFileHandler

HERE = Path(__file__).resolve().parent
CLI = Path(os.environ.get('KICAD_CLI', os.path.expanduser('~/.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli')))
NAME = 'neurband_c_flex'
POD_PITCH = 18.0
POD_WIDTH = 7.1  # 6.5 mm electrode + two 0.30 mm copper/outline margins.
POD_LENGTH = 30.0
TAIL_LENGTH = 8.5
STIFFENER_LENGTH = 3.7
WIDTH = 0.1
CLEARANCE = 0.1
VIA_D = 0.6      # 0.15 mm annular ring on the 0.30 mm drill (flex: more ring than rigid minimum)
VIA_DRILL = 0.3
ORIGIN = (65.0, 35.0)
NS = uuid.UUID('973b1454-8245-4b50-a64c-3bf6d0613e84')
from flex_pinmap import TAIL                                  # noqa: E402
LANES = [3.55, 3.75, 3.95, 4.15, 5.85, 6.05, 6.25, 6.45]    # trunk lanes through every pod's B-N gap
ROW = {1: 7.0, 0: 7.7}       # root via rows for the trunk lines (odd / even finger), staggered
POD4 = {'E4P': (8.25, 9.85), 'E4N': (8.45, 9.15)}           # pod 4 pair across the root: (lane y, via y)
NECK_W, NECK_L = 0.2, 0.45   # widened track at electrode exits and vias (teardrop-like strain relief)
TAIL_W = 0.2                 # tail lines: 0.20 mm from the root vias to the fingers (stiffener edge, U-bend)
DISC_CLEAR = 3.6             # no B-side hatch within this radius of a P/N electrode centre (less C to GND)
ELECTRODE_MASK = -0.1        # coverlay overlaps each electrode edge by 0.1 mm (captures the pad)


def q(s):
    return json.dumps(str(s))


def uid(s):
    return str(uuid.uuid5(NS, str(s)))


def f(v):
    return f'{v:.6f}'.rstrip('0').rstrip('.') or '0'


def xy(p):
    return f'{f(p[0]+ORIGIN[0])} {f(p[1]+ORIGIN[1])}'


def parse_sexpr(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+|[()]', text)
    stack, root = [], None
    for token in tokens:
        if token == '(':
            obj = []
            if stack:
                stack[-1].append(obj)
            stack.append(obj)
        elif token == ')':
            root = stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    return root


def child(node, tag):
    return next(x for x in node if isinstance(x, list) and x[0] == tag)


def contract():
    sch = parse_sexpr((HERE / (NAME+'.kicad_sch')).read_text())
    root = child(sch, 'uuid')[1]
    refs = {}
    for sym in sch:
        if isinstance(sym, list) and sym[0] == 'symbol':
            props = {x[1]: x[2] for x in sym if isinstance(x, list) and x[0] == 'property'}
            refs[props['Reference']] = (child(sym, 'uuid')[1], props['Value'])
    netlist = parse_sexpr((HERE / (NAME+'.net')).read_text())
    pads = {}
    for net in child(netlist, 'nets')[1:]:
        name = child(net, 'name')[1]
        for node in net:
            if isinstance(node, list) and node[0] == 'node':
                pads[(child(node, 'ref')[1], child(node, 'pin')[1])] = name
    expected = {pin: (net if net == 'GND' else '/'+net) for pin, net in TAIL.items()}
    assert {n:pads['J1',str(n)] for n in range(1,21)} == expected
    assert all(pads[f'E{i}B','1']=='/BIAS_E' for i in range(1,9))
    return root, refs, pads, expected


def contact_x(pin):
    # U-turn is about world X: main TOP J1.1 must retain positive world X.
    return (10.5-pin)*0.5


class Board:
    def __init__(self, pitch, tail_length, schematic):
        self.size = 'C'
        self.pitch = pitch
        self.tip = POD_LENGTH/2+tail_length
        self.root,self.refs,self.pads,self.tail = schematic
        self.xs = {i:(i-3.5)*pitch for i in range(1,9)}
        self.nets = {n:i+1 for i,n in enumerate(sorted(set(self.pads.values())))}
        self.items,self.segments,self.vias,self.pad_shapes = [],[],[],[]
        self.endpoints = {}
        self.serial = 0

    def id(self):
        self.serial += 1
        return uid(self.serial)

    def track(self, net, points, layer='F.Cu', width=WIDTH):
        for a,b in zip(points,points[1:]):
            if math.dist(a,b)<1e-7:
                continue
            self.segments.append((net,a,b,layer,width))
            self.items.append(f'(segment (start {xy(a)}) (end {xy(b)}) (width {f(width)}) (layer "{layer}") (net {self.nets[net]}) (uuid "{self.id()}"))')

    def via(self, net, p):
        self.vias.append((net,p))
        self.items.append(f'(via (at {xy(p)}) (size {VIA_D}) (drill {VIA_DRILL}) (layers "F.Cu" "B.Cu") (net {self.nets[net]}) (uuid "{self.id()}"))')

    def line(self,a,b,layer='Edge.Cuts',width=0.05):
        if layer in ('F.SilkS','B.SilkS'):
            width=max(width,0.15)
        self.items.append(f'(gr_line (start {xy(a)}) (end {xy(b)}) (stroke (width {width}) (type default)) (layer "{layer}") (uuid "{self.id()}"))')

    def text(self,text,p,layer='F.SilkS',size=0.65):
        mirror='(justify mirror)' if layer.startswith('B.') else ''
        stroke=0.15 if layer in ('F.SilkS','B.SilkS') else 0.12
        self.items.append(f'(gr_text {q(text)} (at {xy(p)}) (layer "{layer}") (uuid "{self.id()}") (effects (font (size {size} {size}) (thickness {stroke})) {mirror}))')

    def footprint(self,ref,name,p,side,pads):
        stamp,value=self.refs[ref]
        body=[f'(footprint "neurband_c_flex:{name}" (layer "{side}.Cu") (uuid "{uid(ref)}") (at {xy(p)})',
              f'(property "Reference" {q(ref)} (at 0 -4) (layer "{side}.Fab") (effects (font (size 0.7 0.7)) (hide yes)))',
              f'(property "Value" {q(value)} (at 0 4) (layer "{side}.Fab") (effects (font (size 0.7 0.7)) (hide yes)))',
              '(property "MPN" "" (at 0 0) (layer "F.Fab") (effects (font (size 0.7 0.7)) (hide yes)))',
              '(property "LCSC" "" (at 0 0) (layer "F.Fab") (effects (font (size 0.7 0.7)) (hide yes)))',
              f'(path "/{self.root}/{stamp}") (attr smd exclude_from_pos_files exclude_from_bom{" allow_soldermask_bridges" if ref=="J1" else ""})']
        for num,local,dims,shape in pads:
            net=self.pads[ref,str(num)]
            self.pad_shapes.append((net,(p[0]+local[0],p[1]+local[1]),dims,shape,0 if side=='F' else 1))
            layers=f'"{side}.Cu"' if ref=='J1' else f'"{side}.Cu" "{side}.Mask"'
            margin=0 if ref=='J1' else ELECTRODE_MASK
            body.append(f'(pad "{num}" smd {shape} (at {f(local[0])} {f(local[1])}) (size {f(dims[0])} {f(dims[1])}) (layers {layers}) (solder_mask_margin {margin}) (net {self.nets[net]} {q(net)}) (uuid "{uid(ref+str(num))}"))')
        if ref=='J1':
            pts=' '.join(f'(xy {f(x)} {f(y)})' for x,y in [(-5.25,-1.65),(5.25,-1.65),(5.25,1.9),(-5.25,1.9)])
            body.append(f'(fp_poly (pts {pts}) (stroke (width 0) (type default)) (fill solid) (layer "B.Mask") (uuid "{self.id()}"))')
        self.items.append('\n'.join(body+[')']))

    def geometry(self):
        pods=[box(x-POD_WIDTH/2,-POD_LENGTH/2,x+POD_WIDTH/2,POD_LENGTH/2).buffer(-0.8).buffer(0.8,quad_segs=12) for x in self.xs.values()]
        spine=box(self.xs[1],-0.6,self.xs[8],7)
        # Rounded cable leading corners R0.30; 10.50 mm tab width.
        tail=box(-5.25,3,5.25,self.tip).buffer(-0.3).buffer(0.3,quad_segs=10)
        outline=unary_union(pods+[spine,tail]).buffer(0.6,quad_segs=12).buffer(-0.6,quad_segs=12)
        assert outline.geom_type=='Polygon' and outline.is_valid
        self.outline=outline
        self.contour=[(round(x,6),round(y,6)) for x,y in list(outline.exterior.coords)[:-1]]
        for a,b in zip(self.contour,self.contour[1:]+self.contour[:1]):
            self.line(a,b)
        for i,x in self.xs.items():
            for kind,y in [('P',-10),('B',0),('N',10)]:
                self.footprint(f'E{i}{kind}','Electrode_D6.5mm',(x,y),'F',[(1,(0,0),(6.5,6.5),'circle')])
            for k,y in enumerate((-5,5)):
                self.items.append(f'''(footprint "neurband_c_flex:Alignment_D1.2mm" (layer "F.Cu") (uuid "{uid('H'+str(i)+str(k))}") (at {xy((x,y))})
                  (property "Reference" "H{i}{k}" (at 0 0) (layer "F.Fab") (effects (font (size 0.6 0.6)) (hide yes)))
                  (property "Value" "Alignment 1.2mm" (at 0 0) (layer "F.Fab") (effects (font (size 0.6 0.6)) (hide yes)))
                  (attr through_hole board_only exclude_from_pos_files exclude_from_bom)
                  (pad "" np_thru_hole circle (at 0 0) (size 1.2 1.2) (drill 1.2) (layers "*.Cu") (uuid "{self.id()}")))''')
            self.text(str(i),(x,-14),size=0.8)
            self.text(str(i),(x,-14),'B.SilkS',0.8)
        self.footprint('J1','FPC_Tail_20_P0.5mm',(0,self.tip-1.9),'B',[(p,(contact_x(p),0),(0.3,3.2),'rect') for p in range(1,21)])
        self.text('1',(4.3,self.tip-4.3),'B.SilkS',0.8)
        self.text('20',(-3.8,self.tip-4.3),'B.SilkS',0.8)
        self.text('1',(4.3,self.tip-7.1),'F.SilkS',0.8)
        self.text('C / SKIN',(0,12.6),'F.SilkS',0.8)
        self.text('OUTER',(0,12.6),'B.SilkS',0.8)
        self.text('Optional: 2-3 SMD spring pins, 2 mm heads per round ENIG pad; no paste stencil',(self.xs[4],-19),'F.Fab',0.8)
        stiff=[(-5.25,self.tip-STIFFENER_LENGTH),(5.25,self.tip-STIFFENER_LENGTH),(5.25,self.tip),(-5.25,self.tip)]
        self.items.append(f'(gr_rect (start {xy(stiff[0])}) (end {xy(stiff[2])}) (stroke (width 0) (type default)) (fill yes) (layer "User.2") (uuid "{self.id()}"))')
        self.text('F-side PI stiffener; total 0.30 +/-0.03 mm',(0,self.tip+3),'User.2',0.7)
        self.text('Root y3..15 captured; bend only y15..stiffener',(0,17),'User.1',0.65)

    def path(self, net, points, layer='F.Cu', start=None, end=None):
        """Straight segments through `points`, widened to NECK_W at either end (teardrop-like strain relief):
        start/end = 'via' widens the first/last NECK_L mm; a number r (an electrode radius, the path starting at
        the pad centre) widens through the pad and NECK_L beyond its edge. The rest is WIDTH."""
        def cut(pts, length):
            out, cur = [pts[0]], pts[0]
            for i, nxt in enumerate(pts[1:], 1):
                d = math.dist(cur, nxt)
                if d >= length:
                    t = length / d if d else 0
                    c = (cur[0] + (nxt[0] - cur[0]) * t, cur[1] + (nxt[1] - cur[1]) * t)
                    return out + [c], [c] + pts[i:]
                out.append(nxt); length -= d; cur = nxt
            return out, None
        def width(spec):
            return None if spec is None else NECK_L + (0 if spec == 'via' else spec)
        head, body, tail = None, points, None
        if width(start):
            head, body = cut(body, width(start))
        if body and width(end):
            rev, rest = cut(body[::-1], width(end))
            if rest is None:             # short path: wide all the way
                head, body = (head or []) + body[1:] if head else body, None
            else:
                tail, body = rev[::-1], rest[::-1]
        for seg, w in ((head, NECK_W), (body, WIDTH), (tail, NECK_W)):
            if seg and len(seg) > 1:
                self.track(net, seg, layer, w)

    def route(self):
        """Explicit straight-line routing; see the module docstring."""
        pin_of = {net: pin for pin, net in TAIL.items()}
        tip_y = self.tip - 1.9
        R = 3.25
        # ---- pods 1-3 (heading +x to the root) and 5-8 (heading -x), as paired lanes through the pod gaps
        for group, direction in ((list(range(1, 4)), 1), (list(range(8, 4, -1)), -1)):
            for rank, i in enumerate(group):
                x = self.xs[i]
                ys = LANES[2 * rank:2 * rank + 2]
                kinds = 'PN' if direction == 1 else 'NP'          # upper lane first
                for k, kind in enumerate(kinds):
                    name = f'E{i}{kind}'
                    net = '/' + name
                    lane = ys[k]
                    xf = contact_x(pin_of[name])
                    vy = ROW[pin_of[name] % 2]
                    if kind == 'P':
                        vx = x - 2.45
                        self.path(net, [(x, -10), (vx, -10 + 2.45), (vx, -6.8)], start=R, end='via')
                        self.via(net, (vx, -6.8))
                        self.path(net, [(vx, -6.8), (vx, 7.05)], 'B.Cu', 'via', 'via')   # under the bias electrode
                        self.via(net, (vx, 7.05))
                        self.path(net, [(vx, 7.05), (vx, lane), (xf, lane), (xf, vy)], start='via', end='via')
                    else:
                        vx = x + 2.45
                        self.path(net, [(x, 10), (vx, 10 - 2.45), (vx, lane), (xf, lane), (xf, vy)], start=R, end='via')
                    self.via(net, (xf, vy))
                    self.track(net, [(xf, vy), (xf, tip_y)], 'B.Cu', TAIL_W)
        # ---- pod 4 sits at the root: its pair runs across the root below the via rows
        x = self.xs[4]
        p_lane, p_via = POD4['E4P']
        n_lane, n_via = POD4['E4N']
        xp, xn = contact_x(pin_of['E4P']), contact_x(pin_of['E4N'])
        vx = x - 2.45
        self.path('/E4P', [(x, -10), (vx, -10 + 2.45), (vx, -6.8)], start=R, end='via')
        self.via('/E4P', (vx, -6.8))
        self.path('/E4P', [(vx, -6.8), (vx, 7.05)], 'B.Cu', 'via', 'via')
        self.via('/E4P', (vx, 7.05))
        b = (vx - (p_lane - 7.05), p_lane)                            # 45 deg down-left onto its lane
        self.path('/E4P', [(vx, 7.05), b, (xp, p_lane), (xp, p_via)], start='via', end='via')
        c = (x - (10 - n_lane), n_lane)                               # 45 deg up-left out of the pad
        self.path('/E4N', [(x, 10), c, (xn, n_lane), (xn, n_via)], start=R, end='via')
        for net, xv, yv in (('/E4P', xp, p_via), ('/E4N', xn, n_via)):
            self.via(net, (xv, yv))
            self.track(net, [(xv, yv), (xv, tip_y)], 'B.Cu', TAIL_W)
        # ---- bias: one bus straight through the middle electrodes; tail fingers 2/19 join it by vias
        xb = [contact_x(19), contact_x(2)]                            # -4.25, +4.25
        self.track('/BIAS_E', [(self.xs[1], 0), (xb[0], 0)], width=0.25)
        self.track('/BIAS_E', [(xb[0], 0), (xb[1], 0)], width=0.25)
        self.track('/BIAS_E', [(xb[1], 0), (self.xs[8], 0)], width=0.25)
        for xv in xb:
            self.via('/BIAS_E', (xv, 0))
            self.track('/BIAS_E', [(xv, 0), (xv, tip_y)], 'B.Cu', TAIL_W)
        # ---- ground: per pod an F-side bar through the P-B gap and two B-side verticals; the free links
        # carry one 0.2 mm B-side return at y GY, away from the F-side lanes (no copper stacked across a bend);
        # across the root the two sides meet on F.Cu at y 2.3 and run down the tail to fingers 1 and 20
        GY = 1.5
        for i, x in self.xs.items():
            for dx in (-2.95, 2.95):
                self.via('GND', (x + dx, -6))
                if not (i == 1 and dx < 0 or i == 8 and dx > 0):
                    self.track('GND', [(x + dx, -6), (x + dx, GY)], 'B.Cu')
            self.track('GND', [(x - 2.95, -6), (x + 2.95, -6)])
        for i in range(1, 8):
            a_, b_ = self.xs[i] + 2.95, self.xs[i + 1] - 2.95
            if i == 3:
                for xg, pin in ((a_, 20), (b_, 1)):
                    xc = contact_x(pin)
                    self.track('GND', [(xg, GY), (xc, GY), (xc, 2.3)], 'B.Cu', 0.2)
                    self.via('GND', (xc, 2.3))
                    self.track('GND', [(xc, 2.3), (xc, tip_y)], 'B.Cu', 0.2)
                self.track('GND', [(contact_x(20), 2.3), (contact_x(1), 2.3)], 'F.Cu', 0.2)
            else:
                self.track('GND', [(a_, GY), (b_, GY)], 'B.Cu', 0.2)

    def shield(self):
        # Rule areas: no B-side pour behind the P/N skin discs. A grounded hatch right behind a 6.5 mm disc is
        # ~20 pF per electrode, which converts electrode-impedance mismatch into differential mains pickup.
        for x in self.xs.values():
            for y in (-10, 10):
                pts=' '.join(f'(xy {xy((x+DISC_CLEAR*math.cos(a/32*2*math.pi), y+DISC_CLEAR*math.sin(a/32*2*math.pi)))})' for a in range(32))
                self.items.append(f'''(zone (net 0) (net_name "") (layer "B.Cu") (uuid "{self.id()}") (hatch edge 0.5)
                  (connect_pads (clearance 0)) (min_thickness 0.25)
                  (keepout (tracks allowed) (vias allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
                  (polygon (pts {pts})))''')
        contours=[[(x-POD_WIDTH/2,-POD_LENGTH/2),(x+POD_WIDTH/2,-POD_LENGTH/2),(x+POD_WIDTH/2,POD_LENGTH/2),(x-POD_WIDTH/2,POD_LENGTH/2)] for x in self.xs.values()]
        contours.append([(-5.25,3),(5.25,3),(5.25,self.tip-STIFFENER_LENGTH),(-5.25,self.tip-STIFFENER_LENGTH)])
        for contour in contours:
            pts=' '.join(f'(xy {xy(p)})' for p in contour)
            self.items.append(f'''(zone (net {self.nets['GND']}) (net_name "GND") (layer "B.Cu") (uuid "{self.id()}")
              (hatch edge 0.5) (connect_pads yes (clearance 0.127)) (min_thickness 0.15)
              (fill yes (mode hatch) (thermal_gap 0.2) (thermal_bridge_width 0.2)
              (hatch_thickness 0.2) (hatch_gap 0.8) (hatch_orientation 45)
              (hatch_smoothing_level 0) (hatch_smoothing_value 0) (island_removal_mode 0) (island_area_min 0))
              (polygon (pts {pts})))''')

    def save(self,path):
        layers=[(0,'F.Cu','signal'),(31,'B.Cu','signal'),(36,'B.SilkS','user'),(37,'F.SilkS','user'),(38,'B.Mask','user'),(39,'F.Mask','user'),(44,'Edge.Cuts','user'),(48,'B.Fab','user'),(49,'F.Fab','user'),(50,'User.1','user'),(51,'User.2','user "Stiffener"')]  # named so the Gerber is "...-Stiffener.gbr"
        header=f'''(kicad_pcb (version 20241229) (generator "neurband_flex_c")
          (general (thickness 0.099)) (paper "A3")
          (layers {' '.join(f'({n} "{name}" {kind})' for n,name,kind in layers)})
          (setup (pad_to_mask_clearance 0) (solder_mask_min_width 0.1)
          (stackup (layer "F.SilkS" (type "Top Silk Screen"))
          (layer "F.Mask" (type "Top Solder Mask") (thickness 0.025) (material "Polyimide coverlay"))
          (layer "F.Cu" (type "copper") (thickness 0.012))
          (layer "dielectric 1" (type "core") (thickness 0.025) (material "Polyimide") (epsilon_r 3.4) (loss_tangent 0.02))
          (layer "B.Cu" (type "copper") (thickness 0.012))
          (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.025) (material "Polyimide coverlay"))
          (layer "B.SilkS" (type "Bottom Silk Screen")) (copper_finish "ENIG") (dielectric_constraints no)) (tenting front back))'''
        nets='\n'.join(f'(net {n} {q(name)})' for name,n in self.nets.items())
        path.write_text(header+'\n'+nets+'\n'+'\n'.join(self.items)+'\n)\n')


def library():
    lib=HERE/'neurband_c_flex.pretty'
    lib.mkdir(exist_ok=True)
    definitions=[
        ('Electrode_D6.5mm','Round exposed ENIG skin electrode; no paste',
         [(1,(0,0),(6.5,6.5),'circle')],'F'),
        ('FPC_Tail_20_P0.5mm','XUNPU 20x0.5 cable; B contacts; F stiffener; 10.50 tab; finished 0.30mm',
         [(p,(contact_x(p),0),(0.3,3.2),'rect') for p in range(1,21)],'B')]
    for name,description,pads,side in definitions:
        fp=Footprint(name,FootprintType.SMD)
        fp.setDescription(description)
        fp.excludeFromBOM=True
        fp.excludeFromPositionFiles=True
        fp.append(Property(name=Property.REFERENCE,text='REF**',at=[0,-4],layer='F.Fab'))
        fp.append(Property(name=Property.VALUE,text=name,at=[0,4],layer='F.Fab'))
        for number,at,size,shape in pads:
            fp.append(Pad(number=number,type=Pad.TYPE_SMT,shape=shape,at=list(at),size=list(size),
                          layers=['F.Cu'] if side=='B' else ['F.Cu','F.Mask'],solder_mask_margin=0))
        if side=='B':
            fp.allow_soldermask_bridges=True
            fp.append(Polygon(shape=[(-5.25,-1.9),(5.25,-1.9),(5.25,1.65),(-5.25,1.65)],layer='F.Mask',width=0,fill=True))
        KicadFileHandler(fp).writeFile(str(lib/(name+'.kicad_mod')))
    fp=Footprint('Alignment_D1.2mm',FootprintType.THT)
    fp.not_in_schematic=True
    fp.excludeFromBOM=True
    fp.excludeFromPositionFiles=True
    fp.append(Property(name=Property.REFERENCE,text='REF**',at=[0,0],layer='F.Fab'))
    fp.append(Property(name=Property.VALUE,text='Alignment 1.2mm',at=[0,0],layer='F.Fab'))
    fp.append(Pad(number='',type=Pad.TYPE_NPTH,shape=Pad.SHAPE_CIRCLE,at=[0,0],size=[1.2,1.2],drill=1.2,layers=['*.Cu']))
    KicadFileHandler(fp).writeFile(str(lib/'Alignment_D1.2mm.kicad_mod'))
    (HERE/'fp-lib-table').write_text('(fp_lib_table (lib (name "neurband_c_flex")(type "KiCad")(uri "${KIPRJMOD}/neurband_c_flex.pretty")(options "")(descr "REV C fabricated contacts")))\n')


def route_board(board):
    board.geometry()
    board.route()
    board.shield()
    return board


def verify(path):
    build=HERE/'build'
    build.mkdir(exist_ok=True)
    report=build/(NAME+'-drc.json')
    subprocess.run([str(CLI),'pcb','drc','--refill-zones','--save-board','--schematic-parity',
                    '--format','json','-o',str(report),str(path)],check=True)
    data=json.loads(report.read_text())
    errors=[v for v in data['violations'] if v['severity']=='error']
    print(f'DRC: {len(errors)} errors; {len(data["unconnected_items"])} unconnected; parity {len(data.get("schematic_parity",[]))}',flush=True)
    if data['violations'] or data['unconnected_items'] or data.get('schematic_parity'):
        raise RuntimeError(f'DRC failed: {report}')
    areas=shield_areas(path)
    (build/(NAME+'-shield.json')).write_text(json.dumps(areas,indent=2)+'\n')
    print('Measured GND shield copper per pod, mm2:',areas,flush=True)


def shield_areas(path):
    """Check actual filled copper, not merely the presence of zone outlines."""
    pcb=parse_sexpr(path.read_text())
    scale=1_000_000
    copper=[]
    pods={}
    for item in pcb:
        if not isinstance(item,list):
            continue
        if item[0]=='footprint':
            props={x[1]:x[2] for x in item if isinstance(x,list) and x[0]=='property'}
            if re.fullmatch(r'E[1-8]B',props.get('Reference','')):
                at=next((x for x in item if isinstance(x,list) and x[0]=='at'),None)
                position=at if at is not None else child(child(item,'transform'),'translate')
                pods[props['Reference']]=tuple(map(float,position[1:3]))
        net=next((x for x in item if isinstance(x,list) and x[0]=='net'),None)
        if item[0]=='zone' and net is not None and net[1]=='GND':
            for filled in item:
                if isinstance(filled,list) and filled[0]=='filled_polygon' and child(filled,'layer')[1]=='B.Cu':
                    copper.append([(round(float(p[1])*scale),round(float(p[2])*scale)) for p in child(filled,'pts')[1:]])
    if len(pods)!=8 or not copper:
        raise RuntimeError('Missing pod geometry or filled shield')
    areas={}
    for ref,(x,y) in sorted(pods.items()):
        window=[(x-3,y-14),(x+3,y-14),(x+3,y+14),(x-3,y+14)]
        clip=pyclipper.Pyclipper()
        clip.AddPaths(copper,pyclipper.PT_SUBJECT,True)
        clip.AddPath([(round(a*scale),round(b*scale)) for a,b in window],pyclipper.PT_CLIP,True)
        result=clip.Execute(pyclipper.CT_INTERSECTION,pyclipper.PFT_NONZERO,pyclipper.PFT_NONZERO)
        areas[ref]=round(abs(sum(pyclipper.Area(p) for p in result))/scale**2,3)
    if any(area<10 for area in areas.values()):
        raise RuntimeError(f'Missing pod shield copper: {areas}')
    return areas


def render(path):
    out=HERE/'renders'
    out.mkdir(exist_ok=True)
    for side,layers,mirror in [('top','F.Cu,F.SilkS,Edge.Cuts',[]),('bottom','B.Cu,B.SilkS,Edge.Cuts',['--mirror'])]:
        svg=out/(NAME+'_'+side+'.svg')
        subprocess.run([str(CLI),'pcb','export','svg','--layers',layers,'--page-size-mode','2','--exclude-drawing-sheet',
                        '--mode-single',*mirror,'-o',str(svg),str(path)],check=True)
        subprocess.run(['rsvg-convert','-w','2600','-o',str(svg.with_suffix('.png')),str(svg)],check=True)
    for side in ('top','bottom'):
        subprocess.run([str(CLI),'pcb','render','--output',str(out/(NAME+'_'+side+'_3d.png')),
                        '--width','2400','--height','1100','--side',side,'--zoom','1.8',
                        '--background','opaque','--quality','basic',str(path)],check=True)
    subprocess.run([str(CLI),'pcb','render','--output',str(out/(NAME+'_iso_3d.png')),
                    '--width','2400','--height','1100','--side','top','--zoom','1.8',
                    '--rotate','325,0,15','--background','opaque','--quality','basic',str(path)],check=True)


def export_step(path):
    # KiCad board-only STEP is the 0.025 mm core; real covered stack is 0.099 mm.
    origin=f'{ORIGIN[0]}x{ORIGIN[1]}mm'
    subprocess.run([str(CLI),'pcb','export','step','--force','--board-only',
                    '--user-origin',origin,'--output',str(path.with_suffix('.step')),str(path)],
                   check=True,timeout=120)


def fabrication_metadata(path):
    pcb=parse_sexpr(path.read_text())
    points=[]
    drills=[]
    for item in pcb:
        if not isinstance(item,list):
            continue
        if item[0]=='gr_line' and child(item,'layer')[1]=='Edge.Cuts':
            points.extend(tuple(map(float,child(item,k)[1:3])) for k in ('start','end'))
        if item[0]=='via':
            drills.append(float(child(item,'drill')[1]))
    features={'width_mm':round(max(p[0] for p in points)-min(p[0] for p in points),6),
              'height_mm':round(max(p[1] for p in points)-min(p[1] for p in points),6),
              'min_drill_mm':min(drills)}
    metadata={'kind':'flex','name':'Electrode flex rev C','source':path.name,'qty':5,
              'options':{'layers':2,'thickness_mm':0.11,'coverlay':'yellow','stiffener':'polyimide_0.225',
                         'emi_shield':'none','gold_uin':2},'features':features}
    manifest=path.with_suffix('.fab.json')
    if manifest.exists():
        previous=json.loads(manifest.read_text())
        previous['features']=features
        metadata=previous
    manifest.write_text(json.dumps(metadata,indent=2)+'\n')
    return features


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pitch',type=float,default=POD_PITCH)
    parser.add_argument('--tail-length',type=float,default=TAIL_LENGTH)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--step',action='store_true')
    args=parser.parse_args()
    if args.pitch<17 or args.tail_length<8.5:
        parser.error('Pitch >=17 mm and tail >=8.5 mm required by this captured-root/stiffener layout')
    library()
    path=HERE/(NAME+'.kicad_pcb')
    board=route_board(Board(args.pitch,args.tail_length,contract()))
    board.save(path)
    if args.verify:
        verify(path)
    if args.render:
        render(path)
    if args.step:
        export_step(path)
    print('Measured fabrication features:',fabrication_metadata(path),flush=True)


if __name__=='__main__':
    main()
