# -*- coding: utf-8 -*-
"""Pilot: proposed exact-DP + SCA versus full baselines on Phase-1 variants."""
from pathlib import Path
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

local_core.GRID_LEVELS = (F(1, 20), F(1, 10), F(1, 5))


def q_rate(coeff, p, q):
    g1, g2, r = coeff
    x = float(g1) * float(p)
    y = float(g2) * float(q)
    d = 1.0 + x + y + (1.0 - float(r)) * x * y
    return 2.0 * math.log(d) - math.log1p(x) - math.log1p(y)


def best_assignment(k, s, data, powers):
    n = 1 << k
    weights = {(u, v, t): q_rate(coeff, powers[u], powers[v]) for (u, v, t), coeff in data.items()}
    neg = -1e300
    values = [neg] * n
    choice = [None] * n
    values[0] = 0.0
    for mask in range(1, n):
        bits = mask.bit_count()
        if bits % 2:
            continue
        t = bits // 2 - 1
        best, pair = neg, None
        rem = mask
        while rem:
            ub = rem & -rem
            rem -= ub
            u = ub.bit_length() - 1
            tail = rem
            while tail:
                vb = tail & -tail
                tail -= vb
                v = vb.bit_length() - 1
                old = mask ^ ub ^ vb
                cand = values[old] + weights[u, v, t]
                if cand > best:
                    best, pair = cand, (u, v)
        values[mask], choice[mask] = best, pair
    pairs = [None] * s
    mask = n - 1
    for t in reversed(range(s)):
        u, v = choice[mask]
        pairs[t] = (u, v)
        mask ^= (1 << u) | (1 << v)
    return pairs, values[-1]


def rate(schedule, data):
    return sum(q_rate(data[u, v, t], F(p1), F(p2))
               for t, (u, v, p1, p2) in enumerate(schedule))


def schedule_from_pairs(pairs, powers):
    return [(min(u, v), max(u, v), str(powers[u]), str(powers[v])) for u, v in pairs]


def proposed(case, seconds=20.0):
    import numpy as np
    began = time.perf_counter()
    k, s, low, high, budget, data, gains = checker.reconstruct(case)
    rng = np.random.default_rng(20261109)

    def descent(pairs, powers):
        best_rate = rate(schedule_from_pairs(pairs, powers), data)
        best_pairs, best_powers = list(pairs), list(powers)
        for _ in range(8):
            if time.perf_counter() - began > seconds:
                break
            new_pairs, _ = best_assignment(k, s, data, powers)
            deadline = min(began + seconds, time.perf_counter() + 5.0)
            refined, status = producer.refine(new_pairs, powers, data, low, high, budget, deadline)
            new_rate = rate(schedule_from_pairs(new_pairs, refined), data)
            if new_rate > best_rate + 1e-9:
                best_rate, best_pairs, best_powers = new_rate, list(new_pairs), list(refined)
            if new_pairs == pairs and max(abs(float(a - b)) for a, b in zip(refined, powers)) < 1e-6:
                break
            pairs, powers = new_pairs, refined
        return best_rate, best_pairs, best_powers

    # Start 0: sequential pairing + uniform budget.
    seq = [(2 * t, 2 * t + 1) for t in range(s)]
    starts = [(seq, [budget / k] * k)]
    # Random starts: random permutation and feasible random powers.
    for _ in range(7):
        perm = list(rng.permutation(k))
        pairs = [tuple(sorted((int(perm[2 * t]), int(perm[2 * t + 1])))) for t in range(s)]
        raw = [float(low) + rng.random() * (float(high) - float(low)) for _ in range(k)]
        scale = min(1.0, float(budget) / max(sum(raw), 1e-12))
        powers = [low + F(float(x * scale)).limit_denominator(10**9) for x in raw]
        # Repair exactly by reducing the largest entries.
        excess = sum(powers, F(0)) - budget
        if excess > 0:
            for i in sorted(range(k), key=lambda j: powers[j], reverse=True):
                take = min(excess, powers[i] - low)
                powers[i] -= take
                excess -= take
                if excess == 0:
                    break
        starts.append((pairs, powers))

    best = None
    for pairs, powers in starts:
        if time.perf_counter() - began > seconds:
            break
        candidate = descent(pairs, powers)
        if best is None or candidate[0] > best[0]:
            best = candidate
    best_rate, best_pairs, best_powers = best
    return dict(method="proposed_dp_sca_multistart", rate_nats=best_rate,
                schedule=schedule_from_pairs(best_pairs, best_powers),
                elapsed=time.perf_counter() - began, iterations=len(starts))


def baseline_rate(result, case):
    if result.get("rate_nats") is not None:
        return float(result["rate_nats"])
    sched = result.get("schedule", [])
    if not sched:
        return None
    _, _, _, _, _, data, _ = checker.reconstruct(case)
    return sum(q_rate(data[tuple(sorted(row["users"])) + (row["resource"],)],
                      F(row["powers"][0]), F(row["powers"][1])) for row in sched)


def main():
    names = ["asu-main-00-M2", "asu-main-01-M4", "o1-main-00-M2", "o1-main-01-M4",
             "asu-scale-00-M2", "o1-scale-00-M2"]
    for name in names:
        case = json.loads((BENCH / (name + ".json")).read_text(encoding="utf-8"))
        print("=====", name, "K", case["K"], "M", case["M"], flush=True)
        rows = {}
        for method, fn in [
            ("grid", lambda: local_core.solve(case, "grid", 20)),
            ("slsqp", lambda: local_core.solve(case, "slsqp", 20)),
            ("iwmmse", lambda: local_core.solve(case, "iwmmse", 20)),
            ("matching", lambda: matching_baseline.solve(case, 20, seed=1101)),
            ("proposed", lambda: proposed(case, 20)),
        ]:
            t0 = time.perf_counter()
            try:
                res = fn()
                r = baseline_rate(res, case) if method != "proposed" else res["rate_nats"]
                rows[method] = dict(rate=r, status=res.get("status"), elapsed=res.get("elapsed", time.perf_counter() - t0))
                print(f"  {method:9s} rate={r:.6f} status={res.get('status')} time={rows[method]['elapsed']:.2f}s", flush=True)
            except Exception as exc:
                print(f"  {method:9s} ERROR {type(exc).__name__}: {exc}", flush=True)
                rows[method] = dict(rate=None, error=str(exc))
        (OUT / "pilot" ).mkdir(exist_ok=True)
        (OUT / "pilot" / (name + ".json")).write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
