# Render pipeline notes

- Hand/arm asset: Blender "Human Base Meshes" bundle v1.4.1 (CC0, blender.org demo files), in
  `extra/render_assets/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend`.
  Objects: `Hand  - Realistic` (two spaces; 0.151 x 0.065 x 0.283 m, hand + ~9 cm forearm stub, MULTIRES),
  `GEO-body_male_realistic` (full body, A-pose, MULTIRES) for a whole-arm shot.
- The asset objects sit off-origin: clear parent, set location (0,0,0), `view_layer.update()` before bbox.
- Faceted unless you add a Subdivision Surface modifier (levels 2) and set polygons smooth
  (`for p in mesh.polygons: p.use_smooth = True`).
- Lighting at this scale (0.3 m subject): area lights of ~10-30 W at ~0.6 m, AgX view transform.
- Skin: Principled, base ~(0.80, 0.56, 0.45), subsurface weight ~0.25, radius (0.012, 0.004, 0.002) m.
- The forearm stub ends in a flat cut: frame shots so it is out of view, or fade it with a dark sleeve.
- GPU: 2x RTX 3090, Cycles OptiX works (`render/test_hand.py`).
- STEP -> GLB with colours: FreeCAD GUI offscreen, `ImportGui.insert(step, doc)` then
  `ImportGui.export([root objects], "x.glb")` (tested on mech/rev_c/band_assembly.step, 1.4 MB).
- Boards -> GLB with components and real colours: `kicad-cli pcb export glb --include-tracks --include-pads
  --include-zones --include-silkscreen --include-soldermask -o board.glb board.kicad_pcb` (check `--help`).
- Blender imports GLB natively (`bpy.ops.import_scene.gltf`). Replace imported materials with proper
  shaders (matte PA12/anodised housing, TPU, ENIG gold, polyimide amber, solder mask) for hero shots.

## Render pipeline (render/make_renders.py -> render/nb_blender.py), lessons
- Entry point: `python3 render/make_renders.py [--quick] [--shots a,b] [--no-export] [--save-blend]`;
  docs in `docs/renders.md`. One Blender process per shot, one worker per GPU (CUDA_VISIBLE_DEVICES).
- The on-arm shots use the right arm of `GEO-body_male_realistic` (long forearm, cut out of frame), not
  `Hand  - Realistic`. Crop radius must be wider around the hand (thumb tip is ~9 cm off the axis),
  otherwise the fingertips get holes that render black.
- KiCad GLB: board-level materials carry real PBR values; component (VRML-derived) materials all come
  in as metallic 1 / roughness 1 - classify them by colour. Silkscreen has alpha 0.9, test it before
  the soldermask (alpha 0.83). Board GLBs need `KICAD10_3DMODEL_DIR` for the component models.
- Do not bend KiCad GLB copper: tracks are long two-vertex quads and turn into floating chords.
- ENIG pads only read gold when something moderately bright sits in the camera's mirror direction
  (a dim area light "card"); too bright and they go cream/white.
- FreeCAD GUI-mode `print` does not reach stdout; check the produced files instead.
