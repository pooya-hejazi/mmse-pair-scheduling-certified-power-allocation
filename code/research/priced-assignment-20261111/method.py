"""Integral assignment with jointly priced pair powers and feasible local refinement."""
import os
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import importlib.util
import itertools
import math
import time
from pathlib import Path
import numpy as np
from numba import njit

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "independent-cdl-20261110" / "run_campaign.py"
spec = importlib.util.spec_from_file_location("original_cdl_campaign", ORIGINAL)
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
from modern.common import guard, project, DeadlineReached

GRID_INTERVALS = 32
PRICE_STEPS = 14


@njit
def _fill(weights, values, chosen_u, chosen_v, pop, bit_number, begin, end):
    for mask in range(begin, end):
        pop[mask] = pop[mask & (mask - 1)] + 1
        if pop[mask] & 1:
            continue
        s = pop[mask] // 2 - 1
        rem = mask
        while rem:
            ub = rem & -rem
            rem -= ub
            u = bit_number[ub]
            tail = rem
            while tail:
                vb = tail & -tail
                tail -= vb
                v = bit_number[vb]
                score = values[mask ^ ub ^ vb] + weights[s, u, v]
                if score > values[mask]:
                    values[mask] = score
                    chosen_u[mask], chosen_v[mask] = u, v


def _best_assignment(weights, deadline):
    """Exact subset recurrence on binary64 weights, in ascending pair tie order."""
    guard(deadline)
    s, k, _ = weights.shape
    if not 2 <= k <= 20 or 2*s != k:
        raise ValueError("assignment requires even 2 <= K <= 20")
    n = 1 << k
    values = np.full(n, -np.inf)
    values[0] = 0.
    chosen_u = np.zeros(n, np.int8)
    chosen_v = np.zeros_like(chosen_u)
    pop = np.zeros_like(chosen_u)
    bit_number = np.zeros_like(chosen_u)
    bit_number[1 << np.arange(k)] = np.arange(k)
    for begin in range(1, n, 2048):
        guard(deadline)
        _fill(weights, values, chosen_u, chosen_v, pop, bit_number, begin, min(n, begin+2048))
    guard(deadline)
    pairs, mask = [None]*s, n-1
    for resource in reversed(range(s)):
        u, v = int(chosen_u[mask]), int(chosen_v[mask])
        pairs[resource] = (u, v)
        mask ^= (1 << u) | (1 << v)
    return tuple(pairs), float(values[-1])


def warmup():
    """Compile once on synthetic weights, shared by every arm before search."""
    start = time.monotonic()
    _best_assignment(np.zeros((1, 2, 2)), math.inf)
    return time.monotonic() - start


def dp_assignment(k, data, powers, deadline):
    guard(deadline)
    weights = np.zeros((k//2, k, k))
    p = np.asarray(powers, dtype=float)
    for (u, v, s), (g, h, r) in data.items():
        x, y = g*p[u], h*p[v]
        weights[s, u, v] = 2*math.log(1+x+y+(1-r)*x*y)-math.log1p(x)-math.log1p(y)
    return _best_assignment(weights, deadline)


def _grid(problem):
    keys = list(problem.lookup)
    user, partner, resource = np.asarray(keys).T
    g, h, r = np.asarray([problem.lookup[key] for key in keys]).T
    lo, hi = float(problem.low), float(problem.high)
    frac = np.linspace(0, 1, GRID_INTERVALS+1)

    def axis(gain):
        gain = gain[:, None]
        left = np.log1p(gain*lo)
        log_step = (np.log1p(gain*hi)-left)/GRID_INTERVALS
        powers = np.divide(np.expm1(left + GRID_INTERVALS*log_step*frac), gain,
                           out=np.tile(lo+(hi-lo)*frac, (len(gain), 1)), where=gain != 0)
        powers[:, 0], powers[:, -1] = lo, hi
        return powers, np.expm1(log_step[:, 0])**2/8

    p, ep = axis(g)
    t, et = axis(h)
    x = g[:, None, None]*p[:, :, None]
    y = h[:, None, None]*t[:, None, :]
    d = 1+x+y+(1-r[:, None, None])*x*y
    rates = 2*np.log(d)-np.log1p(x)-np.log1p(y)
    cost = p[:, :, None]+t[:, None, :]
    # The univariate interpolation error per coordinate is at most
    # (gain * delta_power / (1 + gain * left_power))**2 / 8.
    return (user, partner, resource), p, t, rates, cost, ep+et


def solve(problem, starts, cap=10., block=5.):
    original.shared.certificates.clear_caches()
    begun = time.monotonic()
    deadline = begun + cap
    unit = problem.s*math.log(2)
    counts = dict(starts_started=0, starts_completed=0, dp_completed=0, power_calls=0, accepted=0,
                  price_dp_completed=0, price_schedules=0)
    history, diagnostics = [], []
    best = problem.checked_candidate(*starts[0])
    problem.matrix_scalar_check(best)

    def record(candidate, kind):
        return dict(kind=kind, seconds=time.monotonic()-begun, schedule=candidate["schedule"],
                    rate_nats=candidate["value"], se_bits=candidate["value"]/unit,
                    lower_nats=str(candidate["lo"]), upper_nats=str(candidate["hi"]))

    history.append(record(best, "initial"))

    def retain(a, p):
        nonlocal best
        guard(deadline)
        candidate = problem.checked_candidate(a, p)
        problem.matrix_scalar_check(candidate)
        guard(deadline)
        if problem.improves(candidate, best):
            row = record(candidate, "improvement")
            guard(deadline)
            history.append(row)
            best = candidate
            counts["accepted"] += 1
        return candidate

    def polish(current):
        guard(deadline)
        a = current["assignment"]
        stop = time.perf_counter()+max(0., min(block, deadline-time.monotonic()))
        counts["power_calls"] += 1
        p, d = original.shared.producer.refine(a, current["powers"], problem.model.data,
                                               problem.low, problem.high, problem.budget, stop)
        diagnostics.append(dict(method="LOCAL_SQP", **d))
        candidate = retain(a, p)
        return candidate if problem.improves(candidate, current) else current

    def alternate(current):
        for _ in range(8):
            a, value = dp_assignment(problem.k, problem.lookup, current["powers"], deadline)
            counts["dp_completed"] += 1
            assigned = retain(a, current["powers"])
            if abs(value-assigned["value"]) > 1e-7:
                raise ArithmeticError("fixed-power DP replay disagrees")
            updated = polish(assigned)
            if updated["assignment"] == current["assignment"] and not problem.improves(updated, current):
                break
            current = updated

    reason = "starts_exhausted"
    best_upper = math.inf
    try:
        counts["starts_started"] += 1
        diagnostics.append(dict(method="COMMON_START", start_id=0))
        alternate(best)
        counts["starts_completed"] += 1
        initial_price = float(original.shared.producer.propose_lambda(best["schedule"], problem.model.data,
                              problem.k, problem.low, problem.high, problem.budget))
        idx, p, t, rate, cost, error = _grid(problem)
        u, v, s = idx
        edge = np.arange(len(u))
        lookup = np.zeros((problem.s, problem.k, problem.k), int)
        lookup[s, u, v] = edge
        min_price, max_price = 0., None
        price = initial_price
        seen = set()
        for _ in range(PRICE_STEPS):
            guard(deadline)
            net = (rate-price*cost).reshape(len(edge), -1)
            choice = net.argmax(axis=1)
            selected = net[edge, choice]
            weights = np.zeros(lookup.shape)
            weights[s, u, v] = selected
            a, value = _best_assignment(weights, deadline)
            counts["price_dp_completed"] += 1
            counts["dp_completed"] += 1
            selected_edge = lookup[np.arange(problem.s), *np.asarray(a).T]
            i, j = np.unravel_index(choice[selected_edge], rate.shape[1:])
            raw = np.empty(problem.k)
            raw[u[selected_edge]] = p[selected_edge, i]
            raw[v[selected_edge]] = t[selected_edge, j]
            used = float(np.sum(raw))
            # Max error per resource covers all schedules. This is float arithmetic.
            upper = value+price*float(problem.budget)+sum(float(error[s == z].max()) for z in range(problem.s))
            best_upper = min(best_upper, upper)
            diagnostics.append(dict(method="GRID_PRICE", price=price, unprojected_power=used,
                                    numerical_upper_nats=upper))
            feasible = project(raw, problem.low, problem.high, problem.budget)
            # Different endpoint power patterns on one schedule can reach distinct local optima.
            marker = (a, tuple((raw <= float(problem.low)+1e-12).tolist()),
                      tuple((raw >= float(problem.high)-1e-12).tolist()))
            if marker not in seen:
                seen.add(marker)
                counts["price_schedules"] += 1
                current = polish(retain(a, feasible))
                if current["assignment"] == best["assignment"]:
                    alternate(current)
            if used > float(problem.budget):
                min_price = price
                price = (2*price if price else 1.) if max_price is None else (price+max_price)/2
            else:
                max_price = price
                price = (min_price+price)/2
            if max_price is not None and max_price-min_price <= 1e-7*max(1., max_price):
                break
        for start_id, (a, start) in enumerate(starts[1:], 1):
            guard(deadline)
            counts["starts_started"] += 1
            diagnostics.append(dict(method="COMMON_START", start_id=start_id))
            alternate(retain(a, start))
            counts["starts_completed"] += 1
    except DeadlineReached:
        reason = "deadline"
    elapsed = time.monotonic()-begun
    audit_begun = time.monotonic()
    _, powers = problem.model.decode(best["schedule"])
    audit = problem.matrix_scalar_check(best)
    if sum(powers) > problem.budget or history[-1]["seconds"] > cap:
        raise AssertionError("infeasible or late incumbent")
    return dict(arm="Price-DP-SQP", rate_nats=best["value"], se_bits=best["value"]/unit,
                lower_nats=str(best["lo"]), upper_nats=str(best["hi"]), schedule=best["schedule"],
                total_power=str(sum(powers)), elapsed_seconds=elapsed, cap_seconds=cap, block_seconds=block,
                overrun_seconds=max(0., elapsed-cap), audit_seconds=time.monotonic()-audit_begun,
                audit=audit, status=reason, counts=counts, history=history, diagnostics=diagnostics,
                numerical_upper_nats=best_upper if math.isfinite(best_upper) else None)


def self_check():
    """Compare fixed-power and arbitrary signed-weight DPs to exhaustive schedules."""
    rng = np.random.default_rng(1279)
    k = 4
    perms = {tuple(tuple(sorted(perm[2*z:2*z+2])) for z in range(2))
             for perm in itertools.permutations(range(k))}
    for tied in (False, True):
        w = np.zeros((2, k, k)) if tied else rng.normal(size=(2, k, k))
        a, value = _best_assignment(w, math.inf)
        score = lambda pairs: sum(w[z, *pair] for z, pair in enumerate(pairs))
        assert score(a) == value == max(map(score, perms))
    powers = [.031, .112, .17, .2]
    data = {(u,v,s): tuple(rng.uniform(size=3)) for u,v in itertools.combinations(range(k),2) for s in range(2)}
    assert dp_assignment(k, data, powers, math.inf) == original.shared.dp_assignment(k, data, powers, math.inf)
    # Check interpolation formula including zero gain and dense off-grid powers.
    from types import SimpleNamespace
    problem = SimpleNamespace(low=.001, high=.2, lookup={(0,1,0):(0.,60.,1.), (0,2,0):(1e4,1e3,.95)})
    _, _, _, rate, cost, error = _grid(problem)
    for row, (g,h,r) in enumerate(problem.lookup.values()):
        x = rng.uniform(.001,.2,10_000)
        y = rng.uniform(.001,.2,10_000)
        q = 2*np.log(1+g*x+h*y+(1-r)*g*x*h*y)-np.log1p(g*x)-np.log1p(h*y)
        for price in (0., 5., 30.):
            assert np.max(q-price*(x+y)) <= np.max(rate[row]-price*cost[row])+error[row]+1e-12
    try:
        _best_assignment(w, time.monotonic()-1.)
    except DeadlineReached:
        return
    raise AssertionError("expired deadline accepted")

