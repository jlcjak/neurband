# Mechanics

Everything current is in [`rev_c/`](rev_c/): one FreeCAD script per part (`module.py`, `pod.py`,
`strap.py`, `charge_puck.py`), the fit and assembly scripts, their STEP files and the parts' fab files.
`cadutil.py` and `fitgeom.py` here are shared helpers those scripts import.

Design notes: [docs/mech/mechanical_c.md](../docs/mech/mechanical_c.md). Build guide:
[docs/build/assembly.md](../docs/build/assembly.md). The rev A/B mechanics are in
[archive/mech_revAB](../archive/mech_revAB/).
