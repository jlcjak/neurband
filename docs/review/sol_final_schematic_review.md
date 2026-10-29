# neurband rev C — final read-only schematic review

Reviewed 2026-10-29. Scope: the saved `boards/neurband_c/neurband_c.kicad_sch`, readable generator `boards/neurband_c/gen_c_sch.py`, `boards/neurband_c/neurband_c_bom.csv`, `firmware_c/`, `docs/firmware_c.md`, `docs/layout/flex_c_layout.md`, and the three requested previous reviews. Only this report was edited. No checkout, commit, regeneration, board modification, or manufacturing release was performed.

**No confirmed BOARD-KILLER or FEATURE-KILLER was found.** The circuit has a credible path to useful eight-channel sEMG, BLE and IMU data. That is a schematic conclusion, not a claim that dry contacts, on-wrist RF performance, populated-board noise or uninterrupted streaming have been measured. The confirmed shortcomings are charger-presence detection and lack of reverse-polarity protection; these do not require throwing away correctly assembled, correctly connected boards.

The question's START/PWDN/RESET premise needs correction: **START is separate** (`ADC_START`, P0.13). Only **PWDN and RESET share `ADC_PWDN`, P0.14**, with R11 = 100 kohm to GND.

## Evidence and sources

The selected KiCad CLI reported 10.99.0. A fresh XML netlist, schematic SVG/PNG, and ERC report were generated outside the repository. The schematic render and Nordic's QFN LDO reference drawing were visually inspected; the pin tables below come from the saved schematic's exported connectivity, including hidden stacked supply pins. ERC returned **0 errors and 8 warnings**: U5.1/2 and U2.17/18/42/44/45/46 versus power flags. These are mode-dependent bidirectional pins deliberately strapped to supply/ground, supported by the device documentation; they are not eight independently discovered circuit faults. No claim of zero ERC warnings is made.

Datasheets were fetched from the web. Manufacturer PDFs hosted by mirrors remain manufacturer-authored sources. Direct Nordic v1.9 PDF retrieval was blocked; its current online product-specification sections were read instead and the QFN reference drawing was checked in the downloadable v1.0 PDF. Direct downloads of the ST/Torex PDFs were also blocked, but their PDF content and relevant page images were available through web retrieval. No finding relies on an unread PDF being silently treated as available.

| Tag | Primary technical evidence |
|---|---|
| TI | [ADS129x SBAS459K](https://www.ti.com/lit/ds/symlink/ads1298.pdf): §6 TQFP pin table pp.10–11; §7.3/7.5–7.7 supplies, electrical limits and SPI timing; §9.3.1.5 input range; §9.3.1.6 reference; §9.3.1.7.6 RLD; §9.3.2.1–3 GPIO/power-down/reset; §9.5/9.6 serial commands/registers; §11/Fig.105–106 startup and bypassing. |
| N-pin | [Nordic current QFN48 pin assignments](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/pin.html). |
| N-ref | [Nordic current reference circuitry](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/ref_circuitry.html); manufacturer [PS v1.0 PDF mirror](https://cdn.sparkfun.com/datasheets/Wireless/Bluetooth/nRF52832_PS_v1.0.pdf), §53.1 Fig.167/Table139 p.539. |
| N-clock | [Nordic CLOCK](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/clock.html): HFXO electrical limits and LFRC calibration. |
| N-power | [Nordic POWER](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/power.html): LDO default, System OFF/wakeup, sleep current. |
| N-adc | [Nordic SAADC](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/saadc.html): acquisition-time/source-resistance table. |
| ST | [LSM6DSL DocID028475 Rev7](https://www.st.com/resource/en/datasheet/lsm6dsl.pdf): Table2 pins; Table4 currents/levels; Table7 I2C; §6.1 address; §7 application circuit/Table18; §9 control registers. |
| TX | [Torex XC6206 ETR03005-009](https://product.torexsemi.com/system/files/series/xc6206.pdf): p.1 application; p.3 SOT-23 pinout/absolute limits; pp.4–5 electrical characteristics; p.6 Notes on Use. |
| TP | [Original TP4054-42-SOT25-R datasheet mirror](https://www.olimex.com/Products/Power-Supply/Modules/USB-uLiPo/resources/tp4054.pdf): PDF p.1 absolute limits, p.2 electrical table, p.5 pin functions, pp.6–7 charging/status, p.11 three-state status detection and reverse-input protection. Printed page numbers in this copy are offset by one. |
| YX | [Yangxing X201632MKB4SI specification B.0](https://www.quartz1.com/price/techdata/YSX211SL%5B32MHz%5D.pdf), p.3: crystal load, ESR, C0, tolerance and aging. The exact stocked part's linked PDF could not be retrieved; the same-MPN B.0 document was read. |

## Findings and simplest remedies

Severity describes the existing limitation and its repairability. Conditional damage from reversed wiring is distinguished from a board that fails in normal use. OK/NOTE rows are checks or qualifications, not extra faults.

| ID | Severity | Confirmed finding / evidence | Simplest fix or disposition |
|---|---|---|---|
| F1 | **BODGEABLE** | **The automatic interlock does not detect every attached-charger state.** U4.1 CHRG goes from strong low during charging to a weak approximately 20 uA sink after termination (TP pin functions/Charge Status Indicator). `main.c` reads only a digital level with the nRF internal pull-up. At approximately 13 kohm, 20 uA drops only 0.26 V: the input reads high and firmware interprets this as charger removed. `chg_work_fn()` can power the AFE again if connected over BLE. A full battery may also fail to produce a low level on charger insertion, defeating the advertised charger wake. | For reliable charger presence, add a suitably divided VCHG signal to an unused GPIO and update firmware. Alternatively implement TP's documented two-strength status-reading circuit. A firmware latch can keep the AFE off after an observed charging event, but cannot reliably distinguish a full-battery insertion or determine removal from this single fixed-pull-up digital reading. Existing off-body charging remains an operating restriction. |
| F2 | **BODGEABLE** | **Reversing the two-contact charge clip is electrically destructive-risk, not supported operation.** J3.1 connects directly to U4.4 VCC, J3.2 to GND. Reversal applies approximately −5 V to VCC; TP specifies a −0.3 V lower absolute limit and explicitly shows optional reverse-input protection. Protected battery circuitry does not protect this input. | Use a polarity-keyed clip, or add the series diode/P-channel protection described by TP in the charging lead. A diode must leave sufficient voltage at VCC during 4.2 V charging; a low-drop solution preserves more margin. No respin is essential for a lead-mounted fix. |
| F3 | **BODGEABLE** | **Battery solder pads have no reverse-polarity protection.** J2.1 VBAT directly feeds U3.3 VIN and U4.3 BAT. A reversed cell exceeds TX VIN and TP BAT negative limits (−0.3 V). “Protected cell” normally describes cell protection, not a guarantee that the board tolerates reversed pack leads. | Verify polarity before soldering; use a keyed protected pack/lead assembly or add battery-side reverse protection. A protected cell must still be fitted as specified. No evidence establishes that a correctly connected cell will fail. |
| F4 | **DEGRADED** | **System OFF still drains the cell.** U2 remains supplied in hardware power-down; U5 remains supplied; R6/R7 and R12/R13 continuously conduct. TX has no enable pin. Calculation below gives approximately **11 uA before the cell protector/self-discharge**, rather than the MCU's 0.3 uA alone. | Normal for this architecture. Recharge during storage; disconnect the pack for prolonged storage or add a lead switch if required. Do not promise multiyear storage. |
| F5 | **OK/NOTE** | **Regulated 3.3 V does not extend to the cell protector cutoff.** TX p.5 gives 75 mV typical/350 mV max dropout at 30 mA for the relevant voltage group; dropout is load-dependent. Near depletion the rails follow VBAT downward. TI requires AVDD ≥2.7 V. `main.c` stops at VBAT <3.3 V for three samples, substantially earlier than an unspecified protector cutoff. | Retain the early firmware stop. Verify rail minimum and stability under radio peaks near the threshold; TX Notes on Use specifically requires evaluation near dropout. This is not a demonstrated undervoltage failure at ordinary battery voltages. |
| F6 | **OK/NOTE** | **100 mA charging is approximately 0.77 C for 130 mAh, not automatically a safe cell rating.** R4=10 kohm gives TP's nominal 100 mA, electrical-table range 90–110 mA before resistor tolerance. No cell MPN, charge-current rating, protector threshold or protector quiescent current is specified in the reviewed BOM. | Match the actual protected 4.2 V cell specification. If it permits only 0.5 C (65 mA), replace R4 with approximately 15.4 kohm or a larger standard value. This is a missing cell qualification, not proof that 100 mA is excessive for the eventual cell. |
| F7 | **OK/NOTE** | **10 kohm I2C pull-ups at 400 kHz require a small bus capacitance.** R9/R10 are 10 kohm in the current schematic/BOM. For a 300 ns fast-mode rise-time budget, `tr ≈0.8473 R C` gives Cbus ≤35 pF nominal. ST Table7 permits 400 kHz; no extracted or measured bus capacitance was established here. | Measure edges; if necessary use 4.7 kohm pull-ups or reduce the overlay to 100 kHz. Do not declare the IMU dead solely because the pull-ups are 10 kohm. |
| F8 | **OK/NOTE** | **Crystal tolerance needs exact supplied-grade confirmation.** Y1 has correct frequency/load/topology. The same-MPN YX B.0 specification gives ±10 ppm initial, ±30 ppm temperature and ±3 ppm/year aging, leaving no guaranteed load/aging margin against N-clock's ±40 ppm BLE total requirement. The fab's stock attributes instead state ±20 ppm temperature and 80 ohm ESR. This discrepancy is not a demonstrated oscillation failure. | Obtain the supplied grade's specification or qualify frequency over the intended temperature range; use a tighter same-size 8 pF crystal if a full-range lifetime guarantee is required. No evidence justifies calling present BLE nonfunctional. |
| F9 | **OK/NOTE** | **Schematic correctness cannot certify signal quality or worn antenna performance.** The electrical ANT matching topology matches N-ref. RLD stability depends on the body/electrode loop (TI §9.3.1.7.6). Prior analog/RF simulations and layout concerns are not physical measurements. | First-board internal-test/shorted-input acquisition, all-channel offset/headroom checks, radio-on noise and worn link tests remain necessary. This review does not reclassify an unmeasured concern as a feature failure. |

## ADS1298 functional checks

All 64 pins are accounted for in the ledger below. The KiCad symbol calls pin 18 `TESTP_PACE_OUT2`; TI calls it **TESTN_PACE_OUT2**. This is a symbol-name typo, not a pin-number or connectivity error.

- **Rails and bypass:** AVDD pins 19/21/22/56/59 and AVDD1.54 are on +3V3A; AVSS 20/23/32/57/58 and AVSS1.53 on GND. DVDD 48/50 is +3V3 and DGND 33/49/51 is GND. R5=10 ohm drops approximately 28 mV at 2.75 mA analog current, giving about 3.27 V while the main rail regulates. Analog and digital rails are within TI §7.3. C7/C8/C9 and C33, C28/C29 provide analog bypass; C10/C11 provide digital bypass. Nominal values cover the §11 1 uF/100 nF recommendations. AVDD1 star routing and local capacitor placement are PCB matters, not proven by a net name.
- **VCAP and reference:** C5=22 uF on VCAP1.28; C4/C3/C2=1 uF on VCAP2.30/VCAP3.55/VCAP4.26, all to AVSS. VREFP.24 has C6=10 uF plus C1=100 nF to GND; VREFN.25 is grounded. These agree with TI pin table/Fig.106. BOM C3 is a 25 V 1 uF part, appropriate for VCAP3's AVDD+1.9 V boosted node. No 3.3 V-rated part was found there. Actual bias derating/microphonics are not quantified here. TI §11 specifically warns about class-II VCAP1 ceramics in a vibrating system; X5R use is not forbidden or proof of unusable data.
- **Fixed/unused pins:** 17/18 to AVDD follows the pin-table unused-input footnote. Keep pace outputs disabled (firmware leaves PACE reset default). GPIO1–4 on GND are legal with GPIO control inputs; reset GPIO register 0x0F selects inputs and firmware does not change it. DAISY_IN.41 and RESV1.31 are grounded as required. **27/29 are explicitly NC**, with an optional 10 kohm tie allowed by TI; no tie is required. WCT.64 open is consistent with all WCT amplifiers disabled. CLKSEL.52 high selects the internal oscillator; CLK.37 open is correct with CONFIG1.CLK_EN=0.
- **Shared PWDN/RESET startup:** R11 holds both low during MCU reset. `ads_power_up()` keeps START low, releases PWDN/RESET high, waits 300 ms, sends SDATAC, sends SPI RESET, waits 20 us and sends SDATAC again. TI §11.1/Table38 requires a reset after at least 2^18 clock periods (128 ms nominal) and VCAP1 ≥1.1 V; 20 us exceeds the reset-command 18-clock initialization. The later SPI RESET supplies the independent reset event the shared GPIO cannot supply. Then CONFIG3=0xC4 enables the 2.4 V reference/RLD and another 300 ms is allowed for reference settling. **The tie is not inherently illegal and does not require a bodge.** A fixed 300 ms delay is not measurement of VCAP1; verify the threshold once during bring-up, especially with C5 tolerance/temperature. A hardware-reset pulse on this shared net necessarily power-cycles the AFE, so use SPI RESET for register-only reset.
- **RLD:** R1=1 Mohm parallel C12=4.7 nF connects RLDOUT.63 to RLDINV.61; R2=100 kohm lies between output and BIAS_E. RLDIN.62 now connects to RLDOUT on the amplifier side of R2, not directly to the exposed electrode bus. It is a mux input, not a missing feedback terminal. R12/R13=1 Mohm and C32=1 uF provide external midpoint reference at RLDREF.60; TI §9.3.1.7.6 expressly permits an external divider. CONFIG3=0xC4 correctly selects it and enables the RLD amplifier. The nominal divider pole is 0.318 Hz; feedback impedance pole 33.9 Hz. Firmware senses P/N of channels 1–4 (0x0F), while **all eight acquisition channels remain enabled**. Neither a mandatory divider buffer nor an extra resistor on RLDIN is established by TI. Loop stability is a bench qualification, not guaranteed by the feedback pole alone.
- **Range:** TI §9.3.1.5 equations give ±2.4/6=**±400 mV differential**, including electrode DC offset. At AVDD=3.27 V, the legal common-mode interval is approximately `0.2 + 3|Vdiff| < Vcm < 3.07 − 3|Vdiff|`. It is 1.10–2.17 V at 300 mV differential, 1.40–1.87 V at 400 mV. Midpoint approximately 1.635 V fits. RLD controls a selected average; it does **not guarantee every pair's common-mode voltage** or remove pairwise DC offsets. Large offsets can clip before any digital high-pass filter. Existing `gain 4` or lower is the simplest response where offsets demand it; measure all channels rather than assume gold offsets.
- **Digital interface:** `ads1298.c` uses CPOL=0/CPHA=1 (mode 1), MSB first, 1 MHz register traffic and 8 MHz frame reads. These match TI §9.5/§7.6; 27 bytes takes 27 us at 8 MHz versus a 250 us frame at 4 kSPS. A 3 us CS delay exceeds four internal-clock periods; the 1 MHz byte time exceeds command-decode time. All logic uses the same +3V3 digital rail: ADS VIH≥0.8 DVDD and nRF standard-drive output levels are compatible, as are ADS outputs and nRF inputs. No level shifter is required.

## nRF52832, IMU and firmware match

N-ref's LDO circuit uses DEC1 100 nF, DEC3 100 pF, DEC4 1 uF, DEC2 unpopulated, DCC unconnected: **the present schematic matches**. VDD bulk is increased to 10 uF with two 100 nF capacitors; all VDD pins and exposed VSS pad are in the netlist. Firmware overlay requests LDO mode where supported; `firmware_c/zephyr37.conf` disables the old board DC/DC option. There is no DCC inductor, so a different firmware build must not enable DC/DC.

Y1 connects XC1/XC2 with C19/C20=12 pF to GND and case pads 2/4 grounded. Equal 12 pF loads match Nordic's 8 pF reference implementation (approximately 6 pF series load plus pin/PCB parasitics). Actual load depends on layout. No 32 kHz crystal is required: `prj.conf` selects LFRC and 500 ppm sleep-clock accuracy. SWDIO/SWDCLK, GND and target voltage are accessible at TP2/TP3/TP5/TP1; TP4 reaches P0.21 reset. Reset function requires matching UICR PSELRESET entries; this is a programming configuration, not a missing mandatory external reset pull-up. No flashed image/UICR was inspected. SWD remains the programming path.

| Signal | Schematic U1 physical pin / GPIO | Exact `firmware_c/boards/nrf52dk_nrf52832.overlay` assignment | Result |
|---|---|---|---|
| ADC_CS | 8 / P0.06 | spi2 cs gpio0 6 active low | OK |
| SPI_SCK | 9 / P0.07 | SPIM_SCK 0,7 | OK |
| SPI_MOSI | 10 / P0.08 | SPIM_MOSI 0,8 | OK |
| SPI_MISO | 14 / P0.11 | SPIM_MISO 0,11 | OK |
| ADC_DRDY | 15 / P0.12 | drdy gpio0 12 active low | OK |
| ADC_START | 16 / P0.13 | start gpio0 13 active high | OK |
| ADC_PWDN (+ RESET) | 17 / P0.14 | pwdn gpio0 14 active low | OK |
| LED | 18 / P0.15 | led gpio0 15 active low | OK |
| BUTTON | 19 / P0.16 | button gpio0 16, pull-up, active low | OK |
| CHG_N | 20 / P0.17 | chg gpio0 17, pull-up, active low | OK mapping; F1 limitation |
| VBAT_SENSE | 4 / P0.02 / AIN0 | SAADC channel 0, NRF_SAADC_AIN0 | OK |
| I2C_SDA | 5 / P0.03 | TWIM_SDA 0,3 (TWI0 selected) | OK |
| I2C_SCL | 6 / P0.04 | TWIM_SCL 0,4 | OK |
| IMU_INT | 29 / P0.24 | irq gpio0 24 active high | OK |

P0.09/P0.10 are **both unused**, so no feature depends on releasing NFC pins. P0.24 only receives the IMU's low-frequency interrupt; fast SPI is outside the near-radio GPIO bank. The ANT circuit has the correct chip-side 0.8 pF shunt and 3.9 nH series element, then R3=0 ohm and two DNP shunts for antenna tuning. Correct topology does not establish worn antenna efficiency.

U5 is in ST Mode 1: CS.12 high, SA0.1 low, SDx.2/SCx.3 grounded, NC.10/11 open. These are the documented connections, not missing auxiliary pull-ups. The seven-bit address is **0x6A**, matching the overlay and WHO_AM_I expected by `imu.c`. VDDIO.5/VDD.8 are +3V3, GND.6/7 grounded, with C31=100 nF on the shared rail. INT1.4 reaches P0.24; INT2.9 is unused. `imu.c` enables active-high DRDY on INT1 and power-downs both sensors on stop; the accelerometer/gyro settings decode to 208 Hz, ±4 g / ±500 dps. No pin-level IMU feature failure was found.

## Power, battery sense, UI and charging details

U3 uses the correct **SOT-23** pinout, not the different SOT-89 order: 1 GND, 2 output +3V3, 3 input VBAT. C26/C27 are 1 uF input/output capacitors, consistent with TX's application circuit, with additional rail bulk elsewhere. TX warns to account for effective capacitance, short routing and dropout stability. No claim of local placement adequacy is made by this schematic-only review.

The reasonable load scale is approximately 3.3–3.5 mA AFE plus IMU, CPU and radio: the firmware document estimates approximately 8 mA average default streaming and 12 mA raw streaming. These are estimates, not measurements. The regulator's 200 mA-class current capability is ample; radio/CPU peaks of order 20–30 mA matter more for dropout than average current. At 4.2 V/20 mA, LDO dissipation is only about 18 mW. At 3.3 V battery voltage, the output is necessarily below nominal; do not substitute the 100 mA dropout specification as the expected dropout at an 8 mA average load. Nor is the typical dropout a worst-case guarantee. The actual protected cell's cutoff is unspecified and cannot be assigned a fabricated value; any continued acquisition below 2.7 V AVDD would be out of spec. Existing early shutdown avoids relying on that cutoff.

U4's MCP73831 symbol is pin-compatible with the fitted TP4054 here: 1 CHRG, 2 GND, 3 BAT, 4 VCC, 5 PROG. C24=1 uF meets the VCC bypass recommendation; C25=10 uF is present at BAT. The charger's reverse-current blocking with VCC absent is **not reverse-polarity protection**. There is no dedicated power-path controller: device load comes from BAT and contributes to the charge-termination measurement. Nominal termination is 10 mA; AFE-off idle load is well below this in the intended charging state, so no definite termination failure is established. Cell charging limits still require F6 qualification.

R6/R7=1 Mohm/1 Mohm yield **500 kohm Thevenin resistance**. N-adc allows up to 800 kohm with **40 us** acquisition, exactly selected by the overlay. C30=100 nF further supplies transient sampling charge; the divider's 50 ms time constant is short relative to periodic battery reads. Full cell 4.2 V produces 2.1 V at AIN0, within the configured 3.6 V ADC scale and ordinary powered GPIO limits. This is **not a SAADC source-impedance violation**. Resistor ratio and ADC gain error limit absolute cutoff accuracy; no precision fuel gauge is claimed.

SW1 connects BUTTON to GND; the overlay enables its internal pull-up and active-low sense. `power_off()` waits for release then sets level-active wake, which maps to low-level GPIO SENSE. Nordic supports GPIO wake from System OFF and retains GPIO configuration. D1's anode is fed from +3V3 through R8=1 kohm and cathode reaches P0.15; active-low drive sinks approximately 1–1.5 mA. The firmware turns it off before System OFF. No inverted LED or missing mandatory external button pull-up was found.

### Sleep-current and shelf-life estimate

Assume a correctly flashed board, no debugger, no charger, button released, LED off, PWDN held low, idle I2C lines high, and both IMU sensors stopped. `power_off()` calls `acq_stop()` (which calls `imu_stop()` while streaming) then `ads_prepare_off()`. The ADC_PWDN 100 kohm pull-down has essentially no DC voltage across it in this state.

| Contributor | Estimated current | Evidence / limitation |
|---|---:|---|
| nRF System OFF | 0.3 uA | N-power, no RAM retention; exclude debugger's emulated OFF |
| ADS hardware power-down | approximately 3 uA | TI §7.5 gives 10 uW at 3 V supply conditions; approximate conversion for this rail arrangement, not a 3.3 V maximum guarantee |
| IMU both sensors off | 3 uA | ST Table4 typical |
| R6+R7 battery divider | 1.85 uA at 3.7 V | 3.7 V / 2 Mohm |
| R12+R13 RLDREF divider | approximately 1.65 uA | 3.3 V / 2 Mohm; present even when ADS is off |
| XC6206 own supply current | 1 uA typical | TX pp.1/4; 3 uA max at stated conditions |
| TP4054 battery drain, VCC absent | approximately 1 uA typical, 2 uA limit | TP electrical table; do not confuse VCC shutdown current with drain from BAT |
| **Total excluding pack protection** | **approximately 11 uA** | Typical planning estimate, not a summed guaranteed maximum |
| Protected-cell circuit + self-discharge | **unknown** | No exact pack specification supplied |

130 mAh / 0.011 mA ≈ **11,800 hours ≈ 1.35 years** is an ideal full-capacity upper planning number before pack protection and self-discharge. With 80% usable capacity it is approximately **13 months**; adding 1–5 uA protector drain gives roughly **9–12 months** before self-discharge. Those protector numbers are examples, not the specification of this cell. A partly discharged unit placed into storage lasts less, especially after low-battery shutdown. Use a **months-scale storage/recharge policy**, not a guaranteed one-year shelf-life claim. A switch is optional for use, useful for storage.

## Electrode flex interface

The main J1 netlist matches the current `docs/layout/flex_c_layout.md` table exactly:

| J1 contacts | Net |
|---|---|
| 1, 20 | GND, covered shield/return |
| 2, 19 | BIAS_E, all eight middle electrodes |
| 3/4 | E1P/E1N |
| 5/6 | E2P/E2N |
| 7/8 | E3P/E3N |
| 9/10 | E4P/E4N |
| 11/12 | E5P/E5N |
| 13/14 | E6P/E6N |
| 15/16 | E7P/E7N |
| 17/18 | E8P/E8N |

Each signal then passes its own 10 kohm array element to the correct ADS input. No P/N swap or lost channel was found. The current flex document preserves J1.n→J1.n through the distal U-turn and identifies pod 4 under the antenna; older pod-3 wording is not evidence of an electrical net reversal. Physical contact-face/continuity qualification remains separate from the schematic pin-map check.

## Complete IC pin ledger

Every row was compared against the corresponding datasheet pin table and exported netlist. `NC` below means deliberately unconnected. Capacitors listed terminate at GND. Unless a row references F1–F8, its disposition is **OK/NOTE**, with no schematic fix indicated. The tables preserve physical pin numbers, including the nRF exposed pad 49. Supply groups are not inferred solely from a visible symbol pin.

### U2 — TI §6, TQFP pin table pp.10–11

| Pin | Function | Saved schematic connection / check |
|---|---|---|
| 1 | IN8N | Net-(RN4D-R4.1); E8N through its own 10 kohm RN element |
| 2 | IN8P | Net-(RN4C-R3.1); E8P through its own 10 kohm RN element |
| 3 | IN7N | Net-(RN4B-R2.1); E7N through its own 10 kohm RN element |
| 4 | IN7P | Net-(RN4A-R1.1); E7P through its own 10 kohm RN element |
| 5 | IN6N | Net-(RN3D-R4.1); E6N through its own 10 kohm RN element |
| 6 | IN6P | Net-(RN3C-R3.1); E6P through its own 10 kohm RN element |
| 7 | IN5N | Net-(RN3B-R2.1); E5N through its own 10 kohm RN element |
| 8 | IN5P | Net-(RN3A-R1.1); E5P through its own 10 kohm RN element |
| 9 | IN4N | Net-(RN2D-R4.1); E4N through its own 10 kohm RN element |
| 10 | IN4P | Net-(RN2C-R3.1); E4P through its own 10 kohm RN element |
| 11 | IN3N | Net-(RN2B-R2.1); E3N through its own 10 kohm RN element |
| 12 | IN3P | Net-(RN2A-R1.1); E3P through its own 10 kohm RN element |
| 13 | IN2N | Net-(RN1D-R4.1); E2N through its own 10 kohm RN element |
| 14 | IN2P | Net-(RN1C-R3.1); E2P through its own 10 kohm RN element |
| 15 | IN1N | Net-(RN1B-R2.1); E1N through its own 10 kohm RN element |
| 16 | IN1P | Net-(RN1A-R1.1); E1P through its own 10 kohm RN element |
| 17 | TESTP_PACE_OUT1 | +3V3A; Unused test/pace pin: AVDD per TI footnote; pace disabled |
| 18 | TESTN_PACE_OUT2 (symbol typo) | +3V3A; TI name TESTN_PACE_OUT2; unused: AVDD per footnote |
| 19 | AVDD | +3V3A; Supply/return correct |
| 20 | AVSS | GND; Supply/return correct |
| 21 | AVDD | +3V3A; Supply/return correct |
| 22 | AVDD | +3V3A; Supply/return correct |
| 23 | AVSS | GND; Supply/return correct |
| 24 | VREFP | Net-(U2-VREFP); C6 10 uF + C1 100 nF; internal 2.4 V reference |
| 25 | VREFN | GND; Negative reference = AVSS |
| 26 | VCAP4 | Net-(U2-VCAP4); C2 1 uF |
| 27 | NC | NC; True NC; optional tie is not mandatory |
| 28 | VCAP1 | Net-(U2-VCAP1); C5 22 uF |
| 29 | NC | NC; True NC; optional tie is not mandatory |
| 30 | VCAP2 | Net-(U2-VCAP2); C4 1 uF |
| 31 | RESV1 | GND; Required logic-low strap |
| 32 | AVSS | GND; Supply/return correct |
| 33 | DGND | GND; Supply/return correct |
| 34 | DIN | SPI_MOSI; SPI DIN from P0.08 |
| 35 | ~{PWDN} | ADC_PWDN; Shared PWDN/RESET; R11 100 kohm low; firmware sequencing above |
| 36 | ~{RESET} | ADC_PWDN; Shared with PWDN; independent reset by SPI command |
| 37 | CLK | NC; NC with CLKSEL high, CLK_EN=0 |
| 38 | START | ADC_START; Separate START GPIO P0.13 |
| 39 | ~{CS} | ADC_CS; CS active low P0.06 |
| 40 | SCLK | SPI_SCK; SCK P0.07; mode 1 |
| 41 | DAISY_IN | GND; Required ground when unused |
| 42 | GPIO1 | GND; Ground; GPIO remains input |
| 43 | DOUT | SPI_MISO; MISO to P0.11 |
| 44 | GPIO2 | GND; Ground; GPIO remains input |
| 45 | GPIO3 | GND; Ground; GPIO remains input |
| 46 | GPIO4 | GND; Ground; GPIO remains input |
| 47 | ~{DRDY} | ADC_DRDY; DRDY to P0.12 |
| 48 | DVDD | +3V3; Supply/return correct |
| 49 | DGND | GND; Supply/return correct |
| 50 | DVDD | +3V3; Supply/return correct |
| 51 | DGND | GND; Supply/return correct |
| 52 | CLKSEL | +3V3; High selects internal clock |
| 53 | AVSS1 | GND; Charge-pump ground |
| 54 | AVDD1 | +3V3A; Charge-pump supply; C33 1 uF on this rail |
| 55 | VCAP3 | Net-(U2-VCAP3); C3 1 uF / 25 V; boosted node |
| 56 | AVDD | +3V3A; Supply/return correct |
| 57 | AVSS | GND; Supply/return correct |
| 58 | AVSS | GND; Supply/return correct |
| 59 | AVDD | +3V3A; Supply/return correct |
| 60 | RLDREF | RLDREF; R12/R13 1 Mohm divider, C32 1 uF; CONFIG3.RLDREF_INT=0 |
| 61 | RLDINV | Net-(U2-RLDINV); R1 1 Mohm parallel C12 4.7 nF to RLDOUT |
| 62 | RLDIN | RLD_DRV; Mux input tied to RLDOUT, before R2 |
| 63 | RLDOUT | RLD_DRV; Feedback plus R2 100 kohm to BIAS_E |
| 64 | WCT | NC; NC; WCT amplifiers disabled |

### U1 — N-pin QFN48 table; N-ref LDO schematic

| Pin | Function | Saved schematic connection / check |
|---|---|---|
| 1 | DEC1 | DEC1; C13 100 nF |
| 2 | P0.00/XL1 | NC; No LFXO; unused GPIO |
| 3 | P0.01/XL2 | NC; No LFXO; unused GPIO |
| 4 | P0.02/AIN0 | VBAT_SENSE; AIN0; R6/R7 divider, C30 100 nF |
| 5 | P0.03/AIN1 | I2C_SDA; TWI SDA P0.03 |
| 6 | P0.04/AIN2 | I2C_SCL; TWI SCL P0.04 |
| 7 | P0.05/AIN3 | NC; Unused GPIO |
| 8 | P0.06 | ADC_CS; CS GPIO 6 |
| 9 | P0.07 | SPI_SCK; SCK GPIO 7 |
| 10 | P0.08 | SPI_MOSI; MOSI GPIO 8 |
| 11 | NFC1/P0.09 | NC; NFC unused; no GPIO freeing needed |
| 12 | NFC2/P0.10 | NC; NFC unused; no GPIO freeing needed |
| 13 | VDD | +3V3; VDD bypass C17/C18 100 nF + C16 10 uF on common rail |
| 14 | P0.11 | SPI_MISO; MISO GPIO 11 |
| 15 | P0.12 | ADC_DRDY; DRDY GPIO 12 |
| 16 | P0.13 | ADC_START; START GPIO 13 |
| 17 | P0.14 | ADC_PWDN; PWDN/RESET GPIO 14 |
| 18 | P0.15 | LED; Active-low LED GPIO 15 |
| 19 | P0.16 | BUTTON; Button GPIO 16; internal pull-up |
| 20 | P0.17 | CHG_N; CHRG GPIO 17; internal pull-up; F1 |
| 21 | P0.18/SWO | NC; Unused GPIO |
| 22 | P0.19 | NC; Unused GPIO |
| 23 | P0.20 | NC; Unused GPIO |
| 24 | P0.21/~{RESET} | NRST; TP4; reset requires UICR configuration |
| 25 | SWDCLK | SWDCLK; TP3 SWD clock |
| 26 | SWDIO | SWDIO; TP2 SWD data |
| 27 | P0.22 | NC; Unused GPIO |
| 28 | P0.23 | NC; Unused GPIO |
| 29 | P0.24 | IMU_INT; IMU INT1; low-frequency input |
| 30 | ANT | Net-(U1-ANT); C21 0.8 pF shunt, L1 3.9 nH series |
| 31 | VSS | GND; RF ground |
| 32 | DEC2 | NC; NC per QFN LDO reference |
| 33 | DEC3 | DEC3; C14 100 pF |
| 34 | XC1 | Net-(U1-XC1); Y1.3 + C19 12 pF |
| 35 | XC2 | Net-(U1-XC2); Y1.1 + C20 12 pF |
| 36 | VDD | +3V3; VDD bypass on common rail |
| 37 | P0.25 | NC; Unused GPIO |
| 38 | P0.26 | NC; Unused GPIO |
| 39 | P0.27 | NC; Unused GPIO |
| 40 | P0.28/AIN4 | NC; Unused GPIO |
| 41 | P0.29/AIN5 | NC; Unused GPIO |
| 42 | P0.30/AIN6 | NC; Unused GPIO |
| 43 | P0.31/AIN7 | NC; Unused GPIO |
| 44 | NC | NC; Mandatory NC |
| 45 | VSS | GND; Ground |
| 46 | DEC4 | DEC4; C15 1 uF |
| 47 | DCC | NC; NC; DC/DC disabled |
| 48 | VDD | +3V3; VDD bypass including C16 10 uF |
| 49 | VSS | GND; Exposed pad grounded |

### U5 — ST Table2 and Table18

| Pin | Function | Saved schematic connection / check |
|---|---|---|
| 1 | SDO/SA0 | GND; SA0 low: address 0x6A |
| 2 | SDX | GND; Mode 1: ground explicitly permitted |
| 3 | SCX | GND; Mode 1: ground explicitly permitted |
| 4 | INT1 | IMU_INT; INT1 to P0.24; active-high DRDY |
| 5 | VDDIO | +3V3; VDDIO; common +3V3 bypass C31 100 nF |
| 6 | GND | GND; Ground |
| 7 | GND | GND; Ground |
| 8 | VDD | +3V3; VDD; common +3V3 bypass C31 100 nF |
| 9 | INT2 | NC; Unused output, NC |
| 10 | NC | NC; Must remain unconnected |
| 11 | NC | NC; Must remain unconnected |
| 12 | CS | +3V3; High enables I2C |
| 13 | SCL | I2C_SCL; SCL to P0.04; R10 10 kohm pull-up |
| 14 | SDA | I2C_SDA; SDA to P0.03; R9 10 kohm pull-up |

### U3 — TX p.3 SOT-23 table

| Pin | Function | Saved schematic connection / check |
|---|---|---|
| 1 | GND | GND; VSS, correct SOT-23 order |
| 2 | VO | +3V3; VOUT; C27 1 uF plus rail bulk |
| 3 | VI | VBAT; VIN; C26 1 uF; reverse-battery risk F3 |

### U4 — TP pin functions; actual TP4054 names take precedence over MCP73831 symbol labels

| Pin | Function | Saved schematic connection / check |
|---|---|---|
| 1 | CHRG | CHG_N; Actual TP4054 CHRG; internal MCU pull-up; F1 |
| 2 | GND | GND; GND |
| 3 | BAT | VBAT; BAT; C25 10 uF, system load and protected pack |
| 4 | VCC | VCHG; VCC; C24 1 uF; reverse-clip risk F2 |
| 5 | PROG | Net-(U4-PROG); PROG through R4 10 kohm to GND; nominal 100 mA |

## Differences from earlier records and review limits

Current facts override historical recommendations: RN1–RN4 are 10 kohm; RLDIN is on RLDOUT; C33 is present; C6/C28 are 0603 10 uF; C34 is 12 pF; R9/R10 are 10 kohm; R11 exists; external RLDREF is fitted and firmware selects it. `docs/firmware_c.md` still contains historical statements that ADC_PWDN has no pull-down, and the opening `ads1298.c` comment says RLDREF is open. Those statements are stale; the actual code/netlist are compatible. No changes were made to those documents.

This review did not re-run layout DRC, prove capacitor placement, qualify production assembly, measure RF/contact noise, run firmware on hardware, or establish a specific cell's limits. No calculated or previously simulated phase margin is represented as a datasheet guarantee. The checked firmware pin map, register choices and timing provide a feasible bring-up path; they do not prove real-time throughput without a capable BLE central and physical testing.

**BOARD-KILLER items: none confirmed. FEATURE-KILLER items: none confirmed.** The specific confirmed repairable limitations are F1 (charger-presence/interlock coverage), F2 (reversed charge clip), and F3 (reversed battery). F4 quantifies the unavoidable current of the present always-connected architecture; F5–F9 are explicit qualifications, not asserted feature failures.
