from pathlib import Path
from fractions import Fraction as F
from itertools import combinations,product
import json,time,hashlib,os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
from scipy.sparse import csc_matrix
from rational_oracle import maximize,objective_iv,iv,ln_point
D=Path(__file__).resolve().parent;R=D.parents[1];start=time.perf_counter()
inp=R/'research/comparison/inputs/power-8.npz'
expected=next(e['sha256'] for e in json.loads((R/'research/comparison/inputs.json').read_text()) if e.get('mode')=='power' and e.get('users')==8)
assert hashlib.sha256(inp.read_bytes()).hexdigest()==expected
h=np.load(inp)['h'];K,M,S=h.shape;assert (K,S)==(8,4)
budget=F(4,5);levels=[F(1,20),F(1,10),F(1,5)]
hr={};g={}
for u in range(K):
 for t in range(S):
  hr[u,t]=[(F(float(z.real)),F(float(z.imag))) for z in h[u,:,t]]
  g[u,t]=sum(a*a+b*b for a,b in hr[u,t]);assert g[u,t]>0
pairdata=[];columns=[];cost=[];rates=[]
for u,v in combinations(range(K),2):
 for t in range(S):
  re=sum(a*c+b*d for (a,b),(c,d) in zip(hr[u,t],hr[v,t]))
  im=sum(a*d-b*c for (a,b),(c,d) in zip(hr[u,t],hr[v,t]))
  r=(re*re+im*im)/(g[u,t]*g[v,t]);assert 0<=r<=1
  pairdata.append((u,v,t,r))
  for p1,p2 in product(levels,repeat=2):
   x=float(g[u,t]*p1);y=float(g[v,t]*p2)
   q=2*np.log1p(x+y+(1-float(r))*x*y)-np.log1p(x)-np.log1p(y)
   columns.append((u,v,t,p1,p2,r));cost.append(float(p1+p2));rates.append(q)
A=np.zeros((K+S,len(columns)))
for j,(u,v,t,*_) in enumerate(columns):A[[u,v,K+t],j]=1
cost=np.array(cost);rates=np.array(rates)
lp=linprog(-rates,A_ub=cost[None,:],b_ub=[float(budget)],A_eq=A,b_eq=np.ones(K+S),bounds=(0,None),method='highs',options={'time_limit':5})
assert lp.success,lp.message
alpha=[F(float(-x)) for x in lp.eqlin.marginals[:K]]
lam=max(F(0),F(float(-lp.ineqlin.marginals[0])))
ip=milp(-rates,integrality=np.ones(len(columns)),bounds=Bounds(0,1),constraints=[LinearConstraint(csc_matrix(A),1,1),LinearConstraint(csc_matrix(cost[None,:]),-np.inf,float(budget))],options={'time_limit':5,'mip_rel_gap':0})
assert ip.x is not None,ip.message
selected=np.flatnonzero(ip.x>.5);assert np.allclose(ip.x,np.round(ip.x),atol=1e-7)
assert np.all(A[:,selected].sum(1)==1)
power=sum(columns[j][3]+columns[j][4] for j in selected);assert power<=budget
low=F(0);schedule=[]
for j in selected:
 u,v,t,p1,p2,r=columns[j]
 lower,upper=objective_iv(iv(g[u,t]*p1),iv(g[v,t]*p2),r,F(0),F(0))
 low+=lower;schedule.append({'users':[u,v],'resource':t,'powers':[str(p1),str(p2)],'rate_lower_nats':str(lower)})
beta=[None]*S;proofrows=[]
for u,v,t,r in pairdata:
 out=maximize(r,lam/g[u,t],lam/g[v,t],(g[u,t]*levels[0],g[u,t]*levels[-1],g[v,t]*levels[0],g[v,t]*levels[-1]))
 b=out['upper']-alpha[u]-alpha[v]
 beta[t]=b if beta[t] is None else max(beta[t],b)
 proofrows.append({'users':[u,v],'resource':t,'gain1':str(g[u,t]),'gain2':str(g[v,t]),'r':str(r),'pricing_upper_nats':str(out['upper']),'pricing_width':str(out['upper']-out['lower']),'root_digits':out['root_digits']})
assert len(proofrows)==112 and all(b is not None for b in beta)
up=sum(alpha)+sum(beta)+lam*budget;assert up>=low
ln2lo,ln2hi=ln_point(F(2))
result={'status':'COMPLETED','input_sha256':expected,'users':K,'resources':S,'receive_dimensions':M,'grid_columns':len(columns),'pair_pricings':len(proofrows),'lower_nats':str(low),'upper_nats':str(up),'lower_sumSE_display':float(low/ln2hi),'upper_sumSE_display':float(up/ln2lo),'relative_gap_upper_display':float((up-low)/low),'radiated_power_W':str(power),'alpha':[str(x) for x in alpha],'lambda':str(lam),'beta':[str(x) for x in beta],'schedule':schedule,'pricing_certificates':proofrows,'numerical_LP_nats':float(-lp.fun),'numerical_MILP_nats':float(-ip.fun),'MILP_status':int(ip.status),'elapsed_seconds':time.perf_counter()-start,'scope':'provisional integrated continuous-configuration dual certificate; independent integration review pending; no S04, novelty or speedup claim'}
p=D/'network-result.json';assert not p.exists();p.write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ['pricing_certificates','alpha','lambda','beta','schedule','lower_nats','upper_nats']},indent=2))
