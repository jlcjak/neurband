#!/usr/bin/env python3
"""Swap the board's 0402/0603 R, C and L footprints for the smaller project-local ones in
layout/neurband.pretty (*_Small: compact project-local passive land patterns).

Each instance keeps its position, rotation, uuid, schematic link, fields, attributes (DNP), pad nets,
pad uuids and per-pad zone settings. Pads without paste (DNP parts) stay without paste. Only the
footprint id, description, tags, pads' geometry, drawings and 3D model change. Tracks are not touched.

Run: python3 layout/swap_passives_small.py neurband_c.kicad_pcb
"""
import re, sys, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = HERE / 'neurband.pretty'
SWAP = {
    'Capacitor_SMD:C_0402_1005Metric': 'C_0402_Small',
    'Capacitor_SMD:C_0603_1608Metric': 'C_0603_Small',
    'Resistor_SMD:R_0402_1005Metric': 'R_0402_Small',
    'Inductor_SMD:L_0402_1005Metric': 'L_0402_Small',
}
LIB_ONLY_FIELDS = {'KiLib_Generator'}         # fields that came from the old library, not the schematic
GRAPHICS = {'fp_rect', 'fp_line', 'fp_arc', 'fp_circle', 'fp_poly', 'fp_text', 'fp_text_box'}


# ---------------- minimal s-expression reader/writer ----------------
class Str(str):
    pass


def parse(text):
    tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)
    pos, stack, cur = 0, [], []
    while True:
        m = tok.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        if m.group(1):
            stack.append(cur); cur = []
        elif m.group(2):
            done = cur; cur = stack.pop(); cur.append(done)
        elif m.group(3) is not None:
            cur.append(Str(re.sub(r'\\(.)', r'\1', m.group(3))))
        else:
            cur.append(m.group(4))
    return cur[0]


def atom(a):
    if isinstance(a, Str):
        return '"' + a.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return a


def dump(x, ind):
    if not any(isinstance(c, list) for c in x):
        return '(' + ' '.join(atom(c) for c in x) + ')'
    head = [c for c in x if not isinstance(c, list)]
    out = '(' + ' '.join(atom(c) for c in head)
    for c in x:
        if isinstance(c, list):
            out += '\n' + '\t' * (ind + 1) + dump(c, ind + 1)
    return out + '\n' + '\t' * ind + ')'


def find(x, key):
    return next((c for c in x if isinstance(c, list) and c and c[0] == key), None)


def fmt(v):
    return ('%.4f' % v).rstrip('0').rstrip('.') if v != int(v) else str(int(v))


# ---------------- swap ----------------
def new_footprint(old, libname, libfp):
    rot = float(find(find(old, 'transform'), 'rotate')[1]) if find(old, 'transform') else 0.0
    fp = [old[0], Str('neurband:' + libname)]
    old_pads = {c[1]: c for c in old if isinstance(c, list) and c[0] == 'pad'}
    for c in old[2:]:
        if not isinstance(c, list):
            fp.append(c); continue
        k = c[0]
        if k == 'descr':
            fp.append(find(libfp, 'descr'))
        elif k == 'tags':
            fp.append(find(libfp, 'tags'))
        elif k == 'property' and c[1] in LIB_ONLY_FIELDS:
            continue
        elif k == 'duplicate_pad_numbers_are_jumpers':
            fp.append(c)
            for g in libfp:                                      # library drawings go here
                if isinstance(g, list) and g[0] in GRAPHICS:
                    g = [list(e) if isinstance(e, list) else e for e in g]
                    if g[0] == 'fp_text':
                        at = find(g, 'at'); at[:] = ['at', at[1], at[2]] + ([fmt(rot)] if rot else [])
                    g.append(['uuid', Str(str(uuid.uuid4()))])
                    fp.append(g)
        elif k in GRAPHICS:
            continue
        elif k == 'pad':
            lp = next(p for p in libfp if isinstance(p, list) and p[0] == 'pad' and p[1] == c[1])
            pad = [list(e) if isinstance(e, list) else e for e in c]
            pad[2:4] = lp[2:4]                                   # smd roundrect
            for i, e in enumerate(pad):
                if not isinstance(e, list):
                    continue
                if e[0] == 'at':
                    la = find(lp, 'at')
                    pad[i] = ['at', fmt(float(la[1])), fmt(float(la[2]))] + ([fmt(rot)] if rot else [])
                elif e[0] == 'size':
                    pad[i] = ['size'] + [fmt(float(v)) for v in find(lp, 'size')[1:]]
                elif e[0] == 'layers':
                    keep_paste = any('Paste' in v for v in e[1:])
                    pad[i] = ['layers'] + [v for v in find(lp, 'layers')[1:] if keep_paste or 'Paste' not in v]
                elif e[0] == 'roundrect_rratio':
                    pad[i] = ['roundrect_rratio', fmt(float(find(lp, 'roundrect_rratio')[1]))]
            fp.append(pad)
        elif k == 'model':
            lm = [list(e) if isinstance(e, list) else e for e in find(libfp, 'model')]
            lm[1] = Str('${KIPRJMOD}/layout/models/' + Path(lm[1]).name)
            fp.append(lm)
        else:
            fp.append(c)
    assert set(old_pads) == {p[1] for p in libfp if isinstance(p, list) and p[0] == 'pad'}
    return fp


def main(board):
    text = Path(board).read_text()
    libs = {n: parse((LIB / f'{n}.kicad_mod').read_text()) for n in set(SWAP.values())}
    out, last, n = [], 0, 0
    for m in re.finditer(r'\n\t\(footprint "([^"]+)"\n.*?\n\t\)', text, re.S):
        if m.group(1) not in SWAP:
            continue
        old = parse(m.group(0))
        new = new_footprint(old, SWAP[m.group(1)], libs[SWAP[m.group(1)]])
        out.append(text[last:m.start()] + '\n\t' + dump(new, 1))
        last = m.end(); n += 1
    out.append(text[last:])
    Path(board).write_text(''.join(out))
    print(f'swapped {n} footprints')


if __name__ == '__main__':
    main(sys.argv[1])
