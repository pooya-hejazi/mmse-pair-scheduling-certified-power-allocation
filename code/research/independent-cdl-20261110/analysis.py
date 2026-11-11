"""Prespecified block-level analysis of the independent native-CDL campaign.

Reads complete, independently audited saved results. Never imports a runner or
optimizer. Run --self-test before outcomes; run without arguments after replay.
"""
from pathlib import Path
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os

import numpy as np

HERE = Path(__file__).resolve().parent
ARMS = ('DP-SQP', 'DP-Fu-SCA', 'DP-Thu-IDE', 'Fixed-SQP', 'DP-uniform')
PROFILES = ('A', 'B', 'C')
SNRS = (0, 10, 20)
BLOCKS = tuple(range(20))
PRIMARY = ('DP-Fu-SCA', 'DP-Thu-IDE')
ABLATIONS = ('Fixed-SQP', 'DP-uniform')
TIE = 1e-5
DRAWS = 20000
LABELS = ('DP + SQP', 'DP + Fu adaptation', 'DP + IDE adaptation',
          'Fixed pairing + SQP', 'DP, uniform power')
COLORS = ('#185a9d', '#d55e00', '#009e73', '#9055a2', '#6c6c6c')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def csv_out(path, rows):
    require(bool(rows), 'Cannot emit empty results table')
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def wtl(values):
    values = np.asarray(values, dtype=float)
    return dict(wins=int(np.sum(values > TIE)), ties=int(np.sum(abs(values) <= TIE)),
                losses=int(np.sum(values < -TIE)))


def mean_interval(block_values, indices, confidence=.95):
    values = np.asarray(block_values, dtype=float)
    require(values.shape == (20,) and np.isfinite(values).all(), 'Expected 20 finite block effects')
    draws = values[indices].mean(axis=1)
    alpha = 1-confidence
    bounds = np.quantile(draws, [alpha/2, 1-alpha/2])
    return dict(mean=float(values.mean()), low=float(bounds[0]), high=float(bounds[1]),
                confidence=confidence, independent_blocks=20)


def contrast(proposed, baseline, indices, confidence):
    proposed, baseline = np.asarray(proposed), np.asarray(baseline)
    require(proposed.shape == baseline.shape and proposed.shape[0] == 20,
            'Contrast must retain all 20 blocks and identical cells')
    require(np.all(baseline > 0), 'Nonpositive comparator makes relative endpoint undefined')
    delta = proposed-baseline
    relative = 100*delta/baseline
    block_absolute = delta.reshape(20, -1).mean(axis=1)
    block_relative = relative.reshape(20, -1).mean(axis=1)
    return dict(absolute_bpshz=mean_interval(block_absolute, indices, confidence),
                relative_pct_secondary=mean_interval(block_relative, indices, .95),
                block_absolute_bpshz=block_absolute.tolist(),
                block_relative_pct=block_relative.tolist(), case_wtl=wtl(delta),
                block_wtl=wtl(block_absolute),
                n_cases=int(delta.size), tolerance_bpshz=TIE)


def load_stage(stage):
    files = [p for p in sorted((HERE/'runs'/stage).glob('*.json'))
             if p.name != 'manifest.json' and not p.name.endswith('-starts.json')]
    arms = ARMS if stage == 'main' else ARMS[:3]
    profiles = PROFILES if stage == 'main' else ('B',)
    snrs = SNRS if stage == 'main' else (10,)
    expected = {(b, p, s, a) for b in BLOCKS for p in profiles for s in snrs for a in arms}
    rows = {}
    for path in files:
        require('FAILURE' not in path.name and 'rejected' not in path.name.lower(),
                f'Unresolved failed/rejected run: {path.name}')
        row = read_json(path)
        require(type(row.get('block')) is int, f'Invalid block in {path.name}')
        key = (row['block'], row['profile'], row['snr_db'], row['arm'])
        require(key in expected and key not in rows, f'Unexpected/duplicate record: {key}')
        for field in ('se_bits', 'rate_nats', 'elapsed_seconds'):
            require(isinstance(row.get(field), (int, float)) and
                    math.isfinite(row[field]), f'Nonfinite/missing {field}: {path.name}')
        require(row['elapsed_seconds'] >= 0 and row['rate_nats'] >= 0, 'Negative time/rate')
        require(abs(row['se_bits']-row['rate_nats']/(8*math.log(2))) < 1e-10,
                f'Occupied-band normalization: {path.name}')
        require(all(field in row for field in ('counts', 'diagnostics', 'schedule', 'history',
                                               'case_path', 'case_sha256')),
                f'Missing saved-evidence field: {path.name}')
        rows[key] = row
    require(set(rows) == expected,
            f'{stage}: expected {len(expected)} records, got {len(rows)}; no partial analysis')
    return rows, files


def summarize_diagnostics(rows):
    categories = defaultdict(Counter)
    numerical = defaultdict(list)
    counters = Counter()

    def walk(value, prefix=''):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f'{prefix}.{key}'.strip('.'))
        elif isinstance(value, list):
            for item in value:
                walk(item, prefix+'[]')
        elif isinstance(value, str):
            categories[prefix][value] += 1
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            require(math.isfinite(value), f'Nonfinite diagnostic: {prefix}')
            numerical[prefix].append(value)
        elif isinstance(value, bool):
            categories[prefix][str(value)] += 1

    for row in rows:
        categories['run_status'][str(row.get('status', 'not_recorded'))] += 1
        for key, value in row['counts'].items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                counters[key] += value
        walk(row['diagnostics'])
    return dict(completed_work_totals=dict(counters),
                categorical={key: dict(value) for key, value in sorted(categories.items())},
                numerical={key: dict(n=len(value), minimum=min(value), maximum=max(value),
                                     median=float(np.median(value)))
                           for key, value in sorted(numerical.items())})


def run_analysis():
    main, main_files = load_stage('main')
    sensitivity, sensitivity_files = load_stage('sensitivity')
    audit = read_json(HERE/'audit_campaign.json')
    require(audit.get('status') == 'PASS', 'Independent final replay must pass before analysis')
    expected_hashes = {str(p.relative_to(HERE)).replace('\\', '/'): sha(p)
                       for p in main_files+sensitivity_files}
    require(audit.get('runs_sha256') == expected_hashes,
            'Run files differ from the independent replay; rerun audit first')
    require(audit.get('scope') == 'main-and-sensitivity' and audit.get('final_allocations') == 960,
            'Full independent audit required; pilot replay is excluded')
    require(audit.get('source_manifest_sha256') == sha(HERE/'source_manifest.json') and
            audit.get('seed_manifest_sha256') == sha(HERE/'seed_manifest.json'),
            'Source/seed manifest changed after replay')
    seeds = read_json(HERE/'seed_manifest.json')
    seed = seeds['bootstrap']['effective_seed']
    require(type(seed) is int and 0 <= seed < 2**32, 'Invalid frozen bootstrap seed')
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, 20, size=(DRAWS, 20))
    values = np.array([[[[main[b, p, s, a]['se_bits'] for a in ARMS]
                        for s in SNRS] for p in PROFILES] for b in BLOCKS])
    long_values = np.array([[sensitivity[b, 'B', 10, a]['se_bits']
                            for a in ARMS[:3]] for b in BLOCKS])
    primary = {arm: contrast(values[..., 0], values[..., ARMS.index(arm)], indices, .975)
               for arm in PRIMARY}
    ablations = {arm: contrast(values[..., 0], values[..., ARMS.index(arm)], indices, .95)
                 for arm in ABLATIONS}
    cells = []
    cell_contrasts = []
    for pi, profile in enumerate(PROFILES):
        for si, snr in enumerate(SNRS):
            for ai, arm in enumerate(ARMS):
                est = mean_interval(values[:, pi, si, ai], indices)
                cells.append(dict(profile=profile, snr_db=snr, arm=arm,
                                  mean_se=est['mean'], low=est['low'], high=est['high'],
                                  confidence=.95, independent_blocks=20))
            for arm in PRIMARY+ABLATIONS:
                ai = ARMS.index(arm)
                est = contrast(values[:, pi, si, 0], values[:, pi, si, ai], indices, .95)
                cell_contrasts.append(dict(profile=profile, snr_db=snr, comparator=arm,
                    mean_difference=est['absolute_bpshz']['mean'],
                    low=est['absolute_bpshz']['low'], high=est['absolute_bpshz']['high'],
                    confidence=.95, **est['case_wtl']))
    block_rows = []
    for block in BLOCKS:
        row = dict(block=block)
        row.update({arm+'_mean_se': float(values[block, ..., ai].mean())
                    for ai, arm in enumerate(ARMS)})
        for arm, con in {**primary, **ablations}.items():
            row['SQP_minus_'+arm+'_bpshz'] = con['block_absolute_bpshz'][block]
            row['SQP_minus_'+arm+'_relative_pct'] = con['block_relative_pct'][block]
        block_rows.append(row)
    case_rows = []
    for block in BLOCKS:
        for pi, profile in enumerate(PROFILES):
            for si, snr in enumerate(SNRS):
                row = dict(block=block, profile=profile, snr_db=snr)
                row.update({arm+'_se': float(values[block, pi, si, ai])
                            for ai, arm in enumerate(ARMS)})
                row.update({'SQP_minus_'+arm+'_bpshz': float(values[block, pi, si, 0]-
                            values[block, pi, si, ARMS.index(arm)]) for arm in PRIMARY+ABLATIONS})
                case_rows.append(row)
    runtimes, diagnostics = {}, {}
    for stage, rows in [('main', main), ('sensitivity', sensitivity)]:
        runtimes[stage], diagnostics[stage] = {}, {}
        for arm in (ARMS if stage == 'main' else ARMS[:3]):
            selected = [row for key, row in rows.items() if key[-1] == arm]
            times = np.array([row['elapsed_seconds'] for row in selected])
            runtimes[stage][arm] = dict(n=len(times), mean=float(times.mean()),
                median=float(np.median(times)), p90=float(np.percentile(times, 90)),
                minimum=float(times.min()), maximum=float(times.max()))
            diagnostics[stage][arm] = summarize_diagnostics(selected)
    budget = dict(arms={}, contrasts={}, setting='20 CDL-B blocks at nominal 10 dB')
    for ai, arm in enumerate(ARMS[:3]):
        short = values[:, 1, 1, ai]
        budget['arms'][arm] = dict(main_10s=mean_interval(short, indices),
            sensitivity_30s=mean_interval(long_values[:, ai], indices),
            increment_30s_minus_10s=contrast(long_values[:, ai], short, indices, .95))
    for arm in PRIMARY:
        ai = ARMS.index(arm)
        short_delta = values[:, 1, 1, 0]-values[:, 1, 1, ai]
        long_delta = long_values[:, 0]-long_values[:, ai]
        budget['contrasts'][arm] = dict(main_10s=contrast(values[:, 1, 1, 0],
            values[:, 1, 1, ai], indices, .95), sensitivity_30s=contrast(long_values[:, 0],
            long_values[:, ai], indices, .95), change_in_absolute_contrast=mean_interval(
            long_delta-short_delta, indices), change_by_block_bpshz=(long_delta-short_delta).tolist())
    overall = {arm: mean_interval(values[..., ai].mean(axis=(1, 2)), indices)
               for ai, arm in enumerate(ARMS)}
    summary = dict(status='COMPLETE', n_main_cases=180, n_main_runs=900,
        n_sensitivity_cases=20, n_sensitivity_runs=60, independent_blocks=20,
        estimand='Mean of 20 root-block effects; each main block equally averages nine profile/SNR cells',
        bootstrap=dict(draws=DRAWS, effective_seed=seed, generator='numpy.default_rng/PCG64',
            unit='root block', primary_individual_confidence=.975,
            primary_percentiles=[1.25, 98.75], secondary_pointwise_confidence=.95,
            family='Bonferroni nominal 95% family for two absolute primary contrasts; approximate bootstrap coverage'),
        tolerance_bpshz=TIE, overall_mean_se=overall, primary=primary, ablations=ablations,
        cells=cells, cell_contrasts=cell_contrasts, runtime=runtimes,
        diagnostics=diagnostics, sensitivity=budget,
        provenance=dict(runs_sha256=expected_hashes, seed_manifest_sha256=sha(HERE/'seed_manifest.json'),
            protocol_sha256=sha(HERE/'PROTOCOL.md'), auditor_report_sha256=sha(HERE/'audit_campaign.json'),
            analysis_source_sha256=sha(Path(__file__))))
    out = HERE/'analysis'
    out.mkdir(exist_ok=True)
    dump(out/'results.json', summary)
    csv_out(out/'cells.csv', cells)
    csv_out(out/'cell_contrasts.csv', cell_contrasts)
    csv_out(out/'block_effects.csv', block_rows)
    csv_out(out/'case_values.csv', case_rows)
    lines = ['# Independent native-CDL saved-data analysis', '',
        'Complete main population: 180 cases in 20 independent root blocks; 900 allocations. '
        'Sensitivity: 20 CDL-B/10 dB cases and 60 allocations. No pilot or historical case is pooled.', '',
        'Primary intervals are individual 97.5% whole-block percentile intervals '
        '(Bonferroni nominal 95% family for two absolute contrasts; approximate bootstrap coverage). '
        'All other intervals are pointwise 95%. Positive differences favour DP-SQP. '
        'Ties use an absolute 1e-5 bit/s/Hz band and do not establish equivalence.', '',
        '| Comparator | Mean absolute difference (bit/s/Hz) | 97.5% interval | Case W/T/L |',
        '|---|---:|---|---|']
    for arm, con in primary.items():
        est, counts = con['absolute_bpshz'], con['case_wtl']
        lines.append(f"| {arm} | {est['mean']:.8g} | [{est['low']:.8g}, {est['high']:.8g}] | "
                     f"{counts['wins']}/{counts['ties']}/{counts['losses']} |")
    lines += ['', 'All 20 block effects, all cell values, secondary relative effects, ablations, '
        'runtime, completed work, numerical returns and 10/30-second sensitivity are retained in '
        'the machine-readable outputs. No convergence or deployment claim follows from a bounded run. '
        'DP-uniform is a deterministic ablation, not a time-matched iterative competitor.', '']
    (out/'RESULTS.md').write_text('\n'.join(lines), encoding='utf-8')
    plot(summary, main, out)
    print(json.dumps({key: summary[key] for key in ('status', 'n_main_cases',
        'independent_blocks', 'primary')}, indent=2))


def plot(summary, main, out):
    os.environ.setdefault('MPLCONFIGDIR', str(HERE/'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': True, 'grid.alpha': .2, 'pdf.fonttype': 42})
    figures = out/'figures'
    figures.mkdir(exist_ok=True)

    def save(fig, name):
        fig.savefig(figures/(name+'.pdf'), bbox_inches='tight')
        fig.savefig(figures/(name+'.png'), dpi=220, bbox_inches='tight')
        plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.4), sharey=True)
    for ax, profile in zip(axes, PROFILES):
        for ai, arm in enumerate(ARMS):
            rows = [r for r in summary['cells'] if r['profile'] == profile and r['arm'] == arm]
            mean = np.array([r['mean_se'] for r in rows])
            low, high = np.array([r['low'] for r in rows]), np.array([r['high'] for r in rows])
            ax.plot(SNRS, mean, color=COLORS[ai], marker=('o','s','^','D','v')[ai],
                    markersize=4, label=LABELS[ai], linestyle=('-','--',':','-.','--')[ai])
            ax.fill_between(SNRS, low, high, color=COLORS[ai], alpha=.09)
        ax.set(title='CDL-'+profile, xlabel='Nominal SNR (dB)', xticks=SNRS)
    axes[0].set_ylabel('Occupied-band SE (bit/s/Hz)')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.5, -.16), ncol=3,
               fontsize=8, frameon=False)
    fig.suptitle('Means over 20 blocks; shaded pointwise 95% intervals', fontsize=9)
    fig.tight_layout()
    save(fig, 'native_cdl_profile_se')

    for name, contrasts, coverage in [('native_cdl_primary', summary['primary'], '97.5%'),
                                      ('native_cdl_ablation', summary['ablations'], '95%')]:
        fig, ax = plt.subplots(figsize=(3.5, 3.0))
        for yi, (arm, con) in enumerate(contrasts.items()):
            est = con['absolute_bpshz']
            ax.scatter(con['block_absolute_bpshz'], yi+np.linspace(-.14,.14,20),
                       s=13, color=COLORS[ARMS.index(arm)], alpha=.55)
            ax.plot([est['low'],est['high']], [yi,yi], color='black', linewidth=2)
            ax.scatter(est['mean'], yi, marker='D', color='black', s=32, zorder=5)
        ax.axvline(0, color='black', linewidth=.8, linestyle='--')
        ax.set(yticks=range(len(contrasts)), yticklabels=list(contrasts),
               xlabel='DP-SQP minus comparator (bit/s/Hz)',
               title=f'20 block effects; mean and {coverage} interval')
        ax.tick_params(axis='y', labelsize=8)
        fig.tight_layout()
        save(fig, name)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
    for ax, arm in zip(axes, PRIMARY):
        for pi, profile in enumerate(PROFILES):
            rows = [r for r in summary['cell_contrasts'] if r['profile']==profile and r['comparator']==arm]
            mean = np.array([r['mean_difference'] for r in rows])
            ax.errorbar(np.array(SNRS)+(pi-1)*.3, mean,
                yerr=[mean-np.array([r['low'] for r in rows]), np.array([r['high'] for r in rows])-mean],
                fmt=('o-','s--','^:')[pi], capsize=2, label='CDL-'+profile)
        ax.axhline(0, color='black', linewidth=.7)
        ax.set(title='DP-SQP minus '+arm, xlabel='Nominal SNR (dB)', xticks=SNRS)
    axes[0].set_ylabel('Mean difference (bit/s/Hz)')
    axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle('Pointwise 95% whole-block intervals', fontsize=9)
    fig.tight_layout()
    save(fig, 'native_cdl_cell_differences')

    fig, ax = plt.subplots(figsize=(3.5, 3.2))
    times = [[row['elapsed_seconds'] for key,row in main.items() if key[-1]==arm] for arm in ARMS]
    ax.boxplot(times, tick_labels=('SQP','Fu','IDE','Fixed\nSQP','Uniform'), showfliers=True,
               flierprops={'markersize':2})
    ax.set(ylabel='Recorded search time (s)', title='180 cases per arm; uniform is an ablation')
    ax.axhline(10, linestyle='--', color='grey', linewidth=.7)
    fig.tight_layout()
    save(fig, 'native_cdl_runtime')

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    for ai, arm in enumerate(ARMS[:3]):
        estimates = [summary['sensitivity']['arms'][arm][key] for key in ('main_10s','sensitivity_30s')]
        mean = np.array([r['mean'] for r in estimates])
        axes[0].errorbar(np.array([10,30])+(ai-1)*.35, mean,
            yerr=[mean-np.array([r['low'] for r in estimates]),np.array([r['high'] for r in estimates])-mean],
            color=COLORS[ai], marker=('o','s','^')[ai], capsize=2, label=LABELS[ai])
        axes[1].plot([10,30], [summary['runtime'][stage][arm]['mean']
                    if stage=='sensitivity' else np.mean([main[b,'B',10,arm]['elapsed_seconds'] for b in BLOCKS])
                    for stage in ('main','sensitivity')], color=COLORS[ai], marker=('o','s','^')[ai])
    axes[0].set(ylabel='Mean SE (bit/s/Hz)', xlabel='Search cap (s)', xticks=[10,30])
    axes[1].set(ylabel='Mean recorded search time (s)', xlabel='Search cap (s)', xticks=[10,30])
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle('Same 20 CDL-B/10 dB cases; SE intervals are pointwise 95%', fontsize=9)
    fig.tight_layout()
    save(fig, 'native_cdl_budget_sensitivity')


def self_test():
    # Pure arithmetic checks; no synthetic outcomes are written or mixed into evidence.
    idx = np.random.default_rng(123).integers(0,20,(DRAWS,20))
    exact = mean_interval(np.full(20,.25), idx, .975)
    assert exact['mean'] == exact['low'] == exact['high'] == .25
    baseline = np.full((20,3,3), 2.)
    block_effects = np.arange(20)/100
    proposed = baseline+block_effects[:,None,None]
    got = contrast(proposed, baseline, idx, .975)
    assert np.allclose(got['block_absolute_bpshz'], block_effects)
    assert abs(got['absolute_bpshz']['mean']-.095)<1e-14
    assert np.allclose(got['block_relative_pct'], 50*block_effects)
    assert got['case_wtl'] == dict(wins=171,ties=9,losses=0)
    assert wtl([-2*TIE,-TIE,0,TIE,2*TIE]) == dict(wins=1,ties=3,losses=1)
    try:
        contrast(proposed,np.zeros_like(baseline),idx,.975)
    except ValueError:
        pass
    else:
        raise AssertionError('Zero relative denominator was accepted')
    print('PASS: block averaging, percentile interval, relative endpoint and W/T/L self-checks; no outcome files written')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    self_test() if args.self_test else run_analysis()
