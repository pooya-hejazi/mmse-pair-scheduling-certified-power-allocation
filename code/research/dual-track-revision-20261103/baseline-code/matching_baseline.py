"""Full-service matching/WMMSE incumbent search; no global certificate.

Only NumPy/SciPy and standard-library dependencies. Import has no experiments or
I/O. All setup and callback work inside solve is charged to its wall clock.
See MATCHING_EQUATION_CODE_MAP.md for the frozen algorithm and fidelity limits.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import time
from fractions import Fraction
from typing import Callable

import numpy as np
from scipy.optimize import linear_sum_assignment

METHOD = "matching_wmmse_full_service_v1"
MAX_OUTER = 128
RANDOM_STARTS = 8
EXCHANGE_SWEEPS = 2
EXCHANGE_POWER_STEPS = 16
ABS_STOP = 1e-10
REL_STOP = 1e-9
RATE_CHECK_ATOL = 2e-8
RATE_CHECK_RTOL = 2e-8
COEFFICIENT_RTOL = 2e-9


class NumericalFailure(RuntimeError):
    pass


class ProgressFailure(RuntimeError):
    pass


def _fraction(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a rational coefficient")
    return Fraction(str(value))


def _rational_powers(values, pmin, pmax, budget):
    """Clip and repair in rational arithmetic, including binary64 roundoff.

    Final strings, rather than an approximate float sum, define feasibility.
    """
    out = [max(pmin, min(pmax, Fraction.from_float(float(v)))) for v in values]
    excess = sum(out, Fraction(0)) - budget
    if excess > 0:
        # Largest slack first, deterministic on ties; never reduce below pmin.
        for k in sorted(range(len(out)), key=lambda i: (-(out[i] - pmin), i)):
            delta = min(excess, out[k] - pmin)
            out[k] -= delta
            excess -= delta
            if excess == 0:
                break
    if sum(out, Fraction(0)) > budget or any(p < pmin or p > pmax for p in out):
        raise NumericalFailure("Rational power repair failed")
    return out


def _mmse(h, assignment, powers):
    """Slot receivers and inverse MSE weights, using positive residual MSE."""
    k_count, m, s_count = h.shape
    u = np.empty((k_count, m), complex)
    weights = np.empty(k_count, float)
    for s in range(s_count):
        users = assignment[2*s:2*s+2]
        hs = h[users, :, s].T  # M x 2
        vp = np.sqrt(powers[users])
        covariance = np.eye(m, dtype=complex) + (hs * powers[users]) @ hs.conj().T
        us = np.linalg.solve(covariance, hs * vp).T
        cross = us.conj() @ hs
        # e_i = |v_i u_i^H h_i - 1|² + p_j|u_i^H h_j|² + ||u_i||²
        mse = np.sum(np.abs(us)**2, axis=1)
        mse += np.abs(vp * np.diag(cross) - 1)**2
        mse += powers[users[::-1]] * np.abs(cross[[0, 1], [1, 0]])**2
        if not np.all(np.isfinite(mse)) or np.any(mse <= 0):
            raise NumericalFailure("Nonpositive or nonfinite MMSE")
        u[2*s:2*s+2] = us
        weights[2*s:2*s+2] = 1 / mse
    if not np.all(np.isfinite(u)) or not np.all(np.isfinite(weights)):
        raise NumericalFailure("Nonfinite receiver/weight")
    return u, weights


def _assignment_scores(h, powers, u, weights):
    """D[k,a]; row=user, column=slot. Every entry, including negative, kept."""
    k_count, _, s_count = h.shape
    scores = np.empty((k_count, k_count))
    for s in range(s_count):
        slots = slice(2*s, 2*s+2)
        cross = h[:, :, s] @ u[slots].conj().T
        penalty = np.sum(np.abs(cross)**2 * weights[slots], axis=1)
        scores[:, slots] = (2*np.sqrt(powers)[:, None] * cross.real * weights[slots]
                            - powers[:, None] * penalty[:, None])
    if not np.all(np.isfinite(scores)):
        raise NumericalFailure("Nonfinite matching score")
    return scores


def _perfect_assignment(scores):
    rows, cols = linear_sum_assignment(scores, maximize=True)
    assignment = np.empty(len(rows), dtype=int)
    assignment[cols] = rows
    return assignment


def _power_coefficients(h, assignment, u, weights):
    a = np.zeros(len(assignment))
    b = np.zeros(len(assignment))
    for s in range(h.shape[2]):
        slots = slice(2*s, 2*s+2)
        users = assignment[slots]
        cross = h[users, :, s] @ u[slots].conj().T
        a[users] = np.sum(np.abs(cross)**2 * weights[slots], axis=1)
        b[users] = weights[slots] * np.diag(cross).real
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)) or np.any(a < 0):
        raise NumericalFailure("Invalid amplitude coefficients")
    # Recomputed MMSE gives B >= 0. Significant negative values are an error.
    if np.any(b < -1e-12*np.maximum(1, np.abs(b))):
        raise NumericalFailure("Negative useful-link coefficient after MMSE")
    return a, np.maximum(b, 0)


def _amplitude_update(a, b, pmin, pmax, budget):
    """Solve the convex frozen-WMMSE amplitude block by one shared multiplier."""
    k_count = len(a)
    if k_count*pmin == budget or pmin == pmax:
        return np.full(k_count, float(pmin)), 0
    lower, upper, cap = math.sqrt(float(pmin)), math.sqrt(float(pmax)), float(budget)

    def at(lam):
        denominator = a + lam
        v = np.full(k_count, lower)
        np.divide(b, denominator, out=v, where=denominator > 0)
        return np.clip(v, lower, upper)**2

    candidate = at(0.0)
    iterations = 0
    if math.fsum(candidate) > cap:
        lo, hi = 0.0, max(1.0, float(np.max(b)) / max(lower, np.finfo(float).tiny))
        while math.fsum(at(hi)) > cap:
            hi *= 2
            iterations += 1
            if not math.isfinite(hi) or iterations > 1024:
                raise NumericalFailure("Unable to bracket shared multiplier")
        # Return feasible high side, never the potentially infeasible midpoint.
        for _ in range(80):
            mid = lo + (hi-lo)/2
            if mid == lo or mid == hi:
                break
            if math.fsum(at(mid)) > cap:
                lo = mid
            else:
                hi = mid
            iterations += 1
        candidate = at(hi)
    rational = _rational_powers(candidate, pmin, pmax, budget)
    return np.array([float(v) for v in rational]), iterations


def _matrix_rate(h, assignment, powers):
    """Independent receiver-model rate via interference-only covariance solves."""
    m, s_count = h.shape[1:]
    terms = []
    for s in range(s_count):
        users = assignment[2*s:2*s+2]
        for i, j in (users, users[::-1]):
            hi, hj = h[i, :, s], h[j, :, s]
            covariance = np.eye(m, dtype=complex) + powers[j]*np.outer(hj, hj.conj())
            z = np.vdot(hi, np.linalg.solve(covariance, hi))
            if abs(z.imag) > 1e-8*max(1, abs(z.real)) or z.real < -1e-10:
                raise NumericalFailure("Invalid quadratic form in matrix rate")
            sinr = powers[i]*max(0.0, float(z.real))
            terms.append(math.log1p(sinr))
    result = math.fsum(terms)
    if not math.isfinite(result):
        raise NumericalFailure("Nonfinite matrix rate")
    return result


class _Problem:
    def __init__(self, case):
        self.k, self.s, self.m = int(case["K"]), int(case["S"]), int(case["M"])
        if self.k <= 0 or self.k != 2*self.s or self.m <= 0:
            raise ValueError("Require positive K=2S and M")
        self.pmin, self.pmax, self.budget = map(_fraction,
                                               (case["pmin"], case["pmax"], case["budget"]))
        if not (0 < self.pmin <= self.pmax and self.k*self.pmin <= self.budget):
            raise ValueError("Infeasible positive box/shared budget")
        # A binary64 optimization algorithm needs representable positive bounds.
        if (not all(math.isfinite(float(q)) for q in (self.pmin, self.pmax, self.budget))
                or float(self.pmin) <= 0):
            raise ValueError("Power domain outside binary64 range")
        self.pairs = {}
        for row in case["pairs"]:
            i, j = map(int, row["users"])
            s = int(row["resource"])
            g1, g2, r = map(_fraction, (row["gain1"], row["gain2"], row["r"]))
            if not (0 <= i < self.k and 0 <= j < self.k and i != j and 0 <= s < self.s):
                raise ValueError("Invalid pair indices")
            if not (g1 >= 0 and g2 >= 0 and 0 <= r <= 1):
                raise ValueError("Invalid scalar channel coefficients")
            if i > j:
                i, j, g1, g2 = j, i, g2, g1
            key = (i, j, s)
            if key in self.pairs:
                raise ValueError("Duplicate pair/resource coefficient row")
            coefficients = (float(g1), float(g2), float(r))
            if not all(math.isfinite(v) for v in coefficients):
                raise ValueError("Channel coefficient outside binary64 range")
            self.pairs[key] = coefficients
        if len(self.pairs) != self.k*(self.k-1)//2*self.s:
            raise ValueError("Require every pair/resource coefficient row")
        real, imag = np.asarray(case["channels_re"], float), np.asarray(case["channels_im"], float)
        if real.shape != (self.k, self.m, self.s) or imag.shape != real.shape:
            raise ValueError("Both channel components require shape[K,M,S]")
        self.h = real + 1j*imag
        if self.h.shape != (self.k, self.m, self.s) or not np.all(np.isfinite(self.h)):
            raise ValueError("Require finite complex channels with shape[K,M,S]")
        self.digest = hashlib.sha256(json.dumps(case, sort_keys=True, separators=(",", ":"),
                                               allow_nan=False).encode()).hexdigest()

    def validate_channels(self):
        gains = np.sum(np.abs(self.h)**2, axis=1)
        for (i, j, s), (g1, g2, r) in self.pairs.items():
            actual1, actual2 = gains[i, s], gains[j, s]
            actual_r = (abs(np.vdot(self.h[i, :, s], self.h[j, :, s]))**2 / actual1 / actual2
                        if actual1 > 0 and actual2 > 0 else 0.0)
            if not (math.isclose(g1, actual1, rel_tol=COEFFICIENT_RTOL, abs_tol=1e-14)
                    and math.isclose(g2, actual2, rel_tol=COEFFICIENT_RTOL, abs_tol=1e-14)
                    and math.isclose(r, actual_r, rel_tol=COEFFICIENT_RTOL, abs_tol=2e-12)):
                raise ValueError(f"Stored scalar coefficients disagree with channels: {(i,j,s)}")

    def scalar_rate(self, assignment, powers):
        terms = []
        for s in range(self.s):
            i, j = sorted(map(int, assignment[2*s:2*s+2]))
            g1, g2, r = self.pairs[i, j, s]
            x, y = g1*powers[i], g2*powers[j]
            # Stable positive SINRs avoid cancellation of 2log d-log(1+x)-log(1+y).
            gamma1 = x*((1-r) + r/(1+y))
            gamma2 = y*((1-r) + r/(1+x))
            terms.extend((math.log1p(gamma1), math.log1p(gamma2)))
        rate = math.fsum(terms)
        if not math.isfinite(rate):
            raise NumericalFailure("Nonfinite scalar rate")
        return rate

    def checked_rate(self, assignment, powers, metrics):
        scalar = self.scalar_rate(assignment, powers)
        matrix = _matrix_rate(self.h, assignment, powers)
        metrics["rate_checks"] += 1
        metrics["rate_linear_solves"] += 2*self.s
        delta = abs(scalar-matrix)
        metrics["max_matrix_scalar_discrepancy"] = max(metrics["max_matrix_scalar_discrepancy"], delta)
        if delta > RATE_CHECK_ATOL + RATE_CHECK_RTOL*max(abs(scalar), abs(matrix)):
            raise NumericalFailure(f"Matrix/scalar objective discrepancy: {scalar} versus {matrix}")
        return scalar

    def schedule(self, assignment, powers):
        rational = _rational_powers(powers, self.pmin, self.pmax, self.budget)
        schedule = []
        for s in range(self.s):
            users = sorted(map(int, assignment[2*s:2*s+2]))
            schedule.append({"users": users, "resource": s,
                             "powers": [str(rational[i]) for i in users]})
        return schedule, np.array([float(q) for q in rational]), rational


def solve(case, seconds=20.0, seed=1101, progress: Callable | None = None):
    """Return feasible incumbent and complete status/metrics, never an upper bound.

    progress(payload) receives JSON-safe incumbent improvements. Callback exceptions
    end the method with progress_error, preserving the best in-memory incumbent.
    The deadline is cooperative, checked between bounded numerical operations;
    callers retain an external watchdog. Missing/invalid channels are input errors.
    """
    start_time = time.perf_counter()
    metrics = {"elapsed_seconds": 0.0, "starts_started": 0, "starts_completed": 0,
               "outer_iterations": 0, "matching_calls": 0, "mmse_calls": 0,
               "mmse_linear_solves": 0, "rate_linear_solves": 0,
               "power_steps": 0, "bisection_iterations": 0, "rate_checks": 0,
               "max_matrix_scalar_discrepancy": 0.0, "rejected_decreases": 0,
               "roundoff_decreases_rejected": 0, "max_rejected_decrease": 0.0,
               "exchange_candidates": 0, "exchange_accepted": 0,
               "exchange_sweeps_completed": 0, "progress_calls": 0,
               "start_records": [], "incumbent_history": [],
               "settings": {"max_outer": MAX_OUTER, "random_starts": RANDOM_STARTS,
                            "exchange_sweeps": EXCHANGE_SWEEPS,
                            "exchange_power_steps": EXCHANGE_POWER_STEPS,
                            "abs_stop": ABS_STOP, "rel_stop": REL_STOP}}
    result = {"method": METHOD, "status": "invalid_input", "schedule": [],
              "rate_nats": None, "rate_bits": None, "global_upper_bound": None,
              "metrics": metrics, "errors": []}
    best_assignment = best_powers = None
    best_rate = -math.inf
    active_record = None
    completed = False
    try:
        seconds = float(seconds)
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("seconds must be finite and nonnegative")
        seed = int(seed)
        if seed < 0:
            raise ValueError("seed must be nonnegative")
        deadline = start_time + seconds
        problem = _Problem(case)
        result["case_sha256"] = problem.digest
        metrics["seed"] = seed
        metrics["start_seed_derivation"] = "numpy.default_rng(SeedSequence([seed,index])), index=0..7"

        def expired():
            return time.perf_counter() >= deadline

        def record_best(assignment, powers, rate, stage, check=True):
            nonlocal best_assignment, best_powers, best_rate
            if rate <= best_rate:
                return
            schedule, serialized_powers, rationals = problem.schedule(assignment, powers)
            actual = (problem.checked_rate(assignment, serialized_powers, metrics) if check
                      else problem.scalar_rate(assignment, serialized_powers))
            if actual <= best_rate:
                return
            best_assignment, best_powers, best_rate = assignment.copy(), serialized_powers.copy(), actual
            result.update(schedule=schedule, rate_nats=actual, rate_bits=actual/math.log(2))
            metrics["power_budget_slack_rational"] = str(problem.budget-sum(rationals, Fraction(0)))
            metrics["incumbent_history"].append({"stage": stage, "rate_nats": actual,
                                                "elapsed_seconds": time.perf_counter()-start_time})
            if progress is not None and not expired():
                payload = {"method": METHOD, "status": "running", "schedule": schedule,
                           "rate_nats": actual, "rate_bits": actual/math.log(2),
                           "elapsed_seconds": time.perf_counter()-start_time,
                           "sequence": metrics["progress_calls"], "stage": stage,
                           "case_sha256": problem.digest}
                metrics["progress_calls"] += 1
                try:
                    # A consumer may retain/mutate its snapshot; isolate our incumbent.
                    progress(json.loads(json.dumps(payload, allow_nan=False)))
                except Exception as exc:
                    raise ProgressFailure(f"{type(exc).__name__}: {exc}") from exc

        assignment = np.arange(problem.k, dtype=int)
        powers = np.full(problem.k, float(problem.pmin))
        # Construct a rational-feasible fallback before optional consistency/search work.
        record_best(assignment, powers, problem.scalar_rate(assignment, powers), "minimum_power_fallback", False)
        if expired():
            result["status"] = "time_limit"
            metrics["channel_consistency_checked"] = False
            return result
        problem.validate_channels()
        metrics["channel_consistency_checked"] = True
        problem.checked_rate(assignment, powers, metrics)

        def receivers(assignment, powers):
            metrics["mmse_calls"] += 1
            metrics["mmse_linear_solves"] += problem.s
            return _mmse(problem.h, assignment, powers)

        def accept_nondecreasing(old_rate, new_rate):
            if new_rate >= old_rate:
                return True
            loss = old_rate-new_rate
            metrics["max_rejected_decrease"] = max(metrics["max_rejected_decrease"], loss)
            if loss <= ABS_STOP+REL_STOP*max(1, abs(old_rate)):
                metrics["roundoff_decreases_rejected"] += 1
            else:
                metrics["rejected_decreases"] += 1
            return False  # Keep the best actual measured value, even for roundoff.

        def power_step(assignment, powers, rate):
            u, weights = receivers(assignment, powers)
            a, b = _power_coefficients(problem.h, assignment, u, weights)
            candidate, count = _amplitude_update(a, b, problem.pmin, problem.pmax, problem.budget)
            metrics["power_steps"] += 1
            metrics["bisection_iterations"] += count
            candidate_rate = problem.checked_rate(assignment, candidate, metrics)
            if accept_nondecreasing(rate, candidate_rate):
                return candidate, candidate_rate
            return powers, rate

        for index in range(RANDOM_STARTS+1):
            if expired():
                break
            if index == 0:
                assignment = np.arange(problem.k, dtype=int)
                uniform = min(problem.pmax, problem.budget/problem.k)
                powers = np.full(problem.k, float(uniform))
            else:
                rng = np.random.default_rng(np.random.SeedSequence([seed, index-1]))
                assignment = rng.permutation(problem.k)
                residual = (float(problem.pmax)-float(problem.pmin))*rng.random(problem.k)
                available = max(0.0, float(problem.budget-problem.k*problem.pmin))
                if math.fsum(residual) > available and math.fsum(residual) > 0:
                    residual *= available/math.fsum(residual)
                powers = float(problem.pmin)+residual
            powers = np.array([float(q) for q in _rational_powers(
                powers, problem.pmin, problem.pmax, problem.budget)])
            rate = problem.checked_rate(assignment, powers, metrics)
            active_record = {"index": index, "kind": "uniform" if index == 0 else "seeded",
                             "initial_rate_nats": rate, "final_rate_nats": rate,
                             "iterations": 0, "status": "running", "trace": [rate]}
            metrics["start_records"].append(active_record)
            metrics["starts_started"] += 1
            record_best(assignment, powers, rate, f"start_{index}")
            for iteration in range(MAX_OUTER):
                if expired():
                    active_record["status"] = "time_limit"
                    break
                previous = rate
                u, weights = receivers(assignment, powers)
                scores = _assignment_scores(problem.h, powers, u, weights)
                proposal = _perfect_assignment(scores)
                metrics["matching_calls"] += 1
                candidate_rate = problem.checked_rate(proposal, powers, metrics)
                if accept_nondecreasing(rate, candidate_rate):
                    assignment, rate = proposal, candidate_rate
                record_best(assignment, powers, rate, f"matching_{index}_{iteration}")
                if expired():
                    active_record["status"] = "time_limit"
                    break
                powers, rate = power_step(assignment, powers, rate)
                metrics["outer_iterations"] += 1
                active_record["iterations"] += 1
                active_record["final_rate_nats"] = rate
                active_record["trace"].append(rate)
                record_best(assignment, powers, rate, f"power_{index}_{iteration}")
                if rate-previous <= ABS_STOP+REL_STOP*max(1, abs(previous)):
                    active_record["status"] = "objective_tolerance"
                    break
            else:
                active_record["status"] = "iteration_limit"
            active_record["final_rate_nats"] = rate
            if active_record["status"] != "time_limit":
                metrics["starts_completed"] += 1
            active_record = None

        # Bounded exact-four-user exchanges: 6 allocations to two labeled resources.
        # Each candidate's powers are refined over ALL users under the shared budget.
        if not expired() and best_assignment is not None:
            assignment, powers, rate = best_assignment.copy(), best_powers.copy(), best_rate
            for sweep in range(EXCHANGE_SWEEPS):
                sweep_changed = False
                sweep_complete = True
                for s1, s2 in itertools.combinations(range(problem.s), 2):
                    if expired():
                        sweep_complete = False
                        break
                    four = sorted(map(int, np.r_[assignment[2*s1:2*s1+2], assignment[2*s2:2*s2+2]]))
                    for first in itertools.combinations(four, 2):
                        if expired():
                            sweep_complete = False
                            break
                        second = [i for i in four if i not in first]
                        candidate = assignment.copy()
                        candidate[2*s1:2*s1+2], candidate[2*s2:2*s2+2] = first, second
                        if (set(candidate[2*s1:2*s1+2]) == set(assignment[2*s1:2*s1+2])
                                and set(candidate[2*s2:2*s2+2]) == set(assignment[2*s2:2*s2+2])):
                            continue
                        candidate_powers = powers.copy()
                        candidate_rate = problem.checked_rate(candidate, candidate_powers, metrics)
                        metrics["exchange_candidates"] += 1
                        for _ in range(EXCHANGE_POWER_STEPS):
                            if expired():
                                break
                            old = candidate_rate
                            candidate_powers, candidate_rate = power_step(candidate, candidate_powers, candidate_rate)
                            if candidate_rate-old <= ABS_STOP+REL_STOP*max(1, abs(old)):
                                break
                        if candidate_rate > rate+ABS_STOP+REL_STOP*max(1, abs(rate)):
                            assignment, powers, rate = candidate, candidate_powers, candidate_rate
                            metrics["exchange_accepted"] += 1
                            sweep_changed = True
                            record_best(assignment, powers, rate, f"exchange_{sweep}_{s1}_{s2}")
                    if not sweep_complete:
                        break
                if sweep_complete:
                    metrics["exchange_sweeps_completed"] += 1
                if not sweep_complete or not sweep_changed:
                    break
            completed = not expired()
        result["status"] = "completed" if completed else "time_limit"
    except ProgressFailure as exc:
        result["status"] = "progress_error"
        result["errors"].append({"type": type(exc).__name__, "message": str(exc)})
    except (NumericalFailure, np.linalg.LinAlgError, FloatingPointError) as exc:
        result["status"] = "numerical_error"
        result["errors"].append({"type": type(exc).__name__, "message": str(exc)})
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        result["status"] = "invalid_input"
        result["errors"].append({"type": type(exc).__name__, "message": str(exc)})
    finally:
        if active_record is not None and active_record["status"] == "running":
            active_record["status"] = result["status"]
        metrics["elapsed_seconds"] = time.perf_counter()-start_time
        metrics["deadline_overrun_seconds"] = max(0.0, metrics["elapsed_seconds"]-float(seconds)) if isinstance(seconds, (float, int)) else None
    return result
