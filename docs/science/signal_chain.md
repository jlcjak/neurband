# Rev C signal-chain science review

2026-10-26 · **Verdict: credible low-cost EMG acquisition experiment, not yet a demonstrated Meta-equivalent interface.** Keep one ADS1298; acquire at 4 kSPS. Contact stability, common-mode conversion and bias-loop stability—not 24-bit resolution—are the principal risks. Eight channels can support useful personalized gestures; handwriting/typing performance remains unproven.

**Evidence labels:** **P** published/manufacturer result; **C** calculation from stated assumptions; **E** engineering estimate; **A** proposed acceptance criterion, not a standard. **No neurband hardware was measured.** Reviewed the four requested documents and `boards/neurband_c/gen_c_sch.py`, including its 16 input resistors, bias feedback, RC supply branch and charger. Earlier rev A recommendations are not rev C measurements. Changes below are recommendations for the hardware lead; no design files were changed.

## 1. Signal and noise

There is no universal wrist voltage: muscle, posture, electrode location, force and processing bandwidth matter. Do not convert a percentage of MVC **force** directly into a percentage of EMG voltage.

| Activity | Input-referred amplitude / evidence |
|---|---|
| Supported, relaxed wrist | **E:** recorded baseline approximately 2–10 µVrms, including physiology and interference; not a guaranteed neural signal amplitude |
| Light finger gestures; typing/handwriting-level contractions | **E:** characterize 10–100 µVrms on responsive channels; individual channels/events can be below 10 µV. These are design envelopes, not published distal-wrist population percentiles |
| Strong contraction / MVC | **E:** approximately 0.1–1 mVrms on responsive distal channels, occasionally higher. **P:** prepared-skin proximal ECR measurements report roughly 0.43–0.84 mV RMS-derived maximal activity; not a wrist calibration [4] |
| Relevant low-signal evidence | **P:** Meta resolves putative wrist motor-unit potentials on µV scales and reports 2.46 µVrms shorted-input noise [1]. Dry-gold functional testing including writing reports a 46 µV mean **linear envelope**, pooled across tests/muscles—not writing-only RMS [3] |

**A:** electronics ≤2 µVrms and quiet on-body baseline preferably ≤5 µVrms. A 10 µVrms signal has 14 dB amplitude-ratio SNR over 2 µV noise, but only 6 dB over 5 µV. Detecting strong fists alone does not validate subtle input.

**P:** ADS1298 Table 1 specifies typical total shorted-input noise of **1.1 µVrms at 2 kSPS; 1.5 µVrms at 4 kSPS**, HR/gain 6/2.4 V reference/3 V analog supply [2]. These are not 20–850 Hz brick-wall measurements or production maximums.

**C, model:** use `H(f) ≈ sinc(f/Fs)^3`; calibrate white input noise to each published total. Integrate its folded power spectrum `S(f)=Σk |H(f+kFs)|²` over each band; total equivalent bandwidth is approximately `0.275 Fs`. This gives the following **output noise referred through DC PGA gain**, without inverse-sinc equalization. Actual ADC shaped/low-frequency noise may differ: band-specific ADS noise cannot be uniquely recovered from Table 1. Its published total is the conservative typical upper bound for any narrower ideal band.

| Fs | Analysis band, Hz | Model effective BW, Hz | ADS alone, µVrms | Two 4.7 kΩ resistors, µVrms | Total with each electrode modeled as 10 kΩ / 100 kΩ / 1 MΩ, µVrms |
|---|---:|---:|---:|---:|---:|
| 2 kSPS | 20–450 | 365 | 0.90 | 0.24 | 0.99 / 1.44 / 3.60 |
| 2 kSPS | 20–850 | 508 | 1.06 | 0.28 | 1.17 / 1.70 / 4.25 |
| 4 kSPS | 20–450 | 412 | 0.92 | 0.25 | 1.02 / 1.51 / 3.82 |
| 4 kSPS | 20–850 | 718 | 1.21 | 0.33 | 1.35 / 1.99 / 5.04 |

Thermal calculation: `σ² = 4kT ∫ Re[ZP(f)+ZN(f)+9400 Ω] |H(f)|² df`, T=300 K; table uses constant resistances and negligible input loading. **Do not substitute impedance magnitude for its real part.** For an ideal, unity-gain brick-wall band, the resistor pair contributes 0.26/0.36 µVrms over 20–450/20–850 Hz; a 100 kΩ-per-contact pair contributes 1.19/1.66 µVrms. Real dry interfaces add polarization/excess noise, current-noise conversion and motion, excluded here. TI does not specify enough input-current-noise data to close that budget at MΩ source impedance. **Decision:** ADC noise is adequate; dry contacts can dominate it.

## 2. Dry-gold contact, offsets and mechanics

**P:** Yamagami's 5×1 mm gold/PET contacts, alcohol-cleaned skin and light wrap, averaged **252 kΩ at 53 Hz, 139 kΩ at 151 Hz** after settling over approximately **two hours** [3]. Four-day testing included multi-MΩ values and individual changes up to 11–12 MΩ. This is not a specification for ENIG wrist pads.

| Frequency / condition | Defensible characterization envelope for rev C (**E**, per contact) |
|---|---|
| 50/60 Hz | Test 0.1–1 MΩ nominally, 1–10 MΩ adverse; 53 Hz publication above is the nearest numerical anchor |
| 100 Hz | Approximately 0.05–0.5 MΩ planning range; small-contact published spectra show hundreds of kΩ |
| 1 kHz | Approximately 0.01–0.1 MΩ planning range; published small-gold spectra show tens of kΩ |
| After donning / sweat | Expect decreasing impedance with hydration, but not a guaranteed settling time or reduction factor. Measure at 0, 5, 15, 30, 60, 120 min and after mild sweating; sweating can also cause slip and bridges |

Gold is polarizable. Matched electrode offsets partly cancel; gold's electrochemical standard potential is **not** the differential skin offset. No checked source establishes a 6.5 mm gold-wrist offset/drift distribution. **E:** stress-test ±10/50/100/300 mV offsets, 0.1–10 mV/min drift and 1–100 mV abrupt contact steps; these are test cases, not claimed percentiles. Software high-pass cannot recover clipped analog data.

**C:** gain 6 gives ±400 mV differential range and 0.0477 µV/ADC count. PGA headroom additionally requires `0.2+3|Vdiff| < VCM < AVDD−0.2−3|Vdiff|` [2]. With approximately 3.27 V AVDD after the supply resistor, ±400 mV leaves VCM about **1.40–1.87 V**; common-mode excursions can therefore clip before differential full scale. **A:** warn above |DC|=100 mV; reject/reseat above 300 mV or on clipping. Reducing gain is a diagnostic option, not a cure for contact instability.

**C:** 1 nA input-bias current through 1 MΩ adds 1 mV; 6 nA lead-off through a 2 MΩ pair adds about 12 mV before polarization. Include these in headroom tests rather than assuming lead-off is electrically invisible [2,13].

**Decision:** 6.5 mm ENIG plus a compliant backing is acceptable for first experiments, not established durable skin-contact hardware. Area is **33.2 mm²**; keep **6–8 mm rounded contacts**. A rigid dome alone cannot equalize force. Start with soft backing and approximately **2–3 kPa nominal pressure** (0.066–0.10 N per 6.5 mm pad), then test comfort/contact; this is extrapolated from textile-padding evidence, not a gold pressure optimum [5]. Stop for discomfort or skin changes.

Spring loading may maintain preload through wrist motion; **no defensible matched-study dB or impedance improvement factor was found**. A 2 mm head has **10.6× less area**: at equal interface properties, inverse-area scaling predicts worse impedance despite better compliance. Prefer springs behind broad caps, not needle-like contacts. ENIG's thin, potentially porous gold over nickel is not a skin-wear qualification [11]; inspect wear/irritation and do not solder on the skin-facing contact surface. Motion changes epidermal potential, contact area and local electrolyte distribution; static impedance alone does not predict artifacts [5].

## 3. Common mode, passive flex and bias drive

**P:** ADS inputs are approximately 1 GΩ DC minimum without lead-off and 20 pF typical; Meta reports 10 TΩ∥10 pF locally at each pod [1,2]. **E:** explore **20–80 pF additional flex/shield capacitance per trace**; actual stackup/overlap must be measured. A grounded hatch reduces electric-field coupling but adds capacitance; keep it insulated from skin.

**C:** `Vi/Vbody = 1/[1+(Zi+4.7k)(1/Rin+jωCi)]`. At 60 Hz with 100/200 kΩ contacts, 1 GΩ inputs and equal **50 pF total** input capacitance, conversion is **0.00189 (−54.5 dB)**: **10 mVrms body-to-board CM →18.9 µVrms differential**. ADS capacitance alone gives 7.6 µV; 100 pF total gives 37.7 µV. A further 5 pF mismatch with otherwise equal 100 kΩ contacts gives about 2 µV. This dominates the chip's −115 dB typical CMRR. Keeping residual CM below **2.6 mVrms** holds the 50 pF/100 kΩ-imbalance example below 5 µV. Direct unequal field coupling onto traces is an additional path.

Battery operation removes a galvanic mains return, **not capacitive pickup**: 1 pF coupled to 230 Vrms/50 Hz carries approximately 72 nArms. Resulting CM depends on body/device/environment return capacitances; there is no universal battery-only mains residual [6].

**C:** with all eight channels' P and N selected, 16 internal 220 kΩ paths give `A0≈16×1M/220k=72.7`; `RfCf` pole=106 Hz. Ideal unity body return gives **|1+A(60 Hz)|≈64 (36 dB)** suppression. This is not demonstrated system suppression. TI's one-channel phantom test measured about **12 dB improvement** with 100 kΩ protection [6].

Stability is the unresolved issue. **E/C stress model:** add a body-return pole from `(100k+Zbias) Cbody` and a sensing pole from `Zelectrode Cin`. With 1 MΩ/contact, eight parallel bias contacts, Cbody=1 nF and Cin=50 pF, poles are approximately 707 Hz/3.18 kHz. The three-pole model predicts unity crossing around 2.08 kHz and **−11° phase margin** with all 16 senses. These assumed lumped elements are not a measured person or a complete ADS macromodel, but demonstrate why copying 1M∥1.5nF does not prove stability. Contact loss changes the loop again.

**Recommendation:** selectable healthy-contact sensing, not unconditional `RLD_SENSP/N=0xff`; omit disconnected contacts immediately. Begin phantom evaluation with two good channels and 4.7 nF feedback (the same adverse model gives approximately 50° margin), then optimize measured stability versus mains rejection. Keep one shared 100 kΩ limiter; eight bias pads provide contact redundancy, not eight independent control loops. Never expose the GND shield as a body electrode.

**Buffers? Not mandatory for this first build.** If good mechanical contacts plus stable bias cannot achieve ≤5 µVrms mains residual, add local buffers. A hypothetical ≥10 GΩ/5 pF buffer input reduces the example conversion to approximately **1.9 µV per 10 mV CM**, before other errors—about 10× below the 50 pF case. Specify low current noise and roughly ≤10 nV/√Hz voltage noise; buffers do not cure electrode motion. Short, matched, strain-relieved P/N routes are cheaper first.

## 4. Sampling, processing and transport

| Native ADS rate | −3 dB bandwidth (**P**) | Sinc attenuation at 450 / 850 Hz (**C**) | Interpretation |
|---|---:|---:|---|
| 2 kSPS | 524 Hz | −2.21 / −8.26 dB | Useful conventional EMG, not Meta's 850 Hz response |
| 4 kSPS | 1048 Hz | −0.54 / −1.96 dB | Preferred acquisition; preserves more high-frequency information |

Use **HR/4 kSPS/gain 6/2.4 V reference**. Commission with packed raw 24-bit 4 kSPS capture; default long recordings may use **4→2 kSPS antialiased, high-passed 16-bit samples**. Meta's analog −3 dB point at 850 Hz is not a brick wall either [1]. Do not inverse-equalize aggressively or claim transfer-function identity.

Suggested causal nRF pipeline: fourth-order Butterworth HP at **20 Hz**, selectable **40 Hz** for Meta-style decoding [1]; 127-tap Kaiser FIR, β=5.65, cutoff=925 Hz at 4 kSPS; decimate by two. **C:** the normalized windowed-sinc design has <0.01 dB passband error through 850 Hz, >62 dB stop attenuation from 1 kHz and 15.75 ms FIR delay. ADS droop remains. Use identical filters across channels; optional 50/60 Hz notch only after diagnosing pickup. Preserve filter/scale metadata and periodic raw-DC/clip/lead-off status; 16-bit HP streams cannot establish offset headroom.

**C/E:** polyphase decimation needs 2.03 M MAC/s before FIR symmetry optimization; two HP biquads add 0.32 M multiplications/s. At an assumed 4–8 cycles/MAC-equivalent including memory/control, approximately **15–30% of the 64 MHz M4F** is plausible, not benchmarked [7]. Budget <40% measured DSP CPU, several kB of filter state plus separate DMA/radio queues. SPI reads 27 bytes×4k=108 kB/s; at 8 MHz, each frame takes 27 µs of the 250 µs period. Use DMA and do not filter inside the DRDY ISR.

After HP, choose **0.25 µV/count**: signed 16-bit range approximately ±8.192 mV; quantization RMS=0.072 µV. Flag packing saturation. Simply keeping the upper 16 ADC bits gives **12.2 µV steps**, unacceptable for subtle signals.

**P:** nRF52832/S132 supports 2M PHY, DLE and large ATT MTU [7,8]. Negotiate and log **MTU 247, LL length 251** at both ends; usable notification value=244 bytes. Nordic's encrypted, interference-free benchmark reaches 1327.5 kbit/s at 50 ms interval/full-length events; default MTU 23 reaches only 256 kbit/s even on 2M [8]. The USB dongle needs actual high-throughput central/USB firmware, not just compatible silicon.

| Stream, 8 channels | Raw payload | Example: 8-byte packet metadata + whole frames | Notifications/s | Calculated 2M airtime including LL/L2CAP/ATT, MIC, empty ACK and two 150 µs gaps |
|---|---:|---|---:|---:|
| 2 kSPS ×16 bit | 256 kbit/s | 14 frames, 232-byte value | 142.9 | 19.4% |
| 2 kSPS ×24 bit | 384 kbit/s | 9 frames, 224-byte value | 222.2 | 29.5% |
| 4 kSPS ×16 bit | 512 kbit/s | 14 frames, 232-byte value | 285.7 | 38.9% |
| 4 kSPS ×24 bit | 768 kbit/s | 9 frames, 224-byte value | 444.4 | 59.0% |

**C stress budget:** at 7.5 ms interval, reserve 0.30 ms/event for scheduling/control. A 3.75 ms event fits only two approximately 1.33–1.36 ms packet exchanges. Allow 25% unavailable events and 20% extra exchanges for retries: service falls to **167 notifications/s**—only 2 kSPS/16-bit is comfortably supported. A 6.25 ms event fits four exchanges and gives **333/s** under that stress: raw 4 kSPS/24-bit still fails. It needs more radio time, a cleaner link or reduced payload. These are explicit engineering allowances, not BLE guarantees; interference/disconnection has no finite worst-case delivery bound. Queue and report gaps; never silently interpolate training data. Default to 2 kSPS/16-bit after proper decimation, not native 2 kSPS acquisition.

## 5. Channel count and geometry

Keep **20 mm longitudinal P–N spacing**; it matches Meta, but is not proof of optimal wrist selectivity. The **18–22 mm circumferential pod pitch** is a different parameter: approximately 36–44 mm is the shortest spatial wavelength sampled without aliasing in a simplified uniform-ring model. Meta's 10.6–15 mm pitch samples more densely; its cited 5–10 mm spatial detail is not fully captured by eight pods [1]. Tendon/volume-conducted fields complicate any literal spatial-Nyquist interpretation.

| Evidence | What it establishes—and does not |
|---|---|
| Meta, 16 channels [1] | Demonstrated handwriting at 20.9 WPM using thousands of training participants; not an 8-channel ablation |
| Zhong et al., 2026 **preprint**, n=10 [9] | Six thumb classes: random bipolar reduction **15→8 channels changed accuracy 82.3→78.1%**. Within-person block evaluation, not cross-donning handwriting |
| Pelaez Murciego et al., n=13 [10] | Eight selected forearm channels gave median online completion **71.4%**, versus **57.1%** for circumferential placement. Placement matters; selected channels were subject-specific |
| emg2qwerty [12] | Typing dataset uses **two 16-channel wristbands**. Neither its geometry nor pretrained input is directly interchangeable with one 8-channel band |

**Decision:** eight is defensible for a cheap personalized gesture instrument; finger-specific low-force decoding, rotation robustness and continuous text are higher risks. No checked study justifies a numerical handwriting penalty for this exact reduction. Dropping alternate Meta channels permits an offline screening experiment, but does not simulate new contact/routing noise or guarantee compatible pretrained weights.

A fixed flex does not stretch: covering wrists 145–180 mm by changing only the ulnar gap can lose coverage or contact. Verify fit at both endpoints, not just nominal medium. Keep all eight middle bias pads for redundancy, with 3.5 mm edge gaps from adjacent 6.5 mm pads at 10 mm center spacing; test sweat bridging. Meta's middle contacts are documented as shield/ground, **not publicly established as driven RLD** [1].

## 6. Validation before decoder claims

**All limits below are A, chosen project gates.** First bench-only, then ≥5 volunteers with differing wrist sizes, three independent donnings each. Record unprepared clean/dry skin, timestamps, posture, strap setting, circumference, elapsed wear and sweat. Report every channel and failure, not just the best trace.

**Safety:** on-body = battery and wireless only; no charger, USB, SWD or grounded instrument. Rev C includes charge pads/TP4054: turning the AFE off in firmware does **not** isolate a charging cable. The 100 kΩ limits an ideal 3.3 V drive fault to 33 µA but is not mains isolation or medical single-fault compliance.

| Check | Procedure and pass/fail gate |
|---|---|
| Digital/internal test | Read back configuration; verify all 8 channels, polarity and simultaneous framing. Internal test at fCLK/2²¹≈0.9766 Hz, then fCLK/2²⁰≈1.9531 Hz; compare settled levels to datasheet Vref/2400 amplitude setting, ±5%, channel gain spread ≤1%. Verify external 100 Hz/1 mVrms to ±5%; internal source shares the reference and cannot independently calibrate it |
| Noise | 60 s each: internal MUX short, then remote-flex P/N tied to buffered midrail. No notch. 4 kSPS: each channel ≤1.5 µVrms in 20–450 and ≤2.0 in 20–850; 2 kSPS: ≤1.5/1.6 respectively. Radio-induced quadrature excess √max(σon²−σoff²,0) ≤0.5 µVrms. Noise limits apply after specified analysis bands, not sample standard deviation of unfiltered data |
| Offset/headroom | Bench sine 10/100 µVrms at 100 Hz, differential DC 0/±100/±300 mV, common mode 1.4–1.9 V where legal by PGA inequality. No missing/clipped samples in legal cases; 100 Hz gain within ±5%. Repeat with unequal source impedance |
| Bias stability/mains phantom | Sweep contacts 10 kΩ–1 MΩ with parallel 1–20 nF, open individual contacts; vary body return 0.1–1 nF and trace capacitance 20–100 pF. Capacitively inject 50/60 Hz, sweep injected current 5–100 nArms **bench only**. Require no sustained oscillation/railing, measured loop margin ≥45° where characterized, and ≤5 µVrms differential mains. Check contact-loss recovery <1 s without corrupting healthy channels |
| Lead-off | Start at 6 nA DC (±20% current accuracy [2]); disconnect each P, N and the bias connection separately. Flag opens <1 s; do not claim low contact impedance from absence of flags. Remove failed channels from RLD sensing; disable excitation during clean noise characterization |
| Impedance | Calibrate lead-off against 10/100 kΩ/1 MΩ standards, including 9.4 kΩ series path. DC polarity flip: `Rloop≈(V+−V−)/(2I)−9.4k`; distinguish polarization/settling from resistance. For AC at Fs/4=1 kHz on 4 kSPS, calibrate complex transfer/current on known R/RC loads and demodulate **before decimation**; correct ADS attenuation. Target calibration error ≤25%; target contact |Z(1kHz)|≤100 kΩ, investigate >1 MΩ or >3:1 pair imbalance. Pair-loop impedance is not individual contact impedance; use a calibrated large return/reference to characterize individual pads. A 1 kHz reading does not establish 50/100 Hz impedance |
| Rest/mains on-body | Supported relaxed hand, 60 s, ordinary powered room; before notch: fundamental 50/60±1 Hz ≤3 µVrms, harmonics within band RSS ≤5 µVrms; 20–450 baseline target ≤5 µVrms, >10 fails subtle-signal readiness unless physiology is independently identified |
| MVC and light tasks | Three 3 s comfortable maximal grips, resisted extension/flexion, finger/thumb gestures with 10 s rest; use best 1 s interior windows. Per-channel incremental SNR=`10log10[(Pactive−Prest)/Prest]`. Each channel target ≥15 dB on some task; ≥6/8 should reach ≥20 dB. Low ulna response alone is not failed electronics if injected tests pass. Each target light gesture should exceed 6 dB on ≥2 channels in ≥90% of 20 repetitions; add actual typing and pen/air writing |
| Crosstalk | Bench: drive one pair at 100 Hz/10 mVrms while others have realistic terminated contacts; victim coherent tone <−60 dB, repeat all pairs. On-body: log channel correlations/spatial maps; repeatable near-identical traces (|r|>0.98 across several selective tasks) trigger mapping/short checks, not an automatic biological failure |
| Motion | Relaxed supported hand; assistant moves strap/tail and applies controlled approximately 1 mm tangential disturbances, 10 repeats; separately test real wrist motion. No ADC/packing clipping, settle to within 2× resting RMS in <0.5 s, and 40–450 Hz artifact RMS <10 µV in ≥90% of disturbance windows. A matched flat/spring crossover should reduce 95th-percentile artifact RMS ≥6 dB without worse comfort/impedance to justify its cost |
| Transport/CPU | 30 min at 1–3 m including body shadow and ordinary RF traffic: <0.1% missing samples, no unmarked gaps, no acquisition overruns; repeat packing/filter modes. DSP <40% CPU, no growing queues; record negotiated MTU/PHY/DLE/event settings |
| Battery | Measure streaming current off-body and runtime, not just cell voltage. **E:** 8–15 mA total and 80 mAh usable from nominal 100 mAh imply 5.3–10 h; regulator dropout/cell discharge determine actual usable capacity. **A:** ≥4 h of compliant streaming, without noise degradation/reset/clipping through discharge |

For AC square-current excitation, a calibrated ±I square wave has fundamental peak `4I/π`; do not divide RMS voltage by nominal DC I indiscriminately. Example: 6 nA through a purely resistive 200 kΩ loop gives approximately 0.80 mVrms fundamental after the 4 kSPS ADS response at 1 kHz. Real skin is complex; calibrate actual excitation mode/current and loading [2,13]. At native 2 kSPS the lead-off tone is **500 Hz, inside the desired 850 Hz band**. Keep impedance scans separate from clean recordings; periodic DC probing may also alter polarization/noise. Obtain independent low-current, battery-isolated impedance spectra at 50/60/100/1000 Hz for the pad evaluation rather than extrapolating from one frequency.

### Recorder checks (reference Python; not a firmware change)

Compute these on contiguous, finite, correctly scaled **raw** blocks; never bridge packet loss for PSD. Keep DC/clip diagnostics from the pre-HP stream. The example uses two-second Hann Welch segments and returns **band powers in V²**:

```python
import numpy as np

def band_powers(x, fs):                 # x: samples × channels, volts
    n = 2 * int(fs)
    if len(x) < n or not np.isfinite(x).all():
        raise ValueError("Need >=2 s of contiguous finite samples")
    w = np.hanning(n)
    spectra = []
    for start in range(0, len(x) - n + 1, n // 2):
        y = x[start:start+n]
        y = (y - y.mean(axis=0)) * w[:, None]
        p = abs(np.fft.rfft(y, axis=0))**2 / (fs * (w @ w))
        p[1:-1] *= 2
        spectra.append(p)
    p = np.mean(spectra, axis=0)
    f = np.fft.rfftfreq(n, 1/fs)
    def power(lo, hi):
        return p[(f >= lo) & (f < hi)].sum(axis=0) * (fs/n)
    return {"20_450": power(20, 450), "20_850": power(20, 850),
            "motion": power(0.5, 20), "line50": power(49, 51),
            "line60": power(59, 61)}
```

Also compute packet sequence/sample-index gaps, actual sample rate/clock drift, raw median and DC slope, ADC-near-rail fraction (e.g. |code|≥0.95×2²³), int16 packing clips, bad-contact duty cycle, channel RMS/MVC SNR, mains-harmonic RSS, spectral median frequency and correlation matrices. Use `sqrt(power)*1e6` for µVrms. Label rested physiology separately from electronic noise; **do not define all power above 400 Hz as noise**. Train/test by complete trials and held-out donnings/days, not overlapping random windows. Useful decoding gate: ≥90% balanced accuracy on a small predefined gesture set in a held-out donning and <1 false activation/min during 10 min of rest/ordinary non-target activity; report handwriting CER separately, without promising Meta's result.

## 7. Concrete rev C recommendations — hardware lead decides

| Rank | Recommendation | Value / cost |
|---|---|---|
| **1 — recommend** | 4 kSPS acquisition; antialias before 2 kSPS/16-bit streaming, calibrated 0.25 µV/count; retain raw-DC/contact diagnostics and sequence/sample indices | Highest information preservation; firmware effort, no AFE change |
| **2 — recommend** | Compliant backing, broad 6–8 mm contacts, strain relief and endpoint-size fit tests; retain 20 mm bipolar spacing | Addresses the likely dominant failure mode; small mechanical cost. Do not treat 2 mm spring heads as an automatic upgrade |
| **3 — recommend** | Select only healthy RLD senses; make compensation tunable, evaluate 4.7 nF/two-channel starting point; remove failed contacts from feedback | Avoids system-wide railing/oscillation; firmware plus capacitor choice. All-channel 1.5 nF remains unvalidated |
| **4 — recommend** | Match/shorten high-impedance traces; measure capacitance. Reserve small differential RF-capacitor footprints and fit only after source-impedance/bandwidth testing | Cheap layout insurance; 4.7 kΩ alone is not a defined RF filter. Avoid large unmatched capacitors to GND; even differential 100 pF with a 2 MΩ source sum gives an approximately 796 Hz pole |
| **5 — conditional** | Keep the shared LDO only if radio-on noise passes; otherwise use a separate quiet analog regulator. Verify effective biased ceramic capacitance | The nominal 10 Ω/10 µF corner is 1.59 kHz and drops approximately 28 mV at 2.8 mA; it barely attenuates mains or slow radio envelopes. Additional regulator justified by measurement, not assumed necessary |
| **6 — conditional** | Add per-pod buffers only after contact/bias/routing fixes fail the ≤5 µV mains gate; consider 16 channels only if held-out-donning task performance is insufficient | Larger cost/complexity. More channels cannot repair poor contacts; eight good channels beat sixteen corrupted ones |
| **Safety prerequisite** | Physically prevent charging/programming while worn; qualify contact finish for intended skin use | Firmware AFE-off does not remove a galvanic cable path; not a claim of medical certification |

### Sources

[1] Kaifosh, Reardon & CTRL-labs, *Nature* (2025), Methods and Extended Data 1: https://www.nature.com/articles/s41586-025-09255-w

[2] TI ADS129x datasheet, SBAS459K, Table 1, electrical characteristics, §§9.3.1.5, 9.3.1.7, 9.3.2.4 and register descriptions (local text: `docs/datasheets/ads1298.txt`): https://www.ti.com/lit/ds/symlink/ads1298.pdf

[3] Yamagami et al., *Assessment of Dry Epidermal Electrodes for Long-Term Electromyography Measurements* (2018), §§2–3, Fig. 5: https://pmc.ncbi.nlm.nih.gov/articles/PMC5948629/

[4] Dahlqvist et al., forearm maximal-electrical-activity study (2018), Table 2: https://pmc.ncbi.nlm.nih.gov/articles/PMC5870034/

[5] Cömert et al., *Effect of pressure and padding on motion artifact of textile electrodes* (2013); gold-contact extrapolation explicitly limited: https://pmc.ncbi.nlm.nih.gov/articles/PMC3637835/

[6] TI, *Improving Common-Mode Rejection Using the Right-Leg Drive Amplifier*, SBAA188, §§4–6: https://www.ti.com/lit/an/sbaa188/sbaa188.pdf

[7] Nordic nRF52832 processor/radio specifications: https://www.nordicsemi.com/Products/nRF52832 ; S132 capabilities: https://www.nordicsemi.com/Products/Development-software/s132

[8] Nordic S132 throughput measurements: https://docs.nordicsemi.com/r/bundle/sds_s132/page/sds/s1xx/ble_data_throughput/ble_data_throughput.html ; event configuration: https://docs.nordicsemi.com/r/bundle/s132_v7.3.0_api/page/group_b_l_e_g_a_p_e_v_e_n_t_l_e_n_g_t_h.html

[9] Zhong et al., *On Optimizing Electrode Configuration for Wrist-Worn sEMG-Based Thumb Gesture Recognition* (2026), **preprint**, §III-C: https://arxiv.org/html/2604.04623v1

[10] Pelaez Murciego et al., *Reducing the number of EMG electrodes during online hand gesture classification with changing wrist positions* (2022): https://doi.org/10.1186/s12984-022-01056-w

[11] IPC-4552 with amendments (2012), ENIG layer structure/porosity and 0.05 µm minimum gold specification; not a skin-contact standard: https://www.electronics.org/TOC/IPC-4552wAm-1-2.pdf

[12] Sivakumar et al., *emg2qwerty* (2024): https://arxiv.org/html/2410.20081v1

[13] TI, *Understanding Lead-Off Detection in ECG*, SBAA196A: https://www.ti.com/lit/an/sbaa196a/sbaa196a.pdf

**Verification performed for this review:** numerical integration of the stated noise model, sinc response, Johnson-noise/RSS budgets, common-mode conversion and lumped bias-loop stress cases; FIR frequency-response sweep; packet airtime/event arithmetic. The recorder reference code passed synthetic 100/50/700/10 Hz tone checks with 10/3/7/50 µVrms amplitudes and rejected short/nonfinite blocks. These are calculations and synthetic checks, not bench, firmware-cycle or human-subject results.
