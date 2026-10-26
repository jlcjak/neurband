# ESP32-C3-MINI-1 — rev B footprint verification

## Deliverables and scope

- `neurband.pretty/ESP32-C3-MINI-1.kicad_mod`
- `ESP32-C3-MINI-1.yaml`: dimensional review manifest, not a generator input.
- `models/ESP32-C3-MINI-1.{py,FCStd,step,log}`: parameterized simplified FreeCAD envelope, native document, colored STEP, validation evidence.
- `ESP32-C3-MINI-1-review/`: KiCad SVG, overview PNG, pad-numbering PNG, numeric verification output and datasheet figure captures.
- `models/renders/ESP32-C3-MINI-1.*.png`: Backplane mechanical renders.

No canonical board/schematic, library tables, existing models or other existing files were edited. No pcbnew SWIG, new generator, board writes, builds, lint, tests or board DRC were used. This verifies a library artifact, not its placement/routing on rev B.

## Sources and reuse

Primary source: repository `docs/datasheets/esp32-c3-mini-1.pdf`, datasheet v2.2, Fig. 11-1 (page 38) and Fig. 3-1 (page 10), both rasterized and visually inspected, with accompanying `.txt`. Nominal module 13.2 × 16.6 × 2.4 mm.

Public source: https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.pdf

Installed library has no C3-MINI-1 footprint. Existing `RF_Module:ESP32-C6-MINI-1` at `$KICAD_ROOT/share/kicad/footprints/RF_Module.pretty/ESP32-C6-MINI-1.kicad_mod` has matching land coordinates, numbering, mechanical envelope and antenna geometry. Reused its complete geometry; changed name, description, tags, model path and UUIDs. Its external-antenna description was incorrect for MINI-1 and is not carried over. This is mechanical/land-pattern reuse, not a claim of C3/C6 signal interchangeability. Existing project convention is standalone footprints plus YAML and model review assets; no new generator implemented.

## Exact local geometry

Millimetres; top view; 0° rotation; +X right, +Y down. Origin is the center of the nine-island GND array, **not the module body center**. Body center is (0, −2.7). Antenna points −Y.

| Feature | Bounds or pad-center formula |
|---|---|
| Nominal module | X −6.6…6.6; Y −11…5.6; Z 0…2.4 |
| Antenna substrate | X −6.6…6.6; Y −11…−5.6; depth 5.4 |
| Supported module region | X −6.6…6.6; Y −5.6…5.6 |
| Pins 1…11, left | X −5.9; Y −4 + 0.8(n−1); XY size 0.8 × 0.4 |
| Pins 12…24, bottom | X −4.8 + 0.8(n−12); Y 4.9; XY size 0.4 × 0.8 |
| Pins 25…35, right | X 5.9; Y 4 − 0.8(n−25); XY size 0.8 × 0.4 |
| Pins 36…48, top | X 4.8 − 0.8(n−36); Y −4.9; XY size 0.4 × 0.8 |
| GND 49 | Nine 1.45 × 1.45 islands at X,Y ∈ {−1.975, 0, 1.975} |
| GND 50 / 51 / 52 / 53 | (5.95,−4.95) / (5.95,4.95) / (−5.95,4.95) / (−5.95,−4.95); each 0.7 × 0.7 |
| All-copper antenna rule area | X −21.6…21.6; Y −26…−5.6 |
| Courtyard | Broad antenna portion X ±21.6, Y −26…−5.6; body portion X ±6.85, Y −5.6…5.85 |

48 narrow pads + 4 corner pads + 9 central islands = **61 physical pads, 53 unique pin numbers**. All islands use number 49, not separate additional numbers. EP envelope is 5.4 × 5.4; island gaps 0.525. Upper-left island has the stock chamfer ratio 0.41 (0.5945 mm, representing the drawing's nominal 0.6 mm chamfer). Fig. 11-1's 1.6 mm dimensions concern optional thermal-via locations, not EP island pitch. No drilled vias are included; ground stitching and via paste treatment are board-layout decisions.

Fig. 3-1 numbering anchors match: 1/2 GND; 3 3V3; 8 EN; 12 IO0; 26 IO18/USB D−; 27 IO19/USB D+; 30 RXD0; 31 TXD0; 36…53 GND. Independent numeric comparison confirms pad number set exactly equals all 53 pin numbers in `lib/neurband.kicad_sym`, including its hidden GND pins.

## Antenna and intended placement

At 0°, put the board's outward/top edge at local **Y = −5.6**. Antenna extends 5.4 mm beyond this edge. Rotate the entire footprint and rule area together for another board edge. The antenna's projected region must not sit over host-board copper on any layer.

Rule area explicitly enumerates F.Cu, B.Cu and In1.Cu…In30.Cu; tracks, vias, pads, pours and other footprints are forbidden. It extends 15 mm beyond each antenna side and 15 mm beyond its tip, matching the stock module-clearance policy. It does not prohibit ground under the supported body behind Y=−5.6. Courtyard alone is not the copper exclusion mechanism. Overhang is intended but cannot be enforced by this footprint alone; verify board edge placement, housing/metal/battery clearance and RF performance during integration.

## 3D model and alignment

No installed C3 footprint/model was available. FreeCAD GUI ran offscreen and exported colored STEP with `ImportGui.export`. Both solid shapes passed `shape.isValid()`. Measured compound bounds: CAD X −6.6…6.6, Y −5.6…11, Z 0…2.4; exactly 13.2 × 16.6 × 2.4 mm. CAD XY is footprint (X,−Y); mounting plane Z=0. Footprint model offset/rotation zero and scale unity. Model path `${KIPRJMOD}/layout/models/ESP32-C3-MINI-1.step` resolves with the main KiCad project in `boards/neurband_main`.

This is an envelope model, not a vendor detailed shield model: green substrate uses an illustrative 0.8 mm internal height split and the shield-envelope block fills the supported 11.2 mm region up to total height 2.4 mm. No invented antenna trace, internal electronics or precision shield-edge claims. Do not use its simplified shield edges as controlled mechanical mating surfaces.

## Executed verification

1. Rendered datasheet pages 10 and 38 with `pdftoppm`; visually compared pin direction/corners, island chamfer and dimension chains.
2. Independently derived all 61 pad centers and XY sizes from C3 Fig. 11-1 formulas, parsed the finished footprint and compared every value (tolerance 1e−8 mm): PASS. Symbol pin-set equality 1…53: PASS. Rule area all 32 copper layers and five exclusions: PASS. Output saved in `ESP32-C3-MINI-1-review/verification.txt`.
3. Selected KiCad CLI reports `10.99.0`; `fp export svg` successfully loaded and rendered the footprint. Inspected overview and monochrome F.Fab pad-numbering render: correct antenna-up orientation, left 1…11, bottom 12…24, right 25…35, top 36…48, corner 50…53, nine 49 islands and upper-left chamfer. Central reference text overlaps island labels in the plot only; copper shapes are distinct.
4. Offscreen FreeCAD export completed successfully with dimensions asserted and logged. Backplane renderer produced iso/front/top/right PNGs; iso visually inspected for antenna/substrate extension and shield orientation.

Initial SVG export failed because the requested temporary output directory did not exist; creating the review directory resolved it. Python CairoSVG was unavailable, so ImageMagick rasterized the actual KiCad SVG instead. Neither issue affected the completed footprint or model.
