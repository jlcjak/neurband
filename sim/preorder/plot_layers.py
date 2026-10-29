"""Plot each copper layer of the rev C main board with nets coloured by class (review aid).

Output: sim/preorder/build/layers_<layer>.png (gitignored). Run with the sim/preorder venv:
    sim/preorder/build/.venv/bin/python sim/preorder/plot_layers.py
"""
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from shapely.geometry import LineString

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pcbgeom import Board  # noqa: E402

PCB = os.path.join(HERE, "../../boards/neurband_c/neurband_c.kicad_pcb")
OUT = os.path.join(HERE, "build")


def klass(net):
    if re.fullmatch(r"/E\dP|/E\dN", net):
        return "elec_j1"
    if net.startswith("Net-(RN"):
        return "elec_ads"
    if net in ("/BIAS_E", "Net-(U2-RLDOUT)", "Net-(U2-RLDINV)", "/RLDREF"):
        return "bias"
    if net in ("GND",):
        return "gnd"
    if net in ("+3V3", "+3V3A", "VBAT", "VCHG") or "VCAP" in net or "VREFP" in net or net.startswith("/DEC"):
        return "power"
    if net in ("Net-(AE1-A)", "Net-(U1-ANT)", "Net-(C22-Pad1)", "Net-(U1-XC1)", "Net-(U1-XC2)"):
        return "rf"
    return "digital"


COL = {"elec_j1": "#d62728", "elec_ads": "#ff7f0e", "bias": "#9467bd", "gnd": "#cccccc", "power": "#2ca02c",
       "rf": "#e377c2", "digital": "#1f77b4"}


def main():
    b = Board(PCB)
    os.makedirs(OUT, exist_ok=True)
    for layer in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"):
        fig, ax = plt.subplots(figsize=(11, 10.5))
        for z in b.zones:
            for fl, pts in z["fills"]:
                if fl == layer:
                    ax.add_patch(MPoly(pts, closed=True, fc="#eeeeee", ec="#999999", lw=0.3))
            if z["keepout"] and (layer in z["layers"]) and z["outline"]:
                ax.add_patch(MPoly(z["outline"], closed=True, fill=False, ec="k", ls="--", lw=0.6))
        for t in b.tracks:
            if t["layer"] != layer:
                continue
            c = COL[klass(t["net"])]
            g = LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).buffer(t["w"] / 2, 4)
            if g.geom_type == "Polygon":
                ax.add_patch(MPoly(list(g.exterior.coords), closed=True, fc=c, ec="none", alpha=0.9))
        for p in b.pads:
            if layer in p["layers"] or "*.Cu" in p["layers"]:
                g = b.pad_poly(p)
                ax.add_patch(MPoly(list(g.exterior.coords), closed=True, fc=COL[klass(p["net"])] if p["net"] else "#000",
                                   ec="k", lw=0.2, alpha=0.6))
        for v in b.vias:
            ax.add_patch(plt.Circle((v["x"], v["y"]), v["size"] / 2, fc=COL[klass(v["net"])], ec="k", lw=0.3))
        for ref, f in b.fps.items():
            if f["layer"] == ("B.Cu" if layer == "B.Cu" else "F.Cu"):
                ax.text(f["x"], f["y"], ref, fontsize=6, ha="center", va="center")
        ax.set_xlim(-0.5, 29.2)
        ax.set_ylim(27.5, -4)
        ax.set_aspect("equal")
        ax.grid(True, lw=0.2)
        ax.set_xticks(range(0, 30, 1))
        ax.set_yticks(range(-3, 28, 1))
        ax.tick_params(labelsize=6)
        ax.set_title(f"neurband rev C {layer}: red=electrode (J1 side), orange=electrode (ADS side), "
                     "purple=bias/RLD, blue=digital, green=power, pink=RF/xtal", fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, f"layers_{layer.replace('.', '_')}.png"), dpi=130)
        plt.close(fig)
    print("written", OUT)


if __name__ == "__main__":
    main()
