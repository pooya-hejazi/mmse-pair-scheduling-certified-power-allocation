"""Mathematical, coverage, provenance, and replay tests before protocol freeze."""
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations, permutations, product
from pathlib import Path
import contextlib
import decimal
import hashlib
import io
import json
import random
import time
import unittest
import sympy as sp
import checker
import producer
from integer_logs import log_enclosure
from source_data import ARCHIVE, HERE, FrozenArchive, save


def synthetic(k=4, seed=19, zero=False):
    rng = random.Random(seed)
    m, s = 3, k//2
    re = [[[float(F(rng.randint(-5, 7), 4)) for _ in range(s)] for _ in range(m)] for _ in range(k)]
    im = [[[float(F(rng.randint(-3, 3), 4)) for _ in range(s)] for _ in range(m)] for _ in range(k)]
    if zero:
        re[0] = [[0.]*s for _ in range(m)]
        im[0] = [[0.]*s for _ in range(m)]
    vectors = {(i, t): [(F(re[i][j][t]), F(im[i][j][t])) for j in range(m)]
               for i in range(k) for t in range(s)}
    gains = {key: sum(a*a+b*b for a, b in val) for key, val in vectors.items()}
    pairs = []
    for u, v in combinations(range(k), 2):
        for t in range(s):
            real = sum(a*c+b*d for (a, b), (c, d) in zip(vectors[u, t], vectors[v, t]))
            imag = sum(a*d-b*c for (a, b), (c, d) in zip(vectors[u, t], vectors[v, t]))
            g, h = gains[u, t], gains[v, t]
            r = (real*real+imag*imag)/(g*h) if g*h else F(0)
            pairs.append(dict(users=[u, v], resource=t, gain1=str(g), gain2=str(h), r=str(r)))
    case = dict(name=f'synthetic-nonorthogonal-{k}-{seed}', K=k, S=s, M=m,
                pmin='1/20', pmax='1/5', budget=str(F(k, 10)), pairs=pairs,
                channels_re=re, channels_im=im)
    anchor = [dict(users=[2*t, 2*t+1], resource=t, powers=['1/10', '1/10']) for t in range(s)]
    return case, anchor


def reseal(w):
    w.pop('witness_sha256', None)
    return producer.seal(w)


class MathematicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case, cls.anchor = synthetic()
        cls.witness = producer.run(cls.case, cls.anchor, {'synthetic': True}, seconds=1.)

    def test_hessian_and_monotonicity_exact_symbolic(self):
        x, y, r = sp.symbols('x y r', nonnegative=True)
        a = 1-r
        d = 1+x+y+a*x*y
        q = 2*sp.log(d)-sp.log(1+x)-sp.log(1+y)
        u, v, w = (1+x)*(1+a*y)/d, (1+y)*(1+a*x)/d, r*(1+x)*(1+y)/d**2
        for expr in (sp.diff(q, x, x)*(1+x)**2-(1-2*u*u),
                     sp.diff(q, y, y)*(1+y)**2-(1-2*v*v),
                     sp.diff(q, x, y)*(1+x)*(1+y)+2*w,
                     sp.diff(u, x)-r*y*(1+a*y)/d**2,
                     sp.diff(u, y)+r*(1+x)/d**2):
            self.assertEqual(sp.factor(expr), 0)
        polynomial = (a*a*x*x*y*y+2*a*x*x*y+x*x+2*a*(2*a-1)*x*y*y+
                      4*(2*a-1)*x*y+2*a*x+(2*a*a-1)*y*y+2*(3*a-2)*y+2*a-1)
        self.assertEqual(sp.factor(d*d*(2*u*u-1-2*w)-polynomial), 0)

    def test_above_threshold_and_endpoints(self):
        self.assertLess(2*(1-F(3, 4))**2, 1)
        self.assertEqual(producer.concavity(F(3, 4), F(100), F(400), F(100), F(400)), 'finite_box')
        self.assertEqual(checker.curvature(F(3, 4), F(100), F(400), F(100), F(400)), 'finite_box')
        self.assertEqual(checker.curvature(F(1), F(0), F(1), F(0), F(1)), 'generic')
        self.assertEqual(checker.curvature(F(0), F(0), F(0), F(0), F(10)), 'quadrant')
        self.assertEqual(checker.curvature(F(4, 5), F(10), F(20), F(10), F(20)), 'finite_box')
        self.assertEqual(checker.curvature(F(1, 4), F(0), F(1), F(0), F(1)), 'quadrant')
        for r in (F(0), F(1, 3), F(3, 4), F(1)):
            for l, h in ((F(0), F(1)), (F(100), F(400)), (F(1), F(1))):
                reason = checker.curvature(r, l, h, l, h)
                self.assertEqual(reason, producer.concavity(r, l, h, l, h))
                if reason != 'generic':
                    for x, y in product((l, (l+h)/2, h), repeat=2):
                        a, d = 1-r, 1+x+y+(1-r)*x*y
                        xx = 1/(1+x)**2-2*(1+a*y)**2/d**2
                        yy = 1/(1+y)**2-2*(1+a*x)**2/d**2
                        xy = -2*r/d**2
                        self.assertLessEqual(xx, 0)
                        self.assertLessEqual(yy, 0)
                        self.assertGreaterEqual(xx*yy-xy*xy, 0)

    def test_log_enclosures_independent_decimal(self):
        with decimal.localcontext() as ctx:
            ctx.prec = 110
            for x in (F(1), F(1, 1000000), F(2), F(7, 3), F(2)**100, F(10)**-30):
                truth = (decimal.Decimal(x.numerator)/decimal.Decimal(x.denominator)).ln()
                low, high = log_enclosure(x)
                self.assertLessEqual(decimal.Decimal(low.numerator)/decimal.Decimal(low.denominator), truth)
                self.assertGreaterEqual(decimal.Decimal(high.numerator)/decimal.Decimal(high.denominator), truth)

    def test_integer_dp_vs_enumeration_k4_k8(self):
        rng = random.Random(4901)
        for k in (4, 8):
            weights = {(u, v, t): rng.randint(-100, 100)*(1 << 90)+rng.randrange(100)
                       for u, v in combinations(range(k), 2) for t in range(k//2)}
            enumerated = max(sum(weights[p[2*t], p[2*t+1], t] for t in range(k//2))
                             for p in permutations(range(k))
                             if all(p[2*t] < p[2*t+1] for t in range(k//2)))
            produced, schedule = producer.integral_dp(k, weights)
            checked, _ = checker.integral_maximum(k, weights)
            self.assertEqual(enumerated, produced)
            self.assertEqual(enumerated, checked)
            self.assertEqual(sum(weights[(*pair, t)] for t, pair in enumerate(schedule)), enumerated)

    def test_labelled_resources_do_not_force_smallest_user(self):
        weights = {(u, v, t): 0 for u, v in combinations(range(4), 2) for t in range(2)}
        weights[2, 3, 0] = weights[0, 1, 1] = 10
        self.assertEqual(producer.integral_dp(4, weights)[0], 20)
        self.assertEqual(checker.integral_maximum(4, weights)[0], 20)

    def test_signed_ceiling_and_rounding_slack(self):
        self.assertEqual(producer.ceil_units(F(-3, 2*producer.SCALE)), -1)
        self.assertEqual(producer.ceil_units(F(-1, 2*producer.SCALE)), 0)
        self.assertEqual(producer.ceil_units(F(1, 2*producer.SCALE)), 1)
        weights = {(u, v, t): F((u+1)*(v+2)-20+t, 37)
                   for u, v in combinations(range(4), 2) for t in range(2)}
        exact = max(sum(weights[p[2*t], p[2*t+1], t] for t in range(2))
                    for p in permutations(range(4)) if p[0] < p[1] and p[2] < p[3])
        rounded = {key: producer.ceil_units(v) for key, v in weights.items()}
        value = F(checker.integral_maximum(4, rounded)[0], producer.SCALE)
        self.assertGreaterEqual(value, exact)
        self.assertLess(value-exact, F(2, producer.SCALE))
        budget_term = F(7, 11)
        fully_rounded = value+F(producer.ceil_units(budget_term), producer.SCALE)
        self.assertLess(fully_rounded-(exact+budget_term), F(3, producer.SCALE))

    def test_cancellation_safe_r_one_and_zero_gain_physical_price(self):
        r, x, y = F(1), F(10)**200, F(10)**250
        d = 1+x+y
        w2 = r*((1+x)*(1+y))**2/d**2
        delta = 1-r*x/(1+x)*y/(1+y)
        self.assertGreater(delta, 0)
        self.assertEqual(w2, r/delta**2)
        self.assertEqual(checker.curvature(r, F(0), x, F(0), y), 'generic')
        data, lam = (F(0), F(0), F(0)), F(7, 3)
        lo, hi, point = (F(1, 20),)*2, (F(1, 5),)*2, (F(1, 10),)*2
        expected = producer.ceil_units(-lam*sum(lo))
        self.assertEqual(producer.leaf_bound(data, lam, lo, hi, point)[0], expected)
        self.assertEqual(checker.leaf_price(data, lam, lo, hi, point)[0], expected)

    def test_exact_power_budget_duality_gap_counterexample(self):
        excess = F(9, 4)**4*F(8, 3)-F(128, 55)**5
        self.assertEqual(excess, F(1171300349, 16105100000))
        self.assertGreater(excess, 0)
        mix_lower = F(4, 5)*log_enclosure(F(9, 4))[0]+F(1, 5)*log_enclosure(F(8, 3))[0]
        feasible_upper = log_enclosure(F(128, 55))[1]
        self.assertGreater(mix_lower, feasible_upper)

    def test_certified_upper_covers_independently_checked_schedules(self):
        result = checker.verify(self.case, self.witness, self.anchor, {'synthetic': True})
        self.assertIsNotNone(self.witness['price'])
        model = checker.reconstruct(self.case)
        upper = F(result['upper_nats'])
        count = 0
        for p in permutations(range(4)):
            if any(p[2*t] > p[2*t+1] for t in range(2)):
                continue
            for power in product((F(1, 20), F(1, 10), F(1, 5)), repeat=4):
                if sum(power) > F(2, 5):
                    continue
                schedule = [dict(users=[p[2*t], p[2*t+1]], resource=t,
                                 powers=[str(power[p[2*t]]), str(power[p[2*t+1]])]) for t in range(2)]
                self.assertGreaterEqual(upper, checker.check_schedule(schedule, model)[1])
                count += 1
        self.assertGreater(count, 100)
        self.assertGreaterEqual(F(result['lower_nats']), F(result['anchor_lower_nats']))

    def test_missing_duplicate_price_rows_rejected_after_rehash(self):
        for edit in ('missing', 'duplicate'):
            w = deepcopy(self.witness)
            if edit == 'missing':
                w['price']['rows'].pop()
            else:
                w['price']['rows'][-1] = deepcopy(w['price']['rows'][0])
            with self.assertRaises(ValueError):
                checker.verify(self.case, reseal(w), self.anchor, {'synthetic': True})

    def test_tampered_weights_points_dp_and_hash_rejected(self):
        edits = [lambda w: w['price']['rows'][0].__setitem__('upper_units', 0),
                 lambda w: w['price'].__setitem__('dp_units', w['price']['dp_units']+1),
                 lambda w: w['price']['rows'][0]['leaves'][0].__setitem__('point', ['99', '99']),
                 lambda w: w['price']['rows'][0]['leaves'].pop(),
                 lambda w: w.__setitem__('binding', {'synthetic': False})]
        for edit in edits:
            w = deepcopy(self.witness)
            edit(w)
            with self.assertRaises(ValueError):
                checker.verify(self.case, reseal(w), self.anchor, {'synthetic': True})
        w = deepcopy(self.witness)
        w['metrics']['seconds'] += 1
        with self.assertRaisesRegex(ValueError, 'hash'):
            checker.verify(self.case, w, self.anchor, {'synthetic': True})

    def test_partition_omission_duplicate_and_outside_split(self):
        valid = [['', 0, '1/8'], ['0', 1, '1/10']]
        leaves = checker.partition(valid, F(1, 20), F(1, 5), lambda: None)
        self.assertEqual(set(leaves), {'00', '01', '1'})
        for bad in ([['00', 0, '1/10']], [['', 0, '1/8'], ['', 1, '1/8']], [['', 1, '9']]):
            with self.assertRaises(ValueError):
                checker.partition(bad, F(1, 20), F(1, 5), lambda: None)

    def test_zero_gain_and_r_one_full_domain(self):
        case, anchor = synthetic(zero=True)
        witness = producer.run(case, anchor, {'synthetic': True}, seconds=.7)
        self.assertTrue(checker.verify(case, witness, anchor, {'synthetic': True})['valid'])
        data = (F(2), F(3), F(1))
        lo, hi, point = (F(0), F(0)), (F(1), F(1)), (F(1, 2), F(1, 2))
        ub, reason = checker.leaf_price(data, F(2, 3), lo, hi, point)
        for p, q in product([F(i, 10) for i in range(11)], repeat=2):
            self.assertGreaterEqual(F(ub, checker.SCALE), checker.rate_interval(data, p, q)[1]-F(2, 3)*(p+q))

    def test_exact_channel_reconstruction_rejects_scalar_change(self):
        case = deepcopy(self.case)
        case['pairs'][0]['gain1'] = '0'
        with self.assertRaisesRegex(ValueError, 'scalar'):
            checker.reconstruct(case)

    def test_archive_binding_and_serialized_output_replay(self):
        source = FrozenArchive()
        item = source.load('o1-main-00', 'original')
        source.extract(item, 'original')
        archive = checker.ArchivedInputs(ARCHIVE)
        case, anchor, dual = archive.load(item['binding'])
        self.assertEqual(case, item['case'])
        witness = producer.run(case, anchor, item['binding'], dual, seconds=2.)
        path = HERE/'development'/'test-archive-witness.json'
        save(path, witness)
        restored = json.loads(path.read_text())
        result = checker.verify(case, restored, anchor, item['binding'], dual)
        self.assertTrue(result['valid'])
        bad = deepcopy(item['binding'])
        bad['case_file_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'hash'):
            archive.load(bad)
        altered = deepcopy(case)
        altered['channels_re'][0][0][0] += 1
        with self.assertRaisesRegex(ValueError, 'hash'):
            checker.verify(altered, restored, anchor, item['binding'], dual)


if __name__ == '__main__':
    began = time.perf_counter()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(MathematicalTests))
    text = stream.getvalue()
    print(text)
    save(HERE/'development'/'tests-result.json', dict(passed=result.wasSuccessful(), tests=result.testsRun,
         failures=len(result.failures), errors=len(result.errors), seconds=time.perf_counter()-began, log=text,
         tested_sources={n: hashlib.sha256((HERE/n).read_bytes()).hexdigest()
                         for n in ('producer.py', 'checker.py', 'integer_logs.py', 'tests.py', 'source_data.py')}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
