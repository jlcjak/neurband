#!/bin/sh
# Re-run every neurband rev C AFE simulation (ngspice-47 + numpy + matplotlib). Outputs: sim/out/
set -e
cd "$(dirname "$0")"
for s in q1_rld_loop q2_cm_to_dm q3_input_filter q4_supply; do
    echo "== $s"; python3 "$s.py" > "out/$s.log" 2>&1; tail -3 "out/$s.log"
done
