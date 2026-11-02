"""Pi retune for the owner's board (results/*_r0.25_v3.json): feed 11.79 mm, 0.151 mm (~51 ohm)."""
import json, os, numpy as np
import analysis as A
FB = np.array([2.40e9, 2.42e9, 2.44e9, 2.46e9, 2.48e9])
def zpi(d, df=0.0):
    f = d['f']; z = np.interp(FB + df, f, d['Z'].real) + 1j * np.interp(FB + df, f, d['Z'].imag)
    return A.line(z, FB, l=11.79e-3, Z0=51.0)
fs, worn = A.load('fs_r0.25_v3'), A.load('worn_r0.25_v3')
far = A.load('worn_far_r0.25')          # skin 1.5 mm farther (first board; sensitivity only)
def db(p): return float(10 * np.log10(p.min()))
THRU = (('DNP', 0), ('0', 0), ('DNP', 0))
cands = A.best_pi(zpi(worn), FB)[:400]
rows = []
for wmin, wmean, net in cands:
    r = dict(net=A.fmt_net(net), worn=db(A.delivered(zpi(worn), FB, net)),
             worn_m75=db(A.delivered(zpi(worn, -75e6), FB, net)), worn_p75=db(A.delivered(zpi(worn, 75e6), FB, net)),
             worn_m150=db(A.delivered(zpi(worn, -150e6), FB, net)), worn_p150=db(A.delivered(zpi(worn, 150e6), FB, net)),
             far=db(A.delivered(zpi(far), FB, net)), fs=db(A.delivered(zpi(fs), FB, net)), raw=net)
    r['robust'] = min(r['worn'], r['worn_m75'], r['worn_p75'], r['far'])
    rows.append(r)
t = rows[0].copy(); thru = {k: db(A.delivered(zpi(d, s), FB, THRU)) for k, d, s in
     (('worn', worn, 0), ('worn_m75', worn, -75e6), ('worn_p75', worn, 75e6), ('worn_m150', worn, -150e6), ('worn_p150', worn, 150e6), ('far', far, 0), ('fs', fs, 0))}
thru['robust'] = min(thru['worn'], thru['worn_m75'], thru['worn_p75'], thru['far'])
print('THROUGH (0 ohm):', {k: round(v, 2) for k, v in thru.items()})
print('Zpi worn', np.round(zpi(worn), 1), 'fs', np.round(zpi(fs), 1))
for key in ('worn', 'robust'):
    print('--- best by', key)
    for r in sorted(rows, key=lambda r: -r[key])[:6]:
        print(' ', r['net'], {k: round(r[k], 2) for k in ('worn', 'worn_m75', 'worn_p75', 'worn_m150', 'worn_p150', 'far', 'fs', 'robust')})
json.dump(dict(through=thru, top=[{k: v for k, v in r.items() if k != 'raw'} for r in sorted(rows, key=lambda r: -r['robust'])[:10]]),
          open(os.path.join(A.RES, 'match_v3.json'), 'w'), indent=1)
