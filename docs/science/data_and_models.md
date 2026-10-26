# neurband: what the data can support, and how to collect it

Data/ML plan for the **rev C** band: 8 bipolar channels (ADS1298, 24-bit, gain 6, 2 or 4 kSPS), one pod per
channel, evenly spaced around the distal forearm/wrist (one size, 145–180 mm wrists). Each pod has two 6.5 mm dry gold
pads 20 mm apart along the forearm and a driven bias pad between them. The gap sits over the ulna. Data streams over BLE to a PC.
Recordings are `.npz` files (`emg [N, C]` float32 volts, `t`, `markers`, `meta`), as written by
`host/neurband_rec.py`. Code: `analysis/` (see [README.md](README.md)).

Notation: **[F]** = a published fact, with its source. **[J]** = my judgment or inference. Numbers from figures
only are marked as approximate.

## (a) What 8-channel wrist sEMG can realistically decode

### Literature numbers (WS = within-session, XS = cross-session/day, XU = cross-user; "per-user" = trained and tested on the same person)

**Discrete gestures, effect of channel count**

| Study | Channels / site / electrodes | Task | Condition | Result [F] |
|---|---|---|---|---|
| Côté-Allard et al. 2019, IEEE TNSRE 27:760 ([arXiv:1801.07756](https://arxiv.org/abs/1801.07756)) | Myo 8 ch, forearm, dry, 200 Hz | 7 gestures, 17 users | per-user, same day | ConvNet + transfer learning 98.3 % (20 s per gesture), 94.7 % (5 s). TD+LDA 97.6 % |
| same | same | 7 gestures, 8 users | real time, user re-dons, 14 days, no recalibration | 95.4 % on day 1, then degrades without feedback |
| Pizzolato et al. 2017, NinaPro DB5 ([PMC5638457](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5638457/)) | 1 Myo (8) vs 2 Myo (16) vs 12 Delsys | 41 movements, 10 users | per-user WS | **8 ch 55.3 %, 16 ch 69.0 %**, 12 gel 74.0 % |
| Zia ur Rehman et al. 2018, Sensors ([PMC6111443](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6111443/)) | Myo 8, dry | 7 gestures, 7 users, 15 days | per-user | CNN error 2.9 % WS → 5.8 % XS same day → 9.8 % across days. LDA 7.5 → 11.6 → 14.7 % |
| Kaczmarek et al. 2019, putEMG ([arXiv:1907.07428](https://arxiv.org/abs/1907.07428)) | 24 ch vs one 8-ch ring, forearm, wet | 8 incl. 4 pinches, 44 users | per-user WS | ~90 % with 24 ch. With 8 ch, whole-hand gestures hold up but **pinch precision drops 10–23 points** |
| Simon et al. 2024, Front. Rehabil. Sci. ([doi](https://doi.org/10.3389/fresc.2024.1345364)) | 8 vs 16, forearm | 6 classes, 6 + 4 users | per-user | error 7.0 % (8 ch) → 3.0 % (16 ch) |
| Young, Hargrove, Kuiken 2012, IEEE TBME ([PMC4234037](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4234037/)) | 8 bipolar, forearm | 7 classes | per-user | "four to six channels were sufficient" |
| Botros et al. 2025, J. Neural Eng. 22(5) ([doi](https://doi.org/10.1088/1741-2552/ae08eb)) | 4 wrist vs 4 forearm, 1 kHz | 5 + rest, 33 users | per-user / XU zero-shot / XU + 1 rep calibration | wrist 97.7 / **78.2** / **91.6 %** vs forearm 96.6 / 71.6 / 86.9 % |
| Pradhan, He, Jiang 2022, GRABMyo ([PMC9712490](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9712490/)) | 16 forearm vs 12 wrist, gel | 16 + rest, 43 users | per-user WS | AUC forearm 0.948 ≈ wrist 0.941 |
| Kaifosh et al. 2025, *Nature* ([doi](https://doi.org/10.1038/s41586-025-09255-w)) | **16 bipolar, wrist, dry gold, 2 kHz** | 9 gestures (index/middle press-release, thumb tap, 4 thumb swipes) | **XU generic**, thousands of training users | > 90 % offline on held-out users. 0.88 gestures/s closed loop |

**Fingers, pinches, thumb micro-gestures**

| Study | Setup | Result [F] |
|---|---|---|
| Zhong, Ma, Nazarpour 2026 ([arXiv:2604.04623](https://arxiv.org/abs/2604.04623), preprint) | **wrist**, 6 thumb gestures (tap, double tap, 4 swipes), 10 users, per-user WS, CNN | monopolar 15 ch 88.5 %, **8 ch 86.4 %**, 4 ch 82.3 %. 15 bipolar ch 82.3 %. Extensor side better than flexor side |
| Al-Timemy et al. 2013, IEEE JBHI 17:608 (PMID 24592463) | forearm, 15 finger movements, per-user | 98 % intact, 90 % amputees. 6-channel subsets ≈ full set |
| Baghernezhad et al. 2025 ([arXiv:2512.07997](https://arxiv.org/abs/2512.07997), preprint) | 4 wrist + 4 forearm, gel, 17 classes incl. single fingers, LDA | EMG wrist 63 %, forearm 56 %. The IMU alone did better (83 %) |

**Continuous kinematics**

| Study | Setup | Result [F] |
|---|---|---|
| Salter et al. 2024, emg2pose ([arXiv:2412.02725](https://arxiv.org/abs/2412.02725)) | 16 ch wrist, 20 joint angles, 193 users, XU | 12.2° unseen user, 15.8° unseen user + stage. Tracking 7.7° |
| Colot et al. 2026 ([arXiv:2604.22499](https://arxiv.org/abs/2604.22499), preprint) | **8-ch dry armband**, forearm, 15 finger joints, 20 users | **9.8° per-user, 16.7° XU** |
| Liu et al. 2021, NeuroPose ([NSF PAR](https://par.nsf.gov/biblio/10295971)) | Myo 8 ch, finger angles, 12 users | median 6.2°, 90th percentile 18.3° (per-user, with transfer step) |
| Muceli, Jiang, Farina 2010, EMBC (PMID 21097125) | forearm, 3 wrist DoF, per-user | R² 0.83 flexion/extension, 0.75 radial/ulnar, 0.77 pronation/supination |
| Kaifosh et al. 2025 | 16 ch wrist, wrist velocity, XU | < 13°/s offline. 1-D cursor 0.66 targets/s closed loop |

**Handwriting and typing**

| Study | Setup | Result [F] |
|---|---|---|
| Linderman et al. 2009, PLoS One ([PMC2727961](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2727961/)) | 8 bipolar, paste, 4 forearm + **4 intrinsic hand** muscles, digits 0–9, 6 users, per-user | 90.4 % |
| Beltran-Hernandez et al. 2020, MBE 17:5432 ([doi](https://doi.org/10.3934/mbe.2020293)) | Myo 8, 36 isolated characters, 3 users, pooled | 94.9 % |
| Kaifosh et al. 2025 | 16 ch wrist, free handwriting, XU generic from 6,527 users | 20.9 WPM closed loop. 20 min of personalisation: −16 % median CER |
| Sivakumar et al. 2024, emg2qwerty ([arXiv:2410.20081](https://arxiv.org/abs/2410.20081)) | **2 wrists × 16 ch**, touch typing, 108 users | CER with LM: generic 51.8 %, per-user from scratch 9.55 %, generic fine-tuned 6.95 % |
| Gazzari et al. 2021, IMWUT ([arXiv:2112.02382](https://arxiv.org/abs/2112.02382)) | Myo EMG + IMU, 52 keys, XU | key-press detection ~76 % balanced accuracy. Key identity top-3 ~32 % |

**Robustness, placement, sampling**

- **Band rotation/shift.**
  - Young et al. 2011 ([PMC4234036](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4234036/)): a 1 cm shift perpendicular to the fibres raised the error from ~8 to ~18 % (read from the figures).
  - Mongardi et al. 2025 ([PMC11991082](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11991082/)): a ±30° rotation of a 7-ch armband cost ~8 points (91.9 → 83.8 %). A 1-minute orientation calibration restored it (93.4 %).
  - Training on shifted data largely recovers the loss (Hargrove 2006, via a secondary source).
- **Wrist vs forearm.** The wrist is as good or better for finger and thumb gestures (Botros 2022, [doi](https://doi.org/10.1109/ACCESS.2022.3225761): 93.8–95.7 % vs 91.3–92.6 % across days; Botros 2025 above; GRABMyo).
- **Dry vs gel.** Small studies show little classification penalty once contact is stable: Steenbergen et al. 2023 ([doi](https://doi.org/10.1063/5.0148101)), 99.5 % vs 98.7 % on 4 classes.
- **Sampling.** 200 Hz loses a lot (Phinyomark et al. 2018, [PMC5982518](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5982518/)). 500 Hz vs 1 kHz costs ~2 % (Li et al. 2011, PMID 21293972). 2 kHz is ample.
- **Windows.** Smith et al. 2011 ([PMC4241762](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4241762/)): TD+LDA error plateaus at windows ≥ 150 ms, and 150–250 ms is optimal. Farrell & Weir 2007 (PMID 17436883): best controller delay ~100–125 ms.

### Judgment for neurband rev C (8 bipolar, dry, wrist) [J]

| Capability | Per-user (with calibration, several donnings) | Cross-user (no calibration) |
|---|---|---|
| Rest vs activity, gesture onset | ~100 % | yes |
| 6–8 gross hand/wrist postures (fist, open, wrist flex/ext/deviation) | **90–98 % within a donning, ~85–95 % across donnings.** A 1–2 min recalibration per donning recovers most of the gap | ~70–80 %, like Botros' 4-channel wrist zero-shot. Not a product |
| Meta-style micro-gestures (2 pinches, thumb tap, 4 swipes) | **~75–90 %**. Thumb swipes are the hardest. Wrist placement helps (Zhong: 8 ch only ~2 points below 15 ch). Usable as a detector only with null-data training | no: Meta needed 16 ch and thousands of users |
| Individual finger presses (5 fingers) | 70–90 %, with ring/little finger worst | no |
| Continuous wrist angle/velocity (2 DoF) | R² ~0.75–0.85: good enough for cursor control | coarse |
| Pinch force (proportional) | yes, monotonic ~0.8–0.9 correlation with a force label (needs a load cell for ground truth) | after normalising to MVC |
| Full hand pose (20 joints) | ~10° error (Colot 2026: 8-ch dry, per-user). Coarse hand state, not tracking | ~17° |
| Handwriting | isolated characters or digits per-user: plausible (Myo 8 ch: ~95 % on 36 characters, 3 users). Fluent text: research, needs many hours or a large pretrained model | no |
| Typing | **largely no.** One band sees one hand, and even 2 × 16 channels needed per-user data to reach < 10 % CER. Key-press *detection* on one hand is plausible | no |

What 8 vs 16 channels costs [J]: roughly a halving of the error ceiling on large or fine gesture sets (NinaPro 55 → 69 %;
Simon 7 → 3 % error). Little for ≤ 8 gross classes. Our pitch (~20 mm) is coarser than the forearm's ~5–10 mm spatial
bandwidth, so neighbouring channels carry less redundant information. That helps the information per channel but makes
band rotation matter more.

---

## (b) Using Meta's open datasets

### What exists (verified 2026-10-26 by reading the repos/code and opening real files)

| | generic-neuromotor-interface (GNI) | emg2qwerty | emg2pose |
|---|---|---|---|
| Paper | Kaifosh, Reardon et al., *Nature* 645 (2025) [doi:10.1038/s41586-025-09255-w](https://doi.org/10.1038/s41586-025-09255-w) | Sivakumar et al., NeurIPS 2024 D&B [arXiv:2410.20081](https://arxiv.org/abs/2410.20081) | Salter et al., NeurIPS 2024 D&B [arXiv:2412.02725](https://arxiv.org/abs/2412.02725) |
| Repo | [facebookresearch/generic-neuromotor-interface](https://github.com/facebookresearch/generic-neuromotor-interface) | [facebookresearch/emg2qwerty](https://github.com/facebookresearch/emg2qwerty) | [facebookresearch/emg2pose](https://github.com/facebookresearch/emg2pose) |
| Content | 3 tasks × 100 users: discrete gestures (~64 h), handwriting (~141 h), wrist angles (~77 h) | 108 users, 1,135 sessions, 346 h of typing, **two bands (both wrists)** | 193 users, 751 sessions, 370 h, 29 movement "stages", hand pose from motion capture |
| Size | 33.4 / 74.7 / 49.1 GB; 3-user subsets 1.1 / 2.0 / 1.3 GB (`--small-subset`) | 308 GB, one tarball | 463 GB full, **647 MB mini** |
| Format | HDF5 dataset `data`: `emg` f4 (16,), `time` f8 (Unix s), `wrist_angles` (2,) rad for the wrist task. pandas tables `prompts` (gesture name + time, or text + start/end) and `stages` | HDF5 `emg2qwerty/timeseries`: `emg_left`, `emg_right` (16,), `time`; attrs `keystrokes` (JSON: key, start, end), `prompts`, `user`, ... | HDF5 `emg2pose/timeseries`: `emg` (16,), `joint_angles` (20,) rad at 2 kHz (from 60 Hz mocap + inverse kinematics; failures = all-zero rows), `time`; attrs side, stage, user, split |
| Sampling / filtering | 2 kHz, high-passed at 40 Hz | 2 kHz, 40 Hz HP, drift-corrected | 2 kHz, 40 Hz HP |
| Units | **Not volts.** Scaled so the noise floor has std ≈ 1. The emg2pose datasheet states this; files measured: the quietest 1 s windows have std 1.1–1.2. The unit is ≈ 2.46 µV, the sEMG-RD input noise [J, inferred from the Nature preprocessing "rescaled by 2.46×10⁻⁶"] | same | same |
| Licence (data + code + checkpoints) | CC BY-NC 4.0 (LICENSE file) | README says CC BY-NC 4.0, LICENSE file says **CC BY-NC-SA 4.0**: assume SA | CC BY-NC-SA 4.0 |
| Checkpoints | yes (`download_models`): discrete gestures 6.5 M params, wrist 4.4 M, handwriting 1.0 M (the paper's best is 60 M, not released) | generic + 8 personalised users + 6-gram char LM | vemg2pose (~6 M), NeuroPose (6.35 M) |

**Licence consequence [J, not legal advice]:** fine for this non-commercial DIY research. Models trained or fine-tuned on
these data should be treated as non-commercial too, and as ShareAlike for emg2qwerty/emg2pose derivatives. If neurband
ever becomes a product, retrain from scratch on your own data. Correction to `docs/research/meta_semg_research.md`:
it lists GNI as CC BY-NC-SA 4.0, but the repo's LICENSE file is CC BY-NC 4.0 (no ShareAlike).

### Channel layout and mapping 16 → 8

- **[F]** All three use the sEMG-RD: 16 bipolar channels, proximal–distal pairs at 20 mm, 6.5 mm gold electrodes. The gap
  between channel 0 and channel 15 sits on the ulnar side next to the ulnar styloid. Left and right bands share indices
  that align with the same anatomy, but the differential polarity is reversed, so left-hand data are sign-flipped in the
  releases (emg2pose App. B.1; Nature Methods).
- **[F, measured on the files by the research agent]** Envelope correlation falls steadily with circular index distance, and channel 0
  correlates equally with 1 and 15. So indices run round the wrist in order. **Which way** they run (dorsal first or palmar
  first) is not stated anywhere.
- **Pitch [J]:** sEMG-RD pitch is 10.6–15 mm (4 sizes). Every other channel is therefore 21–30 mm apart. Our 8 pods
  around a 145–180 mm wrist sit ~18–22 mm apart. Our electrodes have the same size and the same 20 mm pair spacing.
  **Taking every other channel (`emg[:, 0::2]` or `emg[:, 1::2]`) is the closest physical match**, better than
  averaging neighbours (that would mimic bigger electrodes). emg2pose's code already has this as `ChannelDownsampling(2)`.
  It is unused, and no paper reports results with fewer than 16 channels. `analysis.filters.subsample_16_to_8` and
  `analysis.meta_data.load_meta_hdf5(..., n_channels=8, offset=0|1)` do the mapping. Use both offsets as data
  augmentation (a half-pitch rotation).
- **Index alignment [J]:** number our pods like Meta's: pod 1 = the first pod after the ulnar gap, then onwards around
  the wrist. To settle the direction, record wrist flexion/extension and compare which channels light up with Meta's
  wrist dataset (flexors on the palm side, extensors on the dorsum). Or simply try both orders and keep the one that
  transfers better.
- **Polarity [J]:** RMS, spectral and covariance-magnitude features do not care about sign. Raw-waveform models (Meta's
  Conv1d front end) do. Our P/N assignment versus Meta's is unknown, so add a global sign-flip augmentation, or test
  both.

### Band rotation augmentation

- **[F]** Meta rolls the channel axis by an offset drawn from {−1, 0, +1} (handwriting, emg2qwerty, emg2pose) or
  {−2…+2} (discrete gestures), and adds rotation-invariant pooling over ±1 shifts. Source code:
  `RandomBandRotation(offsets=(-1,0,1))` in emg2qwerty, `RotationAugmentation` in GNI and emg2pose.
- **[J]** For 8 channels at ~20 mm pitch, one pod is a much bigger rotation than one sEMG-RD channel (10–15 mm). Real
  donning variation is probably ±0.5 pod. Recommended:
  1. roll by ±1 pod only as an occasional augmentation;
  2. use fractional rotations by interpolating neighbouring channels (`analysis.dataset.fractional_rotate`, CLI
     `train --rotate-aug=-0.5,0,0.5`);
  3. mainly, **record many donnings** so the real variation is in the data.

### Pretrain on Meta, fine-tune on neurband: is it plausible?

Domain differences [J unless marked]:

| | sEMG-RD (Meta) | neurband rev C | Effect / what to do |
|---|---|---|---|
| Channels / pitch | 16, 10.6–15 mm | 8, ~18–22 mm | subsample 16 → 8 (above) |
| Electrodes | 6.5 mm gold, spring-loaded pogo pins [F] | 6.5 mm gold flat pads on flex, strap pressure | same geometry. Our contact pressure is less even → more motion artefact and lift-off. Augment with noise bursts |
| AFE | AC-coupled 20–850 Hz, gain 190, 12-bit, 2.46 µVrms, 10 TΩ ∥ 10 pF [F] | DC-coupled, gain 6, 24-bit ΣΔ (sinc), ~1–1.5 µVrms shorted (datasheet), 4.7 kΩ series | apply a 40 Hz HP in software like Meta's releases. Bandwidth: at 2 kSPS the ADS1298's −3 dB point is ~524 Hz, at 4 kSPS ~1 kHz (docs/DESIGN.md). **Record at 4 kSPS and decimate to 2 kHz** if BLE can carry it; otherwise everything above ~500 Hz differs from Meta's |
| Units | noise-floor units ≈ 2.46 µV | volts | divide our volts by 2.46e-6 (`meta_data.NOISE_UNIT`), then check that our rest noise reads ~1–2 units |
| Sampling | 2000 Hz | 2000/4000 Hz | decimate 4 k → 2 k (`filters.decimate`) |
| People | 100–193 per dataset | 1 (you) | per-user fine-tuning is needed anyway |

**Verdict [J]:**
- **Zero-shot** use of Meta's checkpoints on our data will most likely fail. They are 16-channel models, cross-user
  error is already large on Meta's own hardware, and our channels, contact and AFE differ.
- **Pretraining an 8-channel model on subsampled Meta data and then fine-tuning on ours is plausible and worth one
  experiment** once we have ≥ 1–2 h of our own labelled data:
  - [F] Pretraining helps personalisation on the same hardware. emg2qwerty CER with LM: 6.95 % fine-tuned from the generic
    model vs 9.55 % trained per user from scratch (Table 3).
  - [F] Nature: 20 min of personalisation data improved handwriting CER by a median 16 %. For a small generic model it
    was worth ~7× more pretraining data.
  - What transfers is low-level structure: spectral shape, MUAP-like temporal filters, rotation tolerance. Gesture
    semantics will transfer less.
  - Decide with the leave-one-session-out numbers on our data, not on hope: fine-tuned must beat from-scratch on the same
    held-out donnings.
- Best candidates:
  - **emg2pose** for continuous hand state. Every movement is labelled by mocap, so it pretrains general hand
    representations.
  - **GNI discrete gestures** for Meta's gesture vocabulary.
  - **emg2qwerty** is least useful for one wrist band, and it is 308 GB.
- **Start small:** GNI discrete-gesture small subset (1.1 GB) plus emg2pose mini (647 MB) to build the loaders and check
  units. Download a full set only once a model needs it.

---

## (c) First-week data-collection protocol (one user)

Principles:
1. **The unit of generalisation is the donning.** Evaluate on donnings the model has never seen; within-donning accuracy
   is nearly meaningless [F: Nature calls sessions "band donnings" and repositions the band on purpose].
2. Vary posture: Meta recorded seated/hand on surface, hand on leg and standing.
3. Record "null" data (everyday hand use) so detectors learn what *not* to fire on [F: ~1/3 of Meta's gesture corpus was
   null data].
4. Labels come from prompts, refined by the EMG.

### Tasks (protocols in `analysis/protocol.py`; `python3 -m analysis protocols` lists them)

| Protocol | Content | Length | Purpose |
|---|---|---|---|
| `quick` | sync, rest 10 s, MVC ×1, 6 gestures + rest ×3, sync | ~2.6 min | smoke test after every donning |
| `basic` | rest 30 s, MVC (fist; open+extend) ×2, **6 postures + rest** (fist, open, wrist flex/ext, radial/ulnar deviation) ×10, 2 s holds | ~7.5 min | first models; proves the pipeline |
| `meta` | rest 20 s, MVC ×1, **7 micro-gestures + rest** (index pinch, middle pinch, thumb click, thumb in/out/up/down: GNI's class names) ×15, one action per cue | ~8 min | Meta-style discrete gestures |
| `pinch` | MVC, then index-thumb and middle-thumb pinch force ramps to 30 % and 60 % MVC, following an on-screen bar | ~3.5 min | proportional (force) control |
| `handwriting` | write 10 prompted words/characters on paper with a pen, wrist resting, Enter after each | ~4+ min, user-paced | sequence decoding (CTC) |
| `typing` | type pangrams in the tkinter window (`--gui` logs key press **and** release times, like emg2qwerty) | user-paced | keystroke decoding |

Free-form **null** recording (no prompts, just the recorder running): 5–10 min of typing, phone use, picking things up,
walking. Label the whole file `null`.

### Session structure (one donning)
1. Put the band on with pod 1 just after the ulnar styloid. Note the wrist circumference, the distance from the wrist
   crease, and any deliberate rotation.
2. **Wait 5 min** before recording. Dry-electrode impedance falls as sweat builds up [J; standard dry-electrode
   behaviour]. Use this time for the `quick` protocol, then run `python3 -m analysis report` and continue only if the
   verdict is not REJECT.
3. Run 1–3 protocols, each with its own `.npz` + `.labels.json`
   (naming: `data/<user>_d<day>_s<donning>_<protocol>.npz`).
4. Take the band off, move about for 1–2 min, then put it back on 2–5 mm or a few degrees away from before.

### Week plan (~45–70 min of recording per day)

| Day | Donnings | Protocols | Milestone |
|---|---|---|---|
| 0 | bench | firmware bring-up checklist (shorted noise, test signal), then 1 on-body donning with `quick` | quality report passes |
| 1 | 3 | `basic` ×3 (one per donning) + 2 min rest recording | first LDA, leave-one-session-out (LOSO) |
| 2 | 3 | `basic` + `meta` per donning | LOSO on 6 sessions of `basic` |
| 3 | 3 | `meta` in 3 postures (forearm on table / arm hanging / standing) + 5 min null | posture robustness |
| 4 | 3 | `pinch` + `meta` + 10 min null | false-activation rate on null data |
| 5 | 3 | `handwriting` ×2 + `typing` ×2 per donning (~15 min each) | sequence data pilot |
| 6 | 2 | `basic` + `meta`, **no retraining** | **cross-day test**: train on days 1–4, test on day 6 |
| 7 | 2 | whatever day 6 shows is weakest (usually micro-gestures) | decide the next week |

By the end of the week: ~8 donnings × 10 reps = 80+ reps per `basic` class, ~13 donnings × 15 = 200 reps per `meta`
class, ~1 h of handwriting/typing, ~25 min of null.

### Labels and timing sync (implemented in `analysis/collect.py` + `analysis/align.py`)
- `collect.py` shows each prompt as "next: X" (prep), then "GO" (hold or do once), then "relax", and writes the host
  `time.time()` of every cue to `<name>.labels.json` after every step. Each run starts and ends with **3 "press the
  band button" cues**.
- The band's marker button puts markers in the recording (rev A/B: the BOOT button, packet resolution 5 ms).
  `align.fit_clock` finds the host→device offset that matches the most cue/press pairs (it tolerates missed or extra
  presses), assumes a 0.25 s reaction time, and fits drift for runs longer than 2 min. Expected error: ~30–50 ms,
  which is the spread of the reaction time. Tested on synthetic data: 10–20 ms residual.
- Then `align.device_events` refines each trial onto the actual movement: the channel-averaged RMS envelope crosses 25 %
  of the way from the prep-period baseline to the trial peak. Synthetic test: median error 20 ms against a true reaction
  time of 300 ± 80 ms. Trials with no movement found are dropped. This is a much simpler version of Meta's generative
  time alignment.
- **Rev C recorder requests [J]:**
  1. store the host receive time of every BLE packet next to the device timestamp;
  2. accept software markers on a local UDP port (`collect --mark-udp 127.0.0.1:5006` already sends `MARK <label>`);
  3. keep a hardware marker button;
  4. keep sequence numbers and count losses.
  Points 1–2 make prompt alignment exact to the BLE latency jitter (~10 ms), with no reliance on reaction time.
- Typing: the tkinter window logs press/release per key. That matches emg2qwerty's `keystrokes`, so their CTC recipe
  applies. Handwriting: the label is the prompted text plus its start/end (Enter). Like Meta, use CTC, so no per-stroke
  alignment is needed. A phone video at 60 fps is a cheap check if labels look wrong.

### How many minutes for a useful per-user model [J, anchored to the literature in (a)]

| Goal | Data | Notes |
|---|---|---|
| 6–7 gross postures, LDA | **3 donnings × 10 reps ≈ 25 min** of protocol time | classic myoelectric results plateau after a few reps per class *per session*; what matters is the number of donnings |
| 7 micro-gestures + rest, LDA/logistic | ≥ 6 donnings × 15 reps ≈ 50 min | expect lower accuracy; null data is needed for a usable detector |
| Small CNN on raw EMG for micro-gestures | ≥ 2–3 h (≥ 300 reps/class over ≥ 10 donnings) | below this, features + logistic regression usually win |
| Pinch force (ordinal / proportional) | 30 min of ramps over ≥ 4 donnings | a cheap load cell (HX711) logged on the PC gives a real force label |
| Handwriting / typing per user from scratch | many hours. emg2qwerty sessions average ~18 min [F: 346 h / 1,135 sessions], and personalised models trained on each user's remaining sessions, roughly 4–14 [J from the split description] | research-grade, and one wrist band only sees one hand (see (a)) |

---

## (d) Signal-quality gates (what to reject)

`python3 -m analysis report rec.npz` grades every channel (gates in `analysis/quality.py`, all [J] for this hardware):

| Metric | How | ok | warn | fail | Why |
|---|---|---|---|---|---|
| **Rest noise floor** | RMS, 20–450 Hz band-pass + mains notches, during labelled rest (else the quietest 10 % of 1 s windows) | ≤ 5 µV | 5–10 µV | > 10 µV | ADS1298 shorted ≈ 1 µV in band (datasheet). Dry skin adds contact noise. The Neural Band reportedly rests at 2–10 µV after 20–450 Hz ([MIXED, RawMeta report](https://mixed-news.com/en/rawmeta-meta-neural-band-eight-channel-2048hz-emg-recorder/), community). Micro-gesture MUAPs are ~10–20 µV [F, Nature Fig. 1], so a 10 µV floor hides them |
| **Mains residual** | narrow-band RMS at 50/60 Hz and harmonics, raw, at rest | ≤ 30 µV | ≤ 200 µV | > 200 µV | the notch removes it, but large pickup means a poor or unbalanced contact, and its intermodulation and harmonics leak |
| **Low-frequency instability** | 1–15 Hz RMS at rest | ≤ 300 µV | ≤ 2 mV | > 2 mV | pad rocking or lifting. Leaks past the 20 Hz high-pass during movement |
| **DC offset** | median / full scale (±400 mV at gain 6) | < 50 % | 50–90 % | > 90 % | DC-coupled: near the rail a movement clips |
| **Clipping** | samples at ≥ 99.9 % full scale | 0 | > 0.001 % | > 0.1 % | |
| **Lead-off** | fraction of packets with a lead-off flag | 0 | > 0.1 % | > 1 % | |
| **Flat channel** | detrended raw std < 0.5 µV | — | — | fail | open/shorted input |
| **MVC SNR** | 20·log10(RMS at MVC / RMS at rest), 20–450 Hz | ≥ 20 dB | 12–20 dB | < 12 dB | gel forearm EMG typically gives 30–40 dB [J]. A channel over the ulna will be lower: one warn is normal |
| Electrode bridge | rest correlation of neighbours > 0.95 | | warn | | sweat bridge or shorted pads |
| Packet loss | `lost_packets` from the recorder | ≤ 0.1 % | ≤ 1 % | > 1 % | gaps corrupt temporal models and labels |

Recording verdict: **REJECT** if > 1 % loss or ≥ 2 failed channels. **USABLE WITH WARNINGS** for 1 failed channel
(mask it, or drop the session for spatial models). Otherwise GOOD.

Session-level gates (check by hand for now):
- ≥ 4 of 6 sync presses matched (`Clock(...)` printout);
- movement detected in ≥ 90 % of non-rest trials (`train` prints `n_used/n_trials`);
- within-session sanity: the `basic` postures should be ≥ 90 % separable. If not, the band is not seeing muscle.

---

## (e) Model progression

| Stage | Input / model | Size, compute | Expected on our band [J] | When to move on |
|---|---|---|---|---|
| 0 | Envelope threshold (`align.envelope`) | none | rest vs activity ≈ 100 % | immediately |
| 1 | **TD features (log RMS, MAV, WL, ZC, SSC) per 200 ms window + shrinkage LDA / logistic regression** (`analysis.model`), majority vote per trial | trains in ms on a laptop | gross postures: ≥ 95 % within-donning, ~85–95 % LOSO. Micro-gestures: much lower (see (a)) | LOSO plateaus as donnings are added |
| 2 | Spectral/covariance features: log-spectrogram (64-pt FFT, 33 bins at 125 Hz like emg2qwerty) or Meta-style band covariance ("MPF") + logistic/MLP | CPU, seconds–minutes | +5–15 points on micro-gestures [J] | ≥ 1 h of data |
| 3 | Small **1D CNN / TDS-conv** on 2 kHz raw: Conv1d stride 10 (→ 200 Hz), 2–4 TDS or GRU blocks, 50–300 k params, rotation + gain + noise augmentation, event targets (gesture onset) for detection | laptop CPU minutes to an hour; any GPU much faster | beats stage 2 once there are ≥ 2–3 h and ≥ 10 donnings | it beats stage 2 on LOSO and on the null-data false-positive rate |
| 4 | Pretrain stage 3 on Meta data subsampled to 8 ch, fine-tune on ours | 1 GPU (A10-class) for hours: Nature reports ~3 h on 1×A10G for their discrete-gesture model on 100 users [F] | unknown: test it (see (b)) | fine-tuned > from-scratch on held-out donnings |
| 5 | Transformer/conformer + CTC for handwriting/typing (emg2qwerty TDS 5.3 M params; Nature handwriting conformer 1–60 M) | GPU, many hours | needs hours per user. With one 8-ch band, research only | — |

Model-size note [J]: Meta's 4–6 M-parameter models were trained on ~100 users; the 60 M handwriting model used 6,527.
A one-person dataset of a few hours supports ~10⁵ parameters before overfitting becomes the main problem, so stay small.

Real-time note: everything in `analysis/` is offline (zero-phase filters). Online decoding needs causal filters and
windows that use only past samples. Retrain with the causal front end before judging latency.
