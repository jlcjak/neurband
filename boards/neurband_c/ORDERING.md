# Ordering the rev C main board

The main board is ordered through Backplane (**Buy it**). That flow exports the Gerbers, drill files,
`bom.csv` and the raw `kicad-cli pcb export pos` placement file and gets the fab's quote. Everything
below is what that order has to be; the evidence is in
[docs/review/manufacturing_preorder.md](../../docs/review/manufacturing_preorder.md).

| Item | Setting |
|---|---|
| Board | 28.7 × 27.0 mm, 4 layers, 1.0 mm, ENIG, black solder mask, 5 boards |
| Stackup | The fab's 1.0 mm four-layer build with ~0.0994 mm prepregs ("3313" class), matching the KiCad stackup. Confirm this construction for the 0.16 mm post-match RF feed |
| Assembly | 2 of the 5 boards, top side only, the fab's standard assembly service (black mask + ENIG on 4 layers is not offered in the economy tier). Small board: the fab adds its own rails and fiducials; snap the rails off gently |
| Parts | `neurband_c_bom.csv`: every line has its MPN and the fab's part number; 6 extended parts (U1, U2, U5, Y1, J1, C21) |
| Placement | The footprints of U1, U2, U3, U4 and RN1–RN4 carry the fab's 0° orientation, and J1's anchor is its pad centre, so the raw position file is already in the fab's convention. Pin-1 dots (and D1's cathode bar) are on the silkscreen; the raw position file and actual pad numbering are the assembly authority. Do **not** apply a rotation database on top |
| DNP | C22, C23 (antenna tuning shunts) are not fitted; R3 is 0 Ω |

The electrode flex is **not** part of this order: the rigid-board flow cannot express a polyimide flex
(see [../neurband_c_flex/ORDERING.md](../neurband_c_flex/ORDERING.md)). Printed parts are ordered
from their own `mech/rev_c/*.fab.json`.
