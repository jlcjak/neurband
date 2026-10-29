# REV C Step 0 schematic review

> **Historical Step 0 review — superseded for current REV C circuit values and firmware.** The original review below is retained as history, not current assembly instructions. In particular its 2.2 nF C12, open RLDREF / internal-reference CONFIG3=0xCC, and recommendation against an external divider no longer describe the circuit. Use the current as-built addendum immediately below and [REV C layout record](../layout/main_c_layout.md). The final saved-board native check after J3 relocation and source-footprint propagation reports 0 DRC errors, 0 unconnected and 0 schematic-parity issues.

## Current REV C as-built addendum — 2026-10-26

- Current `boards/neurband_c/gen_c_sch.py` sets **R1=1 Mohm, C12=4.7 nF** in parallel: feedback pole approximately **33.86 Hz**, not the historical 72 Hz. This is a nominal circuit pole, not a measured body-loop stability margin.
- Added **U5 LSM6DSL**, **C31=100 nF** supply bypass and **R9/R10=4.7 kohm** I2C pull-ups. I2C_SDA is nRF **P0.03/AIN1, pin 5**; I2C_SCL is **P0.04/AIN2, pin 6**. IMU_INT is **P0.24, pin 29**, from U5 INT1. The generator/current netlist, not an earlier GPIO map, define firmware wiring.
- Added **R11=100 kohm** ADC_PWDN pull-down so the shared ADS1298 RESET/PWDN net remains low until the MCU drives it.
- Added **R12/R13=1 Mohm** divider from +3V3A to GND and **C32=1 uF** filtering on external **RLDREF (ADS1298 pin 60)**. This provides nominal AVDD/2; it is no longer an open pin. The divider's nominal Thevenin resistance is 500 kohm and its unloaded RC pole is approximately 0.318 Hz.
- **Firmware must set CONFIG3.RLDREF_INT=0 (bit 3)** to use this external reference. TI SBAS459K Table 20 (`docs/datasheets/ads1298.txt`, CONFIG3 section) was read: bit 7 enables the internal ADC reference buffer, bit 6 must be 1, bit 5 selects 2.4/4 V, bit 4 enables RLD measurement, bit 3 selects external/internal RLDREF, bit 2 enables the RLD buffer, bit 1 enables RLD lead-off sensing, and bit 0 is read-only status. For the same normal-acquisition assumptions as the historical review—2.4 V ADC reference enabled, RLD enabled, RLD measurement and lead-off sensing disabled—the write value is therefore **0xC4**, not 0xCC. Other operating modes require their own field choices; an external RLD reference does not mean disabling the ADC's internal VREF buffer.
- The layout uses **67 footprint positions** in `.archive/neurband_c_layout_scripts/place_c.py`. All assembled parts are TOP; bottom interfaces are only wire/test pads. Eight reviewed footprint choices (J1, J2, J3 and TP1–TP5) were initially board-only; the main-schematic owner subsequently propagated their IDs into the deterministic source. This layout task did not edit the schematic or generator.
- Final `layout/build/final-drc.json` reports **0 errors, 0 unconnected and 0 schematic-parity issues**. J3's final bottom coordinates are VCHG (14,6), GND (14,9); all 66 other placements stayed fixed. No hole-spacing or dangling-copper warnings remain. The **59 library-definition mismatch warnings** reflect intentional sparse silkscreen/model changes; this is not a warning-free-board claim. Component and board-only STEP exports, top/bottom/3D renders and measured fabrication metadata were regenerated; see the layout record for evidence and limits.

The circuit review did not reassess manufacturer parts, supplier stock, fabrication quotes, ERC, hardware or RF measurements. Native layout DRC results are reported separately above. The repaired `layout/build/component-heights.json` contains finite FreeCAD physical-solid measurements for J1/U1 and the other listed models; the previous 1e100 datum-plane artefacts are invalid and superseded. These are visual-model measurements, not vendor tolerance certificates or measurements of populated hardware; see the layout record.

## Historical Step 0 record

Reviewed 2026-10-26: `boards/neurband_c/gen_c_sch.py`, `boards/neurband_c/neurband_c.net`, and `docs/research/nrf52832_refcircuit.md`. Scope: blocking circuit errors and practical cost simplifications, not layout sign-off. Parent reports netcheck already passed; it was not rerun. No schematic, generator, or flex changes were made.

## 1. Real errors / layout decision

**No blocking electrical error found in the reviewed ADS1298, nRF52832, TP4054, or XC6206 connections. Layout can proceed.** This does not sign off the electrode connector's manufacturer land pattern/contact orientation, which is being checked separately, or RF performance on the final populated board.

### ADS1298 pin strapping and supplies

- The actual exported nets include all AVDD pins 19/21/22/56/59 and AVDD1 pin 54 on `+3V3A`; DVDD 48/50 on `+3V3`; all AVSS/AVSS1/DGND pins on GND. Hidden stacked symbol pins have not been lost.
- A filtered nominal 3.3 V analog supply is within TI's 2.7–5.25 V range; 3.3 V DVDD is within 1.65–3.6 V. The 10-ohm filter loses about 28 mV at TI's typical 2.75 mA HR-mode analog current. It is not an undervoltage problem with a regulated 3.3 V rail. Battery depletion/dropout still limits operating time: stop acquisition before the actual analog rail falls below 2.7 V; do not assume regulation down to the battery protection cutoff.
- RESV1 pin 31 and DAISY_IN pin 41 are tied low as required. Unused GPIOs are tied low; firmware must leave them as inputs rather than drive them high. Unused TESTP/TESTN pins 17/18 are tied to AVDD, matching TI's pin-table footnote. Keep pace outputs disabled. NC 27/29 and unused WCT are open. CLKSEL is high for the internal oscillator, with CLK unused.
- VREFN is grounded; VREFP has 10 uF plus 100 nF; VCAP1 has 22 uF and VCAP2/3/4 each have 1 uF, matching the pin-table requirements. VCAP3 is a boosted internal node, approximately AVDD + 1.9 V: retain an adequate capacitor voltage rating there, not a 4 V substitution.
- Layout must split the AVDD1/AVSS1 charge-pump branch locally from the quiet AVDD/AVSS branch as TI specifies; this is placement/routing on the existing nets, not a request for another regulator. Preserve local supply bypasses.

### RLD / body bias

- Netlist confirms R1 (1 Mohm) and C12 (2.2 nF) are in parallel between RLDOUT pin 63 and RLDINV pin 61. R2 (100 kohm) is in series from the amplifier output to BIAS_E, J1 pins 2/19, and RLDIN pin 62. There is no accidental short of the feedback or omission of the series resistor.
- RLDREF pin 60 being open is valid when firmware selects the internal midpoint reference. It is not a reason to add a divider. For acquisition, enable the internal reference buffer, select 2.4 V (not 4 V), select internal RLDREF, enable RLD, and select appropriate P/N channels in RLD_SENSP/N. For normal acquisition with RLD measurement disabled, CONFIG3 = 0xCC expresses those choices including the mandatory reserved bit. Reset defaults do not enable the needed reference/RLD functions.
- The 1 Mohm / 2.2 nF feedback pole is approximately 72 Hz versus approximately 106 Hz for TI's 1.5 nF example. That value difference is not a demonstrated blocker. Body/electrode-loop behavior requires bench evaluation, not a claim of guaranteed stability from this review.
- RESET and PWDN share one MCU GPIO. This sacrifices independent hardware reset, not normal operation: use the SPI RESET command for a reset without power-down and observe TI power-up/reference settling times after leaving power-down.

### nRF52832 RF, clock, decoupling

- ANT has the Nordic QFN reference topology: 0.8 pF shunt on the chip side, then 3.9 nH series to the antenna-side feed. No reversed shunt position was found. The additional 0-ohm link and two DNP shunt sites are antenna tuning provisions, not additional populated matching capacitors.
- DEC1 100 nF, DEC3 100 pF, DEC4 1 uF, DEC2 open, and DCC open match Nordic's LDO-only QFN configuration. Keep the internal DC/DC disabled in firmware. Exported nets include all VDD 13/36/48 and VSS 31/45/49, including the exposed pad.
- The 32 MHz crystal is between XC1/XC2, with one 12 pF load capacitor per side; both crystal ground pads are grounded in the netlist. These values match Nordic's 8 pF-load reference. An omitted 32.768 kHz crystal is supported; configure/calibrate LFRC appropriately. Exact selected crystal total frequency tolerance/ESR was not independently established from a manufacturer specification in this time-boxed review; no observed incompatibility is asserted.
- Essential layout detail: ground the 0.8 pF RF capacitor through VSS pin 31 as in Nordic's reference, not through an arbitrary nearby plane via. Keep the reference matching geometry compact, respect its inner-layer keepout, and put the 4.7 uF / 100 nF / 100 nF VDD capacitors near pins 48 / 13 / 36 respectively. Keep the IFA's full copper/metal clearance, including the battery. These are layout constraints, not new schematic blockers.

### Exact charger / LDO pinouts

| Device fitted | Manufacturer pin functions | Actual exported connections | Result |
| --- | --- | --- | --- |
| TOP POWER ASIC TP4054-42-SOT25R, C32574 | 1 CHRG, 2 GND, 3 BAT, 4 VCC, 5 PROG | 1 CHG_N, 2 GND, 3 VBAT, 4 VCHG, 5 10 kohm to GND | Correct. The MCP73831 symbol pin numbering is compatible here. |
| TOREX XC6206P332MR-G, C5446, **SOT-23** | 1 VSS, 2 VOUT, 3 VIN | 1 GND, 2 +3V3, 3 VBAT | Correct. Do not substitute the SOT-89 pin order. |

TP4054's 10 kohm program resistor gives nominal 100 mA for this part, not an assumed generic charger formula. Its charge-status output is open-drain, so firmware needs a pull-up; the nRF internal pull-up can serve. A roughly 100 mAh cell must actually permit the selected charge current; capacity alone is not a charge-current rating. With no power-path circuit, keep the system in low consumption while charging so its load does not defeat the nominal 10 mA termination threshold. CHG_N alone is not an infallible charger-present or isolation signal. Preserve the explicit no-wearing-while-charging/debugging restriction. This review does not certify patient safety.

## 2. Cost and size simplifications

1. **Keep the present architecture.** One ADS1298, chip-down nRF52832, one LDO, printed antenna, resistor arrays, battery solder pads, and SWD test pads already avoid the large cost/area additions. There is no circuit-driven reason here to add a second regulator, RF module, DC/DC inductors, LF crystal, external RLD divider, or SWD connector.
2. **The LED plus its 1 kohm resistor are the cleanest optional deletion** if layout becomes tight; they cost two placements and are not needed to record data. Keep the button if wake/mark is a requirement. Do not quietly delete user-visible features just to shave cents.
3. **Keep the two DNP RF shunts and the 0-ohm link for this prototype.** DNP pads incur no component placements and allow tuning after the battery/housing are present. Saving one populated resistor by removing the link is not worth losing convenient series tuning/rework access in this first printed-antenna build.
4. **Do not cut the ADS VCAP/reference capacitors or per-pin nRF bypasses.** They are functional parts, not bulk-cap duplication to remove blindly. The battery divider's two resistors and capacitor likewise implement real battery measurement; deleting them trades away that feature, not a free simplification.
5. **Treat the $200–250 whole-prototype target as a purchasing target, not an established quote.** Assembly setup/extended-part handling, the ADS1298, and a separate flex order can dominate passive savings. This review did not obtain a current fabrication/assembly quote or confirm stock.

## Sources and evidence limits

- TI ADS129x datasheet SBAS459K (August 2015), local `docs/datasheets/ads1298.pdf` and extracted `ads1298.txt`: TQFP pin table pp. 10–11; supply/current specifications; CONFIG3 table; RLD sections; power-up and supply recommendations pp. 96–98. [TI product datasheet](https://www.ti.com/lit/ds/symlink/ads1298.pdf).
- Nordic nRF52832 Product Specification v1.0, local `docs/datasheets/nrf52832_ps_v1.0.pdf`, with current online reference BOM cross-check already documented in `docs/research/nrf52832_refcircuit.md`: QFN LDO reference schematic/BOM and layout guidelines, pp. 539–543. [Nordic reference circuitry](https://docs.nordicsemi.com/bundle/ps_nrf52832/page/ref_circuitry.html). This review relied on that source-backed research rather than claiming a newly retrieved modern PDF.
- [TP4054 original manufacturer datasheet mirrored by Olimex](https://www.olimex.com/Products/Power-Supply/Modules/USB-uLiPo/resources/tp4054.pdf), pin functions p. 5, charging-current programming p. 6, status/termination descriptions. [Exact C32574 listing](https://www.lcsc.com/product-detail/C32574.html) identifies TOP POWER ASIC and TP4054-42-SOT25R.
- [TOREX XC6206 manufacturer datasheet](https://product.torexsemi.com/system/files/series/xc6206.pdf), pin-assignment table: SOT-23 1 VSS / 3 VIN / 2 VOUT. The PDF fetch returned HTTP 403, but the search-indexed manufacturer table supplied these pin rows; [DigiKey mirror reference](https://www.digikey.com/htmldatasheets/production/1823955/0/0/1/xc6206-series.html) returned 410. Exact part identity/package also agrees with [C5446 listing](https://www.lcsc.com/product-detail/C5446.html). This is a documented retrieval limitation, not a fabricated full-PDF inspection.

No build, ERC/netcheck rerun, simulation, hardware test, or RF measurement was performed as part of this review.
