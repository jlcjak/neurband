# Archive (`.archive/`)

The folder name starts with a dot so Backplane's project and part lists skip it; git and GitHub still show it.

Older work, kept for reference. Nothing here is current or ordered (every fab file here has
`"order": false`).

| Folder | What it is |
|---|---|
| `neurband_main_revA/` | Rev A main board: 16 channels, ESP32-S3, 54 × 34 mm ([docs/DESIGN.md](../docs/DESIGN.md)) |
| `neurband_main_revB/` | Rev B main board: compact 16 channels, unfinished |
| `neurband_electrodes_revB/` | Rev B electrode flex in four sizes |
| `mech_revAB/` | Rev A/B mechanics: housing, pod shells, strap, fit checks ([docs/mech/mechanical.md](../docs/mech/mechanical.md)). The scripts import `mech/cadutil.py` and `mech/fitgeom.py` |
| `neurband_c_layout_scripts/` | The one-off scripts used while laying out the rev C main board. They record how it was done; the board file itself is now the source. They expect to run from `boards/neurband_c/layout/` |
| `local/` | Local-only backups (working copies, layout build backups); not in git |
