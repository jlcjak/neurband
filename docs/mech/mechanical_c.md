# neurband rev C mechanical design (8 pods, one size M)

Rev C is a small, clean 8-channel bipolar band. The design language is a premium consumer
wearable: one **continuous woven band**, a small pebble module and no visible clips, lugs or pins.
It comes in **one size, worn on 145-180 mm wrists**.

**To build one, follow [docs/build/assembly.md](../build/assembly.md)** (ordering, printing, gluing,
bring-up, the assembly sequence with images, strap, charging, troubleshooting).

All CAD is in `mech/rev_c/` as FreeCAD scripts, one per part, with the named parameters at the
top. Units are mm, Z is up and the front faces -Y. Every script checks `isValid()` and writes
`.FCStd`, a coloured `.step` and a log in `mech/rev_c/logs/`. Rev A/B (`mech/*.py`,
[mechanical.md](mechanical.md)) are untouched; the shared helpers `mech/cadutil.py`,
`mech/fitgeom.py` and `extra/wrists/wrist.py` are reused, and wrist.py gained a 145 mm size.

```
QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/<part>.py
build order: pod.py, module.py, strap.py, charge_puck.py, fit.py, assembly.py
```

![band](../../mech/rev_c/renders/band_assembly.iso.png)
![band front](../../mech/rev_c/renders/band_assembly.front.png)
![on the 160 mm wrist](../../mech/rev_c/renders/fit_160.iso.png)

## 1. Summary

| | |
|---|---|
| Module | **31.9 x 34.3 x 9.9 mm** (across x along the arm x thickness at the apex). R3.4 plan corners; the crowned lid has R2.5 blends and the underside is a R42 hollow. The body edges hang 3.1 mm lower, 13.0 mm overall. There are no external lugs: the strap enters hidden slots in the two end faces. The button is a flush disc and the light pipe a flush dot. It stands 10.5-10.8 mm above the skin |
| Strap | **One continuous 22 x 1.2 mm elastic woven webbing** (loop-fabric face) around the whole outside. Two identical slim printed loops snap onto the hidden integral bars. The ulnar end is sewn round one loop's far bar; the radial end passes through the other loop and folds back with a 40 mm hook tab. Opens fully |
| Pods | 6 TPU pods, 9.0 x 32.0 x 3.9 mm with 1.0 mm minimum walls. They cover the whole 30 mm flex paddle, so no flex shows, and their ends taper to 2.0 mm beyond the band edges. The webbing slides through a captive edge sleeve; only the soft tapered pod ends show beyond the band. Pods 3 and 4 sit in the module underside |
| Contact | Each 6.5 mm gold pad sits on a 6.0 x 1.5 mm self-adhesive foam disk in a 6.2 x 0.5 mm pocket, so it stands 1.0 mm proud (about 0.65 mm when worn). P-N spacing is 20 mm |
| Sizes | One size. A wrist of 145 / 160 / 180 mm leaves a 17 / 32 / 52 mm gap between pods 1 and 8 on the volar-ulnar side, which the band bridges. The electrodes cover 89 / 81 / 72 % of the circumference |
| Materials | MJF PA12 (natural grey or dyed black) for the module base, lid, button cap and strap loop. TPU 95A for the pods (own FDM printer, on their side, or MJF TPU). Bought webbing, foam and hook tape |
| Charging | The board's bottom pads VCHG/GND are reached through a 1.7 mm deep window in the module underside, with 2 magnets and a printed pogo puck. Skin cannot reach the pads, so the band cannot charge while worn |
| Printability | Every printed part has walls of at least 1.0 mm, measured on the exported STEPs (`wallcheck.py`, sec. 8) |
| Mass (estimate) | About 5 g of printed parts, plus the board, the 401225 cell (about 3 g), the webbing and the flex: roughly 15 g |

## 2. Concept and frame

The wrist frame is the same as rev A/B (`mech/fitgeom.py`): right forearm palm down, X radial (+) /
ulnar (-), Y along the arm with the hand toward -Y, Z dorsal. The band centre line is 25 mm
proximal of the crease. The module frame has its origin at the apex of the module underside on
that line.

- **The module is two electrode pods plus the electronics.** The flex tail leaves the strip
  between pods 3 and 4, so the module sits over them, centred on the dorsal side. Its curved
  underside carries flex pods 3 and 4 at an arc of +/-9 mm (foam pockets and locating pins,
  exactly like a pod shell).
- **Flex tail U-turn.** The tail leaves the strip's distal edge (y = -15) heading distal. It
  bends up (R1) through a floor slot next to the distal wall and bends again (R1) into J1. The
  path is 8.2 mm, which is why the tail is 8.5 mm with the stiffener only on the last 3.7 mm (as
  agreed with the flex layout). The tail fingers are on the non-skin side.
- **Continuous band, sliding pods.** The webbing runs through every pod sleeve and slides freely.
  This is essential: the flex links between pods are inextensible (18 mm pitch), while elastic
  webbing stretches 5-15 % when worn. Pods fixed to the webbing would pull the flex apart. The
  flex sets the pod positions and the webbing only presses them on. The 22 mm webbing presses the
  middle 22 mm of each pod. The pod's 1.0 mm-wall TPU shell, a box 3.9 mm deep, carries that load
  to all three pads.
- **Module-edge spine links** (pods 3 to 2 and 4 to 5) leave the paddle edge along the R42 seat
  and hang free on a smooth tangent curve to pod 2/5. They pass under the loop clips and the
  strap's wraps round the loops' far bars with at least 0.1 mm clearance and bend at R2.3 mm or
  more. The strap is always outside the flex.
- **The gap** between pod 1 and pod 8 (17-52 mm) lies on the volar-ulnar side, centred
  137-145 deg from the dorsal centre. The band bridges it, so from outside the band is
  continuous.

## 3. Module (`module.py` -> `module_base`, `module_lid`, `button_cap`, `module_assy`)

![module](../../mech/rev_c/renders/module_assy.iso.png) ![end slot](../../mech/rev_c/renders/module_assy.right.png)
![base](../../mech/rev_c/renders/module_base.iso.png) ![section](../../mech/rev_c/renders/module_section.right.png)

(`module_section.step` is a cut at X = +3 mm, distal end on the left. It shows the tail U-turn
into J1, the board on its supports, the cell over the TQFP and the pod 3/4 foam and pads under
the floor.)

**Shape.** The plan is a 31.9 x 34.3 mm rounded rectangle with R3.4 corners, offset +0.35 mm
radially because the board is 28.7 mm wide on its +X side. The corner radius was reduced from 5.5
so the strap slots keep 1.0 mm side walls; with R5.5 the slots cut into the corner arcs and left
0.2 mm slivers. The underside, pods 3/4 and the tail stay on
the dorsal centre.
- The lid is a single soft crown (R65 across the wrist) with R2.5 blends into the walls. R2.5 is
  the largest blend that keeps the lid clear of the cell's proximal end.
- The underside is a R42 hollow along the arm with R1.4 edge blends.
- The **parting surface runs at a constant 2.0 mm above the underside**, so the seam follows the
  curve as a 0.3 x 0.12 mm hairline.
- Walls are 1.1 mm, the floor 1.1 mm and the top 1.0 mm. A 3 mm pry notch sits at the proximal
  seam.
- Behind the pod 3/4 foam pockets, the floor has 1.0 mm bosses inside. The pockets are cut from
  below the curved underside, so no feathered skin is left at their mouths.
- The distal wall keeps a square bottom edge across the tail slot, where there is no floor behind
  it. That keeps its 1.1 mm all the way down.

**Hidden strap attachment.** Each X end face has a slot 24.8 mm wide (along the arm), 3.35 mm deep
and open underneath, through which the webbing enters the body. It looks like a watch band slot.
The slot has 1.0 mm side walls and a 1.0 mm roof (slot top 0.7 under the board bottom at 1.7).
Below z = -0.25 the slot stops 1.0 mm short of the pod 3/4 foam pockets; only the part that
holds the loop clip is full depth (3.35 mm).
- Inside each slot an **integral PA12 bar** (1.3 x 1.6 mm stadium section, rated for about 5 N of
  strap tension) spans the slot at z = -0.8, 0.6 mm in from the end face, so its outer face is
  flush. There are no pins, no metal, and nothing protrudes.
- An identical slim loop snaps onto each bar. The webbing never wraps the bars themselves, so
  nothing bulky sits under the module edge and the flex links pass beneath on a gentle curve.
- Ulnar side: the webbing end is sewn round its loop's far bar (fixed).
- Radial side: the webbing passes through its loop and folds back (closure).
- The slot roofs are the board's supports: both X edges of the board rest on them (KiCad
  x 0..2.75 and 25.95..28.7). A 1 mm relief under the J2 battery pads leaves room for the wire
  joints. The separate standoffs were removed because they overlapped the roofs.
- **Snap:** four square snap features on the +/-Y walls. The X walls carry the slots, and round
  beads would leave sub-1 mm tips and lips.
  - Each is a local tongue riser, 1.3 mm thick and 3.0-4.5 mm long, with a 0.3 x 1.2 mm groove and at
    least 1.0 mm of material on all sides.
  - A 1.0 mm tall rib on the lid, 0.35 mm deep, clicks into the groove. Its top sits 0.15 mm below the
    groove's top, which absorbs height tolerance, so the catch is 0.25 mm.
  - A 0.3 mm 45 deg lead-in chamfer on the riser's top outer edge cams the lid wall out as the lid goes
    on. The lip above the groove stays 1.0 mm thick under the chamfer.
- **Tongue clearance.** Above the parting surface the tongue (1.3 mm) is 0.1 mm clear of the lid's
  inner wall. Before it was line-to-line, which MJF or FDM tolerance would turn into an interference
  fit. Below the parting surface the tongue is solid with the wall, so no slit is left.
- **Clear of J1 for the fold-in.** The tongue is cut back to x = +/-7.5 over the tail U-turn, and the
  distal snaps start there. J1 is 14.4 mm wide, so the board can be plugged onto its tail standing
  upright and folded into the base without its connector catching on a riser
  ([assembly.md](../build/assembly.md) sec. 6.5). With the board flat, the tail has 0.3 mm of slack:
  it cannot be plugged in that way.
- **Battery-lead gate.** The tongue is also cut away on the distal wall from x = +10.5 to the +X corner,
  in front of SW1. The battery pads J2 are on the board's underside. Elsewhere the board edge is 0.2 mm
  from the tongue and 0.5 mm from the lid wall, and no wire fits there. So the two 30 AWG leads run in the
  1.0 mm J2 relief, wrap the board's distal edge through the gate, and come up past SW1's outer end to the
  cell. This is also the hinge line when the board is folded out for re-flashing.

**Lid details.**
- **Button:** a 4.3 mm PA12 disc (`button_cap`) in a 4.6 mm opening over SW1. The 0.15 mm hairline was
  0.1 mm, too tight for MJF or FDM tolerance.
  Its flat top sits just below the lowest point of the crown around it, so it reads as a subtle
  flush pad with no knife edge. It is retained by a 6.0 x 1.0 mm flange under the lid, and its
  stem stops 0.15 mm above the switch. It is a separate part, put in from inside before the lid
  closes.
- **Light pipe:** a 1.5 mm PMMA rod (or clear UV resin) in a 3.6 mm guide tube (1.0 mm wall) over
  D1, cut flush with the crown.

**Stack at the centre (z above the underside apex).**

| z (mm) | item |
|---|---|
| 0-1.1 | floor; pods 3/4 foam pockets 0.5 deep on the outside, with 1.0 mm bosses behind them |
| 1.1-1.7 | 0.6 mm gap for bottom pads and wire joints (SWD, battery, charge pads) |
| 1.7-2.7 | board, 28.7 x 27 x 1.0 mm (`boards/neurband_c/neurband_c.step`) |
| 2.7-4.7 | parts: J1 FPC and SW1 2.0 mm, TQFP 1.2 mm |
| 4.15-8.15 (+0.3 swell) | LiPo 401225 on 0.15 mm tape over KiCad x 10.5-22.5, y -3.3..21.7 (on the final board the parts under it are at most 1.11 mm: the TQFP; the 0603 caps are 0.92 mm or less), proximal of J1 and clear of the antenna region (x 0..5.65, y 11.65..27) |
| 8.9-9.9 | lid top |

**Charging, with a safety interlock by geometry (signal-chain review sec. 7).**
- VCHG and GND are board bottom pads at KiCad **(14, 6) and (14, 9)**. They were moved off the
  flex spine, which runs under the module centre strip at y -7..+0.6.
- They sit in a 3.0 x 6.0 mm stadium window, **1.7 mm deep** (at least 1.5 mm), at module
  y 1.7..7.7. When worn the pads are about 2.4 mm from the skin, so skin cannot touch them.
- Two N52 3 x 1 mm magnets sit in **through holes**, glued flush with the underside at
  (x = +/-2.1, y = 11.25). They are proximal of the window with 1.0 mm webs, clear of the spine
  and of the antenna region, so no thin skin is left over them. Set them N/S to key the polarity;
  they also locate the charger, so there is no counterbore.
- `charge_puck.step` carries two 2.0 x 6 mm pogo pins, staggered +/-0.5 mm across the 2 mm pads
  (1.1 mm web between the holes), and two magnets of opposite polarity, glued flush under flat
  spot faces. It has a USB lead. It has no nose: the magnets centre it.

![puck](../../mech/rev_c/renders/charge_puck.iso.png)

**Clash check** (`logs/module_checks.json`, against the real `boards/neurband_c/neurband_c.step`):
board, parts, cell (including the swell box), tail, button cap, base and lid are all at
0.00-0.006 mm3, which is tessellation level. The tallest part under the cell is the TQFP at 1.11 mm (final board STEP, 0603 caps at most 0.92 mm, all under the 1.3 mm limit), and SW1 (2.0 mm) sits 0.14 mm under the cap stem. Measured clearances: cell to lid 0.09 mm at its proximal +X top corner, cell to parts 0.15 mm, cell to the charger IC U4 (1.56 mm tall, outside the cell zone) 0.45 mm, cap to lid 0.15 mm.

**Printing.** MJF PA12 is the recommended process: the snaps, clip and integral bars need its
toughness, and it needs no supports. On your own FDM printer, stand the base and lid on their proximal
end faces in PETG at 0.12 mm layers. The crown, the R42 underside and the slot roofs then need no
supports; only the lid's light-pipe tube does. The integral bars print vertically and are weaker in
bending, so an FDM base is for fit tests. Per-part settings and the tolerance checks are in
[assembly.md](../build/assembly.md) sec. 3.

## 4. Electrode pods and compliant contact (`pod.py` -> `pod.step`, `pod_with_flex.step`)

![pod](../../mech/rev_c/renders/pod_with_flex.iso.png) ![pod shell](../../mech/rev_c/renders/pod.iso.png)

- **Shape.** A TPU 95A pebble, 9.0 x 32.0 x 3.9 mm (4.75 mm above the skin when worn), with R0.8
  top and face blends. It covers the whole 30 mm flex paddle, and the ends taper from 3.9 mm at
  the sleeve rims to 2.0 mm at the tips.
- **Walls:** at least 1.0 mm everywhere (FDM TPU: 2.5 perimeters at 0.4 mm). The floor behind the
  foam pockets is 1.0 mm and the sleeve rims are 1.0 mm thick. That is why the pod is 3.9 mm
  rather than 3.2 mm: with the 1.5 mm foam kept, there is no thinner way. The face blends are the strain relief where the flex
  spine leaves at +/-X (y -7..+0.6).
- **Captive edge sleeve.** A 22.4 x 1.4 mm slot runs through the pod along the band. Its roof is
  open over the middle 19.4 mm, so the fabric stays visible, and two 1.5 x 1.0 mm rims hold the
  webbing edges. To assemble, thread the webbing through the pods; it cannot pop out and slides
  freely. Nothing protrudes: from outside the pods read as small soft bumps under the band.
- **Compliant contact** (signal-chain review sec. 2). A 6.2 x 0.5 mm pocket behind each pad
  (y = -10/0/+10) holds a 6.0 x 1.5 mm **double-sided** adhesive PU or PE foam disc (6 mm punch), so the pad stands
  1.0 mm proud when free and about 0.65 mm when worn. The flex is held only by the adhesive foam
  and floats between the pads (polyimide cannot be forced into a dome).
- **Locating pins.** Two pins, 1.0 mm diameter and 0.55 mm tall, sit at y = +/-5 in the flex's
  1.2 mm holes (0.2 mm clearance, not a press fit).
  - The free foam stands 1.0 mm proud, so the adhesive meets the flex 0.45 mm before the pins reach
    the holes. The pins cannot pull a misplaced flex into line.
  - Sight the holes onto the pins first: rest a needle through each hole on its pin's domed tip, then
    slide the flex down ([assembly.md](../build/assembly.md) sec. 6.4).
  - The pins then hold the flex while you press, disengage when worn and stop over-compression. They
    must stay shorter than the worn foam (0.65 mm), or they would poke the skin through the holes.
- **Tuning.** If a pod reads poorly, use a thicker or denser foam disk.

**Pressure.** The load on a pod is T x (wrap angle). About 0.4 N of strap tension gives about
3 kPa per pad; a firmly closed band (1-2 N) gives about 7-15 kPa.

## 5. Strap (`strap.py` -> `strap_loop.step`; the webbing is a swept band in the assemblies)

![loop](../../mech/rev_c/renders/strap_loop.iso.png)

**Chosen: one continuous 22 x 1.2 mm elastic woven webbing** with a loop-fabric face
(off-the-shelf 7/8 in elastic hook-and-loop band; plain elastic webbing plus 110 mm of sew-on
loop tape also works). Keep it at 1.2-1.4 mm: the wraps round the loops' far bars pass just over the
spine links.
- **Ulnar end:** fixed, sewn round the far bar of a slim loop snapped onto the hidden ulnar bar.
- **Around the wrist:** the webbing runs through the six pod sleeves and across the gap.
- **Radial end:** it passes through the identical loop on the radial side. Each loop is
  24.4 x 6.4 x 3.8 mm, with 1.0 mm side links and a 1.0 mm C-clip.
- The clip's 80 deg opening points up, away from the strap pull, so tension seats the clip on the
  bar. It snaps on with 0.14 mm interference over the bar's 1.3 mm side.
- The ulnar loop is the same part turned over. The webbing turns
  round the loop's far bar and folds back over its own outer face, closing with a 22 x 40 mm hook
  tab.
- The fold-back is 77 / 63 / 45 mm on 145 / 160 / 180 mm wrists. The whole band opens by peeling
  the tab and pulling the end out of the loop.

Why 22 mm: the module's strap slots must keep 1.0 mm walls beside the straight part of the end
faces. Slot half-width + 1.0 mm cannot exceed the straight half-length (17.15 mm minus the plan
corner radius). For a 25 mm band (27.4 mm slot) that would need corners of R2.4 or less, a boxy
module. The 22 mm band (24.8 mm slot) allows R3.4.

The cost is that the 32 mm pods show about 5 mm of their tapered TPU ends at each band edge; the
flex stays covered. The band presses the centre 22 mm of each pod, and the stiffer 1.0 mm-wall
TPU shell spreads it to the outer pads.

Alternatives considered:
1. Two-piece webbing with a printed buckle ring at the gap (the previous version). Rejected: it
   puts a visible buckle on the volar side and breaks the continuous look.
2. An off-the-shelf nylon sport loop with spring bars. It is 2-3 mm thick and would need steel
   spring bars next to the antenna.
3. A printed TPU band with tang buckle. It is not elastic and adjusts in steps.
4. Shock-cord tensioner (Meta sEMG-RD style). The most uniform load, but cord and cord lock look
   technical.

**Cut list (from `fit_results.json`):** 2 strap loops; webbing **226 mm**, including the 12 mm sewn loop round
the ulnar loop's far bar and a 45 mm fold-back at 180 mm. Hook tape 22 x 40 mm.

## 6. Fit check (`fit.py` -> `fit_results.json`, `fit_145.step`, `fit_180.step`; `assembly.py` -> `fit_160.step`, `band_assembly.step`)

![145](../../mech/rev_c/renders/fit_145.iso.png) ![160](../../mech/rev_c/renders/fit_160.iso.png) ![180](../../mech/rev_c/renders/fit_180.iso.png)
![160 top](../../mech/rev_c/renders/fit_160.top.png)

The wrist model is the rev A/B ellipse forearm (`extra/wrists/wrist.py`), now also built at
145 mm. In each case:
- the module rests centred on the pads of pods 3 and 4, with the foam at its worn compression;
- the free pods sit 18 mm apart along the flex, tangent to the wrist, and are tilted to follow
  the forearm taper (the module tilts 2.7-3.4 deg);
- the webbing is taut, modelled as the convex hull of the hidden ulnar bar, the pod sleeves, the
  skin across the gap and the loop's far bar, then swept as one smooth B-spline band;
- collisions are CAD Boolean volumes.

| | 145 mm | 160 mm | 180 mm |
|---|---|---|---|
| Model wrist semi-axes a x b (mm); dorsal / side radius | 25.9 x 20.1; R 33.4 / 15.6 | 28.6 x 22.2; R 36.8 / 17.2 | 32.1 x 24.9; R 41.4 / 19.3 |
| Gap between pod 1 and pod 8, edge to edge (mm) | 17.2 | 32.2 | 52.2 |
| Gap centre from the dorsal centre (90 = ulnar apex, 180 = volar centre) | 137 deg | 141 deg | 145 deg |
| Electrode coverage (pod 1 to pod 8 arc / circumference) | 88.6 % (128.4 mm) | 80.5 % (128.9 mm) | 71.8 % (129.3 mm) |
| Pod collisions (shell-shell, shell-module, CAD mm3) | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| Spine bend radius, min free link (mm); module-edge links (free, under the loops) | 10.51; 2.46 | 11.81; 2.28 | 13.44; 2.42 |
| Module seat gap underside-skin: centre / edge (mm) | 0.61 / 1.63 | 0.73 / 1.3 | 0.85 / 0.97 |
| Module tilt following the forearm taper | 2.72 deg | 3.0 deg | 3.37 deg |
| Strap loop far bar clearance to skin (mm) | 2.19 | 2.11 | 2.03 |
| Module / pod shells vs. skin (CAD mm3); strap inner face to skin, min (mm) | 0.0 / 0.0; 1.11 | 0.0 / 0.0; -0.33 | 0.0 / 0.0; -0.48 |
| Strap vs. pods / module; loop vs. module / pods (CAD mm3) | 0.0 / 0.0; 0.0 / 0.0 | 0.0 / 0.0; 0.0 / 0.0 | 0.0 / 0.0; 0.0 / 0.0 |
| Strap load per pod, relative (pods 1, 2, 5, 6, 7, 8) | 1.41, 0.88, 0.78, 1.26, 0.79, 0.87 | 1.59, 0.73, 0.63, 1.26, 0.84, 0.96 | 1.63, 0.61, 0.50, 1.27, 0.98, 1.01 |
| Strap load max / min | 1.8 | 2.54 | 3.26 |
| Strap tension for 3 kPa on an average pad (N) | 0.39 | 0.4 | 0.44 |
| Strap path ulnar bar -> loop (mm); fold-back (mm) | 125.0; 77.1 | 138.7; 63.4 | 157.0; 45.0 |
| Pads pressed into the rigid wrist model (taper; foam/skin take it, CAD mm3) | 11.505 | 12.222 | 13.344 |
| Strap vs. flex links (CAD mm3) | 0.0 | 0.0 | 0.0 |

Notes:
- **Gap and the ulna.** The flex chain is 133 mm long, so the gap absorbs the 35 mm size range.
  Pod 1 lands within about 10 deg of the ulnar apex (108 / 98 / 87 deg).
- **Bend radius.** The free spine links bend at R10.6 mm or more and the module-edge links at
  R14.5 mm or more, at least 3.5x the 3 mm rule.
- **Module seat.** Only the 6 pads touch. The underside clears the skin by 0.6-0.85 mm at the
  centre and 1.0-1.6 mm at the edges.
- **Strap.** The webbing rests on the skin across the gap. Strap-vs-pod volume is measured with
  untilted pods: the 1-3 deg taper tilt of each pod is taken by a slight twist of the webbing.
  The module-edge links hang free from the R42 seat to pods 2/5 and bend at R2.3-8.8 mm (the
  tightest is the ulnar link), well above the 1.2 mm guideline for 2-layer flex. The load spread across pods is 1.8-3.3:1. Pods 1 and 6 carry the most; pods 2 and 5 next to
  the module the least.

## 7. Interface to the board and flex

- **Board** (`boards/neurband_c/neurband_c.step`, 28.7 x 27 x 1.0 mm):
  - J1 centred at x = 14 with its mouth on the y = 27 edge;
  - SW1 at (24.8, 25.1), D1 at (2, 1), and J2 (bottom) at (23.9, 25.6)/(26.9, 25.6);
  - **J3 VCHG/GND must be at (14, 6)/(14, 9)**, as agreed with the coordinator; the window and the
    magnets (KiCad (11.9, 0.95)/(16.1, 0.95), under the board) follow that position;
  - the board rests on the two lug-slot roofs along its X edges, KiCad x 0..2.75 and 25.95..28.7
    (y -1.2..25.6), with no separate standoffs. Keep bottom copper off those strips; J2 has its
    own relief in the +X roof;
  - parts under the cell rectangle must be at most 1.3 mm;
  - the mapping is KiCad (x, y) to module (x - 14, -14.8 + 27 - y) (`module.k2m`).
- **Flex** (`flex_c_layout.md`):
  - pods 7.1 x 30 at an 18 mm pitch, 1.2 mm holes at +/-5, spine at native Y -0.6..+7.0;
  - the tail is 8.5 mm long with the stiffener on the last 3.7 mm, fingers on the non-skin side,
    and is mirrored at the fingers;
  - the outline is otherwise as used here.

## 8. Parts, fab files and cost

| Part | File | Process / material | Qty (fab) | Size mm | Volume cm3 |
|---|---|---|---|---|---|
| Module base | `mech/rev_c/module_base.step` | MJF PA12, grey | 3 | 34.5 x 32.1 x 7.8 | 1.56 |
| Module lid | `mech/rev_c/module_lid.step` | MJF PA12, grey | 3 | 34.5 x 32.1 x 11.1 | 1.95 |
| Button cap | `mech/rev_c/button_cap.step` | MJF PA12, grey | 4 | 6.0 x 6.0 x 3.7 | 0.06 |
| Pod shell | `mech/rev_c/pod.step` | TPU 95A (FDM or MJF TPU), black | 16 (2 bands + 4) | 32.1 x 9.1 x 4.5 | 0.51 |
| Strap loop | `mech/rev_c/strap_loop.step` | MJF PA12, black | 5 (2 per band) | 24.4 x 6.8 x 3.8 | 0.22 |
| Charger puck | `mech/rev_c/charge_puck.step` | MJF PA12 or FDM PETG | 2 | 30.1 x 26.1 x 7.1 | 3.65 |

The fab files are `mech/rev_c/<part>.fab.json` (kind 3dp; volume, area and size measured from the
FreeCAD shapes, plus `min_wall_mm` from the wall check).

**Minimum wall per part** (`wallcheck.py` on the exported STEPs -> `wall_check.json` and
`min_wall_mm` in each fab.json). Rays are shot along the inward normal from a grid on every face
(0.3 mm in from the edges) and intersected exactly with the solid. A ray counts as a wall only
where it leaves through a roughly opposite face, so acute rims, such as the lid's edge where the
curved parting meets the wall at 21 deg, are not reported as walls.

| Part | Process | Min wall measured (mm) | 1st percentile (mm) | Samples | Design minima |
|---|---|---|---|---|---|
| module_base | MJF PA12 | **0.98** | 1.00 | 6063 | walls 1.1, floor 1.1, 1.0 behind the pod 3/4 foam pockets, tongue 1.3 (1.0 behind the 0.3 snap groove, a 1.0 lip above it even under the lead-in chamfer), slot side walls and roof 1.0, magnets in through holes. The 0.98 spots are the distal wall's square bottom edge across the tail slot, unchanged |
| module_lid | MJF PA12 | **0.98** | 1.00 | 4147 | walls 1.1, crown 1.0, light-pipe tube 1.0, square snap ribs 0.35 x 1.0 on the 1.1 wall |
| button_cap | MJF PA12 | **1.00** | 1.00 | 339 | flat-topped 4.3 mm disc, flange 6.0 x 1.0, stem 2.0 |
| strap_loop | MJF PA12 | **1.00** | 1.00 | 838 | C-clip 1.0 (80 deg opening), side links 1.0, far bar 1.3 x 1.6 |
| charge_puck | MJF PA12 / FDM PETG | **1.00** | 1.29 | 1577 | magnet pocket walls >= 1.5, pin-hole web 1.1 (staggered pins), solid body |
| pod | FDM TPU 95A | **1.00** | 1.00 | 1485 | floor behind the foam 1.0, sleeve rims 1.0, foam-pocket-to-side 1.1 |

Bought parts per band (specs in [assembly.md](../build/assembly.md) sec. 1):
- 22 mm (7/8 in) elastic woven webbing with a loop face (0.25 m) and a 22 mm sew-on hook tab;
- double-sided (both faces adhesive) foam tape, 1.5-1.6 mm (24 discs: 18 for the pods, 6 for the module);
- 4 N52 3 x 1 mm magnets, 2 x 2.0 x 6 mm pogo pins and a USB lead;
- 1.5 mm PMMA fibre;
- a protected 401225-class LiPo, at most 4.0 x 12.0 x 25.0 mm overall including its protection board;
- 30 AWG PTFE or Kynar wire (battery leads), thin double-sided tape, Kapton tape, a soft foam pad.

Together these are about 6-10 EUR.

**Cost.** MJF PA12 from the fab is roughly 1.5-3 USD per part (the per-part minimum
dominates), so the 5 PA12 parts per band (base, lid, cap, 2 loops) cost about 8-15 USD. The six TPU pods on your own FDM
printer use about 1.5 g of TPU, well under 0.10 EUR. These are estimates; take the live quote
from the fab files.

## 9. Assembly

The full sequence, with images, is in **[docs/build/assembly.md](../build/assembly.md)**. The steps
that drive the mechanics:

1. **Flash first.** SWD (TP1-TP5) and the battery pads (J2) are on the board's underside and cannot be
   reached once the board sits on the slot roofs. Flash and bench-test the bare board, then solder two
   40 mm, 30 AWG leads flat onto J2. Each lap joint must stay under 0.5 mm in the 1.0 mm J2 relief.
2. **Magnets.** Glue the base magnets in first, with opposite poles out. The base then sets the puck's
   magnets: they snap onto the base's magnets through cling film, and the base is lowered onto the puck
   until the glue cures.
3. **Flex.** Fit 24 double-sided foam discs. Bond the flex to the base pockets and to each pod, sighting
   the holes onto the pins with needles. Tape the flex root to the underside as the tail's strain relief.
4. **Book fold.** The tail goes up through the floor slot and stands upright. Hold the board upright
   above the distal end, J1's mouth down, and lower it onto the tail. Close the latch and fold the board
   down onto the slot roofs. The leads wrap the distal edge through the lead gate.
5. **Cell.** Tape it on the ADS1298 against J1's back, splice its leads to the board leads one at a
   time, and add a soft foam pad on top against rattle.
6. **Lid.** Put the light pipe in (cut flush with the tube's inner end, 0.3 mm above D1) and the button
   cap, then snap the lid on. Open it with a pick at the proximal pry notch.
7. **Strap.** Sew (or glue) the webbing round the far bar of one loop and snap it onto the ulnar bar,
   with the clip's gap facing up. Thread the webbing through the six pod sleeves. Snap the second loop
   onto the radial bar, pass the end through it, fold back and press the hook tab.
8. **Wear and charge.** Wear the module on the back of the wrist, about 25 mm above the crease. To
   charge, take the band off and lay it module-down on the puck.

## 10. Open issues

- **J3 position** must move to (14, 6)/(14, 9) on the board (agreed, not yet in the 03:12 PCB).
- **Antenna.** The plastic-only region (KiCad x 0..5.65, y 11.65..27) is kept free of metal by
  the module (integral bars, magnets at x 10.4/17.6). Pod 3's flex lies below it (pod 4 in the flex's
  own numbering). Tune with the band worn.
- **Pod load spread** is up to 3.3:1 on 180 mm wrists; pods 2 and 5 next to the module carry the
  least. A 0.5-1 mm shim in their sleeves evens it out.
- **Strap bars are integral PA12** (about 5 N). If a bar ever cracks, drill 1.6 mm and use a
  1.5 mm steel spring bar, on the radial side only.
- **Module size:** 31.9 x 34.3 mm, set by the 28.7 mm board and the 25 mm cell.
- **Foam choice and pressure.** Measure contact impedance per channel against strap tension
  (signal-chain review sec. 2).
- **No sealing** (snap lid). The charge window is open to sweat; wipe it, or conformal-coat the
  board bottom outside the pads.
- **Board-side wishes for a rev D**, to make assembly easier (the rev C board interface is frozen):
  - top-side or edge-castellated battery pads near the cell's lead end, which would remove the lead gate
    and the 0.6 mm joint-height limit;
  - SWD reachable without taking the board out: top-side pads by the J1 edge, or a BLE DFU bootloader;
  - the final board's top silkscreen has a **CELL** outline at x 10.5-22.5 (the module's cell position),
    a vertical **DOWN** mark between J1 and SW1 and J1's pin-1 mark. x 11-23 would be the +X limit,
    where the cell touches the proximal +X snap riser and has 0.05 mm to the lid. On a rev D, the
    "CELL" label (now under U2) and the outline segments under U1/U2 could move to where they stay
    visible after assembly, and the flex tail could get a matching pin-1 mark.
- **Pod names.** This document and `fit.py` number the pods in the mirrored order of the real flex
  (`docs/layout/flex_c_layout.md`, "Pod under the main-board antenna"). The pods are identical, so the
  mechanics and assembly are unaffected; only the channel names differ.
