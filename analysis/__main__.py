"""Command line:  python3 -m analysis <command> ...

  protocols                          list collection protocols and their length
  collect PROTOCOL --out PATH        run a prompted session (see analysis/collect.py)
  report REC.npz [...]               signal-quality report (+ --json)
  train REC.npz REC.npz ...          baseline classifier, leave-one-session-out
  synth OUT_DIR                      write synthetic recordings to try everything
"""
import argparse
import json
import sys

import numpy as np


def cmd_protocols(a):
    from . import protocol as P
    for name in P.PROTOCOLS:
        s = P.build(name)
        print(f"{name:<12} {len(s):>4} steps  ~{P.duration(s) / 60:5.1f} min")


def cmd_collect(a):
    from .collect import main as collect_main
    collect_main(a)


def cmd_report(a):
    from .quality import format_report, report
    from .recording import load
    out = []
    for p in a.files:
        r = report(load(p), mains=a.mains)
        out.append(r)
        if not a.json:
            print(format_report(r) + "\n")
    if a.json:
        print(json.dumps(out, indent=1, default=float))


def cmd_train(a):
    from . import dataset, model
    rot = tuple(float(v) for v in a.rotate_aug.split(",")) if a.rotate_aug else (0.0,)
    classes = a.classes.split(",") if a.classes else None
    test = [dataset.windows(p, a.win_ms, a.hop_ms, mains=a.mains, classes=classes) for p in a.files]
    for s in test:
        print(f"{s['session']}: {len(s['y'])} windows, {s['n_used']}/{s['n_trials']} trials with a detected movement")
    train = None
    if rot != (0.0,):
        train = [dataset.windows(p, a.win_ms, a.hop_ms, mains=a.mains, classes=classes, rotations=rot) for p in a.files]
    if len(test) < 2:
        sys.exit("need at least 2 sessions (separate donnings) for leave-one-session-out")
    r = model.loso(test, a.model, train_sessions=train)
    print(model.format_loso(r))


def cmd_synth(a):
    from . import synth
    faults = {}
    for f in a.fault or []:
        ch, kind = f.split(":")
        faults[int(ch) - 1] = kind
    paths = synth.make_dataset(a.out_dir, a.sessions, a.protocol, a.fs, a.seed, faults=faults or None)
    print("\n".join(paths))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m analysis", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("protocols").set_defaults(fn=cmd_protocols)

    c = sub.add_parser("collect", help="prompted collection session")
    c.add_argument("protocol")
    c.add_argument("--out", required=True, help="base path; writes OUT.labels.json, record to OUT.npz")
    c.add_argument("--gui", action="store_true", help="tkinter window (best for typing)")
    c.add_argument("--reps", type=int)
    c.add_argument("--seed", type=int, default=0)
    c.add_argument("--session", help="session id (default: basename of --out)")
    c.add_argument("--subject", default="u1")
    c.add_argument("--donning", type=int, default=1, help="donning number this day")
    c.add_argument("--posture", default="seated, forearm on table")
    c.add_argument("--arm", default="right")
    c.add_argument("--notes", default="")
    c.add_argument("--mark-udp", metavar="HOST:PORT")
    c.add_argument("--scale", type=float, default=1.0, help="time scale for all durations (testing)")
    c.add_argument("--force", action="store_true")
    c.set_defaults(fn=cmd_collect)

    r = sub.add_parser("report", help="signal-quality report")
    r.add_argument("files", nargs="+")
    r.add_argument("--mains", type=float, help="50 or 60 (default: from the recording, else 50)")
    r.add_argument("--json", action="store_true")
    r.set_defaults(fn=cmd_report)

    t = sub.add_parser("train", help="baseline classifier, leave-one-session-out")
    t.add_argument("files", nargs="+", help="one .npz per session (with .labels.json)")
    t.add_argument("--model", choices=("lda", "logreg"), default="lda")
    t.add_argument("--win-ms", type=float, default=200.0)
    t.add_argument("--hop-ms", type=float, default=50.0)
    t.add_argument("--mains", type=float)
    t.add_argument("--classes", help="comma-separated subset of labels")
    t.add_argument("--rotate-aug", help="training rotations in pods, e.g. -0.5,0,0.5")
    t.set_defaults(fn=cmd_train)

    s = sub.add_parser("synth", help="synthetic recordings")
    s.add_argument("out_dir")
    s.add_argument("--sessions", type=int, default=3)
    s.add_argument("--protocol", default="basic")
    s.add_argument("--fs", type=int, default=2000)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--fault", action="append", help="CH:KIND, kind in flat/leadoff/clip/noisy/line (1-based ch)")
    s.set_defaults(fn=cmd_synth)

    a = ap.parse_args(argv)
    np.set_printoptions(suppress=True)
    a.fn(a)


if __name__ == "__main__":
    main()
