"""Prompt-driven data collection. Shows what to do, when, and writes <out>.labels.json with
host-clock times for every prompt. The recorder runs separately and writes <out>.npz;
analysis.align matches the two through the band's marker button.

  terminal 1:  python3 host/neurband_rec.py --udp -o data/u1_d1_s1_basic.npz
  terminal 2:  python3 -m analysis collect basic --out data/u1_d1_s1_basic [--gui]

At the start and end of every run the script asks for 3 presses of the band's marker
button, one per beep. Press it as soon as you see the cue: each press puts a marker in the
recording, and the cue/press pairs give the host->device clock offset (and drift).
--mark-udp HOST:PORT also sends 'MARK <label>' datagrams at every cue, for a recorder
that stores software markers (recommended for the rev C BLE recorder; the rev A/B
recorder ignores them).
"""
import json
import os
import socket
import sys
import time

from . import protocol as P
from .recording import save_labels


# ------------------------------------------------------------------ user interfaces
class TerminalUI:
    """Plain ANSI terminal. Typing captures key presses only (no release times)."""

    COLORS = {"go": "\033[1;42;30m", "ready": "\033[1;43;30m", "rest": "\033[1;44;37m",
              "sync": "\033[1;45;37m", "info": "\033[1m"}

    def __init__(self, now=time.time, sleep=time.sleep):
        self.now, self._sleep = now, sleep

    def show(self, title, sub="", style="info"):
        sys.stdout.write("\033[2J\033[H\n\n")
        sys.stdout.write(f"   {self.COLORS.get(style, '')}  {title.upper()}  \033[0m\n\n   {sub}\n\n")
        sys.stdout.flush()

    def beep(self):
        sys.stdout.write("\a")
        sys.stdout.flush()

    def wait(self, dur, bar=None):
        """Wait dur s, drawing a countdown or (bar(u) -> 0..1) a force-target bar."""
        t_end = self.now() + dur
        while True:
            left = t_end - self.now()
            if left <= 0:
                break
            u = 1 - left / dur if dur else 1
            if bar is not None:
                k = int(40 * bar(u))
                sys.stdout.write(f"\r   target [{'#' * k}{' ' * (40 - k)}]  ")
            else:
                sys.stdout.write(f"\r   {left:4.1f} s ")
            sys.stdout.flush()
            self._sleep(min(0.05, left))
        sys.stdout.write("\r" + " " * 60 + "\r")

    def wait_enter(self, msg="press Enter when done"):
        input(f"   ({msg}) ")
        return self.now()

    def type_text(self, text):
        """Return [(char, t_press, None)], finished by Enter. Needs a real tty."""
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        keys = []
        sys.stdout.write("   > ")
        sys.stdout.flush()
        try:
            tty.setcbreak(fd)
            while True:
                ch = sys.stdin.read(1)
                t = self.now()
                if ch in ("\n", "\r"):
                    break
                keys.append((ch, t, None))
                sys.stdout.write("\b \b" if ch == "\x7f" else ch)
                sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return keys

    def close(self):
        print()


class TkUI(TerminalUI):
    """Big full-window prompts; typing logs press and release times (like emg2qwerty)."""

    BG = {"go": "#1e8e3e", "ready": "#f9ab00", "rest": "#1a73e8", "sync": "#a142f4", "info": "#202124"}

    def __init__(self, now=time.time, sleep=time.sleep):
        super().__init__(now, sleep)
        import tkinter as tk
        self.tk = tk
        self.root = tk.Tk()
        self.root.title("neurband collect")
        self.root.geometry("900x500")
        self.title = tk.Label(self.root, font=("Helvetica", 54, "bold"), fg="white")
        self.sub = tk.Label(self.root, font=("Helvetica", 22), fg="white", wraplength=850)
        self.bar = tk.Canvas(self.root, height=40, highlightthickness=0)
        self.entry = tk.Label(self.root, font=("Courier", 22), fg="white")
        for w in (self.title, self.sub, self.bar, self.entry):
            w.pack(fill="x", pady=12)
        self._keys, self._enter = [], False
        self.root.bind("<KeyPress>", self._press)
        self.root.bind("<KeyRelease>", self._release)

    def _press(self, ev):
        t = self.now()
        if ev.keysym == "Return":
            self._enter = True
        elif ev.keysym not in ("Shift_L", "Shift_R"):
            self._keys.append([ev.char or ev.keysym, t, None, ev.keysym])
            self.entry.config(text=self.entry.cget("text") + (ev.char if ev.char.isprintable() else ""))

    def _release(self, ev):
        for k in reversed(self._keys):
            if k[3] == ev.keysym and k[2] is None:
                k[2] = self.now()
                break

    def show(self, title, sub="", style="info"):
        bg = self.BG.get(style, "#202124")
        for w in (self.root, self.title, self.sub, self.bar, self.entry):
            w.config(bg=bg)
        self.title.config(text=title.upper())
        self.sub.config(text=sub)
        self.bar.delete("all")
        self.entry.config(text="")
        self.root.update()

    def beep(self):
        self.root.bell()

    def wait(self, dur, bar=None):
        t_end = self.now() + dur
        while self.now() < t_end:
            u = 1 - (t_end - self.now()) / dur if dur else 1
            self.bar.delete("all")
            w = self.bar.winfo_width()
            frac = bar(u) if bar is not None else 1 - u
            self.bar.create_rectangle(0, 0, int(w * frac), 40, fill="white", width=0)
            self.root.update()
            self._sleep(0.01)

    def wait_enter(self, msg="press Enter when done"):
        self.sub.config(text=self.sub.cget("text") + f"\n({msg})")
        self._enter = False
        while not self._enter:
            self.root.update()
            self._sleep(0.01)
        return self.now()

    def type_text(self, text):
        self._keys, self._enter = [], False
        while not self._enter:
            self.root.update()
            self._sleep(0.002)
        return [tuple(k[:3]) for k in self._keys]

    def close(self):
        self.root.destroy()


# ------------------------------------------------------------------ runner
def run(steps, ui, out, meta=None, mark=None, scale=1.0):
    """Run the protocol steps, writing <out>.labels.json after every step. `scale`
    multiplies all scripted durations (tests use a tiny value). Returns the labels dict."""
    labels = {"version": 1, "clock": "host time.time()", "started": ui.now(), "events": [], **(meta or {})}
    path = out + ".labels.json"

    def cue(label):
        if mark:
            mark(label)

    for i, s in enumerate(steps):
        k, lab = s["kind"], s["label"]
        ev = {"kind": k, "label": lab, "step": i, "rep": s.get("rep", 0)}
        txt = P.INSTRUCTIONS.get(lab, lab)
        if k == "sync":
            ui.show("press the band button", "one press, now", "sync")
            ui.beep()
            ev["t_cue"] = ev["t_start"] = ui.now()
            cue("sync")
            ui.wait(s["dur"] * scale)
            ev["t_end"] = ui.now()
        elif k == "rest":
            ui.show("relax", P.INSTRUCTIONS["rest"], "rest")
            ev["t_cue"] = ev["t_start"] = ui.now()
            cue(lab)
            ui.wait(s["dur"] * scale)
            ev["t_end"] = ui.now()
        elif k in ("gesture", "mvc", "ramp"):
            ui.show(f"next: {lab.replace('_', ' ')}", txt, "ready")
            ev["t_cue"] = ui.now()
            ui.wait(s["prep"] * scale)
            ui.show(lab.replace("_", " "), txt + ("  (hold)" if k == "gesture" and lab not in P.GESTURES_META
                                                 else "  (once)" if k == "gesture" else ""), "go")
            ev["t_start"] = ui.now()
            cue(lab)
            if k == "ramp":
                peak = s.get("peak", 0.5)
                ev["peak"] = peak
                ui.wait(s["hold"] * scale, bar=lambda u: peak * (1 - abs(2 * u - 1)))
            else:
                ui.wait(s["hold"] * scale)
            ev["t_end"] = ui.now()
            ui.show("relax", "", "rest")
            ui.wait(s["rest"] * scale)
        elif k == "text":
            ui.show("write by hand:", s["text"], "go")
            ev["t_cue"] = ev["t_start"] = ui.now()
            ev["text"] = s["text"]
            cue(lab)
            ev["t_end"] = ui.wait_enter()
        elif k == "typing":
            ui.show("type:", s["text"], "go")
            ev["t_cue"] = ev["t_start"] = ui.now()
            ev["text"] = s["text"]
            cue(lab)
            ev["keys"] = ui.type_text(s["text"])
            ev["t_end"] = ui.now()
        labels["events"].append(ev)
        save_labels(path, labels)
    labels["finished"] = ui.now()
    save_labels(path, labels)
    return labels


def udp_marker(target):
    host, port = target.rsplit(":", 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return lambda label: sock.sendto(f"MARK {label}\n".encode(), (host, int(port)))


def main(args):
    steps = P.build(args.protocol, reps=args.reps, seed=args.seed)
    out = args.out[:-4] if args.out.endswith(".npz") else args.out
    if os.path.exists(out + ".labels.json") and not args.force:
        sys.exit(f"{out}.labels.json exists (use --force to overwrite)")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    meta = {"protocol": args.protocol, "session": args.session or os.path.basename(out),
            "subject": args.subject, "donning": args.donning, "posture": args.posture,
            "arm": args.arm, "notes": args.notes, "steps": steps}
    print(f"protocol '{args.protocol}': {len(steps)} steps, about {P.duration(steps) / 60:.1f} min")
    print(f"start the recorder now, e.g.\n  python3 host/neurband_rec.py --udp -o {out}.npz")
    input("then press Enter here to begin ")
    ui = TkUI() if args.gui else TerminalUI()
    try:
        run(steps, ui, out, meta, udp_marker(args.mark_udp) if args.mark_udp else None, args.scale)
    finally:
        ui.close()
    print(f"done: wrote {out}.labels.json. Stop the recorder (Ctrl-C) now.\n"
          f"check it:  python3 -m analysis report {out}.npz")
