# Rev C analog pre-order review: noise and interference into the EMG inputs

## Re-check of the reworked board (2026-10-29)

Board: `boards/neurband_c/neurband_c.kicad_pcb`, SHA-256 `0b4550553c25…98e8`, matching
`boards/neurband_c/layout/preorder_release.json`. The schematic is the current `gen_c_sch.py`. This was a
read-only, independent re-run:

- **Changes to the scripts.** `coupling.py`, `inject.py` and `ground.py` were rerun with:
  - **new 2D tables for the as-built 3313 stack** (`out/xsec_tables_3313.json`): 0.0994 mm prepreg at εr 4.1,
    0.70 mm core at εr 4.4, 15 µm inner copper;
  - the real **10 kΩ** on the ADS-side nodes;
  - a new **via-land victim** pass (`via_lands.py`), which the original extractor lacked.
- **New checks.** `nrf_rf_check.py` (nRF RF/decoupling layout), `power_paths.py` (DC path resistance) and
  `q6_rework_loop.py` (RLD loop with the new parts).
- **Where the outputs are.** Everything carries a `_rework` / `_rework3313` suffix in `sim/preorder/out/`.
  For comparison, the pre-rework board was extracted from git to `sim/preorder/build/neurband_c_head.kicad_pcb`.

### Verdict

**OK to order: no MUST items remain.**

- **M1 (I2C/IMU_INT against the inputs) is fixed:** CH1 went from 4.1 to 0.16 µVrms and CH4 from 1.3 to
  0.001 µVrms. No active digital net is routed over or beside an electrode trace on In2/B.Cu (minimum edge
  distance 0.95 mm).
- **M2 is fixed:** U2 pins 62 and 63 are both on `/RLD_DRV`, behind R2.
- **S1, S3 and S4 are fitted as recommended.** C34 is 12 pF rather than 22 pF; that is equivalent (§R4).
- **Two SHOULD items remain.** Both are small layout moves, and both were introduced by the rework:
  1. **E1N via next to the IMU's I2C pads.** The via at (24.3, 19.975) has a land-to-pad gap of **0.18 mm to U5
     pin 13 (SCL)** and 0.21-0.25 mm to pin 14 (SDA). Before the rework it was at y = 19.80, 0.35 mm away;
     the via/pad clearance repair moved it. That adds ≈ 3.4 + 2.6 fF. **CH1 becomes 0.16 µVrms at 1 MΩ‖10 nF
     and 1.4 µVrms at 1 MΩ‖1 nF**: coherent lines at 208 Hz × k, 1.6× over the 0.1 µV gate. The owner's
     0.045 µV comes from tracks and pads only, which is correct as far as it goes, but misses the via land.
     **Fix:** keep the E1N and E2P via lands ≥ 0.4 mm from U5 pads 13/14, for example back at y ≈ 19.80. That
     gives ≲ 1 fF each and brings CH1 to ≲ 0.07 µV. **If not fixed:** poll the IMU FIFO on a timer locked to
     the ADC frames, e.g. every 20 frames. The I2C bursts are then sample-synchronous, and their 200 Hz × k
     lines can be removed exactly by synchronous template subtraction.
  2. **RF: C18 on nRF VDD pin 36.** C18 (100 nF) now reaches pin 36 through a **6.0 mm track** (was 2.9 mm). Its
     GND pad sits **1.8 mm from a via** (was 0.5 mm), on a single-via F.Cu island shared with C14 (DEC3).
     **Fix:** rotate C18 so its +3V3 pad faces pin 36 and add a via at its GND pad, if the crystal routing
     allows. Otherwise accept: the link margin is 31-34 dB (`docs/science/antenna_sim.md`).

### Results table

| Check | Owner reports | This re-check (independent) | Verdict |
|---|---|---|---|
| Worst active-digital coupling, tracks + pads | 0.59 fF (CH1) | 0.59 fF on the old tables, same on the 3313 tables (E1N/I2C_SCL, F.Cu, 0.395 mm) | **Confirmed** |
| Worst coupling incl. via lands | — | **E1N: 3.39 fF (SCL) + 2.57 fF (SDA) + 1.1 fF tracks ≈ 7 fF**; E2P 0.63 fF; all other channels < 0.1 fF | **Refuted for CH1** |
| Injected, 1M‖10n | 0.045 µVrms (CH1) | Tracks/pads 0.043 (3313) / 0.045 (old). **With via lands: CH1 0.158, CH2 0.021, CH3 0.007, CH8 0.003, others ≤ 0.001 µVrms** | CH1 SHOULD |
| Injected, 1M‖1n | 0.354 µVrms | CH1 **1.40**, CH2 0.19, others ≤ 0.05 µVrms | — |
| P/N mismatch, board | 1.49 pF (CH1) | 1.49 pF on the old tables / **1.33 pF on 3313**. CH2-8: 0.07-0.43 pF. With the unchanged flex (≈ 1-1.5 pF), CH1 totals ≈ 2.5-3 pF; q5 shows this costs ≤ 0.1 µV battery-typical | **Confirmed**, acceptable |
| GND vias / via-free maximum | 103 / 3.73 mm at (20.37, 26.5) | 103 / 3.81 mm at (20.4, 26.6) on a 0.1 mm grid; RF and AFE regions ≤ 3.0 mm | **Confirmed** |
| U1 EP vias | 9 | 9, inside the EP; no copper under the matching keepout on In1/In2/B.Cu | **Confirmed** |

### R1. The owner's remaining items

| Item | Numbers | Acceptable to order? |
|---|---|---|
| E7N In2 reference gap, 2.0 mm at x 15.34-16.75, y 20.25-20.78 | The B.Cu copper under the gap is **E8P**, another quiet electrode net; no digital or rail copper. E7N-E8P is 151 fF broadside + 42 fF same-layer: crosstalk −94 dB (10 nF contacts) / −74 dB (1 nF), i.e. 0.02-0.2 µV per 1 mV of CH8 EMG. In1 (0.70 mm above) still references the trace, and the self-C change is < 0.1 pF. | **Yes** |
| Unfinished VBAT trunk / C27 star | J2 → U3 VIN is **180 mΩ** (was 300 mΩ), 4.5 mV at a 25 mA peak (20 mV at 100 mA charging, off-body). C27 is 1.3 mΩ from U3 VOUT. The +3V3 branch shared between the nRF and the AVDD tap is ≤ 26 mΩ, i.e. 0.4 mV of radio ripple against the LDO's own ~20 mVpp (q4). VBAT → E1P: 129 fF of tracks + 2 × 30 fF of via lands → **0.037 µV** (10 nF) / 0.26 µV (1 nF) with the 6 mV ripple model, ≈ 0.05 µV including the trunk drop. | **Yes** |
| Single-anchor GND fragments | I count **21** single-via fragments (F 10 / In2 6 / B 5) and none with zero vias; definitions differ from the owner's 18. | **Yes** |
| — longest ones | The longest extent from a via is **6.2 mm**: an In2 strip at x 6.6-8.7, y 12.2-22.0, beside the antenna fence. As a grounded stub its λ/4 resonance is ≈ 5.9 GHz (37° at 2.44 GHz), so it is not resonant in band. Others > 5 mm: In2 under U1's west edge (7.5 × 0.9 mm, 5.6 mm from its via); In2 under J1 (7.1 mm, 5.7); F.Cu along J1's south side (7.0 × 0.9 mm, 4.5); F.Cu between the arrays (5.0 mm, 3.4). | — |
| — component returns on single-via fragments | C27 + J1.1, C14 (DEC3) + C18, C19 + Y1 GND, C28, C10, C34, C1. Each GND pad is 0.6-1.8 mm from its via, i.e. ≤ ~1.5 nH: adequate for LDO, decoupling and load-cap returns. For C34 it is ≈ 10 Ω at 2.44 GHz in series with the 12 pF, still a shunt against the bias bus. | — |
| — optional improvement | NICE: a second via at the far end of the In2 strip beside the antenna fence, and at the C18 and C34 GND pads, where room allows. | — |
| 3.7 mm via-free point near the test pads | It sits at the bottom edge under J1, about 15 mm from the radiator, with a local via pitch of ≈ 7.5 mm (≈ λg/9 at 2.44 GHz). It is outside the RF and AFE regions (both ≤ 3.0 mm) and irrelevant for EMG. | **Yes** |

### R2. nRF52832 RF layout vs Nordic's QFN48 LDO reference (`out/nrf_rf_check_rework.json`, compared with the pre-rework board)

| Item | As built | Verdict |
|---|---|---|
| EP | 9 GND vias (0.30/0.45 mm), inside the EP, tented, paste 61 %. The pre-rework board had 0 | Good |
| DEC1 (pin 1) C13 100 nF | 1.2 mm, 1.3 mm track; GND pad 2.2 mm from a via (was 1.4) | OK |
| DEC3 (pin 33) C14 100 pF | 2.4 mm, 2.5 mm track; GND via 0.68 mm. Unchanged; the matching keepout and crystal crowd pins 30-35 | NICE: Nordic places it right at the pin |
| DEC4 (pin 46) C15 1 µF | 1.4 mm, GND via 0.55 mm | Good |
| VDD 48 / 13 | C17 100 nF at 1.5 mm (pin 48); C16 10 µF at 2.0 mm (pin 13) | Good |
| VDD 36 | **C18 100 nF: 6.0 mm track (was 2.9), GND via 1.8 mm (was 0.5)** | **SHOULD (regression)** |
| C21 0.8 pF return | Its GND pad has no pour; 4 dedicated GND track pieces run only to **VSS pin 31**; no via on them (nearest GND via 2.2 mm) | Matches Nordic |
| L1 / C21 position | C21 1.35 mm and L1 2.36 mm from ANT (pin 30). Both inside the matching keepout, unchanged | OK |
| Matching-section exclusion | Keepout (2.0-6.35, 4.8-6.85) on In1/In2/B.Cu: **0 mm² of fill, no tracks, no vias** | Good |
| Post-match feed (pi → antenna) | 0.16 mm, 12.2 mm, F.Cu, unchanged. ≥ 0.50 mm to the GND pour and to CHG_N/PROG/+3V3 on the uniform run. **0.22 mm from Y1 pad 1 (XC2)** over ≈ 0.4 mm, also before the rework: ≈ 5-10 fF, i.e. 8 kΩ at 2.44 GHz on a 50 Ω line | Acceptable, pre-existing |
| Crystal Y1 + C19/C20 | XC1 4.9 mm, XC2 5.3 mm (was 8.6), both F.Cu, no vias. In1 covers 94 % under the crystal (the rest is antipads). C19 GND via 0.63 mm; C20 1.9 mm (was 1.1). Y1 GND and C19 share a single-via island | OK |
| Digital/power copper under the matching network | None on any layer | Good |
| Copper near the crystal | **F.Cu:** +3V3 track ≈ 0.14 mm from the XC1 pad (decoupled rail: only adds load C, harmless); DEC3 0.23 mm; VCHG 0.44 mm (static). **In2/B.Cu**, under In1: +3V3, CHG_N, PROG, NRST, SWDIO and IMU_INT pass beneath. They are static or slow, shielded by In1 at 0.1 mm | Acceptable |
| ANT pin neighbour | IMU_INT on pin 29 is 0.24-0.29 mm from the ANT net (pre-existing). It is an input with 75 µs pulses at 208 Hz; Nordic asks for slow, low-drive signals near the radio, and this qualifies. It is static if INT1 is disabled | OK |

### R3. RLD loop and noise with the new parts

From `q6_rework_loop.py` / `out/q6_loop.csv`. The grid covers pads 100 kΩ-10 MΩ, bench-grounded/battery, the
1 nF body stress, GBW 100/50 kHz and 8 or 1 bias pads in contact.

| Configuration | N8, Cf 4.7 nF: worst PM nominal / 1 nF stress | N16, 4.7 nF | N16, 10 nF | 50 Hz suppression (N8) |
|---|---|---|---|---|
| First review: 4.7 kΩ, no C34, RLDIN on BIAS_E, bus 20 pF | 56.2° / 46.9° | 41.2° / 33.3° | 56.5° / 47.0° | 25.0-26.3 dB |
| As built: 10 kΩ, C34 12 pF, RLDIN on RLD_DRV, bus 20 pF | 56.2° / 46.8° | 41.1° / 33.2° | 56.5° / 46.9° | same |
| As built with the realistic flex bias bus, 140 pF (8 × 16 pF pads + bus) | **54.1° / 45.6°** | 39.4° / 32.3° | 54.4° / 45.7° | same |
| As built, bus 200 pF stress | 53.2° / 45.1° | 38.6° / 31.9° | 53.5° / 45.1° | same |

- **C34 and RLDIN.** The C34/RLDIN changes cost ≈ 0.1°. The flex bus (which was always there) costs ≈ 2°.
- **Firmware rule.** The default must stay at **N = 8 with 4.7 nF**; use 10 nF to sense all 16 inputs.
- **C34 at RF.** 12 pF C0G 0402 is a better 2.44 GHz shunt than 22 pF: its self-resonance with ~0.4 nH ESL is
  ≈ 2.3 GHz. The `gen_c_sch.py` comment on C34 still says "22 pF" (cosmetic).
- **Noise, 20-850 Hz incl. ADS at 4 kSPS (q5).**

  | Contacts | 4.7 kΩ | 10 kΩ |
  |---|---|---|
  | 1 MΩ‖10 nF | 1.39 µVrms | **1.44** µVrms |
  | 100 kΩ‖10 nF | 1.50 µVrms | 1.55 µVrms |
  | 1 MΩ‖1 nF | 2.87 µVrms | 2.90 µVrms |

  The two 10 kΩ alone are 0.52 µVrms over a rectangular band, which agrees with the owner's figure.
- **DC side.** Bias current through 10 kΩ gives 2 µV; 6 nA of lead-off gives 60 µV. Both irrelevant. Droop
  and CMRR are unchanged.

### R4. Anything else the rework introduced

- **E1N via (SHOULD) and C18 (SHOULD).** Covered in the verdict above.
- **ADS placement changes.**
  - Improved: C7 (AVDD 1 µF) 1.85 → 0.94 mm, C6 (VREFP 10 µF) 2.98 → 1.98 mm.
  - C33 is new, 1.5 mm from AVDD1 pin 54 with its GND via at 1.8 mm. That is an improvement, though not tight.
  - Moved out: **C3 (VCAP3)** 1.45 → 2.65 mm, with its GND via 0.6 → 2.0 mm; **C1 (VREFP 100 nF)**
    1.6 → 3.9 mm.
  - Both are NICE only. VCAP3 is a 1 µF charge-pump reservoir for which ~2 nH is irrelevant at 2 MHz; VREFP
    has its 10 µF closer now.
  - C12/R1 (RLD feedback) are 3.7 mm from pins 61/63. The RLD nodes couple to no active net, and
    RLDINV-RLD_DRV (22 fF) is in parallel with C12's 4.7 nF.
- **RLDREF divider.** R12/R13 now sit in the top-left corner (3.75-4.85, 1.9-4.0) beside the nRF/matching
  area, with RLDREF routed ~12 mm on In2 to C32. It is harmless: C32 stays 2.6 mm from pin 60, so radio
  ripple and ground differences at R12/R13 are filtered by 500 kΩ/1 µF (−52 dB at 133 Hz). The resistors
  cannot rectify RF.
- **Inner copper is now 15 µm** (Rs 1.13 mΩ/sq, ×2.3). Plane drops roughly double to ~16 µV CM at 10 mA,
  still < 0.03 µV differential. No action.
- **BIAS_E next to E2P/E2N.** The routing gives an asymmetry of 205 vs 127 fF. It acts only on the bias-to-body
  voltage, so it adds nV in battery use and ~1 µV only in the grounded 3.3 MΩ‖1 nF bench case (where q2
  already gives 28 µV). No action.
- **I2C pull-ups at 10 kΩ.** With about 15 pF of bus, the rise is ≈ 130 ns (30-70 %), below the 300 ns
  fast-mode limit. The in-band envelope is unchanged.
- **Flex.** The routing is unchanged (alignment-hole layers and manifest only), so §7 below stands.

---

## Original review (2026-10-28)

2026-10-28. Scope: everything that can put noise or interference into the eight bipolar EMG channels, on
the main board (`boards/neurband_c/neurband_c.kicad_pcb`, schematic source `boards/neurband_c/gen_c_sch.py`)
and on the electrode flex (`boards/neurband_c_flex/`). **No design file was changed.** Analysis scripts are in
`sim/preorder/` (run `sim/preorder/run_all.sh`); small outputs are in `sim/preorder/out/`, plots and logs in
`sim/preorder/build/` (gitignored). Part numbers are from the fab's stock on 2026-10-28.

Labels as in `docs/science/signal_chain.md`: **C** = calculation/simulation from the actual copper, **E** =
engineering estimate, **P** = datasheet. Nothing was measured. The pass mark used throughout is **0.1 µVrms
in 20-850 Hz**, referred to the input. For scale, the ADS1298 alone gives 1.2 µVrms at 4 kSPS.

## Summary

| # | Severity | Finding | Key number | Minimal fix |
|---|---|---|---|---|
| M1 | **MUST** | I2C_SCL (B.Cu), I2C_SDA (In2) and IMU_INT (B.Cu) run next to, or 0.1 mm under, CH1 and CH4 electrode traces | Cm 84 + 73 fF onto IN1P (ADS side), 25 fF onto E1P, 89/28 fF onto E4P/E4N. Gives **4.1 µVrms on CH1, 1.3 µVrms on CH4** (1 MΩ‖10 nF contacts); 36/12 µVrms with 1 MΩ‖1 nF. Coherent lines at 208 Hz × k | Reroute the three nets off In2/B.Cu across the electrode corridor (details in §1.4). Gate: < 2 fF from any active digital net to any electrode net |
| M2 | **MUST** | BIAS_E (8 skin pads) goes straight to ADS **RLDIN, pin 62**, with no series resistance | ESD into a bias pad is limited only by the source: 6 A at 2 kV and 24 A at 8 kV (IEC 330 Ω). The pin's HBM-2 kV level is 1.33 A. The pin also sees the full RF on the 170 mm bias bus | Connect RLDIN to **RLDOUT (adjacent pin 63)** instead of BIAS_E. That puts it behind R2 (100 kΩ), adds no parts and keeps the RLD_MEAS diagnostic |
| S1 | SHOULD | Electrode-input ESD margin with 4.7 kΩ | An 8 kV contact on a pad drives ≤ 1.6 A into the pin (> 1.33 A HBM-2 kV level) | **RN1-RN4 → 10 kΩ, 4D03WGJ0103T5E (C29718, basic, same footprint)**: 0.77 A at 8 kV. Cost: noise 1.39 → 1.44 µVrms; no CMRR, droop or loop-margin cost |
| S2 | SHOULD | Pour fragments on In2/B.Cu are poorly stitched around the ADS, arrays and J1 fan-out | Largest via-free radius **6.2 mm** at (18.3, 16.7). Fragments with 1-3 vias reach 6-17 mm from their nearest tie, against λ/20 ≈ 3.5 mm at 2.44 GHz | Add GND vias or delete the slivers (§2.3). Rule: no pour point > 3 mm from a GND via |
| S3 | SHOULD | RF/ESD shunt on the bias net at the board entry | Bias bus ≈ 140 pF distributed on the flex, but nothing at J1 | **22 pF C0G, 0402CG220J500NT (C1555, basic)**, BIAS_E to GND at R2's BIAS_E pad. Costs < 0.5° of RLD phase margin (100 pF costs 1.8°, 1 nF costs 13°) |
| S4 | SHOULD | ADS support parts | AVDD1/AVSS1 (pins 54/53, charge pump) has only 100 nF, 2.8 mm away. VREFP 10 µF 0402 6.3 V is ≈ 5 µF at 2.4 V | Add **1 µF (C52923)** at pins 54/53. **C6 (VREFP) → 10 µF 0603 10 V, CL10A106KP8NNNC (C19702, basic)** |
| S5 | SHOULD (firmware) | SPI frame read starts in software after DRDY, so its timing jitters with BLE events | Radio-correlated DRDY/CS/SCK timing has 0.2 Vrms in-band content. It is harmless now (no coupling) but sets up die-internal coupling | Trigger SPIM from DRDY in hardware (GPIOTE → PPI → SPIM START). Disable IMU INT1 until M1 is done |
| N1 | NICE | No RFI caps at the ADS inputs | On-chip 3 MHz filter plus 4.7 kΩ leaves ≤ 15 µV of RF at the PGA even with 1 V at J1, so rectification is negligible (§4) | Optional 10 pF C0G CM cap per input at the ADS pins (C32949 basic, or 22 pF 4x0402 array C576614). Costs +11 % CM→DM and −3° PM. Fit only if a radio-on test fails |
| N2 | NICE | Shared XC6206; AVDD RC filter with derated caps | PSRR path ≤ 0.1 µV. The worst q4 path (internal RLDREF) is now cut ≈ 52 dB by the external RLDREF | No ferrite (it resonates), no larger RC. Separate LDO (TPS7A2033, C2862740) only if the radio-on/off test fails |
| N3 | NICE | X5R microphonics on VCAP1/VREFP while worn; reference noise multiplies electrode DC offsets | With a 100 mV offset, 1 ppm of VREF disturbance is 0.1 µV | Tap test on the bench. If it fails, VCAP1 → 22 µF tantalum A-case (C11366, extended) |
| N4 | NICE | Flex: 2 layers are adequate | External 50 Hz field on pod 8's free links: 0.02-0.12 µV DM at 10 V/m (link on skin / lifted); 0.2-1.2 µV at 100 V/m (§7). Skin-side crosstalk −54…−68 dB | No 4-layer flex and no driven shield. Keep links on the skin. The pod under the antenna gets antenna tuning (§7.5) |
| N5 | NICE (firmware) | Dry-gold DC offsets vs gain 6 | ±400 mV range. The PGA CM window stays legal up to 300 mV, so headroom is set by full scale, not CM | Per-channel fallback to gain 4 (±600 mV) when \|DC\| > 300 mV. Lead-off off while recording; use AC lead-off at 1 kHz (4 kSPS) |
| — | no action | In1 plane, ground drops, clock/aliasing, START/PWDN/MOSI, LED, crystal, RF feed, battery leads, magnetic pickup, charge pads, button, P/N capacitance mismatch | Each ≤ 0.04 µV, or static while recording (§2, §8) | — |

**Bottom line:** two cheap but real layout/schematic defects (M1, M2) must be fixed before ordering. The
rest is insurance worth a few parts (S1-S4) or a firmware change (S5). The supply, ground plane, flex layer
count and RF rectification do **not** justify extra hardware on the numbers.

## Method

- **Geometry.** `sim/preorder/pcbgeom.py` parses the board file directly, with no SWIG. `coupling.py` samples
  every electrode-net copper item (both sides of RN1-RN4), BIAS_E, RLDOUT, RLDINV and RLDREF every 25 µm.
  For each sample it finds the nearest copper of every other net:
  - **Same layer:** edge gap.
  - **In2 ↔ B.Cu** (0.1 mm FR-4): lateral offset for parallel runs, plus lumped crossings.
  - **F.Cu ↔ In2:** shielded by the solid In1, so ignored.

  Whether GND pour, or any third conductor, lies between a victim and an aggressor is read from the real
  filled zones.
- **Capacitance.** Per-mm values come from a 2D finite-difference solver (`fd2d.py`) on the real stack: 35 µm
  copper, 0.1/0.64/0.1 mm FR-4 (εr 4.3) and 10 µm mask. The solver was checked against the Hammerstad
  microstrip: 53.1 vs 53.2 Ω. Tables are in `out/xsec_tables.json`. Examples at 0.1 mm gap: F.Cu 24 fF/mm,
  In2 34 fF/mm. With GND pour between at a 0.3 mm gap, both fall to 0.9-2.5 fF/mm. A broadside In2/B.Cu
  overlap is 48-73 fF/mm.
- **Aggressor waveforms.** `inject.py` synthesises them from the firmware timing:
  - SPI 8 MHz reads after every 4 kSPS DRDY, with latency that grows during BLE events;
  - LSM6DSL at 208 Hz, 75 µs INT1 pulses and 140-clock 400 kHz I2C reads;
  - LED flash 50 ms every 0.5 s;
  - radio bursts of 10 mA × 2.5 ms every 7.5 ms on VBAT/+3V3/+3V3A, using the q4 ripple levels.

  The coupled voltage is `V_agg(f) · |jωCm · (Zs ‖ C_node)|`, with `Zs = R‖C_e`. Above the contact corner
  this is `V_agg · Cm/C_e`. In-band aggressor content (20-850 Hz, Vrms): I2C_SCL 0.38, I2C_SDA 0.32,
  LED 0.32, DRDY 0.20, IMU_INT 0.15, MISO 0.023, CS 0.012, SCK 0.010, +3V3 0.009, VBAT 0.003, +3V3A 0.002.
- **Cm budget.** For 0.1 µV at C_e = 10 nF, the allowed Cm is about 2.7 fF for I2C, 3 fF for the LED, 7 fF
  for IMU_INT, 100 fF for SPI clock and 400 fF for the analog rail. Divide by 10 for a 1 nF contact.
- **Extended sims.** `q5_input_options.py` adds series R, C0G CM/differential caps, a BIAS_E shunt and TVS
  capacitance to the existing `sim/afe.py` ngspice model, so q1/q2 are reproduced and extended.
  `flex_field.py` is a 2D field model of external-field pickup on the flex. `ground.py` covers plane voids,
  pour fragments and stitching.

## 1. Capacitive / inductive coupling into the electrode nets

### 1.1 Where the electrode nets run

From J1 the 16 nets drop through vias under the J1 body (y ≈ 23.1/23.8) and run on **In2 or B.Cu** to the
J1-side pads of RN1-RN4 (y 17.95-19.2). The ADS-side nets leave the arrays (y 16.15-17.4) on In2/B.Cu to vias
at y ≈ 14.5-15.2, then reach U2 pins 1-16 on F.Cu. Board-only lengths and estimated capacitance per line:

| Ch | P: F / In2 / B.Cu (mm) | N: F / In2 / B.Cu (mm) | C board P / N (pF, E) |
|---|---|---|---|
| 1 | 3.8 / 33.1 / 0 | 3.4 / 23.7 / 0 | 5.6 / 4.2 |
| 2 | 4.1 / 0 / 22.1 | 3.1 / 0 / 18.9 | 3.3 / 2.9 |
| 3 | 15.8 / 0 / 0 | 3.4 / 0 / 10.5 | 1.8 / 1.9 |
| 4 | 4.1 / 9.2 / 0 | 3.1 / 8.8 / 0 | 2.2 / 2.0 |
| 5 | 4.0 / 5.7 / 0 | 7.7 / 0 / 0 | 1.6 / 0.9 |
| 6 | 6.5 / 0 / 0 | 3.9 / 0 / 0 | 0.8 / 0.5 |
| 7 | 3.0 / 3.5 / 0 | 2.8 / 4.8 / 0 | 1.2 / 1.4 |
| 8 | 3.2 / 0 / 7.4 | 3.1 / 0 / 9.0 | 1.6 / 1.7 |

E1P takes a 33 mm detour on In2 around the ADS. P/N pairs are generally not routed as pairs: CH3 has P on
F.Cu and N on B.Cu. Board mismatch is ≤ 1.4 pF.

### 1.2 Results (full table `sim/preorder/out/inject_summary.csv`; geometry `out/coupling_pairs.csv`)

| Victim (channel) | Aggressor | Where | Cm (fF) | µVrms at 100k‖10n / 1M‖10n / 1M‖1n |
|---|---|---|---:|---|
| RN1A-R1.1 = IN1P, ADS side (CH1 P) | I2C_SCL, B.Cu, 0.1 mm below | x 25.0-25.4, y 15.1-17.0, plus offset runs | 84 | 2.9 / **3.2** / 28 |
| RN1A-R1.1 (CH1 P) | I2C_SDA, In2, 0.15 mm gap | x 25.0-25.5, y 15.1-17.1 | 73 | 2.2 / **2.3** / 21 |
| E4P (CH4 P) | IMU_INT, B.Cu below | x 13.7-16.4, y 24.1-24.4 (J1 fan-out) | 89 | 1.2 / **1.3** / 12 |
| E1P (CH1 P) | I2C_SCL, B.Cu below | x 24.7-25.4, y 18.0-19.1 | 25 | 0.88 / **0.95** / 8.5 |
| E4N (CH4 N) | IMU_INT, B.Cu below | x 14.1-15.4, y 24.1 | 28 | 0.37 / **0.40** / 3.6 |
| E1P (CH1 P) | VBAT, In2, 0.13 mm gap | 12 mm along the E1P detour, x 14.8-16.2, y 12-13 | 236 | 0.05 / 0.06 / 0.45 |
| RN4C-R3.1 (CH8 P, ADS side) | VBAT, In2 above B.Cu | 3 crossings | 128 | 0.03 / 0.03 / 0.24 |
| E1P | +3V3A crossings | — | 78 | 0.01 / 0.02 / 0.13 |
| BIAS_E | IMU_INT, B.Cu, 0.15 mm, 8.4 mm long | y ≈ 24 | 178 | < 0.001 (CM only) |
| All others | — | — | — | ≤ 0.013 / ≤ 0.013 / ≤ 0.12 |

Per channel, with no P/N cancellation assumed (1M‖10n): **CH1 4.1 µVrms, CH4 1.3 µVrms**, CH8 0.04, all
others ≤ 0.013 µVrms. The interference is a set of coherent lines at 208 Hz × k (208/416/624/832 Hz),
drifting with the IMU's own oscillator. A notch would remove it from the spectrum but not from features near
those frequencies.

Static nets were checked and have no in-band activity while recording: BUTTON, NRST, SWDIO, SWDCLK, START,
PWDN, VCHG, CHG_N and VBAT_SENSE. Their couplings (up to 134 fF BIAS_E/BUTTON, 89 fF E1P/VCHG, 44 fF
E3P/SWDCLK) only matter during a button press or a debug session; a button press is a user-marked event
anyway. MOSI is held low in RDATAC. DRDY, CS, SCK, MISO, the LED, the crystal (XC1/XC2), the RF feed and
DEC1-4 have no coupling above 0.01 fF to any electrode net.

BIAS_E, RLDOUT and RLDINV victims are about 70 dB less sensitive than an electrode trace. Charge injected
there moves the body as common mode; the RLD loop suppresses it about 5× at 200 Hz, and CM→DM conversion is
about −54 dB. RLDREF is 500 kΩ‖1 µF, below 1 Ω in band.

### 1.3 HF, aliasing and intermodulation

- **Aliasing.** The ADS modulator samples at fMOD = 512 kHz. Only content within ±850 Hz of n·512 kHz aliases
  in band; the sinc³ is unity at the images. The board clocks never get closer than 64 kHz:

  | Source | Nearest n·512 kHz | Distance |
  |---|---|---|
  | I2C 400 kHz | — | ≥ 112 kHz |
  | SPI 8 MHz | 8.192 MHz | 192 kHz |
  | SPI 3rd harmonic, 24 MHz | — | 64 kHz |
  | nRF crystal 32 MHz | — | 256 kHz |

  Sinc³ rejection at those offsets is > 100 dB. The 8th SPI harmonic, 64 MHz = 125·fMOD, would alias only if
  the ADS oscillator were within ±13 ppm of nominal (its tolerance is ~0.5 %). It also lies 26 dB down the
  on-chip EMI filter and ~60 dB down the 64 kHz PGA pole.
- **Shorting by the contacts.** At MHz, the J1-side nodes are shorted to the body by C_e (10 nF is 2 Ω at
  8 MHz). The ADS-side nodes see ≈ 800 Ω (4.7 kΩ ‖ 25 pF).
- **Burst envelopes.** These are what matters, and they are in band by construction. They are treated
  linearly in §1.2.
- **SPI bursts.** They are locked to DRDY, so their 4 kHz lines fall on sinc³ nulls or alias to DC, giving a
  fixed offset. Only radio-induced *timing jitter* moves them (S5).
- **Intermodulation.** Mixing in the PGA needs mV-level HF at the PGA input; the largest digital HF at the
  ADS-side pins is ~mV before the internal 5 kΩ/10 pF, so this is negligible.

### 1.4 Fix for M1 (layout)

1. **I2C_SCL and I2C_SDA.** In the right-edge column x ≈ 24.5-26, y ≈ 13.5-20, move them to **F.Cu**. F.Cu is
   shielded from In2/B.Cu by the solid In1. Alternatively, move them ≥ 0.5 mm laterally from RN1A-R1.1, E1P
   and E1N, with GND pour between on their own layer *and* GND pour on the adjacent layer. The electrode
   traces there (RN1A-R1.1, E1P on In2) must have **solid B.Cu GND directly under them**.
2. **IMU_INT.** Take it off the B.Cu run along y ≈ 24.4 under the J1 fan-out (x 8.6-18.4). Route it on F.Cu,
   or on In2/B.Cu outside the electrode corridor. Doing the same for the parallel BIAS_E run is optional (CM
   only).
3. **Corridor rule for the layout owner.** Between J1 and U2 (x 9-26, y 13-25), electrode nets may use In2 or
   B.Cu. The other of those two layers must then be GND pour in projection, ±0.3 mm. No digital net may cross
   the corridor on In2 or B.Cu; cross on F.Cu, where In1 shields it. Not required for this order, but cheap
   if the router is rerun: E1P's 33 mm In2 detour beside VBAT can be shortened.
4. **Gate.** Rerun `sim/preorder/coupling.py` and `inject.py` on the rerouted board. Every electrode net
   must be < 2 fF from I2C/IMU_INT/LED and < 5 fF from DRDY/SPI, i.e. < 0.1 µV at 1M‖10n.

**Interim firmware mitigation** (until the layout is fixed): set INT1_CTRL = 0 and read the LSM6DSL FIFO on a
timer. That removes the IMU_INT term (CH4 → 0.01 µV). The I2C term on CH1 cannot be removed in firmware: any
IMU read rate leaves a burst envelope in band.

## 2. Ground

### 2.1 Planes

**C (`out/ground_summary.json`).** In1 is one filled plane with no tracks; it covers 89 % of the 12 × 12 mm
ADS area (the rest is via antipads). No analog track runs over an In1 void other than its own via antipad,
≈ 0.7 mm per via. The only large voids are intentional: the antenna keepout and the Nordic matching keepout
(2.0-6.35 × 4.8-6.85). Merged antipads form small slots, e.g. 1.5 mm² at (15.9-17.9, 19.5-21.1) in the J1
fan-out, with nothing routed across them on F.Cu. **No action.**

### 2.2 Return paths and drops

**E/C.**

- **Battery/LDO loop.** The battery return enters at J2 GND (26.9, 25.6). The LDO is U3 at (8.6, 19.0) and the
  nRF U1 at (9, 5.7), so the DC/LF radio return (10-15 mA bursts) flows nRF → LDO → battery along the left
  and bottom of In1, below the RN arrays and J1.
- **Plane resistance.** 35 µm copper is 0.49 mΩ/sq. Between two 0.4 mm contacts 18 mm apart that is
  ≈ (Rs/π)·ln(d/a) ≈ 0.7 mΩ, so **~7 µV at 10 mA** between the J2 corner and the LDO.
- **Drops near the ADS.** Between the RLDREF filter ground (C32/R13 at x ≈ 10, y ≈ 12, beside the nRF-LDO
  path) and the ADS AVSS pins (x 14.5), the drop is < 1 µV. All of it is common mode, either on the body
  reference (RLDREF) or on AVSS. After −54 dB CM→DM it is **< 0.01 µV**.
- **AVSS pins.** All 16 AVSS/DGND pins of U2 have a GND via within 0.9-1.8 mm; 17 GND vias lie within 7 mm of
  the ADS.
- **Flex ground.** The flex GND (J1 pins 1/20) sits near the bottom-edge return path. A 10 µV drop on the
  hatch couples to the traces through ~10 pF against 10 nF, giving 0.01 µV.
- **Verdict.** Ground drops are not a noise source.

### 2.3 Stitching

**C.** There are 63 GND vias and one GND through-hole pad. The pour fragments with few ties are:

| Layer | Fragment bbox (mm) | Area mm² | GND vias | Farthest point from a tie |
|---|---|---:|---:|---:|
| B.Cu | (0.3-23.2, 2.5-26.7), long sliver along the left/bottom | 52.6 | 11 | **17.1 mm** |
| B.Cu | (2.1-10.9, 0.3-9.0), under the nRF/RF area | 25.5 | **1** | 9.4 mm |
| B.Cu | (10.9-17.4, 18.3-24.0), under the J1/RN fan-out | 10.0 | **1** | 5.6 mm |
| In2 | (8.2-16.6, 0.3-24.0) | 69.4 | 10 | 9.0 mm |
| In2 | (16.8-25.2, 6.3-15.0), under the ADS | 26.2 | 3 | 7.3 mm |
| In2 | (5.65-28.4, full height), main | 241.8 | 28 | 9.2 mm |
| F.Cu | main | 306.3 | 54 | 6.2 mm |

The largest via-free circles are **6.2 mm** at (18.3, 16.7) between RN2 and RN3, 5.7 mm at (14.2, 26.6) under
J1, 4.7 mm at (21.3, 16.1) and (15.5, 15.5), and 4.4 mm at (19.8, 13.5) below the ADS. Electrostatically,
for EMG, one tie is enough. At 2.44 GHz, however, a 9-17 mm unstitched sliver is a λ/4-class resonator
(λ/4 ≈ 15-17 mm in FR-4). These slivers sit around the electrode traces and the antenna counterpoise. **S2:**

- Add GND vias so that no pour point is more than 3 mm from one: 4-6 vias on the B.Cu sliver, 2 on the
  under-nRF B.Cu fragment, 1-2 on the J1/RN B.Cu fragment, 2 on the In2 fragment under the ADS (around
  (19.8, 13.5) and (21.3, 16.1)), and one at (18.3, 16.7) if the array fan-out leaves room.
- Or remove fragments that cannot be stitched (raise the zone min-width / island-removal threshold).
- **0.30/0.45 mm vias; no new drill class.**

## 3. ADS1298 support parts vs SBAS459K

| Pin(s) | Datasheet (pin table, Fig. 106, §11) | Board | Verdict |
|---|---|---|---|
| AVDD 19/21/22 | 1 µF + 0.1 µF, close | C7 1 µF at 1.85 mm, C8 100 nF at 2.2 mm | OK |
| AVDD1 54 / AVSS1 53 (charge pump, fCLK transients); AVDD 56/59 | 1 µF + 0.1 µF; star AVDD1/AVSS1 to AVDD/AVSS | C9 100 nF only: 1.45 mm from pin 59, ~2.8 mm from pin 54. The RC bulk C28 is 9.4 mm away at R5 | **S4: add 1 µF 0402 (C52923, basic)** between pins 54 and 53, as close as the VCAP3 cap allows |
| DVDD 48/50 | 1 µF + 0.1 µF | C10 1 µF at 1.5 mm, C11 100 nF at 2.4 mm | OK |
| VREFP 24 / VREFN 25 | 10 µF + 0.1 µF; VREFN to AVSS | C1 100 nF at 1.6 mm; **C6 10 µF 0402 6.3 V X5R (C15525)** at 3.0 mm | 10 µF 0402 6.3 V at 2.4 V keeps ≈ 40-55 % (**E**; the maker's curve was not retrievable), i.e. ≈ 5 µF. **S4: C6 → CL10A106KP8NNNC 10 µF 0603 10 V (C19702, basic)**, or CL10A106MA8NRNC 25 V (C96446, basic) |
| VCAP1 28 | 22 µF to AVSS; C0G/tantalum if vibration | C5 22 µF 0603 6.3 V X5R (C59461, basic) at 3.2 mm | VCAP1 sits at ~1.1-1.5 V (only the ≥ 1.1 V power-up threshold is given), so ≈ 60-70 % remains, ≈ 14 µF (**E**). Adequate. Piezo noise is the real question → N3 |
| VCAP2 30, VCAP4 26 | 1 µF each | C4/C2 1 µF at 1.6 mm | OK |
| VCAP3 55 (AVDD + 1.9 V ≈ 5.2 V) | 1 µF | C3 1 µF CL05A105KA5NQNC, **25 V** | OK. Keep ≥ 10 V parts here |
| RLDOUT 63 / RLDINV 61 | external Rf‖Cf | R1 1 MΩ and C12 4.7 nF at 1.8-2.8 mm | OK |
| RLDIN 62 | mux input, optional | **On BIAS_E, no series R** | **M2** |
| RLDREF 60 | AVDD/2 when external | R12/R13 1 MΩ + C32 1 µF at 3.9-5 mm; CONFIG3 = 0xC4 | OK. 0.32 Hz pole, 52 dB at 133 Hz |
| WCT 64, NC 27/29, CLK 37 | open | open; CLKSEL high, CLK_EN = 0 | OK |
| TESTP/N 17/18 | unused → AVDD | +3V3A | OK |
| GPIO1-4, DAISY_IN, RESV1 | low | GND | OK (GPIOs stay inputs in firmware) |
| PWDN/RESET | — | shared net, 100 kΩ pull-down | OK (documented) |

**AVDD filter with real capacitance.** C28 (10 µF 0402 6.3 V) at 3.27 V keeps ≈ 30-40 %. With C7 and the
100 nF parts, the effective C is ≈ 4.5 µF, so the corner is ≈ 3.5 kHz rather than the nominal 1.6 kHz. That
changes nothing in band, because neither corner touches the 133 Hz envelope (§5). Moving C28 to 0603 (C19702)
is optional. Per Fig. 106, the bulk would preferably sit at the AVDD pins rather than at R5; that is NICE
only.

## 4. RF into the AFE

### 4.1 Field and coupling

**E**, ±10 dB; no EM solver was available.

- **TX power.** The firmware does not set it, so it runs at 0 dBm. +4 dBm (2.5 mW) is the worst case.
- **Field.** The far-field formula gives E ≈ √(30·P·G)/r ≈ 15 V/m at r = λ/2π = 20 mm. A few mm from the
  IFA arm, in the reactive near field, it is ~100-300 V/m. The feed sees ≈ 0.5 Vpk into 50 Ω, and the open
  end of the arm a few Vpk.
- **The pod under the antenna.** One pod's GND hatch, its two signal traces, its bias pad and the bias bus lie
  about 1.8 mm below the board underside, directly under the radiator. The hatch is tied to GND only through
  ≥ 20 mm of flex, so the flex is part of the antenna's ground structure (see `docs/science/antenna_sim.md`,
  which finds the RF-opaque hatch screening the traces).
- **RF on the electrode traces at J1.** Taken here as an upper-range **30-300 mVpk, mostly common mode**.

### 4.2 Attenuation along the input chain

Attenuation from q3 (no added caps):

| Point | CM | DM |
|---|---|---|
| Die pin | −37 to −55 dB | −31 to −49 dB |
| PGA input, after the internal 5 kΩ/10 pF | — | −77 to −105 dB |

The resulting RF levels:

| RF at J1 | At die pin / ESD diodes | At PGA input |
|---|---|---|
| 300 mV | ≤ 8 mV | ≤ 40 µV |
| 1 V (unlikely) | ≤ 28 mV | ≤ 140 µV |

Both rows are worst case.

### 4.3 Rectification

- **ESD diodes.** They are reverse-biased by ≈ 1.6 V each way. With V_rf ≪ 2·V_T·ln(…), the rectified current
  ~ I_s·(V_rf/2V_T)² is fA-level. Into 1 MΩ that is nV.
- **CMOS PGA input.** The second-order offset ~ V_rf²/(4·V_ov) ≈ (40 µV)²/0.4 V = 4 nV.
- **Envelope.** The radio burst envelope (133 Hz × k) would reach the output only through these terms, so it
  is **negligible**. Unlike a bare op-amp, the ADS1298's internal 3 MHz filter does the job.
- **The exception was RLDIN.** It sees the BIAS_E RF without the 4.7 kΩ, at roughly −10…−20 dB of the J1 level,
  i.e. ≈ 0.1-0.3 V at 1 V on the bus. That approaches diode conduction. M2 removes it.

### 4.4 Minimal filter

Numbers from `q5_input_options.py`; outputs `out/q5_*.csv`.

| Option | RF benefit | CM→DM at 50 Hz (battery adverse, 1M‖10n, 30 % + 2 pF mismatch) | RLD PM (N8, 4.7 nF; nominal / 1 nF stress) | Noise 20-850 Hz incl. ADS (1M‖10n) | Droop at 850 Hz (1M‖1n) |
|---|---|---|---|---|---|
| As built, 4.7 kΩ | die-pin CM −37…−55 dB | 0.33 µV | 57.6° / 47.9° | 1.39 µV | −0.17 dB |
| **RN → 10 kΩ (C29718)** | same at GHz (parasitic C bypasses R); halves ESD current | 0.33 | 57.6 / 47.9 | 1.44 | −0.17 |
| RN → 22 kΩ (C25729, ext) | as 10 k; ESD ÷4.7 | 0.33 | 57.5 / 47.8 | 1.55 | −0.17 |
| + 10 pF C0G CM caps at the pins, ±5 % (C32949) | die-pin CM → −91 dB | 0.37 (+11 %) | 54.9 / 46.3 | 1.39 | −0.25 |
| + 22 pF CM caps | as above | 0.41 (+23 %) | 52.1 / 44.7 | 1.39 | −0.35 |
| + 47 pF CM caps | — | 0.50 (+52 %) | — | — | — |
| 47 pF differential cap | DM only (RF is mostly CM) | 0.32 | — | 1.39 | −0.91 |
| **22 pF C0G on BIAS_E (C1555)** | RF short at 2.44 GHz at the board entry | 0.33 | ≈ 57.2 / 47.7 | — | — |
| 100 pF / 470 pF / 1 nF on BIAS_E | — | 0.33 | 55.8 / 46.9; 50.3 / 43.5; 44.7 / 39.9 | — | — |

**Recommendation.** S1 (10 kΩ arrays) and S3 (22 pF on BIAS_E) cost almost nothing and help ESD and RF on
the weakest net.

The 16 CM caps (N1) are justified only if a radio-on test shows burst-correlated lines. If footprints are
added, use C0G 10 pF ±5 % (CL05C100JB5NNNC, C32949, basic) from each ADS-side net to AVSS at the U2 pins.
The other option is 4x0402 22 pF arrays (CA0508JRNPO9BN220, C576614, extended, 2 k in stock); no 10 pF array
is in stock.

Do not fit differential caps (in-band droop, DM-only), and keep CM caps ≤ 22 pF.

## 5. Supply

- **What the radio does to the rails.** Radio pulses (10-15 mA, 1-3.75 ms, every 7.5 ms) through the XC6206's
  load regulation give 20 mVpp on +3V3 (q4 nominal; 76 mV slow model). After 10 Ω + ≈ 4.5 µF real
  capacitance, that becomes 5 mVpp / 0.9-2.7 mVrms in band on AVDD. A 133 Hz envelope passes any RC with a
  kHz corner.
- **PSRR path.** 90 dB at 50/60 Hz; Fig. 9 shows ≥ 80 dB in band. That gives 0.03-0.09 µVrms. **OK.**
- **Body-bias path (q4's dominant 0.6-7 µV term).** That term used the internal RLDREF. Rev C now has the
  external 2 × 1 MΩ + 1 µF RLDREF (0.32 Hz pole), which is ≈ 52 dB down at 133 Hz, so it drops to
  0.002-0.02 µV. **Fixed.** Its own kT/C noise is 64 nV, concentrated below 1 Hz.
- **Reference × offset path (not specified by TI).** If the internal VREF tracks AVDD with ~60 dB of
  rejection, 2.7 mV of ripple is ≈ 1 ppm of VREF. That scales the electrode DC offset: 0.1 µV at 100 mV,
  0.3 µV at 300 mV. This cannot be settled on paper. **Bench test:** apply 100 and 300 mV DC differential
  through 1 MΩ‖10 nF, radio on vs off, and look for 133 Hz × k lines that grow with offset.
- **DVDD from +3V3 directly.** Acceptable: the digital core and the internal oscillator have no in-band
  analog path.
- **Ferrite (q4).** It gives no in-band attenuation and resonates (3× spikes). **Do not fit.**
- **Larger RC.** 47 Ω buys only 5-15 % and costs 0.1 V of AVDD. **Do not.**
- **Separate LDO.** Only if the bench test fails: TPS7A2033PDBVR (C2862740, extended, 95 dB at 1 kHz,
  7 µVrms) or LP5907MFX-3.3 (C80670), from VBAT to AVDD. Keep the 10 Ω. The fab's stock has no basic
  low-noise LDO.
- **DC/DC.** The nRF stays in LDO mode (overlay `regulator-initial-mode = LDO`), so there is no switching
  noise. Keep it that way; there is no DCC inductor.

## 6. ESD into the electrodes

### 6.1 Risk

**E/C.** Worn, the band and the body move together; a discharge from body to door handle does not pass
through the inputs. The realistic stress comes when the band is off-body and floating, at donning and
handling: a finger at 2-8 kV touches a pad.

- **Model.** IEC 61000-4-2 contact, 150 pF / 330 Ω. The pad's own 16 pF to the hatch takes the first
  nanoseconds.
- **Electrode input.** Peak pin current ≤ V/(Rs + 330 Ω): 0.4 A at 2 kV and 1.6 A at 8 kV with 4.7 kΩ. The
  1.33 A of an HBM 2 kV event is the device's rated level.
- **Bias pad.** Through BIAS_E → RLDIN there is **no resistor at all** (M2).
- **Exposure.** A daily-worn prototype is touched hundreds of times. Pin damage usually shows first as raised
  leakage: the 200 pA bias becomes nA, adding mV offsets and current noise through MΩ contacts.

### 6.2 Minimal fix

M2 (RLDIN → RLDOUT, free) plus S1 (RN → 10 kΩ: 0.77 A at 8 kV, within the HBM-2 kV current, +0.05 µVrms).
22 kΩ gives 0.36 A for +0.16 µVrms, but it is an extended part. The 0603 array element also sets a
flashover limit of ~2-3 kV across its 0.8 mm gap; at that point the current is already limited by the
source plus the pad-to-hatch charge sharing.

### 6.3 TVS option (not needed for this order)

Best candidate: TPD4E05U06DQAR (C138714, extended): 4 channels, 0.5 pF, ΔC 0.05 pF, leakage 0.01 nA typ /
10 nA max. Other candidates are ESD224DQAR (C1981316) and TPD4E02B04 (C106794). Five USON-10 parts would be
needed at the J1 side (16 inputs + BIAS_E), where the fan-out has no room.

Their cost to the signal, from q5:

| Effect | Value |
|---|---|
| Added capacitance | 0.5-1 pF, ΔC 0.07-0.1 pF |
| CM→DM change | +0.4-1.1 % |
| Shot noise, 1M‖10n | 0.03 µV at 0.1 nA; 0.08 at 1 nA; 0.26 at 10 nA (max spec) |
| Shot noise, 1M‖1n | 0.11 / 0.36 / 1.14 µV at the same leakages |
| DC offset per 1 nA of leakage mismatch | 1 mV through 1 MΩ |

Acceptable for typical parts. A worst-case-leakage part would be marginal at 1 nF contacts.

## 7. The flex

**Two layers are enough. No driven shield and no 4-layer flex.**

### 7.1 Geometry

**C, `pcbgeom` on `neurband_c_flex.kicad_pcb`.**

- **Hatch coverage.** The B.Cu hatch covers 36.8-37.3 % of every pod window and **37 % of every 6.5 mm pad**
  (12.3 of 33.2 mm²). Pad-to-hatch capacitance through 25 µm PI is therefore ≈ 15-18 pF per pad, P and N
  equal to within ±1 %, about ±0.2 pF. That is good: the pads are partly shielded from outside fields.
- **Line capacitance.** Per line: ≈ 16 pF pad + 3-4 pF traces + board 1-6 pF + ADS 20 pF ≈ 40-46 pF. q2 and
  q5 were run with this range (25 pF/line + 20 pF ADS).
- **Pair lengths.** The P traces are 20 mm longer than their N partners and take a 13.9 mm B.Cu underpass on
  their own pod: E1P 88 vs E1N 69 mm, E2P 68 vs 48, E3P 48 vs 26, E4P 40 vs 18. That gives ≈ 1-1.5 pF of
  flex mismatch (**E**), which with the board makes ≤ 2.5 pF per channel. q5's 2 pF case gives 0.06 µV
  (battery typical) to 0.33 µV (battery adverse) at 1M‖10n. Inside the ≤ 2 pF guideline of
  `docs/science/simulations.md`; **no action.**
- **Bias bus.** BIAS_E carries 8 pads (≈ 130 pF) plus the bus (126 mm F.Cu, 43 mm B.Cu), ≈ 140 pF in total.
  Against q1's 20 pF that costs ≈ 2° of RLD margin (q5: 100 pF → −1.8°). It is still ≥ 55°/46° (nominal /
  1 nF stress) with N = 8 and 4.7 nF. **OK.**

### 7.2 External 50 Hz field

**C, `flex_field.py`, `out/flex_field.json`.**

The capture width of a 0.1 mm trace on a free link lying on the skin is 0.19 mm: the skin shields it from
below and from the sides. Lifted 0.65 mm off the skin it grows to ~1.0 mm. Under a pod's hatch (pod lifted 0.65 mm) it is 0.30 mm for P and 0.47 mm for N, averaged over the hatch
position (range 0.12-0.46 mm for P). So the hatch cuts capture 2-3× compared with an unshielded lifted
trace, but leaves some P/N asymmetry.

The worst traces are pod 8's, which cross 4 free links, about 48 mm. Pickup through |Zs| = 303 kΩ at 50 Hz:

| Field at the wrist | Link on skin | Link lifted 0.65 mm |
|---|---|---|
| 10 V/m (typical room) | per trace 0.075 µV, **DM ≈ 0.02 µV** | per trace 0.41 µV, DM ≈ 0.12 µV |
| 100 V/m (wrist on a mains cord or power strip) | per trace 0.75 µV, DM ≈ 0.23 µV | per trace 4.0 µV, DM ≈ 1.2 µV |

The same 21 mm of pod 8 traces under the hatches of pods 5-7 add 0.05 µV DM at 10 V/m and 0.47 µV at
100 V/m.

This is the same order as the residual through the body common mode: q2 gives 0.07-0.8 µV for battery
operation with N8. It is well below the 3 µV mains gate, and it can be notched.

### 7.3 Skin side of the traces

The F.Cu traces are skin-facing behind 25 µm of coverlay: 0.19 pF/mm when in contact, ~0.02 pF/mm on a pod,
where the flex floats ~0.65 mm above the skin between the foam-backed pads.

- **Crosstalk.** A trace picks up the skin potential under it at ωC_ts|Zs| ≈ −68 dB (3.8 pF, 1M‖10n, 100 Hz)
  to −54 dB (1M‖1n). In practice that is 0.4-2 µV of a neighbouring pod's 1 mV burst: spatial blurring, not
  noise.
- **Common mode.** C_ts in parallel with the contact is > 800 MΩ at 50 Hz, so it is negligible.
- **Verdict.** NICE, not worth a layer swap.

### 7.4 Motion and triboelectric artefacts

**E.**

- **Mechanism.** A trace sits at body potential plus that electrode's half-cell offset. When the trace-skin
  capacitance moves (link flexing, pod lift), charge V_off·ΔC flows through the contact:
  ΔV ≈ V_off·ΔC/C_e.
- **Size.** For 100 mV, 0.5 pF and 10 nF that is ≈ 5 µV, decaying with RC (ms). Rubbing charge on the skin-side
  coverlay over a trace, at ~1 µC/m² over 1 mm², gives ~100 µV transients on 10 nF.
- **Context.** Both are smaller than the electrode-interface artefacts they ride on, and both sit below
  20 Hz.
- **Mitigations (mechanical, free).**
  - Keep the free links lying on the skin, or fixed in the strap, rather than flapping.
  - Avoid foam or strap rubbing over trace areas.
  - Keep the hatch side (B) towards the foam, as now: the hatch partly screens foam-side triboelectric
    charge.
- **What would change the conclusion.** A 4-layer flex (GND/sig/GND) would screen both sides. Only consider
  it if the bench motion test (signal_chain.md §6) fails on trace areas rather than pads.

### 7.5 The pod under the antenna

- **Which pod.** `docs/mech/mechanical_c.md` and `mech/rev_c/fit.py` put pod 3 at module X = −9, i.e. KiCad
  x ≈ 5, under the radiator. The flex frame in `docs/layout/flex_c_layout.md` (pin 1 at X = +4.75 mating
  board x = 9.25, so +x_board = −X_world) maps X_flex = −9 to board x ≈ 23, which puts **pod 4** under the
  antenna.
- **Check before ordering.** One of the two numberings is mirrored. It does not change any analog
  conclusion, only which channel sits under the IFA, but confirm it on the mechanical model.
- **RF effect.** The parallel full-wave study (`docs/science/antenna_sim.md`) models the 0.2/0.8 mm hatch as
  opaque at 2.4 GHz. Seen from the antenna, the pod's skin-side signal traces therefore lie *behind* a
  screen.
- **Keep the hatch.** That study finds cutting the hatch under the antenna costs 1.3 dB worn, because the
  near field then reaches the skin and the pads directly.
- **What the AFE sees.** The hatch carries RF ground currents (a hatch/spine/tail loop resonance near
  2.3 GHz). The traces ride on it through ~4 pF (a few Ω at 2.44 GHz), so what reaches J1 is mostly
  common mode on traces and GND together. That is consistent with the §4 conclusion: no rectification risk
  on the electrode inputs once M2 is fixed.
- **Tuning.** Tune the matching pi with the band worn, as that study and the mechanical doc already plan.

## 8. Everything else

- **Clock.** The internal 2.048 MHz oscillator is used (CLKSEL high, CLK pin open, CLK_EN = 0), so no clock
  trace leaves the chip. For aliasing see §1.3. No action.
- **START / DRDY / PWDN.** START and PWDN are static while recording. DRDY toggles at 4 kHz with a
  radio-jittered low time (0.2 Vrms in band). It has no coupling to any electrode net, so it is harmless
  now; S5 removes the jitter at its source. SCK, at 8 MHz over ≈ 14 mm, has edge length ≫ trace delay and
  needs no termination.
- **LED.** It is 0.32 Vrms in band (50 ms flash every 0.5 s while streaming) but has no electrode coupling: it
  sits at the top-left. Its 1.4 mA steps appear on +3V3 as 0.3 mV, below PSRR. No action. To be safe, make
  the streaming pattern a constant-off or a slower blink.
- **IMU.** Its supply current at 208 Hz is negligible. Its digital lines are M1.
- **Battery leads.** The J2 pads sit at the bottom-right, near J1 and the tail. Magnetic coupling from a 10 mA
  loop at 5-10 mm into a pad-to-pad loop (20 mm × 0.65 mm) gives ~2 nV in band. Mains magnetic fields of
  1 µT give ~4 nV. No action. Keep the leads twisted and away from the antenna region (already required).
- **Charge pads.** They cannot be reached while worn (1.7 mm deep window), and the firmware turns the AFE off
  on CHG_N. VCHG is static at ~0 V when not charging; its 89 fF to E1P is irrelevant. No action.
- **Button.** Static except when pressed. A press is a 3.3 V step through 134 fF into BIAS_E (CM) and ≤ 7 fF
  into E1P/E4P: a sub-µV transient on a user-marked event. No action.
- **Foam/pod.** Covered in §7.4.
- **Electrode DC offsets and range.**
  - Gain 6 gives ±400 mV differential.
  - CM headroom with AVDD = 3.27 V is `0.2 + 3|Vd| < VCM < AVDD − 0.2 − 3|Vd|`: 0.5-2.77 V at 100 mV,
    1.1-2.17 V at 300 mV, 1.4-1.87 V at 400 mV. VCM ≈ RLDREF = 1.635 V minus the mean offset of the sensed
    electrodes, so it stays legal up to full scale.
  - For dry gold, 100-300 mV fits. If |DC| > 300 mV, firmware should drop that channel to gain 4 (±600 mV;
    window 1.2-2.07 V at 500 mV) rather than clip.
  - The RLD amplifier's CM range (AVSS + 0.7 to AVDD − 0.3) contains 1.635 V.
  - Input bias current of 200 pA (1 nA at 70 °C) through 1 MΩ gives 0.2-1 mV.
  - With 10 kΩ arrays (S1), a 6 nA DC lead-off current adds only 60 µV across the resistors.
- **Lead-off.** DC current lead-off (6 nA) adds 6 mV/MΩ of offset and current noise, and polarises gold. Keep
  it **off while recording**. For periodic checks use AC lead-off at fDR/4 = 1 kHz in 4 kSPS mode: outside
  20-850 Hz and in the FIR stop band (> 62 dB from 1 kHz). Do not use it in native 2 kSPS mode, where the
  tone is 500 Hz.
- **Crosstalk between channels.** Electrode-to-electrode couplings of ≤ 0.1 pF give −84 dB or better at
  100 Hz through 1 MΩ. No action.

## 9. What to do before ordering (in order)

1. **M1:** reroute I2C_SCL, I2C_SDA and IMU_INT out of the electrode corridor (§1.4). Rerun
   `sim/preorder/coupling.py` + `inject.py` as the gate.
2. **M2:** in `gen_c_sch.py`, label U2 pin RLDIN as the RLDOUT net, i.e. `Net-(U2-RLDOUT)` instead of BIAS_E.
   Rewire on the board: pins 62 and 63 are adjacent; delete the BIAS_E stub to pin 62.
3. **S1:** RN1-RN4 → 4D03WGJ0103T5E 10 kΩ (C29718, basic). This is a BOM-only change.
4. **S3:** add 22 pF C0G (C1555) BIAS_E → GND at R2's BIAS_E pad.
5. **S4:** add 1 µF (C52923) at AVDD1/AVSS1 pins 54/53. C6 → 10 µF 0603 (C19702).
6. **S2:** add GND stitching vias, or delete unstitched slivers (§2.3).
7. **Firmware:**
   - (S5) hardware-triggered SPI read;
   - INT1 off / IMU FIFO polling;
   - lead-off off while recording, AC at 1 kHz for checks;
   - gain-4 fallback for large offsets.
8. **Bench, before skin.** In addition to the `signal_chain.md` §6 gates:
   - radio on/off with 100/300 mV DC offsets applied (§5);
   - a tap test for VCAP1/VREFP microphonics (N3);
   - an RF match measurement with the band worn (§7.5).

## Limits

- The coupling model is 2.5D: per-length 2D capacitances integrated along the real copper, with crossings
  lumped. Expect ±30 % on individual Cm values. The *ranking*, and the factor of > 30 between the M1 pairs
  and everything else, is robust.
- Aggressor waveforms come from the firmware as written. Radio-latency and battery-ESR numbers are **E**.
- RF levels in §4 are order-of-magnitude **E**: no EM solver.
- DC-bias derating is **E**: the maker's curves were not retrievable.
- Nothing here is a measurement.
