import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
from pathlib import Path
import itertools,json,time,sys
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,vstack
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'comparison'));from supervisor import atomic

def matrices(n):
 start=time.perf_counter();s=n//2;edges=list(itertools.combinations(range(n),2));cols=[(e,r) for e in edges for r in range(s)];index={c:i for i,c in enumerate(cols)}
 A=np.zeros((n+s,len(cols)))
 for j,(e,r) in enumerate(cols):A[list(e)+[n+r],j]=1
 odd=[];b=[]
 for size in range(3,n,2):
  for group in itertools.combinations(range(n),size):
   odd.append([int(set(e)<=set(group)) for e,r in cols]);b.append((size-1)/2)
 supports=[]
 for group in itertools.combinations(range(n),4):
  a,c,d,e=group;parts=[[(a,c),(d,e)],[(a,d),(c,e)],[(a,e),(c,d)]]
  for r,t in itertools.combinations(range(s),2):
   for i,j in itertools.permutations(range(3),2):
    support=[index[(x,r)] for x in parts[i]]+[index[(x,t)] for x in parts[j]]
    for u,v in itertools.combinations(support,2):
     eu,ru=cols[u];ev,rv=cols[v];assert ru==rv or set(eu)&set(ev)
    supports.append(support)
 row=np.repeat(np.arange(len(supports)),4);col=np.array(supports).ravel()
 clique=csr_matrix((np.ones(len(row)),(row,col)),shape=(len(supports),len(cols)))
 C=csr_matrix(np.array(odd));both=vstack([C,clique],format='csr');rhs=np.r_[b,np.ones(len(supports))]
 return A,C,np.array(b),both,rhs,len(supports),time.perf_counter()-start

def solve(q,A,C,b):
 start=time.perf_counter();p=linprog(-q,A_eq=A,b_eq=np.ones(A.shape[0]),A_ub=C,b_ub=b,bounds=(0,1),method='highs',options={'time_limit':3})
 duration=time.perf_counter()-start
 if not p.success:return {'status':'UNRESOLVED','solver_status':int(p.status),'seconds':duration}
 assert np.max(abs(A@p.x-1))<1e-7 and np.max(C@p.x-b)<1e-7 and min(p.x)>-1e-7 and max(p.x)<1+1e-7
 lam=-p.eqlin.marginals;mu=np.maximum(0,-p.ineqlin.marginals)
 residual=q-A.T@lam-C.T@mu
 upper=float(lam.sum()+b@mu+np.maximum(0,residual).sum());primal=float(q@p.x)
 assert upper>=primal-1e-7 and upper-primal<1e-6
 return {'status':'OPTIMAL','objective':primal,'dual_upper':upper,'seconds':duration,'fractional_variables':int(np.count_nonzero(abs(p.x-np.round(p.x))>1e-7)),'max_primal_residual':float(max(np.max(abs(A@p.x-1)),np.max(C@p.x-b)))}

start=time.perf_counter();data=json.loads((R.parent/'structure/solver-results.json').read_text());assert len(data['rows'])==240
cache={n:matrices(n) for n in [4,6,8]};rows=[]
for i,case in enumerate(data['rows']):
 assert case['status']=='OPTIMAL'
 A,C,b,D,d,num,build=cache[case['users']];q=np.array(case['q']).ravel()
 old=solve(q,A,C,b);new=solve(q,A,D,d)
 if old['status']=='OPTIMAL':assert abs(old['objective']-case['LP_odd'])<1e-7
 if new['status']=='OPTIMAL':assert case['MILP']<=new['dual_upper']+1e-7 and new['objective']<=case['LP_odd']+1e-7
 rows.append({'index':i,**{k:case[k] for k in ['users','geometry','mode','noise','sample','MILP','LP_odd']},'clique_rows':num,'build_seconds_once_per_size':build,'base':old,'strengthened':new})
 atomic(R/'cut-results.json',{'status':'IN_PROGRESS','rows':rows,'elapsed':time.perf_counter()-start})
 if (i+1)%40==0:print('completed',i+1,flush=True)
atomic(R/'cut-results.json',{'status':'COMPLETED','rows':rows,'elapsed':time.perf_counter()-start,'scope':'all240 preexisting fixed-power development tables, classical cuts, not general exactness or novelty'})
