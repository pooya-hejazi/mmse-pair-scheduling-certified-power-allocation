"""Freeze, then run the single all32 campaign. No optimization during freeze."""
from datetime import datetime, timezone
from fractions import Fraction as F
from pathlib import Path
import argparse
import csv
import importlib.util
import json
import math
import statistics
import time
import traceback
import checker
import producer
from source_data import ARCHIVE, HERE, VENDOR, FrozenArchive, canonical, population_names, save, sha


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def freeze():
    if (HERE/'FROZEN.json').exists():
        raise RuntimeError('already frozen: do not overwrite')
    tests = json.loads((HERE/'development/tests-result.json').read_text())
    if not tests['passed']:
        raise RuntimeError('tests have not passed')
    for name, expected in tests['tested_sources'].items():
        if sha((HERE/name).read_bytes()) != expected:
            raise RuntimeError('source changed after tests: '+name)
    archive = FrozenArchive()
    cases = []
    for name in population_names():
        item = archive.load(name, 'corrected')
        if item['dual'] is None:
            raise RuntimeError('missing archived dual proposal: '+name)
        archive.extract(item, 'corrected')
        folder = HERE/'inputs/corrected'/name
        history = []
        for method in (('full' if item['case']['K'] == 8 else 'pricing'), 'joint'):
            member = f'reproduction/studies/corrected/cells/{name}-{method}/result.json'
            raw = archive.zip.read(member)
            filename = f'historical-{method}.json'
            (folder/filename).write_bytes(raw)
            history.append(dict(label='old_full_or_pricing' if method != 'joint' else 'old_joint',
                                method=method, container='nested', member=member,
                                file=filename, sha256=sha(raw)))
        outer_input = f'CR033/study/inputs/{name}.json'
        if outer_input in archive.outer.namelist():
            raw = archive.outer.read(outer_input)
            (folder/'modern-input.json').write_bytes(raw)
            for method in ('T', 'S', 'W', 'FU_SCA', 'THU_IDE'):
                member = f'CR033/study/cells/{name}-{method}/result.json'
                b = archive.outer.read(member)
                filename = f'historical-modern-{method}.json'
                (folder/filename).write_bytes(b)
                history.append(dict(label='modern_'+method, method=method, container='outer', member=member,
                                    file=filename, sha256=sha(b), input_member=outer_input,
                                    input_file='modern-input.json', input_sha256=sha(raw)))
        cases.append(dict(name=name, K=item['case']['K'], binding=item['binding'], history=history))
    if len(cases) != 32 or sum(c['K'] == 8 for c in cases) != 24:
        raise RuntimeError('population mismatch')
    save(HERE/'INPUT_MANIFEST.json', dict(cases=cases, population='all32 corrected physical cases',
                                         outer_sha256=archive.outer_hash, nested_sha256=archive.inner_hash))
    sources = {p.name: sha(p.read_bytes()) for p in HERE.glob('*.py')}
    for n in ('PROTOCOL.md', 'PROOF_NOTE.md', 'INPUT_MANIFEST.json', 'development/tests-result.json'):
        sources[n] = sha((HERE/n).read_bytes())
    vendor_hashes = {n: sha((VENDOR/n).read_bytes()) for n in ('certificates.py', 'verify_upper.py', 'grid_core.py')}
    save(HERE/'FROZEN.json', dict(utc=datetime.now(timezone.utc).isoformat(), source_sha256=sources,
                                 vendor_sha256=vendor_hashes, tests=tests['tests'], n_cases=32,
                                 proof_audit_sha256=sha((HERE.parent/'PROOF_AUDIT.md').read_bytes()),
                                 producer_cap=10., checker_cap=15., max_campaign_seconds=1000.,
                                 target_median_anchor_gap_reduction=.5, target_certificates=16,
                                 certificate_gap_nats='1/100', material_rate_gain_fraction=.01))
    print('Frozen: 32 cases, source hashes, protocol, archive bindings, passed tests.', flush=True)


def check_freeze():
    frozen = json.loads((HERE/'FROZEN.json').read_text())
    for n, expected in frozen['source_sha256'].items():
        if sha((HERE/n).read_bytes()) != expected:
            raise RuntimeError('frozen source changed: '+n)
    for n, expected in frozen['vendor_sha256'].items():
        if sha((VENDOR/n).read_bytes()) != expected:
            raise RuntimeError('frozen vendor changed: '+n)
    return frozen


def quantiles(values):
    values = sorted(values)
    def q(f):
        x = (len(values)-1)*f
        i = int(x)
        return values[i] if i+1 == len(values) else values[i]+(values[i+1]-values[i])*(x-i)
    return dict(n=len(values), minimum=values[0], p10=q(.1), median=q(.5), p90=q(.9), maximum=values[-1],
                mean=statistics.mean(values)) if values else None


def describe_case(case, model):
    gains = model[-1]
    snr = [float(g*F(1, 10)) for g in gains.values()]
    correlations = [float(z[2]) for z in model[-2].values()]
    positive_db = [10*math.log10(v) for v in snr if v > 0]
    return dict(nominal_power_W=.1, user_resource_links=len(snr), zero_gain_links=sum(v == 0 for v in snr),
                snr_linear=snr, positive_snr_db=positive_db,
                positive_snr_db_quantiles=quantiles(positive_db), correlations=correlations,
                r_quantiles=quantiles(correlations))


def historical_checks(case, model, anchor, source_row):
    folder = HERE/'inputs/corrected'/source_row['name']
    output = []
    for record in source_row['history']:
        row = dict(record)
        try:
            raw = (folder/record['file']).read_bytes()
            checker.require(sha(raw) == record['sha256'], 'historical result hash')
            saved = json.loads(raw)
            if 'input_file' in record:
                b = (folder/record['input_file']).read_bytes()
                checker.require(sha(b) == record['input_sha256'], 'historical input hash')
                other_case = json.loads(b)
                checker.require(other_case['channels_re'] == case['channels_re'] and
                                other_case['channels_im'] == case['channels_im'], 'historical binary64 channel mismatch')
                other = checker.reconstruct(other_case)
                checker.require(other == model, 'historical physical-model mismatch')
            lower, upper = checker.check_schedule(saved['schedule'], model)
            diagnostic_anchor = saved.get('worker_status', {}).get('diagnostics', {}).get('common_anchor')
            row.update(valid_schedule=True, checked_lower_nats=str(lower), checked_upper_nats=str(upper),
                       saved_lower_nats=saved.get('lower_nats'), saved_upper_nats=saved.get('upper_nats'),
                       saved_status=saved.get('status'), saved_errors=saved.get('errors', []),
                       saved_verification_timeouts=saved.get('verification_timeouts', []),
                       saved_elapsed=saved.get('elapsed'),
                       saved_charged=saved.get('charged', saved.get('charged_actual')),
                       saved_allowance=saved.get('charged', saved.get('charged_allowance')),
                       common_anchor_identical=(diagnostic_anchor == anchor if diagnostic_anchor is not None else None))
        except Exception as exc:
            row.update(valid_schedule=False, error=type(exc).__name__+': '+str(exc))
        output.append(row)
    return output


def summarize(rows, duration):
    available = [r for r in rows if 'new_upper_nats' in r]
    groups = {}
    for label, chosen in [('all', available)]+[(scene, [r for r in available if r['scene'] == scene])
                                              for scene in ('asu', 'o1')]+[
            (f'K{k}', [r for r in available if r['K'] == k]) for k in (8, 16)]:
        def nums(key):
            return [float(F(r[key])) for r in chosen]
        reductions = [1-float((F(r['new_upper_nats'])-F(r['anchor_lower_nats']))/
                              (F(r['baseline_upper_nats'])-F(r['anchor_lower_nats'])))
                      for r in chosen if F(r['baseline_upper_nats']) > F(r['anchor_lower_nats'])]
        rates = [float((F(r['new_lower_nats'])-F(r['anchor_lower_nats']))/F(r['anchor_lower_nats']))
                 for r in chosen if F(r['anchor_lower_nats']) > 0]
        headroom = [r['old_full_headroom_fraction'] for r in chosen if r.get('old_full_headroom_fraction') is not None]
        groups[label] = dict(n=len(chosen), certificates_new=sum(r['new_certificate'] for r in chosen),
                             certificates_baseline=sum(r['baseline_certificate'] for r in chosen),
                             complete_new=sum(r['new_complete'] for r in chosen),
                             new_gap_nats=quantiles(nums('new_gap_nats')),
                             baseline_gap_nats=quantiles(nums('baseline_gap_nats')),
                             fixed_anchor_gap_reduction=quantiles(reductions),
                             achieved_gain_from_grid_fraction=quantiles(rates),
                             gain_from_grid_at_least_one_percent=sum(x >= .01 for x in rates),
                             old_full_remaining_headroom_fraction=quantiles(headroom),
                             producer_seconds_new=quantiles([r['new_producer_seconds'] for r in chosen]),
                             checker_seconds_new=quantiles([r['new_checker_seconds'] for r in chosen]),
                             producer_seconds_baseline=quantiles([r['baseline_producer_seconds'] for r in chosen]),
                             checker_seconds_baseline=quantiles([r['baseline_checker_seconds'] for r in chosen]),
                             quadrant_boxes=sum(r['curvature']['quadrant_roots'] for r in chosen),
                             finite_box_only=sum(r['curvature']['finite_box_only_roots'] for r in chosen),
                             generic_boxes=sum(r['curvature']['generic_roots'] for r in chosen),
                             errors=sum(bool(r['errors']) for r in chosen))
    all_stats = groups['all']
    success = (len(available) == 32 and all(r['new_complete'] and not r['errors'] for r in available)
               and all_stats['certificates_new'] >= 16
               and all_stats['fixed_anchor_gap_reduction']['median'] >= .5)
    return dict(population=32, rows=len(rows), evaluated=len(available), prospective_target_met=success,
                groups=groups, campaign_wall_seconds=duration,
                timing_scope='10s computation producer + separately 15s checker; imports/archive/fallback/I/O excluded from cells',
                rate_significance_test='none; descriptive material threshold 1%',
                warnings=[r for r in rows if r.get('errors') or 'new_upper_nats' not in r])


def run():
    frozen = check_freeze()
    manifest = json.loads((HERE/'INPUT_MANIFEST.json').read_text())
    final = HERE/'final'
    final.mkdir(exist_ok=False)
    began = time.perf_counter()
    archived = checker.ArchivedInputs(ARCHIVE)
    baseline = load_module('frozen_certificates_campaign', VENDOR/'certificates.py')
    baseline_check = load_module('frozen_verify_campaign', VENDOR/'verify_upper.py')
    rows = []
    for index, source_row in enumerate(manifest['cases']):
        name, binding = source_row['name'], source_row['binding']
        folder = final/name
        folder.mkdir()
        if time.perf_counter()-began > frozen['max_campaign_seconds']:
            row = dict(name=name, errors=[dict(stage='campaign', error='overall time guard')], status='INCOMPLETE')
            rows.append(row)
            save(folder/'row.json', row)
            continue
        setup = time.perf_counter()
        case, anchor, dual = archived.load(binding)
        model = checker.reconstruct(case)
        fallback = producer.seal(dict(schema='FINITE_BOX_INTEGRAL_V1', case_sha256=producer.digest(case),
                binding=binding, anchor_sha256=producer.digest(anchor), schedule=anchor, price=None,
                metrics=dict(status='VERIFIED_UNIVERSAL_FALLBACK', seconds=0.)))
        fallback_checked = checker.verify(case, fallback, anchor, binding, dual, seconds=15.)
        base_fallback = dict(proof=baseline.universal_proof(case), schedule=anchor)
        baseline_check.clear_caches()
        base_fallback_checked = baseline_check.verify(case, base_fallback, seconds=15.)
        save(folder/'fallback.json', fallback)
        save(folder/'fallback-checked.json', fallback_checked)
        errors, outcomes = [], {}
        setup_seconds = time.perf_counter()-setup
        for method in (('new', 'baseline') if index % 2 == 0 else ('baseline', 'new')):
            candidate = fallback if method == 'new' else base_fallback
            receipt = fallback_checked if method == 'new' else base_fallback_checked
            produced, verified, prod_time, check_time = False, False, 0., 0.
            t = time.perf_counter()
            try:
                if method == 'new':
                    candidate = producer.run(case, anchor, binding, dual, seconds=10.)
                else:
                    baseline.clear_caches()
                    candidate = baseline.run(case, 'grid_repair', initial=anchor, grid_duals=dual, seconds=10.)
                prod_time = time.perf_counter()-t
                produced = True
                save(folder/f'{method}-witness.json', candidate)
                t = time.perf_counter()
                if method == 'new':
                    receipt = checker.verify(case, candidate, anchor, binding, dual, seconds=15.)
                else:
                    baseline_check.clear_caches()
                    receipt = baseline_check.verify(case, candidate, seconds=15.)
                check_time = time.perf_counter()-t
                verified = True
                if prod_time > 10.:
                    errors.append(dict(method=method, stage='producer', error='10s cap exceeded', seconds=prod_time))
            except Exception as exc:
                elapsed = time.perf_counter()-t
                if produced:
                    check_time = elapsed
                else:
                    prod_time = elapsed
                errors.append(dict(method=method, stage='checker' if produced else 'producer',
                                   error=type(exc).__name__+': '+str(exc), traceback=traceback.format_exc()))
                # Keep failed saved witness for audit; publish a separately identified fallback.
                candidate = fallback if method == 'new' else base_fallback
                receipt = fallback_checked if method == 'new' else base_fallback_checked
                save(folder/f'{method}-retained-fallback.json', candidate)
            save(folder/f'{method}-checked.json', receipt)
            outcomes[method] = dict(candidate=candidate, receipt=receipt, produced=produced, verified=verified,
                                     producer_seconds=prod_time, checker_seconds=check_time)
        new, base = outcomes['new'], outcomes['baseline']
        nv, bv = new['receipt'], base['receipt']
        histories = historical_checks(case, model, anchor, source_row)
        save(folder/'historical-checks.json', histories)
        distribution = describe_case(case, model)
        save(folder/'data-diagnostics.json', distribution)
        old = next((h for h in histories if h['label'] == 'old_full_or_pricing' and h['valid_schedule']), None)
        if any(not h['valid_schedule'] for h in histories):
            errors.append(dict(stage='historical_schedule', error='one or more archived schedules failed; see historical-checks.json'))
        for h in histories:
            if h['valid_schedule'] and F(h['checked_lower_nats']) > F(nv['upper_nats']):
                errors.append(dict(stage='integrity', error='new upper below archived feasible lower', label=h['label']))
        row = dict(name=name, scene=name.split('-')[0], K=case['K'], S=case['S'], binding=binding,
                   new_lower_nats=nv['lower_nats'], new_upper_nats=nv['upper_nats'], new_gap_nats=nv['gap_nats'],
                   baseline_lower_nats=bv['lower_nats'], baseline_upper_nats=bv['upper_nats'], baseline_gap_nats=bv['gap_nats'],
                   anchor_lower_nats=nv['anchor_lower_nats'], new_certificate=nv['certificate_mathematical'],
                   baseline_certificate=bv['certificate_mathematical'], new_complete=new['verified'] and nv['metrics']['dp_complete'],
                   baseline_verified=base['verified'], new_producer_seconds=new['producer_seconds'],
                   new_checker_seconds=new['checker_seconds'], baseline_producer_seconds=base['producer_seconds'],
                   baseline_checker_seconds=base['checker_seconds'], setup_seconds=setup_seconds,
                   new_status=new['candidate']['metrics']['status'], curvature=nv['metrics'],
                   old_full_lower_nats=old['checked_lower_nats'] if old else None,
                   old_full_headroom_fraction=(float((F(nv['upper_nats'])-F(old['checked_lower_nats']))/
                                                      F(old['checked_lower_nats'])) if old and F(old['checked_lower_nats']) > 0 else None),
                   errors=errors)
        rows.append(row)
        save(folder/'row.json', row)
        print(f"{index+1:02d}/32 {name}: gap {float(F(nv['gap_nats'])):.6g} vs {float(F(bv['gap_nats'])):.6g}; "
              f"time {new['producer_seconds']:.3f}+{new['checker_seconds']:.3f}s; errors {len(errors)}", flush=True)
    duration = time.perf_counter()-began
    save(final/'rows.json', rows)
    save(final/'summary.json', summarize(rows, duration))
    columns = ['name', 'scene', 'K', 'new_lower_nats', 'new_upper_nats', 'new_gap_nats', 'baseline_lower_nats',
               'baseline_upper_nats', 'baseline_gap_nats', 'anchor_lower_nats', 'old_full_lower_nats',
               'new_certificate', 'baseline_certificate', 'new_complete', 'new_producer_seconds',
               'new_checker_seconds', 'baseline_producer_seconds', 'baseline_checker_seconds', 'old_full_headroom_fraction', 'errors']
    with (final/'results.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow({key: (float(F(r[key])) if key.endswith('_nats') and r.get(key) is not None
                                   else json.dumps(r[key]) if key == 'errors' else r.get(key)) for key in columns})
    outputs = {str(p.relative_to(final)).replace('\\', '/'): sha(p.read_bytes())
               for p in final.rglob('*') if p.is_file()}
    save(final/'OUTPUT_MANIFEST.json', dict(files=outputs, freeze_sha256=sha((HERE/'FROZEN.json').read_bytes()),
                                           archive_open_seconds=archived.seconds, campaign_seconds=duration))
    print('Campaign saved. Run replay.py before citing results.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('freeze', 'run'))
    args = parser.parse_args()
    freeze() if args.action == 'freeze' else run()
