#!/bin/sh
# Pre-order analog review of rev C (docs/review/analog_preorder_review.md). Read-only on design files.
# Needs numpy, scipy, shapely, matplotlib (a venv in sim/preorder/build/.venv) and ngspice for q5.
#   uv venv sim/preorder/build/.venv && uv pip install --python sim/preorder/build/.venv/bin/python numpy scipy shapely matplotlib
# Outputs: sim/preorder/out/ (small CSV/JSON/PNG), sim/preorder/build/ (plots, logs; gitignored).
set -e
cd "$(dirname "$0")"
PY=${PY:-build/.venv/bin/python}
$PY xsec_tables.py > build/xsec_tables.log          # 2D FD capacitance tables, ~5 min
$PY xsec_broadside_between.py >> build/xsec_tables.log
$PY coupling.py                                      # victim/aggressor geometry -> out/coupling_pairs.csv
$PY inject.py | tee build/inject.log                 # in-band uV per pair / channel
$PY ground.py > build/ground.log                     # In1 voids, pour fragments, stitching
$PY q5_input_options.py | tee build/q5.log           # series R / C0G caps / BIAS_E cap / TVS / ESD (ngspice)
$PY flex_field.py | tee build/flex_field.log         # external-field pickup on flex traces, ~8 min
$PY plot_layers.py && $PY plot_hotspots.py

# ---- 2026-10-29 re-check of the reworked board (as-built 3313 stack, 10 kOhm arrays) ----
STACK=3313 $PY xsec_tables.py > build/xsec_3313.log && STACK=3313 $PY xsec_broadside_between.py >> build/xsec_3313.log
XSEC=xsec_tables_3313.json TAG=_rework3313 RSER=10000 $PY coupling.py
XSEC=xsec_tables_3313.json TAG=_rework3313 RSER=10000 $PY inject.py > build/inject_rework3313.log
XSEC=xsec_tables_3313.json TAG=_rework3313 RSER=10000 $PY via_lands.py | tee build/via_lands_rework3313.log
TAG=_rework $PY ground.py > build/ground_rework.log
TAG=_rework $PY nrf_rf_check.py > build/nrf_rf_check_rework.log
TAG=_rework $PY power_paths.py | tee build/power_paths_rework.log
$PY q6_rework_loop.py | tee build/q6.log
# pre-rework comparison: git show <rev>:boards/neurband_c/neurband_c.kicad_pcb > build/neurband_c_head.kicad_pcb
#   PCB=build/neurband_c_head.kicad_pcb TAG=_head $PY nrf_rf_check.py
