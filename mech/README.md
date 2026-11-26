# Neurband mechanics

FreeCAD scripts for the housing of **neurband rev C**. Build notes, print settings and assembly:
[rev_c/README.md](rev_c/README.md).

## Structure

- `cadutil.py`, `fitgeom.py`: shared FreeCAD helpers and the older forearm-ellipse model
- `rev_c/`
  - `params.py`: every dimension (pure Python)
  - `fit.py`: 2D fit of the band on wrist cross-sections; compares the cradle with the flat case it replaced
  - `module.py`: `cradle`, `holder`, `lug_bar` and `lid`, checked against the real board model, the cell and the flex tail
  - `band.py`: `pod`, `bond_jig`, and the band on a wrist (`band_assembly.step`, `band_assembly_wrap.step`)
  - `sections.py`: exact cross-section drawings and half models
  - `export_to_print.py`: `to_print/` (parts lying on the bed) and the `.fab.json` files
  - `ref/neurband_c_parts.step`: the main board with its components, exported from KiCad
  - `to_print/`: bed-oriented STEP files and Bambu Studio plates

## Rebuild

```bash
python3 mech/rev_c/fit.py
unset DISPLAY WAYLAND_DISPLAY
for f in module band sections jig_adapters export_to_print; do QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/$f.py; done
python3 mech/rev_c/sections.py
python3 render/rev_c_views.py
```
