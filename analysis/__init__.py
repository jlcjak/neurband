"""neurband analysis: load, filter, quality-check, featurise and classify sEMG recordings.

Works with numpy alone; uses scipy for IIR filtering when it is installed.
Modules:
  recording load/save recordings (.npz from host/neurband_rec.py) and label files
  filters   20-450 Hz band-pass, mains notch, resampling, 16->8 channel helpers
  quality   per-channel signal-quality report and pass/warn/fail gates
  features  windowed time-domain features (RMS, MAV, WL, ZC, SSC)
  align     map prompt times (host clock) onto recording samples via markers
  dataset   turn recordings + labels into labelled feature windows
  model     LDA / logistic-regression baselines, leave-one-session-out evaluation
  synth     synthetic 8-channel wrist sEMG with a known ground truth
  collect   prompt-driven collection script (terminal or tkinter)
  meta_data read Meta's open datasets (h5py) into the same format, 16 -> 8 channels
Run `python3 -m analysis --help` for the command line.
"""
__version__ = "0.1"
