import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
from pathlib import Path
import sys,itertools,json,time,numpy as np
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'comparison'))
from core import evaluate,optimize_all4,upper_bound,schedules4
from supervisor import atomic
sys.path.insert(0,str(R.parent/'gpu'));import benchmark as grid

def main(jobpath):
 start=time.perf_counter();job=json.loads(Path(jobpath).read_text());d=np.load(job['input']);out=Path(job['output'])
 atomic(out,{'stage':'loaded','completed':False})
 scale=np.sqrt(.1*float(d['noise']));truth=d['truth'].reshape(4,-1,2)/scale;est=d['estimate'].reshape(4,-1,2)/scale
 edges,A,power,slot,pidx=grid.matrices(4)
 q=grid.rates(truth*np.sqrt(grid.NOISE),edges,np).ravel()/2
 qhat=grid.rates(est*np.sqrt(grid.NOISE),edges,np).ravel()/2
 actions=[]
 for schedule in schedules4():
  for p in itertools.product(grid.GRID,repeat=4):
   if sum(p)>.4+1e-12:continue
   cols=[]
   for pair,s in schedule:
    e=edges.index(pair);profile=list(itertools.product(grid.GRID,repeat=2)).index((p[pair[0]],p[pair[1]]))
    cols.append((e*2+s)*9+profile)
   actions.append((schedule,np.array(p),cols))
 scores=np.array([q[a[2]].sum() for a in actions]);estscores=np.array([qhat[a[2]].sum() for a in actions])
 optimum=float(scores.max());schedule,p,cols=actions[int(estscores.argmax())]
 raw0=evaluate(truth,est,p,schedule)[0]/2;perfect0=evaluate(truth,truth,p,schedule)[0]/2
 assert abs(perfect0-q[cols].sum())<1e-8 and raw0<=perfect0+1e-8
 ip=milp(-q,integrality=np.ones(len(q)),bounds=Bounds(0,1),constraints=[LinearConstraint(A,1,1),LinearConstraint(power[None,:],-np.inf,.4)],options={'time_limit':2,'mip_rel_gap':0})
 lp=linprog(-q,A_eq=A,b_eq=np.ones(A.shape[0]),A_ub=power[None,:],b_ub=[.4],bounds=(0,1),method='highs',options={'time_limit':2})
 assert ip.status==lp.status==0 and abs(-ip.fun-optimum)<1e-7
 lam=-lp.eqlin.marginals;mu=float(-lp.ineqlin.marginals[0]);assert mu>=-1e-10;mu=max(mu,0)
 dual=float(lam.sum()+mu*.4+np.maximum(0,q-A.T@lam-mu*power).sum())
 assert dual>=optimum-1e-7 and abs(dual+lp.fun)<1e-7
 baseline=job['continuous_baseline'];pcont=np.array(baseline['p']);sc=baseline['schedule']
 actualcont=evaluate(truth,est,pcont,sc)[0]/2;perfectcont=evaluate(truth,truth,pcont,sc)[0]/2
 assert abs(actualcont-baseline['actual_sumSE']/2)<1e-8 and actualcont<=perfectcont+1e-8
 oracle=optimize_all4(truth);lower=max(oracle['nominal_SE']/2,perfectcont,optimum)
 upper=upper_bound(truth,.4)/2
 assert upper>=lower-1e-8 and upper>=optimum-1e-8
 result={'completed':True,'stage':'completed','seconds':time.perf_counter()-start,'actions_enumerated':len(actions),
 'grid':{'causal_actual_raw':raw0,'same_action_perfect_raw':perfect0,'receiver_loss':perfect0-raw0,'oracle_exact_raw':optimum,'scheduling_power_opportunity':optimum-perfect0,'LP_upper_raw':dual,'LP_gap':dual-optimum,'no_probe_net':.98*raw0,'B_exact':.975*optimum-.98*raw0,'B_LP':.975*dual-.98*raw0},
 'continuous':{'causal_actual_raw':actualcont,'same_action_perfect_raw':perfectcont,'receiver_loss':perfectcont-actualcont,'oracle_lower_raw':lower,'oracle_upper_raw':upper,'scheduling_power_lower':lower-perfectcont,'scheduling_power_upper':upper-perfectcont,'no_probe_net':.98*actualcont,'B_lower':.975*lower-.98*actualcont,'B_upper':.975*upper-.98*actualcont},
 'witness':{'q_true':q,'q_estimate':qhat,'LP_x':lp.x,'IP_x':ip.x,'lambda':lam,'mu':mu,'grid_initial_power':p,'grid_initial_schedule':schedule},'scope':'offline true-CSI diagnostic, not an online causal policy or novel theorem'}
 atomic(out,result)
if __name__=='__main__':main(sys.argv[1])
