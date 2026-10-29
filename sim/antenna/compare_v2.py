"""Compare the re-run on the reworked-ground board (results/*_r0.25_v2.json) with the first
board version (results/*_r0.25.json), and evaluate the small-monopole chip-antenna stand-in.

    python sim/antenna/compare_v2.py
"""
import json, os
import numpy as np
import analysis as A

FB = np.array([2.40e9, 2.44e9, 2.48e9])
THROUGH = (('DNP', 0), ('0', 0), ('DNP', 0))


def row(d):
    f, Z = d['f'], d['Z']
    s11 = 20 * np.log10(np.abs(A.gamma(Z)))
    i = np.argmin(abs(f - 2.44e9))
    band = (f >= 2.4e9) & (f <= 2.48e9)
    return dict(f_min=float(f[np.argmin(s11)] / 1e9), s11_min=float(s11.min()), s11_244=float(s11[i]),
                s11_band=float(s11[band].max()), Z=[float(Z[i].real), float(Z[i].imag)],
                eta_rad_db=float(10 * np.log10(d['eta_rad'][1])), eta_tot_db=float(10 * np.log10(d['eta_tot'][1])),
                eta_rad=float(d['eta_rad'][1]), eta_tot=float(d['eta_tot'][1]), n_cells=d['n_cells'])


def zband(d, line=True):
    f, Z = d['f'], d['Z']
    Zp = A.line(Z, f) if line else Z
    return np.interp(FB, f, Zp.real) + 1j * np.interp(FB, f, Zp.imag)


def main():
    out = {}
    for case in ('fs', 'worn'):
        v1, v2 = A.load(f'{case}_r0.25'), A.load(f'{case}_r0.25_v2')
        if v1 is None or v2 is None:
            continue
        r1, r2 = row(v1), row(v2)
        out[case] = {'v1': r1, 'v2': r2}
        print(f"{case:5s} v1: fmin {r1['f_min']:.3f} ({r1['s11_min']:.1f} dB) S11(2.44) {r1['s11_244']:.2f} "
              f"Z {r1['Z'][0]:.1f}{r1['Z'][1]:+.1f}j  eta_rad {r1['eta_rad_db']:.2f}  eta_tot {r1['eta_tot_db']:.2f}")
        print(f"{case:5s} v2: fmin {r2['f_min']:.3f} ({r2['s11_min']:.1f} dB) S11(2.44) {r2['s11_244']:.2f} "
              f"Z {r2['Z'][0]:.1f}{r2['Z'][1]:+.1f}j  eta_rad {r2['eta_rad_db']:.2f}  eta_tot {r2['eta_tot_db']:.2f}")
    # the worn-case pi (5.6 nH series + 0.5 pF shunt) on the new board
    v2w = A.load('worn_r0.25_v2')
    if v2w is not None:
        net = (('DNP', 0), ('L', 5.6), ('C', 0.5))
        zb = zband(v2w)
        out['pi_v2'] = dict(through_db=float(10 * np.log10(A.delivered(zb, FB, THROUGH).min())),
                            matched_db=float(10 * np.log10(A.delivered(zb, FB, net).min())),
                            best=A.fmt_net(A.best_pi(zb, FB)[0][2]),
                            best_db=float(10 * np.log10(A.best_pi(zb, FB)[0][0])))
        print('pi on v2 worn', out['pi_v2'])

    # small-monopole stand-in: match directly at its feed (a chip antenna's match sits at the chip)
    mf, mw = A.load('mono_fs_r0.25_v2'), A.load('mono_worn_r0.25_v2')
    if mf is not None and mw is not None:
        rf, rw = row(mf), row(mw)
        zf, zw = zband(mf, line=False), zband(mw, line=False)
        bench = A.best_pi(zf, FB)[0]          # tuned on the bench (free space)
        onbody = A.best_pi(zw, FB)[0]         # tuned on the wrist
        d_bench_fs = float(10 * np.log10(bench[0]))
        d_bench_worn = float(10 * np.log10(A.delivered(zw, FB, bench[2]).min()))
        d_body_worn = float(10 * np.log10(onbody[0]))
        # -10 dB bandwidth of the bench-tuned stand-in in free space
        f = mf['f']
        Zf = mf['Z']
        dl = A.delivered(Zf, f, bench[2])
        ok = f[dl > 0.9]
        out['mono'] = dict(fs=rf, worn=rw, bench_net=A.fmt_net(bench[2]), body_net=A.fmt_net(onbody[2]),
                           bench_fs_worst_db=d_bench_fs, bench_worn_worst_db=d_bench_worn,
                           body_worn_worst_db=d_body_worn,
                           bench_bw10_MHz=float((ok.max() - ok.min()) / 1e6) if len(ok) else 0.0,
                           tot_worn_bench_db=rw['eta_rad_db'] + d_bench_worn,
                           tot_worn_body_db=rw['eta_rad_db'] + d_body_worn)
        print('mono', json.dumps(out['mono'], indent=1))
    json.dump(out, open(os.path.join(A.RES, 'compare_v2.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
