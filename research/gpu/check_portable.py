"""CPU-only portable correctness test; no scenario, GPU, or trained estimator required."""
import itertools,json,numpy as np
from benchmark import matrices,rates,NOISE,cpu_solve,matchings,GRID
rng=np.random.default_rng(126000)
h=(rng.normal(size=(4,5,2))+1j*rng.normal(size=(4,5,2)))*np.sqrt(NOISE)
edges,A,power,slot,pidx=matrices(4);v=rates(h,edges,np);q=v.ravel()
for e,(u,w) in enumerate(edges):
 for s in range(2):
  for j,(pu,pv) in enumerate(itertools.product(GRID,repeat=2)):
   a=h[u,:,s];b=h[w,:,s];eye=NOISE*np.eye(5)
   aa=pu*np.vdot(a,np.linalg.solve(eye+pv*np.outer(b,b.conj()),a)).real
   bb=pv*np.vdot(b,np.linalg.solve(eye+pu*np.outer(a,a.conj()),b)).real
   assert np.isclose(v[e,s,j],np.log2(1+aa)+np.log2(1+bb),atol=1e-10)
fi,_=cpu_solve(q,A,power,.4,'max_rate',True,mask=np.flatnonzero(pidx==4));target=.95*fi['rate_Mbps']
feasible=[]
for m in matchings(list(range(4))):
 for ss in itertools.permutations(range(2)):
  for pp in itertools.product(range(9),repeat=2):
   ix=[(edges.index(e)*2+s)*9+p for e,s,p in zip(m,ss,pp)]
   if power[ix].sum()<=.4+1e-12:feasible.append((q[ix].sum(),power[ix].sum()))
for kind,key,optimum in [('max_rate','rate_Mbps',max(v for v,p in feasible)),('min_power','power_W',min(p for v,p in feasible if v>=target-1e-10))]:
 t=None if kind=='max_rate' else target
 ip,_=cpu_solve(q,A,power,.4,kind,True,target=t);lp,_=cpu_solve(q,A,power,.4,kind,False,target=t)
 assert ip['optimal'] and lp['optimal'] and abs(ip[key]-optimum)<1e-7
 assert lp[key]>=ip[key]-1e-7 if kind=='max_rate' else lp[key]<=ip[key]+1e-7
print(json.dumps({'result':'PASS','scope':'synthetic 4UE matrix-rate check and complete scheduling/power enumeration for both objectives; not real-data replication'}))
