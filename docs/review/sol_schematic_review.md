# neurband schematic review — Sol

Review only; 2026-10-25. Generator locations: `boards/neurband_main/gen_main_sch.py`, `boards/neurband_electrodes/gen_electrodes_sch.py`. Sources: both generators, exported schematic netlists, rendered main schematic, local ADS1298 datasheet and [Meta research](../research/meta_semg_research.md). No hardware measurements; “good dry-electrode data” remains a bench acceptance criterion.

## Decision

Keep **16 channels, two ADS1298s, passive flex and ESP32-S3/Wi-Fi**. Remove the IMU, charger, LEDs, battery divider, power switch and on-board USB; program through unpopulated UART/EN/BOOT pads **off-body**, charge a removable protected battery externally. Keep both LDOs and input protection. This removes conveniences rather than EMG capability.

## Electrical findings

- **ADS startup needs explicit correction/validation.** `ads()` ties RESET and PWDN together and leaves CS/START/control levels unspecified during MCU boot. PWDN stops the oscillator/reference; RESET needs a running clock; U3 has no clock until U2's `CLK_EN=1`. For the minimum design, hold PWDN/RESET high and reset by individually selected SPI commands; add two CS pullups and one START pulldown. Initialize U2/CLK_EN before resetting/configuring U3. Wait at least 2^18 clock cycles (~128 ms), or until VCAP1 exceeds 1.1 V, whichever is later; repeat the slave wait after its clock starts. Do not assume one shared pulse initializes both chips. [ADS §§9.3.2.2–3, 9.3.2.6, 11.1]
- **Multi-device topology otherwise sound:** shared SPI with separate CS is supported; DOUT becomes high-impedance when deselected. Never select both chips simultaneously. Shared START/clock and identical rates allow U2-only DRDY; read both complete 27-byte frames before the next conversion. Unrelated SCLK edges also clear DRDY: avoid losing its event. SPI traffic is **1.728 Mbit/s**, versus 1.536 Mbit/s electrode payload. Enable HR/4 kSPS, both 2.4 V reference buffers and internal RLD reference; enable only U2's RLD amplifier and select suitable RLD_SENS inputs on both chips. Shared RLDINV matches **Figure 45**, not an amplifier-output short. The 1M||1.5nF feedback is connected correctly, but stability must be tested with real contacts/cable capacitance and the selected number of inputs.
- **Unused ADS pins/supplies:** all stacked AVDD/DVDD/ground pins connect correctly; VCAP1=22µF, other VCAPs=1µF; VREFN/RESV1/DAISY_IN grounded; NC27/29 and WCT floating are appropriate. TESTP/N tied AVDD is specified for unused pins: never enable pace outputs. Keep grounded GPIOs configured as inputs. RLDREF may float only with internal-reference selection. RLDIN is a mux input, not another driver. Do not share VCAPs or parallel internal VREFP buffers.
- **DC coupling:** gain 6 gives ±400mV differential range, not unlimited electrode-offset tolerance. At 350mV differential, allowable common mode is only 1.25–1.75V on 3V AVDD. Bias-contact loss, polarization and motion can clip before any software high-pass. Check raw DC/saturation and recoverability; start with lead-off excitation disabled.
- **Power:** 3V AVDD/3.3V DVDD is legal. [AP2112](https://www.diodes.com/assets/Datasheets/AP2112.pdf) dropout is up to 200mV at 300mA; radio peaks can brown out before the analog rail fails. Do not promise operation down to the cell protector threshold. A single 3V rail has no ESP supply margin; LP5907's 250mA rating is unsuitable for the whole Wi-Fi load. Verify effective ceramic capacitance, not just printed values. VCAP1 X5R is microphonic; TI recommends nonferroelectric dielectric under vibration (§11).
- **Charger/off-state:** MCP73831's ~213mA setting must suit the cell. It has no power-path/load sharing: running Wi-Fi while charging can prevent termination and discharge the battery despite USB. R11/R12 still drive an unpowered ESP input when the enable switch is off; remove the divider or feed its top from PWR_EN (zero added parts, grounded when off). Use a protected cell; the charger is not discharge protection.

- **USB omission if retained:** GPIO19=D−/GPIO20=D+ routing is correct, but VBUS never reaches an ESP input. A self-powered CDC device needs [VBUS monitoring](https://docs.espressif.com/projects/esp-usb/en/latest/esp32s3/usb_device.html#self-powered-device) and pullup/disconnect control; add a safe divider/comparator or delete USB as recommended. Two independent CC pulldowns and USBLC6 flow-through wiring are correct.

- **MCU/IMU:** [ESP straps/EN](https://documentation.espressif.com/esp32-s3-mini-1_mini-1u_datasheet_en.pdf) are valid: GPIO0 internal pullup, GPIO45/46 pulldowns; BOOT grounds GPIO0; EN has 10k/1µF. The S2-named footprint needs S3-specific outline/antenna-keepout verification. [LSM6DSO](https://www.st.com/resource/en/datasheet/lsm6dso.pdf) pin assignments match the LSM6DSL symbol; CS high/SA0 low selects 0x6A. If retained, provide separate local 100nF bypasses at VDD/VDDIO, rather than one shared capacitor.

## Ranked cuts

Savings are **physical packages**, not resistor elements; RN1–RN8 are **eight** four-resistor arrays, not four.

| Change | Saves | Risk | Recommend yes/no |
|---|---:|---|---|
| Drop IMU U4/C27/R5/R6 | 4 | No motion labels/fusion; EMG unchanged | Yes |
| External charging: drop U5/R9/D1/R10/C29 | 5 | Must unplug pack to charge; retain C28 if USB remains | Yes |
| Drop USB J1/U6/R7/R8/C28; use programming pads | 5 | External UART programmer; no wired streaming | Yes |
| Drop status D2/R4 | 2 | No visual status; host can report it | Yes |
| Drop battery divider R11/R12/C34 | 3 | No battery telemetry; short, supervised sessions | Yes |
| Drop SW1; unplug battery for off/reset | 1 | Less convenient | Yes |
| One shared 3.3V LDO; remove analog LDO/bypass | ~3 | Wi-Fi transients couple into AFE; noise unproven | No, first spin |
| Feed AVDD directly from battery | ~3 | Supply/bias moves with battery and RF load | No, first spin |
| Delete input arrays | 8 | Lose series current/ESD/RF limiting for only ~0.36µVrms resistor noise | No |
| Fit only one ADS1298 | 16: IC+4 arrays+11 capacitors | Loses eight channels/spatial coverage and dataset compatibility | No; useful 8-ch experiment only |
| One bias contact instead of sixteen | 0 assembled parts; 15 copper contacts | Worse contact redundancy; no IC/net reduction | No strong benefit |
| Daisy-chain SPI instead of two CS | 0; one MCU net | More coupled readout/debugging | No |

A “single ground electrode” must mean **midrail-biased body contact**, not circuit GND: grounding the body violates the unipolar ADS common-mode range. Existing middle contacts already share one net; keeping all sixteen costs no assembly. Meta's middle-contact role is not publicly established as active bias.

## Architecture alternatives

[ADS1299](https://www.ti.com/product/ADS1299) needs 4.75–5.25V analog power: extra conversion, not simpler. [ADS131M08](https://www.ti.com/product/ADS131M08) presents 330kΩ at low gains and ≥1MΩ at higher gains; dry electrodes need buffering for robust performance, undoing the IC saving. Sixteen discrete INAs plus filters and an MCU ADC multiply parts and complicate noise/synchronization.

[Intan RHD2216](https://intantech.com/files/Intan_RHD2000_series_datasheet.pdf) is the strongest true integration alternative: **one 16-differential-channel AFE**, internal DC blocking/bandpass, 3.3V supply, ~2.4µVrms noise. However, its ADC is multiplexed, input range is ±5mV, and sourcing/package/firmware require a redesign. Evaluate it before a later clean-sheet revision; do not claim simultaneous ADS-equivalent sampling.

Keep ESP32-S3 for raw Wi-Fi transport. nRF52840 BLE saves power, not necessarily packages: [2M PHY yields roughly 1.4Mbit/s ideal application throughput](https://devzone.nordicsemi.com/f/nordic-q-a/104711/what-is-the-maximum-throughput-of-nrf53-ble-and-what-challenges-need-to-be-addressed-to-achieve-it), insufficient for 1.536Mbit/s raw. Filter/decimate ADS 4kSPS to 2kSPS first (768kbit/s at 24 bits), or high-pass and rescale before 16-bit packing. Blindly retaining the top 16 ADS bits gives 12.2µV steps. A USB-only MCU is viable electrically, but patient isolation adds system complexity; USB-powered is not the safe minimum.

## Noise, safety and first-spin acceptance

ADS HR/4kSPS/gain6 specifies ~1.5µVrms shorted-input noise and 1048Hz −3dB bandwidth (~−2dB at 850Hz), **not** Meta's complete 20–850Hz response. Native 2kSPS cuts bandwidth to 524Hz. Retain 4kSPS raw data; filter on the host and antialias before decimation. DC-coupled input cannot be repaired after clipping.

Passive 10–15cm traces precede amplification, unlike Meta's per-pod AFEs. ADS input is ~1GΩ/20pF, not Meta's 10TΩ/10pF; flex capacitance and unequal skin impedance convert mains pickup into differential noise. Route each pair together, away from radio/digital lines; insulate the grounded outer shield from skin. A hatch helps electric shielding but is not a Faraday enclosure and adds input capacitance. Series resistors alone are not a defined antialias filter; reserve/test differential RF capacitors (16 extra if needed), avoiding unmatched shunt capacitances.

**On-body: battery + wireless only; no charger, USB, debugger or grounded oscilloscope.** Neither 4.7k nor the shared 100k bias resistor provides mains isolation or medical single-fault protection. Tethering requires appropriately rated isolation of **both power and data** and leakage verification; a laptop or ordinary USB isolator is not automatically patient-safe.

**Count:** 69 existing main-board packages. Ranked low-risk cuts remove 20 → **49**, plus two CS pullups and one START pulldown → **~52 packages: 5 IC/modules, 30 capacitors, 8 arrays, 6 resistors, 2 connectors, BOOT button**. Copper electrodes/tail, battery and external programming/charging fixtures excluded. RF filtering may raise this to ~68.

Before skin use: verify startup/clock/register readback and coherent 16-channel streaming; measure shorted-input 20–850Hz noise, electrode-impedance imbalance/mains pickup, motion clipping and Wi-Fi burst coupling. No measured noise claim is established here.

**Checks performed:** KiCad 10.99.0 ERC: main **1 error/14 warnings**; shared DOUT error is a tri-state-symbol false positive, warnings concern specified rail ties. Flex **0 errors/49 warnings**, all missing `neurband` footprint-library links. Exported netlists verify all 32 input paths, supply pins, 16 bias pads and matching connector pin maps; physical FPC contact orientation still needs footprint verification. Reviewed main schematic render and ADS Figure 45. Temporary evidence: `/tmp/neurband-sol-{main,electrodes}-erc.rpt`, `/tmp/neurband-sol-{main,electrodes}.xml`.
