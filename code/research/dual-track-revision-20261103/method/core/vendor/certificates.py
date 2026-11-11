"""Proof-producing MMSE bounds. No experiments or file writes on import.

Pricing is generic rectangular subdivision, NOT the seventeen-candidate oracle.
Producer numerical enclosures are advisory; use verify_upper.verify's bounds.
"""
from fractions import Fraction as F
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
from functools import lru_cache
from itertools import combinations
import hashlib
import heapq
import json
import math
import time

SCHEMA = 'MMSE_PARTITION_PROOF_V1'
MAX_SPLITS = 1200
MAX_ROOTS = 3000


def clear_caches():
    log_bounds.cache_clear()
    pair_majorant.cache_clear()


def case_digest(case):
    return hashlib.sha256(json.dumps(case, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def universal_proof(case):
    return dict(schema=SCHEMA, case_sha256=case_digest(case), universal=True,
                dual=None, spatial=None)


@lru_cache(maxsize=40000)
def log_bounds(x):
    x = F(x)
    if x <= 0:
        raise ValueError('log domain')
    if x == 1:
        return F(0), F(0)
    with localcontext() as c:
        c.prec = 55
        c.rounding = ROUND_FLOOR
        a = Decimal(x.numerator) / Decimal(x.denominator)
        c.rounding = ROUND_CEILING
        b = Decimal(x.numerator) / Decimal(x.denominator)
        low, high = F(a.ln().next_minus()), F(b.ln().next_plus())
    # Keep proof-search fractions compact without losing outward enclosure.
    scale = 1 << 100
    return F((low * scale).__floor__(), scale), F((high * scale).__ceil__(), scale)


def rate(g, h, r, p, q):
    x, y = g*p, h*q
    dl, du = log_bounds(1+x+y+(1-r)*x*y)
    al, au = log_bounds(1+x)
    bl, bu = log_bounds(1+y)
    return 2*dl-au-bu, 2*du-al-bl


@lru_cache(maxsize=40000)
def pair_majorant(g, h, r, pl, ph, ql, qh, pc, qc, curvature):
    a = 1-r
    xl, xh, yl, yh, x, y = g*pl, g*ph, h*ql, h*qh, g*pc, h*qc
    d = 1+x+y+a*x*y
    tx, ty = 2*(1+a*y)/d, 2*(1+a*x)/d
    if curvature and 2*a*a >= 1:
        dx, dy = tx-1/(1+x), ty-1/(1+y)
        constant = rate(g, h, r, pc, qc)[1]-dx*x-dy*y
    else:
        def secant(l, u):
            fl = -log_bounds(1+l)[0]
            if l == u:
                return F(0), fl
            fu = -log_bounds(1+u)[0]
            slope = (fu-fl)/(u-l)
            return slope, fl-slope*l
        sx, bx = secant(xl, xh)
        sy, by = secant(yl, yh)
        dx, dy = tx+sx, ty+sy
        constant = 2*log_bounds(d)[1]-tx*x-ty*y+bx+by
    mixed = (log_bounds(1+xh*(1+a*yl)/(1+yl))[1]
             + log_bounds(1+yh*(1+a*xl)/(1+xl))[1])
    return dx*g, dy*h, constant, mixed


def assignments(k):
    def visit(left, prefix):
        if not left:
            yield tuple(prefix)
        else:
            for u, v in combinations(left, 2):
                yield from visit(tuple(i for i in left if i != u and i != v),
                                 prefix+[(u, v)])
    yield from visit(tuple(range(k)), [])


class Model:
    def __init__(self, case):
        self.k, self.s = int(case['K']), int(case['S'])
        self.low, self.high, self.budget = map(F, (case['pmin'], case['pmax'], case['budget']))
        if self.k != 2*self.s or self.k < 2 or not 0 <= self.low <= self.high or self.k*self.low > self.budget:
            raise ValueError('infeasible model')
        self.data, self.gains = {}, {}
        for row in case['pairs']:
            u, v = row['users']; s = row['resource']
            g, h, r = map(F, (row['gain1'], row['gain2'], row['r']))
            key = (u, v, s)
            if not (0 <= u < v < self.k and 0 <= s < self.s and g >= 0 and h >= 0 and 0 <= r <= 1):
                raise ValueError('pair domain')
            if key in self.data or ((g == 0 or h == 0) and r != 0):
                raise ValueError('duplicate pair or zero gain convention')
            for i, z in ((u, g), (v, h)):
                if (i, s) in self.gains and self.gains[i, s] != z:
                    raise ValueError('inconsistent user gain')
                self.gains[i, s] = z
            self.data[key] = (g, h, r)
        if len(self.data) != self.s*self.k*(self.k-1)//2:
            raise ValueError('missing pair')
        self.ceiling = sum(max(log_bounds(1+self.gains[i, s]*self.high)[1]
                               for s in range(self.s)) for i in range(self.k))

    def decode(self, rows):
        if len(rows) != self.s:
            raise ValueError('schedule size')
        pairs, powers = [None]*self.s, [None]*self.k
        for row in rows:
            u, v = row['users']; s = row['resource']
            p, q = map(F, row['powers'])
            if not (0 <= u < v < self.k and 0 <= s < self.s):
                raise ValueError('schedule index')
            if pairs[s] is not None or powers[u] is not None or powers[v] is not None:
                raise ValueError('schedule incidence')
            pairs[s], powers[u], powers[v] = (u, v), p, q
        if any(x is None or not self.low <= x <= self.high for x in powers) or sum(powers) > self.budget:
            raise ValueError('schedule powers')
        return tuple(pairs), tuple(powers)

    def encode(self, pairs, powers):
        return [dict(users=list(pair), resource=s, powers=[str(powers[i]) for i in pair])
                for s, pair in enumerate(pairs)]

    def value(self, pairs, powers):
        bounds = [rate(*self.data[u, v, s], powers[u], powers[v])
                  for s, (u, v) in enumerate(pairs)]
        return sum(x[0] for x in bounds), sum(x[1] for x in bounds)

    def spatial_bound(self, pairs, lo, hi, curvature):
        if sum(lo) > self.budget:
            return None
        hi = tuple(min(h, self.budget-sum(lo)+l) for l, h in zip(lo, hi))
        width = sum(h-l for l, h in zip(lo, hi))
        theta = min(F(1, 2), (self.budget-sum(lo))/width) if width else F(0)
        center = tuple(l+theta*(h-l) for l, h in zip(lo, hi))
        coeff, const, mixed = [F(0)]*self.k, F(0), F(0)
        for s, (u, v) in enumerate(pairs):
            ax, ay, c, m = pair_majorant(*self.data[u, v, s], lo[u], hi[u], lo[v], hi[v],
                                        center[u], center[v], curvature)
            coeff[u], coeff[v] = ax, ay
            const += c; mixed += m
        affine, remaining = const+sum(c*l for c, l in zip(coeff, lo)), self.budget-sum(lo)
        for i in sorted(range(self.k), key=lambda i: coeff[i], reverse=True):
            if coeff[i] <= 0 or remaining <= 0:
                break
            delta = min(hi[i]-lo[i], remaining)
            affine += coeff[i]*delta; remaining -= delta
        return min(affine, mixed), center


def _pricing_bound(params, lo, hi):
    g, h, r, lam = params
    mid = tuple((a+b)/2 for a, b in zip(lo, hi))
    ax, ay, c, mixed = pair_majorant(g, h, r, lo[0], hi[0], lo[1], hi[1], *mid, True)
    coeff = (ax-lam, ay-lam)
    upper = min(c+sum(z*(b if z >= 0 else a) for z, a, b in zip(coeff, lo, hi)),
                mixed-lam*sum(lo))
    lower = rate(g, h, r, *mid)[0]-lam*sum(mid)
    return lower, upper


class PriceTree:
    def __init__(self, params, low, high):
        self.params = params
        self.events, self.leaves, self.heap = [], {}, []
        self.lower = None
        self._add('', (low, low), (high, high))

    def _add(self, path, lo, hi):
        lower, upper = _pricing_bound(self.params, lo, hi)
        self.lower = lower if self.lower is None else max(lower, self.lower)
        self.leaves[path] = (lo, hi, upper)
        heapq.heappush(self.heap, (-upper, path))

    @property
    def upper(self):
        return -self.heap[0][0]

    def split(self):
        _, path = heapq.heappop(self.heap)
        lo, hi, upper = self.leaves[path]
        dim = max(range(2), key=lambda i: hi[i]-lo[i])
        if lo[dim] == hi[dim]:
            heapq.heappush(self.heap, (-upper, path)); return False
        cut = (lo[dim]+hi[dim])/2
        a, b = list(hi), list(lo); a[dim], b[dim] = cut, cut
        # Commit an entire partition, never a half split.
        del self.leaves[path]
        self._add(path+'0', lo, tuple(a)); self._add(path+'1', tuple(b), hi)
        self.events.append([path, dim, str(cut)])
        return True


def price_pair(g1, g2, r, lam, lo, hi, seconds=1., max_splits=256, tolerance='1/10000000'):
    """Diagnostic generic rectangle proof. Verify with verify_upper.verify_pair."""
    start = time.perf_counter(); stop = start+max(0, seconds)
    g1, g2, r, lam, lo, hi = map(F, (g1, g2, r, lam, lo, hi))
    if min(g1, g2, lam, lo) < 0 or not (0 <= r <= 1 and lo <= hi) or ((g1 == 0 or g2 == 0) and r):
        raise ValueError('pricing input')
    tree = PriceTree((g1, g2, r, lam), lo, hi)
    while time.perf_counter() < stop and len(tree.events) < min(max_splits, MAX_SPLITS):
        if tree.upper-tree.lower <= F(tolerance) or not tree.split():
            break
    return dict(proof=dict(schema='PAIR_PARTITION_V1', inputs=list(map(str, (g1, g2, r, lam, lo, hi))),
                           splits=tree.events), lower_nats=str(tree.lower), upper_nats=str(tree.upper),
                metrics=dict(splits=len(tree.events), seconds=time.perf_counter()-start),
                method='verified generic rectangle subdivision; no finite-candidate speedup claim')


def run(case, mode, initial=None, grid_duals=None, seconds=10., progress=None):
    """Return serializable candidate/proof; callbacks are synchronous and charged.

    Modes: universal, curvature, reference, full, grid_repair. Full allocates at
    most one quarter of its supplied time to generic pricing before spatial work.
    Spatial proof is capped at 3000 roots/1200 splits; larger families retain
    an explicit universal cover for all omitted assignments.
    """
    mode = {'ceiling': 'universal', 'pricing': 'grid_repair'}.get(mode, mode)
    if mode not in ('universal', 'curvature', 'reference', 'full', 'grid_repair'):
        raise ValueError('unknown mode')
    began = time.perf_counter(); stop = began+max(0., float(seconds))
    p = Model(case)
    pairs = next(assignments(p.k)); powers = (min(p.high, p.budget/p.k),)*p.k
    if initial is not None:
        alt, power_alt = p.decode(initial)
        if p.value(alt, power_alt)[0] > p.value(pairs, powers)[0]:
            pairs, powers = alt, power_alt
    best = p.value(pairs, powers)[0]
    proof = universal_proof(case)
    metrics = dict(pricing_method='generic_partition', priced_pairs=0, total_pairs=len(p.data),
                   pricing_splits=0, spatial_roots=0, spatial_splits=0,
                   assignments_total=math.factorial(p.k)//2**p.s)
    last_callback = began
    def result(status='BUDGET_OR_METHOD_RETURNED'):
        return dict(schedule=p.encode(pairs, powers), proof=proof, metrics=dict(metrics, seconds=time.perf_counter()-began),
                    status=status, producer_lower_nats=str(best))
    def notify():
        nonlocal last_callback
        if progress and time.perf_counter()-last_callback >= 1 and time.perf_counter() < stop:
            progress(result('PROGRESS')); last_callback = time.perf_counter()

    if mode in ('full', 'grid_repair') and grid_duals is not None and time.perf_counter() < stop:
        alpha = tuple(map(F, grid_duals['alpha']))
        lam = F(grid_duals.get('lambda', grid_duals.get('lambda_value')))
        if len(alpha) != p.k or lam < 0:
            raise ValueError('dual domain')
        price_stop = stop if mode == 'grid_repair' else min(stop, began+max(0., float(seconds))*.25)
        trees, rows = {}, []
        for key in sorted(p.data):
            if time.perf_counter() >= price_stop:
                break
            tree = PriceTree((*p.data[key], lam), p.low, p.high)
            trees[key] = tree
            rows.append(dict(users=list(key[:2]), resource=key[2], splits=tree.events))
            metrics['priced_pairs'] += 1
        if len(trees) == len(p.data):
            proof['dual'] = dict(alpha=list(map(str, alpha)), lambda_value=str(lam), rows=rows)
            # Refine the rectangle with the largest unresolved pricing gap.
            heap = [(-(t.upper-t.lower), key) for key, t in trees.items()]
            heapq.heapify(heap)
            while heap and time.perf_counter() < price_stop and metrics['pricing_splits'] < MAX_SPLITS:
                neg, key = heapq.heappop(heap); t = trees[key]
                if -neg <= F(1, 10**7): break
                if t.split():
                    metrics['pricing_splits'] += 1
                    heapq.heappush(heap, (-(t.upper-t.lower), key))
                notify()
        else:
            metrics['pricing_status'] = 'INCOMPLETE_FAMILY_UNIVERSAL_RETAINED'
    if mode in ('reference', 'curvature', 'full') and time.perf_counter() < stop:
        roots, leaf_boxes, heap = [], {}, []
        proof['spatial'] = dict(curvature=mode != 'reference', roots=roots, unlisted='universal')
        lo, hi = (p.low,)*p.k, (p.high,)*p.k
        def add(root_id, schedule, path, l, h, observe=False):
            nonlocal best, pairs, powers
            bound = p.spatial_bound(schedule, l, h, mode != 'reference')
            leaf_boxes[root_id, path] = (l, h)
            if bound is not None:
                upper, center = bound
                if observe:
                    val = p.value(schedule, center)[0]
                    if val > best:
                        best, pairs, powers = val, schedule, center
                if upper > best:
                    heapq.heappush(heap, (-upper, root_id, path, schedule))
        for schedule in assignments(p.k):
            if time.perf_counter() >= stop or len(roots) >= MAX_ROOTS:
                break
            idx = len(roots)
            add(idx, schedule, '', lo, hi)
            roots.append(dict(pairs=[list(x) for x in schedule], splits=[]))
            metrics['spatial_roots'] += 1
            notify()
        # Refinement cannot improve the universal cover until all roots exist.
        if len(roots) == metrics['assignments_total']:
            while heap and time.perf_counter() < stop and metrics['spatial_splits'] < MAX_SPLITS:
                neg, idx, path, schedule = heapq.heappop(heap)
                if -neg <= best: continue
                l, h = leaf_boxes[idx, path]
                dim = max(range(p.k), key=lambda i: h[i]-l[i])
                if h[dim] == l[dim]: continue
                cut = (l[dim]+h[dim])/2
                left, right = list(h), list(l); left[dim], right[dim] = cut, cut
                add(idx, schedule, path+'0', l, tuple(left), True)
                add(idx, schedule, path+'1', tuple(right), h, True)
                del leaf_boxes[idx, path]
                roots[idx]['splits'].append([path, dim, str(cut)])
                metrics['spatial_splits'] += 1
                notify()
    metrics['pricing_split_limit_reached'] = metrics['pricing_splits'] >= MAX_SPLITS
    metrics['spatial_split_limit_reached'] = metrics['spatial_splits'] >= MAX_SPLITS
    metrics['spatial_root_limit_reached'] = metrics['spatial_roots'] >= MAX_ROOTS and metrics['spatial_roots'] < metrics['assignments_total']
    return result()
