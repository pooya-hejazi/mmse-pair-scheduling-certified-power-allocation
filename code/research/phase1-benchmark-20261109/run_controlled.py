# -*- coding: utf-8 -*-
"""Run controlled K=16, M=2 cases."""
from pathlib import Path
import csv
import json
import sys
import time
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "research" / "manuscript-refinement-20261106" / "certification"
OUT = ROOT / "research" / "phase1-benchmark-20261109"
CASES = OUT / "controlled_cases"
sys.path.insert(0, str(CERT))
sys.path.insert(0, str(ROOT / "research" / "completion-20261031" / "confirmation"))
sys.path.insert(0, str(ROOT / "research" / "dual-track-revision-20261103" / "baseline-code"))
sys.path.insert(0, str(OUT))
import local_core  # noqa: E402
import matching_baseline  # noqa: E402
from run_benchmark_m2 import case_rate  # noqa: E402
from run_pilot import proposed  # noqa: E402

local_core.GRID_LEVELS = (F(1, 20), F(1, 10), F(1, 5))


def main():
    rows = []
    for i, path in enumerate(sorted(CASES.glob("*.json"))):
        case = json.loads(path.read_text(encoding="utf-8"))
        seconds = 10
        print(f"[{i+1}] {case['name']} {case['metadata']['snr_db']}dB nf={case['metadata']['nearfar_db']}", flush=True)
        rec = dict(name=case["name"], scene="controlled", K=case["K"], M=case["M"], seconds=seconds,
                   snr_db=case["metadata"]["snr_db"], nearfar_db=case["metadata"]["nearfar_db"])
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
        with open(OUT / "controlled_results.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
