import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
from pathlib import Path
import sys,json,itertools,time,numpy as np
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'comparison'))
from core import evaluate,schedules4
from supervisor import atomic
sys.path.insert(0,str(R.parent/'gpu'));import benchmark as grid
def main(jobpath):
 start=time.perf_counter();job=json.loads(Path(jobpath).read_text());d=np.load(job['input']);out=Path(job['output']);scale=np.sqrt(.1*float(d['noise']))
 H=d['truth'].reshape(4,-1,2)/scale;est=d['estimate'].reshape(4,-1,2)/scale
 atomic(out,{'completed':False,'stage':'loaded'})
 edges,A,power,slot,pidx=grid.matrices(4);profiles=list(itertools.product(grid.GRID,repeat=2))
 qtrue=grid.rates(H*np.sqrt(grid.NOISE),edges,np).ravel()/2;qhat=grid.rates(est*np.sqrt(grid.NOISE),edges,np).ravel()/2;qfixed=np.zeros(len(qtrue))
 for j,e in enumerate(edges):
  for s in range(2):
   for k,profile in enumerate(profiles):
    p=np.full(4,.1);p[list(e)]=profile
    qfixed[(j*2+s)*9+k]=evaluate(H,est,p,[(e,s)])[0]/2
 assert np.all(qfixed<=qtrue+1e-8)
 actions=[]
 for sc in schedules4():
  for pp in itertools.product(grid.GRID,repeat=4):
   if sum(pp)>.4+1e-12:continue
   cols=[(edges.index(e)*2+s)*9+profiles.index((pp[e[0]],pp[e[1]])) for e,s in sc]
   actions.append((sc,np.array(pp),cols))
 values=np.array([sum(qfixed[a[2]]) for a in actions]);initial=int(np.argmax([sum(qhat[a[2]]) for a in actions]));V=float(values.max());R0=float(values[initial]);sc,p,cols=actions[initial]
 assert abs(evaluate(H,est,p,sc)[0]/2-R0)<1e-8 and V>=R0-1e-8
 ip=milp(-qfixed,integrality=np.ones(len(qfixed)),bounds=Bounds(0,1),constraints=[LinearConstraint(A,1,1),LinearConstraint(power[None,:],-np.inf,.4)],options={'time_limit':2,'mip_rel_gap':0})
 lp=linprog(-qfixed,A_eq=A,b_eq=np.ones(A.shape[0]),A_ub=power[None,:],b_ub=[.4],bounds=(0,1),method='highs',options={'time_limit':2})
 assert ip.status==lp.status==0 and abs(-ip.fun-V)<1e-7
 lam=-lp.eqlin.marginals;mu=max(0,float(-lp.ineqlin.marginals[0]));upper=float(lam.sum()+.4*mu+np.maximum(0,qfixed-A.T@lam-mu*power).sum())
 assert upper>=V-1e-7 and abs(upper+lp.fun)<1e-7
 atomic(out,{'completed':True,'seconds':time.perf_counter()-start,'causal_raw':R0,'oracle_raw':V,'LP_upper':upper,'LP_gap':upper-V,'B_exact':.975*V-.98*R0,'B_LP':.975*upper-.98*R0,'no_probe_net':.98*R0,'raw_action_gain':V-R0,'actions':len(actions),'witness':{'q_frozen_receiver':qfixed,'q_true_MMSE':qtrue,'q_estimate':qhat,'lambda':lam,'mu':mu,'LP_x':lp.x,'IP_x':ip.x},'scope':'fixed initial-estimate receiver mapping, finite power grid, offline diagnostic only'})
if __name__=='__main__':main(sys.argv[1])
