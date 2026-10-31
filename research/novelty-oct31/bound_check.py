from pathlib import Path
from fractions import Fraction as F
import itertools,json,hashlib,time
import numpy as np
R=Path(__file__).resolve().parent;root=R.parents[1];start=time.perf_counter()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((R/'bound-manifest.json').read_text())
for name,h in manifest['files'].items():assert digest(root/name)==h
grid=[F(1,20),F(1,10),F(1,5)];powers=[F(1,20),F(3,40),F(1,10),F(3,20),F(1,5)]
def product(g1,g2,c,p1,p2):
 D=(1+g1*p1)*(1+g2*p2)-c*p1*p2
 return D*D/((1+g1*p1)*(1+g2*p2))
cases=0;negative_derivatives=0
for g1,g2,r,p1,p2 in itertools.product([F(0),F(1),F(10)],[F(0),F(1),F(10)],[F(0),F(1,2),F(1)],powers,powers):
 c=g1*g2*r;D=(1+g1*p1)*(1+g2*p2)-c*p1*p2
 for gi,pi,pj in [(g1,p1,p2),(g2,p2,p1)]:
  Di=gi+(g1*g2-c)*pj;derivative=2*Di/D-gi/(1+gi*pi);cap=gi/(1+gi*pi)
  assert -cap<=derivative<=cap;negative_derivatives+=int(derivative<0)
 a=max(x for x in grid if x<=p1);b=max(x for x in grid if x<=p2)
 assert a>=grid[0] and b>=grid[0] and a+b<=p1+p2
 ratio=product(g1,g2,c,p1,p2)/product(g1,g2,c,a,b)
 integrated=((1+g1*p1)/(1+g1*a))*((1+g2*p2)/(1+g2*b))
 global_cap=np.prod([max((1+g*hi)/(1+g*lo) for lo,hi in zip(grid[:-1],grid[1:])) for g in [g1,g2]])
 assert F(1,1)/integrated<=ratio<=integrated<=global_cap
 cases+=1
old=json.loads((root/'research/comparison/results.json').read_text());inputs=json.loads((root/'research/comparison/inputs.json').read_text());rows=[]
for n in [8,16,32]:
 inp=next(i for i in inputs if i['mode']=='power' and i['users']==n);p=root/'research/comparison/inputs'/Path(inp['input']).name
 assert digest(p)==inp['sha256'];h=np.load(p)['h'];gmax=(abs(h)**2).sum(axis=1).max(axis=1)
 a=np.array([.05,.1]);b=np.array([.1,.2]);Ei=np.log2((1+gmax[:,None]*b)/(1+gmax[:,None]*a)).max(axis=1);E=float(Ei.sum())
 ip=next(r for r in old['rows'] if r['mode']=='power' and r['users']==n and r['arm']=='grid');lp=next(r for r in old['rows'] if r['mode']=='power' and r['users']==n and r['arm']=='lp')
 assert ip['status']==lp['status']=='COMPLETED' and ip['result']['optimal'] and lp['result']['optimal']
 V=float(ip['result']['nominal_SE']);U=float(lp['result']['nominal_SE'])
 assert 0<=E<=n+1e-10
 rows.append({'users':n,'archived_grid_MILP_sumSE':V,'archived_grid_LP_sumSE_numerical':U,'rounding_allowance_sumSE':E,'allowance_over_archived_grid_value':E/V,'conditional_LP_value_plus_allowance':U+E,'certified_continuous_upper_from_archived_dual':False,'reason':'archived LP dual vectors were not retained; adding E to a reported numerical optimum is illustrative, not a new rigorous certificate'})
for name,h in manifest['files'].items():assert digest(root/name)==h
out={'result':'PASS','rational_cases':cases,'derivative_assertions':2*cases,'negative_derivative_cases':negative_derivatives,'elapsed_seconds':time.perf_counter()-start,'rows':rows,'scope':'standard bound checks and all3 existing input allowances; no new solver run, no performance improvement or novelty evidence'}
(R/'bound-checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
