# neurband rev C: review of the owner's layout before ordering (2026-11-01)

Six independent read-only reviews of the main board as the owner re-placed and re-routed it (board SHA-256
`d428025a…0e46d5`, schematic as edited by hand), plus a review of the re-routed electrode flex (rev C.2):

| Review | Scope | Verdict |
|---|---|---|
| Schematic | every net change since the reviewed state, J1 -> ADS map, nRF pins vs firmware, ERC, BOM | clean (5 notes) |
| Analog front end | input pairs, digital coupling, P/N mismatch, ADS support parts | clean, much better than before (5 notes) |
| Power and ground | supply paths, IR drop, decoupling, planes, EP, charger | 4 fixes + 5 notes |
| RF, crystal, digital | match, feed, keepout, stitching, crystal, nRF pins | 2 fixes + 4 notes |
| Manufacturability | fab limits, lands, paste, tombstoning, orientation, BOM/CPL, stock | 4 fixes + 4 notes |
| Second opinion (Sol) | whole board, independent | "order after specific fixes" |
| Electrode flex rev C.2 | connectivity, flex rules, reliability, mating | see the flex section |

## Verdict: main board

**Not ready as is; good to order after a short list of local fixes.** Nobody found a board-killer or a
feature-killer: every channel, BLE, the IMU, charging and power work as drawn. The analog input routing is the
best this board has had. The items below are each a local edit (moving vias, a cap or two, a few stitching
vias), not a re-route.

What got better than the reviewed layout (measured with the same scripts):

| Metric | Old layout | Owner's layout |
|---|---|---|
| Worst digital-to-input coupling | 0.894 fF | 0.028 fF |
| Worst injected input noise | 0.057 uVrms | 0.009 uVrms |
| Worst P/N capacitance mismatch | 0.71 pF | 0.093 pF |
| Input vias | 26 | 0 (all 32 input nets on F.Cu over solid In1 GND) |
| Crystal (XC2) to RF feed | 0.22 mm | 0.84 mm |

## Fix before ordering

Coordinates: board frame, mm from the outline's top-left.

| # | Found by | What | Why | Fix |
|---|---|---|---|---|
| 1 | Sol, power, manufacturability | **U1 exposed-pad paste windows don't match the new vias.** 12 of the 13 EP via drills sit fully under paste (the windows still have notches for the old 9-via pattern); 0.92 mm3 of open barrel vs ~0.6-0.8 mm3 of printed solder | Solder drains into the vias: voids and a starved EP joint (U1's main RF/thermal ground) | Put the vias back on the old 9 sites in the windows' notches, or re-clip the paste windows to clear each via land by >= 0.10-0.15 mm, or order plugged/capped vias |
| 2 | Sol, RF, power | **C21 (0.8 pF, Nordic's C3) grounds straight to a via at (5.33, 4.50)**, not through U1 VSS pin 31 | Nordic requires C3 to return through VSS31 to filter harmonics; higher 2nd/3rd harmonics, match drifts from the reference | Put C21's GND pad at about (4.80, 6.40) (rotate it; the ANT pad stays on the ANT line), a short F.Cu stub to pin 31, delete the C21-to-via track |
| 3 | RF, power | **No ground stitching along the antenna's ground edge and the bottom edge** (the old layout had 7 vias at x = 6.0 and 16 below y = 22; now 0 and 5) | The In1/In2 plane edge beside the radiator is unbonded over ~15 mm: detuning/efficiency loss (likely < 1 dB) | GND vias at (6.05, 13.4 / 16.2 / 18.2 / 20.2 / 22.2 / 24.2 / 26.2) (all clear of the feed by >= 0.57 mm) and 4-6 along y ~ 26.2 |
| 4 | Manufacturability, power | **Vias cutting into pasted pads** (11: C28.2/C29.2 shared via at (14.02, 3.90), C11.2, Y1.2, C14.2, C9.2, C17.2, R9.2, R10.1, R10.2, C28.1) and **tight pad gaps**: 12 different-net pairs at 0.14-0.16 mm, including VBAT-GND at R6.1/R7.2 (7.75, 9.7) and R6.1/C30.2 (7.75, 11.1), +3V3A-GND at C9/C33 (0.141 mm) | Starved joints and tombstoning on 0402s; bridging risk (a VBAT-GND bridge shorts the battery) | Move those vias so the drill is >= 0.1 mm outside the pad; spread side-by-side pairs from 0.70 to >= 0.75 mm pitch |
| 5 | Sol, power, analog | **ADS1298 bypass not local**: AVDD1 (pin 54, the charge pump) has no cap of its own (C33 is 4.7-6 mm of copper away, next to pin 56); right-side AVDD pins 17-22 reach C7/C8 through 6-9 mm and 2-3 vias; VREFP's 100 nF (C1) is 6.5 mm away | Outside TI's layout guidance; in-band effect likely negligible but unmeasured | Move C33 to pins 54/53 and C1 to pins 24/25; add or move a 100 nF to the right-side AVDD pins and tie pins 17/18 to 19 on F.Cu |
| 6 | Power | **J3 charge input has no protection**: no TVS, C24 sits after U4's pin, J3 is exposed on the bottom, and the new case charges through a magnetic pogo connector (a bouncing hot-plug) | TP4054 VCC abs max is 10 V; its datasheet warns hot-plugging into an MLCC can ring above that: a dead charger | Schematic: add a 5 V TVS (SOD-523/0402 class) at VCHG and 1-1.5 ohm in series; route J3 -> C24 -> U4 pin 4 |

## Worth doing (notes)

- **Copper near the edge** (manufacturability): In1/In2 come to 0.30 mm from every edge (old: 0.50); /ADC_PWDN runs 0.30 mm from the top edge, VBAT 0.325 mm; ceramics within 0.4-0.7 mm of the right edge (C26, C1, C2, C25, C5, C6). When the fab breaks off its rails, caps that close can crack. Set a 0.5 mm zone-to-edge rule, pull the two edge tracks in, and ask for rails on the y = 0 and y = 27 edges only.
- **Tombstoning** (manufacturability): 28 of 46 passives have a GND via within 0.25 mm of one pad and a thin track on the other. Acceptable for 2 boards; worth fixing on C21, C19, C20, C14.
- **Bias/RLD next to an input** (analog): BIAS_E/RLD_DRV pads at y = 15.2 sit 0.175 mm from IN8N for ~2 mm (22 fF imbalance; ~0.3 uV bench worst case; an ESD path past RN4). Make it >= 0.4 mm. Also the BIAS_E via at (18.56, 22.57) is 0.128 mm from E1N.
- **J1 hold-down tabs** have no net (one is 0.10 mm from BUTTON, 0.13 mm from E1P): tie both to GND.
- **J2 VBAT pad**: a tented GND via 0.125 mm from its edge at (27.9, 18.6); hand-soldering the cell lead can lift the mask and short VBAT. Move it >= 0.3 mm away.
- **0603 lands** (C5, C6, C16, C25, C28): 1.90 mm end to end is below IPC least (~2.05) for thick 22 uF/10 uF bodies; 0.80 x 0.85 pads at +-0.725 fit with >= 0.105 mm clearance.
- **Inner-plane clearance 0.5 mm** merges via antipads into slots at (24.1-25.2, 10.0-13.4) and (7.8-10.8, 1.6-2.4); 0.25 mm would keep the planes whole.
- **VBAT** runs as a 48 mm loop on B.Cu 0.325 mm from the top edge and along the RF cut-out under the ANT pin: pull it >= 0.5 mm in.
- **RF feed** is 0.151 mm (designed 0.160): ~51-52 ohm, negligible; widen if convenient.
- **U4 GND** has one via: add a second. **U1 VSS pin 45** isn't tied to the EP on top (it grounds through C15's via).
- **SWD pads**: 1.0 mm diamonds with 0.27 mm gaps, TP1 (+3V3) next to TP2: use thin wire when soldering.
- **Silkscreen**: the "STACKUP: ...3313" text lies outside the outline (the fab will clip or query it): move it to the order notes. The back-side Backplane logo and handle sit under the antenna area (thin ink on the far face, ~1 mm from the antenna copper: negligible, but easy to move to the free centre of the back).
- **Order data**: regenerate the position file with `--exclude-dnp` (C22/C23); the main board's fab.json still says "Unrouted"; the BOM CSV now matches the schematic (C9/C31 are 1 uF, by the owner's edit).
- **Net names**: the main board's J1 nets (E1P..E8N) no longer correspond to pods; the channel map lives in `host/neurband_ble.py` (`POD_MAP`) and `docs/firmware_c.md`.

## Checked and fine (all reviews)

Schematic: every J1 pair reaches exactly one ADS channel; every nRF pin the firmware uses is wired right (the firmware builds with the current overlay); P0.28/AIN4 and P0.31 are sensible choices; ERC has only the 8 long-standing tied-pin warnings; all 69 footprints exist and match their parts. Power: supply paths, IR drop (< 1 mV), LDO stability, brown-out margin during BLE TX and AFE start, TP4054 heat, nRF decoupling distances (0.36-1.84 mm), VCAP/DVDD caps (0.5-3.7 mm), single solid In1/In2 planes with no islands. RF: match placement identical to the reviewed board, Nordic matching keepout clear on In1/In2/B.Cu, 100 % ground under the feed after L1, other top copper >= 0.528 mm from the feed, antenna keepout empty, crystal fully over ground with nothing switching nearby, decoupling values per Nordic. Manufacturing: 0.10/0.10 mm minimum track/gap, all vias 0.30/0.45, hole-to-copper >= 0.20, mask webs >= 0.15 mm, silkscreen >= 0.15 mm lines and clear of pads, all 11 pin-1 marks on the right pin, raw position-file rotations consistent with the fab's convention, bodies >= 0.15 mm apart, no bottom-side parts, all parts in stock (ADS1298 lowest at 1,650).

## Electrode flex (rev C.2)

**Good to order.** No board-killer or feature-killer. Checked from the copper: every finger reaches the
electrode in `flex_pinmap.py`, and combined with the main board every pod lands on exactly one ADS channel,
matching `POD_MAP` (host) and the table in `docs/firmware_c.md`. DRC/ERC/parity 0; tracks/gaps >= 0.10 mm;
52 vias at 0.60/0.30; copper >= 0.30 mm from the cut edge; 24 electrode openings of 6.3 mm (coverlay captures the
pads); one B-side finger window, no slivers; vias only in pods and in the captured root (none in the links or the
free tail); no copper stacked on both faces in any link or the free tail; mating interface identical to rev C
(finger pads, pin 1 side, tab 10.50, B window, stiffener, holes).

Applied after the review: the 20 tail lines are 0.20 mm from the root vias to the fingers (they were 0.10 mm
where they cross the stiffener edge); the ground hatch is kept out from behind the P/N skin discs (it was ~88 % of
each line's ~22 pF to GND, which converts electrode-impedance mismatch into mains pickup at about -49 dB; now
~2-3 pF); ORDERING.md says 52 vias and 6.3 mm openings with no expansion.

Notes left: the module-side links (2-3, 4-5) bend at R >= 2.3 mm, ~0.8 % strain on the F-side lanes: fine for
installation, above the guideline for constant flexing (the new conventional strap bends them far less than
the old slip-on loop); 24 lane edges are exactly 0.20 mm from the 1.2 mm alignment holes, so the fab must drill
them, not laser-cut them; silkscreen digits sit in the U-bend zone (cosmetic).
