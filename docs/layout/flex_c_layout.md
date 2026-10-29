# Electrode flex — REV C, medium

Native project and generators: `boards/neurband_c_flex/`. This is a **passive, two-layer polyimide flex**, not a rigid PCB. Eight pods, 24 fabricated electrodes, no purchased components or flex assembly BOM. Other boards, mechanical files and their generators are not changed.

## Dimensions and coordinate frame

X follows the wrist; +Y is distal along the forearm. Origin is the tail centreline at the middle-electrode Y coordinate. The native KiCad translation is **(+65, +35) mm**: add it to the coordinates below. In the supplied F-side plan view +X is right and +Y is down. F.Cu is skin-facing; B.Cu is outward-facing.

- One medium size: **18.0 mm pod pitch**, parameter `--pitch`.
- Pods: **7.1 × 30.0 mm**, Y = −15…+15; nominal 0.8 mm outside corner radius and 0.6 mm rounded bridge junctions. The requested 7.0 mm width is incompatible with a 6.5 mm copper pad plus 0.30 mm clearance on both sides. **Necessary dimensional deviation: 7.1 mm**, preserving the electrode size and edge clearance rather than silently relaxing DRC.
- All electrodes: round **6.5 mm copper / nominal exposed ENIG diameter**; P/B/N centres at Y = −10/0/+10 mm. P–N separation is 20 mm.
- **16 non-plated, 1.2 mm alignment holes**, two per pod, exactly on each pod centreline at **Y = −5 and +5 mm**. These sit in the gaps, not beyond the electrodes. Hole-to-pad nominal edge gap is 1.15 mm. Shell pins need their own fit/tolerance allowance; do not make a 1.2 mm printed pin a press-fit into a nominal 1.2 mm hole. The holes carry **no coverlay opening** on either side: they are drilled through both coverlays (signal traces run 0.20 mm from the hole edges, closer than the fab's 0.15 mm opening-to-trace rule would allow after its 0.1 mm opening expansion). The generator gives these NPTH pads copper layers only (`*.Cu`, for the 0.20 mm hole clearance), no `*.Mask`.
- Spine: **7.6 mm wide**, Y = −0.6…+7.0, with rounded shoulders. This keeps a direct bias bus through the middle electrodes and two paired signal banks around the +5 mm alignment holes, retaining **0.20 mm drilled-hole clearance**. It is narrower than the pods' 30 mm forearm length but intentionally not a full-width strip. Free spans between straight pod sides are 10.9 mm; corner fillets shorten the fully straight span.
- Tail centreline X = 0 lies **between pods 3 and 4**. It heads distal from Y = +15. Default `--tail-length 8.5` gives tip **Y = +23.5**, native KiCad Y = 58.5. The free bend starts beyond Y = +15; **only the last 3.7 mm is stiffened**, leaving **4.8 mm unstiffened**. These dimensions follow the mechanical owner's measured module interface.
- Measured saved outline: **133.100 × 38.500 mm**, native bounds X = 16.450…149.550, Y = 20.000…58.500. Outline polygon area **2458.210 mm²** before subtracting drilled holes; it has one closed, valid perimeter.
- Electrode-covered arc: 132.5 mm. The 133.1 mm overall strip leaves roughly **11.9…46.9 mm** for the closure/module/strap around a 145…180 mm wrist. This is a geometric allowance, not a completed shell/strap fit validation. Do not stretch the flex to accommodate wrist size.

### Electrode and alignment positions

Coordinates in mm, relative to the frame above. Each electrode symbol has pad 1. All B electrodes are **BIAS_E, never GND**.

| Pod | X | Proximal P | Middle B | Distal N | Alignment holes |
|---|---:|---|---|---|---|
| 1 | −45 | E1P (−45, −10) | E1B (−45, 0) | E1N (−45, +10) | (−45, −5), (−45, +5) |
| 2 | −27 | E2P (−27, −10) | E2B (−27, 0) | E2N (−27, +10) | (−27, −5), (−27, +5) |
| 3 | −9 | E3P (−9, −10) | E3B (−9, 0) | E3N (−9, +10) | (−9, −5), (−9, +5) |
| 4 | +9 | E4P (+9, −10) | E4B (+9, 0) | E4N (+9, +10) | (+9, −5), (+9, +5) |
| 5 | +27 | E5P (+27, −10) | E5B (+27, 0) | E5N (+27, +10) | (+27, −5), (+27, +5) |
| 6 | +45 | E6P (+45, −10) | E6B (+45, 0) | E6N (+45, +10) | (+45, −5), (+45, +5) |
| 7 | +63 | E7P (+63, −10) | E7B (+63, 0) | E7N (+63, +10) | (+63, −5), (+63, +5) |
| 8 | +81 | E8P (+81, −10) | E8B (+81, 0) | E8N (+81, +10) | (+81, −5), (+81, +5) |

## Tail interface and pinout

Mates to **XUNPU FPC-05F-20PH20**, 20 contacts, 0.50 mm pitch, bottom contact, 0.30 mm cable, flip lock; the fab's stock number C2856803. Source: manufacturer's `FPC-05F-NPH20`, `FPC 0.5PH H2.0`, REV A drawing, sheet 1/1, specifically its **RECOMMENDED FPC/FFC DIMENSION**, not the PCB solder-land drawing. [Connector drawing](https://datasheet.lcsc.com/datasheet/pdf/3a5d0ddaf61b312ec7a8c470eadfb5fe.pdf?productCode=C2856803); [exact-part datasheet entry](https://www.lcsc.com/datasheet/C2856803.pdf).

| Cable feature | Drawing / implementation |
|---|---|
| Tab width | (N+1) × 0.50 = **10.50 ±0.03 mm** |
| Outer contact-centre span | (N−1) × 0.50 = **9.50 ±0.03 mm** |
| Contact pitch | **0.50 mm** |
| Outer contact centre to tab edge | **0.50 ±0.03 mm** |
| Finger width | **0.30 ±0.03 mm** |
| Exposed length | Drawing **3.00 mm minimum**; artwork **3.20 mm** |
| Artwork finger extent | Y = tip−3.50…tip−0.30; centre Y = tip−1.90 |
| Copper to cable tip / side edge | **0.30 / 0.35 mm** nominal |
| Leading corners | Nominal **R0.30 mm** |
| Finished mating thickness | **0.30 ±0.03 mm**, complete laminated stack |
| End region / stiffener | Drawing depicts a **6.00 mm** end-region sketch; the measured module interface explicitly uses **3.70 mm F-side PI**, covering the inserted part plus 0.20 mm. This mechanical integration choice is not an insertion-depth dimension taken from the drawing; qualify retention/flatness on the first sample. |

There is one common **B-side coverlay opening** over the fingers. No solder paste apertures, no solder on fingers. J1 intentionally allows solder-mask bridges because the contact window is continuous. Individual copper clearances remain checked. The drawing does not specify a separate insertion-depth dimension; do not equate the 3 mm exposed length or 6 mm end region with insertion depth.

| Pin | Net | Pin | Net |
|---:|---|---:|---|
| 1 | GND | 11 | E5P |
| 2 | BIAS_E | 12 | E5N |
| 3 | E1P | 13 | E6P |
| 4 | E1N | 14 | E6N |
| 5 | E2P | 15 | E7P |
| 6 | E2N | 16 | E7N |
| 7 | E3P | 17 | E8P |
| 8 | E3N | 18 | E8N |
| 9 | E4P | 19 | BIAS_E |
| 10 | E4N | 20 | GND |

The schematic/netlist map matches `boards/neurband_c/gen_c_sch.py` J1_MAP. Signals are E1P/E1N…E8P/E8N, not zero-padded REV B names. Pins 2 and 19 join the same bias bus; pins 1 and 20 join the covered shield/return. These contacts are fabricated features, not fictitious BOM parts with invented MPNs.

### Fold and pin-1 rule

**Exposed fingers are B.Cu, opposite the skin electrodes. The PI stiffener is F-side, on the skin face.** The tail leaves distally, U-turns 180° up the module's distal wall, then enters the bottom-contact J1 heading proximally. At insertion the exposed B fingers must face the mating PCB's contacts. Keep the stiffener out of the bend. Use a smooth U, not a crease or an axial twist.

Physical **pin 1 is X = +4.75 mm**, pin 20 is X = −4.75. Finger position is `X(n) = (10.5 − n) × 0.50 mm`; the electrical `J1.n → net` map is unchanged. In the skin-side/F view with the distal tip **down**, pin 1 is **right**; in the outer/B contact-face view with the tip **down**, pin 1 is **left**. Native J1.1 is (69.75, 56.60) mm and J1.20 is (60.25, 56.60) mm at the default tail length.

World frame: X around the wrist, Y distal, Z away from skin. Main board TOP faces +Z; its top view has distal down-screen and **+x_board = −X_world**. Main J1 is centred at x_board = 14 mm, with pin 1 at 9.25 and pin 20 at 18.75, hence `X_world(pin 1) = 14 − 9.25 = +4.75 mm`. The flex F/skin view looks from −Z, so **+x_flex = +X_world**. The distal-wall U-turn is a rotation about X_world: **X is preserved**, while travel reverses from +Y to −Y and the B contact-face normal flips down toward the main PCB. Therefore flex pin 1 must also be at **+4.75 mm**, not −4.75. This is a face/view transform, not a pin-map reversal.

```text
F-side flex plan, distal down-screen (looking from -Z_world):

   -X_world                                      +X_world
   pin 20 ... 19 ... [20 x 0.50 mm fingers] ... 2 ... pin 1
                            |
                            v  +Y_world, distal tail before folding

Side view of installed U-turn (+X_world out of page; not to scale):

  +Z_world ^
           |   main TOP / J1  <================\
           |   [ main PCB ]                   |  distal module wall
           |   flex strip   =================>/
           +--------------------------------------> +Y_world, distal

The +X edge carries pin 1 throughout; no axial twist.
```

Maintain **flex J1.1 → main J1.1** through the U-turn. Mirroring the artwork's physical finger order corrected the earlier negative-X pin-1 checkpoint; the schematic pinout was not changed. Qualify continuity on the first physical sample.

The **8.5 mm** tail has **4.8 mm unstiffened** between strip edge Y = +15 and stiffener start Y = +19.8. A nominal **R1.0 mm** semicircle consumes about 3.14 mm of developed length, leaving about 1.66 mm for straight portions; the final 3.7 mm stiffener spans Y = +19.8…+23.5 and stays outside the bend. These are the mechanical owner's integration dimensions, not a repeated-flex hinge rating.

The main-board owner confirms a **local XUNPU J1 footprint on TOP**, mouth at distal board y = 27 mm, tail insertion travelling proximally (−y). The old Hirose assignment is superseded on the main-board side. No main-board file is modified by this flex task.

### Pod under the main-board antenna: pod 4

**Flex pod 4 (E4P/E4B/E4N, ADS1298 channel 4) lies under the main board's printed antenna, not pod 3.** This follows only from F facing the skin and the tail leaving distally, not from the pin map:

- Flex: KiCad F view is seen from −Z_world with the tail toward +Y_world, so **X_world = x_flex − 65** (native), Y_world = y_flex − 35.
- Main board: TOP faces +Z_world with KiCad +y distal, so **X_world = 14 − x_board**, and the shared distal edges give **Y_world = y_board − 12.2** (board distal edge at module Y = −14.8, strip distal edge at −15).
- `mech/rev_c/module.py` uses its own module frame (X radial +, distal = −Y, Z up; right forearm palm down) and places the board without mirroring, `X_mech = x_board − 14`. So **X_mech = −X_world** and the ulnar side is +X_world.
- Radiator AE1, KiCad x 0.75…6.15, y 12.15…26.55 → X_world **+7.85…+13.25**, Y_world −0.05…+14.35. Pod 4 is at X_world +9 (pod 3 at −9). The rectangular overlap of pod 4 with the all-layer keepout (x 0…5.65, y 11.65…27) is **64.47 mm²**; nothing of pod 3 is under it.
- Cross-check: flex J1.1 at x_flex +4.75 → x_board 14 − 4.75 = 9.25 = main J1.1.

Under the radiator, read from the saved board: **E4N** fully and most of **E4B (BIAS_E)**, the pod-4 alignment hole at (+9, +5), pod 4's B-side GND hatch, and on F.Cu the BIAS_E bus, the E4N lead and the spine trunk pairs of pods 5–8 (E5P/N…E8P/N) between Y = −0.6 and +7. E4P (Y = −10) is outside. There are no vias under it.

`mech/rev_c/fit.py`, `docs/mech/mechanical_c.md`, `docs/science/antenna_sim.md` and the preorder reviews call this pod "pod 3": the mechanical model numbers its pods in the mirrored order (pods 1–2 at −X_mech, 5–8 at +X_mech). The real flex has pods 1–2 at +X_mech (radial on a right forearm) and 5–8 at −X_mech (ulnar). The RF and analog conclusions hold for whichever pod is there; only the channel name changes.

## Routing, coverlay and shielding

- Signal trunks are explicit **P/N pairs**, **0.10 mm track / 0.10 mm gap**, remaining on F.Cu across wrist links. The two banks straddle the alignment holes; this is why minimum-rule copper is used instead of 0.127 mm. These low-frequency electrode pairs are not controlled-impedance or length-matched transmission lines.
- BIAS_E: one **0.20 mm F.Cu bus** through the middle contacts.
- Covered B.Cu signal underpasses and vias are confined to pod columns and the housing-captured root; root crossovers may also use supported pods 3 and 4. The paired tail leads transition to B.Cu inside that root and run on B.Cu all the way to the fingers; **no vias in the free tail beyond Y = +15**. P underpasses use pod gaps; N leaves its pad on F.Cu. Electrode circles are kept free of vias.
- Vias: **0.55 mm diameter / 0.30 mm plated drill**, 0.125 mm nominal annular ring, tented both sides. The saved layout contains **60 vias**, all with 0.30 mm drills; the project minima and default via geometry match. These replace the previous 62 smaller-drill vias to avoid requiring the fab's small-drill process class.
- Minimum copper/edge: **0.30 mm everywhere**, including the mating tab; no local edge exception. Drilled-hole clearance: **0.20 mm**. The `.kicad_dru` file explicitly enforces track, gap, edge and drilled-hole minima.
- B-side GND shield: **0.20 mm hatch / 0.80 mm hatch gap / 45°** on each pod and available root/tail area. **No hatched shield across the free wrist bridges**: just one 0.10 mm B-side GND return conductor there, to reduce bending stiffness. The return takes pod-local F-side underpasses around the signal crossings. No exposed GND skin contact.
- KiCad removes isolated zone islands. Verification measures actual filled GND in a 6 × 28 mm window at all eight pods: **61.735…62.728 mm²** per window in this build. This detects missing shield fill, not electromagnetic shielding performance.
- Skin-side coverlay opens only at the 24 round pads (not at the alignment holes, which are drilled through it). The outer coverlay opens at the B-side fingers, not at the shield. Gold electrode pads remain round and solderable. The F.Fab note permits **2–3 cheap SMD spring pins with 2 mm heads per pad**; these are optional and not installed or priced in this flex. Qualify soldering support, pin travel, pressure and skin compatibility separately.
- Silkscreen manufacturing correction: all **21 F/B labels use 0.15 mm strokes at 0.80 mm text height**. The generator also clamps any silkscreen line stroke to at least 0.15 mm; non-silkscreen strokes are unchanged. Regeneration passes DRC/parity with no pad/edge clearance violations, and the top/bottom renders were inspected for legibility. All non-silkscreen native content is unchanged; fabrication features remain **133.1 × 38.5 mm / 0.30 mm minimum plated drill**. Measurement: `build/silkscreen-stroke-check.json`.

### Via cost check

The **0.30 mm drill / 0.55 mm pad** regeneration passes with **zero DRC violations, zero unconnected items and zero schematic-parity differences**; no 0.25 mm fallback was needed. Only trace/via locations and via dimensions changed: pod-local signal escapes moved to X offsets ±2.45 mm and ground returns to ±2.95 mm. The local router checks actual via-to-track/pad/edge geometry rather than conservatively eroding the routing grid. The outline and every electrode, finger and alignment-hole footprint are byte-equivalent after removing UUID metadata, verified by semantic SHA-256 `882a55eafaa834e94904bce4d45f36ec0c91a74edca7611347616278dc880a78`; all tail dimensions and pin-1 orientation are unchanged. `build/via-cost-check.json` records the measurements. The previous 0.20 mm version is kept only as a backup in `build/via-cost-baseline_0p2/`, not as the active design. This removes the small-drill requirement; the exact price still comes from the fab's quote.

## Fab instructions

Order through the fab's **flex** service as **polyimide flex, two copper layers, rolled-annealed copper if the fab lets you choose it, coverlay both sides, ENIG 2 µ" on the exposed electrodes and fingers, finished ~0.11 mm**; the full settings and paste-in notes are in `boards/neurband_c_flex/ORDERING.md`. Nominal bend stack in the KiCad board (the fab's nearest two-layer build is 0.11 mm):

| Layer | Thickness, mm |
|---|---:|
| F-side PI coverlay + adhesive | 0.025 |
| F.Cu | 0.012 |
| Polyimide core | 0.025 |
| B.Cu | 0.012 |
| B-side PI coverlay + adhesive | 0.025 |
| **Total flexible stack** | **0.099** |

**F-side PI stiffener** over only the final **10.50 × 3.70 mm** tail region, **Y = +19.8…+23.5** at the default 8.5 mm tail. `User.2` (Gerber `User_2`) is the stiffener layer and must be sent and named as such. Specify **0.30 ±0.03 mm finished total at the fingers**, not a 0.30 mm stiffener added on top. At the fingers the B coverlay is opened and there is no F copper, so the stack there is 0.11 − 0.0275 − 0.012 ≈ 0.071 mm and the stiffener is **0.225 mm PI** (≈0.296 mm total), not the ≈0.201 mm obtained by subtracting the whole 0.099 mm stack. Do not stiffen the 4.8 mm free tail or wrist links. Keep pod-local vias within supported shells and capture the root before its R1 U-turn.

`neurband_c_flex.fab.json` is marked `"order": false`: the rigid-board order flow cannot describe a flex, and its **0.4 mm thickness is only a placeholder**. It is not the flex stack or the connector tongue thickness: **do not fabricate a 0.4 mm rigid PCB, a 0.4 mm flex stack, or a 0.4 mm mating tongue**. The generator refreshes only that file's measured features and keeps its order flag and note. Confirm the flex stack, coverlay registration, tab tolerances, plated drill capability and stiffener thickness with the fab. ENIG is a prototype contact finish; assess wear, cleaning and skin exposure before prolonged use. Green in the KiCad renders is visualization, not a coverlay material/colour prescription. The native 3D rendering shows the 0.099 mm flat flex and copper, not the added stiffener or installed U-bend.

The fit-check STEP is `boards/neurband_c_flex/neurband_c_flex.step`, exported by KiCad with `--board-only --user-origin 65x35mm`. FreeCAD validates one solid, **133.1 × 38.5 × 0.025 mm**: KiCad's board-only STEP exports the **polyimide core**, excluding copper and coverlay. The real flexible laminate is **0.099 mm**, so the mechanical assembly must allow that complete stack, not the STEP core thickness. The STEP includes alignment holes but no spring pins, stiffener or U-bend. STEP X equals the relative X table; STEP Y = −(table Y), with the tail toward negative STEP Y. Its bounds are X = −48.55…84.55, Y = −23.5…15, Z = 0…0.025 mm; +Z is the F/skin face. To place it in the `mech/rev_c` module frame (X radial, distal = −Y, Z up), rotate it 180° about Y: X_mech = −X_step, Y_mech = Y_step, Z_mech = −Z_step, which puts the tail distal and pod 4 at X_mech = −9 under the antenna. Do not infer a 0.30 mm stiffened tongue from this bare-core STEP.

## Regeneration and verification

From the project root:

```sh
uv venv boards/neurband_c_flex/.venv
uv pip install --python boards/neurband_c_flex/.venv/bin/python -r boards/neurband_c_flex/requirements.txt
boards/neurband_c_flex/.venv/bin/python boards/neurband_c_flex/gen_flex_c_sch.py
kicad-cli sch export netlist --format kicadsexpr \
  -o boards/neurband_c_flex/neurband_c_flex.net boards/neurband_c_flex/neurband_c_flex.kicad_sch
boards/neurband_c_flex/.venv/bin/python boards/neurband_c_flex/gen_flex_c_pcb.py --verify --render --step
kicad-cli sch erc --format json \
  -o boards/neurband_c_flex/build/neurband_c_flex-erc.json boards/neurband_c_flex/neurband_c_flex.kicad_sch
```

Optional geometry switches: `--pitch 18 --tail-length 8.5`; only one output size/project is produced. `STIFFENER_LENGTH = 3.7` is a named generator parameter. Keep the generated `.kicad_pro`, `.kicad_dru`, `fp-lib-table` and `neurband_c_flex.pretty` beside the board. Python dependencies include **pyclipper**, NumPy, Shapely and a pinned official KiCad Library Tools commit; use the supplied isolated environment, never `pcbnew`/SWIG. `rsvg-convert` is needed for PNG layer plots. No other board generator is imported at regeneration time.

The schematic generator is adapted from the existing electrode schematic generator and uses `tools/schgen.py`. The PCB generator reuses REV B's deterministic artwork/official-library-tool conventions and local root fanout algorithm, with explicit REV C pod/trunk geometry. Regeneration overwrites this flex's generated native board; do not regenerate over unsaved manual PCB edits. KiCad IPC board commands on the project-only headless server returned `unknown command`; generation therefore follows the archived no-SWIG file generator, followed by CLI refill/save and full DRC.

The saved board is regenerated with coverlay-covered alignment holes: all 16 NPTH pads use `*.Cu` without `*.Mask`. All 447 trace segments and 60 vias are geometrically identical to the pre-correction board; the 0.20 mm hole clearance and GND hatch are unchanged. Native refill/parity check: **0 DRC violations, 0 unconnected, 0 parity differences**.

Verification rejects **all DRC warnings/errors**, unconnected items, schematic-parity differences and missing pod shield fill. Accepted build: **0 DRC violations, 0 unconnected, 0 schematic-parity issues, 0 ERC violations**. Native measurements are in `build/geometry.json`, the DRC/ERC reports and filled-shield measurements in `build/`; current top/bottom copper PNGs, covered top/bottom 3D PNGs, isometric 3D PNG and schematic render are in `renders/` and were visually inspected. The native board and matching schematic retain the common project name `neurband_c_flex`.

Final fabrication-preview inspection (2026-10-29): macro-complete copper, coverlay, outline and User_2 Gerbers were rendered from `mfg/20261029_preorder/flex/gerbers/`. The F coverlay has only the 24 electrode openings; B has the finger window, with no alignment-hole coverlay openings. Final native DRC/refill/parity and ERC reports in `build/preorder_20261029/` contain zero issues.

Final polish (2026-10-29): User_2 now contains one **closed filled 10.50 × 3.70 mm rectangle**, board coordinates (59.75,54.80)..(70.25,58.50), plus its label. All 447 segments, 60 vias and J1 finger pads compare unchanged against the pre-polish save. Native DRC/refill/parity and ERC again report **0/0/0 and 0**. STEP, renders and the User_2 Gerber were refreshed; `order: false` is retained. Evidence: `boards/neurband_c_flex/build/preorder_20261029/polish/proof.json`.
