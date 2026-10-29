# Electrode flex layout — rev B

Source: `archive/neurband_electrodes_revB/gen_flex_pcb.py`. This is a passive, two-layer **polyimide flex**, not a rigid PCB. Main-board connector: **Hirose FH26W-39S-0.3SHW(60)** on the main board's bottom, skin-facing side. The old 40-contact, 0.5 mm interface is not compatible.

## Regeneration

```sh
uv venv archive/neurband_electrodes_revB/.venv
uv pip install --python archive/neurband_electrodes_revB/.venv/bin/python -r archive/neurband_electrodes_revB/requirements.txt
archive/neurband_electrodes_revB/.venv/bin/python archive/neurband_electrodes_revB/gen_flex_pcb.py --verify --render
```

Python 3.13+, pinned NumPy, **pyclipper 1.4.0**, and the official KiCad Library Tools are in `requirements.txt`. KiCad CLI 10.99.0-bp.4 refills/saves the boards and checks DRC. `rsvg-convert` converts the layer plots to PNG. `--sizes M` selects one size. `TAIL_LENGTH`, `STIFFENER_LENGTH`, and `PITCHES` are the geometry parameters.

The generator reads the generated schematic and netlist; it does not modify the schematic generator. M is `neurband_electrodes.kicad_pcb`; other boards have `_S`, `_L`, `_XL` suffixes. The M fabrication JSON is measured from the saved board. `.kicad_dru` files are generated alongside the projects and are required for the connector's local edge-clearance rule.

## Strip and sizes

PCB frame: F.Cu looking toward the skin contacts; X runs around the wrist, Y along the forearm. Tail centre X = 0 lies between pods 4 and 5. The distal strip edge is Y = +17; the tail points +Y. These axes are not a direct copy of the mechanical model's frame.

Each of 16 pods has P/B/N electrodes at Y = −10/0/+10 mm, diameter 6.5 mm. P/N separation is 20 mm. All middle electrodes connect to the driven bias net, not to GND. Pod pitches and electrode positions are unchanged from the mechanically refined layout.

| Size | Pod pitch, mm | Strip length, mm | Electrode-covered arc, mm | Overall height with 12 mm tail, mm |
|---|---:|---:|---:|---:|
| S | 8.6 | 139 | 135.5 | 46 |
| M | 9.5 | 152.5 | 149 | 46 |
| L | 10.8 | 172 | 168.5 | 46 |
| XL | 12.4 | 196 | 192.5 | 46 |

Strip length = `15 × pitch + 10`; covered arc = `15 × pitch + 6.5`. The strip is 34 mm wide. It is continuous, without slits: a narrow central bridge cannot carry the present paired trunk topology. Optional pod backings must not span the flexible links.

## FH26W cable termination

References: Hirose's [FH26 series catalog](https://www.hirose.com/product/document?documentid=D49355_en&documenttype=Catalog&lang=en&series=FH26), recommended FPC drawing and dimension table; [accessible catalog copy](https://media.digikey.com/pdf/Data%20Sheets/Hirose%20PDFs/FH26.pdf), printed page 4. The current connector drawing reviewed by the main-board owner is EDC3-323714-05, revision 2. The cable artwork follows the published FPC recommendation, not the connector's solder-land pattern.

- 39 contacts; 0.30 mm pitch; same-row pitch 0.60 mm.
- Cable insertion tab **12.00 ±0.05 mm**; outer contact-centre span **11.40 ±0.03 mm**; edge to outer odd contact centre **0.30 ±0.07 mm**.
- **Staggered contact heads**, not 39 full-length rectangular fingers. Odd contacts 1/3/…/39 have tip-side heads; even contacts 2/4/…/38 have the second-depth heads.
- Heads are 0.28 mm wide; necks are 0.10 mm. The drawing permits 0.27–0.34 mm heads and 0.08–0.12 mm necks. Request controlled 0.28 ±0.01 mm head width from the fab.
- Depth is measured back from the cable tip. Odd heads start at depth 0.30 and end at 0.95 mm, tapering to the neck by 1.15 mm. Even contacts widen from a neck at 0.95 to full head width at 1.15, remain broad to 2.10, then taper to the neck by 2.25 mm. Copper leads continue to depth 2.50 mm.
- The 0.95/1.15 mm transition lies within the drawing's 1.0 ±0.1 / 1.1 ±0.1 mm limits. Matching transition endpoints retain detail H's relative A/B alignment. The longer taper avoids the approximately 0.0707 mm diagonal gap produced by a nominal 0.3/0.1 mm, 45-degree transition. Designed minimum transition gap is approximately **0.1003 mm**.
- One common F-side coverlay window exposes the terminal to depth 2.50 mm. J1 explicitly carries KiCad's `allow_soldermask_bridges` footprint attribute: a continuous coverlay opening is intentional for these mechanical contacts, which receive no solder or paste. Other footprints keep ordinary mask-bridge checking, and copper spacing remains checked everywhere. No B-side copper is exposed. The 0.10 mm rectangular custom-pad anchor is not the contact-head size. The final track approaches each neck vertically to avoid an acute copper sliver.
- B-side PI stiffener extends **3.50 mm** back from the tip, matching the catalog minimum. Finished insertion thickness, including copper, coverlay, stiffener and adhesive: **0.20 ±0.03 mm**.

### Fabrication capability

The fab publishes a flex capability of 3/3 mil (0.0762/0.0762 mm) with 12 µm copper, and 3.5/3.5 mil with 18 µm copper. The nominal 0.10 mm necks and ≥0.1003 mm terminal spacing are within that normal flex feature class; a 0.3 mm connector pitch alone does not require HDI. **The dimensional tolerances still require fab confirmation**: contact-head etch width, adjacent-pitch accuracy, A/B registration, tab outline and finished thickness must all be maintained together. Nominal CAD clearance is not a worst-case tolerance guarantee.

The cable drawing necessarily places the outer heads about 0.16 mm from the tab edge. A named insertion-tab rule allows 0.15 mm edge clearance only for non-zone items intersecting that terminal area. Other copper, including the shield zones, retains the 0.30 mm edge requirement. This is a documented connector geometry constraint, not a waived DRC violation.

## Tail and fold

- `TAIL_LENGTH = 12.0 mm`, measured from Y = 17 to tip Y = 29. Body width is 14 mm; the last 4 mm narrows to the 12 mm insertion tab.
- Stiffener starts at Y = 25.5, leaving **8.5 mm unstiffened**.
- The tail has no signal-layer changes: signal and bias leads fan in on F.Cu; B.Cu remains a covered hatched shield. Via banks and searched crossovers stay inside the captured strip root, below Y = 17.
- Form an **uncreased U-bend**, not the old two-bend riser into a top-side connector. A 180-degree R1.5 mm bend consumes approximately 4.71 mm of developed length; 12 mm is the integration target, not a substitute for a final housing fit check. Do not put the stiffener into the bend or clamp a via into an active bend.
- FH26W bottom contacts face the mounting PCB. With J2 on the main board's underside, the exposed F.Cu contacts must face **toward the main PCB** at insertion. The U-turn reverses the original skin-facing surface; do not add an axial twist.
- Pin 1 is at negative X (left when viewing the F.Cu artwork with the tip pointing +Y). Keep pin 1 connected to main-board J2 pin 1; reverse neither the net map nor the cable laterally. Pin 1 and pin 39 are marked on silk. Qualify orientation with continuity on the first physical sample.
- Current J2 origin is **(22, 2.1) mm** in the main board's top-view frame, on BOTTOM. Its mouth faces −Y; insertion is +Y. Pin 1 is **(16.3, 0.7)** and pin 39 **(27.7, 0.7)**. The mouth is near Y = 0.2; cable centre is X = 22, offset 6 mm from the 32 mm board's centre. Align the housing to that cable axis rather than assuming a centred connector. These coordinates are already top-view positions of bottom-side pads: do not mirror them again. See `docs/layout/main_board_layout.md`; the flex skin-side artwork and rigid-board top view are opposite viewing directions.

## Pin map

| Pin | Net | Pin | Net | Pin | Net | Pin | Net |
|---|---|---|---|---|---|---|---|
| 1 | GND | 11 | E04N | 21 | E09N | 31 | E14N |
| 2 | GND | 12 | E05P | 22 | E10P | 32 | E15P |
| 3 | BIAS_E | 13 | E05N | 23 | E10N | 33 | E15N |
| 4 | E01P | 14 | E06P | 24 | E11P | 34 | E16P |
| 5 | E01N | 15 | E06N | 25 | E11N | 35 | E16N |
| 6 | E02P | 16 | E07P | 26 | E12P | 36 | BIAS_E |
| 7 | E02N | 17 | E07N | 27 | E12N | 37 | GND |
| 8 | E03P | 18 | E08P | 28 | E13P | 38 | GND |
| 9 | E03N | 19 | E08N | 29 | E13N | 39 | GND |
| 10 | E04P | 20 | E09P | 30 | E14P | — | — |

Pin 40 has been removed. FPC fingers and electrode lands are fabricated copper, not purchased assembly components; no fictitious component MPNs are assigned.

## Stack and stiffeners

| Layer | Nominal thickness, mm |
|---|---:|
| Skin-side PI coverlay including adhesive | 0.025 |
| F.Cu, rolled-annealed copper | 0.012 |
| Polyimide core | 0.025 |
| B.Cu | 0.012 |
| Outer PI coverlay including adhesive | 0.025 |
| **Flexible stack total** | **0.099** |

Nominal added PI stiffener/adhesive thickness is 0.10 mm, giving about 0.199 mm at the terminal; the fab adjusts the stack to the required **0.20 ±0.03 mm finished thickness**. `User.2` marks its B-side extent. `User.1` marks optional 7 × 32 mm pod backings. These are drawings, not actual KiCad stiffener layers.

The fabrication JSON's 0.4 mm thickness option remains a quoting proxy. Order as **FLEX / polyimide / coverlay / stiffener**, separately quoted from a rigid board; never build a 0.4 mm rigid strip or a 0.4 mm connector tongue from that proxy.

## Routing and shield

- Paired circumferential P/N trunks: **0.10 mm width / 0.10 mm gap**. This minimum-rule bank frees the root space needed for the short, via-free tail; it replaces the previous 0.127/0.127 mm bank. Tail leads also use 0.10 mm tracks.
- BIAS_E is one 0.20 mm F.Cu bus. It is separate from the covered GND return at Y = 4.5.
- Pod-local B.Cu underpasses remain on each pod column between Y = −6.1 and +6.1. Their vias are not in circumferential bend links.
- Tail fan-in uses a staggered root via bank at Y = 16.3/16.6, 0.47 mm lateral pitch. Crossovers are searched inside the static root. The housing must capture X = ±15 mm there; do not treat it as a free-bending hinge.
- Via pads/drills: 0.45/0.20 mm; 0.125 mm annular rings. Vias are covered on both sides. The 0.20 mm drill may cost more than a standard larger drill.
- B.Cu GND shield: 0.20 mm hatch lines / 0.80 mm gap / 45 degrees. Every pod has an F.Cu GND return and shield via; pod 5 on S has a second return for its partitioned shield.
- S retains separate 7 mm pod shields outside the captured root; a continuous root shield joins them inside X = ±15. Free links outside that region have no B.Cu signal copper. Other sizes retain the continuous strip shield.
- Skin coverlay opens only for the 48 electrode contacts and the terminal window. The shield is never an exposed skin electrode.

## Verification and outputs

`--verify` rejects every DRC violation (warnings included), unconnected item and schematic-parity discrepancy. It also measures actual filled GND copper in a 6 × 30 mm review window at every pod and rejects any window below 10 mm². DRC alone can miss a shield island deleted by the zone filler. This is a gross-loss check, not an electromagnetic shielding specification.

Reports and measurements are under `archive/neurband_electrodes_revB/build/`. Top/bottom copper PNGs for all four sizes, plus M's covered skin/outer 3D views, are under `renders/`. The 3D viewer's green is a visualization, not a colour/material prescription. Current native files, projects, custom rules, `neurband.pretty`, pinned dependencies and generator are all in the electrode-board folder. The clean previous 40-contact checkpoint is archived under `build/rev-a-16mm/`, not used by rev B.

ENIG is suitable for prototype evaluation but its thin gold wears. Confirm skin compatibility, hard-gold alternatives, cleaning and optional dome/pogo attachment before prolonged use. This is a passive high-impedance interconnect, not Meta's per-pod amplified architecture: bench-test noise and motion artefacts.

No main-board layout, schematic generator or mechanical CAD is modified by this task.
