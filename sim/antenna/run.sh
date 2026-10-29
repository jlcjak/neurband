#!/bin/bash
# Run one or more antenna cases: sim/antenna/run.sh <res> <threads> case1 [case2 ...]
# Needs the openEMS conda env described in docs/science/antenna_sim.md (OE_PREFIX).
OE_PREFIX=${OE_PREFIX:-$HOME/.local/mm/root/envs/oe}
HERE=$(cd "$(dirname "$0")" && pwd)
res=$1; thr=$2; shift 2
for c in "$@"; do
  LD_LIBRARY_PATH=$OE_PREFIX/lib $OE_PREFIX/bin/python "$HERE/model.py" --case "$c" --res "$res" --threads "$thr" \
    > "$HERE/build/log_${c}_r${res}.txt" 2>&1
  tail -1 "$HERE/build/log_${c}_r${res}.txt"
done
