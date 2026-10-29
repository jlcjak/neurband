"""neurband rev C: 8-channel sEMG band core, nRF52832 BLE + one ADS1298. Generates neurband_c.kicad_sch.

Cost-first: one AFE, chip-down nRF52832 with a printed antenna (TI SWRA117D), a single basic LDO,
basic/preferred passives wherever the fab stocks them. Run: python3 gen_c_sch.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../tools"))
from schgen import Schematic  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
s = Schematic("neurband rev C: 8-ch sEMG, nRF52832 BLE, ADS1298", paper="User 420 310", project="neurband_c")

FP = {
    "R0402": "Resistor_SMD:R_0402_1005Metric",
    "C0402": "Capacitor_SMD:C_0402_1005Metric",
    "C0603": "Capacitor_SMD:C_0603_1608Metric",
    "L0402": "Inductor_SMD:L_0402_1005Metric",
    "LED": "LED_SMD:LED_0603_1608Metric",
    "RN": "neurband:R_Array_Convex_4x0603_FabZero",
}
# value -> (footprint, MPN, fab part #). Basic/preferred parts unless noted.
PARTS = {
    "R:10": ("R0402", "0402WGF100JTCE", "C25077"),
    "R:1k": ("R0402", "0402WGF1001TCE", "C11702"),
    "R:10k": ("R0402", "0402WGF1002TCE", "C25744"),
    "R:100k": ("R0402", "0402WGF1003TCE", "C25741"),
    "R:1M": ("R0402", "0402WGF1004TCE", "C26083"),
    "R:0": ("R0402", "0402WGF0000TCE", "C17168"),
    "C:100nF": ("C0402", "CL05B104KO5NNNC", "C1525"),
    "C:1uF": ("C0402", "CL05A105KA5NQNC", "C52923"),
    "C:10uF": ("C0603", "CL10A106KP8NNNC", "C19702"),     # 0603 10 V: ~2x the in-circuit C of 0402 6.3 V at 2.4-3.3 V
    "C:22uF": ("C0603", "CL10A226MQ8NRNC", "C59461"),
    "C:4.7nF": ("C0402", "0402B472K500NT", "C1538"),       # basic
    "C:12pF": ("C0402", "0402CG120J500NT", "C1547"),
    "C:100pF": ("C0402", "0402CG101J500NT", "C1546"),
    "C:1.0pF": ("C0402", "0402CG1R0C500NT", "C1550"),
    "C:0.8pF": ("C0402", "0402CG0R8B500NT", "C285068"),    # extended (RF match)
    "C:DNP": ("C0402", "", ""),
    "L:3.9nH": ("L0402", "SDCL1005C3N9STDF", "C14033"),   # preferred (RF match)
}
_n = {"R": 0, "C": 0, "L": 0}


def fields(mpn, lcsc):
    return {"MPN": mpn, "LCSC": lcsc}


def passive(kind, value, x, y, rot=0, text="right", ref=None):
    """ref=None numbers in drawing order; parts added after the first layout get an explicit ref
    (C33, ...) so existing references, and the UUIDs derived from them, never shift."""
    if ref is None:
        _n[kind] += 1
        ref = f"{kind}{_n[kind]}"
    fp, mpn, lcsc = PARTS[f"{kind}:{value}"]
    lib = {"R": "Device:R_Small_US", "C": "Device:C_Small", "L": "Device:L_Small"}[kind]
    p = s.add(lib, ref, value if value != "DNP" else "DNP", x, y, rot, footprint=FP[fp],
              fields=fields(mpn, lcsc), dnp=(value == "DNP"))
    if rot == 0:
        sx, j = (1.9, "left") if text == "right" else (-1.9, "right")
        p.ref_at = (p.x + sx, p.y - 0.6, 0, j)
        p.val_at = (p.x + sx, p.y + 1.9, 0, j)
    else:
        p.ref_at = (p.x, p.y - 2.9, 0)
        p.val_at = (p.x, p.y + 3.4, 0)
    return p


def cap_down(x, y, value, gnd=True, text="left"):
    """Vertical cap whose top pin is (x, y); GND symbol at its bottom."""
    c = passive("C", value, x, y + 2.54, text=text)
    if gnd:
        s.power("GND", x, y + 5.08)
    return c


def bank(x, y, net, values, pitch=7.62, refs=None):
    refs = refs or [None] * len(values)
    caps = [passive("C", v, x + i * pitch, y, ref=r) for i, (v, r) in enumerate(zip(values, refs))]
    x_end = x + (len(values) - 1) * pitch
    s.wire([(x - 2.54, y - 2.54), (x_end, y - 2.54)])
    s.wire([(x - 2.54, y + 2.54), (x_end, y + 2.54)])
    for i in range(1, len(values) - 1):
        s.junction(x + i * pitch, y - 2.54)
        s.junction(x + i * pitch, y + 2.54)
    s.power(net, x - 2.54, y - 2.54)
    s.power("GND", x - 2.54, y + 2.54)
    return caps


COL = {"afe": "40 120 200", "mcu": "200 120 40", "rf": "160 60 160", "pwr": "200 50 50", "conn": "60 160 80"}

# ============================================================ electrode connector
J1X, J1Y = 33.02, 99.06
j1 = s.add("Connector_Generic:Conn_01x20", "J1", "FPC 20p 0.5mm (electrode flex)", J1X, J1Y, mirror="y",
           footprint="neurband:XUNPU_FPC-05F-20PH20_Centroid",
           fields=fields("FPC-05F-20PH20", "C2856803"))
j1.ref_at = (J1X, J1Y - 27.94, 0)
j1.val_at = (J1X, J1Y + 29.21, 0)
J1_MAP = {1: "GND", 2: "BIAS_E", 19: "BIAS_E", 20: "GND"}
for ch in range(8):
    J1_MAP[3 + 2 * ch] = f"E{ch + 1}P"
    J1_MAP[4 + 2 * ch] = f"E{ch + 1}N"
for n, net in sorted(J1_MAP.items()):
    if net == "GND":
        x, y, _ = j1.pin(str(n))
        s.wire([(x, y), (x + 15.24, y)])
        s.power("GND", x + 15.24, y)
    else:
        s.pin_label(j1, str(n), net)
s.rect(15.24, 63.5, 63.5, 139.7, fill=COL["conn"], title="Electrode flex")
s.text("Pod n: EnP proximal, EnN distal (20 mm apart),\nBIAS_E = middle pad of every pod.", 17.78, 135.89)

# ============================================================ ADS1298 (8 channels)
AX, AY = 152.4, 104.14
u2 = s.add("Analog_ADC:ADS1298xPAG", "U2", "ADS1298IPAGR", AX, AY,
           footprint="neurband:TQFP-64_10x10mm_P0.5mm_FabZero", fields=fields("ADS1298IPAGR", "C527440"))
u2.ref_at = (AX - 15.24, AY - 45.72, 0, "left")
u2.val_at = (AX + 2.54, AY - 45.72, 0, "left")
RN = {"n": 0, "u": 0}
for i in range(8):
    for pol in "PN":
        x, y, _ = u2.pin(f"IN{i + 1}{pol}")
        if RN["u"] % 4 == 0:
            RN["n"] += 1
        unit = RN["u"] % 4 + 1
        RN["u"] += 1
        cx = x - 2.54 - 3.81
        r = s.add("Device:R_Pack04_Split", f"RN{RN['n']}", "10k", cx, y, 90, unit=unit, footprint=FP["RN"],
                  fields=fields("4D03WGJ0103T5E", "C29718"))
        r.ref_at = (cx, y - 1.0, 0)
        r.fsize = 1.0
        r.hide_value = True
        s.wire([(x, y), (x - 2.54, y)])
        s.wire([(cx - 3.81, y), (cx - 6.35, y)])
        s.label(f"E{i + 1}{pol}", cx - 6.35, y, 180)
# reference + bypass (datasheet fig. 106)
gx, gy, _ = u2.pin("VREFN")
s.wire([(gx, gy), (gx - 2.54, gy)])
s.power("GND", gx - 2.54, gy)
for pin, dx, val in (("VREFP", 7.62, "100nF"), ("VCAP4", 27.94, "1uF"), ("VCAP3", 38.1, "1uF"),
                     ("VCAP2", 48.26, "1uF"), ("VCAP1", 58.42, "22uF")):
    x, y, _ = u2.pin(pin)
    s.wire([(x, y), (x - dx, y)])
    cap_down(x - dx, y, val)
x, y, _ = u2.pin("VREFP")
s.junction(x - 7.62, y)
s.wire([(x - 7.62, y), (x - 17.78, y)])
cap_down(x - 17.78, y, "10uF")
# supplies
ax, ay, _ = u2.pin("19")
a1x, a1y, _ = u2.pin("AVDD1")
s.wire([(ax, ay), (a1x, a1y)])
s.wire([(ax, ay), (ax, ay - 2.54)])
s.power("+3V3A", ax, ay - 2.54, lib="power:+3V3")
x, y, _ = u2.pin("48")
s.wire([(x, y), (x, y - 2.54)])
s.power("+3V3", x, y - 2.54)
g1x, g1y, _ = u2.pin("20")
g3x, g3y, _ = u2.pin("33")
s.wire([(g1x, g1y), (g3x, g3y)])
s.junction(AX, g1y)
s.wire([(AX, g1y), (AX, g1y + 2.54)])
s.power("GND", AX, g1y + 2.54)
bank(184.15, 50.8, "+3V3A", ["1uF", "100nF", "100nF"])
bank(195.58, 83.82, "+3V3A", ["1uF"], refs=["C33"])
s.text("C33: local to AVDD1/AVSS1\n(pins 54/53, charge pump)", 201.93, 91.44)
bank(209.55, 50.8, "+3V3", ["1uF", "100nF"])
# unused / fixed pins
for p in ("WCT", "27", "29", "CLK"):
    s.pin_nc(u2, p)
t1x, t1y, _ = u2.pin("17")
t2x, t2y, _ = u2.pin("18")
s.wire([(t1x, t1y), (t1x + 5.08, t1y), (t2x + 5.08, t2y), (t2x, t2y)])
s.junction(t1x + 5.08, t1y)
s.wire([(t1x + 5.08, t1y), (t1x + 15.24, t1y)])
s.power("+3V3A", t1x + 15.24, t1y, lib="power:+3V3")
rail = []
for p in ("GPIO1", "GPIO2", "GPIO3", "GPIO4", "DAISY_IN"):
    px, py, _ = u2.pin(p)
    s.wire([(px, py), (px + 5.08, py)])
    rail.append((px + 5.08, py))
s.wire([rail[0], rail[-1]])
for p in rail[:-1]:
    s.junction(*p)
s.wire([rail[0], (rail[0][0] + 7.62, rail[0][1])])
s.power("GND", rail[0][0] + 7.62, rail[0][1])
rx, ry, _ = u2.pin("RESV1")
s.wire([(rx, ry), (rx + 5.08, ry)])
s.power("GND", rx + 5.08, ry)
cx_, cy_, _ = u2.pin("CLKSEL")
s.wire([(cx_, cy_), (cx_ + 17.78, cy_)])
s.power("+3V3", cx_ + 17.78, cy_)  # internal 2.048 MHz oscillator
for p, net in (("SCLK", "SPI_SCK"), ("DIN", "SPI_MOSI"), ("DOUT", "SPI_MISO"), ("~{CS}", "ADC_CS"),
               ("START", "ADC_START"), ("~{DRDY}", "ADC_DRDY"), ("~{PWDN}", "ADC_PWDN"), ("~{RESET}", "ADC_PWDN"),
               ("RLDIN", "RLD_DRV")):
    s.pin_label(u2, p, net)
# bias (right-leg) drive: 1M || 4.7nF feedback, 100k to the bias pads
ox, oy, _ = u2.pin("RLDOUT")
ix, iy, _ = u2.pin("RLDINV")
s.wire([(ox, oy), (ox + 30.48, oy)])
s.wire([(ix, iy), (ix + 27.94, iy)])
r = passive("R", "1M", ox + 20.32, oy + 2.54, text="left")
c = passive("C", "4.7nF", ox + 27.94, oy + 2.54)  # 1M x 4.7nF = 34 Hz: stability margin (docs/science/signal_chain.md)
for xx in (ox + 20.32, ox + 27.94):
    s.junction(xx, oy)
s.junction(ox + 20.32, iy)
passive("R", "100k", ox + 35.56, oy, 90)
s.wire([(ox + 30.48, oy), (ox + 33.02, oy)])
s.wire([(ox + 38.1, oy), (ox + 40.64, oy)])
s.label("BIAS_E", ox + 40.64, oy, 0)
# RLDIN (pin 62) sits on the amplifier side of the 100k, never directly on the bias pads (ESD)
s.label("RLD_DRV", ox + 12.7, oy, 0)
# 12 pF C0G from the bias bus to GND at the 100k: RF shunt for the 170 mm bias bus (< 0.5 deg RLD margin)
s.junction(ox + 40.64, oy)
s.wire([(ox + 40.64, oy), (ox + 40.64, oy + 2.54)])
cb = passive("C", "12pF", ox + 40.64, oy + 5.08, ref="C34")
s.power("GND", ox + 40.64, oy + 7.62)
s.rect(68.58, 35.56, 226.06, 160.02, fill=COL["afe"], title="Analog front end: ADS1298, 8 bipolar channels + bias drive")
s.text("RN1-RN4: 4x 10 kOhm arrays in series with every electrode (ESD current limit).", 71.12, 157.48)

# ============================================================ nRF52832
NX, NY = 309.88, 104.14
u1 = s.add("MCU_Nordic:nRF52832-QFxx", "U1", "nRF52832-QFAA", NX, NY,
           footprint="neurband:QFN-48-1EP_6x6mm_P0.4mm_EP4.6x4.6mm_FabZero", fields=fields("NRF52832-QFAA-R", "C77540"))
u1.ref_at = (NX + 7.62, NY - 45.72, 0, "left")
u1.val_at = (NX + 7.62, NY - 43.18, 0, "left")
# supply: VDD with 10uF + 100nF; DEC1 100nF; DEC4 1uF; DEC2/DEC3 per reference; DCC unused (LDO mode)
x, y, _ = u1.pin("13")
s.wire([(x, y), (x, y - 2.54)])
s.power("+3V3", x, y - 2.54)
g = u1.pin("31")
s.wire([(g[0], g[1]), (g[0], g[1] + 2.54)])
s.power("GND", g[0], g[1] + 2.54)
NRF_DEC = {"DEC1": "100nF", "DEC2": None, "DEC3": "100pF", "DEC4": "1uF"}  # Nordic ref.: C4, (C6 n.m.), C7, C10
for k, (pin, val) in enumerate(NRF_DEC.items()):
    x, y, _ = u1.pin(pin)
    if val is None:
        s.noconnect(x, y)
        continue
    s.wire([(x, y), (x, y - 5.08 - 2.54 * k)])
    s.label(pin, x, y - 5.08 - 2.54 * k, 90)
for k, (pin, val) in enumerate([(p, v) for p, v in NRF_DEC.items() if v]):
    cx = 365.76 + k * 10.16
    s.label(pin, cx, 50.8, 90)
    s.wire([(cx, 50.8), (cx, 53.34)])
    passive("C", val, cx, 55.88)
    s.power("GND", cx, 58.42)
s.pin_nc(u1, "DCC")
bank(337.82, 38.1, "+3V3", ["10uF", "100nF", "100nF"])
s.text("VDD: 10uF at pin 48,\n100nF at pins 13 and 36", 360.68, 35.56)
s.text("nRF DEC caps", 363.22, 45.72)
# 32 MHz crystal (8 pF load) with 12 pF caps
xc1 = u1.pin("XC1")
xc2 = u1.pin("XC2")
YX = NX - 40.64
y1 = s.add("Device:Crystal_GND24_Small", "Y1", "32MHz 8pF", YX, (xc1[1] + xc2[1]) / 2, 90,
           footprint="Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm", fields=fields("X201632MKB4SI", "C718072"))
y1.ref_at = (YX + 10.16, y1.y - 2.54, 0, "left")
y1.val_at = (YX + 10.16, y1.y + 3.81, 0, "left")
p1 = y1.pin("1")
p3 = y1.pin("3")
s.wire([(xc1[0], xc1[1]), (p3[0], xc1[1]), (p3[0], p3[1])] if p3[1] < p1[1] else [(xc1[0], xc1[1]), (p1[0], xc1[1]), (p1[0], p1[1])])
s.wire([(xc2[0], xc2[1]), (p1[0], xc2[1]), (p1[0], p1[1])] if p3[1] < p1[1] else [(xc2[0], xc2[1]), (p3[0], xc2[1]), (p3[0], p3[1])])
for yy in (xc1[1], xc2[1]):
    s.wire([(YX, yy), (YX - 7.62, yy)])
    s.junction(YX, yy)
    cap_down(YX - 7.62, yy, "12pF", text="left")
gp = y1.pin("2")
s.wire([(gp[0], gp[1]), (gp[0] + 5.08, gp[1])])
s.power("GND", gp[0] + 5.08, gp[1])
# RF: ANT -> Nordic match (series L, shunt C) -> pi tuning pads (DNP shunts) -> printed antenna
NRF_RF = {"L_series": "3.9nH", "C_shunt_ant": None, "C_shunt_chip": "0.8pF"}  # Nordic ref. config (C3 at ANT/VSS pin 31, L1 series)
ant = u1.pin("ANT")
x0, y0 = ant[0], ant[1]
xs = x0 - 10.16
s.wire([(x0, y0), (xs + 2.54, y0)])
l1 = passive("L", NRF_RF["L_series"], xs, y0, 90)
cs = x0 - 5.08
s.junction(cs, y0)
if NRF_RF["C_shunt_chip"]:
    cap_down(cs, y0, NRF_RF["C_shunt_chip"], text="right")
# pi network for antenna tuning: shunt DNP, series 0R, shunt DNP
xp = xs - 10.16
s.wire([(xs - 2.54, y0), (xp, y0)])
s.junction(xp, y0)
cap_down(xp, y0, "DNP", text="right")
passive("R", "0", xp - 5.08, y0, 90)
s.wire([(xp, y0), (xp - 2.54, y0)])
xq = xp - 10.16
s.wire([(xp - 7.62, y0), (xq, y0)])
s.junction(xq, y0)
cap_down(xq, y0, "DNP", text="right")
ae = s.add("Device:Antenna_Shield", "AE1", "PCB IFA 2.4GHz", xq - 10.16, y0 - 10.16,
           footprint="RF_Antenna:Texas_SWRA117D_2.4GHz_Left", fields=fields("", ""), in_bom=False)
ae.ref_at = (ae.x + 3.81, ae.y - 5.08, 0, "left")
ae.val_at = (ae.x + 3.81, ae.y - 2.54, 0, "left")
a1 = ae.pin("1")
a2 = ae.pin("2")
s.wire([(xq, y0), (a1[0], y0), (a1[0], a1[1])])
s.wire([(a2[0], a2[1]), (xq - 2.54, a2[1])])
s.power("GND", xq - 2.54, a2[1])
# debug + GPIO map (any GPIO works for SPI on nRF52; layout may swap within this list)
for p, net in (("SWDIO", "SWDIO"), ("SWDCLK", "SWDCLK"), ("P0.21/~{RESET}", "NRST")):
    s.pin_label(u1, p, net)
GPIO = {"P0.06": "ADC_CS", "P0.07": "SPI_SCK", "P0.08": "SPI_MOSI", "P0.11": "SPI_MISO", "P0.12": "ADC_DRDY",
        "P0.13": "ADC_START", "P0.14": "ADC_PWDN", "P0.15": "LED", "P0.16": "BUTTON", "P0.17": "CHG_N",
        "P0.02/AIN0": "VBAT_SENSE", "P0.03/AIN1": "I2C_SDA", "P0.04/AIN2": "I2C_SCL", "P0.24": "IMU_INT"}
for p, net in GPIO.items():
    s.pin_label(u1, p, net)
for p in ("P0.00/XL1", "P0.01/XL2", "P0.05/AIN3", "NFC1/P0.09", "NFC2/P0.10",
          "P0.18/SWO", "P0.19", "P0.20", "P0.22", "P0.23", "P0.25", "P0.26", "P0.27", "P0.28/AIN4",
          "P0.29/AIN5", "P0.30/AIN6", "P0.31/AIN7", "44"):
    s.pin_nc(u1, p)
s.rect(229.87, 25.4, 401.32, 160.02, fill=COL["mcu"], title="MCU + BLE: nRF52832 (chip-down, printed antenna)")
s.text("RF: ANT -> L/C match (Nordic ref.) -> pi tuning pads (0R + 2 DNP) -> TI SWRA117D antenna.", 238.76, 157.48)

# ============================================================ power, charge, UI
PY = 205.74
# battery pads (solder the LiPo wires)
bt = s.add("Connector_Generic:Conn_01x02", "J2", "LiPo 3.7V (protected)", 30.48, PY, mirror="y",
           footprint="neurband:WirePads_2x1.5x2mm_P3mm", fields=fields("", ""), in_bom=False)
bt.ref_at = (30.48, PY - 5.08, 0)
bt.val_at = (30.48, PY + 6.35, 0)
x, y, _ = bt.pin("1")
s.wire([(x, y), (x + 7.62, y)])
s.power("VBAT", x + 7.62, y)
x, y, _ = bt.pin("2")
s.wire([(x, y), (x + 7.62, y)])
s.power("GND", x + 7.62, y)
s.junction(x + 2.54, y)
s.wire([(x + 2.54, y), (x + 2.54, y + 7.62)])
f = s.add("power:PWR_FLAG", "#FLG02", "PWR_FLAG", x + 2.54, y + 7.62, 180)
f.hide_ref = True
f.val_at = (x + 2.54, y + 11.43, 0)
# charge pads (magnetic 2-pin cable) + TP4054 (MCP73831 pinout)
cp = s.add("Connector_Generic:Conn_01x02", "J3", "Charge 5V (magnetic pads)", 30.48, PY + 33.02, mirror="y",
           footprint="neurband:WirePads_2x1.5x2mm_P3mm", fields=fields("", ""), in_bom=False)
cp.ref_at = (30.48, PY + 27.94, 0)
cp.val_at = (30.48, PY + 39.37, 0)
x, y, _ = cp.pin("1")
s.wire([(x, y), (x + 7.62, y)])
s.power("VCHG", x + 7.62, y, lib="power:VBUS")
s.junction(x + 2.54, y)
s.wire([(x + 2.54, y), (x + 2.54, y - 5.08)])
f = s.add("power:PWR_FLAG", "#FLG03", "PWR_FLAG", x + 2.54, y - 5.08)
f.hide_ref = True
f.val_at = (x + 2.54, y - 8.89, 0)
x, y, _ = cp.pin("2")
s.wire([(x, y), (x + 7.62, y)])
s.power("GND", x + 7.62, y)
u4 = s.add("Battery_Management:MCP73831-2-OT", "U4", "TP4054", 83.82, PY + 25.4,
           footprint="neurband:SOT-23-5_FabZero", fields=fields("TP4054-42-SOT25R", "C32574"))
u4.ref_at = (73.66, PY + 15.24, 0, "right")
u4.val_at = (73.66, PY + 17.78, 0, "right")
x, y, _ = u4.pin("4")
s.wire([(x, y), (x, y - 2.54)])
s.power("VCHG", x, y - 2.54, lib="power:VBUS")
x, y, _ = u4.pin("2")
s.wire([(x, y), (x, y + 2.54)])
s.power("GND", x, y + 2.54)
x, y, _ = u4.pin("PROG")
s.wire([(x, y), (x - 5.08, y)])
r = passive("R", "10k", x - 5.08, y + 2.54, text="left")
s.power("GND", x - 5.08, y + 5.08)
x, y, _ = u4.pin("V_{BAT}")
s.wire([(x, y), (x + 5.08, y)])
s.power("VBAT", x + 5.08, y)
s.pin_label(u4, "STAT", "CHG_N")
bank(109.22, PY + 5.08, "VCHG", ["1uF"])
bank(124.46, PY + 5.08, "VBAT", ["10uF"])
s.text("TP4054: PROG 10k -> 100 mA.\nCHG_N low while charging: firmware turns the AFE off\n(never wear the band while it charges).", 68.58, PY + 40.64)
# LDO: one basic XC6206 3.3 V for everything, RC-filtered branch for the ADS analog supply
u3 = s.add("Regulator_Linear:XC6206PxxxMR", "U3", "XC6206P332MR", 165.1, PY + 5.08,
           footprint="neurband:SOT-23-3_FabZero", fields=fields("XC6206P332MR-G", "C5446"))
u3.ref_at = (165.1, PY - 2.54, 0)
u3.val_at = (165.1, PY, 0)
x, y, _ = u3.pin("VI")
s.wire([(x, y), (x - 5.08, y)])
s.power("VBAT", x - 5.08, y)
x, y, _ = u3.pin("GND")
s.wire([(x, y), (x, y + 2.54)])
s.power("GND", x, y + 2.54)
x, y, _ = u3.pin("VO")
s.wire([(x, y), (x + 5.08, y)])
s.power("+3V3", x + 5.08, y)
bank(142.24, PY + 20.32, "VBAT", ["1uF"])
bank(182.88, PY + 20.32, "+3V3", ["1uF"])
# AVDD filter: +3V3 -> 10R -> +3V3A, 10uF + 100nF
s.power("+3V3", 198.12, PY + 2.54)
s.wire([(198.12, PY + 2.54), (198.12, PY + 5.08), (200.66, PY + 5.08)])
passive("R", "10", 203.2, PY + 5.08, 90)
s.wire([(205.74, PY + 5.08), (215.9, PY + 5.08)])
s.power("+3V3A", 215.9, PY + 5.08, lib="power:+3V3")
s.junction(212.09, PY + 5.08)
s.wire([(212.09, PY + 5.08), (212.09, PY + 0.0)])
f = s.add("power:PWR_FLAG", "#FLG04", "PWR_FLAG", 212.09, PY + 0.0)
f.hide_ref = True
f.val_at = (212.09, PY - 3.81, 0)
bank(208.28, PY + 20.32, "+3V3A", ["10uF", "100nF"])
s.text("+3V3A = ADS1298 AVDD (RC-filtered, 1.6 kHz corner).", 190.5, PY + 33.02)
# battery sense 1M/1M + 100nF
r1 = passive("R", "1M", 243.84, PY + 5.08)
s.power("VBAT", 243.84, PY + 2.54)
r2 = passive("R", "1M", 243.84, PY + 15.24)
s.wire([(243.84, PY + 7.62), (243.84, PY + 12.7)])
s.junction(243.84, PY + 10.16)
s.wire([(243.84, PY + 10.16), (259.08, PY + 10.16)])
s.junction(251.46, PY + 10.16)
passive("C", "100nF", 251.46, PY + 12.7)
s.power("GND", 251.46, PY + 15.24)
s.power("GND", 243.84, PY + 17.78)
s.label("VBAT_SENSE", 259.08, PY + 10.16, 0)
# button (wake / marker) and LED
sw = s.add("Switch:SW_Push", "SW1", "WAKE / MARK", 297.18, PY + 2.54, footprint="Button_Switch_SMD:SW_SPST_TS-1088-xR020",
           fields=fields("TS-1088-AR02016", "C720477"))
sw.ref_at = (297.18, PY - 0.76, 0)
sw.val_at = (297.18, PY + 5.84, 0)
s.pin_label(sw, "1", "BUTTON")
x, y, _ = sw.pin("2")
s.wire([(x, y), (x + 2.54, y)])
s.power("GND", x + 2.54, y)
r = passive("R", "1k", 297.18, PY + 17.78, 90)
x, y, _ = r.pin("1")
s.wire([(x, y), (x - 2.54, y)])
s.power("+3V3", x - 2.54, y)
d = s.add("Device:LED_Small", "D1", "red", 307.34, PY + 17.78, 180, footprint=FP["LED"], fields=fields("KT-0603R", "C2286"))
d.ref_at = (307.34, PY + 15.0, 0)
d.val_at = (307.34, PY + 21.0, 0)
s.wire([(r.pin("2")[0], y), (d.pin("A")[0], y)])
x, y, _ = d.pin("K")
s.wire([(x, y), (x + 2.54, y)])
s.label("LED", x + 2.54, y, 0)
# SWD + test pads
PADS = ["+3V3", "SWDIO", "SWDCLK", "NRST", "GND"]
for i, net in enumerate(PADS):
    yy = PY + i * 6.35
    tp = s.add("Connector:TestPoint", f"TP{i + 1}", "pad", 345.44, yy, 90,
               footprint="neurband:SWD_Pad_1x1_P1.27", fields=fields("", ""), in_bom=False)
    tp.ref_at = (342.9, yy - 1.27, 0)
    tp.hide_value = True
    px, py, _ = tp.pin("1")
    dx = 12.7 if net == "+3V3" else 5.08
    s.wire([(px, py), (px + dx, py)])
    if net in ("+3V3", "GND"):
        s.power(net, px + dx, py)
    else:
        s.label(net, px + dx, py, 0)
s.text("SWD: program with any CMSIS-DAP probe (e.g. Raspberry Pi Pico debugprobe), off-body.", 330.2, PY + 33.02)
s.rect(15.24, 177.8, 401.32, 248.92, fill=COL["pwr"], title="Power, charging, user interface, debug")


# ============================================================ IMU (motion reference, like Meta's sEMG-RD)
IX, IY = 101.6, 274.32
u5 = s.add("Sensor_Motion:LSM6DSL", "U5", "LSM6DSL", IX, IY,
           footprint="Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y", fields=fields("LSM6DSLTR", "C126672"))
u5.ref_at = (IX + 5.08, IY - 13.97, 0, "left")
u5.val_at = (IX + 5.08, IY - 11.43, 0, "left")
vx, vy, _ = u5.pin("VDDIO")
wx, wy, _ = u5.pin("VDD")
s.wire([(vx, vy), (wx, wy)])
s.wire([(vx, vy), (vx, vy - 2.54)])
s.power("+3V3", vx, vy - 2.54)
gx, gy, _ = u5.pin("6")
s.wire([(gx, gy), (gx, gy + 2.54)])
s.power("GND", gx, gy + 2.54)
s.pin_label(u5, "SDA", "I2C_SDA")
s.pin_label(u5, "SCL", "I2C_SCL")
s.pin_label(u5, "INT1", "IMU_INT")
for p in ("INT2", "10", "11"):
    s.pin_nc(u5, p)
rail = []
for p in ("SDO/SA0", "SDX", "SCX"):
    px, py, _ = u5.pin(p)
    s.wire([(px, py), (px - 7.62, py)])
    rail.append((px - 7.62, py))
s.wire([rail[0], rail[-1]])
s.junction(*rail[0])
s.junction(*rail[1])
s.wire([rail[0], (rail[0][0] - 7.62, rail[0][1])])
s.power("GND", rail[0][0] - 7.62, rail[0][1])
cx_, cy_, _ = u5.pin("CS")
s.wire([(cx_, cy_), (cx_ - 22.86, cy_), (cx_ - 22.86, rail[0][1] - 5.08)])
s.power("+3V3", cx_ - 22.86, rail[0][1] - 5.08)
bank(129.54, 269.24, "+3V3", ["100nF"])
for i, net in enumerate(("I2C_SDA", "I2C_SCL")):
    r = passive("R", "10k", 147.32 + i * 10.16, 269.24)
    s.power("+3V3", r.x, r.y - 2.54)
    s.wire([(r.x, r.y + 2.54), (r.x, r.y + 5.08)])
    s.label(net, r.x, r.y + 5.08, 270)
s.rect(15.24, 251.46, 172.72, 294.64, fill="140 80 180", title="IMU: LSM6DSL (I2C 0x6A)")

# ADC_PWDN pull-down: ADS1298 stays powered down until the nRF52 drives the pin (it floats at power-on)
r = passive("R", "100k", 271.78, 205.74 + 33.02)
s.wire([(271.78, 205.74 + 30.48), (271.78, 205.74 + 27.94)])
s.label("ADC_PWDN", 271.78, 205.74 + 27.94, 90)
s.power("GND", 271.78, 205.74 + 35.56)

# RLDREF: filtered AVDD/2 bias reference (RLDREF_INT=0). Keeps nRF radio bursts on AVDD out of the body bias
# (docs/science/simulations.md Q4: 0.6-7 uVrms via the internal reference). 2 x 1M divider, 1uF -> 0.3 Hz.
s.pin_label(u2, "RLDREF", "RLDREF")
QX, QY = 88.9, 50.8
s.label("RLDREF", QX + 5.08, QY, 0)
s.wire([(QX, QY), (QX + 5.08, QY)])
rq1 = passive("R", "1M", QX, QY - 2.54, text="left")
s.power("+3V3A", QX, QY - 5.08, lib="power:+3V3")
s.junction(QX, QY)
rq2 = passive("R", "1M", QX, QY + 2.54, text="left")
s.power("GND", QX, QY + 5.08)
s.wire([(QX + 5.08, QY), (QX + 12.7, QY)])
s.junction(QX + 5.08, QY)
cq = passive("C", "1uF", QX + 12.7, QY + 2.54)
s.power("GND", QX + 12.7, QY + 5.08)
s.text("Bias reference: filtered AVDD/2", QX - 12.7, QY + 12.7)

s.write(os.path.join(HERE, "neurband_c.kicad_sch"))
print("written")
