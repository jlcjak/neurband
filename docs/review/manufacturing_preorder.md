# neurband rev C: pre-order manufacturability review (DFM / DFA / CPL / BOM)

Date: 2026-10-28, re-checked 2026-10-29 on the reworked boards (next section). Original scope: the two boards as saved in git (`21677f8`): the main board `boards/neurband_c/neurband_c.kicad_pcb` and the electrode flex `boards/neurband_c_flex/neurband_c_flex.kicad_pcb`. The target is the fab's PCB, flex and SMT assembly service, checked against the fab's published capability, assembly and price pages as read on 2026-10-28. Part data comes from the fab's stock, checked live on 2026-10-28.

**Read-only.** No `.kicad_*` file, generator, layout script, BOM or fab.json was edited. Everything that writes (zone refill, `--save-board`, Gerber, drill, position and IPC-D-356 exports) ran on copies in a temporary directory. The only file written in the repo is this report.

Electrical design (bypassing, analogue noise, antenna) is out of scope, except where it sets a manufacturing parameter (the stackup). For that topic see `docs/review/sol_preorder_review.md`.

## Final delta check (2026-10-29)

**Verdict: ready to order. No MUST in the design files.** The order-time confirmations R1–R3 from the re-check below still apply.

Scope: the boards after the final polish pass, checked read-only on temporary copies. All four design files were unchanged from start to end.

| File | SHA-256 | Note |
|---|---|---|
| `boards/neurband_c/neurband_c.kicad_pcb` | `766f7908…eaf3` | Same hash as `preorder_release.json` |
| `boards/neurband_c_flex/neurband_c_flex.kicad_pcb` | `b4bcde70…694a` | — |

**What I checked:**
- **DRC.** Main: 0 errors, 0 unconnected, 0 parity, plus 52 stock-library mismatch warnings. Flex: 0 / 0 / 0. The same after refill.
- **Zone fills current.** 0.0000 mm² saved-vs-refilled difference on every zone, and Gerbers identical with `--check-zones`.
- **Drills.** Main: 254 × 0.30 mm PTH. Flex: 60 × 0.30 mm PTH and 16 × 1.2 mm NPTH.
- **CPL.** The fab-footprint fit on the raw `kicad-cli pcb export pos` gives **all 59 parts delta 0 and pad-centre offset ≤0.03 mm**, with UUIDs matching 25/25. Exported values: U1 90, U2 0, U3 180, U4 0, RN1–RN4 180, J1 (14.0000, −23.1925).
- **BOM.** 25 lines, 59 references, matching the board's Value, Footprint, MPN and fab part number exactly.
- **Silkscreen.** Measured from exact geometry, it is **≥0.150 mm from every mask opening**.
  - The new top-side CELL outline (x 10.5 and 22.5) is broken around pads at exactly 0.150 mm.
  - The vertical "DOWN" text is 0.215 mm from J1.
  - Nothing is inside the antenna keepout.
  - All texts are 1.0 / 0.15 mm.
  - Pin-1 dots are at the fab's pin 1 of U1–U5, Y1, RN1–RN4 and J1. D1's bar is on its cathode (KiCad pad 1 / fab pad 2).
- **Paste.** **None on the DNP C22/C23 pads.** F_Paste has 297 apertures, down from 301.
- **Via holes near pasted pads.** No via hole lies inside any pasted mask opening (0 % for all 27 pairs). RN4.3, RN4.4 and RN4.8 are now 0.125 mm.
  - **C6 pad 2 is new and now the tightest:** hole edge 0.025 mm. C6 moved 0.0375 mm toward the via in the edge pass; the via stays at (26.975, 12.725). It is a GND 0603, so the risk is minor wicking or a tombstone.
  - Then U2.35/36 0.041, R11.1 0.045, and RN3.3/3.4, RN4.5/4.6 and U1.19 at exactly 0.050 mm.
- **Edge copper against the 0.4 mm V-cut rule.** Pours are 0.50 mm from the edge. Everything else is ≥0.400 mm from the straight edges, except:
  - the DNP C22/C23 GND pads at 0.340 mm (harmless if nicked);
  - a GND via at (28.05, 0.80), which is 0.425 mm from the straight edge and 0.372 mm only to the R1 corner arc.
- **Flex.** User_2 now plots as **one filled region, 10.50 × 3.70 mm** (x 59.75–70.25, y 54.80–58.50, inside the tab), plus its text label drawn outside the board outline. Copper, mask/coverlay, outline and drill Gerbers are geometrically identical to the re-check (0 mm² difference; only the plot order changed). The tail pads are unchanged.

**Left as SHOULD:**
- The C6.2 via.
- The other seven tight vias (R6).
- J1's new pin-1 dot at (8.75, 20.35) is about as close to U3 pin 2 (0.56 mm) as to J1 pin 1 (0.58 mm). U3 has its own dot 0.19 mm from its pin 1, so this is a minor ambiguity.
- The flex stiffener overlaps the coverlay edge by only 0.15 mm (R9).

The re-check below this section is resolved as follows:
- **Fixed:** R4 ("DOWN" now 0.215 mm), R10 (filled stiffener), and the DNP-paste, J1 pin-1 and CELL-side points of R11.
- **Mostly fixed:** R5. The DNP pads are left at 0.34 mm, and the corner via is within the rule for a straight V-cut.


## Re-check of the reworked boards (2026-10-29)

An independent re-run of the whole pre-order check on the saved files, read-only, with all writes on temporary copies.

| File | SHA-256 |
|---|---|
| `boards/neurband_c/neurband_c.kicad_pcb` | `0b455055…98e8` |
| `boards/neurband_c_flex/neurband_c_flex.kicad_pcb` | `911ba74a…43db` |

The main-board hash is the same one recorded in `boards/neurband_c/layout/preorder_release.json`. All four design files (both boards, the BOM and the schematic) were unchanged from the start of the check to the end.

### Verdict

**Ready to order. Nothing in the design files has to change first.** Every main-board MUST from the first review has been fixed in the files:
- The footprints carry the fab's rotations, and J1 is placed at its pad centre.
- The KiCad stackup is now the 3313 build.
- The flex is set to `order: false` and has its own ordering sheet.
- The stiffener is specified as 0.225 mm.

What is left are three order-time confirmations (R1–R3) plus SHOULD-level polish (R4–R13).

**MUST (order-time; these can't be checked in the files):**
- **R1 – Stackup.** The order must actually request the fab's 1.0 mm "3313" four-layer build. `neurband_c.fab.json` has no field for it, and the fab's default "7628" build puts the 0.16 mm RF feed at about 75 Ω instead of about 51 Ω. `boards/neurband_c/ORDERING.md` states the requirement, but someone must make sure the Buy-it order carries it.
- **R2 – No server-side rotation database.** Backplane must confirm that its order server passes `positions.csv` to the fab unmodified. The rotations are now baked into the footprints, so a name-pattern database applied on top would rotate U2, U3, U4 and RN1–RN4 wrong again (§1.4.4).
- **R3 – Assembly tier and flex.** The quote must be for the fab's **Standard** one-side assembly; the economy tier is not offered for black mask with ENIG on 4 layers. The flex is ordered separately through the fab's flex service using `boards/neurband_c_flex/ORDERING.md`.

**SHOULD (polish; fine to order without):**
- **R4 – "DOWN" text on pads.** The "DOWN" silk text is **0.06 mm** from the RN2 and RN3 bottom-row pad openings (RN2.5, RN2.6, RN3.6, RN3.8). The fab wants ≥0.15 mm and will clip the text there. Move it off the 1.37 mm channel between the arrays and J1.
- **R5 – Copper near the V-cut rails.** The ground pours are now 0.50 mm from the edge, but other copper is still inside the 0.4 mm V-cut rule on every edge:
  - top: C29 pad 2 at 0.34 mm
  - right: a +3V3A track at 0.35 mm
  - bottom: a GND via at 0.375 mm
  - left: the DNP C22/C23 pads at 0.34 mm, and GND vias at 0.40 mm (right at the limit)

  The fab chooses which two edges get rails. Pull this copper back to ≥0.4 mm, or accept a possible DFM query.
- **R6 – Vias crowding fine-pitch pads.** Ten vias have their **hole edge within 0.041–0.050 mm** of a pasted pad's mask opening, with the via copper merged into the pad. No hole is inside any pasted opening, but the tent web over the hole is only that wide. These are the pairs that matter for wicking:
  - U2 pins 35/36 (one via shared between both pads)
  - R11 pad 1 (0402: a tombstoning risk if it wicks)
  - RN4 pads 3, 4, 5, 6, 8 and RN3 pads 3, 4
  - U1 pin 19 (0.4 mm-pitch QFN)

  Keep the rule from §1.6 (via hole ≥0.20 mm from SMD pads) when these are next touched.
- **R7 – Watch the U1 exposed-pad vias.** Accept them, but check the first articles (§R.4).
- **R8 – Silkscreen dots between the arrays.** Several dots sit in the gap between parts and are nearer a neighbour's pad than their own pin 1. Each dot is still nearest its own part's fab pin 1, and an RN read 180° off is electrically identical, so this is cosmetic. Moving the RN dots off the gaps would remove the ambiguity.
- **R9 – Flex stiffener overlap (FS1, unchanged).** The stiffener overlaps the B-side coverlay edge by only 0.15 mm (stiffener from y 54.80, coverlay window from 54.95). This is the mechanical owner's call.
- **R10 – Flex stiffener layer.** `User_2` is still a four-line outline plus a text label. A filled outline would be clearer to the fab's CAM.
- **R11 – Informational:**
  - The CELL outline is on the **bottom** silkscreen, while the cell sits over the top components. Confirm that is intended.
  - J1 lost its "1" silk mark. Its footprint can only fit one way, so that is acceptable.
  - The RN1–RN4 3D model rotation on the board (−90) differs by 180° from the local library copy (−630 ≡ +90). The model is symmetric, so this is invisible.
  - DNP C22/C23 still receive paste.
  - `docs/rev_c/cost.md` still says 27 part types; it is now 25 (about $72 in fees, not $75).

### R.1 DRC, zone fills, Gerbers, drills, outline

- **DRC.** Main: **0 errors, 0 unconnected, 0 schematic-parity issues**, plus 52 `lib_footprint_mismatch` warnings. Those warnings are only on stock-library footprints whose silkscreen was stripped; none are on the local FabZero or Centroid footprints. Flex: **0 / 0 / 0**. Refilling on a copy (`--refill-zones --save-board`) gives identical results.
- **Zone fills are current.** Saved and refilled fills differ by **0.0000 mm²** on every zone: main F.Cu 306.7, In1 577.1, In2 443.3, B.Cu 441.6 mm²; flex B.Cu hatch 669.5 mm². Gerbers exported with and without `--check-zones` are identical apart from headers.
- **Layers.** Main has 4 copper layers. In1 is a single GND plane with 0 tracks; In2 carries GND plus routing. All 11 production layers are present and B.Paste is empty. The KiCad stackup is now 0.0994 / 0.7 / 0.0994 mm (3313, εr 4.1), inner copper 0.0152 mm.
- **Outline.** Main: one closed loop, 28.700 × 27.000 mm. Flex: one closed loop, 133.100 × 38.500 mm.
- **Drills.** Main: 253 vias of 0.300/0.45 mm plus one 0.300 mm component hole (AE1 pad 2, now 0.6 mm wide, so its ring is 0.15 mm: S6 fixed); no NPTH. Flex: 60 vias of 0.300 mm and 16 NPTH of 1.200 mm.
- **Fab rules** (unchanged from §1.1 or better):

| Rule | Main board | Fab limit | Result |
|---|---|---|---|
| Min track | 0.100 mm | 0.09 (multilayer) | pass |
| Mask dams | LGA 0.150, QFN/TQFP/FPC 0.200 mm | ≥0.13 (black) | pass |
| Paste area ratio | ≥0.69 at a 0.12 mm stencil | — | pass |
| Pad-to-pad, between parts | ≥0.30 mm | 0.18 | pass |

### R.2 CPL: fab-footprint fit for all 59 placed parts

The fit from §1.4 was re-run on the raw `kicad-cli pcb export pos` output. All 25 part numbers link to the fab footprints already identified, with UUIDs matching the fab's part records 25/25; the two new numbers, C19702 and C29718, use the same footprints as the parts they replace.

**Every part comes out at delta 0 and offset 0**, including every part that moved or rotated in the rework. Offset here is fab pad-centre vs KiCad anchor, and it is ≤0.03 mm everywhere; the 0.03 mm on U3 is a pad-size artefact, not an origin shift.

| Ref | Fab part no. | Footprint (board) | Exported rot = fab rot | Fit (next best) | Exported Mid X, Y |
|---|---|---|---|---|---|
| U1 | C77540 | QFN-48 …_FabZero | 90 | 0.042 (5.20) | 9.0000, −5.7000 |
| U2 | C527440 | TQFP-64 …_FabZero | 0 | 0.113 (9.58) | 20.2000, −10.1000 |
| U3 | C5446 | SOT-23-3_FabZero | 180 | 0.130 (2.24) | 8.6000, −18.9500 |
| U4 | C32574 | SOT-23-5_FabZero | 0 | 0.019 (2.37) | 8.6000, −13.7000 |
| U5 | C126672 | LGA-14 (stock) | 0 | 0.100 (2.05) | 24.5000, −21.6000 |
| Y1 | C718072 | Crystal 2016 (stock) | 90 | 0.000 (1.26) | 4.3500, −9.9000 |
| D1 | C2286 | LED_0603 (stock) | 0 | 0.037 by cathode (1.09) | 2.0000, −1.0000 |
| J1 | C2856803 | XUNPU …_Centroid | 0 | 0.000 (6.72) | **14.0000, −23.1925** (pad centre; fab drawing origin −0.3125 mm from it, §1.4.2) |
| SW1 | C720477 | TS-1088 (stock) | 0 | 0.040 (3.12) | 24.8000, −25.1000 |
| RN1–RN4 | C29718 | R_Array_Convex_4x0603_FabZero | 180 | 0.100 (2.14) | (23.9 / 20.1 / 16.3 / 12.5), (−18.3 / −18.3 / −18.3 / −17.05) |
| 46 passives (C1–C21, C24–C34, R1–R13, L1) | as BOM | stock C/R/L 0402/0603 | = KiCad rot | ≤0.077 | as exported |

**J1's copper is unchanged:** pin 1 at (9.25, 21.5925), pin 20 at (18.75, 21.5925), mounting lands at y 24.168. Only the anchor moved, by +1.600 mm.

**3D models.** Top-view renders of the old (git HEAD) and new boards were compared:
- U1, U2, U3, U4 and U5 show their model's pin-1 dot at the fab pin-1 corner, matching the pads.
- J1's body sits in exactly the same place relative to its lands, because the model offset (0, +1.6) compensates the anchor move.
- RN1–RN4 have symmetric models (see the R11 note on the 180° model-rotation mismatch).

### R.3 Silkscreen

- **Text.** All 12 texts are **1.0 mm / 0.15 mm**: "DOWN" on the top; "5V", "GND", "V D C R G", "rev C", "CELL" and "BAT +" on the bottom. No footprint silkscreen.
- **Pin-1 dots.** There are 10 filled dots (0.25 mm). Each one's nearest fab pin 1 is the intended part's, measured from the dot edge:

| Part | Dot (x, y) | Distance to the part's fab pin 1 | Notes |
|---|---|---|---|
| Y1 | (5.70, 11.00) | 0.29 mm to pin 1 / XC2 | |
| U4 | (6.50, 15.00) | 0.72 mm | 0.23 mm from AE1's feed copper, which is not assembled |
| U3 | (6.65, 17.50) | 0.19 mm | |
| U1 | (12.15, 8.82) | 0.70 mm, at the lower-right body corner | 0.20 mm from C3, which is non-polar |
| U2 | (15.90, 16.70) | 0.35 mm, at the lower-left corner | 0.18 mm from RN3.3 |
| RN4 | (14.60, 16.15) | 0.53 mm | |
| RN3 | (18.35, 17.40) | 0.48 mm | 0.18 mm from RN2.4 |
| RN2 | (22.10, 17.40) | 0.43 mm | 0.22 mm from RN1.4 |
| U5 | (22.65, 20.25) | 0.48 mm | |
| RN1 | (26.00, 17.50) | 0.53 mm | |

The near-neighbour notes are R8.
- **D1 cathode bar.** It sits at x = 0.40, y 0.5–1.5, which is **0.30 mm from the cathode pad** (KiCad pad 1, net /LED, which is fab pad 2) and 1.88 mm from the anode. That is the correct side.
- **"DOWN" marker.** The board reads "DOWN" plus a down arrow; there is no "CONTACTS" word. It sits above J1, 0.158 mm from J1's pads but 0.06 mm from RN2/RN3 (R4).
- **CELL outline.** The outline and label are on the bottom silkscreen, x 11–23, y 0.2–21.7. They are 0.37 mm from the test pads and 0.125 mm from the top edge.
- **Antenna keepout.** No silkscreen inside it (x 0–5.65, y 11.65–27): 0.000 mm².
- **Pads.** Apart from R4, top silkscreen is ≥0.148 mm from every mask opening and bottom silkscreen ≥0.37 mm.

### R.4 Assembly (DFA)

**U1 exposed pad.**
- **The via holes are open on top.** The EP's 4.6 mm mask opening plus the vias' own front-untented 0.45 mm openings leave all nine holes 100 % exposed in F_Mask. They are tented on the bottom (no B_Mask openings), and no paste lands on any hole (0 %).
- **Paste:** 9 windowpanes, **60.6 %** coverage, ≥0.109 mm from the via lands and ≥0.184 mm from the holes. Sol's numbers are confirmed.
- **This is the fab's own low-cost option.** Its QFN guidance is to tent vias on the opposite side or fill and cap them, so the fab's assembly accepts this.
- **Limits:**
  - The vias are closer together (pitch down to 0.67 mm) and closer to the EP edge (0.05 mm) than the fab's thermal-via guidance (1.0–1.2 mm pitch, ≥0.15 mm from the edge).
  - Nine open 0.30 mm holes can take a large share of the EP solder. Worst case is about 0.44 mm³ of plated hole volume against about 0.75 mm³ of solder from a 0.12 mm stencil.
  - Expect some EP voiding, and possibly small solder bumps under the bottom tents. The fab X-rays QFNs.
- **Recommendation:** acceptable for this prototype. The robust alternative is the fab's paid "epoxy filled & capped" via option on 4-layer boards, but the Buy-it flow can't select it.

**Via hole-to-pad pairs under 0.20 mm.** There are 41 in total:

| Group | Pairs | Concern |
|---|---|---|
| U1 exposed pad (above) | 9 | — |
| Bottom test pad TP2 (drill inside the pad, no solder) | 1 | none |
| Bottom J2/J3 pads (no paste) | 3 | none |
| DNP C22/C23 | 2 | none |
| **Pasted top pads** | **26** | see below |

The 26 pasted top pairs plus TP2 are the **27** Sol reported, minimum 0.041 mm. Of the 26:
- No hole lies inside any pasted pad's opening; the hole-in-opening area is 0 % for all 26.
- In 12 pairs the via copper overlaps the pad. Ten have the hole edge only 0.041–0.050 mm outside the opening; that is the R6 list. C6.2 and C15.2 are at 0.062 and 0.074 mm (low risk).
- In the other 14, the hole is covered by ≥0.075 mm of mask and only the edge of the annulus can show. No wicking concern.

This is much better than the first review (82 vias touching pads plus 29 within 0.1 mm).

**Tombstoning.** All 34 GND pads of the placed 0402/0603 passives now have thermal reliefs (`zone_connect 1`, 0.25 mm spokes, 0.10–0.15 mm gap). The measured fill shows 2–4 spokes per pad; the share of each pad's perimeter touching the pour is 0.08–0.47, down from 1.0. The other terminal is fed by 0.1–0.25 mm tracks. S1 is fixed. U1's EP stays solid. The RF capacitor C21 has no pour connection.

**Edges.** Pours are ≥0.50 mm from every edge on all four layers (S4 pours fixed). Other copper is inside the V-cut rule (R5).

**Part spacing.** The closest gap between parts is 0.30 mm pad-to-pad (fab minimum 0.18). U1's and U2's nearest passives are 0.40–0.59 mm away. That is still under the fab's *recommended* 1.0/1.25 mm for rework access, which is informational.

### R.5 BOM

`boards/neurband_c/neurband_c_bom.csv` has 25 lines covering 59 references. Its Value, Footprint, MPN and fab part number agree exactly with the board footprint fields (0 mismatches) and with the schematic symbol fields (0 mismatches). The schematic's other symbols are excluded as intended (AE1, J2, J3, TP1–TP5 not in the BOM; C22/C23 DNP).

| Change since the first review | New part |
|---|---|
| C6, C16, C25, C28 → 10 µF 0603 | CL10A106KP8NNNC, C19702 (basic). Replaces the 10 µF 0402 parts, so my earlier DC-bias note no longer applies |
| R4, R9, R10 → 10 k | C25744 |
| RN1–RN4 → 10 k | 4D03WGJ0103T5E, C29718 (basic) |
| Added | C33 (1 µF), C34 (12 pF) |
| Dropped | C15525, C19666, C25900, C1980 |

**Part counts.** 25 part types: **17 basic, 2 preferred (C14033, C32574), 6 extended (U1, U2, U5, Y1, J1, C21)**. No new extended part has appeared.

**Live stock (2026-10-29):**
- ADS1298IPAGR: **1,755** (the lowest)
- nRF52832-QFAA-R: 22,192
- LSM6DSLTR: 20,242
- 32 MHz crystal: 88,585
- FPC connector: 126,383
- 0.8 pF: 48,780
- C19702: 12.3 M; C29718: 1.35 M; XC6206: 534 k; TP4054: 47.9 k
- All other passives ≥118 k

That is ample for 2 or 5 boards.

**Cost.**
- Parts are about **$27.4 per board**, so about **$55 for 2 boards** and about **$138 for 5**, with typical passive attrition.
- Standard assembly fees are **$25.56 setup + $8.21 stencil + 25 × $1.53 loading = $72.02**. X-ray, if charged, is up to $1.64 per QFN/LGA part.

### R.6 fab.json

- **Main** (`boards/neurband_c/neurband_c.fab.json`): 28.7 × 27.0 mm and min drill 0.3 mm, **measured and current**. Options are 4 layers, 1.0 mm, black, ENIG, qty 5. There is still no field for the stackup (R1).
- **Flex** (`boards/neurband_c_flex/neurband_c_flex.fab.json`): **`"order": false`**, with a note pointing to `ORDERING.md`. Its features (133.1 × 38.5 mm, min drill 0.3 mm) are measured and current. The rigid 0.4 mm options are labelled as a placeholder only. F1 is fixed.

### R.7 Flex

- **Alignment holes are drilled through closed coverlay.** The 16 NPTH holes are now `*.Cu` only, and neither mask/coverlay Gerber has any opening at a hole.
  - The only F_Mask openings are the 24 electrodes (795.1 mm²).
  - The only B_Mask opening is the 10.5 × 3.55 mm finger window (37.4 mm²).
  - Traces stay 0.20 mm from the holes, and there is no longer a coverlay opening there to expose them. FS2 is fixed.
- **DRC** 0 / 0 / 0, before and after refill. Fills current.
- **Fingers unchanged.** The tail's 20 finger pads are identical to git HEAD: pin 1 is GND at (69.75, 56.60), pin 20 is GND at (60.25, 56.60), all B.Cu, 0.30 × 3.2 mm. The tab is 10.50 mm with 0.30/0.35 mm copper-to-edge.
- **`boards/neurband_c_flex/ORDERING.md` matches this review:**
  - PI flex, finished about 0.11 mm, coverlay both sides, ENIG 2 µ".
  - **F-side 0.225 mm PI stiffener on `User_2`, 0.30 ±0.03 mm at the fingers**, which is the F2 correction.
  - ±0.05 mm tail request, NPTH drilled through the coverlay, the `User_2` layer named, qty 5.
  - It asks for rolled-annealed copper with confirmation; the fab doesn't let you choose the copper type, so that confirmation is the right request.
- **Still open:** R9 (stiffener/coverlay overlap) and R10 (stiffener drawn as lines rather than a filled outline).

---

The original review of 2026-10-28 follows unchanged. Where it differs from the re-check above, the re-check is current.

## Verdict (2026-10-28 original review)

The design files are clean: DRC has 0 errors, the zone fills are current, the Gerbers match the last export, and the footprints match their datasheets. The order settings and the pick-and-place data are not ready. If ordered as-is through the export that `mfg/20261026-1042/` reflects, the most likely results are:

1. **Wrong rotation on U1 and U2, which kills the boards.** U3, U4 and RN1–RN4 are also rotated wrong. The Buy-it flow sends raw KiCad rotations, there is no placement preview, and the board has no silkscreen pin-1 marks for the fab's engineers to correct against.
2. **J1 placed 1.6 mm off its lands**, because its KiCad anchor is not the pad centre the fab places by.
3. **A ~75 Ω RF feed.** The fab's default 1.0 mm 4-layer stackup has a 0.21 mm prepreg, not the 0.10 mm the 0.16 mm feed was sized for.
4. **The flex ordered as a rigid 0.4 mm FR-4 board.** Even if it is ordered as a flex, the stiffener thickness in the docs is short by about 0.025 mm.

None of these needs a copper change before ordering. Each is fixed with order settings, plus fab-oriented footprints (or a corrected CPL) and pin-1 silkscreen. Section 1.3 is the main-board list, section 2.3 the flex list, and the summary at the end has both.

---

## 0. What was run

| Check | Result |
|---|---|
| `kicad-cli pcb drc --severity-all --severity-exclusions --schematic-parity`, saved fills | Main: **0 errors, 0 unconnected, 0 parity**, 59 `lib_footprint_mismatch` warnings (sparse silkscreen/models vs library; J1's local footprint only differs by silkscreen). Flex: **0 / 0 / 0**. |
| Same, with `--refill-zones --save-board` on a copy | Identical results on both boards. |
| Zone-fill staleness: saved vs refilled `filled_polygon` geometry, per zone and layer (polygon symmetric difference) | **0.0000 mm² on every zone.** Main: GND F.Cu 339.9 mm², In1 597.6, In2 434.6, B.Cu 413.5. Flex: B.Cu hatch 669.5. **The fills are current.** |
| `pcb export gerbers --board-plot-params` vs `--check-zones` | Byte-identical apart from header lines, on both boards. |
| Fresh export vs `mfg/20261026-1042/` (the last Backplane export) | Every copper, mask, paste, silk and edge layer and both drill files are **identical** (headers stripped). That export is current. |
| Positions (`pcb export pos --format csv --units mm --side front --exclude-dnp`), IPC-D-356 | 57 top placements; matches the Backplane `positions.csv`. IPC-D-356 was used to validate the coordinate transforms. |
| Geometry analysis | Parsed the s-expressions directly (no SWIG): mask dams, via/pad overlap, pour connection per pad, paste area ratios, edge distances, flex tab and coverlay window. |
| Fab footprint comparison | For each of the 27 BOM part numbers, pulled the footprint the fab's library links to it (UUID equals the part record's: 27/27). Fitted it pad-by-pad to the KiCad footprint at 0/90/180/270°, checked the fab's symbol pinouts, and rendered overlays. Compared the result with two community rotation databases. See section 1.4. |
| Datasheets read | Torex XC6206 (pin table), YXC YSX211SL 2016 (pinout + land), ST LSM6DSL (LGA-14 outline), XUNPU TS-1088 (land), XUNPU FPC-05F-NPH20 drawing (`boards/neurband_c/layout/XUNPU_FPC-05F-20PH20.png`), Nordic nRF52832 PS v1.0 (QFN48 dimensions, reference BOM, HFXO limits), TI ADS1298 (PAG pinout). |

---

## 1. Main board (`boards/neurband_c`)

28.7 × 27.0 mm, 4 layers, 1.0 mm, ENIG, black mask, top-side SMT only. It has 204 vias at 0.30/0.45 mm and one 0.30 mm plated antenna-short hole.

### 1.1 Fine as-is

**Fab rules**
- **Track and gap.** 4,526 of 4,583 segments are 0.100 mm; the rest are 0.127 mm and 0.160 mm (RF). The copper gap rule is 0.100 mm. The fab's multilayer minimum is 0.09/0.09 mm, so 0.10 mm passes with no surcharge, though it is not "comfortable". In1 has 0 tracks and one GND polygon. In2 has 1,367 tracks plus a GND pour.
- **Vias.** All 204 are 0.30/0.45 mm with a 0.075 mm ring. The fab's surcharge only applies to holes ≤0.25 mm, or 0.2–0.25 mm holes with a pad under 0.45 mm, so these are **no surcharge**. The via rule is pad = hole + 0.10 (0.15 preferred). Via-to-via ≥0.25 mm against the fab's 0.2. Hole-to-copper rule is 0.20 mm against the fab's 0.20 for via hole to track and inner copper.
- **Copper to routed edge.** 0.30 mm on every layer (DRC-enforced; the fab needs ≥0.2). This is not enough at a V-cut; see S4.
- **Solder mask.** `pad_to_mask_clearance` is 0, and the fab's LDI mask has been 1:1 since 2025, so the openings print as drawn. The narrowest dams are 0.150 mm on the LGA-14 and 0.200 mm on the QFN-48, TQFP-64 and FPC-20. Black mask needs **≥0.13 mm** (green 0.10), so all pass. No bottom dam is under 0.2 mm. Vias are tented both sides.
- **Silkscreen.** No footprint silkscreen. 12 board texts, all 0.15 mm stroke and ≥0.5 mm from pads. Text height is 0.8 mm; see S3.
- **Drills and outline.** `PTH.drl` has a single 0.300 mm size: 204 via holes plus 1 component hole (AE1 pad 2). `NPTH.drl` is empty, which is harmless. The outline is closed: 4 lines plus 4 R1 arcs, 28.7 × 27.0.
- **Layers.** All 11 production layers are present: F/In1/In2/B Cu, F/B Mask, F/B Silk, F/B Paste, Edge. The B.Paste layer is empty, as it should be. The job file is present.

**Paste (stencil area ratios, 1:1 apertures)**

| Footprint | Ratio at 0.12 mm stencil | Ratio at 0.10 mm stencil |
|---|---|---|
| QFN 0.2 × 0.8 | 0.69 | 0.82 |
| LGA 0.35 × 0.625 | 0.98 | 1.18 |
| FPC 0.3 × 1.25 | 1.01 | 1.21 |
| TQFP 0.3 × 1.475 | 1.07 | 1.28 |
| Everything else | >1.1 | >1.1 |

All are ≥0.66, so they print.

The **U1 exposed pad is paste-free, with 9 windowpane apertures of 1.24 × 1.24 mm = 63 % coverage**. The fab's guidance is 50–75 %. **No vias are inside the EP**, so there is no in-pad wicking. The one exception is the edge via under M/S2.

**Footprints vs datasheets**
- **J1 (XUNPU FPC-05F-20PH20).** 20 lands of 0.30 × 1.25 mm at 0.50 pitch. Mounting lands are 2.0 × 2.5 mm at x = ±6.44, y = +2.575 (toward the mouth). This matches the drawing's 2.69 / 0.70 / 2.00 / 2.50 / 1.25 / 0.30 dimensions. It is also pad-for-pad identical to the fab's stock footprint (pin 1 left, top view, not mirrored); only the origin differs (see M2).
- **Y1 (32 MHz 2016).** Lands 0.9 × 0.8 at ±0.7 / ±0.55 match the YXC land exactly. Pin 1 is bottom-left, pins 1 and 3 are the crystal, 2 and 4 are GND. The board has pads 1 and 3 on XC2/XC1 and pads 2 and 4 on GND. **Correct.**
- **U5 (LSM6DSL, LGA-14 2.5 × 3).** ST gives 0.25 × 0.475 terminals; the KiCad lands are 0.35 × 0.625 (IPC nominal). Pin 1 is top-left with 4 pins per short side, 3 per long side, and the numbering matches. Nets are SA0 = GND, VDDIO = +3V3, INT1 = /IMU_INT, SDA = pin 14.
- **U1 (nRF52832 QFAA).** The Nordic EP is 4.60 (4.50–4.70) mm, b = 0.20, e = 0.40. The 4.6 × 4.6 EP and 0.2 × 0.8 leads are correct.
  - Note: **the fab's stock footprint for C77540 draws a 3.8 mm EP.** That only affects their preview; do not "fix" the board to it.
- **U2 (ADS1298 PAG).** Pin 1 / 19 / 24 / 28 nets match TI's PAG table: pin 1 = IN8N path, 19 = AVDD, 20 = AVSS, 24 = VREFP, 28 = VCAP1.
- **U3 (XC6206, SOT-23).** The Torex table says **1 = VSS, 2 = VOUT, 3 = VIN**. The board has pad 1 = GND, 2 = +3V3, 3 = VBAT, so it is **correct**. The fab's stock *symbol* says 2 = Vin, 3 = Vout, which is wrong. Ignore it if the fab's engineers query it.
- **U4 (TP4054).** 1 CHRG, 2 GND, 3 BAT, 4 VCC, 5 PROG, matching the board.
- **SW1 (TS-1088-AR02016).** Lands 1.05 × 2.0 on a 4.45 mm pitch (3.40 / 5.50 in the drawing) match exactly.
- **D1.** Cathode (KiCad pad 1) is on /LED, anode through R8 to +3V3, as intended.

**Assembly basics**
- 57 placements, all top. C22 and C23 (DNP) are excluded from the BOM and CPL. AE1, J2, J3 and TP1–TP5 are excluded from assembly.
- Heights: max 2.0 mm (J1, SW1).
- Courtyard DRC is clean. The smallest pad-to-pad gap between parts is 0.31 mm; the fab's minimum is 0.18 for 0402.
- Bottom side is wire, pogo and test pads only: mask openings, no paste.

### 1.2 BOM and stock (live, 2026-10-28)

All 27 BOM lines have an MPN and the fab's part number. The BOM expands to exactly the 57 placed references.

- Stock is ample for 2 or 5 boards. **The lowest is ADS1298IPAGR at 1,765** (alternate: ADS1298IPAG C1520667, tray, 111 in stock, same die and package).
- nRF52832-QFAA-R: 30,049 (alternate NRF52832-QFAA-G-R C3606606, 3,174).
- LSM6DSLTR: 20,243 (fallback LSM6DS3TR-C C967633, 23,554; same footprint and pinout, but different registers, so it needs a firmware change).
- 32 MHz crystal: 88,621 (alternate C2965582, same YXC 2016 / 8 pF / ±10 ppm).
- FPC-05F-20PH20: 106,580. 0.8 pF: 48,880.
- Everything else is ≥48 k.

**The four parts you asked to confirm are the intended parts:**

| Fab part | Part | Check |
|---|---|---|
| C285068 | 0402CG0R8B500NT, 0.8 pF C0G 50 V, **±0.1 pF** | Nordic reference C3 = 0.8 pF NP0 (lists ±5 %). ±0.1 pF is the normal sub-pF grade. A ±0.05 pF part would match the reference more closely, but the π network is there to tune anyway. |
| C14033 | Sunlord SDCL1005C3N9STDF, 3.9 nH multilayer, ±0.3 nH, SRF 4 GHz | Nordic reference L1 = 3.9 nH high-frequency 0402. Equivalent class. |
| C718072 | YXC X201632MKB4SI, 32 MHz, CL 8 pF, ±10 / ±20 ppm, ESR 80 Ω max | nRF52832 allows ESR ≤100 Ω at C0 ≤3 pF and CL ≤12 pF; reference is ±40 ppm total. **OK.** |
| C2856803 | XUNPU FPC-05F-20PH20, 20P 0.5 mm, bottom contact, flip-top, H2.0, 0.3 mm FPC | Exact part. Its contacts are **tin**-plated and the flex is ENIG gold. That mix is common and acceptable for a prototype, not for many mating cycles. |

**Library classes.** 19 basic, 2 preferred (C14033, C32574) and **6 extended**: U1, U2, U5, Y1, J1, C21.

**Prices** (1+ tier, the fab's stock):
- Parts are about **$27.4 per board**. ADS1298 is $19.99, nRF52832 $4.03, LSM6DSL $2.55; the rest total about $0.85.
- **2 boards:** about **$55** of parts, including typical attrition on passives.
- **5 boards:** about **$138**.

**Assembly fees.** These depend on the tier, and **this board cannot use the cheap tier** (see M4).

| Tier | Fees for this order |
|---|---|
| Standard (required) | setup $25.56 + stencil $8.21 + loading $1.53 × 27 unique parts = **$75.08** |
| Economic (not available here) | $8.18 + $1.53 + $3.07 × 6 extended = $28.13 |

On top of Standard come X-ray for the QFN/LGA (up to $1.64 per component) and $0.45 for placement confirmation. `docs/rev_c/cost.md` budgets about $28 (setup + stencil ~$10, extended ~$18). **Budget about $50 more.**

A non-DFM observation for the schematic owner: C6 (VREFP) and C28 are 10 µF 0402 6.3 V X5R parts and lose most of their capacitance at 2.4–3.3 V DC bias.

### 1.3 MUST fix before ordering (order data and settings; no copper change needed)

**M1. Make the raw position export match the fab's rotation convention for U1, U2, U3, U4 and RN1–RN4.**
Backplane's Buy-it flow sends the raw `kicad-cli pcb export pos` output with the columns renamed and nothing else. That was checked in the installed app: its buy-thread instructions, and `kistack/skills/export/scripts/convert_position.py`, which only renames columns. The owner never sees a placement preview. `mfg/20261026-1042/main_board/positions.csv` carries the raw KiCad rotations.

As exported today:
- **U1 and U2 would be placed 90° wrong.**
- U4 90° wrong; U3 180° wrong.
- RN1–RN4 180° wrong. That is electrically harmless (isolated array) but contradicts the fab's pin 1.

The fix is to bake the fab rotation into the footprints: rotate each footprint's internal geometry by −delta and place it at KiCad rotation + delta, so the copper is unchanged (the planned approach). The deltas and evidence are in table 1.4.

Also add silkscreen pin-1 / polarity marks (S3). The fab follows the silkscreen when it disagrees with the CPL (§1.4.4), so the marks protect against any residual error.

**M2. Put J1's placement reference at the centre of its pads: Mid (14.0000, −23.1925), rotation 0.**
- The fab places at the pad centre ("component centroid"; §1.4.2). That centre is **1.600 mm** from the KiCad anchor toward the mouth (board +Y).
- The fab's EDA footprint origin is 1.2875 mm from the anchor, which is 0.3125 mm short of the pad centre.
- Uncorrected (−21.5925), the tails land 1.6 mm off the lands, toward the board centre.
- When baking, move J1's footprint anchor to the pad centre. In the footprint's own frame that is (0, +1.600); on the board it is (14.0, 23.1925).

**M3. Order the 1.0 mm 4-layer "3313" stackup, not the fab's default.**

| Stackup | Prepreg L1–L2 | εr | Core | 0.16 mm feed impedance (Hammerstad, before mask) |
|---|---|---|---|---|
| Fab default "7628" | 0.2104 mm | 4.4 | 0.5 mm | **≈75 Ω** |
| "3313" | 0.0994 mm | 4.1 | 0.7 mm | **≈52.7 Ω** (≈51 Ω with mask) |

The KiCad stackup and `docs/layout/main_c_layout.md` assume 0.100 mm at εr 4.3, which only 3313 matches. The fab lists no extra fee for 3313. `neurband_c.fab.json` has no field for this, so it **must be set in the order**. If the Buy-it flow cannot set it, add it in the order remarks or with the fab's support before production. The fallback is to accept a mismatched feed and retune with the π sites.

**M4. Order Standard PCBA (one side, top). Do not try to force Economic.**
- The fab's Economic table lists 4-layer 1.0 mm with **green mask and HASL only**. This order is black and ENIG, so Economic is not offered.
- Switching fab.json to green + HASL to get Economic is **not recommended**, for two reasons:
  - HASL coplanarity on the 0.4 mm QFN and 0.5 mm LGA.
  - Economic boards without rails get **2–3 tooling holes of 1.152 mm drilled "near the corners … possibly within copper areas"**. On this 28.7 × 27 board the corners hold D1/R8, C30/R7, SW1 and the antenna radiator corner.
- Standard PCBA on a board under 70 × 70 mm gets **5 mm process rails on two sides, attached by V-cut, plus fiducials on the rails**. These are added automatically and priced in the quote, so no board fiducials are needed.
- **Assemble 2 of 5 is allowed** (minimum 2). With fewer assembled than fabricated, keep "accept shortages" below the difference.
- X-ray is applied to the QFN and LGA. Keep it.

### 1.4 Verified CPL table (fab convention for each exact part number)

**Columns**
- **Fab rot**: the rotation the fab needs in the CPL. Counter-clockwise is positive, top view, which is the convention of both the fab and KiCad.
- **Delta**: fab rot − KiCad rot. To bake it in, rotate the footprint's internal geometry by −delta and place the footprint at KiCad rot + delta.
- **Offset**: the vector, in the board frame (x right, y down, mm), from the current KiCad anchor to the fab's placement reference, which is the pad centre. In the CPL, y is negated.
- **Fit**: the largest pad-centre error, in mm, after placing the fab's footprint (its own pad numbers) on the KiCad pads. The value in brackets is the best fit at any other angle.
- **Footprint naming**: "BL", "TL" and "BR" are the fab footprint name suffixes giving the pin-1 corner at 0°.

| Ref | Fab part no. | KiCad footprint | KiCad rot | Fab rot | Delta | Offset (mm, board) | Evidence | Confidence |
|---|---|---|---|---|---|---|---|---|
| U1 | C77540 | QFN-48-1EP_6x6mm_P0.4mm_EP4.6x4.6mm | 180 | 90 | -90 | 0, 0 | Fab QFN-48 "BL": pin 1 bottom-left, pins 1–12 along the bottom. Fit 0.04 mm (≥5.2 at other angles). Symbol 1 = DEC1, 49 = EP. DB A uses 270 for QFN-16…40 (§1.4.3). | High |
| U2 | C527440 | TQFP-64_10x10mm_P0.5mm | 90 | 0 | -90 | 0, 0 | Fab TQFP-64 "BL". Fit 0.11 (≥9.6). Symbol 1 = IN8N, as TI PAG. Community DBs A and B: TQFP 270, agreeing. | High |
| U3 | C5446 | SOT-23-3 | 0 | 180 | +180 | 0, 0 | Fab SOT-23-3 "BR": pins 1–2 in a **vertical** column on the right, pin 3 left. Fit 0.13 (≥2.2). Torex: 1 VSS, 2 VOUT, 3 VIN. | Medium-high |
| U4 | C32574 | SOT-23-5 | 90 | 0 | -90 | 0, 0 | Fab SOT-23-5 "BL": pins 1–3 in a **horizontal** row along the bottom. Fit 0.02 (≥2.37). Symbol 1 CHRG … 5 PROG. | Medium-high |
| U5 | C126672 | LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y | 0 | 0 | 0 | 0, 0 | Fab LGA-14 "TL", same layout as KiCad. Fit 0.10 (≥2.05). Symbol 1 SDO/SA0 … 14 SDA, as ST. | High |
| Y1 | C718072 | Crystal_SMD_2016-4Pin_2.0x1.6mm | 90 | 90 | 0 | 0, 0 | Fab 2016 "BL", same lands as KiCad. Fit 0.000. YXC: pin 1 bottom-left, pins 1/3 = crystal. | High |
| D1 | C2286 | LED_0603_1608Metric | 0 | 0 | 0 | 0, 0 | Fab symbol 1 = A, 2 = K. Fab pad 2 (K, left) carries the "−" mark. KiCad pad 1 = K (left). Fit 0.04 by function; **by pad number it reads 180 = reversed LED.** | High (judged by cathode) |
| J1 | C2856803 | XUNPU_FPC-05F-20PH20 | 0 | 0 | 0 | **0, +1.600** (fab EDA origin: 0, +1.2875) | Fab lands identical. Fit 0.000 (≥6.7). Fab places by pad centre: +1.600 mm (§1.4.2). | High (rotation); medium-high (offset) |
| SW1 | C720477 | SW_SPST_TS-1088-xR020 | 0 | 0 | 0 | 0, 0 | Fab 2-pad, P4.45. Fit 0.04. Non-polar; 180 is equivalent. | High |
| RN1 | C1980 | R_Array_Convex_4x0603 | -90 | 180 | -90 | 0, 0 | Fab 0603×4 "BL": pin 1 bottom-left, pins 1–4 along the bottom. Fit 0.10 with numbering (2.14 at ±90). Community 90 is the same pads with numbering 180° off; electrically equal. | High |
| RN2 | C1980 | R_Array_Convex_4x0603 | -90 | 180 | -90 | 0, 0 | Fab 0603×4 "BL": pin 1 bottom-left, pins 1–4 along the bottom. Fit 0.10 with numbering (2.14 at ±90). Community 90 is the same pads with numbering 180° off; electrically equal. | High |
| RN3 | C1980 | R_Array_Convex_4x0603 | -90 | 180 | -90 | 0, 0 | Fab 0603×4 "BL": pin 1 bottom-left, pins 1–4 along the bottom. Fit 0.10 with numbering (2.14 at ±90). Community 90 is the same pads with numbering 180° off; electrically equal. | High |
| RN4 | C1980 | R_Array_Convex_4x0603 | -90 | 180 | -90 | 0, 0 | Fab 0603×4 "BL": pin 1 bottom-left, pins 1–4 along the bottom. Fit 0.10 with numbering (2.14 at ±90). Community 90 is the same pads with numbering 180° off; electrically equal. | High |
| C1 | C1525 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C2 | C52923 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C3 | C52923 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C4 | C52923 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C5 | C59461 | C_0603_1608Metric | 90 | 90 | 0 | 0, 0 | Fab C0603, pad 1 left at 0°. Fit 0.07 (≥1.04). Non-polar; 180 is equivalent. | High |
| C6 | C15525 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C7 | C52923 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C8 | C1525 | C_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C9 | C1525 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C10 | C52923 | C_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C11 | C1525 | C_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C12 | C1538 | C_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C13 | C1525 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C14 | C1546 | C_0402_1005Metric | 180 | 180 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C15 | C52923 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C16 | C19666 | C_0603_1608Metric | -90 | 270 | 0 | 0, 0 | Fab C0603, pad 1 left at 0°. Fit 0.07 (≥1.04). Non-polar; 180 is equivalent. | High |
| C17 | C1525 | C_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C18 | C1525 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C19 | C1547 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C20 | C1547 | C_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C21 | C285068 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C24 | C52923 | C_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C25 | C19666 | C_0603_1608Metric | 0 | 0 | 0 | 0, 0 | Fab C0603, pad 1 left at 0°. Fit 0.07 (≥1.04). Non-polar; 180 is equivalent. | High |
| C26 | C52923 | C_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C27 | C52923 | C_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C28 | C15525 | C_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C29 | C1525 | C_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C30 | C1525 | C_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C31 | C1525 | C_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| C32 | C52923 | C_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab C0402, pad 1 left at 0°. Fit 0.06 (≥0.64). Non-polar; 180 is equivalent. | High |
| R1 | C26083 | R_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R2 | C25741 | R_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R3 | C17168 | R_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R4 | C25744 | R_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R5 | C25077 | R_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R6 | C26083 | R_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R7 | C26083 | R_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R8 | C11702 | R_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R9 | C25900 | R_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R10 | C25900 | R_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R11 | C25741 | R_0402_1005Metric | -90 | 270 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R12 | C26083 | R_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| R13 | C26083 | R_0402_1005Metric | 90 | 90 | 0 | 0, 0 | Fab R0402, pad 1 left at 0°. Fit 0.08 (≥0.67). Non-polar; 180 is equivalent. | High |
| L1 | C14033 | L_0402_1005Metric | 0 | 0 | 0 | 0, 0 | Fab L0402, pad 1 left at 0°. Fit 0.07 (≥0.64). Non-polar; 180 is equivalent. | High |

C22 and C23 are DNP and are not in the CPL. Their pads still get stencil paste and will carry small solder bumps, which is harmless.

#### 1.4.1 Method and evidence

1. **The fab's own footprint for each exact part number.**
   - For all 27 BOM part numbers, the footprint the fab's library links to the part was downloaded from the fab's EDA library.
   - Its UUID equals the footprint UUID in the fab's part record (parts database, 2026-10-28). That is **27/27 matches**, so these are the footprints the fab uses for these parts, not look-alikes.
   - The fab states that its 0° is "the component orientation in the packaging (tape/reel)" and that positive rotation is counter-clockwise. The linked footprint is how the fab draws that 0°, and the fab's own EDA tool exports this footprint's rotation directly as the CPL rotation, which is why its users need no correction table.
2. **Pad-by-pad fit at 0/90/180/270°.** Each fab footprint was fitted, using its own pad numbers, onto the KiCad pads at the current placement. For every polarized part, one angle fits within 0.00–0.13 mm and every other angle misses by at least 2 mm (5–13 mm for the quads). The pad-size difference between the libraries explains the small residuals.
3. **Pad numbers mean the same pins in both libraries.**
   - The fab's symbol pinouts were checked: nRF52832 1 = DEC1, 49 = EP; ADS1298 1 = IN8N … 64 = WCT; LSM6DSL 1 SDO/SA0 … 14 SDA; TP4054 1 CHRG … 5 PROG; crystal 1/3 = crystal, 2/4 = GND; FPC 1–20 plus 21/22 mounting.
   - These match the datasheets, so a pad-number match is a pin match.
   - **The single exception is the LED.** The fab numbers pad 1 = anode, while KiCad numbers pad 1 = cathode. D1 was therefore fitted by function, and the fab's footprint marks its left pad (pad 2, K) "−" and its right pad "+".
   - The XC6206's fab symbol has VIN and VOUT names swapped against the Torex table (1 VSS, 2 VOUT, 3 VIN). That does not affect placement, which follows the package pin numbers, and the board follows Torex.
4. **Visual check.** Overlay renders of the fab footprint at the derived rotation on the KiCad pads were inspected for U1, U2, U3, U4, U5, Y1, D1, J1, RN1 and SW1. The numbers coincide pad for pad; the only visible difference is the fab's 3.8 mm thermal pad drawing inside the 4.6 mm KiCad pad on U1.

#### 1.4.2 Which point is "Mid X / Mid Y"? (J1 only)

The fab specifies "Mid X/Mid Y = the X/Y coordinate of the component centroid". Two sources support the pad centre over the drawing origin:
- The fab's own EDA tool defines its "Mid X, Mid Y" CPL columns as **"the center coordinate of the footprint pads"** (with "Ref X/Y" as the footprint origin).
- The most widely used KiCad plugin for this fab (Bouni's plugin) writes the **centre of the bounding box of all soldered pads** for every footprint.

For **every part except J1**, the KiCad anchor, the KiCad pad-box centre, the fab origin and the fab pad-box centre all coincide (≤0.005 mm). The raw export is therefore right for them.

For J1:

| Point | Distance from the signal row toward the mouth |
|---|---|
| KiCad anchor | 0 (it is the signal row) |
| Fab EDA origin | 1.2875 mm |
| Pad-box centre (signal lands y −0.625 … mounting lands +3.825; the same point in both libraries) | **1.600 mm** |

Use the pad centre. If the fab used its drawing origin instead, the error would be 0.31 mm along the 1.25 mm lead axis, still on the lands. Using the drawing origin when the fab places by pad centre would be the same 0.31 mm the other way. The evidence favours the pad centre.

#### 1.4.3 Why this disagrees in places with community rotation databases

Pattern databases key on the KiCad footprint *name*. The fab's 0° belongs to the *part number*, and different part numbers in the same package are drawn differently. Fetched 2026-10-28:

| Database | SOT-23 | QFN | TQFP | R_Array_Convex |
|---|---|---|---|---|
| A: matthewlai's KiCad fab tools `cpl_rotations_db.csv` (also the default download of Bouni's plugin) | **−90** (regex `^SOT-23`, so it covers SOT-23-3 and -5) | 270, but only QFN-16/20/24/28/40 (**QFN-48 gets 0**) | 270 | 90 |
| B: bennymeg Fabrication-Toolkit `transformations.csv` | **180** | **90** | 270 | 90 |

All are added to the KiCad rotation. The coordinator's recollection (SOT-23 180, QFN 270, TQFP 270, arrays 90) mixes the two. Resolved per part:

- **U2 (TQFP-64, C527440).** Fab footprint "BL" → +270 ≡ −90. **A and B agree with this result.**
- **U1 (QFN-48, C77540).** Fab footprint "BL" → −90 ≡ +270, the same value A uses for smaller QFNs.
  - A applies 0 to QFN-48 (pattern gap), which would leave U1 90° wrong.
  - B's 90 would be 180° wrong.
  - Note that the fab also has a separate assembly-only catalogue entry for nRF52832 that uses a "TL" EP4.6 footprint. If the fab ever substituted it, a different delta would apply. The BOM part C77540 links to the "BL" footprint, which is one more reason to add the pin-1 silkscreen dot.
- **U3 (SOT-23-3, C5446).** The fab draws this part with pins 1–2 in a **vertical** column (pin 1 bottom-right), so only 180 fits (0.13 mm). A −90 or +90 would turn the rows horizontal: 2.2 mm misfit, geometrically impossible. **B (180) is right; A (−90) is wrong for this part.**
- **U4 (SOT-23-5, C32574).** The fab draws this one with pins 1–3 in a **horizontal** row at the bottom, so only −90 fits (0.02 mm). **A (−90) is right; B (180) is wrong** (2.37 mm misfit).
  - The two SOT-23s on this board need different corrections, which a name pattern cannot express. Bouni's plugin added per-part-number corrections for exactly this reason: "two parts on one footprint name can need different rotations".
- **RN1–RN4 (C1980).** A and B (90) give the same pad outline as this result (−90), with the pin numbers rotated 180°.
  - For this isolated array (resistors 1–8, 2–7, 3–6, 4–5) that is electrically identical.
  - −90 is used because it is the only angle at which the fab's pin 1 sits on KiCad pin 1. That matters if pin-1 silkscreen marks are added, since the fab follows the silkscreen.
- **LED, crystal, LSM6DSL, TS-1088 switch, 0402/0603 parts.** No database entry (0). This result is also 0, so they agree.

#### 1.4.4 Do the fab's engineers fix rotations? Can the order server double-correct?

**The fab's engineers.** The fab's assembly FAQ (part 2) says its engineers "will review and fix the rotation and polarity of the components based on the silkscreen markings before assembly". It also says: "When there is a mark point in the silkscreen layer, but it is inconsistent with your CPL file … we will make the placement according to the silkscreen layer by default."

So with clear pin-1 / polarity silkscreen marks, a wrong CPL rotation is plausibly caught and corrected, because **the silkscreen wins**. Without marks, as on this board today, the engineers have only the CPL and their footprint. Two consequences:
- Add pin-1 dots next to pin 1, outside the body: U1, U2, U3, U4, U5, Y1 (pin 1 = XC2 corner) and RN1–RN4 (at the fab pin 1 per the table). Add a cathode bar for D1.
- A wrong mark is worse than none.

**Double correction.**
- **Locally, no.** Backplane's installed client applies no rotation database. The buy thread exports `kicad-cli pcb export pos` and its converter only renames columns.
- **The order server could not be inspected from here.** Before baking the corrections into the footprints, get Backplane to confirm that the server passes positions to the fab unmodified. If the server applied a name-pattern database on top of the baked rotations, parts would come out wrong again:
  - With A: U2 → 270, U3 → 90, U4 → 270 (U1 unaffected).
  - With B: U1 → 180, U2 → 270, U3 → 0, U4 → 270.
  - In both cases RN1–RN4 → 270.
- Baking plus correct silkscreen marks is robust either way, because the fab places by the silkscreen when the two disagree.

#### 1.4.5 When baking the corrections

- Footprints that change: U1, U2, U3, U4, RN1–RN4 (rotation) and J1 (anchor). All the others have delta 0 and offset 0 and should stay as they are.
- The KiCad standard library footprints must be copied to local, fab-oriented variants. Rotate the 3D model offset and rotation with the geometry. Expect the `lib_footprint_mismatch` warnings to change.
- After the edit, re-run the same fit. **Every part must then show delta 0 and offset 0**, and the exported positions must read U1 90, U2 0, U3 180, U4 0, RN1–RN4 180, and J1 (14.0000, −23.1925).
- Copper, mask and paste Gerbers must be byte-identical to before (apart from headers).

### 1.5 SHOULD (recommended now if cheap, otherwise in the planned re-layout)

**S1. Tombstoning: solid pour connections on 32 two-terminal parts.**
Every GND zone uses `connect_pads yes` (solid, no thermal spokes). 32 placed passives (29 × 0402, 3 × 0603) have their GND pad fully merged into the F.Cu pour plus In1, while the other pad is fed by a 0.10 mm track:
- C1–C11, C13–C20, C24–C32 (excluding the DNP parts)
- R4, R7, R11, R13

This asymmetry is the classic cause of 0402 tombstoning. In the re-layout, give SMD pads on the F.Cu GND pour **thermal reliefs** (gap 0.15–0.20, spoke 0.20–0.25, ≥2 spokes). Keep U1 pad 49 solid (it already has its own `zone_connect 2`). Keep RF and decoupling returns short with a via at the pad.

Until then, accept the risk and inspect the first articles. 0402 rework is easy by hand.

**S2. Vias touching SMD pads (tented 0.30 mm holes).**
- There are 82 top-side via/pad copper contacts on 44 footprints, every RN pad among them. In each, the hole edge sits only **0.04–0.075 mm** outside the pad's mask opening.
- 29 more via/pad pairs are 0.025–0.09 mm apart, leaving a mask sliver under 0.1 mm. 26 of them are on U2: ADS1298 toe fanout, mostly 0.037 mm.
- With the 1:1 LDI mask the holes should stay tented, but the tent web is marginal there, and the fab's ink plugging is not allowed within 0.35 mm of a mask opening.
- **U1 pad 49 / pin 31 GND via at (6.65, 5.90):** 29 % of its drill lies inside the EP mask opening, so it is a partly open via at the EP edge and will wick a little EP solder. That is acceptable for a prototype. It sits in the 0.25 mm gap between pin 31's toe and the EP, so it cannot simply move. Either the RF owner relocates C21's ground return, or the fab plugs that via (epoxy filled & capped, a paid option on 4-layer; give the via in the remarks).
- TP2 and TP3: drills inside the bottom pogo pads. Fine; that side is never soldered.

Rule for the re-layout: `physical_hole_clearance ≥ 0.20 mm` between via holes and SMD pads (same net included). That leaves at least a 0.125 mm mask web.

**S3. Silkscreen.**
- Add pin-1 / polarity marks for U1, U2, U3, U4, U5, Y1, D1 (cathode bar) and RN1–RN4. The fab uses them to catch CPL rotation errors, and they help rework.
- Raise texts from 0.8 mm to **≥1.0 mm** height (the fab's minimum; 0.15 mm stroke is OK).
- Choose where the fab's order-number text goes (a "specify location" placeholder on the bottom, clear of pads), or pay to remove it.

**S4. V-cut rails vs the 0.30 mm edge clearance.**
The fab's auto rails are V-cut, and V-cut needs **copper ≥0.4 mm**. Every GND pour, on all four layers and all four edges, is exactly 0.30 mm from the edge. Parts close to the edges:

| Edge | Parts and distance |
|---|---|
| Top | R6, R7, R9, R10, C30 at **0.48 mm** |
| Bottom | J1 mouth **flush** |
| Right | C1/C2/C4/C6/C7 at 1.02 mm |
| Left | DNP C22/C23 at 0.34 mm; antenna |

For now, if the order allows a remark: "rails on the x = 0 and x = 28.7 edges only, not on the J1 (y = 27) or top edges". Snap the rails with even pressure or cut them, because MLCCs sit close to the score. For the next layout, set zone-to-edge clearance to **0.5 mm** and keep pads ≥0.5 mm from the rail edges.

Housing fit: V-cut edges hold ±0.4 mm against ±0.2 mm for routed edges, so allow it in the 28.7 × 27 pocket or deburr.

**S5. Update the KiCad stackup to the ordered 3313 build** (prepreg 0.0994 / εr 4.1, core 0.70, inner Cu 0.0152, mask εr 3.8). This is for record consistency; the 0.16 mm feed stays valid.

**S6. AE1 pad 2 annular ring.** This plated hole (0.30 mm drill in a 0.5 × 0.9 mm pad) is exported as a component drill. Its annular ring is 0.10 mm on the narrow side, against the fab's 0.15 mm multilayer PTH minimum. If the fab's DFM queries it, answer "treat as a via". Otherwise widen the pad to 0.6 mm.

**S7. Rework spacing (informational).** The fab *recommends* ≥1.0 mm QFN/LGA-to-passive and ≥1.25 mm QFP-to-passive. U1 has caps at 0.43 mm and U2 at 0.40 mm. This is only a rework-access concern.

### 1.6 Rules the changed layout must respect

For the coming input filter caps, stitching and possible antenna change:

1. Track/gap ≥0.10 mm (0.127 mm preferred where room allows).
2. Vias 0.30/0.45 mm only. Hole-to-other-copper ≥0.20 mm. Via-to-via ≥0.25 mm.
3. Mask dams ≥0.13 mm (black). Keep `pad_to_mask_clearance 0`. Add a KiCad `solder_mask_sliver` constraint of 0.13 mm.
4. Via hole ≥0.20 mm from any SMD pad (S2), or in-pad and filled & capped.
5. Thermal reliefs on SMD pads in the pours (S1).
6. Pours ≥0.5 mm from the edge (S4).
7. Silk ≥1.0 mm text / 0.15 mm stroke, plus pin-1 marks.
8. Keep the RF feed on the L1–L2 0.0994 mm dielectric with continuous In1 GND.
9. Re-run the CPL rotation/offset fit for any new or changed footprint. Any new 0402/0603 from the standard KiCad library has zero correction; quads and SOT-23s do not.
10. After the change, re-run DRC with `--refill-zones` and check the fills are saved before export.

---

## 2. Electrode flex (`boards/neurband_c_flex`)

2-layer polyimide flex, 133.1 × 38.5 mm (one closed outline, 2,458.2 mm²), not assembled. It has 60 vias at 0.30/0.55 mm, 16 NPTH holes of 1.2 mm, 24 round 6.5 mm electrodes, and a 20-finger tail.

### 2.1 Fine as-is

**Fab rules**
- Tracks are 0.10/0.10 mm against the fab's flex minimum of 3/3 mil (12 µm) or 3.5/3.5 mil (18 µm Cu). There is one 0.20 mm bias bus.
- Vias 0.30/0.55 mm are the fab's **regular** flex via, so no surcharge.
- Copper-to-edge ≥0.30 mm everywhere, which equals the fab's flex 0.30 rule. The fingers sit 0.30 mm from the tip and 0.35 mm from the sides; the fab's gold-finger minimum is ≥0.20.
- NPTH-to-copper is 0.20 mm, equal to the fab's ≥0.20.
- Size is well inside the fab's 234 × 490 mm flex panel, so 133 mm is fine and no panelization is needed.
- No vias in the free tail beyond Y = +15. No F.Cu in the tab or stiffener region (y > 54).

**Tab geometry vs the connector drawing**
- Width **10.500 mm** from y = 51.0 to 58.2. R0.3 leading corners.
- Finger pitch 0.50, width 0.30, outer finger centres 0.50 from the edges.
- Fingers run y = 55.0–58.2 (3.2 mm exposed; the drawing asks ≥3.0).
- One B-side coverlay window, 10.5 × 3.55 mm (y 54.95 to the tip), with no paste.
- The GND hatch ends at y = 54.8, before the window.
- Pin 1 is at +4.75 (native (69.75, 56.60)), matching the main J1 pin 1 through the no-twist U-turn (`docs/layout/flex_c_layout.md`).

**Fills and silk**
- Fills current; DRC clean.
- Silk is 0.15 mm stroke, 0.8 mm text. Legibility only.

### 2.2 The fab's flex capabilities that matter, and the ±0.03 mm question

**Outline.** Laser-cut flex outlines hold **±0.1 mm standard, ±0.05 mm on request** (extra cost). The connector drawing asks 10.50 ±0.03 mm. Is the risk real?

- **Oversize.** The flip-lock's mouth is (N−1)·0.5 + 1.10 = **10.60 mm**, so a tab up to about +0.10 mm still enters, if snugly. More would jam.
- **Undersize.** At −0.10 mm the tab floats ±0.10 mm sideways. Add about ±0.05 mm copper-to-outline registration, and a contact can land up to about 0.15 mm off the centre of a 0.30 mm finger. That is still on the finger, with 0.20 mm gap to the neighbour.

So the risk is modest, not zero: a loose fit or edge-of-finger contact at the extreme, not shorts. **Request ±0.05 mm on the outline if the surcharge is small; otherwise accept ±0.1 mm and qualify the first article** (insertion, continuity of all 20 contacts, and a wiggle test).

**Thickness.** The fab holds the gold-finger region to **±0.03 mm**, which matches the connector's 0.30 ±0.03.

**Coverlay**
- 0.1 mm per side expansion is the fab's default.
- Coverlay opening to trace ≥0.15 mm. Minimum coverlay bridge 0.5 mm, met everywhere. Windows ≤20 mm long, met.
- Registration is about ±0.1–0.15 mm. The fab does not publish this in its spec table.

**Finish:** ENIG only, 1 or 2 µ" gold. **Copper type** (rolled-annealed or electro-deposited) cannot be selected.

**PI stiffener thicknesses offered:** 0.10 / 0.15 / 0.20 / 0.225 / 0.25 mm. Stiffeners must be drawn as an outline on a dedicated Gerber layer and named in the remarks.

### 2.3 MUST before ordering

**F1. Do not let it be ordered as a rigid board.**
`neurband_c_flex.fab.json` says `kind pcb`, 2 layers, `thickness_mm 0.4`, ENIG, with nothing that marks it as flex, coverlay or stiffener. That describes a 0.4 mm FR-4 2-layer board, and 0.4 mm is not one of the fab's flex thicknesses (2-layer flex is **0.11 / 0.12 / 0.2 mm**). The previous order review recorded "flex quoted separately". Make sure it really goes through the fab's **flex** service with the options in section 2.5. If the Buy-it flow cannot express flex, order it there by hand.

**F2. Stiffener thickness: about 0.225 mm PI, not "about 0.201 mm".**
`docs/layout/flex_c_layout.md` and `docs/review/sol_preorder_review.md` compute 0.30 − 0.099. But at the fingers **the B-side coverlay is opened and there is no F-side copper**. The fab's own method is gold-finger total = FPC − one coverlay − one copper + stiffener:
- **0.11 mm** build: 0.11 − 0.0275 − 0.012 = 0.0705, then add the stiffener:
  - **0.225 mm PI → ≈0.296 mm** total (recommended).
  - 0.25 mm PI → ≈0.321 mm total. The fab's calculator rounds up to this for the same case; it is still inside ±0.03, but tight.
- On the **0.12 mm** build, 0.225 mm PI gives ≈0.306 mm.

In the order, specify **"total thickness at gold fingers 0.30 ±0.03 mm; PI stiffener 0.225 mm (or as needed to reach it)"**.

**F3. Name the stiffener layer.**
The stiffener exists only as a 4-line rectangle on User.2 (y 54.8–58.5, 10.5 × 3.7) plus a text label. A default `--board-plot-params` export does **not** output User.2. The Buy-it export in `mfg/20261026-1042/electrode_flex/gerbers/` did include `neurband_c_flex-User_2.gbr`. Either way, the fab ignores unnamed user layers. Send User_2 and state in the remarks that it is the **F-side PI stiffener, 0.225 mm, on the side opposite the exposed fingers**. Ideally also make the outline a filled polygon in the generator.

### 2.4 SHOULD

**FS1. The stiffener barely overlaps the coverlay edge.**

| Feature | y |
|---|---|
| Stiffener edge | 54.80 |
| GND hatch ends | 54.80 |
| B coverlay window opens | 54.95 |
| Fingers start | 55.00 |

That is only 0.15 mm of overlap. After the fab's 0.1 mm coverlay expansion and ±0.1–0.15 mm registration, plus stiffener placement tolerance, **the coverlay termination can land in the unsupported tail**. That is exactly where the U-turn starts, and it becomes a crack point on the finger traces. Usual flex practice is a stiffener that overlaps the coverlay edge by ≥0.5–1.0 mm; the fab publishes no figure.

Options:
- Lengthen the stiffener toward the root by 0.5–1.0 mm (3.7 → 4.2–4.7 mm). This cuts the free tail from 4.8 mm to 4.3–3.8 mm, against the R1 bend's ~3.14 mm developed length. The mechanical owner decides.
- Or lengthen the tail by the same amount.
- Also end the hatch a little away from the stiffener line, so the two transitions do not coincide.

**FS2. Alignment-hole coverlay openings.**
The 16 NPTH holes carry `*.Mask`, so the coverlay gets a 1.2 mm opening at each. 24 signal traces run **0.20 mm** from these hole edges. After the fab's 0.1 mm expansion that is 0.10 mm, under its ≥0.15 mm opening-to-trace rule, so electrode traces can be exposed at the pin holes on the skin side. Remove the mask layers from `Alignment_D1.2mm` in `gen_flex_c_pcb.py`, so the holes are drilled through the coverlay. Or write in the remarks: "NPTH holes drilled through coverlay, no coverlay pre-opening".

**FS3. Electrode openings.** The closest other-net trace is E1P at 0.25 mm from E1B. After the 0.1 mm expansion that is 0.15 mm, exactly at the limit. Either allow the expansion, or ask for the coverlay openings 1:1 as drawn.

**FS4. Other options.** ENIG **2 µ"** (contacts and skin electrodes). Yellow coverlay (the fab's recommended colour). Copper type cannot be chosen; the wrist links between pods will flex repeatedly, so watch them in use.

### 2.5 Order notes to paste for the flex

> 2-layer polyimide FPC, 25 µm PI, finished 0.11 mm. Coverlay both sides (yellow), openings per F_Mask (24 round electrodes) and B_Mask (finger window). ENIG 2 µ" on all exposed copper. Laser-cut outline; tail width 10.50 mm, please hold ±0.05 mm on the tail (`Edge_Cuts`). **Stiffener: PI 0.225 mm on the F (top) side, area per layer User_2 (10.5 × 3.7 mm at the tail tip), on the side opposite the exposed B-side gold fingers. Total thickness at the gold fingers 0.30 ±0.03 mm.** 16 × 1.2 mm NPTH holes: drill through the coverlay, no coverlay pre-opening needed. No assembly. Qty 5.

---

## 3. fab.json files

| File | Features | Options | Verdict |
|---|---|---|---|
| `boards/neurband_c/neurband_c.fab.json` | width 28.7, height 27.0, min_drill 0.3, all **measured and current** (outline 28.700 × 27.000; every hole 0.300) | 4 layers, 1.0 mm, black, ENIG, qty 5 (the manifest assembles 2): correct | No field for **stackup 3313 (M3)** or Standard PCBA / rails (M4). These must be set in the order. |
| `boards/neurband_c_flex/neurband_c_flex.fab.json` | width 133.1, height 38.5, min_drill 0.3 (vias; NPTH 1.2): **measured and current** | 2 layers, ENIG: right. `thickness_mm 0.4` is **wrong for a flex**; use 0.11. No flex/coverlay/stiffener expression. | **F1**: as written it describes a rigid board. |

## 4. Gerber and drill sanity

Exports on copies match `mfg/20261026-1042/`.

| | Main | Flex |
|---|---|---|
| Copper | 4 (F, In1 GND plane with 0 tracks, In2 GND + routing, B) | 2 |
| Mask / paste | F/B mask; F paste (297 apertures, including DNP C22/C23); B paste empty | F/B mask (coverlay); no paste |
| Silk | F/B (texts only) | F/B (21 texts) |
| Outline | closed, 28.7 × 27.0, R1 corners | closed, 133.1 × 38.5 |
| Drills | PTH 0.300 × 205 (204 vias + AE1 short); NPTH empty | PTH 0.300 × 60; NPTH 1.200 × 16 |
| Extra layers in the Buy-it set | User_1–4, Eco1/2, Comments, Drawings, Margin, Adhesive, Fab, Courtyard (all empty or documentation) | User_1 (note), **User_2 (stiffener, needed)** |

For the main board, send only the production layers listed above plus Edge and the drills, to avoid CAM questions. For the flex, send the same plus User_2 named as the stiffener.

---

## Summary: MUST / SHOULD (2026-10-28 original review; see the re-check at the top for current status)

**MUST (before ordering)**

*Main board*
- **M1** Make the raw position export carry the fab rotations: U1 180 → **90**, U2 90 → **0**, U3 0 → **180**, U4 90 → **0**, RN1–RN4 −90 → **180** (deltas −90 / −90 / 180 / −90 / −90; all other parts 0). Bake them into fab-oriented footprints. Confirm with Backplane that the order server applies no rotation database of its own. Add pin-1 silkscreen, which the fab follows when it conflicts with the CPL.
- **M2** J1 placement reference at the **pad centre**: Mid (14.0000, **−23.1925**), i.e. the anchor moves 1.600 mm toward the mouth (the fab's EDA origin is at 1.2875 mm). Rotation 0.
- **M3** Order the **1.0 mm 4-layer "3313" stackup** (0.0994 mm prepreg). The default 7628 makes the 0.16 mm RF feed ≈75 Ω instead of ≈51 Ω.
- **M4** Order **Standard PCBA** (Economic does not allow black/ENIG on 4-layer, and drills tooling holes into the board). The fab adds V-cut rails and fiducials automatically. Assemble 2 of 5. Budget about $75 in assembly fees, about $50 over `docs/rev_c/cost.md`.

*Flex*
- **F1** Order it through the fab's **flex** service (2-layer PI, 0.11 mm, coverlay both sides, ENIG), not as the rigid 0.4 mm board `neurband_c_flex.fab.json` describes.
- **F2** PI stiffener **0.225 mm**, F side; specify "0.30 ±0.03 mm total at the gold fingers". The documented "~0.201 mm" ignores the opened B coverlay.
- **F3** Send **User_2** and name it as the stiffener layer in the remarks.

**SHOULD (now if cheap, otherwise in the planned re-layout)**

*Main board*
- **S1** Thermal reliefs on SMD pads in the GND pours: 32 passives are tied solidly on one side, a tombstoning risk. Keep the U1 EP solid.
- **S2** Via holes ≥0.20 mm from SMD pads. 82 via/pad contacts, plus 29 pairs within 0.1 mm. The U1 EP-edge via at (6.65, 5.90) is partly open; plug it or move it.
- **S3** Pin-1 / polarity silkscreen: effectively part of M1, since the fab follows the silkscreen. Text ≥1.0 mm. Place or remove the fab's order number.
- **S4** Pours ≥0.5 mm from the edges (V-cut rails need ≥0.4). Ask for rails on the x = 0 / x = 28.7 edges. Snap the rails gently. Allow ±0.4 mm on V-cut edges in the housing.
- **S5** Update the KiCad stackup to the ordered 3313 build.
- **S6** AE1 pad 2 annular ring of 0.10 mm (answer "treat as a via", or widen the pad to 0.6 mm).
- **S7** Informational: U1/U2 neighbours are closer than the fab's recommended rework spacing.

*Flex*
- **FS1** Lengthen the stiffener 0.5–1.0 mm toward the root so it overlaps the coverlay edge (currently 0.15 mm), or lengthen the tail. Mechanical owner's call.
- **FS2** Drop the coverlay openings at the 16 alignment holes (traces 0.20 mm from the hole edges), or note "drill through coverlay".
- **FS3** Allow the fab's coverlay expansion at the electrodes (E1P 0.25 mm from E1B).
- **FS4** ENIG 2 µ"; request ±0.05 mm on the tail outline if cheap, otherwise qualify the first article.
