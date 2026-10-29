# Main board rev C — saved preorder layout

Checked 2026-10-29. Canonical PCB: `boards/neurband_c/neurband_c.kicad_pcb`. SHA-256: `ff1ad4d21b00e9b893da6967b5471a5043ebf84c73a8b2679c2bac27fdfc35b6`.

**The full analog suite, including via lands, and native DRC gates pass.** The independent reviews accepted the earlier routing exceptions; the remaining polish limitations are recorded below. Complete measured evidence: `boards/neurband_c/layout/preorder_release.json`. Coordinates are mm, top view, origin at the upper-left outline corner, +Y down; raw position output uses −Y. The band uses nRF52832; the separate USB dongle uses nRF52840.

## Construction and frozen interfaces

28.7 × 27.0 mm, four R1 outline corners, nominal 1.0 mm, four copper layers, black mask and ENIG. All 59 assembled parts are on F.Cu. Ordinary through-vias remain 0.30 mm drill / 0.45 mm land; no small-drill, blind/buried, extra-layer or outline change. The measured manifest features are 28.7 × 27.0 / 0.30 mm.

| Stack, top to bottom | Thickness / material |
|---|---|
| Top mask | 0.010, Er 3.8 |
| F.Cu | 0.035 copper |
| Prepreg | 0.0994, FR4 3313, Er 4.1 |
| In1.Cu | 0.0152 copper, common GND |
| Core | 0.700 FR4, Er 4.4 |
| In2.Cu | 0.0152 copper |
| Prepreg | 0.0994, FR4 3313, Er 4.1 |
| B.Cu | 0.035 copper |
| Bottom mask | 0.010, Er 3.8 |

The copper-plus-dielectric sum is 0.9992 mm; KiCad includes the mask films and reports 1.0192 mm. Order the fab's nominal 1.0 mm **3313** construction explicitly. GND pour boundaries are inset 0.50 mm from the edge; minimum trace/gap remains 0.10 mm. This pour inset does not move the frozen pads or antenna.

| Frozen interface | Saved coordinates |
|---|---|
| J1 signal pin n | x = 9.25 + 0.5(n−1), y = 21.5925 |
| J2 VBAT / GND | (23.9,25.6) / (26.9,25.6), B side |
| J3 charge / GND | (14,6) / (14,9), B side |
| TP1–TP5 | x = 16.00 / 17.27 / 18.54 / 19.81 / 21.08, y = 25.7 |
| TP1–TP5 nets | +3V3 / SWDIO / SWDCLK / NRST / GND |
| SW1 / D1 | (24.8,25.1) / (2,1) |
| Bottom support exclusions | R1.5 at (1.6,1.6), (26.4,1.6), (1.6,25.4), (26.6,22.6) |

All listed pad centres compare with the isolated pre-layout baseline at **0 mm movement**. The nominal cell placement is x=10.5..22.5, y=−3.3..21.7 (x=11..23 was the placement-limit envelope); its 1.3 mm underside clearance is retained, with U2 reserved to 1.2 mm. J1 and SW1 remain outside that height envelope. J2 has no bottom components; retain bottom access for 30 AWG leads and the J2/SW1 corner exit.

## Power and quiet analog routing

C27 moved to (7.75,21.12), with a short 0.25 mm F.Cu link from U3 VOUT and a local GND return. Its courtyard fits the unoccupied corner above J1: J1's local courtyard is notched around the actual housing/land envelope; its lands, body model and actuator position did not move. C25 (10 µF 0603) is beside U4 BAT. C33 (1 µF) serves U2 AVDD1/AVSS1; C32 is beside RLDREF. VREFP/VCAP routing is on F.Cu, with C5 at the VCAP1 group. DVDD bypasses reach both ADS supply pin groups.

Power sections were widened to 0.25 mm where native clearance and input separation allowed; 0.10–0.20 mm bottlenecks remain. VBAT, SWDCLK and BIAS_E bottom crossings below the AFE inputs were lifted/reworked to restore the reference. The complete south/left VBAT trunk and two short C27 star branches remain constrained by the fixed layout. The independent review accepted the saved network: J2→U3 is 180 mΩ, C27→U3 VOUT 1.3 mΩ, and the shared +3V3 branch ≤26 mΩ.

RN1–RN4 are 10 kΩ. C6/C28 and C16/C25 are 10 µF 0603, 10 V. R9/R10 are 10 kΩ. C34 is the subsequently accepted **12 pF C0G** BIAS_E shunt (the initial 22 pF proposal was superseded). U2 RLDIN62 and RLDOUT63 share `/RLD_DRV` upstream of R2; BIAS_E remains on its protected/contact side. No nRF pin assignment changed.

## Input integrity and acceptance

I2C/IMU routes leave the electrode corridor; SPI/DRDY/START/CS retain the north partition. The final independent cross-layer track-projection audit found no active-digital/electrode overlap. Routes use common channel layers where achievable, without length-matching meanders. Some local F.Cu hops remain; the measured P/N capacitance difference, rather than equal trace length, is the acceptance quantity.

The complete `sim/preorder/run_all.sh` passed. The release gate uses its **3313 tables, actual 10 kΩ arrays and via-land victim extraction**. Track/pad and via-land capacitances are summed per victim/aggressor before applying `inject.victim_gain`; channel RSS assumes no P/N cancellation. Mutual capacitance below is the largest active victim/aggressor sum in each channel; injection includes modeled supply ripple and uses 1 MΩ || 10 nF contacts. The delivered tracks, vias, pad geometry and filled zones compare identical to the analyzed source save.

| Channel | Max active coupling, fF | Injected noise, µV RMS | P/N mismatch, pF |
|---:|---:|---:|---:|
| 1 | 0.894 | 0.0565 | 0.712 |
| 2 | 0.674 | 0.0255 | 0.127 |
| 3 | 0.124 | 0.0119 | 0.186 |
| 4 | 0* | 0.0015 | 0.067 |
| 5 | 0* | 0.0000 | 0.242 |
| 6 | 0* | <0.0001* | 0.435 |
| 7 | 0* | 0.0000 | 0.366 |
| 8 | 0* | 0.0063 | 0.003 |

*The track/pad extractor omits rows below 0.01 fF; the supplied via-land pass omits rows below 0.05 fF. Zero denotes the extraction floor, not physical zero. All channels pass <2 fF, ≤0.1 µV RMS and ≤2 pF mismatch. These are modeled incremental interference values, not total ADC/contact/motion noise. The adverse 1 MΩ || 1 nF case gives 0.4520 µV RMS on CH1; the contact assumption matters.

Remaining In2.Cu→B.Cu GND-reference gaps, excluding own-via antipads, follow. Each location is a bounding box (xmin,ymin)..(xmax,ymax) of one connected missing-reference interval. Lengths are along the trace, not box diagonals.

| Net | Gap length, mm | Location, mm |
|---|---:|---|
| `/E1N` | 0.3487 | (11.550,19.169)..(11.681,19.463) |
| `/E1N` | 0.3010 | (11.769,18.869)..(11.981,19.081) |
| `/E1N` | 0.8488 | (12.745,17.944)..(13.506,18.155) |
| `/E1N` | 0.7780 | (14.323,16.975)..(15.038,17.127) |
| `/E1P` | 0.3550 | (9.325,19.099)..(9.476,19.392) |
| `/E1P` | 0.0015 | (9.901,23.650)..(9.902,23.650) |
| `/E4N` | 0.3317 | (16.175,22.149)..(16.401,22.388) |
| `/E4P` | 0.3323 | (17.175,22.543)..(17.175,22.875) |
| `/E7N` | 2.0137 | (15.337,20.250)..(16.750,20.775) |
| `/E7P` | 0.4048 | (14.725,18.549)..(14.975,18.851) |
| `/E7P` | 0.1671 | (15.550,20.037)..(15.663,20.150) |
| `Net-(RN1B-R2.1)` | 0.0011 | (24.091,17.891)..(24.092,17.892) |
| `Net-(RN3D-R4.1)` | 0.2497 | (15.001,17.375)..(15.251,17.375) |
| `Net-(RN4B-R2.1)` | 0.0010 | (15.528,15.747)..(15.528,15.747) |

**E7N retains a 2.014 mm gap at x=15.337..16.750, y=20.250..20.775**, above quiet E8P copper. Local bottom-crossing and paired F/In2 reroutes for E7/E8 were attempted and rejected when no connected clearance-clean route remained. It is the remaining >1 mm reference exception. The independent analog review accepts it: modeled crosstalk is −94 dB with 10 nF contacts. The complete interval list remains authoritative.

## Ground and RF

One common GND network, with **103 GND vias** and an uninterrupted In1 plane outside the intentional antenna/matching exclusions. The nine added U1 EP vias are ordinary 0.30/0.45 mm through-vias, fully enclosed by the EP, with bottom tenting. Their positions were adjusted away from existing inner/bottom signals rather than forcing a geometrically regular grid. The former straddling via at (6.65,5.90) remains removed; (6.20,3.00) provides an outside anchor. Another GND anchor at (11.60,11.35) serves the crowded bypass/reference region.

| Via-free GND metric | Maximum, mm | Location |
|---|---:|---|
| RF | 2.9624 | (6.1331,10.4406) |
| AFE | 2.9879 | (13.6156,9.1444) |
| all | 3.7340 | (20.3715,26.5000) |

The distance is the maximum over native filled-polygon/Voronoi-cell vertices, measured to GND via centres. RF region: x=0..13.5, y=0..11.65; AFE region: x=10.5..26.6, y=3.7..16.5. The overall maximum is near the bottom test pads and is within the subsequently relaxed 4 mm target there. The JSON retains exact values rather than rounding a small overrun into compliance.

Every active-digital transition within 8 mm of the ADS centre has a GND via within **0.9779 mm**. Full layer-wise GND union has no component ≥0.2 mm² without an anchor; **18 components still have only one anchor**, including narrow fingers bounded by routing. Additional standard-drill sites were not available for all of them; complete second-anchor coverage is not claimed. Their areas and bounds are in the release JSON.

AE1 remains the AN043 printed IFA. Its radiator polygons and the three RF-net track/via geometries compare unchanged with the isolated CPL baseline. Keepout x=0..5.65, y=11.65..27 and the Nordic matching exclusion are unchanged. Seven counterpoise fence vias remain at x=6.0, y=13.4/16.2/18.2/20.2/22.2/24.2/26.2. C21 returns through VSS31 only; the new EP vias add no direct C21-pad connection. C22/C23 remain DNP, R3=0 Ω. AE1 pad 2's minimum land width is now 0.60 mm around its 0.30 mm drill; the radiator polygon is unchanged.

Post-match RF copper remains 0.160 mm. On the documented 3313 stack the review estimates approximately 51 Ω covered; this is not a new full-wave solution or a measured antenna match. Preserve the matching exclusion and feed-side GND setback. The documented worn link margin is a model result; the flex electrode/shield copper remains below the antenna. In the reconciled mechanical frame **pod 4** is underneath it: `X_world = X_flex − 65 = 14 − X_main`. See `docs/layout/flex_c_layout.md`.

## Assembly and CPL

U1 EP paste has **nine clipped window apertures, 60.60% coverage**, at least **0.109 mm** from every via land. No paste lies on those vias; B.Mask has no opening over them. The minimum EP-edge clearance of a new via land is 0.050 mm. Home assembly needs a stencil and controlled reflow for the QFN; this is an ordinary-drill, bottom-tented implementation, not filled/capped vias.

0402/0603 passive GND pads use thermal reliefs, normally 0.25 mm spokes with 0.15 mm gap. C9/C13 use 0.10 mm gaps; C32 uses 0.20 mm spokes / 0.10 mm gap to retain connected reliefs. QFN EP, RF match and antenna short remain solid. Pad/via repair moved 28 signal/ground barrels away from pasted pads and removed redundant barrels; the channel-8 move was deliberately restored when it produced a noise-failing detour. The exact drill-to-pad pairs below the 0.20 mm preference are listed in the release JSON; minimum 0.0408 mm remains; all holes clear the actual pasted SMD lands. Exact exceptions are in the JSON. The intentional EP vias have paste exclusion and are reported separately.

Pin-1 dots mark actual KiCad pad 1 for U1–U5, Y1 and RN1–RN4 in their baked orientation. D1 has a cathode bar. Main-board text is ≥1.0 mm / 0.15 mm stroke. F.Silk carries the clipped nominal cell outline and CELL label. Vertical DOWN sits beside J1 with ≥0.2148 mm stroke-to-pad clearance, with a down arrow above the connector and a restored pin-1 dot. These marks clear the closed actuator, SW1 and antenna exclusion. Top/bottom renders and macro-complete Gerbers were inspected.

The initial isolated footprint bake compared **309 pads: maximum absolute pad displacement 0 mm, rotation change 0°**. All eight copper/mask/paste Gerbers matched apart from generated headers. Later layout/EP-paste changes are intentional and separate. Model rotations were corrected for KiCad's opposite model-Z convention; the old and new world orientations agree. J1's anchor moves +1.600 mm in board Y to the soldered-land bounding-box centre without moving any land. No position-file postprocessing is used.

| Reference | Raw rotation |
|---|---:|
| U1 | 90° |
| U2 | 0° |
| U3 | 180° |
| U4 | 0° |
| RN1 / RN2 / RN3 / RN4 | 180° each |
| J1 | 0°, Mid (14.0000, −23.1925) |

Baked local footprints and J1's centroid footprint are under `boards/neurband_c/layout/neurband.pretty/`; the schematic generator uses those IDs. New capacitor/array choices use basic parts from the fab's stock. The 25 assembled BOM types were checked against positive stock on 2026-10-29: 17 basic, 2 preferred, 6 pre-existing extended types (U1/U2/U5/Y1/J1/C21); no new extended type. Availability is a snapshot, not a reservation.

## Release files and checks

**Main:** 0 DRC errors, 0 unconnected, 0 parity differences after refill/save; only 52 `lib_footprint_mismatch` warnings remain. ERC has 0 errors and 8 pin-to-pin warnings: U5 pins 1/2 and U2 pins 17/18/42/44/45/46 are bidirectional library pins tied to flagged supply nets. These are explicitly retained warnings, not suppressed checks.

**Flex:** regenerated and refilled, 0 DRC violations/unconnected/parity and 0 ERC violations. All 16 alignment holes are drilled through coverlay without mask pre-openings; 447 trace segments and 60 vias retain their geometry and the 0.20 mm hole clearance. The flex manifest remains `order: false`. `boards/neurband_c_flex/ORDERING.md` specifies PI/RA copper, coverlay both sides, ENIG 2 µ", ~0.11 mm laminate, F-side 0.225 mm PI stiffener on User_2 for 0.30 ±0.03 mm fingers, B-side contacts, ±0.05 mm tail width request, NPTH holes and quantity 5.

Main schematic BOM was regenerated with the existing columns and checked against all 59 assembled placement references; 25 lines, every line has MPN. Exports: `boards/neurband_c/neurband_c.step`, `neurband_c_board_only.step`, `renders/`, `docs/media/board_top.png`, `board_bottom.png`, `board_layers.png`. Flex STEP/renders are refreshed. Review Gerbers/drills and the unmodified raw placement CSV are in `mfg/20261029_preorder/`; these are regenerable previews. Native reports, bake proof, stock snapshot and intermediate backups were kept locally in `layout/build/preorder_20261029/` (not in the repo) and the flex `build/` directory.

Self-review rechecked signal projections, reference gaps, EP paste/drills, model/pad pin-1 orientation, frozen interfaces, RF exclusions, via costs, BOM/CPL agreement and saved-file exports. Remaining exceptions are the E7N gap, incomplete VBAT/star topology, single-anchor fragments and sub-0.20 mm drill-to-pad preferences; the exact RF/AFE distance above also remains authoritative. No nRF pin swap, larger board, extra layer, small drill or additional extended part was used.

## Schematic second opinion

The 10 kΩ arrays improve input-current isolation but add resistor noise: approximately 0.52 µV RMS for two 10 kΩ resistors over a rectangular 20–850 Hz band at 300 K, versus 0.36 µV for two 4.7 kΩ resistors. This is separate from the injected-noise table. They do not establish an ESD rating. The 0603/10 V bulk capacitors offer better DC-bias margin; effective capacitance still depends on voltage and tolerance. C33 is appropriate local AVDD1 bypassing and does not replace VCAP3. Amplifier-side RLDIN avoids bypassing R2; the accepted 12 pF shunt is modest RF filtering, not surge protection or bias-loop qualification.

The 10 kΩ I2C pull-ups reduce low-state current; at 400 kHz, a 300 ns rise-time budget permits about 35 pF total bus capacitance, so verify the assembled rise time. A possible future simplification is internal RLDREF instead of R12/R13/C32, but only with firmware/register and bias-loop validation; those parts remain fitted here. The integrated antenna and DNP tuning sites are retained. Operate battery/BLE only while worn, with charging/programming disconnected.

## Final polish (2026-10-29)

E1N moved to (25.675,19.800) and E2P to (23.450,19.900); their minimum via-land gaps to U5 SCL/SDA are 0.9612 and 0.4157 mm. Both exceed 0.40 mm. C29 moved 0.075 mm inward and C6 0.0375 mm inward; the short right-edge +3V3A section is 0.10 mm wide. Measured non-pour copper clearances are C29 0.415 mm, right +3V3A 0.400 mm and bottom GND via 0.425 mm. C22/C23 remain at 0.340 mm to preserve RF geometry; their paste apertures were removed.

Three of the ten crowded barrels now have 0.125 mm hole-to-pasted-pad clearance: RN4.3, RN4.4 and RN4.8. Seven remain at 0.0408–0.0500 mm: U2.35/36, R11.1, RN4.5/6, RN3.3/4 and U1.19. Nearby trial sites were unavailable or failed native 0.20 mm hole clearance and were rolled back. No hole overlaps a pasted opening. C18 remains unchanged (6.0 mm supply route, 1.8 mm to its GND via): two pin-facing placements could not cross the crystal escape field cleanly, and proposed local GND vias conflicted with DEC3 or the bottom PROG route. This is the independent review’s explicitly acceptable conditional SHOULD limitation.

The CELL outline is on F.Silk at nominal x=10.5..22.5, clipped to y=0.2..21.7, with ≥0.1502 mm stroke-to-pad clearance and breaks around the DOWN text. The flex stiffener is one closed filled User_2 rectangle, 10.50 × 3.70 mm; all 447 trace segments, 60 vias and J1 finger geometry compare unchanged. Flex DRC/ERC/parity remain zero. The BOM, raw CPL, main/flex STEP, renders, layer images, measured manifests and manufacturing previews were refreshed.

Final coordinator delta: the C6 return via moved from (26.975,12.725) to (24.700,12.800), with its F.Cu return tied through adjacent ADS GND pin 20. C6 and the edge-side AVDD track did not move. Hole-to-C6-pad clearance is 2.300 mm, with no new sub-0.20 mm pasted-pad pair. J1’s pin-1 dot is at (9.075,20.650), above its pin-1 end and clear of the closed body; actual dot-to-pin-1-pad gap is 0.194 mm, versus ≥0.488 mm to every other front pad. Only that GND via/return and the dot changed in this delta.

## Raw assembled-part positions

Direct `pcb export pos --format csv --units mm --side front --exclude-dnp` output. Coordinates/rotations are copied as exported; no additional fab rotation correction.

| Ref | Value | Raw X | Raw Y | Raw rotation |
|---|---|---:|---:|---:|
| C1 | 100nF | 27.4625 | -14.3500 | -90 |
| C2 | 1uF | 27.3700 | -9.4000 | -90 |
| C3 | 1uF | 12.1000 | -9.9000 | 90 |
| C4 | 1uF | 27.3700 | -7.4000 | -90 |
| C5 | 22uF | 27.6625 | -4.9500 | 90 |
| C6 | 10uF | 27.6250 | -11.9500 | -90 |
| C7 | 1uF | 26.0625 | -15.2500 | -90 |
| C8 | 100nF | 27.0625 | -16.2500 | -90 |
| C9 | 100nF | 13.0750 | -11.7500 | -90 |
| C10 | 1uF | 16.4500 | -2.4500 | 90 |
| C11 | 100nF | 13.0750 | -3.5000 | 90 |
| C12 | 4.7nF | 10.9000 | -13.4000 | 90 |
| C13 | 100nF | 13.0900 | -8.0000 | -90 |
| C14 | 100pF | 3.2000 | -6.9000 | 180 |
| C15 | 1uF | 9.6000 | -10.2500 | -90 |
| C16 | 10uF | 12.9000 | -1.0000 | 0 |
| C17 | 100nF | 10.9000 | -10.6000 | -90 |
| C18 | 100nF | 4.1000 | -7.9000 | 0 |
| C19 | 12pF | 2.5500 | -10.2000 | -90 |
| C20 | 12pF | 6.8000 | -10.4000 | 0 |
| C21 | 0.8pF | 4.7000 | -5.9000 | -90 |
| C24 | 1uF | 8.6000 | -10.6000 | -90 |
| C25 | 10uF | 8.7500 | -16.5000 | 180 |
| C26 | 1uF | 12.5000 | -20.1000 | 0 |
| C27 | 1uF | 7.7500 | -21.1200 | 0 |
| C28 | 10uF | 24.3100 | -2.2000 | 0 |
| C29 | 100nF | 14.8750 | -1.1750 | 90 |
| C30 | 100nF | 26.0000 | -0.8000 | 0 |
| C31 | 100nF | 27.3500 | -21.6000 | 90 |
| C32 | 1uF | 11.5000 | -12.0000 | 180 |
| C33 | 1uF | 13.0750 | -9.9000 | -90 |
| C34 | 12pF | 11.3000 | -14.8000 | 180 |
| D1 | red | 2.0000 | -1.0000 | 0 |
| J1 | FPC 20p 0.5mm (electrode flex) | 14.0000 | -23.1925 | 0 |
| L1 | 3.9nH | 3.2000 | -5.5000 | 0 |
| R1 | 1M | 12.1000 | -13.4000 | 90 |
| R2 | 100k | 13.9000 | -15.0000 | 180 |
| R3 | 0 | 1.5800 | -8.3000 | 90 |
| R4 | 10k | 2.3000 | -2.8000 | 0 |
| R5 | 10 | 21.8000 | -2.2000 | 0 |
| R6 | 1M | 20.7000 | -0.8000 | 0 |
| R7 | 1M | 23.8000 | -0.8000 | 0 |
| R8 | 1k | 5.0000 | -1.0000 | 0 |
| R9 | 10k | 16.5000 | -0.8000 | 0 |
| R10 | 10k | 18.8000 | -0.8000 | 0 |
| R11 | 100k | 24.8500 | -3.9000 | 90 |
| R12 | 1M | 3.7500 | -3.5000 | 90 |
| R13 | 1M | 4.8500 | -2.4000 | 90 |
| RN1 | 10k | 23.9000 | -18.3000 | 180 |
| RN2 | 10k | 20.1000 | -18.3000 | 180 |
| RN3 | 10k | 16.3000 | -18.3000 | 180 |
| RN4 | 10k | 12.5000 | -17.0500 | 180 |
| SW1 | WAKE / MARK | 24.8000 | -25.1000 | 0 |
| U1 | nRF52832-QFAA | 9.0000 | -5.7000 | 90 |
| U2 | ADS1298IPAGR | 20.2000 | -10.1000 | 0 |
| U3 | XC6206P332MR | 8.6000 | -18.9500 | 180 |
| U4 | TP4054 | 8.6000 | -13.7000 | 0 |
| U5 | LSM6DSL | 24.5000 | -21.6000 | 0 |
| Y1 | 32MHz 8pF | 4.3500 | -9.9000 | 90 |
