# neurband product renders

These are the launch and social-media images of the rev C band. They are Blender 5.2 Cycles renders made
from the real CAD (`mech/rev_c`) and the real KiCad boards. One command rebuilds every image from the
current files.

## Images (`render/out/`)

| File | Format | Shot |
|---|---|---|
| `hero_arm.png` | 4:5, 1638 x 2048 | Hero shot. The hand rests on the table on gently curled fingertips, with the forearm raised. Seen from above on the thumb side, with the module facing the camera at a 3/4 angle. Shallow depth of field. |
| `hero_arm_wide.png` | 16:9, 2048 x 1152 | Low side view of the same pose, with the hand leading into the frame and contact shadows under the fingertips. |
| `hero_crop.png` | 4:5 | Tight 3/4 forearm crop. The module fills the frame. |
| `hero_dark.png`, `hero_dark_wide.png` | 4:5, 16:9 | Moody variant of the hero pose. Deep charcoal sweep with a faint gradient, a warm key, and cool rims that are light-linked to the arm and band only, so the backdrop stays dark. f/2.8. |
| `arm_volar.png` | 4:5 | Palm up, held above the backdrop. Shows the strap, buckle side and pods on the volar wrist. |
| `flatlay.png` | 16:9 | Top-down flat-lay of the band laid open, skin side up: all 8 pods with their gold pads, and the module underside with the charge window. |
| `pods_inside.png` | 4:5 | Close-up into the closed band: gold pads on the pods and under the module. |
| `band_product.png` | 4:5 | The band alone, closed, on a pedestal against a deep charcoal backdrop. Graphite PA12, satin pods, amber flex. |
| `band_bone.png` | 16:9 | Bone-white housing variant on a warm grey sweep. |
| `xray.png` | 16:9 | Clear-resin housing showing the LiPo, the main board, the J1 FPC connector and the flex tail U-turn. |
| `exploded.png` | 4:5 | Module exploded along its stack: lid, cell, main board, base (with magnets and strap bars), pods 3/4 flex, foam and pads. |
| `pcb_top.png` | 16:9 | Main board top macro: black mask, ENIG, the KiCad 3D models. |
| `pcb_pair.png` | 16:9 | Main board top and bottom side by side. The bottom shows the VCHG/GND charge pads and the SWD pads. |
| `flex_detail.png` | 16:9 | Electrode flex close-up, skin side up: ENIG pads on amber polyimide. |
| `turntable.mp4`, `turntable.gif` | 1080 x 1350, GIF 576 x 720 | 360-degree turntable in the `band_product` look. 4.5 s at 30 fps (135 frames) with a cosine ease that loops seamlessly. The MP4 is H.264, yuv420p, CRF 18 (about 1 MB); the GIF is 15 fps with a 96-colour palette (about 4 MB). |

The look is meant to be restrained:
- warm-grey, deep-charcoal or slate sweeps;
- a warm softbox key, a soft neutral fill and a subtle rim that separates the band from the
  background;
- AgX (Medium High Contrast), real depth of field, and a soft radial vignette (18 %) applied to the
  saved PNG.

There are no text overlays, flares or glow effects.

## Regenerate

```
python3 render/make_renders.py            # final: 2048 px long side, 768 spp + OptiX denoise (~15 min)
python3 render/make_renders.py --quick    # previews: 40 % size, 64 spp (~1 min)
python3 render/make_renders.py --shots xray,pcb_top --no-export --save-blend
python3 render/make_renders.py --video          # stills plus the turntable MP4 and GIF (about 5 min extra)
python3 render/make_renders.py --video-only     # turntable only
python3 render/make_renders.py --social --no-export --shots hero_crop,pods_inside,pcb_top --video
                                               # 16:9 versions for social posts, subject centred -> render/out/social/
```

The turntable frames are split across the GPUs (even and odd frames) and written to
`render/build/turntable/`. ffmpeg then encodes `render/out/turntable.mp4` (libx264) and
`turntable.gif` (palettegen and paletteuse).

Every run does the following:

1. It re-exports the inputs into `render/build/`, which is git-ignored:
   - `kicad-cli pcb drc` on `boards/neurband_c/neurband_c.kicad_pcb`. This only records the result in
     `main_board_drc.json` and does not block the run, because the layout is still in progress.
   - `kicad-cli pcb export glb` (tracks, pads, zones, silkscreen, soldermask, `--subst-models`) to
     `main_board.glb`.
   - The same export of `boards/neurband_c_flex/neurband_c_flex.kicad_pcb` to `flex_board.glb`, when
     that file exists. Without it, `flex_detail` falls back to the flex modelled in
     `band_assembly.step`.
   - FreeCAD (`render/step2glb.py`, ImportGui offscreen) converts `mech/rev_c/band_assembly.step`,
     `module_assy.step`, `fit_160.step` and `pod_with_flex.step` to GLB, keeping part names and colours.
2. It renders each shot in its own `blender -b` process (`render/nb_blender.py`). There is one worker
   queue per GPU (`--gpus 0,1`), with Cycles OptiX on each. Logs go to `render/build/logs/`.

### How the scenes are built (`render/nb_blender.py`)

- **The arm** is the right forearm and hand of `GEO-body_male_realistic`, at multires level 3. The
  script finds the forearm axis from cross-sections and puts the band centre 10 mm proximal of the
  narrowest wrist section, which is about 25-30 mm above the crease. The dorsal direction is the minor
  axis of the wrist section. The arm is then cropped about 19 cm up the forearm, so the cut is always
  out of frame, and moved into the CAD frame (X radial, Y proximal, Z dorsal). Finally it is scaled
  uniformly so that the wrist under the band is 160 mm around, the size `band_assembly.step` is fitted
  to (scale 0.96).
- **Pose.** The A-pose fingers are relaxed procedurally (`curl_fingers`): everything distal of the
  knuckle line, about 9 cm from the fingertip, bends toward the palm with constant curvature. The
  ulnar fingers bend more, and the finger spread closes by 15 %. The posed forearm sits on the table
  through its lowest point, so the fingertips make real contact shadows.
- **Band fit.** Rays are cast around the arm axis against both the CAD wrist model (`fit_160`) and
  the human arm. The difference in radius, as a function of angle and position along the arm, drives
  a radial warp of the pod ring, flex and strap. The module, cell and board move rigidly onto the
  dorsal seat. The log reports the pad seating: pad centres sit within -1.3 to +0.7 mm of the skin
  surface, so the pads touch the skin and do not float.
- **The real board inside the module** is aligned to the CAD placeholder board using the same mapping
  as `module.k2m`, which puts the KiCad board's distal edge at Y_B0. It is carried into the band frame
  by a rigid fit of the cell, which is the same part in both GLBs.
- **Materials** are procedural:
  - MJF PA12 in graphite or bone white: bead-blast grain plus micro-roughness variation. The x-ray
    shot uses clear resin instead.
  - Pods: satin TPU-look elastomer.
  - Strap: woven webbing. A plain-weave normal (0.55 mm threads) is driven by a `weave` attribute,
    which is the arc length around the wrist plus the position across the strap. It has fibre fuzz
    and sheen.
  - Boards: ENIG gold, amber polyimide and coverlay, black LPI mask with a clear coat, white
    silkscreen, tin terminations and epoxy component bodies (classified from the KiCad colours).
  - Skin: short random-walk SSS (not waxy), mottled albedo with freckle-scale speckle, pore and
    micro-normal bumps, and roughness variation. It also has a `redness` attribute, computed from
    mesh convexity on the back of the hand, the palm and the wrist crease, which warms the knuckles
    and the crease.
- **Flat-lay.** The closed band is unrolled by arc length around the CAD wrist, starting at the strap
  gap. Small rigid parts (pods, pads, foam, buckle, and each flex pod and link) move by their
  centroid. The strap unrolls per vertex, and the module stays rigid. Everything off the module then
  drapes down to the table.

### Inputs used for the current images (2026-10-26, 03:30)

- Main board: `neurband_c.kicad_pcb` from 03:12. DRC shows 0 errors, 59 warnings and 0
  unconnected items.
- Electrode flex: `neurband_c_flex.kicad_pcb` from 03:17.
- Mech: the restyled `mech/rev_c` from 03:15-03:22. It has a continuous woven strap over
  low-profile TPU pods, a strap loop, a button cap and hidden bars.
- Known CAD issue, visible from the ulnar side of the ring interior: near the ulnar lug, the strap
  geometry pokes through the flex spine link between pod 2 and the module. `pods_inside` therefore
  looks at the radial side.

A full run takes about 4.5 minutes on 2x RTX 3090.

### When the CAD or boards change

Re-run `python3 render/make_renders.py`. Shot framing is set relative to the module and board
bounding boxes, so small geometry changes need no edits. Check the following after a re-run:

- When `boards/neurband_c/neurband_c.step` is released, `module.py`, `fit.py` and `assembly.py`
  re-import it. The render pipeline uses the KiCad board directly, so nothing changes there.
- If the electrode flex outline changes a lot, check the framing of `flex_detail` (it shows the
  middle of the strip).
- If the band is refitted to a different wrist, update `WRIST_C` and the `fit_160` reference in
  `nb_blender.py`.

## Licences

- **Human:** the "Human Base Meshes" bundle v1.4.1 by Blender Studio, which is **CC0 1.0** (public
  domain). Attribution is optional; credit "Human Base Meshes, Blender Studio (CC0)" if you wish. It is
  downloaded by `render/fetch_assets.sh` into `extra/render_assets/` and is not committed.
- **Component 3D models** in the board renders come from the KiCad 3D library (CC BY-SA 4.0 with the
  KiCad libraries exception, which lets you use them in renders of your designs) plus the project's own
  models (`boards/neurband_c/layout/models`).
- Everything else (band CAD, boards, scripts) is the project's own work.
