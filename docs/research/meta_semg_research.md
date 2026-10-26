# Meta surface-EMG wristband: hardware research (sEMG-RD and Meta Neural Band)

Compiled 2026-10-25 for building a minimal sEMG wristband from first principles.

**How to read this document**

- **[Q]** = quoted or directly stated by the cited source (paraphrased closely; verbatim text is in quotes).
- **[I]** = my inference or arithmetic from quoted numbers. Treat it as a hypothesis.
- **[C]** = community reverse-engineering or third-party reporting. Not confirmed by Meta. Reported for one firmware build.
- "Not public" = I searched and found no primary source.

## Primary sources

| Key | Source | URL |
|---|---|---|
| N25 | CTRL-labs at Reality Labs (Kaifosh, Reardon et al.), "A generic non-invasive neuromotor interface for human-computer interaction", *Nature* 645, 702–711 (2025). Main text, Methods, Extended Data Fig. 1–3, Data availability | https://doi.org/10.1038/s41586-025-09255-w (open-access PDF mirror: https://repository.cshl.edu/id/eprint/42049/1/10.1038.s41586-025-09255-w.pdf) |
| BX24 | bioRxiv preprint of the same paper (2024) | https://www.biorxiv.org/content/10.1101/2024.02.23.581779 |
| GNI | facebookresearch/generic-neuromotor-interface (dataset and code README) | https://github.com/facebookresearch/generic-neuromotor-interface |
| Q24 | Sivakumar et al., "emg2qwerty", NeurIPS 2024 Datasets & Benchmarks (Sec. 4, "sEMG-RD Hardware") | https://arxiv.org/abs/2410.20081 · https://github.com/facebookresearch/emg2qwerty |
| P24 | Salter et al., "emg2pose", NeurIPS 2024 (Sec. 3.1, Appendix B.1 "sEMG Sensing") | https://arxiv.org/abs/2412.02725 · https://github.com/facebookresearch/emg2pose |
| MNR | Meta Newsroom launch post, Sept 2025 | https://about.fb.com/news/2025/09/meta-ray-ban-display-ai-glasses-emg-wristband/ |
| MHW | Meta Help, "How to use Meta Neural Band" | https://www.meta.com/help/ai-glasses/764536076119235/ |
| MHC | Meta Help, "How to charge Meta Neural Band" | https://www.meta.com/help/ai-glasses/4072180799705484/ |
| MEMG | Meta, "EMG wearable technology" page | https://www.meta.com/emerging-tech/emg-wearable-technology/ |
| TI | TechInsights, "Meta Ray-Ban Display Teardown Reveals More Than Meets the Eye" (public summary, 2026-06-10; full report paywalled) | https://www.techinsights.com/blog/meta-ray-ban-display-teardown-reveals-more-meets-eye |
| NBP | callbacked/neural-band-poc, `docs/findings.md` (community BLE reverse engineering) | https://github.com/callbacked/neural-band-poc/blob/main/docs/findings.md |
| MIX | MIXED, "RawMeta: Meta Neural Band eight-channel 2048 Hz EMG recorder" (2026-10-13; reports on a UCSD Triton NeuroTech tool; the GitHub repo was not reachable when I checked) | https://mixed-news.com/en/rawmeta-meta-neural-band-eight-channel-2048hz-emg-recorder/ |
| TG | Tom's Guide launch coverage (weight) | https://www.tomsguide.com/computing/smart-glasses/meta-ray-ban-display-glasses-features-neural-link-price-and-availability |
| BAB | Big Apple Buddy sizing guide (band size ranges, "Meta's official guidance, confirmed by support teams on community forums") | https://www.bigapplebuddy.com/blog/how-to-size-and-buy-meta-ray-ban-display-without-an-in-store-visit |
| FCC | FCC ID 2AGOZ-WQ8, model WQ8 (from a search-result summary; the fccid.io page returned 403 to me) | https://fccid.io/2AGOZWQ8 |

---

## 1. Spec table

| Parameter | sEMG-RD (research device) | Meta Neural Band (consumer) | Source |
|---|---|---|---|
| Sensing channels | 16 bipolar (differential) channels [Q] | 8 channels: "Equipped with eight sensors" [Q-TI]; band reports EMG config "2,048 Hz, eight channels" [C] | N25 Fig.1b, ED Fig.1; TI; NBP; MIX |
| Electrode count | 48 electrodes ("pogo-pin style round electrodes") [Q] | Not public | N25 ED Fig.1 |
| Electrode roles | 32 sensing (16 pairs); "the remainder electrodes serving as either shield or ground" [Q]. That leaves 16 non-sensing electrodes, 1 per pod [I] | Not public | N25 ED Fig.1 |
| Topology | Bipolar, sensing axis along the proximal–distal (forearm) axis [Q] | Not public | N25 Fig.1b |
| Proximal–distal inter-electrode distance (within a pair) | 20 mm centre-to-centre [Q] | Not public | N25 ED Fig.1 |
| Circumferential pitch (channel to channel) | 10.6 / 12 / 13 / 15 mm, depending on band size [Q] | Not public | N25 main text |
| Electrode size / shape | 6.5 mm diameter, round [Q] | Not public ("flat electrodes" in press coverage, unverified) | N25 ED Fig.1 |
| Electrode material | Gold-plated brass, dry [Q] | Not public | N25 ED Fig.1; Q24; P24 |
| Electrode compliance | Pogo-pin style; "spring-loaded to further adjust across small variations in wrist sizes" [Q] | Not public | N25 ED Fig.1; P24 App. B.1 |
| Skin prep / gel | None needed [Q] | None (consumer device) [I] | N25 ED Fig.1 |
| Driven-right-leg / bias electrode | Not described. Only "shield or ground" electrodes are mentioned [Q]. Whether any are actively driven is not public | Not public | N25 ED Fig.1 |
| Sampling rate | 2000 Hz per channel [Q] | 2048 Hz reported by the band's config [C] | N25; NBP; MIX |
| ADC resolution | 12 bit [Q] | 16 bit reported by the band's config [C] | Q24; P24; NBP |
| ADC full scale | 2.5 V [Q]. Max input amplitude 6.6 mV [Q] | ~0.2008 µV/count claimed by RawMeta [C]. This equals 2.5 V / 190 / 2^16 exactly, so it was probably derived from sEMG-RD numbers rather than measured [I] | N25 ED Fig.1; Q24; MIX |
| AFE gain | 190 (nominal) [Q] | Not public | N25 ED Fig.1 |
| Analog bandwidth | 20 Hz high-pass, 850 Hz low-pass (–3 dB) [Q] | Not public | N25 Methods; Q24 |
| Input-referred noise | 2.46 µVrms, benchtop, differential inputs shorted to mid-point [Q] | Not public | N25 ED Fig.1 |
| Dynamic range | ~65.5 dB [Q] | Not public | N25 ED Fig.1 |
| Input impedance | ~10 pF in parallel with 10 TΩ [Q] | Not public | N25 ED Fig.1 |
| CMRR | Not public | Not public | — |
| AFE architecture / ICs | 16 discrete analog front-end "sensors", one per pod/link, on multilayer rigid PCBs. Analog signals go over a flex PCB to a shared ADC in the capsule [Q]. IC part numbers not public | SoC: "Qualcomm QCC5100-001" [Q-TI]. AFE/ADC IC not public (TI full report is paywalled) | N25 Methods & ED Fig.1; TI |
| MCU / radio | Microcontroller + radio, "BLE 5.0" (ED Fig.1a block diagram) [Q]. Raw ADC + IMU data streamed to a USB Bluetooth receiver at the PC [Q] | Qualcomm QCC5100-001 [Q-TI]; 2402–2480 MHz [C-FCC summary]. Sends gesture events to the glasses; raw EMG processed on-device [Q-MEMG]; raw stream can be enabled over BLE [C] | N25; TI; MEMG; NBP |
| Raw data rate | 16 ch × 2000 Hz × 12 bit ≈ 384 kbit/s payload [I] | 8 ch × 2048 Hz × 16 bit ≈ 262 kbit/s when raw streaming is enabled; 16 samples/batch, 128 batches/s [C] | arithmetic; NBP; MIX |
| IMU | 3-axis accel + 3-axis gyro + 3-axis mag at 100 Hz, "not utilized" in the paper's experiments [Q] | Yes: "acceleration, rotation, orientation data" [Q-MEMG]; gyro and quaternion streams observed [C] | N25 ED Fig.1; MEMG; NBP |
| Other I/O | LEDs + buttons [Q] | Haptic feedback [Q-MEMG]; LED charge indicator [Q-MHC] | N25 ED Fig.1a; MEMG; MHC |
| Sizes | 4 sizes in Nature: S 130–148, M 148–169, L 169–193, XL 193–220 mm wrist circumference [Q]. (emg2pose says "three different sizes" [Q], probably an earlier fleet [I]) | 3 sizes [Q-MNR]: reported as 1: 130–148, 2: 148–169, 3: 169–198 mm [third-party, BAB] | N25 Methods; P24; MNR; BAB |
| Mechanical construction | 16 pods (rigid PCB + electrodes in Nylon-12 PA 3D-printed housings) joined by a multilayer flex PCB + strain-relief fabric. A continuous elastic nylon cord tied at the gap acts as clasp and tensioner. Capsule screwed on and connected via a connector on the flex [Q] | Vectran fibre band [Q-MNR], "clasp" closure, line on band faces user, compute module on top of wrist [Q-MHW]. Clasp mechanism details not public | N25 Methods; MNR; MHW |
| Placement | Wrist, capsule on dorsal side, electrode gap over the ulna [Q]; dominant-hand wrist [Q] | "Wear on the hand you write with", "just past your wrist bone", "snug", compute module on top [Q-MHW] | N25; MHW |
| Mass | Not public | 42 g [Q-TG] | TG |
| Battery | Battery life "more than 4 h" [Q]; capacity not public | Up to 18 h [Q-MNR]; Li-ion; capacity not confirmed (a "134 mAh" figure shows up in search summaries but I found no primary source) | N25; MNR |
| Charging | Not public | Proprietary magnetic charger, attaches under compute module, USB-C on the other end [Q-MHC] | MHC |
| Water rating | Not public (biocompatibility tested [Q]) | IPX7 [Q-MNR] | MNR |
| Training population | 162 (wrist), 4,900 (discrete gestures), 6,627 (handwriting); 11,236 total measured [Q] | "nearly 200,000 research participants" [Q-MNR] | N25; MNR |

---

## 2. sEMG-RD details

### 2.1 Electrode array and geometry
- **Layout [Q, N25 ED Fig.1]:** "48 pogo-pin style round electrodes … configured into 16 bipolar channels arranged proximo-distally, with the remainder electrodes serving as either shield or ground. Each electrode is 6.5 mm in diameter (gold plated brass). For each differential sensing channel (16 in total), centre-to-centre spacing between paired sensing electrodes is 20 mm."
- **Per-pod arrangement [I, from the Fig. 1b render]:** each of the 16 pods shows a row of 3 pins along the forearm axis, so 16 × 3 = 48. The most likely layout is the two outer pins as the 20 mm sensing pair and the middle pin as shield/ground. The paper does not state which pin is which.
- **Circumferential pitch [Q, N25 main text]:** "four sizes, with a circumferential interelectrode spacing of 10.6, 12, 13 or 15 mm, approaching the spatial bandwidth of EMG signals at the forearm (~5–10 mm), while minimizing the device's form factor."
  - [I] 16 × pitch ≈ 170 / 192 / 208 / 240 mm. That is longer than the wrist ranges because pod pitch is measured along the outer chain, and the ulnar gap absorbs the slack.
- **Gap [Q]:** "We placed the gap in electrodes to allow for tightening adjustments along the ulna bone, where muscles are reduced in density." ED Fig.1c says the gap between channels 0 and 15 "arises … due to variation in wrist circumference and elasticity between compartments" and is aligned with the ulna.
- **Left/right symmetry [Q, ED Fig.1; Q24; P24]:** because every pair is proximal–distal, the same band works on either hand. Electrode indices map to the same anatomy and only the differential polarity flips. Released datasets sign-flip left-hand data.

### 2.2 Analog front end and digitisation
- [Q, N25 Methods] "The analogue wristband comprised discrete links that each housed a multilayer rigid printed circuit board that contained the low-noise analogue front-end circuits and gold-plated electrodes." "The analogue front end applied 20-Hz high-pass and 850-Hz low-pass filters."
- [Q, ED Fig.1] Input-referred noise **2.46 µVrms** (inputs shorted to mid-point voltage). Nominal gain **190**. ADC full scale **2.5 V**. Dynamic range **~65.5 dB**. **2000 Hz** per channel. Input impedance **~10 pF ∥ 10 TΩ**, "providing excellent signal robustness against large variations of electrode-skin impedance among the population."
- [Q, Q24] "sampled at 2 kHz with a bit depth of 12 bits and a maximum signal amplitude of 6.6 mV … bandpass filtered with -3 dB cutoffs at 20 Hz and 850 Hz before digitization."
- [I] Consistency check: 2.5 V / 190 = 13.16 mV p-p, which matches the ±6.6 mV maximum. A full-scale sine is 4.65 mVrms, and 4.65 mV / 2.46 µV ≈ 1890, which is 65.5 dB. So the quoted dynamic range is FS-sine-RMS over noise.
- [I] 12-bit LSB referred to input = 13.16 mV / 4096 ≈ 3.2 µV. Quantisation noise ≈ 3.2/√12 ≈ 0.93 µVrms, below the 2.46 µVrms analog noise. A 12-bit converter after ×190 gain is therefore just about enough. A 24-bit ΣΔ ADC with lower gain would also work.
- [I] Architecture: the gain stage is local to each pod (short, high-impedance electrode traces). Amplified single-ended or differential analog signals run over the flex PCB to one ADC in the capsule. The 10 TΩ / 10 pF figure points to a CMOS/JFET instrumentation-amp input with no DC bias resistor at the electrode, or a bootstrapped bias. Neither the IC nor the bias scheme is disclosed.
- **Not public:** CMRR, AFE/ADC/MCU part numbers, whether any electrode is actively driven (DRL), shield-drive scheme, anti-alias filter order.

### 2.3 Digital, radio, power, mechanics
- [Q, N25 Methods] Compute capsule: "the battery, antenna for Bluetooth communication and a printed circuit board that contained a microcontroller, an analogue-to-digital converter and an inertial measurement unit."
- [Q, ED Fig.1a] Block diagram: 48× electrodes → 16× analog sensors → ADC → "Microcontroller + Radio (BLE 5.0)" → antenna; IMU; LEDs + buttons. "The microcontroller facilitates the transfer of unprocessed data from all ADCs and IMU directly to the bluetooth radio." All decoding ran on the host.
- [Q] IMU: 3-axis accel, gyro and magnetometer at 100 Hz, not used in any experiment.
- [Q] Battery life "more than 4 h". Streams "over secure Bluetooth protocols" to a Bluetooth receiver on the laptop.
- [Q, N25 Methods] Mechanics: "printed circuit boards were inserted into Nylon 12 PA 3D printed housings and then strung together with a multilayer flexible printed circuit board along with a strain-relieving fabric. An elastic nylon cord was routed continuously between the links and was tied together at the wristband gap to form a clasp and tensioning mechanism. Finally, the digital compute capsule was connected to the analogue wristband through a connector on the flexible printed circuit board and fastened together with screws." ED Fig.1b: "a kinematic chain with flexible joints connecting 16 pods."
- [Q, P24 App. B.1] "The band is tightened with an elastic strap and the size of the gap depends on the subject's wrist size and tightness … manufactured in three different sizes … electrodes themselves are spring-loaded."
- Mass: not public.

### 2.4 Signal characteristics reported
- Putative single MUAPs of ~10–20 µV amplitude, ~20 ms windows, visible on single channels during low-force contractions [Q, Fig.1b inset; ED Fig.2 scale bars 20 µV].
- Fig. 1e/2a gesture power ~10⁻⁷ V² summed across channels, i.e. roughly 100s of µV [Q/I].
- Model input preprocessing [Q, Methods]: divide by 2.46e-6 (noise s.d. → 1), 4th-order Butterworth **40 Hz high-pass** "motivated by the need to remove motion artifacts". Released datasets are already high-passed at 40 Hz [Q, GNI].

---

## 3. Meta Neural Band (consumer)

### 3.1 What Meta states
- Up to 18 h battery, IPX7, three sizes, Vectran fibre ("strong as steel when pulled, yet soft enough to bend easily"), "fidelity to measure movement even before it's visually perceptible", "nearly 200,000 research participants" [Q, MNR].
- Processes "electrical signals from muscle movement, and acceleration, rotation, orientation data". ML runs "locally on-device". Haptic feedback confirms gestures [Q, MEMG].
- Wear: dominant ("hand you write with"), "line on the band faces you", "just past your wrist bone", "snug and comfortably with the clasp closed", "compute module is on top of your wrist" [Q, MHW]. This is the same dorsal-capsule convention as the sEMG-RD [I].
- Charging: magnetic charger "to the compute module underneath the band", USB-C cable. LED: green >80 %, orange 20–80 %, blinking orange <20 % [Q, MHC].
- Electrode count, electrode material, sampling rate, ADC, AFE: **not published by Meta.**

### 3.2 Teardown and third-party findings
- **TechInsights [Q, TI public summary]:** "Equipped with eight sensors … The Neural Band contributes approximately 7.2% of the overall BOM and is powered by a Qualcomm QCC5100-001 SoC … the absence of a microphone or speaker suggests Meta is leveraging the device for sensor processing, gesture recognition, and wireless communication." The full component list (AFE, battery, IMU) is paywalled.
- **iFixit:** published a teardown of the Ray-Ban Display glasses (960 mWh glasses battery). I found **no iFixit teardown of the Neural Band itself**.
- **FCC [C]:** FCC ID 2AGOZ-WQ8, model WQ8, 2402–2480 MHz, application 2025-08-12, with internal photos on file (search-result summary; I could not open fccid.io). The internal-photo PDF is the best free source for the AFE chip if someone can fetch it.
- **Weight:** 42 g [Q, TG].
- **Sizes:** three; reported ranges 130–148 / 148–169 / 169–198 mm [third-party, BAB]. [I] The first two boundaries match the sEMG-RD S/M ranges exactly, which suggests the research sizing carried over to the product.
- **Raw BLE stream, community reverse engineering [C, NBP, firmware `297b870dc9be+`]:** after link setup, `StreamControlReq.enableRawEmg` starts a stream. The band's EMG config reports "**2,048 Hz, eight channels, 16-bit ADC, 16 samples/batch**". Each 256-byte block = 16 frames × 8 ch × uint16 LE. Timestamps step by ~7,812 µs (16 samples at 2,048 Hz). Gyro (3× int16) and quaternion streams are also available. Transport: P-256 ECDH, HKDF-SHA256, AES-CBC, 8-byte truncated HMAC. The author warns that voltage scaling and electrode mapping are unverified and that packet loss was 9–23 % in their runs. App strings mention a "wrist16" decoder path [C], so a 16-channel mode may exist internally (unverified).
- **RawMeta [C, MIX]:** 8 ch, 2048 Hz, 16-bit, "16 samples per Bluetooth batch at 128 batches a second", "each count worth about 0.2008 microvolts", ~60 ms latency, 0.13 % loss. "A resting forearm sits at roughly two to 10 microvolts RMS after a 20 to 450Hz filter, and a strong fist hits hundreds of µV to a few mV on the flexor-side channels." [I] 0.2008 µV = 2.5 V / 190 / 65536 exactly, so the scale factor was almost certainly copied from the sEMG-RD numbers and is not an independent calibration.

### 3.3 Inference: what changed from research device to product
- [I] 16 → 8 channels (TI's "eight sensors" and the 8-channel config agree), roughly 4 h → 18 h battery, ~42 g, on-device inference on a Qualcomm BLE SoC, IMU fused into gestures. The fact that a generic model works on 8 channels is the strongest public evidence that 16 is not a hard requirement for pinch/swipe/tap-class gestures. Note that the product supports fewer gestures than the paper; NBP says ring/pinky gestures are not supported natively.

---

## 4. Data and training requirements (N25 unless noted)

| Task | Training participants | Data per participant | Labels | Result |
|---|---|---|---|---|
| Wrist (1D/2D cursor) | 162 (96 with 2 sessions) [Q] | sessions of open-loop centre-out (40 reps) + cursor-to-target + smooth pursuit [Q] | motion-capture wrist angle at 60 Hz, OptiTrack [Q] | < 13°/s velocity error offline; 0.66 acquisitions/s online [Q] |
| Discrete gestures (9: index/middle press & release, thumb tap, thumb swipes L/R/U/D) | 4,900 [Q] | multiple postures; ~1/3 of the corpus is "null" data (snaps, flicks, typing); gestures in ~6 % of samples [Q] | prompt times, refined by a generative time-alignment algorithm [Q] | 0.88 gesture detections/s online [Q] |
| Handwriting | 6,627 [Q] | ~1 h 15 min each on average [Q]; 3 postures (seated on surface, on leg, standing on leg) | prompted text, CTC loss [Q] | 20.9 WPM online; 20 min personalisation → 16 % median CER improvement [Q] |

- **Generalisation [Q]:** single-person models do not transfer across people. Cross-user generalisation needed hundreds to thousands of people, and error follows a power law in participants and model size. Sessions = "band donnings"; participants "remove and slightly reposition the sEMG wristband" between sessions on purpose to get placement variation.
- **Session logistics [Q]:** 2–3 h study sessions, up to 300 participants/day at peak.
- **Models [Q]:** gestures use raw 2 kHz → Conv1d (stride 10 → 200 Hz) → 3 LSTM layers, 353k FLOPs/output sample (large). Wrist and handwriting use "MPF" features: cross-spectral density in 6 bands (0–62.5, 62.5–125, 125–250, 250–375, 375–687.5, 687.5–1000 Hz), 16×16 matrices, log-matrix, 50 Hz output. These require phase-coherent simultaneous sampling across channels [I].
- **Rotation invariance [Q]:** augmentation by circularly shifting all channels by −1/0/+1 positions, plus a "rotational-invariance module" that applies the same layer to the ±1-shifted channels and averages the results (wrist, handwriting, emg2qwerty). In other words, about one electrode pitch (10–15 mm) of band rotation is expected between donnings and handled in the model.
- **Open data [Q]:** paper statement: 300 participants (100 per task). GNI README table: discrete gestures 100 users / ~64 h, handwriting 100 users / ~141 h, wrist 100 users / ~77 h, all at 2 kHz and 40 Hz high-passed. Licence: CC BY-NC 4.0 per the repository LICENSE file (an earlier version of this note said BY-NC-SA; corrected after the data review in docs/science/data_and_models.md). emg2qwerty: 108 users, 346 h, two bands (32 ch). emg2pose: 193 users, 370 h, 16 ch + mocap hand pose.

## 5. What the authors say mattered

- **Electrode density vs. spatial bandwidth [Q]:** pitch chosen to approach the ~5–10 mm spatial bandwidth of forearm EMG "while minimizing the device's form factor".
- **Contact quality [Q]:** pogo-pin, spring-loaded dry electrodes and a kinematic chain "to provide good comfort and contact quality" and "consistent quality contact between the dry electrode and skin" across a broad population.
- **Very high input impedance [Q]:** chosen for "robustness against large variations of electrode-skin impedance among the population". No gel, no skin prep.
- **Sizing [Q]:** 4 sizes covering 130–220 mm, with participants measured and fitted on arrival.
- **Anatomical alignment [Q]:** gap on the ulna, capsule dorsal. Proximal–distal pairs keep left/right symmetry. Placement variation between donnings is a major source of variability. Cosine distances of the same gesture across sessions and users "heavily overlapped" with distances between different gestures.
- **Motion artefact [Q]:** handled by a 40 Hz high-pass in software, on top of the 20 Hz analog HPF. emg2pose lists electrode-skin contact artefacts, sweat impedance changes, external interference and fatigue as untested "signal aggressors" that "likely play a minor role".
- **Data scale over hardware tricks [Q/I]:** the paper's central claim is that thousands of participants plus prompting and time alignment produce generic models. The hardware's job is a consistent, low-noise, rotation-tolerant signal.

---

## 6. Implications for a minimal DIY copy (all [I] unless marked)

1. **Topology:** copy the proven geometry. Use N bipolar pairs oriented proximal–distal, ~20 mm centre spacing, plus one ground/shield contact per pod between the pair. **8 channels** is a defensible minimum (the shipping product appears to use 8). **16** matches the open datasets, so you could pre-train on Meta's data and fine-tune with your own. Choose 16 if you want to reuse the released models and data directly.
2. **Pitch and sizes:** for 16 channels, ~10.6–15 mm circumferential pitch with an ulnar gap. For 8 channels, roughly double that. Plan 2–3 band lengths (130–148, 148–169, 169–193 mm) or an elastic chain with slack at the gap.
3. **Electrodes:** 6.5 mm round, gold-plated, spring-loaded (pogo pins with domed heads are an off-the-shelf approximation), dry. Put the electrodes in individual rigid pods on a flex, held by an elastic tensioner, rather than in a rigid band.
4. **AFE targets:** ≤ ~2.5 µVrms input-referred noise over 20–850 Hz, very high input impedance (≥ GΩ, low pF; Meta quotes 10 TΩ ∥ 10 pF), ±6.6 mV input range, 20 Hz HPF / ~850 Hz LPF, ≥ 2 kHz simultaneous sampling, ≥ 12 effective bits after gain ~190. Meta used per-pod amplification. A practical DIY shortcut is a multichannel biopotential ADC (24-bit ΣΔ with integrated PGA and bias drive, e.g. ADS1298-class) placed close to the electrodes, which lets you skip the per-pod amplifiers. Whether that meets 2.5 µVrms at dry-electrode impedance has to be verified on the bench. Meta's CMRR and DRL use are not public, so add a bias/DRL electrode as cheap insurance.
5. **Radio budget:** 16 ch × 2 kHz × 16 bit ≈ 512 kbit/s raw (384 kbit/s at 12 bit). That fits BLE 5 2M PHY with care. Stream raw to a host first, as Meta's research device did, and move inference on-device later. Use timestamped batches (the Neural Band uses 16-sample batches) and sequence numbers so you can detect loss.
6. **IMU:** include one (cheap). Meta did not use it in the paper but the product fuses it.
7. **Data:** generic cross-user models needed thousands of people, which a small team cannot reproduce. Plan to (a) start from the released 16-ch 2 kHz datasets/models with matching geometry and signal scaling (divide by your noise RMS, 40 Hz HPF), and (b) personalise. 20 min per user gave measurable gains on top of a strong generic model, and single-user models from a few sessions do work for that user. Record deliberate re-donnings and ±1-channel rotations, and use rotation augmentation.
8. **Unknowns to bench-test yourself:** CMRR, DRL vs. passive ground, shield-electrode benefit, motion artefact with dry pins, sweat drift, and whether 8 channels at your pitch keeps enough spatial information for your gesture set.
