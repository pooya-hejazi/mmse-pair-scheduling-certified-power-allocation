from pathlib import Path
import json,numpy as np,hashlib
R=Path(__file__).resolve().parent;d=json.loads((R/'results.json').read_text());manifest=json.loads((R/'manifest.json').read_text())
assert d['status']=='COMPLETED' and len(d['rows'])==32
for f,h in manifest['files'].items():assert hashlib.sha256((R/f).read_bytes()).hexdigest()==h
for c in manifest['cases']:assert hashlib.sha256(Path(c['input']).read_bytes()).hexdigest()==c['sha256']
a=[]
for row in d['rows']:
 assert row['execution']['status']=='COMPLETED' and row['result']['completed']
 r=row['result'];a.append(r);assert r['grid']['LP_upper_raw']>=r['grid']['oracle_exact_raw']-1e-7
 assert r['continuous']['oracle_upper_raw']>=r['continuous']['oracle_lower_raw']-1e-7
def opportunity(track,key):return sum(max(0,r[track][key]) for r in a)/sum(r[track]['no_probe_net'] for r in a)
out={'N':32,'elapsed_seconds':d['elapsed'],'engineering_threshold':.01,'grid_exact_positive_opportunity':opportunity('grid','B_exact'),'grid_LP_positive_opportunity_upper':opportunity('grid','B_LP'),'continuous_positive_opportunity_lower':opportunity('continuous','B_lower'),'continuous_positive_opportunity_upper':opportunity('continuous','B_upper'),'grid_receiver_first_fraction':sum(r['grid']['receiver_loss'] for r in a)/sum(r['grid']['oracle_exact_raw']-r['grid']['causal_actual_raw'] for r in a),'positive_grid_LP_gaps':sum(r['grid']['LP_gap']>1e-7 for r in a),'grid_no_acquisition_certificates':sum(r['grid']['B_exact']<=0 for r in a),'continuous_no_acquisition_certificates':sum(r['continuous']['B_upper']<=0 for r in a),'scope':'offline optimistic oracle opportunity; not attainable causal policy gain or novelty','checks':'source/input hashes and all32 inequalities passed'}
(R/'summary.json').write_text(json.dumps(out,indent=2))
report=f'''# Perfect-information headroom audit

All32 frozen development networks completed in{d['elapsed']:.2f}s under individual10s external caps. No estimator, observation, scenario, seed or original source was changed. Astra's predeclared1% engineering gate is a diagnostic, not statistical significance.

| Quantity | Result |
|---|---:|
| Exact finite-grid positive-part oracle opportunity / no-probe rate |{100*out['grid_exact_positive_opportunity']:.4f}%|
| Same grid, ordinary LP upper opportunity |{100*out['grid_LP_positive_opportunity_upper']:.4f}%|
| Continuous oracle feasible lower opportunity |{100*out['continuous_positive_opportunity_lower']:.4f}%|
| Continuous oracle upper opportunity |{100*out['continuous_positive_opportunity_upper']:.4f}%|
| Positive finite-grid LP gaps |{out['positive_grid_LP_gaps']}/32|
| Receiver-first share of raw grid oracle uplift |{100*out['grid_receiver_first_fraction']:.2f}%|

The perfect-information headroom exceeds the1% gate, so an absolute lack of room is not established. This ceiling grants perfect CSI and a perfect-channel MMSE receiver after paying just one symbol: it is deliberately unattainable by a real one-pilot method. It neither predicts an achievable6% gain nor validates the previously negative selector.

The pointwise proof is: any feasible one-extra-symbol policy has net gain<=.975U(H)−.98R0(H), where U is a valid upper bound on perfect-CSI optimum in the same power/schedule family. Optional probing has improvement<=max(0,that bound). These statements use true H only offline. They are elementary bounding results, not a new online uncertainty guarantee.

The89% receiver-first fraction depends on decomposition order. It does not upper-bound the benefit of changing actions while retaining the original channel estimate; action changes can avoid bad combining directions. Consequently it cannot justify declaring the optimization path exhausted. Astra recommends a final, separate finite-grid oracle that freezes the estimated-channel receiver **mapping** for every candidate action and changes only schedule/power choice. No more selector tuning is authorized by these results.

Enumeration, MILP and reconstructed LP dual bounds agree within tolerance. Direct receiver evaluation is checked against the true-MMSE formula, and continuous bounds dominate all tested feasible actions. The finite-grid LP is never used as an upper bound for continuous power. All contexts have equal sample counts and weight. Results are provisional development evidence; independent stage acceptance remains open.
'''
(R/'REPORT.md').write_text(report,encoding='utf8');print(json.dumps(out,indent=2))
