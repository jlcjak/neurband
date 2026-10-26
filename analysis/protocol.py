"""Collection protocols: gesture sets and the step lists that collect.py runs (and synth.py
simulates). All times in seconds. See docs/science/data_and_models.md section (c).

Step kinds
  sync     "press the band button now": cue for clock alignment (marker press)
  rest     relax, hand still, for `dur` s (noise floor, null class)
  mvc      maximum voluntary contraction for `hold` s (SNR reference, normalisation)
  gesture  get ready (`prep`), GO: hold or perform once (`hold`), relax (`rest`)
  ramp     follow a force target 0 -> `peak` (fraction of MVC) -> 0 over `hold` s
  text     handwrite the prompt (user-paced, Enter when done)
  typing   type the prompt; every key is logged with its time
"""
import random

# Tier 1: gross hand/wrist postures. Easy for 8 channels; proves the pipeline.
GESTURES_BASIC = ["fist", "open", "wrist_flex", "wrist_ext", "radial_dev", "ulnar_dev"]

# Tier 2: Meta-style discrete micro-gestures, named like the generic-neuromotor-interface
# classes (index/middle press+release, thumb_click, thumb_in/out/up/down). We count a
# press+release as one pinch. Hand in a loose fist, thumb resting on the side of the index
# finger like on a d-pad; one action per cue, relaxed in between. The exact directions Meta
# used are defined in their paper's figure; ours are an approximation.
GESTURES_META = ["index_pinch", "middle_pinch", "thumb_click", "thumb_in", "thumb_out", "thumb_up", "thumb_down"]

INSTRUCTIONS = {
    "fist": "Make a firm fist (about half strength)",
    "open": "Open the hand, fingers spread",
    "wrist_flex": "Bend the wrist toward the palm",
    "wrist_ext": "Bend the wrist back",
    "radial_dev": "Tilt the hand toward the thumb",
    "ulnar_dev": "Tilt the hand toward the little finger",
    "index_pinch": "Pinch index fingertip to thumb, release",
    "middle_pinch": "Pinch middle fingertip to thumb, release",
    "thumb_click": "Tap the thumb down on the side of the index finger",
    "thumb_in": "Swipe the thumb toward the palm",
    "thumb_out": "Swipe the thumb away from the palm",
    "thumb_up": "Swipe the thumb along the index finger toward the fingertip",
    "thumb_down": "Swipe the thumb along the index finger toward the knuckle",
    "rest": "Relax. Hand still",
    "mvc_fist": "SQUEEZE a fist as hard as you can",
    "mvc_open": "OPEN and bend the wrist back as hard as you can",
    "pinch_ramp_index": "Index-thumb pinch: follow the bar up and down",
    "pinch_ramp_middle": "Middle-thumb pinch: follow the bar up and down",
}

HANDWRITING_PROMPTS = ["a b c d e", "hello", "the quick brown fox", "neurband", "0 1 2 3 4 5 6 7 8 9",
                       "jumps over", "the lazy dog", "sphinx of black quartz", "judge my vow", "emg"]
TYPING_PROMPTS = ["the quick brown fox jumps over the lazy dog",
                  "pack my box with five dozen liquor jugs",
                  "how vexingly quick daft zebras jump",
                  "sphinx of black quartz judge my vow",
                  "the five boxing wizards jump quickly"]


def sync(n=3, gap=4.0):
    return [{"kind": "sync", "label": "sync", "dur": gap} for _ in range(n)]


def gesture_block(gestures, reps, prep=1.0, hold=2.0, rest=2.0, with_rest=True, seed=0):
    """`reps` rounds; each round has every gesture once (plus a 'rest' null trial) in random order."""
    rng = random.Random(seed)
    steps = []
    labels = list(gestures) + (["rest"] if with_rest else [])
    for r in range(reps):
        order = labels[:]
        rng.shuffle(order)
        for g in order:
            steps.append({"kind": "gesture", "label": g, "prep": prep, "hold": hold, "rest": rest, "rep": r})
    return steps


def mvc_block(reps=2, hold=3.0, rest=5.0):
    steps = []
    for _ in range(reps):
        for lab in ("mvc_fist", "mvc_open"):
            steps.append({"kind": "mvc", "label": lab, "prep": 2.0, "hold": hold, "rest": rest})
    return steps


def build(name, reps=None, seed=0):
    """Named protocols. Durations are approximate (see the docs table)."""
    if name == "quick":  # ~2.5 min smoke test
        steps = sync() + [{"kind": "rest", "label": "rest", "dur": 10.0}] + mvc_block(1) + \
            gesture_block(GESTURES_BASIC, reps or 3, seed=seed) + sync()
    elif name == "basic":  # ~9 min: rest, MVC, 6 postures + rest x 10
        steps = sync() + [{"kind": "rest", "label": "rest", "dur": 30.0}] + mvc_block(2) + \
            gesture_block(GESTURES_BASIC, reps or 10, seed=seed) + sync()
    elif name == "meta":  # ~8 min: MVC, 7 micro-gestures + rest x 15, one action per cue
        steps = sync() + [{"kind": "rest", "label": "rest", "dur": 20.0}] + mvc_block(1) + \
            gesture_block(GESTURES_META, reps or 15, prep=0.8, hold=1.0, rest=1.5, seed=seed) + sync()
    elif name == "pinch":  # ~4 min: slow force ramps to 30 % and 60 % MVC
        steps = sync() + mvc_block(1)
        for r in range(reps or 4):
            for lab in ("pinch_ramp_index", "pinch_ramp_middle"):
                for peak in (0.3, 0.6):
                    steps.append({"kind": "ramp", "label": lab, "prep": 1.5, "hold": 6.0, "rest": 3.0,
                                  "peak": peak, "rep": r})
        steps += sync()
    elif name == "handwriting":
        steps = sync() + [{"kind": "text", "label": "handwrite", "text": p, "rep": r}
                          for r in range(reps or 2) for p in HANDWRITING_PROMPTS] + sync()
    elif name == "typing":
        steps = sync() + [{"kind": "typing", "label": "typing", "text": p, "rep": r}
                          for r in range(reps or 2) for p in TYPING_PROMPTS] + sync()
    else:
        raise ValueError(f"unknown protocol {name!r}; choose from {PROTOCOLS}")
    return steps


PROTOCOLS = ("quick", "basic", "meta", "pinch", "handwriting", "typing")


def duration(steps):
    """Scripted duration in s (user-paced text/typing steps counted as 10 s)."""
    d = 0.0
    for s in steps:
        d += s.get("dur", 0) + s.get("prep", 0) + s.get("hold", 0) + s.get("rest", 0)
        d += 10.0 if s["kind"] in ("text", "typing") else 0
    return d
