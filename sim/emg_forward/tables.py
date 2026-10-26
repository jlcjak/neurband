"""Markdown tables for the doc (muscle/tendon content at the band, MU pools)."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geometry import build_model, MUSCLES, muscle_fraction  # noqa: E402
from sources import build_pools  # noqa: E402


def muscle_table():
    m = build_model()
    pools = build_pools(m, np.random.default_rng(1))
    a = m.h[0] * m.h[1]
    rows = ["| Compartment | Role | Area (mm²) | Muscle area at z = 30 / 40 / 50 mm (mm²) | Distal MTJ z (mm) | Fibre length (mm) | MUs / fibres modelled |",
            "|---|---|---|---|---|---|---|"]
    for k, mu in enumerate(MUSCLES):
        comp = (m.comp2d == k).sum() * a
        ar = [(m.comp3d[:, :, int(np.argmin(abs(m.z - zz)))] == k).sum() * a for zz in (30, 40, 50)]
        mtj = "—" if mu.z_mtj < -1e8 else f"{mu.z_mtj:.0f}"
        if mu.name == "PQ":
            mtj = f"spans {mu.z_range[0]:.0f}-{mu.z_range[1]:.0f}, transverse fibres"
        p = pools.get(mu.name, [])
        rows.append(f"| {mu.label} ({mu.name}) | {mu.role} | {comp:.0f} | {ar[0]:.0f} / {ar[1]:.0f} / {ar[2]:.0f} | {mtj} | "
                    f"{mu.fibre_len:.0f} | {len(p)} / {sum(x.n_fibres for x in p)} |")
    return "\n".join(rows)


if __name__ == "__main__":
    print(muscle_table())
