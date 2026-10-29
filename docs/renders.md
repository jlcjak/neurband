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
| `arm_volar.png` | 4:5 | Palm up, held above the backdrop. Shows the webbing loop and the pods on the volar wrist. |
| `flatlay.png` | 16:9 | Top-down flat-lay of the band laid open, skin side up: all 8 pods with their gold pads, and the module underside with the charge window. |
| `pods_inside.png` | 4:5 | Close-up into the closed band: gold pads on the pods and under the module. |
| `band_product.png` | 4:5 | The band alone, closed, on a pedestal against a deep charcoal backdrop. Graphite PA12, satin pods, amber flex. |
| `band_bone.png` | 16:9 | Bone-white housing variant on a warm grey sweep. |
| `xray.png` | 16:9 | Clear-resin housing showing the LiPo, the main board, the J1 FPC connector and the flex tail U-turn. |
| `exploded.png` | 4:5 | Module exploded along its stack: lid, cell, main board, base (with its hidden strap bars), pods 3/4 flex, foam dots and pads. |
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

Every band shot shows the pod ring in the real flex's order, with pods 1-2 on the radial (button) side
and 5-8 ulnar. `nb_blender.load_band` mirrors the ring parts of `band_assembly.step` for this
(`mirror_ring`; set `MIRROR_RING = False` for the raw CAD order). Each slide is drawn as the CAD
places it: swung in line with the band, with the webbing end locked round its friction bar.

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

### Assembly animation (`render/assembly_anim.py`)

```
python3 render/assembly_anim.py                 # re-export inputs, 733 frames on GPUs 0,1, captions, MP4 + GIF (~15 min)
python3 render/assembly_anim.py --no-export     # reuse render/build/*.glb
python3 render/assembly_anim.py --quick         # half size, 16 spp preview -> render/build/assembly_quick_out/
python3 render/assembly_anim.py --encode-only   # redo captions, cross-fade and encoding from existing frames
blender -b --python render/assembly_anim.py -- --scene ring --quick --times 9.4,16.2   # debug stills
```

- **Output.** `docs/media/assembly.mp4` (1920 x 1080, 24 s at 30 fps, H.264 CRF 20) and
  `docs/media/assembly.gif` (720 px wide, 8 fps, 64 colours with ordered dither, about 9.4 MB; at 10 fps it
  goes over 10 MB).
- **Two scenes, cross-faded at 6.6-7.0 s.** Each is rendered in its own `blender -b` process per GPU,
  to `render/build/assembly/j_NNNN.png` and `r_NNNN.png`.
  - The **jig** scene (`guide_figures.jig_scene`) covers the bonding jig. The flat KiCad flex lies
    pads-down on the pins, bent onto the saddle and with its tail turned up. The foam dots drop into
    the pods and the base, which are pocket-up. Each part turns over and presses into its fence.
  - The **ring** scene (`ring_scene`) is the band as fitted on the 160 mm wrist. The board comes down
    onto the upright tail and book-folds. Then come the cell, the button cap and the lid. Next, the two
    slides clip on, the webbing loop is revealed from slide A round to slide B and the tails pull.
    Last, the charge clip slides on from the proximal end and off again.
- **The pod order is mirrored.** `fit.py` (and so `band_assembly.step`) puts pods 1-2 on the ulnar
  side. The real flex has them radial (`docs/layout/flex_c_layout.md`). The ring parts are therefore
  mirrored about the module's X = 0 (`nb_blender.mirror_ring`). The fit's wrist section is an ellipse,
  so the fit itself is unchanged.
- **Modelled in the script:**
  - the flex tail, a ribbon of constant free length while the board folds on it;
  - the cell's leads round the distal +X corner through the lead gate;
  - the USB lead.
- **The webbing pieces.** The five webbing solids (loop, two wraps, two tails) are fused in
  `band_assembly.step`. The script rebuilds them with `mech/rev_c/fit.py` under FreeCAD into
  `render/build/strap_pieces.glb`.
- **Rendering.** 40 spp with OptiX denoising: about 2 s a frame for the jig and 3 s for the ring on an
  RTX 3090.
- **Captions** are drawn afterwards with PIL (Noto Sans, on a soft pill), so the 3D frames stay clean.

### Build-guide figures (`render/guide_figures.py`)

```
python3 render/guide_figures.py                     # all 12 figures: Blender on GPUs 0,1, then PIL (~3 min)
python3 render/guide_figures.py --only s3_bond,xsec # some figures (stale images are only removed on a full run)
python3 render/guide_figures.py --annotate-only     # redo the PIL annotations from render/build/guide/
python3 render/guide_figures.py --quick             # 40 % size, 16 spp -> render/build/guide_quick_out/
python3 render/guide_figures.py --xsec              # also rebuild the cross-section solids (FreeCAD)
```

- **Output.** `docs/build/img/*.jpg`, 1600 x 1000 JPEG q88, readable at 900 px wide:
  - `hero`, `exploded`, `xsec` and `strap_path`;
  - one figure per step, `s1_swd` ... `s8_charge`.

  On a full run, any other file in `docs/build/img/` is deleted.
- **The Blender pass** (128 spp, OptiX denoise) uses the docs/media look. It reuses
  `assembly_anim.ring_scene` and `jig_scene`, and adds three scenes of its own: the SWD jig with the
  board, the board bottom-up with the cell, and the module alone with a see-through charge clip.
  - For each figure it writes the raw render, a highlight mask and the 2D positions of its anchor
    points and paths, all to `render/build/guide/`. The mask is the highlighted part, emissive, with
    holdout on everything else.
  - The cross-section (`xsec`) comes from `render/build/guide_xsec.glb`. FreeCAD builds it from
    `mech/rev_c`: pod, flex with spine links, pads, worn foam dots, webbing and a 30 mm skin slab, cut
    at the middle pad.
- **The PIL pass** draws the annotations:
  - the step badge and title;
  - thin leader lines with white dot anchors;
  - Noto Sans labels, de-overlapped in side columns, with a light stroke;
  - orange motion arrows;
  - an orange outline round the highlighted part;
  - for `s6_strap`, a 2D side section of the slide's threading.

  The label text and placement are in `SPEC` at the end of the script.

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

### README JPGs

The board shots in `docs/media/` (`pcb_top`, `pcb_pair`, `xray`, `exploded`, `flatlay`) are the
`render/out/` PNGs scaled to a 1600 px long side (Lanczos) and saved as JPEG quality 88, which matches the
quantisation tables of the earlier files. These five, the assembly animation and the build-guide images
were re-rendered on 2026-10-29 from the final main board (`neurband_c.kicad_pcb` SHA-256 766f7908...,
DRC 0 errors, 52 warnings; CELL outline on the top silkscreen, vertical DOWN mark at J1) and the final
`mech/rev_c`. The other shots and the turntable are from the inputs below. To redo them:

```
python3 render/make_renders.py --shots pcb_top,pcb_pair,xray,exploded,flatlay
python3 render/assembly_anim.py --no-export && python3 render/assembly_anim.py --no-export --stills
```

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
