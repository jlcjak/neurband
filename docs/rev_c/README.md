# neurband rev C — design overview

Rev C is the build-it-now version: **8 channels, Bluetooth LE, ~$200 all-in**, a module about the size of a
small watch face (31.9 × 34.3 × 9.9 mm) on a band of 8 electrode pods. It keeps what matters from Meta's
research band (bipolar gold electrodes 20 mm apart along the forearm, a 24-bit front end with µV-level noise,
2 kHz data) and drops everything that only costs money.

Rev A (16 channels, Wi-Fi, 54 × 34 mm board) and rev B (compact 16-channel, unfinished) are in `archive/`;
their reasoning is in [`../DESIGN.md`](../DESIGN.md).

## Block diagram

```
 skin ─ 8 pods × (P, bias, N) gold pads, 6.5 mm, P–N 20 mm
          │ 2-layer polyimide flex, outer GND hatch, 20-pin 0.5 mm tail
          ▼
  J1 FPC ─ 16 × 10 kΩ ─ ADS1298 (8 ch, 24 bit, 4 kSPS, gain 6, internal 2.4 V ref)
                          ├─ RLD bias amp: 1 MΩ ‖ 4.7 nF, 100 kΩ → all 8 middle pads
                          └─ RLDREF: 2 × 1 MΩ + 1 µF (filtered AVDD/2)
                          │ SPI (CS, SCK, MOSI, MISO, DRDY, START, PWDN)
                          ▼
                     nRF52832 (BLE 5, 2M PHY) ─ printed inverted-F antenna (TI SWRA117D)
                          ├─ LSM6DSL IMU (I²C)
                          ├─ button (wake / marker), LED
                          └─ SWD pads (bottom)
  LiPo 401225 ~100 mAh ─ XC6206 3.3 V LDO ─ 10 Ω/10 µF RC → ADS AVDD
  charge pads (bottom, recessed) ─ TP4054 (100 mA)
```

## What the numbers say

| | Value | Source |
|---|---|---|
| ADC noise, 20–850 Hz, 4 kSPS, gain 6 | ~1.2 µVrms | [science/signal_chain.md](../science/signal_chain.md) |
| Single-muscle EMG at 5 % effort, under the band | 14–81 µVrms (model; may be high by up to 2×) | [science/emg_forward_model.md](../science/emg_forward_model.md) |
| Mains residual, battery-powered, 30 % contact mismatch | ≤ 1.5 µV (simulated) | [science/simulations.md](../science/simulations.md) |
| Bias loop phase margin, 8 sensed inputs, 4.7 nF | 57° worst case (simulated) | same |
| Stream | 2 kSPS × 8 ch, 16 bit, 0.25 µV/count after 20 Hz high-pass (4 kSPS acquisition + FIR) | [firmware_c.md](../firmware_c.md) |
| Per-user gesture accuracy to expect | 6–8 hand/wrist postures ~90–98 %; pinches/swipes ~75–90 % | [science/data_and_models.md](../science/data_and_models.md) |
| Not expected | cross-user models without calibration, typing, fluent handwriting | same |

## Design decisions (why it looks like this)

1. **8 channels, one ADS1298.** The ADC is most of the cost ($20 per 8 channels). The consumer Neural Band
   reportedly streams 8 channels at ~2 kHz. The forward model shows 8 channels separate single muscles at
   98–100 % and subtle co-activations at 70–74 % (16 channels: 78–87 %), so 16 is a later upgrade, not a
   requirement to start.
2. **Passive flex, gold pads, compliant backing.** Each 6.5 mm ENIG pad sits on a 1.5 mm foam disc in a printed
   pod and stands 1 mm proud. Dry contact is the dominant risk (signal_chain §2), and 2 mm spring pins convert about
   10× more mains than a 6.5 mm pad (forward model), so big pads with even pressure win.
3. **Bias in every pod, external RLDREF.** The bias amplifier senses 8 inputs by default (stable, 25 dB mains
   reduction). Its reference comes from a filtered divider, because radio bursts on the shared 3.3 V rail would
   otherwise reach the body through the internal AVDD/2 reference (0.6–7 µVrms, simulations Q4).
4. **nRF52832 chip-down + printed antenna.** BLE at ~10 mA instead of Wi-Fi at ~150 mA means a 100 mAh cell and a
   10 mm-thick module. The printed antenna costs nothing; a π network (0 Ω + 2 DNP) allows tuning on the bench.
5. **One basic LDO.** BLE currents are small; the ADS analog rail is RC-filtered and its bias reference is
   filtered separately. A second LDO stays a rev D option if the radio-on noise test fails.
6. **Charging only off the wrist.** The charge pads are on the bottom of the board, behind a 1.7 mm recess in the
   module floor; the magnetic charger puck can only reach them when the band is off. The firmware also powers the
   ADC down while charging.
7. **Cost-first parts.** Basic/preferred parts wherever possible; 6 extended parts in total; one-sided assembly;
   standard 0.3 mm vias (the board grew 0.7 mm rather than use small drills).

## Wearing it

The forward model shows that placement matters as much as channel count:

- Wear the band so the pods sit about **4–6 cm above the wrist crease** (more muscle, less tendon under the pads).
- Keep the module **centred on the back of the wrist**, and put it back the same way every time (half-pitch
  rotations of ±9 mm drop an un-augmented classifier from 99 % to ~60 %).
- Let dry pads settle ~5 minutes before recording; check the quality report every session.

## Files

| What | Where |
|---|---|
| Schematic (generated) | `boards/neurband_c/gen_c_sch.py` → `neurband_c.kicad_sch` |
| Main board | `boards/neurband_c/neurband_c.kicad_pcb`, [layout notes](../layout/main_c_layout.md) |
| Electrode flex | `boards/neurband_c_flex/`, [layout notes](../layout/flex_c_layout.md) |
| Mechanics | `mech/rev_c/`, [mechanical_c.md](../mech/mechanical_c.md) |
| Firmware (Zephyr) | `firmware_c/`, [firmware_c.md](../firmware_c.md) |
| BLE recorder | `host/neurband_ble.py` |
| Analysis / models | `analysis/`, [science/README.md](../science/README.md) |
| Simulations | `sim/`, [simulations.md](../science/simulations.md), [emg_forward_model.md](../science/emg_forward_model.md) |
| Cost | [cost.md](cost.md) |
| Reviews | [../review/](../review/) |
