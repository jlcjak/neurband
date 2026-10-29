"""Post-processing of the openEMS antenna runs: tables, pi-network retune, BLE link budget, plots.

    python sim/antenna/analysis.py            (reads sim/antenna/results/*.json)

Writes sim/antenna/results/summary.json and docs/science/figures/antenna_*.png.
"""
import itertools, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
RES = os.path.join(HERE, 'results')
FIG = os.path.join(ROOT, 'docs', 'science', 'figures')
C0 = 299792458.0

# ---- feed line from the pi network (R3 pad 1 / C23) to the antenna feed pad ----------
# tracks of Net-(AE1-A) in the board: 0.89 + 1.65 + 5.32 + 3.35 + 1.00 mm, 0.16 mm wide,
# 0.1 mm over L2; ~50 ohm covered (boards/neurband_c/layout/rf_geometry.md), eps_eff ~3.05
L_FEED = 12.21e-3
Z0_FEED, EEFF_FEED = 50.0, 3.05
LOSS_FEED_DB = 0.3      # conductor (ENIG/roughness) + tan d 0.02, 12 mm at 2.44 GHz

# 0402 parts: C0G caps and the fab's stock inductor values; Q at 2.4 GHz (typical
# datasheet: C0G 0402 Q 50-100 at 2.4 GHz, multilayer 0402 L Q 15-25 at 2.4 GHz)
CAPS = [0.3, 0.4, 0.5, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.9, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1, 10.0]   # FH 0402CG C0G in the fab stock
INDS = [1.0, 1.3, 1.8, 2.0, 2.2, 2.4, 2.7, 3.3, 3.9, 4.3, 4.7, 5.1, 5.6, 6.8, 7.5, 8.2, 9.1, 10.0]   # Sunlord SDCL1005 values in the fab stock
QC, QL = 60.0, 20.0

CASES = [('fs', 'board alone, free space'),
         ('enc', '+ cell + PA12 housing'),
         ('flex', '+ flex pods 3/4 (pads + GND hatch)'),
         ('worn', '+ wrist (worn)'),
         ('worn_nohatch', 'worn, pod 3 hatch cut under antenna'),
         ('worn_far', 'worn, skin 1.5 mm farther (sensitivity)'),
         ('mono_fs', 'small monopole stand-in, free space'),
         ('mono_worn', 'small monopole stand-in, worn')]


def load(tag):
    p = os.path.join(RES, tag + '.json')
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    d['f'] = np.array(d['f'])
    d['Z'] = np.array(d['Zin_re']) + 1j * np.array(d['Zin_im'])
    return d


def gamma(Z, Z0=50.0):
    return (Z - Z0) / (Z + Z0)


def line(ZL, f, l=L_FEED, Z0=Z0_FEED, eeff=EEFF_FEED):
    """Input impedance of a lossless line of length l terminated in ZL."""
    t = np.tan(2 * np.pi * f * np.sqrt(eeff) / C0 * l)
    return Z0 * (ZL + 1j * Z0 * t) / (Z0 + 1j * ZL * t)


def zc(C, f):
    w = 2 * np.pi * f
    X = -1 / (w * C * 1e-12)
    return abs(X) / QC + 1j * X


def zl(L, f):
    w = 2 * np.pi * f
    X = w * L * 1e-9
    return X / QL + 1j * X


def par(a, b):
    return a * b / (a + b)


def element(kind, v, f):
    if kind == 'C':
        return zc(v, f)
    if kind == 'L':
        return zl(v, f)
    if kind == '0':
        return 0.05 + 0j * f
    return None   # DNP


def delivered(Zload, f, net):
    """Fraction of available power from a 50-ohm source that reaches Zload through the
    pi (shunt1 at the radio side = C22, series = R3, shunt2 at antenna side = C23).
    Lossy parts: computed via ABCD, P_load / P_avail."""
    s1, se, s2 = net
    n = len(np.atleast_1d(f))
    A = np.ones(n, complex); B = np.zeros(n, complex); C = np.zeros(n, complex); D = np.ones(n, complex)

    def cascade(M, A, B, C, D):
        a, b, c, d = M
        return A * a + B * c, A * b + B * d, C * a + D * c, C * b + D * d
    for pos, (k, v) in zip(('sh', 'se', 'sh'), (s1, se, s2)):
        z = element(k, v, f)
        if z is None:
            continue
        M = (1, 0, 1 / z, 1) if pos == 'sh' else (1, z, 0, 1)
        A, B, C, D = cascade(M, A, B, C, D)
    Zs = 50.0
    # V_load / V_s for source Zs, load ZL:  ZL / (A ZL + B + Zs (C ZL + D))
    VL = Zload / (A * Zload + B + Zs * (C * Zload + D))
    PL = np.abs(VL) ** 2 * np.real(Zload) / np.abs(Zload) ** 2 / 2
    Pav = 1 / (8 * Zs)
    return PL / Pav


def best_pi(Zpi_band, fband, weight=None):
    """Search two-element L sections and the full pi with standard values. Returns list
    sorted by worst-case delivered power over fband."""
    sh = [('DNP', 0)] + [('C', c) for c in CAPS] + [('L', l) for l in INDS]
    se = [('0', 0)] + [('C', c) for c in CAPS] + [('L', l) for l in INDS]
    out = []
    for s1, s, s2 in itertools.product(sh, se, sh):
        nparts = (s1[0] != 'DNP') + (s[0] != '0') + (s2[0] != 'DNP')
        if nparts > 2:
            continue
        p = delivered(Zpi_band, fband, (s1, s, s2))
        out.append((float(p.min()), float(p.mean()), (s1, s, s2)))
    out.sort(key=lambda t: -t[0])
    return out


def fmt_net(net):
    s1, s, s2 = net
    def f(e, shunt):
        k, v = e
        if k == 'DNP':
            return 'DNP'
        if k == '0':
            return '0 ohm'
        return f'{v:g} {"pF" if k == "C" else "nH"}'
    return f'C22 pos: {f(s1, 1)}; R3 pos: {f(s, 0)}; C23 pos: {f(s2, 1)}'


def main():
    os.makedirs(FIG, exist_ok=True)
    summ = {}
    fband = np.array([2.40e9, 2.44e9, 2.48e9])
    data = {}
    for tag, label in CASES:
        d = load(tag + '_r0.25')
        if d is None:
            continue
        data[tag] = d
        f, Z = d['f'], d['Z']
        G = gamma(Z)
        s11 = 20 * np.log10(np.abs(G))
        i = np.argmin(abs(f - 2.44e9))
        band = (f >= 2.4e9) & (f <= 2.48e9)
        below = f[s11 < -10]
        fres = f[np.argmin(s11)]
        Zpi = line(Z, f)
        e = dict(label=label, Z244=[Z[i].real, Z[i].imag], s11_244=float(s11[i]),
                 s11_band_worst=float(s11[band].max()), f_min=float(fres),
                 s11_min=float(s11.min()),
                 bw10=[float(below.min()), float(below.max())] if len(below) else None,
                 Zpi244=[Zpi[i].real, Zpi[i].imag],
                 mismatch_db_244=float(10 * np.log10(1 - abs(G[i]) ** 2)),
                 eta_rad=d['eta_rad'], eta_tot=d['eta_tot'],
                 eta_rad_db=list(10 * np.log10(d['eta_rad'])), eta_tot_db=list(10 * np.log10(d['eta_tot'])),
                 n_cells=d['n_cells'], run_s=d.get('run_s'))
        summ[tag] = e
        print(f"{tag:13s} Z(2.44)={Z[i]:.1f}  S11={s11[i]:6.1f} dB  worst-band {e['s11_band_worst']:6.1f}  "
              f"fmin={fres/1e9:.3f} ({e['s11_min']:.1f} dB)  bw10={e['bw10']}  "
              f"eta_rad={np.round(e['eta_rad_db'],1)} dB  eta_tot={np.round(e['eta_tot_db'],1)} dB")

    # convergence pairs
    conv = {}
    for tag in ('fs', 'worn', 'flex'):
        for r in ('0.35', '0.18'):
            d = load(f'{tag}_r{r}')
            if d is not None:
                f, Z = d['f'], d['Z']
                s11 = 20 * np.log10(np.abs(gamma(Z)))
                i = np.argmin(abs(f - 2.44e9))
                conv[f'{tag}_r{r}'] = dict(f_min=float(f[np.argmin(s11)]), s11_244=float(s11[i]),
                                           Z244=[Z[i].real, Z[i].imag],
                                           eta_rad_db=list(10 * np.log10(d['eta_rad'])),
                                           eta_tot_db=list(10 * np.log10(d['eta_tot'])),
                                           n_cells=d['n_cells'])
                print('conv', tag, r, conv[f'{tag}_r{r}'])
    summ['convergence'] = conv

    # ---- pi-network retune for the worn case (and the hatch-cut variant) ----------
    match = {}
    for tag in ('worn', 'worn_nohatch', 'worn_far', 'flex', 'mono_fs', 'mono_worn'):
        if tag not in data:
            continue
        d = data[tag]
        f, Z = d['f'], d['Z']
        Zpi = line(Z, f)
        zb = np.interp(fband, f, Zpi.real) + 1j * np.interp(fband, f, Zpi.imag)
        base = delivered(zb, fband, (('DNP', 0), ('0', 0), ('DNP', 0)))
        cands = best_pi(zb, fband)
        top = cands[0]
        # robustness: the same parts with the free-space / enclosure-only impedance
        other = {}
        others = ('mono_fs', 'mono_worn') if tag.startswith('mono') else ('fs', 'enc', 'flex', 'worn', 'worn_nohatch', 'worn_far')
        for o in others:
            if o in data:
                Zo = line(data[o]['Z'], data[o]['f'])
                zo = np.interp(fband, data[o]['f'], Zo.real) + 1j * np.interp(fband, data[o]['f'], Zo.imag)
                other[o] = [float(10 * np.log10(delivered(zo, fband, top[2]).min())),
                            float(10 * np.log10(delivered(zo, fband, (('DNP', 0), ('0', 0), ('DNP', 0))).min()))]
        # robustness to a model frequency error: evaluate at Z(f + df)
        shift = {}
        for df in (-150e6, -75e6, 75e6, 150e6):
            zs = np.interp(fband + df, f, Zpi.real) + 1j * np.interp(fband + df, f, Zpi.imag)
            shift[f'{df/1e6:+.0f} MHz'] = [round(float(10 * np.log10(delivered(zs, fband, top[2]).min())), 2),
                                           round(float(10 * np.log10(delivered(zs, fband, (('DNP', 0), ('0', 0), ('DNP', 0))).min())), 2)]
        match_shift = shift
        match[tag] = dict(Zpi_band=[[z.real, z.imag] for z in zb], freq_error_matched_vs_through_db=match_shift,
                          through_db=[float(x) for x in 10 * np.log10(base)],
                          best=fmt_net(top[2]), best_worst_db=float(10 * np.log10(top[0])),
                          best_mean_db=float(10 * np.log10(top[1])),
                          gain_db=float(10 * np.log10(top[0]) - 10 * np.log10(base.min())),
                          top5=[(fmt_net(c[2]), round(10 * np.log10(c[0]), 2)) for c in cands[:5]],
                          same_parts_other_cases_worst_db_vs_through=other)
        print('MATCH', tag, json.dumps(match[tag], indent=1))
    summ['match'] = match

    # ---- BLE link budget ----------------------------------------------------------
    lb = {}
    if 'worn' in summ:
        variants = []
        for tag in ('worn', 'worn_nohatch', 'worn_far'):
            if tag in summ:
                variants.append((tag, summ[tag]['eta_tot_db'][1]))     # includes mismatch at 2.44 GHz
        if 'worn' in match:
            # retuned pi (worn design) applied to worn: radiation eff x delivered fraction (worst in band)
            variants.append(('worn+pi', 10 * np.log10(summ['worn']['eta_rad'][1]) + match['worn']['best_worst_db']))
        for tag, eta_tot_db in variants:
            rows = []
            for dist in (0.5, 1.0, 2.0, 3.0):
                fspl = 20 * np.log10(4 * np.pi * dist * 2.44e9 / C0)
                for phy, sens in (('1M', -96.0), ('2M', -93.0)):
                    # long (251 B) packets need ~3 dB above the BER 1e-3 sensitivity point
                    req = sens + 3.0
                    prx = 4.0 + eta_tot_db - LOSS_FEED_DB + (-2.0) - fspl
                    rows.append(dict(d=dist, phy=phy, fspl=round(fspl, 1), prx_los=round(prx, 1),
                                     margin_los=round(prx - req, 1),
                                     margin_arm=round(prx - 10 - req, 1),
                                     margin_torso=round(prx - 25 - req, 1)))
            lb[tag] = dict(eta_tot_db=eta_tot_db, rows=rows)
            for r in rows:
                print('LB', tag, r)
    summ['link_budget'] = lb
    json.dump(summ, open(os.path.join(RES, 'summary.json'), 'w'), indent=1)
    # markdown rows for docs/science/antenna_sim.md
    print('\n| Case | S11 min (GHz, dB) | S11 at 2.44 | worst S11 2.40-2.48 | Z feed at 2.44 (ohm) | '
          'eta_rad 2.44 | eta_tot 2.44 (incl. mismatch) |')
    print('|---|---|---:|---:|---|---:|---:|')
    for tag, label in CASES:
        if tag not in summ:
            continue
        e = summ[tag]
        z = e['Z244']
        er, et = e['eta_rad'][1], e['eta_tot'][1]
        print(f"| {label} | {e['f_min']/1e9:.3f}, {e['s11_min']:.1f} | {e['s11_244']:.1f} dB | "
              f"{e['s11_band_worst']:.1f} dB | {z[0]:.0f} {'+' if z[1] >= 0 else '-'} j{abs(z[1]):.0f} | "
              f"{100*er:.0f} % ({10*np.log10(er):.1f} dB) | {100*et:.0f} % ({10*np.log10(et):.1f} dB) |")
    plots(data, summ)


def plots(data, summ):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cols = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7']
    dashes = ['-', '--', '-.', '-', '--', ':', '-.']
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': '#999999', 'axes.linewidth': 0.6,
                         'xtick.color': '#555555', 'ytick.color': '#555555'})
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=130)
    ax.axvspan(2.40, 2.4835, color='#eeeeee', lw=0)
    ax.axhline(-10, color='#bbbbbb', lw=0.8)
    for k, (tag, label) in enumerate(CASES):
        if tag not in data:
            continue
        d = data[tag]
        s11 = 20 * np.log10(np.abs(gamma(d['Z'])))
        ax.plot(d['f'] / 1e9, s11, dashes[k], color=cols[k], lw=2, label=label)
    ax.set_xlim(2.2, 2.7)
    ax.set_xlabel('Frequency (GHz)')
    ax.set_ylabel('|S11| at antenna feed (dB, 50 ohm)')
    ax.grid(color='#eeeeee', lw=0.6)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=7, frameon=False, loc='lower right')
    ax.text(2.442, ax.get_ylim()[1] - 1, 'BLE band', ha='center', va='top', fontsize=7, color='#555555')
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'antenna_s11.png'))
    plt.close(fig)

    # efficiency bars (total = radiated / available, at 2.44 GHz)
    tags = [t for t, _ in CASES if t in summ]
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=130)
    y = np.arange(len(tags))[::-1]
    tot = [summ[t]['eta_tot_db'][1] for t in tags]
    rad = [summ[t]['eta_rad_db'][1] for t in tags]
    ax.barh(y + 0.18, rad, height=0.34, color='#2a78d6', label='radiation efficiency (of accepted power)')
    ax.barh(y - 0.18, tot, height=0.34, color='#eb6834', label='total efficiency (incl. 50 ohm mismatch)')
    for yy, a, b in zip(y, rad, tot):
        ax.text(a - 0.15, yy + 0.18, f'{a:.1f}', va='center', ha='right', fontsize=7, color='#222222')
        ax.text(b - 0.15, yy - 0.18, f'{b:.1f}', va='center', ha='right', fontsize=7, color='#222222')
    ax.set_xlim(min(tot + rad) - 2.0, 0.3)
    ax.set_yticks(y)
    ax.set_yticklabels([dict(CASES)[t] for t in tags], fontsize=7)
    ax.set_xlabel('Efficiency at 2.44 GHz (dB)')
    ax.axvline(0, color='#999999', lw=0.6)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=7, frameon=False, loc='lower left', bbox_to_anchor=(-0.6, 1.0), ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'antenna_efficiency.png'))
    plt.close(fig)


if __name__ == '__main__':
    main()
