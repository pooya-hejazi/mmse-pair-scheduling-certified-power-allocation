"""Independent proof checker: standard library only, no producer/optimizer import.

Log bounds use integer fixed-point atanh sums with explicit remainder bounds,
not Decimal/SymPy or the producer logarithm. All delivered upper bounds are
recomputed from complete domains. Historical claimed upper numbers are unused.
"""
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import math
import time

F = Fraction
UNIT = 1 << 100
TERMS = 40
MAX_EVENTS = 6000
MAX_ROOTS = 3000
_CHANNEL_BINDINGS = set()


def clear_caches():
    """Call before each charged cell; reuse within a cell is permitted."""
    log_enclosure.cache_clear()
    _support.cache_clear()
    _CHANNEL_BINDINGS.clear()


def _require(ok, text):
    if not ok:
        raise ValueError(text)


def _integer(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _ceildiv(a, b):
    return -((-a)//b)


def _atanh_bounds(y):
    # 0 <= y <= 1/3. Every integer operation rounds outwards at scale UNIT.
    _require(0 <= y <= F(1, 3), 'atanh domain')
    low = y.numerator*UNIT//y.denominator
    high = _ceildiv(y.numerator*UNIT, y.denominator)
    sq_low, sq_high = low*low//UNIT, _ceildiv(high*high, UNIT)
    pl, ph, sl, sh = low, high, 0, 0
    for n in range(TERMS):
        sl += pl//(2*n+1)
        sh += _ceildiv(ph, 2*n+1)
        pl = pl*sq_low//UNIT
        ph = _ceildiv(ph*sq_high, UNIT)
    # Entire positive tail bounded using y <= 1/3, after powers through 2N-1.
    tail = F(2, (2*TERMS+1)*3**(2*TERMS+1))*F(9, 8)
    return F(2*sl, UNIT), F(2*sh+_ceildiv(tail.numerator*UNIT, tail.denominator), UNIT)


LOG2 = _atanh_bounds(F(1, 3))


@lru_cache(maxsize=40000)
def log_enclosure(value):
    """Exact rational enclosure of ln(value), including values below one."""
    z = F(value)
    _require(z > 0, 'nonpositive logarithm')
    if z == 1:
        return F(0), F(0)
    k = z.numerator.bit_length()-z.denominator.bit_length()
    q = z / (F(2)**k)
    if q < 1:
        q *= 2; k -= 1
    if q >= 2:
        q /= 2; k += 1
    _require(1 <= q < 2, 'log range reduction')
    l, u = _atanh_bounds((q-1)/(q+1))
    return ((l+k*LOG2[0], u+k*LOG2[1]) if k >= 0
            else (l+k*LOG2[1], u+k*LOG2[0]))


def _rate(g, h, r, p, q):
    x, y = g*p, h*q
    d = log_enclosure(1+x+y+(1-r)*x*y)
    first, second = log_enclosure(1+x), log_enclosure(1+y)
    return 2*d[0]-first[1]-second[1], 2*d[1]-first[0]-second[0]


@lru_cache(maxsize=40000)
def _support(g, h, r, lower_p, upper_p, lower_q, upper_q, at_p, at_q, curvature):
    # Independently rebuild both valid majorants from their mathematical formulas.
    a = 1-r
    x, y = g*at_p, h*at_q
    d = 1+x+y+a*x*y
    lx, ux, ly, uy = g*lower_p, g*upper_p, h*lower_q, h*upper_q
    if curvature and 2*a*a >= 1:
        dx = 2*(1+a*y)/d-1/(1+x)
        dy = 2*(1+a*x)/d-1/(1+y)
        intercept = _rate(g, h, r, at_p, at_q)[1]-dx*x-dy*y
    else:
        dx, dy = 2*(1+a*y)/d, 2*(1+a*x)/d
        intercept = 2*log_enclosure(d)[1]-dx*x-dy*y
        for axis, l, u in ((0, lx, ux), (1, ly, uy)):
            fl = -log_enclosure(1+l)[0]
            slope = F(0) if l == u else (-log_enclosure(1+u)[0]-fl)/(u-l)
            intercept += fl-slope*l
            if axis == 0:
                dx += slope
            else:
                dy += slope
    direct = log_enclosure(1+ux*(1+a*ly)/(1+ly))[1]
    direct += log_enclosure(1+uy*(1+a*lx)/(1+lx))[1]
    return (g*dx, h*dy), intercept, direct


def _deadline(seconds):
    stop = None if seconds is None else time.perf_counter()+max(0, float(seconds))
    def check():
        if stop is not None and time.perf_counter() >= stop:
            raise TimeoutError('independent verification deadline')
    return check


def _case(case, check):
    check()
    k, s = case['K'], case['S']
    _require(_integer(k) and _integer(s) and k >= 2 and k == 2*s, 'dimensions')
    low, high, budget = (F(case[n]) for n in ('pmin', 'pmax', 'budget'))
    _require(0 <= low <= high and k*low <= budget, 'power domain')
    data, gain = {}, {}
    for row in case['pairs']:
        check()
        _require(len(row['users']) == 2, 'pair size')
        u, v = row['users']; t = row['resource']
        _require(all(_integer(i) for i in (u, v, t)), 'pair index type')
        _require(0 <= u < v < k and 0 <= t < s, 'pair indices')
        key = u, v, t
        _require(key not in data, 'duplicate pair')
        g, h, r = (F(row[n]) for n in ('gain1', 'gain2', 'r'))
        _require(g >= 0 and h >= 0 and 0 <= r <= 1, 'pair scalars')
        _require((g != 0 and h != 0) or r == 0, 'zero gain convention')
        for i, val in ((u, g), (v, h)):
            _require((i, t) not in gain or gain[i, t] == val, 'gain inconsistency')
            gain[i, t] = val
        data[key] = g, h, r
    _require(len(data) == s*k*(k-1)//2, 'incomplete model')
    return k, s, low, high, budget, data, gain


def _schedule(rows, k, s, low, high, budget, data):
    _require(isinstance(rows, list) and len(rows) == s, 'schedule size')
    seen_users, seen_resources, lower, upper = set(), set(), F(0), F(0)
    for row in rows:
        _require(len(row['users']) == 2 and len(row['powers']) == 2, 'schedule pair length')
        u, v = row['users']; t = row['resource']
        _require(all(_integer(i) for i in (u, v, t)) and (u, v, t) in data, 'schedule indices')
        _require(u not in seen_users and v not in seen_users and t not in seen_resources, 'schedule duplicate')
        seen_users.update((u, v)); seen_resources.add(t)
        p, q = map(F, row['powers'])
        _require(low <= p <= high and low <= q <= high, 'schedule box')
        budget -= p+q
        l, h = _rate(*data[u, v, t], p, q)
        lower += l; upper += h
    _require(len(seen_users) == k and budget >= 0, 'schedule service/budget')
    return lower, upper


def _check_channels(case, digest, k, s, data, gain, check):
    """Independently bind scalar coefficients to optional stored complex vectors."""
    has_re, has_im = 'channels_re' in case, 'channels_im' in case
    _require(has_re == has_im, 'incomplete channel arrays')
    if not has_re:
        return False
    if digest in _CHANNEL_BINDINGS:
        return True
    m = case['M']; re, im = case['channels_re'], case['channels_im']
    _require(_integer(m) and m > 0 and len(re) == len(im) == k, 'channel dimensions')
    vectors = {}
    for i in range(k):
        _require(len(re[i]) == len(im[i]) == m, 'channel antenna dimensions')
        _require(all(len(re[i][j]) == len(im[i][j]) == s for j in range(m)), 'channel resource dimensions')
        for t in range(s):
            check()
            vec = tuple((F(re[i][j][t]), F(im[i][j][t])) for j in range(m))
            _require(sum(x*x+y*y for x, y in vec) == gain[i, t], 'channel gain mismatch')
            vectors[i, t] = vec
    for (u, v, t), (g, h, r) in data.items():
        check()
        left, right = vectors[u, t], vectors[v, t]
        real = sum(a*c+b*d for (a, b), (c, d) in zip(left, right))
        imag = sum(a*d-b*c for (a, b), (c, d) in zip(left, right))
        expected = (real*real+imag*imag)/(g*h) if g*h else F(0)
        _require(expected == r, 'channel correlation mismatch')
    if len(_CHANNEL_BINDINGS) >= 2:
        _CHANNEL_BINDINGS.clear()
    _CHANNEL_BINDINGS.add(digest)
    return True


def _partition(events, low, high, check):
    """Replay a full binary subdivision; no implicit pruning or missing child."""
    _require(isinstance(events, list) and len(events) <= MAX_EVENTS, 'partition size')
    leaves = {'': (tuple(low), tuple(high))}
    for event in events:
        check()
        _require(isinstance(event, list) and len(event) == 3, 'split shape')
        path, dim, raw = event
        _require(isinstance(path, str) and len(path) <= MAX_EVENTS and path in leaves, 'missing/duplicate split parent')
        _require(_integer(dim) and 0 <= dim < len(low), 'split dimension')
        l, h = leaves.pop(path); cut = F(raw)
        _require(l[dim] < cut < h[dim], 'split outside domain')
        lh, rl = list(h), list(l); lh[dim] = cut; rl[dim] = cut
        leaves[path+'0'] = l, tuple(lh)
        leaves[path+'1'] = tuple(rl), h
    return leaves.values()


def _price(params, lo, hi, events, check):
    g, h, r, lam = params
    lower, upper = None, None
    for l, u in _partition(events, (lo, lo), (hi, hi), check):
        check()
        middle = tuple((a+b)/2 for a, b in zip(l, u))
        coeff, constant, direct = _support(g, h, r, l[0], u[0], l[1], u[1], *middle, True)
        adjusted = tuple(c-lam for c in coeff)
        affine = constant+sum(c*(b if c >= 0 else a) for c, a, b in zip(adjusted, l, u))
        ub = min(affine, direct-lam*sum(l))
        lb = _rate(g, h, r, *middle)[0]-lam*sum(middle)
        lower = lb if lower is None else max(lower, lb)
        upper = ub if upper is None else max(upper, ub)
    _require(lower is not None and lower <= upper, 'pricing interval')
    return lower, upper


def verify_pair(candidate, seconds=None):
    check = _deadline(seconds)
    proof = candidate.get('proof', candidate)
    _require(set(proof) == {'schema', 'inputs', 'splits'} and proof['schema'] == 'PAIR_PARTITION_V1', 'pair proof schema')
    _require(len(proof['inputs']) == 6, 'pair inputs')
    g, h, r, lam, lo, hi = map(F, proof['inputs'])
    _require(min(g, h, lam, lo) >= 0 and 0 <= r <= 1 and lo <= hi, 'pair domain')
    _require((g != 0 and h != 0) or r == 0, 'zero gain convention')
    lower, upper = _price((g, h, r, lam), lo, hi, proof['splits'], check)
    check()
    return dict(valid=True, lower_nats=str(lower), upper_nats=str(upper), gap_nats=str(upper-lower),
                arithmetic='integer fixed-point logarithm enclosures with rational remainder')


def _spatial_leaf(pairs, lo, hi, budget, data, curvature):
    if sum(lo) > budget:
        return None
    hi = tuple(min(h, budget-sum(lo)+l) for l, h in zip(lo, hi))
    span = sum(h-l for l, h in zip(lo, hi))
    weight = min(F(1, 2), (budget-sum(lo))/span) if span else F(0)
    middle = tuple(l+weight*(h-l) for l, h in zip(lo, hi))
    slopes, constant, direct = [F(0)]*len(lo), F(0), F(0)
    for s, (u, v) in enumerate(pairs):
        ab, c, m = _support(*data[u, v, s], lo[u], hi[u], lo[v], hi[v], middle[u], middle[v], curvature)
        slopes[u], slopes[v] = ab
        constant += c; direct += m
    # Exact continuous knapsack maximization under the remaining shared budget.
    affine = constant+sum(c*l for c, l in zip(slopes, lo))
    left = budget-sum(lo)
    for c, room in sorted(((c, h-l) for c, l, h in zip(slopes, lo, hi)), reverse=True):
        if c <= 0 or left <= 0:
            break
        take = min(room, left); affine += c*take; left -= take
    return min(affine, direct)


def verify(case, candidate_or_proof, schedule=None, seconds=None):
    """Derive independently justified bounds; raise on malformed proof or timeout.

    Missing spatial assignments are accepted ONLY with the explicit universal
    cover; incomplete dual families are rejected. No supplied upper is trusted.
    """
    began = time.perf_counter(); check = _deadline(seconds)
    proof = candidate_or_proof.get('proof', candidate_or_proof)
    if schedule is None:
        schedule = candidate_or_proof.get('schedule')
    _require(set(proof) == {'schema', 'case_sha256', 'universal', 'dual', 'spatial'}, 'proof keys')
    _require(proof['schema'] == 'MMSE_PARTITION_PROOF_V1' and proof['universal'] is True, 'proof schema')
    encoded = json.dumps(case, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    _require(hashlib.sha256(encoded).hexdigest() == proof['case_sha256'], 'case hash mismatch')
    k, s, low, high, budget, data, gain = _case(case, check)
    channels_checked = _check_channels(case, proof['case_sha256'], k, s, data, gain, check)
    lower, incumbent_upper = _schedule(schedule, k, s, low, high, budget, data)
    ceiling = sum(max(log_enclosure(1+gain[i, t]*high)[1] for t in range(s)) for i in range(k))
    upper = ceiling
    metrics = dict(pricing_rows=0, spatial_roots=0, spatial_leaves=0, proof_splits=0,
                   stored_channel_coefficients_checked=channels_checked,
                   assignments_total=math.factorial(k)//2**s, complete_assignment_coverage=False)
    if proof['dual'] is not None:
        dual = proof['dual']
        _require(set(dual) == {'alpha', 'lambda_value', 'rows'}, 'dual keys')
        _require(len(dual['alpha']) == k and isinstance(dual['rows'], list), 'dual size')
        alpha = list(map(F, dual['alpha'])); lam = F(dual['lambda_value'])
        _require(lam >= 0 and len(dual['rows']) == len(data), 'dual sign/complete coverage')
        seen, beta = set(), [None]*s
        for row in dual['rows']:
            check()
            _require(set(row) == {'users', 'resource', 'splits'} and len(row['users']) == 2, 'price row keys')
            u, v = row['users']; t = row['resource']; key = u, v, t
            _require(all(_integer(i) for i in key) and key in data and key not in seen, 'price row incidence')
            seen.add(key)
            metrics['proof_splits'] += len(row['splits'])
            _require(metrics['proof_splits'] <= MAX_EVENTS, 'aggregate proof size')
            _, price_upper = _price((*data[key], lam), low, high, row['splits'], check)
            val = price_upper-alpha[u]-alpha[v]
            beta[t] = val if beta[t] is None else max(val, beta[t])
        _require(seen == set(data), 'missing prices')
        dual_upper = sum(alpha)+sum(beta)+lam*budget
        upper = min(upper, dual_upper); metrics['pricing_rows'] = len(seen)
        metrics['dual_upper_nats'] = str(dual_upper)
    if proof['spatial'] is not None:
        sp = proof['spatial']
        _require(set(sp) == {'curvature', 'roots', 'unlisted'} and isinstance(sp['curvature'], bool), 'spatial keys')
        _require(sp['unlisted'] == 'universal' and isinstance(sp['roots'], list) and len(sp['roots']) <= MAX_ROOTS, 'spatial cover')
        seen, spatial_upper = set(), None
        for root in sp['roots']:
            check()
            _require(set(root) == {'pairs', 'splits'} and len(root['pairs']) == s, 'spatial root')
            _require(all(isinstance(p, list) and len(p) == 2 for p in root['pairs']), 'root pair shape')
            pairs = tuple(tuple(p) for p in root['pairs'])
            _require(all(all(_integer(i) for i in p) and (p[0], p[1], t) in data for t, p in enumerate(pairs)), 'root indices')
            _require(sorted(i for pair in pairs for i in pair) == list(range(k)), 'root user cover')
            _require(pairs not in seen, 'duplicate root'); seen.add(pairs)
            metrics['proof_splits'] += len(root['splits'])
            _require(metrics['proof_splits'] <= MAX_EVENTS, 'aggregate proof size')
            for lo, hi in _partition(root['splits'], (low,)*k, (high,)*k, check):
                check(); metrics['spatial_leaves'] += 1
                bound = _spatial_leaf(pairs, lo, hi, budget, data, sp['curvature'])
                if bound is not None:
                    spatial_upper = bound if spatial_upper is None else max(spatial_upper, bound)
        count = len(seen)
        _require(count <= metrics['assignments_total'], 'too many roots')
        metrics['spatial_roots'] = count
        metrics['complete_assignment_coverage'] = count == metrics['assignments_total']
        if count < metrics['assignments_total']:
            spatial_upper = ceiling if spatial_upper is None else max(spatial_upper, ceiling)
        _require(spatial_upper is not None, 'no feasible domain cover')
        upper = min(upper, spatial_upper); metrics['spatial_upper_nats'] = str(spatial_upper)
    check()
    _require(lower <= upper, 'upper below validated incumbent')
    return dict(valid=True, lower_nats=str(lower), upper_nats=str(upper), gap_nats=str(upper-lower),
                incumbent_upper_nats=str(incumbent_upper), metrics=metrics,
                certificate_mathematical=upper-lower <= F(1, 100), seconds=time.perf_counter()-began,
                arithmetic='integer fixed-point logarithm enclosures with rational remainder')
