# FH26W-39S-0.3SHW(60) / C92280 review

## Decision

Use stock `Connector_FFC-FPC:Hirose_FH26-39S-0.3SHW_2Rows-39Pins-1MP_P0.60mm_Horizontal` for the copper land pattern. All 39 signal lands and both retention lands match the inspected Hirose engineering drawing's nominal copper dimensions. No corrected local footprint was created. This does not certify the stock paste apertures: they are larger than Hirose's recommended stencil apertures and need assembly-process review.

Only new `FH26W-*` files in this layout folder were written by this verification task. A background child updated only the requested rev B constraint line in `.backplane/intent.md`. No PCB, schematic/generator, flex, mech or ESP footprint was edited. No tests, builds, formatters or DRC were run.

## Official sources and saved evidence

- [Exact Hirose product](https://www.hirose.com/en/product/p/CL0580-2412-8-60), CL0580-2412-8-60. Saved reader copy: `FH26W-official-product-page.txt`. Product specifications updated October 2, 2026: 39 positions, bottom contact, FPC 0.2 mm, horizontal insertion, front actuator, body 13.2 x 3.2 x 1 mm.
- [Official exact-part engineering drawing endpoint](https://www.hirose.com/api/v1/products/CL0580-2412-8-60/documents/drawing_2d/content?lang=EN). Official document title `FH26W-39S-0.3SHW(60)_CL05802412860_2d.pdf`, six sheets. Saved first-sheet visual: `FH26W-official-drawing.png`. Drawing EDC3-323714-05, generic family title FH26W-**S-0.3SHW(60), rev 2 dated 2020-04-28; reference watermark October 1, 2026. Saved limited text extraction: `FH26W-official-drawing-extraction.txt`.
- Direct official requests and browser received HTTP 403. A reader proxy retrieved the official first-sheet image and document metadata. The complete six-sheet PDF was NOT downloaded; remaining sheets were not visually reviewed. Do not misrepresent the saved PNG as the complete PDF.
- [Hirose catalog, 2024-watermarked mirror](https://img.ic.ecer.com/e8/79/6afb613582cd73d7d5bb790af7aaba70.pdf), saved `FH26W-reference-0.pdf`: p5 explicitly covers suffix (60), p6 connector drawing, p7 39-pin dimension row, p8 copper/stencil/FPC drawing, p9 39-pin FPC dimension row, p14 insertion/contact orientation, p16 actuator rotation.
- [Older Hirose catalog mirror](https://media.digikey.com/pdf/Data%20Sheets/Hirose%20PDFs/FH26.pdf), saved `FH26W-catalog.pdf`: matching dimensioned illustrations rendered to `FH26W-catalog-03.png`, `FH26W-catalog-04.png`; enlarged cable geometry `FH26W-fpc-contacts-04.png`.
- [Fab C92280 part page](https://www.lcsc.com/product-detail/FFC-FPC-Connectors_HRS-Hirose-FH26W-39S-0-3SHW-60_C92280.html): MPN FH26W-39S-0.3SHW(60), bottom contact, 0.2 mm FPC. Its linked [datasheet](https://datasheet.lcsc.com/datasheet/pdf/0cfd8688fa084275891235874b6d7d0a.pdf?productCode=C92280) was readable through the document tool and is a Hirose series catalog, not an exact-part engineering drawing. No live stock count was verified through a stock API.

## Copper geometry and pin 1

Installed source: `/usr/share/kicad/footprints/Connector_FFC-FPC.pretty/Hirose_FH26-39S-0.3SHW_2Rows-39Pins-1MP_P0.60mm_Horizontal.kicad_mod`.

Footprint-local coordinates below are the stock F.Cu orientation, in mm (X right, Y down):

| Feature | Centre / bounds | Size |
| --- | --- | --- |
| Odd pins 1,3,...39 | x=-1.400; y=-5.700..+5.700, step 0.600 | 0.800 X x 0.300 Y |
| Even pins 2,4,...38 | x=+1.475; y=-5.400..+5.400, step 0.600 | 0.650 X x 0.300 Y |
| Retention pads MP | x=-1.125, y=+-6.400 | 0.950 X x 0.400 Y |
| F.Fab outline bounding box | x=[-1.900,+1.350], y=[-6.600,+6.600] | 3.250 x 13.200 |
| Courtyard | x=[-2.650,+2.300], y=[-7.100,+7.100] | 4.950 x 14.200 |

Hirose dimensions: C=11.4 mm odd-row centre span, B=10.8 mm even-row span, row-to-row inner copper gap=2.15 mm. Outer copper edges span 3.6 mm in the insertion axis. The F.Fab silhouette is a stock approximation (3.25 mm bounding depth versus nominal body depth 3.2 mm), not a closed- or open-state mechanical solid.

Official top view marks contact 1 at the left of the front/actuator edge; contact 2 is on the opposite solder row. Rotating that drawing to the stock orientation puts pin 1 at (-1.4,-5.7). Flex exits local -X and is inserted toward +X. The 0.3 mm cable pitch alternates between two 0.6 mm solder rows; it is not a conventional single-row 0.3 mm PCB footprint.

Numerical verification result saved in `FH26W-stock-comparison.json`: 39 signal pads, two MP pads, zero nominal copper deviations. Every stock pad was compared with the dimension-derived coordinates and sizes. `FH26W-stock-landpattern.png` was rendered from those parsed stock pad coordinates and visually inspected.

## Paste is not the recommended stencil

Official drawing sheet 1 recommends a 0.1 mm stencil with signal apertures 0.23 mm wide, odd-row length 0.65 mm, even-row length 0.55 mm; MP apertures 0.9 x 0.3 mm. The odd aperture front edge is dimensioned 0.1 mm inward from the copper front edge; do not assume every reduction is exactly concentric. The stock footprint has F.Paste equal to its copper rectangles (0.3 x 0.8, 0.3 x 0.65, MP 0.95 x 0.4). Assembly must specify the recommended apertures or validate its alternative paste process. This is not a copper incompatibility and does not justify silently swapping the PCB footprint in this support task.

## Bottom-side placement example requested by parent

Board 0..32 X, 0..26 Y; J2 origin (22,2.1), flex exiting toward global -Y:

`globalX = 22 + localY; globalY = 2.1 + localX`

This is a mirrored transform, determinant -1, not a top-side rotation. If the placement pipeline mirrors local Y first, use KiCad angle 270 degrees; if it mirrors local X first, use 90 degrees. Verify the resulting pad centres, not the angle label alone:

- Pin 1 = (16.3,0.7); pin 39 = (27.7,0.7).
- Pin 2 = (16.6,3.575); pin 38 = (27.4,3.575).
- MPs = (15.6,0.975), (28.4,0.975).
- Stock F.Fab bounds become X=[15.4,28.6], Y=[0.2,3.45].
- Courtyard becomes X=[14.9,29.1], Y=[-0.55,4.4]. The courtyard crosses board edge Y=0 by 0.55 mm; the drawn body does not. Treat this consciously as an edge-facing connector, not an unnoticed courtyard fit.
- Mouth/front copper near Y=0.3..1.1; rear signal lands Y=3.25..3.9. Parent's U3 input row at Y=7.6 leaves about 3.7 mm from the rear copper edge.

These are computed placement recommendations only; the canonical PCB was not changed or measured at these coordinates.

## Height, contact side and operation

Official engineering sheet 1 section B:

- Closed height: 1.0 +-0.1 mm above the mounting PCB surface.
- Open at 135 degrees: reference height 1.9 mm.
- Maximum sweep at 90 degrees: reference height 2.3 mm. Reserve at least this operating volume PLUS tolerance and handling clearance; 1 mm closed height is not an assembly access allowance.
- Bottom contact means exposed FPC conductors face the connector's mounting PCB surface. For a connector on B.Cu this is upward toward the board in global board orientation, not necessarily global -Z. Stiffener is on the opposite face. Do not confuse cable contact side with board layer names.
- FPC inserted parallel to board; open front actuator before insertion; do not bend the tail directly against the actuator or obstruct its sweep.

## Cable interface warning for flex owner

Hirose catalog p8/9 (2024 mirror), or p4 older catalog:

- Cable width F=12.0 +-0.05 mm; outer/odd centre span C=11.4 +-0.03; even centre span B=10.8 +-0.03.
- Outer odd centre is 0.3 +-0.07 mm from each cable edge; 0.3 +-0.02 pitch, 0.6 +-0.02 same-row pitch.
- Total reinforced mating thickness 0.2 +-0.03 mm, INCLUDING stiffener/adhesive, not a 0.2 mm stiffener added to the flex.
- Stiffener length 3.5 mm minimum; shorter requires dimension M >=0.5 mm as shown. Tip corner R0.2 max.
- Broad finger heads are 0.3 +0.04/-0.03 mm wide, narrowed interleaving necks 0.1 +-0.02 mm. Broad heads occupy two longitudinal contact bands: tip-side heads start 0.3 +-0.1 mm from tip and reach the 1.0 +-0.1 transition; interleaved heads begin around the 1.1 +-0.1 transition and reach the 2.1 +-0.1 transition. The drawing also specifies 2.25 +-0.1 and 2.5 +-0.3 boundaries. Use the enlarged drawing for the tapers and relative A/B transition constraint; do not reduce it to simple rectangles.
- Thirty-nine uniform 0.2 mm-wide straight fingers are NOT the published recommended cable geometry. Connector compatibility must be judged against the interdigitated drawing, not pitch alone.
- Current exact engineering drawing cable sheets were not recovered visually; the above cable geometry is explicitly sourced to Hirose's series catalog. Flex owner was sent the source and image and retains ownership of all flex edits.

## 3D availability

The installed stock footprint references `${KICAD10_3DMODEL_DIR}/Connector_FFC-FPC.3dshapes/Hirose_FH26-39S-0.3SHW_2Rows-39Pins-1MP_P0.60mm_Horizontal.step`; the corresponding file exists in `/usr/share/kicad/3dmodels/Connector_FFC-FPC.3dshapes/`. This is a generic FH26 stock model, not a verified exact FH26W(60) engineering solid or an actuator-sweep model.

The exact Hirose product page offers [STEP](https://www.hirose.com/api/v1/products/CL0580-2412-8-60/documents/model_3d_step/content) and [IGES](https://www.hirose.com/api/v1/products/CL0580-2412-8-60/documents/model_3d_iges/content) ZIP downloads. Availability of those links is verified; exact vendor model download/alignment and 3D interference were not verified in this task. No new mechanical model was fabricated.
