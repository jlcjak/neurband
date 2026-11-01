# Mechanics

Everything current is in [`rev_c/`](rev_c/): one FreeCAD script per part (`module.py`: base with the two
integral strap bars, lid, button cap, cell spacer; `pod.py`; `bond_jig.py` and `base_jig.py`, the two bonding
stages), `strap.py` (the bought hook-and-loop strap and the strength log of its anchor), the fit and assembly
scripts (`fit.py`, `assembly.py`), `wallcheck.py`, their STEP files and the parts' fab files. Retired in r2 and
not ordered: `strap_slide`, `charge_clip`, `swd_jig` (`"order": false`). `ref/` holds the main board STEP
exported from the KiCad file for the fit checks (the r1 scripts are in git history).
`cadutil.py` and `fitgeom.py` here are shared helpers those scripts import.

Design notes: [docs/mech/mechanical_c.md](../docs/mech/mechanical_c.md). Build guide:
[docs/build/assembly.md](../docs/build/assembly.md). The rev A/B mechanics are in
[.archive/mech_revAB](../.archive/mech_revAB/).
