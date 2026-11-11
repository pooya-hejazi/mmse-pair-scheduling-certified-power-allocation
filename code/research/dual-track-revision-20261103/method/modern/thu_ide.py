"""Thu arXiv2607.21860v1 Algorithm1/Eqs31-36 adapted power search.

Two source mutations, source parameter adaptation, disclosed common-model
projection/encoding. No stock scipy DE, channel generation or import-time I/O.
"""
import math
import time
import numpy as np
try:
    from .common import (guard, checked, improves, projected_exact,
                         publish_candidate, diagnostics, DeadlineReached)
except ImportError:
    from common import (guard, checked, improves, projected_exact,
                        publish_candidate, diagnostics, DeadlineReached)


def mutation(parent, pbest, r1, r2, factor, operator):
    if operator == 0:
        return pbest+factor*(r1-r2)
    if operator == 1:
        return parent+factor*(pbest-parent)+factor*(r1-r2)
    raise ValueError('unknown mutation operator')


def crossover(parent, mutant, rate, rng):
    mask = np.asarray(rng.random(len(parent))) < rate
    forced = int(rng.integers(len(parent)))
    mask[forced] = True
    return np.where(mask, mutant, parent)


def lehmer(values, gains, previous):
    values, gains = np.asarray(values, float), np.asarray(gains, float)
    if len(values) == 0:
        return float(previous)
    total = float(np.sum(gains))
    if total <= 0 or not np.isfinite(total):
        return float(previous)
    weights = gains/total
    denominator = float(np.dot(weights, values))
    return (float(np.dot(weights, values*values)/denominator)
            if denominator > 0 else float(previous))


def operator_probability(gains, counts, previous):
    if min(counts) == 0:
        return float(previous)
    return .8 if gains[0]/counts[0] > gains[1]/counts[1] else .2


def trim_archive(archive, capacity, rng):
    archive = [x.copy() for x in archive]
    while len(archive) > capacity:
        del archive[int(rng.integers(len(archive)))]
    return archive


def sample_parameters(mu_f, mu_cr, rng, deadline):
    factor = -1.0
    while factor <= 0:
        guard(deadline)
        factor = float(mu_f + .1*rng.standard_cauchy())
    factor = min(1.0, factor)
    rate = float(np.clip(rng.normal(mu_cr, .1), 0, 1))
    if not (math.isfinite(factor) and math.isfinite(rate)):
        raise ValueError('nonfinite IDE parameters')
    return factor, rate


def generation(population, records, archive, means_f, means_cr, probability,
               window_gains, window_counts, evaluate, rng, deadline, diagnostics=None):
    """One synchronous source generation; evaluate returns checked record.

    Old population/archive never mutate. Counts include ALL operator calls.
    Exact-enclosure selection preserves common-model feasibility/monotonicity.
    """
    old = np.asarray(population, float).copy()
    old_archive = [np.asarray(x, float).copy() for x in archive]
    q, dimension = old.shape
    ranked = sorted(range(q), key=lambda j: (-records[j]['value'], j))
    top = ranked[:max(2, int(math.ceil(.1*q)))]
    next_population = old.copy()
    next_records = list(records)
    displaced = []
    successes_f, successes_cr, successes_gain = [[], []], [[], []], [[], []]
    for index in range(q):
        guard(deadline)
        op = 0 if float(rng.random()) < probability else 1
        window_counts[op] += 1
        if diagnostics is not None:
            diagnostics['operator_invocations'][op] += 1
        factor, rate = sample_parameters(means_f[op], means_cr[op], rng, deadline)
        pbest_index = top[int(rng.integers(len(top)))]
        r1_pool = [j for j in range(q) if j != index]
        r1_index = r1_pool[int(rng.integers(len(r1_pool)))]
        combined = [old[j] for j in range(q)] + old_archive
        r2_pool = [j for j in range(len(combined)) if j not in (index, r1_index)]
        r2_index = r2_pool[int(rng.integers(len(r2_pool)))]
        mutant = mutation(old[index], old[pbest_index], old[r1_index],
                          combined[r2_index], factor, op)
        trial = crossover(old[index], mutant, rate, rng)
        result, phenotype = evaluate(trial)
        guard(deadline)
        if result is None:
            continue  # Invalid numerical trial: retain parent, invocation counted.
        if improves(result, records[index]):
            gain = result['value']-records[index]['value']
            next_population[index] = phenotype
            next_records[index] = result
            displaced.append(old[index].copy())
            window_gains[op] += gain
            successes_f[op].append(factor)
            successes_cr[op].append(rate)
            successes_gain[op].append(gain)
    for op in (0, 1):
        means_f[op] = lehmer(successes_f[op], successes_gain[op], means_f[op])
        means_cr[op] = lehmer(successes_cr[op], successes_gain[op], means_cr[op])
    return next_population, next_records, trim_archive(old_archive+displaced, q, rng)


def refine_power(problem, assignment, p0, deadline, rng, publish):
    began = time.monotonic()
    d = diagnostics('THU_IDE')
    d.update(generations=0, restarts=0, initializations=0, incomplete_generation=False)
    d['operator_invocations'] = [0, 0]
    out = np.asarray(p0, float).copy()
    best = None
    low, high = float(problem.low), float(problem.high)
    width = high-low
    try:
        best = checked(problem, assignment, out, deadline)
        out = best['numeric'].copy()
        d['evaluations'] += 1
        if width == 0 or problem.k*problem.low == problem.budget:
            d['stop_reason'] = 'singleton_feasible_set'
            return out, d
        q = min(4*problem.k, 300)

        def evaluate(z):
            nonlocal best, out
            guard(deadline)
            try:
                powers = projected_exact(problem, low+width*np.asarray(z, float))
            except (ValueError, FloatingPointError):
                d['error_count'] += 1
                return None, None
            result = checked(problem, assignment, powers, deadline)
            d['evaluations'] += 1
            if improves(result, best):
                best = result
                out = best['numeric'].copy()
                d['accepted'] += 1
                publish_candidate(publish, assignment, best, d, deadline)
            return result, (result['numeric']-low)/width

        while True:
            guard(deadline)
            population = [(out-low)/width]
            records = [best]
            seen = {tuple(float(x) for x in out)}
            starts = list(getattr(problem, 'common_power_starts', []))
            if not starts:
                starts = [np.full(problem.k, min(high, float(problem.budget)/problem.k))]
            start_index = 0
            while len(population) < q:
                guard(deadline)
                if start_index < len(starts):
                    raw = np.asarray(starts[start_index], float)
                    start_index += 1
                else:
                    raw = low+width*rng.random(problem.k)
                powers = projected_exact(problem, raw)
                key = tuple(float(x) for x in powers)
                if key in seen:
                    continue
                seen.add(key)
                record, z = evaluate((powers-low)/width)
                population.append(z)
                records.append(record)
            population = np.asarray(population)
            d['initializations'] += 1
            archive = []
            means_f, means_cr = np.array([.2, .2]), np.array([1., 1.])
            probability = .2
            gains, counts = np.zeros(2), np.zeros(2, dtype=int)
            for g in range(1, 501):
                guard(deadline)
                d['incomplete_generation'] = True
                population, records, archive = generation(
                    population, records, archive, means_f, means_cr,
                    probability, gains, counts, evaluate, rng, deadline, diagnostics=d)
                d['incomplete_generation'] = False
                d['generations'] += 1
                d['iterations'] += 1
                if g % 10 == 0:
                    probability = operator_probability(gains, counts, probability)
                    d['last_window_invocations'] = counts.tolist()
                    d['last_window_gains'] = gains.tolist()
                    gains[:] = 0
                    counts[:] = 0
                d.update(mu_F=means_f.tolist(), mu_CR=means_cr.tolist(),
                         operator1_probability=float(probability), archive_size=len(archive))
            d['cap_count'] += 1
            d['restarts'] += 1
    except DeadlineReached:
        d['stop_reason'] = 'deadline'
    finally:
        d['elapsed_seconds'] = time.monotonic()-began
    return out, d
