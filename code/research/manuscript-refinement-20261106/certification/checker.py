"""Independent standard-library checker. Never imports producer or an optimizer.

Rebuilds exact coefficients from archived binary64 channels, all leaf bounds,
the integer schedule maximum, feasible lower rates, and provenance bindings.
The only shared mathematical code is the pinned integer-log primitive.
"""
from fractions import Fraction as F
from functools import lru_cache
from itertools import combinations
from pathlib import Path
import hashlib
import io
import json
import math
import time
import zipfile
from integer_logs import log_enclosure

SCALE = 1 << 40
MAX_EVENTS = 1200


def require(test, message):
    if not test:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def object_hash(obj):
    return sha(json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def integer(n):
    return isinstance(n, int) and not isinstance(n, bool)


def deadline(seconds):
    stop = math.inf if seconds is None else time.perf_counter()+seconds
    def check():
        if time.perf_counter() >= stop:
            raise TimeoutError('independent verification deadline')
    return check


class ArchivedInputs:
    """Hash/read archive once per replay process; each member is checked again."""
    def __init__(self, path):
        began = time.perf_counter()
        raw = Path(path).read_bytes()
        self.outer_sha256 = sha(raw)
        outer = zipfile.ZipFile(io.BytesIO(raw))
        self.member = 'baseline_R1/Supplementary_Materials.zip'
        nested = outer.read(self.member)
        self.nested_sha256 = sha(nested)
        self.inner = zipfile.ZipFile(io.BytesIO(nested))
        self.seconds = time.perf_counter()-began

    def load(self, binding):
        require(set(binding) == {'outer_sha256', 'nested_sha256', 'nested_member', 'case_member',
                                 'case_file_sha256', 'grid_member', 'grid_file_sha256',
                                 'dual_member', 'dual_file_sha256'}, 'archive binding keys')
        require(binding['outer_sha256'] == self.outer_sha256 and
                binding['nested_sha256'] == self.nested_sha256 and
                binding['nested_member'] == self.member, 'archive hash mismatch')
        result = []
        for member, checksum in (('case_member', 'case_file_sha256'), ('grid_member', 'grid_file_sha256'),
                                 ('dual_member', 'dual_file_sha256')):
            if binding[member] is None:
                require(member == 'dual_member' and binding[checksum] is None, 'missing archive input')
                result.append(None)
            else:
                data = self.inner.read(binding[member])
                require(sha(data) == binding[checksum], 'archived member hash mismatch')
                result.append(json.loads(data))
        case, grid, dual = result
        return case, grid['schedule'], dual


def reconstruct(case, check=lambda: None):
    k, s, m = (case[n] for n in ('K', 'S', 'M'))
    require(all(integer(n) for n in (k, s, m)) and 2 <= k <= 16 and k == 2*s and m > 0, 'dimensions')
    low, high, budget = (F(case[n]) for n in ('pmin', 'pmax', 'budget'))
    require(0 <= low <= high and k*low <= budget, 'power domain')
    re, im = case['channels_re'], case['channels_im']
    require(len(re) == len(im) == k, 'channel user dimensions')
    vectors, gains = {}, {}
    for i in range(k):
        require(len(re[i]) == len(im[i]) == m, 'channel antenna dimensions')
        require(all(len(re[i][j]) == len(im[i][j]) == s for j in range(m)), 'channel resource dimensions')
        for t in range(s):
            check()
            vector = tuple((F(re[i][j][t]), F(im[i][j][t])) for j in range(m))
            vectors[i, t] = vector
            gains[i, t] = sum(x*x+y*y for x, y in vector)
    data = {}
    require(isinstance(case['pairs'], list) and len(case['pairs']) == s*k*(k-1)//2, 'incomplete model')
    for row in case['pairs']:
        check()
        require(len(row['users']) == 2, 'pair shape')
        u, v = row['users']
        t = row['resource']
        require(all(integer(i) for i in (u, v, t)) and 0 <= u < v < k and 0 <= t < s, 'pair indices')
        key = u, v, t
        require(key not in data, 'duplicate pair')
        g, h = gains[u, t], gains[v, t]
        real = sum(x*z+y*w for (x, y), (z, w) in zip(vectors[u, t], vectors[v, t]))
        imag = sum(x*w-y*z for (x, y), (z, w) in zip(vectors[u, t], vectors[v, t]))
        r = (real*real+imag*imag)/(g*h) if g*h else F(0)
        require(0 <= r <= 1, 'channel correlation domain')
        require((g, h, r) == tuple(F(row[n]) for n in ('gain1', 'gain2', 'r')), 'channel scalar mismatch')
        data[key] = g, h, r
    return k, s, low, high, budget, data, gains


def rate_interval(coefficients, power1, power2):
    gain1, gain2, correlation = coefficients
    x, y = gain1*power1, gain2*power2
    d = log_enclosure(1+x+y+(1-correlation)*x*y)
    b = log_enclosure(1+x)
    c = log_enclosure(1+y)
    return 2*d[0]-b[1]-c[1], 2*d[1]-b[0]-c[0]


def check_schedule(rows, model):
    k, s, low, high, budget, data, _ = model
    require(isinstance(rows, list) and len(rows) == s, 'schedule row count')
    users, resources, rate_low, rate_high = set(), set(), F(0), F(0)
    for row in rows:
        require(set(row) == {'users', 'resource', 'powers'} and len(row['users']) == len(row['powers']) == 2,
                'schedule keys/shape')
        u, v = row['users']
        t = row['resource']
        require(all(integer(i) for i in (u, v, t)) and (u, v, t) in data, 'schedule indices')
        require(u not in users and v not in users and t not in resources, 'duplicate schedule incidence')
        users.update((u, v))
        resources.add(t)
        p, q = map(F, row['powers'])
        require(low <= p <= high and low <= q <= high, 'schedule power box')
        budget -= p+q
        l, h = rate_interval(data[u, v, t], p, q)
        rate_low += l
        rate_high += h
    require(len(users) == k and len(resources) == s and budget >= 0, 'schedule service/budget')
    return rate_low, rate_high


def curvature(r, xlo, xhi, ylo, yhi):
    """Independent implementation via u=1-ry/d and v=1-rx/d."""
    if 2*(1-r)**2 >= 1:
        return 'quadrant'
    def determinant_factor(x, y):
        return 1+x+y+(1-r)*x*y
    u_lower = 1-r*yhi/determinant_factor(xlo, yhi)
    v_lower = 1-r*xhi/determinant_factor(xhi, ylo)
    w_upper = min(r*(1+xhi)*(1+yhi)/determinant_factor(xlo, ylo)**2,
                  r*((1+xhi)*(1+yhi))**2/
                  ((1+xlo)*(1+ylo)*determinant_factor(xhi, yhi)**2))
    first, second = 2*u_lower**2-1, 2*v_lower**2-1
    if first >= 0 and second >= 0 and first*second >= 4*w_upper**2:
        return 'finite_box'
    return 'generic'


def leaf_price(coefficients, lam, lower, upper, point):
    g, h, r = coefficients
    xl, yl = g*lower[0], h*lower[1]
    xu, yu = g*upper[0], h*upper[1]
    x, y = g*point[0], h*point[1]
    d = 1+x+y+(1-r)*x*y
    kind = curvature(r, xl, xu, yl, yu)
    slopes = [2*(1+(1-r)*y)/d, 2*(1+(1-r)*x)/d]
    if kind != 'generic':
        slopes[0] -= 1/(1+x)
        slopes[1] -= 1/(1+y)
        constant = rate_interval(coefficients, *point)[1]-slopes[0]*x-slopes[1]*y
    else:
        constant = 2*log_enclosure(d)[1]-slopes[0]*x-slopes[1]*y
        for axis, a, b in ((0, xl, xu), (1, yl, yu)):
            endpoint_a = -log_enclosure(1+a)[0]
            secant_slope = F(0) if a == b else (-log_enclosure(1+b)[0]-endpoint_a)/(b-a)
            constant += endpoint_a-secant_slope*a
            slopes[axis] += secant_slope
    price_slopes = (g*slopes[0]-lam, h*slopes[1]-lam)
    affine = constant+sum(max(c*l, c*u) for c, l, u in zip(price_slopes, lower, upper))
    direct = sum((log_enclosure(1+xu*(1+(1-r)*yl)/(1+yl))[1],
                  log_enclosure(1+yu*(1+(1-r)*xl)/(1+xl))[1]))-lam*sum(lower)
    bound = min(affine, direct)*SCALE
    return -((-bound.numerator)//bound.denominator), kind


def partition(events, low, high, check):
    require(isinstance(events, list) and len(events) <= MAX_EVENTS, 'partition size')
    leaves = {'': ((low, low), (high, high))}
    for event in events:
        check()
        require(isinstance(event, list) and len(event) == 3, 'split shape')
        path, dim, text = event
        require(isinstance(path, str) and path in leaves, 'missing/duplicate split parent')
        require(integer(dim) and dim in (0, 1), 'split dimension')
        l, u = leaves.pop(path)
        cut = F(text)
        require(l[dim] < cut < u[dim], 'split domain')
        left_top, right_bottom = list(u), list(l)
        left_top[dim] = cut
        right_bottom[dim] = cut
        leaves[path+'0'] = l, tuple(left_top)
        leaves[path+'1'] = tuple(right_bottom), u
    return leaves


def integral_maximum(k, weights, check=lambda: None):
    """Independent top-down recurrence with Python integers, no NumPy/native DP."""
    calls = 0
    @lru_cache(maxsize=None)
    def solve(mask):
        nonlocal calls
        if mask == 0:
            return 0
        calls += 1
        if calls % 128 == 0:
            check()
        members = [i for i in range(k) if mask & (1 << i)]
        resource = len(members)//2-1
        return max(solve(mask ^ (1 << u) ^ (1 << v))+weights[u, v, resource]
                   for u, v in combinations(members, 2))
    result = solve((1 << k)-1)
    check()
    return result, solve.cache_info().currsize


def verify(case, witness, anchor, expected_binding, archived_duals=None, seconds=15.):
    began = time.perf_counter()
    check = deadline(seconds)
    log_enclosure.cache_clear()
    require(set(witness) == {'schema', 'case_sha256', 'binding', 'anchor_sha256', 'schedule',
                             'price', 'metrics', 'witness_sha256'}, 'witness keys')
    require(witness['schema'] == 'FINITE_BOX_INTEGRAL_V1', 'schema')
    unsealed = {k: v for k, v in witness.items() if k != 'witness_sha256'}
    require(object_hash(unsealed) == witness['witness_sha256'], 'witness hash mismatch')
    require(witness['case_sha256'] == object_hash(case), 'case hash mismatch')
    require(witness['binding'] == expected_binding, 'frozen binding mismatch')
    require(witness['anchor_sha256'] == object_hash(anchor), 'anchor hash mismatch')
    model = reconstruct(case, check)
    k, s, low, high, budget, data, gains = model
    anchor_rate = check_schedule(anchor, model)
    proposed_rate = check_schedule(witness['schedule'], model)
    lower = max(anchor_rate[0], proposed_rate[0])
    universal = sum(max(log_enclosure(1+gains[i, t]*high)[1] for t in range(s)) for i in range(k))
    upper = universal
    stats = dict(channels_reconstructed=True, price_rows=0, splits=0, leaves=0,
                 quadrant_roots=0, finite_box_only_roots=0, generic_roots=0,
                 dp_complete=False, fixed_alpha_upper_nats=None, integral_upper_nats=None)
    for g, h, r in data.values():
        check()
        kind = curvature(r, g*low, g*high, h*low, h*high)
        stats[{'quadrant': 'quadrant_roots', 'finite_box': 'finite_box_only_roots',
               'generic': 'generic_roots'}[kind]] += 1
    price = witness['price']
    if price is not None:
        require(set(price) == {'lambda_value', 'rounding_bits', 'rows', 'dp_units',
                               'dp_schedule', 'archived_alpha'}, 'price keys')
        lam = F(price['lambda_value'])
        require(lam >= 0 and integer(price['rounding_bits']) and price['rounding_bits'] == 40, 'price/rounding domain')
        require(isinstance(price['rows'], list) and len(price['rows']) == len(data), 'missing price rows')
        require(price['archived_alpha'] == (archived_duals or {}).get('alpha'), 'archived alpha binding')
        weights = {}
        for row in price['rows']:
            check()
            require(set(row) == {'users', 'resource', 'splits', 'leaves', 'upper_units'} and len(row['users']) == 2,
                    'price row keys')
            key = (*row['users'], row['resource'])
            require(all(integer(i) for i in key) and key in data and key not in weights, 'duplicate/invalid price row')
            boxes = partition(row['splits'], low, high, check)
            stats['splits'] += len(row['splits'])
            require(stats['splits'] <= MAX_EVENTS, 'total split limit')
            require(isinstance(row['leaves'], list) and len(row['leaves']) == len(boxes), 'missing leaf points')
            seen, values = set(), []
            for leaf in row['leaves']:
                check()
                require(set(leaf) == {'path', 'point'} and leaf['path'] in boxes and leaf['path'] not in seen,
                        'duplicate/missing leaf path')
                require(isinstance(leaf['point'], list) and len(leaf['point']) == 2, 'tangent shape')
                seen.add(leaf['path'])
                l, u = boxes[leaf['path']]
                c = tuple(map(F, leaf['point']))
                require(all(a <= p <= b for a, p, b in zip(l, c, u)), 'tangent outside leaf')
                value, kind = leaf_price(data[key], lam, l, u, c)
                values.append(value)
            require(seen == set(boxes), 'incomplete partition coverage')
            require(integer(row['upper_units']) and row['upper_units'] == max(values), 'price weight mismatch')
            weights[key] = max(values)
            stats['leaves'] += len(values)
        require(set(weights) == set(data), 'incomplete prices')
        dp_start = time.perf_counter()
        maximum, count = integral_maximum(k, weights, check)
        stats['dp_seconds'] = time.perf_counter()-dp_start
        require(integer(price['dp_units']) and maximum == price['dp_units'], 'DP maximum mismatch')
        pairs = price['dp_schedule']
        require(isinstance(pairs, list) and len(pairs) == s and
                all(isinstance(p, list) and len(p) == 2 and all(integer(i) for i in p) for p in pairs),
                'DP schedule shape')
        require(sorted(i for pair in pairs for i in pair) == list(range(k)) and
                all((*p, t) in weights for t, p in enumerate(pairs)), 'DP schedule incidence')
        require(sum(weights[(*pair, t)] for t, pair in enumerate(pairs)) == maximum, 'DP witness sum')
        integral_upper = lam*budget+F(maximum, SCALE)
        upper = min(upper, integral_upper)
        stats.update(dp_complete=True, dp_states=count, price_rows=len(weights),
                     integral_upper_nats=str(integral_upper))
        if price['archived_alpha'] is not None:
            alpha = list(map(F, price['archived_alpha']))
            require(len(alpha) == k, 'alpha size')
            relaxed = lam*budget+sum(alpha)+sum(max(F(w, SCALE)-alpha[u]-alpha[v]
                                                   for (u, v, t), w in weights.items() if t == resource)
                                                 for resource in range(s))
            require(relaxed >= integral_upper, 'integral/relaxation consistency')
            stats['fixed_alpha_upper_nats'] = str(relaxed)
    check()
    require(upper >= lower, 'upper below independently validated lower')
    return dict(valid=True, witness_sha256=witness['witness_sha256'], case_sha256=witness['case_sha256'],
                lower_nats=str(lower), upper_nats=str(upper), gap_nats=str(upper-lower),
                anchor_lower_nats=str(anchor_rate[0]), anchor_upper_nats=str(anchor_rate[1]),
                proposed_lower_nats=str(proposed_rate[0]), proposed_upper_nats=str(proposed_rate[1]),
                universal_upper_nats=str(universal), certificate_mathematical=upper-lower <= F(1, 100),
                metrics=stats, seconds=time.perf_counter()-began,
                arithmetic='exact rational coefficients; pinned outward integer log series; integer subset DP')
