"""Generates neurband_main.kicad_sch (main board: 16-ch sEMG AFE + ESP32-S3 + power).

Run:  python3 gen_main_sch.py
Every connection is made here; the schematic file is an output, edit this script.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../tools"))
import schgen  # noqa: E402
from schgen import Schematic  # noqa: E402

schgen.LOCAL_LIBS["neurband"] = os.path.join(os.path.dirname(__file__), "../../lib/neurband.kicad_sym")

HERE = os.path.dirname(os.path.abspath(__file__))
s = Schematic("neurband main board: 16-ch sEMG front-end + ESP32-S3", paper="A2", project="neurband_main")

# ---------------------------------------------------------------- part data
FP = {
    "R0402": "Resistor_SMD:R_0402_1005Metric",
    "C0402": "Capacitor_SMD:C_0402_1005Metric",
    "C0603": "Capacitor_SMD:C_0603_1608Metric",
    "LED": "LED_SMD:LED_0603_1608Metric",
    "RN": "Resistor_SMD:R_Array_Convex_4x0402",
}
PARTS = {  # value -> (footprint, MPN, LCSC)
    "R:10k": ("R0402", "0402WGF1002TCE", "C25744"),
    "R:5.1k": ("R0402", "0402WGF5101TCE", "C25905"),
    "R:4.7k": ("R0402", "0402WGF4701TCE", "C25900"),
    "R:1k": ("R0402", "0402WGF1001TCE", "C11702"),
    "R:1M": ("R0402", "0402WGF1004TCE", "C26083"),
    "R:100k": ("R0402", "0402WGF1003TCE", "C25741"),
    "C:100nF": ("C0402", "CL05B104KO5NNNC", "C1525"),
    "C:1uF": ("C0402", "CL05A105KA5NQNC", "C52923"),
    "C:1.5nF": ("C0402", "CC0402KRX7R9BB152", "C107022"),
    "C:4.7uF": ("C0603", "CL10A475KO8NNNC", "C19666"),
    "C:10uF": ("C0402", "CL05A106MQ5NUNC", "C15525"),
    "C:22uF": ("C0603", "CL10A226MQ8NRNC", "C59461"),
}
_n = {"R": 0, "C": 0, "D": 0}


def fields(mpn, lcsc):
    return {"MPN": mpn, "LCSC": lcsc}


def passive(kind, value, x, y, rot=0):
    """kind 'R' or 'C'. rot 0 = vertical (pin 1 top), 90 = horizontal (pin 1 left)."""
    _n[kind] += 1
    fp, mpn, lcsc = PARTS[f"{kind}:{value}"]
    lib = "Device:R_Small_US" if kind == "R" else "Device:C_Small"
    p = s.add(lib, f"{kind}{_n[kind]}", value.replace("uF", "uF"), x, y, rot, footprint=FP[fp], fields=fields(mpn, lcsc))
    if rot == 0:
        p.ref_at = (p.x + 1.9, p.y - 0.6, 0, "left")
        p.val_at = (p.x + 1.9, p.y + 1.9, 0, "left")
    else:
        p.ref_at = (p.x, p.y - 2.9, 0)
        p.val_at = (p.x, p.y + 3.4, 0)
    return p


def vcap_left(sym, pin, value, dx, label_left=True):
    """Cap hanging down from a wire run left out of a left-side pin; text left of the cap."""
    x, y, _ = sym.pin(pin)
    cx = x - dx
    s.wire([(x, y), (cx, y)])
    c = passive("C", value, cx, y + 2.54)
    c.ref_at = (cx - 1.9, c.y - 0.6, 0, "right")
    c.val_at = (cx - 1.9, c.y + 1.9, 0, "right")
    s.power("GND", cx, y + 5.08)
    return c


def bank(x, y, net, values, gnd="GND", pitch=7.62):
    """Row of decoupling caps between a top rail (power symbol at left) and a GND rail."""
    caps = [passive("C", v, x + i * pitch, y) for i, v in enumerate(values)]
    top, bot = y - 2.54, y + 2.54
    x_end = x + (len(values) - 1) * pitch
    s.wire([(x - 2.54, top), (x_end, top)])
    s.wire([(x - 2.54, bot), (x_end, bot)])
    for i in range(1, len(values) - 1):
        s.junction(x + i * pitch, top)
        s.junction(x + i * pitch, bot)
    s.power(net, x - 2.54, top)
    s.power(gnd, x - 2.54, bot)
    return caps


def stub_power(sym, pin, kind, length=2.54):
    return s.pin_power(sym, pin, kind, length)


# ---------------------------------------------------------------- colours (r g b)
COL = {
    "afe": "40 120 200",
    "mcu": "200 120 40",
    "pwr": "200 50 50",
    "conn": "60 160 80",
    "imu": "140 80 180",
}

# ================================================================ electrode connector J2
J2X, J2Y = 40.64, 152.4
j2 = s.add("Connector_Generic:Conn_01x39", "J2", "FPC 39p 0.3mm (electrode flex)", J2X, J2Y, mirror="y",
           footprint="Connector_FFC-FPC:Hirose_FH26-39S-0.3SHW_2Rows-39Pins-1MP_P0.60mm_Horizontal",
           fields=fields("FH26W-39S-0.3SHW(60)", "C92280"))
j2.ref_at = (J2X, J2Y - 53.34, 0)
j2.val_at = (J2X, J2Y + 54.61, 0)
J2_MAP = {1: "GND", 2: "GND", 3: "BIAS_E", 36: "BIAS_E", 37: "GND", 38: "GND", 39: "GND"}
for ch in range(16):
    J2_MAP[4 + 2 * ch] = f"E{ch + 1:02d}P"
    J2_MAP[5 + 2 * ch] = f"E{ch + 1:02d}N"
gnd_pins = [n for n, v in J2_MAP.items() if v == "GND"]
for n, net in sorted(J2_MAP.items()):
    if net == "GND":
        continue
    s.pin_label(j2, str(n), net)
# GND pins: short stubs joined on a vertical rail at the right
for grp in ([1, 2], [37, 38, 39]):
    pts = []
    for n in grp:
        x, y, _ = j2.pin(str(n))
        s.wire([(x, y), (x + 5.08, y)])
        pts.append((x + 5.08, y))
    s.wire([pts[0], pts[-1]])
    for p in pts[1:-1]:
        s.junction(*p)
    if grp[0] == 1:  # pin 3 (BIAS_E) is just below: take GND off the top of the rail
        s.junction(*pts[0])
        s.wire([pts[0], (pts[0][0] + 5.08, pts[0][1])])
        s.power("GND", pts[0][0] + 5.08, pts[0][1])
    else:
        s.power("GND", *pts[-1])
s.rect(15.24, 88.9, 76.2, 228.6, fill=COL["conn"], title="Electrode flex connector")
s.text("Pinout matches the electrode flex tail.\nPair n: EnnP = proximal, EnnN = distal electrode.\nBIAS_E = middle electrode of every pod (driven).", 17.78, 223.52, size=1.27)

# ================================================================ ADS1298 front-ends
RN = {"n": 0, "unit": 0}


def series_r(sym, pin, net):
    """4.7k input resistor (one unit of a 4x array) between electrode label and AFE pin."""
    x, y, _ = sym.pin(pin)
    if RN["unit"] % 4 == 0:
        RN["n"] += 1
    unit = RN["unit"] % 4 + 1
    RN["unit"] += 1
    cx = x - 2.54 - 3.81
    r = s.add("Device:R_Pack04_Split", f"RN{RN['n']}", "4.7k", cx, y, 90, unit=unit,
              footprint=FP["RN"], fields=fields("4D02WGJ0472TCE", "C29586"))
    r.ref_at = (cx, y - 1.0, 0)
    r.fsize = 1.0
    r.hide_value = True
    s.wire([(x, y), (x - 2.54, y)])
    lx = cx - 3.81
    s.wire([(lx, y), (lx - 2.54, y)])
    s.label(net, lx - 2.54, y, 180)
    return r


def ads(ref, x, y, ch0, master):
    u = s.add("Analog_ADC:ADS1298xPAG", ref, "ADS1298IPAGR", x, y,
              footprint="Package_QFP:TQFP-64_10x10mm_P0.5mm", fields=fields("ADS1298IPAGR", "C527440"))
    u.ref_at = (x - 15.24, y - 45.72, 0, "left")
    u.val_at = (x + 2.54, y - 45.72, 0, "left")
    # inputs
    for i in range(8):
        n = ch0 + i
        series_r(u, f"IN{i + 1}P", f"E{n:02d}P")
        series_r(u, f"IN{i + 1}N", f"E{n:02d}N")
    # reference + bypass (datasheet fig. 106), staircase to the left
    gx, gy, _ = u.pin("VREFN")
    s.wire([(gx, gy), (gx - 2.54, gy)])
    s.power("GND", gx - 2.54, gy)
    vcap_left(u, "VREFP", "100nF", 7.62)
    xr, yr, _ = u.pin("VREFP")
    s.junction(xr - 7.62, yr)
    s.wire([(xr - 7.62, yr), (xr - 17.78, yr)])
    c = passive("C", "10uF", xr - 17.78, yr + 2.54)
    c.ref_at = (xr - 17.78 - 1.9, c.y - 0.6, 0, "right")
    c.val_at = (xr - 17.78 - 1.9, c.y + 1.9, 0, "right")
    s.power("GND", xr - 17.78, yr + 5.08)
    vcap_left(u, "VCAP4", "1uF", 27.94)
    vcap_left(u, "VCAP3", "1uF", 38.1)
    vcap_left(u, "VCAP2", "1uF", 48.26)
    vcap_left(u, "VCAP1", "22uF", 58.42)
    # supplies: AVDD + AVDD1 joined -> +3V0, DVDD -> +3V3 ; grounds joined
    ax, ay, _ = u.pin("19")
    a1x, a1y, _ = u.pin("AVDD1")
    s.wire([(ax, ay), (a1x, a1y)])
    s.wire([(ax, ay), (ax, ay - 2.54)])
    s.power("+3V0", ax, ay - 2.54)
    stub_power(u, "48", "+3V3")
    gx1, gy1, _ = u.pin("20")
    gx3, gy3, _ = u.pin("33")
    s.wire([(gx1, gy1), (gx3, gy3)])
    s.junction(x, gy1)
    s.wire([(x, gy1), (x, gy1 + 2.54)])
    s.power("GND", x, gy1 + 2.54)
    # right side
    s.pin_nc(u, "WCT")
    s.pin_nc(u, "RLDREF")
    s.pin_nc(u, "27")
    s.pin_nc(u, "29")
    # TESTP/TESTN unused -> AVDD (datasheet note 1)
    t1x, t1y, _ = u.pin("17")
    t2x, t2y, _ = u.pin("18")
    s.wire([(t1x, t1y), (t1x + 5.08, t1y)])
    s.wire([(t2x, t2y), (t2x + 5.08, t2y)])
    s.wire([(t1x + 5.08, t1y), (t2x + 5.08, t2y)])
    s.wire([(t1x + 5.08, t1y), (t1x + 5.08, t1y - 2.54)])
    s.power("+3V0", t1x + 5.08, t1y - 2.54)
    # GPIO1-4 + DAISY_IN unused -> DGND (rail on the right, GND at its top-right)
    rail = []
    for p in ("GPIO1", "GPIO2", "GPIO3", "GPIO4", "DAISY_IN"):
        px, py, _ = u.pin(p)
        s.wire([(px, py), (px + 5.08, py)])
        rail.append((px + 5.08, py))
    s.wire([rail[0], rail[-1]])
    for p in rail[1:-1]:
        s.junction(*p)
    s.wire([rail[0], (rail[0][0] + 7.62, rail[0][1])])
    s.junction(*rail[0])
    s.power("GND", rail[0][0] + 7.62, rail[0][1])
    rx, ry, _ = u.pin("RESV1")
    s.wire([(rx, ry), (rx + 5.08, ry)])
    s.power("GND", rx + 5.08, ry)
    # SPI + control
    s.pin_label(u, "SCLK", "SPI_SCLK")
    s.pin_label(u, "DIN", "SPI_MOSI")
    s.pin_label(u, "DOUT", "SPI_MISO")
    s.pin_label(u, "~{CS}", "ADC_CS_A" if master else "ADC_CS_B")
    s.pin_label(u, "START", "ADC_START")
    # PWDN + RESET held high; reset is done with the SPI RESET opcode (master first, then slave once CLK runs)
    p1x, p1y, _ = u.pin("~{PWDN}")
    p2x, p2y, _ = u.pin("~{RESET}")
    s.wire([(p1x, p1y), (p1x + 5.08, p1y)])
    s.wire([(p2x, p2y), (p2x + 5.08, p2y)])
    s.wire([(p1x + 5.08, p1y), (p2x + 5.08, p2y)])
    s.junction(p1x + 5.08, p1y)
    s.wire([(p1x + 5.08, p1y), (p1x + 27.94, p1y)])
    s.power("+3V3", p1x + 27.94, p1y)
    s.pin_label(u, "CLK", "ADC_CLK")
    cx_, cy_, _ = u.pin("CLKSEL")
    s.wire([(cx_, cy_), (cx_ + 17.78, cy_)])
    cx_ += 5.08
    if master:
        s.pin_label(u, "~{DRDY}", "ADC_DRDY")
        s.power("+3V3", cx_ + 12.7, cy_)  # internal oscillator, CLK pin drives the slave
    else:
        s.pin_nc(u, "~{DRDY}")
        s.power("GND", cx_ + 12.7, cy_)  # clock taken from master's CLK pin
    # bias (right-leg) drive
    s.pin_label(u, "RLDIN", "BIAS_E")
    ox, oy, _ = u.pin("RLDOUT")
    ix, iy, _ = u.pin("RLDINV")
    if master:
        # 1M || 1.5nF feedback (datasheet fig. 45/RLD section), 100k series to the bias electrodes
        s.wire([(ox, oy), (ox + 30.48, oy)])
        s.wire([(ix, iy), (ix + 38.1, iy)])
        r = passive("R", "1M", ox + 20.32, oy + 2.54)
        r.ref_at = (r.x - 1.9, r.y - 0.6, 0, "right")
        r.val_at = (r.x - 1.9, r.y + 1.9, 0, "right")
        c = passive("C", "1.5nF", ox + 27.94, oy + 2.54)
        s.junction(ox + 20.32, oy)
        s.junction(ox + 20.32, iy)
        s.junction(ox + 27.94, oy)
        s.junction(ox + 27.94, iy)
        s.label("RLD_INV", ix + 38.1, iy, 0)
        rs = passive("R", "100k", ox + 43.18, oy, 90)
        s.wire([(ox + 30.48, oy), (ox + 40.64, oy)])
        s.wire([(ox + 45.72, oy), (ox + 48.26, oy)])
        s.label("BIAS_E", ox + 48.26, oy, 0)
    else:
        s.pin_nc(u, "RLDOUT")  # amplifier powered down; only its RLDINV summing node is shared
        s.pin_label(u, "RLDINV", "RLD_INV")
    return u


U2 = ads("U2", 190.5, 101.6, 1, True)
U3 = ads("U3", 190.5, 220.98, 9, False)
s.text("RN1-RN8: 4x 4.7 kOhm 0402 arrays (4D02WGJ0472TCE)\nin series with every electrode: RF/ESD current limit.", 99.06, 160.02, size=1.27)
bank(229.87, 50.8, "+3V0", ["1uF", "100nF", "100nF"])
bank(229.87, 170.18, "+3V0", ["1uF", "100nF", "100nF"])
bank(259.08, 50.8, "+3V3", ["1uF", "100nF"])
bank(259.08, 170.18, "+3V3", ["1uF", "100nF"])
s.rect(99.06, 40.64, 284.48, 152.4, fill=COL["afe"], title="AFE A: ADS1298, channels 1-8 (clock + bias master)")
s.rect(99.06, 160.02 + 2.54, 284.48, 271.78, fill=COL["afe"], title="AFE B: ADS1298, channels 9-16")

# ================================================================ ESP32-S3
UX, UY = 350.52, 99.06
u1 = s.add("neurband:ESP32-C3-MINI-1", "U1", "ESP32-C3-MINI-1-N4", UX, UY,
           footprint="neurband:ESP32-C3-MINI-1", fields=fields("ESP32-C3-MINI-1-N4", "C2838502"))
u1.ref_at = (UX - 10.16, UY - 25.4, 0, "left")
u1.val_at = (UX + 2.54, UY - 25.4, 0, "left")
stub_power(u1, "3V3", "+3V3")
stub_power(u1, "1", "GND")
# strap pins: IO8 and IO2 must be high at boot -> they carry the CS lines, whose 10k pull-ups do it;
# IO9 = BOOT (internal pull-up, pad to GND for download mode)
ESP = {
    "IO9": "BOOT", "IO10": "ADC_START", "IO3": "ADC_DRDY",
    "IO2": "ADC_CS_B", "IO8": "ADC_CS_A", "IO7": "SPI_MOSI", "IO6": "SPI_SCLK", "IO5": "SPI_MISO",
    "IO18/USB_D-": "USB_DN", "IO19/USB_D+": "USB_DP", "TXD0/IO21": "UART_TX", "RXD0/IO20": "UART_RX",
}
for p, net in ESP.items():
    s.pin_label(u1, p, net)
for p in ["IO0", "IO1", "IO4"]:
    s.pin_nc(u1, p)
# EN: 10k pull-up + 1uF delay (Espressif reference)
ex, ey, _ = u1.pin("EN")
s.wire([(ex, ey), (ex - 25.4, ey)])
r = passive("R", "10k", ex - 12.7, ey - 2.54)
s.junction(ex - 12.7, ey)
s.power("+3V3", ex - 12.7, ey - 5.08)
c = passive("C", "1uF", ex - 25.4, ey + 2.54)
c.ref_at = (ex - 25.4 - 1.9, c.y - 0.6, 0, "right")
c.val_at = (ex - 25.4 - 1.9, c.y + 1.9, 0, "right")
s.power("GND", ex - 25.4, ey + 5.08)
s.wire([(ex - 25.4, ey), (ex - 30.48, ey)])
s.label("EN", ex - 30.48, ey, 180)
bank(375.92, 45.72, "+3V3", ["10uF", "100nF"])
# keep the ADCs deselected and idle while the ESP32 boots (its GPIOs float until firmware runs)
for i, (net, to) in enumerate((("ADC_CS_A", "+3V3"), ("ADC_CS_B", "+3V3"), ("ADC_START", "GND"))):
    rx = 386.08 + i * 10.16
    r = passive("R", "10k", rx, 162.56)
    if to == "+3V3":
        s.power("+3V3", rx, 160.02)
        s.wire([(rx, 165.1), (rx, 167.64)])
        s.label(net, rx, 167.64, 270)
    else:
        s.power("GND", rx, 165.1)
        s.wire([(rx, 160.02), (rx, 157.48)])
        s.label(net, rx, 157.48, 90)
# programming / debug pads (no parts): UART download, native USB, power
PADS = ["VBAT", "+3V3", "EN", "BOOT", "UART_TX", "UART_RX", "USB_DP", "USB_DN", "GND"]
for i, net in enumerate(PADS):
    y = 149.86 + i * 6.35
    tp = s.add("Connector:TestPoint", f"TP{i + 1}", "pad", 314.96, y, 90,
               footprint="TestPoint:TestPoint_Pad_1.0x1.0mm", fields={"MPN": "", "LCSC": ""}, in_bom=False)
    tp.ref_at = (307.34, y - 1.27, 0)
    tp.hide_value = True
    px, py, _ = tp.pin("1")
    dx = {"VBAT": 5.08, "+3V3": 12.7}.get(net, 5.08)
    s.wire([(px, py), (px + dx, py)])
    if net in ("GND", "+3V3", "VBAT"):
        s.power(net, px + dx, py)
    else:
        s.label(net, px + dx, py, 0)
s.text("Pads TP1-TP9: flash/debug OFF-BODY only\n(download: short BOOT pad to GND, pulse EN; UART0 or native USB D+/D-).", 299.72, 213.36)
s.rect(297.18, 30.48, 429.26, 218.44, fill=COL["mcu"], title="MCU + radio: ESP32-C3-MINI-1 (Wi-Fi streaming)")

# ================================================================ power (battery only, wireless on-body)
PY = 309.88
j3 = s.add("Connector_Generic:Conn_01x02", "J1", "LiPo 3.7V protected", 40.64, PY, mirror="y",
           footprint="Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal",
           fields=fields("SM02B-SRSS-TB(LF)(SN)", "C160402"))
j3.ref_at = (40.64, PY - 5.08, 0)
j3.val_at = (40.64, PY + 6.35, 0)
x, y, _ = j3.pin("1")
s.wire([(x, y), (x + 7.62, y)])
s.power("VBAT", x + 7.62, y)
x, y, _ = j3.pin("2")
s.wire([(x, y), (x + 7.62, y)])
s.power("GND", x + 7.62, y)
fx, fy, _ = j3.pin("1")
s.junction(fx + 2.54, fy)
s.wire([(fx + 2.54, fy), (fx + 2.54, fy - 5.08)])
f = s.add("power:PWR_FLAG", "#FLG01", "PWR_FLAG", fx + 2.54, fy - 5.08)
f.hide_ref = True
f.val_at = (fx + 2.54, fy - 8.89, 0)
gx, gy, _ = j3.pin("2")
s.junction(gx + 2.54, gy)
s.wire([(gx + 2.54, gy), (gx + 2.54, gy + 7.62)])
f = s.add("power:PWR_FLAG", "#FLG02", "PWR_FLAG", gx + 2.54, gy + 7.62, 180)
f.hide_ref = True
f.val_at = (gx + 2.54, gy + 11.43, 0)
s.text("Charge the cell off the band with any 1S LiPo charger.\nUse a cell with a protection circuit. Unplug = off.", 22.86, 330.20)


def ldo(ref, lib, val, x, y, out, mpn, lcsc):
    u = s.add(lib, ref, val, x, y, footprint="Package_TO_SOT_SMD:SOT-23-5", fields=fields(mpn, lcsc))
    u.ref_at = (x, y - 10.16, 0)
    u.val_at = (x, y - 7.62, 0)
    ix, iy, _ = u.pin("1")
    ex_, ey_, _ = u.pin("3")
    s.wire([(ix, iy), (ix - 5.08, iy)])
    s.wire([(ex_, ey_), (ix - 5.08, ey_), (ix - 5.08, iy)])
    s.junction(ix - 5.08, iy)
    s.wire([(ix - 5.08, iy), (ix - 10.16, iy)])
    s.power("VBAT", ix - 10.16, iy)
    stub_power(u, "2", "GND")
    s.pin_nc(u, "4")
    ox, oy, _ = u.pin("5")
    s.wire([(ox, oy), (ox + 5.08, oy)])
    s.power(out, ox + 5.08, oy)
    return u


ldo("U4", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", 132.08, 307.34, "+3V3", "AP2112K-3.3TRG1", "C51118")
ldo("U5", "Regulator_Linear:LP5907MFX-3.0", "LP5907MFX-3.0", 223.52, 307.34, "+3V0", "LP5907MFX-3.0/NOPB", "C475492")
bank(86.36, 307.34, "VBAT", ["4.7uF", "1uF"])
bank(154.94, 307.34, "+3V3", ["1uF"])
bank(246.38, 307.34, "+3V0", ["1uF"])
s.text("+3V3: digital (ESP32 Wi-Fi peaks ~350 mA, ADS DVDD)\n+3V0: analog AVDD of both ADS1298 (low-noise LDO, 6.5 uVrms)\n"
       "Below ~3.5 V cell the 3V3 rail sags first under Wi-Fi bursts.", 271.78, 304.80)
s.rect(15.24, 287.02, 429.26, 340.36, fill=COL["pwr"], title="Power: protected 1S LiPo -> two LDOs (no charger, no USB on-body)")

s.write(os.path.join(HERE, "neurband_main.kicad_sch"))
print("written")
