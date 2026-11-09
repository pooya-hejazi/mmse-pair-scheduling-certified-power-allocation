"""Matched, bounded full-schedule baselines; numerical candidates, not certificates.

Public API: solve(case, method, seconds=20), method in grid/slsqp/iwmmse.
All times include construction and evaluation inside this call, but not imports.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

from fractions import Fraction as F
from itertools import combinations, product
import math
import time
import numpy as np
from scipy.optimize import minimize, linprog, milp, Bounds, LinearConstraint
from scipy.sparse import csc_matrix


# Optional campaign callback: persists exact-validated feasible candidates.
PROGRESS = lambda result: None
GRID_LEVELS = None
NATIVE_CAP = 10.

class Deadline(Exception):
    pass


def assignments(k, resource=0, remaining=None):
    """All unordered pairs on labelled resources, in deterministic order."""
    remaining = tuple(range(k)) if remaining is None else remaining
    if not remaining:
        yield ()
        return
    for u, v in combinations(remaining, 2):
        rest = tuple(i for i in remaining if i not in (u, v))
        for tail in assignments(k, resource + 1, rest):
            yield ((u, v, resource),) + tail


def _read(case):
    k, s = int(case['K']), int(case['S'])
    low, high, budget = map(F, (case['pmin'], case['pmax'], case['budget']))
    if k != 2*s or not 0 <= low <= high or k*low > budget:
        raise ValueError('infeasible domain')
    lookup = {}
    for row in case['pairs']:
        u, v = map(int, row['users']); t = int(row['resource'])
        g1, g2, r = map(F, (row['gain1'], row['gain2'], row['r']))
        if not (0 <= u < v < k and 0 <= t < s and g1 >= 0 and g2 >= 0 and 0 <= r <= 1):
            raise ValueError('invalid pair')
        key = (u, v, t)
        if key in lookup:
            raise ValueError('duplicate pair')
        lookup[key] = (float(g1), float(g2), float(r))
    if len(lookup) != s*k*(k-1)//2:
        raise ValueError('incomplete all-pair family')
    return k, s, low, high, budget, lookup


def repair_exact(p, low, high, budget):
    """Clip binary64 proposal exactly and remove any sum-budget excess."""
    if not all(np.isfinite(z) for z in p):
        raise ValueError('nonfinite candidate')
    vals = [max(low, min(high, F(float(z)))) for z in p]
    excess = max(F(0), sum(vals, F(0))-budget)
    for i in range(len(vals)):
        take = min(excess, vals[i]-low)
        vals[i] -= take
        excess -= take
    assert excess == 0 and sum(vals, F(0)) <= budget
    return vals


def value_gradient(p, schedule, lookup):
    out = 0.0
    grad = np.zeros(len(p))
    for u, v, t in schedule:
        g1, g2, r = lookup[u, v, t]
        x, y, a = g1*p[u], g2*p[v], 1-r
        d = 1+x+y+a*x*y
        out += 2*np.log(d)-np.log1p(x)-np.log1p(y)
        grad[u] = g1*(2*(1+a*y)/d-1/(1+x))
        grad[v] = g2*(2*(1+a*x)/d-1/(1+y))
    return float(out), grad


def _schedule_json(schedule, p):
    return [{'users': [u, v], 'resource': t, 'powers': [str(p[u]), str(p[v])]}
            for u, v, t in schedule]


def _local(case, method, seconds):
    began = time.perf_counter()
    deadline = began + seconds
    k, s, low, high, budget, lookup = _read(case)
    lo, hi, cap = float(low), float(high), float(budget)
    count_total = math.factorial(k)//2**s
    first = next(assignments(k))
    p0 = [min(high, budget/k)]*k
    best = {'p': p0, 'schedule': first,
            'value': value_gradient(np.array(list(map(float, p0))), first, lookup)[0]}
    visited = complete = starts_done = iterations = 0
    numerical_failures = 0
    finite_iteration_stops = 0
    largest_wmmse_descent = 0.0

    def alive():
        if time.perf_counter() >= deadline:
            raise Deadline

    def retain(p, schedule):
        nonlocal best
        exact = repair_exact(p, low, high, budget)
        numeric = np.array(list(map(float, exact)))
        q = value_gradient(numeric, schedule, lookup)[0]
        if q > best['value']:
            best = {'p': exact, 'schedule': schedule, 'value': q}
        PROGRESS({'schedule': _schedule_json(best['schedule'], best['p']), 'status': 'LOCAL_PROGRESS'})
        return numeric, q

    status = 'ALL_ASSIGNMENTS_VISITED_LOCAL_ONLY'
    try:
        for schedule in assignments(k):
            alive()
            visited += 1
            starts = [np.full(k, lo), np.full(k, min(hi, cap/k))]
            for start in starts:
                alive()
                p, before = retain(start, schedule)
                if method == 'slsqp':
                    def objective(z):
                        alive()
                        q, grad = value_gradient(z, schedule, lookup)
                        return -q, -grad
                    def callback(z):
                        retain(z, schedule)
                        alive()
                    sol = minimize(objective, p, jac=True, method='SLSQP',
                                   bounds=[(lo, hi)]*k,
                                   constraints=[{'type': 'ineq', 'fun': lambda z: cap-z.sum(),
                                                 'jac': lambda z: -np.ones(k)}],
                                   callback=callback,
                                   options={'maxiter': 500, 'ftol': 1e-10})
                    iterations += int(sol.nit)
                    numerical_failures += not bool(sol.success)
                    retain(sol.x, schedule)
                else:
                    converged = False
                    for it in range(500):
                        alive()
                        aa, bb = np.zeros(k), np.zeros(k)
                        for u, v, t in schedule:
                            g1, g2, r = lookup[u, v, t]
                            ids = np.array([u, v])
                            amps = np.sqrt(p[ids])
                            cross = np.sqrt(g1*g2*r)
                            gram = np.array([[g1, cross], [cross, g2]])
                            coupling = np.eye(2) + amps[:, None]*gram*amps[None, :]
                            # G_ij = u_i^H h_j, via the two-dimensional Gram system.
                            G = np.linalg.solve(coupling, amps[:, None]*gram)
                            x, y = g1*p[u], g2*p[v]
                            d = 1+x+y+(1-r)*x*y
                            errors = np.array([(1+y)/d, (1+x)/d])
                            weights = 1/errors
                            aa[ids] = (weights[:, None]*(G*G)).sum(axis=0)
                            bb[ids] = weights*np.diag(G)
                        def update(lam):
                            return np.clip(bb/np.maximum(aa+lam, 1e-300),
                                           np.sqrt(lo), np.sqrt(hi))**2
                        candidate = update(0.0)
                        if candidate.sum() > cap:
                            left, right = 0.0, max(1.0, float(np.max(bb)/max(np.sqrt(lo), 1e-150)))
                            for _ in range(100):
                                if update(right).sum() <= cap:
                                    break
                                right *= 2
                            else:
                                raise ArithmeticError('power-price bracket failed')
                            for _ in range(60):
                                mid = (left+right)/2
                                if update(mid).sum() > cap:
                                    left = mid
                                else:
                                    right = mid
                            candidate = update(right)
                        numeric, after = retain(candidate, schedule)
                        iterations += 1
                        descent = before-after
                        largest_wmmse_descent = max(largest_wmmse_descent, descent)
                        if descent > 1e-7*max(1.0, abs(before)):
                            numerical_failures += 1
                            break
                        gain = after-before
                        p, before = numeric, after
                        if gain <= 1e-9*max(1.0, abs(after)):
                            converged = True
                            break
                    finite_iteration_stops += not converged
                starts_done += 1
            complete += 1
    except Deadline:
        status = 'TIME_LIMIT_LOCAL_INCUMBENT'
    return {'method': method, 'status': status,
            'schedule': _schedule_json(best['schedule'], best['p']),
            'Q_nats': best['value'], 'radiated_power': str(sum(best['p'], F(0))),
            'assignments_total': count_total, 'assignments_visited': visited,
            'assignments_completed': complete, 'starts_completed': starts_done,
            'iterations': iterations, 'numerical_solver_failures': int(numerical_failures),
            'finite_iteration_stops': int(finite_iteration_stops),
            'largest_wmmse_numerical_descent': largest_wmmse_descent,
            'seconds': time.perf_counter()-began,
            'scope': 'feasible numerical candidate; all-schedule visitation is not global continuous optimality'}


def _grid(case, seconds):
    began = time.perf_counter()
    k, s, low, high, budget, lookup = _read(case)
    levels = [v for v in (GRID_LEVELS or (F(1,20), F(1,10), F(1,5))) if low <= v <= high]
    if not levels or k*min(levels) > budget:
        raise ValueError('declared grid infeasible')
    columns, rates, costs = [], [], []
    for u, v, t in sorted(lookup):
        g1, g2, r = lookup[u, v, t]
        for p1, p2 in product(levels, repeat=2):
            x, y = g1*float(p1), g2*float(p2)
            q = 2*np.log1p(x+y+(1-r)*x*y)-np.log1p(x)-np.log1p(y)
            columns.append((u,v,t,p1,p2));rates.append(q);costs.append(float(p1+p2))
    A = np.zeros((k+s, len(columns)))
    for j, (u,v,t,*_) in enumerate(columns):
        A[[u,v,k+t],j] = 1
    rates, costs = np.asarray(rates), np.asarray(costs)
    first = next(assignments(k))
    best_p = [min(levels)]*k
    best_schedule = first
    best_value = value_gradient(np.array(list(map(float,best_p))), first, lookup)[0]
    # Separate native caps do not certify a shared external time bound.
    remaining = max(.001, min(NATIVE_CAP, seconds-(time.perf_counter()-began)))
    ip = milp(-rates, integrality=np.ones(len(columns)), bounds=Bounds(0,1),
              constraints=[LinearConstraint(csc_matrix(A),1,1),
                           LinearConstraint(csc_matrix(costs[None,:]),-np.inf,float(budget))],
              options={'time_limit': remaining, 'mip_rel_gap': 0})
    incumbent_valid = False
    if ip.x is not None and np.max(abs(ip.x-np.round(ip.x))) <= 1e-7:
        selected = np.flatnonzero(ip.x > .5)
        if np.all(A[:, selected].sum(axis=1) == 1):
            pp = [None]*k; sched=[]
            for j in selected:
                u,v,t,p1,p2 = columns[j];pp[u]=p1;pp[v]=p2;sched.append((u,v,t))
            if all(p is not None for p in pp) and sum(pp,F(0)) <= budget:
                best_p, best_schedule = pp, tuple(sorted(sched,key=lambda z:z[2]))
                best_value = value_gradient(np.array(list(map(float,pp))), best_schedule, lookup)[0]
                incumbent_valid = True
    remaining = max(.001, min(NATIVE_CAP, seconds-(time.perf_counter()-began)))
    PROGRESS({'schedule': _schedule_json(best_schedule,best_p), 'status': 'GRID_MILP_PROGRESS'})
    if time.perf_counter()-began >= seconds:
        return {'schedule': _schedule_json(best_schedule,best_p), 'status': 'GRID_NO_TIME_FOR_LP'}
    lp = linprog(-rates, A_ub=costs[None,:], b_ub=[float(budget)],
                 A_eq=A, b_eq=np.ones(k+s), bounds=(0,None), method='highs',
                 options={'time_limit': remaining})
    out = {'method': 'grid', 'status': 'GRID_SOLVES_RETURNED',
           'schedule': _schedule_json(best_schedule,best_p), 'Q_nats': best_value,
           'radiated_power': str(sum(best_p,F(0))), 'columns': len(columns),
           'MILP_status': int(ip.status), 'MILP_message': str(ip.message),
           'MILP_incumbent_valid': incumbent_valid,
           'numerical_MILP_nats': float(-ip.fun) if ip.fun is not None else None,
           'numerical_MILP_gap': float(ip.mip_gap) if getattr(ip,'mip_gap',None) is not None else None,
           'numerical_MILP_dual_bound': float(-ip.mip_dual_bound) if getattr(ip,'mip_dual_bound',None) is not None else None,
           'LP_status': int(lp.status), 'LP_message': str(lp.message),
           'numerical_LP_nats': float(-lp.fun) if lp.fun is not None else None,
           'seconds': time.perf_counter()-began,
           'scope': 'numerical finite-grid ILP/LP; LP is not a continuous-domain bound'}
    if lp.success:
        out['alpha'] = [str(F(float(-v))) for v in lp.eqlin.marginals[:k]]
        out['lambda'] = str(max(F(0),F(float(-lp.ineqlin.marginals[0]))))
        out['resource_duals'] = [str(F(float(-v))) for v in lp.eqlin.marginals[k:]]
    return out


def solve(case, method, seconds=20):
    if not np.isfinite(seconds) or seconds < 0:
        raise ValueError('invalid time budget')
    if method == 'grid':
        return _grid(case,seconds)
    if method in ('slsqp','iwmmse'):
        return _local(case,method,seconds)
    raise ValueError('unknown method')
