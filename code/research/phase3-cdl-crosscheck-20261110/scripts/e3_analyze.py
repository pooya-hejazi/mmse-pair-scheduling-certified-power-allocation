# -*- coding: utf-8 -*-
"""E3-A analysis: does the angle-model ablation explain the E2 difference?"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PHASE3, bootstrap_ci

OUT = PHASE3 / "output"


def main() -> None:
    rows = list(csv.DictReader((OUT / "e3a_results.csv").open(encoding="utf-8")))
    g = np.asarray([float(r["gain"]) for r in rows], float)
    med = float(np.median(g))
    ci = bootstrap_ci(g, np.median, seed=20261109)
    e2 = json.loads((OUT / "e2_summary.json").read_text(encoding="utf-8"))
    orig = e2["M0"]
    e2m = e2["M_hat"]
    rel = abs(med - e2m) / max(abs(e2m), 1e-12)
    summary = dict(
        n_cases=len(g), median=med, mean=float(np.mean(g)),
        ci_median=list(ci), abs_median=float(np.median([
            (float(r["proposed_rate"]) - max(float(r["grid_rate"]), float(r["slsqp_rate"]),
             float(r["iwmmse_rate"]), float(r["matching_rate"]))) / (8 * np.log(2))
            for r in rows])),
        wins=int((g > 1e-4).sum()), ties=int((np.abs(g) <= 1e-4).sum()),
        losses=int((g < -1e-4).sum()),
        e2_median=e2m, original_median=orig,
        distance_to_e2=rel,
        angle_model_attribution=bool(rel <= 0.20),
        note=("E3-A replaces the deterministic z-scored cluster angles with i.i.d. "
              "N(0,cASA^2) offsets, holding gains and phases fixed. It is a sensitivity "
              "arm and never substitutes for E2."),
    )
    (OUT / "e3_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
