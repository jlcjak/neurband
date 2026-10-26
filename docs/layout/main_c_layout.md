# Main board REV C as-built layout

Canonical PCB: `boards/neurband_c/neurband_c.kicad_pcb`. Placement source: `boards/neurband_c/layout/place_c.py`, dictionary `P` (67 positions). All coordinates and heights below are **mm**; top view, origin at the upper-left outline corner (0,0), +X right, +Y down. Bottom pad coordinates use this same frame, not a second mirror. Final saved-board native checks after the last J3 move report **0 DRC errors, 0 unconnected, and 0 schematic-parity issues**.

## Outline, construction and manufacturing tradeoff

The outline is **28.7 × 27, four R1 corners**. The original ≤28 × 24 target was not achieved; the integration owner accepted 28 × 27, then the extra 0.7 mm on the right to retain standard **0.30 drill / 0.45 copper-diameter through-vias** rather than paying for small drills. No blind/buried vias or HDI are specified. All assembled components are **TOP only**; the bottom contains wire/pogo pads, not assembled packages. Bottom copper routing is not prohibited by one-side assembly.

| Stack, top to bottom | Nominal thickness / material |
|---|---|
| Top soldermask | 0.010, black |
| F.Cu | 0.035 copper |
| L1–L2 dielectric | 0.100 FR-4, Er 4.3 |
| In1.Cu (L2) | 0.035 copper, GND reference |
| L2–L3 dielectric | 0.640 FR-4, Er 4.3 |
| In2.Cu (L3) | 0.035 copper |
| L3–L4 dielectric | 0.100 FR-4, Er 4.3 |
| B.Cu | 0.035 copper |
| Bottom soldermask | 0.010, black |

Copper plus dielectric is **0.980 mm**; two 0.010 mm mask layers make the native finished stack **1.000 mm**, confirmed by the CLI statistics export. The inner core was reduced from the initial 0.660 to 0.640 mm to account for mask rather than exporting an invalid 1.020 mm fabrication option. The RF reference spacing remains 0.100 mm. ENIG is the intended finish. These nominal inputs are not a fabricator-approved impedance stackup. L2 is reserved for GND, with **no signal tracks**; read-only native IPC inspection confirmed **one filled L2 polygon and zero L2 tracks**. The Nordic matching and antenna exclusions intentionally remove the plane rather than filling it for apparent continuity.

Routing limits: minimum top track **0.100**, ordinary local track **0.127**, nominal RF feed **0.160**, ordinary copper gap **0.100**, through-vias **0.30/0.45**, copper-to-edge **0.300**. RF separation has additional requirements below; 0.100 clearance alone is not the RF prescription. Standard drill size, conventional paste apertures and one-side assembly are cost-oriented choices, not a manufacturing quote. The $200–250 whole-prototype target remains a purchasing target, not a checked price or stock commitment.

## RF implementation and exclusions

AE1 is the printed TI SWRA117D IFA at **(5.9,14.7), rotation 90°**. Feed pad 1 is **(5.9,14.7)**; ground-short pad 2 is **(5.9,12.6)**. The enforced radiator exclusion is **x=0..5.65, y=11.65..27 on every copper layer**. No unrelated copper, tracks, vias, battery, wires, fasteners or other metal may occupy the antenna region. The antenna itself and deliberate feed/ground-short connections are the functional exceptions. Preserve a genuine right-side GND connection at the short; do not isolate it inside a blanket keepout.

This implemented radiator exclusion is distinct from the larger rotated stock courtyard **x=0.30..6.25, y=11.50..27.00** discussed in [RF geometry](../../boards/neurband_c/layout/rf_geometry.md). The geometry report's courtyard-wide proposed exclusion is not a claim that the native radiator rule area covers that entire courtyard. Feed and short sit on the connection side of the **x=5.65** plane boundary.

The intended path is **nRF ANT → Nordic C21/L1 match → pi tuning sites → IFA**. C21's ground must route explicitly through **U1 VSS pin 31 only before the plane via at (6.65,5.9)**, not via an independent nearby ground shortcut. Keep the Nordic matching-section inner-layer exclusion; that short unreferenced section is not uniform microstrip.

For the post-match L1-to-pi-to-IFA feed, **0.160 covered width** is the nominal approximately 50-ohm prescription from the linked RF calculation: 35 µm copper, 100 µm dielectric to L2, Er 4.3 and 10 µm mask (assumed mask Er 3.3). The calculation asks for unrelated top copper at least **0.50 edge-to-edge** from the uniform feed and continuous L2 below it, outside the intentional RF exclusions. Component launches, reference-plane transitions, and the antenna feed/short are discontinuities, not certified uniform sections. In particular, the feed approaches a **finite plane edge** near the antenna; the ideal cross-section calculation cannot certify that transition or the actual antenna match.

This is **not fab-confirmed controlled impedance** and not RF sign-off. Obtain pressed-stack/finished-width confirmation for an impedance order and tune/measure the assembled antenna with the actual battery, enclosure, flex and body loading. Published TI reference performance does not automatically transfer to this smaller 1 mm four-layer board.

Seven deliberate counterpoise stitches are at **x=6.0, y=13.4/16.2/18.2/20.2/22.2/24.2/26.2**, using ordinary 0.30/0.45 vias. They remain outside the radiator exclusion and at least 0.50 mm copper-edge spacing from the uniform RF feed.


## Housing supports and bottom access

Four native bottom support exclusion discs have **R=1.5**, centred at:

- (1.6,1.6)
- (26.4,1.6)
- (1.6,25.4)
- (26.6,22.6)

Bottom copper pours, tracks, vias and pads are excluded from these seats; the rules apply to **B.Cu**, not the top components or the L2 reference plane. Preserve the listed connector/wire/test-pad locations when implementing the housing; do not solve support interference by moving an electrical interface. Supports must carry the PCB without bending it against the wrist curve and must not obstruct the antenna or bottom service pads.

## J1 electrode flex connector

**XUNPU FPC-05F-20PH20**, 20 contacts at 0.5 pitch, bottom-contact, closed lever; TOP origin **(14,21.5925), 0°**. Signal pin n is `(9.25 + 0.5*(n−1),21.5925)`: pin 1 **(9.25,21.5925)**, pin 20 **(18.75,21.5925)**. These are drawing-backed land centres, not body-centre coordinates.

The closed housing is **14.4 wide × 5.12 deep × 2.0 high**, body envelope **x=6.8..21.2, y=21.88..27.0**. The mouth is the **+Y edge at 27.0**; the cable enters toward −Y with exposed contacts facing down toward the PCB and stiffener on the opposite face. Do not mirror the top-side footprint. Body Y registration is inferred from secondary footprint artwork, **not certified metrology**; the authoritative drawing fixes the lands and overall body dimensions. See [J1 review, saved drawing and footprint evidence](../../boards/neurband_c/layout/j1_review.md).

The current visual STEP measures overall 14.4 × 5.8875 including lands, with physical solids Z=0.02..2.0; this is not the same as the housing-only 5.12 depth. A 2.0 closed height does **not** specify the open actuator sweep or required finger/tool access. Reserve access above and forward of J1 and cable exit space beyond y=27; the drawing does not quantify the open service envelope.

Assembly frame contract from the integration owner: the distal-wall U-turn preserves `X_world`, while main-board top-view X and flex F-side-view X have opposite world signs. Therefore the **main J1 pin 1 stays LEFT in PCB top view; flex pin 1 must be RIGHT in its F-side KiCad view**. The flex owner was asked to mirror the finger order for this no-axial-twist mating arrangement. This is a cross-project mating requirement, not a reason to mirror this manufacturer's connector footprint.


## Other interfaces and height planning

| Reference | Side / centre / rotation | Height above TOP / role |
|---|---|---|
| U1 nRF52832 | TOP (9,5.7), 180° | Simplified visual model 0.905; reserve 1.0 |
| U2 ADS1298 | TOP (20.2,10.1), 90° | Stock TQFP model 1.1; reserve 1.2; 12 × 12 toe span |
| U3 LDO | TOP (8.6,18.95), 0° | Outside current cell footprint |
| U4 charger | TOP (8.6,15.2), 90° | Outside current cell footprint |
| U5 LSM6DSL | TOP (24.5,21.6), 0° | Model height 0.78 |
| SW1 | TOP (24.8,25.1), 0° | Model 5 × 3, height **2.0**; preserve user access |
| D1 | TOP (2,1), 0° | Model 1.6 × 0.8, height **1.1** |
| J2 battery pads | BOTTOM origin (23.9,25.6), 0° | VBAT **(23.9,25.6)**; GND **(26.9,25.6)** |
| J3 charge pads | BOTTOM origin (14,6), 270° | VCHG **(14,6)**; GND **(14,9)** |

Final mechanical interface update: J3 moved **3 mm toward y=0** to keep the charge window clear of the flex spine. Its bottom legends moved with it. Native before/after position comparison confirmed **all 66 other footprint placements unchanged**; the four bottom support exclusions remain intact. Charge routing and the affected SDA/ADC-divider fanout were repaired, not the component placement.

TP1–TP5 are BOTTOM, y=25.7, 1.27 pitch. Net labels below come from the current `boards/neurband_c/neurband_c.net` (not an assumed generic SWD order):

| Pad | Centre | Net |
|---|---|---|
| TP1 | (16.00,25.7) | +3V3 |
| TP2 | (17.27,25.7) | /SWDIO |
| TP3 | (18.54,25.7) | /SWDCLK |
| TP4 | (19.81,25.7) | /NRST |
| TP5 | (21.08,25.7) | GND |

Use approximately **0.5 mm contact-tip diameter** pogo probes on the pad centres. TP2/TP3 retain offset access drills at (16.90,25.325)/(18.20,25.350); their nearest drill edges are approximately 0.377/0.338 mm from the respective contact centres. The central TP5 ground drill was removed; GND connectivity remains through the filled planes. Pad centres and 1.27 mm pitch did not move.


Height evidence is `boards/neurband_c/layout/build/component-heights.json` and `height-measurement.log`: repaired FreeCAD imports now select physical PartFeatures/solids, excluding unbounded datum planes. The earlier J1/U1 1e100 results were invalid and are superseded. These finite numbers are **visual-model measurements, not vendor tolerance certificates or measured assembled hardware**. U1 is a simplified 6 × 6 body, including its visual dot; use its 1.0 design reserve rather than asserting package tolerance from 0.905. Likewise retain U2's 1.2 reserve despite its 1.1 stock model.

## Battery and fit limits

The current **401225 cell envelope** is nominal **4 thick × 12 × 25**, located in the KiCad top-view frame at **x=11..23, y=−3.3..21.7**. It therefore extends **3.3 beyond the board's upper edge**. This is a real carrier/enclosure overhang requirement, not a cell contained inside the PCB outline. Its bottom is nominally **1.3 above the top PCB surface**: every component under its complete projected footprint must remain at or below 1.3, with the TQFP reserved to 1.2. Allow insulation, tolerances, swelling, protection/lead geometry and a non-loading carrier; model clearance is not permission to rest a cell on packages. Keep the cell and leads out of the antenna region.

The user's initial **25 × 20 × 4 alternative** cannot be claimed to fit this actual assembly without a carrier. It needs **more than 2.5 standoff**, plus insulation/tolerance and separate service access to the 2.0-high J1 and SW1. The smaller current cell and its 1.3 standoff are not evidence that the larger alternative fits at that height.

Further shrinkage is constrained by the ADS1298's **12 mm TQFP toe span**, the **14.4 mm-wide / 2.0 mm-high J1**, roughly **26 mm board-height allocation for the printed IFA/keepout arrangement**, four resistor-array fanouts, standard-drill escapes, conventional paste access and the four bottom supports. These constraints interact: reducing outline dimensions by moving only a courtyard or ignoring the metal-free RF volume is not an established smaller design. The 26 mm allocation is not the radiator rectangle's length (its y=11.65..27 exclusion is 15.35 long).

## Schematic parity and release evidence

Eight footprint decisions were initially board-only: J1 → `neurband:XUNPU_FPC-05F-20PH20`; J2/J3 → `neurband:WirePads_2x1.5x2mm_P3mm`; TP1–TP5 → `neurband:SWD_Pad_1x1_P1.27`. The main-schematic owner subsequently propagated those exact IDs into the deterministic generator/schematic, so **final parity is fully clean** rather than retaining eight exceptions. This layout task did not edit the generator or schematic. Cosmetic library-definition mismatch warnings from removed dense silkscreen/model changes do not imply missing components or justify calling the board warning-free.

Evidence paths: placement `layout/place_c.py` and `placement.json`; native board and current `neurband_c.net`; connector `layout/j1_review.md` and its saved manufacturer PDF/PNG; RF `layout/rf_geometry.md`; stackup `layout/build/intended-stackup.json`; model measurements `layout/build/component-heights.json` and `height-measurement.log`, all under `boards/neurband_c/` unless otherwise stated. Current electrical changes and datasheet-backed CONFIG3 interpretation are in the [review addendum](../review/sol_rev_c_review.md).

Final release evidence is under `boards/neurband_c/`:

- `layout/build/final-drc.json`: **0 errors, 0 unconnected, 0 schematic-parity issues** after the final J3 relocation and source-footprint regeneration. No hole-spacing, dangling-via or dangling-track warnings remain. The remaining **59 `lib_footprint_mismatch` warnings** describe intentional sparse-silkscreen/model differences from library definitions; the board is not claimed warning-free.
- `layout/build/final-netcheck.log`, `final-import.json`: frozen electrical connectivity/fields and deterministic symbol identities imported without resetting reviewed footprint geometry. These snapshots preceded the main-schematic owner's footprint-ID propagation; the final parity check confirms the current regenerated source matches. Neither the generator nor schematic was edited by this layout task.
- `layout/build/board-stats.json` and `neurband_c.fab.json`: measured outline **28.7 × 27.0**, native finished thickness **1.000**, minimum plated drill **0.300**, four layers, black mask/ENIG, quantity five.
- `neurband_c.step`: full component export, with DNP models omitted; `neurband_c_board_only.step`: board-only export. Both selected-CLI exports completed successfully. J1/U1 use the documented, finite, valid custom envelope models; do not mistake them for certified vendor tolerance models.
- `renders/top.png`, `bottom.png`, `3d.png`: inspected after iteration. Branding no longer clips the board edge; the isometric camera now includes the entire board. Bottom-only service pads, antenna exclusion and one-sided assembly are visible. `renders/layers/` contains board-framed native copper exports for plane/routing inspection.

These are geometric/connectivity and export checks, not a stock check, price quotation, manufacturing-order approval, analog-noise test or antenna certification.

Battery/wireless operation only while worn: no charger, programmer or grounded bench instrument connected to skin-contact hardware. Geometric DRC does not establish patient safety, bias-loop stability, analog noise or on-body RF performance.
