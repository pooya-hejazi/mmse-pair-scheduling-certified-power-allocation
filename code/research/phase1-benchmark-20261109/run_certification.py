# -*- coding: utf-8 -*-
"""Certify the proposed M=2 schedules with the frozen finite-box/integral producer."""
from pathlib import Path
import csv
import json
import sys
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "research" / "manuscript-refinement-20261106" / "certification"
BENCH = ROOT / "research" / "phase1-benchmark-20261109" / "cases"
OUT = ROOT / "research" / "phase1-benchmark-20261109"
sys.path.insert(0, str(CERT))
sys.path.insert(0, str(OUT))
import checker  # noqa: E402
import producer  # noqa: E402
from run_pilot import proposed  # noqa: E402


def main():
    rows = []
    paths = sorted(BENCH.glob("*-M2.json"))
    for i, path in enumerate(paths):
        case = json.loads(path.read_text(encoding="utf-8"))
        r = proposed(case, 20)
        sched = [{"users": [u, v], "resource": t, "powers": [p1, p2]}
                 for t, (u, v, p1, p2) in enumerate(r["schedule"])]
        pr = producer.run(case, sched, {}, seconds=10)
        upper = F(pr["metrics"]["rounds"][-1]["upper_nats"])
        k, s, low, high, budget, data, gains = checker.reconstruct(case)
        lower, _ = checker.check_schedule(sched, (k, s, low, high, budget, data, gains))
        gap = upper - lower
        rec = dict(name=case["name"], scene=case["metadata"].get("scene", case["name"].split("-")[0]),
                   K=case["K"], M=case["M"], proposed_rate=float(lower), upper_nats=float(upper),
                   gap_nats=float(gap), gap_fraction=float(gap / lower) if lower > 0 else None,
                   status=pr["metrics"]["status"], producer_seconds=pr["metrics"].get("seconds"),
                   iterations=r["iterations"])
        rows.append(rec)
        print(f"[{i+1}/{len(paths)}] {case['name']} rate={float(lower):.6f} "
              f"gap={float(gap):.3e} status={rec['status']}", flush=True)
        with open(OUT / "m2_certification.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
