# Rev C prototype cost

Goal from the owner: a working prototype for **~$200–250 all-in**, including the electrode flex.
Rev A (16 ch, ESP32, 2× ADS1298, 54 × 34 mm board) was heading for ~$500+.

Where rev C saves money:

| Change | Saves (per order of 2 boards) |
|---|---|
| 8 channels, one ADS1298 instead of two | ~$40 in parts + 1 extended-part fee |
| nRF52832 chip-down ($4.0) instead of an ESP32-S3 module ($4.7); BLE ~10 mA instead of Wi-Fi ~150 mA → 100 mAh LiPo instead of 200–400 mAh | small in parts, big in battery size and module height |
| One basic LDO (XC6206) + RC filter instead of two LDOs | 1 part + 1 extended fee |
| Printed PCB antenna instead of a chip antenna | 1 part + 1 extended fee |
| Basic/preferred parts everywhere possible; only 6 extended parts (ADS1298, nRF52832, LSM6DSL IMU, 32 MHz crystal, FPC connector, 0.8 pF RF cap) | ~$3 per avoided extended part type |
| One-sided assembly | avoids second-side setup + stencil |
| One band size (medium) instead of four flex variants | 3 flex orders |
| Flat ENIG gold pads pushed by printed domes instead of gold pogo pins | ~$20–50 of pins |

## Estimate (order of 2 assembled boards + 5 bare boards, 5 flexes)

These are **estimates**. The exact price comes from Backplane: press **Buy it** (Ready to order bar above the
composer); it checks the design, gets the fab's quote from Backplane's order server and shows it before payment.

| Item | Estimate | Note |
|---|---|---|
| Main board, 4 layers, ~28 × 24 mm, 5 pcs | $8–15 | |
| Assembly, 2 boards, one side: setup + stencil | ~$10 | |
| Extended-part fees (6 types) | ~$18 | |
| Parts for 2 boards (ADS1298 $20, nRF52832 $4, LSM6DSL IMU $2.6, rest ~$2 each) | ~$57 | IMU added on request (Meta's band has one too) |
| Electrode flex, 2 layers, ~140 × 40 mm + tail, 5 pcs, ENIG + PI stiffener | $20–40 | flex is quoted separately from rigid boards |
| Shipping (one combined parcel) | $20–30 | import duties/tariffs depend on your country and are not included |
| **Fab subtotal** | **~$135–170** | |
| Protected LiPo 100 mAh (e.g. 501220 / 401225), ×2 | ~€11 | AliExpress, ~€5–6 each |
| 2-pin magnetic charge connector (smartwatch style) | ~€5 | AliExpress |
| BLE receiver: nRF52840 USB dongle | ~€11 | or a "Pro Micro nRF52840" board ~€5.50 |
| SWD probe: Raspberry Pi Pico running debugprobe | ~€5 | any CMSIS-DAP probe works |
| Elastic strap 22 mm + hook-and-loop | ~€5 | |
| Optional: 2 mm-head gold SMD spring pins (10 for €0.59) | ~€3 | only an experiment: 10× less contact area than the 6.5 mm pad (see docs/science/signal_chain.md) |
| 3D prints (module + 8 pods) | ~€2 own FDM / $10–20 at the fab | |
| **Total** | **≈ $195–240** | |

Prices checked on 2026-10-26 (fab stock via the parts database; AliExpress search pages in the
Backplane browser, EU region, EUR).
