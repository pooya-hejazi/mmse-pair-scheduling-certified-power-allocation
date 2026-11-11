# -*- coding: utf-8 -*-
"""Ablation on the 3GPP CDL K=16 cases."""
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
sys.path.insert(0, str(ROOT / "research" / "phase1-benchmark-20261109"))
import checker  # noqa: E402
import producer  # noqa: E402
from run_pilot import q_rate, best_assignment, proposed  # noqa: E402


def main():
    rows = []
    for path in sorted((CDL / "cases").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        k, s, low, high, budget, data, gains = checker.reconstruct(case)
        seq = [(2*t, 2*t+1) for t in range(s)]
        uniform = [budget / k] * k
        u = sum(q_rate(data[a, b, t], uniform[a], uniform[b]) for t, (a, b) in enumerate(seq))
        pairs, _ = best_assignment(k, s, data, uniform)
        a = sum(q_rate(data[x, y, t], uniform[x], uniform[y]) for t, (x, y) in enumerate(pairs))
        pp, _ = producer.refine(seq, uniform, data, low, high, budget, time.perf_counter()+5)
        p = sum(q_rate(data[x, y, t], pp[x], pp[y]) for t, (x, y) in enumerate(seq))
        j = proposed(case, 10)["rate_nats"]
        rows.append(dict(name=case["name"], profile=case["metadata"]["profile"],
                         uniform=u, assignment=a, power=p, joint=j))
        print(case["name"], "uniform", round(u, 3), "assignment", round(a, 3), "power", round(p, 3), "joint", round(j, 3), flush=True)
        with open(CDL / "cdl_ablation.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
