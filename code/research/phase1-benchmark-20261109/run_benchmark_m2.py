# -*- coding: utf-8 -*-
"""Run the Phase-1 M=2 benchmark: full baselines vs proposed DP+SCA."""
from pathlib import Path
import csv
import json
import math
import sys
import time
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "research" / "manuscript-refinement-20261106" / "certification"
BENCH = ROOT / "research" / "phase1-benchmark-20261109" / "cases"
OUT = ROOT / "research" / "phase1-benchmark-20261109"
sys.path.insert(0, str(CERT))
sys.path.insert(0, str(ROOT / "research" / "completion-20261031" / "confirmation"))
sys.path.insert(0, str(ROOT / "research" / "dual-track-revision-20261103" / "baseline-code"))
import checker  # noqa: E402
import producer  # noqa: E402
import local_core  # noqa: E402
import matching_baseline  # noqa: E402
from run_pilot import q_rate, best_assignment, schedule_from_pairs, proposed  # noqa: E402

local_core.GRID_LEVELS = (F(1, 20), F(1, 10), F(1, 5))


def case_rate(result, case):
    if result.get("rate_nats") is not None:
        return float(result["rate_nats"])
    sched = result.get("schedule", [])
    if not sched:
        return None
    _, _, _, _, _, data, _ = checker.reconstruct(case)
    return sum(q_rate(data[tuple(sorted(row["users"])) + (row["resource"],)],
                      F(row["powers"][0]), F(row["powers"][1])) for row in sched)


def main():
    paths = sorted(BENCH.glob("*-M2.json"))
    rows = []
    for i, path in enumerate(paths):
        case = json.loads(path.read_text(encoding="utf-8"))
        seconds = 20 if case["K"] == 16 else 12
        print(f"[{i+1}/{len(paths)}] {case['name']} K={case['K']}", flush=True)
        rec = dict(name=case["name"], scene=case["metadata"].get("scene", case["name"].split("-")[0]),
                   K=case["K"], M=case["M"], seconds=seconds)
        for method, fn in [
            ("grid", lambda: local_core.solve(case, "grid", seconds)),
            ("slsqp", lambda: local_core.solve(case, "slsqp", seconds)),
            ("iwmmse", lambda: local_core.solve(case, "iwmmse", seconds)),
            ("matching", lambda: matching_baseline.solve(case, seconds, seed=1101)),
            ("proposed", lambda: proposed(case, seconds)),
        ]:
            t0 = time.perf_counter()
            try:
                res = fn()
                rate = res["rate_nats"] if method == "proposed" else case_rate(res, case)
                rec[f"{method}_rate"] = rate
                rec[f"{method}_status"] = res.get("status", "proposed")
                rec[f"{method}_time"] = res.get("elapsed", time.perf_counter() - t0)
                print(f"  {method:9s} {rate:.6f} {rec[f'{method}_time']:.2f}s", flush=True)
            except Exception as exc:
                rec[f"{method}_rate"] = None
                rec[f"{method}_status"] = f"ERROR {type(exc).__name__}: {exc}"
                rec[f"{method}_time"] = time.perf_counter() - t0
                print(f"  {method:9s} ERROR {exc}", flush=True)
        rows.append(rec)
        with open(OUT / "m2_results.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)
    print("DONE", len(rows))


if __name__ == "__main__":
    main()
