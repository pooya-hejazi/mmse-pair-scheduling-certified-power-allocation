"""Fu2026 Eq.(25c) power SCA, adapted with exact uplink denominator.

Printed Eq.(25e)'s extra old denominator is deliberately NOT copied. The
common-model exact N restores tightness. No DE/LP-RZF or global claim is made.
"""
import math
import time
import numpy as np
from scipy.optimize import minimize
try:
    from .common import (guard, checked, improves, projected_exact,
                         publish_candidate, diagnostics, DeadlineReached)
except ImportError:
    from common import (guard, checked, improves, projected_exact,
                        publish_candidate, diagnostics, DeadlineReached)


def frozen_coefficients(problem, assignment, powers):
    """Unit MMSE directions; all coefficients indexed by user."""
    b = np.zeros(problem.k)
    c = np.zeros((problem.k, problem.k))
    n = np.ones(problem.k)
    for s, users in enumerate(assignment):
        hs = problem.h[list(users), :, s].T
        cov = np.eye(problem.m, dtype=complex) + (hs * powers[list(users)]) @ hs.conj().T
        directions = np.linalg.solve(cov, hs)
        for col, i in enumerate(users):
            w = directions[:, col]
            norm = np.linalg.norm(w)
            if norm == 0:
                # Zero desired channel: choose an arbitrary unit direction;
                # a_i=0 removes its objective term consistently.
                w = np.zeros(problem.m, complex)
                w[0] = 1
            else:
                w = w/norm
            b[i] = abs(np.vdot(w, problem.h[i, :, s]))
            n[i] = float(np.vdot(w, w).real)
            for j in users:
                if j != i:
                    c[i, j] = abs(np.vdot(w, problem.h[j, :, s]))**2
    if not all(np.all(np.isfinite(x)) for x in (b, c, n)):
        raise ValueError('nonfinite MMSE coefficients')
    return b, c, n


def tangent_coefficients(b, c, n, vbar):
    return b*vbar/(n+c@(vbar*vbar))


def surrogate(v, b, c, n, a):
    """Return H, gradient, t and Jacobian. C1 log extension outside domain."""
    t = 2*a*b*v-a*a*(n+c@(v*v))
    jac = np.diag(2*a*b)-2*(a*a)[:, None]*c*v[None, :]
    z = 1+t
    floor = 1e-8
    safe = np.maximum(z, floor)
    logs = np.log(safe) + np.minimum(z-floor, 0)/floor
    return float(np.sum(logs)), np.sum(jac/safe[:, None], axis=0), t, jac


def solve_surrogate(vbar, b, c, n, a, low, high, budget, deadline, counter=None):
    """Convex SCA subproblem, NOT SLSQP on original nonconvex rate."""
    calls = 0
    def fun(v):
        nonlocal calls
        guard(deadline)
        calls += 1
        if counter is not None:
            counter['evaluations'] += 1
        h, grad, _, _ = surrogate(v, b, c, n, a)
        return -h, -grad
    def tg(v):
        guard(deadline)
        return surrogate(v, b, c, n, a)[2]
    def tj(v):
        guard(deadline)
        return surrogate(v, b, c, n, a)[3]
    def bg(v):
        guard(deadline)
        return budget-np.dot(v, v)
    result = minimize(fun, vbar, jac=True, method='SLSQP',
                      bounds=[(math.sqrt(low), math.sqrt(high))]*len(vbar),
                      constraints=[dict(type='ineq', fun=tg, jac=tj),
                                   dict(type='ineq', fun=bg, jac=lambda v: -2*v)],
                      options=dict(ftol=1e-10, maxiter=500))
    guard(deadline)
    return result, calls


def stationarity_residual(v, gradient, low, high, budget):
    """Projected-gradient mapping for actual objective in power coordinates."""
    try:
        from .common import project
    except ImportError:
        from common import project
    p = v*v
    scale = max(1.0, float(np.linalg.norm(gradient, np.inf)))
    return float(np.linalg.norm(project(p+gradient/scale, low, high, budget)-p, np.inf))


def refine_power(problem, assignment, p0, deadline, rng, publish):
    del rng  # deterministic conditional on common start and assignment
    began = time.monotonic()
    d = diagnostics('FU_SCA')
    out = np.array(p0, float)
    current = None
    try:
        current = checked(problem, assignment, out, deadline)
        d['evaluations'] += 1
        out = current['numeric'].copy()
        low, high, cap = float(problem.low), float(problem.high), float(problem.budget)
        if low == high or problem.k*problem.low == problem.budget:
            d['stop_reason'] = 'singleton_feasible_set'
            return out, d
        while True:
            guard(deadline)
            d['iterations'] += 1
            try:
                b, c, n = frozen_coefficients(problem, assignment, out)
            except (ValueError, np.linalg.LinAlgError, FloatingPointError):
                d['error_count'] += 1
                d['stop_reason'] = 'receiver_numerical_failure'
                return out, d
            vbar = np.sqrt(out)
            a = tangent_coefficients(b, c, n, vbar)
            old_h = surrogate(vbar, b, c, n, a)[0]
            seed = vbar.copy()
            while True:
                guard(deadline)
                try:
                    result, calls = solve_surrogate(seed, b, c, n, a, low, high, cap, deadline, counter=d)
                    proposal = projected_exact(problem, result.x*result.x)
                except (ValueError, np.linalg.LinAlgError, FloatingPointError):
                    d['error_count'] += 1
                    d['stop_reason'] = 'subproblem_numerical_failure'
                    return out, d
                hnew, _, tnew, _ = surrogate(np.sqrt(proposal), b, c, n, a)
                tolerance = 1e-9+1e-10*max(1, abs(old_h))
                if (not np.all(np.isfinite(proposal)) or np.min(tnew) < -1e-9
                        or hnew < old_h-tolerance):
                    d['error_count'] += 1
                    d['stop_reason'] = 'surrogate_validation_failure'
                    return out, d
                if int(result.status) == 9:
                    d['cap_count'] += 1
                    # Resume the SAME frozen convex block, with feasible endpoint.
                    seed = np.sqrt(proposal)
                    continue
                break
            candidate = checked(problem, assignment, proposal, deadline)
            d['evaluations'] += 1
            if improves(candidate, current):
                old_value = current['value']
                current = candidate
                out = current['numeric'].copy()
                d['accepted'] += 1
                publish_candidate(publish, assignment, current, d, deadline)
                gain = current['value']-old_value
            else:
                gain = 0.0
            _, gradient = problem.value_gradient(assignment, out)
            d['evaluations'] += 1
            residual = stationarity_residual(np.sqrt(out), gradient, low, high, cap)
            d['stationarity_residual'] = residual
            d['last_subproblem_status'] = int(result.status)
            if gain <= 1e-9+1e-9*max(1, abs(current['value'])):
                if residual <= 1e-7:
                    d['stop_reason'] = 'stationary_tolerance'
                else:
                    d['stop_reason'] = 'numerical_stall'
                break
    except DeadlineReached:
        d['stop_reason'] = 'deadline'
    finally:
        d['elapsed_seconds'] = time.monotonic()-began
    return out, d
