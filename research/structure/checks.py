from pathlib import Path
import json,itertools,hashlib
import numpy as np
from scipy.optimize import linear_sum_assignment
from solver_study import structure,assignment,solve
R=Path(__file__).resolve().parent
# Generic assignment reduction counterexample; not a claimed physical channel witness.
W=np.zeros((6,6))
for group in [(0,1,2),(3,4,5)]:
    for a,b in itertools.combinations(group,2):W[a,b]=W[b,a]=10
ri,ci=linear_sum_assignment(-W);edges,_,_,_,mats=structure(6)
match=max(sum(W[edges[e]] for e in m) for m in mats)
assert W[ri,ci].sum()==60 and match==20
# Printed 2025 objective: trace(PSD PSD)>=0 and M=0 makes objective zero.
cov=[np.diag([1.,2.]),np.diag([2.,3.])];coeff=np.trace(cov[0]@cov[1]);assert coeff==8
assert 0*coeff==0 and .5*.5*coeff > .5*(0*coeff+0*coeff)
result=json.loads((R/'solver-results.json').read_text());count=0
for row in result['rows']:
    q=np.array(row['q']);st=structure(row['users'])
    # Complete independent integer objective by enumerating pairings, then exact resource assignment.
    exact=max(assignment(q,m)[0] for m in st[-1])
    if row['status']=='OPTIMAL':
        assert abs(exact-row['MILP'])<1e-7
        assert row['lower']<=exact+1e-7<=row['upper_priced']+2e-7
        if row['conflictfree_certificate']:assert abs(row['lower']-exact)<1e-7
    count+=1
base=json.loads((R.parent/'reproduction/run-manifest.json').read_text())
for f in base['files']:assert hashlib.sha256((R.parents[1]/f['path']).read_bytes()).hexdigest()==f['sha256']
out={'integer_objectives_replayed':count,'assignment_counterexample':{'permutation_half_weight':30,'true_pair_matching':20,'permutation':ci.tolist(),'scope':'arbitrary symmetric nonnegative weights; not physical realization'},'printed_bilinear_problem_zero_feasible':True,'S02_unchanged':True,'scope':'author checks; independent stage acceptance pending'}
(R/'checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
