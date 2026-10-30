"""Replay saved feasible schedules, bound directions, input hashes, and small exact bounds."""
from pathlib import Path
from fractions import Fraction as F
import json,itertools,hashlib
import numpy as np
from benchmark import matrices,matchings,feasibility,FEAS
R=Path(__file__).resolve().parent
pre=json.loads((R/'pre-run-manifest.json').read_text())
for f in pre['files']:assert hashlib.sha256((R/f['path']).read_bytes()).hexdigest()==f['sha256']
d=json.loads((R/'results.json').read_text());checked=[]
for row in d['rows']:
 if 'columns' not in row:continue
 n=row['users'];inp=np.load(R/f'instance-{n}.npz');q=inp['q'];power=inp['power'];edges,A,ee,slot,pidx=matrices(n)
 assert np.array_equal(ee,power) and len(q)==row['columns']
 assert hashlib.sha256((R/f'instance-{n}.npz').read_bytes()).hexdigest()==row['instance_sha256']
 for name in ['fixed_power_MILP','joint_power_MILP','minimum_power_MILP']:
  if name not in row or not row[name]['feasibility']['valid']:continue
  sol=row[name];x=np.zeros(len(q));x[sol['selected']]=1
  target=row.get('minimum_power_target_Mbps') if name=='minimum_power_MILP' else None
  assert feasibility(x,A,power,row['power_budget_W'],True,q,target)['valid']
  assert abs(q@x-sol['rate_Mbps'])<FEAS and abs(power@x-sol['power_W'])<FEAS
  if name=='fixed_power_MILP':assert np.all(pidx[sol['selected']]==4)
 if row['joint_power_LP']['optimal'] and row['joint_power_MILP']['feasibility']['valid']:
  assert row['joint_power_LP']['rate_Mbps']>=row['joint_power_MILP']['rate_Mbps']-FEAS
 if row.get('minimum_power_LP',{}).get('optimal') and row['minimum_power_MILP']['feasibility']['valid']:
  assert row['minimum_power_LP']['power_W']<=row['minimum_power_MILP']['power_W']+FEAS
 checked.append(n)
# Weighted budget destroys integrality even for a choose-one polytope.
integer_value=F(2);fractional=F(1,2)*2+F(1,2)*3
assert fractional==F(5,2)>integer_value and F(1,2)*1+F(1,2)*2==F(3,2)
# Check matching+resource+power-price upper bound independently on a full small family.
rng=np.random.default_rng(127000);edges,A,power,slot,pidx=matrices(4);q=rng.uniform(0,10,(6,2,9));budget=.4
solutions=[]
for mat in matchings(list(range(4))):
 for slots in itertools.permutations(range(2)):
  for profiles in itertools.product(range(9),repeat=2):
   ix=[(edges.index(e)*2+s)*9+p for e,s,p in zip(mat,slots,profiles)]
   if power[ix].sum()<=budget+1e-12:solutions.append(float(q.ravel()[ix].sum()))
opt=max(solutions)
for _ in range(30):
 lam=rng.normal(size=2);mu=rng.uniform(0,10);adjusted=q-lam[None,:,None]-mu*power.reshape(6,2,9)
 weights=adjusted.max(axis=(1,2));upper=lam.sum()+mu*budget+max(sum(weights[edges.index(e)] for e in mat) for mat in matchings(list(range(4))))
 assert upper>=opt-1e-10
base=json.loads((R.parent/'reproduction/run-manifest.json').read_text())
for f in base['files']:assert hashlib.sha256((R.parents[1]/f['path']).read_bytes()).hexdigest()==f['sha256']
out={'result':'PASS','saved_incumbent_sizes_replayed':checked,'pre_run_hashes_unchanged':True,'S02_hashes_unchanged':True,'exact_budget_counterexample':{'IP':'2','LP':'5/2'},'power_price_bounds_checked':30,'scope':'author verification; no independent scientific stage acceptance; LP primal vectors not stored, solver LP statuses are recorded evidence'}
(R/'verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
