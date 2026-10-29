#!/usr/bin/env python3
"""Deterministic neurband flex artwork; no pcbnew/SWIG required.

The repeated electrode escapes and paired trunks are explicit geometry. A small
clearance-aware fanout search is restricted to the tail/root, where the fixed
39-pin order needs crossovers. KiCad DRC, not this search, is the acceptance gate.
Run with --verify --render for all sizes and inspected fabrication-layer PNGs.
"""
from __future__ import annotations
import os
import argparse
import copy
import heapq
import json
import math
from pathlib import Path
import re
import subprocess
import uuid

import numpy as np
import pyclipper
from KicadModTree import Footprint, FootprintType, Pad, Polygon, Property, KicadFileHandler

HERE = Path(__file__).resolve().parent
CLI = Path(os.environ.get('KICAD_CLI', os.path.expanduser('~/.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli')))
PITCHES = {'S': 8.6, 'M': 9.5, 'L': 10.8, 'XL': 12.4}
STRIP_HALF = 17.0
TAIL_LENGTH = 12.0
STIFFENER_LENGTH = 3.5
CONTACT_COUNT = 39
CONTACT_PITCH = 0.3
CONTACT_CENTRE = (CONTACT_COUNT+1)/2
TIP_Y = STRIP_HALF + TAIL_LENGTH
FINGER_Y = TIP_Y - 2.4
WIDTH = 0.1
CLEARANCE = 0.1
LANE = 0.2
VIA_D = 0.45
VIA_DRILL = 0.2
ORIGIN = (55.0, 45.0)
NS = uuid.UUID('786992e1-7f37-48c0-9da1-4f48dd166729')


def contact_x(pin):
    return (pin-CONTACT_CENTRE)*CONTACT_PITCH


def contact_profile(pin):
    """FH26W staggered heads; dimensions within the published drawing tolerances.

    0.28 mm heads and a 0.95..1.15 mm transition preserve 0.1 mm spacing,
    unlike the 0.0707 mm diagonal gap of the nominal 45-degree transition.
    Coordinates are relative to the anchor 2.4 mm behind the cable tip.
    """
    profile=([(0.3,0.14),(0.95,0.14),(1.15,0.05),(2.5,0.05)] if pin%2 else
             [(0.95,0.05),(1.15,0.14),(2.1,0.14),(2.25,0.05),(2.5,0.05)])
    return [(-w,2.4-d) for d,w in profile]+[(w,2.4-d) for d,w in reversed(profile)]


def coverlay_window():
    return [(-6.05,-0.1),(6.05,-0.1),(6.05,2.45),(-6.05,2.45)]


def q(s):
    return json.dumps(str(s))


def uid(s):
    return str(uuid.uuid5(NS, str(s)))


def f(v):
    return f'{v:.6f}'.rstrip('0').rstrip('.') or '0'


def xy(p):
    return f'{f(p[0] + ORIGIN[0])} {f(p[1] + ORIGIN[1])}'


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


def schematic_contract():
    sch = parse_sexpr((HERE / 'neurband_electrodes.kicad_sch').read_text())
    root = child(sch, 'uuid')[1]
    refs = {}
    for sym in sch:
        if not isinstance(sym, list) or sym[0] != 'symbol':
            continue
        props = {x[1]: x[2] for x in sym if isinstance(x, list) and x[0] == 'property'}
        refs[props['Reference']] = (child(sym, 'uuid')[1], props['Value'])
    # Read the actual generated netlist, not a second hand-maintained pin map.
    netlist = parse_sexpr((HERE / 'neurband_electrodes.net').read_text())
    pads = {}
    for net in child(netlist, 'nets')[1:]:
        name = child(net, 'name')[1]
        for node in net:
            if isinstance(node, list) and node[0] == 'node':
                pads[(child(node, 'ref')[1], child(node, 'pin')[1])] = name
    tail = {n: pads['J1', str(n)] for n in range(1, CONTACT_COUNT+1)}
    expected = {1: 'GND', 2: 'GND', 3: '/BIAS_E', 36: '/BIAS_E', **{i: 'GND' for i in range(37, CONTACT_COUNT+1)}}
    expected.update({4 + 2 * (i - 1) + k: f'/E{i:02d}{kind}' for i in range(1, 17) for k, kind in enumerate('PN')})
    assert tail == expected, (tail, expected)
    return root, refs, pads, tail


class Board:
    def __init__(self, size, pitch, contract):
        self.size, self.pitch = size, pitch
        self.root, self.refs, self.pads, self.tail = contract
        self.xs = {i: (i - 4.5) * pitch for i in range(1, 17)}
        self.xmin, self.xmax = self.xs[1] - 5, self.xs[16] + 5
        names = sorted(set(self.pads.values()))
        self.nets = {name: i + 1 for i, name in enumerate(names)}
        self.items, self.segments, self.vias, self.pad_shapes = [], [], [], []
        self.via_indices = []
        self.serial = 0
        self.endpoints = {}

    def id(self):
        self.serial += 1
        return uid(f'{self.size}:{self.serial}')

    def track(self, net, points, layer='F.Cu', width=WIDTH):
        for a, b in zip(points, points[1:]):
            if math.dist(a, b) < 1e-7:
                continue
            self.segments.append((net, a, b, layer, width))
            self.items.append(f'(segment (start {xy(a)}) (end {xy(b)}) (width {f(width)}) (layer "{layer}") (net {self.nets[net]}) (uuid "{self.id()}"))')

    def via(self, net, p):
        self.vias.append((net, p))
        self.via_indices.append(len(self.items))
        self.items.append(f'(via (at {xy(p)}) (size {VIA_D}) (drill {VIA_DRILL}) (layers "F.Cu" "B.Cu") (net {self.nets[net]}) (uuid "{self.id()}"))')

    def remove_redundant_vias(self):
        """Remove unused fanout landing vias, not warnings about real defects."""
        drop = set()
        kept = []
        for index,(net,p) in zip(self.via_indices,self.vias):
            connected = set()
            for track_net,a,b,layer,width in self.segments:
                if track_net != net:
                    continue
                dx,dy=b[0]-a[0],b[1]-a[1]
                t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
                if math.dist(p,(a[0]+t*dx,a[1]+t*dy)) < VIA_D/2+width/2-1e-5:
                    connected.add(layer)
            if net=='GND' or connected=={'F.Cu','B.Cu'}:
                kept.append((net,p))
            else:
                drop.add(index)
        self.items=[item for i,item in enumerate(self.items) if i not in drop]
        self.vias=kept

    def line(self, a, b, layer='Edge.Cuts', width=0.05):
        self.items.append(f'(gr_line (start {xy(a)}) (end {xy(b)}) (stroke (width {width}) (type default)) (layer "{layer}") (uuid "{self.id()}"))')

    def text(self, text, p, layer='F.SilkS', size=0.8):
        mirror = '(justify mirror)' if layer.startswith('B.') else ''
        self.items.append(f'(gr_text {q(text)} (at {xy(p)}) (layer "{layer}") (uuid "{self.id()}") (effects (font (size {size} {size}) (thickness 0.15)) {mirror}))')

    def footprint(self, ref, name, p, pads):
        stamp, value = self.refs[ref]
        body = [f'(footprint "neurband:{name}" (layer "F.Cu") (uuid "{uid(self.size + ref)}") (at {xy(p)})',
                f'(property "Reference" {q(ref)} (at 0 -4.1) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))',
                f'(property "Value" {q(value)} (at 0 4.1) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))',
                '(property "MPN" "" (at 0 0) (layer "F.Fab") (effects (font (size 0.7 0.7)) (hide yes)))',
                '(property "LCSC" "" (at 0 0) (layer "F.Fab") (effects (font (size 0.7 0.7)) (hide yes)))',
                f'(path "/{self.root}/{stamp}") (attr smd exclude_from_pos_files{" allow_soldermask_bridges" if ref=="J1" else ""})']
        for num, local, dims, shape in pads:
            net = self.pads[ref, str(num)]
            self.pad_shapes.append((net, (p[0] + local[0], p[1] + local[1]), dims, shape))
            if shape=='custom':
                pts=' '.join(f'(xy {f(x)} {f(y)})' for x,y in contact_profile(num))
                body.append(f'(pad "{num}" smd custom (at {f(local[0])} {f(local[1])}) (size 0.1 0.1) (layers "F.Cu") (net {self.nets[net]} {q(net)}) (uuid "{uid(self.size+ref+str(num))}") (options (clearance outline) (anchor rect)) (primitives (gr_poly (pts {pts}) (width 0) (fill yes))))')
            else:
                body.append(f'(pad "{num}" smd {shape} (at {f(local[0])} {f(local[1])}) (size {f(dims[0])} {f(dims[1])}) (layers "F.Cu" "F.Mask") (solder_mask_margin 0.05) (net {self.nets[net]} {q(net)}) (uuid "{uid(self.size + ref + str(num))}"))')
        if ref=='J1':
            pts=' '.join(f'(xy {f(x)} {f(y)})' for x,y in coverlay_window())
            body.append(f'(fp_poly (pts {pts}) (stroke (width 0) (type default)) (fill solid) (layer "F.Mask") (uuid "{self.id()}"))')
        body.append(')')
        self.items.append('\n'.join(body))

    def geometry(self):
        # Chamfered external corners, generous tail-root shoulders; one closed contour.
        a, b = self.xmin, self.xmax
        contour = [(a + 1, -17), (b - 1, -17), (b, -16), (b, 16), (b - 1, 17),
                   (9,17),(7,19),(7,TIP_Y-5),(6,TIP_Y-4),(6,TIP_Y-0.1),(5.9,TIP_Y),
                   (-5.9,TIP_Y),(-6,TIP_Y-0.1),(-6,TIP_Y-4),(-7,TIP_Y-5),(-7,19),(-9,17),
                   (a + 1, 17), (a, 16), (a, -16)]
        self.contour = contour
        for p1, p2 in zip(contour, contour[1:] + contour[:1]):
            self.line(p1, p2)
        for i, x in self.xs.items():
            for kind, y in [('P', -10), ('B', 0), ('N', 10)]:
                self.footprint(f'E{i}{kind}', 'Electrode_D6.5mm', (x, y), [(1, (0, 0), (6.5, 6.5), 'circle')])
            self.text(str(i), (x, -5), size=0.8)
            # Optional stiffener extent: not a cut or coverlay opening.
            for p1, p2 in zip([(-3.5,-16), (3.5,-16), (3.5,16), (-3.5,16)], [(3.5,-16), (3.5,16), (-3.5,16), (-3.5,-16)]):
                self.line((x+p1[0],p1[1]), (x+p2[0],p2[1]), 'User.1', 0.1)
        self.footprint('J1','FPC_Tail_39_P0.3mm',(0,FINGER_Y),
                       [(n,(contact_x(n),0),(0.1,0.1),'custom') for n in range(1,CONTACT_COUNT+1)])
        self.text('1',(-5.6,TIP_Y-5),size=0.8)
        self.text('39',(5.6,TIP_Y-5),size=0.8)
        self.text(f'neurband FLEX {self.size} / SKIN',(0,14),size=0.85)
        self.text('P1 > J2 P1 / NO TWIST',(0,16),size=0.8)
        self.text('OUTER / COVERLAY',(0,14),'B.SilkS',0.8)
        stiffener=[(-6,TIP_Y-STIFFENER_LENGTH),(6,TIP_Y-STIFFENER_LENGTH),
                   (6,TIP_Y-0.1),(5.9,TIP_Y),(-5.9,TIP_Y),(-6,TIP_Y-0.1)]
        for p1,p2 in zip(stiffener,stiffener[1:]+stiffener[:1]):
            self.line(p1,p2,'User.2',0.15)
        self.text('B stiffener: PI; finished insertion 0.20 +/-0.03 mm',(0,TIP_Y-8),'User.2',0.65)
        self.text('Optional PI pod backing on B; do not bridge flex hinges', ((a+b)/2, 20), 'User.1', 0.7)
        self.text('Root x +/-15: housing-captured R44; no free bending', (0,22), 'User.1', 0.65)

    def trunks(self):
        groups = [(range(2,0,-1), -1, 1), (range(4,2,-1), 1, 1),
                  (range(5,11), -1, -1), (range(11,17), 1, -1)]
        for channels, side, direction in groups:
            for rank, i in enumerate(channels):
                x = self.xs[i]
                direct = 'P' if side == -1 else 'N'
                other = 'N' if side == -1 else 'P'
                # Underpass only within the pod, never in a circumferential flex link.
                net = self.pads[f'E{i}{other}', '1']
                self.track(net, [(x, -side*10), (x, -side*6.1)])
                self.via(net, (x, -side*6.1))
                self.track(net, [(x, -side*6.1), (x, side*6.1)], 'B.Cu')
                self.via(net, (x, side*6.1))
                for k, kind in enumerate([direct,other]):
                    net = self.pads[f'E{i}{kind}', '1']
                    y = side*(13.65 + (2*rank+k)*LANE)
                    escape_x = x - direction*(3.6 + k*LANE)
                    source_y = side*(10 if k==0 else 6.1)
                    # Endpoints stay in a small root region; fanout may cross layers.
                    endx = (-3.4 if direction==1 else 3.4) + direction*(2*rank+k)*0.8
                    bank = (endx, y - side*0.18)
                    self.track(net, [(x,source_y),(escape_x,source_y),(escape_x,y),(endx,y),bank])
                    self.via(net, bank)
                    self.endpoints[net] = (*bank,1)
        # The driven-bias bus is electrically separate from the outer GND shield.
        self.track('/BIAS_E', [(self.xs[1],0),(self.xs[16],0)], width=0.2)
        self.endpoints['/BIAS_E'] = (0,0,0)
        # Root crossovers can partition the B shield. Give every pod a real return;
        # on S this also joins shields without any B copper in free-bending links.
        self.track('GND', [(self.xs[1]+2,4.5),(self.xs[16]+2,4.5)])
        for x in self.xs.values():
            self.via('GND',(x+2,4.5))
        if self.size=='S':
            # Pod 5's vertical signal underpass separates its split shield.
            # Ground both sides rather than relying on copper across a flex link.
            self.via('GND',(self.xs[5]-2,4.5))

    def shield(self):
        contours = [self.contour]
        if self.size == 'S':
            contours = [[(x-3.5,-17),(x+3.5,-17),(x+3.5,17),(x-3.5,17)] for x in self.xs.values()]
            # Clip the actual outline so the captured root and tail form one
            # shield, without an artificial seam across the dense via bank.
            scale=1_000_000
            clip=pyclipper.Pyclipper()
            clip.AddPath([(round(x*scale),round(y*scale)) for x,y in self.contour],pyclipper.PT_SUBJECT,True)
            clip.AddPath([(-15*scale,-17*scale),(15*scale,-17*scale),
                          (15*scale,round(TIP_Y*scale)),(-15*scale,round(TIP_Y*scale))],pyclipper.PT_CLIP,True)
            contours.extend([[(x/scale,y/scale) for x,y in path] for path in
                             clip.Execute(pyclipper.CT_INTERSECTION,pyclipper.PFT_NONZERO,pyclipper.PFT_NONZERO)])
        for contour in contours:
            pts = ' '.join(f'(xy {xy(p)})' for p in contour)
            self.items.append(f'''(zone (net {self.nets['GND']}) (net_name "GND") (layer "B.Cu") (uuid "{self.id()}")
              (hatch edge 0.5) (connect_pads yes (clearance 0.127)) (min_thickness 0.15)
              (fill yes (mode hatch) (thermal_gap 0.2) (thermal_bridge_width 0.2)
              (hatch_thickness 0.2) (hatch_gap 0.8) (hatch_orientation 45)
              (hatch_smoothing_level 0) (hatch_smoothing_value 0) (island_removal_mode 0) (island_area_min 0))
              (polygon (pts {pts})))''')
        pts=' '.join(f'(xy {xy(p)})' for p in [(-6.2,TIP_Y-4.1),(6.2,TIP_Y-4.1),(6.2,TIP_Y+0.1),(-6.2,TIP_Y+0.1)])
        self.items.append(f'''(zone (net 0) (net_name "") (layers "F.Cu" "B.Cu") (uuid "{self.id()}")
          (name "FH26W insertion tab") (hatch edge 0.5)
          (keepout (tracks allowed) (vias allowed) (pads allowed) (copperpour allowed) (footprints allowed))
          (polygon (pts {pts})))''')

    def save(self, path):
        layers = [(0,'F.Cu','signal'),(31,'B.Cu','signal'),(36,'B.SilkS','user'),(37,'F.SilkS','user'),
                  (38,'B.Mask','user'),(39,'F.Mask','user'),(44,'Edge.Cuts','user'),
                  (48,'B.Fab','user'),(49,'F.Fab','user'),(50,'User.1','user'),(51,'User.2','user')]
        header = f'''(kicad_pcb (version 20241229) (generator "neurband_flex")
          (general (thickness 0.099)) (paper "A3")
          (layers {' '.join(f'({n} "{name}" {kind})' for n,name,kind in layers)})
          (setup (pad_to_mask_clearance 0.05) (solder_mask_min_width 0.1)
          (stackup (layer "F.SilkS" (type "Top Silk Screen"))
          (layer "F.Mask" (type "Top Solder Mask") (thickness 0.025) (material "Polyimide coverlay"))
          (layer "F.Cu" (type "copper") (thickness 0.012))
          (layer "dielectric 1" (type "core") (thickness 0.025) (material "Polyimide") (epsilon_r 3.4) (loss_tangent 0.02))
          (layer "B.Cu" (type "copper") (thickness 0.012))
          (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.025) (material "Polyimide coverlay"))
          (layer "B.SilkS" (type "Bottom Silk Screen")) (copper_finish "ENIG") (dielectric_constraints no))
          (tenting front back))'''
        nets = '\n'.join(f'(net {n} {q(name)})' for name,n in self.nets.items())
        path.write_text(header+'\n'+nets+'\n'+'\n'.join(self.items)+'\n)\n')


class Fanout:
    """Local two-layer tail fanout, 0.05 mm grid and 0.1 mm tracks."""
    STEP = 0.05
    def __init__(self, board):
        self.b = board
        self.x0, self.y0 = -15, -16.8
        self.nx, self.ny = 601, round((TIP_Y-self.y0)/self.STEP)+2
        self.occ = np.zeros((2,self.ny,self.nx), dtype=np.int16)
        self.outside = np.ones((self.ny,self.nx),dtype=bool)
        ys, xs = np.mgrid[:self.ny,:self.nx]
        xx, yy = xs*self.STEP+self.x0, ys*self.STEP+self.y0
        inside_strip = (yy>=-16.65)&(yy<=16.65)
        inside_tail = (np.abs(xx)<=6.6)&(yy>=16)&(yy<=TIP_Y-5)
        inside_tail |= (np.abs(xx)<=5.65)&(yy>=TIP_Y-5)&(yy<=TIP_Y-0.4)
        self.outside[:] = ~(inside_strip|inside_tail)
        self.owners=None
        self.penalty=None
        # Reserve the very end for straight finger escapes.
        for net,p,dims,shape in board.pad_shapes:
            self.shape(net,p,dims,shape,0)
        for net,a,b,layer,width in board.segments:
            self.segment(net,a,b,0 if layer=='F.Cu' else 1,width)
        for net,p in board.vias:
            for layer in (0,1):
                self.shape(net,p,(VIA_D,VIA_D),'circle',layer)
        self.dist = np.empty((2,self.ny,self.nx),dtype=np.float32)
        self.prev = np.empty((2,self.ny,self.nx),dtype=np.int32)
        self.owners=np.zeros_like(self.occ,dtype=np.uint64)

    def grid(self,p):
        return round((p[0]-self.x0)/self.STEP),round((p[1]-self.y0)/self.STEP)

    def point(self,x,y):
        return round(x*self.STEP+self.x0,6),round(y*self.STEP+self.y0,6)

    def paint(self,net,xmin,xmax,ymin,ymax,test,layer):
        xa,ya = self.grid((xmin,ymin)); xb,yb = self.grid((xmax,ymax))
        xa,xb=max(0,xa-1),min(self.nx,xb+2); ya,yb=max(0,ya-1),min(self.ny,yb+2)
        if xa>=xb or ya>=yb:
            return
        yy,xx=np.mgrid[ya:yb,xa:xb]
        mask=test(xx*self.STEP+self.x0,yy*self.STEP+self.y0)
        region=self.occ[layer,ya:yb,xa:xb]
        # Overlapping clearance envelopes are blocked for every net.
        n=self.b.nets[net]
        if self.owners is not None:
            owners=self.owners[layer,ya:yb,xa:xb]
            owners[mask] |= np.uint64(1) << np.uint64(n)
        region[mask & (region!=0) & (region!=n)] = -1
        region[mask & (region==0)] = n

    def shape(self,net,p,dims,shape,layer):
        extra=0.1+0.05+0.01
        rx,ry=dims[0]/2+extra,dims[1]/2+extra
        def test(x,y):
            if shape=='circle':
                return (x-p[0])**2+(y-p[1])**2<=rx**2
            return (abs(x-p[0])<=rx)&(abs(y-p[1])<=ry)
        self.paint(net,p[0]-rx,p[0]+rx,p[1]-ry,p[1]+ry,test,layer)

    def segment(self,net,a,b,layer,width):
        r=width/2+0.1+0.05+0.01
        dx,dy=b[0]-a[0],b[1]-a[1]
        ll=dx*dx+dy*dy
        def test(x,y):
            t=np.clip(((x-a[0])*dx+(y-a[1])*dy)/ll,0,1)
            return (x-a[0]-t*dx)**2+(y-a[1]-t*dy)**2<=r*r
        self.paint(net,min(a[0],b[0])-r,max(a[0],b[0])+r,min(a[1],b[1])-r,max(a[1],b[1])+r,test,layer)

    def route(self,net,start,end):
        sx,sy=self.grid(start[:2]); ex,ey=self.grid(end[:2]); sl,el=start[2],end[2]
        n=self.b.nets[net]
        valid=((self.occ==0)|(self.occ==n)) & ~self.outside[None,:,:]
        row_y=np.arange(self.ny)*self.STEP+self.y0
        # The entire tail is prewired on F.Cu; search only the captured strip.
        valid[:,row_y>16.65+1e-6,:]=False
        if not valid[sl,sy,sx] or not valid[el,ey,ex]:
            raise RuntimeError(f'{net} blocked endpoints {start} {end}')
        # Via centres need an extra radius over track centre clearance.
        via_valid=valid[0]&valid[1]
        for dy in range(-4,5):
            for dx in range(-4,5):
                if dx*dx+dy*dy>16:
                    continue
                via_valid &= np.roll(np.roll(valid[0]&valid[1],dy,axis=0),dx,axis=1)
        existing_vias = {}
        yy,xx=np.mgrid[:self.ny,:self.nx]
        physical_y=yy*self.STEP+self.y0
        via_valid &= physical_y<=16.6
        for via_net, p in self.b.vias:
            vx,vy = self.grid(p)
            via_valid[(xx-vx)**2+(yy-vy)**2 <= (0.46/self.STEP)**2] = False
            if via_net == net and 0 <= vx < self.nx and 0 <= vy < self.ny:
                existing_vias[vx,vy] = p
        for (vx,vy),p in existing_vias.items():
            via_valid[vy,vx] = valid[0,vy,vx] and valid[1,vy,vx]
        self.dist.fill(np.inf); self.prev.fill(-1)
        self.dist[sl,sy,sx]=0
        def h(x,y,l):
            a,b=abs(x-ex),abs(y-ey)
            return max(a,b)+0.414214*min(a,b)+(35 if l!=el else 0)
        queue=[(h(sx,sy,sl),0,sx,sy,sl)]
        moves=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.414214),(1,-1,1.414214),(-1,1,1.414214),(-1,-1,1.414214)]
        found=False
        while queue:
            _,cost,x,y,l=heapq.heappop(queue)
            if cost>self.dist[l,y,x]+1e-3:
                continue
            if (x,y,l)==(ex,ey,el):
                found=True;break
            idx=(l*self.ny+y)*self.nx+x
            for dx,dy,w in moves:
                xx,yy=x+dx,y+dy
                if not (0<=xx<self.nx and 0<=yy<self.ny and valid[l,yy,xx]):
                    continue
                if dx and dy and not (valid[l,y,xx] and valid[l,yy,x]):
                    continue
                new=cost+w
                if self.penalty is not None:
                    new+=float(self.penalty[l,yy,xx])
                if new+1e-4<self.dist[l,yy,xx]:
                    self.dist[l,yy,xx]=new;self.prev[l,yy,xx]=idx
                    heapq.heappush(queue,(new+h(xx,yy,l),new,xx,yy,l))
            if via_valid[y,x]:
                ll=1-l;new=cost+35
                if new+1e-4<self.dist[ll,y,x]:
                    self.dist[ll,y,x]=new;self.prev[ll,y,x]=idx
                    heapq.heappush(queue,(new+h(x,y,ll),new,x,y,ll))
        if not found:
            raise RuntimeError(f'No tail fanout for {net}')
        path=[];x,y,l=ex,ey,el
        while True:
            path.append((x,y,l))
            prev=int(self.prev[l,y,x])
            if prev<0:break
            x=prev%self.nx;v=prev//self.nx;y=v%self.ny;l=v//self.ny
        path.reverse()
        self.last_path=path
        # Compress only collinear grid runs; retain layer transitions as actual vias.
        points=[path[0]]
        for k in range(1,len(path)-1):
            a,b,c=path[k-1:k+2]
            if (b[0]-a[0],b[1]-a[1],b[2]-a[2])!=(c[0]-b[0],c[1]-b[1],c[2]-b[2]):
                points.append(b)
        points.append(path[-1])
        # Exact endpoints join the regular 0.254 mm bus to the 0.1 mm grid.
        grid_start=self.point(*points[0][:2]);grid_end=self.point(*points[-1][:2])
        self.b.track(net,[start[:2],grid_start], 'F.Cu' if sl==0 else 'B.Cu',0.1)
        for a,b in zip(points,points[1:]):
            pa,pb=self.point(*a[:2]),self.point(*b[:2])
            if a[2]!=b[2]:
                existing = existing_vias.get(a[:2])
                if existing is not None:
                    for layer in ('F.Cu','B.Cu'):
                        self.b.track(net,[pa,existing],layer,0.1)
                else:
                    self.b.via(net,pa)
                    for layer in (0,1):self.shape(net,pa,(VIA_D,VIA_D),'circle',layer)
            else:
                self.b.track(net,[pa,pb],'F.Cu' if a[2]==0 else 'B.Cu',0.1)
                self.segment(net,pa,pb,a[2],0.1)
        self.b.track(net,[grid_end,end[:2]],'F.Cu' if el==0 else 'B.Cu',0.1)
        print(f'{self.b.size} fanout {net}: {len(points)} corners',flush=True)


def library():
    """Official KiCad Library Tools, deliberately without solder-paste apertures."""
    lib=HERE/'neurband.pretty';lib.mkdir(exist_ok=True)
    for name,description,pads in [
        ('Electrode_D6.5mm','6.5 mm exposed gold skin electrode; F coverlay opening; no paste',
         [(1,(0,0),(6.5,6.5),Pad.SHAPE_CIRCLE)]),
        ('FPC_Tail_39_P0.3mm','FH26W 39 x 0.3 mm staggered F contacts; 12.0 mm tab; finished thickness 0.20 +/-0.03 mm',
         [(n,(contact_x(n),0),(0.1,0.1),Pad.SHAPE_CUSTOM) for n in range(1,CONTACT_COUNT+1)])
    ]:
        fp=Footprint(name,FootprintType.SMD)
        fp.allow_soldermask_bridges=name.startswith('FPC_')
        fp.setDescription(description)
        fp.append(Property(name=Property.REFERENCE,text='REF**',at=[0,-4.1],layer='F.Fab'))
        fp.append(Property(name=Property.VALUE,text=name,at=[0,4.1],layer='F.Fab'))
        for number,at,size,shape in pads:
            if shape==Pad.SHAPE_CUSTOM:
                fp.append(Pad(number=number,type=Pad.TYPE_SMT,shape=shape,at=list(at),
                              size=list(size),layers=['F.Cu'],anchor_shape=Pad.SHAPE_RECT,
                              primitives=[Polygon(shape=contact_profile(number),layer='F.Cu',width=0,fill=True)]))
            else:
                fp.append(Pad(number=number,type=Pad.TYPE_SMT,shape=shape,at=list(at),
                              size=list(size),layers=['F.Cu','F.Mask'],solder_mask_margin=0.05))
        if name.startswith('FPC_'):
            fp.append(Polygon(shape=coverlay_window(),layer='F.Mask',width=0,fill=True))
        KicadFileHandler(fp).writeFile(str(lib/(name+'.kicad_mod')))
    (HERE/'fp-lib-table').write_text('(fp_lib_table\n  (lib (name "neurband")(type "KiCad")(uri "${KIPRJMOD}/neurband.pretty")(options "")(descr "Electrode flex artwork"))\n)\n')


def project_settings(path):
    data=json.loads((HERE/'neurband_electrodes.kicad_pro').read_text())
    settings=data.setdefault('board',{}).setdefault('design_settings',{})
    settings['rules']={'min_clearance':0.1,'min_track_width':0.1,'min_via_diameter':0.45,
                       'min_through_hole_diameter':0.2,'min_via_annular_width':0.125,
                       'min_copper_edge_clearance':0.15,'min_hole_clearance':0.2,
                       'min_silk_clearance':0.1,'min_silk_text_height':0.6,'min_silk_text_thickness':0.1}
    data['net_settings']={'classes':[{'name':'Default','clearance':0.1,'track_width':0.127,
                'via_diameter':0.45,'via_drill':0.2,'microvia_diameter':0.3,'microvia_drill':0.1,
                'diff_pair_width':0.127,'diff_pair_gap':0.127,'diff_pair_via_gap':0.25}], 'meta':{'version':3}}
    data['meta']['filename']=path.name
    path.write_text(json.dumps(data,indent=2)+'\n')
    path.with_suffix('.kicad_dru').write_text('''(version 1)
(rule "Flex copper edge clearance" (constraint edge_clearance (min 0.3mm)))
(rule "FH26W standardized cable edge"
  (condition "A.Type != 'Zone' && A.intersectsArea('FH26W insertion tab')")
  (constraint edge_clearance (min 0.15mm)))
''')


def shield_areas(path):
    """Measure filled GND copper per pod; DRC alone misses deleted zone islands."""
    pcb=parse_sexpr(path.read_text())
    scale=1_000_000
    copper=[];pods={}
    for item in pcb:
        if not isinstance(item,list):
            continue
        if item[0]=='footprint':
            props={x[1]:x[2] for x in item if isinstance(x,list) and x[0]=='property'}
            if re.fullmatch(r'E[0-9]+B',props.get('Reference','')):
                at=next((x for x in item if isinstance(x,list) and x[0]=='at'),None)
                position=at if at is not None else child(child(item,'transform'),'translate')
                pods[props['Reference']]=tuple(map(float,position[1:3]))
        net=next((x for x in item if isinstance(x,list) and x[0]=='net'),[])
        if item[0]=='zone' and net[1:]==['GND']:
            for filled in item:
                if isinstance(filled,list) and filled[0]=='filled_polygon' and child(filled,'layer')[1]=='B.Cu':
                    copper.append([(round(float(p[1])*scale),round(float(p[2])*scale)) for p in child(filled,'pts')[1:]])
    if len(pods)!=16 or not copper:
        raise RuntimeError(f'{path.name}: missing pod geometry or filled shield')
    areas={}
    for ref,(x,y) in pods.items():
        window=[(x-3,y-15),(x+3,y-15),(x+3,y+15),(x-3,y+15)]
        clip=pyclipper.Pyclipper()
        clip.AddPaths(copper,pyclipper.PT_SUBJECT,True)
        clip.AddPath([(round(a*scale),round(b*scale)) for a,b in window],pyclipper.PT_CLIP,True)
        result=clip.Execute(pyclipper.CT_INTERSECTION,pyclipper.PFT_NONZERO,pyclipper.PFT_NONZERO)
        areas[ref]=round(abs(sum(pyclipper.Area(p) for p in result))/scale**2,3)
    # Gross-loss regression guard, not an electromagnetic shielding specification.
    missing=[ref for ref,area in areas.items() if area<10]
    if missing:
        raise RuntimeError(f'{path.name}: missing shield over {missing}; copper areas {areas}')
    return areas


def verify(path):
    out=HERE/'build';out.mkdir(exist_ok=True)
    report=out/(path.stem+'-drc.json')
    parity=['--schematic-parity'] if path.stem=='neurband_electrodes' else []
    subprocess.run([str(CLI),'pcb','drc','--refill-zones','--save-board','--format','json',*parity,'-o',str(report),str(path)],check=True)
    data=json.loads(report.read_text())
    errors=[v for v in data['violations'] if v['severity']=='error']
    unconnected=data['unconnected_items']
    print(f'{path.name}: {len(errors)} errors, {len(unconnected)} unconnected, {len(data["violations"])-len(errors)} warnings',flush=True)
    if data['violations'] or unconnected or data.get('schematic_parity'):
        raise RuntimeError(f'DRC failed: {report}')
    areas=shield_areas(path)
    (out/(path.stem+'-shield.json')).write_text(json.dumps(areas,indent=2)+'\n')
    print(f'{path.name}: filled shield copper {min(areas.values()):.3f}..{max(areas.values()):.3f} mm2 per 6x30 mm pod window',flush=True)


def render(path):
    out=HERE/'renders';out.mkdir(exist_ok=True)
    for side,layers,mirror in [('top','F.Cu,F.SilkS,Edge.Cuts',[]),('bottom','B.Cu,B.SilkS,Edge.Cuts',['--mirror'])]:
        svg=out/f'{path.stem}_{side}.svg'
        subprocess.run([str(CLI),'pcb','export','svg','--layers',layers,'--page-size-mode','2','--exclude-drawing-sheet','--mode-single',*mirror,'-o',str(svg),str(path)],check=True)
        subprocess.run(['rsvg-convert','-w','2400','-o',str(svg.with_suffix('.png')),str(svg)],check=True)
    if path.stem=='neurband_electrodes':
        for side,label in [('top','skin'),('bottom','outer')]:
            subprocess.run([str(CLI),'pcb','render','--output',str(out/f'{path.stem}_{label}_3d.png'),
                            '--width','2400','--height','1100','--side',side,'--background','opaque',
                            '--quality','basic',str(path)],check=True)


def route_board(size,contract):
    board=Board(size,PITCHES[size],contract);board.geometry();board.trunks()
    for pins,sign in [([1,2],-1),([37,38,39],1)]:
        landing=(sign*8.65,16.6)
        board.via('GND',landing)
        for pin in pins:
            board.track('GND',[(contact_x(pin),FINGER_Y),(contact_x(pin),TIP_Y-3.0),(sign*5.6,TIP_Y-3.8),
                              (sign*6.45,19),(sign*8.5,17),landing])
    contacts={}
    for pin in range(3,37):
        net=board.tail[pin];x=contact_x(pin)
        bank=((pin-CONTACT_CENTRE)*0.47,16.3 if pin%2 else 16.6)
        board.track(net,[bank,(bank[0],17),(x*1.1,19),(x,TIP_Y-3.0),(x,FINGER_Y)])
        board.via(net,bank)
        contacts[pin]=(*bank,1)
    return_x=-board.pitch
    board.track('GND',[(return_x,4.5),(return_x,13.1)])
    board.via('GND',(return_x,13.1))
    board.track('GND',[(return_x,13.1),(return_x,15.3)],'B.Cu')
    board.via('GND',(return_x,15.3))
    board.track('GND',[(return_x,15.3),(-8.65,16.6)])
    base=Fanout(board)
    history=np.zeros_like(base.occ,dtype=np.float32)
    routes={}

    def restore(records):
        fan=copy.deepcopy(base)
        for segments,vias in records.values():
            for net,a,b,layer,width in segments:
                fan.b.track(net,[a,b],layer,width)
                fan.segment(net,a,b,0 if layer=='F.Cu' else 1,width)
            for net,p in vias:
                fan.b.via(net,p)
                for layer in (0,1):
                    fan.shape(net,p,(VIA_D,VIA_D),'circle',layer)
        fan.penalty=history
        return fan

    priority=[32,31,35,30,27]
    pending=priority+[p for p in range(4,36) if p not in priority]+[3,36]
    for step in range(512):
        if not pending:
            result=restore(routes).b
            result.remove_redundant_vias();result.shield()
            return result
        pin=pending.pop(0);net=board.tail[pin]
        fan=restore(routes)
        ns,nv=len(fan.b.segments),len(fan.b.vias)
        try:
            fan.route(net,board.endpoints[net],contacts[pin])
        except RuntimeError as exc:
            if not str(exc).startswith('No tail fanout'):
                raise
            # Keep successful paths. Rip up only paths actually blocking this net.
            own={p:r for p,r in routes.items() if board.tail[p]==net}
            soft=restore(own)
            foreign=fan.owners & np.uint64(~(1<<board.nets[net]) & ((1<<64)-1))
            soft.penalty=history+(foreign!=0)*8
            ns,nv=len(soft.b.segments),len(soft.b.vias)
            soft.route(net,board.endpoints[net],contacts[pin])
            # A diagonal move also requires its two orthogonal corner cells.
            # Include them when identifying blockers, not only path centres.
            used_cells=set(soft.last_path)
            for a,b in zip(soft.last_path,soft.last_path[1:]):
                if a[2]==b[2] and a[0]!=b[0] and a[1]!=b[1]:
                    used_cells.update([(a[0],b[1],a[2]),(b[0],a[1],a[2])])
            bits=0
            for x,y,layer in used_cells:
                bits |= int(foreign[layer,y,x])
            for _,p in soft.b.vias[nv:]:
                x,y=soft.grid(p)
                patch=foreign[:,max(0,y-4):y+5,max(0,x-4):x+5]
                bits |= int(np.bitwise_or.reduce(patch.ravel(),initial=np.uint64(0)))
            blocked=[p for p in routes if bits & (1<<board.nets[board.tail[p]])]
            if not blocked:
                raise RuntimeError(f'{size}: cannot identify fanout blocker for pin {pin}') from exc
            for x,y,layer in used_cells:
                if foreign[layer,y,x]:
                    patch=history[layer,max(0,y-2):y+3,max(0,x-2):x+3]
                    np.minimum(patch+0.5,8,out=patch)
            for p in blocked:
                del routes[p]
            pending.extend(p for p in blocked if p not in pending)
            print(f'{size}: rip up {blocked} for pin {pin}',flush=True)
            fan=soft
        routes[pin]=(fan.b.segments[ns:],fan.b.vias[nv:])
    raise RuntimeError(f'{size}: fanout negotiation did not converge')


def fabrication_metadata(path):
    """Measure the saved KiCad file, including CLI zone-fill/save transformations."""
    pcb=parse_sexpr(path.read_text())
    points=[];drills=[]
    for item in pcb:
        if not isinstance(item,list):
            continue
        if item[0]=='gr_line' and child(item,'layer')[1]=='Edge.Cuts':
            points.extend(tuple(map(float,child(item,key)[1:3])) for key in ['start','end'])
        if item[0]=='via':
            drills.append(float(child(item,'drill')[1]))
    widths=[p[0] for p in points];heights=[p[1] for p in points]
    features={'width_mm':round(max(widths)-min(widths),6),
              'height_mm':round(max(heights)-min(heights),6),'min_drill_mm':min(drills)}
    metadata={'kind':'pcb','name':'Electrode flex (M)','source':path.name,'qty':5,
              'options':{'layers':2,'thickness_mm':0.4,'finish':'enig'},'features':features}
    path.with_suffix('.fab.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return features


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes',nargs='+',choices=list(PITCHES),default=list(PITCHES))
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--render',action='store_true')
    args=parser.parse_args()
    library();contract=schematic_contract()
    for size in args.sizes:
        board=route_board(size,contract)
        suffix='' if size=='M' else '_'+size
        path=HERE/('neurband_electrodes'+suffix+'.kicad_pcb')
        project_settings(path.with_suffix('.kicad_pro'))
        board.save(path)
        if args.verify:verify(path)
        if args.render:render(path)
        if size=='M':
            print('Measured fabrication features:',fabrication_metadata(path),flush=True)
        print(f'Written {path.name}: pitch {board.pitch}, strip {board.xmax-board.xmin:.3f} x 34, covered arc {15*board.pitch+6.5:.3f}',flush=True)


if __name__=='__main__':
    main()
