"""sections.py - cut drawings of the rev C2 module and pod (exact slices of the solids, drawn with matplotlib).

Step 1 (FreeCAD):  /usr/bin/freecadcmd -c "__file__='mech/rev_c2/sections.py'; exec(open(__file__).read())"
                   slices the solids, writes logs/sections.json and the half models module_section_*.step.
Step 2 (python3):  python3 mech/rev_c2/sections.py     draws renders/section_*.png from that file.
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import params as P

XB = P.XC + P.BODY_HX + P.PIN_DX
CUTS = [                                   # name, plane ('y' = XZ drawing, 'x' = YZ drawing), position, title
    ('xz_mid', 'y', 0.0, 'Across the wrist through the middle pads (y = 0), seen from the hand'),
    ('xz_lug', 'y', 13.5, 'Across the wrist through the strap lugs and bars (y = +13.5)'),
    ('yz_mid', 'x', 0.3, 'Along the arm through the flex tail and J1 (x = +0.3)'),
    ('yz_pads', 'x', 9.0, 'Along the arm through the three pads of one runner and SW1 (x = +9)'),
    ('yz_wall', 'x', P.XC + P.IN_HX + 0.3, 'Along the arm, 0.3 mm inside the +X wall: peg slots, lid pegs and the detent strip'),
    ('xz_peg', 'y', P.PEG_Y[0] + 0.4, 'Across the wrist through two lid pegs under their ledges (y = %.1f)' % (P.PEG_Y[0] + 0.4)),
    ('yz_leads', 'x', 12.0, 'Along the arm through the battery leads and the charge-lead riser (x = +12)'),
]
COL = {'tub': '#2a5cb8', 'lid': '#3d80e0', 'blue_inlay': '#7fb2ff', 'lug_bars': '#1b3f8a', 'main_board': '#0d6b29',
       'board_parts': '#262626', 'lipo': '#c7c9d1', 'lipo_pcm': '#dbb21f', 'leads': '#bf1f1a', 'flex': '#d9801a',
       'electrodes': '#d9ad38', 'strap': '#1c3160', 'pod': '#2a5cb8'}
ORDER = ['strap', 'tub', 'pod', 'lug_bars', 'lid', 'blue_inlay', 'main_board', 'lipo', 'lipo_pcm', 'board_parts', 'flex', 'electrodes', 'leads']

try:
    import FreeCAD
    IN_FREECAD = True
except ImportError:
    IN_FREECAD = False

if IN_FREECAD:
    sys.neurband_lib = True
    import Part
    import c2 as R
    import case as C
    import pod as PD
    V = FreeCAD.Vector

    def module_items():
        pcb, parts = C.board_real()
        bat, pcm = C.battery_solids(False)
        sheet, gold, tail, strip = C.flex_solids()
        lid = C.build_lid()
        return [('tub', C.build_tub(), R.C_TUB), *C.lid_materials(lid), ('lug_bars', C.lug_bars_placed(), R.C_BAR),
                ('main_board', pcb, R.C_PCB), ('board_parts', parts, R.C_PARTS), ('lipo', bat, R.C_LIPO), ('lipo_pcm', pcm, R.C_PCM),
                ('leads', C.leads_visual(), R.C_WIRE), ('flex', Part.makeCompound([sheet, tail, strip]), R.C_FLEX), ('electrodes', gold, R.C_GOLD)]

    def slices(items, axis, pos):
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
        return polys

    log = R.Log('sections')
    items = module_items()
    out = {}
    for name, axis, pos, title in CUTS:
        out[name] = dict(title=title, axis=axis, pos=pos, polys=slices(items, axis, pos), kind='module')
        log(f"  {name}: {len(out[name]['polys'])} outlines")
    pod, _ = PD.build_pod()
    fl, gold = PD.flex_on_pod()
    out['pod'] = dict(title='Pod profile, free (the wings spring %.1f mm before they are level with the middle pad)' % P.WING_D0, axis='x', pos=0.0,
                      polys=slices([('pod', pod, R.C_POD)], 'x', 0.0), kind='pod')
    with open(os.path.join(HERE, 'logs', 'sections.json'), 'w') as f:
        json.dump(out, f)
    big = 200
    for stem, keep in (('module_section_xz', Part.makeBox(big, big, big, V(-big / 2, 0, -big / 2))),
                       ('module_section_yz', Part.makeBox(big, big, big, V(-big + 0.3, -big / 2, -big / 2)))):
        cut = [(n, s.common(keep), c) for n, s, c in items]
        R.save(stem, [(n, s, c) for n, s, c in cut if s.Volume > 1e-3], log)
    R.finish(log)
else:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    data = json.load(open(os.path.join(HERE, 'logs', 'sections.json')))

    def area(p):
        return abs(sum(p[i][0] * p[i + 1][1] - p[i + 1][0] * p[i][1] for i in range(len(p) - 1))) / 2

    def inside(pt, poly):
        x, y = pt
        c = False
        for i in range(len(poly) - 1):
            (x0, y0), (x1, y1) = poly[i], poly[i + 1]
            if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                c = not c
        return c

    for name, d in data.items():
        pod = d.get('kind') == 'pod'
        fig, ax = plt.subplots(figsize=(14, 5.2 if pod else (7.0 if d['axis'] == 'x' else 6.2)))
        by = {}
        for iname, pts in d['polys']:
            by.setdefault(iname, []).append(pts)
        for iname in sorted(by, key=lambda n: ORDER.index(n) if n in ORDER else 99):
            loops = sorted(by[iname], key=area, reverse=True)
            drawn = []
            for lp in loops:
                depth = sum(1 for o in drawn if inside(lp[len(lp) // 3], o))
                ax.add_patch(Polygon(lp, closed=True, facecolor=COL.get(iname, '#888888') if depth % 2 == 0 else 'white',
                                     edgecolor='#111111', linewidth=0.35, zorder=ORDER.index(iname) + 2 if iname in ORDER else 3))
                drawn.append(lp)
        if pod:
            ax.plot([-17, 17], [-P.POD_HC] * 2, color='#c98b6b', lw=1.2, zorder=1)
            ax.text(16.8, -P.POD_HC - 0.25, 'skin when worn', ha='right', va='top', fontsize=8, color='#a0623f')
            ax.set_xlim(-17, 17)
            ax.set_ylim(-4.6, 5.4)
            ax.set_xlabel('along the arm, mm')
            ax.set_ylabel('mm (0 = skin side of the plate; strap side up)')
        else:
            lim = (-25, 25) if d['axis'] == 'y' else (-20, 20)
            ax.plot(lim, [P.Z_SKIN - P.TAPE_T - P.FLEX_T] * 2, color='#c98b6b', lw=1.2, zorder=1)
            ax.set_xlim(*lim)
            ax.set_ylim(-5.2, 9.0)
            ax.set_xlabel('x, mm' if d['axis'] == 'y' else 'y, mm (hand, tail and J1 on the left)')
            ax.set_ylabel('z, mm (0 = floor under the board)')
        ax.set_aspect('equal')
        ax.set_title(d['title'], fontsize=11)
        ax.grid(True, lw=0.2, color='#bbbbbb')
        ax.set_xticks(range(int(ax.get_xlim()[0]), int(ax.get_xlim()[1]) + 1, 2))
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, 'renders', f'section_{name}.png'), dpi=120)
        plt.close(fig)
    print('wrote', ', '.join(f'renders/section_{n}.png' for n in data))
