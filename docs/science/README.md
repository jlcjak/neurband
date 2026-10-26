# neurband science: from recordings to models

This folder answers one question: once the band is built, can its data train useful models? Start here.

| File | What |
|---|---|
| [data_and_models.md](data_and_models.md) | (a) what 8-channel wrist sEMG can decode, with literature numbers; (b) using Meta's open datasets; (c) the first-week collection protocol; (d) signal-quality gates; (e) model progression |
| `../../analysis/` | Python package. Runs with numpy alone (scipy optional, h5py only for Meta's files) |
| `../research/meta_semg_research.md` | hardware research on Meta's sEMG-RD and Neural Band |

## The pipeline

```
band ──BLE/UDP──> host/neurband_rec.py ──> data/u1_d1_s1_basic.npz          (emg volts, t, markers, meta)
                  python3 -m analysis collect basic --out data/u1_d1_s1_basic   (prompts -> .labels.json)
                                    │
     python3 -m analysis report data/*.npz          quality gates: noise, mains, clipping, lead-off, MVC SNR
     python3 -m analysis train data/u1_*_basic.npz  features + LDA/logistic, leave-one-session-out
```

1. Start the recorder (terminal 1). Start `collect` with the same base name (terminal 2). Press the band button at each
   magenta "press the band button" cue: 3 at the start, 3 at the end.
2. `report` straight away. Re-seat the band if the verdict is REJECT.
3. After 2 or more donnings, `train` gives cross-donning accuracy and a confusion matrix.

Try everything now without hardware:

```sh
python3 -m analysis synth /tmp/nb --sessions 3 --protocol basic      # 3 synthetic donnings
python3 -m analysis report /tmp/nb/synth_s00.npz
python3 -m analysis train /tmp/nb/*.npz [--model logreg] [--rotate-aug=-0.5,0,0.5]
python3 -m analysis synth /tmp/nbf --sessions 1 --fault 3:flat --fault 5:line && python3 -m analysis report /tmp/nbf/*.npz
python3 -m unittest discover -s analysis/tests -v                     # 15 tests, ~15 s, numpy only
```

The synthetic generator only exists to test the code: its accuracies say nothing about the real band.

Package map: `recording` (load/save .npz + labels), `filters` (zero-phase 20–450 Hz band-pass + mains notch, scipy
or numpy-FFT; decimation; 16→8 mapping), `quality`, `features` (RMS, MAV, WL, ZC, SSC), `align` (marker-based clock
fit + EMG onset refinement), `dataset` (labelled windows, rotation augmentation), `model` (LDA, logistic regression,
LOSO), `protocol` + `collect` (prompted sessions, terminal or `--gui` tkinter with keystroke logging), `synth`,
`meta_data` (Meta HDF5 → same format).

## Verdict

Evidence and sources are in [data_and_models.md](data_and_models.md) (a). Everything below is my judgment.

**The band will be able to:**
- detect rest vs activity and gesture onsets reliably;
- classify **6–8 gross hand/wrist postures per user at ~90–98 %** within a donning and ~85–95 % across donnings,
  with a minute of recalibration per donning;
- do **2-DoF continuous wrist control** and **proportional pinch force**;
- classify Meta-style **micro-gestures (pinches, thumb tap/swipes) per user at roughly 75–90 %**. Thumb swipes will be
  the weakest; this is the most interesting result the band can realistically reach;
- give coarse hand-pose estimates (~10° per user).

8 channels at the wrist are enough for all of this. The literature shows 4–8 channels saturate for ≤ 8 gross classes,
the wrist is as good as the forearm for finger/thumb gestures, and the shipping Neural Band reportedly streams 8.

**It will not:**
- give **cross-user, plug-and-play** models. Meta needed 16 channels, thousands of people and large models to reach
  ~90 % on held-out users;
- do **typing**. One band sees one hand, and even two 16-channel bands needed per-user data to get below 10 % CER;
- do **fluent handwriting**, or precise finger tracking at emg2pose quality. Isolated characters per user are plausible.

Pretraining on Meta's data (subsampled 16 → 8) and fine-tuning on ours is a plausible experiment once we have ~1–2 h of
labelled data. Treat it as unproven until it beats from-scratch training on held-out donnings. Licences are
non-commercial.

**The 3 most important things for data quality:**
1. **Stable, even skin contact.** This is the biggest risk with flat dry pads on a strap (Meta used spring-loaded
   pins). Let contacts settle ~5 min after donning, and keep pods from rocking when the wrist moves. Gate every
   recording on rest noise ≤ 5 µV, low 1–15 Hz content and no lead-off/clipping (`analysis report`).
2. **Many donnings, judged across donnings.** Re-don 2–3 times a day with small deliberate shifts, vary posture,
   record null (everyday) data, log placement metadata, and only trust leave-one-session-out and cross-day numbers.
   Within-donning accuracy flatters everything.
3. **Exact, lossless timing.** Sync cues with marker presses, refine labels from the EMG onset, keep packet loss below
   0.1 %, and record at 4 kSPS (decimate to 2 kHz) if BLE can carry it. For rev C, have the recorder store host
   receive times and accept software markers. That makes label alignment exact.
