# Rev C prototype cost

Goal from the owner: a working prototype for **~$200–250 all-in**, including the electrode flex.
Rev A (16 ch, ESP32, 2× ADS1298, 54 × 34 mm board) was heading for ~$500+.

Where rev C saves money:

| Change | Saves (per order of 2 boards) |
|---|---|
| 8 channels, one ADS1298 instead of two | ~$40 in parts + 1 extended-part fee |
| nRF52832 chip-down ($4.0) instead of an ESP32-S3 module ($4.7); BLE ~10 mA instead of Wi-Fi ~150 mA → 100 mAh LiPo instead of 200–400 mAh | small in parts, big in battery size and module height |
| One basic LDO (XC6206) + RC filter instead of two LDOs | 1 part + 1 extended fee |
| Printed PCB antenna instead of a chip antenna | 1 part + 1 extended fee (and it performs as well on this board: [antenna_sim.md](../science/antenna_sim.md)) |
| Basic/preferred parts everywhere possible; only 6 extended parts (ADS1298, nRF52832, LSM6DSL IMU, 32 MHz crystal, FPC connector, 0.8 pF RF cap) | ~$3 per avoided extended part type |
| One-sided assembly | avoids second-side setup + stencil |
| One band size (medium) instead of four flex variants | 3 flex orders |
| Flat ENIG gold pads pushed by printed domes instead of gold pogo pins | ~$20–50 of pins |

## Estimate (5 main boards, 2 of them assembled; 5 flexes)

These are **estimates** from the fab's published prices and stock on 2026-10-28
([manufacturing_preorder.md](../review/manufacturing_preorder.md), section 1.2). The exact price of the
main board and the prints comes from Backplane: press **Buy it**; it checks the design and gets the
fab's quote before payment.

| Item | Estimate | Note |
|---|---|---|
| Main board, 4 layers, 28.7 × 27 mm, 1.0 mm, ENIG, black, 5 pcs | $10–20 | |
| Assembly, 2 boards, top side, the fab's standard tier | ~$72 | setup $25.6 + stencil $8.2 + $1.53 × 25 part types (the BOM was consolidated from 27). The economy tier is not possible here: it only does green/HASL on 4 layers and drills tooling holes into boards this small |
| X-ray inspection of the QFN/LGA | ~$3 | |
| Parts for 2 boards (ADS1298 $20, nRF52832 $4, LSM6DSL $2.6, rest ~$0.9 each) | ~$55 | all in the fab's stock |
| Shipping, main board + prints (one parcel) | $20–30 | import duties/tariffs depend on your country and are not included |
| **Main-board order** | **~$165–185** | |
| Electrode flex, 2-layer polyimide, ENIG, PI stiffener, 5 pcs | $25–50 + shipping $15–25 | its own **Buy it** order ([ORDERING.md](../../boards/neurband_c_flex/ORDERING.md)); a flex ships separately from rigid boards |
| 3D prints: module base (with its two strap bars), lid, button cap (MJF PA12) | $15–25 | r2: no strap slides, no charge clip, no SWD jig. The six TPU pods and the two bonding jigs can be printed at home (FDM) |
| Protected LiPo 401223-class, ~130 mAh (≤ 4 × 12 × 25 mm incl. protection board), ×2 | ~€24 | a "401225" is ~27 mm with its board and does not fit ([sourcing.md](../build/sourcing.md)) |
| 20 mm one-piece hook-and-loop watch strap (single pass, size L) | ~€11.50 | r2: open strap on the module's two bars, no sewing ([sourcing.md](../build/sourcing.md) §1) |
| 2-pin magnetic charging connector pair + USB-A pigtail | ~€6 + ~€9 (or an old USB cable) | r2: replaces the printed charge clip ([sourcing.md](../build/sourcing.md) §5) |
| Pre-cut 6 × 2 mm double-sided foam dots (a pack of ~1000) | ~€13 incl. shipping | the only adhesive in the build |
| SWD probe: Raspberry Pi Pico 2 running debugprobe | ~€6 | or the Raspberry Pi Debug Probe, ~€15 |
| BLE receiver: nRF52840 USB dongle | ~€12 + shipping | or an nRF52840 "SuperMini" board, ~€7 |
| **Total** | **≈ $300–360** | |

The first estimate (≈ $195–240) assumed the cheap assembly tier and the flex in the same parcel; the
pre-order manufacturing review showed neither is possible. The r2 mechanics (Nov 2026) swap the elastic
webbing, two printed strap slides, the printed charge clip, the SWD jig and the pogo pins for a bought
hook-and-loop strap and a magnetic connector pair: about €15 more off the shelf, three fewer printed
parts, and no small printed part carries the band's load any more; the cell that really fits
(401223-class) costs more than the 401225 first assumed. The second
assembled board and three spare bare boards are included in that price.
