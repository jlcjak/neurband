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
| Electrode flex, 2-layer polyimide, ENIG, PI stiffener, 5 pcs | $25–50 + shipping $15–25 | ordered separately from a flex service ([ORDERING.md](../../boards/neurband_c_flex/ORDERING.md)) |
| 3D prints: module base, lid, button cap, 2 strap loops (MJF PA12) + charger puck | $15–25 | the six TPU pods on your own FDM printer cost cents |
| Protected LiPo 100 mAh 401225 (≤ 4 × 12 × 25 mm incl. protection board), ×2 | ~€11 | AliExpress, ~€5–6 each |
| 2-pin magnetic charge parts (4 N52 3 × 1 mm magnets, 2 pogo pins, USB lead) | ~€5 | |
| BLE receiver: nRF52840 USB dongle | ~€11 | or a "Pro Micro nRF52840" board ~€5.50 |
| SWD probe: Raspberry Pi Pico running debugprobe | ~€5 | any CMSIS-DAP probe works |
| 22 mm elastic hook-and-loop webbing, double-sided 1.5 mm foam tape, 1.5 mm PMMA fibre | ~€8 | |
| **Total** | **≈ $280–330** | |

The first estimate (≈ $195–240) assumed the cheap assembly tier and the flex in the same parcel; the
pre-order manufacturing review showed neither is possible. Everything else is as before. The second
assembled board and three spare bare boards are included in that price.
