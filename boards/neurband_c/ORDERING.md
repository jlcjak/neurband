# Ordering the rev C main board

The main board is ordered through Backplane (**Buy it**). That flow exports the Gerbers, drill files,
`bom.csv` and the raw `kicad-cli pcb export pos` placement file and gets the fab's quote. Everything
below is what that order has to be; the evidence is in
[docs/review/manufacturing_preorder.md](../../docs/review/manufacturing_preorder.md).

| Item | Setting |
|---|---|
| Board | 28.7 × 27.0 mm, 4 layers, 1.0 mm, OSP, green solder mask, 5 boards |
| Stackup | **JLC04101H-3313** (0.0994 mm prepregs, 0.7 mm core), matching the KiCad stackup; the RF feed is ~50 ohm only on this build. It rules out the economy assembly tier |
| Assembly | 2 of the 5 boards, top side only, the fab's standard assembly service (black mask + ENIG on 4 layers is not offered in the economy tier). Small board: the fab adds its own rails and fiducials; snap the rails off gently |
| Parts | `neurband_c_bom.csv`: every line has its MPN and the fab's part number; 6 extended parts (U1, U2, U5, Y1, J1, C21) |
| Placement | The footprints of U1, U2, U3, U4 and RN1–RN4 carry the fab's 0° orientation, and J1's anchor is its pad centre, so the raw position file is already in the fab's convention. Pin-1 dots (and D1's cathode bar) are on the silkscreen; the raw position file and actual pad numbering are the assembly authority. Do **not** apply a rotation database on top |
| Antenna match | L2 = 5.1 nH series, C23 = 0.5 pF shunt (pre-tuned for the wrist, docs/science/antenna_sim.md); C22 is DNP |

**Status (2026-11-02): in the cart.** 5 boards, 2 assembled (standard tier), OSP, green, JLC04101H-3313, no file or placement confirmation; files in `mfg/order_20261102/`. The review and its fixes are in docs/review/owner_layout_review_20261101.md.
The routed and reviewed layout is kept in `boards/neurband_c_old/` (not ordered).

The electrode flex is its own Buy it order ([../neurband_c_flex/ORDERING.md](../neurband_c_flex/ORDERING.md)).
Printed parts are ordered from their own `mech/rev_c/*.fab.json`.
