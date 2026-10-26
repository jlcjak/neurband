#!/usr/bin/env python3
"""copper_layers.py - quad view of the four copper layers of the rev C main board.

Exports each copper layer and the outline with kicad-cli (SVG, board area only), rasterises them with
rsvg-convert and composes a 2 x 2 image, all layers seen from the top:

  python3 tools/copper_layers.py [out.png]       # default docs/media/board_layers.png
"""
import os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'boards/neurband_c/neurband_c.kicad_pcb')
KCLI = os.environ.get('KICAD_CLI', os.path.expanduser('~/.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli'))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'docs/media/board_layers.png')

LAYERS = [('F.Cu', 'L1  F.Cu', 'parts, signal routing, GND pour'),
          ('In1.Cu', 'L2  In1.Cu', 'solid GND reference plane'),
          ('In2.Cu', 'L3  In2.Cu', '+3V3 and VBAT, signals, GND fill'),
          ('B.Cu', 'L4  B.Cu', 'routing, GND pour, service pads')]
PANEL_W = 960                      # board raster width per panel, px
BG = (14, 15, 17)
SUBSTRATE = (30, 34, 38)
COPPER = np.array((226, 146, 88), float)
EDGE = (120, 126, 132)
TEXT = (236, 236, 236)
SUB = (150, 154, 160)


def font(names, size):
    for n in names:
        for d in ('/usr/share/fonts/noto', '/usr/share/fonts/TTF', '/usr/share/fonts/truetype/noto',
                  '/usr/share/fonts/truetype/dejavu'):
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def raster(layers, tmp, name, drills='2'):
    svg = os.path.join(tmp, name + '.svg')
    subprocess.run([KCLI, 'pcb', 'export', 'svg', '--mode-single', '--layers', layers, '--page-size-mode', '2',
                    '--exclude-drawing-sheet', '--drill-shape-opt', drills, '--black-and-white', '-o', svg, PCB],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    png = os.path.join(tmp, name + '.png')
    subprocess.run(['rsvg-convert', '-b', 'white', '-w', str(PANEL_W), svg, '-o', png], check=True)
    return 1.0 - np.asarray(Image.open(png).convert('L'), float) / 255.0       # 1 = copper / line


def main():
    with tempfile.TemporaryDirectory() as tmp:
        edge = raster('Edge.Cuts', tmp, 'edge', drills='0')
        cu = [raster(l, tmp, l.replace('.', '_')) for l, _, _ in LAYERS]
    h, w = edge.shape
    # board area: flood-fill the outline from the board centre
    em = Image.fromarray((edge > 0.3).astype(np.uint8) * 255)
    ImageDraw.floodfill(em, (w // 2, h // 2), 128)
    inside = (np.asarray(em) > 0).astype(float)

    pad, gap, head, label = 70, 56, 150, 104
    W = 2 * w + gap + 2 * pad
    H = head + 2 * (h + label) + gap + pad
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title = font(['NotoSans-Medium.ttf', 'DejaVuSans.ttf'], 46)
    f_sub = font(['NotoSans-Regular.ttf', 'DejaVuSans.ttf'], 28)
    f_lab = font(['JetBrainsMonoNerdFont-Regular.ttf', 'DejaVuSansMono.ttf'], 34)
    d.text((pad, 44), 'neurband rev C main board: four copper layers', font=f_title, fill=TEXT)
    d.text((pad, 104), '28.7 × 27 mm, 1.0 mm thick, all layers seen from the top', font=f_sub, fill=SUB)
    for k, (m, (_, name, what)) in enumerate(zip(cu, LAYERS)):
        x0 = pad + (k % 2) * (w + gap)
        y0 = head + (k // 2) * (h + label + gap)
        a = np.clip(m, 0, 1)[..., None]
        base = np.where(inside[..., None] > 0, np.array(SUBSTRATE, float), np.array(BG, float))
        px = base * (1 - a) + COPPER * a
        e = np.clip(edge, 0, 1)[..., None]
        px = px * (1 - e) + np.array(EDGE, float) * e
        img.paste(Image.fromarray(px.astype(np.uint8)), (x0, y0))
        d.text((x0, y0 + h + 22), name, font=f_lab, fill=TEXT)
        d.text((x0 + 250, y0 + h + 27), what, font=f_sub, fill=SUB)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT, optimize=True)
    print(OUT, img.size)


if __name__ == '__main__':
    main()
