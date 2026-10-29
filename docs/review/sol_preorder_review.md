# neurband rev C — layout owner's preorder consult

2026-10-28. **Recommendation: hold the order for a bounded power/input-routing correction and manufacturing release clarification. Do not substitute a chip antenna merely to buy confidence. Keep the two-layer flex.** The present integrated antenna placement is an RF experiment, not something I can confidently sign off for reliable on-wrist operation.

Read-only review: no board, schematic, project, generator, layout script, BOM or fabrication manifest was edited. CLI operations that refill/save used isolated temporary copies. This report supersedes earlier blanket statements of preorder readiness where the findings below differ. In particular, clean DRC does not establish local bypass effectiveness, absence of via-in-pad, or a metal-free antenna volume.

## Evidence and interpretation

- **Measured geometry:** parsed the saved main board, including footprint transforms, tracks, vias and filled polygons; compared actual same-layer routes and adjacent L3/L4 copper projections. Coordinates below are main-board top-view KiCad coordinates, millimetres, unless explicitly identified as flex coordinates.
- **Native checks:** selected KiCad CLI reports version **10.99.0**. Saved-fill and refilled-copy DRC both give main **0 errors, 59 library-footprint-mismatch warnings, 0 unconnected, 0 schematic-parity differences**; flex **0 violations, 0 unconnected, 0 parity differences**. Complete saved filled-polygon coordinates were unchanged by refill on the copies. No stale fill was found. Some project checks, including missing-courtyard and footprint-type/filter checks, are disabled; this is not unrestricted manufacturing certification.
- **Actual outputs inspected:** generated copper, mask, paste and drill outputs; visually checked macro-complete Gerber renders, including the QFN stencil apertures and flex contact window. Existing saved copper-layer renders were also inspected. Temporary analysis included a power-only routing map that makes the remote regulator bypass topology visible.
- **Calculated/estimated:** coupling capacitances, injected voltages, bend strain and planning times are explicitly estimates, not extracted field solutions or hardware measurements. No antenna, electronic-noise, electrode, ESD or human-subject measurement was performed.
- **Availability:** the part-catalogue MCP is not installed in this review environment. All populated BOM references have MPNs and match the saved board/schematic, but current availability, basic/preferred/extended classification and prices in **the fab's stock** are unverified. Install/connect the catalogue MCP for live release checking; historical stock counts are not current reservations.

Reviewed sources include `boards/neurband_c/neurband_c.kicad_pcb`, its schematic/netlist/BOM, `boards/neurband_c/layout/`, `boards/neurband_c_flex/`, `docs/layout/main_c_layout.md`, `docs/layout/flex_c_layout.md`, `docs/mech/mechanical_c.md`, `docs/science/signal_chain.md`, `docs/science/simulations.md`, the previous reviews, and relevant `firmware_c/` settings. The older `firmware/` and `docs/review/sol_schematic_review.md` concern a different, two-ADS architecture and must not drive rev-C changes.

## 1. Analog: will it be noisy, how does it couple, and is grounding adequate?

### Direct answer

**There will be intrinsic ADC/contact noise; additional digital/RF interference is physically plausible through identified routes. Its actual amplitude is not yet known.** The dominant preventable layout issues are a remote LDO output bypass, avoidable active digital/input adjacency, unequal P/N capacitance environments, and the antenna sitting immediately above electrode/shield copper. A split ground or a blanket increase in stitching will not cure those.

The ADS1298 itself is credible for this use: TI's typical total shorted-input noise is about **1.5 µVrms at 4 kSPS, gain 6**, not a guaranteed 20–850 Hz production limit. The existing signal-chain calculation gives about **1.21 µVrms ADS-only** and **0.33 µVrms from the two 4.7 kΩ resistors** in its modeled 20–850 Hz band. With purely resistive 100 kΩ or 1 MΩ contacts on each input, its combined model is about **1.99 or 5.04 µVrms**, before motion, excess contact noise, mains and radio interference. Real dry contacts are complex impedances; their real part, not impedance magnitude alone, sets thermal noise.

### 1.1 Saved J1 → arrays → ADS routes

U2 is at **(20.2,10.1), 90°**. Its input pads form the south row, **x=16.45…23.95, y=15.7625**. RN1/RN2/RN3 are at **(23.9/20.1/16.3,18.3), 270°**; RN4 is at **(12.5,17.05), 270°**. J1 signal lands are at y=21.5925, x=9.25…18.75. The channel ordering makes the first pairs take the longest crossovers.

Summed saved track-centreline lengths, **excluding vertical via travel and the resistor body**:

| Channel | P, J1→array→ADS | N, J1→array→ADS | Difference |
|---|---:|---:|---:|
| 1 | 41.86 | 30.95 | 10.91 |
| 2 | 31.31 | 24.97 | 6.34 |
| 3 | 21.11 | 17.83 | 3.28 |
| 4 | 18.75 | 15.61 | 3.14 |
| 5 | 15.66 | 12.39 | 3.28 |
| 6 | 12.73 | 9.06 | 3.67 |
| 7 | 12.45 | 13.26 | 0.81 |
| 8 | 17.31 | 18.56 | 1.25 |

These are **not timing-skew failures**: these signals do not need RF-style length matching. They show unnecessarily different capacitance/pickup environments. For example, E3P is entirely F.Cu while E3N has 10.54 mm on B.Cu; E5N is entirely F.Cu while E5P uses In2.Cu. Post-resistor routes alone are **4.22…8.02 mm**, often with two vias. The resistor is not at the ADS pin and does not protect copper picked up downstream of it.

For scale, the documented RF microstrip model has about **0.119 pF/mm** for a 0.16 mm track over 0.10 mm dielectric. That is not an extraction for these 0.10 mm mixed-layer routes, but it explains why a 10.9 mm route imbalance can plausibly mean order-**1 pF** capacitance imbalance. Via barrels/pads and changing ground coverage also matter. Do not add meanders simply to equalize millimetres; shorten and pair the paths and match their layer/reference exposure.

### 1.2 Actual aggressor proximity

Clearances below are **copper edge-to-edge**, not centreline gaps. Parallel overlaps are projected overlaps of nearly parallel saved segments; multiple small segments should not be mistaken for independent long routes.

| Victim / aggressor | Measured geometry | Interpretation |
|---|---|---|
| RN1A→U2 IN1P / I2C_SDA | In2.Cu, **1.25 mm parallel at 0.15 mm gap**; victim x=25.35, y=15.525…16.925, SDA x=25.60 | Active digital line beside an unfiltered post-resistor input; first reroute target |
| Same IN1P / I2C_SCL | L3 victim above B.Cu SCL at x≈25.30, y=15.225…16.20; **0.0516 mm² aggregate copper-projection overlap** including transitions | Only 0.10 mm dielectric and no intervening ground; changing layer is not shielding |
| E4P / IMU_INT | In2.Cu x=13.925…15.30, y=24.375 above B.Cu INT y=24.425; **1.375 mm main parallel overlap**, **0.0738 mm² aggregate projection overlap** | Direct broadside capacitive path in connector escape field |
| E3P / SWDCLK | F.Cu, **4.50 mm parallel at 0.20 mm gap**, overlap x=12.775…17.275, y=24.125 versus 24.425 | Bad routing precedent, but SWD should be disconnected/inactive while worn; lower normal-operation priority than I2C |
| E1P / ADC_START | In2.Cu, **1.59 mm parallel at 0.395 mm gap**, several additional short near-parallel pieces; closest approach **0.271 mm** | START is normally static during streaming; transition concern, not an assumed continuous clock |
| E4P / SWDIO | In2.Cu, **1.375 mm parallel at 0.625 mm gap** | Debug-only activity should not occur on-body |

The SPI separation is better than the mixed-layer image alone suggests. Minimum same-layer input-to-SPI gaps are approximately **SCK 7.82 mm, MOSI 5.37 mm, MISO 6.74 mm, CS 4.46 mm**; DRDY's closest same-layer approach is **1.69 mm**. No close SPI/input L3–L4 copper-projection overlap was found by this geometric audit. This is not a full EM extraction, but there is no basis to call SPI the principal direct parallel-run offender. Preserve its north-side partition.

Crystal-node same-layer distances to input routing are about **9.80 mm for XC1 and 4.73 mm for XC2**. The LED control route is about **12.98 mm** away. Their stronger plausible paths are rail/ground current, radiated fields and clock-image aliasing, rather than an observed adjacent input run. The post-match antenna feed approaches input copper to about **4.08 mm** on F.Cu; the **radiator and flex electrodes** are a separate, much more serious three-dimensional proximity problem (§2).

### 1.3 Coupling magnitude: useful scale, not a predicted noise trace

For a low-frequency aggressor component, a first-order model is:

`Vvictim(f) ≈ j·2πf·Cm·Zsource(f)·Vaggressor(f) / [1 + j·2πf·Zsource(f)·Cin]`.

Differential error depends on **unequal coupling and unequal source impedances** on P and N. Equal common-mode coupling does not simply disappear when contacts differ. Use the electrode's complex impedance at the frequency in question, adding 4.7 kΩ for the post-resistor side.

- **Same-layer estimate:** for the 1.25 mm/0.15 mm-gap L3 run, use an order-of-magnitude **0.01…0.05 pF** mutual-capacitance bracket, not a precise extracted value. Nearby ground reduces coupling; ground fragmentation and fringing change it. The longer SWD run could be order **0.03…0.15 pF**, but is normally inactive.
- **Broadside estimate:** `C≈ε0·εr·A/h`, εr=4.3, h=0.10 mm, gives **0.0197 pF** for the aggregate IN1P/SCL overlap and **0.0281 pF** for E4P/IMU_INT. These are parallel-plate terms, not full capacitances: conductor width is comparable with spacing, so fringing and nearby conductors make precise extraction necessary for sign-off.
- At **133.33 Hz**, a **1 Vrms spectral component** coupled through 0.01/0.02/0.05 pF gives respectively **0.84/1.68/4.19 µVrms into 100 kΩ**, or **8.38/16.76/41.89 µVrms into 1 MΩ**, before differential cancellation and actual contact reactance. A hypothetical 0–3.3 V, 50%-duty square wave has 1.486 Vrms fundamental: 0.02 pF would give **2.49/24.9 µVrms** for those source resistances.
- That square wave is a **sensitivity example**, not a claim that SDA, INT or the RF carrier has that component. Actual I2C edge patterns, polling/interrupt cadence, ADS filtering and demodulation decide the observed spectrum. A 7.5 ms radio envelope cannot be substituted for the 2.4 GHz carrier voltage in this linear formula.
- A fast 3.3 V edge through **0.02 pF into 50 pF total input capacitance** initially gives about **1.32 mV** by charge sharing. Purely resistive 100 kΩ/1 MΩ sources give approximately **5/50 µs** recovery. This is an edge-scale illustration, not ADC-output amplitude; repetitive patterns, sampling images and nonlinearities determine in-band residue.

The 7.5 ms connection interval creates an RF/supply envelope at **133.3 Hz**, with harmonics at **266.7, 400, 533.3, 666.7 and 800 Hz**, all inside the target band. RF rectification can demodulate that envelope in input/protection junctions. Separately, interference near ADS modulator passband images can alias. Linear input-RC simulations cannot predict nonlinear rectification; the GHz lumped models in `docs/science/simulations.md` are sensitivity studies, not measured rejection guarantees.

### 1.4 Ground plane, return paths and stitching

**Keep one common ground. Do not split AGND/DGND or cut a moat under the AFE.** TI explicitly permits/recommends a common plane with analog/digital placement partitioning. The actual stack is F.Cu–0.10 mm–L2 GND–0.64 mm–L3–0.10 mm–B.Cu. L2 has **zero signal tracks**, one connected filled component, about **597.64 mm²** saved fill. Its main deliberate voids are the antenna and Nordic matching exclusions; signal-via antipads puncture it, but no cross-board split was found.

However, **L3 is five times farther from L2 in copper-centre spacing than F.Cu is** (approximately 0.675 versus 0.135 mm). Its closest conductor is B.Cu, which is routed and fragmented, not a continuous plane. In the saved geometry, B-side GND fill covers only about **41% of the E4P L3 strip projection, 49% of E4N, 44% of RN4A, and 52% of RN1A**. These percentages count zone-fill projection, not a solved return-current distribution. L2 remains a fallback reference, but broadside digital tracks on B.Cu can couple directly, and returns must redistribute around B-side slots.

Counts: **204 main through-vias, 63 GND**, plus AE1's intentional plated ground-short pad. All vias are 0.45/0.30 mm. GND-via nearest-neighbour spacing is **0.57 mm minimum, 1.52 mm median, 4.37 mm maximum**; these are nearest-neighbour statistics, not a maximum coverage radius. The seven antenna-boundary stitches at **x=6.0, y=13.4/16.2/18.2/20.2/22.2/24.2/26.2** have maximum consecutive spacing **2.8 mm**, then 2 mm. Do not add stitches inside the radiator or Nordic matching exclusion.

Saved GND zone fill has **7 F-side, 8 L3 and 11 B-side polygon components**. Every component intersects at least one GND via; I found no completely unanchored saved fill component. These are fill components, not separate ground nets: pads/traces and L2 can interconnect them. Nevertheless, some pieces have a long distance to their only direct through-via:

| Fill piece | Area / bounds | Direct via / concern | Suggested second-anchor region |
|---|---|---|---|
| B.Cu upper-left | 25.53 mm², x=2.05…10.92, y=0.30…8.96 | Only (3.725,2.8); farthest polygon boundary about **9.45 mm** away | Trial **(7.60,1.75)**, plus reassess near its lower-right branch during reroute |
| B.Cu connector field | 10.03 mm², x=10.88…17.41, y=18.29…24.02 | Only (12.475,20.2); farthest boundary about **5.73 mm** away | Trial **(16.75,23.00)** |
| F.Cu crystal-side piece | 3.84 mm², x=2.16…5.35, y=7.98…10.77 | Only (3.175,10.6) | Trial **(5.10,8.45)**, outside matching exclusion |

These trial centres passed a conservative planar obstacle/paste/keepout screen on the saved geometry, **not native DRC or RF validation of a modified board**. They are candidates for the later implementation, not promised legal sites after rerouting.

More useful than a perimeter via carpet: add short cap-ground returns and a nearby ground via at signal-layer transitions, especially I2C/INT in the connector/AFE field. A trial at **(12.565,8.505)** could shorten C13's return to about 0.526 mm. The same conservative search found **no simple extra via within ±0.875 mm** of C9/C16/C29 ground pads without conflicts; free space by changing placement/routing rather than squeeze drills between solder lands. Keep C21's mandated return through VSS31; never give it an independent plane shortcut.

At 2.4 GHz, 2 mm stitching is a reasonable local RF layout scale, not an EMG-ground requirement or an antenna-efficiency guarantee. The existing fence is not obviously underpopulated. Added ground cannot shield the radiator from an electrode physically under it without also loading the radiator.

### 1.5 Power distribution and decoupling: the most concrete electrical release defect

**U3's output capacitor C27 is electrically remote. Fix this before ordering.** U3 VOUT is **(7.4625,19.90)**; C27's supply land is **(11.12,19.10)**, only **3.744 mm away geometrically**, but there is no short local connection. VOUT heads south to **(7.15,22.5)**, around the B-side bottom route through the TP1/U5 region, up the right-hand distribution, and back through the upper rail. C27 is fed by a long top-layer stub from the upper distribution. A centreline/via graph gives order **60–70 mm** U3-to-C27 electrical route, rather than 3.7 mm; it is an approximate route metric, not a parasitic extraction.

This places substantial trace inductance/resistance between the regulator and its stability/transient capacitor. It also shares long supply sections with IMU, MCU and ADC loads. Clean net connectivity cannot validate that loop. Do not try to repair this first by adding a second analog LDO or a ferrite.

Other measured placement/path facts:

| Network | Saved evidence | Decision |
|---|---|---|
| nRF VDD | C16 supply pad→pin48 **1.59 mm straight**, C17→pin13 **2.21 mm**, C18→pin36 **2.05 mm**; C16 ground's nearest GND via **1.27 mm** away | Bring bypasses closer and keep rail→cap→pin branches local; C13's ground-via distance is also **1.43 mm** |
| ADS DVDD | C10 is **1.51 mm** from pin48; C11 **2.39 mm** from pin48 but **5.43 mm** from pin50 | Redistribute bypasses to serve both pin groups, not just north-side room |
| ADS quiet AVDD | C9 supply→pin59 **1.45 mm**, direct; C9 ground's nearest GND via **1.62 mm** away | Preserve supply link, shorten ground/return and separate reference/charge-pump paths |
| ADS charge pump | Pin54 AVDD1 **(14.5375,8.85)** has no dedicated nearby local supply bypass; C9→pin54 centreline route about **10 mm**, while C3 is the separate VCAP3 capacitor | Give AVDD1/AVSS1 a local bypass branch and star its supply feed with quiet AVDD, following TI §11; do not confuse VCAP3 with AVDD1 bypass |
| Right ADS AVDD pins | C7→pin19 **2.56 mm straight**, C8→pin19 **3.20 mm**; C28/C29 are supply-filter caps about **9 mm or more** from the nearest right AVDD pins | Move/allocate local caps to actual supply pins; bulk filter capacitors are not local bypass substitutes |
| VREFP | C1→pin24 track path about **1.91 mm**, C6→pin24 about **3.84 mm**; all F.Cu, no signal vias | Reasonable topology, improve compactness if moving right-side caps; return separately toward VREFN/AVSS23 rather than through supply-return copper |
| VCAP1 | C5→pin28 saved trace length **4.84 mm**; C5 is a 22 µF class-II ceramic | Shorten and mechanically avoid board/cell pressure; its microphonics can enter the reference system |
| Charger BAT bypass | C25 at **(2.3,2.8)** is **15.74 mm straight** from U4 BAT, approximate trace/via route **30 mm** | Move it near U4 BAT/GND instead of treating a remote VBAT reservoir as local bypass |

Actual loop area is not cap-to-pin distance squared: returns spread in planes and reroute around slots. I have not assigned fictitiously precise loop areas. The remote C27 rail, known trace lengths, layer spacing and missing local charge-pump bypass are sufficient to justify correction.

The battery feed from J2 **(23.9,25.6)** toward U3 also takes a long distributed path; radio supply current is not confined to a compact left-side loop. L2 is continuous, so high-frequency returns tend to follow the relevant outward conductor where possible, while low-frequency current spreads according to resistance. This is **shared impedance**, not proof that all digital return current passes through ADS AVSS. Re-route battery/regulator/MCU supply branches to keep their dominant loops away from reference/input circuitry. J3→charger currents can also cross the central board, but charging must not occur during worn acquisition; charger interference is not an acceptable explanation for normal on-body noise.

The **10 Ω / 10 µF nominal** analog feed has a **1.59 kHz nominal corner**. With an illustrative effective 4 µF after DC bias, it is **3.98 kHz**. At 133 Hz its attenuation is essentially zero. The exact biased capacitance of C28 must come from its actual part curve, not the illustrative derating assumption. Retain a low-impedance common ground and short distribution; increasing the resistor to 47 Ω loses headroom without solving the low-frequency envelope. A ferrite is not a 133 Hz filter.

Importantly, **the previous Q4 simulation's dominant internal-RLDREF supply path has already been addressed in the circuit**: R12/R13=1 MΩ and C32=1 µF provide external filtered midrail; `firmware_c/src/ads1298.c` defaults to CONFIG3=0xC4. The unloaded divider's τ≈0.5 s gives about **−52.4 dB at 133 Hz**. Do not report the old simulation's 1.5–7 µV internal-reference predictions as current-board results. RLD amplifier PSRR, ground differences, real LDO dynamics and direct pickup remain unmeasured.

### 1.6 RLD, guarding, RF/ESD protection and flex layers

- RLDINV and RLDOUT are compact F-side nets: approximately **3.09 and 4.06 mm aggregate track length**, no vias. Preserve the **1 MΩ || 4.7 nF** feedback and **100 kΩ** body-current limiter. RLDINV is sensitive; do not run digital traffic alongside it.
- RLDREF is **8.36 mm aggregate F-side tree**, including its divider branches; C32's supply pad is **3.94 mm** from pin60. Move C32 close to pin60 and return it to the local quiet AVSS region, not a radio-current corridor. The capacitor lowers node impedance in-band; it is not a reason to route it through noisy fields.
- BIAS_E is **28.47 mm aggregate**, four vias, shared by J1 pins2/19 and RLDIN. It drives eight pads; it is not the grounded flex shield. Keep it away from fast digital lines and evaluate stability/contact loss with the actual flex. The current firmware default `rld_mask=0x0F` selects eight sensed inputs, consistent with the 4.7 nF simulation recommendation; do not claim a measured 57° margin from that model.
- **Ground guarding:** use modest grounded separation between digital and inputs where it does not add large, unequal input capacitance. A grounded guard is electrostatic shielding, not a driven high-impedance guard. Do not repurpose RLDOUT/BIAS_E as an RF shield or add a driven guard without a stability design.
- **RF-filter provisions:** reserve, where space permits, one differential capacitor and a matched common-mode pair per channel on the **ADS side of the 4.7 kΩ elements**, with very short common-mode-cap ground returns. Initial experimental values around **10 pF C0G/NP0**, DNP until tested, are more defensible than automatically fitting 100 pF or nF parts. A differential capacitor alone does not reject common-mode RF. At a purely resistive 2 MΩ source sum, 100 pF differential gives a **796 Hz** pole; it is not a free EMG-band filter. Validate loading, tolerance/mismatch and GHz layout parasitics; a lumped simulation's deep RF notch is not guaranteed in hardware.
- **Exposed-input ESD:** sixteen resistors are not a verified ESD protection system. Reserve a credible low-leakage/low-capacitance protection approach at the connector, with a short discharge return, and qualify contact-discharge performance before claiming robust use. Generic high-capacitance/leaky TVS arrays can worsen this AFE: **1 nA × 1 MΩ = 1 mV**, before polarization. No ADS damage or ESD pass is asserted by this review.

**Keep the passive flex at two layers.** Its F-side P/N pairing and pod-local outward GND hatch are sensible cost/flexibility compromises. Four layers would add stiffness, bend-fatigue risk, cost and input capacitance; they do not remove the antenna/pod collision or electrode-contact mismatch. The free links deliberately have only a 0.10 mm GND return, not a continuous shield: the pod hatch is not an RF enclosure. For scale, one 10.9 mm-long, 0.10×0.012 mm copper link is about **0.15 Ω DC**; even order-10 nH inductance is about **150 Ω at 2.4 GHz**. That inductance is an illustrative estimate, not an extracted flex impedance.

Preserve P/N adjacency on the free links, supported local underpasses and matched exposure. Avoid expanding the hatch blindly over every link: that raises capacitance and stiffness, and adding/removing it under the antenna changes the antenna. Removing only pod3's hatch would still leave its large P/BIAS/N gold pads and the wrist under the radiator. Never connect the outward GND hatch as another skin electrode.

## 2. Antenna recommendation

**Keep the existing MIFA for a small engineering build after the electrical/process corrections; do not buy a chip expecting a no-tuning solution. I am not confident in the present antenna-plus-pod3 stack for a reliability-oriented order.** Before release, resolve that integration conflict or explicitly classify the build as an RF-risk prototype. If dependable on-wrist performance without iteration is the requirement, stop here and change the antenna/mechanical allocation, not just the radiator part number.

### Why the current placement is unqualified

The enforced board-only exclusion is **x=0…5.65, y=11.65…27**, all four layers. The radiator itself reaches **x=0.75…6.15, y=12.15…26.55**. Pod3 occupies about **x=1.45…8.55**, with 6.5 mm gold pads centred near **(5,2.2)/(5,12.2)/(5,22.2)** and outward hatch. Thus its BIAS and distal signal pad/hatch lie directly below the radiator; the rectangular keepout/pod overlap is **64.47 mm²**. This is a projected bounding overlap, not copper-overlap area or an EM result.

At 2.45 GHz, 2.8 mm vertical separation is only **0.023 free-space wavelengths**. The antenna can capacitively couple to the electrode/hatch/body, detune, lose efficiency, and inject RF into AFE wiring. A valid PCB keepout is necessary but not a three-dimensional metal-free volume. A good impedance match can also hide tissue absorption; S11 alone does not prove useful radiation.

The nearby cell is another load. There is a source discrepancy to reconcile: the assignment/layout record says **x=11…23**, while `docs/mech/mechanical_c.md`/the mechanical implementation use **x=10.5…22.5**. Use the smaller clearance for planning. Neither nominal location establishes an RF clearance certificate. Battery leads, charger magnets, the enclosure and wet strap must be part of the eventual RF assessment.

### Candidates in the supplied stock list

The following vendor implementation documents were retrieved and their relevant layout drawings inspected; catalogue identifiers below are identifiers, **not live stock claims**.

| Part / catalogue ID | Documented implementation | Recommendation |
|---|---|---|
| YAGEO ANT3216LL00R2400A / C293767 | 3.2×1.6×1.2 mm; 40×18 mm evaluation board with **10 mm ungrounded end region** and 30 mm ground length; second terminal is a soldering point, not ground | Not preferred in the present 5.65 mm strip; a smaller custom exclusion would be a new qualification exercise |
| Walsin RFANT3216120A5T / C127629 | 3.2×1.6×1.2 mm; **6×6 mm empty corner**, 45×20×1.2 mm test PCB; reference **6.8 nH series** match | Well-documented alternative, not a drop-in guarantee; x=0…6, y=21…27 would fit a corner in projection but still overlays pod3 and approaches J1 |
| Kinghelm KH-3216-A27 / C504001 | 3.2×1.6×0.6 mm; **5×6 mm clearance drawing**, 90×50 mm evaluation board; reference **5.6 nH series + 0.5 pF antenna-side shunt** | **First chip trial if a deliberate respin is chosen**; smallest directly documented clearance among the complete retrieved candidates, but much smaller product ground than its evaluation board |
| Rainsun AN2051-245 / C99727 | 5.1×2.0×1.2 mm, nominal 110 MHz bandwidth; retrieved sheets lack usable land/ground-clearance implementation | Do not select before obtaining complete layout guidance |
| Rainsun AN9520-245 / C99665 | Full V2.3 sheet: 9.5×2.1×1.0 mm; 35×60×0.6 mm test PCB, **20 mm ungrounded end region** | Reject for the frozen compact geometry; nominal bandwidth is not wearable-performance evidence |

If a chip trial is selected, reserve **KH-3216-A27 at the left edge in x=0…6, y=14.5…19.5**, all-layer exclusion except vendor-required feed/pad copper. Orient its long axis parallel to the edge, feed-side drawing toward larger y. Copy the entire vendor land/feed pattern, not a generic 3216 footprint. Put the antenna matching immediately outside the feed-side boundary in space freed by the MIFA; re-route the post-match 50 Ω feed without running it through the radiator keepout. These are **trial allocation coordinates, not a routed/DRC-verified placement**.

That proposed chip region still overlaps pod3 by **22.75 mm²** in projection. It does not solve the three-dimensional conductor conflict. Moving the pod/flex away or moving the radiator outside its footprint is a real mechanical redesign; no retrieved sheet certifies 2.8 mm external-metal clearance. An outboard or lid-mounted antenna is an alternative only with a new verified antenna/ground/battery clearance arrangement, not a magic external-antenna fallback.

Retain **Nordic C21=0.8 pF and L1=3.9 nH**, their inner-layer exclusion and C21→VSS31 return. This is the nRF port matching/filtering, distinct from **C22/R3/C23 antenna tuning**. The chip vendors' 5.6/6.8 nH values belong to an additional antenna-side match; do not substitute them for Nordic L1. Keep the π provisions and use high-Q inductors/C0G capacitors. Present 0.160 mm feed impedance is calculated for the nominal stack, not fab-confirmed controlled impedance.

## 3. Manufacturability: what passes, what still needs a release decision

### Main board

- **Geometry:** 4,583 tracks, of which **4,526 are 0.100 mm**, 49 are 0.127 and eight are 0.160. Four-layer 0.100 mm copper is within the review limit of 0.09 mm, but the board is overwhelmingly minimum-rule routing, not mostly 0.127 mm. Copper-edge rule is 0.300 mm and the saved/refilled board passes it. Outline is closed, **28.7×27 mm**.
- **Drills/rings:** all **204 vias are 0.45/0.30 mm**, nominal **0.075 mm radial ring**. Ordinary 0.30 mm drilling is economical, but it does not establish every annular-ring/CAM condition automatically. The antenna ground-short is a plated footprint hole, not a component lead needing the 0.13 mm lead-hole ring criterion. Obtain order-specific acceptance of ring/finished-hole interpretation and the stackup. No blind/buried process is specified.
- **Assembly:** 60 front footprints and seven back footprints; the back items are only J2/J3 and TP1–TP5, excluded from assembly. AE1 is printed, C22/C23 are DNP, leaving **57 purchased top-side placements**. Current BOM expands to those 57 references with matching values/footprints/MPNs/catalogue fields. Check pin1/polarity in the assembly preview for U1/U2/U3/U4/U5/Y1/J1/D1; KiCad and assembly-library rotation zeros are not universally identical.

**U1 edge-of-exposed-pad via: resolve before assembly release.** EP49 is 4.60×4.60 mm, bounds **x=6.70…11.30, y=3.40…8.00**. The GND via at **(6.65,5.90)** has annular copper penetrating the EP by **0.175 mm**, and its **0.30 mm drilled circle penetrates by 0.100 mm**. The drill reaches x=6.80; nearest EP paste aperture starts x=6.85, only **0.050 mm away**. This is a real edge-of-pad solder-wicking/voiding risk. Global tenting cannot be assumed to isolate a via within the common EP mask opening. Move the drill clear while preserving Nordic return geometry, or obtain explicit filled/plugged/process acceptance from the fab and assembler. Do not add a random C21 ground via as a workaround. TP2/TP3 also have the documented offset drill/land overlaps, but they are unpasted pogo access pads; no other pasted main-pad drill issue was identified.

**EP paste itself is sensible:** nine **1.24×1.24 mm rounded-square windows**, 1.53 mm pitch, 0.29 mm webs, about **13.36 mm² / 63.1%** actual paste area of the 21.16 mm² EP. Keep the windowing, not one full EP aperture. Peripheral U1 aperture area/perimeter estimates are about **0.825/0.687/0.550** for **0.10/0.12/0.15 mm** stencil foil respectively. Ask the assembler for a suitable **0.10–0.12 mm stencil/process** and QFN inspection rather than silently accepting thick generic foil. C22/C23 are DNP in the BOM but still have paste openings: specify stencil/deposition treatment for the unpopulated variant.

**Black-mask dams exist nominally.** Zero mask expansion is present in native/output artwork. Narrow webs: **U1 0.20 mm, U2 0.20, J1 0.20, U5 0.15**. Published black-mask guidance gives 0.13 mm minimum pad spacing for 1 oz construction, so U5's nominal margin is only 0.02 mm, but this is not an observed violation. A blanket +0.05 mm opening expansion per side would reduce U5's web to **0.05 mm**, and the others to 0.10. Require approval before automatic expansion or gang openings. Published guidance is not the actual order's CAM approval.

**Tombstoning risk, not a predicted failure rate:** zone connections are solid, not thermal spokes. Many 0402 ground pads meet broad copper while the other pad meets a 0.10 mm track. For example, C27's ground pad has about **0.389 mm²** adjacent contiguous GND in a 0.15 mm external collar; its supply has no equivalent plane connection. C3/C4/C6/C7/C8/C13/C26/C29/C30/C32 show similar asymmetry. Have the assembler review paste/preheat/placement/reflow and first articles; selectively balance connections where necessary. Do not destroy RF/bypass return impedance by indiscriminately thermal-relieving all grounds.

### Two-layer electrode flex

- **Geometry:** 447 segments, **446 at 0.100 mm**, one 0.200 mm bias bus; **60 vias at 0.55/0.30 mm**, 0.125 mm ring; **16 NPTH 1.2 mm** alignment holes. Width/gap 0.100, copper-edge 0.300 and hole-clearance 0.200 rules pass. Electrode side-edge gap is nominally 0.300; outer finger-to-tab-side 0.350, finger-to-tip 0.300. The 133.1×38.5 mm outline is closed. No drill overlaps an electrode or finger land.
- **Do not order from the generic 0.4 mm manifest alone.** It is a quote-option proxy. Actual requirement is **two-layer polyimide, rolled-annealed copper, coverlay both sides, nominal 0.099 mm flexible stack**, exposed finish defined separately, plus the F-side PI/adhesive tongue build-up. Current native stiffener information is drawing/text, not a validated structural-region definition. A successful structure-export command does not certify stiffener construction.
- **FPC dimensional acceptance is a release gate:** drawing requires **10.50±0.03 mm tab width, 9.50±0.03 mm outer contact-centre span, 0.30±0.03 mm finger width, ≥3.00 mm exposed length, 0.30±0.03 mm finished mating thickness**. Artwork is nominally correct: 0.50 pitch, 0.30 fingers, 3.20 copper length. The connector mouth is nominal 10.60, only 0.10 wider than the tongue; unspecified mouth/cutting tolerances prevent a certified clearance stack. Get explicit cutting/copper/coverlay registration and finished-thickness agreement.
- **Stiffener:** F-side, **10.50×3.70 mm**, native flex bounds x=59.75…70.25, y=54.80…58.50. About **0.201 mm added PI/adhesive** is required over the 0.099 mm stack to reach 0.30 total; a 0.30 mm stiffener added to the laminate is wrong. The drawing depicts a 6 mm end region; the chosen 3.7 mm length is an integration decision requiring retention/flatness acceptance or first-sample qualification.
- **Contact orientation is consistent:** B-side fingers, F-side stiffener; flex pin1 **(69.75,56.60)** is right in the skin-side/F view, matching main J1 pin1 through the no-axial-twist U-turn. Preserve physical face/orientation and electrically verify the first assembly, rather than reverse the pin map again.
- **Bend:** 4.8 mm free tail, R1 semicircle consumes 3.14 mm, leaving 1.66 mm straight allowance. No free-tail vias. R1 is about **10× laminate thickness**; a simple neutral-axis estimate gives order **1.85% copper-centroid / 2.45% outer-copper strain**. This is not fatigue qualification. Treat it as an assembly U-bend, capture the root and keep the stiffener outside it; no repeated-flex hinge claim.
- **Coverlay/finish:** electrode copper and nominal opening are both Ø6.50 with zero margin. Registration can reduce exposed diameter; 6.5 mm copper is not a guaranteed 6.5 mm exposed contact. Specify acceptable exposure/registration. ENIG is a prototype finish, not hard-gold mating endurance or long-term skin-suitability certification. Qualify wear/cleaning/skin interface; keep solder and paste off fingers. Consider avoiding skin-side marking ink in the skin-contact region.

## 4. Simplifications without losing the intended function

**No major component deletion is justified as a free win.** Keep one ADS1298, chip-down nRF, one shared LDO, passive two-layer flex, resistor arrays, battery pads and bottom SWD pads. Correcting the layout is simpler and more informative than adding a second analog regulator, RF module or four-layer flex before measuring.

- Keep the RF series tuning link and two DNP shunts: two unpopulated sites cost no placements and preserve tuning/rework options. Removing them is false economy on an unqualified antenna.
- Keep reference/VCAP/per-pin bypass capacitors and the external RLDREF divider. The divider specifically addresses an identified supply-to-body path; removing it reintroduces that risk.
- The LED plus R8 could be omitted if loss of the local status indicator is explicitly acceptable; that is **two saved placements but a feature deletion**, not function-preserving simplification. Holding it static/off while acquiring is a diagnostic operating option.
- Removing U5/C31/R9/R10 loses motion/IMU functionality, while deleting the charger or battery measurement loses those functions. They are not recommendations under the stated no-function-loss constraint.
- Simplify **routing**, not the safety/bypass network: local regulator capacitors, explicit supply branches, one ground plane, paired inputs, and digital traffic outside the input corridor. Keep the current LFRC/LDO-only architecture; no new LF crystal or DC/DC inductor is needed for this consult's fixes.

## 5. Exactly what I would relayout, and the effort/risk

The following is an implementation brief for the later task, **not an already-routed solution**. Footprint trial centres require native courtyard/clearance, height and routing checks. Preserve J1/J2/J3, TP1–TP5, button, outline and mechanical interface coordinates unless a separate mechanical change is agreed. Update deterministic sources together with the final implementation, not board-only undocumented changes.

### A. Mandatory bounded power repair; do this even if U2 does not move

1. **U3/C26/C27 area, x≈7…12, y≈17.5…21.3:** move C27 next to U3 VOUT/GND; trial centre **(8.1,20.4)**, orientation selected for supply toward pin2, is an allocation starting point, not approved placement. Route **VOUT→C27→load branches locally on F.Cu**, with short/wide connections and a cap-ground via adjacent to the ground pad. Keep C26 local to VIN; move C25 from (2.3,2.8) toward U4 BAT/GND in x≈9.5…11.5, y≈15…17. Do not retain a 60–70 mm detour in the regulator feedback/bypass loop.
2. Route **J2 VBAT→U3 VIN** through the south/left power corridor without touring the AFE/reference region. From C27, give the nRF VDD network a direct left/central branch, nominal corridor **x≈8…12, y≈9…20**; feed the analog RC separately, rather than through the IMU/ADC perimeter rail. Use **0.25–0.40 mm trunks where space permits**, not 0.10 mm everywhere. No extra regulator is the first fix.
3. Reallocate U1 and U2 bypass capacitors to their pins. In **x≈12.5…16, y≈7.5…12.5**, reserve local AVDD1/AVSS1 bypass and short quiet AVDD/reference returns. Connect charge-pump and quiet supply branches at a local supply star **without cutting L2**. Move C32 toward U2 pin60. Keep the VREF return distinct up to AVSS23; keep the reference/VCAP tree F.Cu.
4. Resolve the **(6.65,5.90) edge-EP via** with a reviewed Nordic-compatible return/land change or an explicitly approved filled/plugged process. Check paste/mask after the move, not just electrical DRC.

**Estimate:** roughly **one engineer-day**, potentially two with congested bypass re-placement and release exports. Risk is rerouting disturbance/decap access, not a new architecture. Acceptance: local cap connectivity/path inspection, native DRC/parity, stencil inspection, then actual load-step/radio-on power measurements on hardware.

### B. Bounded active-input interference repair

At minimum, remove **I2C_SDA from the IN1P parallel run x≈25.3…25.6, y≈15.3…17.1** and remove **B-side I2C_SCL directly under it**. Keep the U5 approach in the east corridor **x≈26.5…28.1, y≈16…22**, allowing for C7/C8/C31 and the 0.30 edge rule; re-place those capacitors if the corridor is blocked. Keep digital crossings short/near-orthogonal, with a continuous reference and ground-transition via nearby. A different signal layer without a ground between it and the input is not sufficient.

Move the **IMU_INT B-side cross-board run at y≈24.425** out from under E4P, preferably to the east/perimeter digital corridor before it heads north. Keep SWD stubs away from input escapes around **x≈12…19, y≈23…25** where practical; SWD inactivity makes this lower priority than I2C. Keep START static during acquisition; preserve the already good north-side SPI partition.

**Estimate:** **half to one engineer-day**, including local refill/DRC/output review; congestion may merge this with C. Risk is losing reference continuity while merely chasing spacing. Target ≥0.5 mm lateral digital/input separation where feasible, no long adjacent L3/L4 overlap, and no close digital line after the input resistor.

### C. Preferred analog cleanup if doing more than a patch

Reserve the south analog corridor **x≈14…26.5, y≈15.5…20.5** for inputs/arrays/filter provisions and no active digital traffic. Keep U2's input side facing J1. If the extra space is needed, trial U2 at **(20.2,9.1), 90°**, 1 mm north of present; this moves the input row to **y=14.7625** and requires north-side DVDD/SPI/decap rework.

A starting array allocation is **RN1/RN2/RN3/RN4 at x≈23.3/20.7/18.1/15.5, y≈18.4, rotation 0°**: vertical four-element banks rather than the present horizontal staggered fanout. This is deliberately a new trial placement, not a claimed collision-free packing. Work outward from the ADS pins, reserve any RF-capacitor sites at the post-resistor side first, and change the trial if exact pads/courtyards do not leave room.

Route each P/N together on **F.Cu over L2** for as much of the ADS-side path as possible. Use paired, short via transitions only where crossings force them. Confine raw J1 crossovers to the connector/root field; if L3 is unavoidable, keep a continuous B-side GND reference under that route and remove digital copper from that field. Do not use the current mixed-layer P/N lengths as a target to reproduce. Aim for short paths, same reference/layer exposure and approximately **≤2 pF modeled/measured P/N capacitance mismatch**, not cosmetic exact length equality.

Add the few useful fragment/return stitches listed in §1.4; retain the antenna fence and matching exclusions. A short grounded separator may help in the digital boundary, but do not turn the whole input bank into an unnecessarily high-capacitance grounded cage.

**Estimate:** **two to three engineer-days** including coherent placement/routing, source synchronization and release rechecks; A/B work overlaps this estimate rather than simply adding to it. Medium risk: a 1 mm U2 move can cascade through decoupling and routing, and filter sites consume real area. No promise that a packed footprint trial will route without iteration.

### D. Antenna/mechanics decision

A chip-only trial using the KH allocation in §2 is about **one to two engineer-days** for footprint/BOM/layout/mechanical review, **then two to four bench-days** for initial matching/link/AFE coexistence characterization once hardware/VNA/fixtures exist. Allow at least one hardware iteration. Shipping, fabrication and formal compliance are excluded.

If the goal is to remove pod3 from the antenna's near field rather than simply change antenna technology, the scope includes flex/pod/module allocation and possibly outline/enclosure changes: budget **several additional engineering days**, not a quick passive swap. Exact geometry depends on preserving eight contact positions and strap fit; no current alternate placement has been validated. This uncertainty is the reason I will not promise that any listed chip makes the present assembly reliable without tuning.

## 6. Acceptance after implementation / on the engineering build

Before releasing modified fabrication files: native DRC/parity, explicit route/return/paste review, complete flex process/tolerance acceptance, stock check, and assembly orientation preview. These are not substituted by the old clean reports.

On hardware, use the existing `docs/science/signal_chain.md` acceptance framework: internal short and remote-flex midrail terminations, realistic **100 kΩ–1 MΩ unequal source fixtures**, radio off/on/max intended TX and actual streaming, full-flex raw DC/clipping/PSD/TX-triggered averages, and RLD contact-loss stability. Proposed gates include **≤2 µVrms electronics in 20–850 Hz at 4 kSPS** and **≤0.5 µVrms radio-induced quadrature excess**; these are project targets, not measured results. Check specifically 133 Hz and harmonics without hiding them with notches.

For RF, de-embed a feed measurement with the radio disconnected and compare bare board, cell, enclosure, flex and tissue phantom. Then test radiated/link behavior on low/mid/high BLE channels, orientations/body shadow and dry/wet strap. Demonstrate the intended 2 kSPS×8×16-bit stream and gap reporting at the target distance; S11 alone is not acceptance. On-body tests must be battery/wireless only, with no ordinary VNA/scope/debugger/charger galvanically attached to a wearer. The recessed charger arrangement is not patient-isolation certification.

## Sources

- TI ADS129x SBAS459K, especially §§9.3.1.1, 11 and 12; local extracted source `docs/datasheets/ads1298.txt`: https://www.ti.com/lit/ds/symlink/ads1298.pdf
- TI AN043/SWRA117D, antenna implementation, ground/enclosure/measurement sensitivity: https://www.ti.com/lit/an/swra117d/swra117d.pdf
- Nordic nRF52832 reference circuitry: https://docs.nordicsemi.com/bundle/ps_nrf52832/page/ref_circuitry.html ; source-backed transcription in `docs/research/nrf52832_refcircuit.md` and calculation in `boards/neurband_c/layout/rf_geometry.md`.
- Yageo/Pulse implementation sheet: https://www.yageogroup.com/content/datasheet/asset/file/DATASHEET_ANT3216LL00R2400A
- Walsin V09 implementation sheet: https://www.passivecomponent.com/wp-content/uploads/2013/12/ASC_RFANT3216120A5T_V09.pdf
- Kinghelm V1.3 implementation sheet: https://www.kinghelm.net/upload/file/20240819/KH-3216-A27.pdf
- Rainsun primary summaries: https://rainsun.com/rswordpress/wp-content/uploads/2022/10/RainSun-AN2051.pdf and https://rainsun.com/rswordpress/wp-content/uploads/2022/10/RainSun-AN9520.pdf
- Manufacturer-authored AN9520 full-sheet mirror: https://datasheet.lcsc.com/datasheet/pdf/d4908b3a1e6947f5895e019d7c36e95d.pdf?productCode=C99665
- TI RF rectification mechanism, not an ADS1298-specific rejection measurement: https://www.ti.com/lit/an/sbot014a/sbot014a.pdf
- The fab's published solder-mask design guidance (its capabilities blog), not order-specific acceptance.
- J1 drawing/land evidence retained at `boards/neurband_c/layout/XUNPU_FPC-05F-20PH20.pdf` and `.png`, with interpretation in `boards/neurband_c/layout/j1_review.md`.

## Prioritized change list

### MUST — before ordering

1. **Repair U3/C27 and the main supply tree:** local VOUT→output capacitor→loads; keep charger BAT/VIN capacitors local and remove power detours through AFE distribution. Do not treat clean connectivity as bypass correctness.
2. **Remove the identified active input/digital coupling:** reroute IN1P-adjacent I2C_SDA and underlying I2C_SCL; remove IMU_INT broadside overlap with E4P. Preserve a real reference/return path.
3. **Resolve antenna/pod3 integration before calling the order reliable:** remove the conductor overlap through an agreed antenna/mechanical allocation, or explicitly release only an RF-risk engineering batch retaining tuning access. A chip substitution alone does not close this item.
4. **Resolve the U1 edge-EP drill:** move/reshape with Nordic return topology preserved, or obtain explicit filled/plugged assembly-process acceptance. Retain the windowed EP paste.
5. **Release an actual flex construction/tolerance specification:** 0.099 mm PI/RA/coverlay laminate, 0.30±0.03 total tongue, accepted tab/copper/coverlay tolerances and 3.7 mm stiffener retention. The generic 0.4 mm proxy is not the order specification.
6. **Obtain manufacturing/assembly release acceptance:** preserve zero-expansion black-mask dams, specify stencil/DNP deposition, review pin1/rotations and current stock, and regenerate/check outputs after the agreed changes.

### SHOULD

1. Reallocate local ADS AVDD1/DVDD and nRF bypasses; shorten C9/C32 ground/reference returns and C5's VCAP1 route. Star charge-pump/quiet branches without splitting L2.
2. Shorten/re-pair the analog corridor, especially channels 1/2 and mixed-layer pairs; target matched capacitance/reference exposure, not added length-matching meanders.
3. Add the few identified fragment/transition stitches, not a blanket via carpet; retain RF/matching keepouts and C21→VSS31 grounding.
4. Reserve/test small C0G differential/matched common-mode RF-filter sites and low-leakage ESD provisions; verify radio-on and contact-discharge behavior before robustness claims.
5. Validate assembled antenna/link/AFE coexistence and RLD contact-loss behavior; retain two-layer flex and qualify its assembly bend/finish.

### NICE

1. If a deliberate chip trial is wanted, use **KH-3216-A27**, with the documented clearance/match and explicit tuning budget; Walsin is the documented alternative, not an interchangeable footprint.
2. Consider omitting the LED/R8 only if the local status feature can be dropped; otherwise keep it quiet during acquisition.
3. Improve explicit release metadata/drawings and remove skin-facing legend ink from contact areas if the chosen coverlay/ink process warrants it; no architecture expansion is needed.
