# ESP32-S3-MINI-1-N8 footprint review

## Result

The installed `RF_Module:ESP32-S2-MINI-1` has the correct S3 pad geometry and numbering, but is **not an exact mechanical/antenna match**. Its fabricated body is 15.4 × 20.0 mm, whereas ESP32-S3-MINI-1-N8 is 15.4 × 20.5 × 2.4 mm (body XY tolerance ±0.2 mm). Its antenna keepout stops 0.5 mm short of a 15 mm forward clearance measured from the S3 body tip. Use the standalone `neurband.pretty/ESP32-S3-MINI-1-N8.kicad_mod` in this directory. Canonical PCB and schematic were not edited.

Source footprint inspected: `$KICAD_ROOT/share/kicad/footprints/RF_Module.pretty/ESP32-S2-MINI-1.kicad_mod`. Its description incorrectly calls this an external-antenna module; MINI-1 has an onboard PCB antenna, MINI-1U has an external connector.

## Exact local geometry

Millimetres, top view, zero footprint rotation, +X right, +Y down. Retain the stock origin and all pads; the module is not geometrically centered about this origin.

| Feature | Local coordinates / dimensions |
| --- | --- |
| S3 nominal body | X = −7.7…+7.7; Y = −10.25…+10.25 |
| Antenna area (datasheet Fig. 11-1, 5.05 mm deep) | X = −7.7…+7.7; Y = −10.25…−5.20 |
| Pads 1…15, left | X = −7; Y = −3.40 + 0.85 × (pin−1); 0.8 × 0.4 |
| Pads 16…30, bottom | X = −5.95 + 0.85 × (pin−16); Y = 9.55; 0.4 × 0.8 in XY |
| Pads 31…45, right | X = +7; Y = 8.50 − 0.85 × (pin−31); 0.8 × 0.4 |
| Pads 46…60, top | X = 5.95 − 0.85 × (pin−46); Y = −4.45; 0.4 × 0.8 in XY |
| Pad 61, exposed ground | Nine 1.2 × 1.2 islands; X ∈ {−1.65, 0, +1.65}; Y ∈ {0.90, 2.55, 4.20}; upper-left island chamfered |
| Pads 62, 63, 64, 65, ground corners | (−7, −4.45), (−7, 9.55), (+7, 9.55), (+7, −4.45); each 0.8 × 0.8 |
| All-layer antenna rule area | X = −22.70…+22.70; Y = −25.25…−5.20 |

There are **65 numbered electrical pins and 73 physical SMD pad objects**: 60 narrow perimeter pads + 4 square ground corners + 9 islands sharing number 61. This matches datasheet Figs. 3-1 and 11-1. All top-edge pins 46…60 are GND; corners 62…65 and EP 61 are also GND. Example numbering anchors: 1/2 GND, 3 3V3, 4 IO0, 45 EN. Physical compatibility does not imply S2 and S3 GPIO functions are interchangeable.

EP island envelope is X = −2.25…2.25 and Y = 0.30…4.80 (4.5 × 4.5); inter-island gaps are 0.45 mm. The datasheet's 1.7 mm via-location dimension is not an instruction to change the pad-island pitch. Thermal/ground stitching vias are board-layout work; neither stock nor corrected footprint includes drilled vias.

## Placement and clearance

Prefer top-side assembly at a board end, antenna pointing outward and **the entire antenna area overhanging the board**. At 0° place the board's top edge at local Y = −5.20; substrate/body below this line remains supported and the antenna extends 5.05 mm outward. Choose the end opposite the FPC/analog inputs and battery wiring where practical. Rotate the entire geometry together if another edge is used.

The corrected rule area preserves the stock policy: tracks, vias, pads, pours and other footprints forbidden on **all copper layers**, including F.Cu, In1.Cu, In2.Cu and B.Cu on this four-layer board. It extends 15 mm sideways and forward of the antenna; the rear boundary is the antenna/body transition, not 15 mm into the shielded module. Ground planes and stitching remain under the shielded module/body, outside the antenna rule area. A courtyard alone is not sufficient.

Official guidance strongly recommends antenna overhang. If overhang is impossible, place the feed close to an edge and cut away base-board material beneath and beside the antenna; do not bury the module at board center with a four-sided slot. Keep the 402030 battery, leads, metal, housing obstructions and other boards away from the antenna volume, not merely off its copper projection. Espressif recommends at least 15 mm clearance in all directions inside the housing. Validate the assembled product's range/throughput; planar KiCad DRC cannot establish 3D RF clearance.

## Corrected footprint scope

Only module name/description, S3 body tip (−9.75 → −10.25), antenna rear boundary (−5.25 → −5.20), and forward keepout/courtyard boundary (−24.75 → −25.25) are changed from stock; pad copper/numbering is unchanged. The incorrect S2 STEP model is omitted, not replaced by a guessed S3 model. No canonical-board cutover was performed.

## Primary evidence

- [Espressif ESP32-S3-MINI-1 / MINI-1U Datasheet v1.7](https://documentation.espressif.com/esp32-s3-mini-1_mini-1u_datasheet_en.pdf): Table 1-1 (N8 and body size), Fig. 3-1 / Table 3-1 (65-pin numbering), Fig. 10-1 (mechanical envelope), Fig. 11-1 (recommended land pattern and antenna area). Figures 3-1 and 11-1 were inspected as rendered PDF images, not inferred from flattened text.
- [Espressif ESP32-S3 Hardware Design Guidelines — module positioning](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html#general-principles-of-pcb-layout-for-modules-positioning-a-module-on-a-base-board): overhang, board cutaway, housing clearance ≥15 mm and end-product RF testing. Same document recommends four-layer PCB and top-only component placement.

Requested `skill://footprint` and `skill://layout` were unavailable in this worker's skill registry (only diagnose-crash, hf-cli and omarchy are registered). No builds/tests/DRC were run; this is dimensional/document inspection, not board sign-off.
