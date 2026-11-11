"""Descriptive analysis of the one frozen campaign; no optimizer or dataset edits.

Created after algorithm freeze. Does not alter final/ or its output manifest.
"""
from fractions import Fraction as F
from pathlib import Path
import csv
import json
import math
import statistics
from source_data import HERE, save, sha


def distribution(values):
    v = sorted(values)
    if not v:
        return None
    def q(p):
        x = (len(v)-1)*p
        i = int(x)
        return v[i] if i+1 == len(v) else v[i]+(v[i+1]-v[i])*(x-i)
    return dict(n=len(v), min=v[0], p10=q(.1), median=q(.5), p90=q(.9), max=v[-1], mean=statistics.mean(v))


def snr_distribution_with_zeros(linear):
    """Extended-real dB quantiles retain zero-gain links as minus infinity."""
    values = sorted(10*math.log10(v) if v > 0 else -math.inf for v in linear)
    def q(p):
        x = (len(values)-1)*p
        i = int(x)
        if not math.isfinite(values[i]):
            return '-inf'
        return values[i] if i+1 == len(values) else values[i]+(values[i+1]-values[i])*(x-i)
    return dict(n=len(values), zero_links=sum(v == 0 for v in linear),
                min=q(0), p10=q(.1), median=q(.5), p90=q(.9), max=q(1))


def main():
    final = HERE/'final'
    replay = json.loads((HERE/'replay-result.json').read_text())
    if not replay['valid']:
        raise RuntimeError('replay has not passed; analyze failures before reporting efficacy')
    manifest = json.loads((final/'OUTPUT_MANIFEST.json').read_text())
    for path, expected in manifest['files'].items():
        if sha((final/path).read_bytes()) != expected:
            raise RuntimeError('output changed: '+path)
    rows = json.loads((final/'rows.json').read_text())
    groups, modern, detailed = {}, [], []
    for scene in ('asu', 'o1'):
        selected = [r for r in rows if r['scene'] == scene]
        snr, medians, rhos, root_box, root_global, count, zeros = [], [], [], 0, 0, 0, 0
        all_linear, all_case_medians, case_curvature_fractions = [], [], []
        for r in selected:
            d = json.loads((final/r['name']/'data-diagnostics.json').read_text())
            snr.extend(d['positive_snr_db'])
            all_linear.extend(d['snr_linear'])
            all_case_medians.append(snr_distribution_with_zeros(d['snr_linear'])['median'])
            medians.append(d['positive_snr_db_quantiles']['median'])
            rhos.extend(d['correlations'])
            zeros += d['zero_gain_links']
            c = r['curvature']
            root_box += c['quadrant_roots']+c['finite_box_only_roots']
            root_global += c['quadrant_roots']
            count += c['quadrant_roots']+c['finite_box_only_roots']+c['generic_roots']
            case_curvature_fractions.append((c['quadrant_roots']+c['finite_box_only_roots'])/
                                            (c['quadrant_roots']+c['finite_box_only_roots']+c['generic_roots']))
        groups[scene] = dict(n_cases=len(selected), positive_received_snr_db_pooled=distribution(snr),
                              all_link_received_snr_db_pooled=snr_distribution_with_zeros(all_linear),
                              all_link_case_median_snr_db=distribution(all_case_medians),
                              per_case_median_received_snr_db=distribution(medians), zero_gain_links=zeros,
                              squared_correlation_pooled=distribution(rhos), total_pair_boxes=count,
                              certified_full_boxes=root_box, whole_quadrant_boxes=root_global,
                              full_box_qualifying_fraction=root_box/count, whole_quadrant_fraction=root_global/count,
                              per_case_full_box_qualifying_fraction=distribution(case_curvature_fractions))
    for r in rows:
        lower, upper, anchor = map(lambda n: F(r[n]), ('new_lower_nats', 'new_upper_nats', 'anchor_lower_nats'))
        histories = json.loads((final/r['name']/'historical-checks.json').read_text())
        record = dict(name=r['name'], scene=r['scene'], K=r['K'],
                      Q_new_nats=float(lower), Q_grid_nats=float(anchor),
                      delta_grid_nats=float(lower-anchor), relative_delta_grid=float((lower-anchor)/anchor),
                      verified_grid_headroom_nats=float(upper-anchor), verified_grid_headroom_fraction=float((upper-anchor)/anchor),
                      verified_final_gap_nats=float(upper-lower),
                      final_receipt_computation_seconds=r['new_producer_seconds']+r['new_checker_seconds'],
                      new_certificate=r['new_certificate'])
        c = r['curvature']
        if c['fixed_alpha_upper_nats'] is not None:
            record['matched_fixed_alpha_repair_minus_integral_nats'] = float(
                F(c['fixed_alpha_upper_nats'])-F(c['integral_upper_nats']))
        for h in histories:
            if not h['valid_schedule']:
                continue
            old = F(h['checked_lower_nats'])
            if h['label'] == 'old_full_or_pricing':
                record.update(Q_old_full_or_pricing_nats=float(old), delta_old_full_nats=float(lower-old),
                              relative_delta_old_full=float((lower-old)/old),
                              verified_old_full_headroom_nats=float(upper-old),
                              verified_old_full_headroom_fraction=float((upper-old)/old))
            if h['label'].startswith('modern_'):
                modern.append(dict(name=r['name'], method=h['method'], rate_nats=float(old),
                                   delta_new_minus_modern_nats=float(lower-old),
                                   delta_new_minus_modern_SE=float(lower-old)/(r['S']*math.log(2)),
                                   fraction_new_minus_modern=float((lower-old)/old),
                                   same_common_anchor=h['common_anchor_identical'],
                                   saved_elapsed=h['saved_elapsed'], saved_charged=h['saved_charged'],
                                   saved_errors=h['saved_errors'], saved_timeouts=h['saved_verification_timeouts']))
        detailed.append(record)
    rates = {}
    for name, selected in [('all', detailed)]+[(s, [r for r in detailed if r['scene'] == s]) for s in ('asu', 'o1')]:
        rates[name] = {key: distribution([r[key] for r in selected if key in r]) for key in
                       ('delta_grid_nats', 'relative_delta_grid', 'delta_old_full_nats', 'relative_delta_old_full',
                        'verified_old_full_headroom_nats', 'verified_old_full_headroom_fraction',
                        'final_receipt_computation_seconds', 'matched_fixed_alpha_repair_minus_integral_nats')}
        rates[name]['material_grid_gains'] = sum(r['relative_delta_grid'] >= .01 for r in selected)
        rates[name]['material_old_full_gains'] = sum(r.get('relative_delta_old_full', 0) >= .01 for r in selected)
    comparison = {}
    for method in ('T', 'S', 'W', 'FU_SCA', 'THU_IDE'):
        chosen = [r for r in modern if r['method'] == method]
        comparison[method] = dict(n=len(chosen), delta_nats=distribution([r['delta_new_minus_modern_nats'] for r in chosen]),
                                 relative_delta=distribution([r['fraction_new_minus_modern'] for r in chosen]),
                                 known_identical_anchors=sum(r['same_common_anchor'] is True for r in chosen),
                                 saved_error_rows=sum(bool(r['saved_errors']) for r in chosen),
                                 saved_timeout_rows=sum(bool(r['saved_timeouts']) for r in chosen))
    scope = ('Descriptive unchanged physical all32 study. Pooled user/resource distributions weight K16 cases more heavily; '
             'median-of-case-medians gives each case equal weight. All SNRs are nominal received SNR g*0.1 W, not SINR or throughput. '
             'Historical rates were exactly rechecked; their timing scopes differ. No rate-significance test was performed.')
    output = dict(data_suitability=groups, rates=rates, modern_summary=comparison, modern_rows=modern,
                  all_case_rates=detailed, scope=scope,
                  replay_sha256=sha((HERE/'replay-result.json').read_bytes()),
                  output_manifest_sha256=sha((final/'OUTPUT_MANIFEST.json').read_bytes()))
    save(HERE/'analysis'/'descriptive.json', output)
    for filename, table in (('all-case-rates.csv', detailed), ('historical-modern-rates.csv', modern)):
        columns = sorted({k for row in table for k in row})
        with (HERE/'analysis'/filename).open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(table)
    print(json.dumps(dict(data_suitability=groups, rates=rates, modern_summary=comparison), indent=2))


if __name__ == '__main__':
    main()
