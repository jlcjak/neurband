# REV C RF feed geometry and antenna exclusion

Calculated 2026-10-26. This is a **design-assumption calculation, not a fabricator-confirmed stackup or an RF sign-off**. No board or schematic was changed by this calculation.

## Layout decision

- Use **0.160 mm nominal finished copper width** for the uniform top-layer, soldermask-covered, post-matching 50 ohm feed on the assumed stack below.
- Keep unrelated top-layer copper, including GND pours, **at least 0.50 mm edge-to-edge from each side of that feed**. This is an explicit non-coplanar geometry choice, not an ordinary clearance-rule default. Keep the L2 GND reference continuous underneath. At this separation the calculated coplanar perturbation is approximately 0.1 ohm; a close pour at 0.10 mm is not equivalent.
- The existing 0.150 mm feed is **not grossly wrong**: 53.20 ohm bare / approximately 51.6 ohm with the specified mask. It is modestly narrower than the nominal covered 50 ohm solution. Do not change it to 0.20 mm: that is only 45.68 ohm even before mask loading.
- **Do not apply this microstrip result inside Nordic's ANT/C3/L1 matching section.** Nordic requires inner-layer copper exclusion directly below the matching circuitry. That short section is intentionally unreferenced, not a uniform 100 micrometre-height microstrip. Resume the solid L2 reference only after the matching section; the reference-plane transition and component pads are discontinuities requiring layout review/tuning, not lengths certified by this calculation.
- The rotated antenna's stock **15.50 x 5.95 mm courtyard** maps to **x = 0.30..6.25 mm, y = 11.50..27.00 mm**. The proposed x = 0..6.25 mm exclusion merely extends it to the left board edge; no larger speculative antenna rectangle is needed. Preserve explicit feed and ground-short connection tabs at its right side.

## Assumed cross-section

| Parameter | Assumed value |
|---|---:|
| Copper, each of F.Cu / L2 / L3 / B.Cu | 35 micrometres finished thickness |
| F.Cu bottom to L2 top, dielectric `h` | 100 micrometres |
| L2 to L3 dielectric | 640 micrometres |
| L3 to B.Cu dielectric | 100 micrometres |
| Total copper plus dielectrics / finished with mask | 0.980 mm / 1.000 mm |
| FR-4 relative permittivity `er` | 4.3 nominal |
| Soldermask thickness / relative permittivity | 10 micrometres / 3.3 |
| Reference conductor for uniform feed | Continuous L2 GND |

Here `h` is the clear dielectric spacing, **not** the overall board thickness, nor a copper-centre separation. The deeper layers do not set this microstrip impedance when L2 is solid. The result does not apply over L2 voids, slots, the Nordic matching exclusion, or the antenna exclusion. The mask calculation assumes 10 micrometres over the copper top, conformal side coating, and 10 micrometres over exposed laminate; a planarized mask fill is a different cross-section.

The fabricator must confirm actual pressed dielectric thickness, GHz design Dk, finished/plated outer copper thickness, etched width/trapezoid, and mask profile before an impedance-controlled order. A generic '1 mm, four-layer FR-4' service is not sufficient confirmation. For scale, at width 0.160 mm the bare Hammerstad result changes from 51.49 ohm to 48.43 / 54.33 ohm if `h` is 90 / 110 micrometres, or to 52.54 / 50.50 ohm if `er` is 4.1 / 4.5.

## Finite-thickness Hammerstad–Jensen calculation

Equations follow [Qucs, Single microstrip line, equations 11.4–11.6, 11.15–11.18 and 11.22–11.25](https://qucs.sourceforge.net/tech/node75.html). Use dimensionless `u = w/h` and `tau = t/h`; normalizing explicitly avoids the dimensional ambiguity in the rendered thickness-correction notation on that page.

```text
f(u) = 6 + (2*pi - 6) * exp(-(30.666/u)^0.7528)
Za(u) = eta0/(2*pi) * ln(f(u)/u + sqrt(1 + (2/u)^2))
eta0 = 376.730313668 ohm

a(u) = 1 + ln((u^4 + (u/52)^2)/(u^4 + 0.432))/49
         + ln(1 + (u/18.1)^3)/18.7
b(er) = 0.564 * ((er - 0.9)/(er + 3))^0.053
e0(u,er) = (er + 1)/2 + (er - 1)/2 * (1 + 10/u)^(-a(u)*b(er))

du1 = tau/pi * ln(1 + 4*e/(tau*coth(sqrt(6.517*u))^2))
dur = du1/2 * (1 + sech(sqrt(er - 1)))
u1 = u + du1
ur = u + dur

Z0_bare = Za(ur)/sqrt(e0(ur,er))
e_eff_finite = e0(ur,er) * (Za(u1)/Za(ur))^2
```

`du1` and `dur` are normalized width increments, not millimetres. For w = 0.150 mm, `u = 1.5`, `tau = 0.35`, `du1 = 0.3855114`, `dur = 0.2538178`; thus the mixed-media equivalent width is 0.1753818 mm. The finite-thickness effective permittivity is 2.99186 and bare impedance is **53.1994 ohm**. Ignoring copper thickness instead gives **58.1540 ohm**, a materially different answer.

| Finished width (mm) | Bare finite-thickness H–J Z0 (ohm) |
|---:|---:|
| 0.150 | 53.199 |
| 0.160 | 51.488 |
| 0.165 | 50.676 |
| 0.170 | 49.891 |
| 0.180 | 48.397 |
| 0.200 | 45.679 |

The solved **bare** 50 ohm width is **0.169293 mm**. It is not the final covered-trace recommendation.

### Wheeler thickness cross-check

Qucs equations 11.19–11.20 give an alternative finite-thickness correction:

```text
DeltaW1 = t/pi * ln(4*e / sqrt((t/h)^2 + (1/pi)/(w/t + 1.10)))
DeltaWr = DeltaW1/2 * (1 + 1/er)
Z_WheelerCorrection = Za((w + DeltaWr)/h)
                      / sqrt(e0((w + DeltaWr)/h, er))
```

This deliberately uses the same H–J zero-thickness core to isolate the **Wheeler width correction**, not a claim to have used Wheeler's complete original impedance fit (the Qucs text limits that older impedance approximation to alumina-like permittivities).

At 0.150 mm, `DeltaW1 = 0.0360881 mm`, `DeltaWr = 0.0222403 mm`, giving **53.7624 ohm**. At 0.160 mm it gives **52.0040 ohm**; the bare 50 ohm width is **0.172332 mm**. The independent thickness corrections agree within about 0.6 ohm here. Since `t/h = 0.35`, mask/shape-aware field calculation is preferable to pretending the thin-strip closed form is exact.

## Soldermask loading: electrostatic cross-section calculation

The bare Hammerstad formula has no soldermask layer. A separate two-dimensional quasi-TEM electrostatic calculation included the rectangular finite-thickness conductor and the specified stepped/conformal coating. It solved

```text
div(epsilon * grad(V)) = 0
V_trace = 1 V; V_ground = 0 V
C  = integral(epsilon * |grad(V)|^2 dA) / (1 V)^2
C0 = same geometry and conductors, with every dielectric replaced by vacuum
Z0 = 1 / (c * sqrt(C*C0))
```

The energy integral above gives capacitance directly (stored energy is half this integral). Calculation used first-order triangular finite elements on a structured, locally refined cross-section, a symmetry boundary at the trace centre, and remote grounded boundaries 3 mm laterally / 3 mm above the laminate. L2 was the grounded bottom boundary, 0.100 mm below the trace bottom. Near-conductor spacing was 1 micrometre; outer cells grew geometrically. The substrate was er = 4.3, mask er = 3.3, and remaining space air. This is a quasi-static numerical calculation, **not** a measured coupon, full-wave antenna simulation, or fab-approved impedance specification.

| Width (mm) | Bare FEM (ohm) | 10 micrometre mask FEM (ohm) |
|---:|---:|---:|
| 0.150 | 53.177 | 51.601 |
| 0.160 | 51.470 | 50.000 |

At 0.160 mm covered width, the 1 micrometre mesh gave `C0 = 37.316 pF/m` and `C = 119.265 pF/m`. Reducing local mesh spacing to 0.5 micrometre gave 50.016 ohm; moving the remote boundaries to 6 mm at 1 micrometre spacing gave 50.035 ohm. These calculation-sensitivity runs justify rounding to **about 50.0 ohm**, not promising manufacturing precision to hundredths of an ohm. Bare FEM also agrees with the H–J values above. The mask shifts the optimum width from approximately 0.169 mm bare to approximately **0.160 mm covered** for this assumed coating profile.

At 2.45 GHz, `h/lambda0` is approximately 0.00082, supporting the quasi-static cross-section approximation. Loss, roughness, pad transitions, material dispersion and real etched/mask profiles are not certified by it.

## Nearby top-layer GND: do not silently change to grounded coplanar

A same-layer pour adds capacitance and lowers impedance. It cannot be included by treating its clearance as an ordinary DRC-only number. To isolate the effect, the same finite-thickness FEM was run **without mask** at w = 0.160 mm with symmetric, grounded top copper starting at edge-to-edge gap `g` on each side:

| Top ground gap g (mm) | Bare calculated Z0 (ohm) | Change from no top ground |
|---:|---:|---:|
| No top ground | 51.470 | — |
| 0.100 | 46.829 | -4.641 |
| 0.200 | 50.243 | -1.227 |
| 0.500 | 51.361 | -0.109 |
| 1.000 | 51.459 | -0.011 |

These figures isolate coplanar loading; they are not the masked impedance table. Mask also lowers the feed impedance, so a 0.100 mm gap cannot be justified using the non-coplanar 0.160 mm prescription. Use **g >= 0.500 mm** to retain the approximately non-coplanar assumption; put ground stitching outside that corridor, not inside it. If a tighter gap is necessary, recalculate the actual covered grounded-coplanar geometry, including pad transitions and ground continuity, instead of reusing the present width as a 50 ohm claim. The antenna feed/ground tab and matching-component launches are local exceptions, not uniform transmission-line sections.

## Nordic matching-section boundary

The existing [nRF52832 reference-circuit research](../../../docs/research/nrf52832_refcircuit.md), section 4, transcribes Nordic Product Specification section 53.4–53.5: on multilayer boards use an **inner-layer keepout directly below the antenna matching circuitry** to reduce stray capacitance. C3 returns through VSS pin 31 rather than having its own direct via to the plane. Source PDF: [Nordic nRF52832 Product Specification v1.0, pp.541–543](https://cdn.sparkfun.com/datasheets/Wireless/Bluetooth/nRF52832_PS_v1.0.pdf); current [Nordic reference-circuit page](https://docs.nordicsemi.com/bundle/ps_nrf52832/page/ref_circuitry.html).

Thus L2 is solid under the **post-match feed**, but not under the ANT/C3/L1 matching footprint/traces. The 3.9 nH Nordic L1 series inductor and its immediate layout are not to be 'fixed' by filling L2 below them. Likewise, the antenna exclusion is not to be filled to restore a microstrip reference. Keep matching and antenna exclusions distinct from the ordinary referenced feed.

## TI antenna: actual geometry, keepout and rotated placement

Official source: [TI SWRA117D / AN043, Small Size 2.4 GHz PCB Antenna](https://www.ti.com/lit/an/swra117d/swra117d.pdf), especially page 4 Figure 3 / Table 1, page 6 ground-plane and enclosure sensitivity, and page 20 Table 6. Figure 3 was inspected as a rendered drawing, not only extracted PDF text. It shows the lower ground-plane boundary on the feed/short side, not ground extending underneath the meander.

Stock footprint inspected: [`RF_Antenna:Texas_SWRA117D_2.4GHz_Left`](https://gitlab.com/kicad/libraries/kicad-footprints/-/blob/master/RF_Antenna.pretty/Texas_SWRA117D_2.4GHz_Left.kicad_mod), installed in the KiCad 10 footprint library. It has a top copper polygon, 0.50 x 0.50 mm feed pad 1 at local (0,0), and a 0.90 x 0.50 mm short-to-ground through-hole pad 2 at local (2.10,0), drill 0.30 mm. **The stock footprint has no functional rule-area keepout**: its crossed Dwgs.User rectangle and courtyard are only drawings. Layout must enforce the exclusion explicitly on F.Cu, L2, L3 and B.Cu; the intentional antenna copper and its feed/short connections are exceptions, not arbitrary routing permission.

TI dimensions in millimetres:

| L1 | L2 | L3 | L4 | L5 | L6 | W1 | W2 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3.94 | 2.70 | 5.00 | 2.64 | 2.00 | 4.90 | 0.90 | 0.50 |

| D1 | D2 | D3 | D4 | D5 | D6 |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 0.30 | 0.30 | 0.50 | 1.40 | 1.70 |

TI quotes **15.2 x 5.7 mm** total antenna implementation space. The stock courtyard is slightly larger, **15.5 x 5.95 mm**, not a requirement for an invented still-larger keepout. The crossed radiator-only rectangle is **15.2 x 5.2 mm**; the difference in height comes from the feed/ground connection region.

For the parent's origin `(X0,Y0) = (5.90,14.70) mm`, rotation `90 degrees` in KiCad's coordinates:

```text
X = 5.90 + y_local
Y = 14.70 - x_local
```

| Stock feature | Local coordinates (mm) | Rotated global bounds / centre (mm) |
|---|---|---|
| Courtyard / F.Fab rectangle | x -12.30..3.20; y -5.60..0.35 | x 0.30..6.25; y 11.50..27.00 |
| Crossed Dwgs.User radiator area | x -12.15..3.05; y -5.45..-0.25 | x 0.45..5.65; y 11.65..26.85 |
| Radiator copper polygon bounds | x -11.85..2.55; y -5.15..0.25 | x 0.75..6.15; y 12.15..26.55 |
| Feed pad 1 | centre (0,0), size 0.50 x 0.50 | centre (5.90,14.70); x 5.65..6.15; y 14.45..14.95 |
| Ground-short pad 2 | centre (2.10,0), size 0.90 x 0.50 | centre (5.90,12.60); x 5.65..6.15; y 12.15..13.05 |

Therefore the proposed all-layer exclusion **x 0..6.25, y 11.50..27.00 mm contains the entire stock courtyard**, and extends only 0.30 mm farther toward the left edge. It is conservative relative to the stock drawing; do not enlarge it by guessing a module-antenna style 7 or 10 mm border.

However, a blanket ban on all copper across that entire rectangle would also isolate the intended shorting via and feed. Define the radiator exclusion on every copper layer while allowing the explicit feed/ground tabs on the connection side: the TI ground-plane boundary is local `y = -0.25`, i.e. **global x = 5.65 mm**, with ground on its larger-X side. In particular the shorting through-hole at (5.90,12.60) must have a real GND connection to the reference plane via a right-side tab, not sit isolated inside the exclusion. Pad 1 similarly needs its intentional feed connection from the right. Such tabs must not spread ground into the meander region x < 5.65 mm. If the larger courtyard rectangle is retained as the implementation keepout, carve only those deliberate connection exceptions rather than opening it to unrelated tracks/vias/pours.

TI recommends copying its antenna exactly and using the same substrate thickness/material as the reference design; it does **not** establish that this new 1.0 mm four-layer board, smaller ground plane, enclosure, nearby flex/battery or body loading will preserve the published match. Maintain copper-free radiator space on all layers, keep unrelated conductors/components away, and perform antenna impedance/tuning and radiated-performance measurements in the final assembly. The rectangle calculation confirms geometric containment, not antenna certification.
