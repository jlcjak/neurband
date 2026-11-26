"""sections.py - cut drawings of the module (exact slices of the solids, drawn with matplotlib).

Step 1 (FreeCAD):  freecadcmd -c "__file__='mech/rev_c/sections.py'; exec(open(__file__).read())"
                   slices every solid of the module and writes logs/sections.json, and saves
                   module_section_xz.step / module_section_yz.step (half models for the 3D viewer).
Step 2 (python3):  python3 mech/rev_c/sections.py     draws renders/section_*.png from that file.
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import params as P

CUTS = [                                   # name, plane ('y' = XZ drawing, 'x' = YZ drawing), position, title
    ('xz_mid', 'y', 0.0, 'Across the wrist through the pod centres (y = 0), seen from the hand'),
    ('xz_e3', 'y', 10.0, 'Across the wrist through the proximal electrodes (y = +10)'),
    ('yz_sw1', 'x', P.SW1[0], 'Along the arm through the SW1 guard and battery deck (x = +10.8)'),
    ('yz_mid', 'x', 0.0, 'Along the arm through the flex tail and J1 (x = 0)'),
    ('yz_wires', 'x', 12.3, 'Along the arm through the battery leads (x = +12.3)'),
]
COL = {'cradle': '#2a5cb8', 'holder': '#1b3f8a', 'lid': '#3d80e0', 'lug_bars': '#1b3f8a',
       'main_board': '#0d6b29', 'board_parts': '#262626', 'lipo': '#c7c9d1',
       'lipo_pcm': '#dbb21f', 'leads': '#bf1f1a', 'tail': '#d9801a', 'flex': '#d9801a', 'foam_dots': '#efefe8',
       'electrodes': '#d9ad38', 'strap': '#1c3160', 'pods': '#2a5cb8'}

try:
    import FreeCAD
    IN_FREECAD = True
except ImportError:
    IN_FREECAD = False

if IN_FREECAD:
    sys.neurband_lib = True
    sys.neurband_band_lib = True
    import Part
    import rc as R
    import module as M
    import cadutil as U
    V = FreeCAD.Vector

    def module_items():
        pcb, parts = M.board_real()
        bat, pcm, _ = M.battery_solids()
        tail, _ = M.tail_shape()
        pad0, gold0, foam0 = R.flex_pod_visual(P.FOAM_WORN)
        flex, gold, foam = [tail], [], []
        for sx in (1, -1):
            pl = FreeCAD.Placement(V(sx * P.DIMPLE_X, 0, P.DIMPLE_Z), FreeCAD.Rotation(V(0, 1, 0), math.degrees(sx * P.POD_TILT)))
            for src, dst in ((pad0, flex), (gold0, gold), (foam0, foam)):
                for sh in (src if isinstance(src, list) else [src]):
                    c = sh.copy()
                    c.Placement = pl.multiply(c.Placement)
                    dst.append(c)
        # Printed slide-in cross-bars + 26 mm sewn nylon loop wrapping round them
        t = P.STRAP_T * 0.65
        strap = []
        for sx in (1, -1):
            xp = M.XC + sx * (P.BODY_HX + P.PIN_DX)
            zp = P.BAR_ZC
            x_out = M.XC + sx * (P.LUG_HX + 4.0)
            hw_b, hh_b = P.BAR_W / 2 + 0.12, P.BAR_H / 2 + 0.12
            loop_pts = [
                (x_out, zp - 3.4 + t),
                (xp + sx * (hw_b + t * 0.7), zp + hh_b + t),
                (xp - sx * (hw_b + t), zp + hh_b + t),
                (xp - sx * (hw_b + t), zp - hh_b - t),
                (xp + sx * hw_b, zp - hh_b - t),
                (x_out, zp - 3.4 - t),
                (x_out, zp - 3.4 - 0.12),
                (xp + sx * hw_b, zp - hh_b),
                (xp - sx * hw_b, zp - hh_b),
                (xp - sx * hw_b, zp + hh_b),
                (xp + sx * hw_b, zp + hh_b),
                (x_out, zp - 3.4 + 0.12),
            ]
            strap.append(R.prism_xz(loop_pts, -P.STRAP_W / 2, P.STRAP_W / 2))
        return [('cradle', M.build_cradle(), R.C_CRADLE), ('holder', M.build_holder(), R.C_HOLDER),
                ('lid', M.build_lid(), R.C_LID), ('lug_bars', M.lug_pins_visual(), R.C_HOLDER),
                ('main_board', pcb, R.C_PCB), ('board_parts', parts, R.C_PARTS),
                ('lipo', bat, R.C_LIPO), ('lipo_pcm', pcm, R.C_PCM), ('leads', M.wires_visual(), R.C_WIRE),
                ('flex', Part.makeCompound(flex), R.C_FLEX), ('foam_dots', Part.makeCompound(foam), R.C_FOAM),
                ('electrodes', Part.makeCompound(gold), R.C_GOLD), ('strap', Part.makeCompound(strap), R.C_STRAP)]

    log = R.Log('sections')
    items = module_items()
    out = {}
    for name, axis, pos, title in CUTS:
        nrm = V(0, 1, 0) if axis == 'y' else V(1, 0, 0)
        polys = []
        for iname, sh, col in items:
            for sol in (sh.Solids or [sh]):
                try:
                    wires = sol.slice(nrm, pos)
                except Exception:
                    continue
                for w in wires:
                    pts = w.discretize(Deflection=0.02)
                    polys.append((iname, [(round(p.x if axis == 'y' else p.y, 3), round(p.z, 3)) for p in pts]))
        out[name] = dict(title=title, axis=axis, pos=pos, polys=polys)
        log(f"  {name}: {len(polys)} outlines")
    with open(os.path.join(HERE, 'logs', 'sections.json'), 'w') as f:
        json.dump(out, f)
    big = 200
    for stem, keep in (('module_section_xz', Part.makeBox(big, big, big, V(-big / 2, 0, -big / 2))),
                       ('module_section_yz', Part.makeBox(big, big, big, V(-big + P.SW1[0], -big / 2, -big / 2)))):
        cut = [(n, s.common(keep), c) for n, s, c in items]
        R.save(stem, [(n, s, c) for n, s, c in cut if s.Volume > 1e-3], log)
    R.finish(log)
else:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    data = json.load(open(os.path.join(HERE, 'logs', 'sections.json')))
    order = ['strap', 'cradle', 'lug_bars', 'holder', 'lid', 'main_board', 'lipo', 'lipo_pcm', 'board_parts', 'foam_dots', 'flex', 'electrodes', 'leads']
    for name, d in data.items():
        fig, ax = plt.subplots(figsize=(14, 7.5 if d['axis'] == 'x' else 6.5))
        # holes: an outline that lies inside another outline of the same part is drawn in the background colour
        by = {}
        for iname, pts in d['polys']:
            by.setdefault(iname, []).append(pts)
        for iname in sorted(by, key=lambda n: order.index(n) if n in order else 99):
            loops = by[iname]
            def area(p):
                return abs(sum(p[i][0] * p[i + 1][1] - p[i + 1][0] * p[i][1] for i in range(len(p) - 1))) / 2
            loops.sort(key=area, reverse=True)
            def inside(pt, poly):
                x, y = pt; c = False
                for i in range(len(poly) - 1):
                    (x0, y0), (x1, y1) = poly[i], poly[i + 1]
                    if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                        c = not c
                return c
            drawn = []
            for lp in loops:
                depth = sum(1 for o in drawn if inside(lp[len(lp) // 3], o))
                ax.add_patch(Polygon(lp, closed=True, facecolor=COL.get(iname, '#888888') if depth % 2 == 0 else 'white',
                                     edgecolor='#111111', linewidth=0.35, zorder=order.index(iname) + 2 if iname in order else 3))
                drawn.append(lp)
        if d['axis'] == 'y':
            # design skin under the module
            xs = [x / 5.0 for x in range(-130, 131)]
            ax.plot(xs, [P.SKIN_ZC + math.sqrt(P.R_DESIGN ** 2 - x * x) for x in xs], color='#c98b6b', lw=1.2, zorder=1)
            ax.set_xlim(-27, 27); ax.set_ylim(-9.5, 10.2)
        else:
            ax.plot([-21, 21], [P.SKIN_APEX_Z] * 2, color='#c98b6b', lw=1.2, zorder=1)
            ax.set_xlim(-21, 21); ax.set_ylim(-5, 10.2)
        ax.set_aspect('equal')
        ax.set_title(d['title'], fontsize=11)
        ax.set_xlabel('x, mm' if d['axis'] == 'y' else 'y, mm (tail and J1 end on the left)')
        ax.set_ylabel('z, mm (0 = cradle top / board underside)')
        ax.grid(True, lw=0.2, color='#bbbbbb')
        ax.set_xticks(range(int(ax.get_xlim()[0]), int(ax.get_xlim()[1]) + 1, 2))
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, 'renders', f'section_{name}.png'), dpi=120)
        plt.close(fig)
    print('wrote', ', '.join(f'renders/section_{n}.png' for n in data))
