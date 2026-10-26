"""Model-uncertainty checks on the 8 baseline channels: grid refinement and tissue-parameter variants.

Each variant recomputes the 16 monopolar lead fields; MU pools are those of the baseline model
(same fibres in mm coordinates) except for the fat-thickness variant, whose anatomy changes.
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "4")
import json
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geometry import SIG, build_model, Z_BAND  # noqa: E402
from leadfield import CACHE  # noqa: E402
from study import Study, ALL, VIS  # noqa: E402


def main():
    base_model = build_model()
    ref = Study()
    C8 = ref.config()
    keep = {ref.els[i].key() for i in np.r_[C8[0], C8[1]]}
    S_ref = ref.sens(C8) * 1e6
    variants = {
        "grid_1mm": dict(h=(1.0, 1.0, 1.0), variant="", variant_kwargs={}, pool_model=base_model),
        "itis_conductivities": dict(h=(0.5, 0.5, 1.0), variant="itis",
                                    variant_kwargs=dict(sig=dict(SIG, muscle_L=0.415, muscle_T=0.132, fat=0.0776,
                                                                 skin=0.148, tendon=0.368, bone_cortical=0.0063)),
                                    pool_model=base_model),
        "skin_0.4": dict(h=(0.5, 0.5, 1.0), variant="skin04", variant_kwargs=dict(sig=dict(SIG, skin=0.4)),
                         pool_model=base_model),
        "fat_5mm": dict(h=(0.5, 0.5, 1.0), variant="fat5", variant_kwargs=dict(t_fat=5.0), pool_model=None),
        "muscle_isotropic_0.3": dict(h=(0.5, 0.5, 1.0), variant="isomus",
                                     variant_kwargs=dict(sig=dict(SIG, muscle_L=0.3, muscle_T=0.3)), pool_model=base_model),
    }
    out = {}
    for name, kw in variants.items():
        st = Study(h=kw["h"], variant=kw["variant"], variant_kwargs=kw["variant_kwargs"], pool_model=kw["pool_model"],
                   electrodes=lambda els: [e for e in els if e.key() in keep])
        S = st.sens(st.config()) * 1e6
        r = {}
        for n in VIS:
            j = ALL.index(n)
            r[n] = dict(max_ratio=float(S[:, j].max() / S_ref[:, j].max()),
                        corr=float(np.corrcoef(S[:, j], S_ref[:, j])[0, 1]))
        A = S[:, [ALL.index(n) for n in VIS]]
        A = A / np.linalg.norm(A, axis=0)
        sv = np.linalg.svd(A, compute_uv=False)
        out[name] = dict(per_muscle=r,
                         median_amp_ratio=float(np.median([v["max_ratio"] for v in r.values()])),
                         min_corr=float(min(v["corr"] for v in r.values())),
                         cond=float(sv[0] / sv[-1]))
        print(name, json.dumps({k: v for k, v in out[name].items() if k != "per_muscle"}), flush=True)
    with open(os.path.join(CACHE, "sensitivity.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
