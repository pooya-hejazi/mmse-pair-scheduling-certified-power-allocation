from pathlib import Path
import json,hashlib,numpy as np
R=Path(__file__).resolve().parent;d=json.loads((R/'frozen-results.json').read_text());manifest=json.loads((R/'frozen-manifest.json').read_text());prior=json.loads((R/'results.json').read_text())
assert d['status']=='COMPLETED' and len(d['rows'])==32
for f,h in manifest['files'].items():assert hashlib.sha256((R/f).read_bytes()).hexdigest()==h
for c in manifest['cases']:assert hashlib.sha256(Path(c['input']).read_bytes()).hexdigest()==c['sha256']
old={(r['context'],r['sample']):r['result'] for r in prior['rows']};values=[]
for row in d['rows']:
 assert row['execution']['status']=='COMPLETED' and row['result']['completed']
 r=row['result'];values.append(r);previous=old[(row['context'],row['sample'])]
 assert r['oracle_raw']<=previous['grid']['oracle_exact_raw']+1e-7
 assert abs(r['causal_raw']-previous['grid']['causal_actual_raw'])<1e-8
 assert np.all(np.array(r['witness']['q_frozen_receiver'])<=np.array(r['witness']['q_true_MMSE'])+1e-8)
denom=sum(r['no_probe_net'] for r in values)
opportunity=sum(max(0,r['B_exact']) for r in values)/denom
out={'N':32,'elapsed_seconds':d['elapsed'],'exact_grid_decision_only_positive_opportunity':opportunity,'LP_positive_opportunity_upper':sum(max(0,r['B_LP']) for r in values)/denom,'no_acquisition_certificates_exact':sum(r['B_exact']<=0 for r in values),'no_acquisition_certificates_LP':sum(r['B_LP']<=0 for r in values),'positive_LP_gaps':sum(r['LP_gap']>1e-7 for r in values),'threshold':.01,'gate':'STOP_THIS_GRID_FIXED_ESTIMATE_SELECTOR_ROUTE' if opportunity<=.01 else 'NECESSARY_HEADROOM_GATE_ONLY','checks':'all32complete; hashes, coefficientdomination, causalbaselineidentity and oracleordering passed','limits':'finite-grid, same32developmentnetworks, fixedestimate receiver mapping, T200; not allcontinuous or allwirelessmodels'}
(R/'frozen-summary.json').write_text(json.dumps(out,indent=2))
text=f'''# Optimization-only information: the current route fails its gate

All32 prescribed cases completed in{d['elapsed']:.2f}s. The initial channel estimate is fixed for every candidate's receiver calculation; only the action is granted true-channel oracle knowledge. All six schedules and the full prescribed power grid were enumerated and checked against MILP and LP.

Exact positive-part opportunity is **{100*opportunity:.4f}%** of aggregate no-probe rate, below the predeclared1% engineering threshold. In{out['no_acquisition_certificates_exact']}/32 cases even an oracle choosing the best action cannot repay the additional pilot symbol under this fixed receiver-information contract. The ordinary LP upper-bound opportunity is{100*out['LP_positive_opportunity_upper']:.4f}%; its looseness is reported separately.

Decision: stop further tuning of selective information for this unchanged finite-grid, fixed-estimate receiver-mapping family. This is an offline pointwise bound and an empirical aggregate over the32fixedcases, not a population impossibility theorem. It does not rule out continuous-power decisions, receiver-information improvement or a different physical model. No favorable context was selected and no threshold was changed.

The earlier89% receiver-first decomposition was merely descriptive; the present calculation supplies the correctly scoped decision-only ceiling. The continuous/I-WMMSE baseline experiment remains negative without proving a corresponding universal continuous ceiling.

Astra's proposed next alternative keeps the emphasis on optimization: construct rational multiantenna channels that realize positive LP gaps even arbitrarily close to orthogonality, and examine a precise complexity reduction. Existing abstract X3C evidence did not establish hardness of the physical two-user-group family. Any resulting theorem must state channel/dimension/resource assumptions and undergo prior-art and independent mathematical review; no novelty or publishability is currently asserted.
'''
(R/'FROZEN_REPORT.md').write_text(text,encoding='utf8');print(json.dumps(out,indent=2))
