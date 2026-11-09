# -*- coding: utf-8 -*-
"""Ablation: uniform, assignment-only, power-only, joint on M=2 cases."""
from pathlib import Path
import csv
import json
import sys
import time
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "research" / "manuscript-refinement-20261106" / "certification"
BENCH = ROOT / "research" / "phase1-benchmark-20261109" / "cases"
OUT = ROOT / "research" / "phase1-benchmark-20261109"
sys.path.insert(0, str(CERT))
sys.path.insert(0, str(OUT))
import checker  # noqa: E402
import producer  # noqa: E402
from run_pilot import q_rate, best_assignment, schedule_from_pairs, proposed  # noqa: E402


def main():
    rows = []
    for path in sorted(BENCH.glob("*-M2.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        k, s, low, high, budget, data, gains = checker.reconstruct(case)
        seq = [(2 * t, 2 * t + 1) for t in range(s)]
        uniform = [budget / k] * k
        uniform_rate = sum(q_rate(data[u, v, t], uniform[u], uniform[v]) for t, (u, v) in enumerate(seq))
        assign, _ = best_assignment(k, s, data, uniform)
        assign_rate = sum(q_rate(data[u, v, t], uniform[u], uniform[v]) for t, (u, v) in enumerate(assign))
        deadline = time.perf_counter() + 5.0
        power_p, _ = producer.refine(seq, uniform, data, low, high, budget, deadline)
        power_rate = sum(q_rate(data[u, v, t], power_p[u], power_p[v]) for t, (u, v) in enumerate(seq))
        joint = proposed(case, 20)
        rec = dict(name=case["name"], scene=case["metadata"].get("scene", case["name"].split("-")[0]),
                   K=case["K"], M=case["M"], uniform=uniform_rate, assignment=assign_rate,
                   power_only=power_rate, joint=joint["rate_nats"])
        rows.append(rec)
        print(f"{case['name']}: uniform={uniform_rate:.4f} assign={assign_rate:.4f} "
              f"power={power_rate:.4f} joint={joint['rate_nats']:.4f}", flush=True)
    with open(OUT / "m2_ablation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
