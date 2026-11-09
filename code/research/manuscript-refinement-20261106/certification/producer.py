"""Numerical proposals plus exact finite-box bounds and integral scheduling.

No finite-candidate algebraic oracle is used. The independently implemented
checker.py, not numerical optimizer termination, decides validity.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

from fractions import Fraction as F
import hashlib
import heapq
import json
import math
import time
import numpy as np
from scipy.optimize import minimize
from integer_logs import log_enclosure as logb

BITS = 40
SCALE = 1 << BITS
MAX_SPLITS = 1200


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def seal(candidate):
    candidate['witness_sha256'] = digest(candidate)
    return candidate


def ceil_units(value):
    value *= SCALE
    return -((-value.numerator)//value.denominator)


def concavity(r, lx, ux, ly, uy):
    """Exact sufficient test; returns the mathematical justification used."""
    a = 1-r
    if 2*a*a >= 1:
        return 'quadrant'
    d = lambda x, y: 1+x+y+a*x*y
    u0 = (1+lx)*(1+a*uy)/d(lx, uy)
    v0 = (1+ly)*(1+a*ux)/d(ux, ly)
    w0 = min(r*(1+ux)*(1+uy)/d(lx, ly)**2,
             r*((1+ux)*(1+uy))**2/((1+lx)*(1+ly)*d(ux, uy)**2))
    b, c = 2*u0*u0-1, 2*v0*v0-1
    return 'finite_box' if b >= 0 and c >= 0 and b*c >= 4*w0*w0 else 'generic'


def rate_bounds(data, p, q):
    g, h, r = data
    x, y = g*p, h*q
    dl, du = logb(1+x+y+(1-r)*x*y)
    al, au = logb(1+x)
    bl, bu = logb(1+y)
    return 2*dl-au-bu, 2*du-al-bl


def leaf_bound(data, lam, lo, hi, point):
    g, h, r = data
    a = 1-r
    lx, ux, ly, uy = g*lo[0], g*hi[0], h*lo[1], h*hi[1]
    x, y = g*point[0], h*point[1]
    d = 1+x+y+a*x*y
    tx, ty = 2*(1+a*y)/d, 2*(1+a*x)/d
    reason = concavity(r, lx, ux, ly, uy)
    if reason != 'generic':
        dx, dy = tx-1/(1+x), ty-1/(1+y)
        intercept = rate_bounds(data, *point)[1]-dx*x-dy*y
    else:
        def secant(l, u):
            low = -logb(1+l)[0]
            slope = F(0) if l == u else (-logb(1+u)[0]-low)/(u-l)
            return slope, low-slope*l
        sx, bx = secant(lx, ux)
        sy, by = secant(ly, uy)
        dx, dy = tx+sx, ty+sy
        intercept = 2*logb(d)[1]-tx*x-ty*y+bx+by
    cp, cq = g*dx-lam, h*dy-lam
    affine = intercept+cp*(hi[0] if cp >= 0 else lo[0])+cq*(hi[1] if cq >= 0 else lo[1])
    mixed = logb(1+ux*(1+a*ly)/(1+ly))[1]+logb(1+uy*(1+a*lx)/(1+lx))[1]
    upper = min(affine, mixed-lam*sum(lo))
    return ceil_units(upper), reason


def numeric_value_gradient(data, point, lam=0.):
    g, h, r = map(float, data)
    p, q = point
    x, y, a = g*p, h*q, 1-r
    d = 1+x+y+a*x*y
    val = 2*math.log(d)-math.log1p(x)-math.log1p(y)-lam*(p+q)
    grad = np.array([g*(2*(1+a*y)/d-1/(1+x))-lam,
                     h*(2*(1+a*x)/d-1/(1+y))-lam])
    return val, grad


def point_proposal(data, lam, lo, hi, start=None):
    low, high = np.array(list(map(float, lo))), np.array(list(map(float, hi)))
    start = (low+high)/2 if start is None else np.clip(np.array(list(map(float, start))), low, high)
    def objective(z):
        val, grad = numeric_value_gradient(data, z, float(lam))
        return -val, -grad
    sol = minimize(objective, start, jac=True, method='L-BFGS-B',
                   bounds=list(zip(low, high)),
                   options={'ftol': 1e-14, 'gtol': 1e-10, 'maxiter': 60, 'maxls': 30})
    choices = [start, sol.x] if np.all(np.isfinite(sol.x)) else [start]
    best = max(choices, key=lambda z: numeric_value_gradient(data, z, float(lam))[0])
    exact = tuple(max(l, min(u, F(float(z)))) for z, l, u in zip(best, lo, hi))
    return exact, numeric_value_gradient(data, list(map(float, exact)), float(lam))[0]


class PriceTree:
    def __init__(self, data, lam, low, high):
        self.data, self.lam = data, lam
        self.events, self.leaves, self.heap = [], {}, []
        self.lower_proposal = -math.inf
        self.add('', (low, low), (high, high))

    def add(self, path, lo, hi, start=None):
        point, val = point_proposal(self.data, self.lam, lo, hi, start)
        upper, reason = leaf_bound(self.data, self.lam, lo, hi, point)
        self.lower_proposal = max(self.lower_proposal, val)
        self.leaves[path] = lo, hi, point, upper, reason
        heapq.heappush(self.heap, (-upper, path))

    @property
    def upper(self):
        return -self.heap[0][0]

    @property
    def gap_priority(self):
        return float(F(self.upper, SCALE))-self.lower_proposal

    def split(self):
        _, path = heapq.heappop(self.heap)
        lo, hi, point, upper, reason = self.leaves[path]
        dim = max(range(2), key=lambda i: hi[i]-lo[i])
        if lo[dim] == hi[dim]:
            heapq.heappush(self.heap, (-upper, path))
            return False
        cut = (lo[dim]+hi[dim])/2
        left_hi, right_lo = list(hi), list(lo)
        left_hi[dim] = right_lo[dim] = cut
        # Never commit one child without the other.
        self.add(path+'0', lo, tuple(left_hi), point)
        self.add(path+'1', tuple(right_lo), hi, point)
        del self.leaves[path]
        self.events.append([path, dim, str(cut)])
        return True

    def record(self, key):
        return dict(users=list(key[:2]), resource=key[2], splits=self.events,
                    leaves=[dict(path=p, point=list(map(str, self.leaves[p][2]))) for p in sorted(self.leaves)],
                    upper_units=self.upper)


def integral_dp(k, weights, deadline=math.inf):
    """Bottom-up, arbitrary-size Python integers; labelled resources."""
    n = 1 << k
    values, previous = [None]*n, [None]*n
    values[0] = 0
    table = {(u, v, s): w for (u, v, s), w in weights.items()}
    for mask in range(1, n):
        bits = mask.bit_count()
        if bits % 2:
            continue
        if mask % 128 == 0 and time.perf_counter() >= deadline:
            raise TimeoutError('producer integral DP deadline')
        s = bits//2-1
        remaining, best, chosen = mask, None, None
        while remaining:
            ub = remaining & -remaining
            remaining -= ub
            u = ub.bit_length()-1
            tail = remaining
            while tail:
                vb = tail & -tail
                tail -= vb
                v = vb.bit_length()-1
                old = mask ^ ub ^ vb
                candidate = values[old]+table[u, v, s]
                if best is None or candidate > best:
                    best, chosen = candidate, (u, v)
        values[mask], previous[mask] = best, chosen
    result, mask, pairs = values[-1], n-1, [None]*(k//2)
    for s in reversed(range(k//2)):
        u, v = previous[mask]
        pairs[s] = (u, v)
        mask ^= (1 << u) | (1 << v)
    return result, pairs


def repair(p, low, high, budget):
    vals = [max(low, min(high, F(float(z)))) for z in p]
    excess = max(F(0), sum(vals)-budget)
    for i in range(len(vals)):
        take = min(excess, vals[i]-low)
        vals[i] -= take
        excess -= take
    if excess:
        raise ValueError('infeasible proposal')
    return vals


def encode(pairs, powers):
    return [dict(users=list(pair), resource=s, powers=[str(powers[i]) for i in pair])
            for s, pair in enumerate(pairs)]


def schedule_lower(schedule, data):
    return sum(rate_bounds(data[(*row['users'], row['resource'])], *map(F, row['powers']))[0]
               for row in schedule)


def refine(pairs, start, data, low, high, budget, deadline):
    k = len(start)
    def objective(z):
        if time.perf_counter() >= deadline:
            raise TimeoutError('local proposal deadline')
        val, grad = 0., np.zeros(k)
        for s, (u, v) in enumerate(pairs):
            q, g = numeric_value_gradient(data[u, v, s], (z[u], z[v]))
            val += q
            grad[u], grad[v] = g
        return -val, -grad
    try:
        sol = minimize(objective, list(map(float, start)), jac=True, method='SLSQP',
                       bounds=[(float(low), float(high))]*k,
                       constraints=[dict(type='ineq', fun=lambda p: float(budget)-sum(p),
                                         jac=lambda p: -np.ones(k))],
                       options={'maxiter': 120, 'ftol': 1e-12})
        powers = repair(sol.x, low, high, budget) if np.all(np.isfinite(sol.x)) else list(start)
        status = dict(success=bool(sol.success), iterations=int(sol.nit), message=str(sol.message))
    except TimeoutError:
        powers, status = list(start), dict(success=False, message='proposal deadline')
    return powers, status


def propose_lambda(schedule, data, k, low, high, budget):
    derivatives, used = [], F(0)
    for row in schedule:
        p, q = map(F, row['powers'])
        used += p+q
        _, grad = numeric_value_gradient(data[(*row['users'], row['resource'])], (float(p), float(q)))
        for power, derivative in zip((p, q), grad):
            if float(low)+1e-7 < float(power) < float(high)-1e-7:
                derivatives.append(float(derivative))
    guess = float(np.median(derivatives)) if derivatives else k/float(budget)
    if float(used) < float(budget)-1e-7:
        guess = 0.
    return F(round(max(0., guess)*(1 << 30)), 1 << 30)


def build_price(data, lam, k, low, high, budget, archived_duals, stop):
    began = time.perf_counter()
    reserve = 1.6 if k >= 16 else .15
    pricing_stop = stop-reserve
    trees = {}
    row = dict(lambda_value=str(lam), price_rows=0, splits=0, status='INCOMPLETE_PRICES')
    for key in sorted(data):
        if time.perf_counter() >= pricing_stop:
            break
        trees[key] = PriceTree(data[key], lam, low, high)
    row['price_rows'] = len(trees)
    if len(trees) != len(data):
        row['seconds'] = time.perf_counter()-began
        return None, trees, row
    queue = [(-tree.gap_priority, key) for key, tree in trees.items()]
    heapq.heapify(queue)
    while queue and row['splits'] < MAX_SPLITS and time.perf_counter() < pricing_stop:
        neg, key = heapq.heappop(queue)
        if -neg <= 1e-7:
            break
        if trees[key].split():
            row['splits'] += 1
            heapq.heappush(queue, (-trees[key].gap_priority, key))
    row['pricing_seconds'] = time.perf_counter()-began
    try:
        dp_start = time.perf_counter()
        total, dp_pairs = integral_dp(k, {key: t.upper for key, t in trees.items()}, stop-.05)
        row['dp_seconds'] = time.perf_counter()-dp_start
        price = dict(lambda_value=str(lam), rounding_bits=BITS,
                     rows=[trees[key].record(key) for key in sorted(trees)],
                     dp_units=total, dp_schedule=[list(p) for p in dp_pairs],
                     archived_alpha=(archived_duals or {}).get('alpha'))
        row['upper_nats'] = str(lam*budget+F(total, SCALE))
        row['status'] = 'COMPLETE'
    except TimeoutError as exc:
        price = None
        row.update(status='INCOMPLETE_DP', error=str(exc))
    row['seconds'] = time.perf_counter()-began
    return price, trees, row


def run(case, anchor, binding, archived_duals=None, seconds=10.):
    began = time.perf_counter()
    stop = began+seconds
    logb.cache_clear()
    k, s = case['K'], case['S']
    low, high, budget = map(F, (case['pmin'], case['pmax'], case['budget']))
    data = {(*r['users'], r['resource']): tuple(F(r[n]) for n in ('gain1', 'gain2', 'r'))
            for r in case['pairs']}
    pairs = [None]*s
    powers = [None]*k
    for row in anchor:
        u, v = row['users']
        pairs[row['resource']] = (u, v)
        powers[u], powers[v] = map(F, row['powers'])
    anchor_lower = schedule_lower(anchor, data)
    newpowers, local_status = refine(pairs, powers, data, low, high, budget, min(stop, began+1.))
    schedule = encode(pairs, newpowers)
    best = schedule_lower(schedule, data)
    if best < anchor_lower:
        schedule, newpowers, best = anchor, powers, anchor_lower
    lam = propose_lambda(schedule, data, k, low, high, budget)
    candidate = dict(schema='FINITE_BOX_INTEGRAL_V1', case_sha256=digest(case),
                     binding=binding, anchor_sha256=digest(anchor), schedule=schedule,
                     price=None, metrics={})
    metrics = dict(status='UNIVERSAL_FALLBACK', local_proposal=local_status,
                   lambda_proposal=str(lam), price_rows=0, total_rows=len(data), splits=0, rounds=[],
                   dp_complete=False, algorithm='finite-box tangent / generic split; integral subset DP')
    best_upper = None
    # Up to three price proposals, adapting only to a feasible DP-schedule refiner.
    # Every retained bound has a complete family; failed later rounds cannot erase it.
    for attempt in range(3):
        price, trees, round_metrics = build_price(data, lam, k, low, high, budget, archived_duals, stop)
        metrics['rounds'].append(round_metrics)
        metrics['splits'] += round_metrics['splits']
        metrics['price_rows'] = max(metrics['price_rows'], round_metrics['price_rows'])
        if price is None:
            break
        this_upper = F(round_metrics['upper_nats'])
        if best_upper is None or this_upper < best_upper:
            candidate['price'], best_upper = price, this_upper
        dp_pairs = price['dp_schedule']
        alt = candidate['schedule']
        if time.perf_counter() < stop-.04:
            start = [min(high, budget/k)]*k
            for t, (u, v) in enumerate(dp_pairs):
                leaf = max(trees[u, v, t].leaves.values(), key=lambda leaf: leaf[3])
                start[u], start[v] = leaf[2]
            start = repair(list(map(float, start)), low, high, budget)
            pp, st = refine(dp_pairs, start, data, low, high, budget, stop-.02)
            alt = encode(dp_pairs, pp)
            val = schedule_lower(alt, data)
            round_metrics['local_proposal'] = st
            if val > best:
                candidate['schedule'], best = alt, val
        next_lam = propose_lambda(alt, data, k, low, high, budget)
        if best_upper-best <= F(1, 1000) or abs(lam-next_lam) <= F(1, 10**6):
            break
        lam = next_lam
    metrics['dp_complete'] = candidate['price'] is not None
    metrics['status'] = ('COMPLETE_INTEGRAL_BOUND' if metrics['dp_complete']
                         else metrics['rounds'][-1]['status']+'_UNIVERSAL_RETAINED')
    metrics['seconds'] = time.perf_counter()-began
    metrics['producer_lower_nats'] = str(best)
    metrics['cap_seconds'] = seconds
    metrics['cap_exceeded'] = metrics['seconds'] > seconds
    candidate['metrics'] = metrics
    return seal(candidate)
