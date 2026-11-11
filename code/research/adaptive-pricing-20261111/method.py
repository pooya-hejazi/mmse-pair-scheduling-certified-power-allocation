"""Elasticity-gated truncation of the frozen Price–DP–SQP search."""
import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[variable] = "1"

import importlib.util
import math
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / "priced-assignment-20261111"
spec = importlib.util.spec_from_file_location("published_study_runner", PREVIOUS / "run_study.py")
published = importlib.util.module_from_spec(spec)
spec.loader.exec_module(published)
price = published.engine()
prior = published.prior
producer = prior.shared.producer
guard, DeadlineReached = prior.guard, prior.DeadlineReached
ADAPT, ONE, SHORT, DP, FULL = ARMS = (
    "Adaptive-DP-SQP", "Uniform-start-DP-SQP", "Always-short-price", "DP-SQP", "Price-DP-SQP")
PREFIX = "DP-SQP-time-prefix"
CAP, BLOCK, CUT, TRIALS = 10., 5., .90, 6
clock = time.perf_counter


class Meter:
    """Nonoverlapping stage clocks; retain the screen's first DP for the solver."""
    def __init__(self):
        names = ("screen", "fixed_dp", "price_dp", "grid_setup", "initial_price", "sqp")
        self.seconds = dict.fromkeys(names, 0.)
        self.calls = dict.fromkeys(names, 0)
        self.in_fixed_dp = False
        self.pending_dp = None
        self.cache_hits = 0
        self.dp_original = price.dp_assignment
        self.subset_original = price._best_assignment
        self.record_original = prior.record

    def timed(self, stage, fn):
        def call(*args, **kwargs):
            start = clock()
            self.calls[stage] += 1
            try:
                return fn(*args, **kwargs)
            finally:
                self.seconds[stage] += clock() - start
        return call

    def fixed(self, k, data, powers, deadline):
        if self.pending_dp is not None:
            saved_powers, answer = self.pending_dp
            if tuple(powers) != saved_powers:
                raise ValueError("Uniform assignment cache used at different powers")
            guard(deadline)
            self.pending_dp = None
            self.cache_hits += 1
            return answer
        self.in_fixed_dp = True
        try:
            return self.timed("fixed_dp", self.dp_original)(k, data, powers, deadline)
        finally:
            self.in_fixed_dp = False

    def subset(self, weights, deadline):
        if self.in_fixed_dp:
            return self.subset_original(weights, deadline)
        return self.timed("price_dp", self.subset_original)(weights, deadline)

    def record(self, candidate, seconds, kind):
        item = self.record_original(candidate, seconds, kind)
        item["dispatch_seconds"] = clock() - self.begun
        return item

    def install(self, stack):
        stack.enter_context(patch.object(price, "dp_assignment", self.fixed))
        stack.enter_context(patch.object(prior.shared, "dp_assignment", self.fixed))
        stack.enter_context(patch.object(price, "_best_assignment", self.subset))
        stack.enter_context(patch.object(price, "_grid", self.timed("grid_setup", price._grid)))
        stack.enter_context(patch.object(producer, "propose_lambda", self.timed("initial_price", producer.propose_lambda)))
        stack.enter_context(patch.object(producer, "refine", self.timed("sqp", producer.refine)))
        stack.enter_context(patch.object(prior, "record", self.record))


def elasticities(problem, assignment, powers):
    q = problem.budget / problem.k
    if any(p != q for p in powers):
        raise ValueError("Screen requires feasible common equal powers")
    _, marginal = problem.value_gradient(assignment, powers)
    e = float(q) * marginal
    if not np.all(np.isfinite(e)):
        raise ArithmeticError("Nonfinite marginal")
    return list(map(float, e))


def first_trajectory(problem, start, deadline, block, meter):
    """The first alternate(best) trajectory of the published priced method."""
    prior.shared.certificates.clear_caches()
    best = problem.checked_candidate(*start)
    problem.matrix_scalar_check(best)
    current = best
    history = [prior.record(best, clock() - meter.begun, "initial")]
    diagnostics = [dict(method="COMMON_START", start_id=0)]
    counts = dict(starts_started=1, starts_completed=0, dp_completed=0, power_calls=0,
                  accepted=0, price_dp_completed=0, price_schedules=0)

    def retain(assignment, powers):
        nonlocal best
        guard(deadline)
        candidate = problem.checked_candidate(assignment, powers)
        problem.matrix_scalar_check(candidate)
        guard(deadline)
        if problem.improves(candidate, best):
            item = prior.record(candidate, clock() - meter.begun, "improvement")
            guard(deadline)
            best = candidate
            history.append(item)
            counts["accepted"] += 1
        return candidate

    reason = "starts_exhausted"
    try:
        for _ in range(8):
            assignment, value = meter.fixed(problem.k, problem.lookup, current["powers"], deadline)
            counts["dp_completed"] += 1
            assigned = retain(assignment, current["powers"])
            if abs(value - assigned["value"]) > 1e-7:
                raise ArithmeticError("Uniform trajectory fixed-power replay disagrees")
            stop = clock() + max(0., min(block, deadline - time.monotonic()))
            counts["power_calls"] += 1
            powers, diag = producer.refine(assignment, assigned["powers"], problem.model.data,
                                           problem.low, problem.high, problem.budget, stop)
            diagnostics.append(dict(method="LOCAL_SQP", **diag))
            candidate = retain(assignment, powers)
            updated = candidate if problem.improves(candidate, assigned) else assigned
            if updated["assignment"] == current["assignment"] and not problem.improves(updated, current):
                break
            current = updated
        counts["starts_completed"] = 1
    except DeadlineReached:
        reason = "deadline"
    elapsed = clock() - meter.begun
    begun_audit = clock()
    _, powers = problem.model.decode(best["schedule"])
    audit = problem.matrix_scalar_check(best)
    return dict(rate_nats=best["value"], se_bits=best["value"]/(problem.s*math.log(2)),
                lower_nats=str(best["lo"]), upper_nats=str(best["hi"]), schedule=best["schedule"],
                total_power=str(sum(powers)), elapsed_seconds=elapsed, audit_seconds=clock()-begun_audit,
                audit=audit, status=reason, counts=counts, history=history, diagnostics=diagnostics)


def solve(problem, starts, search_seed, arm, cap=CAP, block=BLOCK):
    if arm not in ARMS or len(starts) != 8:
        raise ValueError("Unsupported arm or different common start count")
    meter = Meter()
    with ExitStack() as stack:
        meter.install(stack)
        meter.begun = clock()
        deadline = time.monotonic() + cap
        screen = None
        if arm == ADAPT:
            powers = starts[0][1]
            answer = meter.fixed(problem.k, problem.lookup, powers, deadline)
            e = meter.timed("screen", elasticities)(problem, answer[0], powers)
            meter.pending_dp = (tuple(powers), answer)
            screen = dict(elasticities=e, minimum=min(e), passed=min(e) >= CUT,
                          uniform_assignment=answer[0], equal_power=str(powers[0]))
        if arm == ONE or (arm == ADAPT and screen["passed"]):
            result = first_trajectory(problem, starts[0], deadline, block, meter)
        elif arm == DP:
            result = prior.solve(problem, starts, DP, search_seed, deadline - time.monotonic(), block)
        else:
            truncated = arm != FULL
            if truncated:
                stack.enter_context(patch.object(price, "PRICE_STEPS", TRIALS))
            result = price.solve(problem, starts[:2] if truncated else starts, deadline - time.monotonic(), block)
        elapsed = clock() - meter.begun
    if meter.pending_dp is not None or meter.cache_hits != int(arm == ADAPT):
        raise ValueError("Unconsumed or unexpected uniform-DP cache")
    remainder = elapsed - sum(meter.seconds.values())
    if remainder < 0 or not require_progress(result, elapsed, cap):
        raise ValueError("Invalid incumbent or component clock")
    result.update(arm=arm, solver_elapsed_seconds=result["elapsed_seconds"], elapsed_seconds=elapsed,
                  cap_seconds=cap, block_seconds=block, overrun_seconds=max(0., elapsed-cap),
                  stage_seconds={**meter.seconds, "other": remainder}, stage_calls=meter.calls,
                  uniform_dp_cache_hits=meter.cache_hits, screen=screen)
    return result


def require_progress(row, elapsed, cap):
    history = row["history"]
    return (history and history[0]["kind"] == "initial" and history[-1]["schedule"] == row["schedule"]
            and row["counts"]["accepted"] == len(history)-1 and 0 < elapsed < cap+.5)


def prefix(case_row):
    adaptive = case_row["arms"][ADAPT]
    dp = case_row["arms"][DP]
    available = [event for event in dp["history"] if event["dispatch_seconds"] <= adaptive["elapsed_seconds"]]
    event = available[-1] if available else dp["history"][0]
    return event, bool(available)
