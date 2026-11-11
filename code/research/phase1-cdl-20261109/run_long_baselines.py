# -*- coding: utf-8 -*-
"""Sensitivity: give SLSQP and Matching 30 s on a 12-case CDL subset."""
from pathlib import Path
import csv
import json
import sys
import time
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "research" / "manuscript-refinement-20261106" / "certification"
CDL = ROOT / "research" / "phase1-cdl-20261109"
sys.path.insert(0, str(CERT))
sys.path.insert(0, str(ROOT / "research" / "completion-20261031" / "confirmation"))
sys.path.insert(0, str(ROOT / "research" / "dual-track-revision-20261103" / "baseline-code"))
sys.path.insert(0, str(ROOT / "research" / "phase1-benchmark-20261109"))
import local_core  # noqa: E402
import matching_baseline  # noqa: E402
from run_benchmark_m2 import case_rate  # noqa: E402
from run_pilot import proposed  # noqa: E402

local_core.GRID_LEVELS = (F(1, 20), F(1, 10), F(1, 5))


def main():
    paths = []
    for p in "ABC":
        paths += sorted((CDL / "cases").glob(f"cdl-{p.lower()}-sep2-s*.json"))[:4]
    rows = []
    for path in paths:
        case = json.loads(path.read_text(encoding="utf-8"))
        print(case["name"], flush=True)
        rec = dict(name=case["name"], profile=case["metadata"]["profile"])
        for method, fn, sec in [
            ("matching30", lambda: matching_baseline.solve(case, 30, seed=1101), 30),
            ("slsqp30", lambda: local_core.solve(case, "slsqp", 30), 30),
            ("proposed10", lambda: proposed(case, 10), 10),
        ]:
            try:
                res = fn()
                rate = res["rate_nats"] if method.startswith("proposed") else case_rate(res, case)
                rec[method] = rate
                print(f"  {method} {rate:.6f}", flush=True)
            except Exception as exc:
                rec[method] = None
                print(f"  {method} ERROR {exc}", flush=True)
        rows.append(rec)
        with open(CDL / "cdl_long_baseline.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
