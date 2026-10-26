#!/usr/bin/env python3
"""REV C deterministic flex artwork, adapted from archived REV B generator.

Explicit paired trunks and pod-local underpasses; clearance-aware routing only
inside the housing-captured root. KiCad is the connectivity/DRC acceptance gate.
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
import shapely
from shapely.geometry import LineString, Point, box
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
VIA_D = 0.55
VIA_DRILL = 0.3
ORIGIN = (65.0, 35.0)
NS = uuid.UUID('973b1454-8245-4b50-a64c-3bf6d0613e84')


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
    expected = {1: 'GND', 2: '/BIAS_E', 19: '/BIAS_E', 20: 'GND'}
    expected.update({3+2*(i-1)+k: f'/E{i}{kind}' for i in range(1,9) for k,kind in enumerate('PN')})
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
        self.items.append(f'(gr_line (start {xy(a)}) (end {xy(b)}) (stroke (width {width}) (type default)) (layer "{layer}") (uuid "{self.id()}"))')

    def text(self,text,p,layer='F.SilkS',size=0.65):
        mirror='(justify mirror)' if layer.startswith('B.') else ''
        self.items.append(f'(gr_text {q(text)} (at {xy(p)}) (layer "{layer}") (uuid "{self.id()}") (effects (font (size {size} {size}) (thickness 0.12)) {mirror}))')

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
            body.append(f'(pad "{num}" smd {shape} (at {f(local[0])} {f(local[1])}) (size {f(dims[0])} {f(dims[1])}) (layers {layers}) (solder_mask_margin 0) (net {self.nets[net]} {q(net)}) (uuid "{uid(ref+str(num))}"))')
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
                  (pad "" np_thru_hole circle (at 0 0) (size 1.2 1.2) (drill 1.2) (layers "*.Cu" "*.Mask") (uuid "{self.id()}")))''')
            self.text(str(i),(x,-14),size=0.8)
            self.text(str(i),(x,-14),'B.SilkS',0.8)
        self.footprint('J1','FPC_Tail_20_P0.5mm',(0,self.tip-1.9),'B',[(p,(contact_x(p),0),(0.3,3.2),'rect') for p in range(1,21)])
        self.text('1',(4.3,self.tip-4.3),'B.SilkS',0.8)
        self.text('20',(-3.8,self.tip-4.3),'B.SilkS',0.8)
        self.text('1',(4.3,self.tip-7.1),'F.SilkS',0.8)
        self.text('C / SKIN',(0,9),'F.SilkS',0.8)
        self.text('OUTER',(0,9),'B.SilkS',0.8)
        self.text('Optional: 2-3 SMD spring pins, 2 mm heads per round ENIG pad; no paste stencil',(self.xs[4],-19),'F.Fab',0.8)
        stiff=[(-5.25,self.tip-STIFFENER_LENGTH),(5.25,self.tip-STIFFENER_LENGTH),(5.25,self.tip),(-5.25,self.tip)]
        for a,b in zip(stiff,stiff[1:]+stiff[:1]):
            self.line(a,b,'User.2',0.1)
        self.text('F-side PI stiffener; total 0.30 +/-0.03 mm',(0,self.tip+3),'User.2',0.7)
        self.text('Root y3..15 captured; bend only y15..stiffener',(0,17),'User.1',0.65)

    def trunks(self):
        # At the alignment holes, split the trunk into two four-track banks.
        # Each new pair joins above existing tracks; order anticipates mirrored fingers.
        lanes=[3.55,3.75,3.95,4.15,5.85,6.05,6.25,6.45]
        for group,direction in [(list(range(1,4)),1),(list(range(8,4,-1)),-1)]:
            for rank,i in enumerate(group):
                x=self.xs[i]
                ys=lanes[2*rank:2*rank+2]
                for k,kind in enumerate('PN' if direction==1 else 'NP'):
                    net=self.pads[f'E{i}{kind}','1']
                    # Upper lane joins rootward of lower lane; mirrored at the root.
                    vx=x+direction*(-2.45 if k==0 else 2.45)
                    landing=(vx,7.1)
                    if kind=='P':
                        source=(vx,-6.8)
                        self.track(net,[(x,-10),source])
                        self.via(net,source)
                        self.track(net,[source,landing],'B.Cu')
                        self.via(net,landing)
                    else:
                        self.track(net,[(x,10),landing])
                    endpoint=(-4.4 if direction==1 else 4.4,ys[k])
                    self.track(net,[landing,(vx,ys[k]),endpoint])
                    self.endpoints[net]=(*endpoint,0)
        # Pod 4 terminates directly into the captured root, not through its hole.
        x=self.xs[4]
        for kind,y,ey in [('P',-10,-6.7),('N',10,11.8)]:
            net=self.pads[f'E4{kind}','1']
            self.track(net,[(x,y),(x-1.8,ey)])
            target_y=5.0 if kind=='P' else ey
            if kind=='P':
                self.via(net,(x-1.8,ey))
                self.track(net,[(x-1.8,ey),(x-1.8,target_y)],'B.Cu')
                self.via(net,(x-1.8,target_y))
            self.track(net,[(x-1.8,target_y),(3.5,target_y)])
            self.endpoints[net]=(3.5,target_y,0)
        # One simple bias bus directly joins the middle electrodes.
        self.track('/BIAS_E',[(self.xs[1],0),(self.xs[8],0)],width=0.2)
        # A covered B-side return crosses each free link; F-side pod underpasses
        # avoid the B-side signal crossings. The root underpass is also F.Cu.
        for i,x in self.xs.items():
            for dx in (-2.95,2.95):
                self.via('GND',(x+dx,-6))
                if not (i==1 and dx<0 or i==8 and dx>0):
                    self.track('GND',[(x+dx,-6),(x+dx,3.41)],'B.Cu')
            self.track('GND',[(x-2.95,-6),(x+2.95,-6)])
        for i in range(1,8):
            a,b=self.xs[i],self.xs[i+1]
            if i==3:
                for x in (a+2.95,b-2.95):
                    self.track('GND',[(x,3.41),(x,2.3)],'B.Cu')
                    self.via('GND',(x,2.3))
                self.track('GND',[(a+2.95,2.3),(b-2.95,2.3)])
            else:
                self.track('GND',[(a+2.95,3.41),(b-2.95,3.41)],'B.Cu')

    def shield(self):
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
        layers=[(0,'F.Cu','signal'),(31,'B.Cu','signal'),(36,'B.SilkS','user'),(37,'F.SilkS','user'),(38,'B.Mask','user'),(39,'F.Mask','user'),(44,'Edge.Cuts','user'),(48,'B.Fab','user'),(49,'F.Fab','user'),(50,'User.1','user'),(51,'User.2','user')]
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


class Fanout:
    """Local two-layer root fanout, 0.10 mm grid and 0.10 mm tracks."""
    STEP = 0.1
    def __init__(self, board):
        self.b=board
        self.x0,self.y0=-12.0,-14.65
        self.nx,self.ny=241,292
        self.occ=np.zeros((2,self.ny,self.nx),dtype=np.int16)
        ys,xs=np.mgrid[:self.ny,:self.nx]
        xx,yy=xs*self.STEP+self.x0,ys*self.STEP+self.y0
        self.outside=~shapely.contains_xy(board.outline.buffer(-0.36),xx,yy)
        # Root crossovers may also use the two supported adjacent pod columns.
        # Drilled holes block both routing layers, including prospective vias.
        for x in board.xs.values():
            for y in (-5,5):
                self.outside |= (xx-x)**2+(yy-y)**2 < (0.6+0.2+WIDTH/2)**2
        self.owners=None
        self.penalty=None
        for net,p,dims,shape,layer in board.pad_shapes:
            self.shape(net,p,dims,shape,layer)
        for net,a,b,layer,width in board.segments:
            self.segment(net,a,b,0 if layer=='F.Cu' else 1,width)
        for net,p in board.vias:
            for layer in (0,1):
                self.shape(net,p,(VIA_D,VIA_D),'circle',layer)
        self.dist=np.empty_like(self.occ,dtype=np.float32)
        self.prev=np.empty_like(self.occ,dtype=np.int32)
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
        extra=0.1+0.05-1e-7
        rx,ry=dims[0]/2+extra,dims[1]/2+extra
        def test(x,y):
            if shape=='circle':
                return (x-p[0])**2+(y-p[1])**2<=rx**2
            return (abs(x-p[0])<=rx)&(abs(y-p[1])<=ry)
        self.paint(net,p[0]-rx,p[0]+rx,p[1]-ry,p[1]+ry,test,layer)

    def segment(self,net,a,b,layer,width):
        r=width/2+0.1+0.05-1e-7
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
        # The free tail is prewired on B.Cu; search only the captured root.
        valid[:,row_y>14.5+1e-6,:]=False
        if not valid[sl,sy,sx] or not valid[el,ey,ex]:
            raise RuntimeError(f'{net} blocked endpoints {start} {end}')
        # Evaluate via geometry directly; grid erosion over-reserves diagonal
        # channels and cannot accurately distinguish 0.45/0.50/0.55 mm pads.
        yy,xx=np.mgrid[:self.ny,:self.nx]
        physical_x=xx*self.STEP+self.x0
        physical_y=yy*self.STEP+self.y0
        extra=VIA_D/2+CLEARANCE+0.003
        obstacles=[]
        for pad_net,p,dims,shape,layer in self.b.pad_shapes:
            if pad_net==net and not (layer==0 and shape=='circle'):
                continue
            if shape=='circle':
                obstacles.append(Point(p).buffer(dims[0]/2+extra,quad_segs=32))
            else:
                obstacles.append(box(p[0]-dims[0]/2,p[1]-dims[1]/2,
                                     p[0]+dims[0]/2,p[1]+dims[1]/2).buffer(extra,quad_segs=32))
        for track_net,a,b,layer,width in self.b.segments:
            if track_net!=net:
                obstacles.append(LineString([a,b]).buffer(width/2+extra,quad_segs=32))
        for x in self.b.xs.values():
            for y in (-5,5):
                obstacles.append(Point(x,y).buffer(0.6+0.2+VIA_D/2+0.003,quad_segs=32))
        existing_vias={}
        for via_net,p in self.b.vias:
            if via_net!=net:
                obstacles.append(Point(p).buffer(VIA_D+CLEARANCE+0.003,quad_segs=32))
            else:
                vx,vy=self.grid(p)
                if 0<=vx<self.nx and 0<=vy<self.ny:
                    existing_vias[vx,vy]=p
        via_valid=valid[0]&valid[1]&(physical_y<=14.0)
        via_valid &= shapely.contains_xy(self.b.outline.buffer(-(0.3+VIA_D/2+0.003)),
                                        physical_x,physical_y)
        via_valid &= ~shapely.contains_xy(unary_union(obstacles),physical_x,physical_y)
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
        # Exact physical endpoints also support pitches not aligned to this grid.
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
    fp.append(Pad(number='',type=Pad.TYPE_NPTH,shape=Pad.SHAPE_CIRCLE,at=[0,0],size=[1.2,1.2],drill=1.2,layers=Pad.LAYERS_NPTH))
    KicadFileHandler(fp).writeFile(str(lib/'Alignment_D1.2mm.kicad_mod'))
    (HERE/'fp-lib-table').write_text('(fp_lib_table (lib (name "neurband_c_flex")(type "KiCad")(uri "${KIPRJMOD}/neurband_c_flex.pretty")(options "")(descr "REV C fabricated contacts")))\n')


def route_board(board):
    board.geometry()
    board.trunks()
    contacts={}
    for pin in range(1,21):
        net=board.tail[pin]
        x=contact_x(pin)
        board.track(net,[(x,board.tip-1.9),(x,14.5)],'B.Cu')
        contacts[pin]=(x,14.5,1)
    for pin in (1,20):
        x=contact_x(pin)
        board.track('GND',[(x,14.5),(x,2.3)],'B.Cu')
        board.via('GND',(x,2.3))
    for pin in (2,19):
        x=contact_x(pin)
        board.track('/BIAS_E',[(x,14.5),(x,0)],'B.Cu')
        board.via('/BIAS_E',(x,0))
    grid=Fanout(board)
    # Reserve the exact-to-grid stubs before any route; otherwise a later
    # route can obstruct another contact's off-grid access point.
    for net,p in list(board.endpoints.items()):
        point=grid.point(*grid.grid(p[:2]))
        board.track(net,[p[:2],point],'F.Cu' if p[2]==0 else 'B.Cu')
        board.endpoints[net]=(*point,p[2])
    for pin,p in list(contacts.items()):
        if pin not in range(3,19):
            continue
        point=grid.point(*grid.grid(p[:2]))
        board.track(board.tail[pin],[p[:2],point],'B.Cu')
        contacts[pin]=(*point,p[2])
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

    pending=[9,10,4,3,6,5,8,7,18,17,16,15,14,13,12,11]
    for step in range(384):
        if not pending:
            result=restore(routes).b
            result.shield()
            return result
        pin=pending.pop(0)
        net=board.tail[pin]
        fan=restore(routes)
        # Left-bank crossovers favour B, right-bank crossovers favour F.
        # This separates the two opposing bundles instead of braiding both layers.
        fan.penalty=history.copy()
        fan.penalty[0 if board.endpoints[net][0]<0 else 1]+=2
        ns,nv=len(fan.b.segments),len(fan.b.vias)
        try:
            fan.route(net,board.endpoints[net],contacts[pin])
        except RuntimeError as exc:
            if not str(exc).startswith('No tail fanout'):
                raise
            own={p:r for p,r in routes.items() if board.tail[p]==net}
            soft=restore(own)
            foreign=fan.owners & np.uint64(~(1<<board.nets[net]) & ((1<<64)-1))
            soft.penalty=history+(foreign!=0)*8
            soft.penalty[0 if board.endpoints[net][0]<0 else 1]+=2
            ns,nv=len(soft.b.segments),len(soft.b.vias)
            soft.route(net,board.endpoints[net],contacts[pin])
            used_cells=set(soft.last_path)
            for a,b in zip(soft.last_path,soft.last_path[1:]):
                if a[2]==b[2] and a[0]!=b[0] and a[1]!=b[1]:
                    used_cells.update([(a[0],b[1],a[2]),(b[0],a[1],a[2])])
            bits=0
            for x,y,layer in used_cells:
                bits |= int(foreign[layer,y,x])
            for _,p in soft.b.vias[nv:]:
                x,y=soft.grid(p)
                bits |= int(np.bitwise_or.reduce(foreign[:,max(0,y-4):y+5,max(0,x-4):x+5].ravel(),initial=np.uint64(0)))
            blocked=[p for p in routes if bits & (1<<board.nets[board.tail[p]])]
            if not blocked:
                raise RuntimeError(f'Cannot identify root blocker for pin {pin}') from exc
            for x,y,layer in used_cells:
                if foreign[layer,y,x]:
                    patch=history[layer,max(0,y-2):y+3,max(0,x-2):x+3]
                    np.minimum(patch+0.5,8,out=patch)
            for p in blocked:
                del routes[p]
            pending.extend(p for p in blocked if p not in pending)
            print(f'Root: rip up {blocked} for pin {pin}',flush=True)
            fan=soft
        routes[pin]=(fan.b.segments[ns:],fan.b.vias[nv:])
    raise RuntimeError('Root fanout negotiation did not converge')


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
        if item[0]=='zone' and child(item,'net')[1]=='GND':
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
    metadata={'kind':'pcb','name':'Electrode flex rev C','source':path.name,'qty':5,
              'options':{'layers':2,'thickness_mm':0.4,'finish':'enig'},'features':features}
    path.with_suffix('.fab.json').write_text(json.dumps(metadata,indent=2)+'\n')
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
