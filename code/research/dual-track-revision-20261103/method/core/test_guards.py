"""Guard fixtures after final callback/deadline integration edits."""
import json,time
from pathlib import Path
from fractions import Fraction as F
import numpy as np
from problem import Problem,Deadline
from test_core import physical_case,scalar_problem
import transfer,search,reference_orthogonal

h=np.zeros((4,4,2),complex)
for i in range(4):
    for s in range(2):h[i,i,s]=(16+3*i+2*s)/16
problem=Problem(physical_case(h));assignment=((0,1),(2,3));anchor=problem.checked_candidate(assignment,[F(1,20)]*4)
def bad_publish(*args):raise OSError('injected publication failure')
result=search.run('T',problem,anchor,time.monotonic()+2,991,bad_publish)
assert result['status']=='error' and result['diagnostics']['errors'][0]['type']=='OSError',result
assert result['candidate']['schedule']==anchor['schedule'],'unpublished candidate incorrectly committed'
# All planned random starts identical, irrespective of method, with deadline already expired.
starts=[]
for name in ['T','S','W']:
    result=search.run(name,problem,anchor,time.monotonic()-1,991)
    starts.append(result['diagnostics']['planned_start_sha256'])
    assert result['candidate']['schedule']==anchor['schedule']
assert len(set(starts))==1
# Accepted callbacks are rational, strictly enclosure-monotone within fixed assignment.
old=anchor;trace=[]
def record(a,p,d):
    global old
    new=problem.checked_candidate(a,p)
    assert new['lo']>old['hi'];assert sum(new['powers'])<=problem.budget
    old=new;trace.append(float(new['lo']));return True
out,diag=transfer.refine_power(problem,assignment,anchor['powers'],time.monotonic()+.5,np.random.default_rng(991),record)
assert trace and problem.checked_candidate(assignment,out)['lo']>=anchor['lo']
# Root failure: endpoints/zero retained and feasible, no exact-line claim.
p=scalar_problem('1','10','1/2');st=transfer.new_stats()
def bad_roots(c):raise ValueError('forced roots')
out=transfer.line_best(p,assignment,[.1]*4,[1,-1,0,0],-.05,.05,time.monotonic()+1,st,bad_roots)
assert st['root_failures']==1 and p.checked_candidate(assignment,out)['lo']>=p.checked_candidate(assignment,[.1]*4)['lo']
# Expired line evaluation fails immediately before proposal/check publication.
try:transfer.line_best(p,assignment,[.1]*4,[1,-1,0,0],-.05,.05,time.monotonic()-1)
except Deadline:pass
else:raise AssertionError('deadline not honored')
# Exact orthogonal reference rejects nonorthogonal model and retains conservative bound on timeout.
c=physical_case(h);timed=reference_orthogonal.solve(c,time.monotonic()-1)
assert timed['status']=='deadline' and F(timed['lower_nats'])<=F(timed['upper_nats'])
c['pairs'][0]['r']='1/2'
try:reference_orthogonal.solve(c,time.monotonic()+1)
except ValueError:pass
else:raise AssertionError('nonorthogonal reference accepted')
# Illegal incidence, nonfinite proposals, and exact power repair guard.
for bad_assignment,powers in [(((0,1),(0,3)),[.1]*4),(assignment,[float('nan')]*4)]:
    try:problem.checked_candidate(bad_assignment,powers)
    except (ValueError,KeyError):pass
    else:raise AssertionError('invalid candidate accepted')
repaired=problem.repair([.3,.3,.3,.3]);assert sum(repaired)<=problem.budget and min(repaired)>=problem.low
Path('CORE_GUARD_RESULTS.json').write_text(json.dumps(dict(status='PASS',publication_failure_rolled_back=True,planned_starts_identical=True,monotone_accepted_moves=len(trace),forced_root_fallback=True,expired_line=True,reference_rejects_nonorthogonal=True,exact_feasibility=True),indent=2),encoding='utf-8')
print('Core guards PASS')
