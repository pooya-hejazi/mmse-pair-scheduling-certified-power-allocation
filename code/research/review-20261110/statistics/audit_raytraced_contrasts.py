"""Recompute the four archived contrasts in supplementary Section S12."""
from pathlib import Path
import csv, json
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT/'research/phase1-benchmark-20261109'
def read(name):
    with (DATA/name).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))
ray, controlled = read('m2_results.csv'), read('controlled_results.csv')
groups = [('K8_ray_slsqp', [r for r in ray if int(r['K']) == 8], 'slsqp', 24),
          ('K8_ray_matching', [r for r in ray if int(r['K']) == 8], 'matching', 24),
          ('K16_ray_matching', [r for r in ray if int(r['K']) == 16], 'matching', 8),
          ('K16_controlled_matching', controlled, 'matching', 12)]
result = {}
for name, rows, baseline, count in groups:
    assert len(rows) == count and len({r['name'] for r in rows}) == count
    gain = np.array([(float(r['proposed_rate'])-float(r[baseline+'_rate'])) /
                     float(r[baseline+'_rate']) for r in rows])
    draws = np.random.default_rng(20261109).integers(0, count, (10000, count))
    result[name] = dict(n=count, median_percent=float(np.median(gain)*100),
        mean_percent=float(np.mean(gain)*100),
        mean_case_bootstrap_95_percent=np.percentile(gain[draws].mean(1)*100, [2.5,97.5]).tolist(),
        relative_tolerance=1e-4,
        wins_ties_losses=[int(sum(gain>1e-4)), int(sum(abs(gain)<=1e-4)), int(sum(gain< -1e-4))])
(HERE/'raytraced_contrasts.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('Four archived S12 contrasts recomputed; case resampling is descriptive.')
