"""Bounded common-DP comparison; see frozen PROTOCOL.md. No original files changed."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import sys
sys.dont_write_bytecode = True
import argparse, csv, hashlib, itertools, json, math, platform, time
from fractions import Fraction as F
from pathlib import Path
import numpy as np
import scipy
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
METHOD = ROOT / 'research/dual-track-revision-20261103/method'
CERT = ROOT / 'research/manuscript-refinement-20261106/certification'
sys.path[:0] = [str(METHOD), str(CERT)]
from core.problem import Problem, certificates
from modern import fu_sca, thu_ide
from modern.common import DeadlineReached, guard
import producer
ARMS = ('DP-SQP', 'DP-Fu-SCA', 'DP-Thu-IDE')
SEPARATIONS = (0.5, 2, 6, 12)
SEEDS = (2026110901, 2026110902)
CAP, BLOCK = 10., 2.

def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dp_assignment(k, data, powers, deadline):
    # shortcut: exponential subset DP is restricted to K<=20; use a scalable assignment solver above it.
    if k > 20 or k < 2 or k % 2:
        raise ValueError('bounded exact-assignment wrapper requires even 2<=K<=20')
    guard(deadline)
    weights = {}
    for (u, v, s), (g, h, r) in data.items():
        x, y = g*float(powers[u]), h*float(powers[v])
        weights[u, v, s] = 2*math.log(1+x+y+(1-r)*x*y)-math.log1p(x)-math.log1p(y)
    n = 1 << k
    values, previous = [-math.inf]*n, [None]*n
    values[0] = 0.
    for mask in range(1, n):
        if mask % 256 == 0:
            guard(deadline)
        bits = mask.bit_count()
        if bits % 2:
            continue
        s, rem = bits//2-1, mask
        best, chosen = -math.inf, None
        while rem:
            ub = rem & -rem
            rem -= ub
            u = ub.bit_length()-1
            tail = rem
            while tail:
                vb = tail & -tail
                tail -= vb
                v = vb.bit_length()-1
                val = values[mask ^ ub ^ vb] + weights[u, v, s]
                if val > best:
                    best, chosen = val, (u, v)
        values[mask], previous[mask] = best, chosen
    guard(deadline)
    pairs, mask = [None]*(k//2), n-1
    for s in reversed(range(k//2)):
        u, v = previous[mask]
        pairs[s] = (u, v)
        mask ^= (1 << u) | (1 << v)
    return tuple(pairs), values[-1]

def starts_for(problem):
    rng = np.random.default_rng(20261109)
    result = [(tuple((2*s, 2*s+1) for s in range(problem.s)),
               problem.repair([problem.budget/problem.k]*problem.k))]
    for _ in range(7):
        perm = list(map(int, rng.permutation(problem.k)))
        pairs = tuple(tuple(sorted(perm[2*s:2*s+2])) for s in range(problem.s))
        p = problem.repair(float(problem.low)+rng.random(problem.k)*float(problem.high-problem.low))
        result.append((pairs, p))
    for a, p in result:
        problem.model.decode(problem.model.encode(a, p))
    return result

def solve(problem, starts, arm):
    certificates.clear_caches()
    rng = np.random.default_rng(20261110)
    problem.common_power_starts = [np.asarray(p, float) for _, p in starts]
    begun = time.monotonic()
    deadline = begun+CAP
    fallback = problem.checked_candidate(*starts[0])
    best = fallback
    history, diagnostics = [], []
    counts = dict(starts_started=0, starts_completed=0, dp_completed=0, power_calls=0, accepted=0)
    reason = 'starts_exhausted'
    def retain(a, p, diagnostic=None):
        nonlocal best
        guard(deadline)
        candidate = problem.checked_candidate(a, p)
        problem.matrix_scalar_check(candidate)
        guard(deadline)
        if problem.improves(candidate, best):
            best = candidate
            counts['accepted'] += 1
            history.append(dict(seconds=time.monotonic()-begun, rate_nats=best['value']))
        return candidate
    try:
        for a, p in starts:
            guard(deadline)
            counts['starts_started'] += 1
            current = retain(a, p)
            for step in range(8):
                guard(deadline)
                before = current
                a, dp_value = dp_assignment(problem.k, problem.lookup, current['powers'], deadline)
                counts['dp_completed'] += 1
                current = retain(a, current['powers'])
                assert abs(current['value']-dp_value) < 1e-7
                block_deadline = min(deadline, time.monotonic()+BLOCK)
                counts['power_calls'] += 1
                if arm == 'DP-SQP':
                    # Existing SQP expects perf_counter, whereas common refiners use monotonic.
                    sqp_deadline = time.perf_counter()+max(0., block_deadline-time.monotonic())
                    pp, d = producer.refine(a, current['powers'], problem.model.data,
                                           problem.low, problem.high, problem.budget, sqp_deadline)
                    d['method'] = 'LOCAL_SQP'
                else:
                    refiner = fu_sca.refine_power if arm == 'DP-Fu-SCA' else thu_ide.refine_power
                    pp, d = refiner(problem, a, current['numeric'], block_deadline, rng, retain)
                diagnostics.append(d)
                candidate = retain(a, pp)
                if problem.improves(candidate, current):
                    current = candidate
                if (current['assignment'] == before['assignment'] and
                    abs(current['value']-before['value']) <= 1e-9*max(1., abs(before['value']))):
                    break
            counts['starts_completed'] += 1
    except DeadlineReached:
        reason = 'deadline'
    elapsed = time.monotonic()-begun
    audit_start = time.monotonic()
    # Decode rejects any unrepaired violation; matrix path is independent of scalar arithmetic.
    a, p = problem.model.decode(best['schedule'])
    assert min(p) >= problem.low and max(p) <= problem.high and sum(p) <= problem.budget
    audit = problem.matrix_scalar_check(best)
    assert math.isfinite(best['value']) and best['value'] >= fallback['value']-1e-8
    assert all(item['seconds'] <= CAP for item in history)
    return dict(arm=arm, rate_nats=best['value'], se_bits=best['value']/(problem.s*math.log(2)),
                aggregate_bits=best['value']/math.log(2),
                elapsed_seconds=elapsed, cap_seconds=CAP, overrun_seconds=max(0., elapsed-CAP),
                audit_seconds=time.monotonic()-audit_start, status=reason, counts=counts,
                schedule=best['schedule'], audit=audit, total_power=str(sum(p)),
                history=history, diagnostics=diagnostics)

def self_check():
    rng = np.random.default_rng(4)
    data = {(u,v,s): (float(rng.uniform(.2, 4)), float(rng.uniform(.2, 4)), float(rng.uniform(0,1)))
            for u,v in itertools.combinations(range(4),2) for s in range(2)}
    powers = [.1,.2,.3,.4]
    a, value = dp_assignment(4, data, powers, time.monotonic()+2)
    def rate(a):
        total = 0.
        for s,(u,v) in enumerate(a):
            g,h,r = data[u,v,s]; x,y = g*powers[u],h*powers[v]
            total += 2*math.log(1+x+y+(1-r)*x*y)-math.log1p(x)-math.log1p(y)
        return total
    alternatives = [tuple(tuple(sorted(perm[2*s:2*s+2])) for s in range(2))
                    for perm in itertools.permutations(range(4))]
    assert abs(value-max(map(rate, alternatives))) < 1e-12
    for k, stop, exception in ((32,time.monotonic()+1,ValueError),(4,0,DeadlineReached)):
        try:
            dp_assignment(k,data,powers,stop)
        except exception:
            pass
        else:
            raise AssertionError('guard failed')
    print('Self-check: exhaustive K4 DP, expired deadline, K32 allocation guard PASS', flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pilot', action='store_true')
    args = ap.parse_args()
    self_check()
    target = OUT / ('pilot_normalized' if args.pilot else 'campaign')
    target.mkdir(exist_ok=False)
    files = [Path(__file__), OUT/'PROTOCOL.md', CERT/'producer.py', METHOD/'core/problem.py',
             METHOD/'modern/fu_sca.py', METHOD/'modern/thu_ide.py', METHOD/'modern/common.py']
    dump(target/'manifest.json', dict(python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
          platform=platform.platform(), hashes={str(f):sha(f) for f in files}, cap=CAP, block=BLOCK,
          created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())))
    cases = [(profile, sep, seed) for sep in SEPARATIONS for profile in 'abc' for seed in SEEDS]
    if args.pilot:
        cases = cases[:1]
    with (target/'raw.csv').open('w', newline='', encoding='utf-8') as stream:
        fields = ['case','profile','separation_deg','seed','arm','se_bits','aggregate_bits','rate_nats','elapsed_seconds',
                  'overrun_seconds','audit_seconds','status','starts_started','starts_completed',
                  'dp_completed','power_calls','accepted','matrix_discrepancy']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for index,(profile,sep,seed) in enumerate(cases):
            name = f'cdl-{profile}-sep{sep}-s{seed}-M2'
            path = ROOT/'research/phase1-cdl-20261109/cases'/f'{name}.json'
            case = json.loads(path.read_text(encoding='utf-8'))
            assert (case['K'],case['S'],case['M']) == (16,8,2)
            problem = Problem(case)
            starts = starts_for(problem)
            dump(target/f'{name}-starts.json', dict(case_sha256=sha(path),
                 starts=[problem.model.encode(a,p) for a,p in starts]))
            order = ARMS[index%3:]+ARMS[:index%3]
            for arm in order:
                result = solve(problem, starts, arm)
                result.update(case=name, profile=profile.upper(), separation_deg=sep, seed=seed,
                              case_sha256=sha(path), order=list(order))
                dump(target/f'{name}-{arm}.json', result)
                row = {k:result[k] for k in fields if k in result}
                row.update(result['counts']); row['matrix_discrepancy'] = result['audit']['discrepancy']
                writer.writerow(row); stream.flush()
                print(f'{index+1}/{len(cases)} {name} {arm}: {result["se_bits"]:.8f} bit/s/Hz; '
                      f'{result["elapsed_seconds"]:.3f}s; {result["counts"]}', flush=True)
                assert result['overrun_seconds'] < .5, 'unexpected deadline overrun; halt'
    print('DONE', target, flush=True)

if __name__ == '__main__':
    main()

