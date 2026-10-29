"""Deterministic native-file fallback for rev C; no SWIG or running editor.

All paths are repository relative. Writes retain unrelated native items and
companion metadata. The native CLI must refill/save before release checks.
"""
from bake_cpl_c import parse, dump, get, kids, num, rotate
from pathlib import Path
import copy, json, math, uuid, sys, collections
from shapely.geometry import Point, LineString, Polygon, box
from shapely import affinity, unary_union, contains_xy
import numpy as np

PCB = Path('boards/neurband_c/neurband_c.kicad_pcb')
BUILD = PCB.parent/'layout/build/preorder_20261029'
LAYERS = ['F.Cu','In2.Cu','B.Cu']

def uq(s): return str(s).strip('"')
def ident(): return ['uuid',json.dumps(str(uuid.uuid4()))]
def ref(f): return next(uq(p[2]) for p in kids(f,'property') if uq(p[1])=='Reference')
def setc(n,k,*v):
    c=get(n,k)
    if c is None: n.append([k,*map(str,v)])
    else: c[:]=[k,*map(str,v)]
def pos(f):
    t=get(f,'transform');p=get(t,'translate');r=get(t,'rotate')
    return float(p[1]),float(p[2]),float(r[1])
def move(f,x,y,a=None):
    old=pos(f);a=old[2] if a is None else a
    setc(get(f,'transform'),'translate',num(x),num(y))
    setc(get(f,'transform'),'rotate',num(a))
    for c in f:
        if isinstance(c,list) and c[0] in ('pad','property','fp_text'):
            at=get(c,'at')
            if at:
                angle=(float(at[3]) if len(at)>3 else 0)+a-old[2]
                at[3:]=[num(angle)]
def load(path=PCB): return parse(Path(path).read_text())
def save(t,path=PCB):
    path=Path(path); path.write_text(dump(t)+'\n')
    reread=load(path)
    assert len(kids(reread,'footprint'))==len(kids(t,'footprint'))
def net(n):
    c=get(n,'net');return uq(c[-1]) if c else ''
def item_id(n): return uq(get(n,'uuid')[1])
def track(a,b,n,ly='F.Cu',w=.127):
    return ['segment',['start',*map(num,a)],['end',*map(num,b)],['width',num(w)],['layer',json.dumps(ly)],['net',json.dumps(n)],ident()]
def wire(t,n,pts,ly='F.Cu',w=.127):
    for a,b in zip(pts,pts[1:]):
        if math.dist(a,b)>1e-8:t.append(track(a,b,n,ly,w))
def via(x,y,n='GND'):
    return ['via',['at',num(x),num(y)],['size','0.45'],['drill','0.3'],['layers','"F.Cu"','"B.Cu"'],['tenting','front','back'],['net',json.dumps(n)],ident()]
def remove_ids(t,ids):t[:]=[c for c in t if not(isinstance(c,list)and get(c,'uuid')and item_id(c)in ids)]
def copper(t): return kids(t,'segment')+kids(t,'via')
def pad_data(t):
    out=[]
    for f in kids(t,'footprint'):
        x,y,a=pos(f)
        for p in kids(f,'pad'):
            at=get(p,'at');dx,dy=rotate(float(at[1]),float(at[2]),a);px,py=x+dx,y+dy
            sz=get(p,'size');w,h=map(float,sz[1:]);ang=float(at[3])if len(at)>3 else 0
            if p[3]=='circle':g=Point(0,0).buffer(w/2,quad_segs=24)
            elif p[3]=='oval':
                d=abs(w-h)/2;r=min(w,h)/2
                g=LineString([(-d,0),(d,0)]if w>=h else[(0,-d),(0,d)]).buffer(r,quad_segs=24)
            else:
                r=float(get(p,'roundrect_rratio')[1])*min(w,h)if get(p,'roundrect_rratio')else 0
                g=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r,quad_segs=16)if r else box(-w/2,-h/2,w/2,h/2)
            g=affinity.translate(affinity.rotate(g,-ang,origin=(0,0)),px,py)
            layers=[uq(l)for l in get(p,'layers')[1:]]
            zs=[z for z,l in enumerate(LAYERS)if l in layers or '*.Cu'in layers]
            out.append(dict(ref=ref(f),num=uq(p[1]),net=net(p),poly=g,center=(px,py),layers=zs,id=item_id(p),node=p))
    return out
def shape(c):
    if c[0]=='via':
        a=list(map(float,get(c,'at')[1:3]));return Point(a).buffer(float(get(c,'size')[1])/2,quad_segs=16),[0,1,2]
    a=list(map(float,get(c,'start')[1:3]));b=list(map(float,get(c,'end')[1:3]));ly=uq(get(c,'layer')[1])
    return LineString([a,b]).buffer(float(get(c,'width')[1])/2,quad_segs=12),[LAYERS.index(ly)]

class Router:
    """Fine-grid local route helper with explicit analogue/digital partitions.

    Uses the repository's compiled shortest-path engine. Does not route the
    whole board or alter fixed copper. Every generated link needs native DRC.
    """
    def __init__(self,t,width=.1):
        import ctypes
        self.t=t;self.width=width;self.step=.025;self.W=1149;self.H=1081;self.WH=self.W*self.H
        self.pads=pad_data(t);self.lookup={p['id']:p for p in self.pads}
        self.geometry=collections.defaultdict(lambda:[[],[],[]]);self.vias=[]
        for p in self.pads:
            for z in p['layers']:self.geometry[p['net']][z].append(p['poly'])
        for c in copper(t):
            g,zs=shape(c);n=net(c)
            for z in zs:self.geometry[n][z].append(g)
            self.lookup[item_id(c)]={'net':n,'layers':zs,'center':tuple(map(float,get(c,'at')[1:3]))if c[0]=='via'else tuple(map(float,get(c,'start')[1:3])), 'ends':[tuple(map(float,get(c,k)[1:3]))for k in ('start','end')]if c[0]=='segment'else None}
            if c[0]=='via':self.vias.append((*map(float,get(c,'at')[1:3]),n))
        self.total=np.zeros((3,self.H,self.W),np.int16);self.vtotal=np.zeros((self.H,self.W),np.int16);self.masks={};self.vmasks={}
        outer=box(1,1,27.7,26).buffer(1,quad_segs=32)
        self.edge=np.tile(~self.raster(outer.buffer(-(.3+width/2+.015))),(3,1,1))
        self.vedge=~self.raster(outer.buffer(-.54))
        self.ant=box(0,11.65,5.65,27)
        self.match=Polygon([(2,4.8),(5.7,4.8),(5.7,5.3),(6.35,5.3),(6.35,6.85),(2,6.85)])
        self.edge[:,self.raster(self.ant.buffer(width/2+.015))]=1
        self.edge[:,self.raster(self.match.buffer(width/2+.015))]=1
        self.vedge[self.raster(unary_union([self.ant,self.match]).buffer(.24))]=1
        self.supports=[Point(x,y).buffer(1.5,quad_segs=32)for x,y in [(1.6,1.6),(26.4,1.6),(1.6,25.4),(26.6,22.6)]]
        self.edge[2,self.raster(unary_union(self.supports).buffer(width/2+.015))]=1
        self.vedge[self.raster(unary_union(self.supports).buffer(.24))]=1
        self.vedge[self.raster(unary_union([p['poly']for p in self.pads if p['ref']!='AE1']).buffer(.355))]=1
        analog=[gs for n,gs in self.geometry.items()if n.startswith('/E')or n.startswith('Net-(RN')]
        self.guard0=self.raster(unary_union([g for gs in analog for g in gs[0]]).buffer(1.6))
        self.guard12=self.raster(unary_union([g for gs in analog for ll in gs[1:]for g in ll]).buffer(1.6))
        for n in list(self.geometry):self.refresh(n)
        self.lib=ctypes.CDLL('archive/neurband_main_revB/layout/build/grid_rev_b.so')
        self.lib.route.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int]
    def raster(self,g):
        o=np.zeros((self.H,self.W),bool)
        if g.is_empty:return o
        a,b,c,d=g.bounds;x0=max(0,math.floor(a/self.step));x1=min(self.W,math.ceil(c/self.step)+1);y0=max(0,math.floor(b/self.step));y1=min(self.H,math.ceil(d/self.step)+1)
        if x1>x0 and y1>y0:o[y0:y1,x0:x1]=contains_xy(g,np.arange(x0,x1)[None,:]*self.step,np.arange(y0,y1)[:,None]*self.step)
        return o
    def refresh(self,n):
        if n in self.masks:self.total-=self.masks[n];self.vtotal-=self.vmasks[n]
        gs=self.geometry[n];m=np.zeros_like(self.total,dtype=bool)
        for z in range(3):
            if gs[z]:m[z]=self.raster(unary_union(gs[z]).buffer(.1+self.width/2+.03,quad_segs=8))
        v=self.raster(unary_union([g for ll in gs for g in ll]).buffer(.35+.03,quad_segs=8))
        self.masks[n]=m;self.vmasks[n]=v;self.total+=m;self.vtotal+=v
    def idx(self,p,z):return z*self.WH+round(p[1]/self.step)*self.W+round(p[0]/self.step)
    def coord(self,i):return ((i%self.W)*self.step,(i//self.W%self.H)*self.step,i//self.WH)
    def available(self,n):
        m=self.masks.get(n,np.zeros_like(self.total));v=self.vmasks.get(n,np.zeros_like(self.vtotal))
        b=np.ascontiguousarray(((self.total-m)>0)|self.edge,dtype=np.uint8);vs=np.ascontiguousarray(((self.vtotal-v)==0)&~self.vedge,dtype=np.uint8)
        if n.startswith(('/I2C_','/SPI_','/IMU_INT','/ADC_','/LED'))or n=='Net-(D1-A)':
            b[0,self.guard0]=1;b[1:,self.guard12]=1;vs[self.guard0|self.guard12]=0
        if n.startswith(('/SPI_','/ADC_')):b[:,int(16.6/self.step):,int(10.5/self.step):]=1
        if 'VCAP'in n or 'VREFP'in n or n in ('/RLD_DRV','Net-(U2-RLDINV)'):
            b[1:]=1;vs[:]=0
        return b,vs
    def search(self,n,starts,goals,allow_vias=True):
        b,v=self.available(n)
        if not allow_vias:v[:]=0
        s=np.array(starts,np.int32);g=np.array(goals,np.int32);out=np.empty(30000,np.int32)
        r=self.lib.route(b.ctypes.data,v.ctypes.data,self.W,self.H,3,s.ctypes.data,len(s),g.ctypes.data,len(g),out.ctypes.data,len(out),60,4000000)
        return list(map(int,out[:r]))if r>0 else None
    def link(self,n,a,az,b,bz,allow_vias=True):
        path=self.search(n,[self.idx(a,z)for z in az],[self.idx(b,z)for z in bz],False)
        if path is None and allow_vias:path=self.search(n,[self.idx(a,z)for z in az],[self.idx(b,z)for z in bz],True)
        if path is None:return False
        start=0;direction=None;segs=[];vs=[]
        for k in range(1,len(path)):
            p,q=self.coord(path[k-1]),self.coord(path[k]);d=(round((q[0]-p[0])/self.step),round((q[1]-p[1])/self.step),q[2]-p[2])
            if d[2]:
                if start!=k-1:segs.append((self.coord(path[start]),p))
                vs.append(q[:2]);start=k;direction=None
            elif direction is not None and d!=direction:segs.append((self.coord(path[start]),p));start=k-1;direction=d
            else:direction=d
        if start!=len(path)-1:segs.append((self.coord(path[start]),self.coord(path[-1])))
        p=self.coord(path[0]);q=self.coord(path[-1])
        if math.dist(a,p[:2])>1e-8:segs.insert(0,((*a,p[2]),p))
        if math.dist(b,q[:2])>1e-8:segs.append((q,(*b,q[2])))
        for p,q in segs:
            if math.dist(p[:2],q[:2])<1e-8:continue
            c=track(p[:2],q[:2],n,LAYERS[p[2]],self.width);self.t.append(c);g,_=shape(c);self.geometry[n][p[2]].append(g)
        for x,y in set(vs):
            if any(nn==n and math.dist((x,y),(xx,yy))<.04 for xx,yy,nn in self.vias):continue
            c=via(x,y,n);self.t.append(c);g,zs=shape(c);self.vias.append((x,y,n))
            for z in zs:self.geometry[n][z].append(g)
        self.refresh(n);return True
    def close(self,report):
        failed=[]
        for row in report['unconnected_items']:
            aa=[self.lookup.get(q['uuid'])for q in row['items']]
            if not all(aa):continue
            a,b=aa;n=a['net'];assert n==b['net']
            ends1=a.get('ends')or[a['center']];ends2=b.get('ends')or[b['center']]
            pa,pb=min(((pa,pb)for pa in ends1 for pb in ends2),key=lambda ab:math.dist(*ab))
            ok=self.link(n,pa,a['layers'],pb,b['layers']);print('CLOSE',n,pa,pb,ok,flush=True)
            if not ok:failed.append(row)
        return failed

if __name__=='__main__':
    t=load();r=Router(t)
    failed=r.close(json.loads(Path(sys.argv[1]).read_text()));save(t)
    (BUILD/'closure-failures.json').write_text(json.dumps(failed,indent=2)+'\n')
