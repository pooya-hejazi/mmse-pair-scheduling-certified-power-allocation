# -*- coding: utf-8 -*-
"""E2: run the frozen optimizer and baselines on the Sionna cross-check cases."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PHASE3, SECONDS, add_repo_to_path, case_gain

add_repo_to_path()
import local_core  # noqa: E402
import matching_baseline  # noqa: E402
from run_benchmark_m2 import case_rate  # noqa: E402
from run_pilot import proposed  # noqa: E402

local_core.GRID_LEVELS = (F(1, 20), F(1, 10), F(1, 5))
CASES = PHASE3 / "cases"
OUT = PHASE3 / "output"


def run_case(case: dict, seconds: float) -> dict:
    rec = dict(name=case["name"], profile=case["metadata"]["profile"],
               separation=case["metadata"]["separation_deg"],
               seed=case["metadata"]["seed"],
               realization=case["metadata"].get("realization", 0),
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
    try:
        rec["gain"] = case_gain(rec)
    except Exception:
        rec["gain"] = None
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=SECONDS)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="e2_results.csv")
    ap.add_argument("--glob", default="*-sionna-r*.json")
    ap.add_argument("--names-file")
    ap.add_argument("--cases-dir", default=str(CASES))
    args = ap.parse_args()

    paths = sorted(Path(args.cases_dir).glob(args.glob))
    if args.names_file:
        wanted = set(Path(args.names_file).read_text(encoding="utf-8").split())
        paths = [p for p in paths if p.stem in wanted]
    if args.limit:
        paths = paths[:args.limit]
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / args.out
    rows = []
    if out_path.exists() and not args.limit:
        rows = list(csv.DictReader(out_path.open(encoding="utf-8")))
    done = {r["name"] for r in rows}
    for i, path in enumerate(paths):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case["name"] in done:
            continue
        print(f"[{i+1}/{len(paths)}] {case['name']}", flush=True)
        rec = run_case(case, args.seconds)
        rows.append(rec)
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print("DONE", len(rows))


if __name__ == "__main__":
    main()
