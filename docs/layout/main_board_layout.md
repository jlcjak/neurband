# Main board rev B layout

Canonical PCB: `archive/neurband_main_revB/neurband_main.kicad_pcb`. Coordinates below are millimetres in the **top view**, +X right, +Y down. Bottom-side coordinates are still expressed in that same top-view frame; do not mirror them a second time.

## Outline and assembly

The saved native board measures **32.0000 × 26.0000 mm**, Edge.Cuts X=0…32, Y=0…26, with four R1 corners. Native outline area is 831.138 mm². This is a 54.7% reduction in bounding-box area from rev A's 54 × 34 mm. No mounting holes: the housing must clamp/support the rigid PCB at its edges on coplanar seats, not bend it against the wrist curve.

Four copper layers: F.Cu, In1.Cu, In2.Cu, B.Cu. Two-sided assembly. In1.Cu is reserved for the GND plane, with no signal tracks; F.Cu/B.Cu carry component-local routing and In2.Cu carries crossovers. The current native thickness is **1.6 mm**, retained from rev A; 1.0 mm is the requested preference, not the thickness currently saved. Do not design the housing slot or fabrication order around 1.0 mm until the native construction is changed and re-exported.

Minimum routed width is 0.10 mm, clearance rule 0.10 mm, copper-to-edge 0.30 mm. Compact fine-pitch escapes use ordinary **0.20 mm drill / 0.45 mm copper through-vias**. This is a cost tradeoff relative to rev A's 0.30/0.55 mm vias, not a microvia/HDI requirement. The fabrication fields must be regenerated from the final saved board statistics.

## Mechanical interfaces

| Part | Side / origin / KiCad rotation | Housing interface |
|---|---|---|
| U1 ESP32-C3-MINI-1-N4 | TOP, (5.6,13.1), 90° | Antenna points −X and overhangs the left edge by 5.4 mm |
| U2 ADS1298, channels 1–8 | TOP, (23,15.15), −90° | 10 × 10 mm body; local references, VCAP and supply bypass on TOP |
| U3 ADS1298, channels 9–16 | BOTTOM, (23,15.15), −90° after native mirror | Stacked directly beneath U2; its own bypass/reference capacitors on BOTTOM |
| J2 FH26W-39S-0.3SHW(60) | BOTTOM, **(22,2.1), 270° after native mirror** | Opening faces **−Y**, insertion is **+Y**; deliberately offset right, not board-centred |
| J1 JST-SH battery | TOP, **(28.6,2.75), 90°** | Right edge, opposite the antenna; cable exits **+X** |
| U4 AP2112K-3.3 | TOP, (7.8,23), 0° | Digital/radio regulator |
| U5 LP5907-3.0 | BOTTOM, (6,21.8), 0° | Analog regulator; +3V0 feeds ADS AVDD, not DVDD |
| TP1–TP9 | BOTTOM, Y=24.8; X=6.20 + 1.27(n−1) | Rear-edge 1.27 mm-pitch pogo row; reserve clip access with the electrode band unplugged |

RN1–RN4 are TOP; RN5–RN8 are BOTTOM. These 4×0402 arrays are staggered to preserve the stock 0.25 mm courtyards while aligning all four output pads exactly with their ADC input X coordinates. TOP centres: RN1 (20,5.45), RN2 (22,7.5), RN3 (24,5.45), RN4 (26,7.5). BOTTOM: RN5 (26,5.45), RN6 (24,7.5), RN7 (22,5.45), RN8 (20,7.5). All use native KiCad angle 90°. The 32 post-resistor paths are straight, same-side, 0.127 mm copper with no vias; each P/N pair has equal post-resistor length.

### J2: exact cable orientation

Verified transform from stock-footprint local coordinates to the board top view:

`global X = 22 + local Y; global Y = 2.1 + local X`.

- **Pin 1 is at the left end**, (16.3,0.7); pin 39 is (27.7,0.7).
- Pin 2 is (16.6,3.575); pin 38 is (27.4,3.575).
- Retention pads are (15.6,0.975), (28.4,0.975).
- Nominal body/F.Fab envelope: **X=15.4…28.6, Y=0.2…3.45**. Mouth/front is near Y=0.2.
- Courtyard: X=14.9…29.1, Y=−0.55…4.4. The intentional courtyard overhang is cable/actuator access, not a copper overhang.
- Bottom contact: the exposed flex conductors face the connector's mounting PCB surface—**toward the main board**, not away from it. Tail stiffener is on the opposite face. Confirm the complete folded cable's pin-1 continuity on the first article before skin contact.
- FPC width **12.0 ±0.05 mm**, total reinforced mating thickness **0.20 ±0.03 mm**, including adhesive/stiffener. Use the specified staggered/interdigitated fingers, not 39 uniform rectangular fingers.
- Closed connector height **1.0 ±0.1 mm**. Open reference 1.9 mm at 135°; actuator sweep reference **2.3 mm at 90°**. Reserve at least that operating volume plus tolerance and finger/tool access.

The verified stock FH26 copper land pattern is compatible with FH26W. The stock paste apertures equal the copper; the assembly stencil must instead follow Hirose's drawing: 0.1 mm stencil, 0.23 × 0.65 mm odd apertures, 0.23 × 0.55 mm even apertures, 0.9 × 0.3 mm retention apertures, including the drawing's odd-aperture offset. See [connector review](../../archive/neurband_main_revB/layout/FH26W-review.md). No electrode-flex files were changed by this layout work.

### Antenna, battery and height allowances

U1's nominal module envelope is **X=−5.4…11.2, Y=6.5…19.7**, height 2.4 mm above TOP. The PCB-plus-module bounding envelope is therefore **37.4 × 26 mm**, not merely the 32 mm PCB length. The all-layer antenna keepout is X=−20.4…0, Y=−8.5…34.7; it is outside the board. Keep the cell, leads, fasteners and enclosure metal out of this external RF volume. The antenna-overhang part is not mechanically supported by the PCB.

The 402030 LiPo remains above the board's non-antenna region. Its nominal 30 × 20 × 4 mm dimensions do not include swelling, protection circuit, insulation, lead bend or assembly tolerance. Support/insulate it above components and do not let it load U1's shield or cover the antenna. RF performance with the installed cell/housing remains a bench measurement.

Height planning, measured from each PCB surface:

- **TOP maximum installed-model height: 2.96 mm at J1**, from the rev A stock-model measurement; U1 is 2.4 mm. Use a top component allowance of at least 3.1 mm before insulation/battery, rather than interpreting a model measurement as a guaranteed component tolerance.
- **BOTTOM maximum component package height: 1.45 mm**, the LP5907 SOT-23-5 DBV package, confirmed in [TI's package drawing](https://www.ti.com/lit/ds/symlink/lp5907.pdf). ADS1298 TQFP allowance is 1.2 mm; J2 closed maximum is 1.1 mm. These package allowances are not measurements of an assembled sample.
- J2 actuation needs a separate **≥2.3 mm** bottom-side operating envelope, plus tolerance/access. Pogo clearance also needs an opening or removable cover; a flush wrist-contact surface cannot occupy the populated bottom component volume.

## Verification status

This is an active routing revision, **not manufacturing sign-off**. The most recently exercised native check before escape-protected rerouting found 37 unconnected items and zero schematic-parity issues. No clean final DRC or final render inspection is claimed here. Final connectivity, width/clearance, filled-plane continuity, silkscreen, heights/models and top/bottom/3D images must be reviewed against the final saved PCB before ordering.

## Reuse and rev A

Rev A is preserved under `archive/neurband_main_revA/`: 54 × 34 mm, four layers, 1.6 mm, top-only assembly, ESP32-S3 and the old 40-way connector. Rev B reuses its ADS supply/reference grouping, decoupling rationale, probe-pad convention and DRC limits, but not its one-sided placement or obsolete radio/connector footprints. The new C3 footprint has **53 unique electrical pin numbers / 61 physical pad objects**, including nine islands sharing GND pad 49; see [module review](../../archive/neurband_main_revB/layout/ESP32-C3-MINI-1-review.md).

Battery/wireless operation only while worn. No charger, programmer or grounded bench instrument may remain connected to skin-contact hardware. DRC does not establish electrical noise, bias-loop stability, radio coexistence or body-contact safety.
