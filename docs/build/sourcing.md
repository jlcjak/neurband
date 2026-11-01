# Sourcing the off-the-shelf parts (rev C)

These are the parts you buy yourself, not the ones the fab fits to the board. Sections 1 and 5 were checked on
2026-11-01 (r2: open hook-and-loop strap, magnetic charging); the other listings were checked
on 2026-10-29 from Greece. Prices are in EUR with VAT for the variant the page showed, and they move
a lot (AliExpress runs 11.11 sales). Delivery dates are the ones the page gave for Greece. "Not
stated" means the listing does not give that number in its text or photos.

Notes on the sources:

- AliExpress photos are often mock-ups. A drawing that disagrees with the cell's own name, for
  example a "401223" drawn 10.4 x 2.4 mm, is not a measurement. **Measure every cell before you
  finish the CAD.**
- Amazon.de ships most of these items to Greece, with free delivery from EUR 59. Lithium cells are
  the exception: the DronePost 401225 page says it cannot be sent to Greece.
- German shops charge 19% VAT. When they sell to Greece they usually charge 24%, so add about 4%.

## 1. Strap: 20 mm one-piece hook-and-loop strap (r2, Nov 2026)

The band is an **open** strap on two thick bars that are part of the module base. A one-piece
"single pass" hook-and-loop watch strap has the right layout. It has a steel ring sewn on one end, a
plain end carrying a 44 mm hook tab, and a loop panel in the middle. Cut the ring end off. That end
then locks round bar A. The hook end goes through bar B and folds back onto the loop panel. Checked
2026-11-01.

| Pick | Listing | Price | Width / length | Thickness | Construction (from the listing photos) |
|---|---|---|---|---|---|
| **First pick** | [Amazon.de B0CWH1XS7B: watchdives one-piece hook-and-loop strap, black, size L](https://www.amazon.de/dp/B0CWH1XS7B) (green L: [B0CWH4WF3K](https://www.amazon.de/dp/B0CWH4WF3K)) | 11.46 (green 10.40) | 20 mm; **302 mm** (seller drawing, size L) | **Not stated** | Steel rectangular ring X-stitched on one end; plain end with a 44 mm hook tab (258-302 mm from the ring end); 75 mm loop panel 127-202 mm from the ring end; comes with 3 spring bars (not used) |
| Fallback | [Amazon.de B06XRYRDRR: Eichmüller textile strap with hook-and-loop, black, 20 mm](https://www.amazon.de/dp/B06XRYRDRR) | 12.50 | 20 mm; about 325 mm (fits 175-240 mm watch wrists) | **Not stated** | Steel D-ring sewn on one end, plain end with the hook strip; longer, so better for wrists over 170 mm |
| Same type, thickness stated | [StrapHabit hook-and-loop single pass](https://straphabit.com/products/hook-and-loop-single-pass-watch-straps) (US) | $29 | 20 mm; 267 mm | **1.5 mm (stated)** | Same layout. Shipping and import VAT make it the dear option |

Thickness: neither EU listing states it. The same strap type is 1.5 mm (StrapHabit, stated) and
comparable 20 mm nylon hook-and-loop straps state 1.5-2.0 mm. The CAD takes a **1.3-2.4 mm** band
and a hook end of up to 3.0 mm:

- slot B is 3.5 mm;
- slot A is 4.4 mm (two layers);
- the pod channels clear 2.5 mm.

**Measure the strap with calipers when it arrives** (build guide, step 7.1).

How long to cut it: see the table in the build guide (step 7.2). On wrists of 145-165 mm, 10-30 mm
comes off the ring end and the whole hook tab lands on the loop panel. On a 180 mm wrist, size L is
just long enough: cut only the ring off, and about 25 of the 44 mm of hook still land on the panel.
Use the longer fallback for wrists over 170 mm.

Why not these:

- **VELCRO ONE-WRAP 20 mm** (back-to-back hook and loop, 1.35 mm, Velcro TDS_206). It only grips when
  it is wound round something like a spiral. A strap that goes through a bar and folds back meets
  itself face to face, hook on hook, so it does not grip.
- **Apple-style nylon sport loops** ([WOCCI B09YTPMRJY](https://www.amazon.de/dp/B09YTPMRJY), 9.36;
  [Runostrich B096VLWDW7](https://www.amazon.de/dp/B096VLWDW7), 12.50). Their 240 mm band is too short
  here. Our band runs about 6 mm off the skin on the pods, so it needs 240-270 mm from the lock to the
  end of the hook zone.

Fraying and heat-sealing: polyester and nylon are thermoplastic. Pass a lighter flame over the cut and
the yarn melts into a sealed edge. Keep the bead small, because it has to pass slot A.

## 3. Double-sided foam dots (24 per band)

| Listing | Price | Pack | Size | Foam / adhesive | Delivery to GR |
|---|---|---|---|---|---|
| [Amazon.de B0GTVY9GP9: Larrel 1160 foam adhesive pads, 4 shapes](https://www.amazon.de/dp/B0GTVY9GP9) | 6.24 | 1160 (2 sheets per shape) | **Round 6 x 2 mm**; square 6 x 6 x 2 and 12 x 12 x 2 mm; strips 3 x 98 mm | EVA foam, adhesive on both faces | 6.82, Nov 21 (only 3 left) |
| [Amazon.de B0GS1XVMZG: 8 sheets 3D adhesive dots, 4 sizes](https://www.amazon.de/dp/B0GS1XVMZG) | 5.18 | 1060 | **Round 8 and 10 mm, 1 mm thick**; square 6 and 12 mm | EVA foam, both faces | 6.65, Nov 21 (only 9 left) |
| [Amazon.de B0H8339Z36: 2000 3D adhesive dots](https://www.amazon.de/dp/B0H8339Z36) | 6.24 | 2000 | Square 5 x 5 x 2 mm (the title says 3 mm, the description 2 mm) | EVA foam, both faces | Free over EUR 59, Nov 21 |
| [AliExpress 32904464994: 3M 1600T double-coated PE foam circles, 1 mm](https://www.aliexpress.com/item/32904464994.html) | 8.07 (30 mm x 20) | e.g. 10 mm x 100 | Diameter 10-80 mm, 1.0 mm thick | PE foam, acrylic on both faces (a real industrial tape) | Not captured |

The ones to avoid are clear "glue dots" (6 mm clear dots, for example the Amazon TIESOME and JZK
packs). They are adhesive with no foam, about 0.1 mm thick.

Craft EVA dots are firmer, and their glue is weaker, than an acrylic PE or PU foam tape. They are
fine for a first build. For a band you plan to keep, punch 6 mm discs from a proper tape:

| Fallback tape roll | Price | Size | Notes |
|---|---|---|---|
| [Amazon.de B0BK6VPYM2: "Super strong double sided foam tape, 2 mm, 10 mm x 10 m"](https://www.amazon.de/dp/B0BK6VPYM2) | 7.45 | 10 mm x 10 m x 2 mm | Foam type not checked |
| [Amazon.de B0GVSFNNSV: double-sided tape "5952 raw material", 10 mm x 3 m, 1.1 mm](https://www.amazon.de/dp/B0GVSFNNSV) | 11.46 | 10 mm x 3 m x 1.1 mm | VHB-type acrylic foam: very strong, but firm (less squash) |

## 4. LiPo cell (protected), envelope at most 4.0 x 12.0 x 25.0 mm

Calibration point: DronePost on Amazon.de sells a "401225" as **27 x 12 x 4 +/- 0.5 mm**
([B0876MYY69](https://www.amazon.de/dp/B0876MYY69), 100 mAh) and a "401215" as **17 x 12 x 4 mm**
([B08769T6N8](https://www.amazon.de/dp/B08769T6N8), 50 mAh). The protection board and taped tabs
add about 2 mm to the length in the name. So a cell has to be named "401223" or shorter to fit
25.0 mm, and a 401225 does not fit.

| Listing | Price | Pack | Stated size | Fits? | Capacity | Leads | Delivery to GR |
|---|---|---|---|---|---|---|---|
| [AliExpress 1005013473853786: "401223 3.7V 130mAh Li Polymer Battery ... with Wire" (2000+ sold)](https://www.aliexpress.com/item/1005013473853786.html) | 11.09 (9.10 each for 2+) | 1 | Drawing says **25 mm long incl. board**, but also gives 10.4 x 2.4 mm, which is impossible for 130 mAh, so the drawing is a mock-up. By the calibration above, expect about **4.0 x 12 x 25 mm** | Borderline: right at 25 | 130 mAh (stated) | 2 wires from the board end, with a small plug; length not stated (about 40 mm from the photo) | 1.24, Nov 15-28 |
| [AliExpress 1005010700825875: EVE PL401223GH 131 mAh, for Xiaomi Band 3-6](https://www.aliexpress.com/item/1005010700825875.html) | 7.95 | 1 | Not stated (about 4.0 x 12 x 23 + board). A known-brand cell | Borderline | 131 typ / 125 min mAh. **High-voltage cell: 3.85 V nominal, 4.4 V full.** A 4.2 V charger is safe and gives about 10-15% less | 2 short bare wires ("need to be welded") from the board end; length not stated (short) | Not captured |
| [AliExpress 32732436814: "301225 031225P 70mAh with protection board"](https://www.aliexpress.com/item/32732436814.html) | 1.77 | 1 | 3 x 12 x 25 mm; whether the board is included is not stated | Yes if 25 includes the board; may be 27 | 70 mAh | 2 wires, end exit; length not stated | Not captured |
| [AliExpress 1005005450826923: "401120 041120P with protection board"](https://www.aliexpress.com/item/1005005450826923.html) (same store) | 1.75 | 1 | 4 x 11 x 20 mm | Yes (about 22 with board) | Not stated. The label photo says 100 mAh, which is not credible; expect 50-60 | 2 wires from the end, taped, with a small connector; length not stated (about 30-40 mm from the photo) | Not captured |
| [AliExpress 1005010044382723: "Mini 401020 3.7V 55mAh" with protection](https://www.aliexpress.com/item/1005010044382723.html) | 14.82 (multi-pack variant shown) | Multi-pack (a review mentions 6 pcs) | **Photo: thickness 4 mm, width 10 mm, length 21 mm** | Yes, with margin | 55 mAh | 2 wires from the short end with a plug; length not stated (looks about 50 mm) | Not captured |
| [AliExpress 1005012943489493: "401020 3.7V 55mAh ... with Protection Board"](https://www.aliexpress.com/item/1005012943489493.html) | 11.67 | 1 | Photo marks 20 x 10 mm | Yes | 55 mAh | 2 wires plus plug | Not captured |
| [AliExpress 1005009111179345: "3.7V 100mAh ... 401225"](https://www.aliexpress.com/item/1005009111179345.html) (reference) | 5.09 for 2 | 2, 5, 10 | Not stated (a 401225 is about 27 mm) | **No** (too long) | 100 stated; a buyer measured 90 | 2 wires | 2.16, Nov 11 - Dec 31 |

None of the cells that reach 80-150 mAh comes with a trustworthy drawing. The 401223 class is the
only one that does, on paper, and it sits right at 25 mm. The 401020/401120 class fits with 3-4 mm to
spare but gives only 50-60 mAh.

The cheap approach is to buy one 401223 (130 mAh) and one 401120 (about EUR 1.75), measure both,
and size the pocket for the one you keep. Leads of 40 mm or more are not guaranteed on any of these:
plan to solder an extension or use short leads. Cut off any plug that comes fitted.

## 5. Magnetic charging connector (r2)

The charge pads J3 (5 V, GND) are on the bottom of the board, in the corner above pod 4. They are wired
to a small 2-pin magnetic connector. Its device half is glued into a pocket in the proximal wall of
the module base, face flush. The cable half is wired to a USB-A lead.

| Item | Listing | Price | Details |
|---|---|---|---|
| **2-pin magnetic pogo pair, 2.5 mm pitch** (Samzo PR5L4015-2P type), male + female | [Amazon.de B0FXL1C7N1](https://www.amazon.de/dp/B0FXL1C7N1) ("14.5 x 4 mm", 1 pair); 2 pairs: [B0HHMGMGJY](https://www.amazon.de/dp/B0HHMGMGJY) | 6.24 (8.32 for 2 pairs) | Datasheet: [Electrokit 41035992](https://www.electrokit.com/upload/quick/66/56/99e1_41035992.pdf). Female (device side): flat face with 2 flush gold pads between N and S magnets; boss 12.5 x 4.0 x 2.0 mm, flange 14.5 x 4.0 x 2.0 mm, 2 pins 0.7 x 1.5 mm. Male: 2 sprung pins (0.9 mm, 1.1 mm stroke) between 2 magnets. 12 V, 2-3 A |
| Same pair, EU shops | [Electrokit](https://www.electrokit.com/en/2-pin-female-magnetic-pogo-pin-connector) female 41035992 + male 41035991; [Berrybase 157030](https://www.berrybase.de/en/berrybase-pogo-pin-plug-and-socket-magnetic-2a-dc-with-cable/plug-port-with-lugs/type-2-pin) | 18.50 SEK each; 2.90 | The Berrybase 157026 version comes with 150 mm leads on both halves (easiest cable) |
| USB-A pigtail for the cable half | [Amazon.de B0DFCFZD9Y](https://www.amazon.de/dp/B0DFCFZD9Y) (12 pcs), or cut an old USB cable | 9.36 | Red (5 V) and black (GND) only |
| 30 AWG silicone or PTFE wire | any, e.g. Kynar wire-wrap wire | about 5 | J3 to the connector (2 x 45 mm), the five one-time SWD wires, and the cell lead extensions if needed |

No ready-made USB cable matches this pair. One half must be wired to USB. A smaller connector
(under 10 mm) was not found on 2026-11-01. This one costs the module about 2.7 mm of length at the
proximal end.

Pogo pins (P50) are **no longer needed**. The SWD jig and the printed charge clip are retired. The
bare board is flashed through four soldered wires on its SWD pads (3V3, SWDIO, SWDCLK, GND) before assembly; to re-flash later, open the
module, fold the board out and re-attach the wires (or leave them as short pigtails). Bluetooth updates (MCUboot +
SMP) are planned, not yet in the firmware.

## 6. SWD probe

| Item | Seller | Price | Stock / delivery |
|---|---|---|---|
| Raspberry Pi Debug Probe | [nettop.gr](https://nettop.gr/index.php/en/raspberry-pi-en/pico/raspberry-pi-pico-kits/raspberry-pi-debug-probe.html) (GR) | **14.50** | 59 in stock |
| Raspberry Pi Debug Probe | [grobotronics.com](https://grobotronics.com/raspberry-pi-debug-probe.html) (GR) | 16.80 | Made to order, 1-3 days |
| Raspberry Pi Debug Probe | [berrybase.de](https://www.berrybase.de/en/raspberry-pi-debug-probe) / [welectron.com](https://www.welectron.com/Raspberry-Pi-Debug-Probe_1) (DE) | 12.20 / 11.90 (19% VAT) | Shipping to GR not shown |
| Pico 2 (RP2350) | [nettop.gr](https://nettop.gr/index.php/en/raspberry-pi-en/pico/raspberry-pi-pico-kits/raspberry-pi-pico-2.html) (GR) | **5.60** | 554 in stock |
| Pico 2 | [grobotronics.com](https://grobotronics.com/raspberry-pi-pico-2.html) (GR) | 5.90 | Ships in 24 h |
| Pico (RP2040) / Pico H | [grobotronics.com](https://grobotronics.com/raspberry-pi-pico.html) (GR) | 4.80 / 7.00 (headers fitted) | In stock |

The Debug Probe comes with its cables. A bare Pico needs debugprobe firmware and five jumper wires.

## 7. BLE receiver for the PC

| Item | Seller | Price | Notes |
|---|---|---|---|
| Nordic nRF52840 Dongle (PCA10059) | [DigiKey](https://www.digikey.ie/en/products/detail/nordic-semiconductor-asa/NRF52840-DONGLE/9491124) | about 12 with VAT (9.78 without) | USB-A on the board; Nordic DFU bootloader, flashed over USB with nRF Connect Programmer or nrfutil (no SWD needed). DigiKey charges 25 shipping under EUR 75. Farnell about 9.91 without VAT. No Greek seller found |
| Seeed XIAO nRF52840 | [digikey.gr](https://www.digikey.gr/en/products/detail/seeed-technology-co-ltd/102010448/16652893) | 11.42 with Greek VAT | USB-C, UF2 bootloader |
| "SuperMini / nice!nano / Pro Micro nRF52840" | [AliExpress search](https://www.aliexpress.com/w/wholesale-nrf52840-supermini.html) | about 6.60-11 per board | USB-C, Adafruit UF2 bootloader (nice!nano build); quality varies by seller |
| Makerdiary nRF52840 MDK USB Dongle | [digikey.gr](https://www.digikey.gr/en/products/detail/seeed-technology-co-ltd/113990714/10290291) | 27.52 | USB-A, UF2 |

## 8. Kapton (and the magnets, no longer needed)

| Item | Listing | Price | Notes |
|---|---|---|---|
| 3 x 1 mm disc magnets, axial | [supermagnete.de S-03-01-N](https://www.supermagnete.de/eng/disc-magnets-neodymium/disc-magnet-3mm-1mm_S-03-01-N) | 4.40 / 20 pcs | **N48**, not N52 (the difference is small). 1-3 days in Germany |
| 3 x 1 mm, N52 | [Green Stuff World, 50 pcs](https://www.greenstuffworld.com/en/neodymium-magnets-n52/505-neodymium-magnets-3x1mm-50-units-n52.html) (ES) | about 5 (not verified) | |
| 3 x 1 mm | [Amazon.de B0DLKG7JF9](https://www.amazon.de/dp/B0DLKG7JF9) | about 6.99 / 100 (from a search snippet) | Grade not stated |
| Kapton tape 10 mm x 33 m | [Amazon.de B094X62PSM](https://www.amazon.de/dp/B094X62PSM) / [B0DXVJWTRQ](https://www.amazon.de/dp/B0DXVJWTRQ) | about 5.99 (from search snippets) | |
| Kapton tape 10 mm | [AliExpress search](https://www.aliexpress.com/w/wholesale-kapton-tape-10mm.html) | about 2.60-4.50 | Check that the variant is 10 mm |

## Numbers for the CAD

| Part | Design to |
|---|---|
| Strap | 20.0 mm wide (+/- 0.5); band 1.3-2.4 mm thick (2.0 nominal in the fit model); hook end up to 3.0 mm. Slot A 4.4 mm (pinch lock, two layers), slot B 3.5 mm, both 20.8 mm long; pod channels 20.8 x 2.5 mm with 0.8 mm snap-in lips |
| Foam dot | 6 mm round, 2.0 mm free height (EVA craft dot), or punched from 1.1-2.0 mm tape |
| LiPo | Pocket 4.2 x 12.4 x 25.5 mm for a cell of at most 4.0 x 12.0 x 25.0, with leads leaving one 12 mm end. Assume leads may be only about 30 mm long and that the cell can be as small as 4 x 10 x 21 mm (401020) |
| Magnetic connector | Device half: boss 12.5 x 4.0 x 2.0 (in a 2.0 mm wall window, 0.15 mm clearance), flange 14.5 x 4.0 x 2.0 behind the wall, pins toward the board, under the cell's overhang |
