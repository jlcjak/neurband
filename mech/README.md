# Neurband mechanics

FreeCAD scripts for the housing of **neurband rev C**. The current housing is mechanical revision 2,
in `rev_c2/`: build notes, print settings and what is not yet verified are in
[rev_c2/README.md](rev_c2/README.md); assembly is in [docs/build/assembly.md](../docs/build/assembly.md).
`rev_c/` is the earlier three-piece case (cradle, holder, lid, foam dots), kept for reference.

## Structure

- `cadutil.py`, `fitgeom.py`: shared FreeCAD helpers and the older forearm-ellipse model
- `rev_c2/`
  - `params.py`: every dimension (pure Python), with the flex-tail length budget
  - `springs.py`: beam model of a pod wing (stiffness, strain, tilt)
  - `fit.py`: 2D fit of the band on wrist cross-sections; compares this case with the rev C1 cradle
  - `case.py`: `tub`, `lid` and `lug_bar`, checked against the real board model, the cell, the leads and the flex tail
  - `pod.py`: the pod with its two spring wings
  - `tray.py`: the bonding tray, with the tub and pods pressed on
  - `band.py`: the band on a wrist (`band_assembly.step`)
  - `sections.py`: exact cross-section drawings
  - `export_to_print.py`: `to_print/` (parts lying on the bed) and the `.fab.json` files
  - `make_plate.py`: the two Bambu Studio projects in `to_print/`
  - `ref/neurband_c_parts.step`: the main board with its components, exported from KiCad
- `rev_c/`: the earlier housing, same layout (`module.py`, `band.py`, `jig_adapters.py`)

## Rebuild

```bash
python3 mech/rev_c2/springs.py
python3 mech/rev_c2/fit.py
unset DISPLAY WAYLAND_DISPLAY
for f in pod case tray band sections export_to_print make_plate; do QT_QPA_PLATFORMTHEME="" QT_QPA_PLATFORM=offscreen timeout 600 /usr/bin/freecad mech/rev_c2/$f.py; done
python3 mech/rev_c2/sections.py
```

Each script writes a log into `rev_c2/logs/` with its checks: valid solids, clash volumes against the
board, cell and flex, the lid's way on and off, overhangs and bridges in print orientation.
