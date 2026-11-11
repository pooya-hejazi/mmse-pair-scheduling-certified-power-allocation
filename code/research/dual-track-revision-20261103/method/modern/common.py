"""Shared adapter mechanics; no experiments or I/O on import."""
import math
import time
import numpy as np


class DeadlineReached(Exception):
    pass


def guard(deadline):
    if time.monotonic() >= deadline:
        raise DeadlineReached()


def checked(problem, assignment, powers, deadline):
    guard(deadline)
    result = problem.checked_candidate(assignment, powers)
    guard(deadline)
    if not math.isfinite(result['value']):
        raise ValueError('nonfinite checked objective')
    return result


def improves(candidate, old):
    tol = 1e-10 + 1e-9 * max(1.0, abs(old['value']))
    return candidate['lo'] > old['hi'] and candidate['value'] > old['value'] + tol


def project(raw, low, high, budget):
    """Euclidean projection onto box intersected with sum <= budget."""
    x = np.asarray(raw, dtype=float)
    if x.ndim != 1 or not np.all(np.isfinite(x)):
        raise ValueError('nonfinite or nonvector powers')
    low, high, budget = float(low), float(high), float(budget)
    if not (0 < low <= high and len(x)*low <= budget):
        raise ValueError('invalid positive box/shared budget')
    y = np.clip(x, low, high)
    if math.fsum(y) <= budget:
        return y
    left, right = 0.0, max(0.0, float(np.max(x-low)))
    for _ in range(100):
        mid = (left+right)/2
        if mid == left or mid == right:
            break
        if math.fsum(np.clip(x-mid, low, high)) > budget:
            left = mid
        else:
            right = mid
    return np.clip(x-right, low, high)


def projected_exact(problem, raw):
    p = project(raw, problem.low, problem.high, problem.budget)
    return np.array([float(x) for x in problem.repair(p)])


def publish_candidate(publish, assignment, candidate, diagnostics, deadline):
    guard(deadline)
    # False indicates only global retention; callers keep their local improvement.
    publish(assignment, candidate['powers'], dict(diagnostics))
    guard(deadline)


def diagnostics(method):
    return dict(method=method, stop_reason='running', evaluations=0,
                iterations=0, cap_count=0, error_count=0, accepted=0)
