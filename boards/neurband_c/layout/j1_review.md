# J1 — XUNPU FPC-05F-20PH20 / LCSC C2856803

## Deliverable

Load library ID `neurband:XUNPU_FPC-05F-20PH20`.

- Footprint: `boards/neurband_c/layout/neurband.pretty/XUNPU_FPC-05F-20PH20.kicad_mod`
- Registration: `boards/neurband_c/fp-lib-table`; nickname `neurband`, URI `${KIPRJMOD}/layout/neurband.pretty`.
- Manufacturer drawing saved as `XUNPU_FPC-05F-20PH20.pdf` beside this report; rasterized original `XUNPU_FPC-05F-20PH20.png`.
- Footprint inspection render: `XUNPU_FPC-05F-20PH20_footprint.png`.

No board, schematic, or flex was changed. This is not the Hirose FH12 footprint.

## Sources and authority

1. [LCSC C2856803 product identification](https://www.lcsc.com/product-detail/C2856803.html): manufacturer XUNPU, exact MPN FPC-05F-20PH20, 20 contacts, 0.5 mm pitch, bottom-contact, right-angle SMT, flip-top, 0.3 mm FPC thickness.
2. [Manufacturer drawing supplied by LCSC](https://datasheet.lcsc.com/datasheet/pdf/3a5d0ddaf61b312ec7a8c470eadfb5fe.pdf?productCode=C2856803), obtained through the product's [datasheet link](https://www.lcsc.com/datasheet/C2856803.pdf). Title block: DongGuan XunPu Electronics Co., Ltd.; `FPC 0.5PH H2.0` front-flip series; part family `FPC-05F-NPH20`; revision A; sheet 1/1. The sheet is parametric: substitute N=20. This is a manufacturer-authored drawing hosted by its distributor, not a guessed substitute or an EasyEDA-only footprint.
3. [Distributor EasyEDA footprint SVG](https://image.easyeda.com/component_svgs/prod/882c630401bf425abe1cf720e600162b.svg): secondary corroboration only, for pin-number orientation and undimensioned body-to-land registration. Copper dimensions below are from source 2.

The PDF has a damaged/circular cross-reference table: the text reader could not parse it, but Poppler rasterized the full sheet successfully. The saved PNG preserves the inspected sheet.

## Drawing interpretation and exact land coordinates

All dimensions below are millimetres. View the unrotated footprint from the **top of the PCB**: +X right, +Y down. Origin is the centre of the signal-pad row, not the body centre.

| Feature | Drawing / local implementation |
| --- | --- |
| Signal count / pitch | 20 / 0.50 |
| Signal pad size | 0.30 X by 1.25 Y, rectangular |
| Signal pad centres | pin n: `X = -4.75 + 0.50*(n-1)`, `Y = 0` |
| Pin 1 | `(-4.75, 0)`; silkscreen `1` above/left and F.Fab triangle below |
| Pin 20 | `(+4.75, 0)` |
| End-to-end contact span | `(N-1)*0.5 = 9.50` |
| Left mounting pad | centre `(-6.44, 2.575)`, size 2.00 X by 2.50 Y |
| Right mounting pad | centre `(+6.44, 2.575)`, size 2.00 X by 2.50 Y |
| Overall copper X bounds | -7.44 to +7.44 |
| Overall copper Y bounds | -0.625 to +3.825 |
| Courtyard | X -7.70 to +7.70; Y -0.90 to +5.70 |

The drawing's 2.69 dimension runs from the mounting land's outer edge to the nearest signal-pad centre. Thus left mounting-pad centre is `-4.75 - 2.69 + 1.00 = -6.44`; the other side is symmetric. The 0.70 vertical gap is between the signal-land inner edge and mounting-land upper edge. Thus mounting Y is `1.25/2 + 0.70 + 2.50/2 = 2.575`. These distinctions matter: treating 2.69 as centre-to-centre, or 0.70 as a centre offset, gives the wrong footprint.

All lands have F.Cu, F.Paste and F.Mask; no unusual paste shrink or mask enlargement was invented. Mounting lands have empty pad numbers: they are mechanical solder anchors, not signal pins 21/22 and not automatically ground. Assign no schematic signal to them. KiCad/fabricator mask rules apply.

## Mouth, contact side, pin numbering

The solder tails are at Y=0. The mouth / actuator is the opposite long edge, on **+Y**, approximately Y=5.41. The free flex lies beyond +Y and is inserted **toward -Y**, into the connector. The flex's exposed copper faces **down toward the PCB**, because this is a bottom-contact connector. The stiffener belongs on the opposite/upward side at the mating end.

With the unrotated footprint viewed from above, numbering is 1 at left through 20 at right along the rear solder-tail row. The manufacturer labels Circuit 1 on the right in its **contact-face FPC view**. Turning that bottom contact face down into the connector mirrors its left/right appearance in the PCB top view; this agrees with the distributor's pin-1-left top-view footprint. Do not mirror this footprint for a top-side assembly, and do not copy the contact-face flex numbering directly onto a top-view PCB image. The moulding drawing does not separately number every metal tail; the manufacturer Circuit 1 callout plus this explicit mating convention defines pin 1 unambiguously.

Recommended mating FPC dimensions from the sheet: total width `(N+1)*0.50 = 10.50 ±0.03`; conductor-centre span 9.50 ±0.03; conductor width 0.30 ±0.03; pitch 0.50 ±0.03; first conductor centre 0.50 from cable edge; exposed contact length 3.00 minimum; thickness 0.30 ±0.03; illustrated reinforced end length 6.00; corner R0.30. Flex design is outside this deliverable.

## Body / actuator envelope and 3D

- Drawing body width: `(N-1)*0.5 + 4.90 = 14.40`.
- Drawing overall front-to-back closed outline: 5.12.
- Drawing closed body/actuator height above PCB: **2.00**. This is the closed envelope; the sheet does **not** dimension the fully opened actuator height or sweep. Do not treat 2.00 as the service clearance needed to open it.
- Front opening width: `(N-1)*0.5 + 1.10 = 10.60`.
- F.Fab closed outline: X ±7.20; Y 0.2875 to 5.4075. **The Y registration is inferred from the secondary footprint artwork**, because the manufacturer does not dimension body location relative to land Y=0. The actual 14.40 by 5.12 envelope dimensions remain manufacturer-backed. This registration does not change any copper land position. Courtyard uses 0.25 mm or greater nominal clearance around the combined copper/closed-body envelope; it does not reserve cable length or actuator operating space.

No verified manufacturer STEP model was exposed by the authoritative drawing/product page, so no unverified cosmetic model is attached. The dimensional record above is the mechanical deliverable. Reserve additional unquantified access above/forward of the actuator until an open-actuator drawing or physical sample is available.

## Method / verification record

Used the available official KiCad Library Tools checkout (`kicad-library-tools`, commit directory `36d1ed20`) and its KicadModTree serializer. Inspected the existing `SMD_single_row_plus_mounting_pad` connector generator/pattern and the project's prior connector YAML convention; used its single-row plus two solder-anchor topology, with the manufacturer's exact rectangular lands. No new general-purpose generator was added.

Inspected the rasterized manufacturer sheet and rendered the actual KicadModTree pad/outline nodes. The rendered footprint shows twenty sequential signal lands, symmetric independent anchors, top-view pin 1 on the left, and +Y mouth. Land dimensions and offsets were algebraically reconciled with all labelled land-pattern dimensions as above. No builds, lint, DRC, board edits or IPC import were run here; Main should perform the actual IPC import and board-level clearance verification. The library is registered and the standalone footprint is ready for that import.
