"""Overlay In2.Cu (solid) and B.Cu (dashed outline) electrode-region routing with the worst aggressors
highlighted. Output: sim/preorder/out/hotspots_in2_bcu.png and hotspots_fcu.png."""
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
HI = {"/IMU_INT": "#e41a1c", "/I2C_SCL": "#ff7f00", "/I2C_SDA": "#a65628", "VBAT": "#4daf4a",
      "+3V3": "#66c2a5", "+3V3A": "#1b9e77", "VCHG": "#984ea3", "/BUTTON": "#999999", "/NRST": "#bbbbbb",
      "/SWDCLK": "#cccccc", "/SWDIO": "#cccccc", "/ADC_START": "#f781bf", "/ADC_DRDY": "#f781bf",
      "/SPI_SCK": "#f781bf", "/SPI_MISO": "#f781bf", "/SPI_MOSI": "#f781bf", "/ADC_CS": "#f781bf"}


def is_e(n):
    return bool(re.fullmatch(r"/E\d[PN]", n) or n.startswith("Net-(RN") or n == "/BIAS_E")


def draw(ax, b, layer, solid, lw_scale=1.0):
    for t in b.tracks:
        if t["layer"] != layer:
            continue
        n = t["net"]
        if is_e(n):
            c = "#08306b" if n != "/BIAS_E" else "#6a51a3"
        elif n in HI:
            c = HI[n]
        else:
            continue
        g = LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).buffer(t["w"] / 2, 4)
        if g.geom_type != "Polygon":
            continue
        if solid:
            ax.add_patch(MPoly(list(g.exterior.coords), closed=True, fc=c, ec="none", alpha=0.85))
        else:
            ax.add_patch(MPoly(list(g.exterior.coords), closed=True, fc=c, ec="k", lw=0.3, alpha=0.35, hatch="////"))


def label_nets(ax, b, layers, nets):
    done = set()
    for t in b.tracks:
        if t["layer"] in layers and t["net"] in nets and (t["net"], t["layer"]) not in done:
            L = ((t["x2"] - t["x1"]) ** 2 + (t["y2"] - t["y1"]) ** 2) ** 0.5
            if L > 1.5:
                ax.text((t["x1"] + t["x2"]) / 2, (t["y1"] + t["y2"]) / 2,
                        t["net"].replace("Net-(", "").replace(")", "").replace("/", "") + ("" if t["layer"] == "In2.Cu" else " (B)"),
                        fontsize=5, color="k", rotation=0, ha="center", va="center",
                        bbox=dict(fc="white", ec="none", alpha=0.6, pad=0.2))
                done.add((t["net"], t["layer"]))


def main():
    b = Board(PCB)
    fig, ax = plt.subplots(figsize=(10, 9))
    draw(ax, b, "In2.Cu", True)
    draw(ax, b, "B.Cu", False)
    for v in b.vias:
        if is_e(v["net"]) or v["net"] in HI:
            ax.add_patch(plt.Circle((v["x"], v["y"]), 0.225, fc="none", ec="k", lw=0.4))
    nets = {t["net"] for t in b.tracks if is_e(t["net"])} | set(list(HI)[:4])
    label_nets(ax, b, ("In2.Cu", "B.Cu"), nets)
    ax.set_xlim(6, 28.7)
    ax.set_ylim(26.5, 8)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.2)
    ax.set_title("In2.Cu (solid) over B.Cu (hatched), 0.1 mm apart. Navy = electrode nets (J1 and ADS side), purple = BIAS_E,\n"
                 "red = IMU_INT, orange = I2C_SCL, brown = I2C_SDA, green = VBAT, teal = +3V3/+3V3A, violet = VCHG", fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    fig.savefig(os.path.join(HERE, "out", "hotspots_in2_bcu.png"), dpi=140)
    print("written")


if __name__ == "__main__":
    main()
