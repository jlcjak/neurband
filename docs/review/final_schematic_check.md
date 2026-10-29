# neurband rev C: final pin-by-pin schematic check

Independent, read-only check before ordering (2026-10-29). Every IC pin was traced in the exported
netlist and compared with its datasheet (TI SBAS459K for the ADS1298, Nordic nRF52832 PS v1.0 §53.1 for
the reference circuit, ST LSM6DSL DocID028475, Torex XC6206, TP4054), and the firmware pin map and register
values were compared with the hardware. Inputs: schematic SHA-256 `5797e7c0…`, board `ff1ad4d2…`
(schematic parity 0, unconnected 0). A parallel review by the layout owner is in
[sol_final_schematic_review.md](sol_final_schematic_review.md); both reach the same verdict.

## Verdict

**No BOARD-KILLER and no FEATURE-KILLER.** Every IC pin is connected as its datasheet requires and the
firmware pin map matches the schematic net by net.

| # | Area | Finding | Severity |
|---|---|---|---|
| F1 | ADS1298 power-up | `ads_power_up()` sends the RESET opcode 300 ms after PWDN/RESET rise. TI §11.1 asks for the reset after tPOR **or once VCAP1 > 1.1 V, whichever is later**; with 22 µF on VCAP1 (Fig. 31, R1 = 12.5 kΩ) that is ~0.55–0.82 s. VREFP is also still ~11 % low when the function returns. Likely harmless (registers are pin-reset, rewritten and verified), but outside the datasheet sequence. Fix: wait ≥ 1 s before the RESET opcode, ~2 s before trusting absolute amplitude | FIRMWARE-FIXABLE |
| F2 | Charger interlock | After charge termination the TP4054 CHRG pin becomes a weak ~8–35 µA pull-down; against the nRF's 11–16 kΩ pull-up it reads "not charging" while the charger is still attached, so the firmware can re-enable the AFE. Fix: precharge the pin high, release the pull-up, read after ~100 µs (three-state detection the TP4054 datasheet describes) | FIRMWARE-FIXABLE |
| F3 | Charge current | PROG = 10 kΩ → 90–110 mA: fine for the 130 mAh cell (0.7–0.85C); 1.5–2.2C for a 50–60 mAh fallback cell | BODGEABLE (R4 → 20 kΩ with a small cell) |
| F4 | Charge input | No reverse-polarity protection on VCHG (TP4054 VCC −0.3 V min). A mis-wired clip can destroy U4. The clip is keyed; meter it before first use | BODGEABLE |
| F5 | U3 XC6206 pinout | Schematic/footprint match Torex (1 VSS, 2 VOUT, 3 VIN). The fab's parts-library symbol for C5446 swaps pins 2/3; **don't accept a "pin swap" suggestion from the fab's review** | OK (note) |
| F6 | Docs/comments | `docs/firmware_c.md` bring-up step 1 says no ADC_PWDN pull-down (R11 100 kΩ is fitted); `ads1298.c` header says "RLDREF pin open" (the divider is fitted and CONFIG3 = 0xC4 is correct) | OK (stale text) |
| F7 | J2 silk | "+" is over VBAT (correct); there is no "−" over GND | OK (cosmetic) |
| F8 | VCAP1 dielectric | C5 22 µF X5R. TI §11 recommends tantalum or C0G on VCAP1 where the board vibrates (piezoelectric noise); a wrist band moves. Bench test: `--mode short` and tap the module; if all channels step together, swap C5 for a 22 µF tantalum | DEGRADED (possible) |

Also checked and OK: ADS1298 pins 27/29 (true NC), TESTP_PACE_OUT1/2 to AVDD (TI footnote "connect
unused pins to AVDD"; isolated when INT_TEST = 1), shared ~PWDN/~RESET with the RESET opcode (allowed by
§9.3.2.3/§11.1), CLKSEL/CLK, GPIO1–4/DAISY_IN/RESV1 to GND, VCAP1–4 and VREFP values, RLD loop and external
RLDREF, input range at gain 6 down to AVDD ≈ 2.9 V, all register values; nRF52832 LDO-mode reference
circuit, 32 MHz crystal load, LFRC, GPIO map, NFC pins unused, reset/SWD; LSM6DSL CS high (I²C), SA0 low
(0x6A), aux pins, INT1; XC6206 dropout down to the 3.3 V firmware cut-off; VBAT divider vs SAADC (500 kΩ at
40 µs TACQ); LED (active low), button, System OFF wake; J1 pinout vs the flex.

Sleep current in System OFF ≈ 11–16 µA on the board (+ ~3 µA cell protector): roughly 6–9 months of shelf
life on the 130 mAh cell. Bench check: SCK/MOSI float in the sleep pin state; if sleep current is well above
~20 µA, drive them low.
