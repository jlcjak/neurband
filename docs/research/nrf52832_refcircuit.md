# nRF52832-QFAA (QFN48 6x6) reference circuitry, for a chip-down schematic

Compiled 2026-10-26. Values are taken only from Nordic sources. Where something could not be confirmed from an official source, the text says so.

## Sources

| Tag | Source | Notes |
|---|---|---|
| [RC] | http://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/ref_circuitry.html (redirect target of https://docs.nordicsemi.com/bundle/ps_nrf52832/page/ref_circuitry.html) | Current online PS, read with WebFetch. Contains the BOM tables only. The schematic images and the PCB guidelines text were not available through the fetch. |
| [PIN] | http://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/pin.html | Current online PS, QFN48 pin table. |
| [CLK] | http://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/clock.html | Current online PS, HFXO/LFXO tables. |
| [PWR] | http://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/power.html | Current online PS, LDO and DC/DC text. |
| [PS10] | nRF52832 Product Specification v1.0 (Nordic, 2016-02-17), PDF mirrored at https://cdn.sparkfun.com/datasheets/Wireless/Bluetooth/nRF52832_PS_v1.0.pdf. Local copy: `docs/datasheets/nrf52832_ps_v1.0.pdf` | Official Nordic PDF. Pin table on pp.13-15, HFXO on pp.99 and 105, reference circuitry and PCB guidelines on pp.539-543. **The pin connections below come from the schematic figures (Fig. 167/168) in this PDF.** |
| [DZ-DCC] | https://devzone.nordicsemi.com/f/nordic-q-a/59028/routing-gpio-over-unused-dcc-pin | Nordic staff answer (run_ar, marked verified). |
| [DZ-DEC2] | https://devzone.nordicsemi.com/f/nordic-q-a/23226/grounding-of-dec2-pin-on-nrf52832 | Nordic staff answer (Sigurd). |
| [DZ-RST] | https://devzone.nordicsemi.com/f/nordic-q-a/72848/nordic-nrf52832---nreset-pull-up | Nordic staff answer (Kenneth). |
| [KICAD] | `$KICAD_ROOT/share/kicad/symbols/MCU_Nordic.kicad_symdir/nRF52832-QFxx.kicad_sym` | Stock KiCad symbol. |

**What I could not get:** the v1.8 and v1.9 PDFs and the reference-layout zip. Every route I tried returned HTTP 403 from Cloudflare: docs-be.nordicsemi.com, infocenter.nordicsemi.com/pdf, nordicsemi.com downloads and Mouser. The existing file `docs/datasheets/nrf52832_ps.pdf` (5.6 kB) is a Cloudflare "Just a moment..." HTML page, not a PDF. I cross-checked the current online BOM [RC] against the v1.0 PDF [PS10]. **All component values match.** The only differences are listed in section 2.4.

---

## 1. QFN48 pinout (top view, counter-clockwise from pin 1)

Source: [PIN] (current) and [PS10] Table 2, pp.13-15. The two agree on every pin.

| Pin | Name (PS) | Type | Function / note |
|---|---|---|---|
| 1 | DEC1 | Power | 0.9 V regulator digital supply decoupling |
| 2 | P0.00 / XL1 | Digital I/O / Analog in | GPIO; 32.768 kHz crystal (LFXO) |
| 3 | P0.01 / XL2 | Digital I/O / Analog in | GPIO; 32.768 kHz crystal (LFXO) |
| 4 | P0.02 / AIN0 | Digital I/O / Analog in | GPIO; SAADC/COMP/LPCOMP input |
| 5 | P0.03 / AIN1 | Digital I/O / Analog in | GPIO; SAADC/COMP/LPCOMP input |
| 6 | P0.04 / AIN2 | Digital I/O / Analog in | GPIO; SAADC/COMP/LPCOMP input |
| 7 | P0.05 / AIN3 | Digital I/O / Analog in | GPIO; SAADC/COMP/LPCOMP input |
| 8 | P0.06 | Digital I/O | GPIO |
| 9 | P0.07 | Digital I/O | GPIO |
| 10 | P0.08 | Digital I/O | GPIO |
| 11 | NFC1 / P0.09 | NFC in / Digital I/O | NFC antenna, or GPIO (factory default is NFC; reconfigure via UICR) |
| 12 | NFC2 / P0.10 | NFC in / Digital I/O | NFC antenna, or GPIO (factory default is NFC; reconfigure via UICR) |
| 13 | VDD | Power | Power supply |
| 14 | P0.11 | Digital I/O | GPIO |
| 15 | P0.12 | Digital I/O | GPIO |
| 16 | P0.13 | Digital I/O | GPIO |
| 17 | P0.14 / TRACEDATA[3] | Digital I/O | GPIO; trace port output |
| 18 | P0.15 / TRACEDATA[2] | Digital I/O | GPIO; trace port output |
| 19 | P0.16 / TRACEDATA[1] | Digital I/O | GPIO; trace port output |
| 20 | P0.17 | Digital I/O | GPIO |
| 21 | P0.18 / TRACEDATA[0] / SWO | Digital I/O | GPIO; Serial Wire Output; trace port output |
| 22 | P0.19 | Digital I/O | GPIO |
| 23 | P0.20 / TRACECLK | Digital I/O | GPIO; trace port clock output |
| 24 | P0.21 / nRESET | Digital I/O | GPIO; "Configurable as pin reset" |
| 25 | SWDCLK | Digital input | SWD clock (internal pull-down) |
| 26 | SWDIO | Digital I/O | SWD I/O (internal pull-up) |
| 27 | P0.22 | Digital I/O | GPIO (near radio, see note) |
| 28 | P0.23 | Digital I/O | GPIO (near radio) |
| 29 | P0.24 | Digital I/O | GPIO (near radio) |
| 30 | ANT | RF | Single-ended radio antenna connection |
| 31 | VSS | Power | Ground (radio supply) |
| 32 | DEC2 | Power | 1.3 V regulator supply decoupling (radio supply) |
| 33 | DEC3 | Power | Power supply decoupling |
| 34 | XC1 | Analog in | 32 MHz crystal |
| 35 | XC2 | Analog in | 32 MHz crystal |
| 36 | VDD | Power | Power supply |
| 37 | P0.25 | Digital I/O | GPIO (near radio) |
| 38 | P0.26 | Digital I/O | GPIO (near radio) |
| 39 | P0.27 | Digital I/O | GPIO (near radio) |
| 40 | P0.28 / AIN4 | Digital I/O / Analog in | GPIO (near radio); SAADC input |
| 41 | P0.29 / AIN5 | Digital I/O / Analog in | GPIO (near radio); SAADC input |
| 42 | P0.30 / AIN6 | Digital I/O / Analog in | GPIO (near radio); SAADC input |
| 43 | P0.31 / AIN7 | Digital I/O / Analog in | GPIO (near radio); SAADC input |
| 44 | NC | - | No connect. Leave unconnected. |
| 45 | VSS | Power | Ground |
| 46 | DEC4 | Power | 1.3 V regulator supply decoupling. Input from DC/DC, output from 1.3 V LDO. |
| 47 | DCC | Power | DC/DC regulator output |
| 48 | VDD | Power | Power supply |
| EP (49) | VSS | Power | "Exposed die pad must be connected to ground (VSS) for proper device operation." |

**GPIO near the radio** ([PS10] §20.2.1, Table 23, p.109): P0.22-P0.31 (pins 27-29, 37-43) are "Low drive, low frequency I/O only." Do not put the ADS1298 SPI clock or data, or any other fast or high-drive signal, on these pins.

### KiCad symbol cross-check ([KICAD], `nRF52832-QFxx`)

Footprint field: `Package_DFN_QFN:QFN-48-1EP_6x6mm_P0.4mm_EP4.6x4.6mm`. This matches [PS10] Table 126: D/E 6.0 mm, e 0.4 mm, D2/E2 4.60 mm nom (4.50-4.70).

Pin numbers map to the same functions as the PS on all 49 pads. **There are no functional mismatches.** The cosmetic and ERC-relevant differences are:

| Pin | PS name | KiCad name | Comment |
|---|---|---|---|
| 17, 18, 19 | P0.14/TRACEDATA[3], P0.15/TRACEDATA[2], P0.16/TRACEDATA[1] | P0.14, P0.15, P0.16 | KiCad omits the trace alternates. |
| 21 | P0.18/TRACEDATA[0]/SWO | P0.18/SWO | Trace alternate omitted. |
| 23 | P0.20/TRACECLK | P0.20 | Trace alternate omitted. |
| 24 | P0.21/nRESET | P0.21/~{RESET} | Same function, different notation. |
| 36, 48 | VDD | VDD (hidden, passive) | Stacked under the visible pin 13 (power_in). |
| 45, 49 (EP) | VSS | VSS (hidden, passive) | Stacked under the visible pin 31 (power_in). |
| 44 | NC | NC (hidden, no_connect) | OK. |
| 47 | DCC | DCC (power_out, visible) | In the LDO-only build, put a no-connect flag on it. |

Because of the stacking you cannot draw a separate decoupling cap on each VDD pin in the schematic. They all land on one VDD net. Record the per-pin cap assignment (C5 on pin 13, C8 on pin 36, C9 on pin 48) as a schematic note or in the layout placement rules. The same applies to C3: in the schematic it goes to GND, but in layout it must ground through the VSS pin 31 pad (see section 4).

---

## 2. Reference BOM and connections

Designators follow Nordic's. BOM values come from [RC] (current) and [PS10] Table 139 (LDO) / Table 140 (DC/DC); the two are identical except for the notes in 2.4. Pin connections come from [PS10] Figures 167 and 168, read from the vector schematic.

### 2.1 Config A: internal LDO only, no 32.768 kHz crystal

This is Nordic's "QFAA QFN48 with internal LDO setup". In Nordic's schematic, X2, C11 and C12 sit inside a dashed box labelled **"Optional"** ([PS10] Fig. 167; [RC] also states X2 is marked Optional). Omitting them gives the build without a 32.768 kHz crystal.

| Ref | Value | Description (verbatim from BOM) | Pkg | Connection (from Fig. 167) |
|---|---|---|---|---|
| U1 | nRF52832-QFAA | Multi-protocol BLE, ANT, 2.4 GHz SoC ([RC] lists "nRF52832-QFAA and nRF52832-QFAB") | QFN-48 | - |
| C1 | 12 pF | Capacitor, NP0, ±2% | 0402 | XC1 (pin 34) to GND |
| C2 | 12 pF | Capacitor, NP0, ±2% | 0402 | XC2 (pin 35) to GND |
| X1 | 32 MHz | XTAL SMD 2016, 32 MHz, Cl=8 pF, total tol. ±40 ppm | XTAL_2016 (2.0x1.6 mm) | Between XC1 (34) and XC2 (35) |
| C3 | 0.8 pF | Capacitor, NP0, ±5% | 0402 | Shunt: ANT (pin 30) node to **VSS pin 31** |
| L1 | 3.9 nH | High frequency chip inductor ±5% | 0402 | Series: ANT node (pin 30 / C3) to "RF" (50 ohm antenna feed) |
| C4 | 100 nF | Capacitor, X7R, ±10% | 0402 | DEC1 (pin 1) to GND |
| C5 | 100 nF | Capacitor, X7R, ±10% | 0402 | VDD pin 13 to GND |
| C8 | 100 nF | Capacitor, X7R, ±10% | 0402 | VDD pin 36 to GND |
| C9 | 4.7 µF | Capacitor, X5R, ±10% | 0603 | VDD pin 48 to GND (bulk) |
| C6 | N.C. | Not mounted | 0402 | DEC2 (pin 32) to GND, **do not populate** |
| C7 | 100 pF | Capacitor, NP0, ±5% | 0402 | DEC3 (pin 33) to GND |
| C10 | 1.0 µF | Capacitor, X7R, ±10% | 0603 | DEC4 (pin 46) to GND (same node as VSS pin 45) |
| X2, C11, C12 | (32.768 kHz, 12 pF, 12 pF) | Optional LFXO | - | **Not fitted.** P0.00 and P0.01 are free as GPIO. Use LFRC (±250 ppm after calibration, [PS10] §19.4.4) or LFSYNT. |

Pins with no external components in the reference schematic:

- **DCC (pin 47): leave unconnected** in the LDO build. In Fig. 167 it is a bare stub. Nordic staff: "There is a switch that disconnects DCC and puts it in High Impedance state when DCDC is disabled" [DZ-DCC]. Add a KiCad no-connect flag.
- **DEC2 (pin 32): leave unconnected.** C6 is N.C. Nordic staff: "For QFN-package the DEC2 pin should be left unconnected." Earlier reference designs had this cap, but testing showed the QFN does not need it; WLCSP still does [DZ-DEC2]. Keeping the 0402 footprint unpopulated is optional and matches Nordic's layout.
- **NC (pin 44):** unconnected.
- **P0.21 / nRESET (pin 24):** the reference schematic shows only a net label, with no pull-up and no cap. Pin reset only works once UICR PSELRESET[0] and PSELRESET[1] both hold 21 ([PS10] §14.1.60-61). In the SDK this is `CONFIG_GPIO_AS_PINRESET`. Internal pull-up is 13 kΩ, and an external pull-up or cap is allowed but only lengthens start-up [DZ-RST]. Route it to the SWD connector's nRESET pin.
- **SWDIO (pin 26) / SWDCLK (pin 25):** net labels only. No external resistors in the reference. "The SWDIO line has an internal pull-up resistor. The SWDCLK line has an internal pull-down resistor." ([PS10] §16.1, p.70). Route both to the SWD header, together with VDD (VTref), GND and nRESET.
- **VDD net "VDD_nRF":** 1.7-3.0-3.6 V (min-nom-max); supply rise time 0 V to 1.7 V must be ≤ 60 ms or POR may misbehave ([PS10] Table 4, p.17).
- **Exposed pad:** GND.

### 2.2 Config B: DC/DC regulator ("QFAA QFN48 with DC/DC regulator setup")

This is everything in Config A (X2, C11 and C12 are again in the "Optional" box) **plus**:

| Ref | Value | Description (verbatim) | Pkg | Connection (from Fig. 168) |
|---|---|---|---|---|
| L2 | 10 µH | Chip inductor, IDC,min = 50 mA, ±20% | 0603 | DCC (pin 47) to L2 to L3 |
| L3 | 15 nH | High frequency chip inductor ±10% | 0402 | L2 to DEC4 (pin 46) / C10 node |

The series chain is **DCC (47) - L2 10 µH - L3 15 nH - DEC4 (46)**, and C10 1.0 µF runs from DEC4 to GND. All other parts, values and connections are identical to Config A, including C6 N.C. and DEC2 left open. Firmware must set `POWER->DCDCEN = 1`. The LDO stays the default otherwise [PWR]. Nordic: "Two additional external passive components are required to use the DC/DC regulator." [PWR], [PS10] §18.

A practical note, not from Nordic: if you want to keep the DC/DC option open, place L2 and L3 footprints and leave them unpopulated. With DCDCEN=0 the DCC pin is high-Z [DZ-DCC], so an unpopulated L2 is harmless. Do not enable DCDCEN without L2 and L3 fitted.

### 2.3 Config C (for reference only): DC/DC + NFC

This is Config B plus Ctune1 and Ctune2: "TBD pF, Capacitor, NP0, ±5%, 0402". "The value of C_tune1 and C_tune2 must be tuned to match the selected NFC antenna." [RC]. Not needed for neurband.

### 2.4 Differences between current online PS [RC] and PDF v1.0 [PS10]

- U1: v1.0 lists "nRF52832-QFAA"; current lists "nRF52832-QFAA and nRF52832-QFAB".
- X2 description: v1.0 says "9 pF, ±20 ppm"; current says "CI=9 pF, total tol. ±50 ppm". This does not matter here because X2 is not fitted.
- C7: the current HTML table renders the value as "100 pB" (seen in two separate fetches). This is almost certainly a typo for 100 pF. The v1.0 PDF table and the v1.0 schematic both say **100 pF**, and the description "Capacitor, NP0, ±5%" only makes sense for pF values. **Use 100 pF.**
- All other values are identical: C1/C2/C11/C12, C3, C4/C5/C8, C6, C9, C10, L1, L2, L3, X1.

---

## 3. 32 MHz crystal (HFXO) requirements and load caps

HFXO electrical spec ([PS10] §19.4.2, pp.105; the same numbers appear in the current [CLK]):

| Parameter | Symbol | Value |
|---|---|---|
| Crystal frequency | fXTAL_HFXO | 32 MHz (AT-cut, parallel resonant) |
| Frequency tolerance, BLE | fTOL_HFXO_BLE | ±40 ppm max (total) |
| Frequency tolerance, 2.4 GHz proprietary | fTOL_HFXO | ±60 ppm max |
| Load capacitance | CL_HFXO | 12 pF max |
| Shunt capacitance | C0_HFXO | 7 pF max |
| ESR | RS_HFXO_7PF / _5PF / _3PF | 60 / 80 / 100 ohm max at C0 = 7 / 5 / 3 pF |
| Drive level | PD_HFXO | 100 µW max |
| Pin input capacitance XC1, XC2 | CPIN_HFXO | 4 pF typ |
| Run current / start-up | IHFXO / tSTART_HFXO | 250 µA / 0.36 ms typ |

Nordic's reference crystal is "XTAL SMD 2016, 32 MHz, Cl=8 pF, total tol. ±40 ppm" [RC]. The PS also says: "It is recommended to use a crystal with lower than maximum load capacitance and/or shunt capacitance. A low load capacitance will reduce both start up time and current consumption." ([PS10] p.99).

**Load-cap formula** ([PS10] §19.1.1, p.99; [CLK]):

```
CL  = (C1' * C2') / (C1' + C2')
C1' = C1 + Cpcb1 + Cpin
C2' = C2 + Cpcb2 + Cpin
```

"The load capacitors C1 and C2 should have the same value." With C1 = C2 and Cpcb1 = Cpcb2 this reduces to `C1 = 2*CL - Cpin - Cpcb`.

Worked example for an 8 pF crystal with Cpin = 4 pF: C1 = C2 = 16 - 4 - Cpcb = 12 pF - Cpcb. Nordic uses **12 pF**, which assumes negligible PCB stray capacitance. With about 1 pF of stray the effective CL is about 8.5 pF, a pull of a few ppm. 12 pF NP0 ±2% is the reference value; 11 pF is the strict-math alternative if you estimate about 1-2 pF of stray. The crystal's own datasheet tolerance plus temperature and ageing must stay within ±40 ppm total for BLE.

LFXO (not fitted, for completeness): CL ≤ 12.5 pF, C0 ≤ 2 pF, ESR ≤ 100 kΩ, drive ≤ 1 µW, Cpin 4 pF; BLE tolerance ±250 ppm ([PS10] §19.4.3). Nordic's optional reference is 32.768 kHz, CL 9 pF, with 12 pF caps.

---

## 4. Layout notes

Quoted or condensed from [PS10] §53.4-53.5, pp.541-543. The current [RC] page as fetched did not include this text.

- "it is highly recommended to use the PCB layouts and component values provided by Nordic Semiconductor."
- "Especially in the case of the antenna matching circuitry (components between device pin ANT and the antenna), any changes to the layout can change the behavior, resulting in degradation of RF performance or a need to change component values. **All the reference circuits are designed for use with a 50 ohm single end antenna.**"
- "A PCB with a minimum of two layers, including a ground plane, is recommended... On PCBs with more than two layers, put a **keep-out area on the inner layers directly below the antenna matching circuitry** ... to reduce the stray capacitances that influence RF performance."
- "**Pay attention to how the capacitor C3 is grounded. It is not directly connected to the ground plane, but grounded via VSS pin 31.** This is done to create additional filtering of harmonic components." In practice, C3's ground pad is a short top-layer trace to the pin 31 pad, with no via straight to the plane at C3.
- "The DC supply voltage should be decoupled as close as possible to the VDD pins with high performance RF capacitors... The supply voltage for the chip should be filtered and routed separately from the supply voltages of any digital circuitry."
- "Long power supply lines on the PCB should be avoided. All device grounds, VDD connections, and VDD bypass capacitors must be connected as close as possible to the IC... For a PCB with a bottom ground plane, the best technique is to have via holes as close as possible to the VSS pads. **A minimum of one via hole should be used for each VSS pin.**"
- "Fast switching digital signals should not be routed close to the crystal or the power supply lines. Capacitive loading of fast switching digital output lines should be minimized in order to avoid radio interference."
- The reference layout (Fig. 171/172, 2-layer, LDO setup) shows a **4x4 array of 16 vias** in the exposed pad to the bottom ground plane, all components on top ("No components in bottom layer"), C3 and L1 placed immediately at the ANT pin with the RF trace leaving the chip edge, and X1 with C1/C2 tight against XC1/XC2.
- GPIO near the radio (P0.22-P0.31): low drive and low frequency only (section 1).

**Not found authoritatively:** the 50-ohm trace geometry (width, gap, stackup) for the ANT-to-antenna feed. Nordic gives it only implicitly in the reference-layout Gerbers/Altium zip, which I could not download (Cloudflare 403). Compute a 50-ohm grounded coplanar waveguide (or microstrip) for your fab's stackup, keep the run from the L1 output to the antenna or connector short, and via-stitch the coplanar ground. That last recommendation is general RF practice, not a Nordic-sourced value. The antenna itself and any antenna-side pi tuning network are outside Nordic's reference circuit, which ends at "RF" = 50 ohm.
