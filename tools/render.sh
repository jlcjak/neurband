#!/bin/bash
# render.sh <file.kicad_sch> <outdir> [width_px]  -> outdir/<name>.png
K=${KICAD_CLI:-$HOME/.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli}
mkdir -p "$2"
$K sch export svg --no-background-color -o "$2" "$1" >/dev/null 2>&1
for f in "$2"/*.svg; do rsvg-convert -b white -w ${3:-4000} "$f" -o "${f%.svg}.png"; done
ls "$2"/*.png
