# To print

[Open the complete 12-piece black-and-blue X2D plate](neurband_22mm_complete_x2d.3mf) for the full band and the 18:11 jig shim. Assign black PLA Matte to filament 1 and blue PLA Matte to filament 2. The lid prints face down, with a flush 0.32 mm inlay on layers 1 and 2.

Open **reinforced_case_22mm_pla.3mf** in Bambu Studio for the revised cradle, holder, lid and two matched bars. Use the matching 31.95 mm bars with the revised cradle. It uses the X2D 0.4 mm nozzle and the 0.12 mm PLA Matte profile. The STEP files below are current, including the bonding jig with narrower locating tongues.

For the electrode change, [print the cradle and six pods together](contact_cradle_and_pods_22mm.3mf). The X2D plate has a 3 mm outer brim on each pod. The cradle has 0.28 mm more projection at both contact seats. All printable STEP files are in bed orientation.

| File | Qty | Material | Settings |
|---|---|---|---|
| `cradle.step` | 1 | PETG, ABS, ASA or PC (PLA fine for fit test) | **0.12 mm layers**, 5 walls, 100 % infill. Flat face down, curved wrist side up; 22.5 mm strap openings print with chamfered cross-bar slots with a 1.71 mm outboard wall at mid-ear and a rounded wrist-facing toe |
| `holder.step` | 1 | PLA, PETG, ABS, ASA or PC | 0.12 mm layers, 3 walls. Flat battery deck down, spring tabs up. The supplied plates add removable black support under the holder overhangs |
| `lid.step` | 1 | PETG, ABS, ASA or PC (PLA fine for fit test) | 0.12 mm layers, 3 walls. Unbroken flat top down |
| `lug_bar_x2.step` | 2 | PETG, ABS, ASA or PC (PLA fine for fit test) | **0.12 to 0.16 mm layers**, **100 % infill / 4 walls**. Prints flat on the bed so continuous filament strands run end-to-end |
| `pod_x6.step` | 6 | PETG, ABS, ASA or PC (PLA fine for fit test) | 0.12 to 0.16 mm layers, 3 walls. **Open-back side-ear clip pod for the 22 mm strap** (`8.0 × 30.2 mm`; `1.26 mm` centre plate + low-profile `±Y` C-ears) — prints flat on its `X = -4.0 mm` side edge so continuous filament loops wrap around both C-ears (zero supports, zero bridges; add a 3 mm outer brim if your bed needs extra grip) |
| `bond_jig.step` | 1 | PLA is fine | 0.20 mm layers. Check that all 12 pins printed |

Strap attachment: pop/unscrew the two black QuickFit clips off the ends of your `22 mm` Tech-Protect Nylon Classic strap to expose its sewn nylon loops, place each loop between `cradle`'s lug ears, and slide a printed `lug_bar` in from the `-Y` side until the `+Y` split snap-barb clicks flush.
See the [illustrated assembly and bonding instructions](../../../docs/build/assembly.md).

## Using an earlier bonding jig

Measure one of the two raised guides that fit between the cradle lugs and one of the six small platforms with a pair of pins. Measure both widths parallel to the line between the pins.

| Cradle guide width | Pod platform width | Setup |
|---|---|---|
| 21.8 mm | 16.7 mm | Seat the cradle and pods directly. |
| 25.8 mm | 16.7 mm | One cradle shim fits. The full adapter set gives more slack in the two short flex links during bonding. |
| 25.8 mm | 20.7 mm | Use the full adapter set. |

[The full adapter plate](legacy_bond_jig_adapters.3mf) contains two cradle shims and six pod caps. Stack the shims keyed face up over the raised wire-bay key, with their open notches facing the flex-tail channel. Place the cradle board-face down on the top shim. Slide one cap, pins up, onto each original pair of pins and seat each pod over the new pins. The complete set lifts all eight paddle seats by the same 3.36 mm relative to the jig. These pieces stay on the jig during bonding.

With the single-shim setup, use [one cradle shim](jig_cradle_shim.step) and place the pods directly over the original pins. This leaves only about 0.04 mm of nominal straight-line allowance in the shortest link with the foam unloaded. Align the dry flex on all twelve pins before exposing the adhesive. The full set leaves about 0.16 mm in that link and the new pins extend 0.58 mm past the unloaded flex.
