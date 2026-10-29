# Main board, rev C

| File | What it is |
|---|---|
| `neurband_c.kicad_pro` / `.kicad_pcb` / `.kicad_sch` | The KiCad project. Open the `.kicad_pro` |
| `gen_c_sch.py` | Generates the schematic (`python3 gen_c_sch.py`); edit this, not the `.kicad_sch` |
| `ORDERING.md`, `neurband_c.fab.json` | How the board is ordered (**Buy it**) |
| `neurband_c_bom.csv` | Bill of materials with MPNs and the fab's part numbers |
| `neurband_c.step`, `neurband_c_board_only.step` | 3D models, with and without parts |
| `renders/` | Top, bottom, 3D and per-layer images |
| `layout/neurband.pretty`, `layout/models` | Local footprints and 3D models the board needs |
| `layout/*.md`, `layout/preorder_release.json`, `layout/XUNPU_*` | Evidence: RF geometry, J1 connector review, release checks |

Layout notes: [docs/layout/main_c_layout.md](../../docs/layout/main_c_layout.md). The scripts used while
laying it out are in [archive/neurband_c_layout_scripts](../../archive/neurband_c_layout_scripts/).
