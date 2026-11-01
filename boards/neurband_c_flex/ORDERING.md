# Ordering the rev C electrode flex

The electrode flex is a two-layer polyimide flex. It is ordered through Backplane (**Buy it**):
`neurband_c_flex.fab.json` is `"kind": "flex"` with 2 layers, 0.11 mm, yellow coverlay, a 0.225 mm
polyimide stiffener and 2 µ" ENIG gold. The table below is what the order has to be; check the quote
against it, and paste the order notes at the end if the order asks for remarks. The evidence is in
[docs/review/manufacturing_preorder.md](../../docs/review/manufacturing_preorder.md) (§2, F1–F3,
FS2–FS4) and the design in [docs/layout/flex_c_layout.md](../../docs/layout/flex_c_layout.md).

| Item | Setting |
|---|---|
| Board | 133.1 × 38.5 mm outline, 2 copper layers, polyimide (PI) base, **finished ~0.11 mm**, 5 pieces, no assembly |
| Copper | Rolled-annealed (RA) copper, 12 µm (1/3 oz) both sides. Request explicit confirmation of copper type before production |
| Coverlay | PI coverlay **both sides** (yellow). F side opens only at the 24 round electrodes (`F_Mask`); B side opens only over the 20 fingers (`B_Mask`). Openings at the electrodes may take the fab's usual 0.1 mm expansion (closest other-net copper is 0.25 mm from an electrode) |
| Finish | **ENIG, 2 µ" gold**, on all exposed copper (skin electrodes and fingers) |
| Stiffener | **PI 0.225 mm on the F (top, skin) side**, the side opposite the exposed B-side fingers. Outline on layer **`User.2`**, named `Stiffener` (Gerber `neurband_c_flex-Stiffener.gbr`): 10.50 × 3.70 mm at the tail tip |
| Mating thickness | **0.30 ±0.03 mm total at the gold fingers** (0.11 build − one coverlay − one copper + 0.225 PI ≈ 0.296 mm). If the fab's stack differs, choose the stiffener that reaches 0.30 ±0.03 |
| Fingers | B side, 20 × 0.30 mm at 0.50 mm pitch, 3.2 mm exposed; tab width 10.50 mm |
| Outline | Laser cut per `Edge_Cuts`. Request **±0.05 mm on the 10.50 mm tail**; obtain the fab's tolerance confirmation before production |
| Holes | 60 × 0.30 mm plated vias (tented). **16 × 1.2 mm NPTH alignment holes, drilled through both coverlays, no coverlay pre-opening** |
| Quantity | 5 |

Files the fab needs: `F_Cu`, `B_Cu`, `F_Mask`, `B_Mask`, `F_Silkscreen`, `B_Silkscreen`, `Edge_Cuts`,
**`Stiffener`** and the PTH and NPTH drill files. Buy it exports all of them (a plain `kicad-cli pcb
export gerbers` includes the `Stiffener` layer). `User_1` holds only a design note and the Fab layers
only outlines; the fab can ignore them. No paste, position or BOM files: the flex has no parts.

## Order notes to paste

> 2-layer polyimide FPC, rolled-annealed copper, finished 0.11 mm. Coverlay both sides (yellow),
> openings per F_Mask (24 round electrodes) and B_Mask (finger window). ENIG 2 µ" on all exposed
> copper. Laser-cut outline; tail width 10.50 mm, please hold ±0.05 mm on the tail (Edge_Cuts).
> Stiffener: PI 0.225 mm on the F (top) side, area per layer User_2 (the stiffener layer, 10.5 × 3.7 mm
> at the tail tip, Gerber "Stiffener"), on the side opposite the exposed B-side gold fingers. Total thickness at the gold
> fingers 0.30 ±0.03 mm. 16 × 1.2 mm NPTH holes: drill through the coverlay, no coverlay pre-opening.
> No assembly. Qty 5.
